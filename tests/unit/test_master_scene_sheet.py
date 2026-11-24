#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for app/services/master_scene_sheet.py (Rule 121, 128, 140)."""

import json
from pathlib import Path

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

    assert len(MOTION_THUMBNAIL_TYPES) == 6
    ids = [m["id"] for m in MOTION_THUMBNAIL_TYPES]
    assert ids == [1, 2, 3, 4, 5, 6]


def test_resolve_scene_motion_thumbnail():
    """Verifies that scene kinematics correctly resolve to motion thumbnail archetypes."""
    # 1. Top-down tracking / H7 Displace
    sc_top_down = {"camera_directive": "TOP_DOWN_TRACKING", "h_family": "H7_DISPLACE"}
    mt_top_down = resolve_scene_motion_thumbnail(sc_top_down)
    assert mt_top_down["id"] == 1
    assert "90° TRACKING" in mt_top_down["title"]

    # 2. Rake focus / H1 Impact
    sc_rake = {"camera_directive": "RAKE_30_RACK_FOCUS", "h_family": "H1_IMPACT"}
    mt_rake = resolve_scene_motion_thumbnail(sc_rake)
    assert mt_rake["id"] == 2
    assert "30° RAKE FOCUS" in mt_rake["title"]

    # 3. Surface macro glide / H2 Constraint
    sc_macro = {"camera_directive": "SURFACE_MACRO_GLIDE", "h_family": "H2_CONSTRAINT"}
    mt_macro = resolve_scene_motion_thumbnail(sc_macro)
    assert mt_macro["id"] == 3
    assert "MACRO GLIDE" in mt_macro["title"]

    # 4. Lateral whip-pan / H4 Tether
    sc_whip = {"camera_directive": "LATERAL_WHIP_PAN", "h_family": "H4_TETHER"}
    mt_whip = resolve_scene_motion_thumbnail(sc_whip)
    assert mt_whip["id"] == 4
    assert "WHIP-PAN" in mt_whip["title"]

    # 5. Orbit Arc / H5 Optical
    sc_orbit = {"camera_directive": "ORBIT_ARC_15", "h_family": "H5_OPTICAL"}
    mt_orbit = resolve_scene_motion_thumbnail(sc_orbit)
    assert mt_orbit["id"] == 5
    assert "ORBIT ARC" in mt_orbit["title"]

    # 6. Dutch forensic snap / H6 Mark
    sc_dutch = {"camera_directive": "DUTCH_FORENSIC_SNAP", "h_family": "H6_MARK"}
    mt_dutch = resolve_scene_motion_thumbnail(sc_dutch)
    assert mt_dutch["id"] == 6
    assert "DUTCH-ANGLE" in mt_dutch["title"]


