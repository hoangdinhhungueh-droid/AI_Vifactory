#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s05_director_plan.py — Stage S5: Vox-Style Director Plan & Prompts (AVF-STAB-001).

Implements Stage Shape Standard. Encodes Prompt 2 (Director & Image) and Prompt 3 (Universal Video Prompt).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

from core.config import RunContext
from core.contracts.stages import Provenance, Scene, Shot, StageArtifact, StageID
from core.gates import emit_artifact, validate_artifact
from tools.codemap.runtime import pipeline_stage
from vox.planner import plan_scenes_from_script

logger = logging.getLogger("s05_director_plan")

STAGE: StageID = StageID.S5_DIRECTOR_PLAN


def build_vox_scene_prompts(
    scene: Scene,
    idx: int,
    total_scenes: int,
    prev_scene: Optional[Scene] = None
) -> Dict[str, Any]:
    """Decomposes scene into rich Vox Physical Objects, Kinematics, Omni and Google Flow I2V Prompts."""
    headline = scene.headline or f"BEAT {idx+1:02d}"
    color = scene.color_accent or "Vox Yellow #F2C230 & Navy #1B2B4A"
    hero_obj = scene.visual_metaphor or f"Tactile paper document representing beat {idx+1:02d}"

    # Pick deterministic camera movement
    camera_move = CANONICAL_CAMERA_MOVES[idx % len(CANONICAL_CAMERA_MOVES)]

    # 1. Physical Objects Breakdown
    objects = [
        {
            "id": f"o{idx+1}_1",
            "name": hero_obj,
            "attributes": ["tactile paper cutout", "2-4px deckle edge", "soft drop shadow"],
            "role": "primary"
        },
        {
            "id": f"o{idx+1}_2",
            "name": "crimson forensic seal and brass anchor pin",
            "attributes": ["crimson wax imprint", "brass patina pin"],
            "role": "secondary"
        },
        {
            "id": f"o{idx+1}_3",
            "name": "aged cream newsprint desk backdrop",
            "attributes": ["#F4F1EA", "vintage print halftone grid", "creased archival paper"],
            "role": "backdrop"
        }
    ]

    # 2. Kinematics Actions Breakdown
    actions = [
        {
            "subject": f"o{idx+1}_1",
            "verb": "slides_in",
            "target": "center_stage",
            "motion": "smooth_slide_left_to_right",
            "intensity": "low",
            "role": "primary"
        },
        {
            "subject": f"o{idx+1}_2",
            "verb": "stamps",
            "target": f"o{idx+1}_1",
            "motion": "downward_impact",
            "intensity": "high",
            "role": "secondary"
        }
    ]

    # 3. Kinematic Motion Track
    motion_track = {
        "entry_action": f"0.0-2.0s: Tactile entry of {hero_obj} sliding into center stage with soft paper drop shadow.",
        "assembly_step": "2.0-7.0s: Crimson seal stamps firmly onto the document; paper cutouts assemble and lock into spatial anchor.",
        "spatial_anchor": "Center-left quadrant of canvas, permanently locked as anchor for subsequent scene.",
        "camera_rule": "Completely static top-down desk view, crisp focus, zero 3D camera pan/tilt."
    }

    # 4. Graphic Typography
    graphic_typo = {
        "headline": headline,
        "english_tag": "FORENSIC EVIDENCE",
        "color_bar": color,
        "position": "Top-left quadrant, occupying 25% negative space"
    }

    # 5. Visual Continuity Link
    continuity_link = (
        f"Object o{idx+1}_1 remains locked on the newsprint desk; "
        f"Scene {idx+2 if idx+1 < total_scenes else 'Outro'} physically builds upon this exact foundation."
    )

    # 6. 5-Layer Image Prompt (Master Prompt: vox_b3_director_image_prompt.md)
    image_prompt = (
        f"Editorial investigative documentary frame in signature VOX paper-cut collage style. "
        f"[Layer 1: Aged Cream Newsprint Desk #F4F1EA with subtle print halftone grid] -> "
        f"[Layer 2: bold flat geometric color block in {color}] -> "
        f"[Layer 3: negative space reserved for large bold editorial typography '{headline}', occupying 25% of frame] -> "
        f"[Layer 4: high-contrast tactile paper cutout subject with crisp 2-4px white deckle edge and realistic soft drop shadow: {hero_obj}. "
        f"Interacting elements: crimson forensic seal stamp and brass pin] -> "
        f"[Layer 5: vintage print ink texture, natural paper grain, subtle fold creases, authentic newspaper print misregistration]. "
        f"Strictly locked color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A on Off-white Cream #F4F1EA. "
        f"Clear object-assembly composition, strong editorial hierarchy, tactile paper craft. "
        f"Negative prompt: no clutter, no unnecessary objects, no glossy 3D rendering, no photorealistic background, "
        f"no oversaturated rainbow colors, maintain clean premium VOX editorial collage."
    )

    # 7. Omni I2V Prompt (Action-centric, motion-first)
    i2v_omni = (
        f"Tactile paper cutout animation in signature Vox documentary style. "
        f"Animate composition: {hero_obj} on Aged Cream Paper #F4F1EA desk. "
        f"Hero cutout slides in smoothly from left edge, crimson verification stamp impacts firmly at 3.0s, "
        f"holding locked spatial anchor with subtle paper micro-breathing <= 2px. "
        f"Static top-down camera, zero camera drift."
    )

    # 8. Google Flow Veo Fast I2V Prompt (Universal Prompt 3)
    i2v_google_flow = (
        f"Editorial paper cutout animation in Vox documentary style. "
        f"Animate completed composition: {hero_obj} on Cream Paper #F4F1EA background. "
        f"0.0-2.0s: Tactile entry of bold geometric paper shapes and headline '{headline}'. "
        f"2.0-7.0s: Main cutout elements assemble smoothly with layered drop shadows and deckle white edges. "
        f"7.0-10.0s: Spatial anchor locked, subtle micro-shadow breathing <= 2px, zero drift. "
        f"Camera: Completely static top-down desk view, crisp focus, no 3D pan or tilt. "
        f"Color Palette: {color} on muted paper texture."
    )

    return {
        "canvas_workspace": "Aged Cream Newsprint Desk #F4F1EA with subtle print halftone grid",
        "hero_cutout_object": hero_obj,
        "interacting_objects": ["crimson forensic seal stamp", "brass anchor pin"],
        "motion_track_and_assembly": motion_track,
        "graphic_typography": graphic_typo,
        "visual_continuity_link_to_next": continuity_link,
        "objects": objects,
        "actions": actions,
        "camera_move": camera_move,
        "image_prompt": image_prompt,
        "i2v_prompt_omni": i2v_omni,
        "i2v_prompt_google_flow": i2v_google_flow,
    }


