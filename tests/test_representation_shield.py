# -*- coding: utf-8 -*-
"""tests/test_representation_shield.py
Unit tests for the Ethical Representation Shield and Cliffhanger Patterns Audit.
"""

import pytest
from app.services.representation_shield import (
    detect_child_representation,
    resolve_child_symbolic_artifact,
    apply_real_person_censor_shield,
    scrub_public_figure_names_for_video,
    shield_visual_roster,
    SYMBOLIC_CHILD_ARCHETYPES
)
from app.services.vox_automated_director import (
    audit_cliffhanger_patterns,
    VOX_PAPER_MATERIALS_LIBRARY,
    VoxAutomatedDirector
)


def test_detect_child_representation_multilingual():
    # English
    assert detect_child_representation("A primary school student walking down the street") is True
    assert detect_child_representation("Interview with the victim's young daughter and kid") is True
    assert detect_child_representation("Federal prosecutor examining bank records") is False
    assert detect_child_representation("Chief executive officer testifying before congress") is False

    # Vietnamese
    assert detect_child_representation("Lời khai của học sinh và trẻ em tại trường") is True
    assert detect_child_representation("Luật sư bào chữa trình bày chứng cứ tại tòa án") is False

    # Japanese
    assert detect_child_representation("事件に巻き込まれた児童と生徒の記録") is True
    assert detect_child_representation("東京地方裁判所の裁判官による判決") is False

    # Korean
    assert detect_child_representation("실종된 어린이와 학생에 관한 수사 기록") is True
    assert detect_child_representation("검찰청 수사관의 공식 발표") is False


def test_resolve_child_symbolic_artifact():
    # Context with playground / park
    art_swing = resolve_child_symbolic_artifact("Child missing from neighborhood", context_text="The playground was silent")
    assert art_swing["type"] == "evidence_prop"
    assert art_swing["is_child_symbolic"] is True
    assert "swing" in art_swing["description"].lower() or "swaying" in art_swing["description"].lower()
    assert "human figures" not in art_swing["description"] or "no human figures" in art_swing["description"]

    # Context with school / backpack
    art_school = resolve_child_symbolic_artifact("Young student", context_text="He left his classroom and backpack on the stairs")
    assert art_school["type"] == "evidence_prop"
    assert "backpack" in art_school["description"].lower() or "school" in art_school["description"].lower()

    # Context with doorway / shoes
    art_shoes = resolve_child_symbolic_artifact("Missing toddler", context_text="Near the front door of the domestic home")
    assert art_shoes["type"] == "evidence_prop"
    assert "shoes" in art_shoes["description"].lower() or "doorstep" in art_shoes["description"].lower()


def test_apply_real_person_censor_shield():
    desc = "Federal prosecutor Jerome Vance in dark navy wool suit, waist-up three-quarter angle."
    shielded = apply_real_person_censor_shield(desc, fg_key="fg_character_prosecutor")
    assert "censor bar" in shielded.lower()
    assert "black censor bar across the eyes" in shielded.lower()
    assert "midground distance" in shielded.lower()
    assert "non-photorealistic" in shielded.lower()

    # Re-applying does not duplicate censor bar
    shielded_again = apply_real_person_censor_shield(shielded, fg_key="fg_character_prosecutor")
    assert shielded_again.count("censor bar") == 1


def test_scrub_public_figure_names_for_video():
    raw_prompt = "Camera pushes past Senator John Smith and Jerome Vance holding a red dossier."
    scrubbed = scrub_public_figure_names_for_video(raw_prompt, extra_names=["Jerome Vance"])
    assert "John Smith" not in scrubbed
    assert "Jerome Vance" not in scrubbed
    assert "black-and-white halftone cutout figure with a black censor bar" in scrubbed


def test_shield_visual_roster_execution():
    bg_roster = {
        "bg_courthouse": {
            "title": "Courthouse Steps",
            "description": "Courthouse entrance steps with crowds of reporters and students.",
            "beats": [1, 2]
        }
    }
    fg_roster = {
        "fg_character_young_victim": {
            "title": "Young Schoolgirl Victim",
            "description": "A 10-year-old child student holding a school notebook.",
            "role": "Victim",
            "type": "character",
            "beats": [1, 2]
        },
        "fg_character_lead_investigator": {
            "title": "Lead Detective Vance",
            "description": "Veteran detective reviewing evidence binder.",
            "role": "Investigator",
            "type": "character",
            "beats": [2, 3]
        },
        "fg_evidence_docket": {
            "title": "Court Docket",
            "description": "Official court filing with seal.",
            "role": "Document",
            "type": "document",
            "beats": [1]
        }
    }

    clean_bg, clean_fg = shield_visual_roster(bg_roster, fg_roster, story_text="A historic school disappearance case", market="EN")

    # 1. Background human crowds purged
    assert "empty architectural spaces" in clean_bg["bg_courthouse"]["description"]

    # 2. Child character converted to symbolic evidence prop
    assert clean_fg["fg_character_young_victim"]["type"] == "evidence_prop"
    assert clean_fg["fg_character_young_victim"].get("is_child_symbolic") is True
    assert "no human figures" in clean_fg["fg_character_young_victim"]["description"].lower()

    # 3. Adult character shielded with censor bar
    assert "censor bar across the eyes" in clean_fg["fg_character_lead_investigator"]["description"].lower()
    assert clean_fg["fg_character_lead_investigator"].get("censor_bar_enforced") is True

    # 4. Normal document unchanged in type
    assert clean_fg["fg_evidence_docket"]["type"] == "document"


def test_audit_cliffhanger_5_patterns():
    # 1. THE_PRICE_LINE
    p1 = audit_cliffhanger_patterns("The price was millions of lives and a divided memory.")
    assert p1["matched"] is True
    assert p1["pattern"] == "THE_PRICE_LINE"

    # 2. THE_DATED_FORWARD_JUMP
    p2 = audit_cliffhanger_patterns("Then, in 1980, a boy found the money.")
    assert p2["matched"] is True
    assert p2["pattern"] == "THE_DATED_FORWARD_JUMP"

    # 3. THE_MISSING_PIECE
    p3 = audit_cliffhanger_patterns("They had his tie. They never had his name.")
    assert p3["matched"] is True
    assert p3["pattern"] == "THE_MISSING_PIECE"

    # 4. THE_UNRESOLVED_OBJECT
    p4 = audit_cliffhanger_patterns("The parachute has never been found.")
    assert p4["matched"] is True
    assert p4["pattern"] == "THE_UNRESOLVED_OBJECT"

    # 5. THE_QUIET_CONTRADICTION
    p5 = audit_cliffhanger_patterns("Yet throughout the entire trial, the vault was empty all along.")
    assert p5["matched"] is True
    assert p5["pattern"] == "THE_QUIET_CONTRADICTION"

    # 6. Generic non-pattern
    p6 = audit_cliffhanger_patterns("And so things continued to be normal and everyone went home.")
    assert p6["matched"] is False


def test_vox_paper_materials_library():
    assert len(VOX_PAPER_MATERIALS_LIBRARY) >= 6
    required_keys = ["aged_newsprint", "bleached_newsprint", "manila_docket", "vintage_kraft", "vellum_tracing", "cotton_parchment"]
    for k in required_keys:
        assert k in VOX_PAPER_MATERIALS_LIBRARY
        mat = VOX_PAPER_MATERIALS_LIBRARY[k]
        assert "label" in mat
        assert "description" in mat
        assert "hex" in mat
        assert len(mat["tactile_props"]) >= 2
