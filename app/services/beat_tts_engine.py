# app/services/beat_tts_engine.py
"""Beat-Level TTS & Word Karaoke Synchronization Engine.

Architecture:
1. Synthesizes Edge-TTS per Beat (1..5) with natural documentary cadence (male voice, rate -8%, pitch -2Hz).
2. Captures native `SentenceBoundary` events in real-time, completely bypassing slow Faster-Whisper CPU passes.
3. Distributes word/clause tokens for real-time Karaoke highlighting in Remotion.
4. Seamlessly bridges inter-scene and inter-beat gaps so:
   sum(scene_durations) == total_audio_duration (Zero-Drift Guarantee).
5. Exports:
   - tts_out.mp3 (Master audio)
   - whisper_segments.json (1:1 scene-mapped segments for Remotion & S6)
   - subtitles.srt & subtitles_<lang>.srt (For YouTube Captions API & Native AI Dubbing)
"""
from __future__ import annotations

import os
import sys
import json
import re
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("vf.beat_tts_engine")

LANG_VOICE = {
    "en": "en-US-ChristopherNeural",
    "vi": "vi-VN-NamMinhNeural",
    "zh": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
}

def format_srt_time(ms: int) -> str:
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

def tokenize_for_karaoke(text: str, start_ms: int, end_ms: int, lang_code: str) -> List[Dict[str, Any]]:
    """Break sentence into Karaoke tokens with distributed timestamps."""
    text = text.strip()
    if not text:
        return []
    total_dur = max(50, end_ms - start_ms)
    
    if lang_code in ("ja", "zh"):
        # For Japanese/Chinese: split by punctuation clauses or 4-6 char token chunks
        parts = re.split(r'([、。，,！!？?]+)', text)
        tokens = []
        for i in range(0, len(parts), 2):
            w = parts[i]
            punct = parts[i+1] if i+1 < len(parts) else ""
            comb = (w + punct).strip()
            if comb:
                # if chunk is longer than 6 chars, split into 3-4 char sub-chunks
                if len(comb) > 6:
                    for k in range(0, len(comb), 4):
                        sub = comb[k:k+4]
                        if sub:
                            tokens.append(sub)
                else:
                    tokens.append(comb)
    else:
        # For EN, VI, KO: whitespace separated words
        tokens = text.split()

    if not tokens:
        tokens = [text]

    # Distribute timestamps proportionally by token length
    total_weight = sum(max(1, len(t)) for t in tokens)
    curr_ms = start_ms
    word_entries = []
    for t in tokens:
        w_dur = max(25, int(total_dur * (max(1, len(t)) / total_weight)))
        t_end = min(end_ms, curr_ms + w_dur)
        word_entries.append({
            "word": t,
            "start_ms": curr_ms,
            "end_ms": t_end,
            "start": round(curr_ms / 1000.0, 3),
            "end": round(t_end / 1000.0, 3)
        })
        curr_ms = t_end

    if word_entries:
        word_entries[-1]["end_ms"] = end_ms
        word_entries[-1]["end"] = round(end_ms / 1000.0, 3)
    return word_entries

