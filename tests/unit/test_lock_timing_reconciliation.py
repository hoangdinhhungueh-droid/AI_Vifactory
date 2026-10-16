#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_lock_timing_reconciliation.py
Unit tests verifying lock timing reconciliation, dynamic hard_max vs TTL,
force-displacement metadata tracking, and market normalization (Boss Round 11 & Rule 128).
"""

import json
import shutil
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch
import pytest

from app.services.daily_market_lock import (
    acquire_in_progress,
    is_market_done_today,
    _is_lock_stale,
    _validate_market,
    _get_lock_file_path,
)


@pytest.fixture
def temp_state_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_lock_reconcile_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_market_normalization():
    """Verify that market aliases are normalized (JA -> JP, KO -> KR, lowercase -> uppercase)."""
    assert _validate_market("JA") == "JP"
    assert _validate_market("ja") == "JP"
    assert _validate_market("KO") == "KR"
    assert _validate_market("ko") == "KR"
    assert _validate_market("us") == "US"
    assert _validate_market("US") == "US"
    assert _validate_market("vn") == "VN"


def test_live_holder_inside_ttl_not_stale(temp_state_dir):
    """A lock holder older than 2 hours but within its TTL (e.g. 2.5 hours into a 4h TTL)
    must NOT be considered stale if the process is alive.
    """
    now = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    now_ts = now.timestamp()
    # Lock acquired 2.5 hours ago (9000s ago) with ttl_seconds=14400 (4 hours)
    created_at = datetime.fromtimestamp(now_ts - 9000, tz=timezone.utc).isoformat()
    lock_data = {
        "status": "IN_PROGRESS",
        "topic_id": "test_topic_1",
        "lock_token": "original_token_111",
        "pid": 99999,
        "created_at_utc": created_at,
        "updated_at_utc": created_at,
        "ttl_seconds": 14400,
        "process_start_time": 1000.0,
    }

    with patch("app.services.alert_cooldown.is_pid_alive", return_value=True), \
         patch("app.services.daily_market_lock._get_process_start_time", return_value=1000.0):
        stale, reason = _is_lock_stale(lock_data, now)
        # Inside TTL (9000s < 14400s), age <= rec_ttl, so not_stale
        assert stale is False
        assert reason == "not_stale"

        # Write this lock file to the canonical lock path
        lock_file = _get_lock_file_path("US", state_dir=temp_state_dir, now=now)
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file, "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Another process attempting to acquire must fail
        ok = acquire_in_progress("US", topic_id="new_topic", state_dir=temp_state_dir, now=now)
        assert ok is False

        # is_market_done_today must see it as active in progress (done=True to skip duplicate runs)
        done, reason, details = is_market_done_today("US", state_dir=temp_state_dir, now=now, check_registry=False, check_episodes=False)
        assert done is True
        assert reason == "lock_in_progress"


def test_lock_exceeding_hard_max_is_stale(temp_state_dir):
    """When a lock exceeds hard_max (max(ttl + 7200, 28800)), it is stale regardless of process status."""
    now = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    now_ts = now.timestamp()
    # Lock acquired 9 hours ago (32400s ago) with ttl_seconds=7200 (hard_max is 28800s)
    created_at = datetime.fromtimestamp(now_ts - 32400, tz=timezone.utc).isoformat()
    lock_data = {
        "status": "IN_PROGRESS",
        "topic_id": "stale_topic",
        "lock_token": "old_token",
        "pid": 99999,
        "created_at_utc": created_at,
        "updated_at_utc": created_at,
        "ttl_seconds": 7200,
        "process_start_time": 1000.0,
    }

    with patch("app.services.alert_cooldown.is_pid_alive", return_value=True), \
         patch("app.services.daily_market_lock._get_process_start_time", return_value=1000.0):
        stale, reason = _is_lock_stale(lock_data, now)
        assert stale is True
        assert "hard_max_age_exceeded" in reason

        # Write lock file
        lock_file = _get_lock_file_path("US", state_dir=temp_state_dir, now=now)
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file, "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # A new process can acquire because old one is stale
        ok = acquire_in_progress("US", topic_id="fresh_topic", state_dir=temp_state_dir, now=now)
        assert ok is True


def test_force_displacement_records_metadata(temp_state_dir):
    """When acquire_in_progress is called with force=True over an active lock,
    it records displaced_token and displaced_pid in the new lock metadata.
    """
    now = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    lock_data = {
        "status": "IN_PROGRESS",
        "topic_id": "active_topic",
        "lock_token": "token_to_displace_123",
        "pid": 4321,
        "created_at_utc": now.isoformat(),
        "updated_at_utc": now.isoformat(),
        "ttl_seconds": 7200,
        "process_start_time": 1000.0,
    }

    lock_file = _get_lock_file_path("US", state_dir=temp_state_dir, now=now)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(lock_data, f)

    with patch("app.services.alert_cooldown.is_pid_alive", return_value=True), \
         patch("app.services.daily_market_lock._get_process_start_time", return_value=1000.0):
        # Force acquire with new token and pid
        ok = acquire_in_progress(
            "US",
            topic_id="forced_topic",
            state_dir=temp_state_dir,
            now=now,
            force=True,
            lock_token="new_forced_token_456",
            owner_pid=8765
        )
        assert ok is True

        # Verify new lock file has displacement audit trail
        with open(lock_file, "r", encoding="utf-8") as f:
            new_data = json.load(f)

        assert new_data["lock_token"] == "new_forced_token_456"
        assert new_data["pid"] == 8765
        assert new_data["displaced_token"] == "token_to_displace_123"
        assert new_data["displaced_pid"] == 4321
        assert new_data.get("forced") is True
