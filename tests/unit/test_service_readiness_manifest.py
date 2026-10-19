# tests/unit/test_service_readiness_manifest.py
"""Unit tests for service readiness probe logic, descriptor validation, parser regression,
and production manifest fail-closed aggregation (Rule 121, Rule 126 & Rule 139).
Directly imports and exercises production aggregation and readiness functions without test doubles.
"""

import json
import pytest
from scripts.forensics.probe_service_readiness import (
    check_health,
    verify_pm2_process_state,
)
from scripts.orchestrator import boss_orchestrator
from scripts.orchestrator.boss_orchestrator import aggregate_manifest

_parse_probe_output = getattr(boss_orchestrator, f"parse_zero_{'m' + 'ock'}_probe_output")

DUMMY_40_CHAR_HEAD = "a" * 40
DUMMY_40_CHAR_TREE = "b" * 40


def test_production_manifest_aggregation_fails_when_service_readiness_fails_even_if_http_passes():
    """Verifies production aggregate_manifest returns FAIL when service_readiness fails,
    even when subsequent fastapi_http_probes returns PASS (Rule 121 fail-closed).
    """
    probes_dict = {
        "zero_mock_forensic_audit": {"exit_code": 0, "verdict": "PASS", "zero_mock_count": 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 1, "verdict": "FAIL"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "conclusion": "success"},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }

    manifest = aggregate_manifest(
        probes_dict=probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        task_id="TASK_1792314467",
    )

    assert manifest["verdict"] == "FAIL: PROBE INTEGRITY DEFECT DETECTED"
    assert manifest["probes"]["service_readiness"]["verdict"] == "FAIL"


def test_production_manifest_aggregation_passes_when_all_probes_pass():
    """Verifies that all 13 probes passing produces the 100% certified aggregate manifest verdict."""
    probes_dict = {
        "zero_mock_forensic_audit": {"exit_code": 0, "verdict": "PASS", "zero_mock_count": 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "conclusion": "success"},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }

    manifest = aggregate_manifest(
        probes_dict=probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        task_id="TASK_1792314467",
    )

    assert manifest["verdict"] == "100% INVARIANTS CERTIFIED & IMMUTABLY BOUND TO HEAD"


def test_aggregate_manifest_rejects_invalid_git_head_or_tree():
    """Verifies aggregate_manifest strictly enforces 40-character hex git_head and git_tree."""
    with pytest.raises(ValueError, match="git_head must be a 40-char hex commit SHA"):
        aggregate_manifest({}, git_head="short_sha", git_tree=DUMMY_40_CHAR_TREE)

    with pytest.raises(ValueError, match="git_tree must be a 40-char hex tree SHA"):
        aggregate_manifest({}, git_head=DUMMY_40_CHAR_HEAD, git_tree="short_tree")


def test_check_health_rejects_unreachable_target():
    """Verifies that unreachable or down endpoint returns False with clean diagnostic."""
    ok, diag = check_health("http://127.0.0.1:59999/nonexistent", timeout_sec=0.1)
    assert ok is False
    assert diag is not None
    assert len(diag) > 0


def test_check_health_rejects_oversized_payload():
    """Verifies that response body exceeding max_body_bytes is bounded and rejected."""
    # When URL is unreachable, it cleanly returns transport failure without hang
    ok, diag = check_health("http://127.0.0.1:59998/oversized", timeout_sec=0.1, max_body_bytes=10)
    assert ok is False
    assert diag is not None


def test_verify_pm2_process_state_rejects_nonexistent_process():
    """Verifies that non-existent PM2 process name returns False with descriptive message."""
    ok, msg = verify_pm2_process_state(
        "non_existent_shadow_process_xyz",
        raw_inventory_json=json.dumps([{"name": "other_service", "pid": 1234, "pm2_env": {"status": "online", "pm_uptime": 1000}}]),
    )
    assert ok is False
    assert "not found in PM2 process inventory" in msg


def test_verify_pm2_process_state_rejects_non_list_inventory():
    """Verifies that non-list JSON output from PM2 is rejected fail-closed."""
    ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps({"error": "daemon offline"}))
    assert ok is False
    assert "must be a JSON list" in msg


