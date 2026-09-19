"""
tests/test_v7_feedback_loop.py
=============================================================================
Unit and Integration Tests for INFRA_V7_AUTONOMOUS_FEEDBACK_LOOP
Covers:
  1. Benchmark Calculation (Total / Average mốc V7).
  2. 3-Layer Clean Learning Filter (Views >= 10, CTR/AVD dual threshold, Semantic Niche Gate).
  3. V7 Pool Persistence & Deduplication (v7_winning_pool.json).
  4. B1.0 Candidate Retrieval & State Transition (PENDING -> CONSUMED).
  5. Rule 118 Zero-Mock Compliance & Resilient Fallback.
=============================================================================
"""
import os
import json
import tempfile
import pytest
from datetime import datetime, timezone

from scripts.b11_channel_analytics import (
    calculate_v7_benchmarks,
    harvest_v7_suggested_candidates
)
from scripts.b11_antigravity_engine import (
    load_v7_pool,
    save_v7_pool,
    update_v7_pool
)
from app.services.trend_engine_b1 import (
    fetch_pending_v7_candidates,
    mark_v7_candidate_consumed
)


# ==============================================================================
# 1. BENCHMARK CALCULATION TESTS
# ==============================================================================

def test_calculate_v7_benchmarks_empty():
    avg_ctr, avg_avd = calculate_v7_benchmarks([])
    assert avg_ctr == 0.0
    assert avg_avd == 0.0


def test_calculate_v7_benchmarks_sample():
    # Simulated suggested video rows similar to An Ong's Studio case study
    rows = [
        {"views": 100, "watch_minutes": 10.0, "watch_seconds": 600.0, "ctr_percent": 5.0},
        {"views": 200, "watch_minutes": 30.0, "watch_seconds": 1800.0, "ctr_percent": 10.0},
        {"views": 50,  "watch_minutes": 2.5,  "watch_seconds": 150.0,  "ctr_percent": 3.0}
    ]
    avg_ctr, avg_avd = calculate_v7_benchmarks(rows)
    # Average CTR = (5.0 + 10.0 + 3.0) / 3 = 6.0
    assert avg_ctr == 6.0
    # Total watch seconds = 600 + 1800 + 150 = 2550
    # Total views = 350 -> AVD = 2550 / 350 = 7.29s
    assert avg_avd == 7.29


# ==============================================================================
# 2. 3-LAYER CLEAN LEARNING GATE TESTS
# ==============================================================================

def test_v7_harvesting_three_layer_filter(monkeypatch):
    # Mock YouTube Analytics API response
    mock_analytics_data = {
        "rows": [
            # Candidate 1: Low views (< 10) -> Must be rejected by Layer 1
            ["ref_low_views", 5, 2.0, 400.0],
            # Candidate 2: High views, high AVD, high CTR, on-niche title -> Must PASS
            ["ref_winning_stoic", 50, 40.0, 360.0],
            # Candidate 3: High views, but low AVD -> Must be rejected by Layer 2
            ["ref_low_avd", 40, 5.0, 60.0],
            # Candidate 4: High views, high AVD, but off-niche entertainment -> Rejected by Layer 3
            ["ref_off_niche_music", 45, 30.0, 350.0]
        ]
    }

    # Mock video snippets lookup
    mock_snippets = {
        "ref_winning_stoic": {
            "title": "Stoic Philosophy and the Art of Quiet Resilience in Modern Life",
            "channelTitle": "Wisdom Daily"
        },
        "ref_off_niche_music": {
            "title": "Top 10 K-pop Dance Hits 2026 Official MV",
            "channelTitle": "MusicVibes"
        }
    }

    def mock_query_analytics(token, params):
        return mock_analytics_data

    def mock_query_youtube(token, endpoint, params):
        if endpoint == "videos":
            return {
                "items": [
                    {"id": vid, "snippet": snip}
                    for vid, snip in mock_snippets.items()
                ]
            }
        return {}

    import scripts.b11_channel_analytics as b11_ca
    monkeypatch.setattr(b11_ca, "query_youtube_analytics_api", mock_query_analytics)
    monkeypatch.setattr(b11_ca, "query_youtube_data_api", mock_query_youtube)

    candidates = harvest_v7_suggested_candidates(
        access_token="mock_token",
        winning_video_ids=["win_ep01"],
        market="EN",
        min_views=10
    )

    # Only Candidate 2 (ref_winning_stoic) should survive the 3-layer filter
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["referring_video_id"] == "ref_winning_stoic"
    assert cand["candidate_id"] == "V7_EN_ref_winning_stoic"
    assert cand["canonical_pillar"] == "indigenous_philosophy_stoicism"
    assert cand["status"] == "PENDING"
    assert cand["views_from_source"] == 50
    assert cand["avd_seconds"] > cand["benchmark_avg_avd"]


