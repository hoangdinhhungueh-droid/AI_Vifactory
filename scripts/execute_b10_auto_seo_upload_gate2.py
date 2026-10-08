#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical B10 (Upload) entrypoint -- AUTO SEO generation, Notion sync, YouTube
upload, and Human Gate 2 dispatch, with ZERO manual "paste into Antigravity"
step. Added 23/08/2026 per user request; implements Skill AI Rule 119.

Flow:
  1. Load episode context (brain_input.json + Story Library row for the
     already-validated B1 keyword & breakout queries, Rule 117).
  2. Auto-call HHTech GPT-6-Astra (app.services.seo_package_forge) to generate
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

try:
    from app.services.youtube_upload import upload_from_payload
except ImportError:
    upload_from_payload = None

try:
    from app.services.youtube_thumbnail import set_thumbnail
except ImportError:
    set_thumbnail = None

try:
    from app.services.telegram_buttons import send_gate3_card
except ImportError:
    send_gate3_card = None
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


def _clean_and_localize_seo_description(desc: str, ep_dir: Path, market: str, title: str = "") -> str:
    """Ensure SEO description has NO 'Key topics & search queries' line, and chapters are dynamic/synchronized."""
    if not desc:
        return ""
    lines = desc.split("\n")
    cleaned_lines = []
    for line in lines:
        l_lower = line.strip().lower()
        if l_lower.startswith("key topics & search queries:") or l_lower.startswith("topics covered:"):
            continue
        cleaned_lines.append(line)

    desc_cleaned = "\n".join(cleaned_lines)

    # Rule 135: Synchronize exact YouTube chapters from remotion_props.json (Ground-Truth Timeline)
    try:
        from app.services.seo_package_forge import sync_exact_chapters_from_remotion
        
        # Extract existing chapters from description if present
        existing_ch = []
        ch_idx = desc_cleaned.find("Chapters:")
        if ch_idx != -1:
            ch_sub = desc_cleaned[ch_idx + len("Chapters:"):].strip()
            for ch_line in ch_sub.splitlines():
                ch_line_s = ch_line.strip()
                if not ch_line_s:
                    continue
                if ch_line_s.startswith("#") or "This video" in ch_line_s or "This story" in ch_line_s:
                    break
                if re.match(r'^\d{1,2}:\d{2}', ch_line_s):
                    existing_ch.append(ch_line_s)

        synced_ch = sync_exact_chapters_from_remotion(
            task_id=ep_dir.name,
            market=market,
            existing_chapters=existing_ch,
            ep_dir_path=str(ep_dir),
            title=title
        )

        if synced_ch:
            ch_block = "Chapters:\n" + "\n".join(synced_ch)
            if ch_idx != -1:
                head = desc_cleaned[:ch_idx].rstrip()
                tail = ""
                for sep in ["\n#", "\nThis video incorporates", "\nThis story and its"]:
                    s_idx = desc_cleaned.find(sep, ch_idx)
                    if s_idx != -1:
                        tail = desc_cleaned[s_idx:].lstrip()
                        break
                desc_cleaned = f"{head}\n\n{ch_block}\n\n{tail}".strip()
            else:
                desc_cleaned = f"{desc_cleaned}\n\n{ch_block}".strip()
    except Exception as e:
        print(f"[b10_seo] Chapter sync error: {e}")

    # Tầng 2: Multi-Language Description Bridge (cross_channel_promoter)
    try:
        from app.services.cross_channel_promoter import build_description_bridge
        bridge = build_description_bridge(market)
        if bridge and "Official Global Network" not in desc_cleaned and "公式グローバルネットワーク" not in desc_cleaned and "공식 글로벌" not in desc_cleaned:
            for sep in ["\nThis video incorporates", "\nThis story and its"]:
                if sep in desc_cleaned:
                    p1, p2 = desc_cleaned.split(sep, 1)
                    desc_cleaned = f"{p1.rstrip()}\n\n{bridge}\n\n{sep.lstrip()}{p2}"
                    break
            else:
                desc_cleaned = f"{desc_cleaned}\n\n{bridge}".strip()
    except Exception as e_br:
        print(f"[b10_seo] Description bridge error: {e_br}")

    return desc_cleaned


