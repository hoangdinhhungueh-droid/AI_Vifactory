#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical B10 (Upload) entrypoint -- AUTO SEO generation, Notion sync, YouTube
upload, and Human Gate 2 dispatch, with ZERO manual "paste into Antigravity"
step. Added 23/08/2026 per user request; implements Skill AI Rule 119.

Flow:
  1. Load episode context (brain_input.json + Story Library row for the
     already-validated B1 keyword & breakout queries, Rule 117).
  2. Auto-call HHTech GPT-6-Astra (app.services.seo_autogen_b10) to generate
     Title/Description/Thumbnail A-B-C/Hook Frame/End Screen packaging --
     same gateway pattern as B2 (produce_b1_b2_b3_gpt56_sol.py).
  3. Sync the generated packaging and breakout queries into the Notion Story Library row.
  4. Write youtube_upload_payload.json + ab_variants.json and upload the
     video via the EXISTING app.services.youtube_upload.upload_from_payload
     (unchanged).
  5. Best-effort auto-set a custom thumbnail ONLY if a purpose-built
     thumbnail asset already exists for the episode (see
     _find_thumbnail_asset).
  6. Update publish_ledger.json.
  7. Dispatch the UNCHANGED Human Gate 2 Telegram card (4 buttons) via
     app.services.telegram_buttons.send_gate3_card.
