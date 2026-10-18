#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_b2_b3_handoff.py — Zero-Mock Adversarial Verification Suite (Boss Plan TASK_1792304389).

Rigorous test cases (A1 to A13) enforcing:
1. Verbatim B2->B3 context preservation.
2. Complete purge of mock default_beats (Canary & Static Gate).
3. Fail-closed contract invariants (B2ContractError).
4. Full CJK Japanese quote & currency preservation.
"""

import json
import re
from pathlib import Path

import pytest

from core.contracts.b2_b3_contract import (
    B2ContractError,
    load_spoken_script,
    segment_ja,
)

CANARY_MOCK_STRINGS = [
    "In late 2026, an unprecedented regulatory decision",
    "permanently overturned the status quo",
    "THE SHOCK VERDICT",
    "A monumental legal document torn cleanly across jurisdictional borders",
    "THE FALSE FRONT",
    "Two asymmetrical scale weights demonstrating 100x structural disparity",
    "65% OFFSHORE DRAIN",
    "THE LEGAL VACUUM",
    "THE LIVING WARNING",
]


def _find_test_episode_dir():
    candidates = [
        Path("/var/vf/episodes/JP_EP0002_us_deficit_refunds"),
        Path("/root/video_factory/episodes/JP_EP0002_us_deficit_refunds"),
        Path(__file__).resolve().parent.parent / "episodes" / "JP_EP0002_us_deficit_refunds",
        Path("episodes/JP_EP0002_us_deficit_refunds")
    ]
    for c in candidates:
        if c.exists() and ((c / "spoken_script.txt").exists() or (c / "spoken_sentences.json").exists()):
            return c
    return None


def test_a1_real_b2_reaches_b3_verbatim():
    """A1: Real B2 artifact loads verbatim without loss or distortion."""
    ep_dir = _find_test_episode_dir()
    if not ep_dir:
        pytest.skip("JP_EP0002_us_deficit_refunds episode not found")

    spoken = load_spoken_script(ep_dir, market="JA")
    assert spoken.total_beats > 0
    assert len(spoken.beats) == spoken.total_beats
    assert "JP_EP0002_us_deficit_refunds" in spoken.episode_id
    assert len(spoken.source_sha256) == 64

    # First beat must be the authentic Japanese text
    assert "2024" in spoken.beats[0].text or "米財務省" in spoken.beats[0].text
    for b in spoken.beats:
        assert b.text.strip(), f"Beat {b.beat_id} has empty text!"
        assert len(b.text_sha1) == 40


def test_a2_default_beats_canary(tmp_path):
    """A2: Canary strings from the 5 old mock beats NEVER appear in load output."""
    ep_dir = _find_test_episode_dir()
    if ep_dir:
        spoken = load_spoken_script(ep_dir, market="JA")
        all_text = " ".join([b.text for b in spoken.beats])
        for canary in CANARY_MOCK_STRINGS:
            assert canary.lower() not in all_text.lower(), f"Canary leak detected: '{canary}' found in output!"


def test_a3_missing_b2_raises_contract_error(tmp_path):
    """A3: Missing B2 must raise B2ContractError (Rule 118 Zero-Mock)."""
    empty_ep = tmp_path / "TEST_EP_EMPTY"
    empty_ep.mkdir()

    with pytest.raises(B2ContractError) as exc_info:
        load_spoken_script(empty_ep, market="JA")
    assert "Zero-Mock Violation" in str(exc_info.value)


def test_a4_whitespace_b2_raises_contract_error(tmp_path):
    """A4: Empty or whitespace-only B2 must raise B2ContractError."""
    ws_ep = tmp_path / "TEST_EP_WHITESPACE"
    ws_ep.mkdir()
    (ws_ep / "spoken_script.txt").write_text("   \n\n\t  \n", encoding="utf-8")

    with pytest.raises(B2ContractError) as exc_info:
        load_spoken_script(ws_ep, market="JA")
    assert "Zero-Mock Violation" in str(exc_info.value)


def test_a5_fenced_json_b2_parses_correctly(tmp_path):
    """A5: Markdown fenced JSON is sanitized and parsed without error."""
    fence_ep = tmp_path / "TEST_EP_FENCED"
    fence_ep.mkdir()
    fenced_payload = """```json
[
  {"sentence_id": "sent_01", "beat_index": 1, "text": "第1文です。"},
  {"sentence_id": "sent_02", "beat_index": 2, "text": "第2文です。"}
]
```"""
    (fence_ep / "spoken_sentences.json").write_text(fenced_payload, encoding="utf-8")

    spoken = load_spoken_script(fence_ep, market="JA")
    assert spoken.total_beats == 2
    assert spoken.beats[0].text == "第1文です。"
    assert spoken.beats[1].text == "第2文です。"


def test_a6_japanese_segmentation_quote_and_currency_integrity():
    """A6: Japanese segmentation preserves quotes 「」 and currency terms 兆ドル/$."""
    sample = (
        "2024年10月18日、米財務省は「連邦赤字は1.83兆ドル（約280兆円）に達した。」と発表しました！"
        "果たして国債利回り4.5%の壁を越えられるのか？"
    )
    segmented = segment_ja(sample)
    assert len(segmented) == 2
    # The full quote 「...」 containing a period 。 must NOT be split in half
    # NFKC normalizes full-width parens and exclamation marks
    assert "「連邦赤字は1.83兆ドル(約280兆円)に達した。」と発表しました!" in segmented[0]
    assert "4.5%" in segmented[1]


def test_a7_static_scan_zero_default_beats_in_production():
    """A7: Static gate ensuring default_beats does not exist anywhere outside tests."""
    repo_root = Path(__file__).resolve().parent.parent
    target_dirs = ["stages", "app", "core", "orchestrator", "vox"]

    violations = []
    for d_name in target_dirs:
        d_path = repo_root / d_name
        if not d_path.exists():
            continue
        for py_file in d_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matches = re.findall(r"\bdefault_beats\b", content)
            if matches:
                violations.append(f"{py_file}: found {len(matches)} occurrences of 'default_beats'")

    assert not violations, "Production code contains default_beats! Violations:\n" + "\n".join(violations)


def test_a8_director_plan_spatial_decomposition_and_kinematics(tmp_path):
    """A8: Verifies that director_plan exports decomposed objects, kinematic actions, and Omni/Flow I2V prompts."""
    from app.services.unified_vox_director import build_unified_director_plan

    test_ep = tmp_path / "JP_EP9999_clinic_insolvency"
    test_ep.mkdir()

    spoken = [
        {"text": "2026年1月から9月、医療機関の倒産は59件に達しました。", "duration_sec": 4.5, "beat_index": 1},
        {"text": "診療所が消える背景には、公定価格と2か月の入金遅延があります。", "duration_sec": 5.0, "beat_index": 2},
    ]

    result = build_unified_director_plan(spoken, test_ep, style_preset="vox_forensic_paper")
    scenes = result.get("scenes", [])
    assert len(scenes) == 2

    for sc in scenes:
        # 1. Physical Object Decomposition
        objs = sc.get("objects", [])
        assert len(objs) >= 2, f"Scene {sc.get('scene_id')} must have at least 2 decomposed objects"
        hero_obj = objs[0]
        assert hero_obj.get("role") == "primary"
        assert any("deckle" in attr for attr in hero_obj.get("attributes", []))
        assert any("drop shadow" in attr for attr in hero_obj.get("attributes", []))

        # 2. Kinematic Actions
        acts = sc.get("actions", [])
        assert len(acts) >= 1, f"Scene {sc.get('scene_id')} must have kinematics actions"
        assert acts[0].get("subject")
        assert acts[0].get("verb")
        assert acts[0].get("motion")

        # 3. Omni & Google Flow Prompts
        assert sc.get("i2v_prompt_omni"), f"Scene {sc.get('scene_id')} missing i2v_prompt_omni"
        assert sc.get("i2v_prompt_google_flow"), f"Scene {sc.get('scene_id')} missing i2v_prompt_google_flow"
        omni_prompt_low = sc["i2v_prompt_omni"].lower()
        assert "paper" in omni_prompt_low and "cutout" in omni_prompt_low

        # 4. Strict Zero-JGB Finance Lexicon Negative Assertion across all scene fields (Boss Item 3)
        finance_blacklist = ["jgb", "国債", "日銀", "boj", "利回り", "sovereign bond", "yield curve", "ktb"]
        sc_dump = f"{sc.get('headline', '')} {sc.get('scene_title', '')} {sc.get('visual_metaphor', '')} {sc.get('i2v_prompt_omni', '')} {json.dumps(objs)}".lower()
        for bad_tok in finance_blacklist:
            assert bad_tok not in sc_dump, f"Forbidden finance/JGB token '{bad_tok}' leaked into healthcare scene: {sc.get('scene_id')}"


def test_a9_healthcare_roster_zero_jgb_bonds_leak():
    """A9: Verifies topic-anchored healthcare roster contains clinical assets and 0 JGB bond leaks (Rule 128 & Boss Item 3)."""
    from app.services.unified_vox_director import generate_topic_anchored_roster

    topic = "医療機関 倒産 過去最多59件"
    claims = [
        "Tokyo Shoko Research recorded 59 medical institution bankruptcies nationwide.",
        "Straight liquidation accounted for over 97% of clinic failures.",
        "Reimbursement payments from the Social Insurance Fund take 2 months.",
    ]
    bgs, fgs = generate_topic_anchored_roster(topic, "JP", ["59件"], claims)

    # Must contain authentic clinical assets
    assert "bg_clinic_waiting_room" in bgs or "bg_clinic_director_examination_room" in bgs
    assert any("clinic" in k or "receipt" in k or "medical" in k or "doctor" in k for k in fgs)

    # Schema consistency: all entries must have required keys (Boss Item 2)
    for bg_k, bg_v in bgs.items():
        assert "title" in bg_v and bg_v["title"], f"{bg_k} missing title"
        assert "description" in bg_v and bg_v["description"], f"{bg_k} missing description"
        assert "beats" in bg_v, f"{bg_k} missing beats"

    # Must have 0 JGB sovereign debt leaks across keys and descriptions
    finance_blacklist = ["jgb", "国債", "日銀", "boj", "利回り", "sovereign bond", "yield curve", "ktb"]
    for bg_key, bg_val in bgs.items():
        bg_dump = f"{bg_key} {bg_val.get('title', '')} {bg_val.get('description', '')}".lower()
        for bad_tok in finance_blacklist:
            assert bad_tok not in bg_dump, f"Leak detected: '{bad_tok}' in {bg_key}"
    for fg_key, fg_val in fgs.items():
        fg_dump = f"{fg_key} {fg_val.get('title', '')} {fg_val.get('description', '')}".lower()
        for bad_tok in finance_blacklist:
            assert bad_tok not in fg_dump, f"Leak detected: '{bad_tok}' in {fg_key}"


def test_a10_domain_taxonomy_robust_matching_and_negative_case():
    """A10: Verifies CJK unsegmented text, underscore slugs, plurals, and negative non-healthcare case (Boss Item 1)."""
    from app.services.unified_vox_director import generate_topic_anchored_roster

    # 1. Unsegmented Japanese narration
    unsegmented_jp = "医療機関の倒産が過去最多となり、地域診療所が次々と閉鎖されている"
    bgs_jp, fgs_jp = generate_topic_anchored_roster(unsegmented_jp, "JP", [], [])
    assert "bg_clinic_waiting_room" in bgs_jp, "Unsegmented JP text failed to activate healthcare roster"

    # 2. Underscore-delimited slug
    slug_topic = "jp_ep9999_clinic_insolvency_liquidation"
    bgs_slug, fgs_slug = generate_topic_anchored_roster(slug_topic, "JP", [], [])
    assert "bg_clinic_waiting_room" in bgs_slug, "Underscore slug failed to activate healthcare roster"

    # 3. English plurals and derivatives
    plural_topic = "Hospitals, clinics, and pharmaceutical wholesalers face catastrophic liquidity shortfalls"
    bgs_en, fgs_en = generate_topic_anchored_roster(plural_topic, "EN", [], [])
    assert "bg_clinic_waiting_room" in bgs_en, "English plurals failed to activate healthcare roster"

    # 4. Negative non-healthcare case (BOJ sovereign bond policy) -> MUST NOT trigger healthcare roster
    finance_topic = "BOJ raises interest rates on Japanese Government Bonds as JGB yields surge"
    bgs_fin, fgs_fin = generate_topic_anchored_roster(finance_topic, "JP", ["1.5%"], ["BOJ adjusts yield curve"])
    assert "bg_clinic_waiting_room" not in bgs_fin, "Negative case falsely activated healthcare roster"
    assert "bg_boj_market_operations_floor" in bgs_fin or "bg_jgb_syndicate_auction_hall" in bgs_fin, "Finance case failed to select JGB/BOJ roster"


def test_a11_taxonomy_loader_fail_closed_on_missing_or_corrupt_file(tmp_path, monkeypatch):
    """A11: Verifies that visual taxonomy loader fails closed on missing or corrupt files (Boss Round 2 Item 6)."""
    import json
    import pytest
    from app.services import unified_vox_director

    # Reset cache
    monkeypatch.setattr(unified_vox_director, "_TAXONOMY_CACHE", None)

    # 1. Missing file -> raises FileNotFoundError
    non_existent = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(unified_vox_director, "ROOT_DIR", tmp_path)
    with pytest.raises(FileNotFoundError) as exc_info:
        unified_vox_director._load_visual_taxonomy()
    assert "Critical SoT failure" in str(exc_info.value)

    # 2. Corrupt file -> raises json.decoder.JSONDecodeError or ValueError
    tax_dir = tmp_path / "config" / "taxonomies"
    tax_dir.mkdir(parents=True, exist_ok=True)
    corrupt_file = tax_dir / "visual_rosters.json"
    corrupt_file.write_text("{invalid_json: true,", encoding="utf-8")
    monkeypatch.setattr(unified_vox_director, "_TAXONOMY_CACHE", None)
    with pytest.raises(Exception):
        unified_vox_director._load_visual_taxonomy()

    # Reset cache
    monkeypatch.setattr(unified_vox_director, "_TAXONOMY_CACHE", None)


def test_a12_taxonomy_schema_integrity():
    """A12: Verifies that all visual taxonomy entries conform to required schema keys (Boss Round 2 Item 6)."""
    from app.services.unified_vox_director import _load_visual_taxonomy
    tax = _load_visual_taxonomy()
    assert "domains" in tax, "Taxonomy missing 'domains' root key"
    domains = tax["domains"]
    assert "healthcare" in domains, "Taxonomy missing 'healthcare' domain"
    hc = domains["healthcare"]
    assert "keywords_cjk" in hc, "Healthcare domain missing 'keywords_cjk'"
    assert "keywords_en_regex" in hc, "Healthcare domain missing 'keywords_en_regex'"
    assert "negative_finance_tokens" in hc, "Healthcare domain missing 'negative_finance_tokens'"
    assert "markets" in hc and "JP" in hc["markets"], "Healthcare missing JP market"

    jp_market = hc["markets"]["JP"]
    assert "bg_roster" in jp_market, "JP market missing 'bg_roster'"
    assert "fg_roster" in jp_market, "JP market missing 'fg_roster'"

    req_bg_keys = {"title", "description", "beats"}
    for bg_key, bg_val in jp_market["bg_roster"].items():
        missing = req_bg_keys - set(bg_val.keys())
        assert not missing, f"Healthcare background {bg_key} missing required keys: {missing}"
        assert len(bg_val["description"].strip()) > 10, f"Healthcare background {bg_key} has empty/short description"

    req_fg_keys = {"title", "description", "role", "type", "keywords"}
    for fg_key, fg_val in jp_market["fg_roster"].items():
        missing = req_fg_keys - set(fg_val.keys())
        assert not missing, f"Healthcare foreground {fg_key} missing required keys: {missing}"



