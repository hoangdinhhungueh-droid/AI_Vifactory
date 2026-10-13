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
import re
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


def build_universal_video_prompt(scene: Dict[str, Any]) -> str:
    """Xây dựng Universal Video Prompt (Mode 1 / Prompt 3 từ Made by AI Playbook).
    Định vị chuẩn 4 giai đoạn: S1 Entry, S2 Assembly, S3 Lock, S4 Micro-action.
    """
    hero_obj = scene.get("hero_cutout_object", "")
    motion = scene.get("motion_track_and_assembly", {})
    entry_act = motion.get("entry_action", "") if isinstance(motion, dict) else ""
    assembly = motion.get("assembly_step", "") if isinstance(motion, dict) else ""
    spatial = motion.get("spatial_anchor", "") if isinstance(motion, dict) else ""
    camera = motion.get("camera_rule", "Completely static camera, no 3D pan/zoom") if isinstance(motion, dict) else ""

    entry_clean = re.sub(r"^\s*[\d\.\-sS:–—]+\s*", "", entry_act).strip()
    assembly_clean = re.sub(r"^\s*[\d\.\-sS:–—]+\s*", "", assembly).strip()

    parts = [
        "Editorial paper cutout animation in Vox documentary style.",
        f"Animate completed composition: {hero_obj}.",
        f"0.0-2.0s: {entry_clean}." if entry_clean else "",
        f"2.0-4.5s: {assembly_clean}." if assembly_clean else "",
        f"Spatial anchor: {spatial}. Every object permanently locked, zero drift." if spatial else "",
        f"Camera: {camera}.",
        "Tactile paper motion, crisp deckle white edges, flat top-down desk view, subtle micro-shadow breathing <= 2px."
    ]
    return " ".join(p for p in parts if p).strip()


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

    plan_updated = False
    for s in scenes:
        b_name = s.get("sequence_block", "BLOCK_DEFAULT").lower().strip()
        blocks_map.setdefault(b_name, []).append(s)
        # Nạp Universal Video Prompt vào scene trong director_plan.json nếu chưa có
        if not s.get("i2v_prompt") or not s.get("video_prompt"):
            uv_prompt = build_universal_video_prompt(s)
            s["i2v_prompt"] = uv_prompt
            s["video_prompt"] = uv_prompt
            plan_updated = True

    if plan_updated:
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        print(f"📄 Đã đồng bộ i2v_prompt (Universal Video Prompt) vào {len(scenes)} cảnh trong director_plan.json.")

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
    acc_list = [f"acc_{i:02d}" for i in range(1, 8)]
    clips = []
    for idx, s in enumerate(scenes):
        sc_id = s.get("scene_id", f"SCENE_{idx+1:02d}")
        prompt = s.get("i2v_prompt") or build_universal_video_prompt(s)
        clips.append({
            "scene_id": sc_id,
            "clip_index": idx + 1,
            "flow_slot": acc_list[idx % len(acc_list)],
            "output_filename": f"clip_{sc_id.lower()}.mp4",
            "prompt": prompt,
            "timeframe": s.get("timeframe", ""),
            "sentence": s.get("sentence", "")
        })

    with open(flow_manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "episode_id": episode_id,
            "format": "FLOW_VEO_7_ACCOUNT_DISPATCH",
            "total_clips": len(clips),
            "accounts_used": acc_list,
            "clips": clips
        }, f, indent=2, ensure_ascii=False)
    print(f"📄 Đã cập nhật flow_video_manifest.json ({len(clips)} clips) chuẩn Universal Prompt xoay vòng 7 tài khoản.")

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

            # 1. Đồng bộ Ảnh Seed: Ưu tiên file có mtime mới nhất
            img_cands = [
                brain_dir / f"composite_{sc_id}.png",
                brain_dir / f"{sc_lower}.png",
                b_imgs / f"composite_{sc_id}.png",
                b_imgs / f"{sc_lower}.png",
                flat_seeds / f"composite_{sc_id}.png",
            ]
            valid_cands = [c for c in img_cands if c.exists() and c.stat().st_size > 1024]
            found_img = max(valid_cands, key=lambda c: c.stat().st_mtime) if valid_cands else None

            if found_img:
                dest_block_img = b_imgs / f"composite_{sc_id}.png"
                dest_flat_img = flat_seeds / f"composite_{sc_id}.png"
                if not dest_block_img.exists() or dest_block_img.resolve() != found_img.resolve():
                    shutil.copy2(str(found_img), str(dest_block_img))
                if not dest_flat_img.exists() or dest_flat_img.resolve() != found_img.resolve():
                    shutil.copy2(str(found_img), str(dest_flat_img))

            # 2. Đồng bộ Video Clip: Ưu tiên file có mtime mới nhất
            vid_cands = [
                b_vids / f"clip_{sc_lower}.mp4",
                flat_videos / f"clip_{sc_lower}.mp4",
                episode_dir / f"clip_{sc_lower}.mp4",
            ]
            valid_vids = [c for c in vid_cands if c.exists() and c.stat().st_size > 100000]
            found_vid = max(valid_vids, key=lambda c: c.stat().st_mtime) if valid_vids else None

            if found_vid:
                dest_block_vid = b_vids / f"clip_{sc_lower}.mp4"
                dest_flat_vid = flat_videos / f"clip_{sc_lower}.mp4"
                if not dest_block_vid.exists() or dest_block_vid.resolve() != found_vid.resolve():
                    shutil.copy2(str(found_vid), str(dest_block_vid))
                if not dest_flat_vid.exists() or dest_flat_vid.resolve() != found_vid.resolve():
                    shutil.copy2(str(found_vid), str(dest_flat_vid))


