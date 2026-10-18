#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s03_script.py — Stage S3: 5-Beat Investigative Docudrama Script (AVF-STAB-001).

Implements Stage Shape Standard. Produces structured Scene objects governed by Rule 444 & 445.
"""

from __future__ import annotations

import logging
import time
from typing import List

from core.config import RunContext
from core.contracts.stages import Provenance, Scene, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S3_SCRIPT


@pipeline_stage(
    id="s03_script",
    order=3,
    name="5-Beat Docudrama Script",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s02_research"],
    upstream=["s02_research"],
    downstream=["s04_critic_script", "s09_voice_tts"],
    artifacts=["runs/{run_id}/s03_script/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s03_script --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S3: 5-Beat Docudrama Script Generation."""
    start_ts = time.time()
    s2_art = require_input(STAGE, ctx.paths)
    topic = s2_art.payload.get("topic", "Corporate Monopoly Inquest")

    # Strict B2 Spoken Script Ingestion (Rule 118 Zero-Mock & Rule 125 Single Pipeline)
    from core.contracts.b2_b3_contract import load_spoken_script

    market = "JA" if "JP_" in ctx.run_id else ("KO" if "KR_" in ctx.run_id else ("VI" if "VN_" in ctx.run_id else "EN"))
    spoken_script = load_spoken_script(ctx.paths.root, episode_id=ctx.run_id, market=market)

    # Convert B2 spoken beats into canonical Scene objects
    total_beats = len(spoken_script.beats)
    all_scenes: List[Scene] = []

    for idx, b in enumerate(spoken_script.beats, start=1):
        pos = idx / max(1, total_beats)
        if pos <= 0.20:
            block_slug = "act_i_catalyst"
            role = "hook"
        elif pos <= 0.40:
            block_slug = "act_ii_false_front"
            role = "context"
        elif pos <= 0.65:
            block_slug = "act_iii_forensic_trail"
            role = "tension"
        elif pos <= 0.85:
            block_slug = "act_iv_smoking_gun"
            role = "reveal"
        else:
            block_slug = "act_v_living_warning"
            role = "payoff"

        all_scenes.append(Scene(
            scene_id=f"SCENE_{idx:02d}",
            sequence_block=f"block_{idx}_{block_slug}",
            beat_role=role,
            narration=b.text,
            headline=f"BEAT {idx:02d}",
            visual_metaphor=f"Tactile editorial evidence for beat {idx:02d}",
            color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
            duration_est_sec=6.0
        ))

    # Apply limits from profile if specified (e.g. e2e_min limits to 1 scene)
    max_sc = ctx.config.limits.max_scenes
    if max_sc > 0 and len(all_scenes) > max_sc:
        scenes = all_scenes[:max_sc]
    else:
        scenes = all_scenes

    payload = {
        "task_id": ctx.run_id,
        "topic": topic,
        "total_scenes": len(scenes),
        "b2_source_path": spoken_script.source_path,
        "b2_source_sha256": spoken_script.source_sha256,
        "script_text": "\n".join([s.narration for s in scenes]),
        "scenes": [s.model_dump() for s in scenes]
    }

    prov = Provenance(
        generator="stages.s03_script",
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
