"""Hermetic tests for B1.5 Competitor Recon (app/services/competitor_recon_b15.py).

Khong goi mang: moi test stub call_haiku hoac chi kiem tra ham thuan.
"""

import json
from datetime import datetime

import pytest

from app.services import competitor_recon_b15 as b15


def _benchmarks():
    return [
        {
            "video_id": "vidA",
            "channel": "ColdFusion",
            "title": "Enron - The Biggest Fraud in History",
            "views": 8649522,
            "comments": 12034,
            "published_at": "2019-08-30T11:30:00Z",
            "avg_views_per_day": 3388,
            "hook_strategy": "",
            "critical_flaw": "",
        },
        {
            "video_id": "vidB",
            "channel": "Company Man",
            "title": "The Enron Scandal - A Simple Overview",
            "views": 1890000,
            "comments": 3100,
            "published_at": "2017-01-05T00:00:00Z",
            "avg_views_per_day": 575,
            "hook_strategy": "",
            "critical_flaw": "",
        },
    ]


def _gaps():
    return [
        {"text": "I could never figure out how they made money", "likes": 2483, "author": "u1"},
        {"text": "why did the auditors sign off on this", "likes": 91, "author": "u2"},
    ]


def _haiku_reply():
    return {
        "competitor_analysis": [
            {"video_id": "vidA", "hook_strategy": "Superlative framing", "critical_flaw": "No mechanism explanation"},
            {"video_id": "vidB", "hook_strategy": "Accessible entry point", "critical_flaw": "Omits SPEs"},
        ],
        "golden_facts_to_keep": ["Buffett could not model Enron revenue"],
        "audience_comment_gaps": [
            {
                "unanswered_question": "I could never figure out how they made money",
                "viewer_frustration": "Wants the revenue mechanism, not just the verdict",
            }
        ],
        "recommended_10x_angle": {
            "hook_proposal": "How mark-to-market turned imaginary profit into real loss",
            "core_mechanism_to_clarify": "SPEs and revenue recognition",
            "differentiator": "Forensic clarity instead of oversimplification",
        },
    }


# ---------- filter_comment_gaps ----------

def test_gap_filter_requires_both_likes_and_keyword():
    comments = [
        {"text": "why did nobody stop this", "likes": 10, "author": "a"},
        {"text": "why did nobody stop this", "likes": 1, "author": "b"},
        {"text": "great video thanks", "likes": 500, "author": "c"},
    ]
    gaps = b15.filter_comment_gaps(comments, min_likes=3)
    assert len(gaps) == 1
    assert gaps[0]["likes"] == 10


# ---------- build_synth_prompt ----------

def test_prompt_carries_real_metrics_and_verbatim_comments():
    p = b15.build_synth_prompt("Enron Scandal Explained", "Corporate Crime", _benchmarks(), _gaps())
    assert "video_id=vidA" in p
    assert "views=8649522" in p
    assert "views_per_day=3388" in p
    assert "[2483 likes] I could never figure out how they made money" in p
    assert "TARGET KEYWORD: Enron Scandal Explained" in p


def test_prompt_flattens_newlines_in_comments():
    gaps = [{"text": "why\nis\tthis", "likes": 5, "author": "a"}]
    p = b15.build_synth_prompt("k", "n", _benchmarks(), gaps)
    assert "[5 likes] why is this" in p


def test_prompt_survives_empty_gaps():
    p = b15.build_synth_prompt("k", "n", _benchmarks(), [])
    assert "none passed the gap filter" in p


# ---------- apply_haiku_synthesis ----------

def test_synthesis_merges_real_haiku_output(monkeypatch):
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: _haiku_reply())
    card = {"competitor_benchmarks": _benchmarks()}
    out = b15.apply_haiku_synthesis(card, "Enron", "Corporate Crime", _gaps())

    assert out["synthesis_status"] == "haiku_ok"
    assert out["synthesis_model"] == b15.HAIKU_MODEL
    by_id = {b["video_id"]: b for b in out["competitor_benchmarks"]}
    assert by_id["vidA"]["critical_flaw"] == "No mechanism explanation"
    assert by_id["vidB"]["hook_strategy"] == "Accessible entry point"
    assert out["golden_facts_to_keep"] == ["Buffett could not model Enron revenue"]
    assert out["recommended_10x_angle"]["differentiator"].startswith("Forensic")


