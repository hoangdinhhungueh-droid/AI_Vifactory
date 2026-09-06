# app/audit/db.py -- Database layer for audit results + skill enhancements
# Uses existing PostgreSQL connection (utils.db_helpers.get_pg_connection)
import json
import logging
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)

# === SQL SCHEMA (run once via scripts/init-audit-tables.sql) ===

SCHEMA_SQL = """
-- Audit results: one row per audit run
CREATE TABLE IF NOT EXISTS audit_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id TEXT NOT NULL,
    audit_type TEXT NOT NULL,          -- story | director | prompt | image
    stage TEXT NOT NULL,                -- S2 | S2.5 | S5 | S9
    score NUMERIC(4,2) NOT NULL,        -- 0.00-10.00 composite score
    verdict TEXT NOT NULL,              -- APPROVED | REVIEW | REJECTED
    axis_scores JSONB NOT NULL,         -- {"structure": 9, "hook": 8, ...}
    issues JSONB NOT NULL,              -- [{"severity": "high", "axis": "hook", "message": "...", "fix": "..."}]
    recommendations JSONB NOT NULL,    -- [{"skill": "/video:story", "update": "...", "priority": "high"}]
    llm_used TEXT,                      -- groq | gemini | rule_only
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Skill enhancement proposals: generated from audit patterns
CREATE TABLE IF NOT EXISTS skill_enhancements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_result_id UUID REFERENCES audit_results(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,          -- /video:story, /video:director, /video:prompt
    enhancement_type TEXT NOT NULL,    -- prompt_update | rule_add | threshold_adjust | pattern_learn
    current_value TEXT,                -- current skill config value
    proposed_value TEXT NOT NULL,      -- proposed new value
    rationale TEXT NOT NULL,            -- why this enhancement is needed
    confidence NUMERIC(3,2) DEFAULT 0.50,  -- 0.00-1.00 confidence score
    status TEXT DEFAULT 'pending',     -- pending | approved | rejected | applied
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_results_episode ON audit_results (episode_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_results_type ON audit_results (audit_type, verdict, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_enhancements_status ON skill_enhancements (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_enhancements_skill ON skill_enhancements (skill_name, status);
"""


def get_conn():
    """Get PostgreSQL connection using existing VF infrastructure."""
    try:
        from utils.db_helpers import get_pg_connection
        return get_pg_connection()
    except ImportError:
        import os
        import psycopg2
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost/video_factory_db")
        return psycopg2.connect(db_url)


