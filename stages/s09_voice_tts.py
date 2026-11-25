#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s09_voice_tts.py — Stage S9: Voiceover TTS & Word-Level Karaoke (AVF-STAB-001).

Implements Stage Shape Standard. Generates Edge-TTS speech with real WordBoundary
events, normalizes loudness to EBU R128 broadcast standards, and measures acoustic
word-level timestamps via faster-whisper (Rule 118 & Rule 120).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import difflib
import json
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from core.config import RunContext
from core.contracts.render_props import KaraokeWord
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import emit_artifact
from tools.codemap.runtime import pipeline_stage

STAGE: StageID = StageID.S9_VOICE_TTS


def _to_ass_time(sec: float) -> str:
    """Formats seconds into ASS subtitle timecode H:MM:SS.cc."""
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _resolve_lang(market: str) -> str:
    """Maps canonical market identifier to ISO 639-1 language code."""
    m = market.strip().upper()
    return {"JA": "ja", "JP": "ja", "KO": "ko", "KR": "ko", "VI": "vi", "VN": "vi"}.get(m, "en")


async def _synthesize_edge_tts_stream(
    text: str,
    voice: str,
    rate: str,
    audio_file: Path,
) -> List[Dict[str, Any]]:
    """Synthesizes Edge-TTS MP3 while recording real WordBoundary events."""
    import edge_tts

    audio_file.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    boundaries: List[Dict[str, Any]] = []
    with open(audio_file, "wb") as out_f:
        async for chunk in communicate.stream():
            ctype = chunk.get("type")
            if ctype == "audio":
                data = chunk.get("data")
                if data:
                    out_f.write(data)
            elif ctype == "WordBoundary":
                start_s = float(chunk.get("offset", 0)) / 10_000_000.0
                dur_s = float(chunk.get("duration", 0)) / 10_000_000.0
                tok = str(chunk.get("text") or "").strip()
                if tok:
                    boundaries.append({
                        "word": tok,
                        "start": round(start_s, 3),
                        "end": round(max(start_s + 0.02, start_s + dur_s), 3),
                    })
    return boundaries


