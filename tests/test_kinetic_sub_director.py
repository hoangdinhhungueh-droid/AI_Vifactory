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

    # 1. Toạ độ 2D chuẩn xác sinh động học theo layout
    layout = plan["spatial_layout"]
    assert layout["initial_pos"] in prompt
    assert layout["target_contact_pos"] in prompt
    assert layout["dock_pin_pos"] in prompt
    assert layout["bounding_box_bounds"] in prompt

    # 2. Điểm dừng hình (Snap-stop freeze holds)
    assert "Snap-stop freeze holds completely still" in prompt
    assert "Unified cluster freeze holds motionless" in prompt

    # 3. Liên kết vật lý hợp nhất (Unified physical cluster)
    assert f"docks flush against the hero tool base at coordinate {layout['dock_pin_pos']}" in prompt
    assert "locking all objects into a single unified physical cluster" in prompt


def test_has_metrics_cross_market_comprehensive():
    """Kiểm tra regex lượng hóa đa thị trường (Rule 120, 128): đơn vị % lẻ, CJK liền kề, tiền tệ JP/VN/EN."""
    assert SemanticClauseMapper.calculate_beat_count("Chỉ 5% lưu lượng được kiểm tra.") >= 5
    assert SemanticClauseMapper.calculate_beat_count("5% of the total dataset was corrupted.") >= 5
    assert SemanticClauseMapper.calculate_beat_count("売上は30%減少し、深刻な打撃を受けた。") >= 5
    assert SemanticClauseMapper.calculate_beat_count("価格は5円です。") >= 5
    assert SemanticClauseMapper.calculate_beat_count("Doanh thu giảm 5 tỷ đồng trong quý trước.") >= 5
    assert SemanticClauseMapper.calculate_beat_count("The company invested 5 billion dollars into security.") >= 5
    # Negative cases: không có metric hay đơn vị lượng hóa
    assert SemanticClauseMapper.calculate_beat_count("This is a narrative sentence without any figures.") == 4
    assert SemanticClauseMapper.calculate_beat_count("Step 1 was executed without anomalies.") == 4


def test_cjk_character_ranges():
    """Kiểm tra độ phủ ký tự CJK (Hán tự, CJK Ext-A, Hiragana, Katakana, Halfwidth Katakana, Hangul, Hangul Jamo)."""
    from app.services.kinetic_sub_director import _is_cjk_char
    # CJK Unified Ideographs
    assert _is_cjk_char("\u4e00") is True
    # CJK Extension A
    assert _is_cjk_char("\u3400") is True
    # Hiragana
    assert _is_cjk_char("\u3042") is True
    # Katakana
    assert _is_cjk_char("\u30a2") is True
    # Halfwidth Katakana
    assert _is_cjk_char("\uff66") is True
    # Hangul Syllables
    assert _is_cjk_char("\uac00") is True
    # Hangul Jamo
    assert _is_cjk_char("\u1100") is True
    # Non-CJK characters
    assert _is_cjk_char("A") is False
    assert _is_cjk_char("7") is False
    assert _is_cjk_char(" ") is False
    assert _is_cjk_char("%") is False


def test_whisper_word_timestamps_validation_and_no_clamp():
    """Kiểm tra tích hợp Whisper word-level timestamps (Rule 120, 135): fail-closed & không kẹp 10.0s."""
    import pytest

    # 1. Đo lường chính xác không bị kẹp 10s đối với câu thoại dài thực tế 12.8s
    valid_words = [
        {"word": "In", "start": 0.2, "end": 0.5},
        {"word": "conclusion", "start": 12.0, "end": 13.0}
    ]
    plan = generate_scene_sub_director_plan(
        scene_id="SC_WHISPER_LONG",
        sentence="A very long sentence measured by Whisper.",
        hero_cutout_object="Audit Document",
        interacting_objects=["Brass caliper", "Red marker"],
        whisper_words=valid_words
    )
    assert plan["scene_duration_sec"] == 12.8  # 13.0 - 0.2 = 12.8s, không bị kẹp về 10s!

    # 2. Fail closed khi whisper_words rỗng
    with pytest.raises(ValueError, match="non-empty list"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_EMPTY",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[]
        )

    # 3. Fail closed khi thiếu trường start hoặc end
    with pytest.raises(ValueError, match="missing valid"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_MISSING",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[{"word": "bad", "start": 0.0}]
        )

    # 4. Fail closed khi timestamp đảo ngược
    with pytest.raises(ValueError, match="inverted or negative"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_INVERTED",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[{"word": "bad", "start": 5.0, "end": 3.0}]
        )


def test_spatial_layout_derivation_invariants():
    """Kiểm tra bất biến hình học: target_contact_pos luôn nằm bên trong bounding_box_bounds."""
    import re
    from app.services.kinetic_sub_director import compute_kinetic_spatial_layout, KineticFamily

    for scene_id in ["SCENE_01", "SCENE_02", "SCENE_03", "SCENE_10", "SCENE_01_ALT"]:
        for fam in [KineticFamily.H1_IMPACT, KineticFamily.H2_CONSTRAINT, KineticFamily.H3_SEVER]:
            layout = compute_kinetic_spatial_layout(scene_id, family=fam)
            
            # Trích xuất toạ độ target (X:T_X%, Y:T_Y%)
            m_target = re.search(r"\(X:(\d+)%,\s*Y:(\d+)%\)", layout.target_contact_pos)
            assert m_target, f"Invalid target format: {layout.target_contact_pos}"
            tx, ty = int(m_target.group(1)), int(m_target.group(2))

            # Trích xuất bounding box [X:minX%-maxX%, Y:minY%-maxY%]
            m_box = re.search(r"\[X:(\d+)%-(\d+)%,\s*Y:(\d+)%-(\d+)%\]", layout.bounding_box_bounds)
            assert m_box, f"Invalid bounding box format: {layout.bounding_box_bounds}"
            min_x, max_x = int(m_box.group(1)), int(m_box.group(2))
            min_y, max_y = int(m_box.group(3)), int(m_box.group(4))

            # Bất biến hình học: Điểm chạm phải nằm trọn trong khung bounding box
            assert min_x <= tx <= max_x, f"Target X={tx}% is outside [{min_x}%, {max_x}%] in {scene_id}"
            assert min_y <= ty <= max_y, f"Target Y={ty}% is outside [{min_y}%, {max_y}%] in {scene_id}"


def test_match_keyword_word_boundaries():
    """Kiểm tra khớp từ khóa word boundary tiếng Việt/Latinh và CJK."""
    from app.services.kinetic_sub_director import _match_keyword

    # 1. Tiếng Việt: 'chi' khớp độc lập, không khớp bên trong 'machine', 'children'
    assert _match_keyword("chi", "Doanh nghiệp chi 4 tỷ đồng.") is True
    assert _match_keyword("chi", "Hệ thống machine learning hoạt động.") is False
    assert _match_keyword("chi", "Children playing outside.") is False

    # 2. CJK: Khớp chuỗi không cần khoảng trắng
    assert _match_keyword("ハイライト", "重要項目をハイライトする。") is True
    assert _match_keyword("警告", "異常事態の警告を発令した。") is True
