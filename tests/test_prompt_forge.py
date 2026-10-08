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
    assert "floor band" in bg or "open right space" in bg
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
    assert "no bright neon attire, no glowing saturated clothes" in fg_char_out

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


def test_opus_astra_round3_fragment_and_text_magnet_remediations():
    """Rule 134: Test all 17 Root Causes & Leaked Fragments identified in Round 3 audit by Opus 5.5 and Astra 6."""
    # 1. Bar chart & currency fragments
    raw_trust = "VOX-style comparison bar chart: left bar Trust (Mar 2024) $242 million – Final Offer over 5 years (Dec 2025) with an arrow bridging them"
    trust_out = _sanitize_foreground_prompt(raw_trust, fg_key="fg_evidence_trust_offer_bar_chart", market="EN")
    assert "(Mar )" not in trust_out
    assert "(Dec )" not in trust_out
    assert ")$" not in trust_out
    assert "$multimillion" not in trust_out
    assert "multimillion-dollar final settlement sum" in trust_out
    assert "over multi-year intervals" in trust_out

    # 2. Priority waterfall
    raw_waterfall = "Explanatory waterfall diagram: top tier Tier 1, cascading down to Tier 2, then Tier 3, with water drained before reaching the bottom tier"
    waterfall_out = _sanitize_foreground_prompt(raw_waterfall, fg_key="fg_evidence_priority_waterfall", market="EN")
    assert "cascading down to, then," not in waterfall_out
    assert "cascading down through descending structural levels" in waterfall_out

    # 3. Ballot tabulation & text magnets
    raw_ballot = "Claims agent's declaration with a summary table for the survivor claimant class and a large stylized donut chart showing REJECT versus ACCEPT"
    ballot_out = _sanitize_foreground_prompt(raw_ballot, fg_key="fg_evidence_ballot_tabulation", market="EN")
    assert "Claims agent's with" not in ballot_out
    assert "Claims agent's declaration folio" in ballot_out
    assert "donut chart showing REJECT versus ACCEPT" not in ballot_out
    assert "dual-tone proportional ring graphic" in ballot_out

    # 4. Timeline clock
    raw_clock = "Stylized tear-off desk calendar fused with a clock face, pages flying off from 2023 to 2026, clock hands spinning, a small tag reading 'Exhibit A'"
    clock_out = _sanitize_foreground_prompt(raw_clock, fg_key="fg_evidence_case_timeline_clock", market="EN")
    assert "from to," not in clock_out
    assert "across elapsed calendar years" in clock_out
    assert "tag reading ." not in clock_out
    assert "evidentiary archival tag" in clock_out

    # 5. Civil complaint stack
    raw_complaint = "Towering stack of civil complaints from Superior Court, captions reading, a counter tag reading ."
    complaint_out = _sanitize_foreground_prompt(raw_complaint, fg_key="fg_evidence_civil_complaint_stack", market="EN")
    assert "captions reading," not in complaint_out
    assert "counter tag reading ." not in complaint_out
    assert "blank official header blocks" in complaint_out

    # 6. Decade histogram
    raw_hist = "Editorial bar chart with title, bars for 1950s through 2010s with the – bars heavily inked and bracketed ."
    hist_out = _sanitize_foreground_prompt(raw_hist, fg_key="fg_evidence_claims_decade_histogram", market="EN")
    assert "– bars" not in hist_out
    assert "bracketed ." not in hist_out
    assert "prominent peak period bars" in hist_out

    # 7. Chapter 11 petition
    raw_ch11 = "Official Form 201, debtor info, filing date May 8, 2023"
    ch11_out = _sanitize_foreground_prompt(raw_ch11, fg_key="fg_evidence_chapter11_petition", market="EN")
    assert "Official Form," not in ch11_out
    assert "filing date May," not in ch11_out
    assert "Official Form blank template" in ch11_out

    # 8. Motion to dismiss
    raw_motion = "Court filing captioned 'Motion to Dismiss', filed September 2025, with electronic stamp"
    motion_out = _sanitize_foreground_prompt(raw_motion, fg_key="fg_evidence_motion_to_dismiss", market="EN")
    assert "captioned," not in motion_out
    assert "filed September," not in motion_out
    assert "with formal judicial header" in motion_out

    # 9. Dismissal order
    raw_order = "Signed court order, dated October 5, 2026, judge's signature line, a red rubber-stamp style graphic overlay"
    order_out = _sanitize_foreground_prompt(raw_order, fg_key="fg_evidence_dismissal_order", market="EN")
    assert "dated October," not in order_out
    assert "rubber-stamp style graphic overlay" not in order_out
    assert "with formal date notation line" in order_out
    assert "geometric dismiss graphic marking without typography" in order_out

    # 10. Operating loss ledger
    raw_ledger = "Open accounting ledger, totals ending at a red-circled $16 million, a pencil"
    ledger_out = _sanitize_foreground_prompt(raw_ledger, fg_key="fg_evidence_operating_loss_ledger", market="EN")
    assert "ending at a red-circled," not in ledger_out
    assert "ending at a red-circled ledger entry" in ledger_out

    # 11. Professional fees meter
    raw_meter = "Stylized analog gauge meter with needle swung to, with abstract shading, against a full-scale ring marked, ticking cash-register numerals beneath"
    meter_out = _sanitize_foreground_prompt(raw_meter, fg_key="fg_evidence_professional_fees_meter", market="EN")
    assert "needle swung to," not in meter_out
    assert "ring marked," not in meter_out
    assert "cash-register numerals" not in meter_out
    assert "swung high into the critical warning threshold" in meter_out
    assert "ring marked with division indices" in meter_out

    # 12. Settlement term sheet
    raw_term = "Settlement term sheet headed 'Agreement', with a payment schedule and a bolded line '$242M'"
    term_out = _sanitize_foreground_prompt(raw_term, fg_key="fg_evidence_settlement_term_sheet", market="EN")
    assert "headed," not in term_out
    assert "bolded line ." not in term_out
    assert "with formal title block" in term_out
    assert "bolded highlight summary rule line." in term_out

    # 13. Third amended plan
    raw_plan = "Thick bound legal document, cover reading 'Third Amended Plan', dated March 2024, with colored tabs for Trust"
    plan_out = _sanitize_foreground_prompt(raw_plan, fg_key="fg_evidence_third_amended_plan", market="EN")
    assert "cover reading," not in plan_out
    assert "dated March," not in plan_out
    assert "cover folio with blank header block" in plan_out
    assert "with formal date notation line" in plan_out

    # 14. Character investigative journalist
    raw_journo = "Journalist reviewing PACER docket sheet for Case 23-40523 and circling key entry"
    journo_out = _sanitize_foreground_prompt(raw_journo, fg_key="fg_character_investigative_journalist", market="EN")
    assert "for and circling" not in journo_out
    assert "electronic docket sheet folio with ruled grid, circling a line-item entry with a pen" in journo_out

    # 15. Character state legislator 2019
    raw_legis = "State lawmaker holding a bound document with AB 218 on the cover"
    legis_out = _sanitize_foreground_prompt(raw_legis, fg_key="fg_character_state_legislator_2019", market="EN")
    assert "with on the cover" not in legis_out
    assert "a bound legislative bill document folio with a formal blind-debossed insignia on the cover" in legis_out

    # 16. Background insurance policy warehouse
    raw_wh = "Cavernous records warehouse with banker's boxes labeled by policy year (1960, 1985), a rolling ladder"
    wh_out = _sanitize_background_prompt(raw_wh, bg_key="bg_insurance_policy_warehouse", market="EN")
    assert "(, )" not in wh_out
    assert "by policy year (, )" not in wh_out
    assert "by historical policy period" in wh_out

    # 17. Background vacated chancery office
    raw_off = "Diocesan office with stacked moving boxes marked 'Records', a framed diocesan coat of arms"
    off_out = _sanitize_background_prompt(raw_off, bg_key="bg_vacated_chancery_office", market="EN")
    assert "boxes marked," not in off_out
    assert "sealed with tape, a framed" in off_out


