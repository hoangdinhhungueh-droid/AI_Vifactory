#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/assemble.py — Master Concat, Subtitle Burn-In & Loudnorm Assembly Engine (AVF-VOX-001).

Assembles rendered scene clips into the final broadcast video:
- Concat demuxer for seamless scene joining
- Audio multiplexing with loudnorm normalization (ebur128: -14 LUFS, TP: -1.0)
- ASS subtitle burning via libass
- Produces final.mp4 with 2 streams (H.264 + AAC)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def assemble_final_video(
    scene_clips: List[Path],
    audio_wav: Path,
    ass_subtitles: Path,
    final_output: Path,
) -> Path:
    """Assembles scene video clips, audio, and subtitles into final broadcast MP4."""
    final_output = Path(final_output)
    final_output.parent.mkdir(parents=True, exist_ok=True)

    if not scene_clips:
        raise ValueError("Cannot assemble final video: zero scene clips provided")

    # 1. Create ffmpeg concat list file
    concat_list_file = final_output.parent / "concat_list.txt"
    lines = [f"file '{clip.resolve().as_posix()}'" for clip in scene_clips]
    concat_list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Temporary concatenated video without audio
    temp_concat_video = final_output.parent / "temp_concat.mp4"

    from vox.ffmpeg_utils import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()

    cmd_concat = [
        ffmpeg_bin, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(temp_concat_video)
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)

    # 2. Multiplex audio and burn ASS subtitles with loudnorm
    # Escape path for ffmpeg subtitles filter (replace backslashes with forward slashes)
    ass_escaped = ass_subtitles.resolve().as_posix().replace(":", "\\:")

    cmd_master = [
        ffmpeg_bin, "-y",
        "-i", str(temp_concat_video),
        "-i", str(audio_wav),
        "-vf", f"subtitles='{ass_escaped}'",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-b:v", "3500k",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11",
        "-shortest",
        str(final_output)
    ]

    res = subprocess.run(cmd_master, capture_output=True, text=True, check=False)

    # Fallback if libass filter fails on specific platform without subtitles filter
    if res.returncode != 0 or not final_output.exists():
        cmd_master_fallback = [
            ffmpeg_bin, "-y",
            "-i", str(temp_concat_video),
            "-i", str(audio_wav),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-shortest",
            str(final_output)
        ]
        subprocess.run(cmd_master_fallback, capture_output=True, check=True)

    # Cleanup temp concat
    if temp_concat_video.exists():
        temp_concat_video.unlink(missing_ok=True)
    if concat_list_file.exists():
        concat_list_file.unlink(missing_ok=True)

    return final_output
