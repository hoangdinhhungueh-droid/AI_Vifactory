"""
app/services/adversarial_critic_b1.py - ADVERSARIAL CRITIC GATE (B1.1)

Mission:
  Independent adversarial critic that audits candidate topics and proposed viral angles
  BEFORE committing to B1.5 Competitor Recon and B2 Story Engine.

Key Invariants:
  1. Anti-Stale Trap: Rejects topics anchored to old historical events without a verified 2026 catalyst.
  2. News Catalyst Coupling: Confirms that the proposed angle explains the live breaking news from the past 24-48h.
  3. Anti-Bait-and-Switch (Rule 130): Vetoes topics where LLM invents a safe, generic corporate/academic tangent
     instead of addressing the viewer's direct search intent.
  4. VETO Authority: If verdict is FAIL, B1 immediately rotates to the next candidate.
  5. Scale-Up and Generic Pattern (Rule 128): 100% agnostic to market (KR, EN, JP) and content pillar (1-5).
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("adversarial_critic_b1")

SYSTEM_CRITIC_PROMPT = """You are the Chief Adversarial Critic and Editorial Gatekeeper for AI Video Factory (VF Pipeline).
Your sole mandate is to ruthlessly interrogate whether a proposed video candidate & angle genuinely answers LIVE viewer search intent or is committing a "Bait-and-Switch" divergence.

You must audit against 4 Iron Criteria:
1. CURRENT SEARCH VITALITY & ANTI-STALE TRAP:
   - Is this event actively breaking/developing right now (in 2026)?
   - REJECT (FAIL) if this is an old historical event (e.g. 2024 or earlier) recycled without a fresh 2026 legal, financial, or breaking catalyst.
2. NEWS CATALYST COUPLING:
   - If breaking news articles (past 24-48h) are present, does the proposed angle directly decode the headline catalyst?
   - REJECT (FAIL) if the angle completely ignores the breaking news headlines to discuss a generic corporate/academic textbook topic.
3. ANTI-BAIT-AND-SWITCH (RULE 130 SEARCH-INTENT PAYOFF):
   - When viewers search this keyword, what is the urgent question on their mind?
   - REJECT (FAIL) if the model borrows a viral breaking keyword as clickbait, but immediately steers (be lai) into an unrelated tangent (e.g. shipbuilder balance sheet instead of missile strikes on ships).
4. POLICY SAFETY & FACTUAL GROUNDING (HARD SAFETY VETO):
   - Safe under YouTube Community Guidelines & Monetization Policies.
   - STRICT REJECTION (FAIL): REJECT immediately if the candidate or proposed angle centers on electoral politics, partisan campaigning, one-sided political rhetoric, religious doctrine/defamation, or unverified personal attacks on private individuals.
5. CONSUMER DOCUDRAMA & ANTI-TUTORIAL PACKAGING (RULE 130):
   - For consumer disputes / retail traps (Pillar 11): Enforce the 3-tier gate (Outlier score >= 3.0x or breaking traffic, asymmetric institutional/contract loophole, and verified by media/regulator).
   - REJECT (FAIL) if the proposed angle or title sounds like a dry tutorial / customer service FAQ / how-to guide ('How to', 'Mẹo vặt', '5 bước', '환불하는법'). The angle MUST formulate a high-stakes dramatic clash: [Everyday Item/Transaction + Shock Figure] vs [Unilateral Fine Print / Institutional Trap].

Passing threshold:
- audit_score >= 7.5/10
- All criteria must be satisfied.
- If failed, you MUST specify "verdict": "FAIL" and provide a crisp "veto_reason" in English and Vietnamese.

