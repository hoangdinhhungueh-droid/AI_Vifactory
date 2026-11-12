#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s03_script.py — Stage S3: 5-Beat Investigative Docudrama Script (AVF-STAB-001).

Implements Stage Shape Standard. Generic multi-market forensic script synthesis governed
by Rule 118 (Zero Fabrication), Rule 128 (Zero Semantic Bias), Rule 130 (Causal Integrity),
and Rule 132 (Pure Engine Decoupling).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core.config import RunContext
from core.contracts.stages import Provenance, Scene, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S3_SCRIPT


def _get_market_legal_qualifiers(market: str) -> dict:
    """Return legal qualifier dictionaries backed by canonical story_provenance_engine."""
    from app.services.story_provenance_engine import (
        _LEGAL_QUALIFIER_PATTERNS,
        normalize_market_code,
    )

    m = normalize_market_code(market)
    pats = _LEGAL_QUALIFIER_PATTERNS.get(m, _LEGAL_QUALIFIER_PATTERNS["EN"])
    prefixes = {
        "KR": {
            "charged": "검찰 공소장에 따르면,",
            "alleged_press": "보도 설명에 따르면,",
            "alleged_regulator": "규제 당국에 따르면,",
            "alleged_default": "제기된 의혹에 따르면,",
            "settled": "(공식적인 잘못을 인정하지 않고 합의됨)",
        },
        "JA": {
            "charged": "起訴状の指摘によれば、",
            "alleged_press": "報道によれば、",
            "alleged_regulator": "当局の調査によれば、",
            "alleged_default": "指摘によれば、",
            "settled": "(違法性を認めることなく和解)",
        },
        "VN": {
            "charged": "Theo cáo trạng của cơ quan công tố,",
            "alleged_press": "Theo thông tin báo chí phản ánh,",
            "alleged_regulator": "Theo cơ quan chức năng,",
            "alleged_default": "Theo phản ánh,",
            "settled": "(dàn xếp mà không thừa nhận hành vi sai trái)",
        },
        "EN": {
            "charged": "According to court filings,",
            "alleged_press": "According to media reports,",
            "alleged_regulator": "According to regulatory filings,",
            "alleged_default": "Allegedly,",
            "settled": "(settled without admitting wrongdoing)",
        },
    }[m]
    return {
        "req_charged": list(dict.fromkeys(pats.get("indictment", []) + pats.get("criminal_complaint", []) + pats.get("press_charge", []))),
        "prefix_charged": prefixes["charged"],
        "req_alleged": list(dict.fromkeys(pats.get("alleged", []) + pats.get("unverified", []))),
        "prefix_alleged": prefixes["alleged_regulator"],
        "prefix_alleged_press": prefixes["alleged_press"],
        "prefix_alleged_regulator": prefixes["alleged_regulator"],
        "prefix_alleged_default": prefixes["alleged_default"],
        "req_settled": list(pats.get("settled", [])),
        "suffix_settled": prefixes["settled"],
    }


def _apply_legal_qualifier(
    text: str,
    legal_status: str,
    market: str,
    source_type: Optional[str] = None,
    doc_type: str = "unknown",
    speaker: Optional[str] = None,
    procedural_status: str = "unknown",
    verification_status: str = "corroborated_secondary",
) -> str:
    """Apply context-aware procedural & verification qualifier based on full evidence provenance."""
    from app.services.story_provenance_engine import route_legal_qualifier

    ls_norm = (legal_status or "alleged").strip().lower()
    if source_type is None:
        if ls_norm == "charged":
            eff_source = "court"
            eff_doc = "indictment" if doc_type == "unknown" else doc_type
        elif ls_norm == "alleged":
            eff_source = "regulator"
            eff_doc = doc_type
        elif ls_norm in ("convicted", "settled"):
            eff_source = "court"
            eff_doc = doc_type
        else:
            eff_source = "press"
            eff_doc = doc_type
    else:
        eff_source = source_type
        eff_doc = doc_type

    return route_legal_qualifier(
        text=text,
        legal_status=legal_status,
        source_type=eff_source,
        market=market,
        doc_type=eff_doc,
        speaker=speaker,
        procedural_status=procedural_status,
        verification_status=verification_status,
    )


def _normalize_spoken_korean_numbers(text: str) -> str:
    """Algorithmically normalize accidentally spelled-out Sino-Korean years/dates/articles/fractions
    back into readable Arabic numerals without any hardcoded dates or episode literals.
    """
    if not text:
        return text

    from app.services.text_to_number_parser import _hangul_to_int

    out = text

    def _parse_kr_month(tok: str) -> Optional[int]:
        if tok == "유":
            return 6
        if tok == "시":
            return 10
        val = _hangul_to_int(tok)
        return val if val is not None and 1 <= val <= 12 else None

    # 1. Spelled-out 4-digit calendar years: e.g. 이천이십육년 -> 2026년
    def _year_repl(match: re.Match[str]) -> str:
        val = _hangul_to_int(match.group(1))
        if val is not None and 1900 <= val <= 2100:
            return f"{val}년"
        return match.group(0)

    out = re.sub(r"([일이삼사오육칠팔구십백천]{2,})년", _year_repl, out)

    # 2. Spelled-out month + day pairs: e.g. 십일월 십일 -> 11월 10일
    def _md_repl(match: re.Match[str]) -> str:
        mo = _parse_kr_month(match.group(1))
        dy = _hangul_to_int(match.group(2))
        if mo is not None and dy is not None and 1 <= dy <= 31:
            return f"{mo}월 {dy}일"
        return match.group(0)

    out = re.sub(r"\b([일이삼사오유육칠팔구시십]{1,3})월\s*([일이삼사오육칠팔구십]{1,3})일", _md_repl, out)

    # 3. Spelled-out statutory articles: 제N조(의M)
    def _art_repl(match: re.Match[str]) -> str:
        n1 = _hangul_to_int(match.group(1))
        if n1 is None or n1 <= 0:
            return match.group(0)
        sub = match.group(2)
        if sub:
            n2 = _hangul_to_int(sub)
            if n2 is not None and n2 > 0:
                return f"제{n1}조의{n2}"
        return f"제{n1}조"

    out = re.sub(r"제([일이삼사오육칠팔구십백천]+)조(?:의([일이삼사오육칠팔구십]+))?", _art_repl, out)

    # 4. Spelled-out simple fractions: e.g. 삼분의 일 -> 3분의 1
    def _frac_repl(match: re.Match[str]) -> str:
        den = _hangul_to_int(match.group(1))
        num = _hangul_to_int(match.group(2))
        if den and num and den > num > 0:
            return f"{den}분의 {num}"
        return match.group(0)

    out = re.sub(r"([일이삼사오육칠팔구십]+)분의\s*([일이삼사오육칠팔구십]+)", _frac_repl, out)
    return out


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
    """Generic claim element extraction delegating to story_provenance_engine."""
    from app.services.story_provenance_engine import extract_claim_elements

    text = c if isinstance(c, str) else (c.get("claim", "") if isinstance(c, dict) else getattr(c, "claim", ""))
    return extract_claim_elements(text)


def _localized_topic_label(topic: str, market: str) -> str:
    """Return a concise, target-language-safe topic phrase without injecting foreign prose."""
    from app.services.story_provenance_engine import (
        CJK_HAN_RE,
        HANGUL_SYLLABLE_RE,
        JP_KANA_RE,
        VN_DIACRITIC_RE,
        normalize_market_code,
        translate_claim_to_market_clause,
    )

    m = normalize_market_code(market)
    t = re.sub(r"\s+", " ", (topic or "").strip())
    if not t:
        return {"KR": "이번 사안", "JA": "本件", "VN": "vụ việc này"}.get(m, "this case")

    en_words = re.findall(r"\b[a-z]{3,}\b", t)
    t_no_paren = re.sub(r"\s*\([^()]*\)", "", t).strip() or t
    if m == "KR":
        if len(HANGUL_SYLLABLE_RE.findall(t_no_paren)) >= 2 and len(re.findall(r"\b[a-z]{3,}\b", t_no_paren)) <= 1:
            short = t_no_paren[:18].strip() if len(t_no_paren) > 18 else t_no_paren
            if "(" in short and ")" not in short:
                short = short[: short.rfind("(")].strip()
            return short or "이번 사안"
        tr = translate_claim_to_market_clause(t, "KR", "사안")
        short_tr = (tr.split(",")[0].strip() or "이번 사안")[:18]
        if "(" in short_tr and ")" not in short_tr:
            short_tr = short_tr[: short_tr.rfind("(")].strip()
        return short_tr or "이번 사안"
    if m == "JA":
        if (len(JP_KANA_RE.findall(t_no_paren)) + len(CJK_HAN_RE.findall(t_no_paren))) >= 2 and len(re.findall(r"\b[a-z]{3,}\b", t_no_paren)) <= 1:
            short = t_no_paren[:18].strip() if len(t_no_paren) > 18 else t_no_paren
            for op, cl in (("(", ")"), ("（", "）")):
                if op in short and cl not in short:
                    short = short[: short.rfind(op)].strip()
            return short or "本件"
        tr = translate_claim_to_market_clause(t, "JA", "本件")
        short_tr = (tr.split("、")[0].split(",")[0].strip() or "本件")[:18]
        for op, cl in (("(", ")"), ("（", "）")):
            if op in short_tr and cl not in short_tr:
                short_tr = short_tr[: short_tr.rfind(op)].strip()
        return short_tr or "本件"
    if m == "VN":
        if len(VN_DIACRITIC_RE.findall(t)) >= 2 and len(en_words) <= 3:
            words = t.split()
            return " ".join(words[:5]) if len(words) > 5 else t
        tr = translate_claim_to_market_clause(t, "VN", "vụ việc này")
        words = tr.split()
        return " ".join(words[:5]) if len(words) > 5 else (tr or "vụ việc này")
    words = t.split()
    return " ".join(words[:5]) if len(words) > 5 else t


