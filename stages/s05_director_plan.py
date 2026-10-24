#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s05_director_plan.py — Stage S5: Vox-Style Director Plan & Prompts (AVF-STAB-001).

Implements Stage Shape Standard. Encodes Prompt 2 (Director & Image) and Prompt 3 (Universal Video Prompt).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import RunContext
from core.contracts.stages import (
    AssetRegistry,
    AssetRegistryItem,
    Chunk,
    Provenance,
    Scene,
    Shot,
    StageArtifact,
    StageID,
)
from core.gates import emit_artifact, validate_artifact
from tools.codemap.runtime import pipeline_stage
from vox.planner import plan_scenes_from_script

logger = logging.getLogger("s05_director_plan")

STAGE: StageID = StageID.S5_DIRECTOR_PLAN

__all__ = [
    "STAGE",
    "run",
    "build_vox_scene_prompts",
    "plan_scenes_from_script",
    "partition_timeline_into_chunks",
    "build_master_asset_registry",
    "validate_and_sanitize_director_plan",
    "generate_7acc_flow_manifest",
    "FLOW_ACCOUNTS"
]

FLOW_ACCOUNTS: List[str] = ["acc_01", "acc_02", "acc_03", "acc_04", "acc_05", "acc_06", "acc_07"]


def generate_7acc_flow_manifest(target_dir: Path, episode_id: str, scenes: List[Any]) -> Dict[str, Any]:
    """Generates canonical flow_video_manifest.json for Google Flow (Veo 3.1 / Omni 1.1 Flash)
    with guaranteed round-robin rotation across 7 accounts (Rule 125, 128, 132).
    """
    clips = []
    for idx, s in enumerate(scenes):
        slot = FLOW_ACCOUNTS[idx % len(FLOW_ACCOUNTS)]
        sc_id = getattr(s, "scene_id", None) or (s.get("scene_id") if isinstance(s, dict) else f"SCENE_{idx+1:02d}")
        out_fn = f"clip_{sc_id.lower()}.mp4"
        i2v_prompt = (
            getattr(s, "i2v_prompt_omni", None)
            or getattr(s, "i2v_prompt_google_flow", None)
            or (s.get("i2v_prompt_omni") if isinstance(s, dict) else "")
            or (s.get("i2v_prompt_google_flow") if isinstance(s, dict) else "")
            or (s.get("flow_video_prompt") if isinstance(s, dict) else "")
            or ""
        )
        dur = float(
            getattr(s, "duration_est_sec", None)
            or (s.get("duration_est_sec") if isinstance(s, dict) else 5.0)
            or 5.0
        )
        hero = getattr(s, "hero_cutout_object", None) or (s.get("hero_cutout_object") if isinstance(s, dict) else "")
        cam = getattr(s, "camera_directive", None) or (s.get("camera_directive") if isinstance(s, dict) else "STATIC_OVERHEAD")

        clips.append({
            "scene_id": sc_id,
            "clip_index": idx + 1,
            "flow_slot": slot,
            "output_filename": out_fn,
            "prompt": i2v_prompt,
            "duration_sec": dur,
            "hero_cutout_object": hero,
            "camera_directive": cam
        })

    manifest = {
        "episode_id": episode_id,
        "format": "FLOW_VEO_7_ACCOUNT_DISPATCH",
        "total_clips": len(clips),
        "accounts_used": FLOW_ACCOUNTS,
        "clips": clips
    }
    target_dir.mkdir(parents=True, exist_ok=True)
    man_path = target_dir / "flow_video_manifest.json"
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info(f"[s05_director_plan] Generated flow_video_manifest.json ({len(clips)} clips) -> {man_path}")
    return manifest


