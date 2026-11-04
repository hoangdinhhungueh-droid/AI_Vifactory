#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_pacing_budgeter.py — Comprehensive Unit Tests for PacingBudgeter.

Validates:
- Rule 118: Zero-Mock truthful speech calculation.
- Rule 120: Whisper timestamps integration and 0ms drift.
- Rule 128: Multi-market calibrated speech rates:
  * KR: 5.8 syl/s
  * JP: 6.5 morae/s
  * EN: 3.2 words/s
  * VN: 3.6 words/s
- Rule 140: Action Phase <= 0.4s and Living Hold calculation.
- Projected Frame Outline generation and timeline contiguity.
"""

import pytest

from core.pacing_budgeter import (
    CALIBRATED_SPEECH_RATES,
    DOCUDRAMA_MAX_WPM,
    DOCUDRAMA_MIN_WPM,
    DOCUDRAMA_TARGET_WPM,
    MAX_ACTION_SNAP_SEC,
    MAX_SCENE_DURATION_SEC,
    MIN_SCENE_DURATION_SEC,
    calculate_word_budget_for_duration,
    calculate_wpm,
    calibrate_scene_durations_to_target,
    clamp_narration_duration_to_pacing,
    compute_scene_frame_budget,
    count_speech_units,
    estimate_calibrated_speech_duration,
    generate_projected_frame_outline,
    is_docudrama_pacing_valid,
)


def test_speech_rate_constants():
    assert CALIBRATED_SPEECH_RATES["KR"] == 5.8
    assert CALIBRATED_SPEECH_RATES["JP"] == 6.5
    assert CALIBRATED_SPEECH_RATES["EN"] == 3.2
    assert CALIBRATED_SPEECH_RATES["VN"] == 3.6


def test_count_speech_units_multilingual():
    # Korean (CJK non-whitespace char count)
    assert count_speech_units("공정위 제재가 보도됐습니다", "KR") == 12

    # Japanese (CJK non-whitespace char count)
    assert count_speech_units("公正取引委員会の制裁", "JP") == 10

    # English (word count)
    assert count_speech_units("The regulator sanctioned four major developer firms", "EN") == 7

    # Vietnamese (word count)
    assert count_speech_units("Cơ quan điều tra phát hiện bốn sai phạm lớn", "VN") == 10


def test_calibrated_speech_duration_estimates():
    # KR 31 Hangul syllables -> 31 / 5.8 = 5.345s
    kr_sentence = "공정거래위원회의 시정명령과 과징금 처분이 공식적으로 발표되었습니다"
    assert 5.0 <= estimate_calibrated_speech_duration(kr_sentence, "KR") <= 5.5

    # JP 30 characters -> 30 / 6.5 = 4.615s
    jp_sentence = "公正取引委員会は不正な不動産勧誘行為に対して警告を発しました"
    assert 4.4 <= estimate_calibrated_speech_duration(jp_sentence, "JP") <= 4.8

    # EN 17 words -> 17 / 3.2 = 5.312s
    en_sentence = "The investigation revealed that developers collected deposits long before obtaining official construction and zoning approval from regulators."
    assert 5.0 <= estimate_calibrated_speech_duration(en_sentence, "EN") <= 5.5

    # Clamping tests
    assert estimate_calibrated_speech_duration("Short", "EN") == MIN_SCENE_DURATION_SEC
    long_text = "Word " * 100
    assert estimate_calibrated_speech_duration(long_text, "EN") == MAX_SCENE_DURATION_SEC


def test_missing_market_fails_closed():
    with pytest.raises(ValueError, match="No market specified"):
        estimate_calibrated_speech_duration("Sentence without market", market=None)


def test_compute_scene_frame_budget_whisper_priority():
    whisper_words = [
        {"word": "Word1", "start": 1.0, "end": 2.5},
        {"word": "Word2", "start": 2.5, "end": 4.5},
    ]
    budget = compute_scene_frame_budget(
        scene_id="SCENE_01",
        sentence="Word1 Word2",
        market="EN",
        start_sec=0.0,
        fps=30,
        whisper_words=whisper_words,
    )
    assert budget.source == "whisper_aligned"
    assert budget.exact_duration_sec == 3.5  # 4.5 - 1.0
    assert budget.target_frames_30fps == 105
    assert budget.action_phase_sec <= MAX_ACTION_SNAP_SEC
    assert budget.living_hold_sec > 0


def test_projected_frame_outline_contiguous_timeline():
    scenes = [
        {"scene_id": "SC_01", "sentence": "공정위 제재가 보도됐습니다"},
        {"scene_id": "SC_02", "sentence": "시행사 네 곳 드림하우징 외 3개사 대상입니다"},
        {"scene_id": "SC_03", "sentence": "시정명령과 경고 처분을 내렸습니다"},
    ]
    outline = generate_projected_frame_outline(scenes, market="KR", fps=30)

    assert outline.total_scenes == 3
    assert outline.fps == 30
    assert outline.total_duration_sec > 7.0

    # Verify contiguous timestamps without gaps or overlaps
    assert outline.scenes[0].start_sec == 0.0
    assert outline.scenes[1].start_sec == outline.scenes[0].end_sec
    assert outline.scenes[2].start_sec == outline.scenes[1].end_sec
    assert outline.scenes[0].start_frame_30fps == 0
    assert outline.scenes[1].start_frame_30fps == outline.scenes[0].end_frame_30fps
    assert outline.scenes[2].start_frame_30fps == outline.scenes[1].end_frame_30fps


def test_docudrama_pacing_constants():
    assert DOCUDRAMA_MIN_WPM == 115.0
    assert DOCUDRAMA_MAX_WPM == 135.0
    assert DOCUDRAMA_TARGET_WPM == 125.0


def test_calculate_word_budget_for_duration():
    # Standard 240s episode (4:00)
    b240 = calculate_word_budget_for_duration(240.0)
    assert b240["min"] == 460
    assert b240["max"] == 540
    assert b240["target"] == 500
    assert b240["optimal_min"] == 480
    assert b240["optimal_max"] == 520

    # Macro 600s episode (10:00)
    b600 = calculate_word_budget_for_duration(600.0)
    assert b600["min"] == 1150
    assert b600["max"] == 1350
    assert b600["target"] == 1250


def test_calculate_wpm_and_validation():
    # 500 words across 240s = 125.0 WPM
    assert calculate_wpm(500, 240.0) == 125.0
    assert is_docudrama_pacing_valid(500, 240.0) is True

    # 460 words across 240s = 115.0 WPM (lower bound PASS)
    assert calculate_wpm(460, 240.0) == 115.0
    assert is_docudrama_pacing_valid(460, 240.0) is True

    # 540 words across 240s = 135.0 WPM (upper bound PASS)
    assert calculate_wpm(540, 240.0) == 135.0
    assert is_docudrama_pacing_valid(540, 240.0) is True

    # 600 words across 240s = 150.0 WPM (exceeds ceiling FAIL)
    assert calculate_wpm(600, 240.0) == 150.0
    assert is_docudrama_pacing_valid(600, 240.0) is False

    # 400 words across 240s = 100.0 WPM (below floor FAIL)
    assert calculate_wpm(400, 240.0) == 100.0
    assert is_docudrama_pacing_valid(400, 240.0) is False


def test_clamp_narration_duration_to_pacing():
    # 25 words at 125 WPM (2.0833 wps) -> 25 / 2.0833 = 12.0s clamped to max (10.0s)
    dur = clamp_narration_duration_to_pacing(25, target_wpm=125.0, min_duration=2.5, max_duration=10.0)
    assert dur == 10.0

    # 10 words at 125 WPM (2.0833 wps) -> 10 / 2.0833 = 4.8s
    dur10 = clamp_narration_duration_to_pacing(10, target_wpm=125.0)
    assert 4.5 <= dur10 <= 5.0

    # 2 words at 125 WPM -> 0.96s -> clamped to MIN_SCENE_DURATION_SEC (2.5s)
    dur2 = clamp_narration_duration_to_pacing(2, target_wpm=125.0)
    assert dur2 == 2.5


def test_calibrate_scene_durations_to_target():
    scenes = [
        {"scene_id": "SC_01", "narration": "In an acute market crisis, the collapse began with alarming speed."}, # 11 words
        {"scene_id": "SC_02", "narration": "Regulatory examiners uncovered major anomalies across the primary accounting ledgers."}, # 9 words
        {"scene_id": "SC_03", "narration": "Documented statutory exemptions allowed the consortium to proceed unhindered."}, # 8 words
    ]
    # Total words = 11 + 10 + 9 = 30 words
    # Calibrate to 14.4s (30 / 14.4 * 60 = 125.0 WPM)
    wpm = calibrate_scene_durations_to_target(scenes, target_total_duration_sec=14.4, target_wpm=125.0)
    assert 124.0 <= wpm <= 126.0

    dur_sum = sum(s["duration_est_sec"] for s in scenes)
    assert abs(dur_sum - 14.4) <= 0.1
