import unittest
import sys
from pathlib import Path
from pydantic import ValidationError

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.contracts.stages import (
    StageID, StageArtifact, Provenance, Scene, Shot, VideoAsset, CouncilDecision, CriticVerdict
)
from core.contracts.render_props import RemotionRenderProps, SceneRenderProp, KaraokeWord


class TestContracts(unittest.TestCase):
    def test_stage_id_enum(self):
        self.assertEqual(len(StageID), 11)
        self.assertEqual(StageID.S1_IDEATION.value, "s01_ideation")
        self.assertEqual(StageID.S10_RENDER.value, "s10_render")

    def test_extra_forbid_on_shot(self):
        with self.assertRaises(ValidationError):
            Shot(
                shot_id="sh_01",
                scene_id="sc_01",
                visual_prompt="test prompt",
                unexpected_rogue_key="forbidden"
            )

    def test_stage_artifact_serialization(self):
        shot = Shot(
            shot_id="sh_01",
            scene_id="SCENE_01",
            visual_prompt="Paper cutout test prompt",
            account_slot="acc_01"
        )
        scene = Scene(
            scene_id="SCENE_01",
            narration="Test narration statement.",
            shots=[shot]
        )
        prov = Provenance(generator="unit_test", latency_sec=0.1)
        art = StageArtifact(
            run_id="RUN_TEST_01",
            stage=StageID.S5_DIRECTOR_PLAN,
            payload={"scenes": [scene.model_dump()]},
            provenance=prov
        )
        json_data = art.model_dump_json()
        loaded = StageArtifact.model_validate_json(json_data)
        self.assertEqual(loaded.stage, StageID.S5_DIRECTOR_PLAN)
        self.assertEqual(loaded.run_id, "RUN_TEST_01")

    def test_remotion_render_props(self):
        kw = KaraokeWord(word="Hello", start=0.0, end=0.5)
        sc = SceneRenderProp(
            scene_id="SCENE_01",
            duration_in_frames=90,
            video_clip_path="clip_sc01.mp4",
            subtitles=[kw]
        )
        props = RemotionRenderProps(
            episode_id="EP_TEST",
            title="Test Video",
            duration_in_frames=90,
            scenes=[sc]
        )
        self.assertEqual(len(props.scenes), 1)
        self.assertEqual(props.fps, 30)


if __name__ == "__main__":
    unittest.main()
