"""
Unit test for B3 VOX Editorial Storyboard & Object-Focus Engine.
Validates:
1. detect_object_focus for legal, memo, financial, money trail, org chart keywords.
2. detect_layout_zone for spatial alternation.
3. detect_animation_cue for trigger word parsing.
4. detect_frame_transition for camera/tension mapping.
5. Foreground character hard cap pruning (<= 12 scenes).
6. Adversarial director gate integrity audits.
"""
import pytest
from app.services.director_planner_b3 import (
    detect_object_focus,
    detect_layout_zone,
    detect_animation_cue,
    detect_frame_transition,
)
from scripts.orchestrator.adversarial_director_gate import audit_props_integrity, auto_repair_props


def test_detect_object_focus():
    # Court docket
    doc = detect_object_focus("The FTC filed an antitrust lawsuit against the corporation.")
    assert doc is not None
    assert doc["type"] == "court_docket"
    assert "DISTRICT COURT" in doc["title"]

    # Redacted memo
    memo = detect_object_focus("An internal confidential memo revealed the hidden strategy.")
    assert memo is not None
    assert memo["type"] == "redacted_memo"

    # Financial ledger
    ledger = detect_object_focus("The audit ledger showed billions of dollars in unallocated revenue.")
    assert ledger is not None
    assert ledger["type"] == "financial_ledger"

    # Money trail network
    wire = detect_object_focus("They used offshore wire transfers and intermediary shell accounts.")
    assert wire is not None
    assert wire["type"] == "money_trail_network"

    # Corporate org chart
    org = detect_object_focus("The parent company controlled 14 subsidiaries across the region.")
    assert org is not None
    assert org["type"] == "corporate_org_chart"


def test_detect_layout_zone():
    # No FG -> full bleed center document
    lz_no_fg = detect_layout_zone(has_fg=False, scene_idx=0)
    assert lz_no_fg["placement"] in ("center_hero_document", "macro_detail_focus")

    # FG right -> split left
    lz_fg_right = detect_layout_zone(has_fg=True, fg_position="right", scene_idx=1)
    assert lz_fg_right["placement"] == "split_evidence_left"

    # FG left -> split right
    lz_fg_left = detect_layout_zone(has_fg=True, fg_position="left", scene_idx=2)
    assert lz_fg_left["placement"] == "split_evidence_right"


def test_detect_animation_cue():
    # Metric rollup
    cue_metric = detect_animation_cue("The loss exceeded $20 billion in three months.")
    assert cue_metric["effect"] == "counter_rollup"
    assert cue_metric["trigger_word"] in ("$", "20", "billion")

    # Red stamp slam
    cue_stamp = detect_animation_cue("This illegal scheme was a massive fraud on sellers.")
    assert cue_stamp["effect"] == "red_stamp_slam"

    # Marker highlight default
    cue_highlight = detect_animation_cue("The contracts were quietly signed behind closed doors.")
    assert cue_highlight["effect"] == "yellow_marker_highlight"


def test_detect_frame_transition():
    trans_zoom = detect_frame_transition("snap_zoom", "high", scene_idx=0)
    assert trans_zoom["type"] == "macro_zoom_through"
    assert trans_zoom["sfx_cue"] == "stamp_thud"

    trans_pan = detect_frame_transition("cinematic_pan", "medium", scene_idx=0)
    assert "whip_pan" in trans_pan["type"]
    assert trans_pan["sfx_cue"] == "camera_whoosh"


def test_adversarial_director_gate_fg_audit_and_repair():
    # Create 20 scenes with 15 foreground characters (> 20% density)
    scenes = []
    for i in range(20):
        scenes.append({
            "background": f"bg_{i}.jpg",
            "foreground": f"fg_{i}.png" if i < 15 else "",
            "layout_zone": {"placement": "split_evidence_left"},
            "narration": f"Scene narration line {i}",
            "durationInFrames": 120,
        })
    props = {"scenes": scenes}

    # Audit should flag high FG density
    is_clean, defects = audit_props_integrity(props, "EN")
    assert not is_clean
    assert any("FG_DENSITY_TOO_HIGH" in d for d in defects)

    # Auto-repair should prune FG down to <= 12
    repaired = auto_repair_props(props, "EN")
    repaired_fg_count = sum(1 for s in repaired["scenes"] if s.get("foreground"))
    assert repaired_fg_count <= 12
