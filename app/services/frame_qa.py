"""
Frame QA v2 -- real per-clip timing table for frame extraction.

Root cause fixed (Decisions Log 27/07 "P2 - Khong co bang thoi gian clip
that"): the EP002 frame review extracted frames using a uniform AVERAGE
scene length (idx-0.5)*avg_scene_len, where avg_scene_len = total_audio
duration / N_scenes (~6.393s for EP002). Real clips are ~5.0s each and are
concatenated with a fixed crossfade overlap (video_render.XFADE_DURATION)
between every pair. Uniform-average timing silently drifts away from the
real per-clip boundaries the moment any clip's true duration differs from
the average -> extracted frames get mislabeled with the wrong scene index.

This module builds a REAL timing table from the actual ordered clip list
(the same list handed to video_render._concat_clips for the render) using
ffprobe per clip, then extracts one representative frame per clip at the
midpoint of that clip's true, non-crossfade-blended span in the final
concatenated timeline. No duration is ever assumed or averaged.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional

from app.services.mpt_ported.video_render import XFADE_DURATION


@dataclass
class ClipTiming:
    scene_index: int          # 1-based, matches Notion-authored scene numbering
    clip_path: str
    duration_s: float         # real ffprobe duration of the source clip
    final_start_s: float      # start of this clip in the final concatenated video
    final_end_s: float        # end of this clip in the final concatenated video
    frame_time_s: float       # recommended timestamp to extract a representative frame at


async def _probe_duration(path: str) -> Optional[float]:
    """ffprobe duration in seconds; None on failure (never a silent numeric
    fallback -- Rule 32: do not let a probe failure masquerade as data)."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", path]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        return float(out.decode().strip())
    except Exception:
        return None


async def build_clip_timing_table(
    clip_paths: List[str],
    xfade_s: float = XFADE_DURATION,
    scene_index_offset: int = 1,
) -> List[ClipTiming]:
    """Build the REAL per-clip timing table for a rendered episode.

    clip_paths must be the exact ordered list handed to
    video_render._concat_clips for this render (same clips, same order) --
    this function never guesses scene boundaries from total duration.
    """
    if not clip_paths:
        raise ValueError("[frame_qa] clip_paths is empty")

    durations: List[float] = []
    for path in clip_paths:
        d = await _probe_duration(path)
        if d is None:
            raise RuntimeError(
                f"[frame_qa] ffprobe failed on {path} - refusing to build a "
                "timing table on incomplete data")
        durations.append(d)

    table: List[ClipTiming] = []
    cursor = 0.0
    n = len(clip_paths)
    for i, (path, dur) in enumerate(zip(clip_paths, durations)):
        start = cursor
        end = start + dur
        # Stable (non-crossfade-blended) span: trim half the crossfade off
        # each edge that actually has a neighbouring transition.
        stable_start = start + (xfade_s / 2 if i > 0 else 0.0)
        stable_end = end - (xfade_s / 2 if i < n - 1 else 0.0)
        frame_time = (stable_start + stable_end) / 2
        table.append(ClipTiming(
            scene_index=i + scene_index_offset,
            clip_path=path,
            duration_s=round(dur, 3),
            final_start_s=round(start, 3),
            final_end_s=round(end, 3),
            frame_time_s=round(frame_time, 3),
        ))
        # Next clip starts xfade_s seconds before this one ends (rolling
        # pairwise xfade overlap -- see video_render._concat_clips).
        cursor = end - xfade_s
    return table


async def extract_frames(
    final_video_path: str,
    table: List[ClipTiming],
    out_dir: str,
) -> List[str]:
    """Extract one frame per table entry from the FINAL concatenated video,
    at each entry's frame_time_s, named by real (1-based) scene_index."""
    os.makedirs(out_dir, exist_ok=True)
    out_paths: List[str] = []
    for entry in table:
        out_path = os.path.join(out_dir, f"scene_{entry.scene_index:03d}.jpg")
        cmd = [
            "ffmpeg", "-y", "-ss", f"{entry.frame_time_s:.3f}",
            "-i", final_video_path, "-frames:v", "1", "-q:v", "2", out_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if proc.returncode == 0 and os.path.exists(out_path):
            out_paths.append(out_path)
    return out_paths


def write_timing_table_json(table: List[ClipTiming], path: str) -> None:
    with open(path, "w") as f:
        json.dump([asdict(t) for t in table], f, indent=2)
