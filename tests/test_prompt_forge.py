"""
Unit tests for B3.5 Prompt Engineering Forge.
Verifies concise strategic rules loader, anti-stuttering, Gate 6 greedy regex immunity, and prompt formatting.
"""
import re
import pytest
from app.services.skill_loader import get_b35_strategic_rules
from app.services.prompt_forge import (
    deduplicate_phrase_stutter,
    _sanitize_background_prompt,
    _sanitize_foreground_prompt,
    generate_scene_prompts
)


def test_concise_strategic_rules_loader():
    rules = get_b35_strategic_rules()
    assert isinstance(rules, str)
    assert 500 < len(rules) < 2500, f"Expected concise rules (~1,200 chars), got {len(rules)}"
    assert "116" in rules
    assert "120" in rules
    assert "#FF00FF" in rules
    assert "128" in rules
    assert "435" in rules


def test_anti_stuttering_gate6_greedy_regex():
    stutter_prompt = (
        "Stylized Editorial Graphic Novel Digital Illustration of Stylized Editorial figure, "
        "1:1 aspect ratio, 1:1 aspect ratio, full-body head-to-shoes, "
        "isolated on solid #FF00FF magenta background, isolated on solid #FF00FF magenta background"
    )
    sanitized = _sanitize_foreground_prompt(stutter_prompt)

    # Gate 6 test check
    greedy_match = re.search(r"(Stylized editorial.*){2,}", sanitized, re.IGNORECASE)
    assert greedy_match is None, f"Greedy regex (Stylized editorial.*){2,} matched: {sanitized}"

    # Stylized editorial must appear at most once
    count = len(re.findall(r"stylized editorial", sanitized, re.IGNORECASE))
    assert count <= 1, f"Expected at most 1 'stylized editorial', got {count}"


def test_anti_stuttering_consecutive_phrase_deduplication():
    raw_text = "1:1 aspect ratio, 1:1 aspect ratio, clean chroma-key cutout, clean chroma-key cutout"
    deduped = deduplicate_phrase_stutter(raw_text)
    assert "1:1 aspect ratio, 1:1 aspect ratio" not in deduped
    assert "clean chroma-key cutout, clean chroma-key cutout" not in deduped


def test_sanitize_background_prompt_contract():
    raw_bg = "Ancient Roman Forum in ruined marble under dramatic sunset"
    bg = _sanitize_background_prompt(raw_bg)
    assert "16:9" in bg
    assert "bottom 20% safe-zone" in bg or "safe-zone" in bg
    assert "[STYLE MANDATE]" in bg
    assert "[STRICT NEGATIVE PROMPT]" in bg
    # Verify no consecutive word stuttering
    assert not re.search(r"(\b\w+\b)\s+\1\b", bg, re.IGNORECASE)


def test_sanitize_foreground_prompt_contract():
    raw_fg = "Roman Senator in woolen toga clutching parchment scroll"
    fg = _sanitize_foreground_prompt(raw_fg)
    assert "#FF00FF" in fg
    assert "1:1 aspect ratio" in fg
    assert "[STYLE MANDATE]" in fg
    assert "full-body" in fg
    # Verify Gate 6 regex clean
    assert re.search(r"(Stylized editorial.*){2,}", fg, re.IGNORECASE) is None


from unittest.mock import patch


def test_generate_scene_prompts_fallback_dual_layer():
    mock_bg = {
        "bg_loc0": {"visual_hint": "Rural vineyard hillside under overcast gray sky"}
    }
    mock_fg = {
        "fg_char0": {"visual_hint": "Vineyard caretaker holding pruning shears"}
    }
    mock_scenes = [
        {"scene_id": "sc01", "bg_id": "bg_loc0", "fg_id": "fg_char0", "narration": "In the valley..."}
    ]

    with patch("app.services.prompt_forge.call_gpt6_astra", return_value=None):
        res = generate_scene_prompts(mock_bg, mock_fg, "Harvest Dispute", mock_scenes)
    assert "backgrounds" in res
    assert "foregrounds" in res
    assert "bg_loc0" in res["backgrounds"]
    assert "fg_char0" in res["foregrounds"]

    bg_p = res["backgrounds"]["bg_loc0"]
    fg_p = res["foregrounds"]["fg_char0"]

    assert "16:9" in bg_p
    assert "#FF00FF" in fg_p
    assert "1:1 aspect ratio" in fg_p
    assert re.search(r"(Stylized editorial.*){2,}", fg_p, re.IGNORECASE) is None


def test_generate_scene_prompts_astra_success():
    mock_bg = {"bg_loc0": {"visual_hint": "Rural vineyard hillside"}}
    mock_fg = {"fg_char0": {"visual_hint": "Vineyard caretaker"}}
    mock_scenes = [{"scene_id": "sc01", "bg_id": "bg_loc0", "fg_id": "fg_char0", "narration": "In the valley..."}]
    fake_json = '{"backgrounds": {"bg_loc0": "Ancient vineyard, 16:9 aspect ratio, bottom 20% safe-zone clear [STYLE MANDATE]"}, "foregrounds": {"fg_char0": "Stylized Editorial Graphic Novel Digital Illustration of Caretaker, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio, full-body head-to-shoes [STYLE MANDATE]"}}'
    with patch("app.services.prompt_forge.call_gpt6_astra", return_value=fake_json):
        res = generate_scene_prompts(mock_bg, mock_fg, "Harvest Dispute", mock_scenes)
    assert "bg_loc0" in res["backgrounds"]
    assert "fg_char0" in res["foregrounds"]
    assert "#FF00FF" in res["foregrounds"]["fg_char0"]


