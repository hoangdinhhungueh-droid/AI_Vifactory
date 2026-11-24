#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_papertrails_harness.py — Verification for Papertrails Harness & State Machine (FT-301..FT-303)."""

import json
from pathlib import Path
import unittest

from app.services.papertrails_director import build_papertrails_timeline


class TestPapertrailsHarness(unittest.TestCase):
    def test_harness_contracts_consistency(self):
        harness_path = Path(".harness/01_CONTRACTS.md")
        self.assertTrue(harness_path.exists())
        content = harness_path.read_text(encoding="utf-8")
        self.assertIn("PapertrailsTimelineSpec", content)
        self.assertIn("PapertrailsScene", content)
        self.assertIn("PapertrailsCaptionWord", content)

    def test_harness_features_consistency(self):
        features_path = Path(".harness/02_FEATURES.md")
        self.assertTrue(features_path.exists())
        content = features_path.read_text(encoding="utf-8")
        self.assertIn("[FT-301]", content)
        self.assertIn("[FT-302]", content)
        self.assertIn("[FT-303]", content)

    def test_harness_wiring_consistency(self):
        wiring_path = Path(".harness/03_WIRING.md")
        self.assertTrue(wiring_path.exists())
        content = wiring_path.read_text(encoding="utf-8")
        self.assertIn("build_papertrails_timeline", content)
        self.assertIn("render_papertrails_on_vps", content)

    def test_papertrails_timeline_compliance(self):
        # Generate sample timeline
        sample_scenes = [
            {"scene_id": "SCENE_01", "headline": "Thế Giới Giấy", "narration": "Một thế giới giấy 3D mở ra trước mắt.", "prop": "village", "biome": "heartland"},
            {"scene_id": "SCENE_02", "headline": "Khu Rừng Thông", "narration": "Đi sâu vào rừng thông xanh mướt.", "prop": "forest", "biome": "pinewood"}
        ]
        t = build_papertrails_timeline(
            scenes_script=sample_scenes,
            audio_path=Path("/tmp/voice.mp3"),
            audio_duration=6.0,
            orientation="landscape",
            fps=30
        )
        self.assertEqual(t["version"], 1)
        self.assertEqual(t["duration"], 6.0)
        self.assertEqual(len(t["scenes"]), 2)
        # Check uninterrupted scene timeline
        self.assertEqual(t["scenes"][0]["start"], 0.0)
        self.assertEqual(t["scenes"][0]["end"], t["scenes"][1]["start"])
        self.assertEqual(t["scenes"][1]["end"], 6.0)


if __name__ == "__main__":
    unittest.main()
