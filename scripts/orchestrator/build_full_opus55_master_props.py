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
from app.services.build_remotion_props import extract_stat_card, synthesize_scene_motion_props


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
    m_code = episode_id[:2].upper() if len(episode_id) >= 2 else "EN"
    print(f"🎬 [OPUS 5.5 MASTER] Nạp {total_scenes} phân cảnh từ {props_path}...")

    # Phân nhóm phân cảnh theo 5 Beats tỷ lệ động (Rule 128 Generic Percentile)
    beat_scenes: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: [], 4: [], 5: []}

    for idx, sc in enumerate(scenes):
        b = sc.get("beat") or sc.get("beat_index")
        if not b:
            pct = idx / max(1, total_scenes)
            if pct < 0.22:
                b = 1
            elif pct < 0.44:
                b = 2
            elif pct < 0.68:
                b = 3
            elif pct < 0.88:
                b = 4
            else:
                b = 5
        b_num = max(1, min(5, int(b)))
        sc["beat"] = b_num
        sc["scene_idx"] = idx
        beat_scenes[b_num].append(sc)

    for b in range(1, 6):
        print(f"   * Beat {b}: {len(beat_scenes[b])} phân cảnh")

    all_optimized_scenes: List[Dict[str, Any]] = []
    intra_transitions = ["paper_slide", "vox_push_zoom", "match_cut"]

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

        for s_idx, sc in enumerate(opt_batch):
            global_idx = int(sc.get("scene_idx", s_idx))
            board_idx = global_idx // 4
            board_pos = global_idx % 4
            sc["boardId"] = f"board_{board_idx + 1:03d}"
            sc["boardPosition"] = board_pos
            sc["enableParallax"] = True
            sc["atmosphericLighting"] = True

            # Quy chuẩn thẻ hạ tầng Rule 136 (Clean Speaker Tags)
            spk = sc.get("speakerTag") or ""
            if not spk or "ARCHIVE" in spk or ".png" in spk or ".jpg" in spk or ":" in spk:
                act = sc.get("actTitle") or f"BEAT {b_idx}"
                clean_title = re.sub(r"^BEAT\s*\d+[:\s\-]*", "", act, flags=re.I).strip().upper()
                sc["speakerTag"] = f"BEAT {b_idx} // {clean_title[:32]}"

            # Trích xuất Stat Card đa ngôn ngữ nếu chưa có
            stat_val = sc.get("statValue")
            stat_lbl = sc.get("statLabel")
            if not stat_val:
                stat_val, stat_lbl = extract_stat_card(sc)
                if stat_val:
                    sc["statValue"] = stat_val
                    sc["statLabel"] = stat_lbl

            # Phân bổ Motion Directives & Transition_out chuẩn Stateful Board (hard_cut <= 15%)
            overlay = sc.get("forensicOverlay") or sc.get("forensic_overlay")
            has_fg = bool(sc.get("foreground"))
            current_md = sc.get("motionDirective")
            if not current_md or current_md not in VALID_MOTION_DIRECTIVES:
                if stat_val and any(char.isdigit() for char in str(stat_val)):
                    sc["motionDirective"] = "counter_rollup"
                    sc["cameraMovement"] = "dramatic_push"
                elif overlay and isinstance(overlay, dict) and overlay.get("type") in ["kinetic_headline", "redacted_doc", "smoking_gun"]:
                    sc["motionDirective"] = "yellow_marker_highlight"
                    sc["cameraMovement"] = "forensic_lock"
                elif has_fg and (s_idx % 3 == 0):
                    sc["motionDirective"] = "subtle_drift"
                    sc["cameraMovement"] = "slow_push_in"
                else:
                    sc["motionDirective"] = "subtle_drift"
                    sc["cameraMovement"] = "continuous_drift"

            if board_pos < 3:
                t_out = intra_transitions[(board_idx + board_pos) % len(intra_transitions)]
            else:
                t_out = "hard_cut" if (board_idx % 4 == 3) else "push_through"
            sc["transition_out"] = t_out
            sc["transition"] = t_out

            # Tổng hợp Vector nhân quả / thời gian + Fact-Safety Uncertainty Guard
            meta = synthesize_scene_motion_props(
                sc,
                sc.get("foregroundPosition", "left"),
                overlay if isinstance(overlay, dict) else None,
                stat_val,
                stat_lbl,
                global_idx,
                market=m_code,
            )
            sc["connection"] = meta["connection"]
            sc["connections"] = meta["connections"]
            sc["radiatingConnections"] = meta["radiating_connections"]
            sc["supportingCutouts"] = meta["supporting_cutouts"]
            sc["editorialHeadline"] = meta["editorial_headline"]

            all_optimized_scenes.append(sc)

    all_optimized_scenes.sort(key=lambda x: x.get("scene_idx", 0))

    opus55_props = dict(master_props)
    opus55_props["scenes"] = all_optimized_scenes
    opus55_props["project_id"] = f"{episode_id}_OPUS55_MASTER"
    opus55_props["director_model"] = "claude-opus-5-5"
    opus55_props["edition"] = "Opus 5.5 Showrunner Directed Master"

    out_props_path = ep_dir / "final_opus55_master_props.json"
    out_props_path.write_text(json.dumps(opus55_props, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n🎉 [OPUS 5.5 MASTER] Đã ghi nhận Master Props ({len(all_optimized_scenes)} phân cảnh) tại: {out_props_path} ({round(out_props_path.stat().st_size/1024, 1)} KB)")

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
