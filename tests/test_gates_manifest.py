import unittest
import sys
import shutil
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.paths import resolve_run_paths
from core.contracts.stages import StageID, StageArtifact, Provenance, SCHEMA_VERSION
from core.gates import validate_artifact, emit_artifact, require_input, GateError
from core.run_manifest import RunManifest
from core.legacy_guard import forbid_legacy, LegacyFlowError
from core.no_mock import assert_never_mock, MockLeakError


class TestGatesAndManifest(unittest.TestCase):
    def setUp(self):
        self.test_run_id = "GATE_TEST_001"
        self.paths = resolve_run_paths(self.test_run_id)

    def tearDown(self):
        if self.paths.root.exists():
            shutil.rmtree(self.paths.root, ignore_errors=True)

    def test_validate_artifact_pass(self):
        prov = Provenance(generator="unit_test")
        art = StageArtifact(
            run_id=self.test_run_id,
            stage=StageID.S1_IDEATION,
            payload={"topic": "Test Topic"},
            provenance=prov
        )
        validated = validate_artifact(StageID.S1_IDEATION, art.model_dump())
        self.assertEqual(validated.stage, StageID.S1_IDEATION)

    def test_validate_artifact_stage_mismatch(self):
        prov = Provenance(generator="unit_test")
        art = StageArtifact(
            run_id=self.test_run_id,
            stage=StageID.S1_IDEATION,
            payload={"topic": "Test Topic"},
            provenance=prov
        )
        with self.assertRaises(GateError):
            validate_artifact(StageID.S2_RESEARCH, art.model_dump())

    def test_emit_and_require_input(self):
        prov = Provenance(generator="unit_test")
        art1 = StageArtifact(
            run_id=self.test_run_id,
            stage=StageID.S1_IDEATION,
            payload={"topic": "AI Revolution"},
            provenance=prov
        )
        emitted_path = emit_artifact(art1, self.paths)
        self.assertTrue(emitted_path.exists())

        # S2 requires S1
        loaded_input = require_input(StageID.S2_RESEARCH, self.paths)
        self.assertIsNotNone(loaded_input)
        self.assertEqual(loaded_input.stage, StageID.S1_IDEATION)

    def test_manifest_lifecycle(self):
        m = RunManifest.create_new(self.test_run_id, profile="e2e_min")
        self.assertEqual(m.next_pending_stage(), StageID.S1_IDEATION)

        m.mark(StageID.S1_IDEATION, "running")
        self.assertEqual(m.stages[StageID.S1_IDEATION].status, "running")

        m.mark(StageID.S1_IDEATION, "done", artifact_sha256="abc123sha")
        self.assertEqual(m.stages[StageID.S1_IDEATION].status, "done")
        self.assertEqual(m.next_pending_stage(), StageID.S2_RESEARCH)

        m.save_atomic(self.paths)
        loaded = RunManifest.load_or_create(self.paths)
        self.assertEqual(loaded.stages[StageID.S1_IDEATION].status, "done")

    def test_legacy_guard(self):
        with self.assertRaises(LegacyFlowError):
            forbid_legacy("old_module.py")

    def test_no_mock_guard(self):
        old_env = os.environ.get("AVF_ALLOW_MOCK")
        if "AVF_ALLOW_MOCK" in os.environ:
            del os.environ["AVF_ALLOW_MOCK"]
        try:
            with self.assertRaises(MockLeakError):
                assert_never_mock("test production call")
        finally:
            if old_env:
                os.environ["AVF_ALLOW_MOCK"] = old_env


if __name__ == "__main__":
    unittest.main()
