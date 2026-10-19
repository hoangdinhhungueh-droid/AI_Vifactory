#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_critic_gate_fail_closed.py
Unit tests verifying that the B1.1 Critic Gate in trend_engine_b1.py operates in a strict
fail-closed posture: any exception, non-PASS verdict, or low score (< 7.5) rejects the candidate
WITHOUT invoking downstream token-consuming functions (run_b15, reason_topic_niche, generate_5_arc_story).
"""

import json
from unittest.mock import patch, MagicMock
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


@pytest.fixture(autouse=True)
def hermetic_alert_guard():
    with patch("app.services.trend_engine_b1._send_guarded_alert", return_value=True), \
         patch("app.services.telegram_buttons.send_telegram_broadcast", return_value=123):
        yield


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
            market="EN",
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
            market="EN",
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
            market="EN",
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
            market="EN",
            max_candidates=1,
            auto_commit=False,
            strict_critic_gate=True
        )

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
def test_b1_angle_self_repair_success(
    mock_reason, mock_b15, mock_viability, mock_facts, mock_recon,
    mock_catalyst, mock_prefilter, mock_fetch_terms, mock_acquire, dummy_candidate_context
):
    """When initial critic score is near passing (7.1), 1-shot repair generates improved angle and passes."""
    mock_fetch_terms.return_value = dummy_candidate_context
    mock_viability.return_value = {
        "viability_score": 9.0,
        "is_video_viable": True,
        "specific_viral_angle": "France Debt Crisis vs Pension Squeeze",
        "visual_feasibility_score": 8.5,
        "conflict_depth_score": 8.5
    }
    mock_reason.return_value = {
        "search_specific_keyword": "France Debt Crisis",
        "task_slug": "france-debt-crisis",
        "niche_angle_brief": "Investigative documentary",
        "story_direction_5_arcs": []
    }
    mock_b15.return_value = {"competitor_narrative_anatomy": {"fatal_explanatory_vacuum": "gap"}}

    critic_side_effects = [
        # Call 1: Original angle rejected with 7.1
        {"verdict": "FAIL", "audit_score": 7.1, "veto_reason": "Lacks imminent deadline catalyst"},
        # Call 2: Repaired angle approved with 8.6
        {"verdict": "PASS", "audit_score": 8.6, "veto_reason": None}
    ]

    with patch(
        "app.services.adversarial_critic_b1.audit_candidate_trend_alignment",
        side_effect=critic_side_effects
    ), patch(
        "app.services.adversarial_critic_b1.repair_candidate_angle",
        return_value="France's Make-or-Break Debt Showdown: Imminent Default Risk"
    ), patch(
        "app.services.grounding_layer_b15.run_grounding_research",
        return_value={"verified_claims": [1, 2, 3], "claims": list(range(8)), "dated_claims": [1, 2, 3]}
    ), patch(
        "app.services.grounding_layer_b15.passes_grounding_gate",
        return_value=(True, "Grounding passed")
    ), patch(
        "app.services.seo_package_forge.forge_seo_package",
        return_value={"title_a": "France Debt Showdown", "specific_viral_angle": "France's Make-or-Break Debt Showdown: Imminent Default Risk"}
    ), patch(
        "app.services.story_engine_b2.generate_5_arc_story",
        return_value={"story": "Valid script", "story_gate_score": 12, "story_verdict": "PASS", "fact_causal_audit": {"verdict": "PASS", "audit_score": 9.0}}
    ), patch(
        "app.services.trend_engine_b1.send_pure_telegram_gate1_notification"
    ), patch(
        "app.services.trend_engine_b1.record_handled_topic"
    ), patch(
        "app.services.daily_market_lock.mark_completed",
        return_value=True
    ), patch("app.services.trend_engine_b1.commit_trend_task", return_value="EN_EP9999_france_debt"):

        results = discover_and_produce_market_trend(
            market="EN",
            max_candidates=1,
            auto_commit=False,
            strict_critic_gate=True
        )

    assert len(results) == 1
    assert results[0]["specific_viral_angle"] == "France's Make-or-Break Debt Showdown: Imminent Default Risk"
    mock_b15.assert_called_once()
    mock_reason.assert_called_once()


def test_repair_candidate_angle_unit():
    """Unit test for repair_candidate_angle gateway call and parsing."""
    from app.services.adversarial_critic_b1 import repair_candidate_angle

    mock_llm_response = json.dumps({
        "repaired_angle": "France Make or Break: How Default Risk Impacts Europe",
        "repair_rationale": "Directly centered on imminent deadline"
    })

    with patch("app.services.model_gateway.get_global_gateway") as mock_gw:
        mock_gateway_inst = MagicMock()
        mock_gateway_inst.call_llm.return_value = mock_llm_response
        mock_gw.return_value = mock_gateway_inst

        repaired = repair_candidate_angle(
            candidate_term="France debt",
            original_angle="Old angle",
            veto_reason="Lacks deadline",
            market="EN"
        )

    assert repaired == "France Make or Break: How Default Risk Impacts Europe"

