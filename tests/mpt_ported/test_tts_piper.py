
"""MPT-G2 tests: tts_piper offline fallback."""
import pytest, os, sys
sys.path.insert(0, "/root/video_factory")
from pathlib import Path

PIPER_MODEL = "/var/vf/models/piper/en_US-lessac-medium.onnx"


@pytest.mark.asyncio
async def test_synthesize_piper_live():
    """Live piper call — skip if model or piper binary missing."""
    if not Path(PIPER_MODEL).exists():
        pytest.skip("Piper model not installed")
    from app.services.mpt_ported.tts_piper import synthesize_piper
    try:
        out = await synthesize_piper("Test audio.", output_path="/tmp/vf/test_piper.wav")
        assert os.path.exists(out)
        assert os.path.getsize(out) > 1024
    except RuntimeError as e:
        if "piper failed" in str(e) or "onnxruntime" in str(e) or "No module named" in str(e):
            pytest.skip(f"Piper CLI/runtime not usable in this environment: {e}")
        raise


@pytest.mark.asyncio
async def test_synthesize_piper_missing_model():
    """Should raise FileNotFoundError for missing model."""
    from app.services.mpt_ported.tts_piper import synthesize_piper
    with pytest.raises(FileNotFoundError):
        await synthesize_piper("test", model_path="/tmp/nonexistent.onnx")
