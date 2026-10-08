# -*- coding: utf-8 -*-
"""tests/test_vox_automated_director.py
Unit tests for the Autonomous Vox Director Engine (Rule 118, 120, 128, 132).
"""

import pytest
from app.services.vox_automated_director import VoxAutomatedDirector


def test_niche_classification():
    director = VoxAutomatedDirector(market="EN")
    assert director.classify_niche("Federal bank failure and sovereign bond yields") == "money_power"
    assert director.classify_niche("The 1971 D.B. Cooper hijacking and FBI manhunt") == "crime_documentary"
    assert director.classify_niche("Ancient Roman civil war and Caesar's conquest") == "history"
    assert director.classify_niche("Aviation crash over the Andes mountains") == "disasters_survival"
    assert director.classify_niche("Silicon Valley semiconductor chip war and AI computing") == "technology"


def test_word_math_calculation():
    director = VoxAutomatedDirector(market="EN")
    assert director.compute_word_budget(30) == 75
    assert director.compute_word_budget(60) == 150
    assert director.compute_word_budget(120) == 300
    assert director.compute_word_budget(180) == 450


def test_script_dna_validation():
    director = VoxAutomatedDirector(market="EN")
    script = (
        "November 24, 1971. Portland International Airport. A calm passenger named Dan Cooper boards Flight 305 to Seattle. "
        "Midway through the flight, he hands flight attendant Florence Schaffner a quiet note claiming he has a bomb. "
        "He demands two hundred thousand dollars in cash and four parachutes upon landing. "
        "Federal authorities scramble, meeting his ransom demands in exchange for thirty-six passengers. "
        "The aircraft refuels and takes off toward Reno through a freezing November storm. "
        "Somewhere over southwest Washington, Cooper lowers the aft stairs and leaps into darkness. "
        "He was never found."
    )
    audit = director.validate_script_dna(script, duration_sec=35)
    assert audit["has_temporal_anchor"] is True
    assert audit["has_tight_ending"] is True
    assert audit["has_em_dash"] is False
    assert audit["score"] >= 8.0


def test_beat_breakdown_two_shot_cadence():
    director = VoxAutomatedDirector(market="EN", fps=30)
    script = (
        "November 24, 1971. Portland International Airport. A man in a dark suit buys a one-way ticket. "
        "He boards Northwest Orient Flight 305 carrying a heavy black briefcase."
    )
    beats = director.breakdown_beats(script, duration_sec=15)
    assert len(beats) >= 2
    for beat in beats:
        # Every beat must have exactly 2 shots: Shot A (Wide) and Shot B (Detail)
        assert len(beat["shots"]) == 2
        shot_a = beat["shots"][0]
        shot_b = beat["shots"][1]
        assert shot_a["type"] == "EST_WIDE"
        assert shot_a["has_headline"] is True
        assert len(shot_a["headline_text"]) > 0
        assert shot_b["type"] == "DETAIL_CUTIN"
        assert shot_b["has_headline"] is False
        assert shot_a["start_frame"] < shot_b["start_frame"]
        assert shot_b["end_frame"] == beat["end_frame"]


def test_remotion_manifest_generation():
    director = VoxAutomatedDirector(market="EN", fps=30)
    script = "November 24, 1971. Portland Airport. Dan Cooper boards the aircraft."
    beats = director.breakdown_beats(script, duration_sec=10)
    manifest = director.build_remotion_manifest(beats, theme="newsprint-editorial", topic="D.B. Cooper")

    assert manifest["fps"] == 30
    assert manifest["width"] == 1920
    assert manifest["height"] == 1080
    assert len(manifest["scenes"]) == len(beats)
    first_scene = manifest["scenes"][0]
    assert first_scene["component"] == "VoxBuildOnStage"
    assert first_scene["theme"] == "newsprint-editorial"
    assert len(first_scene["supportingCutouts"]) == 2
    assert len(first_scene["yarns"]) == 1


def test_thumbnail_generation():
    director = VoxAutomatedDirector(market="EN")
    thumbs = director.generate_thumbnails("D.B. Cooper Hijacking", "VANISHED", "newsprint-editorial")
    assert len(thumbs) == 3
    for t in thumbs:
        assert "censor bar" in t.lower()
        assert "16:9" in t
        assert "halftone" in t.lower()


def test_generate_ideas_state_2():
    director = VoxAutomatedDirector(market="EN")
    ideas = director.generate_ideas("crime_documentary", count=10)
    assert len(ideas) == 10
    for idx, idea in enumerate(ideas, 1):
        assert len(idea["title"]) > 10
        assert len(idea["hook"]) > 5
        # Ensure title follows non-clickbait documentary shapes
        assert any(prefix in idea["title"] for prefix in ["The ", "How ", "What ", "Why "])

    # Test with custom topic hint
    custom_ideas = director.generate_ideas("technology", count=5, topic_hint="Quantum Computing Race")
    assert len(custom_ideas) == 5
    assert "Quantum Computing Race" in custom_ideas[0]["title"]


