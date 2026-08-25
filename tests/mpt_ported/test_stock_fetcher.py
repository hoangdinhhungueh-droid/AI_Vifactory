
"""MPT-G3 tests: stock_fetcher."""
import pytest, sys
sys.path.insert(0, "/root/video_factory")
from app.services.mpt_ported.stock_fetcher import _cache_key, _check_rate_limit, fetch_stock_clip

def test_cache_key_stable():
    assert _cache_key("dragon", "video", 0) == _cache_key("dragon", "video", 0)
    assert _cache_key("dragon", "video", 0) != _cache_key("dragon", "photo", 0)

def test_rate_limit_does_not_raise_under_limit():
    from app.services.mpt_ported import stock_fetcher
    stock_fetcher._call_log = []
    _check_rate_limit()  # should not raise

def test_rate_limit_raises_at_cap():
    import time
    from app.services.mpt_ported import stock_fetcher
    stock_fetcher._call_log = [time.time()] * 200
    with pytest.raises(RuntimeError):
        _check_rate_limit()
    stock_fetcher._call_log = []

@pytest.mark.asyncio
async def test_fetch_no_keys_raises():
    import os
    os.environ.pop("PEXELS_API_KEY", None)
    os.environ.pop("PIXABAY_API_KEY", None)
    import importlib, app.services.mpt_ported.stock_fetcher as sf
    sf.PEXELS_API_KEY = ""
    sf.PIXABAY_API_KEY = ""
    with pytest.raises(RuntimeError):
        await fetch_stock_clip("ancient temple", media_type="video")
