#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_visual_taxonomy_and_regex.py

Focused tests for Visual Taxonomy Loading, Schema Validation, Cache Invalidation,
and CJK / English Regex Boundary Matching (Rule 128, Rule 132 & Boss Round 8 Item 19).
"""

import json
from pathlib import Path
import re
import pytest

from app.services.unified_vox_director import (
    _load_visual_taxonomy,
    _reset_taxonomy_cache,
    generate_topic_anchored_roster,
)


VALID_FG_ITEM = {
    "title": "T1",
    "description": "D1",
    "beats": [1, 2],
    "role": "Lead",
    "type": "character",
    "keywords": ["test"],
}

VALID_BG_ITEM = {
    "title": "B1",
    "description": "D1",
    "beats": [1, 2],
}


def test_production_visual_taxonomy_structure_and_schema():
    """Verifies that the canonical visual_rosters.json satisfies all required structural schemas."""
    _reset_taxonomy_cache()
    tax = _load_visual_taxonomy()
    assert isinstance(tax, dict), "Taxonomy root must be a dict"
    assert "domains" in tax and isinstance(tax["domains"], dict)
    assert len(tax["domains"]) >= 1, "Expected at least 1 domain defined"

    for dom_name, dom_data in tax["domains"].items():
        assert "keywords_cjk" in dom_data, f"Domain {dom_name} missing keywords_cjk"
        assert isinstance(dom_data["keywords_cjk"], list), f"keywords_cjk in {dom_name} must be a list"
        assert all(isinstance(k, str) and k.strip() for k in dom_data["keywords_cjk"]), f"keywords_cjk in {dom_name} must be non-empty strings"
        assert "keywords_en_regex" in dom_data, f"Domain {dom_name} missing keywords_en_regex"
        assert "_compiled_en_regex" in dom_data, f"Domain {dom_name} missing pre-compiled regex"
        assert isinstance(dom_data["_compiled_en_regex"], re.Pattern)
        assert "markets" in dom_data, f"Domain {dom_name} missing markets mapping"

        for mkt_name, mkt_data in dom_data["markets"].items():
            assert "bg_roster" in mkt_data, f"Market {mkt_name} missing bg_roster in {dom_name}"
            assert "fg_roster" in mkt_data, f"Market {mkt_name} missing fg_roster in {dom_name}"
            assert len(mkt_data["bg_roster"]) >= 2, f"Expected >= 2 BGs in {dom_name}/{mkt_name}"
            assert len(mkt_data["fg_roster"]) >= 2, f"Expected >= 2 FGs in {dom_name}/{mkt_name}"

            for bg_k, bg_v in mkt_data["bg_roster"].items():
                assert "title" in bg_v and bg_v["title"], f"BG {bg_k} missing title"
                assert "description" in bg_v and bg_v["description"], f"BG {bg_k} missing description"
                assert "beats" in bg_v and isinstance(bg_v["beats"], list), f"BG {bg_k} missing beats list"
                assert all(isinstance(b, int) and not isinstance(b, bool) and 1 <= b <= 5 for b in bg_v["beats"])

            for fg_k, fg_v in mkt_data["fg_roster"].items():
                assert "title" in fg_v and fg_v["title"], f"FG {fg_k} missing title"
                assert "description" in fg_v and fg_v["description"], f"FG {fg_k} missing description"
                assert "beats" in fg_v and isinstance(fg_v["beats"], list), f"FG {fg_k} missing beats list"
                assert all(isinstance(b, int) and not isinstance(b, bool) and 1 <= b <= 5 for b in fg_v["beats"])


def test_taxonomy_missing_file_fails_closed(tmp_path: Path):
    """Rule 128: Asserts FileNotFoundError when taxonomy file does not exist."""
    missing_path = tmp_path / "non_existent_rosters.json"
    with pytest.raises(FileNotFoundError) as exc_info:
        _load_visual_taxonomy(custom_path=missing_path)
    assert "visual taxonomy file not found" in str(exc_info.value)


def test_taxonomy_malformed_json_fails_closed(tmp_path: Path):
    """Rule 128: Asserts JSONDecodeError when taxonomy file contains malformed syntax."""
    bad_json = tmp_path / "corrupted.json"
    bad_json.write_text("{ unquoted_key: missing_quotes, }", encoding="utf-8")
    with pytest.raises(Exception):
        _load_visual_taxonomy(custom_path=bad_json)


def test_taxonomy_empty_or_non_dict_fails_closed(tmp_path: Path):
    """Rule 128: Asserts ValueError when taxonomy root is empty or non-dict."""
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        _load_visual_taxonomy(custom_path=empty_json)
    assert "Taxonomy root must be a non-empty JSON object" in str(exc_info.value)

    list_json = tmp_path / "list.json"
    list_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        _load_visual_taxonomy(custom_path=list_json)


def test_taxonomy_missing_domains_or_markets_fails_closed(tmp_path: Path):
    """Rule 128: Asserts ValueError when required 'domains' or 'markets' mappings are missing."""
    no_domains = tmp_path / "no_domains.json"
    no_domains.write_text('{"version": 1}', encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        _load_visual_taxonomy(custom_path=no_domains)
    assert "must contain a non-empty 'domains' mapping" in str(exc_info.value)

    no_markets = tmp_path / "no_markets.json"
    no_markets.write_text('{"domains": {"healthcare": {"keywords_cjk": ["a"], "keywords_en_regex": "a"}}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        _load_visual_taxonomy(custom_path=no_markets)
    assert "missing non-empty 'markets' mapping" in str(exc_info.value)


def _make_tax(dom_name="test", cjk=None, regex="a", markets=None):
    if cjk is None:
        cjk = ["a"]
    if markets is None:
        markets = {
            "EN": {
                "bg_roster": {"bg_1": VALID_BG_ITEM},
                "fg_roster": {"fg_1": VALID_FG_ITEM},
            }
        }
    return {
        "domains": {
            dom_name: {
                "keywords_cjk": cjk,
                "keywords_en_regex": regex,
                "markets": markets,
            }
        }
    }


def test_taxonomy_malformed_nested_structures_fails_closed(tmp_path: Path):
    """Boss Round 8 Item 19: Tests malformed markets, missing/empty rosters, and bad beat arrays."""
    # 1. Missing bg_roster
    no_bg = tmp_path / "no_bg.json"
    no_bg.write_text(json.dumps(_make_tax(markets={"EN": {"fg_roster": {"fg_1": VALID_FG_ITEM}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=no_bg)
    assert "missing non-empty 'bg_roster' dict" in str(exc.value)

    # 2. Empty bg_roster
    empty_bg = tmp_path / "empty_bg.json"
    empty_bg.write_text(json.dumps(_make_tax(markets={"EN": {"bg_roster": {}, "fg_roster": {"fg_1": VALID_FG_ITEM}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=empty_bg)
    assert "missing non-empty 'bg_roster' dict" in str(exc.value)

    # 3. Missing fg_roster
    no_fg = tmp_path / "no_fg.json"
    no_fg.write_text(json.dumps(_make_tax(markets={"EN": {"bg_roster": {"bg_1": VALID_BG_ITEM}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=no_fg)
    assert "missing non-empty 'fg_roster' dict" in str(exc.value)

    # 4. Empty fg_roster
    empty_fg = tmp_path / "empty_fg.json"
    empty_fg.write_text(json.dumps(_make_tax(markets={"EN": {"bg_roster": {"bg_1": VALID_BG_ITEM}, "fg_roster": {}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=empty_fg)
    assert "missing non-empty 'fg_roster' dict" in str(exc.value)

    # 5. Invalid beat arrays (empty beats, non-int beats, boolean beats, out-of-range beats)
    empty_beats = tmp_path / "empty_beats.json"
    empty_beats.write_text(json.dumps(_make_tax(markets={"EN": {"bg_roster": {"bg_1": {"title": "T", "description": "D", "beats": []}}, "fg_roster": {"fg_1": VALID_FG_ITEM}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=empty_beats)
    assert "invalid 'beats' array" in str(exc.value)

    bool_beats = tmp_path / "bool_beats.json"
    # In JSON, true/false are booleans
    bool_beats.write_text('{"domains": {"test": {"keywords_cjk": ["a"], "keywords_en_regex": "a", "markets": {"EN": {"bg_roster": {"bg_1": {"title": "T", "description": "D", "beats": [true, 2]}}, "fg_roster": {"fg_1": {"title": "T1", "description": "D1", "beats": [1, 2], "role": "Lead", "type": "character", "keywords": ["test"]}}}}}}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=bool_beats)
    assert "invalid 'beats' array" in str(exc.value)

    str_beats = tmp_path / "str_beats.json"
    str_beats.write_text(json.dumps(_make_tax(markets={"EN": {"bg_roster": {"bg_1": {"title": "T", "description": "D", "beats": ["one"]}}, "fg_roster": {"fg_1": VALID_FG_ITEM}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=str_beats)
    assert "invalid 'beats' array" in str(exc.value)

    out_of_range_beats = tmp_path / "oor_beats.json"
    out_of_range_beats.write_text(json.dumps(_make_tax(markets={"EN": {"bg_roster": {"bg_1": {"title": "T", "description": "D", "beats": [0, 6]}}, "fg_roster": {"fg_1": VALID_FG_ITEM}}})), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=out_of_range_beats)
    assert "invalid 'beats' array" in str(exc.value)


def test_taxonomy_domain_level_schema_fails_closed(tmp_path: Path):
    """Boss Round 8 Item 19: Tests malformed domains (non-dict, invalid CJK elements, invalid regexes)."""
    # 1. Domain not a dict
    bad_dom = tmp_path / "bad_dom.json"
    bad_dom.write_text('{"domains": {"healthcare": "not_a_dict"}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=bad_dom)
    assert "must be a dict" in str(exc.value)

    # 2. Missing keywords_cjk
    no_cjk = tmp_path / "no_cjk.json"
    no_cjk.write_text('{"domains": {"healthcare": {"keywords_en_regex": "regex", "markets": {"EN": {}}}}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=no_cjk)
    assert "missing non-empty 'keywords_cjk' list" in str(exc.value)

    # 3. Invalid keywords_cjk elements (empty string or non-string)
    bad_cjk_item = tmp_path / "bad_cjk_item.json"
    bad_cjk_item.write_text('{"domains": {"healthcare": {"keywords_cjk": ["valid", ""], "keywords_en_regex": "regex", "markets": {"EN": {}}}}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=bad_cjk_item)
    assert "contains invalid element" in str(exc.value)

    # 4. Missing keywords_en_regex
    no_regex = tmp_path / "no_regex.json"
    no_regex.write_text('{"domains": {"healthcare": {"keywords_cjk": ["a"], "markets": {"EN": {}}}}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=no_regex)
    assert "missing valid 'keywords_en_regex' string" in str(exc.value)

    # 5. Invalid regex syntax in keywords_en_regex
    bad_regex = tmp_path / "bad_regex.json"
    bad_regex.write_text('{"domains": {"healthcare": {"keywords_cjk": ["a"], "keywords_en_regex": "(unclosed[regex", "markets": {"EN": {}}}}}', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_visual_taxonomy(custom_path=bad_regex)
    assert "invalid 'keywords_en_regex'" in str(exc.value)


def test_taxonomy_precompiled_regex():
    """Boss Round 8 Item 19: Verifies that keywords_en_regex is pre-compiled during loading."""
    _reset_taxonomy_cache()
    tax = _load_visual_taxonomy()
    assert "_compiled_en_regex" in tax["domains"]["healthcare"]
    assert isinstance(tax["domains"]["healthcare"]["_compiled_en_regex"], re.Pattern)


def test_consumer_fails_closed_when_taxonomy_domain_missing(tmp_path: Path):
    """Boss Round 8 Item 19: Verifies that consumer fails closed when domain is not in taxonomy (no embedded defaults)."""
    # Create taxonomy with ONLY domain 'macro_energy'
    energy_tax = tmp_path / "energy_tax.json"
    energy_tax.write_text(json.dumps({
        "domains": {
            "macro_energy": {
                "keywords_cjk": ["石油", "天然ガス"],
                "keywords_en_regex": r"(petroleum|oil|gas)",
                "markets": {
                    "JP": {
                        "bg_roster": {"bg_refinery": VALID_BG_ITEM},
                        "fg_roster": {"fg_inspector": VALID_FG_ITEM},
                    }
                }
            }
        }
    }), encoding="utf-8")

    _reset_taxonomy_cache()
    _load_visual_taxonomy(custom_path=energy_tax)

    # 1. Consumer explicitly requesting domain 'healthcare' on energy-only taxonomy must fail-closed
    with pytest.raises(ValueError) as exc:
        generate_topic_anchored_roster(
            topic="医療機関 倒産 過去最多59件",
            market="JP",
            key_metrics=[],
            claims=[],
            domain="healthcare",
        )
    assert "Requested domain 'healthcare' is not configured in visual taxonomy" in str(exc.value)

    # 2. Consumer requiring 'healthcare' during taxonomy loading must fail-closed
    with pytest.raises(ValueError) as exc_load:
        _load_visual_taxonomy(custom_path=energy_tax, required_domains=["healthcare"])
    assert "Taxonomy missing required domain 'healthcare'" in str(exc_load.value)

    _reset_taxonomy_cache()


def test_cjk_keyword_boundaries_and_near_misses():
    """Rule 128 & Boss Item 2: Verifies CJK keyword matching precision and false-positive resistance."""
    _reset_taxonomy_cache()
    tax = _load_visual_taxonomy()
    cjk_keywords = tax["domains"]["healthcare"]["keywords_cjk"]

    # True positives (Japanese healthcare topics)
    assert any(kw in "医療機関 倒産 過去最多59件" for kw in cjk_keywords)
    assert any(kw in "大手総合病院の病床削減計画" for kw in cjk_keywords)
    assert any(kw in "地方クリニックの閉院問題" for kw in cjk_keywords)
    assert any(kw in "中医協における診療報酬改定の議論" for kw in cjk_keywords)
    assert any(kw in "歯科診療所の経営悪化" for kw in cjk_keywords)

    # True negatives / near-miss non-matches (unrelated topics containing common particles)
    unrelated_macro = "日本国債の利回り急騰と日銀の市場オペレーション"
    assert not any(kw in unrelated_macro for kw in cjk_keywords)

    unrelated_tech = "人工知能半導体の輸出規制強化とサプライチェーン分断"
    assert not any(kw in unrelated_tech for kw in cjk_keywords)

    unrelated_consumer = "電気自動車の普及停滞とバッテリー生産設備過剰"
    assert not any(kw in unrelated_consumer for kw in cjk_keywords)


def test_english_regex_boundaries_prefixes_slugs_and_suffixes():
    """Rule 128 & Boss Item 2: Verifies English regex boundary semantics, slug tolerance, and suffix isolation."""
    _reset_taxonomy_cache()
    tax = _load_visual_taxonomy()
    compiled_re = tax["domains"]["healthcare"]["_compiled_en_regex"]

    # 1. Exact base matches
    assert compiled_re.search("hospital capacity crisis")
    assert compiled_re.search("rural clinic closure")
    assert compiled_re.search("doctor shortage report")
    assert compiled_re.search("prescription drug price surge")
    assert compiled_re.search("medicare reimbursement cut")

    # 2. Slug and hyphenated boundary tolerance
    assert compiled_re.search("urgent-care-clinic-insolvency")
    assert compiled_re.search("private_hospital_chain_debt")
    assert compiled_re.search("sub-clinic-network")
    assert compiled_re.search("pre-clinical trial failure")

    # 3. True negative near-misses
    assert not compiled_re.search("macroeconomic cyclical debt rollover")
    assert not compiled_re.search("antelope national park conservation")
    assert not compiled_re.search("telephonic customer service center")
    assert not compiled_re.search("technological semiconductor wafer fabrication")


def test_generate_topic_anchored_roster_end_to_end_healthcare():
    """Verifies that generate_topic_anchored_roster selects correct healthcare taxonomy for JP."""
    _reset_taxonomy_cache()
    bg_roster, fg_roster = generate_topic_anchored_roster(
        topic="医療機関 倒産 過去最多59件",
        market="JP",
        key_metrics=["過去最多59件の医療機関倒産"],
        claims=["診療報酬改定", "物価高騰"]
    )
    assert isinstance(bg_roster, dict)
    assert isinstance(fg_roster, dict)
    assert "bg_clinic_waiting_room" in bg_roster
    assert "fg_character_clinic_director_doctor" in fg_roster
    assert bg_roster["bg_clinic_waiting_room"]["beats"] == [1, 2]
    assert fg_roster["fg_character_clinic_director_doctor"]["beats"] == [1, 2, 4]
