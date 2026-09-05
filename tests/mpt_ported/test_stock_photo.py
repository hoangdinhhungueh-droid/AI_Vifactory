
"""MPT-G3 tests: stock photo (media_type=photo) path."""
import pytest, sys
sys.path.insert(0, "/root/video_factory")
from app.services.mpt_ported.stock_fetcher import _cache_key

def test_cache_key_photo_differs_from_video():
    assert _cache_key("mountain", "photo", 0) != _cache_key("mountain", "video", 0)
