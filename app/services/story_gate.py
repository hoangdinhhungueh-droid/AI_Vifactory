"""Story Brain gate (outline stage) - measurable 12/12 check (v4), no network.

v4 upgrade 07/08/2026 per Phase 3 (Hand-off Viec 2 checklist A+B code-hoa):
v3's nine rules PLUS three new checks:
    10_banned_phrases   - expanded anti-AI-tone banned-phrase list (checklist A)
    11_according_to_cap - max 2 paragraphs opening with "According to X..." (checklist A)
    12_pattern_interrupt - at least 1 short sentence (<=6 words) in Mechanism (checklist B)

v3 upgrade 05/08/2026 per Hand-off Viec 2 decision: v2's six rules PLUS
narrative-arc and segmentation checks (ported from scripts/story_gate_v3.py)
now run inline at S3.6, so a flat wall of text with no dramatic structure can
no longer score max on the deterministic gate. Added after EP004 feedback:
"chua co hook, cac hoi ... khong phan biet duoc doan nao ra doan nao".

New checks vs v2:
    7_arc_five_acts  - the five acts (hook-shock / build / knot / resolution /
                       denouement) must each show their own cue vocabulary in
                       the correct fifth of the script.
    8_segmentation   - the story must be broken into paragraphs of a readable
                       size, so S2 can map beat -> scene cleanly.
    9_hook_shock     - the opening must land a concrete shock (number or
                       superlative) within the first 60 words, not just a
                       question.

Public API:
    score_story(story_text) -> dict with checks/score/max_score/verdict/fixes
    gate_mode() -> "off" | "warn" | "block"   (env VF_STORY_GATE)
"""
from __future__ import annotations

import math
import os
import re

WPM = 152.0

LOOP_OPEN = [
    r"\?",
    r"(?i)\bbut (?:nobody|no one|almost no one|what)\b",
    r"(?i)\bwhat (?:nobody|no one|almost nobody) (?:knew|saw|noticed)\b",
    r"(?i)\bthat number would\b",
    r"(?i)\bnot yet\b",
    r"(?i)\bkeep that (?:number|figure|date) in mind\b",
    r"(?i)\bwe will come back to\b",
    r"(?i)\bfor now\b",
]
LOOP_CLOSE = [
    r"(?i)\bthat is (?:why|how|when)\b",
    r"(?i)\bwhich is (?:why|how)\b",
    r"(?i)\bhere is (?:why|what happened|the answer)\b",
    r"(?i)\bremember (?:that|the)\b",
    r"(?i)\bthe answer\b",
    r"(?i)\bso when\b",
    r"(?i)\bin the end\b",
]
SOURCE = [
    r"(?i)according to",
    r"(?i)\bfiling\b",
    r"(?i)\breport(?:ed|s)?\b",
    r"(?i)\bbalance sheet\b",
    r"(?i)\bexaminer\b",
    r"(?i)\bcourt\b",
    r"(?i)\btestimony\b",
]
NUM = r"(?:\$\s?\d[\d,\.]*\s?(?:billion|million|trillion|B|M|T)?|\b\d[\d,\.]*\s?(?:%|percent|billion|million|trillion|years|employees|days)\b|\b(?:1[89]|20)\d{2}\b)"

# --- act cue vocabularies (v3: each act must speak its own language) --------
ACT_CUES = {
    "act1_hook_shock": [
        r"(?i)\b(?:vanish|disappear|collapse[sd]?|gone|wiped out|shock|nobody|no one)\b",
        r"(?i)\b(?:largest|biggest|worst|first|only|never)\b",
        r"\?",
    ],
    "act2_build": [
        r"(?i)\b(?:founded|opened|grew|expanded|built|became|launched|rose|boom(?:ed|ing)?|empire)\b",
        r"(?i)\b(?:by \d{4}|store[s]?|market share|dominat(?:ed|ing))\b",
    ],
    "act3_knot": [
        r"(?i)\b(?:but|however|then|instead|trap|debt|leverage[d]?|loan[s]?|interest|deal|buyout|pressure)\b",
        r"(?i)\b(?:began to|started to|could not|couldn't|no longer)\b",
    ],
    "act4_resolution": [
        r"(?i)\b(?:filed|bankrupt(?:cy)?|chapter 11|liquidat(?:e|ed|ion)|clos(?:ed|ing)|shut|court|creditors?|failed)\b",
    ],
    "act5_denouement": [
        r"(?i)\b(?:today|years later|since then|legacy|remains?|lesson|aftermath|what happened to|left behind|still)\b",
    ],
}
ACT_ORDER = ["act1_hook_shock", "act2_build", "act3_knot",
             "act4_resolution", "act5_denouement"]

