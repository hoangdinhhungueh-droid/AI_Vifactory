"""seo_metadata.py - Multi-platform SEO metadata engine (#5.1 / Phase 2).

FREE, deterministic, NO network, NO paid calls. Consumes the chapter-split
metadata produced by S3.5 (story_gate.json / episode['chapters']) and emits
platform-specific upload payloads: safe titles, front-loaded 2-line
descriptions, chapter timestamps + sub-descriptions, hidden tags, and
hashtags validated against each platform's hard caps (Q2/2026 rules,
page 22 SoT). No SoT duplication: this is the executable form of the
playbook spec, not a new strategy.

Public API:
    PLATFORM_HASHTAG_LIMITS, PLATFORM_SEO_RULES
    format_timestamp(seconds) -> str
    validate_hashtags(platform, hashtags, notify=None) -> list
    build_hashtags(primary_kw, niche=None, trend_keywords=None, breakout_queries=None, extras=None) -> list
    build_seo_tags(primary_kw, secondary=None, niche=None, breakout_queries=None, ...) -> list
    generate_chapters_with_subdesc(chapters) -> str
    build_description_first_2_lines(series_meta, hook, notify=None) -> str
    build_engagement_cta(series_meta, hook) -> str
    resolve_series_meta(episode, series_meta=None) -> dict
    build_seo_payload(platform, episode, series_meta=None, notify=None) -> dict
    build_all_payloads(episode, series_meta=None, platforms=None, notify=None) -> dict
    write_seo_payloads(episode, out_dir, series_meta=None, notify=None) -> dict
"""
from __future__ import annotations

import os
import re
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("vf.seo")


def _env(n, d):
    v = os.getenv(n)
    return v if v is not None else d


def _enabled():
    return _env("VF_SEO_ENABLED", "1") == "1"


# ---- Platform rules (Q2/2026, page 22 SoT) ---------------------------------
PLATFORM_HASHTAG_LIMITS = {
    "youtube":         {"max": 5,  "note": "Q2/2026: >5 reduces discoverability; >15 dropped"},
    "youtube_shorts":  {"max": 5,  "note": "3 quality + loop"},
    "tiktok":          {"max": 5,  "note": "3 trending + 2 niche"},
    "instagram_reels": {"max": 15, "note": "mix trending + niche"},
    "facebook_reels":  {"max": 5,  "note": "less is more; niche tags"},
    "spotify":         {"max": 3,  "note": "embed in RSS description"},
}

PLATFORM_SEO_RULES = {
    "youtube": {
        "title_max": 100, "desc_max": 5000, "desc_first_chars_critical": 150,
        "tags_max_chars": 500, "tags_max": 7, "hashtag_max": 5,
        "chapters_supported": True, "srt_manual_upload": True, "category_id": "22",
    },
    "youtube_shorts": {
        "title_max": 100, "desc_max": 5000, "desc_first_chars_critical": 150,
        "tags_max_chars": 500, "tags_max": 7, "hashtag_max": 5,
        "hook_3s_required": True, "loop_ending_required": True,
        "chapters_supported": False, "category_id": "22",
    },
    "tiktok": {
        "title_max": 150, "caption_max": 2200, "caption_first_chars_critical": 150,
        "hashtag_max": 5, "hook_3s_required": True, "loop_ending_required": True,
        "srt_manual_upload": True, "ab_method": "separate_short_upload",
    },
    "instagram_reels": {
        "title_max": 150, "caption_max": 2200, "hashtag_max": 15,
        "niche_hashtag_priority": True, "hook_3s_required": True,
        "cta_burn_in_last_5s": True,
    },
    "facebook_reels": {
        "title_max": 125, "caption_first_chars_critical": 125, "hashtag_max": 5,
        "avoid_generic_hashtags": True, "hook_3s_required": True,
        "cta_burn_in_last_5s": True,
    },
    "spotify": {
        "title_max": 120, "desc_first_para_critical": True,
        "category": "Fiction / Story", "transcript_upload_txt": True, "hashtag_max": 3,
    },
}

DEFAULT_PLATFORMS = ("youtube", "tiktok", "instagram_reels", "facebook_reels", "spotify")

AI_DISCLOSURE = ("This story and its visuals are AI-assisted / synthetic, "
                 "created as original fiction for entertainment.")

GENERIC_HASHTAGS = {"viral", "fyp", "foryou", "foryoupage", "reels", "trending",
                    "explore", "video", "shorts", "story"}

