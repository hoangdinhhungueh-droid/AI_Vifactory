# tests/test_text_to_number_parser.py
"""Unit tests for text_to_number_parser.py.
Verifies parsing of spoken numbers, currencies, percentages, and zero-mock behavior.
"""
import pytest
from app.services.text_to_number_parser import parse_spoken_number, _words_to_number


def test_words_to_number():
    assert _words_to_number("ten") == 10
    assert _words_to_number("five hundred thirty-eight") == 538
    assert _words_to_number("three hundred") == 300
    assert _words_to_number("five hundred") == 500
    assert _words_to_number("one point two") == 1.2
    assert _words_to_number("one-point-two") == 1.2
    assert _words_to_number("forty-one point eight") == 41.8


def test_parse_spoken_number_real_daycare_sentences():
    # Scene 1: "Ten million taxpayer dollars allegedly vanished through childcare claims in San Diego."
    p1 = parse_spoken_number("Ten million taxpayer dollars allegedly vanished through childcare claims in San Diego.")
    assert p1 is not None
    assert p1.display_value == 10.0
    assert p1.unit == "M"
    assert p1.prefix == "$"
    assert p1.formatted == "$10M"
    assert p1.trend == "down"

    # Scene 40: "Court documents describe payments ranging from five hundred thirty-eight thousand to one-point-two million dollars."
    p40 = parse_spoken_number("Court documents describe payments ranging from five hundred thirty-eight thousand to one-point-two million dollars.")
    assert p40 is not None
    # Matches the first or dominant metric
    assert p40.unit in ["K", "M"]
    assert p40.prefix == "$"

    # Scene 41: "Prosecutors allege Abdulrahman Alawad received more than three hundred thousand dollars during twenty twenty-five."
    p41 = parse_spoken_number("Prosecutors allege Abdulrahman Alawad received more than three hundred thousand dollars during twenty twenty-five.")
    assert p41 is not None
    assert p41.display_value == 300.0
    assert p41.unit == "K"
    assert p41.prefix == "$"
    assert p41.formatted == "$300K"

    # Scene 105: "The Justice Department also cited a maximum fine of five hundred thousand dollars."
    p105 = parse_spoken_number("The Justice Department also cited a maximum fine of five hundred thousand dollars.")
    assert p105 is not None
    assert p105.display_value == 500.0
    assert p105.unit == "K"
    assert p105.prefix == "$"
    assert p105.formatted == "$500K"


def test_parse_spoken_number_alphanumeric_and_symbols():
    p_alpha = parse_spoken_number("The fund lost $41.8M in under twenty minutes.")
    assert p_alpha is not None
    assert p_alpha.display_value == 41.8
    assert p_alpha.unit == "M"
    assert p_alpha.prefix == "$"
    assert p_alpha.formatted == "$41.8M"

    p_pct = parse_spoken_number("The margin collapsed by -52% within two quarters.")
    assert p_pct is not None
    assert p_pct.display_value == 52.0
    assert p_pct.unit == "%"
    assert p_pct.formatted == "-52%"

    p_vn = parse_spoken_number("Khoản thất thoát ước tính lên tới 500 tỷ đồng.")
    assert p_vn is not None
    assert p_vn.display_value == 500.0
    assert p_vn.unit == "TỶ"
    assert "ĐỒNG" in p_vn.suffix

    p_kr = parse_spoken_number("피해액은 350만 원에 달했습니다.")
    assert p_kr is not None
    assert p_kr.display_value == 350.0
    assert p_kr.unit == "만"
    assert "원" in p_kr.suffix


def test_parse_spoken_number_zero_mock_fallback():
    # Sentence with no numbers must return None (Rule 118: Zero-Mock)
    p_none = parse_spoken_number("This was not a market collapse flashing across financial screens or stock exchanges.")
    assert p_none is None

    p_ordinary = parse_spoken_number("The detectives arrived at the daycare center early in the morning.")
    assert p_ordinary is None
