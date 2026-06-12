import os, json, time, logging
import requests
import psycopg2
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATABASE_URL            = os.getenv("DATABASE_URL")
GEMINI_API_KEY          = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY            = os.getenv("GROQ_API_KEY")
# 2 OpenRouter keys — TACH BIET (page 08). Key1 = LLM :free ($0). Key2 = Media (image, cap $15-20).
OPENROUTER_API_KEY       = os.getenv("OPENROUTER_API_KEY", "")        # LLM :free only — balance khong bi tru
OPENROUTER_MEDIA_API_KEY = os.getenv("OPENROUTER_MEDIA_API_KEY", "")  # Media only — KHONG dung cho text
OPENROUTER_BASE_URL      = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OR_FREE_MODEL            = os.getenv("OR_FREE_MODEL", "")             # DEPRECATED — thay bang OR_PRIORITY list. Giu cho backward-compat.
# OnMay Gemini proxy (Tier C-1, VPS-only)
ONMAY_API_KEY            = os.getenv("ONMAY_API_KEY", "")
ONMAY_BASE_URL           = os.getenv("ONMAY_BASE_URL", "")
# Cerebras :free (Tier B) — 1M tok/day, ~3000 tok/s, OpenAI-compatible
CEREBRAS_API_KEY         = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_BASE_URL        = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
# Mistral free API (Tier mid cloud — OpenAI-compatible; behind Cloudflare -> browser UA + stream:false)
MISTRAL_API_KEY          = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_BASE_URL         = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
MISTRAL_MODEL            = os.getenv("MISTRAL_MODEL", "mistral-medium-latest")   # >28K tok auto -> mistral-large-latest (256K)
BROWSER_UA               = os.getenv("BENCH_UA", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TELEGRAM_BOT_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID         = os.getenv("TELEGRAM_CHAT_ID", "")

# -- Daily usage tracking: BOTH request count AND token count (reset 00:00 UTC) --
# Schema: api_usage(service TEXT, day DATE, calls_count INT, tokens_count BIGINT, PRIMARY KEY(service, day))
def _get_usage(service: str) -> dict:
    day = datetime.now(timezone.utc).date().isoformat()
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT calls_count, tokens_count FROM api_usage WHERE service=%s AND day=%s", (service, day))
            row = cur.fetchone()
            return {"calls": row[0] if row else 0, "tokens": row[1] if row else 0}

def _inc_usage(service: str, tokens: int = 0):
    day = datetime.now(timezone.utc).date().isoformat()
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO api_usage (service, day, calls_count, tokens_count) VALUES (%s, %s, 1, %s)
                ON CONFLICT (service, day) DO UPDATE
                  SET calls_count = api_usage.calls_count + 1,
                      tokens_count = api_usage.tokens_count + EXCLUDED.tokens_count
            """, (service, day, tokens))
            conn.commit()

def _send_telegram(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")

def _call_gemini(prompt: str, system: str = "") -> str:
    # RUN#8 RE-ACTIVATED: chi gemini-2.5-flash-lite. Auth qua HEADER x-goog-api-key (KHONG ?key= tren URL).
    model = os.getenv("GEMINI_MODEL_25FL", "gemini-2.5-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    resp = requests.post(url, json=body, headers={"User-Agent": BROWSER_UA, "x-goog-api-key": GEMINI_API_KEY}, timeout=90)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

def _call_groq(prompt: str, system: str = "") -> str:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json", "User-Agent": BROWSER_UA}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                         headers=headers,
                         json={"model": os.getenv("GROQ_MODEL", "qwen/qwen3-32b"),
                               "messages": messages, "max_tokens": 4096,
                               "reasoning_format": "parsed"},   # qwen3-32b reasoning model -> tach reasoning ra field rieng
                         timeout=60)
    resp.raise_for_status()
    import re as _re
    txt = resp.json()["choices"][0]["message"]["content"] or ""
    # STRIP <think>...</think> phong khi reasoning van lot vao content (source of truth: page 08)
    return _re.sub(r"<think>.*?</think>", "", txt, flags=_re.S).strip()

def _call_ollama(prompt: str, system: str = "") -> str:
    resp = requests.post("http://localhost:11434/api/generate",
                         json={"model": "qwen2.5:7b", "prompt": prompt, "system": system, "stream": False},
                         timeout=120)
    resp.raise_for_status()
    return resp.json()["response"]

def _call_openrouter_free(prompt: str, system: str = "") -> str:
    """Tier A — OpenRouter :free PINNED PRIORITY. Thu tung model trong OR_PRIORITY theo
    thu tu (best-of-free) den khi 1 model tra ket qua hop le. KHONG dung OR_FREE_MODEL single."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set in .env")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://video-factory.internal",
        "X-Title": "AI Video Factory",
        "User-Agent": BROWSER_UA
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    last = None
    for model in OR_PRIORITY:                      # pinned priority, best-of-free truoc
        try:
            resp = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions",
                                 headers=headers,
                                 json={"model": model, "messages": messages, "max_tokens": 4096},
                                 timeout=90)
            if resp.status_code >= 400:
                last = f"{model} {resp.status_code}: {resp.text[:200]}"
                continue                            # model nay loi/het quota -> model ke trong list
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last = f"{model} ERR: {e}"
            continue
    raise RuntimeError(f"All OR_PRIORITY models failed. last={last}")

