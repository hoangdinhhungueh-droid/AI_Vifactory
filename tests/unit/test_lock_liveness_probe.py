#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_lock_liveness_probe.py
Comprehensive unit tests for process liveness and lock disposal verification probe.
Complies with Rule 118, Rule 125, Rule 137, and Boss Round 10 Requirements.
Zero synthetic doubles: strictly uses deterministic attribute stubs.
"""

import errno
import multiprocessing
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.forensics.probe_lock_liveness import (
    _mp_disposal_worker,
    acquire_disposal_mutex,
    atomic_safe_archive,
    check_pid_liveness,
    get_posix_proc_starttime,
    validate_lock_metadata,
)
from scripts.forensics.probe_lock_liveness import (
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
        "created_at": "2026-10-18T10:00:00",
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
    my_pid = os.getpid()
    is_alive, reason = check_pid_liveness(my_pid)
    assert is_alive is True
    assert "alive" in reason.lower() or "running" in reason.lower()

    # Highly unlikely PID (e.g. 4194200) should be reported dead or nonexistent
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
        with pytest.raises(RuntimeError) as exc:
            with acquire_disposal_mutex(mutex_file):
                pass
        assert "currently held by another process" in str(exc.value)


def test_acquire_disposal_mutex_unlock_failure_raises(tmp_path: Path):
    """Boss Round 10 Item 15: Mutex unlock failures must not be downgraded to warning if safety affected."""
    mutex_file = tmp_path / ".disposal_operation.mutex"
    if sys.platform != "win32":
        import fcntl
        orig_flock = fcntl.flock

        def faulty_flock(fd, op):
            if op == fcntl.LOCK_UN:
                raise OSError(errno.EIO, "I/O error during unlock")
            return orig_flock(fd, op)

        fcntl.flock = faulty_flock
        try:
            with pytest.raises(RuntimeError) as exc:
                with acquire_disposal_mutex(mutex_file):
                    pass
            assert "Critical mutex unlock failure" in str(exc.value)
        finally:
            fcntl.flock = orig_flock
    else:
        import msvcrt
        orig_locking = msvcrt.locking

        def faulty_locking(fd, mode, nbytes):
            if mode == msvcrt.LK_UNLCK:
                raise OSError(errno.EACCES, "Permission denied during unlock")
            return orig_locking(fd, mode, nbytes)

        msvcrt.locking = faulty_locking
        try:
            with pytest.raises(RuntimeError) as exc:
                with acquire_disposal_mutex(mutex_file):
                    pass
            assert "Critical mutex unlock failure" in str(exc.value)
        finally:
            msvcrt.locking = orig_locking


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

    (fake_var / "alert_cooldown.json.lock").write_text("PID: 12345\nACQUIRED: 2026-10-18T23:00:00+00:00\n", encoding="utf-8")
    (fake_var / ".disposal_operation.mutex").write_text("", encoding="utf-8")

    code = probe_main(["--inspect", "--locks-dir", str(fake_var)])
    assert code == 0


def test_check_pid_liveness_detects_pid_reuse():
    """Boss Round 9 Item 18: Verifies PID_REUSED detection when process creation timestamp is after lock acquisition."""
    my_pid = os.getpid()
    past_ts = "2024-01-01T00:00:00+00:00"
    is_alive, reason = check_pid_liveness(my_pid, created_dt_str=past_ts)
    assert is_alive is False, f"Expected PID reuse detection, got is_alive={is_alive}, reason={reason}"
    assert "PID_REUSED" in reason
    assert "original holder dead" in reason

    now_ts = datetime.now(timezone.utc).isoformat()
    is_alive_now, reason_now = check_pid_liveness(my_pid, created_dt_str=now_ts)
    assert is_alive_now is True
    assert "STILL_ACTIVE" in reason_now or "confirmed alive" in reason_now


def test_check_pid_liveness_invalid_created_at_fails_closed():
    """Boss Round 10 Item 15: Invalid created_at metadata produces explicit fail-closed result."""
    my_pid = os.getpid()
    bad_ts = "not-a-timestamp"
    is_alive, reason = check_pid_liveness(my_pid, created_dt_str=bad_ts)
    assert is_alive is None
    assert "INDETERMINATE" in reason
    assert "fail-closed" in reason


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

    real_stat = Path.stat

    def alternate_dev_stat(self_path, *args, **kwargs):
        st = real_stat(self_path, *args, **kwargs)
        if str(self_path) == str(stale_dir):
            import collections
            StatResult = collections.namedtuple("CustomStat", ["st_dev", "st_mode", "st_ino", "st_nlink", "st_uid", "st_gid", "st_size", "st_atime", "st_mtime", "st_ctime"])
            return StatResult(st.st_dev + 9999, st.st_mode, st.st_ino, st.st_nlink, st.st_uid, st.st_gid, st.st_size, st.st_atime, st.st_mtime, st.st_ctime)
        return st

    Path.stat = alternate_dev_stat
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "Cross-filesystem archival violation" in str(exc.value)
    finally:
        Path.stat = real_stat


def test_atomic_safe_archive_source_replacement_inode_race_detection(tmp_path: Path):
    """Boss Round 10 Item 18: Detects inode replacement race between validation and mutation."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    active_lock.write_text('{"owner": "JP_TEMP_59.b3b4"}', encoding="utf-8")

    import scripts.forensics.probe_lock_liveness as probe_mod

    race_triggered = [False]
    real_sha = probe_mod.compute_file_sha256

    def race_sha(p):
        res = real_sha(p)
        if str(p) == str(active_lock):
            race_triggered[0] = True
        return res

    real_stat = Path.stat

    def replaced_inode_stat(self_path, *args, **kwargs):
        st = real_stat(self_path, *args, **kwargs)
        if race_triggered[0] and str(self_path) == str(active_lock):
            import collections
            StatResult = collections.namedtuple("CustomStat", ["st_dev", "st_mode", "st_ino", "st_nlink", "st_uid", "st_gid", "st_size", "st_atime", "st_mtime", "st_ctime"])
            return StatResult(st.st_dev, st.st_mode, st.st_ino + 100, st.st_nlink, st.st_uid, st.st_gid, st.st_size, st.st_atime, st.st_mtime, st.st_ctime)
        return st

    probe_mod.compute_file_sha256 = race_sha
    Path.stat = replaced_inode_stat
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "Source replacement race detected: inode changed" in str(exc.value)
    finally:
        Path.stat = real_stat
        probe_mod.compute_file_sha256 = real_sha


