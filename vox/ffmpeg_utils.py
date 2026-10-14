#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/ffmpeg_utils.py — Dynamic FFmpeg & FFprobe Resolution Utility (AVF-VOX-001).

Resolves ffmpeg and ffprobe executable paths across Windows and Linux VPS.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def get_ffmpeg_binary() -> str:
    """Returns path to ffmpeg executable."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
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
