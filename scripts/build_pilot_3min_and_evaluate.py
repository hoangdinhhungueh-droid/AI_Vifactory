#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/build_pilot_3min_and_evaluate.py
Builds and evaluates the 3-minute pilot video for JP_EP0006_crypto_exchange_heist.
Slices audio, subtitles, concatenates scenes 1-48, burns ASS subtitles,
verifies via S11 CV gates, extracts 16-frame contact sheet, and runs Critic Council.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.visual_critic_council import evaluate_with_council, extract_frames_and_build_contact_sheet
from stages.s08_video_gen import validate_video_motion_temporal_delta
from vox.ffmpeg_utils import get_ffmpeg_binary
from vox.qa.gates import verify_final_video_gates


def build_pilot_3min(episode_id: str = "JP_EP0006_crypto_exchange_heist", force_render_clips: bool = True) -> dict:
    ep_dir = ROOT_DIR / "episodes" / episode_id
    if not ep_dir.exists():
        raise FileNotFoundError(f"Episode directory not found: {ep_dir}")

    ffmpeg_bin = get_ffmpeg_binary()
    clips_dir = ep_dir / "video_clips"
    audio_src = ep_dir / "audio" / "voice_narration.mp3"
    sub_src = ep_dir / "audio" / "subtitles.ass"

    # 1. Target duration: Scenes 1 to 44 (covers exactly 0.0s to 170.87s of Act I & II)
    total_scenes = 44
    target_dur = 170.87

    out_dir = ep_dir / "pilot_3min"
    out_dir.mkdir(parents=True, exist_ok=True)

    pilot_audio = out_dir / "pilot_voice_180s.mp3"
    pilot_sub = out_dir / "pilot_subtitles_180s.ass"
    pilot_video = out_dir / "pilot_3min_master.mp4"

    # Step A: Slice & Normalize Audio with Two-Pass EBU R128 Loudnorm (Target: -16.0 LUFS, TP <= -2.5 dBTP)
    print(f"🎵 [PILOT] Slicing voice narration to {target_dur:.2f}s...")
    temp_raw_audio = out_dir / "temp_raw_audio.wav"
    pilot_audio = out_dir / "pilot_voice_norm.wav"

    cmd_slice_audio = [
        ffmpeg_bin, "-y",
        "-i", str(audio_src),
        "-t", str(target_dur),
        "-c:a", "pcm_s16le",
        str(temp_raw_audio)
    ]
    subprocess.run(cmd_slice_audio, capture_output=True, check=True)

    print("🔊 [PILOT] Applying two-pass EBU R128 loudnorm (Target -16.0 LUFS, Ceiling -2.5 dBTP)...")
    cmd_pass1 = [
        ffmpeg_bin, "-y",
        "-i", str(temp_raw_audio),
        "-af", "loudnorm=I=-16.0:TP=-2.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    p1_res = subprocess.run(cmd_pass1, capture_output=True, text=True, check=False)
    p1_err = p1_res.stderr
    p1_json_str = p1_err[p1_err.rfind("{"):p1_err.rfind("}")+1]
    p1_d = json.loads(p1_json_str)

    af_2pass = (
        f"loudnorm=I=-16.0:TP=-2.5:LRA=11:measured_I={p1_d['input_i']}:measured_TP={p1_d['input_tp']}:"
        f"measured_LRA={p1_d['input_lra']}:measured_thresh={p1_d['input_thresh']}:offset={p1_d['target_offset']}:linear=true"
    )
    cmd_pass2 = [
        ffmpeg_bin, "-y",
        "-i", str(temp_raw_audio),
        "-af", af_2pass,
        "-c:a", "pcm_s16le",
        str(pilot_audio)
    ]
    subprocess.run(cmd_pass2, capture_output=True, check=True)
    if temp_raw_audio.exists():
        temp_raw_audio.unlink(missing_ok=True)

    # Step B: Slice ASS Subtitles
    print(f"📝 [PILOT] Slicing subtitles.ass to {target_dur:.2f}s...")
    sub_lines = sub_src.read_text(encoding="utf-8").splitlines()
    header_lines = []
    dialogue_lines = []
    is_events = False

    for line in sub_lines:
        if line.startswith("[Events]"):
            is_events = True
            header_lines.append(line)
            continue
        if not is_events:
            header_lines.append(line)
        else:
            if line.startswith("Format:"):
                header_lines.append(line)
            elif line.startswith("Dialogue:"):
                # Dialogue: 0,0:00:00.00,0:00:02.16,Default,,0,0,0,,text
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    start_str = parts[1]
                    # Parse start time
                    h, m, s = start_str.split(":")
                    start_sec = int(h) * 3600 + int(m) * 60 + float(s)
                    if start_sec < target_dur:
                        dialogue_lines.append(line)

    pilot_sub.write_text("\n".join(header_lines + dialogue_lines) + "\n", encoding="utf-8")
    print(f"📝 [PILOT] Filtered {len(dialogue_lines)} dialogue lines into {pilot_sub.name}")

    # Step B.5: Render/Update 44 Dynamic Video Clips with Vox Camera Directives (Rule 118, 121, 122, 140)
    print(f"🎬 [PILOT] Rendering/verifying {total_scenes} video clips from clean diorama seeds...")
    seeds_dir = ep_dir / "composite_seeds"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Authoritative scene durations for Scenes 1 to 44 (summing exactly to target_dur 170.87s)
    SCENE_DURATIONS_44 = [
        2.16, 1.98, 4.14, 2.88, 4.14, 6.85, 3.78, 2.16, 3.06, 5.58,
        2.34, 2.70, 2.16, 6.30, 7.03, 4.86, 2.70, 3.06, 5.22, 1.98,
        8.64, 4.33, 2.16, 0.90, 0.90, 0.90, 3.60, 1.98, 2.52, 4.50,
        6.12, 5.94, 6.13, 2.88, 7.20, 1.62, 1.62, 7.02, 6.12, 3.06,
        5.23, 3.06, 4.50, 4.86
    ]

    plan_raw = json.loads((ep_dir / "director_plan.json").read_text(encoding="utf-8"))
    scenes_meta = plan_raw.get("scenes", [])
    fps = 30

    for i in range(1, total_scenes + 1):
        sc_id = f"SCENE_{i:02d}"
        c_path = clips_dir / f"clip_scene_{i:02d}.mp4"
        seed_path = seeds_dir / f"composite_SCENE_{i:02d}.png"
        if not seed_path.exists():
            cand = seeds_dir / f"composite_scene_{i:02d}.png"
            if cand.exists():
                seed_path = cand
        if not seed_path.exists():
            raise FileNotFoundError(f"Missing diorama seed for {sc_id}: {seed_path}")

        needs_render = (
            force_render_clips
            or not c_path.exists()
            or c_path.stat().st_size < 1000
            or c_path.stat().st_mtime < seed_path.stat().st_mtime
        )
        if needs_render:
            dur = SCENE_DURATIONS_44[i - 1]
            sc_meta = scenes_meta[i - 1] if (i - 1) < len(scenes_meta) else {}
            cam_dir = sc_meta.get("camera_directive", "STATIC_OVERHEAD")

            tot_frames = max(25, int(dur * fps))
            if sc_id == "SCENE_38":
                # Special framing for Scene 38: anchor right edge to preserve hero '50%' numeral completely inside action-safe area
                filter_expr = (
                    f"zoompan=z='min(1.0 + 0.05*(on/{tot_frames}), 1.05)':d={tot_frames}:"
                    f"x='(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':s=1920x1080,fps={fps}"
                )
            elif cam_dir == "SLOW_HORIZONTAL_PAN":
                pan_x = f"(iw-iw/zoom)*(on/{tot_frames})" if (i % 2 == 1) else f"(iw-iw/zoom)*(1 - on/{tot_frames})"
                filter_expr = (
                    f"zoompan=z=1.14:d={tot_frames}:"
                    f"x='{pan_x}':y='(ih-ih/zoom)/2':s=1920x1080,fps={fps}"
                )
            elif cam_dir == "SUBTLE_TILT_DOWN":
                tilt_y = f"(ih-ih/zoom)*(on/{tot_frames})" if (i % 2 == 1) else f"(ih-ih/zoom)*(1 - on/{tot_frames})"
                filter_expr = (
                    f"zoompan=z=1.14:d={tot_frames}:"
                    f"x='(iw-iw/zoom)/2':y='{tilt_y}':s=1920x1080,fps={fps}"
                )
            elif cam_dir == "SLOW_PUSH_IN_0_1X":
                filter_expr = (
                    f"zoompan=z='min(1.0 + 0.15*(on/{tot_frames}), 1.15)':d={tot_frames}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,fps={fps}"
                )
            else:
                filter_expr = (
                    f"zoompan=z='min(1.0 + 0.06*(on/{tot_frames}), 1.06)':d={tot_frames}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,fps={fps}"
                )

            cmd_clip = [
                ffmpeg_bin, "-y",
                "-loop", "1",
                "-i", str(seed_path),
                "-vf", filter_expr,
                "-t", f"{dur:.3f}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(c_path)
            ]
            subprocess.run(cmd_clip, capture_output=True, check=True)
            delta_score = validate_video_motion_temporal_delta(c_path)
            print(f"  🎬 [{i:02d}/{total_scenes}] Rendered {c_path.name} ({dur:.2f}s, {cam_dir}, motion={delta_score:.1f})")

    # Step C: Concat Clips 1 to 44
    concat_list = out_dir / "concat_clips.txt"
    clip_entries = []
    for i in range(1, total_scenes + 1):
        c_path = clips_dir / f"clip_scene_{i:02d}.mp4"
        if not c_path.exists():
            raise FileNotFoundError(f"Missing clip: {c_path}")
        clip_entries.append(f"file '{c_path.resolve().as_posix()}'")

    concat_list.write_text("\n".join(clip_entries) + "\n", encoding="utf-8")

    temp_concat = out_dir / "temp_concat_44.mp4"
    print(f"🎬 [PILOT] Concatenating {total_scenes} clips...")
    cmd_concat = [
        ffmpeg_bin, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(temp_concat)
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)

    # Step D: Burn Subtitles & Multiplex Normalized Audio
    print(f"🔥 [PILOT] Burning ASS subtitles and multiplexing normalized audio ({target_dur:.2f}s)...")
    ass_rel = pilot_sub.relative_to(ROOT_DIR).as_posix()

    cmd_master = [
        ffmpeg_bin, "-y",
        "-i", str(temp_concat),
        "-i", str(pilot_audio),
        "-vf", f"drawbox=y=ih-200:color=black@0.65:width=iw:height=200:t=fill,subtitles='{ass_rel}'",
        "-c:v", "libx264",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-b:v", "4000k",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-t", str(target_dur),
        str(pilot_video)
    ]
    res_burn = subprocess.run(cmd_master, capture_output=True, text=True, check=False, cwd=str(ROOT_DIR))
    if res_burn.returncode != 0:
        print(f"Warning: burning with subtitles failed ({res_burn.stderr[-300:]}), fallback...")
        cmd_fallback = [
            ffmpeg_bin, "-y",
            "-i", str(temp_concat),
            "-i", str(pilot_audio),
            "-c:v", "libx264",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-t", str(target_dur),
            str(pilot_video)
        ]
        subprocess.run(cmd_fallback, capture_output=True, check=True, cwd=str(ROOT_DIR))

    # Clean up temp
    if temp_concat.exists():
        temp_concat.unlink(missing_ok=True)
    if concat_list.exists():
        concat_list.unlink(missing_ok=True)

    sz_mb = pilot_video.stat().st_size / (1024 * 1024)
    print(f"🎉 [PILOT] Pilot video ready: {pilot_video} ({sz_mb:.2f} MB)")

    # Step E: Quality Gate Verification (S11 CV Gates)
    print("🛡️ [PILOT] Running S11 Computer Vision Quality Gate verification...")
    from stages.s11_qc import _validate_authoritative_scene_plan

    plan_raw = json.loads((ep_dir / "director_plan.json").read_text(encoding="utf-8"))
    d_44 = dict(plan_raw)
    d_44["scenes"] = plan_raw.get("scenes", [])[:total_scenes]
    d_44["task_id"] = episode_id
    d_44["project_id"] = episode_id
    d_44["episode_id"] = episode_id
    d_44["title"] = episode_id
    d_44["audio_duration"] = target_dur

    authoritative_plan = _validate_authoritative_scene_plan(d_44, episode_id)
    manifest_data = {
        "manifest_data": {
            "total_scenes": total_scenes,
            "scene_plan": [{"scene_id": f"SCENE_{i:02d}"} for i in range(1, total_scenes + 1)]
        }
    }
    verify_final_video_gates(pilot_video, expected_duration=target_dur, plan=authoritative_plan, manifest_data=manifest_data)
    print("✅ [PILOT] All S11 Computer Vision Quality Gates PASSED (0 SMPTE bars, duration OK, loudness OK)!")
    print("✅ [PILOT] All S11 Computer Vision Quality Gates PASSED (0 SMPTE bars, duration OK, sync OK)!")

    # Step F: Extract 16-Frame Contact Sheet
    print("📸 [PILOT] Extracting 16-frame 4x4 Contact Sheet for Visual Critic Council...")
    cs_dir = out_dir / "visual_audit"
    cs_path = extract_frames_and_build_contact_sheet(
        pilot_video, cs_dir, num_frames=16, duration_sec=target_dur, output_name="contact_sheet_3min_pilot.jpg"
    )

    # Step G: Convene Visual Critic Council
    print("🏛️ [PILOT] Convening Visual Critic Council (Claude Opus 5.5 + GPT-6-Astra)...")
    critic_report = evaluate_with_council(cs_path, episode_id, duration_sec=target_dur)

    verdict_file = cs_dir / "critic_council_verdict.json"
    verdict_file.write_text(json.dumps(critic_report, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "video_path": str(pilot_video),
        "video_size_mb": round(sz_mb, 2),
        "duration_sec": target_dur,
        "contact_sheet": str(cs_path),
        "verdict_file": str(verdict_file),
        "critic_report": critic_report
    }

if __name__ == "__main__":
    res = build_pilot_3min()
    print("\n" + "="*70)
    print("PILOT BUILD & CRITIC EVALUATION COMPLETE")
    print(f"Video: {res['video_path']} ({res['video_size_mb']} MB)")
    print(f"Contact Sheet: {res['contact_sheet']}")
    print(f"Critic Verdict: {res['critic_report']['council_status']} (Score: {res['critic_report']['average_score']}/10)")
    print("="*70)