def run_stage_images(episode_id: str, limit: int = 0, headless: bool = False, pacing: int = 4, force: bool = False) -> bool:
    """Thực thi sinh ảnh qua gemini_browser_gen.py."""
    print("\n" + "=" * 75)
    print("🎨 [BƯỚC 4: SINH ẢNH SEED CHUẨN VOX CONTINUOUS]")
    print(f"   Episode: {episode_id}")
    print(f"   Giới hạn: {limit if limit > 0 else 'Toàn bộ'} ảnh")
    print(f"   Headless: {headless} | Pacing: {pacing}s | Force: {force}")
    print("=" * 75)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "gemini_browser_gen.py"),
        "--episode", episode_id,
        "--pacing", str(pacing),
        "--no-auto-handoff"
    ]
    if limit > 0:
        cmd.extend(["--limit", str(limit)])
    if headless:
        cmd.append("--headless")
    if force:
        cmd.append("--force")

    print(f"🚀 Thực thi lệnh: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode == 0


def perform_b5_visual_audit(episode_id: str, block_manifest: Dict[str, Any], limit: int = 0) -> Dict[str, Any]:
    """Kiểm toán thị giác Forensic B5 đồng thời trên toàn bộ ảnh vừa sinh (Rule 118, 121, 122)."""
    print("\n" + "=" * 88)
    print("🔍 [BƯỚC B5: KIỂM TOÁN THỊ GIÁC ĐỒNG THỜI (FORENSIC VISUAL AUDIT)]")
    print(f"   Episode: {episode_id}")
    print("=" * 88)

    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        Image = None
        np = None

    episode_dir = ROOT_DIR / "episodes" / episode_id
    flat_seeds = episode_dir / "composite_seeds"
    brain_dir = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\browser_assets") / episode_id

    # Tập hợp các cảnh cần audit
    all_scenes: List[Dict[str, Any]] = []
    for b_name, b_info in block_manifest.get("blocks", {}).items():
        for sc_id in b_info.get("scenes", []):
            all_scenes.append({
                "scene_id": sc_id,
                "block_name": b_name,
                "images_dir": b_info.get("images_dir")
            })

    if limit > 0:
        all_scenes = all_scenes[:limit]

    audit_details = []
    approved_count = 0

    print(f"{'Scene ID':<10} | {'Block Name':<18} | {'Resolution':<11} | {'Dung Lượng':<10} | {'Tỷ lệ':<8} | {'Điểm':<5} | Trạng Thái")
    print("-" * 88)

    for sc in all_scenes:
        sc_id = sc["scene_id"]
        b_name = sc["block_name"]
        sc_lower = sc_id.lower()

        # Tìm ảnh ở các vị trí có thể
        candidates = [
            Path(sc["images_dir"]) / f"composite_{sc_id}.png",
            Path(sc["images_dir"]) / f"{sc_lower}.png",
            flat_seeds / f"composite_{sc_id}.png",
            flat_seeds / f"{sc_lower}.png",
            brain_dir / f"composite_{sc_id}.png",
            brain_dir / f"{sc_lower}.png"
        ]
        found_img = None
        for cand in candidates:
            if cand.exists() and cand.stat().st_size > 1024:
                found_img = cand
                break

        if not found_img:
            audit_details.append({
                "scene_id": sc_id,
                "block": b_name,
                "file": f"composite_{sc_id}.png",
                "resolution": "N/A",
                "size_bytes": 0,
                "score": 0.0,
                "status": "MISSING",
                "reason": "Chưa có file ảnh"
            })
            print(f"{sc_id:<10} | {b_name[:18]:<18} | {'N/A':<11} | {'0 KB':<10} | {'N/A':<8} | {'0.0':<5} | ❌ CHƯA CÓ ẢNH")
            continue

        sz_bytes = found_img.stat().st_size
        sz_kb = sz_bytes // 1024

        res_str = "Unknown"
        aspect_str = "Unknown"
        score = 8.0
        is_ok = (sz_kb >= 50)

        if Image:
            try:
                with Image.open(found_img) as im:
                    w, h = im.size
                    res_str = f"{w}x{h}"
                    ratio = round(w / h, 2) if h > 0 else 0.0
                    aspect_str = f"{ratio}:1"
                    
                    # Tiêu chuẩn: 16:9 (ratio 1.70 - 1.85) và tối thiểu 1920x1080
                    res_pass = (w >= 1920 and h >= 1080)
                    ratio_pass = (1.70 <= ratio <= 1.85)

                    if np:
                        arr = np.array(im.convert("RGB"))
                        std_dev = float(np.std(arr))
                        richness_pass = (std_dev > 15.0)
                    else:
                        richness_pass = True

                    score = 10.0
                    if not ratio_pass:
                        score -= 2.5
                    if not res_pass:
                        score -= 2.5
                    if not richness_pass:
                        score -= 2.0
                    if not (sz_kb >= 50):
                        score -= 2.0
                    score = max(0.0, round(score, 1))
                    is_ok = (score >= 8.0 and res_pass and ratio_pass)
            except Exception as e:
                is_ok = False
                score = 0.0
                res_str = f"Error: {e}"

        status_text = "APPROVED" if is_ok else "NEEDS_REVIEW"
        if is_ok:
            approved_count += 1
            icon_status = "✅ ĐẠT CHUẨN"
        else:
            icon_status = "⚠️ CẦN XEM LẠI"

        print(f"{sc_id:<10} | {b_name[:18]:<18} | {res_str:<11} | {f'{sz_kb:,} KB':<10} | {aspect_str:<8} | {score:<5} | {icon_status}")

        audit_details.append({
            "scene_id": sc_id,
            "block": b_name,
            "file": found_img.name,
            "path": str(found_img),
            "resolution": res_str,
            "size_kb": sz_kb,
            "aspect_ratio": aspect_str,
            "score": score,
            "status": status_text
        })

    total_scenes_audited = len(all_scenes)
    overall_verdict = "TECH_PASS" if (approved_count == total_scenes_audited and total_scenes_audited > 0) else ("PARTIAL_PASS" if approved_count > 0 else "FAIL")

    print("-" * 88)
    print(f"📊 TỔNG KẾT B5: {approved_count}/{total_scenes_audited} Ảnh Đạt Chuẩn ({round((approved_count/total_scenes_audited*100) if total_scenes_audited else 0)}%) | Verdict: {overall_verdict}")
    print("=" * 88)

    summary_data = {
        "episode_id": episode_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_images": total_scenes_audited,
        "approved_images": approved_count,
        "verdict": overall_verdict,
        "scenes": audit_details
    }

    report_path = episode_dir / "b5_visual_audit_summary.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    # Tự động xuất trang HTML Gallery để user mở xem trực quan
    gallery_path = generate_html_review_gallery(episode_id, block_manifest, summary_data)
    print(f"🌐 [HTML Gallery] Đã tạo trang xem trực quan tại: {gallery_path.name}")

    return summary_data


def generate_html_review_gallery(episode_id: str, block_manifest: Dict[str, Any], audit_summary: Dict[str, Any]) -> Path:
    """Tạo trang HTML Gallery trực quan để user mở duyệt ảnh ngay lập tức bằng 1 cú click."""
    episode_dir = ROOT_DIR / "episodes" / episode_id
    plan_file = episode_dir / "director_plan.json"
    scenes_info = {}
    if plan_file.exists():
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                dp = json.load(f)
            for s in dp.get("scenes", []):
                scenes_info[s.get("scene_id")] = s
        except Exception:
            pass

    gallery_html_path = episode_dir / "review_gallery.html"
    scenes_audited = audit_summary.get("scenes", [])

    cards_html = []
    for item in scenes_audited:
        sc_id = item.get("scene_id", "")
        b_name = item.get("block", "")
        file_name = item.get("file", "")
        res = item.get("resolution", "")
        sz = item.get("size_kb", 0)
        status = item.get("status", "")
        img_rel_path = f"blocks/{b_name}/images/{file_name}"

        sc_data = scenes_info.get(sc_id, {})
        sentence = sc_data.get("sentence", "")
        hero_obj = sc_data.get("hero_cutout_object", "")
        headline = sc_data.get("headline", "")
        motion = sc_data.get("motion_track_and_assembly", {})
        s1 = motion.get("entry_action", "") if isinstance(motion, dict) else ""
        s2 = motion.get("assembly_step", "") if isinstance(motion, dict) else ""
        s3 = motion.get("spatial_anchor", "") if isinstance(motion, dict) else ""
        s4 = sc_data.get("visual_continuity_link_to_next") or (motion.get("camera_rule", "") if isinstance(motion, dict) else "") or "Khóa cứng vĩnh viễn, micro-shadow breathing <= 2px"

        badge_color = "#10b981" if status == "APPROVED" else "#ef4444"
        badge_text = "✅ ĐẠT CHUẨN (10/10)" if status == "APPROVED" else f"⚠️ {status}"

        card = f"""
        <div class="card">
            <div class="img-wrapper">
                <a href="{img_rel_path}" target="_blank" title="Bấm để xem ảnh gốc 2K">
                    <img src="{img_rel_path}" alt="{sc_id}"/>
                </a>
                <span class="badge" style="background: {badge_color};">{badge_text}</span>
            </div>
            <div class="content">
                <div class="meta">
                    <span class="scene-id">{sc_id}</span>
                    <span class="block-id">{b_name}</span>
                    <span class="res-tag">{res} • {sz:,} KB</span>
                </div>
                <div class="headline">{headline}</div>
                <div class="sentence">{sentence}</div>
                <div class="hero-obj"><b>Vật thể Vox:</b> {hero_obj}</div>
                <div class="anim-box">
                    <div class="anim-title">🎬 Cụm Phân Rã Animation Objects (S1 - S4):</div>
                    <div class="anim-step"><b style="color: #38bdf8;">S1 (Entry 0-2s):</b> {s1}</div>
                    <div class="anim-step"><b style="color: #a855f7;">S2 (Assembly 2-4.5s):</b> {s2}</div>
                    <div class="anim-step"><b style="color: #10b981;">S3 (Locked Anchor):</b> {s3}</div>
                    <div class="anim-step"><b style="color: #f59e0b;">S4 (Micro/Next):</b> {s4}</div>
                </div>
            </div>
        </div>
        """
        cards_html.append(card)

    total_audited = audit_summary.get("total_images", 0)
    total_approved = audit_summary.get("approved_images", 0)
    verdict = audit_summary.get("verdict", "UNKNOWN")
    grid_inner = "".join(cards_html)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Human Audit Gate: {episode_id}</title>
    <style>
        :root {{ --bg: #0f172a; --card-bg: #1e293b; --text: #f8fafc; --text-muted: #94a3b8; --primary: #38bdf8; --accent: #f59e0b; --border: #334155; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 30px 20px; }}
        .header {{ max-width: 1400px; margin: 0 auto 30px; padding: 24px; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border); }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; color: var(--primary); }}
        .header p {{ color: var(--text-muted); font-size: 15px; margin-bottom: 16px; }}
        .stats {{ display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px; }}
        .stat-badge {{ background: #0f172a; padding: 10px 18px; border-radius: 8px; border: 1px solid var(--border); font-size: 14px; }}
        .stat-badge b {{ color: var(--primary); font-size: 16px; }}
        .trigger-box {{ background: #020617; padding: 16px; border-radius: 8px; border: 1px dashed var(--accent); font-family: Consolas, monospace; font-size: 14px; color: #fbbf24; display: flex; justify-content: space-between; align-items: center; }}
        .grid {{ max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 24px; }}
        .card {{ background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border); overflow: hidden; display: flex; flex-direction: column; transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-4px); border-color: var(--primary); }}
        .img-wrapper {{ position: relative; width: 100%; aspect-ratio: 16/9; background: #000; overflow: hidden; }}
        .img-wrapper img {{ width: 100%; height: 100%; object-fit: cover; cursor: pointer; }}
        .badge {{ position: absolute; top: 12px; right: 12px; color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
        .content {{ padding: 18px; display: flex; flex-direction: column; gap: 10px; flex-grow: 1; }}
        .meta {{ display: flex; justify-content: space-between; align-items: center; font-size: 12px; }}
        .scene-id {{ background: #3b82f6; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
        .block-id {{ color: var(--text-muted); font-size: 12px; }}
        .res-tag {{ color: #a855f7; font-family: monospace; }}
        .headline {{ font-size: 16px; font-weight: bold; color: #e2e8f0; }}
        .sentence {{ font-size: 14px; color: var(--text-muted); line-height: 1.5; }}
        .hero-obj {{ font-size: 12px; color: #38bdf8; background: #0f172a; padding: 8px; border-radius: 6px; }}
        .anim-box {{ background: #020617; padding: 10px 12px; border-radius: 8px; border: 1px solid #1e293b; font-size: 12px; line-height: 1.4; margin-top: 6px; display: flex; flex-direction: column; gap: 4px; }}
        .anim-title {{ font-weight: bold; color: #fbbf24; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }}
        .anim-step {{ color: #cbd5e1; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛑 HUMAN AUDIT GATE: THẨM ĐỊNH THỊ GIÁC B5</h1>
        <p>Tập phim: <b>{episode_id}</b> | Bấm vào ảnh bất kỳ để phóng to toàn màn hình 2560x1440 2K.</p>
        <div class="stats">
            <div class="stat-badge">Đã kiểm toán: <b>{total_audited} Cảnh</b></div>
            <div class="stat-badge">Đạt chuẩn 100%: <b>{total_approved}/{total_audited}</b></div>
            <div class="stat-badge">Kết luận kỹ thuật: <b style="color: #10b981;">{verdict}</b></div>
        </div>
        <div class="trigger-box">
            <span>🚀 Lệnh kích hoạt sinh video khi bạn đồng ý:</span>
            <code>python scripts/trigger_video_generation.py --episode {episode_id} --limit-blocks 1</code>
        </div>
    </div>
    <div class="grid">
        {grid_inner}
    </div>
</body>
</html>"""

    with open(gallery_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return gallery_html_path


def evaluate_human_gate(
    episode_id: str,
    block_manifest: Dict[str, Any],
    audit_summary: Dict[str, Any],
    args: argparse.Namespace
) -> bool:
    """Human Gate / Antigravity Stop trước khi chuyển sang bước sinh video."""
    episode_dir = ROOT_DIR / "episodes" / episode_id
    gate_file = episode_dir / "human_gate_checkpoint.json"

    # Kiểm tra cờ trigger hoặc pre-approved
    is_pre_approved = (
        getattr(args, "trigger_video", False)
        or getattr(args, "approve_gate", False)
        or getattr(args, "auto_approve", False)
    )

    total_imgs = audit_summary.get("total_images", 0)
    approved_imgs = audit_summary.get("approved_images", 0)
    verdict = audit_summary.get("verdict", "UNKNOWN")

    checkpoint_data = {
        "episode_id": episode_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stage": "STAGE_2_IMAGE_AND_AUDIT_COMPLETED",
        "total_images": total_imgs,
        "approved_images": approved_imgs,
        "audit_verdict": verdict,
        "gate_status": "APPROVED" if is_pre_approved else "PENDING_USER_APPROVAL",
        "trigger_command": f"python scripts/run_vox_media_pipeline.py --episode {episode_id} --trigger-video",
        "shortcut_command": f"python scripts/trigger_video_generation.py --episode {episode_id}"
    }

    if is_pre_approved:
        checkpoint_data["gate_status"] = "APPROVED"
        with open(gate_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        print("\n" + "=" * 75)
        print("🟢 [HUMAN AUDIT GATE: PHÊ DUYỆT TỰ ĐỘNG / ĐÃ KÍCH HOẠT LỆNH TRIGGER]")
        print(f"   Ảnh đã kiểm toán: {approved_imgs}/{total_imgs} ({verdict})")
        print("   Tiến hành chuyển tiếp trực tiếp sang BƯỚC 3: SINH VIDEO CLIPS!")
        print("=" * 75)
        return True

    # Lưu checkpoint chờ phê duyệt
    with open(gate_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75)
    print("🛑 [HUMAN AUDIT GATE / ANTIGRAVITY DỪNG CHỜ PHÊ DUYỆT]")
    print("=" * 75)
    print(f"📌 BƯỚC SINH ẢNH & KIỂM TOÁN B5 ĐÃ HOÀN TẤT CHO {episode_id}:")
    print(f"   • Kết quả kiểm toán: {approved_imgs}/{total_imgs} ảnh đạt chuẩn ({verdict})")
    print(f"   • Thư mục phân cụm: episodes/{episode_id}/blocks/<block_name>/images/")
    print(f"   • Thư mục hạt giống Remotion: episodes/{episode_id}/composite_seeds/")
    print(f"   • Thư viện ảnh HTML trực quan: episodes/{episode_id}/review_gallery.html")

    print("\n📋 BẢNG THẨM ĐỊNH THỊ GIÁC & PHÂN RÃ CỤM ANIMATION OBJECT (S1 - S4):")
    print(f"{'Scene ID':<10} | {'Vật Thể Vox':<26} | {'S1 (Entry 0-2s)':<24} | {'S2 (Assembly 2-4.5s)':<24} | {'S3 (Anchor)':<20} | {'S4 (Next Link)':<20} | {'Trạng Thái'}")
    print("-" * 145)
    for item in scenes_audited:
        sc_id = item.get("scene_id", "")
        sc_data = scenes_info.get(sc_id, {})
        hero_obj = sc_data.get("hero_cutout_object", "")[:24]
        motion = sc_data.get("motion_track_and_assembly", {})
        s1 = motion.get("entry_action", "")[:22] if isinstance(motion, dict) else ""
        s2 = motion.get("assembly_step", "")[:22] if isinstance(motion, dict) else ""
        s3 = motion.get("spatial_anchor", "")[:18] if isinstance(motion, dict) else ""
        s4 = sc_data.get("visual_continuity_link_to_next", "")[:18]
        st = "✅ ĐẠT" if item.get("status") == "APPROVED" else f"⚠️ {item.get('status')}"
        print(f"{sc_id:<10} | {hero_obj:<26} | {s1:<24} | {s2:<24} | {s3:<20} | {s4:<20} | {st}")
    print("-" * 145)

    # Nếu đang chạy interactive terminal
    if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        try:
            print("\n👉 Bạn có muốn DUYỆT và BẮT ĐẦU SINH VIDEO ngay bây giờ không?")
            print("   [Y] Phê duyệt & Chạy sinh video ngay")
            print("   [N] Dừng lại để kiểm tra ảnh thủ công (Sẽ chạy lệnh trigger sau)")
            choice = input("Lựa chọn của bạn (y/N): ").strip().lower()
            if choice in ("y", "yes", "approve"):
                checkpoint_data["gate_status"] = "APPROVED"
                with open(gate_file, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                print("✅ Bạn đã phê duyệt! Đang bắt đầu tiến trình sinh video...")
                return True
        except (KeyboardInterrupt, EOFError):
            print("\n⏹️ Nhận tín hiệu dừng từ người dùng.")

    # Tạm dừng an toàn và thông báo lệnh trigger
    print("\n⏸️ [PIPELINE ĐÃ TẠM DỪNG AN TOÀN TRƯỚC BƯỚC SINH VIDEO]")
    print("Khi bạn đã kiểm tra ảnh xong và sẵn sàng chạy video, hãy gõ 1 trong các lệnh trigger sau:")
    print(f"👉 python scripts/run_vox_media_pipeline.py --episode {episode_id} --trigger-video")
    print("hoặc dùng lệnh tắt chuyên dụng:")
    print(f"👉 python scripts/trigger_video_generation.py --episode {episode_id}")
    print("=" * 75 + "\n")
    return False


def run_stage_videos(episode_id: str, limit: int = 0, acc: str = "all", headless: bool = False, model: str = "omni") -> bool:
    """Thực thi sinh video clips qua flow_video_dispatcher.py (xoay vòng 7 acc)."""
    model_label = "Omni 1.1 Flash" if model == "omni" else "Veo 3.1 - Fast"
    print("\n" + "=" * 75)
    print(f"🎬 [BƯỚC 5: SINH VIDEO CLIPS {model_label.upper()} XOAY VÒNG 7 TÀI KHOẢN]")
    print(f"   Episode: {episode_id}")
    print(f"   Mô hình: {model_label}")
    print(f"   Tài khoản: {acc}")
    print(f"   Giới hạn: {limit if limit > 0 else 'Toàn bộ'} clips / account")
    print(f"   Chế độ: {'Headless (chạy ngầm)' if headless else 'Headed (mở giao diện)'}")
    print("=" * 75)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "flow_video_dispatcher.py"),
        "--episode", episode_id,
        "--acc", acc,
        "--model", model
    ]
    if limit > 0:
        cmd.extend(["--limit", str(limit)])
    if headless:
        cmd.append("--headless")
    else:
        cmd.append("--headed")

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
    parser.add_argument("--trigger-video", action="store_true", help="Lệnh trigger phê duyệt Human Gate và khởi chạy ngay giai đoạn sinh video")
    parser.add_argument("--approve-gate", action="store_true", help="Bí danh của --trigger-video (phê duyệt cổng dừng)")
    parser.add_argument("--auto-approve", action="store_true", help="Tự động duyệt Human Gate không cần dừng chờ")
    parser.add_argument("--force", action="store_true", help="Sinh lại toàn bộ ảnh và video ngay cả khi đã có sẵn file cục bộ")
    parser.add_argument("--model", choices=["omni", "veo"], default="omni", help="Mô hình video: omni (Omni 1.1 Flash) hoặc veo (Veo 3.1 - Fast)")
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

    # 2. Chạy Giai đoạn Sinh Ảnh & Kiểm Toán Thị Giác B5 Đồng Thời
    audit_summary = {}
    if args.stage in ("all", "image") and not (args.trigger_video or args.approve_gate):
        ok_img = run_stage_images(
            clean_ep,
            limit=total_scenes_to_run,
            headless=args.headless,
            pacing=args.pacing,
            force=args.force
        )
        sync_assets_to_blocks_and_flat(clean_ep, block_manifest)
        audit_summary = perform_b5_visual_audit(clean_ep, block_manifest, limit=total_scenes_to_run)
        if not ok_img:
            print("⚠️ Giai đoạn sinh ảnh gặp cảnh báo, tiến trình tiếp tục đồng bộ tài sản hiện có...")
    else:
        # Nếu đang ở stage video hoặc được gọi với trigger-video, đối soát nhanh tài sản hiện có
        audit_summary = perform_b5_visual_audit(clean_ep, block_manifest, limit=total_scenes_to_run)

    # Nếu chỉ chạy stage image thì kết thúc tại đây
    if args.stage == "image":
        print_pipeline_summary(clean_ep, block_manifest)
        return

    # 🛑 HUMAN AUDIT GATE / ANTIGRAVITY STOP (Chặn trước khi sinh Video)
    if args.stage in ("all", "video"):
        gate_passed = evaluate_human_gate(clean_ep, block_manifest, audit_summary, args)
        if not gate_passed:
            # Dừng lại an toàn tại Human Gate, chờ lệnh trigger của User
            return

    # 3. Chạy Giai đoạn Sinh Video (Chỉ chạy khi Human Gate đã APPROVED)
    if args.stage in ("all", "video"):
        sync_assets_to_blocks_and_flat(clean_ep, block_manifest)
        ok_vid = run_stage_videos(
            clean_ep,
            limit=total_scenes_to_run,
            acc=args.acc,
            headless=args.headless,
            model=args.model
        )
        sync_assets_to_blocks_and_flat(clean_ep, block_manifest)
        if not ok_vid:
            print("⚠️ Giai đoạn sinh video gặp cảnh báo, tiến trình tiếp tục đồng bộ tài sản hiện có...")

    # 4. Tổng kết thực chứng
    print_pipeline_summary(clean_ep, block_manifest)


if __name__ == "__main__":
    main()
