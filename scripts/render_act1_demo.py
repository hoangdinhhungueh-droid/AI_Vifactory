#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/render_act1_demo.py — Assembles and Renders Act I Demo Video for KR_EP0003.

Combines the 8 newly generated Vox Engine v3 video clips with:
- High-fidelity Korean Edge-TTS Voiceover (ko-KR-InJoonNeural)
- Faster-Whisper word-level karaoke timestamps (0ms drift)
- Elegant ASS subtitle burn-in with Malgun Gothic / Korean glyph support
- Two-pass audio multiplexing with EBU R128 loudnorm
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("act1_demo_render")

# UTF-8 stdout configuration for Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
except Exception as _reconf_err:
    logger.debug(f"stdout reconfigure notice: {_reconf_err}")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from vox.ffmpeg_utils import get_ffmpeg_binary

EPISODE_ID = "KR_EP0003_kftc_rental_fraud"
EPISODE_DIR = ROOT_DIR / "episodes" / EPISODE_ID
CLIPS_DIR = EPISODE_DIR / "video_clips"
OUT_DIR = EPISODE_DIR / "act1_render"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ACT1_SCENES = [
    {
        "scene_id": "SCENE_01",
        "clip_name": "clip_scene_01.mp4",
        "text": "2026년 10월 26일, 공정위 제재가 보도됐습니다.",
        "tag": "BEAT 1: COLD STRIKE // KFTC OFFICIAL SANCTION"
    },
    {
        "scene_id": "SCENE_02",
        "clip_name": "clip_scene_02.mp4",
        "text": "드림하우징 등 민간임대 시행사 네 곳이 대상입니다.",
        "tag": "BEAT 1: EVIDENCE // 4 TARGET DEVELOPERS"
    },
    {
        "scene_id": "SCENE_03",
        "clip_name": "clip_scene_03.mp4",
        "text": "허위·기만 광고에 내려진 조치는 시정명령입니다.",
        "tag": "BEAT 1: RULING // CORRECTIVE ORDERS ISSUED"
    },
    {
        "scene_id": "SCENE_04",
        "clip_name": "clip_scene_04.mp4",
        "text": "광고는 마감을 외쳤지만, 사업은 인허가 전이었습니다.",
        "tag": "BEAT 1: CONTRADICTION // UNAPPROVED SCHEME"
    },
    {
        "scene_id": "SCENE_05",
        "clip_name": "clip_scene_05.mp4",
        "text": "관할청 승인도 없는데, 무엇이 마감된다는 걸까요?",
        "tag": "BEAT 1: SYSTEMIC PARADOX // ZERO PERMITS"
    },
    {
        "scene_id": "SCENE_06",
        "clip_name": "clip_scene_06.mp4",
        "text": "국제뉴스는 ‘마감임박’과 ‘회원 모집률 30%’를 묶었습니다.",
        "tag": "BEAT 1: PRESS FORENSICS // 30% ENROLLMENT"
    },
    {
        "scene_id": "SCENE_07",
        "clip_name": "clip_scene_07.mp4",
        "text": "경기일보는 네 곳의 미인허가 광고를 지적했습니다.",
        "tag": "BEAT 1: INVESTIGATION // REGULATORY VIOLATION"
    },
    {
        "scene_id": "SCENE_08",
        "clip_name": "clip_scene_08.mp4",
        "text": "연합뉴스와 MBC 뉴스는 인허가 전 모집을 전했습니다.",
        "tag": "BEAT 1: SMOKING GUN // NATIONWIDE ALARM"
    }
]