def test_opus_astra_round4_rc1_rc2_remediations():
    """Rule 134: Test Round 4 Root Causes (RC1 Category-aware negatives & RC2 Role/Background Anchors)."""
    # RC1.1: Data visualizations/charts must EXEMPT 'no charts' and 'no chart values' from negative prompt
    chart_keys = [
        ("fg_evidence_ballot_tabulation", "Tabulation of ballots showing rejection"),
        ("fg_evidence_claims_decade_histogram", "Histogram of abuse claims by decade"),
        ("fg_evidence_trust_offer_bar_chart", "Bar chart comparing trust settlement offers"),
        ("fg_evidence_priority_waterfall", "Priority waterfall chart of bankruptcy payouts")
    ]
    for key, desc in chart_keys:
        out = _sanitize_foreground_prompt(desc, fg_key=key, market="EN")
        neg_prompt = out.split("[STRICT NEGATIVE PROMPT]")[1]
        assert "no charts" not in neg_prompt, f"Failed for {key}: 'no charts' found in negative prompt"
        assert "no chart values" not in neg_prompt, f"Failed for {key}: 'no chart values' found in negative prompt"
        assert "no human body" in neg_prompt
        assert "#FF00FF" in out

    # Non-chart objects DO contain 'no charts' in negative prompt
    doc_out = _sanitize_foreground_prompt("Insurance policy binder on table", fg_key="fg_evidence_liability_policies", market="EN")
    assert "no charts" in doc_out.split("[STRICT NEGATIVE PROMPT]")[1]

    # RC1.2: Backgrounds must NEVER receive document hygiene suffixes
    bg_raw = "Sacramento committee hearing room, unfilled template with official border, blank amount fields, empty ruled lines"
    bg_out = _sanitize_background_prompt(bg_raw, bg_key="bg_hearing_room", market="EN")
    assert "unfilled template" not in bg_out
    assert "blank amount fields" not in bg_out
    assert "empty ruled lines" not in bg_out
    assert "16:9" in bg_out

    # RC2.1: Legal counsel role anchors (no 180-degree role inversions)
    debtor_counsel_out = _sanitize_foreground_prompt(
        "Debtor's restructuring counsel presenting reorganization documents",
        fg_key="fg_character_debtor_counsel", market="EN"
    )
    assert "reorganization debtor defense counsel" in debtor_counsel_out
    assert "plaintiffs' legal counsel" not in debtor_counsel_out

    carrier_counsel_out = _sanitize_foreground_prompt(
        "Insurance carrier defense counsel reviewing coverage reservations",
        fg_key="fg_character_insurance_carrier_counsel", market="EN"
    )
    assert "insurance carrier defense litigator" in carrier_counsel_out
    assert "plaintiffs' legal counsel" not in carrier_counsel_out

    # RC2.2: Creditors' committee counsel must NOT receive claimant invariant
    comm_counsel_out = _sanitize_foreground_prompt(
        "Creditors' committee counsel advocating on behalf of survivor claimants",
        fg_key="fg_character_creditors_committee_counsel", market="EN"
    )
    assert "creditors' committee counsel" in comm_counsel_out
    assert "Subject exhibiting dignified restraint, steady solemn gaze, holding personal record" not in comm_counsel_out
    assert "Subject actively manipulating physical documentary prop" in comm_counsel_out

    # RC2.3: Court fee examiner and investigative journalist anchors
    fee_out = _sanitize_foreground_prompt("Court fee examiner auditing billing entries", fg_key="fg_character_fee_examiner", market="EN")
    assert "court fee examiner or forensic billing auditor" in fee_out

    journo_out = _sanitize_foreground_prompt("Investigative journalist reviewing PACER filings", fg_key="fg_character_investigative_journalist", market="EN")
    assert "investigative journalist or court reporter" in journo_out

    # RC2.4: State legislator 2019 era anchor
    legis_out = _sanitize_foreground_prompt("State legislator presenting assembly bill", fg_key="fg_character_state_legislator_2019", market="EN")
    assert "legislative assembly era" in legis_out

    # RC2.5: Background environment anchors (no category bleed)
    street_out = _sanitize_background_prompt("Street outside parish exterior in 1970", bg_key="bg_1970s_oakland_streetscape", market="EN")
    assert "1970s municipal streetscape" in street_out
    assert "cathedral facade with glass-and-timber structure" not in street_out

    map_out = _sanitize_background_prompt("Dioceses territorial boundary overview", bg_key="bg_california_dioceses_map", market="EN")
    assert "archival geographic map chart" in map_out
    assert "rectory corridor" not in map_out

    ledger_out = _sanitize_background_prompt("Detailed audit records grid", bg_key="bg_chancery_accounting_office", market="EN")
    assert "accounting office interior" in ledger_out
    assert "corporate or government headquarters" not in ledger_out

    court_out = _sanitize_background_prompt("Historic county courthouse exterior stonework", bg_key="bg_alameda_superior_courthouse", market="EN")
    assert "Art Deco county courthouse" in court_out
    assert "modern federal office tower and glass rotunda" not in court_out

    war_out = _sanitize_background_prompt("Legal war room with conference table", bg_key="bg_restructuring_war_room", market="EN")
    assert "corporate legal conference war room interior" in war_out

    capitol_out = _sanitize_background_prompt("State assembly chamber interior", bg_key="bg_sacramento_capitol_assembly_2019", market="EN")
    assert "legislative assembly chamber interior" in capitol_out

    med_out = _sanitize_background_prompt("Settlement negotiation chamber", bg_key="bg_settlement_mediation_chamber", market="EN")
    assert "settlement mediation suite interior" in med_out

    # RC2.6: Landmark glyphs
    flag_out = _sanitize_background_prompt("Room with California bear flag on wall", bg_key="bg_office", market="EN")
    assert "bear-and-star silhouette without typography" in flag_out

    tower_out = _sanitize_background_prompt("Oakland skyline featuring Tribune Tower", bg_key="bg_skyline", market="EN")
    assert "clock tower with numeral-free clock face" in tower_out


