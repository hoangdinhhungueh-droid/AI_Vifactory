import sys
import os
import base64
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.vps_runner import run_vps_cmd

TARGET_DIR = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\9819991d-66fe-4cd4-95ad-1e51da5ffe74\qa_frames")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

def download_chunked(remote_path: str, local_name: str) -> bool:
    res = run_vps_cmd(f"wc -c < {remote_path}")
    stdout = res.get("stdout", "").strip()
    if not stdout.isdigit():
        print(f"❌ Failed to get size for {remote_path}: {stdout}")
        return False
    total_len = int(stdout)
    print(f"📥 Downloading {remote_path} ({total_len} bytes) -> {local_name}...")

    chunk_size = 3000
    all_data = bytearray()
    offset = 0

    while offset < total_len:
        count = min(chunk_size, total_len - offset)
        cmd = f'python3 -c "import base64; f=open(\'{remote_path}\',\'rb\'); f.seek({offset}); print(base64.b64encode(f.read({count})).decode())"'
        chunk_res = run_vps_cmd(cmd)
        b64 = chunk_res.get("stdout", "").strip()
        if not b64:
            print(f"⚠️ Empty chunk at offset {offset}")
            return False
        all_data.extend(base64.b64decode(b64))
        offset += count

    out_file = TARGET_DIR / local_name
    with open(out_file, "wb") as f:
        f.write(all_data)

    try:
        with Image.open(out_file) as im:
            im.verify()
        print(f"✅ PASS: {local_name} verified ({len(all_data)} bytes)")
        return True
    except Exception as e:
        print(f"❌ Corrupt image {local_name}: {e}")
        return False

if __name__ == "__main__":
    targets = [
        ("/tmp/b450_sm.jpg", "baseline_frame_0450.jpg"),
        ("/tmp/p450_sm.jpg", "pilot_frame_0450.jpg"),
    ]
    all_ok = True
    for rem, loc in targets:
        ok = download_chunked(rem, loc)
        if not ok:
            all_ok = False
    sys.exit(0 if all_ok else 1)
