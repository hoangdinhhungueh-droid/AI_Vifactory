#!/usr/bin/env python3
"""
tests/test_b15_traffic_bridge.py - Verifies that B1.5 competitor recon generates
traffic bridges to eliminate the YouTube 0-view cold start.
"""

import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.competitor_recon_b15 import build_intel_card, QuotaTracker


def test_build_intel_card_generates_traffic_bridges(tmp_path):
    mock_benchmarks = [
        {
            "video_id": "test_vid_001",
            "title": "Top Secret Forensic Investigation 1",
            "channel": "Forensic Files Daily",
            "views": 250000,
            "vph": 1250.5,
            "tags": ["forensic", "investigation", "audit", "offshore", "money", "flow"],
        },
        {
            "video_id": "test_vid_002",
            "title": "The Collapse of Megacorp 2",
            "channel": "Economy Deep Dive",
            "views": 180000,
            "vph": 980.2,
            "tags": ["collapse", "megacorp", "scandal"],
        },
        {
            "video_id": "test_vid_003",
            "title": "Shadow Banking Breakdown 3",
            "channel": "Investigative Reports",
            "views": 120000,
            "vph": 740.0,
            "tags": ["banking", "shadow", "dossier"],
        },
        {
            "video_id": "test_vid_004",
            "title": "Outlier Video 4",
            "channel": "Channel 4",
            "views": 50000,
            "vph": 200.0,
            "tags": ["extra"],
        }
    ]

    mock_anatomy = {
        "audience_wishlist_topics": ["Forensic paper trail proof"],
        "ai_slop_redlines": ["Avoid robotic narration"],
        "transposition_opportunities": {},
        "target_audience_profile": "investigative documentary viewers",
    }

    quota = QuotaTracker(state_path=tmp_path / "quota.json")

    card = build_intel_card(
        task_id="TEST_TASK_001",
        target_keyword="shadow banking audit",
        niche="forensic_finance",
        market="EN",
        selected=mock_benchmarks,
        gaps=[],
        quota=quota,
        competitor_narrative_anatomy=mock_anatomy,
    )

    assert "traffic_bridges" in card, "Expected 'traffic_bridges' field in intel card"
    bridges = card["traffic_bridges"]

    # Maximum 3 traffic bridges from top benchmarks
    assert len(bridges) == 3, f"Expected 3 traffic bridges, got {len(bridges)}"

    # First bridge checks
    first = bridges[0]
    assert first["video_id"] == "test_vid_001"
    assert first["title"] == "Top Secret Forensic Investigation 1"
    assert first["channel"] == "Forensic Files Daily"
    assert first["url"] == "https://www.youtube.com/watch?v=test_vid_001"
    assert len(first["seed_tags"]) <= 5
    assert first["vph"] == 1250.5
