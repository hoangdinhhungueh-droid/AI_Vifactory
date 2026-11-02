#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_story_preset.py — Unit & Invariant Tests for Pipeline Presets."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from app.services.preset_loader import (
    load_preset,
    list_available_presets,
    Preset,
    DurationWindow,
    WordBudget,
    PaletteConfig,
)


def test_load_story_forensic_preset():
    preset = load_preset("story_forensic")
    assert preset.name == "story_forensic"
    assert preset.aspect_ratio == "16:9"
    assert preset.resolution.width == 1920
    assert preset.resolution.height == 1080
    assert preset.duration_window_s.min == 180
    assert preset.duration_window_s.max == 300
    assert preset.duration_window_s.target == 240
    assert preset.narration.word_budget.min == 450
    assert preset.narration.word_budget.max == 750
    assert len(preset.beats) == 5
    total_share = sum(b.share for b in preset.beats)
    assert abs(total_share - 1.0) < 1e-4
    assert preset.visual.palette.paper == "#F4F1EA"
    assert preset.visual.veo_share_max == 0.30
    assert preset.visual.forbid_photoreal_real_persons is True
    assert preset.tts.voice == "en-US-ChristopherNeural"

    # Also test loading with extension and relative path
    preset_yaml = load_preset("story_forensic.yaml")
    assert preset_yaml.name == "story_forensic"

    preset_path = load_preset("config/presets/story_forensic.yaml")
    assert preset_path.name == "story_forensic"


def test_load_macro_legacy_preset():
    preset = load_preset("macro_legacy")
    assert preset.name == "macro_legacy"
    assert preset.aspect_ratio == "16:9"
    assert preset.duration_window_s.min == 480
    assert preset.duration_window_s.max == 720
    assert preset.duration_window_s.target == 600
    total_share = sum(b.share for b in preset.beats)
    assert abs(total_share - 1.0) < 1e-4
    assert preset.visual.palette.paper == "#F4F1EA"


def test_list_available_presets():
    presets = list_available_presets()
    assert "story_forensic" in presets
    assert "macro_legacy" in presets


def test_preset_invalid_shares():
    raw = {
        "name": "invalid_shares",
        "duration_window_s": {"min": 180, "max": 300, "target": 240},
        "narration": {"wpm_estimate": 150, "word_budget": {"min": 400, "max": 700}},
        "beats": [
            {"id": "b1", "share": 0.5},
            {"id": "b2", "share": 0.3},
        ],
    }
    with pytest.raises(ValidationError):
        Preset.model_validate(raw)


def test_preset_invalid_duration_bounds():
    with pytest.raises(ValidationError):
        DurationWindow(min=300, max=180, target=240)

    with pytest.raises(ValidationError):
        DurationWindow(min=180, max=300, target=350)


def test_preset_invalid_palette_hex():
    with pytest.raises(ValidationError):
        PaletteConfig(paper="invalid_color")

    with pytest.raises(ValidationError):
        PaletteConfig(paper="#12345")  # only 5 hex digits
