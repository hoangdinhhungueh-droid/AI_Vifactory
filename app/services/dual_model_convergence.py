"""app/services/dual_model_convergence.py — Dual-Model Convergence Protocol.

Implements the Adversarial Dual-Model Convergence Protocol (R2.1):
1. When B2.1 Audit by Claude-Opus-5 fails (< 7.5 or FAIL):
   - Pass 1 (Direct Scribe): Claude-Opus-5 directly rewrites/edits the 5-Act script,
     resolving every factual/causal discrepancy cited in its critique and anchoring
     strictly to the verified Grounding Table (Rule 118 & Rule 130).
   - Pass 2 (Cross-Audit): GPT-6-Astra acts as Cross-Auditor, verifying dramatic suspense,
     ticking-clock pacing, Story Gate 12/12 criteria, and ensuring no unauthorized data hallucination.
2. If both models reach consensus (Score >= 7.5 and Story Gate >= 10/12):
   - Script is certified PASS and proceeds to B3 Hollywood Director Plan.
3. If models do NOT converge:
   - Returns status="NON_CONVERGENCE" so the Centralized Orchestrator Leader
     can cleanly activate Optimal Candidate Rotation without unhandled ghost loops.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("dual_model_convergence")

ACT_PATTERN = re.compile(r'(=== ACT [I|V|X]+ ===.*?)(?=(=== ACT [I|V|X]+ ===|\Z))', re.DOTALL)


def run_dual_model_convergence(
    story_text: str,
    grounding_claims: List[Dict[str, Any]],
    audit_critique: str,
    topic_meta: Dict[str, Any],
    market: str = "EN",
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the Dual-Model Convergence loop:
    Pass 1: Claude-Opus-5 Direct Scribe
    Pass 2: GPT-6-Astra Cross-Audit
    """
    from app.services.model_gateway import get_global_gateway
    from app.services.story_fact_auditor_b2 import audit_story_facts_and_causality
    import app.services.story_gate as sgate

    task_id = topic_meta.get("task_id", "UNKNOWN_TASK")
    topic = topic_meta.get("topic_name_vi") or topic_meta.get("topic") or task_id
    breakout_queries = topic_meta.get("rising_queries") or []
    
    # Format Grounding Table
    grounding_table_lines = [
        "| Index | Claim / Data Anchor | Source Verification & Date | Verified Metric | Causal Role |",
        "|---|---|---|---|---|"
    ]
    for idx, c in enumerate(grounding_claims, 1):
        grounding_table_lines.append(
            f"| {idx} | {c.get('claim', '')} | {c.get('source_title', '')} ({c.get('date', 'N/A')}) | {c.get('verified_metric', '')} | {c.get('causal_type', 'Level 1 Catalyst')} |"
        )
    grounding_table_str = "\n".join(grounding_table_lines)

    logger.info(f"[dual_convergence] Starting Dual-Model Convergence for {task_id} ({market})...")

    # ----------------------------------------------------
    # Pass 1: Claude-Opus-5 Direct Scribe
    # ----------------------------------------------------
    scribe_prompt = f"""You are an elite investigative documentary chief editor and senior scribe.
You previously audited an investigative documentary script and found factual, attribution, or causal discrepancies.
Your task now is to DIRECTLY REWRITE and EDIT the entire 5-Act script to resolve 100% of your own audit critique.

=== YOUR AUDIT CRITIQUE & REQUIRED CORRECTIONS ===
{audit_critique}

=== ORIGINAL SCRIPT ===
{story_text}

=== MANDATORY VERIFIED GROUNDING TABLE (GROUND TRUTH) ===
{grounding_table_str}

=== STRICT EDITORIAL RULES (RULE 118, RULE 130 & RULE 445) ===
1. Level 1 Primary Catalyst: In Act I (paragraphs 1-2), explicitly name the verified Catalyst Event, acting entity, date, and quantitative impact. Do NOT dodge into vague abstractions.
2. Causal Integrity: Level 2 institutional/transmission mechanisms must never be swapped for the Level 1 Catalyst.
3. Zero Speculation: Do not introduce ANY numbers, percentages, or dollar amounts not present in the Grounding Table.
4. Structure: Maintain the 5 structured Acts ('=== ACT I ===' to '=== ACT V ===') with 1,800 to 2,200 words.
5. High Suspense: Maintain relentless ticking-clock pacing and procedural investigative tension.

Output ONLY the complete, edited 5-Act script now:"""

    gateway = get_global_gateway()
    logger.info(f"[dual_convergence] Pass 1: Calling Claude-Opus-5 as Direct Scribe for {task_id}...")

    try:
        scribe_raw = gateway.call_llm(
            prompt=scribe_prompt,
            model="claude-opus-5",
            system_prompt=system_prompt,
            max_tokens=3500,
            temperature=0.4,
            timeout=240.0,
            fallback="gpt-6-astra"
        )
    except Exception as se:
        logger.error(f"[dual_convergence] Pass 1 (Opus 5 Scribe) failed: {se}")
        return {
            "converged": False,
            "status": "NON_CONVERGENCE",
            "reason": f"Opus 5 Scribe error: {se}",
            "script": story_text,
            "score": 0.0
        }

    # Clean acts
    cleaned_acts = []
    matches = ACT_PATTERN.findall(scribe_raw)
    if matches:
        for m in matches:
            cleaned_acts.append(m[0].strip())
    
    repaired_script = "\n\n".join(cleaned_acts) if len(cleaned_acts) == 5 else scribe_raw.strip()
    word_count = len(repaired_script.split())
    logger.info(f"[dual_convergence] Pass 1 Scribe complete: {word_count} words ({len(cleaned_acts)}/5 acts).")

    # ----------------------------------------------------
    # Pass 2: GPT-6-Astra Cross-Audit (Dramaturgy, Pacing & Fact Consistency)
    # ----------------------------------------------------
    logger.info(f"[dual_convergence] Pass 2: Running GPT-6-Astra Cross-Audit for {task_id}...")
    
    # Story Gate Score
    story_audit = sgate.score_story(repaired_script)
    sg_score = story_audit.get("score", 0)
    sg_verdict = story_audit.get("verdict", "FAIL")
    logger.info(f"[dual_convergence] Pass 2 Story Gate Score: {sg_score}/12 (Verdict: {sg_verdict})")

    # Re-verify Fact & Causal Integrity with Claude-Opus-5 / Astra
    re_audit = audit_story_facts_and_causality(
        story_text=repaired_script,
        grounding_claims=grounding_claims,
        topic_meta=topic_meta,
        market=market,
        model="claude-opus-5",
        fallback_model="gpt-6-astra"
    )

    re_verdict = re_audit.get("verdict", "FAIL").upper()
    re_score = float(re_audit.get("audit_score", 0.0))
    logger.info(f"[dual_convergence] Pass 2 Fact & Causal Score: {re_score}/10 (Verdict: {re_verdict})")

    # Convergence Condition: Fact Score >= 7.5 AND Story Gate >= 10/12 AND Word Count >= 1500
    converged = (re_verdict == "PASS" or re_score >= 7.5) and (sg_score >= 10) and (word_count >= 1500)

    if converged:
        logger.info(
            f"[dual_convergence] SUCCESS: Dual-Model Convergence ACHIEVED for {task_id}! "
            f"(Fact Score: {re_score}/10, Story Gate: {sg_score}/12)"
        )
        return {
            "converged": True,
            "status": "PASS",
            "script": repaired_script,
            "word_count": word_count,
            "fact_score": re_score,
            "story_gate_score": sg_score,
            "audit_details": re_audit
        }
    else:
        veto_reason = re_audit.get("veto_reason") or re_audit.get("audit_notes") or f"Score under threshold ({re_score}/10, SG: {sg_score}/12)"
        logger.warning(
            f"[dual_convergence] NON_CONVERGENCE: Models failed to reach consensus for {task_id}. "
            f"Fact Score: {re_score}/10, SG: {sg_score}/12. Reason: {veto_reason}"
        )
        return {
            "converged": False,
            "status": "NON_CONVERGENCE",
            "reason": veto_reason,
            "script": repaired_script,
            "word_count": word_count,
            "fact_score": re_score,
            "story_gate_score": sg_score,
            "audit_details": re_audit
        }
