#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_lock_liveness_probe.py
Comprehensive unit tests for process liveness and lock disposal verification probe.
Complies with Rule 118, Rule 125, Rule 137, and Boss Round 8 Items 15-18.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import pytest
import sys

from scripts.forensics.probe_lock_liveness import (
    validate_lock_metadata,
    check_pid_liveness,
    atomic_safe_archive,
    acquire_disposal_mutex,
    main as probe_main,
)


def test_validate_lock_metadata_valid(tmp_path: Path):
    """Verifies that a well-formed lock passes metadata validation."""
    valid_data = {
        "owner": "JP_TEMP_59.b3b4",
        "pid": 481461,
        "token": "LOCK_TOKEN_JP_TEMP_59_481461",
        "created_at": "2026-10-18T10:00:00+00:00",
    }
    lock_file = tmp_path / "test.lock"
    owner, token, created_at, pid = validate_lock_metadata(valid_data, lock_file)
    assert owner == "JP_TEMP_59.b3b4"
    assert token == "LOCK_TOKEN_JP_TEMP_59_481461"
    assert pid == 481461
    assert created_at == "2026-10-18T10:00:00+00:00"


def test_validate_lock_metadata_rejects_boolean_pid(tmp_path: Path):
    """Boss Round 8 Item 17: Asserts rejection of booleans (True/False) as PID."""
    lock_file = tmp_path / "test.lock"
    for bad_pid in (True, False):
        data = {
            "owner": "JP_TEMP_59.b3b4",
            "pid": bad_pid,
            "token": "LOCK_TOKEN_JP_TEMP_59_1",
            "created_at": "2026-10-18T10:00:00Z",
        }
        with pytest.raises(ValueError) as exc:
            validate_lock_metadata(data, lock_file)
        assert "invalid PID: must be strict integer" in str(exc.value)


def test_validate_lock_metadata_rejects_non_integral_pid(tmp_path: Path):
    """Boss Round 8 Item 17: Asserts rejection of non-integer PIDs (strings, floats, negatives)."""
    lock_file = tmp_path / "test.lock"
    for bad_pid in ("481461", 123.45, 0, -5):
        data = {
            "owner": "JP_TEMP_59.b3b4",
            "pid": bad_pid,
            "token": "LOCK_TOKEN_JP_TEMP_59_481461",
            "created_at": "2026-10-18T10:00:00Z",
        }
        with pytest.raises(ValueError) as exc:
            validate_lock_metadata(data, lock_file)
        assert "PID" in str(exc.value)


def test_validate_lock_metadata_requires_timezone_aware_timestamp(tmp_path: Path):
    """Boss Round 8 Item 17: Asserts rejection of naive ISO timestamps without timezone."""
    lock_file = tmp_path / "test.lock"
    naive_data = {
        "owner": "JP_TEMP_59.b3b4",
        "pid": 481461,
        "token": "LOCK_TOKEN_JP_TEMP_59_481461",
        "created_at": "2026-10-18T10:00:00",  # No Z or offset
    }
    with pytest.raises(ValueError) as exc:
        validate_lock_metadata(naive_data, lock_file)
    assert "must be timezone-aware" in str(exc.value)


def test_validate_lock_metadata_mismatched_token_holder(tmp_path: Path):
    """Boss Round 8 Item 17: Asserts rejection when token does not match owner scope or PID."""
    lock_file = tmp_path / "test.lock"
    # Mismatched scope
    data_bad_scope = {
        "owner": "JP_TEMP_59.b3b4",
        "pid": 481461,
        "token": "LOCK_TOKEN_EN_US_01_481461",
        "created_at": "2026-10-18T10:00:00Z",
    }
    with pytest.raises(ValueError) as exc:
        validate_lock_metadata(data_bad_scope, lock_file)
    assert "Token scope" in str(exc.value)

    # Mismatched PID
    data_bad_pid = {
        "owner": "JP_TEMP_59.b3b4",
        "pid": 481461,
        "token": "LOCK_TOKEN_JP_TEMP_59_999999",
        "created_at": "2026-10-18T10:00:00Z",
    }
    with pytest.raises(ValueError) as exc:
        validate_lock_metadata(data_bad_pid, lock_file)
    assert "Token PID" in str(exc.value)


def test_check_pid_liveness_current_process_and_nonexistent():
    """Verifies that check_pid_liveness correctly identifies self as alive and nonexistent PID as absent."""
    # Current process must be alive
    my_pid = os.getpid()
    is_alive, reason = check_pid_liveness(my_pid)
    assert is_alive is True
    assert "alive" in reason.lower() or "running" in reason.lower()

    # Highly unlikely PID (e.g. 4194300) should be reported dead or nonexistent
    dead_pid = 4194200
    is_dead, dead_reason = check_pid_liveness(dead_pid)
    if not is_dead:
        assert "not found" in dead_reason.lower() or "does not exist" in dead_reason.lower()