SHOCK = r"(?:\$\s?\d[\d,\.]*\s?(?:billion|million|trillion)|\b\d[\d,\.]*\s?(?:%|percent)|\b(?:largest|biggest|worst|never|nobody|no one)\b)"

MAX_PARA_WORDS = 160
MIN_PARAS = 8

# --- Checklist A: anti-AI-tone banned phrases (v4) ---------------------------
BANNED_PHRASES_GATE = [
    r"(?i)\blet'?s dive in\b",
    r"(?i)\bit'?s worth noting\b",
    r"(?i)\bunleash(?:d|es|ing)?\b",
    r"(?i)\bboundless\b",
    r"(?i)\bat the end of the day\b",
    r"(?i)\blittle did they know\b",
    r"(?i)\bthe truth is\b",
    r"(?i)\bunravel(?:ed|ing|s)?\b",
    r"(?i)\bunderscore(?:d|s|ing)?\b",
]

# --- Checklist A: "According to X..." opener cap (v4) ------------------------
ACCORDING_TO_RE = re.compile(r"(?im)^\s*according to\b")
MAX_ACCORDING_TO = 2

# --- Checklist B: pattern interrupt — short sentence in Mechanism (v4) -------
PATTERN_INTERRUPT_MAX_WORDS = 6


def _count(pats, text):
    return sum(len(re.findall(p, text)) for p in pats)


def _words(text):
    return text.split()


def gate_mode() -> str:
    v = (os.getenv("VF_STORY_GATE", "block") or "block").strip().lower()  # default flipped 27/07/2026: pm2 does not carry launch env
    return v if v in ("off", "warn", "block") else "warn"


