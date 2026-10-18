#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/contracts/b2_b3_contract.py — B2 to B3/B3.5 Contract Authority (AVF-VOX-001 / Rule 125).

Defines strict input contracts for Stage S03 (Script Handoff) and Stage S05 (Director Plan).
Zero-Mock Mandate (Rule 118): Fails loud with B2ContractError if B2 script is missing or invalid.
Never falls back to hardcoded mock beats.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

logger = logging.getLogger("b2_b3_contract")


class B2ContractError(RuntimeError):
    """Raised when B2 spoken script is missing, empty, or fails contract shape.
    
    Rule 118 & Rule 125: Strictly fail-closed. Never silently fallback to mock beats.
    """
    pass


class SpokenBeat(BaseModel):
    """Single spoken narration beat verbatim from B2."""
    beat_id: str = Field(description="Deterministic beat ID e.g. 'b01', 'b02'")
    beat_index: int = Field(default=1, description="1-indexed sequence order")
    text: str = Field(description="Verbatim narration text from B2 without alterations")
    text_sha1: str = Field(description="SHA1 of NFKC normalized trimmed text")

    @classmethod
    def create(cls, beat_id: str, text: str, beat_index: int = 1) -> SpokenBeat:
        norm = unicodedata.normalize("NFKC", text).strip()
        sha1 = hashlib.sha1(norm.encode("utf-8")).hexdigest()
        return cls(beat_id=beat_id, beat_index=beat_index, text=text.strip(), text_sha1=sha1)


class SpokenScript(BaseModel):
    """Complete B2 spoken script payload with cryptographic provenance."""
    episode_id: str
    source_path: str
    source_sha256: str
    total_beats: int
    beats: List[SpokenBeat]


class ObjectSpec(BaseModel):
    """Individual cutout or backdrop element for Vox composition."""
    id: str
    name: str
    attributes: List[str] = Field(default_factory=list)
    role: str = "primary"  # primary | secondary | backdrop


class ActionSpec(BaseModel):
    """Discrete kinematics and motion track for an object in a beat."""
    subject: str
    verb: str  # slides_in | stamps | drops | cuts | scales_up | connects | holds
    target: Optional[str] = None
    motion: str = "left_to_right"
    intensity: str = "medium"
    role: str = "primary"  # primary | secondary


class CameraSpec(BaseModel):
    """Cinematic camera movement specification."""
    shot: str = "medium"
    move: str = "slow_push_in"


class DirectorBeat(BaseModel):
    """B3 Director Plan beat combining B2 verbatim narration with visual specifications."""
    beat_id: str
    narration: str
    narration_sha1: str
    headline: str = ""
    visual_metaphor: str = ""
    image_prompt: str
    objects: List[ObjectSpec] = Field(default_factory=list)
    actions: List[ActionSpec] = Field(default_factory=list)
    camera: CameraSpec = Field(default_factory=CameraSpec)
    i2v_prompt_omni: str = ""
    i2v_prompt_google_flow: str = ""
    duration_s: float = 6.0


def segment_ja(text: str) -> List[str]:
    """Segment Japanese text by sentence terminators (。！？\n) respecting quotes (「」『』（）)."""
    norm = unicodedata.normalize("NFKC", text).strip()
    if not norm:
        return []

    sentences: List[str] = []
    current: List[str] = []
    quote_depth = 0

    open_quotes = {"「", "『", "（", "(", "“"}
    close_quotes = {"」", "』", "）", ")", "”"}
    terminators = {"。", "！", "？", "!", "?"}

    for char in norm:
        current.append(char)
        if char in open_quotes:
            quote_depth += 1
        elif char in close_quotes:
            quote_depth = max(0, quote_depth - 1)
        elif char in terminators and quote_depth == 0:
            s_str = "".join(current).strip()
            if s_str:
                sentences.append(s_str)
            current = []

    if current:
        trailing = "".join(current).strip()
        if trailing:
            sentences.append(trailing)

    return sentences


def segment_multilingual(text: str, market: str = "JA") -> List[str]:
    """Domain and market adaptive sentence segmentation."""
    m_up = (market or "JA").upper()
    if m_up in {"JA", "JP"}:
        return segment_ja(text)
    
    # Generic Latin / CJK segmentation
    norm = unicodedata.normalize("NFKC", text).strip()
    # Split by standard sentence delimiters
    raw_parts = re.split(r"(?<=[.!?。！？])\s+", norm)
    result = [p.strip() for p in raw_parts if p.strip()]
    if not result and norm:
        result = [norm]
    return result


