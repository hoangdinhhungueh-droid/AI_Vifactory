#!/usr/bin/env python3
"""vox/align.py — Whisper Word Timestamps & Script Text Alignment Engine (AVF-VOX-001).

Aligns speech audio with canonical script text:
- Extracts word-level timestamps using faster-whisper or acoustic fallback
- Aligns detected speech tokens to exact original script words (preserving casing & punctuation)
- Strictly enforces:
  - match_ratio >= 0.95
  - Monotonic timestamps (end > start)
  - end <= audio_duration + 0.05s
  - Populates scene.start and scene.end for every scene in ScenePlan
"""

from __future__ import annotations

import difflib
import wave
from pathlib import Path
from typing import Any

from vox.schemas import ScenePlan, Word, WordTimeline


class AlignmentUnavailableError(RuntimeError):
    """Raised when audio speech alignment is unavailable or fails match threshold."""
    pass


def get_audio_duration_wav(wav_path: Path) -> float:
    """Reads exact duration of WAV file from headers."""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def resolve_whisper_model_and_language(market: str = "EN", model_size: str = "base") -> tuple[str, str | None]:
    """Resolves market-aware Whisper model and language tag per Rule 120 & 128.

    Multilingual markets (JP, KR, VN) require the multilingual Whisper model
    without the '.en' monolingual suffix, and specify the ISO language code.
    """
    m_upper = market.upper()
    lang_map = {
        "JA": "ja", "JP": "ja",
        "KO": "ko", "KR": "ko",
        "VI": "vi", "VN": "vi",
        "EN": "en", "US": "en"
    }
    lang = lang_map.get(m_upper, "en")
    if lang == "en" and not model_size.endswith(".en") and model_size in ("tiny", "base", "small", "medium"):
        resolved_model = f"{model_size}.en"
    else:
        resolved_model = model_size.replace(".en", "")
    return resolved_model, lang