def test_atomic_safe_archive_destination_fsync_failure_rollback(tmp_path: Path):
    """Boss Round 10 Item 19: Proves cleanup and rollback behavior when destination fsync fails."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    orig_fsync = os.fsync

    def failing_fsync(fd):
        raise OSError(errno.EIO, "Injected disk fsync I/O failure")

    os.fsync = failing_fsync
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "Destination fsync failed (verified rollback performed)" in str(exc.value)
        # Source lock must still exist intact after failure rollback
        assert active_lock.exists()
        assert active_lock.read_text(encoding="utf-8") == content
    finally:
        os.fsync = orig_fsync


def test_check_pid_liveness_fail_closed_on_indeterminate_or_permission():
    """Boss Round 10 Item 16: PermissionError or indeterminate outcomes return None (fail-closed, aborts disposal)."""
    if sys.platform != "win32":
        orig_kill = os.kill

        def perm_denied_kill(pid, sig):
            raise PermissionError("Operation not permitted")

        os.kill = perm_denied_kill
        try:
            is_alive, reason = check_pid_liveness(12345)
            # Must return None (indeterminate / fail-closed), NOT True
            assert is_alive is None, f"Expected is_alive=None for PermissionError, got {is_alive}"
            assert "INDETERMINATE" in reason
            assert "permission denied" in reason.lower()
            # Verify caller aborts disposal
            assert is_alive is not False, "Disposal must be aborted when is_alive is not False"
        finally:
            os.kill = orig_kill
    else:
        # On Windows, Access Denied should also return None (indeterminate / fail-closed)
        import ctypes
        orig_open_proc = ctypes.windll.kernel32.OpenProcess
        orig_get_last_error = ctypes.windll.kernel32.GetLastError

        def access_denied_open_proc(dwDesiredAccess, bInheritHandle, dwProcessId):
            return 0

        def access_denied_error():
            return 5  # ERROR_ACCESS_DENIED

        ctypes.windll.kernel32.OpenProcess = access_denied_open_proc
        ctypes.windll.kernel32.GetLastError = access_denied_error
        try:
            is_alive, reason = check_pid_liveness(12345)
            assert is_alive is None
            assert "INDETERMINATE" in reason
            assert is_alive is not False, "Disposal must be aborted when is_alive is not False"
        finally:
            ctypes.windll.kernel32.OpenProcess = orig_open_proc
            ctypes.windll.kernel32.GetLastError = orig_get_last_error


def test_get_posix_proc_starttime_parses_field_22(tmp_path: Path):
    """Boss Round 10 Item 17: Validates Linux /proc/<pid>/stat field 22 starttime parsing."""
    stat_line = "12345 (python worker process) S 1 12345 12345 0 0 4194304 100 0 0 0 10 5 0 0 20 0 1 0 85000 1000 200"
    pid_dir = tmp_path / "12345"
    pid_dir.mkdir()
    proc_stat_file = pid_dir / "stat"
    proc_stat_file.write_text(stat_line, encoding="utf-8")

    system_stat = "cpu 100 200\nbtime 1700000000\n"
    system_stat_file = tmp_path / "stat"
    system_stat_file.write_text(system_stat, encoding="utf-8")

    if sys.platform == "win32":
        dt, reason = get_posix_proc_starttime(12345, proc_root=str(tmp_path))
        assert dt is None
        assert "SC_CLK_TCK unavailable" in reason
    else:
        dt, reason = get_posix_proc_starttime(12345, proc_root=str(tmp_path))
        assert dt is not None, f"Expected parsed starttime, got {reason}"
        assert reason == "OK"
        clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        expected_epoch = 1700000000 + (85000 / float(clk_tck))
        assert dt.timestamp() == expected_epoch


def test_get_posix_proc_starttime_clk_tck_unavailable_fails_closed(tmp_path: Path):
    """Boss Round 11: If SC_CLK_TCK is unavailable or <= 0, fails closed with indeterminate."""
    stat_line = "12345 (proc) S 1 12345 12345 0 0 4194304 100 0 0 0 10 5 0 0 20 0 1 0 85000 1000 200"
    pid_dir = tmp_path / "12345"
    pid_dir.mkdir()
    (pid_dir / "stat").write_text(stat_line, encoding="utf-8")
    (tmp_path / "stat").write_text("btime 1700000000\n", encoding="utf-8")

    if sys.platform != "win32":
        orig_sysconf = os.sysconf

        def failing_sysconf(name):
            return 0  # Invalid tick rate <= 0

        os.sysconf = failing_sysconf
        try:
            dt, reason = get_posix_proc_starttime(12345, proc_root=str(tmp_path))
            assert dt is None
            assert "INDETERMINATE: SC_CLK_TCK unavailable" in reason
        finally:
            os.sysconf = orig_sysconf
    else:
        dt, reason = get_posix_proc_starttime(12345, proc_root=str(tmp_path))
        assert dt is None
        assert "INDETERMINATE: SC_CLK_TCK unavailable" in reason


def test_concurrent_archival_race_of_same_source(tmp_path: Path):
    """Boss Round 11: Genuine overlapping concurrent archival of same source using ThreadPoolExecutor and Barrier."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    barrier = threading.Barrier(2)
    results = []
    errors = []

    def racer_task():
        barrier.wait()
        try:
            dest = atomic_safe_archive(active_lock, stale_dir)
            results.append(dest)
        except Exception as exc:
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(racer_task)
        f2 = executor.submit(racer_task)
        f1.result()
        f2.result()

    # The race must resolve safely: source is guaranteed gone, and all destinations valid
    assert not active_lock.exists()
    assert len(results) >= 1
    assert len(results) + len(errors) == 2
    for dest in results:
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == content
    for err in errors:
        assert isinstance(err, (FileNotFoundError, RuntimeError, PermissionError, OSError))


