#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_critic_gate_fail_closed.py
Unit tests verifying that the B1.1 Critic Gate in trend_engine_b1.py operates in a strict
fail-closed posture: any exception, non-PASS verdict, or low score (< 7.5) rejects the candidate
WITHOUT invoking downstream token-consuming functions (run_b15, reason_topic_niche, generate_5_arc_story).
"""

from unittest.mock import patch
import pytest

from app.services.trend_engine_b1 import discover_and_produce_market_trend


@pytest.fixture
def dummy_candidate_context():
    """Returns candidate mock data sufficient to reach the Critic Gate stage."""
    return [
        {
            "term": "test semiconductor shortage crisis",
            "primary_geo": "US",
            "geos_present": ["US"],
            "approx_traffic": "100K+",
            "source": "gtrends_rss",
            "sources_present": ["gtrends_rss"],
            "news_title": "Semiconductor shortage hits auto industry"
        }
    ]


@patch("app.services.trend_engine_b1.acquire_in_progress", return_value="dummy_token")
@patch("app.services.trend_engine_b1.fetch_live_trending_terms")
@patch("app.services.trend_engine_b1.forensic_pre_filter", return_value=(True, "pass"))
@patch("app.services.trend_engine_b1.check_evidence_catalyst_gate", return_value=(True, "pass"))
@patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]})
@patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "facts"})
@patch("app.services.trend_engine_b1.assess_keyword_video_viability")
@patch("app.services.trend_engine_b1.run_b15")
@patch("app.services.trend_engine_b1.reason_topic_niche")
def test_critic_gate_exception_fails_closed(
    mock_reason, mock_b15, mock_viability, mock_facts, mock_recon,
    mock_catalyst, mock_prefilter, mock_fetch_terms, mock_acquire, dummy_candidate_context
):
    """When audit_candidate_trend_alignment raises an exception, the candidate must be rejected
    fail-closed without calling run_b15 or reason_topic_niche.
    """
    mock_fetch_terms.return_value = dummy_candidate_context
    mock_viability.return_value = {
        "viability_score": 9.0,
        "is_viable": True,
        "specific_viral_angle": "The hidden chokehold on global microchips",
        "visual_feasibility_score": 8.5,
        "conflict_depth_score": 8.5
    }

    with patch(
        "app.services.adversarial_critic_b1.audit_candidate_trend_alignment",
        side_effect=RuntimeError("HHTech API network failure")
    ):
        results = discover_and_produce_market_trend(
            market="US",
            max_candidates=1,
            auto_commit=False,
            strict_critic_gate=True
        )

    # Must produce 0 candidates since Critic Gate failed closed
    assert len(results) == 0
    mock_b15.assert_not_called()
    mock_reason.assert_not_called()


@patch("app.services.trend_engine_b1.acquire_in_progress", return_value="dummy_token")
@patch("app.services.trend_engine_b1.fetch_live_trending_terms")
@patch("app.services.trend_engine_b1.forensic_pre_filter", return_value=(True, "pass"))
@patch("app.services.trend_engine_b1.check_evidence_catalyst_gate", return_value=(True, "pass"))
@patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]})
@patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "facts"})
@patch("app.services.trend_engine_b1.assess_keyword_video_viability")
@patch("app.services.trend_engine_b1.run_b15")
@patch("app.services.trend_engine_b1.reason_topic_niche")
def test_critic_gate_revise_or_fail_verdict_rejects(
    mock_reason, mock_b15, mock_viability, mock_facts, mock_recon,
    mock_catalyst, mock_prefilter, mock_fetch_terms, mock_acquire, dummy_candidate_context
):
    """When audit_candidate_trend_alignment returns REVISE or FAIL, candidate is rejected."""
    mock_fetch_terms.return_value = dummy_candidate_context
    mock_viability.return_value = {
        "viability_score": 9.0,
        "is_viable": True,
        "specific_viral_angle": "The hidden chokehold on global microchips",
        "visual_feasibility_score": 8.5,
        "conflict_depth_score": 8.5
    }

    # Test verdict="REVISE"
    with patch(
        "app.services.adversarial_critic_b1.audit_candidate_trend_alignment",
        return_value={"verdict": "REVISE", "audit_score": 6.0, "veto_reason": "Angle lacks high-stakes hook"}
    ):
        results_revise = discover_and_produce_market_trend(
            market="US",
            max_candidates=1,
            auto_commit=False,
            strict_critic_gate=True
        )

    assert len(results_revise) == 0
    mock_b15.assert_not_called()
    mock_reason.assert_not_called()

    # Test verdict="FAIL"
    with patch(
        "app.services.adversarial_critic_b1.audit_candidate_trend_alignment",
        return_value={"verdict": "FAIL", "audit_score": 4.0, "veto_reason": "Bait and switch topic"}
    ):
        results_fail = discover_and_produce_market_trend(
            market="US",
            max_candidates=1,
            auto_commit=False,
            strict_critic_gate=True
        )

    assert len(results_fail) == 0
    mock_b15.assert_not_called()
    mock_reason.assert_not_called()


@patch("app.services.trend_engine_b1.acquire_in_progress", return_value="dummy_token")
@patch("app.services.trend_engine_b1.fetch_live_trending_terms")
@patch("app.services.trend_engine_b1.forensic_pre_filter", return_value=(True, "pass"))
@patch("app.services.trend_engine_b1.check_evidence_catalyst_gate", return_value=(True, "pass"))
@patch("app.services.trend_engine_b1.perform_direct_platform_recon", return_value={"rising_queries": [], "viral_videos": [], "news_catalysts": [{"title": "News"}]})
@patch("app.services.trend_engine_b1.fetch_ground_truth_factsheet", return_value={"extract": "facts"})
@patch("app.services.trend_engine_b1.assess_keyword_video_viability")
@patch("app.services.trend_engine_b1.run_b15")
@patch("app.services.trend_engine_b1.reason_topic_niche")
def test_critic_gate_low_score_rejects(
    mock_reason, mock_b15, mock_viability, mock_facts, mock_recon,
    mock_catalyst, mock_prefilter, mock_fetch_terms, mock_acquire, dummy_candidate_context
):
    """Even if verdict is PASS, if score < 7.5, candidate is rejected."""
    mock_fetch_terms.return_value = dummy_candidate_context
    mock_viability.return_value = {
        "viability_score": 9.0,
        "is_viable": True,
        "specific_viral_angle": "The hidden chokehold on global microchips",
        "visual_feasibility_score": 8.5,
        "conflict_depth_score": 8.5
    }

    with patch(
        "app.services.adversarial_critic_b1.audit_candidate_trend_alignment",
        return_value={"verdict": "PASS", "audit_score": 7.0, "veto_reason": "Score below 7.5 threshold"}
    ):
        results = discover_and_produce_market_trend(
            market="US",
            max_candidates=1,
            auto_commit=False,
            strict_critic_gate=True
        )

    assert len(results) == 0
    mock_b15.assert_not_called()
    mock_reason.assert_not_called()
