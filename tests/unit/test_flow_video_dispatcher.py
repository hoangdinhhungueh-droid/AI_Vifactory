#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for flow_video_dispatcher dynamic quota detection and account rotation (Rule 121 & 140)."""

import pytest
from pathlib import Path

from scripts.flow_video_dispatcher import (
    FlowQuotaExhaustedError,
    detect_flow_quota_exhausted,
    get_seed_image_path,
    PROFILES,
    DISABLED_ACCOUNTS
)


class StubPage:
    """Pure duck-typed browser page stub for quota detection testing."""
    def __init__(self, hit: bool = False, msg: str = ""):
        self._result = {"hit": hit, "msg": msg}

    def evaluate(self, script: str):
        return self._result


def test_detect_flow_quota_exhausted_positive():
    """Verifies that detect_flow_quota_exhausted detects various quota exhaustion texts in DOM."""
    stub = StubPage(hit=True, msg="Insufficient credits")
    hit, msg = detect_flow_quota_exhausted(stub)
    assert hit is True
    assert msg == "Insufficient credits"


def test_detect_flow_quota_exhausted_negative():
    """Verifies that detect_flow_quota_exhausted returns False when DOM is clean."""
    stub = StubPage(hit=False, msg="")
    hit, msg = detect_flow_quota_exhausted(stub)
    assert hit is False
    assert msg == ""


def test_flow_quota_exhausted_error_inheritance():
    """Ensures FlowQuotaExhaustedError inherits from RuntimeError."""
    err = FlowQuotaExhaustedError("Quota reached")
    assert isinstance(err, RuntimeError)
    assert str(err) == "Quota reached"


def test_get_seed_image_path_resolution(tmp_path):
    """Verifies get_seed_image_path looks in composite_seeds and returns valid Path."""
    ep_dir = tmp_path / "EP_TEST"
    seeds_dir = ep_dir / "composite_seeds"
    seeds_dir.mkdir(parents=True)
    target_file = seeds_dir / "composite_SCENE_01.png"
    target_file.write_bytes(b"PNG_DATA_" + b"0" * 15000)

    resolved = get_seed_image_path(ep_dir, "SCENE_01")
    assert resolved == target_file
    assert resolved.exists()


def test_fleet_profiles_integrity():
    """Ensures active profiles are properly registered (excluding dropped pro acc_06)."""
    for i in [1, 2, 3, 4, 5, 7]:
        acc_key = f"acc_{i:02d}"
        assert acc_key in PROFILES
        assert "email" in PROFILES[acc_key]
        assert "path" in PROFILES[acc_key]
    assert "acc_06" not in PROFILES
    assert "acc_06" in DISABLED_ACCOUNTS
    assert "hết gói pro" in DISABLED_ACCOUNTS["acc_06"].lower()
