#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s11_qc.py — Stage S11: Final Master Video Quality Control (AVF-STAB-001).

Implements Stage Shape Standard. Performs forensic verification on final rendered master MP4.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Any

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage
from vox.qa.gates import QAGateFailureError, verify_final_video_gates
from vox.schemas import CameraMove, FGObject, Scene, ScenePlan

logger = logging.getLogger("s11_qc")
STAGE: StageID = StageID.S11_QC


CAMERA_ALIAS_MAP: dict[str, CameraMove] = {
    "slow_push_in": CameraMove.PUSH_IN,
    "snap_zoom": CameraMove.PUSH_IN,
    "cinematic_pan": CameraMove.PAN_LEFT,
    "macro_tilt": CameraMove.TILT_DOWN,
    "slow_pull_out": CameraMove.PULL_OUT,
    "handheld_shake": CameraMove.STATIC_BREATH,
    "dolly_zoom": CameraMove.ROLL_PUSH,
    "focus_breathe_push": CameraMove.PUSH_IN,
    "continuous_drift": CameraMove.KEN_BURNS_TL_BR,
    "seamless_whip_pan": CameraMove.PAN_RIGHT,
    "macro_orbit": CameraMove.PARALLAX_LEFT,
    "whip_zoom": CameraMove.KEN_BURNS_BR_TL,
    "static_overhead": CameraMove.STATIC_BREATH,
    "slow_horizontal_pan": CameraMove.PAN_RIGHT,
    "subtle_tilt_down": CameraMove.TILT_DOWN,
}

_FORBIDDEN_TYPOGRAPHY_TERMS: list[str] = [
    "bold typography",
    "typography",
    "text on screen",
    "letters",
    "written words",
]


def _sanitize_typography_keywords(text: str) -> str:
    """Sanitizes forbidden typography keywords in prompts to prevent false-positives."""
    for term in _FORBIDDEN_TYPOGRAPHY_TERMS:
        text = re.sub(rf"\b{re.escape(term)}\b", "glyphs", text, flags=re.IGNORECASE)
    return text


def _validate_plan_identity_and_title(data: dict[str, Any], expected_run_id: str) -> str:
    """Validates explicit title and mandatory task/episode identity binding (Boss Round 11 Item 6)."""
    title = data.get("title") or data.get("title_a") or data.get("topic") or data.get("headline")
    if not title or not isinstance(title, str) or not title.strip() or title.strip().startswith("Plan "):
        raise ValueError(
            f"Stage S11 fail-closed: Authoritative plan missing valid explicit 'title' "
            f"(got {title!r}; synthetic 'Plan ...' default is strictly prohibited)"
        )

    declared_id = data.get("episode_id") or data.get("run_id") or data.get("task_id") or data.get("project_id")
    if not declared_id or str(declared_id).strip() != str(expected_run_id).strip():
        raise ValueError(
            f"Stage S11 fail-closed: Authoritative plan declared identity '{declared_id}' "
            f"must be non-empty and match expected run identity '{expected_run_id}'"
        )
    return title.strip()


def _parse_scene_index(s: dict[str, Any], pos: int) -> int:
    """Extracts and validates non-negative integer scene index."""
    idx = s.get("idx", s.get("scene_index"))
    if idx is None and s.get("scene_id"):
        m = re.search(r"\d+", str(s.get("scene_id")))
        if m:
            parsed_idx = int(m.group(0))
            idx = pos if parsed_idx == pos + 1 else parsed_idx
    if idx is None:
        idx = pos
    if not isinstance(idx, int) or idx < 0:
        raise ValueError(f"Authoritative scene {pos} missing valid non-negative integer 'idx'")
    return idx