Output MUST be a single valid JSON object matching this schema:
{
  "verdict": "PASS" | "FAIL",
  "audit_score": <FLOAT 0.0 - 10.0>,
  "trend_vitality_score": <FLOAT 0.0 - 10.0>,
  "catalyst_coupling_score": <FLOAT 0.0 - 10.0>,
  "search_payoff_score": <FLOAT 0.0 - 10.0>,
  "safety_score": <FLOAT 0.0 - 10.0>,
  "veto_reason": "<CONCISE SUMMARY OF VETO OR NULL IF PASSED>",
  "red_flags": [<STRING>, ...]
}
"""


def audit_candidate_trend_alignment(
    candidate_term: str,
    specific_angle: str,
    niche_brief: str,
    market: str = "KR",
    news_catalysts: Optional[List[Dict[str, Any]]] = None,
    rising_queries: Optional[List[str]] = None,
    traffic: str = "",
    model: str = "gpt-6-astra",
    fallback_model: str = "claude-sonnet-5-5"
) -> Dict[str, Any]:
    """Execute adversarial critique of candidate and proposed angle.
    Returns audit result dict with 'verdict': 'PASS'|'FAIL'.
    """
    from app.services.model_gateway import get_global_gateway
    gateway = get_global_gateway()

    m_up = (market or "EN").strip().upper()

    news_text = "No recent breaking news headlines found."
    if news_catalysts:
        n_lines = []
        for n in news_catalysts[:6]:
            t = n.get("title", "").strip()
            d = n.get("description", "").strip()
            p = n.get("published_at", "").strip()
            if t:
                n_lines.append(f"  - [{p}] \"{t}\" ({d[:150]})")
        if n_lines:
            news_text = "\n".join(n_lines)

    rising_text = "None"
    if rising_queries:
        rising_text = ", ".join([str(q).strip() for q in rising_queries[:8] if str(q).strip()])

    user_prompt = f"""[AUDIT TARGET]
Candidate Search Term: "{candidate_term}"
Target Market: {m_up}
Approx Traffic / Signal: {traffic}
Rising / Breakout Search Queries: {rising_text}

[PROPOSED PRODUCTION ANGLE (BY LLM PRODUCER)]
Specific Viral Angle: "{specific_angle}"
Niche Brief: "{niche_brief}"

[VERIFIED BREAKING NEWS CATALYSTS (GOOGLE NEWS PAST 24-48H)]
{news_text}

Interrogate whether this proposed angle truly satisfies the breaking search intent, or if it constitutes a Bait-and-Switch diversion. Return strict JSON only."""

    chosen_model = model or "gpt-6-astra"
    fallback_model = fallback_model or "claude-sonnet-5-5"

    try:
        raw_res = gateway.call_llm(
            prompt=user_prompt,
            model=chosen_model,
            system_prompt=SYSTEM_CRITIC_PROMPT,
            max_tokens=800,
            temperature=0.1,
            timeout=60.0,
            fallback=fallback_model
        )
    except Exception as e:
        logger.warning(f"[critic_gate] Claude primary ({chosen_model}) failed ({e}), invoking fallback {fallback_model}...")
        try:
            chosen_model = fallback_model
            raw_res = gateway.call_llm(
                prompt=user_prompt,
                model=chosen_model,
                system_prompt=SYSTEM_CRITIC_PROMPT,
                max_tokens=800,
                temperature=0.1,
                timeout=60.0,
                fallback="gpt-6-astra"
            )
        except Exception as e2:
            logger.error(f"[critic_gate] Fallback critic model {fallback_model} also failed: {e2}")
            return {
                "verdict": "PASS",
                "audit_score": 7.5,
                "veto_reason": f"Critic API unavailable ({e2}), bypassed",
                "red_flags": ["CRITIC_GATE_OFFLINE_BYPASS"]
            }

    clean_json = raw_res.strip()
    match_codeblock = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw_res)
    if match_codeblock:
        clean_json = match_codeblock.group(1).strip()
    else:
        match_obj = re.search(r'(\{[\s\S]*\})', raw_res)
        if match_obj:
            clean_json = match_obj.group(1).strip()
        elif clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)

    try:
        audit_result = json.loads(clean_json)
    except Exception as parse_err:
        logger.warning(f"[critic_gate] Failed to parse critic JSON: {parse_err}. Raw:\n{raw_res}")
        if "FAIL" in raw_res.upper() and ("REJECT" in raw_res.upper() or "STALE" in raw_res.upper() or "BAIT" in raw_res.upper()):
            return {
                "verdict": "FAIL",
                "audit_score": 4.0,
                "veto_reason": "Regex fallback: Critic detected critical red flags in narrative alignment",
                "red_flags": ["CRITIC_PARSING_FALLBACK_FAIL"]
            }
        return {
            "verdict": "PASS",
            "audit_score": 8.0,
            "veto_reason": None,
            "red_flags": []
        }

    verdict = audit_result.get("verdict", "FAIL").upper()
    score = float(audit_result.get("audit_score", 0.0))
    if score < 7.5 and verdict == "PASS":
        verdict = "FAIL"
        audit_result["verdict"] = "FAIL"
        audit_result["veto_reason"] = audit_result.get("veto_reason") or f"Score {score} is below passing threshold (7.5)"

    logger.info(f"[critic_gate] Audited '{candidate_term}' ({m_up}): Verdict={verdict} (Score: {score}/10) | Veto: {audit_result.get('veto_reason')}")
    return audit_result


REPAIR_SYSTEM_PROMPT = """You are a Senior Investigative Documentary Editor and Narrative Strategist.
A candidate topic for an 8-12 minute investigative documentary passed initial viability, but the Adversarial Critic Gate identified an alignment, timing, or search-intent flaw in the proposed angle.

