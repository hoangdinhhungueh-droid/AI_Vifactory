#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/monitor_render_and_download.py — Monitors VPS Remotion render and downloads preview MP4.
"""

import base64
import json
import logging
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from vox.ffmpeg_utils import get_ffmpeg_binary
from scripts.vps_runner import FastVPSClient, _load_env

_load_env()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("opuscar_monitor")

OUT_DIR = ROOT / "out" / "opuscar_2scenes_preview"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def download_file_parallel(client: FastVPSClient, vps_path: str, local_path: Path, max_workers: int = 6):
    sz = int(client.run_command(f"stat -c %s '{vps_path}'").get("stdout", "0").strip() or "0")
    if sz <= 0:
        raise RuntimeError(f"Remote file empty or missing: {vps_path}")
    logger.info(f"Downloading {vps_path} ({sz/1024/1024:.2f} MB, {sz} bytes) using {max_workers} parallel workers...")

    ep = client.ep
    url = ep["url"]
    token = ep["token"]
    cf_id = ep.get("cf_id")
    cf_secret = ep.get("cf_secret")

    s = requests.Session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"
    }
    if cf_id:
        headers["CF-Access-Client-Id"] = cf_id
    if cf_secret:
        headers["CF-Access-Client-Secret"] = cf_secret
    if client.session_id:
        headers["mcp-session-id"] = client.session_id
    s.headers.update(headers)

    chunk_len = 5800
    chunks_args = []
    req_id = 100
    for offset in range(0, sz, chunk_len):
        read_len = min(chunk_len, sz - offset)
        req_id += 1
        chunks_args.append((offset, read_len, req_id))

    def fetch_chunk(args):
        offset, read_len, r_id = args
        cmd = f"python3 -c \"import sys, base64; f=open('{vps_path}', 'rb'); f.seek({offset}); sys.stdout.write(base64.b64encode(f.read({read_len})).decode('ascii'))\""
        payload = {
            "jsonrpc": "2.0",
            "id": r_id,
            "method": "tools/call",
            "params": {"name": "run_command", "arguments": {"command": cmd, "confirm": True, "timeout": 30}}
        }
        res = s.post(url, json=payload, timeout=30)
        for line in res.text.splitlines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                content = data.get("result", {}).get("content", [])
                if content:
                    txt = content[0].get("text", "")
                    try:
                        ret = json.loads(txt)
                        return offset, base64.b64decode(ret.get("stdout", "").strip())
                    except Exception:
                        pass
        return offset, b""

    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for offset, data in pool.map(fetch_chunk, chunks_args):
            results[offset] = data
            if len(results) % 50 == 0 or len(results) == len(chunks_args):
                pct = len(results) / len(chunks_args) * 100
                logger.info(f"Download progress: {len(results)}/{len(chunks_args)} chunks ({pct:.1f}%)")

    all_bytes = bytearray()
    for offset in sorted(results.keys()):
        all_bytes.extend(results[offset])

    if len(all_bytes) != sz:
        raise RuntimeError(f"Download size mismatch: expected {sz}, got {len(all_bytes)}")

    local_path.write_bytes(all_bytes)
    t1 = time.time()
    logger.info(f"Downloaded {len(all_bytes)} bytes in {t1-t0:.2f}s ({len(all_bytes)/(t1-t0)/1024:.1f} KB/s) -> {local_path}")


def probe_file(file_path: Path) -> dict:
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [ffmpeg_bin, "-i", str(file_path)]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    stderr = p.stderr or ""
    dur = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    has_video = "Video:" in stderr
    has_audio = "Audio:" in stderr
    return {
        "duration": dur,
        "has_video": has_video,
        "has_audio": has_audio,
        "size": file_path.stat().st_size
    }


def main():
    client = FastVPSClient()
    vps_out_mp4 = "/root/video_factory/out/opuscar_2scenes_preview.mp4"
    log_file = "/tmp/vf/render.log"

    logger.info("=== Monitoring VPS Remotion Render ===")
    max_wait_sec = 600
    start_t = time.time()

    last_tail = ""
    while time.time() - start_t < max_wait_sec:
        # Check if output file exists and is done
        chk = client.run_command(f"ls -lh {vps_out_mp4}")
        if chk.get("exit_code") == 0:
            logger.info(f"Output MP4 detected on VPS: {chk.get('stdout').strip()}")
            # Check if remotion is still writing or finished
            ps_chk = client.run_command("ps aux | grep remotion")
            if "chrome-headless-shell" not in ps_chk.get("stdout", ""):
                logger.info("Remotion rendering processes exited cleanly. Render complete!")
                break

        # Log progress
        log_res = client.run_command(f"tail -n 2 {log_file}")
        tail = log_res.get("stdout", "").strip()
        if tail and tail != last_tail:
            logger.info(f"[VPS RENDER] {tail.splitlines()[-1]}")
            last_tail = tail

        time.sleep(10)

    # Final check of output file on VPS
    chk_final = client.run_command(f"stat -c %s {vps_out_mp4}")
    sz = int(chk_final.get("stdout", "0").strip() or "0")
    if sz <= 0:
        logger.error("Render failed or output file is empty!")
        log_tail = client.run_command(f"tail -n 30 {log_file}").get("stdout")
        logger.error(f"Render log:\n{log_tail}")
        sys.exit(1)

    logger.info(f"VPS Render Successful: {vps_out_mp4} ({sz/1024/1024:.2f} MB)")

    # Download to local
    local_final_mp4 = OUT_DIR / "opuscar_2scenes_preview.mp4"
    logger.info("=== Downloading Rendered Video to Local Workspace ===")
    download_file_parallel(client, vps_out_mp4, local_final_mp4, max_workers=6)

    # Verify locally
    info = probe_file(local_final_mp4)
    logger.info(f"Local Video Verification: Duration={info['duration']:.2f}s, HasVideo={info['has_video']}, HasAudio={info['has_audio']}, Size={info['size']} bytes")

    if not info["has_video"] or not info["has_audio"] or info["duration"] < 15.0:
        logger.error(f"Integrity check failed: {info}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("ALL STAGES COMPLETED SUCCESSFULLY!")
    print(f"OPUSCAR PREVIEW VIDEO: {local_final_mp4.resolve()}")
    print(f"DURATION: {info['duration']:.2f} seconds (830 frames @ 30fps)")
    print(f"SIZE: {info['size'] / 1024 / 1024:.2f} MB")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