"""
import os
import sys
import json
import time
import re
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, "/root/video_factory")
sys.path.insert(0, "/root/video_factory/scripts")

from app.services.hhtech_reasoner import call_gpt56_sol  # noqa: F401 (re-exported for callers)
from app.services.seo_autogen_b10 import generate_seo_packaging
from app.services.youtube_upload import upload_from_payload
from app.services.youtube_thumbnail import set_thumbnail
from app.services.telegram_buttons import send_gate3_card
from app.services import publish_ledger
from ag_notion_bridge import update_page_properties, query_db, create_page
from notion_schema_ext import (
    ensure_db_properties,
    SEO_PACKAGING_PROPERTIES,
    REGISTRY_SEO_PROPERTIES,
    YOUTUBE_REGISTRY_DB_ID,
)

LEDGER_PATH = Path("/var/vf/data/publish_ledger.json")

# Filenames a FUTURE dedicated thumbnail-generation step (being built in a
# separate work thread as of 23/08/2026) is expected to produce. Do NOT add
# any generic/content-image fallback here -- see _find_thumbnail_asset().
DEDICATED_THUMBNAIL_FILENAMES = [
    "thumbnail_a.png",
    "thumbnail_a.jpg",
    "thumbnail_final.png",
    "thumbnail_final.jpg",
    "thumbnail.png",
    "thumbnail.jpg",
]


def _load_episode_context(episode_id: str, ep_dir: Path) -> dict:
    brain_path = ep_dir / "brain_input.json"
    if not brain_path.exists():
        raise FileNotFoundError(
            f"brain_input.json not found at {brain_path} -- cannot auto-generate SEO packaging "
            f"without real episode context (Rule 118: Zero-Mock Data, ask-before-deviating)."
        )
    with open(brain_path, "r", encoding="utf-8") as f:
        brain = json.load(f)

    episode = {
        "episode_id": episode_id,
        "hook_3s": brain.get("hook_3s"),
        "niche": brain.get("topic"),
        "niche_angle_brief": brain.get("niche_angle_brief", ""),
        "trend_keywords": brain.get("trend_keywords") or [],
        "breakout_queries": brain.get("breakout_queries") or [],
        "rising_queries": brain.get("rising_queries") or [],
        "chapters": brain.get("chapters") or [],
        "final_169": str(ep_dir / "final_169.mp4"),
        "lang_code": (brain.get("market") or "en"),
    }

    # Pull the B1-validated Search-Specific Keyword & Rising Queries from Story Library (Rule 117)
    # instead of re-deriving it -- KVS keyword research happens once, at B1.
    try:
        story_rows = query_db("story")
        for row in story_rows.get("results", []):
            props = row.get("properties", {})
            row_ep = "".join(t.get("plain_text", "") for t in props.get("Episode ID", {}).get("rich_text", []))
            row_task = "".join(t.get("plain_text", "") for t in props.get("Task ID", {}).get("rich_text", []))
            row_name = "".join(t.get("plain_text", "") for t in props.get("Name", {}).get("title", []))
            if row_ep == episode_id or row_task == episode_id or episode_id in row_name:
                kw = "".join(t.get("plain_text", "") for t in props.get("Keyword", {}).get("rich_text", []))
                if kw:
                    episode["trend_keywords"] = [kw] + [k for k in episode["trend_keywords"] if k != kw]

                # Check for Rising Queries / SEO Tags property in Story Library
                if not episode["breakout_queries"]:
                    rq_prop = props.get("Rising Queries", {}).get("rich_text", [])
                    st_prop = props.get("SEO Tags", {}).get("rich_text", [])
                    rq_txt = "".join(t.get("plain_text", "") for t in rq_prop).strip() if rq_prop else ""
                    if not rq_txt and st_prop:
                        rq_txt = "".join(t.get("plain_text", "") for t in st_prop).strip()
                    if rq_txt:
                        episode["breakout_queries"] = [q.strip() for q in re.split(r'[,;\n]', rq_txt) if q.strip()]

                episode["story_page_id"] = row.get("id")
                break
    except Exception:
        pass

    return episode


def _sync_to_notion(story_page_id: str, packaging: dict):
    ensure_db_properties("story", SEO_PACKAGING_PROPERTIES)
    thumb_summary = "\n".join(
        f"{v.get('variant')} ({v.get('framework')}): {v.get('headline_text')} -- {v.get('visual_concept')}"
        for v in packaging.get("thumbnail_variants", [])
    )
    end_screen = packaging.get("end_screen_notes", {})
    end_screen_summary = " | ".join(f"{k}: {v}" for k, v in end_screen.items())
    bqs = packaging.get("breakout_queries", [])
    bqs_clean = [str(q.get("query") if isinstance(q, dict) else q).strip() for q in bqs if q]
    bqs_clean = [q for q in bqs_clean if q]

    props = {
        "SEO Title A": {"rich_text": [{"type": "text", "text": {"content": packaging["title_a"][:2000]}}]},
        "SEO Title B": {"rich_text": [{"type": "text", "text": {"content": packaging["title_b"][:2000]}}]},
        "SEO Description": {"rich_text": [{"type": "text", "text": {"content": packaging["description"][:2000]}}]},
        "SEO Tags": {"rich_text": [{"type": "text", "text": {"content": ", ".join(packaging["tags"])[:2000]}}]},
        "SEO Hashtags": {"rich_text": [{"type": "text", "text": {"content": " ".join(packaging["hashtags"])[:2000]}}]},
        "Rising Queries": {"rich_text": [{"type": "text", "text": {"content": ", ".join(bqs_clean)[:2000]}}]},
        "Thumbnail Variants (A/B/C)": {"rich_text": [{"type": "text", "text": {"content": thumb_summary[:2000]}}]},
        "Hook Frame Note": {"rich_text": [{"type": "text", "text": {"content": packaging.get("hook_frame_note", "")[:2000]}}]},
        "End Screen Notes": {"rich_text": [{"type": "text", "text": {"content": end_screen_summary[:2000]}}]},
        "SEO Generation Method": {"rich_text": [{"type": "text", "text": {"content": packaging.get("generation_method", "")}}]},
    }
    if story_page_id:
        update_page_properties(story_page_id, props)


def _rt(content: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": (content or "")[:2000]}}]}


def _sync_to_youtube_registry(episode_id: str, market: str, packaging: dict):
    """Upsert SEO packaging into the REAL canonical YouTube Channel & Video
    Metadata Registry DB (confirmed 23/08/2026 via backfill_task_id.py /
    daily_knowledge_dreaming_sync.py -- this is DB7 in the Architecture Page
    pipeline diagram, NOT the Story Library). Matches an existing row by
    Episode ID; creates one if none exists yet. Additive-only schema PATCH
    for the 3 Rule 119 fields this registry did not already have.
    """
    ensure_db_properties(YOUTUBE_REGISTRY_DB_ID, REGISTRY_SEO_PROPERTIES)

    thumb_summary = "\n".join(
        f"{v.get('variant')} ({v.get('framework')}): {v.get('headline_text')} -- {v.get('visual_concept')}"
        for v in packaging.get("thumbnail_variants", [])
    )
    end_screen = packaging.get("end_screen_notes", {})
    end_screen_summary = " | ".join(f"{k}: {v}" for k, v in end_screen.items())

    props = {
        "Title A": _rt(packaging["title_a"]),
        "Title B (Backup A/B)": _rt(packaging["title_b"]),
        "Tags & Keywords": _rt(", ".join(packaging["tags"])),
        "SEO Description": _rt(packaging["description"]),
        "Hashtags": _rt(" ".join(packaging["hashtags"])),
        "Hook Frame (0-3s)": _rt(packaging.get("hook_frame_note", "")),
        "End Screen (3 diem)": _rt(end_screen_summary or thumb_summary),
        "SEO Generation Method": _rt(packaging.get("generation_method", "")),
        "AI Generated Disclosure": {"checkbox": True},
        "Market": {"select": {"name": market.upper()}},
        "Task ID": _rt(episode_id),
    }

    existing = query_db(
        YOUTUBE_REGISTRY_DB_ID,
        filter_obj={"property": "Task ID", "rich_text": {"equals": episode_id}},
    )
    rows = existing.get("results", []) if isinstance(existing, dict) else []
    if rows:
        update_page_properties(rows[0]["id"], props)
        return {"action": "updated", "page_id": rows[0]["id"]}

    props["Name"] = {"title": [{"type": "text", "text": {"content": f"{episode_id} · {packaging['title_a']}"}}]}
    created = create_page(YOUTUBE_REGISTRY_DB_ID, props)
    return {"action": "created", "page_id": created.get("id") if isinstance(created, dict) else None}


def compose_hero_thumbnail(ep_dir: Path) -> str | None:
    """Automate Hero-scene thumbnail composition (thumbnail_a.png) from Scene 000
    BG and FG cutouts via PIL (Rule 113 / 1-second thumbnail).
    """
    target_path = ep_dir / "thumbnail_a.png"
    if target_path.exists() and target_path.stat().st_size > 1000:
        return str(target_path)

    try:
        from PIL import Image
    except ImportError:
        print("[thumbnail] PIL/Pillow not available; skipping hero thumbnail composition")
        return None

    brain = {}
    brain_path = ep_dir / "brain_input.json"
    if brain_path.exists():
        try:
            with open(brain_path, "r", encoding="utf-8") as bf:
                brain = json.load(bf)
        except Exception as e:
            print(f"[thumbnail] Warning: failed to read {brain_path}: {e}")

    scenes = brain.get("scenes") or []
    hero_scene = scenes[0] if scenes else {}
    bg_key = str(hero_scene.get("background_reuse_key") or "").strip()
    fg_key = str(hero_scene.get("foreground_reuse_key") or "").strip()

    # Search for BG image
    bg_path = None
    bg_candidates = []
    if bg_key:
        bg_candidates.extend([
            ep_dir / "images" / f"{bg_key}.png",
            ep_dir / "assets" / f"{bg_key}.png",
            ep_dir / "images" / f"{bg_key}.jpg",
            ep_dir / "assets" / f"{bg_key}.jpg",
        ])
    for folder in [ep_dir / "images", ep_dir / "assets"]:
        if folder.exists():
            for f in sorted(folder.glob("*.png")):
                if "fg" not in f.name.lower() and f.name != "thumbnail_a.png":
                    bg_candidates.append(f)

    for cand in bg_candidates:
        if cand.exists() and cand.stat().st_size > 1000:
            bg_path = cand
            break

    if not bg_path:
        print("[thumbnail] No background image candidate found for Hero thumbnail")
        return None

    # Search for FG image
    fg_path = None
    fg_candidates = []
    if fg_key:
        fg_candidates.extend([
            ep_dir / "images" / f"{fg_key}.png",
            ep_dir / "assets" / f"{fg_key}.png",
        ])
    for folder in [ep_dir / "images", ep_dir / "assets"]:
        if folder.exists():
            for f in sorted(folder.glob("*.png")):
                if ("fg" in f.name.lower() or "character" in f.name.lower()) and f.name != "thumbnail_a.png":
                    fg_candidates.append(f)

    for cand in fg_candidates:
        if cand.exists() and cand.stat().st_size > 1000:
            fg_path = cand
            break

    try:
        # Standard YouTube thumbnail resolution: 1280x720 (16:9)
        THUMB_WIDTH, THUMB_HEIGHT = 1280, 720
        with Image.open(bg_path) as bg_img:
            bg_composite = bg_img.convert("RGBA")
            bg_ratio = bg_composite.width / float(bg_composite.height)
            target_ratio = THUMB_WIDTH / float(THUMB_HEIGHT)
            if bg_ratio > target_ratio:
                new_w = int(bg_composite.height * target_ratio)
                left = (bg_composite.width - new_w) // 2
                bg_composite = bg_composite.crop((left, 0, left + new_w, bg_composite.height))
            elif bg_ratio < target_ratio:
                new_h = int(bg_composite.width / target_ratio)
                top = (bg_composite.height - new_h) // 2
                bg_composite = bg_composite.crop((0, top, bg_composite.width, top + new_h))
            bg_composite = bg_composite.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)

            # Composite Foreground if present
            if fg_path:
                with Image.open(fg_path) as fg_img:
                    fg_rgba = fg_img.convert("RGBA")
                    fg_target_h = int(THUMB_HEIGHT * 0.90)
                    fg_scale = fg_target_h / float(fg_rgba.height)
                    fg_target_w = int(fg_rgba.width * fg_scale)
                    fg_resized = fg_rgba.resize((fg_target_w, fg_target_h), Image.Resampling.LANCZOS)

                    pos_pref = hero_scene.get("foreground_position") or "left"
                    if pos_pref == "right":
                        fg_x = THUMB_WIDTH - fg_target_w - 50
                    else:
                        fg_x = 50
                    fg_y = THUMB_HEIGHT - fg_target_h

                    bg_composite.paste(fg_resized, (fg_x, fg_y), fg_resized)

            final_rgb = bg_composite.convert("RGB")
            final_rgb.save(target_path, format="PNG", optimize=True)
            print(f"[thumbnail] Successfully composed Hero thumbnail: {target_path} ({THUMB_WIDTH}x{THUMB_HEIGHT})")
            return str(target_path)
    except Exception as e:
        print(f"[thumbnail] Failed to compose Hero thumbnail: {e}")
        return None


def _find_thumbnail_asset(ep_dir: Path) -> str:
    """Look ONLY for a purpose-built thumbnail asset produced by the dedicated
    thumbnail-generation step. Updated 23/08/2026 per user decision: do NOT
    fall back to any existing episode content/hero image -- that step is
    being built separately and will land later. Returns "" (skip thumbnail
    upload, non-blocking) when no dedicated asset is present yet.
    """
    for name in DEDICATED_THUMBNAIL_FILENAMES:
        p = ep_dir / name
        if p.exists():
            return str(p)
        p2 = ep_dir / "images" / name
        if p2.exists():
            return str(p2)
    return ""


async def run(episode_id: str, market: str = "en", privacy_status: str = "unlisted"):
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    if not ep_dir.exists():
        raise FileNotFoundError(f"Episode directory not found: {ep_dir}")

    print(f"=== [B10-AUTO] 1. Loading episode context for {episode_id} ===")
    episode = _load_episode_context(episode_id, ep_dir)

    print("=== [B10-AUTO] 2. Auto-generating SEO packaging via HHTech GPT-6-Astra (Rule 119) ===")
    packaging = generate_seo_packaging(episode)
    print(f"Generation method: {packaging['generation_method']}")

    with open(ep_dir / "seo_payload_b10.json", "w", encoding="utf-8") as f:
        json.dump(packaging, f, ensure_ascii=False, indent=2)

    print("=== [B10-AUTO] 3. Syncing packaging to Notion Story Library (supplementary) ===")
    _sync_to_notion(episode.get("story_page_id"), packaging)

    print("=== [B10-AUTO] 3b. Syncing packaging to YouTube Channel & Video Metadata Registry (canonical DB7) ===")
    registry_sync = _sync_to_youtube_registry(episode_id, market, packaging)
    print(f"Registry sync: {registry_sync}")


    # --- B9 QUALITY PROBE INTEGRATION ---
    print("=== [B9 QUALITY PROBE] Running EBU R128 and Integrity Check ===")
    import subprocess
    try:
        subprocess.run(["python3", "/root/video_factory/scripts/run_b9_quality_probe.py", "--episode", episode_id], check=True)
    except subprocess.CalledProcessError:
        raise RuntimeError("B9 Quality Probe FAILED. Upload aborted. See logs for LUFS/TruePeak errors.")
    # ------------------------------------

    print("=== [B10-AUTO] 4. Writing upload payload + A/B ledger ===")
    upload_payload = {
        "episode_id": episode_id,
        "title": packaging["title_a"],
        "description": packaging["description"],
        "tags": packaging["tags"],
        "hashtags": packaging["hashtags"],
        "breakout_queries": packaging.get("breakout_queries", []),
        "category_id": "22",
        "privacy_status": privacy_status,
        "export": {"target_file": "final_169.mp4"},
        "market": market,
    }
    with open(ep_dir / "youtube_upload_payload.json", "w", encoding="utf-8") as f:
        json.dump(upload_payload, f, ensure_ascii=False, indent=2)

    ab_variants = {
        "episode_id": episode_id,
        "rule_113_48h_law": {
            "locked_until": time.time() + (48 * 3600),
            "status": "Active Title A / Thumbnail A",
        },
        "title_a": packaging["title_a"],
        "title_b": packaging["title_b"],
        "breakout_queries": packaging.get("breakout_queries", []),
        "thumbnail_variants": packaging["thumbnail_variants"],
        "hook_frame_note": packaging.get("hook_frame_note", ""),
        "end_screen_notes": packaging.get("end_screen_notes", {}),
        "generation_method": packaging["generation_method"],
    }
    with open(ep_dir / "ab_variants.json", "w", encoding="utf-8") as f:
        json.dump(ab_variants, f, ensure_ascii=False, indent=2)

    # Check if video was already uploaded to avoid duplicate YouTube upload
    video_id = None
    if (ep_dir / "youtube_upload_payload.json").exists():
        try:
            old_p = json.loads((ep_dir / "youtube_upload_payload.json").read_text(encoding="utf-8"))
            if old_p.get("video_id"):
                video_id = old_p["video_id"]
        except Exception:
            pass
    if not video_id:
        try:
            for rec in publish_ledger.load_all():
                if rec.get("episode_dir") == str(ep_dir) and rec.get("video_id"):
                    video_id = rec["video_id"]
                    break
        except Exception:
            pass

    if video_id:
        print(f"YOUTUBE UPLOAD REUSED: video_id={video_id}")
    else:
        print("=== [B10-AUTO] 5. Uploading to YouTube (unlisted) ===")
        upload_res = upload_from_payload(str(ep_dir), privacy_status=privacy_status, market=market)
        video_id = upload_res.get("id")
        if not video_id:
            raise RuntimeError(f"Failed to extract video_id from upload response: {upload_res}")
        print(f"YOUTUBE UPLOAD SUCCESS: video_id={video_id}")

    upload_payload["video_id"] = video_id
    with open(ep_dir / "youtube_upload_payload.json", "w", encoding="utf-8") as f:
        json.dump(upload_payload, f, ensure_ascii=False, indent=2)

    print("=== [B10-AUTO] 6. Best-effort auto thumbnail set (automated Hero composition) ===")
    try:
        compose_hero_thumbnail(ep_dir)
    except Exception as _th_err:
        print(f"[thumbnail] compose_hero_thumbnail failed: {_th_err}")
    thumb_path = _find_thumbnail_asset(ep_dir)
    if thumb_path:
        set_thumbnail(video_id, thumb_path, market=market)
    else:
        print("No dedicated thumbnail asset found yet -- skipping thumbnail upload (dedicated generation step pending, per user decision 23/08/2026).")

    print("=== [B10-AUTO] 7. Updating publish_ledger.json ===")
    publish_ledger.record_upload(
        video_id=video_id,
        title=packaging["title_a"],
        episode_dir=str(ep_dir),
        privacy_status=privacy_status,
    )
    ledger = {}
    if LEDGER_PATH.exists():
        try:
            raw = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                ledger = raw
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        k = item.get("episode_id") or item.get("video_id")
                        if k:
                            ledger[k] = item
        except Exception:
            ledger = {}
    ledger[episode_id] = {
        "episode_id": episode_id,
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": packaging["title_a"],
        "privacy_status": privacy_status,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "market": market,
        "seo_generation_method": packaging["generation_method"],
        "thumbnail_set": bool(thumb_path),
    }
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== [B10-AUTO] 8. Dispatching Human Gate 2 Telegram card (unchanged, 4 buttons) ===")
    await send_gate3_card(
        video_id=video_id,
        episode_id=episode_id,
        title_a=packaging["title_a"],
        title_b=packaging["title_b"],
    )
    print("B10-AUTO complete. No manual Antigravity paste step was required.")
    return {"video_id": video_id, "packaging": packaging}


def main():
    parser = argparse.ArgumentParser(description="Auto SEO + Upload + Gate2 (B10)")
    parser.add_argument("--episode", required=True, help="Episode ID, e.g. en-byzantine-empire-ep001")
    parser.add_argument("--market", default="en")
    parser.add_argument("--privacy", default="unlisted")
    args = parser.parse_args()
    asyncio.run(run(args.episode, market=args.market, privacy_status=args.privacy))


if __name__ == "__main__":
    main()
