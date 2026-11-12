#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Systemic Architecture & Adversarial Verification Suite for Stages S01-S04.

Proves zero-stub runtime integrity across:
1. Full DAG provenance, downstream export purge, optional S9->S8 propagation,
   symlink-safe deletion boundaries, and exclusive run-lock mutual exclusion.
2. Recon RSS / aggregator non-elevation and documented_outcome isolation in S01/S02.
3. Structured legal, procedural, speaker, and verification qualifier routing across KR/JA/VN/EN.
4. Algorithmic numeral normalization and un-tautological TTS duration calibration.
5. Closed S04 Gate 8 loopholes (60% coverage, 100% verified catalysts, Beat 1 safety,
   causal polarity), Gate 6A/6B bidirectional script & entity purity, and calibrated scoring.
6. Multi-market, non-Jeonse cross-topic end-to-end execution strictly bounded to S01-S04.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _make_ctx(tmp_path: Path, run_id: str, market: str, topic: str):
    from app.services.preset_loader import load_preset
    from core.config import RunContext, load_profile
    from core.paths import RunPaths
    from core.run_manifest import RunManifest

    paths = RunPaths(run_id=run_id, repo_root=tmp_path)
    paths.ensure_dirs()
    manifest = RunManifest.create_new(run_id=run_id, profile="e2e_min", market=market)
    cfg = load_profile("e2e_min")
    preset = load_preset("story_forensic")
    return RunContext(
        run_id=run_id,
        preset=preset,
        paths=paths,
        manifest=manifest,
        config=cfg,
        dry_run=True,
        topic=topic,
    )


def test_dag_provenance_invalidation_export_purge_and_lock(tmp_path):
    from core.contracts.stages import Provenance, StageArtifact, StageID
    from core.dag_provenance import (
        STAGE_EXPORT_SPECS,
        acquire_run_lock,
        check_stage_cache_valid,
        compute_stage_config_sha256,
        compute_stage_input_provenance,
        stamp_artifact_provenance,
    )
    from core.gates import emit_artifact
    from core.paths import RunPaths
    from core.run_manifest import RunManifest

    paths = RunPaths(run_id="TEST_DAG_FULL", repo_root=tmp_path)
    paths.ensure_dirs()
    manifest = RunManifest.create_new("TEST_DAG_FULL", profile="e2e_min")

    # Populate artifacts for all S1..S11 plus secondary root files, globs, and subdirs
    for sid in StageID:
        art = StageArtifact(
            schema_version="1.0.0",
            run_id="TEST_DAG_FULL",
            stage=sid,
            status="ok",
            payload={"topic": "Semiconductor Audit", "market": "KR"},
            provenance=Provenance(generator="unit_test"),
        )
        art_path = emit_artifact(art, paths)
        sha = art_path.read_bytes()
        import hashlib
        sha_hex = hashlib.sha256(sha).hexdigest()
        manifest.mark(sid, "done", artifact_sha256=sha_hex)

        spec = STAGE_EXPORT_SPECS.get(sid, {})
        for rf in spec.get("root_files", []):
            p = paths.root / rf
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("stale_export", encoding="utf-8")
        for rd in spec.get("root_dirs", []):
            d = paths.root / rd
            d.mkdir(parents=True, exist_ok=True)
            (d / "dummy.bin").write_bytes(b"stale_dir_payload")
        for idx, _ in enumerate(spec.get("root_globs", [])):
            (paths.root / f"clip_scene_{idx:02d}.mp4").write_bytes(b"stale_clip")

    # External sentinel file outside episode root must never be touched
    outside_sentinel = tmp_path / "external_keep.txt"
    outside_sentinel.write_text("keep_me", encoding="utf-8")

    # 1. Invalidating S2 (inclusive=False) must invalidate S3..S11 and purge all secondary exports + subdirs
    invalidated = manifest.invalidate_downstream(StageID.S2_RESEARCH, inclusive=False, paths=paths)
    assert StageID.S3_SCRIPT.value in invalidated
    assert StageID.S11_QC.value in invalidated
    assert manifest.stages[StageID.S1_IDEATION.value].status == "done"
    assert manifest.stages[StageID.S2_RESEARCH.value].status == "done"
    assert manifest.stages[StageID.S3_SCRIPT.value].status == "pending"
    assert not (paths.root / "spoken_script.txt").exists()
    assert not (paths.root / "director_plan.json").exists()
    assert not (paths.root / "remotion_props.json").exists()
    assert not (paths.root / "seo_package.json").exists()
    assert not (paths.root / "clip_scene_00.mp4").exists()
    assert not (paths.root / "video_clips").exists()
    assert not (paths.root / "audio").exists()
    assert not (paths.root / "10_render").exists()
    assert not (paths.root / "master_sheets").exists()
    assert outside_sentinel.read_text(encoding="utf-8") == "keep_me"

    # 2. Optional parent propagation: S9 -> S8 -> S10 -> S11
    for sid in (StageID.S8_VIDEO_GEN, StageID.S9_VOICE_TTS, StageID.S10_RENDER, StageID.S11_QC):
        manifest.mark(sid, "done", artifact_sha256="deadbeef")
        emit_artifact(
            StageArtifact(
                schema_version="1.0.0",
                run_id="TEST_DAG_FULL",
                stage=sid,
                status="ok",
                payload={"ok": True},
                provenance=Provenance(generator="unit_test"),
            ),
            paths,
        )
    manifest.stages[StageID.S8_VIDEO_GEN.value].upstream_artifacts = {
        StageID.S9_VOICE_TTS.value: "deadbeef"
    }
    s9_down = manifest.invalidate_downstream(StageID.S9_VOICE_TTS, paths=paths)
    assert StageID.S8_VIDEO_GEN.value in s9_down
    assert StageID.S10_RENDER.value in s9_down
    assert StageID.S11_QC.value in s9_down

    # 3. Cryptographic cache validation catches grounding_intel.json and config mutations
    (paths.root / "grounding_intel.json").write_text('{"claims": ["v1"]}', encoding="utf-8")
    s3_art = StageArtifact(
        schema_version="1.0.0",
        run_id="TEST_DAG_FULL",
        stage=StageID.S3_SCRIPT,
        status="ok",
        payload={"ok": True},
        provenance=Provenance(generator="unit_test"),
    )
    s3_path = emit_artifact(s3_art, paths)
    cfg_sha = compute_stage_config_sha256(
        StageID.S3_SCRIPT,
        preset_name="e2e_min",
        repo_root=ROOT_DIR,
        extra_params={"preset": "story_forensic"},
    )
    in_sha, up_map = compute_stage_input_provenance(StageID.S3_SCRIPT, paths, cfg_sha)
    stamp_artifact_provenance(s3_path, in_sha, cfg_sha, up_map, "nonce-1")

    import hashlib
    s3_sha = hashlib.sha256(s3_path.read_bytes()).hexdigest()
    manifest.mark(StageID.S3_SCRIPT, "done", artifact_sha256=s3_sha)
    manifest.stages[StageID.S3_SCRIPT.value].input_sha256 = in_sha
    manifest.stages[StageID.S3_SCRIPT.value].config_sha256 = cfg_sha
    manifest.stages[StageID.S3_SCRIPT.value].upstream_artifacts = up_map
    ok_hit, reason_hit = check_stage_cache_valid(
        StageID.S3_SCRIPT, paths, manifest.stages[StageID.S3_SCRIPT.value], in_sha, cfg_sha, s3_sha
    )
    assert ok_hit is True and reason_hit == "ok"

    # Mutate grounding_intel.json -> cache misses
    (paths.root / "grounding_intel.json").write_text('{"claims": ["v2_edited"]}', encoding="utf-8")
    new_in_sha, _ = compute_stage_input_provenance(StageID.S3_SCRIPT, paths, cfg_sha)
    ok_g, reason_g = check_stage_cache_valid(
        StageID.S3_SCRIPT, paths, manifest.stages[StageID.S3_SCRIPT.value], new_in_sha, cfg_sha, s3_sha
    )
    assert ok_g is False and reason_g == "input_provenance_changed"

    # Mutate config hash -> cache misses
    ok_c, reason_c = check_stage_cache_valid(
        StageID.S3_SCRIPT, paths, manifest.stages[StageID.S3_SCRIPT.value], in_sha, "different_cfg_sha", s3_sha
    )
    assert ok_c is False and reason_c == "config_provenance_changed"

    # 4. Exclusive lock prevents concurrent acquisition on same episode
    err_holder = []

    def _contend():
        try:
            with acquire_run_lock(paths, timeout_sec=0.2):
                pass
        except TimeoutError as exc:
            err_holder.append(exc)

    with acquire_run_lock(paths, timeout_sec=2.0):
        t = threading.Thread(target=_contend)
        t.start()
        t.join(timeout=3.0)
    assert len(err_holder) == 1 and isinstance(err_holder[0], TimeoutError)