def test_animation_duration_timing_6s_vs_10s():
    # 10s mode
    dir_10 = VoxAutomatedDirector(market="EN", fps=30, animation_duration_sec=10)
    beats = dir_10.breakdown_beats("November 24, 1971. Portland Airport. Dan Cooper buys a ticket.", duration_sec=10)
    manifest_10 = dir_10.build_remotion_manifest(beats, theme="newsprint-editorial")
    scene_10 = manifest_10["scenes"][0]
    assert scene_10["supportingCutouts"][0]["delaySec"] == 1.2
    assert scene_10["supportingCutouts"][1]["delaySec"] == 1.6
    assert scene_10["yarns"][0]["delaySec"] == 2.2
    assert manifest_10["meta"]["animationDurationSec"] == 10
    assert manifest_10["meta"]["buildEndSec"] == 7.0

    # 6s mode
    dir_6 = VoxAutomatedDirector(market="EN", fps=30, animation_duration_sec=6)
    manifest_6 = dir_6.build_remotion_manifest(beats, theme="newsprint-editorial")
    scene_6 = manifest_6["scenes"][0]
    assert scene_6["supportingCutouts"][0]["delaySec"] == 0.72
    assert scene_6["supportingCutouts"][1]["delaySec"] == 0.96
    assert scene_6["yarns"][0]["delaySec"] == 1.32
    assert manifest_6["meta"]["animationDurationSec"] == 6
    assert manifest_6["meta"]["buildEndSec"] == 3.8


def test_textify_bulk_prompts_format():
    director = VoxAutomatedDirector(market="EN")
    fake_manifest = [
        {"image_prompt": "Prompt Block 1: Hand-cut documentary paper collage on aged newsprint..."},
        {"image_prompt": "Prompt Block 2: Hand-cut documentary paper collage on aged newsprint..."},
        {"image_prompt": "Prompt Block 3: Hand-cut documentary paper collage on aged newsprint..."}
    ]
    bulk_text = director.format_textify_bulk_prompts(fake_manifest)
    blocks = bulk_text.split("\n\n")
    assert len(blocks) == 3
    for b in blocks:
        assert not b.startswith("#")
        assert not b.startswith("1.")
        assert "Hand-cut documentary paper collage" in b


def test_build_diorama_video_prompts_cl3_formula():
    director = VoxAutomatedDirector(market="EN", fps=30)
    script = (
        "November 24, 1971. Portland International Airport. A calm passenger boards Flight 305. "
        "Inside the cabin, Senator John Smith reviews a classified federal ledger with $200,000 missing. "
        "Deep inside the Washington canyon, the FBI search grid uncovers a critical smoking gun crisis. "
        "Ultimately, the vault remained empty and the case became an enduring mirror of institutional failure."
    )
    beats = director.breakdown_beats(script, duration_sec=40)
    video_prompts = director.build_diorama_video_prompts(beats, video_engine_mode="flow_veo_fast")

    assert len(video_prompts) == len(beats)
    alert_wash_count = 0
    style_blocks_seen = set()

    for vp in video_prompts:
        style_blocks_seen.add(vp["style_block_type"])
        assert vp["style_block_type"] in ("FLAT_PARALLAX", "DEEP_DIORAMA", "LOCKED_STAGE")
        assert "Use the attached style sheet" in vp["video_prompt"]
        assert "SHOT:" in vp["video_prompt"]
        assert "Settle " in vp["video_prompt"]
        assert "AUDIO:" in vp["video_prompt"]
        assert "AVOID:" in vp["video_prompt"]
        assert vp["trim_start_sec"] == 0.25
        assert vp["retain_native_sfx_volume"] == 0.18
        assert vp["style_reference_sheet"] == "config/prompts/vox_master_style_sheet.png"
        # Ensure public figure name "John Smith" was scrubbed from video prompt
        assert "John Smith" not in vp["video_prompt"]
        if vp["is_alert_wash"]:
            alert_wash_count += 1

    # Rule: Max 1 ALERT WASH per sequence
    assert alert_wash_count == 1
    assert len(style_blocks_seen) >= 2


def test_low_token_36_and_omni_48_budget_modes():
    from app.services.unified_vox_director import (
        select_dynamic_hero_indices,
        inject_speech_timestamp_cue
    )

    sents = [
        {"index": i, "text": f"Sentence {i} reveals a $500 million crisis and sudden collapse in the vault.", "duration_sec": 6.0}
        for i in range(120)
    ]

    std_indices = select_dynamic_hero_indices(sents, video_budget_mode="standard_18")
    low_token_indices = select_dynamic_hero_indices(sents, video_budget_mode="low_token_36")
    omni_indices = select_dynamic_hero_indices(sents, video_budget_mode="omni_48")

    assert 12 <= len(std_indices) <= 22
    assert len(low_token_indices) == 36
    assert len(omni_indices) == 48

    cue = inject_speech_timestamp_cue(sents[0], dur_sec=6.0)
    assert cue.startswith("At ")
    assert "s when narration hits" in cue or "s mid-sentence beat" in cue
    assert "trigger primary" in cue

