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
    audit_papertrails_timeline_antipatterns,
    build_papertrails_timeline,
    direct_papertrails_timeline_with_llm,
)
from core.contracts.stages import StageID
from vox.ffmpeg_utils import build_procedural_foley_inputs_and_filter


def test_custom_investigative_props_registered():
    expected = {
        "courthouse", "gavel", "ledger", "container", "vault",
        "scale", "contract", "megaphone", "briefcase", "shield",
        "hanko-stamp", "brass-caliper", "forensic-loupe",
    }
    assert expected.issubset(VALID_PROPS)
    assert len(VALID_PROPS) == 36


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


def test_timing_sheet_and_antipattern_audit():
    segments = [
        {
            "start": 0.0,
            "end": 4.2,
            "text": "Auditors stamped the secret footnote with a 42 percent spread.",
            "words": [
                {"word": w, "start": i * 0.35, "end": (i + 1) * 0.35}
                for i, w in enumerate(
                    ["Auditors", "stamped", "the", "secret", "footnote", "with", "a", "42", "percent", "spread."]
                )
            ],
        },
        {
            "start": 4.2,
            "end": 8.0,
            "text": "The federal ruling locked the treasury vault.",
            "words": [
                {"word": w, "start": 4.2 + i * 0.5, "end": min(8.0, 4.2 + (i + 1) * 0.5)}
                for i, w in enumerate(["The", "federal", "ruling", "locked", "the", "treasury", "vault."])
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
    assert len(tl["foley_cues"]) == len(tl["scenes"])
    for sc in tl["scenes"]:
        dur = sc["end"] - sc["start"]
        assert 0.0 <= sc["timing"]["contactSec"] <= dur
        assert sc["timing"]["sfxKind"]

    clean_audit = audit_papertrails_timeline_antipatterns(tl)
    assert clean_audit["passed"], clean_audit

    bad_cam = {**tl, "scenes": [{**tl["scenes"][0], "camera": "wide"}, *tl["scenes"][1:]]}
    cam_audit = audit_papertrails_timeline_antipatterns(bad_cam)
    assert not cam_audit["passed"]
    assert any("non-kinetic camera" in v for v in cam_audit["violations"])

    if len(tl["scenes"]) >= 2:
        s0 = tl["scenes"][0]
        s1_dup = {**tl["scenes"][1], "biome": s0["biome"], "prop": s0["prop"]}
        dup_audit = audit_papertrails_timeline_antipatterns({**tl, "scenes": [s0, s1_dup, *tl["scenes"][2:]]})
        assert not dup_audit["passed"]
        assert any("consecutive duplicate staging" in v for v in dup_audit["violations"])

        s1_same_prop = {
            **tl["scenes"][1],
            "biome": "desert" if s0["biome"] != "desert" else "snow",
            "prop": s0["prop"],
        }
        prop_audit = audit_papertrails_timeline_antipatterns({**tl, "scenes": [s0, s1_same_prop, *tl["scenes"][2:]]})
        assert not prop_audit["passed"]
        assert any("consecutive duplicate prop" in v for v in prop_audit["violations"])


def test_attach_grounded_evidence_cards_native_language_kr():
    """Ensure 12+ shot Korean timeline auto-populates native Hangul note cards and avoids adjacent cards."""
    segments = [
        {
            "start": i * 3.0,
            "end": (i + 1) * 3.0,
            "text": f"제 {i + 1} 구간의 약 {10 + i}조 원 규모 점검 결과입니다.",
            "words": [
                {"word": w, "start": i * 3.0 + j * 0.45, "end": i * 3.0 + (j + 1) * 0.45}
                for j, w in enumerate(["제", f"{i + 1}번", f"{10 + i}조", "원", "규모", "검증", "보고."])
            ],
        }
        for i in range(12)
    ]
    claims = [
        {"claim_id": "C001", "quantified_value": "10조 원", "statement": "기관 출자 약정 규모가 10조 원으로 집계됐습니다.", "source": "경제신문"},
        {"claim_id": "C002", "quantified_value": "25곳", "statement": "금융회사 25곳의 참여 여부를 점검 중입니다.", "source": "금융보도"},
    ]
    tl = direct_papertrails_timeline_with_llm(
        transcript_segments=segments,
        audio_path=Path("voice.mp3"),
        audio_duration=36.0,
        grounding_claims=claims,
        market="KR",
        timing_source="faster-whisper+edge-boundary",
        dry_run=True,
    )
    audit = audit_papertrails_timeline_antipatterns(tl)
    assert audit["passed"], audit
    cards = [sc for sc in tl["scenes"] if sc.get("card")]
    assert len(cards) >= 3
    for sc in cards:
        assert "핵심 근거" in sc["card"]["head"]
        assert any("`" in ln for ln in sc["card"]["lines"])
    for a, b in zip(tl["scenes"], tl["scenes"][1:]):
        assert a["prop"] != b["prop"]
        assert not (a.get("card") and b.get("card"))


def test_procedural_foley_filter_graph_builder():
    cues = [
        {"scene_id": "shot-001", "cue_idx": 0, "prop": "hanko-stamp", "sfx_kind": "stamp_thud", "time_sec": 0.4},
        {"scene_id": "shot-002", "cue_idx": 1, "prop": "brass-caliper", "sfx_kind": "caliper_click", "time_sec": 2.1},
        {"scene_id": "shot-003", "cue_idx": 2, "prop": "forensic-loupe", "sfx_kind": "loupe_whoosh", "time_sec": 4.8},
    ]
    inputs_a, graph_a = build_procedural_foley_inputs_and_filter(cues, duration_sec=8.0, seed=42)
    inputs_b, _ = build_procedural_foley_inputs_and_filter(cues, duration_sec=8.0, seed=99)
    assert inputs_a.count("lavfi") == 3
    assert "adelay=400:all=1" in graph_a
    assert "adelay=2100:all=1" in graph_a
    assert "amix=inputs=4:normalize=0:duration=first[aout]" in graph_a
    assert inputs_a != inputs_b
