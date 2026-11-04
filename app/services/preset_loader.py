#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/preset_loader.py — Pipeline Preset Loader & Validator.

Enforces:
- Rule 128: Generic Contract Pattern (preset-driven architecture).
- Rule 134: Single Canonical Truth & Parity.
- Strict Pydantic validation: sum of beat shares == 1.0, duration bounds, hex color validation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Resolution(BaseModel):
    model_config = ConfigDict(extra="ignore")
    width: int = 1920
    height: int = 1080


class DurationWindow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min: float
    max: float
    target: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "DurationWindow":
        if not (self.min < self.target < self.max):
            raise ValueError(
                f"Duration bounds invalid: min ({self.min}) < target ({self.target}) < max ({self.max}) not satisfied"
            )
        return self


class WordBudget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min: int
    max: int

    @model_validator(mode="after")
    def validate_bounds(self) -> "WordBudget":
        if self.min >= self.max:
            raise ValueError(
                f"Word budget min ({self.min}) must be strictly less than max ({self.max})"
            )
        return self


class NarrationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    wpm_estimate: float = 125.0
    word_budget: WordBudget


class BeatConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    share: float
    intent: Optional[str] = None


class RetentionConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pattern_interrupt_max_gap_s: float = 30.0
    max_consecutive_same_h_family: int = 2


class PaletteConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    paper: str = "#F4F1EA"

    @field_validator("paper")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError(f"Invalid hex color code: '{v}'. Must match #RRGGBB.")
        return v


class VisualConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    palette: PaletteConfig = Field(default_factory=PaletteConfig)
    tactile_props: List[str] = Field(
        default_factory=lambda: ["newspaper_cutout", "stamp", "compass", "ruler"]
    )
    shot_avg_s: float = 5.5
    veo_share_max: float = 0.30
    forbid_photoreal_real_persons: bool = True


class LegalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    required_status_language: Dict[str, List[str]] = Field(default_factory=dict)
    min_independent_sources: int = 3


class TTSConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    voice: str = "en-US-ChristopherNeural"
    rate: str = "+0%"


class Preset(BaseModel):
    """Authoritative Pydantic model for Pipeline Presets."""
    model_config = ConfigDict(extra="ignore")

    name: str
    aspect_ratio: str = "16:9"
    market: str = "EN"
    resolution: Resolution = Field(default_factory=Resolution)
    duration_window_s: DurationWindow
    narration: NarrationConfig
    beats: List[BeatConfig]
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    visual: VisualConfig = Field(default_factory=VisualConfig)
    legal: LegalConfig = Field(default_factory=LegalConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)

    @model_validator(mode="after")
    def validate_shares(self) -> "Preset":
        total_share = sum(b.share for b in self.beats)
        if abs(total_share - 1.0) > 0.001:
            raise ValueError(
                f"Sum of beat shares must equal 1.0 (got {total_share:.4f})"
            )
        return self


def load_preset(name_or_path: str, repo_root: Optional[Path] = None) -> Preset:
    """Loads and validates a pipeline preset by name or file path."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent

    candidate = Path(name_or_path)
    file_path: Optional[Path] = None

    if candidate.is_file():
        file_path = candidate
    elif (repo_root / candidate).is_file():
        file_path = repo_root / candidate
    else:
        # Strip .yaml/.yml extension if provided in preset name
        clean_name = str(name_or_path).strip()
        if clean_name.lower().endswith(".yaml"):
            clean_name = clean_name[:-5]
        elif clean_name.lower().endswith(".yml"):
            clean_name = clean_name[:-4]

        presets_dir = repo_root / "config" / "presets"
        cand_yaml = presets_dir / f"{clean_name}.yaml"
        cand_yml = presets_dir / f"{clean_name}.yml"
        if cand_yaml.exists():
            file_path = cand_yaml
        elif cand_yml.exists():
            file_path = cand_yml

    if file_path is None or not file_path.exists():
        raise FileNotFoundError(
            f"Preset file not found for '{name_or_path}' (searched in {repo_root / 'config' / 'presets'})"
        )

    raw_data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise ValueError(f"Preset file at {file_path} did not parse into a dictionary.")

    return Preset.model_validate(raw_data)


def list_available_presets(repo_root: Optional[Path] = None) -> List[str]:
    """Lists available preset names in config/presets/."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent

    presets_dir = repo_root / "config" / "presets"
    if not presets_dir.exists():
        return []

    return [p.stem for p in presets_dir.glob("*.yaml")] + [p.stem for p in presets_dir.glob("*.yml")]
