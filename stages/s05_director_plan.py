#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s05_director_plan.py — Stage S5: Vox-Style Director Plan & Prompts (AVF-STAB-001).

Implements Stage Shape Standard. Encodes Prompt 2 (Director & Image) and Prompt 3 (Universal Video Prompt).
"""

from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Dict, Any, List

from core.contracts.stages import StageID, StageArtifact, Provenance, Scene, Shot
from core.config import RunContext
from core.gates import require_input, emit_artifact

STAGE: StageID = StageID.S5_DIRECTOR_PLAN


def build_universal_video_prompt(scene: Scene) -> str:
    """Encodes Prompt 3 from Made by AI Playbook: 0-7s layer-by-layer, 7-10s hold micro-motion."""
    hero_obj = scene.visual_metaphor or "Tactile paper cutout elements"
    color = scene.color_accent or "Vox Yellow #F2C230 and Navy #1B2B4A"
    headline = scene.headline or "EDITORIAL FOCUS"

    parts = [
        "Editorial paper cutout animation in Vox documentary style.",
        f"Animate completed composition: {hero_obj} on Cream Paper #F4F1EA background.",
        f"0.0-2.0s: Tactile entry of bold geometric paper shapes and headline '{headline}'.",
        f"2.0-7.0s: Main cutout elements assemble smoothly with layered drop shadows and deckle white edges.",
        "7.0-10.0s: Spatial anchor locked, subtle micro-shadow breathing <= 2px, zero drift.",
        "Camera: Completely static top-down desk view, crisp focus, no 3D pan or tilt.",
        f"Color Palette: {color} on muted paper texture."
    ]
    return " ".join(parts)


def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S5: Director Plan & Prompts Forge."""
    start_ts = time.time()
    
    # Read S3 script artifact directly to retrieve scenes
    s3_artifact_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    if not s3_artifact_path.exists():
        raise FileNotFoundError(f"Missing S3 artifact at: {s3_artifact_path}")
    
    s3_data = json.loads(s3_artifact_path.read_text(encoding="utf-8"))
    raw_scenes = s3_data.get("payload", {}).get("scenes", [])

    acc_pool = ctx.config.video_generation.account_pool or ["acc_01"]
    scenes: List[Scene] = []

    for idx, sc_dict in enumerate(raw_scenes):
        scene = Scene.model_validate(sc_dict)
        shot_id = f"sc_{idx+1:02d}_sh_01"
        uv_prompt = build_universal_video_prompt(scene)
        slot = acc_pool[idx % len(acc_pool)]

        shot = Shot(
            shot_id=shot_id,
            scene_id=scene.scene_id,
            visual_prompt=uv_prompt,
            negative_prompt="photorealistic, 3d render, glossy, blurry, chaotic motion, camera shake",
            seed_image=f"composite_{scene.scene_id.lower()}.png",
            duration_sec=ctx.config.video_generation.duration_per_clip_sec,
            aspect=ctx.config.video_generation.aspect,
            account_slot=slot
        )
        scene.shots = [shot]
        scenes.append(scene)

    payload = {
        "task_id": ctx.run_id,
        "total_scenes": len(scenes),
        "account_slots_used": acc_pool,
        "scenes": [s.model_dump() for s in scenes]
    }

    prov = Provenance(
        generator="stages.s05_director_plan",
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
    return artifact
