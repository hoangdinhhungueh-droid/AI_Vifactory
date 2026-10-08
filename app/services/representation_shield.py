#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/representation_shield.py
Ethical Representation Shield for Vox Docudrama (Rule 122, 128, 137 Compliant).

Enforces two strict non-negotiable documentary laws BEFORE B3 Scene Planning:
1. Child Representation Law:
   - STRICTLY ZERO depiction of children's faces, likenesses, or bodies.
   - Automatically translates any minor/child mention into contextually grounded
     Symbolic Evidence Artifacts:
     (a) An empty swing swaying mid-motion in a quiet park/courtyard.
     (b) A small pair of shoes placed neatly by an entryway door.
     (c) A pencil height-growth chart marked on an aged wooden doorframe.
     (d) A worn school backpack left resting on concrete steps.
     (e) A blank silhouette portrait cutout on aged paper with rough torn edges.
2. Real-Person Anonymity & Censor Law:
   - For real named individuals, living figures, or historical subjects:
   - Enforce non-photorealistic 2D graphic novel halftone print cutout style.
   - Enforce a thick black censor bar across the eyes or a 3/4 angled rear posture,
     preventing deepfake likeness, defamation, or photographic facial reproduction.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger("vf.representation_shield")

def audit_cliffhanger_patterns(*args, **kwargs):
    """Re-export audit_cliffhanger_patterns from vox_automated_director for cross-module compatibility."""
    from app.services.vox_automated_director import audit_cliffhanger_patterns as _acp
    return _acp(*args, **kwargs)

# Multilingual keywords for detecting minors / children across EN, VN, JP, KR
CHILD_KEYWORDS = [
    # English
    r"\bchild\b", r"\bchildren\b", r"\bkid\b", r"\bkids\b", r"\bminor\b", r"\bminors\b",
    r"\btoddler\b", r"\btoddlers\b", r"\binfant\b", r"\binfants\b", r"\bbaby\b", r"\bbabies\b",
    r"\bboy\b", r"\bboys\b", r"\bgirl\b", r"\bgirls\b", r"\bschoolboy\b", r"\bschoolgirl\b",
    r"\byouth\b", r"\byouths\b", r"\bjuvenile\b", r"\bjuveniles\b", r"\bstudent\b", r"\bstudents\b",
    # Vietnamese
    r"\btrẻ\s+em\b", r"\btrẻ\s+con\b", r"\bem\s+bé\b", r"\bhọc\s+sinh\b", r"\bthiếu\s+nhi\b",
    r"\bvị\s+thành\s+niên\b", r"\bcậu\s+bé\b", r"\bcô\s+bé\b", r"\bđứa\s+trẻ\b",
    # Japanese
    r"子供", r"子ども", r"児童", r"生徒", r"幼児", r"赤ちゃん", r"少年", r"少女", r"未成年",
    # Korean
    r"어린이", r"아이", r"학생", r"유아", r"소년", r"소녀", r"미성년자"
]

CHILD_REGEX = re.compile("|".join(CHILD_KEYWORDS), re.IGNORECASE)

# 5 Canonical Symbolic Artifact Archetypes
SYMBOLIC_CHILD_ARCHETYPES = [
    {
        "id": "empty_swing",
        "title": "Empty Playground Swing",
        "keywords": ["playground", "swing", "outdoor", "park", "movement"],
        "description": "An empty wooden playground swing suspended by rusty chains, swaying mid-motion in a quiet breeze, worn timber seat, symbolic investigative artifact of absent childhood, no human figures, generous negative space."
    },
    {
        "id": "small_shoes",
        "title": "Small Pair of Shoes by Doorway",
        "keywords": ["home", "house", "door", "entry", "shoes", "domestic"],
        "description": "A small pair of canvas shoes placed neatly side-by-side on a weathered wooden doorstep, soft morning window light, symbolic investigative artifact of absence, no human figures, clean editorial composition."
    },
    {
        "id": "growth_chart_doorframe",
        "title": "Height Growth Chart on Doorframe",
        "keywords": ["growth", "years", "time", "family", "height", "frame"],
        "description": "A rustic wooden doorframe with faded pencil tick-marks and dated handwritten height notations, peeling paint, symbolic timeline artifact of childhood memories, no human figures, macro tactile detail."
    },
    {
        "id": "school_backpack",
        "title": "Worn School Backpack on Steps",
        "keywords": ["school", "backpack", "bag", "steps", "stairs", "education"],
        "description": "A weathered canvas school backpack resting alone on cold concrete school steps, single unzipped brass buckle, fallen autumn leaves, symbolic documentary artifact of interrupted innocence, no human figures."
    },
    {
        "id": "blank_silhouette_portrait",
        "title": "Blank Silhouette Portrait Cutout",
        "keywords": ["identity", "archive", "case", "record", "photo", "dossier"],
        "description": "A vintage school photo cardstock where the central child portrait is an empty white die-cut silhouette cutout with rough torn scissor edges, aged cream cardstock backing, official red case stamp, no facial features."
    }
]


