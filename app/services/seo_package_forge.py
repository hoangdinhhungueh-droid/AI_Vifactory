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

import os
import sys
import json
import time
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("vf.seo_package_forge")

EPISODES_BASE = Path("/var/vf/episodes")
PENDING_BASE = Path("/var/vf/pending_tasks")
YOUTUBE_REGISTRY_DB_ID = "3c301989-2400-81b9-a4bb-e5568ce942f8"
STORY_LIBRARY_DB_ID = "b0301989-2400-836b-bdb5-8131fea17736"

AI_DISCLOSURE_TEXT = (
    "This video incorporates AI-assisted research, synthetic voice narration, "
    "and stylized visual illustrations created under human editorial direction."
)

SEO_HOOK_SYSTEM_PROMPT = """You are the Packaging & Narrative Hook Director for Video Factory.
Your mission: Given the target keyword, market, niche brief, and competitor narrative gap from B1.5 Recon, forge the complete YouTube SEO Package and opening Narrative Contract for the episode.

Strict Constraints (Skill AI Packaging & Rule 444 An Ong Hook):
1. TITLE A (KVS method): The primary keyword MUST lead or feature prominently at the front. Compelling curiosity gap or emotional contradiction. Maximum 100 characters (optimal 60-70).
2. TITLE B (Backup A/B): Alternate emotional, mystery, or curiosity-gap angle for A/B testing. Maximum 100 characters.
3. DESCRIPTION: Front-loaded 2-line hook (<=150 chars). NEVER start with "In this video" or "Welcome".
4. HASHTAGS: Exactly 3 high-intent hashtags (#Tag1 #Tag2 #Tag3). Cap strictly at 3.
5. TAGS: High-value SEO tags within a 400-character budget (max 7-10 tags).
6. 3-SECOND COLD OPEN (hook_3s): The single most startling visual or contradiction statement (0-3s).
7. 60-SECOND NARRATIVE HOOK (hook_60s): An Ong narrative contract (Rule 444 & Rule 130). A 90-130 word opening monologue for Act I setting up the quantitative shock, leading directly with the Level 1 Primary Catalyst (verified dates, events, numbers), the systemic contradiction, and the core puzzle. STRICTLY FORBIDDEN: Starting with 'Now imagine...', 'Imagine a world...', or hypothetical hand-waving. Lead with real, verifiable stakes.
8. SPECIFIC VIRAL ANGLE (specific_viral_angle): The 10x pivot angle directly exploiting the competitor's fatal explanatory vacuum.
9. THUMBNAIL A/B/C: Exactly 3 distinct copywriting variants:
   - Variant A = emotion_first: Short emotional punch headline (<=32 chars, UPPERCASE).
   - Variant B = keyword_first: Primary keyword-led headline (<=32 chars, UPPERCASE).
   - Variant C = curiosity_gap: Counter-intuitive paradox or number (<=32 chars, UPPERCASE).
   Each with a 1-sentence visual_concept.
10. END SCREEN: 3 timing markers (~3:00 branding, 70% playlist, last 20s CTA).
11. ANTI-FACT-DENIAL & TEMPORAL INTEGRITY (RULE 130 MANDATE):
    - NEVER dismiss verified contemporary events or crisis data (e.g. 2026 traffic drops, military declarations, insurance surges) as 'hypotheses' or 'unauthenticated propositions'.
    - NEVER retreat into past decades (e.g. 2019 Front Altair) as the primary subject of a contemporary search query.
    - Historical precedents may ONLY be referenced as comparative mechanisms to explain the legal/financial transmission chain, NEVER to displace or deny contemporary crisis events.

Return ONLY valid JSON matching this schema:
{
  "title_a": "<title with keyword, <=100 chars>",
  "title_b": "<alternate title, <=100 chars>",
  "description_hook": "<2 lines, <=150 chars, no In this video/Welcome>",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3"],
  "tags": ["tag1", "tag2", "tag3"],
  "hook_3s": "<0-3s cold open statement>",
  "hook_60s": "<60s An Ong narrative contract 90-130 words>",
  "specific_viral_angle": "<10x pivot angle>",
  "thumbnail_variants": [
    {"variant": "A", "framework": "emotion_first", "headline_text": "<<=32 chars UPPERCASE>", "visual_concept": "<1 sentence>"},
    {"variant": "B", "framework": "keyword_first", "headline_text": "<<=32 chars UPPERCASE>", "visual_concept": "<1 sentence>"},
    {"variant": "C", "framework": "curiosity_gap", "headline_text": "<<=32 chars UPPERCASE>", "visual_concept": "<1 sentence>"}
  ],
  "end_screen_notes": {
    "point_1_intro": "~3:00 -- series/channel branding overlay",
    "point_2_70pct": "70% duration -- playlist/related episode overlay",
    "point_3_last_20s": "last 20s -- next-episode CTA + subscribe"
  }
}"""


