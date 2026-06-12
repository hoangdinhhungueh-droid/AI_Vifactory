#!/usr/bin/env python3
# scripts/llm_endpoint_benchmark.py
# LIVE benchmark: OnMay, Gemini FREE Flash/Flash-Lite (2.5-FL / 3 / 3.1 — auth header x-goog-api-key), Groq, Ollama (local), Mistral.
# Detect: dead / silent-fail / hang. Measure latency + tok/s + enhance quality.
# Test small-ctx AND big-ctx (~reproduce >50K failure). FAIL provider -> drop from router.
import os, time, json, statistics
import urllib.request, urllib.error

TIMEOUT_S       = int(os.getenv("BENCH_TIMEOUT_S", "90"))           # hang > timeout => FAIL
LARGE_CTX_CHARS = int(os.getenv("BENCH_LARGE_CHARS", "120000"))     # ~30K tok -> reproduce Groq 413 / OnMay hang
N_RUNS          = int(os.getenv("BENCH_RUNS", "2"))                 # runs/case (median)
MAX_RETRIES     = int(os.getenv("BENCH_MAX_RETRIES", "3"))          # retry khi 429 (free-tier RPM/quota)
RETRY_BASE_S    = float(os.getenv("BENCH_RETRY_BASE_S", "8"))       # backoff base (s): free Gemini/Gemma RPM rat thap
SLEEP_BETWEEN_S = float(os.getenv("BENCH_SLEEP_S", "2"))            # nghi giua cac call -> tranh burst RPM
BROWSER_UA      = os.getenv("BENCH_UA", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")  # FIX Cloudflare 1010

SMALL_PROMPT = (
    "Enhance this narrative paragraph: improve flow and vividness, keep meaning, "
    "return ONLY the enhanced text.\n\n"
    "The old man walked to the sea every morning. He had not caught a fish in eighty four days. "
    "The boy who loved him was told by his parents to fish on a luckier boat."
)

def _big_text():
    base = ("Chapter draft line: the protagonist faced another setback as the storm rolled in "
            "over the harbor, testing resolve and reshaping the plan for tomorrow. ")
    return base * ((LARGE_CTX_CHARS // len(base)) + 1)

BIG_PROMPT = ("Summarize then enhance the following long draft into a tighter, vivid version. "
              "Return ONLY the enhanced summary (<= 400 words).\n\n" + _big_text())

def _post(url, payload, headers, timeout):
    data = json.dumps(payload).encode()
    headers = {"User-Agent": BROWSER_UA, **headers}   # FIX: Cloudflare error 1010 blocks default Python-urllib UA (Groq/OnMay are behind CF)
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode(), time.time() - t0

def _loads(body, status):
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        snippet = (body or "")[:160].replace(chr(10), " ")
        raise RuntimeError("non-JSON status=" + str(status) + " body[:160]=" + repr(snippet))  # diagnose OnMay JSONDecodeError

def call_openai_compatible(base, key, model, prompt, timeout):
    url = base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.7, "max_tokens": 700, "stream": False}  # FIX OnMay: returns SSE 'data: ...chunk' if stream not false
    status, body, dt = _post(url, payload, headers, timeout)
    j = _loads(body, status)
    text = (j.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    return text, dt, status, j.get("usage", {}).get("completion_tokens")

def call_gemini_aistudio(key, model, prompt, timeout):
    # AUTH MOI (theo quickstart ai.google.dev): API key qua HEADER x-goog-api-key, KHONG con ?key= tren URL
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 0.7, "maxOutputTokens": 700}}
    status, body, dt = _post(url, payload, headers, timeout)
    j = _loads(body, status)
    cands = j.get("candidates") or []
    text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", [])) if cands else ""
    return text, dt, status, j.get("usageMetadata", {}).get("candidatesTokenCount")

def call_ollama(base, model, prompt, timeout):
    url = base.rstrip("/") + "/api/chat"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "stream": False, "keep_alive": 0,  # on-demand: unload model + nha RAM ngay sau moi call
               "options": {"temperature": 0.7, "num_predict": 700}}
    status, body, dt = _post(url, payload, {"Content-Type": "application/json"}, timeout)
    j = _loads(body, status)
    return j.get("message", {}).get("content", "") or "", dt, status, j.get("eval_count")