def build_vox_scene_prompts(
    scene: Scene,
    idx: int,
    total_scenes: int,
    prev_scene: Optional[Scene] = None
) -> Dict[str, Any]:
    """Decomposes scene into rich Vox Physical Objects, Kinematics, Omni and Google Flow I2V Prompts."""
    headline = scene.headline or f"BEAT {idx+1:02d}"
    color = scene.color_accent or "Vox Yellow #F2C230 & Navy #1B2B4A"
    hero_obj = scene.visual_metaphor or f"Tactile paper document representing beat {idx+1:02d}"
    dur = float(scene.duration_est_sec or 5.0)

    # Pick deterministic single camera movement (Studio Touch 7: Single Camera Mandate)
    allowed_camera_directives = ["STATIC_OVERHEAD", "SLOW_PUSH_IN_0_1X", "SLOW_HORIZONTAL_PAN", "SUBTLE_TILT_DOWN"]
    camera_directive = allowed_camera_directives[idx % len(allowed_camera_directives)]
    camera_move = CANONICAL_CAMERA_MOVES[idx % len(CANONICAL_CAMERA_MOVES)]

    # 1. Physical Objects Breakdown & Objects Roster
    objects = [
        {
            "id": f"o{idx+1}_1",
            "name": hero_obj,
            "attributes": ["tactile paper cutout", "2-4px deckle edge", "soft drop shadow"],
            "role": "primary"
        },
        {
            "id": f"o{idx+1}_2",
            "name": "crimson forensic seal and brass anchor pin",
            "attributes": ["crimson wax imprint", "brass patina pin"],
            "role": "secondary"
        },
        {
            "id": f"o{idx+1}_3",
            "name": "aged cream newsprint desk backdrop",
            "attributes": ["#F4F1EA", "vintage print halftone grid", "creased archival paper"],
            "role": "backdrop"
        }
    ]

    objects_roster = [
        {
            "object_id": f"o{idx+1}_1",
            "name": f"asset_doc_{idx+1:03d}",
            "type": "paper_cutout",
            "texture_spec": "Halftone black-and-white 60lpi print with crisp 3px white deckle edge and 2mm flat drop shadow"
        },
        {
            "object_id": f"o{idx+1}_2",
            "name": "asset_seal_stamp",
            "type": "tactile_prop",
            "texture_spec": "Solid forensic tool, rubber stamp with crimson ink"
        }
    ]

    # 2. Kinematics Actions Breakdown & Second-by-Second Decomposition (S0 -> S1 -> S2)
    t_entry_end = min(1.5, round(dur * 0.3, 1))
    t_hold_start = max(t_entry_end + 1.0, round(dur - 1.0, 1))
    second_by_second_action_breakdown = [
        {
            "time_window": f"0.0s - {t_entry_end:.1f}s",
            "active_object_id": f"o{idx+1}_1",
            "action_type": "slide_in",
            "mechanical_action": f"{hero_obj} slides diagonally into center anchor with snappy deceleration",
            "spatial_coordinate": "X:30%, Y:45%"
        },
        {
            "time_window": f"{t_entry_end:.1f}s - {t_hold_start:.1f}s",
            "active_object_id": f"o{idx+1}_2",
            "action_type": "stamp_strike",
            "mechanical_action": "Crimson rubber inspection seal slams downward onto lower margin, micro paper dust settles",
            "spatial_coordinate": "X:35%, Y:60%"
        },
        {
            "time_window": f"{t_hold_start:.1f}s - {dur:.1f}s",
            "active_object_id": "ALL_OBJECTS",
            "action_type": "living_poster_hold",
            "mechanical_action": "All objects freeze rigidly into spatial anchor, subtle 12fps paper drop shadow breathing",
            "spatial_coordinate": "LOCKED_SPATIAL_ANCHOR"
        }
    ]

    actions = [
        {
            "subject": f"o{idx+1}_1",
            "verb": "slides_in",
            "target": "center_stage",
            "motion": "smooth_slide_left_to_right",
            "intensity": "low",
            "role": "primary"
        },
        {
            "subject": f"o{idx+1}_2",
            "verb": "stamps",
            "target": f"o{idx+1}_1",
            "motion": "downward_impact",
            "intensity": "high",
            "role": "secondary"
        }
    ]

    # 3. Kinematic Motion Track
    motion_track = {
        "entry_action": f"0.0-{t_entry_end:.1f}s: Tactile entry of {hero_obj} sliding into center stage with soft paper drop shadow.",
        "assembly_step": f"{t_entry_end:.1f}-{t_hold_start:.1f}s: Crimson seal stamps firmly onto the document; paper cutouts assemble and lock into spatial anchor.",
        "spatial_anchor": "Center-left quadrant of canvas, permanently locked as anchor for subsequent scene.",
        "camera_rule": camera_directive
    }

    # 4. Graphic Typography
    graphic_typo = {
        "headline": headline,
        "english_tag": "FORENSIC EVIDENCE",
        "color_bar": color,
        "position": "Top-left quadrant, occupying 25% negative space"
    }

    headline_typography = {
        "text": headline,
        "color_accent": color,
        "reserved_negative_space": "Top 30% empty flat block"
    }

    # 5. Visual Continuity Link
    continuity_link = (
        f"Object o{idx+1}_1 remains locked on the newsprint desk; "
        f"Scene {idx+2 if idx+1 < total_scenes else 'Outro'} physically builds upon this exact foundation."
    )

    audio_foley_cues = [
        {"at_second": 0.8, "sfx_name": "paper_slide_fast"},
        {"at_second": min(2.0, t_hold_start - 0.2), "sfx_name": "stamp_slam_heavy"}
    ]

    # 6. 5-Layer Image Prompt (Master Prompt: vox_b3_director_image_prompt.md)
    image_prompt = (
        f"Editorial investigative documentary frame in signature VOX paper-cut collage style. "
        f"[Layer 1: Aged Cream Newsprint Desk #F4F1EA with subtle print halftone grid] -> "
        f"[Layer 2: bold flat geometric color block in {color}] -> "
        f"[Layer 3: negative space reserved for large bold editorial typography '{headline}', occupying 25% of frame] -> "
        f"[Layer 4: high-contrast tactile paper cutout subject with crisp 2-4px white deckle edge and realistic soft drop shadow: {hero_obj}. "
        f"Interacting elements: crimson forensic seal stamp and brass pin] -> "
        f"[Layer 5: vintage print ink texture, natural paper grain, subtle fold creases, authentic newspaper print misregistration]. "
        f"Strictly locked color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A on Off-white Cream #F4F1EA. "
        f"Clear object-assembly composition, strong editorial hierarchy, tactile paper craft. "
        f"Negative prompt: no clutter, no unnecessary objects, no glossy 3D rendering, no photorealistic background, "
        f"no oversaturated rainbow colors, maintain clean premium VOX editorial collage."
    )

    # 7. Sub-Director Plan & Causal Compound Verb Prompts (Rule 140 v3)
    try:
        from app.services.kinetic_sub_director import build_kinetic_causal_i2v_prompt, generate_scene_sub_director_plan
        sub_plan = generate_scene_sub_director_plan(
            scene_id=getattr(scene, "scene_id", f"SCENE_{idx+1:02d}"),
            sentence=getattr(scene, "narration_text", "") or getattr(scene, "sentence", "") or headline,
            hero_cutout_object=hero_obj,
            interacting_objects=["crimson forensic seal stamp", "brass anchor pin"],
            duration_sec=dur,
            market=getattr(scene, "market", "EN") or "EN"
        )
        i2v_google_flow = build_kinetic_causal_i2v_prompt(sub_plan, camera_directive=camera_directive)
        i2v_omni = i2v_google_flow
    except Exception as _k_err:
        logger.warning(f"[build_vox_scene_prompts] Kinetic sub-director fallback notice: {_k_err}")
        sub_plan = {}
        i2v_omni = (
            f"Tactile paper cutout animation in signature Vox documentary style. "
            f"Animate composition: {hero_obj} on Aged Cream Paper #F4F1EA desk. "
            f"Hero cutout slides in smoothly from left edge, crimson verification stamp impacts firmly at 3.0s, "
            f"holding locked spatial anchor with subtle paper micro-breathing <= 2px. "
            f"Static top-down camera, zero camera drift."
        )
        i2v_google_flow = (
            f"Editorial paper cutout animation in Vox documentary style. Headline: '{headline}'. "
            f"IMAGE-TO-VIDEO TECHNICAL DIRECTIVE: "
            f"[Camera: {camera_directive}]. "
            f"[Timeline Kinematics: From 0.0s to {t_entry_end:.1f}s: {hero_obj} slides into position and lands flat. "
            f"From {t_entry_end:.1f}s to {t_hold_start:.1f}s: Crimson rubber seal stamps firmly onto document. "
            f"From {t_hold_start:.1f}s to {dur:.1f}s: Rigid spatial anchor hold with micro paper breathing]. "
            f"[Pacing: Restrained mechanical paper physics, snappy stops, micro settling]. "
            f"[Constraints: Strict flat 2D tactile paper collage physics, zero 3D fluid morphing, zero face warping]."
        )

    return {
        "canvas_workspace": "Aged Cream Newsprint Desk #F4F1EA with subtle print halftone grid",
        "hero_cutout_object": hero_obj,
        "interacting_objects": ["crimson forensic seal stamp", "brass anchor pin"],
        "motion_track_and_assembly": motion_track,
        "graphic_typography": graphic_typo,
        "visual_continuity_link_to_next": continuity_link,
        "objects": objects,
        "actions": actions,
        "camera_move": camera_move,
        "camera_directive": camera_directive,
        "objects_roster": objects_roster,
        "second_by_second_action_breakdown": second_by_second_action_breakdown,
        "headline_typography": headline_typography,
        "audio_foley_cues": audio_foley_cues,
        "image_prompt": image_prompt,
        "i2v_prompt_omni": i2v_omni,
        "i2v_prompt_google_flow": i2v_google_flow,
        "scene_sub_director_plan": sub_plan,
    }