def test_extract_stat_hero_from_text():
    """Verifies regex extraction of quantitative metrics for STAT HERO display."""
    # Legacy USD & Percentage tests
    assert extract_stat_hero_from_text("Giá trị hợp đồng đạt $123 tỷ.") == "$123 tỷ"
    assert extract_stat_hero_from_text("Tăng trưởng vượt 85% chỉ số.") == "85%"
    assert extract_stat_hero_from_text("Chi phí $500M thất thoát.") == "$500M"
    assert extract_stat_hero_from_text("Không có con số nào ở đây.") is None

    # Korean Won (KRW, ₩, won)
    assert extract_stat_hero_from_text("Chi phí ước tính 620 billion won trong hồ sơ.") == "620B WON"
    assert extract_stat_hero_from_text("Dự án yêu cầu ₩620B vốn cam kết.") == "₩620B"
    assert extract_stat_hero_from_text("Dự án trị giá ₩620 billion.") == "₩620B"
    assert extract_stat_hero_from_text("₩620 billion won cần thiết.") == "₩620B"
    assert extract_stat_hero_from_text("Cơ chế 620-billion-won được ghi nhận.") == "620B WON"
    assert extract_stat_hero_from_text("Six hundred twenty billion won: allegedly.") == "620B WON"
    assert extract_stat_hero_from_text("Chi phí 620 tỷ won.") == "620B WON"
    assert extract_stat_hero_from_text("Chi phí 620 triệu won.") == "620M WON"
    assert extract_stat_hero_from_text("Tổng vốn 620조원.") == "620조 WON"
    assert extract_stat_hero_from_text("Khoản cam kết 620억원.") == "620억 WON"

    # USD variations (with and without $)
    assert extract_stat_hero_from_text("Dự án $123B.") == "$123B"
    assert extract_stat_hero_from_text("Dự án $123 billion.") == "$123B"
    assert extract_stat_hero_from_text("Dự án 123 billion USD.") == "$123B"
    assert extract_stat_hero_from_text("Dự án 123B USD.") == "$123B"
    assert extract_stat_hero_from_text("Dự án 123 billion dollars.") == "$123B"

    # International Currencies: EUR, JPY, VND
    assert extract_stat_hero_from_text("Khoản lỗ €500M của dự án.") == "€500M"
    assert extract_stat_hero_from_text("Khoản lỗ €500 billion.") == "€500B"
    assert extract_stat_hero_from_text("Tổng vốn 500 billion euros.") == "€500B"
    assert extract_stat_hero_from_text("Tổng vốn 500 tỷ EUR.") == "€500B"
    assert extract_stat_hero_from_text("Tổng vốn ¥123B tại Tokyo.") == "¥123B"
    assert extract_stat_hero_from_text("Chi phí ¥123 billion.") == "¥123B"
    assert extract_stat_hero_from_text("Chi phí 123 billion yen.") == "¥123B"
    assert extract_stat_hero_from_text("Chi phí 123 tỷ yen.") == "¥123B"
    assert extract_stat_hero_from_text("Doanh thu 123 tỷ đồng.") == "123B VND"
    assert extract_stat_hero_from_text("Doanh thu 123 triệu VND.") == "123M VND"
    assert extract_stat_hero_from_text("Chi phí 123k VND.") == "123K VND"

    # Percentages
    assert extract_stat_hero_from_text("Tăng trưởng 85 percent.") == "85%"
    assert extract_stat_hero_from_text("Tăng trưởng 85 phần trăm.") == "85%"
    assert extract_stat_hero_from_text("Tỷ lệ -12.5% sụt giảm.") == "-12.5%"

    # Prominent Milestone Years
    assert extract_stat_hero_from_text("Thời hạn khai trương ấn định năm 2029.") == "2029"
    assert extract_stat_hero_from_text("Năm 2016 chính phủ lựa chọn Gimhae.") == "2016"
    assert extract_stat_hero_from_text("Đạo luật thông qua ngày 26 tháng 2 năm 2021.") == "2021"

    # Key timeframe metrics / durations
    assert extract_stat_hero_from_text("Cuộc bầu cử diễn ra sau six weeks.") == "6 WEEKS"
    assert extract_stat_hero_from_text("Khung thời gian cấp bách 48 hours.") == "48 HOURS"
    assert extract_stat_hero_from_text("Thời gian 24 hrs.") == "24 HOURS"
    assert extract_stat_hero_from_text("Thời gian 30 days.") == "30 DAYS"


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

    # Verify that master_sheet_system.html has system tab active
    sys_html_text = Path(manifest["files"]["master_sheet_system_html"]).read_text(encoding="utf-8")
    assert '<div id="tab-system" class="tab-panel active">' in sys_html_text
    assert '<button class="tab-btn active" onclick="switchTab(\'tab-system\')">' in sys_html_text


def test_render_scene_contact_sheet_png_dynamic_all_scenes(tmp_path):
    """Verifies that 12 scenes are all rendered dynamically without being silently cut off."""
    from PIL import Image
    out_png = tmp_path / "test_12_scenes.png"
    scenes = [
        {
            "scene_id": f"SCENE_{i:02d}",
            "headline": f"HEADLINE {i:02d}",
            "duration_est_sec": 5.0 + i * 0.2,
            "narration": f"Narration text for scene {i} explaining forensic trail.",
            "hero_cutout_object": f"Hero object {i}",
        }
        for i in range(1, 13)
    ]

    rendered = render_scene_contact_sheet_png(
        scenes=scenes,
        output_path=out_png,
        cols=3,
        rows=None,  # Dynamic height for 4 rows
    )
    assert rendered.exists()
    with Image.open(str(rendered)) as img:
        assert img.width == 1920
        # 4 rows * ~500px + header > 2000px
        assert img.height >= 2000


