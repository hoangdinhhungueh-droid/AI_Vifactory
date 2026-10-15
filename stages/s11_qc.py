#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s11_qc.py — Stage S11: Final Master Video Quality Control (AVF-STAB-001).

Implements Stage Shape Standard. Performs forensic verification on final rendered master MP4.
"""

from __future__ import annotations

import time
from pathlib import Path

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage
from vox.qa.gates import QAGateFailureError, verify_final_video_gates

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
    verify_cmds=["python -m vox.qa.gates --help"]
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
    gate_passed = False

    fps = float(s10_art.payload.get("fps", 30.0) or 30.0)
    frames = s10_art.payload.get("duration_in_frames")
    expected_dur = (frames / fps) if frames else None

    try:
        # Delegate directly to canonical vox.qa.gates for forensic verification (Rule 125 & 139)
        gate_res = verify_final_video_gates(p, expected_duration=expected_dur)
        qc_details.update(gate_res)
        qc_details["gates_verified"] = True
        gate_passed = True
    except (QAGateFailureError, ValueError) as e:
        qc_details["gates_verified"] = False
        qc_details["gate_note"] = str(e)
        gate_passed = False

    qc_verdict = "PASS" if gate_passed else "FAIL"
    integrity_verified = gate_passed

    payload = {
        "task_id": ctx.run_id,
        "qc_verdict": qc_verdict,
        "final_video_path": str(p),
        "size_bytes": sz,
        "integrity_verified": integrity_verified,
        "qc_details": qc_details,
        "message": (
            f"Master video successfully verified ({sz:,} bytes)."
            if gate_passed
            else f"Master video FAILED quality gates: {qc_details.get('gate_note', 'Unknown QA error')}"
        ),
    }

    prov = Provenance(
        generator="stages.s11_qc",
        latency_sec=round(time.time() - start_ts, 2)
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok" if gate_passed else "failed",
        payload=payload,
        provenance=prov
    )

    emit_artifact(artifact, ctx.paths)
    return artifact
