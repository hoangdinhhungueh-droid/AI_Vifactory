#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/trigger_video_generation.py — Human Gate Video Trigger Command.

Lệnh chuyên dụng kích hoạt sinh video Veo 3.1 xoay vòng 7 tài khoản
sau khi đã qua Human Gate / Antigravity Review.

Tuân thủ:
- Rule 118: Zero-mock, chỉ sinh video thật từ Google Flow.
- Rule 121: Forensic verification (kiểm tra tồn tại, kích thước file).
- Rule 126: Three-way physical sync (Local -> VPS).
"""

from __future__ import annotations

import os
import sys
import argparse
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Human Gate Video Trigger Command (Veo 3.1 Fast - 7 Accounts)")
    parser.add_argument("--episode", required=True, help="Episode ID (e.g. KR_EP0001_google_kr_tax_loss)")
    parser.add_argument("--acc", default="all", help="Tài khoản Google Flow (acc_01 đến acc_07 hoặc all)")
    parser.add_argument("--limit-blocks", type=int, default=0, help="Giới hạn số cụm block cần sinh video")
    parser.add_argument("--limit-scenes", type=int, default=0, help="Giới hạn số cảnh cần sinh video")
    parser.add_argument("--model", choices=["omni", "veo"], default="omni", help="Mô hình video: omni (Omni 1.1 Flash) hoặc veo (Veo 3.1 - Fast)")
    parser.add_argument("--headless", action="store_true", help="Chạy ngầm browser")
    args = parser.parse_args()

    clean_ep = args.episode.strip().strip("'\"")
    if clean_ep.lower().startswith("task:"):
        clean_ep = clean_ep[5:].strip()

    model_name = "Omni 1.1 Flash" if args.model == "omni" else "Veo 3.1 - Fast"
    print("\n" + "=" * 75)
    print(f"🎬 [TRIGGER COMMAND] KÍCH HOẠT SINH VIDEO {model_name.upper()} — EPISODE: {clean_ep}")
    print(f"   Mô hình: {model_name}")
    print(f"   Tài khoản: {args.acc}")
    print(f"   Giới hạn block: {args.limit_blocks if args.limit_blocks > 0 else 'Toàn bộ'}")
    print(f"   Giới hạn cảnh: {args.limit_scenes if args.limit_scenes > 0 else 'Toàn bộ'}")
    print("=" * 75)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_vox_media_pipeline.py"),
        "--episode", clean_ep,
        "--stage", "video",
        "--trigger-video",
        "--acc", args.acc,
        "--model", args.model
    ]
    if args.limit_blocks > 0:
        cmd.extend(["--limit-blocks", str(args.limit_blocks)])
    if args.limit_scenes > 0:
        cmd.extend(["--limit-scenes", str(args.limit_scenes)])
    if args.headless:
        cmd.append("--headless")

    print(f"🚀 Thực thi lệnh điều phối: {' '.join(cmd)}\n")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


if __name__ == "__main__":
    main()