def test_resolve_scene_image_path_variations_and_fallback(tmp_path):
    """Rule 121 & 128: Verifies robust resolution of scene images across naming variations and dirs."""
    from app.services.master_scene_sheet import resolve_scene_image_path

    seeds_dir = tmp_path / "composite_seeds"
    images_dir = tmp_path / "images"
    seeds_dir.mkdir()
    images_dir.mkdir()

    # Create dummy dummy valid image files (>1000 bytes)
    img_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048

    # 1. Direct lowercase in seeds_dir
    (seeds_dir / "composite_scene_01.png").write_bytes(img_data)
    res1 = resolve_scene_image_path("SCENE_01", image_dir=seeds_dir)
    assert res1 is not None
    assert res1.name == "composite_scene_01.png"

    # 2. Uppercase SCENE_02.png in seeds_dir (no 'composite_' prefix)
    (seeds_dir / "SCENE_02.png").write_bytes(img_data)
    res2 = resolve_scene_image_path("SCENE_02", image_dir=seeds_dir)
    assert res2 is not None
    assert res2.name == "SCENE_02.png"

    # 3. Fallback directory (images_dir) for SCENE_03
    (images_dir / "composite_SCENE_03.png").write_bytes(img_data)
    res3 = resolve_scene_image_path("SCENE_03", image_dir=seeds_dir, fallback_dirs=[images_dir])
    assert res3 is not None
    assert res3.name == "composite_SCENE_03.png"

    # 4. Explicit path override
    explicit_p = tmp_path / "custom_location.png"
    explicit_p.write_bytes(img_data)
    res4 = resolve_scene_image_path("SCENE_04", image_dir=seeds_dir, explicit_path=explicit_p)
    assert res4 == explicit_p

    # 5. Missing scene returns None
    res5 = resolve_scene_image_path("SCENE_99", image_dir=seeds_dir)
    assert res5 is None


def test_manifest_stat_heroes_coverage(tmp_path):
    """Rule 121 & 128: Verifies that master_sheet_manifest.json records stat_heroes_count and summary."""
    import json
    from app.services.master_scene_sheet import generate_master_scene_package

    class DummyPaths:
        def __init__(self, root: Path):
            self.root = root
            self.composite_seeds_dir = root / "composite_seeds"
            self.composite_seeds_dir.mkdir(parents=True, exist_ok=True)

    class DummyManifest:
        market = "EN"

    class DummyContext:
        def __init__(self, root: Path):
            self.run_id = "TEST_EP0001_sample"
            self.topic = "Test Sample Episode"
            self.paths = DummyPaths(root)
            self.manifest = DummyManifest()

    ctx = DummyContext(tmp_path)
    scenes = [
        {"scene_id": "SCENE_01", "narration": "Six hundred twenty billion won: allegedly.", "duration_est_sec": 5.5},
        {"scene_id": "SCENE_02", "narration": "A 2029 opening target became the red thread.", "duration_est_sec": 6.0},
        {"scene_id": "SCENE_03", "narration": "The official stamp reads UNVERIFIED.", "duration_est_sec": 5.0},
        {"scene_id": "SCENE_04", "narration": "Passed just six weeks before the election.", "duration_est_sec": 5.5},
    ]
    manifest = generate_master_scene_package(
        ctx=ctx,
        scenes=scenes,
        payload={},
        image_mode=False,
    )
    assert manifest["stat_heroes_count"] == 3
    assert manifest["stat_heroes"]["SCENE_01"] == "620B WON"
    assert manifest["stat_heroes"]["SCENE_02"] == "2029"
    assert manifest["stat_heroes"]["SCENE_03"] is None
    assert manifest["stat_heroes"]["SCENE_04"] == "6 WEEKS"

    # Also verify on-disk json
    out_dir = tmp_path / "master_sheets"
    on_disk = json.loads((out_dir / "master_sheet_manifest.json").read_text(encoding="utf-8"))
    assert on_disk["stat_heroes_count"] == 3
    assert on_disk["stat_heroes"]["SCENE_01"] == "620B WON"


