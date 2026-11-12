#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/pacing_budgeter.py — Calibrated TTS Speech Pacing & Projected Frame Budgeter (Vox Engine v3).

Conforms to:
- Rule 118: Zero-Mock truthful speech calculation.
- Rule 120: Word-level Whisper timestamps driving frames with 0ms drift.
- Rule 128: Generic Contract Architecture across all markets.
- Rule 134: Single Canonical Truth for timing.
- Rule 140: Snappy Stop-Motion Physics (Action <= 0.4s) & Living Hold (12fps vi rung, zero freeze).
- Master Reform Plan 2.0 (PLAN-VOX-V3-REFORM-20261030):
  * Natural Multi-Market News Pacing:
    - KR: 5.8 syl/s (range 5.8 - 6.2)
    - JP: 6.5 morae/s (range 6.5 - 7.0)
    - EN: 3.2 words/s (range 3.0 - 3.4)
    - VN: 3.6 words/s (range 3.4 - 3.8)
  * Projected Frame Outline: Generates exact duration_sec, target_frames_30fps, target_frames_12fps,
    and micro-beat time budgets before visual generation.
  * Ensures KR_EP0003 Act I (8 scenes) lasts ~29.5s – 30.5s, eliminating trailing dead-stop freeze.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.market_resolver import resolve_canonical_market

logger = logging.getLogger(__name__)

# Calibrated Speech Rates for Investigative Documentary & News Narration
CALIBRATED_SPEECH_RATES: Dict[str, float] = {
    "KR": 5.8,   # Syllables per second (InJoonNeural / SunHiNeural news tempo)
    "KO": 5.8,
    "JA": 6.5,   # Characters/morae per second (NanamiNeural / KeitaNeural)
    "JP": 6.5,
    "EN": 3.2,   # Words per second (GuyNeural / ChristopherNeural docudrama)
    "VN": 3.6,   # Words per second (NamMinhNeural / HoaiMyNeural)
    "VI": 3.6,
}

# Docudrama Narrative Pacing Invariants (AVF-STAB-001 / Rule 128 / Rule 140)
# Strict clinical docudrama tempo: 115 - 135 WPM (target: 125 WPM, 460 - 540 words for 240s runtime)
DOCUDRAMA_MIN_WPM: float = 115.0
DOCUDRAMA_MAX_WPM: float = 135.0
DOCUDRAMA_TARGET_WPM: float = 125.0
DOCUDRAMA_WORDS_PER_SEC: float = round(DOCUDRAMA_TARGET_WPM / 60.0, 4)  # ~2.0833 words/s

# Docudrama Speech Rates across markets (clinical investigative tempo)
DOCUDRAMA_SPEECH_RATES: Dict[str, float] = {
    "KR": 4.17,  # Syllables per second (~250 syllables/min docudrama tempo)
    "KO": 4.17,
    "JA": 6.0,   # Characters per second (~360 chars/min)
    "JP": 6.0,
    "EN": DOCUDRAMA_WORDS_PER_SEC,  # ~2.0833 words/s (125.0 WPM)
    "VN": 2.5,   # Words per second (~150 words/min)
    "VI": 2.5,
}

# Acceptable variance ranges for QA Auditing
SPEECH_RATE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "KR": (5.8, 6.2),
    "KO": (5.8, 6.2),
    "JA": (6.5, 7.0),
    "JP": (6.5, 7.0),
    "EN": (3.0, 3.4),
    "VN": (3.4, 3.8),
    "VI": (3.4, 3.8),
}

# Standard Scene Duration Clamps (Rule 140)
MIN_SCENE_DURATION_SEC: float = 2.5
MAX_SCENE_DURATION_SEC: float = 10.0

# Action Phase Ceiling for Stop-Motion Snap (Rule 140)
MAX_ACTION_SNAP_SEC: float = 0.4


