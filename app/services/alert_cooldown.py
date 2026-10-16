"""
app/services/alert_cooldown.py — ALERT RATE LIMITER & COOLDOWN ENGINE
Mandate:
  1. Prevents repetitive Telegram alert spam when pipeline re-runs or retries fail.
  2. Tracks suppressed alert count and appends '(+N suppressed)' to next eligible alert.
  3. Records last_sent_utc ONLY after successful dispatch (or atomic reservation).
  4. Cross-platform safe: Windows & Linux compatible, fail-closed inter-process locking.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.atomic_io import atomic_write_json, cleanup_corrupt_quarantines
from core.paths import resolve_state_dir

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_WINDOW_SECONDS = 14400  # 4 hours


class LockTimeoutError(TimeoutError):
    """Raised when an inter-process lock cannot be acquired within the timeout window (fail-closed)."""

    pass


class AlertSendDecision:
    """Encapsulates alert sending decision with backward-compatible tuple unpacking (Boss Item 19)."""

    def __init__(
        self,
        can_send: bool,
        suppressed: int,
        suffix: str,
        previous_last_sent: Optional[str] = None,
    ):
        self.can_send = bool(can_send)
        self.suppressed = int(suppressed)
        self.suffix = str(suffix)
        self.previous_last_sent = previous_last_sent

    def __bool__(self) -> bool:
        return self.can_send

    def __iter__(self):
        return iter((self.can_send, self.suppressed, self.suffix))

    def __getitem__(self, item):
        return (self.can_send, self.suppressed, self.suffix)[item]

    def __repr__(self) -> str:
        return (
            f"AlertSendDecision(can_send={self.can_send}, suppressed={self.suppressed}, "
            f"suffix={self.suffix!r}, previous_last_sent={self.previous_last_sent!r})"
        )


def _validate_alert_args(alert_type: Any, market: Any) -> Tuple[str, str]:
    """Validate and normalize alert_type and market strings; reject None, empty, whitespace, or non-string."""
    if not alert_type or not isinstance(alert_type, str) or not alert_type.strip():
        raise ValueError(f"Alert type identifier must be a non-empty string, got: {alert_type!r}")
    if not market or not isinstance(market, str) or not market.strip():
        raise ValueError(f"Market identifier must be a non-empty string, got: {market!r}")
    return alert_type.strip().lower(), market.strip().upper()


def _resolve_cooldown_file(state_dir: Optional[str] = None) -> Path:
    base = resolve_state_dir(state_dir)
    return base / "alert_cooldown.json"


def is_pid_alive(pid: int) -> bool:
    """Platform-safe check whether process with given PID is currently alive without terminating it.

    Windows: Uses ctypes.WinDLL('kernel32', use_last_error=True) and OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION).
             Treats ONLY ERROR_INVALID_PARAMETER (87) as dead PID (Rule 126 Windows Safety).
             Returns True (fail-closed) for ERROR_ACCESS_DENIED or any other error.
    Linux/POSIX: Uses os.kill(pid, 0) handling PermissionError (alive) and ProcessLookupError / ESRCH (dead).
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        ERROR_INVALID_PARAMETER = 87
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_proc:
            err = ctypes.get_last_error()
            if err == ERROR_INVALID_PARAMETER:
                return False
            # Fail-closed for all other errors (ACCESS_DENIED, etc.)
            return True
        try:
            exit_code = ctypes.wintypes.DWORD()
            if kernel32.GetExitCodeProcess(h_proc, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return True  # Fail-closed if GetExitCodeProcess fails
        finally:
            kernel32.CloseHandle(h_proc)
    else:
        import errno
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            # Process exists and is running under another user / privilege
            return True
        except ProcessLookupError:
            # ESRCH: Process does not exist
            return False
        except OSError as e:
            if e.errno == errno.EPERM:
                return True
            if e.errno == errno.ESRCH:
                return False
            return True


@contextmanager
def _interprocess_lock(file_path: Path, timeout: float = 10.0, poll_interval: float = 0.05):
    """Zero-dependency fail-closed cross-platform inter-process lock using O_CREAT | O_EXCL.
    Writes unique holder token (pid:uuid).
    Unlinks only if token matches in finally.
    Raises LockTimeoutError on timeout (fail-closed).
    """
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}:{uuid.uuid4().hex}"
    start_time = time.time()
    fd = None
    acquired = False

    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                os.write(fd, token.encode("utf-8"))
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                fd = None
                lock_file.unlink(missing_ok=True)
                raise
            acquired = True
            break
        except (FileExistsError, PermissionError):
            now_ts = time.time()
            # Stale lock check: if lock file age exceeds 30.0s and dead pid
            try:
                mtime = os.path.getmtime(lock_file)
                if now_ts - mtime > 30.0:
                    try:
                        with open(lock_file, "r", encoding="utf-8") as rf:
                            raw = rf.read().strip()
                        parts = raw.split(":")
                        dead_pid = False
                        if parts and parts[0].isdigit():
                            pid = int(parts[0])
                            dead_pid = not is_pid_alive(pid)
                        else:
                            # Empty or unparseable lock file older than 30.0s is considered dead
                            dead_pid = True
                            pid = 0

                        if dead_pid:
                            # TOCTOU-safe reclaim: atomically rename stale lock_file to unique tombstone
                            tombstone = lock_file.with_name(f"{lock_file.name}.tombstone.{uuid.uuid4().hex}")
                            try:
                                os.rename(str(lock_file), str(tombstone))
                                # We won the race to reclaim this stale lock
                                try:
                                    with open(tombstone, "r", encoding="utf-8") as tf:
                                        tomb_content = tf.read().strip()
                                    if tomb_content == raw:
                                        logger.warning(
                                            "[alert_cooldown] Reclaimed dead PID %s lock %s via tombstone %s",
                                            pid, lock_file, tombstone.name,
                                        )
                                        os.unlink(str(tombstone))
                                    else:
                                        # Content mismatch: another process updated lock between read and rename.
                                        # Restore lock_file immediately so we do not hijack a live holder's lock (Boss Item 18).
                                        logger.error(
                                            "[alert_cooldown] Stale lock mismatch: expected %r, found %r. Restoring lock_file!",
                                            raw, tomb_content,
                                        )
                                        try:
                                            os.replace(str(tombstone), str(lock_file))
                                        except OSError as rest_err:
                                            logger.error("[alert_cooldown] Failed to restore lock_file %s: %s", lock_file, rest_err)
                                except OSError as t_err:
                                    logger.warning("[alert_cooldown] Error reading/unlinking tombstone %s: %s", tombstone, t_err)
                            except (FileNotFoundError, OSError) as ren_err:
                                logger.debug("[alert_cooldown] Stale lock race on rename %s: %s", lock_file, ren_err)
                    except OSError as r_err:
                        logger.warning("[alert_cooldown] Error checking stale lock %s: %s", lock_file, r_err)
            except OSError as stat_err:
                logger.warning("[alert_cooldown] Error stating lock file %s: %s", lock_file, stat_err)

            if time.time() - start_time >= timeout:
                raise LockTimeoutError(
                    f"Timeout acquiring lock for {file_path} after {timeout}s (lock_file={lock_file})"
                )
            time.sleep(poll_interval)
        except Exception as e:
            raise RuntimeError(f"Unexpected error acquiring lock {lock_file}: {e}") from e

    try:
        yield
    finally:
        if acquired and fd is not None:
            try:
                os.close(fd)
            except OSError as close_err:
                logger.warning(f"[alert_cooldown] Error closing fd {fd} for {lock_file}: {close_err}")
            # Only unlink if the token matches our token (prevent unlinking someone else's reclaimed lock)
            try:
                if lock_file.exists():
                    with open(lock_file, "r", encoding="utf-8") as rf:
                        existing_token = rf.read().strip()
                    if existing_token == token:
                        os.unlink(lock_file)
            except OSError as unlink_err:
                logger.warning(f"[alert_cooldown] Error unlinking lock_file {lock_file}: {unlink_err}")


