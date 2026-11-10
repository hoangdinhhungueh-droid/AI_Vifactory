#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/run_manifest.py — Run State Machine & Manifest Governor (AVF-STAB-001).

Manages execution state, idempotency hash matching, and deterministic resume.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

from core.contracts.stages import SCHEMA_VERSION, StageID
from core.paths import RunPaths


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
    market: Optional[str] = None
    preset: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    stages: Dict[StageID, StageState] = Field(default_factory=dict)

    @classmethod
    def create_new(cls, run_id: str, profile: str = "prod", market: Optional[str] = None, preset: Optional[str] = None) -> RunManifest:
        """Creates a fresh manifest with all 11 stages initialized to 'pending'."""
        manifest = cls(run_id=run_id, profile=profile, market=market, preset=preset)
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
        elif status == "pending":
            st.artifact_sha256 = None
            st.finished_at = None
            st.error = None

        self.updated_at = now

    def invalidate_downstream(
        self,
        from_stage: StageID,
        inclusive: bool = True,
        paths: Optional[RunPaths] = None
    ) -> None:
        """Resets status to 'pending' and clears artifact_sha256 for all stages from from_stage onwards.
        If paths is provided, purges stale artifact files on disk to prevent split-brain reads.
        """
        all_stages = list(StageID)
        try:
            start_idx = all_stages.index(from_stage)
        except ValueError:
            return
        if not inclusive:
            start_idx += 1
        for s in all_stages[start_idx:]:
            self.mark(s, "pending", artifact_sha256=None)
            if paths:
                try:
                    art_file = paths.artifact_file(s.value)
                    if art_file.exists():
                        art_file.unlink()
                except OSError as _unlink_err:
                    logger.debug(f"[invalidate_downstream] Notice unlinking artifact for {s.value}: {_unlink_err}")

                # Purge root-level secondary exports for invalidated stages to prevent split-brain reads
                secondary_files = []
                if s == StageID.S3_SCRIPT:
                    secondary_files.append(paths.root / "spoken_script.txt")
                elif s == StageID.S5_DIRECTOR_PLAN:
                    secondary_files.extend([
                        paths.root / "director_plan.json",
                        paths.root / "dp_plan.json",
                        paths.root / "flow_video_manifest.json",
                        paths.root / "bulk_image_prompts.txt",
                    ])
                elif s == StageID.S7_IMAGE_GEN:
                    secondary_files.append(paths.root / "images_manifest.json")

                for sec_f in secondary_files:
                    try:
                        if sec_f.exists():
                            sec_f.unlink()
                    except OSError as _sec_err:
                        logger.debug(f"[invalidate_downstream] Notice unlinking secondary file {sec_f.name}: {_sec_err}")

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
