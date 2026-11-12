#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/run_manifest.py — Run State Machine & Manifest Governor (AVF-STAB-001).

Manages execution state, idempotency hash matching, and deterministic resume.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Dict, List, Literal, Optional

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
    input_sha256: Optional[str] = None
    config_sha256: Optional[str] = None
    upstream_artifacts: dict[str, str] = Field(default_factory=dict)
    run_nonce: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None

    def clear_provenance(self) -> None:
        self.artifact_sha256 = None
        self.input_sha256 = None
        self.config_sha256 = None
        self.upstream_artifacts = {}
        self.run_nonce = None


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
    ) -> List[str]:
        """Resets status to 'pending' and clears artifact_sha256 for all stages from from_stage onwards.
        If paths is provided, purges stale artifact files on disk to prevent split-brain reads.
        Returns the ordered list of invalidated stage IDs.
        """
        invalidated: List[str] = []
        all_stages = list(StageID)
        try:
            start_idx = all_stages.index(from_stage)
        except ValueError:
            return invalidated
        if not inclusive:
            start_idx += 1
        for s in all_stages[start_idx:]:
            self.mark(s, "pending", artifact_sha256=None)
            st_obj = self.stages.get(s.value) or self.stages.get(s)
            if st_obj is not None:
                st_obj.clear_provenance()
            invalidated.append(s.value)
            if paths:
                from core.dag_provenance import purge_stage_outputs

                purged = purge_stage_outputs(s, paths, include_artifact_file=True)
                if purged:
                    logger.debug(f"[invalidate_downstream] Purged {len(purged)} outputs for {s.value}: {purged}")

        # Cross-edge invalidation: if S9_VOICE_TTS was invalidated and S8_VIDEO_GEN recorded S9 as upstream, invalidate S8 too
        if (
            StageID.S9_VOICE_TTS in all_stages[start_idx:]
            and StageID.S8_VIDEO_GEN not in all_stages[start_idx:]
        ):
            s8_state = self.stages.get(StageID.S8_VIDEO_GEN.value) or self.stages.get(StageID.S8_VIDEO_GEN)
            if s8_state and StageID.S9_VOICE_TTS.value in (s8_state.upstream_artifacts or {}):
                self.mark(StageID.S8_VIDEO_GEN, "pending", artifact_sha256=None)
                s8_state.clear_provenance()
                invalidated.append(StageID.S8_VIDEO_GEN.value)
                if paths:
                    from core.dag_provenance import purge_stage_outputs
                    purge_stage_outputs(StageID.S8_VIDEO_GEN, paths, include_artifact_file=True)

        return invalidated

    def save_atomic(self, paths: RunPaths) -> Path:
        """Atomically saves manifest to run root via lock + fsync-backed replace (no pre-unlink race)."""
        from filelock import FileLock

        from core.atomic_io import atomic_write_json

        manifest_path = paths.manifest_file
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(manifest_path.with_name(".run_manifest.lock")), timeout=15.0)
        with lock:
            atomic_write_json(manifest_path, self.model_dump(mode="json"), indent=2)
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