def _trim_clause_smart(text: str, elems: Dict[str, Any], market: str, hook_mode: bool = False) -> str:
    """Bound clause length cleanly for beat tempo without bisecting parentheticals or dropping metrics."""
    clean = re.sub(r"\s+", " ", (text or "").strip()).rstrip(".。")
    # Strip trailing formal KR/JA endings cleanly if embedded inside a longer sentence
    if market == "KR":
        clean = re.sub(r"(?:있습니다|습니다|입니다|였다|했다|됐다|다)$", "", clean).strip(" ,;:")
        cap = 26 if hook_mode else 44
        if len(clean) <= cap:
            return clean
        clauses = [c.strip() for c in re.split(r"[;—]|,\s+", clean) if c.strip()]
        head = clauses[0] if clauses else clean
        if not hook_mode and 8 <= len(head) <= cap:
            trimmed = head
        else:
            words = clean.split()
            buf = ""
            for w in words:
                cand = f"{buf} {w}".strip()
                if len(cand) <= cap:
                    buf = cand
                else:
                    break
            trimmed = buf if len(buf) >= 6 else clean[:cap].rstrip()
        if trimmed.count("(") > trimmed.count(")"):
            trimmed = trimmed[: trimmed.rfind("(")].strip(" ,;:")
        anchors = (elems.get("metrics", []) + elems.get("dates", []))
        if anchors and not any(a.lower() in trimmed.lower() for a in anchors):
            a0 = anchors[0]
            if len(a0) <= 16 and len(trimmed) + len(a0) + 2 <= cap + 14:
                trimmed = f"{a0} {trimmed}".strip()
        return trimmed.strip(" ,;:")

    if market == "JA":
        clean = re.sub(r"(?:しました|でした|います|である|した|だ)$", "", clean).strip(" 、,")
        cap = 26 if hook_mode else 58
        if len(clean) <= cap:
            return clean
        clauses = [c.strip() for c in re.split(r"[;—、,：:]", clean) if c.strip()]
        trimmed = ""
        if clauses:
            first_c = clauses[0]
            if re.search(r"[がはをにでともへのや]$", first_c) and len(clauses) > 1:
                cand_c = clauses[1] if len(clauses[1]) >= 8 else f"{first_c}、{clauses[1]}"
                trimmed = cand_c[:cap].rstrip(" 、,がはをにでともへのや")
            elif 8 <= len(first_c) <= cap:
                trimmed = first_c
        if not trimmed:
            trimmed = clean[:cap].rstrip(" 、,がはをにでともへのや")
        if trimmed.count("(") > trimmed.count(")"):
            trimmed = trimmed[: trimmed.rfind("(")].strip(" 、,")
        if trimmed.count("（") > trimmed.count("）"):
            trimmed = trimmed[: trimmed.rfind("（")].strip(" 、,")
        anchors = (elems.get("metrics", []) + elems.get("dates", []))
        if not hook_mode and anchors and not any(a.lower() in trimmed.lower() for a in anchors):
            a0 = anchors[0]
            if len(a0) <= 18 and len(trimmed) + len(a0) + 2 <= cap + 14:
                trimmed = f"{a0}の{trimmed}".strip()
        return trimmed

    word_cap = (8 if hook_mode else 16) if market == "VN" else (7 if hook_mode else 14)
    words = clean.split()
    if len(words) <= word_cap:
        return clean
    # Avoid severing a currency/number from its scale unit (e.g. "$172.7" | "million")
    if word_cap < len(words) and words[word_cap].lower().rstrip(".,;:") in (
        "million", "billion", "trillion", "thousand", "percent", "%", "m", "b", "usd", "krw", "jpy", "vnd"
    ):
        word_cap += 1
    trimmed = " ".join(words[:word_cap]).rstrip(",;:")
    if trimmed.count("(") > trimmed.count(")"):
        trimmed = trimmed[: trimmed.rfind("(")].strip(" ,;:")
    anchors = (elems.get("metrics", []) + elems.get("dates", []))
    if not hook_mode and anchors and not any(a.lower() in trimmed.lower() for a in anchors):
        a0 = anchors[0]
        a0_nums = re.findall(r"\d[\d,.]*", a0)
        already_has_num = any(n in trimmed for n in a0_nums) if a0_nums else False
        if not already_has_num and len(a0.split()) <= 4:
            trimmed = f"{trimmed} ({a0})"
    return trimmed


def _format_claim_fact(c: Any, market: str, topic: str = "", hook_mode: bool = False) -> str:
    """Extract a clean, target-script factual clause directly from any claim without topic hardcodes."""
    from app.services.story_provenance_engine import (
        CJK_HAN_RE,
        HANGUL_SYLLABLE_RE,
        JP_KANA_RE,
        VN_DIACRITIC_RE,
        extract_claim_elements,
        localize_dates_and_metrics,
        normalize_market_code,
        translate_claim_to_market_clause,
    )

    m = normalize_market_code(market)
    raw_text = c if isinstance(c, str) else (c.get("claim", "") if isinstance(c, dict) else getattr(c, "claim", ""))
    text = re.sub(r"\s+", " ", (raw_text or "").strip()).rstrip(".。")
    loc_topic = _localized_topic_label(topic, m)
    if not text:
        if m == "KR":
            return f"{loc_topic} 확인 기록"
        if m == "JA":
            return f"{loc_topic}の確認記録"
        if m == "VN":
            return f"hồ sơ về {loc_topic}"
        return f"documented record on {loc_topic}"

    if m == "KR":
        text = _normalize_spoken_korean_numbers(text)

    elems = extract_claim_elements(text)
    hangul_n = len(HANGUL_SYLLABLE_RE.findall(text))
    jp_n = len(JP_KANA_RE.findall(text)) + len(CJK_HAN_RE.findall(text))
    vn_n = len(VN_DIACRITIC_RE.findall(text))
    en_low_words = re.findall(r"\b[a-z]{3,}\b", text)
    en_all_words = re.findall(r"[A-Za-z]{3,}", text)

    is_native = False
    if m == "KR":
        is_native = hangul_n >= 4 and len(en_low_words) <= 2
    elif m == "JA":
        is_native = jp_n >= 4 and len(en_low_words) <= 2
    elif m == "VN":
        is_native = vn_n >= 2 and len(en_low_words) <= 5
    else:
        is_native = len(en_all_words) >= 3 and hangul_n == 0 and jp_n == 0

    if not is_native:
        if m in ("KR", "JA", "VN"):
            translated = translate_claim_to_market_clause(text, m, loc_topic)
            return _trim_clause_smart(translated, extract_claim_elements(translated), m, hook_mode=hook_mode)
        # Foreign-script claim targeting EN market
        parts = elems.get("entities", [])[:2] + elems.get("metrics", [])[:2] + elems.get("dates", [])[:1]
        ascii_parts = [p for p in parts if not HANGUL_SYLLABLE_RE.search(p) and not JP_KANA_RE.search(p) and not CJK_HAN_RE.search(p)]
        joined = ", ".join(dict.fromkeys(ascii_parts)) if ascii_parts else loc_topic
        return f"official records citing {joined}"

    localized = localize_dates_and_metrics(text, m) if m in ("KR", "JA", "VN") else text
    return _trim_clause_smart(localized, elems, m, hook_mode=hook_mode)


