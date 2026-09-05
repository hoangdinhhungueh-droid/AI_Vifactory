#!/usr/bin/env python3
"""
VF Pattern 1: Event-Driven Transitions - Image Ready Watcher
=============================================================

Purpose: Replace 10-min cron poller with real-time file watcher for B5→B6 transition
Trigger: Creation of /var/vf/episodes/{task_id}/images_ready.json
Action: Trigger B6 (Audio/TTS generation)
Latency: <30 seconds (vs 10 minutes with cron)

Architecture:
- Uses watchdog library (inotify wrapper)
- Monitors /var/vf/episodes recursively
- Deduplication via processed set
- Fallback: Cron poller runs every 30 min

Note: images_ready.json is created by auto_b5_audit.py after approving 26/26 images

Deployment:
- Systemd service: vf-image-ready-watcher.service
- Log: /var/vf/logs/image_ready_watcher.log
- Auto-restart on crash

Ref: INTEGRATION_ROADMAP_DRAMACLAW_PATTERNS.md (Week 1-2)
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add project to path
sys.path.insert(0, '/root/video_factory')


class ImageReadyHandler(FileSystemEventHandler):
    """
    File system event handler for images_ready.json creation.

    Monitors /var/vf/episodes/{task_id}/images_ready.json files.
    When created, triggers B6 (Audio/TTS generation).
    """

    def __init__(self):
        self.processed = set()
        self.log_file = Path("/var/vf/logs/image_ready_watcher.log")
        self.checkpoint_file = Path("/var/vf/image_ready_watcher_state.json")

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Load processed state from checkpoint (survive restarts)
        self._load_checkpoint()

        self._log(f"[INIT] Watcher initialized. Already processed: {len(self.processed)} episodes")

    def _log(self, message: str):
        """Log with timestamp to both stdout and file."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"

        print(log_line)

        try:
            with open(self.log_file, 'a') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print(f"[LOG ERROR] Failed to write to log file: {e}")

    def _load_checkpoint(self):
        """Load processed episodes from checkpoint file."""
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text())
                self.processed = set(data.get('processed', []))
                self._log(f"[CHECKPOINT] Loaded {len(self.processed)} processed episodes")
            except Exception as e:
                self._log(f"[CHECKPOINT ERROR] Failed to load: {e}")
                self.processed = set()

    def _save_checkpoint(self):
        """Save processed episodes to checkpoint file."""
        try:
            data = {
                'processed': list(self.processed),
                'last_updated': datetime.utcnow().isoformat()
            }
            self.checkpoint_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            self._log(f"[CHECKPOINT ERROR] Failed to save: {e}")

    def on_created(self, event):
        """
        Called when a file is created.

        Filters for images_ready.json files and triggers B6.
        """
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Check if this is an images_ready.json file
        if path.name != "images_ready.json":
            return

        # Extract task_id from path: /var/vf/episodes/{task_id}/images_ready.json
        try:
            task_id = path.parent.name
        except Exception as e:
            self._log(f"[ERROR] Failed to extract task_id from {path}: {e}")
            return

        # Check if already processed
        if task_id in self.processed:
            self._log(f"[SKIP] {task_id} already processed")
            return

        self._log(f"[DETECTED] images_ready.json created for {task_id}")

        # Trigger B6 (Audio/TTS)
        success = self._trigger_b6(task_id, path)

        if success:
            # Mark as processed
            self.processed.add(task_id)
            self._save_checkpoint()
            self._log(f"[SUCCESS] B6 triggered for {task_id}")
        else:
            self._log(f"[FAILED] B6 trigger failed for {task_id}. Cron fallback will retry.")

    def _trigger_b6(self, task_id: str, images_file: Path) -> bool:
        """
        Trigger B6 (Audio/TTS generation).

        Uses existing continue_after_images.py script.
        Returns True if successful, False otherwise.
        """
        try:
            # Verify images_ready.json is valid
            if not images_file.exists():
                self._log(f"[ERROR] {task_id}: images_ready.json disappeared")
                return False

            # Read and validate JSON
            try:
                images_data = json.loads(images_file.read_text())
                approved_count = images_data.get('approved_count', 0)
                self._log(f"[VALIDATE] {task_id}: {approved_count}/26 images approved")

                if approved_count != 26:
                    self._log(f"[ERROR] {task_id}: Expected 26 approved images, got {approved_count}")
                    return False

            except json.JSONDecodeError as e:
                self._log(f"[ERROR] {task_id}: Invalid JSON in images_ready.json: {e}")
                return False

            # Import and call B6 trigger
            # Note: This uses the existing Antigravity B5→B6 integration
            # Ref: B5_IMPLEMENTATION_COMPLETE.md
            from scripts.telegram_buttons import trigger_b6_after_approval

            # Trigger B6
            trigger_b6_after_approval(task_id)

            self._log(f"[B6 TRIGGER] {task_id}: Audio/TTS generation started")

            return True

        except ImportError as e:
            self._log(f"[ERROR] Failed to import B6 trigger function: {e}")
            self._log(f"[FALLBACK] Attempting direct script call...")

            # Fallback: Call continue_after_images.py directly
            try:
                import subprocess
                result = subprocess.run(
                    ["python3", "/root/video_factory/scripts/continue_after_images.py", task_id],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                self._log(f"[B6 DIRECT] {task_id}: {result.stdout}")
                return True
            except Exception as e2:
                self._log(f"[ERROR] {task_id}: Direct script call failed: {e2}")
                return False

        except Exception as e:
            self._log(f"[ERROR] {task_id}: Exception in B6 trigger: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False


def main():
    """Main entry point for the watcher."""

    watch_dir = Path("/var/vf/episodes")

    # Ensure watch directory exists
    if not watch_dir.exists():
        print(f"[FATAL] Watch directory does not exist: {watch_dir}")
        sys.exit(1)

    print(f"[START] VF Image Ready Watcher")
    print(f"[START] Watching: {watch_dir}")
    print(f"[START] Target: images_ready.json files")
    print(f"[START] Action: Trigger B6 (Audio/TTS generation)")
    print(f"[START] Ref: Pattern 1 - Event-Driven Transitions")
    print("-" * 60)

    # Create handler and observer
    handler = ImageReadyHandler()
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=True)
    observer.start()

    handler._log(f"[ACTIVE] Watching {watch_dir} for images_ready.json...")

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler._log("[SHUTDOWN] Received keyboard interrupt")
        observer.stop()
    except Exception as e:
        handler._log(f"[FATAL] Unexpected error: {e}")
        import traceback
        handler._log(traceback.format_exc())
        observer.stop()
        sys.exit(1)

    observer.join()
    handler._log("[SHUTDOWN] Watcher stopped")


if __name__ == "__main__":
    main()
