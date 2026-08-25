
"""MPT-G3 tests: visual_terms."""
import pytest, sys
sys.path.insert(0, "/root/video_factory")

def test_import_ok():
    from app.services.mpt_ported.visual_terms import extract_visual_terms, SYSTEM_PROMPT
    assert "visual" in SYSTEM_PROMPT.lower()

@pytest.mark.asyncio
async def test_extract_fallback_when_llm_unreachable():
    """When LLM endpoint is unreachable, should return sentence-based fallback."""
    import os
    os.environ["VF_API_URL"] = "http://localhost:19999"  # unreachable
    import importlib
    import app.services.mpt_ported.visual_terms as vt
    importlib.reload(vt)
    result = await vt.extract_visual_terms("The warrior raised his sword. The dragon roared.")
    assert isinstance(result, list)
    assert len(result) >= 1
    for item in result:
        assert "visual_term" in item
        assert "duration_s" in item
    os.environ.pop("VF_API_URL", None)
