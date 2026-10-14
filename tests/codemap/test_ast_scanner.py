#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/codemap/test_ast_scanner.py — Unit test for CodebaseASTScanner on mini_pipeline."""

from pathlib import Path
from tools.codemap.ast_scanner import CodebaseASTScanner


def test_ast_scanner_mini_pipeline():
    repo_root = Path(__file__).resolve().parent.parent.parent
    scanner = CodebaseASTScanner(repo_root)
    symbols, stages = scanner.scan()

    # Find mini_s1 and mini_s2 stages
    stage_ids = {s.id: s for s in stages}
    assert "mini_s1" in stage_ids
    assert "mini_s2" in stage_ids

    s1 = stage_ids["mini_s1"]
    assert s1.order == 1
    assert s1.input_model == "MiniInput"
    assert s1.output_model == "MiniOutput"
    assert "mini_s2" in s1.downstream
    assert s1.ref.line_start > 0
    assert s1.ref.line_end >= s1.ref.line_start

    # Verify failure modes detected
    exc_types = [fm.exc_type for fm in s1.failure_modes]
    assert "RuntimeError" in exc_types or "ValueError" in exc_types or "Exception" in exc_types

    s2 = stage_ids["mini_s2"]
    assert s2.order == 2
    assert "mini_s1" in s2.upstream

    # Verify symbol graph connections
    qual_s1 = s1.qualname
    assert qual_s1 in symbols
    sym_s1 = symbols[qual_s1]
    assert sym_s1.stage_id == "mini_s1"