def align_script_with_audio(
    plan: ScenePlan,
    wav_path: Path,
    model_size: str = "base",
    market: str = "EN",
    language: str | None = None,
    allow_synthetic_alignment: bool = False,
) -> tuple[WordTimeline, ScenePlan]:
    """Aligns script narration to audio wav file and populates scene timecodes.

    Args:
        plan: Input ScenePlan with scenes needing start/end timestamps.
        wav_path: Path to 48kHz mono WAV narration file.
        model_size: Faster-whisper model size ('tiny', 'base', 'small', 'medium').
        market: Canonical market identifier ('EN', 'JA', 'KO', 'VN').
        language: Optional explicit ISO language code override.
        allow_synthetic_alignment: If False (production default), raises AlignmentUnavailableError
            on faster-whisper failure or low match ratio (<0.95). If True (tests only),
            falls back to deterministic linear allocation and tags alignment_model='synthetic'.

    Returns:
        Tuple of (WordTimeline, updated ScenePlan).
    """
    wav_path = Path(wav_path)
    audio_dur = get_audio_duration_wav(wav_path)
    resolved_model, detected_lang = resolve_whisper_model_and_language(market, model_size)
    target_lang = language or detected_lang

    # Collect all script words mapped to their scene index
    script_words: list[tuple[str, int]] = []
    for sc in plan.scenes:
        for w in sc.narration.strip().split():
            script_words.append((w, sc.idx))

    if not script_words:
        raise ValueError("ScenePlan contains zero words across all scenes")

    whisper_words: list[dict[str, Any]] = []
    whisper_success = False
    alignment_model = resolved_model

    # 1. Attempt live faster-whisper extraction
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(resolved_model, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(wav_path), word_timestamps=True, language=target_lang)
        for seg in segments:
            if seg.words:
                for w_obj in seg.words:
                    whisper_words.append({
                        "word": w_obj.word.strip(),
                        "start": float(w_obj.start),
                        "end": float(w_obj.end),
                        "probability": float(getattr(w_obj, "probability", 1.0)),
                    })
        if whisper_words:
            whisper_success = True
    except (ImportError, RuntimeError) as exc:
        if not allow_synthetic_alignment:
            raise AlignmentUnavailableError(
                f"faster-whisper runtime alignment unavailable: {exc}. "
                "Production paths require real audio alignment (Rule 118 & 120)."
            ) from exc
    except Exception as exc:
        if not allow_synthetic_alignment:
            raise AlignmentUnavailableError(
                f"faster-whisper transcription error: {exc}"
            ) from exc

    # 2. Test fallback gated strictly by allow_synthetic_alignment=True
    if not whisper_success or len(whisper_words) == 0:
        if not allow_synthetic_alignment:
            raise AlignmentUnavailableError(
                "Whisper detected 0 words in audio stream and allow_synthetic_alignment is False"
            )
        alignment_model = "synthetic"
        total_chars = sum(len(w[0]) for w in script_words)
        curr = 0.0
        for w_text, sc_idx in script_words:
            dur = max(0.2, (len(w_text) / max(1, total_chars)) * audio_dur)
            end_t = min(audio_dur, curr + dur)
            whisper_words.append({
                "word": w_text,
                "start": round(curr, 3),
                "end": round(max(curr + 0.1, end_t), 3),
                "probability": 1.0,
            })
            curr = end_t

    # 3. Align script tokens with Whisper timestamps using SequenceMatcher opcodes
    script_tokens = [w[0].lower().strip(".,!?:;\"'()[]{}") for w in script_words]
    whisper_tokens = [w["word"].lower().strip(".,!?:;\"'()[]{}") for w in whisper_words]

    matcher = difflib.SequenceMatcher(None, script_tokens, whisper_tokens)
    opcodes = matcher.get_opcodes()
    real_match_ratio = matcher.ratio()

    if real_match_ratio < 0.95 and not allow_synthetic_alignment:
        raise AlignmentUnavailableError(
            f"Speech alignment match ratio {real_match_ratio:.3f} is below mandatory threshold 0.95 (Rule 120). "
            f"Expected script: '{' '.join(script_tokens[:10])}...', "
            f"Whisper heard: '{' '.join(whisper_tokens[:10])}...'"
        )

    # Use SequenceMatcher opcodes to map script tokens to Whisper timestamps
    script_to_whisper: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for offset in range(i2 - i1):
                script_to_whisper[i1 + offset] = j1 + offset
        elif tag == "replace":
            span_s = i2 - i1
            span_w = j2 - j1
            for offset in range(span_s):
                w_idx = j1 + int(offset * span_w / max(1, span_s))
                script_to_whisper[i1 + offset] = min(w_idx, len(whisper_words) - 1)

    aligned_words: list[Word] = []
    last_end = 0.0
    for i, (orig_text, sc_idx) in enumerate(script_words):
        prob = 1.0
        if i in script_to_whisper and script_to_whisper[i] < len(whisper_words):
            w_item = whisper_words[script_to_whisper[i]]
            w_start = max(last_end, w_item["start"])
            w_end = max(w_start + 0.08, w_item["end"])
            prob = float(w_item.get("probability", 1.0))
        elif i < len(whisper_words):
            w_item = whisper_words[i]
            w_start = max(last_end, w_item["start"])
            w_end = max(w_start + 0.08, w_item["end"])
            prob = float(w_item.get("probability", 1.0))
        else:
            w_start = last_end
            w_end = min(audio_dur, w_start + 0.3)

        w_end = min(audio_dur + 0.05, max(w_start + 0.05, w_end))
        aligned_words.append(Word(
            text=orig_text,
            start=round(w_start, 3),
            end=round(w_end, 3),
            scene_idx=sc_idx,
            probability=round(prob, 3),
        ))
        last_end = w_end

    match_ratio = round(real_match_ratio, 3)

    fps = 30.0
    frame_dur = round(1.0 / fps, 3)
    num_scenes = len(plan.scenes)
    audio_dur_clean = round(audio_dur, 3)

    # 4. Populate Scene start and end boundaries on 30fps frame grid
    # Every scene MUST span at least 1 frame (>= frame_dur) and cover the exact audio duration
    if num_scenes == 1:
        plan.scenes[0].start = 0.0
        plan.scenes[0].end = audio_dur_clean
    else:
        # Initial forward allocation bounded by remaining frame requirements
        curr_start = 0.0
        for i in range(num_scenes - 1):
            sc = plan.scenes[i]
            sc.start = curr_start
            sc_words = [w for w in aligned_words if w.scene_idx == sc.idx]
            min_end = round(sc.start + frame_dur, 3)
            max_end = round(audio_dur_clean - (num_scenes - 1 - i) * frame_dur, 3)

            if sc_words:
                raw_target = sc_words[-1].end
            else:
                raw_target = sc.start + (audio_dur_clean - sc.start) / (num_scenes - i)

            snapped_target = round(round(raw_target * fps) / fps, 3)
            # Bound scene end so all remaining scenes have at least 1 frame
            sc.end = round(min(max(snapped_target, min_end), max_end), 3)
            curr_start = sc.end

        # Final scene consumes exactly up to audio duration
        plan.scenes[-1].start = plan.scenes[-2].end
        plan.scenes[-1].end = audio_dur_clean

        # Backtrack safety guard: ensure final scene has at least 1 frame
        if plan.scenes[-1].end <= plan.scenes[-1].start:
            for j in range(num_scenes - 2, -1, -1):
                plan.scenes[j].end = round(audio_dur_clean - (num_scenes - 1 - j) * frame_dur, 3)
                plan.scenes[j + 1].start = plan.scenes[j].end

    plan.scenes[0].start = 0.0
    plan.scenes[-1].end = audio_dur_clean
    plan.audio_duration = audio_dur_clean

    # Synchronize words to scene boundaries and guarantee monotonicity
    for sc in plan.scenes:
        sc_w = [w for w in aligned_words if w.scene_idx == sc.idx]
        if sc_w:
            for w in sc_w:
                w.start = max(sc.start, min(w.start, sc.end - 0.005))
                w.end = max(w.start + 0.005, min(w.end, sc.end))
            for k in range(len(sc_w) - 1):
                if sc_w[k].end > sc_w[k + 1].start:
                    sc_w[k + 1].start = sc_w[k].end
            sc_w[-1].end = sc.end

    timeline = WordTimeline(
        words=aligned_words,
        audio_duration=round(audio_dur, 3),
        match_ratio=match_ratio,
        alignment_model=alignment_model,
    )

    return timeline, plan
