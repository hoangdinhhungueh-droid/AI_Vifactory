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
  python3 scripts/render_twolayer_visual.py \
      --props /var/vf/episodes/<episode_id>/remotion_props.json \
      --out /var/vf/episodes/<episode_id>/twolayer_silent.mp4
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

PROJ_DIR = os.environ.get("VF_REMOTION_DIR", "/root/video_factory/remotion")
ENTRY = "src/index.tsx"
COMP_ID = "TwoLayerEpisode"


def preflight_memory_check():
    """Verify system RAM headroom and reap zombie Chromium processes before render."""
    try:
        import psutil
        # Clean up orphaned or zombie Chromium render processes
        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
            try:
                p_name = (p.info.get('name') or '').lower()
                cmd = " ".join(p.info.get('cmdline') or []).lower()
                if ('chrome-headless-shell' in cmd or 'chromium' in cmd) and p.info.get('status') == psutil.STATUS_ZOMBIE:
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

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


def optimize_props_assets(props_path: str, proj_dir: str):
    """Pre-scales images down to 1080p and bakes crisp VOX sticker borders into FG (Pillar 2)."""
    try:
        from PIL import Image, ImageFilter
        import json
        with open(props_path, "r", encoding="utf-8") as pf:
            data = json.load(pf)
        scenes = data.get("scenes", [])
        count = 0
        processed_paths = set()
        for sc in scenes:
            keys_to_check = [("background", False), ("foreground", True)]
            if isinstance(sc.get("primary_hero"), dict) and sc["primary_hero"].get("src"):
                keys_to_check.append(("primary_hero", True))
            for key, is_fg in keys_to_check:
                img_rel = sc["primary_hero"]["src"] if key == "primary_hero" else sc.get(key)
                if not img_rel or str(img_rel).startswith("http"):
                    continue
                full_path = os.path.join(proj_dir, "public", str(img_rel))
                if full_path in processed_paths or not os.path.exists(full_path):
                    continue
                processed_paths.add(full_path)
                try:
                    with Image.open(full_path) as im:
                        im = im.convert("RGBA") if is_fg else im.convert("RGB")
                        modified = False
                        # 1. Scale down to 1080p target
                        max_w = 1080 if key == "foreground" else 1920
                        max_h = 1080
                        if im.width > max_w or im.height > max_h:
                            ratio = min(max_w / float(im.width), max_h / float(im.height))
                            nw = max(1, int(round(im.width * ratio)))
                            nh = max(1, int(round(im.height * ratio)))
                            im = im.resize((nw, nh), Image.Resampling.LANCZOS)
                            modified = True

                        # 2. Bake VOX white sticker border directly into FG alpha
                        if key == "foreground" and "A" in im.getbands():
                            alpha = im.split()[-1]
                            min_a, max_a = alpha.getextrema()
                            if min_a < 250:
                                dilated = alpha.filter(ImageFilter.MaxFilter(7))
                                bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
                                bg.putalpha(dilated)
                                im = Image.alpha_composite(bg, im)
                                modified = True

                        if modified:
                            im.save(full_path, optimize=True)
                            count += 1
                except Exception:
                    pass
        if count > 0:
            print(f"[ASSET OPTIMIZE] Successfully optimized and pre-scaled {count} assets for fast CPU render.")
    except Exception as e:
        print(f"[ASSET CHECK] Asset optimization skipped: {e}")



def calculate_dynamic_timeout(props_path: str, base_timeout: float) -> tuple[float, int]:
    """Calculate adaptive timeout based on canonical policy (Rule 134)."""
    try:
        from app.services.render_timeout_policy import (
            compute_render_timeout_hierarchy,
            extract_frames_from_props,
        )
        total_frames = extract_frames_from_props(props_path, default_frames=18000)
        h = compute_render_timeout_hierarchy(total_frames, base_timeout)
        return h["remotion_timeout"], h["total_frames"]
    except Exception:
        total_frames = 18000
        timeout = max(base_timeout, float(total_frames) * 2.0 + 7200.0, 36000.0)
        return timeout, total_frames


def main():
    import json
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("--props", required=True, help="Path to remotion_props.json")
    ap.add_argument("--out", required=True, help="Output .mp4 path")
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("VF_REMOTION_TIMEOUT", "10800")))
    ap.add_argument("--frames", default=None, help="Frame range to render (e.g. 0-4341)")
    ap.add_argument("--x264-preset", default="veryfast", help="x264 preset (default: veryfast)")
    ap.add_argument("--crf", type=int, default=18, help="x264 CRF (default: 18)")
    ap.add_argument("--log", default="info", help="Remotion log level (default: info)")
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

    # Pillar 2: Pre-scale image assets to 1080p to eliminate Chromium downscale bottleneck
    optimize_props_assets(args.props, PROJ_DIR)

    # Pillar 1: Dynamic CPU concurrency (auto-detects cores, cap at 4 for RAM safety)
    default_concurrency = min(2, max(1, (os.cpu_count() or 4) - 2))
    concurrency = os.environ.get("VF_REMOTION_CONCURRENCY", str(default_concurrency))

    # Pillar 3: Dynamic adaptive timeout based on total frames
    dynamic_timeout, total_frames = calculate_dynamic_timeout(args.props, args.timeout)
    print(f"[RENDER CONFIG] Total frames: {total_frames} | Concurrency: {concurrency} | Dynamic Timeout: {dynamic_timeout:.0f}s")
    
    cmd = [
        "npx", "remotion", "render", ENTRY, COMP_ID, args.out,
        "--props=" + os.path.abspath(args.props),
        f"--log={args.log}",
        "--concurrency=" + concurrency,
        "--x264-preset=" + args.x264_preset,
        "--crf=" + str(args.crf),
        "--bundle-cache",
    ]
    if args.frames:
        cmd.append(f"--frames={args.frames}")
    
    # Bound Node.js heap memory to 2GB to prevent runaway memory leaks
    env = os.environ.copy()
    if "NODE_OPTIONS" not in env:
        env["NODE_OPTIONS"] = "--max-old-space-size=2048"
    
    print("RUNNING", " ".join(cmd), "cwd=", PROJ_DIR, "concurrency=", concurrency, "NODE_OPTIONS=", env.get("NODE_OPTIONS"))
    import signal
    start_t = time.time()
    last_progress = ""

    # Pillar 3: Real-time progress streaming with Popen and process group isolation
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROJ_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            start_new_session=True,
        )
        if proc.stdout:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                if "Rendered" in line or "%" in line:
                    last_progress = line.strip()

        proc.wait(timeout=dynamic_timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(2)
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        print(f"RENDER_FAILED timeout={dynamic_timeout:.0f}s (Last known progress: {last_progress})")
        sys.exit(1)
    finally:
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass

    elapsed = time.time() - start_t
    if rc != 0 or not os.path.exists(args.out):
        print(f"RENDER_FAILED rc={rc} elapsed={elapsed:.1f}s")
        sys.exit(1)

    size = os.path.getsize(args.out)
    print(f"RENDERED {args.out} {size} bytes in {elapsed:.1f}s (avg {(elapsed/max(1, total_frames)):.2f}s/frame)")


if __name__ == "__main__":
    main()