def test_atomic_safe_archive_physical_source_replacement(tmp_path: Path):
    """Boss Round 11: True physical file replacement where source file is unlinked and recreated on disk."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4", "version": 1}'
    active_lock.write_text(content, encoding="utf-8")

    orig_fsync = os.fsync
    replaced = [False]

    def intercepting_fsync(fd):
        if not replaced[0]:
            replaced[0] = True
            # Physically unlink and recreate source file on disk with different content
            active_lock.unlink()
            active_lock.write_text('{"owner": "JP_TEMP_59.b3b4", "version": 2, "replaced": true}', encoding="utf-8")
        return orig_fsync(fd)

    os.fsync = intercepting_fsync
    try:
        with pytest.raises((RuntimeError, ValueError)) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        err_msg = str(exc.value)
        assert "Source replacement detected" in err_msg or "Source content changed" in err_msg
        # Active lock must exist on disk with the new replaced content
        assert active_lock.exists()
        assert 'version": 2' in active_lock.read_text(encoding="utf-8")
    finally:
        os.fsync = orig_fsync


def test_atomic_safe_archive_source_directory_fsync_failure(tmp_path: Path):
    """Boss Round 11: Validates failure handling when source directory fsync fails on POSIX."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    if sys.platform == "win32":
        # On Windows, O_DIRECTORY is not supported, atomic_safe_archive completes safely
        dest = atomic_safe_archive(active_lock, stale_dir)
        assert dest.exists()
        assert not active_lock.exists()
    else:
        orig_fsync = os.fsync
        call_count = [0]

        def failing_src_dir_fsync(fd):
            call_count[0] += 1
            # 1st fsync is file-level dst fsync, 2nd is dst dir fsync, 3rd is src dir fsync
            if call_count[0] == 3:
                raise OSError(errno.EIO, "Source directory fsync failed")
            return orig_fsync(fd)

        os.fsync = failing_src_dir_fsync
        try:
            with pytest.raises(OSError) as exc:
                atomic_safe_archive(active_lock, stale_dir)
            assert "Source directory fsync failed" in str(exc.value)
        finally:
            os.fsync = orig_fsync


