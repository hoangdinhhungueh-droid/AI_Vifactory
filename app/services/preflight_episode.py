# app/services/preflight_episode.py — Phase 2b (Luong chuan v1, BUOC 8).
# POST /api/v1/episodes/<episode_id>/preflight
# The single "green light to press render" gate (diem xanh bam may):
#   1. COMPILE   — compiler with --require-images: every BG/FG reuse key has
#                  an Approved/Pulled-by-VPS row in Image Asset Library, plus
#                  all compiler validations (CPS Rule 75, prompt <=1700
#                  Rule 32, banned objects, narration/duration present).
#                  (FG _nobg >80% transparent was already enforced FAIL-HARD
#                  at generation time, Rule 76 — failed images never reach
#                  IAL, so Approved status implies the check passed.)
#   2. HASH      — compile_log.json content_hash matches the brain_input.json
#                  just compiled (proves no drift between Notion and disk).
#   3. DURATION  — total scene duration >= VF_PREFLIGHT_MIN_DUR (default
#                  480s = Long >= 8' mid-roll requirement, 7 KHOA #4).
#   4. TTS       — audio + subtitles.srt exist in the episode dir (B7 done).
# One consolidated JSON → the /video:produce skill turns it into ONE Telegram
# message. Every check reports ok + detail; overall ok = ALL checks pass.
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

EPISODES_DIR = Path("/var/vf/episodes")
COMPILER = "/root/video_factory/scripts/compile_episode_from_notion.py"
MIN_DUR = float(os.environ.get("VF_PREFLIGHT_MIN_DUR", "480"))


@router.post("/api/v1/episodes/{episode_id}/preflight")
async def preflight(episode_id: str):
    episode_id = (episode_id or "").strip()
    if not episode_id:
        return {"ok": False, "error": "episode_id required"}
    ep_dir = EPISODES_DIR / episode_id
    checks = {}

    # 1. COMPILE (with image gate)
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, COMPILER, episode_id, "--require-images"],
            capture_output=True, text=True, timeout=300)
        last = (proc.stdout or "").strip().splitlines()
        comp = {}
        if last:
            try:
                comp = json.loads(last[-1])
            except Exception:
                comp = {}
        ok = proc.returncode == 0 and comp.get("ok")
        checks["compile_and_images"] = {
            "ok": bool(ok),
            "detail": "scenes=%s hash=%s"
                      % (comp.get("scenes"),
                         str(comp.get("content_hash", ""))[:12]) if ok
                      else (comp.get("error")
                            or (proc.stderr or proc.stdout)[-300:]),
        }
    except Exception as e:
        checks["compile_and_images"] = {"ok": False,
                                        "detail": "compiler run failed: %s" % e}

    # 2. HASH — compile_log hash == brain_input hash
    try:
        brain = json.loads((ep_dir / "brain_input.json").read_text(
            encoding="utf-8"))
        log = json.loads((ep_dir / "compile_log.json").read_text(
            encoding="utf-8"))
        same = bool(brain.get("_content_hash")) and \
            brain.get("_content_hash") == log.get("content_hash")
        checks["hash_match"] = {
            "ok": same,
            "detail": "brain=%s log=%s"
                      % (str(brain.get("_content_hash"))[:12],
                         str(log.get("content_hash"))[:12]),
        }
    except Exception as e:
        checks["hash_match"] = {"ok": False,
                                "detail": "cannot read brain/compile_log: %s" % e}
        brain = {}

    # 3. DURATION — Long >= 8 minutes (7 KHOA #4)
    scenes = brain.get("scenes") or []
    total = sum(float(s.get("duration_sec") or 0) for s in scenes)
    checks["duration"] = {
        "ok": bool(scenes) and total >= MIN_DUR,
        "detail": "%.0fs / min %.0fs across %d scenes" % (total, MIN_DUR,
                                                          len(scenes)),
    }

    # 4. TTS — audio + subtitle artifacts present (B7 must have run)
    audio = None
    for cand in ("tts_out.mp3", "audio_norm.mp3"):
        if (ep_dir / cand).exists():
            audio = cand
            break
    if audio is None and ep_dir.exists():
        mp3s = [p.name for p in ep_dir.glob("*.mp3")]
        if mp3s:
            audio = mp3s[0]
    srt = (ep_dir / "subtitles.srt").exists()
    checks["tts_artifacts"] = {
        "ok": bool(audio) and srt,
        "detail": "audio=%s subtitles.srt=%s"
                  % (audio or "MISSING", "ok" if srt else "MISSING"),
    }

    # 4b. TTS QUALITY (17/08/2026 - B7 pipeline audit): ffprobe the real audio
    # file, then record a "tts" row into PG audit_results for the learn loop.
    try:
        if audio:
            _ap = str(ep_dir / audio)
            _pr = await asyncio.to_thread(
                subprocess.run,
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", _ap],
                capture_output=True, text=True, timeout=60)
            _meta = json.loads(_pr.stdout or "{}")
            _dur = float((_meta.get("format") or {}).get("duration") or 0)
            _size = int((_meta.get("format") or {}).get("size") or 0)
            _st = _meta.get("streams") or []
            _sr = int(_st[0].get("sample_rate") or 0) if _st else 0
            _okq = _dur >= 60 and _size > 100000 and _sr >= 22050
            checks["tts_quality"] = {
                "ok": _okq,
                "detail": "dur=%.0fs size=%dB rate=%dHz" % (_dur, _size, _sr),
            }
            try:
                from app.audit.db import save_audit_result
                save_audit_result(
                    episode_id, "tts", "S4", 10.0 if _okq else 4.0,
                    "APPROVED" if _okq else "REVIEW",
                    {"duration_s": round(_dur, 1), "sample_rate": _sr,
                     "size_bytes": _size},
                    [] if _okq else [{"severity": "high", "axis": "audio",
                                      "message": "audio below quality thresholds"}],
                    [], "rule_only")
            except Exception as _e2:
                logger.warning("[preflight] tts audit record failed: %s", _e2)
        else:
            checks["tts_quality"] = {"ok": False, "detail": "no audio file found"}
    except Exception as e:
        checks["tts_quality"] = {"ok": False, "detail": "ffprobe failed: %s" % e}

    ok_all = all(c["ok"] for c in checks.values())
    return {"ok": ok_all, "episode_id": episode_id, "checks": checks,
            "verdict": "PREFLIGHT PASS" if ok_all else "PREFLIGHT FAIL"}
