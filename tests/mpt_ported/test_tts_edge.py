
"""MPT-G2 tests: tts_edge synthesize + SSML builder."""
import pytest, sys, os
sys.path.insert(0, "/root/video_factory")

from app.services.mpt_ported.tts_edge import build_ssml, SSML_SUPPORTED_VOICES


def test_build_ssml_plain():
    """build_ssml without style should produce valid SSML."""
    ssml = build_ssml("Hello world", "en-US-AriaNeural")
    assert '<speak' in ssml
    assert 'Hello world' in ssml
    assert '<voice' in ssml


def test_build_ssml_with_style():
    """build_ssml with supported style should include express-as tag."""
    ssml = build_ssml("Hello", "en-US-AriaNeural", style="cheerful")
    assert 'mstts:express-as' in ssml
    assert 'cheerful' in ssml


def test_build_ssml_unsupported_style():
    """build_ssml with unsupported style should drop style gracefully."""
    ssml = build_ssml("Hello", "vi-VN-HoaiMyNeural", style="cheerful")
    # vi-VN-HoaiMyNeural has no supported styles -> no express-as
    assert 'mstts:express-as' not in ssml


def test_build_ssml_xml_escape():
    """Special XML chars must be escaped."""
    ssml = build_ssml("a & b < c > d", "en-US-AriaNeural")
    assert "&amp;" in ssml
    assert "&lt;" in ssml
    assert "&gt;" in ssml


def test_ssml_voices_dict():
    """SSML_SUPPORTED_VOICES must contain EN + VI entries."""
    assert "en-US-AriaNeural" in SSML_SUPPORTED_VOICES
    assert "vi-VN-HoaiMyNeural" in SSML_SUPPORTED_VOICES


@pytest.mark.integration
@pytest.mark.asyncio
async def test_synthesize_live():
    """Live edge-tts call — skip if network unavailable."""
    pytest.importorskip("edge_tts")
    import asyncio
    from app.services.mpt_ported.tts_edge import synthesize
    out = await synthesize("Hello, this is a test.", output_path="/tmp/vf/test_tts.mp3")
    assert os.path.exists(out)
    assert os.path.getsize(out) > 5000
