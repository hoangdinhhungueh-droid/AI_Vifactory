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
    _is_cjk_char,
    _match_keyword,
    build_kinetic_causal_i2v_prompt,
    compute_kinetic_spatial_layout,
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
    assert beats_short[-1]["time_window"].endswith("3.200s")
    prompt_short = build_kinetic_causal_i2v_prompt(plan_short)
    assert "3.200s:" in prompt_short

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
    assert beats_long[-1]["time_window"].endswith("9.500s")
    prompt_long = build_kinetic_causal_i2v_prompt(plan_long)
    assert "9.500s:" in prompt_long

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

    # 1. Toạ độ 2D cụ thể (Non-tautological concrete coordinate assertions)
    layout = plan["spatial_layout"]
    assert layout["initial_pos"] == "(X:52%, Y:42%)"
    assert layout["target_contact_pos"] == "(X:68%, Y:42%)"
    assert layout["dock_pin_pos"] == "(X:42%, Y:65%)"
    assert layout["bounding_box_bounds"] == "[X:58%-84%, Y:38%-68%]"

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


def test_has_metrics_predicate_positives_and_negatives():
    """Kiểm tra trực tiếp vị từ SemanticClauseMapper.has_metrics() (Boss Item 15):
    - Đơn vị Latin đơn ký tự/ngắn (b, m, k, ty) có trailing non-letter guard:
      '3 minutes', '2 key points', '4 types', '5 bugs', '1 member' BẮT BUỘC trả về False!
    - Các số liệu hợp lệ đa thị trường (5%, 5 tỷ, 30%減, 5円, 5 billion, 100k, 50) BẮT BUỘC trả về True!
    """
    # 1. Positives (Bắt buộc True)
    assert SemanticClauseMapper.has_metrics("5%") is True
    assert SemanticClauseMapper.has_metrics("Chỉ 5% lưu lượng được kiểm tra.") is True
    assert SemanticClauseMapper.has_metrics("5 tỷ") is True
    assert SemanticClauseMapper.has_metrics("Doanh thu giảm 5 tỷ đồng trong quý trước.") is True
    assert SemanticClauseMapper.has_metrics("30%減") is True
    assert SemanticClauseMapper.has_metrics("売上は30%減少し、深刻な打撃を受けた。") is True
    assert SemanticClauseMapper.has_metrics("5円") is True
    assert SemanticClauseMapper.has_metrics("5 billion") is True
    assert SemanticClauseMapper.has_metrics("100k") is True
    assert SemanticClauseMapper.has_metrics("50") is True
    assert SemanticClauseMapper.has_metrics("2.5 million") is True
    assert SemanticClauseMapper.has_metrics("500 usd") is True
    assert SemanticClauseMapper.has_metrics("10 won") is True

    # 2. Negatives (Bắt buộc False - Trailing Unicode non-letter guard & structural exclusions)
    assert SemanticClauseMapper.has_metrics("3 minutes") is False
    assert SemanticClauseMapper.has_metrics("The meeting lasted 3 minutes.") is False
    assert SemanticClauseMapper.has_metrics("2 key points") is False
    assert SemanticClauseMapper.has_metrics("We identified 2 key points.") is False
    assert SemanticClauseMapper.has_metrics("4 types") is False
    assert SemanticClauseMapper.has_metrics("There are 4 types of vulnerabilities.") is False
    assert SemanticClauseMapper.has_metrics("5 bugs") is False
    assert SemanticClauseMapper.has_metrics("The team fixed 5 bugs yesterday.") is False
    assert SemanticClauseMapper.has_metrics("1 member") is False
    assert SemanticClauseMapper.has_metrics("Only 1 member attended the session.") is False
    assert SemanticClauseMapper.has_metrics("Step 1 was executed without anomalies.") is False
    assert SemanticClauseMapper.has_metrics("Narrative text with zero metrics.") is False

    # Vietnamese-market negative cases with trailing Unicode-letter diacritics
    assert SemanticClauseMapper.has_metrics("Chúng tôi thực hiện 5 bước kiểm tra.") is False
    assert SemanticClauseMapper.has_metrics("5 bước") is False
    assert SemanticClauseMapper.has_metrics("Có 3 mẹo để tối ưu hóa.") is False
    assert SemanticClauseMapper.has_metrics("3 mẹo") is False
    assert SemanticClauseMapper.has_metrics("Chính phủ công bố 2 kế hoạch ứng phó.") is False
    assert SemanticClauseMapper.has_metrics("2 kế hoạch") is False

    # Korean-market negative cases
    assert SemanticClauseMapper.has_metrics("5 단계 절차를 따릅니다.") is False
    assert SemanticClauseMapper.has_metrics("5 단계") is False
    assert SemanticClauseMapper.has_metrics("3 가지 핵심 요소를 분석했습니다.") is False
    assert SemanticClauseMapper.has_metrics("3 가지") is False

    # Structural sequence & year identifiers (documented decision on bare \d{2,})
    assert SemanticClauseMapper.has_metrics("Step 10") is False
    assert SemanticClauseMapper.has_metrics("Episode 02") is False
    assert SemanticClauseMapper.has_metrics("Year 1999") is False


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
    """Kiểm tra độ phủ ký tự CJK (Hán tự, CJK Ext-A, Hiragana, Katakana, Halfwidth Katakana, Hangul, Hangul Jamo, Compatibility Jamo)."""
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
    # Hangul Compatibility Jamo (0x3130 - 0x318F) (Boss Item 18)
    assert _is_cjk_char("\u3131") is True  # Hangul Letter Giyeok
    assert _is_cjk_char("\u314f") is True  # Hangul Letter A
    assert _is_cjk_char("\u318e") is True  # Hangul Compatibility Jamo
    # Non-CJK characters
    assert _is_cjk_char("A") is False
    assert _is_cjk_char("7") is False
    assert _is_cjk_char(" ") is False
    assert _is_cjk_char("%") is False


