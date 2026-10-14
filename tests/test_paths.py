import unittest
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.paths import resolve_run_paths, new_run_paths, RunPaths


class TestCorePaths(unittest.TestCase):
    def setUp(self):
        self.test_run_id = "TEST_RUN_9999"
        self.test_root = Path("runs") / self.test_run_id
        if self.test_root.exists():
            shutil.rmtree(self.test_root, ignore_errors=True)

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root, ignore_errors=True)

    def test_run_paths_creation(self):
        paths = resolve_run_paths(self.test_run_id)
        self.assertTrue(paths.root.is_absolute())
        self.assertTrue(paths.root.exists())
        self.assertTrue(paths.composite_seeds_dir.exists())
        self.assertTrue(paths.video_clips_dir.exists())
        self.assertTrue(paths.audio_dir.exists())

    def test_stage_artifact_path(self):
        paths = resolve_run_paths(self.test_run_id)
        art = paths.artifact_file("s01_ideation")
        self.assertTrue(art.is_absolute())
        self.assertEqual(art.name, "artifact.json")
        self.assertTrue(art.parent.exists())

    def test_seed_and_clip_path(self):
        paths = resolve_run_paths(self.test_run_id)
        img_p = paths.seed_image_path("SCENE_01")
        vid_p = paths.video_clip_path("SCENE_01")
        self.assertEqual(img_p.name, "composite_scene_01.png")
        self.assertEqual(vid_p.name, "clip_scene_01.mp4")

    def test_new_run_paths(self):
        paths = new_run_paths(prefix="MINI")
        self.assertTrue("MINI_" in paths.run_id)
        self.assertTrue(paths.root.exists())
        shutil.rmtree(paths.root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
