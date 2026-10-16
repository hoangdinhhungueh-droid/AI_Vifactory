# tests/conftest.py
"""Global pytest fixtures and test state isolation guards (Boss Item 15 & Rule 125)."""

import os
import pytest
from pathlib import Path
from core.paths import resolve_state_dir


@pytest.fixture(autouse=True)
def guard_test_state_dir_isolation(monkeypatch, tmp_path):
    """Guarantees that test runs never read or write to live /var/vf/locks state.

    If neither VF_STATE_DIR nor AVF_STATE_DIR is explicitly configured by the test,
    redirects state to an isolated temporary directory.
    Fails closed if resolve_state_dir points to /var/vf in any test.
    """
    if "VF_STATE_DIR" not in os.environ and "AVF_STATE_DIR" not in os.environ:
        test_state = tmp_path / "isolated_test_vf_state"
        test_state.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("VF_STATE_DIR", str(test_state))
        monkeypatch.setenv("AVF_STATE_DIR", str(test_state))

    if "TOPIC_HISTORY_PATH" not in os.environ:
        test_history = tmp_path / "isolated_topic_history.json"
        monkeypatch.setenv("TOPIC_HISTORY_PATH", str(test_history))

    # Assert that resolved state directory does not point to live VPS production lock path
    resolved = resolve_state_dir(read_only=True)
    resolved_str = str(resolved).replace("\\", "/")
    assert not resolved_str.startswith("/var/vf/locks"), (
        f"Test state isolation violation: resolve_state_dir returned production path '{resolved}'!"
    )

    from core.paths import resolve_topic_history_path
    resolved_history = str(resolve_topic_history_path()).replace("\\", "/")
    assert not resolved_history.startswith("/root/video_factory/data"), (
        f"Topic history isolation violation: resolve_topic_history_path returned production path '{resolved_history}'!"
    )
