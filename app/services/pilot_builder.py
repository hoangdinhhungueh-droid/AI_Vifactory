#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/pilot_builder.py — 30-Second Demo / Pilot Video Generator (AVF-STAB-001).

Implements Gate 4 30-second Demo/Pilot Generation & Multimodal Visual Critic Inspection.
Slices Beat 1 audio & subtitles, assembles pilot_30s.mp4, extracts 16-frame contact sheet,
and evaluates visual quality with Claude Opus 5.5 + GPT-6-Astra (Skill: /vf-visual-critic).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import RunContext
from core.contracts.stages import StageID
from vox.assemble import assemble_final_video
from vox.ffmpeg_utils import get_ffmpeg_binary

logger = logging.getLogger("pilot_builder")


def build_and_evaluate_pilot(
    ctx: RunContext,
    target_duration_sec: float = 30.0,
) -> Dict[str, Any]:
    """Generates a 30-second Beat 1 Pilot video, extracts 16-frame contact sheet,
    and runs the Multimodal Visual Critic Council evaluation.
    """
    start_ts = time.time()
    ffmpeg_bin = get_ffmpeg_binary()
    fps = ctx.config.render.fps if (ctx.config and hasattr(ctx.config, "render")) else 30

    print("\n" + "=" * 75)
    print("🎬 GENERATING 30-SECOND DEMO / PILOT VIDEO (BEAT 1 HOOK)")
    print("=" * 75)

    # 1. Load S05 Director Plan
    s5_path = ctx.paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    if not s5_path.exists():
        raise RuntimeError(
            f"Director plan artifact S05 missing at '{s5_path}'. "
            f"Run stages S01-S05 before generating pilot video."
        )

    s5_data = json.loads(s5_path.read_text(encoding="utf-8"))
    scenes = s5_data.get("payload", {}).get("scenes", [])
    if not scenes:
        raise RuntimeError(f"No scenes declared in S05 director plan: {s5_path}")

    # 2. Verify or Generate Voice Audio (S09)
    audio_path = ctx.paths.audio_dir / "voice_narration.mp3"
    s9_path = ctx.paths.artifact_file(StageID.S9_VOICE_TTS.value)
    if not audio_path.exists() or not s9_path.exists():
        print("🔊 Voice narration not found, executing Stage S09 Voice TTS...")
        import importlib
        s9_mod = importlib.import_module("stages.s09_voice_tts")
        s9_mod.run(ctx)

    if not audio_path.exists() or audio_path.stat().st_size < 100:
        raise RuntimeError(f"Voice narration audio missing at '{audio_path}' after S09 execution.")

    # 3. Select Beat 1 Scenes (approx target_duration_sec, minimum 2 scenes)
    pilot_scenes: List[Dict[str, Any]] = []
    accum_dur = 0.0
    for sc in scenes:
        d = float(sc.get("duration_est_sec") or 5.5)
        pilot_scenes.append(sc)
        accum_dur += d
        if accum_dur >= target_duration_sec and len(pilot_scenes) >= 2:
            break

    target_dur = round(accum_dur, 2)
    print(f"📋 Selected {len(pilot_scenes)} scenes for Beat 1 pilot ({target_dur}s target runtime).")

    # 4. Verify / Generate Video Clips for Beat 1
    pilot_clip_paths: List[Path] = []
    for sc in pilot_scenes:
        sc_id = sc.get("scene_id", "SCENE_01")
        target_clip = ctx.paths.video_clip_path(sc_id)
        sc_dur = float(sc.get("duration_est_sec") or 5.5)

        if not target_clip.exists() or target_clip.stat().st_size < 1000:
            # Check video_clips or legacy candidates before raising error
            legacy_cands = [
                ctx.paths.root / "video_clips" / f"clip_{sc_id.lower()}.mp4",
                ctx.paths.root / f"clip_{sc_id.lower()}.mp4",
                ctx.paths.root / "blocks" / sc.get("sequence_block", "block_1_act_i").lower() / "videos" / f"clip_{sc_id.lower()}.mp4"
            ]
            found = next((p for p in legacy_cands if p.exists() and p.stat().st_size > 1000), None)
            if found:
                import shutil
                shutil.copy2(str(found), str(target_clip))

        if not target_clip.exists() or target_clip.stat().st_size < 1000:
            if ctx.dry_run or (ctx.config and ctx.config.name == "e2e_min"):
                cmd = [
                    ffmpeg_bin, "-y", "-f", "lavfi",
                    "-i", f"testsrc=duration={sc_dur}:size=1920x1080:rate={fps}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(target_clip)
                ]
                subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            else:
                # Rule 118, 121 & Anti-Destructive Iron Law:
                # ZERO-MOCK MANDATE: Static image zoompan shortcuts are strictly eliminated.
                raise RuntimeError(
                    f"[pilot_builder] Authentic video clip missing for scene '{sc_id}' at '{target_clip}'. "
                    f"FFmpeg static image shortcuts (zoompan) are strictly forbidden per Rule 118 & 121. "
                    f"Please generate video clips first via: "
                    f"'python scripts/flow_video_dispatcher.py --episode {ctx.run_id} --model omni'."
                )

        pilot_clip_paths.append(target_clip)

    # 5. Slice Audio and Subtitles for Beat 1
    pilot_dir = ctx.paths.root / "pilot_30s"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    pilot_audio = pilot_dir / "pilot_audio.mp3"
    pilot_sub = pilot_dir / "pilot_subtitles.ass"
    pilot_video = pilot_dir / "pilot_30s.mp4"

    print(f"✂️ Slicing voice narration to {target_dur}s...")
    cmd_audio = [
        ffmpeg_bin, "-y",
        "-i", str(audio_path),
        "-t", str(target_dur),
        "-c:a", "libmp3lame",
        str(pilot_audio)
    ]
    subprocess.run(cmd_audio, capture_output=True, check=True, timeout=20)

    # Subtitles: copy or generate ASS
    sub_src = ctx.paths.audio_dir / "subtitles.ass"
    if not sub_src.exists():
        sub_src = ctx.paths.root / "subtitles.ass"
    if sub_src.exists():
        pilot_sub.write_text(sub_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        pilot_sub.write_text(
            "[Script Info]\nTitle: Pilot\nScriptType: v4.00+\n[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
            encoding="utf-8"
        )

    # 6. Assemble Pilot Master MP4
    print(f"🔨 Assembling pilot video: {pilot_video.name} ({len(pilot_clip_paths)} clips)...")
    assemble_final_video(pilot_clip_paths, pilot_audio, pilot_sub, pilot_video)

    if not pilot_video.exists() or pilot_video.stat().st_size < 1000:
        raise RuntimeError(f"Pilot video assembly failed: {pilot_video}")

    # Copy to root pilot_30s.mp4 for convenience
    root_pilot = ctx.paths.root / "pilot_30s.mp4"
    if root_pilot.resolve() != pilot_video.resolve():
        import shutil
        shutil.copy2(str(pilot_video), str(root_pilot))

    # 7. Extract 16-Frame Contact Sheet (4x4 Grid)
    print("📸 Extracting 16-frame contact sheet for Visual Critic Council...")
    from scripts.visual_critic_council import (
        evaluate_with_council,
        extract_frames_and_build_contact_sheet,
    )
    cs_dir = ctx.paths.root / "visual_audit"
    cs_path = extract_frames_and_build_contact_sheet(
        video_path=pilot_video,
        out_dir=cs_dir,
        num_frames=16,
        duration_sec=target_dur,
        output_name="contact_sheet_30s.jpg"
    )

    # 8. Evaluate with Visual Critic Council (Claude Opus 5.5 + GPT-6-Astra)
    eval_result: Dict[str, Any] = {}
    if not ctx.dry_run:
        print("🧠 Invoking Visual Critic Council (Claude Opus 5.5 + GPT-6-Astra)...")
        try:
            eval_result = evaluate_with_council(
                contact_sheet_path=cs_path,
                episode_id=ctx.run_id,
                duration_sec=target_dur,
                scope_desc=f"30-second Beat 1 pilot ({target_dur:.1f}s runtime)"
            )
        except Exception as eval_err:
            logger.warning(f"Visual Critic Council API error: {eval_err}")
            # Rule 118 & Truthful Reporting Iron Law: Never fabricate mock passing scores when evaluation fails
            eval_result = {
                "verdict": "UNVERIFIED",
                "overall_score": None,
                "error": str(eval_err),
                "note": f"Visual Critic Council API call failed: {eval_err}. Transparent reporting per Truthful Reporting Iron Law.",
                "axis_scores": None
            }
    else:
        print("⚡ [DRY-RUN] Visual Critic Council evaluation simulated (Score: 9.2 / 10).")
        eval_result = {
            "verdict": "PASS",
            "overall_score": 9.2,
            "evaluator": "dry_run",
            "axis_scores": {
                "cinematic_motion_physics": 9.2,
                "tactile_paper_aesthetics": 9.3,
                "editing_pacing": 9.1,
                "typography_data_clarity": 9.2
            }
        }

    elapsed = round(time.time() - start_ts, 1)
    sz_mb = round(pilot_video.stat().st_size / (1024 * 1024), 2)
    print(f"✅ Pilot video assembled in {elapsed}s ({sz_mb} MB) -> {pilot_video}")

    manifest_data = {
        "run_id": ctx.run_id,
        "pilot_video": str(pilot_video),
        "contact_sheet": str(cs_path),
        "target_duration_sec": target_dur,
        "total_scenes": len(pilot_scenes),
        "size_bytes": pilot_video.stat().st_size,
        "size_mb": sz_mb,
        "evaluation": eval_result,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    manifest_file = ctx.paths.root / "pilot_manifest.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_data
