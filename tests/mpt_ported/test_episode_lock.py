"""Tests for episode state / lock table."""
import pytest
import sys; sys.path.insert(0, "/root/video_factory")

def test_vf_episode_state_table():
    """Verify vf_episode_state table exists in Postgres."""
    try:
        import psycopg2, os
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT to_regclass(%(t)s)", {"t": "public.vf_episode_state"})
        result = cur.fetchone()[0]
        conn.close()
        assert result is not None, "vf_episode_state table missing"
    except ImportError:
        pytest.skip("psycopg2 not installed")

def test_episode_id_format():
    """episode_id must follow ep-<lang>-<slug>-<id> pattern."""
    import re
    pattern = re.compile(r"^ep-[a-z]{2}-[a-z0-9-]+-[a-z0-9]+$")
    valid   = ["ep-en-isekai-001", "ep-vi-truyen-abc", "ep-ko-story-x99"]
    invalid = ["episode_001", "EP-EN-TEST", "ep_en_001"]
    for v in valid:   assert pattern.match(v), f"{v} should be valid"
    for i in invalid: assert not pattern.match(i), f"{i} should be invalid"
