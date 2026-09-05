#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3.5→B4 automation gap fix (P0-1 blocker, 01/09/2026).

Episodes stuck at B3.5 after prompts_forge.json creation with no automation
triggering B4 image generation. This poller bridges that gap:

For every episode under /var/vf/episodes/ that has a prompts_forge.json
(i.e. went through B3.5 Prompt Forge) but no images/ directory yet:

  1. Checks prompts_forge.json mtime > 5 minutes (avoids racing with file creation)
  2. Checks lock file doesn't exist: /var/vf/locks/<id>.b3b4.lock
  3. Checks images/ directory doesn't exist (B4 not started yet)
  4. If all conditions met → spawns b4_generate_from_notion_prompts.py

Intended to run every 10 minutes from cron:

  */10 * * * * vfuser cd /root/video_factory && /root/video_factory/venv/bin/python3 scripts/prompts_forge_poller.py >> /var/vf/logs/prompts_forge_poller.log 2>&1

Safe to run concurrently: uses O_CREAT|O_EXCL lock pattern from
image_completion_poller.py to prevent double-spawns.

Root cause: Discovered during EN_EP0251 incident (stuck 26+ hours at B3.5).
Template: image_completion_poller.py (working B5→B6 automation).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EPISODES = Path("/var/vf/episodes")
LOCK_DIR = Path("/var/vf/locks")
LOG_DIR = Path("/var/vf/logs")
PROMPTS_FORGE_MIN_AGE_SEC = 300  # 5 minutes


def _log(msg):
    print("[%s] %s" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg), flush=True)


def _lock_path(episode_id):
    return LOCK_DIR / ("%s.b3b4.lock" % episode_id)


def already_dispatched(episode_id):
    return _lock_path(episode_id).exists()


def spawn_b4_generation(episode_id):
    """Spawn b4_generate_from_notion_prompts.py in detached mode."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    lock = _lock_path(episode_id)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        _log("%s: lock already held, skipping (already running or done)" % episode_id)
        return False
    
    log_path = LOG_DIR / ("%s_b4.log" % episode_id)
    try:
        logfd = os.open(str(log_path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        proc = subprocess.Popen(
            [sys.executable, "scripts/b4_generate_from_notion_prompts.py",
             "--episode", episode_id],
            cwd="/root/video_factory",
            stdout=logfd, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True, pass_fds=(logfd,),
        )
        os.write(fd, str(proc.pid).encode())
        os.close(logfd)
        _log("%s: dispatched b4_generate_from_notion_prompts.py pid=%d log=%s" %
             (episode_id, proc.pid, log_path))
        return True
    except Exception as e:
        os.unlink(str(lock))
        _log("%s: spawn failed: %s" % (episode_id, e))
        return False
    finally:
        os.close(fd)


def main():
    if not EPISODES.exists():
        _log("ERROR no episodes dir at %s" % EPISODES)
        return 1

    candidates = sorted(p for p in EPISODES.iterdir()
                        if p.is_dir() and not p.name.startswith("_dead_"))
    
    if not candidates:
        _log("no episode directories found")
        return 0

    found_waiting = 0
    found_dispatched = 0

    for ep_dir in candidates:
        episode_id = ep_dir.name
        prompts_forge = ep_dir / "prompts_forge.json"
        images_dir = ep_dir / "images"
        
        # Skip if no prompts_forge.json
        if not prompts_forge.exists():
            continue
        
        # Skip if images/ directory already exists (B4 already started)
        if images_dir.exists():
            continue
        
        # Skip if already dispatched
        if already_dispatched(episode_id):
            continue
        
        # Check prompts_forge.json age (avoid racing with file creation)
        try:
            mtime = prompts_forge.stat().st_mtime
            age_sec = time.time() - mtime
            if age_sec < PROMPTS_FORGE_MIN_AGE_SEC:
                _log("%s: prompts_forge.json too recent (%.0fs old), waiting" % 
                     (episode_id, age_sec))
                found_waiting += 1
                continue
        except Exception as e:
            _log("%s: cannot stat prompts_forge.json: %s" % (episode_id, e))
            continue
        
        # All conditions met → trigger B4
        _log("%s: prompts_forge.json ready (%.0fmin old), no images/ → triggering B4" %
             (episode_id, age_sec / 60))
        if spawn_b4_generation(episode_id):
            found_dispatched += 1
    
    _log("scan complete: %d waiting, %d dispatched" % (found_waiting, found_dispatched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