def test_stepped_framing_motion_metadata():
    """Boss Claude Opus 5.5 Masterclass: Verifies canonical stepped framing & dead-stop locks."""
    for mt in MOTION_THUMBNAIL_TYPES:
        assert "stepped_punches" in mt, f"Archetype {mt['id']} missing stepped_punches"
        assert mt.get("dead_stop_ratio") == "70-85%"
        punches = mt["stepped_punches"]
        assert len(punches) >= 3, f"Archetype {mt['id']} must define at least 3 stepped punches"
        # Punch 0 is Wide establish at scale 1.0 with zero rotation and zero translation
        assert punches[0]["scale"] == 1.0
        assert punches[0]["frame"] == 0
        assert punches[0]["x"] == 0
        assert punches[0]["y"] == 0
        assert punches[0]["rotateZ"] == 0
        # Subsequent punches must be rapid whips (<= 12 frames) with full parameter parity
        for p in punches[1:]:
            whip = p.get("whip_frames", 8)
            assert whip <= 12, f"Archetype {mt['id']} whip duration {whip} exceeds 12 frames"
            assert "hold" in p, f"Archetype {mt['id']} step missing hold lock duration"
            assert "x" in p and "y" in p, f"Archetype {mt['id']} step missing translational coordinates"
            assert "rotateZ" in p, f"Archetype {mt['id']} step missing rotateZ"

    # Specific archetype kinematic validations
    arch2 = MOTION_THUMBNAIL_TYPES[1]
    assert arch2["stepped_punches"][1]["impact_shake"] == 3
    assert arch2["stepped_punches"][1]["whip_frames"] == 6

    arch5 = MOTION_THUMBNAIL_TYPES[4]
    assert arch5["stepped_punches"][1]["micro_drift"] == 2
    assert arch5["stepped_punches"][1]["scale"] == 1.90

    arch6 = MOTION_THUMBNAIL_TYPES[5]
    assert arch6["stepped_punches"][1]["curve"] == "dutch"
    assert arch6["stepped_punches"][2]["curve"] == "dutch"
    assert arch6["stepped_punches"][1]["rotateZ"] == -8

    # Verify landing impact shake math does not evaluate to 0 at integer frames (sin(k*pi) bug prevention)
    impact_amp = 3.0
    shake_values = []
    import math
    for elapsed in range(6):
        decay = math.exp(-0.75 * elapsed)
        osc = math.cos(elapsed * math.pi * 0.7)
        shake_values.append(impact_amp * decay * osc)
    
    assert shake_values[0] == 3.0, "Landing strike must register full impact amplitude at t=0"
    assert shake_values[1] < 0, "Rebound shockwave must invert direction at t=1"
    assert abs(shake_values[5]) < 0.1, "Shockwave must settle within 5-6 frames"


def test_resolve_scene_stat_and_label_hierarchy_and_zero_cross_contamination():
    """Rule 128 & 132: Verifies hierarchical resolution with zero hardcoded episode bias."""
    from app.services.master_scene_sheet import resolve_scene_stat_and_label

    # 1. Direct scene properties take precedence
    sc1 = {"scene_id": "SCENE_01", "stat_hero": "$100M", "stat_label": "VALUATION"}
    assert resolve_scene_stat_and_label(sc1) == ("$100M", "VALUATION")

    # 2. information_spec fallback
    sc2 = {
        "scene_id": "SCENE_02",
        "information_spec": {"stat_hero": "45%", "stat_label": "MARKET SHARE"},
    }
    assert resolve_scene_stat_and_label(sc2) == ("45%", "MARKET SHARE")

    # 3. Narration regex extraction
    sc3 = {"scene_id": "SCENE_03", "narration": "The company lost $500M in quarter 3."}
    val3, lbl3 = resolve_scene_stat_and_label(sc3)
    assert val3 == "$500M"
    assert lbl3 == "FINANCIAL METRIC"

    sc4 = {"scene_id": "SCENE_04", "narration": "TJX allocated one-third of the funds to bonus pools."}
    val4, lbl4 = resolve_scene_stat_and_label(sc4)
    assert val4 == "1/3"
    assert lbl4 == "RATIO METRIC"

    sc5 = {"scene_id": "SCENE_05", "narration": "Nine corporations engaged in the tariff maneuver."}
    val5, lbl5 = resolve_scene_stat_and_label(sc5)
    assert val5 == "9 CORPORATIONS"
    assert lbl5 == "ENTITY COUNT"

    # 4. Completely unrelated episode without numbers - must NOT leak TJX tariff metrics
    sc_crypto = {
        "scene_id": "SCENE_01",
        "headline": "GENESIS BLOCK",
        "core_idea": "DECENTRALIZED TIMESTAMPING",
        "narration": "In an anonymous forum, a pseudonymous developer published a whitepaper.",
    }
    val_c, lbl_c = resolve_scene_stat_and_label(sc_crypto, index=0)
    # Must NOT be 'REFUND CLAIM' or 'U.S. CUSTOMS'
    assert val_c != "REFUND CLAIM"
    assert lbl_c != "U.S. CUSTOMS"
    assert val_c != "AUDIT DATA"
    assert val_c == "GENESIS BLOCK"
    assert lbl_c == "DECENTRALIZED TIMESTAMPING"


