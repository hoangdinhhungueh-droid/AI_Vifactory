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
    assert "waist-up three-quarter angle action framing" in fg
    assert "active hands" in fg
    assert "[ACTION & GAZE INVARIANT]" in fg
    assert "head-to-shoes" not in fg
    # Verify Gate 6 regex clean
    assert re.search(r"(Stylized editorial.*){2,}", fg, re.IGNORECASE) is None


def test_vox_actor_prop_invariant_injection():
    """Verify passive character description automatically receives active verb + prop + gaze invariant."""
    passive_fg = "Corporate compliance officer in dark suit"
    fg = _sanitize_foreground_prompt(passive_fg, fg_key="fg_character_officer", market="JP")
    assert "actively holding up documentary evidence prop" in fg
    assert "pointing index finger" in fg
    assert "[ACTION & GAZE INVARIANT]" in fg
    assert "no static standing figure with arms at sides" in fg


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

    en = resolve_market_profile("EN")
    assert en["market_code"] == "EN"


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


def test_resolve_character_anchor_decoupling_rule128():
    """Rule 128 & Rule 134: Verify non-Japanese characters in JP market are decoupled from salaryman/hanko bias."""
    raw_fg = "Chinese agricultural laborer cutting bamboo shoots on hillside"
    fg_prompt = _sanitize_foreground_prompt(
        raw_fg,
        fg_key="fg_character_chinese_bamboo_harvester",
        market="JP"
    )
    # Must have authentic Chinese regional characteristics
    assert "Authentic Chinese individual" in fg_prompt
    assert "agricultural produce" in fg_prompt or "utilitarian workwear" in fg_prompt
    # MUST NOT contain Japanese salaryman or hanko bias in positive prompt
    pos_fg = fg_prompt.split("[STRICT NEGATIVE PROMPT]")[0]
    assert "salaryman" not in pos_fg.lower()
    assert "hanko" not in pos_fg.lower()
    assert "sha-sho" not in pos_fg.lower()
    assert "no Japanese salaryman suit" in fg_prompt

    # Test Japanese civil servant character in JP market
    raw_jp = "Quarantine inspection officer checking import documents"
    jp_prompt = _sanitize_foreground_prompt(
        raw_jp,
        fg_key="fg_character_jp_quarantine_inspector",
        market="JP"
    )
    assert "Authentic Japanese public official" in jp_prompt
    assert "quarantine inspection specialist" in jp_prompt


def test_zero_aspect_ratio_mutilation_and_en_negative_isolation():
    """Verify 16:9 and 1:1 aspect ratios are never mutilated into ':aspect ratio' and EN market is free of JP tokens."""
    raw_bg = "Federal bankruptcy courtroom interior, $160 million settlement dispute, 16:9 aspect ratio"
    bg_out = _sanitize_background_prompt(raw_bg, bg_key="bg_courtroom", market="EN")
    assert "16:9" in bg_out
    assert not re.search(r"(?<!\d):\s*(?:aspect\s*ratio|1\s*aspect\s*ratio)", bg_out, re.IGNORECASE)

    raw_fg_char = "Presiding bankruptcy judge in dark judicial robe, 1:1 aspect ratio"
    fg_char_out = _sanitize_foreground_prompt(raw_fg_char, fg_key="fg_character_presiding_federal_judge", market="EN")
    assert "1:1 aspect ratio" in fg_char_out
    assert not re.search(r"(?<!\d):\s*(?:aspect\s*ratio|1\s*aspect\s*ratio)", fg_char_out, re.IGNORECASE)
    assert "salaryman" not in fg_char_out.lower()
    assert "hanko" not in fg_char_out.lower()
    assert "no magenta, purple, fuchsia, or neon pink attire" in fg_char_out

    raw_fg_prop = "Full-body Federal Court Reorganization Plan Rejection Order figure in authentic period attire, 1:1 aspect ratio"
    fg_prop_out = _sanitize_foreground_prompt(raw_fg_prop, fg_key="fg_evidence_reorganization_plan_rejection_order", market="EN")
    pos_part = fg_prop_out.split("[STRICT NEGATIVE PROMPT]")[0]
    assert "full-body" not in pos_part.lower()
    assert "figure in authentic" not in pos_part.lower()
    assert "[OBJECT FOCUS]" in fg_prop_out


