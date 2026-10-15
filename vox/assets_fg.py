#!/usr/bin/env python3
"""vox/assets_fg.py — Foreground RGBA Object Generator & Cutout Engine (AVF-VOX-001).

Generates isolated tactical foreground cutouts:
- Target resolution: 1024x1024 RGBA PNG
- Procedural shape diversification: ledgers with folded dog-ears, notched tokens/medallions,
  heraldic crests/wax seals with ribbons, and monetary balance scales.
- Applies background removal and verifies all 4 mathematical cutout gates.
"""

from __future__ import annotations

import hashlib
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from vox.cutout import remove_background, verify_cutout_gates
from vox.schemas import FGObject


def _draw_ledger_folio(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, scale: float, rng: np.random.Generator) -> None:
    """Draws a tactile archival ledger/dossier with folded dog-ear corner and forensic stamp."""
    aspect = 0.78 + float(rng.uniform(-0.04, 0.06))
    r_w = int(w * scale * 0.44 * aspect)
    r_h = int(h * scale * 0.44 / aspect)
    fold = int(32 + rng.integers(8, 20))

    pts = [
        (cx - r_w, cy - r_h),
        (cx + r_w - fold, cy - r_h),
        (cx + r_w, cy - r_h + fold),
        (cx + r_w, cy + r_h),
        (cx - r_w, cy + r_h),
    ]
    paper_col = (int(230 + rng.integers(0, 15)), int(220 + rng.integers(0, 15)), int(195 + rng.integers(0, 20)), 255)
    ink_col = (35, 32, 28, 255)
    draw.polygon(pts, fill=paper_col, outline=ink_col, width=5)

    # Dog-ear fold flap
    flap_pts = [
        (cx + r_w - fold, cy - r_h),
        (cx + r_w, cy - r_h + fold),
        (cx + r_w - fold, cy - r_h + fold),
    ]
    flap_col = (195, 185, 160, 255)
    draw.polygon(flap_pts, fill=flap_col, outline=ink_col, width=4)

    # Ruled ledger lines
    line_y_start = cy - r_h + fold + 20
    line_y_end = cy + r_h - 25
    step = max(18, int((line_y_end - line_y_start) / 6))
    for y_pos in range(line_y_start, line_y_end, step):
        draw.line([cx - r_w + 24, y_pos, cx + r_w - 24, y_pos], fill=(130, 125, 115, 255), width=2)

    # Forensic red stamp mark
    draw.ellipse([cx - r_w + 30, cy + r_h - 85, cx - r_w + 95, cy + r_h - 25], outline=(190, 42, 42, 255), width=4)


def _draw_token_medallion(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, scale: float, rng: np.random.Generator) -> None:
    """Draws a tactile metallic token / medallion with notched gear rim and cracked relief."""
    eff_scale = max(scale, 0.35)
    r = int(min(w, h) * eff_scale * 0.44 * rng.uniform(0.96, 1.04))
    n_notches = 24
    pts = []
    for k in range(n_notches * 2):
        angle = k * math.pi / n_notches
        cur_r = r if (k % 2 == 0) else (r - 10)
        pts.append((int(cx + cur_r * math.cos(angle)), int(cy + cur_r * math.sin(angle))))

    token_col = (int(175 + rng.integers(0, 30)), int(190 + rng.integers(0, 25)), int(205 + rng.integers(0, 25)), 255)
    draw.polygon(pts, fill=token_col, outline=(30, 35, 45, 255), width=5)

    # Inner concentric rings
    draw.ellipse([cx - int(r * 0.72), cy - int(r * 0.72), cx + int(r * 0.72), cy + int(r * 0.72)], outline=(70, 80, 95, 255), width=3)
    draw.ellipse([cx - int(r * 0.42), cy - int(r * 0.42), cx + int(r * 0.42), cy + int(r * 0.42)], outline=(90, 105, 125, 255), width=2)

    # Cracked relief motif across center
    draw.line([cx - int(r * 0.45), cy - 10, cx - 8, cy + 12], fill=(25, 30, 40, 255), width=4)
    draw.line([cx - 8, cy + 12, cx + 15, cy - 6], fill=(25, 30, 40, 255), width=4)
    draw.line([cx + 15, cy - 6, cx + int(r * 0.45), cy + 15], fill=(25, 30, 40, 255), width=4)