def _read_cooldown_data(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict root, got {type(data).__name__}")
            return data
    except Exception as e:
        ts = int(datetime.now(timezone.utc).timestamp())
        corrupt_path = file_path.with_name(f"{file_path.name}.corrupt.{ts}")
        logger.error(
            f"[alert_cooldown] Corrupt cooldown file {file_path}: {e}. "
            f"Quarantining to {corrupt_path.name} (fail-closed)"
        )
        try:
            os.replace(str(file_path), str(corrupt_path))
        except OSError as ex:
            logger.warning(f"[alert_cooldown] Failed to quarantine corrupt file {file_path}: {ex}")
        cleanup_corrupt_quarantines(file_path.parent)
        return {}


def _write_cooldown_data(file_path: Path, data: Dict[str, Any]) -> None:
    """Atomic write via core.atomic_io.atomic_write_json (Rule 125 single truth)."""
    atomic_write_json(file_path, data)


def check_alert_eligibility(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    window_seconds: int = DEFAULT_COOLDOWN_WINDOW_SECONDS,
    now: Optional[datetime] = None,
) -> Tuple[bool, int, str]:
    """Pure read-only check of alert eligibility. Does NOT record suppression or mutate state.

    Returns:
        (can_send, suppressed_count, formatted_suffix)
        - can_send: True if window has passed or first alert; False if throttled.
        - suppressed_count: number of alerts suppressed during the cooldown window.
        - formatted_suffix: formatted note e.g. " (+3 cảnh báo tương tự đã được gom trong 4h qua)"
    """
    a_clean, m_clean = _validate_alert_args(alert_type, market)

    if os.getenv("DISABLE_ALERT_COOLDOWN") == "1":
        return True, 0, ""

    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)

    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    entry = data.get(key, {})
    last_sent_str = entry.get("last_sent_utc")
    suppressed = int(entry.get("suppressed_since_last", 0))

    if last_sent_str:
        try:
            last_dt = datetime.fromisoformat(last_sent_str)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            elapsed = (now_utc - last_dt).total_seconds()
            if elapsed < window_seconds:
                return False, suppressed, ""
        except Exception as _p_err:
            logger.warning(f"[alert_cooldown] Error parsing timestamp: {_p_err}")

    # Eligible to send!
    suffix = ""
    if suppressed > 0:
        hrs = max(1, int(round(window_seconds / 3600.0)))
        suffix = f"\n<i>ℹ️ (+{suppressed} cảnh báo tương tự đã được gom trong {hrs}h qua)</i>"

    return True, suppressed, suffix