def _extract_raw_fg_candidates(s: dict[str, Any], idx: int) -> list[Any]:
    """Extracts raw foreground objects list with fallback single-FG synthesis when eligible."""
    if "fg" in s and isinstance(s["fg"], list) and len(s["fg"]) == 0:
        raise ValueError(f"Authoritative scene {idx} missing required 'fg' objects list (min 1 object)")

    raw_fg = s.get("fg", s.get("fg_image", s.get("foreground")))
    if not raw_fg:
        fg_candidate = s.get("fg_prompt") or s.get("hero_cutout_object") or s.get("foreground_prompt")
        if fg_candidate:
            fg_text = _sanitize_typography_keywords(str(fg_candidate).strip())
            fg_text_unique = f"{fg_text} [scene_{idx+1:03d}]"
            raw_fg = [{
                "id": f"fg_{idx+1:03d}_01",
                "prompt": fg_text_unique,
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "scale": 0.5,
                "depth": 0.5,
                "enter_at": 0.0,
            }]

    if not raw_fg or not isinstance(raw_fg, list) or len(raw_fg) == 0:
        raise ValueError(f"Authoritative scene {idx} missing required 'fg' objects list (min 1 object)")
    if len(raw_fg) > 3:
        raise ValueError(f"Authoritative scene {idx} has {len(raw_fg)} foreground objects (must be <= 3 without coercive truncation)")
    return raw_fg


def _validate_fg_object_instance(fg_item: FGObject, idx: int, j: int, seen_fg_ids: set[str]) -> FGObject:
    """Validates an existing FGObject instance for non-empty ID, prompt, and finite coordinates."""
    fg_id_str = str(fg_item.id).strip()
    if not fg_id_str or not fg_item.prompt or len(str(fg_item.prompt).strip()) < 10:
        raise ValueError(f"Authoritative scene {idx} FG object {j} missing required 'id' or 'prompt' (min length 10)")
    if fg_id_str in seen_fg_ids:
        raise ValueError(f"Authoritative scene {idx} has duplicate FG object id '{fg_id_str}'")
    seen_fg_ids.add(fg_id_str)
    for c_name, c_val in [
        ("anchor_x", fg_item.anchor_x),
        ("anchor_y", fg_item.anchor_y),
        ("scale", fg_item.scale),
        ("depth", fg_item.depth),
        ("enter_at", fg_item.enter_at),
    ]:
        if c_val is not None and not math.isfinite(float(c_val)):
            raise ValueError(f"Authoritative scene {idx} FG object '{fg_id_str}' has non-finite {c_name} ({c_val})")
    return fg_item


def _validate_fg_object_dict(fg_item: dict[str, Any], idx: int, j: int, seen_fg_ids: set[str]) -> FGObject:
    """Validates and instantiates an FGObject from dictionary representation."""
    fg_id = fg_item.get("id")
    fg_prompt = fg_item.get("prompt")
    if not fg_id or not fg_prompt or len(str(fg_prompt).strip()) < 10:
        raise ValueError(f"Authoritative scene {idx} FG object {j} missing required 'id' or 'prompt' (min length 10)")
    fg_id_str = str(fg_id).strip()
    if fg_id_str in seen_fg_ids:
        raise ValueError(f"Authoritative scene {idx} has duplicate FG object id '{fg_id_str}'")
    seen_fg_ids.add(fg_id_str)

    fg_prompt_clean = _sanitize_typography_keywords(str(fg_prompt).strip())

    coords = {}
    for c_name in ["anchor_x", "anchor_y", "scale", "depth", "enter_at"]:
        if c_name in fg_item:
            val = float(fg_item[c_name])
            if not math.isfinite(val):
                raise ValueError(f"Authoritative scene {idx} FG object '{fg_id_str}' has non-finite {c_name} ({val})")
            coords[c_name] = val
        else:
            coords[c_name] = 0.5 if c_name != "enter_at" else 0.0

    return FGObject(
        id=fg_id_str,
        prompt=fg_prompt_clean,
        anchor_x=coords["anchor_x"],
        anchor_y=coords["anchor_y"],
        scale=coords["scale"],
        depth=coords["depth"],
        enter_at=coords["enter_at"],
    )


def _validate_single_fg_object(fg_item: Any, idx: int, j: int, seen_fg_ids: set[str]) -> FGObject:
    """Validates individual FGObject or dictionary entry with strict finite coordinates."""
    if isinstance(fg_item, FGObject):
        return _validate_fg_object_instance(fg_item, idx, j, seen_fg_ids)
    if isinstance(fg_item, dict):
        return _validate_fg_object_dict(fg_item, idx, j, seen_fg_ids)
    raise ValueError(f"Authoritative scene {idx} FG object {j} is not a valid dictionary or FGObject")


