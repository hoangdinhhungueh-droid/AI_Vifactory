#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s11_qc.py — Stage S11: Final Master Video Quality Control (AVF-STAB-001).

Implements Stage Shape Standard. Performs forensic verification on final rendered master MP4.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage
from vox.qa.gates import QAGateFailureError, verify_final_video_gates

logger = logging.getLogger("s11_qc")
STAGE: StageID = StageID.S11_QC


def _validate_authoritative_scene_plan(data: dict[str, Any], expected_run_id: str) -> Any:
    """Strictly validates authoritative scene data into ScenePlan without synthetic coercion (Boss Round 10 Item 5)."""
    from vox.schemas import CameraMove, FGObject, Scene, ScenePlan

    # Validate task/episode binding if declared in plan
    declared_id = data.get("episode_id") or data.get("run_id") or data.get("task_id")
    if declared_id and str(declared_id).strip() != str(expected_run_id).strip():
        raise ValueError(
            f"Stage S11 fail-closed: Authoritative plan declared identity '{declared_id}' "
            f"contradicts expected run identity '{expected_run_id}'"
        )

    sc_list = data.get("scenes", [])
    if not sc_list or not isinstance(sc_list, list):
        raise ValueError("Empty or non-list scenes declared in authoritative plan data")

    validated_scenes: list[Scene] = []
    for i, s in enumerate(sc_list):
        if isinstance(s, Scene):
            validated_scenes.append(s)
            continue
        if not isinstance(s, dict):
            raise ValueError(f"Authoritative scene entry {i} is not a valid dictionary: {s}")

        idx = s.get("idx", s.get("scene_index"))
        if idx is None or not isinstance(idx, int) or idx < 0:
            raise ValueError(f"Authoritative scene {i} missing valid non-negative integer 'idx'")

        narration = s.get("narration", s.get("narration_text", s.get("text")))
        if not narration or not isinstance(narration, str) or not narration.strip():
            raise ValueError(f"Authoritative scene {idx} missing required non-empty 'narration'")

        bg_prompt = s.get("bg_prompt", s.get("bg_image", s.get("background")))
        if not bg_prompt or not isinstance(bg_prompt, str) or len(bg_prompt.strip()) < 10:
            raise ValueError(f"Authoritative scene {idx} missing required 'bg_prompt' (min length 10)")

        raw_fg = s.get("fg", s.get("fg_image", s.get("foreground")))
        if not raw_fg or not isinstance(raw_fg, list) or len(raw_fg) == 0:
            raise ValueError(f"Authoritative scene {idx} missing required 'fg' objects list (min 1 object)")

        valid_fg_list: list[FGObject] = []
        for j, fg_item in enumerate(raw_fg):
            if isinstance(fg_item, FGObject):
                valid_fg_list.append(fg_item)
            elif isinstance(fg_item, dict):
                fg_id = fg_item.get("id")
                fg_prompt = fg_item.get("prompt")
                if not fg_id or not fg_prompt or len(str(fg_prompt).strip()) < 10:
                    raise ValueError(f"Authoritative scene {idx} FG object {j} missing required 'id' or 'prompt' (min length 10)")
                valid_fg_list.append(FGObject(
                    id=str(fg_id),
                    prompt=str(fg_prompt).strip(),
                    anchor_x=float(fg_item.get("anchor_x", 0.5)),
                    anchor_y=float(fg_item.get("anchor_y", 0.5)),
                    scale=float(fg_item.get("scale", 0.5)),
                    depth=float(fg_item.get("depth", 0.5)),
                    enter_at=float(fg_item.get("enter_at", 0.0)),
                ))
            else:
                raise ValueError(f"Authoritative scene {idx} FG object {j} is not a valid dictionary or FGObject")

        raw_cam = str(s.get("camera", s.get("camera_move", ""))).strip().lower()
        if not raw_cam:
            raise ValueError(f"Authoritative scene {idx} missing required 'camera' move")
        try:
            cam_enum = CameraMove(raw_cam)
        except ValueError:
            raise ValueError(f"Authoritative scene {idx} has invalid camera move '{raw_cam}' (must be one of 12 canonical CameraMove values)")

        validated_scenes.append(Scene(
            idx=idx,
            narration=narration.strip(),
            bg_prompt=bg_prompt.strip(),
            fg=valid_fg_list[:3],
            camera=cam_enum,
            start=float(s["start"]) if s.get("start") is not None else None,
            end=float(s["end"]) if s.get("end") is not None else None,
        ))

    return ScenePlan(
        title=str(data.get("title", f"Plan {expected_run_id}")),
        scenes=validated_scenes,
        audio_duration=float(data["audio_duration"]) if data.get("audio_duration") is not None else None,
    )


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
    if frames is None or frames <= 0:
        raise ValueError(f"Stage S11 requires positive duration_in_frames in S10 artifact payload, got: {frames}")
    expected_dur = frames / fps

    # Reconstruct ScenePlan for camera variety and prompt semantics verification (Rule 125, 128 & 139)
    plan = None
    props_path_str = s10_art.payload.get("remotion_props_file")
    if props_path_str:
        props_path = Path(props_path_str)
        if not props_path.exists():
            raise FileNotFoundError(f"Stage S11 fail-closed: Declared remotion_props_file missing: {props_path}")
        try:
            props_data = json.loads(props_path.read_text(encoding="utf-8"))
            sc_list = props_data.get("scenes", [])
            if not sc_list:
                raise ValueError(f"Empty scenes list in remotion_props_file: {props_path}")
            plan = _validate_authoritative_scene_plan(props_data, ctx.run_id)
        except Exception as p_err:
            raise ValueError(f"Stage S11 fail-closed: Malformed authoritative remotion_props_file '{props_path}': {p_err}")
    else:
        # Fallback strictly to task-local director_plan.json (Rule 128: cấm tìm repo-level unrelated plans)
        local_dp = ctx.paths.root / "director_plan.json"
        if local_dp.exists():
            try:
                dp_data = json.loads(local_dp.read_text(encoding="utf-8"))
                sc_list = dp_data.get("scenes", [])
                if not sc_list:
                    raise ValueError(f"Empty scenes list in run-local director_plan: {local_dp}")
                plan = _validate_authoritative_scene_plan(dp_data, ctx.run_id)
            except Exception as dp_err:
                raise ValueError(f"Stage S11 fail-closed: Malformed run-local director_plan '{local_dp}': {dp_err}")
        else:
            raise ValueError(f"Stage S11 fail-closed: No authoritative ScenePlan found for run '{ctx.run_id}' (both remotion_props_file and local director_plan missing)")

    if not plan or not plan.scenes:
        raise ValueError(f"Stage S11 fail-closed: ScenePlan is empty or invalid for run '{ctx.run_id}'")

    try:
        # Delegate directly to canonical vox.qa.gates for forensic verification (Rule 125 & 139)
        gate_res = verify_final_video_gates(p, expected_duration=expected_dur, plan=plan)
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
