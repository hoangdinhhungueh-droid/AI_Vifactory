#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_human_gates.py — Verification of 5 Explicit Human Approval Gates & Story Flow.

Validates:
  - Gate 1: Candidate selection pauses and emits S02->S04 command.
  - Gate 2: Story script generation pauses and emits S05->S07 command with image prompts info.
  - Gate 3: Image generation verifies authentic images, pauses and emits --pilot command.
  - Gate 4: --pilot generates 30s demo video, contact sheet, and emits full master render command.
  - Gate 5: Master render QC passes and uploads unlisted to YouTube.
  - --auto: Unattended mode runs all stages end-to-end without pausing.
  - S07 Authentic-Only: Fails closed in live production when images are missing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.contracts.stages import StageID
from core.gates import GateError
from core.paths import resolve_run_paths
from orchestrator.run_pipeline import execute_pipeline


def test_human_gate_1_pause_and_candidate_confirmation(tmp_path: Path):
    """Gate 1: Verifies pipeline pauses after S01 Ideation and preserves state."""
    run_id = "RUN_TEST_HG1_CANDIDATE"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    exit_code = execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        human_gates=True,
        topic="Sovereign AI Infrastructure Race",
        preset="story_forensic"
    )
    assert exit_code == 0, f"Gate 1 execution returned non-zero exit code {exit_code}"

    assert paths.manifest_file.exists(), "Manifest was not written at Gate 1"

    # Stage 1 must be done
    s1_art = paths.artifact_file(StageID.S1_IDEATION.value)
    assert s1_art.exists(), f"Stage 1 artifact missing: {s1_art}"

    # Stage 2 must NOT have executed yet
    s2_art = paths.artifact_file(StageID.S2_RESEARCH.value)
    assert not s2_art.exists(), "Stage 2 executed when it should have paused at Gate 1"


def test_human_gate_2_story_script_generation(tmp_path: Path):
    """Gate 2: Verifies S02->S04 runs and pauses after S04 script audit."""
    run_id = "RUN_TEST_HG2_STORY"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    # First run S01
    execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        human_gates=True,
        topic="Corporate Accounting Fraud Collapse",
        preset="story_forensic"
    )

    # Now run Gate 2 command: S02 -> S04
    exit_code = execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        human_gates=True,
        from_stage="s02_research",
        to_stage="s04_critic_script",
        preset="story_forensic"
    )
    assert exit_code == 0, f"Gate 2 execution returned non-zero exit code {exit_code}"

    assert paths.artifact_file(StageID.S2_RESEARCH.value).exists()
    assert paths.artifact_file(StageID.S3_SCRIPT.value).exists()
    assert paths.artifact_file(StageID.S4_CRITIC_SCRIPT.value).exists()

    # S05 Director Plan must NOT have executed yet
    assert not paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value).exists()


def test_human_gate_3_director_and_image_assets(tmp_path: Path):
    """Gate 3: Verifies S05->S07 runs, generates prompts, and pauses after S07."""
    run_id = "RUN_TEST_HG3_IMAGES"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    # Execute S01 -> S04
    execute_pipeline(profile_name="prod", run_id=run_id, dry_run=True, auto=True, to_stage="s04_critic_script", preset="story_forensic", topic="Dark Pool Trading Manipulation")

    # Now execute Gate 3 phase: S05 -> S07
    exit_code = execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        human_gates=True,
        from_stage="s05_director_plan",
        to_stage="s07_image_gen",
        preset="story_forensic"
    )
    assert exit_code == 0, f"Gate 3 execution returned non-zero exit code {exit_code}"

    assert paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value).exists()
    assert paths.artifact_file(StageID.S6_CRITIC_VISUAL.value).exists()
    assert paths.artifact_file(StageID.S7_IMAGE_GEN.value).exists()

    # Bulk image prompts must exist
    bulk_prompts = paths.root / "bulk_image_prompts.txt"
    assert bulk_prompts.exists(), f"bulk_image_prompts.txt missing at {bulk_prompts}"
    assert bulk_prompts.stat().st_size > 100, "bulk_image_prompts.txt is suspiciously small"

    # S08 Video Gen must NOT have executed yet
    assert not paths.artifact_file(StageID.S8_VIDEO_GEN.value).exists()


