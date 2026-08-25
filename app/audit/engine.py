# app/audit/engine.py — Main audit engine: orchestrates checks, scoring, storage, notification
# Design: 100% free (rule-first), no crash (timeout+graceful), RAM efficient (<200MB)
import logging
import time
import json
from datetime import datetime

from app.audit.rubrics import get_rubric, calculate_composite_score, get_verdict, get_axes_by_method
from app.audit.db import save_audit_result, save_enhancement
from app.audit.notifier import send_audit_notification

logger = logging.getLogger(__name__)

# Circuit breaker for LLM calls
_llm_failure_count = 0
_LLM_FAILURE_THRESHOLD = 3
_LLM_TIMEOUT_S = 15  # 15s per LLM call


def _call_llm(prompt: str, system: str = "") -> str:
    # 16/08: skill-loaded scoring - inject approved learn-cycle rules
    try:
        from app.audit.db import get_approved_enhancements
        _rules = get_approved_enhancements(limit=10)
        if _rules:
            system = (system + "\n\nLEARNED RULES (approved from previous audit cycles):\n" + "\n".join("- " + str(r)[:150] for r in _rules)).strip()
    except Exception as e:
        logger.warning(f"learn-rules inject skipped: {e}")
    """Groq first, DeepSeek-hhtech fallback (17/08, llm_chain). Returns text or None."""
    global _llm_failure_count
    if _llm_failure_count >= _LLM_FAILURE_THRESHOLD:
        logger.warning("LLM circuit breaker open - rule-only scoring")
        return None
    from app.audit.llm_chain import call_llm
    content, provider = call_llm(prompt, system, timeout=_LLM_TIMEOUT_S)
    if content:
        _llm_failure_count = 0
        logger.info(f"LLM audit call OK via {provider}")
        return content
    _llm_failure_count += 1
    return None


def run_audit(episode_id: str, audit_type: str, stage: str, content: dict) -> dict:
    """
    Main audit entry point. Runs all checks for the given audit type.
    
    Args:
        episode_id: Episode identifier (e.g. "en-enron-ep006")
        audit_type: "story" | "director" | "prompt" | "image"
        stage: Pipeline stage that triggered audit ("S2", "S2.5", "S5")
        content: Dict with the content to audit (story_text, scenes, prompts, images)
    
    Returns:
        {"score": float, "verdict": str, "axis_scores": dict, "issues": list, "recommendations": list}
    """
    start_time = time.time()
    rubric = get_rubric(audit_type)
    if not rubric:
        return {"score": 0, "verdict": "REJECTED", "axis_scores": {}, "issues": [{"severity": "critical", "message": f"Unknown audit type: {audit_type}"}], "recommendations": []}

    logger.info(f"[audit] Starting {audit_type} audit for {episode_id} at stage {stage}")

    # Dispatch to specific audit module
    axis_scores = {}
    issues = []
    recommendations = []
    llm_used = "rule_only"

    try:
        if audit_type == "story":
            from app.audit.story_audit import audit_story
            axis_scores, issues, recommendations, llm_used = audit_story(content, _call_llm)
        elif audit_type == "director":
            from app.audit.director_audit import audit_director
            axis_scores, issues, recommendations, llm_used = audit_director(content, _call_llm)
        elif audit_type == "prompt":
            from app.audit.prompt_audit import audit_prompt
            axis_scores, issues, recommendations, llm_used = audit_prompt(content, _call_llm)
        elif audit_type == "image":
            # Image audit uses rule-based checks only (no LLM needed for basic checks)
            from app.audit.image_audit import audit_image
            axis_scores, issues, recommendations, llm_used = audit_image(content, _call_llm)
    except Exception as e:
        logger.error(f"[audit] {audit_type} audit failed: {e}", exc_info=True)
        issues.append({"severity": "critical", "axis": "system", "message": f"Audit engine error: {str(e)}", "fix": "Check audit pipeline code"})
        # Graceful degradation: score what we can
        for axis in rubric.get("axes", {}):
            if axis not in axis_scores:
                axis_scores[axis] = 5.0  # Neutral score for unassessed axes

    # Calculate composite score
    score = calculate_composite_score(axis_scores, rubric)
    verdict = get_verdict(score, rubric, axis_scores)

    # Generate skill enhancement recommendations from issues
    for issue in issues:
        if issue.get("severity") in ("high", "critical"):
            skill_map = {
                "story": "/video:story",
                "director": "/video:director",
                "prompt": "/video:prompt",
                "image": "/video:prompt",
            }
            recommendations.append({
                "skill": skill_map.get(audit_type, ""),
                "update": issue.get("fix", "Review and update skill"),
                "priority": issue.get("severity", "medium"),
                "axis": issue.get("axis", ""),
            })

    # Store in Postgres
    try:
        audit_id = save_audit_result(
            episode_id=episode_id,
            audit_type=audit_type,
            stage=stage,
            score=score,
            verdict=verdict,
            axis_scores=axis_scores,
            issues=issues,
            recommendations=recommendations,
            llm_used=llm_used,
        )
        # Save high-priority recommendations as enhancement proposals
        for rec in recommendations:
            if rec.get("priority") in ("high", "critical"):
                save_enhancement(
                    audit_result_id=audit_id,
                    skill_name=rec.get("skill", ""),
                    enhancement_type="pattern_learn",
                    current_value="",
                    proposed_value=rec.get("update", ""),
                    rationale=f"{audit_type} audit score {score}/10: {rec.get('axis', '')} issue",
                    confidence=min(score / 10.0, 0.95),
                )
    except Exception as e:
        logger.error(f"[audit] Failed to store results: {e}")

    # Send Telegram notification
    try:
        send_audit_notification(episode_id, audit_type, stage, score, verdict, axis_scores, issues)
    except Exception as e:
        logger.warning(f"[audit] Notification failed: {e}")

    elapsed = time.time() - start_time
    logger.info(f"[audit] {audit_type}/{episode_id} complete: score={score} verdict={verdict} ({elapsed:.1f}s)")

    return {
        "score": score,
        "verdict": verdict,
        "axis_scores": axis_scores,
        "issues": issues,
        "recommendations": recommendations,
        "audit_id": audit_id if 'audit_id' in dir() else None,
        "elapsed_s": round(elapsed, 1),
    }


def reset_llm_circuit_breaker():
    """Reset the LLM circuit breaker (call after LLM service recovers)."""
    global _llm_failure_count
    _llm_failure_count = 0
    logger.info("LLM circuit breaker reset.")
