#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/master_scene_sheet.py — Master Scene & Master Sheet Generator.

Implements Vox Style Master Sheet visual system for documentary-collage explainer series:
1. Master Sheet Chung (System Master Sheet):
   - Type Specimen: H1 Headline (bold condensed sans), Stat Hero (giant red bold condensed numeral),
     Annotation Label (typewriter serif with red underline).
   - Palette: Archival Tan (#C9BB9C), Ink Black (#1A1A1A), Halftone Gray (#8C8C8C),
     Hot Red (#B62E1F - reserved for strokes, underlines, arrows), Mustard (#D9A441 - secondary accent),
     Cream Paper (#F4F1EA - stage base).
   - Component Zoo: Halftone cutouts with rough deckle white keyline & offset red stroke,
     torn paper ledger strips, giant red stat cards, red map pins, underlined titles, archival photo mounts.
   - Mini-Scene Examples: Stat-driven narrative, map + annotation, archival photo + label.
   - Motion Thumbnails: 1 Cutout springs up with overshoot, 2 Counter ticks upward,
     3 Red underline swipes in, 4 Camera holds a slow 2% drift.
   - The Stage: Aged map texture on archival cream paper (#F4F1EA).
   - System Notes: Construction logic, accent rules, torn edges, print grain.
2. Master Sheet Từng Phân Cảnh (Per-Scene Storyboards / Contact Boards):
   - Ghép hình ảnh composite từng scene với câu thoại (narration), thời lượng,
     động thái motion thumbnail (overshoot, counter rollup, swipe, camera drift),
     các thành phần đạo cụ thống nhất, và Omni I2V prompt.
3. Chốt Chặn Phê Duyệt (Human Gate Review Dashboard):
   - Standalone interactive HTML + PIL high-res PNG contact boards.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("master_scene_sheet")

# ==============================================================================
# CANONICAL VOX PALETTE & TYPOGRAPHY SPECIFICATION (RULE 128 & 140)
# ==============================================================================
VOX_PALETTE = {
    "archival_tan": "#C9BB9C",
    "ink_black": "#1A1A1A",
    "halftone_gray": "#8C8C8C",
    "hot_red": "#B62E1F",
    "mustard": "#D9A441",
    "cream_paper": "#F4F1EA",
    "aged_border": "#3A352A",
    "paper_shadow": "rgba(26, 26, 26, 0.18)",
}

MOTION_THUMBNAIL_TYPES = [
    {
        "id": 1,
        "code": "top_down_tracking",
        "title": "1 POP-UP UNFOLD & 90° TRACKING STEPPED GLIDE",
        "directive": "Accordion paper unfold in 0.3s held steady, then 8f micro-whip to Mid (1.35x, 45°) locked 40f, then 7f whip to Macro (1.70x, 90°) locked 55f for vector graphics.",
        "h_family": "H7_DISPLACE / H6_MARK",
        "camera": "TOP_DOWN_TRACKING",
        "stepped_punches": [
            {"frame": 0, "scale": 1.0, "rotateZ": 0, "x": 0, "y": 0, "hold": 20},
            {"frame": 20, "scale": 1.35, "rotateZ": 45, "x": 15, "y": -15, "hold": 40, "whip_frames": 8, "curve": "whip"},
            {"frame": 68, "scale": 1.70, "rotateZ": 90, "x": 30, "y": -30, "hold": 55, "whip_frames": 7, "curve": "whip"},
        ],
        "dead_stop_ratio": "70-85%",
    },
    {
        "id": 2,
        "code": "rake_30_focus",
        "title": "2 SEAL STAMP IMPACT & 30° RAKE FOCUS CALLOUT",
        "directive": "Heavy seal stamp strikes with 6f whip impact and 3px shake, 35f dead-stop lock at Mid 15°, then 9f whip to Macro 30° locked 60f.",
        "h_family": "H1_IMPACT / H2_CONSTRAINT",
        "camera": "RAKE_30_RACK_FOCUS",
        "stepped_punches": [
            {"frame": 0, "scale": 1.0, "rotateZ": 0, "x": 0, "y": 0, "hold": 15},
            {"frame": 15, "scale": 1.30, "rotateZ": 15, "x": 0, "y": 10, "hold": 35, "whip_frames": 6, "impact_shake": 3, "curve": "whip"},
            {"frame": 56, "scale": 1.65, "rotateZ": 30, "x": 0, "y": 20, "hold": 60, "whip_frames": 9, "curve": "whip"},
        ],
        "dead_stop_ratio": "70-85%",
    },
    {
        "id": 3,
        "code": "macro_glide",
        "title": "3 CALIPER CLAMP & ANCHORED MACRO GLIDE ROLLUP",
        "directive": "Wide establish held 18f, 12f smooth glide to Mid (1.30x) locked 45f with odometer rollup, then 7f whip to Macro (1.75x) locked 70f.",
        "h_family": "H2_CONSTRAINT / H5_OPTICAL",
        "camera": "SURFACE_MACRO_GLIDE",
        "stepped_punches": [
            {"frame": 0, "scale": 1.0, "rotateZ": 0, "x": 0, "y": 0, "hold": 18},
            {"frame": 18, "scale": 1.30, "rotateZ": 0, "x": 10, "y": 0, "hold": 45, "whip_frames": 12, "curve": "glide"},
            {"frame": 75, "scale": 1.75, "rotateZ": 0, "x": 20, "y": 0, "hold": 70, "whip_frames": 7, "curve": "whip"},
        ],
        "dead_stop_ratio": "70-85%",
    },
    {
        "id": 4,
        "code": "whip_pan",
        "title": "4 RED YARN TENSION & MOTIVATED FOLLOW WHIP-PAN SNAP",
        "directive": "Taut crimson yarn staccato snap: Wide held 8f, 7f snap to Pin A (1.35x) locked 20f, then 8f snap to Pin B (1.68x) locked 25f.",
        "h_family": "H4_TETHER / H3_SEVER",
        "camera": "LATERAL_WHIP_PAN",
        "stepped_punches": [
            {"frame": 0, "scale": 1.0, "rotateZ": 0, "x": 0, "y": 0, "hold": 8},
            {"frame": 8, "scale": 1.35, "rotateZ": -2, "x": -120, "y": 40, "hold": 20, "whip_frames": 7, "curve": "staccato"},
            {"frame": 35, "scale": 1.68, "rotateZ": 1.5, "x": 90, "y": -60, "hold": 25, "whip_frames": 8, "curve": "staccato"},
        ],
        "dead_stop_ratio": "70-85%",
    },
    {
        "id": 5,
        "code": "orbit_arc",
        "title": "5 OPTICAL LOUPE & 8° PIVOT ORBIT ARC PUNCH",
        "directive": "Wide establish held 10f, 10f punch to Loupe Macro (1.90x) with +/-2px tactile micro-drift locked 24f, then 6f pull to Mid (1.40x) locked 25f.",
        "h_family": "H5_OPTICAL / H7_DISPLACE",
        "camera": "ORBIT_ARC_15",
        "stepped_punches": [
            {"frame": 0, "scale": 1.0, "rotateZ": 0, "x": 0, "y": 0, "hold": 10},
            {"frame": 10, "scale": 1.90, "rotateZ": 0, "x": 30, "y": -10, "hold": 24, "whip_frames": 10, "micro_drift": 2, "curve": "whip"},
            {"frame": 44, "scale": 1.40, "rotateZ": 0, "x": 0, "y": 0, "hold": 25, "whip_frames": 6, "curve": "whip"},
        ],
        "dead_stop_ratio": "70-85%",
    },
    {
        "id": 6,
        "code": "dutch_snap",
        "title": "6 PARADOX & FIXED DUTCH-ANGLE HIGHLIGHT PUSH",
        "directive": "Neutral held 6f, 12f push to Fixed Dutch -8° (1.50x) locked 30f, then 10f micro-push to Highlight (1.75x) locked 40f without frame roll.",
        "h_family": "H1_IMPACT / H6_MARK",
        "camera": "DUTCH_FORENSIC_SNAP",
        "stepped_punches": [
            {"frame": 0, "scale": 1.0, "rotateZ": 0, "x": 0, "y": 0, "hold": 6},
            {"frame": 6, "scale": 1.50, "rotateZ": -8, "x": 0, "y": 0, "hold": 30, "whip_frames": 12, "curve": "dutch"},
            {"frame": 48, "scale": 1.75, "rotateZ": -8, "x": 0, "y": 0, "hold": 40, "whip_frames": 10, "curve": "dutch"},
        ],
        "dead_stop_ratio": "70-85%",
    },
]


def resolve_scene_motion_thumbnail(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves which motion thumbnail archetype best matches the scene kinematics."""
    cam = str(scene.get("camera_directive") or "").upper()
    h_fam = str(scene.get("h_family") or "").upper()

    if "TOP_DOWN" in cam or "UNFOLD" in cam:
        return MOTION_THUMBNAIL_TYPES[0]
    elif "RAKE" in cam or "STAMP" in cam:
        return MOTION_THUMBNAIL_TYPES[1]
    elif "MACRO" in cam or "GLIDE" in cam or "CALIPER" in cam:
        return MOTION_THUMBNAIL_TYPES[2]
    elif "WHIP" in cam or "LATERAL" in cam or "YARN" in cam or "STACCATO" in cam:
        return MOTION_THUMBNAIL_TYPES[3]
    elif "ORBIT" in cam or "LOUPE" in cam:
        return MOTION_THUMBNAIL_TYPES[4]
    elif "DUTCH" in cam or "PARADOX" in cam:
        return MOTION_THUMBNAIL_TYPES[5]

    # Fallback to H-family mapping
    if "H7" in h_fam:
        return MOTION_THUMBNAIL_TYPES[0]
    elif "H1" in h_fam:
        return MOTION_THUMBNAIL_TYPES[1]
    elif "H2" in h_fam:
        return MOTION_THUMBNAIL_TYPES[2]
    elif "H4" in h_fam or "H3" in h_fam:
        return MOTION_THUMBNAIL_TYPES[3]
    elif "H5" in h_fam:
        return MOTION_THUMBNAIL_TYPES[4]
    elif "H6" in h_fam:
        return MOTION_THUMBNAIL_TYPES[5]

    return MOTION_THUMBNAIL_TYPES[0]


_WORD_NUM_MAP: Dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def _words_to_num(text: str) -> Optional[int]:
    """Converts simple English number phrases like 'six', 'forty-eight', 'six hundred twenty' to int."""
    tokens = text.lower().replace("-", " ").split()
    total = 0
    current = 0
    found_any = False
    for t in tokens:
        if t in _WORD_NUM_MAP:
            current += _WORD_NUM_MAP[t]
            found_any = True
        elif t == "hundred":
            if current == 0:
                current = 1
            current *= 100
            found_any = True
        elif t == "thousand":
            if current == 0:
                current = 1
            total += current * 1000
            current = 0
            found_any = True
        elif t == "and":
            continue
        else:
            return None
    if not found_any:
        return None
    return total + current


def _normalize_stat_scale(scale_raw: Optional[str]) -> str:
    """Normalizes currency/metric scale strings (e.g. 'billion', 'tỷ', 'm') to standard compact codes."""
    if not scale_raw:
        return ""
    s = scale_raw.lower().strip()
    if s in ("billion", "b", "tỷ", "ty"):
        return "B"
    if s in ("million", "m", "triệu", "trieu"):
        return "M"
    if s in ("trillion", "t", "nghìn tỷ", "nghin ty", "cho", "조"):
        return "T"
    if s in ("thousand", "k", "nghìn", "nghin"):
        return "K"
    return s[0].upper()


def extract_stat_hero_from_text(text: str) -> Optional[str]:
    """Extracts prominent quantitative metric for STAT HERO display.

    Supports:
    - Currencies: Won (KRW, ₩, won), USD ($), EUR (€), VND (đồng, đ), JPY (¥, yen)
    - Percentages: 85%, 12.5%, 85 percent, 85 phần trăm
    - Timeframe metrics: 48 hours, six weeks, 30 days, 10 years, 24 hrs
    - Milestone years: 2029, 2016, 2021, etc.
    """
    if not text or not isinstance(text, str):
        return None
    clean_text = text.strip()
    if not clean_text:
        return None

    # 1. USD:
    # 1a. Preserve legacy formats like "$123 tỷ"
    m_legacy = re.search(r"(\$\s*\d+(?:[,\.]\d+)?(?:\s*[BMKbmk]|(?:\s*(?:tỷ|triệu))))\b", clean_text, re.IGNORECASE)
    if m_legacy:
        return m_legacy.group(1).strip()

    # 1b. Symbol $ followed by digits and optional scale
    m_usd_sym = re.search(r"\$\s*(\d+(?:[,\.]\d+)?)\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?\b", clean_text, re.IGNORECASE)
    if m_usd_sym:
        val = m_usd_sym.group(1)
        scale = _normalize_stat_scale(m_usd_sym.group(2))
        return f"${val}{scale}"

    # 1c. Number followed by USD / dollars
    m_usd_suffix = re.search(r"\b(\d+(?:[,\.]\d+)?)\s*(?:-| )?\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?\s*(?:-| )?\s*(?:usd|dollars?)\b", clean_text, re.IGNORECASE)
    if m_usd_suffix:
        val = m_usd_suffix.group(1)
        scale = _normalize_stat_scale(m_usd_suffix.group(2))
        return f"${val}{scale}"

    # 2. Korean Won:
    # 2a. Symbol ₩ followed by digits and optional scale
    m_won_sym = re.search(r"₩\s*(\d+(?:[,\.]\d+)?)\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?(?:\s*(?:won|krw))?\b", clean_text, re.IGNORECASE)
    if m_won_sym:
        val = m_won_sym.group(1)
        scale = _normalize_stat_scale(m_won_sym.group(2))
        return f"₩{val}{scale}"

    # 2b. Won / KRW suffix with digits
    m_won = re.search(r"\b(\d+(?:[,\.]\d+)?)\s*(?:-| )?\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?\s*(?:-| )?\s*(?:won|krw)\b", clean_text, re.IGNORECASE)
    if m_won:
        val = m_won.group(1)
        scale = _normalize_stat_scale(m_won.group(2))
        return f"{val}{scale} WON" if scale else f"{val} WON"

    # 2c. Spoken English words for Won
    m_won_words = re.search(r"\b((?:six|seven|eight|nine|ten|one|two|three|four|five|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|[\s-])+)\s+(billion|million|trillion)?\s*(?:-| )?\s*won\b", clean_text, re.IGNORECASE)
    if m_won_words:
        num = _words_to_num(m_won_words.group(1))
        if num is not None:
            scale = _normalize_stat_scale(m_won_words.group(2))
            return f"{num}{scale} WON" if scale else f"{num} WON"

    # 2d. Korean native units: 조 (trillion), 억 (100 million)
    m_won_kr = re.search(r"\b(\d+(?:[,\.]\d+)?)\s*(조|억)?\s*원\b", clean_text)
    if m_won_kr:
        val = m_won_kr.group(1)
        unit = m_won_kr.group(2) or ""
        return f"{val}{unit} WON"

    # 3. Euro (€, EUR)
    m_eur_sym = re.search(r"€\s*(\d+(?:[,\.]\d+)?)\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?(?:\s*(?:euros?|eur))?\b", clean_text, re.IGNORECASE)
    if m_eur_sym:
        val = m_eur_sym.group(1)
        scale = _normalize_stat_scale(m_eur_sym.group(2))
        return f"€{val}{scale}"

    m_eur = re.search(r"\b(\d+(?:[,\.]\d+)?)\s*(?:-| )?\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?\s*(?:-| )?\s*(?:euros?|eur)\b", clean_text, re.IGNORECASE)
    if m_eur:
        val = m_eur.group(1)
        scale = _normalize_stat_scale(m_eur.group(2))
        return f"€{val}{scale}"

    # 4. Japanese Yen (¥, JPY, yen)
    m_yen_sym = re.search(r"¥\s*(\d+(?:[,\.]\d+)?)\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?(?:\s*(?:yen|jpy))?\b", clean_text, re.IGNORECASE)
    if m_yen_sym:
        val = m_yen_sym.group(1)
        scale = _normalize_stat_scale(m_yen_sym.group(2))
        return f"¥{val}{scale}"

    m_yen = re.search(r"\b(\d+(?:[,\.]\d+)?)\s*(?:-| )?\s*(billion|million|trillion|thousand|tỷ|triệu|b|m|k|t)?\s*(?:-| )?\s*(?:yen|jpy)\b", clean_text, re.IGNORECASE)
    if m_yen:
        val = m_yen.group(1)
        scale = _normalize_stat_scale(m_yen.group(2))
        return f"¥{val}{scale}"

    # 5. Vietnamese Dong (đồng, đ, VND, VNĐ)
    m_vnd = re.search(r"\b(\d+(?:[,\.]\d+)?)\s*(tỷ|triệu|nghìn|ty|trieu|nghin|billion|million|b|m|k)?\s*(?:đồng|đ|vnd|vnđ)\b", clean_text, re.IGNORECASE)
    if m_vnd:
        val = m_vnd.group(1)
        scale = _normalize_stat_scale(m_vnd.group(2))
        return f"{val}{scale} VND" if scale else f"{val} VND"

    # 6. Percentages
    m_pct = re.search(r"([+-]?\d+(?:[,\.]\d+)?\s*%)", clean_text)
    if m_pct:
        return m_pct.group(1).replace(" ", "")

    m_pct_word = re.search(r"\b([+-]?\d+(?:[,\.]\d+)?)\s*(?:percent|phần trăm|phan tram)\b", clean_text, re.IGNORECASE)
    if m_pct_word:
        return f"{m_pct_word.group(1)}%"

    # 7. Durations / Timeframe metrics
    m_dur = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|sixteen|twenty|twenty-four|twenty four|thirty|forty-eight|forty eight|seventy-two|seventy two)\s+(hours?|hrs?|weeks?|wks?|days?|months?|mos?|years?|yrs?)\b", clean_text, re.IGNORECASE)
    if m_dur:
        raw_num = m_dur.group(1)
        raw_unit = m_dur.group(2).lower()
        if raw_num.isdigit():
            num_val = raw_num
        else:
            parsed = _words_to_num(raw_num)
            num_val = str(parsed) if parsed is not None else raw_num.upper()

        if "hour" in raw_unit or "hr" in raw_unit:
            unit_str = "HOURS"
        elif "week" in raw_unit or "wk" in raw_unit:
            unit_str = "WEEKS"
        elif "day" in raw_unit:
            unit_str = "DAYS"
        elif "month" in raw_unit or "mo" in raw_unit:
            unit_str = "MONTHS"
        elif "year" in raw_unit or "yr" in raw_unit:
            unit_str = "YEARS"
        else:
            unit_str = raw_unit.upper()
        return f"{num_val} {unit_str}"

    # 8. Milestone Years (4 digits 19xx or 20xx)
    m_year = re.search(r"\b(19\d{2}|20\d{2})\b", clean_text)
    if m_year:
        return m_year.group(1)

    return None


# ==============================================================================
# PIL GRAPHIC GENERATOR (IMAGE-BASED MASTER SHEETS)
# ==============================================================================
def _get_pil_fonts() -> Dict[str, Any]:
    """Loads robust PIL TrueType fonts with graceful default fallbacks."""
    from PIL import ImageFont
    fonts: Dict[str, Any] = {}
    candidates = [
        # Windows standard font paths
        ("impact", ["C:/Windows/Fonts/impact.ttf", "impact.ttf", "arialbd.ttf"]),
        ("sans_bold", ["C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]),
        ("sans_reg", ["C:/Windows/Fonts/arial.ttf", "arial.ttf", "DejaVuSans.ttf"]),
        ("typewriter", ["C:/Windows/Fonts/courbd.ttf", "courbd.ttf", "Courier_New_Bold.ttf", "cour.ttf"]),
        ("serif_bold", ["C:/Windows/Fonts/georgiab.ttf", "georgiab.ttf", "timesbd.ttf"]),
    ]

    for key, path_list in candidates:
        loaded = None
        for p in path_list:
            try:
                loaded = ImageFont.truetype(p, size=24)
                break
            except Exception:
                continue
        fonts[key] = loaded or ImageFont.load_default()

    def make_sized_font(font_key: str, size: int):
        f = fonts.get(font_key)
        if hasattr(f, "path") and f.path:
            try:
                return ImageFont.truetype(f.path, size=size)
            except Exception as _f_err:
                logger.debug(f"Font size loading notice for {font_key}: {_f_err}")
        return ImageFont.load_default()

    return {
        "title": make_sized_font("impact", 38),
        "h1": make_sized_font("impact", 54),
        "stat_hero": make_sized_font("impact", 76),
        "stat_medium": make_sized_font("impact", 42),
        "typewriter": make_sized_font("typewriter", 20),
        "typewriter_small": make_sized_font("typewriter", 15),
        "body_bold": make_sized_font("sans_bold", 18),
        "body_reg": make_sized_font("sans_reg", 16),
        "label": make_sized_font("sans_bold", 14),
        "caption": make_sized_font("sans_reg", 13),
    }


def render_master_system_sheet_png(
    episode_title: str,
    output_path: Path,
    market: str = "EN",
    runtime_s: float = 180.0,
    total_scenes: int = 15,
) -> Path:
    """Renders high-fidelity Master Visual System Sheet matching user reference image."""
    from PIL import Image, ImageDraw

    w, h = 1920, 1080
    bg_color = VOX_PALETTE["cream_paper"]
    card_bg = "#FFFFFF"
    ink = VOX_PALETTE["ink_black"]
    hot_red = VOX_PALETTE["hot_red"]
    tan = VOX_PALETTE["archival_tan"]
    gray = VOX_PALETTE["halftone_gray"]
    mustard = VOX_PALETTE["mustard"]
    border_col = VOX_PALETTE["aged_border"]

    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)
    fonts = _get_pil_fonts()

    # Outer aged frame border
    draw.rectangle([16, 16, w - 16, h - 16], outline=border_col, width=3)

    # 1. TOP HEADER BAR
    draw.rectangle([20, 20, w - 20, 75], fill=ink)
    draw.text((36, 28), "VOX STYLE MASTER SHEET", fill="#FFFFFF", font=fonts["title"])
    sub_title = f"VISUAL SYSTEM FOR A DOCUMENTARY-COLLAGE EXPLAINER SERIES // EPISODE: {episode_title.upper()[:45]} ({market}) // {total_scenes} SCENES (~{int(runtime_s)}S)"
    draw.text((w - 28, 38), sub_title, fill="#E2E8F0", font=fonts["body_bold"], anchor="ra")

    # Helper function for boxed cards
    def draw_box(x1, y1, x2, y2, title=""):
        draw.rectangle([x1, y1, x2, y2], fill=bg_color, outline=border_col, width=2)
        if title:
            draw.text((x1 + 12, y1 + 8), title.upper(), fill=ink, font=fonts["label"])
            draw.line([x1 + 10, y1 + 30, x2 - 10, y1 + 30], fill=border_col, width=1)

    # -------------------------------------------------------------------------
    # 2. TOP ROW (y: 85 -> 380)
    # Box A: TYPE SPECIMEN (x: 25 -> 580)
    draw_box(25, 85, 580, 380, "TYPE SPECIMEN")
    draw.text((45, 125), "H1 HEADLINE", fill=gray, font=fonts["label"])
    draw.text((45, 145), "THE DEAL", fill=ink, font=fonts["h1"])

    draw.text((45, 230), "STAT HERO", fill=gray, font=fonts["label"])
    draw.text((45, 250), "$123", fill=hot_red, font=fonts["stat_hero"])

    draw.text((310, 230), "ANNOTATION LABEL", fill=gray, font=fonts["label"])
    draw.text((310, 260), "Fig. 3 - Trade Route", fill=ink, font=fonts["typewriter"])
    draw.line([310, 290, 520, 290], fill=hot_red, width=3)

    # Box B: PALETTE (x: 595 -> 1160)
    draw_box(595, 85, 1160, 380, "PALETTE")
    swatches = [
        ("ARCHIVAL TAN", tan, "#C9BB9C"),
        ("INK BLACK", ink, "#1A1A1A"),
        ("HALFTONE GRAY", gray, "#8C8C8C"),
        ("HOT RED", hot_red, "#B62E1F"),
        ("MUSTARD", mustard, "#D9A441"),
    ]
    sw_w, sw_h = 95, 130
    start_sx = 615
    for idx, (s_name, s_hex, s_code) in enumerate(swatches):
        sx = start_sx + idx * (sw_w + 14)
        draw.rectangle([sx, 125, sx + sw_w, 125 + sw_h], fill=s_hex, outline=border_col, width=1)
        draw.text((sx + sw_w // 2, 265), s_name, fill=ink, font=fonts["caption"], anchor="ma")
        draw.text((sx + sw_w // 2, 282), s_code, fill=gray, font=fonts["caption"], anchor="ma")

    draw.text((615, 318), "HOT RED IS RESERVED FOR STROKES, UNDERLINES, AND ARROWS.", fill=hot_red, font=fonts["caption"])
    draw.text((615, 338), "MUSTARD IS SECONDARY ACCENT ONLY.", fill=mustard, font=fonts["caption"])

    # Box C: COMPONENT ZOO (x: 1175 -> 1895)
    draw_box(1175, 85, 1895, 380, "COMPONENT ZOO")
    # Cutout figure mockup
    draw.rectangle([1195, 125, 1315, 355], fill="#E2D9C8", outline=hot_red, width=2)
    draw.rectangle([1200, 130, 1310, 350], fill="#D5CAB4", outline="#FFFFFF", width=3)
    draw.text((1255, 230), "[HALFTONE\nCUTOUT\nFIGURE]", fill=ink, font=fonts["caption"], anchor="mm")

    # Torn paper strip
    draw.rectangle([1345, 135, 1605, 195], fill="#FFFFFF", outline=border_col, width=1)
    draw.text((1475, 165), "=== TORN LEDGER STRIP ===", fill=gray, font=fonts["typewriter_small"], anchor="mm")

    # Giant stat card
    draw.rectangle([1635, 135, 1865, 220], fill=hot_red, outline=border_col, width=2)
    draw.text((1750, 178), "$123", fill="#FFFFFF", font=fonts["stat_medium"], anchor="mm")

    # Red Map pin
    draw.ellipse([1355, 225, 1405, 275], fill=hot_red, outline="#FFFFFF", width=2)
    draw.ellipse([1373, 243, 1387, 257], fill="#FFFFFF")
    draw.polygon([(1365, 265), (1395, 265), (1380, 295)], fill=hot_red)

    # Underlined title
    draw.text((1445, 240), "THE DEAL", fill=ink, font=fonts["title"])
    draw.line([1440, 285, 1600, 285], fill=hot_red, width=5)

    # Archival photo card
    draw.rectangle([1635, 240, 1865, 355], fill="#EAE5D9", outline=border_col, width=1)
    draw.rectangle([1645, 250, 1855, 330], fill="#BFB8A5")
    draw.text((1750, 290), "[ARCHIVAL PHOTO]", fill=ink, font=fonts["caption"], anchor="mm")

    # -------------------------------------------------------------------------
    # 3. MIDDLE ROW (y: 395 -> 730)
    # Box D: MINI-SCENE EXAMPLES (x: 25 -> 1160)
    draw_box(25, 395, 1160, 730, "MINI-SCENE EXAMPLES")

    # Mini-Scene A: Stat Driven Narrative
    draw.rectangle([45, 435, 390, 705], fill=card_bg, outline=border_col, width=1)
    draw.text((55, 445), "A  STAT DRIVEN NARRATIVE", fill="#FFFFFF", font=fonts["caption"])
    draw.rectangle([50, 440, 240, 465], fill=ink)
    draw.text((145, 452), "A  STAT DRIVEN NARRATIVE", fill="#FFFFFF", font=fonts["caption"], anchor="mm")
    # Mockup graphic
    draw.rectangle([65, 485, 155, 685], fill="#E2D9C8", outline=hot_red, width=2)
    draw.text((110, 580), "[CUTOUT]", fill=ink, font=fonts["caption"], anchor="mm")
    draw.line([165, 585, 225, 585], fill=hot_red, width=3)
    draw.polygon([(225, 578), (240, 585), (225, 592)], fill=hot_red)
    draw.rectangle([250, 535, 375, 635], fill=hot_red)
    draw.text((312, 585), "$123", fill="#FFFFFF", font=fonts["stat_medium"], anchor="mm")

    # Mini-Scene B: Map + Annotation
    draw.rectangle([410, 435, 775, 705], fill="#EFE8D8", outline=border_col, width=1)
    draw.rectangle([415, 440, 585, 465], fill=ink)
    draw.text((500, 452), "B  MAP + ANNOTATION", fill="#FFFFFF", font=fonts["caption"], anchor="mm")
    # Map graphic sketch
    for gy in range(485, 695, 35):
        draw.line([425, gy, 760, gy], fill="#D8CFBD", width=1)
    draw.ellipse([645, 495, 675, 525], fill=hot_red)
    draw.line([455, 610, 655, 520], fill=hot_red, width=2)
    draw.rectangle([445, 630, 680, 680], fill="#FFFFFF", outline=border_col, width=1)
    draw.text((562, 655), "Fig. 3 - Trade Route", fill=ink, font=fonts["typewriter_small"], anchor="mm")
    draw.line([460, 670, 665, 670], fill=hot_red, width=2)

    # Mini-Scene C: Archival Photo + Label
    draw.rectangle([795, 435, 1140, 705], fill=card_bg, outline=border_col, width=1)
    draw.rectangle([800, 440, 990, 465], fill=ink)
    draw.text((895, 452), "C  ARCHIVAL PHOTO + LABEL", fill="#FFFFFF", font=fonts["caption"], anchor="mm")
    draw.rectangle([815, 480, 1075, 675], fill="#D1C7B2", outline=border_col, width=2)
    draw.text((945, 560), "[TORN ARCHIVAL PHOTO]", fill=ink, font=fonts["body_bold"], anchor="mm")
    draw.rectangle([1015, 605, 1130, 675], fill=mustard, outline=border_col, width=1)
    draw.text((1072, 640), "Fig. 3 -\nTrade Route", fill=ink, font=fonts["caption"], anchor="mm")

    # Box E: MOTION THUMBNAILS (x: 1175 -> 1895)
    draw_box(1175, 395, 1895, 730, "MOTION THUMBNAILS")
    m_w, _m_h = 160, 245
    m_start_x = 1195
    for idx, mt in enumerate(MOTION_THUMBNAIL_TYPES):
        mx = m_start_x + idx * (m_w + 20)
        # Header banner
        draw.rectangle([mx, 435, mx + m_w, 485], fill="#FFFFFF", outline=border_col, width=1)
        draw.rectangle([mx + 4, 440, mx + 26, 462], fill=ink)
        draw.text((mx + 15, 451), str(mt["id"]), fill="#FFFFFF", font=fonts["caption"], anchor="mm")
        t_words = mt["title"].replace(f"{mt['id']} ", "").split()
        l1 = " ".join(t_words[:2])
        l2 = " ".join(t_words[2:])
        draw.text((mx + 32, 443), l1, fill=ink, font=fonts["caption"])
        if l2:
            draw.text((mx + 32, 459), l2, fill=ink, font=fonts["caption"])

        # Content box
        draw.rectangle([mx, 495, mx + m_w, 495 + 200], fill=card_bg, outline=border_col, width=1)
        if mt["id"] == 1:
            draw.rectangle([mx + 45, 545, mx + 115, 675], fill="#D8CFBD", outline=hot_red, width=2)
            draw.text((mx + 80, 610), "[CUTOUT]", fill=ink, font=fonts["caption"], anchor="mm")
            # Spring lines / upward curved arrow
            draw.line([mx + 125, 660, mx + 140, 580], fill=hot_red, width=3)
            draw.polygon([(mx + 133, 580), (mx + 140, 570), (mx + 147, 582)], fill=hot_red)
        elif mt["id"] == 2:
            draw.rectangle([mx + 15, 570, mx + 145, 650], fill=hot_red)
            draw.text((mx + 80, 610), "$123", fill="#FFFFFF", font=fonts["stat_medium"], anchor="mm")
            draw.line([mx + 130, 660, mx + 130, 540], fill=hot_red, width=2)
            draw.polygon([(mx + 125, 540), (mx + 130, 530), (mx + 135, 540)], fill=hot_red)
        elif mt["id"] == 3:
            draw.text((mx + 80, 580), "THE DEAL", fill=ink, font=fonts["title"], anchor="mm")
            draw.line([mx + 20, 630, mx + 140, 630], fill=hot_red, width=4)
            draw.polygon([(mx + 135, 624), (mx + 148, 630), (mx + 135, 636)], fill=hot_red)
        elif mt["id"] == 4:
            draw.rectangle([mx + 25, 530, mx + 135, 660], fill="#EFE8D8", outline=hot_red, width=1)
            # Corner drift arrows
            for cx, cy, dx, dy in [(mx + 25, 530, -1, -1), (mx + 135, 530, 1, -1), (mx + 25, 660, -1, 1), (mx + 135, 660, 1, 1)]:
                draw.line([cx, cy, cx + dx * 12, cy + dy * 12], fill=hot_red, width=2)

    # -------------------------------------------------------------------------
    # 4. BOTTOM ROW (y: 745 -> 1060)
    # Box F: THE STAGE (x: 25 -> 1360)
    draw_box(25, 745, 1360, 1060, "THE STAGE (ARCHIVAL CREAM PAPER #F4F1EA & VINTAGE DESK)")
    draw.rectangle([45, 785, 1340, 1040], fill="#EFE9DA", outline=border_col, width=1)
    # Draw faint grid / antique compass rose decoration
    for gy in range(805, 1030, 45):
        draw.line([55, gy, 1330, gy], fill="#E4DBC8", width=1)
    for gx in range(65, 1320, 90):
        draw.line([gx, 795, gx, 1030], fill="#E4DBC8", width=1)
    draw.ellipse([640, 860, 740, 960], outline="#D5CAB4", width=2)
    draw.line([690, 850, 690, 970], fill="#D5CAB4", width=2)
    draw.line([630, 910, 750, 910], fill="#D5CAB4", width=2)
    draw.text((690, 910), "NORTH", fill=gray, font=fonts["caption"], anchor="mm")
    draw.text((95, 815), "ARCHIVAL AGED MAP TEXTURE - 100% DIORAMA BACKDROP STAGE", fill=ink, font=fonts["body_bold"])
    draw.text((95, 845), "All exhibits, cards, cutouts and forensic documents exist physically on this tabletop diorama surface.", fill=gray, font=fonts["caption"])

    # Box G: SYSTEM NOTES (x: 1375 -> 1895)
    draw_box(1375, 745, 1895, 1060, "SYSTEM NOTES")
    bullet_points = [
        "• ALL ELEMENTS SHARE A SINGLE CONSTRUCTION LOGIC:\n  HALFTONE TEXTURE, ROUGH KEYLINE, AND OFFSET RED STROKE.",
        "• RED IS FOR EMPHASIS ONLY: STROKES, UNDERLINES, ARROWS.",
        "• MUSTARD IS SECONDARY ACCENT, USE SPARINGLY.",
        "• TORN EDGES, PRINT GRAIN, HALFTONE, AND MATTE FINISH\n  CREATE A UNIFIED, ARCHIVAL, NEWSROOM FEEL.",
        f"• EPISODE SCOPE: {total_scenes} SCENES, 0% CGI, 100% TACTILE DIORAMA.",
    ]
    cur_y = 790
    for bp in bullet_points:
        draw.text((1395, cur_y), bp, fill=ink, font=fonts["caption"])
        cur_y += 48

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG", quality=95)
    logger.info(f"Master Visual System Sheet rendered to: {output_path}")
    return output_path


def resolve_scene_image_path(
    scene_id: str,
    image_dir: Optional[Path] = None,
    fallback_dirs: Optional[List[Path]] = None,
    explicit_path: Optional[str | Path] = None,
) -> Optional[Path]:
    """Dynamically and robustly resolves the authentic seed image for a given scene.

    Supports:
    - Explicit image paths if valid and existing.
    - Multiple candidate search directories (composite_seeds, images, assets, browser_assets).
    - Case-insensitive matching across both Windows and Linux filesystems (ext4 parity).
    - Variations: composite_{sc_id}.png/jpg, {sc_id}.png/jpg, zero-padded (SCENE_01 vs SCENE_1).
    """
    if explicit_path:
        try:
            ep = Path(explicit_path)
            if ep.exists() and ep.is_file() and ep.stat().st_size > 1000:
                return ep
        except (OSError, ValueError) as _path_err:
            logger.debug(f"Explicit path invalid or inaccessible '{explicit_path}': {_path_err}")

    clean_id = str(scene_id).strip()
    if not clean_id:
        return None

    # Build unique token variants
    tokens = [clean_id]
    m = re.search(r"(\d+)", clean_id)
    if m:
        num = int(m.group(1))
        tokens.extend([f"SCENE_{num:02d}", f"SCENE_{num}", f"scene_{num:02d}", f"scene_{num}"])

    cand_filenames: List[str] = []
    seen = set()
    for tok in tokens:
        for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG"):
            for prefix in ("composite_", "COMPOSITE_", ""):
                fn = f"{prefix}{tok}{ext}"
                if fn not in seen:
                    seen.add(fn)
                    cand_filenames.append(fn)
                fn_lower = f"{prefix}{tok.lower()}{ext}"
                if fn_lower not in seen:
                    seen.add(fn_lower)
                    cand_filenames.append(fn_lower)
                fn_upper = f"{prefix}{tok.upper()}{ext}"
                if fn_upper not in seen:
                    seen.add(fn_upper)
                    cand_filenames.append(fn_upper)

    # Gather search directories
    search_dirs: List[Path] = []
    if image_dir and Path(image_dir).exists():
        search_dirs.append(Path(image_dir))
    if fallback_dirs:
        for fb in fallback_dirs:
            if fb and Path(fb).exists() and Path(fb) not in search_dirs:
                search_dirs.append(Path(fb))

    # Fast direct lookup
    for d in search_dirs:
        for fn in cand_filenames:
            cand_p = d / fn
            if cand_p.exists() and cand_p.is_file() and cand_p.stat().st_size > 1000:
                return cand_p.resolve()

    # Case-insensitive filesystem scan for Linux ext4 parity
    cand_lower_set = {fn.lower() for fn in cand_filenames}
    for d in search_dirs:
        try:
            for entry in d.iterdir():
                if entry.is_file() and entry.name.lower() in cand_lower_set and entry.stat().st_size > 1000:
                    return entry.resolve()
        except OSError:
            continue

    return None


def render_scene_contact_sheet_png(
    scenes: List[Dict[str, Any]],
    output_path: Path,
    image_dir: Optional[Path] = None,
    cols: int = 3,
    rows: Optional[int] = None,
    page_index: int = 0,
) -> Path:
    """Renders a visual Contact Sheet / Storyboard page of scenes with images and narration."""
    from PIL import Image, ImageDraw

    w = 1920
    bg_color = VOX_PALETTE["cream_paper"]
    card_bg = "#FFFFFF"
    ink = VOX_PALETTE["ink_black"]
    hot_red = VOX_PALETTE["hot_red"]
    border_col = VOX_PALETTE["aged_border"]
    gray = VOX_PALETTE["halftone_gray"]

    if rows is None:
        effective_rows = max(1, math.ceil(len(scenes) / cols))
        card_w = (w - 60 - (cols - 1) * 20) // cols
        card_h = 480
        h = max(1080, 100 + effective_rows * (card_h + 20) + 20)
        page_scenes = scenes
        start_i = 0
        header_sub = f"ALL {len(scenes)} SCENES // COMPOSITE FRAMES, NARRATION & KINEMATICS"
    else:
        effective_rows = rows
        per_page = cols * effective_rows
        start_i = page_index * per_page
        page_scenes = scenes[start_i:start_i + per_page]
        h = 1080
        card_w = (w - 60 - (cols - 1) * 20) // cols
        card_h = (h - 110 - (effective_rows - 1) * 20) // effective_rows
        header_sub = f"PAGE {page_index + 1} // COMPOSITE FRAMES, NARRATION & KINEMATICS"

    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)
    fonts = _get_pil_fonts()

    # Outer aged frame border
    draw.rectangle([16, 16, w - 16, h - 16], outline=border_col, width=3)

    # Top Header
    draw.rectangle([20, 20, w - 20, 75], fill=ink)
    draw.text((36, 28), "VOX SCENE MASTER STORYBOARD CONTACT SHEET", fill="#FFFFFF", font=fonts["title"])
    draw.text((w - 28, 38), header_sub, fill="#E2E8F0", font=fonts["body_bold"], anchor="ra")

    for idx, sc in enumerate(page_scenes):
        c = idx % cols
        r = idx // cols
        x1 = 30 + c * (card_w + 20)
        y1 = 90 + r * (card_h + 20)
        x2 = x1 + card_w
        y2 = y1 + card_h

        # Card container
        draw.rectangle([x1, y1, x2, y2], fill=card_bg, outline=border_col, width=2)

        # Scene Header
        sc_id = sc.get("scene_id", f"SCENE_{start_i + idx + 1:02d}")
        headline = (sc.get("headline") or "TACTILE EVIDENCE").upper()
        dur = float(sc.get("duration_est_sec") or 5.5)

        draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y1 + 36], fill=ink)
        draw.text((x1 + 10, y1 + 8), f"{sc_id} // {headline[:32]}", fill="#FFFFFF", font=fonts["body_bold"])
        draw.text((x2 - 10, y1 + 8), f"{dur:.1f}s", fill=hot_red, font=fonts["body_bold"], anchor="ra")

        # Composite Image Box (16:9 ratio inside top portion of card)
        img_w = card_w - 20
        img_h = int(img_w * 9 / 16)
        img_x = x1 + 10
        img_y = y1 + 44

        img_drawn = False
        fallback_dirs = []
        if image_dir:
            fallback_dirs.extend([image_dir.parent / "images", image_dir.parent / "assets"])
        first_shot = sc.get("shots", [{}])[0] if isinstance(sc.get("shots"), list) and len(sc.get("shots")) > 0 else {}
        explicit_target = (
            sc.get("image_path")
            or sc.get("seed_image")
            or sc.get("file_path")
            or first_shot.get("seed_image")
            or first_shot.get("image_path")
        )
        target_img_path = resolve_scene_image_path(
            scene_id=sc_id,
            image_dir=image_dir,
            fallback_dirs=fallback_dirs,
            explicit_path=explicit_target,
        )

        if target_img_path:
            try:
                with Image.open(str(target_img_path)) as c_img:
                    thumb = c_img.convert("RGB").resize((img_w, img_h))
                    img.paste(thumb, (img_x, img_y))
                    draw.rectangle([img_x, img_y, img_x + img_w, img_y + img_h], outline=border_col, width=1)
                    img_drawn = True
            except Exception as _load_err:
                logger.debug(f"Could not load image {target_img_path}: {_load_err}")

        stat_hero = extract_stat_hero_from_text(sc.get("narration") or "")

        if not img_drawn:
            # Fallback stylized diorama frame
            draw.rectangle([img_x, img_y, img_x + img_w, img_y + img_h], fill="#F4F1EA", outline=border_col, width=1)
            hero = sc.get("hero_cutout_object") or "Archival Subject"
            draw.text((img_x + img_w // 2, img_y + img_h // 2), f"[{hero.upper()[:24]}]", fill=ink, font=fonts["body_bold"], anchor="mm")
            draw.text((img_x + img_w // 2, img_y + img_h - 18), "AUTHENTIC SEED COMPOSITE PREVIEW", fill=gray, font=fonts["caption"], anchor="mm")

        # Stat Hero Badge: prominent red badge rendered over top-left of preview image/diorama
        if stat_hero:
            font_stat = fonts.get("stat_medium") or fonts.get("body_bold")
            try:
                bbox = draw.textbbox((0, 0), stat_hero, font=font_stat)
                bw = (bbox[2] - bbox[0]) + 24
                bh = (bbox[3] - bbox[1]) + 16
            except Exception:
                bw = max(120, len(stat_hero) * 12 + 24)
                bh = 40
            bx1 = img_x + 12
            by1 = img_y + 12
            bx2 = bx1 + bw
            by2 = by1 + bh
            draw.rectangle([bx1, by1, bx2, by2], fill=hot_red)
            draw.text(((bx1 + bx2) // 2, (by1 + by2) // 2), stat_hero, fill="#FFFFFF", font=font_stat, anchor="mm")

        # Narration Box
        narr_y = img_y + img_h + 10
        narr = sc.get("narration") or "Tactile documentary investigation."
        # Wrap narration into 2-3 lines
        words = narr.split()
        lines = []
        cur_l = ""
        for w_item in words:
            if len(cur_l) + len(w_item) + 1 <= 54:
                cur_l += (" " if cur_l else "") + w_item
            else:
                lines.append(cur_l)
                cur_l = w_item
            if len(lines) >= 3:
                break
        if cur_l and len(lines) < 3:
            lines.append(cur_l)

        draw.text((x1 + 10, narr_y), "VOICEOVER NARRATION:", fill=gray, font=fonts["caption"])
        for l_idx, l_str in enumerate(lines[:3]):
            draw.text((x1 + 10, narr_y + 16 + l_idx * 18), l_str, fill=ink, font=fonts["typewriter_small"])

        # Bottom Bar: Motion Thumbnail Badge & H-Family
        mt = resolve_scene_motion_thumbnail(sc)
        h_family = sc.get("h_family") or mt.get("h_family") or "H1_IMPACT"
        bar_y = y2 - 32
        draw.line([x1 + 6, bar_y - 4, x2 - 6, bar_y - 4], fill="#CBD5E1", width=1)
        draw.rectangle([x1 + 8, bar_y, x1 + 210, bar_y + 24], fill=hot_red)
        draw.text((x1 + 12, bar_y + 5), f"MOTION: {mt['title'][:22]}", fill="#FFFFFF", font=fonts["caption"])
        draw.text((x2 - 10, bar_y + 5), f"{h_family}", fill=ink, font=fonts["caption"], anchor="ra")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG", quality=95)
    logger.info(f"Scene Contact Sheet rendered to: {output_path}")
    return output_path


# ==============================================================================
# INTERACTIVE STANDALONE HTML GENERATOR (EXECUTIVE DASHBOARD)
# ==============================================================================
def generate_master_scene_dashboard_html(
    episode_id: str,
    episode_title: str,
    scenes: List[Dict[str, Any]],
    output_path: Path,
    market: str = "EN",
    runtime_s: float = 180.0,
    seeds_dir_rel: str = "../composite_seeds",
    image_paths_map: Optional[Dict[str, str]] = None,
) -> Path:
    """Generates an executive standalone interactive HTML dashboard containing:
    1. The Master Visual System (Type Specimen, Palette, Zoo, Motion Thumbnails, System Notes)
    2. Per-Scene Master Storyboards (Images, Dialogue/Narration, Durations, Motion Thumbnail, Omni Prompts)
    3. Human Gate Review & Approval Controls for Omni 2-Scene Pilot and Full Video.
    """
    image_paths_map = image_paths_map or {}
    total_scenes = len(scenes)

    # Build scene cards HTML
    scene_cards_html = []
    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", f"SCENE_{idx+1:02d}")
        headline = sc.get("headline") or "FORENSIC FOCUS"
        dur = float(sc.get("duration_est_sec") or 5.5)
        narration = sc.get("narration") or ""
        mt = resolve_scene_motion_thumbnail(sc)
        h_family = sc.get("h_family") or mt.get("h_family") or "H1_IMPACT"
        hero = sc.get("hero_cutout_object") or "Archival Character Cutout"
        props = sc.get("interacting_objects") or ["Torn paper ledger", "Red evidence marker"]
        props_str = ", ".join(props) if isinstance(props, list) else str(props)
        first_shot = sc.get("shots", [{}])[0] if isinstance(sc.get("shots"), list) and len(sc.get("shots")) > 0 else {}
        omni_prompt = (
            sc.get("i2v_prompt_omni")
            or sc.get("i2v_prompt_google_flow")
            or sc.get("image_prompt")
            or first_shot.get("visual_prompt")
            or first_shot.get("prompt")
            or ""
        )
        stat_hero = extract_stat_hero_from_text(narration)

        # Image source logic: check image_paths_map or relative path
        img_src = image_paths_map.get(sc_id) or f"{seeds_dir_rel}/composite_{sc_id.lower()}.png"

        stat_badge_html = f'<div class="stat-hero-badge">{stat_hero}</div>' if stat_hero else ""

        cam_dir = sc.get("camera_directive") or mt.get("camera") or "TOP_DOWN_TRACKING"

        card_html = f"""
        <div class="scene-card" id="card_{sc_id.lower()}">
            <div class="scene-card-header">
                <span class="scene-tag">{sc_id} // {idx+1:02d}</span>
                <span class="scene-headline">{headline}</span>
                <span class="scene-dur">{dur:.1f}s</span>
            </div>
            <div class="scene-visual-wrapper">
                {stat_badge_html}
                <img src="{img_src}" alt="{sc_id} Composite" onerror="this.onerror=null; this.parentElement.classList.add('fallback-visual'); this.style.display='none';" />
                <div class="visual-fallback-diorama">
                    <div class="diorama-hero-label">[{hero.upper()}]</div>
                    <div class="diorama-subtext">Composite Seed Pending Render</div>
                </div>
            </div>
            <div class="scene-body">
                <div class="body-row narration-row">
                    <span class="field-label">NARRATION:</span>
                    <p class="narration-text">"{narration}"</p>
                </div>
                <div class="body-row meta-grid">
                    <div><span class="field-label">MOTION:</span> <span class="badge badge-motion">{mt['title']}</span></div>
                    <div><span class="field-label">CAMERA:</span> <span class="badge badge-cam">{cam_dir}</span></div>
                    <div><span class="field-label">H-FAMILY:</span> <span class="badge badge-h">{h_family}</span></div>
                    <div><span class="field-label">HERO CUTOUT:</span> <span class="meta-val">{hero}</span></div>
                    <div><span class="field-label">PROPS:</span> <span class="meta-val">{props_str}</span></div>
                </div>
                <div class="body-row prompt-accordion">
                    <details>
                        <summary>Omni 1.1 Flash / Google Flow I2V Prompt</summary>
                        <pre class="prompt-code">{omni_prompt}</pre>
                    </details>
                </div>
            </div>
        </div>
        """
        scene_cards_html.append(card_html)

    all_scenes_joined = "\n".join(scene_cards_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOX MASTER SCENE DASHBOARD — {episode_id}</title>
    <style>
        :root {{
            --bg-cream: #F4F1EA;
            --archival-tan: #C9BB9C;
            --ink-black: #1A1A1A;
            --halftone-gray: #8C8C8C;
            --hot-red: #B62E1F;
            --mustard: #D9A441;
            --border-aged: #3A352A;
            --card-shadow: 0 4px 14px rgba(26, 26, 26, 0.08);
            --font-headline: Impact, "Arial Narrow", "League Gothic", sans-serif;
            --font-typewriter: "Courier New", Courier, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-cream);
            color: var(--ink-black);
            font-family: var(--font-sans);
            line-height: 1.45;
            padding: 24px;
        }}

        /* Header Bar */
        .master-header {{
            background: var(--ink-black);
            color: #FFFFFF;
            padding: 20px 28px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 2px solid var(--border-aged);
            margin-bottom: 24px;
        }}
        .master-header h1 {{
            font-family: var(--font-headline);
            font-size: 2.2rem;
            letter-spacing: 1px;
            color: #FFFFFF;
        }}
        .master-header .header-meta {{
            text-align: right;
            font-size: 0.95rem;
            color: #E2E8F0;
        }}
        .master-header .header-meta strong {{
            color: var(--mustard);
        }}

        /* Navigation Tabs */
        .tab-bar {{
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            border-bottom: 2px solid var(--border-aged);
            padding-bottom: 8px;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            font-family: var(--font-headline);
            font-size: 1.25rem;
            letter-spacing: 0.5px;
            padding: 8px 18px;
            cursor: pointer;
            color: var(--halftone-gray);
            border-bottom: 3px solid transparent;
            transition: all 0.2s ease;
        }}
        .tab-btn.active {{
            color: var(--hot-red);
            border-bottom-color: var(--hot-red);
        }}

        /* Section Containers */
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}

        /* SYSTEM SPEC SHEET SECTION */
        .system-sheet-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1.2fr;
            gap: 20px;
            margin-bottom: 24px;
        }}
        .system-card {{
            background: #FFFFFF;
            border: 2px solid var(--border-aged);
            padding: 20px;
            border-radius: 4px;
            box-shadow: var(--card-shadow);
        }}
        .system-card h2 {{
            font-family: var(--font-headline);
            font-size: 1.4rem;
            border-bottom: 1px solid var(--border-aged);
            padding-bottom: 8px;
            margin-bottom: 14px;
            letter-spacing: 0.5px;
        }}

        /* Type Specimen Card */
        .specimen-h1 {{ font-family: var(--font-headline); font-size: 2.8rem; margin: 8px 0; }}
        .specimen-stat {{ font-family: var(--font-headline); font-size: 4rem; color: var(--hot-red); }}
        .specimen-label {{
            font-family: var(--font-typewriter);
            font-size: 1.25rem;
            display: inline-block;
            border-bottom: 3px solid var(--hot-red);
            padding-bottom: 4px;
            margin-top: 10px;
        }}

        /* Swatches */
        .swatches-row {{ display: flex; gap: 10px; margin: 12px 0; }}
        .swatch-box {{
            flex: 1;
            height: 90px;
            border: 1px solid var(--border-aged);
            border-radius: 2px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: 6px;
            font-size: 0.75rem;
            font-weight: bold;
        }}
        .swatch-box span {{ background: rgba(255,255,255,0.85); padding: 2px 4px; border-radius: 2px; }}

        /* Motion Thumbnails Grid */
        .motion-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-top: 12px;
        }}
        .motion-card {{
            border: 1px solid var(--border-aged);
            background: var(--bg-cream);
            padding: 12px;
            border-radius: 2px;
        }}
        .motion-badge {{
            background: var(--ink-black);
            color: #FFFFFF;
            font-size: 0.75rem;
            font-weight: bold;
            padding: 2px 6px;
            display: inline-block;
            margin-bottom: 6px;
        }}
        .motion-title {{ font-weight: bold; font-size: 0.88rem; margin-bottom: 6px; }}
        .motion-desc {{ font-size: 0.78rem; color: #4B5563; }}

        /* SCENE STORYBOARD GRID */
        .scene-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 24px;
        }}
        .scene-card {{
            background: #FFFFFF;
            border: 2px solid var(--border-aged);
            border-radius: 4px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
        }}
        .scene-card-header {{
            background: var(--ink-black);
            color: #FFFFFF;
            padding: 10px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .scene-tag {{
            font-family: var(--font-headline);
            color: #F8FAFC;
            font-size: 1.1rem;
        }}
        .scene-headline {{
            font-family: var(--font-headline);
            color: #E2E8F0;
            font-size: 1.15rem;
            margin: 0 10px;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .scene-dur {{
            color: var(--hot-red);
            font-weight: bold;
            font-size: 1rem;
        }}

        .scene-visual-wrapper {{
            width: 100%;
            height: 236px;
            background: #EFE9DA;
            border-bottom: 1px solid var(--border-aged);
            position: relative;
            overflow: hidden;
        }}
        .scene-visual-wrapper img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .visual-fallback-diorama {{
            display: none;
            width: 100%;
            height: 100%;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: #F4F1EA;
            border: 2px dashed #C9BB9C;
        }}
        .fallback-visual .visual-fallback-diorama {{
            display: flex;
        }}
        .stat-hero-badge {{
            position: absolute;
            top: 12px;
            left: 12px;
            z-index: 10;
            background: var(--hot-red);
            color: #FFFFFF;
            font-family: var(--font-headline);
            font-size: 1.6rem;
            font-weight: bold;
            padding: 4px 14px;
            border-radius: 2px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.35);
            letter-spacing: 0.5px;
            pointer-events: none;
        }}
        .diorama-hero-label {{
            font-family: var(--font-headline);
            font-size: 1.3rem;
            color: var(--ink-black);
        }}
        .diorama-subtext {{
            font-size: 0.8rem;
            color: var(--halftone-gray);
            margin-top: 4px;
        }}

        .scene-body {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            flex: 1;
        }}
        .field-label {{
            font-size: 0.75rem;
            font-weight: bold;
            color: var(--halftone-gray);
            letter-spacing: 0.5px;
        }}
        .narration-text {{
            font-family: var(--font-typewriter);
            font-size: 0.92rem;
            color: var(--ink-black);
            background: #FAF8F5;
            padding: 8px 10px;
            border-left: 3px solid var(--hot-red);
            margin-top: 4px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 0.82rem;
        }}
        .meta-val {{ font-weight: 500; color: #1E293B; }}
        .badge {{
            display: inline-block;
            font-size: 0.72rem;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 2px;
        }}
        .badge-motion {{ background: #FEE2E2; color: var(--hot-red); }}
        .badge-h {{ background: #FEF3C7; color: #92400E; }}
        .badge-cam {{ background: #E0E7FF; color: #1E3A8A; }}

        .prompt-accordion details {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 3px;
            padding: 6px 10px;
        }}
        .prompt-accordion summary {{
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: bold;
            color: #475569;
        }}
        .prompt-code {{
            margin-top: 8px;
            font-family: var(--font-typewriter);
            font-size: 0.75rem;
            white-space: pre-wrap;
            word-break: break-all;
            color: #0F172A;
            background: #F1F5F9;
            padding: 8px;
            border-radius: 2px;
            max-height: 140px;
            overflow-y: auto;
        }}

        /* HUMAN GATE ACTION FOOTER */
        .human-gate-footer {{
            margin-top: 32px;
            background: #FFFFFF;
            border: 2px solid var(--hot-red);
            padding: 24px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: var(--card-shadow);
        }}
        .human-gate-info h3 {{
            font-family: var(--font-headline);
            font-size: 1.6rem;
            color: var(--hot-red);
            margin-bottom: 4px;
        }}
        .human-gate-info p {{
            font-size: 0.95rem;
            color: #334155;
        }}
        .gate-actions {{
            display: flex;
            gap: 14px;
        }}
        .btn {{
            font-family: var(--font-headline);
            font-size: 1.15rem;
            letter-spacing: 0.5px;
            padding: 12px 24px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .btn-omni {{
            background: var(--hot-red);
            color: #FFFFFF;
        }}
        .btn-omni:hover {{ background: #962215; }}
        .btn-full {{
            background: var(--ink-black);
            color: #FFFFFF;
        }}
        .btn-full:hover {{ background: #000000; }}
    </style>
</head>
<body>

    <!-- TOP HEADER -->
    <div class="master-header">
        <div>
            <h1>VOX MASTER SCENE DASHBOARD</h1>
            <div style="font-family: var(--font-typewriter); font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">
                AVF-STAB-001 // DOCUMENTARY-COLLAGE EXPLAINER PRODUCTION
            </div>
        </div>
        <div class="header-meta">
            <div>EPISODE: <strong>{episode_id}</strong> ({market})</div>
            <div>TITLE: {episode_title[:45]}</div>
            <div>RUNTIME: ~{int(runtime_s)}s // TOTAL SCENES: {total_scenes}</div>
        </div>
    </div>

    <!-- NAVIGATION TABS -->
    <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('tab-storyboard')">PER-SCENE STORYBOARDS ({total_scenes})</button>
        <button class="tab-btn" onclick="switchTab('tab-system')">MASTER VISUAL SYSTEM</button>
    </div>

    <!-- TAB 1: PER-SCENE STORYBOARDS -->
    <div id="tab-storyboard" class="tab-panel active">
        <div class="scene-grid">
            {all_scenes_joined}
        </div>
    </div>

    <!-- TAB 2: MASTER VISUAL SYSTEM -->
    <div id="tab-system" class="tab-panel">
        <div class="system-sheet-grid">
            <!-- TYPE SPECIMEN -->
            <div class="system-card">
                <h2>TYPE SPECIMEN</h2>
                <div style="font-size: 0.75rem; color: var(--halftone-gray); font-weight: bold;">H1 HEADLINE</div>
                <div class="specimen-h1">THE DEAL</div>
                <div style="font-size: 0.75rem; color: var(--halftone-gray); font-weight: bold; margin-top: 12px;">STAT HERO</div>
                <div class="specimen-stat">$123</div>
                <div style="font-size: 0.75rem; color: var(--halftone-gray); font-weight: bold; margin-top: 14px;">ANNOTATION LABEL</div>
                <div><span class="specimen-label">Fig. 3 - Trade Route</span></div>
            </div>

            <!-- PALETTE -->
            <div class="system-card">
                <h2>PALETTE SPECIFICATION</h2>
                <div class="swatches-row">
                    <div class="swatch-box" style="background: #C9BB9C;"><span>#C9BB9C TAN</span></div>
                    <div class="swatch-box" style="background: #1A1A1A; color: white;"><span>#1A1A1A INK</span></div>
                    <div class="swatch-box" style="background: #8C8C8C;"><span>#8C8C8C GRAY</span></div>
                    <div class="swatch-box" style="background: #B62E1F; color: white;"><span>#B62E1F RED</span></div>
                    <div class="swatch-box" style="background: #D9A441;"><span>#D9A441 GOLD</span></div>
                </div>
                <div style="font-size: 0.8rem; margin-top: 14px; color: var(--hot-red); font-weight: bold;">
                    • HOT RED IS RESERVED FOR STROKES, UNDERLINES, AND ARROWS.
                </div>
                <div style="font-size: 0.8rem; color: var(--mustard); font-weight: bold; margin-top: 4px;">
                    • MUSTARD IS SECONDARY ACCENT ONLY.
                </div>
                <div style="font-size: 0.8rem; color: #475569; margin-top: 8px;">
                    • BASE STAGE: Archival Cream Paper #F4F1EA with 100% diorama tabletop lighting.
                </div>
            </div>

            <!-- COMPONENT ZOO & SYSTEM NOTES -->
            <div class="system-card">
                <h2>COMPONENT ZOO & SYSTEM NOTES</h2>
                <ul style="font-size: 0.85rem; padding-left: 18px; line-height: 1.6; color: #334155;">
                    <li><strong>Halftone Cutouts:</strong> 60lpi halftone with rough deckle white keyline & offset crimson drop stroke.</li>
                    <li><strong>Torn Paper Ledger:</strong> Archival torn receipts, accounting ledgers with jagged tear alpha.</li>
                    <li><strong>Giant Stat Cards:</strong> Red rectangular cards with giant bold condensed white numbers.</li>
                    <li><strong>Red Map Pins & Underlines:</strong> Precision geometric location markers and directional strokes.</li>
                    <li><strong>Single Construction Logic:</strong> Halftone texture, rough keyline, offset red stroke across 100% elements.</li>
                    <li><strong>Zero CGI Mandate:</strong> 100% tactile desk diorama with newsroom archival authenticity.</li>
                </ul>
            </div>
        </div>

        <!-- MOTION THUMBNAILS -->
        <div class="system-card" style="margin-top: 20px;">
            <h2>MOTION THUMBNAIL SYSTEM (VOX CONTINUOUS TACTILE KINEMATICS & DOCUMENTARY CAMERAS)</h2>
            <div class="motion-grid">
                <div class="motion-card">
                    <span class="motion-badge">MOTION 1</span>
                    <div class="motion-title">POP-UP UNFOLD & 90° DIAGONAL GLIDE</div>
                    <div class="motion-desc">Accordion paper unfold in 0.3s held steady, then gentle 10-15° diagonal tracking easing to resting stop.</div>
                </div>
                <div class="motion-card">
                    <span class="motion-badge">MOTION 2</span>
                    <div class="motion-title">SEAL STAMP IMPACT & SEQUENTIAL RACK FOCUS</div>
                    <div class="motion-desc">Heavy seal stamp strikes with 8-frame damped impact, 6-frame pause, then smooth 20-frame focus rack to ledger.</div>
                </div>
                <div class="motion-card">
                    <span class="motion-badge">MOTION 3</span>
                    <div class="motion-title">CALIPER CLAMP & ANCHORED MACRO GLIDE</div>
                    <div class="motion-desc">Brass caliper clamps document margin locked at frame center while background paper drifts slowly at &le; 4%/s.</div>
                </div>
                <div class="motion-card">
                    <span class="motion-badge">MOTION 4</span>
                    <div class="motion-title">RED YARN TENSION & MOTIVATED FOLLOW-PAN</div>
                    <div class="motion-desc">Taut crimson evidence yarn snaps taut, camera smoothly follows tension line with long gentle deceleration landing.</div>
                </div>
                <div class="motion-card">
                    <span class="motion-badge">MOTION 5</span>
                    <div class="motion-title">OPTICAL LOUPE & 8° PIVOT ORBIT</div>
                    <div class="motion-desc">Convex loupe reveals fine print, subtle 8° orbit centered on lens maintaining magnified text locked at center.</div>
                </div>
                <div class="motion-card">
                    <span class="motion-badge">MOTION 6</span>
                    <div class="motion-title">PARADOX & FIXED DUTCH HIGHLIGHT PUSH</div>
                    <div class="motion-desc">Static overhead view at fixed 5° angle without roll, gentle 5% push-in decelerating smoothly onto highlighted clause.</div>
                </div>
            </div>
        </div>
    </div>

    <!-- HUMAN GATE APPROVAL FOOTER -->
    <div class="human-gate-footer">
        <div class="human-gate-info">
            <h3>🛑 HUMAN GATE: MASTER SCENES & STORYBOARDS READY FOR REVIEW</h3>
            <p>Inspect composite seed layouts, dialogue sync, typography hierarchy, and motion thumbnails above.</p>
        </div>
        <div class="gate-actions">
            <button class="btn btn-omni" onclick="alert('CLI Command: python scripts/flow_video_dispatcher.py --episode {episode_id} --model omni --limit 2')">
                ▶ RUN OMNI PILOT (2 SCENES DEMO)
            </button>
            <button class="btn btn-full" onclick="alert('CLI Command: python -m orchestrator.run_pipeline --run-id {episode_id} --from s08_video_gen --to s11_qc')">
                ▶ APPROVE & RENDER FULL VIDEO
            </button>
        </div>
    </div>

    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    logger.info(f"Master Scene Dashboard HTML generated at: {output_path}")
    return output_path


# ==============================================================================
# MASTER SERVICE ENTRYPOINT (CALLED BY S05, S07 & PIPELINE)
# ==============================================================================
def generate_master_scene_package(
    ctx: Any,
    scenes: List[Dict[str, Any]],
    payload: Optional[Dict[str, Any]] = None,
    image_mode: bool = False,
) -> Dict[str, Any]:
    """Generates the comprehensive Vox Master Scene and Master Sheet package.

    Emits:
    1. master_sheet_system.png & master_sheet_system.html: Master Visual System
    2. master_sheet_scenes.png & master_sheet_scenes.html: Per-Scene Storyboard Contact Sheet
    3. master_sheet_dashboard.html: Interactive Human Gate Dashboard
    4. master_sheet_manifest.json: Machine-readable contract
    """
    start_ts = time.time()
    payload = payload or {}

    # Support string run_id or arbitrary objects gracefully
    if isinstance(ctx, str):
        from core.paths import RunPaths
        run_paths = RunPaths(ctx)
        class _SimpleContext:
            def __init__(self, run_id, paths):
                self.run_id = run_id
                self.paths = paths
                self.topic = run_id
                self.manifest = None
        ctx = _SimpleContext(ctx, run_paths)
    elif not hasattr(ctx, "paths"):
        from core.paths import RunPaths
        run_id = getattr(ctx, "run_id", "EPISODE")
        setattr(ctx, "paths", RunPaths(run_id))

    out_dir = ctx.paths.root / "master_sheets"
    out_dir.mkdir(parents=True, exist_ok=True)

    episode_id = str(ctx.run_id)
    episode_title = str(ctx.topic or payload.get("title") or payload.get("title_working") or episode_id)
    market = getattr(ctx.manifest, "market", "EN") if hasattr(ctx, "manifest") and ctx.manifest else "EN"
    runtime_s = float(payload.get("runtime_seconds") or sum(float(s.get("duration_est_sec") or 5.5) for s in scenes) or 180.0)

    # 1. Master System Sheet (PNG & HTML)
    sys_png = out_dir / "master_sheet_system.png"
    try:
        render_master_system_sheet_png(
            episode_title=episode_title,
            output_path=sys_png,
            market=market,
            runtime_s=runtime_s,
            total_scenes=len(scenes),
        )
    except Exception as _png_err:
        logger.warning(f"Failed to render master_sheet_system.png: {_png_err}")
        sys_png = None

    # Pre-resolve scene images dynamically across canonical and fallback directories
    seeds_dir = ctx.paths.composite_seeds_dir if hasattr(ctx, "paths") and hasattr(ctx.paths, "composite_seeds_dir") else out_dir.parent / "composite_seeds"
    search_dirs: List[Path] = [seeds_dir, out_dir.parent / "images", out_dir.parent / "assets"]
    brain_browser_dir = Path.home() / ".gemini" / "antigravity" / "brain" / "browser_assets" / episode_id
    if brain_browser_dir.exists():
        search_dirs.append(brain_browser_dir)

    image_paths_map: Dict[str, str] = {}
    resolved_scenes: List[str] = []
    missing_scenes: List[str] = []

    for idx_sc, sc in enumerate(scenes):
        sc_id = sc.get("scene_id") or f"SCENE_{idx_sc + 1:02d}"
        first_shot = sc.get("shots", [{}])[0] if isinstance(sc.get("shots"), list) and len(sc.get("shots")) > 0 else {}
        explicit = (
            sc.get("image_path")
            or sc.get("seed_image")
            or sc.get("file_path")
            or first_shot.get("seed_image")
            or first_shot.get("image_path")
        )
        resolved = resolve_scene_image_path(
            scene_id=sc_id,
            image_dir=seeds_dir,
            fallback_dirs=search_dirs,
            explicit_path=explicit,
        )
        if resolved and resolved.exists():
            resolved_scenes.append(sc_id)
            # Ensure copy into composite_seeds if resolved from an alternate directory
            if seeds_dir.exists() and resolved.parent.resolve() != seeds_dir.resolve():
                target_copy = seeds_dir / f"composite_{sc_id.lower()}.png"
                if not target_copy.exists() or target_copy.stat().st_size < 1000:
                    try:
                        import shutil
                        shutil.copy2(str(resolved), str(target_copy))
                        resolved = target_copy
                    except Exception as _cpe:
                        logger.debug(f"Copying resolved image to seeds_dir notice: {_cpe}")
            try:
                rel = resolved.relative_to(out_dir.parent)
                image_paths_map[sc_id] = f"../{rel.as_posix()}"
            except ValueError:
                image_paths_map[sc_id] = resolved.as_posix()
        else:
            missing_scenes.append(sc_id)
            image_paths_map[sc_id] = f"../composite_seeds/composite_{sc_id.lower()}.png"

    # 2. Scene Storyboard Contact Sheet (PNG)
    scenes_png = out_dir / "master_sheet_scenes.png"
    try:
        render_scene_contact_sheet_png(
            scenes=scenes,
            output_path=scenes_png,
            image_dir=seeds_dir,
            cols=3,
            rows=None,
            page_index=0,
        )
    except Exception as _sc_err:
        logger.warning(f"Failed to render master_sheet_scenes.png: {_sc_err}")
        scenes_png = None

    # 3. Interactive Master Scene Dashboard (HTML)
    dashboard_html = out_dir / "master_sheet_dashboard.html"
    generate_master_scene_dashboard_html(
        episode_id=episode_id,
        episode_title=episode_title,
        scenes=scenes,
        output_path=dashboard_html,
        market=market,
        runtime_s=runtime_s,
        seeds_dir_rel="../composite_seeds",
        image_paths_map=image_paths_map,
    )

    # Also emit master_sheet_scenes.html and master_sheet_system.html
    scenes_html = out_dir / "master_sheet_scenes.html"
    scenes_html.write_text(dashboard_html.read_text(encoding="utf-8"), encoding="utf-8")

    # In master_sheet_system.html, activate the SYSTEM tab by default
    sys_html = out_dir / "master_sheet_system.html"
    raw_dashboard = dashboard_html.read_text(encoding="utf-8")
    sys_content = raw_dashboard.replace(
        '<button class="tab-btn active" onclick="switchTab(\'tab-storyboard\')">',
        '<button class="tab-btn" onclick="switchTab(\'tab-storyboard\')">'
    ).replace(
        '<button class="tab-btn" onclick="switchTab(\'tab-system\')">',
        '<button class="tab-btn active" onclick="switchTab(\'tab-system\')">'
    ).replace(
        '<div id="tab-storyboard" class="tab-panel active">',
        '<div id="tab-storyboard" class="tab-panel">'
    ).replace(
        '<div id="tab-system" class="tab-panel">',
        '<div id="tab-system" class="tab-panel active">'
    )
    sys_html.write_text(sys_content, encoding="utf-8")

    effective_image_mode = bool(image_mode or (len(scenes) > 0 and len(missing_scenes) == 0))

    # Compute Stat Hero manifest coverage
    stat_heroes_summary: Dict[str, Optional[str]] = {}
    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", f"SCENE_{idx+1:02d}")
        stat_heroes_summary[sc_id] = extract_stat_hero_from_text(sc.get("narration") or "")
    stat_heroes_count = sum(1 for v in stat_heroes_summary.values() if v is not None)

    manifest = {
        "episode_id": episode_id,
        "episode_title": episode_title,
        "market": market,
        "total_scenes": len(scenes),
        "available_images_count": len(resolved_scenes),
        "missing_images_count": len(missing_scenes),
        "missing_scenes": missing_scenes,
        "image_mode": effective_image_mode,
        "runtime_seconds": runtime_s,
        "stat_heroes_count": stat_heroes_count,
        "stat_heroes": stat_heroes_summary,
        "files": {
            "master_sheet_system_png": str(sys_png) if sys_png and sys_png.exists() else None,
            "master_sheet_scenes_png": str(scenes_png) if scenes_png and scenes_png.exists() else None,
            "master_sheet_dashboard_html": str(dashboard_html),
            "master_sheet_scenes_html": str(scenes_html),
            "master_sheet_system_html": str(sys_html),
        },
        "palette": VOX_PALETTE,
        "motion_thumbnails": MOTION_THUMBNAIL_TYPES,
        "generation_latency_sec": round(time.time() - start_ts, 2),
    }

    manifest_path = out_dir / "master_sheet_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Master Scene Package generated successfully: {manifest_path} (Images: {len(resolved_scenes)}/{len(scenes)})")
    return manifest


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Master Scene & Master Sheet Generator")
    parser.add_argument("--episode", type=str, required=True, help="Episode / Run ID (e.g. KR_EP0005_gadeok_cost_risk)")
    parser.add_argument("--repo-root", type=str, default=None, help="Optional repo root path")
    parser.add_argument("--image-mode", action="store_true", default=True, help="Include composite seed images")
    parser.add_argument("--no-image-mode", dest="image_mode", action="store_false", help="Render pre-production wireframe storyboards without images")
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parent.parent.parent
    ep_id = args.episode.strip().strip("'\"")

    from core.paths import resolve_run_paths
    paths = resolve_run_paths(ep_id, repo_root=repo_root)

    payload = {}
    scenes = []
    dp_candidates = [
        paths.root / "director_plan.json",
        paths.root / "s05_director_plan" / "artifact.json",
        paths.root / "dp_plan.json",
    ]
    for c in dp_candidates:
        if c.exists() and c.stat().st_size > 100:
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
                if "payload" in data:
                    payload = data["payload"]
                    scenes = payload.get("scenes", [])
                elif "scenes" in data:
                    payload = data
                    scenes = data.get("scenes", [])
                if scenes:
                    break
            except Exception as _e:
                continue

    if not scenes:
        print(f"ERROR: No scenes found in director plan for {ep_id}")
        sys.exit(1)

    class _Context:
        def __init__(self, run_id, paths, topic):
            self.run_id = run_id
            self.paths = paths
            self.topic = topic
            self.manifest = None

    ctx = _Context(ep_id, paths, ep_id)
    result = generate_master_scene_package(ctx, scenes=scenes, payload=payload, image_mode=args.image_mode)
    print(json.dumps(result, indent=2))