def _parse_llm_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return {}


def _clean_hashtag(tag: str) -> str:
    tag = tag.strip()
    if not tag.startswith("#"):
        tag = "#" + tag
    # Remove whitespace and invalid characters
    return "#" + re.sub(r"[^\w]", "", tag[1:])


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
        {"variant": "A", "framework": "emotion_first", "headline_text": f"THEY HID THIS"[:32], "visual_concept": "High-contrast dramatic lighting focusing on confidential investigative records."},
        {"variant": "B", "framework": "keyword_first", "headline_text": f"{kw.upper()[:32]}", "visual_concept": "Central focal illustration of the primary subject under intense forensic spotlight."},
        {"variant": "C", "framework": "curiosity_gap", "headline_text": "THE FATAL LIE"[:32], "visual_concept": "Split composition contrasting official reports with unredacted leaked memos."}
    ]

    desc_parts = [
        desc_hook,
        "",
        f"Key topics & search queries: {', '.join(rising_queries[:5]) if rising_queries else kw}",
        "",
        "Chapters:",
        f"00:00 - {title_a[:35]}",
        "01:00 - The Impossible Contradiction",
        "04:30 - The False Narrative & Red Herring",
        "08:00 - The Systemic Blindspot",
        "11:30 - The Smoking Gun",
        "14:00 - The Living Warning",
        "",
        " ".join(hashtags),
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
        from scripts.ag_notion_bridge import query_db, update_page_properties, create_page
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
    grounding_intel: dict = None
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
        for cand in [
            os.path.join(EPISODES_BASE, task_id, "grounding_intel.json"),
            os.path.join("/root/video_factory/episodes", task_id, "grounding_intel.json"),
        ]:
            if os.path.exists(cand):
                try:
                    with open(cand, "r", encoding="utf-8") as gf:
                        grounding_intel = json.load(gf)
                        if grounding_intel:
                            break
                except Exception:
                    pass

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
                system_prompt=SEO_HOOK_SYSTEM_PROMPT,
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
        if len(hook_60s.split()) < 30:
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

        # Assemble full description (5 acts chapter outline + keywords + hashtags + disclosure)
        clean_bqs = [str(q).strip() for q in (bq or rq) if str(q).strip()]
        desc_parts = [
            desc_hook,
            "",
            f"Key topics & search queries: {', '.join(clean_bqs[:5]) if clean_bqs else kw}",
            "",
            "Chapters:",
            f"00:00 - {title_a[:35]}",
            "01:00 - The Impossible Contradiction",
            "04:30 - The False Narrative & Red Herring",
            "08:00 - The Systemic Blindspot",
            "11:30 - The Smoking Gun",
            "14:00 - The Living Warning",
            "",
            " ".join(hashtags),
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

    # 1. Save to /var/vf/episodes/<task_id>/seo_package.json
    for ep_base in [EPISODES_BASE, Path("/root/video_factory/episodes")]:
        try:
            ep_dir = ep_base / task_id
            ep_dir.mkdir(parents=True, exist_ok=True)
            pkg_path = ep_dir / "seo_package.json"
            with open(pkg_path, "w", encoding="utf-8") as f:
                json.dump(package, f, ensure_ascii=False, indent=2)
            logger.info(f"[seo_package_forge] Saved SEO package to {pkg_path}")
        except Exception as _fe:
            logger.warning(f"[seo_package_forge] Could not write package to {ep_base}: {_fe}")

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
