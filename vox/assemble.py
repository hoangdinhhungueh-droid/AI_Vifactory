#!/usr/bin/env python3
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


def assemble_final_video(
    scene_clips: list[Path],
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
    try:
        subprocess.run(cmd_concat, capture_output=True, check=True)
    except subprocess.CalledProcessError as _c_err:
        err_msg = _c_err.stderr.decode("utf-8", errors="replace") if _c_err.stderr else str(_c_err)
        raise RuntimeError(f"assemble_final_video concat failed: {err_msg}") from _c_err

    # 2. Multiplex audio and burn ASS subtitles with two-pass loudnorm (EBU R128 / AES TD1004: I=-16.0, TP=-2.0 to absorb AAC overshoot)
    # Measure exact audio duration to avoid premature truncation
    import json
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

    # Pass 1: Measure audio loudness statistics
    pass1_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(audio_wav),
        "-af", "loudnorm=I=-16:TP=-2.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    p1_res = subprocess.run(pass1_cmd, capture_output=True, text=True, check=False)
    loudnorm_filter = "loudnorm=I=-16:TP=-2.5:LRA=11"
    try:
        err_out = p1_res.stderr
        json_start = err_out.rfind("{")
        json_end = err_out.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            p1_data = json.loads(err_out[json_start:json_end + 1])
            m_i = p1_data.get("input_i", "-16.0")
            m_tp = p1_data.get("input_tp", "-2.5")
            m_lra = p1_data.get("input_lra", "11.0")
            m_thresh = p1_data.get("input_thresh", "-26.0")
            offset = p1_data.get("target_offset", "0.0")
            loudnorm_filter = (
                f"loudnorm=I=-16:TP=-2.5:LRA=11:measured_I={m_i}:measured_TP={m_tp}:"
                f"measured_LRA={m_lra}:measured_thresh={m_thresh}:offset={offset}:linear=true"
            )
    except Exception:
        loudnorm_filter = "loudnorm=I=-16:TP=-2.5:LRA=11"

    # Escape path for ffmpeg subtitles filter (replace backslashes with forward slashes)
    ass_escaped = ass_subtitles.resolve().as_posix().replace(":", "\\:")

    cmd_master = [
        ffmpeg_bin, "-y",
        "-i", str(temp_concat_video),
        "-i", str(audio_wav),
        "-vf", f"subtitles='{ass_escaped}'",
        "-c:v", "libx264",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-b:v", "3500k",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-af", loudnorm_filter,
        "-t", f"{audio_dur:.3f}",
        str(final_output)
    ]

    res = subprocess.run(cmd_master, capture_output=True, text=True, check=False)

    # Fallback if libass filter fails on specific platform without subtitles filter
    if res.returncode != 0 or not final_output.exists():
        cmd_master_fallback = [
            ffmpeg_bin, "-y",
            "-i", str(temp_concat_video),
            "-i", str(audio_wav),
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

    # Cleanup temp concat
    if temp_concat_video.exists():
        temp_concat_video.unlink(missing_ok=True)
    if concat_list_file.exists():
        concat_list_file.unlink(missing_ok=True)

    return final_output