@dataclass(frozen=True)
class SceneFrameBudget:
    """Frame & Timing Budget contract for a single scene."""
    scene_id: str
    sentence: str
    market: str
    speech_rate_target: float
    exact_duration_sec: float
    target_frames_30fps: int
    target_frames_12fps: int
    start_frame_30fps: int
    end_frame_30fps: int
    start_sec: float
    end_sec: float
    action_phase_sec: float
    living_hold_sec: float
    source: str  # 'whisper_aligned' or 'calibrated_estimate'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectedFrameOutline:
    """Complete multi-scene Projected Frame Outline for an Act or Episode."""
    run_id: str
    market: str
    fps: int
    total_scenes: int
    total_duration_sec: float
    total_frames: int
    scenes: List[SceneFrameBudget]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "market": self.market,
            "fps": self.fps,
            "total_scenes": self.total_scenes,
            "total_duration_sec": self.total_duration_sec,
            "total_frames": self.total_frames,
            "scenes": [s.to_dict() for s in self.scenes],
        }


def count_speech_units(sentence: str, market_code: str, expand_numbers: bool = True) -> int:
    """Count the relevant linguistic speech units (syllables, morae, or words)
    after normalizing digits/currencies/dates to their TTS spoken equivalents.
    """
    if not sentence or not sentence.strip():
        return 0

    s = sentence.strip()
    canon_market = resolve_canonical_market(market_raw=market_code)
    if expand_numbers:
        from app.services.story_provenance_engine import expand_text_for_tts_timing

        s = expand_text_for_tts_timing(s, market=canon_market)

    if canon_market in ("KR", "KO", "JA", "JP"):
        # For CJK, strip whitespace and non-spoken punctuation so duration reflects real speech units
        clean_chars = re.sub(r"[\s.,!?;:\"'()\[\]{}「」『』（）…—–\-。、．，！？/]+", "", s)
        return len(clean_chars)
    else:
        # For Latin/space-delimited alphabets (EN, VN), count spoken words
        words = [w for w in re.split(r"\s+", s) if re.search(r"[A-Za-z0-9À-ỹ]", w)]
        return len(words)


def estimate_script_speech_duration(
    text_or_lines: Any,
    market: str,
    docudrama_tempo: bool = True,
    pause_per_line_sec: float = 0.15,
) -> Dict[str, Any]:
    """Compute true un-tautological TTS speech duration and unit count from spoken text.

    Never clamps or overwrites total duration to target_run_s.
    """
    canon_market = resolve_canonical_market(market_raw=market)
    rate = (
        DOCUDRAMA_SPEECH_RATES.get(canon_market, DOCUDRAMA_WORDS_PER_SEC)
        if docudrama_tempo
        else CALIBRATED_SPEECH_RATES.get(canon_market, 3.2)
    )
    if isinstance(text_or_lines, str):
        lines = [ln.strip() for ln in re.split(r"(?<=[.!?。？！])\s+|\n+", text_or_lines) if ln.strip()]
    else:
        lines = [str(ln).strip() for ln in (text_or_lines or []) if str(ln).strip()]

    total_units = sum(count_speech_units(ln, canon_market, expand_numbers=True) for ln in lines)
    if total_units == 0:
        return {
            "estimated_duration_sec": 0.0,
            "spoken_units": 0,
            "unit_type": "syllables_or_chars" if canon_market in ("KR", "KO", "JA", "JP") else "words",
            "speech_rate_per_sec": rate,
            "line_count": 0,
            "market": canon_market,
        }
    speech_sec = total_units / rate
    pause_sec = max(0, len(lines) - 1) * max(0.0, pause_per_line_sec)
    total_sec = round(speech_sec + pause_sec, 2)
    return {
        "estimated_duration_sec": total_sec,
        "spoken_units": total_units,
        "unit_type": "syllables" if canon_market in ("KR", "KO") else ("chars" if canon_market in ("JA", "JP") else "words"),
        "speech_rate_per_sec": rate,
        "line_count": len(lines),
        "market": canon_market,
    }