def test_whisper_word_timestamps_validation_and_no_clamp():
    """Kiểm tra tích hợp Whisper word-level timestamps (Rule 120, 135): fail-closed & không kẹp 10.0s."""
    # 1. Đo lường chính xác không bị kẹp 10s đối với câu thoại dài thực tế 12.8s
    valid_words = [
        {"word": "In", "start": 0.200, "end": 0.500},
        {"word": "a", "start": 0.500, "end": 1.000},
        {"word": "final", "start": 1.000, "end": 2.000},
        {"word": "conclusion", "start": 12.000, "end": 13.000}
    ]
    plan = generate_scene_sub_director_plan(
        scene_id="SC_WHISPER_LONG",
        sentence="A very long sentence measured by Whisper.",
        hero_cutout_object="Audit Document",
        interacting_objects=["Brass caliper", "Red marker"],
        whisper_words=valid_words
    )
    assert plan["scene_duration_sec"] == 12.8

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
    with pytest.raises(ValueError, match="negative or inverted"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_INVERTED",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[{"word": "bad", "start": 5.0, "end": 3.0}]
        )

    # 5. Fail closed khi timestamp là NaN hoặc Inf (Boss Item 17)
    with pytest.raises(ValueError, match="NaN or Inf"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_NAN",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[{"word": "bad", "start": float("nan"), "end": 1.0}]
        )
    with pytest.raises(ValueError, match="NaN or Inf"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_INF",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[{"word": "bad", "start": 0.0, "end": float("inf")}]
        )

    # 6. Fail closed khi timestamp là boolean (Boss Item 17)
    with pytest.raises(ValueError, match="cannot be boolean"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_BOOL",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[{"word": "bad", "start": True, "end": 1.0}]
        )

    # 7. Fail closed khi timestamp không đơn điệu (non-monotonic) (Boss Item 17)
    with pytest.raises(ValueError, match="non-monotonic"):
        generate_scene_sub_director_plan(
            scene_id="SC_FAIL_NON_MONOTONIC",
            sentence="Test sentence.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=[
                {"word": "first", "start": 0.0, "end": 2.0},
                {"word": "second", "start": 1.5, "end": 3.0}
            ]
        )


