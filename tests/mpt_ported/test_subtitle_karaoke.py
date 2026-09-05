
"""MPT-G3 tests: subtitle_karaoke."""
import pytest, sys
sys.path.insert(0, "/root/video_factory")
from app.services.mpt_ported.subtitle_karaoke import _segments_to_ass, MARGIN_V

def test_segments_to_ass_basic():
    segs = [{"start_ms": 0, "end_ms": 2000, "text": "Hello world"}]
    ass = _segments_to_ass(segs, "", "bottom")
    assert "[Events]" in ass
    assert "Hello world" in ass
    assert "0:00:00.00" in ass

def test_segments_to_ass_margin_v():
    segs = [{"start_ms": 0, "end_ms": 1000, "text": "test"}]
    ass_bottom = _segments_to_ass(segs, "", "bottom")
    ass_top    = _segments_to_ass(segs, "", "top")
    assert str(MARGIN_V["bottom"]) in ass_bottom
    assert str(MARGIN_V["top"]) in ass_top

def test_segments_to_ass_cjk():
    from app.services.mpt_ported.subtitle_karaoke import NOTO_FONT_PATH
    segs = [{"start_ms": 0, "end_ms": 2000, "text": "中文"}]
    ass = _segments_to_ass(segs, NOTO_FONT_PATH, "bottom")
    assert "中文" in ass
