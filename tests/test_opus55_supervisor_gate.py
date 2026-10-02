"""tests/test_opus55_supervisor_gate.py — Tests for Opus 5.5 Anti-Token-Bloat Supervisory Engine."""

import json
from pathlib import Path
import pytest

from scripts.orchestrator.opus55_supervisor_gate import (
    estimate_tokens,
    build_anti_bloat_digest,
    call_opus55_supervisor,
    run_supervisory_gate,
    MAX_SUPERVISOR_INPUT_TOKENS,
)
from scripts.orchestrator.runner import build_parser, OrchestratorRunner


class TestOpus55SupervisorGate:
    """Verifies Token Budget Cap and Anti-Token-Bloat enforcement."""

    def test_estimate_tokens(self):
        text = "This is a simple test sentence for token estimation"
        toks = estimate_tokens(text)
        assert toks > 0
        assert toks == int(9 * 1.3)

    def test_build_anti_bloat_digest_under_limit(self):
        digest = build_anti_bloat_digest(
            task_id="EN_EP0260_macro_liquidity",
            task_objective="Implement modular orchestrator component",
            diff_summary="app/services/new_feature.py | 12 ++++",
            compact_diff="+ def new_feature():\n+     return True",
            qa_summary="Tests 25 passed",
            ocr_status="0 Critical / 0 High",
        )
        assert digest["task_id"] == "EN_EP0260_macro_liquidity"
        assert digest["estimated_tokens"] <= MAX_SUPERVISOR_INPUT_TOKENS
        assert "compact_diff" in digest

    def test_build_anti_bloat_digest_compaction_guard(self):
        # Generate giant diff simulating bloated logs to exceed 10,000 tokens
        huge_diff = "\n".join([f"+ line_{i} = complex_state_variable_assignment_data_{i}" for i in range(8000)])
        digest = build_anti_bloat_digest(
            task_id="EN_EP0260_macro_liquidity",
            task_objective="Stress test token compaction at 10,000 tokens ceiling",
            compact_diff=huge_diff,
        )
        # Verify it was capped to prevent context blowout
        assert digest["estimated_tokens"] <= MAX_SUPERVISOR_INPUT_TOKENS
        assert "Anti-Bloat Truncation Active" in digest["compact_diff"]

    def test_call_opus55_supervisor_dry_run(self):
        digest = {
            "task_id": "TEST_TASK",
            "task_objective": "Dry run verification",
            "estimated_tokens": 50,
        }
        res = call_opus55_supervisor(digest, dry_run=True)
        assert res["verdict"] == "APPROVED"
        assert res["score"] >= 9.0
        assert res["architectural_fit"] == "STRICT_COMPLIANT"

    def test_run_supervisory_gate_dry_run(self):
        gate_res = run_supervisory_gate(
            task_id="EN_EP0260_macro_liquidity",
            task_objective="Full dry-run gate check",
            dry_run=True,
        )
        assert "digest" in gate_res
        assert "supervision" in gate_res
        assert gate_res["supervision"]["verdict"] == "APPROVED"

    def test_cli_runner_supervise_mode(self, capsys):
        parser = build_parser()
        args = parser.parse_args([
            "--mode", "supervise",
            "--task-id", "EN_EP0260_macro_liquidity",
            "--dry-run",
            "--json-output",
        ])
        runner = OrchestratorRunner(args)
        ret = runner.run()
        assert ret == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["status"] == "success"
        assert payload["result"]["supervision"]["verdict"] == "APPROVED"

    def test_cli_runner_council_with_opus_supervision(self, capsys):
        parser = build_parser()
        args = parser.parse_args([
            "--mode", "council",
            "--task-id", "EN_EP0260_macro_liquidity",
            "--supervise-with-opus",
            "--dry-run",
            "--json-output",
        ])
        runner = OrchestratorRunner(args)
        ret = runner.run()
        assert ret == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["status"] == "success"
        matrix = payload["council_matrix"]
        assert matrix["council_quorum"] == "UNANIMOUS_5_OF_5"
        assert "supreme_supervisor_opus55" in matrix["votes"]
        assert matrix["votes"]["supreme_supervisor_opus55"]["vote"] == "APPROVED"