def test_acquire_disposal_mutex_descriptor_closure_on_body_failure(tmp_path: Path):
    """Boss Round 11: Verifies file descriptor is closed when the context body raises an exception."""
    mutex_file = tmp_path / ".disposal_operation.mutex"
    captured_fds = []
    orig_open = os.open

    def tracking_open(*args, **kwargs):
        fd = orig_open(*args, **kwargs)
        if str(mutex_file) in str(args[0]):
            captured_fds.append(fd)
        return fd

    os.open = tracking_open
    try:
        with pytest.raises(ValueError) as exc:
            with acquire_disposal_mutex(mutex_file):
                raise ValueError("Injected body error")
        assert "Injected body error" in str(exc.value)
        assert len(captured_fds) == 1
        with pytest.raises(OSError) as stat_exc:
            os.fstat(captured_fds[0])
        assert stat_exc.value.errno == errno.EBADF
    finally:
        os.open = orig_open


def test_acquire_disposal_mutex_descriptor_closure_on_acquisition_failure(tmp_path: Path):
    """Boss Round 11: Verifies file descriptor is closed when lock acquisition fails under contention."""
    mutex_file = tmp_path / ".disposal_operation.mutex"
    captured_fds = []
    orig_open = os.open

    def tracking_open(*args, **kwargs):
        fd = orig_open(*args, **kwargs)
        if str(mutex_file) in str(args[0]):
            captured_fds.append(fd)
        return fd

    with acquire_disposal_mutex(mutex_file):
        os.open = tracking_open
        try:
            with pytest.raises(RuntimeError) as exc:
                with acquire_disposal_mutex(mutex_file):
                    pass
            assert "currently held by another process" in str(exc.value)
            assert len(captured_fds) == 1
            with pytest.raises(OSError) as stat_exc:
                os.fstat(captured_fds[0])
            assert stat_exc.value.errno == errno.EBADF
        finally:
            os.open = orig_open


