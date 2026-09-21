#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/download_from_vps.py
Download a remote file from VPS to local via FastVPSClient chunking.
"""
import base64
import sys
import os
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.vps_runner import FastVPSClient

def download_file(vps_path: str, local_path: str, chunk_size: int = 5000):
    client = FastVPSClient()
    print(f"Checking remote file {vps_path}...")
    res = client.call_tool("run_command", {"command": f"test -f '{vps_path}' && wc -c < '{vps_path}' || echo 'NOT_FOUND'"})
    out = (res.get("stdout") or "").strip()
    if out == "NOT_FOUND" or not out.isdigit():
        print(f"Error: {vps_path} does not exist on VPS. Output: {out}", file=sys.stderr)
        return False

    total_bytes = int(out)
    print(f"Remote file size: {total_bytes} bytes. Generating base64 on VPS...")

    tmp_b64 = f"/tmp/dl_{Path(vps_path).name}.b64"
    client.call_tool("run_command", {"command": f"base64 -w 0 '{vps_path}' > '{tmp_b64}'"})

    res_len = client.call_tool("run_command", {"command": f"wc -c < '{tmp_b64}'"})
    b64_len = int((res_len.get("stdout") or "0").strip())
    print(f"Base64 length: {b64_len} characters. Downloading in chunks of {chunk_size}...")

    b64_parts = []
    offset = 0
    while offset < b64_len:
        py_cmd = f"python3 -c \"with open('{tmp_b64}', 'r') as f: f.seek({offset}); print(f.read({chunk_size}), end='')\""
        chunk_res = client.call_tool("run_command", {"command": py_cmd})
        chunk_text = chunk_res.get("stdout") or ""
        b64_parts.append(chunk_text)
        offset += len(chunk_text)
        if not chunk_text:
            break

    full_b64 = "".join(b64_parts)
    print(f"Downloaded {len(full_b64)} base64 chars. Cleaning up remote tmp...")
    client.call_tool("run_command", {"command": f"rm -f '{tmp_b64}'"})

    try:
        raw_bytes = base64.b64decode(full_b64)
    except Exception as e:
        print(f"Base64 decode error: {e}", file=sys.stderr)
        return False

    out_p = Path(local_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_bytes(raw_bytes)
    print(f"Successfully saved to {local_path} ({len(raw_bytes)} bytes)")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/download_from_vps.py <vps_path> <local_path>")
        sys.exit(1)
    success = download_file(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