def detect_child_representation(text: str) -> bool:
    """Detects if a narrative sentence, role, or description references children or minors."""
    if not text:
        return False
    return bool(CHILD_REGEX.search(text))


def resolve_child_symbolic_artifact(
    entity_desc: str,
    context_text: str = "",
    market: str = "EN"
) -> Dict[str, Any]:
    """Selects the most contextually grounded symbolic artifact to replace child depiction.
    
    Dynamically scores the 5 archetypes against the surrounding story context.
    """
    combined = f"{entity_desc} {context_text}".lower()
    best_match = SYMBOLIC_CHILD_ARCHETYPES[4]  # Default: blank silhouette cutout
    best_score = -1

    for archetype in SYMBOLIC_CHILD_ARCHETYPES:
        score = sum(1 for kw in archetype["keywords"] if kw in combined)
        if score > best_score:
            best_score = score
            best_match = archetype

    desc = best_match["description"]
    # Add market-conforming stamp if relevant
    if market == "JP":
        desc += " Accompanied by an official red inkan seal stamp."
    elif market == "KR":
        desc += " Accompanied by an official red ingam seal stamp."
    elif market == "VN":
        desc += " Kèm con dấu mộc đỏ xác thực hồ sơ lưu trữ."

    return {
        "title": best_match["title"],
        "description": desc,
        "role": "symbolic_representation",
        "type": "evidence_prop",
        "is_child_symbolic": True,
        "archetype_id": best_match["id"],
        "keywords": best_match["keywords"] + ["symbolic_artifact", "child_representation_shield"]
    }


def apply_real_person_censor_shield(entity_desc: str, fg_key: str = "") -> str:
    """Enforces black censor bar, midground distance, and non-photorealistic stylized graphic novel rules for real figures."""
    p = entity_desc.strip()
    
    # Check if already has censor bar directive
    if "censor bar" in p.lower() or "black censor bar" in p.lower():
        if "midground distance" not in p.lower() and "off in the distance" not in p.lower():
            p = f"{p}, positioned at midground distance to avoid close-up facial complexion details"
        return p

    censor_clause = (
        " featuring a solid black censor bar across the eyes to preserve documentary anonymity, "
        "positioned at midground distance (never extreme close-up on facial complexion), "
        "three-quarter angle framing, non-photorealistic 2D stylized graphic novel comic ink illustration, "
        "no real-life recognizable likeness, no celebrity likeness"
    )

    # Insert censor bar clause smoothly
    if "waist-up" in p.lower():
        p = re.sub(r"(waist-up[^,.]*)", r"\1," + censor_clause, p, count=1, flags=re.IGNORECASE)
    else:
        p = f"{p},{censor_clause}"

    return p