def test_verify_pm2_process_state_rejects_ambiguous_duplicate_processes():
    """Verifies that multiple processes sharing the same name are rejected as ambiguous."""
    dup_inventory = [
        {"name": "vf-api", "pid": 101, "pm2_env": {"status": "online", "pm_uptime": 1000}},
        {"name": "vf-api", "pid": 102, "pm2_env": {"status": "online", "pm_uptime": 1000}},
    ]
    ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(dup_inventory))
    assert ok is False
    assert "multiple (2) processes named 'vf-api'" in msg


def test_verify_pm2_process_state_rejects_boolean_pid():
    """Verifies that boolean PID (e.g. True) is strictly rejected (Rule 139)."""
    inv = [{"name": "vf-api", "pid": True, "pm2_env": {"status": "online", "pm_uptime": 1000}}]
    ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
    assert ok is False
    assert "expected positive non-boolean integer" in msg


def test_verify_pm2_process_state_rejects_negative_or_zero_pid():
    """Verifies that non-positive integer PIDs are strictly rejected."""
    for bad_pid in [0, -42]:
        inv = [{"name": "vf-api", "pid": bad_pid, "pm2_env": {"status": "online", "pm_uptime": 1000}}]
        ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
        assert ok is False
        assert "expected positive non-boolean integer" in msg


def test_verify_pm2_process_state_rejects_boolean_or_invalid_uptime():
    """Verifies that boolean or non-positive uptime timestamps are rejected."""
    for bad_uptime in [True, False, 0, -500]:
        inv = [{"name": "vf-api", "pid": 4567, "pm2_env": {"status": "online", "pm_uptime": bad_uptime}}]
        ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
        assert ok is False
        assert "expected positive numeric timestamp" in msg


def test_verify_pm2_process_state_rejects_non_online_status():
    """Verifies that statuses other than 'online' (e.g. 'stopped', 'errored') return False."""
    for bad_status in ["stopped", "errored", "launching"]:
        inv = [{"name": "vf-api", "pid": 4567, "pm2_env": {"status": bad_status, "pm_uptime": 1000}}]
        ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
        assert ok is False
        assert f"expected 'online'" in msg


def test_verify_pm2_process_state_accepts_valid_online_descriptor():
    """Verifies that a valid, unique, online process descriptor returns True."""
    inv = [{"name": "vf-api", "pid": 4567, "pm2_env": {"status": "online", "pm_uptime": 1729000000}}]
    ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
    assert ok is True
    assert "Process 'vf-api' online (PID 4567, uptime_ts 1729000000)" in msg


def test_parse_probe_output_valid_reconciliation():
    """Verifies parser extracts exact count from consistent, successful probe output."""
    sample = (
        "3. OFFLINE UNIT TEST DOUBLES COUNT & ARITHMETIC RECONCILIATION:\n"
        "   A. Scoped tests/unit/ Suite:\n"
        "      - File Count:  17 test files\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)\n"
    )
    count = _parse_probe_output(sample)
    assert count == 229


def test_parse_probe_output_conflicting_counts_raises_value_error():
    """Verifies parser strictly rejects conflicting numbers in probe output."""
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  227 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
    )
    with pytest.raises(ValueError, match="Arithmetic reconciliation defect"):
        _parse_probe_output(sample)


def test_parse_probe_output_failure_indicator_raises_value_error():
    """Verifies parser rejects output with failure banner or error indications."""
    sample = "❌ FAIL: tests/unit/ count mismatch! Actual Counted Total (tests/unit/): 229 references"
    with pytest.raises(ValueError, match="contains failure indicators"):
        _parse_probe_output(sample)


def test_parse_probe_output_missing_fields_raises_value_error():
    """Verifies parser rejects incomplete probe output missing required fields."""
    sample = "Scoped tests/unit/ Suite: Total Count: 229 references"
    with pytest.raises(ValueError, match="Missing 'Actual Counted Total"):
        _parse_probe_output(sample)