def build_universal_video_prompt(scene: Scene) -> str:
    """Encodes Causal Compound Video Prompt (Rule 140 v3 / Made by AI Playbook)."""
    color = scene.color_accent or "Vox Crimson #E53935"
    if scene.i2v_prompt_google_flow:
        return scene.i2v_prompt_google_flow
    try:
        from app.services.kinetic_sub_director import build_kinetic_causal_i2v_prompt, generate_scene_sub_director_plan
        sub_plan = generate_scene_sub_director_plan(
            scene_id=getattr(scene, "scene_id", "SCENE_01"),
            sentence=getattr(scene, "narration_text", "") or getattr(scene, "sentence", "") or getattr(scene, "headline", ""),
            hero_cutout_object=getattr(scene, "visual_metaphor", "") or getattr(scene, "hero_cutout_object", ""),
            interacting_objects=["tactile measurement tool", "crimson verification seal"],
            duration_sec=float(getattr(scene, "duration_est_sec", 8.0) or 8.0),
            market=getattr(scene, "market", "EN") or "EN"
        )
        return build_kinetic_causal_i2v_prompt(sub_plan, camera_directive=getattr(scene, "camera_directive", ""))
    except Exception as _ex:
        logger.warning(f"[build_universal_video_prompt] Fallback notice: {_ex}")
    return (
        f"Editorial paper cutout animation in Vox documentary style. "
        f"Animate completed composition: {scene.visual_metaphor or 'Tactile paper elements'} on Cream Paper #F4F1EA background. "
        f"0.0-2.0s: Tactile entry of bold geometric paper shapes and headline '{scene.headline or 'EDITORIAL FOCUS'}'. "
        f"2.0-7.0s: Main cutout elements assemble smoothly with layered drop shadows and deckle white edges. "
        f"7.0-10.0s: Spatial anchor locked, subtle micro-shadow breathing <= 2px, zero drift. "
        f"Camera: Completely static top-down desk view, crisp focus, no 3D pan or tilt. "
        f"Color Palette: {color} on muted paper texture."
    )


def partition_timeline_into_chunks(
    scenes: List[Scene],
    target_chunk_duration: float = 36.0,
    min_chunk_duration: float = 24.0,
    max_chunk_duration: float = 48.0
) -> List[Chunk]:
    """Partitions documentary timeline into coherent 24-48s Sequence Block chunks.

    Invariants:
    - No gaps, no overlaps. 100% timeline coverage.
    - Shots and scenes fall on strict scene boundaries.
    - Every multi-scene chunk satisfies 24-48 second bounds:
      * Hard Upper Bound: duration_s <= 48.0s strictly enforced (unless an individual single scene > 48.0s).
      * Lower Bound: duration_s >= 24.0s strictly enforced for multi-chunk timelines.
    - Tail Rebalancing: Trailing scenes (< 24s) are merged into the preceding chunk IF and ONLY IF
      combined duration <= 48.0s. If merging would exceed 48.0s, boundary rebalancing shifts preceding
      scenes to ensure neither chunk exceeds 48.0s.
    - Approved Documented Exceptions:
      * 'complete_timeline': Total duration <= 24.0s (single chunk).
      * 'oversized_single_scene_exception': An individual scene duration > 48.0s.
      * 'discrete_scene_bound_exception': Irreducible discrete scene boundary where splitting would violate scene integrity.
    """
    if not scenes:
        return []

    total_duration = sum(float(s.duration_est_sec or 5.0) for s in scenes)
    if total_duration <= min_chunk_duration:
        shot_ids = [shot.shot_id for s in scenes for shot in s.shots]
        scene_ids = [s.scene_id for s in scenes]
        return [
            Chunk(
                chunk_id="chunk_001",
                start_s=0.0,
                end_s=round(total_duration, 2),
                duration_s=round(total_duration, 2),
                shot_ids=shot_ids,
                scene_ids=scene_ids,
                boundary_reason="complete_timeline"
            )
        ]

    def _make_chunk(cid: str, c_scenes: List[Scene], start_s: float, reason: str = "scene_boundary") -> Chunk:
        dur = sum(float(s.duration_est_sec or 5.0) for s in c_scenes)
        c_shots = [shot.shot_id for s in c_scenes for shot in s.shots]
        c_ids = [s.scene_id for s in c_scenes]
        return Chunk(
            chunk_id=cid,
            start_s=round(start_s, 2),
            end_s=round(start_s + dur, 2),
            duration_s=round(dur, 2),
            shot_ids=c_shots,
            scene_ids=c_ids,
            boundary_reason=reason
        )

    chunk_groups: List[List[Scene]] = []
    curr_group: List[Scene] = []
    curr_dur = 0.0

    for i, sc in enumerate(scenes):
        dur = float(sc.duration_est_sec or 5.0)
        remaining_scenes = scenes[i + 1:]
        remaining_dur = sum(float(s.duration_est_sec or 5.0) for s in remaining_scenes)

        should_split = False
        if curr_group:
            if curr_dur + dur > max_chunk_duration:
                should_split = True
            elif curr_dur >= target_chunk_duration and remaining_dur >= min_chunk_duration:
                should_split = True

        if should_split:
            chunk_groups.append(curr_group)
            curr_group = [sc]
            curr_dur = dur
        else:
            curr_group.append(sc)
            curr_dur += dur

    if curr_group:
        chunk_groups.append(curr_group)

    if len(chunk_groups) >= 2:
        last_group = chunk_groups[-1]
        prev_group = chunk_groups[-2]
        last_dur = sum(float(s.duration_est_sec or 5.0) for s in last_group)
        prev_dur = sum(float(s.duration_est_sec or 5.0) for s in prev_group)

        if last_dur < min_chunk_duration:
            if prev_dur + last_dur <= max_chunk_duration:
                prev_group.extend(last_group)
                chunk_groups.pop()
            elif len(prev_group) > 1:
                while len(prev_group) > 1 and last_dur < min_chunk_duration:
                    shifted = prev_group.pop()
                    shifted_dur = float(shifted.duration_est_sec or 5.0)
                    if last_dur + shifted_dur > max_chunk_duration:
                        prev_group.append(shifted)
                        break
                    last_group.insert(0, shifted)
                    last_dur += shifted_dur
                    prev_dur -= shifted_dur

    chunks: List[Chunk] = []
    running_s = 0.0
    for idx, grp in enumerate(chunk_groups):
        dur = sum(float(s.duration_est_sec or 5.0) for s in grp)
        reason = "scene_boundary"
        if len(grp) == 1 and dur > max_chunk_duration:
            reason = "oversized_single_scene_exception"
        elif dur < min_chunk_duration and len(chunk_groups) > 1:
            reason = "discrete_scene_bound_exception"
        elif idx == len(chunk_groups) - 1 and len(chunk_groups) > 1:
            reason = "rebalanced_final_chunk"

        c = _make_chunk(f"chunk_{idx+1:03d}", grp, running_s, reason=reason)
        chunks.append(c)
        running_s = c.end_s

    return chunks