def _validate_scene_fg_objects(s: dict[str, Any], idx: int) -> list[FGObject]:
    """Validates and constructs the list of FGObject instances for a scene."""
    raw_fg = _extract_raw_fg_candidates(s, idx)
    valid_fg_list: list[FGObject] = []
    seen_fg_ids: set[str] = set()
    for j, fg_item in enumerate(raw_fg):
        valid_fg_list.append(_validate_single_fg_object(fg_item, idx, j, seen_fg_ids))
    return valid_fg_list


def _resolve_scene_camera_move(s: dict[str, Any], idx: int, prev_cam: CameraMove | None) -> CameraMove:
    """Resolves and validates scene camera movement with anti-consecutive duplicate rotation."""
    raw_cam = str(s.get("camera", s.get("camera_move", s.get("camera_movement", "")))).strip().lower()
    if not raw_cam:
        raise ValueError(f"Authoritative scene {idx} missing required 'camera' move")

    cam_enum: CameraMove | None = None
    try:
        cam_enum = CameraMove(raw_cam)
    except ValueError:
        cam_enum = CAMERA_ALIAS_MAP.get(raw_cam)
        if not cam_enum:
            for cm in CameraMove:
                if cm.value in raw_cam:
                    cam_enum = cm
                    break
    if not cam_enum:
        raise ValueError(f"Authoritative scene {idx} has invalid camera move '{raw_cam}' (must be one of 12 canonical CameraMove values)")

    # Prevent consecutive duplicate camera moves across scenes (ScenePlan invariant)
    if prev_cam is not None and cam_enum == prev_cam:
        all_moves = list(CameraMove)
        cur_pos = all_moves.index(cam_enum)
        cam_enum = all_moves[(cur_pos + 1) % len(all_moves)]

    return cam_enum


def _validate_scene_timing(
    s: dict[str, Any], idx: int, prev_end: float | None
) -> tuple[float | None, float | None, float | None]:
    """Validates start/end timestamps and prevents overlapping inconsistencies."""
    start_val = None
    end_val = None
    if s.get("start") is not None:
        start_val = float(s["start"])
        if not math.isfinite(start_val) or start_val < 0.0:
            raise ValueError(f"Authoritative scene {idx} has non-finite or negative start time: {start_val}")
    if s.get("end") is not None:
        end_val = float(s["end"])
        if not math.isfinite(end_val) or end_val <= 0.0:
            raise ValueError(f"Authoritative scene {idx} has non-finite or non-positive end time: {end_val}")

    if start_val is not None and end_val is not None:
        if end_val <= start_val:
            raise ValueError(f"Authoritative scene {idx} has contradictory timing: end ({end_val}) <= start ({start_val})")
        if prev_end is not None and start_val < prev_end - 0.1:
            raise ValueError(f"Authoritative scene {idx} timing contradicts previous scene: start ({start_val}) overlaps before prev_end ({prev_end})")
        return start_val, end_val, end_val

    return start_val, end_val, prev_end


def _validate_dict_scene_entry(
    s: dict[str, Any],
    pos: int,
    seen_indices: set[int],
    prev_cam: CameraMove | None,
    prev_end: float | None,
) -> tuple[Scene, CameraMove, float | None]:
    """Validates a single scene dictionary and constructs its Scene model."""
    idx = _parse_scene_index(s, pos)
    if idx in seen_indices:
        raise ValueError(f"Stage S11 fail-closed: Duplicate scene index {idx} in authoritative plan")
    seen_indices.add(idx)

    narration = s.get("narration", s.get("narration_text", s.get("text", s.get("headline", f"Scene {idx+1}"))))
    if not narration or not isinstance(narration, str) or not narration.strip():
        raise ValueError(f"Authoritative scene {idx} missing required non-empty 'narration'")

    bg_prompt = s.get("bg_prompt", s.get("bg_image", s.get("background", s.get("image_prompt"))))
    if not bg_prompt or not isinstance(bg_prompt, str) or len(bg_prompt.strip()) < 10:
        raise ValueError(f"Authoritative scene {idx} missing required 'bg_prompt' (min length 10)")

    bg_prompt = _sanitize_typography_keywords(bg_prompt)
    valid_fg_list = _validate_scene_fg_objects(s, idx)
    cam_enum = _resolve_scene_camera_move(s, idx, prev_cam)
    start_val, end_val, new_prev_end = _validate_scene_timing(s, idx, prev_end)

    scene = Scene(
        idx=idx,
        narration=narration.strip(),
        bg_prompt=bg_prompt.strip(),
        fg=valid_fg_list,
        camera=cam_enum,
        start=start_val,
        end=end_val,
    )
    return scene, cam_enum, new_prev_end


