import os
import json
import pytest
from app.services.director_planner_b3 import (
    CANONICAL_CAMERA_MOVES,
    detect_forensic_overlay,
    detect_stat_card,
    detect_stamp_badge,
    _synthesize_deterministic_director_plan,
    detect_cinematic_archetype
)
from app.services.build_remotion_props import (
    detect_forensic_overlay as remotion_detect_overlay,
    build_remotion_props_data
)


def test_canonical_camera_moves_completeness():
    assert len(CANONICAL_CAMERA_MOVES) == 6
    expected = {"slow_push_in", "snap_zoom", "cinematic_pan", "macro_tilt", "slow_pull_out", "handheld_shake"}
    assert set(CANONICAL_CAMERA_MOVES) == expected


def test_detect_forensic_overlay_categories():
    # Contract / Redacted Doc
    r1 = detect_forensic_overlay("The company signed a classified NDA clause preventing disclosure.")
    assert r1 is not None
    assert r1["type"] == "redacted_doc"

    # Flight / Radar
    r2 = detect_forensic_overlay("The cargo flight vanished from air traffic control radar screens.")
    assert r2 is not None
    assert r2["type"] == "radar_map"

    # Financial / Capital Loss
    r3 = detect_forensic_overlay("A catastrophic 40 billion dollar stock market liquidity collapse.")
    assert r3 is not None
    assert r3["type"] == "financial_chart"

    # Surveillance
    r4 = detect_forensic_overlay("Security warehouse CCTV surveillance footage was quietly erased.")
    assert r4 is not None
    assert r4["type"] == "surveillance_crt"

    # None
    r5 = detect_forensic_overlay("An ordinary conversation in an office.")
    assert r5 is None


def test_detect_stat_card_and_stamp_badge():
    # Multi-currency & metrics
    s1 = detect_stat_card("피해액은 350만 원에 달했습니다.")
    assert s1 is not None
    assert "350만 원" in s1["value"]
    assert "PRICE ANCHOR" in s1["label"]

    s2 = detect_stat_card("The hedge fund lost $41.8M in under twenty minutes.")
    assert s2 is not None
    assert "$41.8M" in s2["value"]

    s3 = detect_stat_card("Khoản thất thoát lên tới 500 tỷ đồng.")
    assert s3 is not None
    assert "500 TỶ ĐỒNG" in s3["value"]

    # Stamp badges
    b1 = detect_stamp_badge("탁구장 환불 거부 사기 혐의가 입증되었습니다.")
    assert b1 == "PRICE_FRAUD"

    b2 = detect_stamp_badge("All classified contract records were stamped secret.")
    assert b2 == "CONFIDENTIAL"

    b3 = detect_stamp_badge("The regulatory agreement was declared void immediately.")
    assert b3 == "VOID"



def test_synthesize_deterministic_director_plan_pacing():
    story_beats = [
        {"content": "On an ordinary morning, Flight 21 vanished into thin air. " * 8},
        {"content": "Official public relations statements claimed weather was the primary cause. " * 8},
        {"content": "Internal maintenance records revealed 14 prior safety violations and ignored warnings. " * 8},
        {"content": "Whistleblower testimony exposed systemic cost-cutting and deliberate contract negligence. " * 8},
        {"content": "The federal aviation administration instituted mandatory operating restrictions across the entire fleet. " * 8}
    ]
    archetype = detect_cinematic_archetype("corporate_crime", "Amazon Air Cargo Crash")
    
    plan = _synthesize_deterministic_director_plan(
        episode_id="EN_EP0002_test_pacing",
        story_beats=story_beats,
        archetype=archetype
    )

    scenes = plan.get("scenes", [])
    assert len(scenes) >= 20

    # Test Hook Scenes (Scenes 0-7 from Beat 1)
    hook_scenes = scenes[:7]
    for idx, sc in enumerate(hook_scenes):
        assert sc["duration_est_sec"] <= 6
        assert sc["camera"]["movement"] in CANONICAL_CAMERA_MOVES
        assert 1 <= sc["bg_cluster_id"] <= 20

    # Test Core Scenes (Scenes 8+)
    core_scenes = scenes[8:]
    for sc in core_scenes:
        assert sc["duration_est_sec"] <= 10
        assert sc["camera"]["movement"] in CANONICAL_CAMERA_MOVES
        assert 1 <= sc["bg_cluster_id"] <= 20
        assert sc["motion_directive"] in {"dramatic_push", "subtle_drift", "split_whip", "forensic_lock"}


def test_build_remotion_props_with_camera_and_overlay(tmp_path):
    brain_data = {
        "scenes": [
            {
                "scene_id": "sc001",
                "narration": "Flight 21 vanished from radar control within seconds.",
                "duration_sec": 4,
                "camera": {"movement": "snap_zoom", "tension_level": "high"},
                "bg_cluster_id": 1,
            },
            {
                "scene_id": "sc002",
                "narration": "Executives signed a secret NDA contract to suppress the report.",
                "duration_sec": 6,
                "camera": {"movement": "macro_tilt", "tension_level": "medium"},
                "bg_cluster_id": 1,
            }
        ]
    }
    brain_file = tmp_path / "brain_input.json"
    brain_file.write_text(json.dumps(brain_data), encoding="utf-8")

    props = build_remotion_props_data(
        episode_id="TEST_EP",
        brain_input_path=str(brain_file),
        public_dir=str(tmp_path)
    )

    assert "scenes" in props
    assert len(props["scenes"]) == 2
    sc0 = props["scenes"][0]
    assert sc0["cameraMovement"] == "snap_zoom"
    assert sc0["tensionLevel"] == "high"
    assert sc0["bgClusterId"] == 1
    assert sc0["forensicOverlay"]["type"] == "radar_map"

    sc1 = props["scenes"][1]
    assert sc1["cameraMovement"] == "macro_tilt"
    assert sc1["tensionLevel"] == "medium"
    assert sc1["bgClusterId"] == 1
    assert sc1["forensicOverlay"]["type"] == "redacted_doc"


def test_korean_pacing_and_scene_count_no_underflow():
    """Verify Korean docudrama story with Latin punctuation (.!?) breaks down into >= 20 scenes per beat."""
    korean_beat = "탁구장 환불 사태의 배후에는 복잡한 금융 구조가 숨겨져 있었습니다. " * 15
    story_beats = [
        {"content": korean_beat}
        for _ in range(5)
    ]
    archetype = detect_cinematic_archetype("business_rise_fall", "Table Tennis Refund Trap")
    plan = _synthesize_deterministic_director_plan(
        episode_id="KR_EP0002_test_korean",
        story_beats=story_beats,
        archetype=archetype
    )
    scenes = plan.get("scenes", [])
    # 5 beats x ~25-30 scenes each must yield >= 100 scenes total
    assert len(scenes) >= 70
    assert all(sc["narration"].endswith((".", "!", "?")) for sc in scenes)
    assert all(1 <= sc["beat_index"] <= 5 for sc in scenes)
