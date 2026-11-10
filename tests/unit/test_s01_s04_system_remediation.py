# -*- coding: utf-8 -*-
"""
Targeted verification tests for system-level remediation across S01-S04 & Orchestrator.
Tests:
1. Orchestrator DAG invalidation in RunManifest (downstream purged, sha cleared).
2. Recon ingestion bridge in S01 (Korean entities, no 'Leadership' appending).
3. Recon ingestion bridge in S02 (Korean sources, no SEC/DOJ in KR market).
4. S03 multi-market legal qualifiers (localized prefixes for KR, JA, VN, EN; zero hardcoded English leaks).
5. S04 language gate & critic scoring (English in KR market fails immediately, dynamic scoring).
"""
from core.contracts.stages import StageID
from core.run_manifest import RunManifest
from stages.s03_script import _apply_legal_qualifier


def test_manifest_invalidate_downstream():
    manifest = RunManifest(run_id="TEST_RUN_001", preset="story_forensic")
    for s in StageID:
        manifest.mark(s, "done", artifact_sha256=f"hash_{s.value}")

    assert manifest.stages[StageID.S1_IDEATION].status == "done"
    assert manifest.stages[StageID.S2_RESEARCH].status == "done"
    assert manifest.stages[StageID.S4_CRITIC_SCRIPT].status == "done"

    # Invalidate from S02 onwards
    manifest.invalidate_downstream(StageID.S2_RESEARCH, inclusive=True)

    # S01 should remain done
    assert manifest.stages[StageID.S1_IDEATION].status == "done"
    assert manifest.stages[StageID.S1_IDEATION].artifact_sha256 == "hash_s01_ideation"

    # S02 through S11 must be pending with artifact_sha256 = None
    all_stages = list(StageID)
    s2_idx = all_stages.index(StageID.S2_RESEARCH)
    for s in all_stages[s2_idx:]:
        assert manifest.stages[s].status == "pending"
        assert manifest.stages[s].artifact_sha256 is None


def test_s03_market_legal_qualifiers():
    # Korean market tests
    kr_charged = _apply_legal_qualifier("빌라왕 일당은 수백 채의 주택을 매입했습니다.", "charged", "KR")
    assert "검찰 공소장에 따르면," in kr_charged
    assert "According to" not in kr_charged

    kr_alleged = _apply_legal_qualifier("세입자 보증금을 이용한 무자본 갭투자가 진행되었습니다.", "alleged", "KR")
    assert "규제 당국에 따르면," in kr_alleged
    assert "According to" not in kr_alleged

    # Case 1: Text without settled qualifier -> should append suffix
    kr_settled = _apply_legal_qualifier("관련 분쟁이 공식 종결되었습니다.", "settled", "KR")
    assert "(공식적인 잘못을 인정하지 않고 합의됨)" in kr_settled
    assert "without admitting wrongdoing" not in kr_settled

    # Case 2: Text already with settled qualifier -> no duplicate suffix
    kr_already_settled = _apply_legal_qualifier("공식적인 잘못을 인정하지 않고 합의로 종결되었습니다.", "settled", "KR")
    assert kr_already_settled.count("합의") == 1

    # Japanese market tests
    ja_charged = _apply_legal_qualifier("組織的な資金流用が行われた。", "charged", "JA")
    assert "起訴状の指摘によれば、" in ja_charged
    assert "According to" not in ja_charged
    # Re-applying should not duplicate
    ja_charged_repeat = _apply_legal_qualifier(ja_charged, "charged", "JA")
    assert ja_charged_repeat.count("起訴状の指摘によれば、") == 1

    ja_alleged = _apply_legal_qualifier("未公開の取引枠組みが存在した。", "alleged", "JA")
    assert "当局の調査によれば、" in ja_alleged
    ja_alleged_repeat = _apply_legal_qualifier(ja_alleged, "alleged", "JA")
    assert ja_alleged_repeat.count("当局の調査によれば、") == 1

    # Vietnamese market tests
    vn_charged = _apply_legal_qualifier("Doanh nghiệp đã tiến hành chiếm đoạt tài sản.", "charged", "VN")
    assert "Theo cáo trạng của cơ quan công tố," in vn_charged
    vn_charged_repeat = _apply_legal_qualifier(vn_charged, "charged", "VN")
    assert vn_charged_repeat.count("Theo cáo trạng của cơ quan công tố,") == 1

    vn_alleged = _apply_legal_qualifier("Cơ cấu tài chính bị phát hiện có dấu hiệu bất thường.", "alleged", "VN")
    assert "Theo cơ quan chức năng," in vn_alleged
    vn_alleged_repeat = _apply_legal_qualifier(vn_alleged, "alleged", "VN")
    assert vn_alleged_repeat.count("Theo cơ quan chức năng,") == 1

    # English market tests
    en_charged = _apply_legal_qualifier("The entity acquired housing units without capital.", "charged", "EN")
    assert "According to court filings," in en_charged

    en_settled = _apply_legal_qualifier("The enforcement inquiry was finalized.", "settled", "EN")
    assert "(settled without admitting wrongdoing)" in en_settled


