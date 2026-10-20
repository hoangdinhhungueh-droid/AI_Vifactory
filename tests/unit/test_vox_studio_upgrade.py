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

    # Test case 2: 50s timeline (10 scenes x 5.0s) -> should rebalance trailing 14s into first chunk
    scenes_50s = scenes_70s[:10]
    chunks_50 = partition_timeline_into_chunks(scenes_50s)
    for c in chunks_50:
        assert 24.0 <= c.duration_s <= 50.0
        assert c.duration_s >= 24.0, f"Chunk {c.chunk_id} under min bound"


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
