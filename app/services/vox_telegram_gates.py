#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/vox_telegram_gates.py
Hệ thống Thông báo Telegram cho 5 Cổng Kiểm Soát Người Dùng (5-Human-Gates Protocol)
cho Vox Continuous Tactile Pipeline.

Mỗi cổng bắt buộc gửi:
1. Trạng thái & số liệu định lượng (Scenes, Beats, Objects, Audio Duration).
2. Lệnh đích danh và prompt template chuẩn cho đúng Episode đang chạy
   để User dán trực tiếp vào Antigravity trigger luồng kế tiếp.
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger("vf.vox_telegram_gates")

try:
    from app.services.telegram_notify import send_message as _tg_send
except ImportError:
    async def _tg_send(text: str) -> bool:
        logger.warning(f"[tg_stub] Would send: {text[:100]}...")
        return False


def build_hg1_message(episode_id: str, topic_title: str, pillar: str, runtime_s: float) -> str:
    return f"""🔎 <b>[HUMAN GATE 1] CÀO DATA & KỊCH BẢN HOÀN TẤT</b>

📺 <b>Episode:</b> <code>{episode_id}</code>
📑 <b>Đề tài:</b> {topic_title}
🏛️ <b>Pillar:</b> {pillar}
⏱️ <b>Thời lượng dự kiến:</b> {runtime_s:.1f}s

📋 <b>Lệnh Antigravity để duyệt và chuyển sang Bước 3 (Director):</b>
<pre>
/vox:b3 --episode {episode_id}
</pre>

⚡ <i>Hành động:</i> Bấm vào Antigravity chat, dán lệnh trên để kích hoạt đạo diễn phân rã Beats thị giác 5-8s theo Rule 140!"""


def build_hg2_message(episode_id: str, total_beats: int, total_blocks: int, 
                      runtime_s: float, objects_count: int) -> str:
    avg_dur = runtime_s / max(total_beats, 1)
    return f"""🎨 <b>[HUMAN GATE 2] ĐẠO DIỄN HOÀN TẤT — DUYỆT DIRECTOR PLAN TRƯỚC KHI TẠO ẢNH</b>

📺 <b>Episode:</b> <code>{episode_id}</code>
🎬 <b>Định dạng:</b> Vox Continuous Tactile Paper-Collage (Rule 140)
⏱️ <b>Thời lượng:</b> {runtime_s:.1f}s (~{int(runtime_s//60)}m {int(runtime_s%60)}s)
📦 <b>Quy mô:</b> {total_blocks} Sequence Blocks · <b>{total_beats} Beats</b> (~{avg_dur:.1f}s/beat)
🛠️ <b>Vật thể xúc giác:</b> {objects_count} đạo cụ (hồ sơ, triện đỏ Hanko, thước cặp, kéo...)
⚡ <b>Động học:</b> Khế ước 4 thì (S1: Entry ➔ S2: Stamp/Impact ➔ S3: Growth ➔ S4: Hold)

📋 <b>Lệnh Antigravity để duyệt và tạo ảnh:</b>
<pre>
/vox:image --episode {episode_id}
</pre>

⚡ <i>Hành động:</i> Dán lệnh trên vào Antigravity để kích hoạt Playwright sinh FULL {total_beats} ảnh seed B4!"""


def build_hg3_message(episode_id: str, image_count: int, gallery_path: str) -> str:
    return f"""🖼️ <b>[HUMAN GATE 3 - MỚI] GALLERY ẢNH SEED ĐÃ XONG — DUYỆT ẢNH TRƯỚC KHI TẠO VIDEO</b>

📺 <b>Episode:</b> <code>{episode_id}</code>
📊 <b>Tổng số ảnh seed:</b> {image_count} ảnh (100% 2560x1440, sạch chữ, viền xơ trắng)
🔍 <b>Gallery Review:</b> <code>{gallery_path}</code>

📋 <b>Lệnh Antigravity để tạo DEMO VIDEO Act I (8-10 clip):</b>
<pre>
/vox:video --episode {episode_id} --mode demo
</pre>

⚡ <i>Hành động:</i> Mở Gallery kiểm tra ảnh. Nếu ưng ý, dán lệnh trên để Google Flow 7 acc tạo clip demo Act I!"""


