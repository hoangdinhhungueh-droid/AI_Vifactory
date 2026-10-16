#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s03_script.py — Stage S3: 5-Beat Investigative Docudrama Script (AVF-STAB-001).

Implements Stage Shape Standard. Produces structured Scene objects governed by Rule 444 & 445.
"""

from __future__ import annotations

import time
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

from core.contracts.stages import StageID, StageArtifact, Provenance, Scene
from core.config import RunContext
from core.gates import require_input, emit_artifact
from tools.codemap.runtime import pipeline_stage

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

    # Check if a pre-existing story or director plan exists in the episode directory
    existing_scenes: List[Scene] = []
    plan_file = ctx.paths.root / "director_plan.json"
    if plan_file.exists():
        try:
            raw_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            for s in raw_plan.get("scenes", []):
                existing_scenes.append(Scene(
                    scene_id=s.get("scene_id", "SCENE_01"),
                    sequence_block=s.get("sequence_block", "block_1_act_i"),
                    narration=s.get("sentence") or s.get("narration") or "Narration text",
                    core_idea=s.get("core_idea", "Core dramatic premise"),
                    headline=s.get("bilingual_headline") or s.get("headline"),
                    visual_metaphor=s.get("visual_metaphor"),
                    color_accent=s.get("color_accent"),
                    duration_est_sec=float(s.get("duration_est_sec", 6.0))
                ))
        except Exception as _plan_err:
            logger.debug("[s03_script] Notice reading existing director plan: %s", _plan_err)

    if not existing_scenes:
        # Generate default canonical 5-Beat scenes
        default_beats = [
            ("SCENE_01", "hook", "block_1_act_i", f"In late 2026, an unprecedented regulatory decision permanently overturned the status quo of {topic}.", "THE SHOCK VERDICT", "A monumental legal document torn cleanly across jurisdictional borders.", "Vox Yellow #F2C230 & Navy #1B2B4A"),
            ("SCENE_02", "context", "block_2_act_i", "For years, the public narrative claimed complete compliance, while domestic operators bore a 100x tax disparity.", "THE FALSE FRONT", "Two asymmetrical scale weights demonstrating 100x structural disparity.", "Terracotta #C85A32 & Cream Paper #F4F1EA"),
            ("SCENE_03", "tension", "block_3_act_ii", "A forensic examination of the contract paperwork reveals how 65% of domestic revenue was rerouted offshore.", "65% OFFSHORE DRAIN", "A bold paper pipeline splitting into a domestic trickle and an offshore torrent.", "Vox Yellow #F2C230 & Charcoal #1A1A1A"),
            ("SCENE_04", "reveal", "block_4_act_iii", "The smoking gun was not hidden secrecy, but an institutional loophole encoded directly into legacy tax law.", "THE LEGAL VACUUM", "An architectural blueprint with dotted dashed lines indicating a missing entity.", "Muted Gold #D4AF37 & Navy #1B2B4A"),
            ("SCENE_05", "payoff", "block_5_act_iv", "This landmark ruling marks the beginning of an era where digital presence directly mandates fiscal accountability.", "THE LIVING WARNING", "A modern smartphone screen casting a long paper shadow over an international map.", "Vox Yellow #F2C230 & Terracotta #C85A32"),
        ]
        for sc_id, role, block, text, hd, meta, col in default_beats:
            existing_scenes.append(Scene(
                scene_id=sc_id,
                sequence_block=block,
                beat_role=role,
                narration=text,
                headline=hd,
                visual_metaphor=meta,
                color_accent=col,
                duration_est_sec=6.0
            ))

    # Apply limits from profile if specified (e.g. e2e_min limits to 1 scene)
    max_sc = ctx.config.limits.max_scenes
    if max_sc > 0 and len(existing_scenes) > max_sc:
        scenes = existing_scenes[:max_sc]
    else:
        scenes = existing_scenes

    payload = {
        "task_id": ctx.run_id,
        "topic": topic,
        "total_scenes": len(scenes),
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
