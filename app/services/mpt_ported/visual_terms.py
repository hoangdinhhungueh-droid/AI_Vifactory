
"""MPT-G3-4 - LLM-based visual term extractor."""
import asyncio, json, os, re
from typing import Optional
import httpx
from app.services.skill_loader import get_skill_rules

LLM_ENDPOINT = os.getenv("VF_API_URL", "http://localhost:8000") + "/api/v1/llm"
LLM_API_KEY  = os.getenv("VF_API_KEY", "")

SYSTEM_PROMPT = """You are a visual director AI. For each sentence in the input,
extract a short visual search term suitable for stock footage.
Respond ONLY with a JSON array, no markdown:
[{"sentence": "...", "visual_term": "...", "duration_s": 5.0, "media_type": "video"}]
media_type is "video" or "photo". duration_s should match the sentence length (~1s per 3 words, min 3)."""


async def extract_visual_terms(
    text: str,
    lang_code: str = "en",
    max_segments: int = 60,
) -> list:
    """
    Returns list of {sentence, visual_term, duration_s, media_type}.
    Uses VPS LLM router (/api/v1/llm).
    """
    # B6: Load Skill AI rules (cache 1h, aligned with B1/B2/B3/B3.5/B4/B5)
    skill_rules = get_skill_rules()
    
    # Split into sentences (simple heuristic)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if len(s) > 5][:max_segments]
    batch = " | ".join(sentences)

    system_with_rules = SYSTEM_PROMPT + "\n\n" + skill_rules
    
    payload = {
        "prompt": batch,
        "task_type": "S3_visual_terms",
        "system": system_with_rules,
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["X-API-Key"] = LLM_API_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(LLM_ENDPOINT, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            raw = data.get("text", "")

            # Extract JSON array from response
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                raise ValueError(f"No JSON array in LLM response: {raw[:200]}")
            terms = json.loads(match.group())
            # Validate + fill defaults
            result = []
            for item in terms:
                result.append({
                    "sentence":    item.get("sentence", ""),
                    "visual_term": item.get("visual_term", item.get("sentence", "")[:30]),
                    "duration_s":  float(item.get("duration_s", 5.0)),
                    "media_type":  item.get("media_type", "video"),
                })
            return result
        except Exception as e:
            print(f"[visual_terms] LLM failed: {e} — returning sentence fallback")
            # Fallback: use sentences directly as visual terms
            return [
                {"sentence": s, "visual_term": s[:40], "duration_s": max(3.0, len(s.split()) / 3),
                 "media_type": "video"}
                for s in sentences
            ]
