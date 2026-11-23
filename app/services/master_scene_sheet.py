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


def render_scene_master_asset_sheet_png(
    scene: Dict[str, Any],
    output_path: Path,
    image_dir: Optional[Path] = None,
    market: str = "EN",
) -> Path:
    """Renders the Canonical Vox Master Asset Sheet for a single scene (FT-201 / Direction A+).
    
    Shows the Assembled Result Anchor on the left, the Modular Decomposed Asset Zoo on the right,
    and the Unidirectional Motion Coupling Contract at the bottom.
    """
    from PIL import Image, ImageDraw

    w, h = 1920, 1080
    bg_color = VOX_PALETTE["cream_paper"]
    card_bg = "#FFFFFF"
    ink = VOX_PALETTE["ink_black"]
    hot_red = VOX_PALETTE["hot_red"]
    border_col = VOX_PALETTE["aged_border"]
    gray = VOX_PALETTE["halftone_gray"]
    fonts = _get_pil_fonts()

    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Outer aged frame border
    draw.rectangle([16, 16, w - 16, h - 16], outline=border_col, width=3)

    # Top Header
    sc_id = scene.get("scene_id", "SCENE_01")
    headline = (scene.get("headline") or "FORENSIC COLLAGE").upper()
    dur = float(scene.get("duration_est_sec") or 5.5)

    draw.rectangle([20, 20, w - 20, 75], fill=ink)
    draw.text((36, 28), f"VOX MASTER ASSET SHEET // {sc_id} (DIRECTION A+)", fill="#FFFFFF", font=fonts["title"])
    draw.text((w - 28, 38), f"{headline[:36]} // {dur:.1f}S // LOCKED COMPUTER FRAME", fill=hot_red, font=fonts["body_bold"], anchor="ra")

    # =========================================================================
    # LEFT PANEL: ASSEMBLED RESULT SCENE (STYLE ANCHOR)
    # =========================================================================
    left_x1, left_y1, left_x2, left_y2 = 40, 95, 880, 780
    draw.rectangle([left_x1, left_y1, left_x2, left_y2], fill=card_bg, outline=border_col, width=2)
    
    # Title bar
    draw.rectangle([left_x1 + 2, left_y1 + 2, left_x2 - 2, left_y1 + 38], fill=ink)
    draw.text((left_x1 + 12, left_y1 + 10), "[STYLE ANCHOR] ASSEMBLED RESULT SCENE (TARGET COMPOSITE)", fill="#FFFFFF", font=fonts["label"])

    # 16:9 Image Area: 820 x 460
    img_x1, img_y1 = left_x1 + 10, left_y1 + 46
    img_w, img_h = 820, 460
    img_x2, img_y2 = img_x1 + img_w, img_y1 + img_h

    # Check for seed image
    img_loaded = False
    if image_dir and image_dir.exists():
        for cand_name in [f"composite_{sc_id.lower()}.png", f"{sc_id.lower()}.png", f"{sc_id}.png"]:
            cand_p = image_dir / cand_name
            if cand_p.exists():
                try:
                    s_img = Image.open(cand_p).convert("RGB")
                    s_img = s_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
                    img.paste(s_img, (img_x1, img_y1))
                    img_loaded = True
                    break
                except Exception as _cand_err:
                    logger.debug(f"Candidate image read bypass: {_cand_err}")

    if not img_loaded:
        # Draw high-fidelity tactile diorama preview
        draw.rectangle([img_x1, img_y1, img_x2, img_y2], fill=(244, 241, 234), outline=border_col, width=1)
        # Grid lines
        for gx in range(img_x1, img_x2, 40):
            draw.line([(gx, img_y1), (gx, img_y2)], fill=(230, 226, 216), width=1)
        for gy in range(img_y1, img_y2, 40):
            draw.line([(img_x1, gy), (img_x2, gy)], fill=(230, 226, 216), width=1)

        # Hero silhouette preview (center-left)
        hero_obj = scene.get("hero_cutout_object") or "Archival Hero Subject"
        hx1, hy1, hx2, hy2 = img_x1 + 60, img_y1 + 70, img_x1 + 320, img_y2 - 60
        # Red drop shadow
        draw.rectangle([hx1 + 10, hy1 + 10, hx2 + 10, hy2 + 10], fill=(214, 46, 31))
        # White deckle edge
        draw.rectangle([hx1, hy1, hx2, hy2], fill="#FFFFFF", outline=ink, width=2)
        # Halftone texture fill
        draw.rectangle([hx1 + 8, hy1 + 8, hx2 - 8, hy2 - 8], fill=(45, 45, 45))
        for dy in range(hy1 + 14, hy2 - 14, 14):
            for dx in range(hx1 + 14, hx2 - 14, 14):
                draw.ellipse([dx - 2, dy - 2, dx + 2, dy + 2], fill=(120, 120, 120))
        draw.text(((hx1 + hx2) // 2, (hy1 + hy2) // 2), f"{hero_obj[:22].upper()}", fill="#FFFFFF", font=fonts["label"], anchor="mm")

        # Stat Card preview (center-right)
        stat_hero = extract_stat_hero_from_text(scene.get("narration") or "")
        if stat_hero:
            cx1, cy1, cx2, cy2 = img_x1 + 420, img_y1 + 100, img_x2 - 50, img_y1 + 320
            draw.rectangle([cx1 + 8, cy1 + 8, cx2 + 8, cy2 + 8], fill=(26, 26, 26, 80))
            draw.rectangle([cx1, cy1, cx2, cy2], fill=bg_color, outline=border_col, width=2)
            draw.rectangle([cx1, cy1, cx2, cy1 + 36], fill=ink)
            draw.text((cx1 + 12, cy1 + 8), "QUANTITATIVE EVIDENCE", fill="#FFFFFF", font=fonts["caption"])
            draw.text(((cx1 + cx2) // 2, cy1 + 110), stat_hero, fill=hot_red, font=fonts["stat_hero"], anchor="mm")

        # Red connecting line / vector
        draw.line([(hx2, (hy1 + hy2) // 2), (img_x1 + 420, img_y1 + 210)], fill=hot_red, width=4)
        draw.ellipse([hx2 - 6, (hy1 + hy2) // 2 - 6, hx2 + 6, (hy1 + hy2) // 2 + 6], fill=(217, 164, 65))
        draw.ellipse([img_x1 + 414, img_y1 + 204, img_x1 + 426, img_y1 + 216], fill=(217, 164, 65))

        draw.text((img_x1 + img_w // 2, img_y2 - 20), "[ASSEMBLED RESULT COMPOSITE DIORAMA — ANCHOR REFERENCE]", fill=gray, font=fonts["caption"], anchor="mm")

    # Narration & Paradox area below image
    narr_y = img_y2 + 12
    narr = scene.get("narration") or "Tactile documentary investigation."
    draw.text((left_x1 + 14, narr_y), "VOICEOVER NARRATION:", fill=gray, font=fonts["caption"])
    words = narr.split()
    l1, l2, l3 = "", "", ""
    for w_i in words:
        if len(l1) + len(w_i) + 1 <= 60:
            l1 += (" " if l1 else "") + w_i
        elif len(l2) + len(w_i) + 1 <= 60:
            l2 += (" " if l2 else "") + w_i
        elif len(l3) + len(w_i) + 1 <= 60:
            l3 += (" " if l3 else "") + w_i
    draw.text((left_x1 + 14, narr_y + 18), l1, fill=ink, font=fonts["typewriter_small"])
    if l2:
        draw.text((left_x1 + 14, narr_y + 36), l2, fill=ink, font=fonts["typewriter_small"])
    if l3:
        draw.text((left_x1 + 14, narr_y + 54), l3, fill=ink, font=fonts["typewriter_small"])

    # =========================================================================
    # RIGHT PANEL: MODULAR ASSET DECOMPOSITION ZOO (4 INDEPENDENT LAYERS)
    # =========================================================================
    right_x1, right_y1, right_x2, right_y2 = 905, 95, 1880, 780
    draw.rectangle([right_x1, right_y1, right_x2, right_y2], fill=bg_color, outline=border_col, width=2)
    
    # Title bar
    draw.rectangle([right_x1 + 2, right_y1 + 2, right_x2 - 2, right_y1 + 38], fill=ink)
    draw.text((right_x1 + 12, right_y1 + 10), "MODULAR ASSET DECOMPOSITION ZOO (REMOTION INPUT LAYERS WITH ALPHA)", fill="#FFFFFF", font=fonts["label"])

    decomp = scene.get("decomposed_prompts") or {}
    tool_name = scene.get("interacting_tool") or "Forensic Brass Caliper / Red Yarn"
    hero_name = scene.get("hero_cutout_object") or "Archival Subject Cutout"
    stat_val = extract_stat_hero_from_text(narr) or "AUDIT DATA"

    # 4 Grid Cards: 2 cols x 2 rows
    # Col 1: 915 -> 1385, Col 2: 1400 -> 1870
    # Row 1: 145 -> 445, Row 2: 460 -> 765
    cw, ch = 470, 305

    # --- CARD 1: STAGE BACKDROP ---
    c1_x1, c1_y1 = right_x1 + 10, right_y1 + 48
    draw.rectangle([c1_x1, c1_y1, c1_x1 + cw, c1_y1 + ch], fill=card_bg, outline=border_col, width=1)
    draw.rectangle([c1_x1 + 2, c1_y1 + 2, c1_x1 + cw - 2, c1_y1 + 28], fill=border_col)
    draw.text((c1_x1 + 8, c1_y1 + 6), "1. THE STAGE (BACKDROP CANVAS)", fill="#FFFFFF", font=fonts["caption"])
    # Thumbnail
    c1_thumb_box = [c1_x1 + 10, c1_y1 + 36, c1_x1 + cw - 10, c1_y1 + 160]
    c1_loaded = False
    if image_dir and image_dir.exists():
        for cand_bg in [f"stage_{sc_id.lower()}.png", f"bg_{sc_id.lower()}.png", f"stage_{sc_id}.png"]:
            cand_p = image_dir / cand_bg
            if cand_p.exists():
                try:
                    bg_im = Image.open(cand_p).convert("RGB")
                    bw, bh = cw - 20, 124
                    bg_im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
                    draw.rectangle(c1_thumb_box, fill="#FFFFFF", outline=gray, width=1)
                    img.paste(bg_im, (c1_x1 + 10 + (bw - bg_im.width) // 2, c1_y1 + 36 + (bh - bg_im.height) // 2))
                    c1_loaded = True
                    break
                except Exception as _cand_err:
                    logger.debug(f"Candidate image read bypass: {_cand_err}")
    if not c1_loaded:
        draw.rectangle(c1_thumb_box, fill=(244, 241, 234), outline=gray, width=1)
        for gx in range(c1_x1 + 10, c1_x1 + cw - 10, 25):
            draw.line([(gx, c1_y1 + 36), (gx, c1_y1 + 160)], fill=(225, 220, 210), width=1)
        draw.text((c1_x1 + cw // 2, c1_y1 + 98), "#F4F1EA AGED NEWSPRINT // ZERO OBJECTS", fill=gray, font=fonts["caption"], anchor="mm")
    # Details
    draw.text((c1_x1 + 10, c1_y1 + 170), "CANVAS: Fixed 1920x1080 Computer Frame Desk", fill=ink, font=fonts["caption"])
    draw.text((c1_x1 + 10, c1_y1 + 190), "SPEC: Flat top-down desk view, fibrous paper grain", fill=gray, font=fonts["caption"])
    draw.text((c1_x1 + 10, c1_y1 + 210), "ALPHA: 0% (Solid opaque background plane)", fill=gray, font=fonts["caption"])

    # --- CARD 2: HERO CUTOUT OBJECT ---
    c2_x1, c2_y1 = right_x1 + cw + 25, right_y1 + 48
    draw.rectangle([c2_x1, c2_y1, c2_x1 + cw, c2_y1 + ch], fill=card_bg, outline=border_col, width=1)
    draw.rectangle([c2_x1 + 2, c2_y1 + 2, c2_x1 + cw - 2, c2_y1 + 28], fill=border_col)
    draw.text((c2_x1 + 8, c2_y1 + 6), "2. HERO CUTOUT (PRIMARY SUBJECT)", fill="#FFFFFF", font=fonts["caption"])
    # Thumbnail: White deckle cutout on pure #FFFFFF
    c2_thumb_box = [c2_x1 + 10, c2_y1 + 36, c2_x1 + cw - 10, c2_y1 + 160]
    draw.rectangle(c2_thumb_box, fill="#FFFFFF", outline=gray, width=1)
    c2_loaded = False
    if image_dir and image_dir.exists():
        for cand_hero in [f"hero_{sc_id.lower()}.png", f"cutout_{sc_id.lower()}.png", f"hero_{sc_id}.png"]:
            cand_p = image_dir / cand_hero
            if cand_p.exists():
                try:
                    h_im = Image.open(cand_p).convert("RGBA")
                    bw, bh = cw - 20, 124
                    h_im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
                    paste_x = c2_x1 + 10 + (bw - h_im.width) // 2
                    paste_y = c2_y1 + 36 + (bh - h_im.height) // 2
                    img.paste(h_im, (paste_x, paste_y), h_im)
                    c2_loaded = True
                    break
                except Exception as _cand_err:
                    logger.debug(f"Candidate image read bypass: {_cand_err}")
    if not c2_loaded:
        draw.rectangle([c2_x1 + 180, c2_y1 + 44, c2_x1 + 290, c2_y1 + 152], fill=(214, 46, 31)) # shadow
        draw.rectangle([c2_x1 + 174, c2_y1 + 38, c2_x1 + 284, c2_y1 + 146], fill="#FFFFFF", outline=ink, width=1) # deckle
        draw.rectangle([c2_x1 + 180, c2_y1 + 44, c2_x1 + 278, c2_y1 + 140], fill=(45, 45, 45)) # halftone
        draw.text((c2_x1 + cw // 2, c2_y1 + 92), f"[{hero_name[:18].upper()}]", fill="#FFFFFF", font=fonts["caption"], anchor="mm")
    # Details
    draw.text((c2_x1 + 10, c2_y1 + 170), f"SUBJECT: {hero_name[:38]}", fill=ink, font=fonts["caption"])
    draw.text((c2_x1 + 10, c2_y1 + 190), "SPEC: 60lpi Halftone B&W, 2-4px deckle edge, #FFFFFF bg", fill=gray, font=fonts["caption"])
    draw.text((c2_x1 + 10, c2_y1 + 210), "ALPHA: Clean alpha cutout boundary for Remotion ingress", fill=hot_red, font=fonts["caption"])

    # --- CARD 3: STAT CARD HERO ---
    c3_x1, c3_y1 = right_x1 + 10, right_y1 + ch + 60
    draw.rectangle([c3_x1, c3_y1, c3_x1 + cw, c3_y1 + ch], fill=card_bg, outline=border_col, width=1)
    draw.rectangle([c3_x1 + 2, c3_y1 + 2, c3_x1 + cw - 2, c3_y1 + 28], fill=border_col)
    draw.text((c3_x1 + 8, c3_y1 + 6), "3. STAT HERO CARD (DATA CHIP)", fill="#FFFFFF", font=fonts["caption"])
    # Thumbnail: Giant red stat on cream card
    draw.rectangle([c3_x1 + 10, c3_y1 + 36, c3_x1 + cw - 10, c3_y1 + 160], fill=bg_color, outline=gray, width=1)
    draw.rectangle([c3_x1 + 10, c3_y1 + 36, c3_x1 + cw - 10, c3_y1 + 60], fill=ink)
    draw.text((c3_x1 + 20, c3_y1 + 42), "VERIFIED FORENSIC METRIC", fill="#FFFFFF", font=fonts["caption"])
    draw.text((c3_x1 + cw // 2, c3_y1 + 110), stat_val, fill=hot_red, font=fonts["stat_medium"], anchor="mm")
    # Details
    draw.text((c3_x1 + 10, c3_y1 + 170), f"METRIC: {stat_val}", fill=hot_red, font=fonts["caption"])
    draw.text((c3_x1 + 10, c3_y1 + 190), "SPEC: Giant bold condensed font, aged cardstock, red ink", fill=gray, font=fonts["caption"])
    draw.text((c3_x1 + 10, c3_y1 + 210), "ALPHA: Independent floating card layer with drop shadow", fill=gray, font=fonts["caption"])

    # --- CARD 4: INTERACTING TOOL / CONNECTOR ---
    c4_x1, c4_y1 = right_x1 + cw + 25, right_y1 + ch + 60
    draw.rectangle([c4_x1, c4_y1, c4_x1 + cw, c4_y1 + ch], fill=card_bg, outline=border_col, width=1)
    draw.rectangle([c4_x1 + 2, c4_y1 + 2, c4_x1 + cw - 2, c4_y1 + 28], fill=border_col)
    draw.text((c4_x1 + 8, c4_y1 + 6), "4. INTERACTING TOOL / CONNECTOR", fill="#FFFFFF", font=fonts["caption"])
    # Thumbnail: Red connector line with brass pins on white or real image
    c4_thumb_box = [c4_x1 + 10, c4_y1 + 36, c4_x1 + cw - 10, c4_y1 + 160]
    draw.rectangle(c4_thumb_box, fill="#FFFFFF", outline=gray, width=1)
    c4_loaded = False
    if image_dir and image_dir.exists():
        for cand_tool in [f"tool_{sc_id.lower()}.png", f"prop_{sc_id.lower()}.png", f"tool_{sc_id}.png"]:
            cand_p = image_dir / cand_tool
            if cand_p.exists():
                try:
                    t_im = Image.open(cand_p).convert("RGBA")
                    bw, bh = cw - 20, 124
                    t_im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
                    paste_x = c4_x1 + 10 + (bw - t_im.width) // 2
                    paste_y = c4_y1 + 36 + (bh - t_im.height) // 2
                    img.paste(t_im, (paste_x, paste_y), t_im)
                    c4_loaded = True
                    break
                except Exception as _cand_err:
                    logger.debug(f"Candidate image read bypass: {_cand_err}")
    if not c4_loaded:
        draw.line([(c4_x1 + 40, c4_y1 + 98), (c4_x1 + cw - 40, c4_y1 + 98)], fill=hot_red, width=4)
        draw.ellipse([c4_x1 + 34, c4_y1 + 92, c4_x1 + 46, c4_y1 + 104], fill=(217, 164, 65))
        draw.ellipse([c4_x1 + cw - 46, c4_y1 + 92, c4_x1 + cw - 34, c4_y1 + 104], fill=(217, 164, 65))
        draw.text((c4_x1 + cw // 2, c4_y1 + 130), f"[{tool_name[:24].upper()}]", fill=ink, font=fonts["caption"], anchor="mm")
    # Details
    draw.text((c4_x1 + 10, c4_y1 + 170), f"PROP: {tool_name[:38]}", fill=ink, font=fonts["caption"])
    draw.text((c4_x1 + 10, c4_y1 + 190), "SPEC: Mechanical instrument, crimson yarn, brass pushpin", fill=gray, font=fonts["caption"])
    draw.text((c4_x1 + 10, c4_y1 + 210), "ALPHA: Dynamic SVG/PNG overlay rendered by Remotion", fill=hot_red, font=fonts["caption"])

    # =========================================================================
    # BOTTOM PANEL: 6-IN-1 MASTER SHEET SPECIFICATION // WIRING & TRANSACTION PROMPT
    # =========================================================================
    bot_x1, bot_y1, bot_x2, bot_y2 = 40, 800, 1880, 1050
    draw.rectangle([bot_x1, bot_y1, bot_x2, bot_y2], fill=(240, 237, 228), outline=border_col, width=2)
    draw.rectangle([bot_x1 + 2, bot_y1 + 2, bot_x2 - 2, bot_y1 + 32], fill=ink)
    draw.text((bot_x1 + 12, bot_y1 + 7), "6-IN-1 MASTER SHEET SPECIFICATION // WIRING COUPLING & TRANSACTION PROMPT (FT-201)", fill="#FFFFFF", font=fonts["label"])

    col_w = (bot_x2 - bot_x1 - 50) // 4
    
    # Col 1: Phase 1 (Ingress)
    p1_x = bot_x1 + 16
    draw.text((p1_x, bot_y1 + 38), "1. KINETIC INGRESS (<=0.4s)", fill=hot_red, font=fonts["label"])
    draw.text((p1_x, bot_y1 + 58), "- Entry from screen-right (X-axis)", fill=ink, font=fonts["caption"])
    draw.text((p1_x, bot_y1 + 74), "- cubic-bezier(.7, 0, .2, 1) curve", fill=ink, font=fonts["caption"])
    draw.text((p1_x, bot_y1 + 90), "- Settle within 12 frames @ 30fps", fill=gray, font=fonts["caption"])

    # Col 2: Relational Wiring Spec
    p2_x = p1_x + col_w + 10
    draw.text((p2_x, bot_y1 + 38), "2. WIRING COUPLING SPEC", fill=hot_red, font=fonts["label"])
    draw.text((p2_x, bot_y1 + 58), f"- Connector: {tool_name[:24]}", fill=ink, font=fonts["caption"])
    draw.text((p2_x, bot_y1 + 74), "- Anchors: [450, 420] -> [1450, 240]", fill=ink, font=fonts["caption"])
    draw.text((p2_x, bot_y1 + 90), "- Dead-stop spatial lock with 12fps paper hold", fill=gray, font=fonts["caption"])

    # Col 3: Engine Roles
    p3_x = p2_x + col_w + 10
    draw.text((p3_x, bot_y1 + 38), "3. ENGINE ROLES (DIRECTION A+)", fill=hot_red, font=fonts["label"])
    draw.text((p3_x, bot_y1 + 58), "• REMOTION: 100% spatial motion & alpha layering", fill=ink, font=fonts["caption"])
    draw.text((p3_x, bot_y1 + 74), "• OMNI: Living texture plate (paper grain/scanlines)", fill=hot_red, font=fonts["caption"])
    draw.text((p3_x, bot_y1 + 90), "• WHISPER: 0ms drift karaoke subtitle sync", fill=gray, font=fonts["caption"])

    # Col 4: Information Spec Summary
    p4_x = p3_x + col_w + 10
    draw.text((p4_x, bot_y1 + 38), "4. INFORMATION SUMMARY", fill=hot_red, font=fonts["label"])
    draw.text((p4_x, bot_y1 + 58), f"• STAT: {stat_val[:18]}", fill=hot_red, font=fonts["caption"])
    draw.text((p4_x, bot_y1 + 74), f"• HERO: {hero_name[:22]}", fill=ink, font=fonts["caption"])
    draw.text((p4_x, bot_y1 + 90), f"• HEADLINE: {headline[:22]}", fill=gray, font=fonts["caption"])

    # Bottom Row: Transaction Prompt Banner
    tx_p = decomp.get("relational_motion_mechanism") or scene.get("universal_video_prompt") or f"[{hero_name}] + interacts with + [{tool_name}], leaving permanent physical residue on aged desk with 12fps paper vibration."
    draw.rectangle([bot_x1 + 10, bot_y1 + 112, bot_x2 - 10, bot_y1 + 134], fill=border_col)
    draw.text((bot_x1 + 16, bot_y1 + 117), "5. TRANSACTION & KINETIC PROMPT (OMNI / VEO LIVING TEXTURE PLATE):", fill="#FFFFFF", font=fonts["caption"])

    # Draw prompt text
    draw.rectangle([bot_x1 + 10, bot_y1 + 136, bot_x2 - 10, bot_y2 - 10], fill="#FFFFFF", outline=gray, width=1)
    words_tx = tx_p.split()
    tw1, tw2, tw3 = "", "", ""
    for w_i in words_tx:
        if len(tw1) + len(w_i) + 1 <= 130:
            tw1 += (" " if tw1 else "") + w_i
        elif len(tw2) + len(w_i) + 1 <= 130:
            tw2 += (" " if tw2 else "") + w_i
        elif len(tw3) + len(w_i) + 1 <= 130:
            tw3 += (" " if tw3 else "") + w_i
    draw.text((bot_x1 + 16, bot_y1 + 142), tw1, fill=ink, font=fonts["typewriter_small"])
    if tw2:
        draw.text((bot_x1 + 16, bot_y1 + 162), tw2, fill=ink, font=fonts["typewriter_small"])
    if tw3:
        draw.text((bot_x1 + 16, bot_y1 + 182), tw3, fill=ink, font=fonts["typewriter_small"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG", quality=95)
    logger.info(f"Scene Master Asset Sheet rendered to: {output_path}")
    return output_path


def render_multiscene_master_asset_sheet_png(
    scenes: List[Dict[str, Any]],
    output_path: Path,
    image_dir: Optional[Path] = None,
) -> Path:
    """Renders a combined 2-Scene Master Asset Sheet (matching scripts/create_multiscene_mastersheet.py)."""
    from PIL import Image, ImageDraw

    w, h = 1920, 1080
    bg_color = (235, 232, 224)
    ink = VOX_PALETTE["ink_black"]
    hot_red = VOX_PALETTE["hot_red"]
    cream_paper = VOX_PALETTE["cream_paper"]
    border_col = VOX_PALETTE["aged_border"]
    gray = VOX_PALETTE["halftone_gray"]
    fonts = _get_pil_fonts()

    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Top Header
    draw.rectangle([0, 0, w, 70], fill=ink)
    draw.text((40, 20), "VOX ENGINE V3: MULTI-SCENE MASTER ASSET SHEET (ACT I SEQUENCE)", fill="#FFFFFF", font=fonts["title"])
    draw.text((1200, 26), "SCENES: 2 // CAMERA: 100% LOCKED VIEWPORT // DIRECTION A+", fill=hot_red, font=fonts["label"], anchor="la")

    s1 = scenes[0] if len(scenes) > 0 else {}
    s2 = scenes[1] if len(scenes) > 1 else {}

    # Scene 1 & 2 Left Thumbnails (Result Scene Anchors)
    for s_idx, (sc, y_offset) in enumerate([(s1, 95), (s2, 575)]):
        sc_id = sc.get("scene_id", f"SCENE_{s_idx+1:02d}")
        sc_head = (sc.get("headline") or "FORENSIC FOCUS").upper()
        # Box
        draw.rectangle([40, y_offset, 850, y_offset + 460], fill="#FFFFFF", outline=ink, width=2)
        draw.rectangle([40, y_offset, 480, y_offset + 32], fill=ink)
        draw.text((48, y_offset + 7), f"{sc_id} RESULT: {sc_head[:28]}", fill="#FFFFFF", font=fonts["caption"])

        # Try to load image
        loaded = False
        if image_dir and image_dir.exists():
            for cn in [f"composite_{sc_id.lower()}.png", f"{sc_id.lower()}.png"]:
                cp = image_dir / cn
                if cp.exists():
                    try:
                        im = Image.open(cp).convert("RGB")
                        im = im.resize((790, 410), Image.Resampling.LANCZOS)
                        img.paste(im, (50, y_offset + 40))
                        loaded = True
                        break
                    except Exception as _cand_err:
                        logger.debug(f"Candidate image read bypass: {_cand_err}")
        if not loaded:
            draw.rectangle([50, y_offset + 40, 840, y_offset + 448], fill=(244, 241, 234), outline=gray, width=1)
            hero_str = sc.get("hero_cutout_object") or "Forensic Subject"
            draw.text((445, y_offset + 240), f"[{sc_id} ASSEMBLED ANCHOR: {hero_str[:24].upper()}]", fill=ink, font=fonts["label"], anchor="mm")

    # Right side: Decomposed Modular Asset Zoo
    rx1, ry1, rx2, ry2 = 880, 95, 1880, 1035
    draw.rectangle([rx1, ry1, rx2, ry2], fill=cream_paper, outline=(200, 190, 175), width=2)
    draw.text((910, 115), "MODULAR ASSET DECOMPOSITION ZOO (REMOTION & OMNI LAYERS)", fill=ink, font=fonts["label"])
    draw.text((910, 140), "All assets rendered as independent orthogonal layers with zero pre-baked overlap.", fill=gray, font=fonts["caption"])

    # Thumbnails of decomposed components (Stage, Hero, Stat, Tool)
    # Stage S1 & S2
    for s_idx, (sc, x1, x2) in enumerate([(s1, 910, 1140), (s2, 1170, 1400)]):
        sc_id = sc.get("scene_id", f"SCENE_{s_idx+1:02d}")
        draw.rectangle([x1, 170, x2, 290], fill="#FFFFFF", outline=gray, width=1)
        st_loaded = False
        if image_dir and image_dir.exists():
            for c_bg in [f"stage_{sc_id.lower()}.png", f"bg_{sc_id.lower()}.png", f"stage_{sc_id}.png"]:
                cp = image_dir / c_bg
                if cp.exists():
                    try:
                        st_im = Image.open(cp).convert("RGB")
                        bw, bh = x2 - x1 - 4, 116
                        st_im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
                        img.paste(st_im, (x1 + 2 + (bw - st_im.width)//2, 172 + (bh - st_im.height)//2))
                        st_loaded = True
                        break
                    except Exception as _cand_err:
                        logger.debug(f"Candidate image read bypass: {_cand_err}")
        if not st_loaded:
            draw.rectangle([x1 + 2, 172, x2 - 2, 288], fill=(244, 241, 234), outline=None)
            for gx in range(x1 + 10, x2 - 10, 20):
                draw.line([(gx, 172), (gx, 288)], fill=(228, 224, 214), width=1)
            draw.text(((x1 + x2)//2, 230), f"Stage {sc_id[-2:]} Desk Canvas", fill=ink, font=fonts["caption"], anchor="mm")
        draw.text((x1, 298), f"Stage {sc_id[-2:]} (#F4F1EA Desk)", fill=ink, font=fonts["caption"])

    # Stat Cards S1 & S2 (Stylized Remotion Vector Card)
    s1_stat = extract_stat_hero_from_text(s1.get("narration") or "") or "AUDIT DATA"
    s2_stat = extract_stat_hero_from_text(s2.get("narration") or "") or "9 RETAIL"
    for s_idx, (st_val, x1, x2) in enumerate([(s1_stat, 1430, 1640), (s2_stat, 1660, 1860)]):
        draw.rectangle([x1, 170, x2, 290], fill=(244, 241, 234), outline=border_col, width=2)
        draw.rectangle([x1, 170, x2, 198], fill=ink)
        draw.text(((x1 + x2)//2, 184), "STAT CHIP // IBM PLEX", fill="#FFFFFF", font=fonts["caption"], anchor="mm")
        draw.text(((x1 + x2)//2, 244), str(st_val)[:8], fill=hot_red, font=fonts["stat_medium"], anchor="mm")
        draw.text((x1, 298), f"Stat S{s_idx+1} Metric Card", fill=hot_red, font=fonts["caption"])

    # Hero Cutouts S1 & S2 (Real AI Cutout Images with Deckle Edge)
    h1_name = s1.get("hero_cutout_object") or "Subject S1"
    h2_name = s2.get("hero_cutout_object") or "Subject S2"
    for s_idx, (sc, h_name, x1, x2) in enumerate([(s1, h1_name, 910, 1140), (s2, h2_name, 1170, 1400)]):
        sc_id = sc.get("scene_id", f"SCENE_{s_idx+1:02d}")
        draw.rectangle([x1, 335, x2, 520], fill="#FFFFFF", outline=gray, width=1)
        h_loaded = False
        if image_dir and image_dir.exists():
            for c_h in [f"hero_{sc_id.lower()}.png", f"cutout_{sc_id.lower()}.png", f"hero_{sc_id}.png"]:
                cp = image_dir / c_h
                if cp.exists():
                    try:
                        h_im = Image.open(cp).convert("RGBA")
                        bw, bh = x2 - x1 - 6, 178
                        h_im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
                        px = x1 + 3 + (bw - h_im.width)//2
                        py = 338 + (bh - h_im.height)//2
                        img.paste(h_im, (px, py), h_im)
                        h_loaded = True
                        break
                    except Exception as _cand_err:
                        logger.debug(f"Candidate image read bypass: {_cand_err}")
        if not h_loaded:
            draw.text(((x1 + x2)//2, 420), f"[{h_name[:14].upper()}]", fill=ink, font=fonts["caption"], anchor="mm")
        draw.text((x1, 530), f"Hero S{s_idx+1}: {h_name[:20]}", fill=ink, font=fonts["caption"])

    # Tools / Connectors S1 & S2 (Real AI Tool / Prop Images)
    t1_name = s1.get("interacting_tool") or "Odometer Counter"
    t2_name = s2.get("interacting_tool") or "Directional Route Arrow"
    for s_idx, (sc, t_name, y1, y2) in enumerate([(s1, t1_name, 335, 420), (s2, t2_name, 455, 540)]):
        sc_id = sc.get("scene_id", f"SCENE_{s_idx+1:02d}")
        draw.rectangle([1430, y1, 1860, y2], fill="#FFFFFF", outline=gray, width=1)
        t_loaded = False
        if image_dir and image_dir.exists():
            for c_t in [f"tool_{sc_id.lower()}.png", f"prop_{sc_id.lower()}.png", f"tool_{sc_id}.png"]:
                cp = image_dir / c_t
                if cp.exists():
                    try:
                        t_im = Image.open(cp).convert("RGBA")
                        bw, bh = 424, y2 - y1 - 6
                        t_im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
                        px = 1433 + (bw - t_im.width)//2
                        py = y1 + 3 + (bh - t_im.height)//2
                        img.paste(t_im, (px, py), t_im)
                        t_loaded = True
                        break
                    except Exception as _cand_err:
                        logger.debug(f"Candidate image read bypass: {_cand_err}")
        if not t_loaded:
            draw.line([(1450, (y1 + y2)//2), (1840, (y1 + y2)//2)], fill=hot_red, width=3)
            draw.text((1645, (y1 + y2)//2 + 18), f"[{t_name[:28]}]", fill=ink, font=fonts["caption"], anchor="mm")
        draw.text((1430, y2 + 10), f"Tool S{s_idx+1}: {t_name[:36]}", fill=hot_red, font=fonts["caption"])

    # Bottom Continuity Rules Box
    draw.rectangle([910, 600, 1860, 1010], fill=(240, 237, 228), outline=hot_red, width=2)
    draw.text((930, 620), "MULTI-SCENE CONTINUITY RULES (VOX ENGINE V3 / DIRECTION A+):", fill=ink, font=fonts["label"])
    draw.text((930, 660), "1. Camera: Locked 1920x1080 computer screen frame (zero zoom, zero roll across scenes).", fill=hot_red, font=fonts["caption"])
    draw.text((930, 695), "2. Ingress: Subject layers enter at high speed from screen-right (<= 0.4s cubic-bezier).", fill=ink, font=fonts["caption"])
    draw.text((930, 730), "3. Connectors: S1 vector -> S2 evidence yarn mechanically lock causal claims across frames.", fill=ink, font=fonts["caption"])
    draw.text((930, 765), "4. Dead-Stop Hold: Rigid spatial anchor lock with continuous 12fps paper grain/shadow breathing.", fill=ink, font=fonts["caption"])
    draw.text((930, 800), "5. Whisper Sync: Remotion locks audio karaoke and subtitles with 0ms drift invariance.", fill=ink, font=fonts["caption"])
    draw.text((930, 835), "6. Omni Guard: Google Flow/Omni serves as pure texture engine (paper grain, CRT scanlines).", fill=hot_red, font=fonts["caption"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG", quality=95)
    logger.info(f"Multi-Scene Master Asset Sheet rendered to: {output_path}")
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
    master_sheet_cards_html = []
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

        # Master Asset Sheet Card for Tab 1 (Direction A+ / FT-201)
        decomp = sc.get("decomposed_prompts") or {}
        ms_p_file = f"master_asset_sheet_{sc_id.lower()}.png"
        tool_label = sc.get("interacting_tool") or "Forensic Instrument / Red Yarn"
        stat_label = stat_hero or "QUANTITATIVE METRIC"

        ms_card = f"""
        <div class="ms-card" id="ms_card_{sc_id.lower()}">
            <div class="ms-card-header">
                <span class="ms-tag">{sc_id} // {headline}</span>
                <span class="ms-dur">{dur:.1f}s</span>
            </div>
            <div class="ms-body-grid">
                <div class="ms-img-col">
                    <img src="{ms_p_file}" alt="{sc_id} Master Asset Sheet" class="ms-sheet-img" onerror="this.style.display='none'; this.parentElement.classList.add('ms-fallback');" />
                    <div class="ms-img-subtext">MASTER ASSET SHEET // ASSEMBLED ANCHOR + DECOMPOSED ZOO</div>
                </div>
                <div class="ms-layers-col">
                    <div class="ms-layer-card">
                        <div class="ms-layer-title">1. THE STAGE (BACKDROP CANVAS)</div>
                        <div class="ms-layer-spec">Fixed 1920x1080 Computer Frame Desk // #F4F1EA Aged Newsprint // 0% Alpha</div>
                        <pre class="ms-layer-prompt">{decomp.get('stage_backdrop_prompt', 'Clean aged archival newsprint diorama backdrop.')}</pre>
                    </div>
                    <div class="ms-layer-card">
                        <div class="ms-layer-title">2. HERO CUTOUT OBJECT: {hero}</div>
                        <div class="ms-layer-spec">60lpi Halftone B&W, 2-4px deckle edge // Solid #FFFFFF background for alpha extraction</div>
                        <pre class="ms-layer-prompt">{decomp.get('hero_cutout_prompt', f'Authentic Vox tactile paper cutout: {hero}')}</pre>
                    </div>
                    <div class="ms-layer-card">
                        <div class="ms-layer-title">3. STAT CARD HERO: {stat_label}</div>
                        <div class="ms-layer-spec">Giant bold red numeral on cream cardstock // Floating alpha layer</div>
                    </div>
                    <div class="ms-layer-card">
                        <div class="ms-layer-title">4. INTERACTING TOOL / CONNECTOR: {tool_label}</div>
                        <div class="ms-layer-spec">Mechanical prop / crimson yarn with brass pins // Solid #FFFFFF background</div>
                        <pre class="ms-layer-prompt">{decomp.get('interacting_tool_prompt', f'Authentic Vox tactile mechanical tool: {tool_label}')}</pre>
                    </div>
                    <div class="ms-layer-card ms-motion-card">
                        <div class="ms-layer-title" style="color: var(--hot-red);">5. RELATIONAL MOTION COUPLING (REMOTION CONTRACT)</div>
                        <p class="ms-motion-text">{decomp.get('relational_motion_mechanism', 'Unidirectional high-speed ingress on X-axis (<=0.4s, cubic-bezier): Hero locks, tool interacts, dead-stop hold with 12fps paper vibration.')}</p>
                    </div>
                </div>
            </div>
        </div>
        """
        master_sheet_cards_html.append(ms_card)

    all_scenes_joined = "\n".join(scene_cards_html)
    all_mastersheets_joined = "\n".join(master_sheet_cards_html)

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

        /* MASTER ASSET SHEETS STYLES */
        .multiscene-banner {{
            background: #FFFFFF;
            border: 2px solid var(--border-aged);
            padding: 16px;
            margin-bottom: 24px;
            border-radius: 4px;
            box-shadow: var(--card-shadow);
        }}
        .multiscene-banner h2 {{
            font-family: var(--font-headline);
            font-size: 1.4rem;
            color: var(--ink-black);
            margin-bottom: 4px;
        }}
        .multiscene-banner p {{
            font-size: 0.85rem;
            color: var(--halftone-gray);
            margin-bottom: 12px;
        }}
        .multiscene-banner-img {{
            width: 100%;
            border: 1px solid var(--border-aged);
            border-radius: 2px;
            display: block;
        }}
        .mastersheets-list {{
            display: flex;
            flex-direction: column;
            gap: 28px;
        }}
        .ms-card {{
            background: #FFFFFF;
            border: 2px solid var(--border-aged);
            border-radius: 4px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
        }}
        .ms-card-header {{
            background: var(--ink-black);
            color: #FFFFFF;
            padding: 10px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .ms-tag {{ font-family: var(--font-headline); font-size: 1.15rem; }}
        .ms-dur {{ color: var(--hot-red); font-weight: bold; font-size: 1rem; }}
        .ms-body-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 18px;
            background: #FAF8F5;
        }}
        @media (max-width: 1200px) {{
            .ms-body-grid {{ grid-template-columns: 1fr; }}
        }}
        .ms-img-col {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .ms-sheet-img {{
            width: 100%;
            border: 1px solid var(--border-aged);
            border-radius: 2px;
            background: #EFE9DA;
        }}
        .ms-img-subtext {{
            font-size: 0.75rem;
            color: var(--halftone-gray);
            font-weight: bold;
            text-align: center;
        }}
        .ms-layers-col {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .ms-layer-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 3px solid var(--ink-black);
            padding: 10px 12px;
            border-radius: 2px;
        }}
        .ms-motion-card {{ border-left-color: var(--hot-red); background: #FFFDF9; }}
        .ms-layer-title {{ font-weight: bold; font-size: 0.88rem; color: var(--ink-black); margin-bottom: 2px; }}
        .ms-layer-spec {{ font-size: 0.78rem; color: var(--halftone-gray); margin-bottom: 6px; }}
        .ms-layer-prompt {{
            font-family: var(--font-typewriter);
            font-size: 0.74rem;
            color: #1E293B;
            background: #F1F5F9;
            padding: 6px 8px;
            border-radius: 2px;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 80px;
            overflow-y: auto;
        }}
        .ms-motion-text {{
            font-family: var(--font-sans);
            font-size: 0.82rem;
            color: #334155;
            line-height: 1.4;
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
        <button class="tab-btn active" onclick="switchTab('tab-mastersheets')">1. MASTER ASSET SHEETS ({total_scenes})</button>
        <button class="tab-btn" onclick="switchTab('tab-storyboard')">2. FULL STORYBOARD CONTACT SHEET</button>
        <button class="tab-btn" onclick="switchTab('tab-system')">3. MASTER VISUAL SYSTEM & TOKENS</button>
    </div>

    <!-- TAB 1: MASTER ASSET SHEETS (DIRECTION A+) -->
    <div id="tab-mastersheets" class="tab-panel active">
        <div class="multiscene-banner">
            <h2>MULTI-SCENE MASTER ASSET SHEET (ACT I SEQUENCE // DIRECTION A+)</h2>
            <p>Left: Result Scene Anchor (Phối cảnh kết quả hoàn thiện) // Right: Modular Asset Decomposition Zoo (Linh kiện phân rã độc lập) // Bottom: Motion Coupling</p>
            <img src="master_sheet_multiscene.png" alt="Multi-Scene Master Asset Sheet" class="multiscene-banner-img" onerror="this.style.display='none';" />
        </div>
        <div class="mastersheets-list">
            {all_mastersheets_joined}
        </div>
    </div>

    <!-- TAB 2: PER-SCENE STORYBOARDS -->
    <div id="tab-storyboard" class="tab-panel">
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
    ctx: Any = None,
    scenes: Optional[List[Dict[str, Any]]] = None,
    payload: Optional[Dict[str, Any]] = None,
    image_mode: bool = False,
    **kwargs: Any,
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

    if ctx is None and "episode_id" in kwargs:
        ctx = kwargs["episode_id"]

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

    if scenes is None:
        dp_path = kwargs.get("director_plan_path") or (ctx.paths.root / "director_plan.json")
        if dp_path and Path(dp_path).exists():
            try:
                plan_data = json.loads(Path(dp_path).read_text(encoding="utf-8"))
                scenes = plan_data.get("scenes") or plan_data.get("shots") or []
                if not payload:
                    payload = plan_data
            except Exception as _e:
                logger.warning(f"Failed to load director_plan from {dp_path}: {_e}")
                scenes = []
        else:
            scenes = []

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

    # 2b. Multi-Scene Master Asset Sheet (matching scripts/create_multiscene_mastersheet.py)
    multiscene_png = out_dir / "master_sheet_multiscene.png"
    try:
        render_multiscene_master_asset_sheet_png(
            scenes=scenes[:2] if len(scenes) >= 2 else scenes,
            output_path=multiscene_png,
            image_dir=seeds_dir,
        )
    except Exception as _ms_err:
        logger.warning(f"Failed to render master_sheet_multiscene.png: {_ms_err}")
        multiscene_png = None

    # 2c. Per-Scene Master Asset Sheets (FT-201 / Direction A+)
    per_scene_master_sheets: Dict[str, str] = {}
    for sc in scenes:
        sc_id = sc.get("scene_id", "SCENE_01")
        sc_png = out_dir / f"master_asset_sheet_{sc_id.lower()}.png"
        try:
            render_scene_master_asset_sheet_png(
                scene=sc,
                output_path=sc_png,
                image_dir=seeds_dir,
                market=market,
            )
            per_scene_master_sheets[sc_id] = str(sc_png)
        except Exception as _p_err:
            logger.warning(f"Failed to render master sheet for {sc_id}: {_p_err}")

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
    decomposed_roster: Dict[str, Dict[str, Any]] = {}
    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", f"SCENE_{idx+1:02d}")
        stat_heroes_summary[sc_id] = extract_stat_hero_from_text(sc.get("narration") or "")
        decomposed_roster[sc_id] = {
            "hero_cutout_object": sc.get("hero_cutout_object"),
            "interacting_tool": sc.get("interacting_tool"),
            "decomposed_prompts": sc.get("decomposed_prompts") or {},
        }
    stat_heroes_count = sum(1 for v in stat_heroes_summary.values() if v is not None)

    # Build 6-in-1 MasterSheetAssetBundle for every scene (FT-201)
    candidate_dirs = search_dirs
    master_sheet_bundles = {}
    for sc in scenes:
        sc_id = sc.get("scene_id", "SCENE_01")
        decomp = sc.get("decomposed_prompts") or {}
        h_obj = sc.get("hero_cutout_object") or "Archival Hero Subject"
        t_obj = sc.get("interacting_tool") or "Forensic Brass Caliper / Red Evidence Yarn"
        narr = sc.get("narration") or ""
        stat_hero = extract_stat_hero_from_text(narr) or "AUDIT DATA"
        headline = sc.get("headline") or "FORENSIC FOCUS"

        resolved_anchor = ""
        resolved_hero = ""
        resolved_tool = ""
        resolved_stage = ""

        if effective_image_mode and candidate_dirs:
            for cdir in candidate_dirs:
                if not cdir.exists():
                    continue
                for f_name in [f"composite_{sc_id.lower()}.png", f"{sc_id.lower()}.png"]:
                    if (cdir / f_name).exists():
                        resolved_anchor = str((cdir / f_name).resolve())
                        break
                for f_name in [f"hero_{sc_id.lower()}.png", f"cutout_{sc_id.lower()}.png"]:
                    if (cdir / f_name).exists():
                        resolved_hero = str((cdir / f_name).resolve())
                        break
                for f_name in [f"tool_{sc_id.lower()}.png", f"prop_{sc_id.lower()}.png"]:
                    if (cdir / f_name).exists():
                        resolved_tool = str((cdir / f_name).resolve())
                        break
                for f_name in [f"stage_{sc_id.lower()}.png", f"bg_{sc_id.lower()}.png"]:
                    if (cdir / f_name).exists():
                        resolved_stage = str((cdir / f_name).resolve())
                        break

        tx_prompt = decomp.get("relational_motion_mechanism") or sc.get("universal_video_prompt") or f"[{h_obj}] + couples with + [{t_obj}], leaving permanent physical residue with 12fps paper vibration."

        bundle_dict = generate_master_sheet_bundle(
            scene_id=sc_id,
            assembled_anchor_url=resolved_anchor or f"composite_seeds/composite_{sc_id.lower()}.png",
            hero_cutout_url=resolved_hero or f"composite_seeds/hero_{sc_id.lower()}.png",
            interacting_tool_url=resolved_tool or f"composite_seeds/tool_{sc_id.lower()}.png",
            stage_backdrop_url=resolved_stage or f"composite_seeds/stage_{sc_id.lower()}.png",
            stat_card_url=f"remotion/stat_card_{sc_id.lower()}.png",
            connector_url=f"remotion/connector_{sc_id.lower()}.png",
            information_spec={
                "headline": headline,
                "stat_hero": stat_hero,
                "stat_label": "QUANTITATIVE EVIDENCE",
                "narration": narr
            },
            transaction_prompt=tx_prompt,
            wiring_spec={
                "connector_type": "red_yarn" if "yarn" in t_obj.lower() else ("brass_caliper" if "caliper" in t_obj.lower() else "turned_wood_seal"),
                "source_anchor": [450, 420],
                "target_anchor": [1450, 240],
                "ingress_axis": "X",
                "ingress_duration_sec": 0.3,
                "hold_fps": 12,
                "snappy_physics": True
            },
            camera_movement="locked"
        )
        master_sheet_bundles[sc_id] = bundle_dict

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
        "decomposed_roster": decomposed_roster,
        "master_sheet_bundles": master_sheet_bundles,
        "files": {
            "master_sheet_system_png": str(sys_png) if sys_png and sys_png.exists() else None,
            "master_sheet_scenes_png": str(scenes_png) if scenes_png and scenes_png.exists() else None,
            "master_sheet_multiscene_png": str(multiscene_png) if multiscene_png and multiscene_png.exists() else None,
            "per_scene_master_sheets": per_scene_master_sheets,
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


from pydantic import BaseModel, Field, ValidationError


class WiringSpec(BaseModel):
    """Khế ước cách đấu nối không gian & động học giữa các object (FT-201)."""
    connector_type: str = Field(default="red_yarn", description="Loại đấu nối: red_yarn, brass_caliper, turned_wood_seal, index_arrow")
    source_anchor: List[int] = Field(default_factory=lambda: [450, 420], description="Tọa độ điểm neo nguồn [x, y]")
    target_anchor: List[int] = Field(default_factory=lambda: [1450, 240], description="Tọa độ điểm neo đích [x, y]")
    ingress_axis: str = Field(default="X", description="Trục chuyển động vào (X đơn hướng)")
    ingress_duration_sec: float = Field(default=0.3, le=0.4, description="Thời gian bứt tốc vào sân khấu (<= 0.4s)")
    hold_fps: int = Field(default=12, description="Tốc độ vi rung nhịp thở stop-motion (12fps on twos)")
    snappy_physics: bool = Field(default=True, description="Khóa cứng gia tốc stop-motion giật dứt khoát")


class InformationSpec(BaseModel):
    """Khế ước thông tin nội dung & dữ liệu định lượng (FT-201)."""
    headline: str = Field(default="", description="Tiêu đề phân cảnh điều tra")
    stat_hero: str = Field(default="", description="Con số định lượng khổng lồ màu đỏ")
    stat_label: str = Field(default="", description="Nhãn định danh con số định lượng")
    narration: str = Field(default="", description="Toàn văn lời đọc voiceover")


class MasterSheetAssetBundle(BaseModel):
    """Khế ước Bộ linh kiện Master Sheet toàn diện 6-trong-1 (FT-201).
    
    Bắt buộc đủ 6 khối:
    1. Assembled Anchor (Image Result mong muốn)
    2. Hero Cutout (Object chủ thể)
    3. Interacting Tool (Object tương tác)
    4. Information Spec (Thông tin định lượng)
    5. Transaction Prompt (Prompt tương tác xúc giác Omni/Veo)
    6. Wiring Spec (Cách đấu nối không gian & động học)
    """
    scene_id: str = Field(..., pattern=r"^SCENE_\d{2}$")
    assembled_anchor_url: str = Field(..., description="1. Image Result mong muốn: Ảnh kết quả tổng thành 2560x1440")
    hero_cutout_url: str = Field(..., description="2. Object Chủ thể: Ảnh tài liệu/nhân vật trên nền trắng #FFFFFF có Alpha")
    interacting_tool_url: str = Field(..., description="3. Object Tương tác: Ảnh thước kẹp/con dấu/chỉ đỏ trên nền trắng #FFFFFF có Alpha")
    stage_backdrop_url: str = Field(default="", description="Ảnh nền sân khấu bàn làm việc (#F4F1EA)")
    stat_card_url: str = Field(default="", description="Ảnh thẻ số liệu đỏ (#D62E1F) hoặc vector chip")
    connector_url: str = Field(default="", description="Ảnh hoặc vector sợi chỉ đỏ / thước kẹp kết nối")
    information_spec: InformationSpec = Field(..., description="4. Thông tin: Headline, stat hero, narration")
    transaction_prompt: str = Field(..., description="5. Transaction Prompt: Prompt tương tác cơ học xúc giác cho Omni/Veo plate")
    wiring_spec: WiringSpec = Field(..., description="6. Cách đấu nối: Tọa độ điểm neo source/target, loại connector, ingress <= 0.4s")
    ingress_direction: str = Field(default="screen_right_to_left", description="Hướng trượt vào duy nhất")
    ingress_duration_sec: float = Field(default=0.3, le=0.4, description="Thời gian bứt tốc vào sân khấu (<= 0.4s)")
    camera_movement: str = Field(default="locked", description="Khóa cứng khung máy tính 1920x1080, cấm zoom/pan")
    dynamic_manifest: Optional[Dict[str, Any]] = Field(default=None, description="Bespoke Opus 5.5 Art Director Manifest")


def generate_master_sheet_bundle(
    scene_id: str,
    assembled_anchor_url: str = "",
    hero_cutout_url: str = "",
    interacting_tool_url: str = "",
    information_spec: Optional[Dict[str, Any]] = None,
    transaction_prompt: str = "",
    wiring_spec: Optional[Dict[str, Any]] = None,
    stage_backdrop_url: str = "",
    stat_card_url: str = "",
    connector_url: str = "",
    ingress_direction: str = "screen_right_to_left",
    ingress_duration_sec: float = 0.3,
    camera_movement: str = "locked",
    dynamic_manifest: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generates a canonical MasterSheetAssetBundle (FT-201) dict for Remotion/Pipeline consumption.

    Enforces 6-in-1 complete Master Sheet specification (Result, Hero, Tool, Info, Transaction Prompt, Wiring Spec).
    Supports dynamic manifest injection from Opus 5.5 Art Director (FT-206) to eliminate hardcoding.
    Invariants (01_CONTRACTS.md):
    - camera_movement MUST be 'locked' (zero zoom, zero pan).
    - ingress_duration_sec <= 0.4s (snappy stop-motion).
    - ingress_direction is unidirectional (default 'screen_right_to_left').
    """
    manifest_dict: Optional[Dict[str, Any]] = None
    if dynamic_manifest is not None:
        if hasattr(dynamic_manifest, "model_dump"):
            manifest_dict = dynamic_manifest.model_dump()
        elif hasattr(dynamic_manifest, "dict"):
            manifest_dict = dynamic_manifest.dict()
        elif isinstance(dynamic_manifest, dict):
            manifest_dict = dynamic_manifest

    if manifest_dict:
        if not transaction_prompt:
            transaction_prompt = manifest_dict.get("assembled_keyframe_prompt", "")
        if ingress_duration_sec == 0.3 and "ingress_duration_sec" in manifest_dict:
            ingress_duration_sec = float(manifest_dict["ingress_duration_sec"])

    if ingress_duration_sec > 0.4:
        raise ValueError(f"ingress_duration_sec ({ingress_duration_sec}) must be <= 0.4s per Rule 140 / FT-201")
    if camera_movement != "locked":
        raise ValueError(f"camera_movement ('{camera_movement}') must be 'locked' per Vox Style Invariant / FT-201")

    info_obj = InformationSpec(**(information_spec or {
        "headline": "FORENSIC FOCUS",
        "stat_hero": "AUDIT DATA",
        "stat_label": "VERIFIED METRIC",
        "narration": "Documentary investigation."
    }))

    # Dynamic Wiring Spec based on manifest contact point
    final_wiring_dict = dict(wiring_spec or {})
    if manifest_dict and "contact_point" in manifest_dict:
        cp = manifest_dict["contact_point"]
        anchor_type = cp.get("anchor_type", "corner_pin")
        host_area = cp.get("host_target_area", "document_face")
        
        # Calculate dynamic non-hardcoded coordinates based on target zone
        area_coords = {
            "top_right_corner": ([520, 480], [1480, 260]),
            "left_margin": ([380, 520], [1380, 520]),
            "paragraph_body": ([460, 420], [1420, 460]),
            "bottom_seal_zone": ([500, 560], [1460, 780]),
            "document_face": ([450, 450], [1450, 450]),
        }
        src_coord, tgt_coord = area_coords.get(host_area, ([480, 450], [1440, 450]))
        
        if "connector_type" not in final_wiring_dict:
            final_wiring_dict["connector_type"] = anchor_type
        if "source_anchor" not in final_wiring_dict:
            final_wiring_dict["source_anchor"] = src_coord
        if "target_anchor" not in final_wiring_dict:
            final_wiring_dict["target_anchor"] = tgt_coord

    wiring_obj = WiringSpec(**(final_wiring_dict or {
        "connector_type": "red_yarn",
        "source_anchor": [450, 420],
        "target_anchor": [1450, 240],
        "ingress_axis": "X",
        "ingress_duration_sec": ingress_duration_sec,
        "hold_fps": 12,
        "snappy_physics": True
    }))

    bundle = MasterSheetAssetBundle(
        scene_id=scene_id,
        assembled_anchor_url=assembled_anchor_url or "images/assembled_anchor.png",
        hero_cutout_url=hero_cutout_url or "images/hero_cutout.png",
        interacting_tool_url=interacting_tool_url or "images/tool_prop.png",
        stage_backdrop_url=stage_backdrop_url or "images/stage_backdrop.png",
        stat_card_url=stat_card_url or "images/stat_card.png",
        connector_url=connector_url or "images/connector_prop.png",
        information_spec=info_obj,
        transaction_prompt=transaction_prompt or "Authentic tactile paper interaction plate with locked camera",
        wiring_spec=wiring_obj,
        ingress_direction=ingress_direction,
        ingress_duration_sec=ingress_duration_sec,
        camera_movement=camera_movement,
        dynamic_manifest=manifest_dict,
    )

    return bundle.model_dump() if hasattr(bundle, "model_dump") else bundle.dict()


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
