"""S4 - TTS synthesis + visual term extraction."""
import os, logging, asyncio, subprocess
from app.services.mpt_ported.state import idempotent_stage
from app.services.mpt_ported.tts_edge import synthesize_with_fallback
from app.services.mpt_ported.visual_terms import extract_visual_terms
from app.services.simulated_asset_gate import assert_not_simulated

logger = logging.getLogger(__name__)

# FIX 07/08/2026 (EP005 QC feedback: "video dang dung giong nu, trong khi toi
# da chot 100% dung giong nam"): "en" mapped to en-US-AriaNeural (FEMALE),
# contradicting the locked decision (Decisions Log + "05 - Stage Details
# S1-S9" spec row: "Voice giong dan ong trung nien") and the rate/pitch
# tuning below (FIX 29/07/2026), which was calibrated specifically for the
# MALE voice's pacing complaint on EP004. Switched to en-US-DavisNeural.
# LOCK 17/08/2026 (user decision): ALWAYS male voice, every market/lang.
LANG_VOICE = {
    "en": "en-US-DavisNeural",
    "vi": "vi-VN-NamMinhNeural",
    "zh": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
}

async def _wav_to_mp3(wav_path: str, mp3_path: str) -> str:
    """Convert wav to mp3 via ffmpeg."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", wav_path, "-c:a", "libmp3lame", "-q:a", "2", mp3_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"wav->mp3 failed: {stderr.decode()[-200:]}")
    return mp3_path

@idempotent_stage("s4_tts")
async def run_s4(episode: dict) -> dict:
    """Input: {episode_id, text, lang_code, voice?, backend?}
    Output: episode + {audio_path, size_bytes, backend, visual_terms}"""
    episode_id = episode["episode_id"]
    text       = episode["text"]
    lang_code  = episode.get("lang_code", "en")
    voice      = episode.get("voice") or LANG_VOICE.get(lang_code, "en-US-DavisNeural")
    backend    = episode.get("backend", "auto")
    out_dir    = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)
    audio_path = os.path.join(out_dir, "tts_out.mp3")  # desired final mp3

    # FIX 29/07/2026: narration pacing. User feedback on EP004: the male
    # voice reads too fast with no emphasis. Slow it down slightly and
    # drop the pitch a touch for a documentary delivery.
    tts_rate = episode.get("tts_rate") or os.getenv("VF_TTS_RATE", "-8%")
    tts_pitch = episode.get("tts_pitch") or os.getenv("VF_TTS_PITCH", "-2Hz")
    # ENHANCE 05/08/2026: SSML auto-emphasis for standout numbers/statistics.
    # Env kill-switch VF_TTS_EMPHASIS=0 disables instantly without a redeploy
    # of pipeline code (same on/off pattern as VF_STORY_GATE/VF_STORY_JUDGE).
    # NOTE 07/08/2026: no longer has any runtime effect (tts_edge.synthesize()
    # fix removed the custom-SSML path) -- kept wired for compatibility.
    tts_emphasize_raw = episode.get("tts_emphasize")
    if tts_emphasize_raw is None:
        tts_emphasize_raw = os.getenv("VF_TTS_EMPHASIS", "1")
    tts_emphasize = str(tts_emphasize_raw) not in ("0", "false", "False", "off")
    logger.info("[S4] %s voice=%s backend=%s rate=%s pitch=%s emphasize=%s",
                episode_id, voice, backend, tts_rate, tts_pitch, tts_emphasize)
    result = await synthesize_with_fallback(
        text=text, voice=voice, output_path=audio_path, backend=backend,
        rate=tts_rate, pitch=tts_pitch, emphasize=tts_emphasize)

    # synthesize_with_fallback may return a different path (e.g. piper .wav)
    actual_path = result.get("path", audio_path)
    used_backend = result.get("backend", "unknown")

    # If piper returned .wav, convert to .mp3
    if actual_path != audio_path and actual_path.endswith(".wav"):
        logger.info("[S4] converting piper wav -> mp3: %s -> %s", actual_path, audio_path)
        await _wav_to_mp3(actual_path, audio_path)
        try:
            os.remove(actual_path)  # clean up wav
        except OSError:
            pass
        actual_path = audio_path

    size = os.path.getsize(actual_path) if os.path.exists(actual_path) else 0
    if size < 1024:
        raise RuntimeError(f"[S4] TTS output too small: {size}B at {actual_path}")

    # WIRE 07/08/2026 (Rule 70 muc 5): re-check in case a human/Notion-AI QC
    # pass already flagged this exact audio path as simulated/placeholder
    # (e.g. via an external mark_simulated call) -- never let it flow silently
    # into S5/S6/S7.
    assert_not_simulated([actual_path])

    visual_terms = await extract_visual_terms(text=text, lang_code=lang_code)
    logger.info("[S4] %s done size=%dB backend=%s terms=%d",
                episode_id, size, used_backend, len(visual_terms))

    return {**episode,
            "audio_path":   actual_path,
            "size_bytes":   size,
            "backend":      used_backend,
            "visual_terms": visual_terms}
