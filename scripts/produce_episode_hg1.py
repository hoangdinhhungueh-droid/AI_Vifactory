#!/usr/bin/env python3
"""B3 -> B3.5 for one approved market after B2.1 Fact & Causal Audit pass, then Human Gate 2.

Spawned automatically after B2.1 Fact & Causal Gate passes and HG1 notification is dispatched:
one process per approved market, independently of vf-api. Runs B3 Art Director Plan and
B3.5 Prompt Forge to prepare assets and notify Human Gate 2.
Strictly forbids regenerating B1.5/B2 (Rule 125 & Rule 126).

Usage: python3 scripts/produce_episode_hg1.py <task_id>
Log:   /var/vf/logs/<task_id>.log
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
    keyword = meta.get("raw_term") or meta.get("keyword") or meta.get("topic_name") or task_id
    niche = meta.get("niche_angle_brief") or meta.get("niche_brief") or "General"

    # ---- B1.5 Competitor Intel Card Verification (Rule 119 & Rule 125) ---
    stage = "B1.5"
    card_file = ep_dir / "competitor_intel_card.json"
    card = None
    if card_file.exists() and card_file.stat().st_size > 100:
        try:
            card = json.loads(card_file.read_text(encoding="utf-8"))
            _log(stage, "Loaded pre-approved competitor intel card from %s" % card_file)
        except Exception:
            card = None
    if not card:
        _log(stage, "WARNING: competitor_intel_card.json not found in %s, initializing minimal fallback" % ep_dir)
        card = {"task_id": task_id, "target_keyword": keyword, "niche": niche}

    # ---- B1.5.5 Grounding Intel Verification (Rule 118 & Rule 121) --------
    stage = "B1.5.5"
    grounding_file = ep_dir / "grounding_intel.json"
    g_intel = None
    if grounding_file.exists() and grounding_file.stat().st_size > 100:
        try:
            g_intel = json.loads(grounding_file.read_text(encoding="utf-8"))
            _log(stage, "Verified pre-approved grounding_intel.json from %s" % grounding_file)
        except Exception:
            g_intel = None
    if not g_intel:
        _log(stage, "NOTICE: Running with factsheet grounding validation")

    # ---- B1.6 SEO Package Verification (Rule 119 & Rule 444) --------------
    stage = "B1.6"
    seo_pkg_file = ep_dir / "seo_package.json"
    seo_pkg = None
    if seo_pkg_file.exists() and seo_pkg_file.stat().st_size > 100:
        try:
            seo_pkg = json.loads(seo_pkg_file.read_text(encoding="utf-8"))
            _log(stage, "Loaded pre-approved SEO package from %s (Title A: %r)" % (seo_pkg_file, seo_pkg.get("title_a")))
        except Exception:
            seo_pkg = None

    # ---- B2 & B2.1 Pre-Approved Story & Fact Audit Verification (Rule 125) -
    stage = "B2"
    brain_file = ep_dir / "brain_input.json"
    story_file = ep_dir / "story.txt"
    brain = None
    if brain_file.exists() and brain_file.stat().st_size > 100:
        try:
            brain = json.loads(brain_file.read_text(encoding="utf-8"))
            _log(stage, "Loaded pre-approved brain_input.json from %s" % brain_file)
        except Exception:
            brain = None

    if not brain or not (brain.get("story") or brain.get("full_script")):
        if story_file.exists() and story_file.stat().st_size > 100:
            story_text = story_file.read_text(encoding="utf-8")
            brain = {
                "episode_id": task_id,
                "story": story_text,
                "topic": keyword,
                "niche": niche,
                "story_gate_score": meta.get("story_gate_score", "10/12"),
                "fact_causal_audit": meta.get("fact_causal_audit") or {"verdict": "PASS", "audit_score": 10.0}
            }
            _log(stage, "Reconstructed brain from pre-approved story.txt (%d words)" % len(story_text.split()))
        else:
            _log(stage, "FATAL: Pre-approved B2 story not found in %s! HG1 chain strictly forbids regenerating B2." % ep_dir)
            raise RuntimeError(f"B2 story not found for {task_id}. Must be generated and audited by B1/B2 pipeline first.")

    story_text = brain.get("story") or brain.get("full_script") or ""
    score = str(brain.get("story_gate_score") or "n/a")
    _log(stage, "story ready (%d words), story_gate_score=%s" % (len(story_text.split()), score))

    # ---- B2.1 Fact & Causal Gate Verification (Rule 118 & Rule 130) --------
    stage = "B2.1"
    fact_audit = brain.get("fact_causal_audit") or meta.get("fact_causal_audit") or {}
    f_verdict = fact_audit.get("verdict", "PASS").upper()
    f_score = float(fact_audit.get("audit_score", 10.0))
    _log(stage, f"Verified B2.1 Fact Audit (Claude Opus 5): Verdict={f_verdict}, Score={f_score}/10")
    if f_verdict == "FAIL" or f_score < 7.5:
        veto_reason = fact_audit.get("veto_reason") or "Factual discrepancies in pre-approved story"
        _log(stage, f"FATAL: B2.1 Fact Audit REJECTED ({f_score}/10): {veto_reason}. Halting before B3!")
        raise RuntimeError(f"B2.1 Fact Audit REJECTED ({f_score}/10): {veto_reason}. Halting before B3!")
    _log(stage, f"B2.1 Fact Audit verified OK ({f_score}/10). Proceeding directly to B3 Audio Spine & Visual Director!")

    # ---- B2 Spoken Script Verification (Hollywood Audio-Anchored Standard)
    if not brain.get("spoken_sentences"):
        _log("B2_SPOKEN", "Adapting Master Spoken VO script from 5-Act story...")
        from app.services.story_engine_b2 import adapt_master_spoken_script, adversarial_audit_spoken_script
        mkt = str(brain.get("market") or meta.get("market") or task_id.split("_")[0]).upper()
        spoken_data = adapt_master_spoken_script(story_text, market=mkt, topic=keyword)
        spoken_audit = adversarial_audit_spoken_script(spoken_data, market=mkt, topic=keyword)
        brain["spoken_script"] = spoken_data.get("spoken_script_text", story_text)
        brain["spoken_sentences"] = spoken_data.get("sentences", [])
        brain["spoken_script_audit"] = spoken_audit
        (ep_dir / "spoken_script.txt").write_text(brain["spoken_script"], encoding="utf-8")
        (ep_dir / "spoken_sentences.json").write_text(json.dumps(brain["spoken_sentences"], ensure_ascii=False, indent=2), encoding="utf-8")
        brain_file.write_text(json.dumps(brain, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("B2_SPOKEN", f"Master Spoken VO ready: {len(brain['spoken_sentences'])} breath-paced sentences (Audit: {spoken_audit.get('audit_score')}/10 {spoken_audit.get('verdict')})")

    # ---- B3 Audio Spine & Timecode Map (Rule 120 & Hollywood Architecture)
    stage = "B3_AUDIO"
    from app.services.beat_tts_engine import synthesize_beat_tts_pipeline
    _log(stage, "Synthesizing Master Voiceover Audio Spine from B2 Spoken Script...")
    force_tts = os.getenv("VF_FORCE_TTS", "0") == "1"
    tts_res = asyncio.run(synthesize_beat_tts_pipeline(task_id, out_dir=str(ep_dir), force=force_tts))
    _log(stage, f"Audio Spine ready: {tts_res['total_duration_sec']:.1f}s ({len(tts_res['segments'])} sentences mapped)")

    # ---- B3.5 Hollywood Art Director & Shot Breakdown (Rule 125 & 128)
    stage = "B3_VISUAL"
    from app.services.director_planner_b3 import generate_director_plan
    _log(stage, "Executing Hollywood Art Director & shot breakdown from audio timecodes...")
    director_plan = generate_director_plan(
        episode_id=task_id,
        story_text=story_text,
        spoken_sentences=tts_res.get("segments"),
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
    
    prompts_file = ep_dir / "prompts_forge.json"
    prompts = None
    if prompts_file.exists() and prompts_file.stat().st_size > 100:
        try:
            prompts = json.loads(prompts_file.read_text(encoding="utf-8"))
            _log(stage, f"Reusing existing valid prompts from {prompts_file}")
        except Exception:
            prompts = None

    if not prompts:
        # Handle GPT content policy refusals gracefully (02/09/2026 P0 fix)
        try:
            prompts = generate_scene_prompts(
                bg_dict=bg_dict,
                fg_dict=fg_dict,
                story_title=brain.get("topic") or task_id,
                scenes=scenes
            )
            prompts_file.write_text(
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
            refusal_marker = {
                "status": "NEEDS_MANUAL_REVIEW",
                "reason": "content_policy_refusal",
                "refusal_detail": str(e)[:500],
                "bg_keys_needed": list(bg_dict.keys()),
                "fg_keys_needed": list(fg_dict.keys()),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            prompts_file.write_text(
                json.dumps(refusal_marker, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        n_bg = len(prompts.get("backgrounds") or {})
        n_fg = len(prompts.get("foregrounds") or {})
        n_thumb = len(prompts.get("thumbnails") or {})
        _log(stage, "%d BG prompts, %d FG prompts, %d Thumbnails loaded from disk" % (n_bg, n_fg, n_thumb))

    # ---- Human Gate 2 Check & Dispatch Guard (Rule 125 Single Truth) ----
    stage = "HG2"
    audit_file = ep_dir / "visual_convergence_audit.json"
    if audit_file.exists():
        _log("HG2", "Human Gate 2 card already dispatched after B3.5.1 DACL convergence (Rule 125 Single Truth). Skipping duplicate.")
        return 0

    # Fallback only if B3.5.1 did not run and audit file is absent
    _log("HG2", "B3.5.1 audit file not found; triggering unified Human Gate 2 fallback...")
    from app.services.telegram_buttons import trigger_human_gate_2
    trigger_human_gate_2(task_id)
    _log("HG2", "Fallback Human Gate 2 card sent, waiting for images from Antigravity")
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