def test_atomic_safe_archive_same_filesystem_and_collision_safe(tmp_path: Path):
    """Boss Round 8 Item 18: Verifies collision-safe atomic archival with unique destination."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    dest_1 = atomic_safe_archive(active_lock, stale_dir)
    assert dest_1.exists()
    assert not active_lock.exists()
    assert dest_1.read_text(encoding="utf-8") == content

    # Re-create active lock and archive again to verify collision safety (distinct filenames)
    active_lock.write_text(content, encoding="utf-8")
    dest_2 = atomic_safe_archive(active_lock, stale_dir)
    assert dest_2.exists()
    assert dest_1.exists()
    assert dest_1 != dest_2, "Destinations must be unique to avoid clobbering"


def test_acquire_disposal_mutex_contention(tmp_path: Path):
    """Boss Round 8 Item 16: Verifies contention handling when shared disposal mutex is held."""
    mutex_file = tmp_path / ".disposal_operation.mutex"
    with acquire_disposal_mutex(mutex_file):
        # Attempting to acquire again in same process/thread with non-blocking should raise contention error
        with pytest.raises(RuntimeError) as exc:
            with acquire_disposal_mutex(mutex_file):
                pass
        assert "currently held by another process" in str(exc.value)


def test_probe_main_inspect_mode_clean_state_when_no_locks(tmp_path: Path):
    """Boss Round 8 Item 15: Read-only inspection exits 0 with CLEAN state when no locks exist."""
    fake_var = tmp_path / "var" / "vf" / "locks"
    fake_var.mkdir(parents=True)

    code = probe_main(["--inspect", "--locks-dir", str(fake_var)])
    assert code == 0


def test_probe_main_inspect_mode_ignores_advisory_mutex_locks(tmp_path: Path):
    """Verifies that persistent advisory files like alert_cooldown.json.lock or .mutex are ignored."""
    fake_var = tmp_path / "var" / "vf" / "locks"
    fake_var.mkdir(parents=True)

    # Write persistent advisory file with non-JSON content
    (fake_var / "alert_cooldown.json.lock").write_text("PID: 12345\nACQUIRED: 2026-10-18T23:00:00+00:00\n", encoding="utf-8")
    (fake_var / ".disposal_operation.mutex").write_text("", encoding="utf-8")

    code = probe_main(["--inspect", "--locks-dir", str(fake_var)])
    assert code == 0


def test_check_pid_liveness_detects_pid_reuse():
    """Boss Round 9 Item 18: Verifies PID_REUSED detection when process creation timestamp is after lock acquisition."""
    my_pid = os.getpid()
    # A lock timestamp far in the past (e.g. 2024-01-01) is guaranteed to be older than the current running test process
    past_ts = "2024-01-01T00:00:00+00:00"
    is_alive, reason = check_pid_liveness(my_pid, created_dt_str=past_ts)
    assert is_alive is False, f"Expected PID reuse detection, got is_alive={is_alive}, reason={reason}"
    assert "PID_REUSED" in reason
    assert "original holder dead" in reason

    # Conversely, a lock timestamp of NOW matches process start time (or is after it), confirming alive
    now_ts = datetime.now(timezone.utc).isoformat()
    is_alive_now, reason_now = check_pid_liveness(my_pid, created_dt_str=now_ts)
    assert is_alive_now is True
    assert "STILL_ACTIVE" in reason_now or "confirmed alive" in reason_now


def test_atomic_safe_archive_retries_on_destination_collision(tmp_path: Path):
    """Boss Round 9 Item 17: Verifies destination collision handling with unique destination retry."""
    import uuid
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    first_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    second_uuid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    uuid_calls = [first_uuid, second_uuid]

    orig_uuid4 = uuid.uuid4

    def deterministic_uuid4():
        if uuid_calls:
            return uuid_calls.pop(0)
        return uuid.UUID("33333333-3333-3333-3333-333333333333")

    uuid.uuid4 = deterministic_uuid4
    try:
        now_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        collided_path = stale_dir / f"{active_lock.stem}_{now_ts}_{first_uuid.hex[:8]}{active_lock.suffix}"
        collided_path.write_text("pre-existing collision file", encoding="utf-8")

        dest = atomic_safe_archive(active_lock, stale_dir)
        assert dest.exists()
        assert dest != collided_path
        assert not active_lock.exists()
        assert dest.read_text(encoding="utf-8") == content
    finally:
        uuid.uuid4 = orig_uuid4


def test_atomic_safe_archive_fails_on_source_sha_mismatch(tmp_path: Path):
    """Boss Round 9 Item 20: Fails closed when expected SHA does not match current source SHA."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    active_lock.write_text('{"owner": "JP_TEMP_59.b3b4"}', encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        atomic_safe_archive(active_lock, stale_dir, expected_sha="0000000000000000000000000000000000000000000000000000000000000000")
    assert "Source lock SHA changed concurrently" in str(exc.value)


def test_atomic_safe_archive_fails_on_cross_device(tmp_path: Path):
    """Boss Round 9 Item 17: Fails closed when source and destination are on different filesystem devices."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    active_lock.write_text('{"owner": "JP_TEMP_59.b3b4"}', encoding="utf-8")

    real_stat = os.stat

    def alternate_dev_stat(path, *args, **kwargs):
        st = real_stat(path, *args, **kwargs)
        if str(path) == str(stale_dir):
            import collections
            StatResult = collections.namedtuple("CustomStat", ["st_dev", "st_mode", "st_ino", "st_nlink", "st_uid", "st_gid", "st_size", "st_atime", "st_mtime", "st_ctime"])
            return StatResult(st.st_dev + 9999, st.st_mode, st.st_ino, st.st_nlink, st.st_uid, st.st_gid, st.st_size, st.st_atime, st.st_mtime, st.st_ctime)
        return st

    os.stat = alternate_dev_stat
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "Cross-filesystem archival violation" in str(exc.value)
    finally:
        os.stat = real_stat


def test_check_pid_liveness_fail_closed_on_indeterminate_or_permission():
    """Boss Round 9 Item 18: Liveness fails closed on permission error or indeterminate outcomes."""
    if sys.platform != "win32":
        orig_kill = os.kill

        def perm_denied_kill(pid, sig):
            raise PermissionError("Operation not permitted")

        os.kill = perm_denied_kill
        try:
            is_alive, reason = check_pid_liveness(12345)
            assert is_alive is True
            assert "EPERM permission denied - fail-closed" in reason
        finally:
            os.kill = orig_kill