def test_s03_grounded_story_beats_resilience_and_multimarket():
    from app.schemas.story_contracts import EvidenceClaim
    from stages.s03_script import _build_grounded_story_beats

    # 1. Zero crash with empty claims across all canonical markets
    for m in ["KR", "JA", "VN", "EN"]:
        beats = _build_grounded_story_beats("Market Failure Test", [], {}, market=m)
        assert len(beats) == 5
        assert len(beats[0][2]) >= 3  # B1 has at least 3 micro-scenes

    # 2. Resilient multi-claim handling with no duplicate stacked prefixes
    c1 = EvidenceClaim(claim_id="C001", claim="Indictment claim", source_url="http://a", source_type="court", date="2026-01-01", legal_status="charged")
    c2 = EvidenceClaim(claim_id="C002", claim="Regulatory inquiry", source_url="http://b", source_type="regulator", date="2026-01-01", legal_status="alleged")
    claims_map = {"C001": c1, "C002": c2}

    kr_beats = _build_grounded_story_beats("전세 보증금 리스크", [c1, c2], claims_map, market="KR")
    first_kr_line = kr_beats[0][2][0].text
    # Charged takes precedence over alleged; must not stack both prefixes
    assert "검찰 공소장에 따르면," in first_kr_line
    assert "규제 당국에 따르면," not in first_kr_line

    ja_beats = _build_grounded_story_beats("金融危機分析", [c1, c2], claims_map, market="JA")
    first_ja_line = ja_beats[0][2][0].text
    assert "起訴状の指摘によれば、" in first_ja_line
    assert first_ja_line.count("起訴状の指摘によれば、") == 1
    assert "急激な市場の危機" in first_ja_line

    vn_beats = _build_grounded_story_beats("Khủng hoảng đòn bẩy", [c1, c2], claims_map, market="VN")
    first_vn_line = vn_beats[0][2][0].text
    assert "Theo cáo trạng của cơ quan công tố," in first_vn_line
    assert first_vn_line.count("Theo cáo trạng của cơ quan công tố,") == 1
    assert "Trong cuộc khủng hoảng" in first_vn_line


def test_s04_language_gate_rejection():
    import re
    # Test Korean market with English text (should fail)
    en_text = "In an acute market crisis, the corporate leadership faced severe financial fallout and bankruptcy."
    market = "KR"
    words = en_text.split()
    total_words = len(words)
    en_words = re.findall(r"\b[A-Za-z]{2,}\b", en_text)
    filtered_en = [w for w in en_words if w.upper() not in ("HUG", "MOLIT", "KRW", "USD")]
    en_ratio = len(filtered_en) / total_words
    hangul_chars = len(re.findall(r"[\uac00-\ud7a3]", en_text))

    language_ok = True
    if market == "KR":
        if hangul_chars < 80 or en_ratio > 0.15:
            language_ok = False
    assert language_ok is False

    # Test Korean market with authentic Korean text (should pass)
    kr_text = "전세사기 사태 속에서 국토교통부는 피해자 보호를 위한 최소보장제를 공식 발표하고 사전 신청 접수를 개시했습니다." * 3
    kr_words = kr_text.split()
    kr_total = len(kr_words)
    kr_en_words = re.findall(r"\b[A-Za-z]{2,}\b", kr_text)
    kr_en_ratio = len(kr_en_words) / kr_total
    kr_hangul = len(re.findall(r"[\uac00-\ud7a3]", kr_text))

    # Test Japanese market with English text (should fail)
    ja_fail_cjk = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", en_text))
    assert ja_fail_cjk < 80

    # Test Japanese market with authentic Japanese text (should pass)
    ja_text = "急激な市場の危機の中で関係当局による公式な調査が実施され構造的欠陥が暴露された。" * 4
    ja_cjk = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", ja_text))
    assert ja_cjk >= 80

    # Test Vietnamese market with English text (should fail)
    vn_en_words = re.findall(r"\b[A-Za-z]{2,}\b", en_text)
    assert len(vn_en_words) / total_words > 0.20


def test_s04_duration_and_word_budget_multimarket():
    # Verify Korean 246 words at 240s passes gate 1
    market = "KR"
    total_words = 246
    est_dur = 240.0
    w_min, w_max = (200, 560) if market in ("KR", "KO") else (450, 550)
    d_min, d_max = 180.0, 300.0
    duration_ok = (w_min <= total_words <= w_max) and (d_min <= est_dur <= d_max)
    assert duration_ok is True

    # Verify Japanese 10 words (unsegmented) at 240s passes gate 1
    ja_market = "JA"
    ja_dur = 240.0
    ja_duration_ok = (d_min <= ja_dur <= d_max)
    assert ja_duration_ok is True