_NONWORD = re.compile(r"[^\w]+", re.UNICODE)
_STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "with",
         "her", "his", "she", "he", "they", "it", "is", "was", "by", "at",
         "as", "but", "then", "ep", "that", "this"}

# ---- anti-AI-tone copy guard (bo sung 06/08, SEO Playbook Sec 7C) ----------
# Generic AI-marketing phrasing that upstream (LLM-generated) hooks may still
# carry. This is a deterministic safety net stripping it before the hook is
# front-loaded into the first 2 description lines; it is not a replacement
# for fixing the upstream generation prompt.
_AI_TONE_BANNED = [
    re.compile(r"\bunlock\b", re.I),
    re.compile(r"\bdiscover the secrets?\b", re.I),
    re.compile(r"\byou won.t believe\b", re.I),
    re.compile(r"\bin this video\b", re.I),
    re.compile(r"\bin today.s video\b", re.I),
    re.compile(r"\bwelcome (back )?(to|everyone)\b", re.I),
    re.compile(r"\bhey (everyone|guys|there)\b", re.I),
    re.compile(r"\bdive into\b", re.I),
    re.compile(r"\bembark on a journey\b", re.I),
]


# ---- helpers ----------------------------------------------------------------
def _slug_tag(s):
    if isinstance(s, bool):
        return ""
    if isinstance(s, dict):
        s = s.get("query") or s.get("term") or s.get("article") or ""
    parts = [w for w in _NONWORD.split(str(s or "")) if w]
    return "".join(w[:1].upper() + w[1:] for w in parts)


def format_timestamp(seconds):
    seconds = int(round(float(seconds or 0)))
    if seconds < 0:
        seconds = 0
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%d:%02d:%02d" % (h, m, s)
    return "%02d:%02d" % (m, s)


def _trim(s, n):
    s = " ".join((s or "").split())
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "\u2026"


def _sanitize_ai_tone(text, notify=None):
    """Strip generic AI-marketing phrasing (bo sung 06/08). Returns cleaned text."""
    s = text or ""
    hit = False
    for pat in _AI_TONE_BANNED:
        if pat.search(s):
            hit = True
            s = pat.sub("", s)
    s = " ".join(s.split())
    if hit:
        logger.info("[SEO] anti-AI-tone guard stripped generic marketing phrasing from hook")
        if notify:
            try:
                notify("SEO ANTI-AI-TONE: stripped generic marketing phrasing from hook - review upstream prompt")
            except Exception:
                pass
    return s


# ---- hashtags ---------------------------------------------------------------
def build_hashtags(primary_kw, niche=None, trend_keywords=None, breakout_queries=None, extras=None):
    cand = []
    sources = []
    if primary_kw:
        sources.append(primary_kw)
    if breakout_queries:
        sources.extend(list(breakout_queries))
    if niche:
        sources.append(niche)
    if trend_keywords:
        sources.extend(list(trend_keywords))
    if extras:
        sources.extend(list(extras))

    for src in sources:
        if not src:
            continue
        if isinstance(src, dict):
            src = src.get("query") or src.get("term") or src.get("article") or ""
        tag = "#" + _slug_tag(src)
        if tag != "#" and tag.lower() not in [c.lower() for c in cand]:
            cand.append(tag)
    return cand


def validate_hashtags(platform, hashtags, notify=None):
    rule = PLATFORM_HASHTAG_LIMITS.get(platform, {"max": 5})
    limit = rule["max"]
    seen, clean = set(), []
    for h in hashtags or []:
        tag = h if str(h).startswith("#") else "#" + _slug_tag(h)
        key = tag.lower()
        if tag == "#" or key in seen:
            continue
        seen.add(key)
        clean.append(tag)
    if PLATFORM_SEO_RULES.get(platform, {}).get("avoid_generic_hashtags"):
        filtered = [t for t in clean if t.lstrip("#").lower() not in GENERIC_HASHTAGS]
        clean = filtered or clean
    if len(clean) > limit:
        if notify:
            try:
                notify("HASHTAG OVERFLOW %s: %d > %d -> auto-trim" % (platform, len(clean), limit))
            except Exception:
                pass
        logger.info("[SEO] hashtag overflow %s: %d > %d -> trim", platform, len(clean), limit)
        clean = clean[:limit]
    return clean


