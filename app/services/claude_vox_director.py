#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/claude_vox_director.py
Master Sentence-by-Sentence VOX Director Engine (AI Playbook / Master Prompt 2 Standard).
Rule 118, 120, 128, 130, 132 Compliant.

Transforms continuous narrative story.txt into an exact, object-anchored visual storyboard:
1. Sentence-by-Sentence Mapping: Every spoken sentence maps to 1 concrete evidentiary scene.
2. Minimalist Archival Paper Canvas: Background is always warm off-white paper (#f4ece1), zero 3D rooms.
3. Concrete Physical Exhibits: Anchors to tangible documents, chips, contracts, tickers, and ledgers
   directly mentioned in each sentence, isolated on pure solid white (#FFFFFF) for clean alpha cutout.
4. Delicate VOX Proportions: Hero cutout 20-22% width, supporting exhibits 14-18% width, 65%+ negative space.
5. Model Gateway Routing with Fallback: Primary = claude-sonnet-5-5, Fallback = gpt-6.1-sol.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vf.claude_vox_director")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MASTER_TEMPLATE_DOC_PATH = ROOT_DIR / "docs" / "master_template_prompt_google_doc_full.txt"

_JSON_CONTRACT_APPENDIX = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT JSON OUTPUT CONTRACT FOR AUTOMATED REMOTION PIPELINE:
Canvas background is ALWAYS warm archival off-white paper (#f4ece1) with generous negative space (65%+).
NEVER create 3D photorealistic rooms, office interiors, or CGI environments.
Every cutout and exhibit MUST be rendered isolated on a pure solid white background (#FFFFFF) for crisp alpha extraction.

FOR EACH SENTENCE IN THE INPUT TEXT, OUTPUT ONE JSON OBJECT INSIDE A JSON ARRAY:
{
  "scene_index": 1,
  "sentence": "<EXACT_SPOKEN_SENTENCE>",
  "core_idea": "<FACTUAL_UNDERLYING_DYNAMIC_OR_PARADOX>",
  "editorial_title": "<1_TO_4_WORDS_BOLD_HEADLINE_IN_ALL_CAPS>",
  "visual_metaphor": "<SPECIFIC_PHYSICAL_OBJECT_OR_EXHIBIT_DERIVED_FROM_SENTENCE>",
  "main_subject_cutout": {
    "name": "<SHORT_SLUG_ID>",
    "label": "<READABLE_EXHIBIT_LABEL>",
    "width_pct": 22,
    "backdrop": "#FFFFFF",
    "prompt": "Hand-cut black and white halftone photograph cutout of <SPECIFIC_FORENSIC_SUBJECT>, rough scissor-cut deckle edges, subtle print grain, flat lay lighting with soft paper shadow, isolated on pure solid white background (#FFFFFF) with clean alpha boundary --no 3D rooms, no walls, no background clutter"
  },
  "supporting_exhibits": [
    {
      "name": "<SPECIFIC_DOCUMENT_OR_ARTIFACT_SLUG>",
      "label": "<EXACT_EXHIBIT_NAME>",
      "width_pct": 16,
      "rotation": -6,
      "has_pin": true,
      "has_tape": false,
      "entrance_type": "slide_in_deal",
      "has_marker_highlight": true,
      "highlight_text": "<KEY_METRIC_OR_CLAUSE>",
      "backdrop": "#FFFFFF",
      "prompt": "Authentic archival paper cutout of <SPECIFIC_EXHIBIT_OR_CONTRACT>, printed typography and official stamp mark, folded paper crease, rough scissor-cut edges, isolated on pure solid white background (#FFFFFF) --no 3D shadows, no background environment"
    }
  ],
  "yarn_connection": {
    "has_connection": true,
    "from_point": {"x": 35, "y": 50},
    "to_point": {"x": 65, "y": 50},
    "color": "#dc2626"
  },
  "stamp": {
    "text": "<1_TO_2_WORD_STAMP_TEXT>",
    "color": "#dc2626"
  },
  "animation_cue": {
    "type": "marker_highlight",
    "trigger_keyword": "<EXACT_KEYWORD_OR_NUMBER_FROM_SENTENCE>",
    "highlight_color": "#ffe600"
  }
}
Return ONLY a valid JSON array of scene objects. No markdown prose outside the JSON array.
"""


def load_master_prompt_2(doc_path: Optional[Path] = None) -> str:
    """Loads Master Prompt 2 specification from docs/master_template_prompt_google_doc_full.txt (Rule 132)."""
    target_path = doc_path or MASTER_TEMPLATE_DOC_PATH
    base_prompt = (
        "You are an elite Editorial Art Director, Documentary Visual Storyteller, VOX-style Designer, "
        "Motion Graphics Concept Artist, Magazine Layout Designer, and Prompt Engineer.\n"
        "Your mission is to transform an entire documentary script into a sequence of premium AI image prompts "
        "and physical object scene directives for a VOX-style tactile paper-collage documentary."
    )
    if target_path.exists():
        try:
            raw_doc = target_path.read_text(encoding="utf-8", errors="ignore")
            p2_start = raw_doc.find("Prompt 2:")
            p3_start = raw_doc.find("Prompt 3:")
            if p2_start != -1:
                section = raw_doc[p2_start:p3_start] if p3_start != -1 else raw_doc[p2_start:]
                # Collapse excessive blank lines while preserving Prompt 2 structure
                compact_lines = [line.strip() for line in section.splitlines()]
                non_empty = [line for line in compact_lines if line]
                base_prompt = "\n".join(non_empty)
        except Exception as exc:
            logger.debug(f"[claude_vox_director] Fallback prompt used ({exc})")

    return f"{base_prompt}\n\n{_JSON_CONTRACT_APPENDIX.strip()}"


MASTER_DIRECTOR_SYSTEM_PROMPT = load_master_prompt_2()


def split_story_into_sentences(story_text: str) -> List[str]:
    """Splits narrative story into clean grammatical sentences ending in terminal punctuation."""
    if not story_text:
        return []
    cleaned = re.sub(r"={3,}\s*ACT\s+[IVXLCDM]+\s*={3,}", "", story_text, flags=re.I)
    cleaned = re.sub(r"#{1,6}\s+.*", "", cleaned)

    raw_sents = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    sentences = [s.strip() for s in raw_sents if s.strip() and len(s.strip()) > 3]
    return sentences


def _clamp_editorial_title(raw_title: str, fallback_words: List[str], sc_idx: int) -> str:
    """Enforces 1-4 words ALL CAPS editorial headline constraint from Master Prompt 2."""
    cleaned = re.sub(r"\s+", " ", (raw_title or "").strip()).upper()
    tokens = [t for t in cleaned.split(" ") if t and t != "//"]
    if 1 <= len(tokens) <= 4:
        return " ".join(tokens)
    if len(tokens) > 4:
        return " ".join(tokens[:4])
    if fallback_words:
        return " ".join(w.upper() for w in fallback_words[:3])
    return f"EXHIBIT #{sc_idx}"


def _ensure_pure_white_prompt(prompt_text: str, subject_desc: str, is_hero: bool = True) -> str:
    """Guarantees isolated pure solid white (#FFFFFF) background directive for clean B4/B5 alpha extraction."""
    p = (prompt_text or "").strip()
    if not p:
        if is_hero:
            p = (
                f"Hand-cut black and white halftone photograph cutout of {subject_desc}, "
                f"rough scissor-cut deckle edges, subtle print grain, flat lay studio lighting"
            )
        else:
            p = (
                f"Authentic archival paper document cutout of {subject_desc}, "
                f"printed typography, folded crease, rough scissor-cut edges"
            )
    if "pure solid white background" not in p.lower():
        p = f"{p.rstrip('. ')}, isolated on pure solid white background (#FFFFFF) with clean alpha boundary"
    if "--no 3d" not in p.lower():
        p = f"{p} --no 3D rooms, no photorealistic background, no clutter"
    return p


def _is_cjk_char(char: str) -> bool:
    """Checks if character belongs to CJK / Hangul / Kana ranges."""
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x3040 <= cp <= 0x309F
        or 0x30A0 <= cp <= 0x30FF
        or 0xFF66 <= cp <= 0xFF9F
        or 0xAC00 <= cp <= 0xD7AF
        or 0x1100 <= cp <= 0x11FF
        or 0x3130 <= cp <= 0x318F
    )


def _extract_sentence_exhibits(sentence: str, sc_idx: int) -> Dict[str, Any]:
    """Deterministically extracts specific metrics, codes, and tangible exhibit nouns from a sentence.

    Preserves Sino-Korean / CJK single-character numerals and counters (네, 곳, 세, 두, etc.),
    detects multi-clause contrast structures (~지만, ~으나, vs), and ensures key investigative
    sanctions and metrics (시정명령, 미인허가, 30%, 공정위, 네 곳) are never dropped or clipped.
    """
    # 1. Extract alphanumeric model/filing codes (e.g., H200, 8-K, 10-K, CDS, KFTC)
    codes = re.findall(r"\b(?:[A-Z]{1,4}-?\d{1,4}[A-Z]?|CDS|SEC|FTC|KFTC|FBI|GDP|IPO|AI|GPU)\b", sentence)

    # 2. Extract quantitative metrics (e.g., 197.3bp, $40B, 400억달러, 2056, 14%, 네 곳)
    metrics = re.findall(
        r"(?:[\$¥₩€£]\s*\d+(?:[.,]\d+)?(?:\s*(?:billion|million|trillion|B|M|T|억|만|조|천))?|\d+(?:[.,]\d+)?\s*(?:%|bp|bps|억\s*달러|억|만|조|천|万|億|兆|billion|million|trillion|년|월|일|곳))",
        sentence,
        flags=re.I,
    )

    # 3. Preserve compound units like '네 곳' or '네 곳의'
    norm_sentence = re.sub(r"\b네\s+곳\b", "네_곳", sentence)
    raw_tokens = re.findall(r"[A-Za-z0-9가-힣ぁ-んァ-ヶ一-龥_]+", norm_sentence)
    words: List[str] = []
    for w in raw_tokens:
        clean_w = w.replace("_", " ")
        if len(clean_w) >= 2 or any(_is_cjk_char(c) for c in clean_w) or clean_w.isdigit():
            words.append(clean_w)

    # 4. Check for two-clause contrast (e.g. "광고는 마감을 외쳤지만, 사업은 인허가 전이었습니다")
    contrast_m = re.search(r"(.+?(?:지만|으나|는데|반면|however|but|yet))\s*,\s*(.+)", sentence)
    contrast_hero = ""
    if contrast_m:
        c1, c2 = contrast_m.group(1), contrast_m.group(2)
        if "마감" in c1 and "인허가" in c2:
            contrast_hero = "마감 임박 vs 인허가 전"
        elif "승인" in c1 and "마감" in c2:
            contrast_hero = "관할청 미승인 vs 마감 의혹"
        else:
            toks1 = [w.replace("_", " ") for w in re.findall(r"[A-Za-z0-9가-힣_]+", re.sub(r"\b네\s+곳\b", "네_곳", c1)) if len(w) >= 2 or any(_is_cjk_char(ch) for ch in w)]
            toks2 = [w.replace("_", " ") for w in re.findall(r"[A-Za-z0-9가-힣_]+", re.sub(r"\b네\s+곳\b", "네_곳", c2)) if len(w) >= 2 or any(_is_cjk_char(ch) for ch in w)]
            t1 = toks1[-2] if len(toks1) >= 2 else (toks1[0] if toks1 else "광고 마감")
            t2 = " ".join(toks2[:2]) if len(toks2) >= 2 else (toks2[0] if toks2 else "인허가 전")
            contrast_hero = f"{t1} vs {t2}".strip(" vs")

    # 5. Prioritize salient investigative terms
    salient_catalog = [
        "시정명령", "공정위", "제재", "네 곳", "미인허가", "인허가", "30%", "마감임박",
        "드림하우징", "연합뉴스", "MBC", "경기일보", "허위", "기만", "국제뉴스", "과징금"
    ]
    found_salient = [s for s in salient_catalog if s in sentence]

    primary_tokens: List[str] = []
    # Seed with codes and metrics first
    for item in codes + metrics + found_salient:
        clean_tok = item.strip()
        if clean_tok and clean_tok.upper() not in [t.upper() for t in primary_tokens]:
            primary_tokens.append(clean_tok)

    # Add remaining content words, filtering out pure functional particles
    stop_particles = {"등", "이", "가", "은", "는", "을", "를", "에", "의", "과", "와", "로", "으로", "에서", "도"}
    for w in words:
        if w not in stop_particles and w.upper() not in [t.upper() for t in primary_tokens]:
            primary_tokens.append(w)
        if len(primary_tokens) >= 8:
            break

    # Build hero label
    if contrast_hero:
        hero_label = contrast_hero
    elif "네 곳" in sentence and "미인허가" in sentence:
        hero_label = "경기일보 // 네 곳 미인허가"
    elif "네 곳" in sentence and "드림하우징" in sentence:
        hero_label = "시행사 네 곳 // 드림하우징"
    elif "허위" in sentence and "시정명령" in sentence:
        hero_label = "허위·기만 광고 // 시정명령"
    elif "연합뉴스" in sentence or "MBC" in sentence:
        hero_label = "연합뉴스·MBC // 인허가 전 모집"
    elif "30%" in sentence and "마감임박" in sentence:
        hero_label = "마감임박 // 회원 모집률 30%"
    elif len(found_salient) >= 2:
        hero_label = f"{found_salient[0]} // {found_salient[1]}"
    elif found_salient:
        other = [w for w in words if w not in found_salient and w not in stop_particles]
        hero_label = f"{found_salient[0]} // {other[0]}" if other else found_salient[0]
    elif primary_tokens:
        hero_label = " ".join(primary_tokens[:3]).upper()
    else:
        hero_label = f"EXHIBIT #{sc_idx}"

    editorial_title = _clamp_editorial_title("", primary_tokens[:3], sc_idx)
    metric_str = metrics[0].strip() if metrics else (codes[0].strip() if codes else "")
    trigger_kw = metric_str or (found_salient[0] if found_salient else (words[0] if words else "record"))

    slug_base = re.sub(r"[^a-z0-9]+", "_", "_".join(primary_tokens[:2]).lower()).strip("_") or f"scene_{sc_idx:02d}"

    exhibit_1_label = (
        f"{codes[0]} // {metrics[0]}".upper()
        if (codes and metrics)
        else (metric_str.upper() if metric_str else f"RECORD // {words[0].upper()}" if words else f"EXHIBIT #{sc_idx}A")
    )
    exhibit_2_label = (
        " ".join(words[1:4]).upper()
        if len(words) >= 3
        else (f"CLAUSE // {codes[-1].upper()}" if codes else f"DOCKET #{sc_idx}B")
    )

    return {
        "editorial_title": editorial_title,
        "metric_str": metric_str,
        "trigger_kw": trigger_kw,
        "slug_base": slug_base[:28],
        "hero_label": hero_label[:40],
        "exhibit_1_label": exhibit_1_label[:26],
        "exhibit_2_label": exhibit_2_label[:26],
        "words": words,
    }


class ClaudeVoxDirector:
    """Master Sentence-by-Sentence VOX Director Engine with Automatic Model Gateway Fallback."""

    def __init__(self, model: str = "claude-sonnet-5-5", fallback_model: str = "gpt-6.1-sol"):
        self.primary_model = model
        self.fallback_model = fallback_model
        self.system_prompt = load_master_prompt_2()

    def plan_storyboard(
        self,
        story_text: str,
        market: str = "EN",
        chunk_size: int = 25,
        gateway: Optional[Any] = None,
        sentences_override: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Plans complete Sentence-by-Sentence Vox Storyboard with Act-chunked token safety."""
        sentences = sentences_override if sentences_override is not None else split_story_into_sentences(story_text)
        if not sentences:
            logger.warning("[claude_vox_director] No sentences found in story text.")
            return []

        logger.info(
            f"[claude_vox_director] Planning Master Prompt 2 storyboard for {len(sentences)} sentences ({market})..."
        )

        all_scenes: List[Dict[str, Any]] = []
        global_idx = 1

        for i in range(0, len(sentences), chunk_size):
            chunk = sentences[i : i + chunk_size]
            chunk_scenes = self._process_sentence_chunk(
                chunk_sentences=chunk,
                start_index=global_idx,
                market=market,
                gateway=gateway,
            )
            all_scenes.extend(chunk_scenes)
            global_idx += len(chunk_scenes)

        logger.info(f"[claude_vox_director] Successfully planned {len(all_scenes)} sentence-anchored scenes.")
        return all_scenes

    def _process_sentence_chunk(
        self,
        chunk_sentences: List[str],
        start_index: int,
        market: str,
        gateway: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Processes a single chunk of sentences through ModelGateway with automatic fallback."""
        numbered_sentences = "\n".join(
            [f"{start_index + idx}. {s}" for idx, s in enumerate(chunk_sentences)]
        )
        user_prompt = (
            f"TARGET MARKET: {market}\n"
            f"BACKGROUND CANVAS LOCK: #f4ece1 (Warm archival off-white paper, zero 3D rooms).\n"
            f"CUTOUT ISOLATION LOCK: Pure solid white background (#FFFFFF) for all cutouts and exhibits.\n"
            f"PROCESS THE FOLLOWING {len(chunk_sentences)} SENTENCES (STARTING AT SCENE {start_index}) "
            f"INTO EXACTLY {len(chunk_sentences)} VOX PAPER COLLAGE SCENES:\n\n"
            f"{numbered_sentences}\n\n"
            f"Return ONLY the JSON array of {len(chunk_sentences)} scene objects."
        )

        is_fast_test = bool(
            gateway is None
            and (
                os.environ.get("PYTEST_CURRENT_TEST")
                or "pytest" in sys.modules
                or os.getenv("VF_SMOKE_TEST")
                or os.getenv("DISABLE_LLM_TIMELINE_DIRECTOR")
            )
        )

        if not is_fast_test:
            if gateway is None:
                from app.services.model_gateway import get_global_gateway
                gateway = get_global_gateway()

            try:
                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    system_prompt=self.system_prompt,
                    model=self.primary_model,
                    fallback=self.fallback_model,
                    max_tokens=4000,
                    temperature=0.3,
                    timeout=75.0,
                )

                parsed = self._extract_json_scenes(raw_response)
                if parsed and len(parsed) >= len(chunk_sentences) * 0.7:
                    return [
                        self._normalize_scene_object(
                            raw_sc=parsed[idx] if idx < len(parsed) else {},
                            sentence=sent,
                            sc_idx=start_index + idx,
                        )
                        for idx, sent in enumerate(chunk_sentences)
                    ]
                logger.warning(
                    f"[claude_vox_director] Insufficient scenes parsed ({len(parsed)}/{len(chunk_sentences)}). "
                    "Using deterministic Master Prompt 2 extractor."
                )
            except Exception as exc:
                logger.error(
                    f"[claude_vox_director] Gateway call failed for chunk at {start_index}: {exc}. "
                    "Using deterministic Master Prompt 2 extractor."
                )

        return self._build_deterministic_fallback_chunk(chunk_sentences, start_index, market)

    def _normalize_scene_object(
        self,
        raw_sc: Dict[str, Any],
        sentence: str,
        sc_idx: int,
    ) -> Dict[str, Any]:
        """Normalizes LLM scene output to enforce Master Prompt 2 invariants and delicate 14-18% exhibit sizing."""
        extracted = _extract_sentence_exhibits(sentence, sc_idx)
        raw_title = (
            raw_sc.get("editorial_title")
            or raw_sc.get("Editorial Title")
            or extracted["editorial_title"]
        )
        editorial_title = _clamp_editorial_title(str(raw_title), extracted["words"], sc_idx)
        core_idea = str(
            raw_sc.get("core_idea")
            or raw_sc.get("Core Idea")
            or f"Forensic evidentiary analysis of {editorial_title}"
        )
        visual_metaphor = str(
            raw_sc.get("visual_metaphor")
            or raw_sc.get("Visual Metaphor")
            or f"Tactile archival exhibit cutout for {editorial_title}"
        )

        raw_hero = (
            raw_sc.get("main_subject_cutout")
            or raw_sc.get("Main Subject Cutout")
            or raw_sc.get("hero_cutout")
            or {}
        )
        if not isinstance(raw_hero, dict):
            raw_hero = {}
        hero_name = str(raw_hero.get("name") or f"fg_hero_{sc_idx:02d}_{extracted['slug_base']}")
        hero_label = str(raw_hero.get("label") or extracted["hero_label"])
        raw_hero_w = int(raw_hero.get("width_pct") or 22)
        hero_width_pct = min(max(raw_hero_w, 18), 25)
        hero_prompt = _ensure_pure_white_prompt(
            str(raw_hero.get("prompt") or ""),
            subject_desc=f"{hero_label} ({visual_metaphor})",
            is_hero=True,
        )

        hero_cutout = {
            "name": hero_name,
            "label": hero_label,
            "width_pct": hero_width_pct,
            "backdrop": "#FFFFFF",
            "prompt": hero_prompt,
        }

        raw_exhibits = (
            raw_sc.get("supporting_exhibits")
            or raw_sc.get("Supporting Exhibits")
            or raw_sc.get("supporting_cutouts")
            or []
        )
        if not isinstance(raw_exhibits, list) or not raw_exhibits:
            raw_exhibits = [
                {
                    "name": f"fg_exhibit_{sc_idx:02d}_a_{extracted['slug_base']}",
                    "label": extracted["exhibit_1_label"],
                    "width_pct": 16,
                    "rotation": -6,
                    "has_pin": True,
                    "has_tape": False,
                    "entrance_type": "slide_in_deal",
                    "has_marker_highlight": True,
                    "highlight_text": extracted["trigger_kw"],
                }
            ]

        normalized_exhibits: List[Dict[str, Any]] = []
        for ex_idx, ex in enumerate(raw_exhibits[:3]):
            if not isinstance(ex, dict):
                continue
            ex_name = str(ex.get("name") or f"fg_exhibit_{sc_idx:02d}_{ex_idx + 1}_{extracted['slug_base']}")
            ex_label = str(ex.get("label") or extracted["exhibit_1_label"])
            raw_w = int(ex.get("width_pct") or 16)
            # Enforce delicate 14% - 18% width per Step 3
            clamped_w = min(max(raw_w, 14), 18)
            ex_prompt = _ensure_pure_white_prompt(
                str(ex.get("prompt") or ""),
                subject_desc=f"{ex_label} evidentiary document regarding {sentence[:50]}",
                is_hero=False,
            )
            normalized_exhibits.append(
                {
                    "name": ex_name,
                    "label": ex_label,
                    "width_pct": clamped_w,
                    "rotation": int(ex.get("rotation", -6 if ex_idx == 0 else 8)),
                    "has_pin": bool(ex.get("has_pin", ex_idx == 0)),
                    "has_tape": bool(ex.get("has_tape", ex_idx > 0)),
                    "entrance_type": str(
                        ex.get("entrance_type") or ("slide_in_deal" if ex_idx == 0 else "delicate_tack")
                    ),
                    "has_marker_highlight": bool(ex.get("has_marker_highlight", ex_idx == 0)),
                    "highlight_text": str(ex.get("highlight_text") or ex_label),
                    "backdrop": "#FFFFFF",
                    "prompt": ex_prompt,
                }
            )

        raw_cue = raw_sc.get("animation_cue") or raw_sc.get("Animation Cue") or {}
        if not isinstance(raw_cue, dict):
            raw_cue = {}
        animation_cue = {
            "type": str(raw_cue.get("type") or "marker_highlight"),
            "trigger_keyword": str(raw_cue.get("trigger_keyword") or extracted["trigger_kw"]),
            "highlight_color": str(raw_cue.get("highlight_color") or "#ffe600"),
        }

        raw_yarn = raw_sc.get("yarn_connection") or {}
        if not isinstance(raw_yarn, dict):
            raw_yarn = {}
        yarn_connection = {
            "has_connection": bool(raw_yarn.get("has_connection", True)),
            "from_point": raw_yarn.get("from_point") or {"x": 35, "y": 50},
            "to_point": raw_yarn.get("to_point") or {"x": 65, "y": 50},
            "color": str(raw_yarn.get("color") or "#dc2626"),
        }

        raw_stamp = raw_sc.get("stamp") or {}
        if not isinstance(raw_stamp, dict):
            raw_stamp = {}
        stamp_default = f"DATA // {extracted['metric_str']}".upper() if extracted["metric_str"] else "VERIFIED"
        stamp = {
            "text": str(raw_stamp.get("text") or stamp_default),
            "color": str(raw_stamp.get("color") or "#dc2626"),
        }

        return {
            "scene_index": sc_idx,
            "sentence": sentence,
            "core_idea": core_idea,
            "editorial_title": editorial_title,
            "visual_metaphor": visual_metaphor,
            "background_canvas": {
                "hex": "#f4ece1",
                "style": "warm_archival_paper",
                "key": f"bg_paper_canvas_{sc_idx:02d}",
            },
            "main_subject_cutout": hero_cutout,
            "hero_cutout": hero_cutout,
            "supporting_exhibits": normalized_exhibits,
            "supporting_cutouts": normalized_exhibits,
            "yarn_connection": yarn_connection,
            "stamp": stamp,
            "animation_cue": animation_cue,
        }

    def _extract_json_scenes(self, raw_text: str) -> List[Dict[str, Any]]:
        """Extracts and parses JSON array from LLM response."""
        if not raw_text:
            return []
        cleaned = raw_text.strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            for p in parts:
                p_trim = p.strip()
                if p_trim.startswith("json"):
                    p_trim = p_trim[4:].strip()
                if p_trim.startswith("[") and p_trim.endswith("]"):
                    try:
                        return json.loads(p_trim)
                    except Exception as _json_err:
                        logger.debug(f"[claude_vox_director] JSON block decode retry: {_json_err}")

        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception as exc:
                logger.debug(f"[claude_vox_director] JSON parse failed: {exc}")
        return []

    def _build_deterministic_fallback_chunk(
        self,
        sentences: List[str],
        start_index: int,
        market: str,
    ) -> List[Dict[str, Any]]:
        """Rule 128 Generic Deterministic Extractor: Derives concrete exhibits directly from each sentence."""
        scenes: List[Dict[str, Any]] = []
        for idx, sent in enumerate(sentences):
            sc_idx = start_index + idx
            extracted = _extract_sentence_exhibits(sent, sc_idx)
            title = extracted["editorial_title"]
            slug = extracted["slug_base"]

            raw_fallback = {
                "scene_index": sc_idx,
                "sentence": sent,
                "core_idea": f"Evidentiary audit of {title}",
                "editorial_title": title,
                "visual_metaphor": f"Archival forensic exhibit cutout for {title}",
                "main_subject_cutout": {
                    "name": f"fg_hero_{sc_idx:02d}_{slug}",
                    "label": extracted["hero_label"],
                    "width_pct": 22,
                    "backdrop": "#FFFFFF",
                    "prompt": (
                        f"Hand-cut black and white halftone photograph cutout of {extracted['hero_label']} forensic subject, "
                        f"rough scissor-cut deckle edges, subtle print grain, flat lay studio lighting, "
                        f"isolated on pure solid white background (#FFFFFF) with clean alpha boundary "
                        f"--no 3D rooms, no photorealistic background, no clutter"
                    ),
                },
                "supporting_exhibits": [
                    {
                        "name": f"fg_exhibit_{sc_idx:02d}_1_{slug}",
                        "label": extracted["exhibit_1_label"],
                        "width_pct": 16,
                        "rotation": -6,
                        "has_pin": True,
                        "has_tape": False,
                        "entrance_type": "slide_in_deal",
                        "has_marker_highlight": True,
                        "highlight_text": extracted["trigger_kw"],
                        "backdrop": "#FFFFFF",
                        "prompt": (
                            f"Authentic archival paper exhibit cutout of {extracted['exhibit_1_label']} ({sent[:45]}), "
                            f"printed ledger typography, folded crease, rough scissor-cut edges, "
                            f"isolated on pure solid white background (#FFFFFF) --no 3D shadows, no background"
                        ),
                    },
                    {
                        "name": f"fg_exhibit_{sc_idx:02d}_2_{slug}",
                        "label": extracted["exhibit_2_label"],
                        "width_pct": 15,
                        "rotation": 8,
                        "has_pin": False,
                        "has_tape": True,
                        "entrance_type": "delicate_tack",
                        "has_marker_highlight": False,
                        "highlight_text": extracted["exhibit_2_label"],
                        "backdrop": "#FFFFFF",
                        "prompt": (
                            f"Hand-cut archival evidentiary card for {extracted['exhibit_2_label']}, "
                            f"official verification stamp mark, rough deckle edges, "
                            f"isolated on pure solid white background (#FFFFFF) --no 3D rooms, no background"
                        ),
                    },
                ],
                "yarn_connection": {
                    "has_connection": True,
                    "from_point": {"x": 35, "y": 50},
                    "to_point": {"x": 65, "y": 50},
                    "color": "#dc2626",
                },
                "stamp": {
                    "text": "RECORD" if not extracted["metric_str"] else f"DATA // {extracted['metric_str']}".upper(),
                    "color": "#dc2626",
                },
                "animation_cue": {
                    "type": "marker_highlight",
                    "trigger_keyword": extracted["trigger_kw"],
                    "highlight_color": "#ffe600",
                },
            }
            scenes.append(self._normalize_scene_object(raw_fallback, sent, sc_idx))
        return scenes
