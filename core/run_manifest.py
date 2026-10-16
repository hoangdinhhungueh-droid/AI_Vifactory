#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/run_manifest.py — Run State Machine & Manifest Governor (AVF-STAB-001).

Manages execution state, idempotency hash matching, and deterministic resume.
"""

from __future__ import annotations

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from core.paths import RunPaths
from core.contracts.stages import StageID, SCHEMA_VERSION


class StageState(BaseModel):
    """Execution status for a single stage."""
    model_config = ConfigDict(extra="forbid")

    stage: StageID
    status: Literal["pending", "running", "done", "failed", "skipped"] = "pending"
    attempts: int = 0
    artifact_sha256: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class RunManifest(BaseModel):
    """The complete state machine manifest of a pipeline run."""
    model_config = ConfigDict(extra="forbid")

    run_id: str
    schema_version: str = SCHEMA_VERSION
    profile: str = "prod"
    pipeline_version: str = "2.0.0"
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    stages: Dict[StageID, StageState] = Field(default_factory=dict)

    @classmethod
    def create_new(cls, run_id: str, profile: str = "prod") -> RunManifest:
        """Creates a fresh manifest with all 11 stages initialized to 'pending'."""
        manifest = cls(run_id=run_id, profile=profile)
        for stage in StageID:
            manifest.stages[stage] = StageState(stage=stage, status="pending")
        return manifest

    def next_pending_stage(self) -> Optional[StageID]:
        """Returns the first stage that is not 'done' or 'skipped'."""
        for stage in StageID:
            state = self.stages.get(stage)
            if state and state.status in ["pending", "failed", "running"]:
                return stage
        return None

    def mark(
        self,
        stage: StageID,
        status: Literal["pending", "running", "done", "failed", "skipped"],
        artifact_sha256: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Updates stage state and timestamp."""
        now = datetime.datetime.now().isoformat()
        if stage not in self.stages:
            self.stages[stage] = StageState(stage=stage)

        st = self.stages[stage]
        st.status = status
        if status == "running":
            st.started_at = now
            st.attempts += 1
            st.error = None
        elif status in ["done", "skipped"]:
            st.finished_at = now
            st.error = None
            if artifact_sha256:
                st.artifact_sha256 = artifact_sha256
        elif status == "failed":
            st.finished_at = now
            st.error = error

        self.updated_at = now

    def save_atomic(self, paths: RunPaths) -> Path:
        """Atomically saves manifest to run root."""
        manifest_path = paths.manifest_file
        tmp_path = manifest_path.with_suffix(".tmp")
        tmp_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        if manifest_path.exists():
            manifest_path.unlink()
        tmp_path.replace(manifest_path)
        return manifest_path

    @classmethod
    def load_or_create(cls, paths: RunPaths, profile: str = "prod") -> RunManifest:
        """Loads existing manifest from disk or initializes a new one."""
        if paths.manifest_file.exists():
            try:
                raw_json = paths.manifest_file.read_text(encoding="utf-8")
                return cls.model_validate_json(raw_json)
            except Exception as _man_err:
                logger.warning("Failed to load existing manifest at %s, recreating: %s", paths.manifest_file, _man_err)
        m = cls.create_new(run_id=paths.run_id, profile=profile)
        m.save_atomic(paths)
        return m
