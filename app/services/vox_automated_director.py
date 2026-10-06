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

logger = logging.getLogger("vf.vox_automated_director")


class VoxAutomatedDirector:
    """Unified Autonomous Director Engine for Vox Docudrama & Motion Collage."""

    def __init__(self, market: str = "EN", fps: int = 30):
        self.market = market.upper()
        self.fps = fps
        self.last_sanitized_bgs: Dict[str, str] = {}
        self.last_sanitized_fgs: Dict[str, str] = {}
        self.last_bg_roster: Dict[str, Any] = {}
        self.last_fg_roster: Dict[str, Any] = {}

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

        # Audit Cliffhanger: Final sentence <= 25 words
        sentences = [s.strip() for s in re.split(r'[.!?]+', script_text) if s.strip()]
        last_sentence_words = sentences[-1].split() if sentences else []
        has_tight_ending = len(last_sentence_words) <= 25

        # Check for banned em dashes
        has_em_dash = "—" in script_text or "–" in script_text

        return {
            "word_count": word_count,
            "target_word_budget": target,
            "is_word_count_valid": is_word_count_valid,
            "has_temporal_anchor": has_temporal_anchor,
            "has_tight_ending": has_tight_ending,
            "has_em_dash": has_em_dash,
            "sentences_count": len(sentences),
            "score": round(
                (1.0 if is_word_count_valid else 0.7) * 4.0 +
                (1.0 if has_temporal_anchor else 0.5) * 3.0 +
                (1.0 if has_tight_ending else 0.5) * 2.0 +
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
        episode_id: str = "VOX_AUTO_EP001"
    ) -> Dict[str, Any]:
        """State 8: Build master remotion_props.json for Remotion VoxBuildOnStage component."""
        scenes = []
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
                        "delaySec": 1.2,
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
                        "delaySec": 1.6,
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
                        "delaySec": 2.2
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
                "compliance": ["Rule 120", "Rule 125", "Rule 128", "Rule 132", "WOWZ.CLOUD"]
            }
        }

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
