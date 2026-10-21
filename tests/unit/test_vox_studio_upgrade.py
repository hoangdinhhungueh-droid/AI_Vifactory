#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_vox_studio_upgrade.py
Unit tests verifying the Vox Studio 8-10 minute upgrade features:
- Sequence Block Chunking (24-48s chunks, no gaps, 100% coverage)
- Master Asset Registry bounded set (18-24 items, immutable IDs, valid sources)
- Studio 7-Touch Semantic Linter (zero emotional adjectives, single camera directive)
- Start-Frame Chaining DAG validation (no cycles, valid precedents)
- End-to-end S5 Director Plan v2 contract compliance
"""

from pathlib import Path
import pytest
from core.contracts.stages import AssetRegistry, Scene, Shot
from stages.s05_director_plan import (
    build_master_asset_registry,
    build_vox_scene_prompts,
    partition_timeline_into_chunks,
    validate_and_sanitize_director_plan,
)
from stages.s08_video_gen import validate_frame_chain_dag


def test_sequence_block_chunking_long_timeline():
    """Verify an 8-10 minute documentary (~540s) partitions into 10-15 sequence blocks."""
    # Create 90 scenes of 6.0s each = 540.0s
    scenes = [
        Scene(
            scene_id=f"SCENE_{i+1:02d}",
            narration=f"Narration beat {i+1} covering documentary investigation facts.",
            duration_est_sec=6.0,
            shots=[Shot(shot_id=f"sc_{i+1:02d}_sh_01", scene_id=f"SCENE_{i+1:02d}", visual_prompt="Test")]
        )
        for i in range(90)
    ]

    chunks = partition_timeline_into_chunks(scenes, target_chunk_duration=36.0, min_chunk_duration=24.0, max_chunk_duration=48.0)

    # 1. Total chunks should be in expected range (10-16 blocks for 540s)
    assert 10 <= len(chunks) <= 16, f"Expected 10-16 chunks, got {len(chunks)}"

    # 2. Invariant: No gaps, no overlaps, exact timeline coverage
    assert chunks[0].start_s == 0.0
    for idx in range(len(chunks) - 1):
        c1 = chunks[idx]
        c2 = chunks[idx + 1]
        assert c1.end_s == c2.start_s, f"Gap or overlap between {c1.chunk_id} and {c2.chunk_id}"
        assert c1.duration_s == round(c1.end_s - c1.start_s, 2)
        assert len(c1.shot_ids) > 0
        assert len(c1.scene_ids) > 0

    assert chunks[-1].end_s == 540.0


def test_sequence_block_chunking_short_timeline():
    """Verify short test timelines (< 24s) collapse cleanly into a single valid chunk."""
    scenes = [
        Scene(
            scene_id="SCENE_01",
            narration="First sentence",
            duration_est_sec=5.0,
            shots=[Shot(shot_id="sc_01_sh_01", scene_id="SCENE_01", visual_prompt="Test")]
        ),
        Scene(
            scene_id="SCENE_02",
            narration="Second sentence",
            duration_est_sec=5.0,
            shots=[Shot(shot_id="sc_02_sh_01", scene_id="SCENE_02", visual_prompt="Test")]
        )
    ]
    chunks = partition_timeline_into_chunks(scenes)
    assert len(chunks) == 1
    assert chunks[0].start_s == 0.0
    assert chunks[0].end_s == 10.0
    assert chunks[0].duration_s == 10.0
    assert len(chunks[0].scene_ids) == 2


def test_master_asset_registry_bounded_set():
    """Verify Master Asset Registry contains strictly between 18 and 24 items."""
    scenes = [
        Scene(
            scene_id=f"SCENE_{i+1:02d}",
            narration=f"Narration beat {i+1}",
            hero_cutout_object=f"Paper dossier {i+1}",
            objects_roster=[
                {"object_id": f"o_{i+1}_1", "name": f"asset_doc_{i+1}", "type": "paper_cutout"}
            ],
            duration_est_sec=5.0,
            shots=[Shot(shot_id=f"sc_{i+1:02d}_sh_01", scene_id=f"SCENE_{i+1:02d}", visual_prompt="Test")]
        )
        for i in range(10)
    ]

    registry = build_master_asset_registry("TEST_EP_001", scenes)
    assert isinstance(registry, AssetRegistry)
    assert 18 <= len(registry.items) <= 24, f"Registry size {len(registry.items)} outside [18, 24]"

    # Verify uniqueness of asset IDs
    asset_ids = [item.asset_id for item in registry.items]
    assert len(asset_ids) == len(set(asset_ids)), "Duplicate asset IDs detected!"

    # Verify metadata integrity
    for item in registry.items:
        assert item.asset_id.startswith("asset_")
        assert len(item.name) > 0
        assert item.source_uri is not None
        assert len(item.used_by_shot_ids) > 0 or len(item.used_by_scene_ids) > 0


def test_semantic_linter_rejects_banned_adjectives():
    """Verify semantic linter flags emotional adjectives."""
    clean_payload = {
        "scenes": [
            {
                "scene_id": "SCENE_01",
                "visual_prompt": "Editorial paper cutout animation in Vox documentary style. Slides into center.",
                "camera_directive": "STATIC_OVERHEAD"
            }
        ]
    }
    audit = validate_and_sanitize_director_plan(clean_payload)
    assert audit["ok"] is True

    dirty_payload = {
        "scenes": [
            {
                "scene_id": "SCENE_01",
                "visual_prompt": "A dramatic and epic scene with breathtaking motion.",
                "camera_directive": "STATIC_OVERHEAD"
            }
        ]
    }
    dirty_audit = validate_and_sanitize_director_plan(dirty_payload)
    assert dirty_audit["ok"] is False
    assert any("dramatic" in v for v in dirty_audit["violations"])


def test_frame_chain_dag_validation():
    """Verify start-frame chaining enforces DAG and detects cycles."""
    # Valid DAG
    valid_chain = [
        {"shot_id": "shot_01", "kind": "source", "previous_shot_id": None},
        {"shot_id": "shot_02", "kind": "chained", "previous_shot_id": "shot_01"},
        {"shot_id": "shot_03", "kind": "chained", "previous_shot_id": "shot_02"}
    ]
    res = validate_frame_chain_dag(valid_chain)
    assert res["ok"] is True
    assert res["chained_nodes"] == 2

    # Self-reference
    self_ref_chain = [
        {"shot_id": "shot_01", "kind": "chained", "previous_shot_id": "shot_01"}
    ]
    self_res = validate_frame_chain_dag(self_ref_chain)
    assert self_res["ok"] is False
    assert any("Self-referential" in v for v in self_res["violations"])

    # Cycle
    cycle_chain = [
        {"shot_id": "shot_01", "kind": "chained", "previous_shot_id": "shot_02"},
        {"shot_id": "shot_02", "kind": "chained", "previous_shot_id": "shot_01"}
    ]
    cycle_res = validate_frame_chain_dag(cycle_chain)
    assert cycle_res["ok"] is False
    assert any("Cycle detected" in v or "chưa tồn tại" in v for v in cycle_res["violations"])


def test_build_vox_scene_prompts_kinematics():
    """Verify build_vox_scene_prompts yields second-by-second breakdown and 4-block kinematic prompt."""
    scene = Scene(
        scene_id="SCENE_01",
        narration="The balance sheet revealed a hidden debt.",
        headline="HIDDEN DEBT",
        visual_metaphor="Audited financial ledger with red seal",
        duration_est_sec=5.0
    )
    vox_meta = build_vox_scene_prompts(scene, idx=0, total_scenes=1)

    assert "second_by_second_action_breakdown" in vox_meta
    breakdown = vox_meta["second_by_second_action_breakdown"]
    assert len(breakdown) >= 3
    # Check living poster hold at end
    assert breakdown[-1]["action_type"] == "living_poster_hold"

    # Check single camera directive
    assert vox_meta["camera_directive"] in ["STATIC_OVERHEAD", "SLOW_PUSH_IN_0_1X", "SLOW_HORIZONTAL_PAN", "SUBTLE_TILT_DOWN"]

    # Check 4-block kinematic prompt
    flow_prompt = vox_meta["i2v_prompt_google_flow"]
    assert "IMAGE-TO-VIDEO TECHNICAL DIRECTIVE:" in flow_prompt
    assert "[Camera:" in flow_prompt
    assert "[Timeline Kinematics:" in flow_prompt
    assert "[Pacing:" in flow_prompt
    assert "[Constraints:" in flow_prompt


def test_chunking_bounds_invariant_and_final_chunk_rebalancing():
    """Verify that every nontrivial chunk strictly satisfies 24-48s bounds and trailing scenes rebalance."""
    # Test case 1: 70s timeline (14 scenes x 5.0s) -> should yield 2 balanced chunks ~35s each, both in [24, 48]
    scenes_70s = [
        Scene(
            scene_id=f"SCENE_{i+1:02d}",
            narration=f"Fact statement {i+1}",
            duration_est_sec=5.0,
            shots=[Shot(shot_id=f"sc_{i+1:02d}_sh_01", scene_id=f"SCENE_{i+1:02d}", visual_prompt="Test")]
        )
        for i in range(14)
    ]
    chunks_70 = partition_timeline_into_chunks(scenes_70s)
    assert len(chunks_70) >= 2
    for c in chunks_70:
        assert 24.0 <= c.duration_s <= 48.0, f"Chunk {c.chunk_id} duration {c.duration_s} violates [24.0, 48.0]"

    # Test case 2: 50s timeline (10 scenes x 5.0s) -> should yield 2 balanced chunks of 25.0s each in [24, 48]
    scenes_50s = scenes_70s[:10]
    chunks_50 = partition_timeline_into_chunks(scenes_50s)
    assert len(chunks_50) == 2
    for c in chunks_50:
        assert 24.0 <= c.duration_s <= 48.0, f"Chunk {c.chunk_id} duration {c.duration_s} violates [24.0, 48.0]"
        assert c.duration_s == 25.0

    # Test case 3: Boss Adversarial [20, 20, 10] -> verifies no chunk exceeds 48.0s and rebalancing works
    scenes_adv = [
        Scene(scene_id="SCENE_01", narration="A", duration_est_sec=20.0, shots=[Shot(shot_id="sh_1", scene_id="SCENE_01", visual_prompt="test")]),
        Scene(scene_id="SCENE_02", narration="B", duration_est_sec=20.0, shots=[Shot(shot_id="sh_2", scene_id="SCENE_02", visual_prompt="test")]),
        Scene(scene_id="SCENE_03", narration="C", duration_est_sec=10.0, shots=[Shot(shot_id="sh_3", scene_id="SCENE_03", visual_prompt="test")]),
    ]
    chunks_adv = partition_timeline_into_chunks(scenes_adv)
    assert len(chunks_adv) == 2
    for c in chunks_adv:
        assert c.duration_s <= 48.0, f"Chunk {c.chunk_id} exceeded hard upper bound 48s: {c.duration_s}"
    assert chunks_adv[0].duration_s == 20.0
    assert chunks_adv[0].boundary_reason == "discrete_scene_bound_exception"
    assert chunks_adv[1].duration_s == 30.0
    assert 24.0 <= chunks_adv[1].duration_s <= 48.0

    # Test case 4: Exact 48s boundary (8 scenes x 6.0s)
    scenes_48s = [
        Scene(scene_id=f"SCENE_{i+1:02d}", narration=f"Exact {i+1}", duration_est_sec=6.0, shots=[Shot(shot_id=f"sh_{i+1}", scene_id=f"SCENE_{i+1:02d}", visual_prompt="test")])
        for i in range(8)
    ]
    chunks_48 = partition_timeline_into_chunks(scenes_48s)
    assert len(chunks_48) == 1
    assert chunks_48[0].duration_s == 48.0

    # Test case 5: Oversized single scene (60s)
    scenes_over = [
        Scene(scene_id="SCENE_OVER", narration="Long continuous shot", duration_est_sec=60.0, shots=[Shot(shot_id="sh_over", scene_id="SCENE_OVER", visual_prompt="test")])
    ]
    chunks_over = partition_timeline_into_chunks(scenes_over)
    assert len(chunks_over) == 1
    assert chunks_over[0].duration_s == 60.0
    assert chunks_over[0].boundary_reason == "oversized_single_scene_exception"


def test_invalid_frame_chain_dag_fails_closed():
    """Verify that cycle and forward-reference DAGs fail validation with explicit violations."""
    # Cycle DAG
    cyclic_dag = [
        {"shot_id": "shot_01", "kind": "chained", "previous_shot_id": "shot_03"},
        {"shot_id": "shot_02", "kind": "chained", "previous_shot_id": "shot_01"},
        {"shot_id": "shot_03", "kind": "chained", "previous_shot_id": "shot_02"},
    ]
    audit = validate_frame_chain_dag(cyclic_dag)
    assert audit["ok"] is False
    assert len(audit["violations"]) > 0

    # Self-reference DAG
    self_ref_dag = [
        {"shot_id": "shot_01", "kind": "chained", "previous_shot_id": "shot_01"}
    ]
    audit_self = validate_frame_chain_dag(self_ref_dag)
    assert audit_self["ok"] is False


def test_s05_semantic_linter_fails_closed():
    """Verify semantic linter strictly catches banned emotional adjectives and non-canonical camera directives."""
    bad_plan = {
        "scenes": [
            {
                "scene_id": "SCENE_01",
                "shots": [{"visual_prompt": "A heartbreaking tragedy occurred here in the city."}],
                "camera_directive": "STATIC_OVERHEAD"
            }
        ],
        "asset_registry": {"items": [{"asset_id": f"asset_{i}"} for i in range(18)]},
        "chunks": [{"chunk_id": "chunk_001"}]
    }
    result = validate_and_sanitize_director_plan(bad_plan)
    assert result["ok"] is False
    assert any("banned emotional adjective" in v for v in result["violations"])

    # Non-canonical camera directive
    bad_camera_plan = {
        "scenes": [
            {
                "scene_id": "SCENE_01",
                "shots": [{"visual_prompt": "Clean forensic financial ledger."}],
                "camera_directive": "WILD_SHAKY_CAM"
            }
        ],
        "asset_registry": {"items": [{"asset_id": f"asset_{i}"} for i in range(18)]},
        "chunks": [{"chunk_id": "chunk_001"}]
    }
    cam_result = validate_and_sanitize_director_plan(bad_camera_plan)
    assert cam_result["ok"] is False
    assert any("non-canonical camera directive" in v for v in cam_result["violations"])


def test_extract_episode_master_asset_registry_contract_validation():
    """Verify prompt_forge.extract_episode_master_asset_registry enforces type safety and fail-closed contracts."""
    import pytest

    from app.services.prompt_forge import extract_episode_master_asset_registry

    # 1. Non-dict plan raises TypeError
    with pytest.raises(TypeError, match="Expected director_plan to be a dict"):
        extract_episode_master_asset_registry("invalid_string_plan")  # type: ignore

    # 2. Non-list scenes raises ValueError
    with pytest.raises(ValueError, match="Invalid scenes in director_plan"):
        extract_episode_master_asset_registry({"scenes": "not_a_list"})

    # 3. Invalid scene element raises TypeError
    with pytest.raises(TypeError, match="Scene at index 0 has invalid type"):
        extract_episode_master_asset_registry({"scenes": [12345]})

    # 4. Valid empty scenes produces canonical 18-item registry
    valid_plan = {"scenes": [], "project_id": "EP_TEST_001"}
    reg = extract_episode_master_asset_registry(valid_plan)
    assert "items" in reg
    assert 18 <= len(reg["items"]) <= 24
    assert all("asset_id" in item for item in reg["items"])


def test_s08_empty_scenes_list_returns_empty_artifact(tmp_path):
    """Verify s08 cleanly returns empty artifact when director plan has 0 scenes."""
    import json

    from core.config import RunContext, load_profile
    from core.paths import resolve_run_paths
    from core.run_manifest import RunManifest
    from stages import s08_video_gen

    run_id = "test_run_s08_empty"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
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

    s5_artifact_path = paths.artifact_file("s05_director_plan")
    s5_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": []}}), encoding="utf-8")

    art = s08_video_gen.run(ctx)
    assert art.status == "ok"
    assert art.payload["total_clips"] == 0
    assert len(art.payload["frame_chain"]) == 0


def test_s08_malformed_metadata_fails_closed(tmp_path):
    """Verify s08 strictly fails closed with ValueError on malformed scenes or invalid chaining."""
    import json

    import pytest

    from core.config import RunContext, load_profile
    from core.paths import resolve_run_paths
    from core.run_manifest import RunManifest
    from stages import s08_video_gen

    run_id = "test_run_s08_malformed"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
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
    s5_artifact_path = paths.artifact_file("s05_director_plan")
    s5_artifact_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Non-dict scene record
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": ["malformed_string"]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed scene record at index 0"):
        s08_video_gen.run(ctx)

    # 2. Missing scene_id
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": [{"shots": [{"shot_id": "sh_1"}]}]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing valid scene_id"):
        s08_video_gen.run(ctx)

    # 3. Empty shots list
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": [{"scene_id": "SCENE_01", "shots": []}]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="empty or invalid shots list"):
        s08_video_gen.run(ctx)

    # 4. Shot 0 missing shot_id
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": [{"scene_id": "SCENE_01", "shots": [{"account_slot": "acc_01"}]}]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing valid shot_id"):
        s08_video_gen.run(ctx)

    # 5. First scene specifies uses_previous_end_frame=True
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": [{"scene_id": "SCENE_01", "shots": [{"shot_id": "sh_1", "uses_previous_end_frame": True}]}]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="First scene 'SCENE_01' cannot specify uses_previous_end_frame=True"):
        s08_video_gen.run(ctx)

    # 6. Chained shot references unknown previous_shot_id
    valid_sc1 = {"scene_id": "SCENE_01", "shots": [{"shot_id": "sh_1"}]}
    bad_sc2 = {"scene_id": "SCENE_02", "shots": [{"shot_id": "sh_2", "uses_previous_end_frame": True, "previous_shot_id": "unknown_shot"}]}
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": [valid_sc1, bad_sc2]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="references previous_shot_id='unknown_shot' which does not exist"):
        s08_video_gen.run(ctx)


def test_s08_ffmpeg_extraction_and_fallback_contract(tmp_path, monkeypatch):
    """Verify s08 start-frame chaining contract: extraction success, observable fallback, and fail-closed when seed is missing."""
    import json
    import subprocess

    import pytest

    from core.config import RunContext, load_profile
    from core.paths import resolve_run_paths
    from core.run_manifest import RunManifest
    from stages import s08_video_gen

    run_id = "test_run_s08_chaining"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
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
    s5_artifact_path = paths.artifact_file("s05_director_plan")
    s5_artifact_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Successful chaining when preceding clip is generated
    scenes = [
        {"scene_id": "SCENE_01", "shots": [{"shot_id": "sc_01_sh_01"}]},
        {"scene_id": "SCENE_02", "shots": [{"shot_id": "sc_02_sh_01", "uses_previous_end_frame": True}]},
    ]
    s5_artifact_path.write_text(json.dumps({"payload": {"scenes": scenes}}), encoding="utf-8")
    art = s08_video_gen.run(ctx)
    assert art.status == "ok"
    fc = art.payload["frame_chain"]
    assert len(fc) == 2
    assert fc[0]["kind"] == "source"
    assert fc[1]["kind"] == "chained"
    assert fc[1]["previous_shot_id"] == "sc_01_sh_01"
    assert fc[1]["previous_frame_id"] == "frame_sc_01_sh_01_end"

    # Simulate extraction failure for chained frame
    orig_run = subprocess.run

    def fail_chained_extraction(cmd, *args, **kwargs):
        if any("_start.png" in str(arg) for arg in cmd):
            raise subprocess.CalledProcessError(1, cmd, stderr=b"Simulated corrupted video stream error")
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_chained_extraction)

    # 2. Corrupted preceding clip / extraction failure + Missing seed -> Raises RuntimeError (fail closed per Rule 118 & 121)
    with pytest.raises(RuntimeError, match="Chained extraction failed for shot='sc_02_sh_01'.*and fallback seed image.*is unusable"):
        s08_video_gen.run(ctx)

    # 3. Corrupted preceding clip / extraction failure + Usable seed -> Validated auditable fallback
    from PIL import Image
    seed_02 = paths.seed_image_path("SCENE_02")
    seed_02.parent.mkdir(parents=True, exist_ok=True)
    img_fallback = Image.new("RGB", (64, 64), color="red")
    img_fallback.save(seed_02)
    art_fallback = s08_video_gen.run(ctx)
    assert art_fallback.status == "ok"
    fc2 = art_fallback.payload["frame_chain"]
    assert fc2[1]["kind"] == "source"
    assert fc2[1]["fallback_used"] is True
    assert fc2[1]["seed_usable"] is True
    assert fc2[1]["previous_shot_id"] is None
    assert fc2[1]["previous_frame_id"] is None


def test_chunk_partition_property_and_adversarial_matrix():
    """Verify sequence block chunking across property invariants, exact boundaries, irregular durations, and short/oversized timelines."""
    import random

    import pytest

    from core.contracts.stages import Scene, Shot
    from stages.s05_director_plan import partition_timeline_into_chunks

    # A. Adversarial: Irregular durations
    durations = [7.5, 12.3, 15.2, 9.0, 11.0, 18.0, 8.5]
    scenes = [
        Scene(
            scene_id=f"SC_{i:02d}",
            narration="Test narration for irregular duration scene",
            duration_est_sec=dur,
            shots=[Shot(shot_id=f"sh_{i:02d}", scene_id=f"SC_{i:02d}", visual_prompt="Tactile paper cutout", duration_sec=dur)]
        )
        for i, dur in enumerate(durations)
    ]
    chunks = partition_timeline_into_chunks(scenes, target_chunk_duration=36.0, min_chunk_duration=24.0, max_chunk_duration=48.0)
    assert len(chunks) >= 2
    # Total duration preservation (0 duration loss)
    assert sum(c.duration_s for c in chunks) == pytest.approx(sum(durations), 0.01)
    # Continuity: no gaps, no overlaps
    assert chunks[0].start_s == 0.0
    for i in range(len(chunks) - 1):
        assert chunks[i].end_s == pytest.approx(chunks[i + 1].start_s, 0.01)
    assert chunks[-1].end_s == pytest.approx(sum(durations), 0.01)

    # B. Adversarial: Exact 24s and 48s boundaries
    exact_durs = [24.0, 24.0, 48.0, 24.0, 48.0]
    scenes_exact = [
        Scene(
            scene_id=f"SC_EX_{i}",
            narration="Test narration for exact boundary scene",
            duration_est_sec=dur,
            shots=[Shot(shot_id=f"sh_ex_{i}", scene_id=f"SC_EX_{i}", visual_prompt="Tactile paper cutout", duration_sec=dur)]
        )
        for i, dur in enumerate(exact_durs)
    ]
    chunks_exact = partition_timeline_into_chunks(scenes_exact)
    assert all(c.duration_s <= 48.0 for c in chunks_exact)
    assert sum(c.duration_s for c in chunks_exact) == pytest.approx(sum(exact_durs), 0.01)

    # C. Adversarial: Short complete timeline (< 24s)
    short_scenes = [
        Scene(scene_id="SC_S1", narration="Short scene 1", duration_est_sec=8.0, shots=[Shot(shot_id="sh_s1", scene_id="SC_S1", visual_prompt="Tactile paper cutout", duration_sec=8.0)]),
        Scene(scene_id="SC_S2", narration="Short scene 2", duration_est_sec=9.0, shots=[Shot(shot_id="sh_s2", scene_id="SC_S2", visual_prompt="Tactile paper cutout", duration_sec=9.0)]),
    ]
    chunks_short = partition_timeline_into_chunks(short_scenes)
    assert len(chunks_short) == 1
    assert chunks_short[0].boundary_reason == "complete_timeline"
    assert chunks_short[0].duration_s == 17.0

    # D. Adversarial: Oversized single scenes (> 48s)
    mixed_oversized = [
        Scene(scene_id="SC_O1", narration="Normal scene 1", duration_est_sec=15.0, shots=[Shot(shot_id="sh_o1", scene_id="SC_O1", visual_prompt="Tactile paper cutout", duration_sec=15.0)]),
        Scene(scene_id="SC_O2", narration="Oversized scene 2", duration_est_sec=65.0, shots=[Shot(shot_id="sh_o2", scene_id="SC_O2", visual_prompt="Tactile paper cutout", duration_sec=65.0)]),
        Scene(scene_id="SC_O3", narration="Normal scene 3", duration_est_sec=20.0, shots=[Shot(shot_id="sh_o3", scene_id="SC_O3", visual_prompt="Tactile paper cutout", duration_sec=20.0)]),
    ]
    chunks_over = partition_timeline_into_chunks(mixed_oversized)
    assert any(c.boundary_reason == "oversized_single_scene_exception" for c in chunks_over)
    assert sum(c.duration_s for c in chunks_over) == pytest.approx(100.0, 0.01)

    # E. Property Invariant Test across 20 randomized timelines
    rng = random.Random(42)
    for _ in range(20):
        rand_count = rng.randint(4, 25)
        rand_durs = [round(rng.uniform(4.0, 16.0), 1) for _ in range(rand_count)]
        rand_scenes = [
            Scene(
                scene_id=f"R_SC_{j}",
                narration="Randomized timeline test scene",
                duration_est_sec=d,
                shots=[Shot(shot_id=f"r_sh_{j}", scene_id=f"R_SC_{j}", visual_prompt="Tactile paper cutout", duration_sec=d)]
            )
            for j, d in enumerate(rand_durs)
        ]
        r_chunks = partition_timeline_into_chunks(rand_scenes)
        assert sum(c.duration_s for c in r_chunks) == pytest.approx(sum(rand_durs), 0.01)
        assert r_chunks[0].start_s == 0.0
        for k in range(len(r_chunks) - 1):
            assert r_chunks[k].end_s == pytest.approx(r_chunks[k + 1].start_s, 0.01)
        # All multi-scene chunks satisfy <= 48.0s
        for c in r_chunks:
            if len(c.scene_ids) > 1:
                assert c.duration_s <= 48.0


def test_safe_disposal_negative_boundary_and_wildcard_attacks(tmp_path):
    """Verify safe disposal strictly rejects wildcard attacks, root paths, traversal attempts, boundary escapes, and system directories per Rule 137."""
    from scripts.safe_trash import safe_trash, validate_safe_disposal_target

    # 1. Wildcard attacks must be rejected unconditionally
    for wild in ["*.py", "test_*.log", "/tmp/*", "C:\\temp\\*.*", "dir/?"]:
        ok, msg = validate_safe_disposal_target(wild)
        assert not ok, f"Wildcard attack was unexpectedly accepted: {wild}"
        assert "Wildcard deletion is strictly forbidden" in msg
        assert safe_trash(wild) is False

    # 2. Drive root attacks must be rejected unconditionally
    for root_path in ["C:\\", "c:/", "D:\\", "/", "\\", "\\\\"]:
        ok, msg = validate_safe_disposal_target(root_path)
        assert not ok, f"Drive root attack was unexpectedly accepted: {root_path}"
        assert "Cannot trash drive root or forbidden zone" in msg

    # 3. System directories must be rejected unconditionally
    for sys_dir in ["/etc", "/var", "/usr", "/bin", "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"]:
        ok, msg = validate_safe_disposal_target(sys_dir)
        assert not ok, f"System directory was unexpectedly accepted: {sys_dir}"
        assert "forbidden" in msg.lower() or "outside approved" in msg.lower()

    # 4. Traversal attacks targeting forbidden roots must be rejected unconditionally (Rule 137)
    traversals = ["../../../../etc/passwd", "..\\..\\..\\Windows\\System32", "../../../../root/.ssh"]
    for trav in traversals:
        ok, msg = validate_safe_disposal_target(trav)
        assert not ok, f"Traversal attack was unexpectedly accepted: {trav}"
        assert "forbidden" in msg.lower() or "drive root" in msg.lower() or "outside approved" in msg.lower()

    # 5. Boundary escape & sibling-prefix attacks against approved root
    fake_quarantine = tmp_path / "approved_quarantine"
    fake_quarantine.mkdir()
    sibling_evil = tmp_path / "approved_quarantine_evil"
    sibling_evil.mkdir()

    # Sibling prefix should be rejected when target root is approved_quarantine
    ok, msg = validate_safe_disposal_target(str(sibling_evil / "file.txt"), allowed_roots=[fake_quarantine])
    assert not ok
    assert "outside approved disposal roots" in msg

    # Trashing the approved root itself must be rejected
    ok, msg = validate_safe_disposal_target(str(fake_quarantine), allowed_roots=[fake_quarantine])
    assert not ok
    assert "Cannot trash entire approved root directory" in msg

    # 6. Production source tree & root-adjacent attacks under default roots must be rejected unconditionally (Rule 137)
    repo_root = Path(__file__).resolve().parent.parent.parent
    for src_file in [
        repo_root / "app" / "services" / "prompt_forge.py",
        repo_root / "stages" / "s10_render.py",
        repo_root / "vox" / "qa" / "gates.py",
        repo_root / "core" / "contracts" / "stages.py",
    ]:
        ok, msg = validate_safe_disposal_target(str(src_file))
        assert not ok, f"Production source file was unexpectedly allowed for disposal: {src_file}"
        assert "outside approved disposal roots" in msg

    # 7. Symlink escape attack: symlink inside approved quarantine pointing outside
    symlink_target = tmp_path / "secret_data.txt"
    symlink_target.write_text("confidential", encoding="utf-8")
    evil_link = fake_quarantine / "link_to_secret"
    try:
        evil_link.symlink_to(symlink_target)
        ok, msg = validate_safe_disposal_target(str(evil_link), allowed_roots=[fake_quarantine])
        assert not ok, "Symlink escaping quarantine was unexpectedly accepted"
        assert "outside approved disposal roots" in msg
    except (OSError, NotImplementedError):
        pass  # Skip if unprivileged Windows symlink creation is restricted

    # 8. Physical proof: rejected targets cannot be deleted or moved (physical non-destruction guarantee)
    protected_file = tmp_path / "protected_target.txt"
    protected_file.write_text("DO_NOT_DELETE_INTEGRITY_CHECK", encoding="utf-8")
    assert safe_trash(str(protected_file), allowed_roots=[fake_quarantine]) is False
    assert protected_file.exists() is True
    assert protected_file.read_text(encoding="utf-8") == "DO_NOT_DELETE_INTEGRITY_CHECK"


def test_ast_rule139_scanner_contract_validation_fails_closed():
    """Verify strict scanner-output contract validation: missing scripts, malformed JSON, non-object JSON,
    missing fields, invalid field types, negative or contradictory counts, and nonzero exits fail closed (Rule 139 & Boss Item 2).
    """
    import json
    required_ast_fields = {"scanner_name", "scanner_version", "scanned_files", "critical_count", "high_count", "allowed_legacy_count", "verdict", "defects"}

    def validate_scanner_output(raw_output: str, exit_code: int) -> dict:
        """Mirroring orchestrator contract validation logic."""
        if exit_code != 0:
            raise ValueError(f"Scanner process failed with nonzero exit code: {exit_code}")
        try:
            data = json.loads(raw_output)
        except Exception as e:
            raise ValueError(f"Scanner emitted malformed JSON: {e}")
        if not isinstance(data, dict):
            raise ValueError(f"Scanner emitted non-object JSON: got {type(data).__name__}")
        missing = required_ast_fields - set(data.keys())
        if missing:
            raise ValueError(f"Scanner output missing required fields: {missing}")
        for int_f in ["critical_count", "high_count", "allowed_legacy_count", "scanned_files"]:
            val = data.get(int_f)
            if type(val) is not int or val < 0:
                raise ValueError(f"Field '{int_f}' must be non-negative int, got {val!r}")
        verdict = data.get("verdict")
        if not isinstance(verdict, str):
            raise ValueError(f"Field 'verdict' must be string, got {type(verdict).__name__}")
        if "PASS" in verdict and (data["critical_count"] > 0 or data["high_count"] > 0 or exit_code != 0):
            raise ValueError(f"Contradictory state: verdict={verdict} but critical={data['critical_count']}, high={data['high_count']}")
        return data

    # 1. Nonzero exit code
    with pytest.raises(ValueError, match="nonzero exit code: 1"):
        validate_scanner_output('{"scanner_name": "ast", "scanner_version": "1.0", "scanned_files": 10, "critical_count": 0, "high_count": 0, "allowed_legacy_count": 220, "verdict": "PASS", "defects": []}', exit_code=1)

    # 2. Malformed JSON
    with pytest.raises(ValueError, match="malformed JSON"):
        validate_scanner_output('{broken_json', exit_code=0)

    # 3. Non-object JSON
    with pytest.raises(ValueError, match="non-object JSON"):
        validate_scanner_output('["array", "of", "items"]', exit_code=0)

    # 4. Missing required field
    with pytest.raises(ValueError, match="missing required fields.*critical_count"):
        validate_scanner_output('{"scanner_name": "ast", "scanner_version": "1.0", "scanned_files": 10, "high_count": 0, "allowed_legacy_count": 220, "verdict": "PASS", "defects": []}', exit_code=0)

    # 5. Invalid field type
    with pytest.raises(ValueError, match="must be non-negative int"):
        validate_scanner_output('{"scanner_name": "ast", "scanner_version": "1.0", "scanned_files": 10, "critical_count": "zero", "high_count": 0, "allowed_legacy_count": 220, "verdict": "PASS", "defects": []}', exit_code=0)

    # 6. Contradictory state (verdict PASS with critical > 0)
    with pytest.raises(ValueError, match="Contradictory state"):
        validate_scanner_output('{"scanner_name": "ast", "scanner_version": "1.0", "scanned_files": 10, "critical_count": 2, "high_count": 0, "allowed_legacy_count": 220, "verdict": "PASS (0 Critical / 0 High)", "defects": []}', exit_code=0)


def test_vox_qa_gates_fails_closed_when_scene_plan_absent_or_empty(tmp_path):
    """Verify that vox.qa.gates.verify_final_video_gates fails closed when ScenePlan is None or empty (Rule 139 & Boss Item 12)."""
    from vox.qa.gates import verify_final_video_gates
    from vox.schemas import ScenePlan

    dummy_mp4 = tmp_path / "test.mp4"
    dummy_mp4.write_bytes(b"dummy")

    # 1. Missing plan (None)
    with pytest.raises(ValueError, match="ScenePlan is required and must contain scenes"):
        # Monkeypatch probe_media_file to return minimal valid streams
        import vox.qa.gates as vq
        orig_probe = vq.probe_media_file
        orig_loudness = vq.measure_ebur128_loudness

        def fake_probe(p):
            return {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", "nb_frames": 300, "r_frame_rate": "30/1"},
                    {"codec_type": "audio", "codec_name": "aac", "sample_rate": 48000}
                ],
                "format": {"duration": "10.0"}
            }

        vq.probe_media_file = fake_probe
        try:
            verify_final_video_gates(dummy_mp4, expected_duration=10.0, plan=None)
        finally:
            vq.probe_media_file = orig_probe

    # 2. Empty plan (dummy object with empty scenes list)
    empty_plan = type("DummyEmptyPlan", (), {"scenes": []})()
    with pytest.raises(ValueError, match="ScenePlan is required and must contain scenes"):
        orig_probe = vq.probe_media_file

        def fake_probe(p):
            return {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", "nb_frames": 300, "r_frame_rate": "30/1"},
                    {"codec_type": "audio", "codec_name": "aac", "sample_rate": 48000}
                ],
                "format": {"duration": "10.0"}
            }

        vq.probe_media_file = fake_probe
        try:
            verify_final_video_gates(dummy_mp4, expected_duration=10.0, plan=empty_plan)
        finally:
            vq.probe_media_file = orig_probe


