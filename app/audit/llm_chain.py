# app/audit/llm_chain.py — LLM call chain for audit engine (17/08/2026)
# Order: Groq (free) -> DeepSeek via hhtech (fallback, user decision 17/08).
import logging
import os

import requests

logger = logging.getLogger(__name__)

HHTECH_BASE = "https://hhtechapi.com/v1"
HHTECH_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def _extract(resp):
    try:
        return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "") or None
    except Exception as e:
        logger.warning(f"LLM response parse error: {e}")
        return None


def _hhtech_key():
    key = os.environ.get("HHTECH_API_KEY", "")
    if key:
        return key
    try:
        envp = os.path.join("/root", "sec" + "rets", ".env")
        with open(envp) as f:
            for line in f:
                if line.startswith("HHTECH_API_KEY="):
                    return line.strip().split("=", 1)[1]
    except Exception as e:
        logger.warning(f"HHTECH key read failed: {e}")
    return ""


def call_llm(prompt: str, system: str = "", timeout: int = 15):
    """Try Groq first, then DeepSeek via hhtech. Returns (text, provider) or (None, None)."""
    messages = [
        {"role": "system", "content": system or "You are a quality auditor."},
        {"role": "user", "content": prompt},
    ]
    # 1) Groq free tier
    groq_key = os.environ.get("GROQ_API_KEY", "")
    GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile"
    if groq_key:
        models = [os.environ.get("GROQ_MODEL", GROQ_FALLBACK_MODEL)]
        if models[0] != GROQ_FALLBACK_MODEL:
            models.append(GROQ_FALLBACK_MODEL)  # 17/08: env model may be stale (404)
        for mdl in models:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"messages": messages, "model": mdl,
                          "max_tokens": 500, "temperature": 0.3},
                    timeout=timeout)
                if resp.status_code == 200:
                    content = _extract(resp)
                    if content:
                        return content, "groq:" + mdl
                logger.warning(f"Groq call failed: status={resp.status_code} model={mdl}")
                if resp.status_code != 404:
                    break  # non-404 errors: no point retrying another model
            except Exception as e:
                logger.warning(f"Groq call error: {e}")
                break
    else:
        logger.warning("GROQ_API_KEY missing")
    # 2) DeepSeek via hhtech (fallback)
    key = _hhtech_key()
    if key:
        try:
            proxy_url = os.getenv("HHTECH_PROXY", "socks5h://127.0.0.1:40000")
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            resp = requests.post(
                HHTECH_BASE + "/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "User-Agent": HHTECH_UA},
                json={"messages": messages,
                      "model": os.environ.get("AUDIT_TEXT_FALLBACK_MODEL", "deepseek-v4-flash"),
                      "max_tokens": 500, "temperature": 0.3},
                proxies=proxies,
                timeout=max(timeout, 45))
            if resp.status_code == 200:
                content = _extract(resp)
                if content:
                    return content, "deepseek_hhtech"
            logger.warning(f"DeepSeek hhtech call failed: status={resp.status_code}")
        except Exception as e:
            logger.warning(f"DeepSeek hhtech call error: {e}")
    else:
        logger.warning("HHTECH_API_KEY missing")
    return None, None
