"""S7 - Final render: concat clips + normalize audio + BGM mix."""
import os, logging
from app.services.mpt_ported.state import idempotent_stage
from app.services.mpt_ported.video_render import render_video, derive_aspect_blurpad, burn_subtitles_for_aspect
from app.services.mpt_ported.audio_normalize import normalize_audio
from app.services.mpt_ported.bgm_selector import select_bgm
from app.services.mpt_ported.motion_cards import build_cards
from app.services.mpt_ported.render_gate import pre_render_check, post_render_check
from app.services.mpt_ported.subtitle_karaoke import burn_karaoke_for_aspect, karaoke_enabled
from app.services.simulated_asset_gate import assert_not_simulated

logger = logging.getLogger(__name__)

def _extract_clip_paths(clips: list) -> list:
    """Convert list of str or dict to list of str paths."""
    paths = []
    for c in (clips or []):
        if isinstance(c, str):
            paths.append(c)
        elif isinstance(c, dict):
            p = c.get("path") or c.get("url", "")
            if p and os.path.exists(str(p)):
                paths.append(str(p))
    return paths

@idempotent_stage("s7_render")
async def run_s7(episode: dict) -> dict:
    """Input: episode + audio_path(S4) + clips(S5) + segments(S6)
    Output: episode + {final_916, final_169, final_11, bgm_path, lufs_report}"""
    episode_id = episode["episode_id"]
    audio_path = episode["audio_path"]
    clips      = episode.get("clips", [])
    segments   = episode.get("segments", [])
    lang_code  = episode.get("lang_code", "en")
    mood       = episode.get("mood", "calm")
    out_dir    = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)

    # Convert clip dicts -> string paths
    clip_paths = _extract_clip_paths(clips)
    if not clip_paths:
        raise ValueError(f"[S7] No valid clip paths in episode.clips: {clips}")

    # WIRE 07/08/2026 (Rule 70 muc 5): never let a marked simulated/placeholder
    # asset (audio or video clip) reach final mux/publish silently. This is
    # the primary hard gate call site named in simulated_asset_gate.py's own
    # docstring.
    assert_not_simulated([audio_path] + clip_paths)

    # 1. Normalize audio (loudnorm -14 LUFS)
    logger.info("[S7] %s normalizing audio", episode_id)
    norm_path   = os.path.join(out_dir, "audio_norm.mp3")
    lufs_report = await normalize_audio(
        input_path=audio_path, output_path=norm_path, platform="spotify")

    # Pre-render quality gate: fail fast on unusable inputs (EP001 class).
    qa = {"pre": await pre_render_check(clip_paths, norm_path), "post": {}}

    # 2. Select BGM (5-Beat Adaptive BGM Engine - Rule 125 & R3)
    duration_s = lufs_report.get("duration_s", 60.0)
    logger.info("[S7] %s assembling 5-Beat adaptive BGM dur=%.1fs", episode_id, duration_s)
    bgm_path = None
    bgm_info = {}
    try:
        from app.services.beat_bgm_engine import generate_beat_adaptive_bgm
        bgm_info = generate_beat_adaptive_bgm(
            episode_id=episode_id,
            out_dir=out_dir,
            audio_path=norm_path
        )
        bgm_path = bgm_info.get("bgm_path")
        logger.info("[S7] %s 5-Beat BGM generated: %s (%d tracks)", episode_id, bgm_path, len(bgm_info.get("tracks", [])))
    except Exception as e:
        logger.warning("[S7] %s 5-Beat BGM failed (%s), falling back to select_bgm", episode_id, e)
        try:
            bgm_info = await select_bgm(mood=mood, duration_s=duration_s)
            bgm_path = bgm_info.get("path")
        except Exception as _e_bgm:
            logger.warning("[S7] %s select_bgm fallback failed: %s", episode_id, _e_bgm)

    # Resolve render_architecture early (Rule 116 / Single Source of Truth)
    render_arch = str(episode.get("render_architecture") or "").strip()
    if not render_arch and os.path.exists(os.path.join(out_dir, "brain_input.json")):
        try:
            import json as _json
            with open(os.path.join(out_dir, "brain_input.json"), "r", encoding="utf-8") as _bf:
                render_arch = str(_json.load(_bf).get("render_architecture") or "").strip()
        except Exception:
            pass

    # 3. Render the 16:9 master ONCE (concat+grade+mux, NO subs yet), then
    #    derive 9:16 & 1:1 from it with a blurred-fill (Hotfix v7 speedup).
    #    Hotfix v8 (21/07): subtitles are burned AFTER deriving each aspect,
    #    per-aspect, so subtitle size/position matches that aspect's real
    #    frame instead of inheriting a 16:9-scaled bake via blurpad).
    renders = {}
    master_aspect = "16:9"
    master_key = "final_169"
    master_path = os.path.join(out_dir, master_key + ".mp4")
    is_two_layer = render_arch in ("two_layer_v1", "remotion_twolayer_karaoke_v4") or "twolayer" in render_arch or render_arch.startswith("two_layer")
    if is_two_layer:
        logger.info("[S7] %s render_architecture == '%s': skipping motion_cards intro/outro to prevent desync & black frame", episode_id, render_arch)
        render_clips = clip_paths
    else:
        render_clips = await build_cards(episode, master_aspect, out_dir, clip_paths)
    logger.info("[S7] %s rendering MASTER %s from %d clips (+%d cards)",
                episode_id, master_aspect, len(clip_paths),
                len(render_clips) - len(clip_paths))
    await render_video(
        clips=render_clips,
        audio_path=norm_path,
        output_path=master_path,
        aspect=master_aspect,
        bgm_path=bgm_path,
        subtitle_segments=None,  # v8: subs burned per-aspect below, not here
        lang_code=lang_code,
        episode_id=episode_id,
    )
    renders[master_key] = master_path
    logger.info("[S7] %s master %s rendered (no subs yet) -> %s", episode_id, master_aspect, master_path)

    for aspect in ["9:16", "1:1"]:
        key      = "final_" + aspect.replace(":", "")
        out_path = os.path.join(out_dir, key + ".mp4")
        logger.info("[S7] %s deriving %s from 16:9 master (blurpad)",
                    episode_id, aspect)
        try:
            await derive_aspect_blurpad(master_path, out_path, aspect)
        except Exception as e:
            logger.warning("[S7] %s blurpad derive failed for %s (%s); "
                           "falling back to full render", episode_id, aspect, e)
            if is_two_layer:
                render_clips = clip_paths
            else:
                render_clips = await build_cards(episode, aspect, out_dir, clip_paths)
            await render_video(
                clips=render_clips, audio_path=norm_path, output_path=out_path,
                aspect=aspect, bgm_path=bgm_path,
                subtitle_segments=None,  # v8: subs burned per-aspect below
                lang_code=lang_code, episode_id=episode_id)
        renders[key] = out_path
        logger.info("[S7] %s %s derived (no subs yet) -> %s", episode_id, aspect, out_path)

    # 4. Hotfix v8: burn dub/subtitles per aspect, AFTER all 3 frames exist,
    #    with an aspect-tuned style (fixes subs shrinking/mispositioning on
    #    9:16 & 1:1 after inheriting the 16:9 bake via blurpad).
    # Single Source of Truth Subtitles: For two_layer_v1, the Remotion Safe-Zone
    # Dialogue Container is the sole on-screen subtitle mechanism. Bypass FFmpeg subtitle
    # burning completely to prevent double/overlapping subtitles.
    render_arch = str(episode.get("render_architecture") or "").strip()
    if not render_arch and os.path.exists(os.path.join(out_dir, "brain_input.json")):
        try:
            import json as _json
            with open(os.path.join(out_dir, "brain_input.json"), "r", encoding="utf-8") as _bf:
                render_arch = str(_json.load(_bf).get("render_architecture") or "").strip()
        except Exception:
            pass

    if is_two_layer:
        logger.info(
            "[S7] %s render_architecture == '%s': skipping redundant FFmpeg subtitle burning "
            "(Remotion Safe-Zone Dialogue Container is sole on-screen subtitle mechanism)",
            episode_id,
            render_arch,
        )
        episode["subtitle_mode"] = "remotion_two_layer"
    elif segments:
        # FLOW ENHANCE 27/07/2026: prefer real karaoke ASS (word-level highlight)
        # and always clean up the temp file, even when the burn fails.
        _use_kara = karaoke_enabled()
        for aspect in [master_aspect, "9:16", "1:1"]:
            key = "final_" + aspect.replace(":", "")
            path = renders[key]
            tmp_subbed = path + ".subbed.mp4"
            try:
                if _use_kara:
                    logger.info("[S7] %s burning KARAOKE subs for %s", episode_id, aspect)
                    try:
                        await burn_karaoke_for_aspect(
                            path, tmp_subbed, segments, aspect, lang_code)
                    except Exception as _ke:
                        logger.warning("[S7] %s karaoke burn failed for %s (%s);"
                                       " falling back to plain SRT burn",
                                       episode_id, aspect, _ke)
                        await burn_subtitles_for_aspect(path, tmp_subbed, segments, aspect)
                else:
                    logger.info("[S7] %s burning subs for %s", episode_id, aspect)
                    await burn_subtitles_for_aspect(path, tmp_subbed, segments, aspect)
                os.replace(tmp_subbed, path)
            finally:
                if os.path.exists(tmp_subbed):
                    try:
                        os.remove(tmp_subbed)
                    except Exception:
                        pass
        episode["subtitle_mode"] = "karaoke_ass" if _use_kara else "srt_burn"

    qa["post"][master_key] = await post_render_check(
        renders[master_key], norm_path, is_primary=True)
    for aspect in ["9:16", "1:1"]:
        key = "final_" + aspect.replace(":", "")
        qa["post"][key] = await post_render_check(
            renders[key], norm_path, is_primary=(aspect == "9:16"))
        logger.info("[S7] %s %s done -> %s", episode_id, aspect, renders[key])

    # AUDIT RECORD (17/08/2026 - B9 pipeline audit): persist render gate verdict.
    try:
        from app.audit.db import save_audit_result
        _post = (qa.get("post") or {})
        _fails = [k for k, v in _post.items()
                  if isinstance(v, dict) and v.get("ok") is False]
        _ok = bool(_post) and not _fails
        save_audit_result(
            episode_id, "render", "S7", 10.0 if _ok else 4.0,
            "APPROVED" if _ok else "REJECTED",
            {"aspects_ok": len(_post) - len(_fails),
             "aspects_total": len(_post)},
            [{"severity": "high", "axis": "render_gate",
              "message": "aspects failed: " + ",".join(_fails)}] if _fails else [],
            [], "rule_only")
    except Exception as _e:
        logger.warning("[S7] render audit record failed: %s", _e)

    return {**episode,
            **renders,
            "bgm_path":        bgm_path,
            "bgm_tracks":      bgm_info.get("tracks", []),
            "bgm_attribution": bgm_info.get("attribution_text", ""),
            "audio_norm":      norm_path,
            "qa_gate":         qa,
            "lufs_report":     lufs_report}
