#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_b3_handoff_contract.py
Unit tests verifying strict Producer-Consumer contract parity between B1 (trend_engine_b1)
and B3 (RunPaths / orchestrator.run_pipeline). Eliminates F2 Split-Brain / Path Entropy.
(Boss Items 3 & 12, Component Review 43a).
"""

import json
from pathlib import Path
import pytest

from core.paths import RunPaths, resolve_episodes_dir


def test_b3_handoff_path_resolution_parity(tmp_path, monkeypatch):
    """B1 writes candidate artifacts to resolve_episodes_dir() / temp_task_id.
    RunPaths(temp_task_id) must resolve to the EXACT SAME directory, not repo/runs/.
    """
    monkeypatch.setenv("VF_EPISODES_DIR", str(tmp_path / "episodes"))

    episodes_dir = resolve_episodes_dir()
    slug = "silicon_chip_war"
    temp_task_id = f"EN_TEMP_{slug}"

    # 1. Simulate Producer (B1 trend_engine_b1) writing artifacts
    producer_dir = episodes_dir / temp_task_id
    producer_dir.mkdir(parents=True, exist_ok=True)

    competitor_card = {"market": "EN", "differentiation_gap": "Forensic breakdown"}
    grounding_data = {"grounding_table": [{"metric": "Market share", "value": "54%"}]}

    (producer_dir / "competitor_intel_card.json").write_text(json.dumps(competitor_card), encoding="utf-8")
    (producer_dir / "grounding_intel.json").write_text(json.dumps(grounding_data), encoding="utf-8")

    # 2. Consumer (RunPaths instantiated with temp_task_id)
    consumer_paths = RunPaths(temp_task_id)

    # Parity assertions
    assert consumer_paths.root == producer_dir, f"Split-brain detected! {consumer_paths.root} != {producer_dir}"
    assert (consumer_paths.root / "competitor_intel_card.json").is_file()
    assert (consumer_paths.root / "grounding_intel.json").is_file()

    loaded_card = json.loads((consumer_paths.root / "competitor_intel_card.json").read_text(encoding="utf-8"))
    assert loaded_card == competitor_card


def test_runpaths_routes_all_canonical_episode_shapes(tmp_path, monkeypatch):
    """Verify that EP_*, *_EP*, *_TEMP_*, and TEMP_* all route to resolve_episodes_dir()."""
    monkeypatch.setenv("VF_EPISODES_DIR", str(tmp_path / "episodes"))
    episodes_dir = resolve_episodes_dir()

    test_ids = [
        "EP_0001",
        "EN_EP0042_lithography",
        "JP_EP0010_kodokushi",
        "KR_TEMP_chaebol_reform",
        "TEMP_fast_recon_99",
        "VN_TEMP_market_surge",
    ]

    for tid in test_ids:
        rp = RunPaths(tid)
        expected_root = episodes_dir / tid
        assert rp.root == expected_root, f"Failed for {tid}: {rp.root} != {expected_root}"


def test_runpaths_rejects_path_traversal():
    """RunPaths must reject path traversal attempts with ValueError."""
    with pytest.raises(ValueError, match="Path traversal"):
        RunPaths("../escape_dir")

    with pytest.raises(ValueError, match="Path traversal"):
        RunPaths("..\\escape_dir")

    with pytest.raises(ValueError, match="Path traversal"):
        RunPaths("sub/folder")
