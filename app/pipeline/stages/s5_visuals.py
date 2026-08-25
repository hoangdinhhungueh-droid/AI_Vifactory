"""S5 Visuals — per-scene clip generation with render_type dispatch.

Per-scene render_type (from brain_input.json scenes[*].render_type):
  'ai_video'        -> image-first FREE Ken Burns (character-consistent via prompt;
                       Kie Veo paid I2V removed 03/07, Decisions Log Moc 1 Item 1.13)
  'ken_burns_image' -> Antigravity Google Image still -> Ken Burns zoompan (no Veo, no PEXELS key needed)
  'text_card'       -> ffmpeg drawtext black card (uses scene.text or scene.image_prompt)
  (default)         -> documentary montage (Pexels/Pixabay) -> Antigravity Google Image_kenburns fallback

Antigravity Google Image+Ken Burns fallback path: when documentary montage returns 0 clips (no API keys),
auto-generate a Antigravity Google Image still per scene + Ken Burns animate. The video will loop to fill
the full audio duration (video_render.py -stream_loop -1 handles this).

NOTE (03/07): Kie.ai Veo (paid image-to-video) and Credit Gate were removed from the
real Visual Engine per CONTENT SPEC v1.1 (FREE-only, no paid video AI). 'ai_video'
scenes now render via the same free image + Ken Burns pipeline as 'ken_burns_image',
seeded with the locked character reference image for prompt continuity.

env toggles: S5_AI_ENABLED, KIE_VEO_MAX_SEC_PER_EP, KIE_VEO_DURATION, KIE_VEO_ASPECT,
             S5_AI_MAX_CLIPS, S5_DOC_MONTAGE, S5_MONTAGE_PER_SCENE,
             S5_KENBURNS, S5_KENBURNS_SEC, VF_CHARREF_LOCK
"""
import asyncio
import logging
import os

from app.services.mpt_ported.state import idempotent_stage
from app.services.mpt_ported.stock_fetcher import fetch_stock_clip

from app.services import character_refs as _cref
from app.services import telegram_notify as _tg
from app.services.mpt_ported import documentary_montage as _docm
from app.services.mpt_ported import remotion_overlay as _remo
from app.services.simulated_asset_gate import assert_not_simulated

logger = logging.getLogger(__name__)

MAX_CLIPS = int(os.environ.get("S5_MAX_CLIPS", "200"))   # max total clips per episode (env-tunable; was hard 14)
AI_ASPECT = os.environ.get("VF_IMAGE_ASPECT", os.environ.get("KIE_VEO_ASPECT", "16:9"))
KB_CACHE = "/tmp/vf/kb_cache"


def _ai_enabled() -> bool:
    return os.environ.get("S5_AI_ENABLED", "1") not in ("0", "false", "False", "")


def _style_prompt(episode: dict) -> str:
    """Reusable art-style descriptor (brain-authored) prepended to every AI image."""
    art = (episode.get("art_style")
           or episode.get("brain_input", {}).get("art_style")
           or {})
    if isinstance(art, dict):
        return (art.get("style_prompt") or art.get("style") or art.get("style_id") or "").strip()
    if isinstance(art, str):
        return art.strip()
    return ""


