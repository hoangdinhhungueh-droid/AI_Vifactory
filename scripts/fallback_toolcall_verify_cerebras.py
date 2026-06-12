#!/usr/bin/env python3
# scripts/fallback_toolcall_verify.py
# TOOL-CALLING nhom FALLBACK (provider truc tiep, payload sach da strip store).
# Xac nhan tung fallback goi tool dung + latency/tps/on-dinh -> giu nguyen chain neu KEEP.
import os, time, json
import urllib.request, urllib.error

TIMEOUT_S = int(os.getenv("FB_TIMEOUT_S", "90"))
N_RUNS    = int(os.getenv("FB_RUNS", "3"))
SLEEP_S   = float(os.getenv("FB_SLEEP_S", "2"))
TOOLS_PAD = int(os.getenv("FB_TOOLS_PAD", "0"))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def _tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}

TOOLS = [
    _tool("run_shell", "Run a shell command on the VPS.", {"command": {"type": "string"}}, ["command"]),
    _tool("notion_search", "Search Notion for pages.", {"query": {"type": "string"}}, ["query"]),
    _tool("calculator", "Evaluate an arithmetic expression.", {"expression": {"type": "string"}}, ["expression"]),
    _tool("read_file", "Read a file by path.", {"path": {"type": "string"}}, ["path"]),
    _tool("save_note", "Save text to a Notion page.", {"page": {"type": "string"}, "content": {"type": "string"}}, ["page", "content"]),
]
CASES = {
    "BRAIN":     ("Kiem tra deploy: chay 'pm2 status' tren VPS.", "run_shell"),
    "REASONING": ("Doc file 'app/llm_router.py' giup toi.", "read_file"),
    "CODE":      ("Chay 'pytest -q'.", "run_shell"),
    "UTILITY":   ("Tinh 27*43+19 bang calculator.", "calculator"),
    "CREATIVE":  ("Luu doan van vao trang Notion 'Draft'.", "save_note"),
}
# Nhom fallback = provider truc tiep (OpenAI-compatible). KHONG gom groq (413 voi 40K).
PROVIDERS = [
    {"name": "cerebras", "base": os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
     "key": os.getenv("CEREBRAS_API_KEY", ""), "model": "gpt-oss-120b"},
    {"name": "cerebras", "base": os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
     "key": os.getenv("CEREBRAS_API_KEY", ""), "model": "zai-glm-4.7"},
]

def _pad_tools():
    tools = list(TOOLS)
    for i in range(TOOLS_PAD):
        tools.append(_tool("dummy_%d" % i, "padding " * 8, {"a_%d" % i: {"type": "string"}}, []))
    return tools

def call_tool(base, key, model, prompt, tools):
    url = base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + key, "User-Agent": UA, "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "tools": tools, "tool_choice": "auto", "temperature": 0.3, "max_tokens": 400, "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        status, body, dt = r.status, r.read().decode(), time.time() - t0
    j = json.loads(body)
    if j.get("error"):
        return {"ok": False, "reason": "err " + str(j["error"])[:80]}
    msg = ((j.get("choices") or [{}])[0].get("message") or {})
    calls = msg.get("tool_calls") or []
    out_tok = (j.get("usage", {}) or {}).get("completion_tokens")
    tps = (out_tok / dt) if (out_tok and dt) else None
    if not calls:
        return {"ok": False, "reason": "no_tool_call", "dt": dt, "tps": tps}
    fn = (calls[0].get("function") or {})
    try:
        json.loads(fn.get("arguments") or "{}"); args_ok = True
    except Exception:
        args_ok = False
    return {"ok": True, "fname": fn.get("name", ""), "args_ok": args_ok, "dt": dt, "tps": tps}

def one(p, prompt, tools):
    try:
        return call_tool(p["base"], p["key"], p["model"], prompt, tools)
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "HTTP " + str(e.code) + " " + e.read()[:100].decode(errors="ignore").replace(chr(10), " ")}
    except Exception as e:
        return {"ok": False, "reason": type(e).__name__ + ": " + str(e)[:90]}

def main():
    tools = _pad_tools()
    print("== FALLBACK TOOL-CALLING VERIFY == runs=" + str(N_RUNS) + " tools=" + str(len(tools)) + "\n")
    rows = []
    for p in PROVIDERS:
        if not p.get("key"):
            print("[SKIP] " + p["name"] + ": missing key"); rows.append((p["name"], 0, None, None)); continue
        print("-- " + p["name"] + " (" + p["model"] + ") --")
        lat, tpsv, total_ok, total = [], [], 0, 0
        for task, (prompt, expect) in CASES.items():
            ok_n = 0; dts = []; tpss = []; reason = ""
            for _ in range(N_RUNS):
                r = one(p, prompt, tools); time.sleep(SLEEP_S); total += 1
                if r["ok"]:
                    if r["fname"] == expect and r["args_ok"]:
                        ok_n += 1; total_ok += 1
                    else:
                        reason = "wrong_tool=" + str(r["fname"])
                    if r.get("dt"): dts.append(r["dt"])
                    if r.get("tps"): tpss.append(r["tps"])
                else:
                    reason = r.get("reason", "")
            rate = ok_n / N_RUNS
            md = round(sorted(dts)[len(dts)//2], 2) if dts else None
            mt = round(sorted(tpss)[len(tpss)//2], 1) if tpss else None
            if md: lat.append(md)
            if mt: tpsv.append(mt)
            print("   " + task.ljust(10) + " ok=" + str(round(rate*100)) + "% dt=" + str(md) + "s tps=" + str(mt) + ("  " + reason if reason else ""))
        avg_rate = total_ok / total if total else 0
        avg_lat = round(sum(lat)/len(lat), 2) if lat else None
        avg_tps = round(sum(tpsv)/len(tpsv), 1) if tpsv else None
        rows.append((p["name"], avg_rate, avg_lat, avg_tps))
        print("   => SUCCESS=" + str(round(avg_rate*100)) + "%  avg_dt=" + str(avg_lat) + "s  avg_tps=" + str(avg_tps) + "\n")
    print("=== FALLBACK SUMMARY ===")
    for name, rate, lat, tps in rows:
        verdict = "KEEP" if rate >= 0.8 else ("WEAK" if rate >= 0.4 else "DROP/review")
        print(name.ljust(14) + ("SUCCESS " + str(round(rate*100)) + "%").ljust(16) + ("avg_dt " + str(lat) + "s").ljust(14) + ("avg_tps " + str(tps)).ljust(16) + verdict)

if __name__ == "__main__":
    main()
