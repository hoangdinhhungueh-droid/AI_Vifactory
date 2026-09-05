"""S3 output schema — ensure visual_terms + content_type present.

Updated 08/08/2026: add scene-level visual_subject_type validation (Rule 74).
Only 2 types: A (named character) and B (stylized figure). No Type C.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CONTENT_TYPES = {"fiction", "non_fiction", "rewrite", "self_write"}

# Rule 74 (08/08/2026): Only 2 visual subject types for Foreground/core.
# Type A = named human character (Rule 46 applies — reference image).
# Type B = stylized human figure, non-named (style anchor tail, no ref image).
# Type C (no foreground) is ELIMINATED — every frame MUST have core image.
VISUAL_SUBJECT_TYPES = {"A", "B"}


def validate_scenes_visual_subject_type(episode: dict) -> dict:
    """Check per-scene visual_subject_type if present (Rule 74).

    Does NOT require the field (backward compatible with existing episodes
    that predate Rule 74). If present, validates it is A or B — warns if
    C found (deprecated, should be converted to B per Rule 74 conversion
    table). Preserves style_anchor_tail as pass-through (no validation needed).
    """
    scenes = (episode.get("scenes")
              or episode.get("brain_input", {}).get("scenes")
              or [])
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            continue
        vst = s.get("visual_subject_type")
        if vst is not None:
            vst_upper = str(vst).strip().upper()
            if vst_upper == "C":
                logger.warning(
                    "[S3] scene %d has visual_subject_type=C (deprecated, "
                    "Rule 74) — should be converted to B", i)
            elif vst_upper not in VISUAL_SUBJECT_TYPES:
                logger.warning(
                    "[S3] scene %d has unknown visual_subject_type=%r "
                    "(expected A or B, Rule 74)", i, vst)
    return episode


def validate_s3_output(episode: dict) -> dict:
    """Normalise S3 output before passing to S4+.
    
    BLOCKER FIX 31/08/2026: Add type guard to catch list-vs-dict mismatch.
    """
    # Type guard: episode must be a dict
    if not isinstance(episode, dict):
        raise TypeError(
            f"validate_s3_output expects dict, got {type(episode).__name__}. "
            f"Check caller is passing episode dict, not scenes list.")
    
    if "visual_terms" not in episode:
        episode["visual_terms"] = []
    if "content_type" not in episode:
        episode["content_type"] = "fiction"
    ct = episode["content_type"]
    if ct not in CONTENT_TYPES:
        raise ValueError("Unknown content_type: %s" % ct)
    # Rule 74 (08/08/2026): validate per-scene visual_subject_type if present
    validate_scenes_visual_subject_type(episode)
    return episode
