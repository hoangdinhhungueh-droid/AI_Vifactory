"""Simulated-output safety gate (Rule 70, muc 5): a video/audio asset that was
produced as a placeholder/simulated fallback (e.g. TTS engine unreachable so a
silent/beep track was substituted, or an image generator failed so a solid-color
placeholder frame was used) must NEVER reach S7 final render / publish silently.

STATUS: WIRED IN (07/08/2026). Imported by app/pipeline/stages/s4_tts.py,
s5_visuals.py, s6_subtitle.py, s7_render.py (assert_not_simulated gates) and
app/pipeline/run_episode.py (mark_simulated call site: the S5 solid-color
fallback_bg.mp4 path, when no stock/AI clips are available). The scripts/
simulated_asset_gate.py copy is now a thin re-export shim for CLI callers;
this app/services/ copy is the canonical implementation -- edit here.

Convention: any stage that falls back to a placeholder/simulated asset calls
mark_simulated(path, reason) to drop a sidecar "<path>.simulated.json" file
next to it. Before final mux/publish, assert_not_simulated(paths) raises if any
sidecar is found, so a simulated asset can only proceed with an explicit
human/Notion-AI override (Rule 70 muc 5's "never silent" requirement).
"""
import json
import os
import time


def _sidecar_path(asset_path: str) -> str:
    return asset_path + ".simulated.json"


def mark_simulated(asset_path: str, reason: str, stage: str) -> str:
    """Call this from a pipeline stage when it had to substitute a
    placeholder/simulated asset instead of a real one.
    """
    sidecar = _sidecar_path(asset_path)
    payload = {
        "asset_path": asset_path,
        "reason": reason,
        "stage": stage,
        "marked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return sidecar


def is_simulated(asset_path: str):
    sidecar = _sidecar_path(asset_path)
    if not os.path.exists(sidecar):
        return None
    with open(sidecar, "r", encoding="utf-8") as f:
        return json.load(f)


def assert_not_simulated(asset_paths):
    """Raise RuntimeError listing every simulated asset found among
    asset_paths. Call sites: top of s4_tts.run_s4 (post-synth), top of
    s5_visuals.run_s5 (pre-generation), top of s6_subtitle.run_s6
    (pre-alignment), and top of s7_render.run_s7 (pre-mux, the primary gate).
    """
    problems = []
    for path in asset_paths:
        info = is_simulated(path)
        if info is not None:
            problems.append(info)
    if problems:
        raise RuntimeError(
            "BLOCKED: %d simulated/placeholder asset(s) would have been rendered silently: %s"
            % (len(problems), json.dumps(problems, ensure_ascii=False))
        )
    return True


def clear_simulated(asset_path: str) -> bool:
    """Explicit human/Notion-AI override after re-checking the asset is fine."""
    sidecar = _sidecar_path(asset_path)
    if os.path.exists(sidecar):
        os.remove(sidecar)
        return True
    return False
