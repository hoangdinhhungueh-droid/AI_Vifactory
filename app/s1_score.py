# app/s1_score.py — S1 Trend Scoring v2 (spec: page 05 §S1 Scoring Formula + page 03 routes)
# POST /api/v1/s1-score      -> score niches x markets -> scoring_history (best-effort)
# POST /api/v1/pipeline/run  -> n8n vf-cron-trend-score entrypoint (stage S1)
# v2 fixes (18/06):
#   (P0) gap parse crash fix (AttributeError when LLM returns a bare float)
#   (P0) require a REAL trend signal (serpapi/pytrends) to PASS — no silent NEUTRAL pass
#   (P1) trend via app.services.trend_signals.trend_meta (serpapi -> pytrends -> neutral, cached)
#   (P2) cooldown/novelty penalty via scoring_history so 1 keyword can't dominate for a week
import os, json, logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel
import psycopg2
from app.llm_router import llm_call, _send_telegram

logger = logging.getLogger(__name__)
router = APIRouter()

THRESHOLD = 0.65
NEUTRAL_TREND = 0.5

# Weights v2 (rebalanced): reduce hard-bias toward a single niche family.
W_CPM   = 0.35
W_TREND = 0.35
W_GAP   = 0.20
W_SAFE  = 0.10  # used as penalty if not safe

# Anti-repeat (P2): niches that passed within COOLDOWN_DAYS get a novelty penalty
# so the same top keyword does not resurface every cron run.
COOLDOWN_DAYS   = int(os.getenv("S1_COOLDOWN_DAYS", "7"))
NOVELTY_PENALTY = float(os.getenv("S1_NOVELTY_PENALTY", "0.15"))

CPM_WEIGHT = {"US": 1.00, "CA": 0.80, "GB": 0.80, "AU": 0.75, "JP": 0.70,
              "NZ": 0.65, "EU": 0.60, "KR": 0.55, "VN": 0.15, "IN": 0.12}

# IP-safe allowlist (gate). Keep broad enough to avoid overfitting.
SAFE_NICHES = [
    "betrayal-revenge", "dark-fiction", "sleep-story", "relationship-drama",
    "true-crime-audio", "mystery-thriller",
    "stoicism", "self-improvement", "productivity",
    "ai-explained", "tech-history",
    "isekai", "litrpg", "xianxia", "cultivation-novel",
]

# Default seeds: diversified; NOT the same as SAFE_NICHES.
SEED_NICHES_DEFAULT = [
    "betrayal-revenge", "dark-fiction", "sleep-story", "relationship-drama",
    "true-crime-audio", "mystery-thriller",
    "stoicism", "productivity",
    "ai-explained", "tech-history",
]

DEFAULT_MARKETS = ["US", "AU", "JP", "KR"]


class S1Request(BaseModel):
    niches: list[str] | None = None
    markets: list[str] | None = None


def _estimate_gap_llm(niches, market):
    """Estimate supply/demand gap (0..1) via free LLM chain, best-effort."""
    prompt = (
        "For each niche below, estimate for the market '" + market + "':\n"
        "- gap: content supply gap (1.0 = high demand, low supply), 0.0-1.0\n"
        "Niches: " + ", ".join(niches) + "\n"
        'Respond ONLY with JSON: {"<niche>": {"gap": 0.0}, ...}'
    )
    res = llm_call(prompt, task_type="S1_gap_estimate",
                   system="You are a precise market analyst. Respond with valid JSON only.")
    txt = res["text"]
    data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    if not isinstance(data, dict):
        raise ValueError("S1 LLM gap estimate is not a JSON object")
    return data, res.get("provider", "unknown")


def _trend_meta(niche, market):
    """Real trend signal (0..1) + source. Neutral only when no provider works."""
    try:
        from app.services.trend_signals import trend_meta as _tm
        m = _tm(niche, market)
        return float(m.get("score", NEUTRAL_TREND)), str(m.get("source", "neutral"))
    except Exception as e:
        logger.warning("[S1] trend_meta failed for %s/%s: %s", niche, market, e)
        return NEUTRAL_TREND, "neutral"


