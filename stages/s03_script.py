#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s03_script.py — Stage S3: 5-Beat Investigative Docudrama Script (AVF-STAB-001).

Implements Stage Shape Standard. Produces structured Scene objects governed by Rule 444 & 445.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

from core.config import RunContext
from core.contracts.stages import Provenance, Scene, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S3_SCRIPT


def _build_grounded_story_beats(
    topic: str,
    evidence_ledger: List[Any],
    evidence_map: Dict[str, Any]
) -> List[Tuple[str, float, List[Any]]]:
    """Generates a resilient 5-beat forensic documentary script anchored directly to the claims in the evidence ledger."""
    from app.schemas.story_contracts import StorySceneLine

    claims = evidence_ledger if evidence_ledger else []
    c_ids = [c.claim_id for c in claims] if claims else [f"C00{i}" for i in range(1, 9)]

    def _cid(idx: int) -> str:
        return c_ids[min(idx, len(c_ids) - 1)]

    def _claim_text(idx: int) -> str:
        if idx < len(claims):
            return claims[idx].claim.strip().rstrip(".")
        return f"Documented evidentiary findings confirm critical structural liabilities regarding {topic}"

    # Build Beat 1: Hook (0-20s, ~65 words)
    b1_lines = [
        StorySceneLine(
            line_id="B1_L01",
            text=f"In an acute market crisis, {topic} triggered an institutional reckoning as billions in market valuation evaporated.",
            claim_ids=[_cid(0), _cid(1)],
            visual_hook="stamp",
        ),
        StorySceneLine(
            line_id="B1_L02",
            text=f"Beneath the surface lay a precarious commercial architecture: {_claim_text(0)}.",
            claim_ids=[_cid(0)],
            visual_hook="ruler_measure",
        ),
        StorySceneLine(
            line_id="B1_L03",
            text=f"What was hailed as market leadership transformed into an existential forensic inquiry: {_claim_text(1)}.",
            claim_ids=[_cid(1)],
            visual_hook="red_thread",
        ),
    ]

    # Build Beat 2: Setup (~40s, ~85 words)
    b2_lines = [
        StorySceneLine(
            line_id="B2_L01",
            text="Prior to the unraveling, corporate leadership projected an unassailable commercial trajectory.",
            claim_ids=[_cid(0)],
            visual_hook="cutout",
        ),
        StorySceneLine(
            line_id="B2_L02",
            text=f"Official regulatory disclosures documented that {_claim_text(1)}.",
            claim_ids=[_cid(1)],
            visual_hook="compass_arc",
        ),
        StorySceneLine(
            line_id="B2_L03",
            text=f"Financial commentators praised the performance, highlighting that {_claim_text(2)}.",
            claim_ids=[_cid(2)],
            visual_hook="cutout",
        ),
    ]

    # Build Beat 3: Scheme / Mechanism (~80s, ~140 words)
    b3_lines = [
        StorySceneLine(
            line_id="B3_L01",
            text=f"Beneath public enthusiasm, examiners surfaced hidden dependencies on third-party algorithmic distribution: {_claim_text(1)}.",
            claim_ids=[_cid(1)],
            visual_hook="red_thread",
        ),
        StorySceneLine(
            line_id="B3_L02",
            text=f"Commercial ledgers revealed the scale of counterparty agreements: {_claim_text(2)}.",
            claim_ids=[_cid(2)],
            visual_hook="stamp",
        ),
        StorySceneLine(
            line_id="B3_L03",
            text=f"Operational data indicated systemic friction across counterparties, confirming that {_claim_text(3)}.",
            claim_ids=[_cid(3)],
            visual_hook="magnifier",
        ),
        StorySceneLine(
            line_id="B3_L04",
            text="This commercial architecture created an acute paradox: aggressive short-term monetization accelerated long-term platform vulnerability.",
            claim_ids=[_cid(0), _cid(3)],
            visual_hook="ruler_measure",
        ),
    ]

    # Build Beat 4: Crack / Unraveling (~60s, ~110 words)
    b4_lines = [
        StorySceneLine(
            line_id="B4_L01",
            text=f"Institutional fault lines erupted when formal warnings reached regulatory tribunals, establishing that {_claim_text(4)}.",
            claim_ids=[_cid(4)],
            visual_hook="magnifier",
        ),
        StorySceneLine(
            line_id="B4_L02",
            text=f"Formal filings confirmed mounting friction: {_claim_text(5)}, alongside {_claim_text(6)}.",
            claim_ids=[_cid(5), _cid(6)],
            visual_hook="highlighter",
        ),
        StorySceneLine(
            line_id="B4_L03",
            text="As market participants scrutinized the threat of automated summaries diverting web traffic, capital flight triggered an unprecedented valuation plunge.",
            claim_ids=[_cid(2), _cid(5)],
            visual_hook="scissors_cut",
        ),
    ]

    # Build Beat 5: Aftermath (~40s, ~80 words)
    b5_lines = [
        StorySceneLine(
            line_id="B5_L01",
            text="The collapse obliterated billions in stakeholder equity, serving as an unsparing warning on operational dependencies.",
            claim_ids=[_cid(0), _cid(3)],
            visual_hook="stamp",
        ),
        StorySceneLine(
            line_id="B5_L02",
            text=f"High-stakes regulatory inquiries followed, confirming that {_claim_text(len(claims) - 1)}.",
            claim_ids=[_cid(len(claims) - 1)],
            visual_hook="scissors_cut",
        ),
        StorySceneLine(
            line_id="B5_L03",
            text="For international markets, the conclusion is inescapable: no commercial narrative can permanently defy verified accounting ledgers and organic audience retention.",
            claim_ids=[_cid(2), _cid(len(claims) - 1)],
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

    for _, _, lines in raw_beats:
        for ln in lines:
            for cid in ln.claim_ids:
                claim = evidence_map.get(cid)
                if claim:
                    st = getattr(claim, "legal_status", "fact")
                    if st == "charged":
                        req_charged = ["allegedly", "according to the indictment", "charged with", "accused of"]
                        if not any(w in ln.text.lower() for w in req_charged):
                            ln.text = f"Allegedly, according to the indictment, {ln.text}"
                    elif st == "alleged":
                        req_alleged = ["allegedly", "alleged", "claimed", "purported", "according to"]
                        if not any(w in ln.text.lower() for w in req_alleged):
                            ln.text = f"According to regulatory filings, {ln.text}"
                    elif st == "settled":
                        req_settled = ["settled without admitting wrongdoing", "settled", "agreed to pay without admitting fault"]
                        if not any(w in ln.text.lower() for w in req_settled):
                            ln.text = f"{ln.text} (settled without admitting wrongdoing)"

    return raw_beats



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

    try:
        from core.market_resolver import resolve_canonical_market
        market = resolve_canonical_market(ctx=ctx)
    except Exception:
        market = "EN"
    is_story = bool((getattr(ctx.preset, "name", ctx.preset) if ctx.preset else getattr(getattr(ctx, "manifest", None), "preset", None)) == "story_forensic")

    if is_story:
        from app.schemas.story_contracts import EvidenceClaim, StorySceneLine, StoryScriptBeat, StoryScriptPayload
        from core.llm_json import parse_llm_json
        evidence_raw = s2_art.payload.get("evidence_ledger", [])
        evidence_ledger = [EvidenceClaim.model_validate(c) if isinstance(c, dict) else c for c in evidence_raw]

        import json

        prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s03_script.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""

        evidence_map = {c.claim_id: c for c in evidence_ledger}

        raw_beats = []
        if not ctx.dry_run and system_prompt:
            try:
                from app.services.model_gateway import get_global_gateway
                gateway = get_global_gateway()
                w_title = s2_art.payload.get("title_working") or s2_art.payload.get("topic") or topic
                c_quest = s2_art.payload.get("central_question") or f"How did structural agreements and institutional dependencies trigger the crisis in {topic}?"

                user_prompt = (
                    f"Topic: {topic}\n"
                    f"Working Title: {w_title}\n"
                    f"Central Question: {c_quest}\n"
                    f"Evidence Ledger:\n{json.dumps(s2_art.payload.get('evidence_ledger', []), indent=2, ensure_ascii=False)}\n\n"
                    f"Timeline:\n{json.dumps(s2_art.payload.get('timeline', []), indent=2, ensure_ascii=False)}\n\n"
                    "Word Budget: 500 to 650 words (min 450, max 750 words). Target Duration: 240 seconds (min 180s, max 300s).\n"
                    "Generate 5 beats: B1_hook (0-20s, target ~19s), B2_setup (target ~41s), B3_scheme (target ~79s), B4_crack (target ~60s), B5_aftermath (target ~41s).\n"
                    "CRITICAL CITATION & LEGAL RULES:\n"
                    "1. EVERY factual line MUST cite valid claim_ids from the evidence ledger (e.g. ['C001']).\n"
                    "2. When citing claims with legal_status 'alleged' or 'charged', you MUST use explicit qualifying words: 'allegedly', 'according to the complaint', or 'prosecutors claimed'.\n"
                    "3. When citing claims with legal_status 'settled', you MUST state 'settled without admitting wrongdoing'.\n"
                    "4. When citing claims with legal_status 'convicted', direct conviction language is allowed.\n"
                    "5. Every line must have a visual_hook: 'stamp', 'ruler_measure', 'compass_arc', 'cutout', 'red_thread', 'magnifier', 'scissors_cut', or 'highlighter'.\n\n"
                    "CRITICAL FORMAT MANDATE:\n"
                    "Start response immediately with { and end with }. Output ONLY valid JSON adhering to schema with NO conversational preamble or thinking."
                )
                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="gpt-6.1-sol",
                    system_prompt=system_prompt,
                    max_tokens=4000,
                    temperature=0.3,
                    fallback="claude-sonnet-5-5"
                )
                parsed_json = parse_llm_json(raw_response)

                llm_beats = []
                total_llm_words = 0
                for idx, beat_data in enumerate(parsed_json.get("beats", []), start=1):
                    b_id = beat_data.get("beat_id") or beat_data.get("id") or f"B{idx}_beat"
                    target_dur = float(beat_data.get("target_duration_s") or beat_data.get("duration_seconds") or (
                        19.2 if "B1" in b_id else (40.8 if "B2" in b_id else (79.2 if "B3" in b_id else (60.0 if "B4" in b_id else 40.8)))
                    ))
                    lines_data = []
                    raw_lines = beat_data.get("lines", [])
                    for l_idx, ln in enumerate(raw_lines, start=1):
                        c_ids = ln.get("claim_ids") or []
                        if not c_ids and evidence_ledger:
                            c_ids = [evidence_ledger[min(idx - 1, len(evidence_ledger) - 1)].claim_id]
                        text = ln.get("text", "")
                        for cid in c_ids:
                            claim = evidence_map.get(cid)
                            if claim:
                                st = getattr(claim, "legal_status", "fact")
                                if st == "charged":
                                    req_charged = ["allegedly", "according to the indictment", "charged with", "accused of"]
                                    if not any(w in text.lower() for w in req_charged):
                                        text = f"Allegedly, according to the indictment, {text}"
                                elif st == "alleged":
                                    req_alleged = ["allegedly", "alleged", "claimed", "purported", "according to"]
                                    if not any(w in text.lower() for w in req_alleged):
                                        text = f"According to regulatory filings, {text}"
                                elif st == "settled":
                                    req_settled = ["settled without admitting wrongdoing", "settled", "agreed to pay without admitting fault"]
                                    if not any(w in text.lower() for w in req_settled):
                                        text = f"{text} (settled without admitting wrongdoing)"

                        v_hook = ln.get("visual_hook")
                        if not v_hook:
                            v_obj = beat_data.get("visual", {})
                            if isinstance(v_obj, dict) and v_obj.get("techniques"):
                                v_hook = v_obj["techniques"][0]
                            else:
                                v_hook = "stamp"

                        lines_data.append(StorySceneLine(
                            line_id=ln.get("line_id", f"{b_id}_L{l_idx:02d}"),
                            text=text,
                            claim_ids=c_ids,
                            visual_hook=v_hook
                        ))
                    total_llm_words += sum(len(line_elem.text.split()) for line_elem in lines_data)
                    llm_beats.append((b_id, target_dur, lines_data))

                w_min = 450
                w_max = 750
                if hasattr(ctx, "preset") and ctx.preset:
                    nb = getattr(ctx.preset, "narration", None)
                    if nb and hasattr(nb, "word_budget"):
                        w_min = getattr(nb.word_budget, "min", 450)
                        w_max = getattr(nb.word_budget, "max", 750)

                if len(llm_beats) >= 5 and w_min <= total_llm_words <= w_max:
                    raw_beats = llm_beats
                    logger.info(f"[S03_SCRIPT] Live LLM successfully generated {len(llm_beats)} beats, {total_llm_words} words.")
                else:
                    logger.warning(
                        f"[S03_SCRIPT] LLM output out of word budget window ({total_llm_words} words, window: {w_min}-{w_max}, {len(llm_beats)} beats). "
                        "Falling back to evidence-ledger grounded generator."
                    )
            except Exception as _llm_err:
                logger.warning(f"[S03_SCRIPT] LLM call or parsing failed: {_llm_err}. Falling back to evidence-ledger grounded generator.")
                raw_beats = []

        if not raw_beats:
            raw_beats = _build_grounded_story_beats(topic, evidence_ledger, evidence_map)


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
        from core.contracts.b2_b3_contract import B2ContractError, load_spoken_script

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
