#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s10_render.py — Stage S10: Remotion Post-Production Render (AVF-STAB-001).

Implements Stage Shape Standard. Assembles RemotionRenderProps and renders final.mp4.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

from core.config import RunContext
from core.contracts.render_props import KaraokeWord, RemotionRenderProps, SceneRenderProp
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import compute_file_sha256, emit_artifact
from tools.codemap.runtime import pipeline_stage
from vox.assemble import assemble_final_video


class MissingSubtitlesError(RuntimeError):
    """Raised when subtitles.ass is missing for final assembly."""
    pass


class MissingClipsError(RuntimeError):
    """Raised when video clips are missing or invalid for final assembly."""
    pass


class MissingAudioError(RuntimeError):
    """Raised when audio narration track is missing or invalid."""
    pass


STAGE: StageID = StageID.S10_RENDER


@pipeline_stage(
    id="s10_render",
    order=10,
    name="Vox Tactile Compositor Final Assembly",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s08_video_gen", "stage:s09_voice_tts"],
    upstream=["s08_video_gen", "s09_voice_tts"],
    downstream=["s11_qc"],
    artifacts=["runs/{run_id}/10_render/final.mp4"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s10_render --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S10: Remotion Master Video Render."""
    start_ts = time.time()

    # 1. Read S8 (Video clips) & S9 (Voice audio)
    s8_path = ctx.paths.artifact_file(StageID.S8_VIDEO_GEN.value)
    s9_path = ctx.paths.artifact_file(StageID.S9_VOICE_TTS.value)

    s8_data = json.loads(s8_path.read_text(encoding="utf-8"))
    s9_data = json.loads(s9_path.read_text(encoding="utf-8"))

    clips = s8_data.get("payload", {}).get("clips", [])
    audio_file = s9_data.get("payload", {}).get("audio_file", "")
    subtitles = s9_data.get("payload", {}).get("subtitles", [])

    fps = ctx.config.render.fps
    scene_props: List[SceneRenderProp] = []
    total_frames = 0

    for cl in clips:
        sc_id = cl.get("scene_id", "SCENE_01")
        dur_sec = cl.get("duration_sec", 6.0)
        frames = int(dur_sec * fps)
        total_frames += frames

        # Map subtitles for this scene
        sc_words = [KaraokeWord.model_validate(w) for w in subtitles[:20]]

        scene_props.append(SceneRenderProp(
            scene_id=sc_id,
            duration_in_frames=frames,
            video_clip_path=cl.get("file_path", ""),
            audio_path=audio_file,
            subtitles=sc_words
        ))

    # Assemble RemotionRenderProps
    render_props = RemotionRenderProps(
        episode_id=ctx.run_id,
        title=f"Episode {ctx.run_id}",
        fps=fps,
        width=ctx.config.render.width,
        height=ctx.config.render.height,
        duration_in_frames=max(total_frames, 30),
        scenes=scene_props,
        bgm_volume=ctx.config.render.bgm_volume
    )

    # Save props file for Remotion
    props_file = ctx.paths.root / "remotion_props.json"
    props_file.write_text(render_props.model_dump_json(indent=2), encoding="utf-8")

    # Render target final.mp4
    final_mp4 = ctx.paths.final_render_dir / "final.mp4"

    is_valid_existing = False
    if final_mp4.exists() and not ctx.force:
        if final_mp4.stat().st_size >= 1000:
            is_valid_existing = True

    if not is_valid_existing:
        if not clips:
            raise MissingClipsError("Stage S10 requires declared S8 video clips, but clips list is empty")

        clip_paths: List[Path] = []
        invalid_clip_indices: List[int] = []
        for idx, cl in enumerate(clips):
            fp = cl.get("file_path")
            if not fp or not Path(fp).exists() or Path(fp).stat().st_size <= 100:
                invalid_clip_indices.append(idx)
            else:
                clip_paths.append(Path(fp))

        if invalid_clip_indices:
            raise MissingClipsError(
                f"Stage S10 requires all declared S8 video clips to be valid and >100B. "
                f"Found {len(invalid_clip_indices)} invalid clip(s) at index/indices {invalid_clip_indices} "
                f"(declared: {len(clips)}, valid: {len(clip_paths)})"
            )

        if not audio_file or not Path(audio_file).exists() or Path(audio_file).stat().st_size < 100:
            raise MissingAudioError(f"Stage S10 requires valid audio narration file from S9, got '{audio_file}'")

        # Source subtitles path from S9 artifact payload contract (Rule 132), with root fallback
        s9_sub_path = s9_data.get("payload", {}).get("subtitles_file") or s9_data.get("payload", {}).get("ass_file")
        if s9_sub_path and Path(s9_sub_path).exists():
            ass_file = Path(s9_sub_path)
        else:
            ass_file = ctx.paths.root / "subtitles.ass"

        if not ass_file.exists() or ass_file.stat().st_size == 0:
            raise MissingSubtitlesError(f"Stage S10 requires valid subtitles file at '{ass_file}'")

        # Delegate strictly to canonical vox assembly engine with two-pass loudnorm (Rule 125 & 139)
        assemble_final_video(clip_paths, Path(audio_file), ass_file, final_mp4)
        if not final_mp4.exists() or final_mp4.stat().st_size < 1000:
            raise RuntimeError(f"assemble_final_video failed to produce master MP4 at {final_mp4}")

    sz = final_mp4.stat().st_size if final_mp4.exists() else 0
    sha = compute_file_sha256(final_mp4) if final_mp4.exists() else "none"

    payload = {
        "task_id": ctx.run_id,
        "final_video_path": str(final_mp4),
        "remotion_props_file": str(props_file),
        "total_scenes_rendered": len(scene_props),
        "duration_in_frames": render_props.duration_in_frames,
        "fps": fps,
        "size_bytes": sz,
        "sha256": sha
    }

    prov = Provenance(
        generator="stages.s10_render",
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
