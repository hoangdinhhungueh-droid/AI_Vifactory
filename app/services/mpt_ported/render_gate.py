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
  QA_LUFS_TARGET   '-14.0' integrated-loudness delivery target (LUFS)
  QA_LUFS_TOL      '2.0'   allowed |LUFS - target| before loudness_off
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


async def _mean_volume_db(path: str, sample_s: int = 60) -> float:
    """Mean volume (dB) of the first sample_s. Digital silence -> ~ -91 dB /
    -inf; real narration is ~ -14..-24 dB. Returns -91.0 when ffmpeg emits no
    mean_volume line (treat as silent)."""
    out = await _run([
        "ffmpeg", "-hide_banner", "-nostats", "-t", str(sample_s),
        "-i", path, "-af", "volumedetect", "-f", "null", "-"], timeout=180)
    m = re.search(r"mean_volume:\s*(-?[0-9.]+)\s*dB", out)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return -91.0
    return -91.0


async def _integrated_lufs(path: str):
    """Integrated program loudness (LUFS) via ebur128, over the whole file.
    Returns the final Summary 'I:' value, or None when unparseable -- a
    measurement failure must not, on its own, fail an otherwise-good render.
    Real -14 LUFS delivery is the target; digital silence reads far lower."""
    try:
        out = await _run([
            "ffmpeg", "-hide_banner", "-nostats",
            "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], timeout=300)
    except Exception:
        return None
    vals = re.findall(r"I:\s*(-?[0-9.]+)\s*LUFS", out)
    if not vals:
        return None
    try:
        return float(vals[-1])
    except Exception:
        return None


async def _freeze_detect(path: str, sample_s: int = 60) -> float:
    """Detect visual freeze frames (>3.0s visual freeze) using ffmpeg freezedetect."""
    out = await _run([
        "ffmpeg", "-hide_banner", "-nostats", "-t", str(sample_s),
        "-i", path, "-vf", "freezedetect=n=-50dB:d=3.0",
        "-an", "-f", "null", "-"], timeout=180)
    max_freeze = 0.0
    for m in re.finditer(r"freeze_duration:\s*([0-9.]+)", out):
        try:
            max_freeze = max(max_freeze, float(m.group(1)))
        except Exception:
            pass
    return max_freeze


async def _fps_check(path: str) -> float:
    """Extract frame rate of primary video stream."""
    out = await _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", path], timeout=60)
    try:
        raw = out.strip().splitlines()[0]
        if "/" in raw:
            num, den = raw.split("/", 1)
            return float(num) / float(den) if float(den) > 0 else 0.0
        return float(raw or 0.0)
    except Exception:
        return 0.0


def check_rule136_props(props_path: str) -> list:
    """Rule 136: Verify zero asset leaks / filenames in speaker tags or lower thirds."""
    if not props_path or not os.path.exists(props_path):
        return []
    leaks = []
    try:
        with open(props_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for sc in data.get("scenes", []):
            sc_id = sc.get("id") or sc.get("scene_id") or "unknown"
            tag = sc.get("speakerTag", "")
            if any(ext in str(tag).lower() for ext in [".png", ".jpg", ".jpeg", ".webp", "hash_", "layer_", "archive x //"]):
                leaks.append(f"rule136_leak:{sc_id}:{tag}")
    except Exception:
        pass
    return leaks


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

    # C-06: detect an audio track that is present but effectively silent
    # (uniform dead-air across the sample), which the has_audio stream check
    # above cannot catch.
    mean_db = None
    if pr.get("has_audio"):
        mean_db = await _mean_volume_db(output_path, 60)
        if mean_db <= _f("QA_SILENT_DB", -60.0):
            issues.append("silent_audio:%.1fdB" % mean_db)

    # C-02: integrated-loudness compliance. volumedetect/silencedetect above
    # only catch silence, not whether the program hits the -14 LUFS delivery
    # target. Only meaningful when real (non-silent) audio is present; a
    # measurement failure (None) is not treated as a gate failure. Fails the
    # gate at the QA_GATE_HARD tier, like black/bars/drift.
    integrated_lufs = None
    lufs_target = _f("QA_LUFS_TARGET", -14.0)
    lufs_tol = _f("QA_LUFS_TOL", 2.0)
    if pr.get("has_audio") and not any(i.startswith("silent_audio") for i in issues):
        integrated_lufs = await _integrated_lufs(output_path)
        if integrated_lufs is not None and abs(integrated_lufs - lufs_target) > lufs_tol:
            issues.append("loudness_off:%.1fLUFS" % integrated_lufs)

    audio_dur = 0.0
    if audio_path and Path(str(audio_path)).exists():
        audio_dur = (await _probe(audio_path)).get("duration", 0.0)
        if audio_dur > 0 and out_dur > 0:
            tol = max(dur_tol_min, audio_dur * dur_tol_frac)
            if abs(out_dur - audio_dur) > tol:
                issues.append("duration_drift:%.1fvs%.1f" % (out_dur, audio_dur))

    # Freeze-frame detection (>3s visual freeze)
    freeze_s = await _freeze_detect(output_path, 60)
    if freeze_s >= _f("QA_FREEZE_MAX", 3.0):
        issues.append("freeze_frame:%.1fs" % freeze_s)

    # FPS drop detection (<24fps on video stream)
    fps = await _fps_check(output_path)
    if pr.get("has_video") and fps > 0 and fps < 24.0:
        issues.append("fps_drop:%.1f" % fps)

    metrics = {
        "duration": round(out_dur, 2),
        "audio_dur": round(audio_dur, 2),
        "black_ratio_20s": round(black, 3),
        "bar_frac": round(bar_frac, 3),
        "silence_s_60s": round(silence, 2),
        "freeze_s": round(freeze_s, 2),
        "fps": round(fps, 2),
        "has_video": pr.get("has_video"),
        "has_audio": pr.get("has_audio"),
        "mean_volume_db": mean_db,
        "integrated_lufs": integrated_lufs,
    }
    ok = not issues
    logger.info("[render_gate] post-check %s ok=%s issues=%s %s",
                Path(str(output_path)).name, ok, issues, metrics)
    # C-06 (always-on, independent of QA_GATE_HARD): an empty or effectively
    # silent audio track must NEVER ship on a primary deliverable. This is the
    # "assert audio-khong-rong sau render" guarantee. False-positive-free:
    # real narration is ~ -14..-24 dB, digital silence is <= -60 dB / -inf.
    audio_empty = ("no_audio_stream" in issues
                   or any(i.startswith("silent_audio") for i in issues))
    if is_primary and audio_empty:
        raise RenderGateError(
            "render gate: empty/silent audio %s: %s" % (output_path, issues))
    if not ok and gate_hard() and is_primary:
        raise RenderGateError("render gate FAILED %s: %s" % (output_path, issues))
    return {"ok": ok, "issues": issues, "metrics": metrics}
