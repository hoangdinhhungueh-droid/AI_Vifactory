# app/services/trend_signals.py — Trend signal provider for S1 scoring (v4, 26/07).
# Order: SerpApi google_trends (TIMESERIES) -> neutral 0.5.
# Denylisted niches return 0.0 so advertiser-unsafe topics never rank.
# v4 (26/07): pytrends REMOVED per decision (low quality / VPS IP often 429’d).
#   Root cause of "SerpApi never used" was fixed instead: a stuck serp_budget
#   exhausted-flag + a broken VPS IPv6 route to serpapi.com (httpx now forced
#   to IPv4 in serp_budget.serp_get). SerpApi is now the sole real trend
#   source; no fallback trend provider before neutral.
# v3 (21/06): SerpApi now routed through serp_budget.serp_get -> a single monthly
#   250 meter governs ALL SerpApi calls. When budget is spent the call returns
#   None and we fall back to neutral 0.5 (no error spam).
# v2 fixes (retained):
#   - defensive .env load (app does NOT dotenv-load; pm2 --update-env convention)
#   - file cache w/ TTL to cut repeat SerpApi calls (still saves budget)
#   - explicit warning when SERPAPI_API_KEY missing from process env
#   - trend_meta() returns the source so the caller can refuse silent NEUTRAL passes
import os
import json
import time
import logging

# app/main.py does NOT call load_dotenv (pm2 --update-env convention). Load here
# so SERPAPI_API_KEY is present even if the process env was not refreshed.
try:
    from dotenv import load_dotenv
    load_dotenv("/root/secrets/.env")
except Exception:
    pass

logger = logging.getLogger(__name__)

NEUTRAL = 0.5
# Kept for backward-compat: trend_discovery imports SERPAPI_ENDPOINT from here.
# Live SerpApi calls now go through serp_budget.serp_get (shares the 250 meter).
SERPAPI_ENDPOINT = "https://serpapi.com/search"

# Cache so the 6h cron does not burn the 250/month SerpApi budget.
# 10 niches x 4 markets = 40 combos; TTL 6 days => ~40 calls/week (~170/month < 250).
CACHE_PATH = os.getenv("TREND_CACHE_PATH", "/tmp/vf/trend_cache.json")
CACHE_TTL = float(os.getenv("TREND_CACHE_TTL_H", "144")) * 3600.0  # default 6 days

DENYLIST = {
    "nsfw", "porn", "pornography", "nude", "nudity", "onlyfans", "escort",
    "gambling", "casino", "betting", "weapons", "gun-sales", "drugs",
    "self-harm", "suicide-methods", "terrorism", "hate-speech",
}

GEO_MAP = {
    "US": "US", "CA": "CA", "GB": "GB", "AU": "AU", "NZ": "NZ",
    "JP": "JP", "KR": "KR", "IN": "IN", "VN": "VN", "EU": "",
}


def has_serpapi_key():
    return bool(os.getenv("SERPAPI_API_KEY"))


def _is_denied(niche):
    n = (niche or "").strip().lower()
    if n in DENYLIST:
        return True
    return any(bad in n for bad in DENYLIST)


def _cache_get(key):
    try:
        with open(CACHE_PATH) as f:
            data = json.load(f)
        entry = data.get(key)
        if entry and (time.time() - float(entry.get("t", 0))) < CACHE_TTL:
            return entry.get("v")
    except Exception:
        pass
    return None


def _cache_put(key, val):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        try:
            with open(CACHE_PATH) as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[key] = {"t": time.time(), "v": val}
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, CACHE_PATH)
    except Exception:
        pass


def _normalize_series(series):
    vals = [float(x) for x in series if x is not None]
    if not vals:
        return NEUTRAL
    avg = sum(vals) / len(vals)
    velocity = vals[-1] - vals[0]
    score = (avg / 100.0) * 0.7 + max(min(velocity / 50.0, 1.0), -1.0) * 0.3
    return float(max(0.0, min(score, 1.0)))


def _serpapi_trend(niche, market, timeout=20.0):
    # Routed through serp_budget.serp_get -> shares the monthly 250 meter.
    # Returns None when the key is missing OR the budget is spent, so trend_meta
    # cleanly falls back to neutral 0.5.
    from app.services import serp_budget
    params = {
        "engine": "google_trends",
        "q": niche.replace("-", " "),
        "data_type": "TIMESERIES",
        "date": "now 7-d",
        "geo": GEO_MAP.get(market, ""),
    }
    r = serp_budget.serp_get(params, timeout=timeout)
    if r is None:
        return None
    try:
        if r.status_code != 200:
            logger.warning("[trend] serpapi http %s for %s/%s", r.status_code, niche, market)
            return None
        data = r.json()
        timeline = (data.get("interest_over_time") or {}).get("timeline_data") or []
        vals = []
        for pt in timeline:
            arr = pt.get("values") or []
            if arr and arr[0].get("extracted_value") is not None:
                vals.append(arr[0]["extracted_value"])
        if not vals:
            return None
        return _normalize_series(vals)
    except Exception as e:
        logger.warning("[trend] serpapi failed for %s/%s: %s", niche, market, e)
        return None


def trend_meta(niche, market):
    if _is_denied(niche):
        logger.info("[trend] denylisted niche skipped: %s", niche)
        return {"score": 0.0, "source": "denylist"}
    key = "%s|%s" % ((niche or "").strip().lower(), (market or "").strip().upper())
    cached = _cache_get(key)
    if isinstance(cached, dict) and "score" in cached:
        return {"score": float(cached["score"]), "source": str(cached.get("source", "cache")) + "+cache"}
    s = _serpapi_trend(niche, market)
    if s is not None:
        res = {"score": s, "source": "serpapi"}
        _cache_put(key, res)
        return res
    return {"score": NEUTRAL, "source": "neutral"}


def trend_score(niche, market):
    return trend_meta(niche, market)["score"]
