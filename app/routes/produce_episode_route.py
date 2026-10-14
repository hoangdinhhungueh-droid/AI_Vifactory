"""POST /api/v1/produce-episode — Notion-brain-driven one-button episode production.

Wraps scripts/produce_episode.py as an HTTP endpoint (Moc 1 item 1.11):
  1. Resolve the Episodes Notion DB by name via /v1/search.
  2. Query it for the row whose `episode_id` property == request.episode_id.
  3. Read the first ```json brain_input code block from that page body.
  4. Write /var/vf/episodes/<episode_id>/brain_input.json (S5 + motion_cards read this).
  5. Call run_pipeline(...) with the brain fields (brain_mode = bool(story_text)),
     unless seed_only=true.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.pipeline.run_episode import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

NOTION_API = "https://api.notion.com/v1"


class ProduceEpisodeRequest(BaseModel):
    episode_id: str
    seed_only: bool = False


def _headers():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN missing")
    return {
        "Authorization": "Bearer " + token,
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _resolve_episodes_db():
    r = requests.post(
        NOTION_API + "/search",
        headers=_headers(),
        json={"query": "Episodes", "filter": {"property": "object", "value": "database"}},
        timeout=60,
    )
    r.raise_for_status()
    for res in r.json().get("results", []):
        title = "".join(t.get("plain_text", "") for t in res.get("title", []))
        if title.strip().lower() == "episodes":
            return res["id"]
    raise RuntimeError("Episodes database not found via search")


def _find_episode_page(db_id, episode_id):
    r = requests.post(
        NOTION_API + "/databases/" + db_id + "/query",
        headers=_headers(),
        json={"filter": {"property": "episode_id", "rich_text": {"equals": episode_id}}},
        timeout=60,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError("No Episodes row with episode_id=" + episode_id)
    return results[0]["id"]


def _read_brain_json(page_id):
    url = NOTION_API + "/blocks/" + page_id + "/children?page_size=100"
    while url:
        r = requests.get(url, headers=_headers(), timeout=60)
        r.raise_for_status()
        data = r.json()
        for blk in data.get("results", []):
            if blk.get("type") == "code":
                code = blk["code"]
                text = "".join(t.get("plain_text", "") for t in code.get("rich_text", []))
                if text.strip().startswith("{"):
                    return json.loads(text)
        if data.get("has_more"):
            url = NOTION_API + "/blocks/" + page_id + "/children?page_size=100&start_cursor=" + data.get("next_cursor")
        else:
            url = None
    raise RuntimeError("brain_input json code block not found on page")


def _seed_file(brain):
    eid = brain["episode_id"]
    d = Path("/var/vf/episodes") / eid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "brain_input.json"
    # seed refuses to overwrite hand-authored prompts (set VF_SEED_FORCE=1 to override)
    _force = os.getenv("VF_SEED_FORCE", "0") == "1"
    if p.exists() and not _force:
        try:
            _cur = json.loads(p.read_text())
        except Exception:
            _cur = {}
        _sc = _cur.get("scenes") or []
        _authored = sum(1 for s in _sc if isinstance(s, dict) and (s.get("image_prompt") or "").strip())
        if _authored:
            raise RuntimeError(
                "refusing to overwrite %s: %d hand-authored image_prompt(s) present; "
                "run the pipeline directly or set VF_SEED_FORCE=1" % (p, _authored)
            )
    p.write_text(json.dumps(brain, ensure_ascii=False, indent=2))
    return p


def _visual_terms(brain):
    vt = brain.get("visual_terms")
    if vt:
        return vt
    terms = []
    for s in brain.get("scenes", []):
        ip = s.get("image_prompt", "")
        terms.append(" ".join(ip.split()[:6]))
    return terms[:8]


async def _render(brain):
    lang = brain.get("lang_code") or "en"
    if isinstance(lang, list):
        lang = lang[0] if lang else "en"
    res = await run_pipeline(
        episode_id=brain["episode_id"],
        niche=brain.get("niche", "documentary"),
        lang_code=lang,
        tts_backend="auto",
        story_text=brain["story"],
        visual_terms=_visual_terms(brain),
        bgm_mood=brain.get("bgm_mood", "dramatic"),
        hook_3s=brain.get("hook_3s"),
        scenes=brain.get("scenes"),
        character_pack=brain.get("character_pack"),
        art_style=brain.get("art_style"),
        trend_keywords=brain.get("trend_keywords"),
        brain=brain,
    )

    # AUTO B9->B10 (Rule 122, 23/08/2026 night): render succeeding now auto-
    # triggers SEO packaging + Notion sync + YouTube upload + Gate 2 dispatch
    # with NO manual VPS/Antigravity step. The human is only the gate AT
    # Gate 2 (post-upload approve/reject via the existing 4 Telegram buttons),
    # never before it. Failure here never re-raises: a render that succeeded
    # must not be lost/blocked because of a downstream SEO/upload hiccup --
    # it is reported via Telegram + result payload for manual retry instead.
    final_video = res.get("final_169") or res.get("final_916") or res.get("final_11")
    if final_video:
        try:
            from scripts.execute_b10_auto_seo_upload_gate2 import run as _run_b10_auto
            b10_result = await _run_b10_auto(
                episode_id=brain["episode_id"],
                market=lang,
                privacy_status="unlisted",
            )
            res["b10_auto"] = {"status": "ok", **b10_result}
            logger.info("[B10-AUTO] auto-triggered after render for %s -> video_id=%s",
                        brain["episode_id"], b10_result.get("video_id"))
        except Exception as _b10_err:
            logger.exception("[B10-AUTO] auto-trigger failed for %s", brain["episode_id"])
            res["b10_auto"] = {"status": "error", "error": str(_b10_err)}
            try:
                from app.services import telegram_notify as _tg
                await _tg.notify_error("B10 auto-trigger (post-render)", brain["episode_id"], str(_b10_err))
            except Exception:
                pass
    else:
        logger.warning("[B10-AUTO] skip: no final video output for %s", brain["episode_id"])
        res["b10_auto"] = {"status": "skipped", "reason": "no final video"}

    return res


@router.post("/api/v1/produce-episode")
async def produce_episode_endpoint(req: ProduceEpisodeRequest):
    """One-button: Notion Episodes row (status=approved) -> full S2->S7 render.

    Mirrors orchestrator/run_pipeline.py so n8n (or any caller) can trigger
    production via HTTP instead of shelling into the VPS.
    """
    try:
        db_id = _resolve_episodes_db()
        page_id = _find_episode_page(db_id, req.episode_id)
        brain = _read_brain_json(page_id)
        brain.setdefault("episode_id", req.episode_id)
        seed_path = _seed_file(brain)
        if req.seed_only:
            return {"status": "ok", "seeded": str(seed_path), "rendered": False}
        result = await _render(brain)
        return {"status": "ok", "seeded": str(seed_path), "rendered": True, "result": result}
    except Exception as e:
        logger.exception("[produce_episode] failed")
        raise HTTPException(status_code=500, detail=str(e))
