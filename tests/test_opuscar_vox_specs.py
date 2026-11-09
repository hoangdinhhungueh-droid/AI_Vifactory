#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_opuscar_vox_specs.py — Verification suite for Opuscar Vox Engine upgrades."""

import json
from pathlib import Path
import pytest

from app.services.kinetic_sub_director import (
    build_cl3_paper_diorama_prompt,
    build_cl3_paper_diorama_image_prompt,
    build_kinetic_causal_i2v_prompt,
    build_natural_kinetic_i2v_prompt,
    generate_scene_sub_director_plan,
)
from app.services.template_registry import get_template_registry


def test_t2i_opuscar_specifications_in_templates():
    reg = get_template_registry()
    t2i_style = reg.get_t2i_style_block()

    assert "#F7F9FB" in t2i_style
    assert "7% opacity" in t2i_style or "7%" in t2i_style
    assert "+8px offset" in t2i_style or "+8px" in t2i_style
    assert "Ben-Day halftone density fields" in t2i_style
    assert "pitted rubber stamps" in t2i_style
    assert "Swiss extreme scale contrast" in t2i_style
    assert "30-35% mass" in t2i_style
    assert "IBM Plex Mono" in t2i_style
    assert "6x12 chips" in t2i_style
    assert "acrylic loupe portal" in t2i_style
    assert "pincushion barrel distortion" in t2i_style
    assert "chromatic aberration" in t2i_style


def test_i2v_opuscar_specifications_in_templates():
    reg = get_template_registry()
    deep_diorama = reg.get_style_block("deep_diorama")

    assert "cubic-bezier(.7, 0, .2, 1)" in deep_diorama
    assert "back-overshoot" in deep_diorama
    assert "0.2s-0.3s" in deep_diorama or "0.2s - 0.3s" in deep_diorama
    assert "0.09s" in deep_diorama
    assert "2.6x to 1x" in deep_diorama
    assert "damped micro-bounce" in deep_diorama
    assert "dimension line rides with arrowhead taps" in deep_diorama
    assert "Dual-rate motion" in deep_diorama
    assert "12fps" in deep_diorama
    assert "on twos" in deep_diorama
    assert "readcheck formula" in deep_diorama
    assert "silence before slams" in deep_diorama


def test_build_cl3_paper_diorama_prompt_opuscar():
    sub_plan = {
        "sentence": "The court issues an immediate corporate asset freeze.",
        "hero_cutout_object": "official corporate seal stamp",
        "interacting_tool": "turned-wood vermilion docket seal stamp",
        "action_type": "H1_IMPACT",
        "tactile_action_verb": "strikes",
        "physical_reaction": "causes an indelible red wax imprint",
        "tactile_residue": "pressed wax residue",
        "camera_directive": "STATIC_OVERHEAD",
    }
    prompt = build_cl3_paper_diorama_prompt(sub_plan, market="EN", style_mode="deep_diorama")
    assert "Stamp slam in 0.09s" in prompt
    assert "drop from 2.6x to 1x" in prompt
    assert "damped micro-bounce" in prompt
    assert "soft ink squelch" in prompt
    assert "dual-rate motion" in prompt
    assert "12fps" in prompt
    assert "readcheck formula" in prompt


def test_build_natural_kinetic_i2v_prompt_opuscar():
    sub_plan = {
        "sentence": "The investigators measure the gap with precision calipers.",
        "hero_cutout_object": "unverified ledger document",
        "interacting_tool": "vintage precision calipers",
        "action_type": "H2_CONSTRAINT",
        "camera_directive": "STATIC_OVERHEAD",
    }
    prompt = build_natural_kinetic_i2v_prompt(sub_plan, market="EN", style_mode="deep_diorama")
    assert "cubic-bezier(.7, 0, .2, 1)" in prompt
    assert "back-overshoot" in prompt
    assert "readcheck formula" in prompt
    assert "dual-rate motion" in prompt
    assert "12fps" in prompt
    assert "two real silences" in prompt
    # Rule 140 & Precedence assertions: Caller objects and 3-Phase Kinematics must be preserved
    assert "unverified ledger document" in prompt
    assert "vintage precision calipers" in prompt
    assert "3-Phase Kinematics" in prompt
    assert "Phase 1 (Entry)" in prompt
    assert "Phase 2 (Contact)" in prompt
    assert "Phase 3 (Retract)" in prompt
    # Anti-Token-Leak assertion: Zero bare hex codes in prompt
    import re
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', prompt)


def test_build_cl3_paper_diorama_image_prompt_stamp_tool_override():
    """Verify build_cl3_paper_diorama_image_prompt triggers circular stamp target zone when tool is a stamp."""
    prompt = build_cl3_paper_diorama_image_prompt(
        "英国の専門家が警告する「身代金交渉の効率10倍」。",
        market="JP",
        scene_id="SCENE_02",
        hero_object_override="accounting ledger cardstock with 10X multiplier exhibit",
        interacting_tool_override="turned-wood vermilion seal stamp"
    )
    assert "accounting ledger cardstock with 10X multiplier" in prompt
    assert "designated circular target stamp zone with dotted red perimeter ring" in prompt
    assert "ZERO stamp tool drawn on document" in prompt
    # Zero bare hex codes
    import re
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', prompt)


def test_generate_scene_sub_director_plan_caller_overrides():
    """Verify caller action_verb, physical_reaction, and tactile_residue are preserved in c1 and micro_beats."""
    plan = generate_scene_sub_director_plan(
        scene_id="SCENE_01",
        sentence="2026年10月9日、テレ朝NEWSが伝えた衝撃の報告。",
        hero_cutout_object="Japanese broadcast newsprint archival report document on cream paper",
        interacting_tool="neon yellow marker highlighting key investigative clause",
        action_type="H6_MARK",
        action_verb="highlights the key investigative clause on",
        physical_reaction="vibrant fluorescent yellow ink absorbs into paper fibers",
        tactile_residue="an indelible highlighted evidentiary band",
        market="JP"
    )
    # Check c1 coupling
    c1 = plan["kinetic_couplings"][0]
    assert c1["action_verb"] == "highlights the key investigative clause on"
    assert c1["physical_reaction"] == "vibrant fluorescent yellow ink absorbs into paper fibers"
    assert c1["residue"] == "an indelible highlighted evidentiary band"

    # Check micro beats 3-phase kinematics and seed state invariant
    beats = plan["dynamic_micro_beats"]
    # B1 (P1_SETUP): tool must NOT be resting on the desk
    assert "poised off-screen" in beats[0]["action_description"]
    # Retract must be present in the hold phase
    retract_beats = [b for b in beats if "Retract" in b["action_description"]]
    assert len(retract_beats) >= 1
    assert "an indelible highlighted evidentiary band" in retract_beats[0]["action_description"]


def test_build_kinetic_causal_i2v_prompt_opuscar():
    plan = generate_scene_sub_director_plan(
        scene_id="SCENE_01",
        sentence="2026年10月9日、テレ朝NEWSが英国の専門家の見方として伝えた「身代金交渉の効率が10倍になり得る」という衝撃の数字。",
        hero_cutout_object="10X stat card",
        interacting_objects=["vermilion stamp"],
        duration_sec=6.0,
        market="JP",
    )
    prompt = build_kinetic_causal_i2v_prompt(plan)
    assert "Opuscar" in prompt
    assert "cubic-bezier(.7, 0, .2, 1)" in prompt
    assert "readcheck formula" in prompt
    assert "two real silences" in prompt
    assert "Dual-rate motion" in prompt
    # Anti-Token-Leak assertion: Zero bare hex codes in prompt
    import re
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', prompt)
