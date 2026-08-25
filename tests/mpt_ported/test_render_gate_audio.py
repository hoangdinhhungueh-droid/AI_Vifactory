import asyncio
import os
import subprocess
import pytest
import sys
sys.path.insert(0, "/root/video_factory")

from app.services.mpt_ported import render_gate as rg
from app.services.mpt_ported.render_gate import post_render_check, RenderGateError


def _mk(monkeypatch, *, has_audio, has_video=True, duration=30.0,
        black=0.0, bars=0.0, silence=0.0, mean_db=-18.0):
    """Stub every ffprobe/ffmpeg helper so post_render_check runs hermetically
    (no external binary, no file content needed)."""
    async def _probe(path):
        return {"ok": True, "has_video": has_video,
                "has_audio": has_audio, "duration": duration}
    async def _black_ratio(path, s=20):
        return black
    async def _bar_frac(path, s=12):
        return bars
    async def _silence_s(path, s=60):
        return silence
    async def _mean_volume_db(path, s=60):
        return mean_db
    monkeypatch.setattr(rg, "_probe", _probe)
    monkeypatch.setattr(rg, "_black_ratio", _black_ratio)
    monkeypatch.setattr(rg, "_bar_frac", _bar_frac)
    monkeypatch.setattr(rg, "_silence_s", _silence_s)
    monkeypatch.setattr(rg, "_mean_volume_db", _mean_volume_db)


@pytest.fixture
def outfile(tmp_path):
    p = tmp_path / "final_169.mp4"
    p.write_bytes(b"x")  # existence check only; _probe is stubbed
    return str(p)


# --- C-06 core guarantee: audio-empty NEVER ships on a primary deliverable,
#     independent of QA_GATE_HARD (unset in these tests) --------------------

@pytest.mark.asyncio
async def test_no_audio_stream_raises_on_primary(monkeypatch, outfile):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=False)
    with pytest.raises(RenderGateError):
        await post_render_check(outfile, "", is_primary=True)


@pytest.mark.asyncio
async def test_silent_audio_raises_on_primary(monkeypatch, outfile):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, mean_db=-91.0)
    with pytest.raises(RenderGateError):
        await post_render_check(outfile, "", is_primary=True)


@pytest.mark.asyncio
async def test_audible_passes_on_primary(monkeypatch, outfile):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, mean_db=-18.0)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is True
    assert res["metrics"]["mean_volume_db"] == -18.0


@pytest.mark.asyncio
async def test_secondary_aspect_silent_does_not_raise(monkeypatch, outfile):
    # 1:1 is derived from the 16:9 master (is_primary=False); it inherits the
    # master audio, so it is logged but never blocks on its own.
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=False)
    res = await post_render_check(outfile, "", is_primary=False)
    assert res["ok"] is False
    assert "no_audio_stream" in res["issues"]


@pytest.mark.asyncio
async def test_silent_threshold_env_override(monkeypatch, outfile):
    # A -50 dB track passes the default (-60) but fails a stricter -45 gate.
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, mean_db=-50.0)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is True
    monkeypatch.setenv("QA_SILENT_DB", "-45")
    with pytest.raises(RenderGateError):
        await post_render_check(outfile, "", is_primary=True)


# --- contract: real ffmpeg-generated files (VPS only) ---------------------

def _ffmpeg(args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                   check=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_silent_mp4_is_blocked(tmp_path, monkeypatch):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    out = str(tmp_path / "silent.mp4")
    _ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
             "-t", "2", "-shortest", "-pix_fmt", "yuv420p", out])
    with pytest.raises(RenderGateError):
        await post_render_check(out, "", is_primary=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_audible_mp4_passes(tmp_path, monkeypatch):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    out = str(tmp_path / "audible.mp4")
    _ffmpeg(["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
             "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
             "-t", "2", "-shortest", "-pix_fmt", "yuv420p", out])
    res = await post_render_check(out, "", is_primary=True)
    assert res["metrics"]["has_audio"] is True
    assert res["metrics"]["mean_volume_db"] > -60.0
