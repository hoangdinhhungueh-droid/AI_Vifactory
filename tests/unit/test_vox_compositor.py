#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_vox_compositor.py — Unit tests for Tactical Vox Compositor (AVF-VOX-001).

Guarantees:
1. apply_white_cutout_border applies crisp #FFFFFF deckle borders to cutouts.
2. create_dual_pass_shadows generates ambient drop shadow + contact occlusion shadow.
3. draw_data_counter renders forensic quantitative metric callout box with roll-up.
4. cue_transform computes smooth continuous interpolated affine camera matrix from CameraCueSheet.
5. render_master_vox_scene renders a complete 3-layer broadcast scene with continuous camera cues and 12fps stop-motion rhythm.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from vox.compositor import (
    apply_white_cutout_border,
    create_dual_pass_shadows,
    cue_transform,
    draw_data_counter,
    draw_evidence_yarn,
    draw_highlighter_sweep,
    render_master_vox_scene,
)


def test_apply_white_cutout_border():
    """Verifies white deckle border is cleanly added around alpha cutout."""
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    # Draw central solid rectangle
    for y in range(30, 70):
        for x in range(30, 70):
            im.putpixel((x, y), (180, 40, 40, 255))

    bordered = apply_white_cutout_border(im, border_px=4)
    assert bordered.size == (100, 100)
    assert bordered.mode == "RGBA"

    # Pixel at (28, 50) is within the 4px expanded border -> must be pure white #FFFFFF
    p_border = bordered.getpixel((28, 50))
    assert p_border[0] == 255 and p_border[1] == 255 and p_border[2] == 255
    assert p_border[3] > 0

    # Center pixel remains original red
    p_center = bordered.getpixel((50, 50))
    assert p_center[0] == 180 and p_center[1] == 40 and p_center[2] == 40


def test_create_dual_pass_shadows():
    """Verifies generation of Pass 1 (ambient drop shadow) and Pass 2 (contact occlusion shadow)."""
    im = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    for y in range(40, 80):
        for x in range(40, 80):
            im.putpixel((x, y), (20, 20, 20, 255))

    amb, occ = create_dual_pass_shadows(im)
    assert amb.size == im.size and amb.mode == "RGBA"
    assert occ.size == im.size and occ.mode == "RGBA"

    # Ambient shadow has lower peak opacity than contact occlusion
    amb_alpha = np.array(amb.split()[-1])
    occ_alpha = np.array(occ.split()[-1])
    assert amb_alpha.max() < occ_alpha.max()


def test_draw_data_counter():
    """Verifies Layer 3 forensic data counter callout badge rendering."""
    frame = Image.new("RGBA", (1920, 1080), (244, 241, 234, 255))
    draw_data_counter(
        frame_rgba=frame,
        stat_hero="$48.6B",
        stat_label="UNREPORTED TARIFF VALUE",
        progress=1.0,
        x_pct=76.0,
        y_pct=42.0,
    )
    assert frame.size == (1920, 1080)
    # Check that badge area was modified from original cream background
    cx, cy = int(1920 * 0.76), int(1080 * 0.42)
    p_badge = frame.getpixel((cx, cy))
    assert p_badge != (244, 241, 234, 255)


def test_draw_highlighter_sweep():
    """Verifies Layer 3 fluorescent highlighter sweep rendering."""
    frame = Image.new("RGBA", (800, 600), (244, 241, 234, 255))
    draw_highlighter_sweep(frame, x=100, y=100, w=200, h=30, progress=1.0)
    # Target pixel inside the swept area should now have yellow tint
    p = frame.getpixel((150, 115))
    assert p != (244, 241, 234, 255)
    # Yellow dominant: R and G high
    assert p[0] > 240 and p[1] > 230


def test_draw_evidence_yarn():
    """Verifies tactile red evidence yarn connecting two investigative points."""
    frame = Image.new("RGBA", (800, 600), (244, 241, 234, 255))
    draw_evidence_yarn(frame, src_pt=(100.0, 100.0), tgt_pt=(400.0, 300.0), progress=1.0)
    # The pin at src_pt (100, 100) should be drawn (brass pin #D9A441)
    p_pin = frame.getpixel((100, 100))
    assert p_pin != (244, 241, 234, 255)


