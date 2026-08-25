import os, sys, json, time, asyncio, shutil
from pathlib import Path

sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.youtube_upload import upload_from_payload
from app.services.telegram_buttons import send_gate2_card

# --episode arg (default: en-byzantine-empire-ep001 for backward compat)
import argparse as _ap
_parser = _ap.ArgumentParser()
_parser.add_argument("--episode", default="en-byzantine-empire-ep001")
ep_id = _parser.parse_known_args()[0].episode
ep_dir = Path(f"/var/vf/episodes/{ep_id}")

# 1. Symlink or copy final_169.mp4 from master_video_pro.mp4
master_mp4 = ep_dir / "master_video_pro.mp4"
final_mp4 = ep_dir / "final_169.mp4"
if not final_mp4.exists():
    os.symlink(str(master_mp4), str(final_mp4))
print("Linked final_169.mp4 -> master_video_pro.mp4 ✅")

title_a = "The Economic Conspiracy That Destroyed the Byzantine Empire | 1204 Fourth Crusade"
title_b = "How a Venetian Debt Trap Ended the World's Richest Empire in 1204"

description = """The Fall of Constantinople in 1204 was not an inevitable military tragedy — it was the culmination of a predatory debt contract engineered by Venice. Discover how the Fourth Crusade was diverted into history's most catastrophic financial default.

TIMESTAMPS:
00:00 The Impenetrable Fortress & The Great Betrayal
02:40 The Venetian Monopoly: Weaponizing Naval Infrastructure
05:30 The Zara Diversion & The Broken Contract
08:45 The Siege & The Great Plunder of 1204
11:30 The Aftermath: How Venice Carved an Empire

AI Disclosure: This documentary contains synthetic voice narration and AI-assisted visual reconstruction.

#ByzantineEmpire #FourthCrusade #Venice #EconomicHistory #Constantinople #HistoryDocumentary"""

tags = [
    "Byzantine Empire", "Fourth Crusade", "Constantinople",
    "Venice", "Economic History", "Debt Trap", "Documentary"
]

# 2. Create youtube_upload_payload.json with strict compliance
payload = {
    "episode_id": ep_id,
    "title": title_a,
    "description": description,
    "tags": tags,
    "category_id": "27",  # Education
    "privacy_status": "unlisted",
    "video_file": "final_169.mp4",
    "market": "en",
    "ai_disclosure": True,
    "made_for_kids": False,
    "selfDeclaredMadeForKids": False,
    "contains_synthetic_media": True
}

payload_path = ep_dir / "youtube_upload_payload.json"
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
print("Saved compliant youtube_upload_payload.json ✅")

# 3. Create ab_variants.json
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

# 4. Upload to YouTube
print("=== 4. UPLOADING TO YOUTUBE (UNLISTED) ===")
upload_res = upload_from_payload(str(ep_dir), payload_file="youtube_upload_payload.json", privacy_status="unlisted", market="en")
print("Upload Result:", upload_res)

video_id = upload_res.get("id") or upload_res.get("video_id")
if not video_id:
    raise RuntimeError(f"Failed to extract video_id from upload response: {upload_res}")

print(f"🎉 YOUTUBE UPLOAD SUCCESS: Video ID = {video_id} (https://www.youtube.com/watch?v={video_id})")

# 5. Update publish_ledger.json
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

# 6. Dispatch Telegram Human Gate 2 Card with 4 interactive buttons
print("=== 6. DISPATCHING HUMAN GATE 2 TELEGRAM CARD ===")
async def dispatch_gate2():
    msg_id = await send_gate2_card(
        video_id=video_id,
        episode_id=ep_id,
        title_a=title_a,
        title_b=title_b,
        duration_str="14:07",
        scenes_count=50,
        frames_count=25421,
        bg_count=10,
        fg_count=7
    )
    print(f"Human Gate 2 Telegram Card dispatched successfully! (Message ID: {msg_id}) 🚀")

asyncio.run(dispatch_gate2())