def load_spoken_script(
    target_dir: Union[str, Path],
    episode_id: Optional[str] = None,
    market: str = "JA"
) -> SpokenScript:
    """Strictly loads B2 spoken script from an episode directory.
    
    Tries in priority order:
    1. spoken_sentences.json (Pre-split sentences from story_engine_b2)
    2. spoken_script.txt (Verbatim full spoken narration)
    3. b2_script.json (Structured B2 output)
    4. brain_input.json (Orchestrator seed)
    5. story.txt (Raw 5-Act story text)

    Raises:
        B2ContractError: If no valid non-empty script is found. (Rule 118 Zero-Mock).
    """
    p = Path(target_dir).resolve()
    ep_id = episode_id or p.name

    chosen_file: Optional[Path] = None
    raw_text: str = ""
    candidate_sentences: List[str] = []

    # 1. Try spoken_sentences.json
    s_json_path = p / "spoken_sentences.json"
    if s_json_path.is_file():
        try:
            content = s_json_path.read_text(encoding="utf-8").strip()
            if content.startswith("```"):
                content = re.sub(r"^`+[a-zA-Z]*\n?|`+$", "", content).strip()
            parsed = json.loads(content)
            if isinstance(parsed, list) and len(parsed) > 0:
                for item in parsed:
                    if isinstance(item, dict) and item.get("text"):
                        txt = str(item["text"]).strip()
                        if txt:
                            candidate_sentences.append(txt)
                    elif isinstance(item, str) and item.strip():
                        candidate_sentences.append(item.strip())
                if candidate_sentences:
                    chosen_file = s_json_path
                    raw_text = "\n".join(candidate_sentences)
        except Exception as err:
            logger.debug(f"Notice reading spoken_sentences.json: {err}")

    # 2. Try spoken_script.txt
    if not candidate_sentences:
        s_txt_path = p / "spoken_script.txt"
        if s_txt_path.is_file():
            content = s_txt_path.read_text(encoding="utf-8").strip()
            if content:
                chosen_file = s_txt_path
                raw_text = content
                candidate_sentences = segment_multilingual(content, market=market)

    # 3. Try b2_script.json
    if not candidate_sentences:
        b2_json_path = p / "b2_script.json"
        if b2_json_path.is_file():
            try:
                content = b2_json_path.read_text(encoding="utf-8").strip()
                if content.startswith("```"):
                    content = re.sub(r"^`+[a-zA-Z]*\n?|`+$", "", content).strip()
                b2_data = json.loads(content)
                script_txt = (
                    b2_data.get("full_spoken_script")
                    or b2_data.get("spoken_script")
                    or b2_data.get("script")
                )
                if script_txt and str(script_txt).strip():
                    chosen_file = b2_json_path
                    raw_text = str(script_txt).strip()
                    candidate_sentences = segment_multilingual(raw_text, market=market)
            except Exception as err:
                logger.debug(f"Notice reading b2_script.json: {err}")

    # 4. Try brain_input.json
    if not candidate_sentences:
        b_input_path = p / "brain_input.json"
        if b_input_path.is_file():
            try:
                content = b_input_path.read_text(encoding="utf-8").strip()
                b_data = json.loads(content)
                script_txt = (
                    b_data.get("spoken_script")
                    or b_data.get("story")
                )
                if script_txt and str(script_txt).strip():
                    chosen_file = b_input_path
                    raw_text = str(script_txt).strip()
                    candidate_sentences = segment_multilingual(raw_text, market=market)
            except Exception as err:
                logger.debug(f"Notice reading brain_input.json: {err}")

    # 5. Try story.txt
    if not candidate_sentences:
        story_txt_path = p / "story.txt"
        if story_txt_path.is_file():
            content = story_txt_path.read_text(encoding="utf-8").strip()
            if content:
                chosen_file = story_txt_path
                raw_text = content
                candidate_sentences = segment_multilingual(content, market=market)

    # Strict Validation (Zero-Mock Mandate): Fail Loud!
    if not chosen_file or not candidate_sentences:
        raise B2ContractError(
            f"Zero-Mock Violation: No valid B2 spoken script found in '{p}'. "
            f"Looked for: spoken_sentences.json, spoken_script.txt, b2_script.json, brain_input.json, story.txt. "
            f"Pipeline cannot proceed with mock data."
        )

    # Compute source sha256
    file_bytes = chosen_file.read_bytes()
    source_sha256 = hashlib.sha256(file_bytes).hexdigest()

    # Build beats
    beats: List[SpokenBeat] = []
    for idx, s_text in enumerate(candidate_sentences, start=1):
        clean_s = s_text.strip()
        if clean_s:
            b_id = f"b{idx:02d}"
            beats.append(SpokenBeat.create(beat_id=b_id, text=clean_s, beat_index=idx))

    if not beats:
        raise B2ContractError(
            f"Zero-Mock Violation: B2 script in '{chosen_file}' yielded 0 non-empty beats."
        )

    return SpokenScript(
        episode_id=ep_id,
        source_path=str(chosen_file.resolve()),
        source_sha256=source_sha256,
        total_beats=len(beats),
        beats=beats
    )