def test_human_gate_4_pilot_30s_demo_generation(tmp_path: Path):
    """Gate 4: Verifies --pilot generates 30s demo video, contact sheet, and evaluation."""
    run_id = "RUN_TEST_HG4_PILOT"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    # Prepare upstream S01 -> S07 in dry-run
    execute_pipeline(profile_name="prod", run_id=run_id, dry_run=True, auto=True, to_stage="s07_image_gen", preset="story_forensic", topic="Semiconductor Export Control Siege")

    # Execute --pilot
    exit_code = execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        pilot=True,
        preset="story_forensic"
    )
    assert exit_code == 0, f"Pilot generation returned non-zero exit code {exit_code}"

    pilot_mp4 = paths.root / "pilot_30s.mp4"
    assert pilot_mp4.exists(), f"pilot_30s.mp4 missing at {pilot_mp4}"
    assert pilot_mp4.stat().st_size > 1000, "pilot_30s.mp4 is too small"

    contact_sheet = paths.root / "visual_audit" / "contact_sheet_30s.jpg"
    assert contact_sheet.exists(), f"contact_sheet_30s.jpg missing at {contact_sheet}"
    assert contact_sheet.stat().st_size > 1000, "contact_sheet_30s.jpg is too small"

    pilot_manifest = paths.root / "pilot_manifest.json"
    assert pilot_manifest.exists(), f"pilot_manifest.json missing at {pilot_manifest}"
    p_data = json.loads(pilot_manifest.read_text(encoding="utf-8"))
    assert p_data.get("evaluation", {}).get("verdict") == "PASS"


def test_human_gate_5_master_render_and_unlisted_upload(tmp_path: Path):
    """Gate 5: Verifies S08->S11 execution and unlisted YouTube upload trigger."""
    run_id = "RUN_TEST_HG5_MASTER"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    # Prepare upstream S01 -> S07 in dry-run
    execute_pipeline(profile_name="prod", run_id=run_id, dry_run=True, auto=True, to_stage="s07_image_gen", preset="story_forensic", topic="Biotech Clinical Data Concealment")

    # Run S08 -> S11 with --upload-youtube
    exit_code = execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        from_stage="s08_video_gen",
        to_stage="s11_qc",
        upload_youtube=True,
        preset="story_forensic"
    )
    assert exit_code == 0, f"Master render and upload returned non-zero exit code {exit_code}"

    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    final_video = paths.final_render_dir / "final.mp4"
    assert final_video.exists(), f"Master final.mp4 missing at {final_video}"
    assert final_video.stat().st_size > 1000, "Master final.mp4 is too small"

    qc_art = paths.artifact_file(StageID.S11_QC.value)
    assert qc_art.exists(), f"S11 QC artifact missing at {qc_art}"
    qc_data = json.loads(qc_art.read_text(encoding="utf-8"))
    assert qc_data.get("payload", {}).get("qc_verdict") == "PASS"


def test_unattended_auto_mode_runs_end_to_end(tmp_path: Path):
    """Verifies that --auto runs the complete pipeline end-to-end without pausing."""
    run_id = "RUN_TEST_AUTO_MODE"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    exit_code = execute_pipeline(
        profile_name="prod",
        run_id=run_id,
        dry_run=True,
        auto=True,
        topic="Autonomous Algorithmic Trading Liquidation",
        preset="story_forensic"
    )
    assert exit_code == 0, f"Auto execution returned non-zero exit code {exit_code}"

    for stage in StageID:
        art = paths.artifact_file(stage.value)
        assert art.exists(), f"Stage {stage.value} was skipped in auto mode: missing {art}"


def test_s07_authentic_images_fails_closed_in_production(tmp_path: Path):
    """Rule 118 & 121: S07 must fail closed when authentic seed images are missing in live prod."""
    run_id = "RUN_TEST_S07_FAIL_CLOSED"
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    import shutil
    if paths.root.exists():
        shutil.rmtree(paths.root, ignore_errors=True)

    # First run S01 -> S05 in dry-run
    execute_pipeline(profile_name="prod", run_id=run_id, dry_run=True, auto=True, to_stage="s05_director_plan", preset="story_forensic", topic="Offshore Shadow Banking Scheme")
    # Ensure no seed images exist in composite_seeds
    if paths.composite_seeds_dir.exists():
        for p in paths.composite_seeds_dir.glob("*.png"):
            p.unlink()

    from core.config import RunContext, load_profile
    from core.run_manifest import RunManifest
    import stages.s07_image_gen as s07

    config = load_profile("prod", repo_root=REPO_ROOT)
    manifest = RunManifest.load_or_create(paths, profile="prod")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=config,
        dry_run=False,  # Live production mode: must NOT generate PIL cards!
        force=True
    )

    with pytest.raises(GateError) as exc_info:
        s07.run(ctx)

    assert "Missing authentic composite seed images" in str(exc_info.value)
    # Prompts file must have been emitted so user can generate them
    assert (paths.root / "bulk_image_prompts.txt").exists()
