# -*- coding: utf-8 -*-
"""
Interactive Telegram Inline Buttons service for Human Gates & Pipeline ops.
Restored 2026-08-23 & Enhanced 24/08/2026:
  - Gate 1: apr:<task_id>, rej:<task_id>, ap_all, rj_all
  - Gate 2: pub:<task_id>, kp:<task_id>, puball, retry:<task_id>
  - Robust HTML escaping on all dynamic fields (prevents Telegram parsing displacement).
  - Explicit display of 🔥 Rising / Breakout Queries (+%) for each market card.

UPDATED 2026-09-02: Added answer_callback() and edit_message_text() helper functions
for HG1 button UX fix (immediate feedback before backend dispatch).
"""
import os
import re
import json
import logging
import html
import time
from typing import List, Tuple, Optional
from datetime import datetime, timezone
import httpx
import asyncio

from app.utils.security import mask_exception_text

logger = logging.getLogger(__name__)

DB_DIR = os.environ.get("VF_DB_DIR", "/root/video_factory/db")
GATE1_PENDING_FILE = os.path.join(DB_DIR, "gate1_pending.json")
GATE2_SENT_FILE = os.path.join(DB_DIR, "gate2_sent.json")

def _load_env_secrets():
    try:
        for envp in ["/root/secrets/.env", "/root/video_factory/.env", ".env"]:
            if os.path.exists(envp):
                with open(envp, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k in ("VF_TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN") and v:
                                if k not in os.environ or not os.environ[k]:
                                    os.environ[k] = v
                            elif k in ("VF_TG_CHAT_ID", "TELEGRAM_CHAT_ID", "TELEGRAM_ENABLED") and v:
                                if k not in os.environ or not os.environ[k]:
                                    os.environ[k] = v
    except (OSError, ValueError) as _env_err:
        logger.debug(f"[telegram_buttons] Notice loading env secrets: {_env_err}")

def _token() -> str:
    _load_env_secrets()
    return os.environ.get("VF_TG_BOT_TOKEN", "").strip() or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

def _chat_id() -> str:
    _load_env_secrets()
    return os.environ.get("VF_TG_CHAT_ID", "").strip() or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

def is_enabled() -> bool:
    if os.environ.get("TELEGRAM_ENABLED", "").strip() == "0":
        return False
    token = _token()
    chat_id = _chat_id()
    if not (token and chat_id):
        return False
    # Allow mock credentials in unit tests
    if token.startswith("mock_") or token.startswith("test_"):
        return True
    # Suppress real Telegram broadcast in test environments unless explicitly forced (Rule 123)
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("VF_TEST_MODE") == "1":
        if os.environ.get("FORCE_REAL_TELEGRAM_IN_TEST", "").strip() != "1":
            return False
    return True

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

async def send_with_buttons(text: str, buttons: Optional[list] = None, parse_mode: str = "HTML") -> Optional[int]:
    """Send Telegram message with custom inline keyboard rows."""
    if not is_enabled():
        logger.warning("[tg-btn] Telegram notifier is disabled or missing credentials.")
        return None
    url = f"https://api.telegram.org/bot{_token()}/sendMessage"
    clean_text = str(text).replace(chr(92) + 'n', chr(10))
    payload = {
        "chat_id": _chat_id(),
        "text": clean_text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if buttons:
        payload["reply_markup"] = build_inline_keyboard(buttons)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                msg_id = data.get("result", {}).get("message_id")
                logger.info(f"[tg-btn] Sent button message (id={msg_id}) to {_chat_id()}")
                return msg_id
            elif parse_mode == "HTML" and res.status_code != 200:
                logger.warning(f"[tg-btn] HTML parse failed ({res.status_code}): {mask_exception_text(res.text)}. Retrying as plain text...")
                payload.pop("parse_mode", None)
                res_plain = await client.post(url, json=payload)
                if res_plain.status_code == 200:
                    data = res_plain.json()
                    msg_id = data.get("result", {}).get("message_id")
                    logger.info(f"[tg-btn] Sent fallback plain text message (id={msg_id}) to {_chat_id()}")
                    return msg_id
                else:
                    logger.error(f"[tg-btn] Plain text fallback also failed: {res_plain.status_code} {mask_exception_text(res_plain.text)}")
                    return None
            else:
                logger.error(
                    f"[tg-btn] Failed to send button message: {res.status_code} "
                    f"{mask_exception_text(res.text)}"
                )
                return None
    except Exception as e:
        logger.error(f"[tg-btn] Exception sending button message: {mask_exception_text(str(e))}")
        return None

def send_telegram_broadcast(text: str, parse_mode: str = "HTML") -> Optional[int]:
    """Synchronous, thread-safe Telegram message dispatcher with auto-secrets loading.
    Can be called safely from any synchronous or asynchronous context.
    Returns message_id if successful, None otherwise.
    """
    _load_env_secrets()
    if not is_enabled():
        logger.warning("[tg-btn] Telegram notifier is disabled or missing credentials.")
        return None

    # Never broadcast test markets or mock test errors to live Telegram (Rule 123)
    if re.search(r"\bTEST_[A-Za-z0-9_]+\b", text):
        logger.info("[tg-btn] Suppressed Telegram broadcast for test market payload.")
        return None

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, send_with_buttons(text, buttons=None, parse_mode=parse_mode)).result()
    else:
        return asyncio.run(send_with_buttons(text, buttons=None, parse_mode=parse_mode))

async def answer_callback(callback_query_id: str, text: str = "", show_alert: bool = False) -> bool:
    """Answer a callback query to remove loading spinner.
    
    Added 2026-09-02 for HG1 button UX fix.
    Call this immediately when user clicks button to provide instant feedback.
    """
    if not is_enabled():
        return False
    url = f"https://api.telegram.org/bot{_token()}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            return res.status_code == 200
    except Exception as e:
        logger.warning(f"[tg-btn] answer_callback failed: {mask_exception_text(str(e))}")
        return False

async def edit_message_text(chat_id: str, message_id: int, text: str, 
                           rows: Optional[list] = None, parse_mode: str = "HTML") -> bool:
    """Edit an existing message's text and optionally its inline keyboard.
    
    Added 2026-09-02 for HG1 button UX fix.
    Use to update button states (Processing... → Approved ✅).
    """
    if not is_enabled():
        return False
    url = f"https://api.telegram.org/bot{_token()}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    if rows is not None:
        payload["reply_markup"] = build_inline_keyboard(rows)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                return True
            else:
                # Telegram returns 400 if text/keyboard unchanged - not an error
                if res.status_code == 400 and "message is not modified" in res.text.lower():
                    return True
                logger.warning(f"[tg-btn] edit_message_text: {res.status_code} {res.text[:200]}")
                return False
    except Exception as e:
        logger.warning(f"[tg-btn] edit_message_text failed: {mask_exception_text(str(e))}")
        return False

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
        safety_label = html.escape(str(pack.get('safety_label', 'Standard')))
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
            f"⚠️ <b>Safety Tier:</b> {safety_label}\n"
            f"• <b>5-Act Direction:</b> {arcs_short}\n"
            f"👉 <b>Task ID:</b> <code>{task_id}</code>\n"
        )

    en_task = str(en_pack.get('task_id', '') or '')
    jp_task = str(jp_pack.get('task_id', '') or '')
    kr_task = str(kr_pack.get('task_id', '') or '')

    _save_gate1_pending({'en': en_task, 'jp': jp_task, 'kr': kr_task})

    text = (
        "🎯 <b>[HUMAN GATE 1] THÔNG BÁO TIẾN ĐỘ CHỦ ĐỀ SẢN XUẤT (GO-LIVE 2026)</b>\n"
        "<i>(✨ Suy luận chiến lược & Đúc kết ngách bởi GPT-6-Astra qua HHTech API)</i>\n\n"
        + _fmt(en_pack, '🇺🇸', 'EN') + "\n"
        + _fmt(jp_pack, '🇯🇵', 'JP') + "\n"
        + _fmt(kr_pack, '🇰🇷', 'KR') + "\n"
        + "--------------------------------------------------\n"
        + "⚙️ <i>Hệ thống đang tự động chuyển tiếp sang <b>B2 Story Engine</b> (Kịch bản điều tra 12–15 phút) & <b>B3 Visual Plan</b>!</i>"
    )

    return await send_with_buttons(text, buttons=None)

