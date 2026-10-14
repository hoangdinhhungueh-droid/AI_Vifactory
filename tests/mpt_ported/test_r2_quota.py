"""Tests for R2 cache quota / rate-limit constants."""
import sys; sys.path.insert(0, "/root/video_factory")
import sys; sys.path.insert(0, "/root/video_factory/venv/lib/python3.12/site-packages")

def test_stock_fetcher_rate_limit_constants():
    from app.services.mpt_ported.stock_fetcher import RATE_LIMIT_CALLS, RATE_LIMIT_WINDOW
    assert RATE_LIMIT_CALLS >= 1
    assert RATE_LIMIT_WINDOW > 0
    # 200 calls/hr = max expected
    assert RATE_LIMIT_CALLS <= 200

def test_r2_cache_dir_configured():
    from app.services.mpt_ported.stock_fetcher import R2_CACHE_DIR
    assert R2_CACHE_DIR is not None
    assert len(str(R2_CACHE_DIR)) > 0


