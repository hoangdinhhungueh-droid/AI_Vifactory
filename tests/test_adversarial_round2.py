import sys, os
sys.path.insert(0, "/root/video_factory")
# tests/test_adversarial_round2.py
"""
Adversarial test suite for Review Round 2.
Attacks edge cases, boundary conditions, malformed inputs, large numbers,
and end-to-end data pipeline integrity across B1 -> B2 -> B10.
"""
import pytest
import json
import re

from app.services.virality_score import (
    is_clean_search_query,
    _parse_growth_value,
    _parse_related_queries_df,
    extract_clean_breakout_queries,
    extract_clean_rising_queries,
)
from app.services.seo_metadata import (
    build_seo_tags,
    build_hashtags,
    validate_hashtags,
    build_seo_payload,
)
from app.services.seo_autogen_b10 import (
    generate_seo_packaging,
    _fallback_packaging,
)
from app.services.telegram_buttons import _token, is_enabled


class TestAdversarialViralityEdgeCases:
    def test_is_clean_search_query_extremes(self):
        # Non-string / empty
        assert is_clean_search_query(None) is False
        assert is_clean_search_query(12345) is False
        assert is_clean_search_query([]) is False
        assert is_clean_search_query("") is False
        assert is_clean_search_query("   ") is False
        assert is_clean_search_query("a") is False  # len < 2

        # Ultra long query (> 120 chars)
        assert is_clean_search_query("a" * 121) is False
        assert is_clean_search_query("a" * 120) is True

        # Technical errors & HTTP artifacts
        assert is_clean_search_query("http://example.com") is False
        assert is_clean_search_query("https://google.com/search") is False
        assert is_clean_search_query("Server Error 500") is False
        assert is_clean_search_query("Page 404 not found") is False
        assert is_clean_search_query("undefined") is False
        assert is_clean_search_query("null") is False
        assert is_clean_search_query("nan") is False
        assert is_clean_search_query("[object Object]") is False
        assert is_clean_search_query("Traceback (most recent call last):") is False
        assert is_clean_search_query("connection reset by peer") is False
        assert is_clean_search_query("<div>html injection</div>") is False
        assert is_clean_search_query('{"json": 1}') is False

        # Valid international queries
        assert is_clean_search_query("Byzantine Empire 1453") is True
        assert is_clean_search_query("日本の歴史 事件") is True
        assert is_clean_search_query("삼풍백화점 붕괴") is True
        assert is_clean_search_query("Livedoor-Skandal 2006") is True

    def test_parse_growth_value_adversarial_numbers(self):
        # None / bool / malformed
        assert _parse_growth_value(None) == (0, "+0%")
        assert _parse_growth_value(False) == (0, "+0%")
        assert _parse_growth_value(True) == (0, "+0%")
        assert _parse_growth_value("") == (0, "+0%")
        assert _parse_growth_value("   ") == (0, "+0%")
        assert _parse_growth_value("undefined") == (0, "+0%")
        assert _parse_growth_value("null") == (0, "+0%")
        assert _parse_growth_value("nan") == (0, "+0%")
        assert _parse_growth_value("invalid-non-numeric") == (0, "invalid-non-numeric")

        # Breakouts
        assert _parse_growth_value("Breakout") == (100_000_000, "Breakout")
        assert _parse_growth_value("breakout") == (100_000_000, "Breakout")
        assert _parse_growth_value("Đột biến") == (100_000_000, "Breakout")
        assert _parse_growth_value("đột biến") == (100_000_000, "Breakout")
        assert _parse_growth_value("dot bien") == (100_000_000, "Breakout")

        # High growth percentages >= 5000%
        p5k, d5k = _parse_growth_value("+5,000%")
        assert p5k == 10_005_000
        assert "+5000% (Breakout)" in d5k

        p10k, d10k = _parse_growth_value(10000)
        assert p10k == 10_010_000
        assert "+10000% (Breakout)" in d10k

        # Decimals & commas
        p_dec, d_dec = _parse_growth_value("+99.4%")
        assert p_dec == 99
        assert d_dec == "+99%"

        p_dec2, d_dec2 = _parse_growth_value("+99.6%")
        assert p_dec2 == 100
        assert d_dec2 == "+100%"

        p_com, d_com = _parse_growth_value("2,450%")
        assert p_com == 2450
        assert d_com == "+2450%"

        # Huge number overflow safety
        huge_str = "+" + ("9" * 40) + "%"
        p_huge, d_huge = _parse_growth_value(huge_str)
        assert p_huge > 10_000_000

    def test_parse_related_queries_df_adversarial(self):
        # 1. Non-dict inputs
        assert _parse_related_queries_df(None) == ([], [])
        assert _parse_related_queries_df([]) == ([], [])
        assert _parse_related_queries_df("invalid") == ([], [])

        # 2. Empty dict
        assert _parse_related_queries_df({}) == ([], [])

        # 3. Dict with None values
        assert _parse_related_queries_df({"test": None}, "test") == ([], [])
        assert _parse_related_queries_df({"test": {"rising": None, "top": None}}, "test") == ([], [])

        # 4. Dict with mixed dirty/clean items
        dirty_rising = [
            {"query": "valid 1", "value": "Breakout"},
            {"query": "http://bad.url", "value": "Breakout"},
            {"query": "valid 2", "value": "+300%"},
            {"query": "", "value": "+200%"},
            None,
            123,
            {"query": "valid 1", "value": "+100%"},
        ]
        r_list, t_list = _parse_related_queries_df({"rising": dirty_rising, "top": []})
        assert len(r_list) == 2
        assert r_list[0]["query"] == "valid 1"
        assert r_list[0]["value"] == "Breakout"
        assert r_list[1]["query"] == "valid 2"
        assert r_list[1]["value"] == "+300%"

    def test_extract_clean_breakout_queries_dedup_and_capping(self):
        raw = [
            {"query": "query a", "value": "+100%"},
            {"query": "Query A", "value": "Breakout"},
            {"query": "query b", "value": "+500%"},
            {"query": "query c", "value": "Breakout"},
            {"query": "query d", "value": "+300%"},
            {"query": "query e", "value": "+200%"},
            {"query": "query f", "value": "+150%"},
            {"query": "query g", "value": "+50%"},
        ]
        res = extract_clean_breakout_queries(raw, max_count=5)
        assert len(res) == 5
        assert "query a" in [q.lower() for q in res]
        assert "query c" in [q.lower() for q in res]
        assert res[2] == "query b"
        assert res[3] == "query d"
        assert res[4] == "query e"


