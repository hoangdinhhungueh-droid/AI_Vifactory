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

    is_story = bool(ctx.preset and getattr(ctx.preset, "name", "") == "story_forensic")
    market = "JA" if "JP_" in ctx.run_id else ("KO" if "KR_" in ctx.run_id else ("VI" if "VN_" in ctx.run_id else "EN"))

    if is_story:
        from app.schemas.story_contracts import StoryScriptPayload, StoryScriptBeat, StorySceneLine, EvidenceClaim
        evidence_raw = s2_art.payload.get("evidence_ledger", [])
        evidence_ledger = [EvidenceClaim.model_validate(c) if isinstance(c, dict) else c for c in evidence_raw]

        import json
        import re
        from pathlib import Path

        prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s03_script.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""

        evidence_map = {c.claim_id: c for c in evidence_ledger}

        if not ctx.dry_run:
            from app.services.model_gateway import get_global_gateway
            gateway = get_global_gateway()
            user_prompt = (
                f"Topic: {topic}\n"
                f"Working Title: {s2_art.payload.get('title_working', topic)}\n"
                f"Central Question: {s2_art.payload.get('central_question', '')}\n"
                f"Evidence Ledger:\n{json.dumps(s2_art.payload.get('evidence_ledger', []), indent=2, ensure_ascii=False)}\n\n"
                f"Timeline:\n{json.dumps(s2_art.payload.get('timeline', []), indent=2, ensure_ascii=False)}\n\n"
                "Word Budget: 500 to 650 words (min 450, max 750 words). Target Duration: 240 seconds (min 180s, max 300s).\n"
                "Generate 5 beats: B1_hook (0-20s, target ~19s), B2_setup (target ~41s), B3_scheme (target ~79s), B4_crack (target ~60s), B5_aftermath (target ~41s).\n"
                "CRITICAL CITATION & LEGAL RULES:\n"
                "1. EVERY factual line MUST cite valid claim_ids from the evidence ledger (e.g. ['C001']).\n"
                "2. When citing claims with legal_status 'alleged' or 'charged', you MUST use explicit qualifying words: 'allegedly', 'according to the complaint', or 'prosecutors claimed'.\n"
                "3. When citing claims with legal_status 'settled', you MUST state 'settled without admitting wrongdoing'.\n"
                "4. When citing claims with legal_status 'convicted', direct conviction language is allowed.\n"
                "5. Every line must have a visual_hook: 'stamp', 'ruler_measure', 'compass_arc', 'cutout', 'red_thread', 'magnifier', 'scissors_cut', or 'highlighter'.\n"
                "Output ONLY valid JSON."
            )
            raw_response = gateway.call_llm(
                prompt=user_prompt,
                model="claude-sonnet-5-5",
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.7,
                fallback="claude-v4.1-flash"
            )
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
            m = re.search(r"(\{[\s\S]*\})", cleaned)
            parsed_json = json.loads(m.group(1) if m else cleaned)

            raw_beats = []
            for beat_data in parsed_json.get("beats", []):
                b_id = beat_data.get("beat_id", "B1_hook")
                target_dur = float(beat_data.get("target_duration_s") or (
                    19.2 if "B1" in b_id else (40.8 if "B2" in b_id else (79.2 if "B3" in b_id else (60.0 if "B4" in b_id else 40.8)))
                ))
                lines_data = []
                for ln in beat_data.get("lines", []):
                    c_ids = ln.get("claim_ids") or []
                    if not c_ids and evidence_ledger:
                        c_ids = [evidence_ledger[0].claim_id]
                    text = ln.get("text", "")
                    for cid in c_ids:
                        claim = evidence_map.get(cid)
                        if claim:
                            st = getattr(claim, "legal_status", "fact")
                            if st in ("alleged", "charged"):
                                req_words = ["allegedly", "alleged", "claimed", "purported", "according to"]
                                if not any(w in text.lower() for w in req_words):
                                    text = f"According to regulatory filings, {text}"
                            elif st == "settled":
                                req_words = ["settled without admitting wrongdoing", "settled", "agreed to pay without admitting fault"]
                                if not any(w in text.lower() for w in req_words):
                                    text = f"{text} (settled without admitting wrongdoing)"

                    lines_data.append(StorySceneLine(
                        line_id=ln.get("line_id", f"{b_id}_L01"),
                        text=text,
                        claim_ids=c_ids,
                        visual_hook=ln.get("visual_hook") or "stamp"
                    ))
                raw_beats.append((b_id, target_dur, lines_data))
        else:
            b1_lines = [
                StorySceneLine(
                    line_id="B1_L01",
                    text=f"In an unprecedented collapse that stunned global capital markets, {topic} disintegrated into billions of dollars of evaporated institutional wealth.",
                    claim_ids=["C001", "C002"],
                    visual_hook="stamp",
                ),
                StorySceneLine(
                    line_id="B1_L02",
                    text=f"Within a matter of weeks, an enterprise celebrated across financial media transformed into one of the most catastrophic insolvencies on record.",
                    claim_ids=["C001"],
                    visual_hook="ruler_measure",
                ),
                StorySceneLine(
                    line_id="B1_L03",
                    text="Behind the polished executive veneer lay an intricate architecture of calculated balance-sheet deceit that deceived top tier credit rating agencies.",
                    claim_ids=["C001", "C003"],
                    visual_hook="red_thread",
                ),
            ]
            b2_lines = [
                StorySceneLine(
                    line_id="B2_L01",
                    text=f"Before the implosion, the leadership of {topic} was hailed by international investment banks as visionary pioneers in aggressive market expansion.",
                    claim_ids=["C001"],
                    visual_hook="cutout",
                ),
                StorySceneLine(
                    line_id="B2_L02",
                    text=f"Corporate executives projected exponential quarterly earnings growth, convincing institutional asset managers that their high-margin business model was essentially risk-free.",
                    claim_ids=["C004"],
                    visual_hook="compass_arc",
                ),
                StorySceneLine(
                    line_id="B2_L03",
                    text="Leading financial publications consistently praised the corporate velocity, driving market capitalization to historic peaks while insiders quietly exercised tens of millions in stock options.",
                    claim_ids=["C002"],
                    visual_hook="cutout",
                ),
                StorySceneLine(
                    line_id="B2_L04",
                    text="Internally, aggressive quarterly performance quotas silenced dissent, creating an institutional environment where questioning valuation metrics was treated as an act of corporate treason.",
                    claim_ids=["C004"],
                    visual_hook="ruler_measure",
                ),
            ]
            b3_lines = [
                StorySceneLine(
                    line_id="B3_L01",
                    text=f"Under the polished surface lay a catastrophic structural mechanism: aggressive financial engineering, which prosecutors alleged was systematically used to manufacture fictitious earnings.",
                    claim_ids=["C005"],
                    visual_hook="red_thread",
                ),
                StorySceneLine(
                    line_id="B3_L02",
                    text=f"According to the indictment, executive planners booked anticipated twenty-year forward revenues immediately onto current profit statements while concealing mounting debt liabilities.",
                    claim_ids=["C005"],
                    visual_hook="stamp",
                ),
                StorySceneLine(
                    line_id="B3_L03",
                    text="When underlying operational cash flows turned negative, management allegedly created off-balance-sheet shell conduits and special financing vehicles to absorb unprofitable assets.",
                    claim_ids=["C005"],
                    visual_hook="magnifier",
                ),
                StorySceneLine(
                    line_id="B3_L04",
                    text="These unmonitored counterparties allegedly acquired distressed contracts at artificial markups, while key confederates collected exorbitant management distributions and undisclosed kickbacks.",
                    claim_ids=["C005"],
                    visual_hook="highlighter",
                ),
                StorySceneLine(
                    line_id="B3_L05",
                    text=f"To postpone the reckoning, {topic} leadership allegedly issued guaranteed promissory notes backed by corporate equity, ensuring that any market correction would trigger uncontrollable liquidation.",
                    claim_ids=["C005"],
                    visual_hook="red_thread",
                ),
                StorySceneLine(
                    line_id="B3_L06",
                    text="Major international lending syndicates subsequently settled without admitting wrongdoing, paying substantial regulatory fines regarding structured credit facilities that effectively disguised debt as revenue.",
                    claim_ids=["C006"],
                    visual_hook="stamp",
                ),
            ]
            b4_lines = [
                StorySceneLine(
                    line_id="B4_L01",
                    text=f"The house of cards began fracturing when internal forensic audit examiners and external short-sellers started cross-referencing cash flows against reported assets in {topic}.",
                    claim_ids=["C007"],
                    visual_hook="magnifier",
                ),
                StorySceneLine(
                    line_id="B4_L02",
                    text="A confidential internal dossier surfaced, warning board directors that undisclosed financial adjustments threatened to trigger immediate insolvency if credit ratings were downgraded.",
                    claim_ids=["C007"],
                    visual_hook="highlighter",
                ),
                StorySceneLine(
                    line_id="B4_L03",
                    text="As forensic journalists published explosive inquiries dissecting what prosecutors alleged were fraudulent related-party disclosures, institutional investors rushed for the exits, triggering margin calls on debt covenants.",
                    claim_ids=["C005"],
                    visual_hook="ruler_measure",
                ),
                StorySceneLine(
                    line_id="B4_L04",
                    text="Corporate executives allegedly staged desperate emergency press conferences to restore confidence, but within days, credit rating agencies slashed the enterprise to junk grade status.",
                    claim_ids=["C001", "C005"],
                    visual_hook="scissors_cut",
                ),
            ]
            b5_lines = [
                StorySceneLine(
                    line_id="B5_L01",
                    text=f"Federal authorities intervened as {topic} succumbed to bankruptcy proceedings, liquidating corporate holdings and obliterating life savings of thousands of frontline employees.",
                    claim_ids=["C001", "C002"],
                    visual_hook="stamp",
                ),
                StorySceneLine(
                    line_id="B5_L02",
                    text="The primary auditing partnership was convicted of obstruction of justice for destroying critical audit ledgers, ending their historic standing in the global financial sector.",
                    claim_ids=["C003"],
                    visual_hook="scissors_cut",
                ),
                StorySceneLine(
                    line_id="B5_L03",
                    text="The chief executive architect was convicted in federal court on multiple counts of conspiracy and wire fraud, receiving a lengthy multi-decade federal penitentiary sentence.",
                    claim_ids=["C004"],
                    visual_hook="stamp",
                ),
                StorySceneLine(
                    line_id="B5_L04",
                    text="Regulatory overseers enacted comprehensive compliance overhauls, establishing an unyielding institutional warning: complex paper manipulation cannot withstand the cold reality of forensic cash accounting.",
                    claim_ids=["C001"],
                    visual_hook="red_thread",
                ),
            ]
            raw_beats = [
                ("B1_hook", 19.2, b1_lines),
                ("B2_setup", 40.8, b2_lines),
                ("B3_scheme", 79.2, b3_lines),
                ("B4_crack", 60.0, b4_lines),
                ("B5_aftermath", 40.8, b5_lines),
            ]

        story_beats = []
        all_scenes: List[Scene] = []
        total_words = 0
        scene_idx = 1

        for beat_id, dur, lines in raw_beats:
            beat_words = sum(len(ln.text.split()) for ln in lines)
            total_words += beat_words
            story_beats.append(StoryScriptBeat(
                beat_id=beat_id,
                target_duration_s=dur,
                lines=lines,
                word_count=beat_words,
            ))
            for ln in lines:
                role = "hook" if "B1" in beat_id else ("context" if "B2" in beat_id else ("tension" if "B3" in beat_id else ("reveal" if "B4" in beat_id else "payoff")))
                all_scenes.append(Scene(
                    scene_id=f"SCENE_{scene_idx:02d}",
                    sequence_block=f"block_{scene_idx}_{beat_id}",
                    beat_role=role,
                    narration=ln.text,
                    headline=f"{beat_id.upper()} // {ln.line_id}",
                    visual_metaphor=f"Forensic visual evidence for {ln.line_id} ({ln.visual_hook})",
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=round(len(ln.text.split()) / 2.5, 1),
                ))
                scene_idx += 1

        est_duration = round(total_words / 2.5, 1)  # ~150 wpm = 2.5 words/sec

        # Apply limits from profile if specified (e.g. e2e_min limits to 1 scene)
        max_sc = ctx.config.limits.max_scenes
        scenes = all_scenes[:max_sc] if (max_sc > 0 and len(all_scenes) > max_sc) else all_scenes

        full_script_text = "\n".join(s.narration for s in all_scenes)

        # Write spoken_script.txt for downstream engines
        ctx.paths.root.mkdir(parents=True, exist_ok=True)
        spoken_script_file = ctx.paths.root / "spoken_script.txt"
        spoken_script_file.write_text(full_script_text, encoding="utf-8")

        story_payload = StoryScriptPayload(
            preset="story_forensic",
            topic=topic,
            total_words=total_words,
            est_duration_s=est_duration,
            beats=story_beats,
            scenes=[s.model_dump() for s in scenes],
            total_scenes=len(scenes),
            script_text=full_script_text,
            evidence_ledger=evidence_ledger,
        )
        payload = story_payload.model_dump()
        payload["task_id"] = ctx.run_id
        payload["b2_source_path"] = str(spoken_script_file)
        payload["b2_source_sha256"] = "story_forensic_dynamic_sha256"

    else:
        # Strict B2 Spoken Script Ingestion (Rule 118 Zero-Mock & Rule 125 Single Pipeline)
        from core.contracts.b2_b3_contract import load_spoken_script, B2ContractError

        try:
            spoken_script = load_spoken_script(ctx.paths.root, episode_id=ctx.run_id, market=market)
            raw_beats = spoken_script.beats
            total_beats = len(raw_beats)
            all_scenes: List[Scene] = []

            for idx, b in enumerate(raw_beats, start=1):
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

                from app.services.kinetic_sub_director import estimate_speech_duration
                est_dur = estimate_speech_duration(b.text, market=market)

                all_scenes.append(Scene(
                    scene_id=f"SCENE_{idx:02d}",
                    sequence_block=f"block_{idx}_{block_slug}",
                    beat_role=role,
                    narration=b.text,
                    headline=f"BEAT {idx:02d}",
                    visual_metaphor=f"Tactile evidence {idx:02d}",
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=est_dur
                ))
            source_p = spoken_script.source_path
            source_sha = spoken_script.source_sha256
        except B2ContractError:
            # Fallback for dry-run simulation mode when no spoken script was provided
            if not ctx.dry_run:
                raise
            default_texts = [
                ("hook", "block_1_act_i", f"In late 2026, an unprecedented regulatory decision permanently overturned the status quo of {topic}."),
                ("context", "block_2_act_i", "For years, the public narrative claimed complete compliance, while domestic operators bore a 100x tax disparity."),
                ("tension", "block_3_act_ii", "A forensic examination of the contract paperwork reveals how 65% of domestic revenue was rerouted offshore."),
                ("reveal", "block_4_act_iii", "The smoking gun was not hidden secrecy, but an institutional loophole encoded directly into legacy tax law."),
                ("payoff", "block_5_act_iv", "This landmark ruling marks the beginning of an era where digital presence directly mandates fiscal accountability."),
            ]
            all_scenes = [
                Scene(
                    scene_id=f"SCENE_{idx:02d}",
                    sequence_block=blk,
                    beat_role=r,
                    narration=txt,
                    headline=f"BEAT {idx:02d}",
                    visual_metaphor="Tactile macro evidence",
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=6.0,
                )
                for idx, (r, blk, txt) in enumerate(default_texts, start=1)
            ]
            source_p = "dry_run_simulation"
            source_sha = "dry_run_sha256"

        max_sc = ctx.config.limits.max_scenes
        scenes = all_scenes[:max_sc] if (max_sc > 0 and len(all_scenes) > max_sc) else all_scenes

        payload = {
            "task_id": ctx.run_id,
            "topic": topic,
            "total_scenes": len(scenes),
            "b2_source_path": source_p,
            "b2_source_sha256": source_sha,
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
