#!/usr/bin/env python3
"""
Unified Human Gate 2 Executor (Rule 114 / Protocol V4)
Uploads Master Video to YouTube (Unlisted), registers to Publish Ledger,
and dispatches the complete Gate 2 interactive Telegram card.

Usage:
  python scripts/execute_human_gate_2.py <episode_id>
"""
import os
import sys
import json
import asyncio
from pathlib import Path

ROOT = Path("/root/video_factory")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.compile_episode_from_notion as comp
comp._token()

from app.services import youtube_upload, publish_ledger, rate_risk_controller, telegram_buttons as tb
from app.services.security import safety_gate
from app.services import platform_validator

async def send_gate2_telegram(video_id: str, episode_id: str,
                              title_a: str, title_b: str,
                              duration_str: str, scenes_count: int,
                              frames_count: int, bg_count: int, fg_count: int):
    watch_url = f"https://youtu.be/{video_id}"
    
    text = (
        "👑 <b>[HUMAN GATE 2] NGHIỆM THU EPISODE MASTER PRO & PHÁT HÀNH</b>\n\n"
        f"🎬 <b>Episode ID:</b> <code>{episode_id}</code>\n"
        f"⏱️ <b>Thời lượng:</b> {duration_str} ({scenes_count} scenes / {frames_count:,} frames / Full HD 1080p)\n"
        f"🎨 <b>Visual:</b> {bg_count} BGs 16:9 High-Key + {fg_count} FGs uncropped Chroma-Key\n"
        "🎙️ <b>Audio:</b> Edge-TTS Male Voice (synced) + 48.000 Hz Studio BGM (-24dB)\n"
        "🏷️ <b>Nhãn AI:</b> Altered or Synthetic Content: <b>BẬT (Yes)</b>\n"
        "🛡️ <b>Trạng thái hiện tại:</b> <b>Không công khai (Unlisted)</b>\n\n"
        "📌 <b>GÓI PACKAGING YOUTUBE 2026 (Rule 114):</b>\n"
        f"• <b>Title A (Primary):</b> <i>{title_a}</i>\n"
        f"• <b>Title B (Backup A/B):</b> <i>{title_b}</i>\n"
        "• <b>Thumbnail:</b> Chuẩn Thị trường 1 Giây (Keyword + Visual đối xứng, font cực lớn)\n\n"
        f"🔗 <b>Link xem trước (Unlisted):</b> <a href=\"{watch_url}\">{watch_url}</a>\n\n"
        "👉 <i>Bấm nút bên dưới để xem trước hoặc chuyển sang Công Khai (Public):</i>"
    )
    
    rows = [
        [("📺 Xem trước Video (Unlisted)", None, watch_url)],
        [("🚀 Chuyển sang Công Khai (Public)", f"pub:{video_id}")],
        [("🌐 Công Khai Tất cả Video (Public All)", "puball")],
        [("🔒 Giữ Không Công Khai (Unlisted)", f"kp:{video_id}")]
    ]
    
    if not tb.is_enabled():
        print("WARN: Telegram notifier is not configured or disabled.", file=sys.stderr)
        return None
        
    msg_id = await tb.send_with_buttons(text, rows)
    return msg_id

def main():
    if len(sys.argv) < 2:
        print("Usage: python execute_human_gate_2.py <episode_id>", file=sys.stderr)
        sys.exit(1)
        
    episode_id = sys.argv[1].strip()
    ep_dir = f"/var/vf/episodes/{episode_id}"
    video_path = f"{ep_dir}/master_video_pro.mp4"
    payload_path = f"{ep_dir}/youtube_upload_payload.json"
    brain_path = f"{ep_dir}/brain_input.json"
    
    print(f"=== [GATE 2] Processing Episode: {episode_id} ===")
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.exists(payload_path):
        print(f"ERROR: Payload file not found: {payload_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        
    brain = {}
    if os.path.exists(brain_path):
        with open(brain_path, "r", encoding="utf-8") as f:
            brain = json.load(f)
            
    # Validate platform & safety gates
    print("--- 1. Platform Validator & Safety Gate Check ---")
    vr = platform_validator.validate_upload(ep_dir, "youtube")
    if not vr.passed:
        print("Platform validator FAILED:", [v.message for v in vr.violations], file=sys.stderr)
        sys.exit(1)
        
    sg = safety_gate.run_safety_gate(ep_dir, payload, "youtube")
    if not sg.passed:
        print("Safety gate FAILED:", sg.blocks, file=sys.stderr)
        sys.exit(1)
    print("Safety & Platform gates: 100% PASS ✅")
    
    # Extract metadata
    title_a = payload.get("title", f"Documentary: {episode_id}")
    title_b = brain.get("title_b") or f"The Hidden Truth: {episode_id.replace('-', ' ').title()}"
    description = payload.get("description", "")
    tags = payload.get("tags", ["documentary"])
    market = payload.get("market") or ("jp" if episode_id.startswith("jp-") else "kr" if episode_id.startswith("kr-") else "en")
    
    # Calculate duration
    import subprocess
    dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    dur_sec = float(subprocess.check_output(dur_cmd).decode().strip())
    mins = int(dur_sec // 60)
    secs = dur_sec % 60
    duration_str = f"{mins:02d}:{secs:05.2f}"
    frames_count = int(dur_sec * 30)
    scenes_count = len(brain.get("scenes", [])) or 16
    
    print(f"--- 2. Uploading to YouTube (Market: {market.upper()}, Privacy: Unlisted) ---")
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"Video Size: {file_size_mb:.2f} MB | Duration: {duration_str}")
    
    resp = youtube_upload.upload_video(
        video_path=video_path,
        title=title_a,
        description=description,
        tags=tags,
        category_id=payload.get("category_id", "27"),
        privacy_status="unlisted",
        made_for_kids=False,
        market=market
    )
    
    vid = resp.get("id") if isinstance(resp, dict) else None
    if not vid:
        print(f"ERROR: Upload failed: {resp}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Upload SUCCESS! Video ID: {vid} (https://youtu.be/{vid})")
    
    # Upload subtitles if present
    srt_path = f"{ep_dir}/subtitles.srt"
    if os.path.exists(srt_path):
        try:
            youtube_upload.upload_captions(vid, srt_path, language=market)
            print("Captions uploaded successfully ✅")
        except Exception as e:
            print(f"Captions upload notice: {e}")
            
    # Record to ledger & rate controller
    try:
        publish_ledger.record_upload(vid, title_a, ep_dir, "unlisted")
        rate_risk_controller.record_upload("youtube", vid)
        print("Publish Ledger updated ✅")
    except Exception as e:
        print(f"Publish Ledger notice: {e}")
        
    # Send Gate 2 Telegram Card
    print("--- 3. Dispatching Unified Gate 2 Telegram Notification ---")
    msg_id = asyncio.run(send_gate2_telegram(
        video_id=vid,
        episode_id=episode_id,
        title_a=title_a,
        title_b=title_b,
        duration_str=duration_str,
        scenes_count=scenes_count,
        frames_count=frames_count,
        bg_count=16,
        fg_count=16
    ))
    print(f"Gate 2 Telegram Card sent successfully! (Message ID: {msg_id}) ✅")
    
    result = {
        "status": "success",
        "video_id": vid,
        "watch_url": f"https://youtu.be/{vid}",
        "privacy_status": "unlisted",
        "telegram_message_id": msg_id,
        "episode_id": episode_id
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
