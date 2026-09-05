
"""MPT-G3-5 tests: srt_utils (fully implemented)."""
import sys
sys.path.insert(0, "/root/video_factory")
from app.services.mpt_ported.srt_utils import ms_to_srt_ts, srt_ts_to_ms

def test_ms_to_srt_ts():
    assert ms_to_srt_ts(0) == "00:00:00,000"
    assert ms_to_srt_ts(3661234) == "01:01:01,234"
    assert ms_to_srt_ts(60000) == "00:01:00,000"

def test_srt_ts_to_ms():
    assert srt_ts_to_ms("00:00:00,000") == 0
    assert srt_ts_to_ms("01:01:01,234") == 3661234
    assert srt_ts_to_ms("00:01:00.000") == 60000  # also accepts dot separator

def test_roundtrip():
    for ms in [0, 999, 60000, 3661234, 86399999]:
        assert srt_ts_to_ms(ms_to_srt_ts(ms)) == ms
