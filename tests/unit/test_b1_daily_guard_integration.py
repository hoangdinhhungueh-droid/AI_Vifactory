"""
tests/unit/test_b1_daily_guard_integration.py — INTEGRATION TESTS FOR B1 DAILY GUARD & SKIP BEHAVIOR
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from app.services.daily_market_lock import mark_completed
from app.services.trend_engine_b1 import discover_and_produce_market_trend


@pytest.fixture
def isolated_env():
    temp_state = tempfile.mkdtemp(prefix="test_b1_int_state_")
    old_state = os.environ.get("AVF_STATE_DIR")
    os.environ["AVF_STATE_DIR"] = temp_state
    yield temp_state
    if old_state:
        os.environ["AVF_STATE_DIR"] = old_state
    else:
        os.environ.pop("AVF_STATE_DIR", None)
    shutil.rmtree(temp_state, ignore_errors=True)


def test_b1_skips_immediately_when_market_already_completed(isolated_env):
    """When market EN is already COMPLETED today, discover_and_produce_market_trend
    must exit immediately without calling any candidate scraper or LLM.
    """
    # Pre-mark market EN as COMPLETED today
    mark_completed("EN", topic_id="EN_EP0001_retatrutide_shadow_market", state_dir=isolated_env)

    # Mock fetch_live_trending_terms to assert it is NEVER called
    with patch("app.services.trend_engine_b1.fetch_live_trending_terms") as mock_fetch:
        results = discover_and_produce_market_trend(market="EN", auto_produce=False)
        assert results == []
        mock_fetch.assert_not_called()


def test_b1_custom_seed_bypasses_daily_completion(isolated_env):
    """When custom_seed is supplied, discover_and_produce_market_trend must bypass the lock (call_count == 1)."""
    mark_completed("EN", topic_id="EN_EP0001_retatrutide_shadow_market", state_dir=isolated_env)
    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=[]) as mock_fetch:
        results = discover_and_produce_market_trend(market="EN", custom_seed="custom_topic", auto_produce=False)
        assert results == []
        assert mock_fetch.call_count == 1


def test_b1_force_crawl_env_bypasses_daily_completion(isolated_env):
    """When B1_FORCE_CRAWL=1 is active, discover_and_produce_market_trend must bypass the lock (call_count == 1)."""
    mark_completed("EN", topic_id="EN_EP0001_retatrutide_shadow_market", state_dir=isolated_env)
    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=[]) as mock_fetch:
        os.environ["B1_FORCE_CRAWL"] = "1"
        try:
            results = discover_and_produce_market_trend(market="EN", auto_produce=False)
            assert results == []
            assert mock_fetch.call_count == 1
        finally:
            os.environ.pop("B1_FORCE_CRAWL", None)
