#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/gates.py — Inter-Stage Boundary Validation Gates (AVF-STAB-001).

Guarantees data integrity between every pipeline stage.
Eliminates F4 (Boundary Blindness). Fails fast with clear diff errors.
"""

from __future__ import annotations

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import ValidationError

from core.paths import RunPaths
from core.contracts.stages import StageID, StageArtifact, SCHEMA_VERSION


STAGE_PREDECESSORS: Dict[StageID, Optional[StageID]] = {
    StageID.S1_IDEATION: None,
    StageID.S2_RESEARCH: StageID.S1_IDEATION,
    StageID.S3_SCRIPT: StageID.S2_RESEARCH,
    StageID.S4_CRITIC_SCRIPT: StageID.S3_SCRIPT,
    StageID.S5_DIRECTOR_PLAN: StageID.S4_CRITIC_SCRIPT,
    StageID.S6_CRITIC_VISUAL: StageID.S5_DIRECTOR_PLAN,
    StageID.S7_IMAGE_GEN: StageID.S6_CRITIC_VISUAL,
    StageID.S8_VIDEO_GEN: StageID.S7_IMAGE_GEN,
    StageID.S9_VOICE_TTS: StageID.S3_SCRIPT,  # Voice reads approved script
    StageID.S10_RENDER: StageID.S8_VIDEO_GEN, # Remotion joins S8 video + S9 audio
    StageID.S11_QC: StageID.S10_RENDER,
}


class GateError(RuntimeError):
    """Raised when an artifact fails boundary validation."""
    def __init__(self, stage: StageID, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[GATE ERROR at {stage.value}]: {message}")
        self.stage = stage
        self.details = details or {}


def validate_artifact(stage: StageID, raw_dict: Dict[str, Any]) -> StageArtifact:
    """Validates raw JSON dictionary against StageArtifact schema."""
    try:
        artifact = StageArtifact.model_validate(raw_dict)
    except ValidationError as e:
        raise GateError(stage, f"Artifact failed Pydantic schema validation: {e.errors()}", {"errors": e.errors()})

    if artifact.stage != stage:
        raise GateError(
            stage,
            f"Stage mismatch in artifact: expected '{stage.value}', got '{artifact.stage.value}'"
        )

    if artifact.schema_version != SCHEMA_VERSION:
        raise GateError(
            stage,
            f"Schema version drift: expected '{SCHEMA_VERSION}', got '{artifact.schema_version}'"
        )

    return artifact


def require_input(stage: StageID, paths: RunPaths) -> Optional[StageArtifact]:
    """Reads and validates the required input artifact for a stage."""
    predecessor = STAGE_PREDECESSORS.get(stage)
    if predecessor is None:
        return None  # First stage S1 has no predecessor

    artifact_file = paths.artifact_file(predecessor.value)
    if not artifact_file.exists():
        raise GateError(
            stage,
            f"Missing required predecessor artifact from {predecessor.value} at: {artifact_file}"
        )

    try:
        raw_data = json.loads(artifact_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise GateError(stage, f"Failed to parse JSON artifact from {artifact_file}: {e}")

    return validate_artifact(predecessor, raw_data)


def emit_artifact(artifact: StageArtifact, paths: RunPaths) -> Path:
    """Atomically validates and writes artifact to disk (tmp + replace)."""
    # Self-validation
    validate_artifact(artifact.stage, artifact.model_dump())

    target_file = paths.artifact_file(artifact.stage.value)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = target_file.with_suffix(".tmp")
    data_json = artifact.model_dump_json(indent=2)
    tmp_file.write_text(data_json, encoding="utf-8")

    # Atomic rename/replace
    if target_file.exists():
        target_file.unlink()
    tmp_file.replace(target_file)

    return target_file


def compute_file_sha256(path: Path) -> str:
    """Computes SHA256 checksum of a file for integrity and idempotency."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()
