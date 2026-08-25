
"""MPT-G3 tests: subtitle position settings."""
import sys
sys.path.insert(0, "/root/video_factory")

def test_margin_v_916_bottom():
    """9:16 video bottom subtitle must have marginv=80."""
    from app.services.mpt_ported.subtitle_karaoke import MARGIN_V
    assert MARGIN_V["bottom"] == 80

def test_margin_v_top():
    from app.services.mpt_ported.subtitle_karaoke import MARGIN_V
    assert MARGIN_V["top"] == 40
