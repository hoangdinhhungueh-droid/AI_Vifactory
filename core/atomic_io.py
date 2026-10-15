#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/atomic_io.py — Canonical Atomic IO & Quarantine Retention Authority (Rule 125).

Unifies atomic JSON persistence with fsync and quarantine cleanup across all modules.
Eliminates divergent implementations between daily_market_lock and alert_cooldown.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def atomic_write_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """Atomic write of JSON data with fsync, unique uuid tempfile, and exception propagation.

    Ensures data durability on disk and handles Windows/POSIX atomic replacement.
    Cleans up temp file on any failure.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_name(f"{file_path.name}.tmp_{os.getpid()}_{uuid.uuid4().hex}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError as fsync_err:
                logger.debug(f"[atomic_io] Notice fsync on {tmp_path}: {fsync_err}")

        # Windows anti-virus retry loop for atomic replace
        for attempt in range(10):
            try:
                os.replace(str(tmp_path), str(file_path))
                break
            except (PermissionError, OSError):
                if attempt == 9:
                    raise
                time.sleep(0.05)
    except Exception as e:
        if tmp_path.exists():
            try:
                os.unlink(tmp_path)
            except OSError as rm_err:
                logger.warning(f"[atomic_io] Error removing tmp file {tmp_path}: {rm_err}")
        raise IOError(f"Failed to persist atomic JSON to {file_path}: {e}") from e


def cleanup_corrupt_quarantines(
    directory: Path,
    pattern: str = "*.corrupt.*",
    max_age_seconds: float = 86400 * 7,
    max_files: int = 5,
) -> int:
    """Retention policy for quarantine files to prevent unbounded disk accumulation (Rule 125 & Boss Item 29).

    Prunes files matching pattern exceeding max_age_seconds or keeping at most the newest max_files.
    Logs pruned files at INFO level.
    Returns the count of pruned files.
    """
    directory = Path(directory)
    if not directory.exists():
        return 0

    corrupt_files = sorted(
        directory.glob(pattern),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    pruned = 0
    now = time.time()
    for idx, cf in enumerate(corrupt_files):
        try:
            age = now - cf.stat().st_mtime
            if idx >= max_files or age > max_age_seconds:
                cf.unlink(missing_ok=True)
                logger.info(f"[atomic_io] Pruned stale retention file {cf.name} (age={int(age)}s)")
                pruned += 1
        except OSError as cf_err:
            logger.warning(f"[atomic_io] Error pruning quarantine file {cf}: {cf_err}")

    # Also clean up stale tombstone files (*tombstone*) older than 300s
    if pattern != "*tombstone*":
        tombstones = sorted(
            directory.glob("*tombstone*"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        for t_idx, tf in enumerate(tombstones):
            try:
                t_age = now - tf.stat().st_mtime
                if t_idx >= max_files or t_age > 300.0:
                    tf.unlink(missing_ok=True)
                    logger.info(f"[atomic_io] Pruned stale tombstone file {tf.name} (age={int(t_age)}s)")
                    pruned += 1
            except OSError as tf_err:
                logger.warning(f"[atomic_io] Error pruning tombstone file {tf}: {tf_err}")

    return pruned
