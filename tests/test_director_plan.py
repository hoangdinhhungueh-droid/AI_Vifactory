#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_director_plan.py — Unit & Invariant Tests for Director Plan & Prompts Forge (AVF-STAB-001)."""

import pytest
from stages.s05_director_plan import (
    CANONICAL_BEATS,
    CANONICAL_CAMERA_MOVES,
    validate_asset_reuse_limits,
    validate_cinematic_tokens,
    sanitize_beat_spoken_for_llm,
    build_universal_video_prompt,
)
import app.services.director_planner_b3 as facade
from core.contracts.stages import Scene


def test_canonical_beats_presence():
    """Validates the 5 canonical docudrama beats."""
    expected = [
        "Cold Strike",
        "False Narrative",
        "Forensic Paper Trail",
        "Smoking Gun",
        "Modern Mirror",
    ]
    assert CANONICAL_BEATS == expected
    assert facade.CANONICAL_BEATS == expected


def test_canonical_camera_moves():
    """Validates supported tactile camera motion types."""
    assert "top_down_static" in CANONICAL_CAMERA_MOVES
    assert "slow_push_in" in CANONICAL_CAMERA_MOVES
    assert facade.CANONICAL_CAMERA_MOVES == CANONICAL_CAMERA_MOVES


def test_validate_asset_reuse_limits_pass():
    """Asset reuse <= 3 passes without error."""
    scenes = [
        {"scene_id": "sc_01", "foreground_reuse_key": "fg_hero"},
        {"scene_id": "sc_02", "foreground_reuse_key": "fg_hero"},
        {"scene_id": "sc_03", "foreground_reuse_key": "fg_hero"},
        {"scene_id": "sc_04", "foreground_reuse_key": "fg_secondary"},
    ]
    res = validate_asset_reuse_limits(scenes, max_reuse=3)
    assert res["valid"] is True
    assert res["reuse_counts"]["fg_hero"] == 3


def test_validate_asset_reuse_limits_violation():
    """Asset reuse > 3 raises ValueError."""
    scenes = [
        {"scene_id": "sc_01", "foreground_reuse_key": "fg_hero"},
        {"scene_id": "sc_02", "foreground_reuse_key": "fg_hero"},
        {"scene_id": "sc_03", "foreground_reuse_key": "fg_hero"},
        {"scene_id": "sc_04", "foreground_reuse_key": "fg_hero"},  # 4th time -> violation!
    ]
    with pytest.raises(ValueError) as exc:
        validate_asset_reuse_limits(scenes, max_reuse=3)
    assert "Asset reuse limit exceeded" in str(exc.value)
    assert "fg_hero" in str(exc.value)


def test_validate_cinematic_tokens():
    """Validates token presence for Vox style and camera constraints."""
    valid_prompt = (
        "Editorial paper cutout animation in Vox documentary style. "
        "Camera: Completely static top-down desk view, crisp focus."
    )
    assert validate_cinematic_tokens(valid_prompt) is True

    # Missing camera
    incomplete_prompt = "Editorial paper cutout animation in Vox documentary style."
    assert validate_cinematic_tokens(incomplete_prompt) is False

    # Empty prompt
    assert validate_cinematic_tokens("") is False


def test_sanitize_beat_spoken_valid():
    """Spoken list with start and end calculates duration cleanly."""
    raw = [
        {"sentence_id": "s1", "text": "Sentence 1", "start": 0.0, "end": 2.5},
        {"sentence_id": "s2", "text": "Sentence 2", "start": 2.5, "end": 6.1},
    ]
    res = sanitize_beat_spoken_for_llm(raw)
    assert len(res) == 2
    assert res[0]["duration_sec"] == 2.5
    assert res[1]["duration_sec"] == 3.6


def test_sanitize_beat_spoken_invalid_timestamps():
    """End <= start strictly raises ValueError (Rule 118 & 120)."""
    raw = [{"sentence_id": "s1", "text": "Broken timestamps", "start": 5.0, "end": 4.0}]
    with pytest.raises(ValueError) as exc:
        sanitize_beat_spoken_for_llm(raw)
    assert "end (4.0) <= start (5.0)" in str(exc.value)


def test_universal_video_prompt_builder():
    """Validates Prompt 3 structure generated for Remotion/I2V."""
    sc = Scene(
        scene_id="sc_01",
        narration="The sudden liquidity freeze caused widespread market panic.",
        headline="BANKRUPTCY CRASH",
        visual_metaphor="Stamping paper docket",
        color_accent="Vox Yellow #F2C230",
        duration_est_sec=5.0,
    )
    prompt = build_universal_video_prompt(sc)
    assert "Editorial paper cutout animation in Vox documentary style." in prompt
    assert "BANKRUPTCY CRASH" in prompt
    assert "Camera: Completely static top-down desk view" in prompt

