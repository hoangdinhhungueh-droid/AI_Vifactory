#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/director_planner_b3.py — Backward-Compatibility Thin Facade (<50 lines).

Rule 125 & Rule 132: The canonical director planning engine is stages/s05_director_plan.py.
This facade re-exports shared utilities and validates timestamps without fail-open defaults.
"""

from typing import List, Dict, Any, Optional
from core.contracts.stages import Scene, Shot
from stages.s05_director_plan import build_universal_video_prompt


def resolve_market_redacted_terms(market: str = "EN") -> List[str]:
    """Market-aware redacted terms resolver (Rule 128)."""
    m = (market or "EN").upper().strip()
    return ["기밀", "미확인", "부적절"] if m == "KR" else ["CONFIDENTIAL", "UNVERIFIED", "RESTRICTED"]


def detect_forensic_overlay(narration_text: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Thin delegate for tactile paper evidence detection."""
    if not narration_text:
        return None
    return {"type": "kinetic_headline", "theme": "vox_paper", "layout": "full_bleed_focus"}


def _sanitize_beat_spoken_for_llm(spoken_list: list) -> list:
    """Sanitizes spoken sentences; strictly rejects invalid end <= start (Rule 118 & 120)."""
    if not spoken_list:
        return []
    lean = []
    for s in spoken_list:
        if not isinstance(s, dict):
            continue
        duration_s = s.get("duration_sec")
        if duration_s is None:
            start, end = s.get("start", 0), s.get("end", 0)
            if end <= start:
                raise ValueError(f"Invalid sentence timestamp: end ({end}) <= start ({start}) violates Rule 118 & Rule 120")
            duration_s = round(end - start, 2)
        elif duration_s <= 0:
            raise ValueError(f"Invalid duration_sec ({duration_s}) <= 0 violates Rule 118")
        lean.append({"sentence_id": s.get("sentence_id") or f"sent_{len(lean)+1:03d}", "text": s.get("text", ""), "duration_sec": duration_s, "beat_index": s.get("beat_index", 1)})
    return lean
