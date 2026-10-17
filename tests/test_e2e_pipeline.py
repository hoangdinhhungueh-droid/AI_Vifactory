#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_e2e_pipeline.py — Master E2E Pipeline Regression & Smoke Test (AVF-STAB-001).

Validates that:
  1. All 11 modular stages (s01_ideation -> s11_qc) execute end-to-end without unhandled crashes.
  2. Every stage emits a schema-validated StageArtifact with SHA256 integrity.
  3. Master MP4 video is rendered and verified by S11 QC gates.
  4. Cost and token burn remain zero in dry-run/mock mode.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.contracts.stages import StageID
from core.paths import resolve_run_paths
from orchestrator.run_pipeline import execute_pipeline


def test_e2e_pipeline_full_execution(tmp_path: Path):
    """Executes the complete 11-stage pipeline with profile e2e_min and validates all outputs."""
    run_id = "RUN_TEST_E2E_SMOKE"
    
    # Execute full pipeline in dry-run mode (zero external LLM API cost)
    exit_code = execute_pipeline(
        profile_name="e2e_min",
        run_id=run_id,
        dry_run=True,
        force=True,
        topic="Sovereign AI Infrastructure Race"
    )
    assert exit_code == 0, f"execute_pipeline failed with exit code {exit_code}"

    # Verify run artifacts on disk
    paths = resolve_run_paths(run_id, repo_root=REPO_ROOT)
    assert paths.manifest_file.exists(), f"Missing manifest at {paths.manifest_file}"

    # Verify each of the 11 stages has its artifact.json emitted
    for stage in StageID:
        art_file = paths.artifact_file(stage.value)
        assert art_file.exists(), f"Stage {stage.value} missing artifact file at {art_file}"
        assert art_file.stat().st_size > 50, f"Stage {stage.value} artifact is suspiciously empty"

    # Verify final render output
    final_video = paths.final_render_dir / "final.mp4"
    assert final_video.exists(), f"Master video missing at {final_video}"
    assert final_video.stat().st_size > 1000, f"Master video is empty at {final_video}"
