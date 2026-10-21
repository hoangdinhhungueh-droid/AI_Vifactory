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

    # Authoritative task-local plan (Rule 128 & Boss Item 6)
    local_dp = paths.root / "director_plan.json"
    local_dp.parent.mkdir(parents=True, exist_ok=True)
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "scenes": [{
            "idx": 0,
            "narration": "Authoritative test narration for scene 0",
            "bg_prompt": "Detailed archival workspace newsprint background",
            "fg": [{"id": "fg_0_0", "prompt": "Tactile forensic document specimen element"}],
            "camera": "push_in",
            "duration_in_frames": 150,
        }]
    }), encoding="utf-8")

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

    # Authoritative task-local plan (Rule 128 & Boss Item 6)
    local_dp = paths.root / "director_plan.json"
    local_dp.parent.mkdir(parents=True, exist_ok=True)
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "scenes": [{
            "idx": 0,
            "narration": "Authoritative test narration for scene 0",
            "bg_prompt": "Detailed archival workspace newsprint background",
            "fg": [{"id": "fg_0_0", "prompt": "Tactile forensic document specimen element"}],
            "camera": "push_in",
            "duration_in_frames": 150,
        }]
    }), encoding="utf-8")

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



def test_s11_qc_fails_closed_on_malformed_authoritative_plan(tmp_path: Path) -> None:
    """Verifies that S11 fails closed with ValueError when authoritative plan is missing or malformed (Rule 128 & Boss Item 6)."""
    run_id = "test_qc_malformed_plan"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    valid_mp4 = paths.final_render_dir / "final.mp4"
    valid_mp4.write_bytes(b"dummy_mp4_bytes")

    # 1. Missing both remotion_props_file and local director_plan
    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps({
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {
            "task_id": run_id,
            "final_video_path": str(valid_mp4),
            "fps": 30.0,
            "duration_in_frames": 150,
        },
        "provenance": {"generator": "stages.s10_render"},
    }), encoding="utf-8")

    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=RunManifest.create_new(run_id, profile="e2e_min"),
        config=load_profile("e2e_min"),
        force=True,
        dry_run=False,
    )

    with pytest.raises(ValueError, match="No authoritative ScenePlan found"):
        run_s11_qc(ctx)

    # 2. Malformed remotion_props_file (broken JSON)
    bad_props = paths.root / "broken_props.json"
    bad_props.write_text("{broken_json", encoding="utf-8")
    s10_art_file.write_text(json.dumps({
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {
            "task_id": run_id,
            "final_video_path": str(valid_mp4),
            "fps": 30.0,
            "duration_in_frames": 150,
            "remotion_props_file": str(bad_props),
        },
        "provenance": {"generator": "stages.s10_render"},
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed authoritative remotion_props_file"):
        run_s11_qc(ctx)

    # 3. Empty scenes in local director_plan
    local_dp = paths.root / "director_plan.json"
    local_dp.write_text(json.dumps({"title": "Empty", "scenes": []}), encoding="utf-8")
    s10_art_file.write_text(json.dumps({
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {
            "task_id": run_id,
            "final_video_path": str(valid_mp4),
            "fps": 30.0,
            "duration_in_frames": 150,
        },
        "provenance": {"generator": "stages.s10_render"},
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="Empty scenes list in run-local director_plan"):
        run_s11_qc(ctx)


def test_s11_qc_fails_closed_on_missing_narration_or_bg_prompt(tmp_path: Path) -> None:
    """Verifies S11 fails closed when narration is missing or bg_prompt is under 10 chars."""
    run_id = "test_qc_narration_bg"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)
    valid_mp4 = paths.final_render_dir / "final.mp4"
    valid_mp4.write_bytes(b"dummy_mp4_bytes")

    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps({
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {"task_id": run_id, "final_video_path": str(valid_mp4), "fps": 30.0, "duration_in_frames": 150},
        "provenance": {"generator": "stages.s10_render"},
    }), encoding="utf-8")

    # 1. Missing narration
    local_dp = paths.root / "director_plan.json"
    local_dp.parent.mkdir(parents=True, exist_ok=True)
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "scenes": [{
            "idx": 0,
            "narration": "",
            "bg_prompt": "Detailed archival workspace newsprint background",
            "fg": [{"id": "fg_0_0", "prompt": "Tactile forensic document specimen element"}],
            "camera": "push_in",
        }]
    }), encoding="utf-8")

    ctx = RunContext(
        run_id=run_id, paths=paths, manifest=RunManifest.create_new(run_id, profile="e2e_min"),
        config=load_profile("e2e_min"), force=True, dry_run=False,
    )
    with pytest.raises(ValueError, match="missing required non-empty 'narration'"):
        run_s11_qc(ctx)

    # 2. Too short bg_prompt (< 10 chars)
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "scenes": [{
            "idx": 0,
            "narration": "Authoritative valid narration text",
            "bg_prompt": "short",
            "fg": [{"id": "fg_0_0", "prompt": "Tactile forensic document specimen element"}],
            "camera": "push_in",
        }]
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required 'bg_prompt'"):
        run_s11_qc(ctx)