PROVIDERS = [
#    {"name": "onmay_gemini",    "kind": "openai", "base": os.getenv("ONMAY_BASE_URL", ""),
 #    "key": os.getenv("ONMAY_API_KEY", ""), "model": "gemini-2.5-flash"},
    # --- RE-TEST Gemini FREE Flash/Flash-Lite (auth qua HEADER x-goog-api-key theo quickstart moi, KHONG dung ?key=) ---
    # CHI test model con FREE: 2.5 Flash-Lite / 3 Flash / 3.1 Flash. TUYET DOI khong tro *-pro (paid-only tu 4/2026 -> 429/403).
    {"name": "gemini_2.5_flash_lite", "kind": "gemini", "key": os.getenv("GEMINI_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL_25FL", "gemini-2.5-flash-lite")},   # free ~1500 RPD, TPM ~1M (nhe/re nhat dong 2.5)
    {"name": "gemini_2.5_flash", "kind": "gemini", "key": os.getenv("GEMINI_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL_3F", "gemini-2.5-flash")},   # free (quota giam, Google khong public so) - Flash mac dinh moi
    {"name": "gemini_3.1_flash", "kind": "gemini", "key": os.getenv("GEMINI_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL_31F", "gemini-3.1-flash")},   # free; muon ban RAT generous (~500-1500 RPD) thi dat = gemini-3.1-flash-lite (preview tat 9/7/2026 -> dung ban GA)  
    {"name": "groq",           "kind": "openai", "base": "https://api.groq.com/openai/v1",
     "key": os.getenv("GROQ_API_KEY", ""), "model": os.getenv("GROQ_MODEL", "qwen/qwen3-32b")},  # qwen3-32b: 131K ctx (llama-3.3-70b chỉ ~free TPM nhỏ -> 413 ở big)
    {"name": "ollama_local",   "kind": "ollama", "base": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
     "key": "", "model": os.getenv("OLLAMA_MODEL", "batiai/gemma4-e2b:q4")},  # qwen2.5:7b + gemma3:4b DROPPED. Gemma 4 E2B Q4 ~3.4GB text-only (official gemma4:e2b=7.2GB KHONG vua 8GB); keep_alive=0 on-demand
    {"name": "mistral",       "kind": "openai", "base": "https://api.mistral.ai/v1",
     "key": os.getenv("MISTRAL_API_KEY", ""), "model": os.getenv("MISTRAL_MODEL", "mistral-medium-latest")},  # Mistral free API (Experiment): OpenAI-compatible; 1 req/s free-tier; large=256K ctx
]

def run_one(p, prompt):
    for attempt in range(MAX_RETRIES + 1):   # retry khi 429 (free-tier RPM/quota)
        try:
            if p["kind"] == "openai":
                text, dt, status, out_tok = call_openai_compatible(p["base"], p["key"], p["model"], prompt, TIMEOUT_S)
            elif p["kind"] == "gemini":
                text, dt, status, out_tok = call_gemini_aistudio(p["key"], p["model"], prompt, TIMEOUT_S)
            else:
                text, dt, status, out_tok = call_ollama(p["base"], p["model"], prompt, TIMEOUT_S)
            text = (text or "").strip()
            if not text or len(text) < 20:   # silent-fail: 200 but empty/short
                return {"ok": False, "reason": "empty_or_short status=" + str(status)}
            tps = (out_tok / dt) if (out_tok and dt) else None
            return {"ok": True, "dt": dt, "tps": tps, "chars": len(text), "preview": text[:100].replace(chr(10), " ")}
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode(errors='ignore')
            if e.code == 429 and attempt < MAX_RETRIES:
                wait = RETRY_BASE_S * (2 ** attempt)   # 429 = quota/RPM free-tier -> backoff roi thu lai
                print("      [429] " + p["name"] + " quota/RPM -> doi " + str(round(wait, 1)) + "s (thu lai " + str(attempt + 1) + "/" + str(MAX_RETRIES) + ")")
                time.sleep(wait); continue
            return {"ok": False, "reason": "HTTP " + str(e.code) + ": " + body[:100]}
        except Exception as e:
            return {"ok": False, "reason": type(e).__name__ + ": " + str(e)[:100]}

def bench_case(p, prompt):
    runs = []
    for _ in range(N_RUNS):
        runs.append(run_one(p, prompt))
        time.sleep(SLEEP_BETWEEN_S)   # nghi giua call -> tranh burst RPM free-tier (Gemini/Gemma de 429)
    oks = [r for r in runs if r["ok"]]
    if not oks:
        return {"ok": False, "reason": runs[-1].get("reason", "fail")}
    med_dt = statistics.median([r["dt"] for r in oks])
    tps_vals = [r["tps"] for r in oks if r.get("tps")]
    return {"ok": True, "dt": round(med_dt, 2),
            "tps": round(statistics.median(tps_vals), 1) if tps_vals else None,
            "preview": oks[-1]["preview"]}

def verdict(s, l):
    if s["ok"] and l["ok"]:        return "KEEP (small+big OK)"
    if s["ok"] and not l["ok"]:    return "KEEP small-ctx only -> DEMOTE big"
    return "DROP (small fail)"

def fmt(x):
    if x["ok"]:
        return "OK " + str(x["dt"]) + "s " + str(x.get("tps")) + "tok/s"
    return "FAIL " + str(x.get("reason", ""))

def main():
    print("== LLM 4-POINT LIVE BENCHMARK == timeout=" + str(TIMEOUT_S) + "s runs=" + str(N_RUNS) + " big=" + str(LARGE_CTX_CHARS) + "c\n")
    rows = []
    for p in PROVIDERS:
        if p["kind"] != "ollama" and not p.get("key"):
            print("[SKIP] " + p["name"] + ": missing API key"); rows.append((p["name"], "NO_KEY", "NO_KEY", "DROP (no key)")); continue
        print("-- " + p["name"] + " (" + p["model"] + ") --")
        s, l = bench_case(p, SMALL_PROMPT), bench_case(p, BIG_PROMPT)
        v = verdict(s, l)
        print("   small : " + fmt(s) + "\n   big   : " + fmt(l) + "\n   => " + v + "\n")
        rows.append((p["name"], fmt(s), fmt(l), v))
    print("=== SUMMARY ===")
    for r in rows:
        print(r[0].ljust(16), r[1].ljust(30), r[2].ljust(30), r[3])

if __name__ == "__main__":
    main()
