#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/config.py — Profile Configuration & RunContext Engine (AVF-STAB-001).

Loads YAML profiles (prod.yaml, e2e_min.yaml) into strictly validated Pydantic models.
Eliminates scattered os.getenv calls across stage modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from core.paths import RunPaths
from core.run_manifest import RunManifest


class LimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_scenes: int = 0
    max_blocks: int = 0
    critic_max_rounds: int = 2


class VideoGenConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: Literal["omni", "veo"] = "omni"
    aspect: Literal["16:9", "9:16", "1:1"] = "16:9"
    duration_per_clip_sec: float = 10.0
    account_pool: List[str] = Field(default_factory=lambda: ["acc_01"])
    circuit_breaker_threshold: int = 7


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tts_engine: str = "edge_tts"
    voice_en: str = "en-US-ChristopherNeural"
    voice_kr: str = "ko-KR-InJoonNeural"
    voice_jp: str = "ja-JP-KeitaNeural"
    voice_vn: str = "vi-VN-NamMinhNeural"


class RenderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    engine: str = "remotion"
    fps: int = 30
    width: int = 1920
    height: int = 1080
    bgm_volume: float = 0.15


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    pipeline_version: str = "2.0.0"
    market: Optional[str] = None
    limits: LimitsConfig
    video_generation: VideoGenConfig
    voice: VoiceConfig
    render: RenderConfig


class RunContext(BaseModel):
    """The canonical execution context passed to every Stage's run() method."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    run_id: str
    paths: RunPaths
    manifest: RunManifest
    config: PipelineConfig
    force: bool = False
    dry_run: bool = False


def load_profile(profile_name: str = "prod", repo_root: Optional[Path] = None) -> PipelineConfig:
    """Loads and validates a profile YAML file from config/profiles/."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    profile_file = repo_root / "config" / "profiles" / f"{profile_name}.yaml"
    if not profile_file.exists():
        raise FileNotFoundError(f"Profile configuration file not found: {profile_file}")

    raw_data = yaml.safe_load(profile_file.read_text(encoding="utf-8"))
    return PipelineConfig.model_validate(raw_data)
