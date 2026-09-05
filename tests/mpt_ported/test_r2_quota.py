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

def test_s3_schema_content_types():
    from app.pipeline.s3_schema import validate_s3_output, CONTENT_TYPES
    assert "fiction" in CONTENT_TYPES
    assert "non_fiction" in CONTENT_TYPES
    ep = {"episode_id": "ep-en-test-001", "text": "hello"}
    out = validate_s3_output(ep)
    assert out["content_type"] == "fiction"
    assert out["visual_terms"] == []

def test_s3_schema_invalid_content_type():
    from app.pipeline.s3_schema import validate_s3_output
    import pytest
    ep = {"episode_id": "ep-en-x-001", "text": "x", "content_type": "unknown_type"}
    try:
        validate_s3_output(ep)
        assert False, "should raise"
    except ValueError as e:
        assert "unknown_type" in str(e)
