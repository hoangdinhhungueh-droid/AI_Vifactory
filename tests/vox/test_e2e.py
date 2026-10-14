#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_e2e.py — End-to-End Production Verification on Golden Fixture (AVF-VOX-001)."""

import pytest
from pathlib import Path

from vox.pipeline import run_pipeline


def test_vox_single_pipeline_golden_e2e(tmp_path):
    golden_script = Path(__file__).parent / "fixtures" / "golden_script.txt"
    assert golden_script.exists()

    out_dir = tmp_path / "golden_run"
    manifest = run_pipeline(golden_script, out_dir, title="Golden Liquidity Crisis")

    # Verify atomic manifest
    manifest_file = out_dir / "manifest.json"
    assert manifest_file.exists()
    assert manifest["pipeline"] == "vox_tactile_explainer_v1"
    assert manifest["scene_count"] == 3

    # Verify final media asset
    final_video = Path(manifest["final_video"]["path"])
    assert final_video.exists()
    assert final_video.stat().st_size > 10000

    # Verify quality gates
    qa = manifest["qa_gates"]
    assert qa["status"] == "PASS"
    assert qa["video_codec"] == "h264"
    assert qa["audio_codec"] == "aac"
    assert qa["width"] == 1920
    assert qa["height"] == 1080
    assert qa["black_sections_detected"] == 0
    assert qa["unique_camera_moves"] >= 3
