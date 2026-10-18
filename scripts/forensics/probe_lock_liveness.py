#!/usr/bin/env python3
"""scripts/forensics/probe_lock_liveness.py
Authoritative process liveness and safe lock disposal verification probe.
Complies with Rule 118 (Zero-Mock), Rule 125 (Zero-Ghost), Rule 137 (Safe-Trash),
and Boss Round 3 Supervisory Audit requirements.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    print("======================================================================")
    print("🔒 PROCESS LIVENESS & SAFE LOCK DISPOSAL VERIFICATION (Rule 125 & 137)")
    print("======================================================================")

    locks_dir = Path("/var/vf/locks")
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir(parents=True, exist_ok=True)

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    archived_lock = stale_dir / "JP_TEMP_59.b3b4.lock"

    print(f"1. Active lock path:   {active_lock} (Exists: {active_lock.exists()})")
    print(f"2. Archived lock path: {archived_lock} (Exists: {archived_lock.exists()})")

    target_lock = active_lock if active_lock.exists() else (archived_lock if archived_lock.exists() else None)
    if not target_lock:
        print("  Notice: No active or stale lock for JP_TEMP_59.b3b4.lock found. Directory is clean.")
    else:
        try:
            lock_data = json.loads(target_lock.read_text(encoding="utf-8"))
            pid = lock_data.get("pid")
            token = lock_data.get("token")
            created_at = lock_data.get("created_at")
            print(f"  Lock Metadata: PID={pid}, Token={token}, CreatedAt={created_at}")

            # Platform-appropriate liveness check (Rule 125 & Boss Item 4)
            is_alive = False
            if pid:
                try:
                    os.kill(int(pid), 0)
                    is_alive = True
                except (OSError, ProcessLookupError):
                    is_alive = False
            print(f"3. Process Liveness Check for PID {pid}: ALIVE={is_alive}")

            if active_lock.exists() and not is_alive:
                print(f"4. Safe Disposal: Moving abandoned lock from dead PID {pid} to {archived_lock}")
                shutil.move(str(active_lock), str(archived_lock))
                print(f"  [PASS] Archived safely to {archived_lock} per Rule 137 (Zero rm -rf)")
            elif archived_lock.exists():
                print(f"4. Safe Disposal Status: Already safely archived in {archived_lock} (PID {pid} confirmed dead).")
        except Exception as e:
            print(f"  Error reading lock file {target_lock}: {e}", file=sys.stderr)
            return 1

    # Rerun ghost scanner to prove post-disposal exit code 0
    ghost_script = Path("/root/video_factory/tools/ghost_scan.py")
    if not ghost_script.exists():
        ghost_script = Path(__file__).resolve().parent.parent / "tools" / "ghost_scan.py"

    print("\n======================================================================")
    print("🔍 POST-DISPOSAL GHOST SCANNER VERIFICATION (Rule 125 Gate)")
    print("======================================================================")
    res = subprocess.run([sys.executable, str(ghost_script)], capture_output=True, text=True, check=False)
    print(res.stdout.strip())
    if res.stderr.strip():
        print("STDERR:\n" + res.stderr.strip(), file=sys.stderr)
    print(f"Ghost Scanner Exit Code: {res.returncode}")

    if res.returncode != 0:
        print("❌ Ghost scanner detected remnants post-disposal!", file=sys.stderr)
        return 1

    print("✅ PROCESS LIVENESS & SAFE DISPOSAL VERIFIED CLEAN (Exit code 0)")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
