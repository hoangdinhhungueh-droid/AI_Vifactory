""""rate_risk_controller.py — Upload rate & risk controller (Phase 4.3).

Enforces per-platform upload rate limits, prevents spam-like patterns,
tracks strike/risk state, and coordinates with n8n scheduling. Uses a
JSON state file (same pattern as publish_ledger.py / upload_mode.py).

Public API:
    can_upload(platform, notify=None) -> RateCheckResult
    record_upload(platform, video_id, notify=None) -> bool
    record_failure(platform, error_type, notify=None) -> bool
    record_strike(platform, reason, notify=None) -> bool
    get_platform_status(platform) -> dict
    get_all_status() -> dict
    RateCheckResult: {allowed: bool, reason: str, wait_seconds: int}

Env:
    VF_RATE_CONTROLLER=1  (default on)
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vf.rate_risk")

_STATE_FILE = Path(os.getenv(
    "RATE_RISK_STATE_FILE",
    "/root/video_factory/db/rate_risk_state.json",
))


def _enabled() -> bool:
    return os.getenv("VF_RATE_CONTROLLER", "1") == "1"


# ---- Per-platform rate limits (conservative defaults) ----

PLATFORM_RATE_LIMITS: Dict[str, Dict[str, Any]] = {
    "youtube": {
        "daily_upload_limit": 6,
        "min_interval_seconds": 600,
        "max_consecutive_failures": 3,
        "cooldown_after_failures_seconds": 3600,
        "strike_threshold": 1,
        "strike_cooldown_seconds": 86400,
    },
    "youtube_shorts": {
        "daily_upload_limit": 6,
        "min_interval_seconds": 300,
        "max_consecutive_failures": 3,
        "cooldown_after_failures_seconds": 3600,
        "strike_threshold": 1,
        "strike_cooldown_seconds": 86400,
    },
    "dailymotion": {
        "daily_upload_limit": 10,
        "min_interval_seconds": 300,
        "max_consecutive_failures": 5,
        "cooldown_after_failures_seconds": 1800,
        "strike_threshold": 2,
        "strike_cooldown_seconds": 43200,
    },
    "facebook_reels": {
        "daily_upload_limit": 5,
        "min_interval_seconds": 600,
        "max_consecutive_failures": 3,
        "cooldown_after_failures_seconds": 3600,
        "strike_threshold": 1,
        "strike_cooldown_seconds": 86400,
    },
    "instagram_reels": {
        "daily_upload_limit": 5,
        "min_interval_seconds": 600,
        "max_consecutive_failures": 3,
        "cooldown_after_failures_seconds": 3600,
        "strike_threshold": 1,
        "strike_cooldown_seconds": 86400,
    },
}


class RateCheckResult:
    """Result of a rate check — never raises."""
    def __init__(self, allowed: bool, reason: str = "", wait_seconds: int = 0):
        self.allowed = allowed
        self.reason = reason
        self.wait_seconds = wait_seconds

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "wait_seconds": self.wait_seconds,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> float:
    return time.time()


def _load_state() -> Dict[str, Any]:
    """Load state JSON. FAIL-SAFE: returns empty state on any error."""
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text())
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.warning("[rate_risk] state load failed: %s", e)
    return {}


def _save_state(state: Dict[str, Any]) -> bool:
    """Save state JSON. FAIL-SAFE."""
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        logger.warning("[rate_risk] state save failed: %s", e)
        return False


def _ensure_platform_state(state: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Ensure platform key exists in state and return it."""
    if "platforms" not in state:
        state["platforms"] = {}
    if platform not in state["platforms"]:
        state["platforms"][platform] = {
            "uploads_today": [],
            "uploads_today_date": "",
            "last_upload_ts": 0,
            "consecutive_failures": 0,
            "cooldown_until": 0,
            "strikes": [],
            "strike_paused_until": 0,
        }
    return state["platforms"][platform]