from app.services.prompt_forge import resolve_market_profile


def test_resolve_market_profile():
    jp = resolve_market_profile("JP")
    assert jp["market_code"] == "JP"
    assert "Japanese" in jp["fg_anchor"]
    assert "no Caucasian traits" in jp["fg_negatives"]

    kr = resolve_market_profile("KR")
    assert kr["market_code"] == "KR"
    assert "Korean" in kr["fg_anchor"]
    assert "no Caucasian traits" in kr["fg_negatives"]

    vn = resolve_market_profile("VN")
    assert vn["market_code"] == "VN"
    assert "Vietnamese" in vn["fg_anchor"]
    assert "no Caucasian traits" in vn["fg_negatives"]

    gl = resolve_market_profile("GLOBAL")
    assert gl["market_code"] == "GLOBAL"


def test_market_adaptive_sanitization_anti_western_bias():
    raw_fg = "Senior financial investigator examining document"
    jp_fg = _sanitize_foreground_prompt(raw_fg, market="JP")
    assert "[MARKET & ETHNIC ANCHOR]" in jp_fg
    assert "Authentic Japanese individual" in jp_fg
    assert "no Caucasian traits" in jp_fg
    assert "#FF00FF" in jp_fg

    raw_bg = "Modern executive boardroom with glass windows"
    kr_bg = _sanitize_background_prompt(raw_bg, market="KR")
    assert "[MARKET & ENVIRONMENT ANCHOR]" in kr_bg
    assert "Seoul or Yeouido" in kr_bg
    assert "no generic Western American cityscapes" in kr_bg
    assert "16:9" in kr_bg


def test_generate_scene_prompts_market_propagation():
    mock_bg = {"bg_1": {"visual_hint": "Ministry office"}}
    mock_fg = {"fg_1": {"visual_hint": "Chief prosecutor"}}
    mock_scenes = [{"scene_id": "sc01", "bg_id": "bg_1", "fg_id": "fg_1", "narration": "The scandal broke..."}]

    with patch("app.services.prompt_forge.call_gpt6_astra", return_value=None):
        res = generate_scene_prompts(
            mock_bg, mock_fg, "Tokyo Financial Scandal", mock_scenes, task_id="JP_EP0042_tokyo_scandal"
        )
    assert "backgrounds" in res and "foregrounds" in res
    fg_p = res["foregrounds"]["fg_1"]
    bg_p = res["backgrounds"]["bg_1"]
    assert "Authentic Japanese individual" in fg_p
    assert "no Caucasian traits" in fg_p
    assert "Authentic Japanese corporate or government headquarters setting" in bg_p
    assert "thumbnails" in res
    assert res["thumbnails"] == {}  # Decoupled to YouTube Studio Native Gemini Designer at HG3


def test_dynamic_acting_and_active_props_mandate():
    """Rule 122: Verify dynamic high-stakes body posture, facial micro-expressions, and active props."""
    raw_fg = "Chief prosecutor presenting indictment"
    kr_fg = _sanitize_foreground_prompt(raw_fg, market="KR")
    assert "dynamic high-stakes body posture" in kr_fg
    assert "intense facial micro-expressions" in kr_fg
    assert "active physical interaction with props" in kr_fg
    assert "ingam dojang" in kr_fg
    assert "no passive blank stare" in kr_fg
    assert "no lifeless neutral pose" in kr_fg
    assert "no passport photo posture" in kr_fg
    assert "no dead eyes" in kr_fg

    jp_prof = resolve_market_profile("JP")
    assert "hanko seal (inkan)" in jp_prof["fg_anchor"]
    assert "sha-sho" in jp_prof["fg_anchor"]
    assert "no dead eyes" in jp_prof["fg_negatives"]

    vn_prof = resolve_market_profile("VN")
    assert "dau moc do" in vn_prof["fg_anchor"]
    assert "red neck lanyard" in vn_prof["fg_anchor"]
    assert "no dead eyes" in vn_prof["fg_negatives"]


def test_object_and_evidence_prompt_sanitization():
    """Verify VOX document & evidence object prompts omit human full-body constraints."""
    raw_obj = "FTC court docket filing with yellow marker highlight"
    obj_fg = _sanitize_foreground_prompt(raw_obj, fg_key="fg_doc_ftc_docket", market="EN")
    assert "#FF00FF" in obj_fg
    assert "1:1 aspect ratio" in obj_fg
    assert "[OBJECT FOCUS]" in obj_fg
    assert "centered investigative artifact" in obj_fg
    assert "no human body" in obj_fg
    assert "full-body head-to-shoes" not in obj_fg
    assert "dynamic high-stakes body posture" not in obj_fg
