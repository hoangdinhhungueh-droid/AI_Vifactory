#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/opus_art_director.py — Opus 5.5 Dynamic Art Director Service (VOX Engine v3).

Executive Art Director powered by Claude Opus 5.5 (HHTech API) with GPT-6-Astra fallback.
Transforms narrative script into a bespoke DynamicMasterArtManifest per scene:
- Zero hardcoded boilerplate props (no universal calipers or red string).
- Domain-native visual language: surfaces, tools, artifacts, and residues match the specific topic.
- Generic open semantic contracts (Rule 128) and decoupled engine (Rule 132).
- Causal inter-scene spatial continuity and 12fps stop-motion choreography (Rule 140).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.model_gateway import get_global_gateway
from app.services.skill_loader import get_opus_art_director_rules

logger = logging.getLogger("opus_art_director")

# ==============================================================================
# PYDANTIC CONTRACTS (100% GENERIC & DOMAIN-NATIVE)
# ==============================================================================

class StageAtmosphereSpec(BaseModel):
    """Môi trường sân khấu đặc thù của đề tài."""
    model_config = ConfigDict(extra="ignore")
    surface_theme: str = Field(default="archival_cream_paper", description="e.g. dark_server_rack, sterile_lab_steel, blueprint_cyan, cargo_desk")
    lighting_mood: str = Field(default="investigative_spotlight", description="e.g. cold_blue_fluorescent, amber_spotlight_noir, terminal_green")
    ambient_texture_overlay: Optional[str] = Field(default=None, description="e.g. crt_scanlines, paper_fibers, steel_scratches")


class DomainArtifact(BaseModel):
    """Đạo cụ / Bằng chứng đặc thù của ngành."""
    model_config = ConfigDict(extra="ignore")
    artifact_name: str = Field(default="evidence_document", description="e.g. sec_form_10k, etherscan_tx, customs_bill_of_lading")
    artifact_type: str = Field(default="physical_document", description="e.g. digital_screen, physical_document, specimen, tool, data_chart")
    visual_description: str = Field(default="", description="Detailed visual description for generation or DOM rendering")


class KineticInteractionSpec(BaseModel):
    """Tương tác cơ học / xúc giác đặc thù của ngành ($H_1 \to H_7$)."""
    model_config = ConfigDict(extra="ignore")
    h_family: str = Field(default="H1_IMPACT", description="H1_IMPACT, H2_CONSTRAINT, H3_SEVER, H4_TETHER, H5_OPTICAL, H6_MARK, H7_DISPLACE")
    actor_tool: str = Field(default="official_stamp", description="e.g. barcode_laser_scanner, micropipette, rj45_cable, scalpel")
    contact_action: str = Field(default="contacts_document", description="e.g. laser_sweeps_over_code, droplet_absorbs, plug_snaps")
    resulting_residue: str = Field(default="status_mark", description="e.g. green_verified_glow, laser_burn_tag, sliced_tape_edge")
    contact_frame: int = Field(default=12, description="Frame trigger for mechanical contact (12fps cadence)")


class InterSceneCausalLink(BaseModel):
    """Chuỗi kết nối không gian & nhân quả nối tiếp giữa các cảnh."""
    model_config = ConfigDict(extra="ignore")
    inherited_anchor: Optional[str] = Field(default=None, description="Residue or detail inherited from prev scene")
    bequeathed_anchor: Optional[str] = Field(default=None, description="Residue or detail left on stage for next scene")
    transition_style: str = Field(default="macro_punch_through", description="macro_punch_through, camera_whip, paper_unfold, tear_matte")
    spatial_offset_coords: List[int] = Field(default_factory=lambda: [0, 0], description="Station coords [x, y] on continuous desk")


class TactileContactPoint(BaseModel):
    """Mechanical contact point spec for Remotion layer docking."""
    model_config = ConfigDict(extra="ignore")
    anchor_type: str = Field(default="center_dock", description="Generic anchor identifier")
    host_target_area: str = Field(default="document_face", description="Target contact zone on host")
    contact_frame_offset: int = Field(default=12, ge=0, le=120, description="Frame trigger for mechanical contact (12fps)")
    physical_residue: str = Field(default="contact_residue", description="Physical residue left behind")
    snappy_impact_damping: float = Field(default=0.75, ge=0.0, le=1.0, description="Stop-motion damping coefficient")