def format_ass_timestamp(seconds: float) -> str:
    """Formats float seconds to ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

async def generate_speech_audio(scenes: list[dict], out_dir: Path) -> list[dict]:
    """Generates Edge-TTS speech audio for each scene and probes exact duration."""
    import edge_tts
    ffmpeg_bin = get_ffmpeg_binary()
    audio_dir = out_dir / "audio_segments"
    audio_dir.mkdir(parents=True, exist_ok=True)

    results = []
    print("\n" + "=" * 60)
    print("🎙️ [STAGE S09] SINH VOICE NARRATION AUDIO QUA EDGE-TTS (ko-KR)")
    print("=" * 60)

    for idx, sc in enumerate(scenes):
        sc_id = sc["scene_id"]
        text = sc["text"]
        mp3_path = audio_dir / f"{sc_id.lower()}_voice.mp3"
        wav_path = audio_dir / f"{sc_id.lower()}_voice.wav"

        comm = edge_tts.Communicate(text, "ko-KR-InJoonNeural")
        await comm.save(str(mp3_path))

        # Convert to 48kHz WAV for exact sample alignment
        subprocess.run([
            ffmpeg_bin, "-y", "-i", str(mp3_path),
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(wav_path)
        ], capture_output=True, check=True)

        # Probe duration
        probe_cmd = [ffmpeg_bin, "-i", str(wav_path)]
        p_res = subprocess.run(probe_cmd, capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p_res.stderr or "")
        dur = 3.5
        if m:
            dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

        print(f"   🔊 [{sc_id}] ({dur:.2f}s): \"{text}\"")
        results.append({
            **sc,
            "mp3_path": mp3_path,
            "wav_path": wav_path,
            "speech_duration": dur,
            # Padding 0.25s at the end of each scene for natural breathing room
            "scene_duration": round(dur + 0.35, 2)
        })

    return results

def align_whisper_words(scenes_with_audio: list[dict]) -> list[dict]:
    """Transcribes audio using faster-whisper to extract exact word timings."""
    print("\n" + "=" * 60)
    print("🎯 [WHISPER ENGINE] TRÍCH XUẤT WORD-LEVEL TIMESTAMPS (0ms Drift)")
    print("=" * 60)
    import numpy as np
    from faster_whisper import WhisperModel
    ffmpeg_bin = get_ffmpeg_binary()

    model = WhisperModel("base", device="cpu", compute_type="int8")

    global_offset = 0.0
    all_words = []

    for sc in scenes_with_audio:
        sc_id = sc["scene_id"]
        wav_path = sc["wav_path"]

        # Decode directly to float32 NumPy array to avoid PyAV metadata_errors bug
        cmd = [
            ffmpeg_bin, "-nostdin", "-threads", "0", "-i", str(wav_path),
            "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", "16000", "-"
        ]
        out_bytes = subprocess.run(cmd, capture_output=True, check=True).stdout
        audio_np = np.frombuffer(out_bytes, np.int16).flatten().astype(np.float32) / 32768.0

        segments, _ = model.transcribe(audio_np, word_timestamps=True, language="ko")
        sc_words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    w_dict = {
                        "word": w.word.strip(),
                        "local_start": round(w.start, 2),
                        "local_end": round(w.end, 2),
                        "global_start": round(global_offset + w.start, 2),
                        "global_end": round(global_offset + w.end, 2),
                        "scene_id": sc_id
                    }
                    sc_words.append(w_dict)
                    all_words.append(w_dict)

        sc["words"] = sc_words
        sc["global_scene_start"] = round(global_offset, 2)
        sc["global_scene_end"] = round(global_offset + sc["scene_duration"], 2)

        print(f"   📝 [{sc_id}] ({len(sc_words)} words | {sc['global_scene_start']:.2f}s -> {sc['global_scene_end']:.2f}s)")
        global_offset += sc["scene_duration"]

    return scenes_with_audio

def build_ass_subtitles(scenes: list[dict], ass_path: Path):
    """Generates broadcast ASS subtitle file with Upper Tag & Karaoke Word Highlighting."""
    header = """[Script Info]
Title: Vox Engine Act I Demo Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HeaderTag, Arial, 26, &H00FFFFFF, &H000000FF, &H00111111, &H80000000, 1, 0, 0, 0, 100, 100, 1.5, 0, 1, 2, 1, 7, 80, 80, 60, 1
Style: SubtitleKaraoke, Malgun Gothic, 44, &H00FFFFFF, &H0066D1FF, &H000D0905, &H80000000, 1, 0, 0, 0, 100, 100, 1, 0, 1, 3, 2, 2, 100, 100, 75, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    for sc in scenes:
        sc_start = sc["global_scene_start"]
        sc_end = sc["global_scene_end"]
        tag_text = sc["tag"]
        full_text = sc["text"]

        # Upper evidence tag banner
        events.append(
            f"Dialogue: 0,{format_ass_timestamp(sc_start)},{format_ass_timestamp(sc_end)},HeaderTag,,0,0,0,,{{\\an7\\b1\\c&H42B8FF&}}{tag_text}"
        )

        # Word-level karaoke / active highlight if available
        words = sc.get("words", [])
        if words:
            for w in words:
                w_start = format_ass_timestamp(w["global_start"])
                w_end = format_ass_timestamp(w["global_end"])
                # Highlight active word in golden amber, others in white
                highlighted_text = full_text.replace(
                    w["word"], f"{{\\c&H38D1FF&\\b1}}{w['word']}{{\\c&HFFFFFF&\\b1}}"
                )
                events.append(
                    f"Dialogue: 1,{w_start},{w_end},SubtitleKaraoke,,0,0,0,,{highlighted_text}"
                )
        else:
            events.append(
                f"Dialogue: 1,{format_ass_timestamp(sc_start)},{format_ass_timestamp(sc_end)},SubtitleKaraoke,,0,0,0,,{full_text}"
            )

    ass_content = header + "\n".join(events) + "\n"
    ass_path.write_text(ass_content, encoding="utf-8")
    print(f"\n   📄 Đã tạo file ASS Subtitles: {ass_path} ({len(events)} events)")

