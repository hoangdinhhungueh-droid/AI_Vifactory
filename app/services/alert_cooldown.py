"""
app/services/alert_cooldown.py — ALERT RATE LIMITER & COOLDOWN ENGINE
Mandate:
  1. Prevents repetitive Telegram alert spam when pipeline re-runs or retries fail.
  2. Tracks suppressed alert count and appends '(+N suppressed)' to next eligible alert.
  3. Records last_sent_utc ONLY after successful dispatch.
  4. Cross-platform safe: Windows & Linux compatible.
"""

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_WINDOW_SECONDS = 14400  # 4 hours


def _validate_market(market: Any) -> str:
    """Validate and normalize market string; reject None, empty or non-string."""
    if not market or not isinstance(market, str) or not market.strip():
        raise ValueError(f"Market identifier must be a non-empty string, got: {market!r}")
    return market.strip().upper()


def _resolve_cooldown_file(state_dir: Optional[str] = None) -> Path:
    from app.services.daily_market_lock import resolve_state_dir
    base = resolve_state_dir(state_dir)
    return base / "alert_cooldown.json"


@contextmanager
def _interprocess_lock(file_path: Path, timeout: float = 10.0, poll_interval: float = 0.05):
    """Zero-dependency cross-platform inter-process lock using O_CREAT | O_EXCL.
    Guarantees atomic serialization of read-modify-write across worker processes.
    """
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, f"{os.getpid()} {time.time()}".encode("utf-8"))
            break
        except FileExistsError:
            try:
                mtime = os.path.getmtime(lock_file)
                if time.time() - mtime > 30.0:  # Stale lock cleanup
                    try:
                        os.unlink(lock_file)
                    except OSError:
                        pass
            except OSError:
                pass
            if time.time() - start_time >= timeout:
                logger.warning(f"[alert_cooldown] Timeout acquiring lock {lock_file}, proceeding fail-safe")
                break
            time.sleep(poll_interval)
        except Exception as e:
            logger.warning(f"[alert_cooldown] Error acquiring lock {lock_file}: {e}")
            break
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                if lock_file.exists():
                    os.unlink(lock_file)
            except OSError:
                pass


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
            f"Quarantining to {corrupt_path.name}"
        )
        try:
            os.replace(str(file_path), str(corrupt_path))
        except OSError as ex:
            logger.warning(f"[alert_cooldown] Failed to quarantine corrupt file {file_path}: {ex}")
        return {}


def _write_cooldown_data(file_path: Path, data: Dict[str, Any]) -> bool:
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = file_path.with_suffix(f".tmp_{os.getpid()}_{int(datetime.now(timezone.utc).timestamp())}")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, file_path)
        return True
    except Exception as e:
        logger.error(f"[alert_cooldown] Error writing {file_path}: {e}")
        return False


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
    if os.getenv("DISABLE_ALERT_COOLDOWN") == "1":
        return True, 0, ""

    m_up = _validate_market(market)
    key = f"{alert_type}::{m_up}"
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
    m_up = _validate_market(market)
    key = f"{alert_type}::{m_up}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        entry = data.get(key, {})
        current_suppressed = int(entry.get("suppressed_since_last", 0))
        new_suppressed = current_suppressed + 1
        entry["suppressed_since_last"] = new_suppressed
        entry["last_suppressed_utc"] = now_utc.isoformat()
        entry["market"] = m_up
        entry["alert_type"] = alert_type
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
) -> Tuple[bool, int, str]:
    """Check if an alert of type `alert_type` for `market` is allowed to be sent.
    If not eligible, atomically records the suppression.

    Returns:
        (can_send, suppressed_count, formatted_suffix)
    """
    can_send, suppressed, suffix = check_alert_eligibility(
        alert_type=alert_type,
        market=market,
        state_dir=state_dir,
        window_seconds=window_seconds,
        now=now,
    )
    if not can_send:
        new_count = record_alert_suppressed(
            alert_type=alert_type,
            market=market,
            state_dir=state_dir,
            now=now,
        )
        return False, new_count, ""

    return True, suppressed, suffix


def record_alert_sent(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Record that an alert was successfully dispatched to Telegram."""
    m_up = _validate_market(market)
    key = f"{alert_type}::{m_up}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)

    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        data[key] = {
            "last_sent_utc": now_utc.isoformat(),
            "suppressed_since_last": 0,
            "market": m_up,
            "alert_type": alert_type,
        }
        return _write_cooldown_data(cooldown_file, data)


def reset_alert_cooldown(alert_type: str, market: str, state_dir: Optional[str] = None) -> bool:
    """Reset cooldown state for testing or manual override."""
    m_up = _validate_market(market)
    key = f"{alert_type}::{m_up}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    with _interprocess_lock(cooldown_file):
        data = _read_cooldown_data(cooldown_file)
        if key in data:
            del data[key]
            return _write_cooldown_data(cooldown_file, data)
    return True

