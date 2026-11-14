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
from typing import Any, Dict, List, Optional, Set, Tuple

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
    slot_idx: int = 0,
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
        slot_idx=slot_idx,
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
            head_part = re.split(r"[:\-—]", t_no_paren)[0].strip()
            topic_base = head_part if len(head_part) >= 4 else t_no_paren
            short = topic_base[:18].strip() if len(topic_base) > 18 else topic_base
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
            return " ".join(words[:8]) if len(words) > 8 else t
        tr = translate_claim_to_market_clause(t, "VN", "vụ việc này")
        words = tr.split()
        return " ".join(words[:8]) if len(words) > 8 else (tr or "vụ việc này")
    words = t.split()
    return " ".join(words[:8]) if len(words) > 8 else t


def _to_kr_attributive(clause: str) -> str:
    """Normalize a Korean factual clause to attach cleanly to noun heads (사실, 점, 내용, 정황)."""
    c = (clause or "").strip().rstrip(". ")
    if not c:
        return c
    repls = [
        (r"(?:있습니다|있었다)$", "있다는"),
        (r"(?:없습니다|없었다)$", "없다는"),
        (r"(?:했습니다|하였다)$", "했다는"),
        (r"(?:됐습니다|되었다)$", "됐다는"),
        (r"(?:였습니다|이었으며|이었고)$", "였다는"),
        (r"입니다$", "라는"),
        (r"습니다$", "다는"),
        (r"했다$", "했다는"),
        (r"됐다$", "됐다는"),
        (r"였다$", "였다는"),
        (r"있다$", "있다는"),
        (r"없다$", "없다는"),
        (r"이다$", "이라는"),
        (r"한다$", "한다는"),
        (r"된다$", "된다는"),
        (r"달한다$", "달한다는"),
        (r"나타났다$", "나타났다는"),
        (r"중단됐다$", "중단됐다는"),
        (r"시작된다$", "시작된다는"),
        (r"지원한다$", "지원한다는"),
        (r"전가했다$", "전가했다는"),
        (r"제공한다$", "제공한다는"),
        (r"이르렀다$", "이르렀다는"),
        (r"정지된다$", "정지된다는"),
        (r"마련했다$", "마련했다는"),
        (r"설치했다$", "설치했다는"),
        (r"회피했다$", "회피했다는"),
    ]
    for pat, rep in repls:
        if re.search(pat, c):
            return re.sub(pat, rep, c)
    if c.endswith("것으로"):
        return c[:-3] + "것이라는"
    if c.endswith("부풀려지다"):
        return c[:-2] + "부풀려졌다는"
    if c.endswith("부풀려졌다"):
        return c[:-2] + "부풀려졌다는"
    if c.endswith("다"):
        return c[:-1] + "다는"
    if c.endswith(("다는", "라는", "은", "는", "인", "된", "한", "울", "를")):
        if c.endswith(("을", "를")):
            return f"{c} 추진했다는"
        return c
    if c.endswith(("이", "가")):
        return f"{c} 발생했다는"
    if c.endswith("공식"):
        return f"{c} 발표했다는"
    if c.endswith(("으로", "로")):
        return f"{c} 알려졌다는"
    if c.endswith("전국"):
        return f"{c}적으로 시행된다는"
    return f"{c}라는"


def _to_kr_honorific(text: str) -> str:
    """Normalize a Korean clause to end cleanly in polite formal honorific (습니다/입니다/합니다/됩니다) without duplication or grammatical mangling."""
    t_clean = re.sub(r"\s+", " ", (text or "").strip()).rstrip(".。")
    if not t_clean:
        return ""
    if t_clean.endswith(("습니다", "입니다", "합니다", "됩니다", "있습니다", "없습니다")):
        return f"{t_clean}."

    # Convert dangling quotation/reported connective endings (e.g. ~마련했다고 -> ~마련했다고 전해졌습니다.)
    if re.search(r"(?:했다고|됐다고|있다고|없다고|된다고|한다고|다는|라는)$", t_clean):
        return f"{t_clean} 전해졌습니다."

    # Convert common mid-sentence conjunctive verbs into declarative past/present stems
    if re.search(r"(?:하고|하며|되고|되며|이고|이며|이고는|면서)$", t_clean):
        t_clean = re.sub(r"(?:하고|하며)$", "했다", t_clean)
        t_clean = re.sub(r"(?:되고|되며)$", "됐다", t_clean)
        t_clean = re.sub(r"(?:이고|이며)$", "이다", t_clean)
        t_clean = re.sub(r"면서$", "했다", t_clean)

    # 1. Past tense verbs ending in ㅆ다 (했다, 됐다, 였다, 났다, 쳤다, 겪었다, 받았다, 멈췄다, 부풀려졌다, etc.)
    if re.search(r"([았었였했됐졌왔뒀썼]다|ㅆ다)$", t_clean):
        return re.sub(r"다$", "습니다.", t_clean)

    # 2. Plain declarative ending in 다
    if t_clean.endswith("다") and len(t_clean) >= 2:
        # 먹는다 / 받는다
        if t_clean.endswith("는다") and len(t_clean) >= 3:
            return t_clean[:-3] + t_clean[-3] + "습니다."
        c = t_clean[-2]
        if '가' <= c <= '힣':
            code = ord(c) - 0xAC00
            jong = code % 28
            if jong == 4:  # Syllable ending in ㄴ (작동한다 -> 작동합니다., 시행된다 -> 시행됩니다., 이른다 -> 이릅니다.)
                return t_clean[:-2] + chr(ord(c) + 13) + "니다."
            elif jong == 0:  # Open vowel syllable (부풀려지다 -> 부풀려집니다., 멈추다 -> 멈춥니다., 보다 -> 봅니다.)
                return t_clean[:-2] + chr(ord(c) + 17) + "니다."
            else:  # Consonant ending (먹다 -> 먹습니다., 있다 -> 있습니다.)
                return t_clean[:-1] + "습니다."

    # 3. Strip trailing grammatical particles before attaching copula입니다.
    t_clean = re.sub(r"(?:은|는|을|를|의|로|으로|에|에서|와|과|이|가)$", "", t_clean).strip()
    if re.search(r"[가-힣0-9a-zA-Z]$", t_clean):
        return f"{t_clean}입니다."
    return f"{t_clean}."


def _soften_kr_reported_predicate(text: str) -> str:
    """Ensure unverified press claims end in reported speech (전해졌습니다/보도됐습니다) rather than definitive established facts."""
    t = text.strip()
    if t.endswith(("전해졌습니다.", "보도됐습니다.", "알려졌습니다.", "설명합니다.", "제시했습니다.")):
        return t
    repls = [
        (r"마련했습니다\.$", "마련한 것으로 전해졌습니다."),
        (r"모집했습니다\.$", "모집한 것으로 보도됐습니다."),
        (r"정체됐습니다\.$", "정체된 것으로 전해졌습니다."),
        (r"이르렀습니다\.$", "이른 것으로 보도됐습니다."),
        (r"지원했습니다\.$", "지원한 것으로 알려졌습니다."),
        (r"설치했습니다\.$", "설치한 것으로 보도됐습니다."),
        (r"작동했습니다\.$", "작동한 것으로 전해졌습니다."),
        (r"전가했습니다\.$", "전가한 것으로 보도됐습니다."),
        (r"제공했습니다\.$", "제공한 것으로 전해졌습니다."),
        (r"회피했습니다\.$", "회피한 것으로 보도됐습니다."),
        (r"했습니다\.$", "한 것으로 보도됐습니다."),
        (r"됐습니다\.$", "된 것으로 전해졌습니다."),
    ]
    for pat, rep in repls:
        if re.search(pat, t):
            return re.sub(pat, rep, t)
    return t


