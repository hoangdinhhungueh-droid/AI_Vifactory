# -*- coding: utf-8 -*-
"""
SEO Auto-Packaging Generator for B10 (Upload stage).

Added 23/08/2026 per user request: removes the manual "paste command into
Antigravity" step for YouTube packaging. Instead, B10 now calls the same
HHTech GPT-6-Astra gateway used at B1/B2 (see hhtech_reasoner.call_gpt56_sol,
Rule 117) to auto-generate the full SEO/packaging bundle for an episode,
strictly following the Skill AI packaging rules (Rule 119): KVS-method
title, front-loaded description, hidden tags, platform-capped hashtags,
breakout & high-growth search query integration, 3-framework thumbnail A/B/C copy,
Hook Frame cold-open note, and End Screen 3-point timing note.

Creative copy (title/description hook/thumbnail concepts) comes from the
LLM. Hard numeric constraints (hashtag caps, tag char budget, per-platform
limits) are ALWAYS enforced deterministically via app.services.seo_metadata,
never trusted to the LLM output, per Rule 118 (Zero-Mock Data / no invented
numbers) and Rule 80 (KPI validate gates).

On any HHTech API failure or invalid JSON, this module falls back to the
existing deterministic seo_metadata.build_seo_payload()/generate_ab_variants()
templates so the pipeline never blocks on the LLM call -- mirrors the
_fallback_topic() pattern already used in hhtech_reasoner.py for B1.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services import seo_metadata as seo
from app.services.skill_loader import get_b10_seo_rules

logger = logging.getLogger("vf.seo_autogen_b10")

SEO_SYSTEM_PROMPT = """Ban la Truong phong SEO & Bao chi hoa Video (Packaging Director) cho Video Factory.
Nhiem vu: sinh GOI PACKAGING YOUTUBE 2026 cho 1 episode, tuan thu TUYET DOI cac quy tac sau (Skill AI Rule 119):

1. TITLE (KVS method): tu khoa chinh (primary_keyword) DA duoc xac thuc tu B1 (Rule 117) -- KHONG tu bo hoac doi tu khoa. Dat title chua NGUYEN tu khoa do o dau title. Toi da 100 ky tu (hien thi dep trong khoang 60-70 ky tu dau).
2. DESCRIPTION: 2 dong dau (khoang 150 ky tu) la tin hieu SEO quan trong nhat -- front-load tu khoa + 1 hook cu the, TUYET DOI KHONG mo dau bang "In this video" hoac "Welcome". Toan bo description toi da 5000 ky tu. Kem 1 cau tom tat <=55 ky tu cho moi chapter neu co chapters truyen vao.
3. BREAKOUT & HIGH-GROWTH SEARCH QUERIES: Don dau xung luc tim kiem (search-intent momentum) bang cach kheo leo long ghep cac tu khoa dot bien (breakout_queries) tu B1 vao Title A/B va 2 dong dau mo ta (Description Hook) de toi da hoa luot hien thi tim kiem tu nhien (organic impressions).
4. THUMBNAIL A/B/C: sinh CHINH XAC 3 bien the, MOI bien the bam dung 1 khung copywriting RIENG BIET (khong doi tu ngu hoi hot):
   - Variant A = emotion_first: cau cam xuc CU THE (khong chung chung).
   - Variant B = keyword_first: dung dung exact keyword o dau cau (co the ket hop breakout query).
   - Variant C = curiosity_gap: cau phan truc giac hoac so lieu bat ngo.
   Moi variant can: headline_text (<=32 ky tu, IN HOA, font chu Ultra-Bold, kich thuoc chiem 35-40% dien tich canvas 16:9 de doc ro tren man hinh Mobile theo Rule 443 An Ong) va visual_concept (1 cau mo ta khung hinh, mobile-first, phi ta thuc theo Rule 19).
5. HOOK FRAME (cold-open): mo ta 1 khung hinh bat ngo nhat cua tap, dung cho 0-3 giay dau video.
6. END SCREEN: goi y 3 diem thoi gian dat end-screen overlay -- (a) ~3 phut dau, (b) 70% thoi luong (cho playlist series), (c) 20 giay cuoi (next-episode CTA + subscribe).
7. AN TOAN: khong duoc de xuat noi dung nham vao tre em, phai giu tinh phi ta thuc/AI-disclosure minh bach.