def test_whisper_drives_per_micro_beat_time_windows():
    """Kiểm tra Whisper word timestamps phân rã chính xác các time window từng micro-beat với độ chính xác mili-giây (Boss Round 4 Item 4)."""
    words = [
        {"word": "Step", "start": 0.000, "end": 0.200},
        {"word": "one", "start": 0.200, "end": 0.400},
        {"word": "begins", "start": 0.400, "end": 0.600},
        {"word": "now", "start": 0.600, "end": 0.800}
    ]
    # Measured duration is 0.800s (without artificial 1.5s clamp)
    plan = generate_scene_sub_director_plan(
        scene_id="SC_WHISPER_BEATS",
        sentence="Step one begins now.",
        hero_cutout_object="Forensic card",
        interacting_objects=["Vernier caliper", "Thread"],
        whisper_words=words
    )
    assert plan["scene_duration_sec"] == 0.800
    beats = plan["dynamic_micro_beats"]
    assert len(beats) == 4
    # Assert every beat's EXACT start and end with millisecond precision
    assert beats[0]["time_window"] == "0.000s - 0.200s"
    assert beats[1]["time_window"] == "0.200s - 0.400s"
    assert beats[2]["time_window"] == "0.400s - 0.600s"
    assert beats[3]["time_window"] == "0.600s - 0.800s"
    assert beats[0]["vo_keyword"] == "Step"
    assert beats[1]["vo_keyword"] == "one"
    assert beats[2]["vo_keyword"] == "begins"
    assert beats[3]["vo_keyword"] == "now"


def test_compute_kinetic_spatial_layout_empty_scene_id_fails_closed():
    """Kiểm tra fail-closed khi scene_id rỗng hoặc whitespace (Rules 118/139)."""
    with pytest.raises(ValueError, match="scene_id cannot be empty"):
        compute_kinetic_spatial_layout("")

    with pytest.raises(ValueError, match="scene_id cannot be empty"):
        compute_kinetic_spatial_layout("   ")


def test_concrete_expected_layout_per_scene_input():
    """Kiểm tra toạ độ cụ thể được tính toán từ bounding box hoặc role định lượng (Rule 140)."""
    # 1. Custom bounding box
    bbox = {"x_min": 60, "x_max": 80, "y_min": 40, "y_max": 60}
    layout_bbox = compute_kinetic_spatial_layout("SCENE_CUSTOM", bounding_box=bbox)
    assert layout_bbox.target_contact_pos == "(X:70%, Y:50%)"
    assert layout_bbox.bounding_box_bounds == "[X:60%-80%, Y:40%-60%]"
    assert layout_bbox.layout_type == "center_right"
    assert layout_bbox.vector_reveal_direction == "horizontal"

    # 2. Vertical layout derive from H1_IMPACT family
    layout_vert = compute_kinetic_spatial_layout(
        "SCENE_STAMP",
        family=KineticFamily.H1_IMPACT,
        hero_cutout_object="crimson rubber stamp drop"
    )
    assert layout_vert.layout_type == "vertical"
    assert layout_vert.target_contact_pos == "(X:50%, Y:56%)"
    assert layout_vert.vector_reveal_direction == "vertical"


def test_spatial_layout_derivation_invariants():
    """Kiểm tra bất biến hình học: target_contact_pos luôn nằm bên trong bounding_box_bounds."""
    import re

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
    # 1. Tiếng Việt: 'chi' khớp độc lập, không khớp bên trong 'machine', 'children'
    assert _match_keyword("chi", "Doanh nghiệp chi 4 tỷ đồng.") is True
    assert _match_keyword("chi", "Hệ thống machine learning hoạt động.") is False
    assert _match_keyword("chi", "Children playing outside.") is False

    # 2. CJK: Khớp chuỗi không cần khoảng trắng
    assert _match_keyword("ハイライト", "重要項目をハイライトする。") is True
    assert _match_keyword("警告", "異常事態の警告を発令した。") is True