# -- Unified Router v4 (Best-of-FREE) --
import re

# Daily quotas (req + token), reset 00:00 UTC. margin ~90% de PREVENT (doi truoc khi cham).
PROVIDER_LIMITS = {
    "openrouter_free": {"rpd": 1000,        "tpd": 8000000,    "margin": 0.90},
    "cerebras_free":   {"rpd": 10**9,       "tpd": 1000000,    "margin": 0.95},  # 1M tok/day, RPS-limited
    "groq":            {"rpd": 14400,       "tpd": 1000000,    "margin": 0.90},
    "gemini":          {"rpd": 1500,        "tpd": 100000000,  "margin": 0.90},  # run#8 RE-ADDED: gemini-2.5-flash-lite, ~1500 RPD
    "onmay":           {"rpd": 200,         "tpd": 2000000,    "margin": 0.90},
    "ollama":          {"rpd": 10**9,       "tpd": 10**12,     "margin": 1.00},  # local unlimited (ollama DROPPED khoi chain)
    "mistral":         {"rpd": 1000000, "tpd": 1000000000, "margin": 0.90},  # Mistral free 1 req/s
}

# OpenRouter :free PINNED PRIORITY (best-of-free). kimi-k2.6:free DA LOAI. owl-alpha KHONG co :free suffix.
OR_PRIORITY = [
    "nvidia/nemotron-3-nano-30b-a3b:free",                # 256K - PRIMARY
    "openai/gpt-oss-20b:free",                            # 131K - backup
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", # 256K - REASONING
    "qwen/qwen3-next-80b-a3b-instruct:free",              # 262K - tool-capable
    "google/gemma-4-31b-it:free",                         # 262K
    "z-ai/glm-4.5-air:free",                              # 128K
    "meta-llama/llama-3.3-70b-instruct:free",             # 131K
    "qwen/qwen3-coder:free",                              # 262K (CODE)
    "google/gemma-4-26b-a4b-it:free",                     # 262K
    "poolside/laguna-m.1:free",                           # 256K
    "nvidia/nemotron-nano-9b-v2:free",                    # 128K
    "nvidia/nemotron-nano-12b-v2-vl:free",                # ~131K
    "liquid/lfm-2.5-1.2b-thinking:free",                  # 33K - utility vat only
    "liquid/lfm-2.5-1.2b-instruct:free",                  # 33K - utility vat only
    # 2x 120B DROPPED (run#7 re-test khong on dinh). owl-alpha removed (NO :free).
]
# Cerebras: CHI gpt-oss-120b (qwen-3-235b-a22b-instruct = 404; llama bo). Free ctx cap ~64K -> >64K fallthrough.
CEREBRAS_MODELS = {"big": "gpt-oss-120b", "fast": "gpt-oss-120b"}

