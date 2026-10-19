# tests/unit/test_junit_validator.py
"""Unit tests for JUnit XML strict metric parsing, exact scope, cardinality, and outcome-child reconciliation (Rule 121 & Rule 139).
Tests complete positive and negative validation matrices without using any test doubles.
"""

import pytest
from scripts.orchestrator.boss_orchestrator import (
    EXPECTED_FOCUSED_TESTCASES,
    EXPECTED_TESTCASE_TO_CLASS,
    _parse_junit_metrics,
)


def _build_xml(testcase_names, failures=0, errors=0, skipped=0, deselected=0):
    total = len(testcase_names)
    tc_tags = "".join(
        f'<testcase classname="{EXPECTED_TESTCASE_TO_CLASS.get(name, "tests.unit.test_visual_taxonomy_and_regex")}" name="{name}" time="0.01" />'
        for name in testcase_names
    )
    return (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="{total}" failures="{failures}" errors="{errors}" '
        f'skipped="{skipped}" deselected="{deselected}" time="1.0">'
        f'{tc_tags}'
        f'</testsuite>'
    )


def test_positive_exact_expected_scope_passes():
    """Verifies that an XML report containing the exact 52 expected testcases passes with 0 failures."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = [
        f'<testcase classname="{EXPECTED_TESTCASE_TO_CLASS[name]}" name="{name}" time="0.01" />'
        for name in tc_list
    ]

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
    xml = '<testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0"><testcase name="t1" classname="tests.unit.test_visual_taxonomy_and_regex" /></testsuite>'
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


def test_lookalike_classname_fails_closed():
    """Verifies that a lookalike classname for a known testcase raises RuntimeError."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = []
    for name in tc_list:
        mod = EXPECTED_TESTCASE_TO_CLASS[name]
        if name == tc_list[0]:
            mod = mod + "_shadow"
        tc_tags.append(f'<testcase classname="{mod}" name="{name}" time="0.01" />')

    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="{len(tc_list)}" failures="0" errors="0" skipped="0" deselected="0" time="1.0">'
        f'{"".join(tc_tags)}'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="class mismatch in Linux VPS"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_wrong_known_classname_fails_closed():
    """Verifies that assigning a testcase to another known canonical module raises RuntimeError."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = []
    for name in tc_list:
        mod = EXPECTED_TESTCASE_TO_CLASS[name]
        if name == "test_production_visual_taxonomy_structure_and_schema":
            mod = "tests.unit.test_lock_liveness_probe"
        tc_tags.append(f'<testcase classname="{mod}" name="{name}" time="0.01" />')

    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="{len(tc_list)}" failures="0" errors="0" skipped="0" deselected="0" time="1.0">'
        f'{"".join(tc_tags)}'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="class mismatch in Linux VPS: expected exact 'tests.unit.test_visual_taxonomy_and_regex'"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_declared_to_element_cardinality_mismatch_fails_closed():
    """Verifies that declared tests attribute mismatch with physical <testcase> count raises RuntimeError."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = [
        f'<testcase classname="{EXPECTED_TESTCASE_TO_CLASS[name]}" name="{name}" time="0.01" />'
        for name in tc_list
    ]
    # Declared 55 tests but only 52 elements provided
    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="55" failures="0" errors="0" skipped="0" deselected="0" time="1.0">'
        f'{"".join(tc_tags)}'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="Declared test count \\(55\\) does not match physical <testcase> element count \\(52\\)"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_malformed_numeric_count_fails_closed():
    """Verifies that non-numeric attribute strings on <testsuite> raise RuntimeError."""
    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="not_a_number" failures="0" errors="0" skipped="0">'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="must be a non-negative integer string"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_negative_numeric_count_fails_closed():
    """Verifies that negative integer strings (e.g. -5) raise RuntimeError."""
    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="-52" failures="0" errors="0" skipped="0">'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="must be a non-negative integer string"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_inconsistent_deselected_scope_fails_closed():
    """Verifies that invalid deselected attribute values raise RuntimeError."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = [
        f'<testcase classname="{EXPECTED_TESTCASE_TO_CLASS[name]}" name="{name}" time="0.01" />'
        for name in tc_list
    ]
    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="52" failures="0" errors="0" skipped="0" deselected="corrupt">'
        f'{"".join(tc_tags)}'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="Attribute 'deselected' must be a non-negative integer string"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)


def test_outcome_child_mismatch_declared_zero_has_child_failure_fails_closed():
    """Verifies that an unannounced physical <failure> child element raises RuntimeError."""
    tc_list = sorted(list(EXPECTED_FOCUSED_TESTCASES))
    tc_tags = []
    for i, name in enumerate(tc_list):
        cls = EXPECTED_TESTCASE_TO_CLASS[name]
        if i == 0:
            tc_tags.append(f'<testcase classname="{cls}" name="{name}"><failure message="boom">trace</failure></testcase>')
        else:
            tc_tags.append(f'<testcase classname="{cls}" name="{name}" />')

    # Declared failures="0", but 1 physical <failure> tag exists
    xml = (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuite name="pytest" tests="52" failures="0" errors="0" skipped="0">'
        f'{"".join(tc_tags)}'
        f'</testsuite>'
    )
    with pytest.raises(RuntimeError, match="Declared failure count \\(0\\) does not match physical <failure> element count \\(1\\)"):
        _parse_junit_metrics(xml, "Linux VPS", exit_code=0, age_seconds=5.0, min_tests=52)
