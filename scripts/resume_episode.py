"""Generic resume: re-run the full pipeline for ANY episode_id from its saved
brain_input.json, relying on the existing per-stage Postgres checkpoint
(app/services/mpt_ported/state.py idempotent_stage + vf_episode_state table)
and the S7 render's own concat/grade cache to skip already-completed work.

This replaces writing a bespoke one-off resume_<episode>.py script per
incident (e.g. resume_ep005_full.py). Usage:

  set -a; source /root/secrets/.env; set +a
  python3 scripts/resume_episode.py --episode-id genghis-khan-2026-ep005

Optional --story-override PATH lets you swap in a corrected narration text
file (same escape hatch resume_ep005_full.py used), but by default this
script reuses the story text already saved in brain_input.json unchanged --
no silent story mutation.

Writes resume_result.json / resume_error.log markers under the episode dir
for polling, matching the convention of the older one-off scripts.
"""
import sys, os, json, asyncio, argparse, traceback
from pathlib import Path

REPO = Path("/root/video_factory")
sys.path.insert(0, str(REPO))

ENV_PATH = "/root/secrets/.env"
try:
    for raw in open(ENV_PATH):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:]
        k, v = line.split("=", 1)
        k = k.strip(); v = v.strip().strip('"').strip("'")
        if v and k not in os.environ:
            os.environ[k] = v
except Exception as e:
    print("ENV_LOAD_ERR", e)

os.environ.setdefault("VF_REQUIRE_BRAIN", "1")


def _visual_terms(b):
    vt = b.get("visual_terms")
    if vt:
        return vt
    terms = []
    for s in b.get("scenes", []):
        ip = s.get("image_prompt", "")
        terms.append(" ".join(ip.split()[:6]))
    return terms[:8]


async def _render(episode_id: str, brain: dict, story_text: str):
    from orchestrator.run_pipeline import execute_pipeline
    exit_code = execute_pipeline(profile="prod", run_id=episode_id, from_stage="s09")
    if exit_code != 0:
        raise RuntimeError(f"Pipeline failed with exit code {exit_code}")
    return {"status": "ok", "episode_id": episode_id}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--story-override", default=None,
                     help="optional path to a corrected narration text file")
    args = ap.parse_args()

    eid = args.episode_id
    out_dir = Path("/var/vf/episodes") / eid
    brain_path = out_dir / "brain_input.json"
    if not brain_path.exists():
        print("RESULT_ERR", "no brain_input.json found for episode_id=%r at %s" % (eid, brain_path))
        sys.exit(1)
    brain = json.loads(brain_path.read_text())
    if not brain.get("render_architecture"):
        if (out_dir / "remotion_props.json").exists() or (out_dir / "prompts_forge.json").exists() or (out_dir / "images_ready.json").exists():
            brain["render_architecture"] = "remotion_twolayer_karaoke_v4"
            brain_path.write_text(json.dumps(brain, ensure_ascii=False, indent=2), encoding="utf-8")
            print("[resume_episode] Auto-injected render_architecture='remotion_twolayer_karaoke_v4'")

    story_text = brain.get("story", "")
    if args.story_override:
        story_text = Path(args.story_override).read_text()
        brain["story"] = story_text
        print("STORY_OVERRIDDEN from", args.story_override)

    try:
        result = asyncio.run(_render(eid, brain, story_text))
        (out_dir / "resume_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2))
        print("RESULT_OK", json.dumps(result, ensure_ascii=False))
    except Exception:
        err = traceback.format_exc()
        (out_dir / "resume_error.log").write_text(err)
        print("RESULT_ERR", err)
        raise


if __name__ == "__main__":
    main()