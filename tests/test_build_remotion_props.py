import pytest
from app.services.build_remotion_props import extract_custom_beat_titles, format_speaker_tag

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