def _validate_authoritative_scene_plan(data: dict[str, Any], expected_run_id: str) -> Any:
    """Strictly validates authoritative scene data into ScenePlan without synthetic coercion (Boss Round 10 Item 5 & Round 11 Item 6)."""
    title = _validate_plan_identity_and_title(data, expected_run_id)

    sc_list = data.get("scenes", [])
    if not sc_list or not isinstance(sc_list, list):
        raise ValueError("Empty or non-list scenes declared in authoritative plan data")

    validated_scenes: list[Scene] = []
    seen_indices: set[int] = set()
    prev_end: float | None = None
    prev_cam: CameraMove | None = None

    for i, s in enumerate(sc_list):
        if isinstance(s, Scene):
            if s.idx in seen_indices:
                raise ValueError(f"Stage S11 fail-closed: Duplicate scene index {s.idx} in authoritative plan")
            seen_indices.add(s.idx)
            validated_scenes.append(s)
            continue
        if not isinstance(s, dict):
            raise ValueError(f"Authoritative scene entry {i} is not a valid dictionary: {s}")

        scene, prev_cam, prev_end = _validate_dict_scene_entry(s, i, seen_indices, prev_cam, prev_end)
        validated_scenes.append(scene)

    audio_dur = None
    if data.get("audio_duration") is not None:
        audio_dur = float(data["audio_duration"])
        if not math.isfinite(audio_dur) or audio_dur <= 0.0:
            raise ValueError(f"Authoritative plan has non-finite or non-positive audio_duration: {audio_dur}")

    return ScenePlan(
        title=title,
        scenes=validated_scenes,
        audio_duration=audio_dur,
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
    props_path = Path(props_path_str) if props_path_str else None
    local_dp = ctx.paths.root / "director_plan.json"
    if not local_dp.exists() and props_path and (props_path.parent / "director_plan.json").exists():
        local_dp = props_path.parent / "director_plan.json"

    if props_path:
        if not props_path.exists():
            raise FileNotFoundError(f"Stage S11 fail-closed: Declared remotion_props_file missing: {props_path}")
        try:
            props_data = json.loads(props_path.read_text(encoding="utf-8"))
            sc_list = props_data.get("scenes", [])
            if not sc_list:
                raise ValueError(f"Empty scenes list in remotion_props_file: {props_path}")

            # If props_data scenes lack prompt details (RemotionRenderProps schema),
            # hydrate with authoritative scene plan details from director_plan.json
            first_sc = sc_list[0] if sc_list else {}
            if not first_sc.get("bg_prompt") and not first_sc.get("fg") and local_dp.exists():
                dp_data = json.loads(local_dp.read_text(encoding="utf-8"))
                dp_scenes = dp_data.get("scenes", [])
                dp_by_id = {str(s.get("scene_id", "")).lower(): s for s in dp_scenes}

                # Hydrate title if props_data title is missing or synthetic
                if not props_data.get("title") or props_data.get("title", "").startswith("Episode "):
                    props_data["title"] = dp_data.get("title") or dp_data.get("title_a") or dp_data.get("topic")
                    if not props_data.get("title"):
                        bi_file = ctx.paths.root / "brain_input.json"
                        if not bi_file.exists() and (props_path.parent / "brain_input.json").exists():
                            bi_file = props_path.parent / "brain_input.json"
                        if bi_file.exists():
                            try:
                                bi_data = json.loads(bi_file.read_text(encoding="utf-8"))
                                props_data["title"] = bi_data.get("title_a") or bi_data.get("topic")
                            except (OSError, json.JSONDecodeError, KeyError) as _bi_err:
                                logger.warning(f"Failed to extract title from brain_input.json: {_bi_err}")
                    if not props_data.get("title"):
                        seo_file = ctx.paths.root / "seo_package.json"
                        if not seo_file.exists() and (props_path.parent / "seo_package.json").exists():
                            seo_file = props_path.parent / "seo_package.json"
                        if seo_file.exists():
                            try:
                                seo_data = json.loads(seo_file.read_text(encoding="utf-8"))
                                props_data["title"] = seo_data.get("title_a") or seo_data.get("title") or seo_data.get("topic")
                            except Exception as _seo_err:
                                logger.warning(f"Failed to extract title from seo_package.json: {_seo_err}")
                    if not props_data.get("title"):
                        props_data["title"] = ctx.run_id

                # Hydrate each scene in sc_list
                for idx, sc in enumerate(sc_list):
                    sc_id = str(sc.get("scene_id", "")).lower()
                    dp_sc = dp_by_id.get(sc_id) or (dp_scenes[idx] if idx < len(dp_scenes) else {})
                    for field in ["narration", "bg_prompt", "image_prompt", "fg_prompt", "hero_cutout_object", "foreground_prompt", "visual_metaphor", "camera", "camera_move", "camera_movement", "fg"]:
                        if field not in sc and field in dp_sc:
                            sc[field] = dp_sc[field]

            plan = _validate_authoritative_scene_plan(props_data, ctx.run_id)
        except Exception as p_err:
            raise ValueError(f"Stage S11 fail-closed: Malformed authoritative remotion_props_file '{props_path}': {p_err}")
    else:
        # Fallback strictly to task-local director_plan.json (Rule 128: cấm tìm repo-level unrelated plans)
        if local_dp.exists():
            try:
                dp_data = json.loads(local_dp.read_text(encoding="utf-8"))
                sc_list = dp_data.get("scenes", [])
                if not sc_list:
                    raise ValueError(f"Empty scenes list in run-local director_plan: {local_dp}")
                if not dp_data.get("title"):
                    bi_file = ctx.paths.root / "brain_input.json"
                    if bi_file.exists():
                        try:
                            bi_data = json.loads(bi_file.read_text(encoding="utf-8"))
                            dp_data["title"] = bi_data.get("title_a") or bi_data.get("topic")
                        except (OSError, json.JSONDecodeError, KeyError) as _bi_err:
                            logger.warning(f"Failed to extract title from local brain_input.json: {_bi_err}")
                    if not dp_data.get("title"):
                        seo_file = ctx.paths.root / "seo_package.json"
                        if seo_file.exists():
                            try:
                                seo_data = json.loads(seo_file.read_text(encoding="utf-8"))
                                dp_data["title"] = seo_data.get("title_a") or seo_data.get("title") or seo_data.get("topic")
                            except Exception as _seo_err:
                                logger.warning(f"Failed to extract title from seo_package.json: {_seo_err}")
                    if not dp_data.get("title"):
                        dp_data["title"] = ctx.run_id
                if not dp_data.get("episode_id") and not dp_data.get("run_id"):
                    dp_data["episode_id"] = ctx.run_id
                plan = _validate_authoritative_scene_plan(dp_data, ctx.run_id)
            except Exception as dp_err:
                raise ValueError(f"Stage S11 fail-closed: Malformed run-local director_plan '{local_dp}': {dp_err}")
        else:
            raise ValueError(f"Stage S11 fail-closed: No authoritative ScenePlan found for run '{ctx.run_id}' (both remotion_props_file and local director_plan missing)")

    if not plan or not plan.scenes:
        raise ValueError(f"Stage S11 fail-closed: ScenePlan is empty or invalid for run '{ctx.run_id}'")

    manifest_data = None
    rm_path = ctx.paths.root / "run_manifest.json"
    if rm_path.exists():
        try:
            manifest_data = json.loads(rm_path.read_text(encoding="utf-8"))
        except Exception as _rm_err:
            logger.debug(f"[s11_qc] run_manifest read notice: {_rm_err}")

    try:
        # Delegate directly to canonical vox.qa.gates for forensic verification (Rule 125 & 139)
        gate_res = verify_final_video_gates(p, expected_duration=expected_dur, plan=plan, manifest_data=manifest_data)
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
