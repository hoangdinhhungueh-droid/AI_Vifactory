#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/vox_automated_director.py
Unified Autonomous Vox Director Engine (Rule 118, 120, 128, 132 Compliant).

Automates all 10 States from VOX ANIMATIONS - WOWZ.CLOUD.docx:
- State 0: Grounding Material resolution
- State 1: Niche classification
- State 2: High-viability Hook generation
- State 3: Word budgeting (2.5 words/sec)
- State 4: Fern-style Continuous Script generation
- State 5: Audio Spine (Edge-TTS + Whisper karaoke timestamps)
- State 6: Beat breakdown (2-3s beats, 2 shots/beat: Wide + Detail)
- State 7: Image Prompts (5-part prompt, 70% Hero + supporting cutouts)
- State 8: Universal Motion Manifest for Remotion VoxBuildOnStage
- State 9: High-CTR Thumbnail Prompts (Censor bar, 1-3 words all-caps)
"""

from __future__ import annotations

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from app.services.skill_loader import (
    get_vox_docudrama_prompt,
    resolve_vox_theme_by_keywords
)
from app.services.unified_vox_director import extract_dynamic_visual_roster
from app.services.prompt_forge import _sanitize_foreground_prompt, _sanitize_background_prompt
from app.services.representation_shield import shield_visual_roster

logger = logging.getLogger("vf.vox_automated_director")

# Canonical Raw Materials Library for High-Tier Director LLM
VOX_PAPER_MATERIALS_LIBRARY: Dict[str, Dict[str, Any]] = {
    "aged_newsprint": {
        "id": "aged_newsprint",
        "label": "Aged Yellowed Newsprint",
        "description": "Aged yellowed newsprint with visible wood pulp fiber and faint print bleed",
        "hex": "#e8e0cc",
        "tactile_props": ["newspaper clipping", "caption strip", "censor bar"]
    },
    "bleached_newsprint": {
        "id": "bleached_newsprint",
        "label": "Bleached Archival Newsprint",
        "description": "Crisp desaturated bleached newsprint with halftone grain and clean margins",
        "hex": "#f4f1ea",
        "tactile_props": ["typewriter memo", "tabular record"]
    },
    "manila_docket": {
        "id": "manila_docket",
        "label": "Manila Archival Docket Cardstock",
        "description": "Heavy fibrous manila paper with worn tab corners and subtle coffee-ring aging",
        "hex": "#dfd2b5",
        "tactile_props": ["official docket", "evidence envelope", "tabbed folder"]
    },
    "vintage_kraft": {
        "id": "vintage_kraft",
        "label": "Heavy Brown Kraft Stock",
        "description": "Rough brown kraft wrapping paper with coarse fiber speckles and scissor-cut edges",
        "hex": "#c8b293",
        "tactile_props": ["evidence parcel", "postal tag", "shipping label"]
    },
    "vellum_tracing": {
        "id": "vellum_tracing",
        "label": "Architectural Vellum Tracing Sheet",
        "description": "Semi-translucent drafting vellum with faint grid overlay and blueprint registration marks",
        "hex": "#eeebe3",
        "tactile_props": ["technical schematic", "cadastral overlay", "flowchart"]
    },
    "cotton_parchment": {
        "id": "cotton_parchment",
        "label": "Historical Cotton-Rag Parchment",
        "description": "Textured cotton-rag parchment with hand-deckled torn borders and dried ink mottling",
        "hex": "#ebe3cf",
        "tactile_props": ["treaty page", "historical deed", "notarial ledger"]
    }
}

# Canonical Paper Diorama 3 Style Blocks (CL3 Vox Videos System)
DIORAMA_STYLE_BLOCKS: Dict[str, str] = {
    "FLAT_PARALLAX": (
        "Use the attached style sheet as the strict visual system — match its aged-newsprint collage surface, "
        "desaturated archival palette with one hot accent, condensed headline caps with giant stat numbers, "
        "halftone black-and-white cutout people with rough white keylines and offset accent strokes, and its print-grain finish. "
        "Do NOT copy the sheet's layout; it defines the language, not the composition. Layers sit at distinct depths like a paper diorama — "
        "true parallax, never glossy 3D. Backgrounds are muted archival fields, varying per clip within this palette. "
        "ALERT WASH means the whole frame floods toward the hot accent tone. Motion: spring pop-ups with overshoot, staggered entrances, "
        "ticking counters, underline swipes; one slow camera move per clip. Audio: sound design only — paper pops, thwips, stamps, ticks, "
        "low newsroom hum. No music. No voice-over."
    ),
    "DEEP_DIORAMA": (
        "Use the attached style sheet for materials only — aged-print collage textures, halftone black-and-white cutout people "
        "with rough keylines and offset accent strokes, giant stat numbers, print grain. Do NOT copy the sheet's layout or its flatness: "
        "every clip is a deep 3D paper diorama — cutouts are physical layers separated in real space, strong shallow depth of field, "
        "foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, dives, whips, racks focus — "
        "one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's palette. "
        "ALERT WASH means the entire frame floods to the hot accent tone in one beat. Motion: springs with overshoot, staggered entrances, "
        "ticking counters. Audio: sound design only — paper pops, whooshes, stamps, ticks. No music. No voice-over."
    ),
    "LOCKED_STAGE": (
        "Documentary cutout-collage stage: a locked, muted archival map/texture background that never changes. "
        "Midground: black-and-white halftone cutouts with a rough white keyline and an offset red marker stroke behind each. "
        "Foreground: structures, props, and big stat numbers in full color. Condensed bold headline caps; numbers rendered huge, as characters. "
        "Desaturated palette plus one hot red accent, secondary mustard. Spring pop-ups with slight overshoot, staggered entrances, "
        "counters ticking up, red underline swipes. Camera: subtle slow drift only, never cuts."
    )
}

DIORAMA_AVOID_BLOCKS: Dict[str, str] = {
    "FLAT_PARALLAX": (
        "no glossy CG 3D, no lens flares, no camera cuts within the clip, no full-color midground portraits "
        "(people stay halftone black-and-white), no warped or gibberish text, no invented logos, no watermarks, "
        "no simultaneous entrances, no music, no soundtrack, no voice-over, no narration, no lyrics"
    ),
    "DEEP_DIORAMA": (
        "no flat single-plane composition, no static locked-off camera, no glossy plastic CG (depth stays papercraft), "
        "no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, "
        "no invented logos, no watermarks, no music, no soundtrack, no voice-over, no narration, no lyrics"
    ),
    "LOCKED_STAGE": (
        "no glossy CG 3D, no lens flares, no camera cuts within the clip, no full-color midground portraits "
        "(people stay halftone black-and-white), no warped or gibberish text, no invented logos, no watermarks, "
        "no simultaneous entrances, no music, no soundtrack, no voice-over, no narration, no lyrics"
    )
}

CAMERA_AUDIO_FOLEY_MAP: Dict[str, str] = {
    "dive": "submerge whoosh, deep pressure hum, low newsroom hum",
    "whip": "three whip whooshes, pops landing each hit, room tone",
    "track": "track rumble, stall click, drain hiss, low hum",
    "orbit": "paper pop, gentle air whoosh, ticking counter, low newsroom hum",
    "push-in": "paper slide, stamp thud, subtle tick, low newsroom hum",
    "drift": "paper rustle, subtle tick, low newsroom hum"
}

NAMED_ESCALATION_BEATS: List[str] = ["ALERT WASH", "STAMP", "TICK-UP", "TEAR", "THREAD PULL"]


def audit_cliffhanger_patterns(final_sentence: str) -> Dict[str, Any]:
    """Audits the final sentence against the 5 Canonical Documentary Cliffhanger Patterns:
    1. THE_UNRESOLVED_OBJECT: ends on a physical thing that still exists / remains missing.
    2. THE_DATED_FORWARD_JUMP: leaps forward to a later date/decade.
    3. THE_MISSING_PIECE: names the one thing investigators never found.
    4. THE_QUIET_CONTRADICTION: cold paradox that undermines preceding narrative.
    5. THE_PRICE_LINE: cold human or financial cost stated flat.
    """
    s_low = (final_sentence or "").lower().strip()
    words = s_low.split()
    
    # 1. THE_PRICE_LINE
    if re.search(r'\b(the\s+price|the\s+cost|total\s+loss|toll\s+was|bill\s+was|damage\s+was|losses?\s+(?:totaled|exceeded)|paid\s+the\s+price|millions?\s+(?:of\s+)?(?:lives|dollars)|billions?\s+(?:of\s+)?(?:dollars|euros))\b', s_low):
        return {
            "pattern": "THE_PRICE_LINE",
            "matched": True,
            "description": "Ends on the cold human or financial cost, stated flat.",
            "confidence": 0.95
        }
        
    # 2. THE_DATED_FORWARD_JUMP
    if re.search(r'\b(?:then,?\s+in\s+\d{4}|decades?\s+later|years?\s+later|by\s+\d{4}|in\s+\d{4},?\s+(?:a\s+|the\s+|investigators)|until\s+\d{4}|to\s+this\s+day)\b', s_low):
        return {
            "pattern": "THE_DATED_FORWARD_JUMP",
            "matched": True,
            "description": "Ends by leaping forward to a later date or modern day.",
            "confidence": 0.92
        }

    # 3. THE_MISSING_PIECE
    if re.search(r'\b(?:they\s+had\s+.*they\s+never|found\s+.*never\s+found|had\s+.*never\s+had|one\s+piece\s+was\s+missing|only\s+one\s+thing\s+was\s+missing|the\s+name\s+was\s+never|identity\s+remains|never\s+identified)\b', s_low):
        return {
            "pattern": "THE_MISSING_PIECE",
            "matched": True,
            "description": "Ends by naming the one elusive thing investigators never got.",
            "confidence": 0.90
        }

    # 4. THE_UNRESOLVED_OBJECT
    if re.search(r'\b(?:never\s+found|never\s+recovered|never\s+surfaced|remains?\s+(?:locked|unsolved|missing|undiscovered|lost)|has\s+never\s+been\s+found|vault\s+remains|tape\s+has\s+never)\b', s_low):
        return {
            "pattern": "THE_UNRESOLVED_OBJECT",
            "matched": True,
            "description": "Ends on a physical object/evidence that still remains unresolved.",
            "confidence": 0.88
        }

    # 5. THE_QUIET_CONTRADICTION
    if re.search(r'\b(?:yet\s+|however\s+|empty\s+all\s+along|nothing\s+was\s+there|was\s+never\s+there|the\s+opposite\s+was\s+true|myth\s+all\s+along)\b', s_low):
        return {
            "pattern": "THE_QUIET_CONTRADICTION",
            "matched": True,
            "description": "Ends on a cold paradox that undermines everything before it.",
            "confidence": 0.82
        }

    # Fallback tight ending (concise but not one of the 5 canonical cliffhanger archetypes)
    if len(words) <= 12 and not any(q in s_low for q in ["?", "imagine", "subscribe", "thanks"]):
        return {
            "pattern": "CONCISE_DECLARATIVE",
            "matched": False,
            "is_concise": True,
            "description": "Short declarative ending (<= 12 words), but lacks 5 canonical cliffhanger archetypes.",
            "confidence": 0.60
        }

    return {
        "pattern": "GENERIC",
        "matched": False,
        "is_concise": False,
        "description": "Generic ending without canonical documentary cliffhanger pattern.",
        "confidence": 0.30
    }


class VoxAutomatedDirector:
    """Unified Autonomous Director Engine for Vox Docudrama & Motion Collage."""

    def __init__(self, market: str = "EN", fps: int = 30, animation_duration_sec: int = 10):
        self.market = market.upper()
        self.fps = fps
        self.animation_duration_sec = animation_duration_sec
        self.last_sanitized_bgs: Dict[str, str] = {}
        self.last_sanitized_fgs: Dict[str, str] = {}
        self.last_bg_roster: Dict[str, Any] = {}
        self.last_fg_roster: Dict[str, Any] = {}

    def generate_ideas(self, niche: str, count: int = 10, topic_hint: str = "") -> List[Dict[str, str]]:
        """State 2: Generate exactly 10 video ideas in the specified niche with concrete documentary hooks."""
        norm_niche = (niche or "crime_documentary").lower().replace(" and ", "_").replace(" ", "_")
        
        # Canonical State 2 idea catalogs with dates, locations, numbers, and names
        catalog: Dict[str, List[Dict[str, str]]] = {
            "crime_documentary": [
                {"title": "The Hunt for Dan Cooper: The 1971 Pacific Northwest Skyjacking", "hook": "November 24, 1971 • Flight 305 • $200,000 ransom"},
                {"title": "How the 2008 Societe Generale Rogue Trader Hid 4.9 Billion Euros", "hook": "January 2008 • Jerome Kerviel • Paris La Defense"},
                {"title": "The Antwerp Diamond Heist: How Thieves Breached Vault 104 in 2003", "hook": "February 15, 2003 • Diamond Center • 109 deposit boxes"},
                {"title": "The Man Who Stole the Mona Lisa: Vincenzo Peruggia's 1911 Louvre Theft", "hook": "August 21, 1911 • The Louvre, Paris • 28 months missing"},
                {"title": "The 1978 Lufthansa Heist: Five Million Dollars at JFK Terminal 26", "hook": "December 11, 1978 • JFK Airport • $5.875M stolen"},
                {"title": "What Really Happened to the Amber Room in Königsberg 1945", "hook": "April 1945 • Königsberg Castle • 6 tons of amber"},
                {"title": "The Gardner Museum Heist: Thirteen Masterpieces Lost in 81 Minutes", "hook": "March 18, 1990 • Boston • $500M in stolen art"},
                {"title": "How Bernie Madoff Ran a 64 Billion Dollar Ponzi Scheme for Three Decades", "hook": "December 11, 2008 • Manhattan • $64.8B paper empire"},
                {"title": "The Secret Syndicate Behind the 1994 Bank of England Bond Robbery", "hook": "May 1990 • City of London • £292M bearer bonds"},
                {"title": "The Untouchable Fixer: What Happened to Jimmy Hoffa on July 30, 1975", "hook": "July 30, 1975 • Machus Red Fox restaurant • Detroit"}
            ],
            "history": [
                {"title": "How the 1914 Assassination in Sarajevo Ignited World War One", "hook": "June 28, 1914 • Latin Bridge, Sarajevo • Archduke Franz Ferdinand"},
                {"title": "The Secret Treaty That Divided the Middle East in May 1916", "hook": "May 16, 1916 • London & Paris • Sykes-Picot Agreement"},
                {"title": "Why the Roman Ninth Legion Vanished in Caledonia 117 AD", "hook": "117 AD • Northern Britannia • 5,000 legionaries"},
                {"title": "The Cold War Submarine That Disappeared: The Story of K-129 in 1968", "hook": "March 8, 1968 • Pacific Ocean • Project Azorian"},
                {"title": "How Venetian Spies Stole the Byzantine Silk Formula in 552 AD", "hook": "552 AD • Constantinople • Bamboo smuggling monks"},
                {"title": "The Man Who Predicted the 1929 Wall Street Crash: Roger Babson's Warning", "hook": "September 5, 1929 • Babson Park • Black Tuesday collapse"},
                {"title": "What Really Happened at the Lost Colony of Roanoke in 1587", "hook": "August 1587 • Outer Banks, North Carolina • 115 settlers"},
                {"title": "How the Dutch East India Company Became a 7.9 Trillion Dollar Empire", "hook": "March 20, 1602 • Amsterdam • World's first megacorporation"},
                {"title": "The 1962 Cuban Missile Crisis: Thirteen Days on the Brink of Nuclear War", "hook": "October 16, 1962 • Washington & Moscow • U-2 surveillance photos"},
                {"title": "The Forgotten Collapse of the Bronze Age in 1177 BC Explained", "hook": "1177 BC • Mediterranean basin • The Sea Peoples invasion"}
            ],
            "money_power": [
                {"title": "How Long-Term Capital Management Almost Crashed Wall Street in 1998", "hook": "September 23, 1998 • Greenwich, Connecticut • $3.6B Fed bailout"},
                {"title": "The Day the Pound Broke: How George Soros Made One Billion Dollars in 1992", "hook": "September 16, 1992 • Bank of England • Black Wednesday"},
                {"title": "The Secret 1910 Meeting at Jekyll Island That Created the Federal Reserve", "hook": "November 20, 1910 • Jekyll Island, Georgia • Six financiers"},
                {"title": "How Lehman Brothers Hid 50 Billion Dollars Using Repo 105 in 2008", "hook": "September 15, 2008 • Wall Street • 25,000 employees laid off"},
                {"title": "The 1971 Nixon Shock: How One Speech Ended the Gold Standard", "hook": "August 15, 1971 • Camp David • $35 per ounce fixed rate dissolved"},
                {"title": "The Aluminum Squeeze of 2011: How Detroit Warehouses Controlled Global Supply", "hook": "2011 • Metro Detroit depots • 1.5 million metric tons held"},
                {"title": "How Standard Oil Controlled 90 Percent of American Refining in 1880", "hook": "1880 • Cleveland & New York • John D. Rockefeller's trust"},
                {"title": "The 1980 Silver Thursday: How the Hunt Brothers Cornered One-Third of the Market", "hook": "March 27, 1980 • COMEX New York • 200 million ounces"},
                {"title": "The Sovereign Debt Trap: How Greece Faced 320 Billion Euros in Default", "hook": "May 2, 2010 • Athens & Frankfurt • Troika bailout packages"},
                {"title": "The Swiss Franc Shock of January 2015: When the Currency Peg Evaporated", "hook": "January 15, 2015 • Zurich • 1.20 floor abandoned in minutes"}
            ],
            "technology": [
                {"title": "The Silicon Valley Espionage War: How Hitachi Was Caught Buying IBM Secrets in 1982", "hook": "June 22, 1982 • Santa Clara, California • FBI Operation Pengem"},
                {"title": "How ASML Mastered Extreme Ultraviolet Lithography After Thirty Years of Failures", "hook": "1984 - 2024 • Veldhoven, Netherlands • 13.5 nanometer EUV mirrors"},
                {"title": "The Stuxnet Virus: How Fifty Kilobytes of Code Sabotaged Natanz Centrifuges", "hook": "June 2010 • Natanz, Iran • 1,000 uranium centrifuges destroyed"},
                {"title": "The Man Who Invented the Transistor and Destroyed His Own Company: William Shockley", "hook": "1956 • Mountain View, California • The Traitorous Eight"},
                {"title": "How TSMC Built an 800 Billion Dollar Semiconductor Fortress in Hsinchu", "hook": "1987 • Hsinchu Science Park • Morris Chang's pure-play foundry"},
                {"title": "The 1988 Morris Worm: How 99 Lines of Code Paralyzed Ten Percent of the Internet", "hook": "November 2, 1988 • MIT & Cornell • 6,000 UNIX hosts crashed"},
                {"title": "The 1999 Microsoft Antitrust Trial: Why Judge Jackson Ordered the Company Split", "hook": "November 5, 1999 • Washington DC • Findings of Fact on Internet Explorer"},
                {"title": "How Deep Blue Defeated Garry Kasparov in May 1997 Game Six", "hook": "May 11, 1997 • Manhattan Equitable Center • 19 moves in Game 6"},
                {"title": "The Secret Apollo Guidance Computer: How Margaret Hamilton Coded the Moon Landing", "hook": "July 20, 1969 • NASA Mission Control • 1202 alarm recovery"},
                {"title": "The Rise and Fall of Netscape: How the 1995 Web Pioneer Was Crushed", "hook": "August 9, 1995 • Silicon Valley • 75% market share lost to Windows"}
            ],
            "disasters_survival": [
                {"title": "How Aloha Airlines Flight 243 Survived with an Open Roof in April 1988", "hook": "April 28, 1988 • 24,000 feet over Maui • 18 feet of fuselage ripped"},
                {"title": "The 1996 Mount Everest Disaster: How Eight Climbers Were Trapped in the Death Zone", "hook": "May 10, 1996 • South Col, Mount Everest • Minus 40 degrees storm"},
                {"title": "The Deepwater Horizon Catastrophe: Why the Blowout Preventer Failed in 2010", "hook": "April 20, 2010 • Macondo Prospect, Gulf of Mexico • 5,000 feet depth"},
                {"title": "The Miracle in the Andes: How Sixteen Rugby Players Survived 72 Days in 1972", "hook": "October 13, 1972 • Glacier of Tears • Fairchild FH-227D crash"},
                {"title": "How the 1986 Chernobyl Disaster Unfolded in Control Room Number Four", "hook": "April 26, 1986 • Pripyat, Ukraine • 1:23:45 AM turbine test"},
                {"title": "The Apollo 13 Oxygen Tank Explosion: How NASA Saved Three Astronauts in 1970", "hook": "April 13, 1970 • 200,000 miles from Earth • Odyssey & Aquarius"},
                {"title": "The 1977 Tenerife Airport Collision: The Deadliest Aviation Disaster in History", "hook": "March 27, 1977 • Los Rodeos Airport • 583 fatalities in dense fog"},
                {"title": "The Collapse of the Hyatt Regency Walkways: How a Simple Design Change Killed 114", "hook": "July 17, 1981 • Kansas City, Missouri • Fourth-floor suspended walkway"},
                {"title": "The 1912 Titanic Inquest: How Six Ice Warnings Were Ignored", "hook": "April 14, 1912 • North Atlantic • 11:40 PM iceberg collision"},
                {"title": "The 1975 Banqiao Dam Failure: How 62 Dams Collapsed in Typhoon Nina", "hook": "August 8, 1975 • Henan, China • 1,060 millimeters of rain in 24 hours"}
            ]
        }
        
        # Match nearest niche key
        matched_key = "crime_documentary"
        for k in catalog:
            if k in norm_niche or norm_niche in k:
                matched_key = k
                break
                
        ideas = catalog[matched_key][:count]
        
        # If user gave topic_hint, tailor first idea
        if topic_hint:
            ideas[0] = {
                "title": f"The Investigative Story of {topic_hint}: What Really Happened",
                "hook": f"Archival investigation • Primary ledger evidence • Verified records"
            }
            
        return ideas

    def classify_niche(self, topic: str) -> str:
        """State 1: Classify topic deterministically into one of the 8 Canonical Niches."""
        t_low = (topic or "").lower()
        if re.search(r'\b(ai|chips?|semiconductor|silicon|computers?|hack|công nghệ|vi mạch|software)\b', t_low):
            return "technology"
        if re.search(r'\b(banks?|fed|debts?|bonds?|dollars?|currency|inflation|stocks?|ngân hàng|nợ|lãi suất|tiền tệ)\b', t_low):
            return "money_power"
        if re.search(r'\b(kill|murder|heist|hijack|police|fbi|scandal|công an|vụ án|thảm án|tội phạm)\b', t_low):
            return "crime_documentary"
        if re.search(r'\b(planes?|crash|tsunami|flood|survive|tai nạn|sống sót|thảm họa|rơi máy bay)\b', t_low):
            return "disasters_survival"
        if re.search(r'\b(aliens?|ufo|vanish|disappear|mystery|mysteries|bí ẩn|mất tích)\b', t_low):
            return "mysteries_unexplained"
        if re.search(r'\b(football|olympic|fifa|champion|thể thao|bóng đá)\b', t_low):
            return "sports"
        if re.search(r'\b(wars?|battle|century|empire|ancient|history|thế chiến|lịch sử|triều đại)\b', t_low):
            return "history"
        return "crime_documentary"

    def compute_word_budget(self, duration_sec: int) -> int:
        """State 3: Word math at 2.5 words per second."""
        return max(25, int(duration_sec * 2.5))

    def validate_script_dna(self, script_text: str, duration_sec: int) -> Dict[str, Any]:
        """State 4 Validation: Audit Fern Script DNA (Word budget, Cold Open, Cliffhanger)."""
        words = script_text.split()
        word_count = len(words)
        target = self.compute_word_budget(duration_sec)
        margin = max(5, int(target * 0.15))

        is_word_count_valid = (target - margin) <= word_count <= (target + margin)

        # Audit Cold Open: Sentence 1-3 should contain numbers/dates
        first_50_words = " ".join(words[:50])
        has_temporal_anchor = bool(re.search(r'(?:19\d\d|20\d\d|january|february|march|april|may|june|july|august|september|october|november|december|年|月|日|년|월|일|\d{1,2}:\d{2})', first_50_words, re.I))

        # Audit Cliffhanger: Final sentence <= 20 words and matches 5 Canonical Patterns
        sentences = [s.strip() for s in re.split(r'[.!?]+', script_text) if s.strip()]
        last_sentence = sentences[-1] if sentences else ""
        last_sentence_words = last_sentence.split()
        cliff_audit = audit_cliffhanger_patterns(last_sentence)
        has_tight_ending = (len(last_sentence_words) <= 20) and (cliff_audit.get("matched", False) or cliff_audit.get("is_concise", False))

        # Check for banned em dashes
        has_em_dash = "—" in script_text or "–" in script_text

        return {
            "word_count": word_count,
            "target_word_budget": target,
            "is_word_count_valid": is_word_count_valid,
            "has_temporal_anchor": has_temporal_anchor,
            "has_tight_ending": has_tight_ending,
            "cliffhanger_audit": cliff_audit,
            "has_em_dash": has_em_dash,
            "sentences_count": len(sentences),
            "score": round(
                (1.0 if is_word_count_valid else 0.7) * 3.5 +
                (1.0 if has_temporal_anchor else 0.5) * 2.5 +
                (1.0 if has_tight_ending else (0.7 if len(last_sentence_words) <= 25 else 0.4)) * 3.0 +
                (0.0 if has_em_dash else 1.0) * 1.0,
                2
            )
        }

    def breakdown_beats(self, script_text: str, duration_sec: int) -> List[Dict[str, Any]]:
        """State 6: Split continuous script into 2-3s visual beats, each divided into 2 shots."""
        raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script_text) if s.strip()]
        if not raw_sentences:
            raw_sentences = [script_text.strip()]

        beats: List[Dict[str, Any]] = []
        total_words = len(script_text.split())
        cum_sec = 0.0

        for b_idx, sent in enumerate(raw_sentences):
            sent_words = sent.split()
            sent_word_count = len(sent_words)
            beat_duration_sec = max(2.0, round(sent_word_count / 2.5, 2))

            # Split sentence into 2 halves for Shot A and Shot B mid-sentence cut
            mid_pt = max(1, sent_word_count // 2)
            shot_a_words = " ".join(sent_words[:mid_pt])
            shot_b_words = " ".join(sent_words[mid_pt:]) if mid_pt < sent_word_count else shot_a_words

            # Extract headline (1-4 words) from sentence for Shot A
            words_cleaned = [re.sub(r'[^a-zA-Z0-9\s]', '', w).upper() for w in sent_words if len(w) > 2]
            headline = " ".join(words_cleaned[:3]) if words_cleaned else f"BEAT #{b_idx + 1}"

            start_frame = int(cum_sec * self.fps)
            end_frame = int((cum_sec + beat_duration_sec) * self.fps)
            mid_frame = start_frame + int((end_frame - start_frame) / 2)

            beat_obj = {
                "beat_index": b_idx + 1,
                "narration": sent,
                "word_count": sent_word_count,
                "duration_sec": beat_duration_sec,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_sec": cum_sec,
                "end_sec": cum_sec + beat_duration_sec,
                "headline": headline,
                "shots": [
                    {
                        "shot_id": f"beat_{b_idx + 1}_a",
                        "type": "EST_WIDE",
                        "has_headline": True,
                        "headline_text": headline,
                        "narration_fragment": shot_a_words,
                        "start_frame": start_frame,
                        "end_frame": mid_frame,
                        "camera_move": "slow_push_in" if b_idx % 2 == 0 else "lateral_parallax_pan"
                    },
                    {
                        "shot_id": f"beat_{b_idx + 1}_b",
                        "type": "DETAIL_CUTIN",
                        "has_headline": False,
                        "headline_text": "",
                        "narration_fragment": shot_b_words,
                        "start_frame": mid_frame,
                        "end_frame": end_frame,
                        "camera_move": "static" if b_idx % 3 == 0 else "gentle_rise"
                    }
                ]
            }
            beats.append(beat_obj)
            cum_sec += beat_duration_sec

        return beats

    def forge_image_prompts(
        self,
        beats: List[Dict[str, Any]],
        theme: str = "newsprint-editorial",
        topic: str = "",
        story_text: str = "",
        spoken_sentences: Optional[List[Dict[str, Any]]] = None,
        grounding_intel: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """State 7: Forge 5-part tactile Image Prompts and dynamic visual roster for every beat."""
        style_block = (
            "Mixed-media hand-cut PAPER COLLAGE, editorial documentary zine style. "
            "Aged newsprint and archival map surfaces, black and white halftone photograph cutouts "
            "with rough scissor-cut edges and offset accent strokes, torn paper edges, masking tape fragments, "
            "typewriter caption strips, rubber stamp marks, red string and brass pins, "
            "desaturated archival palette of tan, ink black, and halftone gray with ONE hot red signal accent, "
            "visible print grain and paper fiber, matte flat even documentary lighting with soft physical cutout drop shadows."
        )
        closer = (
            "Every element must appear physically hand-cut and layered from real paper, with visible cutout edges, "
            "halftone print texture, and soft shadow separation between layers. The composition stays clean, minimal, "
            "and editorial with generous negative space. NOT digital illustration, NOT cartoon, NOT 3D render, "
            "NOT glossy, no gradients, no clutter, no watermark, no logos, no text beyond the specified label. "
            "Premium documentary collage aesthetic, 16:9, ultra-detailed, 8K."
        )

        # 1. Prepare story text and sentences context if omitted
        if not story_text:
            story_text = "\n".join(b.get("narration", "") for b in beats if b.get("narration"))
        if not spoken_sentences:
            spoken_sentences = [
                {
                    "text": b.get("narration", ""),
                    "beat_index": b.get("beat_index", 1),
                    "duration_sec": b.get("duration_sec", 6.0),
                    "start_sec": b.get("start_sec", 0.0),
                    "end_sec": b.get("end_sec", 6.0)
                }
                for b in beats
            ]

        # 2. Extract Dynamic Visual Roster anchored to narrative topic
        bg_roster, fg_roster = extract_dynamic_visual_roster(
            story_text=story_text,
            spoken_sentences=spoken_sentences,
            grounding_intel=grounding_intel or {"topic": topic},
            competitor_card=None,
            market=self.market,
            topic=topic or "investigative docudrama"
        )

        # 2.5 Apply Ethical Representation Shield (Child Representation & Real-Person Shield)
        bg_roster, fg_roster = shield_visual_roster(
            bg_roster=bg_roster,
            fg_roster=fg_roster,
            story_text=story_text,
            market=self.market
        )

        # 3. Sanitize all background and foreground prompts (Rule 116, 122, 128, 137)
        sanitized_bgs: Dict[str, str] = {}
        for bg_k, bg_v in bg_roster.items():
            desc = bg_v.get("description", bg_v.get("title", bg_k))
            sanitized_bgs[bg_k] = _sanitize_background_prompt(desc, bg_k, market=self.market)

        sanitized_fgs: Dict[str, str] = {}
        for fg_k, fg_v in fg_roster.items():
            desc = fg_v.get("description", fg_v.get("title", fg_k))
            sanitized_fgs[fg_k] = _sanitize_foreground_prompt(desc, fg_k, market=self.market)

        char_fg_keys = [
            k for k in fg_roster
            if fg_roster[k].get("type") == "character"
            or k.startswith("char_") or k.startswith("fg_character_")
        ]
        prop_fg_keys = [k for k in fg_roster if k not in char_fg_keys]
        if not prop_fg_keys:
            prop_fg_keys = list(fg_roster.keys())

        total_beats = max(1, len(beats))
        bg_keys = list(bg_roster.keys())
        char_count = 0
        last_char_beat = -99

        prompt_manifest: List[Dict[str, Any]] = []

        for b in beats:
            b_idx = b["beat_index"]
            headline = b["headline"]
            narr = b.get("narration", "")
            narr_lower = narr.lower()

            # Map to 5-Beat Docudrama phase
            beat_phase = int(b.get("beat_phase") or ((b_idx - 1) // max(1, total_beats // 5)) + 1)
            beat_phase = min(max(beat_phase, 1), 5)

            # Assign environmental BG (rotating every 3 beats within matching phase)
            matching_bgs = [k for k, v in bg_roster.items() if beat_phase in v.get("beats", [1, 2, 3, 4, 5])]
            if not matching_bgs:
                matching_bgs = bg_keys
            bg_key = matching_bgs[(b_idx // 3) % len(matching_bgs)]

            # Check if this beat is an actor moment or forensic evidence prop moment
            is_char_moment = (
                bool(char_fg_keys) and
                (char_count < 12) and
                (b_idx - last_char_beat >= 8) and
                (any(q in narr for q in ['"', '“', '”', '「', '」']) or
                 any(w in narr_lower for w in ["said", "testified", "admitted", "warned", "declared", "argued", "ruled", "denied", "objected"]))
            )

            if is_char_moment:
                matched_char = None
                for ck in char_fg_keys:
                    c_info = fg_roster[ck]
                    kws = c_info.get("keywords", []) + c_info.get("title", "").lower().split()
                    if any(kw in narr_lower for kw in kws if len(kw) > 3):
                        matched_char = ck
                        break
                if not matched_char:
                    matched_char = char_fg_keys[char_count % len(char_fg_keys)]
                fg_key = matched_char
                char_count += 1
                last_char_beat = b_idx
            else:
                matched_prop = None
                best_score = 0
                for pk in prop_fg_keys:
                    p_info = fg_roster[pk]
                    p_beats = p_info.get("beats", [1, 2, 3, 4, 5])
                    kws = p_info.get("keywords", []) + p_info.get("title", "").lower().split()
                    score = sum(1 for kw in kws if len(kw) > 3 and kw in narr_lower)
                    if beat_phase in p_beats:
                        score += 1
                    if score > best_score:
                        best_score = score
                        matched_prop = pk
                if not matched_prop or best_score <= 1:
                    phase_props = [k for k in prop_fg_keys if beat_phase in fg_roster[k].get("beats", [1, 2, 3, 4, 5])] or prop_fg_keys
                    matched_prop = phase_props[(b_idx // 2) % len(phase_props)]
                fg_key = matched_prop

            hero_label = fg_roster[fg_key].get("title", "PRIMARY OPERATOR")

            # Build tactile composite prompt
            seal_desc = (
                "a red inkan hanko verification stamp" if self.market == "JP" else (
                    "a red official ingam verification seal stamp" if self.market == "KR" else
                    "an official red embossed verification seal stamp"
                )
            )
            scene_desc = (
                f"SCENE as layered paper cut-outs: Primary forensic subject representing '{hero_label}' (dominant, 70% visual weight), "
                f"accompanied by 2-3 supporting archival scraps: a worn memorandum sheet with official headers, "
                f"{seal_desc}, and brass thumbtacks pinning elements to the newsprint surface."
            )

            prompt_text = (
                f"{style_block}\n\n"
                f"{scene_desc}\n\n"
                f"Background setting: {bg_roster[bg_key].get('title', 'archival desk')}.\n\n"
                f'A torn-paper banner with a big bold headline "{headline}", red seal.\n\n'
                f"{closer}"
            )

            b["bg_key"] = bg_key
            b["fg_key"] = fg_key
            b["bg_prompt"] = sanitized_bgs[bg_key]
            b["fg_prompt"] = sanitized_fgs[fg_key]
            b["targetBackground"] = f"images/{bg_key}.png"
            b["targetHeroSrc"] = f"images/{fg_key}.png"
            b["heroLabel"] = hero_label

            prompt_manifest.append({
                "beat_index": b_idx,
                "headline": headline,
                "narration": b["narration"],
                "theme": theme,
                "bg_key": bg_key,
                "fg_key": fg_key,
                "heroLabel": hero_label,
                "targetBackground": f"images/{bg_key}.png",
                "targetHeroSrc": f"images/{fg_key}.png",
                "image_prompt": prompt_text,
                "fg_prompt": sanitized_fgs[fg_key],
                "bg_prompt": sanitized_bgs[bg_key]
            })

        self.last_sanitized_bgs = sanitized_bgs
        self.last_sanitized_fgs = sanitized_fgs
        self.last_bg_roster = bg_roster
        self.last_fg_roster = fg_roster

        return prompt_manifest

    def build_remotion_manifest(
        self,
        beats: List[Dict[str, Any]],
        theme: str = "newsprint-editorial",
        topic: str = "",
        episode_id: str = "VOX_AUTO_EP001",
        video_engine_mode: str = "flow_veo_fast"
    ) -> Dict[str, Any]:
        """State 8: Build master remotion_props.json for Remotion VoxBuildOnStage component."""
        scenes = []
        # Adapt layer entrance delays based on animation duration preset (6s vs 10s)
        is_6s_mode = self.animation_duration_sec == 6
        delay_doc1 = 0.72 if is_6s_mode else 1.2
        delay_doc2 = 0.96 if is_6s_mode else 1.6
        delay_yarn = 1.32 if is_6s_mode else 2.2

        for b in beats:
            b_idx = b["beat_index"]
            headline = b["headline"]
            duration_frames = b["end_frame"] - b["start_frame"]
            bg_key = b.get("bg_key") or f"bg_{b_idx:02d}"
            fg_key = b.get("fg_key") or f"fg_{b_idx:02d}"
            hero_label = b.get("heroLabel") or f"SUBJECT #{b_idx}"

            scene_entry = {
                "id": f"scene_{b_idx:02d}",
                "component": "VoxBuildOnStage",
                "durationInFrames": duration_frames,
                "durationSec": round(duration_frames / self.fps, 2),
                "headline": headline,
                "subtitle": f"RECORD REF // #{b_idx:02d} • EVIDENCE DOSSIER",
                "theme": theme,
                "narration": b.get("narration", ""),
                "heroSrc": f"images/{fg_key}.png",
                "background": f"images/{bg_key}.png",
                "targetHeroSrc": f"images/{fg_key}.png",
                "targetBackground": f"images/{bg_key}.png",
                "heroLabel": hero_label,
                "hasMarkerHighlight": True,
                "stampText": "VERIFIED // IMPORTANT" if b_idx == 1 else "CLASSIFIED EXHIBIT",
                "stampColor": "#dc2626" if b_idx == 1 else "#b91c1c",
                "heroPosition": {
                    "xPct": 50,
                    "yPct": 52,
                    "widthPct": 38
                },
                "supportingCutouts": [
                    {
                        "id": f"doc_{b_idx}_1",
                        "label": f"MEMO #{b_idx}A",
                        "xPct": 26,
                        "yPct": 62,
                        "widthPct": 22,
                        "rotation": -8,
                        "delaySec": delay_doc1,
                        "hasPin": True,
                        "hasTape": False
                    },
                    {
                        "id": f"doc_{b_idx}_2",
                        "label": f"RECORD #{b_idx}B",
                        "xPct": 74,
                        "yPct": 60,
                        "widthPct": 24,
                        "rotation": 11,
                        "delaySec": delay_doc2,
                        "hasPin": False,
                        "hasTape": True
                    }
                ],
                "yarns": [
                    {
                        "fromX": 30,
                        "fromY": 58,
                        "toX": 70,
                        "toY": 56,
                        "color": "#dc2626",
                        "delaySec": delay_yarn
                    }
                ]
            }
            scenes.append(scene_entry)

        total_frames = sum(s["durationInFrames"] for s in scenes)
        return {
            "episodeId": episode_id,
            "topic": topic,
            "theme": theme,
            "fps": self.fps,
            "width": 1920,
            "height": 1080,
            "totalFrames": total_frames,
            "audioMaster": "tts_out.mp3",
            "bgmFile": "bgm/vox_cinematic_pulse.mp3",
            "bgmVolume": 0.12,
            "scenes": scenes,
            "meta": {
                "generatedBy": "VoxAutomatedDirector",
                "videoEngineMode": video_engine_mode,
                "animationDurationSec": self.animation_duration_sec,
                "buildEndSec": 3.8 if is_6s_mode else 7.0,
                "holdSec": 2.2 if is_6s_mode else 3.0,
                "trimStartSec": 0.25,
                "nativeSfxVolume": 0.18,
                "styleReferenceSheet": "config/prompts/vox_master_style_sheet.png",
                "compliance": ["Rule 120", "Rule 125", "Rule 128", "Rule 132", "WOWZ.CLOUD", "CL3_PAPER_DIORAMA"]
            }
        }

    def build_diorama_video_prompts(
        self,
        beats: List[Dict[str, Any]],
        video_engine_mode: str = "flow_veo_fast"
    ) -> List[Dict[str, Any]]:
        """State 7.5: Build CL3 Paper Diorama AI Video Prompts (STYLE BLOCK -> SHOT -> AUDIO -> AVOID).
        - Alternates between FLAT_PARALLAX (data beats) and DEEP_DIORAMA (escalation/reveal beats).
        - Enforces 5-Beat SHOT Formula: Background -> MG -> FG (with type tags) -> Camera (ONE move) -> Settle on...
        - Injects Speech-Locked Timestamp Cues aligned with narration words.
        - Reserves ALERT WASH for at most 1 beat per video (the climax beat).
        - Scrubs real public figure names from video prompts via scrub_public_figure_names_for_video().
        - Includes FFmpeg 0.25s front-trim and -14dB (0.18) native SFX volume retention.
        """
        from app.services.representation_shield import scrub_public_figure_names_for_video
        from app.services.unified_vox_director import inject_speech_timestamp_cue, FLOW_ACCOUNTS

        video_prompts: List[Dict[str, Any]] = []
        total_beats = max(1, len(beats))
        climax_idx = max(1, int(total_beats * 0.75))  # Climax beat ~75% through video (Beat 4)
        alert_wash_used = False

        camera_moves = [
            ("push-in", "Camera pushes in through the foreground gap, focus racking from torn strips to the midground subject", "push-in"),
            ("orbit", "Camera orbits the layered triangle a quarter turn, focus racking card to card", "orbit"),
            ("dive", "Camera dives through the foreground layer into the archival depth field, focus snapping sharp", "dive"),
            ("whip", "Camera whips left to right past the near cards with motion blur, focus racking front to back", "whip"),
            ("track", "Camera executes a fast lateral track across the evidence board then hard stop with overshoot", "track"),
            ("drift", "Camera holds a slow 2% lateral drift across the stage, focus locked on the central cutout", "drift"),
        ]

        settle_targets = [
            "Settle on the giant stat number.",
            "Settle mid-orbit on the central cutout.",
            "Settle wide on the full paper diorama.",
            "Settle on the red-stamped dossier in macro.",
            "Settle on the taut red thread connection."
        ]

        for idx, b in enumerate(beats):
            b_idx = b.get("beat_index", idx + 1)
            narr = b.get("narration", "")
            headline = b.get("headline", f"EXHIBIT #{b_idx}")
            dur_sec = float(b.get("duration_sec", self.animation_duration_sec))
            fg_key = b.get("fg_key", "")
            bg_key = b.get("bg_key", "")

            fg_info = self.last_fg_roster.get(fg_key, {}) if self.last_fg_roster else {}
            bg_info = self.last_bg_roster.get(bg_key, {}) if self.last_bg_roster else {}
            is_public_figure = fg_info.get("type") == "character"

            # 1. Choose Style Block per beat (Deep Diorama for reveals/catalysts, Flat Parallax for restrained data)
            is_escalation = (b_idx == 1) or (b_idx == climax_idx) or (idx % 2 == 1)
            style_block_key = "DEEP_DIORAMA" if is_escalation else "FLAT_PARALLAX"
            style_block_text = DIORAMA_STYLE_BLOCKS[style_block_key]
            avoid_block_text = DIORAMA_AVOID_BLOCKS[style_block_key]

            # 2. Named Escalation Beat (ALERT WASH strictly max once per video on climax beat)
            if b_idx == climax_idx and not alert_wash_used:
                named_beat = "ALERT WASH floods the entire frame to hot red accent in one beat."
                alert_wash_used = True
            elif idx % 4 == 0:
                named_beat = "STAMP slams an official verification mark at foreground depth with a subtle dust puff."
            elif idx % 4 == 1:
                named_beat = "TICK-UP counts the giant stat number upward with spring overshoot then settles."
            elif idx % 4 == 2:
                named_beat = "THREAD PULL snaps red string taut between brass pins."
            else:
                named_beat = "TEAR rips the upper newsprint strip to reveal the ledger layer beneath."

            # 3. Determine FG type tag: (giant number), (counter), (headline), or (label)
            num_match = re.search(r"(\$?\d+(?:[.,]\d+)?(?:\s*(?:%|billion|million|trillion|B|M|T))?)", narr, re.I)
            if num_match:
                fg_text = num_match.group(1).strip().upper()
                fg_tag = "(giant number)"
            else:
                fg_text = headline
                fg_tag = "(headline)"

            # 4. Speech-Locked Timestamp Cue
            sent_obj = {"text": narr, "start_sec": b.get("start_sec", 0.0)}
            ts_cue = inject_speech_timestamp_cue(sent_obj, dur_sec)

            # 5. Camera Move (never two identical moves in a row) & Audio Foley
            cam_key, cam_clause, audio_key = camera_moves[idx % len(camera_moves)]
            if style_block_key == "FLAT_PARALLAX" and cam_key in ("dive", "whip"):
                cam_key, cam_clause, audio_key = camera_moves[5]  # Restrained drift for Flat Parallax
            audio_foley = CAMERA_AUDIO_FOLEY_MAP.get(audio_key, CAMERA_AUDIO_FOLEY_MAP["push-in"])
            settle_clause = settle_targets[idx % len(settle_targets)]

            # 6. Assemble 5-Beat SHOT (Background -> MG -> FG -> Camera -> Settle)
            bg_surface = bg_info.get("title") or "a faded archival world map and ledger sheet"
            mg_subject = fg_info.get("title") or b.get("heroLabel") or "archival halftone evidence cutout"
            if is_public_figure:
                mg_clause = (
                    f"a black-and-white halftone cutout of {mg_subject} with a solid black censor bar across the eyes, "
                    f"positioned off in the midground distance with rough white keyline and offset red stroke"
                )
            else:
                mg_clause = f"layered paper cutouts of {mg_subject} snapping in at staggered midground depths with rough white keylines"

            raw_shot = (
                f"Background: {bg_surface} tilted in perspective, far out of focus. "
                f"MG: {mg_clause}. "
                f'FG: a torn cardstock card at near depth reading "{fg_text}" {fg_tag}. '
                f"{ts_cue} {named_beat} "
                f"{cam_clause}. {settle_clause}"
            )

            # 7. Scrub public figure names from the entire video prompt (0% safety filter failure)
            clean_shot = scrub_public_figure_names_for_video(raw_shot, fg_roster=self.last_fg_roster)

            full_video_prompt = (
                f"{style_block_text}\n\n"
                f"SHOT:\n{clean_shot}\n\n"
                f"AUDIO: {audio_foley} — sound design only, no music, no narration.\n\n"
                f"AVOID: {avoid_block_text}"
            )

            # Route model: Seedance 2.0 Fast / First-Frame Direct for public figures, Flow Veo Fast / Omni for general diorama
            routed_model = "seedance_2_fast" if (is_public_figure and video_engine_mode == "omni_flash") else video_engine_mode
            flow_slot = FLOW_ACCOUNTS[idx % len(FLOW_ACCOUNTS)]

            video_prompts.append({
                "beat_index": b_idx,
                "style_block": style_block_key,
                "style_block_type": style_block_key,
                "routed_model": routed_model,
                "flow_slot": flow_slot,
                "is_public_figure": is_public_figure,
                "is_alert_wash": "ALERT WASH" in named_beat,
                "input_mode": "direct_first_frame" if is_public_figure else "style_sheet_reference",
                "style_reference_sheet": "config/prompts/vox_master_style_sheet.png",
                "duration_sec": 6 if self.animation_duration_sec == 6 else 6,
                "trim_start_sec": 0.25,
                "retain_native_sfx_volume": 0.18,
                "named_escalation_beat": "ALERT WASH" if "ALERT WASH" in named_beat else named_beat.split()[0],
                "speech_timestamp_cue": ts_cue,
                "video_prompt": full_video_prompt
            })

        return video_prompts

    @staticmethod
    def format_textify_bulk_prompts(prompts_manifest: List[Dict[str, Any]]) -> str:
        """State 7: Format prompts into a clean, blank-line-separated Textify bulk feed."""
        clean_prompts = []
        for p in prompts_manifest:
            prompt_str = (p.get("image_prompt") or p.get("video_prompt") or "").strip()
            if prompt_str:
                clean_prompts.append(prompt_str)
        return "\n\n".join(clean_prompts)

    def generate_thumbnails(self, topic: str, hook: str, theme: str = "newsprint-editorial") -> List[str]:
        """State 9: Generate 3 high-contrast YouTube thumbnail prompts with black censor bar."""
        prompts = []
        words = [w.upper() for w in re.sub(r'[^a-zA-Z0-9\s]', '', topic).split() if len(w) > 2]
        hook_word = words[0] if words else "EXPOSED"

        for variant in [1, 2, 3]:
            if variant == 1:
                label_text = f"{hook_word} // VANISHED"
                device = "heavy red marker circle highlighting confidential date"
            elif variant == 2:
                label_text = "THE TRAP // UNMASKED"
                device = "diagonal rubber stamp stamped in red vermilion ink 'IMPORTANT EVIDENCE'"
            else:
                label_text = "LIQUIDATED // 100%"
                device = "thick fluorescent yellow highlighter bar beneath bold headline"

            thumb_prompt = (
                f"High-contrast YouTube documentary paper-collage thumbnail. "
                f"One dominant black and white halftone photograph cutout of primary subject related to '{topic}', "
                f"featuring a thick black censor bar across the eyes to indicate classified identity. "
                f"Aged yellowed newsprint base with rough torn edges bleeding off frame. "
                f"Huge bold condensed all-caps lettering: '{label_text}' on a torn paper label. "
                f"{device}. "
                f"Extreme graphic novel editorial contrast, designed to read clearly at 200 pixels wide on mobile. "
                f"16:9, ultra-detailed, 8K, no small clutter, no logos."
            )
            prompts.append(thumb_prompt)

        return prompts
