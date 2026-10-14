#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_non_finance_golden.py — Verifies Zero Semantic Bias on Science Golden Script (Rule 128)."""

from pathlib import Path
from vox.planner import plan_scenes_from_script


def test_science_golden_script_has_zero_finance_lexicon_leakage():
    science_script = Path(__file__).parent / "fixtures" / "science_golden_script.txt"
    assert science_script.exists()
    text = science_script.read_text(encoding="utf-8")

    plan = plan_scenes_from_script(text)
    assert len(plan.scenes) >= 3

    # Check zero finance lexicon leakage across all scenes, prompts, and visual elements
    plan_json = plan.model_dump_json().lower()
    finance_terms = ["ledger", "forensic", "interbank", "liquidity crisis", "balance sheet", "margin call"]
    for term in finance_terms:
        assert term not in plan_json, f"Forbidden finance term '{term}' leaked into science scene plan!"

    # Verify content-driven FG layout variance and camera differentiation
    camera_moves = [sc.camera for sc in plan.scenes]
    assert len(set(camera_moves)) >= 2, "Scenes must have differentiated camera moves"

    for sc in plan.scenes:
        assert sc.bg_prompt, "Scene must have non-empty bg_prompt"
        assert len(sc.fg) >= 1, "Scene must have at least one tactile FG element"
        for fg_obj in sc.fg:
            assert fg_obj.prompt, "FG element must have non-empty prompt"
            # Ensure FG prompts reflect astronomy / science domain
            fg_p_lower = fg_obj.prompt.lower()
            for f_term in finance_terms:
                assert f_term not in fg_p_lower, f"Forbidden finance term '{f_term}' found in FG prompt: {fg_obj.prompt}"
