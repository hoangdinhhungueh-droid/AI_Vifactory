#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for unified_vox_director & scene_schema compliance (Rule 121 & Rule 128)."""

import json
import pytest
from pathlib import Path
from app.services.unified_vox_director import (
    load_style_config,
    format_final_veo_prompt,
    get_action_description,
    build_unified_director_plan,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

def test_load_style_config():
    """Verify style-config.yaml loading for both presets."""
    vox_cfg = load_style_config("vox_forensic_paper")
    assert vox_cfg["name"] == "vox_forensic_paper"
    assert "tangible forensic" in vox_cfg["positive"]
    assert "12fps" in vox_cfg["motion_behavior"]
    assert "no photorealism" in vox_cfg["negative"]
    assert "static" in vox_cfg["camera_defaults"]["allowed"]

    voxel_cfg = load_style_config("voxel_stopmotion")
    assert voxel_cfg["name"] == "voxel_stopmotion"
    assert "voxel art style" in voxel_cfg["positive"]
    assert "no motion blur" in voxel_cfg["negative"]

def test_format_final_veo_prompt():
    """Verify final_veo_prompt string formatting matches the template."""
    cfg = load_style_config("voxel_stopmotion")
    prompt = format_final_veo_prompt(
        preset=cfg,
        subject="a small voxel fox character with orange cube fur",
        action="sitting still then slowly turning its head toward camera",
        setting="a miniature pixel forest diorama clearing at dawn",
        camera="static",
        lighting="warm diorama studio light, soft shadows, subtle rim light"
    )
    assert "voxel art style" in prompt
    assert "Scene: a small voxel fox character with orange cube fur sitting still then slowly turning its head toward camera in a miniature pixel forest diorama clearing at dawn." in prompt
    assert "Camera: static. Lighting: warm diorama studio light, soft shadows, subtle rim light." in prompt
    assert "no motion blur" in prompt

def test_scene_schema_compliance(tmp_path):
    """Verify that build_unified_director_plan produces scenes compliant with scene_schema.json."""
    schema_path = ROOT_DIR / "config" / "schemas" / "scene_schema.json"
    assert schema_path.exists(), "scene_schema.json must exist"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    required_fields = schema.get("required", [])
    allowed_cameras = schema.get("properties", {}).get("camera", {}).get("enum", [])
    allowed_transitions = schema.get("properties", {}).get("transition_out", {}).get("enum", [])

    sample_sentences = [
        {"text": "The Federal Trade Commission filed an antitrust lawsuit against Amazon.", "duration_frames": 150, "duration_sec": 5.0, "beat_index": 1},
        {"text": "Twenty billion dollars in damages was calculated across millions of merchants.", "duration_frames": 180, "duration_sec": 6.0, "beat_index": 1},
        {"text": "An internal project Nessie memo revealed algorithmic price gouging.", "duration_frames": 210, "duration_sec": 7.0, "beat_index": 2},
    ]

    result = build_unified_director_plan(sample_sentences, tmp_path, style_preset="vox_forensic_paper")
    scenes = result["scenes"]
    hero_clips = result["hero_clips"]

    assert len(scenes) == 3
    for s in scenes:
        for rf in required_fields:
            assert rf in s, f"Scene {s.get('scene_id')} missing required field: {rf}"
            assert s[rf] is not None, f"Field {rf} cannot be None"
        assert s["camera"] in allowed_cameras, f"Invalid camera: {s['camera']}"
        assert s["transition_out"] in allowed_transitions, f"Invalid transition: {s['transition_out']}"
        assert s["duration_seconds"] >= 4 and s["duration_seconds"] <= 8

    # Check hero clips
    for c in hero_clips:
        assert "final_veo_prompt" in c
        assert "prompt" in c
        assert c["transition_out"] in allowed_transitions

def test_select_dynamic_hero_indices():
    """Verify dynamic cadence selection without hardcoded dead numbers (Rule 128)."""
    from app.services.unified_vox_director import select_dynamic_hero_indices, determine_spatial_physics
    
    # 1. 100 sentences test episode
    sents = [
        {"text": f"Sentence {i} describing financial evidence and system anomalies.", "beat_index": (i // 20) + 1}
        for i in range(100)
    ]
    # Inject catalyst words
    sents[15]["text"] = "The FTC Seattle court docket was filed."
    sents[45]["text"] = "A twenty billion dollars fine was issued."
    sents[85]["text"] = "Andy Jassy signed the internal project Nessie memo."
    sents[99]["text"] = "The judge delivered the final gavel verdict."

    hero_indices = select_dynamic_hero_indices(sents)
    assert 0 in hero_indices, "Scene 0 must always be a hero clip (Hook/Paradox)"
    assert len(hero_indices) >= 12 and len(hero_indices) <= 22, f"Cadence should yield ~14-20 clips for 100 scenes, got {len(hero_indices)}"
    
    # Check minimum distance
    for i in range(len(hero_indices) - 1):
        gap = hero_indices[i+1] - hero_indices[i]
        assert gap >= 3, f"Gap between hero clips must be >= 3, found {gap} between {hero_indices[i]} and {hero_indices[i+1]}"

    # 2. Physics classification
    phys, act, mode, fol = determine_spatial_physics("The judge struck the gavel with authority", "fg_evidence_gavel", 0)
    assert phys == "MACRO_HIGHLIGHT_WIPE"
    assert mode == "CUTOUT_ONLY"
    assert fol == "gavel_thud"

    phys, act, mode, fol = determine_spatial_physics("Confidential memo revealing secret pricing", "fg_evidence_memo", 1)
    assert phys == "CORNER_DOGEAR_PEEL"
    assert mode == "COMPOSITE_16_9"
    assert fol == "paper_page_turn"


def test_dynamic_visual_roster_multi_market():
    """Verify dynamic visual roster extraction across JP, KR, VN, EN (Rule 128 - Zero Semantic Bias)."""
    from app.services.unified_vox_director import extract_dynamic_visual_roster

    # 1. JP Market
    jp_bg, jp_fg = extract_dynamic_visual_roster(market="JP", topic="Bamboo shoot food safety")
    assert any("tokyo" in v["title"].lower() or "courthouse" in v["title"].lower() for v in jp_bg.values())
    assert any("hanko" in k or "inspection" in k for k in jp_fg.keys())
    assert not any("amazon" in v["title"].lower() for v in jp_fg.values())
    assert not any("lina khan" in v["description"].lower() for v in jp_fg.values())

    # 2. KR Market
    kr_bg, kr_fg = extract_dynamic_visual_roster(market="KR", topic="Corporate accounting anomaly")
    assert any("seoul" in v["title"].lower() or "courthouse" in v["title"].lower() for v in kr_bg.values())
    assert any("ingam" in k or "sawonjeung" in k for k in kr_fg.keys())

    # 3. VN Market
    vn_bg, vn_fg = extract_dynamic_visual_roster(market="VN", topic="Thanh tra bất động sản")
    assert any("mộc đỏ" in v["title"].lower() or "thanh tra" in v["title"].lower() for v in vn_fg.values())

    # 4. EN Market
    en_bg, en_fg = extract_dynamic_visual_roster(market="EN", topic="Securities antitrust filing")
    assert any("docket" in k or "invoice" in k for k in en_fg.keys())


def test_build_unified_director_plan_generates_manifest(tmp_path):
    """Verify build_unified_director_plan outputs flow_video_manifest.json and accounts distribution."""
    from app.services.unified_vox_director import build_unified_director_plan, FLOW_ACCOUNTS

    sample_sentences = [
        {"text": f"Investigative scene {i} discussing food quarantine protocols and chemical residue levels.", "beat_index": (i // 5) + 1, "duration_sec": 5.0, "duration_frames": 150}
        for i in range(25)
    ]
    res = build_unified_director_plan(
        spoken_sentences=sample_sentences,
        ep_dir=tmp_path,
        market="JP",
        metadata={"episode_id": "JP_EP0004_test"}
    )
    manifest_path = tmp_path / "flow_video_manifest.json"
    assert manifest_path.exists(), "flow_video_manifest.json must be generated"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["episode_id"] == "JP_EP0004_test"
    assert manifest_data["total_clips"] == len(res["hero_clips"])
    assert len(manifest_data["clips"]) > 0

    # Ensure hero clips are assigned across FLOW_ACCOUNTS
    assigned_slots = {c["flow_slot"] for c in manifest_data["clips"]}
    assert len(assigned_slots) > 1
    for s in assigned_slots:
        assert s in FLOW_ACCOUNTS


def test_canonical_sfx_registry_integrity():
    """Verify Canonical SFX Registry physical integrity, closed vocabulary, and multi-market resolution."""
    from app.services.sfx_registry import (
        CANONICAL_SFX_REGISTRY,
        get_canonical_sfx_list,
        is_valid_sfx,
        resolve_semantic_foley,
        verify_physical_sfx_assets,
    )

    # 1. Closed set of 13 Canonical SFX
    canonical_list = get_canonical_sfx_list()
    assert len(canonical_list) == 13
    assert "gauge_needle_hiss" in canonical_list
    assert "gavel_thud" in canonical_list
    assert "sonar_ping" in canonical_list

    # 2. Validation function
    assert is_valid_sfx("gauge_needle_hiss")
    assert is_valid_sfx("sfx/gauge_needle_hiss.mp3")
    assert not is_valid_sfx("laser_zap")
    assert not is_valid_sfx("steam_burst")
    assert not is_valid_sfx(None)

    # 3. Physical assets check
    ok, missing = verify_physical_sfx_assets()
    assert ok, f"Missing or corrupted physical SFX files: {missing}"

    # 4. Multi-market semantic resolution
    # Japanese chemical residue
    cue_jp = resolve_semantic_foley("中国産タケノコから二酸化硫黄の残余検査", "fg_evidence_chemical")
    assert cue_jp == "gauge_needle_hiss"

    # Korean court ruling
    cue_kr = resolve_semantic_foley("서울중앙지방법원 판사의 최종 유죄 판결", "fg_court_gavel")
    assert cue_kr == "gavel_thud"

    # Vietnamese official seal
    cue_vn = resolve_semantic_foley("Đóng dấu mộc đỏ quyết định xử phạt hành chính", "fg_official_seal")
    assert cue_vn in ["stamp_slam", "stamp_impact"]

    # English recon sonar
    cue_en = resolve_semantic_foley("Satellite radar recon tracked illicit maritime vessels", "fg_radar_screen")
    assert cue_en == "sonar_ping"


def test_vox_roster_depth_and_coverage(tmp_path):
    """Rule 122 & Rule 128: Verify expanded roster depth (>=16 BGs, >=20 FGs) and healthy VOX FG coverage."""
    from app.services.unified_vox_director import extract_dynamic_visual_roster, build_unified_director_plan

    # 1. Roster depth for financial topic
    bg_roster, fg_roster = extract_dynamic_visual_roster(
        market="EN",
        topic="365 Nghìn Tỷ USD Nợ Toàn Cầu: Cái Bẫy Đáo Hạn Khiến Thế Giới Vay Để Trả Nợ"
    )
    assert len(bg_roster) >= 16, f"Expected >= 16 BGs for VOX docudrama, got {len(bg_roster)}"
    assert len(fg_roster) >= 20, f"Expected >= 20 FGs for VOX docudrama, got {len(fg_roster)}"

    # Check distribution: characters vs props
    chars = [k for k, v in fg_roster.items() if v.get("type") == "character" or "character" in k]
    props = [k for k, v in fg_roster.items() if k not in chars]
    assert 3 <= len(chars) <= 8, f"Expected 3-8 character archetypes, got {len(chars)}"
    assert len(props) >= 15, f"Expected >= 15 tactile evidence props, got {len(props)}"

    # 2. Test long-form scene coverage (60 scenes)
    sample_scenes = [
        {"text": f"Scene {i} analyzing sovereign debt rollover risks and bond yield curve spikes.", "beat_index": (i // 12) + 1, "duration_sec": 5.0}
        for i in range(60)
    ]
    plan = build_unified_director_plan(
        spoken_sentences=sample_scenes,
        ep_dir=tmp_path,
        market="EN",
        metadata={"episode_id": "EN_EP0005_test_roster", "topic": "365T Debt"}
    )
    scenes = plan["scenes"]
    assert len(scenes) == 60

    scenes_with_fg = [s for s in scenes if (s.get("foreground") and s["foreground"].get("reuse_key"))]
    fg_ratio = len(scenes_with_fg) / len(scenes)
    # Healthy VOX coverage: between 55% and 75%
    assert 0.55 <= fg_ratio <= 0.75, f"Expected VOX FG ratio between 55% and 75%, got {fg_ratio:.1%}"

    # Verify character appearance cap <= 12
    char_appearances = [
        s for s in scenes_with_fg
        if s["foreground"]["reuse_key"] in chars
    ]
    assert len(char_appearances) <= 12, f"Human character appearances ({len(char_appearances)}) must be <= 12"




