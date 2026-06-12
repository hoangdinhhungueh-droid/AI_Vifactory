#!/usr/bin/env python3
# scripts/or_toolcall_verify.py
# TOOL-CALLING benchmark cho OpenRouter :free -> chot PRIMARY brain.
# Do: correctness (goi dung tool + args JSON), success_rate (N runs = on dinh), latency, tok/s. Theo tung task.
import os, time, json
import urllib.request, urllib.error

OR_BASE   = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OR_KEY    = os.getenv("OPENROUTER_API_KEY", "")
TIMEOUT_S = int(os.getenv("OR_TIMEOUT_S", "90"))
SLEEP_S   = float(os.getenv("OR_SLEEP_S", "3"))     # tranh 20 RPM free
N_RUNS    = int(os.getenv("OR_RUNS", "3"))          # /case -> success_rate
FREE_ONLY = os.getenv("OR_FREE_ONLY", "1") != "0"
MAX_MODELS= int(os.getenv("OR_MAX", "0"))           # 0 = het (~25 model :free)
TOOLS_PAD = int(os.getenv("OR_TOOLS_PAD", "0"))     # +N tool dummy -> mo phong payload 39-tool ~40K
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def _tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}

TOOLS = [
    _tool("run_shell", "Run a shell command on the VPS and return stdout.", {"command": {"type": "string"}}, ["command"]),
    _tool("notion_search", "Search the Notion workspace for pages.", {"query": {"type": "string"}}, ["query"]),
    _tool("calculator", "Evaluate an arithmetic expression.", {"expression": {"type": "string"}}, ["expression"]),
    _tool("read_file", "Read a file by path.", {"path": {"type": "string"}}, ["path"]),
    _tool("save_note", "Save text to a Notion page.", {"page": {"type": "string"}, "content": {"type": "string"}}, ["page", "content"]),
]
CASES = {
    "BRAIN":     ("Kiem tra deploy: chay lenh 'pm2 status' tren VPS giup toi.", "run_shell"),
    "REASONING": ("Hay doc file 'app/llm_router.py' de toi xem cau hinh router.", "read_file"),
    "CODE":      ("Chay test suite bang lenh 'pytest -q'.", "run_shell"),
    "UTILITY":   ("Tinh giup 27*43+19 bang cong cu calculator.", "calculator"),
    "CREATIVE":  ("Luu doan van vao trang Notion 'Draft' voi noi dung 'Bien gioi mo ra'.", "save_note"),
}

def _pad_tools():
    tools = list(TOOLS)
    for i in range(TOOLS_PAD):
        tools.append(_tool("dummy_%d" % i, "padding tool " * 8, {"a_%d" % i: {"type": "string"}}, []))
    return tools

def _req(method, path, payload=None):
    url = OR_BASE.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": "Bearer " + OR_KEY, "User-Agent": UA, "Content-Type": "application/json",
               "HTTP-Referer": "https://localhost", "X-Title": "toolcall-verify"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return r.status, r.read().decode(), time.time() - t0

def list_models():
    pin = [m.strip() for m in os.getenv("OR_MODELS", "").split(",") if m.strip()]
    if pin:
        return pin
    _, body, _ = _req("GET", "/models")
    data = json.loads(body).get("data", [])
    ids = []
    for m in data:
        mid = m.get("id", "")
        if not mid:
            continue
        if FREE_ONLY:
            pr = m.get("pricing", {}) or {}
            free = mid.endswith(":free") or (str(pr.get("prompt", "0")) in ("0", "0.0") and str(pr.get("completion", "0")) in ("0", "0.0"))
            if not free:
                continue
        ids.append(mid)
    ids.sort()
    return ids[:MAX_MODELS] if MAX_MODELS else ids

def call_toolcall(model, prompt, tools):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "tools": tools, "tool_choice": "auto", "temperature": 0.3, "max_tokens": 400, "stream": False}
    status, body, dt = _req("POST", "/chat/completions", payload)
    j = json.loads(body)
    if j.get("error"):
        return {"ok": False, "reason": "err " + str(j["error"].get("code", "")) + " " + str(j["error"].get("message", ""))[:70]}
    msg = ((j.get("choices") or [{}])[0].get("message") or {})
    calls = msg.get("tool_calls") or []
    out_tok = (j.get("usage", {}) or {}).get("completion_tokens")
    tps = (out_tok / dt) if (out_tok and dt) else None
    if not calls:
        return {"ok": False, "reason": "no_tool_call (text-only)", "dt": dt, "tps": tps}
    fn = (calls[0].get("function") or {})
    try:
        json.loads(fn.get("arguments") or "{}"); args_ok = True
    except Exception:
        args_ok = False
    return {"ok": True, "fname": fn.get("name", ""), "args_ok": args_ok, "dt": dt, "tps": tps}

def one(model, prompt, tools):
    try:
        return call_toolcall(model, prompt, tools)
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "HTTP " + str(e.code) + " " + e.read()[:110].decode(errors="ignore").replace(chr(10), " ")}
    except Exception as e:
        return {"ok": False, "reason": type(e).__name__ + ": " + str(e)[:90]}

def main():
    if not OR_KEY:
        print("[FATAL] missing OPENROUTER_API_KEY"); return
    tools = _pad_tools()
    models = list_models()
    print("== OR TOOL-CALLING VERIFY == models=" + str(len(models)) + " runs=" + str(N_RUNS) + " tools=" + str(len(tools)) + "\n")
    rows = []
    for i, m in enumerate(models, 1):
        print("[" + str(i) + "/" + str(len(models)) + "] " + m)
        lat, tpsv, total_ok, total = [], [], 0, 0
        for task, (prompt, expect) in CASES.items():
            ok_n = 0; dts = []; tpss = []; reason = ""
            for _ in range(N_RUNS):
                r = one(m, prompt, tools); time.sleep(SLEEP_S); total += 1
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
        rows.append((m, avg_rate, avg_lat, avg_tps))
        print("   => SUCCESS=" + str(round(avg_rate*100)) + "%  avg_dt=" + str(avg_lat) + "s  avg_tps=" + str(avg_tps) + "\n")
    rows.sort(key=lambda r: (-r[1], r[2] if r[2] is not None else 9e9))
    print("=== RANKING (PRIMARY candidate on top) ===")
    print("MODEL".ljust(50) + "SUCCESS".ljust(9) + "avg_dt".ljust(9) + "avg_tps")
    for m, rate, lat, tps in rows:
        print(m.ljust(50) + (str(round(rate*100)) + "%").ljust(9) + (str(lat) + "s").ljust(9) + str(tps))

if __name__ == "__main__":
    main()
