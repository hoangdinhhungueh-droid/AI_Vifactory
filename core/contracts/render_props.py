#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/contracts/render_props.py — Remotion Master Render Props Contract.

Single Source of Truth between Python Post-Production and TypeScript Remotion.
Exportable to JSON Schema and Zod type in remotion/src/generated/props.ts.
Enforces Rule 128 (Generic Contract) and Rule 140 (Kinetic Coupling).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KaraokeWord(BaseModel):
    """Word-level timestamp for Remotion karaoke subtitles."""
    model_config = ConfigDict(extra="allow")
    word: str
    start: float  # In seconds
    end: float    # In seconds
    start_ms: Optional[float] = None
    end_ms: Optional[float] = None


class SceneRenderProp(BaseModel):
    """Single Scene render specification for Remotion (Master Scene Sheet & Web Forensics)."""
    model_config = ConfigDict(extra="ignore")
    scene_id: str
    duration_in_frames: int
    video_clip_path: Optional[str] = None
    audio_path: Optional[str] = None
    subtitles: List[KaraokeWord] = Field(default_factory=list)
    headline: Optional[str] = None
    bilingual_headline: Optional[str] = None
    color_accent: Optional[str] = None
    render_mode: Optional[str] = "vox_native"
    h_family: Optional[str] = None
    tactile_props: List[str] = Field(default_factory=list)
    narration: Optional[str] = None

    # Master Scene Sheet 3-Layer Fields
    background_desk_path: Optional[str] = None
    hero_cutout_path: Optional[str] = None
    supporting_cutout_paths: List[str] = Field(default_factory=list)
    forensic_web_clip_path: Optional[str] = None
    stamp_badge_text: Optional[str] = None
    highlighter_target_text: Optional[str] = None
    highlighter_start_frame: Optional[int] = None
    motion_thumbnail_code: Optional[str] = "top_down_tracking"
    stop_motion_fps: int = 12
    production_route: Optional[str] = "REMOTION_COLLAGE_MOTION"
    causal_handoff: Optional[Dict[str, Any]] = None
    atmosphere: Optional[Dict[str, Any]] = None
    desk_station_coords: Optional[List[int]] = None


class RemotionRenderProps(BaseModel):
    """Full input props object injected into Remotion composition."""
    model_config = ConfigDict(extra="ignore")
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
    preset: Optional[str] = None
