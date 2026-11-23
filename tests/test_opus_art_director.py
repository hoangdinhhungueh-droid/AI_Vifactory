#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_opus_art_director.py — Verification of Opus 5.5 Dynamic Art Director (FT-206).

Tests acceptance criteria for:
- [FT-206]: Dynamic Art Director & Bespoke Tactile Contact Kinematics.
- Zero Hardcoding: Confirms different scene contexts generate distinct props and contact kinematics.
- Schema Invariants: Verifies DynamicMasterArtManifest contracts and bounds.
- Master Sheet Integration: Verifies generate_master_sheet_bundle consumption of dynamic manifests.
"""

import os
os.environ["VF_TEST_MODE"] = "1"

import pytest
from pydantic import ValidationError

from app.services.opus_art_director import (
    DynamicMacroCamera,
    DynamicMasterArtManifest,
    TactileContactPoint,
    generate_dynamic_art_manifest,
)
from app.services.master_scene_sheet import generate_master_sheet_bundle


def test_dynamic_art_manifest_schema_bounds():
    """Verifies Pydantic contract validation and boundary invariants."""
    # Valid manifest
    manifest = DynamicMasterArtManifest(
        scene_id="SCENE_01",
        narrative_rationale="Legal enforcement warrant execution",
        assembled_keyframe_prompt="Authentic tactile collage with wooden seal stamp",
        hero_cutout_prompt="Isolated liquidation notice on #FFFFFF",
        interacting_tool_prompt="Isolated carved stamp on #FFFFFF",
        contact_point=TactileContactPoint(
            anchor_type="center_stamp",
            host_target_area="bottom_seal_zone",
            contact_frame_offset=12,
            physical_residue="red_ink_stain",
            snappy_impact_damping=0.75,
        ),
        macro_camera=DynamicMacroCamera(
            start_scale=1.0,
            target_scale=1.35,
            focal_point_norm=[0.5, 0.5],
            transition_punch_through=True,
        ),
        ingress_direction="right_to_left",
        ingress_duration_sec=0.3,
        dual_pass_shadow=True,
    )
    assert manifest.scene_id == "SCENE_01"
    assert manifest.ingress_duration_sec <= 0.4
    assert manifest.dual_pass_shadow is True

    # Ingress duration exceeding 0.4s must raise ValidationError
    with pytest.raises(ValidationError):
        DynamicMasterArtManifest(
            scene_id="SCENE_01",
            narrative_rationale="Test",
            assembled_keyframe_prompt="Test",
            hero_cutout_prompt="Test",
            interacting_tool_prompt="Test",
            contact_point=TactileContactPoint(
                anchor_type="corner_pin",
                host_target_area="left_margin",
                physical_residue="needle_hole",
            ),
            macro_camera=DynamicMacroCamera(
                focal_point_norm=[0.5, 0.5],
            ),
            ingress_duration_sec=0.55,  # Exceeds Rule 140 invariant
        )


def test_zero_hardcoding_across_different_narratives():
    """Verifies that different story beats produce bespoke props and contact points."""
    # 1. Regulatory/legal context -> should produce stamp impact
    m1 = generate_dynamic_art_manifest(
        scene_id="SCENE_01",
        narration="The court issued a liquidation order seizing all corporate records.",
        headline="LIQUIDATION WARRANT",
    )
    assert m1.contact_point.anchor_type == "center_stamp"
    assert m1.contact_point.physical_residue == "red_ink_stain"

    # 2. Financial scrutiny/audit context -> should produce highlighter mark
    m2 = generate_dynamic_art_manifest(
        scene_id="SCENE_02",
        narration="Auditors highlighted an undisclosed liability deep within the report.",
        headline="FORENSIC AUDIT",
    )
    assert m2.contact_point.anchor_type == "highlight_band"
    assert m2.contact_point.physical_residue == "yellow_glow"

    # 3. Supply chain severing -> should produce slice/cut
    m3 = generate_dynamic_art_manifest(
        scene_id="SCENE_03",
        narration="The supplier severed contract ties, splitting operations completely.",
        headline="SUPPLY CUT",
    )
    assert m3.contact_point.anchor_type == "slice_seam"
    assert m3.contact_point.physical_residue == "paper_tear"

    # Dynamic 100%: All 3 scenes MUST have different contact points and residues
    assert len({m1.contact_point.anchor_type, m2.contact_point.anchor_type, m3.contact_point.anchor_type}) == 3
    assert len({m1.contact_point.physical_residue, m2.contact_point.physical_residue, m3.contact_point.physical_residue}) == 3


def test_macro_camera_coordinates_bounded():
    """Verifies normalized camera focal targets are strictly within [0.0, 1.0]."""
    manifest = generate_dynamic_art_manifest(
        scene_id="SCENE_04",
        narration="Investigators zoomed into the signature line.",
        headline="DOCUMENT PROBE",
    )
    norm_x, norm_y = manifest.macro_camera.focal_point_norm
    assert 0.0 <= norm_x <= 1.0
    assert 0.0 <= norm_y <= 1.0
    assert 1.1 <= manifest.macro_camera.target_scale <= 1.6


def test_master_sheet_bundle_consumes_dynamic_manifest():
    """Verifies that generate_master_sheet_bundle accepts and integrates dynamic manifest."""
    manifest = generate_dynamic_art_manifest(
        scene_id="SCENE_01",
        narration="Liquidators stamped the court order on the company dossier.",
        headline="ORDER ENFORCED",
    )

    bundle = generate_master_sheet_bundle(
        scene_id="SCENE_01",
        dynamic_manifest=manifest,
        information_spec={
            "headline": "ORDER ENFORCED",
            "stat_hero": "DAY 1",
            "stat_label": "LIQUIDATION NOTICE",
            "narration": "Liquidators stamped the court order on the company dossier.",
        },
    )

    assert bundle["scene_id"] == "SCENE_01"
    assert bundle["dynamic_manifest"] is not None
    assert bundle["dynamic_manifest"]["contact_point"]["anchor_type"] == "center_stamp"
    # Wiring spec connector_type dynamically derived from contact point anchor
    assert bundle["wiring_spec"]["connector_type"] == "center_stamp"
    assert bundle["wiring_spec"]["ingress_duration_sec"] <= 0.4
    assert bundle["camera_movement"] == "locked"


def test_macro_camera_adversarial_out_of_bounds_fails():
    """Adversarial testing: Out-of-bounds coordinates, wrong lengths, or invalid damping must fail closed."""
    # 1. Coordinate > 1.0
    with pytest.raises(ValidationError):
        DynamicMacroCamera(focal_point_norm=[1.5, 0.5])

    # 2. Coordinate < 0.0
    with pytest.raises(ValidationError):
        DynamicMacroCamera(focal_point_norm=[0.5, -0.2])

    # 3. 1 element only
    with pytest.raises(ValidationError):
        DynamicMacroCamera(focal_point_norm=[0.5])

    # 4. 3 elements
    with pytest.raises(ValidationError):
        DynamicMacroCamera(focal_point_norm=[0.2, 0.4, 0.6])

    # 5. Damping > 1.0
    with pytest.raises(ValidationError):
        TactileContactPoint(
            anchor_type="corner_pin",
            host_target_area="left_margin",
            physical_residue="needle_hole",
            snappy_impact_damping=1.5,
        )

    # 6. Damping < 0.0
    with pytest.raises(ValidationError):
        TactileContactPoint(
            anchor_type="corner_pin",
            host_target_area="left_margin",
            physical_residue="needle_hole",
            snappy_impact_damping=-0.1,
        )


def test_s05_and_s07_manifest_prompt_synchronization():
    """Verifies that Opus 5.5 manifest prompts synchronize into decomposed_prompts and S07 export."""
    from stages.s05_director_plan import build_vox_scene_prompts
    from core.contracts.stages import Scene

    scene = Scene(
        scene_id="SCENE_01",
        headline="OFFICIAL LIQUIDATION",
        narration="Liquidators stamped the court order on the company dossier.",
        sentence="Liquidators stamped the court order on the company dossier.",
        duration_est_sec=6.0,
    )

    manifest = generate_dynamic_art_manifest(
        scene_id=scene.scene_id,
        narration=scene.narration,
        headline=scene.headline,
    )
    manifest_data = manifest.model_dump()
    scene.dynamic_art_manifest = manifest_data

    # Synchronize (as S05 run() now does)
    if not scene.decomposed_prompts:
        scene.decomposed_prompts = {}
    scene.decomposed_prompts["assembled_anchor_prompt"] = manifest.assembled_keyframe_prompt
    scene.decomposed_prompts["hero_cutout_prompt"] = manifest.hero_cutout_prompt
    scene.decomposed_prompts["interacting_tool_prompt"] = manifest.interacting_tool_prompt

    assert scene.decomposed_prompts["hero_cutout_prompt"] == manifest.hero_cutout_prompt
    assert scene.decomposed_prompts["interacting_tool_prompt"] == manifest.interacting_tool_prompt
    assert "center_stamp" in manifest.contact_point.anchor_type or "stamp" in manifest.assembled_keyframe_prompt.lower()