def _draw_emblem_seal(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, scale: float, rng: np.random.Generator) -> None:
    """Draws a tactile heraldic badge / wax seal emblem with ribbon tail."""
    eff_scale = max(scale, 0.35)
    r_w = int(w * eff_scale * 0.44)
    r_h = int(h * eff_scale * 0.48)

    # Ribbon tails at bottom
    ribbon_col = (150, 30, 30, 255)
    draw.polygon([(cx - 28, cy + r_h - 15), (cx - 45, cy + r_h + 38), (cx - 12, cy + r_h + 24)], fill=ribbon_col, outline=(25, 25, 30, 255), width=3)
    draw.polygon([(cx + 28, cy + r_h - 15), (cx + 45, cy + r_h + 38), (cx + 12, cy + r_h + 24)], fill=ribbon_col, outline=(25, 25, 30, 255), width=3)

    # Shield-shaped heraldic crest
    pts = [
        (cx - r_w, cy - r_h),
        (cx + r_w, cy - r_h),
        (cx + r_w, cy + int(r_h * 0.3)),
        (cx, cy + r_h),
        (cx - r_w, cy + int(r_h * 0.3)),
    ]
    emblem_col = (int(190 + rng.integers(0, 25)), int(160 + rng.integers(0, 25)), int(80 + rng.integers(0, 25)), 255)
    draw.polygon(pts, fill=emblem_col, outline=(35, 30, 20, 255), width=5)

    # Inner shield crest
    inner_pad = 16
    inner_pts = [
        (cx - r_w + inner_pad, cy - r_h + inner_pad),
        (cx + r_w - inner_pad, cy - r_h + inner_pad),
        (cx + r_w - inner_pad, cy + int(r_h * 0.28)),
        (cx, cy + r_h - inner_pad - 4),
        (cx - r_w + inner_pad, cy + int(r_h * 0.28)),
    ]
    draw.polygon(inner_pts, outline=(120, 95, 45, 255), width=3)

    # Forensic audit star / cross motif
    draw.line([cx, cy - int(r_h * 0.4), cx, cy + int(r_h * 0.25)], fill=(40, 35, 25, 255), width=4)
    draw.line([cx - int(r_w * 0.45), cy - int(r_h * 0.1), cx + int(r_w * 0.45), cy - int(r_h * 0.1)], fill=(40, 35, 25, 255), width=4)


