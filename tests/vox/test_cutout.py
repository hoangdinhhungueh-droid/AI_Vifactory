#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_cutout.py — Quality Gate Tests for Foreground Cutout Engine (AVF-VOX-001)."""

import pytest
from PIL import Image, ImageDraw

from vox.assets_fg import generate_fg_cutout
from vox.cutout import remove_background, verify_cutout_gates
from vox.schemas import FGObject


def test_generated_fg_cutout_passes_all_gates(tmp_path):
    fg = FGObject(
        id="retro_stamp",
        prompt="vintage wax seal stamp on textured paper",
        anchor_x=0.5,
        anchor_y=0.5,
        scale=0.5,
        depth=0.6,
        enter_at=0.5
    )
    png_path, meta = generate_fg_cutout(fg, scene_idx=1, out_dir=tmp_path)
    assert png_path.exists()
    assert meta["gate_report"]["status"] == "PASS"

    img = Image.open(png_path)
    assert img.size == (1024, 1024)
    assert img.mode == "RGBA"


def test_cutout_touching_border_fails():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw rectangle touching x=0
    draw.rectangle([0, 10, 80, 80], fill=(255, 0, 0, 255))

    with pytest.raises(ValueError) as exc:
        verify_cutout_gates(img)
    assert "Cutout Gate" in str(exc.value)


def test_cutout_completely_transparent_fails():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    with pytest.raises(ValueError) as exc:
        verify_cutout_gates(img)
    assert "Gate 1" in str(exc.value) or "Gate 4" in str(exc.value)


def test_remove_background_opaque_input_exercises_chroma_path():
    """Exercises the Chroma / Alpha falloff keyer on a fully opaque RGB input (Boss Item 7)."""
    # Create fully opaque 512x512 RGB canvas with zero existing transparency
    opaque_img = Image.new("RGB", (512, 512), (240, 235, 220))
    draw = ImageDraw.Draw(opaque_img)
    # Draw central tactile seal
    draw.ellipse([128, 128, 384, 384], fill=(180, 40, 40))

    cutout = remove_background(opaque_img)
    assert cutout.mode == "RGBA"
    assert cutout.size == (512, 512)

    # Verify mathematical cutout gates
    report = verify_cutout_gates(cutout)
    assert report["status"] == "PASS"
    assert report["solid_ratio"] >= 0.05
    assert report["soft_ratio"] >= 0.005
    assert report["border_mean"] < 0.05


def test_falsifiable_magenta_fringe_detector_catches_contaminated_swatch():
    """Falsifiable Adversarial Test (Boss Item 8 / Rule 122 Axis 2).
    Generates a synthetic swatch with magenta chroma spill (#FF00FF) on the border pixels
    and proves that the detector flags spill_ratio > 0.0 with status FAIL.
    """
    from vox.cutout import audit_magenta_fringe

    # 100x100 RGBA image
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Central subject
    draw.ellipse([20, 20, 80, 80], fill=(200, 50, 50, 255))

    # Introduce intentional magenta bleed on semi-transparent transition boundary (alpha=100)
    # Magenta in RGB: R=255, G=0, B=255 -> meets (r > 180, g < 70, b > 180)
    for x in range(25, 35):
        img.putpixel((x, 19), (255, 0, 255, 100))

    report = audit_magenta_fringe(img)
    assert report["border_pixels"] > 0
    assert report["magenta_spill_pixels"] >= 10
    assert report["spill_ratio"] > 0.0
    assert report["status"] == "FAIL"


def test_falsifiable_magenta_fringe_clean_cutout_has_zero_spill():
    """Rule 122 Axis 2: Clean foreground cutout has exactly 0.0% magenta fringe."""
    from vox.cutout import audit_magenta_fringe

    # Clean transparent image with smooth alpha edge and neutral colors (no magenta)
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, 80, 80], fill=(180, 140, 90, 255))
    # Soft non-magenta border
    for x in range(20, 80):
        img.putpixel((x, 19), (180, 140, 90, 100))

    report = audit_magenta_fringe(img)
    assert report["border_pixels"] > 0
    assert report["magenta_spill_pixels"] == 0
    assert report["spill_ratio"] == 0.0
    assert report["status"] == "PASS"

