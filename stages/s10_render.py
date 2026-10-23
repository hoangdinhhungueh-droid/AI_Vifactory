#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s10_render.py — Stage S10: Remotion Post-Production Render (AVF-STAB-001).

Implements Stage Shape Standard. Assembles RemotionRenderProps and renders final.mp4.
"""

from __future__ import annotations

import json
import logging
import math
import subprocess
import time
from pathlib import Path
from typing import List

logger = logging.getLogger("s10_render")

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
    """Executes Stage S10: Remotion Master Video Render with fail-closed failure invalidation."""
    start_ts = time.time()
    target_art_file = ctx.paths.artifact_file(STAGE.value) if hasattr(ctx, "paths") and hasattr(ctx.paths, "artifact_file") else None
    try:
        return _run_stage_s10_internal(ctx, start_ts)
    except Exception as render_err:
        if target_art_file and target_art_file.exists():
            try:
                target_art_file.unlink()
            except OSError as unlink_err:
                logger.debug(f"[s10_render] Failure artifact unlink notice: {unlink_err}")
            if target_art_file.exists():
                try:
                    target_art_file.write_text(json.dumps({"status": "failed", "stage": STAGE.value, "error": str(render_err)}), encoding="utf-8")
                except OSError as write_err:
                    logger.debug(f"[s10_render] Failure artifact overwrite notice: {write_err}")
                if target_art_file.exists():
                    raise RuntimeError(f"Stage S10 fail-closed: Unable to unlink or invalidate stale artifact at '{target_art_file}'") from render_err
        raise

def _run_stage_s10_internal(ctx: RunContext, start_ts: float) -> StageArtifact:

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
        frames = int(round(dur_sec * fps))
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
        try:
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(final_mp4)
            ]
            probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True, timeout=30.0)
            probe_data = json.loads(probe_res.stdout)
            streams = probe_data.get("streams", [])
            has_video = any(s.get("codec_type") == "video" for s in streams)
            has_audio = any(s.get("codec_type") == "audio" for s in streams)
            dur_str = probe_data.get("format", {}).get("duration", "0")
            dur = float(dur_str)
            if has_video and has_audio and dur > 0.0:
                is_valid_existing = True
        except Exception as _probe_err:
            logger.debug(f"[s10_render] Existing final.mp4 probe invalid or failed ({_probe_err}), will render fresh output")
            is_valid_existing = False

    if not is_valid_existing:
        if not clips:
            raise MissingClipsError("Stage S10 requires declared S8 video clips, but clips list is empty")

        clip_paths: List[Path] = []
        invalid_clip_indices: List[int] = []
        from stages.s08_video_gen import validate_video_motion_temporal_delta, StaticFreezeFrameError

        for idx, cl in enumerate(clips):
            fp = cl.get("file_path")
            if not fp or not Path(fp).exists() or Path(fp).stat().st_size <= 100:
                invalid_clip_indices.append(idx)
            else:
                p = Path(fp)
                if not ctx.dry_run:
                    try:
                        validate_video_motion_temporal_delta(p)
                    except StaticFreezeFrameError as motion_err:
                        logger.error(f"[s10_render] Clip at index {idx} ({p.name}) failed motion audit: {motion_err}")
                        invalid_clip_indices.append(idx)
                    except Exception as probe_err:
                        logger.warning(f"[s10_render] Notice probing motion on clip {p.name}: {probe_err}")
                clip_paths.append(p)

        if invalid_clip_indices:
            raise MissingClipsError(
                f"Stage S10 requires all declared S8 video clips to be valid and >100B. "
                f"Found {len(invalid_clip_indices)} invalid clip(s) at index/indices {invalid_clip_indices} "
                f"(declared: {len(clips)}, valid: {len(clip_paths)})"
            )

        if not audio_file or not Path(audio_file).exists() or Path(audio_file).stat().st_size < 100:
            raise MissingAudioError(f"Stage S10 requires valid audio narration file from S9, got '{audio_file}'")

        # Source subtitles path strictly from S9 payload contract (Rule 125 & Boss Item 5)
        s9_sub_path = s9_data.get("payload", {}).get("subtitles_file")
        if not s9_sub_path:
            raise MissingSubtitlesError("Stage S10 requires canonical 'subtitles_file' key in S9 payload contract")

        ass_file = Path(s9_sub_path)
        if not ass_file.exists() or ass_file.stat().st_size == 0:
            raise MissingSubtitlesError(f"Stage S10 requires valid subtitles file at '{ass_file}'")

        # Delegate strictly to canonical vox assembly engine with two-pass loudnorm (Rule 125 & 139)
        assemble_final_video(clip_paths, Path(audio_file), ass_file, final_mp4)
        if not final_mp4.exists() or final_mp4.stat().st_size < 1000:
            raise RuntimeError(f"assemble_final_video failed to produce master MP4 at {final_mp4}")

    sz = final_mp4.stat().st_size if final_mp4.exists() else 0
    sha = compute_file_sha256(final_mp4) if final_mp4.exists() else "none"

    # Fail-closed forensic media verification (Rule 121, 125, 139 & Boss Round 6 Item 11)
    if not final_mp4.exists() or final_mp4.stat().st_size < 1000:
        raise FileNotFoundError(f"Stage S10 fail-closed: Master video missing or invalid at {final_mp4}")

    from vox.qa.gates import probe_media_file
    p_info = probe_media_file(final_mp4)
    v_st = next((s for s in p_info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v_st:
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' has no valid video stream")

    # Strict rate parsing: require finite positive measured rate, valid denominator, no silent intended fallback
    r_fps_str = v_st.get("r_frame_rate")
    if not r_fps_str or not isinstance(r_fps_str, str):
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' missing required 'r_frame_rate' telemetry")

    r_fps_str = r_fps_str.strip()
    try:
        if "/" in r_fps_str:
            num_str, den_str = r_fps_str.split("/", 1)
            num = float(num_str)
            den = float(den_str)
            if den <= 0.0 or not math.isfinite(num) or not math.isfinite(den):
                raise ValueError(f"Non-positive or non-finite rational components in '{r_fps_str}'")
            actual_fps = num / den
        else:
            actual_fps = float(r_fps_str)
    except Exception as rate_err:
        raise ValueError(f"Stage S10 fail-closed: Invalid r_frame_rate '{r_fps_str}': {rate_err}")

    if not math.isfinite(actual_fps) or actual_fps <= 0.0:
        raise ValueError(f"Stage S10 fail-closed: Measured video frame rate is non-finite or non-positive: {actual_fps}")

    # Reconcile r_frame_rate with avg_frame_rate if present (Boss Round 10 Item 4)
    avg_fps_str = v_st.get("avg_frame_rate")
    if avg_fps_str and isinstance(avg_fps_str, str) and avg_fps_str.strip() not in ("", "0/0"):
        try:
            if "/" in avg_fps_str:
                a_num, a_den = map(float, avg_fps_str.split("/", 1))
                if not math.isfinite(a_num) or not math.isfinite(a_den) or a_den <= 0.0:
                    raise ValueError(f"Non-positive or non-finite rational components in '{avg_fps_str}'")
                avg_fps = a_num / a_den
            else:
                avg_fps = float(avg_fps_str)
            if not math.isfinite(avg_fps) or avg_fps <= 0.0:
                raise ValueError(f"Non-positive or non-finite avg_frame_rate: {avg_fps}")
            if abs(actual_fps - avg_fps) > 0.1:
                raise ValueError(
                    f"Stage S10 fail-closed: Video r_frame_rate ({actual_fps:.2f}) contradicts avg_frame_rate ({avg_fps:.2f}) by > 0.1 fps"
                )
        except (ValueError, ZeroDivisionError) as avg_err:
            raise ValueError(f"Stage S10 fail-closed: Malformed or non-finite avg_frame_rate '{avg_fps_str}': {avg_err}")

    # Enforce intended vs measured fps agreement (within 0.1 fps)
    if abs(actual_fps - fps) > 0.1:
        raise ValueError(
            f"Stage S10 fail-closed: Measured video frame rate ({actual_fps:.2f} fps) deviates from "
            f"intended frame rate ({fps} fps) by > 0.1 fps"
        )

    # Require finite positive stream AND container format duration with cross-reconciliation
    s_dur_raw = v_st.get("duration")
    c_dur_raw = p_info.get("format", {}).get("duration")
    if s_dur_raw is None or str(s_dur_raw).strip() == "":
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' missing required stream duration")
    if c_dur_raw is None or str(c_dur_raw).strip() == "":
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' missing required container format duration")
    try:
        s_dur = float(s_dur_raw)
        c_dur = float(c_dur_raw)
    except (ValueError, TypeError) as dur_err:
        raise ValueError(f"Stage S10 fail-closed: Non-numeric duration in '{final_mp4}': {dur_err}")

    if not math.isfinite(s_dur) or s_dur <= 0.0 or not math.isfinite(c_dur) or c_dur <= 0.0:
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' has non-positive or non-finite duration (stream={s_dur}, container={c_dur})")

    if abs(s_dur - c_dur) > 0.2:
        raise ValueError(
            f"Stage S10 fail-closed: Stream duration ({s_dur:.3f}s) contradicts container format duration ({c_dur:.3f}s) by > 0.2s"
        )
    measured_dur = s_dur

    # Strictly require verified positive frame count in video stream (zero synthetic fallback)
    v_nb_frames_raw = v_st.get("nb_frames")
    if v_nb_frames_raw is None or str(v_nb_frames_raw).strip() == "":
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' missing required 'nb_frames' stream metadata")
    try:
        actual_frames = int(v_nb_frames_raw)
    except (ValueError, TypeError) as frame_err:
        raise ValueError(f"Stage S10 fail-closed: Malformed 'nb_frames' ({v_nb_frames_raw!r}) in '{final_mp4}': {frame_err}")
    if actual_frames <= 0:
        raise ValueError(f"Stage S10 fail-closed: Master video '{final_mp4}' has non-positive nb_frames ({actual_frames})")

    # Mandatory secondary physical packet-count verification (Boss Round 10 Item 4 & Round 11 Item 5)
    packet_frames_raw = v_st.get("nb_read_packets")
    if packet_frames_raw is None:
        if not final_mp4.exists():
            raise FileNotFoundError(f"Stage S10 fail-closed: Final video '{final_mp4}' missing for packet count verification")
        pkt_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_packets", "-show_entries", "stream=nb_read_packets",
            "-of", "json", str(final_mp4)
        ]
        try:
            pkt_res = subprocess.run(pkt_cmd, capture_output=True, text=True, check=True, timeout=30.0)
            pkt_data = json.loads(pkt_res.stdout)
            st_list = pkt_data.get("streams", [])
            if not st_list or "nb_read_packets" not in st_list[0]:
                raise ValueError("ffprobe output missing stream nb_read_packets field")
            packet_frames_raw = st_list[0].get("nb_read_packets")
        except Exception as pkt_err:
            raise ValueError(f"Stage S10 fail-closed: Mandatory secondary packet-count ffprobe failed: {pkt_err}") from pkt_err

    if packet_frames_raw is None or str(packet_frames_raw).strip() == "":
        raise ValueError(f"Stage S10 fail-closed: Mandatory secondary packet-count unavailable for '{final_mp4}'")

    try:
        packet_frames = int(packet_frames_raw)
    except (ValueError, TypeError) as parse_pkt_err:
        raise ValueError(f"Stage S10 fail-closed: Malformed secondary packet count ({packet_frames_raw!r}): {parse_pkt_err}") from parse_pkt_err

    if packet_frames <= 0:
        raise ValueError(f"Stage S10 fail-closed: Non-positive secondary packet count ({packet_frames}) in '{final_mp4}'")

    if abs(actual_frames - packet_frames) > 1:
        raise ValueError(
            f"Stage S10 fail-closed: Stream nb_frames ({actual_frames}) contradicts independently verified physical packet count ({packet_frames})"
        )

    # Mutual consistency: frame count, duration, and frame rate
    frame_dur_calc = actual_frames / actual_fps
    if abs(frame_dur_calc - measured_dur) > 0.2:
        raise ValueError(
            f"Stage S10 fail-closed: Frame count duration ({frame_dur_calc:.2f}s = {actual_frames} / {actual_fps:.2f}) "
            f"inconsistent with measured media duration ({measured_dur:.2f}s) by > 0.2s"
        )

    remotion_dur = render_props.duration_in_frames / fps
    if abs(measured_dur - remotion_dur) > 0.5:
        raise ValueError(
            f"Stage S10 fail-closed: Measured media duration ({measured_dur:.2f}s) drifts from "
            f"Remotion intended duration ({remotion_dur:.2f}s) by > 0.5s"
        )

    frame_drift = abs(actual_frames - render_props.duration_in_frames)
    max_drift_tolerance = max(3, int(round(actual_fps * 0.15)))  # Max ~0.15s (e.g. 3-4 frames)
    if frame_drift > max_drift_tolerance:
        raise ValueError(
            f"Stage S10 fail-closed: verified media frame count ({actual_frames}) drifts from "
            f"Remotion intended frames ({render_props.duration_in_frames}) by {frame_drift} frames "
            f"(tolerance ceiling: {max_drift_tolerance} frames)"
        )

    payload = {
        "task_id": ctx.run_id,
        "final_video_path": str(final_mp4),
        "remotion_props_file": str(props_file),
        "total_scenes_rendered": len(scene_props),
        "duration_in_frames": actual_frames,
        "fps": actual_fps,
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
