"""
tests/test_desk_world_director.py

Unit & Integration Tests for Continuous Vox DeskWorld & Camera Journey (TEST-207 / FT-207)
Verifies:
1. Unified 3840x2160 desk world canvas with 4 stations.
2. Zero semantic hallucination (ASIC is corporate regulator, NOT a TSMC 7nm microchip).
3. Physical continuity: global connecting yarns link all stations.
4. Camera journey keyframes provide smooth pan/zoom without hard-cut resets.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from app.services.desk_world_director import (
    build_continuous_desk_world,
    ContinuousDeskWorldProps,
    DeskStation,
    CameraKeyframe
)


def test_desk_world_initialization():
    """Kiểm tra khởi tạo bàn điều tra liên tục 3840x2160 với 4 trạm."""
    props = build_continuous_desk_world(act_id="ACT_01")
    assert isinstance(props, ContinuousDeskWorldProps)
    assert props.world_width == 3840
    assert props.world_height == 2160
    assert len(props.stations) == 4

    station_ids = [s.station_id for s in props.stations]
    assert station_ids == ["STATION_01", "STATION_02", "STATION_03", "STATION_04"]


def test_station_01_strict_semantic_integrity():
    """Kiểm tra Station 01 bắt buộc là tài liệu ASIC Úc, cấm tuyệt đối chip TSMC 7nm."""
    props = build_continuous_desk_world(act_id="ACT_01")
    st1 = props.stations[0]

    hero = st1.hero_asset
    assert hero["type"] == "official_regulatory_filing"
    assert "AUSTRALIAN SECURITIES" in hero["authority"]
    assert "GENERAL PANTS CO" in hero["subject_entity"]
    assert "SECTION 436A" in hero["statutory_act"]

    # Strict check against semiconductor hallucination
    forbidden_terms = ["TSMC", "7nm", "microchip", "semiconductor", "circuit board", "fab"]
    full_text = " ".join([str(v) for v in hero.values()]).lower()
    for term in forbidden_terms:
        assert term.lower() not in full_text, f"Found forbidden semiconductor term '{term}' in Station 01 hero!"


def test_global_yarns_physical_desk_continuity():
    """Kiểm tra các sợi chỉ đỏ liên kết xuyên suốt giữa các trạm (Desk Continuity)."""
    props = build_continuous_desk_world(act_id="ACT_01")
    yarns = props.global_yarns

    assert len(yarns) >= 3, "Bắt buộc có tối thiểu 3 sợi chỉ đỏ liên trạm để dẫn hướng camera!"

    # Link 1: Station 1 -> Station 2
    assert yarns[0]["from_x"] < yarns[0]["to_x"]
    assert "REGULATORY NOTICE" in yarns[0]["label"]

    # Link 2: Station 2 -> Station 3 (downward)
    assert yarns[1]["from_y"] < yarns[1]["to_y"]

    # Link 3: Station 3 -> Station 4 (leftward)
    assert yarns[2]["from_x"] > yarns[2]["to_x"]


def test_camera_journey_keyframes_coverage():
    """Kiểm tra camera path bao phủ toàn bộ 32s của Act I không bị đứt gãy."""
    props = build_continuous_desk_world(act_id="ACT_01")
    cams = props.camera_keyframes

    assert len(cams) >= 8
    assert cams[0].time_sec == 0.0
    assert cams[0].target_x == 960.0
    assert cams[0].target_y == 540.0

    # Ensure monotonic time sequence
    times = [c.time_sec for c in cams]
    assert times == sorted(times), "Camera keyframes must be monotonically increasing in time!"
    assert times[-1] >= 32.0, "Camera path must cover the entire duration of Act I!"