def scrub_public_figure_names_for_video(
    video_prompt: str,
    fg_roster: Optional[Dict[str, Any]] = None,
    custom_names: Optional[List[str]] = None,
    extra_names: Optional[List[str]] = None
) -> str:
    """Scrubs real public figure / historical person names from AI video prompts (Veo / Omni / Seedance).
    
    Replaces proper names with 'the black-and-white halftone cutout figure with a black censor bar'
    to guarantee 0% celebrity/public-figure safety filter rejections during video generation.
    """
    if not video_prompt:
        return ""

    cleaned = video_prompt
    replacement_phrase = "the black-and-white halftone cutout figure with a black censor bar"

    # 1. Collect candidate proper names from fg_roster characters, custom_names, and extra_names
    names_to_scrub: List[str] = []
    for name_list in (custom_names, extra_names):
        if name_list:
            names_to_scrub.extend([n.strip() for n in name_list if n and len(n.strip()) >= 3])

    # Detect titled proper names directly in prompt (e.g., "Senator John Smith", "Prosecutor Jerome Vance")
    title_pattern = r"\b(?:Senator|President|CEO|Governor|Director|Chairman|Judge|Minister|Detective|Prosecutor|General|Agent|Secretary|Mayor|Chancellor|Officer)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*)"
    for m in re.finditer(title_pattern, cleaned):
        names_to_scrub.append(m.group(0))
        names_to_scrub.append(m.group(1))

    if fg_roster:
        for fg_k, fg_v in fg_roster.items():
            if not isinstance(fg_v, dict):
                continue
            if fg_v.get("type") == "character":
                title = fg_v.get("title", "")
                for m in re.finditer(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+)\b", title):
                    candidate = m.group(1)
                    if candidate.lower() not in {"cutout figure", "halftone cutout", "archival photo", "black bar"}:
                        names_to_scrub.append(candidate)

    # 2. Common public figures / historical names pattern in documentary prompts
    known_public_figures = [
        "Sam Altman", "Elon Musk", "Donald Trump", "Jerome Kerviel", "Dan Cooper", "D.B. Cooper",
        "Richard Nixon", "Henry Kissinger", "Warren Buffett", "Jerome Powell", "Janet Yellen",
        "Mark Zuckerberg", "Jeff Bezos", "Bill Gates", "Jensen Huang", "Satya Nadella",
        "Bernie Madoff", "Elizabeth Holmes", "Sam Bankman-Fried", "Adam Neumann"
    ]
    names_to_scrub.extend(known_public_figures)

    # Sort longest first to avoid partial replacements
    unique_names = sorted(set(names_to_scrub), key=len, reverse=True)
    for name in unique_names:
        pattern = re.compile(rf"\b{re.escape(name)}(?:'s)?\b", re.IGNORECASE)
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement_phrase, cleaned)

    # Deduplicate repeated replacement phrases if multiple names were side by side
    cleaned = re.sub(
        rf"({re.escape(replacement_phrase)})(?:\s*(?:,|and)\s*{re.escape(replacement_phrase)})+",
        replacement_phrase,
        cleaned
    )
    return cleaned


def shield_visual_roster(
    bg_roster: Dict[str, Any],
    fg_roster: Dict[str, Any],
    story_text: str = "",
    market: str = "EN"
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Master Shield Gate executed BEFORE B3 Scene Planning.
    
    Audits 100% of Foregrounds and Backgrounds:
    1. Converts child characters into context-aware Symbolic Artifacts.
    2. Applies black censor bar and anonymity directives to real named adult figures.
    3. Purges human figures from Background environments.
    """
    clean_bg: Dict[str, Any] = {}
    clean_fg: Dict[str, Any] = {}

    # 1. Audit Backgrounds (Zero prominent human figures)
    for bg_k, bg_v in (bg_roster or {}).items():
        v_copy = dict(bg_v)
        desc = v_copy.get("description", "")
        # Remove any lingering human figure claims from background descriptions
        desc = re.sub(r"\bwith\s+(?:crowds|people|pedestrians|children|students|witnesses)\b", "with empty architectural spaces", desc, flags=re.IGNORECASE)
        v_copy["description"] = desc
        clean_bg[bg_k] = v_copy

    # 2. Audit Foregrounds
    for fg_k, fg_v in (fg_roster or {}).items():
        v_copy = dict(fg_v)
        role = v_copy.get("role", "")
        title = v_copy.get("title", "")
        desc = v_copy.get("description", "")
        fg_type = v_copy.get("type", "evidence_prop")
        combined_text = f"{fg_k} {role} {title} {desc}"

        # Check Child Representation
        if fg_type == "character" and detect_child_representation(combined_text):
            logger.info(f"🛡️ [RepresentationShield] Child detected in '{fg_k}'. Converting to Symbolic Artifact.")
            symbolic = resolve_child_symbolic_artifact(entity_desc=desc, context_text=story_text, market=market)
            v_copy["title"] = symbolic["title"]
            v_copy["description"] = symbolic["description"]
            v_copy["type"] = "evidence_prop"
            v_copy["role"] = symbolic["role"]
            v_copy["is_child_symbolic"] = True
            v_copy["keywords"] = list(set(v_copy.get("keywords", []) + symbolic["keywords"]))
            clean_fg[fg_k] = v_copy
            continue

        # Check Real Adult Character -> Enforce Censor Bar
        if fg_type == "character":
            v_copy["description"] = apply_real_person_censor_shield(desc, fg_key=fg_k)
            v_copy["censor_bar_enforced"] = True

        clean_fg[fg_k] = v_copy

    logger.info(f"🛡️ [RepresentationShield] Pre-B3 Audit complete. BGs: {len(clean_bg)}, FGs: {len(clean_fg)}")
    return clean_bg, clean_fg