async def synthesize_beat_tts_pipeline(
    episode_id: str,
    out_dir: Optional[str] = None,
    inter_beat_pause_ms: int = 800,
    force: bool = False
) -> Dict[str, Any]:
    """Synthesize narration beat-by-beat with millisecond boundary tracking."""
    import edge_tts

    out_dir = out_dir or f"/var/vf/episodes/{episode_id}"
    brain_path = f"{out_dir}/brain_input.json"
    if not os.path.exists(brain_path):
        raise FileNotFoundError(f"Brain input missing: {brain_path}")

    with open(brain_path, "r", encoding="utf-8") as f:
        brain = json.load(f)

    scenes = brain.get("scenes", [])
    if not scenes:
        raise ValueError(f"No scenes found in {brain_path}")

    final_audio_path = f"{out_dir}/tts_out.mp3"
    seg_file = f"{out_dir}/whisper_segments.json"
    srt_file = f"{out_dir}/subtitles.srt"

    # Idempotency check
    if not force and os.path.exists(final_audio_path) and os.path.exists(seg_file):
        if os.path.getsize(final_audio_path) > 1000000 and os.path.getsize(seg_file) > 1000:
            logger.info("[BeatTTS] Reusing existing valid audio & segments for %s", episode_id)
            with open(seg_file, "r", encoding="utf-8") as sf:
                existing_segs = json.load(sf)
            return {
                "audio_path": final_audio_path,
                "size_bytes": os.path.getsize(final_audio_path),
                "segments": existing_segs,
                "srt_path": srt_file,
                "backend": "edge_tts_beat_cached"
            }

    # Market / voice resolution
    market = str(brain.get("market") or episode_id.split("_")[0]).lower()
    market_to_lang = {
        "jp": "ja", "ja": "ja",
        "ko": "ko", "kr": "ko",
        "vn": "vi", "vi": "vi",
        "zh": "zh", "cn": "zh",
        "en": "en"
    }
    lang_code = brain.get("lang_code") or market_to_lang.get(market, "en")
    voice = brain.get("voice") or LANG_VOICE.get(lang_code, "en-US-ChristopherNeural")
    
    # Calibrated pacing per language/market (Rule 128)
    # English uses -8% for deliberate documentary delivery (EP004 QC feedback)
    # CJK / Vietnamese uses +0% to maintain natural, authoritative cadence
    default_rate = "-8%" if lang_code == "en" else "+0%"
    default_pitch = "-2Hz" if lang_code == "en" else "-1Hz"
    
    tts_rate = brain.get("tts_rate") or os.getenv("VF_TTS_RATE") or default_rate
    tts_pitch = brain.get("tts_pitch") or os.getenv("VF_TTS_PITCH") or default_pitch

    logger.info("[BeatTTS] Starting Beat-Level TTS Pipeline for %s", episode_id)
    logger.info("  Market: %s | Lang: %s | Voice: %s | Rate: %s | Pitch: %s", market, lang_code, voice, tts_rate, tts_pitch)

    # Group scenes by beat_index
    beats: Dict[int, List[Dict[str, Any]]] = {}
    for sc in scenes:
        b_idx = int(sc.get("beat_index") or 1)
        beats.setdefault(b_idx, []).append(sc)

    all_segments: List[Dict[str, Any]] = []
    beat_mp3_paths: List[str] = []
    beats_dir = f"{out_dir}/audio_beats"
    os.makedirs(beats_dir, exist_ok=True)

    global_time_offset_ms = 0

    for b_idx in sorted(beats.keys()):
        b_scenes = beats[b_idx]
        beat_text = "\n\n".join(sc.get("narration", "").strip() for sc in b_scenes)
        beat_file = f"{beats_dir}/beat_{b_idx}.mp3"
        logger.info("  Synthesizing Beat %d (%d scenes, %d chars)...", b_idx, len(b_scenes), len(beat_text))

        comm = edge_tts.Communicate(beat_text, voice, rate=tts_rate, pitch=tts_pitch)
        boundaries = []
        beat_audio = bytearray()

        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                beat_audio.extend(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                boundaries.append({
                    "text": chunk["text"],
                    "start_ms": int(chunk["offset"] / 10000),
                    "duration_ms": int(chunk["duration"] / 10000),
                    "end_ms": int((chunk["offset"] + chunk["duration"]) / 10000)
                })

        with open(beat_file, "wb") as bf:
            bf.write(beat_audio)
        beat_mp3_paths.append(beat_file)

        # Exact ffprobe duration of this beat audio
        probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{beat_file}'"
        dur_res = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
        beat_actual_dur_sec = float(dur_res.stdout.strip() or 0.0)
        beat_actual_dur_ms = int(beat_actual_dur_sec * 1000)

        # Map scenes to boundaries
        seg_idx = 0
        beat_segments = []
        for sc in b_scenes:
            sc_text = re.sub(r'\s+', '', sc.get("narration", ""))
            matched = []
            accum = ""
            local_sc_start = boundaries[seg_idx]["start_ms"] if seg_idx < len(boundaries) else 0
            while seg_idx < len(boundaries):
                b_item = boundaries[seg_idx]
                b_clean = re.sub(r'\s+', '', b_item["text"])
                accum += b_clean
                matched.append(b_item)
                seg_idx += 1
                if len(accum) >= len(sc_text) * 0.95 or accum == sc_text:
                    break
            
            local_sc_end = matched[-1]["end_ms"] if matched else local_sc_start + 4000
            
            # Convert to global timeline
            abs_start_ms = global_time_offset_ms + local_sc_start
            abs_end_ms = global_time_offset_ms + local_sc_end
            
            # Words for karaoke
            words = []
            for m in matched:
                w_start = global_time_offset_ms + m["start_ms"]
                w_end = global_time_offset_ms + m["end_ms"]
                sub_words = tokenize_for_karaoke(m["text"], w_start, w_end, lang_code)
                words.extend(sub_words)

            segment_entry = {
                "scene_id": sc.get("scene_id"),
                "beat_index": b_idx,
                "text": sc.get("narration", ""),
                "start_ms": abs_start_ms,
                "end_ms": abs_end_ms,
                "start": round(abs_start_ms / 1000.0, 3),
                "end": round(abs_end_ms / 1000.0, 3),
                "words": words
            }
            beat_segments.append(segment_entry)

        all_segments.extend(beat_segments)
        global_time_offset_ms += beat_actual_dur_ms + inter_beat_pause_ms

    # Inter-scene and inter-beat gap bridging (Zero-Drift Guarantee)
    # Ensure every scene i seamlessly touches scene i+1: scenes[i].end_ms == scenes[i+1].start_ms
    for i in range(len(all_segments) - 1):
        curr_seg = all_segments[i]
        next_seg = all_segments[i + 1]
        curr_seg["end_ms"] = next_seg["start_ms"]
        curr_seg["end"] = round(curr_seg["end_ms"] / 1000.0, 3)
        # Clamp last word end_ms if needed
        if curr_seg.get("words"):
            curr_seg["words"][-1]["end_ms"] = min(curr_seg["end_ms"], max(curr_seg["words"][-1]["end_ms"], curr_seg["words"][-1]["start_ms"] + 100))
            curr_seg["words"][-1]["end"] = round(curr_seg["words"][-1]["end_ms"] / 1000.0, 3)

    # Concatenate audio beats with ffmpeg including inter-beat silence
    concat_list_path = f"{beats_dir}/concat.txt"
    silence_path = f"{beats_dir}/silence_pause.mp3"
    subprocess.run(
        f"ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {inter_beat_pause_ms/1000.0} -q:a 9 -acodec libmp3lame '{silence_path}'",
        shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    with open(concat_list_path, "w", encoding="utf-8") as cf:
        for idx, bp in enumerate(beat_mp3_paths):
            cf.write(f"file '{bp}'\n")
            if idx < len(beat_mp3_paths) - 1:
                cf.write(f"file '{silence_path}'\n")

    subprocess.run(
        f"ffmpeg -y -f concat -safe 0 -i '{concat_list_path}' -c copy '{final_audio_path}'",
        shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Final probe for master audio duration
    final_dur_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{final_audio_path}'"
    final_dur_res = subprocess.run(final_dur_cmd, shell=True, capture_output=True, text=True)
    final_actual_dur_sec = float(final_dur_res.stdout.strip() or 0.0)
    final_actual_dur_ms = int(final_actual_dur_sec * 1000)

    # Align the very last segment to the master audio end
    if all_segments:
        all_segments[-1]["end_ms"] = final_actual_dur_ms
        all_segments[-1]["end"] = round(final_actual_dur_ms / 1000.0, 3)
        if all_segments[-1].get("words"):
            all_segments[-1]["words"][-1]["end_ms"] = final_actual_dur_ms
            all_segments[-1]["words"][-1]["end"] = round(final_actual_dur_ms / 1000.0, 3)

    # Write whisper_segments.json
    with open(seg_file, "w", encoding="utf-8") as sf:
        json.dump(all_segments, sf, ensure_ascii=False, indent=2)

    # Build SRT content
    srt_entries = []
    for i, seg in enumerate(all_segments, 1):
        s_ms = seg["start_ms"]
        e_ms = seg["end_ms"]
        srt_entries.append(
            f"{i}\n"
            f"{format_srt_time(s_ms)} --> {format_srt_time(e_ms)}\n"
            f"{seg.get('text', '').strip()}\n"
        )
    srt_content = "\n".join(srt_entries)

    # Write subtitles.srt and subtitles_<lang>.srt
    srt_lang_file = f"{out_dir}/subtitles_{lang_code}.srt"
    with open(srt_file, "w", encoding="utf-8") as srf:
        srf.write(srt_content)
    with open(srt_lang_file, "w", encoding="utf-8") as srf2:
        srf2.write(srt_content)

    final_size = os.path.getsize(final_audio_path)
    logger.info("[BeatTTS] Complete: %s (%d bytes, %.2fs, %d scenes mapped)", final_audio_path, final_size, final_actual_dur_sec, len(all_segments))

    return {
        "audio_path": final_audio_path,
        "size_bytes": final_size,
        "segments": all_segments,
        "srt_path": srt_file,
        "srt_lang_path": srt_lang_file,
        "total_duration_sec": final_actual_dur_sec,
        "backend": "edge_tts_beat"
    }
