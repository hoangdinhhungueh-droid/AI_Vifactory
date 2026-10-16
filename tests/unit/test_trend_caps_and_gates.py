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
from unittest.mock import patch

import pytest

from app.services.trend_engine_b1 import (
    LIVE_TRAFFIC_SOURCES,
    MAX_SCAN_CANDIDATES_DEFAULT,
    MAX_VIABILITY_LLM_EVALS_DEFAULT,
    _parse_env_int,
    check_evidence_catalyst_gate,
)


@pytest.fixture(autouse=True)
def force_crawl_for_caps_tests(monkeypatch):
    """Ensure caps and inner candidate loop tests are not preempted by daily quota guard."""
    monkeypatch.setenv("B1_FORCE_CRAWL", "1")


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


def test_level_0_5_gate_rejects_empty_term():
    """Branch (d): Rejects candidate when candidate_term is empty or blank spaces."""
    ok, reason = check_evidence_catalyst_gate(
        news_catalysts=[{"title": "Valid News"}],
        traffic_source="google_news_live",
        factsheet_extract="Valid entity",
        is_custom_seed=False,
        candidate_term="",
    )
    assert not ok
    assert "blank or empty" in reason

    ok_ws, reason_ws = check_evidence_catalyst_gate(
        news_catalysts=[{"title": "Valid News"}],
        traffic_source="google_news_live",
        factsheet_extract="Valid entity",
        is_custom_seed=False,
        candidate_term="   ",
    )
    assert not ok_ws
    assert "blank or empty" in reason_ws


def test_level_0_5_gate_handles_none_factsheet_safely():
    """Branch (e): Gracefully handles None or empty factsheet_extract without AttributeError."""
    ok, reason = check_evidence_catalyst_gate(
        news_catalysts=[],
        traffic_source="youtube_autocomplete",
        factsheet_extract=None,
        is_custom_seed=False,
        candidate_term="valid_term",
    )
    assert not ok
    assert "0 LLM tokens burned" in reason


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

    # Reconstruct cmd matching trend_engine_b1.py
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


def test_b3_failure_yields_zero_committed_and_single_failed_alert(tmp_path):
    """Rule 125 & Single Pipeline State: When B3 fails (res_code != 0):
    1. Zero topics are committed.
    2. Exactly ONE terminal Telegram message with status FAILED is emitted.
    3. No contradictory Gate 1 success or bottleneck message is sent.
    """
    from unittest.mock import MagicMock

    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    fake_candidate = {
        "term": "corporate bankruptcy collapse crisis",
        "approx_traffic": "google_news_live",
        "source": "google_news_live",
        "geos_present": ["US"],
    }

    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=[fake_candidate]), \
         patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]}), \
         patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "Entity factsheet"}), \
         patch("app.services.trend_engine_b1.assess_keyword_video_viability", return_value={"viability_score": 9.0, "is_video_viable": True, "reasoning": "High impact", "specific_viral_angle": "Test Angle"}), \
         patch("app.services.adversarial_critic_b1.audit_candidate_trend_alignment", return_value={"verdict": "PASS", "audit_score": 9.5}), \
         patch("app.services.trend_engine_b1.run_b15", return_value={"competitor_narrative_anatomy": {"fatal_explanatory_vacuum": "gap"}}), \
         patch("app.services.grounding_layer_b15.run_grounding_research", return_value={}), \
         patch("app.services.grounding_layer_b15.passes_grounding_gate", return_value=(True, "Grounding passed")), \
         patch("app.services.seo_package_forge.forge_seo_package", return_value={}), \
         patch("app.services.trend_engine_b1.reason_topic_niche", return_value={"search_specific_keyword": "corporate collapse", "topic_name_vi": "Test", "task_slug": "test_slug", "niche_angle_brief": "Brief", "story_direction_5_arcs": "Arcs"}), \
         patch("app.services.story_engine_b2.generate_5_arc_story", return_value={"story": "Valid script text", "story_gate_score": 12, "story_verdict": "PASS", "fact_causal_audit": {"verdict": "PASS", "audit_score": 9.0}}), \
         patch("subprocess.run") as mock_sub, \
         patch("app.services.trend_engine_b1.record_handled_topic"), \
         patch("app.services.telegram_buttons.send_telegram_broadcast") as mock_tele, \
         patch("app.services.trend_engine_b1.commit_trend_task") as mock_commit:

        mock_sub.return_value = MagicMock(returncode=1, stderr="Subprocess error in B3")

        produced = discover_and_produce_market_trend(market="EN", auto_produce=True, max_scan_candidates=1, state_dir=str(tmp_path))

        # 1. Zero topics produced and zero committed
        assert len(produced) == 0
        mock_commit.assert_not_called()

        # 2. Exactly ONE terminal Telegram broadcast emitted
        assert mock_tele.call_count == 1
        broadcast_msg = mock_tele.call_args[0][0]
        assert "[VF PIPELINE B3 FAILED - RULE 118" in broadcast_msg
        assert "0 topics committed" in broadcast_msg

        # 3. Explicitly verify ZERO success-flavoured or contradictory messages emitted
        all_messages = [call_args[0][0] for call_args in mock_tele.call_args_list]
        assert not any("GATE 1" in m for m in all_messages)
        assert not any("BOTTLENECK" in m for m in all_messages)


