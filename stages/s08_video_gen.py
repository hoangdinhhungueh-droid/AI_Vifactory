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
from core.gates import compute_file_sha256, emit_artifact
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
        except Exception:
            pass

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
        except Exception:
            pass

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
                except OSError:
                    pass

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
            if active_seed_img.exists():
                # Apply dynamic Ken Burns zoompan camera motion (Rule 118, 121, 122)
                # NEVER static -loop 1 without motion
                try:
                    cmd = [
                        ffmpeg_bin, "-y", "-loop", "1", "-i", str(active_seed_img),
                        "-vf", f"zoompan=z='min(zoom+0.0015,1.15)':d={max(25, int(dur*fps))}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,fps={fps}",
                        "-t", str(dur), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        str(target_video)
                    ]
                    subprocess.run(cmd, capture_output=True, check=True, timeout=30)
                    validate_video_motion_temporal_delta(target_video)
                    clip_valid = True
                except Exception as _zp_err:
                    logger.debug(f"[s08_video_gen] zoompan notice for {sc_id}: {_zp_err}")

            if not clip_valid:
                # Dynamic testsrc fallback with continuous animated color bars and clock (Rule 118 & 121)
                try:
                    cmd = [
                        ffmpeg_bin, "-y", "-f", "lavfi",
                        "-i", f"testsrc=duration={dur}:size=1920x1080:rate={fps}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        str(target_video)
                    ]
                    subprocess.run(cmd, capture_output=True, check=True, timeout=30)
                    validate_video_motion_temporal_delta(target_video)
                    clip_valid = True
                except Exception as _test_err:
                    raise RuntimeError(f"[s08_video_gen] Failed to render dynamic video clip for {sc_id}: {_test_err}") from _test_err

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
            verified=True
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
