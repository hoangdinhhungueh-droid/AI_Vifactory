#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_timeline_editor_agent.py"""
from unittest.mock import MagicMock, patch
import pytest
from app.services.timeline_editor_agent import (
    VALID_CAMERA_MOVEMENTS,
    audit_and_optimize_timeline,
    llm_timeline_director_review,
)


def test_clean_speaker_tags_rule_136():
    raw_scenes = [
        {"durationInFrames": 60, "speakerTag": "ARCHIVE X // JOHN DOE.PNG"},
        {"durationInFrames": 60, "speakerTag": "DEFAULT // NOMINEE OPERATOR.webp"},
    ]
    out = audit_and_optimize_timeline(raw_scenes, options={"enable_llm_director": False})
    assert out[0]["speakerTag"] == "JOHN DOE"
    assert out[1]["speakerTag"] == "NOMINEE OPERATOR"


def test_visual_monotony_breaker():
    raw_scenes = [
        {"durationInFrames": 60, "forensicOverlay": {"type": "document_highlight", "title": "DOC 1"}},
        {"durationInFrames": 60, "forensicOverlay": {"type": "document_highlight", "title": "DOC 2"}},
        {"durationInFrames": 60, "forensicOverlay": {"type": "document_highlight", "title": "DOC 3"}},
    ]
    out = audit_and_optimize_timeline(raw_scenes, options={"enable_llm_director": False})
    assert out[2]["forensicOverlay"]["type"] == "kinetic_counter"
    assert "CRITICAL FINDING" in out[2]["forensicOverlay"]["badge"]


def test_dead_air_elimination():
    raw_scenes = [
        {"durationInFrames": 180, "narration": "A long static sentence...", "cameraMovement": ""},
    ]
    out = audit_and_optimize_timeline(raw_scenes, options={"max_dead_air_frames": 120, "enable_llm_director": False})
    assert out[0]["cameraMovement"] == "snap_zoom"
    assert out[0]["tensionLevel"] == "high"


def test_word_locked_camera_punch():
    raw_scenes = [
        {"durationInFrames": 90, "narration": "They uncovered massive wire fraud."},
    ]
    whisper_words = [
        {"word": "They", "start_ms": 100, "end_ms": 300},
        {"word": "uncovered", "start_ms": 350, "end_ms": 800},
        {"word": "massive", "start_ms": 850, "end_ms": 1200},
        {"word": "wire", "start_ms": 1250, "end_ms": 1500},
        {"word": "fraud", "start_ms": 1550, "end_ms": 1900},
    ]
    out = audit_and_optimize_timeline(raw_scenes, whisper_words=whisper_words, options={"enable_llm_director": False})
    assert "wordLockedPunches" in out[0]
    punch = out[0]["wordLockedPunches"][0]
    assert punch["camera"] == "snap_zoom"
    assert punch["sfx_cue"] == "stamp_slam"
    assert out[0]["tensionLevel"] == "high"


def test_continuous_camera_movements_support():
    for mov in ["continuous_drift", "seamless_whip_pan", "macro_orbit", "cinematic_orbit"]:
        assert mov in VALID_CAMERA_MOVEMENTS
        scenes = [{"durationInFrames": 90, "cameraMovement": mov}]
        out = audit_and_optimize_timeline(scenes, options={"enable_llm_director": False})
        assert out[0]["cameraMovement"] == mov
        assert out[0]["enableParallax"] is True
        assert out[0]["atmosphericLighting"] is True


def test_llm_director_review_fallback_on_error():
    scenes = [{"scene_id": "sc_01", "durationInFrames": 60, "narration": "Sample text"}]
    with patch("app.services.model_gateway.get_global_gateway") as mock_gw:
        mock_instance = MagicMock()
        mock_instance.call_llm.side_effect = TimeoutError("Gateway timeout")
        mock_gw.return_value = mock_instance

        review = llm_timeline_director_review(scenes, episode_id="TEST_EP0001", timeout=1.0)
        assert review["status"] == "fallback"
        assert review["model"] == "heuristic"

        # audit_and_optimize_timeline should gracefully fallback
        out = audit_and_optimize_timeline(scenes, options={"episode_id": "TEST_EP0001", "timeout_sec": 1.0})
        assert len(out) == 1
        assert out[0]["enableParallax"] is True


def test_llm_director_review_success_merging():
    scenes = [
        {"scene_id": "sc_01", "durationInFrames": 90, "narration": "The secret leak was confirmed.", "speakerTag": "SOURCE.PNG"},
        {"scene_id": "sc_02", "durationInFrames": 120, "narration": "Authorities raided the offices."},
    ]
    mock_llm_json = """
    {
      "editorial_rationale": "High tension cinematic investigative pacing with continuous flow.",
      "scene_adjustments": [
        {
          "idx": 0,
          "cameraMovement": "continuous_drift",
          "tensionLevel": "high",
          "transition": "cross_fade",
          "speakerTag": "KATSUYA OKADA // FORMER DPJ LEADER",
          "directorNote": "Smooth continuous drift tracking"
        },
        {
          "idx": 1,
          "cameraMovement": "seamless_whip_pan",
          "tensionLevel": "extreme",
          "transition": "continuous_whip",
          "directorNote": "Kinetic punch on the raid"
        }
      ]
    }
    """
    with patch("app.services.model_gateway.get_global_gateway") as mock_gw:
        mock_instance = MagicMock()
        mock_instance.call_llm.return_value = mock_llm_json
        mock_gw.return_value = mock_instance

        out = audit_and_optimize_timeline(scenes, options={"episode_id": "TEST_EP0001", "enable_llm_director": True})
        assert len(out) == 2
        # Check LLM adjustments applied
        assert out[0]["cameraMovement"] == "continuous_drift"
        assert out[0]["tensionLevel"] == "high"
        assert out[0]["transition"] == "cross_fade"
        assert out[0]["speakerTag"] == "KATSUYA OKADA // FORMER DPJ LEADER"

        assert out[1]["cameraMovement"] == "seamless_whip_pan"
        assert out[1]["tensionLevel"] == "extreme"
        assert out[1]["transition"] == "continuous_whip"
