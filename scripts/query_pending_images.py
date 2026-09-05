#!/usr/bin/env python3
"""
VPS Script: Query episodes pending image generation (B4).
Called by Windows Antigravity agent via SSH to discover work.

Returns JSON array of episodes where:
- B3.5 (Prompt Forge) is complete (prompts_forge.json exists)
- B4 (Image Generation) is pending (no assets/ dir or incomplete)
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, '/root/video_factory')

EPISODES_DIR = Path("/var/vf/episodes")

def query_pending_episodes():
    """Return list of episodes needing image generation."""
    pending = []

    if not EPISODES_DIR.exists():
        return []

    for episode_dir in EPISODES_DIR.iterdir():
        if not episode_dir.is_dir():
            continue

        # Skip dead episodes
        if episode_dir.name.startswith("_dead_"):
            continue

        episode_id = episode_dir.name
        prompts_file = episode_dir / "prompts_forge.json"
        assets_dir = episode_dir / "assets"

        # Check if B3.5 is complete
        if not prompts_file.exists():
            continue

        # Check if B4 is pending
        needs_images = False

        if not assets_dir.exists():
            needs_images = True
        else:
            # Check if prompts_forge has content but assets is empty/incomplete
            try:
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    prompts_data = json.load(f)

                # Count expected images
                bg_count = len(prompts_data.get("backgrounds", {}))
                fg_count = len(prompts_data.get("foregrounds", {}))
                expected_total = bg_count + fg_count

                if expected_total == 0:
                    continue  # No images needed

                # Count existing images
                existing_images = list(assets_dir.glob("*.png"))
                existing_count = len(existing_images)

                if existing_count < expected_total:
                    needs_images = True

            except Exception:
                # If can't parse, assume needs images
                needs_images = True

        if needs_images:
            pending.append({
                "episode_id": episode_id,
                "prompts_file": str(prompts_file),
                "assets_dir": str(assets_dir),
                "status": "B3.5_COMPLETE_B4_PENDING"
            })

    return pending

def main():
    """Entry point - print JSON to stdout for SSH capture."""
    try:
        pending = query_pending_episodes()
        print(json.dumps(pending, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
