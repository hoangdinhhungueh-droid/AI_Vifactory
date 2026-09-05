# app/services/episode_images.py — Phase 2b (Luong chuan v1, BUOC 6).
# POST /api/v1/episodes/<episode_id>/generate-images
#   1. Run scripts/compile_episode_from_notion.py <id> (subprocess — compiler
#      stays CLI, single writer of brain_input.json, Rule 44 enforced there)
#   2. Read the compiled brain_input.json
#   3. BG per unique background_reuse_key  -> gen_scene_image FREE chain
#      (Google Image via Antigravity UI)
#      FG per scene with visual_subject_type + foreground_prompt
#      -> Type A: gpt-image-2 via character_ref_image (Rule 46 hero ref from
#      character_refs store) | Type B: free chain + style anchor tail
#   4. FG: chroma-key (remove_bg_chromakey) -> validate _nobg >80% transparent
#      pixels — FAIL HARD, never fall back to the raw jpg (Rule 76)
#   5. Upload R2 (image_gen._r2_upload, SigV4 already handled there, Rule 24)
#   6. Create Image Asset Library rows (Status=New, AI Verdict=Pending Review)
#      — Notion AI audits afterwards via viewFileUrl (Rule 47)
#   7. Telegram summary (soft-fail)
# dry_run=true: compile + return the job plan only, zero quota burned.
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import requests
from pathlib import Path
from datetime import datetime
import shutil

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import character_refs as _cref
from app.services import image_gen as _img
from app.services import telegram_notify as _tg
from app.services.hhtech_reasoner import call_gpt56_sol
from app.services.skill_loader import get_skill_rules

sys.path.insert(0, "/root/video_factory/scripts")
try:
    import remove_bg_chromakey as _ck
except Exception:  # pragma: no cover
    _ck = None

logger = logging.getLogger(__name__)
router = APIRouter()

EPISODES_DIR = Path("/var/vf/episodes")
COMPILER = "/root/video_factory/scripts/compile_episode_from_notion.py"
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"
ID_CACHE = Path("/root/video_factory/data/notion_db_ids.json")
_REQ_GAP = 0.35
_ENV_LOADED = False
FG_MIN_TRANSPARENT = 0.80  # Rule 76
UNIFORMITY_MAX_SPREAD = 45.0  # RULE76_UNIFORMITY_CHECK, see below
YOUTUBE_REGISTRY_DB_ID = "3c301989-2400-81b9-a4bb-e5568ce942f8"  # Rule 123 (23/08/2026)