def test_whisper_clause_aligned_windows_uneven_word_counts():
    """Kiểm tra Whisper windowing với số lượng từ không đều (7 từ chia cho 4 beats), đảm bảo liền mạch, không chồng lấn (Boss Round 4 Item 4)."""
    words = [
        {"word": "When", "start": 0.000, "end": 0.300},
        {"word": "the", "start": 0.300, "end": 0.500},
        {"word": "regulator", "start": 0.500, "end": 1.200},
        {"word": "clamped", "start": 1.200, "end": 1.700},
        {"word": "down,", "start": 1.700, "end": 2.100},
        {"word": "all", "start": 2.100, "end": 2.500},
        {"word": "froze.", "start": 2.500, "end": 3.000},
    ]
    plan = generate_scene_sub_director_plan(
        scene_id="SC_UNEVEN_WORDS",
        sentence="When the regulator clamped down, all froze.",
        hero_cutout_object="Regulator card",
        interacting_objects=["Caliper", "Thread"],
        whisper_words=words
    )
    assert plan["scene_duration_sec"] == 3.000
    beats = plan["dynamic_micro_beats"]
    assert len(beats) == 4

    # Phải bắt đầu đúng 0.000s và kết thúc đúng 3.000s
    assert beats[0]["time_window"].startswith("0.000s")
    assert beats[-1]["time_window"].endswith("3.000s")

    # Kiểm tra tính liên tục và không chồng lấn giữa các beat
    import re
    windows = []
    for b in beats:
        m = re.match(r"(\d+\.\d+)s\s*-\s*(\d+\.\d+)s", b["time_window"])
        assert m, f"Invalid time window format: {b['time_window']}"
        s_val, e_val = float(m.group(1)), float(m.group(2))
        assert s_val < e_val, f"Beat start must precede end: {b['time_window']}"
        windows.append((s_val, e_val))

    for idx in range(1, len(windows)):
        assert abs(windows[idx][0] - windows[idx-1][1]) < 1e-4, \
            f"Beat {idx} start ({windows[idx][0]}) must equal Beat {idx-1} end ({windows[idx-1][1]})"


def test_center_left_layout_from_bounding_box_and_roles():
    """Kiểm tra chọn layout center_left từ bounding box (x_c < 50) và object roles (Boss Round 4 Item 3, Item 5)."""
    # 1. Bbox nằm ở nửa trái khung hình (x_c = 28 < 50, x_span = 35 > y_span = 20)
    bbox_left = {"x_min": 10.0, "x_max": 45.0, "y_min": 35.0, "y_max": 55.0}
    layout_bbox = compute_kinetic_spatial_layout("SC_LEFT_BBOX", bounding_box=bbox_left)
    assert layout_bbox.layout_type == "center_left"
    assert layout_bbox.target_contact_pos == "(X:28%, Y:45%)"
    assert layout_bbox.vector_reveal_direction == "horizontal"

    # initial_pos và dock_pin_pos bắt buộc nằm ngoài bounding box [10-45, 35-55]
    import re
    m_init = re.search(r"\(X:(\d+)%,\s*Y:(\d+)%\)", layout_bbox.initial_pos)
    assert m_init
    init_x, init_y = int(m_init.group(1)), int(m_init.group(2))
    assert not (10 <= init_x <= 45 and 35 <= init_y <= 55), f"initial_pos {layout_bbox.initial_pos} inside bbox!"

    m_dock = re.search(r"\(X:(\d+)%,\s*Y:(\d+)%\)", layout_bbox.dock_pin_pos)
    assert m_dock
    dock_x, dock_y = int(m_dock.group(1)), int(m_dock.group(2))
    assert not (10 <= dock_x <= 45 and 35 <= dock_y <= 55), f"dock_pin_pos {layout_bbox.dock_pin_pos} inside bbox!"

    # 2. Suy diễn từ object roles chứa 'baseline' / 'counterpart'
    layout_role = compute_kinetic_spatial_layout(
        "SC_ROLE_LEFT",
        object_roles={"primary_tool": "audit counterpart verification", "ledger": "baseline input"}
    )
    assert layout_role.layout_type == "center_left"


