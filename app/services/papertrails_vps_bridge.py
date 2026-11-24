#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/papertrails_vps_bridge.py — Papertrails VPS Playwright WebGL2 Headless Renderer (FT-302).

Orchestrates headless Three.js WebGL2 video rendering on VPS Linux using Playwright.
Streams deterministic frames directly into FFmpeg and muxes audio with 0ms drift.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("papertrails_vps_bridge")


def render_papertrails_on_vps(
    timeline_path: Path,
    output_mp4: Path,
    quality: str = "high",
    sfx: bool = True,
    gpu: bool = False,
    timeout_sec: int = 900,
) -> Dict[str, Any]:
    """Renders a Papertrails timeline into an MP4 video using Playwright on VPS.

    Args:
        timeline_path: Path to timeline.json.
        output_mp4: Target path for output MP4.
        quality: 'low', 'med', or 'high'.
        sfx: Whether to synthesize tactile paper-flip sound effects at cuts.
        gpu: Whether to pass GPU acceleration flags.
        timeout_sec: Maximum execution timeout in seconds.

    Returns:
        Dict with render metadata (duration, frames, fps, file_path).
    """
    timeline_path = Path(timeline_path).resolve()
    output_mp4 = Path(output_mp4).resolve()
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    if not timeline_path.exists():
        raise FileNotFoundError(f"Timeline JSON not found: {timeline_path}")

    # Detect if we are running directly on VPS or locally via vps_runner
    is_vps_host = Path("/root/video_factory").exists()

    if is_vps_host:
        return _render_local_vps(
            timeline_path=timeline_path,
            output_mp4=output_mp4,
            quality=quality,
            sfx=sfx,
            gpu=gpu,
            timeout_sec=timeout_sec,
        )
    else:
        return _render_via_vps_runner(
            timeline_path=timeline_path,
            output_mp4=output_mp4,
            quality=quality,
            sfx=sfx,
            gpu=gpu,
            timeout_sec=timeout_sec,
        )


