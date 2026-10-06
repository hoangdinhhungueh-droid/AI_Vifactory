# tests/test_story_engine_macro.py
# -*- coding: utf-8 -*-
"""Unit tests for B2 Story Engine Macro Architecture & Rule 128 Compliance.
Verifies:
  - Exact Vietnamese-exclusive character set against complete tone matrix
  - Immunity of Latin-1 loanwords (Beyoncé, Nestlé, José, cliché, São Paulo, Café, Château, Hôtel)
  - Canonical topic precedence across all branches and explicit fail-fast raises
  - Metadata loader fail-fast market validation on forbidden markets (VI, VN)
  - Deterministic multilingual spoken VO script reconciliation (EN, JP, KR)
  - Strict canonical market validation (EN, JP, KR only)
  - Auditor dynamic UTC date derivation
"""

import re
from datetime import datetime, timezone
import pytest

from app.services.story_engine_b2 import (
    SUPPORTED_MARKETS,
    normalize_market,
    validate_market_supported,
    load_task_metadata,
    _strip_market_prefix,
    is_valid_market_text,
    _resolve_canonical_topic,
    _reconcile_spoken_script,
)


def test_market_locale_validation_en_loanwords_and_rejections():
    """Test character-set fidelity for Market EN (Rule 128):
    1. Latin-1 loanwords (Beyoncé, Nestlé, José, cliché, São Paulo, Café, Château, Hôtel) MUST PASS.
    2. Out-of-locale scripts (Vietnamese diacritics, CJK, Hangul, Cyrillic) MUST BE REJECTED.
    """
    loanwords = [
        "Beyoncé World Tour",
        "Nestlé Water Monopoly",
        "San José Corruption Scandal",
        "The Cliché of Wall Street",
        "A Chic Café in Paris",
        "São Paulo Port Logistics",
        "The Luxury Château Empire",
        "Hôtel Ritz Paris Investigation",
    ]
    for word in loanwords:
        assert is_valid_market_text(word, "EN"), f"False rejection: '{word}' incorrectly rejected for EN market!"

    out_of_locale_samples = [
        "Kế hoạch Oakland bị bác bỏ",
        "Vụ án gian lận tài chính",
        "Điều tra nguồn tiền bí ẩn",
        "Sự sụp đổ của đế chế",
        "Người phụ trách vận hành",
        "Thủ đoạn lừa đảo tinh vi",
        "Đại gia bất động sản",
        "Bí mật đằng sau những con số",
        "港湾計画の白紙撤回",
        "오클랜드 항만 계획 무산",
    ]
    for sample in out_of_locale_samples:
        assert not is_valid_market_text(sample, "EN"), f"False acceptance: '{sample}' incorrectly accepted for EN market!"


def test_market_locale_validation_jp_and_kr():
    """Test character-set fidelity for Markets JP and KR (Rule 128):
    - JP accepts Kanji, Hiragana, Katakana, Latin brand names; rejects Hangul and Vietnamese diacritics.
    - KR accepts Hangul, Hanja, Latin brand names; rejects Japanese Kana and Vietnamese diacritics.
    """
    # JP Market validation
    assert is_valid_market_text("港湾計画の白紙撤回", "JP")
    assert is_valid_market_text("オークランド港湾計画", "JP")
    assert is_valid_market_text("Apple Vision Pro 日本発売", "JP")
    assert not is_valid_market_text("오클랜드 항만 계획 무산", "JP")
    assert not is_valid_market_text("Kế hoạch Oakland bị bác bỏ", "JP")

    # KR Market validation
    assert is_valid_market_text("항만 위원회는 비공개 회의를 소집했다", "KR")
    assert is_valid_market_text("오클랜드 항만 계획 무산", "KR")
    assert is_valid_market_text("삼성전자 반도체 혁신", "KR")
    assert is_valid_market_text("OpenAI GPT-5 한국 발표", "KR")
    assert not is_valid_market_text("オークランド港湾計画", "KR")
    assert not is_valid_market_text("Kế hoạch Oakland bị bác bỏ", "KR")


def test_canonical_topic_precedence_all_branches():
    """Test all branches of _resolve_canonical_topic:
    Branch 1: Out-of-locale topic + valid native key -> returns native key.
    Branch 2: Out-of-locale topic + empty native key -> raises ValueError.
    Branch 3: Out-of-locale topic + out-of-locale native key -> raises ValueError.
    Branch 4: Clean valid topic -> returns clean topic (primary editorial precedence).
    Branch 5: Empty raw_topic + valid native key -> returns native key.
    Branch 6: Empty raw_topic + empty native key + task_id -> returns task_id.
    Branch 7: All empty -> raises ValueError.
    """
    # Branch 1: Out-of-locale operator topic sanitized to native candidate
    assert _resolve_canonical_topic("[EN] Vụ án Oakland bị bác bỏ", "Oakland Plan Rejected", "EN_EP0008", market="EN") == "Oakland Plan Rejected"
    assert _resolve_canonical_topic("Kế hoạch Oakland bị bác bỏ", "Oakland Port Deal", "EN_EP0008", market="EN") == "Oakland Port Deal"
    assert _resolve_canonical_topic("Vụ án Livedoor", "ライブドア事件", "JP_EP0007", market="JP") == "ライブドア事件"

    # Branch 2: Out-of-locale operator topic with empty native candidate -> raises ValueError
    with pytest.raises(ValueError, match="Detected out-of-locale topic"):
        _resolve_canonical_topic("Vụ án Oakland bị bác bỏ", "", "EN_EP0008", market="EN")

    # Branch 3: Out-of-locale operator topic with out-of-locale native candidate -> raises ValueError
    with pytest.raises(ValueError, match="Detected out-of-locale topic"):
        _resolve_canonical_topic("Kế hoạch điều tra", "Vụ việc bí ẩn", "EN_EP0008", market="EN")

    # Branch 4: Clean valid topic has precedence over native candidate
    assert _resolve_canonical_topic("Oakland Plan Rejected", "oakland port controversy", "EN_EP0008", market="EN") == "Oakland Plan Rejected"
    assert _resolve_canonical_topic("[EN] Oakland Plan Rejected", "oakland port controversy", "EN_EP0008", market="EN") == "Oakland Plan Rejected"
    assert _resolve_canonical_topic("Beyoncé World Tour", "music tour", "EN_EP0001", market="EN") == "Beyoncé World Tour"
    assert _resolve_canonical_topic("港湾計画の白紙撤回", "港湾疑惑", "JP_EP0003", market="JP") == "港湾計画の白紙撤回"
    assert _resolve_canonical_topic("오클랜드 항만 계획 무산", "항만 비리", "KR_EP0005", market="KR") == "오클랜드 항만 계획 무산"

    # Branch 5: Empty raw_topic falls back to native candidate
    assert _resolve_canonical_topic("", "Oakland Port Authority", "EN_EP0008", market="EN") == "Oakland Port Authority"

    # Branch 6: Both empty falls back to task_id
    assert _resolve_canonical_topic("", "", "EN_EP0008_oakland", market="EN") == "EN_EP0008_oakland"

    # Branch 7: All sources empty raises ValueError (no ambiguous Untitled Episode)
    with pytest.raises(ValueError, match="Unable to resolve topic"):
        _resolve_canonical_topic("", "", "", market="EN")


