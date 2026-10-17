"""tests/test_opus55_supervisor_gate.py — Tests for Opus 5.5 Anti-Token-Bloat Supervisory Engine."""

import json

from scripts.orchestrator.opus55_supervisor_gate import (
    MAX_SUPERVISOR_INPUT_TOKENS,
    build_anti_bloat_digest,
    call_opus55_supervisor,
    condense_qa_telemetry,
    estimate_tokens,
    run_supervisory_gate,
)
from scripts.orchestrator.runner import OrchestratorRunner, build_parser


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

    def test_condense_qa_telemetry_strips_verbose_passed(self):
        verbose_lines = [
            "============================= test session starts =============================",
            "collected 100 items",
        ]
        for i in range(100):
            verbose_lines.append(f"tests/unit/test_subsystem.py::test_case_{i} PASSED [ {i}%]")
        verbose_lines.append("FAILED tests/unit/test_critical.py::test_fail - AssertionError: check failed")
        verbose_lines.append("======================== 99 passed, 1 failed in 4.20s =========================")

        raw_telemetry = "\n".join(verbose_lines)
        condensed = condense_qa_telemetry(raw_telemetry)

        # Verified: Individual 100 PASSED lines are collapsed into a high-density summary
        assert "100 individual unit/integration tests PASSED - line-by-line verbosity condensed" in condensed
        # Verified: Failure is 100% PRESERVED with zero loss
        assert "FAILED tests/unit/test_critical.py::test_fail - AssertionError: check failed" in condensed
        assert "99 passed, 1 failed in 4.20s" in condensed
        assert len(condensed) < len(raw_telemetry) / 4

    def test_build_anti_bloat_digest_enforces_12k_ceiling_with_massive_payload(self):
        # Giant test outputs and giant diff
        giant_qa = "\n".join([f"tests/test_{i}.py::test_{i} PASSED [ {i%100}%]" for i in range(2000)])
        giant_qa += "\n=== 2000 passed in 30.0s ==="
        giant_diff = "\n".join([f"+ def function_{i}():\n+     return {i} * 2" for i in range(1500)])

        digest = build_anti_bloat_digest(
            task_id="MASSIVE_SCALE_TASK",
            task_objective="Verify 12k ceiling under extreme payload stress",
            compact_diff=giant_diff,
            qa_summary=giant_qa,
        )

        assert digest["estimated_tokens"] <= MAX_SUPERVISOR_INPUT_TOKENS
        assert digest["estimated_tokens"] <= 12000
        assert "2000 passed in 30.0s" in digest["qa_summary"]
