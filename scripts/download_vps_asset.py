#!/usr/bin/env python3
"""scripts/download_vps_asset.py — Safe chunked downloader from Hetzner VPS via vps_runner."""

import base64
import os
import subprocess
import sys

def download_file_chunked(vps_path: str, local_path: str, chunk_size: int = 3500) -> bool:
    # 1. Get total size
    cmd_size = f"stat -c %s {vps_path}"
    res = subprocess.run(["python", "scripts/vps_runner.py", cmd_size], capture_output=True, text=True, encoding="utf-8")
    size_str = ""
    rec = False
    for line in res.stdout.splitlines():
        if line.startswith("STDOUT:"):
            rec = True
            continue
        if line.startswith("STDERR:") or line.startswith("EXIT_CODE:"):
            rec = False
            continue
        if rec and line.strip().isdigit():
            size_str = line.strip()
            break
            
    if not size_str:
        print(f"❌ Cannot get size for {vps_path}: {res.stderr}")
        return False
        
    total_size = int(size_str)
    print(f"📥 Downloading {vps_path} ({total_size:,} bytes) ➔ {local_path}...")

    os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
    with open(local_path, "wb") as out_f:
        offset = 0
        while offset < total_size:
            read_len = min(chunk_size, total_size - offset)
            snippet = f"import sys, base64; f=open('{vps_path}', 'rb'); f.seek({offset}); sys.stdout.write(base64.b64encode(f.read({read_len})).decode())"
            py_cmd = f"python3 -c \"{snippet}\""
            res = subprocess.run(["python", "scripts/vps_runner.py", py_cmd], capture_output=True, text=True, encoding="utf-8")
            b64_part = ""
            rec = False
            for line in res.stdout.splitlines():
                if line.startswith("STDOUT:"):
                    rec = True
                    continue
                if line.startswith("STDERR:") or line.startswith("EXIT_CODE:"):
                    rec = False
                    continue
                if rec:
                    b64_part += line.strip()
            if not b64_part:
                print(f"❌ Failed to fetch chunk at offset {offset}")
                return False
            raw_chunk = base64.b64decode(b64_part)
            out_f.write(raw_chunk)
            offset += len(raw_chunk)
            pct = (offset / total_size) * 100
            print(f"   [{pct:5.1f}%] {offset:,} / {total_size:,} bytes", end="\r")
    print(f"\n✅ Finished downloading {local_path} ({os.path.getsize(local_path):,} bytes).")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/download_vps_asset.py <vps_path> <local_path>")
        sys.exit(1)
    success = download_file_chunked(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
