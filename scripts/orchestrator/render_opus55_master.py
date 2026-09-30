#!/usr/bin/env python3
"""
scripts/orchestrator/render_opus55_master.py

End-to-End Master Render & YouTube Private Publisher cho Bản C (Opus 5.5).
1. Render Remotion TwoLayerEpisode -> twolayer_silent_opus55.mp4
2. Mux audio_norm.mp3 & bgm_master.mp3 (sidechain ducking) -> final_opus55_169.mp4
3. Upload Private lên YouTube -> video_id_c
4. Ghi nhận vào publish_ledger.json
Tuân thủ Rule 118, 120, 121, 126, 128, 135, 136.
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

def render_and_publish_opus55(episode_id: str, concurrency: int = 2) -> dict:
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    if not ep_dir.exists():
        ep_dir = ROOT_DIR / "workspace" / episode_id

    props_file = ep_dir / "final_opus55_master_props.json"
    if not props_file.exists():
        raise FileNotFoundError(f"Missing master props: {props_file}")

    remotion_dir = Path("/root/video_factory/remotion")
    if not remotion_dir.exists():
        remotion_dir = ROOT_DIR / "remotion"

    silent_out = ep_dir / "twolayer_silent_opus55.mp4"
    final_out = ep_dir / "final_opus55_169.mp4"
    audio_norm = ep_dir / "audio_norm.mp3"
    bgm_master = ep_dir / "bgm_master.mp3"

    render_dur = 0.0
    if final_out.exists() and final_out.stat().st_size > 50 * 1024 * 1024:
        print(f"⏩ [OPUS 5.5] Video Master Bản C đã tồn tại sẵn: {final_out} ({round(final_out.stat().st_size/1048576, 1)} MB). Bỏ qua render & mux.")
    else:
        # 1. Render Remotion TwoLayerEpisode
        print(f"🎬 [OPUS 5.5] Bắt đầu render Remotion Master Bản C...")
        render_cmd = [
            "npx", "remotion", "render",
            "src/index.tsx", "TwoLayerEpisode",
            str(silent_out),
            f"--props={str(props_file)}",
            f"--concurrency={concurrency}",
            "--gl=angle"
        ]
        
        t0 = time.time()
        res = subprocess.run(render_cmd, cwd=str(remotion_dir), capture_output=True, text=True)
        render_dur = round(time.time() - t0, 1)

        if res.returncode != 0:
            print(f"❌ [OPUS 5.5] Render Remotion thất bại (exit {res.returncode}):\n{res.stderr[-1500:]}")
            return {"status": "failed", "step": "remotion_render", "error": res.stderr}

        print(f"✅ [OPUS 5.5] Render Remotion hoàn tất trong {render_dur}s ({round(silent_out.stat().st_size/1048576, 1)} MB)")

        # 2. Mux Audio & BGM Sidechain Ducking
        print("🎵 [OPUS 5.5] Muxing audio_norm và bgm_master với Sidechain Ducking...")
        
        def probe_dur(p):
            out = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(p)
            ]).decode().strip()
            return float(out or 0.0)

        v_dur = probe_dur(silent_out)
        a_dur = probe_dur(audio_norm) if audio_norm.exists() else v_dur

        if bgm_master.exists():
            bgm_dur = probe_dur(bgm_master)
            loop_args = ["-stream_loop", "-1"] if bgm_dur < a_dur - 1.0 else []
            af = (
                "[1:a]volume=1.0,asplit=2[tts_clean][tts_sc];"
                "[2:a]volume=0.09,highpass=f=85,equalizer=f=2500:t=q:w=1.5:g=-5[bgm_eq];"
                "[bgm_eq][tts_sc]sidechaincompress=threshold=0.02:ratio=10:attack=80:release=350[bgm_ducked];"
                "[tts_clean][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,alimiter=limit=0.84:attack=5:release=50[aout]"
            )
            mux_cmd = [
                "ffmpeg", "-y",
                "-i", str(silent_out),
                "-i", str(audio_norm),
                *loop_args, "-i", str(bgm_master),
                "-filter_complex", af,
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(final_out)
            ]
        else:
            mux_cmd = [
                "ffmpeg", "-y",
                "-i", str(silent_out),
                "-i", str(audio_norm),
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(final_out)
            ]

        mux_res = subprocess.run(mux_cmd, capture_output=True, text=True)
        if mux_res.returncode != 0:
            print(f"❌ [OPUS 5.5] Mux audio thất bại: {mux_res.stderr[-1000:]}")
            return {"status": "failed", "step": "audio_mux", "error": mux_res.stderr}

        print(f"🎉 [OPUS 5.5] Video Master Bản C hoàn chỉnh: {final_out} ({round(final_out.stat().st_size/1048576, 1)} MB)")

    # 3. Upload YouTube ở chế độ Private
    print("🚀 [OPUS 5.5] Uploading Bản C lên YouTube ở chế độ PRIVATE...")
    from app.services.youtube_upload import upload_video
    
    # Nạp metadata từ seo_payload_b10 hoặc youtube_upload_payload
    payload_file = ep_dir / "youtube_upload_payload.json"
    if payload_file.exists():
        payload = json.loads(payload_file.read_text(encoding="utf-8"))
    else:
        payload = {
            "title": f"Foreign Capital US Stocks (Edition C - Opus 5.5 Master)",
            "description": f"Master Video Edition C directed by Claude Opus 5.5.\n\n#ForeignCapital #Opus55",
            "tags": ["foreign capital US stocks", "opus 5.5", "motion graphics"]
        }

    # Đặt title phân biệt rõ cho Bản C
    payload["title"] = f"Foreign Capital US Stocks (Edition C - Opus 5.5 Master)"
    payload["export"] = {"target_file": "final_opus55_169.mp4"}

    try:
        sub_file = ep_dir / "subtitles_en.srt"
        if not sub_file.exists():
            sub_file = ep_dir / "subtitles.srt"

        up_res = upload_video(
            video_path=str(final_out),
            title=payload["title"],
            description=payload.get("description", ""),
            tags=payload.get("tags", []),
            category_id=str(payload.get("category_id", "22")),
            privacy_status="private",
            market="en",
            subtitles_path=str(sub_file) if sub_file.exists() else None
        )
        video_id_c = up_res.get("id") or up_res.get("video_id")
        yt_url = f"https://www.youtube.com/watch?v={video_id_c}"
        print(f"✅ [OPUS 5.5] Upload thành công Bản C lên YouTube! URL: {yt_url}")
    except Exception as e:
        print(f"⚠️ [OPUS 5.5] Lỗi upload YouTube: {e}")
        video_id_c = None
        yt_url = None

    # 4. Ghi nhận vào publish ledger
    ledger_path = Path("/var/vf/data/publish_ledger.json")
    if ledger_path.exists() and video_id_c:
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger[video_id_c] = {
                "video_id": video_id_c,
                "title": payload["title"],
                "edition": "Bản C - Opus 5.5 Showrunner Master",
                "episode_dir": str(ep_dir),
                "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "private",
                "published_at": None
            }
            ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as le:
            print(f"⚠️ Ghi ledger warning: {le}")

    return {
        "status": "success",
        "video_path": str(final_out),
        "video_size_mb": round(final_out.stat().st_size/1048576, 1),
        "video_id_c": video_id_c,
        "youtube_url": yt_url,
        "render_time_sec": render_dur
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render_opus55_master.py <EPISODE_ID> [CONCURRENCY]")
        sys.exit(1)
    ep = sys.argv[1]
    conc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    res = render_and_publish_opus55(ep, conc)
    print(json.dumps(res, indent=2, ensure_ascii=False))