class TestAdversarialB10SEOIntegrity:
    def test_seo_tags_budget_and_character_boundaries(self):
        long_queries = [f"Ultra long breakout search query term number {i} with extensive detail" for i in range(10)]
        tags = build_seo_tags("Primary Keyword Topic", breakout_queries=long_queries, max_chars=500, max_tags=7)
        assert len(tags) <= 7
        assert len(",".join(tags)) <= 500
        for t in tags:
            assert len(t) <= 100
            assert chr(10) not in t
            assert "," not in t

    def test_hashtags_capping_and_cleaning(self):
        dirty_sources = [
            "primary keyword",
            "#already_hashtagged",
            "breakout query with spaces and symbols!@#$",
            "日本語のキーワード",
            "한국어 해시태그",
            "query with special chars: 100% & more",
        ]
        raw_ht = build_hashtags("primary keyword", breakout_queries=dirty_sources)
        clean_ht = validate_hashtags("youtube", raw_ht)
        assert len(clean_ht) <= 5
        for h in clean_ht:
            assert h.startswith("#")
            assert len(h) > 1
            assert " " not in h

    def test_full_pipeline_data_flow_simulation(self):
        b1_rising = [
            {"query": "Constantinople siege 1453", "value": "Breakout"},
            {"query": "Greek fire secret", "value": "+5,200%"},
            {"query": "Mehmed II cannon", "value": "+450%"},
            {"query": "Venetian betrayal 1204", "value": "+300%"},
            {"query": "Theodosian walls fall", "value": "+180%"},
        ]
        b1_breakouts = extract_clean_breakout_queries(b1_rising, max_count=5)
        assert len(b1_breakouts) == 5

        brain = {
            "episode_id": "EN_EP01_byzantine_empire",
            "topic": "Byzantine Empire",
            "trend_keywords": ["Byzantine Empire"],
            "rising_queries": b1_rising,
            "breakout_queries": b1_breakouts,
            "hook_3s": "On May 29, 1453, Constantinople fell.",
            "chapters": [
                {"title": "The Last Roman City", "start": "00:00"},
                {"title": "The Secret Weapon", "start": "02:15"},
                {"title": "The 53-Day Siege", "start": "05:30"},
            ]
        }

        packaging = _fallback_packaging(brain)
        assert packaging["is_fallback"] is True
        assert "Byzantine Empire" in packaging["title_kvs"]

        full_pkg = generate_seo_packaging(brain)
        assert full_pkg["title_a"].startswith("Byzantine Empire")
        assert len(full_pkg["tags"]) <= 7
        assert len(full_pkg["hashtags"]) <= 5
        assert "Key topics & search queries:" in full_pkg["description"] or "Topics covered:" in full_pkg["description"]
        assert "Constantinople siege 1453" in full_pkg["description"]
        assert "Constantinople siege 1453" in full_pkg["tags"]
