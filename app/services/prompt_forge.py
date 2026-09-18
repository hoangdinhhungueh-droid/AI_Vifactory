"""
Service: B3.5 Prompt Engineering Forge (/prompt:forge)
Single Source of Truth: HHTech GPT-6-Astra + Prompt Library Notion DB
Rule 116 & 435: Layer 1 Background (16:9) + Layer 2 Foreground (1:1 stylized graphic novel on #FF00FF).
Rule 120: Isolates prompt generation. FGs strictly generated on flat #FF00FF magenta background.
Rule 128: Zero Semantic Bias. Dynamically matches scene era, architecture, and lighting without topic relics.
Rule 446: English Production Bridge for all visual generation prompts.
"""

import os
import sys
import json
import re
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _load_env():
    try:
        from app.services.youtube_upload import _load_env as le
        le()
    except Exception:
        pass
    if not os.environ.get("NOTION_TOKEN") and os.path.exists("/root/secrets/.env"):
        try:
            with open("/root/secrets/.env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("NOTION_TOKEN="):
                        os.environ["NOTION_TOKEN"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("NOTION_API_KEY="):
                        os.environ["NOTION_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass

_load_env()

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.model_gateway import get_global_gateway
from app.services.skill_loader import get_b35_strategic_rules

sys.path.insert(0, "/root/video_factory/scripts")
import ag_notion_bridge as _bridge

NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
PROMPT_LIBRARY_DB_ID_FALLBACK = "8c801989-2400-831a-901d-014aebdc3b31"

# Rule 128: Concise targeted visual rules (~1.2k chars) replacing 336k chars dump
TARGETED_VISUAL_RULES = get_b35_strategic_rules()


class ContentPolicyRefusalError(Exception):
    """
    Raised when HHTech GPT-6-Astra refuses to generate prompts due to content policy.
    Upstream should route to HG2.5 (human review gate) for manual prompt engineering.
    """
    pass


def resolve_market_profile(market: str = "EN") -> dict:
    """
    Market-specific visual profile resolver for B3.5 Prompt Forge (Rule 122 & Rule 128).
    Prevents Western/Caucasian bias on Asian subjects and aligns background architecture.
    """
    m = (market or "EN").upper().strip()
    if m in ("JP", "JA"):
        return {
            "market_code": "JP",
            "market_name": "Japanese (Japan)",
            "fg_anchor": "Authentic Japanese individual, distinct Japanese facial bone structure, natural East Asian eye shape, neat Japanese corporate salaryman or professional OL styling, dark navy or charcoal tailored business suit, corporate lapel pin badge (sha-sho), corporate ID neck strap, dynamic high-stakes body posture leaning forward into corporate conflict, active physical interaction with props gripping Japanese documents stamped with cinnabar red circular hanko seal (inkan), intense facial micro-expressions with sharp focused glare and resolute jaw, dramatic professional acting",
            "bg_anchor": "Authentic Japanese corporate or government headquarters setting, Tokyo Kasumigaseki or Marunouchi district architecture, Japanese minimalist wood panels and frosted glass partitions, King File document binders with square spine tabs on shelves, discreet Japanese Kanji signage (財務省, 取締役会, 裁判所), authentic Tokyo financial skyline with soft cinematic lighting",
            "fg_negatives": "no Caucasian traits, no Western facial structure, no blue eyes, no blond hair, no American corporate look, no passive blank stare, no lifeless neutral pose, no passport photo posture, no dead eyes, no English text, no Latin letters",
            "bg_negatives": "no generic Western American cityscapes, no foreign architecture, no New York office aesthetic, no English text, no Latin alphabet on boards or walls, no American flags, no generic gray cubicles"
        }
    elif m in ("KR", "KO"):
        return {
            "market_code": "KR",
            "market_name": "Korean (South Korea)",
            "fg_anchor": "Authentic Korean individual, distinct Korean facial bone structure, defined cheekbones, refined East Asian eye shape, modern Korean professional hairstyle, tailored Korean chaebol executive suit, Korean corporate employee ID card lanyard (sawonjeung), dynamic high-stakes body posture with tense dramatic stance, active physical interaction with props slamming palm onto or presenting official Korean legal or financial dossier with prominent circular red or green seal stamp (ingam dojang or seungso seal), intense emotive facial micro-expressions with furrowed brow and fierce determined gaze, dramatic decisive character acting",
            "bg_anchor": "Authentic South Korean corporate or institutional headquarters setting, Seoul or Yeouido financial district architecture, sleek modern Korean high-rise interior, subtle Korean court crest or Taegeuk Mugunghwa emblem, document shelves with Korean vertical binder spines, panoramic window view of Seoul skyline and Han River bridges, high-contrast chiaroscuro lighting",
            "fg_negatives": "no Caucasian traits, no Western facial structure, no blue eyes, no blond hair, no American corporate look, no passive blank stare, no lifeless neutral pose, no passport photo posture, no dead eyes, no English text, no Latin letters",
            "bg_negatives": "no generic Western American cityscapes, no foreign architecture, no New York office aesthetic, no English text, no Latin words on whiteboards, no English signage, no American flags, no generic gray cubicles"
        }
    elif m in ("VN", "VI"):
        return {
            "market_code": "VN",
            "market_name": "Vietnamese (Vietnam)",
            "fg_anchor": "Authentic Vietnamese individual, distinct Vietnamese facial features and bone structure, Southeast Asian eye shape and hair styling, authentic contemporary Vietnamese professional or civil servant attire, official identification card with red neck lanyard, dynamic authoritative body posture leaning over desk or gesturing with conviction, active physical interaction with props holding official Vietnamese dossier with prominent circular red rubber stamp (dau moc do), intense resolute facial micro-expressions with commanding eyes and firm clenched jaw, authoritative decisive character acting",
            "bg_anchor": "Authentic Vietnamese corporate or administrative headquarters setting, contemporary Hanoi or Ho Chi Minh City commercial architecture, Hanoi Ba Dinh administrative office or Saigon District 1 financial center, Vietnamese mahogany wood furniture with gold lacquer accents, subtle National Emblem of Vietnam (Quoc huy Viet Nam) on conference wall, document cabinets with official Vietnamese administrative folders, Saigon river or Hanoi cityscape view",
            "fg_negatives": "no Caucasian traits, no Western facial structure, no blue eyes, no blond hair, no American corporate look, no passive blank stare, no lifeless neutral pose, no passport photo posture, no dead eyes, no English text, no Latin typography",
            "bg_negatives": "no generic Western American cityscapes, no foreign architecture, no New York office aesthetic, no English text, no Latin words on whiteboards, no foreign flags, no generic gray cubicles"
        }
    else:  # EN, US, GLOBAL, etc.
        return {
            "market_code": "GLOBAL",
            "market_name": "Global / Western",
            "fg_anchor": "Authentic professional attire appropriate to the narrative role and era, dynamic high-stakes body posture, intense facial micro-expressions, active physical interaction with narrative props, stylized expressive character acting",
            "bg_anchor": "Authentic period architecture and narrative atmosphere matching the story location",
            "fg_negatives": "no passive blank stare, no lifeless neutral pose, no passport photo posture, no dead eyes",
            "bg_negatives": ""
        }


def deduplicate_phrase_stutter(text: str) -> str:
    """
    Universal Anti-Stuttering & Phrase Deduplication Engine (Rule 128 & Gate 6 Guarantee).
    1. Eliminates consecutive identical words.
    2. Eliminates consecutive repeated word sequences / n-grams (2-8 words repeated consecutively).
    3. Normalizes single-instance structural phrases (such as [STYLE MANDATE], [ERA ANCHOR],
       [MARKET & ETHNIC ANCHOR], [MARKET & ENVIRONMENT ANCHOR], [STRICT NEGATIVE PROMPT],
       16:9, 1:1, #FF00FF, Stylized Editorial) so each appears AT MOST ONCE across the entire prompt.
    4. Cleans up dangling prepositions, duplicate commas, and irregular spacing.
    """
    cleaned = text

    # 1. Deduplicate consecutive identical words: e.g. "the the" -> "the"
    cleaned = re.sub(r"\b(\w+)(?:[\s,]+\1\b)+", r"\1", cleaned, flags=re.IGNORECASE)

    # 2. Deduplicate consecutive repeated phrases (2 to 8 words repeated consecutively)
    for _ in range(3):
        cleaned = re.sub(
            r"(\b[a-zA-Z0-9#_-]+(?:[\s,]+[a-zA-Z0-9#_-]+){1,8}\b)[\s,]+(?:\1\b)+",
            r"\1",
            cleaned,
            flags=re.IGNORECASE
        )

    # 3. Ensure critical architectural phrases appear at most ONCE across the entire prompt
    single_instance_phrases = [
        r"\[STYLE MANDATE\]",
        r"\[MARKET & ETHNIC ANCHOR\]",
        r"\[MARKET & ENVIRONMENT ANCHOR\]",
        r"\[ERA ANCHOR\]",
        r"\[STRICT NEGATIVE PROMPT\]",
        r"16:9 widescreen cinematic documentary environment",
        r"16:9 aspect ratio",
        r"1:1 aspect ratio",
        r"bottom 20% safe-zone for subtitles",
        r"bottom 20% safe-zone",
        r"clear center-right negative space for foreground character overlay",
        r"clear center-right negative space",
        r"solid flat #FF00FF pure magenta background",
        r"solid #FF00FF magenta background",
        r"#FF00FF",
        r"clean chroma-key cutout, sharp silhouette, no borders, no frames",
        r"clean chroma-key cutout",
        r"full-body head-to-shoes",
        r"entire character visible within frame",
        r"Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration",
        r"Stylized Editorial Graphic Novel Digital Illustration",
        r"Stylized Editorial Graphic Novel",
        r"Stylized Editorial"
    ]

    for phrase_pat in single_instance_phrases:
        matches = list(re.finditer(phrase_pat, cleaned, flags=re.IGNORECASE))
        if len(matches) > 1:
            parts = []
            last_idx = 0
            for i, m in enumerate(matches):
                if i == 0:
                    parts.append(cleaned[last_idx:m.end()])
                else:
                    parts.append(cleaned[last_idx:m.start()])
                last_idx = m.end()
            parts.append(cleaned[last_idx:])
            cleaned = "".join(parts)

    # 4. Clean up dangling prepositions, commas, and whitespace
    cleaned = re.sub(r"\b(with|in|of|and|for|at)\s*([,.;])", r"\2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s,]+|[\s,]+$", "", cleaned)
    return cleaned.strip()


def _clean_relics(text: str, is_byzantine_topic: bool = False) -> str:
    """Universal prompt text sanitization: deduplication, spacing, and punctuation cleanup (Rule 128)."""
    return deduplicate_phrase_stutter(text)


def _sanitize_background_prompt(prompt: str, bg_key: str = "", is_byzantine: bool = False, market: str = "EN") -> str:
    """Sanitize and enforce Rule 116 standards for Layer 1 Background prompts with Market Architecture Conformance."""
    p = prompt.strip()
    p = re.sub(r"\[STYLE MANDATE\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[MARKET & ENVIRONMENT ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[ERA ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)

    # Eradicate forbidden photorealistic tokens while protecting 'non-photorealistic'
    p = re.sub(r"\bnon-photorealistic\b", "__NON_PHOTO__", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic\s*(?:8k)?\s*", "", p, flags=re.IGNORECASE)
    p = p.replace("__NON_PHOTO__", "non-photorealistic")
    p = re.sub(r"\bnon-\s*2d\b", "non-photorealistic 2D", p, flags=re.IGNORECASE)
    p = re.sub(r"\b8k\b", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photographic\s*(?:raw\s*camera)?", "", p, flags=re.IGNORECASE)

    # Strip non-ASCII / CJK glyphs from English visual prompts (Rule 446)
    p = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()

    if "16:9" not in p:
        p = f"{p}, 16:9 aspect ratio"
    if "safe-zone" not in p and "safe zone" not in p:
        p = f"{p}, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"

    prof = resolve_market_profile(market)
    bg_anchor = prof["bg_anchor"]
    bg_negs = f", {prof['bg_negatives']}" if prof["bg_negatives"] else ""

    style_prefix = "[STYLE MANDATE] 16:9 widescreen cinematic editorial environment illustration, stylized graphic novel background, atmospheric volumetric lighting, spatial textures, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay."

    p = f"{style_prefix} {p} [MARKET & ENVIRONMENT ANCHOR] {bg_anchor}. [ERA ANCHOR] Authentic period architecture and narrative atmosphere. [STRICT NEGATIVE PROMPT] no prominent foreground human figures, no photorealistic faces, no text, no subtitles, no watermark, no borders, no ui elements, no split frame, no photographic raw camera{bg_negs}."

    return deduplicate_phrase_stutter(p)


def _sanitize_foreground_prompt(prompt: str, fg_key: str = "", is_byzantine: bool = False, market: str = "EN") -> str:
    """Sanitize and enforce Rule 116 & Rule 435 standards for Layer 2 Foreground prompts with Market Ethnicity Conformance."""
    p = prompt.strip()

    p = re.sub(r"\bnon-photorealistic\b", "__NON_PHOTO__", p, flags=re.IGNORECASE)
    p = re.sub(r"studio portrait lighting,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic studio portrait,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic,?\s*", "", p, flags=re.IGNORECASE)
    p = p.replace("__NON_PHOTO__", "non-photorealistic")
    p = re.sub(r"\bnon-\s*2d\b", "non-photorealistic 2D", p, flags=re.IGNORECASE)
    p = re.sub(r"\bnon-\s*exactly\b", "exactly", p, flags=re.IGNORECASE)
    p = re.sub(r"3D render,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"CGI skin,?\s*", "", p, flags=re.IGNORECASE)

    # Strip non-ASCII / CJK glyphs from English visual prompts (Rule 446)
    p = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()

    # Eradicate positional bias from 1:1 cutout (compositor handles left/right placement)
    p = re.sub(r"positioned strictly on the (?:left|right),?\s*", "centered in frame, ", p, flags=re.IGNORECASE)
    p = re.sub(r"on the (?:far\s+)?(?:left|right)(?:-hand)? side of the frame,?\s*", "centered in frame, ", p, flags=re.IGNORECASE)

    p = re.sub(r"\[STYLE MANDATE\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[MARKET & ETHNIC ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[ERA ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(
        r"(?:Non-photorealistic\s+2D\s+)?Stylized\s+Editorial(?:\s+Graphic\s+Novel)?(?:\s+Digital)?(?:\s+Illustration)?(?:\s+of)?\s*,?\s*",
        "",
        p,
        flags=re.IGNORECASE
    ).strip()

    # Clean corrupted character role fragments (e.g. 'ficial' -> 'official')
    p = re.sub(r"\bFull-body\s+ficial\b", "Full-body official", p, flags=re.IGNORECASE)
    p = re.sub(r"\bficial\b", "official", p)

    # Strip redundant chroma and isolation clauses from core description to prevent stutter
    p = re.sub(r",?\s*(?:isolated\s+on(?:\s+a)?(?:\s+solid)?(?:\s+flat)?\s*(?:#FF00FF)?(?:\s+pure)?(?:\s+magenta)?(?:\s+background)?)", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*#FF00FF[^,]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*1:1\s+aspect\s+ratio", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:isolated\s+on(?:\s+a)?|\bon\b|\bwith\b|\bat\b)\s*$", "", p.strip(), flags=re.IGNORECASE)
    p = p.rstrip(",. ").strip()

    prof = resolve_market_profile(market)
    fg_anchor = prof["fg_anchor"]
    fg_negs = f", {prof['fg_negatives']}" if prof["fg_negatives"] else ""

    style_prefix = "[STYLE MANDATE] Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration, clean bold ink linework, cel-shading, rich nuanced colors, 1:1 aspect ratio, full-body head-to-shoes, entire character visible within frame, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames."

    p = f"{style_prefix} {p}, dynamic high-stakes body posture, dramatic physical posing, intense facial micro-expressions with sharp focused gaze, full-body head-to-shoes visible within frame. [MARKET & ETHNIC ANCHOR] {fg_anchor}. [ERA ANCHOR] Authentic professional attire, stylized expressive character acting, active props interaction. [STRICT NEGATIVE PROMPT] no photograph, no photorealistic human, no 3D render, no CGI skin, no white background, no gray background, no halo, no gradients, no cropped head, no cropped feet, no cutoffs, no borders, no ui elements{fg_negs}."

    p = deduplicate_phrase_stutter(p)

    matches = list(re.finditer(r"Stylized\s+editorial", p, flags=re.IGNORECASE))
    if len(matches) > 1:
        parts = []
        last_idx = 0
        for i, m in enumerate(matches):
            parts.append(p[last_idx:m.start()])
            if i == 0:
                parts.append(p[m.start():m.end()])
            else:
                parts.append("expressive illustrated")
            last_idx = m.end()
        parts.append(p[last_idx:])
        p = "".join(parts)

    p = re.sub(r"\s{2,}", " ", p).strip()
    return p


def _sanitize_thumbnail_prompt(prompt: str, thumb_key: str = "", market: str = "EN") -> str:
    """Sanitize and format YouTube 16:9 QHD Hero Thumbnail prompt (Rule 114, Rule 122 & Rule 435)."""
    p = prompt.strip()
    p = p.replace("2K DCI", "").replace("(2K DCI)", "").strip()

    # Protect non-photorealistic tokens
    p = re.sub(r"\bnon-photorealistic\b", "__NON_PHOTO__", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic\s*(?:8k)?\s*", "", p, flags=re.IGNORECASE)
    p = p.replace("__NON_PHOTO__", "non-photorealistic")
    p = re.sub(r"\bnon-\s*2d\b", "non-photorealistic 2D", p, flags=re.IGNORECASE)

    # Strip non-ASCII / CJK glyphs from English visual prompts (Rule 446)
    p = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "", p)
    p = re.sub(r"['\"](?:\s*['\"])?", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()

    if "16:9" not in p:
        p = f"{p}, 16:9 aspect ratio"
    if "2560x1440" not in p:
        p = f"{p}, 2560x1440 resolution (16:9 QHD)"

    prof = resolve_market_profile(market)
    market_negs = f", {prof['fg_negatives']}" if prof["fg_negatives"] else ""

    style_prefix = "[STYLE MANDATE: THUMBNAIL] 16:9 widescreen high-CTR YouTube hero thumbnail, non-photorealistic 2D stylized editorial graphic novel digital illustration, bold ink linework, cel-shading, high visual tension, dramatic high-contrast lighting, bold cinematic color grading, clear focal point, clean negative space for typography."
    strict_negatives = f"[STRICT NEGATIVE PROMPT] no tiny unreadable text, no cluttered composition, no low quality, no blur, no split frame, no watermark, no ui elements, no text, no letters, no words, no typography, no logos, no photorealistic human, no 3D CGI{market_negs}."
    p = f"{style_prefix} {p} {strict_negatives}"
    return deduplicate_phrase_stutter(p)


def _synthesize_thumbnail_prompts(story_title: str, seo_data: dict = None, market: str = "EN") -> dict:
    """
    Synthesize high-CTR YouTube Thumbnail prompts (A/B) from SEO Package & Story Anchor (Rule 114, 122 & Rule 435).
    Thumbnail A: Emotion-First & Specific Viral Angle (Graphic Novel Hero Art).
    Thumbnail B: Curiosity-Gap & Paradox Juxtaposition (Graphic Novel Concept Art).
    """
    prof = resolve_market_profile(market)
    market_hint = f", authentic {prof['market_name']} setting and character styling" if prof["market_code"] != "GLOBAL" else ""

    raw_title_a = (seo_data.get("title_a") if seo_data else "") or story_title or ""
    clean_title_a = re.sub(r"[\r\n]+", " ", raw_title_a).split("|")[0].strip()[:80]
    
    raw_title_b = (seo_data.get("title_b") if seo_data else "") or ""
    clean_title_b = re.sub(r"[\r\n]+", " ", raw_title_b).split("|")[0].strip()[:80]
    
    raw_angle = ((seo_data.get("specific_viral_angle") if seo_data else "") or "").strip()
    angle_sents = [s.strip() for s in re.split(r"[.\n\r。|！？!?]+", raw_angle) if s.strip()]
    first_sent = angle_sents[0] if angle_sents else ""
    if any(kw in first_sent for kw in ["報道の表面", "ではなく", "ではなく、", "突き合わせ", "可視化する", "中心に"]):
        first_sent = clean_title_a
    clean_angle = re.sub(r"[、,;:\s]+$", "", first_sent[:100]) or clean_title_a

    raw_hook = (seo_data.get("hook_3s") if seo_data else "") or ""
    hook_sents = [s.strip() for s in re.split(r"[.\n\r。|！？!?]+", raw_hook) if s.strip()]
    clean_hook = re.sub(r"[、,;:\s]+$", "", hook_sents[0][:100]) if hook_sents else clean_title_a

    thumb_a = (
        f"Stylized editorial graphic novel 16:9 YouTube hero thumbnail for '{clean_title_a}'{market_hint}. "
        f"High visual tension dramatic metaphor illustrating '{clean_angle}', "
        f"dramatic high-contrast chiaroscuro lighting, bold ink outlines, rich nuanced cel-shading, "
        f"clear asymmetric focal point, unobstructed clean negative space for typography, 2560x1440 resolution (16:9 QHD)."
    )
    thumb_b = (
        f"Curiosity-gap stylized graphic novel 16:9 YouTube thumbnail for '{clean_title_b or clean_title_a}'{market_hint}. "
        f"Shocking narrative juxtaposition illustrating the core paradox '{clean_hook or clean_title_a}', "
        f"intense volumetric dramatic chiaroscuro, graphic novel cel-shading with clean ink lines, "
        f"unobstructed safe-zone for title typography, 2560x1440 resolution (16:9 QHD)."
    )
    return {
        "thumbnail_a": _sanitize_thumbnail_prompt(thumb_a, "thumbnail_a", market=market),
        "thumbnail_b": _sanitize_thumbnail_prompt(thumb_b, "thumbnail_b", market=market)
    }



def generate_scene_prompts(
    bg_dict: dict,
    fg_dict: dict,
    story_title: str,
    scenes: list = None,
    **kwargs
) -> dict:
    """
    Calls HHTech GPT-6-Astra via dedicated reasoner to generate high-fidelity image prompts
    for paired Backgrounds (16:9) and Foregrounds (1:1).
    
    Preserves scene-level pairing (background_reuse_key, foreground_reuse_key) to ensure
    Background and Foreground are semantically unified in era, lighting, and narrative context.
    
    Enforces Rule 116, Rule 122 & Rule 435 (non-photorealistic stylized graphic novel FG on #FF00FF).
    Enforces Market Ethnicity & Architectural Conformance (Anti-Western bias on Asian topics).
    Eradicates all hardcoded relics and dynamically adapts to the scene era (Rule 128).
    """
    task_id = kwargs.get("task_id")
    market = kwargs.get("market")
    if not market and task_id and "_" in task_id:
        market = task_id.split("_")[0].upper()
    if not market:
        market = "EN"
    market = str(market).upper()
    market_prof = resolve_market_profile(market)

    scene_pairings = []
    if scenes:
        seen_pairs = {}
        for idx, sc in enumerate(scenes):
            bg_k = sc.get("background_reuse_key") or sc.get("bg_id") or "bg_00"
            raw_fg = sc.get("foreground_reuse_key") or sc.get("fg_id") or None
            # Fix: Never invent phantom foreground keys when scene has no foreground (Rule 118 & 128)
            fg_k = str(raw_fg).strip() if raw_fg and str(raw_fg).strip() else None

            pair_key = (bg_k, fg_k)
            narr = (sc.get("narration") or sc.get("narrative") or "").strip()

            if pair_key not in seen_pairs:
                clean_context = narr[:120] if narr else ""
                seen_pairs[pair_key] = {
                    "background_key": bg_k,
                    "foreground_key": fg_k,
                    "scene_span": f"sc{idx:03d}",
                    "representative_context": clean_context
                }
            else:
                seen_pairs[pair_key]["scene_span"] += f", sc{idx:03d}"

        scene_pairings = list(seen_pairs.values())

    # Prepare strategic prompt for GPT-6-Astra
    b35_rules = get_b35_strategic_rules()
    system_prompt = (
        "You are the Lead Cinematographer and Visual Concept Artist (GPT-6-Astra) for AI Video Factory.\n"
        "Your mission is to forge production-ready image prompts for two distinct visual layers per scene:\n"
        "  - Layer 1 Background (16:9 2560x1440): Wide environmental setting, cinematic lighting, subtitle safe-zone.\n"
        "  - Layer 2 Foreground (1:1 2048x2048): Stylized editorial graphic novel digital illustration isolated on pure #FF00FF magenta chroma key.\n\n"
        f"TARGET MARKET CONTEXT (RULE 122 & RULE 128): {market_prof['market_name']} (Code: {market_prof['market_code']})\n"
        f"  - Foreground Character Phenotype Mandate: {market_prof['fg_anchor']}\n"
        f"  - Background Architecture & Environment Mandate: {market_prof['bg_anchor']}\n\n"
        "CRITICAL ARCHITECTURAL MANDATES (RULE 116 & RULE 435 & RULE 122 & RULE 128):\n"
        f"1. MARKET ETHNICITY & REGIONAL FIDELITY (Rule 122): Strictly adhere to target market {market_prof['market_name']}. "
        "Characters MUST feature authentic ethnic phenotype, bone structure, eye shape, and hairstyles matching this market. "
        "NEVER default to Caucasian, Western, or American facial features for Asian markets (JP/KR/VN)! "
        "Backgrounds MUST feature authentic local corporate/urban architecture and atmosphere matching this market. "
        "NEVER default to generic American high-rises for Asian settings!\n"
        "2. ERA & TOPIC AUTHENTICITY (Rule 128): Strictly derive era, architectural style, atmosphere, color palette, and lighting dynamically from the episode topic and scene narration. Zero domain bleed.\n"
        "3. SCENE SEMANTIC COUPLING: Maintain 100% semantic unity between each Background and its paired Foreground character. The setting, time period, indoor/outdoor lighting angle, and mood MUST match between paired assets in each scene.\n"
        "4. LAYER 1 BACKGROUND PROMPT RULES (16:9):\n"
        "   - Wide-angle cinematic environment establishing scene atmosphere and narrative depth.\n"
        "   - Authentic period architecture, environment textures, dramatic volumetric lighting.\n"
        "   - NO prominent human figures in the foreground. Leave center/right negative space clear for the Layer 2 character overlay.\n"
        "   - Leave the bottom 20% safe zone clear of critical visual elements for on-screen subtitles.\n"
        "   - Style: Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, rich spatial textures, moody chiaroscuro lighting, 16:9 aspect ratio.\n"
        "5. LAYER 2 FOREGROUND PROMPT RULES (1:1):\n"
        "   - NON-PHOTOREALISTIC, STYLIZED EDITORIAL GRAPHIC NOVEL DIGITAL ILLUSTRATION (clean digital artwork, illustrated character drawing, NOT a studio photograph).\n"
        "   - Exactly ONE full-body standing or seated figure/subject visible from head to toe in authentic attire appropriate to the era and role.\n"
        "   - Dynamic dramatic lighting angle aligned with the lighting angle and tone of the paired scene background.\n"
        "   - MUST ALWAYS include the exact technical clause: 'isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio'.\n"
        "   - Completely avoid 'photorealistic studio portrait lighting' for foregrounds. Foreground must be a stylized editorial graphic novel digital illustration.\n\n"
        "Output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"backgrounds\": {\n"
        "    \"<bg_key>\": \"<detailed prompt string>\", ...\n"
        "  },\n"
        "  \"foregrounds\": {\n"
        "    \"<fg_key>\": \"<detailed prompt string>\", ...\n"
        "  }\n"
        "}\n\n"
        f"STRATEGIC VISUAL RULES:\n{b35_rules}"
    )

    user_payload = {
        "title": story_title,
        "market": market,
        "backgrounds_to_generate": bg_dict,
        "foregrounds_to_generate": fg_dict
    }
    if scene_pairings:
        user_payload["unique_asset_pairings"] = scene_pairings

    raw_response = None
    gateway = get_global_gateway()
    for pf_attempt in range(1, 3):
        try:
            logger.info(f"[prompt_forge] Calling Claude Opus 5 for prompts (attempt {pf_attempt}/2, market={market}, fallback=gpt-6-astra)...")
            raw_response = gateway.call_llm(
                prompt=json.dumps(user_payload, ensure_ascii=False),
                system_prompt=system_prompt,
                model="claude-opus-5",
                max_tokens=8500,
                timeout=200.0,
                fallback="gpt-6-astra"
            )
            if raw_response and raw_response.strip():
                break
        except Exception as e:
            logger.warning(f"[prompt_forge] LLM attempt {pf_attempt} encountered issue: {e}")
            if pf_attempt < 2:
                import time
                time.sleep(3.0)
            else:
                logger.warning("[prompt_forge] Activating robust metadata-driven synthesis fallback.")

    parsed = None
    if raw_response and raw_response.strip():
        content = raw_response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Check for content policy refusal
        content_lower = content.lower()
        refusal_indicators = [
            "i cannot generate",
            "i am unable to",
            "content policy",
            "safety policy",
            "against my programming",
            "sensitive themes",
            "violates",
            "inappropriate content"
        ]
        if any(indicator in content_lower for indicator in refusal_indicators):
            logger.error("[prompt_forge] GPT-6-Astra CONTENT POLICY REFUSAL detected")
            raise ContentPolicyRefusalError(
                f"HHTech GPT-6-Astra refused to generate prompts due to content policy for '{story_title}'. "
                f"Refusal: {content[:250]}"
            )

        try:
            parsed = json.loads(content)
        except Exception as e:
            logger.warning(f"[prompt_forge] JSON decode error: {e}. Attempting recovery...")
            m = re.search(r"(\{.*\})", content, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception:
                    pass

    if not parsed or not isinstance(parsed, dict):
        parsed = {"backgrounds": {}, "foregrounds": {}}

    cleaned_backgrounds = {}
    cleaned_foregrounds = {}

    for k, p in parsed.get("backgrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_backgrounds[k] = _sanitize_background_prompt(prompt_str, k, market=market)

    for k, p in parsed.get("foregrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_foregrounds[k] = _sanitize_foreground_prompt(prompt_str, k, market=market)

    # Ensure all requested keys are covered, synthesizing from scene metadata if needed
    for bg_k, bg_meta in bg_dict.items():
        if bg_k not in cleaned_backgrounds:
            if isinstance(bg_meta, dict):
                hint = bg_meta.get("visual_hint") or bg_meta.get("narration_context") or bg_k.replace("-", " ")
                paired_fgs = bg_meta.get("paired_foregrounds", [])
            elif isinstance(bg_meta, str):
                hint = bg_meta
                paired_fgs = []
            else:
                hint = str(bg_meta or bg_k).replace("-", " ")
                paired_fgs = []
            paired_desc = f", paired with {', '.join(paired_fgs)}" if paired_fgs else ""
            fallback_bg = (
                f"Cinematic wide-angle documentary environment of {hint}{paired_desc}, "
                f"atmospheric volumetric natural lighting matching narrative tone, 16:9 aspect ratio, "
                f"bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"
            )
            cleaned_backgrounds[bg_k] = _sanitize_background_prompt(fallback_bg, bg_k, market=market)

    for fg_k, fg_meta in fg_dict.items():
        if fg_k not in cleaned_foregrounds:
            if isinstance(fg_meta, dict):
                hint = fg_meta.get("visual_hint") or fg_meta.get("narration_context") or fg_k.replace("-", " ")
                paired_bgs = fg_meta.get("paired_backgrounds", [])
            elif isinstance(fg_meta, str):
                hint = fg_meta
                paired_bgs = []
            else:
                hint = str(fg_meta or fg_k).replace("-", " ")
                paired_bgs = []
            paired_desc = f", harmonized with setting {', '.join(paired_bgs)}" if paired_bgs else ""
            fallback_fg = (
                f"Full-body {hint} figure in authentic period attire{paired_desc}, "
                f"head to toe visible, dramatic character rim light matching environment, "
                f"isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio"
            )
            cleaned_foregrounds[fg_k] = _sanitize_foreground_prompt(fallback_fg, fg_k, market=market)

    # Architectural Decision: Decoupled to YouTube Studio Native Gemini Designer at HG3.
    # Pipeline B3.5 focuses strictly on Dual-Layer Assets: Backgrounds (16:9) & Foregrounds (1:1 Chroma Key Cutout).
    result = {
        "backgrounds": cleaned_backgrounds,
        "foregrounds": cleaned_foregrounds,
        "thumbnails": {}
    }
    logger.info(f"[prompt_forge] Successfully forged {len(cleaned_backgrounds)} BG prompts, {len(cleaned_foregrounds)} FG prompts for market {market} (Thumbnails decoupled to YouTube Studio HG3)")
    return result



def push_prompts_to_notion(prompts_data: dict, episode_id: str, task_id: str = None):
    """
    Pushes generated prompts to this episode's own Prompt Library child database
    (per-episode subpage+DB resolved dynamically via ag_notion_bridge.resolve_episode_prompt_db).
    Archives old prompts for the same episode first to keep idempotency.
    """
    token = None
    try:
        token = _bridge._get_token()
    except Exception:
        pass
    if not token:
        token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")

    if not token:
        logger.warning("[prompt_forge] No Notion token found, skipping Notion sync.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    resolved = _bridge.resolve_episode_prompt_db(episode_id, task_id=task_id)
    if resolved.get("error"):
        logger.warning(f"[prompt_forge] Could not resolve episode DB for {episode_id}: {resolved}. Using fallback flat DB.")
        prompt_library_db_id = PROMPT_LIBRARY_DB_ID_FALLBACK
    else:
        prompt_library_db_id = resolved["db_id"]
        if resolved.get("created"):
            logger.info(f"[prompt_forge] Created new Prompt Library child DB for {episode_id} (db={prompt_library_db_id})")

    # 0. Archive old prompts for this episode to maintain single-truth
    try:
        filter_obj = {
            "property": "Title",
            "title": {"contains": f"[{episode_id}]"}
        }
        q_res = _bridge.query_db(prompt_library_db_id, filter_obj=filter_obj)
        existing = q_res.get("results", []) if isinstance(q_res, dict) else []
        for r in existing:
            _bridge._req("PATCH", f"pages/{r['id']}", {"archived": True})
        if existing:
            logger.info(f"[prompt_forge] Archived {len(existing)} older prompts for [{episode_id}] in Prompt Library DB.")
    except Exception as e:
        logger.warning(f"[prompt_forge] Error cleaning old prompts: {e}")

    # 1. Backgrounds
    for bg_key, prompt in prompts_data.get("backgrounds", {}).items():
        prompt_str = prompt if isinstance(prompt, str) else prompt.get("prompt", str(prompt))
        bg_props = {
            "Title": {"title": [{"text": {"content": f"[{episode_id}] {bg_key} (BG 16:9)"}}]},
            "prompt_text": {"rich_text": [{"text": {"content": prompt_str[:2000]}}]},
            "category": {"select": {"name": "image"}},
            "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 16:9, Safe Zone: Bottom 20%"}}]},
            "version": {"number": 1}
        }
        try:
            res = _bridge.create_page(prompt_library_db_id, bg_props)
            if not res.get("error"):
                logger.debug(f"[prompt_forge] Pushed BG prompt {bg_key} to Notion Prompt Library DB")
            else:
                logger.warning(f"[prompt_forge] Failed to push BG prompt {bg_key}: {res}")
        except Exception as e:
            logger.warning(f"[prompt_forge] Exception pushing BG prompt {bg_key}: {e}")

    # 2. Foregrounds
    for fg_key, prompt in prompts_data.get("foregrounds", {}).items():
        prompt_str = prompt if isinstance(prompt, str) else prompt.get("prompt", str(prompt))
        fg_props = {
            "Title": {"title": [{"text": {"content": f"[{episode_id}] {fg_key} (FG 1:1 #FF00FF)"}}]},
            "prompt_text": {"rich_text": [{"text": {"content": prompt_str[:2000]}}]},
            "category": {"select": {"name": "image"}},
            "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 1:1, Chroma Key: Flat #FF00FF Magenta Background"}}]},
            "version": {"number": 1}
        }
        try:
            res = _bridge.create_page(prompt_library_db_id, fg_props)
            if not res.get("error"):
                logger.debug(f"[prompt_forge] Pushed FG prompt {fg_key} to Notion Prompt Library DB")
            else:
                logger.warning(f"[prompt_forge] Failed to push FG prompt {fg_key}: {res}")
        except Exception as e:
            logger.warning(f"[prompt_forge] Exception pushing FG prompt {fg_key}: {e}")

    # 2b. Thumbnails (A/B)
    for thumb_key, prompt in prompts_data.get("thumbnails", {}).items():
        prompt_str = prompt if isinstance(prompt, str) else prompt.get("prompt", str(prompt))
        thumb_props = {
            "Title": {"title": [{"text": {"content": f"[{episode_id}] {thumb_key} (Thumbnail 16:9)"}}]},
            "prompt_text": {"rich_text": [{"text": {"content": prompt_str[:2000]}}]},
            "category": {"select": {"name": "image"}},
            "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 16:9 2K DCI, High Contrast, YouTube CTR Hero"}}]},
            "version": {"number": 1}
        }
        try:
            res = _bridge.create_page(prompt_library_db_id, thumb_props)
            if not res.get("error"):
                logger.debug(f"[prompt_forge] Pushed Thumbnail prompt {thumb_key} to Notion Prompt Library DB")
            else:
                logger.warning(f"[prompt_forge] Failed to push Thumbnail prompt {thumb_key}: {res}")
        except Exception as e:
            logger.warning(f"[prompt_forge] Exception pushing Thumbnail prompt {thumb_key}: {e}")

    # 3. Cross-DB State Transitions:

    # Update Director Plan status -> 'Prompted' and Story Library status -> 'Produced'
    try:
        import scripts.ag_notion_bridge as bridge
        # 3a. Update Director Plan status -> 'Prompted'
        dir_res = bridge.resolve_episode_director_db(episode_id, task_id=task_id, create_if_missing=False)
        if isinstance(dir_res, dict) and not dir_res.get("error"):
            subpage_id = dir_res.get("subpage_id")
            if subpage_id:
                bridge.update_page_properties(subpage_id, {"Status": {"status": {"name": "Prompted"}}})
                logger.info(f"[prompt_forge] Transitioned Director Plan [{episode_id}] status to 'Prompted'")

        # 3b. Update Story Library status -> 'Produced'
        story_db_id = bridge.resolve_id("story")
        if story_db_id:
            q_story = bridge.query_db(story_db_id, filter_obj={"or": [
                {"property": "Task ID", "rich_text": {"equals": episode_id}},
                {"property": "Episode ID", "rich_text": {"equals": episode_id}}
            ]})
            if q_story.get("results"):
                story_page_id = q_story["results"][0]["id"]
                bridge.update_page_properties(story_page_id, {"Status": {"status": {"name": "Produced"}}})
                logger.info(f"[prompt_forge] Transitioned Story Library [{episode_id}] status to 'Produced'")
    except Exception as _st_err:
        logger.warning(f"[prompt_forge] Notice updating downstream Notion statuses: {_st_err}")
