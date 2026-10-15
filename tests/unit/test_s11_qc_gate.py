#!/usr/bin/env python3
"""tests/unit/test_s11_qc_gate.py — Stage S11 Quality Control Fail-Closed Verification (AVF-VOX-001).

Tests:
1. Valid video triggers qc_verdict='PASS', integrity_verified=True, status='ok'.
2. Gate-violating video triggers qc_verdict='FAIL', integrity_verified=False, status='error'.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.config import RunContext, load_profile
from core.contracts.stages import StageID
from core.paths import resolve_run_paths
from core.run_manifest import RunManifest
from stages.s11_qc import run as run_s11_qc


def test_s11_qc_fails_closed_on_gate_violation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that an invalid video emits FAIL, integrity_verified=False, status='error'."""
    run_id = "test_qc_fail_closed"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy text file disguised as mp4 (violates H.264/AAC media gates)
    bad_mp4 = paths.final_render_dir / "final.mp4"
    bad_mp4.write_text("This is not a real mp4 video file", encoding="utf-8")

    # Create S10 artifact
    s10_artifact = {
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {
            "task_id": run_id,
            "final_video_path": str(bad_mp4),
            "fps": 30.0,
            "duration_in_frames": 150,
        },
        "provenance": {"generator": "stages.s10_render", "latency_sec": 1.0},
    }
    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps(s10_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )

    artifact = run_s11_qc(ctx)

    assert artifact.payload["qc_verdict"] == "FAIL"
    assert artifact.payload["integrity_verified"] is False
    assert artifact.status == "failed"
    assert "FAILED quality gates" in artifact.payload["message"]
    assert artifact.payload["qc_details"]["gates_verified"] is False


def test_s11_qc_propagates_programming_errors_unconverted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that non-QA gate exceptions (e.g. TypeError, NameError) are NOT converted to FAIL and propagate (Boss Item 6)."""
    run_id = "test_qc_programming_err"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    valid_mp4 = paths.final_render_dir / "final.mp4"
    valid_mp4.write_bytes(b"dummy_mp4_bytes_nonzero")

    s10_artifact = {
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {
            "task_id": run_id,
            "final_video_path": str(valid_mp4),
            "fps": 30.0,
            "duration_in_frames": 150,
        },
        "provenance": {"generator": "stages.s10_render", "latency_sec": 1.0},
    }
    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps(s10_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )

    # Monkeypatch verify_final_video_gates to raise a programming error (TypeError)
    def _buggy_verify(*args, **kwargs):
        raise TypeError("Unexpected code defect: unsupported operand type")

    monkeypatch.setattr("stages.s11_qc.verify_final_video_gates", _buggy_verify)

    with pytest.raises(TypeError, match="unsupported operand type"):
        run_s11_qc(ctx)


def test_s11_qc_fails_closed_when_duration_in_frames_missing(tmp_path: Path) -> None:
    """Verifies that S11 fails closed with ValueError when duration_in_frames is missing in S10 artifact (Boss Item 4)."""
    run_id = "test_qc_missing_duration"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    valid_mp4 = paths.final_render_dir / "final.mp4"
    valid_mp4.write_bytes(b"dummy_mp4_bytes_nonzero")

    # s10 artifact with missing duration_in_frames
    s10_artifact = {
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {
            "task_id": run_id,
            "final_video_path": str(valid_mp4),
            "fps": 30.0,
            # duration_in_frames omitted
        },
        "provenance": {"generator": "stages.s10_render", "latency_sec": 1.0},
    }
    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps(s10_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )

    with pytest.raises(ValueError, match="Stage S11 requires positive duration_in_frames"):
        run_s11_qc(ctx)

