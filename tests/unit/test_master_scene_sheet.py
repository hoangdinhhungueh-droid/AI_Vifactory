#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for app/services/master_scene_sheet.py (Rule 121, 128, 140)."""

import json
from pathlib import Path
import pytest

from app.services.master_scene_sheet import (
    VOX_PALETTE,
    MOTION_THUMBNAIL_TYPES,
    resolve_scene_motion_thumbnail,
    extract_stat_hero_from_text,
    render_master_system_sheet_png,
    render_scene_contact_sheet_png,
    generate_master_scene_dashboard_html,
    generate_master_scene_package,
)


def test_vox_palette_and_motion_constants():
    """Rule 128 & 140: Verifies canonical Vox color palette and motion thumbnail archetypes."""
    assert VOX_PALETTE["archival_tan"] == "#C9BB9C"
    assert VOX_PALETTE["ink_black"] == "#1A1A1A"
    assert VOX_PALETTE["halftone_gray"] == "#8C8C8C"
    assert VOX_PALETTE["hot_red"] == "#B62E1F"
    assert VOX_PALETTE["mustard"] == "#D9A441"
    assert VOX_PALETTE["cream_paper"] == "#F4F1EA"

    assert len(MOTION_THUMBNAIL_TYPES) == 4
    ids = [m["id"] for m in MOTION_THUMBNAIL_TYPES]
    assert ids == [1, 2, 3, 4]


def test_resolve_scene_motion_thumbnail():
    """Verifies that scene kinematics correctly resolve to motion thumbnail archetypes."""
    # 1. Metric / Counter
    sc_metric = {"narration": "Thiệt hại ước tính hơn $123 tỷ USD trong 48 giờ."}
    mt_metric = resolve_scene_motion_thumbnail(sc_metric)
    assert mt_metric["id"] == 2
    assert "COUNTER" in mt_metric["title"]

    # 2. Map / Route / Underline
    sc_map = {"narration": "Toàn bộ hải trình và bản đồ di chuyển bị phát giác.", "headline": "Trade Route"}
    mt_map = resolve_scene_motion_thumbnail(sc_map)
    assert mt_map["id"] == 3
    assert "RED UNDERLINE" in mt_map["title"]

    # 3. Camera Drift
    sc_drift = {"narration": "Toàn cảnh phòng điều hành sau cú sập.", "second_by_second_action_breakdown": "Slow camera drift 2% across diorama"}
    mt_drift = resolve_scene_motion_thumbnail(sc_drift)
    assert mt_drift["id"] == 4
    assert "CAMERA HOLDS" in mt_drift["title"]

    # 4. Default Cutout Spring
    sc_hero = {"narration": "Nhân vật xuất hiện tại hiện trường với hồ sơ mật."}
    mt_hero = resolve_scene_motion_thumbnail(sc_hero)
    assert mt_hero["id"] == 1
    assert "CUTOUT SPRINGS UP" in mt_hero["title"]


def test_extract_stat_hero_from_text():
    """Verifies regex extraction of quantitative metrics for STAT HERO display."""
    assert extract_stat_hero_from_text("Giá trị hợp đồng đạt $123 tỷ.") == "$123 tỷ"
    assert extract_stat_hero_from_text("Tăng trưởng vượt 85% chỉ số.") == "85%"
    assert extract_stat_hero_from_text("Chi phí $500M thất thoát.") == "$500M"
    assert extract_stat_hero_from_text("Không có con số nào ở đây.") is None


def test_render_master_system_sheet_png(tmp_path):
    """Verifies PIL rendering of Master Visual System Sheet to PNG."""
    out_png = tmp_path / "test_system_sheet.png"
    rendered = render_master_system_sheet_png(
        episode_title="The Cooper Vanishing Act",
        output_path=out_png,
        market="EN",
        runtime_s=180.0,
        total_scenes=6,
    )
    assert rendered.exists()
    assert rendered.stat().st_size > 30000  # Should be a substantive image