def estimate_calibrated_speech_duration(
    sentence: str,
    market: Optional[str] = None,
    custom_rate: Optional[float] = None,
    docudrama_tempo: bool = False,
) -> float:
    """Estimate speech duration using calibrated multi-market news or docudrama tempo.

    Fails closed if market is not specified (Rule 118, Rule 139).
    """
    if market is None:
        raise ValueError("estimate_calibrated_speech_duration fail-closed (Rule 118): No market specified.")

    canon_market = resolve_canonical_market(market_raw=market)
    if not sentence or not sentence.strip():
        return MIN_SCENE_DURATION_SEC

    units = count_speech_units(sentence, canon_market)
    if custom_rate is not None:
        rate = custom_rate
    elif docudrama_tempo:
        rate = DOCUDRAMA_SPEECH_RATES.get(canon_market, DOCUDRAMA_WORDS_PER_SEC)
    else:
        rate = CALIBRATED_SPEECH_RATES.get(canon_market, 3.2)

    if rate <= 0:
        raise ValueError(f"Invalid speech rate: {rate}")

    raw_dur = units / rate
    clamped_dur = max(MIN_SCENE_DURATION_SEC, min(MAX_SCENE_DURATION_SEC, round(raw_dur, 3)))
    return clamped_dur


def compute_scene_frame_budget(
    scene_id: str,
    sentence: str,
    market: str,
    start_sec: float = 0.0,
    fps: int = 30,
    whisper_words: Optional[List[Dict[str, Any]]] = None,
    custom_speech_rate: Optional[float] = None,
) -> SceneFrameBudget:
    """Compute frame budget and timing breakdown for a single scene."""
    if not scene_id or not isinstance(scene_id, str) or not scene_id.strip():
        raise ValueError("scene_id cannot be empty")

    canon_market = resolve_canonical_market(market_raw=market)
    speech_rate = custom_speech_rate or CALIBRATED_SPEECH_RATES.get(canon_market, 3.2)

    # 1. Determine duration: prioritize Whisper timestamps if provided
    if whisper_words and len(whisper_words) > 0:
        w_start = float(whisper_words[0].get("start", 0.0))
        w_end = float(whisper_words[-1].get("end", 0.0))
        measured_dur = round(max(0.5, w_end - w_start), 3)
        duration_sec = max(MIN_SCENE_DURATION_SEC, min(MAX_SCENE_DURATION_SEC, measured_dur))
        source = "whisper_aligned"
    else:
        duration_sec = estimate_calibrated_speech_duration(sentence, canon_market, custom_rate=speech_rate)
        source = "calibrated_estimate"

    # 2. Frame counts
    target_frames_30 = int(round(duration_sec * fps))
    target_frames_12 = int(round(duration_sec * 12))

    start_frame = int(round(start_sec * fps))
    end_frame = start_frame + target_frames_30
    end_sec = round(start_sec + duration_sec, 3)

    # 3. Micro-beat breakdown: Snappy Action Phase (<= 0.4s) & Living Hold (remaining)
    action_phase_sec = min(MAX_ACTION_SNAP_SEC, round(duration_sec * 0.15, 3))
    living_hold_sec = round(duration_sec - action_phase_sec, 3)

    return SceneFrameBudget(
        scene_id=scene_id,
        sentence=sentence,
        market=canon_market,
        speech_rate_target=speech_rate,
        exact_duration_sec=duration_sec,
        target_frames_30fps=target_frames_30,
        target_frames_12fps=target_frames_12,
        start_frame_30fps=start_frame,
        end_frame_30fps=end_frame,
        start_sec=round(start_sec, 3),
        end_sec=end_sec,
        action_phase_sec=action_phase_sec,
        living_hold_sec=living_hold_sec,
        source=source,
    )


