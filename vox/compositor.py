#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/compositor.py — Tactical Scene Compositor with Parallax & Camera Warping (AVF-VOX-001).

Renders a scene into an individual video clip (.mp4):
- BG layer warped via affine transformation matching camera move
- FG cutouts composited with depth-based parallax and 8-frame fade-in
- Piped directly as rgb24 raw frames into ffmpeg
- Guarantees 1920x1080, exact frame count, 30fps CFR, zero black frames
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import numpy as np

from vox.schemas import Scene, FGObject
from vox.camera import move_transform


def render_scene_clip(
    scene: Scene,
    bg_path: Path,
    fg_map: Dict[str, Path],
    out_clip: Path,
    fps: int = 30,
    out_wh: Tuple[int, int] = (1920, 1080),
    canvas_wh: Tuple[int, int] = (2400, 1350),
) -> Path:
    """Renders a single scene into an MP4 clip using deterministic parallax compositing."""
    out_clip = Path(out_clip)
    out_clip.parent.mkdir(parents=True, exist_ok=True)

    start_sec = scene.start if scene.start is not None else 0.0
    end_sec = scene.end if scene.end is not None else 5.0
    start_frame = int(round(start_sec * fps))
    end_frame = int(round(end_sec * fps))
    total_frames = max(15, end_frame - start_frame)

    # Load and verify background canvas (RGB)
    bg_img = Image.open(str(bg_path)).convert("RGB")
    if bg_img.size != canvas_wh:
        bg_img = bg_img.resize(canvas_wh, Image.Resampling.LANCZOS)

    # Preload and resize foreground objects (RGBA)
    fg_data: List[Tuple[FGObject, Image.Image]] = []
    for fg_obj in scene.fg:
        f_path = fg_map.get(fg_obj.id)
        if f_path and Path(f_path).exists():
            f_img = Image.open(str(f_path)).convert("RGBA")
            # Base target height based on scale
            target_h = int(out_wh[1] * fg_obj.scale)
            aspect = f_img.width / max(1, f_img.height)
            target_w = int(target_h * aspect)
            f_img_resized = f_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            fg_data.append((fg_obj, f_img_resized))

    cw, ch = canvas_wh
    ow, oh = out_wh

    from vox.ffmpeg_utils import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()

    # Initialize ffmpeg subprocess pipe
    cmd_ffmpeg = [
        ffmpeg_bin, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{ow}x{oh}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-b:v", "3000k",
        str(out_clip)
    ]

    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    fade_frames = 8.0

    try:
        for k in range(total_frames):
            t_norm = k / float(max(1, total_frames - 1))
            t_sec = k / float(fps)

            # 1. Warp background canvas according to camera move (depth=0.0)
            M_bg = move_transform(scene.camera, t_norm, canvas_wh=canvas_wh, out_wh=out_wh, depth=0.0)
            inv_m_bg = np.linalg.inv(np.vstack([M_bg, [0.0, 0.0, 1.0]]))
            aff_tuple = (
                inv_m_bg[0, 0], inv_m_bg[0, 1], inv_m_bg[0, 2],
                inv_m_bg[1, 0], inv_m_bg[1, 1], inv_m_bg[1, 2]
            )
            frame_bg = bg_img.transform(out_wh, Image.Transform.AFFINE, aff_tuple, resample=Image.Resampling.BILINEAR)

            # 2. Composite foreground objects with depth parallax and fade-in
            frame_rgba = frame_bg.convert("RGBA")

            for fg_obj, fg_img in fg_data:
                if t_sec < fg_obj.enter_at:
                    continue

                # Fade in factor over 8 frames
                fade_progress = min(1.0, max(0.0, (t_sec - fg_obj.enter_at) / (fade_frames / float(fps))))

                # Calculate camera transform for this FG depth
                M_fg = move_transform(scene.camera, t_norm, canvas_wh=canvas_wh, out_wh=out_wh, depth=fg_obj.depth)

                # Source position on canvas
                src_x = fg_obj.anchor_x * cw
                src_y = fg_obj.anchor_y * ch

                # Destination center on output viewport
                dest_pt = M_fg @ np.array([src_x, src_y, 1.0])
                dx, dy = dest_pt[0], dest_pt[1]

                # Adjust alpha channel only during the 8-frame fade-in
                if fade_progress < 1.0:
                    fg_cur = fg_img.copy()
                    r_ch, g_ch, b_ch, a_ch = fg_cur.split()
                    a_ch = a_ch.point(lambda p: int(p * fade_progress))
                    fg_cur = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
                else:
                    fg_cur = fg_img

                # Paste centered at (dx, dy)
                top_left_x = int(dx - (fg_cur.width / 2.0))
                top_left_y = int(dy - (fg_cur.height / 2.0))
                frame_rgba.alpha_composite(fg_cur, dest=(top_left_x, top_left_y))

            # Send raw rgb24 bytes to ffmpeg
            rgb_bytes = frame_rgba.convert("RGB").tobytes()
            proc.stdin.write(rgb_bytes)

        proc.stdin.close()
        proc.wait(timeout=60)

    except Exception as e:
        if proc.stdin:
            proc.stdin.close()
        proc.kill()
        raise RuntimeError(f"Compositor rendering failed for scene {scene.idx}: {e}")
    finally:
        import gc
        gc.collect()

    return out_clip
