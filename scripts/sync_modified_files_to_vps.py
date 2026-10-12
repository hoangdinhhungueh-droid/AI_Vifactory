#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/sync_modified_files_to_vps.py
Uploads modified files from local Windows repo to VPS /root/video_factory.
Uses /tmp/vf/writer.py helper to write cleanly in safe 20KB chunks.
Verifies bit-for-bit SHA256 parity and compiles python files.
"""
import base64
import hashlib
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.vps_runner import run_vps_cmd

def get_modified_files():
    res = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=str(_ROOT)).decode("utf-8")
    files = [line.strip().replace("\\", "/") for line in res.splitlines() if line.strip()]
    if not files:
        res = subprocess.check_output(["git", "status", "-s"], cwd=str(_ROOT)).decode("utf-8")
        for line in res.splitlines():
            if line[:2].strip() in ("M", "A", "AM", "MM"):
                rel = line[3:].strip().replace("\\", "/")
                files.append(rel)
    return sorted(list(set(files)))

def main():
    files_to_sync = get_modified_files()
    print(f"🚀 Starting sync of {len(files_to_sync)} modified files to VPS /root/video_factory...")
    chunk_size = 20000

    # Ensure /tmp/vf/writer.py exists on VPS
    ensure_writer = """python3 -c "
import os
os.makedirs('/tmp/vf', exist_ok=True)
with open('/tmp/vf/writer.py', 'w') as f:
    f.write('''import sys, base64, os
mode = sys.argv[1]
path = sys.argv[2]
b64_data = sys.argv[3]
os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
data = base64.b64decode(b64_data)
if mode == 'write':
    with open(path, 'wb') as f:
        f.write(data)
elif mode == 'append':
    with open(path, 'ab') as f:
        f.write(data)
''')
" """
    run_vps_cmd(ensure_writer)

    for idx_f, rel_path in enumerate(files_to_sync, 1):
        local_file = _ROOT / rel_path
        if not local_file.exists():
            print(f"❌ File not found locally: {local_file}")
            sys.exit(1)

        raw_bytes = local_file.read_bytes()
        local_sha = hashlib.sha256(raw_bytes).hexdigest()
        b64_content = base64.b64encode(raw_bytes).decode("ascii")
        target_path = f"/root/video_factory/{rel_path}"

        chunks = [b64_content[i:i+chunk_size] for i in range(0, len(b64_content), chunk_size)]
        
        # First chunk: "write" mode
        cmd = f"python3 /tmp/vf/writer.py write '{target_path}' '{chunks[0]}'"
        res = run_vps_cmd(cmd)
        if isinstance(res, dict) and res.get("exit_code", 0) != 0:
            print(f"❌ Failed write for {rel_path}: {res.get('stderr')}")
            sys.exit(1)

        # Subsequent chunks: "append" mode
        for idx, chunk in enumerate(chunks[1:], start=2):
            cmd = f"python3 /tmp/vf/writer.py append '{target_path}' '{chunk}'"
            res = run_vps_cmd(cmd)
            if isinstance(res, dict) and res.get("exit_code", 0) != 0:
                print(f"❌ Failed append chunk {idx} for {rel_path}: {res.get('stderr')}")
                sys.exit(1)

        # Check sha256 on VPS
        sha_cmd = f"sha256sum '{target_path}'"
        sha_res = run_vps_cmd(sha_cmd)
        vps_sha = ""
        if isinstance(sha_res, dict):
            out = sha_res.get("stdout", "").strip()
            if out:
                vps_sha = out.split()[0]

        if local_sha != vps_sha:
            print(f"❌ SHA256 MISMATCH for {rel_path}: local={local_sha} vs vps={vps_sha}")
            sys.exit(1)

        print(f"[{idx_f}/{len(files_to_sync)}] ✅ Synced & Verified SHA256 -> {target_path} ({len(raw_bytes)} bytes)")

    py_files = [f"/root/video_factory/{p}" for p in files_to_sync if p.endswith(".py")]
    if py_files:
        print("\n🔨 Compiling python files on VPS...")
        compile_cmd = f"python3 -m py_compile {' '.join(py_files)}"
        compile_res = run_vps_cmd(compile_cmd)
        if isinstance(compile_res, dict) and compile_res.get("exit_code", 0) != 0:
            print(f"❌ Compilation failed on VPS:\n{compile_res.get('stderr')}")
            sys.exit(1)
        print(f"✅ All {len(py_files)} python files compiled with exit code 0 on VPS!")
    else:
        print("\nℹ️ No python files to compile (all files are TS/TSX/assets).")

    print("\n🎉 All files synced to VPS successfully with 100% bit-for-bit parity!")

if __name__ == "__main__":
    main()
