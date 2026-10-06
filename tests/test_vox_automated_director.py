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
