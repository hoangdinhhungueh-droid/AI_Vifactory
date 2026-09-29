# tests/test_asset_diversity_guard.py
"""
Unit tests for Asset Diversity Guard (app/services/director_planner_b3.py).
Enforces:
  1. MAX_USES_PER_ASSET = 3
  2. MIN_GAP_SCENES = 4
"""

import pytest
from app.services.director_planner_b3 import (
    validate_asset_reuse_limits,
    MAX_USES_PER_ASSET,
    MIN_GAP_SCENES
)


def test_asset_diversity_clean_pass():
    """Verify that a compliant scene schedule with diverse assets passes."""
    scenes = [
        {"scene_index": 0, "bg_reuse_key": "bg_trading_floor", "fg_reuse_key": "fg_trader"},
        {"scene_index": 1, "bg_reuse_key": "bg_office_dusk", "fg_reuse_key": "fg_analyst"},
        {"scene_index": 2, "bg_reuse_key": "bg_fed_building", "fg_reuse_key": ""},
        {"scene_index": 3, "bg_reuse_key": "bg_server_room", "fg_reuse_key": "fg_doc_audit"},
        {"scene_index": 4, "bg_reuse_key": "bg_courtroom", "fg_reuse_key": ""},
        {"scene_index": 5, "bg_reuse_key": "bg_trading_floor", "fg_reuse_key": "fg_trader"}, # gap = 5 >= 4
        {"scene_index": 6, "bg_reuse_key": "bg_office_dusk", "fg_reuse_key": "fg_analyst"},
        {"scene_index": 7, "bg_reuse_key": "bg_fed_building", "fg_reuse_key": ""},
    ]
    res = validate_asset_reuse_limits(scenes)
    assert res["ok"], f"Expected clean pass, got violations: {res['violations']}"
    assert len(res["violations"]) == 0


def test_asset_diversity_overuse_flagged():
    """Verify that an asset used 4 or more times is flagged as overused."""
    scenes = [
        {"scene_index": 0, "bg_reuse_key": "bg_trading_floor"},
        {"scene_index": 1, "bg_reuse_key": "bg_office_1"},
        {"scene_index": 2, "bg_reuse_key": "bg_office_2"},
        {"scene_index": 3, "bg_reuse_key": "bg_office_3"},
        {"scene_index": 4, "bg_reuse_key": "bg_office_4"},
        {"scene_index": 5, "bg_reuse_key": "bg_trading_floor"},
        {"scene_index": 6, "bg_reuse_key": "bg_office_5"},
        {"scene_index": 7, "bg_reuse_key": "bg_office_6"},
        {"scene_index": 8, "bg_reuse_key": "bg_office_7"},
        {"scene_index": 9, "bg_reuse_key": "bg_office_8"},
        {"scene_index": 10, "bg_reuse_key": "bg_trading_floor"},
        {"scene_index": 11, "bg_reuse_key": "bg_office_9"},
        {"scene_index": 12, "bg_reuse_key": "bg_office_10"},
        {"scene_index": 13, "bg_reuse_key": "bg_office_11"},
        {"scene_index": 14, "bg_reuse_key": "bg_office_12"},
        {"scene_index": 15, "bg_reuse_key": "bg_trading_floor"}, # 4th use!
    ]
    res = validate_asset_reuse_limits(scenes)
    assert not res["ok"]
    assert any("overused: 4 times" in v for v in res["violations"])


def test_asset_diversity_small_gap_flagged():
    """Verify that an asset repeated within fewer than 4 scenes is flagged."""
    scenes = [
        {"scene_index": 0, "fg_reuse_key": "fg_receipt"},
        {"scene_index": 1, "fg_reuse_key": "fg_other"},
        {"scene_index": 2, "fg_reuse_key": "fg_receipt"}, # gap = 2 < 4!
    ]
    res = validate_asset_reuse_limits(scenes)
    assert not res["ok"]
    assert any("repeated too quickly" in v and "gap 2 < 4" in v for v in res["violations"])
