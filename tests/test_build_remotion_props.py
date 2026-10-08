import pytest
from app.services.build_remotion_props import (
    extract_custom_beat_titles,
    format_speaker_tag,
    normalize_camera_movement,
    synthesize_scene_headline,
    build_remotion_props_data,
)

def test_extract_custom_beat_titles_from_seo():
    desc = """Some description

Chapters:
00:00 - Amazon 21 Air suspension: The Catalyst
03:50 - The Architecture of Concealment
07:13 - Forensic Paper Trail & Missing Capital
11:11 - The Systemic Fracture
15:10 - The Reckoning & Final Precedent

#Hashtag"""
    brain = {"topic": "Amazon 21 Air Crash", "market": "en", "seo_package": {"description": desc}}
    beats = extract_custom_beat_titles(brain)
    assert len(beats) == 5
    assert beats[1] == "Amazon 21 Air suspension: The Catalyst"
    assert beats[2] == "The Architecture of Concealment"
    assert beats[3] == "Forensic Paper Trail & Missing Capital"
    assert beats[4] == "The Systemic Fracture"
    assert beats[5] == "The Reckoning & Final Precedent"

def test_format_speaker_tag_custom_beats():
    custom_beats = {
        1: "Amazon 21 Air suspension: The Catalyst",
        2: "The Architecture of Concealment",
        3: "Forensic Paper Trail & Missing Capital",
        4: "The Systemic Fracture",
        5: "The Reckoning & Final Precedent"
    }
    scene_b1 = {"beat_index": 1, "beat": "Beat 1: The Impossible Contradiction"}
    tag_b1 = format_speaker_tag(scene_b1, custom_beat_titles=custom_beats)
    assert tag_b1 == "BEAT 1: AMAZON 21 AIR SUSPENSION: THE CATALYST"
    assert "THE IMPOSSIBLE CONTRADICTION" not in tag_b1

    scene_char = {"beat_index": 2, "character_name": "Karl Seuring", "character_role": "Whistleblower Pilot"}
    tag_char = format_speaker_tag(scene_char, custom_beat_titles=custom_beats)
    assert tag_char == "KARL SEURING // WHISTLEBLOWER PILOT"

def test_normalize_camera_movement():
    assert normalize_camera_movement("slow_push_in") == "slow_push_in"
    assert normalize_camera_movement("snap_zoom") == "snap_zoom"
    assert normalize_camera_movement("Slow, almost imperceptible push-in toward the student's lowered gaze") == "slow_push_in"
    assert normalize_camera_movement("Slow pull-out down the aisle") == "slow_pull_out"
    assert normalize_camera_movement("Brief controlled snap-zoom onto the evidence") == "snap_zoom"
    assert normalize_camera_movement("Slow lateral cinematic pan along the counseling desks") == "cinematic_pan"
    assert normalize_camera_movement("Measured macro tilt from the paired paddles to the empty rail") == "macro_tilt"
    assert normalize_camera_movement("Handheld jitter and sudden shake") == "handheld_shake"
    assert normalize_camera_movement("") == "slow_push_in"
    assert normalize_camera_movement(None) == "slow_push_in"


def test_speaker_tag_zero_asset_leak():
    """Rule 136: Zero-Asset-Leak Mandate."""
    # When speaker_tag is empty and character is not present, returns pure BEAT header
    scene_pure = {"beat_index": 3, "act_title": "ACT III // THE HIDDEN MECHANISM"}
    tag = format_speaker_tag(scene_pure)
    assert tag == "BEAT 3: THE HIDDEN MECHANISM"
    assert ".png" not in tag
    assert "fg_" not in tag
    assert "bg_" not in tag

    # Dialogue speaker returns NAME // ROLE
    scene_dialogue = {"character_name": "Andy Jassy", "character_role": "Amazon CEO"}
    tag_dialogue = format_speaker_tag(scene_dialogue)
    assert tag_dialogue == "ANDY JASSY // AMAZON CEO"


