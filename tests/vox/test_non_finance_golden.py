#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_non_finance_golden.py — Verifies Zero Semantic Bias and 5-Beat E2E Render on Science Fixture (Rule 128 & Boss Item 12)."""

from pathlib import Path

from vox.pipeline import run_pipeline
from vox.planner import plan_scenes_from_script


def test_science_golden_script_has_zero_finance_lexicon_leakage():
    science_script = Path(__file__).parent / "fixtures" / "science_golden_script.txt"
    assert science_script.exists()
    text = science_script.read_text(encoding="utf-8")

    plan = plan_scenes_from_script(text)
    assert len(plan.scenes) == 5, f"Expected exactly 5 scenes/chapters for 5-beat structure, got {len(plan.scenes)}"

    # Check zero finance lexicon leakage across all scenes, prompts, and visual elements
    plan_json = plan.model_dump_json().lower()
    finance_terms = ["ledger", "forensic", "interbank", "liquidity crisis", "balance sheet", "margin call", "chaebol", "insolvency", "debt"]
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


def test_science_golden_e2e_render_and_qa_gates(tmp_path):
    """Executes full e2e pipeline on the 5-beat science fixture, verifying 5 chapters, 0% finance leakage, and QA gates."""
    science_script = Path(__file__).parent / "fixtures" / "science_golden_script.txt"
    out_dir = tmp_path / "science_e2e"

    manifest = run_pipeline(science_script, out_dir, title="Magnetar Radio Pulse Discovery")
    assert manifest["scene_count"] == 5, f"Expected 5 scenes/chapters for 5-beat science fixture, got {manifest['scene_count']}"
    assert len(manifest["scenes"]) == 5

    # Check 0% finance leakage in manifest
    manifest_str = str(manifest).lower()
    finance_terms = ["ledger", "forensic", "interbank", "liquidity crisis", "balance sheet", "margin call", "chaebol", "insolvency"]
    for term in finance_terms:
        assert term not in manifest_str, f"Forbidden finance term '{term}' found in science manifest!"

    # Check QA gates
    qa = manifest["qa_gates"]
    assert qa["status"] == "PASS"
    assert qa["video_codec"] == "h264"
    assert qa["audio_codec"] == "aac"
    assert qa["width"] == 1920
    assert qa["height"] == 1080
    assert qa["actual_duration_sec"] > 0
    assert manifest["subtitles"]["reverse_parity_status"] == "PASS"
