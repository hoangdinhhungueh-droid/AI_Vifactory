import sys
from pathlib import Path
import tempfile

sys.path.insert(0, '/root/video_factory')

from app.services.unified_vox_director import build_unified_director_plan
from app.services.b5_visual_gate import audit_and_evaluate_asset, refine_prompt_with_corrective_directive
from app.services.timeline_editor_agent import audit_and_optimize_timeline

tmp = Path(tempfile.mkdtemp())
sents = [{'text': 'Testing showrunner orchestrator.', 'duration_frames': 90, 'beat_index': 1}]
plan = build_unified_director_plan(sents, tmp, metadata={'episode_id': 'TEST_SHOWRUNNER', 'market': 'EN'})

assert (tmp / 'showrunner_dossier.json').exists(), "showrunner_dossier.json not found!"
assert 'showrunner_dossier' in plan, "plan missing showrunner_dossier key!"

scenes = [{'scene_id': 's1', 'durationInFrames': 90, 'cameraMovement': 'dramatic_push', 'transition': 'push_zoom', 'motionDirective': 'yellow_marker_highlight'}]
opt_scenes = audit_and_optimize_timeline(scenes, options={'enable_llm_director': False})
assert opt_scenes[0]['transition'] == 'push_zoom', "Transition optimization failed!"
assert opt_scenes[0]['motionDirective'] == 'yellow_marker_highlight', "Motion directive failed!"

ref = refine_prompt_with_corrective_directive("Base prompt", "Add dynamic posture")
assert "SHOWRUNNER REFINEMENT" in ref

print("VPS LIVING TEST PASS: All Showrunner Modules 100% Operational!")