def record_alert_suppressed(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
) -> int:
    """Explicitly record that an alert was suppressed, incrementing suppressed_since_last atomically.
    Returns the updated suppressed_since_last count.
    """
    a_clean, m_clean = _validate_alert_args(alert_type, market)
    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        entry = data.get(key, {})
        current_suppressed = int(entry.get("suppressed_since_last", 0))
        new_suppressed = current_suppressed + 1
        entry["suppressed_since_last"] = new_suppressed
        entry["last_suppressed_utc"] = now_utc.isoformat()
        entry["market"] = m_clean
        entry["alert_type"] = a_clean
        data[key] = entry
        _write_cooldown_data(cooldown_file, data)

    logger.info(f"[alert_cooldown] Recorded suppression for '{key}'. Total suppressed: {new_suppressed}")
    return new_suppressed


def should_send_alert(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    window_seconds: int = DEFAULT_COOLDOWN_WINDOW_SECONDS,
    now: Optional[datetime] = None,
    reserve_on_send: bool = True,
) -> AlertSendDecision:
    """Atomic check, suppression increment, and send reservation inside a SINGLE lock acquisition.
    Guarantees that under N parallel callers racing at the same instant, exactly ONE caller
    receives can_send=True, while all others are immediately throttled and counted as suppressed.

    Returns:
        AlertSendDecision(can_send, suppressed_count, formatted_suffix, previous_last_sent)
        Supports backward-compatible 3-element unpacking: (can_send, suppressed_count, suffix).
    """
    a_clean, m_clean = _validate_alert_args(alert_type, market)

    if os.getenv("DISABLE_ALERT_COOLDOWN") == "1":
        return AlertSendDecision(True, 0, "", None)

    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        entry = data.get(key, {})
        last_sent_str = entry.get("last_sent_utc")
        suppressed = int(entry.get("suppressed_since_last", 0))

        if last_sent_str:
            try:
                last_dt = datetime.fromisoformat(last_sent_str)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = (now_utc - last_dt).total_seconds()
                if elapsed < window_seconds:
                    # Throttled! Atomically increment suppressed counter and persist
                    new_suppressed = suppressed + 1
                    entry["suppressed_since_last"] = new_suppressed
                    entry["last_suppressed_utc"] = now_utc.isoformat()
                    entry["market"] = m_clean
                    entry["alert_type"] = a_clean
                    data[key] = entry
                    _write_cooldown_data(cooldown_file, data)
                    logger.info(
                        f"[alert_cooldown] Throttled alert '{key}' (elapsed {int(elapsed)}s < {window_seconds}s). "
                        f"Total suppressed: {new_suppressed}"
                    )
                    return AlertSendDecision(False, new_suppressed, "", last_sent_str)
            except Exception as _p_err:
                logger.error(f"[alert_cooldown] Error parsing timestamp '{last_sent_str}': {_p_err}. Failing closed.")
                return AlertSendDecision(False, suppressed, "", last_sent_str)

        # Eligible to send!
        suffix = ""
        if suppressed > 0:
            hrs = max(1, int(round(window_seconds / 3600.0)))
            suffix = f"\n<i>ℹ️ (+{suppressed} cảnh báo tương tự đã được gom trong {hrs}h qua)</i>"

        # Atomically reserve dispatch slot if reserve_on_send=True
        if reserve_on_send:
            entry["last_sent_utc"] = now_utc.isoformat()
            entry["suppressed_since_last"] = 0
            entry["market"] = m_clean
            entry["alert_type"] = a_clean
            data[key] = entry
            _write_cooldown_data(cooldown_file, data)

        return AlertSendDecision(True, suppressed, suffix, last_sent_str)


