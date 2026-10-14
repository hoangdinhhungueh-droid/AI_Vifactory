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
    """Validates the 12 canonical camera motion primitives."""
    assert len(CANONICAL_CAMERA_MOVES) == 12
    assert "slow_push_in" in CANONICAL_CAMERA_MOVES
    assert "snap_zoom" in CANONICAL_CAMERA_MOVES
    assert "dolly_zoom" in CANONICAL_CAMERA_MOVES
    assert "seamless_whip_pan" in CANONICAL_CAMERA_MOVES
    assert facade.CANONICAL_CAMERA_MOVES == CANONICAL_CAMERA_MOVES


def test_validate_asset_reuse_limits_pass():
    """Asset reuse <= 3 and gap >= 4 passes cleanly."""
    scenes = [
        {"scene_id": "sc_01", "bg_reuse_key": "bg_court"},
        {"scene_id": "sc_02", "bg_reuse_key": "bg_office_1"},
        {"scene_id": "sc_03", "bg_reuse_key": "bg_office_2"},
        {"scene_id": "sc_04", "bg_reuse_key": "bg_office_3"},
        {"scene_id": "sc_05", "bg_reuse_key": "bg_office_4"},
        {"scene_id": "sc_06", "bg_reuse_key": "bg_court"},  # gap = 5 >= 4
    ]
    res = validate_asset_reuse_limits(scenes)
    assert res["ok"] is True
    assert len(res["violations"]) == 0
    assert res["bg_usage"]["bg_court"] == 2


def test_validate_asset_reuse_limits_violation():
    """Asset repeated too quickly (gap < 4) or overused (>3) records violations."""
    scenes = [
        {"scene_id": "sc_01", "bg_reuse_key": "bg_court"},
        {"scene_id": "sc_02", "bg_reuse_key": "bg_court"},  # gap = 1 < 4!
    ]
    res = validate_asset_reuse_limits(scenes)
    assert res["ok"] is False
    assert len(res["violations"]) >= 1
    assert "repeated too quickly" in res["violations"][0]


def test_validate_cinematic_tokens():
    """Validates token presence for Vox 38-token canonical set and semantic fallback."""
    # Direct valid token
    valid_tokens = ["/zoom_through", "/spotbeam"]
    res = validate_cinematic_tokens(valid_tokens)
    assert res == ["/zoom_through", "/spotbeam"]

    # Keyword fallback from narration
    res_map = validate_cinematic_tokens([], narration="The company tracked the smuggling route across the border.")
    assert "/route_draw" in res_map or "/map_pin_drop" in res_map

    res_finance = validate_cinematic_tokens([], narration="The total loss exceeded ten billion dollars.")
    assert "/counter_countup" in res_finance


def test_sanitize_beat_spoken_valid():
    """Spoken list with start and end calculates duration cleanly and prunes heavy metadata."""
    raw = [
        {"sentence_id": "s1", "text": "Sentence 1", "start": 0.0, "end": 2.5, "heavy_whisper_blob": [1, 2, 3]},
        {"sentence_id": "s2", "text": "Sentence 2", "start": 2.5, "end": 6.1},
    ]
    res = sanitize_beat_spoken_for_llm(raw)
    assert len(res) == 2
    assert res[0]["duration_sec"] == 2.5
    assert res[1]["duration_sec"] == 3.6
    assert "heavy_whisper_blob" not in res[0]
    assert res[0]["sentence_id"] == "s1"


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

