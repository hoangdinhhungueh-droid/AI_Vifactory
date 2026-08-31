"""AI Story Judge (outline stage) - LLM semantic check to catch what regex
gates (story_gate.py) cannot: AI-cliche tone, missing narrative technique
(callback / twist / reveal), formulaic repetition, editorial perspective.

Runs AFTER the deterministic story_gate (S3.6) and BEFORE TTS, so a weak
script is still cheap to rewrite. Added 05/08/2026 per Hand-off audit
(Task/Viec 2) - scope is story quality only, does NOT touch discovery/scoring.

v4 update 07/08/2026 (Phase 3): expanded banned-phrase list (checklist A),
added editorial_perspective as 4th LLM axis, made technique axis explicit
about callback + twist/reveal (pattern interrupt now handled by story_gate v4).

Public API:
    judge_mode() -> "off" | "warn" | "block"   (env VF_STORY_JUDGE, default "warn")
    judge_story(story_text) -> dict with verdict/scores/notes
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

from app.llm_router import llm_call
from app.services.skill_loader import get_skill_rules

logger = logging.getLogger(__name__)

BANNED_PHRASES = [
    "in a world where", "delve", "tapestry", "unravel the mystery",
    "little did they know", "the rest is history", "at the end of the day",
    "when it comes to", "in today's world", "it is important to note",
    "a testament to", "boasts a", "stands as a", "plays a crucial role",
    "in conclusion", "navigate the complexities",
    # Checklist A expansion (Phase 3, 07/08/2026):
    "let's dive in", "it's worth noting", "unleash", "boundless",
    "the truth is", "unravel", "underscore",
]

LOG_PATH = "/root/video_factory/logs/story_judge_log.jsonl"

SYSTEM_PROMPT = (
    "You are a strict story-quality judge for a faceless YouTube documentary "
    "channel. You grade a finished outline/script against four axes and "
    "return STRICT JSON only, no markdown, no preamble."
)


def judge_mode() -> str:
    v = (os.getenv("VF_STORY_JUDGE", "warn") or "warn").strip().lower()
    return v if v in ("off", "warn", "block") else "warn"


def _banned_hits(text: str) -> list:
    low = text.lower()
    return [p for p in BANNED_PHRASES if p in low]


def _repeated_openers(text: str, min_count: int = 3) -> list:
    """Flag sentence-opener phrases repeated >= min_count times (formulaic tell)."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    openers = {}
    for s in sents:
        head = " ".join(s.split()[:3]).lower().strip(".,:;")
        if len(head) < 6:
            continue
        openers[head] = openers.get(head, 0) + 1
    return [k for k, c in openers.items() if c >= min_count]


def judge_story(story_text: str, episode_id: str = "") -> dict:
    story = story_text or ""
    banned = _banned_hits(story)
    repeated = _repeated_openers(story)

    # B7: Load Skill AI rules (cache 1h, aligned with B1/B2/B3/B3.5/B4/B5/B6)
    skill_rules = get_skill_rules()
    system_with_rules = SYSTEM_PROMPT + "\n\n" + skill_rules

    prompt = (
        "Grade this documentary voice-over script on 4 axes, 0-2 each "
        "(0=fail, 1=weak, 2=solid):\n"
        "1) anti_ai_tone - free of generic AI-cliche phrasing and robotic "
        "transitions (beyond the banned-phrase list already checked by code).\n"
        "2) technique - must contain at least one callback (a detail from "
        "Hook or Act 1 deliberately revisited in Act 3 or Payoff) AND at "
        "least one twist/reveal (a reversal of expectation built earlier, "
        "occurring in Mechanism or Collapse). Pattern interrupt (short "
        "sentences) is already checked by the regex gate.\n"
        "3) freshness - does not feel like a templated retelling; specific, "
        "concrete details rather than generic summary.\n"
        "4) editorial_perspective - each of the 5 acts (hook-shock / build / "
        "knot / resolution / denouement) contains at least one sentence with "
        "a clear analytical or editorial viewpoint, not just reporting facts.\n\n"
        "Known code-detected banned phrases already found: %s\n"
        "Known repeated sentence-openers (formulaic tell): %s\n\n"
        "SCRIPT:\n%s\n\n"
        "Return STRICT JSON only in exactly this shape:\n"
        '{"anti_ai_tone": <0-2>, "technique": <0-2>, "freshness": <0-2>, '
        '"editorial_perspective": <0-2>, "techniques_used": "<names or none>", '
        '"notes": "<1-2 sentence rationale>"}'
    ) % (banned or "none", repeated or "none", story[:6000])

    result = {
        "episode_id": episode_id,
        "banned_phrases_found": banned,
        "repeated_openers": repeated,
        "llm_ok": False,
    }

    try:
        res = llm_call(prompt, task_type="S3_story_judge", system=system_with_rules,
                        expect_json=True)
        raw = (res.get("text") or "").strip().strip("`").strip()
        parsed = json.loads(raw)
        a = int(parsed.get("anti_ai_tone", 0))
        t = int(parsed.get("technique", 0))
        f = int(parsed.get("freshness", 0))
        e = int(parsed.get("editorial_perspective", 0))
        result.update({
            "llm_ok": True,
            "model": res.get("model"),
            "anti_ai_tone": a,
            "technique": t,
            "freshness": f,
            "editorial_perspective": e,
            "techniques_used": parsed.get("techniques_used", ""),
            "notes": parsed.get("notes", ""),
            "score": a + t + f + e,
            "max_score": 8,
        })
    except Exception as exc:
        logger.warning("[S3.65] story judge LLM failed, fail-open: %s", exc)
        result.update({"score": None, "max_score": 8, "notes": f"LLM error: {exc}"})

    # Hard-fail on code-detected banned phrases regardless of LLM output.
    if banned:
        result["verdict"] = "FAIL"
    elif result.get("score") is None:
        # LLM unavailable -> do not block on this axis alone (fail-open).
        result["verdict"] = "SKIP"
    else:
        result["verdict"] = "PASS" if result["score"] >= 5 else "FAIL"

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({"ts": time.time(), **result}, ensure_ascii=False) + "\n")
    except Exception as _e:
        logger.warning("[S3.65] story judge log write failed: %s", _e)

    return result