# Free fallback chains v8 (page 08): Gemini 2.5 FL RE-ADDED; OnMay LUON CUOI; Ollama DROPPED; Cerebras ctx cap 64K.
CHAIN_BRAIN     = ["openrouter_free", "cerebras_free", "gemini", "mistral", "onmay"]   # Groq loai (big 413)
CHAIN_CREATIVE  = ["cerebras_free", "openrouter_free", "gemini", "groq", "mistral", "onmay"]
CHAIN_REASONING = ["openrouter_free", "cerebras_free", "gemini", "mistral", "onmay"]
CHAIN_UTILITY   = ["groq", "gemini", "cerebras_free", "mistral", "onmay"]
CHAIN_CODE      = ["openrouter_free", "gemini", "mistral", "cerebras_free", "onmay"]

# 15 task key — dong bo key name voi page 08
TASK_CHAIN = {
    "S1_trend_score":      CHAIN_REASONING,
    "S2_story_outline":    CHAIN_CREATIVE,
    "S2_quality_check":    CHAIN_REASONING,
    "S3_script_gen":       CHAIN_CREATIVE,
    "S3_translation":      CHAIN_UTILITY,
    "S4_voiceover_script": CHAIN_CREATIVE,
    "S5_content_safety":   CHAIN_UTILITY,
    "S6_affiliate_inject": CHAIN_REASONING,
    "S8_publish_meta":     CHAIN_UTILITY,
    "S9_dreaming_loop":    CHAIN_REASONING,
    "S9_rule_proposal":    CHAIN_REASONING,
    "SETUP_ORCHESTRATE":   CHAIN_REASONING,
}
# Embedding tasks — local MiniLM ONLY, never a chat model
EMBED_TASKS = {"S1_dedup_embed", "S6_affiliate_embed", "S9_kb_gap_embed"}

def _est_tokens(*texts) -> int:
    return sum(len(t or "") for t in texts) // 4   # ~4 chars/token rough estimate

# -- DETECT: garbage output guard (goi TRUOC khi return) --
def is_garbage_output(text: str, expect_json: bool = False) -> bool:
    if not text or not text.strip():
        return True
    if len(set(text)) <= 3 and len(text) > 20:                 # repeated single chars
        return True
    if re.search(r"(.)\1{15,}", text):                          # long char runs
        return True
    scripts = sum(bool(re.search(p, text)) for p in
                  [r"[\u4e00-\u9fff]", r"[\u3040-\u30ff]", r"[\uac00-\ud7af]",
                   r"[\u0600-\u06ff]", r"[a-zA-Z]"])
    if scripts >= 4:                                            # mixed-script gibberish
        return True
    if expect_json:
        try:
            json.loads(text)
        except Exception:
            return True
    return False

