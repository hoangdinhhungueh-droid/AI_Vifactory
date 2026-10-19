#!/usr/bin/env python3
"""scripts/forensics/probe_lock_liveness.py
Authoritative process liveness and safe lock disposal verification probe.
Complies with Rule 118 (Zero-Mock), Rule 121 (Verification Protocol),
Rule 125 (Zero-Ghost), Rule 137 (Safe-Trash Mandate), and Boss Round 8 Requirements.

Modes:
  --inspect (default): Read-only inspection of active locks and holder liveness.
                       Never creates, restores, or mutates any lock.
  --dispose:           Explicitly authorized disposal of an existing abandoned lock
                       under a shared mutex with atomic collision-safe archival.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import errno
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Generator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


SCOPE_REGEX = re.compile(r"^[A-Z]{2}_[A-Za-z0-9_]+\.[a-z0-9_]+$")
TOKEN_REGEX = re.compile(r"^LOCK_TOKEN_([A-Za-z0-9_]+)_(\d+)$")


def validate_lock_metadata(data: Dict[str, Any], lock_path: Path) -> Tuple[str, str, str, int]:
    """Authenticates lock metadata with fail-closed boundary enforcement.

    Validates:
      1. Dict root structure.
      2. Required fields: owner, token, created_at, pid.
      3. Owner scope pattern (e.g. JP_TEMP_59.b3b4).
      4. Strict integer PID > 0 (rejects booleans and non-integers).
      5. Structural token-holder validation extracting exact scope and PID.
      6. Strict ISO 8601 created_at timestamp with mandatory timezone awareness.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Corrupted lock structure (not a dict): {lock_path}")

    required_keys = ("owner", "token", "created_at", "pid")
    for k in required_keys:
        if k not in data or data[k] is None or data[k] == "":
            raise ValueError(f"Lock file {lock_path} missing required field '{k}' (fail-closed)")

    owner = str(data["owner"]).strip()
    if not SCOPE_REGEX.match(owner):
        raise ValueError(f"Lock file {lock_path} invalid owner scope format: '{owner}'")

    raw_pid = data["pid"]
    if isinstance(raw_pid, bool) or not isinstance(raw_pid, int):
        raise ValueError(f"Lock file {lock_path} invalid PID: must be strict integer, got type {type(raw_pid).__name__}: {raw_pid!r}")
    if raw_pid <= 0:
        raise ValueError(f"Lock file {lock_path} PID must be positive integer, got: {raw_pid}")
    pid = raw_pid

    token = str(data["token"]).strip()
    tok_match = TOKEN_REGEX.match(token)
    if not tok_match:
        raise ValueError(f"Lock file {lock_path} invalid token format: '{token}'")

    token_scope = tok_match.group(1)
    token_pid = int(tok_match.group(2))

    scope_base = owner.split(".")[0]
    sanitized_scope = owner.replace(".", "_")
    if token_scope not in (scope_base, sanitized_scope):
        raise ValueError(f"Token scope '{token_scope}' does not match owner scope '{owner}'")
    if token_pid != pid:
        raise ValueError(f"Token PID {token_pid} does not match lock PID {pid}")

    created_at_str = str(data["created_at"]).strip()
    try:
        norm_ts = created_at_str.replace("Z", "+00:00")
        created_dt = datetime.fromisoformat(norm_ts)
    except Exception as e:
        raise ValueError(f"Lock file {lock_path} invalid ISO 8601 created_at '{created_at_str}': {e}")

    if created_dt.tzinfo is None:
        raise ValueError(f"Lock file {lock_path} created_at '{created_at_str}' must be timezone-aware (fail-closed)")

    now_utc = datetime.now(timezone.utc)
    if created_dt > now_utc + timedelta(minutes=5):
        raise ValueError(f"Lock timestamp '{created_at_str}' is in the future relative to UTC clock")
    if created_dt.year < 2024:
        raise ValueError(f"Lock timestamp '{created_at_str}' year is implausible (< 2024)")

    return owner, token, created_at_str, pid