def test_invalid_and_inverted_bounding_box_fails_closed():
    """Kiểm tra fail-closed khi bounding box đảo ngược, phi số hoặc ngoài phạm vi (Boss Round 4 Item 3, Item 5)."""
    # 1. Inverted x coordinates (x_max <= x_min)
    with pytest.raises(ValueError, match="must be strictly greater than x_min"):
        compute_kinetic_spatial_layout("SC_INV_X", bounding_box={"x_min": 80, "x_max": 20, "y_min": 30, "y_max": 60})

    # 2. Inverted y coordinates (y_max <= y_min)
    with pytest.raises(ValueError, match="must be strictly greater than y_min"):
        compute_kinetic_spatial_layout("SC_INV_Y", bounding_box={"x_min": 20, "x_max": 80, "y_min": 70, "y_max": 30})

    # 3. NaN coordinates
    with pytest.raises(ValueError, match="cannot be NaN or Inf"):
        compute_kinetic_spatial_layout("SC_NAN", bounding_box={"x_min": float("nan"), "x_max": 80, "y_min": 20, "y_max": 60})

    # 4. Out of range coordinates
    with pytest.raises(ValueError, match="percentage range"):
        compute_kinetic_spatial_layout("SC_OOR", bounding_box={"x_min": -5, "x_max": 80, "y_min": 20, "y_max": 60})


def test_substring_false_triggers_prevented():
    """Kiểm tra loại bỏ hoàn toàn substring false triggers ('timestamp', 'dropdown', 'leftover') (Boss Round 4 Item 3, Item 5)."""
    # Không để 'stamp' kích hoạt trong 'timestamp'
    # Không để 'drop' kích hoạt trong 'dropdown'
    # Không để 'left' kích hoạt trong 'leftover'
    layout = compute_kinetic_spatial_layout(
        scene_id="SC_CLEAN_SUBSTRING",
        hero_cutout_object="an archived timestamp dropdown menu leftover on desk",
        interacting_objects=["generic pointer"]
    )
    # Vì các từ khóa trên không khớp word boundary, layout mặc định chuẩn là center_right
    assert layout.layout_type == "center_right"


def test_missing_and_invalid_presets_config_fails_closed():
    """Kiểm tra _load_kinetic_presets fail-closed khi config bị thiếu hoặc lỗi (Boss Round 4 Item 2, Item 5)."""
    from app.services.kinetic_sub_director import _load_kinetic_presets

    with pytest.raises(FileNotFoundError, match="missing at"):
        _load_kinetic_presets("non_existent_presets_file_12345.json")


def test_whisper_fail_closed_when_words_fewer_than_four():
    """Kiểm tra fail-closed khi whisper_words có ít hơn 4 từ (Boss Round 4 Item 4)."""
    too_few_words = [
        {"word": "Only", "start": 0.0, "end": 0.3},
        {"word": "two", "start": 0.3, "end": 0.6}
    ]
    with pytest.raises(ValueError, match="less than required micro-beat count"):
        generate_scene_sub_director_plan(
            scene_id="SC_TOO_FEW_WORDS",
            sentence="Only two words.",
            hero_cutout_object="Doc",
            interacting_objects=["Tool"],
            whisper_words=too_few_words
        )



def test_has_metrics_prefix_currency_and_structural_negatives():
    """Kiểm tra tiền tố tiền tệ ($5, £3, €7), lookbehinds anchored (keep 20, deep 50) và năm niên đại (Boss Round 5)."""
    # 1. Positives
    assert SemanticClauseMapper.has_metrics("$5") is True
    assert SemanticClauseMapper.has_metrics("£3") is True
    assert SemanticClauseMapper.has_metrics("€7") is True
    assert SemanticClauseMapper.has_metrics("$100") is True
    assert SemanticClauseMapper.has_metrics("keep 20 staff members active") is True
    assert SemanticClauseMapper.has_metrics("deep 50 meter exploration") is True
    assert SemanticClauseMapper.has_metrics("100 typesetting templates") is True

    # 2. Negatives
    assert SemanticClauseMapper.has_metrics("Step 10") is False
    assert SemanticClauseMapper.has_metrics("Step  10") is False
    assert SemanticClauseMapper.has_metrics("Step #10") is False
    assert SemanticClauseMapper.has_metrics("Episode 02") is False
    assert SemanticClauseMapper.has_metrics("Year 1999") is False
    assert SemanticClauseMapper.has_metrics("in 1999") is False
    assert SemanticClauseMapper.has_metrics("năm 2008") is False
    assert SemanticClauseMapper.has_metrics("1999") is False
    assert SemanticClauseMapper.has_metrics("2024") is False