# RULE76_AUTOSAMPLE_PATCH (12/08/2026): production chroma-key previously keyed
# against a hardcoded magenta constant (250,4,229) with tol=60/soft=40.
# crimson/red-magenta, e.g. RGB ~(188,5,68) with corner std <1.2 -- a clean
# flat background that the hardcoded key still missed by Euclidean distance
# ~180+). Fix: auto-sample the actual generated background corner color per
# image (same technique validated in the isolated test harness) and key
# against THAT color, with a moderately wider tolerance band to absorb JPEG
# compression noise near the key. This does NOT fix cases where the model
# fails to produce a flat/uniform background at all (corner-sample std > ~5)
# -- that is a generation-quality issue requiring prompt/benchmark work, not
# a chroma-key parameter.
#
# RULE76_UNIFORMITY_CHECK (14/08/2026): the gap flagged by the note above was
# (sc047, en-enron-ep006): the generated frame had black letterbox/pillarbox
# bars top+bottom, so 2 of the previous 4 corner samples landed on near-black
# while the other 2 landed on the real magenta backdrop. Averaging those 4
# points produced a garbage mid-tone key color that matched neither the
# backdrop nor the letterbox, silently corrupting the chroma-key pass instead
# of failing loudly with a clear reason. Fix: sample 8 border points (4
# corners + 4 edge midpoints) instead of 4, and compute the max pairwise
# Euclidean distance between them. A clean uniform backdrop (even one that
# has drifted hue, e.g. crimson instead of magenta) keeps this spread low
# because all 8 points still land on the SAME flat color; letterboxing,
# gradients, or a failed generation blow the spread up sharply because the
# points land on genuinely different colors. Raise immediately when the
# spread is too high so the caller's existing try/except records a specific,
# diagnosable fg_fail reason instead of a vague low-transparent-ratio error.
def _sample_bg_corner_color(path):
    from PIL import Image
    import math
    im = Image.open(path).convert("RGB")
    w, h = im.size
    pts = [
        (2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3),
        (w // 2, 2), (w // 2, h - 3), (2, h // 2), (w - 3, h // 2),
    ]
    px = [im.getpixel(p) for p in pts]
    max_spread = 0.0
    for i in range(len(px)):
        for j in range(i + 1, len(px)):
            d = math.sqrt(sum((px[i][k] - px[j][k]) ** 2 for k in range(3)))
            if d > max_spread:
                max_spread = d
    if max_spread > UNIFORMITY_MAX_SPREAD:
        raise RuntimeError(
            "RULE76_UNIFORMITY_CHECK FAIL: background corner spread %.1f > %.1f"
            " (letterboxing or non-uniform backdrop)"
            % (max_spread, UNIFORMITY_MAX_SPREAD))
    mean = tuple(int(sum(px[i][k] for i in range(len(px))) / len(px))
                 for k in range(3))
    return mean


def _transparent_ratio(path):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    a = [pix[3] for pix in im.getdata()]
    transp = sum(1 for v in a if v < 128)
    return transp / len(a) if a else 0.0


def _load_env():
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    secrets = Path("/root/video_factory/config/secrets.env")
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, eq, v = line.partition("=")
            if eq:
                os.environ.setdefault(k.strip(), v.strip())
    _ENV_LOADED = True


def _call(method, path, body=None):
    _load_env()
    tok = os.environ.get("NOTION_TOKEN", "")
    hdrs = {
        "Authorization": "Bearer " + tok,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    url = API + path
    req = urllib.request.Request(url, headers=hdrs, method=method)
    if body is not None:
        req.data = json.dumps(body).encode("utf-8")
    time.sleep(_REQ_GAP)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _get_db_id(label):
    if ID_CACHE.exists():
        try:
            cache = json.loads(ID_CACHE.read_text())
            if label in cache:
                return cache[label]
        except Exception:
            pass
    return None


_PROVIDER_TO_SOURCE = {
    "google_imagen": "Imagen/Vertex",
    "openai": "OpenAI/DALL-E",
}


class GenImagesReq(BaseModel):
    layer: str = "both"
    dry_run: bool = False


def _hero_ref_path(episode_id, brain):
    if not brain.get("hero_character_ref_id"):
        return None
    ref_local = _cref.get_character_ref_local_path(
        brain["hero_character_ref_id"])
    if ref_local and os.path.exists(ref_local):
        return ref_local
    logger.warning(
        "[genimg] hero_character_ref_id %s not found on disk (episode %s)",
        brain["hero_character_ref_id"], episode_id)
    return None


def _ial_create_row(episode_id, name, reuse_key, img_type, scene_idx,
                     prompt, source, url, image_path=None):
    db = _get_db_id("image_asset_library")
    if not db:
        raise RuntimeError("image_asset_library DB not in cache")
    props = {
        "Name": {"title": [{"type": "text", "text": {"content": name}}]},
        "Reuse Key": {"rich_text": [{"text": {"content": reuse_key}}]},
        "Image Type": {"select": {"name": img_type}},
        "Source": {"select": {"name": source}},
        "Image URL": {"url": url},
        "Status": {"status": {"name": "New"}},
        "AI Verdict": {"select": {"name": "Pending Review"}},
        "Episode ID": {"rich_text": [{"text": {"content": episode_id}}]},
        "Generation Prompt": {"rich_text": [{"text": {"content": prompt[:2000]}}]},
    }
    if scene_idx is not None:
        props["Scene Index"] = {"number": scene_idx}
    if image_path and os.path.exists(image_path):
        props["viewFileUrl"] = {"url": "file://" + image_path}
    _call("POST", "/pages", {"parent": {"database_id": db}, "properties": props})


def _build_plan(brain, layer):
    scenes = brain.get("scenes") or []
    art_style_val = brain.get("art_style")
    style_tail = (art_style_val.get("style_prompt")
                  if isinstance(art_style_val, dict) else art_style_val) or ""
    bg_jobs, fg_jobs = [], []
    for s in scenes:
        if layer in ("both", "bg") and (s.get("image_prompt") or "").strip():
            bgk = s.get("background_reuse_key") or (
                "%s_bg_sc%s" % (brain.get("episode_id"), s.get("scene_index")))
            if not any(j["reuse_key"] == bgk for j in bg_jobs):
                prompt = s.get("image_prompt") or ""
                bg_jobs.append({
                    "reuse_key": bgk,
                    "scene_index": s.get("scene_index"),
                    "prompt": (prompt + ", " + style_tail).strip(", ") if style_tail
                              else prompt,
                })
        if layer in ("both", "fg") and s.get("visual_subject_type") \
                and (s.get("foreground_prompt") or "").strip():
            fg_jobs.append({
                "reuse_key": s.get("foreground_reuse_key")
                or ("%s_fg_sc%s" % (brain.get("episode_id"), s.get("scene_index"))),
                "scene_index": s.get("scene_index"),
                "subject_type": s.get("visual_subject_type"),
                "prompt": s["foreground_prompt"],
            })
    return bg_jobs, fg_jobs


async def _gen_one(prompt, ref=None):
    return await _img.gen_scene_image(prompt, aspect="16:9",
                                      character_ref_image=ref)


# --------------------------------------------------------- PATTERN 4: Checkpoint/Resume
def _checkpoint_path(episode_id: str) -> Path:
    """Return path to b4_checkpoint.json for this episode."""
    return EPISODES_DIR / episode_id / "b4_checkpoint.json"


def _load_checkpoint(episode_id: str) -> dict:
    """Load checkpoint if exists, else return empty dict."""
    ckpt_path = _checkpoint_path(episode_id)
    if ckpt_path.exists():
        try:
            data = json.loads(ckpt_path.read_text(encoding="utf-8"))
            logger.info("[B4] Loaded checkpoint for %s: %d completed images",
                        episode_id, len(data.get("completed_images", [])))
            return data
        except Exception as e:
            logger.warning("[B4] Failed to load checkpoint: %s", e)
    return {}


def _save_checkpoint(episode_id: str, completed_images: list,
                     bg_ok: int = 0, fg_ok: int = 0, thumbnail_ok: bool = False):
    """Save checkpoint with current progress."""
    ckpt_path = _checkpoint_path(episode_id)
    checkpoint = {
        "completed_images": list(set(completed_images)),  # deduplicate
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "episode_id": episode_id,
        "bg_ok": bg_ok,
        "fg_ok": fg_ok,
        "thumbnail_ok": thumbnail_ok,
    }
    try:
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
        logger.info("[B4] Checkpoint saved: %d images completed", len(completed_images))
    except Exception as e:
        logger.warning("[B4] Failed to save checkpoint: %s", e)


def _delete_checkpoint(episode_id: str):
    """Delete checkpoint file when generation is complete."""
    ckpt_path = _checkpoint_path(episode_id)
    if ckpt_path.exists():
        try:
            ckpt_path.unlink()
            logger.info("[B4] Checkpoint deleted for %s (generation complete)", episode_id)
        except Exception as e:
            logger.warning("[B4] Failed to delete checkpoint: %s", e)


def _archive_existing_images(episode_id: str):
    """Archive existing images before regeneration (rollback support).
    Only called if NO checkpoint exists (clean slate generation).
    """
    images_dir = EPISODES_DIR / episode_id / "images"
    if not images_dir.exists():
        return  # No images to archive

    archive_dir = EPISODES_DIR / episode_id / "b4_archives"
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archived_count = 0

    for img_file in images_dir.glob("*.png"):
        try:
            archive_path = archive_dir / f"{img_file.stem}_{timestamp}.png"
            shutil.copy2(img_file, archive_path)
            archived_count += 1
        except Exception as e:
            logger.warning("[B4] Failed to archive %s: %s", img_file.name, e)

    for img_file in images_dir.glob("*.jpg"):
        try:
            archive_path = archive_dir / f"{img_file.stem}_{timestamp}.jpg"
            shutil.copy2(img_file, archive_path)
            archived_count += 1
        except Exception as e:
            logger.warning("[B4] Failed to archive %s: %s", img_file.name, e)

    if archived_count > 0:
        logger.info("[B4] Archived %d existing images to %s", archived_count, archive_dir)


def _is_completed(reuse_key: str, checkpoint: dict) -> bool:
    """Check if this reuse_key is in the completed list."""
    return reuse_key in checkpoint.get("completed_images", [])


# ----------------------------------------------------------------- endpoint
@router.post("/api/v1/episodes/{episode_id}/generate-images")
async def generate_images(episode_id: str, req: GenImagesReq):
    episode_id = (episode_id or "").strip()
    if not episode_id:
        return {"ok": False, "error": "episode_id required"}
    if req.layer not in ("both", "bg", "fg"):
        return {"ok": False, "error": "layer must be both|bg|fg"}

    # 1. compile from Notion (compiler = single writer, enforces validation)
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, COMPILER, episode_id],
            capture_output=True, text=True, timeout=300)
    except Exception as e:
        return {"ok": False, "episode_id": episode_id,
                "error": "compiler run failed: %s" % e}
    last = (proc.stdout or "").strip().splitlines()
    comp = {}
    if last:
        try:
            comp = json.loads(last[-1])
        except Exception:
            comp = {}
    if proc.returncode != 0 or not comp.get("ok"):
        return {"ok": False, "episode_id": episode_id,
                "error": "compile failed: %s" % (comp.get("error")
                         or (proc.stderr or proc.stdout)[-400:])}

    brain_path = EPISODES_DIR / episode_id / "brain_input.json"
    try:
        brain = json.loads(brain_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "episode_id": episode_id,
                "error": "brain_input.json unreadable after compile: %s" % e}

    bg_jobs, fg_jobs = _build_plan(brain, req.layer)
    if req.dry_run:
        return {
            "ok": True, "episode_id": episode_id, "dry_run": True,
            "content_hash": brain.get("_content_hash"),
            "bg_jobs": len(bg_jobs), "fg_jobs": len(fg_jobs),
            "plan": {"bg": bg_jobs, "fg": fg_jobs},
        }

    # PATTERN 4: Load checkpoint and archive existing images if needed
    checkpoint = _load_checkpoint(episode_id)
    completed_images = checkpoint.get("completed_images", [])

    if not checkpoint:
        # First run, archive existing images for rollback support
        _archive_existing_images(episode_id)
        logger.info("[B4] Starting fresh generation for %s", episode_id)
    else:
        logger.info("[B4] Resuming generation for %s (%d images already complete)",
                    episode_id, len(completed_images))

    hero_ref = _hero_ref_path(episode_id, brain)
    out_dir = EPISODES_DIR / episode_id / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {"bg_ok": 0, "bg_fail": 0, "fg_ok": 0, "fg_fail": 0,
               "rows_created": 0, "errors": []}

    async def _finish(job, layer, img):
        local = img.get("local_path")
        provider = img.get("provider") or "unknown"
        r2 = None
        try:
            r2 = _img._r2_upload(
                local, "episodes/%s/%s" % (episode_id, os.path.basename(local)))
        except Exception as e:
            logger.warning("[genimg] r2 upload failed: %s", e)
        try:
            _ial_create_row(
                episode_id,
                "%s · %s" % (episode_id, job["reuse_key"]),
                job["reuse_key"],
                "Background" if layer == "bg" else "Foreground/Overlay",
                job.get("scene_index"), job["prompt"],
                _PROVIDER_TO_SOURCE.get(provider, provider),
                r2 or local,
                image_path=local)
            results["rows_created"] += 1
        except Exception as e:
            logger.warning("[genimg] IAL row create failed: %s", e)
            results["errors"].append("ial_row %s: %s" % (job["reuse_key"], e))

    # BG jobs — free chain, one per unique reuse key
    for job in bg_jobs:
        reuse_key = job["reuse_key"]
        if _is_completed(reuse_key, checkpoint):
            logger.info("[B4] Skipping BG %s (already completed)", reuse_key)
            results["bg_ok"] += 1  # Count as success (already done)
            continue

        try:
            img = await _gen_one(job["prompt"])
            await _finish(job, "bg", img)
            results["bg_ok"] += 1

            # Save checkpoint after each success
            completed_images.append(reuse_key)
            _save_checkpoint(episode_id, completed_images,
                            bg_ok=results["bg_ok"], fg_ok=results["fg_ok"])
        except Exception as e:
            results["bg_fail"] += 1
            results["errors"].append("bg %s: %s" % (reuse_key, e))

    # FG jobs — Type A uses Rule 46 hero ref (gpt-image-2), chroma-key + Rule 76
    for job in fg_jobs:
        reuse_key = job["reuse_key"]
        if _is_completed(reuse_key, checkpoint):
            logger.info("[B4] Skipping FG %s (already completed)", reuse_key)
            results["fg_ok"] += 1  # Count as success (already done)
            continue

        try:
            ref = hero_ref if job.get("subject_type") == "A" else None
            if job.get("subject_type") == "A" and not ref:
                results["errors"].append(
                    "fg %s: Type A but no hero ref on disk — used FREE chain"
                    % reuse_key)
            img = await _gen_one(job["prompt"], ref=ref)
            local = img.get("local_path")
            if _ck is None:
                raise RuntimeError("remove_bg_chromakey module unavailable")
            nobg = os.path.splitext(local)[0] + "_nobg.png"
            _bg_key = await asyncio.to_thread(_sample_bg_corner_color, local)
            await asyncio.to_thread(
                _ck.remove_bg_chromakey, local, nobg,
                bg_color=_bg_key, tol=90.0, soft=60.0)
            ratio = await asyncio.to_thread(_transparent_ratio, nobg)
            if ratio < FG_MIN_TRANSPARENT:
                raise RuntimeError(
                    "chroma-key FAIL HARD (Rule 76): %.0f%% transparent < %.0f%%"
                    % (ratio * 100, FG_MIN_TRANSPARENT * 100))
            img = dict(img, local_path=nobg)
            await _finish(job, "fg", img)
            results["fg_ok"] += 1

            # Save checkpoint after each success
            completed_images.append(reuse_key)
            _save_checkpoint(episode_id, completed_images,
                            bg_ok=results["bg_ok"], fg_ok=results["fg_ok"])
        except Exception as e:
            results["fg_fail"] += 1
            results["errors"].append("fg %s: %s" % (reuse_key, e))

    # --- Rule 123 (23/08/2026): viral thumbnail, generated alongside BG/FG ---
    thumbnail_key = f"{episode_id}_thumbnail"
    if not _is_completed(thumbnail_key, checkpoint):
        try:
            thumb_prompt = _generate_thumbnail_prompt(brain)
            thumb_img = await _gen_one(thumb_prompt)
            thumb_local = thumb_img.get("local_path")
            if thumb_local and os.path.exists(thumb_local):
                from PIL import Image as _PILImage
                thumb_dest = str(out_dir / "thumbnail.png")
                _PILImage.open(thumb_local).convert("RGB").save(thumb_dest, "PNG")
                results["thumbnail_ok"] = True
                results["thumbnail_prompt"] = thumb_prompt

                # Save checkpoint for thumbnail
                completed_images.append(thumbnail_key)
                _save_checkpoint(episode_id, completed_images,
                                bg_ok=results["bg_ok"], fg_ok=results["fg_ok"],
                                thumbnail_ok=True)

                try:
                    thumb_r2 = _img._r2_upload(
                        thumb_dest, "episodes/%s/thumbnail.png" % episode_id)
                    if thumb_r2:
                        results["thumbnail_url"] = thumb_r2
                        _registry_upsert_thumbnail(episode_id, thumb_r2)
                except Exception as e:
                    logger.warning("[genimg] thumbnail R2/registry sync failed: %s", e)
            else:
                results["thumbnail_ok"] = False
                results["errors"].append("thumbnail: no local_path from image gen")
        except Exception as e:
            results["thumbnail_ok"] = False
            results["errors"].append("thumbnail: %s" % e)
            logger.warning("[genimg] thumbnail generation failed: %s", e)
    else:
        logger.info("[B4] Skipping thumbnail (already completed)")
        results["thumbnail_ok"] = True

    try:
        await _tg.notify_production(
            "IMAGES", episode_id,
            "BG %d ok/%d fail · FG %d ok/%d fail · %d IAL rows"
            % (results["bg_ok"], results["bg_fail"], results["fg_ok"],
               results["fg_fail"], results["rows_created"]))
    except Exception as e:
        logger.warning("[genimg] telegram notify failed: %s", e)

    # PATTERN 4: Delete checkpoint if all images successful
    if results["bg_fail"] == 0 and results["fg_fail"] == 0:
        _delete_checkpoint(episode_id)

    return {"ok": results["bg_fail"] == 0 and results["fg_fail"] == 0,
            "episode_id": episode_id,
            "content_hash": brain.get("_content_hash"), **results}


