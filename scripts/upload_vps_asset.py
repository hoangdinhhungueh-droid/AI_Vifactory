#!/usr/bin/env python3
"""scripts/upload_vps_asset.py — Safe direct Python hex-chunked uploader to Hetzner VPS."""

import os
import sys

# Ensure repository root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scripts.vps_runner import run_vps_cmd

def upload_file(local_path: str, vps_path: str, chunk_size: int = 12000) -> bool:
    if not os.path.exists(local_path):
        print(f"❌ Local file not found: {local_path}")
        return False

    file_bytes = open(local_path, "rb").read()
    total_size = len(file_bytes)
    print(f"📤 Uploading {local_path} ({total_size:,} bytes) ➔ {vps_path}...")

    vps_dir = os.path.dirname(vps_path).replace("\\", "/")
    init_res = run_vps_cmd(f"mkdir -p '{vps_dir}' && python3 -c \"open('{vps_path}', 'wb').close()\"")
    if init_res.get("exit_code") != 0:
        print(f"❌ Failed to initialize remote file: {init_res}")
        return False

    offset = 0
    chunk_idx = 0
    while offset < total_size:
        chunk = file_bytes[offset : offset + chunk_size]
        hex_chunk = chunk.hex()
        append_cmd = f"python3 -c \"open('{vps_path}', 'ab').write(bytes.fromhex('{hex_chunk}'))\""
        res = run_vps_cmd(append_cmd)
        if res.get("exit_code") != 0:
            print(f"\n❌ Upload failed at chunk {chunk_idx}: {res}")
            return False
        offset += len(chunk)
        chunk_idx += 1
        pct = (offset / total_size) * 100
        print(f"   [{pct:5.1f}%] {offset:,} / {total_size:,} bytes (chunk {chunk_idx})", end="\r")

    # Verify remote size
    verify_res = run_vps_cmd(f"stat -c %s '{vps_path}'")
    out = verify_res.get("stdout", "").strip()
    remote_size = int(out) if out.isdigit() else 0

    if remote_size == total_size:
        print(f"\n✅ Upload verified! Remote file size matches exactly: {remote_size:,} bytes.")
        return True
    else:
        print(f"\n❌ Size mismatch! Local: {total_size}, Remote: {remote_size}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/upload_vps_asset.py <local_path> <vps_path>")
        sys.exit(1)
    success = upload_file(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
