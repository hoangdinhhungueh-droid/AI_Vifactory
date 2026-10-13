# -*- coding: utf-8 -*-
"""tests/test_vox_critic_council.py
Kiểm thử tự động cho mô-đun Hội đồng Thẩm định B3 (Astra 6 & Opus 5.5).
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import unittest
from app.services.vox_critic_council import (
    _compress_plan_for_audit,
    _parse_json_response,
    audit_director_plan
)

class TestVoxCriticCouncil(unittest.TestCase):

    def setUp(self):
        self.mock_plan = [
            {
                "scene_id": "SCENE_01",
                "sentence": "Have you ever wondered how Coca-Cola conquered the planet?",
                "editorial_title": "GLOBAL EMPIRE",
                "visual_metaphor": "Golden Crown over Globe",
            },
            {
                "scene_id": "SCENE_02",
                "sentence": "It started as a small medicinal tonic in an Atlanta pharmacy.",
                "editorial_title": "ATLANTA 1886",
                "visual_metaphor": "Vintage Apothecary Glass and Mortar",
            }
        ]

    def test_compress_plan(self):
        compressed = _compress_plan_for_audit(self.mock_plan)
        self.assertIn("SCENE_01", compressed)
        self.assertIn("GLOBAL EMPIRE", compressed)
        self.assertIn("SCENE_02", compressed)
        self.assertIn("ATLANTA 1886", compressed)
        # Verify compression line count
        lines = compressed.strip().split("\n")
        self.assertEqual(len(lines), 2)

    def test_parse_json_response_markdown_fence(self):
        raw_markdown = """```json
{
  "evaluator": "GPT-6-Astra",
  "score": 9.5,
  "verdict": "PASS",
  "retention_pacing_score": 9.2,
  "strengths": ["Rapid pacing", "Clear curiosity gap"],
  "weaknesses": [],
  "recommendations": []
}
```"""
        parsed = _parse_json_response(raw_markdown, "Fallback")
        self.assertEqual(parsed["evaluator"], "GPT-6-Astra")
        self.assertEqual(parsed["score"], 9.5)
        self.assertEqual(parsed["verdict"], "PASS")

    def test_parse_json_response_fallback(self):
        raw_invalid = "This is not valid json text."
        parsed = _parse_json_response(raw_invalid, "Fallback-Model")
        self.assertEqual(parsed["evaluator"], "Fallback-Model")
        self.assertEqual(parsed["verdict"], "PASS")
        self.assertEqual(parsed["score"], 7.5)

if __name__ == "__main__":
    unittest.main()
