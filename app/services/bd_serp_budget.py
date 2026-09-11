# app/services/bd_serp_budget.py
# Budget meters for BrightData SERP + Serper API (07/08/2026).
#
# BrightData SERP: 5,000 free requests/month (recurring, auto-reset monthly).
# Serper API: 2,500 free queries (one-time, 6-month validity from first use).
#
# Pattern follows serp_budget.py: persistent JSON counter, thread-safe,
# Telegram alert on exhaustion, graceful degradation to fallback.

import os, json, logging, threading, calendar
from datetime import date

logger = logging.getLogger(__name__)

# --- BrightData ---
BD_CAP = int(os.getenv("BRIGHTDATA_MONTHLY_CAP", "5000"))
BD_RESERVE = int(os.getenv("BRIGHTDATA_RESERVE", "200"))
BD_STATE = os.getenv("BRIGHTDATA_BUDGET_PATH", "/root/video_factory/db/brightdata_budget.json")

# --- Serper ---
SERPER_CAP = int(os.getenv("SERPER_TOTAL_CAP", "2500"))
SERPER_VALIDITY_MO = int(os.getenv("SERPER_VALIDITY_MONTHS", "6"))
SERPER_STATE = os.getenv("SERPER_BUDGET_PATH", "/root/video_factory/db/serper_budget.json")

_LOCK = threading.Lock()


def _month():
    return date.today().strftime("%Y-%m")


def _tg(msg):
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        send_telegram_broadcast(msg)
    except Exception as e:
        logger.warning("[bd-serp] telegram fail: %s", e)


def _add_months(d, months):
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


# ===== BrightData =====

def _bd_load():
    mo = _month()
    try:
        with open(BD_STATE) as f:
            d = json.load(f)
        if d.get("month") != mo:
            return {"month": mo, "used": 0, "exhausted": False}
        return {"month": mo,
                "used": int(d.get("used", 0)),
                "exhausted": bool(d.get("exhausted", False))}
    except Exception:
        return {"month": mo, "used": 0, "exhausted": False}


def _bd_save(s):
    try:
        os.makedirs(os.path.dirname(BD_STATE), exist_ok=True)
        tmp = BD_STATE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(s, f)
        os.replace(tmp, BD_STATE)
    except Exception as e:
        logger.warning("[bd-serp] BD save fail: %s", e)


def bd_status():
    s = _bd_load()
    s["cap"] = BD_CAP
    s["remaining"] = max(0, BD_CAP - BD_RESERVE - s["used"])
    return s


def bd_can_spend(n=1):
    s = _bd_load()
    if s.get("exhausted"):
        return False
    return (s["used"] + n) <= (BD_CAP - BD_RESERVE)


def bd_record(n=1):
    with _LOCK:
        s = _bd_load()
        s["used"] += n
        if s["used"] >= (BD_CAP - BD_RESERVE):
            s["exhausted"] = True
            _bd_save(s)
            _tg("🔻 BrightData SERP het quota thang %s (%d/%d) — Serper fallback." % (s["month"], s["used"], BD_CAP))
        else:
            _bd_save(s)
        return s


def bd_mark_exhausted(reason="soft-cap"):
    with _LOCK:
        s = _bd_load()
        already = s.get("exhausted")
        s["exhausted"] = True
        _bd_save(s)
    if not already:
        _tg("🔻 BrightData SERP het quota (%s) — Serper fallback." % reason)


# ===== Serper =====

def _ser_load():
    try:
        with open(SERPER_STATE) as f:
            d = json.load(f)
        return {"total_cap": int(d.get("total_cap", SERPER_CAP)),
                "used": int(d.get("used", 0)),
                "first_used": d.get("first_used"),
                "valid_until": d.get("valid_until"),
                "exhausted": bool(d.get("exhausted", False))}
    except Exception:
        return {"total_cap": SERPER_CAP, "used": 0,
                "first_used": None, "valid_until": None, "exhausted": False}


def _ser_save(s):
    try:
        os.makedirs(os.path.dirname(SERPER_STATE), exist_ok=True)
        tmp = SERPER_STATE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(s, f)
        os.replace(tmp, SERPER_STATE)
    except Exception as e:
        logger.warning("[bd-serp] Serper save fail: %s", e)


def serper_status():
    s = _ser_load()
    s["remaining"] = max(0, s["total_cap"] - s["used"])
    s["expired"] = False
    if s.get("valid_until"):
        try:
            if date.today() > date.fromisoformat(s["valid_until"]):
                s["expired"] = True
        except Exception:
            pass
    return s


def serper_can_spend(n=1):
    s = _ser_load()
    if s.get("exhausted"):
        return False
    if s.get("valid_until"):
        try:
            if date.today() > date.fromisoformat(s["valid_until"]):
                return False
        except Exception:
            pass
    return (s["used"] + n) <= s["total_cap"]


def serper_record(n=1):
    with _LOCK:
        s = _ser_load()
        if not s["first_used"]:
            s["first_used"] = date.today().isoformat()
            s["valid_until"] = _add_months(date.today(), SERPER_VALIDITY_MO).isoformat()
        s["used"] += n
        if s["used"] >= s["total_cap"]:
            s["exhausted"] = True
            _ser_save(s)
            _tg("🔻 Serper het 2,500 free queries (%d/%d) — khong con fallback search." % (s["used"], s["total_cap"]))
        else:
            _ser_save(s)
        return s


# ===== Combined read for API =====

def read_budget():
    return {"brightdata": bd_status(), "serper": serper_status()}
