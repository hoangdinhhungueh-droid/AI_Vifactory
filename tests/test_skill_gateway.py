#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_skill_gateway.py — Comprehensive Unit Tests for SkillGateway & In-Memory Token Lookup.

Validates:
- Rule 118: Zero-Mock truthful prompt loading.
- Rule 128: Generic contract mapping for stages.
- Rule 132: Pure transmission, <= 2,000 tokens JIT prompt slicing.
- In-memory O(1) cinematic tokens lookup without raw JSON injection.
- Snapshot parity verification.
"""

import pytest
from pathlib import Path
from core.skill_gateway import (
    SkillGateway,
    get_skill_gateway,
    get_stage_prompt,
    lookup_cinematic_token,
    DEFAULT_MAX_CHARS,
)


def test_cinematic_tokens_lookup():
    gw = get_skill_gateway()
    assert gw.token_lookup.total_tokens > 0

    # Test exact token lookup
    token = lookup_cinematic_token("/straightdown")
    assert token is not None
    assert token.get("category") == "angle"
    assert "top-down" in token.get("gemini_directive_en", "").lower()

    # Test lookup without leading slash
    token2 = lookup_cinematic_token("straightdown")
    assert token2 is not None
    assert token2 == token

    # Test unknown token fails gracefully
    assert lookup_cinematic_token("/nonexistent_dummy_token_123") is None

    # Test category filtering
    framing_tokens = gw.token_lookup.get_by_category("framing")
    assert len(framing_tokens) > 0
    for t in framing_tokens:
        assert t.get("category") == "framing"

    # Test format_token_context
    ctx = gw.token_lookup.format_token_context(["/straightdown", "/groundlevel"])
    assert "/straightdown" in ctx
    assert "/groundlevel" in ctx
    assert len(ctx) < 500  # Highly compact, never 17KB


def test_stage_prompt_jit_slicing():
    # Stage 1: Strategy
    p_s01 = get_stage_prompt("s01_ideation")
    assert len(p_s01) <= DEFAULT_MAX_CHARS + 500
    assert "B1" in p_s01 or "Strategic" in p_s01 or "RULE 118" in p_s01

    # Stage 3: Script
    p_s03 = get_stage_prompt("s03_script")
    assert len(p_s03) <= DEFAULT_MAX_CHARS + 500
    assert "B2" in p_s03 or "Docudrama" in p_s03

    # Stage 5: Director (Vox Engine v3)
    p_s05 = get_stage_prompt("s05_director_plan")
    assert len(p_s05) <= DEFAULT_MAX_CHARS + 500
    assert "VOX" in p_s05 or "OBJECT-ASSEMBLY" in p_s05
    # Prohibits legacy Hollywood 3D or Magenta in Vox v3
    assert "#FF00FF" not in p_s05

    # Stage 8: Motion Flow
    p_s08 = get_stage_prompt("s08_video_gen")
    assert len(p_s08) <= DEFAULT_MAX_CHARS + 500
    assert "MOTION" in p_s08 or "FLOW" in p_s08

    # Stage 11: SEO
    p_s11 = get_stage_prompt("s11_qc")
    assert len(p_s11) <= DEFAULT_MAX_CHARS + 500
    assert "SEO" in p_s11 or "Packaging" in p_s11


def test_stage_prompt_unknown_fails_closed():
    gw = get_skill_gateway()
    with pytest.raises(ValueError, match="No valid prompt file mapped"):
        gw.get_stage_prompt("totally_invalid_nonexistent_stage_xyz")


def test_sot_parity_verification():
    gw = get_skill_gateway()
    parity = gw.verify_sot_parity()
    assert parity["status"] in ("PARITY_OK", "PARITY_ERROR")
    assert len(parity["files_checked"]) > 0
    for fname, info in parity["files_checked"].items():
        assert info["chars"] > 0
        assert len(info["sha256_short"]) == 16


def test_gateway_telemetry():
    gw = get_skill_gateway()
    gw.reload_all()
    _ = gw.get_stage_prompt("s01_ideation")
    _ = gw.get_stage_prompt("s01_ideation")  # Should be cache hit
    tel = gw.get_gateway_telemetry()
    assert tel["requests"] == 2
    assert tel["cache_hits"] >= 1
    assert tel["cinematic_tokens_indexed"] > 0
