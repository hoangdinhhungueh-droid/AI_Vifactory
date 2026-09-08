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


async def _notify_gate2(task_id: str, n_scenes: int, n_bg: int, n_fg: int, score: str, n_thumb: int = 2,
                        topic: str = "", director_archetype: str = "", title_a: str = "", title_b: str = "") -> None:
    from app.services.telegram_buttons import send_gate2_card
    await send_gate2_card(task_id, n_scenes, n_bg, n_fg, score, n_thumb=n_thumb,
                          topic=topic, director_archetype=director_archetype, title_a=title_a, title_b=title_b)




async def _notify_gate25_manual_review(task_id: str, reason: str) -> None:
    """
    Notify that episode requires HG2.5 manual prompt engineering review.
    02/09/2026: Added for content policy refusal routing.
    """
    from app.services import telegram_notify as tg
    await tg.notify_error(
        "HG2.5 Manual Review Required",
        task_id,
        f"GPT content policy refusal. Manual prompt engineering needed.\n\nReason: {reason[:300]}"
    )


async def _notify_failure(task_id: str, stage: str, detail: str) -> None:
    from app.services import telegram_notify as tg
    await tg.notify_error("HG1 chain failed at %s" % stage, task_id, detail)


def run_chain(task_id: str) -> int:
    ep_dir = EPISODES / task_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    meta = _load_pending(task_id)
    keyword = meta.get("keyword") or meta.get("topic_name") or task_id
    niche = meta.get("niche_brief") or "General"

    # ---- B1.5 competitor recon (Two-Pass Recon & Competitor Anatomy) --
    stage = "B1.5"
    try:
        from app.services.competitor_recon_b15 import run_b15
        card_file = ep_dir / "competitor_intel_card.json"
        card = None
        if card_file.exists() and card_file.stat().st_size > 100:
            try:
                card = json.loads(card_file.read_text(encoding="utf-8"))
                _log(stage, "Reusing existing valid competitor intel card from %s" % card_file)
            except Exception:
                card = None

        if not card:
            _log(stage, "Two-Pass competitor recon for keyword=%r (niche=%r)" % (keyword, niche))
            card = run_b15(task_id, keyword, niche)
            if not card:
                raise RuntimeError("B1.5 recon returned no intel card for task %s" % task_id)

        _meta = card.get("collection_meta") or {}
        _log(stage, "intel card: %d competitors, %d gaps, %d transcripts, persisted=%s" % (
            len(card.get("competitor_benchmarks") or []),
            len(card.get("audience_comment_gaps") or []),
            _meta.get("transcripts_captured", 0),
            card_file.exists()))
    except Exception as e:
        _log(stage, "FAILED (%s: %s)" % (type(e).__name__, e))
        raise RuntimeError("B1.5 competitor recon failed: %s" % e)

    # ---- B1.5.5 Grounding Layer Fact-Verification (Rule 118 & Rule 121)
    stage = "B1.5.5"
    grounding_file = ep_dir / "grounding_intel.json"
    g_intel = None
    if grounding_file.exists() and grounding_file.stat().st_size > 100:
        try:
            g_intel = json.loads(grounding_file.read_text(encoding="utf-8"))
            _log(stage, "Reusing existing grounding_intel.json from %s" % grounding_file)
        except Exception:
            g_intel = None

    if not g_intel:
        _log(stage, "Running live Google Search Grounding for %s" % task_id)
        try:
            from app.services.grounding_layer_b15 import run_grounding_research, passes_grounding_gate
            g_intel = run_grounding_research(
                topic=keyword,
                search_hint=niche,
                market=meta.get("market") or "EN"
            )
            g_ok, g_msg = passes_grounding_gate(g_intel, min_verified=2, require_whitelist=True)
            if not g_ok:
                _log(stage, "FATAL: Grounding Gate REJECTED (%s). Aborting pipeline!" % g_msg)
                raise RuntimeError(f"B1.5.5 Grounding Gate REJECTED: {g_msg}. Cannot proceed to B2!")
            grounding_file.write_text(json.dumps(g_intel, ensure_ascii=False, indent=2), encoding="utf-8")
            _log(stage, "grounding intel saved: %d claims (%s)" % (len(g_intel.get("claims", [])), g_msg))
        except Exception as ge:
            _log(stage, "FATAL: Grounding Layer execution failed: %s" % ge)
            raise RuntimeError(f"B1.5.5 Grounding Layer failed: {ge}")
    else:
        from app.services.grounding_layer_b15 import passes_grounding_gate
        g_ok, g_msg = passes_grounding_gate(g_intel, min_verified=2, require_whitelist=True)
        if not g_ok:
            _log(stage, "FATAL: Existing grounding_intel.json fails verification (%s). Aborting pipeline!" % g_msg)
            raise RuntimeError(f"B1.5.5 Grounding Gate REJECTED on existing intel: {g_msg}")
        _log(stage, "Existing grounding intel verified OK: %s" % g_msg)

    # ---- B1.6 Early SEO Package & 60s Hook Forge (Rule 119 & Rule 444) ---
    stage = "B1.6"
    seo_pkg_file = ep_dir / "seo_package.json"
    seo_pkg = None
    if seo_pkg_file.exists() and seo_pkg_file.stat().st_size > 100:
        try:
            seo_pkg = json.loads(seo_pkg_file.read_text(encoding="utf-8"))
            _log(stage, "Reusing existing valid SEO package from %s" % seo_pkg_file)
        except Exception:
            seo_pkg = None

    if not seo_pkg:
        _log(stage, "Forging early SEO package & 60s An Ong Hook for task %s via GPT-6-Astra" % task_id)
        try:
            from app.services.seo_package_forge import forge_seo_package
            seo_pkg = forge_seo_package(
                task_id=task_id,
                target_keyword=keyword,
                market=meta.get("market") or "EN",
                niche_brief=niche,
                competitor_card=card if 'card' in locals() else None,
                rising_queries=meta.get("rising_queries") or [],
                breakout_queries=meta.get("breakout_queries") or []
            )
            _log(stage, "SEO package forged: Title A=%r (60s Hook: %d words)" % (
                seo_pkg.get("title_a"), len((seo_pkg.get("hook_60s") or "").split())
            ))
        except Exception as e:
            _log(stage, "Warning: early SEO forge failed (%s: %s). Continuing to B2..." % (type(e).__name__, e))

    # ---- B2 5-Beat Investigative Docudrama (Rule 445) ----------------
    stage = "B2"
    from app.services.story_engine_b2 import generate_5_arc_story
    _log(stage, "generating 5-beat investigative docudrama via HHTech Reasoner")
    brain = generate_5_arc_story(task_id)
    story_text = brain.get("story") or brain.get("full_script") or ""
    score = str(brain.get("story_gate_score") or "n/a")
    _log(stage, "story generated (%d words), story_gate_score=%s" % (len(story_text.split()), score))

    # ---- B2.1 Fact & Causal Integrity Audit Gate (Rule 118 & Rule 130)
    fact_audit = brain.get("fact_causal_audit") or {}
    f_verdict = fact_audit.get("verdict", "PASS").upper()
    f_score = float(fact_audit.get("audit_score", 10.0))
    _log(stage, f"B2.1 Fact & Causal Audit (claude-opus-5): Verdict={f_verdict}, Score={f_score}/10")
    if f_verdict == "FAIL" or f_score < 7.5:
        veto_reason = fact_audit.get("veto_reason") or fact_audit.get("audit_notes") or "Script failed fact/causal integrity audit"
        _log(stage, f"FATAL: B2.1 Fact & Causal Audit REJECTED ({f_score}/10). Reason: {veto_reason}. Halting pipeline before B3!")
        raise RuntimeError(f"B2.1 Fact & Causal Audit REJECTED ({f_score}/10): {veto_reason}. Halting pipeline before B3!")
    _log(stage, f"B2.1 Fact & Causal Audit PASSED ({f_score}/10). Proceeding directly to B3 Hollywood Director Plan!")

    # ---- B3 Hollywood Art Director & Scene Breakdown Engine (Rule 125)
    stage = "B3"
    from app.services.director_planner_b3 import generate_director_plan
    _log(stage, "executing Hollywood Art Director & 8-axis scene breakdown")
    director_plan = generate_director_plan(
        episode_id=task_id,
        story_text=story_text,
        intel_card=card if 'card' in locals() else None,
        metadata={"niche": brain.get("niche") or "Finance", "topic": brain.get("topic") or task_id}
    )
    scenes = director_plan.get("scenes") or []
    _log(stage, "director plan ready: %d scenes (Archetype: %s)" % (len(scenes), director_plan.get("director_archetype", "Standard")))
    if not scenes:
        raise RuntimeError("B3 produced no scenes in director plan")

    # ---- B3.5 prompt forge with scene semantic coupling --------------
    stage = "B3.5"
    from app.services.prompt_forge import generate_scene_prompts, push_prompts_to_notion, ContentPolicyRefusalError
    
    # Build enriched BG and FG metadata preserving scene pairings
    bg_dict, fg_dict = {}, {}
    for s in scenes:
        bg_k = s.get("background_reuse_key")
        fg_k = s.get("foreground_reuse_key")
        arc = s.get("arc", "")
        narration = s.get("narration", "")
        bg_hint = s.get("image_prompt", "")
        fg_hint = s.get("foreground_prompt", "")

        if bg_k:
            if bg_k not in bg_dict:
                bg_dict[bg_k] = {
                    "beat": arc,
                    "narration_context": narration[:400],
                    "visual_hint": bg_hint,
                    "paired_foregrounds": [fg_k] if fg_k else []
                }
            elif fg_k and fg_k not in bg_dict[bg_k].get("paired_foregrounds", []):
                bg_dict[bg_k]["paired_foregrounds"].append(fg_k)

        if fg_k:
            if fg_k not in fg_dict:
                fg_dict[fg_k] = {
                    "beat": arc,
                    "narration_context": narration[:400],
                    "visual_hint": fg_hint,
                    "paired_backgrounds": [bg_k] if bg_k else []
                }
            elif bg_k and bg_k not in fg_dict[fg_k].get("paired_backgrounds", []):
                fg_dict[fg_k]["paired_backgrounds"].append(bg_k)

    _log(stage, "forging prompts for %d BG keys, %d FG keys (scene semantic coupling preserved)" % (len(bg_dict), len(fg_dict)))
    if not bg_dict:
        raise RuntimeError("no background_reuse_key on any scene -- B2 schema regression")
    
    # Handle GPT content policy refusals gracefully (02/09/2026 P0 fix)
    try:
        prompts = generate_scene_prompts(
            bg_dict=bg_dict,
            fg_dict=fg_dict,
            story_title=brain.get("topic") or task_id,
            scenes=scenes
        )
        (ep_dir / "prompts_forge.json").write_text(
            json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")
        n_bg = len(prompts.get("backgrounds") or {})
        n_fg = len(prompts.get("foregrounds") or {})
        n_thumb = len(prompts.get("thumbnails") or {})
        _log(stage, "%d BG prompts, %d FG prompts, %d Thumbnails -> Notion" % (n_bg, n_fg, n_thumb))
        push_prompts_to_notion(prompts, task_id, task_id=task_id)
        
    except ContentPolicyRefusalError as e:
        # GPT refused due to sensitive content - route to HG2.5 manual review
        _log(stage, "CONTENT POLICY REFUSAL - routing to HG2.5 manual review")
        _log(stage, "Refusal: %s" % str(e)[:200])
        
        # Create marker file for manual prompt engineering
        refusal_marker = {
            "status": "NEEDS_MANUAL_REVIEW",
            "reason": "content_policy_refusal",
            "refusal_detail": str(e)[:500],
            "bg_keys_needed": list(bg_dict.keys()),
            "fg_keys_needed": list(fg_dict.keys()),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        (ep_dir / "prompts_forge.json").write_text(
            json.dumps(refusal_marker, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Notify for manual intervention
        asyncio.run(_notify_gate25_manual_review(task_id, str(e)))
        
        _log(stage, "Episode marked for HG2.5 manual prompt engineering")
        _log("HG2.5", "Waiting for human to craft prompts for sensitive topic")
        return 0  # Exit cleanly - not a failure, just needs human input

    # ---- Human Gate 2 -------------------------------------------------
    seo_pkg_file = ep_dir / "seo_package.json"
    t_a, t_b = "", ""
    if seo_pkg_file.exists():
        try:
            s_data = json.loads(seo_pkg_file.read_text(encoding="utf-8"))
            t_a = s_data.get("title_a", "")
            t_b = s_data.get("title_b", "")
        except Exception:
            pass
    asyncio.run(_notify_gate2(
        task_id, len(scenes), n_bg, n_fg, score, n_thumb=n_thumb,
        topic=brain.get("topic") or task_id,
        director_archetype=director_plan.get("director_archetype", "Hollywood Principle"),
        title_a=t_a, title_b=t_b
    ))
    _log("HG2", "card sent, waiting for images from Antigravity")
    return 0




def main() -> int:
    if len(sys.argv) < 2:
        print("usage: produce_episode_hg1.py <task_id>", file=sys.stderr)
        return 2
    task_id = sys.argv[1].strip()
    _log("START", "task_id=%s pid=%d" % (task_id, os.getpid()))
    try:
        return run_chain(task_id)
    except Exception as e:
        tb = traceback.format_exc()
        _log("FAILED", "%s: %s\n%s" % (type(e).__name__, e, tb))
        # Ensure lock file is cleaned up so future attempts are not blocked
        lock_file = Path("/var/vf/locks") / ("%s.lock" % task_id)
        if lock_file.exists():
            try:
                lock_file.unlink()
                _log("CLEANUP", "Removed lockfile %s" % lock_file)
            except Exception:
                pass
        try:
            asyncio.run(_notify_failure(task_id, "chain", "%s: %s" % (type(e).__name__, e)))
        except Exception as ne:
            _log("FAILED", "could not notify: %s" % ne)
        return 1


if __name__ == "__main__":
    sys.exit(main())