def check_pid_liveness(pid: int, created_dt_str: Optional[str] = None) -> Tuple[bool, str]:
    """Non-destructive, platform-appropriate process liveness check.

    Returns:
      (is_alive, diagnostic_reason)
    Fail-closed: Treats only confirmed process absence as stale; permission errors
    or unknown outcomes are treated as alive / in-use.
    """
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        SYNCHRONIZE = 0x00100000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, wintypes.DWORD(pid))
        if handle == 0:
            err = kernel32.GetLastError()
            ERROR_INVALID_PARAMETER = 87
            if err == ERROR_INVALID_PARAMETER:
                return False, f"PID {pid} not found (confirmed absence on Windows)"
            if err == 5:  # ERROR_ACCESS_DENIED
                return True, f"PID {pid} exists (Access Denied - fail-closed)"
            return True, f"OpenProcess({pid}) failed with error {err} (fail-closed)"
        else:
            try:
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    STILL_ACTIVE = 259
                    if exit_code.value == STILL_ACTIVE:
                        return True, f"PID {pid} is running (STILL_ACTIVE)"
                    return False, f"PID {pid} terminated with exit code {exit_code.value}"
                return True, f"Cannot determine exit code for PID {pid} (fail-closed)"
            finally:
                kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, 0)
            return True, f"PID {pid} responded to signal 0 (confirmed alive)"
        except ProcessLookupError:
            return False, f"PID {pid} does not exist (ESRCH confirmed absence)"
        except PermissionError:
            return True, f"PID {pid} exists (EPERM permission denied - fail-closed)"
        except OSError as err:
            if err.errno == errno.ESRCH:
                return False, f"PID {pid} does not exist (ESRCH confirmed absence)"
            elif err.errno == errno.EPERM:
                return True, f"PID {pid} exists (EPERM permission denied - fail-closed)"
            else:
                return True, f"PID {pid} liveness indeterminate (OSError {err.errno} - fail-closed)"


