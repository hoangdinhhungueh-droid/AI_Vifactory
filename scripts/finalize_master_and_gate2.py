#!/usr/bin/env python3
"""
Step B8 Muxing -> Step B9 Quality Probe -> Step B10 YouTube Unlisted + Telegram Human Gate 2
"""

import os, sys, json, time, asyncio, subprocess
from pathlib import Path

sys.path.insert(0, "/root/video_factory")
sys.path.insert(0, "/root/video_factory/scripts")

from app.services.youtube_upload import upload_from_payload, _load_env
_load_env()
from app.services.telegram_buttons import send_gate3_card

# --episode arg (default: en-byzantine-empire-ep001 for backward compat)
import argparse as _ap
_parser = _ap.ArgumentParser()
_parser.add_argument("--episode", default="en-byzantine-empire-ep001")
ep_id = _parser.parse_known_args()[0].episode
ep_dir = Path(f"/var/vf/episodes/{ep_id}")
silent_mp4 = ep_dir / "twolayer_silent.mp4"
voice_wav = ep_dir / "audio" / "voice_norm.wav"
bgm_mp3 = Path("/root/video_factory/assets/bgm/calm_004_fs725597.mp3")
master_mp4 = ep_dir / "master_video_pro.mp4"
final_mp4 = ep_dir / "final_169.mp4"

def mux_audio():
    print("=== 1. MUXING NARRATION & STUDIO BGM (-24 dB) ONTO REMOTION MASTER ===")
    mux_cmd = [
        "ffmpeg", "-y",
        "-i", str(silent_mp4),
        "-i", str(voice_wav),
        "-stream_loop", "-1", "-i", str(bgm_mp3),
        "-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.06[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-shortest",
        str(master_mp4)
    ]
    subprocess.run(mux_cmd, check=True)
    if final_mp4.is_symlink() or final_mp4.exists():
        final_mp4.unlink(missing_ok=True)
    os.symlink(str(master_mp4), str(final_mp4))
    print(f"Muxed {master_mp4} ({master_mp4.stat().st_size / (1024*1024):.2f} MB) ✅")

def quality_probe():
    print("=== 2. RUNNING B9 QUALITY PROBE (EBU R128) ===")
    loud_cmd = [
        "ffmpeg", "-i", str(master_mp4),
        "-af", "ebur128=framelog=verbose",
        "-f", "null", "-"
    ]
    res = subprocess.run(loud_cmd, capture_output=True, text=True)
    for line in res.stderr.split("\n"):
        if "I:" in line or "Threshold:" in line or "LRA:" in line or "Peak:" in line:
            print("  " + line.strip())

def upload_and_gate2():
    print("=== 3. CLEANING OLD LEDGER ENTRY & UPLOADING TO YOUTUBE (UNLISTED) ===")
    lp = Path("/root/video_factory/db/publish_ledger.json")
    if lp.exists():
        try:
            with open(lp) as f:
                entries = json.load(f)
            entries = [e for e in entries if "byzantine" not in e.get("title", "").lower() and "byzantine" not in e.get("episode_dir", "").lower()]
            with open(lp, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except Exception as e:
            print("Error cleaning ledger:", e)

    title_a = "The Economic Conspiracy That Destroyed the Byzantine Empire | 1204 Fourth Crusade"
    title_b = "How a Venetian Debt Trap Ended the World's Richest Empire in 1204"

    upload_res = upload_from_payload(str(ep_dir), payload_file="youtube_upload_payload.json", privacy_status="unlisted", market="en")
    video_id = upload_res.get("id") or upload_res.get("video_id")
    if not video_id:
        raise RuntimeError(f"Failed to extract video_id from upload response: {upload_res}")

    print(f"🎉 YOUTUBE UPLOAD SUCCESS: Video ID = {video_id} (https://www.youtube.com/watch?v={video_id})")

    # Update publish_ledger.json
    entries = []
    if lp.exists():
        try:
            with open(lp) as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.append({
        "video_id": video_id,
        "title": title_a,
        "episode_dir": str(ep_dir),
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "status": "unlisted",
        "published_at": None
    })
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    print("=== 4. DISPATCHING HUMAN GATE 2 TELEGRAM CARD (4 BUTTONS) ===")
    async def dispatch():
        msg_id = await send_gate3_card(
            video_id=video_id,
            episode_id=ep_id,
            title_a=title_a,
            title_b=title_b,
            duration_str="14:07",
            scenes_count=50,
            frames_count=25422,
            bg_count=10,
            fg_count=7
        )
        print(f"🎉 HUMAN GATE 2 TELEGRAM CARD DISPATCHED! Message ID: {msg_id}")

    asyncio.run(dispatch())

def main():
    mux_audio()
    quality_probe()
    upload_and_gate2()

if __name__ == "__main__":
    main()
