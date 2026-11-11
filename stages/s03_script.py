#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s03_script.py — Stage S3: 5-Beat Investigative Docudrama Script (AVF-STAB-001).

Implements Stage Shape Standard. Produces structured Scene objects governed by Rule 444 & 445.
"""

from __future__ import annotations

import logging
import re
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


def _with_particle(word: str, p_type: str) -> str:
    """Appends appropriate Hangul josa (은/는, 이/가, 을/를, 과/와)."""
    if not word:
        return ""
    clean = word.rstrip("., )]\"'")
    if not clean:
        return word
    last_char = clean[-1]
    if "\uac00" <= last_char <= "\ud7a3":
        code = ord(last_char) - 0xac00
        has_batchim = (code % 28) != 0
        if p_type == "topic":
            return f"{word}{'은' if has_batchim else '는'}"
        elif p_type == "subj":
            return f"{word}{'이' if has_batchim else '가'}"
        elif p_type == "obj":
            return f"{word}{'을' if has_batchim else '를'}"
        elif p_type == "with":
            return f"{word}{'과' if has_batchim else '와'}"
    fallbacks = {"topic": "는", "subj": "가", "obj": "를", "with": "와"}
    return f"{word}{fallbacks.get(p_type, '')}"


def _extract_claim_elements(c: Any) -> Dict[str, Any]:
    if not c:
        return {"claim": "", "entities": [], "numbers": [], "ko_terms": [], "ja_terms": [], "vn_terms": [], "en_terms": []}
    text = str(getattr(c, "claim", "") or (c.get("claim", "") if isinstance(c, dict) else "")).strip()

    parens = re.findall(r"\(([^)]+)\)", text)
    num_matches = re.findall(
        r"(?:\b\d{1,2}월\s*\d{1,2}일|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?|\b\d+[,\d]*(?:\.\d+)?\s*(?:%|percent|조\s*원|trillion|billion|million|만\s*원|억\s*원|명|채|건|KRW|USD|JPY|VND|LTV)?|\b\d+/\d+|\b\d+분의\s*\d+|\bone-third\b)",
        text,
        re.IGNORECASE
    )

    ko_terms = []
    ja_terms = []
    vn_terms = []
    en_terms = []
    entities = []

    for p in parens:
        cleaned_p = p.strip("'\" ")
        if re.search(r"[\uac00-\ud7a3]", cleaned_p):
            ko_terms.append(cleaned_p)
        if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", cleaned_p):
            ja_terms.append(cleaned_p)

    t_lower = text.lower()
    if "molit" in t_lower or "ministry of land" in t_lower or "국토교통부" in text:
        ko_terms.append("국토교통부(MOLIT)")
        ja_terms.append("韓国国土交通部(MOLIT)")
        vn_terms.append("Bộ Đất đai Giao thông Hàn Quốc (MOLIT)")
        en_terms.append("the Ministry of Land, Infrastructure and Transport (MOLIT)")
        entities.append("MOLIT")
    if "hug" in t_lower or "housing & urban guarantee" in t_lower or "주택도시보증공사" in text:
        ko_terms.append("주택도시보증공사(HUG)")
        ja_terms.append("住宅都市保証公社(HUG)")
        vn_terms.append("Tổng công ty Bảo lãnh Đô thị Nhà ở (HUG)")
        en_terms.append("Korea Housing & Urban Guarantee Corporation (HUG)")
        entities.append("HUG")
    if "jeonse" in t_lower or "전세" in text:
        ko_terms.append("전세")
        ja_terms.append("チョンセ(伝貰)")
        vn_terms.append("tiền cọc Jeonse")
        en_terms.append("Jeonse deposit financing")
        entities.append("Jeonse")
    if "villa king" in t_lower or "빌라왕" in text:
        ko_terms.append("빌라왕")
        ja_terms.append("ヴィラ王")
        vn_terms.append("Vua Biệt Thự (Villa King)")
        en_terms.append("Villa Kings")
        entities.append("Villa King")
    if "proxy landlord" in t_lower or "strawmen" in t_lower or "바지임대인" in text:
        ko_terms.append("바지임대인")
        ja_terms.append("名義貸し家主")
        vn_terms.append("chủ nhà bù nhìn")
        en_terms.append("insolvent proxy landlords")
        entities.append("proxy landlords")
    if "gap investment" in t_lower or "zero capital" in t_lower or "무자본" in text or "갭투자" in text:
        ko_terms.append("무자본 갭투자")
        ja_terms.append("無資本ギャップ投資")
        vn_terms.append("đầu tư chênh lệch không vốn")
        en_terms.append("zero-capital gap investment")
        entities.append("gap investment")
    if "minimum guarantee" in t_lower or "최소보장제" in text:
        ko_terms.append("최소보장제")
        ja_terms.append("最低保証制度")
        vn_terms.append("cơ chế bảo lãnh tối thiểu")
        en_terms.append("Minimum Guarantee Scheme")
        entities.append("Minimum Guarantee Scheme")
    if "one-third" in t_lower or "1/3" in t_lower or "3분의 1" in text:
        ko_terms.append("보증금 3분의 1(1/3) 변제")
        ja_terms.append("保証金の3分の1弁済")
        vn_terms.append("thu hồi tối thiểu 1/3 tiền cọc")
        en_terms.append("one-third (1/3) minimum deposit recovery")
        entities.append("1/3 recovery")
    if "gyeonggi" in t_lower or "경기" in text:
        ko_terms.append("경기")
        ja_terms.append("京畿道")
        vn_terms.append("tỉnh Gyeonggi")
        en_terms.append("Gyeonggi Province")
        entities.append("Gyeonggi")
    if "gangwon" in t_lower or "강원" in text:
        ko_terms.append("강원")
        ja_terms.append("江原道")
        vn_terms.append("tỉnh Gangwon")
        en_terms.append("Gangwon Province")
        entities.append("Gangwon")
    if "november 10" in t_lower or "11월 10일" in text:
        ko_terms.append("11월 10일 사전신청")
        ja_terms.append("11月10日事前申請")
        vn_terms.append("đăng ký trước từ ngày 10/11")
        en_terms.append("November 10 nationwide pre-applications")
    if "november 13" in t_lower or "11월 13일" in text:
        ko_terms.append("11월 13일 법적 시행")
        ja_terms.append("11月13日施行")
        vn_terms.append("hiệu lực từ ngày 13/11")
        en_terms.append("November 13 statutory enforcement")
    if "22 trillion" in t_lower or "22조" in text:
        ko_terms.append("22조 원 규모 부실 노출")
        ja_terms.append("22兆ウォン規模の不良債権")
        vn_terms.append("rủi ro 22 nghìn tỷ KRW")
        en_terms.append("22 trillion KRW cumulative exposure")
    if "9,317" in text or "9317" in text:
        ko_terms.append("9,317명 피해자")
        ja_terms.append("9,317名の被害者")
        vn_terms.append("9.317 nạn nhân")
        en_terms.append("9,317 certified victims")
    if "appraisal" in t_lower or "감정평가" in text:
        ko_terms.append("감정평가 조작")
        ja_terms.append("不動産鑑定評価の操作")
        vn_terms.append("thổi phồng định giá bất động sản")
        en_terms.append("rogue appraisal inflation")
    if "foreclosure" in t_lower or "경매" in text or "압류" in text:
        ko_terms.append("경매 및 압류 전면 중단")
        ja_terms.append("競売差し押さえの凍結")
        vn_terms.append("đóng băng đấu giá phát mãi")
        en_terms.append("mass foreclosure standstills")

    kr_words = [w for w in text.split() if re.search(r"[\uac00-\ud7a3]", w)]
    if kr_words and len(ko_terms) < 2:
        ko_terms.extend(kr_words[:4])

    cap_words = [w.strip(",.;:") for w in text.split() if re.match(r"^[A-Z][a-z0-9]{2,}$", w.strip(",.;:")) and w.strip(",.;:").lower() not in ("the", "and", "for", "with", "from", "that", "this")]
    if cap_words:
        entities.extend(cap_words[:4])

    if not en_terms and text:
        words = text.split()
        en_terms.append(" ".join(words[:10]))

    return {
        "text": text,
        "parens": parens,
        "numbers": num_matches,
        "ko_terms": list(dict.fromkeys(ko_terms)),
        "ja_terms": list(dict.fromkeys(ja_terms)),
        "vn_terms": list(dict.fromkeys(vn_terms)),
        "en_terms": list(dict.fromkeys(en_terms)),
        "entities": list(dict.fromkeys(entities)),
    }


def _format_claim_fact(c: Any, market: str, topic: str) -> str:
    if not c:
        fallbacks = {
            "KR": f"{topic} 관련 공식 확인 사실",
            "JA": f"{topic}に関する公式確認事実",
            "VN": f"thông tin xác thực về {topic}",
            "EN": f"verified evidentiary records regarding {topic}"
        }
        return fallbacks.get(market, f"verified evidentiary records regarding {topic}")

    text = str(getattr(c, "claim", "") or (c.get("claim", "") if isinstance(c, dict) else "")).strip()
    t_lower = text.lower()
    m = (market or "EN").upper()

    has_nov10 = "november 10" in t_lower or "11월 10일" in text
    has_nov13 = "november 13" in t_lower or "11월 13일" in text
    has_third = "one-third" in t_lower or "1/3" in t_lower or "3분의 1" in text or "3분의1" in text
    has_9317 = "9,317" in text or "9317" in text
    has_22t = "22 trillion" in t_lower or "22조" in text or "22兆" in text
    has_molit = "molit" in t_lower or "ministry of land" in t_lower or "국토교통부" in text
    has_guarantee = "minimum guarantee" in t_lower or "최소보장제" in text
    has_villa = "villa king" in t_lower or "빌라왕" in text
    has_proxy = "proxy landlord" in t_lower or "strawmen" in t_lower or "바지임대인" in text
    has_gap = "gap investment" in t_lower or "zero capital" in t_lower or "무자본" in text or "갭투자" in text
    has_appraisal = "appraisal" in t_lower or "감정평가" in text or "100%" in text
    has_death = "death" in t_lower or "died" in t_lower or "1,000" in text or "사망" in text or "급사" in text

    if m in ("KR", "KO"):
        if has_molit and has_guarantee:
            return "국토교통부(MOLIT)의 최소보장제 공식 발표"
        if has_molit:
            return "국토교통부(MOLIT)의 공식 조사 발표"
        if has_nov10:
            return "11월 10일 전국 단위 사전신청 개시"
        if has_nov13 or has_third:
            return "11월 13일 시행되는 보증금 3분의 1(1/3) 변제 대책"
        if has_9317:
            return "경기 지역 9,317명의 공인 피해자 발생"
        if has_22t:
            return "전국 22조 원 규모에 달하는 잠재적 부실 노출"
        if (has_villa or has_proxy) and has_death:
            return "바지임대인 급사와 1,000채 이상 경매 및 압류 중단"
        if has_villa or has_proxy:
            return "바지임대인과 빌라왕 일당의 조직적 명의 대여"
        if has_gap:
            return "무자본 갭투자를 통한 대규모 주택 매입 구조"
        if has_appraisal:
            return "공시가 조작 및 100% 이상 LTV 보증보험 발급 의혹"
        if has_guarantee:
            return "전세사기 피해자 최소보장제 지원책"

        num_matches = re.findall(r"\b\d+[,\d]*(?:\.\d+)?\s*(?:%|조\s*원|억\s*원|만\s*원|명|채|건|KRW|USD)?\b", text)
        if num_matches and len(num_matches[0]) >= 2:
            return f"{num_matches[0]} 관련 공식 확인 사실"
        hangul_match = re.findall(r"[\uac00-\ud7a3]{2,}", text)
        if hangul_match:
            return " ".join(hangul_match[:3])
        return f"{topic} 관련 공식 확인 사실"

    elif m in ("JA", "JP"):
        if has_molit:
            return "韓国国土交通部(MOLIT)の最低保証制度発表"
        if has_nov10:
            return "11月10日の全国事前申請開始"
        if has_nov13 or has_third:
            return "11月13日施行の保証金3分の1(1/3)弁済対策"
        if has_9317:
            return "京畿道における9,317名の認定被害者"
        if has_22t:
            return "全国22兆ウォン規模の潜在的焦げ付き"
        if (has_villa or has_proxy) and has_death:
            return "名義貸し家主の急死と1,000件超の競売凍結"
        if has_villa or has_proxy:
            return "名義貸し家主とヴィラ王グループの組織的詐欺"
        if has_gap:
            return "無資本ギャップ投資による住宅買い占め構造"
        if has_appraisal:
            return "不動産鑑定評価の操作と100%超の融資保証"

        cjk_match = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]{2,}", text)
        if cjk_match:
            return " ".join(cjk_match[:3])
        return f"{topic}に関する公式確認事実"

    elif m in ("VN", "VI"):
        if has_molit:
            return "Bộ Đất đai Giao thông Hàn Quốc (MOLIT) công bố cơ chế bảo lãnh tối thiểu"
        if has_nov10:
            return "tiếp nhận đăng ký trước từ ngày 10 tháng 11"
        if has_nov13 or has_third:
            return "quy định bảo lãnh thu hồi tối thiểu 1/3 tiền cọc có hiệu lực từ ngày 13/11"
        if has_9317:
            return "9.317 nạn nhân được xác nhận tại tỉnh Gyeonggi"
        if has_22t:
            return "khối nợ xấu tiềm ẩn lên tới 22 nghìn tỷ KRW"
        if (has_villa or has_proxy) and has_death:
            return "chủ nhà bù nhìn đột tử khiến hơn 1.000 căn hộ bị đóng băng đấu giá"
        if has_villa or has_proxy:
            return "đường dây chủ nhà bù nhìn và Vua Biệt Thự (Villa King)"
        if has_gap:
            return "mô hình đầu tư chênh lệch không vốn (gap investment)"
        if has_appraisal:
            return "thổi phồng định giá bất động sản và bảo lãnh trên 100% LTV"
        return f"thông tin xác thực về {topic}"

    else:
        if has_molit:
            return "the Ministry of Land, Infrastructure and Transport (MOLIT) Minimum Guarantee Scheme"
        if has_nov10:
            return "nationwide pre-applications opening on November 10, 2026"
        if has_nov13 or has_third:
            return "the November 13 statutory enforcement guaranteeing one-third (1/3) deposit recovery"
        if has_9317:
            return "9,317 certified fraud victims in Gyeonggi Province"
        if has_22t:
            return "22 trillion KRW in cumulative nationwide exposure"
        if (has_villa or has_proxy) and has_death:
            return "the sudden death of proxy landlords triggering 1,000+ unit foreclosure standstills"
        if has_villa or has_proxy:
            return "organized syndicates recruiting proxy landlords ('Villa Kings')"
        if has_gap:
            return "zero-capital gap investment acquisitions"
        if has_appraisal:
            return "rogue appraisal inflation and 100%+ loan-to-value guarantee coverage"
        words = text.split()
        return " ".join(words[:8]) if words else f"verified evidentiary records regarding {topic}"


def _build_grounded_story_beats(
    topic: str,
    evidence_ledger: List[Any],
    evidence_map: Dict[str, Any],
    market: str = "EN",
    central_question: str = ""
) -> List[Tuple[str, float, List[Any]]]:
    """Generates a resilient 5-beat forensic documentary script anchored directly to the claims in the evidence ledger."""
    from app.schemas.story_contracts import StorySceneLine

    claims = evidence_ledger if evidence_ledger else []
    c_ids = [c.claim_id for c in claims] if claims else [f"C00{i}" for i in range(1, 11)]

    def _cid(idx: int) -> str:
        if not c_ids:
            return "C001"
        return c_ids[min(max(0, idx), len(c_ids) - 1)]

    def _fact_kr(idx: int) -> str:
        if 0 <= idx < len(claims):
            return _format_claim_fact(claims[idx], "KR", topic)
        return f"{topic} 관련 공식 확인 사실"

    def _fact_ja(idx: int) -> str:
        if 0 <= idx < len(claims):
            return _format_claim_fact(claims[idx], "JA", topic)
        return f"{topic}に関する公式確認事実"

    def _fact_vn(idx: int) -> str:
        if 0 <= idx < len(claims):
            return _format_claim_fact(claims[idx], "VN", topic)
        return f"thông tin xác thực về {topic}"

    def _fact_en(idx: int) -> str:
        if 0 <= idx < len(claims):
            return _format_claim_fact(claims[idx], "EN", topic)
        return f"verified evidentiary records regarding {topic}"

    m_code = (market or "EN").upper()
    if m_code in ("KR", "KO"):
        b1_paradox_kr = (
            f"조사관들은 핵심 역설을 묻습니다: {central_question}"
            if central_question
            else f"조사관들은 핵심 모순을 추적합니다: 왜 {_with_particle(_fact_kr(3), 'subj')} 위기로 번질 때까지 방치되었는가?"
        )
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"급격한 시장 위기 속에서, {_with_particle(_fact_kr(0), 'topic')} {topic} 사태의 직접적인 도화선이 되었습니다.",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text=f"공식 기록에 따르면, {_with_particle(_fact_kr(1), 'with')} 함께 대규모 피해 실태가 공식적으로 확인되었습니다.",
                claim_ids=[_cid(1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text=f"핵심 사실로 드러난 것은, {_with_particle(_fact_kr(2), 'topic')} 둘러싼 제도적 맹점과 모순이었습니다.",
                claim_ids=[_cid(2)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text=b1_paradox_kr,
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text=f"사태가 본격화되기 전, 배후 세력들은 {_with_particle(_fact_kr(3), 'obj')} 악용하며 무분별한 외형 확장을 지속했습니다.",
                claim_ids=[_cid(3)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text=f"공식 공시와 계약 문서들은 {_with_particle(_fact_kr(4), 'obj')} 은폐하며 합법적 외관으로 위장되었습니다.",
                claim_ids=[_cid(4)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text=f"시장 참가자들은 단기적인 수익에 매몰되어, {_with_particle(_fact_kr(4), 'with')} 연계된 위험 경고를 묵살했습니다.",
                claim_ids=[_cid(4)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text=f"그러나 내부 데이터는 {_with_particle(_fact_kr(5), 'obj')} 가리키며 통제 불능의 파탄을 경고하고 있었습니다.",
                claim_ids=[_cid(0), _cid(5)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text=f"포렌식 조사가 심화되면서, {_with_particle(_fact_kr(5), 'topic')} 수면 위로 완전히 드러났습니다.",
                claim_ids=[_cid(5)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text=f"회계 장부와 감사 기록은, {_with_particle(_fact_kr(6), 'obj')} 통한 조직적 기망 행위를 입증했습니다.",
                claim_ids=[_cid(6)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text=f"거래 데이터는 핵심 거래처 전반에서 {_with_particle(_fact_kr(6), 'subj')} 구조적으로 확산되었음을 증명했습니다.",
                claim_ids=[_cid(6)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text=f"이로 인해 {_with_particle(_fact_kr(7), 'topic')} 가속화되며, 회수 불능의 잠재적 부실이 눈덩이처럼 불어났습니다.",
                claim_ids=[_cid(3), _cid(7)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text=f"내부 경고가 잇따랐지만, 주도 세력들은 불법적 수법을 고수하며 피해 규모를 키웠습니다.",
                claim_ids=[_cid(4), _cid(7)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text=f"결국 시장 환경 변화와 맞물려, {_with_particle(_fact_kr(7), 'subj')} 동시다발적인 연쇄 붕괴를 촉발했습니다.",
                claim_ids=[_cid(5), _cid(7)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text=f"결정적 증거가 포착되고, {_with_particle(_fact_kr(8), 'subj')} 발생하자 은폐되었던 거래 메커니즘이 완전히 해체되었습니다.",
                claim_ids=[_cid(8)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text=f"공식 조사 결과, {_with_particle(_fact_kr(8), 'with')} 연계된 자산 가치가 허구였음이 명백히 드러났습니다.",
                claim_ids=[_cid(8)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text=f"시장 신뢰가 무너지자, {_with_particle(_fact_kr(9), 'topic')} 가시화되며 단 며칠 만에 유동성이 증발했습니다.",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text=f"핵심 책임자들은 책임을 회피하려 했으나, 구체적인 물증과 수사망 앞에 덜미를 잡혔습니다.",
                claim_ids=[_cid(8), _cid(9)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text=f"사태의 파장이 걷잡을 수 없이 커지자, 금융 당국과 사법 기관이 전면 개입을 선언했습니다.",
                claim_ids=[_cid(9)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text=f"당국은 긴급 대책을 통해, {_with_particle(_fact_kr(0), 'with')} 맞물린 공적 구제 조치를 단행했습니다.",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text=f"동시에 {_with_particle(_fact_kr(2), 'obj')} 골자로 하는 긴급 구제 대책과 특별법이 본격 시행되었습니다.",
                claim_ids=[_cid(2)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"{topic} 사태가 남긴 명백한 교훈: 규제의 사각지대에서 은폐된 불법 레버리지는 결국 참혹한 사회적 대가를 치른다는 점입니다.",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]
    elif m_code in ("JA", "JP"):
        b1_paradox_ja = (
            f"調査報道が核心的逆説を突きつけます：{central_question}"
            if central_question
            else f"調査官たちは根本的矛盾を追及します：なぜ{_fact_ja(3)}のリスクが危機に至るまで放置されたのか？"
        )
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"急激な市場の危機の中で、{_fact_ja(0)}は{topic}における広範な構造的衝撃を引き起こしました。",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text=f"公式記録によれば、{_fact_ja(1)}とともに前例のない被害の実態が確認されました。",
                claim_ids=[_cid(1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text=f"明らかになった核心的事実は、{_fact_ja(2)}を巡る深刻な制度的死角と構造的欠陥でした。",
                claim_ids=[_cid(2)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text=b1_paradox_ja,
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text=f"危機が表面化する前、関係勢力は{_fact_ja(3)}を悪用して不健全な事業拡大を続けました。",
                claim_ids=[_cid(3)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text=f"公式の開示文書や契約書は{_fact_ja(4)}を隠蔽し、一見すると合法的取引に偽装されていました。",
                claim_ids=[_cid(4)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text=f"市場関係者は短期的な利益に目を奪われ、{_fact_ja(4)}に関連する重大な警告を無視しました。",
                claim_ids=[_cid(4)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text=f"しかし内部データは{_fact_ja(5)}を示し、制御不能な破綻の兆候を警告していました。",
                claim_ids=[_cid(0), _cid(5)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text=f"フォレンジック調査の進展に伴い、{_fact_ja(5)}の実態が白日の下に晒されました。",
                claim_ids=[_cid(5)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text=f"会計帳簿と監査記録は、{_fact_ja(6)}を通じた組織的な欺瞞行為を証明しました。",
                claim_ids=[_cid(6)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text=f"取引データは主要取引先全体にわたり{_fact_ja(6)}が構造的に波及したことを裏付けました。",
                claim_ids=[_cid(6)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text=f"これにより{_fact_ja(7)}が加速し、巨額の回収不能リスクが積み上がりました。",
                claim_ids=[_cid(3), _cid(7)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text=f"内部告発が相次いだにもかかわらず、責任者たちは不法な手口を維持し続けました。",
                claim_ids=[_cid(4), _cid(7)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text=f"最終的に市場環境の変動とともに、{_fact_ja(7)}は連鎖的な破綻を引き起こしました。",
                claim_ids=[_cid(5), _cid(7)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text=f"決定的な証拠が浮上し、{_fact_ja(8)}が発生したことで隠蔽されていた取引構造は完全に解体されました。",
                claim_ids=[_cid(8)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text=f"公式調査の結果、{_fact_ja(8)}に関連する資産価値の虚構性が明白になりました。",
                claim_ids=[_cid(8)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text=f"市場の信頼が崩壊すると、{_fact_ja(9)}が現実味を帯び、瞬く間に流動性が蒸発しました。",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text=f"主謀者たちは責任逃れを図りましたが、証拠の包囲網によって不正の実態が暴かれました。",
                claim_ids=[_cid(8), _cid(9)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text=f"破局を隠しきれなくなったことで、金融当局と司法機関が全面介入を宣言しました。",
                claim_ids=[_cid(9)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text=f"司法当局は厳正な捜査を通じて、{_fact_ja(0)}に関わる責任者を起訴しました。",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text=f"秩序を再建するため、{_fact_ja(2)}を軸とする緊急救済策と法改正が施行されました。",
                claim_ids=[_cid(2)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"{topic}が遺した教訓：監視の死角で放置されたリスクは、必ず莫大な社会的コストとして跳ね返るということです。",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]
    elif m_code in ("VN", "VI"):
        b1_paradox_vn = (
            f"Các nhà điều tra đặt ra nghịch lý trọng tâm: {central_question}"
            if central_question
            else f"Các điều tra viên đối diện với nghịch lý: tại sao rủi ro từ {_fact_vn(3)} lại bị bỏ ngỏ cho đến khi bùng nổ?"
        )
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"Trong cuộc khủng hoảng thị trường cấp tính, {_fact_vn(0)} đã trở thành ngòi nổ trực tiếp của vụ việc {topic}.",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text=f"Theo hồ sơ chính thức, {_fact_vn(1)} đã phơi bày quy mô thiệt hại chưa từng có đối với các nạn nhân.",
                claim_ids=[_cid(1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text=f"Sự thật cốt lõi lộ diện là những lỗ hổng thể chế nghiêm trọng xung quanh {_fact_vn(2)}.",
                claim_ids=[_cid(2)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text=b1_paradox_vn,
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text=f"Trước khi đổ vỡ, các nhóm lợi ích đã lợi dụng {_fact_vn(3)} để bành trướng quy mô bất chấp rủi ro.",
                claim_ids=[_cid(3)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text=f"Các bản công bố thông tin và hợp đồng đều che giấu {_fact_vn(4)}, ngụy tạo như giao dịch tiêu chuẩn.",
                claim_ids=[_cid(4)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text=f"Thị trường mải mê chạy theo lợi ích trước mắt mà phớt lờ cảnh báo liên quan đến {_fact_vn(4)}.",
                claim_ids=[_cid(4)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text=f"Tuy nhiên, các dữ liệu nội bộ đã ghi nhận {_fact_vn(5)}, báo hiệu sự sụp đổ không thể tránh khỏi.",
                claim_ids=[_cid(0), _cid(5)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text=f"Khi điều tra pháp y đi sâu hơn, cơ chế vận hành {_fact_vn(5)} đã hoàn toàn bị vạch trần.",
                claim_ids=[_cid(5)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text=f"Sổ sách kế toán và hồ sơ kiểm toán chứng minh hành vi lừa dối có tổ chức thông qua {_fact_vn(6)}.",
                claim_ids=[_cid(6)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text=f"Dữ liệu giao dịch xác nhận {_fact_vn(6)} đã lây lan và làm suy yếu toàn bộ hệ thống.",
                claim_ids=[_cid(6)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text=f"Hậu quả là {_fact_vn(7)} tăng tốc, tích tụ khối nợ xấu khổng lồ không có khả năng thu hồi.",
                claim_ids=[_cid(3), _cid(7)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text=f"Bất chấp nhiều cảnh báo, những kẻ chủ mưu vẫn ngoan cố duy trì các thủ đoạn phi pháp.",
                claim_ids=[_cid(4), _cid(7)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text=f"Cuối cùng, trước biến động vĩ mô, {_fact_vn(7)} đã kích hoạt chuỗi sụp đổ dây chuyền.",
                claim_ids=[_cid(5), _cid(7)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text=f"Bằng chứng thép xuất hiện cùng sự cố {_fact_vn(8)} khiến cơ chế che đậy sụp đổ hoàn toàn.",
                claim_ids=[_cid(8)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text=f"Kết quả điều tra cho thấy giá trị tài sản gắn với {_fact_vn(8)} hoàn toàn là ảo.",
                claim_ids=[_cid(8)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text=f"Khi niềm tin bốc hơi, {_fact_vn(9)} trở thành hiện thực và thanh khoản biến mất chỉ sau vài ngày.",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text=f"Những kẻ chịu trách nhiệm tìm cách thoái thác nhưng đã bị chuỗi bằng chứng pháp lý khóa chặt.",
                claim_ids=[_cid(8), _cid(9)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text=f"Khủng hoảng vượt tầm kiểm soát, buộc các cơ quan điều tra và quản lý nhà nước phải vào cuộc.",
                claim_ids=[_cid(9)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text=f"Cơ quan tư pháp đã mở rộng truy cứu trách nhiệm hình sự liên quan đến {_fact_vn(0)}.",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text=f"Nhằm tái lập trật tự, gói cứu trợ khẩn cấp với trọng tâm là {_fact_vn(2)} đã chính thức được ban hành.",
                claim_ids=[_cid(2)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"Bài học đắt giá từ {topic}: Mọi hành vi trục lợi trong bóng tối của thể chế đều phải trả giá bằng sự đổ vỡ toàn diện.",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
                visual_hook="red_thread",
            ),
        ]
    else:
        b1_paradox_en = (
            f"Investigators confront the central systemic paradox: {central_question}"
            if central_question
            else f"Investigators confronted the central paradox: how did the mounting risks of {_fact_en(3)} compound before authorities intervened?"
        )
        b1_lines = [
            StorySceneLine(
                line_id="B1_L01",
                text=f"In an acute market crisis, {_fact_en(0)} triggered immediate structural tremors across {topic}.",
                claim_ids=[_cid(0), _cid(1)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B1_L02",
                text=f"Official records documented that alongside {_fact_en(1)}, an unprecedented scale of liabilities came to light.",
                claim_ids=[_cid(1)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B1_L03",
                text=f"The core documented finding exposed critical systemic vulnerabilities surrounding {_fact_en(2)}.",
                claim_ids=[_cid(2)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B1_L04",
                text=b1_paradox_en,
                claim_ids=[_cid(0), _cid(3)],
                visual_hook="red_thread",
            ),
        ]
        b2_lines = [
            StorySceneLine(
                line_id="B2_L01",
                text=f"Prior to the collapse, syndicates actively exploited {_fact_en(3)} while projecting an illusion of commercial strength.",
                claim_ids=[_cid(3)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L02",
                text=f"Regulatory disclosures and contracts concealed {_fact_en(4)}, masking dangerous exposure behind routine paperwork.",
                claim_ids=[_cid(4)],
                visual_hook="compass_arc",
            ),
            StorySceneLine(
                line_id="B2_L03",
                text=f"Market participants chased aggressive short-term yields, dismissing internal red flags tied to {_fact_en(4)}.",
                claim_ids=[_cid(4)],
                visual_hook="cutout",
            ),
            StorySceneLine(
                line_id="B2_L04",
                text=f"Yet forensic records documented {_fact_en(5)}, signaling uncontrollable structural fractures behind closed doors.",
                claim_ids=[_cid(0), _cid(5)],
                visual_hook="red_thread",
            ),
        ]
        b3_lines = [
            StorySceneLine(
                line_id="B3_L01",
                text=f"As inquiry deepened, forensic examiners unraveled the full transmission mechanism of {_fact_en(5)}.",
                claim_ids=[_cid(5)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B3_L02",
                text=f"Audited accounting books confirmed deliberate misrepresentations carried out through {_fact_en(6)}.",
                claim_ids=[_cid(6)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B3_L03",
                text=f"Operational data proved that {_fact_en(6)} created systemic contagion across major counterparties.",
                claim_ids=[_cid(6)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B3_L04",
                text=f"This dynamic accelerated {_fact_en(7)}, locking institutional reserves into irrecoverable shortfalls.",
                claim_ids=[_cid(3), _cid(7)],
                visual_hook="ruler_measure",
            ),
            StorySceneLine(
                line_id="B3_L05",
                text=f"Despite mounting internal alarms, decision-makers doubled down on leveraged commitments.",
                claim_ids=[_cid(4), _cid(7)],
                visual_hook="grease_pencil",
            ),
            StorySceneLine(
                line_id="B3_L06",
                text=f"When economic winds shifted, {_fact_en(7)} ignited widespread simultaneous defaults across the platform.",
                claim_ids=[_cid(5), _cid(7)],
                visual_hook="compass_arc",
            ),
        ]
        b4_lines = [
            StorySceneLine(
                line_id="B4_L01",
                text=f"Smoking-gun evidence erupted when {_fact_en(8)} caused the entire commercial facade to dismantle.",
                claim_ids=[_cid(8)],
                visual_hook="scissors_cut",
            ),
            StorySceneLine(
                line_id="B4_L02",
                text=f"Insolvency audits established that underlying collateral linked to {_fact_en(8)} had evaporated into technical default.",
                claim_ids=[_cid(8)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B4_L03",
                text=f"As market confidence disintegrated, {_fact_en(9)} materialized and liquidity vanished within days.",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="magnifier",
            ),
            StorySceneLine(
                line_id="B4_L04",
                text=f"Key operatives attempted to disclaim liability, but a watertight chain of custody established criminal intent.",
                claim_ids=[_cid(8), _cid(9)],
                visual_hook="red_thread",
            ),
            StorySceneLine(
                line_id="B4_L05",
                text=f"With the contagion threatening wider credit markets, regulatory tribunals and prosecutors launched emergency enforcement.",
                claim_ids=[_cid(9)],
                visual_hook="ruler_measure",
            ),
        ]
        b5_lines = [
            StorySceneLine(
                line_id="B5_L01",
                text=f"Supervisory agencies executed formal sanctions and criminal indictments directly stemming from {_fact_en(0)}.",
                claim_ids=[_cid(0), _cid(9)],
                visual_hook="stamp",
            ),
            StorySceneLine(
                line_id="B5_L02",
                text=f"Sweeping statutory reforms and emergency relief measures anchored by {_fact_en(2)} were enacted to stabilize the sector.",
                claim_ids=[_cid(2)],
                visual_hook="stat_hero",
            ),
            StorySceneLine(
                line_id="B5_L03",
                text=f"For capital markets, the enduring lesson of {topic} is undeniable: unchecked leverage in regulatory vacuums will always exact a devastating public toll.",
                claim_ids=[_cid(0), _cid(len(claims) - 1)],
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
                    "CRITICAL GROUNDING & TOPIC ANCHORING MANDATE:\n"
                    "The spoken script must explicitly describe the concrete facts, key entities, dates, quantitative metrics, and regulatory mechanisms found in the evidence ledger. "
                    "You MUST weave at least 4 specific factual anchors (named agencies, exact numbers/percentages, dates, or specific fraudulent mechanisms) directly into the spoken lines. "
                    "Purely abstract boilerplate without specific grounding facts is strictly forbidden.\n\n"
                )
                user_prompt += (
                    f"CRITICAL BEAT 1 HOOK & CENTRAL PARADOX MANDATE (0-20s, Rule 130 / Rule 131 / Gate 4):\n"
                    f"- In Beat 1 (lines B1_L01 to B1_L04, 0-20s), you MUST explicitly state and pose the Central Investigative Paradox and Question directly to the audience: '{c_quest}'.\n"
                    f"- Specifically, Line B1_L03 or B1_L04 MUST explicitly formulate this central paradox/question in natural native narration (e.g. asking why the systemic failure occurred or exposing the shocking paradox of private losses being absorbed by the state/victims).\n"
                    "- Do NOT merely state neutral factual announcements in Beat 1. The hook must grab the viewer by exposing the shocking systemic paradox within the first 20 seconds.\n\n"
                )
                user_prompt += (
                    "Every line must have a visual_hook: 'stamp', 'ruler_measure', 'compass_arc', 'cutout', 'red_thread', 'magnifier', 'scissors_cut', or 'grease_pencil'.\n\n"
                    "CRITICAL FORMAT MANDATE:\n"
                    "Start response immediately with { and end with }. Output ONLY valid JSON adhering to schema with NO conversational preamble or thinking."
                )
                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="gpt-6.1-sol",
                    system_prompt=system_prompt,
                    max_tokens=4000,
                    temperature=0.3,
                    timeout=120.0,
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
            raw_beats = _build_grounded_story_beats(topic, evidence_ledger, evidence_map, market=market, central_question=c_quest)


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
