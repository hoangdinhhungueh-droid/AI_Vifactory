# app/services/trend_keyword_cache.py - Smart Trend-Keyword Cache Library (21/07, revised 22/07).
# Accumulates SerpApi related/story candidates beyond today's pick so nothing is
# wasted once the 250/month free quota (serp_budget.py) is spent.
#
# REVISED 22/07 (chot Decisions Log "SUA HUONG Smart Trend-Keyword Cache"):
#   - VPS/Python only does EXACT-slug dedup on save (cheap, deterministic, no
#     embedding model / LLM call required) - venv has no sentence-transformers/
#     torch and we deliberately do NOT add them or route to a chat LLM instead.
#   - Semantic-cluster/dedup + best-candidate selection is now done by Notion AI
#     (human-in-the-loop "Gate 1"): it reads a pending batch via
#     get_review_batch() and applies its decision via apply_review_decision().
#   - Block-list anti-repeat still reuses app.services.produced_ledger's
#     QID-based canonical entity ledger (unchanged, applied by caller).
# Best-effort everywhere: never raises into the discovery pipeline; a broken
# cache degrades to "no backup candidates", not a crashed run.
import os
import json
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
BACKUP_LIMIT_DEFAULT = int(os.getenv("TREND_CACHE_BACKUP_LIMIT", "10"))
REVIEW_BATCH_LIMIT_DEFAULT = int(os.getenv("TREND_CACHE_REVIEW_LIMIT", os.getenv("TREND_CACHE_CLUSTER_SCAN", "300")))

_SCHEMA_READY = False