def _trim_clause_smart(text: str, elems: Dict[str, Any], market: str, hook_mode: bool = False) -> str:
    """Bound clause length cleanly for beat tempo without bisecting parentheticals or dropping metrics."""
    clean = re.sub(r"\s+", " ", (text or "").strip()).rstrip(".。")
    # Clean trailing formal polite endings if embedded inside a longer sentence
    if market == "KR":
        if "विकल्प" in clean:
            clean = clean.replace("विकल्प", "선택권")
        clean = re.sub(r"[\u0900-\u097F]+", "", clean).strip()
        pat_kr = r"([가-힣]+[다라])(?:는|고)?\s*(?:보도가\s*나왔다|보도이다|의혹이\s*보도되었다|보도가\s*전해졌다|내용이\s*보도되었다|사실이\s*보도되었다|보도되었다|보도됐다|알려졌다|전해졌다|의혹이\s*제기되었다)$"
        clean = re.sub(pat_kr, r"\1", clean)
        clean = re.sub(r"(?:보도되었다|보도됐다|알려졌다|전해졌다)$", "", clean).strip()
        clean = re.sub(r"([가-힣]+)한\s*것으로$", r"\1했다", clean)
        clean = re.sub(r"([가-힣]+)된\s*것으로$", r"\1됐다", clean)
        clean = re.sub(r"([가-힣]+)인\s*것으로$", r"\1이다", clean)

        cap = 55 if hook_mode else 110
        if len(clean) <= cap:
            return clean
        clauses = [c.strip() for c in re.split(r"[;—]|,\s+", clean) if c.strip()]
        if len(clauses) > 1:
            head = clauses[0]
            conj_repls = [
                (r"하고$", "했다"), (r"하며$", "했다"), (r"되어$", "됐다"),
                (r"되고$", "된다"), (r"이고$", "이다"), (r"으며$", "었다"), (r"고$", "다"),
                (r"지만$", "으나")
            ]
            for c_pat, c_rep in conj_repls:
                if re.search(c_pat, head):
                    head = re.sub(c_pat, c_rep, head)
                    break
            if len(head) <= cap and head.endswith("다"):
                return head

        trimmed = clean
        if trimmed.count("(") > trimmed.count(")"):
            trimmed = trimmed[: trimmed.rfind("(")].strip(" ,;:")
        anchors = (elems.get("metrics", []) + elems.get("dates", []))
        if anchors and not any(a.lower() in trimmed.lower() for a in anchors):
            a0 = anchors[0]
            if len(a0) <= 16 and len(trimmed) + len(a0) + 2 <= cap + 14:
                trimmed = f"{a0} {trimmed}".strip()
        return trimmed.strip(" ,;:")

    if market == "JA":
        pat_ja = r"(?:と(?:報じられた|伝えられた|報じられている|発表された)|との(?:報道|発表)があった)$"
        clean = re.sub(pat_ja, "", clean).strip(" 、,")
        cap = 35 if hook_mode else 85
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

        # Repair severed Japanese verb stems caused by character cap trimming
        if re.search(r"してい$", trimmed):
            trimmed += "ます"
        elif re.search(r"され$", trimmed):
            trimmed += "ました"
        elif re.search(r"行われ$", trimmed):
            trimmed += "ました"
        elif re.search(r"確認され$", trimmed):
            trimmed += "ました"
        elif re.search(r"認められ$", trimmed):
            trimmed += "ました"
        elif re.search(r"明らかになっ$", trimmed):
            trimmed += "た"
        elif re.search(r"[がはをにでともへのや]$", trimmed):
            trimmed = trimmed.rstrip("がはをにでともへのや")
        return trimmed

    if not hook_mode:
        word_cap = 48
    else:
        word_cap = 16 if market in ("VN", "VI") else 14

    if market == "VN":
        pat_vn = r"(?:theo thông tin báo chí|được báo chí phản ánh|theo các nguồn tin ban đầu|theo thông tin được công bố)$"
        clean = re.sub(pat_vn, "", clean).strip(" ,;:")
    elif market == "EN":
        pat_en = r",?\s*(?:according to (?:media|press|news) reports|as reported in (?:media|press) accounts|media reports indicate)\.?$"
        clean = re.sub(pat_en, "", clean, flags=re.IGNORECASE).strip(" ,;:")

    words = clean.split()
    if len(words) <= word_cap:
        return clean

    # Never slice off vital legal qualification clauses starting with 'without'
    if any(w.lower().rstrip(".,;:") == "without" for w in words):
        return clean

    # Avoid severing a currency/number from its scale unit (e.g. "$172.7" | "million")
    if word_cap < len(words) and words[word_cap].lower().rstrip(".,;:") in (
        "million", "billion", "trillion", "thousand", "percent", "%", "m", "b", "usd", "krw", "jpy", "vnd"
    ):
        word_cap += 1
    # Avoid severing multi-word capitalized entities at word boundary
    while word_cap < len(words) and word_cap < 30 and words[word_cap - 1][0].isupper() and words[word_cap][0].isupper():
        word_cap += 1

    # Avoid leaving dangling prepositions, conjunctions, or articles at the end of the sentence
    dangling_words = {
        "the", "a", "an", "of", "in", "to", "for", "with", "and", "or", "by",
        "from", "as", "at", "whose", "which", "that", "their", "its", "into",
    }
    while word_cap < len(words) and words[word_cap - 1].lower().rstrip(".,;:") in dangling_words:
        word_cap += 1

    # Avoid slicing off direct object of key transitive or linking verbs
    transitive_verbs = {
        "prohibits", "prohibit", "requires", "require", "mandates", "mandate",
        "discusses", "establishes", "establish", "forbids", "bars",
        "make", "makes", "making", "create", "creates", "creating",
        "cause", "causes", "causing", "be", "is", "are", "was", "were", "been",
        "have", "has", "had", "named", "identify", "identifies", "concerning",
    }
    if word_cap < len(words) and words[word_cap - 1].lower().rstrip(".,;:") in transitive_verbs:
        word_cap = min(len(words), word_cap + 4)

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
    """Group evidence claims cleanly by credibility hierarchy, verification priority, and causal role."""
    from app.services.story_provenance_engine import (
        credibility_tier_rank,
        verification_priority_rank,
    )

    def _get(obj: Any, attr: str, default: Any = "") -> Any:
        return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)

    sorted_claims = sorted(
        list(evidence_ledger or []),
        key=lambda c: (
            credibility_tier_rank(str(_get(c, "credibility_tier", ""))) if _get(c, "credibility_tier")
            else verification_priority_rank(str(_get(c, "verification_status", "unverified_secondary"))),
            0 if str(_get(c, "legal_status", "")).lower() == "charged" else 1,
            0 if _get(c, "causal_role", "") == "primary_catalyst"
            else (1 if _get(c, "causal_role", "") == "transmission_mechanism" else 2),
        ),
    )
    verified_pool = [
        c for c in sorted_claims
        if str(_get(c, "credibility_tier", "")) in ("verified_fact", "official_regulation")
        or (
            str(_get(c, "verification_status", "unverified_secondary")) in ("verified_primary", "corroborated_secondary")
            and str(_get(c, "credibility_tier", "")) != "unconfirmed_claim"
        )
    ]
    unverified_pool = [
        c for c in sorted_claims
        if c not in verified_pool
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
    from app.services.story_provenance_engine import (
        expected_qualifier_bucket,
        normalize_market_code,
    )

    m = normalize_market_code(market)
    hook_mode = role_slot.startswith("hook_")
    loc_topic = _localized_topic_label(topic, m)
    if claim_obj is None:
        cid = "C001"
        fact = _format_claim_fact(topic, m, topic, hook_mode=hook_mode)
        ls, st, dt, sp, ps, vs = "alleged", "press", "unknown", None, "unknown", "unverified_secondary"
        cred_t = "unconfirmed_claim"
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
        cred_t = str(get_attr("credibility_tier", "") or "")

    bucket = expected_qualifier_bucket(
        legal_status=ls,
        source_type=st,
        doc_type=dt,
        speaker=sp,
        procedural_status=ps,
        verification_status=vs,
        credibility_tier=cred_t,
    )

    # Keep central question concise in Beat 1 so hook never spills over 25s
    cq_clean = re.sub(r"\s+", " ", (central_question or "").strip())
    v_idx = slot_idx % 5

    if m == "KR":
        has_existing_pfx = bool(re.search(
            r"^(?:[가-힣A-Za-z0-9·\s]+(?:보도에 따르면|보도에 의하면|보도는|취재에 따르면|기사에 따르면|보도 내용에 따르면|발표에 따르면|공소장에 따르면|판결에 따르면|기록에 따르면)|보도에 따르면|취재에 따르면|공개된 보도)",
            fact
        ))
        if role_slot == "hook_catalyst":
            fact_h = _to_kr_honorific(fact)
            if has_existing_pfx:
                raw = fact_h if (not loc_topic or loc_topic in fact_h or len(loc_topic) > 12) else f"{loc_topic} 사안에서, {fact_h}"
            elif bucket == "final_judgment":
                raw = f"{loc_topic}의 중대한 국면에서, 법원 확정 판결에 따르면, {fact_h}"
            elif bucket == "audit_finding":
                raw = f"{loc_topic}의 발단에서, 감사원 감사 보고서에 따르면, {fact_h}"
            elif bucket == "indictment":
                raw = f"{loc_topic} 사안에서, 검찰 공소장에 따르면, {fact_h}"
            elif bucket == "court_record":
                raw = f"{loc_topic} 사안에서, 법원 접수 기록에 따르면, {fact_h}"
            elif bucket == "alleged_regulator":
                raw = f"{loc_topic} 사안에서, 정부 발표에 따르면, {fact_h}"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"{loc_topic} 사안에서, 언론 보도에 따르면, {fact_h}"
            elif bucket == "settled":
                raw = f"{loc_topic} 사안은 책임을 인정하지 않고 합의로 종결됐습니다: {fact_h}"
            elif bucket == "unverified":
                raw = f"언론 보도에 따르면, {loc_topic} 사안과 관련하여 {fact_h}"
            else:
                raw = f"{loc_topic} 사안에서, {fact_h}" if loc_topic and loc_topic not in fact else fact_h
        elif role_slot == "hook_scale":
            fact_h = _to_kr_honorific(fact)
            if has_existing_pfx:
                raw = fact_h
            elif bucket == "final_judgment":
                raw = f"법원 확정 판결에 적시된 수치에 따르면, {fact_h}"
            elif bucket == "audit_finding":
                raw = f"감사원 감사 보고서에 적시된 수치에 따르면, {fact_h}"
            elif bucket == "indictment":
                raw = f"검찰 공소장에 적시된 수치에 따르면, {fact_h}"
            elif bucket == "court_record":
                raw = f"법원 접수 기록에 적시된 수치에 따르면, {fact_h}"
            elif bucket == "alleged_regulator":
                raw = f"규제 당국에 따르면, 집계된 수치는 {fact_h}"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"언론 보도 집계에 따르면, {fact_h}"
            elif bucket == "settled":
                raw = f"합의 종결된 수치는 {fact_h} (책임을 인정하지 않고 합의됨)."
            elif bucket == "unverified":
                raw = f"언론 보도 집계에 따르면, {fact_h}"
            else:
                raw = f"집계된 수치에 따르면, {fact_h}"
        elif role_slot == "hook_paradox":
            fact_h = _to_kr_honorific(fact)
            q_short = cq_clean if (cq_clean and 6 <= len(cq_clean) <= 16 and not cq_clean.endswith("?")) else "왜 못 막았을까?"
            if not q_short.endswith("?"):
                q_short += "?"
            if has_existing_pfx:
                raw = f"{q_short} {fact_h}"
            elif bucket == "final_judgment" and not any(p in fact for p in ["판결", "유죄", "선고"]):
                raw = f"{q_short} 법원 판결에 따르면, {fact_h}"
            elif bucket == "audit_finding" and not any(p in fact for p in ["감사", "보고서"]):
                raw = f"{q_short} 감사 보고서에 따르면, {fact_h}"
            elif bucket == "indictment" and not any(p in fact for p in ["공소", "기소"]):
                raw = f"{q_short} 검찰 공소장에 따르면, {fact_h}"
            elif bucket == "court_record" and not any(p in fact for p in ["법원", "기록"]):
                raw = f"{q_short} 법원 접수 기록에 따르면, {fact_h}"
            elif bucket == "alleged_regulator" and not any(p in fact for p in ["당국", "발표", "조사"]):
                raw = f"{q_short} 규제 당국에 따르면, {fact_h}"
            elif bucket in ("alleged", "press_allegation", "press_charge") and not any(p in fact for p in ["보도에 따르면", "취재에 따르면", "보도됐다", "전해졌다"]):
                raw = f"{q_short} 언론 보도에 따르면, {fact_h}"
            elif bucket == "settled" and "합의" not in fact:
                raw = f"{q_short} {fact_h} (책임을 인정하지 않고 합의됨)."
            elif bucket == "unverified" and "보도" not in fact:
                raw = f"{q_short} 언론 보도에 따르면, {fact_h}"
            else:
                raw = f"{q_short} {fact_h}"
        else:
            if bucket == "alleged_regulator":
                p_opts = ["정부 발표에 따르면, ", "관계 기관 공식 자료에 따르면, ", "규제 당국의 공식 발표에 따르면, ", "정부 및 관계 당국에 따르면, ", "당국의 공식 분석 자료를 보면, "]
            elif bucket == "audit_finding":
                p_opts = ["감사 보고서에 따르면, ", "감사원 감사 보고서에 따르면, ", "공식 감사 및 점검 결과에 따르면, ", "감사 결과에 의하면, ", "공식 감사 기록에 의하면, "]
            elif bucket == "unverified":
                p_opts = ["언론 보도에 따르면, ", "취재 보도에 의하면, ", "언론 보도 내용에는, ", "보도된 사실관계에 따르면, ", "언론사 취재 결과에 따르면, "]
            elif bucket == "indictment":
                p_opts = ["검찰 공소장에 따르면, ", "공소 사실에 의하면, ", "검찰 수사 및 공소 내용에 따르면, ", "기소장에 따르면, ", "검찰 기소 내용에 의하면, "]
            elif bucket == "court_record":
                p_opts = ["법원 접수 기록에 따르면, ", "법원 문건에 따르면, ", "사법 기록에 따르면, ", "재판부 접수 기록에 따르면, ", "법원에 제출된 기록을 보면, "]
            elif bucket == "final_judgment":
                p_opts = ["법원 확정 판결에 따르면, ", "법원 판결에 따르면, ", "사법부 판단에 따르면, ", "판결문에 의하면, ", "유죄 확정 판결에 따르면, "]
            elif bucket == "criminal_complaint":
                p_opts = ["제출된 고발장에 따르면, ", "고소장 내용에 따르면, ", "소장을 통해 제기된 바에 따르면, ", "고발장에 의하면, ", "제출된 소장에 따르면, "]
            elif bucket == "settled":
                p_opts = ["관계 기관과의 합의 내용에 따르면, ", "공식 합의 및 조정 기록을 보면, ", "과징금 납부와 함께 이뤄진 합의에 따르면, ", "행정 제재 및 합의 종결 기록에 따르면, ", "당사자 간 합의 종결 내용에 의하면, "]
            elif bucket == "proposed":
                p_opts = ["추진 중인 정책 방침에 따르면, ", "입법 추진 초안에 따르면, ", "당국의 정책 검토 자료를 보면, ", "발의된 법안 초안에 따르면, ", "제도 추진 계획에 따르면, "]
            elif bucket == "fact":
                p_opts = [
                    "현행 법령 및 규정에 따르면, ",
                    "공식 시행 법령에 따르면, ",
                    "제도적 기준과 법률에 따르면, ",
                    "관련 법령의 규정에 따라, ",
                    "확립된 행정 기준에 따르면, ",
                ]
            else:  # alleged (press reporting)
                p_opts = ["언론 보도에 따르면, ", "취재 보도에 의하면, ", "공개된 보도 내용에 따르면, ", "보도된 경위를 보면, ", "언론 취재 결과에 따르면, "]

            pfx = "" if has_existing_pfx else p_opts[v_idx]
            fact_h = _to_kr_honorific(fact)
            if vs == "unverified_secondary" and bucket in ("unverified", "alleged"):
                fact_h = _soften_kr_reported_predicate(fact_h)

            if role_slot == "aftermath":
                aftermath_framings = [
                    f"피해 회복과 제도 보완 국면에서, {fact_h}",
                    f"사태 수습과 재발 방지 논의 과정에서, {fact_h}",
                    f"사후 검증과 구조적 대책 단계에서, {fact_h}",
                    f"제도적 평가와 시장 감시 과정에서, {fact_h}",
                    f"후속 조사와 제도 개선 논의에서, {fact_h}",
                ]
                raw = aftermath_framings[v_idx] if (has_existing_pfx or not pfx) else f"{pfx}{aftermath_framings[v_idx]}"
            elif bucket == "settled":
                raw = f"{pfx}{fact_h.rstrip('.')} (공식적인 잘못을 인정하지 않고 합의됨)."
            else:
                raw = f"{pfx}{fact_h}"

    elif m == "JA":
        if role_slot == "hook_catalyst":
            if bucket == "final_judgment":
                raw = f"{loc_topic}の重大な局面において、裁判所の確定判決によれば、{fact}。"
            elif bucket == "audit_finding":
                raw = f"{loc_topic}の発端において、監査報告書によれば、{fact}。"
            elif bucket == "indictment":
                raw = f"急激な市場の危機において、起訴状の指摘によれば、{fact}。"
            elif bucket == "court_record":
                raw = f"{loc_topic}をめぐり、裁判所の記録によれば、{fact}。"
            elif bucket == "alleged_regulator":
                raw = f"{loc_topic}をめぐり、当局の公表によれば、{fact}。"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"{loc_topic}をめぐり、報道によれば、{fact}。"
            elif bucket == "settled":
                raw = f"{loc_topic}をめぐり、違法性を認めることなく和解に至りました：{fact}。"
            elif bucket == "unverified":
                raw = f"未確認の初期報道によれば、{loc_topic}に関して{fact}。"
            else:
                raw = f"{loc_topic}をめぐり、{fact}。" if loc_topic and loc_topic not in fact else f"{fact}。"
        elif role_slot == "hook_scale":
            if bucket == "final_judgment":
                raw = f"確定判決の記録によれば、規模は{fact}。"
            elif bucket == "audit_finding":
                raw = f"監査報告書の指摘によれば、規模は{fact}。"
            elif bucket == "indictment":
                raw = f"起訴状の指摘によれば、規模は{fact}。"
            elif bucket == "court_record":
                raw = f"裁判所の記録によれば、規模は{fact}。"
            elif bucket == "alleged_regulator":
                raw = f"当局の公表資料によれば、規模は{fact}。"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"報道によれば、確認された規模として{fact}。"
            elif bucket == "settled":
                raw = f"合意規模として、{fact}（違法性を認めることなく和解）。"
            elif bucket == "unverified":
                raw = f"未確認の初期報道によれば、規模は{fact}。"
            else:
                raw = f"確認された規模として、{fact}。"
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean) <= 16) else "なぜ止められたはずが放置されたか。"
            if not q_short.endswith(("か。", "？", "?")):
                q_short = f"{q_short.rstrip(' 。')}か。"
            if bucket == "final_judgment" and not any(p in fact for p in ["判決", "確定"]):
                raw = f"{q_short} 裁判所の判決によれば、{fact}。"
            elif bucket == "audit_finding" and not any(p in fact for p in ["監査", "検査"]):
                raw = f"{q_short} 監査報告書によれば、{fact}。"
            elif bucket == "indictment" and not any(p in fact for p in ["起訴", "検察"]):
                raw = f"{q_short} 起訴状によれば、{fact}。"
            elif bucket == "court_record" and not any(p in fact for p in ["裁判所", "記録"]):
                raw = f"{q_short} 裁判所の記録によれば、{fact}。"
            elif bucket == "alleged_regulator" and not any(p in fact for p in ["当局", "公表"]):
                raw = f"{q_short} 当局の公表によれば、{fact}。"
            elif bucket in ("alleged", "press_allegation", "press_charge") and "報道" not in fact:
                raw = f"{q_short} 報道によれば、{fact}。"
            elif bucket == "settled" and "和解" not in fact:
                raw = f"{q_short} {fact}（違法性を認めることなく和解）。"
            elif bucket == "unverified" and "未確認" not in fact:
                raw = f"{q_short} 未確認の初期報道によれば、{fact}。"
            else:
                raw = f"{q_short} {fact}。"
        else:
            if bucket == "alleged_regulator":
                p_opts = ["当局の発表によれば、", "公表資料によれば、", "監督当局の報告書によれば、", "公的機関の公表資料によれば、", "当局の公表によれば、"]
            elif bucket == "audit_finding":
                p_opts = ["監査報告書によれば、", "検査報告の指摘によれば、", "公式監査記録によれば、", "第三者委員会の監査報告書によれば、", "監査結果によれば、"]
            elif bucket == "unverified":
                p_opts = ["未確認の初期報道によれば、", "確認前の報道段階ですが、", "公的確認前の初期報道では、", "未確認の資料によれば、", "初期報道の記述によれば、"]
            elif bucket == "indictment":
                p_opts = ["起訴状によれば、", "起訴状の指摘によれば、", "検察の起訴状によれば、", "検察の発表によれば、", "公判提出の起訴状によれば、"]
            elif bucket == "court_record":
                p_opts = ["裁判所の記録によれば、", "法廷記録によれば、", "裁判所に提出された記録によれば、", "裁判所記録によれば、", "公判記録によれば、"]
            elif bucket == "final_judgment":
                p_opts = ["裁判所の確定判決によれば、", "確定判決によれば、", "裁判所の判決によれば、", "有罪判決の記録によれば、", "確定判決の記述によれば、"]
            elif bucket == "criminal_complaint":
                p_opts = ["訴状によれば、", "告訴状によれば、", "訴状の主張によれば、", "提出された訴状によれば、", "告訴内容によれば、"]
            elif bucket == "settled":
                p_opts = ["違法性を認めることなく成立した和解によれば、", "公表された和解合意によれば、", "課徴金納付と和解の記録によれば、", "当事者間の合意終結によれば、", "合意に基づく和解によれば、"]
            elif bucket == "proposed":
                p_opts = ["検討・予定段階の公表案によれば、", "予定されている推進計画によれば、", "公表された骨子案によれば、", "制度改革の検討資料によれば、", "推進方針の公表内容によれば、"]
            elif bucket == "fact":
                p_opts = ["現行の法令及び規定によれば、", "施行法令の定めに従い、", "制度上の法規範によれば、", "公的基準の定めに従って、", "確立された法制度の枠組みでは、"]
            else:
                p_opts = ["報道によれば、", "取材によれば、", "公表報道によれば、", "報じられた経緯によれば、", "取材報道の記述によれば、"]

            pfx = p_opts[v_idx]
            if role_slot == "setup":
                tails = [f"{fact}という点が初期から伝えられています。", f"{fact}との経緯が基礎資料に記されています。", f"{fact}という点が発端の文書で確認できます。", f"{fact}との内容が初期段階の記録に残されています。", f"{fact}という事実が資料の冒頭に挙げられています。"]
            elif role_slot == "mechanism":
                tails = [f"{fact}という実態が仕組みの記録に示されています。", f"{fact}との流れが取引の文書で確認できます。", f"{fact}という記述が詳細な記録に続きます。", f"{fact}との点が制度上の該当箇所に挙げられています。", f"{fact}という経緯が推移を追った文書に示されています。"]
            elif role_slot == "crack":
                tails = [f"{fact}という内容が後続局面の資料に記されています。", f"{fact}との点が変化の表面化段階で見られます。", f"{fact}という事実が後続の公表記録に挙げられています。", f"{fact}との展開が一連の記録後半に示されています。", f"{fact}という事態が関係資料の後半で確認されます。"]
            else:
                tails = [f"{fact}という点が事後の整理資料に残されています。", f"{fact}との内容が経過をまとめた記録に続きます。", f"{fact}という状況が一連の末尾文書に記されています。", f"{fact}との事実が総括部分の記述に挙げられます。", f"{fact}という教訓が記録全体の結びとして残ります。"]
            raw = f"{pfx}{tails[v_idx]}"

    elif m == "VN":
        if role_slot == "hook_catalyst":
            if bucket == "final_judgment":
                raw = f"Bước ngoặt trong {loc_topic}: Theo phán quyết của tòa án, {fact}."
            elif bucket == "audit_finding":
                raw = f"Trong cuộc thanh tra {loc_topic}: Theo kết luận thanh tra, {fact}."
            elif bucket == "indictment":
                raw = f"Trong cuộc khủng hoảng {loc_topic}, Theo cáo trạng của cơ quan công tố, {fact}."
            elif bucket == "court_record":
                raw = f"Trong vụ việc {loc_topic}: Theo hồ sơ tại tòa án, {fact}."
            elif bucket == "alleged_regulator":
                raw = f"Trong vụ việc {loc_topic}: Theo cơ quan chức năng, {fact}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"Trong bối cảnh {loc_topic}, theo phản ánh của báo chí, {fact}."
            elif bucket == "settled":
                raw = f"Vụ việc {loc_topic} khép lại bằng thỏa thuận dàn xếp: {fact}."
            elif bucket == "unverified":
                raw = f"Theo thông tin bước đầu chưa kiểm chứng về {loc_topic}: {fact}."
            else:
                raw = f"Trong bối cảnh {loc_topic}, {fact}." if loc_topic and loc_topic not in fact else f"{fact}."
        elif role_slot == "hook_scale":
            if bucket == "final_judgment":
                raw = f"Theo bản án có hiệu lực, quy mô xác nhận: {fact}."
            elif bucket == "audit_finding":
                raw = f"Báo cáo kiểm toán xác định quy mô: {fact}."
            elif bucket == "indictment":
                raw = f"Hồ sơ truy tố xác nhận quy mô: {fact}."
            elif bucket == "court_record":
                raw = f"Theo hồ sơ tại tòa án, quy mô xác nhận: {fact}."
            elif bucket == "alleged_regulator":
                raw = f"Theo cơ quan quản lý, quy mô xác nhận: {fact}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"Theo thông tin báo chí, quy mô xác nhận: {fact}."
            elif bucket == "settled":
                raw = f"Quy mô xử lý xác nhận: {fact} (dàn xếp mà không thừa nhận sai phạm)."
            elif bucket == "unverified":
                raw = f"Theo phản ánh ban đầu chưa kiểm chứng, quy mô ước tính: {fact}."
            else:
                raw = f"Quy mô xác nhận: {fact}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean.split()) <= 8) else "Vì sao cảnh báo bị bỏ qua?"
            if not q_short.endswith("?"):
                q_short += "?"
            if bucket == "final_judgment" and not any(p in fact for p in ["tòa", "phán quyết", "bản án"]):
                raw = f"{q_short} Theo phán quyết của tòa án, {fact}."
            elif bucket == "audit_finding" and not any(p in fact for p in ["kiểm toán", "thanh tra"]):
                raw = f"{q_short} Theo kết luận thanh tra, {fact}."
            elif bucket == "indictment" and not any(p in fact for p in ["truy tố", "cáo trạng"]):
                raw = f"{q_short} Theo cáo trạng của cơ quan công tố, {fact}."
            elif bucket == "court_record" and not any(p in fact for p in ["tòa án", "hồ sơ tại tòa"]):
                raw = f"{q_short} Theo hồ sơ tại tòa án, {fact}."
            elif bucket == "alleged_regulator" and not any(p in fact for p in ["cơ quan", "thanh tra", "công bố"]):
                raw = f"{q_short} Theo cơ quan chức năng, {fact}."
            elif bucket in ("alleged", "press_allegation", "press_charge") and "báo chí" not in fact.lower():
                raw = f"{q_short} Theo thông tin báo chí phản ánh, {fact}."
            elif bucket == "settled" and not any(p in fact for p in ["dàn xếp", "hòa giải"]):
                raw = f"{q_short} {fact} (thỏa thuận dàn xếp không thừa nhận sai phạm)."
            elif bucket == "unverified" and "chưa kiểm chứng" not in fact:
                raw = f"{q_short} Theo thông tin bước đầu chưa kiểm chứng, {fact}."
            else:
                raw = f"{q_short} {fact}."
        else:
            if bucket == "alleged_regulator":
                p_opts = ["Theo cơ quan chức năng, ", "Theo báo cáo từ cơ quan quản lý, ", "Theo kết luận từ cơ quan chuyên môn, ", "Theo công bố của cơ quan thanh tra, ", "Theo ghi nhận của các cơ quan quản lý, "]
            elif bucket == "audit_finding":
                p_opts = ["Theo báo cáo kiểm toán, ", "Theo kết luận thanh tra và kiểm toán, ", "Báo cáo kiểm toán độc lập chỉ rõ, ", "Theo kết quả kiểm tra chính thức, ", "Kết luận thanh tra của cơ quan quản lý nêu rõ, "]
            elif bucket == "unverified":
                p_opts = ["Theo thông tin bước đầu chưa kiểm chứng, ", "Nguồn tin ban đầu chưa có kết luận chính thức cho biết ", "Theo phản ánh ban đầu chưa xác minh, ", "Theo các nguồn tin bước đầu chưa được xác minh, ", "Thông tin ban đầu chưa kiểm chứng phản ánh "]
            elif bucket == "indictment":
                p_opts = ["Theo cáo trạng của cơ quan công tố, ", "Theo cáo trạng, ", "Cáo trạng của viện kiểm sát chỉ rõ, ", "Theo hồ sơ truy tố, ", "Cơ quan công tố cáo buộc, "]
            elif bucket == "court_record":
                p_opts = ["Theo hồ sơ tại tòa án, ", "Theo tài liệu tố tụng thụ lý, ", "Theo hồ sơ lưu trữ tại tòa, ", "Theo hồ sơ tòa án, ", "Theo tài liệu nộp tại tòa án, "]
            elif bucket == "final_judgment":
                p_opts = ["Theo phán quyết của tòa án, ", "Theo bản án đã có hiệu lực, ", "Tòa án tuyên ", "Theo quyết định của cơ quan xét xử, ", "Bản án của tòa khẳng định "]
            elif bucket == "criminal_complaint":
                p_opts = ["Theo đơn kiện gửi cơ quan thẩm quyền, ", "Theo đơn tố cáo và hồ sơ khởi kiện, ", "Theo nội dung đơn khởi kiện, ", "Hồ sơ khởi kiện ghi nhận ", "Theo đơn kiện, "]
            elif bucket == "settled":
                p_opts = ["Theo thỏa thuận dàn xếp mà không thừa nhận sai phạm, ", "Theo biên bản hòa giải và xử lý vi phạm, ", "Thỏa thuận dàn xếp chính thức ghi nhận, ", "Theo kết quả hòa giải đã được xác lập, ", "Biên bản xử lý hành chính và dàn xếp ghi rõ, "]
            elif bucket == "proposed":
                p_opts = ["Theo đề xuất đang trong quá trình xem xét, ", "Theo phương án dự thảo đang hoàn thiện, ", "Theo định hướng chính sách đang lấy ý kiến, ", "Dự thảo chính sách mới đề xuất, ", "Phương án cải cách thể chế dự kiến, "]
            elif bucket == "fact":
                p_opts = ["Theo quy định pháp luật hiện hành, ", "Theo chuẩn mực pháp lý và thể chế, ", "Căn cứ khung pháp lý có hiệu lực, ", "Theo quy chuẩn pháp lý chính thức, ", "Hệ thống pháp luật quy định rõ "]
            else:
                p_opts = ["Theo thông tin báo chí phản ánh, ", "Theo các nguồn tin truyền thông, ", "Theo phản ánh từ báo chí, ", "Ghi nhận từ các phương tiện truyền thông, ", "Theo tường thuật của báo chí, "]

            pfx = p_opts[v_idx]
            if role_slot == "setup":
                tails = [f"việc {fact} đã được tài liệu ghi nhận rõ.", f"{fact}, đặt nền tảng ban đầu cho toàn bộ chuỗi giao dịch.", f"dữ liệu khởi đầu cho thấy {fact}, mở ra diễn biến phức tạp tiếp theo.", f"{fact}, tạo tiền đề cho các diễn biến tiếp theo.", f"những ghi chép mở đầu xác nhận việc {fact} trước khi sự việc mở rộng."]
            elif role_slot == "mechanism":
                tails = [f"khi xem xét chi tiết cơ chế, việc {fact} được tài liệu ghi nhận cụ thể.", f"{fact}, thể hiện áp lực tài chính trong giai đoạn này.", f"phân tích chuỗi dòng tiền cho thấy {fact}, tạo nút thắt lớn cho thanh khoản.", f"{fact}, tạo ra kẽ hở trong quản lý và giám sát.", f"theo trình tự dữ liệu công bố, {fact} là mắt xích dẫn đến sai phạm."]
            elif role_slot == "crack":
                tails = [f"ở bước ngoặt điều tra tiếp theo, hồ sơ xác định việc {fact} có dấu hiệu bất thường.", f"{fact}, dẫn tới các biện pháp xử lý và can thiệp từ cơ quan chức năng.", f"các ghi nhận công khai sau đó cho thấy {fact}, buộc các bên phải vào cuộc.", f"{fact}, phơi bày sai phạm trong quản trị.", f"hồ sơ điều tra giai đoạn này ghi nhận việc {fact} như một chứng cứ then chốt."]
            else:
                tails = [f"trong phần tổng kết hồ sơ, tài liệu nêu rõ việc {fact} đã để lại tổn thất lớn.", f"{fact}, để lại hệ quả pháp lý và nghĩa vụ tài chính kéo dài.", f"các kết luận sau sự kiện tiếp tục khẳng định việc {fact} là bài học quản trị đắt giá.", f"{fact}, trở thành bài học cảnh báo sâu sắc cho thị trường.", f"nhìn lại toàn bộ chuỗi chứng cứ, hồ sơ chỉ rõ việc {fact} khó có thể đảo ngược."]
            raw = f"{pfx}{tails[v_idx]}"

    else:  # EN
        if role_slot == "hook_catalyst":
            if bucket == "final_judgment":
                raw = f"Critical turning point in {loc_topic}: According to the court ruling, {fact}."
            elif bucket == "audit_finding":
                raw = f"Crisis trigger in {loc_topic}: According to the audit report, {fact}."
            elif bucket == "indictment":
                raw = f"Crisis trigger in {loc_topic}: According to the indictment, {fact}."
            elif bucket == "court_record":
                raw = f"Crisis trigger in {loc_topic}: According to court records, {fact}."
            elif bucket == "alleged_regulator":
                raw = f"Crisis trigger in {loc_topic}: According to regulatory filings, {fact}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"Crisis trigger in {loc_topic}: According to press reports, {fact}."
            elif bucket == "settled":
                raw = f"{loc_topic} concluded under terms of settlement: {fact}."
            elif bucket == "unverified":
                raw = f"According to preliminary unconfirmed reports regarding {loc_topic}: {fact}."
            else:
                raw = f"Crisis trigger in {loc_topic}: {fact}." if loc_topic and loc_topic not in fact else f"Crisis trigger: {fact}."
        elif role_slot == "hook_scale":
            if bucket == "final_judgment":
                raw = f"Judicial findings establish documented scale: {fact}."
            elif bucket == "audit_finding":
                raw = f"Audit findings establish documented scale: {fact}."
            elif bucket == "indictment":
                raw = f"Charging documents state documented scale: {fact}."
            elif bucket == "court_record":
                raw = f"According to court records, documented scale reached: {fact}."
            elif bucket == "alleged_regulator":
                raw = f"Regulatory filings establish documented scale: {fact}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"According to press reports, documented scale reached: {fact}."
            elif bucket == "settled":
                raw = f"Documented scale under resolved terms: {fact} (settled without admitting wrongdoing)."
            elif bucket == "unverified":
                raw = f"Early unverified reports suggest documented scale: {fact}."
            else:
                raw = f"Verified scale: {fact}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean.split()) <= 8) else "Why did early oversight fail?"
            if not q_short.endswith("?"):
                q_short += "?"
            if bucket == "final_judgment" and not any(p in fact.lower() for p in ["court", "ruling", "verdict"]):
                raw = f"{q_short} According to the court ruling, {fact}."
            elif bucket == "audit_finding" and not any(p in fact.lower() for p in ["audit", "inspector general"]):
                raw = f"{q_short} According to the audit report, {fact}."
            elif bucket == "indictment" and not any(p in fact.lower() for p in ["indictment", "prosecutors", "charging"]):
                raw = f"{q_short} Charging documents state that {fact}."
            elif bucket == "court_record" and not any(p in fact.lower() for p in ["court records", "docket", "filings"]):
                raw = f"{q_short} According to court records, {fact}."
            elif bucket == "alleged_regulator" and not any(p in fact.lower() for p in ["regulatory", "regulators", "filings"]):
                raw = f"{q_short} According to regulatory filings, {fact}."
            elif bucket in ("alleged", "press_allegation", "press_charge") and not any(p in fact.lower() for p in ["reports", "reported", "press"]):
                raw = f"{q_short} According to press reports, {fact}."
            elif bucket == "settled" and "settled" not in fact.lower():
                raw = f"{q_short} {fact} (settled without admitting wrongdoing)."
            elif bucket == "unverified" and "unverified" not in fact.lower():
                raw = f"{q_short} Early unverified reports suggest that {fact}."
            else:
                raw = f"{q_short} {fact}."
        else:
            if bucket == "alleged_regulator":
                p_opts = [
                    "According to regulatory filings, ",
                    "Regulatory records establish that ",
                    "According to official findings, ",
                    "As regulators documented in filings, ",
                    "Official regulatory disclosures note that ",
                ]
            elif bucket == "audit_finding":
                p_opts = [
                    "According to the audit report, ",
                    "Audit exhibits and findings establish, ",
                    "As documented in official audit exhibits, ",
                    "The official audit examination revealed that ",
                    "Audits uncovered records showing that ",
                ]
            elif bucket == "unverified":
                p_opts = [
                    "According to preliminary unconfirmed reports, ",
                    "Early unverified reports suggest that ",
                    "Initial reports pending verification indicate that ",
                    "According to unconfirmed accounts at the time, ",
                    "Early reporting reflects unverified claims that ",
                ]
            elif bucket == "indictment":
                p_opts = [
                    "According to the indictment, ",
                    "Charging documents state that ",
                    "Prosecutors alleged in the indictment that ",
                    "According to formal charging documents, ",
                    "The indictment alleges that ",
                ]
            elif bucket == "court_record":
                p_opts = [
                    "According to court records, ",
                    "According to official docket filings, ",
                    "Judicial records reflect that ",
                    "Court filings indicate that ",
                    "Docket records reflect that ",
                ]
            elif bucket == "final_judgment":
                p_opts = [
                    "According to the court ruling, ",
                    "As ruled by the court, ",
                    "According to final judicial findings, ",
                    "The court ruled that ",
                    "Judicial findings establish that ",
                ]
            elif bucket == "criminal_complaint":
                p_opts = [
                    "According to the complaint, ",
                    "As alleged in the complaint, ",
                    "According to the civil lawsuit filing, ",
                    "The complaint alleges that ",
                    "Lawsuit filings allege that ",
                ]
            elif bucket == "settled":
                p_opts = [
                    "Under the terms of the settlement, ",
                    "Settlement disclosures establish that ",
                    "Without admitting wrongdoing, the parties agreed that ",
                    "Under the resolved consent decree, ",
                    "Official settlement disclosures indicate that ",
                ]
            elif bucket == "proposed":
                p_opts = [
                    "Under the proposed draft framework, ",
                    "According to preliminary policy proposals, ",
                    "Under the pending regulatory plan, ",
                    "Draft administrative rules propose that ",
                    "Initial policy frameworks under consideration suggest that ",
                ]
            elif bucket == "fact":
                p_opts = [
                    "Under established law, ",
                    "As codified in official regulations, ",
                    "Statutory provisions establish that ",
                    "Under the governing regulatory framework, ",
                    "Official administrative standards establish that ",
                ]
            else:  # alleged (press)
                p_opts = [
                    "According to press reports, ",
                    "Media reporting reflects that ",
                    "Published reporting indicates that ",
                    "Press investigations documented that ",
                    "As reported in published accounts, ",
                ]

            pfx = p_opts[v_idx]
            fact_clean = fact.strip().rstrip(". ")
            if pfx:
                if pfx.rstrip().endswith("that") and fact_clean and fact_clean[0].isupper():
                    first_word = fact_clean.split()[0]
                    if not first_word.isupper() and first_word not in (
                        "European", "American", "Korean", "Japanese", "Vietnamese", "Article", "Under", "Review",
                    ):
                        fact_clean = fact_clean[0].lower() + fact_clean[1:]
                raw = f"{pfx}{fact_clean}."
            else:
                raw = f"{fact_clean}."

    return raw, [cid]


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
        + [c for c in verified_pool if c not in pools["catalysts"]]
        or all_claims
    )
    b2_source = pools["backgrounds"] or verified_pool or all_claims
    b3_source = pools["mechanisms"] or verified_pool or all_claims
    b4_source = (pools["unverified_pool"] + pools["mechanisms"] + pools["catalysts"]) or all_claims
    b5_source = (
        [c for c in pools["unverified_pool"] if c not in pools["mechanisms"]]
        + pools["backgrounds"]
        + [c for c in verified_pool if c not in pools["catalysts"]]
        or all_claims
    )

    # Deterministic claim cursor to maximize unique coverage across the entire ledger (>= 70%)
    claim_counts: Dict[str, int] = {}
    recent_picks: List[str] = []

    def _get_cid(cand: Any) -> str:
        return cand.get("claim_id") if isinstance(cand, dict) else getattr(cand, "claim_id", "")

    def _pick_claim(
        preferred: List[Any],
        restrict_to_preferred: bool = False,
        disallow_cids: Optional[Set[str]] = None,
    ) -> Any:
        if not all_claims:
            return None
        disallowed = set(disallow_cids or set())

        # 1. Unused claims from preferred pool
        for cand in preferred:
            cid = _get_cid(cand)
            if cid and cid not in disallowed and claim_counts.get(cid, 0) == 0:
                claim_counts[cid] = claim_counts.get(cid, 0) + 1
                recent_picks.append(cid)
                return cand

        # 2. Unused claims from all_claims
        if not restrict_to_preferred:
            for cand in all_claims:
                cid = _get_cid(cand)
                if cid and cid not in disallowed and claim_counts.get(cid, 0) == 0:
                    claim_counts[cid] = claim_counts.get(cid, 0) + 1
                    recent_picks.append(cid)
                    return cand

        # 3. If all claims used, pick least frequently used claim that wasn't used in last 2 picks
        pool = preferred if (restrict_to_preferred and preferred) else all_claims
        eligible = [c for c in pool if _get_cid(c) not in disallowed and _get_cid(c) not in recent_picks[-2:]]
        if not eligible:
            eligible = [c for c in pool if _get_cid(c) not in disallowed] or pool

        sorted_eligible = sorted(eligible, key=lambda c: claim_counts.get(_get_cid(c), 0))
        chosen = sorted_eligible[0]
        cid = _get_cid(chosen)
        claim_counts[cid] = claim_counts.get(cid, 0) + 1
        recent_picks.append(cid)
        return chosen

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
    b1_catalyst_cid: Optional[str] = None
    for beat_id, dur_s, slots in beat_specs:
        beat_lines: List[StorySceneLine] = []
        is_hook_beat = beat_id.startswith("B1")
        is_aftermath = beat_id.startswith("B5")
        for l_idx, (role_slot, src_pool) in enumerate(slots, start=1):
            disallowed: Set[str] = set()
            used_in_prior = {
                cid
                for b_prior in raw_beats
                for ln_p in b_prior[2]
                for cid in (ln_p.claim_ids or [])
            }
            unused_in_pool = [c for c in src_pool if _get_cid(c) and _get_cid(c) not in used_in_prior]
            if unused_in_pool:
                disallowed.update(used_in_prior)
            elif is_aftermath:
                if b1_catalyst_cid:
                    disallowed.add(b1_catalyst_cid)
                for b_prior in raw_beats[:3]:
                    for ln_p in b_prior[2]:
                        disallowed.update(ln_p.claim_ids or [])
            elif not is_hook_beat:
                if b1_catalyst_cid:
                    disallowed.add(b1_catalyst_cid)
            c_obj = _pick_claim(
                src_pool,
                restrict_to_preferred=(is_hook_beat and bool(verified_pool)),
                disallow_cids=disallowed,
            )
            if is_hook_beat and l_idx == 1:
                b1_catalyst_cid = _get_cid(c_obj)
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

    # 1. Ensure Beat 1 stays concise (<= 24.0s) WITHOUT mangling trailing legal qualifiers
    b1_texts = [ln.text for ln in raw_beats[0][2]]
    b1_dur = float(estimate_script_speech_duration(b1_texts, market=m, docudrama_tempo=True)["estimated_duration_sec"])
    if b1_dur > 24.0 and len(raw_beats[0][2]) > 3:
        while b1_dur > 24.0 and len(raw_beats[0][2]) > 3:
            raw_beats[0][2].pop()
            b1_dur = float(
                estimate_script_speech_duration([ln.text for ln in raw_beats[0][2]], market=m, docudrama_tempo=True)["estimated_duration_sec"]
            )
    if b1_dur > 24.0 and m == "KR":
        raw_beats[0][2][0].text = re.sub(r"^[가-힣0-9a-zA-Z\s]+ 사안에서,\s*", "", raw_beats[0][2][0].text)
        b1_dur = float(
            estimate_script_speech_duration([ln.text for ln in raw_beats[0][2]], market=m, docudrama_tempo=True)["estimated_duration_sec"]
        )
    if b1_dur > 24.0:
        for idx in (2, 1, 0):
            if b1_dur <= 24.0:
                break
            ln_cur = raw_beats[0][2][idx]
            cur_t = ln_cur.text
            if len(cur_t) > 22:
                if idx == 2 and any(sep in cur_t for sep in ("?", "？", "か。")):
                    sep_used = "か。" if "か。" in cur_t else ("？" if "？" in cur_t else "?")
                    q_part, _, rem = cur_t.partition(sep_used)
                    q_text = f"{q_part.strip()}{sep_used}"
                    if m == "JA":
                        rem_clauses = [c.strip(" 、") for c in re.split(r"[、,]", rem) if c.strip(" 、")]
                        rem_shrunk = rem_clauses[0][:20].rstrip(" 、") if rem_clauses else rem[:20].rstrip(" 、")
                        if rem_shrunk and not rem_shrunk.endswith(("。", "！", "？")):
                            rem_shrunk += "。"
                        ln_cur.text = f"{q_text} {rem_shrunk}".strip()
                    elif m == "KR":
                        rem_clean = rem.strip()
                        m_r = re.search(r"^(.*?(?:따르면|의하면|보면|기록에서|사안에서|자료에서|보고서에서|결과에서),)\s*(.*)$", rem_clean)
                        if m_r:
                            pfx_r = m_r.group(1).strip()
                            fact_r = m_r.group(2).strip()
                        else:
                            pfx_r = ""
                            fact_r = rem_clean
                        r_words = fact_r.split()
                        if len(r_words) > 4:
                            shrunk_r = _to_kr_honorific(' '.join(r_words[:4]).rstrip(" ,;:"))
                        else:
                            shrunk_r = _to_kr_honorific(fact_r)
                        rem_shrunk = f"{pfx_r} {shrunk_r}".strip()
                        ln_cur.text = f"{q_text} {rem_shrunk}".strip()
                    else:
                        rem_words = rem.strip().split()
                        rem_shrunk = " ".join(rem_words[:8]).rstrip(" ,;:")
                        if rem_shrunk and not rem_shrunk.endswith((".", "!", "?")):
                            rem_shrunk += "."
                        ln_cur.text = f"{q_text} {rem_shrunk}".strip()
                else:
                    paren_match = re.search(r"\s*(\([^()]+\))\s*[.。!?]?$", cur_t)
                    paren_suffix = paren_match.group(1) if paren_match else ""
                    main_body = cur_t[: paren_match.start()].strip() if paren_match else cur_t.strip().rstrip(".。!?")

                    if m in ("EN", "VN"):
                        words = main_body.split()
                        cap_words = 12 if len(words) > 14 else len(words)
                        shrunk_main = " ".join(words[:cap_words]).rstrip(" ,;:")
                        if paren_suffix:
                            ln_cur.text = f"{shrunk_main} {paren_suffix}."
                        else:
                            if not shrunk_main.endswith((".", "!", "?")):
                                shrunk_main += "."
                            ln_cur.text = shrunk_main
                    elif m == "JA":
                        clauses = [c.strip(" 、") for c in re.split(r"[;—、,]", main_body) if c.strip(" 、")]
                        shrunk_main = clauses[0][:26].rstrip(" 、がはをにでともへのや") if clauses else main_body[:26].rstrip(" 、がはをにでともへのや")
                        if re.search(r"してい$", shrunk_main):
                            shrunk_main += "ます"
                        elif re.search(r"され$", shrunk_main):
                            shrunk_main += "ました"
                        elif re.search(r"行われ$", shrunk_main):
                            shrunk_main += "ました"
                        elif re.search(r"確認され$", shrunk_main):
                            shrunk_main += "ました"
                        elif re.search(r"認められ$", shrunk_main):
                            shrunk_main += "ました"
                        if paren_suffix:
                            ln_cur.text = f"{shrunk_main}{paren_suffix}。"
                        else:
                            if not shrunk_main.endswith(("。", "！", "？")):
                                shrunk_main += "。"
                            ln_cur.text = shrunk_main
                    else:  # KR
                        m_m = re.search(r"^(.*?(?:따르면|의하면|보면|기록에서|사안에서|자료에서|보고서에서|결과에서),)\s*(.*)$", main_body)
                        if m_m:
                            pfx_m = m_m.group(1).strip()
                            fact_m = m_m.group(2).strip()
                        else:
                            pfx_m = ""
                            fact_m = main_body
                        m_words = fact_m.split()
                        if len(m_words) > 4:
                            shrunk_m = _to_kr_honorific(' '.join(m_words[:4]).rstrip(" ,;:"))
                        else:
                            shrunk_m = _to_kr_honorific(fact_m)
                        shrunk_main = f"{pfx_m} {shrunk_m}".strip()
                        if paren_suffix:
                            ln_cur.text = f"{shrunk_main.rstrip('.')} {paren_suffix}."
                        else:
                            ln_cur.text = f"{shrunk_main.rstrip('.')}."
            b1_dur = float(
                estimate_script_speech_duration([ln.text for ln in raw_beats[0][2]], market=m, docudrama_tempo=True)["estimated_duration_sec"]
            )

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
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} spoken Hangul+numeral syllables across 19-24 lines). Beat 1 (B1_hook) MUST have ONLY 3 concise lines totaling <= 98 syllables (~15-20s) and cite ONLY verified_primary or corroborated_secondary claim_ids (NEVER put unverified_secondary claim_ids inside B1_hook!).\n"
                        "3. LEGAL & PROVENANCE ATTRIBUTION:\n"
                        "   - Cite valid claim_ids on every factual line. Do NOT mix unverified_secondary and corroborated/primary claim_ids on the same line unless framed as preliminary/unverified.\n"
                        "   - Distinguish 'court_judgment' (법원 확정 판결에 따르면) vs 'indictment' (검찰 공소장에 따르면) vs 'criminal_complaint' (고발장·소장에 따르면) vs 'press' reports (보도에 따르면).\n"
                        "   - NEVER elevate 'unverified_secondary' claims into Beat 1's opening core premise; attribute them explicitly as preliminary/unverified.\n"
                        "   - Avoid repetitive explainer disclaimers or speculative causal leaps.\n\n"
                    )
                elif market == "JA":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR JAPANESE (JA) MARKET:\n"
                        "1. Write 100% natural, authoritative Japanese investigative narration. No Hangul or foreign sentences.\n"
                        f"2. STRICT LENGTH & PACING: Write 23-28 substantive lines of 50-65 Japanese characters each so total spoken narration is STRICTLY 1,100-1,600 Japanese characters (NEVER < 950 chars! Within {u_min}-{u_max} chars / 180-300s). Beat 1 (B1_hook) MUST have 3 short lines totaling <= 115 chars (~15-19s) citing ONLY verified_primary/corroborated_secondary claim_ids.\n"
                        "3. Distinguish judgment (判決によれば) vs indictment (起訴状によれば) vs complaint (訴状によれば) vs named institution report (日銀公表/報告書によれば) vs unverified press reports (未確認の報道によれば).\n"
                        "4. Do NOT mix unverified_secondary and verified_primary claims on the same line unless explicitly qualified.\n\n"
                    )
                elif market == "VN":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR VIETNAMESE (VN) MARKET:\n"
                        "1. Write 100% natural, authoritative Vietnamese narration with full Vietnamese diacritics. No English/CJK prose.\n"
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} Vietnamese words across 19-24 lines). Beat 1 (B1_hook) MUST have 3 concise lines totaling <= 75 words (<= 21s) citing ONLY verified_primary or corroborated_secondary claim_ids.\n"
                        "3. Distinguish judgment (Theo phán quyết của tòa án) vs indictment (Theo cáo trạng) vs complaint (Theo đơn kiện) vs unverified press reports (Theo thông tin bước đầu chưa kiểm chứng).\n\n"
                    )
                else:
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR ENGLISH (EN) MARKET:\n"
                        f"1. STRICT LENGTH & PACING: Write 100% crisp investigative English narration strictly totaling {u_min}-{u_max} words across 20-26 lines (180-300s). Beat 1 (B1_hook) MUST be 3 tight, punchy lines totaling <= 44 words (<= 22s).\n"
                        "2. Distinguish court_judgment vs indictment vs criminal_complaint vs settled without admitting wrongdoing vs unverified preliminary reports. Attribute DOJ/regulatory allegations directly to the agency/court, NOT to 'press reports'.\n"
                        "3. Beat 1 MUST anchor in verified_primary or corroborated_secondary claim_ids ONLY.\n\n"
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

                            # Never taint a Beat 1 line that already cites verified_primary/corroborated_secondary
                            # with an extra unverified_secondary cid unless all claims on the line are unverified.
                            if "B1" in b_id and len(c_ids) > 1:
                                _ver_cids = [
                                    cid for cid in c_ids
                                    if (
                                        (evidence_map[cid].get("verification_status") if isinstance(evidence_map[cid], dict) else getattr(evidence_map[cid], "verification_status", ""))
                                        in ("verified_primary", "corroborated_secondary")
                                    )
                                ]
                                if _ver_cids:
                                    c_ids = _ver_cids

                            text = ln.get("text", "")
                            if (market or "EN").upper() in ("KR", "KO"):
                                text = _normalize_spoken_korean_numbers(text)

                            from app.services.story_provenance_engine import (
                                expected_qualifier_bucket as _exp_bucket,
                            )
                            from app.services.story_provenance_engine import (
                                line_matches_expected_qualifier as _pre_match_qual,
                            )

                            c_objs = [evidence_map[cid] for cid in c_ids if cid in evidence_map]
                            if len(c_objs) > 1:
                                _bucket_priority = {
                                    "unverified": 0,
                                    "indictment": 1,
                                    "criminal_complaint": 2,
                                    "press_charge": 3,
                                    "alleged_regulator": 4,
                                    "alleged": 5,
                                    "proposed": 6,
                                    "final_judgment": 7,
                                    "settled": 8,
                                    "fact": 9,
                                }
                                c_objs.sort(key=lambda co: _bucket_priority.get(
                                    _exp_bucket(
                                        legal_status=str(co.get("legal_status", "alleged") if isinstance(co, dict) else getattr(co, "legal_status", "alleged")),
                                        source_type=str(co.get("source_type", "press") if isinstance(co, dict) else getattr(co, "source_type", "press")),
                                        doc_type=str(co.get("doc_type", "unknown") if isinstance(co, dict) else getattr(co, "doc_type", "unknown")),
                                        speaker=(co.get("speaker", None) if isinstance(co, dict) else getattr(co, "speaker", None)),
                                        procedural_status=str(co.get("procedural_status", "unknown") if isinstance(co, dict) else getattr(co, "procedural_status", "unknown")),
                                        verification_status=str(co.get("verification_status", "corroborated_secondary") if isinstance(co, dict) else getattr(co, "verification_status", "corroborated_secondary")),
                                    ),
                                    9,
                                ))
                            applied_prefix_bucket = False
                            c_objs_dicts = [
                                (co.model_dump() if hasattr(co, "model_dump") else dict(co))
                                for co in c_objs
                            ]
                            for c_dict_q in c_objs_dicts:
                                ok_already, _ = _pre_match_qual(text, c_dict_q, market=market, peer_claims=c_objs_dicts)
                                if ok_already:
                                    continue
                                bkt = _exp_bucket(
                                    legal_status=str(c_dict_q.get("legal_status", "alleged")),
                                    source_type=str(c_dict_q.get("source_type", "press")),
                                    doc_type=str(c_dict_q.get("doc_type", "unknown")),
                                    speaker=c_dict_q.get("speaker"),
                                    procedural_status=str(c_dict_q.get("procedural_status", "unknown")),
                                    verification_status=str(c_dict_q.get("verification_status", "corroborated_secondary")),
                                )
                                if bkt == "fact" or (bkt != "settled" and applied_prefix_bucket):
                                    continue
                                text = _apply_legal_qualifier(
                                    text=text,
                                    legal_status=str(c_dict_q.get("legal_status", "alleged")),
                                    market=market,
                                    source_type=str(c_dict_q.get("source_type", "press")),
                                    doc_type=str(c_dict_q.get("doc_type", "unknown")),
                                    speaker=c_dict_q.get("speaker"),
                                    procedural_status=str(c_dict_q.get("procedural_status", "unknown")),
                                    verification_status=str(c_dict_q.get("verification_status", "corroborated_secondary")),
                                    slot_idx=l_idx,
                                )
                                if bkt != "settled":
                                    applied_prefix_bucket = True

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
                            line_peer_dicts = [
                                (evidence_map[c].model_dump() if hasattr(evidence_map[c], "model_dump") else dict(evidence_map[c]))
                                for c in (ln.claim_ids or [])
                                if c in evidence_map
                            ]
                            for cid in (ln.claim_ids or []):
                                c_obj = evidence_map.get(cid)
                                if c_obj is not None:
                                    c_dict = c_obj.model_dump() if hasattr(c_obj, "model_dump") else dict(c_obj)
                                    ok_q, q_msg = _match_qual(ln.text, c_dict, market=market, peer_claims=line_peer_dicts)
                                    if not ok_q:
                                        qual_issues.append(f"{ln.line_id}:{cid}:{q_msg}")
                    b1_dur_ok = b1_dur <= 24.5
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
                        if cand_timing["spoken_units"] < u_min:
                            shortfall = u_min - int(cand_timing["spoken_units"])
                            mid_target = int((u_min + u_max) // 2)
                            repair_notes.append(
                                f"TOO SHORT by {shortfall} {cand_timing['unit_type']}: current is ONLY {cand_timing['spoken_units']} "
                                f"({cand_dur:.1f}s), MUST reach {u_min}-{u_max} {cand_timing['unit_type']} (target ~{mid_target}) and {d_min:.0f}-{d_max:.0f}s. "
                                f"ADD 4-6 new substantive lines across B2_setup, B3_scheme, and B4_crack detailing the evidence ledger claims cleanly (do NOT lengthen B1_hook)."
                            )
                        elif cand_timing["spoken_units"] > u_max:
                            excess = int(cand_timing["spoken_units"]) - u_max
                            repair_notes.append(
                                f"TOO LONG by {excess} {cand_timing['unit_type']}: trim redundant wording across B2-B5 to strictly {u_min}-{u_max} {cand_timing['unit_type']} ({d_min:.0f}-{d_max:.0f}s)."
                            )
                        else:
                            repair_notes.append(
                                f"Duration {cand_dur:.1f}s ({cand_timing['spoken_units']} {cand_timing['unit_type']}) is OUT OF BOUNDS: "
                                f"MUST be strictly {d_min:.0f}-{d_max:.0f}s AND {u_min}-{u_max} {cand_timing['unit_type']}."
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
                        max_tokens=4500,
                        temperature=0.35 if not units_ok else 0.2,
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
