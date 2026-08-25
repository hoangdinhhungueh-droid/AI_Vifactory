"""
Full production pipeline: S2 story -> S3 schema -> S4 TTS ->
S5 visuals -> S6 subtitle -> S7 render.

NOTION-BRAIN MODE (vf 2026-06):
  Notion is the brain, VPS is the hands. When the caller supplies
  story_text / visual_terms / bgm_mood (authored in Notion and passed in
  by the API or the n8n orchestrator), the VPS executes DETERMINISTICALLY
  from those fields and DOES NOT self-generate story or visuals.
  This eliminates the "random output" problem.

  If VF_REQUIRE_BRAIN=1 and no story_text is supplied, the pipeline refuses
  to run (rather than inventing a random story).
"""
import asyncio, os, json, logging, time, uuid, sys, re
import urllib.request
from pathlib import Path

from app.pipeline.s3_schema import validate_s3_output
from app.services import story_quality as _sq
from app.services import story_gate as _sgate
from app.services import story_judge as _sjudge
from app.services import chapter_split as _cs
from app.services.mpt_ported.story_segmenter import segment_scenes as _seg_scenes  # Rule 75
from app.pipeline.stages.s4_tts import run_s4
from app.pipeline.stages.s5_visuals import run_s5
from app.pipeline.stages.s6_subtitle import run_s6
from app.pipeline.stages.s7_render import run_s7
from app.pipeline.fallback_clip import make_fallback_clip
from app.services import telegram_notify as tg
from app.services import scene_expander as _scx
from app.services.simulated_asset_gate import mark_simulated
from app.services import preflight_render_gate as _pfgate
try:
    from app.services.credit_gate import usage_summary as _usage_summary
except Exception:
    _usage_summary = None

def _pick_latest_stock_cache_clip() -> str | None:
    """Pick newest downloaded stock clip from /tmp/vf/stock_cache."""
    try:
        import glob, os
        files = glob.glob('/tmp/vf/stock_cache/*.mp4')
        if not files: return None
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        return files[0]
    except Exception:
        return None


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LLM_URL = "http://127.0.0.1:8000/api/v1/llm"

# Legacy self-generation prompt. ONLY used when Notion-brain content is absent
# AND VF_REQUIRE_BRAIN != 1 (i.e. explicit opt-in to legacy/random behavior).
STORY_PROMPT = (
    "Write a SHORT, dramatic story (exactly 80-100 words, English). "
    "Genre: {niche}. Audience: YouTube Shorts. "
    "Style: hook in first sentence, emotional peak at end, narration voice. "
    "Return only the story text, no title, no commentary."
)

FALLBACK_STORY = (
    "She trusted him with everything - her secrets, her heart, her future. "
    "He smiled and took it all. One morning she woke up to silence. "
    "The house was empty. The accounts, drained. "
    "But what he did not know: she had already taken everything back. "
    "One step ahead. Always."
)


