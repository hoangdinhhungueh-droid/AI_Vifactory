#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_template_registry.py — Tests for Rule 132 Decoupled Template Registry."""

import pytest
from pathlib import Path
from app.services.template_registry import (
    TemplateRegistry,
    TemplateNotFoundError,
    CompatibilityError,
    PromptTrace,
    get_template_registry
)
from app.services.kinetic_sub_director import (
    build_cl3_paper_diorama_prompt,
    build_cl3_paper_diorama_image_prompt
)


def test_template_registry_loads_files():
    reg = get_template_registry()
    style = reg.get_style_block("deep_diorama")
    assert "Use the attached style sheet for materials only" in style
    assert len(style) > 100


def test_t2i_style_loads():
    reg = get_template_registry()
    t2i_style = reg.get_t2i_style_block()
    assert "Deep 3D paper diorama with aged-print collage textures" in t2i_style
    # Verify zero video kinematics in T2I style
    assert "camera is an actor" not in t2i_style.lower()


def test_missing_template_raises():
    reg = get_template_registry()
    with pytest.raises(TemplateNotFoundError):
        reg.read_template("non_existent_template_xyz123.md")


def test_camera_precedence_static_overhead():
    reg = get_template_registry()
    trace = PromptTrace()
    avoid = reg.resolve_avoid_block("STATIC_OVERHEAD", trace=trace)
    assert "no static locked-off camera" not in avoid
    assert "STATIC_OVERHEAD" in trace.camera_directive


def test_camera_precedence_slow_push_in():
    reg = get_template_registry()
    avoid = reg.resolve_avoid_block("SLOW_PUSH_IN_0_1X")
    assert "no static locked-off camera" in avoid


def test_prop_action_compatibility_caliper_rejected_on_drain():
    reg = get_template_registry()
    # drain_outflow forbids caliper
    with pytest.raises(CompatibilityError):
        reg.validate_prop_action_compatibility(
            action_type="drain_outflow",
            hero_prop="breached ledger boundary",
            tool_prop="machined brass vernier caliper",
            full_shot_text="The caliper clamps tightly"
        )


def test_prop_action_compatibility_caliper_allowed_when_clean():
    reg = get_template_registry()
    # Should not raise for valid drain tools
    reg.validate_prop_action_compatibility(
        action_type="drain_outflow",
        hero_prop="breached ledger boundary",
        tool_prop="official disclosure announcement slip",
        full_shot_text="disclosure slip slides smoothly"
    )


def test_build_cl3_paper_diorama_prompt_director_precedence():
    trace = PromptTrace()
    sub_plan = {
        "scene_id": "SCENE_01",
        "sentence": "2026年10月30日、",
        "camera_directive": "STATIC_OVERHEAD",
        "hero_cutout_object": 'archival date card reading "2026年10月30日"',
        "interacting_tool": "editorial hands sliding date placard",
        "action_type": "date_anchor",
        "tactile_action_verb": "drops cleanly into the groove beside",
        "physical_reaction": "fibers lock into alignment",
        "tactile_residue": "neatly anchored date placard",
    }
    prompt = build_cl3_paper_diorama_prompt(sub_plan, market="JP", scene_id="SCENE_01", trace=trace)
    assert "STATIC_OVERHEAD" in trace.camera_directive
    assert "no static locked-off camera" not in prompt
    assert "Locked overhead perspective, perfectly static" in prompt
    assert 'archival date card reading "2026年10月30日"' in prompt
    assert "vernier" not in prompt.lower()
    assert "caliper" not in prompt.lower()


def test_build_cl3_paper_diorama_prompt_scene3_zero_calipers():
    sub_plan = {
        "scene_id": "SCENE_03",
        "sentence": "約65億ドル相当の暗号資産が流出したと公表し、",
        "camera_directive": "SLOW_HORIZONTAL_PAN",
        "hero_cutout_object": 'breached crypto asset ledger boundary with token chips reading "約65億ドル"',
        "interacting_tool": 'official disclosure announcement slip reading "公表"',
        "action_type": "drain_outflow",
        "tactile_action_verb": "slides smoothly across the folio as token chips breach",
        "physical_reaction": "paper tokens spill continuously past the margin out of frame",
        "tactile_residue": "unsealed boundary crease with disclosure slip resting flat",
    }
    prompt = build_cl3_paper_diorama_prompt(sub_plan, market="JP", scene_id="SCENE_03")
    assert "caliper" not in prompt.lower()
    assert "vernier" not in prompt.lower()
    assert "Slow horizontal pan from left to right" in prompt
    assert "spill continuously" in prompt
