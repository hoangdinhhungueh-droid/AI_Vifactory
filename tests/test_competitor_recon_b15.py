"""Tests for B1.5 competitor recon (app/services/competitor_recon_b15.py).

Pure-logic coverage: selection formula, comment prefilter, market detection,
quota accounting, card assembly. Network calls are not exercised here; the
live end-to-end run is verified separately against the real YouTube API.
"""
import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.competitor_recon_b15 import (  # noqa: E402
    COMMENT_MIN_LENGTH,
    QUOTA_DAILY_UNITS,
    QuotaTracker,
    age_days,
    build_intel_card,
    filter_comment_gaps,
    filter_comment_tri_buckets,
    is_spam,
    market_of,
    select_competitors,
    velocity,
    calculate_vph,
    calculate_vs_ratio,
    calculate_outlier_score,
    prune_forensic_context,
    youtube_channel_subscribers,
    SMALL_CHANNEL_SUB_CEILING,
    OUTLIER_VS_RATIO_MIN,
    parse_relative_time_to_dt,
)


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def candidate(vid, views, days_old, comments=500, channel_subscribers=None, channel_id=None):
    c = {
        "video_id": vid,
        "channel": f"ch-{vid}",
        "channel_id": channel_id or f"cid-{vid}",
        "title": f"title-{vid}",
        "published_at": iso_days_ago(days_old),
        "views": views,
        "comments": comments,
        "thumbnails": {},
    }
    if channel_subscribers is not None:
        c["channel_subscribers"] = channel_subscribers
    return c


class TestMarketDetection:
    @pytest.mark.parametrize("task_id,expected", [
        ("en-enron-collapse-ep006", "en"),
        ("jp-toyota-recall-ep002", "jp"),
        ("kr-samsung-ep011", "kr"),
        ("EN-UPPER-ep001", "en"),
        ("noprefix", "en"),
        ("zz-unknown-market-ep001", "en"),
    ])
    def test_prefix(self, task_id, expected):
        assert market_of(task_id) == expected


class TestVelocity:
    def test_views_per_day(self):
        assert velocity(1000, iso_days_ago(2)) == 500
        assert velocity(500, iso_days_ago(0)) == 500

    def test_malformed_date_returns_none(self):
        assert velocity(1000, "not-a-date") is None
        assert age_days("") is None


class TestSelectionFormula:
    def test_group1_takes_two_highest_velocity(self):
        cands = [
            candidate("slow", 1_000_000, 2000),
            candidate("fastest", 5_000_000, 100),
            candidate("second", 2_000_000, 100),
        ]
        g1, _ = select_competitors(cands)
        assert [c["video_id"] for c in g1] == ["fastest", "second"]
        assert all(c["selection_group"] == "all_time_top_velocity" for c in g1)

    def test_group2_window_and_comment_floor(self):
        cands = [
            candidate("anchor1", 90_000_000, 30),
            candidate("anchor2", 80_000_000, 30),
            candidate("too_new", 500_000, 45),
            candidate("too_old", 500_000, 800),
            candidate("in_window", 500_000, 200),
            candidate("few_comments", 500_000, 200, comments=12),
        ]
        _, g2 = select_competitors(cands)
        assert [c["video_id"] for c in g2] == ["in_window"]
        assert g2[0]["selection_group"] == "recent_90_365_days"

    def test_window_boundaries_are_inclusive(self):
        cands = [candidate("a", 10_000_000, 5000), candidate("b", 8_000_000, 4000),
                 candidate("lo", 100, 90), candidate("hi", 90, 365)]
        _, g2 = select_competitors(cands)
        assert {c["video_id"] for c in g2} == {"lo", "hi"}

    def test_no_group_overlap(self):
        cands = [candidate(f"v{i}", 1_000_000 - i, 200) for i in range(8)]
        g1, g2 = select_competitors(cands)
        assert not ({c["video_id"] for c in g1} & {c["video_id"] for c in g2})

    def test_undatable_candidates_dropped(self):
        cands = [candidate("ok", 1000, 100),
                 {"video_id": "bad", "channel": "c", "title": "t", "published_at": "garbage"}]
        g1, g2 = select_competitors(cands)
        assert {c["video_id"] for c in g1 + g2} == {"ok"}


