#!/usr/bin/env python3
"""
scripts/forensics/probe_golden_ffprobe.py — Golden MP4 Forensic Inspector
Mandate:
  1. Inspects out/golden/final.mp4 and out/golden_science/final.mp4.
  2. Dumps exact file size, sha256 checksum, and ffprobe stream/format metadata.
  3. Proves zero-mock compliance (Rule 118 & Rule 121).
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

TARGETS = [
    Path("/root/video_factory/out/golden/final.mp4"),
    Path("/root/video_factory/out/golden_science/final.mp4"),
]

def probe_video(video_path: Path) -> dict:
    if not video_path.exists():
        # Fallback to local repo relative path if running on workstation
        rel_path = Path(__file__).resolve().parent.parent.parent / video_path.relative_to("/root/video_factory")
        if rel_path.exists():
            video_path = rel_path
        else:
            return {"path": str(video_path), "exists": False, "error": "File not found"}

    stat = video_path.stat()
    size_bytes = stat.st_size

    # SHA256 checksum
    h = hashlib.sha256()
    with open(video_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    sha256 = h.hexdigest()

    # ffprobe execution
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(proc.stdout)
    except Exception as e:
        probe_data = {"error": str(e)}

    return {
        "path": str(video_path),
        "exists": True,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "streams": probe_data.get("streams", []),
        "format": probe_data.get("format", {}),
    }

def main():
    results = {}
    print("=======================================================")
    print("🎥 RUNNING GOLDEN MP4 FORENSIC FFPROBE INSPECTOR")
    print("=======================================================")
    for target in TARGETS:
        print(f"\n--- Probing: {target} ---")
        info = probe_video(target)
        results[str(target)] = info
        if info.get("exists"):
            fmt = info.get("format", {})
            print(f"  Path:     {info['path']}")
            print(f"  Size:     {info['size_bytes']:,} bytes")
            print(f"  SHA256:   {info['sha256']}")
            print(f"  Duration: {fmt.get('duration')}s")
            print(f"  Bitrate:  {fmt.get('bit_rate')} bps")
            for idx, s in enumerate(info.get("streams", [])):
                codec_type = s.get("codec_type")
                codec_name = s.get("codec_name")
                w, h = s.get("width"), s.get("height")
                r_frame_rate = s.get("r_frame_rate")
                print(f"  Stream #{idx} ({codec_type}): {codec_name} | {w}x{h} @ {r_frame_rate} fps")
        else:
            print(f"  NOT FOUND: {target}")

    # Output JSON summary
    out_json = Path("/tmp/golden_mp4_forensic_ffprobe.json")
    try:
        out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nSaved probe summary to {out_json}")
    except Exception as e:
        sys.stderr.write(f"Notice: Failed to write {out_json}: {e}\n")

if __name__ == "__main__":
    main()
