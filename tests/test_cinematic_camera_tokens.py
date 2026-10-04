#!/usr/bin/env python3
"""
tests/test_cinematic_camera_tokens.py - Verifies the 7 Google Flow / Veo 3.1 cinematic camera tokens
and uppercase shorthand synonyms in prompt_forge.
"""

import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import resolve_cinematic_tokens
from app.services.skill_loader import get_cinematic_tokens_dictionary


def test_cinematic_camera_tokens_presence():
    tokens_dict = get_cinematic_tokens_dictionary(force_refresh=True)
    all_tokens = {t["token"] for t in tokens_dict.get("tokens", [])}
    
    new_camera_tokens = [
        "/macro_zoom",
        "/pov",
        "/earthzoom",
        "/glambot",
        "/product_explosion",
        "/orbit_360",
        "/commercial_grade"
    ]
    for tok in new_camera_tokens:
        assert tok in all_tokens, f"Expected {tok} in cinematic tokens dictionary"


def test_resolve_cinematic_tokens_shorthand_synonyms():
    # Test uppercase and shorthands from video directing prompts
    raw_directives = [
        "/MACRO ZOOM",
        "/POV",
        "/EARTHZOOM",
        "/GLAMBOT",
        "/PRODUCT EXPLOSION",
        "/360",
        "/TVCOMMERCIAL"
    ]
    resolved = resolve_cinematic_tokens(raw_directives)

    camera_directives = " ".join(resolved.get("camera_directives", []))
    vfx_directives = " ".join(resolved.get("vfx_directives", []))
    remotion_fx = resolved.get("remotion_fx", [])

    # Check that directives were resolved into Gemini directives
    assert "macro zoom" in camera_directives
    assert "point-of-view" in camera_directives or "POV" in camera_directives or "first-person" in camera_directives
    assert "earth-zoom" in camera_directives or "plunging" in camera_directives
    assert "glambot" in camera_directives
    assert "isometric view" in vfx_directives or "documents" in vfx_directives
    assert "orbital camera" in camera_directives or "360-degree" in camera_directives
    assert "commercial television broadcast" in vfx_directives

    # Check remotion fx mappings
    assert "macro_zoom" in remotion_fx
    assert "earthzoom_plunge" in remotion_fx
    assert "glambot_curve" in remotion_fx
    assert "exploded_dossier" in remotion_fx
    assert "orbit_360" in remotion_fx
    assert "broadcast_grade" in remotion_fx
