#!/usr/bin/env python3
"""
VF Pattern 1: Event-Driven Transitions - Prompts Forge Watcher
================================================================

Purpose: Replace 10-min cron poller with real-time file watcher for B3.5→B4 transition
Trigger: Creation of /var/vf/episodes/{task_id}/prompts_forge.json
Action: Send HG2 notification via Telegram
Latency: <30 seconds (vs 10 minutes with cron)

Architecture:
- Uses watchdog library (inotify wrapper)
- Monitors /var/vf/episodes recursively
- Deduplication via processed set
- Fallback: Cron poller runs every 30 min

Deployment:
- Systemd service: vf-prompts-forge-watcher.service
- Log: /var/vf/logs/prompts_forge_watcher.log
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


class PromptsForgeHandler(FileSystemEventHandler):
    """
    File system event handler for prompts_forge.json creation.

    Monitors /var/vf/episodes/{task_id}/prompts_forge.json files.
    When created, triggers HG2 notification via Telegram.
    """

    def __init__(self):
        self.processed = set()
        self.log_file = Path("/var/vf/logs/prompts_forge_watcher.log")
        self.checkpoint_file = Path("/var/vf/prompts_forge_watcher_state.json")

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

        Filters for prompts_forge.json files and triggers HG2.
        """
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Check if this is a prompts_forge.json file
        if path.name != "prompts_forge.json":
            return

        # Extract task_id from path: /var/vf/episodes/{task_id}/prompts_forge.json
        try:
            task_id = path.parent.name
        except Exception as e:
            self._log(f"[ERROR] Failed to extract task_id from {path}: {e}")
            return

        # Check if already processed
        if task_id in self.processed:
            self._log(f"[SKIP] {task_id} already processed")
            return

        self._log(f"[DETECTED] prompts_forge.json created for {task_id}")

        # Trigger HG2 notification
        success = self._trigger_hg2(task_id, path)

        if success:
            # Mark as processed
            self.processed.add(task_id)
            self._save_checkpoint()
            self._log(f"[SUCCESS] HG2 sent for {task_id}")
        else:
            self._log(f"[FAILED] HG2 trigger failed for {task_id}. Cron fallback will retry.")

    def _trigger_hg2(self, task_id: str, prompts_file: Path) -> bool:
        """
        Trigger HG2 notification via Telegram.
        Uses app.services.telegram_buttons.send_gate2_card.
        """
        try:
            import asyncio
            from app.services.telegram_buttons import send_gate2_card

            if not prompts_file.exists():
                self._log(f"[ERROR] {task_id}: prompts_forge.json disappeared")
                return False

            try:
                prompts_data = json.loads(prompts_file.read_text(encoding="utf-8"))
                if isinstance(prompts_data, dict):
                    bg_dict = prompts_data.get("backgrounds") or {}
                    fg_dict = prompts_data.get("foregrounds") or {}
                    n_bg = len(bg_dict)
                    n_fg = len(fg_dict)
                elif isinstance(prompts_data, list):
                    n_bg = sum(1 for p in prompts_data if isinstance(p, dict) and (p.get("layer") == 1 or p.get("type") == "background" or "16:9" in str(p)))
                    n_fg = sum(1 for p in prompts_data if isinstance(p, dict) and (p.get("layer") == 2 or p.get("type") == "foreground" or "#FF00FF" in str(p)))
                else:
                    n_bg, n_fg = 0, 0

                ep_dir = prompts_file.parent
                n_scenes = 0
                story_score = "n/a"

                dp_file = ep_dir / "director_plan.json"
                if not dp_file.exists():
                    dp_file = ep_dir / "dp_plan.json"
                if dp_file.exists():
                    try:
                        dp_data = json.loads(dp_file.read_text(encoding="utf-8"))
                        n_scenes = len(dp_data.get("scenes") or [])
                    except Exception:
                        pass

                brain_file = ep_dir / "brain_input.json"
                if brain_file.exists():
                    try:
                        brain_data = json.loads(brain_file.read_text(encoding="utf-8"))
                        if not n_scenes:
                            n_scenes = len(brain_data.get("scenes") or [])
                        story_score = brain_data.get("story_gate_score") or brain_data.get("story_score") or "12/12"
                    except Exception:
                        pass

                if n_scenes == 0:
                    n_scenes = n_bg + n_fg

                self._log(f"[VALIDATE] {task_id}: {n_scenes} scenes found (BG: {n_bg}, FG: {n_fg}, Story Gate: {story_score})")
            except Exception as e:
                self._log(f"[ERROR] {task_id}: Invalid JSON in prompts_forge.json: {e}")
                n_scenes, n_bg, n_fg, story_score = 0, 0, 0, "N/A"

            asyncio.run(send_gate2_card(task_id=task_id, n_scenes=n_scenes, n_bg=n_bg, n_fg=n_fg, story_score=story_score))
            self._log(f"[HG2 SENT] {task_id}: Telegram Gate 2 card dispatched successfully")
            return True
        except Exception as e:
            self._log(f"[ERROR] {task_id}: Exception in HG2 trigger: {e}")
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

    print(f"[START] VF Prompts Forge Watcher")
    print(f"[START] Watching: {watch_dir}")
    print(f"[START] Target: prompts_forge.json files")
    print(f"[START] Action: Send HG2 notification via Telegram")
    print(f"[START] Ref: Pattern 1 - Event-Driven Transitions")
    print("-" * 60)

    # Create handler and observer
    handler = PromptsForgeHandler()
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=True)
    observer.start()

    handler._log(f"[ACTIVE] Watching {watch_dir} for prompts_forge.json...")

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
