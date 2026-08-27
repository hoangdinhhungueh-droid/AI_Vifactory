#!/usr/bin/env python3
"""DEPRECATED: Use render_episode_parameterized.py instead.

This script remains for backward compatibility, calling the parameterized
version with ep001 defaults. All production renders should use:
  python3 render_episode_parameterized.py --episode_id <ID> --market <en|jp|kr>
"""
import subprocess, sys

ep_id = "en-byzantine-empire-ep001"
market = "en"

print(f"[render_byzantine_master.py] Forwarding to render_episode_parameterized.py")
print(f"  episode_id={ep_id}, market={market}")

result = subprocess.run(
    [sys.executable, "/root/video_factory/scripts/render_episode_parameterized.py",
     "--episode_id", ep_id, "--market", market],
    cwd="/root/video_factory"
)
sys.exit(result.returncode)
