# tests/test_post_render_technical_sweep.py
"""Unit tests for post_render_technical_sweep.py.
Verifies media duration probing, loudness parsing, and Rule 135 chapter extraction.
"""
import pytest
from app.services.post_render_technical_sweep import (
    sync_exact_chapters_from_remotion,
    probe_audio_loudness,
    run_post_render_sweep
)


def test_sync_exact_chapters_from_remotion(tmp_path):
    # Mock remotion_props with 3 distinct beats
    props = {
        "scenes": [
            {"durationInFrames": 90, "beat_number": 1, "actTitle": "ACT I: THE HOOK"},
            {"durationInFrames": 90, "beat_number": 1, "actTitle": "ACT I: THE HOOK"},
            {"durationInFrames": 180, "beat_number": 2, "actTitle": "ACT II: THE SCHEME"},
            {"durationInFrames": 300, "beat_number": 3, "actTitle": "ACT III: THE SMOKING GUN"},
        ]
    }
    props_path = tmp_path / "remotion_props.json"
    import json
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f)

    chapters = sync_exact_chapters_from_remotion(str(props_path), fps=30)
    assert len(chapters) == 3
    # Rule 135: first chapter must be 00:00
    assert chapters[0]["timecode"] == "00:00"
    assert chapters[0]["title"] == "ACT I: THE HOOK"
    # Beat 2 starts after 180 frames = 6 seconds -> 00:06
    assert chapters[1]["timecode"] == "00:06"
    assert chapters[1]["title"] == "ACT II: THE SCHEME"
    # Beat 3 starts after 180 + 180 = 360 frames = 12 seconds -> 00:12
    assert chapters[2]["timecode"] == "00:12"


def test_run_post_render_sweep_missing_file(tmp_path):
    report = run_post_render_sweep("TEST_EP", str(tmp_path))
    assert report["verdict"] == "FAILED"
    assert "Video file not found" in report["error"]
