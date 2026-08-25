#!/usr/bin/env python3
"""Generic seed-brain engine (Rule 70 muc 3 + muc 4).

Replaces the copy-pasted per-episode write-json boilerplate that
scripts/seed_brain_input.py (EP001) and scripts/seed_brain_input_ep005.py
(EP005) each hard-coded on their own. Any future scripts/seed_brain_input_
ep0NN.py should keep ONLY its episode-specific story/scene content as data
and call seed_episode_brain(...) here to actually write brain_input.json --
so the reference-role tagging (muc 3) and continuity wiring (muc 4) is
written ONCE and shared by every episode instead of being reinvented (or
skipped) per episode, the way EP001's seed_brain_input.py hard-coded
everything for EP001 only.

muc 3 -- reference-role tagging: every scene gets a `reference_role_tags`
dict (identity/environment/motion/camera_rhythm/style/endpoint) derived
generically from art_style/character_pack/camera_rules/motion_rules/the
scene's own fields -- NOT hard-coded per episode.

muc 4 -- continuity from last accepted shot: for any scene carrying a
foreground_reuse_key or background_reuse_key, this module calls
continuity_retake_helper.last_accepted_shot(...) (and check_review_round_
budget(...)) so the NEXT prompt for that reuse-key family can be built as a
continuation of the most recently Approved/Pulled-by-VPS shot instead of
restarting from scratch. These lookups are soft-fail (never raise, never
block seeding) -- the HARD budget gate (muc 2) lives in
continuity_retake_helper.gate_before_retake(...) and is meant to be called
by whatever actually triggers a regeneration attempt (Notion AI chat or a
future pipeline stage), not by this seed-time script.

Usage (from a per-episode seed script):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from seed_brain_lib import seed_episode_brain
    DATA = {...}  # episode-specific content authored from Notion
    result = seed_episode_brain(EID, DATA, notion_token=os.environ.get("NOTION_TOKEN"))

Safe to import from any seed_brain_input_ep0NN.py. Does not touch
app/pipeline/* at all, so importing/using this cannot affect a live render.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import continuity_retake_helper as _crh  # noqa: E402

# Defensive .env load (same pattern as app/services/trend_signals.py).
# Loads NOTION_TOKEN so seed scripts can call os.environ.get("NOTION_TOKEN")
# and continuity lookups work when running manually (not via pm2).
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.expanduser("~"), "secrets", ".env"))

EPISODES_DIR = Path("/var/vf/episodes")

# Generic camera-rhythm vocabulary fallback used only when an episode's own
# brain data does not define camera_rules.vocabulary (Rule 70 muc 3: applies
# to ANY episode, not just EP001's corporate-thriller camera_rules).
_DEFAULT_CAMERA_VOCAB = ["push-in", "pull-back", "pan", "tilt", "tracking", "static-hold"]

def _first_nonempty(*vals):
    for v in vals:
        if v:
            return v
    return None

def derive_reference_role_tags(scene, art_style=None, character_pack=None,
                                camera_rules=None, motion_rules=None):
    """Generic per-scene reference-role tags: identity/environment/motion/
    camera_rhythm/style/endpoint. Works for ANY episode's brain_input shape
    (2-layer background/foreground scenes OR the older image_prompt/
    motion_prompt scenes) -- nothing here is EP001- or EP005-specific.
    """
    art_style = art_style or {}
    character_pack = character_pack or []
    camera_rules = camera_rules or {}
    motion_rules = motion_rules or {}

    fg_key = scene.get("foreground_reuse_key")
    identity = "no-character/documentary"
    if fg_key and character_pack:
        identity = character_pack[0].get("name", "unknown-character")
        for c in character_pack:
            name = str(c.get("name", "")).strip()
            if name and name.lower().replace(" ", "_") in str(fg_key).lower():
                identity = name
                break
    elif character_pack and (scene.get("image_prompt") or scene.get("motion_prompt")):
        blob = (str(scene.get("image_prompt", "")) + " " + str(scene.get("motion_prompt", ""))).lower()
        for c in character_pack:
            name = str(c.get("name", "")).strip()
            if name and name.lower() in blob:
                identity = name
                break

    environment = _first_nonempty(
        scene.get("background_reuse_key"),
        scene.get("environment"),
        scene.get("image_prompt"),
        "unspecified",
    )

    motion = _first_nonempty(
        scene.get("motion_prompt"),
        motion_rules.get("no_static_hook"),
        "static" if scene.get("render_type") == "text_card" else "unspecified",
    )

    vocab = camera_rules.get("vocabulary") or _DEFAULT_CAMERA_VOCAB
    camera_rhythm = _first_nonempty(
        scene.get("camera_rhythm"),
        (vocab[0] if vocab else None),
        "static-hold",
    )

    style = _first_nonempty(art_style.get("style_id"), art_style.get("style_prompt"), "unspecified-style")

    render_type = (scene.get("render_type") or "").strip()
    if render_type:
        endpoint = render_type
    elif fg_key and character_pack:
        endpoint = "ai_video_character"
    elif scene.get("background_reuse_key") or scene.get("image_prompt"):
        endpoint = "antigravity_kenburns_image"
    else:
        endpoint = "stock_fallback"

    return {
        "identity": identity,
        "environment": environment,
        "motion": motion,
        "camera_rhythm": camera_rhythm,
        "style": style,
        "endpoint": endpoint,
    }

def attach_continuity(scene, episode_id, token, reuse_key_prefix=None):
    """muc 4, soft-fail: attach {last_accepted, budget} continuity info for
    this scene's reuse-key family. NEVER raises and NEVER blocks seeding --
    seeding must still succeed even with no NOTION_TOKEN / API outage.
    Mutates and returns the scene (with a `continuity` key added).
    """
    prefix = reuse_key_prefix or scene.get("foreground_reuse_key") or scene.get("background_reuse_key")
    scene_index = scene.get("scene_index")
    continuity = {"checked": False, "reason": None, "last_accepted": None, "budget": None}
    if not token:
        continuity["reason"] = "no NOTION_TOKEN in env; continuity skipped (non-blocking)"
        scene["continuity"] = continuity
        return scene
    try:
        if prefix:
            continuity["last_accepted"] = _crh.last_accepted_shot(token, episode_id, prefix)
        if scene_index is not None:
            continuity["budget"] = _crh.check_review_round_budget(token, episode_id, scene_index)
        continuity["checked"] = True
    except Exception as e:  # pragma: no cover - never let a Notion API hiccup block seeding
        continuity["reason"] = "continuity lookup failed (non-blocking): %r" % (e,)
    scene["continuity"] = continuity
    return scene

def seed_episode_brain(episode_id, data, notion_token=None, apply_reference_tags=True,
                        apply_continuity=True):
    """Generic seed-brain writer (Rule 70 muc 3 + muc 4), shared by every
    episode. `data` is the episode-specific brain dict (episode_id, hook_3s,
    story, art_style, arcs, character_pack, scenes, pending_scenes, ...)
    exactly like the DATA dict each seed_brain_input_ep0NN.py already builds
    -- this function does not invent any story content, it only (a) attaches
    generic reference-role tags + continuity metadata to each scene and
    (b) writes brain_input.json, so that logic lives in ONE place.
    """
    out_dir = EPISODES_DIR / episode_id
    out_dir.mkdir(parents=True, exist_ok=True)

    art_style = data.get("art_style") or {}
    character_pack = data.get("character_pack") or []
    camera_rules = data.get("camera_rules") or {}
    motion_rules = data.get("motion_rules") or {}
    token = notion_token or os.environ.get("NOTION_TOKEN")

    tagged = 0
    continuity_checked = 0
    for scene in data.get("scenes", []):
        if apply_reference_tags:
            scene["reference_role_tags"] = derive_reference_role_tags(
                scene, art_style=art_style, character_pack=character_pack,
                camera_rules=camera_rules, motion_rules=motion_rules)
            tagged += 1
        if apply_continuity:
            attach_continuity(scene, episode_id, token)
            if scene.get("continuity", {}).get("checked"):
                continuity_checked += 1

    p = out_dir / "brain_input.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return {
        "path": str(p),
        "size_bytes": p.stat().st_size,
        "scenes": len(data.get("scenes", [])),
        "reference_tags_applied": tagged,
        "continuity_checked": continuity_checked,
        "notion_token_present": bool(token),
    }
