#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_papertrails_voice_first.py — Hermetic regression tests for Voice-First Papertrails."""

import sys
from pathlib import Path

from app.services.papertrails_director import (
    KINETIC_CAMERAS,
    VALID_PROPS,
    _normalize_llm_shots_to_words,
    _sanitize_viewer_title,
    build_papertrails_timeline,
    direct_papertrails_timeline_with_llm,
)
from core.contracts.stages import StageID


def test_custom_investigative_props_registered():
    expected = {
        "courthouse", "gavel", "ledger", "container", "vault",
        "scale", "contract", "megaphone", "briefcase", "shield",
    }
    assert expected.issubset(VALID_PROPS)


def test_sanitize_viewer_title_strips_internal_ids():
    assert "B1" not in _sanitize_viewer_title("B1_HOOK // B1_L01", "Auditors flagged a customs dispute.", 0)
    clean = _sanitize_viewer_title("B3_SCHEME // B3_L04: Reserve Account", "Reserve accounts held funds.", 2)
    assert clean == "Reserve Account"
    fallback = _sanitize_viewer_title("", "Customs filings revealed hidden margin transfers.", 1)
    assert fallback == "Customs filings revealed hidden"


def test_normalize_llm_shots_to_words_contiguous_and_splits_long():
    words = [{"word": f"w{i}", "start": i * 0.5, "end": (i + 1) * 0.5} for i in range(16)]
    raw_shots = [
        {"word_start_idx": 0, "word_end_idx": 13, "prop": "courthouse", "biome": "snow"},
    ]
    out = _normalize_llm_shots_to_words(raw_shots, words, audio_duration=8.0)
    assert out[0]["start"] == 0.0
    assert out[-1]["end"] == 8.0
    for a, b in zip(out, out[1:]):
        assert a["end"] == b["start"]
    assert len(out) >= 2


def test_build_timeline_and_voice_first_stage_order():
    segments = [
        {
            "start": 0.0,
            "end": 4.2,
            "text": "The federal court struck down the disputed customs ruling.",
            "words": [
                {"word": w, "start": i * 0.45, "end": (i + 1) * 0.45}
                for i, w in enumerate(["The", "federal", "court", "struck", "down", "the", "disputed", "customs", "ruling."])
            ],
        },
        {
            "start": 4.2,
            "end": 8.0,
            "text": "Auditors traced executive payouts across retail ledgers.",
            "words": [
                {"word": w, "start": 4.2 + i * 0.52, "end": min(8.0, 4.2 + (i + 1) * 0.52)}
                for i, w in enumerate(["Auditors", "traced", "executive", "payouts", "across", "retail", "ledgers."])
            ],
        },
    ]
    tl = direct_papertrails_timeline_with_llm(
        transcript_segments=segments,
        audio_path=Path("voice.mp3"),
        audio_duration=8.0,
        timing_source="faster-whisper+edge-boundary",
        dry_run=True,
    )
    assert tl["width"] == 1920 and tl["height"] == 1080
    assert tl["scenes"][0]["start"] == 0.0
    assert tl["scenes"][-1]["end"] == 8.0
    for sc in tl["scenes"]:
        assert sc["camera"] in KINETIC_CAMERAS
        assert sc["prop"] in VALID_PROPS

    # Ensure build_papertrails_timeline also respects kinetic cameras & no adjacent (biome, prop) duplicates
    bt = build_papertrails_timeline(
        scenes_script=[
            {"scene_id": "S1", "headline": "B1_HOOK // B1_L01", "narration": "Court ruling triggered customs refund."},
            {"scene_id": "S2", "headline": "B2_SETUP // B2_L01", "narration": "Court ruling triggered customs refund."},
        ],
        audio_path=Path("voice.mp3"),
        audio_duration=8.0,
        transcript_segments=segments,
    )
    pairs = [(s["biome"], s["prop"]) for s in bt["scenes"]]
    assert pairs[0] != pairs[1]
    assert all(s["camera"] in KINETIC_CAMERAS for s in bt["scenes"])

    # Verify Voice-First stage ordering excludes S06/S07 and places S09 before S05 -> S08 -> S10 -> S11
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    else:
        sys.path.remove(repo_root)
        sys.path.insert(0, repo_root)
    if "scripts" in str(getattr(sys.modules.get("orchestrator"), "__file__", "")):
        sys.modules.pop("orchestrator", None)
    from orchestrator.run_pipeline import PAPERTRAILS_VOICE_FIRST_STAGES

    assert StageID.S6_CRITIC_VISUAL not in PAPERTRAILS_VOICE_FIRST_STAGES
    assert StageID.S7_IMAGE_GEN not in PAPERTRAILS_VOICE_FIRST_STAGES
    assert (
        PAPERTRAILS_VOICE_FIRST_STAGES.index(StageID.S9_VOICE_TTS)
        < PAPERTRAILS_VOICE_FIRST_STAGES.index(StageID.S5_DIRECTOR_PLAN)
        < PAPERTRAILS_VOICE_FIRST_STAGES.index(StageID.S8_VIDEO_GEN)
        < PAPERTRAILS_VOICE_FIRST_STAGES.index(StageID.S10_RENDER)
        < PAPERTRAILS_VOICE_FIRST_STAGES.index(StageID.S11_QC)
    )