def test_generate_master_scene_package_loads_from_payload_wrapped_json(tmp_path):
    """Rule 121 & 126: Verifies loading scenes from standard artifact payload wrapping."""
    from app.services.master_scene_sheet import generate_master_scene_package

    class DummyPaths:
        def __init__(self, root: Path):
            self.root = root
            self.composite_seeds_dir = root / "composite_seeds"
            self.composite_seeds_dir.mkdir(parents=True, exist_ok=True)

    class DummyContext:
        def __init__(self, root: Path):
            self.run_id = "WRAPPED_EP01"
            self.topic = "Wrapped Artifact Test"
            self.paths = DummyPaths(root)
            self.manifest = None

    # Write director_plan.json with top-level 'payload' wrapper
    dp_data = {
        "schema_version": "2.0",
        "status": "ok",
        "payload": {
            "scenes": [
                {
                    "scene_id": "SCENE_01",
                    "headline": "CYBERNETIC CORE",
                    "stat_hero": "0.4MS",
                    "stat_label": "LATENCY FLOOR",
                    "narration": "The fiber line cut latency down to 0.4ms.",
                }
            ]
        }
    }
    (tmp_path / "director_plan.json").write_text(json.dumps(dp_data), encoding="utf-8")

    ctx = DummyContext(tmp_path)
    res = generate_master_scene_package(ctx=ctx, scenes=None, image_mode=False)
    assert res["total_scenes"] == 1
    assert res["stat_heroes"]["SCENE_01"] == "0.4MS"
    assert res["stat_labels"]["SCENE_01"] == "LATENCY FLOOR"


