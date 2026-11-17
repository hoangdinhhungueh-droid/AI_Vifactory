#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_prompt_engine_systemic_invariants.py
Systemic Invariant Verification Suite for Vox Prompt Engine across ALL Markets (KR, JP, VN, EN).
"""

import pytest
from app.services.kinetic_sub_director import (
    build_cl3_paper_diorama_image_prompt,
    build_cl3_paper_diorama_prompt,
    generate_scene_sub_director_plan,
)

MARKETS = ["KR", "JP", "VN", "EN"]
TEST_SENTENCES = {
    "KR": "전세사기 피해자 대책위원회가 국토교통부에 긴급 실태조사를 요구했습니다.",
    "JP": "被害対策委員会が国土交通省に緊急実態調査を要請しました。",
    "VN": "Ban chỉ đạo điều tra yêu cầu phong tỏa khẩn cấp tài sản của tập đoàn.",
    "EN": "The investigative committee demands an emergency audit into the asset freeze.",
}

# --- TEST 1: LENGTH BUDGET INVARIANT ---
@pytest.mark.parametrize("mkt", MARKETS)
def test_image_prompt_length_budget_invariant(mkt):
    prompt = build_cl3_paper_diorama_image_prompt(TEST_SENTENCES[mkt], market=mkt, scene_id="SCENE_01")
    char_len = len(prompt)
    word_len = len(prompt.split())
    # Bắt buộc tinh gọn: Tối thiểu 300 chars, TỐI ĐA 1,200 chars (khoảng 50-170 từ)
    assert 300 <= char_len <= 1200, f"[{mkt}] image_prompt bloated or too short: {char_len} chars"
    assert 50 <= word_len <= 170, f"[{mkt}] image_prompt word count out of bounds: {word_len} words"


# --- TEST 2: ZERO DESIGN JARGON LEAK INVARIANT ---
FORBIDDEN_JARGON = [
    "IBM Plex Mono",
    "Swiss extreme scale contrast",
    "7% opacity",
    "+8px offset",
    "6x12 chip",
    "grease pencil",
    "Observation 0",
    "Archive Ref:",
]

@pytest.mark.parametrize("mkt", MARKETS)
@pytest.mark.parametrize("jargon", FORBIDDEN_JARGON)
def test_zero_design_jargon_leak_invariant(mkt, jargon):
    img_prompt = build_cl3_paper_diorama_image_prompt(TEST_SENTENCES[mkt], market=mkt, scene_id="SCENE_01")
    assert jargon.lower() not in img_prompt.lower(), f"[{mkt}] Leak detected: '{jargon}' found in image_prompt"


# --- TEST 3: MULTI-MARKET SCRIPT & DEMOGRAPHIC GROUNDING INVARIANT ---
def test_korean_market_grounding_invariant():
    prompt = build_cl3_paper_diorama_image_prompt(
        TEST_SENTENCES["KR"],
        market="KR",
        scene_id="SCENE_13",
        hero_object_override="portrait of an investigative victim"
    )
    assert "Korean Hangul" in prompt
    assert "East Asian South Korean" in prompt
    assert "zero Caucasian" in prompt
    assert "NO English text" in prompt


def test_japanese_market_grounding_invariant():
    prompt = build_cl3_paper_diorama_image_prompt(
        TEST_SENTENCES["JP"],
        market="JP",
        scene_id="SCENE_02",
        hero_object_override="portrait of a forensic auditor"
    )
    assert "Japanese kanji" in prompt
    assert "East Asian Japanese" in prompt
    assert "zero Caucasian" in prompt


def test_vietnamese_market_grounding_invariant():
    prompt = build_cl3_paper_diorama_image_prompt(
        TEST_SENTENCES["VN"],
        market="VN",
        scene_id="SCENE_03",
        hero_object_override="portrait of an economic investigator"
    )
    assert "Vietnamese" in prompt
    assert "zero Western portraits" in prompt


# --- TEST 4: QUANTITATIVE METRIC SEED STATE INVARIANT ---
def test_quantitative_metric_clean_cutout():
    prompt = build_cl3_paper_diorama_image_prompt(
        "피해액이 3,000억 원에 달합니다.",
        market="KR",
        scene_id="SCENE_04",
        extracted_metric="3,000억 원"
    )
    assert "3,000억 원" in prompt
    assert "IBM Plex Mono" not in prompt
    assert "Swiss extreme" not in prompt
    assert "ZERO interactive tools drawn on seed" in prompt


# --- TEST 5: S05 DIRECTOR PLAN CONTRACT INTEGRITY ---
def test_s05_director_plan_schema_and_prompt_fields():
    from stages.s05_director_plan import build_vox_scene_prompts
    from core.contracts.stages import Scene

    dummy_scene = Scene(
        scene_id="SCENE_01",
        narration="전세사기 피해자 대책위원회가 국토교통부에 긴급 조사를 요청했습니다.",
        headline="긴급 실태조사",
        market="KR"
    )
    res = build_vox_scene_prompts(
        scene=dummy_scene,
        idx=0,
        total_scenes=1,
        camera_directive="STATIC_OVERHEAD",
        market="KR"
    )
    assert "image_prompt" in res
    assert "bg_prompt" in res
    assert len(res["image_prompt"]) <= 1200
    assert len(res["bg_prompt"]) < 300
    assert res["bg_prompt"] != res["image_prompt"]
    assert "IBM Plex Mono" not in res["image_prompt"]
    assert "7% opacity" not in res["image_prompt"]

    # Zero Bare Hex Codes Invariant (Rule 140 / Anti-Hallucination)
    import re
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', res["bg_prompt"])
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', res["image_prompt"])


# --- TEST 6: I2V VIDEO PROMPT ZERO JARGON INVARIANT ---
@pytest.mark.parametrize("mkt", MARKETS)
@pytest.mark.parametrize("jargon", FORBIDDEN_JARGON)
def test_i2v_zero_design_jargon_leak_invariant(mkt, jargon):
    sub_plan = {
        "sentence": TEST_SENTENCES[mkt],
        "market": mkt,
        "scene_id": "SCENE_01",
        "camera_directive": "STATIC_OVERHEAD"
    }
    i2v_prompt = build_cl3_paper_diorama_prompt(sub_plan, market=mkt, style_mode="deep_diorama")
    assert jargon.lower() not in i2v_prompt.lower(), f"[{mkt}] Leak detected in I2V: '{jargon}' found in prompt"


# --- TEST 7: NON-CANONICAL MARKET FALLBACK INVARIANT ---
@pytest.mark.parametrize("unsupported_mkt", ["TH", "ZH", "DE", "FR"])
def test_non_canonical_market_fallback_invariant(unsupported_mkt):
    # Must NOT crash with unhandled ValueError; should safely fall back to EN archival
    prompt = build_cl3_paper_diorama_image_prompt(
        "Non-canonical market narrative test.",
        market=unsupported_mkt,
        scene_id="SCENE_01"
    )
    assert 300 <= len(prompt) <= 1200
    assert "archival" in prompt
    assert "Strictly NO placeholder words" in prompt

    i2v = build_cl3_paper_diorama_prompt(
        {"sentence": "Non-canonical I2V test."},
        market=unsupported_mkt,
        style_mode="deep_diorama"
    )
    assert "deep_diorama" in i2v.lower() or "diorama" in i2v.lower()


# --- TEST 8: DEMOGRAPHIC ANCHOR IN MIXED HERO STRING ---
def test_demographic_anchor_in_mixed_hero_string():
    prompt = build_cl3_paper_diorama_image_prompt(
        TEST_SENTENCES["KR"],
        market="KR",
        scene_id="SCENE_05",
        hero_object_override="forensic auditor inspecting accounting ledger"
    )
    assert "East Asian South Korean" in prompt
    assert "zero Caucasian" in prompt


# --- TEST 9: GEMINI BROWSER GEN PROMPTS FORGE SYNC INTEGRITY ---
def test_gemini_browser_gen_prompts_forge_sync_integrity(tmp_path, monkeypatch):
    from pathlib import Path
    import json
    import scripts.gemini_browser_gen as gbg

    test_ep_id = "TEST_INTEGRITY_EP"
    ep_dir = tmp_path / "episodes" / test_ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)

    dp_data = {
        "scenes": [{
            "scene_id": "SCENE_01",
            "image_prompt": "Authentic Vox tactile paper-collage diorama with hero auditor",
            "bg_prompt": "Background: cool backlit table."
        }]
    }
    pf_data = {
        "backgrounds": {"SCENE_01": "Background: cool backlit table."},
        "vox_collages": {"SCENE_01": "Authentic Vox tactile paper-collage diorama with hero auditor"}
    }
    with open(ep_dir / "director_plan.json", "w", encoding="utf-8") as f:
        json.dump(dp_data, f)
    with open(ep_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
        json.dump(pf_data, f)

    monkeypatch.setattr(gbg, "ROOT_DIR", tmp_path)

    items = gbg.fetch_prompts_from_vps(test_ep_id)
    assert len(items) == 1
    # MUST retain the full diorama prompt, NOT the background prompt
    assert "Authentic Vox tactile" in items[0]["prompt"]
    assert items[0]["prompt"].startswith("Authentic Vox")

    # director_plan.json image_prompt must NOT be corrupted into background
    with open(ep_dir / "director_plan.json", "r", encoding="utf-8") as f:
        saved_dp = json.load(f)
    assert saved_dp["scenes"][0]["image_prompt"] == "Authentic Vox tactile paper-collage diorama with hero auditor"
