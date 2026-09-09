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
    is_spam,
    market_of,
    select_competitors,
    velocity,
)


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def candidate(vid, views, days_old, comments=500):
    return {
        "video_id": vid,
        "channel": f"ch-{vid}",
        "title": f"title-{vid}",
        "published_at": iso_days_ago(days_old),
        "views": views,
        "comments": comments,
        "thumbnails": {},
    }


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
        assert velocity(1000, iso_days_ago(10)) == pytest.approx(100, rel=0.2)

    def test_same_day_upload_does_not_divide_by_zero(self):
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
            "task_id", "target_keyword", "niche", "market",
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
