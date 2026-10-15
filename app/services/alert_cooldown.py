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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_WINDOW_SECONDS = 14400  # 4 hours


def _resolve_cooldown_file(state_dir: Optional[str] = None) -> Path:
    from app.services.daily_market_lock import resolve_state_dir
    base = resolve_state_dir(state_dir)
    return base / "alert_cooldown.json"


def _read_cooldown_data(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception as e:
        logger.warning(f"[alert_cooldown] Error reading {file_path}: {e}")
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


def should_send_alert(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    window_seconds: int = DEFAULT_COOLDOWN_WINDOW_SECONDS,
    now: Optional[datetime] = None,
) -> Tuple[bool, int, str]:
    """Check if an alert of type `alert_type` for `market` is allowed to be sent.

    Returns:
        (can_send, suppressed_count, formatted_suffix)
        - can_send: True if window has passed or first time; False if throttled.
        - suppressed_count: number of alerts suppressed during the cooldown window.
        - formatted_suffix: formatted note e.g. " (+3 suppressed alerts in the last 4h)"
    """
    if os.getenv("DISABLE_ALERT_COOLDOWN") == "1":
        return True, 0, ""

    m_up = (market or "GLOBAL").upper()
    key = f"{alert_type}::{m_up}"
    cooldown_file = _resolve_cooldown_file(state_dir)
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
                # Suppress! Increment counter and save
                entry["suppressed_since_last"] = suppressed + 1
                entry["last_suppressed_utc"] = now_utc.isoformat()
                data[key] = entry
                _write_cooldown_data(cooldown_file, data)
                logger.info(
                    f"[alert_cooldown] Throttled alert '{key}' (elapsed {int(elapsed)}s < {window_seconds}s). "
                    f"Total suppressed: {suppressed + 1}"
                )
                return False, suppressed + 1, ""
        except Exception as _p_err:
            logger.warning(f"[alert_cooldown] Error parsing timestamp: {_p_err}")

    # Eligible to send!
    suffix = ""
    if suppressed > 0:
        hrs = max(1, int(round(window_seconds / 3600.0)))
        suffix = f"\n<i>ℹ️ (+{suppressed} cảnh báo tương tự đã được gom trong {hrs}h qua)</i>"

    return True, suppressed, suffix


def record_alert_sent(
    alert_type: str,
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Record that an alert was successfully dispatched to Telegram."""
    m_up = (market or "GLOBAL").upper()
    key = f"{alert_type}::{m_up}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    data = _read_cooldown_data(cooldown_file)

    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    data[key] = {
        "last_sent_utc": now_utc.isoformat(),
        "suppressed_since_last": 0,
        "market": m_up,
        "alert_type": alert_type,
    }
    return _write_cooldown_data(cooldown_file, data)


def reset_alert_cooldown(alert_type: str, market: str, state_dir: Optional[str] = None) -> bool:
    """Reset cooldown state for testing or manual override."""
    m_up = (market or "GLOBAL").upper()
    key = f"{alert_type}::{m_up}"
    cooldown_file = _resolve_cooldown_file(state_dir)
    data = _read_cooldown_data(cooldown_file)
    if key in data:
        del data[key]
        return _write_cooldown_data(cooldown_file, data)
    return True