def record_alert_sent(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
) -> None:
    """Record that an alert was successfully dispatched to Telegram, preserving existing fields (Boss Item 19)."""
    a_clean, m_clean = _validate_alert_args(alert_type, market)
    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        entry = data.get(key, {})
        entry["last_sent_utc"] = now_utc.isoformat()
        entry["suppressed_since_last"] = 0
        entry["market"] = m_clean
        entry["alert_type"] = a_clean
        data[key] = entry
        _write_cooldown_data(cooldown_file, data)


def rollback_alert_reservation(
    alert_type: str,
    market: str,
    previous_suppressed: int = 0,
    previous_last_sent: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> bool:
    """Roll back an alert reservation if Telegram dispatch fails (Boss Item 7).
    Restores prior last_sent_utc and suppressed count so subsequent attempts are not silenced.
    """
    a_clean, m_clean = _validate_alert_args(alert_type, market)
    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        entry = data.get(key, {})
        entry["last_sent_utc"] = previous_last_sent
        entry["suppressed_since_last"] = previous_suppressed
        entry["market"] = m_clean
        entry["alert_type"] = a_clean
        data[key] = entry
        _write_cooldown_data(cooldown_file, data)
        logger.info("[alert_cooldown] Rolled back reservation for '%s'. Next attempt is allowed.", key)
        return True


def reset_alert_cooldown(alert_type: str, market: str, state_dir: Optional[str] = None) -> bool:
    """Reset cooldown state for testing or manual override."""
    a_clean, m_clean = _validate_alert_args(alert_type, market)
    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        if key in data:
            del data[key]
            _write_cooldown_data(cooldown_file, data)
    return True