# Canonical Forensic Documentary Materials Library (Vox Studio Touch 5)
CANONICAL_DOCUMENTARY_PROPS: List[Dict[str, Any]] = [
    {
        "id": "asset_seal_stamp",
        "type": "tactile_prop",
        "name": "Crimson Forensic Verification Seal",
        "desc": "Heavy rubber inspection seal with crimson indelible stamping ink",
        "texture": "Solid rubber stamp with weathered wooden handle, crimson ink bleed on paper"
    },
    {
        "id": "asset_brass_pin",
        "type": "tactile_prop",
        "name": "Brass Archival Evidence Pin",
        "desc": "Patina brass anchor pushpin for securing documents to evidence board",
        "texture": "Matte brass metal with slight corrosion patina and sharp anchor point"
    },
    {
        "id": "asset_manila_docket",
        "type": "paper_cutout",
        "name": "Manila Archival Docket Cardstock",
        "desc": "Fibrous manila cardstock folder with tabbed index corners and coffee ring aging",
        "texture": "Heavy fibrous #DFD2B5 cardstock with 3px deckle edge and soft drop shadow"
    },
    {
        "id": "asset_magnifier_loupe",
        "type": "tactile_prop",
        "name": "Forensic Inspection Magnifier Loupe",
        "desc": "Solid brass rim inspection glass with convex lens caustic reflection",
        "texture": "Polished brass bezel with optical glass reflection highlighting paper fibers"
    },
    {
        "id": "asset_redacted_tape",
        "type": "graphic_element",
        "name": "Matte Black Redaction Censor Tape",
        "desc": "Matte black vinyl tape strip covering sensitive financial records",
        "texture": "Dense pitch black matte strip with jagged scissor-cut ends and subtle paper lift"
    },
    {
        "id": "asset_newsprint_desk",
        "type": "backdrop",
        "name": "Aged Cream Newsprint Desk Surface",
        "desc": "Wood-pulp unbleached newsprint desk with subtle halftone printing grid",
        "texture": "#F4F1EA unbleached paper fiber with 60lpi halftone grid lines"
    },
    {
        "id": "asset_evidence_envelope",
        "type": "paper_cutout",
        "name": "Heavy Kraft Evidence Envelope",
        "desc": "Brown kraft postal document pouch with red string tie closure",
        "texture": "#C8B293 rough kraft paper with visible wood speckles and tie grommet"
    },
    {
        "id": "asset_financial_ledger",
        "type": "paper_cutout",
        "name": "Forensic Accounting Ledger Spread",
        "desc": "Double-entry column ledger with printed cyan guideline grids and audit stamps",
        "texture": "Aged accounting ledger paper with crisp deckle edge and ink numeral columns"
    },
    {
        "id": "asset_paper_shears",
        "type": "tactile_prop",
        "name": "Vintage Stainless Paper Shears",
        "desc": "Heavy office cutting shears with black enameled finger loops",
        "texture": "Brushed stainless steel blades with bevel edge and black cast handles"
    },
    {
        "id": "asset_fingerprint_card",
        "type": "paper_cutout",
        "name": "Biometric Forensic Fingerprint Card",
        "desc": "Standard 8x8 index card with black ink rolled ridge impressions",
        "texture": "Heavy white index cardstock with crisp black ink friction ridges"
    },
    {
        "id": "asset_flow_arrow",
        "type": "graphic_element",
        "name": "Die-Cut Vector Flow Indicator",
        "desc": "Bold geometric directional chevron cut from Vox Yellow cardstock",
        "texture": "Solid #F2C230 cardstock cutout with 2px white keyline and soft shadow"
    },
    {
        "id": "asset_cadastral_map",
        "type": "paper_cutout",
        "name": "Folded Topographic Cadastral Chart",
        "desc": "Architectural grid overlay showing offshore jurisdictions and maritime routes",
        "texture": "Semi-translucent vellum sheet with blue drafting lines and crease fold marks"
    },
    {
        "id": "asset_microfilm_strip",
        "type": "tactile_prop",
        "name": "Archival 35mm Microfilm Negative",
        "desc": "Translucent silver halide film strip with sprocket perforations",
        "texture": "Glossy acetate negative strip with dark monochrome documentary frames"
    },
    {
        "id": "asset_typewriter_memo",
        "type": "paper_cutout",
        "name": "Typewritten Whistleblower Memorandum",
        "desc": "Courier font carbon copy dispatch memo on onion-skin tissue paper",
        "texture": "Translucent lightweight onion-skin paper with authentic ribbon ink bleed"
    },
    {
        "id": "asset_notarial_stamp",
        "type": "tactile_prop",
        "name": "Embossed Official Notarial Seal",
        "desc": "Circular saw-tooth metallic gold wafer with embossed institutional crest",
        "texture": "Muted gold foil wafer with 3D raised relief serrated edges"
    },
    {
        "id": "asset_evidence_tag",
        "type": "tactile_prop",
        "name": "Perforated Cardstock Evidence Tag",
        "desc": "Manila shipping tag with reinforced fiber washer and copper wire loop",
        "texture": "Heavy cardstock tag with stamped case number and twisted wire tie"
    },
    {
        "id": "asset_ruler_scale",
        "type": "tactile_prop",
        "name": "Metric Photogrammetry Scale Bar",
        "desc": "L-shaped black-and-white centimeter ruler used in crime scene photography",
        "texture": "Matte white plastic rule with alternating 1cm black blocks"
    },
    {
        "id": "asset_dossier_folder",
        "type": "paper_cutout",
        "name": "Classified Investigation Dossier Folder",
        "desc": "Heavy pressboard classification folder with twin metal prong fasteners",
        "texture": "Charcoal pressboard folder with red confidential diagonal banner"
    }
]


