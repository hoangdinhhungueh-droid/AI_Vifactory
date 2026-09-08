import json
from unittest.mock import MagicMock, patch
import pytest

import app.services.model_gateway
import app.services.story_fact_auditor_b2
from app.services.dual_model_convergence import run_dual_model_convergence
from app.services.trend_engine_b1 import forensic_pre_filter, get_next_prefiltered_candidate


class TestForensicPreFilter:
    """Test Level-0 Forensic Pre-Filter Gate."""

    def test_filter_kr_investigative_topic(self):
        cand = {
            "term": "홈플러스 망한 이유",
            "news_title": "홈플러스 위기 사태 분석",
            "source": "gtrends_rss"
        }
        passed, reason = forensic_pre_filter(cand, "KR")
        assert passed
        assert "망한" in reason or "위기" in reason

    def test_filter_kr_showbiz_rejection(self):
        cand = {
            "term": "아이돌 컴백 무대",
            "news_title": "새 앨범 발표 쇼케이스",
            "source": "gtrends_rss"
        }
        passed, reason = forensic_pre_filter(cand, "KR")
        assert not passed
        assert "0 LLM tokens burned" in reason

    def test_filter_en_investigative_topic(self):
        cand = {
            "term": "FTX bankruptcy collapse",
            "news_title": "Sam Bankman-Fried fraud investigation",
            "source": "gtrends_rss"
        }
        passed, reason = forensic_pre_filter(cand, "EN")
        assert passed


class TestDualModelConvergence:
    """Test Dual-Model Convergence Protocol."""

    SAMPLE_5ACT_SCRIPT = """=== ACT I ===
The corporate treasury emptied in 48 hours. A $200M cash deficit shocked retail markets.

=== ACT II ===
Public statements claimed stability, but supplier invoices piled up uncollected.

=== ACT III ===
Internal audits uncovered 19 store sale-and-leaseback arrangements.
The paper trail vanished.

=== ACT IV ===
The smoking gun was a clause permitting private equity debt transfer to operations.

=== ACT V ===
Retail giants today stand as cautionary tales of asset-stripping disguised as restructuring."""

    @patch("app.services.story_gate.score_story")
    @patch("app.services.model_gateway.get_global_gateway")
    @patch("app.services.story_fact_auditor_b2.audit_story_facts_and_causality")
    def test_convergence_pass(self, mock_fact_audit, mock_gateway_fn, mock_score_story):
        mock_score_story.return_value = {"score": 12, "max_score": 12, "verdict": "PASS"}

        # Mock Opus 5 Scribe
        mock_gw = MagicMock()
        # Make it return 1800+ words script
        mock_gw.call_llm.return_value = (self.SAMPLE_5ACT_SCRIPT + "\n") * 35
        mock_gateway_fn.return_value = mock_gw

        # Mock Fact Auditor
        mock_fact_audit.return_value = {
            "verdict": "PASS",
            "audit_score": 8.5,
            "claims_verified": 5,
            "discrepancies": []
        }

        claims = [{"claim": "200M deficit", "verified_metric": "200M", "source_title": "Reuters", "date": "2026-08-01"}]
        res = run_dual_model_convergence(
            story_text="Original bad draft",
            grounding_claims=claims,
            audit_critique="Failed attribution",
            topic_meta={"task_id": "KR_EP0004_test", "topic": "Homeplus"},
            market="KR"
        )

        assert res["converged"] is True
        assert res["status"] == "PASS"
        assert res["fact_score"] >= 7.5

    @patch("app.services.model_gateway.get_global_gateway")
    @patch("app.services.story_fact_auditor_b2.audit_story_facts_and_causality")
    def test_convergence_fail(self, mock_fact_audit, mock_gateway_fn):
        mock_gw = MagicMock()
        mock_gw.call_llm.return_value = self.SAMPLE_5ACT_SCRIPT
        mock_gateway_fn.return_value = mock_gw

        mock_fact_audit.return_value = {
            "verdict": "FAIL",
            "audit_score": 6.0,
            "veto_reason": "Continued hallucination of profit margins"
        }

        claims = [{"claim": "200M deficit", "verified_metric": "200M", "source_title": "Reuters", "date": "2026-08-01"}]
        res = run_dual_model_convergence(
            story_text="Original draft",
            grounding_claims=claims,
            audit_critique="Failed attribution",
            topic_meta={"task_id": "KR_EP0004_test", "topic": "Homeplus"},
            market="KR"
        )

        assert res["converged"] is False
        assert res["status"] == "NON_CONVERGENCE"
        assert "veto_reason" in res or "reason" in res
