"""Trend verification lane (SerpApi) = GATE FILTER #1 for candidate keywords.

Chot 26/07/2026 (user):
- Cac lane ben (evergreen / wiki_spike / gtrends_daily / news / AI de xuat) cho ra
  chu de dung gu nhung KHONG biet co dang trend hay khong.
- Lane serpapi rising bat duoc trend nhung de lech chu de.
=> Dung SerpApi Google Trends TIMESERIES lam gate do TREND cho MOI candidate,
   bat ke lane nao sinh ra (ke ca lane 'ai_notion' do Notion AI tu suy luan).

Hieu qua quota: 1 credit = toi da 5 term (q="a,b,c,d,e") -> 20 term ~ 4 credits.

Endpoints:
  POST /api/v1/trend-verify   {market, terms[], window, batch}
  POST /api/v1/trend-ai-lane  {market, terms[{term,theme,note}]}
"""

import datetime as _dt
import json
import os

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from app.services import serp_budget

router = APIRouter()

GEO = {"US": "US", "JP": "JP", "KR": "KR", "UK": "GB", "GB": "GB"}
DEFAULT_WINDOW = os.getenv("TREND_VERIFY_WINDOW", "now 7-d")
BATCH = int(os.getenv("TREND_VERIFY_BATCH", "5"))
HOT_LAST = float(os.getenv("TREND_VERIFY_HOT_LAST", "8"))
HOT_MOM = float(os.getenv("TREND_VERIFY_HOT_MOM", "1.25"))
WARM_LAST = float(os.getenv("TREND_VERIFY_WARM_LAST", "3"))

from core.paths import resolve_raw_pool_dir

RAW_POOL_DIR = str(resolve_raw_pool_dir())


class VerifyReq(BaseModel):
    market: str = "US"
    terms: list = []
    window: str = None
    batch: int = None


class AiLaneReq(BaseModel):
    market: str = "US"
    terms: list = []


