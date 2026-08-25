"""Page 22 item C — S8 Shorts Repurpose (Phase 5, 07/08/2026).

Deterministic, heuristic short-form repurposing of a finished long-form
episode into a vertical Short (<=60-75s). This is NOT ML highlight
detection (no such model/paid API is available on this VPS) — it is a
rule-based cutter that uses REAL, already-accurate timing sources:

  - subtitles.srt (word/sentence-level timestamps synced to the final
    normalized audio actually baked into final_916.mp4), and
  - brain_input.json scenes[].beat (to find the "hook" scene reliably).

Why heuristic, not ML: YouTube/TikTok highlight-detection models are not
available here (no GPU inference stack, no paid highlight API wired into
this project). Instead we apply a documented, testable heuristic:
  1. HOOK block = the first scene(s) tagged beat=="hook" in brain_input.json,
     bounded by the matching subtitle timestamps (usually 0-8s).
  2. CLIMAX block = the subtitle segment cluster with the highest density of
     "pattern-interrupt" / high-intensity cue words (contrast words,
     numbers, questions, superlatives) located in the last third of the
     episode — narratively, paydown/twist beats cluster there in this
     story format (see story_gate.py PATTERN_INTEREST design).
  3. Concatenate HOOK + CLIMAX (trimmed to fit target_duration_s), then
     append a short loop-tail (re-shows the first ~1s hook frame) so the
     Short loops seamlessly on autoplay.

This module produces a REAL output file (ffmpeg concat), not just a plan,
but every result carries manual_review_required=True: a human should watch
the cut before posting, since the cue-word heuristic can pick a mediocre
climax on atypical scripts. This mirrors the transparency requirement used
for build_end_screen_config()/generate_ab_variants() in Phase 5 B/H/I.

Public API:
    build_shorts_plan(episode_dir, target_duration_s=60) -> dict (no file IO)
    generate_shorts(episode_dir, target_duration_s=60, video_key="final_916",
                     out_name="short_01.mp4") -> dict (writes an mp4 + meta json)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cue words that tend to mark a pattern-interrupt / twist / payoff beat.
# Kept intentionally simple & auditable (no ML), same spirit as story_gate.py.
_CUE_WORDS = [
    "but", "however", "until", "then", "suddenly", "never", "secret",
    "truth", "actually", "turns out", "here is", "here's", "nobody",
    "almost nobody", "what if", "why", "how did", "shocking", "betrayed",
    "revenge", "死", "twist",
]

_SRT_TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def _srt_ts_to_s(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(srt_path: str) -> List[Dict[str, Any]]:
    """Parse a .srt file into [{start_s, end_s, text}], sorted by start_s."""
    if not os.path.exists(srt_path):
        return []
    with open(srt_path, "r", encoding="utf-8") as f:
        raw = f.read()
    blocks = re.split(r"\n\s*\n", raw.strip())
    out: List[Dict[str, Any]] = []
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = None
        text_lines = []
        for ln in lines:
            mm = _SRT_TIME_RE.search(ln)
            if mm:
                m = mm
            elif not ln.strip().isdigit():
                text_lines.append(ln.strip())
        if not m:
            continue
        start_s = _srt_ts_to_s(*m.groups()[0:4])
        end_s = _srt_ts_to_s(*m.groups()[4:8])
        out.append({"start_s": start_s, "end_s": end_s, "text": " ".join(text_lines)})
    out.sort(key=lambda x: x["start_s"])
    return out


def _hook_window(brain_input: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, float]:
    """Find the hook window's [start_s, end_s] using brain_input scenes beat==hook
    duration, clipped to available subtitle timeline. Defaults to first 8s.
    """
    scenes = brain_input.get("scenes") or []
    hook_dur = 0.0
    for sc in scenes:
        if (sc.get("beat") or "").lower() == "hook":
            hook_dur += float(sc.get("duration_sec") or 0)
    if hook_dur <= 0:
        hook_dur = 8.0
    end_s = hook_dur
    if segments:
        total = segments[-1]["end_s"]
        end_s = min(hook_dur, total)
    return {"start_s": 0.0, "end_s": round(end_s, 2)}


def _score_segment(text: str) -> int:
    t = (text or "").lower()
    score = 0
    for cue in _CUE_WORDS:
        if cue in t:
            score += 1
    if "?" in t:
        score += 1
    if re.search(r"\d", t):
        score += 1
    return score


def _climax_window(
    segments: List[Dict[str, Any]], hook_end_s: float, target_s: float
) -> Optional[Dict[str, Any]]:
    """Slide a target_s-wide window over the last third of the transcript and
    pick the window with the highest cumulative cue-word score.
    """
    if not segments:
        return None
    total_end = segments[-1]["end_s"]
    search_start = max(hook_end_s, total_end * 0.55)
    candidates = [s for s in segments if s["start_s"] >= search_start]
    if not candidates:
        candidates = [s for s in segments if s["start_s"] >= hook_end_s]
    if not candidates:
        return None
    best = None
    best_score = -1
    for i, seg in enumerate(candidates):
        window_start = seg["start_s"]
        window_end = window_start + target_s
        cluster = [
            c for c in candidates if c["start_s"] >= window_start and c["start_s"] < window_end
        ]
        if not cluster:
            continue
        score = sum(_score_segment(c["text"]) for c in cluster)
        actual_end = min(cluster[-1]["end_s"], window_end)
        if score > best_score:
            best_score = score
            best = {
                "start_s": round(window_start, 2),
                "end_s": round(actual_end, 2),
                "score": score,
                "text_preview": " ".join(c["text"] for c in cluster)[:220],
            }
    return best


def build_shorts_plan(episode_dir: str, target_duration_s: float = 60.0) -> Dict[str, Any]:
    """Compute (but do not cut) hook + climax windows for a Short. Pure/no file IO
    beyond reading brain_input.json and subtitles.srt.
    """
    brain_path = os.path.join(episode_dir, "brain_input.json")
    srt_path = os.path.join(episode_dir, "subtitles.srt")
    brain_input = {}
    if os.path.exists(brain_path):
        with open(brain_path, "r", encoding="utf-8") as f:
            brain_input = json.load(f)
    segments = parse_srt(srt_path)
    if not segments:
        return {
            "ok": False,
            "reason": "no_subtitles_srt_found",
            "episode_dir": episode_dir,
        }
    hook = _hook_window(brain_input, segments)
    remaining = max(5.0, target_duration_s - (hook["end_s"] - hook["start_s"]))
    climax = _climax_window(segments, hook["end_s"], remaining)
    cut_list = [{"label": "hook", **hook}]
    if climax:
        cut_list.append({"label": "climax", **climax})
    total_s = sum(c["end_s"] - c["start_s"] for c in cut_list)
    return {
        "ok": True,
        "episode_dir": episode_dir,
        "cut_list": cut_list,
        "estimated_short_duration_s": round(total_s, 2),
        "method": "heuristic_cue_word_v1",
        "manual_review_required": True,
        "notes": (
            "Deterministic heuristic (no ML highlight detection available on this "
            "VPS). Climax window chosen by contrast/question/number cue-word "
            "density in the back half of the transcript. Always preview before "
            "posting."
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


def generate_shorts(
    episode_dir: str,
    target_duration_s: float = 60.0,
    video_key: str = "final_916",
    out_name: str = "short_01.mp4",
    loop_tail_s: float = 1.0,
) -> Dict[str, Any]:
    """Cut hook+climax from an already-rendered vertical master into a real
    Short mp4, with a short loop-tail (re-appends the opening ~loop_tail_s of
    the hook) so playback loops seamlessly. Writes:
      <episode_dir>/shorts/<out_name>
      <episode_dir>/shorts/<out_name>.meta.json
    """
    plan = build_shorts_plan(episode_dir, target_duration_s=target_duration_s)
    if not plan.get("ok"):
        return plan
    src = os.path.join(episode_dir, video_key + ".mp4")
    if not os.path.exists(src):
        return {"ok": False, "reason": "source_video_not_found", "path": src}
    shorts_dir = os.path.join(episode_dir, "shorts")
    os.makedirs(shorts_dir, exist_ok=True)
    out_path = os.path.join(shorts_dir, out_name)

    cut_list = plan["cut_list"]
    tmp_parts = []
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, cut in enumerate(cut_list):
                part_path = os.path.join(tmpdir, "part_%d.mp4" % i)
                dur = max(0.5, cut["end_s"] - cut["start_s"])
                _run_ffmpeg([
                    "-ss", str(cut["start_s"]), "-i", src, "-t", str(dur),
                    "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero",
                    part_path,
                ])
                tmp_parts.append(part_path)
            # loop-tail: re-show the first loop_tail_s of the hook at the very end
            hook_cut = cut_list[0]
            loop_end = min(hook_cut["start_s"] + loop_tail_s, hook_cut["end_s"])
            loop_part = os.path.join(tmpdir, "loop_tail.mp4")
            _run_ffmpeg([
                "-ss", str(hook_cut["start_s"]), "-i", src, "-t",
                str(max(0.3, loop_end - hook_cut["start_s"])),
                "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero",
                loop_part,
            ])
            tmp_parts.append(loop_part)

            concat_list_path = os.path.join(tmpdir, "concat_list.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for p in tmp_parts:
                    f.write("file '%s'\n" % p)
            _run_ffmpeg([
                "-f", "concat", "-safe", "0", "-i", concat_list_path,
                "-c", "copy", out_path,
            ])
    except Exception as e:
        logger.exception("[shorts_repurpose] ffmpeg cut failed for %s", episode_dir)
        return {"ok": False, "reason": "ffmpeg_error", "detail": str(e)}

    meta = {
        "ok": True,
        "episode_dir": episode_dir,
        "out_path": out_path,
        "cut_list": cut_list,
        "loop_tail_s": loop_tail_s,
        "method": plan["method"],
        "manual_review_required": True,
        "suggested_hashtags": ["#shorts", "#Shorts"],
        "notes": plan["notes"],
    }
    meta_path = out_path + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    meta["meta_path"] = meta_path
    return meta


if __name__ == "__main__":
    import sys
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else "/var/vf/episodes/genghis-khan-2026-ep005"
    print(json.dumps(build_shorts_plan(ep_dir), indent=2, ensure_ascii=False))