def test_s01_s02_rss_non_elevation_and_outcome_isolation(tmp_path):
    from app.schemas.story_contracts import EvidenceClaim
    from stages.s01_ideation import run as s01_run
    from stages.s02_research import run as s02_run

    # Even if upstream attempts to tag a Google News RSS redirect as verified_primary / high,
    # EvidenceClaim and S01/S02 must downgrade and refuse elevation.
    rss_claim = EvidenceClaim(
        claim_id="C900",
        claim="Unverified rumor claims executive was indicted over missing $9B.",
        source_url="https://news.google.com/rss/articles/CBMiUkFVX3lxTE1abGNk",
        source_type="court",
        verification_status="verified_primary",
        evidence_tier="primary",
        confidence="high",
    )
    assert rss_claim.verification_status != "verified_primary"
    assert rss_claim.evidence_tier != "primary"
    assert rss_claim.confidence != "high"

    ctx = _make_ctx(tmp_path, "RUN_RSS_ISO", "EN", "Apex Foundry Export Compliance Audit")
    intel = {
        "topic": "Apex Foundry Export Compliance Audit",
        "claims": [
            {
                "claim": "Aggregator snippet alleges $9B secret offshore bailout deal under review.",
                "source_url": "https://news.google.com/rss/articles/CBMiFakeRss123",
                "source_name": "Google News RSS",
                "source_type": "press",
                "legal_status": "alleged",
                "verification_status": "verified_primary",
                "confidence": "high",
            },
            {
                "claim": "Commerce Department enforcement order assessed a $420 million civil penalty against Apex Foundry on March 14, 2025.",
                "source_url": "https://www.commerce.gov/enforcement/2025-apex-order",
                "source_name": "U.S. Department of Commerce",
                "source_type": "regulator",
                "doc_type": "regulatory_notice",
                "speaker": "regulator",
                "procedural_status": "final_judgment",
                "verification_status": "verified_primary",
                "causal_role": "primary_catalyst",
                "scope": "Apex Foundry US export division",
                "date": "2025-03-14",
                "legal_status": "fact",
                "confidence": "high",
            },
            {
                "claim": "Multi-tier distributor invoices obscured end-user destination codes between 2022 and 2024.",
                "source_url": "https://www.bis.doc.gov/audit-2025",
                "source_name": "Bureau of Industry and Security",
                "source_type": "gov",
                "doc_type": "audit_report",
                "verification_status": "verified_primary",
                "causal_role": "transmission_mechanism",
                "date": "2025-02-01",
                "legal_status": "fact",
                "confidence": "high",
            },
        ],
    }
    (ctx.paths.root / "grounding_intel.json").write_text(json.dumps(intel, indent=2), encoding="utf-8")

    s1_art = s01_run(ctx)
    assert "offshore bailout" not in s1_art.payload.get("documented_outcome", "").lower()
    assert "$420 million" in s1_art.payload.get("documented_outcome", "")

    s2_art = s02_run(ctx)
    ledger = s2_art.payload.get("evidence_ledger", [])
    assert len(ledger) == 3
    # Official verified_primary claims must outrank RSS aggregator claim
    assert ledger[0]["verification_status"] == "verified_primary"
    rss_entries = [c for c in ledger if "news.google.com/rss" in c["source_url"]]
    assert len(rss_entries) == 1
    assert rss_entries[0]["verification_status"] in ("unverified_secondary", "speculative")
    assert rss_entries[0]["confidence"] != "high"
    assert ledger[0]["doc_type"] == "regulatory_notice"
    assert ledger[0]["scope"] == "Apex Foundry US export division"