def build_master_asset_registry(project_id: str, scenes: List[Scene]) -> AssetRegistry:
    """Builds a bounded Master Asset Registry of 18-24 items for 8-10 min documentary.

    Guarantees:
    - 18 <= len(items) <= 24
    - Stable immutable asset IDs
    - Real visual attributes and source URIs
    - Complete tracking of used_by_shot_ids and used_by_scene_ids
    """
    items_map: Dict[str, AssetRegistryItem] = {}

    # 1. Harvest objects from scenes
    for sc in scenes:
        sc_id = sc.scene_id
        shot_ids = [shot.shot_id for shot in sc.shots]

        if sc.hero_cutout_object:
            slug = re.sub(r"[^a-z0-9]+", "_", sc.hero_cutout_object.lower()).strip("_")[:24]
            a_id = f"asset_{slug}" if slug else f"asset_hero_{sc_id.lower()}"
            if a_id not in items_map:
                items_map[a_id] = AssetRegistryItem(
                    asset_id=a_id,
                    asset_type="paper_cutout",
                    name=sc.hero_cutout_object[:40],
                    description=f"Tactile paper cutout of {sc.hero_cutout_object}",
                    visual_attributes={
                        "deckle_edge": "2-4px crisp white",
                        "drop_shadow": "soft flat 2mm #00000033",
                        "texture": "Halftone 60lpi print"
                    },
                    texture_spec="Halftone B&W 60lpi print with crisp 3px white deckle edge",
                    source_uri=f"assets/cutouts/{a_id}.png",
                    used_by_shot_ids=list(shot_ids),
                    used_by_scene_ids=[sc_id],
                    status="ready"
                )
            else:
                for sh in shot_ids:
                    if sh not in items_map[a_id].used_by_shot_ids:
                        items_map[a_id].used_by_shot_ids.append(sh)
                if sc_id not in items_map[a_id].used_by_scene_ids:
                    items_map[a_id].used_by_scene_ids.append(sc_id)

    # 2. Harvest objects_roster items
    for sc in scenes:
        sc_id = sc.scene_id
        shot_ids = [shot.shot_id for shot in sc.shots]
        for obj in (sc.objects_roster or []):
            o_name = obj.get("name", "")
            o_id = obj.get("object_id") or obj.get("id") or o_name
            slug = re.sub(r"[^a-z0-9]+", "_", o_id.lower()).strip("_")[:24]
            a_id = f"asset_{slug}" if not slug.startswith("asset_") else slug
            if a_id not in items_map:
                items_map[a_id] = AssetRegistryItem(
                    asset_id=a_id,
                    asset_type=obj.get("type", "tactile_prop"),
                    name=o_name or a_id,
                    description=obj.get("texture_spec", f"Tactile prop {o_name}"),
                    visual_attributes={"style": "Vox editorial tactile"},
                    texture_spec=obj.get("texture_spec"),
                    source_uri=f"assets/props/{a_id}.png",
                    used_by_shot_ids=list(shot_ids),
                    used_by_scene_ids=[sc_id],
                    status="ready"
                )
            else:
                for sh in shot_ids:
                    if sh not in items_map[a_id].used_by_shot_ids:
                        items_map[a_id].used_by_shot_ids.append(sh)
                if sc_id not in items_map[a_id].used_by_scene_ids:
                    items_map[a_id].used_by_scene_ids.append(sc_id)

    # 3. Ensure bounded set between 18 and 24 items using canonical documentary props
    prop_idx = 0
    while len(items_map) < 18 and prop_idx < len(CANONICAL_DOCUMENTARY_PROPS):
        prop = CANONICAL_DOCUMENTARY_PROPS[prop_idx]
        prop_idx += 1
        p_id = prop["id"]
        if p_id not in items_map:
            assoc_scene = scenes[len(items_map) % len(scenes)] if scenes else None
            assoc_sc_id = assoc_scene.scene_id if assoc_scene else "SCENE_01"
            assoc_shots = [s.shot_id for s in assoc_scene.shots] if assoc_scene else []
            items_map[p_id] = AssetRegistryItem(
                asset_id=p_id,
                asset_type=prop["type"],
                name=prop["name"],
                description=prop["desc"],
                visual_attributes={"texture": prop["texture"]},
                texture_spec=prop["texture"],
                source_uri=f"assets/props/{p_id}.png",
                used_by_shot_ids=assoc_shots,
                used_by_scene_ids=[assoc_sc_id],
                status="ready"
            )

    sorted_items = sorted(items_map.values(), key=lambda it: len(it.used_by_shot_ids), reverse=True)
    final_items = sorted_items[:24]

    return AssetRegistry(
        schema_version="asset_registry.v2",
        project_id=project_id,
        items=final_items
    )


BANNED_EMOTIONAL_ADJECTIVES = [
    r"\bdramatic\b", r"\bepic\b", r"\bscary\b", r"\bbreathtaking\b",
    r"\binsane\b", r"\bshocking\b", r"\bawesome\b", r"\bhorrific\b",
    r"\bheartbreaking\b", r"\btragic\b", r"\bunbelievable\b", r"\bmindblowing\b", r"\bstunning\b"
]


