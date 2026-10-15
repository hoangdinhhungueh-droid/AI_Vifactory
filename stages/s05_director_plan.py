#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s05_director_plan.py — Stage S5: Vox-Style Director Plan & Prompts (AVF-STAB-001).

Implements Stage Shape Standard. Encodes Prompt 2 (Director & Image) and Prompt 3 (Universal Video Prompt).
"""

from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Dict, Any, List

from core.contracts.stages import StageID, StageArtifact, Provenance, Scene, Shot
from core.config import RunContext
from core.gates import require_input, emit_artifact

from tools.codemap.runtime import pipeline_stage
from vox.planner import plan_scenes_from_script

STAGE: StageID = StageID.S5_DIRECTOR_PLAN


def build_universal_video_prompt(scene: Scene) -> str:
    """Encodes Prompt 3 from Made by AI Playbook: 0-7s layer-by-layer, 7-10s hold micro-motion."""
    hero_obj = scene.visual_metaphor or "Tactile paper cutout elements"
    color = scene.color_accent or "Vox Yellow #F2C230 and Navy #1B2B4A"
    headline = scene.headline or "EDITORIAL FOCUS"

    parts = [
        "Editorial paper cutout animation in Vox documentary style.",
        f"Animate completed composition: {hero_obj} on Cream Paper #F4F1EA background.",
        f"0.0-2.0s: Tactile entry of bold geometric paper shapes and headline '{headline}'.",
        f"2.0-7.0s: Main cutout elements assemble smoothly with layered drop shadows and deckle white edges.",
        "7.0-10.0s: Spatial anchor locked, subtle micro-shadow breathing <= 2px, zero drift.",
        "Camera: Completely static top-down desk view, crisp focus, no 3D pan or tilt.",
        f"Color Palette: {color} on muted paper texture."
    ]
    return " ".join(parts)


@pipeline_stage(
    id="s05_director_plan",
    order=5,
    name="Dynamic Director Plan & Cutouts",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s04_critic_script"],
    upstream=["s04_critic_script"],
    downstream=["s06_critic_visual"],
    artifacts=["runs/{run_id}/s05_director_plan/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s05_director_plan --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S5: Director Plan & Prompts Forge."""
    start_ts = time.time()
    
    # Read S3 script artifact directly to retrieve scenes
    s3_artifact_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    if not s3_artifact_path.exists():
        raise FileNotFoundError(f"Missing S3 artifact at: {s3_artifact_path}")
    
    raw_scenes = s3_data.get("payload", {}).get("scenes", [])
    script_text = s3_data.get("payload", {}).get("script_text", "")

    # Ground scenes with canonical vox.planner engine (Rule 125 & 139)
    if script_text:
        try:
            vox_plan = plan_scenes_from_script(script_text)
            if vox_plan and vox_plan.scenes and not raw_scenes:
                raw_scenes = [{"scene_id": f"SC_{sc.idx:02d}", "visual_metaphor": sc.bg_prompt, "headline": sc.narration[:30]} for sc in vox_plan.scenes]
        except Exception:
            pass

    acc_pool = ctx.config.video_generation.account_pool or ["acc_01"]
    scenes: List[Scene] = []

    for idx, sc_dict in enumerate(raw_scenes):
        scene = Scene.model_validate(sc_dict)
        shot_id = f"sc_{idx+1:02d}_sh_01"
        uv_prompt = build_universal_video_prompt(scene)
        slot = acc_pool[idx % len(acc_pool)]

        shot = Shot(
            shot_id=shot_id,
            scene_id=scene.scene_id,
            visual_prompt=uv_prompt,
            negative_prompt="photorealistic, 3d render, glossy, blurry, chaotic motion, camera shake",
            seed_image=f"composite_{scene.scene_id.lower()}.png",
            duration_sec=ctx.config.video_generation.duration_per_clip_sec,
            aspect=ctx.config.video_generation.aspect,
            account_slot=slot
        )
        scene.shots = [shot]
        scenes.append(scene)

    payload = {
        "task_id": ctx.run_id,
        "total_scenes": len(scenes),
        "account_slots_used": acc_pool,
        "scenes": [s.model_dump() for s in scenes]
    }

    prov = Provenance(
        generator="stages.s05_director_plan",
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


MAX_USES_PER_ASSET: int = 3
MIN_GAP_SCENES: int = 4

CANONICAL_BEATS: List[str] = [
    "Cold Strike",
    "False Narrative",
    "Forensic Paper Trail",
    "Smoking Gun",
    "Modern Mirror",
]

# 12 Canonical Cinematic Camera Movements (Expanded with VOX 3D & Focus Dynamics)
CANONICAL_CAMERA_MOVES: List[str] = [
    "slow_push_in",
    "snap_zoom",
    "cinematic_pan",
    "macro_tilt",
    "slow_pull_out",
    "handheld_shake",
    "dolly_zoom",
    "focus_breathe_push",
    "continuous_drift",
    "seamless_whip_pan",
    "macro_orbit",
    "whip_zoom",
]


def validate_asset_reuse_limits(scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enforces Vox Masterclass asset diversity invariants: max 3 uses per asset, min gap 4 scenes."""
    bg_usage: Dict[str, List[int]] = {}
    fg_usage: Dict[str, List[int]] = {}
    violations: List[str] = []

    for i, sc in enumerate(scenes):
        bg_k = sc.get("bg_reuse_key") or sc.get("background_reuse_key") or ""
        fg_k = sc.get("fg_reuse_key") or sc.get("foreground_reuse_key") or ""

        if bg_k:
            bg_usage.setdefault(bg_k, []).append(i)
        if fg_k:
            fg_usage.setdefault(fg_k, []).append(i)

    for k, indices in bg_usage.items():
        if len(indices) > MAX_USES_PER_ASSET:
            violations.append(f"BG asset '{k}' overused: {len(indices)} times (max {MAX_USES_PER_ASSET})")
        for a, b in zip(indices, indices[1:]):
            if b - a < MIN_GAP_SCENES:
                violations.append(f"BG asset '{k}' repeated too quickly at scenes {a} and {b} (gap {b-a} < {MIN_GAP_SCENES})")

    for k, indices in fg_usage.items():
        if len(indices) > MAX_USES_PER_ASSET:
            violations.append(f"FG asset '{k}' overused: {len(indices)} times (max {MAX_USES_PER_ASSET})")
        for a, b in zip(indices, indices[1:]):
            if b - a < MIN_GAP_SCENES:
                violations.append(f"FG asset '{k}' repeated too quickly at scenes {a} and {b} (gap {b-a} < {MIN_GAP_SCENES})")

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "bg_usage": {k: len(v) for k, v in bg_usage.items()},
        "fg_usage": {k: len(v) for k, v in fg_usage.items()}
    }


def validate_cinematic_tokens(tokens: list | None, narration: str = "") -> list:
    """Rule 128 & Rule 132: Validate and sanitize cinematic flow & transition tokens against the 38 canonical tokens.
    Provides deterministic fallback if LLM omitted tokens.
    """
    valid_set = {
        "/straightdown", "/groundlevel", "/birdseye", "/firstperson", "/secondview",
        "/closecrop", "/tightframe", "/extremeclose", "/thirdgrid", "/innerframe",
        "/darkmood", "/edgelight", "/spotbeam", "/lightrays", "/sunsetglow", "/duskhour",
        "/filmlook", "/highcontrast", "/edgefade", "/digitalglitch",
        "/whip_pan", "/smash_cut", "/match_cut", "/ink_bleed", "/zoom_through",
        "/light_leak", "/paper_tear", "/circle_wipe",
        "/dolly_zoom", "/macro_orbit", "/focus_breathe", "/continuous_drift", "/whip_zoom",
        "/map_pin_drop", "/callout_circle", "/route_draw", "/counter_countup", "/paper_stopmotion"
    }
    cleaned = []
    if isinstance(tokens, list):
        for tok in tokens:
            if isinstance(tok, str):
                t_str = tok.strip()
                if not t_str.startswith("/"):
                    t_str = f"/{t_str}"
                if t_str in valid_set and t_str not in cleaned:
                    cleaned.append(t_str)

    if not cleaned and narration:
        t_low = narration.lower()
        if any(k in t_low for k in ["bản đồ", "tọa độ", "vị trí", "biên giới", "hành trình", "tuyến đường", "map", "coordinate", "border", "route", "chokepoint"]):
            cleaned = ["/route_draw", "/callout_circle", "/map_pin_drop"]
        elif any(k in t_low for k in ["con số", "tỷ", "triệu", "đô la", "usd", "khoản tiền", "thiệt hại", "counter", "metric", "loss", "billion"]):
            cleaned = ["/counter_countup", "/snap_zoom", "/spotbeam"]
        elif any(k in t_low for k in ["hồ sơ", "con dấu", "hợp đồng", "bản án", "bàn làm việc", "dossier", "contract", "verdict", "document", "ledger", "seal", "stamp"]):
            cleaned = ["/straightdown", "/paper_stopmotion", "/edgelight"]
        elif any(k in t_low for k in ["biến mất", "toàn cảnh", "thành phố", "tòa nhà", "quốc gia", "hệ thống", "skyline", "scale"]):
            cleaned = ["/birdseye", "/duskhour", "/filmlook"]
        elif any(k in t_low for k in ["khuôn mặt", "nói", "thì thầm", "khai nhận", "nhìn thẳng", "eyes", "whisper", "confession"]):
            cleaned = ["/tightframe", "/focus_breathe", "/highcontrast"]
        elif any(k in t_low for k in ["chấn động", "bất ngờ", "sụp đổ", "shock", "collapse", "crisis", "fraud"]):
            cleaned = ["/smash_cut", "/dolly_zoom", "/darkmood"]
        else:
            cleaned = ["/thirdgrid", "/darkmood"]

    return cleaned[:3]


def sanitize_beat_spoken_for_llm(spoken_list: list) -> list:
    """
    Prune heavy Whisper audio metadata (word-level timestamps, score arrays,
    and karaoke highlight tokens) from LLM director payload.
    Preserves exact sentence text, sentence ID, and duration budget.
    Downstream Remotion props generator retains full verbatim spoken_sentences.json.
    """
    if not spoken_list:
        return []
    lean = []
    for s in spoken_list:
        if not isinstance(s, dict):
            continue
        duration_s = s.get("duration_sec")
        if duration_s is None:
            start = s.get("start")
            end = s.get("end")
            if start is not None and end is not None:
                if end <= start:
                    raise ValueError(f"Invalid sentence timestamp: end ({end}) <= start ({start}) violates Rule 118 & Rule 120")
                duration_s = round(end - start, 2)
            else:
                duration_s = 5.0
        elif duration_s <= 0:
            raise ValueError(f"Invalid duration_sec ({duration_s}) <= 0 violates Rule 118 & Rule 120")
        lean.append({
            "sentence_id": s.get("sentence_id") or s.get("id") or f"sent_{len(lean)+1:03d}",
            "text": s.get("text") or s.get("sentence") or "",
            "duration_sec": duration_s,
            "beat_index": s.get("beat_index", 1)
        })
    return lean

_sanitize_beat_spoken_for_llm = sanitize_beat_spoken_for_llm


def resolve_market_redacted_terms(market: str = "EN") -> List[str]:
    """Rule 128: Market-aware redacted terms resolver preventing CJK token bleed into EN documents."""
    m = (market or "EN").upper().strip()
    if m in ("EN", "US", "UK"):
        return ["CONFIDENTIAL", "UNVERIFIED", "RESTRICTED", "CLASSIFIED"]
    elif m == "JP":
        return ["CONFIDENTIAL", "UNVERIFIED", "不適切", "不正"]
    elif m == "KR":
        return ["기밀", "미확인", "부적절", "위반"]
    return ["CONFIDENTIAL", "UNVERIFIED", "RESTRICTED"]


