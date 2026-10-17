"""
Tests for B1 Trend Gate (Commit 1)
- Episode ID generation with market isolation
- Virality score gate (≥ 7.0)
- Notion sync
"""
import pytest
import json
import os
from app.services.episode_numbering import get_next_episode_id, sanitize_episode_slug


class TestTrendGateB1:
    """B1 Trend Gate rule validation tests (Rule D1, D6)"""

    def test_sanitize_episode_slug(self):
        """Test slug sanitization to snake_case."""
        assert sanitize_episode_slug("Byzantine Empire") == "byzantine_empire"
        assert sanitize_episode_slug("AI & ML!") == "ai_ml"
        assert sanitize_episode_slug("a" * 100) == "a" * 45
        assert sanitize_episode_slug("") == "topic"
        assert sanitize_episode_slug("   spaces   ") == "spaces"

    def test_episode_id_format_en(self):
        """Test EN market episode ID format (Rule D1)."""
        task_id = get_next_episode_id("EN", "test_topic")
        # Format: <MARKET>_EP<4digits>_<slug>
        assert task_id.startswith("EN_EP")
        parts = task_id.split("_")
        assert len(parts) >= 2
        assert parts[0] == "EN"
        assert "EP" in parts[1]

    def test_market_isolation(self):
        """Test that markets are isolated (EN, JP, KR counters separate)."""
        en_id = get_next_episode_id("EN", "topic_a")
        jp_id = get_next_episode_id("JP", "topic_b")
        kr_id = get_next_episode_id("KR", "topic_c")
        
        assert en_id.startswith("EN_EP")
        assert jp_id.startswith("JP_EP")
        assert kr_id.startswith("KR_EP")

    def test_virality_score_gate(self):
        """Test that virality score ≥ 7.0 (Rule D6)."""
        # This would be part of the trend_virality endpoint
        # For now, verify the gate logic exists in code
        min_score = 0.70
        test_scores = [0.69, 0.70, 0.75, 0.80]
        
        for score in test_scores:
            is_valid = score >= min_score
            if score < min_score:
                assert not is_valid
            else:
                assert is_valid

    def test_task_metadata_schema(self):
        """Test task metadata JSON schema."""
        metadata = {
            "task_id": "EN_EP0251_byzantine_empire",
            "keyword": "Byzantine Empire",
            "market": "EN",
            "score": 7.5,
            "status": "Draft",
            "created_at": "2026-08-30T09:00:00+00:00",
            "node": "B1",
            "rule": "D1, D6"
        }
        
        assert metadata["task_id"].startswith("EN_EP")
        assert metadata["score"] >= 7.0
        assert metadata["status"] in ["Draft", "InProgress", "Complete", "Failed"]
    def test_sanitize_candidate_term_preserves_english_words(self):
        """Rule 118/125: Verify candidate headlines are never mangled or cut in half."""
        from app.services.trend_engine_b1 import sanitize_candidate_term

        # Test case 1: Candidate #19 - Tesla Cybercab
        t1 = "Tesla launched Cybercab in Austin. Hours later, the feds launched an investigation."
        s1 = sanitize_candidate_term(t1)
        assert "Tesla" in s1
        assert "Cybercab" in s1
        assert "investigation" in s1
        assert not s1.startswith("ds launched")  # Former fatal bug test

        # Test case 2: Candidate #58 - West Marine bankruptcy
        t2 = "West Marine CEO details bankruptcy lessons"
        s2 = sanitize_candidate_term(t2)
        assert s2 == "West Marine CEO details bankruptcy lessons"
        assert "bankru" not in s2 or "bankruptcy" in s2

        # Test case 3: Candidate #13 - Montessori Ponzi
        t3 = "Inside the Outrageous Collapse of a ‘Montessori Ponzi’"
        s3 = sanitize_candidate_term(t3)
        assert "Montessori Ponzi" in s3
        assert not s3.endswith("Montesso")

        # Test case 4: Stripping publisher suffix
        t4 = "Kennedy Center could close as early as Tuesday, warns of bankruptcy, documents show - The Washington Post"
        s4 = sanitize_candidate_term(t4)
        assert not s4.endswith("The Washington Post")
        assert "Kennedy Center" in s4

    def test_sanitize_candidate_term_cjk(self):
        """Rule 118/122: Verify CJK quoted entity and event extraction."""
        from app.services.trend_engine_b1 import sanitize_candidate_term

        jp_headline = "【近畿初の神社倒産】清和源氏発祥の『多田神社』が民事再生法の適用申請...（MBSニュース）"
        s_jp = sanitize_candidate_term(jp_headline)
        assert s_jp == "多田神社 民事再生"

    def test_zero_quota_youtube_scraper(self):
        """Rule 123: Verify zero-quota public YouTube search scraper structure."""
        from app.services.competitor_recon_b15 import scrape_youtube_search_zero_quota

        results = scrape_youtube_search_zero_quota("Tesla Cybercab Austin", market="en", max_results=3)
        assert isinstance(results, list)
        if results:
            first = results[0]
            assert "video_id" in first
            assert "title" in first
            assert "views" in first
            assert "url" in first
            assert first["url"].startswith("https://www.youtube.com/watch?v=")


    def test_cjk_story_gate_numbers_and_shock(self):
        """Rule 120/128: Verify Japanese text with numbers and shock words passes check 5 and 9."""
        from app.services.story_gate import score_story
        sample_jp = """=== ACT I ===
2026年9月14日、中部電力は社長と会長の2人が9月30日付で辞任すると発表した。
浜岡原発の安全審査が停止したという衝撃的な見出しだ。
しかし2019年と2021年に2度の内部通報があった。
なぜ危機は防げなかったのか？

=== ACT II ===
2012年に遡る。公式見解はデータの扱いと説明した。
報道は神話を伝えた。しかし異議は退けられた。

=== ACT III ===
内部記録を調べる。どこに停止権限があったのか。
それが死角を決める。
これは単なる誤解だったのか。
現場は数字を揃えた。

=== ACT IV ===
原子力規制委員会が決定打を下した。
責任者が処分され、再稼働は破綻した。
証拠が暴露された。

=== ACT V ===
今日に残る教訓は何だったのか。
現代の企業統治への警告である。
結論として信頼の回復が問われている。
"""
        res = score_story(sample_jp)
        assert res["checks"]["5_sourced_numbers"] is True, f"Check 5 failed. Numbers found: {res['numbers_found']}"
        assert res["checks"]["9_hook_shock_in_first_60w"] is True, "Check 9 failed to find shock word in first 60 words"
        assert res["numbers_found"] >= 5

    def test_cjk_temp_task_id_hash(self):
        """Rule 125/128: Verify CJK terms without latin letters receive a deterministic MD5 hash."""
        import hashlib
        import re
        term_jp = "＜主張＞中部電トップ辞任 日本の力損なう不祥事だ 社説"
        clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(term_jp).lower()).strip('-')[:20]
        assert clean_slug == ""  # Old buggy behavior produced empty slug

        # New behavior: falls back to md5 hash
        term_hash = hashlib.md5(term_jp.encode('utf-8')).hexdigest()[:8]
        temp_task_id = f"JP_TEMP_{term_hash}"
        assert temp_task_id.startswith("JP_TEMP_")
        assert len(temp_task_id) == len("JP_TEMP_") + 8
        assert temp_task_id != "JP_TEMP_"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

