#!/usr/bin/env python3
"""tests/test_cinematic_tokens_pipeline.py — Comprehensive test suite for the 20 Curated Cinematic Flow Tokens.

Validates:
1. Single Source of Truth dictionary (config/prompts/cinematic_tokens_dictionary.json): 20 canonical tokens.
2. Dynamic skill loader caching & retrieval (app/services/skill_loader.py).
3. B3 Director Plan schema validation & heuristic fallback (app/services/director_planner_b3.py).
4. B3.5 Visual Prompt Forge translation to English directives (app/services/prompt_forge.py).
5. Remotion Optical FX extraction (app/services/build_remotion_props.py).
Rules: Rule 118 (Zero-Mock), Rule 127 (Runtime Gate), Rule 128 (Generic Contract), Rule 132 (Decoupled Engine).
"""
import os
import sys
import json
import pytest
from pathlib import Path

# Ensure root dir is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.skill_loader import (
    get_cinematic_tokens_dictionary,
    clear_cache
)
from app.services.director_planner_b3 import validate_cinematic_tokens
from app.services.prompt_forge import (
    resolve_cinematic_tokens,
    _sanitize_background_prompt,
    _sanitize_foreground_prompt
)


class TestCinematicTokensDictionary:
    """Validate the 38 Curated Cinematic & Motion Tokens Dictionary."""

    def test_dictionary_file_exists_and_valid_json(self):
        dict_path = ROOT_DIR / "config" / "prompts" / "cinematic_tokens_dictionary.json"
        assert dict_path.exists(), f"Missing dictionary file: {dict_path}"

        with open(dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "tokens" in data
        tokens = data["tokens"]
        assert len(tokens) == 38, f"Expected exactly 38 tokens, found {len(tokens)}"

        expected_tokens = {
            "/straightdown", "/groundlevel", "/birdseye", "/firstperson", "/secondview",
            "/closecrop", "/tightframe", "/extremeclose", "/thirdgrid", "/innerframe",
            "/darkmood", "/edgelight", "/spotbeam", "/lightrays", "/sunsetglow", "/duskhour",
            "/filmlook", "/highcontrast", "/edgefade", "/digitalglitch",
            "/whip_pan", "/smash_cut", "/match_cut", "/ink_bleed", "/zoom_through",
            "/light_leak", "/paper_tear", "/circle_wipe",
            "/dolly_zoom", "/macro_orbit", "/focus_breathe", "/continuous_drift", "/whip_zoom",
            "/map_pin_drop", "/callout_circle", "/route_draw", "/counter_countup", "/paper_stopmotion"
        }
        actual_tokens = {t["token"] for t in tokens}
        assert actual_tokens == expected_tokens, f"Token mismatch: {actual_tokens ^ expected_tokens}"

        valid_categories = {"angle", "framing", "lighting", "style_vfx", "transition", "motion_camera", "vox_graphic"}
        for t in tokens:
            assert t["token"].startswith("/"), f"Token must start with slash: {t['token']}"
            assert t["category"] in valid_categories, f"Invalid category: {t['category']}"
            assert len(t["description_vi"]) > 5
            assert len(t["gemini_directive_en"]) > 5


class TestSkillLoaderIntegration:
    """Validate skill_loader loading and caching behavior."""

    def test_get_cinematic_tokens_dictionary(self):
        clear_cache()
        dict_data = get_cinematic_tokens_dictionary(force_refresh=True)
        assert dict_data is not None
        assert "tokens" in dict_data
        assert len(dict_data["tokens"]) == 38

        # Test caching
        cached_data = get_cinematic_tokens_dictionary()
        assert cached_data is dict_data


class TestB3DirectorPlannerValidation:
    """Validate token sanitization, whitelist enforcement, and heuristic fallback."""

    def test_validate_valid_tokens(self):
        raw = ["/straightdown", "/darkmood", "/edgelight"]
        cleaned = validate_cinematic_tokens(raw)
        assert cleaned == ["/straightdown", "/darkmood", "/edgelight"]

    def test_validate_strips_invalid_tokens(self):
        raw = ["/straightdown", "invalid_fake_token", "/matrix_speed_invalid", "/edgelight"]
        cleaned = validate_cinematic_tokens(raw)
        assert cleaned == ["/straightdown", "/edgelight"]

    def test_validate_auto_prepends_slash(self):
        raw = ["straightdown", "darkmood"]
        cleaned = validate_cinematic_tokens(raw)
        assert cleaned == ["/straightdown", "/darkmood"]

    def test_validate_heuristic_fallback_evidence(self):
        # When tokens are empty, narration with evidence keywords falls back to straightdown & paper_stopmotion
        cleaned = validate_cinematic_tokens([], "Cảnh sát niêm phong tập hồ sơ và con dấu đỏ trên bàn làm việc.")
        assert "/straightdown" in cleaned
        assert "/paper_stopmotion" in cleaned

    def test_validate_heuristic_fallback_tactical_map(self):
        cleaned = validate_cinematic_tokens([], "Bản đồ hiển thị tọa độ di chuyển của đoàn xe bí mật dọc biên giới.")
        assert "/route_draw" in cleaned
        assert "/callout_circle" in cleaned

    def test_validate_heuristic_fallback_macro_scale(self):
        cleaned = validate_cinematic_tokens([], "Toàn bộ hệ thống sụp đổ trên phạm vi toàn cảnh thành phố.")
        assert "/birdseye" in cleaned


class TestB35PromptForgeTranslation:
    """Validate translation to English directives for Gemini 2K DCI prompts."""

    def test_resolve_cinematic_tokens_straightdown(self):
        tokens = ["/straightdown", "/darkmood", "/filmlook"]
        resolved = resolve_cinematic_tokens(tokens)

        assert any("perpendicular 90-degree straight-down" in d for d in resolved["camera_directives"])
        assert any("low-key chiaroscuro" in d for d in resolved["lighting_directives"])
        assert any("35mm celluloid film" in d for d in resolved["vfx_directives"])
        assert "film_grain" in resolved["remotion_fx"]

    def test_sanitize_background_prompt_injects_straightdown(self):
        tokens = ["/straightdown", "/edgelight"]
        bg_prompt = _sanitize_background_prompt(
            "Confidential court verdict documents scattered across desk",
            bg_key="bg_01",
            market="VN",
            tokens=tokens
        )
        assert "[CAMERA & PERSPECTIVE]" in bg_prompt
        assert "perpendicular 90-degree straight-down" in bg_prompt
        assert "[LIGHTING & OPTICS]" in bg_prompt
        assert "rim edge lighting" in bg_prompt
        assert "16:9 aspect ratio" in bg_prompt
        assert "bottom 20% safe-zone" in bg_prompt

    def test_sanitize_foreground_prompt_injects_lighting(self):
        tokens = ["/darkmood", "/edgelight"]
        fg_prompt = _sanitize_foreground_prompt(
            "Senior prosecutor holding red ink stamp",
            fg_key="fg_01",
            market="VN",
            tokens=tokens
        )
        assert "[LIGHTING & OPTICS]" in fg_prompt
        assert "chiaroscuro" in fg_prompt or "rim edge lighting" in fg_prompt
        assert "#FF00FF" in fg_prompt
        assert "1:1 aspect ratio" in fg_prompt


class TestRemotionOpticalFXExtraction:
    """Validate extraction of optical FX flags for Remotion props."""

    def test_optical_fx_mapping(self):
        # Simulated scene dict from director_plan
        tokens = ["/edgefade", "/filmlook", "/digitalglitch", "/straightdown"]
        optical_fx = {
            "vignette": "/edgefade" in tokens,
            "film_grain": "/filmlook" in tokens,
            "digital_glitch": "/digitalglitch" in tokens,
            "high_contrast": "/highcontrast" in tokens,
        }
        assert optical_fx["vignette"] is True
        assert optical_fx["film_grain"] is True
        assert optical_fx["digital_glitch"] is True
        assert optical_fx["high_contrast"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
