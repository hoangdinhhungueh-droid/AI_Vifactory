"""
tests/unit/test_alert_cooldown.py — UNIT TESTS FOR ALERT RATE LIMITER & COOLDOWN ENGINE
"""

import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.alert_cooldown import (
    check_alert_eligibility,
    record_alert_sent,
    record_alert_suppressed,
    should_send_alert,
)


@pytest.fixture
def temp_state_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_cooldown_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_first_alert_is_always_allowed(temp_state_dir):
    """The very first alert should be allowed without suppression."""
    can_send, suppressed, suffix = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir)
    assert can_send is True
    assert suppressed == 0
    assert suffix == ""


def test_cooldown_throttling_within_window(temp_state_dir):
    """Subsequent alerts within window should be throttled and increment suppressed count."""
    t0 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    # First alert dispatched at t0
    can_send, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, now=t0)
    assert can_send is True
    record_alert_sent("b1_viability", "EN", state_dir=temp_state_dir, now=t0)

    # Second alert 10 minutes later (t0 + 10m)
    t1 = t0 + timedelta(minutes=10)
    can_send, suppressed, _ = should_send_alert(
        "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t1
    )
    assert can_send is False
    assert suppressed == 1

    # Third alert 30 minutes later (t0 + 30m)
    t2 = t0 + timedelta(minutes=30)
    can_send, suppressed, _ = should_send_alert(
        "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t2
    )
    assert can_send is False
    assert suppressed == 2

    # Fourth alert 4 hours and 1 minute later (t0 + 4h1m) -> eligible!
    t3 = t0 + timedelta(hours=4, minutes=1)
    can_send, suppressed, suffix = should_send_alert(
        "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t3
    )
    assert can_send is True
    assert suppressed == 2
    assert "2" in suffix
    assert "chặn" in suffix or "gom" in suffix

    # Record dispatch at t3, verifying suppressed reset
    record_alert_sent("b1_viability", "EN", state_dir=temp_state_dir, now=t3)
    t4 = t3 + timedelta(minutes=5)
    can_send, suppressed, _ = should_send_alert(
        "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t4
    )
    assert can_send is False
    assert suppressed == 1


def test_independent_markets_do_not_block_each_other(temp_state_dir):
    """An alert throttled for EN should NOT throttle JP or KR."""
    t0 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    record_alert_sent("b1_viability", "EN", state_dir=temp_state_dir, now=t0)

    # EN is throttled
    can_en, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, now=t0 + timedelta(minutes=5))
    assert can_en is False

    # JP is NOT throttled
    can_jp, suppressed_jp, _ = should_send_alert("b1_viability", "JP", state_dir=temp_state_dir, now=t0 + timedelta(minutes=5))
    assert can_jp is True
    assert suppressed_jp == 0


def test_disable_alert_cooldown_override(temp_state_dir):
    """Env DISABLE_ALERT_COOLDOWN=1 bypasses throttling entirely."""
    t0 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    record_alert_sent("b1_viability", "EN", state_dir=temp_state_dir, now=t0)

    os.environ["DISABLE_ALERT_COOLDOWN"] = "1"
    try:
        can_send, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, now=t0 + timedelta(minutes=1))
        assert can_send is True
    finally:
        os.environ.pop("DISABLE_ALERT_COOLDOWN", None)


