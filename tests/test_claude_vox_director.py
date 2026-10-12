#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_claude_vox_director.py
Comprehensive unit tests for ClaudeVoxDirector (Sentence-by-Sentence Master Prompt 2 Engine).
Rule 118, 120, 128, 130, 132 Compliant.
"""

import pytest
from unittest.mock import MagicMock
from app.services.claude_vox_director import (
    ClaudeVoxDirector,
    split_story_into_sentences,
    load_master_prompt_2,
    MASTER_DIRECTOR_SYSTEM_PROMPT,
)


def test_split_story_into_sentences_asian():
    text = (
        "=== ACT I ===\n"
        "2026년 10월 7일, 주요 항공우주 기업이 차세대 AI 칩 조달을 위해 400억달러 규모의 자금 조달을 추진한다는 보도가 나왔습니다. "
        "주요 경제 매체들이 거의 동시에 같은 거래를 전했습니다. "
        "바로 그 시점에 해당 기업의 5년물 CDS, 즉 부도위험 보험료는 약 197.3bp까지 치솟았습니다."
    )
    sents = split_story_into_sentences(text)
    assert len(sents) == 3
    assert "400억달러" in sents[0]
    assert "197.3bp" in sents[2]


def test_split_story_into_sentences_english():
    text = (
        "May, 1925. Paris. "
        "A well-dressed man reads a newspaper story about the steel tower rusting and costing a fortune to maintain. "
        "His name is Victor. "
        "He has an idea."
    )
    sents = split_story_into_sentences(text)
    assert len(sents) >= 4
    assert sents[0] == "May, 1925."


def test_load_master_prompt_2_structure():
    prompt = load_master_prompt_2()
    assert "Editorial Art Director" in prompt
    assert "#f4ece1" in prompt
    assert "pure solid white" in prompt
    assert "editorial_title" in prompt
    assert "supporting_exhibits" in prompt
    assert "animation_cue" in prompt


def test_claude_vox_director_fallback_sizing_and_invariants():
    director = ClaudeVoxDirector()
    mock_gateway = MagicMock()
    # Simulate network timeout or 503 error on gateway
    mock_gateway.call_llm.side_effect = Exception("HTTP 503 Service Unavailable")

    story = (
        "2026년 10월 7일, 차세대 AI 가속기 구매를 위해 400억달러 규모의 자금 조달이 승인되었습니다. "
        "그 직후 5년물 CDS 부도위험 보험료는 197.3bp까지 폭등했습니다."
    )
    scenes = director.plan_storyboard(story, market="KR", gateway=mock_gateway)
    assert len(scenes) == 2

    for sc in scenes:
        # Step 1: Minimalist paper background (#f4ece1), zero 3D rooms
        assert sc["background_canvas"]["hex"] == "#f4ece1"
        assert sc["background_canvas"]["key"].startswith("bg_paper_canvas_")

        # Step 2: Exact output schema
        assert sc["core_idea"]
        assert sc["editorial_title"]
        # Enforce 1-4 words in ALL CAPS
        assert len(sc["editorial_title"].split()) <= 4
        assert sc["visual_metaphor"]

        # Step 3: Delicate scale & Pure solid white background
        hero = sc["hero_cutout"]
        assert 18 <= hero["width_pct"] <= 25
        assert hero["backdrop"] == "#FFFFFF"
        assert "pure solid white background" in hero["prompt"].lower()
        assert "--no 3d rooms" in hero["prompt"].lower()

        exhibits = sc["supporting_exhibits"]
        assert len(exhibits) >= 1
        for ex in exhibits:
            # Strictly 14% - 18% width
            assert 14 <= ex["width_pct"] <= 18
            assert ex["backdrop"] == "#FFFFFF"
            assert "pure solid white background" in ex["prompt"].lower()
            assert ex["entrance_type"] in ("slide_in_deal", "delicate_tack", "stamp_slam")
            assert isinstance(ex["has_pin"], bool)
            assert isinstance(ex["has_tape"], bool)

        assert sc["yarn_connection"]["has_connection"] is True
        assert sc["yarn_connection"]["color"] == "#dc2626"
        assert sc["stamp"]["text"]
        assert sc["animation_cue"]["type"] in ("marker_highlight", "stamp_slam")
        assert sc["animation_cue"]["highlight_color"] == "#ffe600"


def test_claude_vox_director_successful_json_parsing():
    director = ClaudeVoxDirector()
    mock_gateway = MagicMock()
    mock_json_response = """[
      {
        "scene_index": 1,
        "sentence": "November 24, 1971. A passenger in a dark suit buys a one-way flight coupon.",
        "core_idea": "The initial hijack transaction",
        "editorial_title": "FLIGHT 305 COUPON",
        "visual_metaphor": "Northwest Orient airline ticket coupon",
        "main_subject_cutout": {
          "name": "fg_hero_01_ticket",
          "label": "TICKET #1124",
          "width_pct": 22,
          "prompt": "Hand-cut black and white halftone photograph cutout of vintage airline ticket coupon, rough scissor edges, isolated on pure solid white background (#FFFFFF) --no 3D rooms"
        },
        "supporting_exhibits": [
          {
            "name": "fg_exhibit_01_boarding_pass",
            "label": "BOARDING PASS",
            "width_pct": 16,
            "rotation": -6,
            "has_pin": true,
            "has_tape": false,
            "entrance_type": "slide_in_deal",
            "has_marker_highlight": true,
            "highlight_text": "FLIGHT 305",
            "prompt": "An authentic paper boarding pass cutout, isolated on pure solid white background (#FFFFFF) --no 3D rooms"
          }
        ],
        "yarn_connection": {
          "has_connection": true,
          "from_point": {"x": 35, "y": 50},
          "to_point": {"x": 65, "y": 50},
          "color": "#dc2626"
        },
        "stamp": {"text": "VERIFIED", "color": "#dc2626"},
        "animation_cue": {"type": "marker_highlight", "trigger_keyword": "ticket", "highlight_color": "#ffe600"}
      }
    ]"""
    mock_gateway.call_llm.return_value = mock_json_response

    story = "A passenger in a dark suit buys a one-way flight coupon."
    scenes = director.plan_storyboard(story, market="US", gateway=mock_gateway)
    assert len(scenes) == 1
    sc = scenes[0]
    assert sc["editorial_title"] == "FLIGHT 305 COUPON"
    assert sc["hero_cutout"]["width_pct"] == 22
    assert sc["supporting_exhibits"][0]["width_pct"] == 16
    assert sc["supporting_exhibits"][0]["has_marker_highlight"] is True
    assert sc["background_canvas"]["hex"] == "#f4ece1"