def _reset_daily_if_needed(pstate: Dict[str, Any]):
    """Reset daily upload count if it is a new UTC day."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if pstate.get("uploads_today_date") != today:
        pstate["uploads_today"] = []
        pstate["uploads_today_date"] = today


def can_upload(platform: str, notify=None) -> RateCheckResult:
    """Check if an upload is allowed right now for the given platform.

    Returns RateCheckResult with .allowed=True if upload may proceed,
    or .allowed=False with reason and wait_seconds if blocked.
    """
    if not _enabled():
        return RateCheckResult(True, "rate controller disabled")

    rules = PLATFORM_RATE_LIMITS.get(platform)
    if not rules:
        return RateCheckResult(True, f"no rate rules for {platform}")

    state = _load_state()
    pstate = _ensure_platform_state(state, platform)
    _reset_daily_if_needed(pstate)
    now = _now_ts()

    # 1. Strike check
    strike_until = pstate.get("strike_paused_until", 0)
    if strike_until > now:
        wait = int(strike_until - now)
        reason = f"platform paused due to strike ({wait}s remaining)"
        if notify:
            try:
                notify(f"RATE RISK [{platform}]: {reason}")
            except Exception:
                pass
        return RateCheckResult(False, reason, wait)

    # 2. Cooldown after consecutive failures
    cooldown_until = pstate.get("cooldown_until", 0)
    if cooldown_until > now:
        wait = int(cooldown_until - now)
        reason = f"cooldown after failures ({wait}s remaining)"
        return RateCheckResult(False, reason, wait)

    # 3. Daily upload limit
    uploads_today = pstate.get("uploads_today", [])
    if len(uploads_today) >= rules["daily_upload_limit"]:
        now_dt = datetime.now(timezone.utc)
        tomorrow = (now_dt + timedelta(days=1)).replace(hour=1, minute=30, second=0, microsecond=0)
        wait = int((tomorrow - now_dt).total_seconds())
        reason = f"daily limit reached ({len(uploads_today)}/{rules['daily_upload_limit']})"
        return RateCheckResult(False, reason, max(wait, 0))

    # 4. Minimum interval between uploads
    last_ts = pstate.get("last_upload_ts", 0)
    elapsed = now - last_ts
    min_interval = rules["min_interval_seconds"]
    if elapsed < min_interval:
        wait = int(min_interval - elapsed)
        reason = f"min interval not met ({wait}s remaining)"
        return RateCheckResult(False, reason, wait)

    return RateCheckResult(True)


def record_upload(platform: str, video_id: str = "", notify=None) -> bool:
    """Record a successful upload. Resets consecutive_failures."""
    state = _load_state()
    pstate = _ensure_platform_state(state, platform)
    _reset_daily_if_needed(pstate)
    pstate["uploads_today"].append({
        "video_id": video_id,
        "ts": _now(),
    })
    pstate["last_upload_ts"] = _now_ts()
    pstate["consecutive_failures"] = 0
    logger.info("[rate_risk] %s upload recorded: %s (today: %d)",
                platform, video_id, len(pstate["uploads_today"]))
    return _save_state(state)


def record_failure(platform: str, error_type: str = "", notify=None) -> bool:
    """Record a failed upload. Increments consecutive_failures, may trigger cooldown."""
    rules = PLATFORM_RATE_LIMITS.get(platform, {})
    state = _load_state()
    pstate = _ensure_platform_state(state, platform)
    pstate["consecutive_failures"] = pstate.get("consecutive_failures", 0) + 1
    failures = pstate["consecutive_failures"]
    max_failures = rules.get("max_consecutive_failures", 3)

    if failures >= max_failures:
        cooldown = rules.get("cooldown_after_failures_seconds", 3600)
        pstate["cooldown_until"] = _now_ts() + cooldown
        logger.warning(
            "[rate_risk] %s cooldown triggered after %d consecutive failures (%ds)",
            platform, failures, cooldown,
        )
        if notify:
            try:
                notify(f"RATE RISK [{platform}]: cooldown triggered after {failures} failures ({cooldown}s)")
            except Exception:
                pass

    logger.info("[rate_risk] %s failure recorded: %s (consecutive: %d)",
                platform, error_type, failures)
    return _save_state(state)


def record_strike(platform: str, reason: str = "", notify=None) -> bool:
    """Record a platform strike. Pauses the platform for strike_cooldown_seconds."""
    rules = PLATFORM_RATE_LIMITS.get(platform, {})
    state = _load_state()
    pstate = _ensure_platform_state(state, platform)
    pstate["strikes"].append({
        "reason": reason,
        "ts": _now(),
    })
    cooldown = rules.get("strike_cooldown_seconds", 86400)
    pstate["strike_paused_until"] = _now_ts() + cooldown
    logger.warning(
        "[rate_risk] %s STRIKE recorded: %s (paused for %ds)",
        platform, reason, cooldown,
    )
    if notify:
        try:
            notify(f"RATE RISK [{platform}]: STRIKE - {reason}. Platform paused for {cooldown // 3600}h.")
        except Exception:
            pass
    return _save_state(state)


def get_platform_status(platform: str) -> Dict[str, Any]:
    """Get current status for a platform."""
    if not _enabled():
        return {"enabled": False}
    state = _load_state()
    pstate = _ensure_platform_state(state, platform)
    _reset_daily_if_needed(pstate)
    rules = PLATFORM_RATE_LIMITS.get(platform, {})
    now = _now_ts()
    return {
        "enabled": True,
        "platform": platform,
        "uploads_today": len(pstate.get("uploads_today", [])),
        "daily_limit": rules.get("daily_upload_limit", 0),
        "last_upload_ts": pstate.get("last_upload_ts", 0),
        "consecutive_failures": pstate.get("consecutive_failures", 0),
        "cooldown_active": pstate.get("cooldown_until", 0) > now,
        "cooldown_remaining_s": max(0, int(pstate.get("cooldown_until", 0) - now)),
        "strikes": len(pstate.get("strikes", [])),
        "strike_paused": pstate.get("strike_paused_until", 0) > now,
        "strike_paused_remaining_s": max(0, int(pstate.get("strike_paused_until", 0) - now)),
    }


def get_all_status() -> Dict[str, Any]:
    """Get status for all known platforms."""
    return {p: get_platform_status(p) for p in PLATFORM_RATE_LIMITS}
