#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/contracts/render_props.py — Remotion Master Render Props Contract.

Single Source of Truth between Python Post-Production and TypeScript Remotion.
Exportable to JSON Schema and Zod type in remotion/src/generated/props.ts.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class KaraokeWord(BaseModel):
    """Word-level timestamp for Remotion karaoke subtitles."""
    model_config = ConfigDict(extra="forbid")
    word: str
    start: float  # In seconds
    end: float    # In seconds


class SceneRenderProp(BaseModel):
    """Single Scene render specification for Remotion."""
    model_config = ConfigDict(extra="forbid")
    scene_id: str
    duration_in_frames: int
    video_clip_path: str
    audio_path: Optional[str] = None
    subtitles: List[KaraokeWord] = Field(default_factory=list)
    headline: Optional[str] = None
    bilingual_headline: Optional[str] = None
    color_accent: Optional[str] = None


class RemotionRenderProps(BaseModel):
    """Full input props object injected into Remotion composition."""
    model_config = ConfigDict(extra="forbid")
    episode_id: str
    title: str
    fps: int = 30
    width: int = 1920
    height: int = 1080
    duration_in_frames: int
    scenes: List[SceneRenderProp]
    bgm_path: Optional[str] = None
    bgm_volume: float = 0.15
    audio_spine_path: Optional[str] = None