def compute_file_sha256(path: Path) -> str:
    """Computes SHA256 hex digest of a physical file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@contextmanager
def acquire_disposal_mutex(mutex_file: Path) -> Generator[None, None, None]:
    """Shared advisory mutex for lock disposal operations (Boss Round 8 Item 17)."""
    mutex_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(mutex_file), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        if sys.platform != "win32":
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        yield
    except (BlockingIOError, OSError, PermissionError) as lock_err:
        raise RuntimeError(f"Lock disposal mutex '{mutex_file}' is currently held by another process: {lock_err}") from lock_err
    finally:
        try:
            if sys.platform != "win32":
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
            else:
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        os.close(fd)


def atomic_safe_archive(active_path: Path, stale_dir: Path, expected_sha: Optional[str] = None) -> Path:
    """Executes true collision-safe same-filesystem atomic archival with durability fsync.

    Guarantees:
      1. Source existence and identity revalidation.
      2. Same-filesystem device ID verification (os.stat(src).st_dev == os.stat(dst_dir).st_dev).
      3. Destination collision protection (unique UUID timestamped destination generated upfront).
      4. Atomic rename (os.replace).
      5. Durability fsync on file, destination directory, and source directory on POSIX (fail-closed on error).
      6. Post-action verification (source removed, destination exists, content SHA matches).
    """
    if not active_path.exists():
        raise FileNotFoundError(f"Source lock not found for archival: {active_path}")

    stale_dir.mkdir(parents=True, exist_ok=True)

    # 1. Same-filesystem device check (fail-closed)
    src_stat = os.stat(str(active_path))
    dst_dir_stat = os.stat(str(stale_dir))
    if src_stat.st_dev != dst_dir_stat.st_dev:
        raise RuntimeError(
            f"Cross-filesystem archival violation: source {active_path} (dev {src_stat.st_dev}) "
            f"and target {stale_dir} (dev {dst_dir_stat.st_dev}) must share device ID for atomic rename"
        )

    # 2. Source identity verification
    src_sha = compute_file_sha256(active_path)
    if expected_sha is not None and src_sha != expected_sha:
        raise ValueError(f"Source lock SHA changed concurrently: expected {expected_sha}, got {src_sha}")

    # 3. Collision-safe unique destination path
    ts_suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand_suffix = uuid.uuid4().hex[:8]
    dest_path = stale_dir / f"{active_path.stem}_{ts_suffix}_{rand_suffix}{active_path.suffix}"
    if dest_path.exists():
        raise FileExistsError(f"Destination collision detected: {dest_path}")

    # 4. Atomic rename (POSIX/NTFS atomic replace on same filesystem)
    os.replace(str(active_path), str(dest_path))

    # 5. File-level durability fsync (fail-closed on error)
    with open(dest_path, "a+b") as f_dst:
        os.fsync(f_dst.fileno())

    # 6. Directory-level durability fsync on POSIX (both destination and source directories)
    if hasattr(os, "O_DIRECTORY") and sys.platform != "win32":
        # Destination directory fsync
        dst_fd = os.open(str(stale_dir), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dst_fd)
        finally:
            os.close(dst_fd)

        # Source directory fsync (since directory entry was unlinked)
        src_fd = os.open(str(active_path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(src_fd)
        finally:
            os.close(src_fd)

    # 7. Post-action verification
    if active_path.exists():
        raise RuntimeError(f"Post-action failure: source {active_path} still exists after archival")
    if not dest_path.exists():
        raise RuntimeError(f"Post-action failure: destination {dest_path} does not exist after archival")
    dst_sha = compute_file_sha256(dest_path)
    if src_sha != dst_sha:
        raise ValueError(f"Post-action failure: SHA mismatch {src_sha} != {dst_sha}")

    return dest_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Process liveness and safe lock disposal verification probe (Rule 118 & Rule 137)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--inspect",
        action="store_true",
        default=True,
        help="Read-only inspection of active production locks and holder liveness (default).",
    )
    group.add_argument(
        "--dispose",
        action="store_true",
        help="Explicitly authorized disposal of an existing abandoned production lock.",
    )
    parser.add_argument(
        "--locks-dir",
        type=str,
        default=None,
        help="Custom path to locks directory (defaults to /var/vf/locks or fallback).",
    )
    args = parser.parse_args(argv)

    is_dispose_mode = bool(args.dispose)

    print("======================================================================")
    print("🔒 PROCESS LIVENESS & SAFE LOCK DISPOSAL VERIFICATION (Rule 125 & 137)")
    print(f"   Mode: {'DISPOSE (Explicitly Authorized)' if is_dispose_mode else 'INSPECT (Read-Only By Default)'}")
    print("======================================================================")

    if args.locks_dir:
        locks_dir = Path(args.locks_dir)
    elif Path("/var/vf/locks").exists():
        locks_dir = Path("/var/vf/locks")
    else:
        locks_dir = Path(__file__).resolve().parent.parent.parent / "var" / "vf" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir(parents=True, exist_ok=True)
    mutex_path = locks_dir / ".disposal_operation.mutex"

    print(f"1. Target locks directory: {locks_dir}")
    print(f"2. Safe stale directory:   {stale_dir}")

    # Locate active production locks
    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    candidate_locks = []
    if active_lock.exists():
        candidate_locks.append(active_lock)
    else:
        for p in sorted(locks_dir.glob("*.lock")):
            if p.name.startswith(".") or not p.is_file():
                continue
            # Exclude advisory locks for state files (e.g. *.json.lock, *.mutex)
            if p.name.endswith(".json.lock") or p.name.endswith(".mutex"):
                continue
            scope_name = p.name[:-5] if p.name.endswith(".lock") else p.name
            if SCOPE_REGEX.match(scope_name):
                candidate_locks.append(p)

    if not candidate_locks:
        print("\n3. Active production lock path: None found")
        print("   - STATUS: CLEAN (Zero active abandoned locks in locks directory)")
        print("   - Observation: No qualifying production lock exists to inspect or dispose.")
        print("   - Action: 0 synthetic records generated. Read-only clean state preserved.")
        print("======================================================================")
        print("✅ PROCESS LIVENESS & LOCK REPOSITORY CLEAN (Exit code 0)")
        print("======================================================================")
        return 0

    target_lock = candidate_locks[0]
    print(f"\n3. Active production lock path: {target_lock} (Exists: True)")

    # Read and authenticate lock metadata
    raw_text = target_lock.read_text(encoding="utf-8")
    try:
        data = json.loads(raw_text)
    except Exception as _json_err:
        raise ValueError(f"Corrupted lock structure (invalid JSON) in {target_lock}: {_json_err}") from _json_err
    owner, token, created_at, pid = validate_lock_metadata(data, target_lock)
    current_sha = compute_file_sha256(target_lock)

    print("4. Structural Metadata Validation:")
    print(f"   - Lock Path:      {target_lock}")
    print(f"   - Scope Owner:    {owner} (Matches scope pattern: VALID)")
    print(f"   - Token Holder:   {token} (Structural token format: VALID)")
    print(f"   - Created At:     {created_at} (Timezone-aware ISO 8601: VALID)")
    print(f"   - Target PID:     {pid} (Strict integer: VALID)")
    print(f"   - Current SHA256: {current_sha}")

    # Non-destructive process liveness validation
    is_alive, liveness_reason = check_pid_liveness(pid, created_at)
    print("5. Process Liveness Validation:")
    print(f"   - PID Check:      PID {pid}")
    print(f"   - Status:         ALIVE={is_alive} ({liveness_reason})")

    if not is_dispose_mode:
        print("\n6. Inspection Summary (Read-Only Mode):")
        print("   - Mutation: None performed (read-only inspection by default).")
        print(f"   - Lock Disposition: {'ACTIVE_PROCESS_RUNNING' if is_alive else 'ABANDONED_STALE_LOCK'}")
        print("======================================================================")
        print("✅ PROCESS LIVENESS INSPECTION COMPLETED (Exit code 0)")
        print("======================================================================")
        return 0

    # DISPOSE MODE: Must be confirmed dead and executed under mutex
    if is_alive:
        print(f"❌ Cannot dispose active lock {target_lock}: PID {pid} is running! ({liveness_reason})", file=sys.stderr)
        return 1

    print("\n6. Executing Physical Collision-Safe Safe-Trash Archival (Rule 137):")
    with acquire_disposal_mutex(mutex_path):
        # Re-read and re-validate source immediately before mutation under shared mutex
        re_data = json.loads(target_lock.read_text(encoding="utf-8"))
        validate_lock_metadata(re_data, target_lock)
        re_alive, re_reason = check_pid_liveness(pid, created_at)
        if re_alive:
            raise RuntimeError(f"Race condition detected: PID {pid} became alive immediately before archival: {re_reason}")

        final_dest = atomic_safe_archive(target_lock, stale_dir, expected_sha=current_sha)

    print(f"   - Atomic safe archival completed: {target_lock} -> {final_dest}")
    print(f"   - Source Exists:      {target_lock.exists()} (VERIFIED: False)")
    print(f"   - Destination Exists: {final_dest.exists()} (VERIFIED: True)")
    print(f"   - Destination SHA256: {compute_file_sha256(final_dest)}")
    print("   - Status: Collision-safe same-filesystem archival & durability fsync verified (Rule 137)")

    # Post-disposal ghost scan gate
    ghost_script = Path("/root/video_factory/tools/ghost_scan.py")
    if not ghost_script.exists():
        ghost_script = Path(__file__).resolve().parent.parent.parent / "tools" / "ghost_scan.py"

    print("\n======================================================================")
    print("🔍 POST-DISPOSAL GHOST SCANNER VERIFICATION (Rule 125 Gate)")
    print("======================================================================")
    res = subprocess.run(
        [sys.executable, str(ghost_script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
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