def _run_local_faster_whisper(
    audio_file: Path,
    model_name: str,
    lang: str,
    initial_prompt: str,
) -> List[Dict[str, Any]]:
    """Executes faster-whisper locally if installed in the active Python environment."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    raw_segments, _ = model.transcribe(
        str(audio_file),
        language=lang,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
        initial_prompt=initial_prompt[:400] if initial_prompt else None,
    )
    out: List[Dict[str, Any]] = []
    for seg in raw_segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        words = []
        for w in (seg.words or []):
            tok = (w.word or "").strip()
            if tok and w.end >= w.start:
                words.append({
                    "word": tok,
                    "start": round(float(w.start), 3),
                    "end": round(max(float(w.start) + 0.01, float(w.end)), 3),
                })
        out.append({
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": text,
            "words": words,
        })
    return out


def _measure_words_with_faster_whisper(
    audio_file: Path,
    run_id: str,
    market: str,
    initial_prompt: str,
) -> Optional[List[Dict[str, Any]]]:
    """Extracts acoustic word-level segments via faster-whisper locally or on Hetzner VPS."""
    lang = _resolve_lang(market)
    model_name = "small" if lang != "en" else "small"

    try:
        return _run_local_faster_whisper(audio_file, model_name, lang, initial_prompt)
    except ImportError:
        logger.info("[s09_voice_tts] faster-whisper not local; dispatching ASR measurement to VPS...")
    except Exception as local_err:
        logger.warning("[s09_voice_tts] Local faster-whisper notice (%s); trying VPS...", local_err)

    remote_audio = f"/tmp/s09_asr_{run_id}.mp3"
    remote_json = f"/tmp/s09_asr_{run_id}.json"
    local_json = audio_file.with_name(".asr_vps_result.json")
    try:
        from scripts.download_vps_asset import download_file_chunked
        from scripts.upload_vps_asset import upload_file
        from scripts.vps_runner import run_vps_cmd

        if not upload_file(str(audio_file), remote_audio):
            logger.warning("[s09_voice_tts] Failed uploading audio to VPS for Whisper alignment")
            return None

        py_code = (
            "import json; "
            "from faster_whisper import WhisperModel; "
            f"m=WhisperModel('{model_name}', device='cpu', compute_type='int8'); "
            f"segs,_=m.transcribe('{remote_audio}', language='{lang}', word_timestamps=True, vad_filter=True, beam_size=5); "
            "out=[{'start':round(s.start,3),'end':round(s.end,3),'text':s.text.strip(),"
            "'words':[{'word':w.word.strip(),'start':round(w.start,3),'end':round(max(w.start+0.01,w.end),3)} "
            "for w in (s.words or []) if w.word.strip()]} for s in segs if s.text.strip()]; "
            f"open('{remote_json}','w',encoding='utf-8').write(json.dumps(out,ensure_ascii=False))"
        )
        vps_python = "/root/video_factory/venv/bin/python3"
        cmd = f"{vps_python} -c {json.dumps(py_code)}"
        res = run_vps_cmd(cmd, timeout=240)
        if res.get("exit_code", 1) != 0:
            logger.warning("[s09_voice_tts] VPS faster-whisper error: %s", res.get("stderr") or res)
            return None

        if not download_file_chunked(remote_json, str(local_json)):
            logger.warning("[s09_voice_tts] Failed downloading VPS Whisper JSON")
            return None

        data = json.loads(local_json.read_text(encoding="utf-8"))
        return data if isinstance(data, list) and data else None
    except Exception as vps_err:
        logger.warning("[s09_voice_tts] VPS faster-whisper alignment notice: %s", vps_err)
        return None
    finally:
        try:
            from scripts.vps_runner import run_vps_cmd
            run_vps_cmd(f"rm -f '{remote_audio}' '{remote_json}'", timeout=15)
        except Exception as cleanup_err:
            logger.debug("[s09_voice_tts] VPS tmp cleanup notice: %s", cleanup_err)
        if local_json.exists():
            local_json.unlink(missing_ok=True)


def _norm_tok(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def _group_word_boundaries_into_segments(
    boundaries: List[Dict[str, Any]],
    total_dur: float,
) -> List[Dict[str, Any]]:
    """Groups standalone WordBoundary tokens into pause/length-bounded segments."""
    if not boundaries:
        return []
    segments: List[Dict[str, Any]] = []
    cur: List[Dict[str, Any]] = []
    for idx, tok in enumerate(boundaries):
        if cur:
            gap = tok["start"] - cur[-1]["end"]
            if gap > 0.35 or len(cur) >= 12:
                segments.append({
                    "start": cur[0]["start"],
                    "end": cur[-1]["end"],
                    "text": " ".join(w["word"] for w in cur),
                    "words": list(cur),
                })
                cur = []
        w_copy = dict(tok)
        if idx == len(boundaries) - 1 and total_dur > w_copy["end"]:
            w_copy["end"] = round(min(total_dur, max(w_copy["end"], total_dur)), 3)
        cur.append(w_copy)
    if cur:
        segments.append({
            "start": cur[0]["start"],
            "end": round(max(cur[-1]["end"], total_dur), 3),
            "text": " ".join(w["word"] for w in cur),
            "words": list(cur),
        })
    return segments


def _reconcile_script_casing_onto_whisper(
    whisper_segments: List[Dict[str, Any]],
    script_text: str,
) -> List[Dict[str, Any]]:
    """Preserves exact script spelling/punctuation on 1:1 matched tokens without changing acoustic timestamps."""
    script_tokens = [t for t in script_text.split() if t.strip()]
    flat_whisper: List[Dict[str, Any]] = []
    for seg in whisper_segments:
        for w in seg.get("words") or []:
            flat_whisper.append(w)
    if not script_tokens or not flat_whisper:
        return whisper_segments

    w_norm = [_norm_tok(w["word"]) for w in flat_whisper]
    s_norm = [_norm_tok(t) for t in script_tokens]
    matcher = difflib.SequenceMatcher(None, w_norm, s_norm, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("equal", "replace") and (i2 - i1) == (j2 - j1):
            for offset in range(i2 - i1):
                # Keep Whisper timing untouched; update only display spelling when 1:1 aligned
                flat_whisper[i1 + offset]["word"] = script_tokens[j1 + offset]

    rebuilt: List[Dict[str, Any]] = []
    for seg in whisper_segments:
        words = seg.get("words") or []
        if not words:
            continue
        rebuilt.append({
            "start": round(float(words[0]["start"]), 3),
            "end": round(float(words[-1]["end"]), 3),
            "text": " ".join(w["word"] for w in words).strip(),
            "words": words,
        })
    return rebuilt


@pipeline_stage(
    id="s09_voice_tts",
    order=9,
    name="Edge-TTS Hollywood Voiceover & Karaoke",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s03_script"],
    upstream=["s03_script"],
    downstream=["s05_director_plan", "s10_render"],
    artifacts=[
        "runs/{run_id}/audio/voice_narration.mp3",
        "runs/{run_id}/audio/word_timestamps.json",
        "runs/{run_id}/audio/transcript_segments.json",
    ],
    verify_cmds=["python -m orchestrator.run_pipeline --only s09_voice_tts --profile e2e_min"],
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S9: Voice Narration TTS, EBU R128 Loudnorm & ASR Word Timestamps."""
    start_ts = time.time()

    s3_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    s3_data = json.loads(s3_path.read_text(encoding="utf-8"))
    scenes = s3_data.get("payload", {}).get("scenes", [])

    audio_file = ctx.paths.audio_dir / "voice_narration.mp3"
    subtitles_file = ctx.paths.audio_dir / "word_timestamps.json"
    segments_file = ctx.paths.audio_dir / "transcript_segments.json"
    audio_file.parent.mkdir(parents=True, exist_ok=True)

    full_text = " ".join(str(s.get("narration", "")).strip() for s in scenes if isinstance(s, dict)).strip()
    words = full_text.split()
    is_min_profile = bool((ctx.config.name == "e2e_min" and ctx.config.limits.max_scenes == 1) or ctx.dry_run)

    market = "EN"
    s1_path = ctx.paths.artifact_file(StageID.S1_IDEATION.value)
    if s1_path.exists():
        try:
            s1_data = json.loads(s1_path.read_text(encoding="utf-8"))
            market = s1_data.get("payload", {}).get("market", "EN")
        except (OSError, json.JSONDecodeError) as _m_err:
            logger.debug("[s09_voice_tts] S1 read notice, using default EN: %s", _m_err)

    edge_boundaries: List[Dict[str, Any]] = []
    synthesized_fresh = False

    if not audio_file.exists() or ctx.force:
        legacy_audio = ctx.paths.root / "narration.mp3"
        if legacy_audio.exists() and legacy_audio.stat().st_size > 1000 and not ctx.force:
            shutil.copy2(str(legacy_audio), str(audio_file))
        else:
            if ctx.preset and getattr(ctx.preset, "tts", None) and getattr(ctx.preset.tts, "voice", None):
                voice = ctx.preset.tts.voice
            else:
                voice = ctx.config.voice.voice_en
                m_low = market.lower()
                if m_low in ("ja", "jp"):
                    voice = ctx.config.voice.voice_jp
                elif m_low in ("ko", "kr"):
                    voice = ctx.config.voice.voice_kr
                elif m_low in ("vi", "vn"):
                    voice = ctx.config.voice.voice_vn

            text_to_speak = full_text if full_text else "AI Video Factory master video narration."
            rate_opt = "+0%"
            if ctx.preset and getattr(ctx.preset, "tts", None) and getattr(ctx.preset.tts, "rate", None):
                rate_opt = ctx.preset.tts.rate

            tts_success = False
            try:
                def _run_tts():
                    return asyncio.run(_synthesize_edge_tts_stream(text_to_speak, voice, rate_opt, audio_file))

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    edge_boundaries = pool.submit(_run_tts).result(timeout=180)
                if audio_file.exists() and audio_file.stat().st_size > 1000:
                    tts_success = True
                    synthesized_fresh = True
            except Exception as _tts_err:
                logger.warning("[s09_voice_tts] Edge-TTS synthesis error: %s", _tts_err)
                if not is_min_profile:
                    raise RuntimeError(f"[s09_voice_tts] Edge-TTS failed in live prod mode: {_tts_err}") from _tts_err

            if not tts_success:
                from vox.ffmpeg_utils import get_ffmpeg_binary
                ffmpeg_bin = get_ffmpeg_binary()
                est_dur = max(len(words) * 0.35, 5.0)
                try:
                    subprocess.run(
                        [ffmpeg_bin, "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={est_dur}",
                         "-c:a", "libmp3lame", "-b:a", "128k", str(audio_file)],
                        capture_output=True, check=True,
                    )
                except subprocess.CalledProcessError as _ff_err:
                    logger.warning("[s09_voice_tts] FFmpeg fixture audio notice: %s", _ff_err)
                    audio_file.write_bytes(b"\xff\xfb\x90\x44" + b"\x00" * 8192)

    from vox.ffmpeg_utils import get_ffmpeg_binary, normalize_audio_ebur128
    from vox.qa.gates import probe_media_file

    real_audio_dur = 0.0
    if audio_file.exists() and audio_file.stat().st_size > 100:
        try:
            a_info = probe_media_file(audio_file)
            real_audio_dur = float(a_info.get("format", {}).get("duration", "0"))
        except Exception as _p_err:
            logger.debug("[s09_voice_tts] initial audio probe notice: %s", _p_err)

    # Dynamic duration conformer for preset window compliance BEFORE ASR timing
    conformed_factor = 1.0
    if not is_min_profile and ctx.preset and getattr(ctx.preset, "duration_window_s", None) and real_audio_dur > 0:
        d_min = ctx.preset.duration_window_s.min
        d_max = ctx.preset.duration_window_s.max
        speed_factor = None
        if real_audio_dur > d_max and (real_audio_dur / d_max) <= 1.35:
            target_dur = max(d_min + 5.0, min(d_max - 2.0, getattr(ctx.preset.duration_window_s, "target", (d_min + d_max) / 2.0)))
            speed_factor = round(real_audio_dur / target_dur, 3)
        elif real_audio_dur < d_min and (real_audio_dur / d_min) >= 0.65:
            target_dur = min(d_max - 5.0, max(d_min + 3.0, getattr(ctx.preset.duration_window_s, "target", (d_min + d_max) / 2.0)))
            speed_factor = round(real_audio_dur / target_dur, 3)

        if speed_factor and 0.5 <= speed_factor <= 2.0:
            ffmpeg_bin = get_ffmpeg_binary()
            conformed_audio = audio_file.with_name("voice_narration_conformed.mp3")
            subprocess.run(
                [ffmpeg_bin, "-y", "-i", str(audio_file), "-filter:a", f"atempo={speed_factor}", str(conformed_audio)],
                capture_output=True, check=True,
            )
            if conformed_audio.exists() and conformed_audio.stat().st_size > 100:
                conformed_audio.replace(audio_file)
                conformed_factor = speed_factor
                a_info = probe_media_file(audio_file)
                real_audio_dur = float(a_info.get("format", {}).get("duration", "0"))
                logger.info(f"[s09_voice_tts] Conformed audio duration to {real_audio_dur:.2f}s (speed {speed_factor})")

    # Two-pass EBU R128 broadcast loudness normalization in live prod BEFORE measuring final ASR alignment
    if not is_min_profile and audio_file.exists() and audio_file.stat().st_size > 1000:
        normalize_audio_ebur128(audio_file, target_i=-16.0, target_tp=-2.5, target_lra=7.0)
        a_info = probe_media_file(audio_file)
        real_audio_dur = float(a_info.get("format", {}).get("duration", "0"))
        logger.info("[s09_voice_tts] Normalized voice audio to EBU R128 (-16.0 LUFS, -2.5 dBTP)")

    actual_total_dur = real_audio_dur if real_audio_dur > 0.0 else max(len(words) * 0.35, 5.0)
    if edge_boundaries and conformed_factor != 1.0:
        for b in edge_boundaries:
            b["start"] = round(b["start"] / conformed_factor, 3)
            b["end"] = round(b["end"] / conformed_factor, 3)

    # Measure acoustic word timestamps via faster-whisper + Edge-TTS WordBoundary
    segments: List[Dict[str, Any]] = []
    timing_source = "test-fixture-proportional"

    if not is_min_profile:
        whisper_segments = _measure_words_with_faster_whisper(
            audio_file=audio_file,
            run_id=ctx.run_id,
            market=market,
            initial_prompt=full_text,
        )
        if whisper_segments:
            segments = _reconcile_script_casing_onto_whisper(whisper_segments, full_text)
            timing_source = "faster-whisper+edge-boundary" if (synthesized_fresh and edge_boundaries) else "faster-whisper-measured"
        elif edge_boundaries:
            segments = _group_word_boundaries_into_segments(edge_boundaries, actual_total_dur)
            timing_source = "edge-tts-word-boundary"
        else:
            raise RuntimeError(
                "[s09_voice_tts] Fail-closed (Rule 118/120): Neither faster-whisper ASR nor Edge-TTS "
                "WordBoundary returned measured timestamps; refusing proportional word fabrication in prod mode."
            )
    else:
        # Hermetic e2e_min / dry_run fixture fallback only
        curr_t = 0.0
        step = actual_total_dur / max(1, len(words))
        seg_words = []
        for w in words:
            w_item = {"word": w, "start": round(curr_t, 3), "end": round(curr_t + step, 3)}
            seg_words.append(w_item)
            curr_t += step
        if seg_words:
            segments = [{"start": 0.0, "end": round(actual_total_dur, 3), "text": full_text, "words": seg_words}]

    # Flatten KaraokeWord list + generate ASS file strictly from measured segments
    subtitles: List[Dict[str, Any]] = []
    ass_events: List[str] = []
    for seg in segments:
        seg_text = str(seg.get("text") or "").strip()
        if seg_text:
            ass_events.append(
                f"Dialogue: 0,{_to_ass_time(seg['start'])},{_to_ass_time(seg['end'])},Default,,0,0,0,,{seg_text}"
            )
        for w in seg.get("words") or []:
            w_s = float(w["start"])
            w_e = float(w["end"])
            subtitles.append(KaraokeWord(
                word=str(w["word"]),
                start=round(w_s, 3),
                end=round(w_e, 3),
                start_ms=round(w_s * 1000.0, 1),
                end_ms=round(w_e * 1000.0, 1),
            ).model_dump())

    if not ass_events:
        ass_events.append("Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,AI Video Factory")

    subtitles_file.write_text(json.dumps(subtitles, indent=2, ensure_ascii=False), encoding="utf-8")
    segments_file.write_text(
        json.dumps(
            {"timing_source": timing_source, "duration": round(actual_total_dur, 3), "segments": segments},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    ass_file = ctx.paths.audio_dir / "subtitles.ass"
    ass_lines = [
        "[Script Info]",
        "Title: Vox Tactile Subtitles",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,64,&H00FFFFFF,&H0000FFFF,&H00141414,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,90,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    ass_lines.extend(ass_events)
    ass_file.write_text("\n".join(ass_lines), encoding="utf-8")

    measured_duration_s = round(actual_total_dur, 3)
    if not is_min_profile and ctx.preset and getattr(ctx.preset, "duration_window_s", None):
        d_min = ctx.preset.duration_window_s.min
        d_max = ctx.preset.duration_window_s.max
        if not (d_min <= measured_duration_s <= d_max):
            raise ValueError(
                f"[s09_voice_tts] Measured audio duration {measured_duration_s}s is outside preset window [{d_min}s, {d_max}s]."
            )

    if ctx.preset and getattr(ctx.preset, "narration", None) and measured_duration_s > 0:
        total_w = len(subtitles) or len(words)
        calculated_wpm = round((total_w / (measured_duration_s / 60.0)), 1)
        try:
            ctx.preset.narration.wpm_estimate = calculated_wpm
        except (AttributeError, TypeError) as _wpm_err:
            logger.debug(f"[s09_voice_tts] Could not update preset wpm_estimate: {_wpm_err}")

    payload = {
        "task_id": ctx.run_id,
        "audio_file": str(audio_file),
        "timing_source": timing_source,
        "total_words": len(subtitles),
        "total_duration_sec": measured_duration_s,
        "measured_duration_s": measured_duration_s,
        "subtitles_file": str(ass_file),
        "word_timestamps_file": str(subtitles_file),
        "transcript_segments_file": str(segments_file),
        "segments": segments,
        "subtitles": subtitles,
    }

    prov = Provenance(
        generator="stages.s09_voice_tts",
        latency_sec=round(time.time() - start_ts, 2),
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=prov,
    )

    emit_artifact(artifact, ctx.paths)
    return artifact
