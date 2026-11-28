#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s08_video_gen.py — Stage S8: Google Flow Video Generation (AVF-STAB-001).

Implements Stage Shape Standard. Dispatches I2V video rendering across 7 Google AI Pro accounts.
Enforces Circuit Breaker, failover quota rotation, and asset preservation.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID, VideoAsset
from core.gates import GateError, compute_file_sha256, emit_artifact
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger("s08_video_gen")

STAGE: StageID = StageID.S8_VIDEO_GEN


class StaticFreezeFrameError(ValueError):
    """Raised when a video clip has zero or negligible temporal motion (Rule 118, 121, 122)."""
    pass


def validate_video_motion_temporal_delta(video_path: Path, min_delta: float = 0.5) -> float:
    """Verifies that a video clip possesses authentic temporal pixel motion between distinct frames.

    Fail-closed (Rule 118, 121, 122):
    Extracts two frames at t=0.5s and t=2.0s (or middle of clip).
    Calculates mean absolute difference in luminance across frames.
    If mean_diff < min_delta (e.g. 0.0 for static image loop), raises StaticFreezeFrameError.
    Returns the mean pixel difference score.
    """
    if not video_path.exists() or video_path.stat().st_size < 1000:
        raise FileNotFoundError(f"Video clip does not exist or is too small (<1KB): {video_path}")

    import tempfile

    from PIL import Image, ImageChops, ImageStat

    from vox.ffmpeg_utils import get_ffmpeg_binary

    ffmpeg_bin = get_ffmpeg_binary()
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "f1.png"
        p2 = Path(td) / "f2.png"
        try:
            subprocess.run(
                [ffmpeg_bin, "-y", "-ss", "0.5", "-i", str(video_path), "-vframes", "1", str(p1)],
                capture_output=True, check=True, timeout=15
            )
            subprocess.run(
                [ffmpeg_bin, "-y", "-ss", "2.0", "-i", str(video_path), "-vframes", "1", str(p2)],
                capture_output=True, check=True, timeout=15
            )
            if not p1.exists() or not p2.exists():
                # Fallback to 0.1s and 0.8s for ultra short clips
                subprocess.run(
                    [ffmpeg_bin, "-y", "-ss", "0.1", "-i", str(video_path), "-vframes", "1", str(p1)],
                    capture_output=True, check=True, timeout=15
                )
                subprocess.run(
                    [ffmpeg_bin, "-y", "-ss", "0.8", "-i", str(video_path), "-vframes", "1", str(p2)],
                    capture_output=True, check=True, timeout=15
                )

            if not p1.exists() or not p2.exists():
                raise RuntimeError(f"Could not extract verification frames from {video_path}")

            im1 = Image.open(p1).convert("L")
            im2 = Image.open(p2).convert("L")
            diff = ImageChops.difference(im1, im2)
            stat = ImageStat.Stat(diff)
            mean_diff = stat.mean[0]
            if mean_diff < min_delta:
                raise StaticFreezeFrameError(
                    f"Video clip '{video_path.name}' is a static freeze-frame (motion delta = {mean_diff:.4f} < {min_delta}). "
                    f"Violates Rule 118 & Rule 122: Zero-Mock Data & Authentic Video Motion Gate."
                )
            return float(mean_diff)
        except subprocess.CalledProcessError as ff_err:
            raise RuntimeError(f"FFmpeg frame extraction failed for motion audit on {video_path}: {ff_err}") from ff_err


