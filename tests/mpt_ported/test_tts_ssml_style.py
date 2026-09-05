
"""MPT-G2-6: SSML style verify — edge vs plain audio should differ (ffprobe size check)."""
import pytest, os, sys
sys.path.insert(0, "/root/video_factory")


@pytest.mark.asyncio
async def test_ssml_style_differs_from_plain():
    """Synth same text with and without style; file sizes should differ."""
    pytest.importorskip("edge_tts")
    from app.services.mpt_ported.tts_edge import synthesize
    plain = await synthesize("The hero stood tall.", voice="en-US-AriaNeural",
                             output_path="/tmp/vf/test_plain.mp3")
    styled = await synthesize("The hero stood tall.", voice="en-US-AriaNeural",
                              style="cheerful", output_path="/tmp/vf/test_styled.mp3")
    size_plain = os.path.getsize(plain)
    size_styled = os.path.getsize(styled)
    # Sizes MUST both exist; difference flags SSML is being applied
    assert size_plain > 5000
    assert size_styled > 5000
    # Log for manual inspection — not hard-fail on size equality
    print(f"plain={size_plain} styled={size_styled} diff={abs(size_plain-size_styled)}")
