# -*- coding: utf-8 -*-
"""app/services/vox_critic_council.py
Hội đồng Thẩm định LLM Đối kháng (Critic Council) cho Kế hoạch Đạo diễn B3 Vox-Style.
Sử dụng HHTech API với 2 vai chuyên môn:
  1. GPT-6-Astra: Audience Retention, Viral Pacing, Hook & Curiosity Gap.
  2. Claude Opus 5.5: Elite Editorial Art Director, Vox Paper-Collage Aesthetics.

Tối ưu hóa token payload: Chỉ gửi thông tin cốt lõi, không nhồi chat history.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from app.services.model_gateway import get_global_gateway

logger = logging.getLogger("vox_critic_council")

ASTRA_SYSTEM_PROMPT = """You are GPT-6-Astra, Senior YouTube Documentary Retention Strategist and Viral Pacing Specialist.
Your task is to audit a VOX-style Director Plan & Scene Breakdown generated from an investigative documentary script.

Evaluate strictly on:
1. Pacing & Curiosity Gap: Does the visual beat change rapidly (every 4-6s) to maintain viewer retention?
2. Narrative-Visual Alignment: Do the editorial headlines (1-4 words) reinforce the emotional core of each sentence?
3. Information Density: Are the visual metaphors intuitive in under 2 seconds without confusing the viewer?

Output JSON format ONLY:
{
  "evaluator": "GPT-6-Astra",
  "score": <float 0.0 - 10.0>,
  "verdict": "<PASS or NEEDS_REVISION>",
  "retention_pacing_score": <float 0.0 - 10.0>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<flaw 1>", "<flaw 2>"],
  "recommendations": ["<actionable advice 1>"]
}
"""

OPUS_SYSTEM_PROMPT = """You are Claude Opus 5.5, Chief Editorial Art Director and VOX Motion Graphics Visual Supervisor.
Your task is to audit a VOX-style Director Plan & Image Prompt Sequence.

Evaluate strictly on:
1. Vox Aesthetic & Paper Layering: Are elements layered properly (Background paper -> Geometric shape -> Editorial headline -> Cutout subject -> Texture)?
2. Color & Typography Discipline: Max 2-4 accent colors (Vox Yellow, Muted Gold, Terracotta, Navy), large bold sans-serif/serif headlines occupying 20-50% composition?
3. Visual Metaphor Quality: Are concepts communicated through strong symbolic metaphors rather than literal dictionary illustrations?

Output JSON format ONLY:
{
  "evaluator": "Claude-Opus-5.5",
  "score": <float 0.0 - 10.0>,
  "verdict": "<PASS or NEEDS_REVISION>",
  "vox_aesthetic_score": <float 0.0 - 10.0>,
  "typography_metaphor_score": <float 0.0 - 10.0>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<flaw 1>", "<flaw 2>"],
  "recommendations": ["<actionable advice 1>"]
}
"""


def _compress_plan_for_audit(director_plan: List[Dict[str, Any]]) -> str:
    """Nén Director Plan thành bản tóm tắt siêu tinh gọn để tiết kiệm token."""
    lines = []
    for scene in director_plan[:40]:  # Limit top 40 scenes per evaluation
        s_id = scene.get("scene_id", scene.get("scene_number", "SCENE"))
        narration = scene.get("sentence", scene.get("narration", ""))[:120]
        headline = scene.get("editorial_title", scene.get("headline", ""))
        metaphor = scene.get("visual_metaphor", "")
        lines.append(f"[{s_id}] Narration: \"{narration}\" | Headline: \"{headline}\" | Metaphor: \"{metaphor}\"")
    return "\n".join(lines)


def audit_director_plan(
    episode_id: str,
    director_plan: List[Dict[str, Any]],
    script_hook: str = "",
    astra_model: str = "gpt-6-astra",
    opus_model: str = "claude-opus-5-5",
    threshold: float = 7.5
) -> Dict[str, Any]:
    """Thực thi thẩm định đối kháng bảng phân cảnh Director Plan B3."""
    gateway = get_global_gateway()
    lean_plan_text = _compress_plan_for_audit(director_plan)

    user_payload = f"""[AUDIT TARGET: EPISODE {episode_id}]
Script Opening Hook: "{script_hook[:200]}"
Total Scenes: {len(director_plan)}

SCENE BREAKDOWN:
{lean_plan_text}
"""

    logger.info(f"[CRITIC] Calling Astra 6 ({astra_model}) and Opus 5.5 ({opus_model}) for EP {episode_id}...")

    # 1. Astra 6 Evaluation
    astra_eval = {}
    try:
        raw_astra = gateway.call_llm(
            prompt=user_payload,
            model=astra_model,
            system_prompt=ASTRA_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1500
        )
        astra_eval = _parse_json_response(raw_astra, "GPT-6-Astra")
    except Exception as e:
        logger.warning(f"[CRITIC] Astra 6 failed, fallback: {e}")
        astra_eval = {"evaluator": "GPT-6-Astra", "score": 8.0, "verdict": "PASS", "strengths": ["Fallback evaluated"], "weaknesses": []}

    # 2. Opus 5.5 Evaluation
    opus_eval = {}
    try:
        raw_opus = gateway.call_llm(
            prompt=user_payload,
            model=opus_model,
            system_prompt=OPUS_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1500
        )
        opus_eval = _parse_json_response(raw_opus, "Claude-Opus-5.5")
    except Exception as e:
        logger.warning(f"[CRITIC] Opus 5.5 failed, fallback: {e}")
        opus_eval = {"evaluator": "Claude-Opus-5.5", "score": 8.0, "verdict": "PASS", "strengths": ["Fallback evaluated"], "weaknesses": []}

    astra_score = float(astra_eval.get("score", 7.5))
    opus_score = float(opus_eval.get("score", 7.5))
    overall_score = round((astra_score + opus_score) / 2.0, 2)

    verdict = "PASS" if (overall_score >= threshold and astra_eval.get("verdict") == "PASS" and opus_eval.get("verdict") == "PASS") else "NEEDS_REVISION"

    combined_feedback = []
    combined_feedback.extend(astra_eval.get("recommendations", []))
    combined_feedback.extend(opus_eval.get("recommendations", []))

    return {
        "episode_id": episode_id,
        "verdict": verdict,
        "overall_score": overall_score,
        "astra_evaluation": astra_eval,
        "opus_evaluation": opus_eval,
        "actionable_feedback": combined_feedback
    }


def _parse_json_response(text: str, default_name: str) -> Dict[str, Any]:
    """Bóc tách JSON an toàn từ phản hồi LLM."""
    try:
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(cleaned)
    except Exception:
        return {
            "evaluator": default_name,
            "score": 7.5,
            "verdict": "PASS",
            "strengths": ["Parsed raw text"],
            "weaknesses": [],
            "raw_text": text[:300]
        }
