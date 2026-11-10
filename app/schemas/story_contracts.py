#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/schemas/story_contracts.py — Data Contracts for Story-Driven Forensic Business Pipeline.

Governed by Pydantic v2. Provides strict schemas for S1 through S6 while preserving
backward compatibility for existing macro_legacy payloads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# S1: IDEATION CONTRACTS
# ==============================================================================

class Antagonist(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    type: Literal["person", "company", "state"] = "company"


class SourceSeed(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str
    type: Literal["court", "regulator", "gov", "press"] = "press"


class StoryScore(BaseModel):
    model_config = ConfigDict(extra="ignore")
    conflict: float = 0.0
    mechanism_clarity: float = 0.0
    twist: float = 0.0
    documentation: float = 0.0


class StoryIdeationPayload(BaseModel):
    """S1 Ideation Payload Contract."""
    model_config = ConfigDict(extra="ignore")

    preset: str = "story_forensic"
    niche: Literal["business_heist", "corporate_scandal", "geopolitical_anomaly"] = "corporate_scandal"
    title_working: str = ""
    central_question: str = ""
    antagonist: Optional[Antagonist] = None
    scheme_mechanism_summary: str = ""
    money_at_stake_usd: float = 0.0
    documented_outcome: str = ""
    source_seeds: List[SourceSeed] = Field(default_factory=list)
    story_score: StoryScore = Field(default_factory=StoryScore)

    # Legacy fields
    task_id: Optional[str] = None
    market: Optional[str] = "EN"
    raw_term: Optional[str] = None
    topic: Optional[str] = None
    viability_score: Optional[float] = None
    angle_brief: Optional[str] = None
    status: Optional[str] = "APPROVED"


# ==============================================================================
# S2: RESEARCH & EVIDENCE CONTRACTS
# ==============================================================================

class EvidenceClaim(BaseModel):
    """Forensic evidence claim anchored in primary documents or reputable press."""
    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(description="e.g. C001, C002")
    claim: str
    source_url: str
    source_type: Literal["court", "regulator", "gov", "press"] = "press"
    date: Optional[str] = None
    legal_status: Literal["convicted", "charged", "alleged", "settled", "fact"] = "alleged"
    confidence: Literal["high", "medium", "low"] = "high"


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: str
    event: str
    claim_ids: List[str] = Field(default_factory=list)


class StoryResearchPayload(BaseModel):
    """S2 Research & Grounding Payload Contract."""
    model_config = ConfigDict(extra="ignore")

    preset: str = "story_forensic"
    topic: str = ""
    evidence_ledger: List[EvidenceClaim] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)

    # Legacy fields
    task_id: Optional[str] = None
    market: Optional[str] = "EN"
    factsheet: Optional[Dict[str, Any]] = None
    competitor_vacuums: Optional[List[str]] = None
    status: Optional[str] = "APPROVED"


# ==============================================================================
# S3: 5-BEAT SCRIPT CONTRACTS
# ==============================================================================

class StorySceneLine(BaseModel):
    """Atomic narration line with claim anchoring and physical hook."""
    model_config = ConfigDict(extra="ignore")

    line_id: str = Field(description="e.g. B1_L01, B3_L04")
    text: str
    claim_ids: List[str] = Field(default_factory=list)
    visual_hook: Optional[str] = Field(
        default=None,
        description="stamp | ruler_measure | compass_arc | cutout | none"
    )


class StoryScriptBeat(BaseModel):
    """Canonical Beat in 5-Beat Story Structure."""
    model_config = ConfigDict(extra="ignore")

    beat_id: str = Field(description="B1_hook | B2_setup | B3_scheme | B4_crack | B5_aftermath")
    target_duration_s: float = 0.0
    lines: List[StorySceneLine] = Field(default_factory=list)
    word_count: int = 0


class StoryScriptPayload(BaseModel):
    """S3 Script Payload Contract."""
    model_config = ConfigDict(extra="ignore")

    preset: str = "story_forensic"
    topic: str = ""
    total_words: int = 0
    est_duration_s: float = 0.0
    beats: List[StoryScriptBeat] = Field(default_factory=list)

    # Canonical Scene compatibility for downstream stages
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    total_scenes: Optional[int] = None
    script_text: Optional[str] = None
    evidence_ledger: Optional[List[EvidenceClaim]] = None


# ==============================================================================
# S4: SCRIPT CRITIC CONTRACTS
# ==============================================================================

class StoryScriptCriticGates(BaseModel):
    model_config = ConfigDict(extra="ignore")

    duration_estimate_in_window: bool = True
    every_factual_line_has_claim_id: bool = True
    legal_language_matches_status: bool = True
    hook_within_20s: bool = True
    pattern_interrupt_gap_ok: bool = True
    target_market_language_compliance: bool = True


class StoryCriticViolation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_id: Optional[str] = None
    gate: str
    detail: str


class StoryScriptCriticPayload(BaseModel):
    """S4 Script Critic Council Payload Contract."""
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["pass", "fail", "revise"] = "pass"
    gates: StoryScriptCriticGates = Field(default_factory=StoryScriptCriticGates)
    violations: List[StoryCriticViolation] = Field(default_factory=list)
    aggregate_score: float = 9.0


# ==============================================================================
# S5: DIRECTOR PLAN CONTRACTS
# ==============================================================================

class StoryShotPlan(BaseModel):
    """Atomic shot plan from Director S5."""
    model_config = ConfigDict(extra="ignore")

    shot_id: str = Field(description="e.g. S001, S023")
    line_ids: List[str] = Field(default_factory=list)
    start_hint_s: float = 0.0
    duration_s: float = 5.5
    render_mode: Literal["veo", "vox_native"] = "veo"
    h_family: str = Field(default="H1_IMPACT", description="H1..H7 kinetic family")
    tactile_props: List[str] = Field(default_factory=list)
    prompt: str = ""
    contains_real_person: bool = False


# ==============================================================================
# S6: VISUAL CRITIC CONTRACTS
# ==============================================================================

class StoryVisualCriticGates(BaseModel):
    model_config = ConfigDict(extra="ignore")

    palette_locked: bool = True
    no_photoreal_real_person: bool = True
    h_family_variety: bool = True
    veo_share: bool = True
    aspect_16_9: bool = True


class StoryVisualCriticPayload(BaseModel):
    """S6 Visual Critic Council Payload Contract."""
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["pass", "fail", "revise"] = "pass"
    gates: StoryVisualCriticGates = Field(default_factory=StoryVisualCriticGates)
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    aggregate_score: float = 9.0
