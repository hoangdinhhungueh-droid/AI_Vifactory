#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_s05_fail_closed.py
Unit tests verifying Stage S05 fails closed when vox.planner raises on script_text with empty raw_scenes (Boss Round 12 Item 7).
"""

import json
import pytest
from unittest.mock import patch
from pathlib import Path

from stages.s05_director_plan import run
from core.config import RunContext, load_profile
from core.paths import RunPaths
from core.run_manifest import RunManifest
from core.contracts.stages import StageID, StageArtifact, Provenance


def _build_test_ctx(run_id: str, tmp_path: Path) -> RunContext:
    paths = RunPaths(run_id=run_id, repo_root=tmp_path)
    manifest = RunManifest(run_id=run_id)
    config = load_profile("e2e_min")
    return RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=config,
    )


def test_s05_fails_closed_when_vox_planner_raises_with_empty_scenes(tmp_path):
    """When S3 artifact has script_text but empty scenes, if plan_scenes_from_script raises,
    S05 must fail closed by raising RuntimeError (Boss Round 12 Item 7).
    """
    run_id = "test_run_s05_fail_closed"
    ctx = _build_test_ctx(run_id, tmp_path)
    s3_dir = ctx.paths.stage_dir(StageID.S3_SCRIPT.value)
    s3_dir.mkdir(parents=True, exist_ok=True)
    s3_file = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    s3_art = StageArtifact(
        run_id=run_id,
        stage=StageID.S3_SCRIPT,
        status="ok",
        payload={
            "script_text": "Sample script text for video narration...",
            "scenes": [],
        },
        provenance=Provenance(generator="test", latency_sec=0.1),
    )
    s3_file.write_text(json.dumps(s3_art.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    with patch("stages.s05_director_plan.plan_scenes_from_script", side_effect=RuntimeError("Simulated LLM Planner Failure")):
        with pytest.raises(RuntimeError) as exc_info:
            run(ctx)
        assert "Stage S05 failed closed" in str(exc_info.value)


def test_s05_fails_closed_when_no_scenes_available(tmp_path):
    """When S3 artifact has empty script_text and empty scenes, S05 must fail closed."""
    run_id = "test_run_s05_empty"
    ctx = _build_test_ctx(run_id, tmp_path)
    s3_dir = ctx.paths.stage_dir(StageID.S3_SCRIPT.value)
    s3_dir.mkdir(parents=True, exist_ok=True)
    s3_file = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    s3_art = StageArtifact(
        run_id=run_id,
        stage=StageID.S3_SCRIPT,
        status="ok",
        payload={
            "script_text": "",
            "scenes": [],
        },
        provenance=Provenance(generator="test", latency_sec=0.1),
    )
    s3_file.write_text(json.dumps(s3_art.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        run(ctx)
    assert "Stage S05 failed closed" in str(exc_info.value)
