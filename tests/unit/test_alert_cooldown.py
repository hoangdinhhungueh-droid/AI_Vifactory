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

    # First alert dispatched at t0 (reserve_on_send=True by default)
    can_send, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, now=t0)
    assert can_send is True

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

    t4 = t3 + timedelta(minutes=5)
    can_send, suppressed, _ = should_send_alert(
        "b1_viability", "EN", state_dir=temp_state_dir, window_seconds=14400, now=t4
    )
    assert can_send is False
    assert suppressed == 1


def test_independent_markets_do_not_block_each_other(temp_state_dir):
    """An alert throttled for EN should NOT throttle JP or KR."""
    t0 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, now=t0)

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
    should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, now=t0)

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


def test_should_send_alert_reserve_on_send_false_does_not_reserve(temp_state_dir):
    """When reserve_on_send=False, should_send_alert must report eligibility without reserving the slot."""
    # Calling should_send_alert with reserve_on_send=False
    can_send, suppressed, suffix = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, reserve_on_send=False)
    assert can_send is True
    assert suppressed == 0

    # Because slot was NOT reserved, a subsequent call still reports can_send=True!
    can_send2, suppressed2, suffix2 = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, reserve_on_send=False)
    assert can_send2 is True
    assert suppressed2 == 0

    # Once reserved with reserve_on_send=True:
    can_send3, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, reserve_on_send=True)
    assert can_send3 is True

    # Immediate next call is now throttled!
    can_send4, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir)
    assert can_send4 is False


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

    # Hold the lock in outer context
    with _interprocess_lock(target_file, timeout=2.0):
        # When lock is already held, acquiring with short timeout must raise LockTimeoutError
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


def test_os_advisory_lock_released_on_exit(temp_state_dir):
    """Verify that OS advisory lock is properly released on context exit, allowing immediate re-acquisition."""
    from app.services.alert_cooldown import _interprocess_lock

    target_file = Path(temp_state_dir) / "test_lifecycle.json"

    # First acquisition
    with _interprocess_lock(target_file, timeout=2.0, poll_interval=0.05):
        pass

    # Second acquisition on same persistent lock file succeeds immediately
    acquired_second = False
    with _interprocess_lock(target_file, timeout=2.0, poll_interval=0.05):
        acquired_second = True

    assert acquired_second is True



def test_dispatch_failure_rollback_allows_subsequent_send(temp_state_dir):
    """Boss Item 7: If Telegram dispatch fails after atomic reservation,
    rollback_alert_reservation must restore state so the next attempt is immediately allowed."""
    from app.services.alert_cooldown import rollback_alert_reservation

    # First attempt: reserved
    can_send, suppressed, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, reserve_on_send=True)
    assert can_send is True

    # Simulate dispatch failure (e.g. Telegram network timeout)
    # Roll back reservation
    rolled_back = rollback_alert_reservation("b1_viability", "EN", previous_suppressed=suppressed, state_dir=temp_state_dir)
    assert rolled_back is True

    # Next attempt immediately after rollback should be allowed
    can_send_retry, suppressed_retry, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, reserve_on_send=True)
    assert can_send_retry is True
    assert suppressed_retry == 0


def test_permission_error_fails_immediately_without_spinning(temp_state_dir, monkeypatch):
    """Boss Round 9 Item 6: PermissionError on os.open must fail fast immediately without spinning for timeout."""
    from app.services.alert_cooldown import _interprocess_lock

    target_file = Path(temp_state_dir) / "test_perm.json"

    def mock_open_perm_error(*args, **kwargs):
        raise PermissionError("Simulated EACCES filesystem error")

    monkeypatch.setattr(os, "open", mock_open_perm_error)

    t0 = time.time()
    with pytest.raises(PermissionError, match="Filesystem permission error"):
        with _interprocess_lock(target_file, timeout=5.0, poll_interval=0.05):
            pass
    elapsed = time.time() - t0
    # Must fail fast in less than 0.5s, NOT spinning for the full 5.0s timeout
    assert elapsed < 0.5, f"Expected fast failure, but took {elapsed:.2f}s"



def test_rollback_reservation_preserves_suppressed_count_when_never_sent(temp_state_dir):
    """Boss Item 54: When previous_last_sent is None, rollback_alert_reservation must NOT delete
    the entry and must preserve accumulated suppressions.
    """
    from app.services.alert_cooldown import _read_cooldown_data, _resolve_cooldown_file, rollback_alert_reservation

    # Reserve initial slot
    can_send, _, _ = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir, reserve_on_send=True)
    assert can_send is True

    # Rollback with previous_suppressed=5, previous_last_sent=None
    rolled = rollback_alert_reservation(
        "b1_viability", "EN", previous_suppressed=5, previous_last_sent=None, state_dir=temp_state_dir
    )
    assert rolled is True

    cd_file = _resolve_cooldown_file(temp_state_dir)
    data = _read_cooldown_data(cd_file)
    entry = data.get("b1_viability::EN")
    assert entry is not None
    assert entry["last_sent_utc"] is None
    assert entry["suppressed_since_last"] == 5


