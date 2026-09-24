"""
Telegram notifications for the VF production pipeline.

Env (loaded from /root/secrets/.env):
  TELEGRAM_BOT_TOKEN  - bot token from @BotFather
  TELEGRAM_CHAT_ID    - target chat id (user or group)
  TELEGRAM_ENABLED    - optional "0" to hard-disable (default: on when token+chat set)
  TG_ATTACH_DRAFTS    - optional "1" to attach small draft files directly (default on)

Free view links: large outputs (>~50MB Telegram limit) are uploaded to the R2
public bucket via the existing image_gen._r2_upload helper and shared as a URL.

All functions are FAIL-SAFE: any error is logged and swallowed so the production
pipeline never crashes because of a notification problem.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx
from loguru import logger

from app.services import telegram_buttons as tb

_API = "https://api.telegram.org"
_TG_FILE_LIMIT = 50 * 1024 * 1024  # Telegram bot upload limit ~50MB


def _chat_id() -> str:
    tb._load_env_secrets()
    return os.environ.get("VF_TG_CHAT_ID", "").strip() or os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def _token() -> str:
    tb._load_env_secrets()
    return os.environ.get("VF_TG_BOT_TOKEN", "").strip() or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()



def is_enabled() -> bool:
    if os.environ.get("TELEGRAM_ENABLED", "").strip() == "0":
        return False
    return bool(_token() and _chat_id())


async def send_message(text: str, *, disable_preview: bool = False, silent: bool = False) -> bool:
    if not is_enabled():
        logger.debug("[tg] disabled or not configured; skip message")
        return False
    url = f"{_API}/bot{_token()}/sendMessage"
    payload = {
        "chat_id": _chat_id(),
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_preview,
        "disable_notification": silent,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
        if r.status_code != 200:
            if "can't parse entities" in r.text or "parse" in r.text:
                payload.pop("parse_mode", None)
                async with httpx.AsyncClient(timeout=30) as client:
                    r2 = await client.post(url, json=payload)
                if r2.status_code == 200:
                    return True
            logger.warning(f"[tg] sendMessage {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg] sendMessage error: {e}")
        return False


async def _send_file(method: str, field: str, local_path: str, caption: str = "") -> bool:
    if not is_enabled():
        return False
    if not local_path or not os.path.exists(local_path):
        logger.warning(f"[tg] {method}: file missing {local_path}")
        return False
    try:
        size = os.path.getsize(local_path)
    except OSError:
        size = 0
    if size > _TG_FILE_LIMIT:
        logger.info(f"[tg] {method}: file too big ({size}B); caller should send a link instead")
        return False
    url = f"{_API}/bot{_token()}/{method}"
    data = {"chat_id": _chat_id(), "caption": caption[:1024], "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            with open(local_path, "rb") as fh:
                files = {field: (os.path.basename(local_path), fh)}
                r = await client.post(url, data=data, files=files)
        if r.status_code != 200:
            logger.warning(f"[tg] {method} {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg] {method} error: {e}")
        return False


async def send_document(local_path: str, caption: str = "") -> bool:
    return await _send_file("sendDocument", "document", local_path, caption)


async def send_video(local_path: str, caption: str = "") -> bool:
    return await _send_file("sendVideo", "video", local_path, caption)


async def upload_draft_link(local_path: str, key: Optional[str] = None) -> Optional[str]:
    """Upload a draft/raw asset to the R2 public bucket and return a free view URL.
    Returns None if R2 is not configured or the upload fails."""
    if not local_path or not os.path.exists(local_path):
        return None
    try:
        from app.services.image_gen import _r2_upload  # reuse existing helper
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg] r2 helper import failed: {e}")
        return None
    if key is None:
        key = "drafts/" + os.path.basename(local_path)
    try:
        return await asyncio.to_thread(_r2_upload, local_path, key)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tg] r2 upload error: {e}")
        return None


async def send_media_or_link(local_path: str, caption: str = "", key: Optional[str] = None) -> bool:
    """Try to attach the file directly; if too large or attach disabled, upload to
    R2 and send a free view link instead."""
    if not local_path or not os.path.exists(local_path):
        return False
    attach = os.environ.get("TG_ATTACH_DRAFTS", "1").strip() != "0"
    try:
        size = os.path.getsize(local_path)
    except OSError:
        size = 0
    ext = os.path.splitext(local_path)[1].lower()
    if attach and size <= _TG_FILE_LIMIT:
        if ext in (".mp4", ".mov", ".webm"):
            if await send_video(local_path, caption):
                return True
        else:
            if await send_document(local_path, caption):
                return True
    # fallback: link
    url = await upload_draft_link(local_path, key=key)
    if url:
        return await send_message(f"{caption}\n\U0001F517 <a href=\"{url}\">View / download (free)</a>")
    logger.info(f"[tg] could not attach or link {local_path}")
    return False


# ---- High-level production hooks -------------------------------------------

async def notify_production(stage: str, episode_id: str, detail: str = "") -> bool:
    """Stage progress -> log only.

    The pipeline has exactly 3 human gates (HG1 topic approval, HG2 prompts
    ready, HG3 release card). Per-stage pings drowned those out, so they are
    logged instead of sent. Set VF_STAGE_NOTIFY_TELEGRAM=1 to get them back
    while debugging.
    """
    logger.info(f"[stage] {stage} - {episode_id}" + (f" | {detail}" if detail else ""))
    if os.getenv("VF_STAGE_NOTIFY_TELEGRAM", "0") != "1":
        return True
    msg = f"\U0001F3AC <b>VF Production</b>\n<b>{stage}</b> \u2014 <code>{episode_id}</code>"
    if detail:
        msg += f"\n{detail}"
    return await send_message(msg)


async def notify_cost_summary(month_used_vnd: float, episode_id: str = "",
                              breakdown: Optional[dict] = None) -> bool:
    """Disabled: cost telemetry removed per user mandate to eliminate Telegram clutter."""
    return True


async def notify_budget_alert(provider: str, day_used: float, day_cap: float = 0.0,
                              month_used: float = 0.0, month_cap: float = 0.0) -> bool:
    """Backwards-compatible cost reporting hook without budget cap alarms (Standardized 18/09/2026)."""
    msg = (
        "💰 <b>[VF COST REPORT]</b>\n"
        f"provider: <code>{provider}</code>\n"
        f"day: ${day_used:.4f}\n"
        f"month: ${month_used:.4f}"
    )
    return await send_message(msg)


async def notify_error(stage: str, episode_id: str, error: str) -> bool:
    msg = (
        "\U0001F534 <b>VF ERROR</b>\n"
        f"<b>{stage}</b> \u2014 <code>{episode_id}</code>\n"
        f"<pre>{error[:1500]}</pre>"
    )
    return await send_message(msg)



async def notify_episode_done(episode_id: str, final_path: str = None,
                              credit_usd: Optional[float] = None,
                              breakdown: Optional[dict] = None) -> bool:
    """Human Gate 3 Automated Pipeline Completion Hook (Rule 114 / Protocol V4).
    Automatically triggers execute_b10_auto_seo_upload_gate2 to upload Unlisted
    to YouTube and dispatch the 4-button Human Gate 3 Telegram card.
    """
    try:
        import sys
        import json
        import subprocess
        from pathlib import Path
        ep_dir = Path(f"/var/vf/episodes/{episode_id}")
        market = "en"
        brain_path = ep_dir / "brain_input.json"
        if brain_path.exists():
            try:
                bdata = json.loads(brain_path.read_text(encoding="utf-8"))
                market = bdata.get("market") or bdata.get("lang_code") or market
            except Exception:
                pass
        if market == "en":
            ep_lower = str(episode_id).lower()
            if ep_lower.startswith("jp_") or ep_lower.startswith("jp-"):
                market = "jp"
            elif ep_lower.startswith("kr_") or ep_lower.startswith("kr-"):
                market = "kr"
            elif ep_lower.startswith("vn_") or ep_lower.startswith("vn-"):
                market = "vn"

        # Rule 125 Anti-Double-Dispatch: If continue_after_images.py orchestrator is active, skip internal subprocess
        b4b10_state = ep_dir / "b4b10_state.json"
        if b4b10_state.exists():
            logger.info(f"[Gate 3] Episode {episode_id} orchestrated by continue_after_images (b4b10_state.json detected). Skipping redundant internal B10 trigger.")
            return True

        logger.info(f"[Gate 3] Auto-triggering B10 for {episode_id} (market: {market})...")
        cmd = [
            sys.executable,
            "/root/video_factory/scripts/execute_b10_auto_seo_upload_gate2.py",
            "--episode", episode_id,
            "--market", market,
            "--privacy", "unlisted"
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=600
        )
        if proc.returncode == 0:
            logger.info(f"[Gate 3] B10 & Human Gate 3 succeeded for {episode_id}")
            return True
        else:
            logger.error(f"[Gate 3] B10 failed ({proc.returncode}): {proc.stdout[-500:]}\n{proc.stderr[-500:]}")
            return False
    except Exception as e:
        logger.error(f"[Gate 3] notify_episode_done error: {e}")
        return False



if __name__ == "__main__":
    # Manual smoke test: python3 -m app.services.telegram_notify
    async def _t():
        ok = await send_message("\u2705 VF Telegram notifier online (smoke test)")
        print("enabled=", is_enabled(), "sent=", ok)
    asyncio.run(_t())