def test_load_task_metadata_market_fail_fast():
    """Test that load_task_metadata enforces fail-fast on forbidden markets."""
    # Forbidden markets in task_id prefix raise ValueError immediately
    with pytest.raises(ValueError, match="Unsupported market"):
        load_task_metadata("VI_EP0001_oakland_deal")

    with pytest.raises(ValueError, match="Unsupported market"):
        load_task_metadata("VN_EP0002_hcmc_metro")

    # Canonical markets succeed and populate market correctly
    meta_en = load_task_metadata("EN_EP0008_oakland_plan_rejected")
    assert meta_en["market"] == "EN"

    meta_kr = load_task_metadata("KR_EP0005_chaebol_scandal")
    assert meta_kr["market"] == "KR"

    meta_jp = load_task_metadata("JP_EP0003_olympic_bid")
    assert meta_jp["market"] == "JP"


def test_reconcile_spoken_script_exact_strings():
    """Test deterministic multilingual reconciliation:
    - Sentences list is the single source of truth whenever present.
    - Korean joins with spaces (Hangul word spacing).
    - Japanese joins with empty string (no spaces).
    - English joins with spaces.
    - Empty sentences falls back to raw text.
    """
    # English
    en_sents = [
        {"sentence_id": "sent_001", "text": "The port commissioners met behind closed doors."},
        {"sentence_id": "sent_002", "text": "No public minutes were taken."},
    ]
    assert _reconcile_spoken_script(en_sents, "Mismatched raw text", market="EN") == (
        "The port commissioners met behind closed doors. No public minutes were taken."
    )

    # Japanese: no spaces between sentences
    jp_sents = [
        {"sentence_id": "sent_001", "text": "港湾委員会は密室で協議を行った。"},
        {"sentence_id": "sent_002", "text": "議事録は一切残されていない。"},
    ]
    assert _reconcile_spoken_script(jp_sents, "異なる生テキスト", market="JP") == (
        "港湾委員会は密室で協議を行った。議事録は一切残されていない。"
    )

    # Korean: space-separated Hangul sentences
    kr_sents = [
        {"sentence_id": "sent_001", "text": "항만 위원회는 비공개 회의를 소집했다."},
        {"sentence_id": "sent_002", "text": "공식 회의록은 작성되지 않았다."},
    ]
    assert _reconcile_spoken_script(kr_sents, "다른 원본 텍스트", market="KR") == (
        "항만 위원회는 비공개 회의를 소집했다. 공식 회의록은 작성되지 않았다."
    )

    # Fallback to raw text when sentences list is empty
    assert _reconcile_spoken_script([], "Fallback raw voiceover script.", market="EN") == "Fallback raw voiceover script."
    assert _reconcile_spoken_script(None, "Fallback raw text.", market="EN") == "Fallback raw text."


def test_validate_market_supported_fail_fast():
    """Test market normalization and fail-fast validation."""
    # Forbidden markets raise ValueError
    for bad in ["VN", "VI", "vn", "vi", "DE", "FR", "CN", "RU"]:
        with pytest.raises(ValueError, match="Unsupported market"):
            validate_market_supported(bad)

    # Canonical markets succeed and normalize
    assert validate_market_supported("EN") == "EN"
    assert validate_market_supported("en") == "EN"
    assert validate_market_supported("JP") == "JP"
    assert validate_market_supported("JA") == "JP"
    assert validate_market_supported("KR") == "KR"
    assert validate_market_supported("KO") == "KR"
    assert SUPPORTED_MARKETS == frozenset({"EN", "JP", "KR"})


def test_auditor_dynamic_utc_date_derivation():
    """Test that story_fact_auditor_b2 dynamically derives UTC month and year."""
    expected_month_year = datetime.now(timezone.utc).strftime("%B %Y")
    assert len(expected_month_year) > 4

    from app.services import story_fact_auditor_b2
    import inspect
    source = inspect.getsource(story_fact_auditor_b2.audit_story_facts_and_causality)
    assert 'datetime.now(timezone.utc).strftime("%B %Y")' in source
    assert 'September 2026' not in source