def test_render_scene_contact_sheet_png(tmp_path):
    """Verifies PIL rendering of Scene Storyboard Contact Sheet to PNG."""
    out_png = tmp_path / "test_scenes_sheet.png"
    scenes = [
        {
            "scene_id": "SCENE_01",
            "headline": "THE HIJACKING",
            "duration_est_sec": 5.5,
            "narration": "At 30,000 feet, a quiet man handed the stewardess a folded note.",
            "hero_cutout_object": "Dan Cooper in dark suit",
            "h_family": "H1_IMPACT",
        },
        {
            "scene_id": "SCENE_02",
            "headline": "THE RANSOM DEMAND",
            "duration_est_sec": 6.0,
            "narration": "The note demanded $200,000 in negotiable currency and four parachutes.",
            "hero_cutout_object": "Ransom ledger document",
            "h_family": "H1_IMPACT",
        },
    ]
    rendered = render_scene_contact_sheet_png(
        scenes=scenes,
        output_path=out_png,
        cols=2,
        rows=1,
    )
    assert rendered.exists()
    assert rendered.stat().st_size > 20000


def test_generate_master_scene_dashboard_html(tmp_path):
    """Verifies generation of standalone interactive HTML dashboard."""
    out_html = tmp_path / "master_sheet_dashboard.html"
    scenes = [
        {
            "scene_id": "SCENE_01",
            "headline": "THE HIJACKING",
            "duration_est_sec": 5.5,
            "narration": "Dan Cooper boarded flight 305 wearing sunglasses and a black trenchcoat.",
            "hero_cutout_object": "Dan Cooper cutout",
            "interacting_objects": ["Torn ticket", "Aged briefcase"],
            "h_family": "H1_IMPACT",
            "i2v_prompt_omni": "Tactile diorama diorama with cutout spring and slow drift.",
        }
    ]
    rendered = generate_master_scene_dashboard_html(
        episode_id="EN_EP001_cooper_heist",
        episode_title="The Cooper Heist",
        scenes=scenes,
        output_path=out_html,
        market="EN",
        runtime_s=120.0,
    )
    assert rendered.exists()
    content = rendered.read_text(encoding="utf-8")
    assert "VOX MASTER SCENE DASHBOARD" in content
    assert "EN_EP001_cooper_heist" in content
    assert "THE HIJACKING" in content
    assert "Dan Cooper cutout" in content
    assert "TYPE SPECIMEN" in content
    assert "PALETTE SPECIFICATION" in content
    assert "MOTION THUMBNAIL SYSTEM" in content
    assert "RUN OMNI PILOT (2 SCENES DEMO)" in content


def test_generate_master_scene_package_full_flow(tmp_path):
    """Rule 121 & 126: Full integration test of generate_master_scene_package."""
    class DummyPaths:
        def __init__(self, root: Path):
            self.root = root
            self.composite_seeds_dir = root / "composite_seeds"
            self.composite_seeds_dir.mkdir(parents=True, exist_ok=True)

    class DummyManifest:
        market = "VN"

    class DummyContext:
        def __init__(self, root: Path):
            self.run_id = "VN_EP001_test_case"
            self.topic = "Bí Ẩn Vụ Án D.B. Cooper"
            self.paths = DummyPaths(root)
            self.manifest = DummyManifest()

    ctx = DummyContext(tmp_path)
    scenes = [
        {
            "scene_id": "SCENE_01",
            "headline": "CHUYẾN BAY ĐỊNH MỆNH",
            "duration_est_sec": 5.5,
            "narration": "Người đàn ông bí ẩn mang vali đen bước lên máy bay Boeing 727.",
            "hero_cutout_object": "Vali đen và nhân vật bí ẩn",
        },
        {
            "scene_id": "SCENE_02",
            "headline": "YÊU CẦU TIỀN CHUỘC",
            "duration_est_sec": 6.0,
            "narration": "Khoản tiền chuộc 200,000 USD được yêu cầu đóng vào bao tải vải bạt.",
            "hero_cutout_object": "Bao tải tiền chuộc",
        },
    ]

    manifest = generate_master_scene_package(ctx, scenes=scenes)
    assert manifest["episode_id"] == "VN_EP001_test_case"
    assert manifest["total_scenes"] == 2
    assert Path(manifest["files"]["master_sheet_dashboard_html"]).exists()
    assert Path(manifest["files"]["master_sheet_scenes_html"]).exists()
    assert Path(manifest["files"]["master_sheet_system_html"]).exists()
    assert Path(manifest["files"]["master_sheet_system_png"]).exists()
    assert Path(manifest["files"]["master_sheet_scenes_png"]).exists()