async def run(episode_id: str, market: str = "en", privacy_status: str = "unlisted", force_reupload: bool = False):
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    if not ep_dir.exists():
        raise FileNotFoundError(f"Episode directory not found: {ep_dir}")

    print(f"=== [B10-AUTO] 1. Loading episode context for {episode_id} ===")
    episode = _load_episode_context(episode_id, ep_dir)

    print("=== [B10-AUTO] 2. Loading Pre-Computed SEO Packaging (Zero-LLM Fast Upload) ===")
    seo_file = ep_dir / "seo_package.json"
    packaging = None
    if seo_file.exists():
        try:
            packaging = json.loads(seo_file.read_text(encoding="utf-8"))
            print(f"Loaded pre-computed SEO package from {seo_file} (Method: {packaging.get('generation_method')})")
        except Exception as e:
            print(f"Warning: failed reading {seo_file}: {e}")

    if not packaging:
        print("Checking Notion YouTube Registry for existing SEO package...")
        try:
            res = query_db(YOUTUBE_REGISTRY_DB_ID, filter_obj={"property": "Task ID", "rich_text": {"equals": episode_id}})
            if res.get("results"):
                p_row = res["results"][0].get("properties", {})
                def _g(prop):
                    return "".join(t.get("plain_text", "") for t in p_row.get(prop, {}).get("rich_text", []))
                t_a = _g("Title A")
                if t_a:
                    packaging = {
                        "task_id": episode_id,
                        "title_a": t_a,
                        "title_b": _g("Title B (Backup A/B)"),
                        "description": _g("SEO Description"),
                        "tags": [t.strip() for t in _g("Tags & Keywords").split(",") if t.strip()],
                        "hashtags": [h.strip() for h in _g("Hashtags").split() if h.strip()],
                        "hook_3s": _g("Hook Frame (0-3s)"),
                        "hook_frame_note": _g("Hook Frame (0-3s)"),
                        "thumbnail_variants": [],
                        "generation_method": _g("SEO Generation Method") or "notion_registry_cached"
                    }
                    print(f"Loaded existing SEO package from Notion YouTube Registry: {t_a}")
        except Exception as _qe:
            print(f"Notion registry lookup error: {_qe}")

    if not packaging:
        print("No pre-computed package found; invoking deterministic fallback packaging (Rule 118)")
        from app.services.seo_package_forge import _fallback_seo_package
        kw = episode.get("trend_keywords", [episode.get("niche")])[0] if episode.get("trend_keywords") else (episode.get("niche") or episode_id)
        packaging = _fallback_seo_package(
            task_id=episode_id,
            target_keyword=str(kw),
            market=market,
            niche_brief=episode.get("niche_angle_brief", "")
        )
    print(f"Generation method: {packaging.get('generation_method')}")

    packaging["description"] = _clean_and_localize_seo_description(
        packaging.get("description", ""),
        ep_dir,
        market,
        title=packaging.get("title_a", "")
    )

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
        "privacy_status": "unlisted",
        "contains_synthetic_media": True,
        "self_declared_made_for_kids": False,
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

    if video_id and not force_reupload:
        try:
            from app.services.youtube_upload import _build_client
            yt_client = _build_client(market=market)
            v_check = yt_client.videos().list(part="status", id=video_id).execute()
            if not v_check.get("items"):
                print(f"Warning: video_id={video_id} no longer exists on YouTube (deleted/removed). Invalidate and re-uploading...")
                video_id = None
        except Exception as _e_chk:
            print(f"Warning: failed checking YouTube video status: {_e_chk}")

    if video_id and not force_reupload:
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

    print("=== [B10-AUTO] 6. Thumbnail Step (Decoupled to HG3 / YouTube Studio Native Gemini) ===")
    thumb_path = _find_thumbnail_asset(ep_dir)
    if thumb_path:
        set_thumbnail(video_id, thumb_path, market=market)
    else:
        print("[B10] No dedicated thumbnail file found. Thumbnail creation is delegated to YouTube Studio Native Gemini AI at Human Gate 3.")

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

    print("=== [B10-AUTO] 7b. Smart Multi-Market Cross-Promotion Dispatch (Phương án A) ===")
    try:
        from app.services.cross_channel_promoter import dispatch_cross_promotion
        cross_res = dispatch_cross_promotion(
            video_id=video_id,
            market=market,
            episode_id=episode_id,
            title=packaging["title_a"],
        )
        print(f"[B10-CROSS-PROMOTION] Partner playlists distribution completed: {json.dumps(cross_res, ensure_ascii=False)}")
    except Exception as e_cross:
        print(f"[B10-CROSS-PROMOTION] Warning: Cross-promotion distribution skipped: {e_cross}")

    # Rule 125 Idempotency Gate: Prevent duplicate HG3 telegram card within 10 minutes
    hg3_marker = ep_dir / "hg3_dispatched.json"
    recent_dispatch = False
    if hg3_marker.exists():
        try:
            m_data = json.loads(hg3_marker.read_text(encoding="utf-8"))
            last_ts = m_data.get("timestamp_epoch", 0)
            if time.time() - last_ts < 600 and m_data.get("video_id") == video_id:
                recent_dispatch = True
                print(f"⚠️ [B10-AUTO] HG3 card already dispatched {int(time.time() - last_ts)}s ago for video {video_id}. Skipping duplicate Telegram message.")
        except Exception:
            pass

    if not recent_dispatch:
        print("=== [B10-AUTO] 8. Dispatching Human Gate 3 Telegram card (4 buttons) ===")
        if send_gate3_card:
            try:
                await send_gate3_card(
                    episode_id=episode_id,
                    video_id=video_id,
                    title_a=packaging.get("title_a", ""),
                    title_b=packaging.get("title_b", ""),
                    market=market,
                )
                hg3_marker.write_text(json.dumps({
                    "episode_id": episode_id,
                    "video_id": video_id,
                    "timestamp_epoch": time.time(),
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }, indent=2), encoding="utf-8")
                print("✅ [B10-AUTO] Human Gate 3 card dispatched successfully to Telegram.")
            except Exception as _tg_err:
                print(f"⚠️ [B10-AUTO] HG3 Telegram card dispatch non-fatal warning: {_tg_err}")
        else:
            print("⚠️ [B10-AUTO] send_gate3_card not available, skipping Telegram card.")
    # [POST-SYNC CLEANUP] Rule 125 & Post-Publish Disk Hygiene
    try:
        from scripts.post_sync_cleanup import cleanup_episode_intermediates
        clean_res = cleanup_episode_intermediates(episode_id)
        print(f"[B10-AUTO] Post-publish intermediate cleanup: {clean_res}")
    except Exception as _clean_err:
        print(f"[B10-AUTO] Post-publish cleanup non-fatal warning: {_clean_err}")

    print("B10-AUTO complete. No manual Antigravity paste step was required.")
    return {"video_id": video_id, "packaging": packaging}


def main():
    parser = argparse.ArgumentParser(description="Auto SEO + Upload + Gate2 (B10)")
    parser.add_argument("--episode", required=True, help="Episode ID, e.g. <MARKET>_EP<0000>_<topic_slug>")
    parser.add_argument("--market", default="en")
    parser.add_argument("--privacy", default="unlisted")
    parser.add_argument("--force-reupload", action="store_true", help="Force fresh upload to YouTube even if video_id exists")
    args = parser.parse_args()
    asyncio.run(run(args.episode, market=args.market, privacy_status=args.privacy, force_reupload=args.force_reupload))


if __name__ == "__main__":
    main()
