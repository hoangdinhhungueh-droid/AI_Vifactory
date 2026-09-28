"""
tests/test_quant_profile.py — UNIT TESTS FOR DYNAMIC QUANTITATIVE PROFILE EXTRACTOR
Rule 128 (Anti-Semantic Bias) & Multilingual Zero-Mock Compliance.
"""
import pytest
from app.services.quant_profile import (
    parse_numbers,
    extract_episode_quantitative_profile,
    ValueKind,
    ProfileStatus,
)


def test_multilingual_number_parsing():
    # EN Percentage & Multiplier
    en_res = parse_numbers("Market dominance reached 75% while competitor was 15 times smaller.")
    assert len(en_res) == 2
    assert en_res[0].kind == ValueKind.PERCENT and en_res[0].value == 75.0
    assert en_res[1].kind == ValueKind.MULTIPLIER and en_res[1].value == 15.0

    # JP Exceedance & Measurement
    jp_res = parse_numbers("基準値の24.3倍の二酸化硫黄、実測値4,860 mg/kgが検出された。")
    assert len(jp_res) >= 2
    assert jp_res[0].kind == ValueKind.MULTIPLIER and jp_res[0].value == 24.3
    assert jp_res[1].kind == ValueKind.MEASUREMENT and jp_res[1].value == 4860.0
    assert jp_res[1].unit == "mg/kg"

    # KR Currency & Multiplier
    kr_res = parse_numbers("회계 감사에서 50억원의 부실과 기준의 24배 초과가 드러났다.")
    assert len(kr_res) == 2
    assert kr_res[0].kind == ValueKind.CURRENCY and kr_res[0].value == 5e9
    assert kr_res[0].unit == "KRW"
    assert kr_res[1].kind == ValueKind.MULTIPLIER and kr_res[1].value == 24.0

    # VN Currency & Multiplier
    vn_res = parse_numbers("Công ty bị phạt 500 tỷ đồng, gấp 24 lần lợi nhuận năm trước.")
    assert len(vn_res) == 2
    assert vn_res[0].kind == ValueKind.CURRENCY and vn_res[0].value == 5e11
    assert vn_res[0].unit == "VND"
    assert vn_res[1].kind == ValueKind.MULTIPLIER and vn_res[1].value == 24.0


def test_structured_grounding_table_extraction():
    intel = {
        "grounding_table": [
            {
                "parameter": "Ad Tech Market Share",
                "detected_value": 75.0,
                "baseline_value": 20.0,
                "unit": "%",
                "standard_name": "Sherman Act §2 Competitive Benchmark (20%)",
                "secondary_baseline_value": 10.0,
                "secondary_standard_name": "EU DMA Gatekeeper Threshold (10%)",
                "source_citation": "DOJ v. Google Trial Exhibit PX-0012",
                "is_primary": True
            }
        ]
    }
    profile = extract_episode_quantitative_profile(intel, "", "EN")
    assert profile.status == ProfileStatus.OK
    assert profile.ratio == 3.75
    assert profile.secondary_ratio == 7.5
    assert profile.parameter == "Ad Tech Market Share"
    assert profile.value_kind == ValueKind.PERCENT


def test_insufficient_data_returns_cleanly_without_mock_fallbacks():
    profile = extract_episode_quantitative_profile({}, "The investigation proceeded into the night.", "EN")
    assert profile.status == ProfileStatus.INSUFFICIENT_DATA
    assert profile.ratio is None
    assert profile.detected_value is None
    assert profile.baseline_value is None
