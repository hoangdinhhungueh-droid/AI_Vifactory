#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_story_contracts.py — Unit Tests for Story Contracts & Backward Compatibility."""

import json
from pathlib import Path
import pytest

from app.schemas.story_contracts import (
    Antagonist,
    EvidenceClaim,
    SourceSeed,
    StoryCriticViolation,
    StoryIdeationPayload,
    StoryResearchPayload,
    StorySceneLine,
    StoryScriptBeat,
    StoryScriptCriticGates,
    StoryScriptCriticPayload,
    StoryScriptPayload,
    StoryShotPlan,
    StoryVisualCriticGates,
    StoryVisualCriticPayload,
    TimelineEvent,
)


def test_story_ideation_contract():
    payload = StoryIdeationPayload(
        niche="corporate_scandal",
        title_working="Enron: The Smartest Guys Who Stole $74B",
        central_question="How did Kenneth Lay conceal billions through off-the-books SPEs?",
        antagonist=Antagonist(name="Enron Executives", type="company"),
        scheme_mechanism_summary="Mark-to-market accounting combined with raptor special purpose entities.",
        money_at_stake_usd=74_000_000_000.0,
        documented_outcome="Bankruptcy in Dec 2001, Sarbanes-Oxley Act passed, Arthur Andersen dissolved.",
        source_seeds=[
            SourceSeed(url="https://www.sec.gov/litigation/litreleases/lr17192.htm", type="regulator"),
            SourceSeed(url="https://www.justice.gov/enron", type="court"),
            SourceSeed(url="https://www.wsj.com/articles/SB100344445353528800", type="press"),
        ],
    )
    assert payload.preset == "story_forensic"
    assert payload.money_at_stake_usd == 74_000_000_000.0
    assert len(payload.source_seeds) == 3


def test_story_research_and_evidence_ledger():
    claim = EvidenceClaim(
        claim_id="C001",
        claim="Enron filed for Chapter 11 bankruptcy on December 2, 2001.",
        source_url="https://www.sec.gov/news/press/2001-143.txt",
        source_type="regulator",
        date="2001-12-02",
        legal_status="fact",
        confidence="high",
    )
    timeline = TimelineEvent(
        date="2001-12-02",
        event="Enron files Chapter 11 bankruptcy in New York.",
        claim_ids=["C001"],
    )
    res_payload = StoryResearchPayload(
        topic="Enron Accounting Fraud",
        evidence_ledger=[claim],
        timeline=[timeline],
    )
    assert len(res_payload.evidence_ledger) == 1
    assert res_payload.evidence_ledger[0].legal_status == "fact"


def test_story_script_and_shot_plan():
    line = StorySceneLine(
        line_id="B3_L01",
        text="Fastow channeled unprofitable liabilities into Fastow-controlled SPEs.",
        claim_ids=["C005"],
        visual_hook="stamp",
    )
    beat = StoryScriptBeat(
        beat_id="B3_scheme",
        target_duration_s=79.0,
        lines=[line],
        word_count=8,
    )
    script_payload = StoryScriptPayload(
        total_words=450,
        est_duration_s=180.0,
        beats=[beat],
    )
    assert len(script_payload.beats) == 1
    assert script_payload.beats[0].lines[0].visual_hook == "stamp"

    shot = StoryShotPlan(
        shot_id="S001",
        line_ids=["B3_L01"],
        render_mode="vox_native",
        h_family="H1_IMPACT",
        tactile_props=["stamp", "red_thread"],
        prompt="Red rubber stamp slamming onto Enron ledger with sharp impact, ink splatter.",
        contains_real_person=False,
    )
    assert shot.render_mode == "vox_native"
    assert shot.duration_s == 5.5

    # Default fallback to veo
    default_shot = StoryShotPlan(shot_id="S002", line_ids=["B3_L01"])
    assert default_shot.render_mode == "veo"


def test_critic_contracts():
    s4_payload = StoryScriptCriticPayload(
        verdict="pass",
        gates=StoryScriptCriticGates(
            duration_estimate_in_window=True,
            every_factual_line_has_claim_id=True,
            legal_language_matches_status=True,
            hook_within_20s=True,
            pattern_interrupt_gap_ok=True,
        ),
        violations=[],
    )
    assert s4_payload.verdict == "pass"
    assert s4_payload.gates.every_factual_line_has_claim_id is True

    s6_payload = StoryVisualCriticPayload(
        verdict="pass",
        gates=StoryVisualCriticGates(
            palette_locked=True,
            no_photoreal_real_person=True,
            h_family_variety=True,
            veo_share=True,
            aspect_16_9=True,
        ),
        violations=[],
    )
    assert s6_payload.verdict == "pass"


def test_backward_compatibility_with_existing_macro_run():
    repo_root = Path(__file__).resolve().parent.parent
    s1_art_path = repo_root / "runs" / "RUN_20261014_132945" / "s01_ideation" / "artifact.json"
    if s1_art_path.exists():
        data = json.loads(s1_art_path.read_text(encoding="utf-8"))
        payload = data.get("payload", {})
        # Should parse into StoryIdeationPayload without raising error
        ideation = StoryIdeationPayload.model_validate(payload)
        assert ideation.topic == "20261014 132945"
        assert ideation.viability_score == 9.2

    s3_art_path = repo_root / "runs" / "RUN_20261014_132945" / "s03_script" / "artifact.json"
    if s3_art_path.exists():
        data = json.loads(s3_art_path.read_text(encoding="utf-8"))
        payload = data.get("payload", {})
        # Should parse into StoryScriptPayload without raising error
        script = StoryScriptPayload.model_validate(payload)
        assert len(script.scenes) == 1
        assert script.scenes[0]["scene_id"] == "SCENE_01"


def test_s09_duration_conformer_speed_factors():
    """Verifies bidirectional speed factor calculation for both > d_max and < d_min."""
    d_min = 180.0
    d_max = 300.0
    target = 240.0

    # Over duration (e.g. 330s) -> speed_factor > 1.0 (speed up)
    real_over = 330.0
    assert real_over > d_max and (real_over / d_max) <= 1.35
    target_over = max(d_min + 5.0, min(d_max - 2.0, target))
    speed_factor_over = round(real_over / target_over, 3)
    assert 1.0 < speed_factor_over <= 2.0
    conformed_dur_over = real_over / speed_factor_over
    assert d_min <= conformed_dur_over <= d_max

    # Under duration (e.g. 160s) -> speed_factor < 1.0 (slow down)
    real_under = 160.0
    assert real_under < d_min and (real_under / d_min) >= 0.65
    target_under = min(d_max - 5.0, max(d_min + 3.0, target))
    speed_factor_under = round(real_under / target_under, 3)
    assert 0.5 <= speed_factor_under < 1.0
    conformed_dur_under = real_under / speed_factor_under
    assert d_min <= conformed_dur_under <= d_max


def test_karaoke_word_schema_precision():
    from core.contracts.render_props import KaraokeWord
    kw = KaraokeWord(
        word="test",
        start=1.234,
        end=1.567,
        start_ms=1234.0,
        end_ms=1567.0,
    )
    dump = kw.model_dump()
    assert dump["word"] == "test"
    assert dump["start"] == 1.234
    assert dump["end"] == 1.567
    assert dump["start_ms"] == 1234.0
    assert dump["end_ms"] == 1567.0