class TestCommentPrefilter:
    def test_keeps_liked_question(self):
        c = [{"text": "Why did the auditors never flag the offshore entities here?",
              "likes": 900, "author": "a", "published_at": None}]
        assert len(filter_comment_gaps(c)) == 1

    def test_drops_short_comment(self):
        text = "why though"
        assert len(text) < COMMENT_MIN_LENGTH
        c = [{"text": text, "likes": 5000, "author": "a", "published_at": None}]
        assert filter_comment_gaps(c) == []

    def test_drops_low_likes(self):
        c = [{"text": "Why was this never explained properly in the filings?",
              "likes": 1, "author": "a", "published_at": None}]
        assert filter_comment_gaps(c) == []

    def test_drops_non_question(self):
        c = [{"text": "Excellent documentary, the production quality is outstanding.",
              "likes": 900, "author": "a", "published_at": None}]
        assert filter_comment_gaps(c) == []

    @pytest.mark.parametrize("spam", [
        "Why is this happening? check out my channel https://spam.example/x",
        "How did they do it, subscribe to my page for more www.spam.example",
        "why so bad 🔥🔥🔥🔥🔥🔥",
    ])
    def test_drops_spam(self, spam):
        assert is_spam(spam)
        c = [{"text": spam, "likes": 900, "author": "a", "published_at": None}]
        assert filter_comment_gaps(c) == []

    def test_sorted_by_likes_desc(self):
        c = [
            {"text": "Why was the pension fund wiped out so completely here?", "likes": 10,
             "author": "a", "published_at": None},
            {"text": "How were the swaps kept off the balance sheet for years?", "likes": 999,
             "author": "b", "published_at": None},
        ]
        assert [g["likes"] for g in filter_comment_gaps(c)] == [999, 10]