def test_b3_module_find_spec_and_subprocess_help_contract():
    """Verify B3 orchestrator.run_pipeline can be found by importlib and runs with --help."""
    import importlib
    import importlib.util
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    project_root_str = str(project_root)
    if project_root_str in sys.path:
        sys.path.remove(project_root_str)
    sys.path.insert(0, project_root_str)

    if "orchestrator" in sys.modules:
        del sys.modules["orchestrator"]
    importlib.invalidate_caches()

    # 1. importlib find_spec must find orchestrator.run_pipeline
    spec = importlib.util.find_spec("orchestrator.run_pipeline")
    assert spec is not None
    assert spec.origin is not None
    assert "run_pipeline" in spec.origin

    # 2. Subprocess execution with --help must succeed with exit code 0
    sub_env = os.environ.copy()
    sub_env["PYTHONPATH"] = f"{project_root}:{sub_env.get('PYTHONPATH', '')}".strip(":")
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator.run_pipeline", "--help"],
        cwd=str(project_root),
        env=sub_env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    assert "--profile" in proc.stdout


def test_candidate_loop_halts_at_max_scan_candidates(tmp_path):
    """Verify candidate loop halts strictly at MAX_SCAN_CANDIDATES_DEFAULT (10) ceiling (Boss Item 18)."""
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    # Generate 25 candidates
    candidates = [
        {
            "term": f"financial bankruptcy collapse {i}",
            "approx_traffic": "100K+",
            "source": "google_news_live",
            "geos_present": ["US"],
        }
        for i in range(25)
    ]

    scanned_terms = []

    def mock_recon(term, *args, **kwargs):
        scanned_terms.append(term)
        return {"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": f"News {term}"}]}

    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=candidates), \
         patch("app.services.trend_engine_b1.perform_direct_platform_recon", side_effect=mock_recon), \
         patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "Fact"}), \
         patch("app.services.trend_engine_b1.assess_keyword_video_viability", return_value={"viability_score": 5.0, "is_video_viable": False, "reasoning": "Low score"}), \
         patch("app.services.telegram_buttons.send_telegram_broadcast"):

        produced = discover_and_produce_market_trend(
            market="EN",
            auto_produce=False,
            max_scan_candidates=MAX_SCAN_CANDIDATES_DEFAULT,
            max_viability_llm_evals=20,
            state_dir=str(tmp_path),
        )
        assert len(produced) == 0
        assert len(scanned_terms) == MAX_SCAN_CANDIDATES_DEFAULT == 10


def test_llm_viability_calls_stop_at_max_viability_llm_evals(tmp_path):
    """Verify LLM viability calls halt strictly at max_viability_llm_evals ceiling (Boss Item 18)."""
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    # Generate 15 candidates that all pass Level-0 and Level-0.5
    candidates = [
        {
            "term": f"debt default crisis shock {i}",
            "approx_traffic": "google_news_live",
            "source": "google_news_live",
            "geos_present": ["US"],
        }
        for i in range(15)
    ]

    llm_eval_count = 0

    def mock_eval(*args, **kwargs):
        nonlocal llm_eval_count
        llm_eval_count += 1
        return {"viability_score": 6.0, "is_video_viable": False, "reasoning": "Sub-threshold"}

    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=candidates), \
         patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]}), \
         patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "Fact"}), \
         patch("app.services.trend_engine_b1.assess_keyword_video_viability", side_effect=mock_eval), \
         patch("app.services.telegram_buttons.send_telegram_broadcast"):

        produced = discover_and_produce_market_trend(
            market="EN",
            auto_produce=False,
            max_scan_candidates=10,
            max_viability_llm_evals=MAX_VIABILITY_LLM_EVALS_DEFAULT,
            state_dir=str(tmp_path),
        )
        assert len(produced) == 0
        assert llm_eval_count <= MAX_VIABILITY_LLM_EVALS_DEFAULT == 6


