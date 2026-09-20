#!/usr/bin/env python3
"""
scripts/render_preview_2min.py

Renders a 2-minute (120s / 3600 frames) preview of an episode using the new
Vox Object-Driven Continuous Storyboard Architecture.
Automatically:
1. Renders visual video (frames 0-3599) via Remotion TwoLayerEpisode.
2. Muxes with first 120s of TTS + BGM with Sidechain Ducking -> preview_2min_master.mp4.
3. Extracts 5 key audit frames (Kinetic Counter, Evidence Board, Doc Highlight, Map, 3D Prop).
4. Dispatches the master preview video & photos directly to User Telegram.
"""
import os
import sys
import time
import json
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

EPISODE_ID = "EN_EP0003_san_diego_daycare_fraud"
EP_DIR = Path(f"/var/vf/episodes/{EPISODE_ID}")
PROPS_FILE = EP_DIR / "remotion_props.json"
SILENT_OUT = EP_DIR / "preview_2min_silent.mp4"
MASTER_OUT = EP_DIR / "preview_2min_master.mp4"
AUDIT_DIR = EP_DIR / "audits" / "preview_2min"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_FRAMES = 3600 # Exactly 120.0 seconds @ 30fps

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def send_telegram_msg(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        log(f"Telegram error: {e}")

def send_telegram_video(video_path, caption):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    log(f"Sending video ({video_path.stat().st_size / (1024*1024):.1f} MB) to Telegram...")
    try:
        with open(video_path, "rb") as vf:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML", "supports_streaming": "true"},
                files={"video": vf},
                timeout=180,
            )
        log(f"Telegram video sent. Response status: {resp.status_code}")
    except Exception as e:
        log(f"Telegram sendVideo error: {e}")

