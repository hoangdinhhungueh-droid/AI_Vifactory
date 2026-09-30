#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/orchestrator/run_beat1_opus_pilot.py
Hook Beat 1 Comparative Pilot Runner (Rule 122 & Claude Opus 5.5 POW-SIMPLE Suite)

Trích xuất 60 giây mở đầu (Hook Beat 1) của EP0006, áp dụng Tổng Đạo Diễn Claude Opus 5.5
để gán đầy đủ các Motion Directives (Yellow Marker Highlight, Rolling Counter Punch,
Tactile Stamp Slam, Seamless Push Zoom & Paper Wipe) và render clip đối chứng độc lập.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.timeline_editor_agent import audit_and_optimize_timeline


def prepare_and_render_pilot(
    episode_id: str,
    target_duration_sec: float = 60.0
) -> dict:
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    if not ep_dir.exists():
        ep_dir = Path(f"workspace/{episode_id}")

    props_path = ep_dir / "remotion_props.json"
    if not props_path.exists():
        raise FileNotFoundError(f"Missing master props: {props_path}")

    master_props = json.loads(props_path.read_text(encoding="utf-8"))
    scenes = master_props.get("scenes", [])
    if not scenes:
        raise ValueError("Master props has no scenes!")

    # 1. Trích xuất các phân cảnh của Beat 1 (khoảng 60 giây đầu = 1800 frames)
    target_frames = int(target_duration_sec * 30)
    beat1_scenes = []
    accum_frames = 0

    for s in scenes:
        dur = int(s.get("durationInFrames") or 90)
        beat1_scenes.append(dict(s))
        accum_frames += dur
        if accum_frames >= target_frames:
            break

    print(f"🎬 [PILOT] Trích xuất {len(beat1_scenes)} phân cảnh Beat 1 ({accum_frames} frames ~ {round(accum_frames/30, 1)}s)")

    # 2. Áp dụng Tổng Đạo Diễn Claude Opus 5.5 để gán Motion Directives
    print("🧠 [PILOT] Kích hoạt Claude Opus 5.5 Senior Director Cut Review...")
    optimized_scenes = audit_and_optimize_timeline(
        scenes=beat1_scenes,
        whisper_words=None,
        options={
            "episode_id": episode_id,
            "enable_llm_director": True,
            "model": "claude-opus-5-5",
            "timeout_sec": 45.0
        }
    )

    # Đảm bảo các phân cảnh có motion directives tiêu biểu của POW-SIMPLE
    for i, sc in enumerate(optimized_scenes):
        if i == 0 and not sc.get("motionDirective"):
            sc["motionDirective"] = "dramatic_push"
            sc["transition"] = "push_zoom"
        elif i == 1 and not sc.get("motionDirective"):
            sc["motionDirective"] = "yellow_marker_highlight"
            sc["transition"] = "paper_wipe"
        elif i == 2 and not sc.get("motionDirective"):
            sc["motionDirective"] = "counter_rollup"
            sc["transition"] = "tape_snap"
        elif i == 3 and not sc.get("motionDirective"):
            sc["motionDirective"] = "forensic_lock"
            sc["transition"] = "push_zoom"

    pilot_props = dict(master_props)
    pilot_props["scenes"] = optimized_scenes
    pilot_props["project_id"] = f"{episode_id}_PILOT_BEAT1"

    pilot_props_path = ep_dir / "pilot_beat1_props.json"
    pilot_props_path.write_text(json.dumps(pilot_props, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ [PILOT] Đã lưu pilot props tại: {pilot_props_path}")

    # 3. Render clip thử nghiệm Remotion (pilot_opus55_beat1.mp4)
    out_video = ep_dir / "pilot_opus55_beat1.mp4"
    remotion_dir = Path("/root/video_factory/remotion")
    if not remotion_dir.exists():
        remotion_dir = ROOT_DIR / "remotion"

    cmd = [
        "npx", "remotion", "render",
        "src/index.tsx", "TwoLayerEpisode",
        str(out_video),
        f"--props={str(pilot_props_path)}",
        "--concurrency=2",
        "--gl=angle"
    ]
    print(f"🚀 [PILOT] Bắt đầu render Remotion: {' '.join(cmd)}")
    start_t = time.time()
    res = subprocess.run(cmd, cwd=str(remotion_dir), capture_output=True, text=True)
    render_elapsed = round(time.time() - start_t, 1)

    if res.returncode != 0:
        print(f"❌ [PILOT] Render Remotion thất bại (exit {res.returncode}):\n{res.stderr[:1000]}")
        return {"status": "failed", "error": res.stderr}

    out_size = out_video.stat().st_size if out_video.exists() else 0
    print(f"🎉 [PILOT] Render hoàn tất trong {render_elapsed}s! File: {out_video} ({round(out_size/1048576, 2)} MB)")

    # 4. Trích xuất frame so sánh (Frame 60, 300, 600, 1200)
    frames_dir = ep_dir / "pilot_comparison_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f_idx in [60, 300, 600, 1200]:
        t_sec = f_idx / 30.0
        # Trích xuất từ pilot mới
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(t_sec), "-i", str(out_video),
            "-vframes", "1", "-q:v", "2", str(frames_dir / f"pilot_frame_{f_idx:04d}.jpg")
        ], capture_output=True)

        # Trích xuất từ master baseline cũ
        master_video = ep_dir / "final_169.mp4"
        if master_video.exists():
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(t_sec), "-i", str(master_video),
                "-vframes", "1", "-q:v", "2", str(frames_dir / f"baseline_frame_{f_idx:04d}.jpg")
            ], capture_output=True)

    print(f"📸 [PILOT] Đã trích xuất các khung hình đối soát side-by-side tại: {frames_dir}")
    return {
        "status": "success",
        "video_path": str(out_video),
        "video_size_mb": round(out_size / 1048576, 2),
        "frames_dir": str(frames_dir),
        "elapsed_sec": render_elapsed
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_beat1_opus_pilot.py <EPISODE_ID> [TARGET_DURATION_SEC]")
        sys.exit(1)
    ep = sys.argv[1]
    sec = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    res = prepare_and_render_pilot(ep, sec)
    print(json.dumps(res, indent=2, ensure_ascii=False))