# --------------------------------------------------------- Rule 123 helpers
def _generate_thumbnail_prompt(brain):
    """B3 (viral skill): ask GPT-5.6-Sol for ONE high-CTR YouTube thumbnail
    image-generation prompt, applying the SEO Playbook viral Hook A/B/C
    framework (Emotion-first / Keyword-first / Curiosity-gap) and matching
    this episode's existing BG/FG art style."""
    art_style_val = brain.get("art_style"); style_tail = (art_style_val.get("style_prompt") if isinstance(art_style_val, dict) else art_style_val) or ""
    hook = brain.get("hook_3s") or ""
    story = (brain.get("story") or "")[:1200]

    # B4: Load Skill AI rules (cache 1h, aligned with B1/B2/B3/B3.5)
    skill_rules = get_skill_rules()
    system = (
        "You are the Lead Thumbnail Art Director for Video Factory, applying "
        "the viral CTR-optimization framework (Skill AI SEO Playbook Hook "
        "A/B/C: Emotion-first, Keyword-first, Curiosity-gap). Produce ONE "
        "single AI-image-generation prompt (not three) for a YouTube "
        "thumbnail, 16:9, that maximizes click-through: one dramatic hero "
        "character or moment, extreme facial emotion or high-stakes action, "
        "bold high-contrast lighting, rule-of-thirds composition with a "
        "clear focal point, NO baked-in text or logos (YouTube renders the "
        "title separately). Match the episode's existing visual style: "
        + (style_tail or "flat editorial documentary illustration") +
        ". Output ONLY the raw image prompt text, nothing else."
    )
    system = system + "\n\n" + skill_rules
    user = (
        "Episode hook (0-3s): %s\n\nStory excerpt:\n%s\n\nWrite the single "
        "best viral thumbnail prompt now." % (hook, story)
    )
    try:
        prompt = call_gpt56_sol(user, system_prompt=system, max_tokens=400)
        return prompt.strip().strip(chr(34)).strip()
    except Exception as e:
        logger.warning(
            "[genimg] thumbnail prompt gen (GPT-5.6-Sol) failed, falling "
            "back to hook-based prompt: %s", e)
        return (
            "Dramatic high-contrast documentary thumbnail, %s, extreme "
            "emotional close-up, bold cinematic lighting, 16:9, %s"
            % (hook or brain.get("topic", ""), style_tail)
        ).strip(", ")