def main():
    log("=== STARTING 2-MINUTE PREVIEW PIPELINE (VOX ARCHITECTURE) ===")
    t0 = time.time()

    # Step 1: Render Visual Frames (0-3599)
    log(f"Step 1: Rendering {TOTAL_FRAMES} frames (0-3599) via Remotion...")
    render_script = _REPO_ROOT / "scripts" / "render_twolayer_visual.py"
    render_cmd = [
        sys.executable, str(render_script),
        "--props", str(PROPS_FILE),
        "--out", str(SILENT_OUT),
        "--frames", f"0-{TOTAL_FRAMES - 1}",
        "--x264-preset", "ultrafast",
        "--crf", "19",
    ]
    env = os.environ.copy()
    env["VF_REMOTION_CONCURRENCY"] = "3"
    
    rc = subprocess.run(render_cmd, env=env)
    if rc.returncode != 0 or not SILENT_OUT.exists():
        log(f"FATAL: Visual render failed with code {rc.returncode}")
        send_telegram_msg(f"❌ <b>[Render Failed]</b> Render 2 phút đầu EP EN0003 gặp lỗi (code {rc.returncode}).")
        sys.exit(1)
    
    t_render = time.time() - t0
    log(f"Step 1 Complete: {SILENT_OUT.name} ({SILENT_OUT.stat().st_size / (1024*1024):.1f} MB in {t_render:.1f}s, {TOTAL_FRAMES/t_render:.2f} fps)")

    # Step 2: Audio Muxing with Sidechain Ducking
    log("Step 2: Muxing audio (TTS + BGM with Sidechain Ducking, 120s)...")
    tts_file = EP_DIR / "tts_out.mp3"
    bgm_file = EP_DIR / "bgm_master.mp3"

    mux_cmd = [
        "ffmpeg", "-y",
        "-i", str(SILENT_OUT),
        "-t", "120.0", "-i", str(tts_file),
        "-t", "120.0", "-i", str(bgm_file),
        "-filter_complex",
        "[1:a]volume=1.0,asplit=2[tts_clean][tts_sc];"
        "[2:a]volume=0.09,highpass=f=85,equalizer=f=2500:t=q:w=1.5:g=-5[bgm_eq];"
        "[bgm_eq][tts_sc]sidechaincompress=threshold=0.02:ratio=10:attack=80:release=350[bgm_ducked];"
        "[tts_clean][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,alimiter=limit=0.84:attack=5:release=50[aout]",
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        str(MASTER_OUT)
    ]
    mux_rc = subprocess.run(mux_cmd, capture_output=True, text=True)
    if mux_rc.returncode != 0 or not MASTER_OUT.exists():
        log(f"FATAL: Muxing failed: {mux_rc.stderr}")
        send_telegram_msg("❌ <b>[Mux Failed]</b> Lỗi FFmpeg audio muxing.")
        sys.exit(1)
    
    log(f"Step 2 Complete: Master video ready: {MASTER_OUT} ({MASTER_OUT.stat().st_size / (1024*1024):.1f} MB)")

    # Step 3: Extract Key Forensic Audit Frames
    log("Step 3: Extracting Key Audit Frames for Visual Inspection...")
    key_timestamps = [
        (100, 3.3, "scene00_kinetic_counter.jpg"),
        (350, 11.6, "scene01_evidence_board_fg.jpg"),
        (1200, 40.0, "scene04_document_highlight.jpg"),
        (1700, 56.6, "scene07_tactical_map.jpg"),
        (3350, 111.6, "scene16_3d_evidence_prop.jpg"),
    ]
    for frame_idx, sec, fname in key_timestamps:
        out_f = AUDIT_DIR / fname
        ff_cmd = [
            "ffmpeg", "-y", "-ss", f"{sec:.3f}",
            "-i", str(MASTER_OUT),
            "-frames:v", "1", "-q:v", "2",
            str(out_f)
        ]
        subprocess.run(ff_cmd, capture_output=True)
        log(f"Extracted audit frame: {fname} ({out_f.stat().st_size / 1024:.1f} KB)")

    # Step 4: Dispatch Master Preview to User Telegram
    total_elapsed = time.time() - t0
    caption = (
        f"🎬 <b>[EP EN0003] PREVIEW 2 PHÚT ĐẦU - VOX ARCHITECTURE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Thời lượng:</b> 02:00 (3,600 frames @ 30fps)\n"
        f"⚡ <b>Thời gian render:</b> {total_elapsed/60:.1f} phút ({TOTAL_FRAMES/t_render:.2f} fps)\n"
        f"📦 <b>Dung lượng file:</b> {MASTER_OUT.stat().st_size / (1024*1024):.1f} MB\n\n"
        f"✨ <b>Đặc điểm kiến trúc mới trong video:</b>\n"
        f"1. <b>Vox Tactical Grid Canvas:</b> Blueprint 60px + Halftone Matrix trên Dark Slate (Scene 00-17)\n"
        f"2. <b>Evidence Board & Primary Suspect:</b> Thẻ hồ sơ đối tượng + Cutout nhân vật đổ bóng thực (Scene 01)\n"
        f"3. <b>Document Highlight & Redaction:</b> Hồ sơ thanh tra liên bang với bút dạ vàng + băng che mực (Scene 02-06)\n"
        f"4. <b>Tactical Paper Map:</b> Bản đồ tác chiến kèm vòng radar & tọa độ điều tra (Scene 07, 11)\n"
        f"5. <b>Procedural 3D Evidence Prop:</b> Vật chứng 3D Three.js nguyên khối (Ex. A), vật lý stop-motion 12fps (Scene 16 @ 1:52)\n"
        f"6. <b>Audio Spine:</b> TTS chuẩn studio + BGM Sidechain Ducking tự động dìm nhạc khi có giọng nói."
    )
    target_video = MASTER_OUT
    if MASTER_OUT.stat().st_size > 48 * 1024 * 1024:
        tg_out = EP_DIR / "preview_2min_tg.mp4"
        if not tg_out.exists() or tg_out.stat().st_size == 0:
            log("Master video exceeds 48MB, compressing for Telegram delivery...")
            cmp_cmd = ["ffmpeg", "-y", "-i", str(MASTER_OUT), "-c:v", "libx264", "-crf", "28", "-preset", "faster", "-c:a", "aac", "-b:a", "128k", str(tg_out)]
            subprocess.run(cmp_cmd, capture_output=True)
        if tg_out.exists() and tg_out.stat().st_size > 0:
            target_video = tg_out
            log(f"Using compressed video for Telegram: {target_video} ({target_video.stat().st_size / (1024*1024):.1f} MB)")
    send_telegram_video(target_video, caption)
    log("=== PREVIEW PIPELINE COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