def test_invalid_presets_config_schema_validation(tmp_path):
    """Kiểm tra _load_kinetic_presets fail-closed trên JSON hỏng hoặc thiếu key bắt buộc (Boss Round 5)."""
    import json
    from app.services.kinetic_sub_director import _load_kinetic_presets

    # 1. Invalid JSON syntax
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{broken_json: true", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        _load_kinetic_presets(str(bad_json))

    # 2. Missing layout key
    no_layout = tmp_path / "no_layout.json"
    no_layout.write_text(json.dumps({
        "layouts": {"vertical": {}},
        "spatial_keywords": {"vertical": [], "center_left": []},
        "prose_templates": {"K1": {"DEFAULT": {}}, "K2": {"DEFAULT": {}}}
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing layout 'center_right'"):
        _load_kinetic_presets(str(no_layout))

    # 3. Missing K1.DEFAULT key
    no_k1_default = tmp_path / "no_k1_default.json"
    no_k1_default.write_text(json.dumps({
        "layouts": {
            "center_right": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"},
            "center_left": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"},
            "vertical": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"}
        },
        "spatial_keywords": {"vertical": [], "center_left": []},
        "prose_templates": {"K1": {}, "K2": {"DEFAULT": {}}}
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing 'K1.DEFAULT'"):
        _load_kinetic_presets(str(no_k1_default))


def test_whisper_clause_aligned_boundaries_exact():
    """Kiểm tra Whisper windowing khớp chính xác ranh giới câu con mà không ngắt rời cụm vị ngữ (Boss Round 5)."""
    seven_words = [
        {"word": "When", "start": 0.2, "end": 0.4},
        {"word": "the", "start": 0.4, "end": 0.6},
        {"word": "regulator", "start": 0.6, "end": 1.1},
        {"word": "clamped", "start": 1.1, "end": 1.5},
        {"word": "down,", "start": 1.5, "end": 1.9},
        {"word": "liquidity", "start": 1.9, "end": 2.5},
        {"word": "evaporated", "start": 2.5, "end": 3.1},
    ]
    plan = generate_scene_sub_director_plan(
        scene_id="SC_EXACT_CLAUSE",
        sentence="When the regulator clamped down, liquidity evaporated.",
        hero_cutout_object="Doc",
        interacting_objects=["Tool", "Thread"],
        whisper_words=seven_words
    )
    beats = plan["dynamic_micro_beats"]
    assert len(beats) == 4
    # 'clamped down,' phải đi liền với nhau tại Beat 3, không bị ngắt đôi
    assert beats[2]["vo_keyword"] == "clamped down,"
    assert beats[3]["vo_keyword"] == "liquidity evaporated"
    # Time window Beat 3 phải kết thúc tại word end của 'down,' (1.9 - 0.2 = 1.700s)
    assert beats[2]["time_window"].endswith("1.700s")


def test_whisper_word_and_bounding_box_models():
    """Kiểm tra khế ước Pydantic WhisperWord và BoundingBox với extra='forbid' và validation (Boss Round 5)."""
    from core.contracts.stages import WhisperWord, BoundingBox, Scene
    from pydantic import ValidationError

    # 1. Extra fields rejected (extra='forbid')
    with pytest.raises(ValidationError):
        WhisperWord(word="test", start=1.0, end=2.0, unknown_extra_field=True)

    with pytest.raises(ValidationError):
        BoundingBox(x_min=10, x_max=50, y_min=20, y_max=60, left=10)

    # 2. Inverted and non-monotonic word rejected
    with pytest.raises(ValueError, match="cannot precede start"):
        WhisperWord(word="bad", start=2.5, end=1.0)

    # 3. Scene whisper_words non-monotonic validator
    w1 = WhisperWord(word="first", start=1.0, end=2.0)
    w2_bad = WhisperWord(word="second", start=0.5, end=1.5)
    with pytest.raises(ValueError, match="non-monotonic"):
        Scene(scene_id="SC_BAD_MONO", narration="text", whisper_words=[w1, w2_bad])


def test_spatial_layout_full_canvas_bbox_fails_closed():
    """Kiểm tra fail-closed khi bounding box bao trọn màn hình không còn chỗ đặt ngoài (Boss Round 5)."""
    with pytest.raises(ValueError, match="Bounding box spans full canvas"):
        compute_kinetic_spatial_layout(
            "SC_FULL_CANVAS",
            bounding_box={"x_min": 1.0, "x_max": 99.0, "y_min": 1.0, "y_max": 99.0}
        )


def test_unknown_layout_type_fails_closed():
    """Kiểm tra fail-closed khi truyền layout_type không tồn tại (Boss Round 5)."""
    with pytest.raises(ValueError, match="Unknown kinetic layout type"):
        compute_kinetic_spatial_layout(
            "SC_UNKNOWN_TYPE",
            layout_type="diagonal_spiral"
        )


def test_kinetic_presets_immutability_and_additional_schema_checks(tmp_path):
    """Kiểm tra caller isolation và các key bắt buộc K2.DEFAULT / spatial_keywords (Boss Round 6)."""
    import json
    from app.services.kinetic_sub_director import _load_kinetic_presets

    # 1. Caller isolation: caller mutation does not pollute subsequent calls
    presets1 = _load_kinetic_presets()
    presets1["layouts"]["center_right"] = "MUTATED"
    presets2 = _load_kinetic_presets()
    assert presets2["layouts"]["center_right"] != "MUTATED"
    assert isinstance(presets2["layouts"]["center_right"], dict)

    # 2. Missing K2.DEFAULT template
    cfg_file = tmp_path / "missing_k2.json"
    cfg_file.write_text(json.dumps({
        "layouts": {
            "center_right": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"},
            "center_left": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"},
            "vertical": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"}
        },
        "spatial_keywords": {"vertical": [], "center_left": []},
        "prose_templates": {
            "K1": {"DEFAULT": {"action_verb": "a", "contact_point": "b", "physical_reaction": "c", "residue": "d"}},
            "K2": {}
        }
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing 'K2.DEFAULT'"):
        _load_kinetic_presets(str(cfg_file))

    # 3. Missing spatial_keywords list
    cfg_file2 = tmp_path / "missing_sk.json"
    cfg_file2.write_text(json.dumps({
        "layouts": {
            "center_right": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"},
            "center_left": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"},
            "vertical": {"initial_pos": "a", "target_contact_pos": "b", "dock_pin_pos": "c", "bounding_box_bounds": "d", "vector_reveal_direction": "e"}
        },
        "spatial_keywords": {"vertical": []},
        "prose_templates": {
            "K1": {"DEFAULT": {"action_verb": "a", "contact_point": "b", "physical_reaction": "c", "residue": "d"}},
            "K2": {"DEFAULT": {"action_verb": "a", "contact_point": "b", "physical_reaction": "c", "residue": "d"}}
        }
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="spatial_keywords missing list 'center_left'"):
        _load_kinetic_presets(str(cfg_file2))


def test_has_metrics_korean_won_and_us_dollar():
    """Kiểm tra đồng Won (₩) và US$ được nhận diện đúng là metrics (Boss Round 6)."""
    assert SemanticClauseMapper.has_metrics("Chi phí lên đến ₩50000 cho mỗi giao dịch.") is True
    assert SemanticClauseMapper.has_metrics("Mức phạt ₩ 1000000 áp dụng ngay.") is True
    assert SemanticClauseMapper.has_metrics("Target valuation reached US$100 million.") is True


def test_estimate_speech_duration_fail_closed_on_none_market():
    """Kiểm tra estimate_speech_duration fail-closed khi market=None (Boss Round 6)."""
    with pytest.raises(ValueError, match="No market specified"):
        estimate_speech_duration("This is a sentence", market=None)
    assert estimate_speech_duration("This is a sentence", market="EN") >= 2.5
