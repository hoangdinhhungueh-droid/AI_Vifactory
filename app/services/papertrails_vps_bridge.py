#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/papertrails_vps_bridge.py — Papertrails VPS Playwright WebGL2 Headless Renderer (FT-302).

Orchestrates headless Three.js WebGL2 still previews and parallel video rendering on VPS Linux.
Unsets PM2 IPC env vars cleanly so child Node/Chromium processes never hit SIGABRT.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("papertrails_vps_bridge")


def _clean_pm2_env() -> Dict[str, str]:
    clean_env = os.environ.copy()
    clean_env.pop("NODE_CHANNEL_FD", None)
    clean_env.pop("NODE_CHANNEL_SERIALIZATION_MODE", None)
    clean_env.pop("NODE_APP_INSTANCE", None)
    return clean_env


def _resolve_local_audio(timeline_path: Path, t_json: Dict[str, Any]) -> Path:
    local_audio = Path(str(t_json.get("audio") or ""))
    if not local_audio.exists():
        local_audio = timeline_path.parent / "audio" / "voice_narration.mp3"
    if not local_audio.exists():
        local_audio = timeline_path.parent / "voice_narration.mp3"
    return local_audio


def _sync_timeline_and_audio_to_vps(timeline_path: Path, include_audio: bool = True) -> Dict[str, str]:
    """Uploads Papertrails timeline.json (rewritten to VPS audio path) and optional voice MP3 to VPS."""
    from scripts.upload_vps_asset import upload_file
    from scripts.vps_runner import run_vps_cmd

    ep_id = timeline_path.parent.name
    vps_run_dir = f"/root/video_factory/runs/{ep_id}"
    vps_timeline = f"{vps_run_dir}/timeline.json"
    vps_audio = f"{vps_run_dir}/voice_narration.mp3"

    run_vps_cmd(f"mkdir -p '{vps_run_dir}' /root/video_factory/vox/papertrails_engine")

    t_json = json.loads(timeline_path.read_text(encoding="utf-8"))
    local_audio = _resolve_local_audio(timeline_path, t_json)
    t_json["audio"] = vps_audio

    tmp_tl = timeline_path.with_name(".vps_timeline.tmp.json")
    try:
        tmp_tl.write_text(json.dumps(t_json, indent=2, ensure_ascii=False), encoding="utf-8")
        if not upload_file(str(tmp_tl), vps_timeline):
            raise RuntimeError(f"Failed to upload timeline.json to VPS: {vps_timeline}")
    finally:
        tmp_tl.unlink(missing_ok=True)

    if include_audio and local_audio.exists():
        chk_a = run_vps_cmd(f"stat -c %s '{vps_audio}' 2>/dev/null || echo 0")
        rem_size = int(chk_a.get("stdout", "0").strip()) if chk_a.get("stdout", "").strip().isdigit() else 0
        if rem_size == local_audio.stat().st_size:
            logger.info(f"[papertrails_vps_bridge] Audio matches VPS ({rem_size} bytes).")
        else:
            logger.info(f"[papertrails_vps_bridge] Uploading audio ({local_audio.stat().st_size} bytes) to VPS...")
            if not upload_file(str(local_audio), vps_audio):
                raise RuntimeError(f"Failed to upload audio to VPS: {vps_audio}")

    return {
        "ep_id": ep_id,
        "vps_run_dir": vps_run_dir,
        "vps_timeline": vps_timeline,
        "vps_audio": vps_audio,
    }