def score_story(story_text: str) -> dict:
    story = story_text or ""
    words = _words(story)
    nwords = len(words)
    minutes = nwords / WPM if nwords else 0.0
    sents = [s for s in re.split(r"(?<=[.!?])\s+", story) if s.strip()]
    hook = " ".join(sents[:4])
    first60 = " ".join(words[:60])

    nums = re.findall(NUM, story)
    loops_open = _count(LOOP_OPEN, story)
    loops_close = _count(LOOP_CLOSE, story)
    sources = _count(SOURCE, story)
    need_loops = max(1, math.ceil(minutes / 1.5)) if minutes else 1
    need_nums = max(1, math.ceil(minutes * 60 / 90)) if minutes else 1

    # --- arc (v3): split into five equal-word fifths, score each act's own cues
    fifth = max(1, nwords // 5)
    segments = [" ".join(words[i * fifth:(i + 1) * fifth]) for i in range(5)]
    if nwords > fifth * 5:
        segments[4] += " " + " ".join(words[fifth * 5:])
    arc_hits = {}
    for i, act in enumerate(ACT_ORDER):
        arc_hits[act] = _count(ACT_CUES[act], segments[i]) if i < len(segments) else 0
    acts_present = sum(1 for v in arc_hits.values() if v >= 2)

    # --- segmentation (v3) ----------------------------------------------------
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", story) if p.strip()]
    para_words = [len(_words(p)) for p in paras]
    oversized = [w for w in para_words if w > MAX_PARA_WORDS]
    longest_para = max(para_words) if para_words else nwords

    # --- Checklist A: anti-AI-tone (v4) ---------------------------------------
    banned_hits = []
    for pat in BANNED_PHRASES_GATE:
        m = re.search(pat, story)
        if m:
            banned_hits.append(m.group(0))
    according_to_count = len(ACCORDING_TO_RE.findall(story))

    # --- Checklist B: pattern interrupt (v4) ----------------------------------
    # Mechanism = 25%-70% of the script (Hoi 2)
    mech_start = int(nwords * 0.25)
    mech_end = int(nwords * 0.70)
    if mech_end > mech_start:
        mechanism_text = " ".join(words[mech_start:mech_end])
    else:
        mechanism_text = story
    mech_sents = [s for s in re.split(r"(?<=[.!?])\s+", mechanism_text) if s.strip()]
    short_sents = [s for s in mech_sents if 2 <= len(_words(s)) <= PATTERN_INTERRUPT_MAX_WORDS]

    checks = {
        "1_length_1200_1900_words": 1200 <= nwords <= 1900,
        "2_hook_has_open_question": bool(re.search(r"\?", hook)) or _count(LOOP_OPEN[1:], hook) > 0,
        "3_open_loops_enough": loops_open >= need_loops,
        "4_loops_closed": loops_close >= max(1, math.ceil(need_loops * 0.6)),
        "5_sourced_numbers": len(nums) >= need_nums and sources >= 2,
        "6_pace_in_band": 1200 <= nwords <= 1900,
        "7_arc_five_acts": acts_present == 5,
        "8_segmentation": len(paras) >= MIN_PARAS and not oversized,
        "9_hook_shock_in_first_60w": bool(re.search(SHOCK, first60)),
        "10_banned_phrases": len(banned_hits) == 0,
        "11_according_to_cap": according_to_count <= MAX_ACCORDING_TO,
        "12_pattern_interrupt": len(short_sents) >= 1,
    }
    failed = [k for k, v in checks.items() if not v]
    fixes = {
        "1_length_1200_1900_words": "Rewrite outline to land 1200-1900 words (8-12 min at 152 wpm).",
        "2_hook_has_open_question": "Open with an unanswered question in the first 15 seconds.",
        "3_open_loops_enough": "Plant one open loop every 60-90s (LOOP_OPEN vocabulary).",
        "4_loops_closed": "Every loop opened must be paid off (LOOP_CLOSE vocabulary).",
        "5_sourced_numbers": "At least one sourced number per 90s and >=2 named sources.",
        "6_pace_in_band": "Adjust script length so pace stays in the 145-160 wpm band.",
        "7_arc_five_acts": "Each fifth of the script must speak its own act's vocabulary (hook-shock/build/knot/resolution/denouement) at least twice.",
        "8_segmentation": "Break into >= " + str(MIN_PARAS) + " paragraphs, none longer than " + str(MAX_PARA_WORDS) + " words, so S2 can map beat to scene.",
        "9_hook_shock_in_first_60w": "Land a concrete shock (a number, %, or superlative) within the first 60 words.",
        "10_banned_phrases": "Remove banned AI-cliche phrases: " + ", ".join(banned_hits) if banned_hits else "No banned phrases found.",
        "11_according_to_cap": "Limit 'According to X...' openers to <= " + str(MAX_ACCORDING_TO) + " paragraphs (found " + str(according_to_count) + ").",
        "12_pattern_interrupt": "Add at least 1 very short sentence (<= " + str(PATTERN_INTERRUPT_MAX_WORDS) + " words) in the Mechanism section (25%-70%) to break rhythm.",
    }
    score = sum(1 for v in checks.values() if v)
    max_score = len(checks)
    return {
        "words": nwords,
        "est_minutes": round(minutes, 2),
        "paragraphs": len(paras),
        "longest_paragraph_words": longest_para,
        "oversized_paragraphs": len(oversized),
        "numbers_found": len(nums),
        "numbers_required": need_nums,
        "open_loop_markers": loops_open,
        "open_loops_required": need_loops,
        "close_markers": loops_close,
        "source_markers": sources,
        "arc_hits_per_act": arc_hits,
        "acts_present": acts_present,
        "hook_preview": hook[:220],
        "banned_phrases_found": banned_hits,
        "according_to_count": according_to_count,
        "pattern_interrupt_short_sents": len(short_sents),
        "checks": checks,
        "failed": failed,
        "fix_hints": [fixes[k] for k in failed],
        "score": score,
        "max_score": max_score,
        "verdict": "PASS" if score == max_score else "FAIL",
    }