def test_market_validation_raises_on_invalid(temp_state_dir):
    """Passing None, empty string, or whitespace should raise ValueError."""
    with pytest.raises(ValueError, match="non-empty string"):
        should_send_alert("b1_viability", None, state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        should_send_alert("b1_viability", "", state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        should_send_alert("b1_viability", "   ", state_dir=temp_state_dir)


def test_check_alert_eligibility_is_pure_read_only(temp_state_dir):
    """check_alert_eligibility must be pure read-only and never mutate suppression count."""
    t0 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    record_alert_sent("b1_viability", "EN", state_dir=temp_state_dir, now=t0)

    # Calling check_alert_eligibility 5 times within window
    t1 = t0 + timedelta(minutes=5)
    for _ in range(5):
        can_send, suppressed, suffix = check_alert_eligibility(
            "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t1
        )
        assert can_send is False
        assert suppressed == 0  # Still 0 because pure check never mutates!

    # Now call record_alert_suppressed explicitly
    new_count = record_alert_suppressed("b1_viability", "EN", state_dir=temp_state_dir, now=t1)
    assert new_count == 1

    can_send, suppressed, suffix = check_alert_eligibility(
        "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t1
    )
    assert can_send is False
    assert suppressed == 1


def test_corrupt_json_quarantine(temp_state_dir):
    """Corrupt JSON in alert_cooldown.json should be quarantined with .corrupt.<ts> suffix."""
    from pathlib import Path
    cooldown_file = Path(temp_state_dir) / "alert_cooldown.json"
    cooldown_file.write_text("{corrupt: json content here!", encoding="utf-8")

    # should_send_alert should handle gracefully without crashing
    can_send, suppressed, suffix = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir)
    assert can_send is True
    assert suppressed == 0

    # Verify corrupt file was renamed/quarantined
    corrupt_files = list(Path(temp_state_dir).glob("alert_cooldown.json.corrupt.*"))
    assert len(corrupt_files) == 1
    assert "corrupt: json" in corrupt_files[0].read_text(encoding="utf-8")


def _worker_should_send(args):
    """Top-level worker helper for multiprocess concurrency testing."""
    alert_type, market, state_dir = args
    from app.services.alert_cooldown import should_send_alert
    can_send, _, _ = should_send_alert(alert_type, market, state_dir=state_dir, reserve_on_send=True)
    return can_send


def test_concurrent_should_send_alert_atomic_reservation(temp_state_dir):
    """Multiple racing processes calling should_send_alert simultaneously;
    strictly ONE caller must receive can_send=True, all others must be throttled with can_send=False.
    """
    from concurrent.futures import ProcessPoolExecutor
    n_workers = 6
    tasks = [("b1_viability", "EN", temp_state_dir) for _ in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(_worker_should_send, tasks))

    assert results.count(True) == 1, f"Expected exactly 1 winner, got {results.count(True)}: {results}"
    assert results.count(False) == n_workers - 1


def test_lock_timeout_error_fail_closed(temp_state_dir):
    """_interprocess_lock must fail-closed and raise LockTimeoutError when lock cannot be acquired."""
    from pathlib import Path

    from app.services.alert_cooldown import LockTimeoutError, _interprocess_lock

    target_file = Path(temp_state_dir) / "test.json"
    lock_file = target_file.with_suffix(".json.lock")
    lock_file.write_text("99999:held_by_someone_else", encoding="utf-8")

    # When lock is held, acquiring with short timeout must raise LockTimeoutError
    with pytest.raises(LockTimeoutError):
        with _interprocess_lock(target_file, timeout=0.1, poll_interval=0.02):
            pass


def test_alert_type_validation_raises_on_invalid(temp_state_dir):
    """Passing None, empty string, or whitespace for alert_type should raise ValueError."""
    with pytest.raises(ValueError, match="non-empty string"):
        should_send_alert(None, "EN", state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        should_send_alert("", "EN", state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        should_send_alert("   ", "EN", state_dir=temp_state_dir)


def test_is_pid_alive_platform_safe():
    """Verify platform-safe PID liveness probe across Windows and POSIX."""
    from app.services.alert_cooldown import is_pid_alive

    # Current process is alive
    assert is_pid_alive(os.getpid()) is True
    # Non-existent PID
    assert is_pid_alive(9999999) is False
    # Invalid PID
    assert is_pid_alive(-1) is False
    assert is_pid_alive(0) is False


def test_stale_lock_reclaim_with_tombstone(temp_state_dir):
    """Verify that a lock older than 30s with a dead PID is safely reclaimed via atomic tombstone."""
    from app.services.alert_cooldown import _interprocess_lock

    target_file = Path(temp_state_dir) / "test_stale.json"
    lock_file = target_file.with_suffix(".json.lock")

    # Write a stale lock with dead PID (9999999)
    lock_file.write_text("9999999:dead_token_xyz", encoding="utf-8")
    # Backdate mtime to 35 seconds ago
    old_time = time.time() - 35.0
    os.utime(str(lock_file), (old_time, old_time))

    # Acquiring should detect dead PID, rename to tombstone, and succeed
    acquired = False
    with _interprocess_lock(target_file, timeout=2.0, poll_interval=0.05):
        acquired = True

    assert acquired is True
    # After exit, lock should be cleaned up
    assert not lock_file.exists()