def test_opus_astra_round5_round16_remediations():
    """Rule 122 & Rule 128: Test Round 16 Splitter, Chroma Negative, and Positive Channel Hygiene."""
    from scripts.reforge_oakland_assets_clean import CLEAN_RAW_FGS, CLEAN_RAW_BGS
    from app.services.prompt_forge import split_prompt_channels

    # 1. Evidence positive prompts must NEVER contain text words or seal-bait relics
    for fg_k, raw_p in CLEAN_RAW_FGS.items():
        sanitized = _sanitize_foreground_prompt(raw_p, fg_key=fg_k, market="EN")
        split_dict = split_prompt_channels(sanitized, default_layout="center")
        pos_p = split_dict["positive_prompt"]
        neg_p = split_dict["negative_prompt"]

        # Check positive channel for banned text terms
        assert "seal impression crest" not in pos_p, f"Failed for {fg_k}: 'seal impression crest' in positive"
        assert "with or digits" not in pos_p, f"Failed for {fg_k}: 'with or digits' in positive"
        assert "or digits" not in pos_p, f"Failed for {fg_k}: 'or digits' in positive"
        assert "or lettering" not in pos_p, f"Failed for {fg_k}: 'or lettering' in positive"

        # Check negative channel for chroma collisions on #FF00FF cutouts
        assert "magenta" not in neg_p.lower(), f"Failed for {fg_k}: 'magenta' in negative channel"
        assert "pink" not in neg_p.lower(), f"Failed for {fg_k}: 'pink' in negative channel"
        assert "fuchsia" not in neg_p.lower(), f"Failed for {fg_k}: 'fuchsia' in negative channel"
        assert "or neon pink" not in neg_p.lower(), f"Failed for {fg_k}: 'or neon pink' in negative channel"

    # 2. Background positive prompts must NOT collide with negative subtitle/overlay terms
    for bg_k, raw_bg in CLEAN_RAW_BGS.items():
        sanitized_bg = _sanitize_background_prompt(raw_bg, bg_key=bg_k, market="EN")
        split_bg = split_prompt_channels(sanitized_bg, default_layout="subject-left")
        pos_bg = split_bg["positive_prompt"]

        assert "safe-zone for subtitles" not in pos_bg, f"Failed for {bg_k}: 'safe-zone for subtitles' in positive"
        assert "for graphical overlays" not in pos_bg, f"Failed for {bg_k}: 'for graphical overlays' in positive"
        assert "for overlay" not in pos_bg, f"Failed for {bg_k}: 'for overlay' in positive"

    # 3. Specific asset checks (Round 18/21 audit refinements)
    val_p = CLEAN_RAW_FGS["fg_evidence_valuation_comparison"]
    assert "tiny fraction" in val_p

    ballot_p = CLEAN_RAW_FGS["fg_evidence_ballot_tabulation"]
    assert "overwhelming dark vermilion segment" in ballot_p
    assert "stamp" not in ballot_p


