# tests/unit/test_authoritative_ast_scanner_adversarial.py
"""Adversarial unit tests for authoritative AST Rule 139 scanner (Rule 121, Rule 139).
Tests detection of silent passes, throwaway exception assignments in all AST forms,
and unreachable code without using any test doubles.
Strict zero test-doubles policy (Rule 118).
"""

import ast

from scripts.forensics.probe_ast_rule139 import (
    is_noop_statement,
    is_throwaway_assignment,
)


def _scan_snippet(code_snippet: str) -> list:
    """Helper to parse a synthetic code snippet and return defects."""
    tree = ast.parse(code_snippet, filename="<test_snippet>")
    # We use a dummy file path and scan using ast walk directly
    defects = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            body_stmts = node.body
            all_suppression = bool(body_stmts) and all(
                is_noop_statement(s) or is_throwaway_assignment(s) for s in body_stmts
            )
            if all_suppression:
                has_throwaway = any(is_throwaway_assignment(s) for s in body_stmts)
                h_type = ast.unparse(node.type) if node.type else "bare"
                rule_str = f"RULE_139_THROWAWAY_EXCEPT_SUPPRESSION ({h_type})" if has_throwaway else f"RULE_139_SILENT_EXCEPT_PASS ({h_type})"
                defects.append({"line": node.lineno, "rule": rule_str, "severity": "HIGH"})
        for attr in ("body", "orelse", "finalbody"):
            b_list = getattr(node, attr, None)
            if isinstance(b_list, list) and len(b_list) > 1:
                for idx, stmt in enumerate(b_list[:-1]):
                    if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                        lineno = b_list[idx + 1].lineno
                        defects.append({"line": lineno, "rule": "RULE_139_UNREACHABLE_CODE", "severity": "HIGH"})
    return defects


def test_adversarial_standard_silent_pass():
    """Verifies standard bare and typed except: pass is flagged as SILENT_EXCEPT_PASS."""
    snippet = """
try:
    x = 1
except Exception:
    pass
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert "RULE_139_SILENT_EXCEPT_PASS (Exception)" in defects[0]["rule"]


def test_adversarial_ellipsis_suppression():
    """Verifies except: ... ellipsis suppression is flagged as SILENT_EXCEPT_PASS."""
    snippet = """
try:
    x = 1
except ValueError:
    ...
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert "RULE_139_SILENT_EXCEPT_PASS (ValueError)" in defects[0]["rule"]


def test_adversarial_single_throwaway_assignment():
    """Verifies single _ = exc assignment is flagged as THROWAWAY_EXCEPT_SUPPRESSION."""
    snippet = """
try:
    x = 1
except RuntimeError as err:
    _ = err
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert "RULE_139_THROWAWAY_EXCEPT_SUPPRESSION (RuntimeError)" in defects[0]["rule"]


def test_adversarial_annotated_throwaway_assignment():
    """Verifies annotated _: Any = exc assignment is flagged as THROWAWAY_EXCEPT_SUPPRESSION."""
    snippet = """
try:
    x = 1
except OSError as os_err:
    _: Any = os_err
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert "RULE_139_THROWAWAY_EXCEPT_SUPPRESSION (OSError)" in defects[0]["rule"]


def test_adversarial_chained_throwaway_assignment():
    """Verifies chained assignments containing _ (a = _ = exc or _ = a = exc) are flagged."""
    snippet_1 = """
try:
    x = 1
except TypeError as t_err:
    a = _ = t_err
"""
    defects_1 = _scan_snippet(snippet_1)
    assert len(defects_1) == 1
    assert "RULE_139_THROWAWAY_EXCEPT_SUPPRESSION (TypeError)" in defects_1[0]["rule"]

    snippet_2 = """
try:
    x = 1
except KeyError as k_err:
    _ = b = k_err
"""
    defects_2 = _scan_snippet(snippet_2)
    assert len(defects_2) == 1
    assert "RULE_139_THROWAWAY_EXCEPT_SUPPRESSION (KeyError)" in defects_2[0]["rule"]


def test_adversarial_unpacking_throwaway_assignment():
    """Verifies tuple/list unpacking assignment with _ target is flagged."""
    snippet = """
try:
    x = 1
except ValueError as v_err:
    (_, ignored) = (v_err, 42)
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert "RULE_139_THROWAWAY_EXCEPT_SUPPRESSION (ValueError)" in defects[0]["rule"]


def test_adversarial_noop_docstring_combined_with_throwaway():
    """Verifies docstring constant preceding throwaway is flagged as THROWAWAY_EXCEPT_SUPPRESSION."""
    snippet = """
try:
    x = 1
except AttributeError as a_err:
    \"\"\"Non-fatal suppression rationale docstring.\"\"\"
    _ = a_err
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert "RULE_139_THROWAWAY_EXCEPT_SUPPRESSION (AttributeError)" in defects[0]["rule"]


def test_adversarial_legitimate_handler_with_logger_not_flagged():
    """Verifies legitimate error handler with logging call is NOT flagged."""
    snippet = """
try:
    x = 1
except Exception as log_err:
    logger.error("Operation failed: %s", log_err)
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 0


def test_adversarial_legitimate_handler_with_reraise_not_flagged():
    """Verifies legitimate error handler that raises is NOT flagged."""
    snippet = """
try:
    x = 1
except Exception as wrap_err:
    raise RuntimeError("Wrapped failure") from wrap_err
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 0


def test_adversarial_unreachable_code_detected():
    """Verifies statements after return/raise are flagged as RULE_139_UNREACHABLE_CODE."""
    snippet = """
def test_func():
    return 42
    unreachable_var = 100
"""
    defects = _scan_snippet(snippet)
    assert len(defects) == 1
    assert defects[0]["rule"] == "RULE_139_UNREACHABLE_CODE"
