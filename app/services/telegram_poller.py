"""Background Telegram poller (getUpdates long-poll) for inline-button callbacks.

No public webhook needed (vf-api is private behind the MCP tunnel). On start it
deletes any existing webhook so getUpdates is usable, then long-polls for
callback_query updates and routes them through telegram_actions.dispatch.

Enable: env TELEGRAM_POLLER_ENABLED=1 OR sentinel file db/telegram_poller.on
(default OFF). Offset persisted to db/telegram_offset.json so restarts don't
reprocess. Every error is logged and the loop continues (FAIL-SAFE).

NOTE: run with a SINGLE uvicorn worker; multiple concurrent getUpdates pollers
for the same bot cause 409 Conflict.

FIXED 2026-09-02: Added immediate button state feedback (Processing...) before dispatch
to eliminate user confusion about click registration.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

import httpx
from loguru import logger

from app.services import telegram_buttons as tb
from app.services import upload_mode
from app.services.telegram_actions import dispatch, parse_callback_data

_API = "https://api.telegram.org"
_OFFSET_FILE = Path(os.getenv("TELEGRAM_OFFSET_FILE",
                              "/root/video_factory/db/telegram_offset.json"))
_SENTINEL = Path(os.getenv("TELEGRAM_POLLER_FLAG",
                           "/root/video_factory/db/telegram_poller.on"))
_VIDEO_ID_RE = re.compile(r"videoId:\s*(\S+)")
_task = None


def is_poller_enabled() -> bool:
    if not tb.is_enabled():
        return False
    if os.getenv("TELEGRAM_POLLER_ENABLED", "0").strip() == "1":
        return True
    try:
        return _SENTINEL.exists()
    except Exception:  # noqa: BLE001
        return False


def _load_offset() -> int:
    try:
        return int(json.loads(_OFFSET_FILE.read_text()).get("offset", 0))
    except Exception:  # noqa: BLE001
        return 0


def _save_offset(offset: int):
    try:
        _OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
        _OFFSET_FILE.write_text(json.dumps({"offset": offset}))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg-poll] save offset: {e}")


async def _delete_webhook():
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            await c.post(f"{_API}/bot{tb._token()}/deleteWebhook",
                         json={"drop_pending_updates": False})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg-poll] deleteWebhook: {e}")


async def _handle_callback(cq: dict):
    """Handle callback query with immediate UI feedback before backend processing.

    UX Flow (FIXED 2026-09-02):
    1. Immediately answer callback (removes Telegram loading spinner)
    2. Update button to "⏳ Processing..." state
    3. Execute backend dispatch (Notion DB writes, etc.)
    4. Update button to final state (Approved ✅ / Denied ❌)
    """
    cq_id = cq.get("id")
    data = cq.get("data", "")
    msg = cq.get("message", {}) or {}
    chat_id = (msg.get("chat", {}) or {}).get("id")
    message_id = msg.get("message_id")
    act, arg = parse_callback_data(data)

    # STEP 1: Immediate acknowledgment - removes Telegram loading spinner
    await tb.answer_callback(cq_id, "", show_alert=False)

    # STEP 2: Show "Processing..." state on clicked button BEFORE backend dispatch
    base = (msg.get("text") or "").split("\n— ")[0]
    raw_kb = msg.get("reply_markup", {}).get("inline_keyboard", [])
    processing_rows = []

    if act in ("ap_all", "rj_all"):
        # "Approve All" / "Deny All" clicked - show processing for all buttons
        processing_rows = [[("⏳ Đang xử lý tất cả...", "processing")]]
    elif act in ("apr", "rej", "ap", "rj"):
        # Individual button clicked - show processing on that row only
        for row in raw_kb:
            clicked_in_row = any(b.get("callback_data") == data for b in row)
            if clicked_in_row:
                # Find market prefix (EN/JP/KR)
                prefix = ""
                for b in row:
                    t = b.get("text", "")
                    if "EN:" in t: prefix = "🇺🇸 EN: "
                    elif "JP:" in t: prefix = "🇯🇵 JP: "
                    elif "KR:" in t: prefix = "🇰🇷 KR: "
                processing_rows.append([(prefix + "⏳ Đang xử lý...", "processing")])
            else:
                # Keep other rows unchanged
                row_items = []
                for b in row:
                    row_items.append((b.get("text", ""), b.get("callback_data", "")))
                processing_rows.append(row_items)

    # Update UI to show processing state
    try:
        await tb.edit_message_text(chat_id, message_id, base, rows=processing_rows)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg-poll] edit processing state: {e}")

    # STEP 3: Execute backend dispatch (Notion DB writes, etc.)
    try:
        reply, alert = await asyncio.to_thread(dispatch, act, arg)
    except Exception as e:  # noqa: BLE001
        reply, alert = ("⚠️ Lỗi xử lý: " + str(e)), True
        # Show error in final state
        try:
            await tb.edit_message_text(chat_id, message_id, base + "\n— " + reply, rows=[])
        except Exception:  # noqa: BLE001
            pass
        return

    # STEP 4: Update to final state based on action result
    if act == "tg":
        new_rows = [[(upload_mode.label(), "tg")]]
    elif act == "up":
        m = _VIDEO_ID_RE.search(reply or "")
        if m:
            vid = m.group(1)
            new_rows = [[("🚀 Công khai ngay", "pub:" + vid), ("🔒 Giữ private", "kp:" + vid)]]
        else:
            new_rows = []
    elif act in ("ap", "rj", "ap_all", "rj_all", "apr", "rej"):
        new_rows = []
        if act in ("ap_all", "rj_all"):
            text = "✨ Đã Approve Tất Cả 3 Kênh" if act == "ap_all" else "❌ Đã Deny Tất Cả 3 Kênh"
            new_rows = [[(text, "done")]]
        else:
            for row in raw_kb:
                clicked_in_row = any(b.get("callback_data") == data for b in row)
                if clicked_in_row:
                    prefix = ""
                    for b in row:
                        t = b.get("text", "")
                        if "EN:" in t: prefix = "🇺🇸 EN: "
                        elif "JP:" in t: prefix = "🇯🇵 JP: "
                        elif "KR:" in t: prefix = "🇰🇷 KR: "
                    if act in ("apr", "ap"):
                        new_rows.append([(prefix + "Approved ✨", "done")])
                    else:
                        new_rows.append([(prefix + "Denied ❌", "done")])
                else:
                    row_items = []
                    for b in row:
                        row_items.append((b.get("text", ""), b.get("callback_data", "")))
                    new_rows.append(row_items)
    else:
        new_rows = []

    # Final UI update with result
    try:
        await tb.edit_message_text(chat_id, message_id, base + "\n— " + reply, rows=new_rows)
    except Exception:  # noqa: BLE001
        pass


async def _loop():
    await _delete_webhook()
    offset = _load_offset()
    logger.info(f"[tg-poll] started; offset={offset}")
    while True:
        try:
            async with httpx.AsyncClient(timeout=40) as c:
                r = await c.post(f"{_API}/bot{tb._token()}/getUpdates", json={
                    "offset": offset + 1, "timeout": 25,
                    "allowed_updates": ["callback_query"]})
            if r.status_code != 200:
                logger.warning(f"[tg-poll] getUpdates {r.status_code}: {r.text[:150]}")
                await asyncio.sleep(5)
                continue
            for upd in r.json().get("result", []) or []:
                offset = max(offset, int(upd.get("update_id", offset)))
                cq = upd.get("callback_query")
                if cq:
                    await _handle_callback(cq)
            _save_offset(offset)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[tg-poll] loop error: {e}")
            await asyncio.sleep(5)


def start_poller():
    global _task
    if not is_poller_enabled():
        logger.info("[tg-poll] disabled (env TELEGRAM_POLLER_ENABLED=1 or sentinel file)")
        return
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_loop())
    logger.info("[tg-poll] poller task scheduled")