def _ai_clip_budget() -> int:
    """How many character clips fit in the per-episode AI-clip budget.

    NOTE: env names kept as KIE_VEO_* for backward compat with existing .env
    (Kie Veo itself was removed 03/07); they now just budget the free
    image + Ken Burns character-clip count.
    """
    override = os.environ.get("S5_AI_MAX_CLIPS")
    if override:
        try:
            return max(0, int(override))
        except ValueError:
            pass
    max_sec = int(os.environ.get("KIE_VEO_MAX_SEC_PER_EP", "40"))
    dur = max(1, int(os.environ.get("KIE_VEO_DURATION", "8")))
    return max(0, max_sec // dur)


def _scenes_from_episode(episode: dict) -> list:
    """Normalize per-scene dict from brain output. Preserves render_type, text fields."""
    scenes = (episode.get("scenes")
              or episode.get("brain_input", {}).get("scenes")
              or [])
    norm = []
    for s in scenes:
        if isinstance(s, dict):
            ip = s.get("image_prompt") or s.get("prompt") or s.get("term") or ""
            mp = s.get("motion_prompt") or s.get("motion") or ip
            if ip or mp:
                norm.append({
                    "image_prompt": ip or mp,
                    "motion_prompt": mp or ip,
                    "render_type": s.get("render_type", ""),
                    "is_hero_reference": bool(s.get("is_hero_reference", False)),
                    "reuse_of": str(s.get("reuse_of", "") or "").strip(),
                    "remotion": (s.get("remotion")
                                 if isinstance(s.get("remotion"), dict) else None),
                    "text": s.get("text", "") or s.get("title", ""),
                    "visual_subject_type": s.get("visual_subject_type", "A"),
                    "style_anchor_tail": s.get("style_anchor_tail", ""),
                })
    if norm:
        return norm
    # Fallback: derive scenes from S4 visual_terms.
    terms = episode.get("visual_terms", []) or []
    return [{"image_prompt": t, "motion_prompt": t, "render_type": "", "text": ""}
            for t in terms]


async def _gen_ai_clip(*args, **kwargs):
    raise RuntimeError("Rule 120 Violation")

async def _antigravity_kenburns_clip(*args, **kwargs):
    raise RuntimeError("Rule 120 Violation: VPS Visual Engine is OFF. Cannot generate image on VPS.")


async def _text_card_clip(
    scene: dict,
    episode_id: str,
    idx: int,
    aspect: str,
) -> dict | None:
    """Generate a plain text card clip (black bg + white centered text) via ffmpeg.

    Uses scene.text if set, otherwise scene.image_prompt (truncated to 60 chars).
    Duration: S5_KENBURNS_SEC (default 5s). aspect sizes: 9:16=1080x1920, 16:9=1920x1080.
    """
    text = (scene.get("text") or scene.get("image_prompt") or "Key number").strip()
    # Truncate long prompts; escape ffmpeg drawtext special chars.
    text = text[:60].replace("'", "").replace(":", "-").replace("\\", "")
    sizes = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
    w, h = sizes.get(aspect, sizes.get(AI_ASPECT, (1920, 1080)))
    dur = float(os.environ.get("S5_KENBURNS_SEC", "5"))
    os.makedirs(KB_CACHE, exist_ok=True)
    out_path = os.path.join(KB_CACHE, f"{episode_id}_card_{idx:03d}.mp4")
    vf = (
        f"drawtext=text='{text}':fontcolor=white:fontsize=56:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=16:"
        f"box=1:boxcolor=black@0.0:boxborderw=0"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=30",
        "-vf", vf,
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-an", out_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(err.decode()[-160:])
        return {
            "path": out_path,
            "local_path": out_path,
            "source": "text_card",
            "image_prompt": text,
        }
    except Exception as e:
        logger.warning("[S5] text_card failed scene %d (%s): %s", idx, text, e)
    return None


@idempotent_stage("s5_visuals")
async def run_s5(episode: dict) -> dict:
    """Input: episode + scenes/visual_terms (from S4 + brain).
    Output: episode + {clips: [dict,...]} (each dict has url/path/source).

    render_type dispatch:
      ai_video        -> FREE image + Ken Burns (character-consistent via prompt;
                         Kie Veo removed 03/07, Item 1.13)
      ken_burns_image -> Antigravity Google Image still -> Ken Burns (no Veo, no external API needed)
      text_card       -> ffmpeg lavfi black card + drawtext (numbers/stats)
      (default)       -> documentary montage (Pexels/Pixabay) with Antigravity Google Image_kenburns fallback
    """
    episode_id = episode["episode_id"]
    lang_code = episode.get("lang_code", "en")
    # WIRE 07/08/2026 (Rule 70 muc 5): block a marked simulated/placeholder
    # audio track before spending clip-generation budget on it.
    _s5_audio_path = episode.get("audio_path")
    if _s5_audio_path:
        assert_not_simulated([_s5_audio_path])
    character_pack = (episode.get("character_pack")
                      or episode.get("brain_input", {}).get("character_pack", []))
    style = _style_prompt(episode)
    if style:
        logger.info("[S5] %s art-style prefix: %s...", episode_id, style[:48])

    scenes = _scenes_from_episode(episode)
    if not scenes:
        logger.warning("[S5] %s no scenes/visual_terms - using fallback", episode_id)
        scenes = [{"image_prompt": t, "motion_prompt": t, "render_type": "", "text": ""}
                  for t in ("cinematic landscape", "dramatic sky", "epic scene")]
    scenes = scenes[:MAX_CLIPS]

    # FIX 29/07/2026: adaptive scene duration. Scenes used to be a fixed
    # 5s each, so N scenes never added up to the real narration length
    # and S7 looped the video. Size each scene from the actual audio.
    if os.environ.get('VF_ADAPTIVE_SCENE_DUR', '1') not in ('0', 'false', ''):
        try:
            import subprocess as _sp
            _ap = episode.get('audio_path') or ''
            if _ap and os.path.exists(str(_ap)) and scenes:
                _out = _sp.run(['ffprobe', '-v', 'error', '-show_entries',
                                'format=duration', '-of',
                                'default=nw=1:nk=1', str(_ap)],
                               capture_output=True, text=True).stdout.strip()
                _adur = float(_out)
                _n = len(scenes)
                _xf = float(os.environ.get('VF_XFADE_SEC', '0.5'))
                # every adjacent boundary loses one xfade overlap
                _per = (_adur + _xf * (_n + 1)) / float(_n)
                _per = max(2.5, min(12.0, _per))
                os.environ['S5_KENBURNS_SEC'] = '%.3f' % _per
                logger.info('[S5] adaptive scene duration: audio %.1fs / '
                            '%d scenes -> %.2fs per scene', _adur, _n, _per)
        except Exception as _de:
            logger.warning('[S5] adaptive scene duration failed: %s', _de)

    clips = []
    ai_count = 0

    # ---- Phase 1: render_type-dispatched scenes (explicit override) ----
    # Scenes with render_type='ken_burns_image' or 'text_card' are handled here
    # immediately (no Veo, no Pexels needed). render_type='ai_video' is handled
    # in Phase 2 if character_pack is also present; otherwise falls through.
    explicit_idx = set()  # scene indices handled in this phase
    if _ai_enabled():
        for i, s in enumerate(scenes):
            rt = (s.get("render_type") or "").strip()
            if s.get("is_hero_reference"):
                await _tg.notify_production("S5 - Hero can duyet", episode_id, detail="Scene la hero-reference, vao Image Asset Library duyet anh.")
            if rt == "ken_burns_image":
                logger.info("[S5] scene %d render_type=ken_burns_image", i)
                clip = await _antigravity_kenburns_clip(s, episode_id, i, style, AI_ASPECT)
                if clip:
                    clips.append(clip)
                explicit_idx.add(i)
            elif rt == "text_card":
                logger.info("[S5] scene %d render_type=text_card", i)
                clip = await _text_card_clip(s, episode_id, i, AI_ASPECT)
                if clip:
                    clips.append(clip)
                explicit_idx.add(i)
            # rt='ai_video' or '' -> handled in phases 2+3

    remaining_scenes = [s for i, s in enumerate(scenes) if i not in explicit_idx]

    # ---- Phase 2: AI character clips (FREE image-first Ken Burns), bounded by budget ----
    if _ai_enabled() and character_pack and remaining_scenes:
        ai_max = min(_ai_clip_budget(), len(remaining_scenes))
        ai_scenes = remaining_scenes[:ai_max]
        ref_url = None
        ref_local_path = None
        if ai_scenes:
            _series_id = (episode.get("series_id")
                          or episode.get("brain_input", {}).get("series_id")
                          or episode_id)
            _prim = _cref.primary_character_name(character_pack)
            if _prim:
                _locked_rec = _cref.get_ref(_series_id, _prim)
                if _locked_rec and _locked_rec.get("locked") and _locked_rec.get("public_url"):
                    ref_url = _locked_rec["public_url"]
                    ref_local_path = _locked_rec.get("local_path")
                    logger.info("[S5] %s reusing LOCKED character ref for %r: %s",
                                episode_id, _prim, ref_url)
            if not ref_url:
                try:
                    ref = await gen_reference_image(character_pack, aspect=AI_ASPECT, extra=style)
                    ref_url = ref.get("public_url")
                    ref_local_path = ref.get("local_path")
                    if not ref_url:
                        logger.warning("[S5] %s reference image has no public_url", episode_id)
                    elif _prim:
                        try:
                            _do_lock = os.environ.get("VF_CHARREF_LOCK", "1") not in ("0", "false", "False", "")
                            _cref.save_ref(_series_id, _prim, public_url=ref_url,
                                           local_path=ref.get("local_path"),
                                           prompt=ref.get("prompt"), lock=_do_lock)
                            logger.info("[S5] %s saved%s character ref for %r",
                                        episode_id, " + LOCKED" if _do_lock else "", _prim)
                        except Exception as _e:
                            logger.warning("[S5] %s character ref persist failed: %s", episode_id, _e)
                except Exception as e:
                    logger.warning("[S5] %s reference image failed: %s", episode_id, e)

            # UPDATED 03/08/2026 (Decisions Log budget approval): pass the locked
            # Rule 46 Hero Reference LOCAL file (ref_local_path) as character_ref_image
            # so Foreground/character clips try gpt-image-2 PAID image-to-image first,
            # falling back to the FREE chain automatically if the file is missing/unavailable.
            if ref_local_path and not os.path.exists(str(ref_local_path)):
                logger.info("[S5] %s hero ref local_path missing on disk (%s) - gpt-image-2 skipped, FREE chain still used",
                            episode_id, ref_local_path)

            logger.info("[S5] %s generating %d AI clips (budget=%d)",
                        episode_id, len(ai_scenes), _ai_clip_budget())
            for i, sc in enumerate(ai_scenes):
                try:
                    clip = await _gen_ai_clip(sc, ref_url, episode_id, i, style=style, ref_local_path=ref_local_path)
                    if clip.get("path"):
                        clips.append(clip)
                        ai_count += 1
                    else:
                        raise RuntimeError("no local path for AI clip")
                except Exception as e:
                    term = sc.get("image_prompt", "")
                    logger.warning("[S5] AI clip failed for '%s' (%s) - KB fallback", term, e)
                    # Fallback: Antigravity Google Image+kenburns instead of stock (more reliable when no PEXELS key)
                    clip = await _antigravity_kenburns_clip(sc, episode_id, i, style, AI_ASPECT)
                    if clip:
                        clips.append(clip)
                    else:
                        try:
                            stock = await fetch_stock_clip(query=term, lang_code=lang_code, download=True)
                            if isinstance(stock, dict):
                                clips.append(stock)
                        except Exception as e2:
                            logger.warning("[S5] stock fallback also failed for '%s': %s", term, e2)
        remaining_for_stock = remaining_scenes[len(ai_scenes):]
    else:
        if not character_pack:
            logger.info("[S5] %s no character_pack - documentary montage path", episode_id)
        remaining_for_stock = remaining_scenes

    # ---- Phase 3 (FIX 27/07/2026): AI image-gen (Antigravity Google Image) FIRST for
    # non-character scenes. Root cause of repeated/mismatched imagery was
    # this phase defaulting to keyword-matched stock footage even though the
    # AI backend can generate an on-topic image for any prompt; stock and
    # documentary montage are now only a last-resort fallback if AI
    # generation itself fails or is disabled. ----
    if remaining_for_stock:
        if _ai_enabled():
            logger.info("[S5] %s AI image-gen (Antigravity Google Image) for %d non-character scenes",
                        episode_id, len(remaining_for_stock))
            for si, s in enumerate(remaining_for_stock):
                if len(clips) >= MAX_CLIPS:
                    break
                term = s.get("image_prompt", "")
                si_global = si  # local idx for cache naming
                clip = None
                try:
                    clip = await _antigravity_kenburns_clip(
                        s, episode_id, 1000 + si_global, style, AI_ASPECT)
                except Exception as e:
                    logger.warning("[S5] AI image-gen failed for scene %d (%s): %s", si_global, term[:40], e)
                if clip:
                    clips.append(clip)
                    ai_count += 1
                    continue
                try:
                    montage = None
                    if _docm.doc_montage_enabled():
                        montage = await _docm.build_scene_montage(
                            query=term, lang_code=lang_code, episode_id=episode_id,
                            scene_idx=si_global, aspect=AI_ASPECT)
                    if montage:
                        clips += montage[:max(1, MAX_CLIPS - len(clips))]
                    else:
                        stock = await fetch_stock_clip(
                            query=term, lang_code=lang_code, download=True)
                        if isinstance(stock, dict):
                            clips.append(stock)
                except Exception as e3:
                    logger.warning("[S5] all fallbacks failed for '%s': %s", term, e3)
        else:
            logger.info("[S5] %s AI disabled - documentary montage/stock for %d scenes",
                        episode_id, len(remaining_for_stock))
            if _docm.doc_montage_enabled() and not character_pack:
                for si, s in enumerate(remaining_for_stock):
                    if len(clips) >= MAX_CLIPS:
                        break
                    term = s.get("image_prompt", "")
                    try:
                        montage = await _docm.build_scene_montage(
                            query=term, lang_code=lang_code, episode_id=episode_id,
                            scene_idx=si, aspect=AI_ASPECT)
                        if montage:
                            clips += montage[:max(1, MAX_CLIPS - len(clips))]
                        else:
                            stock = await fetch_stock_clip(
                                query=term, lang_code=lang_code, download=True)
                            if isinstance(stock, dict):
                                clips.append(stock)
                    except Exception as e:
                        logger.warning("[S5] montage exception for scene %d (%s): %s", si, term, e)
            else:
                tasks = [
                    fetch_stock_clip(query=s.get("image_prompt", ""), lang_code=lang_code, download=True)
                    for s in remaining_for_stock
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                clips += [r for r in results if isinstance(r, dict)]

    # Ensure local file paths are used downstream.
    for c in clips:
        lp = c.get("local_path")
        if lp and os.path.exists(str(lp)):
            c["path"] = str(lp)

    logger.info("[S5] %s total %d clips (%d AI + %d stock/KB)",
                episode_id, len(clips), ai_count, len(clips) - ai_count)
    return {**episode, "clips": clips}

# ALREADY_PATCHED_VISUAL_SUBJECT_TYPE
