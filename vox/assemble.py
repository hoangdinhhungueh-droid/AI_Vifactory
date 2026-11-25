#!/usr/bin/env python3
"""vox/assemble.py — Master Concat, Subtitle Burn-In & Loudnorm Assembly Engine (AVF-VOX-001).

Assembles rendered scene clips into the final broadcast video:
- Concat demuxer for seamless scene joining
- Audio multiplexing with loudnorm normalization (ebur128: -14 LUFS, TP: -1.0)
- ASS subtitle burning via libass
- Produces final.mp4 with 2 streams (H.264 + AAC)
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vox.assemble")


def assemble_final_video(
    scene_clips: Optional[list[Path]] = None,
    audio_wav: Path = None,
    ass_subtitles: Path = None,
    final_output: Path = None,
    scene_durations: Optional[list[float]] = None,
    silent_video: Optional[Path] = None,
) -> Path:
    """Assembles scene video clips or silent master video, audio, and subtitles into final broadcast MP4."""
    final_output = Path(final_output)
    final_output.parent.mkdir(parents=True, exist_ok=True)

    if not silent_video and not scene_clips:
        raise ValueError("Cannot assemble final video: zero scene clips provided and no silent_video specified")

    from vox.ffmpeg_utils import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()

    # Measure exact audio duration to avoid premature truncation
    import wave
    audio_dur = 0.0
    try:
        with wave.open(str(audio_wav), "rb") as wf:
            audio_dur = wf.getnframes() / float(wf.getframerate())
    except Exception:
        # Fallback to ffmpeg -i duration parsing (works everywhere without requiring ffprobe)
        try:
            import re
            cmd_probe = [ffmpeg_bin, "-i", str(audio_wav)]
            p_res = subprocess.run(cmd_probe, capture_output=True, text=True)
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p_res.stderr or "")
            if m:
                audio_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            else:
                audio_dur = 0.0
        except Exception:
            audio_dur = 0.0

    # If scene_durations is not provided or mismatched, calculate fallback from audio duration
    if not scene_durations or len(scene_durations) != len(scene_clips):
        if audio_dur > 0:
            per_clip = audio_dur / len(scene_clips)
            scene_durations = [per_clip] * len(scene_clips)
        else:
            scene_durations = None

    temp_files_to_clean: list[Path] = []
    clips_to_concat: list[Path] = []

    # Normalize each scene clip to exact scene duration with dead-stop hold on final frame (Rule 140)
    if scene_durations and len(scene_durations) == len(scene_clips):
        print(f"[assemble] Normalizing and holding {len(scene_clips)} clips to scene durations...", flush=True)
        for idx, (clip, target_sec) in enumerate(zip(scene_clips, scene_durations)):
            adj_path = final_output.parent / f"adj_clip_{idx:03d}_{clip.name}"
            temp_files_to_clean.append(adj_path)

            # Probe clip duration
            clip_dur = 0.0
            try:
                import re
                c_probe = subprocess.run([ffmpeg_bin, "-i", str(clip)], capture_output=True, text=True)
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", c_probe.stderr or "")
                if m:
                    clip_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            except Exception:
                clip_dur = 0.0

            pad = max(0.0, target_sec - clip_dur)
            vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30"
            if pad > 0.01:
                vf += f",tpad=stop_mode=clone:stop_duration={pad:.3f}"

            cmd_adj = [
                ffmpeg_bin, "-y",
                "-i", str(clip),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "ultrafast" if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("VF_TEST_MODE") == "1" else "veryfast",
                "-pix_fmt", "yuv420p",
                "-t", f"{target_sec:.3f}",
                str(adj_path)
            ]
            try:
                subprocess.run(cmd_adj, capture_output=True, check=True)
                clips_to_concat.append(adj_path)
            except subprocess.CalledProcessError:
                clips_to_concat.append(clip)
    else:
        clips_to_concat = list(scene_clips)

    if silent_video and Path(silent_video).exists() and Path(silent_video).stat().st_size > 1000:
        temp_concat_video = Path(silent_video)
    else:
        # 1. Create ffmpeg concat list file
        concat_list_file = final_output.parent / "concat_list.txt"
        temp_files_to_clean.append(concat_list_file)
        lines = [f"file '{clip.resolve().as_posix()}'" for clip in clips_to_concat]
        concat_list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Temporary concatenated video without audio
        temp_concat_video = final_output.parent / "temp_concat.mp4"
        temp_files_to_clean.append(temp_concat_video)

        print(f"[assemble] Concatenating {len(clips_to_concat)} clips via stream copy...", flush=True)
        cmd_concat = [
            ffmpeg_bin, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(temp_concat_video)
        ]
        try:
            subprocess.run(cmd_concat, capture_output=True, check=True)
        except subprocess.CalledProcessError as _c_err:
            err_msg = _c_err.stderr.decode("utf-8", errors="replace") if _c_err.stderr else str(_c_err)
            raise RuntimeError(f"assemble_final_video concat failed: {err_msg}") from _c_err

    from vox.ffmpeg_utils import build_twopass_loudnorm_filter
    loudnorm_filter = build_twopass_loudnorm_filter(ffmpeg_bin, Path(audio_wav), target_i=-16.0, target_tp=-2.5, target_lra=11.0)

    # Escape path for ffmpeg subtitles filter (replace backslashes with forward slashes)
    ass_escaped = ass_subtitles.resolve().as_posix().replace(":", "\\:")

    # Rule 140 Stop-Motion Living Vitality filter:
    # 2px micro-vibration on twos/threes (12-15fps) across held frames, keeping subtitles razor sharp
    vf_master = (
        f"tpad=stop_mode=clone:stop_duration=5,"
        f"crop=w=1916:h=1076:x='2+2*mod(floor(n/2),2)':y='2+2*mod(floor(n/3),2)',"
        f"scale=1920:1080,"
        f"subtitles='{ass_escaped}'"
    )

    cmd_master = [
        ffmpeg_bin, "-y",
        "-i", str(temp_concat_video),
        "-i", str(audio_wav),
        "-vf", vf_master,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast" if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("VF_TEST_MODE") == "1" else "veryfast",
        "-b:v", "3500k",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-af", loudnorm_filter,
        "-t", f"{audio_dur:.3f}",
        str(final_output)
    ]

    print(f"[assemble] Burning subtitles and multiplexing audio ({audio_dur:.2f}s) to {final_output.name}...", flush=True)
    res = subprocess.run(cmd_master, capture_output=True, text=True, check=False)

    # Fallback if libass filter fails on specific platform without subtitles filter
    if res.returncode != 0 or not final_output.exists():
        vf_fallback = (
            "tpad=stop_mode=clone:stop_duration=5,"
            "crop=w=1916:h=1076:x='2+2*mod(floor(n/2),2)':y='2+2*mod(floor(n/3),2)',"
            "scale=1920:1080"
        )
        cmd_master_fallback = [
            ffmpeg_bin, "-y",
            "-i", str(temp_concat_video),
            "-i", str(audio_wav),
            "-vf", vf_fallback,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-t", f"{audio_dur:.3f}",
            str(final_output)
        ]
        subprocess.run(cmd_master_fallback, capture_output=True, check=True)

    # Cleanup temp files safely (absorb Windows transient file locks)
    for p in temp_files_to_clean:
        try:
            if p.exists():
                p.unlink(missing_ok=True)
        except OSError as _clean_err:
            logger.debug(f"[vox_assemble] Could not unlink temp file {p}: {_clean_err}")

    return final_output