def render_papertrails_stills_on_vps(
    timeline_path: Path,
    stills_dir: Path,
    still_times: List[float],
    quality: str = "med",
    gpu: bool = False,
    timeout_sec: int = 600,
) -> List[Path]:
    """Renders representative Papertrails still frames fast (--stills-only) for pre-render inspection."""
    timeline_path = Path(timeline_path).resolve()
    stills_dir = Path(stills_dir).resolve()
    stills_dir.mkdir(parents=True, exist_ok=True)
    if not timeline_path.exists():
        raise FileNotFoundError(f"Timeline JSON not found: {timeline_path}")
    if not still_times:
        raise ValueError("still_times must be non-empty")

    csv_times = ",".join(f"{max(0.0, float(t)):.3f}" for t in still_times)
    is_vps_host = os.name != "nt" and Path("/root/video_factory").exists()

    if is_vps_host:
        engine_dir = Path("/root/video_factory/vox/papertrails_engine")
        prefix_mp4 = stills_dir / "stills_preview.mp4"
        cmd = [
            "node", "scripts/render.mjs", str(timeline_path), str(prefix_mp4),
            "--stills", csv_times, "--stills-only", "--quality", quality,
        ]
        if gpu:
            cmd.append("--gpu")
        res = subprocess.run(
            cmd, cwd=str(engine_dir), env=_clean_pm2_env(),
            capture_output=True, text=True, encoding="utf-8", timeout=timeout_sec,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Papertrails stills render failed (exit {res.returncode}):\n{res.stderr}")
        meta = json.loads(Path(f"{prefix_mp4}.stills.json").read_text(encoding="utf-8"))
        return [Path(item["path"]) for item in meta.get("stills", []) if Path(item["path"]).exists()]

    from scripts.download_vps_asset import download_file_chunked
    from scripts.vps_runner import run_vps_cmd

    synced = _sync_timeline_and_audio_to_vps(timeline_path, include_audio=False)
    vps_run_dir = synced["vps_run_dir"]
    vps_timeline = synced["vps_timeline"]
    vps_prefix = f"{vps_run_dir}/stills_preview.mp4"
    vps_log = f"{vps_run_dir}/stills.log"
    vps_done = f"{vps_run_dir}/stills.done"
    gpu_flag = "--gpu" if gpu else ""

    run_vps_cmd(f"rm -f '{vps_prefix}.still-'*.png '{vps_prefix}.stills.json' '{vps_log}' '{vps_done}'")
    launch_cmd = (
        f"cd /root/video_factory/vox/papertrails_engine && "
        f"env -u NODE_CHANNEL_FD -u NODE_CHANNEL_SERIALIZATION_MODE -u NODE_APP_INSTANCE "
        f"nohup bash -c \"node scripts/render.mjs '{vps_timeline}' '{vps_prefix}' "
        f"--stills '{csv_times}' --stills-only --quality {quality} {gpu_flag} > '{vps_log}' 2>&1; "
        f"echo \\$? > '{vps_done}'\" >/dev/null 2>&1 & echo $!"
    )
    logger.info(f"[papertrails_vps_bridge] Rendering {len(still_times)} preview stills on VPS (quality={quality})...")
    launch_res = run_vps_cmd(launch_cmd, timeout=30)
    if launch_res.get("exit_code", 1) != 0:
        raise RuntimeError(f"VPS stills launch failed:\nSTDOUT: {launch_res.get('stdout')}\nSTDERR: {launch_res.get('stderr')}")

    deadline = time.time() + timeout_sec
    exit_code_str = None
    while time.time() < deadline:
        poll_res = run_vps_cmd(f"if [ -f '{vps_done}' ]; then cat '{vps_done}'; fi", timeout=30)
        txt = (poll_res.get("stdout") or "").strip()
        if txt:
            exit_code_str = txt.splitlines()[-1].strip()
            break
        time.sleep(5.0)

    if exit_code_str != "0":
        tail_log = (run_vps_cmd(f"tail -n 40 '{vps_log}' 2>/dev/null || true", timeout=20).get("stdout") or "")
        raise RuntimeError(f"VPS stills render failed (exit={exit_code_str}):\n{tail_log}")

    meta_chk = run_vps_cmd(f"cat '{vps_prefix}.stills.json'")
    meta = json.loads(meta_chk.get("stdout") or "{}")
    downloaded: List[Path] = []
    for item in meta.get("stills", []):
        rem_png = item["path"]
        loc_png = stills_dir / Path(rem_png).name
        if download_file_chunked(rem_png, str(loc_png), chunk_size=5997):
            downloaded.append(loc_png)
    if not downloaded:
        raise RuntimeError("VPS stills render produced 0 downloadable still PNGs.")
    return sorted(downloaded)


def render_papertrails_on_vps(
    timeline_path: Path,
    output_mp4: Path,
    quality: str = "med",
    sfx: bool = True,
    gpu: bool = False,
    parallel_workers: int = 3,
    force_rerender: bool = False,
    timeout_sec: int = 18000,
) -> Dict[str, Any]:
    """Renders a Papertrails timeline into an MP4 video using Playwright on VPS."""
    timeline_path = Path(timeline_path).resolve()
    output_mp4 = Path(output_mp4).resolve()
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    if not timeline_path.exists():
        raise FileNotFoundError(f"Timeline JSON not found: {timeline_path}")

    is_vps_host = os.name != "nt" and Path("/root/video_factory").exists()
    if is_vps_host:
        return _render_local_vps(
            timeline_path=timeline_path,
            output_mp4=output_mp4,
            quality=quality,
            sfx=sfx,
            gpu=gpu,
            parallel_workers=parallel_workers,
            timeout_sec=timeout_sec,
        )
    return _render_via_vps_runner(
        timeline_path=timeline_path,
        output_mp4=output_mp4,
        quality=quality,
        sfx=sfx,
        gpu=gpu,
        parallel_workers=parallel_workers,
        force_rerender=force_rerender,
        timeout_sec=timeout_sec,
    )


def _render_local_vps(
    timeline_path: Path,
    output_mp4: Path,
    quality: str,
    sfx: bool,
    gpu: bool,
    parallel_workers: int,
    timeout_sec: int,
) -> Dict[str, Any]:
    """Executes render directly on Linux VPS environment."""
    engine_dir = Path("/root/video_factory/vox/papertrails_engine")
    if not engine_dir.exists():
        engine_dir = Path(__file__).resolve().parent.parent.parent / "vox" / "papertrails_engine"

    use_parallel = parallel_workers > 1 and (engine_dir / "scripts" / "render_parallel.mjs").exists()
    render_script = engine_dir / "scripts" / ("render_parallel.mjs" if use_parallel else "render.mjs")
    if not render_script.exists():
        raise FileNotFoundError(f"render script not found at: {render_script}")

    cmd = ["node", str(render_script), str(timeline_path), str(output_mp4), "--quality", quality]
    if sfx:
        cmd.append("--sfx")
    if gpu:
        cmd.append("--gpu")
    if use_parallel:
        cmd.extend(["--workers", str(parallel_workers)])

    logger.info(f"[papertrails_vps_bridge] Executing VPS render: {' '.join(cmd)}")
    t0 = time.time()
    res = subprocess.run(
        cmd, cwd=str(engine_dir), env=_clean_pm2_env(),
        capture_output=True, text=True, encoding="utf-8", timeout=timeout_sec,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Papertrails render failed (exit {res.returncode}):\nSTDERR: {res.stderr}\nSTDOUT: {res.stdout}")

    dur = time.time() - t0
    if not output_mp4.exists() or output_mp4.stat().st_size < 1000:
        raise RuntimeError(f"Output MP4 was not created or is empty: {output_mp4}")

    try:
        metadata = json.loads(res.stdout.strip())
    except (json.JSONDecodeError, ValueError):
        metadata = {
            "output_mp4": str(output_mp4),
            "size_bytes": output_mp4.stat().st_size,
            "render_time_sec": round(dur, 2),
        }
    return metadata


def _render_via_vps_runner(
    timeline_path: Path,
    output_mp4: Path,
    quality: str,
    sfx: bool,
    gpu: bool,
    parallel_workers: int,
    force_rerender: bool,
    timeout_sec: int,
) -> Dict[str, Any]:
    """Executes parallel/single Papertrails render remotely from Windows via vps_runner."""
    from scripts.download_vps_asset import download_file_chunked
    from scripts.vps_runner import run_vps_cmd

    synced = _sync_timeline_and_audio_to_vps(timeline_path)
    ep_id = synced["ep_id"]
    vps_run_dir = synced["vps_run_dir"]
    vps_timeline = synced["vps_timeline"]
    vps_output = f"{vps_run_dir}/final.mp4"
    vps_log = f"{vps_run_dir}/render.log"

    if force_rerender:
        logger.info(f"[papertrails_vps_bridge] force_rerender=True: clearing stale remote render outputs for {ep_id}")
        run_vps_cmd(f"pkill -f 'node scripts/render.*{ep_id}' || true; rm -f '{vps_output}' '{vps_output}.json' '{vps_log}'")

    stat_out = run_vps_cmd(f"stat -c %s '{vps_output}' 2>/dev/null || echo 0")
    out_size = int(stat_out.get("stdout", "0").strip()) if stat_out.get("stdout", "").strip().isdigit() else 0

    pid = None
    if out_size > 1_000_000:
        logger.info(f"[papertrails_vps_bridge] Final video already exists on VPS ({out_size} bytes). Skipping dispatch.")
    else:
        ps_chk = run_vps_cmd(f"pgrep -f 'node scripts/render(_parallel)?\\.mjs.*{ep_id}'")
        pids = [p.strip() for p in (ps_chk.get("stdout") or "").splitlines() if p.strip().isdigit()]
        if pids:
            pid = pids[0]
            logger.info(f"[papertrails_vps_bridge] Attaching to active VPS render PID {pid}...")
        else:
            run_vps_cmd(f"rm -f '{vps_log}'")
            sfx_flag = "--sfx" if sfx else ""
            gpu_flag = "--gpu" if gpu else ""
            entry = "scripts/render_parallel.mjs" if parallel_workers > 1 else "scripts/render.mjs"
            worker_flag = f"--workers {parallel_workers}" if parallel_workers > 1 else ""
            bg_cmd = (
                f"cd /root/video_factory/vox/papertrails_engine && "
                f"env -u NODE_CHANNEL_FD -u NODE_CHANNEL_SERIALIZATION_MODE -u NODE_APP_INSTANCE "
                f"nohup node {entry} '{vps_timeline}' '{vps_output}' --quality {quality} {sfx_flag} {gpu_flag} {worker_flag} > '{vps_log}' 2>&1 & echo $!"
            )
            logger.info(f"[papertrails_vps_bridge] Dispatching VPS render: {bg_cmd}")
            res = run_vps_cmd(bg_cmd, timeout=30)
            pid_str = (res.get("stdout") or "").strip()
            pid = pid_str.splitlines()[-1].strip() if pid_str else ""
            logger.info(f"[papertrails_vps_bridge] Render started with PID {pid}")

    if pid:
        poll_start = time.time()
        last_log_line = ""
        while time.time() - poll_start < timeout_sec:
            time.sleep(15)
            ps_chk = run_vps_cmd(f"ps -p {pid} -o pid=")
            running = bool((ps_chk.get("stdout") or "").strip())

            tail_chk = run_vps_cmd(f"tail -n 1 '{vps_log}'")
            latest = (tail_chk.get("stdout") or "").strip()
            if latest and latest != last_log_line:
                last_log_line = latest
                logger.info(f"[papertrails_vps_bridge] VPS: {latest}")

            if not running:
                logger.info(f"[papertrails_vps_bridge] Process PID {pid} exited.")
                break
        else:
            raise TimeoutError(f"VPS render timed out after {timeout_sec} seconds")

    chk_res = run_vps_cmd(f"stat -c %s '{vps_output}' 2>/dev/null || echo 0")
    fin_size = int(chk_res.get("stdout", "0").strip()) if (chk_res.get("stdout") or "").strip().isdigit() else 0
    if fin_size < 1000:
        err_log = (run_vps_cmd(f"tail -n 60 '{vps_log}'").get("stdout") or "")
        raise RuntimeError(f"VPS Render failed: output MP4 missing/empty at {vps_output}. Tail log:\n{err_log}")

    logger.info(f"[papertrails_vps_bridge] Downloading rendered MP4 ({fin_size:,} bytes) to {output_mp4}...")
    dl_ok = download_file_chunked(vps_output, str(output_mp4), chunk_size=5997)
    if not dl_ok or not output_mp4.exists() or output_mp4.stat().st_size != fin_size:
        raise RuntimeError(f"Failed downloading verified MP4 from VPS ({vps_output} -> {output_mp4})")

    return {
        "vps_output_path": vps_output,
        "local_output_path": str(output_mp4),
        "quality": quality,
        "parallel_workers": parallel_workers,
        "sfx": sfx,
        "size_bytes": fin_size,
    }
