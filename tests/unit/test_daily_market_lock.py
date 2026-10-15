"""
tests/unit/test_daily_market_lock.py — HERMETIC UNIT TESTS FOR DAILY MARKET LOCK & QUOTA GUARD
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from app.services.daily_market_lock import (
    VN_TZ,
    acquire_in_progress,
    is_market_done_today,
    mark_completed,
    release_lock,
    resolve_state_dir,
    vn_now,
    vn_today,
)


@pytest.fixture
def temp_state_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_daily_lock_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_vn_today_timezone_shift():
    """Verify that vn_today correctly reflects Vietnam time (UTC+7) across UTC midnight."""
    # 2026-10-15 18:30 UTC -> 2026-10-16 01:30 VN
    utc_night = datetime(2026, 10, 15, 18, 30, tzinfo=timezone.utc)
    assert vn_today(utc_night) == "2026-10-16"

    # 2026-10-15 15:00 UTC -> 2026-10-15 22:00 VN
    utc_day = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    assert vn_today(utc_day) == "2026-10-15"


def test_not_produced_yet_initial_state(temp_state_dir):
    """When no locks or episodes exist, is_market_done_today should return False."""
    done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
    assert done is False
    assert reason == "not_produced_yet"


def test_acquire_in_progress_and_completion(temp_state_dir):
    """Test standard flow: acquire in_progress -> check done -> mark completed -> check done."""
    # Acquire IN_PROGRESS
    ok = acquire_in_progress("EN", topic_id="EN_TEMP_test1", state_dir=temp_state_dir)
    assert ok is True

    # Should report lock_in_progress (hence done=True to skip duplicate runs)
    done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
    assert done is True
    assert reason == "lock_in_progress"
    assert details["topic_id"] == "EN_TEMP_test1"

    # Mark COMPLETED
    ok = mark_completed("EN", topic_id="EN_EP0001_final", state_dir=temp_state_dir)
    assert ok is True

    # Should report lock_completed
    done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
    assert done is True
    assert reason == "lock_completed"
    assert details["topic_id"] == "EN_EP0001_final"


def test_stale_in_progress_lock_expires(temp_state_dir):
    """An IN_PROGRESS lock older than ttl_seconds should be treated as stale."""
    # Create lock file with creation time 7 hours ago
    past_utc = datetime.now(timezone.utc) - timedelta(hours=7)
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"EN_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({
        "market": "EN",
        "vn_date": today_vn,
        "status": "IN_PROGRESS",
        "topic_id": "EN_TEMP_stale",
        "created_at_utc": past_utc.isoformat(),
        "ttl_seconds": 21600  # 6 hours
    }), encoding="utf-8")

    done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
    assert done is False
    assert reason == "stale_lock"


def test_corrupt_lock_file_fails_closed(temp_state_dir):
    """A corrupt lock file should fail-closed (return done=True) to prevent runaway crawls."""
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"EN_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text("{invalid json content!!!", encoding="utf-8")

    done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
    assert done is True
    assert reason == "corrupt_lock_fail_closed"


def test_force_flag_bypasses_lock(temp_state_dir):
    """The force flag should override COMPLETED lock."""
    mark_completed("EN", topic_id="EN_EP0001_done", state_dir=temp_state_dir)

    # Without force -> True
    done, _, _ = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
    assert done is True

    # With force=True -> False
    done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, force=True, check_registry=False)
    assert done is False
    assert reason == "forced_override"

    # With env var B1_FORCE_CRAWL=1 -> False
    os.environ["B1_FORCE_CRAWL"] = "1"
    try:
        done, reason, _ = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False)
        assert done is False
        assert reason == "forced_override"
    finally:
        os.environ.pop("B1_FORCE_CRAWL", None)


def test_release_lock(temp_state_dir):
    """Releasing lock removes the file so market can run again."""
    acquire_in_progress("JP", topic_id="JP_TEMP_001", state_dir=temp_state_dir)
    done, _, _ = is_market_done_today("JP", state_dir=temp_state_dir, check_registry=False)
    assert done is True

    released = release_lock("JP", state_dir=temp_state_dir)
    assert released is True

    done, reason, _ = is_market_done_today("JP", state_dir=temp_state_dir, check_registry=False)
    assert done is False
    assert reason == "not_produced_yet"