# ---- hidden tags (YouTube) --------------------------------------------------
def build_seo_tags(primary_kw, secondary=None, niche=None, breakout_queries=None, max_chars=500, max_tags=7):
    def _sanitize_tag(raw) -> str:
        if not raw or isinstance(raw, bool):
            return ""
        if isinstance(raw, dict):
            raw = raw.get("query") or raw.get("term") or raw.get("article") or ""
        t = " ".join(str(raw).replace("\r", " ").replace("\n", " ").replace("\t", " ").replace(",", " ").split())
        if len(t) > 100:
            t = t[:100].rstrip()
        return t

    base = []
    sources = []
    if primary_kw:
        sources.append(primary_kw)
    if breakout_queries:
        sources.extend(list(breakout_queries))
    if secondary:
        sources.extend(list(secondary))
    if niche:
        sources.append(niche)

    for s in sources:
        if not s:
            continue
        cleaned = _sanitize_tag(s)
        if cleaned and cleaned.lower() not in [b.lower() for b in base]:
            base.append(cleaned)

    # 1. First add all exact base terms (primary kw + top breakout queries)
    expanded = []
    for b in base:
        if b.lower() not in [x.lower() for x in expanded]:
            expanded.append(b)

    # 2. Then add suffixed variations if space permits
    for suf in (" documentary", " explained", " story", " history"):
        for b in base:
            t = _sanitize_tag(b + suf)
            if t and t.lower() not in [x.lower() for x in expanded]:
                expanded.append(t)

    tags, total = [], 0
    for t in expanded:
        if len(tags) >= max_tags:
            break
        add = len(t) + (1 if tags else 0)
        if total + add > max_chars:
            continue
        tags.append(t)
        total += add
    return tags


# ---- chapters ---------------------------------------------------------------
def generate_chapters_with_subdesc(chapters):
    """Q2/2026: YouTube chapters with 1-sentence sub-descriptions.
    First timestamp must be 00:00. Consumes S3.5 chapter dicts.
    """
    lines, start = [], 0.0
    for i, ch in enumerate(chapters or []):
        ts = format_timestamp(start)
        title = _trim(ch.get("title") or ("Chapter %d" % (i + 1)), 40)
        sub = _trim(ch.get("summary_1_sentence") or "", 55)
        lines.append(("%s %s" % (ts, title)) + ((" - %s" % sub) if sub else ""))
        start += float(ch.get("duration_est_s") or 0)
    return "\n".join(lines)


# ---- description ------------------------------------------------------------
def build_description_first_2_lines(series_meta, hook, notify=None):
    name = series_meta.get("series_name") or "Story"
    kw = series_meta.get("primary_keyword") or name
    ep = series_meta.get("ep_num")
    sec = series_meta.get("secondary_keyword") or "audio story"
    h = _trim(_sanitize_ai_tone(hook, notify=notify), 70)
    line1 = _trim(("%s | %s" % (kw, h)) + ((" Ep %s" % ep) if ep else ""), 80)
    line2 = _trim("%s | %s" % (sec, name), 80)
    return line1 + "\n" + line2


# ---- engagement CTA (bo sung 06/08, SEO Playbook Sec 3B) --------------------
def build_engagement_cta(series_meta, hook):
    """Copywriting CTA formula (bo sung 06/08): replace a generic open-ended
    question ('what did you think?') with a SPECIFIC question tied to the
    episode content, plus a short suggested-reply cue, to lower comment
    friction and lift the engagement/satisfaction signal. Intended for use
    as a pinned first comment, not baked into the front-loaded description.
    """
    kw = series_meta.get("primary_keyword") or series_meta.get("series_name") or "this story"
    h = _trim(_sanitize_ai_tone(hook), 60) or kw
    question = "Which part hit hardest for you \u2014 %s, or the ending?" % h
    reply_hint = "Reply with one word: \U0001F525 (loved it) or \U0001F614 (didn't see that twist coming)."
    return question + "\n" + reply_hint


# ---- series meta ------------------------------------------------------------
def resolve_series_meta(episode, series_meta=None):
    sm = dict(series_meta or {})
    astyle = episode.get("art_style") or {}
    sm.setdefault("series_name",
                  episode.get("series_name") or astyle.get("series_name")
                  or episode.get("niche") or "Story")
    ep = sm.get("ep_num") or episode.get("ep_num")
    if not ep:
        m = re.search(r"ep0*(\d+)", str(episode.get("episode_id") or ""), re.I)
        ep = m.group(1) if m else None
    sm["ep_num"] = ep
    tk = list(episode.get("trend_keywords") or episode.get("visual_terms") or [])
    sm.setdefault("primary_keyword", (tk[0] if tk else None)
                  or episode.get("niche") or sm["series_name"])
    sm.setdefault("secondary_keyword", (tk[1] if len(tk) > 1 else None) or "audio story")
    sm.setdefault("market_code", episode.get("lang_code") or "en")
    sm.setdefault("niche", episode.get("niche") or "story")
    return sm


