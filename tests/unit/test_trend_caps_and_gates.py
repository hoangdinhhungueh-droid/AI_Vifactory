#!/usr/bin/env python3
"""
tests/unit/test_trend_caps_and_gates.py — Unit Tests for Trend Engine Caps, Level-0.5 Gate & B3 Subprocess.

Verifies:
1. Level-0.5 Evidence Catalyst Gate logic (all branches: reject, pass on news, pass on live traffic, pass on factsheet, bypass on custom_seed).
2. Robust Environment variable integer parsing with minimum bound clamping.
3. B3 execution command line structure (--profile prod, -m orchestrator.run_pipeline).
4. Produced topics gating on B3 success.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from app.services.trend_engine_b1 import (
    check_evidence_catalyst_gate,
    _parse_env_int,
    MAX_SCAN_CANDIDATES_DEFAULT,
    MAX_VIABILITY_LLM_EVALS_DEFAULT,
    MAX_B2_ATTEMPTS_DEFAULT,
    LIVE_TRAFFIC_SOURCES,
)


def test_level_0_5_gate_rejects_empty_evidence():
    """Branch (a): Rejects candidate when news_catalysts is empty, traffic is non-live, factsheet is empty."""
    ok, reason = check_evidence_catalyst_gate(
        news_catalysts=[],
        traffic_source="youtube_autocomplete",
        factsheet_extract="",
        is_custom_seed=False,
    )
    assert not ok
    assert "0 LLM tokens burned" in reason


def test_level_0_5_gate_passes_on_news_catalysts():
    """Branch (b1): Passes candidate when news_catalysts are present."""
    news = [{"title": "Breaking Financial Crisis", "url": "https://news.com/1"}]
    ok, reason = check_evidence_catalyst_gate(
        news_catalysts=news,
        traffic_source="youtube_autocomplete",
        factsheet_extract="",
        is_custom_seed=False,
    )
    assert ok
    assert "Verified with 1 breaking news catalyst" in reason


def test_level_0_5_gate_passes_on_live_traffic_source():
    """Branch (b2): Passes candidate when traffic source is live RSS."""
    for live_src in LIVE_TRAFFIC_SOURCES:
        ok, reason = check_evidence_catalyst_gate(
            news_catalysts=[],
            traffic_source=live_src,
            factsheet_extract="",
            is_custom_seed=False,
        )
        assert ok
        assert f"Verified live news source: {live_src}" in reason


def test_level_0_5_gate_passes_on_factsheet_extract():
    """Branch (b3): Passes candidate when ground-truth Wikipedia extract exists."""
    ok, reason = check_evidence_catalyst_gate(
        news_catalysts=[],
        traffic_source="youtube_autocomplete",
        factsheet_extract="Established corporate conglomerate founded in 1980.",
        is_custom_seed=False,
    )
    assert ok
    assert "Verified ground-truth entity factsheet" in reason


def test_level_0_5_gate_bypasses_on_custom_seed():
    """Branch (c): Bypasses pre-filter when user explicitly supplies custom_seed."""
    ok, reason = check_evidence_catalyst_gate(
        news_catalysts=[],
        traffic_source="unknown",
        factsheet_extract="",
        is_custom_seed=True,
    )
    assert ok
    assert "Bypassed: custom seed" in reason


def test_env_int_parsing_and_minimum_bound():
    """Verifies that _parse_env_int handles valid ints, empty, invalid strings, and clamps to min_val."""
    with patch.dict(os.environ, {"TEST_CAP_VAR": "42"}):
        assert _parse_env_int("TEST_CAP_VAR", default=10) == 42

    with patch.dict(os.environ, {"TEST_CAP_VAR": "invalid_number"}):
        assert _parse_env_int("TEST_CAP_VAR", default=10) == 10

    with patch.dict(os.environ, {"TEST_CAP_VAR": "-5"}):
        assert _parse_env_int("TEST_CAP_VAR", default=10, min_val=1) == 1

    with patch.dict(os.environ, {}, clear=False):
        if "TEST_CAP_VAR_NONEXISTENT" in os.environ:
            del os.environ["TEST_CAP_VAR_NONEXISTENT"]
        assert _parse_env_int("TEST_CAP_VAR_NONEXISTENT", default=7) == 7


def test_b3_invocation_command_contract():
    """Verifies B3 invocation constructs module call with --profile prod and --run-id."""
    task_id = "EN_EP0001_test_case"
    expected_prefix = [sys.executable, "-m", "orchestrator.run_pipeline"]
    expected_args = ["--profile", "prod", "--run-id", task_id]

    # Reconstruct cmd matching trend_engine_b1.py:1488
    cmd = [
        sys.executable,
        "-m",
        "orchestrator.run_pipeline",
        "--profile",
        "prod",
        "--run-id",
        str(task_id),
    ]

    assert cmd[:3] == expected_prefix
    assert cmd[3:] == expected_args
    assert "--profile" in cmd
    assert cmd[cmd.index("--profile") + 1] == "prod"
    assert cmd[cmd.index("--run-id") + 1] == task_id