def _call_onmay(prompt: str, system: str = "") -> str:
    if not ONMAY_API_KEY or not ONMAY_BASE_URL:
        raise RuntimeError("ONMAY_API_KEY / ONMAY_BASE_URL not set")
    headers = {"Authorization": f"Bearer {ONMAY_API_KEY}", "Content-Type": "application/json", "User-Agent": BROWSER_UA}
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    resp = requests.post(f"{ONMAY_BASE_URL}/chat/completions", headers=headers,
                         json={"model": "gemini-2.5-flash", "messages": messages, "max_tokens": 4096, "stream": False}, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def _call_cerebras(prompt: str, system: str = "") -> str:
    """Tier B — Cerebras :free. Chi dung gpt-oss-120b (qwen-3-235b 404). Free ctx cap ~64K -> >64K fallthrough."""
    if not CEREBRAS_API_KEY:
        raise RuntimeError("CEREBRAS_API_KEY not set")
    headers = {"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json", "User-Agent": BROWSER_UA}
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    model = CEREBRAS_MODELS["big"] if _est_tokens(prompt, system) > 40000 else CEREBRAS_MODELS["fast"]
    resp = requests.post(f"{CEREBRAS_BASE_URL}/chat/completions", headers=headers,
                         json={"model": model, "messages": messages, "max_tokens": 4096}, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def _call_mistral(prompt: str, system: str = "") -> str:
    """Tier mid cloud fallback - Mistral free API. medium 32K / large 256K (auto >28K). Browser UA + stream:false."""
    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY not set")
    model = "mistral-large-latest" if _est_tokens(prompt, system) > 28000 else MISTRAL_MODEL
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json",
               "User-Agent": BROWSER_UA}
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    resp = requests.post(f"{MISTRAL_BASE_URL}/chat/completions", headers=headers,
                         json={"model": model, "messages": messages, "max_tokens": 4096, "stream": False}, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# Chat callers registry (embedding KHONG nam o day)
CALLERS = {
    "openrouter_free": _call_openrouter_free,
    "cerebras_free":   _call_cerebras,
    "gemini":          _call_gemini,
    "groq":            _call_groq,
    "onmay":           _call_onmay,
    "mistral":         _call_mistral,
}

def embed(texts, task_type: str = "S1_dedup_embed"):
    """Embedding branch — local sentence-transformers MiniLM ONLY."""
    from sentence_transformers import SentenceTransformer
    global _EMBED_MODEL
    try:
        _EMBED_MODEL
    except NameError:
        _EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _EMBED_MODEL.encode(texts).tolist()

# -- PREVENT: con quota (req + token, duoi margin) moi dung provider nay --
def _has_quota(provider: str, est_tokens: int) -> bool:
    lim = PROVIDER_LIMITS[provider]
    u = _get_usage(provider)
    if u["calls"] + 1 > lim["rpd"] * lim["margin"]:
        return False
    if u["tokens"] + est_tokens > lim["tpd"] * lim["margin"]:
        return False
    return True

def _is_retryable(err: Exception) -> bool:
    s = str(err).lower()
    return any(k in s for k in ["429", "rate limit", "quota", "upstream", "enginecore",
                                "timeout", "timed out", "503", "502", "overloaded"])

def llm_call(prompt: str, task_type: str = "SETUP_ORCHESTRATE", system: str = "",
             expect_json: bool = False) -> dict:
    """Unified router: PREVENT -> route free chain -> DETECT -> AWAKE (switch+retry) -> exhaust = ABORT + Telegram."""
    if task_type in EMBED_TASKS:
        raise ValueError(f"{task_type} is an embedding task — call embed(), never a chat model")

    chain = TASK_CHAIN.get(task_type, CHAIN_REASONING)
    est = _est_tokens(prompt, system)
    model_name = {"openrouter_free": "OR_PRIORITY[best-avail]", "cerebras_free": "cerebras:auto(big/fast)",
                  "gemini": "gemini-2.5-flash-lite",
                  "groq": "qwen/qwen3-32b",
                  "onmay": "gemini-2.5-flash",
                  "mistral": "mistral-medium/large-latest"}
    last_err = None

    for provider in chain:
        if provider != "ollama" and not _has_quota(provider, est):
            logger.info(f"[Router] {provider} near/at daily cap — pre-switch")
            continue

        caller = CALLERS[provider]
        for attempt in range(3):                          # AWAKE: retry 3 lan voi backoff
            try:
                text = caller(prompt, system)
                if is_garbage_output(text, expect_json=expect_json):
                    logger.warning(f"[Router] {provider} garbage output — next provider")
                    last_err = RuntimeError(f"{provider} garbage output")
                    break
                _inc_usage(provider, _est_tokens(prompt, system, text))
                return {"text": text, "model": model_name[provider], "provider": provider}
            except Exception as e:
                last_err = e
                if _is_retryable(e) and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(f"[Router] {provider} retryable ({e}); wait {wait}s")
                    time.sleep(wait)
                    continue
                logger.warning(f"[Router] {provider} failed: {e}")
                break

    msg = f"LLM ABORT — task={task_type} — tat ca provider free deu fail. last_err={last_err}"
    logger.error(msg)
    _send_telegram(msg)
    raise RuntimeError(msg)

if __name__ == "__main__":
    result = llm_call("Say hello in one word", task_type="SETUP_ORCHESTRATE")
    print(json.dumps(result, ensure_ascii=False, indent=2))
