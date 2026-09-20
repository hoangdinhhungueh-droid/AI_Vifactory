#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_auto_post_render.py

Unit tests for the automated post-render pipeline and video audit runner.
"""
import pytest
from pathlib import Path
from app.services.video_audit_runner import extract_beat_audit_frames, call_vision_audit_llm


def test_audit_frame_extraction_logic(tmp_path):
    video_dummy = tmp_path / "dummy_video.mp4"
    video_dummy.write_bytes(b"dummy")
    audit_dir = tmp_path / "audits"

    # Testing fallback when ffmpeg cannot probe dummy file
    frames = extract_beat_audit_frames(video_dummy, audit_dir, 60.0)
    assert isinstance(frames, list)


def test_vision_audit_fallback_rule_based(tmp_path):
    # Simulate extracted frames
    f1 = tmp_path / "frame1.png"
    f2 = tmp_path / "frame2.png"
    f1.write_bytes(b"0" * 60000)
    f2.write_bytes(b"0" * 60000)

    # Call with dummy frames when API key might not be set in test env
    res = call_vision_audit_llm([f1, f2], "TEST_EP0001_dummy")
    assert "verdict" in res
    assert "overall_score" in res
    assert res["overall_score"] >= 6.0
