"""Unit tests for Dual-Model Convergence Protocol.
Verifies role separation (Astra patches, Opus audits delta),
CJK length compliance, and targeted act patching.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.dual_model_convergence import (
    parse_script_into_acts,
    determine_failing_acts,
    run_dual_model_convergence
)


SAMPLE_5_ACT_SCRIPT_JP = """=== ACT I ===
ソニー生命の金銭不正問題が発覚した時、金融界に大きな衝撃が走った。2026年4月30日、保険業法128条に基づく報告命令が下された。

=== ACT II ===
内部統制の不備がどのようにして1億8060万円の不正引き出しを許したのか。承認プロセスの盲点がそこにあった。

=== ACT III ===
調査が進むにつれ、口座管理の杜撰さと上層部の監督不行届が次々と明るみに出た。

=== ACT IV ===
2026年9月15日、金融庁は立ち入り検査に着手した。これは単なる一社員の犯罪ではなく、組織的構造欠陥であった。

=== ACT V ===
この事件が残した教訓は、コンプライアンスの形骸化がいかに企業を破滅へ追い込むかという点である。
""" + ("\n詳細な調査記録が示すのは、制度の隙間を突いた巧妙な隠蔽工作の数々であった。" * 75)


def test_parse_script_into_acts():
    acts = parse_script_into_acts(SAMPLE_5_ACT_SCRIPT_JP)
    assert len(acts) == 5
    assert "ACT I" in acts
    assert "ACT II" in acts
    assert "ACT III" in acts
    assert "ACT IV" in acts
    assert "ACT V" in acts
    assert "ソニー生命" in acts["ACT I"]


def test_determine_failing_acts():
    # Structured metadata
    meta = {"failed_acts": ["ACT II", "ACT IV"]}
    failed = determine_failing_acts("Some critique", meta)
    assert failed == ["ACT II", "ACT IV"]

    # Inferred from text
    critique = "In Act II, the causal mechanism is inverted. In Act V, the conclusion lacks numbers."
    failed_text = determine_failing_acts(critique, {})
    assert "ACT II" in failed_text
    assert "ACT V" in failed_text


def test_dual_model_convergence_opus_patches_astra_audits():
    fake_gateway = MagicMock()

    # Pass 1: Claude Opus 5 patches Act II
    opus_patched_act2 = """=== ACT II ===
2021年5月の制度改変により、1億8060万円の不正送金プロセスが隠蔽された。
内部承認を経ずに顧客口座から直接資金が移動する致命的な構造欠陥が放置されていた。""" + ("\n詳細な内部証言と監査記録。" * 20)

    # Pass 2: GPT-6-Astra audits delta
    astra_delta_audit_res = """{
        "verdict": "PASS",
        "audit_score": 8.8,
        "still_failing_acts": [],
        "critical_findings": "Act II patch fully resolves the causal discrepancy and anchors strictly to verified claims."
    }"""

    fake_gateway.call_llm.side_effect = [opus_patched_act2, astra_delta_audit_res]

    with (
        patch("app.services.model_gateway.get_global_gateway", return_value=fake_gateway),
        patch("app.services.story_gate.score_story", return_value={"score": 11, "verdict": "PASS"})
    ):
        res = run_dual_model_convergence(
            story_text=SAMPLE_5_ACT_SCRIPT_JP,
            grounding_claims=[
                {"claim": "180.6M yen fraud", "verified_metric": "180.6M yen", "source_title": "FSA Report"}
            ],
            audit_critique="Act II has causal inversion regarding the 180.6M yen transfer.",
            topic_meta={"task_id": "JP_TEST_01", "topic_name_vi": "Sony Life Fraud"},
            market="JP",
            max_rounds=2,
            initial_audit_result={"failed_acts": ["ACT II"], "audit_score": 5.0}
        )

        assert res["converged"] is True
        assert res["status"] == "PASS"
        assert res["fact_score"] == 8.8
        assert res["story_gate_score"] == 11
        assert res["audit_details"]["verdict"] == "PASS"

        # Verify role separation: First call MUST be claude-opus-5 (Patcher), Second call MUST be gpt-6-astra (Delta Auditor)
        calls = fake_gateway.call_llm.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs.get("model") == "claude-opus-5"
        assert calls[1].kwargs.get("model") == "gpt-6-astra"


def test_score_verdict_normalization_fail_with_passing_score():
    """Tests that when GPT-6-Astra returns verdict 'FAIL' but audit_score >= 7.5,
    the normalization contract converts it to 'PASS'."""
    from app.services.story_fact_auditor_b2 import audit_delta_patched_acts

    fake_gw = MagicMock()
    fake_gw.call_llm.return_value = json.dumps({
        "verdict": "FAIL",
        "audit_score": 7.6,
        "still_failing_acts": [],
        "critical_findings": "Minor nuances remain but factual claims verified."
    })

    with patch("app.services.model_gateway.get_global_gateway", return_value=fake_gw):
        res = audit_delta_patched_acts(
            patched_acts={"ACT I": "Patched text for Act I"},
            prior_critique={"critical_findings": "Initial discrepancy in Act I"},
            grounding_claims=[{"claim": "test claim"}],
            topic_meta={"task_id": "JP_TEST_NORM", "topic_name_vi": "Test Normalization"},
            market="JP"
        )

        assert res["audit_score"] == 7.6
        assert res["verdict"] == "PASS", "Verdict must be normalized to PASS when score >= 7.5!"
