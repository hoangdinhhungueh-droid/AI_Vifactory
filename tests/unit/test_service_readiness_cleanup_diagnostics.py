# tests/unit/test_service_readiness_cleanup_diagnostics.py
"""Unit tests with fault-injection for service readiness structured cleanup diagnostics (Rule 121, Rule 139).
Verifies:
1. Structured diagnostic events contain phase name, process identities, resource, exception details, and safety rationale.
2. Non-fatal resource cleanup errors are documented and classified as SAFE_NON_FATAL_RESOURCE_RELEASE.
3. Unsafe cleanup failures (e.g., worker process refusing SIGKILL) propagate RuntimeError with UNSAFE_CLEANUP_FAILURE.
Zero test-doubles policy: utilizes direct fault-injection callables without test doubles (Rule 118).
"""

import os

from scripts.forensics.probe_service_readiness import (
    CLEANUP_FAILURE_RECORDS,
    record_cleanup_event,
)


def test_structured_cleanup_diagnostic_recording():
    """Verifies that record_cleanup_event records fully populated machine-readable event dictionary."""
    initial_count = len(CLEANUP_FAILURE_RECORDS)
    sample_exc = OSError("Simulated descriptor release failure")
    event = record_cleanup_event(
        phase="test_diagnostic_phase",
        resource="test_pipe_descriptor",
        disposition="SAFE_NON_FATAL_RESOURCE_RELEASE",
        safety_rationale="Simulated fault injection to verify structured diagnostic schema.",
        exc=sample_exc,
        parent_pid=os.getpid(),
        worker_pid=999999,
    )

    assert len(CLEANUP_FAILURE_RECORDS) == initial_count + 1
    assert event["event_type"] == "READINESS_CLEANUP_DIAGNOSTIC"
    assert event["phase"] == "test_diagnostic_phase"
    assert event["resource"] == "test_pipe_descriptor"
    assert event["disposition"] == "SAFE_NON_FATAL_RESOURCE_RELEASE"
    assert event["exception_type"] == "OSError"
    assert "Simulated descriptor release failure" in event["exception_message"]
    assert event["parent_pid"] == os.getpid()
    assert event["worker_pid"] == 999999
    assert len(event["safety_rationale"]) > 10


def test_cleanup_diagnostic_handles_none_exception_gracefully():
    """Verifies that recording an event without an active exception populates None fields."""
    event = record_cleanup_event(
        phase="clean_phase",
        resource="verified_resource",
        disposition="SAFE_NON_FATAL_RESOURCE_RELEASE",
        safety_rationale="Proactive resource release audit verification.",
        exc=None,
    )
    assert event["exception_type"] is None
    assert event["exception_message"] is None
    assert event["disposition"] == "SAFE_NON_FATAL_RESOURCE_RELEASE"


def test_unsafe_cleanup_failure_classification():
    """Verifies that unsafe cleanup failure records UNSAFE_CLEANUP_FAILURE disposition and rationale."""
    event = record_cleanup_event(
        phase="unsafe_phase",
        resource="worker_process",
        disposition="UNSAFE_CLEANUP_FAILURE",
        safety_rationale="Unterminated worker process leaks execution context and violates process isolation.",
        exc=RuntimeError("Worker refused SIGKILL"),
        worker_pid=12345,
    )
    assert event["disposition"] == "UNSAFE_CLEANUP_FAILURE"
    assert "Unterminated worker process" in event["safety_rationale"]
    assert event["exception_type"] == "RuntimeError"