def test_zero_affirmative_text_leakage_and_contradiction():
    """Verify that R137 closing directive does not leak into affirmative text and no positive/negative contradictions occur."""
    from app.services.prompt_forge import split_prompt_channels, R137_CLOSING_DIRECTIVE

    raw = (
        "Waist-up character holding pastoral letter folio and envelope seal, "
        "[STRICT NEGATIVE PROMPT] no seal, no stamp, no borders. " + R137_CLOSING_DIRECTIVE
    )
    res = split_prompt_channels(raw, default_layout="subject-right at xPct: 65")

    # Positive must not contain functional text-magnet nouns or contradicted terms
    assert "pastoral letter folio" not in res["positive_prompt"]
    assert "bound plain folio" in res["positive_prompt"]
    assert "envelope seal" not in res["positive_prompt"]
    assert "The image contains" not in res["positive_prompt"]

    # Negative must not contain leaked affirmative sentence
    assert "The image contains writing or readable digits" not in res["negative_prompt"]
    assert "The image contains" not in res["prompt"]

    # Full prompt must not contain naked affirmative sentence in exclusions
    assert "Strictly" in res["prompt"]
    assert "The image contains writing" not in res["prompt"]


def test_opus_astra_round2_directives_sanitization():
    """Verify that header tags, stutters, prop corruptions, and chroma shadows are properly sanitized."""
    from app.services.prompt_forge import split_prompt_channels

    raw = (
        "[STYLE MANDATE] 2D stylized graphic novel digital illustration, "
        "Subject holding a bound bound plain folio and fingers pressed against the embossed insignia on pure #FF00FF cutout. "
        "[ACTION & GAZE INVARIANT] directional gaze. "
        "[STRICT NEGATIVE PROMPT] no seal, no stamp, photograph. , "
    )
    res = split_prompt_channels(raw, default_layout="subject-right at xPct: 75")

    # Header tags stripped from positive
    assert "[STYLE MANDATE]" not in res["positive_prompt"]
    assert "[ACTION & GAZE INVARIANT]" not in res["positive_prompt"]

    # Word stutter fixed
    assert "bound bound" not in res["positive_prompt"]

    # Contradicted embossed insignia resolved to envelope
    assert "embossed insignia" not in res["positive_prompt"]
    assert "envelope" in res["positive_prompt"]

    # Chroma negatives hardened with shadow exclusions
    neg = res["negative_prompt"]
    assert "background gradients" in neg
    assert "drop shadow" in neg
    assert "cast shadow" in neg
    assert "floor shadow" in neg
    assert ". ," not in neg

    # Map test: verify aerial/cartographic does not contain floor plane
    map_raw = "Aerial cartographic map exhibit of Alameda County parcels with dark floor band."
    map_res = split_prompt_channels(map_raw)
    assert "floor plane" not in map_res["positive_prompt"]


def test_opus_astra_round3_orphan_syntax_and_layout_dedup():
    """Verify that orphan syntax (with ., displaying and) and redundant layout phrases are cleansed."""
    from app.services.prompt_forge import harmonize_prompt_clauses

    raw_fg = "Geometric chart with clean proportional data graphics with . Creditors counsel displaying and abstract line marks only."
    cleaned_fg = harmonize_prompt_clauses(raw_fg)
    assert "with ." not in cleaned_fg
    assert "displaying and" not in cleaned_fg
    assert "displaying" in cleaned_fg

    raw_bg = "16:9 widescreen editorial illustration, stylized graphic novel background, clean low-contrast dark floor band, open right space for balance. Courtroom facade on the left; open quiet space in the right third for composition balance, 16:9 aspect ratio, clean low-contrast subdued foreground floor plane across the lower horizontal edge, open quiet space in the right third for composition balance Authentic federal courtroom"
    cleaned_bg = harmonize_prompt_clauses(raw_bg)
    assert "16:9 aspect ratio" not in cleaned_bg
    assert ". Authentic" in cleaned_bg







