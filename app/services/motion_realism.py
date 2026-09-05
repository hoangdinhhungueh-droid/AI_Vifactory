"""Realism motion-prompt guideline - makes Veo I2V clips look CHAN THUC.

The brain (Notion AI) writes the creative motion intent (what happens / camera
move). This helper appends a consistent set of realism modifiers (lighting,
physics, lens, color) so every clip across the episode shares one believable,
photoreal look. Pure stdlib, no network, FREE.

Env:
  VF_REALISM        default '1'  -> set '0' to disable enrichment
  VF_REALISM_MAXLEN default '600' -> hard cap on final prompt length

Does NOT touch the Credit Gate or budget - only the text prompt.
"""
from __future__ import annotations

import os
import re

# Realism modifiers (positive). Order = priority; near-duplicates are skipped
# when an equivalent token already appears in the brain motion prompt.
DEFAULT_REALISM = [
    "photorealistic",
    "natural realistic lighting",
    "physically accurate motion",
    "subtle handheld camera movement",
    "shallow depth of field",
    "cinematic motion blur",
    "consistent lighting and shadows",
    "lifelike skin texture",
    "true-to-life color grading",
]

# For documentation / downstream negative-prompt use (Veo prompt is positive,
# but image_gen / QA can reuse this to avoid the typical 'AI look').
REALISM_NEGATIVE = (
    "cartoon, anime, illustration, plastic skin, waxy, oversaturated, "
    "warped hands, extra fingers, jittery motion, morphing, flicker"
)

_TOKEN_RE = re.compile(r"[a-z]+")


def _has_equiv(modifier: str, low: str) -> bool:
    """True if the modifier (or a distinctive token of it) is already present."""
    if modifier.lower() in low:
        return True
    toks = [t for t in _TOKEN_RE.findall(modifier.lower()) if len(t) > 4]
    # require the MOST distinctive token (longest) to already be present
    if toks:
        distinctive = max(toks, key=len)
        if distinctive in low:
            return True
    return False


def enhance_motion_prompt(motion_prompt: str, art_style=None, enabled=None) -> str:
    mp = (motion_prompt or "").strip()
    if enabled is None:
        enabled = os.getenv("VF_REALISM", "1") not in ("0", "false", "False", "")
    if not enabled or not mp:
        return mp
    low = mp.lower()
    added = []
    for m in DEFAULT_REALISM:
        if _has_equiv(m, low):
            continue
        added.append(m)
        low += " " + m.lower()  # prevent intra-batch near-dupes
    if isinstance(art_style, dict):
        rn = (art_style.get("realism_note") or "").strip()
        if rn and rn.lower() not in low:
            added.append(rn)
    if not added:
        return mp
    out = mp.rstrip(". ") + ". " + ", ".join(added)
    try:
        cap = int(os.getenv("VF_REALISM_MAXLEN", "600"))
    except Exception:
        cap = 600
    return out[:cap].rstrip(", ")