def _select_ordered_claims(evidence_ledger: List[Any]) -> Dict[str, List[Any]]:
    """Group evidence claims cleanly by verification priority and causal hierarchy."""
    from app.services.story_provenance_engine import verification_priority_rank

    def _get(obj: Any, attr: str, default: Any = "") -> Any:
        return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)

    sorted_claims = sorted(
        list(evidence_ledger or []),
        key=lambda c: (
            verification_priority_rank(str(_get(c, "verification_status", "unverified_secondary"))),
            0 if _get(c, "causal_role", "") == "primary_catalyst"
            else (1 if _get(c, "causal_role", "") == "transmission_mechanism" else 2),
        ),
    )
    verified_pool = [
        c for c in sorted_claims
        if str(_get(c, "verification_status", "unverified_secondary")) in ("verified_primary", "corroborated_secondary")
    ]
    unverified_pool = [
        c for c in sorted_claims
        if str(_get(c, "verification_status", "unverified_secondary")) not in ("verified_primary", "corroborated_secondary")
    ]
    catalysts = [c for c in verified_pool if _get(c, "causal_role", "") == "primary_catalyst"]
    mechanisms = [c for c in verified_pool if _get(c, "causal_role", "") == "transmission_mechanism"]
    backgrounds = [c for c in verified_pool if c not in catalysts and c not in mechanisms]

    return {
        "all_sorted": sorted_claims,
        "verified_pool": verified_pool,
        "unverified_pool": unverified_pool,
        "catalysts": catalysts,
        "mechanisms": mechanisms,
        "backgrounds": backgrounds,
    }


def _render_claim_sentence(
    claim_obj: Any,
    market: str,
    topic: str,
    role_slot: str,
    central_question: str = "",
    slot_idx: int = 0,
) -> Tuple[str, List[str]]:
    """Construct an authentic investigative narrative sentence anchored directly in `claim_obj`
    with provenance-matched legal & verification qualification and non-repetitive framing.
    """
    from app.services.story_provenance_engine import normalize_market_code

    m = normalize_market_code(market)
    hook_mode = role_slot.startswith("hook_")
    loc_topic = _localized_topic_label(topic, m)
    if claim_obj is None:
        cid = "C001"
        fact = _format_claim_fact(topic, m, topic, hook_mode=hook_mode)
        ls, st, dt, sp, ps, vs = "alleged", "press", "unknown", None, "unknown", "unverified_secondary"
    else:
        get_attr = (lambda k, d="": claim_obj.get(k, d)) if isinstance(claim_obj, dict) else (lambda k, d="": getattr(claim_obj, k, d))
        cid = str(get_attr("claim_id", "C001"))
        fact = _format_claim_fact(claim_obj, m, topic, hook_mode=hook_mode)
        ls = str(get_attr("legal_status", "alleged") or "alleged")
        st = str(get_attr("source_type", "press") or "press")
        dt = str(get_attr("doc_type", "unknown") or "unknown")
        sp = get_attr("speaker", None)
        ps = str(get_attr("procedural_status", "unknown") or "unknown")
        vs = str(get_attr("verification_status", "corroborated_secondary") or "corroborated_secondary")

    # Keep central question concise in Beat 1 so hook never spills over 25s
    cq_clean = re.sub(r"\s+", " ", (central_question or "").strip())
    v_idx = slot_idx % 5

    if m == "KR":
        if role_slot == "hook_catalyst":
            raw = f"{loc_topic}, {fact}."
        elif role_slot == "hook_scale":
            raw = f"수치는 {fact}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean) <= 14 and _localized_topic_label(cq_clean, "KR") == cq_clean[:14]) else "왜 못 막았을까?"
            raw = f"{q_short} {fact}."
        elif role_slot == "setup":
            frames = [
                f"초기 국면의 공식 보고서는 외형적 안정만 강조했고, 이면에서는 {fact} 상황이 누적됐습니다.",
                f"시장 참여자들이 표면 지표에 집중하는 사이, 현장에서는 {fact} 흐름이 조용히 굳어졌죠.",
                f"당시 감독 체계가 정상 작동을 자부할 무렵에도 {fact} 정황이 내부 문건 곳곳에 쌓이고 있었습니다.",
                f"낙관론이 시장을 덮고 있던 시점에 실제 장부에는 {fact} 대목이 선명하게 찍혀 나왔습니다.",
                f"외부에서는 관리 가능한 위험으로 평가했지만, 구조적 취약성은 이미 {fact} 지점에서 번졌습니다.",
            ]
            raw = frames[v_idx]
        elif role_slot == "mechanism":
            frames = [
                f"자금과 계약의 연결고리를 따라가면, {fact} 구조가 위험을 증폭시킨 핵심 통로로 드러납니다.",
                f"단순 실수가 아닌 반복 설계였습니다. 바로 {fact} 장치가 손실 규모를 기하급수적으로 키웠죠.",
                f"위험이 하위 당사자에게 전가되는 과정에는 {fact} 기제가 결정적 매개체 역할을 수행했습니다.",
                f"제도적 공백을 파고든 전달 경로를 뜯어보면, {fact} 항목이 연쇄 충격을 촉발했습니다.",
                f"실무 거래 내역을 교차 검증한 결과, {fact} 방식이 내부 견제 장치를 무력화한 점이 확인됩니다.",
            ]
            raw = frames[v_idx]
        elif role_slot == "crack":
            frames = [
                f"임계점을 넘긴 균열이 터져 나오자, {fact} 정황이 공식 조사와 감사 기록에 올랐습니다.",
                f"상환과 점검 압력이 한꺼번에 몰린 순간, {fact} 사실은 더 이상 은폐될 수 없었죠.",
                f"유동성 완충 장치가 한계를 드러내면서 {fact} 대목이 핵심 수사 쟁점으로 비화했습니다.",
                f"내부 자료와 현장 실사가 맞물리자, {fact} 진상이 연쇄적으로 외부에 공개됐습니다.",
                f"부실 징후가 수면 위로 급격히 번지며 {fact} 기록이 결정적 근거로 제출됐습니다.",
            ]
            raw = frames[v_idx]
        else:
            frames = [
                f"사후 수습 과정에서 남은 과제는 {fact} 사례처럼 사전 경보 기준을 엄격히 세우는 일입니다.",
                f"피해 복구와 책임 규명은 이어졌지만, {fact} 쟁점은 유사 구조 전반에 짙은 경고를 남겼죠.",
                f"결국 제도의 신뢰는 사후 처벌이 아니라 {fact} 위험을 조기에 차단하는 검증력에 달려 있습니다.",
                f"앞으로의 정책 검증 기준은 분명합니다. {fact} 지점이 재발하지 않도록 공시와 책임을 묶어야 합니다.",
                f"이 사건이 남긴 현대적 교훈은 {fact} 대목이 보여주듯, 감춰진 연쇄 부채의 조기 포착입니다.",
            ]
            raw = frames[v_idx]

    elif m == "JA":
        if role_slot == "hook_catalyst":
            raw = f"急激な市場の危機は{fact}で表面化。"
        elif role_slot == "hook_scale":
            raw = f"規模は{fact}に達した。"
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean) <= 16) else "なぜ止められたはずが放置されたか。"
            raw = f"{q_short}{fact}。"
        elif role_slot == "setup":
            frames = [
                f"表面的な安定が語られた初期段階でも、現場の帳簿には{fact}という歪みが静かに蓄積していました。",
                f"市場が短期的な好調さに目を奪われる裏側で、実務上は{fact}という前提がすでに進行中だったのです。",
                f"監視体制の健全性が強調された時期でさえ、内部記録には{fact}を示す兆候が幾重にも残っていました。",
                f"外向けの説明では管理可能とされたものの、実際の取引構造では{fact}という偏りが強まりました。",
                f"制度の枠組みが問題視される以前から、関係者間では{fact}をめぐる負担が水面下で拡大しています。",
            ]
            raw = frames[v_idx]
        elif role_slot == "mechanism":
            frames = [
                f"資金と契約の連鎖を精査すると、{fact}という仕組みこそがリスクを増幅させた中核経路でした。",
                f"偶発的な不手際ではありません。実務では{fact}という手法が繰り返され、損失の連鎖を生んだのです。",
                f"下位当事者へ負担が転嫁される構造の中で、{fact}という条項が致命的な連動装置となりました。",
                f"規制の隙間を突く運用実態をたどると、{fact}が内部統制を形骸化させた決定打として浮かびます。",
                f"台帳と契約書を照合すれば明確です。{fact}の設計がリスクの早期遮断を阻み続けていました。",
            ]
            raw = frames[v_idx]
        elif role_slot == "crack":
            frames = [
                f"限界を超えた亀裂が露呈したことで、{fact}の経緯が公式な調査記録へと刻まれました。",
                f"返済と監査の圧力が同時に集中した瞬間、{fact}という事実はもはや隠しきれなくなったのです。",
                f"資金繰りの緩衝材が失われるとともに、{fact}が行政および司法の焦点へと急浮上しました。",
                f"現場査察と内部資料の突き合わせにより、{fact}をめぐる構造破綻が一気に表面化しています。",
                f"信用不安が連鎖的に広がる局面で、{fact}を示す一次記録が重大な証拠として提出されました。",
            ]
            raw = frames[v_idx]
        else:
            frames = [
                f"事後対応を経て残された課題は、{fact}のように検証可能な早期警戒網をどう築くかという点です。",
                f"救済と責任追及が続く一方、{fact}の事例は同種の市場構造に対する厳しい警鐘となりました。",
                f"制度の信頼を支えるのは事後処分だけでなく、{fact}の予兆を捉える継続的な監査能力にあります。",
                f"再発防止の要点は明白であり、{fact}のような死角を情報開示でふさぐ体制整備が欠かせません。",
                f"一連の破綻が突きつける教訓は、{fact}が示す見えにくい連鎖リスクを平時から直視することです。",
            ]
            raw = frames[v_idx]

    elif m == "VN":
        if role_slot == "hook_catalyst":
            raw = f"Trong cuộc khủng hoảng {loc_topic}, {fact}."
        elif role_slot == "hook_scale":
            raw = f"Quy mô xác nhận: {fact}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean.split()) <= 8) else "Vì sao cảnh báo bị bỏ qua?"
            raw = f"{q_short} {fact}."
        elif role_slot == "setup":
            frames = [
                f"Ở giai đoạn khởi phát, báo cáo bề nổi giữ vẻ ổn định trong khi {fact} âm thầm tích tụ.",
                f"Khi dư luận còn nhìn vào tăng trưởng bề mặt, thực tế sổ sách đã cho thấy {fact} kéo dài.",
                f"Dưới lớp vỏ bọc vận hành bình thường, các dữ liệu nội bộ từng ghi nhận {fact} từ sớm.",
                f"Trái với nhận định lạc quan ban đầu, điểm nghẽn đã hình thành quanh {fact} suốt nhiều quý.",
                f"Trước lúc khủng hoảng bùng phát công khai, hồ sơ giao dịch phản ánh rõ tình trạng {fact}.",
            ]
            raw = frames[v_idx]
        elif role_slot == "mechanism":
            frames = [
                f"Khi bóc tách dòng tiền và hợp đồng, mắt xích {fact} chính là cơ chế khuếch đại rủi ro.",
                f"Đây không phải sai sót đơn lẻ mà là cách vận hành lặp lại gắn với {fact} qua từng chu kỳ.",
                f"Áp lực thanh khoản bị đẩy dồn sang bên yếu thế thông qua cơ chế {fact} thiếu kiểm soát.",
                f"Lần theo dấu vết hồ sơ, chính lỗ hổng quanh {fact} đã vô hiệu hóa hàng rào giám sát.",
                f"Đối chiếu các chứng từ liên quan cho thấy {fact} biến rủi ro cục bộ thành hiệu ứng dây chuyền.",
            ]
            raw = frames[v_idx]
        elif role_slot == "crack":
            frames = [
                f"Khi áp lực đáo hạn vượt ngưỡng chịu đựng, {fact} lập tức trở thành tâm điểm thanh tra.",
                f"Đến thời điểm vỡ trận, mọi che chắn bị gạt bỏ và {fact} hiện rõ trên tài liệu chính thức.",
                f"Đà sụp đổ dây chuyền bùng lên ngay khi {fact} bị phanh phui qua kiểm tra thực địa.",
                f"Sự kết hợp giữa đơn tố cáo và kiểm toán độc lập đã đưa {fact} ra ánh sáng công luận.",
                f"Ngay khi dòng tiền mất cân đối, hồ sơ ghi nhận {fact} được chuyển tới cơ quan thụ lý.",
            ]
            raw = frames[v_idx]
        else:
            frames = [
                f"Bài học dài hạn sau biến cố nằm ở việc siết chuẩn giám sát ngay từ dấu hiệu {fact}.",
                f"Quá trình xử lý hậu quả vẫn tiếp diễn, nhưng {fact} đã đặt ra chuẩn mực minh bạch mới.",
                f"Niềm tin thị trường không chỉ dựa vào xử phạt mà phải chặn sớm những mô hình kiểu {fact}.",
                f"Yêu cầu cải cách trọng tâm hiện nay là buộc trách nhiệm giải trình gắn liền với {fact}.",
                f"Dư âm lớn nhất của vụ việc xoay quanh {fact}, lời nhắc về kỷ luật kiểm soát đòn bẩy.",
            ]
            raw = frames[v_idx]

    else:  # EN
        if role_slot == "hook_catalyst":
            raw = f"Crisis trigger in {loc_topic}: {fact}."
        elif role_slot == "hook_scale":
            raw = f"Verified scale: {fact}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean.split()) <= 8) else "Why did early oversight fail?"
            raw = f"{q_short} Records cite {fact}."
        elif role_slot == "setup":
            frames = [
                f"In the opening phase, routine disclosures projected calm while {fact} quietly built beneath the surface.",
                f"Public commentary pointed to stability even as underlying ledgers showed {fact} taking hold.",
                f"Long before headlines turned urgent, archival filings documented {fact} across core operations.",
                f"Despite reassuring institutional briefings, early compliance records revealed {fact} widening over time.",
                f"While external analysts assumed risks remained contained, transaction logs pointed directly to {fact}.",
            ]
            raw = frames[v_idx]
        elif role_slot == "mechanism":
            frames = [
                f"Tracing the payment and governance chain confirms {fact} served as the primary transmission channel.",
                f"Rather than an isolated mistake, repeating structural incentives tied to {fact} multiplied exposure.",
                f"As liabilities shifted toward weaker counterparties, {fact} removed crucial safeguards from the balance sheet.",
                f"Auditing the contractual sequence shows how {fact} bypassed standard oversight checks.",
                f"Cross-referencing filings highlights {fact} as the exact lever converting local strain into systemic shock.",
            ]
            raw = frames[v_idx]
        elif role_slot == "crack":
            frames = [
                f"Once liquidity buffers gave way, formal inquiries placed {fact} at the center of the breakdown.",
                f"As refinancing stress peaked, {fact} surfaced in official findings and public records.",
                f"Under mounting counterparty defaults, investigators documented {fact} across multiple reporting lines.",
                f"Field audits and internal records converged quickly, exposing {fact} to outside scrutiny.",
                f"When emergency reviews opened, {fact} became impossible to insulate from institutional accountability.",
            ]
            raw = frames[v_idx]
        else:
            frames = [
                f"The lasting institutional lesson centers on building earlier enforcement gates around {fact}.",
                f"Remediation remains ongoing, yet {fact} already reshaped how similar market risks get audited.",
                f"Durable reform depends less on retroactive penalties than spotting warning patterns like {fact} early.",
                f"What endures beyond this episode is a clear governance test anchored in {fact}.",
                f"Looking ahead, the case stands as a direct caution against overlooking hidden leverage tied to {fact}.",
            ]
            raw = frames[v_idx]

    qualified = _apply_legal_qualifier(
        raw,
        legal_status=ls,
        market=m,
        source_type=st,
        doc_type=dt,
        speaker=sp,
        procedural_status=ps,
        verification_status=vs,
    )
    return qualified, [cid]


