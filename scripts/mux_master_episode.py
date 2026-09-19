#!/usr/bin/env python3
"""
scripts/mux_master_episode.py

Generic Master Audio/Video Muxer for AI Video Factory (Step S7 / Gate B8).
Adheres to Rule 125, Rule 128, Rule 130, Rule 135.
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.services.mpt_ported.audio_normalize import normalize_audio


def parse_args():
    parser = argparse.ArgumentParser(description="Generic Master Muxer (S7/B8)")
    parser.add_argument("--episode-id", required=True, help="Episode ID e.g. EN_EP0003_san_diego_daycare_fraud")
    parser.add_argument("--episodes-dir", default="/var/vf/episodes", help="Episodes base directory")
    parser.add_argument("--skip-b9", action="store_true", help="Skip B9 quality probe")
    return parser.parse_args()


async def run_mux(episode_id: str, episodes_dir: str, run_b9: bool = True):
    ep_dir = Path(episodes_dir) / episode_id
    if not ep_dir.exists():
        raise FileNotFoundError(f"Episode directory not found: {ep_dir}")

    silent_video = ep_dir / "twolayer_silent.mp4"
    if not silent_video.exists():
        raise FileNotFoundError(f"Silent visual video not found: {silent_video}")

    tts_raw = ep_dir / "tts_out.mp3"
    if not tts_raw.exists():
        raise FileNotFoundError(f"TTS audio not found: {tts_raw}")

    audio_norm = ep_dir / "audio_norm.mp3"
    bgm_master = ep_dir / "bgm_master.mp3"
    final_video = ep_dir / "final_169.mp4"

    # Step 1: Loudness Normalization to -14 LUFS / True Peak -1.5
    if not audio_norm.exists() or audio_norm.stat().st_size == 0:
        print(f"[MUX] Normalizing TTS audio {tts_raw} -> {audio_norm}...")
        res = await normalize_audio(str(tts_raw), str(audio_norm), platform="spotify", true_peak=-1.5)
        print(f"[MUX] Audio normalized: {res}")
    else:
        print(f"[MUX] Using existing normalized audio: {audio_norm}")

    # Probe durations
    def probe_dur(p):
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(p)
        ]).decode().strip()
        return float(out or 0.0)

    v_dur = probe_dur(silent_video)
    a_dur = probe_dur(audio_norm)
    print(f"[MUX] Probed durations: Video={v_dur:.3f}s, Audio={a_dur:.3f}s (Coverage: {v_dur/a_dur*100:.2f}%)")

    # Step 2: Build FFmpeg command with Sidechain Ducking
    if bgm_master.exists():
        bgm_dur = probe_dur(bgm_master)
        loop_args = ["-stream_loop", "-1"] if bgm_dur < a_dur - 1.0 else []
        af = (
            "[1:a]volume=1.0,asplit=2[tts_clean][tts_sc];"
            "[2:a]volume=0.09,highpass=f=85,equalizer=f=2500:t=q:w=1.5:g=-5[bgm_eq];"
            "[bgm_eq][tts_sc]sidechaincompress=threshold=0.02:ratio=10:attack=80:release=350[bgm_ducked];"
            "[tts_clean][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,alimiter=limit=0.84:attack=5:release=50[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(silent_video),
            "-i", str(audio_norm),
            *loop_args, "-i", str(bgm_master),
            "-filter_complex", af,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-t", f"{a_dur + 0.5:.3f}",
            str(final_video)
        ]
    else:
        print("[MUX] No BGM found; muxing voice track only")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(silent_video),
            "-i", str(audio_norm),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-t", f"{a_dur + 0.5:.3f}",
            str(final_video)
        ]

    print(f"[MUX] Executing FFmpeg mux to {final_video}...")
    subprocess.run(cmd, check=True)
    size_mb = final_video.stat().st_size / (1024 * 1024)
    print(f"[MUX] Master video created: {final_video} ({size_mb:.2f} MB) ✅")

    # Step 3: Run B9 Quality Probe
    if run_b9:
        probe_script = _REPO_ROOT / "scripts" / "run_b9_quality_probe.py"
        if probe_script.exists():
            print(f"[MUX] Running B9 Quality Probe...")
            subprocess.run([sys.executable, str(probe_script), "--episode", episode_id], check=True)

    # Step 4: Update state
    state_file = ep_dir / "b4b10_state.json"
    state_data = {}
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            state_data = {}
    state_data.update({
        "stage": "done-render-only",
        "status": "ok",
        "episode_id": episode_id,
        "master_video": str(final_video),
        "video_duration_s": v_dur,
        "audio_duration_s": a_dur
    })
    state_file.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[MUX] State updated at {state_file} ✅")
    return final_video


if __name__ == "__main__":
    import asyncio
    args = parse_args()
    asyncio.run(run_mux(args.episode_id, args.episodes_dir, run_b9=not args.skip_b9))