def _render_local_vps(
    timeline_path: Path,
    output_mp4: Path,
    quality: str,
    sfx: bool,
    gpu: bool,
    timeout_sec: int,
) -> Dict[str, Any]:
    """Executes render directly on Linux VPS environment."""
    engine_dir = Path("/root/video_factory/vox/papertrails_engine")
    if not engine_dir.exists():
        engine_dir = Path(__file__).resolve().parent.parent.parent / "vox" / "papertrails_engine"

    render_script = engine_dir / "scripts" / "render.mjs"
    if not render_script.exists():
        raise FileNotFoundError(f"render.mjs not found at: {render_script}")

    cmd = [
        "node",
        str(render_script),
        str(timeline_path),
        str(output_mp4),
        "--quality", quality,
    ]
    if sfx:
        cmd.append("--sfx")
    if gpu:
        cmd.append("--gpu")

    logger.info(f"[papertrails_vps_bridge] Executing VPS render: {' '.join(cmd)}")
    t0 = time.time()
    res = subprocess.run(
        cmd,
        cwd=str(engine_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_sec,
    )

    if res.returncode != 0:
        raise RuntimeError(
            f"Papertrails render failed (exit {res.returncode}):\nSTDERR: {res.stderr}\nSTDOUT: {res.stdout}"
        )

    dur = time.time() - t0
    logger.info(f"[papertrails_vps_bridge] VPS render completed in {dur:.2f}s")

    # Verify output file
    if not output_mp4.exists() or output_mp4.stat().st_size < 1000:
        raise RuntimeError(f"Output MP4 was not created or is empty: {output_mp4}")

    # Parse stdout JSON if available
    metadata: Dict[str, Any] = {}
    try:
        metadata = json.loads(res.stdout.strip())
    except Exception:
        metadata = {
            "output_mp4": str(output_mp4),
            "size_bytes": output_mp4.stat().st_size,
            "render_time_sec": dur,
        }

    return metadata


def _render_via_vps_runner(
    timeline_path: Path,
    output_mp4: Path,
    quality: str,
    sfx: bool,
    gpu: bool,
    timeout_sec: int,
) -> Dict[str, Any]:
    """Executes render remotely from Windows workstation to VPS via vps_runner."""
    from scripts.vps_runner import run_vps_command

    vps_episodes_dir = Path("/root/video_factory/runs")
    ep_id = timeline_path.parent.name
    vps_run_dir = f"/root/video_factory/runs/{ep_id}"
    vps_timeline = f"{vps_run_dir}/timeline.json"
    vps_output = f"{vps_run_dir}/final.mp4"

    # 1. Read timeline content and write to VPS
    t_content = timeline_path.read_text(encoding="utf-8")
    t_json = json.loads(t_content)

    # In timeline JSON on VPS, ensure audio points to VPS audio file
    vps_audio = f"{vps_run_dir}/voice_narration.mp3"
    t_json["audio"] = vps_audio
    vps_timeline_content = json.dumps(t_json, indent=2, ensure_ascii=False)

    setup_cmd = f"mkdir -p {vps_run_dir} /root/video_factory/vox/papertrails_engine"
    run_vps_command(setup_cmd)

    # Upload timeline.json to VPS
    # Using python base64 write on VPS to avoid shell escaping issues
    import base64
    b64_timeline = base64.b64encode(vps_timeline_content.encode("utf-8")).decode("ascii")
    write_cmd = f"python3 -c 'import base64; open(\"{vps_timeline}\", \"wb\").write(base64.b64decode(\"{b64_timeline}\"))'"
    run_vps_command(write_cmd)

    # If audio exists locally, upload it if needed
    local_audio = Path(t_json.get("audio", ""))
    if not local_audio.exists():
        local_audio = timeline_path.parent / "audio" / "voice_narration.mp3"
    if not local_audio.exists():
        local_audio = timeline_path.parent / "voice_narration.mp3"

    if local_audio.exists():
        b64_audio = base64.b64encode(local_audio.read_bytes()).decode("ascii")
        write_audio_cmd = f"python3 -c 'import base64; open(\"{vps_audio}\", \"wb\").write(base64.b64decode(\"{b64_audio}\"))'"
        run_vps_command(write_audio_cmd)

    # 2. Trigger render script on VPS
    sfx_flag = "--sfx" if sfx else ""
    gpu_flag = "--gpu" if gpu else ""
    render_cmd = (
        f"cd /root/video_factory/vox/papertrails_engine && "
        f"node scripts/render.mjs {vps_timeline} {vps_output} --quality {quality} {sfx_flag} {gpu_flag}"
    )

    logger.info(f"[papertrails_vps_bridge] Dispatching render to VPS: {render_cmd}")
    stdout, stderr, code = run_vps_command(render_cmd, timeout_seconds=timeout_sec)
    if code != 0:
        raise RuntimeError(f"VPS Render failed (exit {code}):\nSTDERR: {stderr}\nSTDOUT: {stdout}")

    logger.info("[papertrails_vps_bridge] VPS Render command succeeded.")

    # 3. Retrieve output MP4 from VPS to local output_mp4
    download_cmd = f"python3 -c 'import base64; print(base64.b64encode(open(\"{vps_output}\", \"rb\").read()).decode(\"ascii\"))'"
    b64_out, b_err, b_code = run_vps_command(download_cmd, timeout_seconds=120)
    if b_code == 0 and b64_out.strip():
        output_mp4.write_bytes(base64.b64decode(b64_out.strip()))
        logger.info(f"[papertrails_vps_bridge] Downloaded final.mp4 ({output_mp4.stat().st_size} bytes)")
    else:
        logger.warning(f"Could not retrieve video payload directly: {b_err}")

    return {
        "vps_output_path": vps_output,
        "local_output_path": str(output_mp4) if output_mp4.exists() else None,
        "quality": quality,
        "sfx": sfx,
    }
