"""Story narration segmenter: splits long narration text into CPS-appropriate segments.

Prevents the '3 lines on 2 frames' problem (user feedback Aug 8 2026) by ensuring
each narration segment fits within the CPS cap for its scene duration. If text is
too long, either:
1. Splits into multiple shorter segments (each a complete sentence/clause)
2. Recommends extending the scene duration
3. Recommends splitting into multiple scenes with the same background

Used before TTS to ensure narration text is properly segmented.

Rule 75 (Skill AI): Story segmentation before TTS -- no narration segment
may exceed CPS cap for its scene duration.
"""
import os
import re
from typing import List, Tuple

# CPS cap (characters per second) -- should match subtitle_karaoke.py
CPS_CAP = float(os.getenv("SUBTITLE_CPS_CAP", "20"))
# Max characters per subtitle line (matches subtitle_karaoke.py MAX_LINE_CHARS)
MAX_LINE_CHARS = int(os.getenv("SUBTITLE_MAX_LINE_CHARS", "42"))
# Max lines per subtitle cue (2 lines visible at once)
MAX_LINES_PER_CUE = 2
# Max characters per cue (2 lines x 42 chars)
MAX_CUE_CHARS = MAX_LINE_CHARS * MAX_LINES_PER_CUE
# Max words per segment before forced split
MAX_WORDS_PER_SEGMENT = int(os.getenv("STORY_MAX_WORDS_PER_SEGMENT", "18"))


def estimate_cps(text: str, duration_sec: float) -> float:
    """Estimate characters per second for a text segment."""
    chars = len(text.replace("\n", ""))
    if duration_sec <= 0:
        return float("inf")
    return chars / duration_sec


def fits_cps(text: str, duration_sec: float) -> bool:
    """Check if text fits within CPS cap for the given duration."""
    return estimate_cps(text, duration_sec) <= CPS_CAP


def min_duration_for_text(text: str) -> float:
    """Calculate minimum duration needed for text at CPS cap."""
    chars = len(text.replace("\n", ""))
    return chars / CPS_CAP if CPS_CAP > 0 else float(chars)


def fits_screen(text: str) -> bool:
    """Check if text fits on screen (max 2 lines x 42 chars)."""
    return len(text.replace("\n", "")) <= MAX_CUE_CHARS


def split_sentences(text: str, max_words: int = None) -> List[str]:
    """Split text into sentences, further splitting long ones at natural break points."""
    if max_words is None:
        max_words = MAX_WORDS_PER_SEGMENT
    text = text.strip()
    if not text:
        return []
    # Split on sentence endings
    sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z])", text)
    result = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        wc = len(s.split())
        if wc > max_words:
            words = s.split()
            split_done = False
            for i in range(max(8, max_words - 5), len(words)):
                if words[i].endswith(",") or words[i].endswith("--") or \
                   words[i].endswith(":") or words[i].endswith(";") or \
                   words[i].endswith("..."):
                    result.append(" ".join(words[:i + 1]))
                    rest = " ".join(words[i + 1:])
                    if rest:
                        result.extend(split_sentences(rest, max_words))
                    split_done = True
                    break
            if not split_done:
                # Hard split at max_words
                for i in range(0, len(words), max_words):
                    chunk = " ".join(words[i:i + max_words])
                    if chunk:
                        result.append(chunk)
        else:
            result.append(s)
    return result


def segment_narration(text: str, duration_sec: float) -> Tuple[List[dict], float]:
    """
    Segment narration text for a scene.

    Returns:
        (segments, recommended_duration)
        segments: list of {text, start_ms, end_ms, cps}
        recommended_duration: minimum duration needed (may exceed input duration)
    """
    if not text or not text.strip():
        return ([], duration_sec)

    text = text.strip()

    # Check if entire text fits both CPS and screen space
    if fits_cps(text, duration_sec) and fits_screen(text):
        return ([{
            "text": text,
            "start_ms": 0,
            "end_ms": int(duration_sec * 1000),
            "cps": estimate_cps(text, duration_sec),
        }], duration_sec)

    # Need to split
    sentences = split_sentences(text)

    # Calculate minimum total duration
    min_total = min_duration_for_text(text)

    if min_total <= duration_sec:
        # Text fits if we split it -- distribute proportionally
        total_words = sum(len(s.split()) for s in sentences)
        segments = []
        t = 0.0
        for s in sentences:
            wc = len(s.split())
            dur = (wc / total_words) * duration_sec if total_words > 0 else duration_sec / len(sentences)
            segments.append({
                "text": s,
                "start_ms": int(t * 1000),
                "end_ms": int((t + dur) * 1000),
                "cps": estimate_cps(s, dur),
            })
            t += dur
        return (segments, duration_sec)
    else:
        # Text doesn't fit even with splitting -- recommend longer duration
        total_words = sum(len(s.split()) for s in sentences)
        segments = []
        t = 0.0
        for s in sentences:
            wc = len(s.split())
            dur = (wc / total_words) * min_total if total_words > 0 else min_total / len(sentences)
            segments.append({
                "text": s,
                "start_ms": int(t * 1000),
                "end_ms": int((t + dur) * 1000),
                "cps": estimate_cps(s, dur),
            })
            t += dur
        return (segments, min_total)


def segment_scenes(scenes: list) -> list:
    """
    Process a list of scenes (from brain_input.json) and segment their narration.

    For each scene:
    - If narration fits within duration, keep as-is
    - If narration is too long, split into segments and extend duration
    - Returns new scenes list with segmented narration

    Each input scene may produce multiple output scenes (same background).
    """
    output = []
    for s in scenes:
        narration = (s.get("narration") or "").strip()
        dur = float(s.get("duration_sec") or 4.0)

        if not narration:
            output.append(s)
            continue

        segments, rec_dur = segment_narration(narration, dur)

        if len(segments) <= 1:
            # Fits in one scene
            s_copy = dict(s)
            if rec_dur > dur:
                s_copy["duration_sec"] = round(rec_dur, 1)
                s_copy["_cps_extended"] = True
                s_copy["_cps_original_dur"] = dur
            output.append(s_copy)
        else:
            # Need multiple scenes with same background
            for i, seg in enumerate(segments):
                s_copy = dict(s)
                s_copy["narration"] = seg["text"]
                seg_dur = (seg["end_ms"] - seg["start_ms"]) / 1000.0
                s_copy["duration_sec"] = round(seg_dur, 1)
                s_copy["_segment_index"] = i
                s_copy["_segment_total"] = len(segments)
                if rec_dur > dur:
                    s_copy["_cps_extended"] = True
                    s_copy["_cps_original_dur"] = dur
                output.append(s_copy)

    return output


def audit_scenes(scenes: list) -> dict:
    """
    Audit scenes for CPS violations. Returns report dict.
    Useful for preflight_render_gate or debugging.
    """
    violations = []
    for i, s in enumerate(scenes):
        narration = (s.get("narration") or "").strip()
        dur = float(s.get("duration_sec") or 4.0)
        if not narration:
            continue
        cps = estimate_cps(narration, dur)
        if cps > CPS_CAP:
            violations.append({
                "scene_index": i,
                "cps": round(cps, 1),
                "duration_sec": dur,
                "text_len": len(narration),
                "text_preview": narration[:80],
            })
    return {
        "total_scenes": len(scenes),
        "violations": violations,
        "violation_count": len(violations),
        "cps_cap": CPS_CAP,
        "max_line_chars": MAX_LINE_CHARS,
        "max_cue_chars": MAX_CUE_CHARS,
    }