def _mean(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return 0.0
    return round(sum(xs) / float(len(xs)), 2)


def _series_metrics(series):
    """series = list of numeric interest values, oldest -> newest."""
    n = len(series)
    if n == 0:
        return {"peak": 0, "mean": 0.0, "last": 0.0, "prev": 0.0,
                "momentum": 0.0, "spike": 0.0, "verdict": "NO_DATA"}
    tail = max(1, n // 4)
    last = _mean(series[-tail:])
    prev = _mean(series[:-tail]) if n > tail else 0.0
    peak = max(series)
    mean = _mean(series)
    momentum = round(last / prev, 2) if prev > 0 else (2.0 if last > 0 else 0.0)
    spike = round(peak / mean, 2) if mean > 0 else 0.0
    if last >= HOT_LAST and momentum >= HOT_MOM:
        verdict = "HOT"
    elif last >= HOT_LAST:
        verdict = "STEADY_HIGH"
    elif last >= WARM_LAST:
        verdict = "WARM"
    elif peak >= HOT_LAST and last < peak * 0.3:
        verdict = "PEAK_PAST"
    else:
        verdict = "FLAT"
    return {"peak": peak, "mean": mean, "last": last, "prev": prev,
            "momentum": momentum, "spike": spike, "verdict": verdict}


def _verify_batch(terms, geo, window):
    """One SerpApi credit for up to 5 terms. Returns {term: metrics} or {}."""
    q = ",".join(terms)
    params = {"engine": "google_trends", "q": q, "data_type": "TIMESERIES",
              "date": window, "geo": geo, "tz": "0"}
    resp = serp_budget.serp_get(params, timeout=30.0)
    if resp is None:
        logger.warning("[trend-verify] serpapi unavailable (key/quota) for %s", q)
        return {}
    if resp.status_code != 200:
        logger.warning("[trend-verify] serpapi http %s for %s", resp.status_code, q)
        return {}
    try:
        data = resp.json() or {}
    except Exception as e:
        logger.warning("[trend-verify] bad json: %s", e)
        return {}
    tl = ((data.get("interest_over_time") or {}).get("timeline_data") or [])
    if not tl:
        logger.warning("[trend-verify] empty timeline for %s", q)
        return {}
    series = {}
    for point in tl:
        for v in (point.get("values") or []):
            name = str(v.get("query") or "").strip()
            if not name:
                continue
            val = v.get("extracted_value")
            if val is None:
                try:
                    val = int(str(v.get("value") or "0").replace("<", "").strip() or 0)
                except Exception:
                    val = 0
            series.setdefault(name, []).append(float(val))
    out = {}
    keys = list(series.keys())
    for i, term in enumerate(terms):
        key = term if term in series else (keys[i] if i < len(keys) else None)
        out[term] = _series_metrics(series.get(key, []) if key else [])
    return out


@router.post("/api/v1/trend-verify")
def trend_verify(req: VerifyReq):
    """Gate filter #1: do do trend that cho tung candidate qua Google Trends."""
    market = (req.market or "US").upper()
    geo = GEO.get(market, market)
    window = req.window or DEFAULT_WINDOW
    batch = int(req.batch or BATCH)
    batch = max(1, min(5, batch))

    terms = []
    for t in (req.terms or []):
        t = str(t).strip()
        if t and t.lower() not in [x.lower() for x in terms]:
            terms.append(t)
    if not terms:
        return {"status": "error", "reason": "terms rong"}

    results = {}
    calls = 0
    for i in range(0, len(terms), batch):
        chunk = terms[i:i + batch]
        got = _verify_batch(chunk, geo, window)
        if got:
            calls += 1
            results.update(got)
        else:
            for t in chunk:
                results[t] = {"verdict": "NO_DATA", "peak": 0, "mean": 0.0,
                              "last": 0.0, "prev": 0.0, "momentum": 0.0, "spike": 0.0}

    rows = []
    for t in terms:
        m = dict(results.get(t) or {})
        m["term"] = t
        rows.append(m)
    order = {"HOT": 0, "STEADY_HIGH": 1, "WARM": 2, "PEAK_PAST": 3,
             "FLAT": 4, "NO_DATA": 5}
    rows.sort(key=lambda r: (order.get(r.get("verdict"), 9), -float(r.get("last") or 0)))

    buckets = {}
    for r in rows:
        buckets[r["verdict"]] = buckets.get(r["verdict"], 0) + 1

    day = _dt.date.today().isoformat()
    path = os.path.join(RAW_POOL_DIR, "trend_verify_%s_%s.json" % (market, day))
    payload = {"market": market, "geo": geo, "window": window, "day": day,
               "serp_calls": calls, "buckets": buckets, "rows": rows}
    try:
        os.makedirs(RAW_POOL_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    except Exception as e:
        logger.warning("[trend-verify] cannot cache: %s", e)
    logger.info("[trend-verify] %s terms=%d calls=%d buckets=%s",
                market, len(terms), calls, buckets)
    payload["cache_file"] = path
    payload["budget"] = serp_budget.read_budget() if hasattr(serp_budget, "read_budget") else None
    return payload


@router.post("/api/v1/trend-ai-lane")
def trend_ai_lane(req: AiLaneReq):
    """Notion AI la 1 lane cao rieng: nap candidate do AI tu suy luan vao raw pool."""
    market = (req.market or "US").upper()
    day = _dt.date.today().isoformat()
    path = os.path.join(RAW_POOL_DIR, "trend_raw_pool_%s.json" % day)
    try:
        with open(path) as f:
            pool = json.load(f)
    except Exception:
        pool = {"day": day, "by_market": {}}
    bm = pool.setdefault("by_market", {}).setdefault(market, {})
    lane = bm.setdefault("ai_notion", [])
    seen = set()
    for row in lane:
        seen.add(str(row.get("term", "")).strip().lower())
    added = []
    for item in (req.terms or []):
        if isinstance(item, str):
            item = {"term": item}
        term = str((item or {}).get("term") or "").strip()
        if not term or term.lower() in seen:
            continue
        seen.add(term.lower())
        row = {"term": term, "lane": "ai_notion",
               "theme": str(item.get("theme") or ""),
               "note": str(item.get("note") or ""),
               "added_at": _dt.datetime.utcnow().isoformat() + "Z"}
        lane.append(row)
        added.append(term)
    counts = bm.setdefault("_counts", {})
    counts["ai_notion"] = len(lane)
    try:
        os.makedirs(RAW_POOL_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(pool, f, ensure_ascii=False, indent=1)
    except Exception as e:
        return {"status": "error", "reason": "cannot write pool: %s" % e}
    logger.info("[ai-lane] %s added=%d total=%d", market, len(added), len(lane))
    return {"status": "ok", "market": market, "added": added,
            "lane_total": len(lane), "pool_file": path}
