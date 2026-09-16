"""Unit tests for app/services/text_metrics.py.
Verifies multi-lingual script length, character counts, and narration pacing estimation.
"""
import pytest
from app.services.text_metrics import (
    is_cjk_market,
    detect_language,
    get_clean_character_count,
    get_word_count,
    get_script_units,
    get_unit_name,
    validate_script_length,
    estimate_narration_seconds
)


def test_is_cjk_market():
    assert is_cjk_market("JP") is True
    assert is_cjk_market("ja") is True
    assert is_cjk_market("KR") is True
    assert is_cjk_market("ko") is True
    assert is_cjk_market("ZH") is True
    assert is_cjk_market("EN") is False
    assert is_cjk_market("VI") is False
    assert is_cjk_market("") is False


def test_detect_language():
    assert detect_language("", "JP") == "JP"
    assert detect_language("", "KR") == "KR"
    assert detect_language("", "EN") == "EN"

    # From text content
    jp_sample = "ソニー生命に金融庁が立ち入り検査着手。金銭不祥事の真因を究明へ。"
    assert detect_language(jp_sample) == "JP"

    kr_sample = "금융감독원이 전면 조사를 개시했습니다. 자금 횡령의 구조적 원인을 파악합니다."
    assert detect_language(kr_sample) == "KR"

    en_sample = "The investigation revealed catastrophic internal controls failure at Sony Life."
    assert detect_language(en_sample) == "EN"


def test_japanese_character_counting():
    # Japanese script without spaces
    jp_text = "これはテストです。" * 300  # 9 chars * 300 = 2700 chars
    clean_chars = get_clean_character_count(jp_text)
    assert clean_chars == 2700

    # .split() would have failed completely on Japanese text
    assert len(jp_text.split()) == 1

    # get_script_units must return character count for JP
    assert get_script_units(jp_text, "JP") == 2700
    assert get_unit_name("JP") == "chars"

    val = validate_script_length(jp_text, "JP", min_cjk_chars=2500)
    assert val["valid"] is True
    assert val["units"] == 2700
    assert val["unit_name"] == "chars"


def test_korean_syllables_counting():
    kr_text = "이것은 테스트 문장입니다. " * 200  # ~3000 Hangul characters
    units = get_script_units(kr_text, "KR")
    assert units > 2000
    val = validate_script_length(kr_text, "KR", min_kr_syllables=2000)
    assert val["valid"] is True


def test_english_word_counting():
    en_text = "word " * 1500
    assert get_script_units(en_text, "EN") == 1500
    assert get_unit_name("EN") == "words"
    val = validate_script_length(en_text, "EN", min_en_words=1200)
    assert val["valid"] is True


def test_estimate_narration_seconds():
    en_text = "word " * 290  # ~2 minutes at 145 wpm
    sec_en = estimate_narration_seconds(en_text, "EN")
    assert 110 <= sec_en <= 130

    jp_text = "あ" * 720  # ~2 minutes at 360 chars/min
    sec_jp = estimate_narration_seconds(jp_text, "JP")
    assert 110 <= sec_jp <= 130