class DynamicMacroCamera(BaseModel):
    """Macro Punch-In camera choreography directed by Opus 5.5."""
    model_config = ConfigDict(extra="ignore")
    start_scale: float = Field(default=1.0, ge=0.5, le=2.0)
    target_scale: float = Field(default=1.35, ge=1.1, le=2.5, description="Close-up zoom scale into contact target")
    focal_point_norm: List[float] = Field(default_factory=lambda: [0.5, 0.5], description="Normalized focal point [norm_x, norm_y]")
    transition_punch_through: bool = Field(default=True, description="Punch-through zoom to match-cut into next scene")

    @field_validator("focal_point_norm")
    @classmethod
    def validate_focal_point(cls, v: List[float]) -> List[float]:
        if len(v) != 2:
            return [0.5, 0.5]
        return [max(0.0, min(1.0, float(v[0]))), max(0.0, min(1.0, float(v[1])))]


class DynamicMasterArtManifest(BaseModel):
    """
    Bespoke Master Scene Art Manifest generated by Opus 5.5 / Astra 6 for each scene.
    Enforces Rule 128 (Generic Contracts) and Rule 132 (Decoupled Engine).
    """
    model_config = ConfigDict(extra="ignore")
    scene_id: str = Field(..., pattern=r"^SCENE_\d{2}$")
    narrative_rationale: str = Field(default="", description="Rationale for visual metaphor and prop selection")
    narrative_thesis: Optional[str] = Field(default=None)
    production_route: str = Field(default="REMOTION_COLLAGE_MOTION", description="PLAYWRIGHT_LIVE_BROWSER or REMOTION_COLLAGE_MOTION")

    # Image generation prompts
    assembled_keyframe_prompt: str = Field(default="", description="AI prompt for generating full assembled master scene")
    assembled_scene_prompt: Optional[str] = Field(default=None)
    hero_cutout_prompt: str = Field(default="", description="AI prompt for generating isolated hero subject on pure #FFFFFF")
    hero_asset_prompt: Optional[str] = Field(default=None)
    interacting_tool_prompt: str = Field(default="", description="AI prompt for generating isolated interacting tool on pure #FFFFFF")
    tool_asset_prompt: Optional[str] = Field(default=None)

    # Domain-native 4 pillars
    atmosphere: Optional[StageAtmosphereSpec] = None
    hero_artifact: Optional[DomainArtifact] = None
    interaction: Optional[KineticInteractionSpec] = None
    causal_link: Optional[InterSceneCausalLink] = None

    # Mechanical tactile contact and macro camera directives
    contact_point: Optional[TactileContactPoint] = None
    macro_camera: Optional[DynamicMacroCamera] = None
    camera_movement: str = Field(default="MACRO_PUNCH_IN", description="Director camera movement directive")
    stop_motion_fps: int = Field(default=12, description="12fps stop-motion cadence on twos")
    ingress_direction: str = Field(default="right_to_left", description="Direction of fast ingress")
    ingress_duration_sec: float = Field(default=0.3, le=0.4, description="Ingress duration <= 0.4s")
    dual_pass_shadow: bool = Field(default=True, description="Dual-pass contact shadow requirement")


# ==============================================================================
# CORE SERVICE LOGIC
# ==============================================================================

def _clean_json_str(raw: str) -> str:
    """Extracts raw JSON payload from potentially markdown-wrapped LLM text."""
    cleaned = raw.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    return cleaned


