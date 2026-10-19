# tests/unit/test_junit_validator.py
"""Unit tests for JUnit XML strict metric parsing and exact scope validation (Rule 121 & Rule 139).
Tests positive cases, negative cases, stale reports, malformed XML, duplicate tests,
and missing age without using any test doubles.
"""

import pytest
from scripts.orchestrator.boss_orchestrator import _parse_junit_metrics, EXPECTED_FOCUSED_TESTCASES


def _build_xml(testcase_names, failures=0, errors=0, skipped=0, deselected=0, module="tests.unit.test_visual_taxonomy_and_regex"):
    total = len(testcase_names)
    tc_tags = "".join(f'<testcase classname="{module}" name="{name}" time="0.01" />' for name in testcase_names)
    return (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="{total}" failures="{failures}" errors="{errors}" '
        f'skipped="{skipped}" deselected="{deselected}" time="1.0">'
        f'{tc_tags}'
        f'</testsuite>'
    )


def test_positive_exact_expected_scope_passes():
    """Verifies that an XML report containing the exact 52 expected testcases passes with 0 failures."""
    # Build complete 52-test XML
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = []
    for name in tc_list:
        if "taxonomy" in name or "cjk" in name or "english" in name or "roster" in name or "financial" in name or "consumer" in name:
            mod = "tests.unit.test_visual_taxonomy_and_regex"
        elif "vps" in name or "failover" in name:
            mod = "tests.unit.test_vps_runner_failover"
        else:
            mod = "tests.unit.test_lock_liveness_probe"
        tc_tags.append(f'<testcase classname="{mod}" name="{name}" time="0.01" />')

    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="{len(tc_list)}" failures="0" errors="0" skipped="0" deselected="0" time="1.0">'
        f'{"".join(tc_tags)}'
        f'</testsuite>'
    )
    tests, passed, fails, errs, skips, desel = _parse_junit_metrics(
        xml, "Test Suite", exit_code=0, age_seconds=10.0, min_tests=52
    )
    assert tests == 52
    assert passed == 52
    assert fails == 0
    assert errs == 0
    assert skips == 0
    assert desel == 0


def test_nonzero_exit_code_fails_closed():
    """Verifies that nonzero exit code raises RuntimeError fail-closed."""
    with pytest.raises(RuntimeError, match="Focused test suite run failed with exit code 1"):
        _parse_junit_metrics("<testsuite></testsuite>", "Linux VPS", exit_code=1, age_seconds=1.0)


def test_missing_age_seconds_fails_closed():
    """Verifies that missing age_seconds (None) raises RuntimeError fail-closed."""
    with pytest.raises(RuntimeError, match="JUnit XML report is missing, invalid or stale"):
        _parse_junit_metrics("<testsuite></testsuite>", "Linux VPS", exit_code=0, age_seconds=None)


def test_stale_age_seconds_fails_closed():
    """Verifies that age_seconds > 600s raises RuntimeError fail-closed."""
    with pytest.raises(RuntimeError, match="age=750.0s > 600s"):
        _parse_junit_metrics("<testsuite></testsuite>", "Linux VPS", exit_code=0, age_seconds=750.0)


def test_malformed_xml_fails_closed():
    """Verifies that malformed unparseable XML raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Failed to dynamically parse JUnit XML"):
        _parse_junit_metrics("<testsuite>unclosed", "Linux VPS", exit_code=0, age_seconds=5.0)


def test_below_minimum_scope_fails_closed():
    """Verifies that test count below minimum required scope raises RuntimeError."""
    xml = '<testsuite name="pytest" tests="10" failures="0" errors="0" skipped="0"><testcase name="t1" classname="tests.unit.test_visual_taxonomy_and_regex" /></testsuite>'
    with pytest.raises(RuntimeError, match="below required minimum scope"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_unexpected_testcase_fails_closed():
    """Verifies that unexpected testcases outside canonical roster are rejected."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES)) + ["test_unregistered_shadow_testcase"]
    xml = _build_xml(tc_list)
    with pytest.raises(RuntimeError, match="JUnit report contains 1 unexpected testcase"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_duplicate_testcase_fails_closed():
    """Verifies that duplicate testcase names are strictly rejected."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))[:51]
    # duplicate the first testcase
    tc_list.append(tc_list[0])
    xml = _build_xml(tc_list)
    with pytest.raises(RuntimeError, match="Duplicate testcase"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_missing_testcase_fails_closed():
    """Verifies that missing testcases are strictly rejected."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))[:40]
    xml = _build_xml(tc_list)
    with pytest.raises(RuntimeError, match="JUnit report missing 12 expected testcase"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=40)
