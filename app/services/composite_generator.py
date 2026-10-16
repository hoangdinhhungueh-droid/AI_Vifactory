#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/composite_generator.py
Generates 16:9 composite frames from Layer 1 Background and Layer 2 Foreground Cutout
with realistic tactile paper drop-shadows for Veo 3.1 3D Origami/Spatial seed inputs.
Compliant with Rule 122 (Visual Audit) and Rule 128 (Generic Contract Architecture).
"""

import sys
from pathlib import Path
from typing import Optional
from PIL import Image, ImageFilter, ImageEnhance

sys.stdout.reconfigure(encoding='utf-8')

def create_composite_frame(
    bg_path: Path,
    fg_path: Path,
    out_path: Path,
    layout: str = "right_dossier",
    scale_factor: float = 0.82
) -> Path:
    """Ghép ảnh Layer 1 Background (16:9) và Layer 2 Foreground Cutout với bóng đổ tách lớp.
    
    Args:
        bg_path: Đường dẫn ảnh nền 16:9
        fg_path: Đường dẫn ảnh cutout hồ sơ (RGBA)
        out_path: Đường dẫn lưu ảnh composite 16:9
        layout: 'right_dossier' | 'center_exhibit' | 'left_dossier'
        scale_factor: Tỷ lệ kích thước của FG so với chiều cao BG
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    bg = Image.open(bg_path).convert("RGBA")
    fg = Image.open(fg_path).convert("RGBA")
    
    # Calculate target dimensions
    target_h = int(bg.height * scale_factor)
    target_w = int(fg.width * (target_h / fg.height))
    fg_resized = fg.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Calculate position based on layout
    if layout == "right_dossier":
        pos_x = int(bg.width * 0.58)
        pos_y = int(bg.height * 0.10)
    elif layout == "left_dossier":
        pos_x = int(bg.width * 0.08)
        pos_y = int(bg.height * 0.10)
    else:  # center_exhibit
        pos_x = int((bg.width - target_w) / 2)
        pos_y = int((bg.height - target_h) / 2)
        
    # Create soft realistic paper drop-shadow
    shadow_offset = (int(bg.width * 0.015), int(bg.height * 0.025))
    shadow_mask = fg_resized.split()[3]  # Alpha channel
    
    # Blur alpha for shadow
    blurred_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=18))
    shadow_img = Image.new("RGBA", fg_resized.size, (0, 0, 0, 160))
    shadow_img.putalpha(blurred_mask)
    
    composite = bg.copy()
    
    # Paste shadow first
    composite.paste(
        shadow_img,
        (pos_x + shadow_offset[0], pos_y + shadow_offset[1]),
        shadow_img
    )
    
    # Paste foreground cutout
    composite.paste(fg_resized, (pos_x, pos_y), fg_resized)
    
    # Convert to RGB and save
    composite.convert("RGB").save(out_path, quality=95)
    return out_path

def batch_generate_composite_seeds(episode_dir: Path, brain_dir: Optional[Path] = None) -> int:
    """Tự động tạo batch ảnh Seed 16:9 cho toàn bộ clips trong flow_video_manifest.json."""
    manifest_path = episode_dir / "flow_video_manifest.json"
    if not manifest_path.exists():
        print(f"❌ Không tìm thấy manifest tại: {manifest_path}")
        return 0

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    clips = manifest.get("clips", [])
    out_dir = episode_dir / "composite_seeds"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Search candidates across local episode dirs and brain dir
    search_dirs = [
        episode_dir / "images",
        episode_dir / "cutouts",
        episode_dir,
    ]
    if brain_dir and brain_dir.exists():
        search_dirs.append(brain_dir)

    success_count = 0
    for clip in clips:
        scene_id = clip["scene_id"]
        bg_key = clip.get("bg_key")
        fg_key = clip.get("fg_key")
        seed_mode = clip.get("seed_asset_mode", "COMPOSITE_16_9")
        out_file = out_dir / f"composite_{scene_id}.png"

        # Find BG
        bg_path = None
        for d in search_dirs:
            candidate = d / f"{bg_key}.png"
            if candidate.exists():
                bg_path = candidate
                break

        # Find FG
        fg_path = None
        for d in search_dirs:
            for ext in [".png", "_nobg.png"]:
                candidate = d / f"{fg_key}{ext}"
                if candidate.exists():
                    fg_path = candidate
                    break
            if fg_path:
                break

        if seed_mode == "COMPOSITE_16_9" and bg_path and fg_path:
            create_composite_frame(bg_path, fg_path, out_file, layout="right_dossier", scale_factor=0.85)
            print(f"   ✅ [TẠO COMPOSITE 16:9] {scene_id} -> {out_file.name} ({bg_key} + {fg_key})")
            success_count += 1
        elif seed_mode == "CUTOUT_ONLY" and fg_path:
            # If cutout only, copy or composite on subtle desk
            if bg_path:
                create_composite_frame(bg_path, fg_path, out_file, layout="center_exhibit", scale_factor=0.88)
            else:
                import shutil
                shutil.copy2(fg_path, out_file)
            print(f"   ✅ [TẠO CUTOUT SEED] {scene_id} -> {out_file.name} ({fg_key})")
            success_count += 1
        else:
            print(f"   ⚠️ Thiếu asset cho {scene_id}: bg={bg_key} (found={bool(bg_path)}), fg={fg_key} (found={bool(fg_path)})")

    print(f"\n🎉 Hoàn thành tạo {success_count}/{len(clips)} ảnh Seed tại: {out_dir}")
    return success_count

if __name__ == "__main__":
    import argparse
    import json
    from typing import Optional

    parser = argparse.ArgumentParser(description="Batch Composite Seed Generator for Veo 3.1 I2V")
    parser.add_argument("--episode", type=str, required=True, help="Episode ID (e.g. <MARKET>_EP<XXXX>_<slug>)")
    parser.add_argument("--brain-dir", type=str, default=None, help="Brain artifacts dir")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    ep_dir = repo_root / "episodes" / args.episode
    brain_dir = Path(args.brain_dir) if args.brain_dir else None

    print(f"🚀 Chạy Batch Composite Generator cho {args.episode}...")
    batch_generate_composite_seeds(ep_dir, brain_dir)

