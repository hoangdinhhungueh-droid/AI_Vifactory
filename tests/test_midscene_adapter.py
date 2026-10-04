#!/usr/bin/env python3
"""
tests/test_midscene_adapter.py - Unit tests for MidsceneAdapter Record-to-Replay caching engine.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.drivers.midscene_adapter import MidsceneAdapter, CachedActionRecord


def test_midscene_cache_key_generation():
    adapter = MidsceneAdapter(cache_file="config/test_midscene_cache.json")
    key = adapter._get_cache_key("https://gemini.google.com/app?hl=en#prompt", "send_button")
    assert key == "https://gemini.google.com/app::send_button"


def test_midscene_record_to_replay_cache(tmp_path):
    cache_file = tmp_path / "midscene_cache.json"
    adapter = MidsceneAdapter(cache_file=cache_file)

    # Mock page
    mock_page = MagicMock()
    mock_page.url = "https://studio.youtube.com/channel/XYZ"

    mock_elem = MagicMock()
    mock_elem.is_visible.return_value = True

    def query_selector_side_effect(sel):
        if sel == 'button[aria-label="Create"]':
            return mock_elem
        return None

    mock_page.query_selector.side_effect = query_selector_side_effect

    # 1. First run: Discovery phase
    heuristic = ['button[aria-label="Create"]', 'button:has-text("Create")']
    resolved_sel = adapter.resolve_selector(
        mock_page,
        semantic_target="create_button",
        heuristic_selectors=heuristic,
        timeout_ms=500
    )

    assert resolved_sel == 'button[aria-label="Create"]'
    assert cache_file.exists()

    # 2. Second run: Replay phase from cache ($0 cost)
    adapter2 = MidsceneAdapter(cache_file=cache_file)
    mock_page_replay = MagicMock()
    mock_page_replay.url = "https://studio.youtube.com/channel/XYZ"
    mock_elem_replay = MagicMock()
    mock_elem_replay.is_visible.return_value = True
    mock_page_replay.query_selector.return_value = mock_elem_replay

    replay_sel = adapter2.resolve_selector(
        mock_page_replay,
        semantic_target="create_button",
        heuristic_selectors=[], # No heuristics needed on replay!
        timeout_ms=500
    )
    assert replay_sel == 'button[aria-label="Create"]'
    cache_key = adapter2._get_cache_key(mock_page_replay.url, "create_button")
    assert adapter2.cache[cache_key].hit_count >= 1


def test_midscene_ai_click_and_fill(tmp_path):
    cache_file = tmp_path / "midscene_cache.json"
    adapter = MidsceneAdapter(cache_file=cache_file)

    mock_page = MagicMock()
    mock_page.url = "https://flow.google.com/studio"
    mock_elem = MagicMock()
    mock_elem.is_visible.return_value = True
    mock_page.query_selector.return_value = mock_elem

    # Test ai_click
    click_success = adapter.ai_click(mock_page, "generate_button", ['button:has-text("Generate")'])
    assert click_success is True
    mock_elem.click.assert_called_once()

    # Test ai_fill
    fill_success = adapter.ai_fill(mock_page, "prompt_input", "Cinematic prompt text", ['textarea[name="prompt"]'])
    assert fill_success is True
    mock_elem.fill.assert_called_once_with("Cinematic prompt text")
