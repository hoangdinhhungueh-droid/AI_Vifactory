#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_e2e.py — End-to-End Production Verification on Golden Fixture (AVF-VOX-001)."""

from pathlib import Path

from vox.pipeline import run_pipeline


def test_vox_single_pipeline_golden_e2e(tmp_path):
    golden_script = Path(__file__).parent / "fixtures" / "golden_script.txt"
    assert golden_script.exists()

    out_dir = tmp_path / "golden_run"
    manifest = run_pipeline(
        golden_script,
        out_dir,
        title="Golden Liquidity Crisis",
    )

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

    # Verify word-level anchors on all scenes and reverse karaoke drift (Rule 120)
    assert manifest["subtitles"]["reverse_parity_status"] == "PASS"
    assert manifest["subtitles"]["max_reverse_drift_ms"] <= 33.3
    for sc in manifest["scenes"]:
        assert sc["word_anchor"] is not None
        assert sc["word_anchor"]["boundary_delta_frames"] <= 1.0

    # Regression test: CLI and embedded gate outputs are strictly identical
    import json
    import os
    import subprocess
    import sys
    repo_root = Path(__file__).resolve().parent.parent.parent
    cmd_env = dict(os.environ, PYTHONPATH=str(repo_root))
    cmd_cli = [sys.executable, "-m", "vox.qa.gates", "verify", str(manifest_file)]
    res = subprocess.run(cmd_cli, capture_output=True, text=True, check=True, cwd=str(repo_root), env=cmd_env)
    assert res.returncode == 0
    assert "[QA GATE AUDIT: PASS]" in res.stdout
    cli_json_str = res.stdout.split("[QA GATE AUDIT: PASS]", 1)[1].strip()
    cli_qa = json.loads(cli_json_str)
    assert cli_qa == qa
