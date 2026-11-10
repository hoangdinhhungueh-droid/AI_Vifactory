#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s03_script.py — Stage S3: 5-Beat Investigative Docudrama Script (AVF-STAB-001).

Implements Stage Shape Standard. Produces structured Scene objects governed by Rule 444 & 445.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

from core.config import RunContext
from core.contracts.stages import Provenance, Scene, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S3_SCRIPT


def _get_market_legal_qualifiers(market: str) -> dict:
    m = (market or "EN").upper()
    if m in ("KR", "KO"):
        return {
            "req_charged": ["검찰 공소장에 따르면", "검찰 공소장", "공소장", "기소", "검찰", "수사", "고발", "혐의", "charged", "indictment"],
            "prefix_charged": "검찰 공소장에 따르면,",
            "req_alleged": ["규제 당국에 따르면", "규제 당국", "당국에 따르면", "주장", "의혹", "조사", "alleged", "claimed"],
            "prefix_alleged": "규제 당국에 따르면,",
            "req_settled": ["공식적인 잘못을 인정하지 않고 합의", "잘못을 인정하지 않고", "합의", "공식적인 잘못", "settled"],
            "suffix_settled": "(공식적인 잘못을 인정하지 않고 합의됨)",
        }
    elif m in ("JA", "JP"):
        return {
            "req_charged": ["起訴状の指摘によれば", "起訴状によれば", "起訴状", "当局の指摘によれば", "疑惑", "起訴", "charged", "indictment"],
            "prefix_charged": "起訴状の指摘によれば、",
            "req_alleged": ["当局の調査によれば", "当局によれば", "指摘によれば", "調査によれば", "主張", "疑惑", "alleged", "claimed"],
            "prefix_alleged": "当局の調査によれば、",
            "req_settled": ["違法性を認めることなく和解", "和解", "settled"],
            "suffix_settled": "(違法性を認めることなく和解)",
        }
    elif m in ("VN", "VI"):
        return {
            "req_charged": ["theo cáo trạng của cơ quan công tố", "theo cáo trạng", "cáo trạng", "viện kiểm sát", "bị khởi tố", "cáo buộc", "charged", "indictment"],
            "prefix_charged": "Theo cáo trạng của cơ quan công tố,",
            "req_alleged": ["theo cơ quan chức năng", "theo cơ quan điều tra", "cơ quan chức năng", "bị nghi vấn", "cáo buộc", "alleged"],
            "prefix_alleged": "Theo cơ quan chức năng,",
            "req_settled": ["dàn xếp mà không thừa nhận hành vi sai trái", "dàn xếp mà không thừa nhận", "dàn xếp", "settled"],
            "suffix_settled": "(dàn xếp mà không thừa nhận hành vi sai trái)",
        }
    else:
        return {
            "req_charged": [
                "allegedly", "according to court filings", "according to the indictment", "according to the complaint",
                "in the complaint", "complaint alleges", "charged with", "accused of",
                "sued for", "court filing", "lawsuit"
            ],
            "prefix_charged": "According to court filings,",
            "req_alleged": ["allegedly", "alleged", "claimed", "purported", "according to regulatory filings", "according to"],
            "prefix_alleged": "According to regulatory filings,",
            "req_settled": ["settled without admitting wrongdoing", "settled", "agreed to pay without admitting fault"],
            "suffix_settled": "(settled without admitting wrongdoing)",
        }


def _apply_legal_qualifier(text: str, legal_status: str, market: str) -> str:
    qual = _get_market_legal_qualifiers(market)
    m = (market or "EN").upper()
    is_en = m == "EN"

    def _has_any(txt: str, kws: list) -> bool:
        target = txt.lower()
        return any(k.lower() in target for k in kws)

    if legal_status == "charged":
        if not _has_any(text, qual["req_charged"]):
            prefix = qual["prefix_charged"]
            if is_en and text:
                first_char = text[:1].lower()
                rest = text[1:] if len(text) > 1 else ""
                return f"{prefix} {first_char}{rest}"
            return f"{prefix} {text}"
    elif legal_status == "alleged":
        if not _has_any(text, qual["req_alleged"]):
            prefix = qual["prefix_alleged"]
            if is_en and text:
                first_char = text[:1].lower()
                rest = text[1:] if len(text) > 1 else ""
                return f"{prefix} {first_char}{rest}"
            return f"{prefix} {text}"
    elif legal_status == "settled":
        if not _has_any(text, qual["req_settled"]):
            suffix = qual["suffix_settled"]
            return f"{text} {suffix}"
    return text


