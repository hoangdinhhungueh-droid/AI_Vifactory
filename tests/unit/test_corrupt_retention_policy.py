#!/usr/bin/env python3
"""tests/unit/test_corrupt_retention_policy.py — Tests for quarantine retention policy (Rule 125 & Boss Item 14).

Verifies that *.corrupt.<epoch> files created by alert_cooldown and daily_market_lock
are pruned according to retention policy (max_files, max_age_seconds) preventing unbounded accumulation.
"""

import time
from pathlib import Path

from app.services.alert_cooldown import cleanup_corrupt_quarantines as alert_cleanup
from app.services.daily_market_lock import _quarantine_corrupt_lock
from app.services.daily_market_lock import cleanup_corrupt_quarantines as lock_cleanup


def test_alert_cooldown_retention_policy_prunes_excess_files(tmp_path: Path):
    """Verifies that alert_cooldown cleanup keeps at most max_files newest corrupt files."""
    for i in range(10):
        f = tmp_path / f"cooldown.json.corrupt.{1700000000 + i}"
        f.write_text("corrupt content", encoding="utf-8")
        time.sleep(0.01)

    corrupt_before = list(tmp_path.glob("*.corrupt.*"))
    assert len(corrupt_before) == 10

    # Prune keeping max_files=4
    pruned = alert_cleanup(tmp_path, max_files=4, max_age_seconds=86400 * 30)
    assert pruned == 6

    corrupt_after = list(tmp_path.glob("*.corrupt.*"))
    assert len(corrupt_after) == 4


def test_daily_market_lock_retention_policy_prunes_stale_files(tmp_path: Path):
    """Verifies that daily_market_lock cleanup prunes files older than max_age_seconds."""
    old_file = tmp_path / "lock.json.corrupt.1600000000"
    old_file.write_text("very old corrupt file", encoding="utf-8")

    import os
    # Set mtime to 30 days ago
    thirty_days_ago = time.time() - (86400 * 30)
    os.utime(str(old_file), (thirty_days_ago, thirty_days_ago))

    new_file = tmp_path / f"lock.json.corrupt.{int(time.time())}"
    new_file.write_text("fresh corrupt file", encoding="utf-8")

    pruned = lock_cleanup(tmp_path, max_files=10, max_age_seconds=86400 * 7)
    assert pruned == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_quarantine_corrupt_lock_creates_file_and_cleans_up(tmp_path: Path):
    """Verifies that _quarantine_corrupt_lock moves the unreadable lock to *.corrupt.<epoch>."""
    bad_lock = tmp_path / "EN_20261015.lock"
    bad_lock.write_text("invalid json", encoding="utf-8")

    corrupt_path = _quarantine_corrupt_lock(bad_lock)
    assert not bad_lock.exists()
    assert corrupt_path.exists()
    assert ".corrupt." in corrupt_path.name