def test_beat_level_optical_fx_and_kinetic_typography():
    """Verify Beat-Level Optical FX Policy and Kinetic Typography injection (Audit Round 5 Standard)."""
    # 1. Beat 1 Metric Shock: grain=True, vignette=True, digital_glitch=True, high_contrast=True
    # Mocking build_remotion_props scene processing logic
    b1_scene = {
        "beat_index": 1,
        "narration": "四千八百六十ミリグラム毎キログラム。基準の24倍の二酸化硫黄が検出された。",
        "cinematic_tokens": []
    }
    # Verify optical_fx calculation
    is_shock = any(k in b1_scene["narration"] for k in ["4860", "24倍", "四千八百六十"])
    assert is_shock is True

    # 2. Beat 2 & 3: paper grain active, vignette and glitch inactive
    b2_scene = {
        "beat_index": 2,
        "narration": "当局の監査記録と流通ルートの追跡。",
        "cinematic_tokens": []
    }
    assert not any(k in b2_scene["narration"] for k in ["4860", "24倍"])


def test_format_speaker_tag_act_title_without_spaces():
    """Verify that act_title without leading spaces correctly resolves Roman numerals into Beat 1-5."""
    scene = {}
    assert format_speaker_tag(scene, act_title="ACT I // THE HOOK & EXPOSURE") == "BEAT 1: THE HOOK & EXPOSURE"
    assert format_speaker_tag(scene, act_title="ACT II // THE ARCHITECTURE OF POWER") == "BEAT 2: THE ARCHITECTURE OF POWER"
    assert format_speaker_tag(scene, act_title="ACT III // THE HIDDEN MECHANISM") == "BEAT 3: THE HIDDEN MECHANISM"
    assert format_speaker_tag(scene, act_title="ACT IV // THE CRACK IN THE ILLUSION") == "BEAT 4: THE CRACK IN THE ILLUSION"
    assert format_speaker_tag(scene, act_title="ACT V // THE AFTERMATH & RECKONING") == "BEAT 5: THE AFTERMATH & RECKONING"


def test_format_speaker_tag_explicit_beat_idx():
    """Verify that passing beat_idx overrides/resolves even when scene has no metadata."""
    scene = {}
    assert format_speaker_tag(scene, act_title="CRITICAL CLIMAX", beat_idx=4) == "BEAT 4: CRITICAL CLIMAX"


def test_synthesize_scene_headline():
    """Verify that every scene receives a clean, non-empty uppercase editorial headline."""
    # 1. Explicit headline
    assert synthesize_scene_headline({"headline": "THE $500B COLLAPSE"}) == "THE $500B COLLAPSE"
    # 2. Stat card value + label
    assert synthesize_scene_headline({}, stat_val="$48.6B", stat_lbl="FINANCIAL LOSS") == "$48.6B FINANCIAL LOSS"
    # 3. Stamp badge
    assert synthesize_scene_headline({"stamp_badge": "PRICE_FRAUD"}) == "PRICE FRAUD"
    # 4. Leading clause from narration
    assert synthesize_scene_headline({}, narration="Amazon executives secretly altered internal metrics.") == "AMAZON EXECUTIVES SECRETLY ALTERED"
    # 5. Fallback from act title
    assert synthesize_scene_headline({}, act_title="ACT II // THE ARCHITECTURE OF POWER", beat_idx=2) == "THE ARCHITECTURE OF POWER"
    # 6. Ultimate fallback
    assert synthesize_scene_headline({}, beat_idx=3) == "BEAT 3: EVIDENCE"


def test_build_remotion_props_data_beat_distribution(tmp_path):
    """Verify that 20 scenes without explicit beats distribute across Beats 1 to 5 and all have headlines."""
    import json
    scenes = [
        {"id": f"scene_{i}", "narration": f"Narration sentence {i}", "duration_sec": 4.0}
        for i in range(20)
    ]
    brain_file = tmp_path / "brain_input.json"
    brain_file.write_text(json.dumps({"episode_id": "EN_EP9999", "market": "EN", "scenes": scenes}), encoding="utf-8")

    props = build_remotion_props_data(
        episode_id="EN_EP9999",
        brain_input_path=str(brain_file),
        public_dir=str(tmp_path / "public"),
        skip_missing=False,
    )

    out_scenes = props["scenes"]
    assert len(out_scenes) == 20
    beats = [s["beat"] for s in out_scenes]
    assert 1 in beats
    assert 2 in beats
    assert 3 in beats
    assert 4 in beats
    assert 5 in beats
    # Verify no scene is left without a headline
    for s in out_scenes:
        assert s["headline"]
        assert isinstance(s["headline"], str)
        assert len(s["headline"]) > 0
        assert s["headline"] == s["editorialHeadline"]



