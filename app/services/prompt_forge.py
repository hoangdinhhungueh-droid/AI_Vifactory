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
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def _load_env():
    try:
        from app.services.youtube_upload import _load_env as le
        le()
    except Exception as _e_le:
        logger.debug("YouTube upload env load: %s", _e_le)
    if not os.environ.get("NOTION_TOKEN") and os.path.exists("/root/secrets/.env"):
        try:
            with open("/root/secrets/.env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("NOTION_TOKEN="):
                        os.environ["NOTION_TOKEN"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("NOTION_API_KEY="):
                        os.environ["NOTION_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception as _e_env:
            logger.debug("Secrets env read error: %s", _e_env)

_load_env()

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.model_gateway import get_global_gateway
from app.services.skill_loader import (
    get_b35_strategic_rules,
    get_cinematic_tokens_dictionary
)

sys.path.insert(0, "/root/video_factory/scripts")
import ag_notion_bridge as _bridge

NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
PROMPT_LIBRARY_DB_ID_FALLBACK = "8c801989-2400-831a-901d-014aebdc3b31"

# Rule 128: Concise targeted visual rules (~1.2k chars) replacing 336k chars dump
TARGETED_VISUAL_RULES = get_b35_strategic_rules()


def resolve_cinematic_tokens(tokens: list | None) -> dict:
    """Translate cinematic tokens into English prompt directives for Gemini 2K DCI.
    Returns categorized visual phrases:
      {
        "camera_directives": list[str],
        "lighting_directives": list[str],
        "vfx_directives": list[str],
        "remotion_fx": list[str]
      }
    """
    dict_data = get_cinematic_tokens_dictionary()
    token_map = {t["token"]: t for t in dict_data.get("tokens", [])}
    
    res = {
        "camera_directives": [],
        "lighting_directives": [],
        "vfx_directives": [],
        "remotion_fx": []
    }
    if not tokens or not isinstance(tokens, list):
        return res
        
    for tok in tokens:
        if not isinstance(tok, str):
            continue
        t_clean = tok.strip()
        if not t_clean.startswith("/"):
            t_clean = f"/{t_clean}"
        t_normalized = t_clean.lower().replace(" ", "_")
        # Handle synonyms and shorthand camera commands
        synonyms = {
            "/macrozoom": "/macro_zoom",
            "/macro_zoom": "/macro_zoom",
            "/pov": "/pov",
            "/firstperson": "/firstperson",
            "/earth_zoom": "/earthzoom",
            "/earthzoom": "/earthzoom",
            "/360": "/orbit_360",
            "/orbit360": "/orbit_360",
            "/orbit_360": "/orbit_360",
            "/glambot": "/glambot",
            "/productexplosion": "/product_explosion",
            "/product_explosion": "/product_explosion",
            "/tvcommercial": "/commercial_grade",
            "/tv_commercial": "/commercial_grade",
            "/commercial_grade": "/commercial_grade"
        }
        mapped_key = synonyms.get(t_normalized, t_normalized)
        info = token_map.get(t_clean) or token_map.get(mapped_key)
        if not info:
            continue
        cat = info.get("category")
        directive = info.get("gemini_directive_en", "")
        if cat in ("angle", "framing", "motion_camera") and directive and directive not in res["camera_directives"]:
            res["camera_directives"].append(directive)
        elif cat == "lighting" and directive and directive not in res["lighting_directives"]:
            res["lighting_directives"].append(directive)
        elif cat in ("style_vfx", "transition", "vox_graphic") and directive and directive not in res["vfx_directives"]:
            res["vfx_directives"].append(directive)
            
        r_fx = info.get("remotion_fx")
        if r_fx and r_fx not in res["remotion_fx"]:
            res["remotion_fx"].append(r_fx)
            
    return res


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
    else:  # EN, US, UK, CA, AU, NZ
        return {
            "market_code": "EN",
            "market_name": "English (US/UK/CA/AU/NZ)",
            "fg_anchor": "Authentic contemporary individual reflecting authentic metropolitan demographic diversity, distinct bone structure, authentic contemporary professional attire, dynamic high-stakes body posture, intense emotive facial micro-expressions with commanding eyes, active physical interaction with narrative props, stylized expressive character acting",
            "bg_anchor": "Authentic Western corporate or institutional headquarters setting, classic and modern architecture, high-contrast chiaroscuro lighting",
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

    # 4. Deduplicate items inside [STRICT NEGATIVE PROMPT] to prevent token dilution while preserving R137 contract
    if "[STRICT NEGATIVE PROMPT]" in cleaned:
        neg_split = cleaned.split("[STRICT NEGATIVE PROMPT]")
        prefix = neg_split[0]
        neg_tail = neg_split[1]
        closing_m = re.search(r"The image contains no writing or readable digits of any kind in any language\.?", neg_tail, re.IGNORECASE)
        closing_txt = f" {closing_m.group(0)}" if closing_m else ""
        neg_body = neg_tail[:closing_m.start()] if closing_m else neg_tail

        has_r137 = NEGATIVE_R137 in neg_body
        if has_r137:
            neg_body_without_r137 = neg_body.replace(NEGATIVE_R137, "__R137_BLOCK__")
            items = [item.strip(" ,.") for item in neg_body_without_r137.split(",") if item.strip(" ,.")]
            seen_neg = set()
            deduped_items = []
            for it in items:
                if it == "__R137_BLOCK__":
                    deduped_items.append(NEGATIVE_R137)
                    continue
                it_key = re.sub(r"^\bno\s+", "", it, flags=re.IGNORECASE).strip().lower()
                if it_key and it_key not in seen_neg and f"no {it_key}" not in NEGATIVE_R137.lower():
                    seen_neg.add(it_key)
                    deduped_items.append(it)
            cleaned = f"{prefix}[STRICT NEGATIVE PROMPT] {', '.join(deduped_items)}.{closing_txt}".strip()
        else:
            items = [item.strip(" ,.") for item in neg_body.split(",") if item.strip(" ,.")]
            seen_neg = set()
            deduped_items = []
            for it in items:
                it_key = re.sub(r"^\bno\s+", "", it, flags=re.IGNORECASE).strip().lower()
                if it_key and it_key not in seen_neg:
                    seen_neg.add(it_key)
                    deduped_items.append(it)
            cleaned = f"{prefix}[STRICT NEGATIVE PROMPT] {', '.join(deduped_items)}.{closing_txt}".strip()

    # 5. Clean up leaked prompt fragments, empty parens, and text-bait triggers (Rule 128 & Rule 137)
    # Empty or date-only parentheses resulting from stripped years
    cleaned = re.sub(r"\(\s*,\s*\)", "", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\(\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:by\s+)?policy\s+year\s*\(\s*,?\s*\)", "by historical policy periods", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpolicy\s+year\b", "historical policy period", cleaned, flags=re.IGNORECASE)

    # Leaked prepositions, participles, and dangling punctuation
    cleaned = re.sub(r"\bfrom\s+to\b", "across elapsed calendar years", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcascading\s+down\s+to(?:\s+Tier)?\s*,\s*then(?:\s+Tier)?\s*,?", "cascading down through descending structural levels,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bswung\s+to\s*,", "swung high into the critical warning threshold,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bring\s+marked\s*,", "ring marked with division indices,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bending\s+at\s+a\s+red-circled\s*,", "ending at a red-circled ledger entry,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcounter\s+tag\s+reading\s*[,.]", "counter tag emblem without readable digits,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\btag\s+reading(?:\s+['\"][^'\"]*['\"])?\s*[,.]?", "evidentiary archival tag,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcaptions?\s+reading(?:\s+['\"][^'\"]*['\"])?\s*[,.]?", "blank official header blocks,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcover\s+reading(?:\s+['\"][^'\"]*['\"])?\s*[,.]?", "cover folio with blank header block,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bCourt\s+filing\s+captioned(?:\s+['\"][^'\"]*['\"])?\s*[,.]?", "Court filing with formal judicial header,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcaptioned(?:\s+['\"][^'\"]*['\"])?\s*[,.]?", "with official judicial header block,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bheaded(?:\s+['\"][^'\"]*['\"])?\s*[,.]?", "with formal title block,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmarked\s*,\s*a\s+framed", "sealed with tape, a framed", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmarked\s*,", "sealed with tape,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bOfficial\s+Form\s*,", "Official Form blank template,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bPACER\s+docket\s+sheet\s+for(?:\s+federal\s+court\s+case\s+record)?\s+and\s+circling\b", "printed PACER electronic docket sheet folio, circling a line-item entry with a pen", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\ba\s+bound\s+document\s+with(?:\s+legislative\s+assembly\s+bill)?\s+on\s+the\s+cover\b", "a bound legislative bill document folio with an official seal on the cover", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bClaims\s+agent's\s+(?:declaration\s+)?with\s+a\b", "Claims agent's declaration folio with a", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bbolded\s+line\s*\.", "bolded highlight summary rule line.", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bwith\s+the\s+[–-]\s*bars\b", "with prominent peak period bars", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bbracketed\s*\.", "bracketed with callout pointers.", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\brubber-stamp\s+style\s+graphic\s+overlay\b", "geometric dismiss seal stamp without typography", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdated\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,", "with formal date notation line,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bfiled\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,", "with formal electronic filing stamp,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bfiling\s+date\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,", "official filing date stamp block,", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bTrust\s+Bold\s+ink\b", "Trust, bold ink", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdonut\s+chart\s+showing\s+REJECT\s+versus\s+ACCEPT\b", "dual-tone proportional ring graphic emphasizing contrasting vote shares without typography", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bticking\s+cash-register\s+numerals\s+beneath\b", "mechanical indicator dials beneath without readable numerals", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcash-register\s+numerals\b", "indicator dials without numbers", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcarved\s+lettering\b", "carved relief texture without typography", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\)\s*[\$¥₩€£]", ")", cleaned)
    cleaned = re.sub(r"[\$¥₩€£]\s*(?=[a-zA-Z])", "", cleaned)

    # 6. Clean up dangling prepositions, commas, and whitespace
    cleaned = re.sub(r"\b(with|in|of|and|for|at)\s*([,.;])", r"\2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s,]+|[\s,]+$", "", cleaned)
    return cleaned.strip()


def _clean_relics(text: str, is_byzantine_topic: bool = False) -> str:
    """Universal prompt text sanitization: deduplication, spacing, and punctuation cleanup (Rule 128)."""
    return deduplicate_phrase_stutter(text)


# =========================================================================
# RULE 137: ZERO-TEXT & ZERO-NUMBER IN VISUAL PROMPT MANDATE (VOX ELEVATION)
# =========================================================================

# Tokens that look numeric/temporal but are visual, cinematographic or era anchors (ALLOWLIST)
R137_ALLOWLIST = re.compile(r"\b(2\.5D|35mm|50mm|85mm|16:9|1:1|21:9|32:9|\d{4}s)\b", re.IGNORECASE)

R137_BANNED = {
    "currency": re.compile(r"[$¥₩€£]|\b(USD|JPY|KRW|dollars?|yen|won)\b|달러|원화|ドル|円", re.IGNORECASE),
    "units": re.compile(r"\b(million|billion|trillion|percent)\b|%|億|兆|万|억|조|만", re.IGNORECASE),
    "digits": re.compile(r"\d"),
    "text_claims": re.compile(
        r"\b(text|words?|letters?|caption|headline|title|label(?:ed)?|reads?|saying|"
        r"written|typography|font|logo|signage|numbers?|chart values)\b", re.IGNORECASE
    ),
    "quoted": re.compile(r"[\"“”「」『』].+?[\"“”「」『』]|(?<!\w)['‘’].+?['‘’](?!\w)"),
}

# Documents are allowed, but strictly as blank forensic templates
DOC_NOUNS = re.compile(r"\b(document|ledger|filing|report|form|memo|invoice|statement|receipt|subpoena|docket)\b", re.IGNORECASE)
BLANK_TEMPLATE = (
    "unfilled template with official border, blank amount fields, "
    "empty ruled lines, embossed seal without inscription, no typography, blank surfaces"
)

NEGATIVE_R137 = (
    "no text, no letters, no words, no numbers, no digits, no currency symbols, no watermark, "
    "no signature, no logo, no caption, no labels, no readable writing, no chart values, "
    "no subtitles, no UI elements, no hanzi, no kanji, no hangul, no latin script typography"
)
R137_CLOSING_DIRECTIVE = "The image contains no writing or readable digits of any kind in any language."

def apply_semantic_numeral_rewrites(text: str) -> str:
    """Rewrite numbers, years, chapters, and statutory codes to descriptive words
    so meaning survives while preventing raw digits from baking into images."""
    if not text:
        return ""
    
    # 1. Historical decades, centuries, and period years
    text = re.sub(r"\b1950s\b", "nineteen-fifties era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1960s\b", "nineteen-sixties era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1970s\b", "nineteen-seventies era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1980s\b", "nineteen-eighties era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1990s\b", "nineteen-nineties era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b2000s\b", "two-thousands era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b2010s\b", "twenty-tens era", text, flags=re.IGNORECASE)
    text = re.sub(r"\b2020s\b", "twenty-twenties era", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcirca\s*:\s*", "circa vintage era, ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcirca\s*19(\d0)s?\b", r"circa nineteen-\1s era", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcirca\s+197\d\b", "circa nineteen-seventies era", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcirca\s+198\d\b", "circa nineteen-eighties era", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcirca\s+196\d\b", "circa nineteen-sixties era", text, flags=re.IGNORECASE)

    # 2. Bankruptcy chapters, legal codes, and statutes
    text = re.sub(r"\bChapter\s+11\s+(?:voluntary\s+)?petition\b", "federal bankruptcy reorganization petition", text, flags=re.IGNORECASE)
    text = re.sub(r"\bChapter\s+11\b", "federal bankruptcy reorganization", text, flags=re.IGNORECASE)
    text = re.sub(r"\bChapter\s+7\b", "federal bankruptcy liquidation", text, flags=re.IGNORECASE)
    text = re.sub(r"\bChapter\s+13\b", "individual debt reorganization", text, flags=re.IGNORECASE)
    text = re.sub(r"\bChapter\s+(?:voluntary\s+)?petition\b", "federal bankruptcy reorganization petition", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAB\s*218\b", "Child Victims Act legislative reform bill", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAB\s*\d+\b", "legislative assembly bill", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCase\s*#?\s*\d+[-\d]*\b", "federal court case record", text, flags=re.IGNORECASE)

    # 3. Currency and metric values
    text = re.sub(r"[\$¥₩€£]?\s*\b330\+?\b", "hundreds of", text)
    text = re.sub(r"[\$¥₩€£]?\s*\b44\.6\s*(?:million|M)\b", "multimillion-dollar fee total", text, flags=re.IGNORECASE)
    text = re.sub(r"[\$¥₩€£]?\s*\b242\s*(?:million|M)\b", "multimillion-dollar final settlement sum", text, flags=re.IGNORECASE)
    text = re.sub(r"[\$¥₩€£]?\s*\b143\.5\s*(?:million|M)\b", "multimillion-dollar trust proposal", text, flags=re.IGNORECASE)
    text = re.sub(r"[\$¥₩€£]?\s*\b76\.1\s*(?:million|M)\b", "multimillion-dollar estate valuation", text, flags=re.IGNORECASE)
    text = re.sub(r"[\$¥₩€£]?\s*\b29\s*(?:million|M)\b", "tens of millions of dollars", text, flags=re.IGNORECASE)
    text = re.sub(r"[\$¥₩€£]?\s*\b106\s*(?:million|M)\b", "hundreds of millions of dollars", text, flags=re.IGNORECASE)
    text = re.sub(r"\b99%\b", "overwhelming majority", text)
    text = re.sub(r"\b42%\b", "substantial forty-percent", text)
    text = re.sub(r"\b59%\b", "majority share", text)
    text = re.sub(r"\b\d+\s+years\b", "multi-year intervals", text, flags=re.IGNORECASE)
    text = re.sub(r"\bover\s+years\b", "over multi-year intervals", text, flags=re.IGNORECASE)
    text = re.sub(r"[\$¥₩€£]\s*(?=[a-zA-Z])", "", text)

    return text


@dataclass
class LintResult:
    ok: bool
    violations: List[Tuple[str, str]]
    prompt: str
    negative: str

def lint_visual_prompt(prompt: str, strict: bool = False, is_prop: bool = False, **kwargs) -> LintResult:
    """
    Rule 137 Strict Prompt Linter.
    Scans visual prompt to purge and prevent baked-in text, currency symbols, and numbers.
    In strict mode, returns ok=False if violations exist.
    In non-strict mode, sanitizes and replaces doc claims with BLANK_TEMPLATE (ONLY for evidence props).
    """
    if not prompt:
        return LintResult(ok=True, violations=[], prompt="", negative=NEGATIVE_R137)
    
    # 0. Apply semantic rewrites first so conceptual terms survive without digits
    prompt = apply_semantic_numeral_rewrites(prompt)
    
    # 1. Protect allowlisted technical tokens
    scrubbed = R137_ALLOWLIST.sub(" ", prompt)
    
    # 2. Check for banned violations
    violations: List[Tuple[str, str]] = []
    for cat, rx in R137_BANNED.items():
        for m in rx.finditer(scrubbed):
            violations.append((cat, m.group(0)))
            
    # 3. Clean and inject blank template if document nouns present (ONLY for raw evidence props that lack hygiene, NEVER environments, characters, or already-hygienic prompts)
    fixed = prompt
    # Remove quoted strings that might contain fake text
    fixed = R137_BANNED["quoted"].sub("", fixed)
    already_hygienic = any(k in fixed.lower() for k in [
        "without typography", "no typography", "blank unfilled", "blank surfaces",
        "without readable", "unlabeled abstract", "chart", "histogram", "waterfall"
    ])
    if not strict and is_prop and DOC_NOUNS.search(fixed) and not already_hygienic and "unfilled template" not in fixed:
        clean_prefix = re.sub(r"(?:\.|\,)?\s*\bFlat\b(?:\.|\,)?\s*$", "", fixed.strip(), flags=re.IGNORECASE).rstrip(". ,")
        fixed = f"{clean_prefix}, {BLANK_TEMPLATE}"
    
    # Protect aspect ratios and cinematographic tokens before stripping numeric amounts
    aspect_masks = {
        "16:9": "__ASPECT_RATIO_16_9__",
        "1:1": "__ASPECT_RATIO_1_1__",
        "21:9": "__ASPECT_RATIO_21_9__",
        "32:9": "__ASPECT_RATIO_32_9__",
        "2.5D": "__CINEMA_TOKEN_2_5D__",
        "35mm": "__CINEMA_TOKEN_35MM__",
        "50mm": "__CINEMA_TOKEN_50MM__",
        "85mm": "__CINEMA_TOKEN_85MM__",
    }
    for raw_tok, mask_tok in aspect_masks.items():
        fixed = re.sub(rf"\b{re.escape(raw_tok)}\b", mask_tok, fixed, flags=re.IGNORECASE)

    # Strip explicit currency amounts like "$942B", "$426 billion", "188 billion" (use space to prevent word welding)
    fixed = re.sub(r"[$¥₩€£]?\s*\b\d+(?:\.\d+)?\s*(?:billion|trillion|million|B|T|M|k|%)?\s*(?:dollars?|yen|won)?\b", " ", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"[$¥₩€£]\s*(?=[a-zA-Z])", "", fixed)

    # Restore allowlisted tokens
    for raw_tok, mask_tok in aspect_masks.items():
        fixed = fixed.replace(mask_tok, raw_tok)

    # Clean any dangling :aspect ratio or :1 aspect ratio relics without corrupting 1:1 or 16:9
    fixed = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"\bcirca\s*:\s*", "circa vintage era, ", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"\bChapter\s*(?:voluntary\s+)?petition\b", "federal bankruptcy reorganization petition", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"\bFlat\s*,\s*", "", fixed)
    fixed = re.sub(r",\s*Flat\b", "", fixed)
    fixed = re.sub(r"(?:\.|\,)?\s*\bFlat\b(?:\.|\,)?\s*$", "", fixed.strip(), flags=re.IGNORECASE)
    
    # Ensure closing directive is present
    if R137_CLOSING_DIRECTIVE not in fixed:
        fixed = f"{fixed.rstrip('. ')}. {R137_CLOSING_DIRECTIVE}"
        
    ok = len(violations) == 0 if strict else True
    return LintResult(ok=ok, violations=violations, prompt=fixed, negative=NEGATIVE_R137)


def resolve_era_anchor(key: str, p: str) -> str:
    """Resolve era-specific timeline anchor dynamically to prevent generic placeholders (Rule 128)."""
    k_norm = (key or "").replace("_", " ").lower()

    # Contemporary institutional roles default strictly to contemporary timeline
    contemporary_roles = [
        "judge", "counsel", "attorney", "lawyer", "litigator", "cfo", "finance",
        "bishop", "clerk", "examiner", "journalist", "reporter", "official", "administrator",
        "debtor", "creditor", "claimant", "survivor", "legislator", "lawmaker"
    ]
    is_contemporary_character = any(r in k_norm for r in contemporary_roles)
    has_vintage_tag_in_key = any(v in k_norm for v in ["1950", "1960", "1970", "1980", "1990", "2019", "vintage", "archival", "flashback"])
    if is_contemporary_character and not has_vintage_tag_in_key:
        return "Contemporary timeline, authentic modern documentary setting."

    # For backgrounds and archival props: check key first, then description
    m_key_decade = re.search(r"\b(19[5-9]0s|20[0-2]0s)\b", k_norm)
    if m_key_decade:
        return f"{m_key_decade.group(1)} era documentary aesthetic, authentic archival period atmosphere."
    m_key_year = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", k_norm)
    if m_key_year:
        return f"{m_key_year.group(1)} timeline, authentic period setting and documentary fidelity."
    if any(k in k_norm for k in ["1970", "seventies", "1970s"]):
        return "1970s era documentary aesthetic, authentic archival period atmosphere."
    elif any(k in k_norm for k in ["1960", "sixties", "1960s"]):
        return "1960s era documentary aesthetic, authentic archival period atmosphere."
    elif any(k in k_norm for k in ["1980", "eighties", "1980s"]):
        return "1980s era documentary aesthetic, authentic archival period atmosphere."
    elif any(k in k_norm for k in ["1990", "nineties", "1990s"]):
        return "1990s era documentary aesthetic, authentic archival period atmosphere."

    combined = f"{key} {p}".replace("_", " ").lower()
    m_decade = re.search(r"\b(19[5-9]0s|20[0-2]0s)\b", combined)
    m_year = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", combined)
    if m_decade:
        return f"{m_decade.group(1)} era documentary aesthetic, authentic archival period atmosphere."
    elif m_year:
        return f"{m_year.group(1)} timeline, authentic period setting and documentary fidelity."
    elif any(k in combined for k in ["1970", "seventies", "1970s"]):
        return "1970s era documentary aesthetic, authentic archival period atmosphere."
    elif any(k in combined for k in ["1980", "eighties", "1980s"]):
        return "1980s era documentary aesthetic, authentic archival period atmosphere."
    elif any(k in combined for k in ["1990", "nineties", "1990s"]):
        return "1990s era documentary aesthetic, authentic archival period atmosphere."
    elif any(k in combined for k in ["1960", "sixties", "1960s"]):
        return "1960s era documentary aesthetic, authentic archival period atmosphere."
    elif "historical" in combined or "archival" in combined:
        return "Archival historical timeline, authentic period textures and documentary fidelity."
    else:
        return "Contemporary timeline, authentic modern documentary setting."


def resolve_background_anchor(bg_key: str, p: str, market: str, prof: dict) -> tuple[str, str]:
    """
    Resolve setting-specific background architecture and atmosphere anchor (Rule 122 & Rule 128).
    Prevents forcing 'corporate headquarters' on cathedrals, courthouses, outdoor scenes, or archives.
    Accurately distinguishes exterior facades from interior chambers to prevent conflicting cues.
    """
    m = (market or "EN").upper().strip()
    combined = f"{bg_key} {p}".lower()
    base_anchor = prof.get("bg_anchor", "Authentic contemporary setting, classic and modern architecture, high-contrast chiaroscuro lighting")
    base_negs = prof.get("bg_negatives", "")

    is_exterior = any(k in combined for k in ["exterior", "dawn", "night", "skyline", "lake", "street", "plaza", "facade", "outdoor", "sidewalk", "entrance"])
    is_interior = any(k in combined for k in ["interior", "courtroom", "gallery", "hallway", "corridor", "vault", "chambers", "bench", "nave", "rectory", "office"])

    # High-specificity checks first (prevent generic ecclesiastical or corporate fall-through)
    if any(k in combined for k in ["dioceses_map", "geographic_map"]) or ("map" in bg_key.lower() and "street" not in bg_key.lower()):
        anchor = "Stylized 2D archival geographic map chart of Northern California municipal jurisdictions, parchment texture, atmospheric cartographic lighting"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["ledger_grid", "abstract_ledger", "financial_grid", "accounting paper texture"]):
        anchor = "Stylized 2D forensic financial ledger grid texture, muted sepia and slate ruled accounting paper, dramatic raking light"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["1970s_oakland_streetscape", "1970s streetscape", "vintage streetscape"]) or (
        "1970" in combined and any(k in combined for k in ["street", "streetscape", "sidewalk", "urban exterior"])
    ):
        anchor = "Authentic 1970s East Bay municipal streetscape and parish brick exterior, vintage 1970s urban atmosphere, overcast atmospheric light"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["alameda_superior_courthouse", "superior court", "county courthouse", "art deco courthouse"]):
        if is_exterior and not is_interior:
            anchor = "Authentic regional historic Art Deco county courthouse facade, monumental civic stonework and civic plaza, atmospheric exterior documentary lighting"
        else:
            anchor = "Authentic historic Art Deco county courtroom setting, dark carved wood paneling, judicial bench, institutional solemnity, raking documentary light"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["capitol_assembly", "sacramento_capitol", "assembly chamber", "legislative assembly"]):
        anchor = "Authentic California State Capitol legislative assembly chamber interior, historic legislative rostrum and polished wood desks, atmospheric civic chamber lighting"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["settlement_mediation", "mediation_chamber", "mediation suite"]):
        anchor = "Neutral dispute resolution settlement mediation suite interior, conference table with confidential case binders, calm diffused interior daylight"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["restructuring_war_room", "war_room", "legal war room"]):
        anchor = "Late-night corporate legal conference war room interior, mahogany conference table, scattered document folios, dramatic interior lamp light"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["dellums", "federal_courthouse", "federal office"]):
        if is_exterior and not is_interior:
            anchor = "Authentic regional modern federal office tower and glass rotunda facade, civic plaza architecture, atmospheric exterior documentary lighting"
        else:
            anchor = "Authentic federal bankruptcy courtroom setting, modern wood paneling, elevated judicial bench, solemn institutional atmosphere, documentary lighting"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["cathedral", "church", "chapel", "sanctuary", "parish", "rectory", "temple", "shrine"]):
        if is_exterior and not is_interior:
            anchor = "Authentic ecclesiastical exterior architecture, iconic cathedral facade with glass-and-timber structure, atmospheric exterior volumetric lighting, solemn, austere institutional stillness"
        else:
            anchor = "Authentic ecclesiastical interior architecture, sacred sanctuary or rectory corridor, atmospheric volumetric window lighting, solemn, austere institutional stillness"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["federal", "courthouse", "courtroom", "chambers", "bench", "tribunal", "docket", "civic_center", "city_hall", "municipal"]):
        if is_exterior and not is_interior:
            if any(k in combined for k in ["modern", "glass", "rotunda", "tower", "high-rise", "office"]):
                anchor = "Authentic regional modern federal office tower and glass rotunda facade, civic plaza architecture, atmospheric exterior documentary lighting"
            else:
                anchor = "Authentic regional civic and judicial exterior architecture, monumental courthouse facade and civic plaza, atmospheric exterior documentary lighting"
        else:
            anchor = "Authentic judicial or municipal courtroom setting, formal wood paneling, judicial bench, institutional solemnity, raking documentary light"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["lake", "skyline", "fog", "street", "plaza", "exterior", "downtown", "district", "harbor", "port", "bridge"]):
        anchor = "Authentic regional civic or urban landscape, atmospheric exterior lighting with time-of-day fidelity, natural environmental textures and spatial depth"
        return anchor, f", {base_negs}" if base_negs else ""

    elif any(k in combined for k in ["archive", "records", "hallway", "corridor", "vault", "basement", "warehouse", "storage"]):
        anchor = "Authentic institutional archive or facility, utilitarian architecture, dramatic corridor perspective, high-contrast noir shadows"
        return anchor, f", {base_negs}" if base_negs else ""

    else:
        return base_anchor, f", {base_negs}" if base_negs else ""


