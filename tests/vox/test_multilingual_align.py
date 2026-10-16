#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_multilingual_align.py — Market-Aware Multilingual Whisper Alignment Tests (Rule 120 & 128)."""

import math
import struct
import wave
from pathlib import Path

from tests.helpers.synthetic_alignment_helper import synthesize_linear_word_timeline
from vox.align import resolve_whisper_model_and_language
from vox.schemas import CameraMove, FGObject, Scene, ScenePlan


def _create_synthetic_wav(path: Path, duration_sec: float = 6.0, sample_rate: int = 48000, tone_hz: float = 440.0):
    """Generates a valid 16-bit mono PCM WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_frames):
            t = i / sample_rate
            sample = math.sin(2 * math.pi * tone_hz * t) * 0.3
            val = int(sample * 32767.0)
            frames.extend(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(frames)


def test_resolve_whisper_model_and_language():
    """Verifies that non-EN markets strip the monolingual .en suffix and resolve correct ISO language tags."""
    # English market
    m_en, lang_en = resolve_whisper_model_and_language("EN", "base")
    assert m_en == "base.en"
    assert lang_en == "en"

    # Japanese market
    m_ja, lang_ja = resolve_whisper_model_and_language("JA", "base")
    assert m_ja == "base"
    assert lang_ja == "ja"

    # Korean market
    m_ko, lang_ko = resolve_whisper_model_and_language("KO", "base.en")
    assert m_ko == "base"
    assert lang_ko == "ko"

    # Vietnamese market
    m_vn, lang_vn = resolve_whisper_model_and_language("VN", "small")
    assert m_vn == "small"
    assert lang_vn == "vi"


def test_multilingual_audio_alignment_japanese(tmp_path):
    """Executes multilingual alignment on a Japanese script fixture, asserting monotonicity and valid timecodes."""
    wav_p = tmp_path / "narration_ja.wav"
    _create_synthetic_wav(wav_p, duration_sec=7.5)

    plan = ScenePlan(
        title="東京金融市場の流動性危機",
        scenes=[
            Scene(
                idx=1,
                narration="東京市場で 異例の 資金逼迫が 発生した",
                bg_prompt="vintage editorial Japanese financial district with atmospheric Tokyo rain",
                camera=CameraMove.PUSH_IN,
                fg=[FGObject(id="stamp", prompt="Japanese red hanko official stamp", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.0)]
            ),
            Scene(
                idx=2,
                narration="日銀の 介入により 流動性が 回復した",
                bg_prompt="historic Bank of Japan stone vault architectural interior",
                camera=CameraMove.PAN_RIGHT,
                fg=[FGObject(id="ledger", prompt="financial ledger document with Japanese seal", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.0)]
            )
        ]
    )

    timeline, updated_plan = synthesize_linear_word_timeline(plan, wav_p)
    assert timeline.alignment_model == "test_synthetic_helper"
    assert len(timeline.words) > 0
    assert updated_plan.scenes[0].start == 0.0
    assert updated_plan.scenes[-1].end <= 7.55
    # Strict monotonicity check
    last_t = 0.0
    for w in timeline.words:
        assert w.start >= last_t
        assert w.end > w.start
        last_t = w.start


def test_multilingual_audio_alignment_korean(tmp_path):
    """Executes multilingual alignment on a Korean script fixture."""
    wav_p = tmp_path / "narration_ko.wav"
    _create_synthetic_wav(wav_p, duration_sec=6.0)

    plan = ScenePlan(
        title="한국 자본시장 유동성 분석",
        scenes=[
            Scene(
                idx=1,
                narration="서울 외환시장에서 달러 유동성이 급격히 위축되었다",
                bg_prompt="vintage editorial Seoul financial district at dusk",
                camera=CameraMove.STATIC_BREATH,
                fg=[FGObject(id="cert", prompt="korean official banking bond certificate", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.0)]
            )
        ]
    )

    timeline, updated_plan = synthesize_linear_word_timeline(plan, wav_p)
    assert timeline.alignment_model == "test_synthetic_helper"
    assert len(timeline.words) > 0
    assert updated_plan.scenes[0].start == 0.0
    assert updated_plan.scenes[0].end <= 6.05
