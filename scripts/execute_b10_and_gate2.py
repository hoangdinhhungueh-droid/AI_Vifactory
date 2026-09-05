import os, sys, json, time, subprocess
from pathlib import Path

sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.youtube_upload import upload_from_payload
from app.services.telegram_notifier import send_with_buttons, send_message

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")

title_a = "The Economic Conspiracy That Destroyed the Byzantine Empire | 1204 Fourth Crusade"
title_b = "How a Venetian Debt Trap Ended the World's Richest Empire in 1204"

description = """The Fall of Constantinople in 1204 was not an inevitable military tragedy — it was the culmination of a predatory debt contract engineered by Venice. Discover how the Fourth Crusade was diverted into history's most catastrophic financial default.

TIMESTAMPS:
00:00 The Impenetrable Fortress & The Great Betrayal
02:40 The Venetian Monopoly: Weaponizing Naval Infrastructure
05:30 The Zara Diversion & The Broken Contract
08:45 The Siege & The Great Plunder of 1204
11:30 The Aftermath: How Venice Carved an Empire

#ByzantineEmpire #FourthCrusade #Venice #EconomicHistory #Constantinople #HistoryDocumentary #MiddleAges"""

tags = [
    "Byzantine Empire", "Fourth Crusade", "Constantinople", "Venice",
    "Enrico Dandolo", "Alexios IV", "Economic History", "Debt Trap",
    "History Documentary", "Medieval History", "Siege of Constantinople"
]

# 1. Create youtube_upload_payload.json
payload = {
    "episode_id": ep_id,
    "title": title_a,
    "description": description,
    "tags": tags,
    "category_id": "27",  # Education
    "privacy_status": "unlisted",
    "video_file": "master_video_pro.mp4",
    "market": "en"
}

payload_path = ep_dir / "youtube_upload_payload.json"
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
print("Saved youtube_upload_payload.json ✅")

# 2. Create ab_variants.json
ab_variants = {
    "episode_id": ep_id,
    "rule_113_48h_law": {
        "locked_until": time.time() + (48 * 3600),
        "status": "Active Title A / Thumbnail A"
    },
    "title_a": title_a,
    "title_b": title_b,
    "thumbnail_a": f"/var/vf/episodes/{ep_id}/images/byz-a1-walls-dawn.png",
    "thumbnail_b": f"/var/vf/episodes/{ep_id}/images/byz-a5-ruins-charred-map.png"
}

ab_path = ep_dir / "ab_variants.json"
with open(ab_path, "w", encoding="utf-8") as f:
    json.dump(ab_variants, f, indent=2)
print("Saved ab_variants.json ✅")

# 3. Upload to YouTube
print("=== 3. UPLOADING TO YOUTUBE (UNLISTED) ===")
upload_res = upload_from_payload(str(ep_dir), payload_file="youtube_upload_payload.json", privacy_status="unlisted", market="en")
print("Upload Result:", upload_res)

video_id = upload_res.get("id") or upload_res.get("video_id")
if not video_id and isinstance(upload_res, dict):
    # Check if id in response
    video_id = upload_res.get("id")

if not video_id:
    raise RuntimeError(f"Failed to extract video_id from upload response: {upload_res}")

print(f"🎉 YOUTUBE UPLOAD SUCCESS: Video ID = {video_id} (https://www.youtube.com/watch?v={video_id})")

# 4. Update publish_ledger.json
ledger_path = Path("/var/vf/data/publish_ledger.json")
ledger_data = {}
if ledger_path.exists():
    try:
        with open(ledger_path) as f:
            ledger_data = json.load(f)
    except Exception:
        ledger_data = {}

ledger_data[ep_id] = {
    "episode_id": ep_id,
    "video_id": video_id,
    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
    "title": title_a,
    "privacy_status": "unlisted",
    "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "duration_seconds": 847.39,
    "market": "en"
}

with open(ledger_path, "w", encoding="utf-8") as f:
    json.dump(ledger_data, f, indent=2)
print(f"Updated publish_ledger.json for {ep_id} ✅")

# 5. Dispatch Telegram Human Gate 2 Card with 4 interactive buttons
print("=== 5. DISPATCHING HUMAN GATE 2 TELEGRAM CARD ===")
gate2_text = f"""🎬 <b>HUMAN GATE 2: MASTER VIDEO PRO & PHÁT HÀNH</b>

📌 <b>Tập</b>: <code>{ep_id}</code> (Byzantine Empire)
🏷 <b>Tiêu đề (Title A)</b>: {title_a}
⏱ <b>Thời lượng</b>: 14:07 (847.4s) | <b>Độ phân giải</b>: 1080p 30fps
🔊 <b>Âm lượng kiểm định (B9)</b>: -14.0 LUFS (Chuẩn Web/YouTube/TikTok — cập nhật 23/08/2026)
🎨 <b>Bố cục 2 lớp</b>: 10 Backgrounds 16:9 + 7 Foregrounds Cutouts (50 Scenes)
📝 <b>Phụ đề</b>: Burned Yellow-White Frosted Subtitles
🔒 <b>Trạng thái</b>: Unlisted (Khóa bao bì 48h - Rule 113)

Vui lòng nghiệm thu sản phẩm và lựa chọn hành động bên dưới:"""

buttons = [
    [{"text": "📺 Xem trước Video (Unlisted)", "url": f"https://www.youtube.com/watch?v={video_id}"}],
    [{"text": "🚀 Chuyển sang Công Khai (Public)", "callback_data": f"pub:{video_id}"}],
    [{"text": "🌐 Công Khai Tất cả Video (Public All)", "callback_data": "puball"}],
    [{"text": "🔒 Giữ Không Công Khai (Unlisted)", "callback_data": f"kp:{video_id}"}]
]

send_with_buttons(gate2_text, buttons)
print("Human Gate 2 Telegram Card dispatched successfully with all 4 interactive buttons! 🚀")
