#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/planner.py — LLM / Rule-Based Scene Decomposition & Director Planner (AVF-VOX-001).

Decomposes script narrative into structured ScenePlan:
- 16:9 editorial background prompt (clean environment, no primary subject)
- 1 to 3 isolated foreground objects (FGObject) with anchors, scales, depths, and enter_at
- 12 canonical camera motion moves with no consecutive duplicate moves
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from vox.schemas import ScenePlan, Scene, FGObject, CameraMove


CAMERA_SEQUENCE = [
    CameraMove.PUSH_IN,
    CameraMove.PARALLAX_LEFT,
    CameraMove.KEN_BURNS_TL_BR,
    CameraMove.PAN_RIGHT,
    CameraMove.PULL_OUT,
    CameraMove.ROLL_PUSH,
    CameraMove.TILT_UP,
    CameraMove.PARALLAX_RIGHT,
    CameraMove.KEN_BURNS_BR_TL,
    CameraMove.PAN_LEFT,
    CameraMove.TILT_DOWN,
    CameraMove.STATIC_BREATH,
]


def plan_scenes_from_script(
    script_text: str,
    title: str = "Vox Explainer Episode",
) -> ScenePlan:
    """Decomposes a script into structured ScenePlan adhering to all Vox contracts."""
    raw_lines = [l.strip() for l in script_text.strip().splitlines() if l.strip()]
    if not raw_lines:
        raise ValueError("Script text is empty")

    scenes: List[Scene] = []

    for i, line in enumerate(raw_lines):
        sc_idx = i + 1
        # Pick camera move ensuring no consecutive duplicates
        cam_move = CAMERA_SEQUENCE[i % len(CAMERA_SEQUENCE)]

        # Procedural decomposition of background and foreground objects
        words = line.split()
        key_term = words[0] if words else "system"
        
        bg_prompt = f"atmospheric editorial graphic novel illustration of {key_term} architectural environment, dimly lit room, high angle, textured comic paper, muted colors"
        
        fg1 = FGObject(
            id=f"obj_{sc_idx}_1",
            prompt=f"vintage retro editorial document representing {key_term} with bold typography and tactile stamp",
            anchor_x=0.45 if (i % 2 == 0) else 0.55,
            anchor_y=0.52,
            scale=0.42,
            depth=0.7,
            enter_at=0.3
        )
        
        fgs = [fg1]
        
        # Add second FG object for visual richness if sentence has more than 5 words
        if len(words) > 5:
            fg2 = FGObject(
                id=f"obj_{sc_idx}_2",
                prompt=f"tactile red official wax seal imprint with intricate forensic stamp marking on aged parchment",
                anchor_x=0.68 if (i % 2 == 0) else 0.32,
                anchor_y=0.65,
                scale=0.28,
                depth=0.9,
                enter_at=0.8
            )
            fgs.append(fg2)

        scenes.append(Scene(
            idx=sc_idx,
            narration=line,
            bg_prompt=bg_prompt,
            fg=fgs,
            camera=cam_move
        ))

    return ScenePlan(title=title, scenes=scenes)
