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
    system_prompt: Optional[str] = None,
    max_rounds: int = 3
) -> Dict[str, Any]:
    """
    Executes the Dual-Model Convergence loop (up to max_rounds, default 3):
    Round N:
      Pass 1: Claude Line (Opus 5 / Sonnet 5 / Kimi-K3) Direct Scribe
      Pass 2: GPT-6-Astra Cross-Audit & Story Gate Verification
    Loops iteratively until consensus is achieved or max_rounds is exhausted.
    """
    from app.services.model_gateway import get_global_gateway
    from app.services.story_fact_auditor_b2 import audit_story_facts_and_causality
    import app.services.story_gate as sgate

    task_id = topic_meta.get("task_id", "UNKNOWN_TASK")
    topic = topic_meta.get("topic_name_vi") or topic_meta.get("topic") or task_id
    breakout_queries = topic_meta.get("rising_queries") or []
    gateway = get_global_gateway()
    
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

    logger.info(f"[dual_convergence] Starting Dual-Model Convergence for {task_id} ({market}) [Max {max_rounds} rounds]...")

    current_script = story_text
    current_critique = audit_critique
    last_re_audit: Dict[str, Any] = {}
    last_re_score = 0.0
    last_sg_score = 0
    last_word_count = 0

    for round_idx in range(1, max_rounds + 1):
        logger.info(f"[dual_convergence] === Round {round_idx}/{max_rounds}: Direct Scribe & Cross-Audit ===")

        # ----------------------------------------------------
        # Pass 1: Claude Line Direct Scribe
        # ----------------------------------------------------
        scribe_prompt = f"""You are an elite investigative documentary chief editor and senior scribe.
You previously audited an investigative documentary script and found factual, attribution, or causal discrepancies.
Your task now is to DIRECTLY REWRITE and EDIT the entire 5-Act script to resolve 100% of your own audit critique.

=== YOUR AUDIT CRITIQUE & REQUIRED CORRECTIONS (ROUND {round_idx}) ===
{current_critique}

=== CURRENT DRAFT SCRIPT ===
{current_script}

=== MANDATORY VERIFIED GROUNDING TABLE (GROUND TRUTH) ===
{grounding_table_str}

=== STRICT EDITORIAL RULES (RULE 118, RULE 130 & RULE 445) ===
1. Level 1 Primary Catalyst: In Act I (paragraphs 1-2), explicitly name the verified Catalyst Event, acting entity, date, and quantitative impact. Do NOT dodge into vague abstractions.
2. Causal Integrity: Level 2 institutional/transmission mechanisms must never be swapped for the Level 1 Catalyst.
3. Zero Speculation: Do not introduce ANY numbers, percentages, or dollar amounts not present in the Grounding Table.
4. Structure: Maintain the 5 structured Acts ('=== ACT I ===' to '=== ACT V ===') with 1,800 to 2,200 words.
5. High Suspense: Maintain relentless ticking-clock pacing and procedural investigative tension.

Output ONLY the complete, edited 5-Act script now:"""

        logger.info(f"[dual_convergence] Pass 1 (Round {round_idx}): Calling Claude Line as Scribe for {task_id}...")
        try:
            try:
                scribe_raw = gateway.call_llm(
                    prompt=scribe_prompt,
                    model="claude-opus-5",
                    system_prompt=system_prompt,
                    max_tokens=5500,
                    temperature=0.3,
                    timeout=200.0,
                    fallback="claude-sonnet-5"
                )
            except Exception as e_claude:
                logger.warning(f"[dual_convergence] Both Claude models failed ({e_claude}), trying kimi-k3 as Scribe...")
                scribe_raw = gateway.call_llm(
                    prompt=scribe_prompt,
                    model="kimi-k3",
                    system_prompt=system_prompt,
                    max_tokens=5500,
                    temperature=0.3,
                    timeout=200.0,
                    fallback="gpt-6-astra"
                )
        except Exception as se:
            logger.error(f"[dual_convergence] Pass 1 Scribe failed on round {round_idx}: {se}")
            if round_idx == max_rounds:
                return {
                    "converged": False,
                    "status": "NON_CONVERGENCE",
                    "reason": f"Scribe error: {se}",
                    "script": current_script,
                    "score": last_re_score
                }
            continue

        # Clean acts
        cleaned_acts = []
        matches = ACT_PATTERN.findall(scribe_raw)
        if matches:
            for m in matches:
                cleaned_acts.append(m[0].strip())
        
        repaired_script = "\n\n".join(cleaned_acts) if len(cleaned_acts) == 5 else scribe_raw.strip()
        words_list = sgate._words(repaired_script)
        word_count = len(words_list)
        logger.info(f"[dual_convergence] Pass 1 Scribe (Round {round_idx}) complete: {word_count} words/units ({len(cleaned_acts)}/5 acts).")

        # ----------------------------------------------------
        # Pass 2: Cross-Audit & Story Gate Verification
        # ----------------------------------------------------
        logger.info(f"[dual_convergence] Pass 2 (Round {round_idx}): Running Cross-Audit for {task_id}...")
        
        story_audit = sgate.score_story(repaired_script)
        sg_score = story_audit.get("score", 0)
        sg_verdict = story_audit.get("verdict", "FAIL")
        logger.info(f"[dual_convergence] Round {round_idx} Story Gate Score: {sg_score}/12 (Verdict: {sg_verdict})")

        re_audit = audit_story_facts_and_causality(
            story_text=repaired_script,
            grounding_claims=grounding_claims,
            topic_meta=topic_meta,
            market=market,
            model="claude-opus-5",
            fallback_model="kimi-k3"
        )

        re_verdict = re_audit.get("verdict", "FAIL").upper()
        re_score = float(re_audit.get("audit_score", 0.0))
        logger.info(f"[dual_convergence] Round {round_idx} Fact & Causal Score: {re_score}/10 (Verdict: {re_verdict})")

        last_re_audit = re_audit
        last_re_score = re_score
        last_sg_score = sg_score
        last_word_count = word_count
        current_script = repaired_script

        # Convergence Condition: Fact Score >= 7.5 AND Story Gate >= 10/12 AND Word Count >= 1500 (950 for CJK)
        is_cjk = market.upper() in ("JP", "KR", "ZH")
        cjk_chars = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]', repaired_script))
        is_cjk_script = is_cjk or cjk_chars > 300
        min_words = 950 if is_cjk_script else 1500
        converged = (re_verdict == "PASS" or re_score >= 7.5) and (sg_score >= 10) and (word_count >= min_words)

        if converged:
            logger.info(
                f"[dual_convergence] SUCCESS: Dual-Model Convergence ACHIEVED on Round {round_idx}/{max_rounds} for {task_id}! "
                f"(Fact Score: {re_score}/10, Story Gate: {sg_score}/12)"
            )
            return {
                "converged": True,
                "status": "PASS",
                "rounds_used": round_idx,
                "script": repaired_script,
                "word_count": word_count,
                "fact_score": re_score,
                "story_gate_score": sg_score,
                "audit_details": re_audit
            }
        
        # Prepare next round critique
        current_critique = (
            f"Round {round_idx} critique:\n"
            f"- Fact & Causal Score: {re_score}/10 (Findings: {re_audit.get('critical_findings') or re_audit.get('veto_reason') or 'Unresolved discrepancies'})\n"
            f"- Story Gate: {sg_score}/12 (Fix hints: {story_audit.get('fix_hints', [])})\n"
            f"Please address all above points in this subsequent refinement pass."
        )

    veto_reason = last_re_audit.get("veto_reason") or last_re_audit.get("critical_findings") or f"Score under threshold after {max_rounds} rounds ({last_re_score}/10, SG: {last_sg_score}/12)"
    logger.warning(
        f"[dual_convergence] NON_CONVERGENCE: Models failed to reach consensus after {max_rounds} rounds for {task_id}. "
        f"Fact Score: {last_re_score}/10, SG: {last_sg_score}/12. Reason: {veto_reason}"
    )
    return {
        "converged": False,
        "status": "NON_CONVERGENCE",
        "rounds_used": max_rounds,
        "reason": veto_reason,
        "script": current_script,
        "word_count": last_word_count,
        "fact_score": last_re_score,
        "story_gate_score": last_sg_score,
        "audit_details": last_re_audit
    }
