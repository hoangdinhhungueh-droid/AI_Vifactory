#!/usr/bin/env python3
"""scripts/forensics/probe_lock_liveness.py
Authoritative process liveness and safe lock disposal verification probe.
Complies with Rule 118 (Zero-Mock), Rule 121 (Verification Protocol),
Rule 125 (Zero-Ghost), Rule 137 (Safe-Trash Mandate), and Boss Round 10 Requirements.

Modes:
  --inspect (default): Read-only inspection of active locks and holder liveness.
                       Never creates, restores, or mutates any lock.
  --dispose:           Explicitly authorized disposal of an existing abandoned lock
                       under a shared mutex with atomic collision-safe archival.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
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


class ProcStartStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    MALFORMED = "MALFORMED"
    INACCESSIBLE = "INACCESSIBLE"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class ProcStartResult:
    status: ProcStartStatus
    start_time: Optional[datetime]
    diagnostic: str

    def __iter__(self):
        yield self.start_time
        yield self.diagnostic


class LivenessStatus(str, Enum):
    VERIFIED_ALIVE = "VERIFIED_ALIVE"
    CONFIRMED_DEAD = "CONFIRMED_DEAD"
    PID_REUSED = "PID_REUSED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class LivenessResult:
    status: LivenessStatus
    is_alive: Optional[bool]
    proc_start: Optional[ProcStartResult]
    diagnostic: str

    def __iter__(self):
        yield self.is_alive
        yield self.diagnostic


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
    except (ValueError, TypeError) as e:
        raise ValueError(f"Lock file {lock_path} invalid ISO 8601 created_at '{created_at_str}': {e}")

    if created_dt.tzinfo is None:
        raise ValueError(f"Lock file {lock_path} created_at '{created_at_str}' must be timezone-aware (fail-closed)")

    now_utc = datetime.now(timezone.utc)
    if created_dt > now_utc + timedelta(minutes=5):
        raise ValueError(f"Lock timestamp '{created_at_str}' is in the future relative to UTC clock")
    if created_dt.year < 2024:
        raise ValueError(f"Lock timestamp '{created_at_str}' year is implausible (< 2024)")

    return owner, token, created_at_str, pid


def get_posix_proc_starttime(pid: int, proc_root: str = "/proc") -> ProcStartResult:
    """Parses Linux kernel starttime from /proc/<pid>/stat field 22.

    Defends against PID reuse by extracting the exact process start tick count
    and combining it with system boot time from /proc/stat per kernel spec.
    Returns typed ProcStartResult with fail-closed status.
    """
    root_dir = Path(proc_root)
    stat_path = root_dir / str(pid) / "stat"
    if not stat_path.exists():
        return ProcStartResult(
            status=ProcStartStatus.NOT_FOUND,
            start_time=None,
            diagnostic=f"{stat_path} does not exist (process absent)",
        )
    try:
        content = stat_path.read_text(encoding="utf-8", errors="replace")
    except PermissionError as pe:
        return ProcStartResult(
            status=ProcStartStatus.INACCESSIBLE,
            start_time=None,
            diagnostic=f"Permission denied reading {stat_path}: {pe}",
        )
    except OSError as oe:
        return ProcStartResult(
            status=ProcStartStatus.INACCESSIBLE,
            start_time=None,
            diagnostic=f"OS error reading {stat_path}: {oe}",
        )

    r_idx = content.rfind(")")
    if r_idx == -1:
        return ProcStartResult(
            status=ProcStartStatus.MALFORMED,
            start_time=None,
            diagnostic=f"Corrupted {stat_path} format (missing ')') in {content[:40]}",
        )
    fields = content[r_idx + 2:].split()
    if len(fields) <= 19:
        return ProcStartResult(
            status=ProcStartStatus.MALFORMED,
            start_time=None,
            diagnostic=f"Truncated {stat_path}: only {len(fields)} fields after comm",
        )

    try:
        starttime_ticks = int(fields[19])
    except ValueError as ve:
        return ProcStartResult(
            status=ProcStartStatus.MALFORMED,
            start_time=None,
            diagnostic=f"Invalid starttime field 22 in {stat_path}: {fields[19]}: {ve}",
        )

    clk_tck: Optional[int] = None
    try:
        if hasattr(os, "sysconf") and "SC_CLK_TCK" in os.sysconf_names:
            clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    except (AttributeError, ValueError, OSError):
        clk_tck = None

    if clk_tck is None or clk_tck <= 0:
        return ProcStartResult(
            status=ProcStartStatus.INDETERMINATE,
            start_time=None,
            diagnostic="INDETERMINATE: SC_CLK_TCK unavailable (fail-closed)",
        )

    system_stat_path = root_dir / "stat"
    btime = 0
    try:
        with open(system_stat_path, "r", encoding="utf-8") as f_stat:
            for line in f_stat:
                if line.startswith("btime "):
                    btime = int(line.split()[1])
                    break
    except (OSError, PermissionError, ValueError) as be:
        return ProcStartResult(
            status=ProcStartStatus.INDETERMINATE,
            start_time=None,
            diagnostic=f"Could not read btime from {system_stat_path}: {be}",
        )

    if btime == 0:
        return ProcStartResult(
            status=ProcStartStatus.INDETERMINATE,
            start_time=None,
            diagnostic=f"btime not found in {system_stat_path}",
        )

    proc_start_epoch = btime + (float(starttime_ticks) / float(clk_tck))
    proc_start_dt = datetime.fromtimestamp(proc_start_epoch, tz=timezone.utc)
    return ProcStartResult(
        status=ProcStartStatus.VERIFIED,
        start_time=proc_start_dt,
        diagnostic="OK",
    )


def check_pid_liveness(pid: int, created_dt_str: Optional[str] = None) -> LivenessResult:
    """Non-destructive, platform-appropriate process liveness check.

    Returns typed LivenessResult containing explicit LivenessStatus enum,
    is_alive flag (True, False, or None), and typed diagnostic metadata.
    """
    created_dt: Optional[datetime] = None
    if created_dt_str:
        try:
            norm_ts = str(created_dt_str).strip().replace("Z", "+00:00")
            created_dt = datetime.fromisoformat(norm_ts)
            if created_dt.tzinfo is None:
                raise ValueError(f"Lock timestamp '{created_dt_str}' must be timezone-aware")
        except (ValueError, TypeError) as ts_err:
            sys.stderr.write(f"[liveness error] invalid lock created_at '{created_dt_str}': {ts_err}\n")
            return LivenessResult(
                status=LivenessStatus.INDETERMINATE,
                is_alive=None,
                proc_start=None,
                diagnostic=f"INDETERMINATE: invalid created_at timestamp '{created_dt_str}': {ts_err} (fail-closed)",
            )

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
                return LivenessResult(
                    status=LivenessStatus.CONFIRMED_DEAD,
                    is_alive=False,
                    proc_start=None,
                    diagnostic=f"PID {pid} not found (confirmed absence on Windows)",
                )
            if err == 5:  # ERROR_ACCESS_DENIED
                return LivenessResult(
                    status=LivenessStatus.INDETERMINATE,
                    is_alive=None,
                    proc_start=None,
                    diagnostic=f"INDETERMINATE: PID {pid} Access Denied (EPERM equivalent - fail-closed)",
                )
            return LivenessResult(
                status=LivenessStatus.INDETERMINATE,
                is_alive=None,
                proc_start=None,
                diagnostic=f"INDETERMINATE: OpenProcess({pid}) failed with error {err} (fail-closed)",
            )
        else:
            try:
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    STILL_ACTIVE = 259
                    if exit_code.value != STILL_ACTIVE:
                        return LivenessResult(
                            status=LivenessStatus.CONFIRMED_DEAD,
                            is_alive=False,
                            proc_start=None,
                            diagnostic=f"PID {pid} terminated with exit code {exit_code.value}",
                        )

                    # Validate process start time against lock metadata (PID reuse defense)
                    class FILETIME(ctypes.Structure):
                        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

                    ft_create = FILETIME()
                    ft_exit = FILETIME()
                    ft_kernel = FILETIME()
                    ft_user = FILETIME()
                    if kernel32.GetProcessTimes(handle, ctypes.byref(ft_create), ctypes.byref(ft_exit), ctypes.byref(ft_kernel), ctypes.byref(ft_user)):
                        intervals = (ft_create.dwHighDateTime << 32) + ft_create.dwLowDateTime
                        if intervals > 0:
                            proc_start_epoch = (intervals - 116444736000000000) / 10000000
                            proc_start_dt = datetime.fromtimestamp(proc_start_epoch, tz=timezone.utc)
                            proc_start_res = ProcStartResult(
                                status=ProcStartStatus.VERIFIED,
                                start_time=proc_start_dt,
                                diagnostic="Windows GetProcessTimes verified",
                            )
                            if created_dt and proc_start_dt > created_dt + timedelta(seconds=2):
                                return LivenessResult(
                                    status=LivenessStatus.PID_REUSED,
                                    is_alive=False,
                                    proc_start=proc_start_res,
                                    diagnostic=f"PID_REUSED: PID {pid} was created at {proc_start_dt.isoformat()} after lock timestamp {created_dt.isoformat()} (original holder dead)",
                                )
                            return LivenessResult(
                                status=LivenessStatus.VERIFIED_ALIVE,
                                is_alive=True,
                                proc_start=proc_start_res,
                                diagnostic=f"PID {pid} is running (STILL_ACTIVE, process identity & start time consistent)",
                            )
                    return LivenessResult(
                        status=LivenessStatus.VERIFIED_ALIVE,
                        is_alive=True,
                        proc_start=None,
                        diagnostic=f"PID {pid} is running (STILL_ACTIVE)",
                    )
                return LivenessResult(
                    status=LivenessStatus.INDETERMINATE,
                    is_alive=None,
                    proc_start=None,
                    diagnostic=f"INDETERMINATE: Cannot determine exit code for PID {pid} (fail-closed)",
                )
            finally:
                kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return LivenessResult(
                status=LivenessStatus.CONFIRMED_DEAD,
                is_alive=False,
                proc_start=ProcStartResult(status=ProcStartStatus.NOT_FOUND, start_time=None, diagnostic="ProcessLookupError"),
                diagnostic=f"PID {pid} does not exist (ESRCH confirmed absence)",
            )
        except PermissionError as pe:
            return LivenessResult(
                status=LivenessStatus.INDETERMINATE,
                is_alive=None,
                proc_start=ProcStartResult(status=ProcStartStatus.INACCESSIBLE, start_time=None, diagnostic=str(pe)),
                diagnostic=f"INDETERMINATE: EPERM permission denied for PID {pid} (fail-closed, cannot confirm dead)",
            )
        except OSError as err:
            if err.errno == errno.ESRCH:
                return LivenessResult(
                    status=LivenessStatus.CONFIRMED_DEAD,
                    is_alive=False,
                    proc_start=ProcStartResult(status=ProcStartStatus.NOT_FOUND, start_time=None, diagnostic=str(err)),
                    diagnostic=f"PID {pid} does not exist (ESRCH confirmed absence)",
                )
            elif err.errno == errno.EPERM:
                return LivenessResult(
                    status=LivenessStatus.INDETERMINATE,
                    is_alive=None,
                    proc_start=ProcStartResult(status=ProcStartStatus.INACCESSIBLE, start_time=None, diagnostic=str(err)),
                    diagnostic=f"INDETERMINATE: EPERM permission denied for PID {pid} (fail-closed, cannot confirm dead)",
                )
            else:
                return LivenessResult(
                    status=LivenessStatus.INDETERMINATE,
                    is_alive=None,
                    proc_start=None,
                    diagnostic=f"INDETERMINATE: OSError {err.errno} for PID {pid} (fail-closed, cannot confirm dead)",
                )

        # Process responded to signal 0. Validate start time from /proc/<pid>/stat field 22 to defend against PID reuse
        start_res = get_posix_proc_starttime(pid)
        if start_res.status == ProcStartStatus.VERIFIED:
            proc_start_dt = start_res.start_time
            if created_dt and proc_start_dt and proc_start_dt > created_dt + timedelta(seconds=2):
                return LivenessResult(
                    status=LivenessStatus.PID_REUSED,
                    is_alive=False,
                    proc_start=start_res,
                    diagnostic=f"PID_REUSED: PID {pid} was created at {proc_start_dt.isoformat()} after lock timestamp {created_dt.isoformat()} (original holder dead)",
                )
            return LivenessResult(
                status=LivenessStatus.VERIFIED_ALIVE,
                is_alive=True,
                proc_start=start_res,
                diagnostic=f"PID {pid} confirmed alive (Linux kernel start time {proc_start_dt.isoformat() if proc_start_dt else 'N/A'} matches lock epoch)",
            )
        else:
            return LivenessResult(
                status=LivenessStatus.INDETERMINATE,
                is_alive=None,
                proc_start=start_res,
                diagnostic=f"INDETERMINATE: Process start time verification status '{start_res.status.value}': {start_res.diagnostic} (fail-closed)",
            )


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
    locked = False
    try:
        if sys.platform != "win32":
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        locked = True
        yield
    except (BlockingIOError, OSError, PermissionError) as lock_err:
        raise RuntimeError(f"Lock disposal mutex '{mutex_file}' is currently held by another process: {lock_err}") from lock_err
    finally:
        try:
            if locked:
                try:
                    if sys.platform != "win32":
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    else:
                        import msvcrt
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError as _unlock_err:
                    sys.stderr.write(f"[mutex error] critical unlock failure on '{mutex_file}': {_unlock_err}\n")
                    raise RuntimeError(f"Critical mutex unlock failure on '{mutex_file}': {_unlock_err}") from _unlock_err
        finally:
            os.close(fd)


def atomic_safe_archive(
    active_path: Path,
    stale_dir: Path,
    expected_sha: Optional[str] = None,
    max_retries: int = 5,
) -> Path:
    """Executes true collision-safe same-filesystem atomic archival with durability fsync.

    Guarantees:
      1. Source existence, device ID, inode, and content SHA verification.
      2. Same-filesystem device check (fail-closed on cross-device).
      3. True atomic exclusive reservation via os.link (or atomic O_CREAT | O_EXCL fallback)
         guaranteeing no concurrent clobber.
      4. Source identity revalidation (inode, dev, SHA) immediately before mutation and unlinking
         to prevent source replacement race conditions.
      5. Durability fsync on destination file, destination directory, and source directory (fail-closed on POSIX).
      6. Rollback / cleanup on partial failure (unlinks candidate destination if source was not unlinked).
      7. Post-action verification (source removed, destination exists, content SHA matches).
    """
    if not active_path.exists():
        raise FileNotFoundError(f"Source lock not found for archival: {active_path}")

    stale_dir.mkdir(parents=True, exist_ok=True)

    # 1. Source stat, inode, device, and SHA verification
    src_stat = active_path.stat()
    src_ino = src_stat.st_ino
    src_dev = src_stat.st_dev
    dst_dir_stat = stale_dir.stat()

    if src_dev != dst_dir_stat.st_dev:
        raise RuntimeError(
            f"Cross-filesystem archival violation: source {active_path} (dev {src_dev}) "
            f"and target {stale_dir} (dev {dst_dir_stat.st_dev}) must share device ID for atomic archival"
        )

    src_sha = compute_file_sha256(active_path)
    if expected_sha is not None and src_sha != expected_sha:
        raise ValueError(f"Source lock SHA changed concurrently: expected {expected_sha}, got {src_sha}")

    dest_path: Optional[Path] = None
    last_err: Optional[Exception] = None

    for attempt in range(max_retries):
        ts_suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rand_suffix = uuid.uuid4().hex[:8]
        candidate_dest = stale_dir / f"{active_path.stem}_{ts_suffix}_{rand_suffix}{active_path.suffix}"

        # Re-verify source identity before reservation attempt
        try:
            curr_stat = active_path.stat()
            if curr_stat.st_ino != src_ino or curr_stat.st_dev != src_dev:
                raise RuntimeError(f"Source replacement race detected: inode changed {src_ino} -> {curr_stat.st_ino}")
            curr_sha = compute_file_sha256(active_path)
            if curr_sha != src_sha:
                raise ValueError(f"Source replacement race detected: SHA changed {src_sha} -> {curr_sha}")
        except FileNotFoundError as fnf:
            raise RuntimeError(f"Source lock disappeared during archival attempt {attempt}: {fnf}") from fnf

        # Attempt atomic link (atomic creation of candidate_dest pointing to active_path; refuses if candidate_dest exists)
        try:
            os.link(str(active_path), str(candidate_dest))
            dest_path = candidate_dest
            break
        except FileExistsError:
            # Destination collided with concurrent actor; retry with new unique timestamp/UUID
            continue
        except (OSError, NotImplementedError) as link_err:
            # Fallback for environments lacking os.link (e.g. FAT32 or certain container mounts)
            try:
                fd = os.open(str(candidate_dest), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                try:
                    with open(active_path, "rb") as f_src:
                        while chunk := f_src.read(65536):
                            written = 0
                            while written < len(chunk):
                                n = os.write(fd, chunk[written:])
                                if n <= 0:
                                    raise OSError("Zero or negative bytes written during copy fallback")
                                written += n
                    os.fsync(fd)
                finally:
                    os.close(fd)

                # Re-verify source integrity before accepting destination
                post_stat = active_path.stat()
                if post_stat.st_ino != src_ino or post_stat.st_dev != src_dev or compute_file_sha256(active_path) != src_sha:
                    if candidate_dest.exists():
                        os.unlink(str(candidate_dest))
                    raise RuntimeError("Source replaced during copy fallback; destination discarded (rollback)")

                dest_path = candidate_dest
                break
            except FileExistsError:
                continue
            except (OSError, RuntimeError, ValueError) as ex:
                if candidate_dest.exists():
                    try:
                        os.unlink(str(candidate_dest))
                    except OSError as _clean_err:
                        sys.stderr.write(f"[cleanup notice] could not unlink candidate {candidate_dest}: {_clean_err}\n")
                last_err = ex
                break

    if dest_path is None:
        raise RuntimeError(f"Failed to atomically reserve unique destination in {stale_dir} after {max_retries} attempts: {last_err}")

    # 4. File-level durability fsync on destination with rollback on failure
    try:
        with open(dest_path, "a+b") as f_dst:
            os.fsync(f_dst.fileno())
    except OSError as fsync_err:
        rollback_ok = False
        if dest_path.exists():
            try:
                os.unlink(str(dest_path))
                rollback_ok = not dest_path.exists()
            except OSError as _clean_err:
                sys.stderr.write(f"[cleanup notice] could not unlink {dest_path}: {_clean_err}\n")
        status_msg = "verified rollback performed" if rollback_ok else "rollback failed or incomplete"
        raise RuntimeError(f"Destination fsync failed ({status_msg}): {fsync_err}") from fsync_err

    # 5. Final source revalidation before unlink
    final_stat = active_path.stat()
    if final_stat.st_ino != src_ino or final_stat.st_dev != src_dev:
        if dest_path.exists():
            os.unlink(str(dest_path))
        raise RuntimeError(f"Source replacement detected immediately before unlink: {src_ino} != {final_stat.st_ino}")
    if compute_file_sha256(active_path) != src_sha:
        if dest_path.exists():
            os.unlink(str(dest_path))
        raise ValueError(f"Source content changed immediately before unlink: {src_sha} != {compute_file_sha256(active_path)}")

    # Atomic unlinking of source entry
    os.unlink(str(active_path))

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


def _mp_disposal_worker(mutex_file: str, lock_file: str, stale_dir: str, barrier: Any, results_queue: Any) -> None:
    """Multiprocessing worker helper for cross-process mutex contention and race validation."""
    try:
        barrier.wait(timeout=10)
        with acquire_disposal_mutex(Path(mutex_file)):
            dest = atomic_safe_archive(Path(lock_file), Path(stale_dir))
            results_queue.put(("SUCCESS", str(dest)))
    except Exception as exc:
        results_queue.put(("ERROR", type(exc).__name__, str(exc)))


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
        print("   - DISPOSAL OUTCOME: QUALIFYING_LOCK_ABSENT (0 locks disposed, 0 synthetic locks created, clean state verified)")
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
    except (json.JSONDecodeError, ValueError) as _json_err:
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
    liveness = check_pid_liveness(pid, created_at)
    print("5. Process Liveness Validation:")
    print(f"   - PID Check:      PID {pid}")
    print(f"   - Status:         STATUS={liveness.status.value} ALIVE={liveness.is_alive} ({liveness.diagnostic})")

    if not is_dispose_mode:
        print("\n6. Inspection Summary (Read-Only Mode):")
        print("   - Mutation: None performed (read-only inspection by default).")
        disposition = (
            "ACTIVE_PROCESS_RUNNING"
            if liveness.status == LivenessStatus.VERIFIED_ALIVE
            else ("ABANDONED_STALE_LOCK" if liveness.status in (LivenessStatus.CONFIRMED_DEAD, LivenessStatus.PID_REUSED) else "INDETERMINATE_FAIL_CLOSED")
        )
        print(f"   - Lock Disposition: {disposition}")
        print("======================================================================")
        print("✅ PROCESS LIVENESS INSPECTION COMPLETED (Exit code 0)")
        print("======================================================================")
        return 0

    # DISPOSE MODE: Must be confirmed dead or PID reused (fail-closed on INDETERMINATE or ALIVE)
    if liveness.status not in (LivenessStatus.CONFIRMED_DEAD, LivenessStatus.PID_REUSED) or liveness.is_alive is not False:
        print(f"❌ Cannot dispose active lock {target_lock}: PID {pid} is not confirmed dead! (status={liveness.status.value}, is_alive={liveness.is_alive}, diagnostic: {liveness.diagnostic})", file=sys.stderr)
        return 1

    print("\n6. Executing Physical Collision-Safe Safe-Trash Archival (Rule 137):")
    with acquire_disposal_mutex(mutex_path):
        # Re-read and re-validate source immediately before mutation under shared mutex
        if not target_lock.exists():
            print(f"❌ Lock {target_lock} disappeared before disposal under mutex", file=sys.stderr)
            return 1
        re_text = target_lock.read_text(encoding="utf-8")
        try:
            re_data = json.loads(re_text)
        except (json.JSONDecodeError, ValueError) as _json_err:
            raise ValueError(f"Corrupted lock structure (invalid JSON) in {target_lock}: {_json_err}") from _json_err
        re_owner, re_token, re_created, re_pid = validate_lock_metadata(re_data, target_lock)
        re_sha = compute_file_sha256(target_lock)
        if re_sha != current_sha:
            raise ValueError(f"Lock SHA changed concurrently under mutex for {target_lock}: expected {current_sha}, got {re_sha}")
        re_liveness = check_pid_liveness(re_pid, re_created)
        if re_liveness.status not in (LivenessStatus.CONFIRMED_DEAD, LivenessStatus.PID_REUSED) or re_liveness.is_alive is not False:
            raise RuntimeError(f"Race condition detected: PID {re_pid} is not confirmed dead immediately before archival: status={re_liveness.status.value}, {re_liveness.diagnostic}")

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
