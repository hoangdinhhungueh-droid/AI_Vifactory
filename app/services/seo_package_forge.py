# -*- coding: utf-8 -*-
"""
Early B1.5 SEO & Narrative Hook Package Forge (seo_package_forge.py).
Part of AI Video Factory Pipeline (Step 1.6 / Post-B1.5 Stage).

Architecture:
  - Generates full SEO Package + 60s An Ong Hook + 3s Cold-Open + 10x Pivot Angle
    immediately after Step 1.5 Competitor Recon via HHTech GPT-6-Astra.
  - Persists package to disk (/var/vf/episodes/<task_id>/seo_package.json)
    and synchronizes dual-Notion SoT:
      1. YouTube Channel & Video Metadata Registry (3c301989-2400-81b9-a4bb-e5568ce942f8)
      2. Story Library (b0301989-2400-836b-bdb5-8131fea17736)
  - Passes pre-computed hook and title directly into B2 Story Engine to guarantee
    zero narrative drift (Act I anchors directly to the promised title & 60s hook).
  - Eliminates LLM calls in B10 Upload stage, loading pre-computed packaging directly.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from core.paths import resolve_episodes_dir, resolve_pending_tasks_dir

logger = logging.getLogger("vf.seo_package_forge")

def _episodes_base() -> Path:
    return Path(resolve_episodes_dir())

def _pending_base() -> Path:
    return Path(resolve_pending_tasks_dir())

EPISODES_BASE = _episodes_base()
PENDING_BASE = _pending_base()
YOUTUBE_REGISTRY_DB_ID = "3c301989-2400-81b9-a4bb-e5568ce942f8"
STORY_LIBRARY_DB_ID = "b0301989-2400-836b-bdb5-8131fea17736"

AI_DISCLOSURE_TEXT = (
    "This video incorporates AI-assisted research, synthetic voice narration, "
    "and stylized visual illustrations created under human editorial direction."
)

from app.services.cross_channel_promoter import build_description_bridge
from app.services.skill_loader import get_seo_editorial_skills


def get_seo_hook_system_prompt() -> str:
    """Load dynamic SEO packaging system prompt from Notion SoT / external template (Rule 132)."""
    return get_seo_editorial_skills()

# Backward-compatible module attribute
SEO_HOOK_SYSTEM_PROMPT = get_seo_hook_system_prompt()


def _parse_llm_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception as _e1:
        logger.debug("Direct json.loads failed in _parse_llm_json: %s", _e1)

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as _e2:
            logger.debug("Code block json.loads failed in _parse_llm_json: %s", _e2)

    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as _e3:
            logger.debug("Regex match json.loads failed in _parse_llm_json: %s", _e3)
    return {}


def _clean_hashtag(tag: str) -> str:
    tag = tag.strip()
    if not tag.startswith("#"):
        tag = "#" + tag
    # Remove whitespace and invalid characters
    return "#" + re.sub(r"[^\w]", "", tag[1:])


def _build_dynamic_chapters(
    title: str,
    market: str,
    target_keyword: str,
    total_duration_s: float = 720.0,
) -> list[str]:
    """Generate dynamic, localized 5-act chapters per episode without formulaic English placeholders."""
    m = (market or "EN").upper()
    dur = max(float(total_duration_s or 720.0), 180.0)

    # Proportional act timestamp offsets
    t_act1 = 0
    t_act2 = int(dur * 0.16)
    t_act3 = int(dur * 0.40)
    t_act4 = int(dur * 0.64)
    t_act5 = int(dur * 0.85)

    def _fmt(sec: int) -> str:
        mm = sec // 60
        ss = sec % 60
        return f"{mm:02d}:{ss:02d}"

    kw = (target_keyword or "").strip()
    if not kw and title:
        kw = title.split("｜")[0].split("|")[0].split(" - ")[0].strip()
    kw = kw or "Investigation"
    topic_clean = re.sub(r'[:|｜-].*$', '', kw).strip()[:24] or kw[:24]

    if m == "JP":
        return [
            f"{_fmt(t_act1)} - {topic_clean}の発端と疑惑",
            f"{_fmt(t_act2)} - 偽りの安全性となぜ起きたのか｜構造の歪み",
            f"{_fmt(t_act3)} - 流通と検査の死角｜隠された痕跡",
            f"{_fmt(t_act4)} - 動かぬ物証と基準超過の衝撃",
            f"{_fmt(t_act5)} - 越境する波紋と現代への警鐘",
        ]
    elif m == "KR":
        return [
            f"{_fmt(t_act1)} - {kw[:30]}: 사건의 발단과 의혹",
            f"{_fmt(t_act2)} - 왜 발생했는가｜은폐된 구조와 왜곡",
            f"{_fmt(t_act3)} - 유통과 검역의 사각지대｜추적된 기록",
            f"{_fmt(t_act4)} - 결정적 물증과 기준 초과의 충격",
            f"{_fmt(t_act5)} - 국경을 넘은 파문과 현대적 경고",
        ]
    else:  # Default EN and others
        return [
            f"{_fmt(t_act1)} - {kw[:35]}: The Catalyst & Initial Suspicions",
            f"{_fmt(t_act2)} - Why It Happened: The Architecture of Concealment",
            f"{_fmt(t_act3)} - Blind Spots in Inspection: The Paper Trail",
            f"{_fmt(t_act4)} - Incontrovertible Evidence: The Shock of Standard Violation",
            f"{_fmt(t_act5)} - Cross-Border Repercussions & Modern Warning",
        ]


def sync_exact_chapters_from_remotion(
    task_id: str = "",
    market: str = "EN",
    existing_chapters: list = None,
    ep_dir_path: str = None,
    title: str = "",
    target_keyword: str = "",
    total_duration_s: float = 720.0,
    remotion_props_path: str = None,
) -> list[str]:
    """Rule 135: Synchronize YouTube chapters with exact frame-accurate timestamps from remotion_props.json.
    Ground-Truth Video Timeline:
      1. First chapter is always 00:00.
      2. Timestamps match the actual rendered video timeline (current_frame / fps).
      3. Preserves localized/creative chapter titles from LLM or existing package.
      4. Falls back gracefully to proportional durations if remotion_props.json is not yet available.
    """
    m = (market or "EN").upper()
    if existing_chapters and isinstance(existing_chapters, str):
        existing_chapters = [line.strip() for line in existing_chapters.splitlines() if line.strip()]

    def _sanitize_chapter_label(label: str, market_code: str = "EN") -> str:
        """Purge sensitive judicial/criminal terms without cross-market language pollution (Rule 128/135)."""
        jp_banned = r'(起訴状記録|起訴事実認定|刑事摘発|司法審査|起訴|刑事|摘発|容疑者)'
        kr_banned = r'(기소장|공소장|형사\s*적발|사법\s*심사|기소|형사|적발|용의자|검찰)'
        en_banned = r'(GRAND JURY|INDICTMENT|PROSECUTOR|CRIMINAL)'

        # Japanese keywords -> 検査・行政指導
        res = re.sub(jp_banned, '検査・行政指導', label)
        # Korean keywords -> 행정 조사
        res = re.sub(kr_banned, '행정 조사', res)
        # English keywords -> REGULATORY INQUIRY (or market native if chapter is in CJK)
        m_code = (market_code or "EN").upper()
        if m_code in ("JP", "JA") and re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', res):
            res = re.sub(en_banned, '検査・行政指導', res, flags=re.IGNORECASE)
        elif m_code in ("KR", "KO") and re.search(r'[\uac00-\ud7a3]', res):
            res = re.sub(en_banned, '행정 조사', res, flags=re.IGNORECASE)
        else:
            res = re.sub(en_banned, 'REGULATORY INQUIRY', res, flags=re.IGNORECASE)
        return res

    # 1. Locate remotion_props.json
    candidates = []
    # Prioritize Vox canonical pipeline manifest (Rule 125 Single Truth & Rule 135)
    if ep_dir_path:
        candidates.append(os.path.join(ep_dir_path, "manifest.json"))
    if task_id:
        ep_dir = _episodes_base() / task_id
        candidates.extend([
            str(ep_dir / "manifest.json"),
        ])
    if remotion_props_path:
        candidates.append(str(remotion_props_path))
    if ep_dir_path:
        candidates.append(os.path.join(ep_dir_path, "remotion_props.json"))
    if task_id and (str(task_id).endswith(".json") or os.path.isfile(str(task_id))):
        candidates.insert(0, str(task_id))
    if task_id:
        ep_dir = _episodes_base() / task_id
        candidates.extend([
            str(ep_dir / "remotion_props.json"),
        ])

    remotion_path = None
    for cand in candidates:
        if os.path.exists(cand):
            remotion_path = cand
            break

    exact_timestamps = []
    total_dur_s = float(total_duration_s or 720.0)

    if remotion_path:
        try:
            with open(remotion_path, "r", encoding="utf-8") as rf:
                rdata = json.load(rf)
            scenes = rdata.get("scenes", [])
            fps = float(rdata.get("fps") or 30.0)
            is_vox_manifest = any("start" in sc for sc in scenes if isinstance(sc, dict))
            if scenes:
                current_frame = 0
                last_beat_key = None
                distinct_beats = {
                    int(sc.get("beat_phase") or sc.get("beat_index") or sc.get("beat"))
                    for sc in scenes
                    if str(sc.get("beat_phase") or sc.get("beat_index") or sc.get("beat") or "").isdigit()
                }
                is_degenerate_beat = (
                    (len(scenes) >= 5 and len(distinct_beats) == 1)
                    or (max(distinct_beats, default=1) > 5)
                )

                for idx, s in enumerate(scenes):
                    speaker_tag = str(s.get("speakerTag") or "")
                    beat_val = s.get("beat_phase") or s.get("beat_index") or s.get("beat")
                    act_title = str(s.get("actTitle") or "")

                    # Extract canonical beat key (prioritize integer beat_phase 1..5 so character speakerTags don't trigger false chapter splits)
                    current_beat_key = None
                    if not is_degenerate_beat and beat_val is not None:
                        try:
                            b_int = int(beat_val)
                            if 1 <= b_int <= 5:
                                current_beat_key = f"BEAT {b_int}"
                        except (ValueError, TypeError) as _ve:
                            logger.debug("Non-integer beat_val %r in scene %s: %s", beat_val, idx, _ve)
                    if not current_beat_key and is_degenerate_beat:
                        pct = (idx + 1) / max(1, len(scenes))
                        b_auto = 1 if pct <= 0.15 else (2 if pct <= 0.40 else (3 if pct <= 0.65 else (4 if pct <= 0.85 else 5)))
                        current_beat_key = f"BEAT {b_auto}"
                    if not current_beat_key:
                        beat_match = re.search(r'\b(BEAT\s*\d+|ACT\s*[IVXLCDM]+)\b', f"{speaker_tag} {beat_val or ''} {act_title}", re.IGNORECASE)
                        if beat_match:
                            current_beat_key = re.sub(r'\s+', ' ', beat_match.group(1).upper()).strip()
                        elif beat_val:
                            current_beat_key = f"BEAT {beat_val}"
                        else:
                            current_beat_key = act_title or f"SCENE_{idx}"

                    if is_vox_manifest and "start" in s:
                        sec = int(float(s["start"]))
                        dur = int(round((float(s.get("end", s["start"])) - float(s["start"])) * fps))
                    else:
                        dur = int(s.get("durationInFrames") or 0)
                        sec = int(current_frame / fps)

                    if current_beat_key != last_beat_key or idx == 0:
                        # Ensure YouTube constraint: chapters at least 10s apart (Rule 135)
                        if not exact_timestamps:
                            exact_timestamps.append(0)
                            last_beat_key = current_beat_key
                        elif sec >= exact_timestamps[-1] + 10:
                            exact_timestamps.append(sec)
                            last_beat_key = current_beat_key

                    current_frame += dur

                # If still over 16 chapters, thin out by merging closest chapters
                while len(exact_timestamps) > 16:
                    # Drop the chapter with the smallest gap from its predecessor (skip 00:00)
                    min_gap_idx = 1
                    min_gap = exact_timestamps[1] - exact_timestamps[0]
                    for g_i in range(2, len(exact_timestamps)):
                        gap = exact_timestamps[g_i] - exact_timestamps[g_i - 1]
                        if gap < min_gap:
                            min_gap = gap
                            min_gap_idx = g_i
                    exact_timestamps.pop(min_gap_idx)

                if current_frame > 0:
                    total_dur_s = current_frame / fps
        except Exception as e:
            logger.warning("[seo_package_forge] Error reading remotion_props: %s", e)

    def _fmt(sec: int) -> str:
        mm = sec // 60
        ss = sec % 60
        return f"{mm:02d}:{ss:02d}"

    # 2. If we got exact timestamps (at least 3 chapters for valid YouTube chapters)
    if len(exact_timestamps) >= 3:
        if existing_chapters and isinstance(existing_chapters, list):
            clean_titles = []
            for ch in existing_chapters:
                ch_str = str(ch).strip()
                title_clean = re.sub(r'^\d{1,2}:\d{2}(?::\d{2})?\s*[-:]?\s*', '', ch_str).strip()
                if title_clean:
                    title_clean = _sanitize_chapter_label(title_clean, m)
                    clean_titles.append(title_clean)

            if len(clean_titles) >= len(exact_timestamps):
                return [f"{_fmt(exact_timestamps[i])} - {clean_titles[i]}" for i in range(len(exact_timestamps))]
            elif len(clean_titles) >= 3:
                n = min(len(clean_titles), len(exact_timestamps))
                return [f"{_fmt(exact_timestamps[i])} - {clean_titles[i]}" for i in range(n)]

        fallback_chapters = _build_dynamic_chapters(title or "Investigation", m, target_keyword or title, total_duration_s=total_dur_s)
        clean_fallback_titles = [_sanitize_chapter_label(re.sub(r'^\d{1,2}:\d{2}\s*[-:]?\s*', '', c).strip(), m) for c in fallback_chapters]
        n = min(len(clean_fallback_titles), len(exact_timestamps))
        return [f"{_fmt(exact_timestamps[i])} - {clean_fallback_titles[i]}" for i in range(n)]

    # 3. Fallback: remotion_props.json not found or fewer than 3 scenes -> use proportional dynamic chapters
    if existing_chapters and len(existing_chapters) >= 3:
        return [_sanitize_chapter_label(str(c).strip(), m) for c in existing_chapters if str(c).strip()]
    return _build_dynamic_chapters(title or "Investigation", m, target_keyword or title, total_duration_s=total_dur_s)


def _fallback_seo_package(
    task_id: str,
    target_keyword: str,
    market: str,
    niche_brief: str = "",
    competitor_gap: str = "",
    rising_queries: list = None
) -> dict:
    """Deterministic fallback if HHTech API or JSON parse fails. Guarantees zero pipeline stall without keyword stuffing."""
    raw_kw = (target_keyword or "Investigative Case").strip()
    kw_words = raw_kw.split()
    kw = " ".join(kw_words[:4]) if len(kw_words) > 4 else raw_kw
    clean_tag = re.sub(r"[^\w]", "", kw.title()) or "Documentary"

    title_a = f"{kw}: The Hidden Investigation"[:100]
    title_b = f"{kw}: What Official Reports Concealed"[:100]
    desc_hook = f"The untold investigative documentary behind {kw}. Exposing the systemic evidence and critical turning points."[:150]

    hashtags = [f"#{clean_tag}", "#Investigation", "#Docudrama"][:3]
    tags = [kw, f"{kw} documentary", f"{kw} investigation", "investigative docudrama", "unfiltered facts", market.lower()]

    hook_3s = f"Everything you were told about {kw} ignores a single, undeniable contradiction."
    hook_60s = (
        f"In the official records of {kw}, the narrative appeared settled. "
        f"Yet beneath the publicized headlines lies an unresolved conflict that investigators struggled to explain. "
        f"When we examined the evidentiary timeline and systemic blindspots, the contradictions could no longer be dismissed. "
        f"This 15-minute investigation uncovers the smoking gun evidence, the key beneficiaries, "
        f"and the enduring truth that public records left in the dark."
    )
    if competitor_gap:
        clean_gap = re.sub(r"[\r\n]+", " ", competitor_gap).strip()
        first_sent = clean_gap.split(".")[0].strip()
        angle = first_sent[:120] if first_sent else f"Exposing the systemic institutional mechanisms behind {kw}"
    else:
        angle = f"Exposing the systemic institutional mechanisms behind {kw}"

    thumbnail_variants = [
        {"variant": "A", "framework": "emotion_first", "headline_text": "THEY HID THIS"[:32], "visual_concept": "High-contrast dramatic lighting focusing on confidential investigative records."},
        {"variant": "B", "framework": "keyword_first", "headline_text": f"{kw.upper()[:32]}", "visual_concept": "Central focal illustration of the primary subject under intense forensic spotlight."},
        {"variant": "C", "framework": "curiosity_gap", "headline_text": "THE FATAL LIE"[:32], "visual_concept": "Split composition contrasting official reports with unredacted leaked memos."}
    ]

    chapters_lines = sync_exact_chapters_from_remotion(task_id, market, title=title_a, target_keyword=kw)

    desc_parts = [
        desc_hook,
        "",
        "Chapters:",
        *chapters_lines,
        "",
        " ".join(hashtags),
        "",
        build_description_bridge(market),
        "",
        AI_DISCLOSURE_TEXT
    ]

    return {
        "task_id": task_id,
        "market": market.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_method": "deterministic_b15_fallback",
        "title_a": title_a,
        "title_b": title_b,
        "description": "\n".join(desc_parts).strip()[:5000],
        "description_hook": desc_hook,
        "hashtags": hashtags,
        "tags": tags,
        "hook_3s": hook_3s,
        "hook_60s": hook_60s,
        "specific_viral_angle": angle,
        "thumbnail_variants": thumbnail_variants,
        "end_screen_notes": {
            "point_1_intro": "~3:00 -- series/channel branding overlay",
            "point_2_70pct": "70% duration -- playlist/related episode overlay",
            "point_3_last_20s": "last 20s -- next-episode CTA + subscribe"
        },
        "ai_disclosure": True,
        "made_for_kids": False,
        "is_fallback": True
    }


def _rt(content: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": (content or "")[:2000]}}]}


def sync_seo_package_to_youtube_registry(task_id: str, market: str, package: dict) -> dict:
    """Upsert SEO package into DB 'YouTube Channel & Video Metadata Registry' (3c301989-2400-81b9-a4bb-e5568ce942f8)."""
    try:
        from scripts.ag_notion_bridge import create_page, query_db, update_page_properties
    except ImportError:
        logger.warning("[seo_package_forge] ag_notion_bridge not available for YouTube Registry sync")
        return {"action": "skipped", "error": "ag_notion_bridge_import_error"}

    thumb_summary = "\n".join(
        f"{v.get('variant')} ({v.get('framework')}): {v.get('headline_text')} -- {v.get('visual_concept')}"
        for v in package.get("thumbnail_variants", [])
    )
    end_screen = package.get("end_screen_notes", {})
    end_screen_summary = " | ".join(f"{k}: {v}" for k, v in end_screen.items())

    props = {
        "Title A": _rt(package.get("title_a", "")),
        "Title B (Backup A/B)": _rt(package.get("title_b", "")),
        "Tags & Keywords": _rt(", ".join(package.get("tags", []))),
        "SEO Description": _rt(package.get("description", "")),
        "Hashtags": _rt(" ".join(package.get("hashtags", []))),
        "Hook Frame (0-3s)": _rt(package.get("hook_3s", "")),
        "End Screen (3 diem)": _rt(end_screen_summary or thumb_summary),
        "SEO Generation Method": _rt(package.get("generation_method", "")),
        "AI Generated Disclosure": {"checkbox": True},
        "Market": {"select": {"name": market.upper()}},
        "Task ID": _rt(task_id),
        "Publish Status": {"select": {"name": "Pending Upload"}},
    }

    try:
        existing = query_db(
            YOUTUBE_REGISTRY_DB_ID,
            filter_obj={"property": "Task ID", "rich_text": {"equals": task_id}}
        )
        rows = existing.get("results", []) if isinstance(existing, dict) else []
        if rows:
            page_id = rows[0]["id"]
            update_page_properties(page_id, props)
            logger.info(f"[seo_package_forge] Updated YouTube Registry row {page_id} for {task_id}")
            return {"action": "updated", "page_id": page_id}

        props["Name"] = {"title": [{"type": "text", "text": {"content": f"{task_id} · {package.get('title_a', '')[:80]}"}}]}
        created = create_page(YOUTUBE_REGISTRY_DB_ID, props)
        page_id = created.get("id") if isinstance(created, dict) else None
        logger.info(f"[seo_package_forge] Created YouTube Registry row {page_id} for {task_id}")
        return {"action": "created", "page_id": page_id}
    except Exception as e:
        logger.warning(f"[seo_package_forge] Failed to sync to YouTube Registry: {e}")
        return {"action": "error", "error": str(e)}


def sync_seo_package_to_story_library(task_id: str, package: dict, story_page_id: str = None) -> dict:
    """Upsert SEO package into DB 'Story Library' (b0301989-2400-836b-bdb5-8131fea17736)."""
    try:
        from scripts.ag_notion_bridge import query_db, update_page_properties
    except ImportError:
        logger.warning("[seo_package_forge] ag_notion_bridge not available for Story Library sync")
        return {"action": "skipped", "error": "ag_notion_bridge_import_error"}

    thumb_summary = "\n".join(
        f"{v.get('variant')} ({v.get('framework')}): {v.get('headline_text')} -- {v.get('visual_concept')}"
        for v in package.get("thumbnail_variants", [])
    )
    end_screen = package.get("end_screen_notes", {})
    end_screen_summary = " | ".join(f"{k}: {v}" for k, v in end_screen.items())

    props = {
        "SEO Title A": _rt(package.get("title_a", "")),
        "SEO Title B": _rt(package.get("title_b", "")),
        "SEO Description": _rt(package.get("description", "")),
        "SEO Tags": _rt(", ".join(package.get("tags", []))),
        "SEO Hashtags": _rt(" ".join(package.get("hashtags", []))),
        "Thumbnail Variants (A/B/C)": _rt(thumb_summary),
        "Hook Frame Note": _rt(package.get("hook_3s", "")),
        "End Screen Notes": _rt(end_screen_summary),
        "SEO Generation Method": _rt(package.get("generation_method", "")),
    }

    try:
        page_id = story_page_id
        if not page_id:
            existing = query_db(
                STORY_LIBRARY_DB_ID,
                filter_obj={"property": "Task ID", "rich_text": {"equals": task_id}}
            )
            rows = existing.get("results", []) if isinstance(existing, dict) else []
            if rows:
                page_id = rows[0]["id"]

        if page_id:
            update_page_properties(page_id, props)
            logger.info(f"[seo_package_forge] Updated Story Library row {page_id} for {task_id}")
            return {"action": "updated", "page_id": page_id}
        else:
            logger.info(f"[seo_package_forge] Story Library row for {task_id} not found yet -- properties ready for B2 creation")
            return {"action": "pending_b2_creation"}
    except Exception as e:
        logger.warning(f"[seo_package_forge] Failed to sync to Story Library: {e}")
        return {"action": "error", "error": str(e)}


def forge_seo_package(
    task_id: str,
    target_keyword: str,
    market: str = "EN",
    niche_brief: str = "",
    competitor_gap: str = "",
    rising_queries: list = None,
    breakout_queries: list = None,
    competitor_card: dict = None,
    story_page_id: str = None,
    grounding_intel: dict = None,
    total_duration_s: float = 720.0,
) -> dict:
    """Forge complete SEO Package and 60s An Ong Hook right after Step 1.5.

    1. Calls HHTech GPT-6-Astra with rich context (target_keyword, niche, competitor gap, rising queries, verified ground facts).
    2. Enforces deterministic length, hashtag cap (exactly 3), and tag budget (<=400 chars).
    3. Persists package to /var/vf/episodes/<task_id>/seo_package.json.
    4. Upserts to YouTube Registry DB and Story Library DB in Notion SoT.
    5. Returns normalized dictionary ready for B2 Story Engine injection and B10 Upload reuse.
    """
    m_up = (market or "EN").upper()
    kw = (target_keyword or "").strip()
    rq = rising_queries or []
    bq = breakout_queries or []
    comp_gap = competitor_gap or ""

    if competitor_card and not comp_gap:
        anatomy = competitor_card.get("competitor_narrative_anatomy") or {}
        comp_gap = anatomy.get("fatal_explanatory_vacuum") or competitor_card.get("competitor_gap", "")

    # Load grounding intel if not explicitly passed
    if not grounding_intel:
        cand = os.path.join(_episodes_base(), task_id, "grounding_intel.json")
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as gf:
                    grounding_intel = json.load(gf)
            except Exception as _ge:
                logger.debug(f"[seo_package_forge] Could not read grounding intel from {cand}: {_ge}")

    verified_facts = []
    if grounding_intel and isinstance(grounding_intel, dict):
        for c in grounding_intel.get("claims", []):
            claim_text = c.get("claim", "").strip()
            src = c.get("source", "").strip()
            dt = c.get("date", "").strip()
            role = c.get("causal_role", "")
            if claim_text:
                prefix = f"[{dt}] " if dt else ""
                suffix = f" (Source: {src}, Role: {role})" if src else ""
                verified_facts.append(f"{prefix}{claim_text}{suffix}")

    user_payload = {
        "task_id": task_id,
        "market": m_up,
        "target_keyword": kw,
        "niche_angle_brief": niche_brief,
        "competitor_fatal_gap": comp_gap,
        "rising_queries": rq[:6],
        "breakout_queries": bq[:4]
    }
    if grounding_intel and isinstance(grounding_intel, dict):
        if grounding_intel.get("temporal_cadence"):
            user_payload["temporal_cadence"] = grounding_intel["temporal_cadence"]
        if grounding_intel.get("causal_epochs"):
            user_payload["causal_epochs"] = grounding_intel["causal_epochs"]
    if verified_facts:
        user_payload["verified_ground_facts"] = verified_facts[:6]

    user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)

    parsed_llm = None
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[seo_package_forge] Attempt {attempt}/{max_retries} calling GPT-6-Astra for {task_id}...")
            from app.services.hhtech_reasoner import call_gpt6_astra
            raw = call_gpt6_astra(
                prompt=user_prompt,
                system_prompt=get_seo_hook_system_prompt(),
                max_tokens=2200,
                timeout=75.0
            )
            parsed = _parse_llm_json(raw)
            if parsed and isinstance(parsed, dict) and parsed.get("title_a"):
                parsed_llm = parsed
                logger.info(f"[seo_package_forge] Successfully forged SEO package on attempt {attempt}")
                break
            else:
                logger.warning(f"[seo_package_forge] Attempt {attempt} returned invalid schema/missing title_a")
        except Exception as e:
            logger.warning(f"[seo_package_forge] Attempt {attempt} failed: {e}")

        if attempt < max_retries:
            time.sleep(2 ** attempt)

    if not parsed_llm or not parsed_llm.get("title_a"):
        logger.warning(f"[seo_package_forge] All {max_retries} LLM attempts failed for {task_id}. Activating deterministic fallback.")
        package = _fallback_seo_package(
            task_id=task_id,
            target_keyword=kw,
            market=m_up,
            niche_brief=niche_brief,
            competitor_gap=comp_gap,
            rising_queries=rq
        )
    else:
        # Deterministic constraint enforcement
        raw_title_a = str(parsed_llm.get("title_a") or f"{kw} | Investigation").strip()
        # KVS check: ensure primary keyword is in title_a
        if kw.lower() not in raw_title_a.lower():
            title_a = f"{kw} | {raw_title_a}"[:100]
        else:
            title_a = raw_title_a[:100]

        title_b = str(parsed_llm.get("title_b") or title_a)[:100]

        # Clean description hook
        desc_hook = str(parsed_llm.get("description_hook") or "").strip()
        for banned in ("in this video", "welcome to"):
            if desc_hook.lower().startswith(banned):
                desc_hook = desc_hook.split(" ", 2)[-1]
        desc_hook = desc_hook[:150] or f"The untold investigative documentary behind {kw}."

        # Strict 3 hashtags
        raw_hts = parsed_llm.get("hashtags") or []
        cleaned_hts = []
        for h in raw_hts:
            cleaned = _clean_hashtag(str(h))
            if cleaned and cleaned not in cleaned_hts:
                cleaned_hts.append(cleaned)
        if len(cleaned_hts) < 3:
            kw_tag = _clean_hashtag(kw.title())
            for extra in [kw_tag, "#Investigation", "#Docudrama"]:
                if extra not in cleaned_hts:
                    cleaned_hts.append(extra)
                if len(cleaned_hts) == 3:
                    break
        hashtags = cleaned_hts[:3]

        # Tags within 400-char budget
        raw_tags = parsed_llm.get("tags") or []
        tags_list = []
        cur_len = 0
        for t in raw_tags:
            t_clean = str(t).strip()
            if t_clean and t_clean not in tags_list:
                if cur_len + len(t_clean) + 2 <= 400:
                    tags_list.append(t_clean)
                    cur_len += len(t_clean) + 2
        if not tags_list:
            tags_list = [kw, f"{kw} documentary", "investigative docudrama", m_up.lower()]

        # Narrative hooks
        hook_3s = str(parsed_llm.get("hook_3s") or f"Everything you knew about {kw} is built on a contradiction.").strip()
        hook_60s = str(parsed_llm.get("hook_60s") or "").strip()
        is_cjk_pkg = m_up in ("JP", "JA", "KR", "KO", "ZH")
        is_hook_too_short = (len(hook_60s) < 60) if is_cjk_pkg else (len(hook_60s.split()) < 30)

        if is_hook_too_short:
            if m_up in ("JP", "JA"):
                hook_60s = (
                    f"{kw}に関する第一報が報じられた当初、その公式発表を疑う者はほとんどいませんでした。"
                    f"しかし組織の内部記録を精査すると、公式見解と真っ向から矛盾する重大な証拠の異常値が浮上しました。"
                    f"本調査ドキュメンタリーは、隠蔽された動機、追跡された記録、そして全てを覆す構造的真実を徹底解明します。"
                )
            elif m_up in ("KR", "KO"):
                hook_60s = (
                    f"{kw}에 관한 최초 보도가 나왔을 때, 공식 발표에 의문을 제기한 사람은 거의 없었습니다. "
                    f"그러나 내부 기록을 추적한 결과, 공식 결론과 정면으로 배치되는 결정적인 증거 이상징후가 드러났습니다. "
                    f"본 탐사 다큐멘터리는 은폐된 동기와 추적된 기록, 그리고 모든 것을 재평가하게 만드는 구조적 진실을 파헤칩니다."
                )
            else:
                hook_60s = (
                    f"When the initial reports regarding {kw} surfaced, few questioned the public narrative. "
                    f"Yet deep inside institutional records, an evidentiary anomaly emerged that contradicted official findings. "
                    f"This investigation explores the forensic paper trail, the concealed motives, and the systemic revelation "
                    f"that forces a re-examination of everything on record."
                )

        angle = str(parsed_llm.get("specific_viral_angle") or comp_gap or f"Exposing the systemic truth of {kw}").strip()

        # Thumbnail variants
        thumbs = parsed_llm.get("thumbnail_variants") or []
        if len(thumbs) < 3:
            thumbs = [
                {"variant": "A", "framework": "emotion_first", "headline_text": "THEY LIED"[:32], "visual_concept": "High-contrast dramatic lighting."},
                {"variant": "B", "framework": "keyword_first", "headline_text": f"{kw.upper()[:32]}", "visual_concept": "Primary subject under intense spotlight."},
                {"variant": "C", "framework": "curiosity_gap", "headline_text": "FATAL EVIDENCE"[:32], "visual_concept": "Split screen contrasting official claim with evidence."}
            ]

        # Assemble full description (dynamic 5 acts chapter outline + hashtags + disclosure)
        chapters = parsed_llm.get("chapters")
        chapter_lines = []
        if chapters and isinstance(chapters, list):
            for ch in chapters:
                if isinstance(ch, dict) and ch.get("title"):
                    ts = ch.get("timestamp") or ch.get("time") or ch.get("start") or "00:00"
                    chapter_lines.append(f"{ts} - {ch['title']}")
                elif isinstance(ch, str) and ch.strip():
                    chapter_lines.append(ch.strip())
        chapter_lines = sync_exact_chapters_from_remotion(
            task_id=task_id,
            market=m_up,
            existing_chapters=chapter_lines,
            title=title_a,
            target_keyword=kw,
            total_duration_s=total_duration_s
        )

        desc_parts = [
            desc_hook,
            "",
            "Chapters:",
            *chapter_lines,
            "",
            " ".join(hashtags),
            "",
            build_description_bridge(m_up),
            "",
            AI_DISCLOSURE_TEXT
        ]

        package = {
            "task_id": task_id,
            "market": m_up,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_method": "hhtech_gpt6astra_b15_forge",
            "title_a": title_a,
            "title_b": title_b,
            "description": "\n".join(desc_parts).strip()[:5000],
            "description_hook": desc_hook,
            "hashtags": hashtags,
            "tags": tags_list,
            "hook_3s": hook_3s,
            "hook_60s": hook_60s,
            "specific_viral_angle": angle,
            "thumbnail_variants": thumbs,
            "end_screen_notes": parsed_llm.get("end_screen_notes") or {
                "point_1_intro": "~3:00 -- series/channel branding overlay",
                "point_2_70pct": "70% duration -- playlist/related episode overlay",
                "point_3_last_20s": "last 20s -- next-episode CTA + subscribe"
            },
            "ai_disclosure": True,
            "made_for_kids": False,
            "is_fallback": False
        }

    # 1. Save to canonical episodes dir
    try:
        ep_dir = _episodes_base() / task_id
        ep_dir.mkdir(parents=True, exist_ok=True)
        pkg_path = ep_dir / "seo_package.json"
        with open(pkg_path, "w", encoding="utf-8") as f:
            json.dump(package, f, ensure_ascii=False, indent=2)
        logger.info(f"[seo_package_forge] Saved SEO package to {pkg_path}")
    except Exception as _fe:
        logger.warning(f"[seo_package_forge] Could not write package to {_episodes_base()}: {_fe}")

    # 2. Update pending task JSON if present
    try:
        pending_file = PENDING_BASE / f"{task_id}.json"
        if pending_file.exists():
            data = json.loads(pending_file.read_text(encoding="utf-8"))
            data["seo_package"] = package
            data["title_a"] = package["title_a"]
            data["title_b"] = package["title_b"]
            data["hook_3s"] = package["hook_3s"]
            data["hook_60s"] = package["hook_60s"]
            data["specific_viral_angle"] = package["specific_viral_angle"]
            pending_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"[seo_package_forge] Augmented pending task file: {pending_file}")
    except Exception as _pe:
        logger.warning(f"[seo_package_forge] Could not augment pending task: {_pe}")

    # 3. Dual-Notion SoT Synchronization
    try:
        sync_seo_package_to_youtube_registry(task_id, m_up, package)
    except Exception as _ye:
        logger.warning(f"[seo_package_forge] YouTube registry sync failed: {_ye}")

    try:
        sync_seo_package_to_story_library(task_id, package, story_page_id=story_page_id)
    except Exception as _se:
        logger.warning(f"[seo_package_forge] Story library sync failed: {_se}")

    return package
