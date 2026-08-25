#!/usr/bin/env python3
"""Render the generic, pipeline-wide "TwoLayerEpisode" Remotion composition
to a silent .mp4, from a remotion_props.json built by
scripts/build_remotion_props.py. Episode-agnostic: takes props path + out
path only, never an episode_id-specific value baked into the command.

Mirrors the production render conventions already used by
app/services/mpt_ported/remotion_overlay.py (concurrency env var, --log=error,
timeout handling) so this new 2-layer path behaves the same operationally as
the existing SceneCard renderer.

Usage:
  python3 scripts/render_twolayer_visual.py \\
      --props /var/vf/episodes/<episode_id>/remotion_props.json \\
      --out /var/vf/episodes/<episode_id>/twolayer_silent.mp4

Exit code is non-zero (and prints RENDER_FAILED) if remotion errors out or
times out, so callers (e.g. render_twolayer_test.py) can fail fast instead of
muxing audio onto a missing/partial video file.
"""
import argparse
import os
import subprocess
import sys

PROJ_DIR = os.environ.get("VF_REMOTION_DIR", "/root/video_factory/remotion")
ENTRY = "src/index.tsx"
COMP_ID = "TwoLayerEpisode"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--props", required=True, help="Path to remotion_props.json")
    ap.add_argument("--out", required=True, help="Output .mp4 path")
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("VF_REMOTION_TIMEOUT", "600")))
    args = ap.parse_args()

    if not os.path.exists(os.path.join(PROJ_DIR, ENTRY)):
        print("ERROR: remotion project missing at %s" % PROJ_DIR)
        sys.exit(1)
    if not os.path.exists(args.props):
        print("ERROR: props file not found: %s" % args.props)
        sys.exit(1)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    concurrency = os.environ.get("VF_REMOTION_CONCURRENCY", "3")
    cmd = [
        "npx", "remotion", "render", ENTRY, COMP_ID, args.out,
        "--props=" + os.path.abspath(args.props),
        "--log=error",
        "--concurrency=" + concurrency,
    ]
    print("RUNNING", " ".join(cmd), "cwd=", PROJ_DIR)
    try:
        proc = subprocess.run(cmd, cwd=PROJ_DIR, capture_output=True, text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print("RENDER_FAILED timeout=%.0fs" % args.timeout)
        sys.exit(1)

    if proc.returncode != 0 or not os.path.exists(args.out):
        print("RENDER_FAILED rc=%s" % proc.returncode)
        print((proc.stderr or "")[-2000:])
        sys.exit(1)

    size = os.path.getsize(args.out)
    print("RENDERED", args.out, size, "bytes")


if __name__ == "__main__":
    main()
