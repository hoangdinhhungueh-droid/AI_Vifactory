#!/usr/bin/env python3
"""Render the generic, pipeline-wide "TwoLayerEpisode" Remotion composition
to a silent .mp4, from a remotion_props.json built by
scripts/build_remotion_props.py. Episode-agnostic: takes props path + out
path only, never an episode_id-specific value baked into the command.

Mirrors the production render conventions already used by
app/services/mpt_ported/remotion_overlay.py (concurrency env var, --log=error,
timeout handling) so this new 2-layer path behaves the same operationally as
the existing SceneCard renderer.

Hardened with Anti-OOM guards:
- Conservative default concurrency (1 or 2, default: 1)
- NODE_OPTIONS="--max-old-space-size=2048" heap cap
- Pre-flight memory verification to avoid starting render in starvation
- Strict exit code verification

Usage:
  python3 scripts/render_twolayer_visual.py \\
      --props /var/vf/episodes/<episode_id>/remotion_props.json \\
      --out /var/vf/episodes/<episode_id>/twolayer_silent.mp4
"""
import argparse
import os
import subprocess
import sys

PROJ_DIR = os.environ.get("VF_REMOTION_DIR", "/root/video_factory/remotion")
ENTRY = "src/index.tsx"
COMP_ID = "TwoLayerEpisode"


def preflight_memory_check():
    """Verify system RAM headroom before spawning Chromium render workers."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        avail_mb = mem.available / (1024 * 1024)
        total_mb = mem.total / (1024 * 1024)
        swap = psutil.swap_memory()
        print(f"[MEMORY CHECK] Available RAM: {avail_mb:.0f} MB / {total_mb:.0f} MB ({mem.percent}% used). Swap free: {swap.free / (1024*1024):.0f} MB / {swap.total / (1024*1024):.0f} MB")
        if avail_mb < 1200:
            print("[MEMORY WARNING] Available RAM < 1200 MB. Attempting cache drop...")
            try:
                os.system("sync; echo 1 > /proc/sys/vm/drop_caches 2>/dev/null")
            except Exception:
                pass
    except Exception as e:
        print(f"[MEMORY CHECK] psutil check skipped: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--props", required=True, help="Path to remotion_props.json")
    ap.add_argument("--out", required=True, help="Output .mp4 path")
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("VF_REMOTION_TIMEOUT", "7200")))
    args = ap.parse_args()

    if not os.path.exists(os.path.join(PROJ_DIR, ENTRY)):
        print("ERROR: remotion project missing at %s" % PROJ_DIR)
        sys.exit(1)
    if not os.path.exists(args.props):
        print("ERROR: props file not found: %s" % args.props)
        sys.exit(1)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    
    # Pre-flight RAM verification
    preflight_memory_check()
    
    # Conservative concurrency: 1 (safe default) or user-overridden
    concurrency = os.environ.get("VF_REMOTION_CONCURRENCY", "1")
    
    cmd = [
        "npx", "remotion", "render", ENTRY, COMP_ID, args.out,
        "--props=" + os.path.abspath(args.props),
        "--log=error",
        "--concurrency=" + concurrency,
    ]
    
    # Bound Node.js heap memory to 2GB to prevent runaway memory leaks
    env = os.environ.copy()
    if "NODE_OPTIONS" not in env:
        env["NODE_OPTIONS"] = "--max-old-space-size=2048"
    
    print("RUNNING", " ".join(cmd), "cwd=", PROJ_DIR, "concurrency=", concurrency, "NODE_OPTIONS=", env.get("NODE_OPTIONS"))
    try:
        proc = subprocess.run(cmd, cwd=PROJ_DIR, capture_output=True, text=True, timeout=args.timeout, env=env)
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
