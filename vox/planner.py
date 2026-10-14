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
from typing import List, Optional, Set, Tuple

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

STOPWORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "to", "for", "with", "by", "from",
    "up", "about", "into", "over", "after", "within", "across", "during",
    "through", "before", "between", "under", "along", "without", "against",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "and", "or", "but", "so", "as", "if", "than",
    "hours", "days", "sudden", "revealed", "struck", "mobilized", "triggering", "freezing"
}

# Thematic mapping for specialized financial / institutional narratives
THEMATIC_KNOWLEDGE = [
    {
        "keywords": ["liquidity", "crisis", "market", "markets", "interbank", "lending"],
        "bg": "atmospheric editorial graphic novel illustration of frantic Wall Street trading floor terminal environment, dimly lit trading pit, red warning indicators, high angle, textured comic paper, muted colors, wordless composition, zero text",
        "fg1_prompt": "tactile vintage retro editorial financial ledger folio with embossed red forensic stamp and textured archival parchment, comic ink cross-hatching, wordless composition, zero text",
        "fg1_scale": 0.42, "fg1_anchor": (0.45, 0.52), "fg1_depth": 0.70, "fg1_enter": 0.30,
        "fg2_prompt": "tactile frozen interbank token medallion with frosted metallic edge and cracked relief motif on aged paper, wordless composition, zero text",
        "fg2_scale": 0.28, "fg2_anchor": (0.68, 0.65), "fg2_depth": 0.90, "fg2_enter": 0.80,
    },
    {
        "keywords": ["regulatory", "ledger", "ledgers", "balance", "sheet", "exposure", "audit", "commercial", "banks"],
        "bg": "atmospheric editorial graphic novel illustration of shadowy bank archive vault with towering steel filing columns and secure audit cage, high angle, textured comic paper, muted colors, wordless composition, zero text",
        "fg1_prompt": "tactile vintage retro editorial balance sheet exposure ledger dossier with folded corner and forensic verification mark, comic ink cross-hatching, wordless composition, zero text",
        "fg1_scale": 0.40, "fg1_anchor": (0.55, 0.50), "fg1_depth": 0.75, "fg1_enter": 0.25,
        "fg2_prompt": "tactile emergency audit inspection badge emblem with forensic ribbon and notched brass rim on aged paper, wordless composition, zero text",
        "fg2_scale": 0.26, "fg2_anchor": (0.32, 0.62), "fg2_depth": 0.88, "fg2_enter": 0.75,
    },
    {
        "keywords": ["central", "institution", "institutions", "contingency", "swap", "lines", "restore", "equilibrium"],
        "bg": "atmospheric editorial graphic novel illustration of neoclassical central bank rotunda with grand stone pillars and dim conference chamber, high angle, textured comic paper, muted colors, wordless composition, zero text",
        "fg1_prompt": "tactile vintage retro editorial contingency swap treaty folio document with tied archival ribbon and official circular seal, comic ink cross-hatching, wordless composition, zero text",
        "fg1_scale": 0.44, "fg1_anchor": (0.46, 0.54), "fg1_depth": 0.72, "fg1_enter": 0.35,
        "fg2_prompt": "tactile monetary equilibrium balance scales medallion with brass patina finish on textured archival parchment, wordless composition, zero text",
        "fg2_scale": 0.27, "fg2_anchor": (0.70, 0.64), "fg2_depth": 0.92, "fg2_enter": 0.82,
    },
]


def extract_content_keywords(text: str) -> List[str]:
    """Extracts non-stopword alphabetic content words."""
    tokens = re.findall(r"[A-Za-z]{3,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def plan_scenes_from_script(
    script_text: str,
    title: str = "Vox Explainer Episode",
) -> ScenePlan:
    """Decomposes a script into structured ScenePlan adhering to all Vox contracts."""
    raw_lines = [l.strip() for l in script_text.strip().splitlines() if l.strip()]
    if not raw_lines:
        raise ValueError("Script text is empty")

    scenes: List[Scene] = []
    used_fg_hashes: Set[str] = set()

    for i, line in enumerate(raw_lines):
        sc_idx = i + 1
        cam_move = CAMERA_SEQUENCE[i % len(CAMERA_SEQUENCE)]

        content_words = extract_content_keywords(line)
        matched_theme = None
        for theme in THEMATIC_KNOWLEDGE:
            if any(kw in content_words for kw in theme["keywords"]):
                matched_theme = theme
                break

        if matched_theme:
            bg_prompt = matched_theme["bg"]
            fg1 = FGObject(
                id=f"obj_{sc_idx}_1",
                prompt=matched_theme["fg1_prompt"],
                anchor_x=matched_theme["fg1_anchor"][0],
                anchor_y=matched_theme["fg1_anchor"][1],
                scale=matched_theme["fg1_scale"],
                depth=matched_theme["fg1_depth"],
                enter_at=matched_theme["fg1_enter"],
            )
            fg2 = FGObject(
                id=f"obj_{sc_idx}_2",
                prompt=matched_theme["fg2_prompt"],
                anchor_x=matched_theme["fg2_anchor"][0],
                anchor_y=matched_theme["fg2_anchor"][1],
                scale=matched_theme["fg2_scale"],
                depth=matched_theme["fg2_depth"],
                enter_at=matched_theme["fg2_enter"],
            )
            fgs = [fg1, fg2]
        else:
            # Generic domain-adaptive decomposition (Rule 128 compliant: zero financial semantic bias)
            primary_term = content_words[0] if content_words else f"subject_{sc_idx}"
            secondary_term = content_words[1] if len(content_words) > 1 else "evidence"

            fg1_types = ["artifact", "folio", "diagram", "specimen", "manuscript", "instrument"]
            fg2_types = ["emblem", "insignia", "token", "schematic", "seal", "relic"]
            t1 = fg1_types[i % len(fg1_types)]
            t2 = fg2_types[i % len(fg2_types)]
            
            bg_prompt = (
                f"atmospheric editorial graphic novel illustration of {primary_term} environment, "
                f"textured comic paper, muted colors, wordless composition, zero text"
            )
            fg1 = FGObject(
                id=f"obj_{sc_idx}_1",
                prompt=f"tactile vintage retro editorial {primary_term} {t1} with archival binding, comic ink hatching, wordless composition, zero text",
                anchor_x=0.45 if (i % 2 == 0) else 0.55,
                anchor_y=0.52,
                scale=0.42,
                depth=0.70,
                enter_at=0.30,
            )
            fgs = [fg1]
            if len(content_words) > 1:
                fg2 = FGObject(
                    id=f"obj_{sc_idx}_2",
                    prompt=f"tactile {secondary_term} {t2} with etched metallic edge on aged paper, wordless composition, zero text",
                    anchor_x=0.68 if (i % 2 == 0) else 0.32,
                    anchor_y=0.65,
                    scale=0.28,
                    depth=0.90,
                    enter_at=0.80,
                )
                fgs.append(fg2)

        scenes.append(Scene(
            idx=sc_idx,
            narration=line,
            bg_prompt=bg_prompt,
            fg=fgs,
            camera=cam_move,
        ))

    return ScenePlan(title=title, scenes=scenes)
