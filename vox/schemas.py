#!/usr/bin/env python3
"""vox/schemas.py — Typed Pydantic Contracts for Unified Vox Pipeline (AVF-VOX-001).

Implements strict validation for:
- 12 Canonical Camera Moves
- Foreground Objects (FGObject with anchors, scale, depth, enter_at)
- Scene (BG prompt, 1-3 FG objects, camera move, timestamps)
- ScenePlan (with no consecutive duplicate camera moves validator)
- Word & WordTimeline (for word-level subtitle alignment)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class CameraMove(str, Enum):
    STATIC_BREATH = "static_breath"      # zoom 1.00 -> 1.03
    PUSH_IN = "push_in"                  # zoom 1.00 -> 1.20
    PULL_OUT = "pull_out"                # zoom 1.20 -> 1.00
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    KEN_BURNS_TL_BR = "ken_burns_tl_br"  # zoom + diagonal
    KEN_BURNS_BR_TL = "ken_burns_br_tl"
    PARALLAX_LEFT = "parallax_left"      # BG slow, FG fast based on depth
    PARALLAX_RIGHT = "parallax_right"
    ROLL_PUSH = "roll_push"              # zoom 1.0 -> 1.15 + roll +-2 deg


class FGObject(BaseModel):
    id: str
    prompt: str = Field(min_length=10)
    anchor_x: float = Field(ge=0.0, le=1.0)   # center coordinate normalized
    anchor_y: float = Field(ge=0.0, le=1.0)
    scale: float = Field(ge=0.1, le=0.8)      # FG size relative to canvas height
    depth: float = Field(ge=0.0, le=1.0)      # 0 = close to BG, 1 = close to camera
    enter_at: float = Field(ge=0.0)           # seconds relative to scene start


class Scene(BaseModel):
    idx: int
    narration: str = Field(min_length=1)
    bg_prompt: str = Field(min_length=10)     # requirements: background without main subject
    fg: list[FGObject] = Field(min_length=1, max_length=3)
    camera: CameraMove
    start: float | None = None             # filled by align.py
    end: float | None = None


class ScenePlan(BaseModel):
    title: str
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def _camera_variety(self) -> ScenePlan:
        # Prevent 2 consecutive scenes from using the exact same camera move
        for a, b in zip(self.scenes, self.scenes[1:]):
            if a.camera == b.camera:
                raise ValueError(f"scene {a.idx}/{b.idx} duplicate camera move: {a.camera}")
        return self


class Word(BaseModel):
    text: str           # taken from original script, not Whisper
    start: float
    end: float
    scene_idx: int
    probability: float = 1.0


class WordTimeline(BaseModel):
    words: list[Word]
    audio_duration: float
    match_ratio: float  # token match ratio between script and Whisper