def _recent_passed_niches(cooldown_days=COOLDOWN_DAYS):
    """Distinct niches that recently passed (anti-repeat). Best-effort; never crash."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return set()
    try:
        with psycopg2.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT column_name FROM information_schema.columns "
                            "WHERE table_name='scoring_history'")
                cols = {r[0] for r in cur.fetchall()}
                niche_col = next((c for c in ("niche_tag", "niche") if c in cols), None)
                score_col = next((c for c in ("composite_score", "composite", "score") if c in cols), None)
                ts_col = next((c for c in ("scored_at", "created_at", "inserted_at", "ts", "created") if c in cols), None)
                if not niche_col or not ts_col:
                    return set()
                q = ('SELECT DISTINCT "' + niche_col + '" FROM scoring_history '
                     'WHERE "' + ts_col + '" >= NOW() - (%s || \' days\')::interval')
                params = [str(int(cooldown_days))]
                if score_col:
                    q += ' AND "' + score_col + '" >= %s'
                    params.append(THRESHOLD)
                cur.execute(q, params)
                return {r[0] for r in cur.fetchall() if r and r[0]}
    except Exception as e:
        logger.warning("[S1] cooldown lookup failed: %s", e)
        return set()


def _persist(rows):
    """Best-effort insert vao scoring_history — runtime column mapping, khong crash vi lech schema."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return "skipped: DATABASE_URL not set"
    try:
        with psycopg2.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT column_name FROM information_schema.columns "
                            "WHERE table_name='scoring_history'")
                cols = {r[0] for r in cur.fetchall()}
                if not cols:
                    return "skipped: scoring_history not found"
                n = 0
                for r in rows:
                    field_map = {
                        "niche_tag": r["niche"], "niche": r["niche"],
                        "market_code": r["market"], "market": r["market"],
                        "composite_score": r["composite"], "composite": r["composite"],
                        "score": r["composite"],
                        "details": json.dumps(r), "metadata": json.dumps(r),
                    }
                    use = {k: v for k, v in field_map.items() if k in cols}
                    if not use:
                        return "skipped: no matching columns in scoring_history"
                    names = ",".join(use.keys())
                    ph = ",".join(["%s"] * len(use))
                    cur.execute("INSERT INTO scoring_history (" + names + ") VALUES (" + ph + ")",
                                list(use.values()))
                    n += 1
            conn.commit()
            return "inserted %d rows" % n
    except Exception as e:
        logger.warning("[S1] scoring_history persist failed: %s", e)
        return "failed: %s" % e


def run_s1(niches=None, markets=None):
    niches = [n.strip() for n in (niches or SEED_NICHES_DEFAULT) if n and n.strip()]
    markets = [m.strip().upper() for m in (markets or DEFAULT_MARKETS) if m and m.strip()]
    recent = _recent_passed_niches()
    out, passed = [], []
    for market in markets:
        cpm = CPM_WEIGHT.get(market, 0.5)
        try:
            est, provider = _estimate_gap_llm(niches, market)
        except Exception as e:  # garbage/exhaust -> neutral fallback, khong chet ca batch
            logger.warning("[S1] LLM estimate failed for %s: %s", market, e)
            est, provider = {}, "fallback_neutral"
        for niche in niches:
            e = est.get(niche) if isinstance(est, dict) else None
            if not isinstance(e, dict):
                e = {}
            trend, trend_source = _trend_meta(niche, market)
            try:
                gap = min(max(float(e.get("gap", 0.5)), 0.0), 1.0)
            except (TypeError, ValueError, AttributeError):
                gap = 0.5
            ip_safe = 1.0 if niche in SAFE_NICHES else 0.0
            safe_penalty = 0.0 if ip_safe >= 1.0 else 0.5
            composite = round(cpm * W_CPM + trend * W_TREND + gap * W_GAP + (ip_safe * W_SAFE), 4)
            if safe_penalty > 0:
                composite = round(composite * (1.0 - safe_penalty), 4)
            on_cooldown = niche in recent
            if on_cooldown:
                composite = round(max(0.0, composite - NOVELTY_PENALTY), 4)
            if composite is None:  # R-QA: never silent-null
                raise ValueError("Score is None for %s" % niche)
            has_real_trend = trend_source not in ("neutral", "denylist")
            is_pass = (ip_safe >= 1.0 and composite >= THRESHOLD and has_real_trend)
            row = {"niche": niche, "market": market, "cpm_score": cpm,
                   "trend": trend, "trend_source": trend_source,
                   "ip_safe": ip_safe, "gap_score": gap, "cooldown": on_cooldown,
                   "composite": composite, "pass": is_pass, "source": provider,
                   "scored_at": datetime.now(timezone.utc).isoformat()}
            out.append(row)
            if is_pass:
                passed.append(row)
    persist = _persist(out)
    return {"threshold": THRESHOLD, "scored": len(out), "passed": len(passed),
            "results": sorted(out, key=lambda r: -r["composite"]),
            "top_passed": sorted(passed, key=lambda r: -r["composite"])[:10],
            "persist": persist}


@router.post("/api/v1/s1-score")
def s1_score(req: S1Request):
    """S1 market scoring — page 05 Scoring Formula v2."""
    return run_s1(req.niches, req.markets)


@router.post("/api/v1/pipeline/run")
async def pipeline_run(request: Request):
    """n8n entrypoint (vf-cron-trend-score). Body: {stage, niches?, markets?}."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    expected = os.getenv("PIPELINE_API_KEY", "")
    if expected and request.headers.get("X-API-Key", "") != expected:
        return {"status": "denied", "reason": "bad X-API-Key"}
    stage = str(body.get("stage") or "S1").upper()
    if stage != "S1":
        return {"status": "not_implemented", "stage": stage,
                "note": "Only S1 is live; S2-S9 di cung MPT gates G1-G5"}
    result = run_s1(body.get("niches"), body.get("markets"))
    if result["passed"]:
        top = result["top_passed"][0]
        _send_telegram("\U0001F4E2 TREND_READY — S1: %d/%d cap niche-market dat nguong %.2f. "
                       "Top: %s/%s = %.2f (trend:%s)"
                       % (result["passed"], result["scored"], THRESHOLD,
                          top["niche"], top["market"], top["composite"],
                          top.get("trend_source", "?")))
    return {"status": "ok", "stage": "S1", "threshold": result["threshold"],
            "scored": result["scored"], "passed": result["passed"],
            "top_passed": result["top_passed"], "persist": result["persist"]}
