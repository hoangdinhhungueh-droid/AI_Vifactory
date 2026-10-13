#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/run_vox_media_pipeline.py — Master 1-Command Vox Media Orchestrator.

Tự động hóa toàn trình 1-LỆNH DUY NHẤT:
1. Phân nhóm Sequence Blocks từ director_plan.json thành các folder định danh chuẩn:
   episodes/<EP_ID>/blocks/<BLOCK_NAME>/images/ và videos/
2. Giai đoạn Sinh Ảnh: Tự động chạy Gemini Web, lưu ảnh vào từng folder cụm.
3. Giai đoạn Sinh Video: Tự động nạp ảnh từ từng folder cụm làm Seed I2V,
   xoay vòng 7 tài khoản Google Flow (Veo 3.1 Fast), lưu video vào folder cụm.
4. Tự động đồng bộ ra composite_seeds/ và video_clips/ để Remotion ghép nối liền mạch.

Tuân thủ:
- Rule 118: Zero-mock, tạo ảnh và video thật 100%.
- Rule 121: Forensic verification (kiểm tra tồn tại, kích thước file).
- Rule 126: Three-way physical sync (Local -> VPS).
"""

from __future__ import annotations

import os
import sys
import time
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Any, Dict, List

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent


def setup_block_directory_structure(episode_id: str) -> Dict[str, Any]:
    """Tạo cấu trúc thư mục phân cụm định danh chuẩn từ director_plan.json."""
    episode_dir = ROOT_DIR / "episodes" / episode_id
    plan_file = episode_dir / "director_plan.json"
    if not plan_file.exists():
        raise FileNotFoundError(f"Không tìm thấy director_plan.json tại {plan_file}")

    with open(plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)

    blocks_dir = episode_dir / "blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    # Thư mục xuất phẳng dùng cho Remotion rendering
    flat_seeds_dir = episode_dir / "composite_seeds"
    flat_videos_dir = episode_dir / "video_clips"
    flat_seeds_dir.mkdir(parents=True, exist_ok=True)
    flat_videos_dir.mkdir(parents=True, exist_ok=True)

    scenes = plan.get("scenes", [])
    blocks_map: Dict[str, List[Dict[str, Any]]] = {}

    for s in scenes:
        b_name = s.get("sequence_block", "BLOCK_DEFAULT").lower().strip()
        blocks_map.setdefault(b_name, []).append(s)

    block_manifest = {
        "episode_id": episode_id,
        "total_blocks": len(blocks_map),
        "total_scenes": len(scenes),
        "blocks": {}
    }

    for b_name, b_scenes in blocks_map.items():
        b_dir = blocks_dir / b_name
        img_dir = b_dir / "images"
        vid_dir = b_dir / "videos"
        img_dir.mkdir(parents=True, exist_ok=True)
        vid_dir.mkdir(parents=True, exist_ok=True)

        block_manifest["blocks"][b_name] = {
            "block_dir": str(b_dir),
            "images_dir": str(img_dir),
            "videos_dir": str(vid_dir),
            "scene_count": len(b_scenes),
            "scenes": [s.get("scene_id") for s in b_scenes]
        }

    manifest_path = episode_dir / "blocks_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(block_manifest, f, ensure_ascii=False, indent=2)

    # Đảm bảo flow_video_manifest.json luôn sẵn sàng cho bước sinh Video
    flow_manifest_path = episode_dir / "flow_video_manifest.json"
    if not flow_manifest_path.exists():
        acc_list = [f"acc_{i:02d}" for i in range(1, 8)]
        clips = []
        for idx, s in enumerate(scenes):
            sc_id = s.get("scene_id", f"SCENE_{idx+1:02d}")
            hero_obj = s.get("hero_cutout_object", "")
            motion = s.get("motion_track_and_assembly", {})
            entry_act = motion.get("entry_action", "") if isinstance(motion, dict) else ""
            prompt = (
                f"Editorial paper cutout animation in Vox documentary style. {hero_obj}. "
                f"{entry_act}. Tactile paper motion, crisp deckle white edges, flat top-down desk view. "
                f"No 3D camera rotation."
            )
            clips.append({
                "scene_id": sc_id,
                "clip_index": idx + 1,
                "flow_slot": acc_list[idx % len(acc_list)],
                "output_filename": f"clip_{sc_id.lower()}.mp4",
                "prompt": prompt
            })
        with open(flow_manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "episode_id": episode_id,
                "format": "FLOW_VEO_7_ACCOUNT_DISPATCH",
                "total_clips": len(clips),
                "accounts_used": acc_list,
                "clips": clips
            }, f, indent=2, ensure_ascii=False)
        print(f"📄 Đã tự động khởi tạo flow_video_manifest.json với {len(clips)} clips xoay vòng 7 tài khoản.")

    return block_manifest


def sync_assets_to_blocks_and_flat(episode_id: str, block_manifest: Dict[str, Any]):
    """Đồng bộ hai chiều giữa thư mục block và thư mục phẳng để Remotion đọc được ngay."""
    episode_dir = ROOT_DIR / "episodes" / episode_id
    flat_seeds = episode_dir / "composite_seeds"
    flat_videos = episode_dir / "video_clips"
    brain_dir = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\browser_assets") / episode_id

    for b_name, b_info in block_manifest.get("blocks", {}).items():
        b_imgs = Path(b_info["images_dir"])
        b_vids = Path(b_info["videos_dir"])

        for sc_id in b_info["scenes"]:
            sc_lower = sc_id.lower()

            # 1. Đồng bộ Ảnh Seed
            img_cands = [
                b_imgs / f"composite_{sc_id}.png",
                b_imgs / f"{sc_lower}.png",
                flat_seeds / f"composite_{sc_id}.png",
                brain_dir / f"composite_{sc_id}.png",
                brain_dir / f"{sc_lower}.png",
            ]
            found_img = None
            for c in img_cands:
                if c.exists() and c.stat().st_size > 1024:
                    found_img = c
                    break

            if found_img:
                dest_block_img = b_imgs / f"composite_{sc_id}.png"
                dest_flat_img = flat_seeds / f"composite_{sc_id}.png"
                if not dest_block_img.exists() or dest_block_img != found_img:
                    shutil.copy2(str(found_img), str(dest_block_img))
                if not dest_flat_img.exists() or dest_flat_img != found_img:
                    shutil.copy2(str(found_img), str(dest_flat_img))

            # 2. Đồng bộ Video Clip
            vid_cands = [
                b_vids / f"clip_{sc_lower}.mp4",
                flat_videos / f"clip_{sc_lower}.mp4",
            ]
            found_vid = None
            for c in vid_cands:
                if c.exists() and c.stat().st_size > 100000:
                    found_vid = c
                    break

            if found_vid:
                dest_block_vid = b_vids / f"clip_{sc_lower}.mp4"
                dest_flat_vid = flat_videos / f"clip_{sc_lower}.mp4"
                if not dest_block_vid.exists() or dest_block_vid != found_vid:
                    shutil.copy2(str(found_vid), str(dest_block_vid))
                if not dest_flat_vid.exists() or dest_flat_vid != found_vid:
                    shutil.copy2(str(found_vid), str(dest_flat_vid))


def run_stage_images(episode_id: str, limit: int = 0, headless: bool = False, pacing: int = 4) -> bool:
    """Thực thi sinh ảnh qua gemini_browser_gen.py."""
    print("\n" + "=" * 75)
    print("🎨 [BƯỚC 4: SINH ẢNH SEED CHUẨN VOX CONTINUOUS]")
    print(f"   Episode: {episode_id}")
    print(f"   Giới hạn: {limit if limit > 0 else 'Toàn bộ'} ảnh")
    print(f"   Headless: {headless} | Pacing: {pacing}s")
    print("=" * 75)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "gemini_browser_gen.py"),
        "--episode", episode_id,
        "--pacing", str(pacing)
    ]
    if limit > 0:
        cmd.extend(["--limit", str(limit)])
    if headless:
        cmd.append("--headless")

    print(f"🚀 Thực thi lệnh: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode == 0


def run_stage_videos(episode_id: str, limit: int = 0, acc: str = "all") -> bool:
    """Thực thi sinh video clips qua flow_video_dispatcher.py (xoay vòng 7 acc)."""
    print("\n" + "=" * 75)
    print("🎬 [BƯỚC 5: SINH VIDEO CLIPS VEO 3.1 XOAY VÒNG 7 TÀI KHOẢN]")
    print(f"   Episode: {episode_id}")
    print(f"   Tài khoản: {acc}")
    print(f"   Giới hạn: {limit if limit > 0 else 'Toàn bộ'} clips / account")
    print("=" * 75)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "flow_video_dispatcher.py"),
        "--episode", episode_id,
        "--acc", acc
    ]
    if limit > 0:
        cmd.extend(["--limit", str(limit)])

    print(f"🚀 Thực thi lệnh: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode == 0


def print_pipeline_summary(episode_id: str, block_manifest: Dict[str, Any]):
    """In bảng tổng kết thực chứng tài sản đã sinh theo từng cụm folder."""
    sync_assets_to_blocks_and_flat(episode_id, block_manifest)

    print("\n" + "=" * 75)
    print("📊 TỔNG KẾT THỰC CHỨNG TÀI SẢN THEO CỤM SEQUENCE BLOCKS:")
    print("=" * 75)

    total_scenes = block_manifest.get("total_scenes", 0)
    total_imgs_found = 0
    total_vids_found = 0

    for b_name, b_info in block_manifest.get("blocks", {}).items():
        b_imgs = Path(b_info["images_dir"])
        b_vids = Path(b_info["videos_dir"])
        sc_list = b_info["scenes"]

        img_cnt = len(list(b_imgs.glob("*.png")))
        vid_cnt = len(list(b_vids.glob("*.mp4")))
        total_imgs_found += img_cnt
        total_vids_found += vid_cnt

        status_str = f"🖼️ {img_cnt}/{len(sc_list)} Ảnh | 🎥 {vid_cnt}/{len(sc_list)} Video"
        print(f"📁 [{b_name.upper()}] ({len(sc_list)} cảnh)")
        print(f"   Thư mục: episodes/{episode_id}/blocks/{b_name}/")
        print(f"   Tiến độ: {status_str}")

    print("-" * 75)
    print(f"🎯 TỔNG CỘNG: {total_imgs_found}/{total_scenes} Ảnh | {total_vids_found}/{total_scenes} Video Clips")
    print(f"📁 Xuất phẳng cho Remotion: episodes/{episode_id}/composite_seeds/ & video_clips/")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Master 1-Command Vox Media Pipeline (Images -> Videos -> Blocks)")
    parser.add_argument("--episode", required=True, help="Episode ID (e.g. KR_EP0001_google_kr_tax_loss)")
    parser.add_argument("--stage", choices=["all", "image", "video"], default="all", help="Giai đoạn: all (full luồng), image (chỉ ảnh), video (chỉ video)")
    parser.add_argument("--limit-blocks", type=int, default=0, help="Giới hạn số cụm Block cần chạy (0: chạy toàn bộ)")
    parser.add_argument("--limit-scenes", type=int, default=0, help="Giới hạn số cảnh cần sinh (0: toàn bộ)")
    parser.add_argument("--acc", default="all", help="Tài khoản Google Flow (acc_01 đến acc_07 hoặc all)")
    parser.add_argument("--headless", action="store_true", help="Chạy ngầm không mở cửa sổ browser")
    parser.add_argument("--pacing", type=int, default=4, help="Thời gian giãn cách giữa các prompt sinh ảnh (giây)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ tạo cấu trúc folder và xuất manifest, không sinh media")
    args = parser.parse_args()

    clean_ep = args.episode.strip().strip("'\"")
    if clean_ep.lower().startswith("task:"):
        clean_ep = clean_ep[5:].strip()

    print("\n" + "#" * 75)
    print(f"🎬 MASTER 1-COMMAND VOX MEDIA PIPELINE — EPISODE: {clean_ep}")
    print("#" * 75)

    # 1. Khởi tạo cấu trúc thư mục Blocks
    print("\n📁 [BƯỚC 1/3] Khởi tạo cây thư mục phân cụm Sequence Blocks...")
    block_manifest = setup_block_directory_structure(clean_ep)
    print(f"✅ Đã thiết lập {block_manifest['total_blocks']} cụm Sequence Blocks trong:")
    print(f"   episodes/{clean_ep}/blocks/")

    if args.dry_run:
        print("\n🏁 Chế độ --dry-run: Hoàn tất thiết lập cấu trúc thư mục.")
        print_pipeline_summary(clean_ep, block_manifest)
        return

    # Tính toán giới hạn scenes nếu user chọn limit-blocks
    total_scenes_to_run = args.limit_scenes
    if args.limit_blocks > 0:
        blocks_subset = list(block_manifest["blocks"].items())[:args.limit_blocks]
        count_in_blocks = sum(len(b[1]["scenes"]) for b in blocks_subset)
        if total_scenes_to_run == 0 or total_scenes_to_run > count_in_blocks:
            total_scenes_to_run = count_in_blocks
        print(f"🎯 Đã giới hạn {args.limit_blocks} cụm Block đầu tiên (~{total_scenes_to_run} cảnh)!")

    # 2. Chạy Giai đoạn Sinh Ảnh
    if args.stage in ("all", "image"):
        ok_img = run_stage_images(
            clean_ep,
            limit=total_scenes_to_run,
            headless=args.headless,
            pacing=args.pacing
        )
        sync_assets_to_blocks_and_flat(clean_ep, block_manifest)
        if not ok_img:
            print("⚠️ Giai đoạn sinh ảnh gặp cảnh báo, tiến trình tiếp tục đồng bộ tài sản hiện có...")

    # 3. Chạy Giai đoạn Sinh Video
    if args.stage in ("all", "video"):
        sync_assets_to_blocks_and_flat(clean_ep, block_manifest)
        ok_vid = run_stage_videos(
            clean_ep,
            limit=total_scenes_to_run,
            acc=args.acc
        )
        sync_assets_to_blocks_and_flat(clean_ep, block_manifest)
        if not ok_vid:
            print("⚠️ Giai đoạn sinh video gặp cảnh báo, tiến trình tiếp tục đồng bộ tài sản hiện có...")

    # 4. Tổng kết thực chứng
    print_pipeline_summary(clean_ep, block_manifest)


if __name__ == "__main__":
    main()
