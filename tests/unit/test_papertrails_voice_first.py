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

    # Verify coarse 5-shot 240s timelines are rejected fail-closed
    coarse_scenes = [
        {**tl["scenes"][0], "id": f"shot-{k + 1:03d}", "start": k * 48.0, "end": (k + 1) * 48.0, "prop": ["chart", "ledger", "contract", "scale", "vault"][k]}
        for k in range(5)
    ]
    coarse_audit = audit_papertrails_timeline_antipatterns({**tl, "duration": 240.0, "scenes": coarse_scenes})
    assert not coarse_audit["passed"]
    assert any("Insufficient shot density" in v for v in coarse_audit["violations"])


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
    assert tl["stageMode"] == "forensic_desk"
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


def test_sanitize_viewer_title_strips_korean_lead_stopwords_and_trailing_verbs():
    assert _sanitize_viewer_title("", "따르면 산업은행이 2020년 약정액을") == "산업은행이 2020년 약정액"
    assert _sanitize_viewer_title("", "출자 규모가 10조원이라고 보도했습니다") == "출자 규모가 10조원"
    assert _sanitize_viewer_title("", "증권 유관기관이 7,600억원을 추가로") == "증권 유관기관이 7,600억원"
    assert _sanitize_viewer_title("100조원으로 확대하자고 제안했다고 보도했습니다", "예비 문장") == "100조원으로 확대"
    assert _sanitize_viewer_title("핵심 기관은 확대를 위해 총력을 기울였다", "예비 문장") == "핵심 기관은 확대"
    assert _sanitize_viewer_title("", "다섯 차례 투입됐습니다") == "다섯 차례"
    assert not _sanitize_viewer_title("", "일각에서 확대를 위해 추가 검토를 진행했다").endswith("위해")


def test_timeline_market_localization_and_forensic_desk_geometry_invariants():
    from app.services.papertrails_director import _assign_beats_and_connectors

    tl = build_papertrails_timeline(
        scenes_script=[{"narration": "금융기관 25개 기관이 7,600억원을 출자했습니다.", "headline": "유관기관 출자 규모"}],
        audio_path=Path("voice.mp3"),
        audio_duration=4.0,
        market="KR",
    )
    assert tl["market"] == "KR"
    assert audit_papertrails_timeline_antipatterns(tl)["passed"]

    root = Path(__file__).resolve().parent.parent.parent / "vox" / "papertrails_engine" / "engine"
    daynight_js = (root / "src" / "render" / "daynight.js").read_text(encoding="utf-8")
    print_js = (root / "src" / "video" / "print_textures.js").read_text(encoding="utf-8")
    desk_js = (root / "src" / "video" / "forensic_desk.js").read_text(encoding="utf-8")
    props_js = (root / "src" / "video" / "props.js").read_text(encoding="utf-8")
    index_js = (root / "src" / "video" / "index.js").read_text(encoding="utf-8")
    timeline_mjs = (root / "src" / "video" / "timeline.mjs").read_text(encoding="utf-8")
    video_html = (root / "video.html").read_text(encoding="utf-8")

    assert "noDayNightGlow" in daynight_js
    assert "핵심 기록 // 보도 분석" in print_js
    assert "preloadIllustrationImages" in print_js
    assert "makeIllustratedCollagePlateMaterial" in print_js
    assert "computeJourneyOrigins" in desk_js
    for conn_name in ("highlighter_sweep", "timeline_rail", "money_flow", "red_yarn", "paper_tear"):
        assert conn_name in desk_js
    assert "illustrationImg" in props_js
    assert "typeof assets.getTilePrototype === 'function'" in props_js
    assert "preloadIllustrationImages" in index_js
    assert "BEAT_STUDIO_MOOD" in index_js
    assert "closeExposure" in index_js
    assert "let warmed = false" in index_js
    assert "if (!warmed)" in index_js
    renderer_mjs = (root.parent / "scripts" / "lib" / "renderer.mjs").read_text(encoding="utf-8")
    assert "Post-init browser settle" in renderer_mjs
    assert "CONNECTORS" in timeline_mjs
    assert "t.illustrations !== undefined" in timeline_mjs
    assert "width:36%" in video_html
    s08_src = (Path(__file__).resolve().parent.parent.parent / "stages" / "s08_video_gen.py").read_text(encoding="utf-8")
    assert "audit_hg3_stills" in s08_src

    # Verify 5-Beat connector diversification & fail-closed red_yarn cap
    sample_scenes = [{"id": f"shot-{i + 1:03d}"} for i in range(20)]
    _assign_beats_and_connectors(sample_scenes)
    assert {s["beat"] for s in sample_scenes} == {1, 2, 3, 4, 5}
    red_cnt = sum(1 for s in sample_scenes if s["connector"] == "red_yarn")
    assert red_cnt / len(sample_scenes) <= 0.20

    bad_desk = {
        **tl,
        "stageMode": "forensic_desk",
        "scenes": [{**tl["scenes"][0], "prop": "bridge"}],
    }
    bad_audit = audit_papertrails_timeline_antipatterns(bad_desk)
    assert not bad_audit["passed"]
    assert any("disallowed in forensic_desk mode" in v for v in bad_audit["violations"])

    over_yarn_scenes = [
        {**tl["scenes"][0], "id": f"shot-{i + 1:03d}", "start": i * 2.0, "end": (i + 1) * 2.0,
         "prop": ["chart", "ledger", "scale", "vault"][i % 4],
         "biome": ["heartland", "desert", "snow", "blossom", "pinewood"][i % 5],
         "camera": ["push", "orbit", "crane", "low"][i % 4],
         "connector": "red_yarn"}
        for i in range(12)
    ]
    over_yarn = audit_papertrails_timeline_antipatterns({**tl, "duration": 24.0, "scenes": over_yarn_scenes})
    assert not over_yarn["passed"]
    assert any("Monotonous red_yarn overuse" in v for v in over_yarn["violations"])


