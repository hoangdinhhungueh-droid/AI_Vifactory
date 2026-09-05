"""S6 - Subtitle alignment (Whisper/Groq) + optional karaoke bake."""
import os, json, hashlib, logging
from app.services.mpt_ported.state import idempotent_stage
from app.services.mpt_ported.subtitle_align import align_subtitles
from app.services.mpt_ported.subtitle_karaoke import render_karaoke, check_reading_speed, resplit_for_cps
from app.services import telegram_notify as tg
from app.services.simulated_asset_gate import assert_not_simulated

logger = logging.getLogger(__name__)
# FLOW ENHANCE 27/07/2026: whisper alignment is ~57% of pipeline runtime
# and is a pure function of (audio bytes, lang) -> cache it by hash.
_ALIGN_CACHE_DIR = os.getenv("VF_ALIGN_CACHE_DIR", "/tmp/vf/align_cache")

@idempotent_stage("s6_subtitle")
async def run_s6(episode: dict) -> dict:
    """Input: episode + audio_path (S4)
    Output: episode + {segments, srt_path, subtitle_video_path?}"""
    episode_id = episode["episode_id"]
    audio_path = episode["audio_path"]
    lang_code  = episode.get("lang_code", "en")
    transcript = episode.get("transcript") or episode.get("text") or episode.get("story_text")
    if not transcript:
        ep_dir = os.path.join("/var/vf/episodes", episode_id)
        for fname in ["brain_input.json", "story.txt"]:
            fpath = os.path.join(ep_dir, fname)
            if os.path.exists(fpath):
                try:
                    if fname.endswith(".json"):
                        with open(fpath, encoding="utf-8") as _bf:
                            _b = json.load(_bf)
                            transcript = _b.get("story") or _b.get("story_text") or _b.get("text")
                    else:
                        with open(fpath, encoding="utf-8") as _bf:
                            transcript = _bf.read()
                    if transcript:
                        break
                except Exception:
                    pass
    out_dir    = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)
    srt_path   = os.path.join(out_dir, "subtitles.srt")

    # WIRE 07/08/2026 (Rule 70 muc 5): block a marked simulated/placeholder
    # audio track before spending whisper-align time on it.
    assert_not_simulated([audio_path])

    logger.info("[S6] %s aligning lang=%s", episode_id, lang_code)
    _cache_on = (os.getenv("VF_ALIGN_CACHE", "1") or "1").strip() == "1"
    _ck = None
    if _cache_on:
        try:
            _h = hashlib.sha1()
            with open(audio_path, "rb") as _af:
                while True:
                    _chunk = _af.read(1048576)
                    if not _chunk:
                        break
                    _h.update(_chunk)
            _h.update(("|" + str(lang_code)).encode())
            os.makedirs(_ALIGN_CACHE_DIR, exist_ok=True)
            _ck = os.path.join(_ALIGN_CACHE_DIR, _h.hexdigest() + ".json")
        except Exception as _e:
            logger.warning("[S6] align cache key failed: %s", _e)
            _ck = None
    segments = None
    if _ck and os.path.exists(_ck):
        try:
            with open(_ck) as _cf:
                segments = json.load(_cf)
            logger.info("[S6] %s align cache HIT %s (%d segments)", episode_id,
                        os.path.basename(_ck), len(segments))
        except Exception as _e:
            logger.warning("[S6] align cache read failed: %s", _e)
            segments = None
    _seg_file = os.path.join(out_dir, "whisper_segments.json")
    if not segments and os.path.exists(_seg_file) and os.path.getsize(_seg_file) > 1000:
        try:
            with open(_seg_file) as _sf:
                segments = json.load(_sf)
            logger.info("[S6] %s using existing whisper_segments.json (%d segments)", episode_id, len(segments))
        except Exception as _e:
            segments = None
    if not segments:
        segments = await align_subtitles(
            audio_path=audio_path,
            transcript=transcript,
            lang_code=lang_code,
            backend="auto",
        )
        if _ck:
            try:
                with open(_ck, "w") as _cf:
                    json.dump(segments, _cf)
                logger.info("[S6] %s align cache STORE %s", episode_id,
                            os.path.basename(_ck))
            except Exception as _e:
                logger.warning("[S6] align cache write failed: %s", _e)
    logger.info("[S6] %s got %d segments", episode_id, len(segments))
    # SCENE-BOUNDARY GUARD 27/07/2026: tell the CPS linger pass how long
    # one still image lasts so a cue never bleeds into the next image.
    scene_len_ms = None
    try:
        _n_sc = len(episode.get('scenes') or [])
        _end_ms = max((sg.get('end_ms') or 0) for sg in segments) if segments else 0
        if _n_sc > 0 and _end_ms > 0:
            scene_len_ms = int(_end_ms / _n_sc)
            logging.getLogger(__name__).info(
                '[S6] scene boundary guard: %d scenes, scene_len=%dms', _n_sc, scene_len_ms)
    except Exception as _e:
        logging.getLogger(__name__).warning('[S6] scene_len_ms calc failed: %s', _e)
        scene_len_ms = None
    segments = resplit_for_cps(segments, scene_len_ms=scene_len_ms)
    logger.info("[S6] %s %d segments after CPS auto-split", episode_id, len(segments))
    speed_warnings = check_reading_speed(segments)
    if speed_warnings:
        logger.warning("[S6] %s %d segment(s) over CPS cap: %s", episode_id, len(speed_warnings), speed_warnings[:3])
        try:
            await tg.notify_production(
                "QUALITY_WARN", episode_id,
                detail=f"Subtitle reading speed: {len(speed_warnings)} segment(s) over CPS cap (script may read too fast)",
            )
        except Exception:
            logger.exception("[S6] %s speed-warning notify failed", episode_id)

    with open(srt_path, "w") as fout:
        for i, seg in enumerate(segments, 1):
            s_ms = int(seg.get("start_ms", seg.get("start", 0) * 1000))
            e_ms = int(seg.get("end_ms", seg.get("end", 0) * 1000))
            def ts(ms):
                h, r = divmod(ms, 3600000)
                m, r = divmod(r, 60000)
                s2, ms2 = divmod(r, 1000)
                return "%02d:%02d:%02d,%03d" % (h, m, s2, ms2)
            fout.write("%d\n%s --> %s\n%s\n\n" % (i, ts(s_ms), ts(e_ms), seg.get("text", "")))

    result = {**episode, "segments": segments, "srt_path": srt_path}
    result["subtitle_speed_warnings"] = speed_warnings

    # Optional: bake karaoke if video_path already exists
    video_path = episode.get("video_path")
    if video_path and os.path.exists(video_path):
        karo_path = os.path.join(out_dir, "video_karaoke.mp4")
        logger.info("[S6] %s baking karaoke", episode_id)
        karo_out = render_karaoke(
            video_path=video_path,
            segments=segments,
            output_path=karo_path,
            lang_code=lang_code,
        )
        result["subtitle_video_path"] = karo_out

    return result
