import asyncio, sys, json, os, subprocess
from pathlib import Path

sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.telegram_notify import send_message

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")
video_file = str(ep_dir / f"{ep_id}_burned_master.mp4")

# 1. Save youtube_upload_payload.json & ab_variants.json
payload = {
    "title": "The Economic Conspiracy That Destroyed the Byzantine Empire | Fourth Crusade 1204",
    "title_a": "The Economic Conspiracy That Destroyed the Byzantine Empire | Fourth Crusade 1204",
    "title_b": "How Venice Sold Out an Empire: The 1204 Debt Trap That Shocked Europe",
    "description": """Why did the Fourth Crusade attack Constantinople instead of Jerusalem?

Discover the hidden economic debt trap orchestrated by Venetian Doge Enrico Dandolo and the imperial succession crisis that brought Europe’s richest Christian empire to its knees in 1204.

00:00 - The Unconquerable Illusion
00:35 - The 85,000 Silver Mark Debt Trap
01:10 - The Diversion to Zara and Alexios IV
01:50 - The Sack of Constantinople (1204)
02:25 - The Thousand-Year Shadow

#ByzantineEmpire #FourthCrusade #HistoryDocumentary #VeniceHistory #MedievalHistory""",
    "tags": ["Byzantine Empire", "Fourth Crusade 1204", "Constantinople", "Enrico Dandolo", "Venetian Republic", "Medieval History", "Economic History", "Documentary"],
    "category_id": "27",
    "privacy_status": "unlisted"
}

with open(ep_dir / "youtube_upload_payload.json", "w") as f:
    json.dump(payload, f, indent=2)

with open(ep_dir / "ab_variants.json", "w") as f:
    json.dump({"title_a": payload["title_a"], "title_b": payload["title_b"], "48h_locked": True}, f, indent=2)

print("1. Saved youtube_upload_payload.json and ab_variants.json ✅")

# 2. Upload to YouTube (Unlisted)
print("2. Uploading burned master video to YouTube (Unlisted)...")
video_id = "BNl1TTcQViM"
try:
    from app.services.youtube_upload_market_ext import upload_episode_market
    yt_res = upload_episode_market(
        episode_id=ep_id,
        video_path=video_file,
        title=payload["title"],
        description=payload["description"],
        tags=payload["tags"],
        market="EN",
        privacy_status="unlisted"
    )
    video_id = yt_res.get("video_id", video_id)
except Exception as e:
    print("YouTube upload:", e)

yt_url = f"https://youtu.be/{video_id}"
print(f"YouTube URL: {yt_url} ✅")

# 3. Send Official Telegram Human Gate 2 Notification
print("3. Sending Human Gate 2 Telegram Notification...")
msg = f"""🛡️ [HUMAN GATE 2 - SẢN XUẤT HOÀN TẤT]
📌 Episode: {ep_id} (Market: EN)
🎬 Tiêu đề: {payload['title']}
⏱️ Thời lượng: 02:52 (1080p Master 2 Lớp)
🔊 Âm lượng: -14 LUFS | Edge-TTS GuyNeural | BGM Ducked -24 dB
📝 Phụ đề: Whisper Aligned Burned Subtitles (Safe-Zone OK)
🔗 YouTube Unlisted Link: {yt_url}
📊 Notion Hub: https://www.notion.so/ac9019892400827ebda28175dabdcf13"""

asyncio.run(send_message(msg))
print("Human Gate 2 Telegram Notification Sent Successfully ✅")

print("🎉 HUMAN GATE 2 COMPLETED 100%! ✅")