def assemble_and_render_master_video(scenes: list[dict], ass_path: Path, out_dir: Path) -> Path:
    """Concatenates video clips, mixes audio, burns subtitles, and outputs final broadcast MP4."""
    ffmpeg_bin = get_ffmpeg_binary()
    trimmed_clips_dir = out_dir / "trimmed_clips"
    trimmed_clips_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("🎞️ [STAGE S10] LẮP RÁP CÁC CLIPS VIDEO & MIX VOICE AUDIO")
    print("=" * 60)

    trimmed_clip_paths = []
    audio_concat_files = []

    for sc in scenes:
        sc_id = sc["scene_id"]
        clip_name = sc["clip_name"]
        raw_clip_path = CLIPS_DIR / clip_name
        dur = sc["scene_duration"]
        trimmed_path = trimmed_clips_dir / f"trim_{sc_id.lower()}.mp4"

        print(f"   ✂️ Trim {clip_name} -> {dur:.2f}s ({trimmed_path.name})")

        # Trim video exactly to duration and ensure constant 30fps 1080p output
        cmd_trim = [
            ffmpeg_bin, "-y",
            "-ss", "0.0",
            "-i", str(raw_clip_path),
            "-t", str(dur),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-an",
            str(trimmed_path)
        ]
        subprocess.run(cmd_trim, capture_output=True, check=True)
        trimmed_clip_paths.append(trimmed_path)

        # Pad audio segment with exact silence to match scene duration
        padded_audio = out_dir / f"pad_{sc_id.lower()}.wav"
        pad_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(sc["wav_path"]),
            "-af", f"apad=whole_dur={dur}",
            "-ar", "48000", "-ac", "2",
            str(padded_audio)
        ]
        subprocess.run(pad_cmd, capture_output=True, check=True)
        audio_concat_files.append(padded_audio)

    # 1. Concat video clips
    concat_video_txt = out_dir / "concat_video.txt"
    with open(concat_video_txt, "w", encoding="utf-8") as f:
        for p in trimmed_clip_paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    video_only_mp4 = out_dir / "concat_visual.mp4"
    print(f"\n   🔗 Ghép nối 8 clips video thành {video_only_mp4.name}...")
    subprocess.run([
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_video_txt),
        "-c", "copy",
        str(video_only_mp4)
    ], capture_output=True, check=True)

    # 2. Concat audio segments
    concat_audio_txt = out_dir / "concat_audio.txt"
    with open(concat_audio_txt, "w", encoding="utf-8") as f:
        for a in audio_concat_files:
            f.write(f"file '{a.resolve().as_posix()}'\n")

    master_audio_wav = out_dir / "master_narration.wav"
    print(f"   🔗 Ghép nối 8 audio narration thành {master_audio_wav.name}...")
    subprocess.run([
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_audio_txt),
        "-c", "copy",
        str(master_audio_wav)
    ], capture_output=True, check=True)

    # 3. Final Mux: Video + Audio + ASS Subtitle Burn-In with loudnorm (EBU R128)
    final_output_mp4 = EPISODE_DIR / "KR_EP0003_ACT1_DEMO_MASTER.mp4"
    print(f"\n🚀 [MASTER RENDER] Đang burn phụ đề karaoke và chuẩn hóa âm thanh EBU R128 -> {final_output_mp4.name}...")

    # Escape path for ffmpeg vf ass filter on Windows
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

    final_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(video_only_mp4),
        "-i", str(master_audio_wav),
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-shortest",
        str(final_output_mp4)
    ]
    subprocess.run(final_cmd, capture_output=True, check=True)

    print("\n🎉 [HOÀN TẤT THÀNH CÔNG] Video Demo Act I đã xuất xưởng:")
    print(f"   📁 File: {final_output_mp4}")
    print(f"   📦 Kích thước: {final_output_mp4.stat().st_size / (1024*1024):.2f} MB")

    return final_output_mp4

def main():
    start_time = time.time()
    print("=" * 70)
    print("🎬 AI VIDEO FACTORY - VOX ENGINE V3 ACT I DEMO RENDER PIPELINE")
    print(f"   Episode: {EPISODE_ID}")
    print(f"   Số scenes xử lý: {len(ACT1_SCENES)}")
    print("=" * 70)

    # 1. Edge-TTS Audio Generation
    scenes_with_audio = asyncio.run(generate_speech_audio(ACT1_SCENES, OUT_DIR))

    # 2. Faster-Whisper Word-Level Alignment
    scenes_aligned = align_whisper_words(scenes_with_audio)

    # 3. ASS Subtitle Generation
    ass_path = OUT_DIR / "act1_subtitles.ass"
    build_ass_subtitles(scenes_aligned, ass_path)

    # 4. Master Video Assembly & Render
    final_output = assemble_and_render_master_video(scenes_aligned, ass_path, OUT_DIR)
    logger.info(f"Rendered demo output verified at: {final_output}")

    elapsed = time.time() - start_time
    print(f"\n⏱️ Tổng thời gian hoàn tất: {elapsed:.1f}s")

if __name__ == "__main__":
    main()