def test_hg3_visual_audit_rejects_crushed_black_and_blown_white_and_accepts_warm_editorial(tmp_path):
    import numpy as np
    from PIL import Image, ImageDraw
    from app.services.hg3_visual_audit import audit_hg3_stills

    dark_path = tmp_path / "dark_cave.png"
    dark_arr = np.full((720, 1280, 3), (10, 8, 7), dtype=np.uint8)
    dark_arr[260:360, 500:780] = (235, 224, 198)
    Image.fromarray(dark_arr, mode="RGB").save(dark_path)

    dark_audit = audit_hg3_stills([dark_path])
    assert dark_audit["passed"] is False
    dark_msg = " ".join(dark_audit["violations"])
    assert "crushed_black_pct" in dark_msg
    assert "mean_luma" in dark_msg

    blown_path = tmp_path / "blown_white.png"
    blown_arr = np.full((720, 1280, 3), (252, 250, 248), dtype=np.uint8)
    blown_arr[300:340, 560:720] = (40, 32, 24)
    Image.fromarray(blown_arr, mode="RGB").save(blown_path)

    blown_audit = audit_hg3_stills([blown_path])
    assert blown_audit["passed"] is False
    blown_msg = " ".join(blown_audit["violations"])
    assert "blown_white_pct" in blown_msg
    assert "mean_luma" in blown_msg

    flat_path = tmp_path / "flat_empty.png"
    flat_arr = np.full((720, 1280, 3), (130, 125, 115), dtype=np.uint8)
    Image.fromarray(flat_arr, mode="RGB").save(flat_path)

    flat_audit = audit_hg3_stills([flat_path])
    assert flat_audit["passed"] is False
    flat_msg = " ".join(flat_audit["violations"])
    assert "dynamic_range" in flat_msg
    assert "edge_energy" in flat_msg

    warm_path = tmp_path / "warm_editorial.png"
    warm_arr = np.full((720, 1280, 3), (184, 156, 116), dtype=np.uint8)
    rng = np.random.default_rng(42)
    grain = rng.integers(-8, 9, size=(720, 1280, 1))
    warm_arr = np.clip(warm_arr.astype(np.int16) + grain, 0, 255).astype(np.uint8)
    warm_img = Image.fromarray(warm_arr, mode="RGB")
    draw = ImageDraw.Draw(warm_img)
    draw.rectangle([280, 120, 1000, 580], fill=(244, 236, 216), outline=(54, 38, 22), width=3)
    draw.rectangle([280, 120, 1000, 196], fill=(31, 37, 46))
    draw.rectangle([820, 134, 982, 184], fill=(200, 62, 43))
    for r in range(6):
        ry = 230 + r * 52
        draw.rectangle([320, ry, 940, ry + 12], fill=(43, 30, 18))
    warm_img.save(warm_path)

    report_path = tmp_path / "hg3_visual_audit.json"
    warm_audit = audit_hg3_stills([warm_path], report_path=report_path)
    assert warm_audit["passed"] is True, warm_audit
    assert report_path.exists()
    m = warm_audit["frames"][0]["metrics"]
    assert 78.0 <= m["mean_luma"] <= 208.0
    assert m["crushed_black_pct"] <= 18.0
    assert m["blown_white_pct"] <= 16.0