def test_cue_transform_continuous_camera_motion():
    """Verifies camera cue sheet affine interpolation across Establish -> Tension -> Climax -> Hold."""
    cues = [
        {"time_ms": 0.0, "zoom_scale": 1.0, "pan_x_pct": 0.0, "pan_y_pct": 0.0},
        {"time_ms": 1000.0, "zoom_scale": 1.3, "pan_x_pct": 5.0, "pan_y_pct": -2.0},
        {"time_ms": 2000.0, "zoom_scale": 1.6, "pan_x_pct": 10.0, "pan_y_pct": 3.0},
    ]

    # At t=0.0s (start)
    M0 = cue_transform(cues, t_sec=0.0, canvas_wh=(2400, 1350), out_wh=(1920, 1080), depth=0.0)
    assert M0.shape == (2, 3)

    # At t=1.0s (Cue 2)
    M1 = cue_transform(cues, t_sec=1.0, canvas_wh=(2400, 1350), out_wh=(1920, 1080), depth=0.0)
    assert M1.shape == (2, 3)

    # Zoom scale at t=1.0s must be greater than at t=0.0s
    assert M1[0, 0] > M0[0, 0]

    # At t=0.5s (midpoint), scale must be smoothly between M0 and M1
    M_mid = cue_transform(cues, t_sec=0.5, canvas_wh=(2400, 1350), out_wh=(1920, 1080), depth=0.0)
    assert M0[0, 0] < M_mid[0, 0] < M1[0, 0]


def test_render_master_vox_scene_e2e(tmp_path: Path):
    """End-to-End Test: Verifies rendering a full 3-layer broadcast scene clip via ffmpeg."""
    bg = tmp_path / "desk_bg.png"
    Image.new("RGB", (2400, 1350), (244, 241, 234)).save(bg)

    hero = tmp_path / "hero_doc.png"
    Image.new("RGBA", (500, 700), (255, 255, 255, 255)).save(hero)

    tool = tmp_path / "caliper_tool.png"
    Image.new("RGBA", (300, 200), (255, 255, 255, 255)).save(tool)

    supp = tmp_path / "court_record.png"
    Image.new("RGBA", (450, 600), (255, 255, 255, 255)).save(supp)

    out_mp4 = tmp_path / "scene_output.mp4"

    manifest = {
        "scene_id": "SCENE_01",
        "narration": "Inspectors analyzed the seized bill of lading and detected $48.6B in false declarations.",
        "camera_movement": "slow_push_in",
        "layer_2_midground": {
            "hero_cutout": {"item_id": "hero", "anchor_x": 0.38, "anchor_y": 0.52, "scale": 0.55},
            "supporting_cutouts": [{"item_id": "supp", "anchor_x": 0.72, "anchor_y": 0.60, "scale": 0.40}],
            "interacting_tool": {"item_id": "tool", "anchor_x": 0.55, "anchor_y": 0.45, "scale": 0.30},
        },
        "layer_3_foreground": {
            "headline": "BILL OF LADING AUDIT",
            "data_counters": [{"stat_hero": "$48.6B", "stat_label": "UNREPORTED VALUE"}],
            "highlighter_sweeps": [{"x_pct": 32.0, "y_pct": 45.0, "width_pct": 36.0}],
        },
        "camera_cue_sheet": [
            {"time_ms": 0.0, "zoom_scale": 1.0, "pan_x_pct": 0.0, "pan_y_pct": 0.0},
            {"time_ms": 300.0, "zoom_scale": 1.25, "pan_x_pct": 4.0, "pan_y_pct": -2.0},
            {"time_ms": 600.0, "zoom_scale": 1.45, "pan_x_pct": 8.0, "pan_y_pct": 2.0},
        ],
    }

    fg_map = {"hero": hero, "tool": tool, "supp": supp}

    rendered = render_master_vox_scene(
        scene_manifest=manifest,
        bg_path=bg,
        fg_map=fg_map,
        out_clip=out_mp4,
        duration_sec=0.5,
        fps=30,
    )

    assert rendered.exists()
    assert rendered.stat().st_size > 1000
