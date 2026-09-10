#!/usr/bin/env python3
"""
Trigger Human Gate 2 Telegram Dispatcher (Rule 125 & Executive 1-Click Mandate).
Dispatches the standard Human Gate 2 Telegram card for any episode.

Usage:
    python scripts/trigger_human_gate_2.py <episode_id>
"""
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.telegram_buttons import trigger_human_gate_2

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/trigger_human_gate_2.py <episode_id>", file=sys.stderr)
        return 1

    episode_id = sys.argv[1].strip()
    print(f"=== [HG2 DISPATCH] Triggering Human Gate 2 for {episode_id} ===")
    msg_id = trigger_human_gate_2(episode_id)
    if msg_id:
        print(f"✅ Human Gate 2 dispatched successfully! Telegram Message ID: {msg_id}")
        return 0
    else:
        print("⚠️ Human Gate 2 dispatch finished (Message ID: None, check logs or Telegram settings).")
        return 0

if __name__ == "__main__":
    sys.exit(main())
