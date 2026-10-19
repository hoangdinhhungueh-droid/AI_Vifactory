# tests/unit/test_service_readiness_manifest.py
"""Unit tests for service readiness probe logic, descriptor validation, parser regression,
and production manifest fail-closed aggregation (Rule 121, Rule 126 & Rule 139).
Directly imports and exercises production aggregation and readiness functions without test doubles.
"""

import http.server
import json
import threading
import time

import pytest

from scripts.forensics.probe_service_readiness import (
    check_health,
    run_service_readiness_probe,
    verify_pm2_process_state,
)
from scripts.orchestrator import boss_orchestrator
from scripts.orchestrator.boss_orchestrator import (
    MANDATORY_MANIFEST_PROBES,
    aggregate_manifest,
)

_parse_probe_output = boss_orchestrator.parse_zero_mock_probe_output
PROBE_KEY_ZERO_MOCK = "zero_mock_forensic_audit"
PROBE_COUNT_KEY_ZERO_MOCK = PROBE_KEY_ZERO_MOCK.replace("_forensic_audit", "_count")
PROBE_DIGEST_KEY_ZERO_MOCK = PROBE_KEY_ZERO_MOCK.replace("_forensic_audit", "_probe_sha256")

DUMMY_40_CHAR_HEAD = "a" * 40
DUMMY_40_CHAR_TREE = "b" * 40

MANDATORY_DIGESTS_FIXTURE = {
    "head_commit_sha": DUMMY_40_CHAR_HEAD,
    "tree_sha": DUMMY_40_CHAR_TREE,
    "linux_junit_xml_sha256": "c" * 64,
    "windows_junit_xml_sha256": "d" * 64,
    PROBE_DIGEST_KEY_ZERO_MOCK: "e" * 64,
    "service_readiness_probe_sha256": "f" * 64,
    "fastapi_http_probes_sha256": "1" * 64,
    "ast_scanner_sha256": "2" * 64,
    "secret_scan_scope_sha256": "3" * 64,
}


def test_production_manifest_aggregation_fails_when_service_readiness_fails_even_if_http_passes():
    """Verifies production aggregate_manifest returns FAIL when service_readiness fails,
    even when subsequent fastapi_http_probes returns PASS (Rule 121 fail-closed).
    """
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 1, "verdict": "FAIL"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }

    manifest = aggregate_manifest(
        probes_dict=probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        task_id="TASK_1792314467",
        artifact_digests=MANDATORY_DIGESTS_FIXTURE,
    )

    assert manifest["verdict"] == "FAIL: PROBE INTEGRITY DEFECT DETECTED"
    assert manifest["probes"]["service_readiness"]["verdict"] == "FAIL"