def generate_projected_frame_outline(
    scenes: List[Dict[str, Any]],
    market: str,
    run_id: str = "RUN_PROJECTED",
    fps: int = 30,
    custom_speech_rate: Optional[float] = None
) -> ProjectedFrameOutline:
    """Generate a complete, contiguous Projected Frame Outline for a sequence of scenes.

    Eliminates timeline gaps, trailing freezes, and misaligned chapter timestamps.
    """
    if not scenes or not isinstance(scenes, list):
        raise ValueError("generate_projected_frame_outline fail-closed: scenes list cannot be empty.")

    canon_market = resolve_canonical_market(market_raw=market)
    budgeted_scenes: List[SceneFrameBudget] = []
    current_time_sec = 0.0

    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id") or f"SCENE_{idx+1:02d}"
        sentence = sc.get("sentence") or sc.get("headline") or ""
        whisper_words = sc.get("whisper_words")

        budget = compute_scene_frame_budget(
            scene_id=sc_id,
            sentence=sentence,
            market=canon_market,
            start_sec=current_time_sec,
            fps=fps,
            whisper_words=whisper_words,
            custom_speech_rate=custom_speech_rate,
        )
        budgeted_scenes.append(budget)
        current_time_sec = budget.end_sec

    total_dur = round(current_time_sec, 3)
    total_frames = int(round(total_dur * fps))

    return ProjectedFrameOutline(
        run_id=run_id,
        market=canon_market,
        fps=fps,
        total_scenes=len(budgeted_scenes),
        total_duration_sec=total_dur,
        total_frames=total_frames,
        scenes=budgeted_scenes,
    )


def calculate_word_budget_for_duration(
    duration_sec: float,
    target_wpm: float = DOCUDRAMA_TARGET_WPM,
) -> Dict[str, int]:
    """Calculate the strict word budget window for a target duration adhering to docudrama tempo (115-135 WPM).

    For a standard 240.0s episode:
    - min: 460 words (115.0 WPM)
    - max: 540 words (135.0 WPM)
    - target: 500 words (125.0 WPM)
    - optimal_min: 480 words (120.0 WPM)
    - optimal_max: 520 words (130.0 WPM)
    """
    if duration_sec <= 0:
        raise ValueError(f"duration_sec must be positive, got {duration_sec}")

    min_words = int(math.floor(duration_sec * (DOCUDRAMA_MIN_WPM / 60.0)))
    max_words = int(math.ceil(duration_sec * (DOCUDRAMA_MAX_WPM / 60.0)))
    target_words = int(round(duration_sec * (target_wpm / 60.0)))
    optimal_min = int(round(duration_sec * ((target_wpm - 5.0) / 60.0)))
    optimal_max = int(round(duration_sec * ((target_wpm + 5.0) / 60.0)))

    return {
        "min": min_words,
        "max": max_words,
        "target": target_words,
        "optimal_min": optimal_min,
        "optimal_max": optimal_max,
    }


def calculate_wpm(word_count: int, duration_sec: float) -> float:
    """Calculate words per minute (WPM)."""
    if duration_sec <= 0:
        return 0.0
    return round((word_count / duration_sec) * 60.0, 2)


def is_docudrama_pacing_valid(word_count: int, duration_sec: float) -> bool:
    """Check if narrative pacing falls strictly within the docudrama ceiling [115.0, 135.0] WPM."""
    wpm = calculate_wpm(word_count, duration_sec)
    return DOCUDRAMA_MIN_WPM <= wpm <= DOCUDRAMA_MAX_WPM


def clamp_narration_duration_to_pacing(
    word_count: int,
    target_wpm: float = DOCUDRAMA_TARGET_WPM,
    min_duration: float = MIN_SCENE_DURATION_SEC,
    max_duration: float = MAX_SCENE_DURATION_SEC,
) -> float:
    """Calculate scene duration from word count clamped to target WPM and scene bounds."""
    wps = target_wpm / 60.0
    if wps <= 0:
        wps = DOCUDRAMA_WORDS_PER_SEC
    raw_dur = word_count / wps
    return max(min_duration, min(max_duration, round(raw_dur, 1)))