def test_opus_astra_audit_macro_remediations():
    """Rule 134: Verify all 6 defects identified by Opus 5.5 and Astra 6 audit council are strictly resolved."""
    # 1. Lay CFO character anchor & vestment exclusion
    cfo_desc = "Waist-up view of a diocesan finance officer in a gray blazer and light blue shirt, running a pen down a column of a monthly operating report ledger"
    cfo_out = _sanitize_foreground_prompt(cfo_desc, fg_key="fg_character_diocesan_cfo", market="EN")
    assert "financial officer or forensic accountant" in cfo_out
    assert "no clerical collar" in cfo_out
    assert "ecclesiastical clergy vestments" not in cfo_out
    assert "Flat," not in cfo_out
    assert "Flat." not in cfo_out
    assert "pointing index finger" not in cfo_out  # Active verb 'running' suppressed contradictory pointing

    # 2. Bishop pose reconciliation & Chapter 11 semantic preservation
    bishop_desc = "Waist-up view of a bishop in black suit, pen pressed to the signature line of a Chapter 11 voluntary petition"
    bishop_out = _sanitize_foreground_prompt(bishop_desc, fg_key="fg_character_diocesan_bishop", market="EN")
    assert "federal bankruptcy reorganization" in bishop_out
    assert "hands folded before them in deliberate silence" not in bishop_out  # Active verb 'pressed' suppressed passive hands folded
    assert "Flat," not in bishop_out
    assert "unfilled template with official border" not in bishop_out  # Human character does not get spliced object template

    # 3. 1970s Parish rectory era anchor & date preservation
    rectory_desc = "2D graphic novel illustration of an East Bay parish rectory office circa 1970s: dark wood desk, rotary telephone"
    rectory_out = _sanitize_background_prompt(rectory_desc, bg_key="bg_1970s_parish_rectory_office", market="EN")
    assert "1970s era documentary aesthetic" in rectory_out
    assert "circa :" not in rectory_out
    assert "nineteen-seventies era" in rectory_out or "1970s" in rectory_out

    # 4. Fluorescent yellow highlighter enforcement
    judge_desc = "Federal bankruptcy judge examining a highlighted fee schedule on desk"
    judge_out = _sanitize_foreground_prompt(judge_desc, fg_key="fg_character_judge", market="EN")
    assert "fluorescent yellow marker ink" in judge_out


def test_opus_astra_round2_audit_macro_remediations():
    """Rule 134: Test all Root Causes identified in Round 2 audit by Opus 5.5 and Astra 6."""
    # 1. Character anchor key-priority routing (Root Cause 1):
    # Counsel handling survivor claims must receive litigator anchor, NOT survivor civilian attire
    counsel_desc = "Debtor's lead counsel reviewing survivor claims proof of claim documents"
    counsel_out = _sanitize_foreground_prompt(counsel_desc, fg_key="fg_character_debtor_counsel", market="EN")
    assert "institutional litigator" in counsel_out or "plaintiffs' legal counsel" in counsel_out
    assert "modest contemporary civilian wardrobe" not in counsel_out
    assert "dignified everyday attire" not in counsel_out
    assert "no specific real-life likeness, no celebrity likeness" in counsel_out

    comm_counsel_desc = "Creditors' committee counsel holding summary showing 99% rejection, jabbing it with an index finger"
    comm_out = _sanitize_foreground_prompt(comm_counsel_desc, fg_key="fg_character_creditors_committee_counsel", market="EN")
    assert "institutional litigator" in comm_out or "plaintiffs' legal counsel" in comm_out
    assert "no aggressive pointing" in comm_out
    assert "jabbing" not in comm_out
    assert "resting an index finger" in comm_out

    # 2. Era anchor misrouting on contemporary figures (Root Cause 2):
    judge_desc = "Federal bankruptcy judge presiding over Case 23-40523 in courtroom"
    judge_out = _sanitize_foreground_prompt(judge_desc, fg_key="fg_character_bankruptcy_judge", market="EN")
    assert "Contemporary timeline" in judge_out
    assert "1960s" not in judge_out

    bishop_desc = "Diocesan bishop sitting at conference table reviewing past 1960-1989 diocesan records"
    bishop_out = _sanitize_foreground_prompt(bishop_desc, fg_key="fg_character_diocesan_bishop", market="EN")
    assert "Contemporary timeline" in bishop_out
    assert "1960s" not in bishop_out
    assert "no specific real-life likeness, no celebrity likeness" in bishop_out

    survivor_desc = "Elderly survivor claimant holding plan ballot envelope, reflecting on 1970s experiences"
    survivor_out = _sanitize_foreground_prompt(survivor_desc, fg_key="fg_character_elderly_survivor_claimant", market="EN")
    assert "Contemporary timeline" in survivor_out
    assert "1970s era documentary aesthetic" not in survivor_out
    assert "folded personal document" not in survivor_out  # Competing prop suppressed because envelope already present!

    # 3. Category bleed into backgrounds (Root Cause 3):
    archive_bg = "Chancery archive file room with rows of labeled drawers and manila folders"
    archive_out = _sanitize_background_prompt(archive_bg, bg_key="bg_chancery_archive_file_room", market="EN")
    assert "unfilled template" not in archive_out
    assert "official border" not in archive_out
    assert "labeled drawers" not in archive_out

    court_bg = "Empty federal bankruptcy courtroom with Great Seal of the United States and evidence monitor"
    court_out = _sanitize_background_prompt(court_bg, bg_key="bg_empty_bankruptcy_courtroom", market="EN")
    assert "Great Seal of the United States" not in court_out
    assert "evidence monitor" not in court_out
    assert "carved wooden eagle" in court_out

    # 4. Text-bait & title removal (Root Cause 4):
    titled_desc = "Counsel reviewing page titled 'Trust Funding' on podium"
    titled_out = _sanitize_foreground_prompt(titled_desc, fg_key="fg_character_counsel", market="EN")
    assert "titled 'Trust Funding'" not in titled_out
    assert "Trust Funding'" not in titled_out
    assert "blank legal document folio" in titled_out


