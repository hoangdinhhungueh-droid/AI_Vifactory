#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B5→B6 Automation Bridge (File Watcher)

Watches: /var/vf/episodes/{EP_ID}/images_ready.json
Action: Trigger continue_after_images.py (starts B6 render)

Root cause: EN_EP0251 stuck 26+ hours after Antigravity completion because
no automation triggered B6 after images became ready.

Solution: File watcher (Pattern 1 - Event-Driven) detects images_ready.json
creation and spawns B6 render within seconds instead of 10-minute cron polling.

Deployed as systemd service: vf-image-ready-watcher.service

Safety:
- Tracks processed episodes to avoid double-spawning
- Uses detached subprocess (start_new_session=True)
- Graceful shutdown on SIGINT

Template: Based on Dramaclaw Pattern 1 (event-driven transitions)
Session: 2026-09-01 Phase 0 Emergency Fixes
"""
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("ERROR: watchdog library not installed", file=sys.stderr)
    print("Run: pip install watchdog", file=sys.stderr)
    sys.exit(1)


class ImagesReadyHandler(FileSystemEventHandler):
    """Detects images_ready.json creation and triggers B6 render."""
    
    def __init__(self):
        self.processed = set()
        self.log("Handler initialized")
    
    def log(self, msg):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        print(f"[{timestamp}] [B5→B6 WATCHER] {msg}", flush=True)
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if path.name != "images_ready.json":
            return
        
        episode_id = path.parent.name
        
        if episode_id in self.processed:
            self.log(f"{episode_id}: already processed, skipping")
            return
        
        self.log(f"Detected images ready: {episode_id}")
        
        try:
            # Trigger B6 render (continue_after_images.py)
            # Uses absolute venv python path for cron safety
            # Fixed: use --episode-id flag (not positional arg)
            subprocess.run(
                [
                    "/root/video_factory/venv/bin/python3",
                    "/root/video_factory/scripts/continue_after_images.py",
                    "--episode-id", episode_id
                ],
                cwd="/root/video_factory",
                check=True,
                capture_output=True,
                text=True
            )
            self.processed.add(episode_id)
            self.log(f"B6 started for {episode_id}")
        except subprocess.CalledProcessError as e:
            self.log(f"ERROR {episode_id}: exit code {e.returncode}")
            self.log(f"stdout: {e.stdout[:200]}")
            self.log(f"stderr: {e.stderr[:200]}")
        except Exception as e:
            self.log(f"ERROR {episode_id}: {type(e).__name__}: {e}")


def main():
    watch_dir = Path("/var/vf/episodes")
    
    if not watch_dir.exists():
        print(f"ERROR: Episodes directory not found: {watch_dir}", file=sys.stderr)
        return 1
    
    handler = ImagesReadyHandler()
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=True)
    observer.start()
    
    handler.log(f"Monitoring {watch_dir} for images_ready.json...")
    handler.log("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler.log("Shutting down...")
        observer.stop()
    
    observer.join()
    handler.log("Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