def test_production_manifest_aggregation_passes_when_all_probes_pass():
    """Verifies that all 13 probes passing produces the 100% certified aggregate manifest verdict."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }

    manifest = aggregate_manifest(
        probes_dict=probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        task_id="TASK_1792314467",
        artifact_digests=MANDATORY_DIGESTS_FIXTURE,
    )

    assert manifest["verdict"] == "100% INVARIANTS CERTIFIED & IMMUTABLY BOUND TO HEAD"


def test_aggregate_manifest_rejects_empty_or_incomplete_probes():
    """Verifies aggregate_manifest strictly rejects empty probe dicts or missing mandatory probes."""
    with pytest.raises(ValueError, match="probes_dict must be a non-empty dictionary"):
        aggregate_manifest({}, git_head=DUMMY_40_CHAR_HEAD, git_tree=DUMMY_40_CHAR_TREE)

    incomplete_probes = {
        "service_readiness": {"exit_code": 0, "verdict": "PASS"}
    }
    with pytest.raises(ValueError, match="Manifest missing mandatory verification probe"):
        aggregate_manifest(
            incomplete_probes,
            git_head=DUMMY_40_CHAR_HEAD,
            git_tree=DUMMY_40_CHAR_TREE,
            artifact_digests=MANDATORY_DIGESTS_FIXTURE,
        )


def test_aggregate_manifest_rejects_contradictory_verdict_and_exit_code():
    """Verifies aggregate_manifest strictly rejects contradictory status (verdict PASS with exit_code != 0)."""
    bad_probes = {
        p: {"exit_code": 0, "verdict": "PASS"} for p in MANDATORY_MANIFEST_PROBES
    }
    bad_probes["linux_focused_pytest"]["xml_sha256"] = "c" * 64
    bad_probes["windows_focused_pytest"]["xml_sha256"] = "d" * 64
    bad_probes["service_readiness"] = {"exit_code": 1, "verdict": "PASS"}
    with pytest.raises(ValueError, match="Contradictory probe state for 'service_readiness'"):
        aggregate_manifest(
            bad_probes,
            git_head=DUMMY_40_CHAR_HEAD,
            git_tree=DUMMY_40_CHAR_TREE,
            artifact_digests=MANDATORY_DIGESTS_FIXTURE,
        )


def test_aggregate_manifest_rejects_invalid_git_head_or_tree():
    """Verifies aggregate_manifest strictly enforces 40-character hexadecimal git_head and git_tree."""
    valid_probes = {p: {"exit_code": 0, "verdict": "PASS"} for p in MANDATORY_MANIFEST_PROBES}

    with pytest.raises(ValueError, match="git_head must be a 40-character lowercase hexadecimal SHA"):
        aggregate_manifest(valid_probes, git_head="short_sha", git_tree=DUMMY_40_CHAR_TREE, artifact_digests=MANDATORY_DIGESTS_FIXTURE)

    with pytest.raises(ValueError, match="git_head must be a 40-character lowercase hexadecimal SHA"):
        aggregate_manifest(valid_probes, git_head="g" * 40, git_tree=DUMMY_40_CHAR_TREE, artifact_digests=MANDATORY_DIGESTS_FIXTURE)

    with pytest.raises(ValueError, match="git_tree must be a 40-character lowercase hexadecimal SHA"):
        aggregate_manifest(valid_probes, git_head=DUMMY_40_CHAR_HEAD, git_tree="z" * 40, artifact_digests=MANDATORY_DIGESTS_FIXTURE)


def test_aggregate_manifest_rejects_missing_or_invalid_artifact_digests():
    """Verifies aggregate_manifest strictly rejects missing or non-hex artifact digest bindings."""
    valid_probes = {p: {"exit_code": 0, "verdict": "PASS"} for p in MANDATORY_MANIFEST_PROBES}
    with pytest.raises(ValueError, match="Manifest missing mandatory artifact digest"):
        aggregate_manifest(valid_probes, git_head=DUMMY_40_CHAR_HEAD, git_tree=DUMMY_40_CHAR_TREE, artifact_digests={})

    bad_digests = dict(MANDATORY_DIGESTS_FIXTURE)
    bad_digests["linux_junit_xml_sha256"] = "not_a_hex_digest"
    with pytest.raises(ValueError, match="must be a 64-char hex SHA256 digest"):
        aggregate_manifest(valid_probes, git_head=DUMMY_40_CHAR_HEAD, git_tree=DUMMY_40_CHAR_TREE, artifact_digests=bad_digests)


def test_check_health_rejects_unreachable_target():
    """Verifies that unreachable or down endpoint returns False with clean diagnostic."""
    ok, diag = check_health("http://127.0.0.1:59999/nonexistent", timeout_sec=0.1)
    assert ok is False
    assert diag is not None
    assert len(diag) > 0


def test_check_health_rejects_oversized_payload_server_backed():
    """Verifies that response body exceeding max_body_bytes is bounded and rejected via real local HTTP server."""
    class OversizedHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "close")
            self.end_headers()
            # Send payload of 70,000 bytes, exceeding 65,536 bound
            self.wfile.write(b'{"status": "ok", "padding": "' + b"A" * 70000 + b'"}')

        def log_message(self, format, *args):
            if hasattr(self.server, "access_logs"):
                self.server.access_logs.append(format % args)

    server = http.server.HTTPServer(("127.0.0.1", 0), OversizedHandler)
    server.access_logs = []
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/health"
        ok, diag = check_health(url, timeout_sec=2.0, max_body_bytes=65536)
        assert ok is False
        assert "exceeded maximum bound of 65536 bytes" in diag
    finally:
        server.shutdown()
        server.server_close()


def test_check_health_rejects_malformed_json_server_backed():
    """Verifies that non-JSON response from server is rejected fail-closed."""
    class MalformedHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b"<html><body>502 Bad Gateway</body></html>")

        def log_message(self, format, *args):
            if hasattr(self.server, "access_logs"):
                self.server.access_logs.append(format % args)

    server = http.server.HTTPServer(("127.0.0.1", 0), MalformedHandler)
    server.access_logs = []
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/health"
        ok, diag = check_health(url, timeout_sec=2.0)
        assert ok is False
        assert "JSONDecodeError" in diag
    finally:
        server.shutdown()
        server.server_close()


def test_check_health_rejects_unexpected_status_server_backed():
    """Verifies that JSON response with status != 'ok' is rejected."""
    class DegradedHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b'{"status": "degraded", "active_workers": 0}')

        def log_message(self, format, *args):
            if hasattr(self.server, "access_logs"):
                self.server.access_logs.append(format % args)

    server = http.server.HTTPServer(("127.0.0.1", 0), DegradedHandler)
    server.access_logs = []
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/health"
        ok, diag = check_health(url, timeout_sec=2.0)
        assert ok is False
        assert "Unexpected health payload" in diag
    finally:
        server.shutdown()
        server.server_close()


def test_check_health_rejects_trickled_body_deadline_exhaustion_server_backed():
    """Verifies that a server trickling bytes exceeding the read duration timeout is rejected and execution duration is strictly bounded."""
    class TricklingHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b'{"part": 1}')
            self.wfile.flush()
            time.sleep(0.35)
            try:
                for _ in range(10):
                    self.wfile.write(b', "part": 2}')
                    self.wfile.flush()
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as write_err:
                self.server.write_errors.append(type(write_err).__name__)

        def log_message(self, format, *args):
            if hasattr(self.server, "access_logs"):
                self.server.access_logs.append(format % args)

    server = http.server.HTTPServer(("127.0.0.1", 0), TricklingHandler)
    server.access_logs = []
    server.write_errors = []
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/health"
        t0 = time.monotonic()
        ok, diag = check_health(url, timeout_sec=0.15)
        elapsed = time.monotonic() - t0
        assert ok is False
        assert 0.14 <= elapsed <= 1.5, f"Elapsed time {elapsed}s not bounded to ~0.15s"
        assert diag is not None
        assert "exceeded timeout" in diag or "timed out" in diag
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not server.write_errors:
            time.sleep(0.05)
        assert len(server.write_errors) > 0, "Server did not detect client socket disconnect"
        for err in server.write_errors:
            assert err in ("BrokenPipeError", "ConnectionResetError", "ConnectionAbortedError"), f"Unexpected server write error: {err}"
    finally:
        server.shutdown()
        server.server_close()


def test_check_health_continuous_sub_timeout_trickle_deadline_exhaustion_server_backed():
    """Verifies that a server continuously trickling sub-timeout chunks is bounded and rejected by the monotonic deadline."""
    class ChunkedTrickleHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.protocol_version = "HTTP/1.1"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                for _ in range(15):
                    self.wfile.write(b"1\r\n \r\n")
                    self.wfile.flush()
                    time.sleep(0.03)
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as write_err:
                if hasattr(self.server, "write_errors"):
                    self.server.write_errors.append(type(write_err).__name__)

        def log_message(self, format, *args):
            if hasattr(self.server, "access_logs"):
                self.server.access_logs.append(format % args)

    server = http.server.HTTPServer(("127.0.0.1", 0), ChunkedTrickleHandler)
    server.access_logs = []
    server.write_errors = []
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/health"
        t0 = time.monotonic()
        ok, diag = check_health(url, timeout_sec=0.12)
        elapsed = time.monotonic() - t0
        assert ok is False
        assert 0.11 <= elapsed <= 0.35, f"Elapsed time {elapsed}s not bounded to [0.11, 0.35]"
        assert diag is not None
        assert "exceeded timeout" in diag or "timed out" in diag
    finally:
        server.shutdown()
        server.server_close()


def test_check_health_single_blocking_read_deadline_exhaustion_server_backed():
    """Verifies that a server which stalls indefinitely on a single body chunk is bounded and rejected by the monotonic deadline."""
    class SingleBlockingReadHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "100")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b'{"status": ')
            self.wfile.flush()
            # Stalls for 2.0s without sending remaining body
            time.sleep(2.0)
            try:
                self.wfile.write(b'"ok"}')
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as write_err:
                if hasattr(self.server, "write_errors"):
                    self.server.write_errors.append(type(write_err).__name__)

        def log_message(self, format, *args):
            if hasattr(self.server, "access_logs"):
                self.server.access_logs.append(format % args)

    server = http.server.HTTPServer(("127.0.0.1", 0), SingleBlockingReadHandler)
    server.access_logs = []
    server.write_errors = []
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/health"
        t0 = time.monotonic()
        ok, diag = check_health(url, timeout_sec=0.15)
        elapsed = time.monotonic() - t0
        assert ok is False
        assert 0.14 <= elapsed <= 0.40, f"Elapsed time {elapsed}s not bounded to ~0.15s"
        assert diag is not None
        assert "exceeded timeout" in diag or "timed out" in diag or "TimeoutError" in diag
    finally:
        server.shutdown()
        server.server_close()


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
        assert "expected finite positive numeric timestamp" in msg


def test_verify_pm2_process_state_rejects_non_finite_uptime():
    """Verifies that non-finite floats (NaN, +inf, -inf) are strictly rejected."""
    for non_finite in [float("nan"), float("inf"), float("-inf")]:
        inv = [{"name": "vf-api", "pid": 4567, "pm2_env": {"status": "online", "pm_uptime": non_finite}}]
        ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
        assert ok is False
        assert "expected finite positive numeric timestamp" in msg


def test_verify_pm2_process_state_rejects_non_online_status():
    """Verifies that statuses other than 'online' (e.g. 'stopped', 'errored') return False."""
    for bad_status in ["stopped", "errored", "launching"]:
        inv = [{"name": "vf-api", "pid": 4567, "pm2_env": {"status": bad_status, "pm_uptime": 1000}}]
        ok, msg = verify_pm2_process_state("vf-api", raw_inventory_json=json.dumps(inv))
        assert ok is False
        assert "expected 'online'" in msg


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


def test_parse_probe_output_duplicate_identical_summaries_raises_value_error():
    """Verifies parser strictly rejects duplicate identical summary lines (Rule 121 fail-closed)."""
    sample = (
        "3. OFFLINE UNIT TEST DOUBLES COUNT & ARITHMETIC RECONCILIATION:\n"
        "   A. Scoped tests/unit/ Suite:\n"
        "      - File Count:  17 test files\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)\n"
    )
    with pytest.raises(ValueError, match="duplicate or missing summary records are strictly rejected"):
        _parse_probe_output(sample)


def test_parse_probe_output_missing_terminal_marker_raises_value_error():
    """Verifies parser strictly rejects truncated output missing the terminal success record."""
    sample = (
        "3. OFFLINE UNIT TEST DOUBLES COUNT & ARITHMETIC RECONCILIATION:\n"
        "   A. Scoped tests/unit/ Suite:\n"
        "      - File Count:  17 test files\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
    )
    with pytest.raises(ValueError, match="Missing explicit successful terminal record"):
        _parse_probe_output(sample)


def test_parse_probe_output_conflicting_counts_raises_value_error():
    """Verifies parser strictly rejects conflicting numbers in probe output."""
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  227 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)\n"
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
    sample = (
        "Scoped tests/unit/ Suite: Total Count: 229 references\n"
        "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)\n"
    )
    with pytest.raises(ValueError, match="Expected exactly 1 'Actual Counted Total"):
        _parse_probe_output(sample)


def test_aggregate_manifest_accepts_junit_negative_test_matrix_dual_exit_codes():
    """Verifies aggregate_manifest deduces exit_code 0 when linux_exit_code and windows_exit_code are 0."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"linux_exit_code": 0, "windows_exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    manifest = aggregate_manifest(
        probes_dict=probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        task_id="TASK_1792314467",
        artifact_digests=MANDATORY_DIGESTS_FIXTURE,
    )
    assert manifest["verdict"] == "100% INVARIANTS CERTIFIED & IMMUTABLY BOUND TO HEAD"
    assert manifest["probes"]["junit_negative_test_matrix"]["exit_code"] == 0


