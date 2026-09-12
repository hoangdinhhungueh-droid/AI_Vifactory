# -*- coding: utf-8 -*-
"""
Round 3 Adversarial Test Suite for Video Factory Rising Queries & B10 SEO Pipeline.
Deep stress tests across R1, R2, R3, Notion payload sync, Telegram card generation,
and downstream pipeline script continuity.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
import re
from unittest.mock import patch, MagicMock

from app.services.virality_score import (
    _parse_growth_value,
    is_clean_search_query,
    extract_clean_breakout_queries,
    extract_clean_rising_queries,
    _parse_related_queries_df,
)
from app.services.hhtech_reasoner import (
    reason_topic_niche,
    _fallback_topic,
    HHTECH_MODEL,
)
from app.services.seo_autogen_b10 import (
    generate_seo_packaging,
    _fallback_packaging,
)
from app.services.seo_metadata import (
    build_seo_tags,
    build_hashtags,
    validate_hashtags,
    build_seo_payload,
    write_seo_payloads,
    generate_ab_variants,
)
from app.services import telegram_buttons as tb
from app.services import episode_numbering as _epnum


class TestR1AdversarialBreakoutSorting:
    """Stress test R1: Top-down sorting of Google Trends Rising Queries table."""

    def test_breakout_variants_and_diacritics_tier1(self):
        """Tier 1: All Breakout / Đột biến / breakout variants must have priority >= 100,000,000."""
        variants = [
            "Breakout", "breakout", "BREAKOUT",
            "Đột biến", "đột biến", "ĐỘT BIẾN",
            "dot bien", "Dot Bien",
        ]
        for v in variants:
            prio, display = _parse_growth_value(v)
            assert prio == 100_000_000, f"Failed for variant: {v}"
            assert display == "Breakout", f"Failed display for variant: {v}"

    def test_high_growth_tier1_extension(self):
        """Percentages >= 5000% must have priority >= 10,000,000 and '(Breakout)' label."""
        test_cases = [
            (5000, 10_005_000, "+5000% (Breakout)"),
            ("5,500%", 10_005_500, "+5500% (Breakout)"),
            ("+12,000%", 10_012_000, "+12000% (Breakout)"),
            ("99999", 10_099_999, "+99999% (Breakout)"),
        ]
        for val_in, expected_prio, expected_disp in test_cases:
            prio, disp = _parse_growth_value(val_in)
            assert prio == expected_prio
            assert disp == expected_disp

    def test_descending_growth_tier2(self):
        """Tier 2: Growth % in descending order (+4500%, +2450%, +500%, +150%, +50%, +0%)."""
        percentages = ["+4500%", "2,450%", "+500%", "150%", "50.4%", "+0%"]
        parsed = [_parse_growth_value(p) for p in percentages]
        priorities = [p[0] for p in parsed]
        assert priorities == sorted(priorities, reverse=True)
        assert priorities == [4500, 2450, 500, 150, 50, 0]

    def test_extract_clean_breakout_queries_strictly_top5(self):
        """Must extract exactly 5 clean queries from a larger pool, strictly adhering to tier priorities."""
        raw_pool = [
            {"query": "low growth 1", "value": "+10%"},
            {"query": "Breakout A", "value": "Breakout"},
            {"query": "high growth 500", "value": "+500%"},
            {"query": "Breakout B (Vietnamese)", "value": "Đột biến"},
            {"query": "high growth 1000", "value": "+1000%"},
            {"query": "super surge 6000", "value": "+6000%"},
            {"query": "low growth 2", "value": "+20%"},
            {"query": "high growth 300", "value": "+300%"},
            {"query": "http://invalid-url.com/leak", "value": "Breakout"},  # Dirty
        ]
        top5 = extract_clean_breakout_queries(raw_pool, max_count=5)
        assert len(top5) == 5
        # Order should be: Breakout A / Breakout B (100M), super surge 6000 (10M+6K), high growth 1000 (1000), high growth 500 (500)
        assert "Breakout A" in top5[:2]
        assert "Breakout B (Vietnamese)" in top5[:2]
        assert top5[2] == "super surge 6000"
        assert top5[3] == "high growth 1000"
        assert top5[4] == "high growth 500"
        assert "http://invalid-url.com/leak" not in top5

    def test_extract_clean_rising_queries_alias_identical(self):
        raw_pool = [{"query": "query x", "value": "Breakout"}, {"query": "query y", "value": "+200%"}]
        res1 = extract_clean_breakout_queries(raw_pool)
        res2 = extract_clean_rising_queries(raw_pool)
        assert res1 == res2 == ["query x", "query y"]


class TestR2AdversarialHHTechReasoning:
    """Stress test R2: GPT-5.6-Sol prompt construction, breakout formatting, and niche reasoning."""

    @pytest.mark.integration
    @patch("app.services.hhtech_reasoner.call_gpt6_astra")
    def test_reason_topic_niche_prompt_formatting_and_breakout_capture(self, mock_call):
        mock_response = json.dumps({
            "topic_name_vi": "Sự sụp đổ của Đế chế La Mã",
            "search_specific_keyword": "Roman Empire collapse lead pipes",
            "task_slug": "roman-empire-collapse",
            "niche_angle_brief": "Cơ chế đầu độc chì trong hệ thống dẫn nước La Mã đẩy nhanh sự suy vong giới quý tộc.",
            "story_direction_5_arcs": "Hồi 1 (Hook): Chì trong nước uống... -> Hồi 2: Cơ chế tích tụ -> Hồi 3: Suy thoái nhận thức -> Hồi 4: Hỗn loạn chính trị -> Hồi 5: Bài học hiện đại",
            "breakout_queries": ["Roman lead pipes theory", "Roman water system poisoning", "Roman aristocracy decline"]
        })
        mock_call.return_value = mock_response

        rising_sample = [
            {"query": "Roman lead pipes theory", "value": "Breakout"},
            {"query": "Roman water system poisoning", "value": "+800%"},
            {"query": "Roman aristocracy decline", "value": "+350%"},
        ]
        top_sample = [
            {"query": "Roman Empire documentary", "value": "100"},
            {"query": "Fall of Rome history", "value": "85"},
        ]

        result = reason_topic_niche("Roman Empire", "EN", virality_score=0.92, rising_queries=rising_sample, top_queries=top_sample)

        # Verify call arguments
        assert mock_call.called
        call_args = mock_call.call_args
        user_prompt = call_args[0][0]
        system_prompt = call_args[1]["system_prompt"]

        # Check user_prompt contains the exact section header and formatted items
        assert "[GOOGLE TRENDS RISING / BREAKOUT QUERIES (NATIVE LANGUAGE)]:" in user_prompt
        assert '"Roman lead pipes theory" (Breakout)' in user_prompt
        assert '"Roman water system poisoning" (+800%)' in user_prompt
        assert '"Roman aristocracy decline" (+350%)' in user_prompt

        assert "[TOP SEARCH QUERIES]:" in user_prompt
        assert '"Roman Empire documentary" (Index: 100)' in user_prompt

        # Check system prompt includes the 5-act and Hook shock instructions
        assert "RULE 444 AN ONG HOOK" in system_prompt
        assert "SEARCH-SPECIFIC TARGETING" in system_prompt

        # Check result structure
        assert result["task_slug"] == "roman-empire-collapse"
        assert len(result["breakout_queries"]) == 3
        assert result["breakout_queries"][0] == "Roman lead pipes theory"

    def test_fallback_topic_preserves_breakout_queries(self):
        """When LLM is unreachable, deterministic fallback must include breakout queries cleanly."""
        rising_sample = [
            {"query": "Live Door Horie arrest", "value": "Breakout"},
            {"query": "Livedoor stock crash", "value": "+500%"},
        ]
        fb = _fallback_topic("ライブドア事件", "JP", 0.85, rising_queries=rising_sample)
        assert fb["topic_name_vi"] == "ライブドア事件 (JP)"
        assert "Live Door Horie arrest" in fb["search_specific_keyword"]
        assert fb["breakout_queries"] == ["Live Door Horie arrest", "Livedoor stock crash"]


class TestR3AdversarialB10SEOAndTelegram:
    """Stress test R3: Multi-layer SEO injection, Telegram Bot token, and packaging integrity."""

    @pytest.mark.integration
    def test_telegram_buttons_token_uses_vf_tg_bot_token(self):
        """_token() must prioritize VF_TG_BOT_TOKEN starting with 8757795778."""
        token = tb._token()
        assert token.startswith("8757795778"), f"Token {token} does not start with 8757795778"

    def test_telegram_gate1_card_html_safety_and_breakout_display(self):
        """Gate 1 card formatting must safely escape HTML and display breakout queries."""
        en_pack = {
            'top_subject': 'Jack the <Ripper>',
            'virality': 0.95,
            'topic_name_vi': 'Bí ẩn <Jack the Ripper>',
            'search_specific_keyword': 'Jack the Ripper police corruption',
            'niche_angle_brief': 'Góc nhìn ngách về <bảo kê tội phạm>.',
            'story_direction_5_arcs': 'Hồi 1: <Vụ án đầu tiên> -> Hồi 2: Hiện trường...',
            'task_id': 'EN_EP0001_jack_ripper',
            'breakout_queries': [
                {'query': 'Jack <Ripper> letters', 'value': 'Breakout'},
                {'query': 'Whitechapel murders', 'value': '+450%'},
            ]
        }
        jp_pack = {'top_subject': 'None', 'virality': 0, 'topic_name_vi': 'None', 'task_id': 'jp-none'}
        kr_pack = {'top_subject': 'None', 'virality': 0, 'topic_name_vi': 'None', 'task_id': 'kr-none'}

        with patch("app.services.telegram_buttons.send_with_buttons") as mock_send:
            mock_send.return_value = 12345
            import asyncio
            msg_id = asyncio.run(tb.send_gate1_card(en_pack, jp_pack, kr_pack))
            assert msg_id == 12345

            call_args = mock_send.call_args
            sent_text = call_args[0][0]
            sent_buttons = call_args[1].get("buttons", call_args[0][1] if len(call_args[0]) > 1 else None)
            assert "&lt;Ripper&gt;" in sent_text
            assert "&lt;Jack the Ripper&gt;" in sent_text
            assert "Jack &lt;Ripper&gt; letters (Breakout)" in sent_text
            assert "Whitechapel murders (+450%)" in sent_text
            assert sent_buttons is None or len(sent_buttons) == 4

    def test_seo_tags_budget_and_breakout_prioritization(self):
        """Breakout queries must be prioritized in tags and never exceed 500 characters or 7 tags."""
        primary_kw = "Byzantine Empire"
        breakouts = [
            "Constantinople siege 1453",
            "Greek fire secret",
            "Mehmed II massive cannon",
            "Venetian debt trap 1204",
            "Justinian plague collapse",
        ]
        secondary = ["history documentary", "roman empire survival", "middle ages"]

        tags = build_seo_tags(primary_kw, secondary=secondary, breakout_queries=breakouts, max_chars=500, max_tags=7)
        assert len(tags) == 7
        assert tags[0] == "Byzantine Empire"
        assert tags[1] == "Constantinople siege 1453"
        assert tags[2] == "Greek fire secret"
        assert tags[3] == "Mehmed II massive cannon"
        assert tags[4] == "Venetian debt trap 1204"
        assert tags[5] == "Justinian plague collapse"
        # Total characters joined by comma
        assert len(",".join(tags)) <= 500

    def test_hashtags_capping_and_cleaning(self):
        """Hashtags must convert breakout queries into slug tags, capped at <= 5."""
        breakouts = [
            "Constantinople 1453",
            "Greek Fire!",
            "Mehmed II Cannon",
            "Fourth Crusade 1204",
            "Roman Empire",
            "Extra Topic Beyond 5",
        ]
        raw_ht = build_hashtags("Byzantine Empire", breakout_queries=breakouts)
        clean_ht = validate_hashtags("youtube", raw_ht)
        assert len(clean_ht) == 5
        assert clean_ht[0] == "#ByzantineEmpire"
        assert clean_ht[1] == "#Constantinople1453"
        assert clean_ht[2] == "#GreekFire"
        assert clean_ht[3] == "#MehmedIICannon"
        assert clean_ht[4] == "#FourthCrusade1204"

    def test_seo_autogen_b10_description_contains_breakout_queries(self):
        """B10 generated description must naturally contain the top rising search queries."""
        episode = {
            "episode_id": "EN_EP0001_byzantine_empire",
            "topic": "Byzantine Empire",
            "trend_keywords": ["Byzantine Empire"],
            "breakout_queries": [
                "Constantinople siege 1453",
                "Greek fire classified weapon",
                "Mehmed II cannon tactics",
            ],
            "hook_3s": "In 1453, a thousand-year empire fell in a single day.",
            "chapters": [
                {"title": "The Last Roman Stronghold", "start": "00:00"},
                {"title": "Secret Fire of the Sea", "start": "03:00"},
            ]
        }
        mock_res = json.dumps({
            "title_kvs": "Byzantine Empire: The Secret Weapon That Held 1,000 Years",
            "description": (
                "In 1453, a thousand-year empire fell in a single day.\n"
                "Featuring Constantinople siege 1453 and Greek fire classified weapon.\n"
                "00:00 The Last Roman Stronghold\n"
                "03:00 Secret Fire of the Sea"
            ),
            "primary_keywords": ["Byzantine Empire"],
            "secondary_keywords": ["Constantinople"],
            "hashtags": ["#ByzantineEmpire", "#History"],
            "chapters": [
                {"title": "The Last Roman Stronghold", "start": "00:00"},
                {"title": "Secret Fire of the Sea", "start": "03:00"}
            ]
        })
        with patch("app.services.seo_autogen_b10.call_gpt6_astra", return_value=mock_res):
            pkg = generate_seo_packaging(episode)
        desc = pkg["description"]
        assert "Byzantine Empire" in pkg["title_a"]
        assert "Key topics & search queries:" not in desc
        assert "Constantinople siege 1453" in desc
        assert "Greek fire classified weapon" in desc
        assert len(desc) <= 5000


class TestNotionAndDownstreamContinuity:
    """Stress test Notion sync properties and downstream episode loading."""

    @pytest.mark.integration
    def test_pending_task_cache_and_commit_roundtrip(self, tmp_path):
        """Test local caching of pending tasks with rising & breakout queries."""
        task_id = "EN_EP0099_test_topic"
        payload = {
            "topic_name": "Test Topic",
            "keyword": "test keyword",
            "virality_score": 0.95,
            "niche_brief": "A concise niche brief.",
            "story_arcs": "5-Arc test direction",
            "rising_queries": [{"query": "test rising 1", "value": "Breakout"}],
            "breakout_queries": ["test rising 1"],
        }
        _epnum.cache_pending_task(task_id, "EN", payload)
        # Verify file exists
        p_path = _epnum._pending_path(task_id)
        assert os.path.exists(p_path)

        with open(p_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["episode_id"] == task_id
        assert data["breakout_queries"] == ["test rising 1"]

        # Clean up
        _epnum.remove_pending_task(task_id)
        assert not os.path.exists(p_path)