Tra ve DUY NHAT 1 JSON object hop le, khong markdown code fence, dung dinh dang:
{
  "title_kvs": "<title chua keyword o dau, <=100 ky tu>",
  "description_hook_2_lines": "<2 dong dau, <=150 ky tu, khong mo dau In this video/Welcome>",
  "chapters_summaries": [{"title": "<ten chapter>", "summary_1_sentence": "<<=55 ky tu>"}],
  "thumbnail_variants": [
    {"variant": "A", "framework": "emotion_first", "headline_text": "<<=32 ky tu IN HOA>", "visual_concept": "<1 cau>"},
    {"variant": "B", "framework": "keyword_first", "headline_text": "<<=32 ky tu IN HOA>", "visual_concept": "<1 cau>"},
    {"variant": "C", "framework": "curiosity_gap", "headline_text": "<<=32 ky tu IN HOA>", "visual_concept": "<1 cau>"}
  ],
  "hook_frame_note": "<mo ta khung hinh 0-3s>",
  "end_screen_notes": {"point_1_intro": "<~3 phut dau: ...>", "point_2_70pct": "<70% thoi luong: ...>", "point_3_last_20s": "<20 giay cuoi: next-episode CTA + subscribe>"}
}"""


def _parse_llm_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _fallback_packaging(episode: dict, series_meta=None) -> dict:
    """Deterministic fallback if HHTech call/JSON parse fails. Never blocks B10."""
    yt_payload = seo.build_seo_payload("youtube", episode, series_meta)
    sm = seo.resolve_series_meta(episode, series_meta)
    chapters = episode.get("chapters") or []
    hook = (episode.get("hook_3s")
            or (chapters[0].get("hook") if chapters else "")
            or sm.get("series_name"))
    first2 = seo.build_description_first_2_lines(sm, hook)
    ab = seo.generate_ab_variants(episode, series_meta, n_variants=3)
    variants = ab.get("variants", [])
    frameworks = ["emotion_first", "keyword_first", "curiosity_gap"]
    thumb_variants = []
    for i, v in enumerate(variants):
        thumb_variants.append({
            "variant": v.get("variant", chr(65 + i)),
            "framework": frameworks[i] if i < len(frameworks) else "emotion_first",
            "headline_text": v.get("thumbnail_text", "")[:32],
            "visual_concept": "(fallback template -- HHTech call unavailable, review before publish)",
        })
    return {
        "title_kvs": yt_payload.get("title", ""),
        "description_hook_2_lines": first2,
        "chapters_summaries": [],
        "thumbnail_variants": thumb_variants,
        "hook_frame_note": "(fallback -- HHTech call unavailable, needs manual Hook Frame review)",
        "end_screen_notes": {
            "point_1_intro": "~3:00 -- series/channel branding overlay",
            "point_2_70pct": "70% duration -- playlist/related episode overlay",
            "point_3_last_20s": "last 20s -- next-episode CTA + subscribe",
        },
        "is_fallback": True,
        "yt_payload_template": yt_payload,
    }


def generate_seo_packaging(episode: dict, series_meta: dict = None) -> dict:
    """Auto-generate the full YouTube SEO/packaging bundle for one episode via
    HHTech GPT-6-Astra (same gateway as B1/B2, Rule 117), then enforce all
    deterministic numeric/format constraints via seo_metadata helpers.

    `episode` should include at minimum: episode_id, trend_keywords or
    niche (primary keyword source), breakout_queries (optional), hook_3s,
    chapters (optional), series_name/niche (optional).
    """
    sm = seo.resolve_series_meta(episode, series_meta)
    primary_kw = sm.get("primary_keyword")
    chapters = episode.get("chapters") or []
    breakout_queries = episode.get("breakout_queries") or []

    user_prompt = json.dumps({
        "episode_id": episode.get("episode_id"),
        "primary_keyword_validated_at_b1": primary_kw,
        "breakout_queries_from_b1": breakout_queries,
        "series_name": sm.get("series_name"),
        "hook_3s": episode.get("hook_3s"),
        "niche_angle_brief": episode.get("niche_angle_brief", ""),
        "chapters_source": chapters,
    }, ensure_ascii=False)

 
    # B10: Load Skill AI rules (cache 1h, aligned with B1/B2/B3/B3.5/B4/B5/B6/B7)
    skill_rules = get_b10_seo_rules()
    system_with_rules = SEO_SYSTEM_PROMPT + "\n\n" + skill_rules

    # Resilient Packaging: 3-attempt retry logic with exponential backoff and intelligent failover
    llm_result = None
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("[seo_autogen_b10] Attempt %d/%d calling HHTech GPT-6-Astra...", attempt, max_retries)
            raw = call_gpt6_astra(user_prompt, system_prompt=system_with_rules, max_tokens=2000, timeout=90.0)
            parsed = _parse_llm_json(raw)
            if parsed and isinstance(parsed, dict) and parsed.get("title_kvs"):
                llm_result = parsed
                logger.info("[seo_autogen_b10] Successfully generated and parsed SEO packaging on attempt %d", attempt)
                break
            else:
                logger.warning("[seo_autogen_b10] Attempt %d returned invalid JSON/missing title_kvs", attempt)
        except Exception as e:
            logger.warning("[seo_autogen_b10] Attempt %d failed with error: %s", attempt, e)

        if attempt < max_retries:
            backoff_s = 2 ** attempt
            logger.info("[seo_autogen_b10] Waiting %ds before retry attempt %d...", backoff_s, attempt + 1)
            time.sleep(backoff_s)

    if not llm_result or not llm_result.get("title_kvs"):
        logger.error("[seo_autogen_b10] All %d attempts failed. Engaging intelligent failover to deterministic fallback.", max_retries)
        packaging = _fallback_packaging(episode, series_meta)
    else:
        packaging = llm_result
        packaging["is_fallback"] = False

    # --- Deterministic, code-enforced constraints (never trust LLM for these) ---
    raw_hashtags = seo.build_hashtags(
        primary_kw,
        sm.get("niche"),
        episode.get("trend_keywords"),
        breakout_queries=breakout_queries
    )
    hashtags = seo.validate_hashtags("youtube", raw_hashtags)
    tags = seo.build_seo_tags(
        primary_kw,
        secondary=episode.get("trend_keywords"),
        niche=sm.get("niche"),
        breakout_queries=breakout_queries,
        max_chars=500,
        max_tags=7
    )

    title = packaging.get("title_kvs") or ""
    if primary_kw and primary_kw.lower() not in title.lower():
        # Hard KVS enforcement: keyword MUST lead the title (Rule 119 / SS11A).
        title = f"{primary_kw} | {title}".strip(" |")
    title = title[:100]

    hook2 = (packaging.get("description_hook_2_lines") or "").strip()
    if not hook2 and packaging.get("description"):
        desc_lines = []
        for line in str(packaging["description"]).splitlines():
            line_s = line.strip()
            if not line_s or line_s.startswith("#") or "00:" in line_s or "01:" in line_s or line_s.lower().startswith("chapter"):
                continue
            desc_lines.append(line_s)
            if len(desc_lines) >= 2:
                break
        hook2 = " ".join(desc_lines)
    for banned in ("in this video", "welcome"):
        if hook2.lower().startswith(banned):
            hook2 = hook2.split(" ", 2)[-1]
    hook2 = hook2[:150]

    chapters_block = ""
    ch_summaries = packaging.get("chapters_summaries") or []
    if ch_summaries and chapters:
        merged_chapters = []
        for i, ch in enumerate(chapters):
            merged = dict(ch)
            if i < len(ch_summaries):
                merged["summary_1_sentence"] = ch_summaries[i].get("summary_1_sentence", merged.get("summary_1_sentence", ""))
            merged_chapters.append(merged)
        chapters_block = seo.generate_chapters_with_subdesc(merged_chapters)
    elif chapters:
        chapters_block = seo.generate_chapters_with_subdesc(chapters)

    desc_parts = [hook2, ""]
    if chapters_block:
        desc_parts += ["Chapters:", chapters_block, ""]
    # Key topics line removed per user instruction (clean SEO description)
    if hashtags:
        desc_parts += [" ".join(hashtags), ""]
    desc_parts.append(seo.AI_DISCLOSURE)
    description = "\n".join(desc_parts).strip()[:5000]

    thumb_variants = packaging.get("thumbnail_variants") or []
    title_b = title
    for v in thumb_variants:
        if v.get("variant") == "B" and v.get("headline_text"):
            title_b = f"{primary_kw} | {v['headline_text']}"[:100]
            break

    result = {
        "episode_id": episode.get("episode_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_method": "hhtech_gpt6astra_auto" if not packaging.get("is_fallback") else "deterministic_fallback",
        "title_a": title,
        "title_b": title_b,
        "description": description,
        "tags": tags,
        "hashtags": hashtags,
        "breakout_queries": breakout_queries,
        "chapters_block": chapters_block,
        "thumbnail_variants": thumb_variants,
        "hook_frame_note": packaging.get("hook_frame_note", ""),
        "end_screen_notes": packaging.get("end_screen_notes", {}),
        "ai_disclosure": True,
        "made_for_kids": False,
        "manual_paste_step_required": False,
    }
    return result


from app.services.seo_package_forge import sync_exact_chapters_from_remotion  # Rule 135
