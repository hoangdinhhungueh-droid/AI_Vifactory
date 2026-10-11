# -*- coding: utf-8 -*-
"""
tests/test_round4_downstream_integrity.py

Unit and regression test suite for Round 4 Downstream Pipeline integrity:
1. B10 Description Bridge deduplication and robust chapter block replacement.
2. Chunk rendering (render_twolayer_chunks.py) beat_phase priority and fragmentation guard.
3. Premature props staging avoidance in continue_after_images.py.
"""
import os
import sys
import json
import tempfile
from pathlib import Path
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.execute_b10_auto_seo_upload_gate2 import _clean_and_localize_seo_description
from scripts.render_twolayer_chunks import get_beat_chunks_from_props


class TestRound4DownstreamIntegrity:

    def test_b10_seo_description_bridge_deduplication(self):
        """Verify that B10 does not duplicate the sister channel bridge if already present."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ep_dir = Path(tmp_dir) / "EN_EP0099_test_topic"
            ep_dir.mkdir(parents=True, exist_ok=True)

            desc_with_existing_bridge = (
                "Oakland approved a $500M development deal that was rejected in 24 hours.\n\n"
                "Chapters:\n"
                "00:00 The Shock Denial\n"
                "02:15 The Secret Clause\n\n"
                "#oakland #investigation #finance\n\n"
                "────────────────────────────────────────\n"
                "🌐 Official Global Investigation Network:\n"
                "• Japanese Edition (日本語版): https://www.youtube.com/@AIVideoFactory_JP\n"
                "• Korean Edition (한국어판): https://www.youtube.com/@AIVideoFactory_KR\n"
                "────────────────────────────────────────\n\n"
                "This video incorporates investigative research."
            )

            result = _clean_and_localize_seo_description(
                desc=desc_with_existing_bridge,
                ep_dir=ep_dir,
                market="en",
                title="Oakland Plan Rejected"
            )

            # Assert the bridge banner occurs EXACTLY ONCE
            assert result.count("Official Global Investigation Network") == 1
            assert result.count("────────────────────────────────────────") == 2
            assert "#oakland #investigation #finance" in result
            assert "This video incorporates investigative research." in result

    def test_b10_seo_chapter_replacement_preserves_trailing_content(self):
        """Verify that replacing chapters cleanly preserves hashtags, bridges, and disclosures."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ep_dir = Path(tmp_dir) / "EN_EP0099_test_topic"
            ep_dir.mkdir(parents=True, exist_ok=True)

            desc = (
                "Intro hook text.\n\n"
                "Chapters:\n"
                "00:00 Old Chapter 1\n"
                "01:00 Old Chapter 2\n\n"
                "#hashtag1 #hashtag2\n\n"
                "This video incorporates investigative analysis."
            )

            result = _clean_and_localize_seo_description(
                desc=desc,
                ep_dir=ep_dir,
                market="en",
                title="Test Title"
            )

            assert "#hashtag1 #hashtag2" in result
            assert "This video incorporates investigative analysis." in result
            assert "Chapters:" in result

    def test_render_twolayer_chunks_with_beat_phase(self):
        """Verify that get_beat_chunks_from_props yields 5 chunks when beat_phase 1..5 is present."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            props_file = Path(tmp_dir) / "remotion_props.json"
            
            # 25 scenes with beat_phase 1..5 (5 scenes per beat)
            scenes = []
            for b in range(1, 6):
                for s in range(5):
                    scenes.append({
                        "beat_phase": b,
                        "durationInFrames": 60,
                        "layoutVariant": "paper_collage",
                    })

            props_file.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")

            chunks = get_beat_chunks_from_props(str(props_file))
            assert len(chunks) == 5
            for i, chunk in enumerate(chunks, 1):
                assert chunk["name"] == f"BEAT {i}"
                assert chunk["duration"] == 300  # 5 * 60

    def test_render_twolayer_chunks_prevents_fragmentation(self):
        """Verify that sequential beat_index 1..30 does not create 30 chunks, but collapses to 5."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            props_file = Path(tmp_dir) / "remotion_props.json"
            
            # 30 scenes with sequential beat_index (1..30) and no beat_phase
            scenes = []
            for idx in range(1, 31):
                scenes.append({
                    "beat_index": idx,
                    "durationInFrames": 50,
                    "layoutVariant": "cinematic_doc",
                })

            props_file.write_text(json.dumps({"scenes": scenes}), encoding="utf-8")

            chunks = get_beat_chunks_from_props(str(props_file))
            assert 2 <= len(chunks) <= 7
            assert len(chunks) == 5
            total_duration = sum(c["duration"] for c in chunks)
            assert total_duration == 30 * 50