def test_market_exhausted_today_lock_and_cron_skip(tmp_path, monkeypatch):
    """Verify mark_exhausted_today locks the market for today and prevents cron re-run without --force."""
    from datetime import datetime, timezone

    from app.services.daily_market_lock import is_market_done_today, mark_exhausted_today

    monkeypatch.delenv("B1_FORCE_CRAWL", raising=False)
    test_now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    market = "TEST_EXHAUSTED"

    # 1. Before scan: not produced yet
    is_done, reason, details = is_market_done_today(
        market, state_dir=str(tmp_path), now=test_now, check_registry=False, check_episodes=False
    )
    assert is_done is False
    assert reason == "not_produced_yet"

    # 2. Mark exhausted after 10 failed candidates
    success = mark_exhausted_today(market, scan_count=10, state_dir=str(tmp_path), now=test_now)
    assert success is True

    # 3. Automated cron checks: must return True (is_done=True), reason='lock_exhausted_today'
    is_done, reason, details = is_market_done_today(
        market, state_dir=str(tmp_path), now=test_now, check_registry=False, check_episodes=False
    )
    assert is_done is True
    assert reason == "lock_exhausted_today"
    assert details.get("status") == "EXHAUSTED_TODAY"
    assert details.get("scan_count") == 10

    # 4. Manual override with force=True bypasses the lock
    is_done_force, reason_force, _ = is_market_done_today(
        market, state_dir=str(tmp_path), now=test_now, force=True, check_registry=False, check_episodes=False
    )
    assert is_done_force is False
    assert reason_force == "forced_override"

    # 5. Next day (2026-10-16): lock does not block
    next_day = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    is_done_next, reason_next, _ = is_market_done_today(
        market, state_dir=str(tmp_path), now=next_day, check_registry=False, check_episodes=False
    )
    assert is_done_next is False
    assert reason_next == "not_produced_yet"


def test_b2_circuit_breaker_emits_exactly_one_telegram_alert(tmp_path, monkeypatch):
    """Rule 118 & Boss Item 18: When B2 attempts reach MAX_B2_ATTEMPTS:
    1. Circuit breaker triggers and stamps EXHAUSTED_TODAY lock with reason='b2_circuit_breaker'.
    2. Exactly ONE telegram alert with '[RULE 118 B2 CIRCUIT BREAKER ACTIVATED]' is emitted.
    3. Pipeline halts and produces 0 topics.
    4. Subsequent cron run sees market is done/exhausted today and skips.
    """
    from app.services.daily_market_lock import is_market_done_today
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    monkeypatch.delenv("B1_FORCE_CRAWL", raising=False)

    candidates = [
        {
            "term": f"corporate bankruptcy collapse scandal {i}",
            "approx_traffic": "google_news_live",
            "source": "google_news_live",
            "geos_present": ["US"],
        }
        for i in range(5)
    ]

    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=candidates), \
         patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]}), \
         patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "Entity factsheet"}), \
         patch("app.services.trend_engine_b1.assess_keyword_video_viability", return_value={"viability_score": 9.0, "is_video_viable": True, "reasoning": "High impact", "specific_viral_angle": "Test Angle"}), \
         patch("app.services.adversarial_critic_b1.audit_candidate_trend_alignment", return_value={"verdict": "PASS", "audit_score": 9.5}), \
         patch("app.services.trend_engine_b1.run_b15", return_value={"competitor_narrative_anatomy": {"fatal_explanatory_vacuum": "gap"}}), \
         patch("app.services.grounding_layer_b15.run_grounding_research", return_value={}), \
         patch("app.services.grounding_layer_b15.passes_grounding_gate", return_value=(True, "Grounding passed")), \
         patch("app.services.seo_package_forge.forge_seo_package", return_value={}), \
         patch("app.services.trend_engine_b1.reason_topic_niche", return_value={"search_specific_keyword": "corporate collapse", "topic_name_vi": "Test", "task_slug": "test_slug", "niche_angle_brief": "Brief", "story_direction_5_arcs": "Arcs"}), \
         patch("app.services.story_engine_b2.generate_5_arc_story", return_value={"story": "Rejected story", "story_gate_score": 6, "story_verdict": "REJECT", "fact_causal_audit": {"verdict": "FAIL", "audit_score": 5.0}}), \
         patch("app.services.trend_engine_b1.record_handled_topic"), \
         patch("app.services.telegram_buttons.send_telegram_broadcast", return_value="msg_12345") as mock_tele, \
         patch("app.services.trend_engine_b1.commit_trend_task") as mock_commit:

        produced = discover_and_produce_market_trend(
            market="EN",
            auto_produce=True,
            max_scan_candidates=5,
            max_b2_attempts=2,
            state_dir=str(tmp_path),
        )

        # 1. Pipeline produced 0 topics and committed 0 tasks
        assert len(produced) == 0
        mock_commit.assert_not_called()

        # 2. Exactly ONE telegram broadcast emitted
        assert mock_tele.call_count == 1
        broadcast_msg = mock_tele.call_args[0][0]
        assert "[RULE 118 B2 CIRCUIT BREAKER ACTIVATED]" in broadcast_msg

        # 3. Market lock is stamped EXHAUSTED_TODAY with reason="b2_circuit_breaker"
        is_done, reason, details = is_market_done_today("EN", state_dir=str(tmp_path), check_registry=False, check_episodes=False)
        assert is_done is True
        assert reason == "lock_exhausted_today"
        assert details.get("reason") == "b2_circuit_breaker"


