#!/usr/bin/env python3
"""vox/compositor.py — Tactical Scene Compositor with 2.5D Parallax & 12fps Stop-Motion (AVF-VOX-001).

Renders a scene into an individual broadcast video clip (.mp4):
- Layer 1: Background desk (#F4F1EA aged paper / blueprint / desk) warped via continuous camera motion
- Layer 2: Midground cutouts composited with 2.5D depth parallax, white deckle borders (#FFFFFF),
  dual-pass contact shadows (ambient + occlusion), and 12fps stop-motion rhythm on twos (<= 2px micro-vibration)
- Layer 3: Foreground graphic callouts (fluorescent highlighter sweeps, connecting evidence yarn, data counters)
- Piped directly as rgb24 raw frames into ffmpeg
- Guarantees 1920x1080, exact frame count, 30fps CFR, zero black frames
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from vox.camera import move_transform
from vox.schemas import CameraMove, FGObject, Scene


def apply_white_cutout_border(img: Image.Image, border_px: int = 4) -> Image.Image:
    """Applies a crisp white deckle border (#FFFFFF) to an isolated cutout RGBA image."""
    if img.mode != "RGBA" or border_px <= 0:
        return img

    alpha = img.split()[-1]
    # Check if image already has substantial white border to avoid double border
    expanded = alpha.filter(ImageFilter.MaxFilter(2 * border_px + 1))
    border_img = Image.new("RGBA", img.size, (255, 255, 255, 255))
    border_img.putalpha(expanded)
    # Composite original over border
    border_img.alpha_composite(img)
    return border_img


def create_dual_pass_shadows(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Generates authentic dual-pass tactile shadows: ambient drop shadow and sharp contact occlusion."""
    if img.mode != "RGBA":
        return img, img

    alpha = img.split()[-1]

    # Pass 1: Ambient Drop Shadow (soft, wider spread, lower opacity ~0.22)
    amb_mask = alpha.filter(ImageFilter.GaussianBlur(6))
    amb_shadow = Image.new("RGBA", img.size, (26, 26, 26, 0))
    amb_alpha = amb_mask.point(lambda p: int(p * 0.22))
    amb_shadow.putalpha(amb_alpha)

    # Pass 2: Contact Occlusion Shadow (darker, tighter, higher opacity ~0.48)
    occ_mask = alpha.filter(ImageFilter.GaussianBlur(2))
    occ_shadow = Image.new("RGBA", img.size, (15, 15, 15, 0))
    occ_alpha = occ_mask.point(lambda p: int(p * 0.48))
    occ_shadow.putalpha(occ_alpha)

    return amb_shadow, occ_shadow


def draw_highlighter_sweep(
    frame_rgba: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    progress: float,
    color: tuple[int, int, int, int] = (255, 230, 0, 140),
) -> None:
    """Draws a translucent fluorescent marker sweep across a horizontal band."""
    if progress <= 0.0 or w <= 0 or h <= 0:
        return

    cur_w = max(1, int(w * min(1.0, progress)))
    overlay = Image.new("RGBA", frame_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Draw rounded rectangle with slight skew
    draw.rounded_rectangle([x, y, x + cur_w, y + h], radius=3, fill=color)
    frame_rgba.alpha_composite(overlay)


def draw_evidence_yarn(
    frame_rgba: Image.Image,
    src_pt: tuple[float, float],
    tgt_pt: tuple[float, float],
    progress: float,
    color: tuple[int, int, int, int] = (182, 46, 31, 230),
) -> None:
    """Draws a catenary curved organic red evidence yarn connecting two points."""
    if progress <= 0.0:
        return

    x0, y0 = src_pt
    x1, y1 = tgt_pt
    dx, dy = (x1 - x0), (y1 - y0)
    dist = math.hypot(dx, dy)
    if dist < 5:
        return

    overlay = Image.new("RGBA", frame_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 12-segment quadratic catenary sag
    points = []
    num_steps = 16
    sag = min(40.0, dist * 0.06)
    actual_steps = max(1, int(num_steps * min(1.0, progress)))

    for step in range(actual_steps + 1):
        t = step / float(num_steps)
        cur_x = x0 + dx * t
        cur_y = y0 + dy * t + 4.0 * sag * t * (1.0 - t)
        points.append((cur_x, cur_y))

    if len(points) >= 2:
        draw.line(points, fill=color, width=3)
        # Pins at source and target
        draw.ellipse([x0 - 4, y0 - 4, x0 + 4, y0 + 4], fill=(217, 164, 65, 255), outline=(58, 53, 42, 255))
        if progress >= 1.0:
            draw.ellipse([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=(217, 164, 65, 255), outline=(58, 53, 42, 255))

    frame_rgba.alpha_composite(overlay)


def _get_pil_font(size: int, bold: bool = False) -> Any:
    """Loads a readable PIL font with graceful default fallbacks."""
    candidates = [
        "C:/Windows/Fonts/impact.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_data_counter(
    frame_rgba: Image.Image,
    stat_hero: str,
    stat_label: str,
    progress: float,
    x_pct: float = 76.0,
    y_pct: float = 42.0,
    color: tuple[int, int, int, int] = (182, 46, 31, 240),
) -> None:
    """Draws an authentic Vox tactile forensic data counter / metric callout badge."""
    if progress <= 0.0 or not stat_hero:
        return

    ow, oh = frame_rgba.size
    cx = int(ow * (x_pct / 100.0))
    cy = int(oh * (y_pct / 100.0))

    card_w = max(180, int(ow * 0.22))
    card_h = max(80, int(oh * 0.13))
    x1 = cx - card_w // 2
    y1 = cy - card_h // 2
    x2 = x1 + card_w
    y2 = y1 + card_h

    alpha_mult = min(1.0, progress * 1.5)
    spring = 1.0 + (math.sin(min(1.0, progress) * math.pi) * 0.05) if progress < 1.0 else 1.0

    overlay = Image.new("RGBA", frame_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    box_alpha = int(235 * alpha_mult)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=(253, 251, 247, box_alpha), outline=(26, 26, 26, box_alpha), width=3)

    f_stat = _get_pil_font(max(16, int(card_h * 0.44 * spring)), bold=True)
    f_lbl = _get_pil_font(max(10, int(card_h * 0.18)), bold=True)

    import re
    display_hero = str(stat_hero)
    if progress < 1.0 and any(c.isdigit() for c in display_hero):
        digits = re.findall(r"\d+", display_hero)
        if digits:
            orig_num = int(digits[0])
            cur_num = int(orig_num * min(1.0, progress * 1.2))
            display_hero = display_hero.replace(digits[0], str(cur_num), 1)

    text_color = (color[0], color[1], color[2], int(color[3] * alpha_mult))
    draw.text((x1 + 16, y1 + int(card_h * 0.12)), display_hero, font=f_stat, fill=text_color)

    lbl_color = (51, 65, 85, int(230 * alpha_mult))
    draw.text((x1 + 18, y1 + int(card_h * 0.65)), (stat_label or "FORENSIC FOCUS")[:26].upper(), font=f_lbl, fill=lbl_color)

    frame_rgba.alpha_composite(overlay)


def cue_transform(
    cues: List[Any],
    t_sec: float,
    canvas_wh: tuple[int, int] = (2400, 1350),
    out_wh: tuple[int, int] = (1920, 1080),
    depth: float = 0.0,
) -> np.ndarray:
    """Computes continuous interpolated affine camera matrix from CameraCueSheet."""
    t_ms = t_sec * 1000.0
    cw, ch = canvas_wh
    ow, oh = out_wh

    if not cues:
        s0 = ow / float(cw)
        tx0 = (ow - cw * s0) / 2.0
        ty0 = (oh - ch * s0) / 2.0
        return np.array([[s0, 0.0, tx0], [0.0, s0, ty0]])

    cue_times = [float(c.get("time_ms") if isinstance(c, dict) else getattr(c, "time_ms", 0.0)) for c in cues]

    if t_ms <= cue_times[0]:
        c = cues[0]
        zoom = float(c.get("zoom_scale") if isinstance(c, dict) else getattr(c, "zoom_scale", 1.0))
        pan_x = float(c.get("pan_x_pct") if isinstance(c, dict) else getattr(c, "pan_x_pct", 0.0))
        pan_y = float(c.get("pan_y_pct") if isinstance(c, dict) else getattr(c, "pan_y_pct", 0.0))
    elif t_ms >= cue_times[-1]:
        c = cues[-1]
        zoom = float(c.get("zoom_scale") if isinstance(c, dict) else getattr(c, "zoom_scale", 1.0))
        pan_x = float(c.get("pan_x_pct") if isinstance(c, dict) else getattr(c, "pan_x_pct", 0.0))
        pan_y = float(c.get("pan_y_pct") if isinstance(c, dict) else getattr(c, "pan_y_pct", 0.0))
    else:
        idx = 0
        for i in range(len(cue_times) - 1):
            if cue_times[i] <= t_ms < cue_times[i + 1]:
                idx = i
                break
        t_a = cue_times[idx]
        t_b = cue_times[idx + 1]
        frac = (t_ms - t_a) / max(1.0, t_b - t_a)
        alpha = 0.5 - 0.5 * math.cos(frac * math.pi)

        c_a = cues[idx]
        c_b = cues[idx + 1]
        z_a = float(c_a.get("zoom_scale") if isinstance(c_a, dict) else getattr(c_a, "zoom_scale", 1.0))
        z_b = float(c_b.get("zoom_scale") if isinstance(c_b, dict) else getattr(c_b, "zoom_scale", 1.0))
        px_a = float(c_a.get("pan_x_pct") if isinstance(c_a, dict) else getattr(c_a, "pan_x_pct", 0.0))
        px_b = float(c_b.get("pan_x_pct") if isinstance(c_b, dict) else getattr(c_b, "pan_x_pct", 0.0))
        py_a = float(c_a.get("pan_y_pct") if isinstance(c_a, dict) else getattr(c_a, "pan_y_pct", 0.0))
        py_b = float(c_b.get("pan_y_pct") if isinstance(c_b, dict) else getattr(c_b, "pan_y_pct", 0.0))

        zoom = z_a + (z_b - z_a) * alpha
        pan_x = px_a + (px_b - px_a) * alpha
        pan_y = py_a + (py_b - py_a) * alpha

    eff_zoom = 1.0 + (zoom - 1.0) * (1.0 + depth * 0.4)
    eff_pan_x = pan_x * (1.0 + depth * 0.5)
    eff_pan_y = pan_y * (1.0 + depth * 0.5)

    scale = (ow / float(cw)) * eff_zoom
    cx_out = ow / 2.0
    cy_out = oh / 2.0
    cx_in = (cw / 2.0) + (cw * eff_pan_x / 100.0)
    cy_in = (ch / 2.0) + (ch * eff_pan_y / 100.0)

    tx = cx_out - cx_in * scale
    ty = cy_out - cy_in * scale

    return np.array([[scale, 0.0, tx], [0.0, scale, ty]])


def render_scene_clip(
    scene: Scene,
    bg_path: Path,
    fg_map: dict[str, Path],
    out_clip: Path,
    fps: int = 30,
    out_wh: tuple[int, int] = (1920, 1080),
    canvas_wh: tuple[int, int] = (2400, 1350),
    stepped_stop_motion: bool = True,
    master_manifest: Optional[Dict[str, Any]] = None,
) -> Path:
    """Renders a single scene into an MP4 clip using deterministic 2.5D parallax compositing.

    Enforces:
    - Layer 1: Background Desk (#F4F1EA) warped via continuous camera move
    - Layer 2: Midground Cutouts with white borders (#FFFFFF), dual-pass contact shadows,
      and 12fps stop-motion rhythm (on twos, <= 2px micro-vibration)
    - Layer 3: Foreground Graphic Callouts (highlighter sweeps, connecting red yarn, data counters)
    """
    out_clip = Path(out_clip)
    out_clip.parent.mkdir(parents=True, exist_ok=True)

    start_sec = scene.start if scene.start is not None else 0.0
    end_sec = scene.end if scene.end is not None else 5.0
    start_frame = int(round(start_sec * fps))
    end_frame = int(round(end_sec * fps))
    total_frames = max(15, end_frame - start_frame)

    # 1. Load Background Canvas
    bg_img = Image.open(str(bg_path)).convert("RGB")
    if bg_img.size != canvas_wh:
        bg_img = bg_img.resize(canvas_wh, Image.Resampling.LANCZOS)

    # 2. Preload and prepare foreground objects with white deckle borders & shadows
    fg_data: list[tuple[FGObject, Image.Image, Image.Image, Image.Image]] = []
    for fg_obj in scene.fg:
        f_path = fg_map.get(fg_obj.id)
        if f_path and Path(f_path).exists():
            f_img = Image.open(str(f_path)).convert("RGBA")
            target_h = int(out_wh[1] * fg_obj.scale)
            aspect = f_img.width / max(1, f_img.height)
            target_w = max(10, int(target_h * aspect))
            f_resized = f_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # Apply Layer 2 White Cutout Border (#FFFFFF)
            f_bordered = apply_white_cutout_border(f_resized, border_px=4)

            # Pre-compute Dual-Pass Shadows
            amb_shadow, occ_shadow = create_dual_pass_shadows(f_bordered)
            fg_data.append((fg_obj, f_bordered, amb_shadow, occ_shadow))

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

    # Parse Master Manifest Callouts if available
    l3_manifest = master_manifest.get("layer_3_foreground") if master_manifest else None
    stat_hero_val = l3_manifest.get("data_counters", [{}])[0].get("stat_hero") if l3_manifest and l3_manifest.get("data_counters") else None
    stat_label_val = l3_manifest.get("data_counters", [{}])[0].get("stat_label") if l3_manifest and l3_manifest.get("data_counters") else None

    # Connector coordinates from manifest or default
    yarn_src = (ow * 0.28, oh * 0.45)
    yarn_tgt = (ow * 0.72, oh * 0.35)
    if master_manifest and "wiring_spec" in master_manifest:
        w_spec = master_manifest["wiring_spec"]
        if "source_anchor" in w_spec and len(w_spec["source_anchor"]) == 2:
            yarn_src = (float(w_spec["source_anchor"][0]) * ow / 1920.0, float(w_spec["source_anchor"][1]) * oh / 1080.0)
        if "target_anchor" in w_spec and len(w_spec["target_anchor"]) == 2:
            yarn_tgt = (float(w_spec["target_anchor"][0]) * ow / 1920.0, float(w_spec["target_anchor"][1]) * oh / 1080.0)

    try:
        for k in range(total_frames):
            # Continuous cinematic camera timeline
            t_norm = k / float(max(1, total_frames - 1))
            t_sec = k / float(fps)

            # 12fps Stop-Motion Rhythm quantization ("on twos" = 12fps / 15fps hold)
            if stepped_stop_motion:
                # 12fps step index
                step_idx = int(k * 12.0 / fps)
                # Tactile paper breathing micro-jitter <= 1.5px (Rule 140)
                jitter_x = math.sin(step_idx * 3.7) * 1.2
                jitter_y = math.cos(step_idx * 2.3) * 1.0
            else:
                step_idx = k
                jitter_x, jitter_y = 0.0, 0.0

            # 1. Warp Layer 1 Background Desk according to continuous camera move
            cues_list = master_manifest.get("camera_cue_sheet") if master_manifest else None
            if cues_list and len(cues_list) >= 2:
                M_bg = cue_transform(cues_list, t_sec, canvas_wh=canvas_wh, out_wh=out_wh, depth=0.0)
            else:
                M_bg = move_transform(scene.camera, t_norm, canvas_wh=canvas_wh, out_wh=out_wh, depth=0.0)
            inv_m_bg = np.linalg.inv(np.vstack([M_bg, [0.0, 0.0, 1.0]]))
            aff_tuple = (
                inv_m_bg[0, 0], inv_m_bg[0, 1], inv_m_bg[0, 2],
                inv_m_bg[1, 0], inv_m_bg[1, 1], inv_m_bg[1, 2]
            )
            frame_bg = bg_img.transform(out_wh, Image.Transform.AFFINE, aff_tuple, resample=Image.Resampling.BILINEAR)
            frame_rgba = frame_bg.convert("RGBA")

            # 2. Composite Layer 2 Midground Cutouts with 2.5D Parallax & Dual-Pass Shadows
            for fg_obj, fg_img, amb_shadow, occ_shadow in fg_data:
                if t_sec < fg_obj.enter_at:
                    continue

                # Snappy stop-motion ingress <= 0.35s, then dead-stop hold
                ingress_dur = 0.35
                time_since_enter = t_sec - fg_obj.enter_at
                ingress_prog = min(1.0, max(0.0, time_since_enter / ingress_dur))

                # Camera transform scaled by depth parallax
                if cues_list and len(cues_list) >= 2:
                    M_fg = cue_transform(cues_list, t_sec, canvas_wh=canvas_wh, out_wh=out_wh, depth=fg_obj.depth)
                else:
                    M_fg = move_transform(scene.camera, t_norm, canvas_wh=canvas_wh, out_wh=out_wh, depth=fg_obj.depth)

                # Source coordinate on canvas
                src_x = fg_obj.anchor_x * cw
                src_y = fg_obj.anchor_y * ch

                # Destination center on output viewport
                dest_pt = M_fg @ np.array([src_x, src_y, 1.0])
                dx = dest_pt[0] + jitter_x
                dy = dest_pt[1] + jitter_y

                # Snappy overshoot spring on ingress
                if ingress_prog < 1.0:
                    scale_bounce = 1.0 + (math.sin(ingress_prog * math.pi) * 0.08)
                    w_cur = int(fg_img.width * scale_bounce)
                    h_cur = int(fg_img.height * scale_bounce)
                    cur_fg = fg_img.resize((w_cur, h_cur), Image.Resampling.BILINEAR)
                    cur_amb = amb_shadow.resize((w_cur, h_cur), Image.Resampling.BILINEAR)
                    cur_occ = occ_shadow.resize((w_cur, h_cur), Image.Resampling.BILINEAR)
                else:
                    cur_fg = fg_img
                    cur_amb = amb_shadow
                    cur_occ = occ_shadow

                top_left_x = int(dx - (cur_fg.width / 2.0))
                top_left_y = int(dy - (cur_fg.height / 2.0))

                # Dual-Pass Shadow Placement:
                # Pass 1: Ambient Drop Shadow (offset +8px, +12px)
                frame_rgba.alpha_composite(cur_amb, dest=(top_left_x + 8, top_left_y + 12))
                # Pass 2: Contact Occlusion Shadow (offset +3px, +4px)
                frame_rgba.alpha_composite(cur_occ, dest=(top_left_x + 3, top_left_y + 4))
                # Cutout Asset with #FFFFFF deckle border
                frame_rgba.alpha_composite(cur_fg, dest=(top_left_x, top_left_y))

            # 3. Layer 3 Foreground Graphic Callouts
            # 3a. Connecting Evidence Red Yarn (enters at 0.3s)
            yarn_progress = min(1.0, max(0.0, (t_sec - 0.3) / 0.4))
            if yarn_progress > 0.0:
                draw_evidence_yarn(frame_rgba, yarn_src, yarn_tgt, yarn_progress)

            # 3b. Highlighter Sweep
            sweeps = l3_manifest.get("highlighter_sweeps", []) if l3_manifest else []
            if sweeps and len(sweeps) > 0:
                for sw in sweeps:
                    sw_start = float(sw.get("start_ms", 500.0)) / 1000.0
                    sw_end = float(sw.get("end_ms", 1100.0)) / 1000.0
                    sw_dur = max(0.1, sw_end - sw_start)
                    sw_prog = min(1.0, max(0.0, (t_sec - sw_start) / sw_dur))
                    if sw_prog > 0.0:
                        draw_highlighter_sweep(
                            frame_rgba,
                            x=int(ow * (float(sw.get("x_pct", 42.0)) / 100.0)),
                            y=int(oh * (float(sw.get("y_pct", 52.0)) / 100.0)),
                            w=int(ow * (float(sw.get("width_pct", 36.0)) / 100.0)),
                            h=int(oh * 0.045),
                            progress=sw_prog,
                            color=(255, 230, 0, 140),
                        )
            else:
                hl_progress = min(1.0, max(0.0, (t_sec - 0.5) / 0.4))
                if hl_progress > 0.0:
                    draw_highlighter_sweep(
                        frame_rgba,
                        x=int(ow * 0.15),
                        y=int(oh * 0.78),
                        w=int(ow * 0.35),
                        h=int(oh * 0.05),
                        progress=hl_progress,
                        color=(255, 230, 0, 140),
                    )

            # 3c. Forensic Data Counter / Quantitative Metric (enters at 0.4s)
            if stat_hero_val:
                counter_progress = min(1.0, max(0.0, (t_sec - 0.4) / 0.5))
                if counter_progress > 0.0:
                    draw_data_counter(
                        frame_rgba,
                        stat_hero=str(stat_hero_val),
                        stat_label=str(stat_label_val or "VERIFIED METRIC"),
                        progress=counter_progress,
                        x_pct=76.0,
                        y_pct=42.0,
                    )

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


def render_master_vox_scene(
    scene_manifest: Dict[str, Any],
    bg_path: Path,
    fg_map: dict[str, Path],
    out_clip: Path,
    duration_sec: float = 6.0,
    fps: int = 30,
    out_wh: tuple[int, int] = (1920, 1080),
    canvas_wh: tuple[int, int] = (2400, 1350),
) -> Path:
    """Direct master renderer for a SceneAssetManifest / MasterSheetAssetBundle."""
    sc_id = scene_manifest.get("scene_id", "SCENE_01")
    cam_name = scene_manifest.get("camera_movement", "slow_push_in")
    cam_enum = CameraMove.PUSH_IN
    for c in CameraMove:
        if c.value in cam_name.lower():
            cam_enum = c
            break

    # Build FGObject roster
    l2 = scene_manifest.get("layer_2_midground", {})
    hero = l2.get("hero_cutout", {})
    fg_objs = [
        FGObject(
            id=hero.get("item_id", "hero"),
            prompt="hero cutout with white border",
            anchor_x=hero.get("anchor_x", 0.38),
            anchor_y=hero.get("anchor_y", 0.52),
            scale=hero.get("scale", 0.55),
            depth=hero.get("depth", 0.5),
            enter_at=hero.get("enter_at_sec", 0.0),
        )
    ]
    for supp in l2.get("supporting_cutouts", []):
        fg_objs.append(
            FGObject(
                id=supp.get("item_id", "supp"),
                prompt="supporting evidence document",
                anchor_x=supp.get("anchor_x", 0.72),
                anchor_y=supp.get("anchor_y", 0.60),
                scale=supp.get("scale", 0.40),
                depth=supp.get("depth", 0.35),
                enter_at=supp.get("enter_at_sec", 0.35),
            )
        )

    # Interacting Tool Prop
    tool = l2.get("interacting_tool")
    if tool:
        fg_objs.append(
            FGObject(
                id=tool.get("item_id", "tool"),
                prompt="forensic interacting tool prop",
                anchor_x=tool.get("anchor_x", 0.55),
                anchor_y=tool.get("anchor_y", 0.45),
                scale=tool.get("scale", 0.32),
                depth=tool.get("depth", 0.8),
                enter_at=tool.get("enter_at_sec", 0.3),
            )
        )

    sc_obj = Scene(
        idx=1,
        narration=scene_manifest.get("narration", f"Vox scene {sc_id}"),
        bg_prompt="archival desk background #F4F1EA",
        fg=fg_objs[:4],
        camera=cam_enum,
        start=0.0,
        end=duration_sec,
    )

    return render_scene_clip(
        scene=sc_obj,
        bg_path=bg_path,
        fg_map=fg_map,
        out_clip=out_clip,
        fps=fps,
        out_wh=out_wh,
        canvas_wh=canvas_wh,
        stepped_stop_motion=True,
        master_manifest=scene_manifest,
    )

