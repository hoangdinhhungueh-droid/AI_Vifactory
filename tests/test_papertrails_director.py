#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_papertrails_director.py — Tests for Papertrails Director & Timeline Forge (FT-301)."""

import json
from pathlib import Path
import unittest

from app.services.papertrails_director import (
    build_papertrails_timeline,
    detect_subject_and_biome,
    split_into_karaoke_captions,
    normalize_vietnamese,
)


class TestPapertrailsDirector(unittest.TestCase):
    def test_normalize_vietnamese(self):
        text = "Nhà máy sản xuất tiền tệ và đồng hồ"
        norm = normalize_vietnamese(text)
        self.assertIn("nha may", norm)
        self.assertIn("san xuat", norm)
        self.assertIn("tien te", norm)
        self.assertIn("dong ho", norm)

    def test_detect_subject_and_biome(self):
        # Factory / industry
        prop, biome = detect_subject_and_biome("Nhà máy sản xuất thép tăng trưởng mạnh")
        self.assertEqual(prop, "factory")
        self.assertEqual(biome, "heartland")

        # Money / coin
        prop, biome = detect_subject_and_biome("Chi phí tiết kiệm hàng tỷ đô la")
        self.assertEqual(prop, "coin")
        self.assertEqual(biome, "heartland")

        # Forest
        prop, biome = detect_subject_and_biome("Cánh rừng bạt ngàn trong tự nhiên")
        self.assertEqual(prop, "forest")
        self.assertEqual(biome, "pinewood")

        # Mountain
        prop, biome = detect_subject_and_biome("Ngọn núi tuyết lạnh giá mùa đông")
        self.assertEqual(prop, "mountain")
        self.assertEqual(biome, "snow")

    def test_split_into_karaoke_captions(self):
        segments = [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Tiết kiệm tiền là bước đầu.",
                "words": [
                    {"word": "Tiết", "start": 0.0, "end": 0.4},
                    {"word": "kiệm", "start": 0.4, "end": 0.8},
                    {"word": "tiền", "start": 0.8, "end": 1.2},
                    {"word": "là", "start": 1.2, "end": 1.5},
                    {"word": "bước", "start": 1.5, "end": 1.9},
                    {"word": "đầu.", "start": 1.9, "end": 2.5},
                ]
            }
        ]
        captions = split_into_karaoke_captions(segments, max_seconds=3.5)
        self.assertTrue(len(captions) >= 1)
        cap = captions[0]
        self.assertEqual(cap["start"], 0.0)
        self.assertEqual(cap["end"], 2.5)
        self.assertEqual(len(cap["words"]), 6)
        self.assertEqual(cap["words"][0]["word"], "Tiết")
        self.assertEqual(cap["words"][0]["start"], 0.0)

    def test_build_papertrails_timeline(self):
        scenes_script = [
            {
                "scene_id": "SCENE_01",
                "headline": "Sự Khởi Đầu Của Nhà Máy",
                "narration": "Nhà máy bắt đầu sản xuất với công suất tối đa.",
                "stat_hero": "100%",
                "stat_label": "Công suất thiết kế",
                "start_sec": 0.0,
                "end_sec": 5.0,
            },
            {
                "scene_id": "SCENE_02",
                "headline": "Khủng Hoảng Chi Phí",
                "narration": "Chi phí tài chính và tiền bạc tăng vọt theo thời gian.",
                "stat_hero": "$50M",
                "stat_label": "Thâm hụt ngân sách",
                "start_sec": 5.0,
                "end_sec": 10.0,
            }
        ]

        dummy_audio = Path("dummy_voice.mp3")
        duration = 10.0

        timeline = build_papertrails_timeline(
            scenes_script=scenes_script,
            audio_path=dummy_audio,
            audio_duration=duration,
            orientation="landscape",
            fps=30,
            seed=123,
        )

        self.assertEqual(timeline["version"], 1)
        self.assertEqual(timeline["width"], 1920)
        self.assertEqual(timeline["height"], 1080)
        self.assertEqual(timeline["fps"], 30)
        self.assertEqual(timeline["duration"], 10.0)
        self.assertEqual(len(timeline["scenes"]), 2)

        # Check Shot 1
        s1 = timeline["scenes"][0]
        self.assertEqual(s1["id"], "shot-001")
        self.assertEqual(s1["prop"], "factory")
        self.assertEqual(s1["biome"], "heartland")
        self.assertIn("card", s1)
        self.assertEqual(s1["card"]["kind"], "note")

        # Check Shot 2
        s2 = timeline["scenes"][1]
        self.assertEqual(s2["id"], "shot-002")
        self.assertEqual(s2["prop"], "coin")
        self.assertEqual(s2["biome"], "heartland")


if __name__ == "__main__":
    unittest.main()
