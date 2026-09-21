# tests/test_adversarial_director_gate.py
"""Unit tests for adversarial_director_gate.py.
Verifies detection of unlocalized text, high overlay density, empty kinetic counters, and auto-repair.
"""
import pytest
from scripts.orchestrator.adversarial_director_gate import (
    audit_props_integrity,
    auto_repair_props,
    run_adversarial_gate
)


def test_audit_props_integrity_detects_flaws():
    # Flawed Japanese episode props: 100% overlay, raw English titles, empty counter
    bad_scenes = []
    for i in range(50):
        bad_scenes.append({
            "scene_id": f"sc_{i}",
            "beat_number": (i % 5) + 1,
            "narration": f"Scene {i}",
            "speakerTag": "ARCHIVE X // DEFAULT",
            "forensicOverlay": {
                "type": "kinetic_counter" if i == 0 else "document_highlight",
                "title": "OFFICIAL INVESTIGATION RECORD",
                "badge": "SUBPOENAED EVIDENCE",
            }
        })
    props = {"scenes": bad_scenes}

    is_clean, defects = audit_props_integrity(props, market="JP")
    assert not is_clean
    assert any("OVERLAY_DENSITY_TOO_HIGH" in d for d in defects)
    assert any("UNLOCALIZED_OVERLAY_TEXT" in d for d in defects)
    assert any("LEAKED_ASSET_TAG" in d for d in defects)
    assert any("EMPTY_KINETIC_COUNTER" in d for d in defects)


def test_auto_repair_fixes_flaws(tmp_path):
    bad_scenes = []
    for i in range(50):
        bad_scenes.append({
            "scene_id": f"sc_{i}",
            "beat_number": (i % 5) + 1,
            "narration": f"Scene {i}",
            "speakerTag": "ARCHIVE X // DEFAULT",
            "forensicOverlay": {
                "type": "document_highlight",
                "title": "OFFICIAL INVESTIGATION RECORD",
                "badge": "SUBPOENAED EVIDENCE",
            }
        })
    props = {"scenes": bad_scenes}

    repaired = auto_repair_props(props, market="JP")
    is_clean, defects = audit_props_integrity(repaired, market="JP")
    assert is_clean
    assert len(defects) == 0

    # Overlay density must now be <= 20%
    fo_count = sum(1 for s in repaired["scenes"] if s.get("forensicOverlay"))
    assert (fo_count / len(repaired["scenes"])) <= 0.20


def test_run_adversarial_gate_end_to_end(tmp_path):
    bad_props = {
        "scenes": [
            {
                "scene_id": f"sc_{i}",
                "beat_number": (i % 5) + 1,
                "narration": f"Scene {i}",
                "forensicOverlay": {"type": "document_highlight", "title": "TEST"}
            }
            for i in range(30)
        ]
    }
    props_file = tmp_path / "remotion_props.json"
    import json
    with open(props_file, "w", encoding="utf-8") as f:
        json.dump(bad_props, f)

    report = run_adversarial_gate(
        episode_id="JP_EP0003_test",
        props_path=str(props_file),
        output_dir=str(tmp_path),
        render_stills=False
    )
    assert report["verdict"] == "PASS"
    assert (tmp_path / "director_gate_report.json").exists()