# ==============================================================================
# 3. V7 POOL PERSISTENCE & DEDUPLICATION TESTS
# ==============================================================================

def test_v7_pool_save_load_update(tmp_path, monkeypatch):
    test_pool_file = str(tmp_path / "v7_winning_pool.json")
    
    import scripts.b11_antigravity_engine as b11_ae
    monkeypatch.setattr(b11_ae, "V7_POOL_FILE", test_pool_file)

    # Initial load: empty
    pool = load_v7_pool("EN")
    assert pool["candidates"] == []

    # Insert new candidate
    cand1 = {
        "candidate_id": "V7_EN_vid1",
        "referring_video_id": "vid1",
        "referring_title": "The Collapse of Enron Explained",
        "ctr_percent": 8.5,
        "avd_seconds": 450.0,
        "views_from_source": 100,
        "status": "PENDING"
    }
    added = update_v7_pool("EN", [cand1])
    assert added == 1

    # Reload and verify
    reloaded = load_v7_pool("EN")
    assert len(reloaded["candidates"]) == 1
    assert reloaded["candidates"][0]["candidate_id"] == "V7_EN_vid1"

    # Try duplicate insert of vid1
    added_dup = update_v7_pool("EN", [cand1])
    assert added_dup == 0  # Deduplicated!
    assert len(load_v7_pool("EN")["candidates"]) == 1


# ==============================================================================
# 4. B1.0 STATE TRANSITION TESTS (PENDING -> CONSUMED)
# ==============================================================================

def test_v7_b1_candidate_consumption(tmp_path, monkeypatch):
    test_pool_file = str(tmp_path / "v7_winning_pool.json")

    sample_pool = {
        "market": "EN",
        "last_harvest_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [
            {
                "candidate_id": "V7_EN_vid100",
                "referring_video_id": "vid100",
                "referring_title": "How Theranos Faked Blood Tests",
                "ctr_percent": 12.4,
                "avd_seconds": 520.0,
                "views_from_source": 85,
                "canonical_pillar": "business_rise_fall",
                "status": "PENDING",
                "consumed_by_episode": None
            }
        ]
    }
    with open(test_pool_file, "w", encoding="utf-8") as f:
        json.dump(sample_pool, f)

    import app.services.trend_engine_b1 as b1_engine
    monkeypatch.setattr(b1_engine, "V7_POOL_FILE", test_pool_file)

    # 1. Fetch pending candidates
    pending = fetch_pending_v7_candidates("EN")
    assert len(pending) == 1
    assert pending[0]["candidate_id"] == "V7_EN_vid100"

    # 2. Mark candidate consumed by new episode
    success = mark_v7_candidate_consumed("V7_EN_vid100", "EN_EP0265_theranos_fraud")
    assert success is True

    # 3. Verify pending is now empty
    pending_after = fetch_pending_v7_candidates("EN")
    assert len(pending_after) == 0

    # 4. Check on-disk state
    with open(test_pool_file, "r", encoding="utf-8") as f:
        updated_data = json.load(f)
    consumed_cand = updated_data["candidates"][0]
    assert consumed_cand["status"] == "CONSUMED"
    assert consumed_cand["consumed_by_episode"] == "EN_EP0265_theranos_fraud"


# ==============================================================================
# 5. ZERO-MOCK FALLBACK TEST (RULE 118)
# ==============================================================================

def test_v7_zero_mock_empty_fallback(tmp_path, monkeypatch):
    # Non-existent file
    empty_file = str(tmp_path / "non_existent_pool.json")
    import app.services.trend_engine_b1 as b1_engine
    monkeypatch.setattr(b1_engine, "V7_POOL_FILE", empty_file)

    # Must return empty list cleanly with 0 synthetic mock items
    pending = fetch_pending_v7_candidates("EN")
    assert pending == []