# ---- per-platform payload ---------------------------------------------------
def build_seo_payload(platform, episode, series_meta=None, notify=None):
    rule = PLATFORM_SEO_RULES.get(platform, {})
    sm = resolve_series_meta(episode, series_meta)
    chapters = episode.get("chapters") or []
    hook = (episode.get("hook_3s")
            or (chapters[0].get("hook") if chapters else "")
            or sm.get("series_name"))
    kw = sm["primary_keyword"]
    name = sm["series_name"]
    ep = sm["ep_num"]
    breakout_queries = episode.get("breakout_queries") or []

    if platform == "spotify":
        hook10 = " ".join((hook or "").split()[:10])
        title = ("%s: Ep %s - %s" % (name, ep, hook10)) if ep else ("%s: %s" % (name, hook10))
    else:
        if kw == name:
            name_suffix = (" | Ep %s" % ep) if ep else ""
        else:
            name_suffix = ((" | %s Ep %s" % (name, ep)) if ep else (" | %s" % name))
        title = ("%s | %s" % (kw, _trim(hook, 55))) + name_suffix
    title = _trim(title, rule.get("title_max", 100))

    raw_tags = build_hashtags(kw, sm.get("niche"), episode.get("trend_keywords"), breakout_queries=breakout_queries)
    hashtags = validate_hashtags(platform, raw_tags, notify=notify)

    first2 = build_description_first_2_lines(sm, hook, notify=notify)
    cta = build_engagement_cta(sm, hook)
    parts = [first2, ""]
    has_chapters = bool(rule.get("chapters_supported") and chapters)
    if has_chapters:
        parts.append("Chapters:")
        parts.append(generate_chapters_with_subdesc(chapters))
        parts.append("")
    if breakout_queries:
        clean_bqs = []
        for q in breakout_queries:
            if not q or isinstance(q, bool):
                continue
            if isinstance(q, dict):
                q = q.get("query") or q.get("term") or q.get("article") or ""
            q_str = str(q).strip()
            if q_str and q_str.lower() not in (kw or "").lower() and q_str.lower() not in [x.lower() for x in clean_bqs]:
                clean_bqs.append(q_str)
        if clean_bqs:
            parts.append("Topics covered: " + ", ".join(clean_bqs[:5]))
            parts.append("")
    if hashtags:
        parts.append(" ".join(hashtags))
        parts.append("")
    parts.append(AI_DISCLOSURE)
    description = "\n".join(parts).strip()
    dmax = rule.get("desc_max") or rule.get("caption_max")
    if dmax:
        description = description[:dmax]

    payload = {
        "platform": platform,
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "engagement_cta": cta,
        "ai_disclosure": True,
        "made_for_kids": False,
        "series": {"name": name, "ep_num": ep, "primary_keyword": kw,
                   "market_code": sm["market_code"]},
    }
    if platform in ("youtube", "youtube_shorts"):
        payload["tags"] = build_seo_tags(
            kw, episode.get("trend_keywords"), sm.get("niche"),
            breakout_queries=breakout_queries,
            max_chars=rule.get("tags_max_chars", 500),
            max_tags=rule.get("tags_max", 7))
        payload["category_id"] = rule.get("category_id", "22")
    if has_chapters:
        payload["chapters_block"] = generate_chapters_with_subdesc(chapters)
    if rule.get("srt_manual_upload"):
        payload["srt_path"] = episode.get("srt_path")
        payload["srt_independent_upload"] = True
    if platform == "spotify":
        payload["category"] = rule.get("category")
        payload["transcript_upload_txt"] = True
    if rule.get("cta_burn_in_last_5s"):
        payload["cta_burn_in_last_5s"] = True
    if rule.get("hook_3s_required"):
        payload["hook_3s"] = _trim(hook, 120)
    if rule.get("loop_ending_required"):
        payload["loop_ending_required"] = True
    return payload


def build_all_payloads(episode, series_meta=None, platforms=None, notify=None):
    platforms = platforms or DEFAULT_PLATFORMS
    return {p: build_seo_payload(p, episode, series_meta, notify=notify) for p in platforms}


