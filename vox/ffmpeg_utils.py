#!/usr/bin/env python3
"""vox/ffmpeg_utils.py — Dynamic FFmpeg & FFprobe Resolution Utility (AVF-VOX-001).

Resolves ffmpeg and ffprobe executable paths across Windows and Linux VPS.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_ffmpeg_binary() -> str:
    """Returns path to ffmpeg executable."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as _ff_err:
        logger.debug("imageio_ffmpeg lookup notice: %s", _ff_err)
    return "ffmpeg"


def get_ffprobe_binary() -> str:
    """Returns path to ffprobe executable."""
    found = shutil.which("ffprobe")
    if found:
        return found
    # Check if ffprobe is alongside ffmpeg
    ffmpeg_path = get_ffmpeg_binary()
    if ffmpeg_path != "ffmpeg":
        p = Path(ffmpeg_path).parent / "ffprobe.exe"
        if p.exists():
            return str(p)
    return "ffprobe"


def build_twopass_loudnorm_filter(
    ffmpeg_bin: str,
    media_path: Path,
    target_i: float = -16.0,
    target_tp: float = -2.5,
    target_lra: float = 7.0,
) -> str:
    """Runs FFmpeg pass-1 loudnorm analysis and returns calibrated pass-2 filter string."""
    base_filter = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
    pass1_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(media_path),
        "-af", f"{base_filter}:print_format=json",
        "-f", "null", "-",
    ]
    p1_res = subprocess.run(pass1_cmd, capture_output=True, text=True, check=False, timeout=120)
    err_out = p1_res.stderr or ""
    json_start = err_out.rfind("{")
    json_end = err_out.rfind("}")
    if json_start == -1 or json_end <= json_start:
        logger.debug("[ffmpeg_utils] Pass-1 loudnorm stats unavailable, falling back to 1-pass filter")
        return base_filter
    try:
        p1_data = json.loads(err_out[json_start:json_end + 1])
        m_i = p1_data.get("input_i", str(target_i))
        m_tp = p1_data.get("input_tp", str(target_tp))
        m_lra = p1_data.get("input_lra", str(target_lra))
        m_thresh = p1_data.get("input_thresh", "-26.0")
        offset = p1_data.get("target_offset", "0.0")
        return (
            f"{base_filter}:measured_I={m_i}:measured_TP={m_tp}:"
            f"measured_LRA={m_lra}:measured_thresh={m_thresh}:offset={offset}:linear=true"
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("[ffmpeg_utils] Failed parsing pass-1 loudnorm stats: %s", exc)
        return base_filter


def normalize_audio_ebur128(
    media_path: Path,
    target_i: float = -16.0,
    target_tp: float = -2.5,
    target_lra: float = 7.0,
) -> Path:
    """Normalizes an audio file in-place via two-pass EBU R128 loudnorm at 48kHz."""
    ffmpeg_bin = get_ffmpeg_binary()
    filt = build_twopass_loudnorm_filter(
        ffmpeg_bin, media_path, target_i=target_i, target_tp=target_tp, target_lra=target_lra
    )
    tmp_out = media_path.with_name(f".loudnorm_{media_path.name}")
    codec_args = ["-c:a", "libmp3lame", "-b:a", "192k"] if media_path.suffix.lower() == ".mp3" else ["-c:a", "aac", "-b:a", "192k"]
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(media_path),
        "-ar", "48000",
        "-af", filt,
        *codec_args,
        str(tmp_out),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=180)
    if tmp_out.exists() and tmp_out.stat().st_size > 1000:
        tmp_out.replace(media_path)
    return media_path
