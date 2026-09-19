import asyncio
import os
import subprocess
import pytest
import sys
sys.path.insert(0, "/root/video_factory")

from app.services.mpt_ported import render_gate as rg
from app.services.mpt_ported.render_gate import post_render_check, RenderGateError


def _mk(monkeypatch, *, has_audio, has_video=True, duration=30.0,
        black=0.0, bars=0.0, silence=0.0, mean_db=-18.0, lufs=-14.0, freeze=0.0, fps=30.0):
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
    async def _integrated_lufs(path):
        return lufs
    async def _freeze_detect(path, s=60):
        return freeze
    async def _fps_check(path):
        return fps
    monkeypatch.setattr(rg, "_probe", _probe)
    monkeypatch.setattr(rg, "_black_ratio", _black_ratio)
    monkeypatch.setattr(rg, "_bar_frac", _bar_frac)
    monkeypatch.setattr(rg, "_silence_s", _silence_s)
    monkeypatch.setattr(rg, "_mean_volume_db", _mean_volume_db)
    monkeypatch.setattr(rg, "_integrated_lufs", _integrated_lufs)
    monkeypatch.setattr(rg, "_freeze_detect", _freeze_detect)
    monkeypatch.setattr(rg, "_fps_check", _fps_check)


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


# --- C-02: delivery loudness must really be -14 LUFS ----------------------

@pytest.mark.asyncio
async def test_loudness_on_target_passes(monkeypatch, outfile):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, lufs=-14.0)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is True
    assert res["metrics"]["integrated_lufs"] == -14.0


@pytest.mark.asyncio
async def test_loudness_within_tolerance_passes(monkeypatch, outfile):
    # LIVE mux lands around -14.5 LUFS; the +/-2 dB window must accept it.
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, lufs=-15.7)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_legacy_minus26_is_now_flagged(monkeypatch, outfile):
    # The old probe accepted -26..-22 as "good". That is 12 dB too quiet.
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, lufs=-26.0)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is False
    assert "loudness_off:-26.0LUFS" in res["issues"]


@pytest.mark.asyncio
async def test_loudness_off_raises_when_gate_hard(monkeypatch, outfile):
    monkeypatch.setenv("QA_GATE_HARD", "1")
    _mk(monkeypatch, has_audio=True, lufs=-26.0)
    with pytest.raises(RenderGateError):
        await post_render_check(outfile, "", is_primary=True)


@pytest.mark.asyncio
async def test_loudness_target_env_override(monkeypatch, outfile):
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    monkeypatch.setenv("QA_LUFS_TARGET", "-24.0")
    _mk(monkeypatch, has_audio=True, lufs=-24.3)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_lufs_measurement_failure_does_not_fail_gate(monkeypatch, outfile):
    # ffmpeg missing / unparseable output -> None, never a gate failure.
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, lufs=None)
    res = await post_render_check(outfile, "", is_primary=True)
    assert res["ok"] is True
    assert res["metrics"]["integrated_lufs"] is None


@pytest.mark.asyncio
async def test_silent_audio_is_not_double_reported_as_loudness(monkeypatch, outfile):
    # Digital silence already fails as silent_audio; measuring its (absurdly
    # low) LUFS would add a redundant second issue, so it is skipped.
    monkeypatch.delenv("QA_GATE_HARD", raising=False)
    _mk(monkeypatch, has_audio=True, mean_db=-91.0, lufs=-70.0)
    res = await post_render_check(outfile, "", is_primary=False)
    assert any(i.startswith("silent_audio") for i in res["issues"])
    assert not any(i.startswith("loudness_off") for i in res["issues"])
    assert res["metrics"]["integrated_lufs"] is None


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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_ebur128_parses_a_known_loudness(tmp_path):
    # Guards the "I:  -x.x LUFS" regex against ffmpeg output-format drift.
    out = str(tmp_path / "tone.mp4")
    _ffmpeg(["-f", "lavfi", "-i", "sine=frequency=440:duration=3",
             "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
             "-t", "3", "-shortest", "-pix_fmt", "yuv420p", out])
    val = await rg._integrated_lufs(out)
    assert val is not None
    assert -60.0 < val < 0.0
