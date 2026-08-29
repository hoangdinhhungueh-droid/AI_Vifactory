# -*- coding: utf-8 -*-
"""
Interactive Telegram Inline Buttons service for Human Gates & Pipeline ops.
Restored 2026-08-23 & Enhanced 24/08/2026:
  - Gate 1: apr:<task_id>, rej:<task_id>, ap_all, rj_all
  - Gate 2: pub:<task_id>, kp:<task_id>, puball, retry:<task_id>
  - Robust HTML escaping on all dynamic fields (prevents Telegram parsing displacement).
  - Explicit display of 🔥 Rising / Breakout Queries (+%) for each market card.
"""
import os
import json
import logging
import html
import time
from typing import List, Tuple, Optional
from datetime import datetime, timezone
import httpx

from app.utils.security import mask_exception_text

logger = logging.getLogger(__name__)

DB_DIR = os.environ.get("VF_DB_DIR", "/root/video_factory/db")
GATE1_PENDING_FILE = os.path.join(DB_DIR, "gate1_pending.json")
GATE2_SENT_FILE = os.path.join(DB_DIR, "gate2_sent.json")

def _load_env_secrets():
    try:
        envp = os.path.join("/root", "secrets", ".env")
        if os.path.exists(envp):
            with open(envp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if k == "VF_TG_BOT_TOKEN" and v:
                            os.environ["VF_TG_BOT_TOKEN"] = v
                        elif k == "TELEGRAM_BOT_TOKEN" and v:
                            if not os.environ.get("VF_TG_BOT_TOKEN"):
                                os.environ["TELEGRAM_BOT_TOKEN"] = v
                        elif k in ("TELEGRAM_CHAT_ID", "TELEGRAM_ENABLED") and v:
                            if k not in os.environ or not os.environ[k]:
                                os.environ[k] = v
    except Exception:
        pass

def _token() -> str:
    _load_env_secrets()
    return os.environ.get("VF_TG_BOT_TOKEN", "").strip() or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

def _chat_id() -> str:
    _load_env_secrets()
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()

def is_enabled() -> bool:
    if os.environ.get("TELEGRAM_ENABLED", "").strip() == "0":
        return False
    return bool(_token() and _chat_id())

def _save_gate1_pending(pending_map: dict):
    """Save Gate 1 task IDs mapping (e.g. {'en': task_id, 'jp': task_id, 'kr': task_id})"""
    try:
        os.makedirs(DB_DIR, exist_ok=True)
        with open(GATE1_PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tasks": pending_map
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[tg-btn] failed to save gate1_pending.json: {e}")

def load_gate1_pending() -> dict:
    try:
        if os.path.exists(GATE1_PENDING_FILE):
            with open(GATE1_PENDING_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("tasks", {})
    except Exception as e:
        logger.warning(f"[tg-btn] failed to load gate1_pending.json: {e}")
    return {}

def _load_gate2_ledger() -> dict:
    try:
        if os.path.exists(GATE2_SENT_FILE):
            with open(GATE2_SENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return {}
    return {}

def _save_gate2_ledger(ledger: dict):
    os.makedirs(DB_DIR, exist_ok=True)
    try:
        with open(GATE2_SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[tg-btn] failed to save gate2 ledger: {e}")

def build_inline_keyboard(rows):
    """
    rows: List of rows, where each row is a list of tuples:
      - (text, callback_data)
      - OR (text, None, url)
    """
    inline_keyboard = []
    for row in rows:
        btn_row = []
        for btn in row:
            if len(btn) == 3 and btn[2]:
                btn_row.append({"text": btn[0], "url": btn[2]})
            else:
                btn_row.append({"text": btn[0], "callback_data": btn[1]})
        inline_keyboard.append(btn_row)
    return {"inline_keyboard": inline_keyboard}

async def send_with_buttons(text: str, buttons: list, parse_mode: str = "HTML") -> Optional[int]:
    """Send Telegram message with custom inline keyboard rows."""
    if not is_enabled():
        logger.warning("[tg-btn] Telegram notifier is disabled or missing credentials.")
        return None
    url = f"https://api.telegram.org/bot{_token()}/sendMessage"
    payload = {
        "chat_id": _chat_id(),
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": build_inline_keyboard(buttons),
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                msg_id = data.get("result", {}).get("message_id")
                logger.info(f"[tg-btn] Sent button message (id={msg_id}) to {_chat_id()}")
                return msg_id
            else:
                logger.error(
                    f"[tg-btn] Failed to send button message: {res.status_code} "
                    f"{mask_exception_text(res.text)}"
                )
                return None
    except Exception as e:
        logger.error(f"[tg-btn] Exception sending button message: {mask_exception_text(str(e))}")
        return None

async def send_gate1_card(en_pack: dict, jp_pack: dict, kr_pack: dict) -> Optional[int]:
    """Send Human Gate 1 Telegram card with 4 interactive button rows.
    Called from trend_gate_ai.py trend_virality endpoint after B1.3 virality scoring.
    """
    def _fmt(pack: dict, flag: str, market: str) -> str:
        subj = html.escape(str(pack.get('top_subject', market)))
        v = pack.get('virality', 0)
        name_vi = html.escape(str(pack.get('topic_name_vi', subj)))
        keyword = html.escape(str(pack.get('search_specific_keyword', subj)))
        niche = html.escape(str(pack.get('niche_angle_brief', '')))
        arcs = html.escape(str(pack.get('story_direction_5_arcs', '')))
        task_id = html.escape(str(pack.get('task_id', f'{market.upper()}_EP0001_{market.lower()}')))

        bqs = pack.get('breakout_queries') or pack.get('rising_queries') or []
        bqs_clean = []
        for q in bqs:
            if not q or isinstance(q, bool):
                continue
            val_str = ""
            if isinstance(q, dict):
                q_name = q.get('query') or q.get('term') or q.get('keyword') or q.get('name') or q.get('article') or ''
                v = q.get('value')
                if v and str(v).strip() not in ('+0%', '0', ''):
                    val_str = str(v).strip()
            else:
                q_name = str(q).strip()
            q_esc = html.escape(q_name)
            if q_esc:
                item_display = f"{q_esc} ({html.escape(val_str)})" if val_str else q_esc
                if item_display not in bqs_clean:
                    bqs_clean.append(item_display)
        bqs_display = ", ".join(bqs_clean[:5]) if bqs_clean else "Đang cập nhật"

        arcs_short = arcs[:180] + '...' if len(arcs) > 180 else arcs
        return (
            f"{flag} <b>Market {market}:</b> <code>{subj}</code> (Virality: {v})\n"
            f"• <b>Đề tài:</b> {name_vi}\n"
            f"• <b>Search-Specific Key:</b> <code>{keyword}</code>\n"
            f"• <b>🔥 Cụm từ tìm kiếm tăng (+%):</b> <code>{bqs_display}</code>\n"
            f"• <b>Niche Brief:</b> {niche}\n"
            f"• <b>5-Act Direction:</b> {arcs_short}\n"
            f"👉 <b>Task ID:</b> <code>{task_id}</code>\n"
        )

    en_task = en_pack.get('task_id', 'EN_EP0001_topic')
    jp_task = jp_pack.get('task_id', 'JP_EP0001_topic')
    kr_task = kr_pack.get('task_id', 'KR_EP0001_topic')

    _save_gate1_pending({'en': en_task, 'jp': jp_task, 'kr': kr_task})

    text = (
        "🎯 <b>[HUMAN GATE 1] PHÊ DUYỆT CHỦ ĐỀ SẢN XUẤT (GO-LIVE 2026)</b>\n"
        "<i>(✨ Suy luận chiến lược & Đúc kết ngách bởi GPT-5.6-Sol qua HHTech API)</i>\n\n"
        + _fmt(en_pack, '🇺🇸', 'EN') + "\n"
        + _fmt(jp_pack, '🇯🇵', 'JP') + "\n"
        + _fmt(kr_pack, '🇰🇷', 'KR') + "\n"
        + "--------------------------------------------------\n"
        + "💡 <i>Bấm <b>[Approve]</b> để duyệt kênh cần sản xuất. Copy <b>Task ID</b> dán vào Antigravity chat để bắt đầu B2-B10!</i>"
    )

    buttons = [
        [(f'🇺🇸 EN: Approve ✅', f'apr:{en_task}'), (f'🇺🇸 EN: Deny ❌', f'rej:{en_task}')],
        [(f'🇯🇵 JP: Approve ✅', f'apr:{jp_task}'), (f'🇯🇵 JP: Deny ❌', f'rej:{jp_task}')],
        [(f'🇰🇷 KR: Approve ✅', f'apr:{kr_task}'), (f'🇰🇷 KR: Deny ❌', f'rej:{kr_task}')],
        [(f'🚀 Approve Tất Cả 3 Kênh', 'ap_all'), ('❌ Deny Tất Cả', 'rj_all')]
    ]

    return await send_with_buttons(text, buttons)

async def send_gate3_card(episode_id: str, video_id: str, title_a: str, title_b: str, duration_str: str = "08:53.99") -> Optional[int]:
    """Send Human Gate 3 Telegram card with 4 mandatory interactive buttons."""
    watch_url = f"https://youtu.be/{video_id}" if video_id else "https://youtube.com"
    safe_ep = html.escape(str(episode_id))
    safe_t_a = html.escape(str(title_a))
    safe_t_b = html.escape(str(title_b))
    safe_dur = html.escape(str(duration_str))

    text = (
        "👑 <b>[HUMAN GATE 3] NGHIỆM THU EPISODE MASTER PRO & PHÁT HÀNH</b>\n\n"
        f"🎬 <b>Episode ID:</b> <code>{safe_ep}</code>\n"
        f"⏱️ <b>Thời lượng:</b> {safe_dur} (Full HD 1080p / 30fps)\n"
        "🎨 <b>Visual:</b> Layer 1 (16:9) + Layer 2 (1:1 Chroma Key Cutout)\n"
        "🎙️ <b>Audio:</b> Edge-TTS en-US-GuyNeural (target -14 LUFS) + BGM (-24dB)\n"
        "🏷️ <b>Nhãn AI:</b> Altered or Synthetic Content: <b>BẬT (Yes)</b>\n"
        "🛡️ <b>Trạng thái hiện tại:</b> <b>Không công khai (Unlisted)</b>\n\n"
        "📌 <b>GÓI PACKAGING YOUTUBE 2026 (Rule 113/119):</b>\n"
        f"• <b>Title A (Primary):</b> <i>{safe_t_a}</i>\n"
        f"• <b>Title B (Backup A/B):</b> <i>{safe_t_b}</i>\n\n"
        f'🔗 <b>Link xem trước (Unlisted):</b> <a href="{watch_url}">{watch_url}</a>\n\n'
        "👉 <i>Bấm nút bên dưới để chuyển trạng thái phát hành:</i>"
    )
    rows = [
        [("📺 Xem trước Video (Unlisted)", None, watch_url)],
        [("🚀 Chuyển sang Công Khai (Public)", f"pub:{video_id}")],
        [("🌐 Công Khai Tất cả Video (Public All)", "puball")],
        [("🔒 Giữ Không Công Khai (Unlisted)", f"kp:{video_id}")]
    ]
    return await send_with_buttons(text, rows)


async def send_gate2_card(task_id: str, n_scenes: int, n_bg: int, n_fg: int,
                          story_score: str = "n/a") -> Optional[int]:
    """Send Human Gate 2: B3.5 finished, prompts are in Notion, images are next.

    Images are generated by Antigravity (owner has AI Pro, no token cost), so
    this card carries a self-contained block the owner pastes into Antigravity
    chat -- the command plus the context Antigravity needs to resolve it.
    """
    safe_task = html.escape(str(task_id))
    paste_block = (
        f"/run:image task:{task_id}\n\n"
        f"CONTEXT & CONSTRAINTS (Rule 435-437):\n"
        f"Episode: {task_id} | Notion Prompt Library subpage | filter Episode={task_id}\n\n"
        f"QUALITY RULES (Rule 435 — 2K Resolution):\n"
        f"ALL images MUST be 2560x1440 (16:9 aspect, 2K DCI).\n"
        f"Append to every prompt: [TECHNICAL: Generate at 2560x1440 resolution (16:9 aspect ratio, 2K DCI). Do not upscale or downscale.]\n\n"
        f"TIMING RULES (Rule 436 — 45s Spacing):\n"
        f"- Minimum 45 seconds between image generation requests\n"
        f"- Per-request timeout: 120 seconds\n"
        f"- Do NOT submit >1 request concurrently\n\n"
        f"LAYER SPECIFICATIONS:\n"
        f"- Background (16:9): cinematic, no people in close-up, documentary lighting\n"
        f"- Foreground (1:1 chroma-key): solid #FF00FF magenta background, full body, clean cutout\n\n"
        f"STORAGE & UPDATE:\n"
        f"1. Save images: /var/vf/episodes/{task_id}/assets/\n"
        f"2. Update Notion Image Asset Library: Episode ID, Reuse Key (match Prompt Library), Layer Type, Status=Approved\n\n"
        f"QUOTA HANDLING (Rule 437):\n"
        f"If 429 'quota exhausted': STOP immediately, VPS poller will auto-resume after reset (~4h50m)"
    )
    text = (
        "🎨 <b>[HUMAN GATE 2] PROMPTS SẴN SÀNG — CẦN SINH ẢNH</b>\n\n"
        f"🎬 <b>Episode:</b> <code>{safe_task}</code>\n"
        f"🎞️ <b>Scenes:</b> {n_scenes} · <b>BG prompts:</b> {n_bg} · <b>FG prompts:</b> {n_fg}\n"
        f"📊 <b>Story gate:</b> {html.escape(str(story_score))}\n"
        "📚 <b>Director Plan + Prompt Library:</b> đã sync Notion ✅\n\n"
        "📋 <b>Dán nguyên khối dưới đây vào Antigravity chat:</b>\n"
        f"<pre>{html.escape(paste_block)}</pre>\n"
        "👉 <i>Pipeline tự kiểm tra mỗi ~10 phút — khi mọi ảnh BG/FG "
        "đã Approved/Pulled by VPS trên Notion, tự chạy tiếp B5 → B10 "
        "và gửi card HG3. Nút dưới đây chỉ để ghi nhận, không kích hoạt render.</i>"
    )
    return await send_with_buttons(text, [[("✅ Đã sinh ảnh xong", f"imgdone:{task_id}")]])