def test_structured_legal_qualifier_routing_matrix():
    from app.services.story_provenance_engine import (
        line_matches_expected_qualifier,
        route_legal_qualifier,
    )

    # 1. KR criminal_complaint (plaintiff) vs prosecutor indictment vs press_charge vs bill_proposed
    comp_line = route_legal_qualifier(
        "계약 위반 손해가 발생했습니다.",
        legal_status="charged",
        source_type="court",
        market="KR",
        doc_type="criminal_complaint",
        speaker="plaintiff",
        verification_status="corroborated_secondary",
    )
    assert "고발장·소장에 따르면" in comp_line
    assert "공소장에 따르면" not in comp_line

    indict_line = route_legal_qualifier(
        "자금이 외부 계좌로 이체됐습니다.",
        legal_status="charged",
        source_type="court",
        market="KR",
        doc_type="indictment",
        speaker="prosecutor",
        verification_status="verified_primary",
    )
    assert "검찰 공소장에 따르면" in indict_line

    press_charge = route_legal_qualifier(
        "관련 임원 3명이 기소됐습니다.",
        legal_status="charged",
        source_type="press",
        market="KR",
        doc_type="news_article",
        verification_status="corroborated_secondary",
    )
    assert "보도된 기소 내용에 따르면" in press_charge
    assert "검찰 공소장에 따르면" not in press_charge

    proposed_line = route_legal_qualifier(
        "신규 예치금 보호 제도가 도입됩니다.",
        legal_status="alleged",
        source_type="gov",
        market="KR",
        doc_type="statute",
        procedural_status="bill_proposed",
        verification_status="corroborated_secondary",
    )
    assert "추진" in proposed_line

    # 2. Unverified RSS claim must never claim regulatory authority
    unv_ja = route_legal_qualifier(
        "子会社の資産評価に疑義が生じました。",
        legal_status="alleged",
        source_type="press",
        market="JA",
        doc_type="rss_snippet",
        verification_status="unverified_secondary",
    )
    assert "未確認" in unv_ja and "当局の調査によれば" not in unv_ja

    unv_vn = route_legal_qualifier(
        "Khoản nợ trái phiếu chậm thanh toán.",
        legal_status="alleged",
        source_type="press",
        market="VN",
        doc_type="rss_snippet",
        verification_status="unverified_secondary",
    )
    assert "chưa kiểm chứng" in unv_vn.lower() and "cơ quan chức năng" not in unv_vn.lower()

    # 3. Verifier gate rejects misattributed lines
    ok_bad, _ = line_matches_expected_qualifier(
        "규제 당국에 따르면, 신규 회계 부정 의혹이 제기됐습니다.",
        {
            "legal_status": "alleged",
            "source_type": "press",
            "doc_type": "rss_snippet",
            "verification_status": "unverified_secondary",
        },
        market="KR",
    )
    assert ok_bad is False


def test_tts_duration_calibration_and_algorithmic_numeral_normalization(tmp_path):
    from core.contracts.stages import Provenance, StageArtifact
    from core.gates import GateError, emit_artifact
    from core.pacing_budgeter import count_speech_units, estimate_script_speech_duration
    from stages.s03_script import _normalize_spoken_korean_numbers
    from stages.s04_critic_script import run as s04_run

    # Arbitrary numerals NOT in any hardcoded lookup table
    norm_kr = _normalize_spoken_korean_numbers("1987년 7월 19일 제48조 위반 742건 및 2029년 12월 기준")
    assert norm_kr == "1987년 7월 19일 제48조 위반 742건 및 2029년 12월 기준"

    units_num = count_speech_units("2029년 12월 24일 742건 18.5%", "KR", expand_numbers=True)
    # Must exceed raw character count (13 hangul/digit chars before normalization -> expanded spoken syllables > 24)
    assert units_num >= 24

    # S04 must reject fake est_duration_s=240.0 when measured spoken duration is ~6 seconds
    ctx = _make_ctx(tmp_path, "RUN_TAUTOLOGY_TRAP", "EN", "Semiconductor Antitrust Audit")
    claims = [
        {
            "claim_id": "C001",
            "claim": "Commerce authority fined Silicon Logistics $120M in 2025.",
            "source_url": "https://www.ftc.gov/case-1",
            "source_type": "regulator",
            "legal_status": "fact",
            "verification_status": "verified_primary",
            "causal_role": "primary_catalyst",
        }
    ]
    fake_beats = [
        {
            "beat_id": "B1_hook",
            "target_duration_s": 19.2,
            "lines": [
                {
                    "line_id": "B1_L01",
                    "text": "Silicon Logistics faced a $120M penalty in 2025.",
                    "claim_ids": ["C001"],
                    "visual_hook": "stat_hero",
                }
            ],
        }
    ]
    timing = estimate_script_speech_duration([fake_beats[0]["lines"][0]["text"]], market="EN", docudrama_tempo=True)
    assert timing["estimated_duration_sec"] < 15.0

    emit_artifact(
        StageArtifact(
            schema_version="1.0.0",
            run_id="RUN_TAUTOLOGY_TRAP",
            stage="s03_script",
            status="ok",
            payload={
                "topic": "Semiconductor Antitrust Audit",
                "market": "EN",
                "total_words": 500,  # Inflated synthetic word count
                "est_duration_s": 240.0,  # Fake tautological duration
                "beats": fake_beats,
                "evidence_ledger": claims,
            },
            provenance=Provenance(generator="unit_test"),
        ),
        ctx.paths,
    )
    with pytest.raises(GateError):
        s04_run(ctx)


