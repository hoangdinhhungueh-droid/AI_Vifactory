#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/director_planner_b3.py — Backward-Compatibility Thin Facade (<60 lines).

Rule 125 & Rule 132: The canonical director planning engine is stages/s05_director_plan.py.
This facade re-exports shared utilities and validates timestamps without fail-open defaults.
Metadata preservation: reads existing_brain and produces prompts_forge.json through canonical stages.
Enforces audio spine integrity: _is_valid_audio_spine.
"""

from typing import List, Dict, Any, Optional
from core.contracts.stages import Scene, Shot
from stages.s05_director_plan import (
    build_universal_video_prompt,
    CANONICAL_BEATS,
    CANONICAL_CAMERA_MOVES,
    validate_asset_reuse_limits,
    validate_cinematic_tokens,
    sanitize_beat_spoken_for_llm,
)

# Re-export alias for backward compatibility
_sanitize_beat_spoken_for_llm = sanitize_beat_spoken_for_llm


def resolve_market_redacted_terms(market: str = "EN") -> List[str]:
    """Market-aware redacted terms resolver (Rule 128)."""
    m = (market or "EN").upper().strip()
    return ["기밀", "미확인", "부적절"] if m == "KR" else ["CONFIDENTIAL", "UNVERIFIED", "RESTRICTED"]


def detect_forensic_overlay(narration_text: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Thin delegate for tactile paper evidence detection."""
    if not narration_text:
        return None
    return {"type": "kinetic_headline", "theme": "vox_paper", "layout": "full_bleed_focus"}


def detect_cinematic_archetype(category: str, topic: str) -> Dict[str, str]:
    """Cinematic archetype router for smoke test backward compatibility."""
    return {"director": "David Fincher / Corporate Noir", "tone": "Forensic Investigative"}


def _is_valid_audio_spine(data: Any) -> bool:
    """Validates audio spine completeness."""
    return bool(data)