async def send_gate3_card(episode_id: str, video_id: str, title_a: str, title_b: str, duration_str: Optional[str] = None, market: Optional[str] = None) -> Optional[int]:
    """Send Human Gate 3 Telegram card with 4 mandatory interactive buttons.
    Dynamically probes duration and resolves market voice/metadata (Rule 114/119).
    """
    _load_env_secrets()
    from pathlib import Path
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")

    # 1. Resolve market
    if not market:
        ep_lower = str(episode_id).lower()
        if ep_lower.startswith("jp_") or ep_lower.startswith("jp-"):
            market = "jp"
        elif ep_lower.startswith("kr_") or ep_lower.startswith("kr-"):
            market = "kr"
        else:
            market = "en"

    # 2. Dynamic duration probe
    if not duration_str or duration_str == "08:53.99":
        duration_str = "12:00.00"
        vid_candidates = [
            ep_dir / "final_169.mp4",
            ep_dir / "master_video_pro.mp4",
            ep_dir / "twolayer_silent.mp4",
        ]
        for vpath in vid_candidates:
            if vpath.exists():
                try:
                    import subprocess
                    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "default=noprint_wrappers=1:nokey=1", str(vpath)]
                    dur_sec = float(subprocess.check_output(cmd).decode().strip())
                    mins = int(dur_sec // 60)
                    secs = dur_sec % 60
                    duration_str = f"{mins:02d}:{secs:05.2f}"
                    break
                except Exception as _pe:
                    logger.debug("[tg-btn] probe duration error: %s", _pe)

    # 3. Dynamic voice / audio string
    voice_map = {
        "jp": "Edge-TTS ja-JP-KeitaNeural (Japanese Male Voice)",
        "kr": "Edge-TTS ko-KR-InJoonNeural (Korean Male Voice)",
        "en": "Edge-TTS en-US-GuyNeural (English Male Voice)",
    }
    voice_str = voice_map.get(market.lower(), "Edge-TTS Studio Voice")

    # 4. Check captions
    captions_ok = False
    for srt_name in (f"subtitles_{market}.srt", "subtitles.srt"):
        if (ep_dir / srt_name).exists():
            captions_ok = True
            break
    captions_str = f"✅ Đã nạp track chuẩn {market.upper()}" if captions_ok else "⏳ Phụ đề tự động"

    watch_url = f"https://youtu.be/{video_id}" if video_id else "https://youtube.com"
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit" if video_id else "https://studio.youtube.com"
    safe_ep = html.escape(str(episode_id))
    safe_t_a = html.escape(str(title_a))
    safe_t_b = html.escape(str(title_b))
    safe_dur = html.escape(str(duration_str))

    text = (
        "👑 <b>[HUMAN GATE 3] NGHIỆM THU EPISODE MASTER PRO & PHÁT HÀNH</b>\n\n"
        f"🎬 <b>Episode ID:</b> <code>{safe_ep}</code>\n"
        f"⏱️ <b>Thời lượng:</b> {safe_dur} (Full HD 1080p / 30fps)\n"
        "🎨 <b>Visual:</b> Layer 1 (16:9) + Layer 2 (1:1 Chroma Key Cutout)\n"
        f"🎙️ <b>Audio:</b> {voice_str} (target -14 LUFS) + BGM (-24dB)\n"
        f"📝 <b>Captions (CC):</b> {captions_str}\n"
        "🏷️ <b>Nhãn AI:</b> Altered or Synthetic Content: <b>BẬT (Yes)</b>\n"
        "🛡️ <b>Trạng thái hiện tại:</b> <b>Không công khai (Unlisted)</b>\n\n"
        "📌 <b>GÓI PACKAGING YOUTUBE 2026 (Rule 113/119):</b>\n"
        f"• <b>Title A (Primary):</b> <i>{safe_t_a}</i>\n"
        f"• <b>Title B (Backup A/B):</b> <i>{safe_t_b}</i>\n\n"
        f'🔗 <b>Link xem trước (Unlisted):</b> <a href="{watch_url}">{watch_url}</a>\n'
        f'🛠️ <b>YouTube Studio Edit:</b> <a href="{studio_url}">{studio_url}</a>\n\n'
        "🎨 <b>QUY TRÌNH THIẾT KẾ THUMBNAIL (GEMINI AI TRÊN YOUTUBE STUDIO):</b>\n"
        "1. Bấm nút <b>'🎨 Mở Studio (Tạo Thumbnail Gemini)'</b> bên dưới.\n"
        "2. Sử dụng tính năng <i>Thiết kế ảnh thu nhỏ (Gemini AI)</i> native của YouTube Studio để chọn concept & tạo thumbnail chuẩn xác nhất.\n"
        "3. Lưu ảnh thu nhỏ trên YouTube Studio rồi bấm <b>'🚀 Chuyển sang Công Khai (Public)'</b>.\n\n"
        "👉 <i>Bấm nút bên dưới để chuyển trạng thái phát hành:</i>"
    )
    rows = [
        [("🎨 Mở Studio (Tạo Thumbnail Gemini)", None, studio_url)],
        [("📺 Xem trước Video (Unlisted)", None, watch_url)],
        [("🚀 Chuyển sang Công Khai (Public)", f"pub:{video_id}")],
        [("🌐 Công Khai Tất cả Video (Public All)", "puball")],
        [("🔒 Giữ Không Công Khai (Unlisted)", f"kp:{video_id}")]
    ]
    return await send_with_buttons(text, rows)



async def send_gate2_card(task_id: str, n_scenes: int, n_bg: int, n_fg: int,
                          story_score: str = "n/a", n_thumb: int = 0,
                          topic: str = "", director_archetype: str = "",
                          era_anchor: str = "", title_a: str = "", title_b: str = "") -> Optional[int]:
    """Send Human Gate 2: B3.5 finished, prompts are in Notion, images are next.
    Lean Executive Briefing format + Antigravity 1-click execution block:
    Delegates deep technical rules (2K DCI, #FF00FF Chroma, 4-Axis Visual Audit)
    to Antigravity Skill `vf-image-gen`.
    """
    safe_task = html.escape(str(task_id))
    safe_score = html.escape(str(story_score))
    safe_topic = html.escape(str(topic)) if topic else safe_task
    safe_arch = html.escape(str(director_archetype)) if director_archetype else "Hollywood Master Principle"

    paste_block = f"/vf-image-gen\n/run:image --episode {task_id} --headless"

    text = (
        "🎨 <b>[HUMAN GATE 2] ĐẠO DIỄN B3/B3.5 HOÀN TẤT — SẴN SÀNG SINH ẢNH</b>\n\n"
        f"🎬 <b>Episode:</b> <code>{safe_task}</code>\n"
        f"📌 <b>Chủ đề:</b> {safe_topic}\n"
        f"🎥 <b>Phong cách Đạo diễn:</b> {safe_arch}\n"
        f"🎞️ <b>Tài nguyên thị giác:</b> {n_scenes} Scenes · {n_bg} BG (16:9) · {n_fg} FG (1:1 Magenta Cutout)\n"
        f"📊 <b>Story Gate:</b> {safe_score} | <b>Notion Prompt Sync:</b> ✅\n"
        "🖼️ <b>Thumbnail:</b> <i>Ủy quyền thiết kế trực tiếp qua Gemini AI trên YouTube Studio tại Human Gate 3 (sau B10 upload).</i>\n\n"
        "📋 <b>Khối lệnh 1-Chạm thực thi trên Antigravity (Copy & Dán):</b>\n"
        f"<pre>{html.escape(paste_block)}</pre>\n"
        "⚡ <i>Quy chuẩn kỹ thuật ảnh 2K DCI, tách nền Chroma HSV, 4-Trục Visual Audit (Rule 122) và Auto-Trigger B6 được ủy quyền trọn vẹn cho Skill <b>vf-image-gen</b>.</i>"
    )
    return await send_with_buttons(text, buttons=None)


def trigger_human_gate_2(episode_id: str) -> Optional[int]:
    """
    Synchronous trigger for Human Gate 2 (Rule 125 & Executive 1-Click Mandate).
    Gathers episode metadata, scenes, visual prompts, thumbnails, and dispatches
    the standard Human Gate 2 Telegram card to the user.
    Safe for synchronous callers and threadpools.
    """
    import asyncio
    from pathlib import Path

    # 1. Resolve canonical episode directory
    candidates = [
        Path(f"/root/video_factory/episodes/{episode_id}"),
        Path(f"/var/vf/episodes/{episode_id}"),
        Path(f"/root/video_factory/workspace/{episode_id}"),
        Path(f"episodes/{episode_id}"),
        Path(f"workspace/{episode_id}")
    ]
    ep_dir = None
    for c in candidates:
        try:
            if c.exists():
                ep_dir = c
                break
        except (PermissionError, OSError):
            continue

    if not ep_dir:
        logger.warning(f"[HG2] Episode directory not found for {episode_id}")
        return None

    # 2. Extract scene count & metadata
    n_scenes = 0
    dp_file = ep_dir / "director_plan.json"
    if not dp_file.exists():
        dp_file = ep_dir / "dp_plan.json"
    dp_data = {}
    if dp_file.exists():
        try:
            dp_data = json.loads(dp_file.read_text(encoding="utf-8"))
            n_scenes = len(dp_data.get("scenes", []))
        except (OSError, json.JSONDecodeError) as _dp_err:
            logger.debug(f"[telegram_buttons] Notice reading dp_file: {_dp_err}")

    # 3. Extract prompts counts
    pforge_file = ep_dir / "prompts_forge.json"
    if not pforge_file.exists():
        pforge_file = ep_dir / "prompts.json"
    n_bg, n_fg, n_thumb = 0, 0, 0
    if pforge_file.exists():
        try:
            p_data = json.loads(pforge_file.read_text(encoding="utf-8"))
            n_bg = len(p_data.get("backgrounds", {}))
            n_fg = len(p_data.get("foregrounds", {}))
            n_thumb = len(p_data.get("thumbnails", {}))
        except (OSError, json.JSONDecodeError) as _pf_err:
            logger.debug(f"[telegram_buttons] Notice reading pforge_file: {_pf_err}")

    # 4. Extract Titles from seo_package
    title_a, title_b = "", ""
    seo_file = ep_dir / "seo_package.json"
    if seo_file.exists():
        try:
            s_data = json.loads(seo_file.read_text(encoding="utf-8"))
            title_a = s_data.get("title_a", "")
            title_b = s_data.get("title_b", "")
        except (OSError, json.JSONDecodeError) as _seo_err:
            logger.debug(f"[telegram_buttons] Notice reading seo_file: {_seo_err}")

    # 5. Extract topic, archetype, story_score
    topic = dp_data.get("topic") or episode_id
    director_arch = dp_data.get("director_archetype") or "Hollywood Master Principle"

    b2_score = None
    brain_file = ep_dir / "brain_input.json"
    if brain_file.exists():
        try:
            b_data = json.loads(brain_file.read_text(encoding="utf-8"))
            b2_val = b_data.get("story_gate_score")
            if b2_val:
                b2_score = str(b2_val)
        except (OSError, json.JSONDecodeError) as _b2_err:
            logger.debug(f"[telegram_buttons] Notice reading brain_file: {_b2_err}")

    # 5. Extract B3.5.1 score and verify convergence (Rule 121 & Rule 125)
    b35_score = None
    audit_file = ep_dir / "visual_convergence_audit.json"
    if not audit_file.exists():
        logger.warning(f"[HG2 Guard] Episode {episode_id} is missing visual_convergence_audit.json. B3.5.1 has not completed. Blocking HG2 card.")
        return None

    try:
        a_data = json.loads(audit_file.read_text(encoding="utf-8"))
        converged = a_data.get("converged", False)
        f_score = a_data.get("final_score")
        if f_score is not None:
            b35_score = f"{float(f_score):.1f}/10"
        if not converged or (f_score is not None and float(f_score) < 8.0):
            logger.warning(f"[HG2 Guard] Episode {episode_id} B3.5.1 has NOT converged (Score: {b35_score}, Converged: {converged}). Blocking Human Gate 2 completion notification.")
            return None
    except Exception as e:
        logger.warning(f"[HG2 Guard] Failed to evaluate visual convergence audit: {e}")
        return None

    if b35_score and b2_score:
        story_score = f"B2: {b2_score} · B3.5.1: {b35_score}"
    elif b35_score:
        story_score = f"B3.5.1 Audit: {b35_score}"
    elif b2_score:
        story_score = f"B2 Gate: {b2_score}"
    else:
        story_score = "Audit: PASS"

    logger.info(f"[HG2] Dispatching Human Gate 2 card for {episode_id} ({n_scenes} scenes, {n_bg} BGs, {n_fg} FGs)...")

    # Async loop execution safety
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            msg_id = pool.submit(
                asyncio.run,
                send_gate2_card(
                    task_id=episode_id,
                    n_scenes=n_scenes,
                    n_bg=n_bg,
                    n_fg=n_fg,
                    story_score=story_score,
                    n_thumb=n_thumb,
                    topic=topic,
                    director_archetype=director_arch,
                    title_a=title_a,
                    title_b=title_b
                )
            ).result()
    else:
        msg_id = asyncio.run(
            send_gate2_card(
                task_id=episode_id,
                n_scenes=n_scenes,
                n_bg=n_bg,
                n_fg=n_fg,
                story_score=story_score,
                n_thumb=n_thumb,
                topic=topic,
                director_archetype=director_arch,
                title_a=title_a,
                title_b=title_b
            )
        )

    if msg_id:
        logger.info(f"[HG2] Successfully dispatched Human Gate 2 Telegram card (msg_id={msg_id}) for {episode_id}")
    return msg_id



