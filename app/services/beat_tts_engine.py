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
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("vf.beat_tts_engine")

# Resilient Multi-Tier Voice Rotation Roster per Market (Rule 120/128)
VOICE_ROTATION_ROSTER: Dict[str, List[str]] = {
    "en": ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-EricNeural", "en-US-BrianNeural"],
    "zh": ["zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-YunyangNeural"],
    "ja": ["ja-JP-KeitaNeural", "ja-JP-DaichiNeural", "ja-JP-NanamiNeural"],
    "ko": ["ko-KR-InJoonNeural", "ko-KR-BongJinNeural", "ko-KR-SunHiNeural"]
}

LANG_VOICE = {k: v[0] for k, v in VOICE_ROTATION_ROSTER.items()}


async def _synthesize_single_beat_resilient(
    beat_text: str,
    voices: List[str],
    rate: str,
    pitch: str,
    beat_file: Path,
    boundary_file: Path,
    force: bool = False,
    max_attempts: int = 4
) -> Tuple[bytearray, List[Dict[str, Any]], str]:
    """
    Synthesizes a single beat using Edge-TTS with 3-layer resilience (Option A):
    1. Layer 1: Exponential backoff with jitter on network/websocket/rate-limit failures.
    2. Layer 2: Voice rotation across candidate voices for the target market.
    3. Layer 3: Beat-level disk caching to resume instantly on partial failures (idempotent).
    """
    import edge_tts
    import random

    # Layer 3: Check disk cache for valid pre-existing beat audio & boundaries
    if not force and beat_file.exists() and beat_file.stat().st_size > 5120 and boundary_file.exists():
        try:
            boundaries = json.loads(boundary_file.read_text(encoding="utf-8"))
            beat_audio = beat_file.read_bytes()
            if len(beat_audio) > 5120 and boundaries:
                logger.info(
                    "    [BeatTTS Cache Hit] Reusing valid cached beat audio (%dB, %d boundaries): %s",
                    len(beat_audio), len(boundaries), beat_file.name
                )
                return beat_audio, boundaries, "cached"
        except Exception as cache_err:
            logger.warning("    [BeatTTS Cache Miss] Corrupt cache on %s: %s. Re-synthesizing...", beat_file.name, cache_err)

    last_exc = None
    for attempt in range(max_attempts):
        curr_voice = voices[attempt % len(voices)]
        if attempt > 0:
            backoff_sec = min(16.0, (1.5 ** attempt) + random.uniform(0.3, 0.9))
            logger.warning(
                "    [BeatTTS Resilient Retry %d/%d] Voice: %s (Backoff: %.2fs)...",
                attempt + 1, max_attempts, curr_voice, backoff_sec
            )
            await asyncio.sleep(backoff_sec)

        boundaries = []
        beat_audio = bytearray()
        try:
            comm = edge_tts.Communicate(beat_text, curr_voice, rate=rate, pitch=pitch)

            async def _stream_beat():
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

            await asyncio.wait_for(_stream_beat(), timeout=60.0)

            if len(beat_audio) > 1024:
                # Save beat audio and boundaries to disk immediately for caching
                beat_file.parent.mkdir(parents=True, exist_ok=True)
                beat_file.write_bytes(beat_audio)

                # Fallback if boundaries array is empty (e.g. non-standard punctuation)
                if not boundaries and len(beat_audio) > 1024:
                    logger.warning("    [BeatTTS] No SentenceBoundary emitted for %s, probing duration...", beat_file.name)
                    probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{beat_file}'"
                    dur_res = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
                    total_ms = int(float(dur_res.stdout.strip() or 1.0) * 1000)
                    boundaries.append({
                        "text": beat_text,
                        "start_ms": 0,
                        "duration_ms": total_ms,
                        "end_ms": total_ms
                    })

                boundary_file.write_text(json.dumps(boundaries, ensure_ascii=False, indent=2), encoding="utf-8")
                return beat_audio, boundaries, curr_voice
            else:
                raise ValueError(f"Synthesized audio payload too small ({len(beat_audio)} bytes)")

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "    [BeatTTS] Attempt %d/%d failed with voice %s: %s - %s",
                attempt + 1, max_attempts, curr_voice, type(exc).__name__, exc
            )

    raise RuntimeError(
        f"HARD GATE VIOLATION (Rule 120/127): Beat TTS failed after {max_attempts} resilient attempts "
        f"across candidate voices: {voices}. Last exception: {last_exc}"
    )


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

    # Hollywood Audio-Anchored Pipeline: prioritize spoken_sentences from B2 over scenes
    spoken_sentences = brain.get("spoken_sentences", [])
    scenes = brain.get("scenes", [])
    
    if not spoken_sentences and not scenes:
        # Check disk fallback for spoken_sentences.json
        disk_sp = f"{out_dir}/spoken_sentences.json"
        if os.path.exists(disk_sp):
            try:
                with open(disk_sp, "r", encoding="utf-8") as sf:
                    spoken_sentences = json.load(sf)
            except Exception:
                pass

    use_spoken_sentences = bool(spoken_sentences)
    units_to_synthesize = spoken_sentences if use_spoken_sentences else scenes
    if not units_to_synthesize:
        raise ValueError(f"No spoken_sentences or scenes found in {brain_path}")

    final_audio_path = f"{out_dir}/tts_out.mp3"
    seg_file = f"{out_dir}/whisper_segments.json"
    spoken_out_file = f"{out_dir}/spoken_sentences.json"
    srt_file = f"{out_dir}/subtitles.srt"

    # Idempotency check
    if not force and os.path.exists(final_audio_path) and os.path.exists(seg_file):
        if os.path.getsize(final_audio_path) > 100000 and os.path.getsize(seg_file) > 1000:
            logger.info("[BeatTTS] Reusing existing valid audio & segments for %s", episode_id)
            with open(seg_file, "r", encoding="utf-8") as sf:
                existing_segs = json.load(sf)
            cached_dur = 0.0
            if existing_segs:
                cached_dur = float(existing_segs[-1].get("end", 0.0))
            if cached_dur <= 0 and os.path.exists(final_audio_path):
                try:
                    probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{final_audio_path}'"
                    dur_res = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
                    cached_dur = float(dur_res.stdout.strip() or 0.0)
                except Exception:
                    pass
            return {
                "audio_path": final_audio_path,
                "size_bytes": os.path.getsize(final_audio_path),
                "segments": existing_segs,
                "srt_path": srt_file,
                "total_duration_sec": cached_dur,
                "backend": "edge_tts_beat_cached"
            }

    # Market / voice resolution
    market = str(brain.get("market") or episode_id.split("_")[0]).lower()
    market_to_lang = {
        "jp": "ja", "ja": "ja",
        "ko": "ko", "kr": "ko",
        "zh": "zh", "cn": "zh",
        "en": "en"
    }
    lang_code = brain.get("lang_code") or market_to_lang.get(market, "en")
    voice = brain.get("voice") or LANG_VOICE.get(lang_code, "en-US-ChristopherNeural")
    roster_candidates = VOICE_ROTATION_ROSTER.get(lang_code, ["en-US-ChristopherNeural"])
    candidate_voices = [voice] + [v for v in roster_candidates if v != voice]
    
    # Calibrated pacing per language/market (Rule 128)
    # English uses -8% for deliberate documentary delivery (EP004 QC feedback)
    # CJK / Vietnamese uses +0% to maintain natural, authoritative cadence
    default_rate = "-8%" if lang_code == "en" else "+0%"
    default_pitch = "-2Hz" if lang_code == "en" else "-1Hz"
    
    tts_rate = brain.get("tts_rate") or os.getenv("VF_TTS_RATE") or default_rate
    tts_pitch = brain.get("tts_pitch") or os.getenv("VF_TTS_PITCH") or default_pitch

    logger.info("[BeatTTS] Starting Beat-Level TTS Pipeline for %s (%s)", episode_id, "spoken_sentences" if use_spoken_sentences else "scenes")
    logger.info("  Market: %s | Lang: %s | Primary Voice: %s | Rotation: %s | Rate: %s | Pitch: %s", market, lang_code, voice, candidate_voices, tts_rate, tts_pitch)

    # Group units by beat_index
    beats: Dict[int, List[Dict[str, Any]]] = {}
    for u in units_to_synthesize:
        b_idx = int(u.get("beat_index") or 1)
        beats.setdefault(b_idx, []).append(u)

    all_segments: List[Dict[str, Any]] = []
    beat_mp3_paths: List[str] = []
    beats_dir = Path(f"{out_dir}/audio_beats")
    beats_dir.mkdir(parents=True, exist_ok=True)

    global_time_offset_ms = 0

    for b_idx in sorted(beats.keys()):
        b_units = beats[b_idx]
        beat_texts = []
        for u in b_units:
            t = (u.get("text") or u.get("narration") or "").strip()
            if t:
                beat_texts.append(t)
        beat_text = "\n\n".join(beat_texts)
        beat_file = beats_dir / f"beat_{b_idx}.mp3"
        boundary_file = beats_dir / f"beat_{b_idx}_boundaries.json"
        logger.info("  Synthesizing Beat %d (%d units, %d chars)...", b_idx, len(b_units), len(beat_text))

        beat_audio, boundaries, used_voice = await _synthesize_single_beat_resilient(
            beat_text=beat_text,
            voices=candidate_voices,
            rate=tts_rate,
            pitch=tts_pitch,
            beat_file=beat_file,
            boundary_file=boundary_file,
            force=force,
            max_attempts=4
        )
        beat_mp3_paths.append(str(beat_file))

        # Exact ffprobe duration of this beat audio
        probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{beat_file}'"
        dur_res = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
        beat_actual_dur_sec = float(dur_res.stdout.strip() or 0.0)
        beat_actual_dur_ms = int(beat_actual_dur_sec * 1000)

        # Map units to boundaries
        seg_idx = 0
        beat_segments = []
        is_exact_1to1 = (len(b_units) == len(boundaries))
        for u_idx, u in enumerate(b_units):
            raw_u_text = u.get("text") or u.get("narration") or ""
            u_clean_text = re.sub(r'\s+', '', raw_u_text)
            matched = []
            if is_exact_1to1:
                matched = [boundaries[u_idx]]
                local_u_start = matched[0]["start_ms"]
            else:
                accum = ""
                local_u_start = boundaries[seg_idx]["start_ms"] if seg_idx < len(boundaries) else 0
                while seg_idx < len(boundaries):
                    b_item = boundaries[seg_idx]
                    b_clean = re.sub(r'\s+', '', b_item["text"])
                    accum += b_clean
                    matched.append(b_item)
                    seg_idx += 1
                    u_punc = re.sub(r'[\W_]+', '', u_clean_text)
                    accum_punc = re.sub(r'[\W_]+', '', accum)
                    if len(accum_punc) >= len(u_punc) * 0.90 or accum == u_clean_text or len(accum) >= len(u_clean_text) - 1:
                        break
            
            local_u_end = matched[-1]["end_ms"] if matched else local_u_start + 4000
            
            # Convert to global timeline
            abs_start_ms = global_time_offset_ms + local_u_start
            abs_end_ms = global_time_offset_ms + local_u_end
            dur_frames = max(1, int(round((abs_end_ms - abs_start_ms) / 1000.0 * 30)))
            
            # Words for karaoke
            words = []
            for m in matched:
                w_start = global_time_offset_ms + m["start_ms"]
                w_end = global_time_offset_ms + m["end_ms"]
                sub_words = tokenize_for_karaoke(m["text"], w_start, w_end, lang_code)
                words.extend(sub_words)

            segment_entry = {
                "sentence_id": u.get("sentence_id") or u.get("scene_id") or f"sent_{len(all_segments) + len(beat_segments) + 1:03d}",
                "scene_id": u.get("scene_id") or u.get("sentence_id"),
                "beat_index": b_idx,
                "text": raw_u_text,
                "start_ms": abs_start_ms,
                "end_ms": abs_end_ms,
                "start": round(abs_start_ms / 1000.0, 3),
                "end": round(abs_end_ms / 1000.0, 3),
                "duration_frames": dur_frames,
                "words": words,
                "karaoke_highlights": u.get("karaoke_highlights", [])
            }
            beat_segments.append(segment_entry)

        all_segments.extend(beat_segments)
        global_time_offset_ms += beat_actual_dur_ms + inter_beat_pause_ms

    # Inter-scene and inter-beat gap bridging (Zero-Drift Guarantee)
    # Ensure every scene i seamlessly touches scene i+1: scenes[i].end_ms == scenes[i+1].start_ms
    prev_cum_frames = 0
    for i in range(len(all_segments) - 1):
        curr_seg = all_segments[i]
        next_seg = all_segments[i + 1]
        curr_seg["end_ms"] = next_seg["start_ms"]
        curr_seg["end"] = round(curr_seg["end_ms"] / 1000.0, 3)
        cum_target = int(round(curr_seg["end_ms"] / 1000.0 * 30))
        curr_seg["duration_frames"] = max(1, cum_target - prev_cum_frames)
        prev_cum_frames += curr_seg["duration_frames"]
        curr_seg["duration_sec"] = round(curr_seg["duration_frames"] / 30.0, 3)
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
        cum_target = int(round(final_actual_dur_ms / 1000.0 * 30))
        all_segments[-1]["duration_frames"] = max(1, cum_target - prev_cum_frames)
        all_segments[-1]["duration_sec"] = round(all_segments[-1]["duration_frames"] / 30.0, 3)
        if all_segments[-1].get("words"):
            all_segments[-1]["words"][-1]["end_ms"] = final_actual_dur_ms
            all_segments[-1]["words"][-1]["end"] = round(final_actual_dur_ms / 1000.0, 3)

    # Write whisper_segments.json and spoken_sentences.json (Hollywood Audio Spine)
    with open(seg_file, "w", encoding="utf-8") as sf:
        json.dump(all_segments, sf, ensure_ascii=False, indent=2)
    with open(spoken_out_file, "w", encoding="utf-8") as sof:
        json.dump(all_segments, sof, ensure_ascii=False, indent=2)

    # Sync back to brain_input.json so downstream stages (B3.5 Director & Remotion) have exact timecodes
    try:
        brain["spoken_sentences"] = all_segments
        brain["audio_duration_sec"] = final_actual_dur_sec
        brain["audio_duration_frames"] = int(round(final_actual_dur_sec * 30))
        with open(brain_path, "w", encoding="utf-8") as bf:
            json.dump(brain, bf, ensure_ascii=False, indent=2)
    except Exception as _b_err:
        logger.warning(f"[BeatTTS] Could not update brain_input.json: {_b_err}")

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