def _sanitize_background_prompt(prompt: str, bg_key: str = "", is_byzantine: bool = False, market: str = "EN", tokens: list | None = None) -> str:
    """Sanitize and enforce Rule 116 & Rule 137 standards for Layer 1 Background prompts with Market Architecture Conformance."""
    p = _sanitize_evidence_notes(prompt.strip())
    # Strip previous style mandate without swallowing the core description
    p = re.sub(r"\[STYLE MANDATE[^\]]*\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(
        r"16:9 widescreen cinematic editorial environment illustration, stylized graphic novel background, atmospheric volumetric lighting, spatial textures, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay\.?,?\s*",
        "",
        p,
        flags=re.IGNORECASE
    )
    p = re.sub(r"\[MARKET & ENVIRONMENT ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[ERA ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[CAMERA & PERSPECTIVE\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[LIGHTING & OPTICS\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[OPTICAL STYLE\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(r"The image contains no writing or readable digits of any kind in any language\.?", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*16:9 aspect ratio", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay", "", p, flags=re.IGNORECASE)

    # String-join fixes & text-bait purging
    p = re.sub(r"\b(?:Bottomkept|Bottomheld|Bottomreserved|Bottomis)\b", "bottom safe-zone", p, flags=re.IGNORECASE)
    p = re.sub(r"\bOaklands\b", "Oakland's", p)
    p = re.sub(r",?\s*home of the U\.S\. Bankruptcy Court[^,.]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*Oakland Division[^,.]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\bABbill\b", "legislative assembly bill", p, flags=re.IGNORECASE)
    p = re.sub(r"\bAB\s*\d+\b", "legislative assembly bill", p, flags=re.IGNORECASE)

    # Eradicate forbidden photorealistic tokens while protecting 'non-photorealistic'
    p = re.sub(r"\bnon-photorealistic\b", "__NON_PHOTO__", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic\s*(?:8k)?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic,?\s*", "", p, flags=re.IGNORECASE)
    p = p.replace("__NON_PHOTO__", "non-photorealistic")
    p = re.sub(r"\bnon-\s*2d\b", "non-photorealistic 2D", p, flags=re.IGNORECASE)
    p = re.sub(r"\b8k\b", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photographic\s*(?:raw\s*camera)?", "", p, flags=re.IGNORECASE)

    # Strip non-ASCII / CJK glyphs from English visual prompts (Rule 446)
    p = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()

    # Clean text magnets and inscribed seals in environment backgrounds (Rule 122 & Rule 137)
    p = re.sub(r"\bGreat\s+Seal\s+of\s+the\s+United\s+States\b", "carved wooden eagle judicial seal emblem without typography or inscription", p, flags=re.IGNORECASE)
    p = re.sub(r"\bevidence\s+monitors?\b", "unlit matte display screen", p, flags=re.IGNORECASE)
    p = re.sub(r"\bmonitors?\b", "unlit display panels", p, flags=re.IGNORECASE)
    p = re.sub(r"\blabeled\s+drawers\b", "neatly arranged dark wood filing drawers without lettering", p, flags=re.IGNORECASE)
    p = re.sub(r"\bmanila\s+folders\b", "plain archival paper folders", p, flags=re.IGNORECASE)
    p = re.sub(r"\btypewriters?\b", "vintage mechanical desktop device", p, flags=re.IGNORECASE)
    p = re.sub(r"\bofficial\s+border\b", "neat architectural paneling", p, flags=re.IGNORECASE)
    p = re.sub(r"\bCalifornia\s+[bB]ear\s+[fF]lag\b", "California state banner with stylized bear-and-star silhouette without typography", p)
    p = re.sub(r"\bTribune\s+Tower\b", "historic Tribune clock tower with numeral-free clock face", p, flags=re.IGNORECASE)
    p = re.sub(r"\bhistoric\s+clock\s+tower\b", "historic clock tower with numeral-free clock face", p, flags=re.IGNORECASE)

    # Document hygiene purge: backgrounds must NEVER describe unfilled templates, blank amount fields, or empty ruled lines
    p = re.sub(r",?\s*(?:unfilled\s+template(?:\s+with\s+official\s+border)?|blank\s+amount\s+fields|empty\s+ruled\s+lines|embossed\s+seal\s+without\s+inscription|blank\s+surfaces)[^,.]*", "", p, flags=re.IGNORECASE)

    # Rule 137: Sanitize visual prompt through linter (is_prop=False strictly prevents BLANK_TEMPLATE bleed into environment)
    lint_res = lint_visual_prompt(p, strict=False, is_prop=False)
    p = lint_res.prompt.replace(R137_CLOSING_DIRECTIVE, "").rstrip(". ,")
    p = re.sub(r"\bOaklands\b", "Oakland's", p)
    p = re.sub(r"\bABbill\b", "legislative assembly bill", p, flags=re.IGNORECASE)
    p = re.sub(r"\b(?:Bottomkept|Bottomheld|Bottomreserved|Bottomis)\b", "bottom safe-zone", p, flags=re.IGNORECASE)

    p = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\bcirca\s*:\s*", "circa vintage era, ", p, flags=re.IGNORECASE)
    p = re.sub(r"\bFlat\s*,\s*", "", p)
    p = re.sub(r",\s*Flat\b", "", p)
    # Thoroughly purge any blank template phrases post-linter
    p = re.sub(r",?\s*(?:unfilled\s+template(?:\s+with\s+official\s+border)?|blank\s+amount\s+fields|empty\s+ruled\s+lines|embossed\s+seal\s+without\s+inscription|blank\s+surfaces)[^,.]*", "", p, flags=re.IGNORECASE)
    if "16:9" not in p:
        p = f"{p}, 16:9 aspect ratio"
    if "safe-zone" not in p and "safe zone" not in p:
        p = f"{p}, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"

    prof = resolve_market_profile(market)
    bg_anchor, bg_negs = resolve_background_anchor(bg_key, p, market, prof)
    era_anchor = resolve_era_anchor(bg_key, p)

    tokens_clauses = []
    if tokens:
        resolved = resolve_cinematic_tokens(tokens)
        if resolved["camera_directives"]:
            tokens_clauses.append(f"[CAMERA & PERSPECTIVE] {', '.join(resolved['camera_directives'])}.")
        # Filter out foreground document/counter directives from Layer 1 background plate
        bg_lighting = [d for d in resolved["lighting_directives"] if not any(k in d.lower() for k in ["evidence document", "critical document", "evidence prop"])]
        if bg_lighting:
            tokens_clauses.append(f"[LIGHTING & OPTICS] {', '.join(bg_lighting)}.")
        bg_vfx = [d for d in resolved["vfx_directives"] if not any(k in d.lower() for k in ["metric counter", "mechanical counter", "spinning up"])]
        if bg_vfx:
            tokens_clauses.append(f"[OPTICAL STYLE] {', '.join(bg_vfx)}.")
    flow_str = f" {' '.join(tokens_clauses)}" if tokens_clauses else ""

    style_prefix = "[STYLE MANDATE] 16:9 widescreen cinematic editorial environment illustration, stylized graphic novel background, atmospheric volumetric lighting, spatial textures, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay."

    p = f"{style_prefix} {p}{flow_str} [MARKET & ENVIRONMENT ANCHOR] {bg_anchor}. [ERA ANCHOR] {era_anchor} [STRICT NEGATIVE PROMPT] no prominent foreground human figures, no photorealistic faces, {NEGATIVE_R137}, no borders, no ui elements, no split frame, no photographic raw camera{bg_negs}. {R137_CLOSING_DIRECTIVE}"

    return deduplicate_phrase_stutter(p)


def _sanitize_evidence_notes(text: str) -> str:
    """
    Purge internal reviewer instructions, audit debris, and corrupted QA tokens from visual prompts (Rule 128).
    E.g. 'able2026 claim supplied; verify release and observation dates'
    'Record-history start not supplied', 'No 1985 reference', 'claim supplied'
    """
    if not text:
        return ""
    patterns = [
        r"able\d{4}\s+claim\s+supplied;?[^'\"]*",
        r"verify\s+(?:release|observation|dates|sources)[^'\"]*",
        r"claim\s+supplied;?\s*",
        r"Record-history\s+start\s+not\s+supplied;?\s*",
        r"No\s+\d{4}\s+reference;?\s*",
        r"no\s+ranking\s+claim;?\s*",
        r"internal\s+verification\s+note[^'\"]*",
        r"audit\s+note[^'\"]*"
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    text = re.sub(r",\s*,\s*", ", ", text)
    text = re.sub(r",\s*\.\s*", ", ", text)
    text = re.sub(r"\.\s*\.\s*", ". ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def resolve_character_anchor(fg_key: str, p: str, market: str, prof: dict) -> tuple[str, str]:
    """
    Resolve character ethnic phenotype, attire, and negative prompts dynamically based on
    market, fg_key, and context description (p).
    Rule 128 (Anti-Semantic Bias) & Rule 122 (Ethnic & Market Integrity):
    - Strictly bound to episode target market (EN, JP, VN, KR).
    - NEVER leak JP/CN quarantine/agricultural anchors into EN episodes.
    - NEVER leak Caucasian negatives ('no Caucasian traits') into EN episodes.
    - Non-human objects/evidence props return empty anchors and empty character negatives.
    """
    # 1. Non-human evidence props, documents, metric tiles, artifacts
    is_object_key = any(k in fg_key.lower() for k in [
        "doc", "evidence", "object", "prop", "item", "meter", "invoice", "check",
        "paper", "artifact", "ledger", "gauge", "statute", "envelope", "stamp",
        "tile", "card", "board", "manifest"
    ])
    if is_object_key and not fg_key.lower().startswith("fg_character_") and not fg_key.lower().startswith("char_"):
        return "", ""

    m = (market or "EN").upper().strip()
    combined = f"{fg_key} {p}".lower()
    base_negs = prof.get("fg_negatives", "")

    # 2. English / Western / Global Markets (EN, US, UK, EU)
    if m in ["EN", "US", "UK"]:
        chroma_safe_negs = "no magenta, purple, fuchsia, or neon pink attire"
        likeness_negs = "no specific real-life likeness, no celebrity likeness"
        k_fg = fg_key.lower().replace("-", "_")

        # Step 2A: Explicit fg_key priority matching (guards against narrative word cross-talk)
        if "debtor" in k_fg and any(k in k_fg for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary reorganization debtor defense counsel or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated dark corporate business suit or tailored charcoal attire, disciplined and composed body posture defending reorganization filings, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["insurance", "carrier"]) and any(k in k_fg for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary insurance carrier defense litigator or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated dark tailored business suit, disciplined and analytical body posture reviewing coverage liabilities, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif "committee" in k_fg and any(k in k_fg for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary creditors' committee counsel or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "sharp dark professional attire, resolute analytical advocacy posture reviewing committee objections, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["fee_examiner", "examiner", "fee_auditor"]):
            anchor = (
                "Authentic contemporary court fee examiner or forensic billing auditor reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated professional office attire or gray tailored blazer, analytical posture reviewing billing ledgers with a pen, sharp focused forensic expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no clerical collar, no theatrical courtroom posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["journalist", "reporter", "court_reporter", "press"]):
            anchor = (
                "Authentic contemporary investigative journalist or court reporter reflecting authentic metropolitan demographic diversity, natural facial features, "
                "smart casual professional newsroom attire, engaged investigative posture reviewing docket records with a pen, observant inquisitive expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary plaintiffs' legal counsel or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated charcoal or dark navy professional attire, disciplined and composed body posture, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["judge", "magistrate"]):
            anchor = (
                "Authentic contemporary judicial professional reflecting authentic metropolitan demographic diversity, natural facial features, "
                "formal dark judicial attire, disciplined and composed body posture, solemn reserved expression, generic fictionalized official"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["cfo", "finance", "financial", "accountant", "auditor", "controller", "treasurer"]):
            anchor = (
                "Authentic contemporary financial officer or forensic accountant reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated dark corporate business suit or gray tailored blazer, disciplined body posture analyzing financial records, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no clerical collar, no ecclesiastical vestments, no religious robes, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["bishop", "clergy", "priest", "pastor", "reverend", "cardinal"]):
            anchor = (
                "Authentic contemporary ecclesiastical figure, natural facial features, "
                "formal clerical attire or ecclesiastical clergy vestments, reserved formal posture, "
                "solemn guarded expression, generic fictionalized ecclesiastical figure"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["legislator", "lawmaker", "senator", "representative", "parliamentarian", "congress"]):
            anchor = (
                "Authentic contemporary lawmaker or institutional legislator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "formal legislative committee business attire, dignified authoritative posture addressing statutory inquiry, "
                "resolute professional expression, generic fictionalized public official"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in k_fg for k in ["survivor", "claimant", "victim", "witness"]):
            anchor = (
                "Authentic contemporary individual reflecting authentic metropolitan demographic diversity, natural facial features, "
                "dignified everyday attire or modest contemporary civilian wardrobe, composed and restrained physical posture, "
                "steady reflective or somber emotive micro-expression, generic fictionalized individual"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no aggressive pointing, no theatrical courtroom posturing, no sensationalized trauma signaling, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        # Step 2B: Fallback matching on combined text (institutional roles checked BEFORE survivor/claimant)
        if any(k in combined for k in ["judge", "magistrate"]):
            anchor = (
                "Authentic contemporary judicial professional reflecting authentic metropolitan demographic diversity, natural facial features, "
                "formal dark judicial attire, disciplined and composed body posture, solemn reserved expression, generic fictionalized official"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif "debtor" in combined and any(k in combined for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary reorganization debtor defense counsel or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated dark corporate business suit or tailored charcoal attire, disciplined and composed body posture defending reorganization filings, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["insurance", "carrier"]) and any(k in combined for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary insurance carrier defense litigator or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated dark tailored business suit, disciplined and analytical body posture reviewing coverage liabilities, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif "committee" in combined and any(k in combined for k in ["counsel", "attorney", "lawyer", "litigator"]):
            anchor = (
                "Authentic contemporary creditors' committee counsel or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "sharp dark professional attire, resolute analytical advocacy posture reviewing committee objections, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["fee examiner", "examiner", "fee auditor"]):
            anchor = (
                "Authentic contemporary court fee examiner or forensic billing auditor reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated professional office attire or gray tailored blazer, analytical posture reviewing billing ledgers with a pen, sharp focused forensic expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no clerical collar, no theatrical courtroom posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["journalist", "reporter", "court reporter"]):
            anchor = (
                "Authentic contemporary investigative journalist or court reporter reflecting authentic metropolitan demographic diversity, natural facial features, "
                "smart casual professional newsroom attire, engaged investigative posture reviewing docket records with a pen, observant inquisitive expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["attorney", "counsel", "litigator", "lawyer"]):
            anchor = (
                "Authentic contemporary plaintiffs' legal counsel or institutional litigator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated charcoal or dark navy professional attire, disciplined and composed body posture, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no judicial robes, no theatrical courtroom posturing, no sensationalized posturing, no aggressive pointing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["cfo", "finance", "financial", "accountant", "auditor", "controller", "treasurer"]):
            anchor = (
                "Authentic contemporary financial officer or forensic accountant reflecting authentic metropolitan demographic diversity, natural facial features, "
                "understated dark corporate business suit or gray tailored blazer, disciplined body posture analyzing financial records, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no clerical collar, no ecclesiastical vestments, no religious robes, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["bishop", "clergy", "priest", "pastor", "reverend", "cardinal"]) or ("diocesan" in combined and not any(f in combined for f in ["cfo", "finance", "officer", "staff", "accountant", "auditor"])):
            anchor = (
                "Authentic contemporary ecclesiastical figure, natural facial features, "
                "formal clerical attire or ecclesiastical clergy vestments, reserved formal posture, "
                "solemn guarded expression, generic fictionalized ecclesiastical figure"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["legislator", "lawmaker", "senator", "representative", "parliamentarian", "congress"]):
            anchor = (
                "Authentic contemporary lawmaker or institutional legislator reflecting authentic metropolitan demographic diversity, natural facial features, "
                "formal legislative committee business attire, dignified authoritative posture addressing statutory inquiry, "
                "resolute professional expression, generic fictionalized public official"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["survivor", "victim", "claimant", "witness"]):
            anchor = (
                "Authentic contemporary individual reflecting authentic metropolitan demographic diversity, natural facial features, "
                "dignified everyday attire or modest contemporary civilian wardrobe, composed and restrained physical posture, "
                "steady reflective or somber emotive micro-expression, generic fictionalized individual"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no aggressive pointing, no theatrical courtroom posturing, no sensationalized trauma signaling, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in [
            "worker", "laborer", "engineer", "electrician", "technician", "operator", "infrastructure"
        ]):
            anchor = (
                "Authentic contemporary American/Western specialist or infrastructure engineer, natural facial features, "
                "durable professional utility workwear or high-visibility vest, dynamic focused posture handling technical documentation or infrastructure tools"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, {likeness_negs}" if base_negs else f"{chroma_safe_negs}, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in ["retail", "consumer", "investor", "shopper"]):
            anchor = (
                "Authentic contemporary American/Western individual, casual contemporary professional attire, "
                "expressive posture engaging with market documentation or mobile device, nuanced emotive micro-expression"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, {likeness_negs}" if base_negs else f"{chroma_safe_negs}, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        elif any(k in combined for k in [
            "analyst", "executive", "trader", "broker", "manager", "official",
            "director", "pm", "allocator", "financier", "banker"
        ]):
            anchor = (
                "Authentic contemporary professional or institutional analyst reflecting authentic metropolitan demographic diversity, natural facial features, "
                "bespoke corporate noir business attire or institutional suit, dynamic investigative body posture, sharp focused expression, generic fictionalized professional"
            )
            negs = f"{base_negs}, {chroma_safe_negs}, no theatrical courtroom posturing, no sensationalized posturing, {likeness_negs}"
            return anchor, f", {negs}" if negs else ""

        else:
            fg_anchor = prof.get("fg_anchor", "Authentic contemporary Western individual, natural facial features, contemporary attire")
            negs = f"{base_negs}, {chroma_safe_negs}, {likeness_negs}" if base_negs else f"{chroma_safe_negs}, {likeness_negs}"
            return fg_anchor, f", {negs}" if negs else ""

    # 3. Japanese Market (JP)
    elif m == "JP":
        if any(k in combined for k in ["chinese", "china", "foreign_worker", "regional_worker", "import_broker"]) and not any(k in combined for k in ["japanese", "tokyo", "quarantine", "mhlw"]):
            anchor = (
                "Authentic Chinese individual from regional agricultural or industrial processing sector, "
                "distinct East Asian facial structure with weathered pragmatic demeanor, durable regional utilitarian "
                "workwear or protective processing apron and rubber gloves, dynamic posture of manual inspection or harvest labor, "
                "active interaction with regional agricultural produce and processing tools"
            )
            negs = f"{base_negs}, no Japanese salaryman suit, no corporate sha-sho lapel pin badge, no Japanese inkan hanko seal, no Western Caucasian traits"
            return anchor, f", {negs}" if negs else ""
        elif any(k in combined for k in ["quarantine", "inspector", "customs", "officer", "analyst", "chemist", "lab", "mhlw", "kasumigaseki"]):
            anchor = (
                "Authentic Japanese individual, Authentic Japanese public official or quarantine inspection specialist, distinct Japanese facial structure, "
                "institutional inspection uniform or pristine business attire with ID lanyard, "
                "dynamic investigative body posture examining official records, intense focused glare"
            )
            negs = f"{base_negs}, no Caucasian traits, no passport photo posture"
            return anchor, f", {negs}" if negs else ""
        elif any(k in combined for k in ["consumer", "shopper", "supermarket", "chef", "cook", "ramen", "housewife"]):
            anchor = (
                "Authentic Japanese individual, consumer or culinary professional, natural East Asian eye shape, "
                "casual contemporary Japanese domestic attire or professional apron, dynamic expressive posture, "
                "closely inspecting packaged product with nuanced micro-expression of concern"
            )
            negs = f"{base_negs}, no Caucasian traits, no passport photo posture"
            return anchor, f", {negs}" if negs else ""
        else:
            fg_anchor = prof.get("fg_anchor", "Authentic Japanese individual, distinct East Asian facial structure, contemporary attire")
            return fg_anchor, f", {base_negs}" if base_negs else ""

    # 4. Korean Market (KR)
    elif m == "KR":
        anchor = prof.get("fg_anchor", "Authentic contemporary Korean individual, natural Korean facial features, contemporary attire")
        return anchor, f", {base_negs}" if base_negs else ""

    # Fallback generic
    fg_anchor = prof.get("fg_anchor", "Authentic individual appropriate to narrative context, contemporary attire")
    fg_negs = f", {prof['fg_negatives']}" if prof.get("fg_negatives") else ""
    return fg_anchor, fg_negs


def _sanitize_foreground_prompt(prompt: str, fg_key: str = "", is_byzantine: bool = False, market: str = "EN", tokens: list | None = None) -> str:
    """Sanitize and enforce Rule 116 & Rule 435 standards for Layer 2 Foreground prompts with Market Ethnicity Conformance."""
    p = _sanitize_evidence_notes(prompt.strip())

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

    # Strip previous style mandate without swallowing the core character description
    p = re.sub(r"\[STYLE MANDATE[^\]]*\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(
        r"Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration, clean bold ink linework, cel-shading, rich (?:nuanced colors|tactile paper and material textures), 1:1 aspect ratio, (?:waist-up three-quarter angle action framing, active hands and upper figure visible within frame|centered investigative artifact, crisp paper-cutout sticker aesthetic), isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames\.?,?\s*",
        "",
        p,
        flags=re.IGNORECASE
    )
    p = re.sub(r"\[ACTION & GAZE INVARIANT\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[MARKET & ETHNIC ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[ERA ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[OBJECT FOCUS\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[CAMERA & PERSPECTIVE\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[LIGHTING & OPTICS\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[OPTICAL STYLE\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(r"The image contains no writing or readable digits of any kind in any language\.?", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*actively holding up documentary evidence prop with one hand while (?:pointing index finger at critical detail|presenting critical detail)", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*composed posture holding a folded personal document [^,]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*solemn reserved posture [^,]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*addressing the committee assembly [^,]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:dynamic high-stakes body posture|dignified composed posture|solemn restrained posture)[^,]*, body turned 20 degrees toward active evidence zone", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:intense facial micro-expressions|composed emotive micro-expressions|solemn guarded micro-expressions)[^,.]*", "", p, flags=re.IGNORECASE)
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
    p = re.sub(r",?\s*(?:isolated\s+on\s+(?:a\s+solid\s+)?flat|isolated\s+on\s+flat|isolated\s+on\s+a\s+solid|isolated\s+on)\s*#FF00FF\s*(?:pure\s+)?(?:magenta\s+)?background.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:on\s+a\s+solid\s+flat|on\s+flat|solid\s+flat|flat\s+solid)\s*#FF00FF.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:isolated\s+on(?:\s+a)?(?:\s+solid)?(?:\s+flat)?\s*(?:#FF00FF)?(?:\s+pure)?(?:\s+magenta)?(?:\s+background)?)", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*#FF00FF[^,.]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[OPTICAL STYLE\][^\].]*\b(?:metric counter|mechanical counter|counter spinning|counter)\b[^.]*\.?", "", p, flags=re.IGNORECASE)
    p = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:1:1|16:9|21:9|32:9)\s+aspect\s+ratio", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:isolated\s+on(?:\s+a)?|\bon\b|\bwith\b|\bat\b)\s*$", "", p.strip(), flags=re.IGNORECASE)
    p = p.rstrip(",. ").strip()
    p = re.sub(r"\bclothing\s*[,.]\s*", "", p, flags=re.IGNORECASE)

    # String-join, chroma artifact, isolation breach, caption collision, and gaze cleaners
    p = re.sub(r"(?:pink|clothing)\.pure flat", "clothing.", p, flags=re.IGNORECASE)
    p = re.sub(r"\b(?:pure\s+flat|flat\s+pure)\b\.?", "", p, flags=re.IGNORECASE)
    p = re.sub(r"(?:\.|\,)?\s*\bFlat\b(?:\.|\,)?\s*$", "", p.strip(), flags=re.IGNORECASE)
    p = re.sub(r"\bFlat\s*,\s*", "", p)
    p = re.sub(r",\s*Flat\b", "", p)
    p = re.sub(r"\bFlat\b\.?", "", p)
    p = re.sub(r"\b(?:Bottomkept|Bottomheld|Bottomreserved|Bottomis)\b", "bottom safe-zone", p, flags=re.IGNORECASE)
    p = re.sub(r"\bOaklands\b", "Oakland's", p)
    p = re.sub(r"\bABbill\b", "legislative assembly bill", p, flags=re.IGNORECASE)
    p = re.sub(r"\bAB\s*\d+\b", "legislative assembly bill", p, flags=re.IGNORECASE)
    # Isolation breach & table contact fixes (preserve pure #FF00FF cutout)
    p = re.sub(r"\bslapping a stack onto a counter\b", "holding a bound case-file portfolio in both hands", p, flags=re.IGNORECASE)
    p = re.sub(r"\bonto a (?:counter|table|desk|podium)\b", "in hand", p, flags=re.IGNORECASE)
    p = re.sub(r"\bslapping\b", "firmly presenting", p, flags=re.IGNORECASE)
    # Caption collide with negative prompt fix & anti-pointing gesture guard
    p = re.sub(r"\bpointing\s+at\s+(?:the\s+)?top\s+(?:caption|document\s+page|page)\b", "resting two fingers on the top page (blank surface, no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\btop caption\b", "top page", p, flags=re.IGNORECASE)

    # Text-bait, named legal document, and typography trigger purging (Rule 137 & Opus 5.5 Gate)
    p = re.sub(r"\b(?:bound\s+plan\s+exhibit\s+)?page\s+titled\s+['\"]?Trust\s+Funding['\"]?", "bound plan exhibit page (blank legal document folio without typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\bpage\s+titled\s+['\"]?[A-Za-z0-9\s_-]+['\"]?(?=\s+gaze|\s*,|\s*\.|\s+with|\s*$)", "blank legal document folio (no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\btitled\s+['\"]?[A-Za-z0-9\s_-]+['\"]?(?=\s+gaze|\s*,|\s*\.|\s+with|\s*$)", "with official blank header block (no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\bpage\s+titled\b", "blank legal document folio (no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\btitled\b", "with official blank header block", p, flags=re.IGNORECASE)
    p = re.sub(r"(?:typed\s+in\s+the\s+caption|with\s+the\s+caption|each\s+caption\s+reading|captions?\s+reading)\s*[^,.]*(?:\.\s*[^,.]*)?", "with blank official header blocks (no glyphs, no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"with\s+(?:spine\s+)?label\s+[^,.]*", "with blank spine label insert (no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\bheadline(?:\s+reading)?\s*[^,.]*", "abstract banner graphic without typography", p, flags=re.IGNORECASE)
    p = re.sub(r"\bsignage(?:\s+reading)?\s*[^,.]*", "civic plaque texture without typography", p, flags=re.IGNORECASE)

    # Sanitizer truncation repairs & non-aggressive gesture enforcement
    p = re.sub(r"\bsummary\s+showing\s*,?\s*jabbing\s+it\s+with\s+an\s+index\s+finger\b", "showing an official ledger summary, resting an index finger on the document", p, flags=re.IGNORECASE)
    p = re.sub(r"\bjabbing\s+it\s+with\s+an\s+index\s+finger\b", "resting an index finger on the document", p, flags=re.IGNORECASE)
    p = re.sub(r"\bjabbing\b", "indicating with an open hand", p, flags=re.IGNORECASE)
    p = re.sub(r"\bshowing\s*,\s*", "showing an official record, ", p, flags=re.IGNORECASE)
    p = re.sub(r"\benvelope\s+stamped\s*,?\s*gaze\b", "ballot envelope with embossed seal, gaze", p, flags=re.IGNORECASE)
    p = re.sub(r"\bstamped\s*,", "with embossed seal,", p, flags=re.IGNORECASE)

    # Reconcile signature actions with negative prompt
    p = re.sub(r"\bsigning\s+a\s+document\b", "holding a document ready for execution", p, flags=re.IGNORECASE)
    p = re.sub(r"\bsignature\s+line\b", "blank execution line", p, flags=re.IGNORECASE)

    # Printed documents, court orders, and legislative bills
    p = re.sub(r"holding\s+[^,.]*?aloft\s+in\s+one\s+hand\s+and\s+pointing\s+at\s+[^,.]*?with\s+the\s+other(?:,\s*gaze\s+directed\s+down\s+at\s+the\s+page)?", "holding a bound legislative bill document at chest height (blank pages with illegible abstract line-marks only, no glyphs, no typography) in one hand while resting a hand flat on the open page, gaze directed down at the page", p, flags=re.IGNORECASE)
    p = re.sub(r"\bindicating\s+a\s+highlighted\s+abstract\s+block\b", "resting a hand flat on the open page", p, flags=re.IGNORECASE)
    p = re.sub(r"\btext\s+aloft\b", "document at chest height", p, flags=re.IGNORECASE)
    p = re.sub(r"\bprinted\s+California\s+Assembly\s+Bill(?:\s+No\.)?(?:\s+chaptered)?", "Official legislative bill document (blank template with illegible abstract line-marks only, no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\bprinted\s+order\s+of\s+dismissal\b", "bound order of dismissal (blank legal paper with illegible abstract line-marks only, no typography)", p, flags=re.IGNORECASE)
    p = re.sub(r"\bprinted\s+on\s+cream\s+ledger\s+paper\b", "rendered on cream ledger paper texture (unlabeled abstract geometric bars, no typography, no digits)", p, flags=re.IGNORECASE)
    p = re.sub(r"\bprinted\s+(?:bill\s+text|document\s+text|order|bill|filing|statute|text)\b", "bound document", p, flags=re.IGNORECASE)
    p = re.sub(r"\bprinted\b", "bound", p, flags=re.IGNORECASE)

    # Marked passage and labeled (enforce yellow marker ink to prevent magenta #FF00FF keyout holes)
    p = re.sub(r"\b(?:highlighted\s+statute\s+of\s+limitations\s+section|highlighted\s+document\s+section|marked\s+passage)\b", "highlighted with fluorescent yellow marker ink abstract block", p, flags=re.IGNORECASE)
    p = re.sub(r"\bhighlighted\b(?!\s+(?:with\s+yellow|in\s+yellow|yellow))", "highlighted with fluorescent yellow marker ink", p, flags=re.IGNORECASE)
    p = re.sub(r"\bhighlighting\b(?!\s+(?:with\s+yellow|in\s+yellow|yellow))", "highlighting with fluorescent yellow marker ink", p, flags=re.IGNORECASE)
    p = re.sub(r"\b(?:tall\s+bar\s+)?labeled,?", "with abstract shading,", p, flags=re.IGNORECASE)
    p = re.sub(r"\blabeled\b", "abstractly shaded", p, flags=re.IGNORECASE)
    p = re.sub(r"\bcase\s+number\s*-\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\ba\s+bold\s+[A-Z\s]+\s+clerk\s+stamp\b", "an embossed circular court clerk seal stamp", p, flags=re.IGNORECASE)
    p = re.sub(r"\bNo\.\s*", "", p)
    p = re.sub(r"\bDoe\s+v\.\s+[^,.]*", "unnamed civil lawsuit filing", p, flags=re.IGNORECASE)
    p = re.sub(r"\btop document page\b", "top document page (blank surface, no typography)", p, flags=re.IGNORECASE)

    # Text-bait and named legal document removal with grammatical consistency
    p = re.sub(r"\ba\s+(?:confidential\s+)?proof\s+of\s+claim\s+form\b", "a folded sheaf of legal claim papers", p, flags=re.IGNORECASE)
    p = re.sub(r"\b(?:confidential\s+)?proof\s+of\s+claim\s+form\b", "folded sheaf of legal claim papers", p, flags=re.IGNORECASE)
    p = re.sub(r"\ba\s+folded\s+legal\s+claim\s+papers\b", "a folded sheaf of legal claim papers", p, flags=re.IGNORECASE)
    p = re.sub(r"\bAlameda County Superior Court civil complaints\b", "thick stack of bound legal filings", p, flags=re.IGNORECASE)
    p = re.sub(r"\bSuperior Court civil complaints\b", "bound legal filings", p, flags=re.IGNORECASE)
    p = re.sub(r"\bin hand with one hand\b", "in one hand", p, flags=re.IGNORECASE)

    # Prop-text mitigation: ensure legal/documentary props specify illegible abstract markings
    p = re.sub(r"\b(folded sheaf of legal claim papers|bound legal filings|legislative assembly bill folio|bound case-file portfolio|bound order of dismissal)(?!\s*\(blank legal papers)\b", r"\1 (blank legal papers with illegible abstract line-marks only, no glyphs, no typography)", p, flags=re.IGNORECASE)
    # Gaze direction correction: screen-right points out of frame on center-right overlays, flip to screen-left
    p = re.sub(r"\bgaze\s+locked\s+screen-left\s+on\s+(?:the\s+stack|documents?|filings?)\b", "gaze directed screen-left toward the judicial bench", p, flags=re.IGNORECASE)
    p = re.sub(r"\bgaze directed screen-right\b", "gaze directed screen-left toward evidence zone", p, flags=re.IGNORECASE)
    p = re.sub(r"\bscreen-right\b", "screen-left", p, flags=re.IGNORECASE)
    # Clothing color guardrail: ensure 'or pink clothing' is never garbled into 'or clothing'
    p = re.sub(r"\bor clothing\b", "or pink clothing", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*no magenta, purple, fuchsia, or (?:neon\s+)?(?:pink|clothing|attire)\.?,?\s*", " ", p, flags=re.IGNORECASE)
    p = re.sub(r"(?:^|[\s,])clothing\s*[,.]\s*", " ", p, flags=re.IGNORECASE)

    prof = resolve_market_profile(market)
    fg_anchor, fg_negs = resolve_character_anchor(fg_key, p, market, prof)

    tokens_clauses = []
    if tokens:
        resolved = resolve_cinematic_tokens(tokens)
        if resolved["lighting_directives"]:
            tokens_clauses.append(f"[LIGHTING & OPTICS] {', '.join(resolved['lighting_directives'])}.")
        if resolved["vfx_directives"]:
            tokens_clauses.append(f"[OPTICAL STYLE] {', '.join(resolved['vfx_directives'])}.")
    fg_flow_str = f" {' '.join(tokens_clauses)}" if tokens_clauses else ""

    # Detect if foreground is an investigative object/document/evidence rather than a human character
    character_indicators = [
        "investigator", "prosecutor", "senator", "caretaker", "official", "executive",
        "judge", "lawyer", "person", "man", "woman", "pilot", "whistleblower", "ceo",
        "director", "agent", "founder", "figure", "character", "analyst", "auditor",
        "individual", "politician", "plaintiff", "defendant", "officer", "inspector",
        "specialist", "worker", "farmer", "harvester", "laborer", "operator", "chef",
        "cook", "shopper", "consumer", "housewife", "trader", "broker", "manager", "chemist"
    ]
    has_character = any(ci in p.lower() for ci in character_indicators)

    evidence_keywords = [
        "document", "docket", "complaint", "lawsuit", "court filing", "subpoena",
        "contract", "invoice", "receipt", "ledger", "bank check", "wire transfer",
        "algorithm", "meter", "gauge", "dial", "search box", "sponsored", "search card",
        "evidence", "folder", "binder", "stamp", "hanko", "seal", "prop", "artifact",
        "server rack", "microchip", "circuit", "hard drive", "tape recorder",
        "dossier", "newspaper clipping", "blueprint", "flowchart", "infographic", "tile"
    ]
    is_character_key = (
        fg_key.lower().startswith("fg_character_") or
        fg_key.lower().startswith("char_") or
        any(k in fg_key.lower() for k in ["character", "harvester", "inspector", "officer", "worker", "shopper", "consumer", "chef"])
    )
    is_object_key = any(k in fg_key.lower() for k in ["doc", "evidence", "object", "prop", "item", "meter", "invoice", "check", "paper", "artifact", "ledger", "gauge", "statute", "envelope", "stamp", "tile"])
    has_evidence_kw = any(kw in p.lower() for kw in evidence_keywords)

    if is_character_key:
        is_object = False
    elif is_object_key:
        is_object = True
    else:
        has_character = any(re.search(rf"\b{re.escape(ci)}\b", p, re.IGNORECASE) for ci in character_indicators)
        if has_character and ("official legal" in p.lower() or "official filing" in p.lower() or "official ftc" in p.lower() or "bold figure" in p.lower()):
            has_character = False
        is_object = has_evidence_kw and not has_character

    # Strip static passport posture relics before linting
    p = re.sub(r",?\s*(?:full-body\s+head-to-shoes|standing\s+head-to-toe|head\s+to\s+toe\s+visible)", "", p, flags=re.IGNORECASE)

    # Rule 137: Sanitize visual prompt through linter (is_prop=is_object ensures characters never receive blank document template)
    lint_res = lint_visual_prompt(p, strict=False, is_prop=is_object)
    p = lint_res.prompt.replace(R137_CLOSING_DIRECTIVE, "").rstrip(". ,")
    p = re.sub(r"\bOaklands\b", "Oakland's", p)
    p = re.sub(r"\bABbill\b", "legislative assembly bill", p, flags=re.IGNORECASE)
    p = re.sub(r"\b(?:Bottomkept|Bottomheld|Bottomreserved|Bottomis)\b", "bottom safe-zone", p, flags=re.IGNORECASE)
    p = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", p, flags=re.IGNORECASE)
    p = re.sub(r",?\s*(?:1:1|16:9|21:9|32:9)\s+aspect\s+ratio", "", p, flags=re.IGNORECASE)

    if is_object:
        p = re.sub(r"\bFull-body\s+", "", p, flags=re.IGNORECASE)
        p = re.sub(r"\s*figure\s+in\s+authentic\s+(?:period|professional)\s+attire", "", p, flags=re.IGNORECASE)
        era_anchor = resolve_era_anchor(fg_key, p)
        style_prefix = "[STYLE MANDATE] Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration, clean bold ink linework, cel-shading, rich tactile paper and material textures, 1:1 aspect ratio, centered investigative artifact, crisp paper-cutout sticker aesthetic, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames."

        # Category-aware negative prompts: data visualizations/charts must not include "no charts" or "no chart values"
        is_data_viz = any(kw in fg_key.lower() or kw in p.lower() for kw in [
            "chart", "histogram", "waterfall", "graph", "tabulation", "infographic", "diagram"
        ])
        if is_data_viz:
            filtered_r137 = ", ".join([clause.strip() for clause in NEGATIVE_R137.split(",") if "chart" not in clause.lower()])
            obj_negs = f"no human body, no photorealistic human, no 3D render, no CGI skin, no white background, no gray background, no halo, no cropped object, no cutoffs, no borders, no extraneous ui elements, no text, no numbers, no digits, no labels, no typography, {filtered_r137}"
        else:
            obj_negs = f"no human body, no photorealistic human, no 3D render, no CGI skin, no white background, no gray background, no halo, no cropped object, no cutoffs, no borders, no extraneous ui elements, no text, no numbers, no charts, no digits, no labels, no typography, {NEGATIVE_R137}"

        p = f"{style_prefix} {p}{fg_flow_str}. [OBJECT FOCUS] Highly detailed documentary evidence artifact, tactile physical realism with graphic novel editorial flair, forensic investigative prop with blank unfilled fields. [ERA ANCHOR] {era_anchor} [STRICT NEGATIVE PROMPT] {obj_negs}. {R137_CLOSING_DIRECTIVE}"
    else:
        # Vox Actor-Prop Invariant: Subject + Action Verb + Physical Prop + Gaze Target
        action_verbs = [
            "holding", "holds", "held", "pointing", "points", "pointed", "clutching", "clutches",
            "examining", "examines", "inspected", "inspecting", "inspects", "stamping", "stamps",
            "pressing", "presses", "pressed", "presenting", "presents", "presented", "gripping", "grips",
            "lifting", "lifts", "cutting", "cuts", "signing", "signs", "signed", "writing", "writes",
            "highlighting", "highlighted", "dialing", "dials", "opening", "opens", "pulling", "pulls",
            "pushing", "pushes", "turning", "turns", "counting", "counts", "sorting", "sorts",
            "checking", "checks", "reviewing", "reviews", "reviewed", "reaching", "reaches",
            "gesturing", "gestures", "running", "runs", "ran", "analyzing", "analyzes"
        ]
        has_action_verb = any(re.search(rf"\b{v}\b", p, re.IGNORECASE) for v in action_verbs)
        comb_fg = f"{fg_key} {p}".lower()
        is_legal_counsel = any(k in comb_fg for k in [
            "counsel", "attorney", "lawyer", "litigator", "examiner", "journalist", "reporter", "auditor", "cfo", "finance"
        ])
        is_claimant_or_survivor = any(k in comb_fg for k in ["survivor", "victim", "claimant"]) and not is_legal_counsel
        existing_prop = any(re.search(rf"\b{pr}\b", p, re.IGNORECASE) for pr in [
            "envelope", "ballot", "folio", "portfolio", "docket", "bill", "filing", "ledger",
            "papers", "document", "sheet", "chart", "map", "clock", "meter"
        ])
        if has_action_verb or existing_prop:
            action_clause = ""
        elif is_claimant_or_survivor:
            action_clause = ", composed posture holding a folded personal document close with steady restrained hands"
        elif any(k in comb_fg for k in ["bishop", "clergy", "priest", "pastor"]):
            action_clause = ", solemn reserved posture with hands folded before them in deliberate silence"
        elif any(k in comb_fg for k in ["legislator", "lawmaker", "senator", "representative"]):
            action_clause = ", addressing the committee assembly with an open palm gesture over legislative folio"
        else:
            action_clause = ", actively holding up documentary evidence prop with one hand while pointing index finger at critical detail"

        if any(w in p.lower() for w in ["turned", "turn", "facing", "angled", "three-quarter"]):
            turn_clause = ""
        elif is_claimant_or_survivor:
            turn_clause = ", dignified composed posture, three-quarter angle framing"
        elif any(k in comb_fg for k in ["bishop", "clergy", "priest"]):
            turn_clause = ", solemn restrained posture, three-quarter angle framing"
        else:
            turn_clause = ", dynamic high-stakes body posture, dramatic physical posing, body turned 20 degrees toward active evidence zone"

        if is_claimant_or_survivor:
            gaze_clause = "composed emotive micro-expressions with steady reflective gaze"
            action_gaze_tag = "[ACTION & GAZE INVARIANT] Subject exhibiting dignified restraint, steady solemn gaze, holding personal record."
        elif any(k in comb_fg for k in ["bishop", "clergy", "priest"]):
            gaze_clause = "solemn guarded micro-expressions with restrained steady gaze"
            action_gaze_tag = "[ACTION & GAZE INVARIANT] Subject exhibiting solemn formal composure with guarded downward gaze."
        else:
            gaze_clause = "intense facial micro-expressions with sharp focused gaze locked onto evidence prop"
            action_gaze_tag = "[ACTION & GAZE INVARIANT] Subject actively manipulating physical documentary prop with clear hand gesture and directional gaze."

        era_anchor = resolve_era_anchor(fg_key, p)
        style_prefix = (
            "[STYLE MANDATE] Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration, "
            "clean bold ink linework, cel-shading, rich nuanced colors, 1:1 aspect ratio, "
            "waist-up three-quarter angle action framing, active hands and upper figure visible within frame, "
            "isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames."
        )
        p = (
            f"{style_prefix} {p}{action_clause}{fg_flow_str}{turn_clause}, "
            f"{gaze_clause}. "
            f"{action_gaze_tag} "
            f"[MARKET & ETHNIC ANCHOR] {fg_anchor}. "
            f"[ERA ANCHOR] {era_anchor} "
            f"[STRICT NEGATIVE PROMPT] no photograph, no photorealistic human, no 3D render, no CGI skin, no white background, no gray background, "
            f"no halo, no gradients, no cropped head, no cropped hands, no cutoffs, no borders, no ui elements, no text, no numbers, no charts, no labels, no typography, "
            f"no static standing figure with arms at sides, no empty passive hands, {NEGATIVE_R137}{fg_negs}. {R137_CLOSING_DIRECTIVE}"
        )

    p = deduplicate_phrase_stutter(p)
    p = re.sub(r",\s*\.\s*", ", ", p)
    p = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\bFlat\s*,\s*", "", p)
    p = re.sub(r",\s*Flat\b", "", p)
    p = re.sub(r"(?:\.|\,)?\s*\bFlat\b(?:\.|\,)?\s*", " ", p)
    p = re.sub(r"\bcirca\s*:\s*", "circa vintage era, ", p, flags=re.IGNORECASE)
    p = re.sub(r"\bChapter\s*(?:voluntary\s+)?petition\b", "federal bankruptcy reorganization petition", p, flags=re.IGNORECASE)
    # Scrub fused words resulting from upstream numeric stripping
    p = re.sub(r"\bturned\s*degrees\b", "turned 20 degrees", p, flags=re.IGNORECASE)
    p = re.sub(r"\bturneddegrees\b", "turned 20 degrees", p, flags=re.IGNORECASE)
    p = re.sub(r"\bcirca\s*\.", "circa contemporary era.", p, flags=re.IGNORECASE)

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

    # Rule 134 Adversarial Invariant: Ensure non-local foreign characters in JP market NEVER leak salaryman or hanko into positive prompt
    if any(k in f"{fg_key} {prompt}".lower() for k in ["chinese", "china", "foreign_worker", "supplier", "regional_worker"]):
        pos_part = p.split("[STRICT NEGATIVE PROMPT]")[0] if "[STRICT NEGATIVE PROMPT]" in p else p
        assert "salaryman" not in pos_part.lower(), f"❌ Market Anchor Bias detected: Chinese character positive prompt contains 'salaryman'!"
        assert "hanko" not in pos_part.lower(), f"❌ Market Anchor Bias detected: Chinese character positive prompt contains 'hanko'!"
        assert "sha-sho" not in pos_part.lower(), f"❌ Market Anchor Bias detected: Chinese character positive prompt contains 'sha-sho'!"

    return p


UNIVERSAL_VOX_ANIMATION_PROMPT = (
    "Tactile documentary stop-motion animation, visual paper collage elements slide smoothly into the frame, "
    "translucent textured masking tape firmly adheres to the corners, golden brass pushpins press into the board, "
    "taut red investigation yarn stretches and connects between evidentiary nodes, subtle organic paper curl and tactile drop shadow movement, "
    "slow controlled cinematic document reveal, editorial investigative motion graphics, 6-second clip, 1080p crisp."
)

ZERO_TEXT_STRICT_NEGATIVE = (
    "NO TEXT, NO NUMBERS, NO CHARTS, NO DIGITS, NO LABELS, NO TYPOGRAPHY, "
    "NO FINANCIAL FIGURES, NO PERCENTAGE SIGNS, NO SUBTITLES, NO WATERMARK, "
    "NO LOGOS, NO GRAPHS, NO INFOGRAPHICS. Pure physical stylized illustration only."
)


def sanitize_numerical_artifacts(text: str) -> str:
    """Strip numbers, currencies, percentages, and financial metrics from positive prompts to avoid baked AI numbers."""
    if not text:
        return ""
    aspect_masks = {
        "16:9": "__ASPECT_RATIO_16_9__",
        "1:1": "__ASPECT_RATIO_1_1__",
        "21:9": "__ASPECT_RATIO_21_9__",
        "32:9": "__ASPECT_RATIO_32_9__",
        "2.5D": "__CINEMA_TOKEN_2_5D__",
        "35mm": "__CINEMA_TOKEN_35MM__",
        "50mm": "__CINEMA_TOKEN_50MM__",
        "85mm": "__CINEMA_TOKEN_85MM__",
    }
    sanitized = text
    for raw_tok, mask_tok in aspect_masks.items():
        sanitized = re.sub(rf"\b{re.escape(raw_tok)}\b", mask_tok, sanitized, flags=re.IGNORECASE)

    sanitized = re.sub(r'[\$€£¥]?\d+(?:\.\d+)?\s*(?:B|M|K|T|%|billion|trillion|bn|tn)?\b', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\b\d+\b', '', sanitized)

    for raw_tok, mask_tok in aspect_masks.items():
        sanitized = sanitized.replace(mask_tok, raw_tok)

    sanitized = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\s{2,}', ' ', sanitized).strip()
    return sanitized


def _sanitize_vox_collage_prompt(
    prompt: str,
    key: str = "",
    market: str = "EN",
    tokens: list | None = None
) -> str:
    """Sanitize and format 16:9 VOX Tactile Documentary Collage prompt (Rule 116, 122 & 128)."""
    p = sanitize_numerical_artifacts(prompt.strip())
    p = re.sub(r"\[STYLE MANDATE[^\]]*\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[MARKET & ENVIRONMENT ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)

    # Protect non-photorealistic
    p = re.sub(r"\bnon-photorealistic\b", "__NON_PHOTO__", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic\s*(?:8k)?\s*", "", p, flags=re.IGNORECASE)
    p = p.replace("__NON_PHOTO__", "non-photorealistic")
    p = re.sub(r"\bnon-\s*2d\b", "non-photorealistic 2D", p, flags=re.IGNORECASE)
    p = re.sub(r"\b8k\b", "", p, flags=re.IGNORECASE)

    # Strip non-ASCII / CJK glyphs from English visual prompts (Rule 446)
    p = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()

    # Rule 137: Sanitize visual prompt through linter
    lint_res = lint_visual_prompt(p, strict=False)
    p = lint_res.prompt.replace(R137_CLOSING_DIRECTIVE, "").rstrip(". ,")

    prof = resolve_market_profile(market)
    market_negs = f", {prof['fg_negatives']}" if prof.get("fg_negatives") else ""

    tokens_clauses = []
    if tokens:
        resolved = resolve_cinematic_tokens(tokens)
        if resolved["camera_directives"]:
            tokens_clauses.append(f"[PERSPECTIVE] {', '.join(resolved['camera_directives'])}.")
        if resolved["lighting_directives"]:
            tokens_clauses.append(f"[LIGHTING] {', '.join(resolved['lighting_directives'])}.")
    flow_str = f" {' '.join(tokens_clauses)}" if tokens_clauses else ""

    style_prefix = (
        "[STYLE MANDATE: VOX TACTILE DOCUMENTARY COLLAGE] 16:9 widescreen physical paper-and-cardboard collage assembly, "
        "tactile editorial journalistic investigation aesthetic, macro physical depth of field, micro drop shadows between layered physical elements, "
        "aged vintage archival newspaper and docket paper background, centered dark charcoal cardboard photo mat secured at 4 corners with "
        "translucent textured masking tape (scotch tape) with subtle adhesive wrinkles and visible newsprint underneath, "
        "crisp 2mm off-white die-cut paper borders on cutout exhibits, brass pushpins, taut red investigation yarn connecting nodes, "
        "weathered typewriter serif label strip, bottom 20% safe-zone clear for subtitles."
    )
    strict_negatives = (
        f"[STRICT NEGATIVE PROMPT] no 3D CGI render, no smooth digital vector illustration, no clean studio portrait, "
        f"no text, no numbers, no charts, no digits, no labels, no typography, no financial figures, no written words, "
        f"no green screen, no purple chroma, no purple halo, no watermark, no digital overlays, no floating text in bottom subtitle zone, "
        f"{NEGATIVE_R137}{market_negs}. {R137_CLOSING_DIRECTIVE}"
    )

    if "16:9" not in p:
        p = f"{p}, 16:9 aspect ratio"

    p = f"{style_prefix} {p}{flow_str} {strict_negatives}"
    return deduplicate_phrase_stutter(p)


def _synthesize_vox_collage_prompt(
    bg_desc: str,
    fg_desc: str = "",
    object_focus: dict = None,
    market: str = "EN",
    scene_idx: int = 1,
    tokens: list = None
) -> str:
    """
    Synthesizes a complete 16:9 VOX Tactile Documentary Collage prompt from scene metadata
    combining Base Texture + Tape-Affixed Dark Card Mat + Halftone Die-Cut Cutouts + Brass Pushpins + Red Yarn + Blank Label Strip.
    Enforces Rule 128 & Zero-Semantic-Bias: NEVER bake in numbers or metrics onto images.
    """
    clean_bg = sanitize_numerical_artifacts(bg_desc.strip())
    clean_fg = sanitize_numerical_artifacts(fg_desc.strip()) if fg_desc else ""
    clean_fg = re.sub(r"#FF00FF|magenta|isolated on|clean chroma-key", "", clean_fg, flags=re.IGNORECASE).strip()

    obj_title = ""
    obj_type = "investigative evidence"
    if object_focus and isinstance(object_focus, dict):
        obj_type = object_focus.get("type") or "investigative document"
        obj_title = sanitize_numerical_artifacts(object_focus.get("title") or "")

    if obj_title:
        exhibit_desc = f"a high-contrast vintage halftone black-and-white print cutout of {obj_type} '{obj_title}' with a distinct 2mm off-white die-cut paper border"
    elif clean_fg:
        exhibit_desc = f"a high-contrast vintage halftone print cutout illustration of {clean_fg[:90]} with a distinct 2mm off-white die-cut paper border"
    else:
        exhibit_desc = f"vintage archival documents and investigative evidence clippings of {clean_bg[:80]} with 2mm off-white die-cut paper borders"

    body = (
        f"A multi-layered physical documentary assemblage centered on {exhibit_desc}. "
        f"The exhibit is mounted upon a thick dark charcoal cardboard mat, firmly pinned with golden brass thumbtacks. "
        f"Taut crimson red investigation yarn connects the brass pins to secondary evidentiary nodes and document clippings across the board. "
        f"At the bottom of the card mat, a weathered blank off-white paper specimen label strip is affixed with translucent scotch tape. "
        f"The entire dark card mat is fastened onto an aged vintage newspaper archive surface with faint weathered paper grain and an antique cartographic map chart, "
        f"held down at each corner with textured translucent masking tape showing the newsprint beneath. "
        f"Cinematic documentary lighting, realistic macro tactile texture, natural soft drop shadows cast by each physical paper layer."
    )

    return _sanitize_vox_collage_prompt(body, key=f"vox_sc_{scene_idx:03d}", market=market, tokens=tokens)


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
    p = re.sub(r"(?<!\d),?\s*:\s*(?:aspect\s*ratio|\d+\s*aspect\s*ratio)", "", p, flags=re.IGNORECASE)
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

    # Prepare strategic prompt for Claude Opus 5
    b35_rules = get_b35_strategic_rules()
    system_prompt = (
        "You are the Lead Cinematographer and Visual Concept Artist (Claude Opus 5) for AI Video Factory.\n"
        "Your mission is to forge production-ready image prompts for two distinct visual layers per scene:\n"
        "  - Layer 1 Background (16:9 2560x1440): Wide environmental setting, cinematic lighting, subtitle safe-zone.\n"
        "  - Layer 2 Foreground (1:1 2048x2048): Stylized editorial graphic novel digital illustration isolated on pure #FF00FF magenta chroma key.\n\n"
        f"TARGET MARKET CONTEXT (RULE 122 & RULE 128): {market_prof['market_name']} (Code: {market_prof['market_code']})\n"
        f"  - Foreground Character Phenotype Mandate: {market_prof['fg_anchor']}\n"
        f"  - Background Architecture & Environment Mandate: {market_prof['bg_anchor']}\n\n"
        "CRITICAL ARCHITECTURAL MANDATES (RULE 116 & RULE 435 & RULE 122 & RULE 128):\n"
        f"1. MARKET ETHNICITY & REGIONAL FIDELITY (Rule 122): Strictly adhere to target market {market_prof['market_name']}. "
        "Characters MUST feature authentic ethnic phenotype, bone structure, eye shape, and hairstyles matching this market. "
        "NEVER default to Caucasian, Western, or American facial features for Asian markets (JP/KR)! "
        "Backgrounds MUST feature authentic local corporate/urban architecture and atmosphere matching this market. "
        "NEVER default to generic American high-rises for Asian settings!\n"
        "2. ERA & TOPIC AUTHENTICITY (Rule 128): Strictly derive era, architectural style, atmosphere, color palette, and lighting dynamically from the episode topic and scene narration. Zero domain bleed.\n"
        "3. SCENE SEMANTIC COUPLING: Maintain 100% semantic unity between each Background and its paired Foreground character. The setting, time period, indoor/outdoor lighting angle, and mood MUST match between paired assets in each scene.\n"
        "4. LAYER 1 BACKGROUND PROMPT RULES (16:9):\n"
        "   - Minimalist Vox-style editorial paper collage background, heavy 300gsm aged fibrous paper texture.\n"
        "   - Muted geometric shapes (large circle, rectangular grid), limited color palette (VOX Yellow #EAB308, muted navy, cream, charcoal).\n"
        "   - Plenty of negative space, zero clutter, zero realistic environment, high-contrast graphic novel composition.\n"
        "   - Authentic period architecture, environment textures, dramatic volumetric lighting.\n"
        "   - NO prominent human figures in the foreground. Leave center/right negative space clear for the Layer 2 character overlay.\n"
        "   - Leave the bottom 20% safe zone clear of critical visual elements for on-screen subtitles.\n"
        "   - Style: Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, rich spatial textures, moody chiaroscuro lighting, 16:9 aspect ratio.\n"
        "5. LAYER 2 FOREGROUND PROMPT RULES (1:1 - VOX ACTOR-PROP INVARIANT):\n"
        "   - NON-PHOTOREALISTIC, STYLIZED EDITORIAL GRAPHIC NOVEL DIGITAL ILLUSTRATION (clean bold ink linework, cel-shading, NOT a studio photograph).\n"
        "   - 5A. For CHARACTER keys ('fg_character_*' or 'char_*'): Every human character MUST satisfy the Vox Actor-Prop Invariant: Subject + Action Verb + Physical Prop + Gaze Target. Use waist-up three-quarter angle action framing, body turned 20 degrees toward active evidence zone, active hands manipulating a physical documentary prop (holding card/document, pointing index finger, stamping seal, inspecting ledger), directional gaze locked onto the prop. NEVER generate static passport photos, ID poses, or stiff standing figures with arms at sides. NEVER dress characters in magenta, purple, fuchsia, or neon pink clothing.\n"
        "   - 5B. For EVIDENCE PROP / DOCUMENT keys ('fg_evidence_*', dockets, ledgers, objects): Centered tactile forensic documentary artifact or physical prop ONLY. ZERO human figures, ZERO attire or body language, and ZERO readable text or digits (unfilled blank visual template).\n"
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
    is_mocked_astra = hasattr(call_gpt6_astra, "_mock_name") or "Mock" in type(call_gpt6_astra).__name__
    is_smoke = bool(
        os.getenv("VF_SMOKE_TEST")
        or os.getenv("FAST_ROSTER")
        or os.environ.get("PYTEST_CURRENT_TEST")
        or "pytest" in sys.modules
        or any("ci_neighbor_tester" in str(a) or "smoketest" in str(a) for a in sys.argv)
    )

    if is_mocked_astra:
        raw_response = call_gpt6_astra(json.dumps(user_payload, ensure_ascii=False), system_prompt=system_prompt)
    elif not is_smoke:
        gateway = get_global_gateway()
        for pf_attempt in range(1, 3):
            try:
                logger.info(f"[prompt_forge] Calling Claude Opus 5.5 for prompts (attempt {pf_attempt}/2, market={market}, fallback=gpt-6-astra)...")
                raw_response = gateway.call_llm(
                    prompt=json.dumps(user_payload, ensure_ascii=False),
                    system_prompt=system_prompt,
                    model="claude-opus-5-5",
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
                except Exception as _e_rec:
                    logger.debug("Recovery JSON parse failed: %s", _e_rec)

    if not parsed or not isinstance(parsed, dict):
        parsed = {"backgrounds": {}, "foregrounds": {}}

    bg_tokens_map = {}
    fg_tokens_map = {}
    if scenes:
        for sc in scenes:
            bg_k = sc.get("background_reuse_key") or sc.get("bg_id") or "bg_00"
            raw_fg = sc.get("foreground_reuse_key") or sc.get("fg_id") or None
            fg_k = str(raw_fg).strip() if raw_fg and str(raw_fg).strip() else None
            toks = sc.get("cinematic_tokens") or []
            if toks:
                bg_tokens_map.setdefault(bg_k, []).extend(toks)
                if fg_k:
                    fg_tokens_map.setdefault(fg_k, []).extend(toks)

    cleaned_backgrounds = {}
    cleaned_foregrounds = {}

    for k, p in parsed.get("backgrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_backgrounds[k] = _sanitize_background_prompt(prompt_str, k, market=market, tokens=bg_tokens_map.get(k))

    for k, p in parsed.get("foregrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_foregrounds[k] = _sanitize_foreground_prompt(prompt_str, k, market=market, tokens=fg_tokens_map.get(k))

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
            cleaned_backgrounds[bg_k] = _sanitize_background_prompt(fallback_bg, bg_k, market=market, tokens=bg_tokens_map.get(bg_k))

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
            is_obj = (
                fg_k.lower().startswith("fg_evidence_") or
                any(k in fg_k.lower() for k in [
                    "doc", "evidence", "object", "prop", "item", "meter", "invoice", "check",
                    "paper", "artifact", "ledger", "gauge", "statute", "envelope", "stamp",
                    "tile", "order", "binder", "drive", "gavel", "docket", "bill", "memo", "affidavit"
                ])
            ) and not fg_k.lower().startswith("fg_character_") and not fg_k.lower().startswith("char_")
            if is_obj:
                fallback_fg = (
                    f"Centred tactile forensic documentary evidence artifact of {hint}{paired_desc}, "
                    f"crisp paper cutout edges, official blank forensic template without text, "
                    f"isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio"
                )
            else:
                fallback_fg = (
                    f"Waist-up three-quarter angle {hint} figure in authentic professional attire{paired_desc}, "
                    f"active hands manipulating physical documentary prop, directional gaze locked onto prop, dramatic character rim light matching environment, "
                    f"isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio"
                )
            cleaned_foregrounds[fg_k] = _sanitize_foreground_prompt(fallback_fg, fg_k, market=market, tokens=fg_tokens_map.get(fg_k))

    # Synthesize VOX Tactile Documentary Collage prompts (16:9) & Universal Video prompts
    cleaned_vox_collages = {}
    animation_tiers = {}

    if scenes:
        for idx, sc in enumerate(scenes):
            bg_k = sc.get("background_reuse_key") or sc.get("bg_id") or "bg_00"
            raw_fg = sc.get("foreground_reuse_key") or sc.get("fg_id") or None
            fg_k = str(raw_fg).strip() if raw_fg and str(raw_fg).strip() else None

            bg_desc = cleaned_backgrounds.get(bg_k, "")
            fg_desc = cleaned_foregrounds.get(fg_k, "") if fg_k else ""
            obj_focus = sc.get("object_focus")
            toks = sc.get("cinematic_tokens") or []

            # Animation Tier: Cold Hook (0-15s) and pivotal clenching moments are Hero AI Video
            anim_tier = sc.get("animation_tier")
            if not anim_tier:
                anim_tier = "HERO_AI_VIDEO_6S" if (idx < 15 or idx % 7 == 0) else "TACTILE_STOPMOTION_STILL"

            vox_key = f"vox_sc_{idx+1:03d}_{bg_k}"
            cleaned_vox_collages[vox_key] = _synthesize_vox_collage_prompt(
                bg_desc=bg_desc,
                fg_desc=fg_desc,
                object_focus=obj_focus,
                market=market,
                scene_idx=idx+1,
                tokens=toks
            )
            animation_tiers[vox_key] = anim_tier
    else:
        # Fallback when only bg_dict and fg_dict are provided (e.g. basic unit tests)
        for idx, (bg_k, bg_meta) in enumerate(bg_dict.items()):
            bg_desc = cleaned_backgrounds.get(bg_k, "")
            paired_fg = list(fg_dict.keys())[0] if fg_dict else None
            fg_desc = cleaned_foregrounds.get(paired_fg, "") if paired_fg else ""
            vox_key = f"vox_{bg_k}"
            cleaned_vox_collages[vox_key] = _synthesize_vox_collage_prompt(
                bg_desc=bg_desc,
                fg_desc=fg_desc,
                market=market,
                scene_idx=idx+1
            )
            animation_tiers[vox_key] = "HERO_AI_VIDEO_6S" if idx == 0 else "TACTILE_STOPMOTION_STILL"

    result = {
        "vox_collages": cleaned_vox_collages,
        "universal_video_prompt": UNIVERSAL_VOX_ANIMATION_PROMPT,
        "animation_tiers": animation_tiers,
        "backgrounds": cleaned_backgrounds,
        "foregrounds": cleaned_foregrounds,
        "thumbnails": {}
    }
    logger.info(
        f"[prompt_forge] Successfully forged {len(cleaned_vox_collages)} VOX Collage prompts, "
        f"{len(cleaned_backgrounds)} BG prompts, {len(cleaned_foregrounds)} FG prompts for market {market} (Thumbnails decoupled to YouTube Studio HG3)"
    )
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
    except Exception as _e_tok:
        logger.debug("Token bridge error: %s", _e_tok)
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

    # 1b. VOX Collages (16:9 Tactile Documentary)
    for vox_key, prompt in prompts_data.get("vox_collages", {}).items():
        prompt_str = prompt if isinstance(prompt, str) else prompt.get("prompt", str(prompt))
        tier = prompts_data.get("animation_tiers", {}).get(vox_key, "TACTILE_STOPMOTION_STILL")
        vox_props = {
            "Title": {"title": [{"text": {"content": f"[{episode_id}] {vox_key} (VOX Collage 16:9)"}}]},
            "prompt_text": {"rich_text": [{"text": {"content": prompt_str[:2000]}}]},
            "category": {"select": {"name": "image"}},
            "variables": {"rich_text": [{"text": {"content": f"Aspect Ratio: 16:9, Style: VOX Tactile Documentary Collage, Tier: {tier}"}}]},
            "version": {"number": 1}
        }
        try:
            res = _bridge.create_page(prompt_library_db_id, vox_props)
            if not res.get("error"):
                logger.debug(f"[prompt_forge] Pushed VOX Collage prompt {vox_key} to Notion Prompt Library DB")
            else:
                logger.warning(f"[prompt_forge] Failed to push VOX Collage prompt {vox_key}: {res}")
        except Exception as e:
            logger.warning(f"[prompt_forge] Exception pushing VOX Collage prompt {vox_key}: {e}")

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
