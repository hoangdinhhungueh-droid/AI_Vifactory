#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_atomic_io.py — Unit Tests for Canonical Atomic IO & Durability (Rule 126 & Boss Item 13)."""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest

from core.atomic_io import atomic_write_json, cleanup_corrupt_quarantines


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="test_atomic_io_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


def test_atomic_write_json_durability_and_fsync(temp_dir, monkeypatch):
    """Boss Round 4 Item 13: Verifies that atomic_write_json flushes and calls fsync before atomic replacement."""
    target_file = temp_dir / "target.json"
    data = {"status": "ok", "count": 42, "nested": {"key": "value"}}

    fsync_called = []
    orig_fsync = os.fsync

    def mock_fsync(fd):
        fsync_called.append(fd)
        return orig_fsync(fd)

    monkeypatch.setattr(os, "fsync", mock_fsync)

    atomic_write_json(target_file, data)

    # 1. Target file must exist and contain exact valid JSON
    assert target_file.exists()
    loaded = json.loads(target_file.read_text(encoding="utf-8"))
    assert loaded == data

    # 2. os.fsync must have been invoked on the temporary file before atomic rename
    assert len(fsync_called) >= 1

    # 3. No leftover temp files in directory
    leftovers = list(temp_dir.glob("*.tmp_*"))
    assert len(leftovers) == 0


def test_atomic_write_json_cleans_up_tmp_on_failure(temp_dir, monkeypatch):
    """Verifies that an unhandled serialization error cleans up the temp file and raises IOError."""
    target_file = temp_dir / "failed.json"

    # Pass non-serializable object (e.g. set) to trigger json.dump failure
    invalid_data = {"unserializable": {1, 2, 3}}

    with pytest.raises(IOError, match="Failed to persist atomic JSON"):
        atomic_write_json(target_file, invalid_data)

    assert not target_file.exists()
    leftovers = list(temp_dir.glob("*.tmp_*"))
    assert len(leftovers) == 0


def test_cleanup_corrupt_quarantines_retention(temp_dir):
    """Verifies retention policy pruning stale corrupt files while keeping newest."""
    # Create 8 dummy corrupt files with different mtimes within the last hour
    now = time.time()
    for i in range(8):
        f = temp_dir / f"test.corrupt.{i}.json"
        f.write_text("corrupted", encoding="utf-8")
        # Staggered mtime: 8 files created within the last 800 seconds (well below 7 days)
        os.utime(str(f), (now - (8 - i) * 100, now - (8 - i) * 100))

    pruned = cleanup_corrupt_quarantines(temp_dir, pattern="*.corrupt.*", max_files=5)
    assert pruned == 3

    remaining = list(temp_dir.glob("*.corrupt.*"))
    assert len(remaining) == 5
