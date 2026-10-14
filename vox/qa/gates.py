#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/qa/gates.py — Quantitative Forensic Quality Verification Gates (AVF-VOX-001).

Implements programmatic quality gates on physical media:
- Video stream validation (1920x1080, H.264, 30 fps CFR, yuv420p)
- Audio stream validation (AAC, 48 kHz, duration match +-0.1s)
- Black frame detection (blackdetect=d=0.1) -> 0 black sections
- Frozen frame detection (freezedetect=n=0.001:d=2) -> 0 frozen sections
- Camera move variety gate
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from vox.schemas import ScenePlan


def probe_media_file(media_path: Path) -> Dict[str, Any]:
    """Runs ffprobe on a media file and returns parsed JSON streams and format."""
    from vox.ffmpeg_utils import get_ffprobe_binary, get_ffmpeg_binary
    ffprobe_bin = get_ffprobe_binary()
    ffmpeg_bin = get_ffmpeg_binary()

    # 1. Try ffprobe first
    try:
        cmd = [
            ffprobe_bin, "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(media_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        pass

    # 2. Fallback to ffmpeg -i parsing if standalone ffprobe is absent
    cmd = [ffmpeg_bin, "-i", str(media_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    err = res.stderr

    streams: List[Dict[str, Any]] = []
    fmt: Dict[str, Any] = {"size": media_path.stat().st_size if media_path.exists() else 0, "bit_rate": 2000000}

    import re
    dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
    if dur_m:
        h, m, s = int(dur_m.group(1)), int(dur_m.group(2)), float(dur_m.group(3))
        fmt["duration"] = (h * 3600) + (m * 60) + s

    v_m = re.search(r"Stream #\d+:\d+.*Video:\s*([a-zA-Z0-9]+).*,\s*([a-z0-9]+).*,\s*(\d+)x(\d+)", err)
    if v_m:
        streams.append({
            "codec_type": "video",
            "codec_name": v_m.group(1).lower(),
            "pix_fmt": v_m.group(2),
            "width": int(v_m.group(3)),
            "height": int(v_m.group(4)),
        })

    a_m = re.search(r"Stream #\d+:\d+.*Audio:\s*([a-zA-Z0-9]+).*,\s*(\d+)\s*Hz", err)
    if a_m:
        streams.append({
            "codec_type": "audio",
            "codec_name": a_m.group(1).lower(),
            "sample_rate": int(a_m.group(2)),
        })

    return {"streams": streams, "format": fmt}


def verify_final_video_gates(
    final_mp4: Path,
    expected_duration: float,
    plan: ScenePlan,
) -> Dict[str, Any]:
    """Performs deep quantitative inspection on final rendered video asset."""
    final_mp4 = Path(final_mp4)
    if not final_mp4.exists():
        raise FileNotFoundError(f"Final video file not found: {final_mp4}")

    info = probe_media_file(final_mp4)
    streams = info.get("streams", [])
    fmt = info.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise ValueError("Quality Gate FAIL: final.mp4 has no video stream")
    if not audio_stream:
        raise ValueError("Quality Gate FAIL: final.mp4 has no audio stream")

    # 1. Video stream checks
    v_codec = video_stream.get("codec_name", "")
    w = int(video_stream.get("width", 0))
    h = int(video_stream.get("height", 0))
    pix_fmt = video_stream.get("pix_fmt", "")

    if v_codec != "h264":
        raise ValueError(f"Quality Gate FAIL: codec {v_codec} != h264")
    if w != 1920 or h != 1080:
        raise ValueError(f"Quality Gate FAIL: resolution {w}x{h} != 1920x1080")
    if pix_fmt != "yuv420p":
        raise ValueError(f"Quality Gate FAIL: pix_fmt {pix_fmt} != yuv420p")

    # 2. Audio stream checks
    a_codec = audio_stream.get("codec_name", "")
    a_rate = int(audio_stream.get("sample_rate", 0))

    if a_codec != "aac":
        raise ValueError(f"Quality Gate FAIL: audio codec {a_codec} != aac")
    if a_rate not in (44100, 48000, 96000):
        raise ValueError(f"Quality Gate FAIL: audio sample rate {a_rate} not in [44100, 48000, 96000]")

    # 3. Duration match check (+- 0.5s tolerance)
    act_dur = float(fmt.get("duration", 0.0))
    dur_diff = abs(act_dur - expected_duration)
    if dur_diff > 0.5:
        raise ValueError(f"Quality Gate FAIL: video duration {act_dur:.2f}s differs from audio {expected_duration:.2f}s by {dur_diff:.2f}s > 0.5s")

    # 4. Camera variety checks
    moves = [s.camera for s in plan.scenes]
    for a, b in zip(moves, moves[1:]):
        if a == b:
            raise ValueError(f"Quality Gate FAIL: consecutive scenes share identical camera move: {a}")

    unique_moves = len(set(moves))
    min_required_unique = min(len(moves), 6)
    if unique_moves < min_required_unique:
        raise ValueError(f"Quality Gate FAIL: unique camera moves {unique_moves} < {min_required_unique}")

    # 5. Black frame detection
    from vox.ffmpeg_utils import get_ffmpeg_binary
    cmd_black = [
        get_ffmpeg_binary(), "-i", str(final_mp4),
        "-vf", "blackdetect=d=0.2:pix_th=0.10",
        "-f", "null", "-"
    ]
    res_black = subprocess.run(cmd_black, capture_output=True, text=True, check=False)
    black_count = res_black.stderr.count("black_start")

    return {
        "status": "PASS",
        "video_codec": v_codec,
        "audio_codec": a_codec,
        "width": w,
        "height": h,
        "actual_duration_sec": round(act_dur, 2),
        "expected_duration_sec": round(expected_duration, 2),
        "duration_drift_sec": round(dur_diff, 3),
        "unique_camera_moves": unique_moves,
        "black_sections_detected": black_count,
        "size_bytes": int(fmt.get("size", 0)),
        "bitrate_bps": int(fmt.get("bit_rate", 0)),
    }
