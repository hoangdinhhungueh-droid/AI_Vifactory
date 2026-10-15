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
    old_avf = os.environ.get("AVF_STATE_DIR")
    old_vf = os.environ.get("VF_STATE_DIR")
    os.environ["AVF_STATE_DIR"] = temp_state
    os.environ["VF_STATE_DIR"] = temp_state
    yield temp_state
    if old_avf:
        os.environ["AVF_STATE_DIR"] = old_avf
    else:
        os.environ.pop("AVF_STATE_DIR", None)
    if old_vf:
        os.environ["VF_STATE_DIR"] = old_vf
    else:
        os.environ.pop("VF_STATE_DIR", None)
    shutil.rmtree(temp_state, ignore_errors=True)


def test_b1_skips_immediately_when_market_already_completed(isolated_env):
    """When market EN is already COMPLETED today, discover_and_produce_market_trend
    must exit immediately without calling any candidate scraper or LLM.
    """
    # Pre-mark market EN as COMPLETED today
    mark_completed("EN", topic_id="EN_EP0001_retatrutide_shadow_market", state_dir=isolated_env)

    # Mock fetch_live_trending_terms to assert it is NEVER called
    with patch("app.services.trend_engine_b1.fetch_live_trending_terms") as mock_fetch:
        results = discover_and_produce_market_trend(market="EN", auto_produce=False, state_dir=isolated_env)
        assert results == []
        mock_fetch.assert_not_called()


def test_b1_custom_seed_bypasses_daily_completion(isolated_env):
    """When custom_seed is supplied, discover_and_produce_market_trend must bypass the lock (call_count == 1)."""
    mark_completed("EN", topic_id="EN_EP0001_retatrutide_shadow_market", state_dir=isolated_env)
    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=[]) as mock_fetch:
        results = discover_and_produce_market_trend(market="EN", custom_seed="custom_topic", auto_produce=False, state_dir=isolated_env)
        assert results == []
        assert mock_fetch.call_count == 1


def test_b1_force_crawl_env_bypasses_daily_completion(isolated_env):
    """When B1_FORCE_CRAWL=1 is active, discover_and_produce_market_trend must bypass the lock (call_count == 1)."""
    mark_completed("EN", topic_id="EN_EP0001_retatrutide_shadow_market", state_dir=isolated_env)
    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=[]) as mock_fetch:
        os.environ["B1_FORCE_CRAWL"] = "1"
        try:
            results = discover_and_produce_market_trend(market="EN", auto_produce=False, state_dir=isolated_env)
            assert results == []
            assert mock_fetch.call_count == 1
        finally:
            os.environ.pop("B1_FORCE_CRAWL", None)


def test_b1_caller_handling_of_lock_timeout_error_no_alert(isolated_env):
    """Boss Item 9: When LockTimeoutError is raised during alert cooldown checks,
    B1 must handle it cleanly: suppress alert, send 0 Telegram messages, and exit cleanly with logged reason."""
    from app.services.alert_cooldown import LockTimeoutError

    cand = [{"term": "test query", "raw_term": "test query", "approx_traffic": "10K+", "geos_present": ["US"]}]

    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=cand), \
         patch("app.services.trend_engine_b1.should_send_alert", side_effect=LockTimeoutError("Simulated lock timeout")), \
         patch("app.services.telegram_buttons.send_telegram_broadcast") as mock_tg:

        results = discover_and_produce_market_trend(market="EN", auto_produce=False, state_dir=isolated_env)
        assert results == []
        # Assert NO alert was broadcast
        mock_tg.assert_not_called()
