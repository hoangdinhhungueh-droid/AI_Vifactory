#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_instinct_manager.py — Unit Tests for InstinctManager & 3-Layer Gatekeeper.

Validates:
- Rule 118: Zero-Mock truthful telemetry routing.
- Rule 128: Generic Contract Pattern across stages.
- 3-Layer Gatekeeper:
  * Layer 1: Statistical Significance (evidence_count >= 3)
  * Layer 2: Safe Parameter Bounding
  * Layer 3: 5-Slot Memory Vault with FIFO eviction
- Signal-to-Stage Routing Matrix.
"""

import pytest
from pathlib import Path
from core.instinct_manager import (
    InstinctManager,
    ThreeLayerGatekeeper,
    get_instinct_manager,
    MAX_SLOTS,
)


def test_three_layer_gatekeeper_bounds():
    # Test Layer 1 Gate
    assert ThreeLayerGatekeeper.validate_statistical_significance(3) is True
    assert ThreeLayerGatekeeper.validate_statistical_significance(5) is True
    assert ThreeLayerGatekeeper.validate_statistical_significance(2) is False
    assert ThreeLayerGatekeeper.validate_statistical_significance(1) is False

    # Test Layer 2 Gate: Clamping
    patch = {
        "ko_speech_rate": 8.0,  # exceeds max 6.5
        "first_metric_max_word_offset": 2,  # below min 4
        "min_text_area_pct": 50,  # within 30-55
    }
    sanitized = ThreeLayerGatekeeper.validate_parameter_bounds(patch)
    assert sanitized["ko_speech_rate"] == 6.5
    assert sanitized["first_metric_max_word_offset"] == 4
    assert sanitized["min_text_area_pct"] == 50


def test_instinct_vault_5_slots(tmp_path: Path):
    tmp_vault_path = tmp_path / "active_instincts.json"
    mgr = InstinctManager(config_path=tmp_vault_path)

    # Add 5 slots
    for i in range(1, 6):
        mgr.propose_instinct(
            target_stage=f"stage_{i}",
            rule_code=f"RULE_{i}",
            parameter_patch={"val": i},
            rationale=f"Rationale {i}",
            evidence_count=3,
        )

    vault = mgr.load_vault()
    assert len(vault["slots"]) == MAX_SLOTS
    assert [s["slot_id"] for s in vault["slots"]] == [1, 2, 3, 4, 5]

    # Propose 6th slot -> triggers FIFO eviction of lowest applied count
    mgr.propose_instinct(
        target_stage="stage_6",
        rule_code="RULE_6",
        parameter_patch={"val": 6},
        rationale="Rationale 6",
        evidence_count=3,
    )
    vault6 = mgr.load_vault()
    assert len(vault6["slots"]) == MAX_SLOTS
    # Verify slot_ids are re-indexed 1..5
    assert [s["slot_id"] for s in vault6["slots"]] == [1, 2, 3, 4, 5]
    assert any(s["rule_code"] == "RULE_6" for s in vault6["slots"])


def test_signal_to_stage_routing(tmp_path: Path):
    tmp_vault_path = tmp_path / "active_instincts.json"
    mgr = InstinctManager(config_path=tmp_vault_path)

    telemetry = {
        "retention_15s_pct": 52.0,  # < 65% -> triggers s03
        "ctr_28h_pct": 4.1,         # < 5.5% -> triggers s11
        "karaoke_drift_max_ms": 120,# > 100ms -> triggers s04
        "visual_critic_score": 7.8, # < 8.5 -> triggers s05
    }
    actions = mgr.evaluate_telemetry_signals(telemetry)
    assert len(actions) == 4
    stages = [a["target_stage"] for a in actions]
    assert "s03_script" in stages
    assert "s11_seo" in stages
    assert "s04_pacing" in stages
    assert "s05_director" in stages
