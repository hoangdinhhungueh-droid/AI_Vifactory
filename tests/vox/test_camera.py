#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_camera.py — Mathematical Invariant Tests for Camera Engine (AVF-VOX-001)."""

import pytest
import numpy as np
from vox.schemas import CameraMove
from vox.camera import move_transform


CANVAS_WH = (2400, 1350)
OUT_WH = (1920, 1080)
SAMPLES = 60


@pytest.mark.parametrize("move", list(CameraMove))
def test_camera_viewport_corners_within_canvas(move: CameraMove):
    """Verifies that all 4 viewport corners map inversely into the overscan canvas with 0 violations."""
    cw, ch = CANVAS_WH
    ow, oh = OUT_WH
    viewport_corners = np.array([
        [0.0, 0.0, 1.0],
        [ow, 0.0, 1.0],
        [ow, oh, 1.0],
        [0.0, oh, 1.0]
    ])  # 4x3 homogeneous

    for i in range(SAMPLES):
        t = i / (SAMPLES - 1)
        # Check BG (depth=0.0) and FG (depth=1.0)
        for depth in (0.0, 0.5, 1.0):
            M = move_transform(move, t, canvas_wh=CANVAS_WH, out_wh=OUT_WH, depth=depth)
            # Invert 2x3 affine matrix to map viewport -> canvas
            M_homo = np.vstack([M, [0.0, 0.0, 1.0]])
            M_inv = np.linalg.inv(M_homo)

            # Map corners to canvas coordinates
            src_corners = (M_inv @ viewport_corners.T).T  # 4x3

            for pt in src_corners:
                x, y = pt[0], pt[1]
                # Allow a tiny numerical epsilon tolerance of 0.5px
                assert -0.5 <= x <= cw + 0.5, f"Move {move.value} at t={t} x={x} exceeds canvas width {cw}"
                assert -0.5 <= y <= ch + 0.5, f"Move {move.value} at t={t} y={y} exceeds canvas height {ch}"


@pytest.mark.parametrize("move", list(CameraMove))
def test_camera_motion_smoothness_and_differentiation(move: CameraMove):
    """Verifies that frame 0 and frame 1 differ, and no consecutive frame jumps > 1.5% frame width."""
    ow, oh = OUT_WH
    center_pt = np.array([ow / 2.0, oh / 2.0, 1.0])

    M0 = move_transform(move, 0.0, canvas_wh=CANVAS_WH, out_wh=OUT_WH)
    M1 = move_transform(move, 1.0, canvas_wh=CANVAS_WH, out_wh=OUT_WH)

    # Verify frame 0 and 1 differ
    diff_norm = np.linalg.norm(M1 - M0)
    assert diff_norm > 1e-4, f"Move {move.value} shows zero motion between t=0 and t=1"

    # For STATIC_BREATH, verify zoom delta >= 0.02
    if move == CameraMove.STATIC_BREATH:
        # Compare scaling factor from matrix norm
        scale0 = np.linalg.norm(M0[:, 0])
        scale1 = np.linalg.norm(M1[:, 0])
        zoom_delta = abs(scale1 - scale0) / scale0
        assert zoom_delta >= 0.02, f"STATIC_BREATH zoom delta {zoom_delta:.4f} < 0.02"

    # Verify smooth continuity across all 60 frames (no jumps > 1.5% of width = 28.8px)
    max_jump_allowed = 0.015 * ow
    prev_src_center = None

    for i in range(SAMPLES):
        t = i / (SAMPLES - 1)
        M = move_transform(move, t, canvas_wh=CANVAS_WH, out_wh=OUT_WH)
        M_homo = np.vstack([M, [0.0, 0.0, 1.0]])
        src_center = (np.linalg.inv(M_homo) @ center_pt)[:2]

        if prev_src_center is not None:
            step_jump = np.linalg.norm(src_center - prev_src_center)
            assert step_jump <= max_jump_allowed, f"Move {move.value} step jump {step_jump:.2f}px > {max_jump_allowed}px at t={t}"

        prev_src_center = src_center