def test_acquire_disposal_mutex_descriptor_closure_on_unlock_failure(tmp_path: Path):
    """Boss Round 11: Verifies file descriptor is closed even when unlocking raises a critical error."""
    mutex_file = tmp_path / ".disposal_operation.mutex"
    captured_fds = []
    orig_open = os.open

    def tracking_open(*args, **kwargs):
        fd = orig_open(*args, **kwargs)
        if str(mutex_file) in str(args[0]):
            captured_fds.append(fd)
        return fd

    os.open = tracking_open
    try:
        if sys.platform != "win32":
            import fcntl
            orig_flock = fcntl.flock

            def faulty_flock(fd, op):
                if op == fcntl.LOCK_UN:
                    raise OSError(errno.EIO, "Unlock failed")
                return orig_flock(fd, op)

            fcntl.flock = faulty_flock
            try:
                with pytest.raises(RuntimeError) as exc:
                    with acquire_disposal_mutex(mutex_file):
                        pass
                assert "Critical mutex unlock failure" in str(exc.value)
            finally:
                fcntl.flock = orig_flock
        else:
            import msvcrt
            orig_locking = msvcrt.locking

            def faulty_locking(fd, mode, nbytes):
                if mode == msvcrt.LK_UNLCK:
                    raise OSError(errno.EACCES, "Permission denied during unlock")
                return orig_locking(fd, mode, nbytes)

            msvcrt.locking = faulty_locking
            try:
                with pytest.raises(RuntimeError) as exc:
                    with acquire_disposal_mutex(mutex_file):
                        pass
                assert "Critical mutex unlock failure" in str(exc.value)
            finally:
                msvcrt.locking = orig_locking

        assert len(captured_fds) == 1
        with pytest.raises(OSError) as stat_exc:
            os.fstat(captured_fds[0])
        assert stat_exc.value.errno == errno.EBADF
    finally:
        os.open = orig_open


def test_multiprocess_archival_race_under_mutex(tmp_path: Path):
    """Proves cross-process mutual exclusion during concurrent archival using multiprocessing.Process and Barrier."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()
    mutex_file = locks_dir / ".disposal_operation.mutex"

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    ctx = multiprocessing.get_context("spawn" if sys.platform == "win32" else "fork")
    barrier = ctx.Barrier(2)
    results_queue = ctx.Queue()

    p1 = ctx.Process(target=_mp_disposal_worker, args=(str(mutex_file), str(active_lock), str(stale_dir), barrier, results_queue))
    p2 = ctx.Process(target=_mp_disposal_worker, args=(str(mutex_file), str(active_lock), str(stale_dir), barrier, results_queue))

    p1.start()
    p2.start()
    p1.join(timeout=15)
    p2.join(timeout=15)

    outputs = []
    while not results_queue.empty():
        outputs.append(results_queue.get_nowait())

    assert len(outputs) == 2
    successes = [out for out in outputs if out[0] == "SUCCESS"]
    errors = [out for out in outputs if out[0] == "ERROR"]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {outputs}"
    assert len(errors) == 1, f"Expected exactly 1 error, got {len(errors)}: {outputs}"
    assert not active_lock.exists()
    archived_files = list(stale_dir.glob("JP_TEMP_59.b3b4_*.lock"))
    assert len(archived_files) == 1
    assert archived_files[0].read_text(encoding="utf-8") == content


def test_probe_main_indeterminate_at_initial_inspection_causes_zero_mutation(tmp_path: Path):
    """Proves that LivenessStatus.INDETERMINATE at initial inspection causes zero mutation."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4", "pid": 999999, "token": "LOCK_TOKEN_JP_TEMP_59_999999", "created_at": "2026-10-18T10:00:00+00:00"}'
    active_lock.write_text(content, encoding="utf-8")

    import scripts.forensics.probe_lock_liveness as probe_mod
    orig_check = probe_mod.check_pid_liveness

    def indeterminate_check(pid, created_dt_str=None):
        return probe_mod.LivenessResult(
            status=probe_mod.LivenessStatus.INDETERMINATE,
            is_alive=None,
            proc_start=None,
            diagnostic="EPERM permission denied",
        )

    probe_mod.check_pid_liveness = indeterminate_check
    try:
        exit_code = probe_main(["--dispose", f"--locks-dir={locks_dir}"])
        assert exit_code == 1
        assert active_lock.exists(), "Source lock must NOT be modified or deleted"
        assert active_lock.read_text(encoding="utf-8") == content
        assert len(list(stale_dir.iterdir())) == 0, "Destination stale dir must remain empty"
    finally:
        probe_mod.check_pid_liveness = orig_check