def test_s04_gate8_loopholes_gate6ab_and_calibrated_rubric(tmp_path):
    from core.contracts.stages import Provenance, StageArtifact
    from core.gates import GateError, emit_artifact
    from stages.s03_script import _build_grounded_story_beats
    from stages.s04_critic_script import run as s04_run

    # Build a 12-claim non-Jeonse ledger
    ledger_12 = [
        {
            "claim_id": f"C{idx:03d}",
            "claim": (
                f"Federal Energy Commission fined Meridian Grid ${100 + idx}M on May {10 + idx}, 2025 for billing manipulation."
                if idx == 1
                else f"Audit exhibit {idx} documented Meridian Grid capacity withholding across Region {idx} totaling {50 * idx} MW."
            ),
            "source_url": "https://www.ferc.gov/orders/2025" if idx <= 6 else "https://news.google.com/rss/articles/CBMi99",
            "source_type": "regulator" if idx <= 6 else "press",
            "legal_status": "fact" if idx <= 4 else "alleged",
            "verification_status": "verified_primary" if idx <= 6 else "unverified_secondary",
            "causal_role": "primary_catalyst" if idx == 1 else ("transmission_mechanism" if idx in (2, 3) else "background_context"),
        }
        for idx in range(1, 13)
    ]

    # 1. Loophole check: 5/12 distinct claims (41.7% >= 3 claims) MUST fail 60% gate
    ctx_5_of_12 = _make_ctx(tmp_path, "RUN_LOOPHOLE_5_12", "EN", "Meridian Grid Billing Audit")
    sub_beats_5 = _build_grounded_story_beats(
        "Meridian Grid Billing Audit", ledger_12[:5], {c["claim_id"]: c for c in ledger_12[:5]}, market="EN"
    )
    # Build enough padding lines citing only C001..C005 to stay inside 180-300s while leaving C006..C012 uncovered
    padded_lines = [ln.model_dump() for _, _, lns in sub_beats_5 for ln in lns]
    emit_artifact(
        StageArtifact(
            schema_version="1.0.0",
            run_id="RUN_LOOPHOLE_5_12",
            stage="s03_script",
            status="ok",
            payload={
                "topic": "Meridian Grid Billing Audit",
                "market": "EN",
                "beats": [
                    {"beat_id": b_id, "target_duration_s": d, "lines": [ln.model_dump() for ln in lns]}
                    for b_id, d, lns in sub_beats_5
                ],
                "evidence_ledger": ledger_12,
                "statement_claim_map": [{"line_id": ln["line_id"], "claim_ids": ln["claim_ids"]} for ln in padded_lines],
            },
            provenance=Provenance(generator="unit_test"),
        ),
        ctx_5_of_12.paths,
    )
    with pytest.raises(GateError) as exc_info_5:
        s04_run(ctx_5_of_12)
    assert exc_info_5.value.details["gates"]["claim_coverage_gate"] is False

    # 2. Gate 6A/6B rejection: inject foreign Hangul & foreign KRW/금감원 into EN script
    ctx_6ab = _make_ctx(tmp_path, "RUN_GATE6AB", "EN", "Meridian Grid Billing Audit")
    full_beats = _build_grounded_story_beats(
        "Meridian Grid Billing Audit", ledger_12, {c["claim_id"]: c for c in ledger_12}, market="EN"
    )
    contaminated_beats = [
        {"beat_id": b_id, "target_duration_s": d, "lines": [ln.model_dump() for ln in lns]}
        for b_id, d, lns in full_beats
    ]
    contaminated_beats[1]["lines"][0]["text"] += " 금융감독원 조사 결과 한국어 문장 혼입."
    emit_artifact(
        StageArtifact(
            schema_version="1.0.0",
            run_id="RUN_GATE6AB",
            stage="s03_script",
            status="ok",
            payload={
                "topic": "Meridian Grid Billing Audit",
                "market": "EN",
                "beats": contaminated_beats,
                "evidence_ledger": ledger_12,
            },
            provenance=Provenance(generator="unit_test"),
        ),
        ctx_6ab.paths,
    )
    with pytest.raises(GateError) as exc_info_6:
        s04_run(ctx_6ab)
    assert exc_info_6.value.details["gates"]["target_market_language_compliance"] is False
    assert exc_info_6.value.details["gates"]["market_entity_appropriateness"] is False

    # 3. Clean 12-claim EN script must pass with calibrated score (NOT hardcoded 9.2)
    ctx_clean = _make_ctx(tmp_path, "RUN_CLEAN_12", "EN", "Meridian Grid Billing Audit")
    clean_beats_dict = [
        {"beat_id": b_id, "target_duration_s": d, "lines": [ln.model_dump() for ln in lns]}
        for b_id, d, lns in full_beats
    ]
    emit_artifact(
        StageArtifact(
            schema_version="1.0.0",
            run_id="RUN_CLEAN_12",
            stage="s03_script",
            status="ok",
            payload={
                "topic": "Meridian Grid Billing Audit",
                "market": "EN",
                "beats": clean_beats_dict,
                "evidence_ledger": ledger_12,
            },
            provenance=Provenance(generator="unit_test"),
        ),
        ctx_clean.paths,
    )
    res_clean = s04_run(ctx_clean)
    assert res_clean.payload["verdict"] == "pass"
    assert res_clean.payload["gates"]["claim_coverage_gate"] is True
    assert res_clean.payload["gates"]["statement_claim_alignment_ok"] is True
    assert res_clean.payload["score_source"] == "deterministic_calibrated_rubric"


