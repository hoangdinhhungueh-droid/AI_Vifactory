#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_timeline_editor_agent.py"""
import pytest
from app.services.timeline_editor_agent import audit_and_optimize_timeline

def test_clean_speaker_tags_rule_136():
    raw_scenes = [
        {"durationInFrames": 60, "speakerTag": "ARCHIVE X // JOHN DOE.PNG"},
        {"durationInFrames": 60, "speakerTag": "DEFAULT // NOMINEE OPERATOR.webp"},
    ]
    out = audit_and_optimize_timeline(raw_scenes)
    assert out[0]["speakerTag"] == "JOHN DOE"
    assert out[1]["speakerTag"] == "NOMINEE OPERATOR"

def test_visual_monotony_breaker():
    raw_scenes = [
        {"durationInFrames": 60, "forensicOverlay": {"type": "document_highlight", "title": "DOC 1"}},
        {"durationInFrames": 60, "forensicOverlay": {"type": "document_highlight", "title": "DOC 2"}},
        {"durationInFrames": 60, "forensicOverlay": {"type": "document_highlight", "title": "DOC 3"}},
    ]
    out = audit_and_optimize_timeline(raw_scenes)
    assert out[2]["forensicOverlay"]["type"] == "kinetic_counter"
    assert "CRITICAL FINDING" in out[2]["forensicOverlay"]["badge"]

def test_dead_air_elimination():
    raw_scenes = [
        {"durationInFrames": 180, "narration": "A long static sentence...", "cameraMovement": "slow_push_in"},
    ]
    out = audit_and_optimize_timeline(raw_scenes, options={"max_dead_air_frames": 120})
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
    out = audit_and_optimize_timeline(raw_scenes, whisper_words=whisper_words)
    assert "wordLockedPunches" in out[0]
    punch = out[0]["wordLockedPunches"][0]
    assert punch["camera"] == "snap_zoom"
    assert punch["sfx_cue"] == "stamp_slam"
    assert out[0]["tensionLevel"] == "high"
