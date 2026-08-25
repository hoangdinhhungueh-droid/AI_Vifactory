
"""MPT-G3 tests: subtitle_align."""
import pytest, sys
sys.path.insert(0, "/root/video_factory")

def test_whisper_model_per_lang():
    from app.services.mpt_ported.subtitle_align import WHISPER_MODEL_PER_LANG
    assert "en" in WHISPER_MODEL_PER_LANG
    assert "vi" in WHISPER_MODEL_PER_LANG

def test_groq_cap_constant():
    from app.services.mpt_ported.subtitle_align import GROQ_DAILY_CAP_SECONDS
    assert GROQ_DAILY_CAP_SECONDS == 6500

@pytest.mark.asyncio
async def test_align_missing_file_raises():
    from app.services.mpt_ported.subtitle_align import align_subtitles
    with pytest.raises(Exception):
        await align_subtitles("/tmp/nonexistent_audio.wav", lang_code="en", backend="whisper")