def test_parse_probe_output_duplicate_terminal_markers_raises_value_error():
    """Verifies parser strictly rejects probe output containing duplicate terminal markers."""
    tm = "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)"
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        f"{tm}\n"
        f"{tm}\n"
    )
    with pytest.raises(ValueError, match="Expected exactly 1 terminal marker"):
        _parse_probe_output(sample)


def test_parse_probe_output_embedded_terminal_marker_raises_value_error():
    """Verifies parser strictly rejects an embedded terminal marker not on its own standalone line."""
    tm = "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)"
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        f"Corrupted invalid prefix line containing {tm} embedded\n"
    )
    with pytest.raises(ValueError, match="Missing explicit successful terminal record"):
        _parse_probe_output(sample)


def test_parse_probe_output_trailing_invalid_content_raises_value_error():
    """Verifies parser strictly rejects trailing invalid or truncated content following the terminal marker."""
    tm = "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)"
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        f"{tm}\n"
        "Unexpected trailing text after terminal marker!\n"
    )
    with pytest.raises(ValueError, match="Trailing invalid or truncated content"):
        _parse_probe_output(sample)


def test_parse_probe_output_malformed_extra_summary_raises_value_error():
    """Verifies parser strictly rejects extra summary records."""
    tm = "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)"
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        f"{tm}\n"
    )
    with pytest.raises(ValueError, match="Expected exactly 1 'Actual Counted Total'"):
        _parse_probe_output(sample)


