#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_audio_alignment_adversarial.py — Adversarial Audio Alignment Perturbation Tests (Rule 120).

Tests:
1. Perturbing audio by expanding duration scales the timeline and shifts word boundaries.
2. Adversarial padding with leading silence preserves strict monotonicity within [0, T].
3. Empty narration or unaligned audio fails closed cleanly.
"""

import math
import struct
import wave
from pathlib import Path

import pytest

from vox.align import align_script_with_audio, get_audio_duration_wav
from vox.schemas import CameraMove, FGObject, Scene, ScenePlan


def _create_synthetic_wav(path: Path, duration_sec: float, sample_rate: int = 48000, tone_hz: float = 440.0, leading_silence_sec: float = 0.0):
    """Generates a valid 16-bit mono PCM WAV file with optional leading silence and a sine tone."""
    path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(duration_sec * sample_rate)
    silence_frames = int(leading_silence_sec * sample_rate)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_frames):
            if i < silence_frames:
                val = 0
            else:
                t = (i - silence_frames) / sample_rate
                sample = math.sin(2 * math.pi * tone_hz * t) * 0.3
                val = int(sample * 32767.0)
            frames.extend(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(frames)


def _make_test_plan() -> ScenePlan:
    return ScenePlan(
        title="Test Audio Alignment",
        scenes=[
            Scene(
                idx=1,
                narration="First sentence explains the initial premise.",
                bg_prompt="A textured comic paper illustration, wordless, zero text",
                camera=CameraMove.STATIC_BREATH,
                fg=[
                    FGObject(
                        id="obj1",
                        prompt="vintage parchment dossier, zero text",
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.4,
                        depth=0.5,
                        enter_at=0.0,
                    )
                ],
            ),
            Scene(
                idx=2,
                narration="Second sentence concludes with key evidence.",
                bg_prompt="An editorial dark background, wordless, zero text",
                camera=CameraMove.PAN_RIGHT,
                fg=[
                    FGObject(
                        id="obj2",
                        prompt="metallic emblem token, zero text",
                        anchor_x=0.6,
                        anchor_y=0.5,
                        scale=0.35,
                        depth=0.7,
                        enter_at=0.5,
                    )
                ],
            ),
        ]
    )


def test_audio_alignment_with_known_duration_offset(tmp_path):
    """Asserts that expanding audio duration shifts the timeline end and scales word allocations proportionally."""
    plan1 = _make_test_plan()
    wav_base = tmp_path / "base.wav"
    wav_expanded = tmp_path / "expanded.wav"

    _create_synthetic_wav(wav_base, duration_sec=4.0)
    _create_synthetic_wav(wav_expanded, duration_sec=8.0)

    timeline_base, plan_base = align_script_with_audio(plan1, wav_base)
    assert timeline_base.audio_duration == 4.0
    assert plan_base.scenes[0].start == 0.0
    assert plan_base.scenes[-1].end == 4.0

    plan2 = _make_test_plan()
    timeline_exp, plan_exp = align_script_with_audio(plan2, wav_expanded)
    assert timeline_exp.audio_duration == 8.0
    assert plan_exp.scenes[0].start == 0.0
    assert plan_exp.scenes[-1].end == 8.0

    # The duration expansion must be reflected across words
    assert timeline_exp.words[-1].end > timeline_base.words[-1].end
    assert abs(timeline_exp.words[-1].end - 8.0) <= 0.1


def test_adversarial_leading_offset_detection(tmp_path):
    """Perturbs audio with leading silence and asserts words remain strictly monotonic within [0, T]."""
    plan = ScenePlan(
        title="Adversarial Offset",
        scenes=[
            Scene(
                idx=1,
                narration="Token one token two token three token four.",
                bg_prompt="Abstract comic backdrop, wordless, zero text",
                camera=CameraMove.PUSH_IN,
                fg=[
                    FGObject(
                        id="obj_adv",
                        prompt="tactile evidence artifact, zero text",
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.4,
                        depth=0.5,
                        enter_at=0.0,
                    )
                ],
            )
        ]
    )

    wav_padded = tmp_path / "padded.wav"
    _create_synthetic_wav(wav_padded, duration_sec=6.0, leading_silence_sec=2.0)

    dur = get_audio_duration_wav(wav_padded)
    assert abs(dur - 6.0) < 0.01

    timeline, plan_out = align_script_with_audio(plan, wav_padded)

    # Assert monotonic timestamps
    for i in range(len(timeline.words) - 1):
        assert timeline.words[i].start <= timeline.words[i].end
        assert timeline.words[i].end <= timeline.words[i+1].start + 0.001

    assert timeline.words[-1].end <= dur + 0.05
    assert plan_out.scenes[0].start == 0.0
    assert plan_out.scenes[0].end == dur


def test_empty_words_fails_closed(tmp_path):
    """Scene with purely whitespace narration must fail closed with ValueError rather than producing invalid timeline."""
    plan = ScenePlan(
        title="Empty Words",
        scenes=[
            Scene(
                idx=1,
                narration="   ",
                bg_prompt="Abstract comic backdrop, wordless, zero text",
                camera=CameraMove.PUSH_IN,
                fg=[
                    FGObject(
                        id="obj_empty",
                        prompt="tactile evidence artifact, zero text",
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.4,
                        depth=0.5,
                        enter_at=0.0,
                    )
                ],
            )
        ]
    )
    wav = tmp_path / "dummy.wav"
    _create_synthetic_wav(wav, duration_sec=2.0)

    with pytest.raises(ValueError, match="zero words"):
        align_script_with_audio(plan, wav)
