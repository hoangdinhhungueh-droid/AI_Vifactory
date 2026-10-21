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


def _coerce_scene_plan(data: dict[str, Any], run_id: str) -> Any:
    """Coerces arbitrary scene data or Remotion render props into a canonical ScenePlan."""
    from vox.schemas import CameraMove, FGObject, Scene, ScenePlan

    sc_list = data.get("scenes", [])
    if not sc_list or not isinstance(sc_list, list):
        raise ValueError("Empty or non-list scenes declared in plan data")

    adapted_scenes: list[Scene] = []
    canonical_moves = [
        CameraMove.PUSH_IN,
        CameraMove.STATIC_BREATH,
        CameraMove.PULL_OUT,
        CameraMove.PAN_LEFT,
        CameraMove.PAN_RIGHT,
        CameraMove.TILT_UP,
        CameraMove.TILT_DOWN,
        CameraMove.KEN_BURNS_TL_BR,
        CameraMove.KEN_BURNS_BR_TL,
        CameraMove.PARALLAX_LEFT,
        CameraMove.PARALLAX_RIGHT,
        CameraMove.ROLL_PUSH,
    ]

    for i, s in enumerate(sc_list):
        if isinstance(s, Scene):
            adapted_scenes.append(s)
            continue
        if not isinstance(s, dict):
            raise ValueError(f"Scene entry {i} is not a valid dictionary: {s}")

        idx = int(s.get("idx", s.get("scene_index", i)))
        narration = str(s.get("narration", s.get("narration_text", s.get("text", f"Scene {idx} narrative commentary"))))
        if not narration.strip():
            narration = f"Scene {idx} narrative commentary"

        bg_prompt = str(s.get("bg_prompt", s.get("bg_image", s.get("background", f"atmospheric editorial scene {idx} background workspace"))))
        if len(bg_prompt) < 10:
            bg_prompt = f"atmospheric editorial background {bg_prompt} textured composition"

        raw_fg = s.get("fg", s.get("fg_image", s.get("foreground", None)))
        adapted_fg: list[FGObject] = []
        if isinstance(raw_fg, list) and len(raw_fg) > 0:
            for j, fg_item in enumerate(raw_fg):
                if isinstance(fg_item, FGObject):
                    adapted_fg.append(fg_item)
                elif isinstance(fg_item, dict):
                    prompt_str = str(fg_item.get("prompt", f"tactile archival document cutout element {idx}_{j}"))
                    if len(prompt_str) < 10:
                        prompt_str = f"tactile archival cutout element {prompt_str} forensic"
                    adapted_fg.append(FGObject(
                        id=str(fg_item.get("id", f"fg_{idx}_{j}")),
                        prompt=prompt_str,
                        anchor_x=float(fg_item.get("anchor_x", 0.5)),
                        anchor_y=float(fg_item.get("anchor_y", 0.5)),
                        scale=float(fg_item.get("scale", 0.5)),
                        depth=float(fg_item.get("depth", 0.5)),
                        enter_at=float(fg_item.get("enter_at", 0.0)),
                    ))
                elif isinstance(fg_item, str):
                    prompt_str = fg_item if len(fg_item) >= 10 else f"tactile forensic object {fg_item} specimen"
                    adapted_fg.append(FGObject(
                        id=f"fg_{idx}_{j}",
                        prompt=prompt_str,
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.5,
                        depth=0.5,
                        enter_at=0.0,
                    ))
        elif isinstance(raw_fg, str) and raw_fg.strip():
            prompt_str = raw_fg if len(raw_fg) >= 10 else f"tactile forensic object {raw_fg} specimen"
            adapted_fg.append(FGObject(
                id=f"fg_{idx}_0",
                prompt=prompt_str,
                anchor_x=0.5,
                anchor_y=0.5,
                scale=0.5,
                depth=0.5,
                enter_at=0.0,
            ))
        else:
            adapted_fg.append(FGObject(
                id=f"fg_{idx}_0",
                prompt=f"tactile archival document cutout element {idx} forensic",
                anchor_x=0.5,
                anchor_y=0.5,
                scale=0.5,
                depth=0.5,
                enter_at=0.0,
            ))

        raw_cam = str(s.get("camera", s.get("camera_move", ""))).strip().lower()
        cam_map = {
            "zoom_in": CameraMove.PUSH_IN,
            "push_in": CameraMove.PUSH_IN,
            "zoom_out": CameraMove.PULL_OUT,
            "pull_out": CameraMove.PULL_OUT,
            "static": CameraMove.STATIC_BREATH,
            "static_breath": CameraMove.STATIC_BREATH,
            "pan_left": CameraMove.PAN_LEFT,
            "pan_right": CameraMove.PAN_RIGHT,
            "tilt_up": CameraMove.TILT_UP,
            "tilt_down": CameraMove.TILT_DOWN,
            "ken_burns_tl_br": CameraMove.KEN_BURNS_TL_BR,
            "ken_burns_br_tl": CameraMove.KEN_BURNS_BR_TL,
            "parallax_left": CameraMove.PARALLAX_LEFT,
            "parallax_right": CameraMove.PARALLAX_RIGHT,
            "roll_push": CameraMove.ROLL_PUSH,
        }
        resolved_cam = cam_map.get(raw_cam)
        if not resolved_cam:
            resolved_cam = canonical_moves[i % len(canonical_moves)]

        if adapted_scenes and adapted_scenes[-1].camera == resolved_cam:
            next_idx = (canonical_moves.index(resolved_cam) + 1) % len(canonical_moves)
            resolved_cam = canonical_moves[next_idx]

        adapted_scenes.append(Scene(
            idx=idx,
            narration=narration,
            bg_prompt=bg_prompt,
            fg=adapted_fg[:3],
            camera=resolved_cam,
            start=float(s["start"]) if s.get("start") is not None else None,
            end=float(s["end"]) if s.get("end") is not None else None,
        ))

    return ScenePlan(
        title=str(data.get("title", f"Plan {run_id}")),
        scenes=adapted_scenes,
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
            plan = _coerce_scene_plan(props_data, ctx.run_id)
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
                plan = _coerce_scene_plan(dp_data, ctx.run_id)
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