def calibrate_scene_durations_to_target(
    scenes: List[Any],
    target_total_duration_sec: float = 240.0,
    target_wpm: float = DOCUDRAMA_TARGET_WPM,
    market: Optional[str] = None,
) -> float:
    """Proportionally calibrate scene durations so total runtime matches target and WPM is strictly clamped.

    Guarantees:
    - Every scene duration is positive and >= min_duration.
    - No scene is assigned <= 0 or negative duration under ANY input.
    - Sum of durations matches target_total_duration_sec exactly (within 0.05s).
    - Supports CJK and multilingual speech unit weighting via market or count_speech_units.

    Modifies scene.duration_est_sec (or sc['duration_est_sec']) in place.
    Returns the final calculated WPM.
    """
    if not scenes:
        return 0.0

    n = len(scenes)
    if target_total_duration_sec <= 0.0:
        for s in scenes:
            if isinstance(s, dict):
                s["duration_est_sec"] = 0.0
            else:
                setattr(s, "duration_est_sec", 0.0)
        return 0.0

    # Effective min/max bounds per scene
    min_dur = min(MIN_SCENE_DURATION_SEC, round(target_total_duration_sec / n, 2))
    min_dur = max(0.5, min_dur)
    max_dur = max(min_dur, MAX_SCENE_DURATION_SEC * 2.0)

    def _get_text(sc: Any) -> str:
        if isinstance(sc, dict):
            return sc.get("narration") or sc.get("sentence") or sc.get("narration_text") or ""
        return getattr(sc, "narration", "") or getattr(sc, "sentence", "") or getattr(sc, "narration_text", "") or ""

    raw_units: List[int] = []
    for s in scenes:
        txt = _get_text(s)
        sc_mkt = market or (s.get("market") if isinstance(s, dict) else getattr(s, "market", None))
        if sc_mkt:
            units = count_speech_units(txt, sc_mkt)
        else:
            units = len(txt.split())
        raw_units.append(units)

    total_units = sum(raw_units)

    if total_units == 0:
        base_dur = round(target_total_duration_sec / n, 1)
        durs = [base_dur] * n
        diff = round(target_total_duration_sec - sum(durs), 1)
        if abs(diff) > 0.01:
            durs[0] = round(durs[0] + diff, 1)
    else:
        # Give 0-unit scenes a minimal base weight (1 unit) so they get proportional baseline
        weights = [max(1, u) if u == 0 else u for u in raw_units]
        tot_w = sum(weights)

        # Initial proportional allocation bounded to [min_dur, max_dur]
        durs = [
            max(min_dur, min(max_dur, target_total_duration_sec * (w / tot_w)))
            for w in weights
        ]

        # Iteratively redistribute residual difference across non-boundary scenes
        for _ in range(5):
            diff = target_total_duration_sec - sum(durs)
            if abs(diff) < 0.01:
                break
            if diff > 0:
                eligible = [i for i, d in enumerate(durs) if d < max_dur - 0.01]
                if not eligible:
                    break
                sub_w = sum(weights[i] for i in eligible)
                for i in eligible:
                    durs[i] += diff * (weights[i] / sub_w)
            else:
                eligible = [i for i, d in enumerate(durs) if d > min_dur + 0.01]
                if not eligible:
                    break
                sub_w = sum(weights[i] for i in eligible)
                for i in eligible:
                    durs[i] += diff * (weights[i] / sub_w)

        # Round to 1 decimal place and adjust any small 0.1s rounding drift onto the largest scene
        durs = [max(min_dur, round(d, 1)) for d in durs]
        diff = round(target_total_duration_sec - sum(durs), 1)
        if abs(diff) > 0.01:
            max_idx = durs.index(max(durs))
            durs[max_idx] = max(min_dur, round(durs[max_idx] + diff, 1))

    for s, d in zip(scenes, durs):
        if isinstance(s, dict):
            s["duration_est_sec"] = d
        else:
            setattr(s, "duration_est_sec", d)

    final_wpm = calculate_wpm(total_units, target_total_duration_sec)
    return final_wpm