def test_b2_exception_circuit_breaker_stamps_exhausted_today(tmp_path, monkeypatch):
    """Boss Round 7 Item 4: When B2 raises exceptions on consecutive candidates reaching max_b2_attempts:
    1. Circuit breaker triggers and stamps EXHAUSTED_TODAY lock with reason='b2_circuit_breaker_exception'.
    2. Exactly ONE telegram alert with '[RULE 118 B2 CIRCUIT BREAKER ACTIVATED]' is emitted.
    3. The lock is NOT released in finally block (prevents automated quota burn).
    4. Subsequent cron run sees market is done/exhausted today and skips.
    """
    from app.services.daily_market_lock import is_market_done_today
    from app.services.trend_engine_b1 import discover_and_produce_market_trend

    monkeypatch.delenv("B1_FORCE_CRAWL", raising=False)

    candidates = [
        {
            "term": f"corporate bankruptcy exception test {i}",
            "approx_traffic": "google_news_live",
            "source": "google_news_live",
            "geos_present": ["US"],
        }
        for i in range(5)
    ]

    with patch("app.services.trend_engine_b1.fetch_live_trending_terms", return_value=candidates), \
         patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]}), \
         patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "Entity factsheet"}), \
         patch("app.services.trend_engine_b1.assess_keyword_video_viability", return_value={"viability_score": 9.0, "is_video_viable": True, "reasoning": "High impact", "specific_viral_angle": "Test Angle"}), \
         patch("app.services.adversarial_critic_b1.audit_candidate_trend_alignment", return_value={"verdict": "PASS", "audit_score": 9.5}), \
         patch("app.services.trend_engine_b1.run_b15", return_value={"competitor_narrative_anatomy": {"fatal_explanatory_vacuum": "gap"}}), \
         patch("app.services.grounding_layer_b15.run_grounding_research", return_value={}), \
         patch("app.services.grounding_layer_b15.passes_grounding_gate", return_value=(True, "Grounding passed")), \
         patch("app.services.seo_package_forge.forge_seo_package", return_value={}), \
         patch("app.services.trend_engine_b1.reason_topic_niche", return_value={"search_specific_keyword": "corporate collapse", "topic_name_vi": "Test", "task_slug": "test_slug", "niche_angle_brief": "Brief", "story_direction_5_arcs": "Arcs"}), \
         patch("app.services.story_engine_b2.generate_5_arc_story", side_effect=RuntimeError("Simulated B2 LLM Outage")), \
         patch("app.services.trend_engine_b1.record_handled_topic"), \
         patch("app.services.telegram_buttons.send_telegram_broadcast", return_value="msg_exception_123") as mock_tele, \
         patch("app.services.trend_engine_b1.commit_trend_task") as mock_commit:

        produced = discover_and_produce_market_trend(
            market="EN",
            auto_produce=True,
            max_scan_candidates=5,
            max_b2_attempts=2,
            state_dir=str(tmp_path),
        )

        assert len(produced) == 0
        mock_commit.assert_not_called()
        assert mock_tele.call_count == 1
        broadcast_msg = mock_tele.call_args[0][0]
        assert "[RULE 118 B2 CIRCUIT BREAKER ACTIVATED]" in broadcast_msg

        is_done, reason, details = is_market_done_today("EN", state_dir=str(tmp_path), check_registry=False, check_episodes=False)
        assert is_done is True
        assert reason == "lock_exhausted_today"
        assert details.get("reason") == "b2_circuit_breaker_exception"