def _registry_upsert_thumbnail(episode_id, thumbnail_url):
    """Narrow, best-effort upsert: writes ONLY the Thumbnail URL property on
    the YouTube Channel & Video Metadata Registry row for this episode.
    Never touches any other property -- safe to run even while the B9/B10
    registry-sync step creates/updates the rest of the row concurrently."""
    try:
        q = _call("POST", "/databases/%s/query" % YOUTUBE_REGISTRY_DB_ID, {
            "filter": {"property": "Task ID", "rich_text": {"equals": episode_id}},
            "page_size": 1,
        })
        rows = (q or {}).get("results", [])
        if rows:
            _call("PATCH", "/pages/%s" % rows[0]["id"], {
                "properties": {"Thumbnail URL": {"url": thumbnail_url}}
            })
        else:
            _call("POST", "/pages", {
                "parent": {"database_id": YOUTUBE_REGISTRY_DB_ID},
                "properties": {
                    "Name": {"title": [{"type": "text", "text": {"content": episode_id}}]},
                    "Task ID": {"rich_text": [{"type": "text", "text": {"content": episode_id}}]},
                    "Thumbnail URL": {"url": thumbnail_url},
                },
            })
        logger.info("[genimg] registry thumbnail synced for %s", episode_id)
    except Exception as e:
        logger.warning("[genimg] registry thumbnail sync failed (non-fatal): %s", e)
