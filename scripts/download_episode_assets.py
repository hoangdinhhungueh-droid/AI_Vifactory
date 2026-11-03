#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/download_episode_assets.py — Downloads episode plan & manifests from VPS to local."""

import argparse
import base64
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.vps_runner import FastVPSClient


def download_vps_file(client: FastVPSClient, vps_path: str, local_path: Path) -> int:
    res = client.run_command(f'gzip -c "{vps_path}" | base64 -w 0 > /tmp/dl.b64 && wc -c < /tmp/dl.b64')
    size_str = res.get("stdout", "0").strip()
    if not size_str.isdigit() or int(size_str) == 0:
        print(f"Warning: file {vps_path} not found or empty on VPS: {res.get('stderr')}")
        return 0
    size = int(size_str)
    CHUNK = 6000
    b64_total = ""
    offset = 0
    while offset < size:
        count = min(CHUNK, size - offset)
        c_res = client.run_command(f"tail -c +{offset+1} /tmp/dl.b64 | head -c {count}")
        b64_total += c_res.get("stdout", "").strip()
        offset += count
    client.run_command("rm -f /tmp/dl.b64")
    raw = gzip.decompress(base64.b64decode(b64_total))
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(raw)
    print(f"Downloaded {vps_path} ({len(raw)} bytes) -> {local_path}")
    return len(raw)


def main():
    parser = argparse.ArgumentParser(description="Download episode plan from VPS")
    parser.add_argument("--episode", required=True, help="Episode ID")
    args = parser.parse_args()

    client = FastVPSClient()
    target_dir = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\browser_assets") / args.episode
    vps_ep_dir = f"/var/vf/episodes/{args.episode}"

    files_to_download = [
        "director_plan.json",
        "bulk_image_prompts.txt",
        "flow_video_manifest.json",
        "spoken_script.txt",
        "run_manifest.json"
    ]

    for fname in files_to_download:
        download_vps_file(client, f"{vps_ep_dir}/{fname}", target_dir / fname)


if __name__ == "__main__":
    main()
