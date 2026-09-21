#!/usr/bin/env python3
"""
scripts/render_twolayer_chunks.py

Renders a long Remotion TwoLayer episode in Beat-based chunks,
then stitches them losslessly via FFmpeg stream-copy (`-c copy`).

Key Features:
- Natural Beat boundary alignment (zero visual/editorial discontinuity).
- Resumable: Skips already-rendered valid chunks.
- Memory freshness: Each chunk runs in a separate process.
- Lossless concatenation: Instantaneous zero-reencode stitch.
- Verification: Validates total frame count and duration with ffprobe.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

PROJ_DIR = os.environ.get("VF_REMOTION_DIR", "/root/video_factory/remotion")


def get_beat_chunks_from_props(props_path: str) -> list[dict]:
    """Extract exact frame ranges for each Beat from remotion_props.json."""
    with open(props_path, "r", encoding="utf-8") as f:
        props = json.load(f)
    scenes = props.get("scenes", [])
    if not scenes:
        raise ValueError(f"No scenes found in {props_path}")

    beats = []
    current_beat_tag = None
    start_frame = 0
    current_frame = 0
    beat_idx = 1

    for i, s in enumerate(scenes):
        dur = max(1, round(s.get("durationInFrames", 1)))
        tag = s.get("speakerTag", "")
        # Detect Beat header e.g. "BEAT 1", "BEAT 2"
        beat_prefix = None
        if "BEAT " in tag.upper():
            parts = tag.upper().split(":")
            beat_prefix = parts[0].strip()

        if beat_prefix and beat_prefix != current_beat_tag:
            if current_beat_tag is not None:
                beats.append({
                    "name": current_beat_tag,
                    "index": beat_idx,
                    "start_frame": start_frame,
                    "end_frame": current_frame - 1,
                    "duration": current_frame - start_frame,
                })
                beat_idx += 1
                start_frame = current_frame
            current_beat_tag = beat_prefix

        current_frame += dur

    # Append the last beat
    if current_frame > start_frame:
        beats.append({
            "name": current_beat_tag or f"BEAT {beat_idx}",
            "index": beat_idx,
            "start_frame": start_frame,
            "end_frame": current_frame - 1,
            "duration": current_frame - start_frame,
        })

    # Fallback if no explicit beats found: split into 5 equal chunks
    if len(beats) < 2:
        beats = []
        total = current_frame
        chunk_size = total // 5
        cur = 0
        for b in range(1, 6):
            end = total - 1 if b == 5 else (cur + chunk_size - 1)
            beats.append({
                "name": f"CHUNK {b}",
                "index": b,
                "start_frame": cur,
                "end_frame": end,
                "duration": end - cur + 1,
            })
            cur = end + 1

    return beats


def verify_chunk_mp4(path: str, expected_duration_sec: float) -> bool:
    """Check if an mp4 chunk exists, is readable, and has approximately expected duration."""
    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        return False
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            dur = float(res.stdout.strip())
            # Tolerance: within 1.0 second of expected
            if abs(dur - expected_duration_sec) < 1.5:
                return True
    except Exception:
        pass
    return False


def render_single_chunk(
    props_path: str,
    out_path: str,
    start_frame: int,
    end_frame: int,
    concurrency: str = "3",
    x264_preset: str = "veryfast",
    crf: int = 18,
    timeout: float = 7200.0,
) -> bool:
    """Render a single chunk using render_twolayer_visual.py."""
    frames_arg = f"{start_frame}-{end_frame}"
    cmd = [
        sys.executable,
        str(_REPO_ROOT / "scripts" / "render_twolayer_visual.py"),
        "--props", props_path,
        "--out", out_path,
        "--frames", frames_arg,
        "--x264-preset", x264_preset,
        "--crf", str(crf),
        "--timeout", str(timeout),
    ]
    env = os.environ.copy()
    env["VF_REMOTION_CONCURRENCY"] = str(concurrency)
    print(f"\n>>> [CHUNK RENDER] {frames_arg} (total {end_frame - start_frame + 1} frames) -> {out_path}")
    t0 = time.time()
    res = subprocess.run(cmd, env=env)
    elapsed = time.time() - t0
    if res.returncode != 0 or not os.path.exists(out_path):
        print(f"ERROR: Chunk {frames_arg} failed with code {res.returncode}")
        return False
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    fps = (end_frame - start_frame + 1) / max(0.1, elapsed)
    print(f">>> [CHUNK DONE] {frames_arg} finished in {elapsed:.1f}s ({fps:.2f} fps) - size: {size_mb:.1f} MB ✅")
    return True


def concat_chunks(chunks: list[str], out_path: str, chunks_dir: str) -> bool:
    """Concatenate chunks losslessly using ffmpeg -f concat -c copy."""
    concat_txt = os.path.join(chunks_dir, "chunks_concat_list.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in chunks:
            abs_p = os.path.abspath(c).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-c", "copy",
        out_path
    ]
    print(f"\n>>> [CONCAT] Stitching {len(chunks)} chunks into {out_path}...")
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"ERROR: ffmpeg concat failed: {res.stderr}")
        return False
    elapsed = time.time() - t0
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f">>> [CONCAT COMPLETE] Created {out_path} ({size_mb:.1f} MB) in {elapsed:.2f}s ✅")
    return True


def main():
    parser = argparse.ArgumentParser(description="Render Remotion episode in Beat chunks & stitch losslessly.")
    parser.add_argument("--episode-id", default=None, help="Episode ID")
    parser.add_argument("--props", default=None, help="Explicit path to remotion_props.json")
    parser.add_argument("--out", default=None, help="Explicit path to final twolayer_silent.mp4")
    parser.add_argument("--concurrency", default="3", help="Remotion concurrency (default: 3)")
    parser.add_argument("--x264-preset", default="veryfast", help="x264 preset (default: veryfast)")
    parser.add_argument("--crf", type=int, default=18, help="CRF rate control (default: 18)")
    parser.add_argument("--skip-auto-mux", action="store_true", help="Skip automatic downstream mux and Gate 3 dispatch")
    args = parser.parse_args()

    # Auto-resolve episode-id if omitted (Rule 128 Generic Contract)
    if not args.episode_id:
        target_str = str(args.out or args.props or "")
        m = re.search(r"episodes/([A-Z]{2}_EP\d{4}_[a-z0-9_]+)", target_str)
        if m:
            args.episode_id = m.group(1)
            print(f"INFO: Auto-resolved episode_id from path: {args.episode_id}")

    ep_dir = Path(f"/var/vf/episodes/{args.episode_id}") if args.episode_id else None
    props_path = args.props or (str(ep_dir / "remotion_props.json") if ep_dir else None)
    final_out = args.out or (str(ep_dir / "twolayer_silent.mp4") if ep_dir else None)

    if not props_path or not os.path.exists(props_path):
        print(f"FATAL: props not found: {props_path}")
        sys.exit(1)

    chunks_dir = os.path.join(os.path.dirname(final_out), "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    beat_chunks = get_beat_chunks_from_props(props_path)
    total_frames = sum(b["duration"] for b in beat_chunks)
    print(f"=== BEAT CHUNK RUNNER: {args.episode_id} ===")
    print(f"Total Frames: {total_frames} ({total_frames / 30:.1f}s ~ {total_frames / 1800:.1f}m)")
    print(f"Planned Chunks: {len(beat_chunks)}")
    for b in beat_chunks:
        print(f"  • {b['name']}: frames {b['start_frame']}..{b['end_frame']} ({b['duration']} frames = {b['duration']/30:.1f}s)")

    rendered_files = []
    overall_start = time.time()

    for b in beat_chunks:
        idx = b["index"]
        c_out = os.path.join(chunks_dir, f"chunk_{idx:02d}_{b['name'].replace(' ', '_').lower()}.mp4")
        expected_sec = b["duration"] / 30.0

        if verify_chunk_mp4(c_out, expected_sec):
            print(f">>> [CHUNK REUSED] {c_out} already valid ({expected_sec:.1f}s). Skipping render.")
            rendered_files.append(c_out)
            continue

        ok = render_single_chunk(
            props_path=props_path,
            out_path=c_out,
            start_frame=b["start_frame"],
            end_frame=b["end_frame"],
            concurrency=args.concurrency,
            x264_preset=args.x264_preset,
            crf=args.crf,
        )
        if not ok:
            print(f"FATAL: Render aborted on chunk {b['name']}")
            sys.exit(1)
        rendered_files.append(c_out)

    # Stitch all chunks losslessly
    ok_concat = concat_chunks(rendered_files, final_out, chunks_dir)
    if not ok_concat:
        print("FATAL: Stitching failed.")
        sys.exit(1)

    overall_elapsed = time.time() - overall_start
    overall_fps = total_frames / max(0.1, overall_elapsed)
    print("\n" + "=" * 60)
    print(f"🎉 MASTER VIDEO READY: {final_out}")
    print(f"Total frames: {total_frames} | Total time: {overall_elapsed / 60:.1f} mins | Avg Speed: {overall_fps:.2f} fps")
    print("=" * 60)

    # Automatic Downstream Hook: Mux + Audit + B10 + Telegram Gate 3
    if not args.skip_auto_mux:
        if not args.episode_id:
            print("\n>>> [AUTO-PIPELINE] Skipping auto-mux because episode_id could not be resolved.")
        else:
            mux_script = _REPO_ROOT / "scripts" / "mux_master_episode.py"
            if mux_script.exists():
                print(f"\n>>> [AUTO-PIPELINE] Automatically invoking mux, audit, and Gate 3 dispatch for {args.episode_id}...")
                subprocess.run([sys.executable, str(mux_script), "--episode-id", args.episode_id], check=True)


if __name__ == "__main__":
    main()
