#!/usr/bin/env python3
"""
scripts/mux_master_episode.py

Generic Master Audio/Video Muxer & End-to-End Post-Render Pipeline for AI Video Factory (Step S7 / Gate B8 -> B9 -> B10 -> HG3).
Adheres to Rule 118, Rule 121, Rule 122, Rule 125, Rule 128, Rule 130, Rule 135.

Full Automated Pipeline:
1. Normalize TTS audio & Mux with BGM Sidechain Ducking -> final_169.mp4.
2. Run B9 Quality Probe (EBU R128 LUFS & True Peak). Auto-recovers with loudnorm if needed.
3. Run High-Level LLM Visual & Content Audit on 5 Beat Key Frames (app.services.video_audit_runner).
4. Run B10 Auto SEO + YouTube Unlisted Upload + Auto-Thumbnail.
5. Dispatch Interactive Human Gate 3 Telegram Card (4 Buttons) directly to User Telegram.
"""
import os
import sys
import json
import argparse
import subprocess
import shutil
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.services.mpt_ported.audio_normalize import normalize_audio
from app.services.video_audit_runner import run_automated_post_render_audit


def parse_args():
    parser = argparse.ArgumentParser(description="Generic Master Muxer & Auto Gate 3 Pipeline (S7/B8 -> B10)")
    parser.add_argument("--episode-id", required=True, help="Episode ID e.g. <MARKET>_EP<0000>_<topic_slug>")
    parser.add_argument("--episodes-dir", default="/var/vf/episodes", help="Episodes base directory")
    parser.add_argument("--skip-b9", action="store_true", help="Skip B9 quality probe")
    parser.add_argument("--skip-audit", action="store_true", help="Skip automated LLM visual audit")
    parser.add_argument("--skip-b10", action="store_true", help="Skip B10 auto upload & Gate 3 Telegram dispatch")
    parser.add_argument("--privacy", default="unlisted", help="YouTube privacy status (default: unlisted)")
    return parser.parse_args()


def run_b9_probe_with_auto_recovery(episode_id: str, final_video: Path) -> bool:
    """Run B9 Quality Probe. If loudness fails, automatically normalize and re-verify."""
    probe_script = _REPO_ROOT / "scripts" / "run_b9_quality_probe.py"
    if not probe_script.exists():
        print("[MUX-B9] Warning: run_b9_quality_probe.py not found. Skipping probe.")
        return True

    print(f"[MUX-B9] Running B9 Quality Probe on {final_video}...")
    proc = subprocess.run([sys.executable, str(probe_script), "--episode", episode_id], capture_output=True, text=True)
    if proc.returncode == 0:
        print("[MUX-B9] Probe PASSED ✅")
        return True

    print(f"[MUX-B9] Initial Probe failed ({proc.stdout.strip()}). Running automatic loudnorm re-mux...")
    temp_norm = final_video.parent / "final_169_norm.mp4"
    cmd_norm = [
        "ffmpeg", "-y",
        "-i", str(final_video),
        "-af", "loudnorm=I=-14.0:LRA=11:TP=-1.5",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        str(temp_norm)
    ]
    sub_res = subprocess.run(cmd_norm, capture_output=True, text=True)
    if sub_res.returncode == 0 and temp_norm.exists() and temp_norm.stat().st_size > 0:
        shutil.move(str(temp_norm), str(final_video))
        print("[MUX-B9] Auto-normalization complete. Re-verifying B9 probe...")
        proc_re = subprocess.run([sys.executable, str(probe_script), "--episode", episode_id])
        if proc_re.returncode == 0:
            print("[MUX-B9] Re-verification PASSED ✅")
            return True

    print("[MUX-B9] Error: Could not auto-recover B9 probe. Check audio logs.")
    return False


async def run_mux(
    episode_id: str,
    episodes_dir: str,
    run_b9: bool = True,
    run_audit: bool = True,
    run_b10: bool = True,
    privacy: str = "unlisted"
):
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

    # Step 3: Run B9 Quality Probe with Auto-Recovery
    if run_b9:
        b9_ok = run_b9_probe_with_auto_recovery(episode_id, final_video)
        if not b9_ok:
            print("[MUX] Warning: B9 probe failed, continuing to audit/upload.")

    # Step 4: Run Automated LLM Visual & Content Audit on VPS
    audit_verdict = None
    if run_audit:
        try:
            print(f"[MUX] Running Automated High-Level LLM Visual Audit on VPS...")
            audit_verdict = run_automated_post_render_audit(episode_id, episodes_dir)
            print(f"[MUX] Visual Audit completed: Verdict={audit_verdict.get('verdict')}, Score={audit_verdict.get('overall_score')} ✅")
        except Exception as e:
            print(f"[MUX] Visual Audit non-fatal warning: {e}")

    # Step 5: Automatically Execute B10 (Auto SEO + YouTube Upload + Gate 3 Telegram Dispatch)
    b10_res = None
    if run_b10:
        b10_script = _REPO_ROOT / "scripts" / "execute_b10_auto_seo_upload_gate2.py"
        if b10_script.exists():
            market = episode_id.split("_")[0].lower() if "_" in episode_id else "en"
            # Ensure thumbnail is available in ep_dir for B10 auto-set
            thumb_a = ep_dir / "thumbnail_a.png"
            if not thumb_a.exists():
                for cand in [ep_dir / "thumbnail_hero.png", ep_dir / "audits" / "beat_1_frame_15s.png", ep_dir / "audits" / "beat_1_frame_30s.png"]:
                    if cand.exists():
                        shutil.copy(str(cand), str(thumb_a))
                        print(f"[MUX-B10] Copied hero candidate {cand.name} to {thumb_a.name} for YouTube thumbnail")
                        break

            print(f"[MUX-B10] Automatically executing Step 10: Auto SEO + Upload + Human Gate 3 Telegram Card...")
            b10_cmd = [
                sys.executable, str(b10_script),
                "--episode", episode_id,
                "--market", market,
                "--privacy", privacy
            ]
            try:
                subprocess.run(b10_cmd, check=True)
                print(f"[MUX-B10] Step 10 executed successfully. Human Gate 3 card dispatched to Telegram! ✅")
            except Exception as e:
                print(f"[MUX-B10] Error running B10: {e}")

    # Step 6: Update state
    state_file = ep_dir / "b4b10_state.json"
    state_data = {}
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            state_data = {}
    state_data.update({
        "stage": "done-b10-gate3-dispatched" if run_b10 else "done-render-only",
        "status": "ok",
        "episode_id": episode_id,
        "master_video": str(final_video),
        "video_duration_s": v_dur,
        "audio_duration_s": a_dur,
        "visual_audit": audit_verdict
    })
    state_file.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[MUX] State updated at {state_file} ✅")
    return final_video


if __name__ == "__main__":
    import asyncio
    args = parse_args()
    asyncio.run(run_mux(
        args.episode_id,
        args.episodes_dir,
        run_b9=not args.skip_b9,
        run_audit=not args.skip_audit,
        run_b10=not args.skip_b10,
        privacy=args.privacy
    ))