@pytest.mark.parametrize(
    "market,topic,claims",
    [
        (
            "KR",
            "반도체 공급망 보조금 감사",
            [
                {
                    "claim": "공정거래위원회가 2025년 4월 8일 오리온반도체에 4,200억 원 과징금을 부과했습니다.",
                    "source_url": "https://www.ftc.go.kr/news/2025-420",
                    "source_name": "공정거래위원회",
                    "source_type": "regulator",
                    "doc_type": "regulatory_notice",
                    "speaker": "regulator",
                    "procedural_status": "final_judgment",
                    "verification_status": "verified_primary",
                    "causal_role": "primary_catalyst",
                    "date": "2025-04-08",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "감사원 보고서는 하청 단가 후려치기와 기술자료 유용 계약 184건을 적발했습니다.",
                    "source_url": "https://www.bai.go.kr/audit-2025",
                    "source_name": "감사원",
                    "source_type": "gov",
                    "doc_type": "audit_report",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-02-19",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "검찰 공소장은 허위 연구비 정산 650억 원이 특수관계사 4곳으로 유출됐다고 적시했습니다.",
                    "source_url": "https://www.scourt.go.kr/case-2025-11",
                    "source_name": "서울중앙지법",
                    "source_type": "court",
                    "doc_type": "indictment",
                    "speaker": "prosecutor",
                    "procedural_status": "indicted",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-05-12",
                    "legal_status": "charged",
                    "confidence": "high",
                },
                {
                    "claim": "일부 언론은 해외 설비 매각 협상이 진행 중이라고 초기 보도했습니다.",
                    "source_url": "https://news.google.com/rss/articles/CBMiSemiKR01",
                    "source_name": "Google News RSS",
                    "source_type": "press",
                    "doc_type": "rss_snippet",
                    "verification_status": "unverified_secondary",
                    "causal_role": "background_context",
                    "date": "2025-06-01",
                    "legal_status": "alleged",
                    "confidence": "medium",
                },
            ],
        ),
        (
            "JA",
            "地方鉄道子会社の会計不正監査",
            [
                {
                    "claim": "国土交通省は2025年3月20日、北陸鉄道子会社に対し380億円の粉飾決算で改善命令を出しました。",
                    "source_url": "https://www.mlit.go.jp/report/2025-380",
                    "source_name": "国土交通省",
                    "source_type": "regulator",
                    "doc_type": "regulatory_notice",
                    "speaker": "regulator",
                    "procedural_status": "final_judgment",
                    "verification_status": "verified_primary",
                    "causal_role": "primary_catalyst",
                    "date": "2025-03-20",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "第三者委員会の監査報告書では、架空修繕費の計上が92件確認されました。",
                    "source_url": "https://www.fsa.go.jp/audit-rail-2025",
                    "source_name": "金融庁",
                    "source_type": "gov",
                    "doc_type": "audit_report",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-04-02",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "検察の起訴状は元取締役が資金45億円を関連会社へ還流させたと指摘しています。",
                    "source_url": "https://www.courts.go.jp/rail-2025",
                    "source_name": "東京地方裁判所",
                    "source_type": "court",
                    "doc_type": "indictment",
                    "speaker": "prosecutor",
                    "procedural_status": "indicted",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-05-15",
                    "legal_status": "charged",
                    "confidence": "high",
                },
                {
                    "claim": "一部報道では再編支援策が検討中と伝えられています。",
                    "source_url": "https://news.google.com/rss/articles/CBMiRailJA02",
                    "source_name": "Google News RSS",
                    "source_type": "press",
                    "doc_type": "rss_snippet",
                    "verification_status": "unverified_secondary",
                    "causal_role": "background_context",
                    "date": "2025-06-10",
                    "legal_status": "alleged",
                    "confidence": "medium",
                },
            ],
        ),
        (
            "VN",
            "Kiểm toán thanh khoản trái phiếu doanh nghiệp",
            [
                {
                    "claim": "Thanh tra Chính phủ ngày 18 tháng 4 năm 2025 công bố kết luận sai phạm phát hành trái phiếu trị giá 8.400 tỷ đồng.",
                    "source_url": "https://thanhtra.gov.vn/ket-luan-2025-8400",
                    "source_name": "Thanh tra Chính phủ",
                    "source_type": "regulator",
                    "doc_type": "regulatory_notice",
                    "speaker": "regulator",
                    "procedural_status": "final_judgment",
                    "verification_status": "verified_primary",
                    "causal_role": "primary_catalyst",
                    "date": "2025-04-18",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "Báo cáo kiểm toán xác định dòng tiền 3.200 tỷ đồng được chuyển lòng vòng qua 12 công ty trung gian.",
                    "source_url": "https://mof.gov.vn/audit-2025",
                    "source_name": "Bộ Tài chính",
                    "source_type": "gov",
                    "doc_type": "audit_report",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-05-03",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "Tài liệu truy tố nêu 5 lãnh đạo sử dụng tài sản đảm bảo định giá khống gấp 4 lần.",
                    "source_url": "https://toaan.gov.vn/ho-so-2025",
                    "source_name": "Tòa án Nhân dân",
                    "source_type": "court",
                    "doc_type": "indictment",
                    "speaker": "prosecutor",
                    "procedural_status": "indicted",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-05-22",
                    "legal_status": "charged",
                    "confidence": "high",
                },
                {
                    "claim": "Tin bước đầu cho rằng phương án giãn nợ đang được đàm phán với các trái chủ.",
                    "source_url": "https://news.google.com/rss/articles/CBMiBondVN03",
                    "source_name": "Google News RSS",
                    "source_type": "press",
                    "doc_type": "rss_snippet",
                    "verification_status": "unverified_secondary",
                    "causal_role": "background_context",
                    "date": "2025-06-04",
                    "legal_status": "alleged",
                    "confidence": "medium",
                },
            ],
        ),
        (
            "EN",
            "Biotech Cold-Chain Logistics Antitrust Investigation",
            [
                {
                    "claim": "The Federal Trade Commission filed an antitrust enforcement action against CryoVault Logistics over $680 million in exclusionary hospital contracts on April 11, 2025.",
                    "source_url": "https://www.ftc.gov/enforcement/cryovault-2025",
                    "source_name": "Federal Trade Commission",
                    "source_type": "regulator",
                    "doc_type": "regulatory_notice",
                    "speaker": "regulator",
                    "procedural_status": "indicted",
                    "verification_status": "verified_primary",
                    "causal_role": "primary_catalyst",
                    "date": "2025-04-11",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "Internal procurement audits uncovered 47 exclusivity clauses restricting regional clinic cooling hubs.",
                    "source_url": "https://www.justice.gov/atr/cryovault-audit",
                    "source_name": "Department of Justice",
                    "source_type": "gov",
                    "doc_type": "audit_report",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-03-02",
                    "legal_status": "fact",
                    "confidence": "high",
                },
                {
                    "claim": "Prosecutors alleged in the federal indictment that automated pricing penalties raised hospital fees by 34%.",
                    "source_url": "https://www.justice.gov/indictment-cryovault",
                    "source_name": "DOJ Antitrust Division",
                    "source_type": "court",
                    "doc_type": "indictment",
                    "speaker": "prosecutor",
                    "procedural_status": "indicted",
                    "verification_status": "verified_primary",
                    "causal_role": "transmission_mechanism",
                    "date": "2025-05-09",
                    "legal_status": "charged",
                    "confidence": "high",
                },
                {
                    "claim": "Preliminary news snippets reported potential divestiture discussions involving two midwest depots.",
                    "source_url": "https://news.google.com/rss/articles/CBMiCryoEN04",
                    "source_name": "Google News RSS",
                    "source_type": "press",
                    "doc_type": "rss_snippet",
                    "verification_status": "unverified_secondary",
                    "causal_role": "background_context",
                    "date": "2025-06-05",
                    "legal_status": "alleged",
                    "confidence": "medium",
                },
            ],
        ),
    ],
)
def test_cross_market_cross_topic_s01_s04_non_jeonse(tmp_path, market, topic, claims):
    """Run S01 -> S02 -> S03 -> S04 strictly (without touching S05+) on 4 non-Jeonse topics."""
    from core.pacing_budgeter import estimate_script_speech_duration
    from stages.s01_ideation import run as s01_run
    from stages.s02_research import run as s02_run
    from stages.s03_script import run as s03_run
    from stages.s04_critic_script import run as s04_run

    ctx = _make_ctx(tmp_path, f"RUN_SYS_{market}", market, topic)
    (ctx.paths.root / "grounding_intel.json").write_text(
        json.dumps({"topic": topic, "market": market, "claims": claims}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    s1 = s01_run(ctx)
    assert s1.status == "ok"

    s2 = s02_run(ctx)
    assert s2.status == "ok"
    assert len(s2.payload["evidence_ledger"]) == len(claims)

    s3 = s03_run(ctx)
    assert s3.status == "ok"
    assert 180.0 <= s3.payload["measured_speech_duration_s"] <= 300.0
    b1_lines = [ln["text"] for ln in s3.payload["beats"][0]["lines"]]
    b1_timing = estimate_script_speech_duration(b1_lines, market=market, docudrama_tempo=True)
    assert b1_timing["estimated_duration_sec"] <= 25.0

    s4 = s04_run(ctx)
    assert s4.payload["verdict"] == "pass"
    for gate_name, gate_ok in s4.payload["gates"].items():
        assert gate_ok is True, f"{market} failed gate {gate_name}"
    assert s4.payload["score_source"] == "deterministic_calibrated_rubric"
    assert not (ctx.paths.root / "s05_director_plan").exists()


def test_kr_ja_complaint_vs_indictment_substring_and_acquittal_provenance():
    """Guard against KR/JA substring collisions ('소장' in '공소장', '訴状' in '起訴状'),
    acquittal/negated-judgment mislabeling as 'convicted', and 'sec' substring misclassification.
    """
    from app.services.story_provenance_engine import (
        classify_claim_provenance,
        line_matches_expected_qualifier,
    )

    kr_complaint = {
        "claim_id": "C001",
        "claim": "민사 소장 제출로 손해배상 청구가 개시되었다.",
        "legal_status": "charged",
        "source_type": "court",
        "doc_type": "criminal_complaint",
        "speaker": "plaintiff",
        "verification_status": "corroborated_secondary",
    }
    ok_kr_launder, _ = line_matches_expected_qualifier("검찰 공소장에 따르면 손해배상 청구가 개시되었다.", kr_complaint, market="KR")
    assert ok_kr_launder is False
    ok_kr_valid, _ = line_matches_expected_qualifier("고발장·소장에 따르면 손해배상 청구가 개시되었다.", kr_complaint, market="KR")
    assert ok_kr_valid is True

    ja_complaint = {
        "claim_id": "C002",
        "claim": "民事訴状の提出により賠償請求が始まった。",
        "legal_status": "charged",
        "source_type": "court",
        "doc_type": "criminal_complaint",
        "speaker": "plaintiff",
        "verification_status": "corroborated_secondary",
    }
    ok_ja_launder, _ = line_matches_expected_qualifier("起訴状の指摘によれば賠償請求が始まった。", ja_complaint, market="JA")
    assert ok_ja_launder is False
    ok_ja_valid, _ = line_matches_expected_qualifier("訴状によれば賠償請求が始まった。", ja_complaint, market="JA")
    assert ok_ja_valid is True

    acq = classify_claim_provenance(
        {
            "claim": "2024년 5월 1일 대법원은 피고인에게 무죄를 선고했다.",
            "source": "대법원",
            "source_url": "https://www.scourt.go.kr/judgments/1",
            "date": "2024-05-01",
        },
        market="KR",
    )
    assert acq["legal_status"] == "fact"
    assert acq["confidence"] == "high"

    pending = classify_claim_provenance(
        {
            "claim": "피고인은 현재 판결 전 상태로 법리 다툼이 진행 중이다.",
            "source": "연합뉴스",
            "source_url": "https://www.yna.co.kr/1",
        },
        market="KR",
    )
    assert pending["legal_status"] != "convicted"

    undated_primary = classify_claim_provenance(
        {
            "claim": "Official commission notice confirmed licensing conditions.",
            "source": "SEC",
            "source_url": "https://www.sec.gov/litigation/1",
        },
        market="EN",
    )
    assert undated_primary["verification_status"] == "verified_primary"
    assert undated_primary["confidence"] == "medium"

    blog = classify_claim_provenance(
        {
            "claim": "Anonymous market commentary on sector risk.",
            "source": "Security Watch Blog",
            "source_url": "https://securitywatch.example.org/post",
        },
        market="EN",
    )
    assert blog["source_type"] == "press"


def test_gate6a_en_vietnamese_leak_and_kr_ja_vn_capitalized_english():
    """Gate 6A must catch Vietnamese-in-EN even with grounded acronyms AND capitalized English in KR/JA/VN."""
    from app.services.story_provenance_engine import check_target_market_language_purity

    en_with_vn = (
        "According to regulatory filings, USD 50 million was transferred. "
        "Các khoản thanh toán bất thường tiếp tục bị kiểm toán viên đặt dấu hỏi."
    )
    ok_en, issues_en = check_target_market_language_purity(en_with_vn, market="EN", grounded_proper_nouns={"USD"})
    assert ok_en is False and any("Vietnamese" in x for x in issues_en)

    kr_with_cap_en = "감독 당국 발표에 따르면 이번 조치는 시장에 큰 영향을 주었다. " * 6 + "The court in NY ruled on it."
    ok_kr, _ = check_target_market_language_purity(kr_with_cap_en, market="KR", grounded_proper_nouns={"NY"})
    assert ok_kr is False

    ja_with_cap_en = "監督当局の発表によれば、今回の措置は市場に大きな影響を与えた。" * 6 + "The court in NY ruled on it."
    ok_ja, _ = check_target_market_language_purity(ja_with_cap_en, market="JA", grounded_proper_nouns={"NY"})
    assert ok_ja is False

    vn_with_cap_en = "Theo cơ quan chức năng, báo cáo kiểm toán cho thấy dòng tiền bị thâm hụt nghiêm trọng. The court ruled on this case."
    ok_vn, _ = check_target_market_language_purity(vn_with_cap_en, market="VN")
    assert ok_vn is False


def test_metric_localization_tts_vn_scale_and_no_duplicate_clause_numbers():
    """Verify $40B localization accuracy, VN $40B TTS expansion, KR 22조원 expansion, and clean clause synthesis."""
    from app.services.story_provenance_engine import (
        expand_text_for_tts_timing,
        localize_dates_and_metrics,
        normalize_spoken_korean_numbers,
        translate_claim_to_market_clause,
    )

    assert "400억 달러" in localize_dates_and_metrics("Losses exceeded $40 billion.", "KR")
    assert "400億ドル" in localize_dates_and_metrics("Losses exceeded $40 billion.", "JA")
    assert "tỷ đô la" in expand_text_for_tts_timing("Thiệt hại lên tới $40B.", "VN")
    assert "이십이조원" in normalize_spoken_korean_numbers("규모는 22조원이다.", expand_for_tts=True)

    kr_clause = translate_claim_to_market_clause(
        "By November 10, 2026, authorities recognized 9,317 certified victims.",
        "KR",
        "보증금 제도",
    )
    assert "9,317, 9317" not in kr_clause
    assert kr_clause.count("9,317") <= 1 or kr_clause.count("9317") == 0


def test_s03_pick_claim_cycles_beyond_ledger_and_no_mid_paren_topic_leak():
    """Verify _localized_topic_label never leaves unbalanced parentheses and _pick_claim cycles across all claims."""
    from app.schemas.story_contracts import EvidenceClaim
    from stages.s03_script import _build_grounded_story_beats, _localized_topic_label

    lbl = _localized_topic_label("전세사기 피해자 최소보장제 (So-called Minimum Guarantee)", "KR")
    assert "(" not in lbl and "So" not in lbl

    claims = [
        EvidenceClaim(
            claim_id=f"C{i:03d}",
            claim=f"Official regulatory filing {i} documented 1,500{i} KRW variance on 2024-0{i}-10.",
            source_url="https://www.korea.kr/doc",
            source_type="regulator",
            date=f"2024-0{i}-10",
            legal_status="fact",
            confidence="high",
        )
        for i in range(1, 4)
    ]
    beats = _build_grounded_story_beats("보증금 검증", claims, {c.claim_id: c for c in claims}, market="KR")
    b5_cids = [cid for ln in beats[-1][2] for cid in ln.claim_ids]
    assert len(set(b5_cids)) >= 2


def test_s04_rejects_all_unverified_rss_dossier(tmp_path):
    """A large dossier (8+ claims) with 0 primary sources and <30% corroborated must be blocked at S04 ('revise')."""
    from core.gates import GateError
    from stages.s01_ideation import run as s01_run
    from stages.s02_research import run as s02_run
    from stages.s03_script import run as s03_run
    from stages.s04_critic_script import run as s04_run

    claims = [
        {
            "claim": f"Unverified aggregator snippet {i} claimed {100 + i} billion KRW exposure on 2025-01-{(i % 9) + 1:02d}.",
            "source": f"Outlet {i}",
            "source_url": f"https://news.google.com/rss/articles/item{i}",
            "date": f"2025-01-{(i % 9) + 1:02d}",
        }
        for i in range(1, 11)
    ]
    ctx = _make_ctx(tmp_path, "RUN_UNV_BLOCK", "KR", "테스트 사안 감사")
    (ctx.paths.root / "grounding_intel.json").write_text(
        json.dumps({"topic": "테스트 사안 감사", "market": "KR", "claims": claims}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    s01_run(ctx)
    s02_run(ctx)
    s03_run(ctx)
    with pytest.raises(GateError):
        s04_run(ctx)

    s4_art = json.loads(ctx.paths.artifact_file("s04_critic_script").read_text(encoding="utf-8"))
    assert s4_art["payload"]["verdict"] in ("revise", "fail")


def test_ja_vn_fallback_without_grounding_and_three_run_cache_hit(tmp_path):
    """JA/VN generic fallback without grounding_intel passes S01->S04 cleanly, and 3 consecutive runs stay cached."""
    import orchestrator.run_pipeline as run_pipeline_mod
    from core.paths import RunPaths
    from orchestrator.run_pipeline import execute_pipeline
    from stages.s01_ideation import run as s01_run
    from stages.s02_research import run as s02_run
    from stages.s03_script import run as s03_run
    from stages.s04_critic_script import run as s04_run

    for mkt, topic in [
        ("JA", "地方鉄道の保守会計監査"),
        ("VN", "Kiểm toán trái phiếu doanh nghiệp"),
    ]:
        ctx = _make_ctx(tmp_path, f"RUN_NO_GI_{mkt}", mkt, topic)
        s01_run(ctx)
        s2 = s02_run(ctx)
        assert len(s2.payload["evidence_ledger"]) == 7
        s03_run(ctx)
        s4 = s04_run(ctx)
        assert s4.payload["verdict"] == "pass"

    test_paths = RunPaths(run_id="RUN_THREE_PASS", repo_root=tmp_path)
    test_paths.ensure_dirs()
    orig_resolve = run_pipeline_mod.resolve_run_paths
    run_pipeline_mod.resolve_run_paths = lambda rid, repo_root=None: test_paths
    try:
        for run_no in range(1, 4):
            rc = execute_pipeline(
                from_stage=None,
                to_stage="s04_critic_script",
                run_id="RUN_THREE_PASS",
                profile="e2e_min",
                preset="story_forensic",
                market="EN",
                topic="Biotech Cold-Chain Logistics Audit",
                dry_run=True,
                human_gates=False,
            )
            assert rc == 0, f"Run {run_no} failed"
            manifest_data = json.loads(test_paths.manifest_file.read_text(encoding="utf-8"))
            for st in ("s01_ideation", "s02_research", "s03_script", "s04_critic_script"):
                expected_status = "done" if run_no == 1 else "skipped"
                assert manifest_data["stages"][st]["status"] == expected_status, (
                    f"Run {run_no} stage {st} had status {manifest_data['stages'][st]['status']}"
                )
    finally:
        run_pipeline_mod.resolve_run_paths = orig_resolve
    assert not test_paths.artifact_file("s05_director_plan").exists()
    assert manifest_data["stages"]["s05_director_plan"]["status"] == "pending"


def test_live_regression_fixes_json_metric_trim_and_tts_rates():
    """Verify parse_llm_json raw_decode resilience, metric regex word-before-letter, and calibrated TTS rates."""
    from app.services.story_provenance_engine import extract_claim_elements
    from core.llm_json import parse_llm_json
    from core.pacing_budgeter import DOCUDRAMA_SPEECH_RATES
    from stages.s03_script import _trim_clause_smart

    # 1. Leading digit / trailing prose must not trigger 'Extra data: line 1 column 2'
    parsed = parse_llm_json('1.\n{"title_working": "Audit Gap", "status": "APPROVED"}\nNote: done')
    assert isinstance(parsed, dict)
    assert parsed["title_working"] == "Audit Gap"

    # 2. '$172.7 million' must not be truncated to '$172.7 m' or duplicated by _trim_clause_smart
    claim_txt = (
        "Documented enforcement outcomes materialized as the insurer agreed to pay $172.7 million "
        "to resolve False Claims Act allegations without admitting liability."
    )
    elems = extract_claim_elements(claim_txt)
    assert any("$172.7 million" in m for m in elems["metrics"]), elems["metrics"]
    assert not any(m.endswith(" m") for m in elems["metrics"]), elems["metrics"]
    trimmed = _trim_clause_smart(claim_txt, elems, market="EN", hook_mode=False)
    assert "($172.7 m)" not in trimmed
    assert trimmed.count("$172.7") == 1

    # 3. Empirically calibrated docudrama TTS speeds
    assert DOCUDRAMA_SPEECH_RATES["KR"] == 5.0
    assert DOCUDRAMA_SPEECH_RATES["JA"] == 6.3
    assert DOCUDRAMA_SPEECH_RATES["VN"] == 3.75
    assert 2.0 <= DOCUDRAMA_SPEECH_RATES["EN"] <= 2.2


def test_systemic_s01_money_null_court_bucket_corroboration_and_bounds():
    """Verify null money_at_stake healing, court alleged routing, RSS multi-outlet corroboration, and shared bounds."""
    from app.services.story_provenance_engine import (
        classify_claim_provenance,
        corroborate_evidence_ledger,
        expected_qualifier_bucket,
        route_legal_qualifier,
    )
    from core.pacing_budgeter import estimate_script_speech_duration, get_market_unit_bounds
    from stages.s01_ideation import _coerce_money_at_stake_usd
    from stages.s03_script import _build_grounded_story_beats

    # 1. S01 null / string money_at_stake_usd coercion
    assert _coerce_money_at_stake_usd(None, 5000000.0) == 5000000.0
    assert _coerce_money_at_stake_usd("$22 trillion", 5000000.0) == 22e12
    assert _coerce_money_at_stake_usd(0, 5000000.0) == 5000000.0

    # 2. court + alleged never gets 'According to press reports,'
    assert expected_qualifier_bucket("alleged", source_type="court", verification_status="verified_primary") == "alleged_regulator"
    out_doj = route_legal_qualifier(
        "Against that enforcement framework, the Justice Department announced allegations involving unsupported codes.",
        legal_status="alleged",
        source_type="court",
        market="EN",
        verification_status="verified_primary",
    )
    assert "press reports" not in out_doj.lower(), out_doj

    # 3. Cross-outlet corroboration promotes multi-outlet reputable RSS claims without promoting RSS to verified_primary
    multi_rss = [
        classify_claim_provenance({
            "claim_id": "C001",
            "claim": "국토교통부가 2026년 11월 13일 최소보장제 시행을 공식 발표했다.",
            "source": "대한민국 정책브리핑",
            "source_url": "https://news.google.com/rss/articles/111",
        }, market="KR"),
        classify_claim_provenance({
            "claim_id": "C002",
            "claim": "연합뉴스 보도에 따르면 2026년 11월 13일 최소보장제 신청이 시작됐다.",
            "source": "연합뉴스",
            "source_url": "https://news.google.com/rss/articles/222",
        }, market="KR"),
        classify_claim_provenance({
            "claim_id": "C003",
            "claim": "익명 커뮤니티에서 완전히 별개의 미확인 추측이 제기됐다.",
            "source": "무명 블로그",
            "source_url": "https://news.google.com/rss/articles/333",
        }, market="KR"),
    ]
    corr = corroborate_evidence_ledger(multi_rss, market="KR")
    assert corr[0]["verification_status"] == "corroborated_secondary"
    assert corr[1]["verification_status"] == "corroborated_secondary"
    assert corr[2]["verification_status"] == "unverified_secondary"
    assert all(c["verification_status"] != "verified_primary" for c in corr)

    # Single-outlet or zero-overlap claims stay unverified_secondary (preserving S04 unverified gate)
    single_only = [
        classify_claim_provenance({
            "claim_id": "S001",
            "claim": "연합뉴스는 단독 500억원 규모 의혹을 전했다.",
            "source": "연합뉴스",
            "source_url": "https://news.google.com/rss/articles/444",
        }, market="KR"),
    ]
    assert corroborate_evidence_ledger(single_only, market="KR")[0]["verification_status"] == "unverified_secondary"

    # 4. Shared bounds & fallback Beat 1 <= 24s + total <= d_max guard
    assert get_market_unit_bounds("KR") == (750, 1550)
    assert get_market_unit_bounds("JA") == (900, 1950)
    assert get_market_unit_bounds("VN") == (640, 1125)
    assert get_market_unit_bounds("EN") == (460, 540)

    long_kr_claims = [
        {
            "claim_id": f"C{i:03d}",
            "claim": f"2026년 11월 {10+i}일 국토교통부와 관련 기관이 총 {i*12}조원 규모의 전세보증금 최소보장제 지원 대상 심사 및 회수 절차를 진행하고 있다는 공식 발표가 나왔다.",
            "verification_status": "corroborated_secondary",
            "source_type": "press",
            "legal_status": "alleged",
            "causal_role": "primary_catalyst" if i == 1 else "transmission_mechanism",
        }
        for i in range(1, 15)
    ]
    beats_fb = _build_grounded_story_beats(
        topic="전세사기 피해자 최소보장제",
        evidence_ledger=long_kr_claims,
        evidence_map={c["claim_id"]: c for c in long_kr_claims},
        market="KR",
        d_min=180.0,
        d_max=300.0,
        u_min=750,
        u_max=1550,
    )
    b1_sec = estimate_script_speech_duration([ln.text for ln in beats_fb[0][2]], market="KR", docudrama_tempo=True)["estimated_duration_sec"]
    tot_info = estimate_script_speech_duration([ln.text for _, _, lns in beats_fb for ln in lns], market="KR", docudrama_tempo=True)
    assert b1_sec <= 24.0, f"Fallback Beat 1 {b1_sec}s > 24.0s"
    assert tot_info["estimated_duration_sec"] <= 300.0, tot_info
    assert tot_info["spoken_units"] <= 1550, tot_info
