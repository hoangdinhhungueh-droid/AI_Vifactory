# app/audit/learn.py — Auto-enhance: audit results → skill enhancement proposals
# This is the FEEDBACK LOOP: audit → learn → enhance skill → better quality → repeat
# Design: 100% free (rule-based pattern extraction, LLM optional), no crash, reliable
import logging
import json
from datetime import datetime

from app.audit.db import get_recent_audits, get_recurring_issues, save_enhancement, get_pending_enhancements
from app.audit.notifier import send_enhancement_notification

logger = logging.getLogger(__name__)

# Skill mapping: audit type → skill name → enhancement type
SKILL_MAP = {
    "story": {
        "skill": "/video:story",
        "axes": {
            "anti_ai_voice": {"type": "rule_add", "description": "Add new anti-AI pattern to detection list"},
            "hook": {"type": "prompt_update", "description": "Update hook generation prompt"},
            "structure": {"type": "prompt_update", "description": "Update story structure template"},
            "open_loops": {"type": "prompt_update", "description": "Update open loop generation"},
            "pacing": {"type": "prompt_update", "description": "Update pacing guidance"},
            "editorial": {"type": "prompt_update", "description": "Update editorial quality guidelines"},
        },
    },
    "director": {
        "skill": "/video:director",
        "axes": {
            "scene_coverage": {"type": "prompt_update", "description": "Update scene generation prompt"},
            "fg_bg_prompts": {"type": "prompt_update", "description": "Update FG/BG prompt generation"},
            "reuse_keys": {"type": "rule_add", "description": "Update reuse key naming convention"},
            "safe_zone": {"type": "rule_add", "description": "Update safe zone assignment rules"},
            "duration": {"type": "rule_add", "description": "Update duration estimation rules"},
            "arc_structure": {"type": "prompt_update", "description": "Update arc structure template"},
            "narration": {"type": "prompt_update", "description": "Update narration generation"},
        },
    },
    "prompt": {
        "skill": "/video:prompt",
        "axes": {
            "style_lock": {"type": "rule_add", "description": "Update style lock keywords"},
            "chroma_key": {"type": "rule_add", "description": "Update chroma-key indicators"},
            "safe_zone": {"type": "rule_add", "description": "Update safe zone rules"},
            "char_limit": {"type": "threshold_adjust", "description": "Adjust character limits"},
            "fg_clarity": {"type": "prompt_update", "description": "Update FG prompt template"},
            "scene_match": {"type": "prompt_update", "description": "Update prompt-scene matching"},
        },
    },
}


def run_learn_cycle(audit_type: str = None, min_occurrences: int = 3, days: int = 30) -> dict:
    """
    Analyze audit results from the past N days, find recurring issues,
    and generate skill enhancement proposals.
    
    This is the AUTOMATED FEEDBACK LOOP:
    1. Collect audit results from period
    2. Find recurring issues (same axis, same pattern, >= min_occurrences)
    3. Generate skill enhancement proposals with confidence scores
    4. Send to Telegram for human approval
    5. Track before/after performance
    
    Returns: {"proposals": int, "patterns": int, "by_type": dict}
    """
    logger.info(f"[learn] Starting learn cycle: type={audit_type} min={min_occurrences} days={days}")
    
    audit_types = [audit_type] if audit_type else ["story", "director", "prompt"]
    total_proposals = 0
    total_patterns = 0
    by_type = {}
    cycle_notifications = []  # 16/08 anti-spam: batch, sent once at cycle end
    
    for atype in audit_types:
        # Get recurring issues for this audit type
        recurring = get_recurring_issues(atype, min_count=min_occurrences, days=days)
        if not recurring:
            by_type[atype] = {"patterns": 0, "proposals": 0}
            continue
        
        skill_config = SKILL_MAP.get(atype, {})
        skill_name = skill_config.get("skill", "")
        axes_config = skill_config.get("axes", {})
        
        type_proposals = 0
        for row in recurring:
            axis = row[0] if row[0] else "unknown"
            message = row[1] if row[1] else ""
            fix = row[2] if row[2] else ""
            count = row[3] if len(row) > 3 else 0
            
            # Get enhancement type for this axis
            axis_config = axes_config.get(axis, {"type": "pattern_learn", "description": "General improvement"})
            enhancement_type = axis_config.get("type", "pattern_learn")
            description = axis_config.get("description", "")
            
            # Calculate confidence: more occurrences = higher confidence
            confidence = min(0.3 + (count * 0.15), 0.95)
            
            # Build proposed value
            proposed_value = f"{description}: {fix} (occurred {count}x in {days}d)"
            rationale = f"Recurring {atype} audit issue on '{axis}' axis: {message} (occurred {count} times in last {days} days)"
            
            # Save enhancement proposal
            try:
                enh_id = save_enhancement(
                    audit_result_id=None,  # 16/08 fix: NULL is FK-safe (column nullable); zero UUID violated skill_enhancements_audit_result_id_fkey
                    skill_name=skill_name,
                    enhancement_type=enhancement_type,
                    current_value="",
                    proposed_value=proposed_value,
                    rationale=rationale,
                    confidence=confidence,
                )
                type_proposals += 1
                total_proposals += 1
                
                # 16/08 anti-spam: collect; ONE summary sent at cycle end
                if confidence >= 0.6:
                    cycle_notifications.append((skill_name, enhancement_type, proposed_value, confidence))
            except Exception as e:
                logger.error(f"[learn] Failed to save enhancement: {e}")
        
        by_type[atype] = {"patterns": len(recurring), "proposals": type_proposals}
        total_patterns += len(recurring)
    
    if cycle_notifications:
        from app.audit.notifier import send_learn_summary
        send_learn_summary(audit_type or "all", total_patterns, total_proposals, cycle_notifications)
    logger.info(f"[learn] Complete: {total_patterns} patterns → {total_proposals} proposals")
    return {"proposals": total_proposals, "patterns": total_patterns, "by_type": by_type}


def get_approval_queue() -> list:
    """Get pending enhancement proposals for human review."""
    return get_pending_enhancements()


def calculate_improvement(audit_type: str, before_date: str, after_date: str) -> dict:
    """
    Calculate quality improvement after skill enhancement was applied.
    A/B test: compare average audit scores before vs after enhancement.
    """
    from app.audit.db import get_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Average score before
            cur.execute("""
                SELECT AVG(score) FROM audit_results
                WHERE audit_type = %s AND created_at < %s
            """, (audit_type, before_date))
            before_avg = float(cur.fetchone()[0] or 0)
            
            # Average score after
            cur.execute("""
                SELECT AVG(score) FROM audit_results
                WHERE audit_type = %s AND created_at >= %s
            """, (audit_type, after_date))
            after_avg = float(cur.fetchone()[0] or 0)
            
            improvement = after_avg - before_avg
            
            return {
                "audit_type": audit_type,
                "before_avg": round(before_avg, 2),
                "after_avg": round(after_avg, 2),
                "improvement": round(improvement, 2),
                "verdict": "improved" if improvement > 0.1 else "no_change" if abs(improvement) < 0.1 else "regressed",
            }
    finally:
        conn.close()
