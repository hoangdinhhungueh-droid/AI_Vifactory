"""app/services/dual_model_convergence.py — Dual-Model Convergence Protocol.

Implements the Adversarial Targeted Delta-Convergence Protocol (Rule 125 & Rule 130):
1. Roles:
   - Claude-Opus-5: Master Scriptwriter & Targeted Patcher (Rewrites ONLY defective Acts; preserves high dramatic tension and emotional power).
   - GPT-6-Astra: Senior Fact-Check Gatekeeper (Audits patched Acts against Grounding Table; enforces Restrained Editorial Policy).
2. Convergence Cycle (Max 3 rounds):
   - Pass 1 (Targeted Patcher - Opus 5): Receives defective Act(s) + Astra 6 fact critique + Grounding Table.
     Outputs ONLY the revised Act(s). Reassembles script with intact passing Acts.
   - Pass 2 (Delta Re-Audit - Astra 6): Evaluates ONLY the patched Act(s) with minimal token context (~3-5K tokens).
3. Consensus Verification:
   - Fact & Causal Score >= 7.5/10 (Astra 6)
   - Story Gate Score >= 10/12 (Rule 121 / 127)
   - Multi-Lingual Length Validity (Rule 120 / text_metrics.py: JP >= 2500 chars, KR >= 2200 chars / 750 words, EN >= 1200 words).
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.text_metrics import (
    validate_script_length,
    get_script_units,
    get_unit_name,
    detect_language
)
from app.services.model_gateway import get_global_gateway

logger = logging.getLogger("dual_model_convergence")

ACT_SPLIT_PATTERN = re.compile(
    r'(=== (ACT [I|V|X]+) ===[\s\S]*?)(?=(?:=== ACT [I|V|X]+ ===)|\Z)',
    re.IGNORECASE
)


def parse_script_into_acts(story_text: str) -> Dict[str, str]:
    """Splits a 5-Act docudrama script into structured dictionary { 'ACT I': text, ... }."""
    acts: Dict[str, str] = {}
    matches = ACT_SPLIT_PATTERN.findall(story_text)
    if matches:
        for full_act_block, act_key in matches:
            clean_key = act_key.upper().strip()
            acts[clean_key] = full_act_block.strip()

    # Fallback if delimiter was slightly non-standard
    if len(acts) < 5:
        roman_nums = ["I", "II", "III", "IV", "V"]
        for idx, r in enumerate(roman_nums):
            act_tag = f"ACT {r}"
            if act_tag not in acts:
                p = re.search(rf'((?:#+\s*|===+\s*)?ACT\s+{r}\b[\s\S]*?)(?=(?:#+\s*|===+\s*)?ACT\s+(?:I{1,3}|IV|V)\b|\Z)', story_text, re.IGNORECASE)
                if p:
                    acts[act_tag] = p.group(1).strip()

    return acts


def determine_failing_acts(
    audit_critique: str,
    audit_meta: Optional[Dict[str, Any]] = None,
    existing_acts: Optional[Dict[str, str]] = None
) -> List[str]:
    """Identifies which specific Acts need repair based on auditor findings."""
    failed: List[str] = []

    # 1. Direct structured metadata from Opus 5
    if audit_meta and isinstance(audit_meta, dict):
        structured_failed = audit_meta.get("failed_acts") or audit_meta.get("still_failing_acts") or []
        for fa in structured_failed:
            fa_clean = str(fa).upper().strip()
            if not fa_clean.startswith("ACT"):
                fa_clean = f"ACT {fa_clean}"
            if fa_clean not in failed:
                failed.append(fa_clean)

    # 2. Textual inspection of critique for Act mentions
    if not failed and audit_critique:
        for r in ["I", "II", "III", "IV", "V"]:
            act_name = f"ACT {r}"
            if re.search(rf'\b(Act\s+{r}|Act_{r}|Act{r})\b', audit_critique, re.IGNORECASE):
                if act_name not in failed:
                    failed.append(act_name)

    # 3. Fallback: If critique is generic, focus on Act I & Act II (Rule 130 core catalyst / transmission)
    if not failed:
        if existing_acts:
            failed = [k for k in ["ACT I", "ACT II"] if k in existing_acts]
        else:
            failed = ["ACT I", "ACT II"]

    return sorted(failed)


def run_dual_model_convergence(
    story_text: str,
    grounding_claims: List[Dict[str, Any]],
    audit_critique: str,
    topic_meta: Dict[str, Any],
    market: str = "EN",
    system_prompt: Optional[str] = None,
    max_rounds: int = 3,
    initial_audit_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Executes Adversarial Targeted Delta-Convergence Loop (up to max_rounds, default 3):
    - Astra acts as Targeted Patcher (rewrites only defective Acts).
    - Opus 5 acts as Pure Forensic Auditor (audits only the delta patch in Round 2+).
    """
    from app.services.model_gateway import get_global_gateway
    from app.services.story_fact_auditor_b2 import audit_delta_patched_acts
    import app.services.story_gate as sgate

    task_id = topic_meta.get("task_id", "UNKNOWN_TASK")
    topic = topic_meta.get("topic") or topic_meta.get("title_a") or topic_meta.get("raw_term") or task_id
    gateway = get_global_gateway()
    m_up = (market or "EN").strip().upper()

    # Format Grounding Table (Rule 126 & 134: Zero-Truncation Parity)
    grounding_table_lines = [
        "| Index | Claim / Data Anchor | Source Verification & Date | Verified Metric | Causal Role |",
        "|---|---|---|---|---|"
    ]
    for idx, c in enumerate(grounding_claims, 1):
        claim_text = c.get('claim', '')
        src = c.get('source_title') or c.get('source', '')
        dt = c.get('date', 'N/A')
        metric = c.get('verified_metric', '')
        role = c.get('causal_type') or c.get('causal_role', 'Level 1 Catalyst')
        grounding_table_lines.append(
            f"| {idx} | {claim_text} | {src} ({dt}) | {metric} | {role} |"
        )
    grounding_table_str = "\n".join(grounding_table_lines)

    logger.info(f"[dual_convergence] Starting Targeted Delta-Convergence for {task_id} ({m_up}) [Max {max_rounds} rounds] with {len(grounding_claims)} baseline claims...")

    acts_dict = parse_script_into_acts(story_text)
    if len(acts_dict) < 5:
        logger.warning(f"[dual_convergence] Story script only parsed {len(acts_dict)}/5 acts. Retaining original blocks.")

    current_script = story_text
    current_meta = initial_audit_result or {}
    current_critique = audit_critique
    last_re_score = float(current_meta.get("audit_score", 6.0)) if current_meta else 6.0
    last_sg_score = 0
    last_units = get_script_units(current_script, m_up)
    unit_name = get_unit_name(m_up, current_script)

    for round_idx in range(1, max_rounds + 1):
        failed_acts = determine_failing_acts(
            audit_critique=current_critique,
            audit_meta=current_meta,
            existing_acts=acts_dict
        )
        logger.info(
            f"[dual_convergence] === Round {round_idx}/{max_rounds}: "
            f"Targeted Patch on {failed_acts or ['FULL_REWRITE']} ==="
        )

        # ----------------------------------------------------
        # Pass 1: Claude Opus 5 Targeted Patcher (Master Scriptwriter)
        # ----------------------------------------------------
        # Extract defective text blocks
        flawed_content_parts = []
        for fa in failed_acts:
            content = acts_dict.get(fa, "")
            flawed_content_parts.append(f"=== {fa} (CURRENT DEFECTIVE DRAFT) ===\n{content}\n")
        flawed_content_str = "\n\n".join(flawed_content_parts) if flawed_content_parts else current_script

        patcher_prompt = f"""You are Claude Opus 5, Master Non-Fiction Investigative Documentary Scriptwriter for Video Factory.
GPT-6-Astra (Senior Fact-Check Gatekeeper) audited your 5-Act documentary script and flagged factual discrepancies in specific Acts.
Your mandate is to REWRITE AND PATCH ONLY THE DEFECTIVE ACTS listed below.

=== TARGET ACTS REQUIRING REPAIR ===
{', '.join(failed_acts)}

=== FACT-CHECK AUDITOR CRITIQUE & REQUIRED CORRECTIONS (ROUND {round_idx}) ===
{current_critique}

=== CURRENT DEFECTIVE ACT CONTENT ===
{flawed_content_str}

=== MANDATORY VERIFIED GROUNDING BASELINE (RULE 118 ZERO-MOCK & RULE 130) ===
{grounding_table_str}

=== EDITORIAL RULES ===
1. Level 1 Catalyst: Explicitly cite verified event, actor, date, and quantitative impact from Grounding Table.
2. Emotional & Cinematic Power: Maintain high dramatic suspense, human stakes, and pattern interrupts. Do NOT let factual corrections make the script dry or clinical.
3. Narrative Continuity: Ensure the patched Acts seamlessly flow with the untouched Acts.
4. Native Diction: Natural high-register native phrasing ({m_up}). Zero raw English jargon in JP/KR.
5. DOCUMENT & EXHIBIT DISCIPLINE (ANTI-HALLUCINATED TITLES - RULE 118):
   - When citing internal company documents, slide decks, memos, or court exhibits:
     STRICTLY FORBIDDEN: Inventing fictitious titles, exhibit labels, or memo numbers in quotation marks (e.g. do NOT invent a slide deck titled "Teen Mental Health Deep Dive" or "Exhibit 42" unless that exact verbatim string exists in the Grounding Table).
   - Use factual, descriptive attribution anchored in the Grounding Table (e.g., 'internal research presented to Congress', 'company slide presentations detailing user risks', 'court-ordered discovery records').
   - Anchor evidence to actual verified entities/dates in the Grounding Table without inventing document titles.

Output ONLY the patched Act(s), formatted with standard headers (e.g. '=== ACT I ===', '=== ACT II ==='):"""

        logger.info(
            f"[dual_convergence] Pass 1 (Round {round_idx}): "
            f"Invoking Claude Opus 5.5 to patch {len(failed_acts)} Act(s)..."
        )

        try:
            patched_raw = gateway.call_llm(
                prompt=patcher_prompt,
                model="claude-opus-5-5",
                system_prompt=system_prompt,
                max_tokens=3500,
                temperature=0.3,
                timeout=180.0,
                fallback="claude-sonnet-5"
            )
        except Exception as e_opus:
            logger.warning(f"[dual_convergence] Claude Opus 5.5 patcher failed ({e_opus}), trying claude-sonnet-5 fallback...")
            try:
                patched_raw = gateway.call_llm(
                    prompt=patcher_prompt,
                    model="claude-sonnet-5",
                    system_prompt=system_prompt,
                    max_tokens=3500,
                    temperature=0.3,
                    timeout=120.0,
                    fallback="gpt-6-astra"
                )
            except Exception as se:
                logger.error(f"[dual_convergence] Patcher failed completely on round {round_idx}: {se}")
                if round_idx == max_rounds:
                    return {
                        "converged": False,
                        "status": "NON_CONVERGENCE",
                        "reason": f"Patcher error: {se}",
                        "script": current_script,
                        "score": last_re_score
                    }
                continue

        # Reassemble script: update patched acts in acts_dict
        newly_patched_acts = parse_script_into_acts(patched_raw)
        if newly_patched_acts:
            for ak, av in newly_patched_acts.items():
                acts_dict[ak] = av
        else:
            # If model didn't use strict headers, apply to first target act
            if failed_acts:
                acts_dict[failed_acts[0]] = f"=== {failed_acts[0]} ===\n{patched_raw.strip()}"

        # Order acts canonically
        ordered_acts = []
        for r in ["ACT I", "ACT II", "ACT III", "ACT IV", "ACT V"]:
            if r in acts_dict:
                ordered_acts.append(acts_dict[r])
        repaired_script = "\n\n".join(ordered_acts) if len(ordered_acts) == 5 else patched_raw.strip()
        current_script = repaired_script

        last_units = get_script_units(repaired_script, m_up)
        logger.info(
            f"[dual_convergence] Pass 1 Patch (Round {round_idx}) reassembled: "
            f"{last_units} {unit_name} ({len(ordered_acts)}/5 acts)."
        )

        # ----------------------------------------------------
        # Pass 2: Targeted Delta Re-Audit via GPT-6-Astra
        # ----------------------------------------------------
        logger.info(f"[dual_convergence] Pass 2 (Round {round_idx}): Running Delta Re-Audit via GPT-6-Astra...")

        # Story Gate Verification (Rule 121 & Rule 127)
        story_audit = sgate.score_story(repaired_script)
        sg_score = story_audit.get("score", 0)
        sg_verdict = story_audit.get("verdict", "FAIL")
        logger.info(f"[dual_convergence] Round {round_idx} Story Gate Score: {sg_score}/12 (Verdict: {sg_verdict})")

        # Delta Re-Audit: Only audit the newly patched Acts
        acts_to_audit = newly_patched_acts if newly_patched_acts else {fa: acts_dict.get(fa, "") for fa in failed_acts}
        delta_critique_map = {fa: current_critique for fa in failed_acts}

        re_audit = audit_delta_patched_acts(
            patched_acts=acts_to_audit,
            prior_critique=delta_critique_map,
            grounding_claims=grounding_claims,
            topic_meta=topic_meta,
            market=m_up,
            model="gpt-6-astra",
            fallback_model="kimi-k3"
        )

        re_verdict = re_audit.get("verdict", "FAIL").upper()
        re_score = float(re_audit.get("audit_score", 0.0))
        logger.info(f"[dual_convergence] Round {round_idx} Delta Fact & Causal Score: {re_score}/10 (Verdict: {re_verdict})")

        # Validate multi-lingual length (Rule 120 / Rule 128)
        len_val = validate_script_length(repaired_script, market=m_up)
        is_length_valid = len_val.get("valid", False)

        last_re_score = re_score
        last_sg_score = sg_score
        current_meta = re_audit

        # Convergence Condition: Fact Score >= 7.5 AND Story Gate >= 10/12 AND Length Valid
        converged = (re_verdict == "PASS" or re_score >= 7.5) and (sg_score >= 10) and is_length_valid

        if converged:
            re_audit["verdict"] = "PASS"
            re_audit["audit_score"] = re_score
            logger.info(
                f"[dual_convergence] SUCCESS: Targeted Delta-Convergence ACHIEVED on Round {round_idx}/{max_rounds} for {task_id}! "
                f"(Fact Score: {re_score}/10, Story Gate: {sg_score}/12, Length: {last_units} {unit_name})"
            )
            return {
                "converged": True,
                "status": "PASS",
                "rounds_used": round_idx,
                "script": repaired_script,
                "units": last_units,
                "unit_name": unit_name,
                "fact_score": re_score,
                "story_gate_score": sg_score,
                "audit_details": re_audit
            }

        # Prepare next round critique
        still_failing = re_audit.get("still_failing_acts") or []
        findings = re_audit.get("critical_findings") or "Discrepancies remain in patched acts"
        current_critique = (
            f"Round {round_idx} Delta Critique:\n"
            f"- Fact & Causal Score: {re_score}/10 (Findings: {findings})\n"
            f"- Remaining defective acts: {still_failing or failed_acts}\n"
            f"- Story Gate: {sg_score}/12 (Fix hints: {story_audit.get('fix_hints', [])})\n"
            f"- Length validity: {len_val.get('message')}\n"
            f"Please address remaining defects exclusively in the target acts."
        )

    veto_reason = current_meta.get("critical_findings") or f"Score under threshold after {max_rounds} rounds ({last_re_score}/10, SG: {last_sg_score}/12)"
    logger.warning(
        f"[dual_convergence] NON_CONVERGENCE: Targeted Delta-Convergence did not converge after {max_rounds} rounds for {task_id}. "
        f"Fact Score: {last_re_score}/10, SG: {last_sg_score}/12. Reason: {veto_reason}"
    )
    return {
        "converged": False,
        "status": "NON_CONVERGENCE",
        "rounds_used": max_rounds,
        "reason": veto_reason,
        "script": current_script,
        "units": last_units,
        "unit_name": unit_name,
        "fact_score": last_re_score,
        "story_gate_score": last_sg_score,
        "audit_details": current_meta
    }