def init_schema():
    """Create audit tables if not exist. Run once at deploy time."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
        logger.info("Audit tables initialized.")
    except Exception as e:
        logger.error(f"Failed to init audit tables: {e}")
        raise
    finally:
        conn.close()


def save_audit_result(episode_id: str, audit_type: str, stage: str,
                       score: float, verdict: str, axis_scores: dict,
                       issues: list, recommendations: list, llm_used: str = "rule_only") -> str:
    """Save audit result to Postgres. Returns audit_result_id."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_results
                    (episode_id, audit_type, stage, score, verdict, axis_scores, issues, recommendations, llm_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (episode_id, audit_type, stage, score, verdict,
                   json.dumps(axis_scores), json.dumps(issues),
                   json.dumps(recommendations), llm_used))
            result_id = str(cur.fetchone()[0])
        conn.commit()
        logger.info(f"Audit result saved: {audit_type}/{episode_id} score={score} verdict={verdict}")
        return result_id
    except Exception as e:
        logger.error(f"Failed to save audit result: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_enhancement(audit_result_id: str, skill_name: str, enhancement_type: str,
                     current_value: str, proposed_value: str, rationale: str,
                     confidence: float = 0.50) -> str:
    """Save a skill enhancement proposal. Returns enhancement_id."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO skill_enhancements
                    (audit_result_id, skill_name, enhancement_type, current_value, proposed_value, rationale, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (audit_result_id, skill_name, enhancement_type,
                   current_value, proposed_value, rationale, confidence))
            enh_id = str(cur.fetchone()[0])
        conn.commit()
        return enh_id
    except Exception as e:
        logger.error(f"Failed to save enhancement: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_recent_audits(audit_type: str = None, limit: int = 20) -> list:
    """Get recent audit results, optionally filtered by type."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if audit_type:
                cur.execute("""
                    SELECT id, episode_id, audit_type, stage, score, verdict, axis_scores, issues, recommendations, created_at
                    FROM audit_results WHERE audit_type = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (audit_type, limit))
            else:
                cur.execute("""
                    SELECT id, episode_id, audit_type, stage, score, verdict, axis_scores, issues, recommendations, created_at
                    FROM audit_results
                    ORDER BY created_at DESC LIMIT %s
                """, (limit,))
            return cur.fetchall()
    finally:
        conn.close()


def get_pending_enhancements() -> list:
    """Get all pending skill enhancement proposals."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, skill_name, enhancement_type, current_value, proposed_value, rationale, confidence, created_at
                FROM skill_enhancements WHERE status = 'pending'
                ORDER BY confidence DESC, created_at DESC
            """)
            return cur.fetchall()
    finally:
        conn.close()


def approve_enhancement(enhancement_id: str):
    """Mark enhancement as approved."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE skill_enhancements SET status = 'approved', approved_at = NOW()
                WHERE id = %s AND status = 'pending'
            """, (enhancement_id,))
        conn.commit()
    finally:
        conn.close()


def apply_enhancement(enhancement_id: str):
    """Mark enhancement as applied (after skill update is done)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE skill_enhancements SET status = 'applied', applied_at = NOW()
                WHERE id = %s AND status = 'approved'
            """, (enhancement_id,))
        conn.commit()
    finally:
        conn.close()


def get_audit_history(episode_id: str) -> list:
    """Get all audit results for a specific episode."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT audit_type, stage, score, verdict, axis_scores, issues, created_at
                FROM audit_results WHERE episode_id = %s
                ORDER BY created_at ASC
            """, (episode_id,))
            return cur.fetchall()
    finally:
        conn.close()


def get_recurring_issues(audit_type: str, min_count: int = 3, days: int = 30) -> list:
    """Find issues that appear in multiple audits -- candidates for skill enhancement."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT issue->>'axis' as axis, issue->>'message' as message,
                       issue->>'fix' as fix, COUNT(*) as occurrence_count
                FROM audit_results, jsonb_array_elements(issues) as issue
                WHERE audit_type = %s
                  AND created_at >= NOW() - INTERVAL '%s days'
                GROUP BY axis, message, fix
                HAVING COUNT(*) >= %s
                ORDER BY occurrence_count DESC
            """, (audit_type, days, min_count))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to get recurring issues: {e}")
        return []
    finally:
        conn.close()


def get_approved_enhancements(skill_name: str = None, limit: int = 10) -> list:
    """16/08: approved/applied enhancement rules, injected into audit prompts (skill-loaded scoring)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if skill_name:
                cur.execute("""SELECT proposed_value FROM skill_enhancements
                    WHERE status IN ('approved','applied') AND skill_name = %s
                    ORDER BY created_at DESC LIMIT %s""", (skill_name, limit))
            else:
                cur.execute("""SELECT proposed_value FROM skill_enhancements
                    WHERE status IN ('approved','applied')
                    ORDER BY created_at DESC LIMIT %s""", (limit,))
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def get_approved_awaiting_sync() -> list:
    """23/08/2026 -- Rule 121 reverse-sync gate: enhancements a human has approved
    (status='approved') but that have NOT yet been pushed into the live Skill AI
    Notion page. Consumed only by scripts/sync_skill_enhancements.py, which runs
    one more GPT-6-Astra strict-audit pass (generalized-not-per-episode + no
    conflict with current Skill AI content) before writing to Notion and calling
    apply_enhancement() to mark the row 'applied'.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, skill_name, enhancement_type, current_value, proposed_value, rationale, confidence
                FROM skill_enhancements WHERE status = 'approved'
                ORDER BY confidence DESC, created_at ASC
            """)
            return cur.fetchall()
    finally:
        conn.close()