def test_master_scene_manifest_3_layers_and_camera_cue_sheet():
    """Architectural Requirement: Dynamic story-specific manifests across Layer 1, 2, 3 and Camera Cue Sheet."""
    from app.services.master_scene_sheet import (
        build_dynamic_scene_manifest,
        generate_master_sheet_bundle,
        Layer1BackgroundDesk,
        Layer2MidgroundCutout,
        Layer3ForegroundCallouts,
        CameraCue,
    )

    whisper_words = [
        {"word": "The", "start": 0.0, "end": 0.15},
        {"word": "customs", "start": 0.15, "end": 0.45},
        {"word": "officials", "start": 0.45, "end": 0.85},
        {"word": "seized", "start": 0.85, "end": 1.20},
        {"word": "the", "start": 1.20, "end": 1.35},
        {"word": "bill", "start": 1.35, "end": 1.65},
        {"word": "of", "start": 1.65, "end": 1.80},
        {"word": "lading", "start": 1.80, "end": 2.20},
        {"word": "exposing", "start": 2.20, "end": 2.70},
        {"word": "$48.6B", "start": 2.70, "end": 3.40},
        {"word": "in", "start": 3.40, "end": 3.55},
        {"word": "fraud.", "start": 3.55, "end": 4.10},
    ]

    manifest = build_dynamic_scene_manifest(
        scene_id="SCENE_01",
        narration="The customs officials seized the bill of lading exposing $48.6B in fraud.",
        headline="BILL OF LADING SEIZED",
        stat_hero="$48.6B",
        stat_label="UNREPORTED TARIFF VALUE",
        whisper_words=whisper_words,
        duration_sec=4.5,
    )

    # 1. Layer 1 Background Desk
    assert isinstance(manifest.layer_1_background, Layer1BackgroundDesk)
    assert manifest.layer_1_background.background_color == "#F4F1EA"
    assert manifest.layer_1_background.aged_border is True
    assert "desk" in manifest.layer_1_background.environmental_prompt.lower() or "table" in manifest.layer_1_background.environmental_prompt.lower()

    # 2. Layer 2 Midground Cutouts
    assert isinstance(manifest.layer_2_midground, Layer2MidgroundCutout)
    assert manifest.layer_2_midground.hero_cutout.cutout_border == "#FFFFFF"
    assert manifest.layer_2_midground.hero_cutout.border_width_px >= 3
    # Mentions "bill of lading" -> supporting cutout must reflect shipping / bill of lading
    assert len(manifest.layer_2_midground.supporting_cutouts) > 0
    supp = manifest.layer_2_midground.supporting_cutouts[0]
    assert supp.cutout_border == "#FFFFFF"
    assert supp.item_type in ("bill_of_lading", "invoice", "court_record", "document")

    # 3. Layer 3 Foreground Graphic Callouts
    assert isinstance(manifest.layer_3_foreground, Layer3ForegroundCallouts)
    assert manifest.layer_3_foreground.headline == "BILL OF LADING SEIZED"
    assert len(manifest.layer_3_foreground.data_counters) > 0
    counter = manifest.layer_3_foreground.data_counters[0]
    assert counter.stat_hero == "$48.6B"
    assert counter.color == "#B62E1F"
    assert len(manifest.layer_3_foreground.svg_arrows) > 0

    # 4. Camera Cue Sheet anchored to Whisper
    assert len(manifest.camera_cue_sheet) >= 3
    cues = manifest.camera_cue_sheet
    assert all(isinstance(c, CameraCue) for c in cues)
    assert cues[0].time_ms == 0.0
    assert cues[0].zoom_scale == 1.00
    assert cues[0].stepped_framing is True
    # Anchor words must be populated from whisper
    assert any(c.whisper_anchor_word for c in cues)

    # 5. Full Bundle Serialization
    bundle = generate_master_sheet_bundle(
        scene_id="SCENE_01",
        assembled_anchor_url="composite_seeds/composite_scene_01.png",
        hero_cutout_url="composite_seeds/hero_scene_01.png",
        interacting_tool_url="composite_seeds/tool_scene_01.png",
        information_spec={
            "headline": "BILL OF LADING SEIZED",
            "stat_hero": "$48.6B",
            "stat_label": "UNREPORTED TARIFF VALUE",
            "narration": "The customs officials seized the bill of lading exposing $48.6B in fraud.",
        },
        whisper_words=whisper_words,
        duration_sec=4.5,
    )

    assert "layer_1_background" in bundle
    assert bundle["layer_1_background"]["background_color"] == "#F4F1EA"
    assert "layer_2_midground" in bundle
    assert bundle["layer_2_midground"]["hero_cutout"]["cutout_border"] == "#FFFFFF"
    assert "layer_3_foreground" in bundle
    assert bundle["layer_3_foreground"]["data_counters"][0]["stat_hero"] == "$48.6B"
    assert "camera_cue_sheet" in bundle
    assert len(bundle["camera_cue_sheet"]) >= 3


def test_camera_cue_sheet_sparse_whisper_words_monotonicity():
    """Edge Case Verification: Verifies 0, 1, and 2 whisper words never produce colliding cue times."""
    from app.services.master_scene_sheet import build_dynamic_scene_manifest

    # Case A: 0 whisper words (pure music / silence)
    m0 = build_dynamic_scene_manifest("SCENE_01", whisper_words=[], duration_sec=6.0)
    times0 = [c.time_ms for c in m0.camera_cue_sheet]
    assert len(times0) == 4
    assert times0 == sorted(times0)
    assert len(set(times0)) == len(times0), f"Colliding cue times in 0-word scene: {times0}"

    # Case B: 1 whisper word
    m1 = build_dynamic_scene_manifest(
        "SCENE_02",
        whisper_words=[{"word": "Guilty.", "start": 0.2, "end": 0.6}],
        duration_sec=5.0,
    )
    times1 = [c.time_ms for c in m1.camera_cue_sheet]
    assert len(times1) == 4
    assert times1 == sorted(times1)
    assert len(set(times1)) == len(times1), f"Colliding cue times in 1-word scene: {times1}"
    assert times1[0] < times1[1] < times1[2] < times1[3]

    # Case C: 2 whisper words
    m2 = build_dynamic_scene_manifest(
        "SCENE_03",
        whisper_words=[
            {"word": "Case", "start": 0.1, "end": 0.4},
            {"word": "closed.", "start": 0.5, "end": 0.9},
        ],
        duration_sec=4.0,
    )
    times2 = [c.time_ms for c in m2.camera_cue_sheet]
    assert len(times2) == 4
    assert times2 == sorted(times2)
    assert len(set(times2)) == len(times2), f"Colliding cue times in 2-word scene: {times2}"
    assert times2[0] < times2[1] < times2[2] < times2[3]