def _call_llm(prompt: str, task_type: str = "S2_story_write") -> str:
    payload = json.dumps({"prompt": prompt, "task_type": task_type}).encode()
    req = urllib.request.Request(
        LLM_URL, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        return data.get("text", "").strip()
    except Exception as e:
        logger.warning("[S2] LLM call failed: %s, using fallback story", e)
        return ""



_PIPELINE_META_NOTE_RE = re.compile(r"\[[^\[\]]{0,600}\]")


def _strip_pipeline_meta_notes(text: str):
    """Strip bracketed pipeline/editorial meta-notes (e.g. a note like
    "[Full N-word story lives in the Notion page ...]") from narrator
    text before it reaches TTS, story_gate, story_judge, chapters, or
    subtitles.

    ADDED 08/08/2026 after an EP005 incident where a one-off seed script
    (scripts/seed_brain_input_ep005.py) hard-coded such a note directly
    into brain_input.json's "story" field; it flowed unsanitized through
    this function into TTS and was read aloud, then leaked into
    subtitles.srt. No real episode narration has ever legitimately
    needed square brackets, so any bracketed span found in story_text is
    treated as contamination and removed here -- once, for every episode,
    regardless of which upstream script produced the brain_input.json.
    """
    stripped = []

    def _capture(m):
        stripped.append(m.group(0))
        return ''

    cleaned = _PIPELINE_META_NOTE_RE.sub(_capture, text)
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()
    return cleaned, stripped


async def run_pipeline(
    episode_id: str = None,
    niche: str = "betrayal revenge",
    lang_code: str = "en",
    tts_backend: str = "auto",
    story_text: str = None,
    visual_terms: list = None,
    bgm_mood: str = None,
    hook_3s: str = None,
    scenes: list = None,
    character_pack: list = None,
    trend_keywords: list = None,
    art_style: dict = None,
    brain: dict = None,
) -> dict:
    """Run full pipeline. Returns dict with output paths.

    Notion-brain params (preferred):
      story_text   : narrator script authored in Notion (Self-Write Stories).
      visual_terms : list[str] of stock-search terms authored in Notion.
      bgm_mood     : mood keyword authored in Notion (drives BGM selection).
      hook_3s      : 3-second hook line (logged / used by QA).
      art_style    : dict {style_id, style_prompt, negative_prompt} authored in
                     Notion brain; style_prompt is prepended to every AI image
                     so the whole episode is visually consistent. No human input.
    """
    if not episode_id:
        slug = niche.lower().replace(" ", "-")[:20]
        uid  = uuid.uuid4().hex[:6]
        episode_id = f"ep-{lang_code}-{slug}-{uid}"

    # DELAYED EP INCREMENT (2026-08-23): if this episode_id matches a
    # pending (not-yet-committed) task cached at Gate-1 time, commit it to
    # the Notion Story Library now -- this is the real "increment" moment,
    # triggered by /run task:<episode_id> actually starting production.
    try:
        from app.services import episode_numbering as _epnum
        _epnum.commit_if_pending(episode_id)
    except Exception as _epnum_err:
        logger.warning("[PIPELINE] episode_numbering commit_if_pending failed: %s", _epnum_err)

    out_dir = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)
    require_brain = os.getenv("VF_REQUIRE_BRAIN", "0") == "1"
    brain_mode = bool(story_text and story_text.strip())
    logger.info("[PIPELINE] START episode_id=%s niche=%s brain_mode=%s require_brain=%s",
                episode_id, niche, brain_mode, require_brain)
    t0 = time.time()
    try:
        _u0 = _usage_summary() if _usage_summary else {}
        _spend0 = float((_u0 or {}).get("today_usd") or 0)
    except Exception:
        _u0, _spend0 = {}, 0.0
    try:
        await tg.notify_production("START", episode_id, f"niche={niche} | brain_mode={brain_mode}")
    except Exception as _swallowed:
        logger.warning("[swallowed] run_episode L%d: %s: %s", 131, type(_swallowed).__name__, _swallowed)

    # -- S2: story (Notion brain preferred; NO self-generation in brain mode) --
    if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
        try:
            await tg.notify_production("S2 · Story", episode_id)
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 138, type(_swallowed).__name__, _swallowed)
    if brain_mode:
        text = story_text.strip()
        text, _meta_stripped = _strip_pipeline_meta_notes(text)
        if _meta_stripped:
            logger.warning(
                '[S2] stripped %d pipeline-meta bracket note(s) from story text '
                'before TTS/gates: %s',
                len(_meta_stripped), '; '.join(n[:120] for n in _meta_stripped))
            try:
                await tg.notify_production(
                    'S2 sanitize', episode_id,
                    f'Stripped {len(_meta_stripped)} bracketed pipeline-meta note(s) '
                    'from story text (would have leaked into TTS/subtitles). Check '
                    'the authoring script for this episode.')
            except Exception as _swallowed:
                logger.warning('[swallowed] run_episode L144b: %s: %s', type(_swallowed).__name__, _swallowed)
        logger.info("[S2] using Notion-authored story (%d chars): %s...", len(text), text[:60])
    else:
        if require_brain:
            raise RuntimeError(
                "VF_REQUIRE_BRAIN=1 but no story_text supplied. "
                "Notion is the brain: author the story in the Self-Write Stories DB "
                "and pass it in. Refusing to self-generate a random story.")
        logger.warning("[S2] LEGACY self-generation (no Notion story supplied)")
        prompt = STORY_PROMPT.format(niche=niche)
        text = _call_llm(prompt)
        if not text or len(text) < 20:
            text = FALLBACK_STORY
        logger.info("[S2] story %d chars: %s...", len(text), text[:60])

    # -- visual terms (Notion brain preferred) -----------------------------
    vterms = [str(v).strip() for v in (visual_terms or []) if str(v).strip()]
    if vterms:
        logger.info("[S2] using %d Notion-authored visual_terms", len(vterms))
    else:
        logger.warning("[S2] no visual_terms supplied; S5 will use generic fallback")

    mood = (bgm_mood or "dramatic").strip()

    # -- per-scene visual prompts + character pack + art style (Notion brain) --
    bscenes = []
    for _s in (scenes or []):
        if isinstance(_s, dict):
            _ip = (_s.get("image_prompt") or _s.get("prompt") or _s.get("term") or "").strip()
            _mp = (_s.get("motion_prompt") or _s.get("motion") or "").strip()
            if _ip or _mp:
                # FLOW FIX 27/07/2026: preserve ALL Notion-authored scene fields
                # (remotion, beat, arc_index, render_type, ...). Previously only
                # image_prompt/motion_prompt survived -> 0 Remotion cards via API.
                _sc = dict(_s)
                _sc["image_prompt"] = _ip or _mp
                _sc["motion_prompt"] = _mp or _ip
                bscenes.append(_sc)
    cpack = [c for c in (character_pack or []) if isinstance(c, dict)]
    astyle = art_style if isinstance(art_style, dict) else {}
    # -- S2.5: auto-expand story -> ~target_image_count per-scene prompts -----
    # Notion is the brain: it authors story + scene_budget + DNA; the expander
    # deterministically fills the full per-cut prompt list (no LLM, no quota).
    _brain = brain if isinstance(brain, dict) else {}
    if _brain.get("auto_generate_scenes"):
        try:
            _sg = _brain.get("scene_generation") or {}
            _tic = _brain.get("target_image_count") or {}
            _target = int(_tic.get("target") or _tic.get("max") or 0) or None
            _budget = _sg.get("scene_budget") or _brain.get("scene_budget") or []
            _style_prompt = str(astyle.get("style_prompt") or "").strip()
            _char_target = int(_sg.get("prompt_char_target") or 1500)
            _expanded = _scx.expand_scenes(
                story=text,
                scene_budget=_budget,
                style_prompt=_style_prompt,
                prompt_template=_brain.get("prompt_template"),
                seed_exemplars=bscenes,
                target_count=_target,
                char_target=_char_target,
                aspect_label="16:9 widescreen",
            )
            if _expanded:
                bscenes = _expanded
                logger.info("[S2.5] auto-generated %d scenes (target=%s, ~%d chars/prompt)",
                            len(bscenes), _target, _char_target)
        except Exception as _e:
            logger.warning("[S2.5] scene auto-expansion failed (%s); keeping authored scenes", _e)
    if bscenes:
        logger.info("[S2] using %d Notion-authored scenes (image+motion prompts)", len(bscenes))
    if cpack:
        logger.info("[S2] using character_pack with %d characters", len(cpack))
    if astyle.get("style_id") or astyle.get("style_prompt"):
        logger.info("[S2] art_style=%s style_prompt=%s...",
                    astyle.get("style_id"), str(astyle.get("style_prompt", ""))[:48])

    # -- S3: Schema validate -----------------------------------------------
    episode = {
        "episode_id": episode_id,
        "text":       text,
        "lang_code":  lang_code,
        "mood":       mood,
        "content_type": "fiction",
        "backend":    tts_backend,
        "visual_terms": vterms,
        "hook_3s":    (hook_3s or "").strip(),
        "scenes":     bscenes,
        "character_pack": cpack,
        "art_style":  astyle,
    }
    episode = validate_s3_output(episode)
    # validate_s3_output may strip unknown keys; re-assert brain fields.
    episode["visual_terms"] = vterms
    episode["mood"] = mood
    # -- Rule 75: segment narration to fit CPS caps before TTS --
    if bscenes:
        try:
            _seg_result = _seg_scenes(bscenes)
            if len(_seg_result) != len(bscenes):
                logger.info("[S3.6] story_segmenter split %d scenes -> %d scenes (CPS compliance)",
                            len(bscenes), len(_seg_result))
            bscenes = _seg_result
        except Exception as _seg_e:
            logger.warning("[S3.6] story_segmenter failed (%s); keeping original scenes", _seg_e)
    episode["scenes"] = bscenes
    try:
        with open(os.path.join(out_dir, "scenes_manifest.json"), "w") as _sf:
            json.dump({"episode_id": episode_id, "scenes": bscenes}, _sf, indent=2)
    except Exception as _e:
        logger.warning("[S2] failed to write scenes_manifest.json: %s", _e)
    episode["character_pack"] = cpack
    episode["art_style"] = astyle
    if hook_3s:
        episode["hook_3s"] = hook_3s.strip()
    logger.info("[S3] schema validated; mood=%s visual_terms=%d scenes=%d chars=%d",
                mood, len(vterms), len(bscenes), len(cpack))

    # -- S3.5: Story Quality Gate + Chapter-split (FREE, deterministic) -----
    try:
        qa = _sq.score_story(
            story_text=text,
            hook_3s=(hook_3s or "").strip() or None,
            trend_keywords=(trend_keywords or vterms or None),
            character_pack=cpack or None,
        )
        episode["quality"] = qa
        _ch = _cs.split_chapters(text)
        episode["chapters"] = _ch.get("chapters", [])
        episode["chapter_meta"] = {k: _ch[k] for k in ("n_chapters", "total_duration_s", "wpm", "split_mode") if k in _ch}
        try:
            with open(os.path.join(out_dir, "story_gate.json"), "w") as _f:
                json.dump({"quality": qa, "chapters": _ch}, _f, indent=2)
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 263, type(_swallowed).__name__, _swallowed)
        logger.info("[S3.5] quality=%.2f passed=%s n_chapters=%d total_s=%.1f",
                    qa.get("quality_score", 0), qa.get("passed"),
                    _ch.get("n_chapters", 0), _ch.get("total_duration_s", 0))
        if not qa.get("passed"):
            _qmsg = (f"score={qa.get('quality_score')} blocking={qa.get('blocking')}\n"
                     f"\u26d4 Pipeline STOPPED (S3.5). Fix the script in Notion, then re-run this episode.")
            try:
                await tg.notify_production("QUALITY_GATE_FAILED", episode_id, _qmsg)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 272, type(_swallowed).__name__, _swallowed)
            # FIX 27/07/2026: default flipped to hard-block. A failing script
            # must never continue burning TTS/render budget; go fix it in
            # Notion first. Set VF_QUAL_GATE=0 only for an explicit override.
            if os.getenv("VF_QUAL_GATE", "1") != "0":
                raise RuntimeError(f"Story quality gate FAILED: {qa.get('blocking')}")
    except RuntimeError:
        raise
    except Exception as _e:
        logger.warning("[S3.5] quality/chapter gate soft-failed: %s", _e)

    # -- S3.6: Story Brain gate (outline stage, 9 hard rules, v3) ----------
    # FLOW ENHANCE 27/07/2026 - runs BEFORE TTS so a weak script is caught
    # while it is still cheap to rewrite. VF_STORY_GATE=off|warn|block.
    # UPGRADED v2->v3 05/08/2026 per Hand-off Viec 2 decision - adds
    # narrative-arc (5 acts), segmentation, and hook-shock checks.
    try:
        _sg_mode = _sgate.gate_mode()
        if _sg_mode != "off":
            _sg = _sgate.score_story(text)
            episode["story_gate"] = _sg
            try:
                with open(os.path.join(out_dir, "story_gate.json"), "w") as _f:
                    json.dump(_sg, _f, indent=2, ensure_ascii=False)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 292, type(_swallowed).__name__, _swallowed)
            logger.info("[S3.6] story gate %s %d/%d words=%d loops=%d/%d nums=%d/%d",
                        _sg["verdict"], _sg["score"], _sg["max_score"], _sg["words"],
                        _sg["open_loop_markers"], _sg["open_loops_required"],
                        _sg["numbers_found"], _sg["numbers_required"])
            if _sg["verdict"] != "PASS":
                logger.warning("[S3.6] story gate failed: %s", ", ".join(_sg["failed"]))
                try:
                    await tg.notify_production(
                        "S3.6 story gate", episode_id,
                        f"{_sg['score']}/{_sg['max_score']} FAIL: " + ", ".join(_sg["failed"]))
                except Exception as _swallowed:
                    logger.warning("[swallowed] run_episode L%d: %s: %s", 304, type(_swallowed).__name__, _swallowed)
                if _sg_mode == "block":
                    raise RuntimeError(
                        "Story gate FAILED (" + str(_sg["score"]) + "/" + str(_sg["max_score"]) + "): "
                        + ", ".join(_sg["failed"]))
    except RuntimeError:
        raise
    except Exception as _e36:
        logger.warning("[S3.6] story gate soft-failed: %s", _e36)

    # -- S3.65: AI Story Judge (LLM semantic check, outline stage) ---------
    # ADDED 05/08/2026 per Hand-off audit (Viec 2) - catches AI-cliche tone /
    # missing narrative technique that regex-only story_gate cannot detect.
    # Fully automatic, no human approval step. VF_STORY_JUDGE=off|warn|block
    # (default warn - new gate, not yet calibrated against production data).
    try:
        _sj_mode = _sjudge.judge_mode()
        if _sj_mode != "off":
            _sj = _sjudge.judge_story(text, episode_id=episode_id)
            episode["story_judge"] = _sj
            try:
                with open(os.path.join(out_dir, "story_judge.json"), "w") as _f:
                    json.dump(_sj, _f, indent=2, ensure_ascii=False)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 3651, type(_swallowed).__name__, _swallowed)
            logger.info("[S3.65] story judge %s score=%s/6 banned=%s",
                        _sj.get("verdict"), _sj.get("score"), _sj.get("banned_phrases_found"))
            if _sj.get("verdict") == "FAIL":
                _sjmsg = f"score={_sj.get('score')}/6 banned={_sj.get('banned_phrases_found')} notes={_sj.get('notes')}"
                try:
                    await tg.notify_production("S3.65 story judge", episode_id, _sjmsg)
                except Exception as _swallowed:
                    logger.warning("[swallowed] run_episode L%d: %s: %s", 3652, type(_swallowed).__name__, _swallowed)
                if _sj_mode == "block":
                    raise RuntimeError("Story judge FAILED: " + _sjmsg)
    except RuntimeError:
        raise
    except Exception as _e365:
        logger.warning("[S3.65] story judge soft-failed: %s", _e365)

    # -- S3.7: Pre-render audit gate (materials + wiring), added 07/08/2026 --
    # Catches, BEFORE any TTS/render work starts, the exact defect classes
    # hit in EP005 production QC: background not removed, wrong/regressed
    # TTS voice, SSML leaking into spoken audio/subtitles, and missing
    # foreground/core images. Defaults to BLOCK (unlike S3.65's default
    # warn) because every check maps to a concrete production defect, not
    # a speculative heuristic. VF_PREFLIGHT_GATE=block|warn|off.
    try:
        _pf_mode = _pfgate.gate_mode()
        if _pf_mode != "off":
            _pf = _pfgate.run_preflight_gate(out_dir, brain=_brain)
            episode["preflight_render_gate"] = _pf
            try:
                with open(os.path.join(out_dir, "preflight_render_report.json"), "w") as _f:
                    json.dump(_pf, _f, indent=2, ensure_ascii=False)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 3700, type(_swallowed).__name__, _swallowed)
            logger.info("[S3.7] preflight gate verdict=%s blocks=%d warns=%d",
                        _pf.get("verdict"), len(_pf.get("blocks", [])), len(_pf.get("warns", [])))
            if _pf.get("verdict") == "BLOCKED":
                _pfmsg = "; ".join(_pf.get("blocks", []))
                try:
                    await tg.notify_production("S3.7 preflight gate BLOCKED", episode_id, _pfmsg)
                except Exception as _swallowed:
                    logger.warning("[swallowed] run_episode L%d: %s: %s", 3701, type(_swallowed).__name__, _swallowed)
                if _pf_mode == "block":
                    raise RuntimeError("Preflight render gate BLOCKED: " + _pfmsg)
    except RuntimeError:
        raise
    except Exception as _e37:
        logger.warning("[S3.7] preflight gate soft-failed: %s", _e37)

    # -- S4: TTS -----------------------------------------------------------
    logger.info("[S4] synthesizing TTS...")
    if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
        try:
            await tg.notify_production("S4 · TTS", episode_id)
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 320, type(_swallowed).__name__, _swallowed)
    # FIX 27/07/2026: the Notion/brain voice was never forwarded, so S4 always
    # fell back to the en-US-AriaNeural language default.
    try:
        _bvoice = (brain or {}).get("voice") if isinstance(brain, dict) else None
        _bvoice = _bvoice or os.environ.get("VF_TTS_VOICE") or ""
        if _bvoice:
            episode["voice"] = _bvoice
            logger.info("[S4] voice from brain/env: %s", _bvoice)
    except Exception as _ev:
        logger.warning("[S4] voice wiring skipped: %s", _ev)
    try:
        episode = await run_s4(episode)
    except Exception as _e4:
        try:
            await tg.notify_error("S4 TTS", episode_id, repr(_e4))
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 337, type(_swallowed).__name__, _swallowed)
        raise
    audio_path = episode["audio_path"]
    # run_s4 may not preserve brain fields; re-assert before S5.
    episode["visual_terms"] = vterms
    episode["scenes"] = bscenes
    try:
        with open(os.path.join(out_dir, "scenes_manifest.json"), "w") as _sf:
            json.dump({"episode_id": episode_id, "scenes": bscenes}, _sf, indent=2)
    except Exception as _e:
        logger.warning("[S2] failed to write scenes_manifest.json: %s", _e)
    episode["character_pack"] = cpack
    episode["art_style"] = astyle
    logger.info("[S4] audio=%s size=%d", audio_path, episode.get("size_bytes", 0))

    # -- S6: Subtitle align ------------------------------------------------
    logger.info("[S6] aligning subtitles (whisper)...")
    if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
        try:
            await tg.notify_production("S6 · Subtitle", episode_id)
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 425, type(_swallowed).__name__, _swallowed)
    episode["clips"] = [{"path": p} for p in clip_paths]
    try:
        episode = await run_s6(episode)
        logger.info("[S6] segments=%d srt=%s",
                    len(episode.get("segments", [])), episode.get("srt_path"))
    except Exception as e:
        logger.warning("[S6] subtitle failed: %s, continuing without subs", e)
        try:
            await tg.notify_error("S6 subtitle (degraded)", episode_id, repr(e))
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 436, type(_swallowed).__name__, _swallowed)
        episode.setdefault("segments", [])
        episode.setdefault("srt_path", None)


    # -- S4.5: Two-layer Remotion render (additive; opt-in via brain_input.json
    # render_architecture == "two_layer_v1"). Builds a silent Background+
    # Foreground visual from Notion-approved images (Image Asset Library,
    # Status=Approved) and uses it AS the clip, skipping the legacy
    # stock-clip fetch below. Any failure falls back to legacy S5 unchanged.
    twolayer_clip_path = None
    _render_arch = str((brain or {}).get("render_architecture") or "").strip()
    if _render_arch == "two_layer_v1":
        logger.info("[S4.5] two_layer_v1 detected; building Remotion 2-layer visual")
        try:
            import subprocess as _sp
            _brain_input_path = os.path.join(out_dir, "brain_input.json")
            if not os.path.exists(_brain_input_path) and isinstance(brain, dict):
                with open(_brain_input_path, "w", encoding="utf-8") as _bf:
                    json.dump(brain, _bf, ensure_ascii=False, indent=2)
            _images_dir = os.path.join(out_dir, "images")
            _manifest_path = os.path.join(_images_dir, "manifest.json")
            _props_path = os.path.join(out_dir, "remotion_props.json")
            _silent_path = os.path.join(out_dir, "twolayer_silent.mp4")
            _sp.run([sys.executable, "/root/video_factory/scripts/pull_approved_images.py",
                     "--episode-id", episode_id, "--out-dir", _images_dir,
                     "--statuses", "Approved,Pulled by VPS"],
                    check=True, timeout=180)
            _segments_path = os.path.join(out_dir, "whisper_segments.json")
            if "segments" in episode:
                with open(_segments_path, "w", encoding="utf-8") as _sf:
                    json.dump(episode["segments"], _sf)

            _sp.run([sys.executable, "/root/video_factory/scripts/build_remotion_props.py",
                     "--episode-id", episode_id, "--brain-input", _brain_input_path,
                     "--segments", _segments_path,
                     "--manifest", _manifest_path, "--out", _props_path, "--skip-missing"],
                    check=True, timeout=120)
            _sp.run([sys.executable, "/root/video_factory/scripts/render_twolayer_visual.py",
                     "--props", _props_path, "--out", _silent_path,
                     "--timeout", str(os.environ.get("VF_REMOTION_TIMEOUT", "1400"))],
                    check=True, timeout=1450)
            if os.path.exists(_silent_path) and os.path.getsize(_silent_path) > 0:
                twolayer_clip_path = _silent_path
                logger.info("[S4.5] two-layer silent visual ready: %s", _silent_path)
            else:
                raise RuntimeError("twolayer silent render produced no output file")
        except Exception as _e2l:
            raise

    # -- S4.6: Early coverage fail-fast (Enhance E, 06/08) ------------------
    # Root cause (EP004 29/07, EP005 06/08): the two-layer visual can end up
    # much shorter than the narration audio (stale/short scene durations vs a
    # longer/overridden story). The existing S7 gate in video_render.py
    # already blocks that combo, but only after S6 whisper-align has run
    # (10-15+ min of wasted GPU/CPU per attempt). Re-check the same coverage
    # ratio right here, on the cheap two-layer file, so a genuine mismatch
    # fails in seconds instead of burning S6+S7 compute first. Runs outside
    # the two-layer try/except above on purpose: a real coverage failure must
    # stop the episode, not be silently swallowed into a legacy-S5 fallback.
    if twolayer_clip_path:
        try:
            from app.services.mpt_ported.video_render import _probe_duration_or_none as _probe_dur
            _e_vdur = await _probe_dur(twolayer_clip_path)
            _e_adur = await _probe_dur(audio_path)
            if _e_vdur is not None and _e_adur is not None and _e_adur > 0:
                _e_cov = float(_e_vdur) / float(_e_adur)
                _e_min_cov = float(os.getenv("VF_MIN_VIDEO_COVERAGE", "0.97"))
                if _e_cov < _e_min_cov:
                    _e_msg = (
                        "[S4.5-coverage] video track %.1fs covers only %.1f%% of "
                        "the %.1fs narration; failing fast before S6/S7 (scene/"
                        "narration length mismatch -- would fail later at S7 "
                        "anyway after wasting whisper-align + render time)"
                        % (_e_vdur, _e_cov * 100.0, _e_adur))
                    logger.error(_e_msg)
                    try:
                        await tg.notify_error("S4.5 coverage (fail-fast)", episode_id, _e_msg)
                    except Exception as _swallowed:
                        logger.warning("[swallowed] run_episode S4.6: %s: %s", type(_swallowed).__name__, _swallowed)
                    if os.getenv("VF_BLOCK_SHORT_VIDEO", "1") not in ("0", "false", ""):
                        raise RuntimeError(_e_msg)
        except RuntimeError:
            raise
        except Exception as _e_probe_err:
            logger.warning("[S4.5-coverage] pre-check skipped (%s)", _e_probe_err)

    # -- S5: Stock visuals (driven by Notion visual_terms) -----------------
    if twolayer_clip_path:
        logger.info("[S5] skipped (two-layer visual already built)")
        episode["clips"] = [{"path": twolayer_clip_path, "source": "twolayer_remotion"}]
    else:
        logger.info("[S5] fetching stock clips for %d visual_terms...", len(vterms))
        if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
            try:
                await tg.notify_production("S5 · Visuals", episode_id)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 358, type(_swallowed).__name__, _swallowed)
        try:
            episode = await run_s5(episode)
        except Exception as e:
            logger.warning("[S5] failed: %s, continuing with empty clips", e)
            try:
                await tg.notify_error("S5 visuals (degraded)", episode_id, repr(e))
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 366, type(_swallowed).__name__, _swallowed)
            episode["clips"] = []
    clips = episode.get("clips", [])
    logger.info("[S5] got %d clips", len(clips))

    # -- S5 fallback: create color bg clip if no stock clips ---------------
    audio_size = episode.get("size_bytes", 60000)
    audio_duration = max(10.0, audio_size / 16000)  # rough est ~128kbps
    clip_paths = []
    for c in (clips or []):
        p = c.get("path") or c.get("url", "")
        if p and os.path.exists(str(p)):
            clip_paths.append(str(p))
    # FLOW FIX F4 27/07/2026: fail loudly instead of rendering a near-empty
    # video. VF_CLIP_GATE=off|warn|block (default block); VF_CLIP_GATE_RATIO.
    _n_scenes = len(episode.get("scenes") or [])
    _cgate = (os.getenv("VF_CLIP_GATE", "block") or "block").strip().lower()
    if _cgate not in ("off", "warn", "block"):
        _cgate = "block"
    if _n_scenes > 0 and _cgate != "off" and not twolayer_clip_path:
        try:
            _ratio = float(os.getenv("VF_CLIP_GATE_RATIO", "0.85"))
        except Exception:
            _ratio = 0.85
        _need = max(1, int(_n_scenes * _ratio))
        if len(clip_paths) < _need:
            _cmsg = "[S5-gate] only %d/%d clips (need >= %d)" % (len(clip_paths), _n_scenes, _need)
            logger.warning(_cmsg)
            try:
                await tg.notify_error("S5 clip gate", episode_id, _cmsg)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 397, type(_swallowed).__name__, _swallowed)
            if _cgate == "block":
                raise RuntimeError(_cmsg)
        else:
            logger.info("[S5-gate] ok %d/%d clips", len(clip_paths), _n_scenes)

    if not clip_paths:
        cache_clip = _pick_latest_stock_cache_clip()
        if cache_clip and os.path.exists(cache_clip):
            logger.info("[S5-cache] no clip_paths but found stock_cache clip: %s", cache_clip)
            clip_paths = [cache_clip]
            episode["clips"] = [{"path": cache_clip, "source": "stock_cache"}]

    if not clip_paths:
        logger.info("[S5-fallback] no valid clips, creating %ds color bg", int(audio_duration))
        fb_path = os.path.join(out_dir, "fallback_bg.mp4")
        await make_fallback_clip(fb_path, duration_s=audio_duration,
                                 aspect=os.environ.get("VF_IMAGE_ASPECT", "16:9"))
        clip_paths = [fb_path]
        episode["clips"] = [{"path": fb_path, "source": "fallback"}]
        # WIRE 07/08/2026 (Rule 70 muc 5): this solid-color background is a
        # genuine simulated/placeholder video asset (no real AI/stock clip
        # was available) -- mark it so S6/S7's assert_not_simulated gates
        # block it before it reaches final render/publish silently.
        mark_simulated(fb_path, "no valid stock/AI clips available for this episode", "s5_fallback")
        logger.info("[S5-fallback] bg clip: %s", fb_path)
    # -- inject clip_paths for S7 ------------------------------------------
    episode["clips"] = [{"path": p} for p in clip_paths]

    # -- S7: Render --------------------------------------------------------
    logger.info("[S7] rendering video...")
    if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
        try:
            await tg.notify_production("S7 · Render", episode_id)
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 449, type(_swallowed).__name__, _swallowed)
    try:
        episode = await run_s7(episode)
    except Exception as _e:
        try:
            await tg.notify_error("S7 render", episode_id, repr(_e))
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 456, type(_swallowed).__name__, _swallowed)
        raise

    # -- S7.5: SEO multi-platform payloads (FREE, deterministic) -----------
    try:
        from app.services.seo_metadata import write_seo_payloads
        if not episode.get("chapters"):
            try:
                with open(os.path.join(out_dir, "story_gate.json")) as _gf:
                    _gate = json.load(_gf)
                episode["chapters"] = (_gate.get("chapters") or {}).get("chapters", [])
            except Exception:
                episode["chapters"] = []
        episode.setdefault("episode_id", episode_id)
        episode.setdefault("niche", niche)
        episode.setdefault("lang_code", lang_code)
        episode["hook_3s"] = hook_3s
        episode["trend_keywords"] = trend_keywords or vterms
        episode["visual_terms"] = vterms
        episode["art_style"] = astyle
        _seo = write_seo_payloads(episode, out_dir)
        episode["seo_payloads"] = _seo
        logger.info("[S7.5] SEO payloads built for %d platforms -> seo_payloads.json", len(_seo or {}))
    except Exception as _e:
        logger.warning("[S7.5] SEO payload build soft-failed: %s", _e)

    elapsed = time.time() - t0
    result = {
        "episode_id":  episode_id,
        "brain_mode":  brain_mode,
        "text_len":    len(text),
        "visual_terms_used": len(vterms),
        "mood":        mood,
        "art_style":   astyle.get("style_id"),
        "audio_path":  audio_path,
        "srt_path":    episode.get("srt_path"),
        "final_916":   episode.get("final_916"),
        "final_169":   episode.get("final_169"),
        "final_11":    episode.get("final_11"),
        "bgm_path":    episode.get("bgm_path"),
        "elapsed_s":   round(elapsed, 1),
        "clips_used":  len(clip_paths),
        "tts_backend": episode.get("backend", tts_backend),
        "seo_platforms": len(episode.get("seo_payloads") or {}),
    }
    # -- Telegram: episode done + cost + free draft link -------------------
    try:
        _u1 = _usage_summary() if _usage_summary else {}
        _spend1 = float((_u1 or {}).get("today_usd") or 0)
        _ep_cost = round(_spend1 - _spend0, 4)
    except Exception:
        _u1, _ep_cost = {}, None
    # FIX 27/07/2026: credit_gate does not exist on this host, so the block
    # above always yielded 0.0 and the READY card advertised "$0.00" after 73
    # paid Antigravity Google Image generations. Fall back to the local usage ledger.
    _cost_breakdown = {}
    try:
        from app.services import cost_ledger as _cl
        _cost_breakdown = _cl.breakdown_between(t0)
        _led_cost = _cl.cost_between(t0, episode_id=episode_id)
        if _led_cost is not None and (not _ep_cost or _led_cost > _ep_cost):
            _ep_cost = _led_cost
        logger.info("[COST] episode=%s usd=%s breakdown=%s",
                    episode_id, _ep_cost, _cost_breakdown)
    except Exception as _ec:
        logger.warning("[COST] ledger unavailable: %s", _ec)
    _final = result.get("final_169") or result.get("final_916") or result.get("final_11")
    try:
        await tg.notify_episode_done(episode_id, _final, _ep_cost,
                                     breakdown=_cost_breakdown)
    except Exception as _swallowed:
        logger.warning("[swallowed] run_episode L%d: %s: %s", 527, type(_swallowed).__name__, _swallowed)
    try:
        if (_u1 or {}).get("monthly_pct", 0) >= 80:
            await tg.notify_budget_alert("ALL", _u1.get("today_usd", 0), _u1.get("daily_cap_usd", 0), _u1.get("month_usd", 0), _u1.get("monthly_cap_usd", 0))
    except Exception as _swallowed:
        logger.warning("[swallowed] run_episode L%d: %s: %s", 532, type(_swallowed).__name__, _swallowed)
    logger.info("[PIPELINE] DONE in %.1fs %s", elapsed, result)
    return result