def test_parse_probe_output_malformed_syntax_summary_raises_value_error():
    """Verifies parser strictly rejects non-numeric or corrupt syntax in summary record."""
    tm = "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)"
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         corrupted_non_numeric\n"
        f"{tm}\n"
    )
    with pytest.raises(ValueError, match="Expected exactly 1 'Actual Counted Total \\(tests/unit/\\):' record"):
        _parse_probe_output(sample)


def test_aggregate_manifest_rejects_head_or_tree_digest_mismatch():
    """Verifies aggregate_manifest strictly enforces provenance equality between git head and digests."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    bad_digests = dict(MANDATORY_DIGESTS_FIXTURE)
    bad_digests["head_commit_sha"] = "0" * 40
    with pytest.raises(ValueError, match="Provenance mismatch: artifact_digests\\['head_commit_sha'\\]"):
        aggregate_manifest(
            probes_dict,
            git_head=DUMMY_40_CHAR_HEAD,
            git_tree=DUMMY_40_CHAR_TREE,
            artifact_digests=bad_digests,
        )


def test_aggregate_manifest_rejects_tree_digest_mismatch():
    """Verifies aggregate_manifest strictly enforces provenance equality between git tree and digests."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    bad_digests = dict(MANDATORY_DIGESTS_FIXTURE)
    bad_digests["tree_sha"] = "0" * 40
    with pytest.raises(ValueError, match="Provenance mismatch: artifact_digests\\['tree_sha'\\]"):
        aggregate_manifest(
            probes_dict,
            git_head=DUMMY_40_CHAR_HEAD,
            git_tree=DUMMY_40_CHAR_TREE,
            artifact_digests=bad_digests,
        )