def test_synthesis_maps_likes_back_to_the_source_comment(monkeypatch):
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: _haiku_reply())
    card = {"competitor_benchmarks": _benchmarks()}
    out = b15.apply_haiku_synthesis(card, "Enron", "Corporate Crime", _gaps())
    assert out["audience_comment_gaps"][0]["likes_count"] == 2483


def test_synthesis_failure_is_flagged_not_papered_over(monkeypatch):
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: None)
    card = {"competitor_benchmarks": _benchmarks()}
    out = b15.apply_haiku_synthesis(card, "Enron", "Corporate Crime", _gaps())
    assert out["synthesis_status"] == "haiku_failed"
    assert out["competitor_benchmarks"][0]["critical_flaw"] == ""
    assert "synthesis_model" not in out


def test_synthesis_skipped_when_no_benchmarks(monkeypatch):
    called = []
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: called.append(1))
    out = b15.apply_haiku_synthesis({"competitor_benchmarks": []}, "k", "n", [])
    assert out["synthesis_status"] == "skipped_no_benchmarks"
    assert called == []


def test_unknown_video_id_from_model_does_not_corrupt_benchmarks(monkeypatch):
    reply = _haiku_reply()
    reply["competitor_analysis"] = [
        {"video_id": "hallucinated", "hook_strategy": "x", "critical_flaw": "y"}
    ]
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: reply)
    card = {"competitor_benchmarks": _benchmarks()}
    out = b15.apply_haiku_synthesis(card, "k", "n", _gaps())
    ids = {b["video_id"] for b in out["competitor_benchmarks"]}
    assert ids == {"vidA", "vidB"}
    assert all(b["critical_flaw"] == "" for b in out["competitor_benchmarks"])


# ---------- synthesize_intel_card ----------

def test_card_no_longer_ships_placeholder_strings(monkeypatch):
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: _haiku_reply())
    competitors = [
        {
            "video_id": "vidA",
            "channel": "ColdFusion",
            "title": "Enron - The Biggest Fraud in History",
            "views": 8649522,
            "comments": 12034,
            "published_at": "2019-08-30T11:30:00Z",
        }
    ]
    card = b15.synthesize_intel_card("en-enron-ep006", "Enron", "Corporate Crime", competitors, _gaps())
    blob = json.dumps(card)
    assert "TBD by Haiku synthesis" not in blob
    assert "Extracted from comment" not in blob
    assert "Analyze first 15s of" not in blob
    assert card["synthesis_status"] == "haiku_ok"


def test_use_haiku_false_skips_the_model_call(monkeypatch):
    called = []
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: called.append(1))
    card = b15.synthesize_intel_card("en-x-ep001", "k", "n", [], [], use_haiku=False)
    assert card["synthesis_status"] == "disabled"
    assert called == []


def test_timestamp_is_timezone_aware():
    card = b15.synthesize_intel_card("en-x-ep001", "k", "n", [], [], use_haiku=False)
    ts = datetime.fromisoformat(card["timestamp"])
    assert ts.tzinfo is not None


def test_velocity_uses_publish_age(monkeypatch):
    monkeypatch.setattr(b15, "call_haiku", lambda *a, **k: None)
    competitors = [
        {
            "video_id": "vidA",
            "channel": "c",
            "title": "t",
            "views": 3650000,
            "comments": 1,
            "published_at": "2019-08-30T11:30:00Z",
        }
    ]
    card = b15.synthesize_intel_card("en-x-ep001", "k", "n", competitors, [])
    vpd = card["competitor_benchmarks"][0]["avg_views_per_day"]
    assert 1000 < vpd < 2000


# ---------- call_haiku guard ----------

def test_call_haiku_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert b15.call_haiku("p", "s", b15.SYNTH_SCHEMA) is None


def test_synth_schema_is_strict():
    assert b15.SYNTH_SCHEMA["additionalProperties"] is False
    for key in ("competitor_analysis", "golden_facts_to_keep", "audience_comment_gaps", "recommended_10x_angle"):
        assert key in b15.SYNTH_SCHEMA["required"]
