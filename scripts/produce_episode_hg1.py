#!/usr/bin/env python3
"""B1.5 -> B2 -> B3 -> B3.5 for one approved market, then Human Gate 2.

Spawned by the HG1 approve button (app/services/telegram_actions.py) as a
detached subprocess: one process per approved market, so approving EN does not
touch JP/KR and a crash in one market cannot take the others down. Runs
independently of vf-api, so restarting the API mid-chain does not lose work.

Usage: python3 scripts/produce_episode_hg1.py <task_id>
Log:   /var/vf/logs/<task_id>.log (the caller redirects stdout/stderr there)
"""
import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, "/root/video_factory")

EPISODES = Path("/var/vf/episodes")
PENDING = Path("/var/vf/pending_tasks")


def _log(stage: str, msg: str) -> None:
    print("[%s] %s: %s" % (time.strftime("%H:%M:%S"), stage, msg), flush=True)


def _load_pending(task_id: str) -> dict:
    p = PENDING / ("%s.json" % task_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


async def _notify_gate2(task_id: str, n_scenes: int, n_bg: int, n_fg: int, score: str) -> None:
    from app.services.telegram_buttons import send_gate2_card
    await send_gate2_card(task_id, n_scenes, n_bg, n_fg, score)


async def _notify_failure(task_id: str, stage: str, detail: str) -> None:
    from app.services import telegram_notify as tg
    await tg.notify_error("HG1 chain failed at %s" % stage, task_id, detail)


def run_chain(task_id: str) -> int:
    ep_dir = EPISODES / task_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    meta = _load_pending(task_id)
    keyword = meta.get("keyword") or meta.get("topic_name") or task_id
    niche = meta.get("niche_brief") or "General"

    # ---- B1.5 competitor recon (data collection only) -----------------
    stage = "B1.5"
    try:
        from app.services.competitor_recon_b15 import run_b15
        _log(stage, "recon for keyword=%r" % keyword)
        card = run_b15(task_id, keyword, niche)
        if not card:
            _log(stage, "no intel card (recon returned nothing) - B2 continues without it")
        else:
            _meta = card.get("collection_meta") or {}
            _log(stage, "intel card: %d competitors, %d gaps, %d transcripts" % (
                len(card.get("competitor_benchmarks") or []),
                len(card.get("audience_comment_gaps") or []),
                _meta.get("transcripts_captured", 0)))
    except Exception as e:
        # Recon is enrichment, not a hard dependency: B2 runs without it.
        _log(stage, "SKIPPED (%s: %s)" % (type(e).__name__, e))

    # ---- B2 story + B3 director plan ---------------------------------
    stage = "B2/B3"
    from app.services.story_engine_b2 import generate_5_arc_story
    _log(stage, "generating 5-act story + director plan via GPT-5.6-Sol")
    brain = generate_5_arc_story(task_id)
    scenes = brain.get("scenes") or []
    score = str(brain.get("story_gate_score") or "n/a")
    _log(stage, "%d scenes, story_gate_score=%s" % (len(scenes), score))
    if not scenes:
        raise RuntimeError("B2 produced no scenes")

    # ---- B3.5 prompt forge -------------------------------------------
    stage = "B3.5"
    from app.services.prompt_forge import generate_scene_prompts, push_prompts_to_notion
    bg_dict, fg_dict = {}, {}
    for s in scenes:
        for key_field, target in (("background_reuse_key", bg_dict),
                                  ("foreground_reuse_key", fg_dict)):
            k = s.get(key_field)
            if k and k not in target:
                target[k] = {
                    "beat": s.get("arc"),
                    "narration_context": s.get("narration", "")[:400],
                }
    _log(stage, "forging prompts for %d BG keys, %d FG keys" % (len(bg_dict), len(fg_dict)))
    if not bg_dict:
        raise RuntimeError("no background_reuse_key on any scene -- B2 schema regression")
    prompts = generate_scene_prompts(bg_dict, fg_dict, brain.get("topic") or task_id)
    (ep_dir / "prompts_forge.json").write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    n_bg = len(prompts.get("backgrounds") or {})
    n_fg = len(prompts.get("foregrounds") or {})
    _log(stage, "%d BG prompts, %d FG prompts -> Notion" % (n_bg, n_fg))
    push_prompts_to_notion(prompts, task_id, task_id=task_id)

    # ---- Human Gate 2 -------------------------------------------------
    asyncio.run(_notify_gate2(task_id, len(scenes), n_bg, n_fg, score))
    _log("HG2", "card sent, waiting for images from Antigravity")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: produce_episode.py <task_id>", file=sys.stderr)
        return 2
    task_id = sys.argv[1].strip()
    _log("START", "task_id=%s pid=%d" % (task_id, os.getpid()))
    try:
        return run_chain(task_id)
    except Exception as e:
        tb = traceback.format_exc()
        _log("FAILED", "%s: %s\n%s" % (type(e).__name__, e, tb))
        try:
            asyncio.run(_notify_failure(task_id, "chain", "%s: %s" % (type(e).__name__, e)))
        except Exception as ne:
            _log("FAILED", "could not notify: %s" % ne)
        return 1


if __name__ == "__main__":
    sys.exit(main())
