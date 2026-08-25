# app/services/serp_budget.py - Centralized SerpApi monthly budget meter (21/06).
# Free plan = 250 searches/month; SerpApi auto-errors when exhausted (no charge,
# no credit). Philosophy (user 21/06): USE the full quota for search quality,
# then degrade gracefully to free layers. Every SerpApi call across the codebase
# (scorer TIMESERIES, related RISING, story site-search) routes through
# serp_get() so a single meter protects the ceiling AND drives the fallback.
import os
import json
import logging
import threading
from datetime import date

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search"

# Env-tunable knobs (documented + overridable; not hard-coded business params).
MONTHLY_CAP = int(os.getenv("SERPAPI_MONTHLY_CAP", "250"))
RESERVE = int(os.getenv("SERPAPI_RESERVE", "15"))      # buffer for ad-hoc/manual
ALERT_PCT = int(os.getenv("SERPAPI_ALERT_PCT", "80"))   # Telegram warn threshold

# Persistent counter (survives reboot; /tmp would reset mid-month). Safe-zone db/.
STATE_PATH = os.getenv("SERPAPI_BUDGET_PATH", "/root/video_factory/db/serpapi_budget.json")

_LOCK = threading.Lock()


def _soft_cap():
    return max(0, MONTHLY_CAP - RESERVE)


def _month_key():
    return date.today().strftime("%Y-%m")


def _blank(month):
    return {"month": month, "used": 0, "alert80": False, "exhausted": False}


def _load():
    month = _month_key()
    try:
        with open(STATE_PATH) as f:
            data = json.load(f)
        if data.get("month") != month:
            return _blank(month)  # new month -> auto-reset
        return {"month": month,
                "used": int(data.get("used", 0)),
                "alert80": bool(data.get("alert80", False)),
                "exhausted": bool(data.get("exhausted", False))}
    except Exception:
        return _blank(month)


def _save(state):
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, STATE_PATH)
    except Exception as e:
        logger.warning("[serp-budget] save failed: %s", e)


def _telegram(msg):
    try:
        from app.llm_router import _send_telegram
        _send_telegram(msg)
    except Exception as e:
        logger.warning("[serp-budget] telegram failed: %s", e)


def status():
    """Read-only snapshot (for logging / a future /v1/serp-budget endpoint)."""
    s = _load()
    s["soft_cap"] = _soft_cap()
    s["monthly_cap"] = MONTHLY_CAP
    s["remaining"] = max(0, _soft_cap() - s["used"])
    return s


def can_spend(n=1):
    """True if we may make n more SerpApi calls this month (under soft-cap)."""
    s = _load()
    if s.get("exhausted"):
        return False
    return (s["used"] + n) <= _soft_cap()


def _looks_exhausted(resp):
    """SerpApi signals exhaustion via 429 or an error string in the JSON body."""
    if resp is None:
        return False
    if resp.status_code == 429:
        return True
    try:
        err = str((resp.json() or {}).get("error", "")).lower()
    except Exception:
        return False
    return any(k in err for k in ("run out of searches", "ran out of searches",
                                 "exceeded your", "account limit",
                                 "no searches left", "have run out"))


def _record(n=1):
    """Increment usage; fire the 80% Telegram alert once."""
    with _LOCK:
        s = _load()
        s["used"] += n
        soft = _soft_cap()
        threshold = MONTHLY_CAP * ALERT_PCT / 100.0
        if (not s["alert80"]) and ALERT_PCT > 0 and s["used"] >= threshold:
            s["alert80"] = True
            _save(s)
            _telegram("\u26a0\ufe0f SerpApi %d/%d (%.0f%%) thang %s \u2014 con ~%d truoc soft-cap %d, sap ve free-only."
                      % (s["used"], MONTHLY_CAP,
                         100.0 * s["used"] / max(1, MONTHLY_CAP),
                         s["month"], max(0, soft - s["used"]), soft))
        else:
            _save(s)
        return s


def mark_exhausted(reason="soft-cap"):
    """Flip the month to free-only; alert once."""
    with _LOCK:
        s = _load()
        already = s.get("exhausted")
        s["exhausted"] = True
        _save(s)
    if not already:
        _telegram("\U0001F53B SerpApi het quota thang %s (%s) \u2014 chuyen sang FREE-ONLY "
                  "(RSS + LLM). Tu khoi phuc dau thang sau."
                  % (s["month"], reason))


def serp_get(params, timeout=20.0):
    """Guarded SerpApi GET. Returns an httpx.Response on a billed 200, or None
    when budget is spent / key missing / call failed -> caller MUST fall back to
    the free layers (localized Google News RSS, LLM estimate)."""
    key = os.getenv("SERPAPI_API_KEY")
    if not key:
        return None
    if not can_spend(1):
        mark_exhausted("soft-cap reached")
        logger.info("[serp-budget] soft-cap reached -> skip serpapi, free fallback")
        return None
    params = dict(params or {})
    params.setdefault("api_key", key)
    try:
        import httpx
        # 26/07 fix: VPS has no working IPv6 route to the outside world, but
        # serpapi.com is dual-stack (A+AAAA). httpx was hanging on the dead
        # IPv6 leg until the read-timeout fired every time. Force IPv4 by
        # binding the client to a v4 wildcard local address via an explicit
        # Client (the module-level httpx.get() shortcut does not accept a
        # transport kwarg on this httpx version).
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        with httpx.Client(transport=transport, timeout=timeout) as client:
            resp = client.get(SERPAPI_ENDPOINT, params=params)
    except Exception as e:
        logger.warning("[serp-budget] http error: %s", e)
        return None
    if _looks_exhausted(resp):
        mark_exhausted("serpapi reported quota exhausted")
        return None
    if resp.status_code == 200:
        _record(1)  # a successful search is what SerpApi bills against the 250
    return resp
