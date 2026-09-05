"""MPT-G3-4 - Legacy visual term extractor (Deprecated - Pure local fallback)."""
import re

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
    DEPRECATED: Rule 116 Go-Live uses Antigravity 2-layer image generation.
    Returns instant sentence-based fallback without external LLM or network calls.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if len(s) > 5][:max_segments]
    return [
        {
            "sentence": s,
            "visual_term": s[:40],
            "duration_s": max(3.0, len(s.split()) / 3),
            "media_type": "video",
        }
        for s in sentences
    ]
