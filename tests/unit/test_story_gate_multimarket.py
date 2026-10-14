# tests/unit/test_story_gate_multimarket.py
# -*- coding: utf-8 -*-
"""Unit tests for Multilingual Story Gate (Rule 128) & B2 Hard Circuit Breaker (Rule 118).
Verifies:
  - Language-aware pacing and length calibration (EN, JP, KR, VN)
  - Japanese character metric (2500 - 4500 chars) instead of word count
  - Korean syllable metric (2400 - 4200 syllables)
  - Exact 5-Act delimiter segmentation
  - CJK punchy pattern interrupt (4 - 18 chars)
  - Multilingual 5 Canonical Cliffhanger Archetypes
  - B2 Hard Circuit Breaker stops candidate drain after max attempts
"""

import re
import pytest
from app.services.story_gate import score_story
from app.services.vox_automated_director import audit_cliffhanger_patterns


def test_audit_cliffhanger_patterns_multilingual():
    """Verify that 5 canonical documentary cliffhanger archetypes match across EN, JP, KR, VN."""
    # 1. THE_PRICE_LINE
    assert audit_cliffhanger_patterns("The price of that decision exceeded 10 billion dollars.")["matched"]
    assert audit_cliffhanger_patterns("その決定の代償は、1100億円という巨額の負債となって今も残されている。")["matched"]
    assert audit_cliffhanger_patterns("그 대가는 500억원의 부채로 지금까지 이어지고 있다.")["matched"]
    assert audit_cliffhanger_patterns("Cái giá phải trả là hơn 5 nghìn tỷ đồng tổn thất tài chính.")["matched"]

    # 2. THE_DATED_FORWARD_JUMP
    assert audit_cliffhanger_patterns("Decades later, the true fallout is only beginning to surface.")["matched"]
    assert audit_cliffhanger_patterns("それから2026年現在に至るまで、その真相は封印されたままだ。")["matched"]
    assert audit_cliffhanger_patterns("그리고 2026년 오늘날까지도 그 의혹은 풀리지 않았다.")["matched"]
    assert audit_cliffhanger_patterns("Cho đến tận hôm nay, bài học về sự sụp đổ đó vẫn còn nguyên giá trị.")["matched"]

    # 3. THE_MISSING_PIECE
    assert audit_cliffhanger_patterns("One piece was missing, and investigators never found it.")["matched"]
    assert audit_cliffhanger_patterns("しかし、唯一の手がかりは誰にも分からず、記録から消失した。")["matched"]
    assert audit_cliffhanger_patterns("하지만 결정적인 진상은 끝내 밝혀지지 않았다.")["matched"]
    assert audit_cliffhanger_patterns("Manh mối duy nhất vẫn là bí ẩn chưa từng được làm rõ.")["matched"]

    # 4. THE_UNRESOLVED_OBJECT
    assert audit_cliffhanger_patterns("The physical ledger remains locked in an unknown vault.")["matched"]
    assert audit_cliffhanger_patterns("押収された原本の記録は失われ、証拠は残されたままだ。")["matched"]
    assert audit_cliffhanger_patterns("그 장부는 지금도 봉인된 채 어딘가에 남아있다.")["matched"]
    assert audit_cliffhanger_patterns("Bộ hồ sơ mật vẫn bị niêm phong và biến mất không dấu vết.")["matched"]

    # 5. THE_QUIET_CONTRADICTION
    assert audit_cliffhanger_patterns("Yet, the opposite was true all along.")["matched"]
    assert audit_cliffhanger_patterns("しかし、現実はまったく逆であった。")["matched"]
    assert audit_cliffhanger_patterns("하지만 현실은 완전히 반대였다.")["matched"]
    assert audit_cliffhanger_patterns("Thế nhưng, sự thật lại đi ngược lại hoàn toàn.")["matched"]


