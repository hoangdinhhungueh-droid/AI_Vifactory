#!/usr/bin/env python3
"""tests/unit/test_visual_audit.py — Unit Tests for Visual Audit Engine (Rule 122 & AVF-VOX-001).

Tests:
1. run_falsifiable_adversarial_checks passes with 0 NameErrors.
2. audit_fg_alpha_and_boundary detects boundary touch and clean alpha.
3. audit_provenance_and_size_signatures formats and prints without exceptions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from tools.forensics.visual_audit import (
    audit_fg_alpha_and_boundary,
    audit_provenance_and_size_signatures,
    run_falsifiable_adversarial_checks,
)


def test_falsifiable_adversarial_checks_pass() -> None:
    """Verifies that synthetic magenta spill and photorealism checks run without NameErrors."""
    run_falsifiable_adversarial_checks()


def test_fg_alpha_boundary_audit(tmp_path: Path) -> None:
    """Tests alpha channel boundary touch detection."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean FG image (centered subject, 0 touch, 0 magenta)
    img_clean = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for x in range(30, 70):
        for y in range(30, 70):
            img_clean.putpixel((x, y), (100, 150, 200, 255))
    clean_path = assets_dir / "fg_clean.png"
    img_clean.save(clean_path)

    results = audit_fg_alpha_and_boundary([str(assets_dir)])
    assert len(results) == 1
    assert results[0]["touching_edge_px"] == 0
    assert results[0]["magenta_spill_ratio"] == 0.0

    # 2. Touching boundary must raise ValueError
    img_touch = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for x in range(0, 50):
        img_touch.putpixel((x, 0), (100, 150, 200, 255))
    touch_path = assets_dir / "fg_touch.png"
    img_touch.save(touch_path)

    with pytest.raises(ValueError, match="touches canvas boundary"):
        audit_fg_alpha_and_boundary([str(assets_dir)])


def test_audit_provenance_and_size_signatures(tmp_path: Path) -> None:
    """Tests manifest provenance reporting without crashing."""
    fixture_dir = tmp_path / "golden"
    assets_dir = fixture_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "visual_adjudication": {
            "evaluator_model": "claude-opus-5-5",
            "request_id": "req_123",
            "raw_response_hash": "a" * 64,
        },
        "assets": {
            "generator_provenance": {
                "provider": "google_gemini_web",
                "model_id": "gemini-2.5-pro",
                "engine": "Playwright Automation Cluster",
                "is_procedural_fill": False,
            }
        },
    }
    (fixture_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Minimal asset
    dummy_img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
    dummy_img.save(assets_dir / "bg_01.png")

    # Should run and print without errors
    audit_provenance_and_size_signatures([(str(fixture_dir), "Test Fixture")])