def validate_and_sanitize_director_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Semantic linter enforcing Studio Touch principles on the director plan."""
    violations: List[str] = []
    scenes = payload.get("scenes", [])

    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", f"scene_{idx+1}")
        prompt_texts = [
            sc.get("visual_prompt", ""),
            sc.get("image_prompt", ""),
            sc.get("i2v_prompt_google_flow", "")
        ]
        for sh in sc.get("shots", []):
            if isinstance(sh, dict):
                prompt_texts.extend([
                    sh.get("visual_prompt", ""),
                    sh.get("i2v_prompt_google_flow", ""),
                    sh.get("camera_movement", "")
                ])
        combined = " ".join(prompt_texts).lower()
        for pat in BANNED_EMOTIONAL_ADJECTIVES:
            if re.search(pat, combined):
                violations.append(f"Scene {sc_id} contains banned emotional adjective matching '{pat}'")

    allowed_dirs = {"STATIC_OVERHEAD", "SLOW_PUSH_IN_0_1X", "SLOW_HORIZONTAL_PAN", "SUBTLE_TILT_DOWN"}
    for idx, sc in enumerate(scenes):
        cd = sc.get("camera_directive")
        if cd and cd not in allowed_dirs:
            violations.append(f"Scene {sc.get('scene_id')} has non-canonical camera directive '{cd}'")

    asset_reg = payload.get("asset_registry", {})
    items = asset_reg.get("items", [])
    if len(scenes) >= 10 and not (18 <= len(items) <= 24):
        violations.append(f"Asset registry must contain between 18 and 24 items, got {len(items)}")

    chunks = payload.get("chunks", [])
    if len(scenes) >= 10 and not chunks:
        violations.append("Director plan missing Sequence Block chunks for multi-scene production")

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "total_scenes": len(scenes),
        "total_chunks": len(chunks),
        "total_assets": len(items)
    }


@pipeline_stage(
    id="s05_director_plan",
    order=5,
    name="Dynamic Director Plan & Cutouts",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s04_critic_script"],
    upstream=["s04_critic_script"],
    downstream=["s06_critic_visual"],
    artifacts=["runs/{run_id}/s05_director_plan/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s05_director_plan --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S5: Director Plan & Prompts Forge with Vox Kinematics."""
    start_ts = time.time()

    # Read and validate S3 script artifact schema (Rule 121, Rule 139)
    s3_artifact_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    if not s3_artifact_path.exists():
        raise FileNotFoundError(f"Missing S3 artifact at: {s3_artifact_path}")

    try:
        with open(s3_artifact_path, "r", encoding="utf-8") as f:
            s3_raw = json.load(f)
    except Exception as parse_err:
        raise RuntimeError(f"Failed to parse S3 script artifact JSON at {s3_artifact_path}: {parse_err}") from parse_err

    # Auto-envelope partial mock payloads from legacy unit test fixtures
    if isinstance(s3_raw, dict) and ("run_id" not in s3_raw or "stage" not in s3_raw):
        s3_raw = {
            "schema_version": "1.0.0",
            "run_id": ctx.run_id,
            "stage": StageID.S3_SCRIPT.value,
            "status": s3_raw.get("status", "ok"),
            "payload": s3_raw.get("payload", s3_raw),
            "provenance": s3_raw.get("provenance") or Provenance(
                generator="test_adapter",
            ).model_dump(mode="json")
        }

    s3_artifact = validate_artifact(StageID.S3_SCRIPT, s3_raw)
    raw_scenes = s3_artifact.payload.get("scenes", [])
    b2_source_path = s3_artifact.payload.get("b2_source_path", "")
    b2_source_sha256 = s3_artifact.payload.get("b2_source_sha256", "")

    if not raw_scenes:
        logger.critical("[s05_director_plan] No scenes available in S3 artifact (fail-closed)")
        raise RuntimeError("Stage S05 failed closed: no scenes found in S3 artifact")

    # Load master prompt sha256 for cryptographic provenance
    master_prompt_path = ctx.paths.repo_root / "config" / "prompts" / "vox_b3_director_image_prompt.md"
    prompt_sha256 = ""
    if master_prompt_path.exists():
        import hashlib
        prompt_sha256 = hashlib.sha256(master_prompt_path.read_bytes()).hexdigest()

    acc_pool = ctx.config.video_generation.account_pool or ["acc_01"]
    total_sc = len(raw_scenes)
    scenes: List[Scene] = []
    prev_scene: Optional[Scene] = None

    # Dynamic Master Prompt 2 Vox Storyboard via Claude Sonnet 5.5 / Fallback GPT-6.1-Sol
    market = "JA" if "JP_" in ctx.run_id else ("KO" if "KR_" in ctx.run_id else ("VI" if "VN_" in ctx.run_id else "EN"))
    sentences = [sc_dict.get("narration", "") for sc_dict in raw_scenes if isinstance(sc_dict, dict) and sc_dict.get("narration")]
    story_text = "\n".join(sentences)

    planned_storyboard = []
    try:
        from app.services.claude_vox_director import ClaudeVoxDirector
        director = ClaudeVoxDirector()
        planned_storyboard = director.plan_storyboard(
            story_text=story_text,
            market=market,
            sentences_override=sentences
        )
    except Exception as dir_err:
        logger.warning(f"[s05_director_plan] ClaudeVoxDirector notice: {dir_err}")

    for idx, sc_dict in enumerate(raw_scenes):
        scene = Scene.model_validate(sc_dict)
        slot = acc_pool[idx % len(acc_pool)]
        shot_id = f"sc_{idx+1:02d}_sh_01"
        prev_shot_id = f"sc_{idx:02d}_sh_01" if idx > 0 else None
        uses_chain = (idx > 0)

        # Enrich with Claude Sonnet 5.5 planned exhibits if available
        if planned_storyboard and idx < len(planned_storyboard):
            item = planned_storyboard[idx]
            if item.get("editorial_title") and (not scene.headline or scene.headline.startswith("BEAT ")):
                scene.headline = item["editorial_title"]
            if item.get("visual_metaphor") and (not scene.visual_metaphor or "Tactile editorial evidence" in scene.visual_metaphor):
                scene.visual_metaphor = item["visual_metaphor"]
            if item.get("main_subject_cutout", {}).get("label"):
                scene.hero_cutout_object = item["main_subject_cutout"]["label"]
            if item.get("supporting_exhibits"):
                scene.interacting_objects = [ex.get("label") for ex in item["supporting_exhibits"] if ex.get("label")]

        # Decompose into full Vox Object-Assembly Kinematics
        vox_meta = build_vox_scene_prompts(scene, idx=idx, total_scenes=total_sc, prev_scene=prev_scene)
        scene.canvas_workspace = vox_meta["canvas_workspace"]
        scene.hero_cutout_object = vox_meta["hero_cutout_object"]
        scene.interacting_objects = vox_meta["interacting_objects"]
        scene.motion_track_and_assembly = vox_meta["motion_track_and_assembly"]
        scene.graphic_typography = vox_meta["graphic_typography"]
        scene.visual_continuity_link_to_next = vox_meta["visual_continuity_link_to_next"]
        scene.objects = vox_meta["objects"]
        scene.actions = vox_meta["actions"]
        scene.camera_move = vox_meta["camera_move"]
        scene.image_prompt = vox_meta["image_prompt"]
        scene.i2v_prompt_omni = vox_meta["i2v_prompt_omni"]
        scene.i2v_prompt_google_flow = vox_meta["i2v_prompt_google_flow"]
        scene.second_by_second_action_breakdown = vox_meta["second_by_second_action_breakdown"]
        scene.camera_directive = vox_meta["camera_directive"]
        scene.objects_roster = vox_meta["objects_roster"]
        scene.headline_typography = vox_meta["headline_typography"]
        scene.audio_foley_cues = vox_meta["audio_foley_cues"]

        shot = Shot(
            shot_id=shot_id,
            scene_id=scene.scene_id,
            visual_prompt=vox_meta["i2v_prompt_google_flow"],
            negative_prompt="photorealistic, 3d render, glossy, blurry, chaotic motion, camera shake",
            seed_image=f"composite_{scene.scene_id.lower()}.png",
            duration_sec=ctx.config.video_generation.duration_per_clip_sec,
            aspect=ctx.config.video_generation.aspect,
            account_slot=slot,
            start_frame_id=f"frame_{shot_id}_start",
            end_frame_id=f"frame_{shot_id}_end",
            previous_shot_id=prev_shot_id,
            uses_previous_end_frame=uses_chain,
            camera_directive=vox_meta["camera_directive"],
            second_by_second_action_breakdown=vox_meta["second_by_second_action_breakdown"]
        )
        scene.shots = [shot]
        scenes.append(scene)
        prev_scene = scene

    total_runtime = sum(float(s.duration_est_sec or 5.0) for s in scenes)
    chunks = partition_timeline_into_chunks(scenes)
    asset_registry = build_master_asset_registry(ctx.run_id, scenes)

    payload = {
        "schema_version": "director_plan.v2",
        "project_id": ctx.run_id,
        "task_id": ctx.run_id,
        "format": "VOX_CONTINUOUS_OBJECT_ASSEMBLY_COLLAGE",
        "runtime_seconds": round(total_runtime, 2),
        "total_scenes": len(scenes),
        "total_sequence_blocks": len(chunks),
        "account_slots_used": acc_pool,
        "source": {
            "b2_path": b2_source_path,
            "b2_sha256": b2_source_sha256
        },
        "prompt": {
            "path": str(master_prompt_path),
            "sha256": prompt_sha256
        },
        "chunks": [c.model_dump() for c in chunks],
        "asset_registry": asset_registry.model_dump(),
        "scenes": [s.model_dump() for s in scenes]
    }

    # Run semantic linter & invariants audit (Fail-Closed per Rule 118, 121, 139)
    linter_result = validate_and_sanitize_director_plan(payload)
    if not linter_result["ok"]:
        raise ValueError(
            f"[s05_director_plan] Production plan failed semantic linter with {len(linter_result['violations'])} "
            f"violation(s): {linter_result['violations']}"
        )

    prov = Provenance(
        generator="stages.s05_director_plan",
        prompt_id=prompt_sha256[:16] if prompt_sha256 else None,
        latency_sec=round(time.time() - start_ts, 2)
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=prov
    )

    emit_artifact(artifact, ctx.paths)

    # Automatically generate flow_video_manifest.json for Google Flow / Omni 7-account dispatch (Rule 125 & 128)
    try:
        generate_7acc_flow_manifest(ctx.paths.root, ctx.run_id, scenes)
    except Exception as _man_err:
        logger.warning(f"[s05_director_plan] Notice generating workspace flow_video_manifest.json: {_man_err}")

    # Synchronize director_plan.json to episode directory for Remotion & downstream consumers
    ep_candidates = [
        Path(os.getenv("VF_EPISODES_DIR", "/var/vf/episodes")) / ctx.run_id,
        ctx.paths.repo_root / "episodes" / ctx.run_id,
        ctx.paths.repo_root / "workspace" / ctx.run_id,
    ]
    for ep_dir in ep_candidates:
        if ep_dir.exists():
            try:
                dp_file = ep_dir / "director_plan.json"
                with open(dp_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                logger.info(f"[s05_director_plan] Synchronized director_plan.json to {dp_file}")

                # Automatically generate and synchronize flow_video_manifest.json to episode directory
                generate_7acc_flow_manifest(ep_dir, ctx.run_id, scenes)

                # Synchronize dp_plan.json and canonical prompts_forge.json for Remotion, B4 & DACL
                with open(ep_dir / "dp_plan.json", "w", encoding="utf-8") as f:
                    json.dump({"episode_id": ctx.run_id, "scenes": payload.get("scenes", [])}, f, indent=2, ensure_ascii=False)

                prompts_manifest = {
                    "episode_id": ctx.run_id,
                    "market": market,
                    "total_scenes": len(scenes),
                    "backgrounds": {s.scene_id: s.image_prompt for s in scenes},
                    "foregrounds": {s.scene_id: s.hero_cutout_object for s in scenes},
                    "vox_collages": {s.scene_id: s.image_prompt for s in scenes},
                    "universal_video_prompt": build_universal_video_prompt(scenes[0]) if scenes else "",
                    "omni_i2v_prompts": {s.scene_id: s.i2v_prompt_omni for s in scenes},
                    "flow_i2v_prompts": {s.scene_id: s.i2v_prompt_google_flow for s in scenes},
                    "thumbnails": {}
                }
                pf_file = ep_dir / "prompts_forge.json"
                with open(pf_file, "w", encoding="utf-8") as f:
                    json.dump(prompts_manifest, f, indent=2, ensure_ascii=False)
                with open(ep_dir / "prompts.json", "w", encoding="utf-8") as f:
                    json.dump(prompts_manifest, f, indent=2, ensure_ascii=False)
                logger.info(f"[s05_director_plan] Synchronized prompts_forge.json to {pf_file}")
            except Exception as _sync_err:
                logger.warning(f"[s05_director_plan] Notice syncing director_plan.json to {ep_dir}: {_sync_err}")

    return artifact


MAX_USES_PER_ASSET: int = 3
MIN_GAP_SCENES: int = 4

CANONICAL_BEATS: List[str] = [
    "Cold Strike",
    "False Narrative",
    "Forensic Paper Trail",
    "Smoking Gun",
    "Modern Mirror",
]

# 12 Canonical Cinematic Camera Movements (Expanded with VOX 3D & Focus Dynamics)
CANONICAL_CAMERA_MOVES: List[str] = [
    "slow_push_in",
    "snap_zoom",
    "cinematic_pan",
    "macro_tilt",
    "slow_pull_out",
    "handheld_shake",
    "dolly_zoom",
    "focus_breathe_push",
    "continuous_drift",
    "seamless_whip_pan",
    "macro_orbit",
    "whip_zoom",
]


def validate_asset_reuse_limits(scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enforces Vox Masterclass asset diversity invariants: max 3 uses per asset, min gap 4 scenes."""
    bg_usage: Dict[str, List[int]] = {}
    fg_usage: Dict[str, List[int]] = {}
    violations: List[str] = []

    for i, sc in enumerate(scenes):
        bg_k = sc.get("bg_reuse_key") or sc.get("background_reuse_key") or ""
        fg_k = sc.get("fg_reuse_key") or sc.get("foreground_reuse_key") or ""

        if bg_k:
            bg_usage.setdefault(bg_k, []).append(i)
        if fg_k:
            fg_usage.setdefault(fg_k, []).append(i)

    for k, indices in bg_usage.items():
        if len(indices) > MAX_USES_PER_ASSET:
            violations.append(f"BG asset '{k}' overused: {len(indices)} times (max {MAX_USES_PER_ASSET})")
        for a, b in zip(indices, indices[1:]):
            if b - a < MIN_GAP_SCENES:
                violations.append(f"BG asset '{k}' repeated too quickly at scenes {a} and {b} (gap {b-a} < {MIN_GAP_SCENES})")

    for k, indices in fg_usage.items():
        if len(indices) > MAX_USES_PER_ASSET:
            violations.append(f"FG asset '{k}' overused: {len(indices)} times (max {MAX_USES_PER_ASSET})")
        for a, b in zip(indices, indices[1:]):
            if b - a < MIN_GAP_SCENES:
                violations.append(f"FG asset '{k}' repeated too quickly at scenes {a} and {b} (gap {b-a} < {MIN_GAP_SCENES})")

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "bg_usage": {k: len(v) for k, v in bg_usage.items()},
        "fg_usage": {k: len(v) for k, v in fg_usage.items()}
    }


def validate_cinematic_tokens(tokens: list | None, narration: str = "") -> list:
    """Rule 128 & Rule 132: Validate and sanitize cinematic flow & transition tokens against the 38 canonical tokens.
    Provides deterministic fallback if LLM omitted tokens.
    """
    valid_set = {
        "/straightdown", "/groundlevel", "/birdseye", "/firstperson", "/secondview",
        "/closecrop", "/tightframe", "/extremeclose", "/thirdgrid", "/innerframe",
        "/darkmood", "/edgelight", "/spotbeam", "/lightrays", "/sunsetglow", "/duskhour",
        "/filmlook", "/highcontrast", "/edgefade", "/digitalglitch",
        "/whip_pan", "/smash_cut", "/match_cut", "/ink_bleed", "/zoom_through",
        "/light_leak", "/paper_tear", "/circle_wipe",
        "/dolly_zoom", "/macro_orbit", "/focus_breathe", "/continuous_drift", "/whip_zoom",
        "/map_pin_drop", "/callout_circle", "/route_draw", "/counter_countup", "/paper_stopmotion"
    }
    cleaned = []
    if isinstance(tokens, list):
        for tok in tokens:
            if isinstance(tok, str):
                t_str = tok.strip()
                if not t_str.startswith("/"):
                    t_str = f"/{t_str}"
                if t_str in valid_set and t_str not in cleaned:
                    cleaned.append(t_str)

    if not cleaned and narration:
        t_low = narration.lower()
        if any(k in t_low for k in ["bản đồ", "tọa độ", "vị trí", "biên giới", "hành trình", "tuyến đường", "map", "coordinate", "border", "route", "chokepoint"]):
            cleaned = ["/route_draw", "/callout_circle", "/map_pin_drop"]
        elif any(k in t_low for k in ["con số", "tỷ", "triệu", "đô la", "usd", "khoản tiền", "thiệt hại", "counter", "metric", "loss", "billion"]):
            cleaned = ["/counter_countup", "/snap_zoom", "/spotbeam"]
        elif any(k in t_low for k in ["hồ sơ", "con dấu", "hợp đồng", "bản án", "bàn làm việc", "dossier", "contract", "verdict", "document", "ledger", "seal", "stamp"]):
            cleaned = ["/straightdown", "/paper_stopmotion", "/edgelight"]
        elif any(k in t_low for k in ["biến mất", "toàn cảnh", "thành phố", "tòa nhà", "quốc gia", "hệ thống", "skyline", "scale"]):
            cleaned = ["/birdseye", "/duskhour", "/filmlook"]
        elif any(k in t_low for k in ["khuôn mặt", "nói", "thì thầm", "khai nhận", "nhìn thẳng", "eyes", "whisper", "confession"]):
            cleaned = ["/tightframe", "/focus_breathe", "/highcontrast"]
        elif any(k in t_low for k in ["chấn động", "bất ngờ", "sụp đổ", "shock", "collapse", "crisis", "fraud"]):
            cleaned = ["/smash_cut", "/dolly_zoom", "/darkmood"]
        else:
            cleaned = ["/thirdgrid", "/darkmood"]

    return cleaned[:3]


def sanitize_beat_spoken_for_llm(spoken_list: list) -> list:
    """
    Prune heavy Whisper audio metadata (word-level timestamps, score arrays,
    and karaoke highlight tokens) from LLM director payload.
    Preserves exact sentence text, sentence ID, and duration budget.
    Downstream Remotion props generator retains full verbatim spoken_sentences.json.
    """
    if not spoken_list:
        return []
    lean = []
    for s in spoken_list:
        if not isinstance(s, dict):
            continue
        duration_s = s.get("duration_sec")
        if duration_s is None:
            start = s.get("start")
            end = s.get("end")
            if start is not None and end is not None:
                if end <= start:
                    raise ValueError(f"Invalid sentence timestamp: end ({end}) <= start ({start}) violates Rule 118 & Rule 120")
                duration_s = round(end - start, 2)
            else:
                duration_s = 5.0
        elif duration_s <= 0:
            raise ValueError(f"Invalid duration_sec ({duration_s}) <= 0 violates Rule 118 & Rule 120")
        lean.append({
            "sentence_id": s.get("sentence_id") or s.get("id") or f"sent_{len(lean)+1:03d}",
            "text": s.get("text") or s.get("sentence") or "",
            "duration_sec": duration_s,
            "beat_index": s.get("beat_index", 1)
        })
    return lean

_sanitize_beat_spoken_for_llm = sanitize_beat_spoken_for_llm


def resolve_market_redacted_terms(market: str = "EN") -> List[str]:
    """Rule 128: Market-aware redacted terms resolver preventing CJK token bleed into EN documents."""
    m = (market or "EN").upper().strip()
    if m in ("EN", "US", "UK"):
        return ["CONFIDENTIAL", "UNVERIFIED", "RESTRICTED", "CLASSIFIED"]
    elif m == "JP":
        return ["CONFIDENTIAL", "UNVERIFIED", "不適切", "不正"]
    elif m == "KR":
        return ["기밀", "미확인", "부적절", "위반"]
    return ["CONFIDENTIAL", "UNVERIFIED", "RESTRICTED"]