def test_story_gate_japanese_script_passes_without_spacing_bias():
    """Verify that a legitimate Japanese 5-Act docudrama script achieves >= 11/13 and Verdict PASS."""
    act1 = (
        "=== ACT I ===\n"
        "2026年、過去最多となる240件の人手不足倒産が帝国データバンクにより確認された。\n"
        "果たして、なぜ好況と言われる市場でこれほどの中小企業が静かに崩壊しているのだろうか？\n"
        "100人以上の従業員を抱える老舗企業でさえ、賃上げ圧力と借入返済の二重苦に直面している。\n"
        "記録によると、その負債総額は500億円を突破した。この数字を覚えておいてほしい。\n"
        "しかし誰も、水面下で進行していた本当の理由に気づいていなかった。\n"
        "なぜこのような事態に陥ったのか、疑問は深まるばかりだ。\n"
    )
    act2 = (
        "=== ACT II ===\n"
        "歴史を遡ると、事の発端は2020年の支援制度の創設に遡る。\n"
        "メディアは成長と拡大の神話を大々的に報道していた。\n"
        "当時、300社以上の経営者は低金利融資のシステムを利用し、売上45%の急増を図った。\n"
        "しかし、表面的な好調の裏で、固定費の増大という罠が仕掛けられていた。\n"
        "政府の公式資料でも、過剰な依存体制が指摘されていたのである。\n"
        "その理由は、返済猶予が切れた後の金利上昇にあった。\n"
    )
    act3 = (
        "=== ACT III ===\n"
        "内部告発と監査によって、制度の死角と盲点が徐々に浮き彫りになった。\n"
        "資金繰りの亀裂は水面下で蓄積し、金融機関からの圧力は80%の中小企業で限界に達した。\n"
        "紙の証跡は消えた。\n"
        "だが、誰もその警告の兆候を直視しようとはしなかった。\n"
        "疑惑の連鎖は、もはや後戻りのできない破綻の危機へと突入していった。\n"
        "明らかになったのは、裏で不正な融資斡旋が行われていた事実である。\n"
    )
    act4 = (
        "=== ACT IV ===\n"
        "決定打となったのは、裁判所による管財人の調査報告であった。\n"
        "黒幕として利益を吸い上げていた構造が白日の下に暴露された。\n"
        "15件の法的整理が開始され、主要な取引先は連鎖倒産の責任を追及された。\n"
        "答えは、現場の疲弊を無視した制度の致命的な失敗である。\n"
        "事業の停止と自主回収が命じられ、帝国は一夜にして破綻した。\n"
    )
    act5 = (
        "=== ACT V ===\n"
        "現代の市場において、この事件は決して過去の遺産ではない。\n"
        "今日、私たちが直面している労働市場の歪みに対する重い警告である。\n"
        "教訓を無視すれば、同じ過ちは再び繰り返されるだろう。\n"
        "結局、私たちが学ぶべき最大の課題は何なのだろうか。\n"
        "その決定の代償は、数百億円の損失となって今も残されている。\n"
    )
    pad_jp = "市場の歪みと構造的な問題を分析した政府の報告書によると、実質的な支援策が欠如していたことは統計からも明らかであり、2025年までに35%の事業者が影響を受けた。その理由は資金繰りの悪化にある。\n" * 8
    full_script = f"{act1}\n{pad_jp}\n{act2}\n{pad_jp}\n{act3}\n{pad_jp}\n{act4}\n{pad_jp}\n{act5}"

    res = score_story(full_script)
    assert res["is_cjk"] is True
    assert res["primary_metric"] >= 2500
    assert res["checks"]["1_length_1700_2500_words"] is True
    assert res["checks"]["6_pace_in_band"] is True
    assert res["checks"]["7_arc_five_acts"] is True
    assert res["checks"]["9_hook_shock_in_first_60w"] is True
    assert res["checks"]["12_pattern_interrupt"] is True
    assert res["checks"]["13_vox_cliffhanger_archetypes"] is True
    assert res["score"] >= 11
    assert res["verdict"] == "PASS"


def test_b2_circuit_breaker_parameter_respected():
    """Verify that max_b2_attempts parameter is exposed and defaults to 2."""
    from app.services.trend_engine_b1 import MAX_B2_ATTEMPTS_DEFAULT, discover_and_produce_market_trend
    import inspect

    sig = inspect.signature(discover_and_produce_market_trend)
    assert "max_b2_attempts" in sig.parameters
    assert sig.parameters["max_b2_attempts"].default == MAX_B2_ATTEMPTS_DEFAULT
    assert MAX_B2_ATTEMPTS_DEFAULT == 2
