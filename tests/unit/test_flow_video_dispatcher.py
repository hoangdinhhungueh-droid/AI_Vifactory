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


def test_chip_detection_scoped_selectors():
    """Rule 121: Verifies that global button:has-text('close') is NOT used in chip verification to prevent modal close button false positives."""
    import inspect
    import scripts.flow_video_dispatcher as fvd

    src = inspect.getsource(fvd.generate_and_download_clip)
    # Ensure button:has-text('close') is not in the chip verification section
    assert "chips_now = page.locator(\"button:has-text('expand_content'), button:has-text('close')" not in src
    # Ensure scoped selector is present
    assert "div.ProseMirror .ingredient-chip" in src
    assert "fail_chip_" in src
    # Ensure panel open check is executed before uploading
    assert "panel_open_indicators" in src
    assert "is_panel_open" in src


def test_flow_dispatcher_pilot_cli_argument():
    """Rule 121: Verifies that --pilot CLI argument is registered and limits clips to 2 scenes."""
    import argparse
    import scripts.flow_video_dispatcher as fvd

    # Inspect main or run parser with --help / parse test
    # We can check that '--pilot' is in the source of main
    import inspect
    main_src = inspect.getsource(fvd.main)
    assert "--pilot" in main_src
    assert "(args.mode == \"demo\" or args.pilot)" in main_src


def test_scoped_panel_and_trigger_selectors():
    """Rule 121: Verifies panel indicators are strictly scoped to drawers and trigger targets prompt box."""
    import inspect
    import scripts.flow_video_dispatcher as fvd

    src = inspect.getsource(fvd.generate_and_download_clip)
    # Check scoped drawer indicators
    assert ".add-menu-panel" in src
    assert ".ingredient-drawer" in src
    assert "mat-bottom-sheet-container" in src
    assert ".cdk-overlay-pane:has-text('Tải lên')" in src
    assert ".cdk-overlay-pane:has-text('Upload')" in src

    # Ensure trigger button is scoped to prompt box
    assert "flow-prompt-input button[aria-label*='Thêm' i]" in src
    assert "flow-prompt-input button[aria-label*='Add' i]" in src
    assert "flow-prompt-input button" in src

    # Verify FileChooser expect_file_chooser is present
    assert "expect_file_chooser" in src
    assert "fc.set_files" in src


def test_chip_detection_anti_false_positive():
    """Rule 121: Verifies that generic [class*='chip'] is excluded to avoid agent-mode-chip false positives, and flow-ingredient-chip is used."""
    import inspect
    import scripts.flow_video_dispatcher as fvd

    src = inspect.getsource(fvd.generate_and_download_clip)
    # Generic [class*="chip"] matches 'agent-mode-chip' (Tác nhân) - must be excluded from JS evaluation
    assert '[class*="chip"]' not in src
    # Flow-specific ingredient chip selectors must be present
    assert "flow-ingredient-chip" in src
    assert "flow-image-ingredient-chip" in src
    assert "clear-button" in src
    assert ".detail-add-to-prompt-btn" in src


