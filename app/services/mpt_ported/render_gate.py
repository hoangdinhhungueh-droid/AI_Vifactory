"""S7 render quality gate - automatic pre/post-render validation.

Catches EP001-class defects (black-screen renders, silent / dead-air audio,
truncated output) BEFORE an episode is shipped, instead of relying on the
manual scripts/qa_gate_phase1.py run after the fact.

  pre_render_check  -> validate inputs (clips + audio) before rendering.
  post_render_check -> validate the deliverable (video+audio streams, duration
                       match, black-frame ratio, dead-air) after rendering.

All checks are cheap/deterministic ffprobe + ffmpeg (blackdetect/silencedetect),
CPU-only, 0 credit. Failures are returned as structured dicts; the caller
decides whether to hard-fail or flag for review.

Env:
  QA_BLACK_MAX     '0.6'   max black-frame ratio (first 20s)
  QA_SILENCE_MAX   '12'    max dead-air seconds (first 60s of deliverable)
  QA_DUR_TOL_FRAC  '0.15'  allowed |out-audio| duration drift (fraction)
  QA_DUR_TOL_MIN   '3'     min absolute duration tolerance (seconds)
  QA_GATE_HARD     '0'     '1' -> raise RenderGateError on primary-aspect fail
"""
import asyncio
import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class RenderGateError(RuntimeError):
    """Raised when a primary-aspect render fails the gate and QA_GATE_HARD=1."""


def _f(env: str, default: float) -> float:
    try:
        return float(os.environ.get(env, str(default)))
    except ValueError:
        return default


def gate_hard() -> bool:
    return os.environ.get("QA_GATE_HARD", "0") not in ("0", "false", "False", "")


async def _run(cmd: list, timeout: int = 180) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return ""
    return (out.decode(errors="ignore") + err.decode(errors="ignore"))


async def _probe(path: str) -> dict:
    out = await _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,codec_name",
        "-of", "json", path], timeout=60)
    try:
        data = json.loads(out)
        streams = data.get("streams", []) or []
        return {
            "ok": True,
            "has_video": any(s.get("codec_type") == "video" for s in streams),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams),
            "duration": float((data.get("format") or {}).get("duration") or 0.0),
        }
    except Exception:
        return {"ok": False, "has_video": False, "has_audio": False, "duration": 0.0}


async def _black_ratio(path: str, sample_s: int = 20) -> float:
    out = await _run([
        "ffmpeg", "-hide_banner", "-nostats", "-t", str(sample_s),
        "-i", path, "-vf", "blackdetect=d=0.2:pix_th=0.10",
        "-an", "-f", "null", "-"], timeout=180)
    total = 0.0
    for m in re.finditer(r"black_duration:([0-9.]+)", out):
        try:
            total += float(m.group(1))
        except Exception:
            pass
    return max(0.0, min(total / float(sample_s), 1.0))


async def _silence_s(path: str, sample_s: int = 60) -> float:
    out = await _run([
        "ffmpeg", "-hide_banner", "-nostats", "-t", str(sample_s),
        "-i", path, "-af", "silencedetect=n=-35dB:d=0.5",
        "-f", "null", "-"], timeout=180)
    total = 0.0
    for m in re.finditer(r"silence_duration: ([0-9.]+)", out):
        try:
            total += float(m.group(1))
        except Exception:
            pass
    return total


async def pre_render_check(clip_paths: list, audio_path: str) -> dict:
    """Validate inputs before render. Returns {ok, issues, metrics}."""
    issues = []
    paths = [p for p in (clip_paths or []) if p and Path(str(p)).exists()]
    if not paths:
        issues.append("no_clip_files")
    if not (audio_path and Path(str(audio_path)).exists()):
        issues.append("missing_audio")
        audio_dur = 0.0
    else:
        audio_dur = (await _probe(audio_path)).get("duration", 0.0)
        if audio_dur < 1.0:
            issues.append("audio_too_short")
    metrics = {"clip_count": len(paths), "audio_dur": round(audio_dur, 2)}
    ok = not issues
    logger.info("[render_gate] pre-check ok=%s issues=%s %s", ok, issues, metrics)
    return {"ok": ok, "issues": issues, "metrics": metrics}


async def _wh(path: str):
    """Frame size of the first video stream, or (0, 0)."""
    out = await _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", path], timeout=60)
    try:
        w, h = out.strip().splitlines()[0].split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