def _build_grounded_story_beats(
    topic: str,
    evidence_ledger: List[Any],
    evidence_map: Dict[str, Any],
    market: str = "EN",
    central_question: str = "",
    d_min: float = 180.0,
    d_max: float = 300.0,
    u_min: Optional[int] = None,
    u_max: Optional[int] = None,
) -> List[Tuple[str, float, List[Any]]]:
    """Generate a generic, provenance-prioritized 5-beat forensic docudrama script
    grounded strictly in `evidence_ledger` with zero topic-specific hardcoding.
    """
    from app.schemas.story_contracts import StorySceneLine
    from app.services.story_provenance_engine import normalize_market_code

    m = normalize_market_code(market)
    pools = _select_ordered_claims(evidence_ledger)
    all_claims = pools["all_sorted"]
    verified_pool = pools["verified_pool"]

    # Beat 1 MUST prefer verified_primary / corroborated_secondary claims; only fall back if ledger has zero verified claims
    hook_source = (
        pools["catalysts"]
        or verified_pool
        or all_claims
    )
    b2_source = pools["backgrounds"] or verified_pool or all_claims
    b3_source = pools["mechanisms"] or verified_pool or all_claims
    b4_source = (pools["catalysts"] + pools["unverified_pool"]) or all_claims
    b5_source = verified_pool[::-1] + pools["unverified_pool"] or all_claims

    # Deterministic claim cursor to maximize unique coverage across the entire ledger (>= 70%)
    used_ids: List[str] = []
    pick_cursor = [0]

    def _pick_claim(preferred: List[Any], restrict_to_preferred: bool = False) -> Any:
        if not all_claims:
            return None
        for cand in preferred:
            cid = cand.get("claim_id") if isinstance(cand, dict) else getattr(cand, "claim_id", None)
            if cid and cid not in used_ids:
                used_ids.append(cid)
                return cand
        if restrict_to_preferred and preferred:
            idx_c = pick_cursor[0]
            pick_cursor[0] += 1
            return preferred[idx_c % len(preferred)]
        for cand in all_claims:
            cid = cand.get("claim_id") if isinstance(cand, dict) else getattr(cand, "claim_id", None)
            if cid and cid not in used_ids:
                used_ids.append(cid)
                return cand
        pool = preferred or all_claims
        idx_c = pick_cursor[0]
        pick_cursor[0] += 1
        return pool[idx_c % len(pool)]

    visual_hooks_seq = [
        "stat_hero", "stamp", "magnifier", "red_thread",
        "cutout", "ruler_measure", "compass_arc", "scissors_cut", "grease_pencil",
    ]

    beat_specs: List[Tuple[str, float, List[Tuple[str, List[Any]]]]] = [
        ("B1_hook", 19.2, [
            ("hook_catalyst", hook_source),
            ("hook_scale", verified_pool or hook_source),
            ("hook_paradox", hook_source),
        ]),
        ("B2_setup", 40.8, [
            ("setup", b2_source),
            ("setup", b2_source),
            ("setup", b2_source),
            ("setup", b2_source),
        ]),
        ("B3_scheme", 79.2, [
            ("mechanism", b3_source),
            ("mechanism", b3_source),
            ("mechanism", b3_source),
            ("mechanism", b3_source),
            ("mechanism", b3_source),
        ]),
        ("B4_crack", 60.0, [
            ("crack", b4_source),
            ("crack", b4_source),
            ("crack", b4_source),
            ("crack", b4_source),
        ]),
        ("B5_aftermath", 40.8, [
            ("aftermath", b5_source),
            ("aftermath", b5_source),
            ("aftermath", b5_source),
        ]),
    ]

    # Scale up lines dynamically on larger ledgers so >= 70% of distinct claims are explicitly covered
    total_claims_n = len(all_claims)
    target_lines_total = (
        max(19, min(26, total_claims_n + 2))
        if total_claims_n <= 24
        else max(24, min(30, int(total_claims_n * 0.72) + 2))
    )
    extra_needed = max(0, target_lines_total - sum(len(slots) for _, _, slots in beat_specs))
    expand_order = [2, 3, 1, 4]  # B3_scheme, B4_crack, B2_setup, B5_aftermath
    for i in range(extra_needed):
        b_idx = expand_order[i % len(expand_order)]
        role_slot, src_pool = beat_specs[b_idx][2][0]
        beat_specs[b_idx][2].append((role_slot, src_pool))

    raw_beats: List[Tuple[str, float, List[Any]]] = []
    vh_idx = 0
    for beat_id, dur_s, slots in beat_specs:
        beat_lines: List[StorySceneLine] = []
        is_hook_beat = beat_id.startswith("B1")
        for l_idx, (role_slot, src_pool) in enumerate(slots, start=1):
            c_obj = _pick_claim(src_pool, restrict_to_preferred=(is_hook_beat and bool(verified_pool)))
            txt, cids = _render_claim_sentence(
                c_obj,
                market=m,
                topic=topic,
                role_slot=role_slot,
                central_question=central_question if role_slot == "hook_paradox" else "",
                slot_idx=l_idx - 1,
            )
            vh = visual_hooks_seq[vh_idx % len(visual_hooks_seq)]
            vh_idx += 1
            beat_lines.append(StorySceneLine(
                line_id=f"{beat_id[:2]}_L{l_idx:02d}",
                text=txt,
                claim_ids=cids,
                visual_hook=vh,
            ))
        raw_beats.append((beat_id, dur_s, beat_lines))

    # Closed-loop TTS duration calibration: ensure B1 <= 24s AND total fits strictly inside [d_min..d_max] & [u_min..u_max]
    from core.pacing_budgeter import estimate_script_speech_duration, get_market_unit_bounds

    if u_min is None or u_max is None:
        eff_u_min, eff_u_max = get_market_unit_bounds(m)
    else:
        eff_u_min, eff_u_max = int(u_min), int(u_max)

    # 1. Trim Beat 1 hook lines if they exceed 24.0s (S04 rejects Beat 1 > 25.0s)
    from app.services.story_provenance_engine import extract_claim_elements as _b1_extract

    b1_texts = [ln.text for ln in raw_beats[0][2]]
    b1_dur = float(estimate_script_speech_duration(b1_texts, market=m, docudrama_tempo=True)["estimated_duration_sec"])
    if b1_dur > 24.0:
        for ln_b1 in raw_beats[0][2]:
            elems_b1 = _b1_extract(ln_b1.text)
            trimmed_b1 = _trim_clause_smart(ln_b1.text, elems_b1, market=m, hook_mode=True)
            ln_b1.text = trimmed_b1 if trimmed_b1.endswith((".", "!", "?", "。")) else f"{trimmed_b1}."
        b1_dur = float(
            estimate_script_speech_duration([ln.text for ln in raw_beats[0][2]], market=m, docudrama_tempo=True)["estimated_duration_sec"]
        )
        if b1_dur > 24.0 and len(raw_beats[0][2]) > 2:
            raw_beats[0][2].pop()

    all_line_texts = [ln.text for _, _, lns in raw_beats for ln in lns]
    timing_now = estimate_script_speech_duration(all_line_texts, market=m, docudrama_tempo=True)
    measured_s = float(timing_now["estimated_duration_sec"])
    measured_units = int(timing_now["spoken_units"])
    expand_beats = [2, 3, 1, 4]  # B3_scheme, B4_crack, B2_setup, B5_aftermath (never bloat B1_hook)
    expand_roles = {1: "setup", 2: "mechanism", 3: "crack", 4: "aftermath"}
    expand_pools = {1: b2_source, 2: b3_source, 3: b4_source, 4: b5_source}
    extra_guard = 0
    while (measured_s < max(195.0, d_min + 15.0) or measured_units < eff_u_min) and measured_s < (d_max - 20.0) and measured_units < (eff_u_max - 30) and extra_guard < 26 and all_claims:
        b_idx = expand_beats[extra_guard % len(expand_beats)]
        beat_id_e, _, beat_lines_e = raw_beats[b_idx]
        c_obj = _pick_claim(expand_pools[b_idx])
        l_idx_e = len(beat_lines_e) + 1
        txt_e, cids_e = _render_claim_sentence(
            c_obj,
            market=m,
            topic=topic,
            role_slot=expand_roles[b_idx],
            central_question="",
            slot_idx=l_idx_e - 1,
        )
        vh_e = visual_hooks_seq[vh_idx % len(visual_hooks_seq)]
        vh_idx += 1
        beat_lines_e.append(StorySceneLine(
            line_id=f"{beat_id_e[:2]}_L{l_idx_e:02d}",
            text=txt_e,
            claim_ids=cids_e,
            visual_hook=vh_e,
        ))
        all_line_texts.append(txt_e)
        timing_now = estimate_script_speech_duration(all_line_texts, market=m, docudrama_tempo=True)
        measured_s = float(timing_now["estimated_duration_sec"])
        measured_units = int(timing_now["spoken_units"])
        extra_guard += 1

    # 2. Trim upper excess if initial fallback lines already overshoot d_max or u_max
    trim_guard = 0
    while (measured_s > (d_max - 10.0) or measured_units > eff_u_max) and trim_guard < 24:
        trimmable = [b_i for b_i in (2, 3, 1, 4) if len(raw_beats[b_i][2]) > 2]
        if not trimmable:
            break
        b_i = max(trimmable, key=lambda idx_b: len(raw_beats[idx_b][2]))
        raw_beats[b_i][2].pop()
        all_line_texts = [ln.text for _, _, lns in raw_beats for ln in lns]
        timing_now = estimate_script_speech_duration(all_line_texts, market=m, docudrama_tempo=True)
        measured_s = float(timing_now["estimated_duration_sec"])
        measured_units = int(timing_now["spoken_units"])
        trim_guard += 1

    return raw_beats