def _generate_contextual_fallback_manifest(
    scene_id: str,
    narration: str,
    headline: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> DynamicMasterArtManifest:
    """
    High-fidelity deterministic fallback if LLM is offline or in dry-run mode.
    Derives unique domain-native props, H1-H7 mechanical interactions, and contact points from narration text.
    """
    ctx_obj = context or {}
    extra_text = " ".join(str(ctx_obj.get(k, "")) for k in ["core_idea", "visual_metaphor", "hero_cutout_object", "interacting_tool", "h_family", "topic"])
    text_lower = (narration + " " + headline + " " + extra_text).lower()

    # Domain Detection & Vocabulary Allocation (No hardcoded stereotypes!)
    if any(k in text_lower for k in ["crypto", "blockchain", "bitcoin", "solidity", "token", "hacker", "wallet", "ftx", "binance", "cyber", "exploit"]):
        route = "PLAYWRIGHT_LIVE_BROWSER" if any(k in text_lower for k in ["scan", "etherscan", "transaction", "github", "code", "wallet"]) else "REMOTION_COLLAGE_MOTION"
        surface = "dark_server_rack_terminal"
        lighting = "cold_blue_fluorescent"
        hero_name = "blockchain_smart_contract_audit_window"
        tool_name = "rj45_ethernet_cable_and_cursor"
        h_fam = "H6_MARK"
        action = "cursor_clicks_and_laser_data_packet_pulses"
        residue = "status_glow_transaction_reverted"
        focal = [0.55, 0.48]
        rationale = f"Cyber / Crypto domain forensic investigation for {scene_id}."
    elif any(k in text_lower for k in ["pharma", "biotech", "vaccine", "clinical", "fda", "drug", "blood", "patient", "theranos", "medical"]):
        route = "REMOTION_COLLAGE_MOTION"
        surface = "sterile_lab_stainless_steel"
        lighting = "high_contrast_lab_white"
        hero_name = "clinical_trial_specimen_slide"
        tool_name = "micropipette_dispenser"
        h_fam = "H1_IMPACT"
        action = "chemical_droplet_absorbs_into_reactive_matrix"
        residue = "chemical_purple_stain_reaction"
        focal = [0.50, 0.45]
        rationale = f"Biomedical forensic investigation for {scene_id}."
    elif any(k in text_lower for k in ["tariff", "customs", "shipping", "cargo", "container", "port", "warehouse", "logistics", "freight", "bill of lading"]):
        route = "REMOTION_COLLAGE_MOTION"
        surface = "cargo_plywood_desk"
        lighting = "amber_spotlight_noir"
        hero_name = "customs_bill_of_lading_document"
        tool_name = "barcode_laser_scanner"
        h_fam = "H6_MARK"
        action = "laser_beam_sweeps_over_container_tracking_barcode"
        residue = "barcode_verified_tag"
        focal = [0.52, 0.42]
        rationale = f"Customs & Supply Chain physical tracking for {scene_id}."
    elif any(k in text_lower for k in ["military", "war", "missile", "satellite", "radar", "border", "geopolitic", "espionage"]):
        route = "REMOTION_COLLAGE_MOTION"
        surface = "radar_optical_satellite_screen"
        lighting = "green_night_vision"
        hero_name = "classified_reconnaissance_satellite_imagery"
        tool_name = "target_crosshair_sight"
        h_fam = "H5_OPTICAL"
        action = "crosshair_locks_onto_clandestine_transit_node"
        residue = "gps_coordinate_lock"
        focal = [0.58, 0.50]
        rationale = f"Geopolitical satellite intelligence for {scene_id}."
    elif any(k in text_lower for k in ["real estate", "housing", "mortgage", "blueprint", "construction", "property", "architect"]):
        route = "REMOTION_COLLAGE_MOTION"
        surface = "blueprint_cyan_drafting_board"
        lighting = "clean_daylight"
        hero_name = "commercial_property_mortgage_deed"
        tool_name = "technical_vernier_caliper"
        h_fam = "H2_CONSTRAINT"
        action = "caliper_jaws_clamp_over_zoning_perimeter"
        residue = "pencil_boundary_circle"
        focal = [0.48, 0.40]
        rationale = f"Real estate & architectural forensic inquiry for {scene_id}."
    else:
        # Generic documentary investigation
        route = "PLAYWRIGHT_LIVE_BROWSER" if any(k in text_lower for k in ["filing", "sec", "10-k", "article", "bloomberg", "reuters", "press"]) else "REMOTION_COLLAGE_MOTION"
        surface = "archival_cream_paper"
        lighting = "investigative_spotlight"
        hero_name = f"official_forensic_evidence_record_{scene_id.lower()}"
        tool_name = "investigative_marking_tool"
        h_fam = "H6_MARK"
        action = "instrument_verifies_forensic_entry"
        residue = "verified_entry_glow"
        focal = [0.50, 0.50]
        rationale = f"Documentary evidence verification for {scene_id}."

    if ctx_obj.get("interacting_tool"):
        tool_name = str(ctx_obj["interacting_tool"])
    if ctx_obj.get("hero_cutout_object"):
        hero_name = str(ctx_obj["hero_cutout_object"])

    full_prompt = (
        f"Authentic Vox motion graphics composition, scene {scene_id}. Top-down 15-degree perspective. "
        f"Surface: {surface} with {lighting} lighting. "
        f"Primary artifact: {hero_name} securely mounted. "
        f"Actor tool: {tool_name} executing {action}, leaving visible {residue}. "
        "Dual-pass contact shadows with razor-sharp black occlusion edge and soft ambient drop shadow. "
        "Stylized editorial graphic novel illustration style, 35mm film grain, clean Swiss layout."
    )

    hero_prompt = (
        f"Isolated subject: {hero_name}, centered on pure solid white background #FFFFFF, "
        "crisp clean borders, sharp focus, high contrast, ready for alpha channel cutout."
    )

    tool_prompt = (
        f"Isolated instrument: {tool_name}, positioned at dynamic action angle on pure solid white background #FFFFFF, "
        "sharp defined edges, zero background spill, ready for alpha channel cutout."
    )

    return DynamicMasterArtManifest(
        scene_id=scene_id,
        narrative_rationale=rationale,
        narrative_thesis=rationale,
        production_route=route,
        assembled_keyframe_prompt=full_prompt,
        assembled_scene_prompt=full_prompt,
        hero_cutout_prompt=hero_prompt,
        hero_asset_prompt=hero_prompt,
        interacting_tool_prompt=tool_prompt,
        tool_asset_prompt=tool_prompt,
        atmosphere=StageAtmosphereSpec(
            surface_theme=surface,
            lighting_mood=lighting,
        ),
        hero_artifact=DomainArtifact(
            artifact_name=hero_name,
            artifact_type="physical_document",
            visual_description=hero_prompt,
        ),
        interaction=KineticInteractionSpec(
            h_family=h_fam,
            actor_tool=tool_name,
            contact_action=action,
            resulting_residue=residue,
            contact_frame=12,
        ),
        causal_link=InterSceneCausalLink(
            inherited_anchor=f"anchor_{scene_id.lower()}_prev",
            bequeathed_anchor=residue,
            transition_style="macro_punch_through",
            spatial_offset_coords=[(int(scene_id.split('_')[-1]) - 1) * 300, 0] if '_' in scene_id else [0, 0],
        ),
        contact_point=TactileContactPoint(
            anchor_type=f"anchor_{h_fam.lower()}",
            host_target_area="document_face",
            contact_frame_offset=12,
            physical_residue=residue,
            snappy_impact_damping=0.75,
        ),
        macro_camera=DynamicMacroCamera(
            start_scale=1.0,
            target_scale=1.38,
            focal_point_norm=focal,
            transition_punch_through=True,
        ),
        camera_movement="MACRO_PUNCH_IN",
        stop_motion_fps=12,
        ingress_direction="right_to_left",
        ingress_duration_sec=0.3,
        dual_pass_shadow=True,
    )


def generate_dynamic_art_manifest(
    scene_id: str,
    narration: str,
    headline: str = "",
    context: Optional[Dict[str, Any]] = None,
    preferred_model: str = "claude-opus-5-5",
    fallback_model: str = "gpt-6-astra",
    dry_run: bool = False,
) -> DynamicMasterArtManifest:
    """
    Generates a bespoke DynamicMasterArtManifest for a scene.
    Calls Claude Opus 5.5 via HHTech API (with Astra 6 fallback).
    Enforces Rule 128 (Generic Contracts) and Rule 132 (Decoupled Engine).
    """
    if not re.match(r"^SCENE_\d{2}$", scene_id):
        m = re.search(r"\d+", scene_id)
        if m:
            scene_id = f"SCENE_{int(m.group(0)):02d}"
        else:
            scene_id = "SCENE_01"

    # Fast offline / test / dry-run path when no HHTech credentials are configured
    from app.services.hhtech_reasoner import get_hhtech_key
    if dry_run or not get_hhtech_key() or os.getenv("VF_TEST_MODE") == "1":
        logger.info(f"[opus_art_director] Using contextual manifest for {scene_id} (offline / test / dry-run).")
        return _generate_contextual_fallback_manifest(
            scene_id=scene_id,
            narration=narration,
            headline=headline,
            context=context,
        )

    system_prompt = get_opus_art_director_rules()
    if not system_prompt:
        logger.warning("[opus_art_director] Missing system prompt from skill_loader, using internal baseline.")
        system_prompt = (
            "You are Claude Opus 5.5, Executive Art Director for Vox-style motion graphics. "
            "Respond ONLY with valid JSON matching DynamicMasterArtManifest schema."
        )

    user_payload = {
        "scene_id": scene_id,
        "headline": headline,
        "narration": narration,
        "context": context or {},
    }

    prompt_str = (
        f"Direct the bespoke domain-native motion graphics composition for this scene.\n\n"
        f"Input Data:\n{json.dumps(user_payload, indent=2, ensure_ascii=False)}\n\n"
        "Requirements:\n"
        "1. Dynamic 100%: Do not use generic props; pick bespoke domain-native tools and surfaces specific to the topic.\n"
        "2. Provide assembled_scene_prompt, hero_asset_prompt (#FFFFFF), and tool_asset_prompt (#FFFFFF).\n"
        "3. Specify domain atmosphere, hero artifact, kinetic interaction (H1-H7), and causal link.\n"
        "4. Specify production_route ('PLAYWRIGHT_LIVE_BROWSER' or 'REMOTION_COLLAGE_MOTION').\n"
        "5. Output JSON ONLY conforming to DynamicMasterArtManifest schema."
    )

    gateway = get_global_gateway()

    # 1. Attempt Primary: Claude Opus 5.5, then Fallback: GPT-6 Astra
    for model_name in [preferred_model, fallback_model]:
        try:
            logger.info(f"[opus_art_director] Calling {model_name} for {scene_id}...")
            raw_response = gateway.call_llm(
                prompt=prompt_str,
                model=model_name,
                system_prompt=system_prompt,
                temperature=0.25,
                max_tokens=1800,
            )
            cleaned_json = _clean_json_str(raw_response)
            data = json.loads(cleaned_json)

            # Ensure scene_id parity
            data["scene_id"] = scene_id

            # Parity mapping between schema keys
            if "assembled_scene_prompt" in data and not data.get("assembled_keyframe_prompt"):
                data["assembled_keyframe_prompt"] = data["assembled_scene_prompt"]
            if "hero_asset_prompt" in data and not data.get("hero_cutout_prompt"):
                data["hero_cutout_prompt"] = data["hero_asset_prompt"]
            if "tool_asset_prompt" in data and not data.get("interacting_tool_prompt"):
                data["interacting_tool_prompt"] = data["tool_asset_prompt"]
            if "narrative_thesis" in data and not data.get("narrative_rationale"):
                data["narrative_rationale"] = data["narrative_thesis"]

            manifest = DynamicMasterArtManifest.model_validate(data)
            logger.info(f"[opus_art_director] Successfully generated manifest for {scene_id} via {model_name}.")
            return manifest
        except Exception as err:
            logger.warning(f"[opus_art_director] Attempt with {model_name} for {scene_id} failed: {err}")

    # Fallback to deterministic contextual manifest
    logger.info(f"[opus_art_director] Falling back to contextual programmatic manifest for {scene_id}.")
    return _generate_contextual_fallback_manifest(
        scene_id=scene_id,
        narration=narration,
        headline=headline,
        context=context,
    )
