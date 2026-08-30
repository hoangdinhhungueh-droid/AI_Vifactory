#!/usr/bin/env python3
"""
Cron poller: Check Antigravity quota state and auto-resume image pull when quota resets.
Runs every 15 minutes. Non-blocking; exits silently if no action needed.

Usage:
  0 */1 * * * python3 scripts/antigravity_quota_poller.py  # every hour
  */15 * * * * python3 scripts/antigravity_quota_poller.py # every 15 min
"""
import sys
import os
import json
import subprocess
import logging
from datetime import datetime, timezone

sys.path.insert(0, '/root/video_factory')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/vf/logs/antigravity_quota_poller.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

from app.services.quota_manager import read_quota, is_quota_available, get_retry_wait_seconds, mark_resumed

QUOTA_FILE = "/tmp/vf/antigravity_quota.json"

def poller():
    """Check quota and retry if reset."""
    
    # Read current quota state
    state = read_quota()
    if not state:
        logger.debug("No quota state file; nothing to check")
        return 0
    
    if state.status != "QUOTA_EXHAUSTED":
        logger.debug(f"Quota status is {state.status}, not exhausted; skipping")
        return 0
    
    episode_id = state.episode_id
    logger.info(f"Checking quota for {episode_id} (generated {state.images_generated}/{state.target_count})")
    
    # Check if quota has reset
    if not is_quota_available(state):
        wait_sec = get_retry_wait_seconds(state)
        wait_min = wait_sec / 60
        logger.info(f"Quota not reset yet. Reset in ~{wait_min:.1f} min at {state.quota_reset_at}")
        return 0
    
    # Quota has reset; resume pull
    logger.info(f"✅ Quota reset! Resuming pull for {episode_id}")
    mark_resumed(state)
    
    # Call pull_approved_images.py to resume
    cmd = [
        sys.executable,
        'scripts/pull_approved_images.py',
        '--episode-id', episode_id
    ]
    
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd='/root/video_factory', capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            logger.info(f"✅ Pull resumed successfully")
            if result.stdout:
                for line in result.stdout.split('\n')[:10]:  # Log first 10 lines
                    if line.strip():
                        logger.info(f"  {line}")
        else:
            logger.error(f"Pull failed (exit={result.returncode})")
            if result.stderr:
                logger.error(f"stderr: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        logger.error("Pull command timed out")
        return 1
    except Exception as e:
        logger.error(f"Failed to resume pull: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(poller())
