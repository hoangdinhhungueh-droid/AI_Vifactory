#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/helpers/synthetic_alignment_helper.py — Test-Only Alignment Helper (Rule 118 Isolation).

Strictly isolated in tests/helpers/. Never importable by production vox/ or stages/.
Provides synthetic linear word distribution exclusively for unit testing of downstream
karaoke/rendering components without audio hardware or model weights.
"""

from pathlib import Path
from vox.schemas import ScenePlan, Word, WordTimeline
from vox.align import get_audio_duration_wav


def synthesize_linear_word_timeline(plan: ScenePlan, wav_path: Path) -> tuple[WordTimeline, ScenePlan]:
    """Test helper creating linear pseudo-timestamps for downstream unit tests."""
    audio_dur = get_audio_duration_wav(wav_path)
    script_words = []
    for sc in plan.scenes:
        for w in sc.narration.strip().split():
            script_words.append((w, sc.idx))
    total_chars = sum(len(w[0]) for w in script_words)
    curr = 0.0
    timeline_words = []
    for w_text, sc_idx in script_words:
        dur = max(0.2, (len(w_text) / max(1, total_chars)) * audio_dur)
        end_t = min(audio_dur, curr + dur)
        timeline_words.append(Word(
            text=w_text,
            start=round(curr, 3),
            end=round(max(curr + 0.1, end_t), 3),
            probability=1.0,
            scene_idx=sc_idx,
        ))
        curr = end_t
    timeline = WordTimeline(
        words=timeline_words,
        audio_duration=audio_dur,
        match_ratio=1.0,
        alignment_model="test_synthetic_helper",
    )
    updated_scenes = []
    for sc in plan.scenes:
        sc_words = [w for w in timeline_words if w.scene_idx == sc.idx]
        sc_start = sc_words[0].start if sc_words else 0.0
        sc_end = sc_words[-1].end if sc_words else audio_dur
        updated_scenes.append(sc.model_copy(update={"start": sc_start, "end": sc_end}))
    return timeline, plan.model_copy(update={"scenes": updated_scenes})
