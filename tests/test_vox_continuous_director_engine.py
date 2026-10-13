#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_vox_continuous_director_engine.py — Unit Tests for Vox Continuous Director Engine."""

import json
import pytest
from pathlib import Path
from app.services.vox_continuous_director_engine import (
    generate_continuous_director_plan,
    generate_7acc_flow_manifest,
    FLOW_ACCOUNTS,
    CANVAS_WORKSPACES,
    VOX_PALETTE
)


@pytest.fixture
def mock_episode_dir(tmp_path):
    """Creates a temporary mock episode folder with b2_script.json."""
    ep_dir = tmp_path / "KR_EP0001_mock_test"
    ep_dir.mkdir(parents=True, exist_ok=True)

    mock_script = {
        "title": "Mock Corporate Tax Episode",
        "market": "KR",
        "topic_slug": "mock_tax",
        "full_spoken_script": (
            "=== ACT I ===\n"
            "2026년 10월 8일, 대법원은 구글코리아의 약 1540억 원 법인세 부과 취소 소송에서 최종 패소 판결을 확정했습니다.\n"
            "세무조사권과 자료 제출 권한을 모두 가진 국가가, 1심과 2심 그리고 대법원까지 세 번 연속으로 무너졌습니다.\n"
            "2016년부터 2018년까지 구글코리아가 한국에서 벌어들인 광고매출은 1조5112억 원이었습니다.\n"
            "그중 9751억 원, 약 65%가 싱가포르의 구글 아시아퍼시픽으로 국경을 넘어 흘러갔습니다.\n"
            "당신이 매일 검색하고 광고를 누르는 스마트폰 화면은 서울에 있습니다.\n"
            "하지만 그 돈을 합법적으로 넘겨받은 법인의 서버는 서울 어디에도 존재하지 않습니다.\n"
            "=== ACT II ===\n"
            "국세청은 이 돈의 실질을 저작권과 노하우에 대한 사용료라고 주장했습니다.\n"
            "반면 구글은 조세조약상 한국에 고정사업장이 없는 한 과세할 수 없다고 맞섰습니다.\n"
            "같은 9751억 원이라는 거대한 돈의 흐름 위에, 서로 다른 법적 이름표가 붙었습니다.\n"
            "=== ACT III ===\n"
            "당신 앞에는 완전히 다른 두 개의 서랍이 놓여 있습니다.\n"
            "첫 번째 서랍의 이름은 사용료이며, 한국 국세청이 원천징수할 수 있는 서랍입니다.\n"
            "두 번째 서랍의 이름은 사업소득이며, 고정사업장 없이는 한 푼도 손댈 수 없는 서랍입니다.\n"
            "=== ACT IV ===\n"
            "1심 법원은 국세청이 내민 사용료 이름표를 공식적으로 기각했습니다.\n"
            "결국 남은 것은 사업소득 서랍뿐이었고, 대법원은 쟁점조차 없다며 문을 닫아버렸습니다.\n"
        )
    }

    script_path = ep_dir / "b2_script.json"
    script_path.write_text(json.dumps(mock_script, ensure_ascii=False, indent=2), encoding="utf-8")
    return ep_dir


def test_flow_accounts_has_7_accounts():
    """Verify that FLOW_ACCOUNTS contains exactly 7 accounts (acc_01 to acc_07)."""
    assert len(FLOW_ACCOUNTS) == 7
    expected = [f"acc_{i:02d}" for i in range(1, 8)]
    assert FLOW_ACCOUNTS == expected


def test_continuous_director_plan_generation(mock_episode_dir):
    """Verify continuous director plan produces 6-layer object-assembly schema."""
    plan = generate_continuous_director_plan(mock_episode_dir)

    assert plan["episode_id"] == "KR_EP0001_mock_test"
    assert plan["format"] == "VOX_CONTINUOUS_OBJECT_ASSEMBLY_COLLAGE"
    assert plan["total_scenes"] >= 14
    assert plan["total_sequence_blocks"] >= 3

    # Inspect each scene for strict object-assembly kinematics
    for scene in plan["scenes"]:
        assert "scene_id" in scene
        assert "sequence_block" in scene
        assert "timeframe" in scene
        assert "canvas_workspace" in scene
        assert scene["canvas_workspace"] in CANVAS_WORKSPACES
        assert "hero_cutout_object" in scene
        assert len(scene["hero_cutout_object"]) > 10
        assert "interacting_objects" in scene
        assert isinstance(scene["interacting_objects"], list)
        assert len(scene["interacting_objects"]) >= 1

        # Motion track kinematics
        mt = scene["motion_track_and_assembly"]
        assert "entry_action" in mt
        assert "assembly_step" in mt
        assert "spatial_anchor" in mt
        assert mt["camera_rule"] == "Completely static camera, no 3D pan/zoom"

        # Typography & Bridging link
        assert "graphic_typography" in scene
        assert "headline" in scene["graphic_typography"]
        assert "english_tag" in scene["graphic_typography"]
        assert "visual_continuity_link_to_next" in scene
        assert len(scene["visual_continuity_link_to_next"]) > 15

        # 5-Layer Image Prompt
        prompt = scene["image_prompt"]
        assert "Layer 1:" in prompt
        assert "Layer 2:" in prompt
        assert "Layer 3:" in prompt
        assert "Layer 4:" in prompt
        assert "Layer 5:" in prompt
        assert "Negative prompt:" in prompt


def test_7_account_flow_manifest_round_robin(mock_episode_dir):
    """Verify flow_video_manifest.json evenly rotates all 7 accounts."""
    generate_continuous_director_plan(mock_episode_dir)

    man_path = mock_episode_dir / "flow_video_manifest.json"
    assert man_path.exists()

    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    assert manifest["format"] == "FLOW_VEO_7_ACCOUNT_DISPATCH"
    assert manifest["accounts_used"] == FLOW_ACCOUNTS
    assert manifest["total_clips"] >= 14

    # Verify that all 7 accounts are utilized
    assigned_slots = {clip["flow_slot"] for clip in manifest["clips"]}
    assert assigned_slots == set(FLOW_ACCOUNTS), "Every single one of the 7 accounts must be assigned clips!"
