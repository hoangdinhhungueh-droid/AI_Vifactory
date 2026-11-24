#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_s07_image_gen.py — Unit tests for Stage S7 Image Generation (AVF-STAB-001).

Guarantees:
1. S07 emits story-specific 3-layer manifests and camera cues in bulk_image_prompts.txt and decomposed_layer_prompts.json.
2. S07 slices or synthesizes modular asset frames (stage, hero, tool, supp) in composite_seeds_dir.
3. S07 attaches master_scene_manifest to scenes and returns them in payload.
4. S07 fails closed with GateError in production when authentic seed images are missing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import stages.s07_image_gen as s07_image_gen
from core.config import RunContext, load_profile
from core.contracts.stages import StageArtifact, StageID
from core.gates import GateError
from core.paths import resolve_run_paths
from core.run_manifest import RunManifest


def test_s07_image_gen_emits_3_layer_manifests_and_camera_cues(tmp_path: Path):
    """Verifies that S07 exports 3-layer manifests, camera cues, and modular asset frames in hermetic mode."""
    run_id = "test_s07_manifest_01"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.composite_seeds_dir.mkdir(parents=True, exist_ok=True)

    # Prepare upstream S5 artifact
    s5_data = {
        "run_id": run_id,
        "stage": "s05_director_plan",
        "status": "ok",
        "payload": {
            "scenes": [
                {
                    "scene_id": "SCENE_01",
                    "headline": "SHIPPING MANIFEST AUDIT",
                    "narration": "Customs inspectors detected an illegal bill of lading hiding $48.6B in cargo.",
                    "stat_hero": "$48.6B",
                    "stat_label": "CONCEALED CARGO VALUE",
                    "hero_cutout_object": "Official Shipping Bill of Lading",
                    "interacting_tool": "Forensic Caliper",
                    "duration_est_sec": 5.0,
                }
            ]
        }
    }
    s5_file = paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    s5_file.parent.mkdir(parents=True, exist_ok=True)
    s5_file.write_text(json.dumps(s5_data), encoding="utf-8")

    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    cfg = load_profile("e2e_min")

    class DummyPreset:
        name = "story_forensic"

    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        preset=DummyPreset(),
        dry_run=True,
    )

    art = s07_image_gen.run(ctx)
    assert isinstance(art, StageArtifact)
    assert art.status == "ok"
    assert art.payload["total_images"] == 1

    # 1. Verify bulk_image_prompts.txt
    bulk_prompts_file = paths.root / "bulk_image_prompts.txt"
    assert bulk_prompts_file.exists()
    bulk_text = bulk_prompts_file.read_text(encoding="utf-8")
    assert "LAYER 1: BACKGROUND DESK (#F4F1EA)" in bulk_text
    assert "LAYER 2: HERO CUTOUT" in bulk_text
    assert "LAYER 2: SUPPORTING CUTOUTS" in bulk_text
    assert "CAMERA CUE SHEET" in bulk_text

    # 2. Verify decomposed_layer_prompts.json
    decomp_file = paths.root / "decomposed_layer_prompts.json"
    assert decomp_file.exists()
    decomp_json = json.loads(decomp_file.read_text(encoding="utf-8"))
    assert "SCENE_01" in decomp_json
    sc_decomp = decomp_json["SCENE_01"]
    assert "master_scene_manifest" in sc_decomp
    assert "layer_1_background" in sc_decomp
    assert sc_decomp["layer_1_background"]["background_color"] == "#F4F1EA"
    assert "layer_2_midground" in sc_decomp
    assert sc_decomp["layer_2_midground"]["hero_cutout"]["cutout_border"] == "#FFFFFF"
    assert "layer_3_foreground" in sc_decomp
    assert sc_decomp["layer_3_foreground"]["data_counters"][0]["stat_hero"] == "$48.6B"
    assert "camera_cue_sheet" in sc_decomp
    assert len(sc_decomp["camera_cue_sheet"]) >= 3

    # 3. Verify modular seed image frames were generated in seeds_dir
    assert (paths.composite_seeds_dir / "composite_scene_01.png").exists()
    assert (paths.composite_seeds_dir / "stage_scene_01.png").exists()
    assert (paths.composite_seeds_dir / "hero_scene_01.png").exists()
    assert (paths.composite_seeds_dir / "tool_scene_01.png").exists()
    assert (paths.composite_seeds_dir / "supp_scene_01.png").exists()

    # 4. Verify payload contains scenes enriched with master_scene_manifest
    assert "scenes" in art.payload
    assert len(art.payload["scenes"]) == 1
    assert "master_scene_manifest" in art.payload["scenes"][0]


def test_s07_image_gen_fails_closed_in_production_when_seeds_missing(tmp_path: Path):
    """Rule 118 & 121: Verifies S07 raises GateError in production mode when seed images are absent."""
    run_id = "test_s07_fail_closed"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.composite_seeds_dir.mkdir(parents=True, exist_ok=True)

    s5_data = {
        "run_id": run_id,
        "stage": "s05_director_plan",
        "status": "ok",
        "payload": {
            "scenes": [
                {
                    "scene_id": "SCENE_01",
                    "headline": "CONCEALED RECORDS",
                    "narration": "Inspectors discovered missing records.",
                }
            ]
        }
    }
    s5_file = paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    s5_file.parent.mkdir(parents=True, exist_ok=True)
    s5_file.write_text(json.dumps(s5_data), encoding="utf-8")

    manifest = RunManifest.create_new(run_id, profile="prod")
    cfg = load_profile("prod")

    class DummyPreset:
        name = "story_forensic"

    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        preset=DummyPreset(),
        dry_run=False,
    )

    with pytest.raises(GateError) as exc_info:
        s07_image_gen.run(ctx)

    assert "Missing authentic composite seed images" in str(exc_info.value)
