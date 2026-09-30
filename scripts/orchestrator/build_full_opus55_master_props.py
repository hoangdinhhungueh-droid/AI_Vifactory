#!/usr/bin/env python3
"""
scripts/orchestrator/build_full_opus55_master_props.py

Xây dựng Master Props hoàn chỉnh cho Bản C (160 phân cảnh, 100% video)
dưới sự điều phối toàn trình của Claude Opus 5.5 (POW-SIMPLE Suite).
Tuân thủ Rule 120, 125, 128, 134, 136.
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.timeline_editor_agent import audit_and_optimize_timeline, VALID_MOTION_DIRECTIVES

def build_opus55_full_props(episode_id: str) -> Dict[str, Any]:
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    if not ep_dir.exists():
        ep_dir = ROOT_DIR / "workspace" / episode_id

    props_path = ep_dir / "remotion_props.json"
    if not props_path.exists():
        raise FileNotFoundError(f"Missing master props: {props_path}")

    master_props = json.loads(props_path.read_text(encoding="utf-8"))
    scenes = master_props.get("scenes", [])
    if not scenes:
        raise ValueError("Master props has no scenes!")

    total_scenes = len(scenes)
    print(f"🎬 [OPUS 5.5 MASTER] Nạp {total_scenes} phân cảnh từ {props_path}...")

    # Phân nhóm phân cảnh theo 5 Beats để gửi cho Tổng Đạo Diễn Opus 5.5
    # Nếu scene không có trường beat, ước lượng theo tỷ lệ thời lượng
    beat_scenes: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    
    for idx, sc in enumerate(scenes):
        b = sc.get("beat") or sc.get("beat_index")
        if not b:
            # Heuristic phân bổ 5 beat: 0-35 (B1), 36-69 (B2), 70-109 (B3), 110-144 (B4), 145-159 (B5)
            if idx <= 35: b = 1
            elif idx <= 69: b = 2
            elif idx <= 109: b = 3
            elif idx <= 144: b = 4
            else: b = 5
        b_num = max(1, min(5, int(b)))
        sc["beat"] = b_num
        sc["scene_idx"] = idx
        beat_scenes[b_num].append(sc)

    for b in range(1, 6):
        print(f"   * Beat {b}: {len(beat_scenes[b])} phân cảnh")

    # Áp dụng Claude Opus 5.5 Senior Director Cut Review cho từng Beat
    all_optimized_scenes: List[Dict[str, Any]] = []

    for b_idx in range(1, 6):
        curr_batch = beat_scenes[b_idx]
        if not curr_batch:
            continue
        print(f"\n🧠 [OPUS 5.5] Đang điều phối & tối ưu hóa Beat {b_idx} ({len(curr_batch)} scenes)...")
        
        opt_batch = audit_and_optimize_timeline(
            scenes=curr_batch,
            whisper_words=None,
            options={
                "episode_id": episode_id,
                "enable_llm_director": True,
                "model": "claude-opus-5-5",
                "timeout_sec": 60.0
            }
        )

        # Hậu kiểm & Chuẩn hóa sâu theo POW-SIMPLE Suite của Opus 5.5
        for s_idx, sc in enumerate(opt_batch):
            # 1. Kỷ luật hạ cánh Paper Placement Drop & Lock
            sc["enableParallax"] = True
            sc["atmosphericLighting"] = True
            
            # 2. Quy chuẩn thẻ hạ tầng Rule 136 (Clean Speaker Tags)
            spk = sc.get("speakerTag") or ""
            # Loại bỏ tiền tố rò rỉ mã asset hoặc lặp tiêu đề thô
            if not spk or "ARCHIVE" in spk or ".png" in spk or ".jpg" in spk or ":" in spk:
                act = sc.get("actTitle") or f"BEAT {b_idx}"
                clean_title = re.sub(r"^BEAT\s*\d+[:\s\-]*", "", act, flags=re.I).strip().upper()
                sc["speakerTag"] = f"BEAT {b_idx} // {clean_title[:32]}"
            
            # 3. Phân bổ Motion Directives linh hoạt, xóa bỏ đơn điệu
            current_md = sc.get("motionDirective")
            if not current_md or current_md not in VALID_MOTION_DIRECTIVES:
                # Phân bổ theo ngữ cảnh nội dung
                stat_val = sc.get("statValue")
                overlay = sc.get("forensicOverlay") or sc.get("forensic_overlay")
                has_fg = bool(sc.get("foreground"))
                
                if stat_val and any(char.isdigit() for char in str(stat_val)):
                    sc["motionDirective"] = "counter_rollup"
                    sc["cameraMovement"] = "dramatic_push"
                    sc["transition"] = "push_zoom"
                elif overlay and overlay.get("type") in ["kinetic_headline", "redacted_doc", "smoking_gun"]:
                    sc["motionDirective"] = "yellow_marker_highlight"
                    sc["cameraMovement"] = "forensic_lock"
                    sc["transition"] = "paper_wipe"
                elif has_fg and (s_idx % 3 == 0):
                    sc["motionDirective"] = "subtle_drift"
                    sc["cameraMovement"] = "slow_push_in"
                    sc["transition"] = "match_cut"
                else:
                    sc["motionDirective"] = "subtle_drift"
                    sc["cameraMovement"] = "continuous_drift"
                    sc["transition"] = "cut"

            all_optimized_scenes.append(sc)

    # Đảm bảo giữ đúng thứ tự 160 phân cảnh ban đầu
    all_optimized_scenes.sort(key=lambda x: x.get("scene_idx", 0))

    # Xây dựng Props tổng thể
    opus55_props = dict(master_props)
    opus55_props["scenes"] = all_optimized_scenes
    opus55_props["project_id"] = f"{episode_id}_OPUS55_MASTER"
    opus55_props["director_model"] = "claude-opus-5-5"
    opus55_props["edition"] = "Bản C - Opus 5.5 Showrunner Directed Master"

    out_props_path = ep_dir / "final_opus55_master_props.json"
    out_props_path.write_text(json.dumps(opus55_props, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n🎉 [OPUS 5.5 MASTER] Đã ghi nhận Master Props 160 phân cảnh tại: {out_props_path} ({round(out_props_path.stat().st_size/1024, 1)} KB)")

    return {
        "status": "success",
        "episode_id": episode_id,
        "scenes_count": len(all_optimized_scenes),
        "props_path": str(out_props_path)
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_full_opus55_master_props.py <EPISODE_ID>")
        sys.exit(1)
    ep = sys.argv[1]
    res = build_opus55_full_props(ep)
    print(json.dumps(res, indent=2, ensure_ascii=False))
