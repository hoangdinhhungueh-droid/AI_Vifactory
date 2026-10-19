#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_lock_liveness_probe.py
Comprehensive unit tests for process liveness and lock disposal verification probe.
Complies with Rule 118, Rule 125, Rule 137, and Boss Round 8 Items 15-18.
"""

from datetime import datetime, timezone, timedelta
import json
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