def _build_grounded_story_beats(
    topic: str,
    evidence_ledger: List[Any],
    evidence_map: Dict[str, Any],
    market: str = "EN"
) -> List[Tuple[str, float, List[Any]]]:
    """Generates a resilient 5-beat forensic documentary script anchored directly to the claims in the evidence ledger."""
    from app.schemas.story_contracts import StorySceneLine

    claims = evidence_ledger if evidence_ledger else []
    c_ids = [c.claim_id for c in claims] if claims else [f"C00{i}" for i in range(1, 9)]

    def _cid(idx: int) -> str:
        if not c_ids:
            return "C001"
        return c_ids[min(max(0, idx), len(c_ids) - 1)]

    def _claim_text(idx: int) -> str:
        if 0 <= idx < len(claims):
            words = claims[idx].claim.strip().rstrip(".").split()
            return " ".join(words[:12])
        return f"evidentiary records confirm critical liabilities for {topic}"

    m_code = (market or "EN").upper()
    if m_code in ("KR", "KO"):
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"급격한 시장 위기 속에서, {topic} 사태는 광범위한 구조적 충격을 촉발했습니다.",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text="표면 아래 도사린 치명적인 구조적 취약성과 제도적 맹점이 수면 위로 드러났습니다.",
                claim_ids=[_cid(0)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text="대외적인 신뢰와 합법적 외관 이면에 숨겨진 실체와 의혹이 폭로되었습니다.",
                claim_ids=[_cid(1)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text="조사관들은 핵심적인 모순에 직면했습니다: 왜 감독 당국과 시장은 이 문제가 위기로 번질 때까지 방치했는가?",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text="사태가 본격화되기 전, 관련 주체들은 대외적으로 건전한 운영을 과시하며 시장의 신뢰를 유지했습니다.",
                claim_ids=[_cid(0)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text="공식 공시와 계약 문서들은 표면상 표준적인 절차처럼 포장되었습니다.",
                claim_ids=[_cid(1)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text="시장 이해관계자들은 단기적인 성과를 앞세워 리스크를 은폐했습니다.",
                claim_ids=[_cid(2)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text="그러나 내부 기록은 공식 발표와 정면으로 배치되는 심각한 운영상 균열을 가리키고 있었습니다.",
                claim_ids=[_cid(0), _cid(2)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text="조사가 심화되면서 외부 거래에 의존한 위험한 구조가 수면 위로 드러났습니다.",
                claim_ids=[_cid(1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text="회계 장부와 감사 기록은 전례 없는 규모의 부실 노출을 폭로했습니다.",
                claim_ids=[_cid(2)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text="운영 데이터는 핵심 거래 상대방 전반에 걸친 시스템적 마찰을 확인했습니다.",
                claim_ids=[_cid(3)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text="단기적인 이익 극대화 구조가 장기적인 시스템 붕괴를 가속화하는 구조적 모순이 발생했습니다.",
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text="내부 경고와 위험 신호가 잇따랐지만, 책임자들은 무리한 레버리지를 지속했습니다.",
                claim_ids=[_cid(1), _cid(3)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text="결국 시장 환경 변화와 함께 숨겨진 취약성이 동시다발적으로 폭발하기 시작했습니다.",
                claim_ids=[_cid(2), _cid(3)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text="결정적 증거와 내부 고발이 이어지며 은폐되었던 거래 메커니즘이 완전히 해체되었습니다.",
                claim_ids=[_cid(3)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text="외부 감사인들은 장부상 자산 가치가 허구였음을 확인하고 긴급 손상 처리를 단행했습니다.",
                claim_ids=[_cid(2), _cid(3)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text="시장 신뢰가 무너지자 단 며칠 만에 막대한 유동성이 증발했습니다.",
                claim_ids=[_cid(0)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text="핵심 책임자들은 책임을 회피하며 사태를 덮으려 했지만 증거의 사슬은 명확했습니다.",
                claim_ids=[_cid(3), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text="더 이상 파국을 감출 수 없게 되자 금융 당국과 사법 기관이 전면 개입을 선언했습니다.",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text="당국의 공식 행정 제재와 사법적 책임 추궁이 현실화되었습니다.",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text="파탄 난 구조를 수습하기 위해 전례 없는 제도 개선안과 특별 대책이 발표되었습니다.",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"{topic} 사태가 남긴 명백한 교훈: 감시와 규제의 사각지대에서 방치된 위험은 반드시 사회적 대가로 귀결된다는 것입니다.",
                claim_ids=[_cid(2), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]
    elif m_code in ("JA", "JP"):
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"急激な市場の危機の中で、{topic}は広範な構造的衝撃を引き起こしました。",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text="表面下に潜む致命的な構造的脆弱性と制度的死角が浮き彫りになりました。",
                claim_ids=[_cid(0)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text="対外的な信頼と合法的な外観の裏に隠された実態と疑惑が暴露されました。",
                claim_ids=[_cid(1)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text="調査員たちは根本的な矛盾に直面しました：なぜ当局と市場は危機に至るまでこれを放置したのか？",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text="事態が表面化する前、関係主体は健全な経営を誇示し市場の信頼を維持していました。",
                claim_ids=[_cid(0)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text="公式の開示文書や契約書類は、一見すると標準的な取引手順として偽装されていました。",
                claim_ids=[_cid(1)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text="関係者は短期的な利益を優先し、潜在的リスクを隠蔽し続けました。",
                claim_ids=[_cid(2)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text="しかし内部記録は、公式発表と真っ向から対立する深刻な構造的亀裂を示していました。",
                claim_ids=[_cid(0), _cid(2)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text="調査の進展に伴い、外部取引に依存した危険な仕組みが白日の下に晒されました。",
                claim_ids=[_cid(1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text="会計帳簿と監査記録は、前例のない規模の潜在的損失を浮き彫りにしました。",
                claim_ids=[_cid(2)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text="取引データは、主要カウンターパーティ全体にわたる構造的摩擦を証明しました。",
                claim_ids=[_cid(3)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text="短期的な利益拡大構造が、長期的なシステム破綻を加速させるという致命的矛盾が生じました。",
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text="内部告発と警告が相次ぎましたが、責任者たちは過剰なリスクを取り続けました。",
                claim_ids=[_cid(1), _cid(3)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text="最終的に市場環境の変動とともに、隠蔽されていた脆弱性が一気に暴発しました。",
                claim_ids=[_cid(2), _cid(3)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text="決定的証拠と内部告発により、隠蔽されていた取引メカニズムは完全に解体されました。",
                claim_ids=[_cid(3)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text="外部監査人は資産価値の実態が虚構であることを確認し、緊急の減損処理を実施しました。",
                claim_ids=[_cid(2), _cid(3)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text="市場の信頼が崩壊すると、わずか数日のうちに膨大な流動性が蒸発しました。",
                claim_ids=[_cid(0)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text="責任者たちは保身に走り疑惑を否定しましたが、証拠の連鎖は明白でした。",
                claim_ids=[_cid(3), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text="もはや事態を覆い隠すことは不可能となり、当局による司法捜査が本格化しました。",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text="当局による公式な行政処分と司法判断が下され、構造的責任が追及されました。",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text="崩壊した秩序を立て直すため、前例のない制度改正と再発防止策が打ち出されました。",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"{topic}が遺した教訓：監視の死角で放置されたリスクは、必ず深刻な社会的コストとして跳ね返るということです。",
                claim_ids=[_cid(2), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]
    elif m_code in ("VN", "VI"):
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"Trong cuộc khủng hoảng thị trường cấp tính, {topic} đã gây ra một cú sốc cấu trúc nghiêm trọng.",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text="Ẩn sâu bên dưới là những lỗ hổng chí mạng và kẽ hở thể chế dần lộ diện.",
                claim_ids=[_cid(0)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text="Đằng sau vỏ bọc uy tín và các thủ tục hợp pháp là những sự thật bị che đậy.",
                claim_ids=[_cid(1)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text="Các điều tra viên đối diện với nghịch lý cốt lõi: tại sao cơ quan quản lý và thị trường lại để rủi ro tích tụ đến mức phát nổ?",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text="Trước khi sụp đổ, các bên liên quan liên tục phô diễn bức tranh tài chính vững chắc nhằm giữ vững niềm tin thị trường.",
                claim_ids=[_cid(0)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text="Các bản công bố thông tin và hợp đồng pháp lý đều được ngụy trang hoàn hảo như những giao dịch thông thường.",
                claim_ids=[_cid(1)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text="Các bên tham gia đặt lợi ích ngắn hạn lên hàng đầu để che giấu những rủi ro ngầm đang phình to.",
                claim_ids=[_cid(2)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text="Tuy nhiên, các tài liệu nội bộ lại ghi nhận những rạn nứt vận hành hoàn toàn trái ngược với tuyên bố công khai.",
                claim_ids=[_cid(0), _cid(2)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text="Khi cuộc điều tra đi sâu hơn, cấu trúc phụ thuộc rủi ro vào các dòng tiền ngoại vi bị phơi bày.",
                claim_ids=[_cid(1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text="Sổ sách kế toán và hồ sơ kiểm toán bộc lộ quy mô thâm hụt và nợ xấu chưa từng có.",
                claim_ids=[_cid(2)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text="Dữ liệu vận hành xác nhận những xung đột lợi ích mang tính hệ thống giữa các đối tác chủ chốt.",
                claim_ids=[_cid(3)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text="Một vòng xoáy luẩn quẩn xuất hiện khi việc tối đa hóa lợi nhuận trước mắt đẩy nhanh tốc độ đổ vỡ hệ thống.",
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text="Mặc dù xuất hiện hàng loạt cảnh báo nội bộ, những người chịu trách nhiệm vẫn bất chấp sử dụng đòn bẩy quá mức.",
                claim_ids=[_cid(1), _cid(3)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text="Cuối cùng, khi bối cảnh kinh tế đảo chiều, những quả bom nợ âm ỉ đồng loạt phát nổ.",
                claim_ids=[_cid(2), _cid(3)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text="Những bằng chứng pháp y quyết định đã bóc trần hoàn toàn cơ chế che giấu tinh vi.",
                claim_ids=[_cid(3)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text="Đơn vị kiểm toán độc lập xác nhận giá trị tài sản trên sổ sách là ảo và buộc phải trích lập dự phòng khẩn cấp.",
                claim_ids=[_cid(2), _cid(3)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text="Niềm tin bốc hơi, hàng loạt đối tác rút vốn khiến thanh khoản biến mất chỉ trong vài ngày.",
                claim_ids=[_cid(0)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text="Các mắt xích chịu trách nhiệm cố gắng thoái thác, nhưng chuỗi chứng cứ pháp lý đã khép chặt.",
                claim_ids=[_cid(3), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text="Khủng hoảng vượt quá ngưỡng chịu đựng, buộc các cơ quan điều tra và quản lý nhà nước phải vào cuộc.",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text="Các quyết định xử phạt hành chính và truy cứu trách nhiệm hình sự chính thức được thực thi.",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text="Các chính sách cải cách khẩn cấp được ban hành nhằm tái thiết lập trật tự và giảm thiểu thiệt hại xã hội.",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"Bài học đắt giá từ {topic}: Mọi rủi ro bị ngó lơ nơi góc tối của thể chế đều sẽ phải trả giá bằng sự đổ vỡ của toàn hệ thống.",
                claim_ids=[_cid(2), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]
    else:
        # Build Beat 1: Hook (0-20s, ~40-45 words, 19.2s)
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"In an acute market crisis, {topic} triggered an immediate valuation collapse as institutional capital evaporated.",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text=f"Beneath the surface lay an acute vulnerability: {_claim_text(0)}.",
                claim_ids=[_cid(0)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text=f"What appeared as market leadership transformed into a forensic investigation: {_claim_text(1)}.",
                claim_ids=[_cid(1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text="Investigators confronted the core paradox: how did this systemic vulnerability compound in plain sight before regulators intervened?",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="magnifier",
            ),
        ]

        # Build Beat 2: Setup (~40s, ~85 words, 40.8s)
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text="Prior to the unraveling, corporate leadership projected an unassailable commercial trajectory, assuring shareholders that competitive balance sheets remained thoroughly robust.",
                claim_ids=[_cid(0)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text=f"Official regulatory disclosures documented operational structures that appeared standard on the surface: {_claim_text(1)}.",
                claim_ids=[_cid(1)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text=f"Financial commentators repeatedly praised quarterly earnings momentum, emphasizing that {_claim_text(2)}.",
                claim_ids=[_cid(2)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text="Yet internal filings told a starkly different story, masking mounting operational friction behind optimistic public press statements.",
                claim_ids=[_cid(0), _cid(2)],
                visual_hook="red_thread",
            ),
        ]

        # Build Beat 3: Scheme / Mechanism (~80s, ~165 words, 79.2s)
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text=f"Beneath public enthusiasm, forensic examiners surfaced hidden dependencies on external commercial distribution: {_claim_text(1)}.",
                claim_ids=[_cid(1)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text=f"Commercial ledgers and audited filings revealed the unprecedented scale of counterparty exposure: {_claim_text(2)}.",
                claim_ids=[_cid(2)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text=f"Operational data indicated systemic friction across critical counterparties, confirming that {_claim_text(3)}.",
                claim_ids=[_cid(3)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text="This commercial architecture created an acute structural paradox: aggressive short-term monetization accelerated long-term platform vulnerability and governance risks.",
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text="Internal correspondence documented growing executive apprehension over uncollateralized guarantees, yet capital allocators continued doubling down on leveraged commitments.",
                claim_ids=[_cid(1), _cid(3)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text=f"By the time supervisory bodies initiated inquiry, the transmission mechanism had already locked capital reserves into unsustainable counterparty obligations: {_claim_text(4)}.",
                claim_ids=[_cid(2), _cid(4)],
                visual_hook="stamp",
            ),
        ]

        # Build Beat 4: Crack / Unraveling (~60s, ~125 words, 60.0s)
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text=f"Institutional fault lines erupted when formal warnings reached regulatory tribunals, establishing that {_claim_text(4)}.",
                claim_ids=[_cid(4)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text=f"Formal court filings confirmed mounting structural friction across key stakeholders: {_claim_text(5)}, alongside {_claim_text(6)}.",
                claim_ids=[_cid(5), _cid(6)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text="As market participants scrutinized the threat of automated disruption, institutional capital flight triggered an unprecedented valuation plunge across secondary debt markets.",
                claim_ids=[_cid(2), _cid(5)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text="Emergency liquidity facilities were abruptly suspended when auditor sign-offs failed, forcing debt covenants into immediate technical default.",
                claim_ids=[_cid(5), _cid(6)],
                visual_hook="ruler_measure",
            ),
        ]

        # Build Beat 5: Aftermath (~40s, ~85 words, 40.8s)
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text="The collapse obliterated billions in stakeholder equity, serving as an unsparing warning on unchecked operational dependencies and regulatory arbitrage across modern capital markets.",
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text=f"High-stakes regulatory inquiries and civil enforcement followed swiftly, confirming that {_claim_text(len(claims) - 1)}.",
                claim_ids=[_cid(len(claims) - 1)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"Sanctions, executive resignations, and comprehensive structural mandates permanently reshaped the institutional landscape surrounding {topic}.",
                claim_ids=[_cid(2), _cid(len(claims) - 1)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B5_L04",
                text="For international markets, the conclusion is inescapable: no commercial narrative can permanently defy verified accounting ledgers and organic economic gravity.",
                claim_ids=[_cid(2), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]

    raw_beats = [
        ("B1_hook", 19.2, b1_lines),
        ("B2_setup", 40.8, b2_lines),
        ("B3_scheme", 79.2, b3_lines),
        ("B4_crack", 60.0, b4_lines),
        ("B5_aftermath", 40.8, b5_lines),
    ]

    for _, _, lines in raw_beats:
        for ln in lines:
            statuses = [getattr(evidence_map.get(cid), "legal_status", "fact") for cid in ln.claim_ids if cid in evidence_map]
            if "charged" in statuses:
                ln.text = _apply_legal_qualifier(ln.text, "charged", market)
            elif "alleged" in statuses:
                ln.text = _apply_legal_qualifier(ln.text, "alleged", market)
            elif "settled" in statuses:
                ln.text = _apply_legal_qualifier(ln.text, "settled", market)

    return raw_beats



@pipeline_stage(
    id="s03_script",
    order=3,
    name="5-Beat Docudrama Script",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s02_research"],
    upstream=["s02_research"],
    downstream=["s04_critic_script", "s09_voice_tts"],
    artifacts=["runs/{run_id}/s03_script/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s03_script --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S3: 5-Beat Docudrama Script Generation."""
    start_ts = time.time()
    s2_art = require_input(STAGE, ctx.paths)
    topic = s2_art.payload.get("topic", "Corporate Monopoly Inquest")

    try:
        from core.market_resolver import resolve_canonical_market
        market = resolve_canonical_market(ctx=ctx)
    except Exception:
        market = "EN"

    preset_raw = (getattr(ctx.preset, "name", ctx.preset) if ctx.preset else getattr(getattr(ctx, "manifest", None), "preset", None)) or "story_forensic"
    is_story = bool(preset_raw in ("story_forensic", "vox_narrative"))

    if is_story:
        from app.schemas.story_contracts import EvidenceClaim, StorySceneLine, StoryScriptBeat, StoryScriptPayload
        from core.llm_json import parse_llm_json
        evidence_raw = s2_art.payload.get("evidence_ledger", [])
        evidence_ledger = [EvidenceClaim.model_validate(c) if isinstance(c, dict) else c for c in evidence_raw]

        import json

        prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s03_script.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""

        evidence_map = {c.claim_id: c for c in evidence_ledger}

        raw_beats = []
        if not ctx.dry_run and system_prompt:
            try:
                from app.services.model_gateway import get_global_gateway
                gateway = get_global_gateway()
                w_title = s2_art.payload.get("title_working") or s2_art.payload.get("topic") or topic
                c_quest = s2_art.payload.get("central_question") or f"How did structural agreements and institutional dependencies trigger the crisis in {topic}?"

                user_prompt = (
                    f"Target Market: {market}\n"
                    f"Topic: {topic}\n"
                    f"Working Title: {w_title}\n"
                    f"Central Question: {c_quest}\n"
                    f"Evidence Ledger:\n{json.dumps(s2_art.payload.get('evidence_ledger', []), indent=2, ensure_ascii=False)}\n\n"
                )
                if market == "KR":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR KOREAN (KR) MARKET:\n"
                        "1. You MUST write 100% natural, authoritative, journalistic Korean narration (Hangul). English narration is STRICTLY FORBIDDEN.\n"
                        "2. All spoken line text ('text') MUST be written in Korean sentences. DO NOT output English sentences.\n"
                        "3. Tone: Serious, objective, investigative docudrama documentary style (~했습니다, ~였습니다, ~밝혀졌습니다).\n"
                        "4. Word Budget: 360 to 480 Korean words (어절) across 18-22 lines (target 240 seconds runtime at natural 100-120 WPM Korean tempo).\n"
                        "5. CRITICAL CITATION & LEGAL RULES IN KOREAN:\n"
                        "   - EVERY factual line MUST cite valid claim_ids from the evidence ledger (e.g. ['C001']).\n"
                        "   - When citing claims with legal_status 'charged', qualify with: '검찰 공소장에 따르면,' or '기소된 혐의에 따르면'.\n"
                        "   - When citing claims with legal_status 'alleged', qualify with: '규제 당국에 따르면,' or '피해자 측 주장에 따르면'.\n"
                        "   - When citing claims with legal_status 'settled', state: '(공식적인 잘못을 인정하지 않고 합의됨)'.\n\n"
                    )
                elif market == "JA":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR JAPANESE (JA) MARKET:\n"
                        "1. You MUST write 100% natural, authoritative Japanese narration (日本語). English narration is STRICTLY FORBIDDEN.\n"
                        "2. All spoken line text ('text') MUST be written in Japanese sentences. DO NOT output English sentences.\n"
                        "3. Tone: Serious, objective, investigative docudrama documentary style.\n"
                        "4. Word Budget: 400 to 550 Japanese characters across 18-22 lines (target 240 seconds runtime).\n"
                        "5. CRITICAL CITATION & LEGAL RULES IN JAPANESE:\n"
                        "   - EVERY factual line MUST cite valid claim_ids from the evidence ledger (e.g. ['C001']).\n"
                        "   - When citing claims with legal_status 'charged', qualify with: '起訴状の指摘によれば、'.\n"
                        "   - When citing claims with legal_status 'alleged', qualify with: '当局の調査によれば、'.\n"
                        "   - When citing claims with legal_status 'settled', state: '(違法性を認めることなく和解)'.\n\n"
                    )
                elif market == "VN":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR VIETNAMESE (VN) MARKET:\n"
                        "1. You MUST write 100% natural, authoritative Vietnamese narration (Tiếng Việt). English narration is STRICTLY FORBIDDEN.\n"
                        "2. All spoken line text ('text') MUST be written in Vietnamese sentences. DO NOT output English sentences.\n"
                        "3. Tone: Serious, objective, investigative docudrama documentary style.\n"
                        "4. Word Budget: 420 to 520 Vietnamese words across 18-22 lines (target 240 seconds runtime).\n"
                        "5. CRITICAL CITATION & LEGAL RULES IN VIETNAMESE:\n"
                        "   - EVERY factual line MUST cite valid claim_ids from the evidence ledger (e.g. ['C001']).\n"
                        "   - When citing claims with legal_status 'charged', qualify with: 'Theo cáo trạng của cơ quan công tố,'.\n"
                        "   - When citing claims with legal_status 'alleged', qualify with: 'Theo cơ quan chức năng,'.\n"
                        "   - When citing claims with legal_status 'settled', state: '(dàn xếp mà không thừa nhận hành vi sai trái)'.\n\n"
                    )
                else:
                    user_prompt += (
                        "Word Budget: 460 to 540 words (target 500 words, strictly 115-135 WPM docudrama tempo). Target Duration: 240 seconds (min 180s, max 300s).\n"
                        "Generate 5 beats: B1_hook (0-20s, target ~19.2s, ~40 words), B2_setup (target ~40.8s, ~85 words), B3_scheme (target ~79.2s, ~165 words), B4_crack (target ~60.0s, ~125 words), B5_aftermath (target ~40.8s, ~85 words).\n"
                        "CRITICAL CITATION & LEGAL RULES:\n"
                        "1. EVERY factual line MUST cite valid claim_ids from the evidence ledger (e.g. ['C001']).\n"
                        "2. When citing claims with legal_status 'alleged' or 'charged', you MUST use explicit qualifying words: 'allegedly', 'according to the complaint', or 'prosecutors claimed'.\n"
                        "3. When citing claims with legal_status 'settled', you MUST state 'settled without admitting wrongdoing'.\n"
                        "4. When citing claims with legal_status 'convicted', direct conviction language is allowed.\n"
                    )
                user_prompt += (
                    "Every line must have a visual_hook: 'stamp', 'ruler_measure', 'compass_arc', 'cutout', 'red_thread', 'magnifier', 'scissors_cut', or 'grease_pencil'.\n\n"
                    "CRITICAL FORMAT MANDATE:\n"
                    "Start response immediately with { and end with }. Output ONLY valid JSON adhering to schema with NO conversational preamble or thinking."
                )
                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="claude-sonnet-5-5",
                    system_prompt=system_prompt,
                    max_tokens=4000,
                    temperature=0.3,
                    timeout=180.0,
                    fallback="claude-v4.1-flash"
                )
                parsed_json = parse_llm_json(raw_response)
                if isinstance(parsed_json, list):
                    if len(parsed_json) > 0 and isinstance(parsed_json[0], dict) and "beats" in parsed_json[0]:
                        parsed_json = parsed_json[0]
                    elif len(parsed_json) > 0 and isinstance(parsed_json[0], dict) and any(k in parsed_json[0] for k in ("beat_id", "lines", "id")):
                        parsed_json = {"beats": parsed_json}
                    else:
                        parsed_json = {}
                elif not isinstance(parsed_json, dict):
                    parsed_json = {}

                llm_beats = []
                total_llm_words = 0
                for idx, beat_data in enumerate(parsed_json.get("beats", []), start=1):
                    if not isinstance(beat_data, dict):
                        continue
                    b_id = beat_data.get("beat_id") or beat_data.get("id") or f"B{idx}_beat"
                    target_dur = float(beat_data.get("target_duration_s") or beat_data.get("duration_seconds") or (
                        19.2 if "B1" in b_id else (40.8 if "B2" in b_id else (79.2 if "B3" in b_id else (60.0 if "B4" in b_id else 40.8)))
                    ))
                    lines_data = []
                    raw_lines = beat_data.get("lines", [])
                    for l_idx, ln in enumerate(raw_lines, start=1):
                        if isinstance(ln, str):
                            ln = {"text": ln}
                        elif not isinstance(ln, dict):
                            continue
                        c_ids = ln.get("claim_ids") or []
                        if not c_ids and evidence_ledger:
                            c_ids = [evidence_ledger[min(idx - 1, len(evidence_ledger) - 1)].claim_id]
                        text = ln.get("text", "")
                        statuses = [getattr(evidence_map.get(cid), "legal_status", "fact") for cid in c_ids if cid in evidence_map]
                        if "charged" in statuses:
                            text = _apply_legal_qualifier(text, "charged", market)
                        elif "alleged" in statuses:
                            text = _apply_legal_qualifier(text, "alleged", market)
                        elif "settled" in statuses:
                            text = _apply_legal_qualifier(text, "settled", market)

                        v_hook = ln.get("visual_hook")
                        if not v_hook:
                            v_obj = beat_data.get("visual", {})
                            if isinstance(v_obj, dict) and v_obj.get("techniques"):
                                v_hook = v_obj["techniques"][0]
                            else:
                                v_hook = "stamp"

                        lines_data.append(StorySceneLine(
                            line_id=ln.get("line_id", f"{b_id}_L{l_idx:02d}"),
                            text=text,
                            claim_ids=c_ids,
                            visual_hook=v_hook
                        ))
                    total_llm_words += sum(len(line_elem.text.split()) for line_elem in lines_data)
                    llm_beats.append((b_id, target_dur, lines_data))

                m_upper = (market or "EN").upper()
                b1_has_micro_scenes = bool(llm_beats and len(llm_beats[0][2]) >= 3)
                if m_upper in ("JA", "JP"):
                    total_ja_chars = sum(len(line_elem.text.strip()) for b_elem in llm_beats for line_elem in b_elem[2])
                    if len(llm_beats) >= 5 and 650 <= total_ja_chars <= 1600 and b1_has_micro_scenes:
                        raw_beats = llm_beats
                        logger.info(f"[S03_SCRIPT] Live LLM successfully generated {len(llm_beats)} beats, {total_ja_chars} JA chars, {len(llm_beats[0][2])} Beat 1 micro-scenes.")
                    else:
                        logger.warning(
                            f"[S03_SCRIPT] LLM output did not meet criteria ({total_ja_chars} JA chars, window: 650-1600, {len(llm_beats)} beats, b1_lines: {len(llm_beats[0][2]) if llm_beats else 0}). "
                            "Falling back to evidence-ledger grounded generator."
                        )
                else:
                    w_min = 200 if m_upper in ("KR", "KO") else (300 if m_upper in ("VN", "VI") else 460)
                    w_max = 600 if m_upper in ("KR", "KO") else (600 if m_upper in ("VN", "VI") else 540)
                    if m_upper not in ("KR", "KO", "VN", "VI") and hasattr(ctx, "preset") and ctx.preset:
                        nb = getattr(ctx.preset, "narration", None)
                        if nb and hasattr(nb, "word_budget"):
                            w_min = getattr(nb.word_budget, "min", 460)
                            w_max = getattr(nb.word_budget, "max", 540)

                    if len(llm_beats) >= 5 and w_min <= total_llm_words <= w_max and b1_has_micro_scenes:
                        raw_beats = llm_beats
                        logger.info(f"[S03_SCRIPT] Live LLM successfully generated {len(llm_beats)} beats, {total_llm_words} words, {len(llm_beats[0][2])} Beat 1 micro-scenes.")
                    else:
                        logger.warning(
                            f"[S03_SCRIPT] LLM output did not meet criteria ({total_llm_words} words, window: {w_min}-{w_max}, {len(llm_beats)} beats, b1_lines: {len(llm_beats[0][2]) if llm_beats else 0}). "
                            "Falling back to evidence-ledger grounded generator."
                        )
            except Exception as _llm_err:
                logger.warning(f"[S03_SCRIPT] LLM call or parsing failed: {_llm_err}. Falling back to evidence-ledger grounded generator.")
                raw_beats = []

        if not raw_beats:
            raw_beats = _build_grounded_story_beats(topic, evidence_ledger, evidence_map, market=market)


        story_beats = []
        all_scenes: List[Scene] = []
        total_words = 0
        scene_idx = 1

        for beat_id, dur, lines in raw_beats:
            beat_words = sum(len(ln.text.split()) for ln in lines)
            total_words += beat_words
            story_beats.append(StoryScriptBeat(
                beat_id=beat_id,
                target_duration_s=dur,
                lines=lines,
                word_count=beat_words,
            ))
            for ln in lines:
                role = "hook" if "B1" in beat_id else ("context" if "B2" in beat_id else ("tension" if "B3" in beat_id else ("reveal" if "B4" in beat_id else "payoff")))
                vh = (getattr(ln, "visual_hook", "") or "").lower()
                if "stat" in vh or "counter" in vh or "metric" in vh:
                    v_meta = "giant bold red stat number card cut from heavy cardstock"
                elif "stamp" in vh or "seal" in vh:
                    v_meta = "heavy turned-wood official sanction seal stamp with vermilion ink"
                elif "ruler" in vh or "caliper" in vh or "measure" in vh:
                    v_meta = "vintage brass vernier caliper measuring an audited financial ledger"
                elif "compass" in vh or "arc" in vh:
                    v_meta = "nautical drafting compass drawing an arc across regional map"
                elif "thread" in vh or "yarn" in vh:
                    v_meta = "taut crimson evidence yarn pinned between document exhibits"
                elif "magnifier" in vh or "lens" in vh:
                    v_meta = "heavy brass magnifying lens focused on fine print contractual clause"
                elif "scissor" in vh or "cut" in vh or "shear" in vh:
                    v_meta = "vintage steel shears cutting through official bond certificate"
                elif "highlight" in vh or "marker" in vh or "pencil" in vh or "grease" in vh:
                    v_meta = "archival crimson grease pencil underlining critical legislative clause"
                elif "cutout" in vh or "portrait" in vh:
                    v_meta = "halftone black-and-white photographic cutout exhibit"
                else:
                    v_meta = "tactile investigative document clipping on aged archival parchment"

                target_wpm = 125.0
                if hasattr(ctx, "preset") and ctx.preset:
                    nb = getattr(ctx.preset, "narration", None)
                    if nb and hasattr(nb, "wpm_estimate"):
                        target_wpm = float(getattr(nb, "wpm_estimate", 125.0) or 125.0)
                target_wpm = max(115.0, min(135.0, target_wpm))
                words_per_sec = target_wpm / 60.0

                all_scenes.append(Scene(
                    scene_id=f"SCENE_{scene_idx:02d}",
                    sequence_block=f"block_{scene_idx}_{beat_id}",
                    beat_role=role,
                    narration=ln.text,
                    headline=f"{beat_id.upper()} // {ln.line_id}",
                    visual_metaphor=v_meta,
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=round(len(ln.text.split()) / words_per_sec, 1),
                ))
                scene_idx += 1

        from core.pacing_budgeter import calibrate_scene_durations_to_target

        target_run_s = 240.0
        if hasattr(ctx, "preset") and ctx.preset:
            dw = getattr(ctx.preset, "duration_window_s", None)
            if dw and hasattr(dw, "target"):
                target_run_s = float(getattr(dw, "target", 240.0) or 240.0)

        # Proportionally calibrate scene durations so timeline matches target duration and WPM is strictly clamped
        final_wpm = calibrate_scene_durations_to_target(
            all_scenes,
            target_total_duration_sec=target_run_s,
            target_wpm=target_wpm,
        )
        est_duration = target_run_s
        logger.info(
            f"[S03_SCRIPT] Narration pacing auto-clamped: {total_words} words across {est_duration:.1f}s -> {final_wpm:.1f} WPM "
            f"(docudrama ceiling [115.0, 135.0] WPM, target {target_wpm:.1f} WPM)."
        )

        # Apply limits from profile if specified (e.g. e2e_min limits to 1 scene)
        max_sc = ctx.config.limits.max_scenes
        scenes = all_scenes[:max_sc] if (max_sc > 0 and len(all_scenes) > max_sc) else all_scenes
        if len(scenes) < len(all_scenes):
            est_duration = round(sum(float(s.duration_est_sec) for s in scenes), 1)
            total_words = sum(len(s.narration.split()) for s in scenes)

        full_script_text = "\n".join(s.narration for s in all_scenes)

        # Write spoken_script.txt for downstream engines
        ctx.paths.root.mkdir(parents=True, exist_ok=True)
        spoken_script_file = ctx.paths.root / "spoken_script.txt"
        spoken_script_file.write_text(full_script_text, encoding="utf-8")

        story_payload = StoryScriptPayload(
            preset=preset_raw if preset_raw in ("story_forensic", "vox_narrative") else "story_forensic",
            topic=topic,
            total_words=total_words,
            est_duration_s=est_duration,
            beats=story_beats,
            scenes=[s.model_dump() for s in scenes],
            total_scenes=len(scenes),
            script_text=full_script_text,
            evidence_ledger=evidence_ledger,
        )
        payload = story_payload.model_dump()
        payload["task_id"] = ctx.run_id
        payload["market"] = market
        payload["b2_source_path"] = str(spoken_script_file)
        payload["b2_source_sha256"] = "story_forensic_dynamic_sha256"

    else:
        # Strict B2 Spoken Script Ingestion (Rule 118 Zero-Mock & Rule 125 Single Pipeline)
        from core.contracts.b2_b3_contract import B2ContractError, load_spoken_script

        try:
            spoken_script = load_spoken_script(ctx.paths.root, episode_id=ctx.run_id, market=market)
            raw_beats = spoken_script.beats
            total_beats = len(raw_beats)
            all_scenes: List[Scene] = []

            for idx, b in enumerate(raw_beats, start=1):
                pos = idx / max(1, total_beats)
                if pos <= 0.20:
                    block_slug = "act_i_catalyst"
                    role = "hook"
                elif pos <= 0.40:
                    block_slug = "act_ii_false_front"
                    role = "context"
                elif pos <= 0.65:
                    block_slug = "act_iii_forensic_trail"
                    role = "tension"
                elif pos <= 0.85:
                    block_slug = "act_iv_smoking_gun"
                    role = "reveal"
                else:
                    block_slug = "act_v_living_warning"
                    role = "payoff"

                from app.services.kinetic_sub_director import estimate_speech_duration
                est_dur = estimate_speech_duration(b.text, market=market)

                all_scenes.append(Scene(
                    scene_id=f"SCENE_{idx:02d}",
                    sequence_block=f"block_{idx}_{block_slug}",
                    beat_role=role,
                    narration=b.text,
                    headline=f"BEAT {idx:02d}",
                    visual_metaphor=f"Tactile evidence {idx:02d}",
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=est_dur
                ))
            source_p = spoken_script.source_path
            source_sha = spoken_script.source_sha256
        except B2ContractError:
            # Fallback for dry-run simulation mode when no spoken script was provided
            if not ctx.dry_run:
                raise
            default_texts = [
                ("hook", "block_1_act_i", f"In late 2026, an unprecedented regulatory decision permanently overturned the status quo of {topic}."),
                ("context", "block_2_act_i", f"For years, public disclosures projected complete institutional compliance regarding {topic}, while counterparty exposures compounded silently."),
                ("tension", "block_3_act_ii", f"A forensic examination of the contract paperwork reveals how critical operational revenues surrounding {topic} were redirected through offshore conduits."),
                ("reveal", "block_4_act_iii", f"The smoking gun in {topic} was not hidden secrecy, but an institutional loophole encoded directly into legacy regulatory frameworks."),
                ("payoff", "block_5_act_iv", f"This landmark ruling on {topic} marks the beginning of an era where operational transparency directly mandates structural accountability."),
            ]
            all_scenes = [
                Scene(
                    scene_id=f"SCENE_{idx:02d}",
                    sequence_block=blk,
                    beat_role=r,
                    narration=txt,
                    headline=f"BEAT {idx:02d}",
                    visual_metaphor="Tactile macro evidence",
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=6.0,
                )
                for idx, (r, blk, txt) in enumerate(default_texts, start=1)
            ]
            source_p = "dry_run_simulation"
            source_sha = "dry_run_sha256"

        max_sc = ctx.config.limits.max_scenes
        scenes = all_scenes[:max_sc] if (max_sc > 0 and len(all_scenes) > max_sc) else all_scenes

        payload = {
            "task_id": ctx.run_id,
            "topic": topic,
            "total_scenes": len(scenes),
            "b2_source_path": source_p,
            "b2_source_sha256": source_sha,
            "script_text": "\n".join([s.narration for s in scenes]),
            "scenes": [s.model_dump() for s in scenes]
        }

    prov = Provenance(
        generator="stages.s03_script",
        latency_sec=round(time.time() - start_ts, 2)
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=prov
    )

    emit_artifact(artifact, ctx.paths)
    return artifact
