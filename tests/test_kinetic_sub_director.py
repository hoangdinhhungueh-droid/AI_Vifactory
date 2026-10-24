#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_kinetic_sub_director.py — Unit Tests for Object-to-Object Kinetic Coupling Engine.

Enforces:
- Rule 121: Strict Verification Protocol.
- Rule 127: Runtime Programmatic Verification.
- Rule 128: Generic Contract Pattern (tested across VN, JA, EN, KR).
- Rule 140 v3: Kinetic Coupling Taxonomy & Causal Compound Verb Prompts.
"""

from app.services.kinetic_sub_director import (
    KineticFamily,
    SemanticClauseMapper,
    build_kinetic_causal_i2v_prompt,
    estimate_speech_duration,
    generate_scene_sub_director_plan,
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
    assert "Forensic documentary motion graphics" in prompt
    assert "tactile stop-motion" in prompt
    assert "[KINETIC CAUSAL CHAIN]:" in prompt
    assert "Zero independent drifting" in prompt
    assert "12fps paper stop-motion" in prompt


def test_estimate_speech_duration_multilingual():
    """Kiểm tra hàm ước tính thời lượng câu thoại đa ngôn ngữ và giới hạn [2.5s, 10.0s]."""
    # 1. Câu tiếng Nhật ngắn (11 ký tự -> ~2.0s raw -> clamped to 2.5s)
    ja_short = "契約が成立した。"
    assert estimate_speech_duration(ja_short, market="JA") == 2.5

    # 2. Câu tiếng Nhật vừa (33 ký tự -> 33 / 5.5 = 6.0s)
    ja_mid = "この数字は市場全体で測定されたものではなく、推計値に過ぎません。"
    dur_ja = estimate_speech_duration(ja_mid, market="JA")
    assert 5.5 <= dur_ja <= 6.5

    # 3. Câu tiếng Anh vừa (12 từ -> 12 / 2.8 = 4.29s)
    en_mid = "The forensic auditor discovered missing ledger records inside the classified intelligence archive."
    assert 4.0 <= estimate_speech_duration(en_mid, market="EN") <= 5.0

    # 4. Câu cực dài vượt trần (>10s) -> Bắt buộc bị kẹp về đúng 10.0s
    long_sentence = "This is an extremely long investigative sentence designed to exceed the normal bounds of documentary narration " * 3
    assert estimate_speech_duration(long_sentence, market="EN") == 10.0


def test_dynamic_pacing_timeline_flexibility():
    """Kiểm tra vi nhịp và timeline co giãn linh hoạt theo độ dài câu thoại thay vì cố định 8s."""
    # 1. Phân cảnh ngắn (3.2s) -> Beat Count Governor khóa về 4 bước, kết thúc đúng 3.2s
    plan_short = generate_scene_sub_director_plan(
        scene_id="SC_SHORT",
        sentence="だますメールを書く。",
        hero_cutout_object="Phishing email draft",
        interacting_objects=["Fountain pen nib"],
        duration_sec=3.2,
        market="JA"
    )
    assert plan_short["scene_duration_sec"] == 3.2
    assert plan_short["calculated_beat_count"] == 4
    beats_short = plan_short["dynamic_micro_beats"]
    assert beats_short[-1]["time_window"].endswith("3.2s")
    prompt_short = build_kinetic_causal_i2v_prompt(plan_short)
    assert "3.2s:" in prompt_short

    # 2. Phân cảnh dài (9.5s) với câu phức -> Nở 6-7 bước, kết thúc đúng 9.5s
    plan_long = generate_scene_sub_director_plan(
        scene_id="SC_LONG",
        sentence="In 2024, the corporation spent 4 billion dollars on security, but only 2 percent reached actual frontline defenses.",
        hero_cutout_object="Corporate financial ledger",
        interacting_objects=["Heavy steel shears", "Red evidence yarn"],
        duration_sec=9.5,
        market="EN"
    )
    assert plan_long["scene_duration_sec"] == 9.5
    assert plan_long["calculated_beat_count"] >= 5
    beats_long = plan_long["dynamic_micro_beats"]
    assert beats_long[-1]["time_window"].endswith("9.5s")
    prompt_long = build_kinetic_causal_i2v_prompt(plan_long)
    assert "9.5s:" in prompt_long

    # 3. Phân cảnh không truyền duration_sec -> Tự động suy ra từ độ dài câu thoại
    plan_auto = generate_scene_sub_director_plan(
        scene_id="SC_AUTO",
        sentence="The confidential archive remained sealed inside the vault.",
        hero_cutout_object="Confidential archive box",
        interacting_objects=["Brass key"],
        duration_sec=None,
        market="EN"
    )
    assert 2.5 <= plan_auto["scene_duration_sec"] <= 10.0



def test_kinetic_coordinates_and_dead_stop_holds():
    """Kiểm tra toạ độ 2D chuẩn xác, điểm dừng hình (snap-stop freeze) và liên kết cụm vật lý."""
    plan = generate_scene_sub_director_plan(
        scene_id="SCENE_02",
        sentence="この数字は市場全体で測定されたものではありません。",
        hero_cutout_object="Vintage mechanical brass caliper measuring tool with engraved metric scales",
        interacting_objects=[
            "Unverified survey ledger sheet with question marks",
            "Muted gray paper bookmark"
        ],
        duration_sec=7.7,
        market="JA"
    )

    prompt = build_kinetic_causal_i2v_prompt(plan)

    # 1. Toạ độ 2D chuẩn xác
    assert "(X:52%, Y:42%)" in prompt
    assert "(X:68%, Y:42%)" in prompt
    assert "(X:42%, Y:65%)" in prompt
    assert "[X:58%-84%, Y:38%-68%]" in prompt

    # 2. Điểm dừng hình (Snap-stop freeze holds)
    assert "Snap-stop freeze holds completely still" in prompt
    assert "Unified cluster freeze holds motionless" in prompt

    # 3. Liên kết vật lý hợp nhất (Unified physical cluster)
    assert "docks flush against the hero tool base at coordinate (X:42%, Y:65%)" in prompt
    assert "locking all objects into a single unified physical cluster" in prompt
