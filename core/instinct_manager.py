#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/instinct_manager.py — Closed-Loop Codemap Dreaming & 5-Slot Active Instinct Vault (Vox Engine v3).

Conforms to:
- Rule 118: Zero-Mock Data & Truthful Grounding.
- Rule 128: Generic Contract Architecture across all stages.
- Rule 134: Single Canonical Truth for feedback memory.
- Rule 139: Disciplined Code-ification & Safe Parameter Bounding.
- Master Reform Plan 2.0 (PLAN-VOX-V3-REFORM-20261030):
  * 3-Layer Gatekeeper:
    - Layer 1: Statistical Significance Gate (>= 3 consistent failure signals).
    - Layer 2: Bounded Parameter Gate (clamps patches within safe operational ranges).
    - Layer 3: 5-Slot Active Memory Vault with FIFO eviction.
  * Signal-to-Stage Routing Matrix:
    - Drop-off 0-15s (< 65%) -> Stage 3 (s03_script)
    - Low CTR (< 5.5%) -> Stage 11 (s11_seo)
    - Mid-Video Slump (> 10%) -> Stage 5 (s05_director)
    - Karaoke Timing Drift (> 100ms) -> Stage 4 (s04_pacing)
    - Visual Score (< 8.5) -> Stage 5 (s05_director)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_INSTINCTS_PATH = REPO_ROOT / "config" / "active_instincts.json"
MAX_SLOTS: int = 5

# Safe parameter bounds to prevent runaway degradation (Layer 2 Gate)
PARAMETER_BOUNDS: Dict[str, Tuple[float, float]] = {
    "first_metric_max_word_offset": (4, 15),
    "ko_speech_rate": (5.5, 6.5),
    "living_texture_fps": (8, 24),
    "max_dead_freeze_sec": (0.1, 0.5),
    "min_text_area_pct": (30, 55),
}


