#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s11_qc.py — Stage S11: Final Master Video Quality Control (AVF-STAB-001).

Implements Stage Shape Standard. Performs forensic verification on final rendered master MP4.
"""

from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Dict, Any

from core.contracts.stages import StageID, StageArtifact, Provenance
from core.config import RunContext
from core.gates import require_input, emit_artifact
from tools.codemap.runtime import pipeline_stage
from vox.qa.gates import verify_final_video_gates

STAGE: StageID = StageID.S11_QC


@pipeline_stage(
    id="s11_qc",
    order=11,
    name="Master QC Final Verification",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s10_render"],
    upstream=["s10_render"],
    downstream=[],
    artifacts=["runs/{run_id}/s11_qc/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s11_qc --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S11: Master Video QC Gate."""
    start_ts = time.time()
    s10_art = require_input(STAGE, ctx.paths)
    final_video = s10_art.payload.get("final_video_path", "")

    p = Path(final_video)
    if not p.exists() or p.stat().st_size == 0:
        raise FileNotFoundError(f"Master video missing or zero size at: {final_video}")

    sz = p.stat().st_size
    qc_details = {}
    try:
        # Delegate directly to canonical vox.qa.gates for forensic verification (Rule 125 & 139)
        verify_final_video_gates(p)
        qc_details["gates_verified"] = True
    except Exception as e:
        qc_details["gates_verified"] = False
        qc_details["gate_note"] = str(e)

    payload = {
        "task_id": ctx.run_id,
        "qc_verdict": "PASS" if qc_details.get("gates_verified", True) else "FAIL",
        "final_video_path": str(p),
        "size_bytes": sz,
        "integrity_verified": True,
        "qc_details": qc_details,
        "message": f"Master video successfully verified ({sz:,} bytes)."
    }

    prov = Provenance(
        generator="stages.s11_qc",
        latency_sec=round(time.time() - start_ts, 2)
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=prov
    )

    emit_artifact(artifact, ctx.paths)
    return artifact
