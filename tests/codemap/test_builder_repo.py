#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/codemap/test_builder_repo.py — Integration test running builder on real repo."""

from pathlib import Path
from tools.codemap.builder import build_codemap, check_codemap


def test_builder_and_freshness_on_real_repo():
    repo_root = Path(__file__).resolve().parent.parent.parent
    registry = build_codemap(repo_root)

    assert registry.schema_version == "1.0"
    stage_ids = [s.id for s in registry.stages]
    assert "mini_s1" not in stage_ids
    assert "mini_s2" not in stage_ids
    assert "stage_consumer" not in stage_ids
    assert len(registry.stages) >= 11
    assert registry.summary["mismatches"] == 0

    code, msg = check_codemap(repo_root)
    assert code == 0
    assert "CLEAN" in msg
