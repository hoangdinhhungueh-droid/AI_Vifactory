#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_s05_director_plan.py — Unit Tests & Regression Gate for Stage S05 Director Plan (Boss Item 17).

Verifies:
1. Stage S05 loads s3_artifact_path correctly via json.load without NameError ('s3_data').
2. Universal video prompts and scene cutouts are generated deterministically.
3. Missing S3 artifact raises FileNotFoundError cleanly.
"""

import json
from pathlib import Path

import pytest

from core.config import RunContext, load_profile
from core.contracts.stages import StageID
from core.paths import resolve_run_paths
from core.run_manifest import RunManifest
from stages.s05_director_plan import build_universal_video_prompt, run


@pytest.fixture
def mock_s05_context(tmp_path: Path) -> RunContext:
    """Creates a hermetic RunContext rooted in tmp_path."""
    run_id = "TEST_EP0099_s05_unit"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    cfg = load_profile("e2e_min")
    cfg.market = "EN"
    manifest = RunManifest.create_new(run_id, profile="e2e_min", market="EN")
    return RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )


def test_build_universal_video_prompt():
    """Verify build_universal_video_prompt formats prompt with required timeline segments."""
    from core.contracts.stages import Scene
    sc = Scene(
        scene_id="SC_01",
        narration="In 2008 the liquidity crisis crippled the commercial paper market.",
        visual_metaphor="Tactile brass vault key",
        color_accent="Vox Crimson #E53935",
        headline="LIQUIDITY CONTRACTION",
        market="EN",
    )
    prompt = build_universal_video_prompt(sc)
    assert "Forensic documentary motion graphics" in prompt
    assert "Tactile brass vault key" in prompt
    assert "KINETIC CAUSAL CHAIN" in prompt
    assert "PHYSICAL CONSTRAINTS" in prompt


def test_s05_director_plan_execution_and_s3_data_loading(mock_s05_context: RunContext):
    """Regression Test for NameError: 's3_data' is not defined (Boss Item 17).

    Verifies that run(ctx) reads S3 artifact from disk, constructs scenes and shots,
    and returns a valid StageArtifact.
    """
    ctx = mock_s05_context
    s3_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    s3_path.parent.mkdir(parents=True, exist_ok=True)

    s3_payload = {
        "schema_version": "1.0.0",
        "run_id": ctx.run_id,
        "stage": StageID.S3_SCRIPT.value,
        "status": "ok",
        "provenance": {
            "generator": "test_s05_director_plan",
        },
        "payload": {
            "script_text": "The 2008 financial crisis crippled the commercial paper market.",
            "scenes": [
                {
                    "scene_id": "SC_01",
                    "narration": "The 2008 financial crisis crippled the commercial paper market.",
                    "visual_metaphor": "Tactile paper balance sheet burning",
                    "headline": "LIQUIDITY CRISIS",
                    "color_accent": "Vox Crimson #C82828",
                },
                {
                    "scene_id": "SC_02",
                    "narration": "Interbank credit froze almost overnight as institutions stopped lending.",
                    "visual_metaphor": "Vault gates locking shut",
                    "headline": "CREDIT FREEZE",
                    "color_accent": "Navy #1B2B4A",
                },
            ],
        },
    }
    s3_path.write_text(json.dumps(s3_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Execute Stage S05
    artifact = run(ctx)

    # 1. Stage Artifact Integrity
    assert artifact.status == "ok"
    assert artifact.stage == StageID.S5_DIRECTOR_PLAN
    assert artifact.run_id == ctx.run_id

    # 2. Payload Structure
    payload = artifact.payload
    assert payload["total_scenes"] == 2
    assert len(payload["scenes"]) == 2

    # 3. Shot and Universal Video Prompt Validation
    sc1 = payload["scenes"][0]
    assert sc1["scene_id"] == "SC_01"
    assert len(sc1["shots"]) == 1
    shot1 = sc1["shots"][0]
    assert "Forensic documentary motion graphics" in shot1["visual_prompt"]
    assert "Tactile paper balance sheet burning" in shot1["visual_prompt"]

    # 4. Artifact written to disk
    out_artifact_path = ctx.paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    assert out_artifact_path.exists()
    written_data = json.loads(out_artifact_path.read_text(encoding="utf-8"))
    assert written_data["payload"]["total_scenes"] == 2


def test_s05_director_plan_missing_s3_raises_file_not_found(mock_s05_context: RunContext):
    """When S3 script artifact is absent, stage must fail-closed with FileNotFoundError."""
    ctx = mock_s05_context
    s3_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    if s3_path.exists():
        s3_path.unlink()

    with pytest.raises(FileNotFoundError, match="Missing S3 artifact"):
        run(ctx)
