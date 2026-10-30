import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.paths import resolve_run_paths
from core.run_manifest import RunManifest
from core.config import load_profile, RunContext


class TestConfig(unittest.TestCase):
    def test_load_prod_profile(self):
        cfg = load_profile("prod")
        self.assertEqual(cfg.name, "prod")
        self.assertEqual(len(cfg.video_generation.account_pool), 6)
        self.assertEqual(cfg.render.fps, 30)

    def test_load_e2e_min_profile(self):
        cfg = load_profile("e2e_min")
        self.assertEqual(cfg.name, "e2e_min")
        self.assertEqual(cfg.limits.max_scenes, 1)
        self.assertEqual(len(cfg.video_generation.account_pool), 1)

    def test_run_context_creation(self):
        cfg = load_profile("e2e_min")
        paths = resolve_run_paths("CTX_TEST_001")
        manifest = RunManifest.create_new("CTX_TEST_001", profile="e2e_min")
        ctx = RunContext(
            run_id="CTX_TEST_001",
            paths=paths,
            manifest=manifest,
            config=cfg,
            force=False,
            dry_run=True
        )
        self.assertEqual(ctx.run_id, "CTX_TEST_001")
        self.assertTrue(ctx.dry_run)


if __name__ == "__main__":
    unittest.main()
