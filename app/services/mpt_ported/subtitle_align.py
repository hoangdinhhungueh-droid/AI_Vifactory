
"""MPT-G3-2 - Subtitle alignment: faster-whisper primary + Groq fallback."""
import asyncio, os, time
from pathlib import Path
from typing import Optional

# FIX 08/08/2026: default model 'small' instead of 'medium' to prevent OOM
# crash on VPS with limited RAM (medium peaked 1.92GB, small ~800MB).
# Override per-lang via env: WHISPER_MODEL_EN=medium etc.
WHISPER_MODEL_PER_LANG = {
    "en": os.getenv("WHISPER_MODEL_EN", "small"),
    "vi": os.getenv("WHISPER_MODEL_VI", "small"),
    "zh": os.getenv("WHISPER_MODEL_ZH", "small"),
    "ja": os.getenv("WHISPER_MODEL_JA", "small"),
    "ko": os.getenv("WHISPER_MODEL_KO", "small"),
}
WHISPER_CACHE = os.getenv("WHISPER_CACHE", "~/.cache/huggingface/hub")
GROQ_DAILY_CAP_SECONDS = 6500   # Groq ASR ~6500s audio/day free

_groq_used_seconds: float = 0.0


def _get_model(lang_code: str) -> str:
    return WHISPER_MODEL_PER_LANG.get(lang_code, "medium")


async def _align_whisper(audio_path: str, lang_code: str) -> list:
    """Run faster-whisper in executor to avoid blocking event loop."""
    def _run():
        from faster_whisper import WhisperModel
        model_name = _get_model(lang_code)
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, language=lang_code,
                                           word_timestamps=True)
        result = []
        for seg in segments:
            words = []
            for w in (getattr(seg, "words", None) or []):
                words.append({
                    "start_ms": int(w.start * 1000),
                    "end_ms":   int(w.end * 1000),
                    "word":     w.word,
                })
            result.append({
                "start_ms": int(seg.start * 1000),
                "end_ms":   int(seg.end * 1000),
                "text":     seg.text.strip(),
                "words":    words,
            })
        return result
    loop = asyncio.get_event_loop()
    # FIX 08/08/2026: timeout to prevent indefinite hang/OOM crash
    try:
        import subprocess as _sp
        _pr = _sp.run(["ffprobe", "-v", "error", "-show_entries",
                       "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                       audio_path], capture_output=True, text=True)
        _dur_est = float(_pr.stdout.strip() or 60.0)
    except Exception:
        _dur_est = 60.0
    timeout_s = float(os.getenv("WHISPER_TIMEOUT_S", str(max(600, int(_dur_est * 1.5)))))
    return await asyncio.wait_for(
        loop.run_in_executor(None, _run),
        timeout=timeout_s,
    )


async def _align_groq(audio_path: str, lang_code: str, transcript: Optional[str]) -> list:
    """Groq Whisper fallback — uses daily cap tracking."""
    global _groq_used_seconds
    import groq
    client = groq.Groq(api_key=os.getenv("GROQ_API_KEY", ""))

    # Estimate duration
    try:
        import subprocess
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                           "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                           audio_path], capture_output=True, text=True)
        duration = float(r.stdout.strip() or 0)
    except Exception:
        duration = 60.0

    if _groq_used_seconds + duration > GROQ_DAILY_CAP_SECONDS:
        raise RuntimeError(f"[subtitle_align] Groq ASR daily cap reached ({_groq_used_seconds:.0f}s used)")

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(Path(audio_path).name, f),
            model="whisper-large-v3",
            response_format="verbose_json",
            language=lang_code,
        )
    _groq_used_seconds += duration

    segments = []
    for seg in (transcription.segments or []):
        segments.append({
            "start_ms": int(seg.start * 1000),
            "end_ms":   int(seg.end * 1000),
            "text":     seg.text.strip(),
        })
    return segments



async def _align_proportional(transcript: str, audio_path: str, lang_code: str) -> list:
    """Last-resort fallback: split transcript by sentences, distribute
    proportionally by word count. No external API/model needed.
    FIX 08/08/2026: prevents go-live crash from OOM or API failures."""
    import re as _re
    import subprocess as _sp

    if not transcript:
        ep_dir = Path(audio_path).parent
        for fname in ["brain_input.json", "story.txt"]:
            fpath = ep_dir / fname
            if fpath.exists():
                try:
                    if fname.endswith(".json"):
                        import json as _j
                        b = _j.loads(fpath.read_text(encoding="utf-8"))
                        transcript = b.get("story") or b.get("story_text") or b.get("text")
                    else:
                        transcript = fpath.read_text(encoding="utf-8")
                    if transcript:
                        break
                except Exception:
                    pass
    if not transcript:
        raise RuntimeError("proportional fallback requires transcript text")

    r = _sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True)
    duration_s = float(r.stdout.strip() or 0)
    if duration_s <= 0:
        duration_s = 60.0

    text = transcript.strip()
    sentences = _re.split(r"(?<=[.?!])\s+(?=[A-Z])", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [{"start_ms": 0, "end_ms": int(duration_s * 1000), "text": text}]

    # Further split long sentences (>18 words)
    result = []
    for s in sentences:
        wc = len(s.split())
        if wc > 18:
            words = s.split()
            split_done = False
            for i in range(10, len(words)):
                if words[i].endswith(",") or words[i].endswith("--") or words[i].endswith(":"):
                    result.append(" ".join(words[:i + 1]))
                    rest = " ".join(words[i + 1:])
                    if rest:
                        result.extend(_re.split(r"(?<=[.?!])\s+(?=[A-Z])", rest))
                    split_done = True
                    break
            if not split_done:
                result.append(s)
        else:
            result.append(s)

    total_words = sum(len(s.split()) for s in result)
    segments = []
    t = 0.0
    for s in result:
        wc = len(s.split())
        dur = (wc / total_words) * duration_s if total_words > 0 else duration_s / len(result)
        segments.append({
            "start_ms": int(t * 1000),
            "end_ms": int((t + dur) * 1000),
            "text": s,
        })
        t += dur

    return segments


async def align_subtitles(
    audio_path: str,
    transcript: Optional[str] = None,
    lang_code: str = "en",
    backend: str = "auto",       # "whisper", "groq", "auto"
) -> list:
    """
    Returns list of {start_ms, end_ms, text}.
    backend=auto: tries faster-whisper first, falls back to Groq.
    """
    errors = []
    def _safe_log(msg):
        try:
            print(msg, flush=True)
        except (BrokenPipeError, OSError):
            pass

    if backend in ("whisper", "auto"):
        try:
            return await _align_whisper(audio_path, lang_code)
        except Exception as e:
            errors.append(f"whisper: {e}")
            if backend == "whisper":
                raise
            _safe_log(f"[subtitle_align] whisper failed: {e} — trying Groq fallback")
    if backend in ("groq", "auto"):
        try:
            return await _align_groq(audio_path, lang_code, transcript)
        except Exception as e:
            errors.append(f"groq: {e}")
            if backend == "groq":
                raise
            _safe_log(f"[subtitle_align] groq failed: {e} — trying proportional fallback")
    # Last resort: proportional distribution (no external API needed)
    _safe_log(f"[subtitle_align] using proportional fallback (errors: {'; '.join(errors)})")
    return await _align_proportional(transcript, audio_path, lang_code)
