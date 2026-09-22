#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for unified_vox_director & scene_schema compliance (Rule 121 & Rule 128)."""

import json
import pytest
from pathlib import Path
from app.services.unified_vox_director import (
    load_style_config,
    format_final_veo_prompt,
    get_action_description,
    build_unified_director_plan,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

def test_load_style_config():
    """Verify style-config.yaml loading for both presets."""
    vox_cfg = load_style_config("vox_forensic_paper")
    assert vox_cfg["name"] == "vox_forensic_paper"
    assert "tangible forensic" in vox_cfg["positive"]
    assert "12fps" in vox_cfg["motion_behavior"]
    assert "no photorealism" in vox_cfg["negative"]
    assert "static" in vox_cfg["camera_defaults"]["allowed"]

    voxel_cfg = load_style_config("voxel_stopmotion")
    assert voxel_cfg["name"] == "voxel_stopmotion"
    assert "voxel art style" in voxel_cfg["positive"]
    assert "no motion blur" in voxel_cfg["negative"]

def test_format_final_veo_prompt():
    """Verify final_veo_prompt string formatting matches the template."""
    cfg = load_style_config("voxel_stopmotion")
    prompt = format_final_veo_prompt(
        preset=cfg,
        subject="a small voxel fox character with orange cube fur",
        action="sitting still then slowly turning its head toward camera",
        setting="a miniature pixel forest diorama clearing at dawn",
        camera="static",
        lighting="warm diorama studio light, soft shadows, subtle rim light"
    )
    assert "voxel art style" in prompt
    assert "Scene: a small voxel fox character with orange cube fur sitting still then slowly turning its head toward camera in a miniature pixel forest diorama clearing at dawn." in prompt
    assert "Camera: static. Lighting: warm diorama studio light, soft shadows, subtle rim light." in prompt
    assert "no motion blur" in prompt

def test_scene_schema_compliance(tmp_path):
    """Verify that build_unified_director_plan produces scenes compliant with scene_schema.json."""
    schema_path = ROOT_DIR / "config" / "schemas" / "scene_schema.json"
    assert schema_path.exists(), "scene_schema.json must exist"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    required_fields = schema.get("required", [])
    allowed_cameras = schema.get("properties", {}).get("camera", {}).get("enum", [])
    allowed_transitions = schema.get("properties", {}).get("transition_out", {}).get("enum", [])

    sample_sentences = [
        {"text": "The Federal Trade Commission filed an antitrust lawsuit against Amazon.", "duration_frames": 150, "duration_sec": 5.0, "beat_index": 1},
        {"text": "Twenty billion dollars in damages was calculated across millions of merchants.", "duration_frames": 180, "duration_sec": 6.0, "beat_index": 1},
        {"text": "An internal project Nessie memo revealed algorithmic price gouging.", "duration_frames": 210, "duration_sec": 7.0, "beat_index": 2},
    ]

    result = build_unified_director_plan(sample_sentences, tmp_path, style_preset="vox_forensic_paper")
    scenes = result["scenes"]
    hero_clips = result["hero_clips"]

    assert len(scenes) == 3
    for s in scenes:
        for rf in required_fields:
            assert rf in s, f"Scene {s.get('scene_id')} missing required field: {rf}"
            assert s[rf] is not None, f"Field {rf} cannot be None"
        assert s["camera"] in allowed_cameras, f"Invalid camera: {s['camera']}"
        assert s["transition_out"] in allowed_transitions, f"Invalid transition: {s['transition_out']}"
        assert s["duration_seconds"] >= 4 and s["duration_seconds"] <= 8

    # Check hero clips
    for c in hero_clips:
        assert "final_veo_prompt" in c
        assert "prompt" in c
        assert c["transition_out"] in allowed_transitions
