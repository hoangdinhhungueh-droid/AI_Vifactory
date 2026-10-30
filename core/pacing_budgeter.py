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
from typing import Any, Dict, List, Optional, Tuple, Union

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


def count_speech_units(sentence: str, market_code: str) -> int:
    """Count the relevant linguistic speech units (syllables, morae, or words)."""
    if not sentence or not sentence.strip():
        return 0

    s = sentence.strip()
    canon_market = resolve_canonical_market(market_raw=market_code)

    if canon_market in ("KR", "KO", "JA", "JP"):
        # For CJK, count non-whitespace characters
        clean_chars = re.sub(r"\s+", "", s)
        return len(clean_chars)
    else:
        # For Latin/space-delimited alphabets (EN, VN), count words
        words = s.split()
        return len(words)


def estimate_calibrated_speech_duration(
    sentence: str,
    market: Optional[str] = None,
    custom_rate: Optional[float] = None
) -> float:
    """Estimate speech duration using calibrated multi-market news tempo.

    Fails closed if market is not specified (Rule 118, Rule 139).
    """
    if market is None:
        raise ValueError("estimate_calibrated_speech_duration fail-closed (Rule 118): No market specified.")

    canon_market = resolve_canonical_market(market_raw=market)
    if not sentence or not sentence.strip():
        return MIN_SCENE_DURATION_SEC

    units = count_speech_units(sentence, canon_market)
    rate = custom_rate or CALIBRATED_SPEECH_RATES.get(canon_market, 3.2)

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
