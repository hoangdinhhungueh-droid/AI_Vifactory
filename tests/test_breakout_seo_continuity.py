# -*- coding: utf-8 -*-
"""Comprehensive verification test suite for Google Trends Breakout Queries & B10 SEO Injection.
Tests all requirements R1, R2, R3 and edge cases.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import re
import json
from pathlib import Path

from app.services.virality_score import (
    is_clean_search_query,
    extract_clean_breakout_queries,
    _parse_growth_value,
)
from app.services.seo_metadata import (
    build_seo_tags,
    build_hashtags,
    validate_hashtags,
    _slug_tag,
    build_seo_payload,
)
from app.services.seo_autogen_b10 import (
    _fallback_packaging,
    generate_seo_packaging,
)


class TestR1BreakoutExtractionAndFiltering:
    """R1: Test rising queries extraction, growth metrics parsing, and artifact filtering."""

    def test_parse_growth_value_priorities(self):
        p_breakout, d_breakout = _parse_growth_value("Breakout")
        p_dotbien, d_dotbien = _parse_growth_value("Đột biến")
        p_dotbien_ascii, _ = _parse_growth_value("dot bien")
        p_5000, d_5000 = _parse_growth_value("+5,200%")
        p_350, d_350 = _parse_growth_value("+350%")
        p_int, d_int = _parse_growth_value(450)
        p_none, d_none = _parse_growth_value(None)
        p_null_str, d_null_str = _parse_growth_value("null")

        assert p_breakout == 100_000_000
        assert p_dotbien == 100_000_000
        assert p_dotbien_ascii == 100_000_000
        assert p_5000 > p_350
        assert p_350 > p_none
        assert p_none == 0 and d_none == "+0%"
        assert p_null_str == 0 and d_null_str == "+0%"
        assert "Breakout" in d_breakout
        assert "Breakout" in d_5000

    def test_clean_search_query_filtering(self):
        # Valid search queries
        assert is_clean_search_query("Byzantine Empire")
        assert is_clean_search_query("Constantinople siege 1453")
        assert is_clean_search_query("おうむ真理教")
        assert is_clean_search_query("신창원 탈옥")
        assert is_clean_search_query("Đại án Livedoor")
        assert is_clean_search_query("Ölkrise 1973")

        # Technical artifacts & errors (MUST be rejected)
        assert not is_clean_search_query("https://example.com/exploit")
        assert not is_clean_search_query("http://malicious.org")
        assert not is_clean_search_query("404 Not Found")
        assert not is_clean_search_query("500 Internal Server Error")
        assert not is_clean_search_query("[object Object]")
        assert not is_clean_search_query("Traceback (most recent call last)")
        assert not is_clean_search_query("stack trace error")
        assert not is_clean_search_query("undefined")
        assert not is_clean_search_query("null")
        assert not is_clean_search_query("{'key': 'value'}")
        assert not is_clean_search_query("<script>alert(1)</script>")
        assert not is_clean_search_query("   ")
        assert not is_clean_search_query("a")  # too short (<2)
        assert not is_clean_search_query(None)
        assert not is_clean_search_query(123)

    def test_extract_clean_breakout_queries_sorting_and_dedup(self):
        raw_rising = [
            {"query": "Low growth term", "value": "+50%"},
            {"query": "Venetian betrayal 1204", "value": "Đột biến"},
            {"query": "https://malicious.link", "value": "Breakout"},
            {"query": "Constantinople siege 1453", "value": "Breakout"},
            {"query": "500 server error", "value": "+9999%"},
            {"query": "Greek fire secret", "value": "+5,500%"},
            {"query": "Mehmed II cannon", "value": "+350%"},
            {"query": "Constantinople siege 1453", "value": "Breakout"},  # duplicate
            {"query": "[object Object]", "value": "Breakout"},
        ]

        extracted = extract_clean_breakout_queries(raw_rising, max_count=5)
        assert len(extracted) == 5
        # Breakouts first (priority 100M)
        assert extracted[0] in ["Venetian betrayal 1204", "Constantinople siege 1453"]
        assert extracted[1] in ["Venetian betrayal 1204", "Constantinople siege 1453"]
        # Then +5500% (priority 10M + 5500)
        assert extracted[2] == "Greek fire secret"
        # Then +350% (priority 350)
        assert extracted[3] == "Mehmed II cannon"
        # Then +50% (priority 50)
        assert extracted[4] == "Low growth term"
        # Artifacts and duplicates completely absent
        assert "https://malicious.link" not in extracted
        assert "500 server error" not in extracted


class TestR2B10SEOInjection:
    """R2: Test YouTube hidden tags, platform-capped hashtags, and natural description injection."""

    def test_build_seo_tags_exact_prioritization_and_no_starvation(self):
        primary = "Byzantine Empire"
        bqs = ["Constantinople siege 1453", "Greek fire secret", "Mehmed II cannon", "Venetian betrayal 1204"]
        tags = build_seo_tags(primary, breakout_queries=bqs, max_chars=500, max_tags=7)

        # Must include primary keyword
        assert tags[0] == "Byzantine Empire"
        # Must include all 4 breakout queries in the first 5 slots without starvation
        for bq in bqs:
            assert bq in tags
        assert len(tags) <= 7
        assert len(",".join(tags)) <= 500

    def test_build_seo_tags_sanitization_and_boundary_conditions(self):
        primary = "Byzantine Empire"
        messy_bqs = [
            "Constantinople, siege of 1453",  # comma inside tag
            "Greek fire\nsecret\tweapon",      # newlines/tabs inside tag
            "a" * 125,                         # individual tag > 100 chars
            {"query": "Dict format query", "value": "Breakout"},  # dict input
            None,                              # None input
            False,                             # bool input
        ]
        tags = build_seo_tags(primary, breakout_queries=messy_bqs, max_chars=500, max_tags=7)

        for t in tags:
            # No comma in any tag
            assert "," not in t
            # No newlines or tabs
            assert "\n" not in t
            assert "\r" not in t
            assert "\t" not in t
            # YouTube strict individual tag limit <= 100
            assert len(t) <= 100
            assert t.strip() == t

        # Total comma-separated string budget <= 500
        assert len(",".join(tags)) <= 500
        assert "Dict format query" in tags

    def test_build_hashtags_and_validate_multilingual_and_capping(self):
        inputs = [
            "Byzantine Empire",
            "Constantinople siege 1453",
            "おうむ真理教",
            "신창원 탈옥",
            "Đại án Livedoor",
            "Ölkrise 1973",
            "#AlreadyHashed",
            {"query": "Dict Hashtag Query", "value": "Breakout"},
            "   ",
            "!!!",
            False,
        ]
        raw_tags = build_hashtags("Primary Keyword", breakout_queries=inputs)
        assert "#ByzantineEmpire" in raw_tags
        assert "#ConstantinopleSiege1453" in raw_tags
        assert "#おうむ真理教" in raw_tags
        assert "#신창원탈옥" in raw_tags
        assert "#ĐạiÁnLivedoor" in raw_tags
        assert "#Ölkrise1973" in raw_tags
        assert "#DictHashtagQuery" in raw_tags
        assert "#" not in raw_tags

        yt_tags = validate_hashtags("youtube", raw_tags)
        assert len(yt_tags) <= 5
        for ht in yt_tags:
            assert ht.startswith("#")
            assert len(ht) > 1

    def test_dict_format_breakout_queries_in_build_seo_payload(self):
        episode = {
            "episode_id": "en-byzantine-empire-ep001",
            "topic": "Byzantine Empire",
            "trend_keywords": ["Byzantine Empire"],
            "breakout_queries": [
                {"query": "Constantinople siege 1453", "value": "Breakout"},
                {"query": "Greek fire secret", "value": "+5000%"},
            ],
            "hook_3s": "On May 29, 1453, Constantinople fell.",
        }
        payload = build_seo_payload("youtube", episode)
        assert "Topics covered:" in payload["description"]
        assert "Constantinople siege 1453" in payload["description"]
        assert "Greek fire secret" in payload["description"]
        assert "Constantinople siege 1453" in payload["tags"]

    def test_deterministic_fallback_packaging_integrity(self):
        episode = {
            "episode_id": "en-byzantine-empire-ep001",
            "topic": "Byzantine Empire",
            "trend_keywords": ["Byzantine Empire"],
            "breakout_queries": [
                "Constantinople siege 1453",
                "Greek fire secret",
                {"query": "Mehmed II cannon", "value": "+350%"},
            ],
            "hook_3s": "On May 29, 1453, a 1,123-year empire collapsed overnight.",
        }

        # Test deterministic fallback helper
        fb = _fallback_packaging(episode)
        assert fb["is_fallback"] is True
        assert fb["title_kvs"].startswith("Byzantine Empire")
        # Ensure description hook is clean (not chopped mid-line)
        assert not fb["description_hook_2_lines"].endswith("...")
        assert "Topics covered:" not in fb["description_hook_2_lines"]

        # Test generate_seo_packaging in fallback mode
        import app.services.seo_autogen_b10 as seo_b10
        orig_call = seo_b10.call_gpt6_astra

        def mock_llm_fail(*a, **kw):
            raise ConnectionError("Simulated LLM network failure")

        seo_b10.call_gpt6_astra = mock_llm_fail
        try:
            pkg = generate_seo_packaging(episode)
        finally:
            seo_b10.call_gpt6_astra = orig_call

        assert pkg["generation_method"] == "deterministic_fallback"
        assert pkg["title_a"].startswith("Byzantine Empire")
        assert len(pkg["tags"]) <= 7
        assert len(",".join(pkg["tags"])) <= 500
        assert len(pkg["hashtags"]) <= 5
        assert len(pkg["description"]) <= 5000
        # Check that breakout queries are included in description and tags
        assert "Constantinople siege 1453" in pkg["tags"]
        assert "Mehmed II cannon" in pkg["tags"]
        assert "Key topics & search queries:" not in pkg["description"]


class TestR3PipelineContinuityAndPayloadAudit:
    """R3: Test data continuity from B1 context -> B10 payload and Notion sync schemas."""

    def test_seo_payload_full_layer_structure(self):
        episode = {
            "episode_id": "en-byzantine-empire-ep001",
            "topic": "Byzantine Empire",
            "trend_keywords": ["Byzantine Empire"],
            "breakout_queries": ["Constantinople siege 1453", "Greek fire secret", "Mehmed II cannon", "Venetian betrayal 1204"],
            "hook_3s": "On May 29, 1453, a 1,123-year empire collapsed overnight.",
            "chapters": [
                {"title": "The Golden Illusion", "summary_1_sentence": "Constantinople stood impregnable for a millennium.", "duration_est_s": 180},
                {"title": "The Classified Fire", "summary_1_sentence": "Greek fire incinerated enemy fleets.", "duration_est_s": 180},
                {"title": "The 1204 Betrayal", "summary_1_sentence": "Venetian debt caused Christian sack.", "duration_est_s": 190},
                {"title": "The Wall Falls", "summary_1_sentence": "Mehmed II massive cannon breaches.", "duration_est_s": 180},
                {"title": "The Legacy", "summary_1_sentence": "Scholars spark European Renaissance.", "duration_est_s": 170},
            ]
        }

        payload = build_seo_payload("youtube", episode)
        assert payload["platform"] == "youtube"
        assert payload["title"].startswith("Byzantine Empire")
        assert len(payload["tags"]) <= 7
        assert len(payload["hashtags"]) <= 5
        assert "Topics covered:" in payload["description"]
        assert "Chapters:" in payload["description"]
        assert "00:00 The Golden Illusion" in payload["description"]
        assert payload["ai_disclosure"] is True
        assert payload["made_for_kids"] is False

    def test_youtube_upload_payload_format(self, tmp_path):
        from app.services.seo_autogen_b10 import generate_seo_packaging

        episode = {
            "episode_id": "en-byzantine-empire-ep001",
            "topic": "Byzantine Empire",
            "trend_keywords": ["Byzantine Empire"],
            "breakout_queries": ["Constantinople siege 1453", "Greek fire secret", "Mehmed II cannon"],
            "hook_3s": "On May 29, 1453, Constantinople fell.",
        }

        # Mock or run deterministic fallback packaging
        import app.services.seo_autogen_b10 as seo_b10
        orig_call = seo_b10.call_gpt6_astra
        seo_b10.call_gpt6_astra = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("Fallback"))
        try:
            pkg = generate_seo_packaging(episode)
        finally:
            seo_b10.call_gpt6_astra = orig_call

        upload_payload = {
            "episode_id": episode["episode_id"],
            "title": pkg["title_a"],
            "description": pkg["description"],
            "tags": pkg["tags"],
            "hashtags": pkg["hashtags"],
            "breakout_queries": pkg.get("breakout_queries", []),
            "category_id": "22",
            "privacy_status": "unlisted",
            "export": {"target_file": "final_169.mp4"},
            "market": "en",
        }

        payload_file = tmp_path / "youtube_upload_payload.json"
        with open(payload_file, "w", encoding="utf-8") as f:
            json.dump(upload_payload, f, ensure_ascii=False, indent=2)

        # Validate saved payload
        with open(payload_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["episode_id"] == "en-byzantine-empire-ep001"
        assert data["title"].startswith("Byzantine Empire")
        assert len(data["tags"]) <= 7
        assert len(data["hashtags"]) <= 5
        assert len(data["breakout_queries"]) == 3
        assert data["privacy_status"] == "unlisted"

    def test_parse_related_queries_df_multi_formats_and_serpapi(self):
        import pandas as pd
        from app.services.virality_score import _parse_related_queries_df

        # 1. Pandas DataFrame with Breakout, high %, lower % and artifacts
        df_rising = pd.DataFrame([
            {"query": "Tier 2 growth term", "value": "+200%"},
            {"query": "Tier 1 breakout", "value": "Breakout"},
            {"query": "Tier 1 high percentage", "value": "+5,500%"},
            {"query": "http://error.com/500", "value": "Breakout"},
            {"query": "Tier 2 second", "value": "+150%"},
        ])
        df_top = pd.DataFrame([
            {"query": "top query clean", "value": 100},
            {"query": "404 not found", "value": 50},
        ])
        res_rising, res_top = _parse_related_queries_df({"ai": {"rising": df_rising, "top": df_top}}, "ai")
        assert len(res_rising) == 4
        assert res_rising[0]["query"] == "Tier 1 breakout"
        assert res_rising[1]["query"] == "Tier 1 high percentage"
        assert res_rising[2]["query"] == "Tier 2 growth term"
        assert res_rising[3]["query"] == "Tier 2 second"
        assert len(res_top) == 1
        assert res_top[0]["query"] == "top query clean"

        # 2. SerpApi JSON dictionary format with extracted_value
        serp_data = {
            "related_queries": {
                "rising": [
                    {"query": "serp query 1", "extracted_value": 5200},
                    {"query": "serp breakout", "value": "Breakout"},
                    {"query": "serp query 2", "extracted_value": 300},
                ],
                "top": [{"query": "serp top", "value": 100}]
            }
        }
        res_serp_rising, res_serp_top = _parse_related_queries_df(serp_data, "subject")
        assert len(res_serp_rising) == 3
        assert res_serp_rising[0]["query"] == "serp breakout"
        assert res_serp_rising[1]["query"] == "serp query 1"
        assert res_serp_rising[2]["query"] == "serp query 2"

        # 3. Direct rising dict
        direct_data = {"rising": [{"query": "direct term", "value": "+500%"}], "top": []}
        r_direct, _ = _parse_related_queries_df(direct_data)
        assert len(r_direct) == 1
        assert r_direct[0]["query"] == "direct term"

    def test_parse_growth_value_decimals_and_commas(self):
        from app.services.virality_score import _parse_growth_value
        p1, d1 = _parse_growth_value("+45.5%")
        assert p1 == 46
        assert d1 == "+46%"

        p2, d2 = _parse_growth_value("1,250%")
        assert p2 == 1250
        assert d2 == "+1250%"

        p3, d3 = _parse_growth_value("5,000%")
        assert p3 > 10_000_000
        assert "Breakout" in d3

    def test_extract_clean_rising_queries_alias(self):
        from app.services.virality_score import extract_clean_rising_queries, extract_clean_breakout_queries
        assert extract_clean_rising_queries == extract_clean_breakout_queries
        res = extract_clean_rising_queries([{"query": "Test Query", "value": "Breakout"}])
        assert res == ["Test Query"]

    @pytest.mark.integration
    def test_telegram_buttons_token_and_gate1_formatting(self):
        from app.services.telegram_buttons import _token, is_enabled, send_gate1_card
        token = _token()
        assert token.startswith("8757795778"), f"Expected bot token to start with 8757795778, got {token[:10]}"
        assert is_enabled() is True

    @pytest.mark.integration
    def test_hhtech_reasoner_prompt_structure(self):
        from app.services.hhtech_reasoner import reason_topic_niche
        import app.services.hhtech_reasoner as hht

        # Capture prompt passed to call_gpt6_astra
        captured = {}
        def mock_call(prompt, system_prompt="", **kw):
            captured["prompt"] = prompt
            captured["system_prompt"] = system_prompt
            return json.dumps({
                "topic_name_vi": "Đế chế Byzantine",
                "search_specific_keyword": "Byzantine Empire Constantinople",
                "task_slug": "byzantine-empire",
                "niche_angle_brief": "Cơ chế tài chính và quân sự sụp đổ.",
                "story_direction_5_arcs": "Hồi 1 (Hook: Constantinople siege 1453): ... -> Hồi 2: ... -> Hồi 3: ... -> Hồi 4: ... -> Hồi 5: ...",
                "breakout_queries": ["Constantinople siege 1453", "Greek fire secret"]
            })

        orig_call = hht.call_gpt6_astra
        hht.call_gpt6_astra = mock_call
        try:
            res = reason_topic_niche(
                subject="Byzantine Empire",
                market="EN",
                virality_score=0.89,
                rising_queries=[
                    {"query": "Constantinople siege 1453", "value": "Breakout"},
                    {"query": "Greek fire secret", "value": "+5,500%"},
                    {"query": "Mehmed II cannon", "value": "+350%"}
                ]
            )
        finally:
            hht.call_gpt6_astra = orig_call

        assert "[GOOGLE TRENDS RISING / BREAKOUT QUERIES (NATIVE LANGUAGE)]:" in captured["prompt"]
        assert "Constantinople siege 1453" in captured["prompt"]
        assert "(Breakout)" in captured["prompt"]
        assert "Greek fire secret" in captured["prompt"]
        assert "RULE 444 AN ONG HOOK:" in captured["system_prompt"]
        assert "SEARCH-SPECIFIC TARGETING:" in captured["system_prompt"]
        assert res["task_slug"] == "byzantine-empire"
        assert len(res["breakout_queries"]) == 2
