#!/usr/bin/env python3
"""
scripts/b11_engine.py
=============================================================================
Unified Forwarder to scripts/b11_antigravity_engine.py (Rule 125 Single Truth)
=============================================================================
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.b11_antigravity_engine import (
    load_secrets,
    load_state,
    save_state,
    get_yt_access_token,
    get_market_oauth,
    query_youtube,
    query_analytics,
    call_hhtech_gpt56,
    notion_api,
    fetch_all_channel_videos,
    sync_to_experiment_lab,
    append_skill_enhancement,
    diagnose_channel_lifecycle,
    run_b11_engine
)

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    is_deep = "--deep" in sys.argv
    target_market = None
    for arg in sys.argv:
        if arg.startswith("--market="):
            target_market = arg.split("=", 1)[1].strip()
        elif arg.startswith("-m="):
            target_market = arg.split("=", 1)[1].strip()
    mode = "deep" if is_deep else "routine"
    run_b11_engine(mode=mode, dry_run=is_dry, target_market=target_market)
