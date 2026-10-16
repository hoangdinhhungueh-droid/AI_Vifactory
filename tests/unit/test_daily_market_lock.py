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

    # Mark COMPLETED with owner verification
    ok = mark_completed("TEST_MKT", topic_id="TEST_EP0001_final", state_dir=temp_state_dir, owner_pid=os.getpid())
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

    released = release_lock("TEST_MKT", state_dir=temp_state_dir, owner_pid=os.getpid())
    assert released is True

    done, reason, _ = is_market_done_today("TEST_MKT", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "not_produced_yet"


def test_detects_completed_episode_on_disk(temp_state_dir):
    """When an episode directory exists with run_manifest.json created today,
    it should detect episode_dir_completed as a pure read check without mutating disk (0 mocks, Boss Round 8).
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


def _worker_offhours_transition(args):
    """Top-level worker helper for 06:00 VN off-hours transition race testing (Boss Item 16)."""
    market, topic_id, state_dir, morning_vn = args
    from app.services.daily_market_lock import acquire_in_progress
    return acquire_in_progress(market, topic_id=topic_id, state_dir=state_dir, now=morning_vn)



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
    """Boss Item 5 & 18: A post-midnight run (< 06:00 AM VN) writes an EXHAUSTED_OFFHOURS lock
    that throttles off-hours ticks but expires at 06:00 AM VN to protect the scheduled morning run."""
    from app.services.daily_market_lock import VN_TZ, is_market_done_today, mark_exhausted_today

    mkt = "TEST_WINDOW"
    # Simulated post-midnight time: 00:42 AM VN on 2026-10-16
    midnight_vn = datetime(2026, 10, 16, 0, 42, tzinfo=VN_TZ)

    # Off-hours run writes EXHAUSTED_OFFHOURS lock (Boss Item 18)
    res = mark_exhausted_today(mkt, scan_count=10, state_dir=temp_state_dir, now=midnight_vn)
    assert res is True

    # Mid-night tick at 01:00 VN is throttled (prevents midnight cron burn)
    done_off, reason_off, _ = is_market_done_today(mkt, state_dir=temp_state_dir, now=midnight_vn, check_registry=False, check_episodes=False)
    assert done_off is True
    assert reason_off == "lock_exhausted_offhours"

    # Check eligibility at 06:00 AM VN: off-hours lock expires, morning run permitted!
    morning_vn = datetime(2026, 10, 16, 6, 0, tzinfo=VN_TZ)
    is_done, reason, details = is_market_done_today(mkt, state_dir=temp_state_dir, now=morning_vn, check_registry=False, check_episodes=False)
    assert is_done is False
    assert reason in ("stale_lock", "not_produced_yet")

    # In contrast, an afternoon exhaustion at 15:00 VN seals normally
    afternoon_vn = datetime(2026, 10, 16, 15, 0, tzinfo=VN_TZ)
    res_pm = mark_exhausted_today(mkt, scan_count=10, state_dir=temp_state_dir, now=afternoon_vn, owner_pid=os.getpid())
    assert res_pm is True

    is_done_pm, reason_pm, _ = is_market_done_today(mkt, state_dir=temp_state_dir, now=afternoon_vn, check_registry=False, check_episodes=False)
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
    assert reason == "registry_committed_pending_render"
    assert details.get("topic_id") == topic_id


def test_held_lock_prevents_second_run_making_llm_calls(temp_state_dir, monkeypatch):
    """Boss Item 13: An active IN_PROGRESS lock must abort a concurrent run immediately,
    guaranteeing ZERO LLM calls or crawls occur under mutual exclusion."""
    from app.services.daily_market_lock import acquire_in_progress
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    # First runner acquires IN_PROGRESS lock
    ok = acquire_in_progress("EN", topic_id="ACTIVE_RUN", state_dir=temp_state_dir)
    assert ok is True

    # Spy on LLM viability call
    llm_called = False
    def mock_assess(*args, **kwargs):
        nonlocal llm_called
        llm_called = True
        return {"is_video_viable": False}

    monkeypatch.setattr("app.services.trend_engine_b1.assess_keyword_video_viability", mock_assess)

    # Second runner attempts to crawl the same market
    res = discover_and_produce_market_trend(market="EN", state_dir=temp_state_dir, auto_produce=False)
    assert res == []
    assert llm_called is False, "A held IN_PROGRESS lock must prevent any LLM calls in concurrent runs"


def test_holder_verification_protects_lock_mutations(temp_state_dir):
    """Boss Item 14: release_lock, mark_completed, and mark_exhausted_today must verify holder (pid + token)
    and refuse to overwrite or unlink locks owned by another process."""
    from app.services.daily_market_lock import (
        acquire_in_progress,
        is_market_done_today,
        mark_completed,
        mark_exhausted_today,
        release_lock,
    )

    owner_pid = 4242
    owner_token = "token_alpha_123"
    wrong_pid = 9999
    wrong_token = "token_bravo_456"

    # Acquire lock with specific owner credentials
    ok = acquire_in_progress(
        "EN",
        topic_id="OWNED_RUN",
        state_dir=temp_state_dir,
        owner_pid=owner_pid,
        lock_token=owner_token,
    )
    assert ok is True

    # Attempt to release with wrong token/pid -> REFUSED
    rel_wrong = release_lock("EN", state_dir=temp_state_dir, lock_token=wrong_token, owner_pid=wrong_pid)
    assert rel_wrong is False

    # Verify lock still exists and is IN_PROGRESS
    done, reason, _ = is_market_done_today("EN", state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason == "lock_in_progress"

    # Attempt to mark_completed with wrong token -> REFUSED
    comp_wrong = mark_completed(
        "EN",
        topic_id="FAKE_DONE",
        state_dir=temp_state_dir,
        lock_token=wrong_token,
        owner_pid=wrong_pid,
    )
    assert comp_wrong is False

    # Attempt to mark_exhausted_today with wrong token -> REFUSED
    ex_wrong = mark_exhausted_today(
        "EN",
        scan_count=5,
        state_dir=temp_state_dir,
        lock_token=wrong_token,
        owner_pid=wrong_pid,
    )
    assert ex_wrong is False

    # Legitimate owner marks COMPLETED -> SUCCEEDS
    comp_ok = mark_completed(
        "EN",
        topic_id="REAL_DONE",
        state_dir=temp_state_dir,
        lock_token=owner_token,
        owner_pid=owner_pid,
    )
    assert comp_ok is True

    done_final, reason_final, details_final = is_market_done_today(
        "EN", state_dir=temp_state_dir, check_registry=False, check_episodes=False
    )
    assert done_final is True
    assert reason_final == "lock_completed"
    assert details_final.get("topic_id") == "REAL_DONE"


def test_load_history_raises_fails_closed(temp_state_dir, monkeypatch):
    """Boss Item 15: If load_history raises an unexpected exception, is_market_done_today
    must fail closed (return is_done=True, reason='registry_unreadable_fail_closed') instead of failing open."""
    import app.services.topic_history_registry as reg_mod
    from app.services.daily_market_lock import is_market_done_today

    def mock_broken_history(*args, **kwargs):
        raise IOError("Simulated corrupted registry database")

    monkeypatch.setattr(reg_mod, "load_history", mock_broken_history)

    is_done, reason, details = is_market_done_today(
        "EN",
        state_dir=temp_state_dir,
        check_registry=True,
        check_episodes=False,
    )
    assert is_done is True, "Unexpected registry errors must fail closed to protect quota"
    assert reason == "registry_unreadable_fail_closed"
    assert "Simulated corrupted registry" in details.get("error", "")


def test_repeated_off_hours_ticks_throttled(temp_state_dir):
    """Boss Item 18: Repeated ticks before 06:00 AM VN must stay throttled via EXHAUSTED_OFFHOURS,
    and then automatically expire at 06:00 AM VN to permit scheduled morning production."""
    from app.services.daily_market_lock import VN_TZ, is_market_done_today, mark_exhausted_today

    mkt = "TEST_THROTTLED"
    # 1. First tick at 01:15 AM VN: scan finds no candidate, writes EXHAUSTED_OFFHOURS
    t1 = datetime(2026, 10, 16, 1, 15, tzinfo=VN_TZ)
    marked = mark_exhausted_today(mkt, scan_count=10, state_dir=temp_state_dir, now=t1)
    assert marked is True

    # 2. Subsequent ticks at 02:00, 03:00, 04:00, 05:00 VN must all be throttled
    for h in [2, 3, 4, 5]:
        t_tick = datetime(2026, 10, 16, h, 0, tzinfo=VN_TZ)
        is_done, reason, _ = is_market_done_today(mkt, state_dir=temp_state_dir, now=t_tick, check_registry=False, check_episodes=False)
        assert is_done is True, f"Tick at {h:02d}:00 VN should be throttled by EXHAUSTED_OFFHOURS"
        assert reason == "lock_exhausted_offhours"

    # 3. Morning arrives at 06:05 AM VN: lock expired, market is ready!
    t_morn = datetime(2026, 10, 16, 6, 5, tzinfo=VN_TZ)
    is_done_morn, reason_morn, _ = is_market_done_today(mkt, state_dir=temp_state_dir, now=t_morn, check_registry=False, check_episodes=False)
    assert is_done_morn is False, "At 06:00 AM VN, off-hours throttle must expire to permit morning production"
    assert reason_morn in ("stale_lock", "not_produced_yet")


def test_concurrent_0600_offhours_transition_race(temp_state_dir):
    """Boss Item 16: Multiple concurrent processes racing to take over an expired EXHAUSTED_OFFHOURS
    lock at 06:00 AM VN; strictly ONE process must win and transition to IN_PROGRESS, all others must fail.
    """
    from concurrent.futures import ProcessPoolExecutor

    from app.services.daily_market_lock import VN_TZ, mark_exhausted_today

    mkt = "TEST_OFFHOURS_RACE"
    # 1. Setup an EXHAUSTED_OFFHOURS lock written at 02:00 AM VN
    t_off = datetime(2026, 10, 16, 2, 0, tzinfo=VN_TZ)
    marked = mark_exhausted_today(mkt, scan_count=10, state_dir=temp_state_dir, now=t_off)
    assert marked is True

    # 2. At 06:00 AM VN, N processes simultaneously attempt to acquire lock
    morning_vn = datetime(2026, 10, 16, 6, 0, tzinfo=VN_TZ)
    n_workers = 6
    tasks = [(mkt, f"morning_topic_{i}", temp_state_dir, morning_vn) for i in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(_worker_offhours_transition, tasks))

    assert results.count(True) == 1, f"Expected exactly 1 takeover winner, got {results.count(True)}: {results}"
    assert results.count(False) == n_workers - 1


def test_crawl_midstream_exception_releases_lock(temp_state_dir, monkeypatch):
    """Boss Item 18 & 29: If an unhandled exception occurs mid-crawl after acquiring lock,
    the try/finally block must automatically release the IN_PROGRESS lock so the market is not hung for 4 hours.
    """
    from app.services.daily_market_lock import is_market_done_today
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    mkt = "TEST_CRASH"

    def mock_failing_fetch(*args, **kwargs):
        raise RuntimeError("Simulated transient network failure mid-crawl")

    monkeypatch.setattr("app.services.trend_engine_b1.fetch_live_trending_terms", mock_failing_fetch)

    with pytest.raises(RuntimeError, match="Simulated transient network failure"):
        discover_and_produce_market_trend(mkt, state_dir=temp_state_dir, auto_produce=False)

    # Verify that the lock was cleanly released in finally and does NOT block subsequent runs
    done, reason, _ = is_market_done_today(mkt, state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False, f"Lock should have been released on exception, but got done=True ({reason})"
    assert reason == "not_produced_yet"


def test_non_timeout_cooldown_error_does_not_abort_quota_stamp(temp_state_dir, monkeypatch):
    """Boss Item 18 & 29: If alert cooldown raises a non-timeout error (e.g. ValueError or IOError),
    mark_exhausted_today has already stamped the lock and the error is suppressed so the quota is protected.
    """
    import app.services.alert_cooldown as ac
    from app.services.daily_market_lock import is_market_done_today
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    mkt = "TEST_COOLDOWN"

    # Mock fetch to return candidate that fails pre-filter so crawl exhausts candidates
    def mock_fetch(*args, **kwargs):
        return [{"term": "test_term_fail", "approx_traffic": 0, "geos_present": []}]

    monkeypatch.setattr("app.services.trend_engine_b1.fetch_live_trending_terms", mock_fetch)

    # Alert cooldown throws unexpected IOError
    def mock_broken_alert(*args, **kwargs):
        raise IOError("Disk full when reserving alert lock")

    monkeypatch.setattr(ac, "should_send_alert", mock_broken_alert)

    # Run crawl: should not raise, should stamp EXHAUSTED_TODAY (or EXHAUSTED_OFFHOURS if before 06:00 VN)
    res = discover_and_produce_market_trend(mkt, state_dir=temp_state_dir, auto_produce=False)
    assert res == []

    # Market must be marked EXHAUSTED_TODAY or EXHAUSTED_OFFHOURS (both represent quota exhaustion)
    done, reason, details = is_market_done_today(mkt, state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason in ("lock_exhausted_today", "lock_exhausted_offhours")


def test_interprocess_lock_write_failure_cleans_up(tmp_path):
    """Boss Round 10 Item 5: Persistent advisory lock file must never be unlinked on error paths,
    so concurrent holders' mutual exclusion remains intact on POSIX.
    """
    import unittest.mock as mock

    from app.services.alert_cooldown import _interprocess_lock

    target_file = tmp_path / "test.json"
    actual_lock_file = target_file.with_suffix(target_file.suffix + ".lock")

    def broken_write(fd, data):
        raise OSError("Simulated disk error during lock write")

    with mock.patch("os.write", side_effect=broken_write):
        with pytest.raises(RuntimeError, match="Unexpected error acquiring lock"):
            with _interprocess_lock(target_file, timeout=1.0):
                pass

    # Persistent lock file must NOT be unlinked on error (Boss Item 5)
    assert actual_lock_file.exists(), "Persistent advisory lock file must not be unlinked on error"


def test_interprocess_lock_holder_error_still_blocks_contenders(tmp_path):
    """Boss Round 10 Item 5: When Process A holds the lock, and Process B encounters
    an injected OSError, Process C still cannot acquire while Process A holds the lock.
    """
    import unittest.mock as mock

    from app.services.alert_cooldown import LockTimeoutError, _interprocess_lock

    target_file = tmp_path / "cooldown.json"

    # Process A acquires lock
    with _interprocess_lock(target_file, timeout=2.0):
        # Process B tries to acquire but hits an injected OSError
        def broken_lseek(fd, pos, how):
            raise OSError("Simulated error in Process B")

        with mock.patch("os.lseek", side_effect=broken_lseek):
            with pytest.raises((RuntimeError, LockTimeoutError)):
                with _interprocess_lock(target_file, timeout=0.1):
                    pass

        # Process C tries to acquire while Process A still holds the lock -> must timeout fail-closed
        with pytest.raises(LockTimeoutError):
            with _interprocess_lock(target_file, timeout=0.1):
                pass



def test_topic_history_registry_vn_day_boundary_attribution(temp_state_dir, monkeypatch):
    """Boss Item 27: Verify that both UTC-aware and naive ISO timestamps in topic_history_registry
    are correctly converted to VN date (UTC+7) across the 00:00 VN boundary.
    """
    import json

    import app.services.topic_history_registry as thr
    from app.services.daily_market_lock import VN_TZ, is_market_done_today

    hist_file = Path(temp_state_dir) / "topic_history.json"
    monkeypatch.setattr(thr, "REGISTRY_PATH", str(hist_file))
    monkeypatch.setattr(thr, "PENDING_DIR", str(Path(temp_state_dir) / "no_pending"))

    mkt = "TEST_VN_BOUNDARY"
    # Case A: 2026-10-15 17:05:00 UTC == 2026-10-16 00:05:00 VN (just after VN midnight)
    # Naive ISO string "2026-10-15T17:05:00" representing UTC
    hist_data = {
        "retatrutide": {
            "term": "retatrutide",
            "task_id": "TEST_EP0001_retatrutide",
            "market": mkt,
            "recorded_at": "2026-10-15T17:05:00",
        }
    }
    hist_file.write_text(json.dumps(hist_data), encoding="utf-8")

    # Probe on 2026-10-16 VN date: should detect entry as recorded on 2026-10-16
    now_vn_16th = datetime(2026, 10, 16, 8, 0, tzinfo=VN_TZ)
    done, reason, details = is_market_done_today(
        mkt,
        state_dir=temp_state_dir,
        now=now_vn_16th,
        check_registry=True,
        check_episodes=False,
    )
    assert done is True
    assert reason == "registry_committed_pending_render"
    assert details["topic_id"] == "TEST_EP0001_retatrutide"
    assert details["vn_date"] == "2026-10-16"

    # Case B: 2026-10-15 16:55:00 UTC == 2026-10-15 23:55:00 VN (5 minutes before VN midnight)
    hist_data["retatrutide"]["recorded_at"] = "2026-10-15T16:55:00Z"
    hist_file.write_text(json.dumps(hist_data), encoding="utf-8")

    done_b, reason_b, _ = is_market_done_today(
        mkt,
        state_dir=temp_state_dir,
        now=now_vn_16th,
        check_registry=True,
        check_episodes=False,
    )
    # On 2026-10-16, the entry from 2026-10-15 does NOT match today's date
    assert done_b is False
    assert reason_b == "not_produced_yet"


def test_exception_mid_crawl_releases_lock_in_finally(temp_state_dir, monkeypatch):
    """Boss Item 18 & 29: When an exception raises mid-crawl, the uncommitted IN_PROGRESS lock
    must be cleanly released in the finally block so subsequent runs are not stuck.
    """
    import unittest.mock as mock

    from app.services.daily_market_lock import is_market_done_today
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    mkt = "TEST_FINALLY"
    with mock.patch("app.services.trend_engine_b1.fetch_live_trending_terms", side_effect=RuntimeError("Simulated mid-crawl crash")):
        with pytest.raises(RuntimeError, match="Simulated mid-crawl crash"):
            discover_and_produce_market_trend(mkt, auto_produce=False, state_dir=temp_state_dir)

    # After exception, lock should be released
    done, reason, _ = is_market_done_today(mkt, state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is False
    assert reason == "not_produced_yet"


def test_non_timeout_cooldown_error_preserves_quota_mark(temp_state_dir, monkeypatch):
    """Boss Item 18 & 29: If alert cooldown raises an arbitrary non-timeout exception (e.g. ValueError or IOError),
    mark_exhausted_today has already stamped the quota, and the exception is caught safely without leaking.
    """
    import unittest.mock as mock

    from app.services.daily_market_lock import is_market_done_today
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    mkt = "TEST_QUOTA_MARK"
    fake_candidates = [{"term": "test term", "approx_traffic": "10K+", "geos_present": ["US"]}]
    with mock.patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=fake_candidates):
        with mock.patch("app.services.trend_engine_b1.forensic_pre_filter", return_value=(False, "Rejected for test")):
            with mock.patch("app.services.trend_engine_b1.should_send_alert", side_effect=IOError("Corrupt disk alert error")):
                res = discover_and_produce_market_trend(mkt, auto_produce=False, state_dir=temp_state_dir)
                assert res == []

    # Daily lock must be stamped EXHAUSTED_TODAY despite alert error
    done, reason, _ = is_market_done_today(mkt, state_dir=temp_state_dir, check_registry=False, check_episodes=False)
    assert done is True
    assert reason in ("lock_exhausted_today", "lock_exhausted_offhours")



def test_unreadable_lock_file_fails_closed_without_exception(temp_state_dir):
    """Boss Round 7 Item 3: An unreadable lock file (or directory at lock path) must fail closed
    (is_done=True, reason='corrupt_lock_fail_closed') without crashing with UnboundLocalError or any exception.
    """
    from app.services.daily_market_lock import _get_lock_file_path, is_market_done_today

    mkt = "TEST_UNREADABLE"
    lock_path = _get_lock_file_path(mkt, state_dir=temp_state_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a directory at the lock file path (makes open() raise IsADirectoryError / PermissionError / OSError)
    lock_path.mkdir(parents=True, exist_ok=True)

    try:
        is_done, reason, details = is_market_done_today(
            mkt, state_dir=temp_state_dir, check_registry=False, check_episodes=False
        )
        assert is_done is True, "Unreadable lock path must fail closed to protect quota"
        assert reason == "corrupt_lock_fail_closed"
        assert "error" in details
    finally:
        # Cleanup
        lock_path.rmdir()


def test_registry_check_ignores_temp_ids(temp_state_dir):
    """Ensure that B2/B2.1-rejected or in-flight *_TEMP_* task entries in topic_history_registry
    are NOT treated as committed by is_market_done_today (Boss Round 8 Revision 6).
    """
    from app.services.daily_market_lock import is_market_done_today

    reg_file = Path(temp_state_dir) / "topic_history.json"
    temp_registry = {
        "en-failed-candidate": {
            "market": "EN",
            "task_id": "EN_TEMP_failed123",
            "raw_term": "Failed Candidate",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        "en-rejected-handled": {
            "market": "EN",
            "task_id": "REJECTED_OR_HANDLED",
            "raw_term": "Rejected Candidate",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    with open(reg_file, "w", encoding="utf-8") as f:
        json.dump(temp_registry, f)

    is_done, reason, details = is_market_done_today(
        "EN", state_dir=temp_state_dir, registry_path=str(reg_file), check_registry=True, check_episodes=False
    )
    assert is_done is False, "TEMP and REJECTED_OR_HANDLED ids must not mark market done"
    assert reason == "not_produced_yet"


def test_unverified_mark_refuses_to_overwrite_existing_lock(temp_state_dir):
    """Boss Round 8 Item 16: mark_completed and mark_exhausted_today must refuse to overwrite
    an existing held lock unless the caller provides matching lock_token or explicit force_unverified=True.
    """
    from app.services.daily_market_lock import acquire_in_progress, mark_completed, mark_exhausted_today

    holder_token = "valid_holder_token_abc"
    acquired = acquire_in_progress("EN", topic_id="", state_dir=temp_state_dir, lock_token=holder_token)
    assert acquired is True

    # 1. Unverified mark_completed (no token, no force) -> must return False
    res1 = mark_completed("EN", topic_id="EN_EP9999_fake", state_dir=temp_state_dir)
    assert res1 is False

    # 2. Unverified mark_exhausted_today (no token, no force) -> must return False
    res2 = mark_exhausted_today("EN", scan_count=5, state_dir=temp_state_dir)
    assert res2 is False

    # 3. Mismatched token -> must return False
    res3 = mark_completed("EN", topic_id="EN_EP9999_fake", state_dir=temp_state_dir, lock_token="wrong_token_xyz")
    assert res3 is False

    # 4. Correct token -> succeeds
    res4 = mark_completed("EN", topic_id="EN_EP9999_fake", state_dir=temp_state_dir, lock_token=holder_token)
    assert res4 is True


def test_takeover_succeeds_when_age_exceeds_hard_max_even_if_pid_reused(temp_state_dir):
    """Boss Round 10 Item 4: When lock age exceeds HARD_MAX_IN_PROGRESS_AGE_SECONDS,
    takeover must succeed even if the PID is currently alive and reused.
    """
    import unittest.mock as mock
    from datetime import datetime, timezone, timedelta
    from app.services.daily_market_lock import (
        acquire_in_progress,
        HARD_MAX_IN_PROGRESS_AGE_SECONDS,
        _get_lock_file_path,
        atomic_write_json,
    )

    # Write an old lock that exceeds HARD_MAX (e.g. 3 hours old) with an "alive" reused PID
    old_time = datetime.now(timezone.utc) - timedelta(seconds=HARD_MAX_IN_PROGRESS_AGE_SECONDS + 600)
    lock_file = _get_lock_file_path("EN", temp_state_dir)
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    reused_pid = 99999
    atomic_write_json(lock_file, {
        "market": "EN",
        "vn_date": "2026-10-16",
        "status": "IN_PROGRESS",
        "created_at_utc": old_time.isoformat(),
        "ttl_seconds": 1800,
        "pid": reused_pid,
        "lock_token": "old_token",
    })

    # Even if is_pid_alive returns True (PID reused by another process)
    with mock.patch("app.services.alert_cooldown.is_pid_alive", return_value=True):
        acquired = acquire_in_progress("EN", state_dir=temp_state_dir, lock_token="new_takeover_token")
        assert acquired is True, "Takeover must succeed when age > HARD_MAX even if PID is alive (PID reuse defense)"