def build_universal_video_prompt(scene: Scene) -> str:
    """Encodes Prompt 3 from Made by AI Playbook: 0-7s layer-by-layer, 7-10s hold micro-motion."""
    return scene.i2v_prompt_google_flow or (
        f"Editorial paper cutout animation in Vox documentary style. "
        f"Animate completed composition: {scene.visual_metaphor or 'Tactile paper elements'} on Cream Paper #F4F1EA background. "
        f"0.0-2.0s: Tactile entry of bold geometric paper shapes and headline '{scene.headline or 'EDITORIAL FOCUS'}'. "
        f"2.0-7.0s: Main cutout elements assemble smoothly with layered drop shadows and deckle white edges. "
        f"7.0-10.0s: Spatial anchor locked, subtle micro-shadow breathing <= 2px, zero drift. "
        f"Camera: Completely static top-down desk view, crisp focus, no 3D pan or tilt."
    )


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
    """Executes Stage S5: Director Plan & Prompts Forge with Vox Kinematics."""
    start_ts = time.time()

    # Read and validate S3 script artifact schema (Rule 121, Rule 139)
    s3_artifact_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    if not s3_artifact_path.exists():
        raise FileNotFoundError(f"Missing S3 artifact at: {s3_artifact_path}")

    try:
        with open(s3_artifact_path, "r", encoding="utf-8") as f:
            s3_raw = json.load(f)
    except Exception as parse_err:
        raise RuntimeError(f"Failed to parse S3 script artifact JSON at {s3_artifact_path}: {parse_err}") from parse_err

    s3_artifact = validate_artifact(StageID.S3_SCRIPT, s3_raw)
    raw_scenes = s3_artifact.payload.get("scenes", [])
    b2_source_path = s3_artifact.payload.get("b2_source_path", "")
    b2_source_sha256 = s3_artifact.payload.get("b2_source_sha256", "")

    if not raw_scenes:
        logger.critical("[s05_director_plan] No scenes available in S3 artifact (fail-closed)")
        raise RuntimeError("Stage S05 failed closed: no scenes found in S3 artifact")

    # Load master prompt sha256 for cryptographic provenance
    master_prompt_path = ctx.paths.repo_root / "config" / "prompts" / "vox_b3_director_image_prompt.md"
    prompt_sha256 = ""
    if master_prompt_path.exists():
        import hashlib
        prompt_sha256 = hashlib.sha256(master_prompt_path.read_bytes()).hexdigest()

    acc_pool = ctx.config.video_generation.account_pool or ["acc_01"]
    total_sc = len(raw_scenes)
    scenes: List[Scene] = []
    prev_scene: Optional[Scene] = None

    for idx, sc_dict in enumerate(raw_scenes):
        scene = Scene.model_validate(sc_dict)
        slot = acc_pool[idx % len(acc_pool)]
        shot_id = f"sc_{idx+1:02d}_sh_01"

        # Decompose into full Vox Object-Assembly Kinematics
        vox_meta = build_vox_scene_prompts(scene, idx=idx, total_scenes=total_sc, prev_scene=prev_scene)
        scene.canvas_workspace = vox_meta["canvas_workspace"]
        scene.hero_cutout_object = vox_meta["hero_cutout_object"]
        scene.interacting_objects = vox_meta["interacting_objects"]
        scene.motion_track_and_assembly = vox_meta["motion_track_and_assembly"]
        scene.graphic_typography = vox_meta["graphic_typography"]
        scene.visual_continuity_link_to_next = vox_meta["visual_continuity_link_to_next"]
        scene.objects = vox_meta["objects"]
        scene.actions = vox_meta["actions"]
        scene.camera_move = vox_meta["camera_move"]
        scene.image_prompt = vox_meta["image_prompt"]
        scene.i2v_prompt_omni = vox_meta["i2v_prompt_omni"]
        scene.i2v_prompt_google_flow = vox_meta["i2v_prompt_google_flow"]

        shot = Shot(
            shot_id=shot_id,
            scene_id=scene.scene_id,
            visual_prompt=vox_meta["i2v_prompt_google_flow"],
            negative_prompt="photorealistic, 3d render, glossy, blurry, chaotic motion, camera shake",
            seed_image=f"composite_{scene.scene_id.lower()}.png",
            duration_sec=ctx.config.video_generation.duration_per_clip_sec,
            aspect=ctx.config.video_generation.aspect,
            account_slot=slot
        )
        scene.shots = [shot]
        scenes.append(scene)
        prev_scene = scene

    payload = {
        "task_id": ctx.run_id,
        "format": "VOX_CONTINUOUS_OBJECT_ASSEMBLY_COLLAGE",
        "total_scenes": len(scenes),
        "account_slots_used": acc_pool,
        "source": {
            "b2_path": b2_source_path,
            "b2_sha256": b2_source_sha256
        },
        "prompt": {
            "path": str(master_prompt_path),
            "sha256": prompt_sha256
        },
        "scenes": [s.model_dump() for s in scenes]
    }

    prov = Provenance(
        generator="stages.s05_director_plan",
        prompt_id=prompt_sha256[:16] if prompt_sha256 else None,
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


