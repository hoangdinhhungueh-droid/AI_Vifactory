#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_forensic_visual_inspector.py — Test suite for Forensic Visual & Kinematic Gate."""

from pathlib import Path

from app.services.forensic_visual_inspector import (
    ForensicVisualInspector,
    MotionAuditReport,
    MotionTimelineSample,
    PromptLintReport,
)


def test_lint_scene_prompts_detects_dead_stop_freeze():
    report = ForensicVisualInspector.lint_scene_prompts(
        scene_id="SCENE_01",
        t2i_prompt="Aged paper with Target Substrate: financial ledger rows and dotted perimeter ring",
        i2v_prompt="Snappy impact in 0.3s. In 0.3s, objects lock into dead-stop hold with dual-rate motion.",
        action_type="H1_IMPACT",
        hero_object="vermilion stamp",
        interacting_tool="turned-wood seal",
    )
    assert not report.passed
    rule_ids = [v.rule_id for v in report.violations]
    assert "RULE_140_ANTI_DEAD_STOP_FREEZE" in rule_ids


def test_lint_scene_prompts_detects_missing_target_substrate():
    report = ForensicVisualInspector.lint_scene_prompts(
        scene_id="SCENE_02",
        t2i_prompt="A blank diorama tabletop with no text and no labels.",
        i2v_prompt="Continuous tactile momentum with dual-rate motion: sustained micro-dynamics.",
        action_type="H1_IMPACT",
        hero_object="corporate seal stamp",
        interacting_tool="vermilion stamp",
    )
    assert not report.passed
    rule_ids = [v.rule_id for v in report.violations]
    assert "RULE_122_AXIS_4_TARGET_SUBSTRATE" in rule_ids


def test_lint_scene_prompts_passes_valid_kinetic_prompt():
    t2i = (
        "Tactile paper diorama. Target Substrate: The document surface is dense with pre-printed forensic evidence, "
        "dense micro-tabular financial ledger rows, and a designated circular target stamp zone with dotted red perimeter ring."
    )
    i2v = (
        "Action: Stamp slam in 0.09s ease-in drop from 2.6x to 1x with damped micro-bounce and soft ink squelch. "
        "Continuous tactile momentum with dual-rate motion: sustained kinetic micro-dynamics (continuous camera tracking, "
        "ink fiber absorption, living 12fps paper grain vibration on twos, zero frozen frames) adhering to readcheck formula."
    )
    report = ForensicVisualInspector.lint_scene_prompts(
        scene_id="SCENE_03",
        t2i_prompt=t2i,
        i2v_prompt=i2v,
        action_type="H1_IMPACT",
        camera_directive="DYNAMIC_CRASH_PUNCH",
        hero_object="corporate seal stamp",
        interacting_tool="vermilion seal",
    )
    assert report.passed
    assert len(report.violations) == 0


def test_audit_image_substrate_detects_blank_void(tmp_path: Path):
    from PIL import Image
    blank_img_path = tmp_path / "blank_substrate.jpg"
    img = Image.new("RGB", (1920, 1080), color=(245, 241, 234))
    img.save(blank_img_path)

    report = ForensicVisualInspector.audit_image_substrate_density(blank_img_path)
    assert report.verdict == "FAIL_BLANK_VOID"
    assert report.sobel_edge_density < 0.01
    assert "Blank void defect detected" in report.diagnosis


def test_audit_image_substrate_passes_textured_document(tmp_path: Path):
    from PIL import Image, ImageDraw
    textured_img_path = tmp_path / "textured_ledger.jpg"
    img = Image.new("RGB", (1920, 1080), color=(245, 241, 234))
    draw = ImageDraw.Draw(img)
    # Draw dense ledger lines and hatched patterns
    for y in range(150, 850, 12):
        draw.line([(250, y), (1650, y)], fill=(30, 30, 30), width=1)
    for x in range(250, 1650, 50):
        draw.line([(x, 150), (x, 850)], fill=(80, 80, 80), width=1)
    # Target stamp circle
    draw.ellipse([(900, 450), (1050, 600)], outline=(200, 30, 30), width=2)
    img.save(textured_img_path)

    report = ForensicVisualInspector.audit_image_substrate_density(textured_img_path)
    assert report.verdict == "PASS"
    assert report.sobel_edge_density >= 0.035
    assert "Substrate texture verified" in report.diagnosis


def test_generate_visual_health_card_compiles_markdown_and_json(tmp_path: Path):
    lint_rep = PromptLintReport(scene_id="SCENE_01", passed=True, violations=[])
    sample1 = MotionTimelineSample(time_sec=0.25, energy_pct=4.5, is_frozen=False)
    sample2 = MotionTimelineSample(time_sec=0.50, energy_pct=6.2, is_frozen=False)
    motion_rep = MotionAuditReport(
        video_path="test_clip.mp4",
        verdict="PASS",
        duration_sec=2.0,
        mean_motion_energy_pct=5.35,
        peak_motion_energy_pct=6.2,
        max_freeze_duration_sec=0.25,
        timeline_samples=[sample1, sample2],
        diagnosis="Kinematic vital signs healthy",
    )
    md_path = tmp_path / "card.md"
    json_path = tmp_path / "card.json"

    data = ForensicVisualInspector.generate_visual_health_card(
        episode_id="TEST_EP001",
        lint_reports=[lint_rep],
        motion_reports=[motion_rep],
        output_markdown_path=md_path,
        output_json_path=json_path,
    )
    assert data["overall_status"] == "PASS"
    assert md_path.exists()
    assert json_path.exists()
    md_text = md_path.read_text(encoding="utf-8")
    assert "VISUAL & KINEMATIC FORENSIC HEALTH CARD" in md_text
    assert "Motion Energy Second-by-Second Profiling" in md_text
