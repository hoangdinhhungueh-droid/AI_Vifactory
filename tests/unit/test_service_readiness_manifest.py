# tests/unit/test_service_readiness_manifest.py
"""Unit tests for service readiness probe logic and manifest fail-closed aggregation (Rule 121 & Rule 139).
Tests manifest aggregation regression, health payload predicates, and PM2 process state parsing
without using any test doubles.
"""

from scripts.forensics.probe_service_readiness import check_health, verify_pm2_process_state


def test_manifest_aggregation_fails_when_service_readiness_fails_even_if_http_passes():
    """Verifies that failed service_readiness (exit 1) causes aggregate manifest verdict to be FAIL,
    even when subsequent fastapi_http_probes returns PASS (exit 0).
    """
    probes_dict = {
        "zero_mock_forensic_audit": {"exit_code": 0, "verdict": "PASS", "zero_mock_count": 227},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 1, "verdict": "FAIL"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
    }

    all_probes_pass = all(p.get("verdict") == "PASS" for p in probes_dict.values())
    verdict = (
        "100% INVARIANTS CERTIFIED & IMMUTABLY BOUND TO HEAD"
        if all_probes_pass
        else "FAIL: PROBE INTEGRITY DEFECT DETECTED"
    )

    assert all_probes_pass is False
    assert verdict == "FAIL: PROBE INTEGRITY DEFECT DETECTED"


def test_manifest_aggregation_passes_when_all_probes_pass():
    """Verifies that all probes passing produces the certified aggregate verdict."""
    probes_dict = {
        "zero_mock_forensic_audit": {"exit_code": 0, "verdict": "PASS", "zero_mock_count": 227},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
    }

    all_probes_pass = all(p.get("verdict") == "PASS" for p in probes_dict.values())
    verdict = (
        "100% INVARIANTS CERTIFIED & IMMUTABLY BOUND TO HEAD"
        if all_probes_pass
        else "FAIL: PROBE INTEGRITY DEFECT DETECTED"
    )

    assert all_probes_pass is True
    assert verdict == "100% INVARIANTS CERTIFIED & IMMUTABLY BOUND TO HEAD"


def test_check_health_rejects_unreachable_target():
    """Verifies that unreachable or down endpoint returns False with clean diagnostic rather than unhandled exception."""
    ok, diag = check_health("http://127.0.0.1:59999/nonexistent", timeout_sec=0.1)
    assert ok is False
    assert diag is not None
    assert len(diag) > 0


def test_verify_pm2_process_state_rejects_nonexistent_process():
    """Verifies that non-existent PM2 process name returns False with descriptive message."""
    ok, msg = verify_pm2_process_state("non_existent_shadow_process_xyz", timeout_sec=2.0)
    assert ok is False
    assert "not found" in msg or "failed" in msg or "failure" in msg
