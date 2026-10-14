#!/usr/bin/env python3
"""vox/camera.py — Pure Mathematical 12-Move Camera & Parallax Transform Engine (AVF-VOX-001).

Implements deterministic 2x3 affine transformation matrices for:
- 12 tactile camera motion moves
- Strict canvas boundary safety constraints (|dx| <= (s - 1) / (2s))
- Parallax depth scaling (1.0 + depth * 0.6)
- Smooth cubic easing (ease_in_out_cubic)
"""

from __future__ import annotations

import math

import numpy as np

from vox.schemas import CameraMove


def ease_in_out_cubic(t: float) -> float:
    """Standard cubic ease-in-out function for organic editorial motion."""
    t = max(0.0, min(1.0, float(t)))
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        f = (2.0 * t) - 2.0
        return 0.5 * (f * f * f) + 1.0


def move_transform(
    move: CameraMove,
    t_norm: float,
    canvas_wh: tuple[int, int] = (2400, 1350),
    out_wh: tuple[int, int] = (1920, 1080),
    depth: float = 0.0,
) -> np.ndarray:
    """Computes a 2x3 affine matrix mapping canvas coordinates to output viewport coordinates.

    Args:
        move: One of the 12 CameraMove enums.
        t_norm: Normalized timeline progress [0.0, 1.0].
        canvas_wh: Dimensions (width, height) of the source overscan canvas.
        out_wh: Dimensions (width, height) of the target output viewport.
        depth: Foreground object depth [0.0 = BG anchor, 1.0 = camera plane].

    Returns:
        np.ndarray of shape (2, 3), float64.
    """
    cw, ch = canvas_wh
    ow, oh = out_wh
    t = ease_in_out_cubic(t_norm)

    # Base scale ratio between canvas and target output (e.g. 1920 / 2400 = 0.8)
    base_s = ow / cw

    # Parallax multiplier for depth
    p_factor = 1.0 + (max(0.0, min(1.0, depth)) * 0.6)

    # Determine move specific zoom (s) and relative offset (dx, dy, angle_rad)
    zoom = 1.0
    dx_rel = 0.0
    dy_rel = 0.0
    angle_rad = 0.0

    if move == CameraMove.STATIC_BREATH:
        # Subtle breath zoom: 1.00 -> 1.03
        zoom = 1.00 + (0.025 * t)

    elif move == CameraMove.PUSH_IN:
        # Editorial push in: 1.00 -> 1.18
        zoom = 1.00 + (0.18 * t)

    elif move == CameraMove.PULL_OUT:
        # Editorial pull out: 1.18 -> 1.00
        zoom = 1.18 - (0.18 * t)

    elif move == CameraMove.PAN_LEFT:
        # Pan left: viewport shifts from center-right to center-left
        zoom = 1.15
        dx_rel = (0.04 - (0.08 * t)) * p_factor

    elif move == CameraMove.PAN_RIGHT:
        # Pan right: viewport shifts from center-left to center-right
        zoom = 1.15
        dx_rel = (-0.04 + (0.08 * t)) * p_factor

    elif move == CameraMove.TILT_UP:
        zoom = 1.15
        dy_rel = (0.04 - (0.08 * t)) * p_factor

    elif move == CameraMove.TILT_DOWN:
        zoom = 1.15
        dy_rel = (-0.04 + (0.08 * t)) * p_factor

    elif move == CameraMove.KEN_BURNS_TL_BR:
        # Zoom in while traveling from Top-Left to Bottom-Right
        zoom = 1.05 + (0.12 * t)
        dx_rel = (-0.03 + (0.06 * t)) * p_factor
        dy_rel = (-0.03 + (0.06 * t)) * p_factor

    elif move == CameraMove.KEN_BURNS_BR_TL:
        # Zoom out while traveling from Bottom-Right to Top-Left
        zoom = 1.17 - (0.12 * t)
        dx_rel = (0.03 - (0.06 * t)) * p_factor
        dy_rel = (0.03 - (0.06 * t)) * p_factor

    elif move == CameraMove.PARALLAX_LEFT:
        zoom = 1.15
        dx_rel = (0.05 - (0.10 * t)) * p_factor

    elif move == CameraMove.PARALLAX_RIGHT:
        zoom = 1.15
        dx_rel = (-0.05 + (0.10 * t)) * p_factor

    elif move == CameraMove.ROLL_PUSH:
        # Zoom 1.06 -> 1.18 + subtle tactile tilt +- 1.0 deg (corners strictly inside canvas)
        zoom = 1.06 + (0.12 * t)
        angle_deg = -1.0 + (2.0 * t)
        angle_rad = math.radians(angle_deg)

    # Mathematical safety clamp: Ensure viewport corners stay strictly within overscan canvas
    # Canvas is overscanned relative to base_s. The maximum allowable relative shift is:
    # (cw - (ow / (base_s * zoom))) / (2 * cw)
    max_dx = max(0.0, (cw - (ow / (base_s * zoom))) / (2.0 * cw))
    max_dy = max(0.0, (ch - (oh / (base_s * zoom))) / (2.0 * ch))

    dx_clamped = max(-max_dx, min(max_dx, dx_rel))
    dy_clamped = max(-max_dy, min(max_dy, dy_rel))

    # Center of canvas and center of viewport
    cx = cw / 2.0
    cy = ch / 2.0
    ox = ow / 2.0
    oy = oh / 2.0

    # Total scale applied
    s = base_s * zoom

    # Construct affine matrix mapping (x, y) in canvas to (u, v) in output viewport:
    # 1. Translate canvas center to origin (-cx - dx_clamped*cw, -cy - dy_clamped*ch)
    # 2. Rotate by angle_rad
    # 3. Scale by s
    # 4. Translate to output viewport center (+ox, +oy)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    tx_src = cx + (dx_clamped * cw)
    ty_src = cy + (dy_clamped * ch)

    # Combined 2x3 matrix:
    # [ u ] = [ s*cos_a  -s*sin_a   ox - s*(cos_a*tx_src - sin_a*ty_src) ] [ x ]
    # [ v ]   [ s*sin_a   s*cos_a   oy - s*(sin_a*tx_src + cos_a*ty_src) ] [ y ]
    m00 = s * cos_a
    m01 = -s * sin_a
    m02 = ox - (s * (cos_a * tx_src - sin_a * ty_src))

    m10 = s * sin_a
    m11 = s * cos_a
    m12 = oy - (s * (sin_a * tx_src + cos_a * ty_src))

    return np.array([
        [m00, m01, m02],
        [m10, m11, m12]
    ], dtype=np.float64)