async def _bar_frac(path: str, sample_s: int = 12) -> float:
    """Fraction of the frame taken up by black bars (pillarbox / letterbox).

    0.0 means the picture fills the frame. ~0.66 is a 9:16 clip padded into a
    16:9 frame. Returns 0.0 when cropdetect gives nothing usable, so this can
    never fail an otherwise-good render.
    """
    fw, fh = await _wh(path)
    if not (fw and fh):
        return 0.0
    # Sample three windows: one scene can be full-frame while the rest of the
    # episode is pillarboxed (EP002 scene 1 was a full-frame Remotion card).
    info = await _probe(path)
    try:
        dur = float(info.get("duration") or 0.0)
    except Exception:
        dur = 0.0
    if dur > (sample_s * 4):
        offsets = [dur * 0.10, dur * 0.45, dur * 0.80]
    else:
        offsets = [2.0]
    worst = 0.0
    for off in offsets:
        out = await _run([
            "ffmpeg", "-hide_banner", "-nostats",
            "-ss", str(round(max(off, 0.0), 2)), "-t", str(sample_s),
            "-i", path, "-vf", "cropdetect=24:2:0", "-an", "-f", "null", "-"],
            timeout=180)
        areas = []
        for m in re.finditer(r"crop=(\d+):(\d+):(-?\d+):(-?\d+)", out):
            cw, ch = int(m.group(1)), int(m.group(2))
            if cw > 0 and ch > 0:
                areas.append(cw * ch)
        if not areas:
            continue
        # Median, not max: one full-frame frame during an xfade must not hide
        # bars that are present for the rest of the window.
        areas.sort()
        med = areas[len(areas) // 2]
        frac = 1.0 - (float(med) / float(fw * fh))
        worst = max(worst, frac)
    return max(0.0, min(worst, 1.0))


async def post_render_check(output_path: str, audio_path: str = "",
                            is_primary: bool = True) -> dict:
    """Validate the rendered deliverable. Returns {ok, issues, metrics}.

    Hard-fails (when QA_GATE_HARD=1 and is_primary) on missing file, no video,
    no audio, mostly-black, excessive dead-air, or large duration drift.
    """
    black_max = _f("QA_BLACK_MAX", 0.6)
    silence_max = _f("QA_SILENCE_MAX", 12.0)
    dur_tol_frac = _f("QA_DUR_TOL_FRAC", 0.15)
    dur_tol_min = _f("QA_DUR_TOL_MIN", 3.0)
    bar_max = _f("QA_BAR_MAX", 0.12)

    issues = []
    if not (output_path and Path(str(output_path)).exists()):
        result = {"ok": False, "issues": ["output_missing"], "metrics": {}}
        if gate_hard() and is_primary:
            raise RenderGateError("render gate: output_missing %s" % output_path)
        return result

    pr = await _probe(output_path)
    if not pr.get("has_video"):
        issues.append("no_video_stream")
    if not pr.get("has_audio"):
        issues.append("no_audio_stream")
    out_dur = pr.get("duration", 0.0)
    if out_dur < 1.0:
        issues.append("output_too_short")

    black = await _black_ratio(output_path, 20)
    if black >= black_max:
        issues.append("mostly_black:%.2f" % black)

    # GATE 27/07/2026: bars check. blackdetect misses pillarbox/letterbox
    # because those frames are not fully black (EP002 scored 0.0 while ~2/3 of
    # the frame was a side bar).
    bar_frac = await _bar_frac(output_path, 12)
    if bar_frac >= bar_max:
        issues.append("pillar_letterbox:%.2f" % bar_frac)

    silence = await _silence_s(output_path, 60)
    if silence > silence_max:
        issues.append("dead_air:%.1fs" % silence)

    audio_dur = 0.0
    if audio_path and Path(str(audio_path)).exists():
        audio_dur = (await _probe(audio_path)).get("duration", 0.0)
        if audio_dur > 0 and out_dur > 0:
            tol = max(dur_tol_min, audio_dur * dur_tol_frac)
            if abs(out_dur - audio_dur) > tol:
                issues.append("duration_drift:%.1fvs%.1f" % (out_dur, audio_dur))

    metrics = {
        "duration": round(out_dur, 2),
        "audio_dur": round(audio_dur, 2),
        "black_ratio_20s": round(black, 3),
        "bar_frac": round(bar_frac, 3),
        "silence_s_60s": round(silence, 2),
        "has_video": pr.get("has_video"),
        "has_audio": pr.get("has_audio"),
    }
    ok = not issues
    logger.info("[render_gate] post-check %s ok=%s issues=%s %s",
                Path(str(output_path)).name, ok, issues, metrics)
    if not ok and gate_hard() and is_primary:
        raise RenderGateError("render gate FAILED %s: %s" % (output_path, issues))
    return {"ok": ok, "issues": issues, "metrics": metrics}
