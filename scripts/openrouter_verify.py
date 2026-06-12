#!/usr/bin/env python3
# scripts/openrouter_verify.py
# Verify OpenRouter models -> pick PRIMARY. Default: quet MOI model :free tu /models.
# Test small-ctx; qua small moi test big-ctx (~50K). Detect 429/413/empty/timeout. Rank theo latency.
import os, time, json
import urllib.request, urllib.error

OR_BASE   = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OR_KEY    = os.getenv("OPENROUTER_API_KEY", "")
TIMEOUT_S = int(os.getenv("OR_TIMEOUT_S", "90"))
BIG_CHARS = int(os.getenv("OR_BIG_CHARS", "120000"))
SLEEP_S   = float(os.getenv("OR_SLEEP_S", "3"))          # nghi giua call -> tranh 20 RPM free
TEST_BIG  = os.getenv("OR_TEST_BIG", "1") != "0"
FREE_ONLY = os.getenv("OR_FREE_ONLY", "1") != "0"
MAX_MODELS = int(os.getenv("OR_MAX", "0"))               # 0 = khong gioi han
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

SMALL_PROMPT = "Enhance this paragraph, keep meaning, return ONLY enhanced text.\n\nThe old man walked to the sea every morning. He had not caught a fish in eighty four days."

def _big_text():
    base = ("Chapter draft line: the protagonist faced another setback as the storm rolled in "
            "over the harbor, testing resolve and reshaping the plan for tomorrow. ")
    return base * ((BIG_CHARS // len(base)) + 1)

BIG_PROMPT = "Summarize then enhance this long draft into <=400 words. Return ONLY the summary.\n\n" + _big_text()

def _req(method, path, payload=None):
    url = OR_BASE.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": "Bearer " + OR_KEY, "User-Agent": UA,
               "Content-Type": "application/json",
               "HTTP-Referer": "https://localhost", "X-Title": "router-verify"}
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

def chat(model, prompt):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.7, "max_tokens": 700, "stream": False}
    status, body, dt = _req("POST", "/chat/completions", payload)
    j = json.loads(body)
    if j.get("error"):
        return {"ok": False, "reason": "err " + str(j["error"].get("code", "")) + " " + str(j["error"].get("message", ""))[:80]}
    text = (((j.get("choices") or [{}])[0].get("message", {}) or {}).get("content", "") or "").strip()
    if len(text) < 20:
        return {"ok": False, "reason": "empty/short status=" + str(status)}
    out_tok = (j.get("usage", {}) or {}).get("completion_tokens")
    tps = (out_tok / dt) if (out_tok and dt) else (len(text) / 4 / dt if dt else None)
    return {"ok": True, "dt": round(dt, 2), "tps": round(tps, 1) if tps else None}

def one(model, prompt):
    try:
        return chat(model, prompt)
    except urllib.error.HTTPError as e:
        msg = e.read()[:120].decode(errors="ignore").replace(chr(10), " ")
        return {"ok": False, "reason": "HTTP " + str(e.code) + " " + msg}
    except Exception as e:
        return {"ok": False, "reason": type(e).__name__ + ": " + str(e)[:100]}

def main():
    if not OR_KEY:
        print("[FATAL] missing OPENROUTER_API_KEY"); return
    models = list_models()
    print("== OPENROUTER VERIFY == models=" + str(len(models)) + " big=" + str(BIG_CHARS) + "c test_big=" + str(TEST_BIG))
    print("")
    rows = []
    for i, m in enumerate(models, 1):
        s = one(m, SMALL_PROMPT)
        time.sleep(SLEEP_S)
        if s["ok"] and TEST_BIG:
            l = one(m, BIG_PROMPT); time.sleep(SLEEP_S)
        else:
            l = {"ok": False, "reason": "skipped" if s["ok"] else "small_failed"}
        sfmt = ("OK " + str(s["dt"]) + "s " + str(s.get("tps")) + "t/s") if s["ok"] else ("FAIL " + s["reason"])
        lfmt = ("OK " + str(l["dt"]) + "s " + str(l.get("tps")) + "t/s") if l["ok"] else ("FAIL " + str(l.get("reason", "")))
        print("[" + str(i) + "/" + str(len(models)) + "] " + m)
        print("   small: " + sfmt)
        print("   big  : " + lfmt)
        print("")
        rows.append((m, s, l))
    ok_small = [r for r in rows if r[1]["ok"]]
    ok_small.sort(key=lambda r: (not r[2]["ok"], r[1]["dt"]))
    print("=== RANKING (PRIMARY candidate on top) ===")
    for m, s, l in ok_small:
        tag = "small+big" if l["ok"] else "small-only"
        print(m.ljust(50) + ("%.2fs" % s["dt"]).ljust(9) + tag)
    print("")
    print("DEAD/FAIL small: " + str(len([r for r in rows if not r[1]["ok"]])) + " / " + str(len(rows)))

if __name__ == "__main__":
    main()