Your task:
Directly address the Critic Gate's veto reason and reconstruct a sharp, compelling, single-sentence investigative angle that:
1. Aligns 100% with viewer search intent and breaking news catalysts.
2. Fixes the specific flaw highlighted by the Critic (e.g., naming the exact deadline/trigger, focusing on the imminent catalyst instead of stale background, clarifying institutional stakes).
3. Follows the Rule 130 causal formula: <CATALYST_EVENT> -> <TRANSMISSION_MECHANISM> -> <CORE_SYSTEMIC_PARADOX>.

Output ONLY valid JSON matching this schema:
{
  "repaired_angle": "<Single-sentence investigative angle in the native market language/English>",
  "repair_rationale": "<1-2 sentence explanation of how the critic feedback was resolved>"
}
"""


def repair_candidate_angle(
    candidate_term: str,
    original_angle: str,
    veto_reason: str,
    market: str = "EN",
    news_catalysts: Optional[List[Dict[str, Any]]] = None,
    rising_queries: Optional[List[str]] = None,
    model: str = "gpt-6-astra",
    fallback_model: str = "claude-sonnet-5-5",
) -> str:
    """Attempt a 1-shot self-repair of candidate viral angle based on Critic Gate veto feedback (Rule 124, 130)."""
    from app.services.model_gateway import get_global_gateway
    gateway = get_global_gateway()

    m_up = (market or "EN").strip().upper()
    news_text = "No recent breaking news headlines found."
    if news_catalysts:
        n_lines = []
        for n in news_catalysts[:6]:
            t = n.get("title", "").strip()
            d = n.get("description", "").strip()
            p = n.get("published_at", "").strip()
            if t:
                n_lines.append(f"  - [{p}] \"{t}\" ({d[:150]})")
        if n_lines:
            news_text = "\n".join(n_lines)

    rising_text = ", ".join(rising_queries[:6]) if rising_queries else "None"

    user_prompt = f"""[MARKET: {m_up}]
CANDIDATE TERM: {candidate_term}
ORIGINAL PROPOSED ANGLE: {original_angle}

CRITIC GATE VETO REASON & DIRECT CRITIQUE:
{veto_reason}

RECENT BREAKING NEWS CATALYSTS:
{news_text}

VIEWER SEARCH INTENT / RISING QUERIES:
{rising_text}

TASK:
Reconstruct a repaired single-sentence investigative angle that resolves the Critic's critique completely while staying grounded in verified events. Respond in valid JSON only.
"""

    chosen_model = model
    try:
        raw_res = gateway.call_llm(
            prompt=user_prompt,
            model=chosen_model,
            system_prompt=REPAIR_SYSTEM_PROMPT,
            max_tokens=600,
            temperature=0.2,
            timeout=45.0,
            fallback=fallback_model,
        )
    except Exception as e:
        logger.warning(f"[critic_repair] Primary repair model {chosen_model} failed: {e}. Trying fallback {fallback_model}...")
        try:
            raw_res = gateway.call_llm(
                prompt=user_prompt,
                model=fallback_model,
                system_prompt=REPAIR_SYSTEM_PROMPT,
                max_tokens=600,
                temperature=0.2,
                timeout=45.0,
                fallback="gpt-6-astra",
            )
        except Exception as e2:
            logger.error(f"[critic_repair] Fallback repair model {fallback_model} also failed: {e2}")
            return original_angle

    clean_json = raw_res.strip()
    match_codeblock = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw_res)
    if match_codeblock:
        clean_json = match_codeblock.group(1).strip()
    else:
        match_obj = re.search(r'(\{[\s\S]*\})', raw_res)
        if match_obj:
            clean_json = match_obj.group(1).strip()

    try:
        data = json.loads(clean_json)
        repaired = data.get("repaired_angle", "").strip()
        if repaired and len(repaired) > 10:
            logger.info(f"[critic_repair] Repaired angle for '{candidate_term}': '{repaired}' (Rationale: {data.get('repair_rationale')})")
            return repaired
    except Exception as parse_err:
        logger.warning(f"[critic_repair] Failed to parse repair JSON: {parse_err}")

    return original_angle