def _draw_scales_monetary(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, scale: float, rng: np.random.Generator) -> None:
    """Draws a tactile monetary balance scales silhouette with solid filled pans."""
    eff_scale = max(scale, 0.38)
    r_w = int(w * eff_scale * 0.44)
    r_h = int(h * eff_scale * 0.44)

    brass_col = (int(205 + rng.integers(0, 20)), int(165 + rng.integers(0, 20)), int(70 + rng.integers(0, 25)), 255)
    ink_col = (30, 28, 24, 255)

    # Base pedestal
    draw.rounded_rectangle([cx - int(r_w * 0.55), cy + r_h - 45, cx + int(r_w * 0.55), cy + r_h], radius=10, fill=brass_col, outline=ink_col, width=4)

    # Central pillar
    draw.rounded_rectangle([cx - 22, cy - r_h + 30, cx + 22, cy + r_h - 20], radius=8, fill=brass_col, outline=ink_col, width=4)

    # Crossbeam
    beam_y = cy - int(r_h * 0.45)
    draw.rounded_rectangle([cx - r_w, beam_y - 12, cx + r_w, beam_y + 12], radius=6, fill=brass_col, outline=ink_col, width=4)

    # Left pan hanging strings & solid pan
    left_x = cx - r_w + 25
    draw.line([left_x, beam_y + 12, left_x - 38, beam_y + 90], fill=ink_col, width=3)
    draw.line([left_x, beam_y + 12, left_x + 38, beam_y + 90], fill=ink_col, width=3)
    draw.polygon([
        (left_x - 48, beam_y + 90),
        (left_x + 48, beam_y + 90),
        (left_x + 32, beam_y + 125),
        (left_x - 32, beam_y + 125),
    ], fill=brass_col, outline=ink_col, width=4)

    # Right pan hanging strings & solid pan
    right_x = cx + r_w - 25
    draw.line([right_x, beam_y + 12, right_x - 38, beam_y + 90], fill=ink_col, width=3)
    draw.line([right_x, beam_y + 12, right_x + 38, beam_y + 90], fill=ink_col, width=3)
    draw.polygon([
        (right_x - 48, beam_y + 90),
        (right_x + 48, beam_y + 90),
        (right_x + 32, beam_y + 125),
        (right_x - 32, beam_y + 125),
    ], fill=brass_col, outline=ink_col, width=4)


def generate_fg_cutout(
    fg_obj: FGObject,
    scene_idx: int,
    out_dir: Path,
    target_wh: tuple[int, int] = (1024, 1024),
) -> tuple[Path, dict[str, Any]]:
    """Generates an isolated tactile foreground object cutout PNG with verified alpha."""
    start_ts = time.time()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fg_{scene_idx:02d}_{fg_obj.id}.png"

    prompt_hash = hashlib.sha256(fg_obj.prompt.encode("utf-8")).hexdigest()[:12]
    seed = int(prompt_hash, 16) % (2**31)

    w, h = target_wh
    rng = np.random.default_rng(seed)

    # 1. Synthesize stylized tactile editorial subject on transparent canvas
    base_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base_img)
    cx, cy = w // 2, h // 2

    prompt_lower = fg_obj.prompt.lower()
    # Check ledgers/documents first so "balance sheet" is handled as a ledger
    if any(k in prompt_lower for k in ["ledger", "folio", "dossier", "document", "treaty"]):
        _draw_ledger_folio(draw, cx, cy, w, h, fg_obj.scale, rng)
    elif any(k in prompt_lower for k in ["token", "medallion", "coin"]):
        _draw_token_medallion(draw, cx, cy, w, h, fg_obj.scale, rng)
    elif any(k in prompt_lower for k in ["emblem", "badge", "seal"]):
        _draw_emblem_seal(draw, cx, cy, w, h, fg_obj.scale, rng)
    elif any(k in prompt_lower for k in ["scales", "balance"]):
        _draw_scales_monetary(draw, cx, cy, w, h, fg_obj.scale, rng)
    else:
        _draw_ledger_folio(draw, cx, cy, w, h, fg_obj.scale, rng)

    # 2. Extract clean alpha cutout with anti-aliasing
    cutout_img = remove_background(base_img)

    # 3. Verify all 4 mathematical cutout gates
    gate_report = verify_cutout_gates(cutout_img)

    # 4. Save PNG
    cutout_img.save(str(out_path), format="PNG")

    latency_sec = round(time.time() - start_ts, 3)
    meta = {
        "file": str(out_path),
        "scene_idx": scene_idx,
        "fg_id": fg_obj.id,
        "generator_model": "vox_tactile_cutout_v1",
        "provider": "vox_native_papercraft",
        "request_id": f"req_fg_{prompt_hash}_{int(start_ts)}",
        "render_latency_sec": latency_sec,
        "prompt_hash": prompt_hash,
        "seed": seed,
        "gate_report": gate_report,
    }

    return out_path, meta
