#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s07_image_gen.py — Stage S7: Composite Seed Image Generation (AVF-STAB-001).

Implements Stage Shape Standard. Generates or verifies authentic composite seed images for I2V.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import GateError, compute_file_sha256, emit_artifact
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger("s07_image_gen")

STAGE: StageID = StageID.S7_IMAGE_GEN


@pipeline_stage(
    id="s07_image_gen",
    order=7,
    name="Gemini Seed Image Generation",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s06_critic_visual"],
    upstream=["s06_critic_visual"],
    downstream=["s08_video_gen"],
    artifacts=["runs/{run_id}/composite_seeds/*.png"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s07_image_gen --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S7: Composite Image Generation."""
    start_ts = time.time()

    # Read S5 Director Plan
    s5_path = ctx.paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    s5_data = json.loads(s5_path.read_text(encoding="utf-8"))
    scenes = s5_data.get("payload", {}).get("scenes", [])

    is_story = bool(ctx.preset and getattr(ctx.preset, "name", "") in ("story_forensic", "vox_narrative"))
    style_prefix = ""
    if is_story:
        prefix_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s07_image_style_prefix.md"
        if prefix_file.exists():
            style_prefix = prefix_file.read_text(encoding="utf-8").strip()

    # Ensure bulk_image_prompts.txt is always emitted for Human Gate 2 / Gate 3
    bulk_prompts_file = ctx.paths.root / "bulk_image_prompts.txt"
    bulk_lines = [f"# Bulk Image Prompts for Run: {ctx.run_id}", ""]
    for sc in scenes:
        sc_id = sc.get("scene_id", "SCENE_01")
        headline = sc.get("headline", "")
        p_text = sc.get("image_prompt") or sc.get("visual_prompt") or sc.get("narration", "")
        bulk_lines.append(f"=== {sc_id} // {headline} ===")
        bulk_lines.append(f"Target: composite_{sc_id.lower()}.png")
        bulk_lines.append(f"Narration: {sc.get('narration', '')}")
        bulk_lines.append(f"Prompt:\n{p_text.strip()}")
        bulk_lines.append("")
    bulk_prompts_file.write_text("\n".join(bulk_lines), encoding="utf-8")
    if ctx.paths.composite_seeds_dir.exists():
        (ctx.paths.composite_seeds_dir / "prompts.txt").write_text("\n".join(bulk_lines), encoding="utf-8")

    images_generated: List[Dict[str, Any]] = []
    missing_scenes: List[str] = []
    is_hermetic_test = bool(ctx.dry_run or (ctx.config and ctx.config.name == "e2e_min"))

    for sc in scenes:
        sc_id = sc.get("scene_id", "SCENE_01")
        target_img = ctx.paths.seed_image_path(sc_id)

        # 1. Check if seed already exists or resolve across candidate locations
        if not target_img.exists() or ctx.force:
            from app.services.master_scene_sheet import resolve_scene_image_path

            brain_browser_dir = Path.home() / ".gemini" / "antigravity" / "brain" / "browser_assets" / ctx.run_id
            fallback_dirs = [
                ctx.paths.root / "images",
                ctx.paths.root / "assets",
            ]
            if brain_browser_dir.exists():
                fallback_dirs.append(brain_browser_dir)

            first_shot = sc.get("shots", [{}])[0] if isinstance(sc.get("shots"), list) and len(sc.get("shots")) > 0 else {}
            explicit_target = (
                sc.get("image_path")
                or sc.get("seed_image")
                or sc.get("file_path")
                or first_shot.get("seed_image")
                or first_shot.get("image_path")
            )
            found = resolve_scene_image_path(
                scene_id=sc_id,
                image_dir=ctx.paths.composite_seeds_dir,
                fallback_dirs=fallback_dirs,
                explicit_path=explicit_target,
            )
            if found and found.exists() and found.stat().st_size > 1024:
                if found.resolve() != target_img.resolve():
                    import shutil
                    shutil.copy2(str(found), str(target_img))
            elif not target_img.exists():
                if is_hermetic_test:
                    # Create editorial placeholder frame via PIL ONLY for hermetic unit tests
                    try:
                        from PIL import Image, ImageDraw
                        bg_color = "#F4F1EA"
                        border_color = "#D62E1F" if is_story else "#F2C230"
                        img = Image.new("RGB", (1920, 1080), color=bg_color)
                        draw = ImageDraw.Draw(img)
                        draw.rectangle([100, 100, 1820, 980], outline=border_color, width=4)
                        draw.text((150, 150), f"{sc_id} // {sc.get('headline', 'EDITORIAL FOCUS')}", fill="#1B2B4A")
                        draw.text((150, 220), sc.get("narration", "")[:120], fill="#334155")
                        img.save(str(target_img), format="PNG")
                    except Exception:
                        target_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)
                else:
                    # In Production: ZERO-MOCK MANDATE (Rule 118 & 121)
                    missing_scenes.append(sc_id)

        if target_img.exists():
            sha = compute_file_sha256(target_img)
            images_generated.append({
                "scene_id": sc_id,
                "file_path": str(target_img),
                "size_bytes": target_img.stat().st_size,
                "sha256": sha
            })

    if missing_scenes:
        raise GateError(
            STAGE,
            f"Missing authentic composite seed images for {len(missing_scenes)} scene(s): {missing_scenes}. "
            f"Found {len(images_generated)}/{len(scenes)} valid images. Refusing to proceed with missing authentic images (Rule 118 & 121): "
            f"authentic illustrations required in production. Prompts saved to '{bulk_prompts_file}'. "
            f"Please generate authentic images via Antigravity UI / Skill /vf-image-gen and place them in "
            f"'{ctx.paths.composite_seeds_dir}' before resuming.",
            details={"missing_scenes": missing_scenes, "prompts_file": str(bulk_prompts_file)}
        )

    # Refresh Master Scene package with authentic composite seed images (Rule 121 & 140)
    master_sheet_manifest = None
    try:
        from app.services.master_scene_sheet import generate_master_scene_package
        master_sheet_manifest = generate_master_scene_package(
            ctx, scenes=scenes, payload=s5_data.get("payload", {}), image_mode=True
        )
        # Synchronize master_sheets to canonical episode directory if separate
        import os
        import shutil
        ms_src = ctx.paths.root / "master_sheets"
        if ms_src.exists():
            ep_candidates = [
                Path(os.getenv("VF_EPISODES_DIR", "/var/vf/episodes")) / ctx.run_id,
                ctx.paths.repo_root / "episodes" / ctx.run_id,
            ]
            for ep_dir in ep_candidates:
                if ep_dir.exists() and ep_dir.resolve() != ctx.paths.root.resolve():
                    shutil.copytree(str(ms_src), str(ep_dir / "master_sheets"), dirs_exist_ok=True)
    except Exception as _ms_err:
        logger.debug(f"[s07_image_gen] Notice refreshing master_scene_package: {_ms_err}")

    payload = {
        "task_id": ctx.run_id,
        "total_images": len(images_generated),
        "composite_seeds_dir": str(ctx.paths.composite_seeds_dir),
        "aspect_ratio": "16:9",
        "style_prefix": style_prefix if is_story else None,
        "images": images_generated,
        "master_sheets": {
            "dir": str(ctx.paths.root / "master_sheets"),
            "manifest": master_sheet_manifest,
        }
    }

    prov = Provenance(
        generator="stages.s07_image_gen",
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