def test_s11_qc_fails_closed_on_invalid_camera_or_empty_fg(tmp_path: Path) -> None:
    """Verifies S11 fails closed on invalid camera move enum or empty FG list."""
    run_id = "test_qc_camera_fg"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)
    valid_mp4 = paths.final_render_dir / "final.mp4"
    valid_mp4.write_bytes(b"dummy_mp4_bytes")

    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps({
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {"task_id": run_id, "final_video_path": str(valid_mp4), "fps": 30.0, "duration_in_frames": 150},
        "provenance": {"generator": "stages.s10_render"},
    }), encoding="utf-8")

    # 1. Invalid camera move
    local_dp = paths.root / "director_plan.json"
    local_dp.parent.mkdir(parents=True, exist_ok=True)
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "scenes": [{
            "idx": 0,
            "narration": "Authoritative valid narration text",
            "bg_prompt": "Detailed archival workspace newsprint background",
            "fg": [{"id": "fg_0_0", "prompt": "Tactile forensic document specimen element"}],
            "camera": "hyperspace_jump_invalid",
        }]
    }), encoding="utf-8")

    ctx = RunContext(
        run_id=run_id, paths=paths, manifest=RunManifest.create_new(run_id, profile="e2e_min"),
        config=load_profile("e2e_min"), force=True, dry_run=False,
    )
    with pytest.raises(ValueError, match="has invalid camera move 'hyperspace_jump_invalid'"):
        run_s11_qc(ctx)

    # 2. Empty FG list
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "scenes": [{
            "idx": 0,
            "narration": "Authoritative valid narration text",
            "bg_prompt": "Detailed archival workspace newsprint background",
            "fg": [],
            "camera": "push_in",
        }]
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required 'fg' objects list"):
        run_s11_qc(ctx)


def test_s11_qc_fails_closed_on_run_id_mismatch(tmp_path: Path) -> None:
    """Verifies S11 fails closed when declared plan identity contradicts expected run identity."""
    run_id = "test_qc_identity_expected"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)
    valid_mp4 = paths.final_render_dir / "final.mp4"
    valid_mp4.write_bytes(b"dummy_mp4_bytes")

    s10_art_file = paths.artifact_file(StageID.S10_RENDER.value)
    s10_art_file.parent.mkdir(parents=True, exist_ok=True)
    s10_art_file.write_text(json.dumps({
        "run_id": run_id,
        "stage": StageID.S10_RENDER.value,
        "status": "ok",
        "payload": {"task_id": run_id, "final_video_path": str(valid_mp4), "fps": 30.0, "duration_in_frames": 150},
        "provenance": {"generator": "stages.s10_render"},
    }), encoding="utf-8")

    local_dp = paths.root / "director_plan.json"
    local_dp.parent.mkdir(parents=True, exist_ok=True)
    local_dp.write_text(json.dumps({
        "title": "Test Plan",
        "episode_id": "CONTRADICTORY_OTHER_RUN_ID",
        "scenes": [{
            "idx": 0,
            "narration": "Authoritative valid narration text",
            "bg_prompt": "Detailed archival workspace newsprint background",
            "fg": [{"id": "fg_0_0", "prompt": "Tactile forensic document specimen element"}],
            "camera": "push_in",
        }]
    }), encoding="utf-8")

    ctx = RunContext(
        run_id=run_id, paths=paths, manifest=RunManifest.create_new(run_id, profile="e2e_min"),
        config=load_profile("e2e_min"), force=True, dry_run=False,
    )
    with pytest.raises(ValueError, match="contradicts expected run identity"):
        run_s11_qc(ctx)
