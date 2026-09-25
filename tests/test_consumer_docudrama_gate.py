import pytest
from app.services.hhtech_reasoner import detect_safety_and_theme
from app.services.skill_loader import get_b1_strategic_rules


def test_consumer_docudrama_theme_detection_multilingual():
    # Korean
    t_kr, s_kr, note_kr = detect_safety_and_theme("환불 거부 영수증 논란", "KR")
    assert t_kr == "consumer_injustice_institutional_trap"
    assert s_kr == "YT-Consumer-Awareness"
    assert "SOCIAL REALITY & CONSUMER INJUSTICE DOCUDRAMA" in note_kr

    t_kr2, _, _ = detect_safety_and_theme("동탄문구점 바가지 가격표시제 위반", "KR")
    assert t_kr2 == "consumer_injustice_institutional_trap"

    # English
    t_en, s_en, _ = detect_safety_and_theme("hidden fee retail cancellation trap", "EN")
    assert t_en == "consumer_injustice_institutional_trap"
    assert s_en == "YT-Consumer-Awareness"

    # Japanese / Global
    t_jp, s_jp, _ = detect_safety_and_theme("subscription trap cancellation fee fine print", "JP")
    assert t_jp == "consumer_injustice_institutional_trap"
    assert s_jp == "YT-Consumer-Awareness"


def test_b1_strategic_rules_contains_pillar11_and_anti_tutorial():
    rules = get_b1_strategic_rules()
    assert "Pillar 11: Everyday Consumer Injustice & Institutional Traps" in rules
    assert "ANTI-TUTORIAL PACKAGING (RULE 130)" in rules
    assert "Strictly forbidden to use tutorial/how-to phrasing" in rules


def test_anti_tutorial_title_regex_rejection():
    # Helper pattern mimicking anti-tutorial filter
    import re
    tutorial_pattern = re.compile(
        r"^(?:how to|steps to|5 steps|cách|mẹo|5 bước|5 điều|환불하는법|解約方法)\b",
        re.IGNORECASE
    )

    bad_titles = [
        "How to get a refund from a retail store",
        "Cách lấy lại tiền khi bị ép giá",
        "Mẹo đòi lại tiền hóa đơn siêu thị",
        "환불하는법: 영수증 도장 확인 5가지",
        "5 bước khiếu nại cửa hàng từ chối đổi trả"
    ]

    for title in bad_titles:
        assert tutorial_pattern.search(title) is not None, f"Failed to catch tutorial title: {title}"

    good_titles = [
        "The $140 Receipt Stamp Trap: How Stores Legally Deny Consumer Rights",
        "14만원 탁구채 환불 거부: 영수증 도장 하나로 소비자를 묶는 법",
        "Chiếc bẫy con dấu 140.000 won: Kẽ hở nào trói chặt người tiêu dùng?",
        "When A Local Store Weaponizes Fine Print Against An Innocent Consumer"
    ]

    for title in good_titles:
        assert tutorial_pattern.search(title) is None, f"False positive on dramatic docudrama title: {title}"