def test_windows_interprocess_lock_contention_and_permission_error(temp_state_dir):
    """Boss Round 4 Item 7: High-contention concurrency test.
    Exercises concurrent lock acquisition across multiple worker threads,
    verifying that PermissionError / contention is retried without crashing.
    """
    import concurrent.futures

    from app.services.alert_cooldown import _interprocess_lock

    test_file = Path(temp_state_dir) / "contention_test.json"
    shared_counter = [0]
    errors = []

    def worker(worker_id: int):
        try:
            for _ in range(10):
                with _interprocess_lock(test_file, timeout=15.0, poll_interval=0.01):
                    val = shared_counter[0]
                    time.sleep(0.005)
                    shared_counter[0] = val + 1
        except Exception as exc:
            errors.append((worker_id, exc))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(worker, i) for i in range(6)]
        concurrent.futures.wait(futures)

    assert len(errors) == 0, f"Errors under lock contention: {errors}"
    assert shared_counter[0] == 60


def test_send_telegram_broadcast_returns_truthy_on_success(monkeypatch):
    """Boss Round 8 Item 5: Prove with test that send_telegram_broadcast returns truthy on success,
    enabling _send_guarded_alert to verify delivery before confirming alert state.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.services.telegram_buttons import send_telegram_broadcast

    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("VF_TG_BOT_TOKEN", "mock_bot_token_123")
    monkeypatch.setenv("VF_TG_CHAT_ID", "mock_chat_id_456")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 789}}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        msg_id = send_telegram_broadcast("<b>Test Alert</b>")
        assert msg_id == 789
        assert bool(msg_id) is True

    # Test failure returns falsy / None
    mock_fail_resp = MagicMock()
    mock_fail_resp.status_code = 500
    mock_fail_resp.text = "Internal Server Error"
    mock_fail_client = AsyncMock()
    mock_fail_client.post.return_value = mock_fail_resp
    mock_fail_client.__aenter__.return_value = mock_fail_client
    mock_fail_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_fail_client):
        fail_id = send_telegram_broadcast("<b>Fail Alert</b>")
        assert fail_id is None
        assert bool(fail_id) is False


def test_transient_ioerror_fails_open_without_overwriting(temp_state_dir):
    """Boss Round 9 Item 5: Transient OSError during read should fail-open without overwriting disk state."""
    from unittest.mock import patch
    import json
    from app.services.alert_cooldown import _resolve_cooldown_file, rollback_alert_reservation, CooldownReadError

    cooldown_file = _resolve_cooldown_file(temp_state_dir)
    original_data = {"b1_viability::EN": {"last_sent_utc": "2026-10-15T12:00:00+00:00", "suppressed_since_last": 5}}
    cooldown_file.write_text(json.dumps(original_data), encoding="utf-8")

    with patch("app.services.alert_cooldown._read_cooldown_data", side_effect=CooldownReadError("Simulated transient EIO")):
        decision = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir)
        assert decision.can_send is True
        assert decision.suppressed == 0

        # Rollback should also safely abort without writing corrupted/empty data
        rb_ok = rollback_alert_reservation("b1_viability", "EN", state_dir=temp_state_dir)
        assert rb_ok is False

    # Verify original file content was completely preserved on disk
    saved_data = json.loads(cooldown_file.read_text(encoding="utf-8"))
    assert saved_data == original_data


def test_read_cooldown_data_raises_cooldown_read_error_on_ioerror(temp_state_dir):
    """Verify that _read_cooldown_data converts OSError to CooldownReadError."""
    from unittest.mock import patch
    from app.services.alert_cooldown import _read_cooldown_data, _resolve_cooldown_file, CooldownReadError

    cooldown_file = _resolve_cooldown_file(temp_state_dir)
    cooldown_file.write_text("{}", encoding="utf-8")

    with patch("builtins.open", side_effect=OSError("Disk read failure")):
        with pytest.raises(CooldownReadError):
            _read_cooldown_data(cooldown_file)



def test_corrupt_timestamp_quarantines_field_and_fails_open(temp_state_dir):
    """Boss Round 9 Item 5: Corrupt timestamp string should quarantine field to corrupted_last_sent_utc and fail open."""
    import json
    from app.services.alert_cooldown import _resolve_cooldown_file

    cooldown_file = _resolve_cooldown_file(temp_state_dir)
    corrupted_data = {"b1_viability::EN": {"last_sent_utc": "BAD_TIMESTAMP_STRING_XYZ", "suppressed_since_last": 2}}
    cooldown_file.write_text(json.dumps(corrupted_data), encoding="utf-8")

    decision = should_send_alert("b1_viability", "EN", state_dir=temp_state_dir)
    assert decision.can_send is True

    # Check that disk entry was quarantined and healed with fresh timestamp
    saved_data = json.loads(cooldown_file.read_text(encoding="utf-8"))
    entry = saved_data["b1_viability::EN"]
    assert entry.get("corrupted_last_sent_utc") == "BAD_TIMESTAMP_STRING_XYZ"
    assert entry.get("last_sent_utc") is not None
    assert entry.get("last_sent_utc") != "BAD_TIMESTAMP_STRING_XYZ"





