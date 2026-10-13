#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/scan_real_episodes.py — Scans real episodes from /var/vf/episodes/ on VPS.
Extracts genuine execution status, stage artifacts, and progress for Pipeline Observability UI.
"""
import sys
import json
import gzip
import base64
import pathlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

def scan_local_or_vps_episodes():
    episodes_dir = pathlib.Path("/var/vf/episodes")
    if not episodes_dir.exists():
        # Check local data fallback
        local_cache = ROOT_DIR / "data" / "vps_episodes_telemetry.json"
        if local_cache.exists():
            return json.loads(local_cache.read_text(encoding="utf-8"))
        return []

    results = []
    for p in sorted(episodes_dir.iterdir()):
        if not p.is_dir() or p.name.startswith(("_", ".")) or p.name in ("VOX_ARCHITECTURE_E2E",):
            continue
        
        ep_id = p.name
        market = ep_id.split("_")[0] if "_" in ep_id else "GLOBAL"
        
        has_competitor = (p / "competitor_intel_card.json").exists()
        has_grounding = (p / "grounding_intel.json").exists()
        has_story = (p / "story.txt").exists() or (p / "spoken_script.txt").exists()
        has_audio = (p / "tts_out.mp3").exists() or (p / "beats.json").exists()
        has_director = (p / "director_plan.json").exists()
        has_prompts = (p / "prompts_forge.json").exists()
        has_images = (p / "images").exists() and any((p / "images").glob("*.png"))
        has_b5_audit = (p / "b5_audit_report.json").exists()
        has_props = (p / "remotion_props.json").exists()
        has_video = (p / "final_169.mp4").exists()
        
        state_file = p / "b4b10_state.json"
        state_info = {}
        if state_file.exists():
            try:
                state_info = json.loads(state_file.read_text())
            except Exception:
                pass
                
        is_active_running = state_info.get("status") == "running"
        
        if has_video:
            current_step = 18
            status = "completed"
            active_artifact = "final_169.mp4 (Master Video Sẵn Sàng)"
            current_stage_name = "Hoàn tất Video Master MP4"
        elif has_props:
            current_step = 15
            status = "running" if is_active_running else "ready_to_render"
            active_artifact = "remotion_props.json (Đang render Remotion CPU...)" if is_active_running else "remotion_props.json"
            current_stage_name = "B7: Render Video Master Remotion"
        elif has_images or has_b5_audit:
            current_step = 13
            status = "running" if is_active_running else "in_progress"
            active_artifact = "images/ + b5_audit_report.json"
            current_stage_name = "B5: Kiểm Toán Thị Giác & Tách Phông"
        elif has_prompts:
            current_step = 10
            status = "in_progress"
            active_artifact = "prompts_forge.json"
            current_stage_name = "B4: Sinh Ảnh Trình Duyệt Gemini"
        elif has_director:
            current_step = 8
            status = "in_progress"
            active_artifact = "director_plan.json"
            current_stage_name = "B3: Đạo Diễn Hình Ảnh & Phân Cảnh"
        elif has_audio:
            current_step = 7
            status = "in_progress"
            active_artifact = "tts_out.mp3 + subtitles.srt"
            current_stage_name = "B2.6: Hollywood Audio Spine & Edge-TTS"
        elif has_story:
            current_step = 5
            status = "in_progress"
            active_artifact = "story.txt"
            current_stage_name = "B2: Kịch Bản 5-Beat Docudrama"
        elif has_grounding:
            current_step = 3
            status = "in_progress"
            active_artifact = "grounding_intel.json"
            current_stage_name = "B1.5.5: Kiểm Chứng Fact Grounding"
        elif has_competitor:
            current_step = 2
            status = "in_progress"
            active_artifact = "competitor_intel_card.json"
            current_stage_name = "B1.5: Do Thám Video Đối Thủ"
        else:
            current_step = 1
            status = "pending"
            active_artifact = "task_payload.json"
            current_stage_name = "B1: Khám Phá Xu Hướng Google Trends"

        results.append({
            "episode_id": ep_id,
            "market": market,
            "current_step_index": current_step,
            "status": status,
            "is_active_running": is_active_running,
            "current_stage_name": current_stage_name,
            "active_artifact": active_artifact,
            "has_video": has_video,
            "mtime": p.stat().st_mtime
        })

    # Sort: running first, then newest mtime
    results.sort(key=lambda x: (not x["is_active_running"], -x["mtime"]))
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--vps-run":
        eps = scan_local_or_vps_episodes()
        # Save to VPS data directory
        p_out = pathlib.Path("/root/video_factory/data/vps_episodes_telemetry.json")
        p_out.parent.mkdir(parents=True, exist_ok=True)
        raw_json = json.dumps(eps, ensure_ascii=False, indent=2)
        p_out.write_text(raw_json, encoding="utf-8")
        
        # Output compressed base64
        gz_data = gzip.compress(raw_json.encode("utf-8"))
        b64 = base64.b64encode(gz_data).decode("ascii")
        print(f"GZ_B64:{b64}")
        sys.exit(0)

    # When executed locally, call VPS to run this script
    from scripts.sync_file_to_vps import sync_file
    from scripts.vps_runner import run_vps_cmd

    sync_file("scripts/scan_real_episodes.py")
    res = run_vps_cmd("python3 /root/video_factory/scripts/scan_real_episodes.py --vps-run")
    if isinstance(res, dict) and res.get("status") == "ok":
        stdout = res.get("stdout", "").strip()
        for line in stdout.splitlines():
            if line.startswith("GZ_B64:"):
                b64_str = line[7:].strip()
                raw_bytes = gzip.decompress(base64.b64decode(b64_str))
                eps = json.loads(raw_bytes.decode("utf-8"))
                print(f"✅ Discovered {len(eps)} real episodes from VPS:")
                for ep in eps:
                    run_tag = "⚡ [RUNNING]" if ep["is_active_running"] else f"[{ep['status'].upper()}]"
                    print(f"  • {run_tag} {ep['episode_id']} ({ep['market']}) — Bước {ep['current_step_index']}/19: {ep['current_stage_name']}")
                
                # Save local cache
                cache_path = ROOT_DIR / "data" / "vps_episodes_telemetry.json"
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(eps, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"\n✅ Cached {len(eps)} real episodes to {cache_path}")
                break
