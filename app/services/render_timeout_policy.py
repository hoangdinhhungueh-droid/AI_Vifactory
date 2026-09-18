# -*- coding: utf-8 -*-
"""Canonical Render Timeout Policy for AI Video Factory (Rule 134 Compliance).

Establishes a single source of truth for render timeouts across all pipeline layers:
  1. Child Remotion render (scripts/render_twolayer_visual.py)
  2. Subprocess wrapper in pipeline (app/pipeline/run_episode.py)
  3. Master stage orchestrator (scripts/continue_after_images.py)

Mathematical Guarantees:
  - Strict Hierarchy: T_continue > T_run_episode > T_remotion (zero premature caller kills)
  - Scalability: Accounts for software CPU rasterization with Vox-style multi-layer CSS transforms
    (rate down to ~0.70 fps -> safe allocation = 2.0s per frame + 7200s buffer)
  - Underflow Floor: Never below 36000s (10 hours) for production safety.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple, Union


# Minimum safe floor in seconds (10 hours)
MIN_RENDER_TIMEOUT_FLOOR = 36000.0

# Multiplier per frame (seconds per frame allocation for CPU rendering)
SECONDS_PER_FRAME_ALLOCATION = 2.0

# Base buffer added to frame calculations (2 hours)
RENDER_BASE_BUFFER_SEC = 7200.0

# Staggered caller buffers ensuring caller > child strict hierarchy
RUN_EPISODE_BUFFER_SEC = 3600.0   # +1 hour over Remotion
CONTINUE_STAGE_BUFFER_SEC = 7200.0 # +2 hours over Remotion


def extract_frames_from_props(props_path: Union[str, Path], default_frames: int = 18000) -> int:
    """Extract exact frame count from remotion_props.json scenes array.
    
    Falls back to durationInFrames top-level key, then default_frames on failure.
    """
    path = Path(props_path)
    if not path.exists():
        return default_frames
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        scenes = data.get("scenes") or []
        if scenes:
            return sum(max(1, int(s.get("durationInFrames", 1))) for s in scenes)
        return int(data.get("durationInFrames", default_frames))
    except Exception:
        return default_frames


def compute_render_timeout_hierarchy(
    total_frames: int,
    base_timeout: float = MIN_RENDER_TIMEOUT_FLOOR
) -> Dict[str, float]:
    """Compute the authoritative timeout hierarchy for a given frame count.
    
    Returns a dict with:
      - 'remotion_timeout': Watchdog for npx remotion render
      - 'run_episode_timeout': Timeout for subprocess in run_episode.py
      - 'continue_timeout': Timeout for B4-B7 stage in continue_after_images.py
      - 'total_frames': Extracted or provided frame count
      - 'estimated_render_sec': Raw estimated render duration
    """
    frames = max(1, int(total_frames))
    raw_calc = float(frames) * SECONDS_PER_FRAME_ALLOCATION + RENDER_BASE_BUFFER_SEC
    remotion_t = max(float(base_timeout), raw_calc, MIN_RENDER_TIMEOUT_FLOOR)
    
    # Enforce strict hierarchy: continue > run_episode > remotion
    run_ep_t = remotion_t + RUN_EPISODE_BUFFER_SEC
    cont_t = remotion_t + CONTINUE_STAGE_BUFFER_SEC
    
    return {
        "remotion_timeout": remotion_t,
        "run_episode_timeout": run_ep_t,
        "continue_timeout": cont_t,
        "total_frames": frames,
        "estimated_render_sec": float(frames) * SECONDS_PER_FRAME_ALLOCATION,
    }


if __name__ == "__main__":
    import sys
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 18000
    h = compute_render_timeout_hierarchy(frames)
    print(json.dumps(h, indent=2))
