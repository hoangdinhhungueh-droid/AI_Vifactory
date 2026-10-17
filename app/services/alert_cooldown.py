"""
app/services/alert_cooldown.py — ALERT RATE LIMITER & COOLDOWN ENGINE
Mandate:
  1. Prevents repetitive Telegram alert spam when pipeline re-runs or retries fail.
  2. Tracks suppressed alert count and appends '(+N suppressed)' to next eligible alert.
  3. Records last_sent_utc ONLY after successful dispatch (or atomic reservation).
  4. Cross-platform safe: Windows & Linux compatible, fail-closed inter-process locking.
  5. Corrupt state policy: Fail-open quarantine. Corrupt state files are quarantined to *.corrupt.<ts> and state resets to {} so operator alert delivery is preserved.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.atomic_io import atomic_write_json, cleanup_corrupt_quarantines
from core.paths import resolve_state_dir

logger = logging.getLogger(__name__)

_intraprocess_lock = threading.Lock()
DEFAULT_COOLDOWN_WINDOW_SECONDS = 14400  # 4 hours


class LockTimeoutError(TimeoutError):
    """Raised when an inter-process lock cannot be acquired within the timeout window (fail-closed)."""

    pass


class CooldownReadError(OSError):
    """Raised when transient I/O or filesystem error prevents reading cooldown data."""

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
    """Zero-dependency fail-closed cross-platform inter-process advisory lock
    using fcntl.flock on POSIX and msvcrt.locking on Windows on a persistent .lock file.
    Eliminates all stale-lock TOCTOU races since the OS kernel automatically releases
    the advisory lock when the process terminates or crashes.

    WINDOWS NTFS 1-BYTE LOCK SEMANTICS (Boss Round 15 Item 9):
    On Windows (NTFS / ReFS), `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` locks exactly the first
    byte (offset 0, length 1) of the file descriptor in exclusive non-blocking mode.
    Since all cooperating processes in the factory open the same canonical `.lock` path and
    seek to byte 0 before requesting exclusive LK_NBLCK on length 1:
      1. Any subsequent process attempting `msvcrt.locking` on byte 0 receives an immediate
         `PermissionError` or `OSError` (errno 13 EACCES / errno 36 EDEADLK), preventing concurrent
         entry.
      2. If the holder process terminates unexpectedly (SIGKILL, crash, reboot), the Windows
         kernel immediately closes all open handles and releases the 1-byte file lock table entry,
         eliminating orphan/stale lock accumulation.
      3. This behavior is functionally identical to POSIX `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`
         for inter-process mutual exclusion.

    Raises LockTimeoutError on timeout (fail-closed).
    """
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    fd = None

    while True:
        try:
            # Step 1: Open/create persistent lock file.
            # Any PermissionError here is a true filesystem permission fault (fail fast, no spinning)
            fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o644)
        except PermissionError as perm_err:
            raise PermissionError(
                f"Filesystem permission error opening lock file {lock_file}: {perm_err}"
            ) from perm_err
        except OSError as os_err:
            raise OSError(f"OS error opening lock file {lock_file}: {os_err}") from os_err

        # Step 2: Acquire OS advisory lock
        try:
            if sys.platform == "win32":
                import msvcrt

                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
                    os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Successfully acquired OS advisory lock
            payload = f"PID: {os.getpid()}\nACQUIRED: {datetime.now(timezone.utc).isoformat()}\n"
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, payload.encode("utf-8"))
            break
        except (BlockingIOError, PermissionError) as lock_err:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as _e:
                    logger.debug("[alert_cooldown] lock fd close notice: %s", _e)
                fd = None

            if time.time() - start_time >= timeout:
                raise LockTimeoutError(
                    f"Timeout acquiring OS lock for {file_path} after {timeout}s (lock_file={lock_file}): {lock_err}"
                ) from lock_err
            time.sleep(poll_interval)
        except OSError as os_err:
            import errno
            if getattr(os_err, "errno", None) in (errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EBUSY):
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError as _e:
                        logger.debug("[alert_cooldown] lock fd close notice: %s", _e)
                    fd = None

                if time.time() - start_time >= timeout:
                    raise LockTimeoutError(
                        f"Timeout acquiring OS lock for {file_path} after {timeout}s (lock_file={lock_file}): {os_err}"
                    ) from os_err
                time.sleep(poll_interval)
            else:
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError as _e:
                        logger.debug("[alert_cooldown] lock fd close notice on write error: %s", _e)
                    fd = None
                raise RuntimeError(f"Unexpected error acquiring lock {lock_file}: {os_err}") from os_err
        except Exception as e:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as _e:
                    logger.debug("[alert_cooldown] lock fd close notice: %s", _e)
                fd = None
            raise RuntimeError(f"Unexpected error acquiring lock {lock_file}: {e}") from e

    try:
        yield
    finally:
        if fd is not None:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    try:
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    except OSError as _e:
                        logger.debug("[alert_cooldown] win32 unlock notice: %s", _e)
                else:
                    import fcntl

                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError as _e:
                        logger.debug("[alert_cooldown] posix unlock notice: %s", _e)
                os.close(fd)
            except OSError as close_err:
                logger.warning(f"[alert_cooldown] Error unlocking/closing fd for {lock_file}: {close_err}")



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
    except (json.JSONDecodeError, ValueError) as e:
        ts = int(datetime.now(timezone.utc).timestamp())
        corrupt_path = file_path.with_name(f"{file_path.name}.corrupt.{ts}")
        logger.error(
            f"[alert_cooldown] Corrupt cooldown file {file_path}: {e}. "
            f"Quarantining to {corrupt_path.name} (fail-open to preserve operator visibility)"
        )
        try:
            os.replace(str(file_path), str(corrupt_path))
        except OSError as ex:
            logger.warning(f"[alert_cooldown] Failed to quarantine corrupt file {file_path}: {ex}")
        cleanup_corrupt_quarantines(file_path.parent)
        return {}
    except (IOError, OSError) as io_err:
        logger.warning(f"[alert_cooldown] Transient I/O error reading cooldown file {file_path}: {io_err}")
        raise CooldownReadError(f"Transient I/O error reading cooldown file {file_path}: {io_err}") from io_err


def _write_cooldown_data(file_path: Path, data: Dict[str, Any]) -> None:
    """Atomic write via core.atomic_io.atomic_write_json (Rule 125 single truth)."""
    try:
        from core.paths import get_current_git_sha
        data["_git_sha"] = get_current_git_sha()
    except Exception as _sha_err:
        logger.debug(f"[alert_cooldown] git sha attach notice: {_sha_err}")
    atomic_write_json(file_path, data)


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

    with _intraprocess_lock, _interprocess_lock(cooldown_file):
        try:
            data = _read_cooldown_data(cooldown_file)
        except CooldownReadError as cre:
            logger.error(
                f"[alert_cooldown] Transient read error for {cooldown_file}: {cre}. "
                "Failing open without persisting state to protect file contents."
            )
            return AlertSendDecision(True, 0, "", None)

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
                    if reserve_on_send:
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
                    else:
                        # Pure read-only check: return current suppression count without mutating state
                        return AlertSendDecision(False, suppressed, "", last_sent_str)
            except (ValueError, TypeError) as _p_err:
                logger.error(
                    f"[alert_cooldown] Corrupt timestamp '{last_sent_str}' for key '{key}': {_p_err}. "
                    "Quarantining entry field and failing open to preserve operator visibility."
                )
                entry["corrupted_last_sent_utc"] = last_sent_str
                entry.pop("last_sent_utc", None)
                data[key] = entry
                _write_cooldown_data(cooldown_file, data)

        # Eligible to send!
        suffix = ""
        if suppressed > 0:
            hrs = max(1, int(round(window_seconds / 3600.0)))
            suffix = f"\n<i>ℹ️ (+{suppressed} cảnh báo tương tự đã được gom trong {hrs}h qua)</i>"

        # Atomically reserve dispatch slot if reserve_on_send=True
        if reserve_on_send:
            entry["last_sent_utc"] = now_utc.isoformat()
            entry["suppressed_since_last"] = 0
            entry.pop("last_suppressed_utc", None)
            entry["market"] = m_clean
            entry["alert_type"] = a_clean
            data[key] = entry
            _write_cooldown_data(cooldown_file, data)

        return AlertSendDecision(True, suppressed, suffix, last_sent_str)


def rollback_alert_reservation(
    alert_type: str,
    market: str,
    previous_suppressed: int = 0,
    previous_last_sent: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> bool:
    """Roll back an alert reservation if Telegram dispatch fails (Boss Item 7).
    Delta-safe: preserves suppressions recorded between reservation and rollback.
    """
    a_clean, m_clean = _validate_alert_args(alert_type, market)
    key = f"{a_clean}::{m_clean}"
    cooldown_file = _resolve_cooldown_file(state_dir)

    with _intraprocess_lock, _interprocess_lock(cooldown_file):
        try:
            data = _read_cooldown_data(cooldown_file)
        except CooldownReadError as cre:
            logger.error(
                f"[alert_cooldown] Transient read error during rollback for {cooldown_file}: {cre}. "
                "Skipping persistence to protect file contents."
            )
            return False

        entry = data.get(key, {})
        current_suppressed = int(entry.get("suppressed_since_last", 0))
        entry["last_sent_utc"] = previous_last_sent
        entry["suppressed_since_last"] = previous_suppressed + current_suppressed
        entry["market"] = m_clean
        entry["alert_type"] = a_clean
        data[key] = entry
        _write_cooldown_data(cooldown_file, data)
        logger.info(
            "[alert_cooldown] Rolled back reservation for '%s' (suppressed=%d). Next attempt is allowed.",
            key, entry["suppressed_since_last"]
        )
        return True


def emit_critical_infrastructure_alert(
    alert_type: str,
    market: str,
    alert_message: str,
    state_dir: Optional[str] = None,
    window_seconds: int = 3600,
) -> bool:
    """Emits critical infrastructure alert with warning-level logging and fallback channel (Boss Round 14 Item 4).
    Guarantees operator visibility: if Telegram broadcast fails or is unconfigured, logs to warning/critical fallback channel.
    """
    decision = should_send_alert(alert_type, market, state_dir=state_dir, window_seconds=window_seconds)
    if not decision.can_send:
        logger.info(f"[alert_cooldown] Suppressed repeat {alert_type} on {market} ({decision.suppressed} suppressed).")
        return False

    full_message = f"{alert_message}{decision.suffix}" if decision.suffix else alert_message
    sent = False
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        sent = bool(send_telegram_broadcast(full_message))
    except Exception as _e:
        logger.warning(f"[alert_cooldown] Primary Telegram broadcast failed for {alert_type} on {market}: {_e}")

    if not sent:
        logger.critical(
            f"[INFRASTRUCTURE ALERT FALLBACK] Alert '{alert_type}' on market '{market}' failed primary dispatch. "
            f"FALLBACK BROADCAST: {full_message}"
        )
        rollback_alert_reservation(
            alert_type,
            market,
            previous_suppressed=decision.suppressed,
            previous_last_sent=decision.previous_last_sent,
            state_dir=state_dir,
        )
        return False

    return True
