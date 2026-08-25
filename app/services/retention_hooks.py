"""Page 22 item D — Retention edit hooks (Phase 5, 07/08/2026).

Enforces/validates three retention-editing directives from the SEO &
Virality Playbook §6 build queue:
  1. Hook-frame 0-3s: the episode's first scene must be a real "hook" beat
     of at least 3 seconds (so autoplay/thumbnail-adjacent preview always
     lands on hook content, not slow establishing shots).
  2. Pattern-interrupt: at least one contrast/twist/question cue should
     land in the middle of the story (25-75% mark) to reset viewer
     attention before the natural mid-video drop-off point.
  3. Loop-ending: the final render should be able to loop back into its
     own opening frame without a hard visual jump, which raises replays/
     average-view-duration on Shorts/Reels-style feeds.

This is validation + a best-effort ffmpeg loop-tail builder, not a full
re-cut of the master render: rewriting run_s7's render_video()/build_cards()
editing decisions (shot order, pacing) is a much larger scope change that
would need explicit design sign-off before touching the production render
path. Kept deliberately in the same spirit as build_end_screen_config() /
generate_ab_variants(): a transparent report + an optional, separate,
non-destructive artifact (loop-tail clip) rather than a silent pipeline
rewrite.

Public API:
    validate_retention_hooks(episode_dir) -> dict (report only, no file IO writes)
    build_loop_tail(episode_dir, video_key="final_916", loop_tail_s=1.0,
                     out_name="loop_tail.mp4") -> dict (writes a small mp4)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, List

from app.services.shorts_repurpose import parse_srt, _CUE_WORDS  # reuse SRT parsing + cue words

logger = logging.getLogger(__name__)

MIN_HOOK_S = 3.0


def _load_brain_input(episode_dir: str) -> Dict[str, Any]:
    p = os.path.join(episode_dir, "brain_input.json")
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_hook_frame(brain_input: Dict[str, Any]) -> Dict[str, Any]:
    scenes = brain_input.get("scenes") or []
    if not scenes:
        return {"passed": False, "reason": "no_scenes_found"}
    first = scenes[0]
    beat = (first.get("beat") or "").lower()
    dur = float(first.get("duration_sec") or 0)
    hook_total = sum(
        float(s.get("duration_sec") or 0) for s in scenes if (s.get("beat") or "").lower() == "hook"
    )
    if beat != "hook":
        return {
            "passed": False,
            "reason": "first_scene_is_not_a_hook_beat",
            "first_scene_beat": beat,
        }
    if hook_total < MIN_HOOK_S:
        return {
            "passed": False,
            "reason": "hook_duration_too_short",
            "hook_total_s": hook_total,
            "min_required_s": MIN_HOOK_S,
        }
    return {"passed": True, "hook_total_s": hook_total, "first_scene_duration_s": dur}


def _check_pattern_interrupt(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not segments:
        return {"passed": False, "reason": "no_subtitles_found"}
    total_end = segments[-1]["end_s"]
    lo, hi = total_end * 0.25, total_end * 0.75
    hits = []
    for seg in segments:
        if lo <= seg["start_s"] <= hi:
            t = seg["text"].lower()
            if any(cue in t for cue in _CUE_WORDS) or "?" in t:
                hits.append({"start_s": seg["start_s"], "text": seg["text"][:120]})
    if not hits:
        return {
            "passed": False,
            "reason": "no_pattern_interrupt_cue_in_middle_50pct",
            "window_s": [round(lo, 2), round(hi, 2)],
        }
    return {"passed": True, "hits": hits[:5], "hit_count": len(hits)}


def validate_retention_hooks(episode_dir: str) -> Dict[str, Any]:
    """Read-only report on hook-frame + pattern-interrupt. Loop-ending is
    reported separately via build_loop_tail (it produces a real artifact).
    """
    brain_input = _load_brain_input(episode_dir)
    srt_path = os.path.join(episode_dir, "subtitles.srt")
    segments = parse_srt(srt_path)
    hook_check = _check_hook_frame(brain_input)
    interrupt_check = _check_pattern_interrupt(segments)
    warns = []
    if not hook_check["passed"]:
        warns.append("hook_frame: " + hook_check["reason"])
    if not interrupt_check["passed"]:
        warns.append("pattern_interrupt: " + interrupt_check["reason"])
    return {
        "episode_dir": episode_dir,
        "passed": hook_check["passed"] and interrupt_check["passed"],
        "hook_frame": hook_check,
        "pattern_interrupt": interrupt_check,
        "warns": warns,
        "note": (
            "Warn-only report (does not block render/upload). Use before "
            "scripting the next episode's story beats, or as a QA checklist "
            "item alongside story_gate."
        ),
    }


def _run_ffmpeg(args: List[str]) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed: %s" % proc.stderr.decode("utf-8", "ignore")[-2000:])


def build_loop_tail(
    episode_dir: str,
    video_key: str = "final_916",
    loop_tail_s: float = 1.0,
    out_name: str = "loop_tail.mp4",
) -> Dict[str, Any]:
    """Cut the opening loop_tail_s of the master render into a small standalone
    clip. This is a non-destructive artifact (does NOT modify final_916/169/11
    in place): the caller (e.g. a future S7.5 step, after explicit sign-off)
    can concat it onto the end of the master to create a seamless loop.
    """
    src = os.path.join(episode_dir, video_key + ".mp4")
    if not os.path.exists(src):
        return {"ok": False, "reason": "source_video_not_found", "path": src}
    out_dir = os.path.join(episode_dir, "retention")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, out_name)
    try:
        _run_ffmpeg([
            "-ss", "0", "-i", src, "-t", str(loop_tail_s),
            "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero",
            out_path,
        ])
    except Exception as e:
        logger.exception("[retention_hooks] loop-tail build failed for %s", episode_dir)
        return {"ok": False, "reason": "ffmpeg_error", "detail": str(e)}
    return {
        "ok": True,
        "episode_dir": episode_dir,
        "out_path": out_path,
        "loop_tail_s": loop_tail_s,
        "manual_action_required": (
            "Concat this clip onto the master's end to enable seamless "
            "loop playback; not auto-applied to final_169/916/11 in this "
            "pass, pending sign-off to change the production render path."
        ),
    }


if __name__ == "__main__":
    import sys
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else "/var/vf/episodes/genghis-khan-2026-ep005"
    print(json.dumps(validate_retention_hooks(ep_dir), indent=2, ensure_ascii=False))
