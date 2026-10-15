"""
tests/unit/test_daily_market_lock.py — HERMETIC UNIT TESTS FOR DAILY MARKET LOCK & QUOTA GUARD
"""

import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.daily_market_lock import (
    acquire_in_progress,
    is_market_done_today,
    mark_completed,
    release_lock,
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
    done, reason, details = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "not_produced_yet"


def test_acquire_in_progress_and_completion(temp_state_dir):
    """Test standard flow: acquire in_progress -> check done -> mark completed -> check done."""
    # Acquire IN_PROGRESS
    ok = acquire_in_progress("TEST_MKT", topic_id="TEST_TEMP_test1", state_dir=temp_state_dir)
    assert ok is True

    # Should report lock_in_progress (hence done=True to skip duplicate runs)
    done, reason, details = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason == "lock_in_progress"
    assert details["topic_id"] == "TEST_TEMP_test1"

    # Mark COMPLETED
    ok = mark_completed("TEST_MKT", topic_id="TEST_EP0001_final", state_dir=temp_state_dir)
    assert ok is True

    # Should report lock_completed
    done, reason, details = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason == "lock_completed"
    assert details["topic_id"] == "TEST_EP0001_final"


def test_stale_in_progress_lock_expires(temp_state_dir):
    """An IN_PROGRESS lock older than ttl_seconds should be treated as stale."""
    # Create lock file with creation time 7 hours ago
    past_utc = datetime.now(timezone.utc) - timedelta(hours=7)
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"TEST_MKT_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({
        "market": "TEST_MKT",
        "vn_date": today_vn,
        "status": "IN_PROGRESS",
        "topic_id": "TEST_TEMP_stale",
        "created_at_utc": past_utc.isoformat(),
        "ttl_seconds": 21600  # 6 hours
    }), encoding="utf-8")

    done, reason, details = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "stale_lock"


