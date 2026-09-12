#!/usr/bin/env python3
"""
Unified Human Gate 2 / Gate 3 Executor (Rule 125 Single Truth).
Delegates directly to execute_b10_auto_seo_upload_gate2.py.
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python execute_human_gate_2.py <episode_id>", file=sys.stderr)
        sys.exit(1)
        
    episode_id = sys.argv[1].strip()
    market = "en"
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    brain_path = ep_dir / "brain_input.json"
    if brain_path.exists():
        try:
            import json
            bdata = json.loads(brain_path.read_text(encoding="utf-8"))
            market = bdata.get("market") or bdata.get("lang_code") or market
        except Exception:
            pass
    if market == "en":
        ep_lower = episode_id.lower()
        if ep_lower.startswith("jp_") or ep_lower.startswith("jp-"):
            market = "jp"
        elif ep_lower.startswith("kr_") or ep_lower.startswith("kr-"):
            market = "kr"
        elif ep_lower.startswith("vn_") or ep_lower.startswith("vn-"):
            market = "vn"

    cmd = [
        sys.executable,
        "/root/video_factory/scripts/execute_b10_auto_seo_upload_gate2.py",
        "--episode", episode_id,
        "--market", market,
        "--privacy", "unlisted"
    ]
    print(f"=== [GATE EXECUTOR] Delegating {episode_id} to B10 Auto SEO + Upload + Gate 3 ===")
    sys.exit(subprocess.call(cmd))

if __name__ == "__main__":
    main()