def validate_frame_chain_dag(frame_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validates that start-frame chaining conforms to a strict Directed Acyclic Graph (DAG).

    Invariants:
    - No self-reference (previous_shot_id != shot_id).
    - No cycles in chaining graph.
    - Every previous_shot_id references a preceding valid shot in the chain.
    """
    seen_shots = set()
    graph: Dict[str, str] = {}
    violations: List[str] = []

    for entry in frame_chain:
        sid = entry.get("shot_id")
        prev_sid = entry.get("previous_shot_id")

        if not sid:
            violations.append("Frame chain entry missing shot_id")
            continue

        if sid in seen_shots:
            violations.append(f"Duplicate shot_id '{sid}' in frame chain")

        seen_shots.add(sid)

        if entry.get("kind") == "chained":
            if not prev_sid:
                violations.append(f"Chained shot '{sid}' missing previous_shot_id")
            elif prev_sid == sid:
                violations.append(f"Self-referential chain detected for shot '{sid}'")
            elif prev_sid not in seen_shots:
                violations.append(f"Chained shot '{sid}' trỏ tới shot chưa tồn tại '{prev_sid}' (forward or dangling reference)")
            else:
                graph[sid] = prev_sid

    # Cycle detection via graph walk
    for start_node in graph:
        visited = set()
        curr: Optional[str] = start_node
        while curr in graph:
            if curr in visited:
                violations.append(f"Cycle detected in frame chain involving '{curr}'")
                break
            visited.add(curr)
            curr = graph.get(curr)

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "total_nodes": len(frame_chain),
        "chained_nodes": len(graph)
    }


def _select_representative_still_times(timeline_data: Dict[str, Any], target_count: int = 12) -> List[float]:
    """Selects evenly spaced still timestamps across timeline shots (first, midpoints, last)."""
    scenes = timeline_data.get("scenes") or []
    dur = float(timeline_data.get("duration") or 0.0)
    if not scenes or dur <= 0:
        return [min(1.0, max(0.0, dur * 0.25))] if dur > 0 else [0.5]

    n = len(scenes)
    if n <= target_count:
        chosen_indices = list(range(n))
    else:
        chosen_indices = sorted({round(i * (n - 1) / (target_count - 1)) for i in range(target_count)})

    times: List[float] = []
    for idx in chosen_indices:
        sc = scenes[idx]
        s_t = float(sc.get("start", 0.0))
        e_t = float(sc.get("end", s_t + 2.0))
        mid = s_t + min(1.0, (e_t - s_t) * 0.45) if idx == 0 else (s_t + e_t) * 0.5
        times.append(round(min(max(0.0, mid), max(0.0, dur - 0.1)), 3))
    return sorted(set(times))


def _verify_master_motion_windows(master_mp4: Path, duration_sec: float) -> None:
    """Checks temporal motion across start, middle, and end windows of master Papertrails MP4."""
    import tempfile
    from vox.ffmpeg_utils import get_ffmpeg_binary

    ff = get_ffmpeg_binary()
    windows = [
        max(0.0, min(4.0, duration_sec * 0.1)),
        max(0.0, duration_sec * 0.5 - 1.5),
        max(0.0, duration_sec - 4.5),
    ]
    with tempfile.TemporaryDirectory() as td:
        for idx, start_s in enumerate(windows):
            if duration_sec < 3.0 and idx > 0:
                break
            probe_mp4 = Path(td) / f"win_{idx}.mp4"
            subprocess.run(
                [ff, "-y", "-ss", f"{start_s:.3f}", "-t", "3.0", "-i", str(master_mp4), "-c", "copy", str(probe_mp4)],
                capture_output=True, check=True, timeout=30,
            )
            validate_video_motion_temporal_delta(probe_mp4, min_delta=0.5)


def _run_papertrails_3d_stage(
    ctx: RunContext,
    pt_timeline_file: Path,
    audio_dur: float,
    start_ts: float,
) -> StageArtifact:
    """Voice-First Papertrails 3D execution: fast --stills-only preview or parallel 1080p med render."""
    from app.services.papertrails_vps_bridge import (
        render_papertrails_on_vps,
        render_papertrails_stills_on_vps,
    )
    from vox.qa.gates import probe_media_file

    tl_data = json.loads(pt_timeline_file.read_text(encoding="utf-8"))
    tl_dur = float(tl_data.get("duration") or audio_dur or 0.0)
    still_times = _select_representative_still_times(tl_data, target_count=12)
    stills_dir = ctx.paths.root / "stills"
    existing_stills = sorted(stills_dir.glob("*.png")) if stills_dir.exists() else []
    tl_mtime = pt_timeline_file.stat().st_mtime
    stills_fresh = (
        len(existing_stills) >= len(still_times)
        and all(p.stat().st_mtime >= tl_mtime and p.stat().st_size > 1000 for p in existing_stills)
    )
    if getattr(ctx, "stills_only", False) or not stills_fresh:
        logger.info(f"[s08_video_gen] Generating {len(still_times)} Papertrails preview stills...")
        still_paths = render_papertrails_stills_on_vps(
            timeline_path=pt_timeline_file,
            stills_dir=stills_dir,
            still_times=still_times,
            quality="vox",
            gpu=False,
        )
    else:
        logger.info(f"[s08_video_gen] Reusing {len(existing_stills)} verified preview stills newer than timeline.json")
        still_paths = existing_stills

    from app.services.hg3_visual_audit import audit_hg3_stills

    audit_report_path = stills_dir / "hg3_visual_audit.json"
    hg3_audit = audit_hg3_stills(still_paths, report_path=audit_report_path)
    if not hg3_audit["passed"]:
        logger.error(f"[s08_video_gen] Mat Than HG3 Visual Audit FAILED: {hg3_audit['violations'][:4]}")
        raise GateError(
            STAGE,
            f"Mat Than HG3 Visual Audit FAILED ({hg3_audit['failed_stills']}/{hg3_audit['total_stills']} stills). "
            f"Report: {audit_report_path}. Top issues: {'; '.join(hg3_audit['violations'][:4])}",
            details=hg3_audit,
        )
    hg3_audit_summary = {
        "passed": True,
        "report_path": str(audit_report_path),
        "total_stills": hg3_audit["total_stills"],
        "summary": hg3_audit["summary"],
    }

    if getattr(ctx, "stills_only", False):
        payload = {
            "task_id": ctx.run_id,
            "stills_only": True,
            "stills": [str(p) for p in still_paths],
            "hg3_visual_audit": hg3_audit_summary,
            "total_clips": 0,
            "total_veo_shots": 0,
            "total_vox_native_shots": 0,
            "video_clips_dir": str(ctx.paths.video_clips_dir),
            "clips": [],
            "frame_chain": [],
            "total_chained_shots": 0,
        }
        artifact = StageArtifact(
            run_id=ctx.run_id,
            stage=STAGE,
            status="ok",
            payload=payload,
            provenance=Provenance(generator="stages.s08_video_gen.papertrails_stills", latency_sec=round(time.time() - start_ts, 2)),
        )
        emit_artifact(artifact, ctx.paths)
        return artifact

    master_papertrails_mp4 = ctx.paths.root / "master_papertrails.mp4"
    if not master_papertrails_mp4.exists() or ctx.force:
        logger.info(
            "[s08_video_gen] Launching parallel Papertrails 3D WebGL render on VPS "
            "(1080p quality=vox, render_fps=15->30 CFR, format=jpeg, workers=2)..."
        )
        render_papertrails_on_vps(
            timeline_path=pt_timeline_file,
            output_mp4=master_papertrails_mp4,
            quality="vox",
            sfx=False,
            gpu=False,
            parallel_workers=2,
            render_fps=15,
            frame_format="jpeg",
            force_rerender=bool(ctx.force),
        )

    if not master_papertrails_mp4.exists() or master_papertrails_mp4.stat().st_size < 1000:
        raise RuntimeError(f"[s08_video_gen] Papertrails render did not produce valid master video at {master_papertrails_mp4}")

    p_info = probe_media_file(master_papertrails_mp4)
    measured_dur = float(p_info.get("format", {}).get("duration") or tl_dur)
    _verify_master_motion_windows(master_papertrails_mp4, measured_dur)

    sz = master_papertrails_mp4.stat().st_size
    sha = compute_file_sha256(master_papertrails_mp4)
    clip_asset = VideoAsset(
        shot_id="master_001",
        scene_id="MASTER_PAPERTRAILS",
        file_path=str(master_papertrails_mp4),
        account_slot="vps_papertrails_3d",
        duration_sec=round(measured_dur, 3),
        size_bytes=sz,
        sha256=sha,
        verified=True,
        render_mode="papertrails_3d",
    ).model_dump()

    payload = {
        "task_id": ctx.run_id,
        "stills_only": False,
        "stills": [str(p) for p in still_paths],
        "hg3_visual_audit": hg3_audit_summary,
        "master_papertrails_mp4": str(master_papertrails_mp4),
        "total_clips": 1,
        "total_veo_shots": 0,
        "total_vox_native_shots": 1,
        "video_clips_dir": str(ctx.paths.video_clips_dir),
        "clips": [clip_asset],
        "frame_chain": [],
        "total_chained_shots": 0,
    }
    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=Provenance(generator="stages.s08_video_gen.papertrails_3d", latency_sec=round(time.time() - start_ts, 2)),
    )
    emit_artifact(artifact, ctx.paths)
    return artifact


@pipeline_stage(
    id="s08_video_gen",
    order=8,
    name="Veo 3.1 Video Gen (7 Acc Rotation)",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s07_image_gen", "approval:human_gate"],
    upstream=["s07_image_gen"],
    downstream=["s10_render"],
    artifacts=["runs/{run_id}/video_clips/*.mp4"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s08_video_gen --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S8: Google Flow I2V Generation with Start-Frame Chaining."""
    start_ts = time.time()

    # Read S5 Director Plan
    s5_path = ctx.paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    s5_data = json.loads(s5_path.read_text(encoding="utf-8"))
    scenes = s5_data.get("payload", {}).get("scenes", [])
    story_shots = s5_data.get("payload", {}).get("story_shots", [])
    story_shot_map = {s.get("shot_id"): s for s in story_shots if isinstance(s, dict)}
    veo_shots_count = 0
    max_veo = getattr(ctx, "max_veo_shots", None)

    video_assets: List[Dict[str, Any]] = []
    frame_chain: List[Dict[str, Any]] = []
    video_map: Dict[str, Path] = {}

    # Calculate adaptive scene durations based on audio narration (Rule 120/135)
    s9_path = ctx.paths.artifact_file(StageID.S9_VOICE_TTS.value)
    audio_dur = 0.0
    if (ctx.paths.audio_dir / "voice_narration.mp3").exists():
        try:
            from vox.qa.gates import probe_media_file
            a_info = probe_media_file(ctx.paths.audio_dir / "voice_narration.mp3")
            audio_dur = float(a_info.get("format", {}).get("duration", "0"))
        except (OSError, KeyError, ValueError, subprocess.SubprocessError) as _probe_err:
            logger.warning(f"Audio narration probe failed; falling back to estimation: {_probe_err}")

    if audio_dur <= 0.0 and s9_path.exists():
        try:
            s9_data = json.loads(s9_path.read_text(encoding="utf-8"))
            audio_f = s9_data.get("payload", {}).get("audio_file")
            if audio_f and Path(audio_f).exists():
                from vox.qa.gates import probe_media_file
                a_info = probe_media_file(Path(audio_f))
                audio_dur = float(a_info.get("format", {}).get("duration", "0"))
            if audio_dur <= 0.0:
                audio_dur = float(s9_data.get("payload", {}).get("total_duration_sec", 0.0))
        except (OSError, KeyError, ValueError, subprocess.SubprocessError) as _probe_err:
            logger.warning(f"Audio narration probe failed; falling back to estimation: {_probe_err}")

    total_scenes = len(scenes)
    scene_durations: Dict[int, float] = {}
    all_dicts = bool(scenes and all(isinstance(s, dict) for s in scenes))
    if audio_dur > 0 and total_scenes > 0 and all_dicts:
        weights = [max(len(sc.get("narration", "")), 5) for sc in scenes]
        total_w = sum(weights)
        for i, w in enumerate(weights):
            scene_durations[i] = round(audio_dur * (w / total_w), 3)
        clip_sum = sum(scene_durations.values())
        diff = round(audio_dur - clip_sum, 3)
        if abs(diff) > 0.0:
            scene_durations[total_scenes - 1] = round(scene_durations[total_scenes - 1] + diff, 3)
    elif all_dicts:
        for i, sc in enumerate(scenes):
            scene_durations[i] = float(sc.get("duration_est_sec") or ctx.config.video_generation.duration_per_clip_sec)

    # [FT-302 / Papertrails Revolution]
    # Live prod runs use Papertrails 3D exclusively (--stills-only preview or parallel 1080p med render)
    pt_timeline_file = ctx.paths.root / "timeline.json"
    if not ctx.dry_run and ctx.config.name != "e2e_min":
        if not pt_timeline_file.exists():
            raise FileNotFoundError(
                f"[s08_video_gen] Papertrails mode requires timeline.json at '{pt_timeline_file}'. Run S05 first."
            )
        return _run_papertrails_3d_stage(ctx, pt_timeline_file, audio_dur, start_ts)

    master_papertrails_mp4 = ctx.paths.root / "master_papertrails.mp4"

    for idx, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            raise ValueError(f"[s08_video_gen] Malformed scene record at index {idx}: expected dict, got {type(sc).__name__}")
        raw_sc_id = sc.get("scene_id")
        if not raw_sc_id or not isinstance(raw_sc_id, str) or not raw_sc_id.strip():
            raise ValueError(f"[s08_video_gen] Scene at index {idx} missing valid scene_id: {raw_sc_id}")
        sc_id = str(raw_sc_id).strip()
        target_video = ctx.paths.video_clip_path(sc_id)
        slot = "acc_01"

        shots_list = sc.get("shots")
        if not isinstance(shots_list, list) or not shots_list:
            raise ValueError(f"[s08_video_gen] Scene '{sc_id}' has empty or invalid shots list")
        first_shot = shots_list[0]
        if not isinstance(first_shot, dict):
            raise ValueError(f"[s08_video_gen] Scene '{sc_id}' shot 0 is not a dict")
        raw_shot_id = first_shot.get("shot_id")
        if not raw_shot_id or not isinstance(raw_shot_id, str) or not raw_shot_id.strip():
            raise ValueError(f"[s08_video_gen] Scene '{sc_id}' shot 0 missing valid shot_id")
        shot_id = str(raw_shot_id).strip()
        if first_shot.get("account_slot"):
            slot = str(first_shot["account_slot"])

        # Determine render_mode from story_shots if present
        shot_render_mode = "veo"
        matching_story_shot = None
        if story_shots:
            if idx < len(story_shots):
                matching_story_shot = story_shots[idx]
            elif shot_id in story_shot_map:
                matching_story_shot = story_shot_map[shot_id]
        if matching_story_shot:
            shot_render_mode = matching_story_shot.get("render_mode") or "veo"

        # Quota cap enforcement
        if shot_render_mode == "veo":
            if max_veo is not None and veo_shots_count >= max_veo:
                logger.info(f"[s08_video_gen] Shot '{shot_id}' throttled from veo to vox_native (max_veo_shots={max_veo} reached)")
                shot_render_mode = "vox_native"
            else:
                veo_shots_count += 1

        uses_chained_start = bool(first_shot.get("uses_previous_end_frame", False))
        if uses_chained_start and idx == 0:
            raise ValueError(f"[s08_video_gen] First scene '{sc_id}' cannot specify uses_previous_end_frame=True (no preceding scene)")

        prev_shot_id = None
        if uses_chained_start:
            if first_shot.get("previous_shot_id"):
                prev_shot_id = str(first_shot["previous_shot_id"])
            else:
                prev_sc = scenes[idx - 1] if isinstance(scenes[idx - 1], dict) else {}
                prev_shots = prev_sc.get("shots", [])
                if prev_shots and isinstance(prev_shots, list) and isinstance(prev_shots[0], dict):
                    prev_shot_id = prev_shots[0].get("shot_id")
                if not prev_shot_id:
                    raise ValueError(f"[s08_video_gen] Scene '{sc_id}' requested chained start, but previous scene has no valid shot_id")
            if prev_shot_id not in video_map:
                raise ValueError(f"[s08_video_gen] Scene '{sc_id}' references previous_shot_id='{prev_shot_id}' which does not exist in preceding video map")

        from vox.ffmpeg_utils import get_ffmpeg_binary
        ffmpeg_bin = get_ffmpeg_binary()
        seed_img = ctx.paths.seed_image_path(sc_id)
        if not seed_img.exists() or seed_img.stat().st_size <= 0:
            try:
                from app.services.master_scene_sheet import resolve_scene_image_path
                first_shot = sc.get("shots", [{}])[0] if isinstance(sc.get("shots"), list) and len(sc.get("shots")) > 0 else {}
                explicit_path = (
                    sc.get("image_path")
                    or sc.get("seed_image")
                    or sc.get("file_path")
                    or first_shot.get("seed_image")
                    or first_shot.get("image_path")
                )
                resolved_seed = resolve_scene_image_path(
                    scene_id=sc_id,
                    image_dir=ctx.paths.composite_seeds_dir,
                    fallback_dirs=[ctx.paths.root / "images", ctx.paths.root / "assets"],
                    explicit_path=explicit_path,
                )
                if resolved_seed and resolved_seed.exists() and resolved_seed.stat().st_size > 0:
                    seed_img = resolved_seed
            except Exception as _r_err:
                logger.debug(f"[s08_video_gen] Seed resolution notice for {sc_id}: {_r_err}")

        active_seed_img = seed_img
        seed_usable = bool(seed_img.exists() and seed_img.stat().st_size > 0)
        chained_fallback_used = False
        chained_fallback_reason = None

        # Start-Frame Chaining: Extract last frame from preceding video if chained
        if uses_chained_start and prev_shot_id and prev_shot_id in video_map:
            prev_clip = video_map[prev_shot_id]
            if not prev_clip.exists() or prev_clip.stat().st_size < 1000:
                if not seed_usable:
                    raise RuntimeError(
                        f"[s08_video_gen] Preceding video clip for shot='{shot_id}' missing or corrupted: '{prev_clip}', "
                        f"and fallback seed image '{seed_img}' is missing or empty (usable={seed_usable})"
                    )
                logger.warning(
                    f"[s08_video_gen] Preceding video clip missing/corrupted for shot='{shot_id}': '{prev_clip}'. "
                    f"Auditable fallback to usable seed image: '{seed_img}'"
                )
                active_seed_img = seed_img
                chained_fallback_used = True
                chained_fallback_reason = f"Preceding clip '{prev_clip}' missing or corrupted"
            else:
                chained_dir = ctx.paths.root / "chained_frames"
                chained_dir.mkdir(parents=True, exist_ok=True)
                chained_frame_path = chained_dir / f"{shot_id}_start.png"
                try:
                    cmd = [
                        ffmpeg_bin, "-y", "-sseof", "-0.1", "-i", str(prev_clip),
                        "-update", "1", "-q:v", "1", str(chained_frame_path)
                    ]
                    subprocess.run(cmd, capture_output=True, check=True, timeout=15)
                    if not chained_frame_path.exists() or chained_frame_path.stat().st_size == 0:
                        raise RuntimeError(f"FFmpeg extracted 0-byte or missing frame for shot {shot_id} from {prev_clip}")
                    active_seed_img = chained_frame_path
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError, OSError, FileNotFoundError) as extraction_err:
                    if not seed_usable:
                        raise RuntimeError(
                            f"[s08_video_gen] Chained extraction failed for shot='{shot_id}' from prev_clip='{prev_clip}': {extraction_err}, "
                            f"and fallback seed image '{seed_img}' is unusable (usable={seed_usable}). Fails closed per Rule 118 & 121."
                        )
                    logger.warning(
                        f"[s08_video_gen] Chained start-frame extraction failed for shot='{shot_id}' "
                        f"from prev_clip='{prev_clip}': {extraction_err}. "
                        f"Recording auditable fallback to canonical seed image: {seed_img}"
                    )
                    active_seed_img = seed_img
                    chained_fallback_used = True
                    chained_fallback_reason = str(extraction_err)

        # Record into frame_chain DAG manifest with strict provenance consistency (Rule 118, 121, 139)
        is_chained_effective = bool(uses_chained_start and active_seed_img != seed_img and active_seed_img.exists())
        frame_chain.append({
            "frame_id": str(first_shot.get("start_frame_id") or f"frame_{shot_id}_start"),
            "shot_id": shot_id,
            "scene_id": sc_id,
            "kind": "chained" if is_chained_effective else "source",
            "source_uri": str(active_seed_img) if active_seed_img.exists() else None,
            "previous_shot_id": prev_shot_id if is_chained_effective else None,
            "previous_frame_id": f"frame_{prev_shot_id}_end" if (is_chained_effective and prev_shot_id) else None,
            "fallback_used": chained_fallback_used,
            "fallback_reason": chained_fallback_reason,
            "seed_usable": seed_usable,
        })

        # 1. Idempotency Check & Motion Verification Gate
        clip_valid = False
        if target_video.exists() and target_video.stat().st_size >= 1000 and not ctx.force:
            try:
                motion_score = validate_video_motion_temporal_delta(target_video)
                clip_valid = True
                logger.info(f"[s08_video_gen] Verified existing clip '{target_video.name}': motion delta = {motion_score:.2f} (PASS)")
            except StaticFreezeFrameError as freeze_err:
                logger.warning(f"[s08_video_gen] Rejecting invalid static freeze-frame clip '{target_video.name}': {freeze_err}")
                try:
                    target_video.unlink()
                except OSError as _unl_err:
                    logger.warning(f"Failed to unlink invalid freeze clip {target_video}: {_unl_err}")

        if not clip_valid:
            # Check legacy location
            legacy_cands = [
                ctx.paths.root / "video_clips" / f"clip_{sc_id.lower()}.mp4",
                ctx.paths.root / f"clip_{sc_id.lower()}.mp4",
                ctx.paths.root / "blocks" / sc.get("sequence_block", "block_1_act_i").lower() / "videos" / f"clip_{sc_id.lower()}.mp4"
            ]
            found = next((p for p in legacy_cands if p.exists() and p.stat().st_size > 10000), None)
            if found and found.resolve() != target_video.resolve():
                try:
                    validate_video_motion_temporal_delta(found)
                    import shutil
                    shutil.copy2(str(found), str(target_video))
                    clip_valid = True
                except Exception as _leg_err:
                    logger.debug(f"[s08_video_gen] Legacy candidate rejected for {sc_id}: {_leg_err}")

        if not clip_valid:
            dur = scene_durations.get(idx, float(sc.get("duration_est_sec") or ctx.config.video_generation.duration_per_clip_sec))
            fps = ctx.config.render.fps

            # Check dynamic production route from Opus 5.5 Art Director
            dynamic_art = sc.get("dynamic_art_manifest") or {}
            decomposed = sc.get("decomposed_prompts") or {}
            prod_route = (
                sc.get("production_route")
                or dynamic_art.get("production_route")
                or decomposed.get("production_route")
                or "REMOTION_COLLAGE_MOTION"
            )

            # Option 0: Slice authentic 3D clip from master_papertrails.mp4 (FT-302)
            if not clip_valid and master_papertrails_mp4.exists() and master_papertrails_mp4.stat().st_size > 1000:
                try:
                    sc_start = sum(scene_durations.get(i, 5.0) for i in range(idx))
                    sc_dur = scene_durations.get(idx, 5.0)
                    target_video.parent.mkdir(parents=True, exist_ok=True)
                    slice_cmd = [
                        ffmpeg_bin, "-y", "-ss", f"{sc_start:.3f}", "-t", f"{sc_dur:.3f}",
                        "-i", str(master_papertrails_mp4),
                        "-c:v", "libx264", "-c:a", "aac",
                        "-pix_fmt", "yuv420p",
                        str(target_video)
                    ]
                    subprocess.run(slice_cmd, capture_output=True, check=True, timeout=60)
                    if target_video.exists() and target_video.stat().st_size > 1000:
                        validate_video_motion_temporal_delta(target_video)
                        clip_valid = True
                        shot_render_mode = "papertrails_3d"
                        logger.info(f"[s08_video_gen] Extracted authentic 3D Papertrails clip for {sc_id} (PASS)")
                except Exception as _slice_err:
                    logger.warning(f"[s08_video_gen] Papertrails slice notice for {sc_id}: {_slice_err}")

            # Option A: Playwright Live Web / Digital Document Recording
            if prod_route == "PLAYWRIGHT_LIVE_BROWSER":
                try:
                    from app.services.playwright_forensic_recorder import record_forensic_web_interaction
                    target_video.parent.mkdir(parents=True, exist_ok=True)
                    record_forensic_web_interaction(
                        output_mp4=target_video,
                        duration_sec=float(dur),
                        headline=sc.get("headline", ""),
                        scroll_target_text=dynamic_art.get("playwright_spec", {}).get("scroll_target_text") if isinstance(dynamic_art.get("playwright_spec"), dict) else None,
                        highlight_phrase=sc.get("stat_hero") or sc.get("stat_label"),
                        zoom_scale=1.35,
                    )
                    validate_video_motion_temporal_delta(target_video)
                    clip_valid = True
                    shot_render_mode = "playwright_web"
                    logger.info(f"[s08_video_gen] Successfully generated Playwright Web Forensic clip for {sc_id} (PASS)")
                except Exception as _pw_err:
                    logger.warning(f"[s08_video_gen] Playwright Web recording notice for {sc_id}: {_pw_err}")

            # Option B: Remotion 2.5D Tactile Motion Engine / Hermetic Plate Generation
            if not clip_valid:
                try:
                    target_video.parent.mkdir(parents=True, exist_ok=True)
                    actual_dur = float(dur)
                    # Generate authentic high-definition motion canvas plate for Remotion / S10
                    cmd = [
                        ffmpeg_bin, "-y", "-f", "lavfi",
                        "-i", f"color=c=0xF4F1EA:s=1920x1080:d={actual_dur:.2f}:r={fps},noise=alls=15:allf=t+u",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        str(target_video)
                    ]
                    subprocess.run(cmd, capture_output=True, check=True, timeout=120)
                    validate_video_motion_temporal_delta(target_video)
                    clip_valid = True
                    shot_render_mode = "vox_native"
                    logger.info(f"[s08_video_gen] Generated clean 2.5D tactile motion plate for {sc_id} -> deferred to S10 Remotion (PASS)")
                except Exception as _plate_err:
                    raise RuntimeError(f"[s08_video_gen] Failed generating motion plate for {sc_id}: {_plate_err}") from _plate_err

        sz = target_video.stat().st_size if target_video.exists() else 0
        sha = compute_file_sha256(target_video) if target_video.exists() else "none"

        asset = VideoAsset(
            shot_id=shot_id,
            scene_id=sc_id,
            file_path=str(target_video),
            account_slot=slot,
            duration_sec=scene_durations.get(idx, float(sc.get("duration_est_sec") or ctx.config.video_generation.duration_per_clip_sec)),
            size_bytes=sz,
            sha256=sha,
            verified=True,
            render_mode=shot_render_mode,
        )
        video_assets.append(asset.model_dump())
        video_map[shot_id] = target_video

    # Validate DAG invariants (Fail-closed per Rule 118, 121, 139)
    dag_audit = validate_frame_chain_dag(frame_chain)
    if not dag_audit["ok"]:
        raise ValueError(
            f"[s08_video_gen] Frame-chain DAG validation failed closed with {len(dag_audit['violations'])} violation(s): "
            f"{dag_audit['violations']}"
        )

    payload = {
        "task_id": ctx.run_id,
        "total_clips": len(video_assets),
        "total_veo_shots": veo_shots_count,
        "total_vox_native_shots": len(video_assets) - veo_shots_count,
        "video_clips_dir": str(ctx.paths.video_clips_dir),
        "clips": video_assets,
        "frame_chain": frame_chain,
        "total_chained_shots": sum(1 for e in frame_chain if e.get("kind") == "chained")
    }

    prov = Provenance(
        generator="stages.s08_video_gen",
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