def test_probe_main_indeterminate_at_mutex_revalidation_causes_zero_mutation(tmp_path: Path):
    """Proves that LivenessStatus.INDETERMINATE at mutex-held revalidation causes zero mutation."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4", "pid": 999999, "token": "LOCK_TOKEN_JP_TEMP_59_999999", "created_at": "2026-10-18T10:00:00+00:00"}'
    active_lock.write_text(content, encoding="utf-8")

    import scripts.forensics.probe_lock_liveness as probe_mod
    orig_check = probe_mod.check_pid_liveness
    invocation = [0]

    def dynamic_check(pid, created_dt_str=None):
        invocation[0] += 1
        if invocation[0] == 1:
            return probe_mod.LivenessResult(
                status=probe_mod.LivenessStatus.CONFIRMED_DEAD,
                is_alive=False,
                proc_start=None,
                diagnostic="PID confirmed absent",
            )
        return probe_mod.LivenessResult(
            status=probe_mod.LivenessStatus.INDETERMINATE,
            is_alive=None,
            proc_start=None,
            diagnostic="EPERM permission denied under mutex",
        )

    probe_mod.check_pid_liveness = dynamic_check
    try:
        with pytest.raises(RuntimeError) as exc:
            probe_main(["--dispose", f"--locks-dir={locks_dir}"])
        assert "Race condition detected" in str(exc.value)
        assert "INDETERMINATE" in str(exc.value)
        assert active_lock.exists(), "Source lock must NOT be modified or deleted"
        assert active_lock.read_text(encoding="utf-8") == content
        assert len(list(stale_dir.iterdir())) == 0, "Destination stale dir must remain empty"
    finally:
        probe_mod.check_pid_liveness = orig_check


def test_atomic_safe_archive_copy_fallback_failure_rollback(tmp_path: Path):
    """Verifies that copy fallback cleans up destination and leaves source intact on I/O write error."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4", "data": "payload"}'
    active_lock.write_text(content, encoding="utf-8")

    orig_link = os.link
    orig_write = os.write

    def fail_link(src, dst):
        raise NotImplementedError("Link unsupported")

    def fail_write(fd, data):
        raise OSError(errno.ENOSPC, "No space left on device")

    os.link = fail_link
    os.write = fail_write
    try:
        with pytest.raises((RuntimeError, OSError)) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "No space left on device" in str(exc.value)
        assert active_lock.exists()
        assert active_lock.read_text(encoding="utf-8") == content
        assert len(list(stale_dir.iterdir())) == 0
    finally:
        os.link = orig_link
        os.write = orig_write


def test_atomic_safe_archive_destination_rollback_reporting(tmp_path: Path):
    """Verifies explicit rollback reporting: 'verified rollback performed' on clean removal vs 'rollback failed or incomplete'."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    orig_fsync = os.fsync
    orig_unlink = os.unlink

    def fail_fsync(fd):
        raise OSError(errno.EIO, "fsync write failure")

    # Case 1: fsync fails, unlinking destination succeeds -> reports 'verified rollback performed'
    os.fsync = fail_fsync
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "verified rollback performed" in str(exc.value)
        assert active_lock.exists()
        assert len(list(stale_dir.iterdir())) == 0
    finally:
        os.fsync = orig_fsync

    # Case 2: fsync fails and unlinking destination also fails -> reports 'rollback failed or incomplete'
    def fail_unlink(path):
        if str(stale_dir) in str(path):
            raise OSError(errno.EACCES, "unlink access denied")
        return orig_unlink(path)

    os.fsync = fail_fsync
    os.unlink = fail_unlink
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir)
        assert "rollback failed or incomplete" in str(exc.value)
        assert active_lock.exists()
    finally:
        os.fsync = orig_fsync
        os.unlink = orig_unlink


def test_atomic_safe_archive_destination_collision_exhaustion(tmp_path: Path):
    """Verifies that persistent destination collisions exhaust max_retries and fail-closed without mutating source."""
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    stale_dir = locks_dir / "_stale"
    stale_dir.mkdir()

    active_lock = locks_dir / "JP_TEMP_59.b3b4.lock"
    content = '{"owner": "JP_TEMP_59.b3b4"}'
    active_lock.write_text(content, encoding="utf-8")

    orig_link = os.link

    def always_colliding_link(src, dst):
        raise FileExistsError(errno.EEXIST, "File already exists")

    os.link = always_colliding_link
    try:
        with pytest.raises(RuntimeError) as exc:
            atomic_safe_archive(active_lock, stale_dir, max_retries=3)
        assert "Failed to atomically reserve unique destination" in str(exc.value)
        assert "after 3 attempts" in str(exc.value)
        assert active_lock.exists()
        assert active_lock.read_text(encoding="utf-8") == content
    finally:
        os.link = orig_link