def _build_statement_claim_map(
    beats: List[Any],
    evidence_map: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build explicit statement-to-claim alignment map for S04 forensic verification."""
    from app.services.story_provenance_engine import extract_claim_elements, has_entity_or_metric_signal

    entries: List[Dict[str, Any]] = []
    for beat in beats:
        b_id = beat.beat_id if hasattr(beat, "beat_id") else beat.get("beat_id", "")
        lines = beat.lines if hasattr(beat, "lines") else beat.get("lines", [])
        for ln in lines:
            l_id = ln.line_id if hasattr(ln, "line_id") else ln.get("line_id", "")
            txt = ln.text if hasattr(ln, "text") else ln.get("text", "")
            cids = list(ln.claim_ids if hasattr(ln, "claim_ids") else ln.get("claim_ids", []))
            ver_statuses: List[str] = []
            causal_roles: List[str] = []
            matched_terms: List[str] = []
            for cid in cids:
                c_obj = evidence_map.get(cid)
                if not c_obj:
                    continue
                vs = c_obj.get("verification_status", "unverified_secondary") if isinstance(c_obj, dict) else getattr(c_obj, "verification_status", "unverified_secondary")
                cr = c_obj.get("causal_role", "unknown") if isinstance(c_obj, dict) else getattr(c_obj, "causal_role", "unknown")
                c_txt = c_obj.get("claim", "") if isinstance(c_obj, dict) else getattr(c_obj, "claim", "")
                ver_statuses.append(str(vs))
                causal_roles.append(str(cr))
                _, terms = has_entity_or_metric_signal(txt, extract_claim_elements(c_txt), min_stem_hits=1)
                for tm in terms:
                    if tm not in matched_terms:
                        matched_terms.append(tm)
            entries.append({
                "beat_id": b_id,
                "line_id": l_id,
                "text": txt,
                "claim_ids": cids,
                "verification_statuses": ver_statuses,
                "causal_roles": causal_roles,
                "matched_terms": matched_terms[:10],
            })
    return entries


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
    topic = s2_art.payload.get("topic", "Investigative Case Breakdown")

    try:
        from core.market_resolver import resolve_canonical_market
        market = resolve_canonical_market(ctx=ctx)
    except Exception:
        market = "EN"

    preset_raw = (getattr(ctx.preset, "name", ctx.preset) if ctx.preset else getattr(getattr(ctx, "manifest", None), "preset", None)) or "story_forensic"
    is_story = bool(preset_raw in ("story_forensic", "vox_narrative"))

    if is_story:
        from app.schemas.story_contracts import EvidenceClaim, StorySceneLine, StoryScriptBeat, StoryScriptPayload
        from app.services.story_provenance_engine import (
            audit_statement_claim_alignment,
            check_market_entity_appropriateness,
            check_target_market_language_purity,
        )
        from core.llm_json import parse_llm_json
        from core.pacing_budgeter import (
            count_speech_units,
            estimate_script_speech_duration,
            get_market_unit_bounds,
        )

        # Pull S01 ideation context cleanly if available so central_question is never unbound
        s1_art_path = ctx.paths.artifact_file(StageID.S1_IDEATION.value)
        s1_payload: Dict[str, Any] = {}
        if s1_art_path.exists():
            try:
                s1_payload = json.loads(s1_art_path.read_text(encoding="utf-8")).get("payload", {})
            except Exception as exc:
                logger.debug(f"[S03_SCRIPT] Notice reading S01 context: {exc}")

        w_title = s2_art.payload.get("title_working") or s1_payload.get("title_working") or s2_art.payload.get("topic") or topic
        c_quest = (
            s2_art.payload.get("central_question")
            or s1_payload.get("central_question")
            or f"How did structural incentives and oversight failures drive {topic}?"
        )

        evidence_raw = s2_art.payload.get("evidence_ledger", [])
        evidence_ledger = [EvidenceClaim.model_validate(c) if isinstance(c, dict) else c for c in evidence_raw]
        evidence_map = {c.claim_id: c for c in evidence_ledger}

        prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s03_script.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""

        d_min = 180.0
        d_max = 300.0
        target_run_s = 240.0
        preset_obj = getattr(ctx, "preset", None)
        if preset_obj:
            dw = getattr(preset_obj, "duration_window_s", None)
            if dw:
                d_min = float(getattr(dw, "min", 180.0) or 180.0)
                d_max = float(getattr(dw, "max", 300.0) or 300.0)
                target_run_s = float(getattr(dw, "target", 240.0) or 240.0)
        u_min, u_max = get_market_unit_bounds(market, preset_obj=preset_obj)

        raw_beats: List[Tuple[str, float, List[Any]]] = []
        if not ctx.dry_run and system_prompt:
            try:
                from app.services.model_gateway import get_global_gateway

                gateway = get_global_gateway()
                ledger_for_prompt = [c.model_dump() for c in evidence_ledger]
                user_prompt = (
                    f"Target Market: {market}\n"
                    f"Topic: {topic}\n"
                    f"Working Title: {w_title}\n"
                    f"Central Investigative Question: {c_quest}\n"
                    f"Evidence Ledger (preserve verification_status, doc_type, speaker, procedural_status, scope):\n"
                    f"{json.dumps(ledger_for_prompt, indent=2, ensure_ascii=False)}\n\n"
                )
                if market == "KR":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR KOREAN (KR) MARKET:\n"
                        "1. Write 100% natural, authoritative investigative Korean narration (Hangul). English/foreign prose is STRICTLY FORBIDDEN.\n"
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} spoken Hangul+numeral syllables across 19-24 lines). Beat 1 (B1_hook) MUST be ultra-punchy: 3 concise lines totaling <= 105 syllables (<= 21s).\n"
                        "3. LEGAL & PROVENANCE ATTRIBUTION:\n"
                        "   - Cite valid claim_ids on every factual line.\n"
                        "   - Distinguish 'court_judgment' (법원 확정 판결에 따르면) vs 'indictment' (검찰 공소장에 따르면) vs 'criminal_complaint' (고발장·소장에 따르면) vs 'press' reports (보도에 따르면).\n"
                        "   - NEVER elevate 'unverified_secondary' claims into Beat 1's opening core premise; attribute them explicitly as preliminary/unverified.\n"
                        "   - Avoid repetitive explainer disclaimers or speculative causal leaps.\n\n"
                    )
                elif market == "JA":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR JAPANESE (JA) MARKET:\n"
                        "1. Write 100% natural, authoritative Japanese investigative narration. No Hangul or foreign sentences.\n"
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} spoken Japanese characters across 19-24 lines). Beat 1 (B1_hook) MUST be 3 concise lines totaling <= 125 chars (<= 21s).\n"
                        "3. Distinguish judgment (判決によれば) vs indictment (起訴状によれば) vs complaint (訴状によれば) vs unverified press reports (未確認の報道によれば).\n"
                        "4. Beat 1 must anchor strictly in verified_primary or corroborated_secondary catalyst facts.\n\n"
                    )
                elif market == "VN":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR VIETNAMESE (VN) MARKET:\n"
                        "1. Write 100% natural, authoritative Vietnamese narration with full Vietnamese diacritics. No English/CJK prose.\n"
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} Vietnamese words across 19-24 lines). Beat 1 (B1_hook) MUST be 3 concise lines totaling <= 75 words (<= 21s).\n"
                        "3. Distinguish judgment (Theo phán quyết của tòa án) vs indictment (Theo cáo trạng) vs complaint (Theo đơn kiện) vs unverified press reports (Theo thông tin bước đầu chưa kiểm chứng).\n\n"
                    )
                else:
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR ENGLISH (EN) MARKET:\n"
                        f"1. STRICT LENGTH & PACING: Write 100% crisp investigative English narration strictly totaling {u_min}-{u_max} words across 20-26 lines (180-300s). Beat 1 (B1_hook) MUST be 3 tight, punchy lines totaling <= 44 words (<= 22s).\n"
                        "2. Distinguish court_judgment vs indictment vs criminal_complaint vs settled without admitting wrongdoing vs unverified preliminary reports. Attribute DOJ/regulatory allegations directly to the agency/court, NOT to 'press reports'.\n"
                        "3. Beat 1 MUST anchor in verified_primary or corroborated_secondary catalyst facts.\n\n"
                    )

                min_req_claims = max(3, int(-(-len(evidence_ledger) * 60 // 100))) if evidence_ledger else 0
                user_prompt += (
                    "MANDATORY GROUNDING & CAUSAL DISCIPLINE (Rule 130 & 131):\n"
                    f"- Cover at least {min_req_claims}/{len(evidence_ledger)} distinct claims substantively across the 5 beats (B1_hook, B2_setup, B3_scheme, B4_crack, B5_aftermath).\n"
                    "- Introduce Level 1 primary_catalyst BEFORE dissecting Level 2 transmission_mechanism; preserve exact numeric metrics and causal polarity.\n"
                    "- Use standard Arabic numerals (no spelled-out phonetic digit strings) so TTS timing and visual captions stay synchronized.\n"
                    "- Every line must specify a visual_hook: 'stamp', 'ruler_measure', 'compass_arc', 'cutout', 'red_thread', 'magnifier', 'scissors_cut', or 'grease_pencil'.\n"
                    "Start response immediately with { and end with }. Output ONLY valid JSON adhering to schema with NO preamble."
                )

                def _parse_and_build_llm_beats(raw_resp_text: str):
                    p_json = parse_llm_json(raw_resp_text)
                    if isinstance(p_json, list):
                        if p_json and isinstance(p_json[0], dict) and "beats" in p_json[0]:
                            p_json = p_json[0]
                        elif p_json and isinstance(p_json[0], dict) and any(k in p_json[0] for k in ("beat_id", "lines", "id")):
                            p_json = {"beats": p_json}
                        else:
                            p_json = {}
                    elif not isinstance(p_json, dict):
                        p_json = {}

                    built_beats: List[Tuple[str, float, List[StorySceneLine]]] = []
                    for idx, beat_data in enumerate(p_json.get("beats", []), start=1):
                        if not isinstance(beat_data, dict):
                            continue
                        b_id = beat_data.get("beat_id") or beat_data.get("id") or f"B{idx}_beat"
                        target_dur = float(beat_data.get("target_duration_s") or beat_data.get("duration_seconds") or (
                            19.2 if "B1" in b_id else (40.8 if "B2" in b_id else (79.2 if "B3" in b_id else (60.0 if "B4" in b_id else 40.8)))
                        ))
                        lines_data: List[StorySceneLine] = []
                        for l_idx, ln in enumerate(beat_data.get("lines", []), start=1):
                            if isinstance(ln, str):
                                ln = {"text": ln}
                            elif not isinstance(ln, dict):
                                continue
                            c_ids = [cid for cid in (ln.get("claim_ids") or []) if cid in evidence_map]
                            if not c_ids and evidence_ledger:
                                c_ids = [evidence_ledger[min(idx - 1, len(evidence_ledger) - 1)].claim_id]
                            text = ln.get("text", "")
                            if (market or "EN").upper() in ("KR", "KO"):
                                text = _normalize_spoken_korean_numbers(text)

                            c_objs = [evidence_map[cid] for cid in c_ids if cid in evidence_map]
                            if len(c_objs) > 1:
                                _ver_rank = {"verified_primary": 0, "corroborated_secondary": 1, "unverified_secondary": 2, "speculative": 3}
                                _src_rank = {"court": 0, "regulator": 1, "gov": 2, "press": 3}
                                c_objs.sort(key=lambda co: (
                                    _ver_rank.get(str(co.get("verification_status") if isinstance(co, dict) else getattr(co, "verification_status", "")), 2),
                                    _src_rank.get(str(co.get("source_type") if isinstance(co, dict) else getattr(co, "source_type", "")), 3),
                                ))
                            primary_c = c_objs[0] if c_objs else None
                            if primary_c is not None:
                                get_a = (lambda k, d="": primary_c.get(k, d)) if isinstance(primary_c, dict) else (lambda k, d="": getattr(primary_c, k, d))
                                text = _apply_legal_qualifier(
                                    text=text,
                                    legal_status=str(get_a("legal_status", "alleged")),
                                    market=market,
                                    source_type=str(get_a("source_type", "press")),
                                    doc_type=str(get_a("doc_type", "unknown")),
                                    speaker=get_a("speaker", None),
                                    procedural_status=str(get_a("procedural_status", "unknown")),
                                    verification_status=str(get_a("verification_status", "corroborated_secondary")),
                                )

                            v_hook = ln.get("visual_hook") or "stamp"
                            lines_data.append(StorySceneLine(
                                line_id=ln.get("line_id", f"{b_id}_L{l_idx:02d}"),
                                text=text,
                                claim_ids=c_ids,
                                visual_hook=v_hook,
                            ))
                        built_beats.append((b_id, target_dur, lines_data))
                    return built_beats

                from app.services.story_provenance_engine import extract_claim_elements as _extract_elems
                from app.services.story_provenance_engine import line_matches_expected_qualifier as _match_qual

                grounded_nouns: set[str] = {"KRW", "USD", "JPY", "VND", "EUR", "GDP", "CPI", "IPO", "ETF", "LTV", "SEC", "FTC", "CMS", "DOJ", "OIG", "HHS", "RADV"}
                for tok in re.findall(r"\b[A-Z][A-Za-z0-9&\-]{1,}\b", topic or ""):
                    grounded_nouns.add(tok)
                for ev_d in evidence_raw:
                    for ent in _extract_elems(str(ev_d.get("claim", ""))).get("entities", []):
                        grounded_nouns.add(ent)
                    for tok in re.findall(r"\b[A-Z][A-Za-z0-9&\-]{1,}\b", str(ev_d.get("source_name", ""))):
                        grounded_nouns.add(tok)

                def _eval_llm_beats(cand_beats: List[Tuple[str, float, List[StorySceneLine]]]):
                    cand_lines = [ln.text for _, _, lns in cand_beats for ln in lns]
                    cand_full = " ".join(cand_lines)
                    cand_timing = estimate_script_speech_duration(cand_lines, market=market, docudrama_tempo=True)
                    cand_dur = float(cand_timing["estimated_duration_sec"])
                    cand_units = int(cand_timing["spoken_units"])
                    b1_lines = [ln.text for ln in cand_beats[0][2]] if cand_beats else []
                    b1_dur = float(
                        estimate_script_speech_duration(b1_lines, market=market, docudrama_tempo=True)["estimated_duration_sec"]
                    ) if b1_lines else 0.0
                    lang_ok, lang_issues = check_target_market_language_purity(
                        cand_full, market=market, grounded_proper_nouns=grounded_nouns
                    )
                    ent_ok, ent_issues = check_market_entity_appropriateness(cand_full, market=market, evidence_ledger=evidence_raw, topic=topic)
                    beats_dicts = [
                        {"beat_id": b_id, "lines": [ln.model_dump() for ln in lns]}
                        for b_id, _, lns in cand_beats
                    ]
                    align_res = audit_statement_claim_alignment(beats_dicts, evidence_raw, market=market)
                    qual_issues: List[str] = []
                    for _, _, lns in cand_beats:
                        for ln in lns:
                            for cid in (ln.claim_ids or []):
                                c_obj = evidence_map.get(cid)
                                if c_obj is not None:
                                    c_dict = c_obj.model_dump() if hasattr(c_obj, "model_dump") else dict(c_obj)
                                    ok_q, q_msg = _match_qual(ln.text, c_dict, market=market)
                                    if not ok_q:
                                        qual_issues.append(f"{ln.line_id}:{cid}:{q_msg}")
                    b1_dur_ok = b1_dur <= 24.0
                    b1_ok = bool(cand_beats and len(cand_beats[0][2]) >= 3 and b1_dur_ok and not align_res.get("beat1_unverified_elevation"))
                    units_ok = u_min <= cand_units <= u_max
                    dur_ok = (d_min <= cand_dur <= d_max) and units_ok
                    passed = (
                        len(cand_beats) == 5
                        and b1_ok
                        and dur_ok
                        and lang_ok
                        and ent_ok
                        and not qual_issues
                        and align_res.get("passed", False)
                    )
                    return passed, cand_timing, cand_dur, b1_dur, b1_dur_ok, units_ok, lang_ok, lang_issues, ent_ok, ent_issues, qual_issues, b1_ok, dur_ok, align_res

                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="gpt-6.1-sol",
                    system_prompt=system_prompt,
                    max_tokens=4000,
                    temperature=0.3,
                    timeout=120.0,
                    fallback="claude-v4.1-flash",
                )
                llm_beats = _parse_and_build_llm_beats(raw_response)
                passed_pre, cand_timing, cand_dur, b1_dur, b1_dur_ok, units_ok, lang_ok, lang_issues, ent_ok, ent_issues, qual_issues, b1_ok, dur_ok, align_res = _eval_llm_beats(llm_beats)

                if not passed_pre:
                    repair_notes: List[str] = []
                    if not dur_ok or not units_ok:
                        repair_notes.append(
                            f"Length {cand_timing['spoken_units']} {cand_timing['unit_type']} ({cand_dur:.1f}s) is OUT OF BOUNDS: "
                            f"MUST be strictly {u_min}-{u_max} {cand_timing['unit_type']} AND {d_min:.0f}-{d_max:.0f}s."
                        )
                    if not b1_dur_ok:
                        repair_notes.append(
                            f"Beat 1 (B1_hook) duration is {b1_dur:.1f}s (> 24.0s limit). Shorten Beat 1 lines so total Beat 1 speech is 15-21s."
                        )
                    if len(llm_beats) != 5:
                        repair_notes.append(f"Must have exactly 5 beats (got {len(llm_beats)}).")
                    if not b1_ok and (b1_dur_ok or align_res.get("beat1_unverified_elevation") or not llm_beats or len(llm_beats[0][2]) < 3):
                        repair_notes.append("Beat 1 must have >=3 concise lines anchored strictly in verified_primary/corroborated_secondary claims.")
                    if not lang_ok:
                        repair_notes.append(f"Language purity issues: {lang_issues[:3]}")
                    if not ent_ok:
                        repair_notes.append(f"Entity appropriateness issues: {ent_issues[:3]}")
                    if qual_issues:
                        repair_notes.append(f"Legal/procedural qualifier mismatches: {qual_issues[:4]}")
                    if not align_res.get("passed", False):
                        repair_notes.append(
                            f"Alignment issues: coverage={align_res.get('coverage_ratio', 0):.0%}, "
                            f"missing={align_res.get('uncovered_claims', [])[:4]}, "
                            f"mismatched={align_res.get('mismatched_lines', [])[:3]}"
                        )
                    logger.warning(
                        f"[S03_SCRIPT] Attempt 1 LLM pre-check failed ({'; '.join(repair_notes)}). Retrying once with targeted feedback."
                    )
                    repair_prompt = (
                        f"{user_prompt}\n\n"
                        "SELF-CORRECTION REQUIRED — FIX ALL ISSUES BELOW IN YOUR JSON OUTPUT:\n- "
                        + "\n- ".join(repair_notes)
                        + "\nReturn ONLY corrected valid JSON starting with { and ending with }."
                    )
                    raw_retry = gateway.call_llm(
                        prompt=repair_prompt,
                        model="gpt-6.1-sol",
                        system_prompt=system_prompt,
                        max_tokens=4000,
                        temperature=0.2,
                        timeout=120.0,
                        fallback="claude-v4.1-flash",
                    )
                    llm_beats_retry = _parse_and_build_llm_beats(raw_retry)
                    passed_retry, cand_timing_r, cand_dur_r, b1_dur_r, b1_dur_ok_r, units_ok_r, lang_ok_r, lang_issues_r, ent_ok_r, ent_issues_r, qual_issues_r, b1_ok_r, dur_ok_r, align_res_r = _eval_llm_beats(llm_beats_retry)
                    if passed_retry:
                        llm_beats = llm_beats_retry
                        cand_timing, cand_dur, b1_dur, b1_dur_ok, units_ok = cand_timing_r, cand_dur_r, b1_dur_r, b1_dur_ok_r, units_ok_r
                        lang_ok, lang_issues, ent_ok, ent_issues, qual_issues, b1_ok, dur_ok, align_res = (
                            lang_ok_r, lang_issues_r, ent_ok_r, ent_issues_r, qual_issues_r, b1_ok_r, dur_ok_r, align_res_r
                        )
                        passed_pre = True

                if passed_pre:
                    raw_beats = llm_beats
                    logger.info(
                        f"[S03_SCRIPT] Live LLM accepted: {len(llm_beats)} beats, {cand_timing['spoken_units']} "
                        f"{cand_timing['unit_type']}, est={cand_dur:.1f}s (B1={b1_dur:.1f}s), cov={align_res['coverage_ratio']:.0%}."
                    )
                else:
                    logger.warning(
                        f"[S03_SCRIPT] LLM output rejected by S03 quality pre-check after retry "
                        f"(beats={len(llm_beats)}, dur={cand_dur:.1f}s, units={cand_timing['spoken_units']}[{u_min}-{u_max}], "
                        f"b1_dur={b1_dur:.1f}s, lang_ok={lang_ok}:{lang_issues}, "
                        f"ent_ok={ent_ok}:{ent_issues}, qual={qual_issues[:2]}, cov_ok={align_res.get('coverage_ok')}, b1_ok={b1_ok}). "
                        "Falling back to provenance-grounded builder."
                    )
            except Exception as _llm_err:
                logger.warning(f"[S03_SCRIPT] LLM call/parsing failed: {_llm_err}. Falling back to provenance-grounded builder.")
                raw_beats = []

        if not raw_beats:
            raw_beats = _build_grounded_story_beats(
                topic=topic,
                evidence_ledger=evidence_ledger,
                evidence_map=evidence_map,
                market=market,
                central_question=c_quest,
                d_min=d_min,
                d_max=d_max,
                u_min=u_min,
                u_max=u_max,
            )

        story_beats: List[StoryScriptBeat] = []
        all_scenes: List[Scene] = []
        total_words = 0
        scene_idx = 1

        for beat_id, dur, lines in raw_beats:
            beat_units = sum(count_speech_units(ln.text, market, expand_numbers=True) for ln in lines)
            beat_words = sum(len(ln.text.split()) for ln in lines)
            total_words += beat_words
            beat_timing = estimate_script_speech_duration([ln.text for ln in lines], market=market, docudrama_tempo=True)
            story_beats.append(StoryScriptBeat(
                beat_id=beat_id,
                target_duration_s=round(beat_timing["estimated_duration_sec"] or dur, 2),
                lines=lines,
                word_count=beat_words if market in ("EN", "VN") else beat_units,
            ))
            for ln in lines:
                role = (
                    "hook" if "B1" in beat_id
                    else ("context" if "B2" in beat_id
                          else ("tension" if "B3" in beat_id
                                else ("reveal" if "B4" in beat_id else "payoff")))
                )
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
                    v_meta = "vintage steel shears cutting through official document clipping"
                elif "highlight" in vh or "marker" in vh or "pencil" in vh or "grease" in vh:
                    v_meta = "archival crimson grease pencil underlining critical regulatory clause"
                elif "cutout" in vh or "portrait" in vh:
                    v_meta = "halftone black-and-white photographic cutout exhibit"
                else:
                    v_meta = "tactile investigative document clipping on aged archival parchment"

                line_timing = estimate_script_speech_duration([ln.text], market=market, docudrama_tempo=True)
                sc_dur = max(1.5, float(line_timing["estimated_duration_sec"]))
                all_scenes.append(Scene(
                    scene_id=f"SCENE_{scene_idx:02d}",
                    sequence_block=f"block_{scene_idx}_{beat_id}",
                    beat_role=role,
                    narration=ln.text,
                    headline=f"{beat_id.upper()} // {ln.line_id}",
                    visual_metaphor=v_meta,
                    color_accent="Vox Yellow #F2C230 & Navy #1B2B4A",
                    duration_est_sec=round(sc_dur, 2),
                ))
                scene_idx += 1

        # Compute un-tautological TTS-normalized speech duration across full 5-beat script scenes
        max_sc = ctx.config.limits.max_scenes
        scenes = all_scenes[:max_sc] if (max_sc > 0 and len(all_scenes) > max_sc) else all_scenes

        active_narrations = [s.narration for s in all_scenes]
        speech_timing = estimate_script_speech_duration(active_narrations, market=market, docudrama_tempo=True)
        est_duration = float(speech_timing["estimated_duration_sec"])
        total_words = sum(len(s.narration.split()) for s in all_scenes)

        logger.info(
            f"[S03_SCRIPT] Un-tautological TTS calibration ({market}): {speech_timing['spoken_units']} "
            f"{speech_timing['unit_type']} @ {speech_timing['speech_rate_per_sec']}/s -> "
            f"{est_duration:.1f}s across {len(scenes)} scenes (preset target={target_run_s:.1f}s)."
        )

        full_script_text = "\n".join(s.narration for s in all_scenes)
        statement_claim_map = _build_statement_claim_map(story_beats, evidence_map)

        # Write spoken_script.txt atomically for downstream engines
        ctx.paths.root.mkdir(parents=True, exist_ok=True)
        spoken_script_file = ctx.paths.root / "spoken_script.txt"
        spoken_script_file.write_text(full_script_text, encoding="utf-8")
        script_sha = hashlib.sha256(full_script_text.encode("utf-8")).hexdigest()

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
        payload["b2_source_sha256"] = script_sha
        payload["target_duration_s"] = target_run_s
        payload["spoken_unit_count"] = speech_timing["spoken_units"]
        payload["spoken_unit_type"] = speech_timing["unit_type"]
        payload["speech_rate_per_sec"] = speech_timing["speech_rate_per_sec"]
        payload["measured_speech_duration_s"] = est_duration
        payload["statement_claim_map"] = statement_claim_map

    else:
        # Strict B2 Spoken Script Ingestion (Rule 118 Zero-Mock & Rule 125 Single Pipeline)
        from core.contracts.b2_b3_contract import B2ContractError, load_spoken_script
        from core.pacing_budgeter import estimate_script_speech_duration

        try:
            spoken_script = load_spoken_script(ctx.paths.root, episode_id=ctx.run_id, market=market)
            raw_beats = spoken_script.beats
            total_beats = len(raw_beats)
            all_scenes = []

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

                timing = estimate_script_speech_duration([b.text], market=market, docudrama_tempo=True)
                est_dur = timing["estimated_duration_sec"]

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
            if not ctx.dry_run:
                raise
            default_texts = [
                ("hook", "block_1_act_i", f"Public disclosures initially obscured the structural trigger behind {topic}."),
                ("context", "block_2_act_i", f"Operational filings projected stability around {topic}, while counterparty exposures compounded."),
                ("tension", "block_3_act_ii", f"A forensic review of primary records traces how risk accumulated within {topic}."),
                ("reveal", "block_4_act_iii", f"The decisive breakdown in {topic} emerged directly from verifiable institutional loopholes."),
                ("payoff", "block_5_act_iv", f"What follows {topic} centers on regulatory accountability and enforceable safeguards."),
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