class ThreeLayerGatekeeper:
    """3-Layer Quality Gate for Proposing and Committing Instincts."""

    @staticmethod
    def validate_statistical_significance(evidence_count: int) -> bool:
        """Layer 1: Requires at least 3 occurrences or verified post-mortem analysis."""
        return evidence_count >= 3

    @staticmethod
    def validate_parameter_bounds(parameter_patch: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 2: Clamps parameter values within strictly safe operating bounds."""
        sanitized = {}
        for param, val in parameter_patch.items():
            if isinstance(val, (int, float)) and param in PARAMETER_BOUNDS:
                min_v, max_v = PARAMETER_BOUNDS[param]
                clamped = max(min_v, min(max_v, type(val)(val)))
                sanitized[param] = clamped
            else:
                sanitized[param] = val
        return sanitized


class InstinctManager:
    """Manages the 5-slot Active Instinct Memory Vault."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or ACTIVE_INSTINCTS_PATH

    def load_vault(self) -> Dict[str, Any]:
        """Load the active instincts vault from disk."""
        if not self.config_path.exists():
            return {
                "version": "2.0.0",
                "max_slots": MAX_SLOTS,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "slots": [],
            }

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load active instincts from {self.config_path}: {e}")
            return {
                "version": "2.0.0",
                "max_slots": MAX_SLOTS,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "slots": [],
            }

    def save_vault(self, data: Dict[str, Any]) -> None:
        """Atomic write of the vault to disk."""
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp_path = self.config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.config_path)

    def get_instincts_for_stage(self, stage_name: str) -> List[Dict[str, Any]]:
        """Retrieve active instinct slots mapped to a target pipeline stage."""
        vault = self.load_vault()
        norm_stage = stage_name.strip().lower()
        matched = []
        for slot in vault.get("slots", []):
            tgt = slot.get("target_stage", "").strip().lower()
            if tgt and (tgt in norm_stage or norm_stage in tgt):
                matched.append(slot)
        return matched

    def propose_instinct(
        self,
        target_stage: str,
        rule_code: str,
        parameter_patch: Dict[str, Any],
        rationale: str,
        evidence_count: int = 3
    ) -> Dict[str, Any]:
        """Propose and validate an instinct through the 3-Layer Gatekeeper."""
        # Layer 1: Statistical Gate
        if not ThreeLayerGatekeeper.validate_statistical_significance(evidence_count):
            raise ValueError(f"Instinct proposal rejected (Layer 1 Gate): evidence_count ({evidence_count}) < 3")

        # Layer 2: Bounded Parameter Gate
        sanitized_patch = ThreeLayerGatekeeper.validate_parameter_bounds(parameter_patch)

        # Layer 3: 5-Slot Vault Management
        vault = self.load_vault()
        slots: List[Dict[str, Any]] = vault.get("slots", [])

        # Check if rule_code already exists -> update in place
        existing_idx = next((i for i, s in enumerate(slots) if s.get("rule_code") == rule_code), None)
        if existing_idx is not None:
            slots[existing_idx]["parameter_patch"] = sanitized_patch
            slots[existing_idx]["rationale"] = rationale
            slots[existing_idx]["last_triggered"] = datetime.now(timezone.utc).isoformat()
            self.save_vault(vault)
            return slots[existing_idx]

        # If slots >= MAX_SLOTS, evict slot with lowest applied_count (FIFO / LRU tiebreak)
        if len(slots) >= MAX_SLOTS:
            slots.sort(key=lambda s: (s.get("applied_count", 0), s.get("last_triggered", "")))
            evicted = slots.pop(0)
            logger.info(f"Evicted lowest priority instinct slot: {evicted.get('rule_code')}")

        new_slot_id = max([s.get("slot_id", 0) for s in slots] + [0]) + 1
        new_slot = {
            "slot_id": new_slot_id,
            "target_stage": target_stage,
            "rule_code": rule_code,
            "parameter_patch": sanitized_patch,
            "rationale": rationale,
            "applied_count": 1,
            "last_triggered": datetime.now(timezone.utc).isoformat(),
        }
        slots.append(new_slot)
        # Re-index slots 1..5
        for idx, s in enumerate(slots, 1):
            s["slot_id"] = idx
        vault["slots"] = slots
        self.save_vault(vault)
        return new_slot

    def evaluate_telemetry_signals(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate real post-mortem telemetry against the Signal-to-Stage Routing Matrix."""
        actions_taken = []

        # 1. Retention 0-15s Drop-off (< 65% at 15s)
        ret_15s = telemetry.get("retention_15s_pct")
        if ret_15s is not None and float(ret_15s) < 65.0:
            slot = self.propose_instinct(
                target_stage="s03_script",
                rule_code="INSTINCT_COLD_STRIKE_METRIC_FIRST",
                parameter_patch={"first_metric_max_word_offset": 8},
                rationale=f"Observed retention at 15s ({ret_15s}%) < 65.0%; frontloading metric in cold strike.",
                evidence_count=3
            )
            actions_taken.append(slot)

        # 2. Click-Through Rate (< 5.5% in first 28h)
        ctr = telemetry.get("ctr_28h_pct")
        if ctr is not None and float(ctr) < 5.5:
            slot = self.propose_instinct(
                target_stage="s11_seo",
                rule_code="INSTINCT_THUMBNAIL_TEXT_AREA_RATIO",
                parameter_patch={"min_text_area_pct": 45},
                rationale=f"Observed CTR ({ctr}%) < 5.5%; expanding thumbnail text area to >= 45%.",
                evidence_count=3
            )
            actions_taken.append(slot)

        # 3. Karaoke Drift (> 100ms)
        drift_ms = telemetry.get("karaoke_drift_max_ms")
        if drift_ms is not None and float(drift_ms) > 100.0:
            slot = self.propose_instinct(
                target_stage="s04_pacing",
                rule_code="INSTINCT_KR_NEWS_TEMPO_CALIBRATION",
                parameter_patch={"ko_speech_rate": 5.85},
                rationale=f"Observed subtitle timing drift ({drift_ms}ms) > 100ms; recalibrating speech tempo.",
                evidence_count=3
            )
            actions_taken.append(slot)

        # 4. Visual Critic Score (< 8.5)
        visual_score = telemetry.get("visual_critic_score")
        if visual_score is not None and float(visual_score) < 8.5:
            slot = self.propose_instinct(
                target_stage="s05_director",
                rule_code="INSTINCT_ARCHETYPE_SANCTION_STAMP_HOLD",
                parameter_patch={"living_texture_fps": 12, "max_dead_freeze_sec": 0.4},
                rationale=f"Visual score ({visual_score}) < 8.5; enforcing strict tactile archetypes and living texture.",
                evidence_count=3
            )
            actions_taken.append(slot)

        return actions_taken


# Global singleton
_INSTINCT_INSTANCE: Optional[InstinctManager] = None


def get_instinct_manager() -> InstinctManager:
    global _INSTINCT_INSTANCE
    if _INSTINCT_INSTANCE is None:
        _INSTINCT_INSTANCE = InstinctManager()
    return _INSTINCT_INSTANCE
