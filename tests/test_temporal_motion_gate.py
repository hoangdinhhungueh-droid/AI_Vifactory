#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_temporal_motion_gate.py
Unit tests for Temporal Video Motion Delta Gate and S05 7-Account Flow Manifest.
Enforces Rule 118, 121, 122, 125, 128.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from stages.s05_director_plan import FLOW_ACCOUNTS, generate_7acc_flow_manifest
from stages.s08_video_gen import StaticFreezeFrameError, validate_video_motion_temporal_delta
from vox.ffmpeg_utils import get_ffmpeg_binary


class TestTemporalMotionGate(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.td.name)
        self.ffmpeg_bin = get_ffmpeg_binary()

    def tearDown(self):
        self.td.cleanup()

    def test_7acc_flow_manifest_generation(self):
        """Verifies that generate_7acc_flow_manifest correctly round-robins across all 7 accounts."""
        scenes = [
            {
                "scene_id": f"SCENE_{i+1:02d}",
                "i2v_prompt_omni": f"Kinematic animation for scene {i+1}",
                "duration_est_sec": 5.0,
                "hero_cutout_object": f"Hero {i+1}",
                "camera_directive": "STATIC_OVERHEAD"
            }
            for i in range(15)
        ]
        manifest = generate_7acc_flow_manifest(self.tmp_dir, "TEST_EP0001", scenes)
        self.assertEqual(manifest["total_clips"], 15)
        self.assertEqual(manifest["accounts_used"], FLOW_ACCOUNTS)
        self.assertEqual(len(FLOW_ACCOUNTS), 7)

        # Check round-robin distribution
        for idx, clip in enumerate(manifest["clips"]):
            expected_slot = FLOW_ACCOUNTS[idx % 7]
            self.assertEqual(clip["flow_slot"], expected_slot)
            self.assertEqual(clip["output_filename"], f"clip_scene_{idx+1:02d}.mp4")

        # Check file was written to disk
        man_file = self.tmp_dir / "flow_video_manifest.json"
        self.assertTrue(man_file.exists())
        loaded = json.loads(man_file.read_text(encoding="utf-8"))
        self.assertEqual(len(loaded["clips"]), 15)

    def test_static_freeze_frame_fails_closed(self):
        """Verifies that a video created via ffmpeg -loop 1 fails the motion audit (Rule 118 & 122)."""
        img_path = self.tmp_dir / "still.png"
        Image.new("RGB", (320, 240), color="blue").save(img_path)
        static_vid = self.tmp_dir / "static_clip.mp4"

        # Create static looped video
        cmd = [
            self.ffmpeg_bin, "-y", "-loop", "1", "-i", str(img_path),
            "-t", "3.0", "-pix_fmt", "yuv420p", str(static_vid)
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        with self.assertRaises(StaticFreezeFrameError) as ctx:
            validate_video_motion_temporal_delta(static_vid, min_delta=0.5)
        self.assertIn("static freeze-frame", str(ctx.exception).lower())

    def test_dynamic_video_passes_motion_gate(self):
        """Verifies that a truly animated video passes the motion audit with delta > 0.5."""
        dyn_vid = self.tmp_dir / "dynamic_clip.mp4"
        cmd = [
            self.ffmpeg_bin, "-y", "-f", "lavfi",
            "-i", "testsrc=duration=3.0:size=320x240:rate=25",
            "-pix_fmt", "yuv420p", str(dyn_vid)
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        score = validate_video_motion_temporal_delta(dyn_vid, min_delta=0.5)
        self.assertGreater(score, 0.5)


if __name__ == "__main__":
    unittest.main()
