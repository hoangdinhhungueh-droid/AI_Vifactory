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
    into the story field and it reached TTS unfiltered. This interceptor
    is cheap, deterministic, and runs in all paths, so both the ad-hoc
    seed-script path and the normal B1/trend pipeline path get the same
    scrubbing.

    Regex pattern: [ ... ] with 0-600 chars inside (no nested brackets).
    """
    return _PIPELINE_META_NOTE_RE.sub("", text).strip()


async def run_pipeline(
    *,
    episode_id: str,
    niche: str,
    lang_code: str = "en",
    tts_backend: str = "auto",
    story_text: str = "",
    visual_terms: list | None = None,
    bgm_mood: str = "epic",
    hook_3s: str = "",
    scenes: list | None = None,
    character_pack: dict | None = None,
    art_style: dict | None = None,
    trend_keywords: list | None = None,
    brain: dict | None = None,
    skip_story_gate: bool = False,
):
    """
    Full pipeline runner (S2 -> S3 -> S4 -> S5 -> S6 -> S7).

    Args (Brain mode):
      episode_id: unique ID for this episode
      niche:      content category (history / relationship story / ...)
      lang_code:  target language (en, vi, ...) - forwarded to TTS + subtitle
      tts_backend: "azure" | "elevenlabs" | "auto"
      story_text: narrator script (from Notion or caller)
      visual_terms: list of search keywords for stock visuals
      bgm_mood:   mood for BGM (epic, calm, dark, ...)
      hook_3s:    short hook text for social cards
      scenes:     list of {scene_num, image_prompt, scene_text, duration_s, ...}
      character_pack: {char_id, names, visual_identity, ...}
      art_style:  {style_id, prompt_suffix, ...}
      trend_keywords: list of trend/SEO keywords
      brain:      raw brain_input dict (contains all of the above + more)

    Returns:
      dict with final_916, final_169, final_11, audio_path, srt_path, ...
    """
    t0 = time.time()
    out_dir = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)

    # BUG FIX 01/09/2026 (Issue #5): Initialize clip_paths early to prevent
    # UnboundLocalError when S4.5 coverage check raises RuntimeError before
    # S5 runs. Line 463 will reassign this during normal S5 execution.
    clip_paths = []

    # -- Usage baseline (if credit_gate is available) -----------------------
    try:
        _u0 = _usage_summary() if _usage_summary else {}
        _spend0 = float((_u0 or {}).get("today_usd") or 0)
    except Exception:
        _u0, _spend0 = {}, 0.0

    # -- Load/construct brain -----------------------------------------------
    _brain = brain or {}
    brain_mode = "notion" if story_text else "legacy"

    # -- Require brain (VF_REQUIRE_BRAIN=1 default) -------------------------
    if not story_text:
        if os.getenv("VF_REQUIRE_BRAIN", "1") == "1":
            raise ValueError(
                "[PIPELINE] VF_REQUIRE_BRAIN=1 but no story_text supplied; "
                "refusing to self-generate random content (Notion is the brain)")
        logger.warning("[PIPELINE] No story_text; falling back to legacy self-gen")

    # -- S2: Story generation (ONLY if no story_text supplied) --------------
    if not story_text:
        logger.info("[S2] no story_text; generating from LLM (legacy)")
        prompt = STORY_PROMPT.format(niche=niche)
        text = _call_llm(prompt)
        if not text or len(text) < 20:
            logger.warning("[S2] LLM story empty/too short, using fallback")
            text = FALLBACK_STORY
    else:
        logger.info("[S2] using supplied story_text (%d chars)", len(story_text))
        text = story_text

    # ADDED 08/08/2026 - strip bracketed editorial meta-notes (Rule 75.5).
    text = _strip_pipeline_meta_notes(text)
    logger.info("[S2.5] stripped meta-notes; final text %d chars", len(text))

    # -- S3: Scene schema validation ----------------------------------------
    if not scenes:
        logger.info("[S3] no scenes supplied; skipping schema validation")
        scenes = []
    else:
        logger.info("[S3] %d scenes from brain", len(scenes))

    vterms = visual_terms or []
    if not vterms and scenes:
        vterms = [" ".join(s.get("image_prompt", "").split()[:6]) for s in scenes[:8]]
        logger.info("[S3] extracted %d visual_terms from scenes", len(vterms))

    astyle = art_style or {}
    mood = bgm_mood or "epic"
    trend_keywords = trend_keywords or []

    episode = {
        "episode_id": episode_id,
        "niche": niche,
        "lang_code": lang_code,
        "text": text,
        "transcript": text,  # Standardized contract for S6 Subtitles
        "visual_terms": vterms,
        "mood": mood,
        "hook_3s": hook_3s,
        "scenes": scenes,
        "character_pack": character_pack,
        "art_style": astyle,
        "trend_keywords": trend_keywords,
        "brain_mode": brain_mode,
    }

    # S3 schema validation (must run after episode dict is built)
    episode = validate_s3_output(episode)
    # -- S3.5: Story quality + chapters (outline stage, 5 scoring axes) -----
    # FLOW ENHANCE 27/07/2026 - runs BEFORE TTS so a weak script is caught
    # while it is still cheap to rewrite. VF_QUAL_GATE=0 to disable hard block.
    try:
        qa = _sq.score_story(story_text=text, hook_3s=hook_3s, trend_keywords=trend_keywords, character_pack=character_pack)
        episode["quality"] = qa
        _ch = {}
        if qa.get("passed") or skip_story_gate:
            _ch = _cs.split_chapters(text, episode_id=episode_id)
            episode["chapters"] = _ch.get("chapters", [])
        try:
            with open(os.path.join(out_dir, "quality_gate.json"), "w") as _f:
                json.dump({"quality": qa, "chapters": _ch}, _f, indent=2)
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 263, type(_swallowed).__name__, _swallowed)
        logger.info("[S3.5] quality=%.2f passed=%s (skip_story_gate=%s) n_chapters=%d total_s=%.1f",
                    qa.get("quality_score", 0), qa.get("passed"), skip_story_gate,
                    _ch.get("n_chapters", 0), _ch.get("total_duration_s", 0))
        if not qa.get("passed") and not skip_story_gate:
            _qmsg = (f"score={qa.get('quality_score')} blocking={qa.get('blocking')}\n"
                     f"⛔ Pipeline STOPPED (S3.5). Fix the script in Notion, then re-run this episode.")
            try:
                await tg.notify_error("S3.5 QUALITY GATE FAILED", episode_id, _qmsg)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 272, type(_swallowed).__name__, _swallowed)
            # FIX 27/07/2026: default flipped to hard-block. A failing script
            # must never continue burning TTS/render budget; go fix it in
            # Notion first. Set VF_QUAL_GATE=0 only for an explicit override.
            if os.getenv("VF_QUAL_GATE", "1") != "0":
                raise RuntimeError(f"Story quality gate FAILED: {qa.get('blocking')}")
        elif not qa.get("passed") and skip_story_gate:
            logger.info("[S3.5] Story quality gate bypassed via skip_story_gate=True (previously approved at B3.5)")
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
        if _sg_mode != "off" and not skip_story_gate:
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
        _sj_mode = "off"  # DECOMMISSIONED: Handled by GPT-6-Astra via HHTech SoT
        if _sj_mode != "off" and not skip_story_gate:
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
        _tts_voice = (_brain or {}).get("tts_voice")
    except Exception:
        _tts_voice = None
    try:
        # Fix: S4 expects backend/voice inside episode dict, not as kwargs
        episode["backend"] = tts_backend
        if _tts_voice:
            episode["voice"] = _tts_voice
        episode = await run_s4(episode)
    except Exception as _e:
        try:
            await tg.notify_error("S4 TTS", episode_id, repr(_e))
        except Exception as _swallowed:
            logger.warning("[swallowed] run_episode L%d: %s: %s", 332, type(_swallowed).__name__, _swallowed)
        raise
    audio_path = episode["audio_path"]
    logger.info("[S4] audio ready: %s", audio_path)

    # -- S4.5: Two-layer Remotion render (additive; opt-in via brain_input.json
    # render_architecture == "two_layer_v1"). Builds a silent Background+
    # Foreground visual from Notion-approved images (Image Asset Library,
    # Status=Approved) and uses it AS the clip, skipping the legacy
    # stock-clip fetch below. Any failure falls back to legacy S5 unchanged.
    twolayer_clip_path = None
    _render_arch = str((brain or {}).get("render_architecture") or "").strip()
    if not _render_arch:
        _render_arch = str(episode.get("render_architecture") or "").strip()
    if not _render_arch:
        if (
            (brain or {}).get("mode") == "remotion"
            or os.path.exists(os.path.join(out_dir, "remotion_props.json"))
            or os.path.exists(os.path.join(out_dir, "images_ready.json"))
            or os.path.exists(os.path.join(out_dir, "prompts_forge.json"))
            or os.path.exists(os.path.join(out_dir, "vox_scene_manifest.json"))
        ):
            _render_arch = "remotion_twolayer_karaoke_v4"
            logger.info("[S4.5] auto-detected render_architecture=%s from episode artifacts", _render_arch)
    if _render_arch:
        episode["render_architecture"] = _render_arch
    is_two_layer = _render_arch in ("two_layer_v1", "remotion_twolayer_karaoke_v4") or "twolayer" in _render_arch or _render_arch.startswith("two_layer")
    if is_two_layer:
        logger.info("[S4.5] two_layer_v1 detected; ensuring S6 Whisper transcription is ready for Remotion props")
        # Ensure speech narration (S4 completed) and Faster-Whisper transcription (S6)
        # run before Remotion prop generation & render (S4.5/S7) so exact word timestamps are available.
        if "segments" not in episode or not episode.get("segments"):
            logger.info("[S4.4] Pre-computing S6 subtitle alignment for two_layer_v1 Remotion synchronization")
            episode["transcript"] = text
            if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
                try:
                    await tg.notify_production("S6 · Subtitles (Pre-Remotion)", episode_id)
                except Exception as _swallowed:
                    logger.warning("[swallowed] run_episode S4.4 notify: %s", _swallowed)
            try:
                episode = await run_s6(episode)
            except Exception as _e_s6:
                try:
                    await tg.notify_error("S6 subtitle (Pre-Remotion)", episode_id, repr(_e_s6))
                except Exception as _swallowed:
                    logger.warning("[swallowed] run_episode L%d: %s: %s", 365, type(_swallowed).__name__, _swallowed)
                raise

        logger.info("[S4.5] building Remotion 2-layer visual")
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
                    check=True, timeout=180, cwd="/root/video_factory")
            _segments_path = os.path.join(out_dir, "whisper_segments.json")
            if "segments" in episode and episode.get("segments"):
                with open(_segments_path, "w", encoding="utf-8") as _sf:
                    json.dump(episode["segments"], _sf, ensure_ascii=False, indent=2)

            _build_props_script = "/root/video_factory/app/services/build_remotion_props.py"
            if not os.path.exists(_build_props_script):
                _build_props_script = "/root/video_factory/scripts/build_remotion_props.py"
            _sp.run([sys.executable, _build_props_script,
                     "--episode-id", episode_id, "--brain-input", _brain_input_path,
                     "--segments", _segments_path,
                     "--manifest", _manifest_path, "--out", _props_path, "--skip-missing"],
                    check=True, timeout=600)

            # Stage B6.2: Autonomous Adversarial Director Gate (VOX minimalism, Rule 122 & 136)
            _gate_script = "/root/video_factory/scripts/orchestrator/adversarial_director_gate.py"
            if os.path.exists(_gate_script):
                logger.info("[S4.5] running adversarial_director_gate on props")
                _sp.run([sys.executable, _gate_script,
                         "--episode-id", episode_id,
                         "--props", _props_path,
                         "--no-stills"], check=False, timeout=120)

            from app.services.render_timeout_policy import (
                compute_render_timeout_hierarchy,
                extract_frames_from_props,
            )
            _calc_frames = extract_frames_from_props(_props_path, default_frames=18000)
            _hierarchy = compute_render_timeout_hierarchy(
                _calc_frames,
                base_timeout=float(os.environ.get("VF_REMOTION_TIMEOUT", "36000"))
            )
            _dynamic_rem_timeout = int(_hierarchy["remotion_timeout"])
            _subproc_timeout = int(_hierarchy["run_episode_timeout"])
            logger.info("[S4.5] launching render_twolayer_chunks with dynamic timeout=%ds (frames=%d, subproc_timeout=%ds)",
                        _dynamic_rem_timeout, _calc_frames, _subproc_timeout)
            _sp.run([sys.executable, "/root/video_factory/scripts/render_twolayer_chunks.py",
                 "--episode-id", episode_id,
                 "--props", _props_path, "--out", _silent_path,
                 "--skip-auto-mux"],
                check=True, timeout=_subproc_timeout)
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
    # GAP-4 FIX (31/08/2026): Skip S5 entirely for two_layer_v1 / remotion_twolayer_karaoke_v4 architecture.
    # S4.5 already validated images during Notion pull; S5 validation is
    # redundant and may fail if S4.5 wrote to a different path than S5 expects.
    if is_two_layer:
        logger.info("[S5] skipped (two-layer visual %s - images validated during S4.5 Notion pull)", _render_arch)
        # S4.5 already pulled and validated images from Notion; set clips to
        # the twolayer output so S7 uses it as the master visual.
        if twolayer_clip_path:
            episode["clips"] = [{"path": twolayer_clip_path, "source": "twolayer_remotion"}]
        else:
            # S4.5 failed but we're in two-layer mode - should have already
            # raised above. If we reach here, set empty clips (S7 will fail).
            episode["clips"] = []
    else:
        logger.info("[S5] fetching stock clips for %d visual_terms... (legacy mode)", len(vterms))
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
    if _n_scenes > 0 and _cgate != "off" and not is_two_layer:
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
                    await tg.notify_error("S3.7 PREFLIGHT GATE BLOCKED", episode_id, _pfmsg)
                except Exception as _swallowed:
                    logger.warning("[swallowed] run_episode L%d: %s: %s", 3701, type(_swallowed).__name__, _swallowed)
                if _pf_mode == "block":
                    raise RuntimeError("Preflight render gate BLOCKED: " + _pfmsg)
    except RuntimeError:
        raise
    except Exception as _e37:
        logger.warning("[S3.7] preflight gate soft-failed: %s", _e37)

    # -- S6: Subtitle generation --------------------------------------------
    logger.info("[S6] generating subtitles...")
    episode["transcript"] = text  # Standardized trigger contract
    if "segments" in episode and episode.get("segments"):
        logger.info("[S6] Subtitles already generated pre-Remotion (exact word timestamps preserved)")
    else:
        if os.getenv("VF_STAGE_NOTIFY", "1") == "1":
            try:
                await tg.notify_production("S6 · Subtitles", episode_id)
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 625, type(_swallowed).__name__, _swallowed)
        try:
            episode = await run_s6(episode)
        except Exception as _e:
            try:
                await tg.notify_error("S6 subtitle", episode_id, repr(_e))
            except Exception as _swallowed:
                logger.warning("[swallowed] run_episode L%d: %s: %s", 632, type(_swallowed).__name__, _swallowed)
            raise

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
                with open(os.path.join(out_dir, "quality_gate.json")) as _gf:
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
    # -- Telegram: episode done + cost reporting (passive telemetry, no budget cap) ----
    _cost_breakdown = {}
    _ep_cost = None
    _monthly_vnd = 0.0
    _model_report = {}
    try:
        from app.services.cost_tracker import get_global_tracker
        _tracker = get_global_tracker()
        _monthly_vnd = _tracker.get_monthly_total()
        _model_report = _tracker.monthly_report()
    except Exception as _tr_err:
        logger.warning("[COST] CostTracker unavailable: %s", _tr_err)

    try:
        from app.services import cost_ledger as _cl
        _cost_breakdown = _cl.breakdown_between(t0)
        _ep_cost = _cl.cost_between(t0, episode_id=episode_id)
    except Exception as _ec:
        logger.warning("[COST] ledger unavailable: %s", _ec)

    logger.info("[COST] episode=%s usd=%s monthly_vnd=%s breakdown=%s",
                episode_id, _ep_cost, _monthly_vnd, _cost_breakdown)

    _final = result.get("final_169") or result.get("final_916") or result.get("final_11")
    try:
        await tg.notify_episode_done(episode_id, _final, _ep_cost,
                                     breakdown=_cost_breakdown)
    except Exception as _swallowed:
        logger.warning("[swallowed] run_episode L%d: %s: %s", 527, type(_swallowed).__name__, _swallowed)

    logger.info("[PIPELINE] DONE in %.1fs %s", elapsed, result)
    return result
