#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_paths_empty_run_id.py
Unit tests verifying RunPaths guards against empty string, whitespace, path traversal,
and drive letters, as well as checking dual directory fallback routing (Boss Round 11 Item 17).
"""

from pathlib import Path
import pytest

from core.paths import RunPaths


def test_empty_and_whitespace_run_id_raises_value_error(tmp_path: Path):
    """Empty string or whitespace-only run_id must raise ValueError."""
    with pytest.raises(ValueError, match="non-empty string"):
        RunPaths("", repo_root=tmp_path)

    with pytest.raises(ValueError, match="non-empty string"):
        RunPaths("   ", repo_root=tmp_path)

    with pytest.raises(ValueError, match="non-empty string"):
        RunPaths("\t\n", repo_root=tmp_path)

    with pytest.raises(ValueError, match="non-empty string"):
        RunPaths(None, repo_root=tmp_path)


def test_path_traversal_and_drive_letters_raise_value_error(tmp_path: Path):
    """run_id with path traversal (.., /, \\) or drive letters (:) must raise ValueError."""
    with pytest.raises(ValueError, match="Path traversal or drive letter"):
        RunPaths("../escape", repo_root=tmp_path)

    with pytest.raises(ValueError, match="Path traversal or drive letter"):
        RunPaths("..\\escape", repo_root=tmp_path)

    with pytest.raises(ValueError, match="Path traversal or drive letter"):
        RunPaths("foo/bar", repo_root=tmp_path)

    with pytest.raises(ValueError, match="Path traversal or drive letter"):
        RunPaths("foo\\bar", repo_root=tmp_path)

    with pytest.raises(ValueError, match="Path traversal or drive letter"):
        RunPaths("C:malicious", repo_root=tmp_path)

    with pytest.raises(ValueError, match="Path traversal or drive letter"):
        RunPaths("D:/var/run", repo_root=tmp_path)


def test_valid_run_id_resolves_and_creates_structure(tmp_path: Path):
    """A valid run_id creates canonical folder structure properly."""
    rp = RunPaths("RUN_20261016_120000", repo_root=tmp_path)
    assert rp.run_id == "RUN_20261016_120000"
    assert rp.root.exists()
    assert rp.composite_seeds_dir.exists()
    assert rp.video_clips_dir.exists()
    assert rp.audio_dir.exists()
    assert rp.blocks_dir.exists()


def test_legacy_episodes_directory_fallback(tmp_path: Path):
    """If an episode exists under <repo_root>/episodes/<run_id>, RunPaths anchors to it."""
    legacy_ep_dir = tmp_path / "episodes" / "EN_EP0099_historical_test"
    legacy_ep_dir.mkdir(parents=True, exist_ok=True)

    rp = RunPaths("EN_EP0099_historical_test", repo_root=tmp_path)
    assert rp.root == legacy_ep_dir