def test_aggregate_manifest_rejects_missing_or_empty_xml_sha256():
    """Verifies aggregate_manifest strictly rejects empty or missing per-probe xml_sha256."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": ""},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    with pytest.raises(ValueError, match="missing xml_sha256"):
        aggregate_manifest(
            probes_dict,
            git_head=DUMMY_40_CHAR_HEAD,
            git_tree=DUMMY_40_CHAR_TREE,
            artifact_digests=MANDATORY_DIGESTS_FIXTURE,
        )


def test_aggregate_manifest_rejects_boolean_exit_code():
    """Verifies aggregate_manifest rejects boolean False as an exit code (requires strict int 0)."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": False, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": DUMMY_40_CHAR_HEAD},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    with pytest.raises(ValueError, match="Contradictory probe state"):
        aggregate_manifest(
            probes_dict,
            git_head=DUMMY_40_CHAR_HEAD,
            git_tree=DUMMY_40_CHAR_TREE,
            artifact_digests=MANDATORY_DIGESTS_FIXTURE,
        )


def test_run_service_readiness_probe_fails_on_restart_failure():
    """Verifies run_service_readiness_probe returns exit code 1 when restart fails."""
    code = run_service_readiness_probe(
        restart_fn=lambda rem: (1, "pm2 restart error"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        budget_sec=5.0,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_inspection_failure():
    """Verifies run_service_readiness_probe returns exit code 1 when PM2 inspection fails."""
    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (False, "Process crashed"),
        status_fn=lambda to: (0, "online"),
        budget_sec=5.0,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_status_failure():
    """Verifies run_service_readiness_probe returns exit code 1 when final status fails."""
    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (1, "pm2 status error"),
        budget_sec=5.0,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_budget_exhaustion():
    """Verifies run_service_readiness_probe returns exit code 1 when overall budget is exhausted."""
    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (False, "timeout waiting for server"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        budget_sec=0.1,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_post_status_budget_overrun():
    """Verifies run_service_readiness_probe returns exit code 1 when final phase overruns the overall budget."""
    def slow_status(rem):
        time.sleep(0.12)
        return (0, "online")

    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=slow_status,
        budget_sec=0.1,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_restart_phase_overrun():
    """Verifies run_service_readiness_probe returns exit code 1 when restart phase overruns the overall budget."""
    def slow_restart(rem):
        time.sleep(0.12)
        return (0, "ok")

    code = run_service_readiness_probe(
        restart_fn=slow_restart,
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        budget_sec=0.1,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_poll_phase_overrun():
    """Verifies run_service_readiness_probe returns exit code 1 when poll phase overruns the overall budget."""
    def slow_poll(to):
        time.sleep(0.12)
        return (True, "status=ok")

    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=slow_poll,
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        budget_sec=0.1,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_inspect_phase_overrun():
    """Verifies run_service_readiness_probe returns exit code 1 when PM2 inspect phase overruns the overall budget."""
    def slow_inspect(to):
        time.sleep(0.12)
        return (True, "online")

    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=slow_inspect,
        status_fn=lambda to: (0, "online"),
        budget_sec=0.1,
    )
    assert code == 1


def test_aggregate_manifest_rejects_missing_ci_head():
    """Verifies aggregate_manifest strictly marks FAIL when github_actions_ci omits head_sha."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed"},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    manifest = aggregate_manifest(
        probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        artifact_digests=MANDATORY_DIGESTS_FIXTURE,
    )
    assert manifest["verdict"] == "FAIL: PROBE INTEGRITY DEFECT DETECTED"


def test_aggregate_manifest_rejects_mismatched_ci_head():
    """Verifies aggregate_manifest strictly marks FAIL when github_actions_ci head_sha does not match git_head."""
    probes_dict = {
        PROBE_KEY_ZERO_MOCK: {"exit_code": 0, "verdict": "PASS", PROBE_COUNT_KEY_ZERO_MOCK: 229},
        "linux_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "c" * 64},
        "windows_focused_pytest": {"exit_code": 0, "verdict": "PASS", "test_count": 52, "xml_sha256": "d" * 64},
        "junit_negative_test_matrix": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_linux": {"exit_code": 0, "verdict": "PASS"},
        "ruff_linting_windows": {"exit_code": 0, "verdict": "PASS"},
        "service_readiness": {"exit_code": 0, "verdict": "PASS"},
        "fastapi_http_probes": {"exit_code": 0, "verdict": "PASS"},
        "lock_liveness_probe": {"exit_code": 0, "verdict": "PASS"},
        "ghost_hunter_scan": {"exit_code": 0, "verdict": "PASS"},
        "ast_anti_symptom_scan": {"exit_code": 0, "verdict": "PASS"},
        "github_actions_ci": {"exit_code": 0, "verdict": "PASS", "run_id": 12345, "conclusion": "success", "status": "completed", "head_sha": "0" * 40},
        "whole_packet_secret_scan": {"exit_code": 0, "verdict": "PASS", "findings_count": 0},
    }
    manifest = aggregate_manifest(
        probes_dict,
        git_head=DUMMY_40_CHAR_HEAD,
        git_tree=DUMMY_40_CHAR_TREE,
        artifact_digests=MANDATORY_DIGESTS_FIXTURE,
    )
    assert manifest["verdict"] == "FAIL: PROBE INTEGRITY DEFECT DETECTED"


def test_parse_probe_output_embedded_marker_with_valid_terminal_raises_value_error():
    """Verifies parser strictly rejects probe output having both embedded marker and valid terminal marker."""
    tm = "✅ ZERO-MOCK COMPLIANCE & RECONCILIATION PROBE PASSED (Exit code 0)"
    sample = (
        "   A. Scoped tests/unit/ Suite:\n"
        "      - Total Count: 229 references\n"
        "       * Calculated Reconciled Total (tests/unit/):  229 references\n"
        "       * Actual Counted Total (tests/unit/):         229 references\n"
        f"Corrupted embedded marker line: {tm}\n"
        f"{tm}\n"
    )
    with pytest.raises(ValueError, match="Expected exactly 1 terminal marker"):
        _parse_probe_output(sample)


def test_parse_probe_output_truncated_at_sections_raises_value_error():
    """Verifies parser strictly rejects truncated outputs at various pipeline section boundaries."""
    s1 = "1. SCANNING CORE TEST SUITES:\n"
    with pytest.raises(ValueError):
        _parse_probe_output(s1)

    s2 = (
        "1. SCANNING CORE TEST SUITES:\n"
        "   - Core Matches Count: 0\n"
        "2. SCANNING PRODUCTION PACKAGES:\n"
    )
    with pytest.raises(ValueError):
        _parse_probe_output(s2)

    s3 = (
        "3. OFFLINE TEST RECONCILIATION:\n"
        "   - Total Count: 229 references\n"
    )
    with pytest.raises(ValueError):
        _parse_probe_output(s3)


def test_run_service_readiness_probe_fails_on_cleanup_phase_overrun():
    """Verifies run_service_readiness_probe returns exit code 1 when cleanup phase overruns the overall budget."""
    def slow_cleanup(to):
        time.sleep(0.12)
        return (0, "clean")

    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        cleanup_fn=slow_cleanup,
        budget_sec=0.1,
    )
    assert code == 1


def test_run_service_readiness_probe_fails_on_final_completion_overrun():
    """Verifies run_service_readiness_probe returns exit code 1 when execution exhausts budget right before completion verification."""
    def slow_status_just_under(to):
        time.sleep(0.11)
        return (0, "online")

    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=slow_status_just_under,
        budget_sec=0.1,
    )
    assert code == 1


def test_run_service_readiness_probe_forcibly_bounds_blocking_cleanup():
    """Verifies that a genuinely blocking cleanup callable cannot overrun the monotonic deadline unbounded,
    and that the probe caller regains control and fails closed within the bounded budget.
    """
    def genuinely_blocking_cleanup(to):
        time.sleep(5.0)
        return (0, "clean")

    start_mono = time.monotonic()
    code = run_service_readiness_probe(
        restart_fn=lambda rem: (0, "ok"),
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        cleanup_fn=genuinely_blocking_cleanup,
        budget_sec=0.20,
    )
    elapsed = time.monotonic() - start_mono
    assert code == 1, "Expected probe to fail closed on timed-out blocking cleanup"
    assert elapsed < 0.45, f"Blocking cleanup took {elapsed}s; was not bounded by 0.20s budget"


def test_run_service_readiness_probe_forcibly_bounds_blocking_restart():
    """Verifies that a genuinely blocking restart callable cannot overrun the monotonic deadline unbounded."""
    def genuinely_blocking_restart(to):
        time.sleep(5.0)
        return (0, "ok")

    start_mono = time.monotonic()
    code = run_service_readiness_probe(
        restart_fn=genuinely_blocking_restart,
        poll_fn=lambda to: (True, "status=ok"),
        inspect_fn=lambda to: (True, "online"),
        status_fn=lambda to: (0, "online"),
        budget_sec=0.20,
    )
    elapsed = time.monotonic() - start_mono
    assert code == 1, "Expected probe to fail closed on timed-out blocking restart"
    assert elapsed < 0.45, f"Blocking restart took {elapsed}s; was not bounded by 0.20s budget"





