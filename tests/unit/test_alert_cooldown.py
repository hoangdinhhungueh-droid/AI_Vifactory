"""
tests/unit/test_alert_cooldown.py — UNIT TESTS FOR ALERT RATE LIMITER & COOLDOWN ENGINE
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

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
