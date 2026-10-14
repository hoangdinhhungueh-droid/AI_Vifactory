#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/assets_fg.py — Foreground RGBA Object Generator & Cutout Engine (AVF-VOX-001).

Generates isolated tactical foreground cutouts:
- Target resolution: 1024x1024 RGBA PNG
- Applies background removal and runs verify_cutout_gates
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw
import numpy as np

from vox.schemas import FGObject
from vox.cutout import remove_background, verify_cutout_gates


def generate_fg_cutout(
    fg_obj: FGObject,
    scene_idx: int,
    out_dir: Path,
    target_wh: Tuple[int, int] = (1024, 1024),
) -> Tuple[Path, Dict[str, Any]]:
    """Generates an isolated tactile foreground object cutout PNG with verified alpha.
    
    Args:
        fg_obj: FGObject definition with prompt and geometry.
        scene_idx: Scene index.
        out_dir: Output directory.
        target_wh: Resolution (1024, 1024).
        
    Returns:
        Tuple of (output PNG path, metadata dict).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fg_{scene_idx:02d}_{fg_obj.id}.png"

    prompt_hash = hashlib.sha256(fg_obj.prompt.encode("utf-8")).hexdigest()[:12]
    seed = int(prompt_hash, 16) % (2**31)

    w, h = target_wh
    rng = np.random.default_rng(seed)

    # 1. Synthesize stylized tactile editorial subject
    base_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base_img)

    cx, cy = w // 2, h // 2
    r_w = int(w * fg_obj.scale * 0.45)
    r_h = int(h * fg_obj.scale * 0.45)

    # Draw tactile textured object (e.g. stamp, document, token, gavel, currency)
    col = tuple(rng.integers(150, 240, size=3, dtype=int)) + (255,)
    draw.rounded_rectangle([cx - r_w, cy - r_h, cx + r_w, cy + r_h], radius=24, fill=col, outline=(30, 30, 40, 255), width=6)
    
    # Internal graphic lines
    draw.line([cx - r_w + 30, cy, cx + r_w - 30, cy], fill=(30, 30, 40, 255), width=4)
    draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], outline=(200, 40, 40, 255), width=5)

    # 2. Extract clean alpha cutout with anti-aliasing
    cutout_img = remove_background(base_img)

    # 3. Verify all 4 mathematical cutout gates
    gate_report = verify_cutout_gates(cutout_img)

    # 4. Save PNG
    cutout_img.save(str(out_path), format="PNG")

    meta = {
        "file": str(out_path),
        "scene_idx": scene_idx,
        "fg_id": fg_obj.id,
        "prompt_hash": prompt_hash,
        "seed": seed,
        "gate_report": gate_report
    }

    return out_path, meta