def _conn():
    import psycopg2
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return True
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return False
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS trend_keyword_cache ("
                    "id SERIAL PRIMARY KEY, "
                    "slug TEXT NOT NULL, "
                    "market TEXT NOT NULL, "
                    "geo TEXT, "
                    "raw_term TEXT NOT NULL, "
                    "aliases JSONB DEFAULT '[]'::jsonb, "
                    "source TEXT, "
                    "score DOUBLE PRECISION DEFAULT 0, "
                    "embedding DOUBLE PRECISION[], "
                    "hit_count INTEGER DEFAULT 1, "
                    "qid TEXT, "
                    "blocked BOOLEAN DEFAULT FALSE, "
                    "consumed BOOLEAN DEFAULT FALSE, "
                    "fetched_at TIMESTAMPTZ DEFAULT NOW(), "
                    "consumed_at TIMESTAMPTZ, "
                    "created_at TIMESTAMPTZ DEFAULT NOW(), "
                    "UNIQUE (market, slug)"
                    ")"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tkc_market_consumed "
                    "ON trend_keyword_cache (market, consumed)"
                )
        _SCHEMA_READY = True
        return True
    except Exception as e:
        logger.warning("[trend_cache] ensure_schema failed: %s", e)
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def save_candidates(items, market, geo, source):
    """items: list of dicts {slug, term, score}. Best-effort upsert with
    EXACT-slug dedup only (semantic-cluster/dedup now done by Notion AI at
    Gate 1 via apply_review_decision, not here)."""
    if not items or not ensure_schema():
        return 0
    market = (market or "").upper()
    saved = 0
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return 0
        with conn:
            with conn.cursor() as cur:
                for it in items:
                    slug = (it.get("slug") or "").strip()
                    term = (it.get("term") or slug).strip()
                    score = float(it.get("score") or 0.0)
                    if not slug:
                        continue
                    cur.execute(
                        "INSERT INTO trend_keyword_cache "
                        "(slug, market, geo, raw_term, source, score) "
                        "VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (market, slug) DO UPDATE SET "
                        "hit_count = trend_keyword_cache.hit_count + 1, "
                        "score = GREATEST(trend_keyword_cache.score, EXCLUDED.score), "
                        "fetched_at = NOW()",
                        (slug, market, geo, term, source, score),
                    )
                    saved += 1
        return saved
    except Exception as e:
        logger.warning("[trend_cache] save_candidates failed: %s", e)
        return saved
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def get_backup_candidates(market, limit=None):
    """Unconsumed, unblocked cache rows for market, newest/highest-score first.
    Block-list filtering (QID) is applied by the caller via produced_ledger."""
    if not ensure_schema():
        return []
    market = (market or "").upper()
    limit = int(limit or BACKUP_LIMIT_DEFAULT)
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return []
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT slug, raw_term, source, score, hit_count FROM trend_keyword_cache "
                    "WHERE market = %s AND consumed = FALSE AND blocked = FALSE "
                    "ORDER BY score DESC, hit_count DESC, fetched_at DESC LIMIT %s",
                    (market, limit),
                )
                rows = cur.fetchall()
        return [
            {"slug": r[0], "raw": r[1], "source": r[2] or "cache_backup",
             "rank_score": float(r[3] or 0.0), "hit_count": int(r[4] or 0)}
            for r in rows
        ]
    except Exception as e:
        logger.warning("[trend_cache] get_backup_candidates failed: %s", e)
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def get_review_batch(market, limit=None):
    """Full unconsumed+unblocked pool (id included) for Notion AI's Gate-1
    review: selection + semantic-cluster/dedup. id lets the caller's decision
    reference exact rows to merge/block/select."""
    if not ensure_schema():
        return []
    market = (market or "").upper()
    limit = int(limit or REVIEW_BATCH_LIMIT_DEFAULT)
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return []
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, slug, raw_term, aliases, source, score, hit_count "
                    "FROM trend_keyword_cache "
                    "WHERE market = %s AND consumed = FALSE AND blocked = FALSE "
                    "ORDER BY fetched_at DESC LIMIT %s",
                    (market, limit),
                )
                rows = cur.fetchall()
        return [
            {"id": r[0], "slug": r[1], "raw": r[2], "aliases": r[3] or [],
             "source": r[4] or "", "rank_score": float(r[5] or 0.0),
             "hit_count": int(r[6] or 0)}
            for r in rows
        ]
    except Exception as e:
        logger.warning("[trend_cache] get_review_batch failed: %s", e)
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def mark_blocked(market, slug):
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE trend_keyword_cache SET blocked = TRUE WHERE market = %s AND slug = %s",
                    ((market or "").upper(), slug),
                )
    except Exception as e:
        logger.warning("[trend_cache] mark_blocked failed: %s", e)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def mark_consumed(market, slug):
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE trend_keyword_cache SET consumed = TRUE, consumed_at = NOW() "
                    "WHERE market = %s AND slug = %s",
                    ((market or "").upper(), slug),
                )
    except Exception as e:
        logger.warning("[trend_cache] mark_consumed failed: %s", e)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def apply_review_decision(market, decisions):
    """decisions: list of dicts from Notion AI's Gate-1 review, each one of:
      {"action": "select", "slug": "..."}                     -> mark_consumed
      {"action": "block", "slug": "..."}                      -> mark_blocked
      {"action": "merge", "slug": "...", "into_slug": "..."} -> fold slug's
        aliases/hit_count into into_slug, then block slug (paraphrase cleanup).
    Best-effort per-item; returns {"applied": n, "errors": [...]}."""
    market = (market or "").upper()
    applied = 0
    errors = []
    if not decisions or not ensure_schema():
        return {"applied": 0, "errors": ["no decisions or schema not ready"]}
    conn = None
    try:
        conn = _conn()
        if conn is None:
            return {"applied": 0, "errors": ["no db connection"]}
        with conn:
            with conn.cursor() as cur:
                for d in decisions:
                    action = (d.get("action") or "").strip().lower()
                    slug = (d.get("slug") or "").strip()
                    if not action or not slug:
                        errors.append("skipped invalid decision: " + json.dumps(d))
                        continue
                    try:
                        if action == "select":
                            cur.execute(
                                "UPDATE trend_keyword_cache SET consumed = TRUE, consumed_at = NOW() "
                                "WHERE market = %s AND slug = %s",
                                (market, slug),
                            )
                        elif action == "block":
                            cur.execute(
                                "UPDATE trend_keyword_cache SET blocked = TRUE "
                                "WHERE market = %s AND slug = %s",
                                (market, slug),
                            )
                        elif action == "merge":
                            into_slug = (d.get("into_slug") or "").strip()
                            if not into_slug:
                                errors.append("merge missing into_slug: " + json.dumps(d))
                                continue
                            cur.execute(
                                "UPDATE trend_keyword_cache SET "
                                "hit_count = trend_keyword_cache.hit_count + ("
                                "SELECT COALESCE(hit_count, 0) FROM trend_keyword_cache "
                                "WHERE market = %s AND slug = %s), "
                                "aliases = aliases || ("
                                "SELECT COALESCE(aliases, '[]'::jsonb) FROM trend_keyword_cache "
                                "WHERE market = %s AND slug = %s) "
                                "WHERE market = %s AND slug = %s",
                                (market, slug, market, slug, market, into_slug),
                            )
                            cur.execute(
                                "UPDATE trend_keyword_cache SET blocked = TRUE "
                                "WHERE market = %s AND slug = %s",
                                (market, slug),
                            )
                        else:
                            errors.append("unknown action: " + action)
                            continue
                        applied += 1
                    except Exception as e:
                        errors.append(slug + ": " + str(e))
        return {"applied": applied, "errors": errors}
    except Exception as e:
        logger.warning("[trend_cache] apply_review_decision failed: %s", e)
        return {"applied": applied, "errors": errors + [str(e)]}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