def test_corrupt_lock_file_fails_closed(temp_state_dir):
    """A corrupt lock file should fail-closed (return done=True) and persist a CORRUPT_FAIL_CLOSED marker (Boss Item 16)."""
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"TEST_MKT_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text("{invalid json content!!!", encoding="utf-8")

    done, reason, details = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason == "corrupt_lock_fail_closed"

    # Verify persistence: on the next run without --force, the CORRUPT_FAIL_CLOSED marker remains and continues to fail closed
    done2, reason2, details2 = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done2 is True
    assert reason2 == "corrupt_lock_fail_closed"


def test_in_progress_missing_created_at_fails_closed(temp_state_dir):
    """IN_PROGRESS lock without created_at_utc must fail closed (Boss Item 16)."""
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"TEST_MKT_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({"status": "IN_PROGRESS", "topic_id": "test_t"}), encoding="utf-8")

    done, reason, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason == "lock_in_progress"


def test_unrecognized_status_fails_closed(temp_state_dir):
    """Any unrecognized lock status must fail closed (Boss Item 16)."""
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"TEST_MKT_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({"status": "UNKNOWN_CUSTOM_STATUS", "topic_id": "test_t"}), encoding="utf-8")

    done, reason, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert "lock_unrecognized" in reason


def test_force_flag_bypasses_lock(temp_state_dir, monkeypatch):
    """The force flag should override COMPLETED lock."""
    mark_completed("TEST_MKT", topic_id="TEST_EP0001_done", state_dir=temp_state_dir)

    # Without force -> True
    done, _, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True

    # With force=True -> False
    done, reason, details = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, force=True, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "forced_override"

    # With env var B1_FORCE_CRAWL=1 -> False (via monkeypatch per Boss Item 17)
    monkeypatch.setenv("B1_FORCE_CRAWL", "1")
    done, reason, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "forced_override"


def test_release_lock(temp_state_dir):
    """Releasing lock removes the file so market can run again."""
    acquire_in_progress("TEST_MKT", topic_id="TEST_TEMP_001", state_dir=temp_state_dir)
    done, _, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True

    released = release_lock("TEST_MKT", state_dir=temp_state_dir)
    assert released is True

    done, reason, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "not_produced_yet"


def test_detects_completed_episode_on_disk(temp_state_dir):
    """When an episode directory exists with run_manifest.json created today,
    it should detect episode_dir_completed and auto-heal the lock on real disk (0 mocks, Boss Item 17).
    """
    ep_dir = Path(temp_state_dir) / "episodes" / "TEST_EP0099_sample_topic"
    ep_dir.mkdir(parents=True, exist_ok=True)
    manifest = ep_dir / "run_manifest.json"
    manifest.write_text(json.dumps({"status": "done"}), encoding="utf-8")

    done, reason, details = is_market_done_today(
        "TEST", state_dir=temp_state_dir, check_registry=False, check_episodes=True
    )
    assert done is True
    assert reason == "episode_dir_completed"
    assert details["topic_id"] == "TEST_EP0099_sample_topic"


def _worker_acquire(args):
    """Top-level worker helper for multiprocess concurrency testing on Windows & Linux."""
    market, topic_id, state_dir = args
    from app.services.daily_market_lock import acquire_in_progress
    return acquire_in_progress(market, topic_id=topic_id, state_dir=state_dir)


def _worker_stale_takeover(args):
    """Top-level worker helper for multiprocess stale takeover concurrency testing."""
    market, topic_id, state_dir = args
    from app.services.daily_market_lock import acquire_in_progress
    return acquire_in_progress(market, topic_id=topic_id, state_dir=state_dir, ttl_seconds=10)


def test_market_validation_raises_on_invalid(temp_state_dir):
    """Passing None, empty string, or whitespace should raise ValueError."""
    with pytest.raises(ValueError, match="non-empty string"):
        acquire_in_progress(None, topic_id="t1", state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        acquire_in_progress("", topic_id="t1", state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        is_market_done_today(None, state_dir=temp_state_dir)

    with pytest.raises(ValueError, match="non-empty string"):
        mark_completed("   ", topic_id="t1", state_dir=temp_state_dir)


def test_concurrent_acquire_in_progress_mutual_exclusion(temp_state_dir):
    """Multiple racing processes attempting to acquire lock simultaneously;
    strictly ONE must win, all others must fail.
    """
    from concurrent.futures import ProcessPoolExecutor
    n_workers = 6
    tasks = [("TEST_RACE", f"topic_{i}", temp_state_dir) for i in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(_worker_acquire, tasks))

    assert results.count(True) == 1, f"Expected exactly 1 winner, got {results.count(True)}: {results}"
    assert results.count(False) == n_workers - 1


def test_minimum_vn_hour_policy_protects_morning_window(temp_state_dir):
    """Boss Item 5: A post-midnight run (< 06:00 AM VN) must NOT seal the market as EXHAUSTED_TODAY,
    ensuring the scheduled 06:00 AM VN production window can evaluate fresh morning news."""
    from app.services.daily_market_lock import VN_TZ, is_market_done_today, mark_exhausted_today

    # Simulated post-midnight time: 00:42 AM VN on 2026-10-16
    midnight_vn = datetime(2026, 10, 16, 0, 42, tzinfo=VN_TZ)

    # Off-hours run fails to seal EXHAUSTED_TODAY
    res = mark_exhausted_today("EN", scan_count=10, state_dir=temp_state_dir, now=midnight_vn)
    assert res is False

    # Check eligibility at 06:00 AM VN: market should NOT be done today!
    morning_vn = datetime(2026, 10, 16, 6, 0, tzinfo=VN_TZ)
    is_done, reason, details = is_market_done_today("EN", state_dir=temp_state_dir, now=morning_vn)
    assert is_done is False
    assert reason == "not_produced_yet"

    # In contrast, an afternoon exhaustion at 15:00 VN seals normally
    afternoon_vn = datetime(2026, 10, 16, 15, 0, tzinfo=VN_TZ)
    res_pm = mark_exhausted_today("EN", scan_count=10, state_dir=temp_state_dir, now=afternoon_vn)
    assert res_pm is True

    is_done_pm, reason_pm, _ = is_market_done_today("EN", state_dir=temp_state_dir, now=afternoon_vn)
    assert is_done_pm is True
    assert reason_pm == "lock_exhausted_today"


def test_stale_lock_exclusive_takeover_race(temp_state_dir):
    """When multiple processes attempt to take over a stale IN_PROGRESS lock concurrently,
    strictly ONE process wins and all other racing contenders lose (Boss Item 17).
    """
    from concurrent.futures import ProcessPoolExecutor
    today_vn = vn_today()
    lock_file = Path(temp_state_dir) / "b1_daily_lock" / f"STALE_MKT_{today_vn}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    past_utc = datetime.now(timezone.utc) - timedelta(hours=10)
    lock_file.write_text(json.dumps({
        "market": "STALE_MKT",
        "vn_date": today_vn,
        "status": "IN_PROGRESS",
        "topic_id": "STALE_HOLDER",
        "created_at_utc": past_utc.isoformat(),
        "ttl_seconds": 10,
    }), encoding="utf-8")

    n_workers = 6
    tasks = [("STALE_MKT", f"new_topic_{i}", temp_state_dir) for i in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(_worker_stale_takeover, tasks))

    assert results.count(True) == 1, f"Expected exactly 1 takeover winner, got {results.count(True)}: {results}"
    assert results.count(False) == n_workers - 1


def test_incident_1_b3_crash_blocks_incident_2_re_crawl(temp_state_dir, monkeypatch):
    """Replay of Incident 1 -> Incident 2 (Boss Item 22):
    Incident 1: 06:21 VN: B1 discovers and approves EN_EP0001_retatrutide_shadow_market,
    Gate 1 Telegram alert sent, recorded in topic_history_registry, acquires IN_PROGRESS lock.
    Downstream B3 immediately crashes (No module named 'orchestrator.run_pipeline') without producing run_manifest.json.
    Incident 2: 15:29 VN (same day): Automated afternoon crawl ticks.
    Must verify that B1 skips crawling today, avoiding candidate re-crawling and alert storms.
    """
    from app.services.daily_market_lock import VN_TZ, acquire_in_progress, is_market_done_today

    # Setup isolated state
    monkeypatch.setenv("VF_STATE_DIR", str(temp_state_dir))
    monkeypatch.setenv("AVF_STATE_DIR", str(temp_state_dir))

    # 1. Incident 1 Morning run at 06:21 AM VN
    m_vn = datetime(2026, 10, 16, 6, 21, tzinfo=VN_TZ)
    topic_id = "EN_EP0001_retatrutide_shadow_market"

    # B1 acquires IN_PROGRESS lock
    acq = acquire_in_progress("EN", topic_id=topic_id, state_dir=temp_state_dir, now=m_vn)
    assert acq is True

    # B1 records approved topic in history registry
    import app.services.topic_history_registry as thr
    hist_file = Path(temp_state_dir) / "topic_history.json"
    monkeypatch.setattr(thr, "REGISTRY_PATH", str(hist_file))
    thr.record_handled_topic(
        term="retatrutide",
        task_id=topic_id,
        market="EN",
        specific_angle="The Retatrutide Black Market",
    )

    # B3 crashes! No episode folder or run_manifest.json is created.

    # 2. Incident 2 Afternoon run at 15:29 VN (same day, ~9h later)
    pm_vn = datetime(2026, 10, 16, 15, 29, tzinfo=VN_TZ)

    # Check whether market is done today
    # Even if TTL elapsed on lock, registry check detects recorded topic for today and heals lock!
    is_done, reason, details = is_market_done_today(
        "EN",
        state_dir=temp_state_dir,
        now=pm_vn,
        check_registry=True,
        check_episodes=True,
    )

    assert is_done is True, f"Expected B1 to skip re-crawl on Incident 2, but got is_done=False (reason={reason})"
    assert reason in ("lock_in_progress", "registry_completed")
    assert details.get("topic_id") == topic_id