def build_hg4_message(episode_id: str, video_count: int, runtime_s: float) -> str:
    return f"""🎬 <b>[HUMAN GATE 4 - MỚI] FULL VIDEO CLIPS HOÀN TẤT — DUYỆT RAW VIDEO TRƯỚC KHI RENDER</b>

📺 <b>Episode:</b> <code>{episode_id}</code>
🎥 <b>Tổng số clip:</b> {video_count} clips Google Flow Veo Fast (1080p, động học 4 thì)
⏱️ <b>Thời lượng video:</b> {runtime_s:.1f}s

📋 <b>Lệnh Antigravity để duyệt và tự động đi full luồng còn lại:</b>
<pre>
/vox:render --episode {episode_id}
</pre>

⚡ <i>Hành động:</i> Dán lệnh trên vào Antigravity để kích hoạt VPS Remotion Master Render (TTS + Subtitles + BGM) ➔ QC B8 ➔ Upload YouTube B10!"""


def build_hg5_message(episode_id: str, youtube_url: str, chapters_count: int) -> str:
    return f"""🚀 <b>[HUMAN GATE 5] VIDEO ĐÃ UPLOAD UNLISTED LÊN YOUTUBE — DUYỆT BẢN FINAL</b>

📺 <b>Episode:</b> <code>{episode_id}</code>
🔗 <b>YouTube Unlisted:</b> {youtube_url}
📑 <b>Timeline Chapters:</b> {chapters_count} mốc thời gian chính xác từ Remotion (Rule 135)
🏷️ <b>Metadata:</b> SEO Title, Description, Tags, Thumbnail B10

⚡ <i>Hành động:</i> Xem video unlisted trên YouTube. Nếu đạt chuẩn, chuyển trạng thái sang Public để xuất bản!"""


async def send_gate_notification(gate_number: int, episode_id: str, **kwargs) -> bool:
    """Bắn thông báo Telegram cho cổng kiểm duyệt tương ứng."""
    text = ""
    if gate_number == 1:
        text = build_hg1_message(
            episode_id, 
            kwargs.get("topic_title", "Phóng sự điều tra Vox"), 
            kwargs.get("pillar", "Macro Economy"), 
            kwargs.get("runtime_s", 540.0)
        )
    elif gate_number == 2:
        text = build_hg2_message(
            episode_id, 
            kwargs.get("total_beats", 72), 
            kwargs.get("total_blocks", 12), 
            kwargs.get("runtime_s", 551.93), 
            kwargs.get("objects_count", 150)
        )
    elif gate_number == 3:
        text = build_hg3_message(
            episode_id, 
            kwargs.get("image_count", 72), 
            kwargs.get("gallery_path", f"episodes/{episode_id}/review_gallery.html")
        )
    elif gate_number == 4:
        text = build_hg4_message(
            episode_id, 
            kwargs.get("video_count", 72), 
            kwargs.get("runtime_s", 551.93)
        )
    elif gate_number == 5:
        text = build_hg5_message(
            episode_id, 
            kwargs.get("youtube_url", "https://youtube.com/watch?v=N/A"), 
            kwargs.get("chapters_count", 5)
        )
    else:
        logger.error(f"Unknown gate number: {gate_number}")
        return False
        
    return await _tg_send(text)


def send_gate_sync(gate_number: int, episode_id: str, **kwargs) -> bool:
    """Wrapper đồng bộ để gọi từ CLI hoặc script."""
    try:
        return asyncio.run(send_gate_notification(gate_number, episode_id, **kwargs))
    except Exception as e:
        logger.error(f"Error in send_gate_sync: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gửi thông báo Telegram cho Human Gates")
    parser.add_argument("--gate", type=int, required=True, choices=[1, 2, 3, 4, 5], help="Cổng kiểm soát 1-5")
    parser.add_argument("--episode", type=str, required=True, help="Episode ID")
    parser.add_argument("--beats", type=int, default=72)
    parser.add_argument("--blocks", type=int, default=12)
    parser.add_argument("--runtime", type=float, default=551.93)
    parser.add_argument("--objects", type=int, default=150)
    parser.add_argument("--gallery", type=str, default="")
    parser.add_argument("--youtube", type=str, default="")
    args = parser.parse_args()

    ok = send_gate_sync(
        args.gate, 
        args.episode, 
        total_beats=args.beats, 
        total_blocks=args.blocks, 
        runtime_s=args.runtime, 
        objects_count=args.objects,
        gallery_path=args.gallery,
        youtube_url=args.youtube
    )
    print(f"Telegram Notification Gate {args.gate}: {'SUCCESS' if ok else 'FAILED'}")
