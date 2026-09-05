#!/usr/bin/env python3
"""CLI: Gui thong bao nghiem thu Human Gate 2 duy nhat (chong spam / chong duplicate noti).
Chuan YouTube 2026: Mac dinh o che do "Khong cong khai (Unlisted)" de User xem truoc ngay lap tuc.
Nguoi dung bam nut de chuyen tu "Khong cong khai (Unlisted)" sang "Cong khai (Public)".

Usage:
  python3 scripts/send_publish_button.py <video_id> [episode_id] [title_a] [title_b]
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import telegram_buttons as tb

async def send_gate2_unified(video_id: str, episode_id: str = "en-enron-ep006",
                             title_a: str = "Enron: The $63B Lie That Fooled Wall Street",
                             title_b: str = "The Day $80 Shares Crashed to Zero: Enron Scandal",
                             duration_str: str = "08:53.99"):
    watch_url = f"https://youtu.be/{video_id}"
    
    text = (
        "👑 <b>[HUMAN GATE 2] NGHIỆM THU EPISODE MASTER PRO & PHÁT HÀNH</b>\n\n"
        f"🎬 <b>Episode ID:</b> <code>{episode_id}</code>\n"
        f"⏱️ <b>Thời lượng:</b> {duration_str} (76 scenes / 16.019 frames / Full HD 1080p)\n"
        "🎨 <b>Visual:</b> 15 BGs 16:9 High-Key + 12 FGs (2 tư thế/nhân vật)\n"
        "🎙️ <b>Audio:</b> ElevenLabs Studio Voice + 48.000 Hz Studio BGM (-22dB)\n"
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
        print("DISABLED: Telegram notifier is not configured or disabled.", file=sys.stderr)
        return None
        
    msg_id = await tb.send_with_buttons(text, rows)
    return msg_id


async def main():
    if len(sys.argv) < 2:
        print("Usage: send_publish_button.py <video_id> [episode_id] [title_a] [title_b]", file=sys.stderr)
        sys.exit(1)
        
    video_id = sys.argv[1]
    episode_id = sys.argv[2] if len(sys.argv) > 2 else "en-enron-ep006"
    title_a = sys.argv[3] if len(sys.argv) > 3 else "Enron: The $63B Lie That Fooled Wall Street"
    title_b = sys.argv[4] if len(sys.argv) > 4 else "The Day $80 Shares Crashed to Zero: Enron Scandal"
    
    msg_id = await send_gate2_unified(video_id, episode_id, title_a, title_b)
    if msg_id:
        print(f"OK Human Gate 2 (Unlisted -> Public) Notification Sent: message_id={msg_id} video_id={video_id}")
    else:
        print("FAILED to send Telegram notification", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
