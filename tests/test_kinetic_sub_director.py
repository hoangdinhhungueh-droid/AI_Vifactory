#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_kinetic_sub_director.py — Unit Tests for Object-to-Object Kinetic Coupling Engine.

Enforces:
- Rule 121: Strict Verification Protocol.
- Rule 127: Runtime Programmatic Verification.
- Rule 128: Generic Contract Pattern (tested across VN, JA, EN, KR).
- Rule 140 v3: Kinetic Coupling Taxonomy & Causal Compound Verb Prompts.
"""

import pytest
from app.services.kinetic_sub_director import (
    KineticFamily,
    SemanticClauseMapper,
    generate_scene_sub_director_plan,
    build_kinetic_causal_i2v_prompt
)


def test_semantic_clause_mapper_multilingual_beat_count():
    """Kiểm tra tính toán số beat linh hoạt (4..7) theo độ phức tạp của câu thoại."""
    # 1. Câu đơn giản (VN) -> 4..5 beats
    vn_simple = "Hồ sơ lưu trữ này đã bị niêm phong suốt hai mươi năm qua."
    assert SemanticClauseMapper.calculate_beat_count(vn_simple) in (4, 5)

    # 2. Câu phức hợp có liên từ đối lập và con số (VN) -> 6..7 beats
    vn_complex = "Năm 2024, công ty chi 4 tỷ đồng cho an ninh mạng, nhưng chỉ 2% bảo vệ được cơ sở dữ liệu."
    assert SemanticClauseMapper.calculate_beat_count(vn_complex) in (6, 7)

    # 3. Câu phức hợp (JA) -> 6..7 beats
    ja_complex = "基準となる測量データが最初から欠落しており、しかし被害額は10倍に急増した。"
    assert SemanticClauseMapper.calculate_beat_count(ja_complex) in (6, 7)

    # 4. Câu đơn giản (EN) -> 4..5 beats
    en_simple = "The confidential archive remained sealed inside the vault."
    assert SemanticClauseMapper.calculate_beat_count(en_simple) in (4, 5)

    # 5. Câu phức hợp (EN) -> 6..7 beats
    en_complex = "In 2019, the corporation spent 4 billion dollars on marketing, but only 2 percent reached actual farmers."
    assert SemanticClauseMapper.calculate_beat_count(en_complex) in (6, 7)


def test_detect_dominant_families():
    """Kiểm tra nhận diện họ tương tác dựa trên từ khóa ngữ nghĩa."""
    # Câu có từ khóa đo đạc, chuẩn mực (H2)
    s1 = "The survey baseline metrics were missing from the initial forensic audit."
    fams1 = SemanticClauseMapper.detect_dominant_families(s1)
    assert KineticFamily.H2_CONSTRAINT in fams1 or KineticFamily.H5_OPTICAL in fams1

    # Câu có từ khóa phê duyệt, đóng dấu (H1)
    s2 = "Chính quyền phê duyệt ngân sách và đóng dấu xác nhận thỏa thuận."
    fams2 = SemanticClauseMapper.detect_dominant_families(s2)
    assert KineticFamily.H1_IMPACT in fams2


def test_generate_scene_sub_director_plan_contract():
    """Kiểm tra khế ước dữ liệu JSON scene_sub_director_plan."""
    plan = generate_scene_sub_director_plan(
        scene_id="SCENE_TEST_01",
        sentence="The regulator clamped down on transactions, but the network tethered offshore accounts.",
        hero_cutout_object="Tactile regulatory ledger on aged newsprint",
        interacting_objects=["Brass caliper gauge", "Red evidence thread"],
        duration_sec=8.0,
        market="EN"
    )

    # Kiểm tra cấu trúc trường
    assert plan["schema_version"] == "scene_sub_director_plan.v3"
    assert plan["scene_id"] == "SCENE_TEST_01"
    assert 4 <= plan["calculated_beat_count"] <= 7

    # Kiểm tra object roster
    roster = plan["object_roster"]
    assert len(roster) >= 3
    for obj in roster:
        assert "id" in obj and "label" in obj and "mass_class" in obj and "z_index" in obj

    # Kiểm tra kinetic couplings
    couplings = plan["kinetic_couplings"]
    assert len(couplings) >= 2
    for c in couplings:
        assert "source_obj_id" in c and "target_obj_id" in c and "action_verb" in c and "physical_reaction" in c

    # Kiểm tra tính toàn vẹn dây xích handoff (Causal Handoff Law)
    beats = plan["dynamic_micro_beats"]
    assert len(beats) == plan["calculated_beat_count"]
    for i in range(len(beats) - 1):
        assert beats[i]["handoff_to"] == beats[i + 1]["beat_id"]
    assert beats[-1]["handoff_to"] is None
    assert plan["validation"]["handoff_chain_intact"] is True


def test_build_kinetic_causal_i2v_prompt_syntax():
    """Kiểm tra cú pháp prompt I2V liên hợp nhân quả (causing + leaving)."""
    plan = generate_scene_sub_director_plan(
        scene_id="SCENE_TEST_02",
        sentence="The heavy brass caliper clamped the metric row, triggering a neon highlight alert.",
        hero_cutout_object="Survey baseline document",
        interacting_objects=["Heavy brass vernier caliper", "Neon yellow marker"],
        duration_sec=8.0,
        market="JA"
    )

    prompt = build_kinetic_causal_i2v_prompt(plan)

    # Cú pháp liên hợp bắt buộc có "causing"
    assert "causing" in prompt
    # Bắt buộc có các ràng buộc vật lý
    assert "Tactile paper collage" in prompt
    assert "[KINETIC CAUSAL CHAIN]:" in prompt
    assert "Zero independent drifting" in prompt
    assert "12fps paper stop-motion" in prompt