def write_seo_payloads(episode, out_dir, series_meta=None, notify=None):
    if not _enabled():
        logger.info("[SEO] disabled via VF_SEO_ENABLED=0")
        return {}
    payloads = build_all_payloads(episode, series_meta, notify=notify)
    try:
        with open(os.path.join(out_dir, "seo_payloads.json"), "w") as f:
            json.dump(payloads, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("[SEO] seo_payloads write failed: %s", e)
    yt = payloads.get("youtube")
    if yt:
        target = os.path.basename(episode.get("final_169")
                                  or episode.get("final_916") or "final_169.mp4")
        up = {
            "title": yt["title"],
            "description": yt["description"],
            "tags": yt.get("tags", []),
            "category_id": yt.get("category_id", "22"),
            "made_for_kids": False,
            "hashtags": yt.get("hashtags", []),
            "chapters_block": yt.get("chapters_block"),
            "srt_path": yt.get("srt_path"),
            "srt_independent_upload": yt.get("srt_independent_upload", True),
            "pinned_comment_cta": yt.get("engagement_cta"),
            "export": {"target_file": target},
        }
        try:
            with open(os.path.join(out_dir, "youtube_upload_payload.json"), "w") as f:
                json.dump(up, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("[SEO] youtube_upload_payload write failed: %s", e)
        try:
            ab = generate_ab_variants(episode, series_meta, notify=notify)
            with open(os.path.join(out_dir, "ab_variants.json"), "w") as f:
                json.dump(ab, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("[SEO] ab_variants write failed (non-blocking): %s", e)
    return payloads


# ---- A/B variant generator (Page 22 item H, Phase 5, 07/08/2026) -----------
def generate_ab_variants(episode, series_meta=None, n_variants=3, notify=None):
    """Generate up to `n_variants` distinct (title, thumbnail_text) pairs for
    the same episode so the operator can run a manual title/thumbnail A/B
    test (YouTube Studio's native Test & Compare tool, or the planned
    Telegram thumbnail-rotator). Planning/content generator only -- does not
    call any YouTube API (no public endpoint creates A/B tests programmatically).

    Returns {episode_id, generated_at, variants: [...], recommended_test,
    manual_action_required: True}.
    """
    sm = resolve_series_meta(episode, series_meta)
    chapters = episode.get("chapters") or []
    hook = (episode.get("hook_3s")
            or (chapters[0].get("hook") if chapters else "")
            or sm.get("series_name"))
    hook_clean = _sanitize_ai_tone(hook, notify=notify) if hook else sm.get("series_name")
    kw = sm["primary_keyword"]
    name = sm["series_name"]
    ep = sm["ep_num"]

    def _t(s, n):
        return _trim(s, n)

    templates = [
        lambda: _t("%s | %s%s" % (kw, _t(hook_clean, 55),
                                   (" | %s Ep %s" % (name, ep)) if ep else ""), 100),
        lambda: _t("%s?! %s%s" % (_t(hook_clean, 70), name,
                                   (" Ep %s" % ep) if ep else ""), 100),
        lambda: _t(("Ep %s: %s (%s)" % (ep, _t(hook_clean, 60), kw)) if ep
                   else ("%s (%s)" % (_t(hook_clean, 70), kw)), 100),
    ]
    thumb_texts = [
        _t(hook_clean, 28).upper(),
        (_t(hook_clean, 24) + " ?!").upper(),
        (kw.upper() + ": " + _t(hook_clean, 18))[:32].upper(),
    ]

    variants = []
    seen = set()
    for i, tpl in enumerate(templates[:max(1, n_variants)]):
        try:
            t = tpl()
        except Exception:
            continue
        if not t or t in seen:
            continue
        seen.add(t)
        variants.append({
            "variant": chr(65 + i),
            "title": t,
            "thumbnail_text": thumb_texts[i] if i < len(thumb_texts) else thumb_texts[0],
        })

    result = {
        "episode_id": episode.get("episode_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "variants": variants,
        "recommended_test": "YouTube Studio native title/thumbnail Test & Compare, 3-7 days/round",
        "manual_action_required": True,
    }
    if notify:
        try:
            lines = ["\U0001f9ea A/B variants ready (%s):" % episode.get("episode_id", "")]
            for v in variants:
                lines.append("%s) %s  [thumb: %s]" % (v["variant"], v["title"], v["thumbnail_text"]))
            notify("\n".join(lines))
        except Exception:
            pass
    return result