class TestQuotaTracker:
    def test_charges_per_endpoint(self, tmp_path):
        q = QuotaTracker(state_path=tmp_path / "q.json")
        q.charge("search")
        q.charge("videos")
        q.charge("commentThreads")
        assert q.spent == 102

    def test_persists_within_same_day(self, tmp_path):
        p = tmp_path / "q.json"
        QuotaTracker(state_path=p).charge("search")
        assert QuotaTracker(state_path=p).spent == 100

    def test_ignores_state_from_another_day(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text(json.dumps({"date": "1999-01-01", "spent": 9999}))
        assert QuotaTracker(state_path=p).spent == 0

    def test_corrupt_state_starts_clean(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text("{not json")
        assert QuotaTracker(state_path=p).spent == 0

    def test_fallback_trips_at_eighty_percent(self, tmp_path):
        q = QuotaTracker(state_path=tmp_path / "q.json")
        q.spent = int(QUOTA_DAILY_UNITS * 0.79)
        assert not q.should_fallback()
        q.spent = int(QUOTA_DAILY_UNITS * 0.80)
        assert q.should_fallback()


class TestIntelCard:
    def _card(self, tmp_path, transcript_status="captions", thumb="/tmp/t.jpg"):
        c = candidate("v1", 1_000_000, 100)
        has_text = transcript_status != "unavailable"
        c.update({
            "avg_views_per_day": 10_000,
            "age_days": 100,
            "selection_group": "all_time_top_velocity",
            "duration": "PT19M4S",
            "likes": 40_000,
            "tags": ["enron"],
            "description_head": "desc",
            "transcript": {
                "status": transcript_status,
                "text": "opening line" if has_text else None,
                "source": "youtube-transcript-api" if has_text else None,
            },
            "thumbnail_path": thumb,
        })
        gaps = [{"video_id": "v1", "text": "Why was the audit signed off?",
                 "likes": 500, "author": "a", "published_at": None}]
        return build_intel_card("en-x-ep001", "kw", "niche", "en", [c], gaps,
                               QuotaTracker(state_path=tmp_path / "q.json"))

    def test_schema_keys(self, tmp_path):
        assert set(self._card(tmp_path)) == {
            "task_id", "target_keyword", "niche", "market", "traffic_bridges",
            "competitor_benchmarks", "audience_comment_gaps",
            "_b2_to_synthesize", "collection_meta",
            "transposition_opportunities", "ai_slop_redlines", "audience_wishlist_topics",
        }

    def test_no_placeholder_verdicts_emitted(self, tmp_path):
        card = self._card(tmp_path)
        blob = json.dumps({k: v for k, v in card.items() if k != "_b2_to_synthesize"})
        for forbidden in ("critical_flaw", "recommended_10x_angle",
                          "golden_facts_to_keep", "TBD", "N/A"):
            assert forbidden not in blob

    def test_b2_contract_is_declared(self, tmp_path):
        assert "recommended_10x_angle" in self._card(tmp_path)["_b2_to_synthesize"]

    def test_comment_kept_verbatim(self, tmp_path):
        gap = self._card(tmp_path)["audience_comment_gaps"][0]
        assert gap["comment_verbatim"] == "Why was the audit signed off?"
        assert gap["likes_count"] == 500

    def test_meta_counts_reflect_capture(self, tmp_path):
        meta = self._card(tmp_path)["collection_meta"]
        assert meta["transcripts_captured"] == 1
        assert meta["thumbnails_captured"] == 1

    def test_unavailable_transcript_recorded_not_faked(self, tmp_path):
        card = self._card(tmp_path, transcript_status="unavailable", thumb=None)
        bench = card["competitor_benchmarks"][0]
        assert bench["transcript_status"] == "unavailable"
        assert bench["transcript_head"] is None
        assert bench["thumbnail_path"] is None
        assert card["collection_meta"]["transcripts_captured"] == 0
        assert card["collection_meta"]["thumbnails_captured"] == 0

    def test_timestamp_is_timezone_aware(self, tmp_path):
        ts = self._card(tmp_path)["collection_meta"]["collected_at"]
        assert datetime.fromisoformat(ts).tzinfo is not None


class TestTubeRadarOutlierMetrics:
    def test_calculate_vph(self):
        # 10,000 views on a video published 10 hours ago -> ~1000 VPH
        vph = calculate_vph(10_000, iso_days_ago(1))  # 24 hours ago
        assert vph is not None
        assert 400 <= vph <= 430

    def test_calculate_vs_ratio(self):
        # 100,000 views on a 2,000 sub channel -> 50.0x ratio
        ratio = calculate_vs_ratio(100_000, 2_000)
        assert ratio == 50.0

        # Floor protection: 0 subs uses floor of 100
        ratio_zero = calculate_vs_ratio(10_000, 0)
        assert ratio_zero == 100.0

    def test_calculate_outlier_score_prefers_small_channels(self):
        # Small channel (2k subs, 100k views, published 5 days ago)
        score_small = calculate_outlier_score(100_000, 2_000, iso_days_ago(5))

        # Huge channel (2M subs, 200k views, published 5 days ago)
        score_huge = calculate_outlier_score(200_000, 2_000_000, iso_days_ago(5))

        assert score_small > score_huge
        assert score_small > 100.0  # High outlier signal
        assert score_huge < 1.0     # Mediocre/underperforming signal


class TestOutlierCompetitorSelection:
    def test_prefers_small_channel_with_high_vs_ratio(self):
        # Candidate 1: Micro channel breakout (1,500 subs, 120k views, 5 days old -> R_vs = 80x)
        c_micro = candidate("micro_viral", 120_000, 5, channel_subscribers=1_500)

        # Candidate 2: Small channel breakout (20,000 subs, 180k views, 10 days old -> R_vs = 9x)
        c_small = candidate("small_viral", 180_000, 10, channel_subscribers=20_000)

        # Candidate 3: Mega channel (5,000,000 subs, 500k views, 10 days old -> R_vs = 0.1x)
        c_mega = candidate("mega_normal", 500_000, 10, channel_subscribers=5_000_000)

        # Candidate 4: Old historical giant (3,000,000 subs, 10M views, 500 days old)
        c_old_giant = candidate("old_giant", 10_000_000, 500, channel_subscribers=3_000_000)

        cands = [c_micro, c_small, c_mega, c_old_giant]
        g1, g2 = select_competitors(cands)

        # Group 1 must contain the small channel outliers
        g1_ids = [c["video_id"] for c in g1]
        assert "micro_viral" in g1_ids
        assert "small_viral" in g1_ids
        assert all(c["selection_group"] == "small_channel_outlier_surge" for c in g1)

        # Group 2 must contain all-time macro benchmarks without overlap
        g2_ids = [c["video_id"] for c in g2]
        assert "old_giant" in g2_ids
        assert all(c["selection_group"] == "all_time_top_velocity" for c in g2)
        assert set(g1_ids).isdisjoint(set(g2_ids))

    def test_enriched_fields_in_selected_candidates(self):
        c_micro = candidate("micro", 50_000, 3, channel_subscribers=2_000)
        cands = [c_micro]
        g1, _ = select_competitors(cands)
        c = g1[0]
        assert "vph" in c
        assert "v_s_ratio" in c
        assert "outlier_score" in c
        assert c["v_s_ratio"] == 25.0
        assert c["channel_subscribers"] == 2000


class TestCommentTriBuckets:
    def test_categorizes_into_three_buckets(self):
        raw_comments = [
            {"text": "Why did nobody explain what happened to the missing fund balance?", "likes": 50},
            {"text": "This video is totally biased and wrong about the legal timeline!", "likes": 30},
            {"text": "Best video on this topic, amazing analysis and masterpiece explanation!", "likes": 40},
            {"text": "Tại sao kiểm toán không phát hiện ra lỗ hổng này sớm hơn?", "likes": 25},
            {"text": "Sai rồi nhé, số liệu đoạn 5:30 bị chém gió hoàn toàn", "likes": 15},
            {"text": "Quá hay và quá cuốn, phân tích cực kỳ chất lượng!", "likes": 60},
        ]
        buckets = filter_comment_tri_buckets(raw_comments, min_likes=5)
        assert len(buckets["unanswered_questions"]) == 2
        assert len(buckets["skepticism_critique"]) == 2
        assert len(buckets["praise_resonance"]) == 2

    def test_filter_comment_gaps_returns_unanswered(self):
        raw_comments = [
            {"text": "How did the executive bypass compliance without detection?", "likes": 100},
            {"text": "I loved this video so much!", "likes": 10},
        ]
        gaps = filter_comment_gaps(raw_comments, min_likes=5)
        assert len(gaps) == 1
        assert "How did" in gaps[0]["text"]


class TestContextPruningAndTokenGuard:
    def test_prune_context_respects_token_caps(self):
        # Create candidate with excessively long transcript (>5000 chars)
        huge_tr = "Sentence about financial crime and forensic evidence. " * 200
        cand = candidate("c1", 100_000, 10, channel_subscribers=2000)
        cand["transcript"] = {"text": huge_tr, "status": "captions", "source": "test"}
        cand["vph"] = 400.0
        cand["v_s_ratio"] = 50.0
        cand["outlier_score"] = 120.0

        # 30 long comments
        comments = [{"text": f"Why did event {i} happen? " * 10, "likes": i} for i in range(30)]

        bench_text, comm_text = prune_forensic_context("Enron Collapse", "EN", "Business", [cand], comments)

        # Transcripts must be truncated per video
        assert len(bench_text) < 3000
        # Comments must be capped to MAX_COMMENTS_IN_PROMPT (15)
        assert comm_text.count("- [") <= 15


class TestChannelSubscribersBatchEndpoint:
    def test_parses_subscriber_counts(self, monkeypatch):
        # Mock _api_get to return YouTube channels API structure
        def mock_api_get(endpoint, params, quota):
            assert endpoint == "channels"
            assert params["part"] == "statistics"
            return {
                "items": [
                    {"id": "cid-1", "statistics": {"subscriberCount": "15200", "hiddenSubscriberCount": False}},
                    {"id": "cid-2", "statistics": {"subscriberCount": "0", "hiddenSubscriberCount": True}},
                ]
            }

        import app.services.competitor_recon_b15 as b15_mod
        monkeypatch.setattr(b15_mod, "_api_get", mock_api_get)

        quota = QuotaTracker()
        subs = youtube_channel_subscribers("fake-key", ["cid-1", "cid-2"], quota)
        assert subs["cid-1"] == 15200
        assert subs["cid-2"] == 0


class TestRelativeTimeAndZeroQuotaResilience:
    def test_parse_relative_time_units(self):
        assert parse_relative_time_to_dt("") is None
        assert parse_relative_time_to_dt("not a date") is None

        now = datetime.now(timezone.utc)
        dt_hr = parse_relative_time_to_dt("8 hours ago")
        assert dt_hr is not None
        assert abs((now - dt_hr).total_seconds() - 8 * 3600) < 5

        dt_day = parse_relative_time_to_dt("2 days ago")
        assert dt_day is not None
        assert abs((now - dt_day).total_seconds() - 2 * 86400) < 5

        dt_wk = parse_relative_time_to_dt("3 weeks ago")
        assert dt_wk is not None
        assert abs((now - dt_wk).total_seconds() - 21 * 86400) < 5

        dt_mo = parse_relative_time_to_dt("1 month ago")
        assert dt_mo is not None
        assert abs((now - dt_mo).total_seconds() - 30 * 86400) < 5

        dt_yr = parse_relative_time_to_dt("2 years ago")
        assert dt_yr is not None
        assert abs((now - dt_yr).total_seconds() - 730 * 86400) < 5

        dt_yest = parse_relative_time_to_dt("yesterday")
        assert dt_yest is not None
        assert abs((now - dt_yest).total_seconds() - 86400) < 5

    def test_age_days_and_vph_with_relative_strings(self):
        assert age_days("8 hours ago") == 1
        assert age_days("3 days ago") == 3
        vph = calculate_vph(1000, "8 hours ago")
        assert vph is not None
        assert 100 <= vph <= 150

    def test_build_intel_card_safe_missing_fields(self):
        quota = QuotaTracker()
        raw_cand = {
            "video_id": "test_123",
            "title": "Raw Candidate Title",
            "views": 5000,
        }
        card = build_intel_card("task_001", "keyword", "niche", "EN", [raw_cand], [], quota)
        assert len(card["competitor_benchmarks"]) == 1
        b = card["competitor_benchmarks"][0]
        assert b["video_id"] == "test_123"
        assert b["age_days"] == 1
        assert b["selection_group"] == "competitor_benchmark"
        assert b["transcript_status"] == "unavailable"


