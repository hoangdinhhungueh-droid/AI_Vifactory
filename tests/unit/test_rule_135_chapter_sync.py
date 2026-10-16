#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_rule_135_chapter_sync.py
Unit tests verifying Rule 135: Exact frame-accurate and timestamp-accurate YouTube chapter synchronization
directly from Remotion / Vox pipeline manifests (manifest.json / remotion_props.json).
"""

import json
from pathlib import Path

from app.services.seo_package_forge import sync_exact_chapters_from_remotion


def test_sync_exact_chapters_from_vox_manifest(tmp_path: Path):
    """Rule 135: YouTube chapter timestamps must strictly match scenes[i].start accumulation."""
    manifest_data = {
        "fps": 30,
        "scenes": [
            {
                "scene_id": "scene_001",
                "beat_phase": 1,
                "start": 0.0,
                "end": 20.0,
                "speakerTag": "BEAT 1: COLD OPEN",
                "actTitle": "The Paradox"
            },
            {
                "scene_id": "scene_002",
                "beat_phase": 2,
                "start": 20.0,
                "end": 50.0,
                "speakerTag": "BEAT 2: RED HERRING",
                "actTitle": "The False Trail"
            },
            {
                "scene_id": "scene_003",
                "beat_phase": 3,
                "start": 50.0,
                "end": 85.0,
                "speakerTag": "BEAT 3: PAPER TRAIL",
                "actTitle": "Institutional Cracks"
            },
            {
                "scene_id": "scene_004",
                "beat_phase": 4,
                "start": 85.0,
                "end": 130.0,
                "speakerTag": "BEAT 4: SMOKING GUN",
                "actTitle": "The Machine Exposed"
            },
            {
                "scene_id": "scene_005",
                "beat_phase": 5,
                "start": 130.0,
                "end": 175.0,
                "speakerTag": "BEAT 5: MODERN MIRROR",
                "actTitle": "The Living Warning"
            }
        ]
    }

    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    chapter_lines = sync_exact_chapters_from_remotion(
        ep_dir_path=str(tmp_path),
        market="EN",
        title="The Forensic Investigation of Global Microchips",
        target_keyword="semiconductor supply chain",
        total_duration_s=175.0
    )

    assert len(chapter_lines) >= 3, f"Expected at least 3 chapters, got: {chapter_lines}"
    # 1. First chapter is always 00:00 (Rule 135)
    assert chapter_lines[0].startswith("00:00"), f"First chapter must start with 00:00: {chapter_lines[0]}"

    # Extract timestamps from lines
    timestamps = [line.split()[0] for line in chapter_lines]
    # 00:00, 00:20, 00:50, 01:25 (85s), 02:10 (130s)
    assert timestamps[0] == "00:00"
    assert timestamps[1] == "00:20"
    assert timestamps[2] == "00:50"
    assert timestamps[3] == "01:25"
    assert timestamps[4] == "02:10"


def test_sync_exact_chapters_duration_in_frames(tmp_path: Path):
    """Rule 135: Remotion durationInFrames accumulation matches (current_frame / fps)."""
    props_data = {
        "fps": 30,
        "scenes": [
            {
                "beat": 1,
                "durationInFrames": 450,  # 15s
                "actTitle": "Introduction"
            },
            {
                "beat": 2,
                "durationInFrames": 600,  # 20s -> total 35s
                "actTitle": "The Conflict"
            },
            {
                "beat": 3,
                "durationInFrames": 750,  # 25s -> total 60s (01:00)
                "actTitle": "The Discovery"
            }
        ]
    }

    props_file = tmp_path / "remotion_props.json"
    props_file.write_text(json.dumps(props_data, indent=2), encoding="utf-8")

    chapter_lines = sync_exact_chapters_from_remotion(
        remotion_props_path=str(props_file),
        market="EN",
        title="Tech Breakdown",
        target_keyword="tech",
        total_duration_s=60.0
    )

    assert len(chapter_lines) == 3
    timestamps = [line.split()[0] for line in chapter_lines]
    assert timestamps[0] == "00:00"
    assert timestamps[1] == "00:15"
    assert timestamps[2] == "00:35"
