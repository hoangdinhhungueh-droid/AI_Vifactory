"""Tests for @idempotent_stage decorator."""
import asyncio, pytest
import sys; sys.path.insert(0, "/root/video_factory")
from app.services.mpt_ported.state import idempotent_stage

call_count = 0

@idempotent_stage("test_stage")
async def _fake_stage(episode: dict) -> dict:
    global call_count
    call_count += 1
    return {**episode, "processed": True}

def test_decorator_callable():
    assert callable(_fake_stage)

def test_decorator_preserves_name():
    assert _fake_stage.__name__ == "_fake_stage"

def test_stage_runs():
    global call_count; call_count = 0
    ep = {"episode_id": "ep-test-001", "text": "hello"}
    result = asyncio.run(_fake_stage(ep))
    assert result["processed"] is True
    assert result["episode_id"] == "ep-test-001"

def test_stage_passthrough():
    ep = {"episode_id": "ep-test-002", "text": "world", "extra": 42}
    result = asyncio.run(_fake_stage(ep))
    assert result["extra"] == 42
    assert result["processed"] is True
