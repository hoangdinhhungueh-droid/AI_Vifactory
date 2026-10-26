#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/contracts/stages.py — Canonical Data Contracts for AI Video Factory (AVF-STAB-001).

Governed by Pydantic v2 with extra='forbid' to eliminate F1 (Contract Drift).
Standardizes the single canonical vocabulary: Scene (narrative) ⊃ Shot (generation).
"""

from __future__ import annotations

import datetime
import math
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class StageID(str, Enum):
    """The 11 Canonical Stages of the AI Video Factory Pipeline."""
    S1_IDEATION = "s01_ideation"
    S2_RESEARCH = "s02_research"
    S3_SCRIPT = "s03_script"
    S4_CRITIC_SCRIPT = "s04_critic_script"
    S5_DIRECTOR_PLAN = "s05_director_plan"
    S6_CRITIC_VISUAL = "s06_critic_visual"
    S7_IMAGE_GEN = "s07_image_gen"
    S8_VIDEO_GEN = "s08_video_gen"
    S9_VOICE_TTS = "s09_voice_tts"
    S10_RENDER = "s10_render"
    S11_QC = "s11_qc"


class Provenance(BaseModel):
    """Metadata regarding how an artifact was generated."""
    model_config = ConfigDict(extra="forbid")

    generator: str = Field(description="Script, module, or model that produced this artifact")
    model_name: Optional[str] = None
    prompt_id: Optional[str] = None
    cost_usd: float = 0.0
    latency_sec: float = 0.0
    total_tokens: int = 0


# ==============================================================================
# CANONICAL GENERATION OBJECTS
# ==============================================================================

class WhisperWord(BaseModel):
    """Word-level Whisper timestamp contract with strict validation (Rule 120, 135)."""
    model_config = ConfigDict(extra="ignore")

    word: str
    start: float = Field(ge=0.0, description="Word start timestamp in seconds")
    end: float = Field(ge=0.0, description="Word end timestamp in seconds")
    probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_monotonic_word(self) -> "WhisperWord":
        if math.isnan(self.start) or math.isnan(self.end) or math.isinf(self.start) or math.isinf(self.end):
            raise ValueError("WhisperWord timestamps cannot be NaN or Inf")
        if self.end < self.start:
            raise ValueError(f"WhisperWord end ({self.end}) cannot precede start ({self.start})")
        return self


class BoundingBox(BaseModel):
    """Spatial 2D bounding box percentage coordinates (0.0 to 100.0) for kinematic targeting (Rule 128, 132)."""
    model_config = ConfigDict(extra="ignore")

    x_min: float = Field(ge=0.0, le=100.0)
    x_max: float = Field(ge=0.0, le=100.0)
    y_min: float = Field(ge=0.0, le=100.0)
    y_max: float = Field(ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if math.isnan(self.x_min) or math.isnan(self.x_max) or math.isnan(self.y_min) or math.isnan(self.y_max):
            raise ValueError("BoundingBox coordinates cannot be NaN")
        if self.x_max <= self.x_min:
            raise ValueError(f"x_max ({self.x_max}) must be strictly greater than x_min ({self.x_min})")
        if self.y_max <= self.y_min:
            raise ValueError(f"y_max ({self.y_max}) must be strictly greater than y_min ({self.y_min})")
        return self


class Shot(BaseModel):
    """Atomic video generation unit passed to Google Flow (I2V / T2V)."""
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(description="e.g. sc_01_sh_01")
    scene_id: str = Field(description="e.g. SCENE_01")
    visual_prompt: str = Field(description="Universal Video Prompt for Google Flow")
    negative_prompt: Optional[str] = None
    seed_image: Optional[str] = Field(default=None, description="Path or filename of composite seed image")
    duration_sec: float = 10.0
    aspect: Literal["16:9", "9:16", "1:1"] = "16:9"
    account_slot: Optional[str] = Field(default=None, description="acc_01 .. acc_07")
    start_frame_id: Optional[str] = None
    end_frame_id: Optional[str] = None
    previous_shot_id: Optional[str] = None
    uses_previous_end_frame: bool = False
    camera_directive: Optional[str] = None
    second_by_second_action_breakdown: Optional[List[Dict[str, Any]]] = None


class Scene(BaseModel):
    """Canonical narrative beat in 5-Beat Docudrama structure."""
    model_config = ConfigDict(extra="ignore")

    scene_id: str = Field(description="e.g. SCENE_01")
    sequence_block: str = Field(default="BLOCK_DEFAULT", description="e.g. block_1_act_i")
    beat_role: Literal["hook", "context", "tension", "reveal", "payoff", "outro"] = "context"
    narration: str = Field(description="Final voiceover narration text")
    market: str = Field(default="EN", description="Canonical market code: EN, JA, KR, VN (Rule 128, 134)")
    core_idea: Optional[str] = None
    headline: Optional[str] = Field(default=None, description="1-4 word editorial headline")
    visual_metaphor: Optional[str] = None
    color_accent: Optional[str] = None
    duration_est_sec: float = 5.0
    shots: List[Shot] = Field(default_factory=list)

    # Vox Kinematic & Object-Assembly Decomposition (AVF-VOX-001)
    canvas_workspace: Optional[str] = None
    hero_cutout_object: Optional[str] = None
    interacting_objects: Optional[List[str]] = Field(default_factory=list)
    motion_track_and_assembly: Optional[Dict[str, Any]] = None
    graphic_typography: Optional[Dict[str, Any]] = None
    visual_continuity_link_to_next: Optional[str] = None
    objects: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    actions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    camera_move: Optional[str] = None
    image_prompt: Optional[str] = None
    i2v_prompt_omni: Optional[str] = None
    i2v_prompt_google_flow: Optional[str] = None
    second_by_second_action_breakdown: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    camera_directive: Optional[str] = None
    objects_roster: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    headline_typography: Optional[Dict[str, Any]] = None
    audio_foley_cues: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    whisper_words: Optional[List[WhisperWord]] = Field(default=None, description="Whisper word-level timestamps (Rule 120)")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Spatial bounding box for kinematic targeting")
    object_roles: Optional[Dict[str, str]] = Field(default=None, description="Mapping of object IDs to semantic roles")


class Chunk(BaseModel):
    """Thematic Sequence Block Partition for 8-10 minute documentary."""
    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    start_s: float
    end_s: float
    duration_s: float
    shot_ids: List[str] = Field(default_factory=list)
    scene_ids: List[str] = Field(default_factory=list)
    boundary_reason: str = "scene_boundary"


class AssetRegistryItem(BaseModel):
    """Canonical Unique Asset item (18-24 bounded set per episode)."""
    model_config = ConfigDict(extra="ignore")

    asset_id: str
    asset_type: str
    name: str
    description: str = ""
    visual_attributes: Dict[str, Any] = Field(default_factory=dict)
    texture_spec: Optional[str] = None
    source_uri: Optional[str] = None
    chroma_prompt: Optional[str] = None
    used_by_shot_ids: List[str] = Field(default_factory=list)
    used_by_scene_ids: List[str] = Field(default_factory=list)
    status: str = "ready"


class AssetRegistry(BaseModel):
    """Master Asset Registry for 8-10 minute documentary (18-24 items)."""
    model_config = ConfigDict(extra="ignore")

    schema_version: str = "asset_registry.v2"
    project_id: str
    items: List[AssetRegistryItem] = Field(default_factory=list)


class VideoAsset(BaseModel):
    """Validated raw MP4 clip generated by Google Flow."""
    model_config = ConfigDict(extra="forbid")

    shot_id: str
    scene_id: str
    file_path: str
    account_slot: str
    duration_sec: float
    size_bytes: int
    sha256: str
    verified: bool = True


# ==============================================================================
# CRITIC COUNCIL CONTRACTS
# ==============================================================================

class CriticIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    severity: Literal["blocker", "major", "minor"]
    description: str
    target_scene_id: Optional[str] = None


class CriticVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    critic_id: str  # e.g. "GPT-6-Astra" or "Claude-Opus-5.5"
    role: str
    score: float = Field(ge=0.0, le=10.0)
    verdict: Literal["pass", "revise", "reject"]
    feedback: List[str] = Field(default_factory=list)
    issues: List[CriticIssue] = Field(default_factory=list)


class CouncilDecision(BaseModel):
    """HHTech Dual-LLM Critic Council decision."""
    model_config = ConfigDict(extra="forbid")
    round_number: int = 1
    max_rounds: int = 2
    verdict: Literal["pass", "revise", "reject"]
    aggregate_score: float = Field(ge=0.0, le=10.0)
    verdicts: List[CriticVerdict] = Field(default_factory=list)
    revision_directives: List[str] = Field(default_factory=list)


# ==============================================================================
# GENERIC STAGE ENVELOPE
# ==============================================================================

class StageArtifact(BaseModel):
    """Strict envelope for every artifact generated between pipeline stages."""
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    run_id: str
    stage: StageID
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    status: Literal["ok", "partial", "failed"] = "ok"
    payload: Dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
