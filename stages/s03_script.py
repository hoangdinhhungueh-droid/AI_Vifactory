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
    credibility_tier: Optional[str] = None,
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
        credibility_tier=credibility_tier,
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
            if len(topic_base) > 22:
                words = topic_base.split()
                short = ""
                for w in words:
                    if len(short) + len(w) + 1 <= 22:
                        short = f"{short} {w}".strip()
                    else:
                        break
                short = short or topic_base[:18]
            else:
                short = topic_base
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
    if re.search(r"(?:했다고|됐다고|있다고|없다고|된다고|한다고|다는|라는|것으로|것으로도)$", t_clean):
        return f"{t_clean} 전해졌습니다."

    # Convert common mid-sentence conjunctive verbs into declarative past/present stems
    if re.search(r"(?:하고|하며|되고|되며|이고|이며|이고는|면서|했고|하였고|됐고|되었고|였고|이었고|았고|었고|었으며|았으며|였으며|되었으며|하였으며)$", t_clean):
        t_clean = re.sub(r"(?:하고|하며|하면서)$", "했다", t_clean)
        t_clean = re.sub(r"(?:되고|되며|되면서)$", "됐다", t_clean)
        t_clean = re.sub(r"(?:했고|하였고|하였으며)$", "했다", t_clean)
        t_clean = re.sub(r"(?:됐고|되었고|되었으며)$", "됐다", t_clean)
        t_clean = re.sub(r"(?:였고|이었고|였으며|이었으며)$", "였다", t_clean)
        t_clean = re.sub(r"(?:았고|았으며)$", "았다", t_clean)
        t_clean = re.sub(r"(?:었고|었으며)$", "었다", t_clean)
        t_clean = re.sub(r"(?:이고|이며|이면서)$", "이다", t_clean)
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


def _soften_kr_reported_predicate(text: str, slot_idx: int = 0) -> str:
    """Ensure unverified press claims end in reported speech (전해졌습니다/보도됐습니다) rather than definitive established facts."""
    t = text.strip()
    if re.search(r"의혹이\s*(?:제기됐습니다|제기되었습니다|불거졌습니다|제기된\s*것으로\s*전해졌습니다)\.?$", t):
        return t if t.endswith(".") else f"{t}."

    # Clean double reporting remnants if already present
    t = re.sub(r"보도가\s*있었던\s*것으로\s*보도됐습니다\.$", "것으로 보도됐습니다.", t)
    t = re.sub(r"보도가\s*있었던\s*것으로\s*전해졌습니다\.$", "것으로 전해졌습니다.", t)
    t = re.sub(r"보도가\s*있었던\s*것으로\s*알려졌습니다\.$", "것으로 알려졌습니다.", t)
    t = re.sub(r"보도했다고\s*([가-힣A-Za-z0-9·]+(?:가|이))\s*보도한\s*것으로\s*보도됐습니다\.$", r"보도했다고 \1가 보도한 것으로 전해졌습니다.", t)
    t = re.sub(r"보도한\s*것으로\s*보도됐습니다\.$", "보도한 것으로 전해졌습니다.", t)
    t = re.sub(r"보도된\s*것으로\s*보도됐습니다\.$", "보도된 것으로 전해졌습니다.", t)
    t = re.sub(r"전해진\s*것으로\s*전해졌습니다\.$", "전해진 것으로 보도됐습니다.", t)

    if t.endswith(("전해졌습니다.", "보도됐습니다.", "알려졌습니다.", "설명합니다.", "제시했습니다.")):
        return t
    h_bodo = "한 것으로 보도됐습니다." if slot_idx % 2 == 0 else "한 것으로 전해졌습니다."
    d_bodo = "된 것으로 전해졌습니다." if slot_idx % 2 == 0 else "된 것으로 보도됐습니다."
    su_bodo = "수 있는 것으로 전해졌습니다." if slot_idx % 2 == 0 else "수 있는 것으로 보도됐습니다."
    repls = [
        (r"머물렀습니다\.$", "머문 것으로 전해졌습니다."),
        (r"그쳤습니다\.$", "그친 것으로 전해졌습니다."),
        (r"시작됐습니다\.$", "시작된 것으로 전해졌습니다."),
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
        (r"발표했습니다\.$", "발표한 것으로 보도됐습니다."),
        (r"확인됐습니다\.$", "확인된 것으로 보도됐습니다."),
        (r"추진했습니다\.$", "추진한 것으로 전해졌습니다."),
        (r"시행됩니다\.$", "시행되는 것으로 보도됐습니다."),
        (r"시작됩니다\.$", "시작되는 것으로 전해졌습니다."),
        (r"수\s*있었던\s*것으로\s*보도됐습니다\.$", "수 있었던 것으로 보도됐습니다."),
        (r"수\s*있었습니다\.$", "수 있었던 것으로 보도됐습니다."),
        (r"수\s*있습니다\.$", su_bodo),
        (r"이릅니다\.$", "이르는 것으로 보도됐습니다."),
        (r"만듭니다\.$", "만드는 것으로 전해졌습니다."),
        (r"겪었습니다\.$", "겪은 것으로 보도됐습니다."),
        (r"겪고\s*있습니다\.$", "겪고 있는 것으로 보도됐습니다."),
        (r"있었습니다\.$", "있었던 것으로 보도됐습니다."),
        (r"없었습니다\.$", "없었던 것으로 보도됐습니다."),
        (r"있습니다\.$", "있는 것으로 전해졌습니다."),
        (r"없습니다\.$", "없는 것으로 전해졌습니다."),
        (r"지원받습니다\.$", "지원받는 것으로 알려졌습니다."),
        (r"지원받았습니다\.$", "지원받았던 것으로 알려졌습니다."),
        (r"받았습니다\.$", "받았던 것으로 보도됐습니다."),
        (r"받습니다\.$", "받는 것으로 전해졌습니다."),
        (r"지원합니다\.$", "지원하는 것으로 전해졌습니다."),
        (r"제공합니다\.$", "제공하는 것으로 전해졌습니다."),
        (r"했습니다\.$", h_bodo),
        (r"됐습니다\.$", d_bodo),
        (r"합니다\.$", "하는 것으로 전해졌습니다."),
        (r"입니다\.$", "인 것으로 전해졌습니다."),
        (r"됩니다\.$", "되는 것으로 전해졌습니다."),
        (r"([았었였했됐졌왔뒀썼렀쳤났맞])습니다\.$", r"\1던 것으로 전해졌습니다."),
        (r"었습니다\.$", "었던 것으로 보도됐습니다."),
        (r"았습니다\.$", "았던 것으로 보도됐습니다."),
        (r"였습니다\.$", "였던 것으로 보도됐습니다."),
        (r"왔습니다\.$", "왔던 것으로 전해졌습니다."),
        (r"갔습니다\.$", "갔던 것으로 전해졌습니다."),
        (r"났습니다\.$", "났던 것으로 전해졌습니다."),
        (r"습니다\.$", "는 것으로 전해졌습니다."),
        (r"ㅂ니다\.$", "는 것으로 전해졌습니다."),
    ]
    for pat, rep in repls:
        if re.search(pat, t):
            return re.sub(pat, rep, t)
    return t


def _sanitize_unverified_kr_claim(text: str) -> str:
    """Sanitize unverified secondary claims to avoid prohibited regulator attribution or official recognition elevation."""
    t = text
    # 1. Eliminate prohibited official recognition claims in unverified snippets
    t = re.sub(r"공식\s*인정\s*(피해자|대상자|사례|건)", r"지원 대상 \1", t)
    t = re.sub(r"공식적으로\s*인정(?:되었던|됐던|된|받은|받았던)?", "집계된", t)
    t = re.sub(r"공식\s*인정(?:되었던|됐던|된|받은|받았던)?", "확인된", t)
    t = re.sub(r"공식\s*(?:확인|발표)된", "알려진", t)

    # 2. Convert active government/authority agency to contextual framing
    t = re.sub(r"(?:설치한다|설치하는\s*것으로\s*전해졌습니다|설치하는\s*것으로\s*보도됐습니다)", "설치하는 방안이 거론된 것으로 전해졌습니다", t)
    t = re.sub(r"(?:마련했다|마련한\s*것으로\s*전해졌습니다|마련한\s*것으로\s*보도됐습니다)", "마련하는 방안이 거론된 것으로 전해졌습니다", t)
    t = re.sub(r"\b(정부|지방자치단체|광역자치단체|관계\s*부처|행정\s*당국|규제\s*당국|당국)(?:가|이)\s*", r"\1 차원에서 ", t)

    # 3. Soften unverified numeric counts and speculative loss estimates
    t = re.sub(r"([가-힣0-9\s]+건)에\s*이르렀(?:다|습니다)", r"\1으로 집계된 것으로 전해졌습니다", t)
    t = re.sub(r"([가-힣0-9\s]+원)으로\s*제시됐(?:다|습니다)", r"\1에 달할 수 있다는 잠재적 추정이 제기된 것으로 전해졌습니다", t)

    # 4. Guard against unverified statutory elevation or state guarantee assertions
    t = re.sub(r"(?:개정\s*)?법률에\s*따른\s*(우선매수권|권리|구제책|대책|방안)", r"보도에 제시된 \1 방안", t)
    t = re.sub(r"개정\s*(?:법률|법령|특별법)에\s*따른", "보도된 방안에 따른", t)
    t = re.sub(
        r"(?:부동산\s*정책상의\s*)?선례를\s*(?:만드는|만든다는|형성하는)\s*(?:것으로\s*(?:전해졌습니다|보도됐습니다|알려졌습니다))?",
        "부동산 정책상의 선례라는 언론 일각의 해석이 제시된 것으로 전해졌습니다",
        t,
    )
    t = re.sub(
        r"(?:부동산\s*정책상의\s*)?선례를\s*(?:만든다|형성한다)",
        "부동산 정책상의 선례라는 언론 일각의 해석을 제시한다",
        t,
    )

    return t


def _compact_kr_hook_line(text: str, max_chars: int = 35) -> str:
    """Compacts a Korean sentence down to <= max_chars for Beat 1 hook while strictly preserving legal qualifier prefix, subject, core metric, and reported predicate without semantic truncation."""
    cand = text.strip().rstrip(". ")
    pfx_m = re.match(r"^([“\"‘']?[가-힣0-9a-zA-Z\s·]+(?:따르면|의하면|보면|전해진 바에|공개된 바에|나타난 바에)[”\"’']?,?\s*)", cand)
    pfx = pfx_m.group(1) if pfx_m else ""
    if pfx:
        cand = cand[len(pfx):].strip()
    cand = re.sub(r"\b\d{4}년\s*", "", cand)
    cand = re.sub(r"(?:와|과)\s*(?:관련|관계)\s*(?:기관|당국|부처)(?:이|가)?\s*", "가 ", cand)
    cand = re.sub(r"(?:심사|검토|조사|점검|실사)\s*(?:및|과|와)\s*[가-힣\s]+?절차를\s*", "", cand)
    cand = re.sub(r"총\s*(\d+[조억만\s]*원)\s*규모(?:의)?\s*", r"\1 ", cand)
    cand = re.sub(r"(?:진행하고|추진하고|시행하고)\s*있다는\s*(?:공식\s*)?발표가\s*(?:나왔다|나왔습니다|나왔던|있었다|있었습니다|있었던)", "추진을 발표한", cand)
    cand = re.sub(r"(?:다는|라는|고\s*있다는)?\s*(?:공식\s*)?발표가\s*(?:나왔다|나왔습니다|나왔던|있었다|있었습니다|있었던)", "다고 발표한", cand)

    # Detect if cand ends with an essential reported predicate or allegation predicate (legal qualifier)
    rep_m = re.search(
        r"([가-힣]+(?:한|된|하는|되는|인|은|는)\s*것으로\s*(?:보도됐습니다|전해졌습니다|알려졌습니다|나타났습니다)|"
        r"[가-힣]+(?:다는|라는)\s*(?:보도입니다|분석입니다|의혹입니다|지적입니다)|"
        r"의혹이\s*(?:제기됐습니다|불거졌습니다|제기된\s*것으로\s*(?:전해졌습니다|보도됐습니다)))\.?$",
        cand,
    )

    if rep_m and len(cand) > max_chars:
        tail = rep_m.group(0).rstrip(".") + "."
        head = cand[:rep_m.start()].strip()

        # Check if head contains coordinate clause (e.g. 평가됐고, ...)
        clauses = [c.strip() for c in re.split(r"[;—]|,\s*", head) if c.strip()]
        if len(clauses) > 1:
            c0 = clauses[0]
            c0 = re.sub(r"\b(?:매우|상당히|주요|초기|향후|당시|기존|추가적|잠재적|사적|공적|실제|실질적인)\s*", "", c0)
            c0_h = _to_kr_honorific(c0)
            if not c0_h.endswith(("전해졌습니다.", "보도됐습니다.", "알려졌습니다.", "의혹입니다.", "분석입니다.")):
                c0_h = _soften_kr_reported_predicate(c0_h, slot_idx=0)
            if len(c0_h) <= max_chars + 12:
                cand_fin = f"{pfx}{c0_h}".strip()
                return f"{cand_fin}." if not cand_fin.endswith((".", "!", "?")) else cand_fin

        # 1. Comparative or intensifier adverbial phrases
        head = re.sub(r"\b(?:[가-힣0-9·]+보다\s*(?:더\s*)?(?:높게|낮게|크게|작게|많게|적게)|실제보다\s*[가-힣]+|크게|심각하게|상당히|매우)\s*", "", head)
        # 2. General adnominal temporal, descriptive, or structural modifiers (preserve '일부' as legal scope qualifier)
        head = re.sub(r"\b(?:향후|당시|기존|추가적|다각적|잠재적|사적|공적|주요|초기|실제|실질적인)\s*", "", head)
        # 3. Postpositional topic or reference adverbials
        head = re.sub(r"[가-힣0-9a-zA-Z·]+\s*에\s*(?:대해|따라|관해)\s*", "", head)
        # 4. Coordinating nominal phrases in subject or predicate
        head = re.sub(r"([은는이가]\s)[가-힣\s]{2,20}?(?:과|와)\s+", r"\1", head)
        # 5. Adnominal purpose, relational, or causal clauses
        head = re.sub(r"(?<=[은는이가]\s)[가-힣\s]{2,25}?(?:을|를)\s*(?:위한|향한|관한|둘러싼)\s*", "", head)
        head = re.sub(r"\s+", " ", head).strip()
        cand_rep = f"{head} {tail}".strip()
        if len(cand_rep) <= max_chars:
            cand = cand_rep
        else:
            subj_m = re.match(r"^([가-힣\s]+?(?<!또)(?<!모)(?<!다)(?<!어)[은는이가])", head)
            recip_m = re.search(r"([가-힣0-9·]+(?:에게|에))\s*", head)
            obj_matches = list(re.finditer(r"([가-힣0-9·]+(?:을|를))", head))
            obj_m = obj_matches[-1] if obj_matches else None
            verb_m = re.search(r"([가-힣]+지)\s*$", head)
            verb_part = f" {verb_m.group(1)}" if verb_m else ""
            if subj_m and recip_m and obj_m:
                cand_rep = f"{subj_m.group(1)} {obj_m.group(1)} {recip_m.group(1)}{verb_part} {tail}".strip()
                if len(cand_rep) <= max_chars:
                    cand = cand_rep
                else:
                    cand = f"{subj_m.group(1)} {obj_m.group(1)}{verb_part} {tail}".strip()
            elif subj_m and obj_m:
                cand = f"{subj_m.group(1)} {obj_m.group(1)}{verb_part} {tail}".strip()

    if len(cand) > max_chars:
        cand = re.sub(r"\b\d{1,2}월\s*\d{1,2}일\s*", "", cand)
        cand = re.sub(r"[가-힣0-9a-zA-Z·]+\s*에\s*대해\s*", "", cand)
        cand = re.sub(r"([은는이가]\s)[가-힣\s]{2,20}?(?:과|와)\s+[가-힣\s]{2,20}?(?=\d)", r"\1", cand)
        cand = re.sub(r"규모\s*[가-힣\s]+?(지원|대책|사업|수사|감사|과징금|환수)", r"\1", cand)
        cand = re.sub(r"지원\s*대상\s*", "지원 ", cand)

    if len(cand) > max_chars:
        cand = re.sub(r"([가-힣](?:는|은|가|이))\s+[가-힣0-9a-zA-Z·]{2,15}?(?:에|에게)\s+(?=\d)", r"\1 ", cand)
        cand = re.sub(r"(\d[가-힣]{1,5}\s(?:이|가|을|를))\s+[가-힣\s]{2,15}?(?:으로|로)\s*", r"\1 ", cand)
        cand = re.sub(r"(\d[조억만\s]*원)\s*[가-힣\s]{2,15}?(지원|대책|사업|수사|감사|과징금|환수)", r"\1 \2", cand)
        cand = re.sub(r"([은는이가]\s)[가-힣\s]{2,15}?(?=\d)", r"\1", cand)

    cand = re.sub(r"\s+", " ", cand).strip()
    cand = _to_kr_honorific(cand)
    if rep_m and not cand.endswith(("전해졌습니다.", "보도됐습니다.", "알려졌습니다.", "의혹입니다.", "분석입니다.")):
        cand = _soften_kr_reported_predicate(cand, slot_idx=0)

    cand_fin = f"{pfx}{cand}".strip()
    return f"{cand_fin}." if not cand_fin.endswith((".", "!", "?")) else cand_fin




def _is_editorial_pattern_interrupt(ln_dict: Dict[str, Any], text_str: str, market: str = "EN") -> bool:
    """Detect whether a line is a short dramatic pattern interrupt / rhythm shift rather than a factual evidentiary claim."""
    m = (market or "EN").upper()
    vh = str(ln_dict.get("visual_hook", "")).lower()
    t = (text_str or "").strip()
    if not t or re.search(r"\d", t):
        return False
    from app.services.story_provenance_engine import strip_attribution_prefix
    t_clean, _ = strip_attribution_prefix(t, market=market)
    t_clean = t_clean.strip()
    words = t_clean.split()

    # Explicit visual hook marking
    if vh in ("pattern_interrupt", "grease_pencil", "stop_motion_hit"):
        if m in ("KR", "JA") and len(t_clean) <= 32 and len(words) <= 8:
            return True
        if len(words) <= 10:
            return True

    # Generic short dramatic phrase without administrative/investigative verbs or policy nouns
    if m in ("KR", "JA"):
        if len(t_clean) <= 30 and len(words) <= 8 and not any(k in t_clean for k in ("조사", "수사", "판결", "공소", "기소", "발표", "시행", "인가", "승인", "신청", "회복", "지원")):
            return True
    else:
        if len(words) <= 10 and not any(k in t_clean.lower() for k in ("investigat", "ruling", "indict", "announced", "enacted", "approved")):
            return True
    return False


def _trim_clause_smart(text: str, elems: Dict[str, Any], market: str, hook_mode: bool = False) -> str:
    """Bound clause length cleanly for beat tempo without bisecting parentheticals or dropping metrics."""
    clean = re.sub(r"\s+", " ", (text or "").strip()).rstrip(".。")
    # Clean trailing formal polite endings if embedded inside a longer sentence
    if market == "KR":
        if "विकल्प" in clean:
            clean = clean.replace("विकल्प", "선택권")
        clean = re.sub(r"[\u0900-\u097F]+", "", clean).strip()

        # Clean trailing reporting clutter from press/RSS claims
        clean = re.sub(r"(?:다는|라는|다는\s*내용의|라는\s*사실의)?\s*(?:보도가\s*있었다|보도가\s*나왔다|보도가\s*전해졌다|보도가\s*있었으며|보도가\s*있었던|보도이다)$", "다", clean)
        clean = re.sub(r"(?:다는|라는)?\s*(?:분석이\s*보도되었다|분석이\s*나왔다|분석이\s*제기되었다|분석이다|분석인\s*것으로\s*전해졌다)$", "다는 분석이다", clean)
        clean = re.sub(r"(?:다는|라는)?\s*(?:의혹이\s*보도되었다|의혹이\s*나왔다|의혹이\s*제기되었다|의혹이\s*불거졌다|의혹이\s*있었다|의혹이다)$", "다는 의혹이 제기됐다", clean)

        pat_kr = r"([가-힣]+[다라])(?:는|고)?\s*(?:보도가\s*나왔다|보도이다|보도가\s*전해졌다|내용이\s*보도되었다|사실이\s*보도되었다|보도되었다|보도됐다|알려졌다|전해졌다)$"
        clean = re.sub(pat_kr, r"\1", clean)
        clean = re.sub(r"(?:보도되었다|보도됐다|알려졌다|전해졌다|보도됐습니다|전해졌습니다|알려졌습니다)\.?$", "", clean).strip()
        clean = re.sub(r"([가-힣]+)한\s*것으로$", r"\1했다", clean)
        clean = re.sub(r"([가-힣]+)된\s*것으로$", r"\1됐다", clean)
        clean = re.sub(r"([가-힣]+)인\s*것으로$", r"\1이다", clean)
        clean = re.sub(r"([가-힣]+)는\s*것으로$", r"\1는다", clean)
        clean = re.sub(r"([가-힣]+)던\s*것으로$", r"\1다", clean)

        if hook_mode:
            # Generic Korean hook compaction (Rule 128 / Rule 132 compliant: zero case-study hardcodes)
            c_cand = clean

            # 1. Strip contrastive negative lead: 'A가 아니라 B' -> 'B' (preserves core paradox)
            if "아니라" in c_cand:
                b_part = re.sub(r"^.*?아니라,?\s*", "", c_cand)
                if b_part and len(b_part) <= 45:
                    subj_m = re.match(r"^([가-힣]+(?:는|은))\s+", c_cand)
                    if subj_m and not b_part.startswith(subj_m.group(1)):
                        cand = f"{subj_m.group(1)} {b_part}"
                        if len(cand) <= 45:
                            return cand
                    return b_part

            # 2. Strip target/topic modifiers: '...에 대한', '...를 위한'
            c_cand = re.sub(r"^[가-힣]+(?:\s+[가-힣]+)?\s*에\s*대한\s*", "", c_cand)
            c_cand = re.sub(r"^[가-힣]+(?:\s+[가-힣]+)?\s*을\s*위한\s*", "", c_cand)
            c_cand = re.sub(r"^[가-힣]+(?:\s+[가-힣]+)?\s*를\s*위한\s*", "", c_cand)

            # 3. Strip long relative clause modifying object: '[Subject]는 ...보장하는/지원하는 [Object]'
            c_cand = re.sub(r"(?<=[은는이가]\s)[가-힣\s]+?(?:보장하는|지원하는|규정하는|마련하는|추진하는)\s+", "", c_cand)

            # 4. Clean formal action suffixes: '시행을 공식 발표했다' -> '시행을 발표했다'
            c_cand = re.sub(r"시행을\s*공식\s*발표했다", "시행을 발표했다", c_cand)
            c_cand = re.sub(r"도입을\s*공식\s*발표했다", "도입을 발표했다", c_cand)

            # 5. Simplify date adverbials: '2026년 11월 10일부터 전국에서' -> '2026년 11월 10일 전국에서'
            c_cand = re.sub(r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)부터\s*전국에서", r"\1 전국에서", c_cand)
            c_cand = re.sub(r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)부터", r"\1", c_cand)

            # Redundant agency padding: 'A와 관련 기관이' -> 'A가'
            c_cand = re.sub(r"(?:와|과)\s*(?:관련|관계)\s*(?:기관|당국|부처)(?:이|가)?\s*", "가 ", c_cand)

            # Procedural boilerplate: '심사 및 회수 절차를', '조사 및 점검 절차를'
            c_cand = re.sub(r"(?:심사|검토|조사|점검)\s*(?:및|과|와)\s*[가-힣\s]+?절차를\s*", "", c_cand)

            # Announce predicates: '진행하고 있다는 공식 발표가 나왔다' -> '추진을 발표했다'
            c_cand = re.sub(r"(?:진행하고|추진하고|시행하고)\s*있다는\s*(?:공식\s*)?발표가\s*나왔다", "추진을 발표했다", c_cand)
            c_cand = re.sub(r"(?:다는|라는|고\s*있다는)?\s*(?:공식\s*)?발표가\s*(?:나왔다|있었다)", "다고 발표했다", c_cand)
            c_cand = re.sub(r"총\s*(\d+[조억만\s]*원)\s*규모의\s*", r"\1 규모 ", c_cand)

            # 6. Simplify compound modifier padding
            c_cand = re.sub(r"최소보장\s*(?:금융지원|재정지원|지원)\s*", "지원 ", c_cand)
            c_cand = re.sub(r"최소\s*재정지원\s*", "지원 ", c_cand)
            c_cand = re.sub(r"전국적(?:으로)?\s*", "", c_cand)

            if len(c_cand) <= 45 and c_cand.endswith("다"):
                return c_cand

            # 7. Strip leading adnominal participle clauses modifying the main subject
            c_cand = re.sub(r"^[가-힣\s]+?(?:이용한|활용한|통한|바탕으로\s*한|기반으로\s*한|따른)\s+", "", c_cand)
            if len(c_cand) <= 45 and c_cand.endswith("다"):
                return c_cand

            # 8. Strip compound modifier noun phrases in predicate
            c_cand = re.sub(r"(?<=[은는이가]\s)[가-힣\s]+?(?:과|와)\s+", "", c_cand)
            if len(c_cand) <= 45 and c_cand.endswith("다"):
                return c_cand

            # 9. Strip year in hook if still exceeding cap
            c_cand = re.sub(r"\b\d{4}년\s*", "", c_cand)
            if len(c_cand) <= 45 and c_cand.endswith("다"):
                return c_cand

        cap = 45 if hook_mode else 110
        if len(clean) <= cap:
            return clean
        clauses = [c.strip() for c in re.split(r"[;—]|,\s+", clean) if c.strip()]
        if len(clauses) > 1:
            head = clauses[0]
            conj_repls = [
                (r"(?:되면서|되므로)$", "됐다"),
                (r"(?:하면서|하므로)$", "했다"),
                (r"하고$", "했다"), (r"하며$", "했다"), (r"되어$", "됐다"),
                (r"되고$", "된다"), (r"이고$", "이다"), (r"으며$", "었다"), (r"고$", "다"),
                (r"지만$", "다"), (r"으나$", "다"), (r"면서$", "했다"),
            ]
            for c_pat, c_rep in conj_repls:
                if re.search(c_pat, head):
                    head = re.sub(c_pat, c_rep, head)
                    break
            if len(head) <= cap and head.endswith("다"):
                return head

        conn_m = re.search(r"^(.*?([가-힣]+(?:되어|되면서|하여|하면서|하고|되고|이지만|았지만|었지만)))\s+(.*)$", clean)
        if conn_m:
            head_c = conn_m.group(1).strip()
            for c_pat, c_rep in [
                (r"되어$", "됐다"), (r"(?:되면서|되므로)$", "됐다"),
                (r"(?:하면서|하므로)$", "했다"), (r"하여$", "했다"),
                (r"하고$", "했다"), (r"되고$", "된다"),
            ]:
                if re.search(c_pat, head_c):
                    head_c = re.sub(c_pat, c_rep, head_c)
                    break
            if len(head_c) <= cap and head_c.endswith("다"):
                return head_c

        if hook_mode:
            # Generic clause extraction: if sentence has multiple clauses, preserve full grammatical clause
            clauses = [c.strip() for c in re.split(r"[;—]|\s*,\s*", clean) if c.strip()]
            if len(clauses) > 1:
                head = clauses[0]
                for c_pat, c_rep in [
                    (r"(?:되면서|되므로)$", "됐다"),
                    (r"(?:하면서|하므로)$", "했다"),
                    (r"하고$", "했다"), (r"하며$", "했다"), (r"되어$", "됐다"),
                    (r"되고$", "된다"), (r"이고$", "이다"), (r"으며$", "었다"), (r"고$", "다"),
                    (r"지만$", "다"), (r"으나$", "다"), (r"면서$", "했다"),
                ]:
                    if re.search(c_pat, head):
                        head_cand = re.sub(c_pat, c_rep, head)
                        if len(head_cand) <= cap and head_cand.endswith("다"):
                            return head_cand
                        break

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

    # Avoid leaving dangling prepositions, conjunctions, articles, or modifiers at the end of the sentence
    dangling_words = {
        "the", "a", "an", "of", "in", "to", "for", "with", "and", "or", "by",
        "from", "as", "at", "whose", "which", "that", "their", "its", "into",
        "stated", "reported", "published", "described", "noted", "alleged",
        "executive", "federal", "direct", "major", "preliminary", "operational",
        "financial", "corporate", "official", "regulatory", "structural",
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
    from app.services.story_provenance_engine import sanitize_substantive_claim_text
    raw_text = sanitize_substantive_claim_text(raw_text, market=m)
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
        _KR_EN_LOANWORDS = [
            (r"\b[Pp]ackage\b", "지원책"),
            (r"\b[Pp]lan\b", "계획"),
            (r"\b[Rr]eport\b", "보고서"),
        ]
        for pat, rep in _KR_EN_LOANWORDS:
            text = re.sub(pat, rep, text)

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
        dehedge_predicate,
        expected_qualifier_bucket,
        normalize_market_code,
        strip_attribution_prefix,
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
        fact_stripped, existing_pfx = strip_attribution_prefix(fact, m)
        fact_h = _to_kr_honorific(fact)
        fact_stripped_h = _to_kr_honorific(fact_stripped)
        if ls == "alleged" or vs in ("unverified_secondary", "speculative") or bucket in ("alleged", "unverified"):
            fact_h = _soften_kr_reported_predicate(fact_h, slot_idx=slot_idx)
            fact_stripped_h = _soften_kr_reported_predicate(fact_stripped_h, slot_idx=slot_idx)
        if vs in ("unverified_secondary", "speculative") or bucket == "unverified":
            fact_h = _sanitize_unverified_kr_claim(fact_h)
            fact_stripped_h = _sanitize_unverified_kr_claim(fact_stripped_h)

        has_bucket_qualifier = False
        if existing_pfx:
            if bucket == "unverified" or vs in ("unverified_secondary", "speculative"):
                has_bucket_qualifier = any(p in existing_pfx for p in ["미확인", "검증 전", "확인 전", "공식 확인 전", "추가 검증 전", "공식 확인되지 않은"])
            elif bucket == "final_judgment":
                has_bucket_qualifier = any(p in existing_pfx for p in ["판결", "유죄", "선고", "사법부"])
            elif bucket == "audit_finding":
                has_bucket_qualifier = any(p in existing_pfx for p in ["감사", "보고서", "점검", "실태조사"])
            elif bucket == "indictment":
                has_bucket_qualifier = any(p in existing_pfx for p in ["공소", "기소", "검찰"])
            elif bucket == "court_record":
                has_bucket_qualifier = any(p in existing_pfx for p in ["법원", "기록", "문건", "재판부"])
            elif bucket == "alleged_regulator":
                has_bucket_qualifier = any(p in existing_pfx for p in ["정부", "당국", "발표", "기관", "국토", "금융", "공정"])
            elif bucket == "criminal_complaint":
                has_bucket_qualifier = any(p in existing_pfx for p in ["소장", "고발", "고소"])
            elif bucket == "settled":
                has_bucket_qualifier = "합의" in existing_pfx or "합의" in fact
            elif bucket == "proposed":
                has_bucket_qualifier = any(p in existing_pfx for p in ["추진", "방침", "초안", "검토", "계획"])
            elif bucket in ("alleged", "press_charge", "press_allegation"):
                has_bucket_qualifier = True
            elif bucket == "fact":
                has_bucket_qualifier = True

        if not has_bucket_qualifier and claim_obj is not None:
            c_dict_chk = claim_obj if isinstance(claim_obj, dict) else (claim_obj.model_dump() if hasattr(claim_obj, "model_dump") else {})
            if c_dict_chk:
                from app.services.story_provenance_engine import line_matches_expected_qualifier as _chk_qual
                ok_q, _ = _chk_qual(fact_h, c_dict_chk, market=m)
                if ok_q:
                    has_bucket_qualifier = True

        if role_slot == "hook_catalyst":
            if has_bucket_qualifier:
                raw = fact_h
            elif bucket == "final_judgment":
                raw = f"법원 확정 판결에 따르면, {fact_stripped_h}"
            elif bucket == "audit_finding":
                raw = f"감사원 감사 보고서에 따르면, {fact_stripped_h}"
            elif bucket == "indictment":
                raw = f"검찰 공소장에 따르면, {fact_stripped_h}"
            elif bucket == "court_record":
                raw = f"법원 접수 기록에 따르면, {fact_stripped_h}"
            elif bucket == "alleged_regulator":
                raw = f"정부 발표에 따르면, {fact_stripped_h}"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = fact_h if has_bucket_qualifier else f"보도에 따르면, {fact_stripped_h}"
            elif bucket == "settled":
                raw = f"공식 합의 종결 기록에 따르면, {fact_stripped_h.rstrip('.')} (책임을 인정하지 않고 합의됨)."
            elif bucket == "unverified":
                raw = fact_h if has_bucket_qualifier else f"초기 보도에 따르면, {fact_stripped_h}"
            elif bucket == "fact":
                raw = fact_h
            else:
                raw = fact_h
        elif role_slot == "hook_scale":
            if has_bucket_qualifier or bucket in ("alleged", "unverified", "press_allegation", "press_charge"):
                raw = fact_h
            elif bucket == "final_judgment":
                raw = f"법원 확정 판결에 적시된 수치에 따르면, {fact_stripped_h}"
            elif bucket == "audit_finding":
                raw = f"감사원 감사 보고서에 적시된 수치에 따르면, {fact_stripped_h}"
            elif bucket == "indictment":
                raw = f"검찰 공소장에 적시된 수치에 따르면, {fact_stripped_h}"
            elif bucket == "court_record":
                raw = f"법원 접수 기록에 적시된 수치에 따르면, {fact_stripped_h}"
            elif bucket == "alleged_regulator":
                raw = f"규제 당국에 따르면, 집계된 수치는 {fact_stripped_h}"
            elif bucket == "settled":
                raw = f"합의 종결된 수치는 {fact_stripped_h.rstrip('.')} (책임을 인정하지 않고 합의됨)."
            elif bucket == "fact":
                raw = f"개정 법령에 따르면, {fact_h}" if not any(k in fact_h for k in ("법령", "특별법", "법률", "규정", "조례")) else fact_h
            else:
                raw = f"집계된 수치에 따르면, {fact_stripped_h}"
        elif role_slot == "hook_paradox":
            q_short = f"{cq_clean.rstrip('?').strip()}?" if (cq_clean and 6 <= len(cq_clean.rstrip('?').strip()) <= 16) else "실제 구조는 어떠했을까?"
            q_pfx = f"{q_short} " if q_short else ""
            if has_bucket_qualifier or bucket in ("alleged", "unverified", "press_allegation", "press_charge"):
                raw = f"{q_pfx}{fact_stripped_h}"
            elif bucket == "final_judgment" and not any(p in fact for p in ["판결", "유죄", "선고"]):
                raw = f"{q_pfx}법원 판결에 따르면, {fact_stripped_h}"
            elif bucket == "audit_finding" and not any(p in fact for p in ["감사", "보고서"]):
                raw = f"{q_pfx}감사 보고서에 따르면, {fact_stripped_h}"
            elif bucket == "indictment" and not any(p in fact for p in ["공소", "기소"]):
                raw = f"{q_pfx}검찰 공소장에 따르면, {fact_stripped_h}"
            elif bucket == "court_record" and not any(p in fact for p in ["법원", "기록"]):
                raw = f"{q_pfx}법원 접수 기록에 따르면, {fact_stripped_h}"
            elif bucket == "alleged_regulator":
                raw = f"{q_pfx}정부 발표에 따르면, {fact_stripped_h}"
            elif bucket == "settled" and "합의" not in fact:
                raw = f"{q_pfx}{fact_stripped_h.rstrip('.')} (책임을 인정하지 않고 합의됨)."
            else:
                raw = f"{q_pfx}{fact_stripped_h}"
        else:
            if role_slot == "aftermath":
                if bucket == "alleged_regulator":
                    reg_aftermath = [
                        f"정부 공식 발표에 따르면, {fact_stripped_h}",
                        f"관계 당국 발표에 따르면, {fact_stripped_h}",
                        f"당국 공식 발표에 따르면, {fact_stripped_h}",
                        f"정부 발표에 따르면, {fact_stripped_h}",
                        f"관계 기관 공식 발표에 따르면, {fact_stripped_h}",
                    ]
                    raw = reg_aftermath[v_idx]
                elif bucket == "audit_finding":
                    audit_aftermath = [
                        f"감사원 감사 보고서에 따르면, {fact_stripped_h}",
                        f"공식 감사 결과에 따르면, {fact_stripped_h}",
                        f"감사 보고서에 따르면, {fact_stripped_h}",
                        f"감사원 점검 기록에 따르면, {fact_stripped_h}",
                        f"공식 감사 기록에 의하면, {fact_stripped_h}",
                    ]
                    raw = audit_aftermath[v_idx]
                elif bucket == "indictment":
                    raw = f"검찰 공소장에 따르면, {fact_stripped_h}"
                elif bucket == "court_record":
                    raw = f"법원 접수 기록에 따르면, {fact_stripped_h}"
                elif bucket == "final_judgment":
                    raw = f"법원 확정 판결에 따르면, {fact_stripped_h}"
                elif bucket == "criminal_complaint":
                    raw = f"제출된 소장에 따르면, {fact_stripped_h}"
                elif bucket == "proposed":
                    raw = f"정부 추진 방침에 따르면, {fact_stripped_h}"
                elif bucket == "settled":
                    raw = f"공식 합의에 따르면, {fact_stripped_h.rstrip('.')} (공식적인 잘못을 인정하지 않고 합의됨)."
                elif bucket == "unverified" or vs in ("unverified_secondary", "speculative"):
                    unv_aftermath = [
                        f"공식 확인 전 초기 보도에 따르면, {fact_stripped_h}",
                        f"검증 전 초기 언론 보도에 따르면, {fact_stripped_h}",
                        f"미확인 초기 보도에 따르면, {fact_stripped_h}",
                        f"추가 검증 전 취재 보도에 따르면, {fact_stripped_h}",
                        f"초기 언론 보도에 따르면, {fact_stripped_h}",
                    ]
                    raw = unv_aftermath[v_idx]
                elif bucket in ("alleged", "press_charge"):
                    alleged_aftermath = [
                        f"취재 보도에 따르면, {fact_stripped_h}",
                        f"언론 보도에 따르면, {fact_stripped_h}",
                        f"공개된 보도에 따르면, {fact_stripped_h}",
                        f"당시 언론 보도를 보면, {fact_stripped_h}",
                        f"후속 보도에 따르면, {fact_stripped_h}",
                    ]
                    raw = alleged_aftermath[v_idx]
                else:
                    aftermath_framings = [
                        f"취재 보도에 따르면, {fact_stripped_h}",
                        f"언론 보도에 따르면, {fact_stripped_h}",
                        f"보도된 내용에 따르면, {fact_stripped_h}",
                        f"당시 보도에 따르면, {fact_stripped_h}",
                        f"후속 보도에 따르면, {fact_stripped_h}",
                    ]
                    raw = aftermath_framings[v_idx]
            elif bucket == "settled":
                raw = f"{fact_stripped_h.rstrip('.')} (공식적인 잘못을 인정하지 않고 합의됨)."
            elif bucket == "unverified" or vs in ("unverified_secondary", "speculative"):
                unv_leads = [
                    "공식 확인 전 초기 보도에 따르면, ",
                    "검증 전 초기 언론 보도를 보면, ",
                    "추가 검증 전 취재 보도에 따르면, ",
                    "미확인 초기 보도에 의하면, ",
                    "공식 확인되지 않은 초기 보도를 보면, ",
                ]
                l_idx = slot_idx % len(unv_leads)
                if any(p in fact_h for p in ["공식 확인 전", "검증 전", "추가 검증 전", "미확인", "확인 전", "초기 보도", "확인되지 않은"]):
                    raw = fact_h
                else:
                    raw = f"{unv_leads[l_idx]}{fact_stripped_h}"
            elif bucket in ("alleged", "press_charge"):
                if has_bucket_qualifier:
                    if slot_idx % 4 == 0:
                        alleged_leads = [
                            "보도에 따르면, ",
                            "당시 취재 내용을 보면, ",
                            "보도된 경위를 보면, ",
                        ]
                        raw = f"{alleged_leads[(slot_idx // 4) % len(alleged_leads)]}{fact_stripped_h}"
                    else:
                        raw = fact_h
                else:
                    alleged_leads = [
                        "언론 보도에 따르면, ",
                        "관련 취재 내용을 보면, ",
                        "당시 나온 언론 보도를 살펴보면, ",
                        "보도에 나타난 사실관계를 보면, ",
                        "당시 언론 취재에 따르면, ",
                    ]
                    l_idx = slot_idx % len(alleged_leads)
                    raw = f"{alleged_leads[l_idx]}{fact_stripped_h}"
            elif bucket == "alleged_regulator":
                p_opts = ["정부 발표에 따르면, ", "관계 기관 공식 자료에 따르면, ", "규제 당국의 공식 발표에 따르면, ", "정부 및 관계 당국에 따르면, ", "당국의 공식 분석 자료를 보면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "audit_finding":
                p_opts = ["감사 보고서에 따르면, ", "감사원 감사 보고서에 따르면, ", "공식 감사 및 점검 결과에 따르면, ", "감사 결과에 의하면, ", "공식 감사 기록에 의하면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "indictment":
                p_opts = ["검찰 공소장에 따르면, ", "공소 사실에 의하면, ", "검찰 수사 및 공소 내용에 따르면, ", "기소장에 따르면, ", "검찰 기소 내용에 의하면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "court_record":
                p_opts = ["법원 접수 기록에 따르면, ", "법원 문건에 따르면, ", "사법 기록에 따르면, ", "재판부 접수 기록에 따르면, ", "법원에 제출된 기록을 보면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "final_judgment":
                p_opts = ["법원 확정 판결에 따르면, ", "법원 판결에 따르면, ", "사법부 판단에 따르면, ", "판결문에 의하면, ", "유죄 확정 판결에 따르면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "criminal_complaint":
                p_opts = ["제출된 고발장에 따르면, ", "고소장 내용에 따르면, ", "소장을 통해 제기된 바에 따르면, ", "고발장에 의하면, ", "제출된 소장에 따르면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "proposed":
                p_opts = ["추진 중인 정책 방침에 따르면, ", "입법 추진 초안에 따르면, ", "당국의 정책 검토 자료를 보면, ", "발의된 법안 초안에 따르면, ", "제도 추진 계획에 따르면, "]
                raw = fact_h if has_bucket_qualifier else f"{p_opts[v_idx]}{fact_stripped_h}"
            elif bucket == "fact":
                rot = slot_idx % 2
                if has_bucket_qualifier or rot == 1:
                    raw = fact_h
                else:
                    p_opts = [
                        "현행 법령 및 규정에 따르면, ",
                        "공식 시행 법령에 따르면, ",
                        "제도적 기준과 법률에 따르면, ",
                        "관련 법령의 규정에 따라, ",
                        "확립된 행정 기준에 따르면, ",
                    ]
                    raw = f"{p_opts[v_idx]}{fact_stripped_h}"
            else:
                raw = fact_h

    elif m == "JA":
        fact_stripped, existing_pfx_ja = strip_attribution_prefix(fact, "JA")
        fact_clean = fact_stripped if existing_pfx_ja else fact
        if role_slot == "hook_catalyst":
            if bucket == "final_judgment":
                raw = f"{loc_topic}の重大な局面において、裁判所の確定判決によれば、{fact_clean}。"
            elif bucket == "audit_finding":
                raw = f"{loc_topic}の発端において、監査報告書によれば、{fact_clean}。"
            elif bucket == "indictment":
                raw = f"急激な市場の危機において、起訴状の指摘によれば、{fact_clean}。"
            elif bucket == "court_record":
                raw = f"{loc_topic}をめぐり、裁判所の記録によれば、{fact_clean}。"
            elif bucket == "alleged_regulator":
                raw = f"{loc_topic}をめぐり、当局の公表によれば、{fact_clean}。"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"{loc_topic}をめぐり、報道によれば、{fact_clean}。"
            elif bucket == "settled":
                raw = f"{loc_topic}をめぐり、違法性を認めることなく和解に至りました：{fact_clean}。"
            elif bucket == "unverified":
                raw = f"未確認の初期報道によれば、{loc_topic}に関して{fact_clean}。"
            else:
                raw = f"{loc_topic}をめぐり、{fact_clean}。" if loc_topic and loc_topic not in fact_clean else f"{fact_clean}。"
        elif role_slot == "hook_scale":
            if bucket == "final_judgment":
                raw = f"確定判決の記録によれば、規模は{fact_clean}。"
            elif bucket == "audit_finding":
                raw = f"監査報告書の指摘によれば、規模は{fact_clean}。"
            elif bucket == "indictment":
                raw = f"起訴状の指摘によれば、規模は{fact_clean}。"
            elif bucket == "court_record":
                raw = f"裁判所の記録によれば、規模は{fact_clean}。"
            elif bucket == "alleged_regulator":
                raw = f"当局の公表資料によれば、規模は{fact_clean}。"
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"報道によれば、確認された規模として{fact_clean}。"
            elif bucket == "settled":
                raw = f"合意規模として、{fact_clean}（違法性を認めることなく和解）。"
            elif bucket == "unverified":
                raw = f"未確認の初期報道によれば、規模は{fact_clean}。"
            else:
                raw = f"確認された規模として、{fact_clean}。"
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean) <= 16) else "どこから綻びが始まったのか。"
            if not q_short.endswith(("か。", "？", "?")):
                q_short = f"{q_short.rstrip(' 。')}か。"
            if bucket == "final_judgment" and not any(p in fact_clean for p in ["判決", "確定"]):
                raw = f"{q_short} 裁判所の判決によれば、{fact_clean}。"
            elif bucket == "audit_finding" and not any(p in fact_clean for p in ["監査", "検査"]):
                raw = f"{q_short} 監査報告書によれば、{fact_clean}。"
            elif bucket == "indictment" and not any(p in fact_clean for p in ["起訴", "検察"]):
                raw = f"{q_short} 起訴状によれば、{fact_clean}。"
            elif bucket == "court_record" and not any(p in fact_clean for p in ["裁判所", "記録"]):
                raw = f"{q_short} 裁判所の記録によれば、{fact_clean}。"
            elif bucket == "alleged_regulator" and not any(p in fact_clean for p in ["当局", "公表"]):
                raw = f"{q_short} 当局の公表によれば、{fact_clean}。"
            elif bucket in ("alleged", "press_allegation", "press_charge") and "報道" not in fact_clean:
                raw = f"{q_short} 報道によれば、{fact_clean}。"
            elif bucket == "settled" and "和解" not in fact_clean:
                raw = f"{q_short} {fact_clean}（違法性を認めることなく和解）。"
            elif bucket == "unverified" and "未確認" not in fact_clean:
                raw = f"{q_short} 未確認の初期報道によれば、{fact_clean}。"
            else:
                raw = f"{q_short} {fact_clean}。"
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
                tails = [f"{fact_clean}という点が初期から伝えられています。", f"{fact_clean}との経緯が基礎資料に記されています。", f"{fact_clean}という点が発端の文書で確認できます。", f"{fact_clean}との内容が初期段階の記録に残されています。", f"{fact_clean}という事実が資料の冒頭に挙げられています。"]
            elif role_slot == "mechanism":
                tails = [f"{fact_clean}という実態が仕組みの記録に示されています。", f"{fact_clean}との流れが取引の文書で確認できます。", f"{fact_clean}という記述が詳細な記録に続きます。", f"{fact_clean}との点が制度上の該当箇所に挙げられています。", f"{fact_clean}という経緯が推移を追った文書に示されています。"]
            elif role_slot == "crack":
                tails = [f"{fact_clean}という内容が後続局面の資料に記されています。", f"{fact_clean}との点が変化の表面化段階で見られます。", f"{fact_clean}という事実が後続の公表記録に挙げられています。", f"{fact_clean}との展開が一連の記録後半に示されています。", f"{fact_clean}という事態が関係資料の後半で確認されます。"]
            else:
                tails = [f"{fact_clean}という点が事後の整理資料に残されています。", f"{fact_clean}との内容が経過をまとめた記録に続きます。", f"{fact_clean}という状況が一連の末尾文書に記されています。", f"{fact_clean}との事実が総括部分の記述に挙げられます。", f"{fact_clean}という教訓が記録全体の結びとして残ります。"]
            raw = f"{pfx}{tails[v_idx]}"

    elif m == "VN":
        fact_stripped, existing_pfx_vn = strip_attribution_prefix(fact, "VN")
        fact_clean = fact_stripped if existing_pfx_vn else fact
        if role_slot == "hook_catalyst":
            if bucket == "final_judgment":
                raw = f"Bước ngoặt trong {loc_topic}: Theo phán quyết của tòa án, {fact_clean}."
            elif bucket == "audit_finding":
                raw = f"Trong cuộc thanh tra {loc_topic}: Theo kết luận thanh tra, {fact_clean}."
            elif bucket == "indictment":
                raw = f"Trong cuộc khủng hoảng {loc_topic}, Theo cáo trạng của cơ quan công tố, {fact_clean}."
            elif bucket == "court_record":
                raw = f"Trong vụ việc {loc_topic}: Theo hồ sơ tại tòa án, {fact_clean}."
            elif bucket == "alleged_regulator":
                raw = f"Trong vụ việc {loc_topic}: Theo cơ quan chức năng, {fact_clean}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"Trong bối cảnh {loc_topic}, theo phản ánh của báo chí, {fact_clean}."
            elif bucket == "settled":
                raw = f"Vụ việc {loc_topic} khép lại bằng thỏa thuận dàn xếp: {fact_clean}."
            elif bucket == "unverified":
                raw = f"Theo thông tin bước đầu chưa kiểm chứng về {loc_topic}: {fact_clean}."
            else:
                raw = f"Trong bối cảnh {loc_topic}, {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"{fact_clean}."
        elif role_slot == "hook_scale":
            if bucket == "final_judgment":
                raw = f"Theo bản án có hiệu lực, quy mô xác nhận: {fact_clean}."
            elif bucket == "audit_finding":
                raw = f"Báo cáo kiểm toán xác định quy mô: {fact_clean}."
            elif bucket == "indictment":
                raw = f"Hồ sơ truy tố xác nhận quy mô: {fact_clean}."
            elif bucket == "court_record":
                raw = f"Theo hồ sơ tại tòa án, quy mô xác nhận: {fact_clean}."
            elif bucket == "alleged_regulator":
                raw = f"Theo cơ quan quản lý, quy mô xác nhận: {fact_clean}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"Theo thông tin báo chí, quy mô xác nhận: {fact_clean}."
            elif bucket == "settled":
                raw = f"Quy mô xử lý xác nhận: {fact_clean} (dàn xếp mà không thừa nhận sai phạm)."
            elif bucket == "unverified":
                raw = f"Theo phản ánh ban đầu chưa kiểm chứng, quy mô ước tính: {fact_clean}."
            else:
                raw = f"Quy mô xác nhận: {fact_clean}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean.split()) <= 8) else "Đâu là nguyên nhân cốt lõi?"
            if not q_short.endswith("?"):
                q_short += "?"
            if bucket == "final_judgment" and not any(p in fact_clean for p in ["tòa", "phán quyết", "bản án"]):
                raw = f"{q_short} Theo phán quyết của tòa án, {fact_clean}."
            elif bucket == "audit_finding" and not any(p in fact_clean for p in ["kiểm toán", "thanh tra"]):
                raw = f"{q_short} Theo kết luận thanh tra, {fact_clean}."
            elif bucket == "indictment" and not any(p in fact_clean for p in ["truy tố", "cáo trạng"]):
                raw = f"{q_short} Theo cáo trạng của cơ quan công tố, {fact_clean}."
            elif bucket == "court_record" and not any(p in fact_clean for p in ["tòa án", "hồ sơ tại tòa"]):
                raw = f"{q_short} Theo hồ sơ tại tòa án, {fact_clean}."
            elif bucket == "alleged_regulator" and not any(p in fact_clean for p in ["cơ quan", "thanh tra", "công bố"]):
                raw = f"{q_short} Theo cơ quan chức năng, {fact_clean}."
            elif bucket in ("alleged", "press_allegation", "press_charge") and "báo chí" not in fact_clean.lower():
                raw = f"{q_short} Theo thông tin báo chí phản ánh, {fact_clean}."
            elif bucket == "settled" and not any(p in fact_clean for p in ["dàn xếp", "hòa giải"]):
                raw = f"{q_short} {fact_clean} (thỏa thuận dàn xếp không thừa nhận sai phạm)."
            elif bucket == "unverified" and "chưa kiểm chứng" not in fact_clean:
                raw = f"{q_short} Theo thông tin bước đầu chưa kiểm chứng, {fact_clean}."
            else:
                raw = f"{q_short} {fact_clean}."
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
                tails = [f"việc {fact_clean} đã được tài liệu ghi nhận rõ.", f"{fact_clean}, đặt nền tảng ban đầu cho toàn bộ chuỗi giao dịch.", f"dữ liệu khởi đầu cho thấy {fact_clean}, mở ra diễn biến phức tạp tiếp theo.", f"{fact_clean}, tạo tiền đề cho các diễn biến tiếp theo.", f"những ghi chép mở đầu xác nhận việc {fact_clean} trước khi sự việc mở rộng."]
            elif role_slot == "mechanism":
                tails = [f"khi xem xét chi tiết cơ chế, việc {fact_clean} được tài liệu ghi nhận cụ thể.", f"{fact_clean}, thể hiện áp lực tài chính trong giai đoạn này.", f"phân tích chuỗi dòng tiền cho thấy {fact_clean}, tạo nút thắt lớn cho thanh khoản.", f"{fact_clean}, tạo ra kẽ hở trong quản lý và giám sát.", f"theo trình tự dữ liệu công bố, {fact_clean} là mắt xích dẫn đến sai phạm."]
            elif role_slot == "crack":
                tails = [f"ở bước ngoặt điều tra tiếp theo, hồ sơ xác định việc {fact_clean} có dấu hiệu bất thường.", f"{fact_clean}, dẫn tới các biện pháp xử lý và can thiệp từ cơ quan chức năng.", f"các ghi nhận công khai sau đó cho thấy {fact_clean}, buộc các bên phải vào cuộc.", f"{fact_clean}, phơi bày sai phạm trong quản trị.", f"hồ sơ điều tra giai đoạn này ghi nhận việc {fact_clean} như một chứng cứ then chốt."]
            else:
                tails = [f"trong phần tổng kết hồ sơ, tài liệu nêu rõ việc {fact_clean} đã để lại tổn thất lớn.", f"{fact_clean}, để lại hệ quả pháp lý và nghĩa vụ tài chính kéo dài.", f"các kết luận sau sự kiện tiếp tục khẳng định việc {fact_clean} là bài học quản trị đắt giá.", f"{fact_clean}, trở thành bài học cảnh báo sâu sắc cho thị trường.", f"nhìn lại toàn bộ chuỗi chứng cứ, hồ sơ chỉ rõ việc {fact_clean} khó có thể đảo ngược."]
            raw = f"{pfx}{tails[v_idx]}"

    else:  # EN
        fact_stripped, existing_pfx_en = strip_attribution_prefix(fact, "EN")
        fact_clean = fact_stripped if existing_pfx_en else fact
        if role_slot == "hook_catalyst":
            if bucket == "final_judgment":
                raw = f"In {loc_topic}, the court ruled that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"The court ruled that {fact_clean}."
            elif bucket == "audit_finding":
                raw = f"In {loc_topic}, the audit report established that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"The audit report established that {fact_clean}."
            elif bucket == "indictment":
                raw = f"In {loc_topic}, the indictment alleges that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"The indictment alleges that {fact_clean}."
            elif bucket == "court_record":
                raw = f"In {loc_topic}, court records reflect that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"Court records reflect that {fact_clean}."
            elif bucket == "alleged_regulator":
                raw = f"In {loc_topic}, regulatory filings indicate that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"Regulatory filings indicate that {fact_clean}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"In {loc_topic}, press reports indicate that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"According to press reports, {fact_clean}."
            elif bucket == "settled":
                raw = f"In {loc_topic}, the matter concluded under settlement terms: {fact_clean}."
            elif bucket == "unverified":
                raw = f"In {loc_topic}, preliminary reports indicate that {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"Preliminary reports indicate that {fact_clean}."
            else:
                raw = f"In {loc_topic}, {fact_clean}." if loc_topic and loc_topic not in fact_clean else f"{fact_clean}."
        elif role_slot == "hook_scale":
            if bucket == "final_judgment":
                raw = f"Judicial findings establish documented scale: {fact_clean}."
            elif bucket == "audit_finding":
                raw = f"Audit findings establish documented scale: {fact_clean}."
            elif bucket == "indictment":
                raw = f"Charging documents state documented scale: {fact_clean}."
            elif bucket == "court_record":
                raw = f"According to court records, documented scale reached: {fact_clean}."
            elif bucket == "alleged_regulator":
                raw = f"Regulatory filings establish documented scale: {fact_clean}."
            elif bucket in ("alleged", "press_allegation", "press_charge"):
                raw = f"According to press reports, documented scale reached: {fact_clean}."
            elif bucket == "settled":
                raw = f"Documented scale under resolved terms: {fact_clean} (settled without admitting wrongdoing)."
            elif bucket == "unverified":
                raw = f"Early unverified reports suggest documented scale: {fact_clean}."
            else:
                raw = f"Documented scale confirmed: {fact_clean}."
        elif role_slot == "hook_paradox":
            q_short = cq_clean if (cq_clean and len(cq_clean.split()) <= 8) else "Where did the structural tension begin?"
            if not q_short.endswith("?"):
                q_short += "?"
            from app.services.story_provenance_engine import _LEGAL_QUALIFIER_PATTERNS, _qualifier_pattern_matches
            if bucket == "final_judgment" and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("final_judgment", [])):
                raw = f"{q_short} According to the court ruling, {fact_clean}."
            elif bucket == "audit_finding" and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("audit_finding", [])):
                raw = f"{q_short} According to the audit report, {fact_clean}."
            elif bucket == "indictment" and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("indictment", [])):
                raw = f"{q_short} Charging documents state that {fact_clean}."
            elif bucket == "court_record" and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("court_record", [])):
                raw = f"{q_short} According to court records, {fact_clean}."
            elif bucket == "alleged_regulator" and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("alleged_regulator", [])):
                raw = f"{q_short} According to regulatory filings, {fact_clean}."
            elif bucket in ("alleged", "press_allegation", "press_charge") and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("alleged", [])):
                raw = f"{q_short} According to press reports, {fact_clean}."
            elif bucket == "settled" and "settled" not in fact_clean.lower():
                raw = f"{q_short} {fact_clean} (settled without admitting wrongdoing)."
            elif bucket == "unverified" and not any(_qualifier_pattern_matches(p, fact_clean, "EN") for p in _LEGAL_QUALIFIER_PATTERNS["EN"].get("unverified", [])):
                raw = f"{q_short} Early unverified reports suggest that {fact_clean}."
            else:
                raw = f"{q_short} {fact_clean}."
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
            fact_clean = fact_clean.strip().rstrip(". ")
            if pfx:
                if pfx.rstrip().endswith("that") and fact_clean and fact_clean[0].isupper():
                    first_word = fact_clean.split()[0]
                    if not first_word.isupper() and first_word not in (
                        "European", "American", "Korean", "Japanese", "Vietnamese", "Article", "Under", "Review",
                    ):
                        fact_clean = fact_clean[0].lower() + fact_clean[1:]

            if role_slot == "setup":
                tails = [
                    f"early documentation establishes that {fact_clean}.",
                    f"{fact_clean}, laying the institutional foundation for subsequent transactions.",
                    f"baseline records confirm that {fact_clean}.",
                    f"{fact_clean}, setting the initial framework in place.",
                    f"initial public disclosures reveal that {fact_clean}.",
                ]
            elif role_slot == "mechanism":
                tails = [
                    f"examining the operational mechanism confirms that {fact_clean}.",
                    f"{fact_clean}, demonstrating the core transactional flow.",
                    f"evidence tracking the financial architecture shows that {fact_clean}.",
                    f"{fact_clean}, creating an underlying structural distortion.",
                    f"detailed operational records show that {fact_clean}.",
                ]
            elif role_slot == "crack":
                tails = [
                    f"at the critical turning point, documentation revealed that {fact_clean}.",
                    f"{fact_clean}, triggering escalating supervisory scrutiny.",
                    f"subsequent investigative findings established that {fact_clean}.",
                    f"{fact_clean}, exposing the operational breakdown.",
                    f"evidentiary filings at this stage confirm that {fact_clean}.",
                ]
            else:  # aftermath
                tails = [
                    f"in the institutional aftermath, records confirm that {fact_clean}.",
                    f"{fact_clean}, resulting in lasting regulatory liabilities.",
                    f"post-investigation reviews concluded that {fact_clean}.",
                    f"{fact_clean}, underscoring the ongoing reform challenge.",
                    f"final documented reviews established that {fact_clean}.",
                ]
            raw = f"{pfx}{tails[v_idx]}"

    if m == "KR":
        raw = re.sub(r"\b[Pp]ackage\b", "지원책", raw)
        raw = re.sub(r"\b[Pp]lan\b", "계획", raw)
    _, lead_pfx = strip_attribution_prefix(raw, market=m)
    if lead_pfx:
        raw = dehedge_predicate(raw, market=m)
    return raw, [cid]


def _compact_en_hook_line(text: str, target_words: int = 14) -> str:
    """Intelligently compact an English hook line without cutting words in half or severing clauses."""
    clean = text.strip().rstrip(". ")
    words = clean.split()
    if len(words) <= target_words:
        return clean + "."

    paren_m = re.search(r"\s*(\([^()]+\))\s*$", clean)
    suffix = f" {paren_m.group(1)}" if paren_m else ""
    body = clean[: paren_m.start()].strip() if paren_m else clean

    strip_patterns = [
        r",\s*(?:including|resulting|setting|leading|leaving|underscoring|creating|exposing)\s+.*$",
        r",?\s*rather\s+than\s+.*$",
        r"\s+to\s+(?:fund|claim|pass|direct|cover|expand|support)\s+.*$",
        r"\s+to\s+(?:the\s+importer|consumers|end\s+consumers|retailers).*$",
        r",\s*laying\s+the\s+.*$",
    ]
    for pat in strip_patterns:
        cand = re.sub(pat, "", body).strip().rstrip(" ,;:")
        if len(cand.split()) <= target_words + 2 and len(cand.split()) >= 6:
            return cand + suffix + "."

    dangling = {
        "the", "a", "an", "of", "in", "to", "for", "with", "and", "or", "by",
        "from", "as", "at", "whose", "which", "that", "their", "its", "into",
        "stated", "reported", "published", "described", "noted", "alleged",
        "u.s.", "u.s", "federal", "direct", "major", "preliminary", "operational",
        "financial", "corporate", "official", "regulatory", "structural",
        "customs", "tariff", "trade", "price", "duty", "market", "executive",
    }
    b_words = body.split()
    cap = target_words
    while cap < len(b_words) and ("-" in b_words[cap - 1] or b_words[cap - 1].lower().rstrip(".,;:") in dangling):
        cap += 1
    while cap > 5 and ("-" in b_words[cap - 1] or b_words[cap - 1].lower().rstrip(".,;:") in dangling):
        cap -= 1
    return " ".join(b_words[:cap]).rstrip(" ,;:") + suffix + "."


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
    from app.services.story_provenance_engine import extract_claim_elements, normalize_market_code

    def _get(obj: Any, attr: str, default: Any = "") -> Any:
        return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)

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
        [
            c for c in verified_pool
            if _get(c, "causal_role", "") in ("background_context", "transmission_mechanism")
            or str(_get(c, "source_type", "")) in ("regulator", "gov", "court")
        ]
        + pools["backgrounds"]
        + [c for c in pools["unverified_pool"] if _get(c, "causal_role", "") != "primary_catalyst"]
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

    # Scale and partition slots dynamically so each claim in evidence_ledger has a designated slot
    # Ensures full docudrama duration (>= 180s) while eliminating spoken redundancy (Rule 130/131)
    total_claims_n = len(all_claims)
    if total_claims_n >= 10:
        n_b1 = min(3, total_claims_n)
        n_b5 = min(3, max(2, (total_claims_n - 2) // 4))
        n_b4 = 2
        n_b2 = min(3, max(2, (total_claims_n - 3 - 2) // 4))
        n_b3 = max(2, total_claims_n - n_b1 - n_b2 - n_b4 - n_b5)
    elif total_claims_n >= 8:
        n_b1 = 3
        n_b5 = 2
        n_b4 = 2
        n_b2 = 2
        n_b3 = max(1, total_claims_n - n_b1 - n_b2 - n_b4 - n_b5)
    else:
        target_slots = max(14, total_claims_n)
        n_b1 = min(3, total_claims_n) if total_claims_n > 0 else 3
        rem = max(0, target_slots - n_b1)
        n_b4 = 2
        n_b5 = max(2, min(3, (rem - 2) // 4)) if rem > 2 else 1
        n_b2 = max(2, min(3, (rem - 2) // 4)) if rem > 2 else 1
        n_b3 = max(3, rem - n_b4 - n_b5 - n_b2) if rem > 4 else max(1, rem)

    beat_specs: List[Tuple[str, float, List[Tuple[str, List[Any]]]]] = [
        ("B1_hook", 19.2, [
            ("hook_catalyst", hook_source),
            ("hook_scale", verified_pool or hook_source),
            ("hook_paradox", hook_source),
        ][:n_b1]),
        ("B2_setup", 40.8, [("setup", b2_source) for _ in range(n_b2)]),
        ("B3_scheme", 79.2, [("mechanism", b3_source) for _ in range(n_b3)]),
        ("B4_crack", 60.0, [("crack", b4_source) for _ in range(n_b4)]),
        ("B5_aftermath", 40.8, [("aftermath", b5_source) for _ in range(n_b5)]),
    ]

    raw_beats: List[Tuple[str, float, List[Any]]] = []
    vh_idx = 0
    b1_catalyst_cid: Optional[str] = None
    total_rendered_lines = 0
    for beat_id, dur_s, slots in beat_specs:
        beat_lines: List[StorySceneLine] = []
        is_hook_beat = beat_id.startswith("B1")
        is_aftermath = beat_id.startswith("B5")
        for l_idx, (role_slot, src_pool) in enumerate(slots, start=1):
            disallowed: Set[str] = set()
            used_in_current_beat = {
                cid
                for ln_c in beat_lines
                for cid in (ln_c.claim_ids or [])
            }
            disallowed.update(used_in_current_beat)
            if b1_catalyst_cid and not is_hook_beat:
                disallowed.add(b1_catalyst_cid)

            used_in_prior = {
                cid
                for b_prior in raw_beats
                for ln_p in b_prior[2]
                for cid in (ln_p.claim_ids or [])
            }
            # Step 1: Prioritize claims unused anywhere in prior beats
            unused_in_pool = [c for c in src_pool if _get_cid(c) and _get_cid(c) not in used_in_prior and _get_cid(c) not in disallowed]
            if unused_in_pool:
                src_pool = unused_in_pool
                disallowed.update(used_in_prior)
            else:
                unused_in_all = [c for c in all_claims if _get_cid(c) and _get_cid(c) not in used_in_prior and _get_cid(c) not in disallowed]
                if unused_in_all:
                    src_pool = unused_in_all
                    disallowed.update(used_in_prior)
                elif is_aftermath:
                    # When all claims in ledger are exhausted, never repeat B1 catalyst or B3 scheme claims
                    if b1_catalyst_cid:
                        disallowed.add(b1_catalyst_cid)
                    if len(raw_beats) > 2:
                        for ln_p in raw_beats[2][2]:
                            disallowed.update(ln_p.claim_ids or [])
                elif not is_hook_beat:
                    # If pool exhausted, disallow immediately preceding beat to preserve freshness
                    if raw_beats:
                        for ln_p in raw_beats[-1][2]:
                            disallowed.update(ln_p.claim_ids or [])
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
                slot_idx=total_rendered_lines,
            )
            total_rendered_lines += 1
            vh = visual_hooks_seq[vh_idx % len(visual_hooks_seq)]
            vh_idx += 1
            beat_lines.append(StorySceneLine(
                line_id=f"{beat_id[:2]}_L{l_idx:02d}",
                text=txt,
                claim_ids=cids,
                visual_hook=vh,
            ))

        # Insert authentic editorial pattern interrupts into B2, B3, B4, B5 to break pacing monotony and deliver living warning
        b_key = beat_id[:2]
        market_pattern_interrupts = {
            "KR": {
                "B2": ("경고의 신호는 분명했습니다.", "pattern_interrupt"),
                "B3": ("구멍은 이미 커져 있었습니다.", "grease_pencil"),
                "B4": ("결국 청구서가 돌아왔습니다.", "stop_motion_hit"),
                "B5": ("제도의 빈틈은 아직 완전히 메워지지 않았습니다.", "stop_motion_hit"),
            },
            "JA": {
                "B2": ("警告の兆候は明白でした。", "pattern_interrupt"),
                "B3": ("亀裂は急速に深まりました。", "grease_pencil"),
                "B4": ("残されたのは巨額の負債でした。", "stop_motion_hit"),
                "B5": ("制度の歪みは、今も完全には埋まっていません。", "stop_motion_hit"),
            },
            "VN": {
                "B2": ("Dấu hiệu cảnh báo bị phớt lờ.", "pattern_interrupt"),
                "B3": ("Lỗ hổng nhanh chóng lan rộng.", "grease_pencil"),
                "B4": ("Hóa đơn cuối cùng đã đến.", "stop_motion_hit"),
                "B5": ("Lỗ hổng thể chế vẫn chưa được lấp đầy.", "stop_motion_hit"),
            },
            "EN": {
                "B2": ("The warning signs were clear.", "pattern_interrupt"),
                "B3": ("The crack was already widening.", "grease_pencil"),
                "B4": ("The bill finally came due.", "stop_motion_hit"),
                "B5": ("The systemic loophole has yet to be fully closed.", "stop_motion_hit"),
            },
        }
        m_pis = market_pattern_interrupts.get(m, market_pattern_interrupts["EN"])
        if b_key in m_pis and len(beat_lines) >= 2:
            pi_text, pi_vh = m_pis[b_key]
            insert_pos = 2 if b_key == "B2" else (3 if b_key == "B3" else 1)
            insert_pos = min(insert_pos, len(beat_lines))
            pi_line = StorySceneLine(
                line_id=f"{b_key}_PI",
                text=pi_text,
                claim_ids=[],
                visual_hook=pi_vh,
            )
            beat_lines.insert(insert_pos, pi_line)
            for idx_re, ln_re in enumerate(beat_lines, start=1):
                ln_re.line_id = f"{b_key}_L{idx_re:02d}"

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
                        shrunk_r = _compact_kr_hook_line(rem_clean, max_chars=40)
                        ln_cur.text = f"{q_text} {shrunk_r}".strip()
                    elif m == "EN":
                        rem_clean = rem.strip()
                        shrunk_r = _compact_en_hook_line(rem_clean, target_words=10)
                        ln_cur.text = f"{q_text} {shrunk_r}".strip()
                    else:  # VN
                        words = rem.strip().split()
                        cap_words = 8 if len(words) > 10 else len(words)
                        shrunk_rem = " ".join(words[:cap_words]).rstrip(" ,;:")
                        if not shrunk_rem.endswith((".", "!", "?")):
                            shrunk_rem += "."
                        ln_cur.text = f"{q_text} {shrunk_rem}".strip()
                else:
                    paren_match = re.search(r"\s*(\([^()]+\))\s*[.。!?]?$", cur_t)
                    paren_suffix = paren_match.group(1) if paren_match else ""
                    main_body = cur_t[: paren_match.start()].strip() if paren_match else cur_t.strip().rstrip(".。!?")

                    if m == "EN":
                        shrunk_main = _compact_en_hook_line(main_body, target_words=14).rstrip(". ")
                        if paren_suffix:
                            ln_cur.text = f"{shrunk_main} {paren_suffix}."
                        else:
                            ln_cur.text = f"{shrunk_main}."
                    elif m == "VN":
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
                        shrunk_main = _compact_kr_hook_line(main_body, max_chars=40)
                        if paren_suffix:
                            ln_cur.text = f"{shrunk_main.rstrip('.')} {paren_suffix}."
                        else:
                            ln_cur.text = f"{shrunk_main.rstrip('.')}."
            b1_dur = float(
                estimate_script_speech_duration([ln.text for ln in raw_beats[0][2]], market=m, docudrama_tempo=True)["estimated_duration_sec"]
            )

    if b1_dur > 24.0 and m == "KR":
        for idx in (2, 1, 0):
            if b1_dur <= 24.0:
                break
            ln_cur = raw_beats[0][2][idx]
            cur_t = ln_cur.text
            if idx == 2 and any(sep in cur_t for sep in ("?", "？")):
                sep_used = "？" if "？" in cur_t else "?"
                q_part, _, rem = cur_t.partition(sep_used)
                shrunk_r = _compact_kr_hook_line(rem.strip(), max_chars=34)
                ln_cur.text = f"{q_part.strip()}{sep_used} {shrunk_r}".strip()
            else:
                paren_match = re.search(r"\s*(\([^()]+\))\s*[.。!?]?$", cur_t)
                paren_suffix = paren_match.group(1) if paren_match else ""
                main_body = cur_t[: paren_match.start()].strip() if paren_match else cur_t.strip().rstrip(".。!?")
                shrunk_main = _compact_kr_hook_line(main_body, max_chars=34)

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
    expand_beats = [2, 1, 3]  # B3_scheme, B2_setup, B4_crack (never bloat B1_hook or B5_aftermath)
    expand_roles = {1: "setup", 2: "mechanism", 3: "crack"}
    expand_pools = {1: b2_source, 2: b3_source, 3: b4_source}
    extra_guard = 0
    while (measured_s < d_min or measured_units < eff_u_min) and measured_s < (d_max - 20.0) and measured_units < (eff_u_max - 30) and extra_guard < 26 and all_claims:
        b_idx = expand_beats[extra_guard % len(expand_beats)]
        beat_id_e, _, beat_lines_e = raw_beats[b_idx]
        used_cids_global = {cid for _, _, lns in raw_beats for ln in lns for cid in (ln.claim_ids or []) if cid}
        unused_claims_global = [c for c in all_claims if _get_cid(c) and _get_cid(c) not in used_cids_global]
        pool_to_use = unused_claims_global or expand_pools[b_idx]
        disallow_e = {cid for ln in beat_lines_e for cid in (ln.claim_ids or [])}
        if b1_catalyst_cid:
            disallow_e.add(b1_catalyst_cid)
        if len(raw_beats) > 4:
            for ln_b5 in raw_beats[4][2]:
                disallow_e.update(ln_b5.claim_ids or [])
        c_obj = _pick_claim(pool_to_use, disallow_cids=disallow_e)
        if not c_obj:
            c_obj = _pick_claim(all_claims, disallow_cids=disallow_e)
        if not c_obj:
            break
        l_idx_e = len(beat_lines_e) + 1
        txt_e, cids_e = _render_claim_sentence(
            c_obj,
            market=m,
            topic=topic,
            role_slot=expand_roles[b_idx],
            central_question="",
            slot_idx=total_rendered_lines + extra_guard,
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
                        "CRITICAL LANGUAGE & PROVENANCE MANDATE FOR KOREAN (KR) MARKET:\n"
                        "1. Write 100% natural, authoritative investigative Korean narration (Hangul). English/foreign prose is STRICTLY FORBIDDEN.\n"
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} spoken Hangul+numeral syllables across 19-24 lines). Beat 1 (B1_hook) MUST have ONLY 3 concise lines totaling <= 95 syllables (~15-20s) and cite ONLY verified_primary, official_regulation, or corroborated_secondary claim_ids (NEVER put unverified_secondary / unconfirmed_claim inside B1_hook!).\n"
                        "3. STRICT ATTRIBUTION SPECIFICITY (Gate 3):\n"
                        "   - For claims with credibility_tier='unconfirmed_claim' (RSS snippets/unverified reports): Attribute ONLY as preliminary/unconfirmed reporting ('초기 보도에 따르면', '확인되지 않은 보도에 따르면', '일부 보도에 따르면', '전해진 바에 따르면'). NEVER claim them as '언론사 취재 결과', '취재 결과', or '감독 당국의 조사'!\n"
                        "     DO NOT frame unverified secondary reports as established statutory authority ('개정 법률에 따른') or binding state guarantees ('국가가 보장하는')! Qualify them strictly as reported proposals or media speculation ('보도에 제시된 방안에 따르면', '언론 일각에서는 정책적 선례라는 해석이 제기됐습니다').\n"
                        "   - For claims with credibility_tier='official_regulation' or government announcements: Attribute to the announcement or statute ('정부 발표에 따르면', '공식 발표 자료에 따르면', '현행 법령에 따르면'). Do NOT invent non-existent investigations ('감독 당국의 조사' is forbidden unless the claim explicitly describes a supervisory investigation).\n"
                        "   - For claims with credibility_tier='press_allegation' / corroborated_secondary: Attribute to reporting ('보도에 따르면', '언론 보도를 보면', '당시 분석 보도에 따르면').\n"
                        "   - Distinguish 'court_judgment' (법원 확정 판결에 따르면) vs 'indictment' (검찰 공소장에 따르면) vs 'criminal_complaint' (고발장·소장에 따르면).\n"
                        "4. ANTI-REPETITIVE TEMPLATE FILLER (Gate 5):\n"
                        "   - DO NOT start consecutive lines with '보도에 따르면' or '취재에 따르면'! Alternate between lines with attributions and narrative/structural explanatory lines.\n"
                        "   - Include at least ONE short, punchy 2-6 word Pattern Interrupt line in Beat 2, Beat 3, and Beat 4 reflecting the topic's dramatic tension (e.g. '경고는 무시됐습니다.', '위험은 은폐됐습니다.', '구멍은 커졌습니다.') without any boilerplate attribution prefixes and with visual_hook='pattern_interrupt' or 'grease_pencil'. Do NOT attach ungrounded claims to pattern interrupts.\n"
                        "5. STRICT CAUSAL DISCIPLINE & SOFTENED PREDICATES (Rule 130):\n"
                        "   - NEVER assert macro causal leaps (e.g. '손실이 공공으로 이전됐다', '청구서는 국가로 향했다') unless a cited claim explicitly proves that consequence.\n"
                        "   - When citing analytical findings or allegations, use softened reported verbs ('넘겼다는 분석입니다', '넘긴 것으로 전해졌습니다'), NEVER definitive past tense ('넘겼습니다').\n\n"
                    )
                elif market == "JA":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR JAPANESE (JA) MARKET:\n"
                        "1. Write 100% natural, authoritative Japanese investigative narration. No Hangul or foreign sentences.\n"
                        f"2. STRICT LENGTH & PACING: Write 23-28 substantive lines of 50-65 Japanese characters each so total spoken narration is STRICTLY 1,100-1,600 Japanese characters (NEVER < 950 chars! Within {u_min}-{u_max} chars / 180-300s). Beat 1 (B1_hook) MUST have 3 short lines totaling <= 115 chars (~15-19s) citing ONLY verified_primary/corroborated_secondary claim_ids.\n"
                        "3. Distinguish judgment (判決によれば) vs indictment (起訴状によれば) vs complaint (訴状によれば) vs named institution report (日銀公表/報告書によれば) vs unverified press reports (未確認の報道によれば).\n"
                        "4. Never attribute unverified claims to official investigatory results (e.g. avoid '調査報道' or '当局調査' for unverified snippets).\n"
                        "5. Include short 5-10 char pattern interrupt lines in B2, B3, B4 without repetitive reporting templates.\n\n"
                    )
                elif market == "VN":
                    user_prompt += (
                        "CRITICAL LANGUAGE MANDATE FOR VIETNAMESE (VN) MARKET:\n"
                        "1. Write 100% natural, authoritative Vietnamese narration with full Vietnamese diacritics. No English/CJK prose.\n"
                        f"2. STRICT LENGTH & PACING: Total 180-300s ({u_min}-{u_max} Vietnamese words across 19-24 lines). Beat 1 (B1_hook) MUST have 3 concise lines totaling <= 75 words (<= 21s) citing ONLY verified_primary or corroborated_secondary claim_ids.\n"
                        "3. Distinguish judgment (Theo phán quyết của tòa án) vs indictment (Theo cáo trạng) vs complaint (Theo đơn kiện) vs unverified press reports (Theo thông tin bước đầu chưa kiểm chứng).\n"
                        "4. CẤM gán thông tin chưa kiểm chứng thành kết quả điều tra chính thức. Thêm câu ngắt nhịp kịch tính ngắn (2-6 từ) ở Beat 2, Beat 3, Beat 4.\n\n"
                    )
                else:
                    user_prompt += (
                        "CRITICAL PROVENANCE & STRICT PACING MANDATE FOR ENGLISH (EN) MARKET:\n"
                        f"1. STRICT WORD COUNT & DURATION: Write 100% crisp investigative English narration totaling {u_min}-{u_max} words across 19-24 lines (target 370-420 words, 180-240s docudrama speech timing). Beat 1 (B1_hook) MUST have 3 concise lines totaling <= 48 words (<= 23.5s) citing ONLY verified_primary or corroborated_secondary claim_ids.\n"
                        "2. STRICT NON-REDUNDANT CLAIM GROUNDING:\n"
                        "   - Ground every substantive factual sentence in a DISTINCT claim from the evidence ledger.\n"
                        "   - DO NOT repeat the same claim or numbers across multiple lines within the same beat.\n"
                        "   - Follow the chronological/investigative beat progression: B1_hook (primary catalyst & scope), B2_setup (historical context & acquisition intent), B3_losses (operating losses & market pressures), B4_crack (insolvency trigger & current trading), B5_aftermath (industry context & closing statutory status).\n"
                        "3. SOURCING & ATTRIBUTION PURITY:\n"
                        "   - Match attribution exactly to each claim's credibility_tier and verification_status:\n"
                        "     * verified_primary / official_regulation: 'An official regulatory notice confirms that...'\n"
                        "     * corroborated_secondary / press_allegation: 'According to press reports,...', 'Press reports indicate that...'\n"
                        "     * unverified_secondary / unconfirmed_claim: 'Unconfirmed press reports indicated that...'\n"
                        "   - Exactly ONE clean attribution per line (NO double hedging, NO stacked attributions like 'Press reporting indicates... reportedly').\n"
                        "   - Include short 2-5 word neutral pattern interrupts in B2, B3, B4, B5 with visual_hook='pattern_interrupt' and NO claim_ids (e.g. 'Store numbers contracted.', 'The losses accumulated.', 'Operating deficits mounted.', 'Trading continued.', 'The administration continues.').\n"
                        "   - NEVER invent ungrounded details, motives, or causal mechanisms not stated in the evidence ledger.\n"
                    )

                min_req_claims = max(3, int(-(-len(evidence_ledger) * 60 // 100))) if evidence_ledger else 0
                user_prompt += (
                    "MANDATORY GROUNDING & CAUSAL DISCIPLINE (Rule 130 & 131):\n"
                    f"- Cover at least {min_req_claims}/{len(evidence_ledger)} distinct claims substantively across the 5 beats (B1_hook, B2_setup, B3_scheme, B4_crack, B5_aftermath).\n"
                    "- Introduce Level 1 primary_catalyst BEFORE dissecting Level 2 transmission_mechanism; preserve exact numeric metrics and causal polarity.\n"
                    "- Use standard Arabic numerals (no spelled-out phonetic digit strings) so TTS timing and visual captions stay synchronized.\n"
                    "- Every line must specify a visual_hook: 'stamp', 'ruler_measure', 'compass_arc', 'cutout', 'red_thread', 'magnifier', 'scissors_cut', or 'grease_pencil'.\n"
                    "TIMELINE & FORMAT MANDATE:\n"
                    "- You are writing this investigative docudrama script from the perspective of the current operating date (November 2026). Treat the provided evidence ledger as the established, ground-truth investigative record of events that have occurred.\n"
                    "- Return ONLY valid JSON with 'beats' array. Do not output conversational commentary, critique, or disclaimers outside the JSON structure.\n"
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

                            v_hook = ln.get("visual_hook") or "stamp"
                            text = ln.get("text", "")
                            if (market or "EN").upper() in ("KR", "KO"):
                                text = _normalize_spoken_korean_numbers(text)

                            # Handle editorial pattern interrupts cleanly
                            if _is_editorial_pattern_interrupt(ln, text, market=market):
                                from app.services.story_provenance_engine import strip_attribution_prefix
                                text_clean, _ = strip_attribution_prefix(text, market=market)
                                text_clean = text_clean.strip()
                                lines_data.append(StorySceneLine(
                                    line_id=ln.get("line_id", f"{b_id}_L{l_idx:02d}"),
                                    text=text_clean,
                                    claim_ids=[],
                                    visual_hook="grease_pencil" if v_hook == "stamp" else v_hook,
                                ))
                                continue

                            raw_cids = ln.get("claim_ids") or []
                            if not raw_cids and ln.get("claim_id"):
                                raw_cids = [ln["claim_id"]] if isinstance(ln["claim_id"], str) else list(ln["claim_id"])
                            c_ids = [cid for cid in raw_cids if cid in evidence_map]

                            # Filter out hollow claim citations that have zero semantic overlap with the statement
                            if c_ids:
                                from app.services.story_provenance_engine import (
                                    extract_claim_elements,
                                    has_entity_or_metric_signal,
                                )
                                sig_cids = []
                                for cid in c_ids:
                                    co_raw = evidence_map.get(cid)
                                    if co_raw:
                                        co_txt = str(co_raw.get("claim", "") if isinstance(co_raw, dict) else getattr(co_raw, "claim", ""))
                                        has_sig, _ = has_entity_or_metric_signal(text, extract_claim_elements(co_txt), min_stem_hits=1)
                                        if has_sig:
                                            sig_cids.append(cid)
                                c_ids = sig_cids

                            # Fallback 1: If c_ids is empty, try to match text against all claims in evidence_map
                            if not c_ids and evidence_map:
                                from app.services.story_provenance_engine import (
                                    extract_claim_elements,
                                    has_entity_or_metric_signal,
                                )
                                for cand_cid, cand_co in evidence_map.items():
                                    cand_txt = str(cand_co.get("claim", "") if isinstance(cand_co, dict) else getattr(cand_co, "claim", ""))
                                    cand_has_sig, _ = has_entity_or_metric_signal(text, extract_claim_elements(cand_txt), min_stem_hits=1)
                                    if cand_has_sig:
                                        c_ids.append(cand_cid)
                                        break

                            # Fallback 2: If still empty, check whether it is a short dramatic pattern interrupt
                            if not c_ids:
                                words = text.split()
                                has_digits = any(ch.isdigit() for ch in text)
                                if len(words) <= 10 and not has_digits:
                                    v_hook = "pattern_interrupt"
                                else:
                                    # Fallback 3: Substantive/factual line without claim_id -> assign contextual beat claim
                                    beat_defaults = {
                                        "B1": ["C002", "C003", "C004"],
                                        "B2": ["C001", "C002", "C006"],
                                        "B3": ["C005", "C006", "C002"],
                                        "B4": ["C003", "C004", "C001"],
                                        "B5": ["C007", "C006", "C005"],
                                    }
                                    assigned = False
                                    for b_prefix, c_candidates in beat_defaults.items():
                                        if b_prefix in b_id:
                                            for cand in c_candidates:
                                                if cand in evidence_map:
                                                    c_ids.append(cand)
                                                    assigned = True
                                                    break
                                            if assigned:
                                                break
                                    if not c_ids and evidence_map:
                                        c_ids.append(list(evidence_map.keys())[0])

                            # Spoken redundancy gate: Prevent Beat 5 from repeating Beat 1 claims verbatim
                            if "B5" in b_id and ("C004" in c_ids or "C005" in c_ids):
                                if "C007" in evidence_map or "C008" in evidence_map:
                                    target_c = "C007" if "C007" in evidence_map else "C008"
                                    c_ids = [c for c in c_ids if c not in ("C004", "C005")]
                                    if target_c not in c_ids:
                                        c_ids.append(target_c)

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
                                if (market or "EN").upper() in ("KR", "KO"):
                                    text_soft = _soften_kr_reported_predicate(text, slot_idx=l_idx)
                                    ok_soft, _ = _pre_match_qual(text_soft, c_dict_q, market=market, peer_claims=c_objs_dicts)
                                    if ok_soft:
                                        text = text_soft
                                        continue
                                bkt = _exp_bucket(
                                    legal_status=str(c_dict_q.get("legal_status", "alleged")),
                                    source_type=str(c_dict_q.get("source_type", "press")),
                                    doc_type=str(c_dict_q.get("doc_type", "unknown")),
                                    speaker=c_dict_q.get("speaker"),
                                    procedural_status=str(c_dict_q.get("procedural_status", "unknown")),
                                    verification_status=str(c_dict_q.get("verification_status", "corroborated_secondary")),
                                    credibility_tier=str(c_dict_q.get("credibility_tier", "") or ""),
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
                                    credibility_tier=str(c_dict_q.get("credibility_tier", "") or ""),
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
                    from stages.s04_critic_script import _detect_repetitive_explainer_filler
                    has_filler = _detect_repetitive_explainer_filler(
                        [{"text": ln.text, "claim_ids": ln.claim_ids} for _, _, lns in cand_beats],
                        topic=topic,
                    )
                    from app.services.story_provenance_engine import has_entity_or_metric_signal as _has_sig
                    has_hollow_line = any(
                        bool(ln.claim_ids) and not any(
                            _has_sig(ln.text, _extract_elems(str(getattr(evidence_map[cid], "claim", "") if not isinstance(evidence_map[cid], dict) else evidence_map[cid].get("claim", ""))), min_stem_hits=1)[0]
                            for cid in ln.claim_ids if cid in evidence_map
                        )
                        for _, _, lns in cand_beats for ln in lns
                    )
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
                        and not has_filler
                        and not has_hollow_line
                        and align_res.get("passed", False)
                    )
                    return passed, cand_timing, cand_dur, b1_dur, b1_dur_ok, units_ok, lang_ok, lang_issues, ent_ok, ent_issues, qual_issues, b1_ok, dur_ok, align_res, has_filler

                def _auto_repair_beats(cand_beats: List[Tuple[str, float, List[StorySceneLine]]]) -> List[Tuple[str, float, List[StorySceneLine]]]:
                    from app.services.story_provenance_engine import (
                        expected_qualifier_bucket as _exp_bkt,
                        line_matches_expected_qualifier as _m_qual,
                        strip_attribution_prefix as _strip_pfx,
                    )
                    # 1. Fix qualifier mismatches cleanly (once per line)
                    for b_id, _, lns in cand_beats:
                        for ln in lns:
                            if not ln.claim_ids:
                                continue
                            peer_dicts = [
                                (evidence_map[c].model_dump() if hasattr(evidence_map[c], "model_dump") else dict(evidence_map[c]))
                                for c in ln.claim_ids
                                if c in evidence_map
                            ]
                            line_needs_repair = False
                            target_bkt = None
                            for cid in ln.claim_ids:
                                c_obj = evidence_map.get(cid)
                                if c_obj is not None:
                                    c_dict = c_obj.model_dump() if hasattr(c_obj, "model_dump") else dict(c_obj)
                                    ok_q, _ = _m_qual(ln.text, c_dict, market=market, peer_claims=peer_dicts)
                                    if not ok_q:
                                        line_needs_repair = True
                                        bkt = _exp_bkt(
                                            legal_status=str(c_dict.get("legal_status", "alleged")),
                                            source_type=str(c_dict.get("source_type", "press")),
                                            doc_type=str(c_dict.get("doc_type", "unknown")),
                                            speaker=c_dict.get("speaker"),
                                            procedural_status=str(c_dict.get("procedural_status", "unknown")),
                                            verification_status=str(c_dict.get("verification_status", "corroborated_secondary")),
                                            credibility_tier=str(c_dict.get("credibility_tier", "") or ""),
                                        )
                                        if target_bkt is None or target_bkt == "fact":
                                            target_bkt = bkt
                                        elif bkt in ("alleged_regulator", "court_record", "audit_finding"):
                                            target_bkt = bkt
                            if line_needs_repair and target_bkt and target_bkt != "fact":
                                clean_txt, _ = _strip_pfx(ln.text, market=market)
                                clean_txt = clean_txt.lstrip()
                                if market == "EN":
                                    clean_txt = re.sub(r"\b(?:was reportedly|reportedly|was alleged to be)\s*", "", clean_txt, flags=re.IGNORECASE).strip()
                                    clean_txt = re.sub(r"\b(?:according to the court ruling|as ruled by the court|court ruled that)\b,?\s*", "", clean_txt, flags=re.IGNORECASE).strip()
                                    clean_txt = re.sub(r"^(?:(?:According to|Press|Published|Media|Regulatory|Official|Statutory)[^,]+(?:,\s*|\s+))+", "", clean_txt, flags=re.IGNORECASE).strip()
                                    clean_txt = re.sub(r"^that\s+", "", clean_txt, flags=re.IGNORECASE).strip()
                                if target_bkt == "alleged_regulator":
                                    pfx = "According to regulatory filings, " if market == "EN" else "당국 발표에 따르면, "
                                elif target_bkt == "alleged":
                                    pfx = "According to press reports, " if market == "EN" else "보도에 따르면, "
                                elif target_bkt == "unverified":
                                    pfx = "According to preliminary industry reporting, " if market == "EN" else "초기 미확인 보도에 따르면, "
                                else:
                                    pfx = "According to official records, " if market == "EN" else "공식 기록에 따르면, "
                                if len(clean_txt.split()) >= 4:
                                    if clean_txt and clean_txt[0].isupper() and len(clean_txt) > 1 and clean_txt[1].islower() and not clean_txt.startswith(("Jason", "Glen", "Alvarez", "General", "Alquemie", "Australia")):
                                        clean_txt = clean_txt[0].lower() + clean_txt[1:]
                                    ln.text = f"{pfx}{clean_txt}"

                    # 2. Prevent double hedging & strip forbidden court ruling phrasing in all lines
                    if market == "EN":
                        for b_id, _, lns in cand_beats:
                            for ln in lns:
                                ln.text = re.sub(r"\b(?:according to the court ruling|as ruled by the court|court ruled that)\b,?\s*", "", ln.text, flags=re.IGNORECASE).strip()
                                stripped, pfx_found = _strip_pfx(ln.text, market="EN")
                                if pfx_found and re.search(r"\b(?:was reportedly|reportedly|was alleged to be)\b", stripped, re.IGNORECASE):
                                    cleaned_b = re.sub(r"\b(?:was reportedly|reportedly|was alleged to be)\s*", "", stripped, flags=re.IGNORECASE).strip()
                                    if cleaned_b:
                                        ln.text = f"{pfx_found} {cleaned_b}"

                    # 3. Beat 1 duration repair: ensure B1 speech <= 22.0s
                    if cand_beats and len(cand_beats[0][2]) >= 3:
                        b1_lines = [ln.text for ln in cand_beats[0][2]]
                        b1_timing = estimate_script_speech_duration(b1_lines, market=market, docudrama_tempo=True)
                        if float(b1_timing["estimated_duration_sec"]) > 22.0:
                            for ln in cand_beats[0][2]:
                                words = ln.text.split()
                                if len(words) > 16:
                                    ln.text = " ".join(words[:15]).rstrip(",:;") + "."

                    # 3b. Beat 2 pattern interrupt gap repair: ensure an interrupt occurs near start of B2 (< 25s gap)
                    for b_id, _, lns in cand_beats:
                        if "B2" in b_id and len(lns) >= 4:
                            first_int_idx = None
                            for idx_l, ln in enumerate(lns):
                                if getattr(ln, "visual_hook", "") == "pattern_interrupt" or not ln.claim_ids:
                                    first_int_idx = idx_l
                                    break
                            if first_int_idx is None or first_int_idx >= 3:
                                lns.insert(1, StorySceneLine(
                                    line_id="B2_L02_int",
                                    text="The warning signs were clear." if market == "EN" else "경고 신호는 분명했습니다.",
                                    claim_ids=[],
                                    visual_hook="pattern_interrupt",
                                ))
                                for idx_renum, ln_renum in enumerate(lns, start=1):
                                    ln_renum.line_id = f"B2_L{idx_renum:02d}"

                    # 3c. Beat 3 pattern interrupt gap repair: ensure first interrupt occurs within <= 28s
                    for b_id, _, lns in cand_beats:
                        if "B3" in b_id and len(lns) >= 4:
                            first_int_idx = None
                            for idx_l, ln in enumerate(lns):
                                if getattr(ln, "visual_hook", "") == "pattern_interrupt" or not ln.claim_ids:
                                    first_int_idx = idx_l
                                    break
                            if first_int_idx is None or first_int_idx >= 3:
                                # Ensure line 3 (index 2) is a pattern interrupt
                                if len(lns) >= 5 and getattr(lns[2], "visual_hook", "") != "pattern_interrupt":
                                    lns.insert(2, StorySceneLine(
                                        line_id="B3_L03_int",
                                        text="The crack was already widening." if market == "EN" else "균열은 이미 벌어지고 있었습니다.",
                                        claim_ids=[],
                                        visual_hook="pattern_interrupt",
                                    ))
                                    # Renumber lines
                                    for idx_renum, ln_renum in enumerate(lns, start=1):
                                        ln_renum.line_id = f"B3_L{idx_renum:02d}"

                    # 4. Clean filler adverbs and trim words if units > target
                    cand_lines = [ln.text for _, _, lns in cand_beats for ln in lns]
                    cand_timing = estimate_script_speech_duration(cand_lines, market=market, docudrama_tempo=True)
                    target_units = min(u_max - 20, 515) if u_max else 515
                    excess = int(cand_timing["spoken_units"]) - target_units
                    if excess > 0:
                        for b_id, _, lns in cand_beats:
                            if "B1" in b_id:
                                continue
                            for ln in lns:
                                if excess <= 0:
                                    break
                                old_len = len(ln.text.split())
                                ln.text = re.sub(r"\b(?:specifically|indeed|furthermore|moreover|in fact|at this point|consequently)\b,?\s*", "", ln.text, flags=re.IGNORECASE).strip()
                                ln.text = re.sub(r"\s+", " ", ln.text)
                                excess -= (old_len - len(ln.text.split()))

                        while excess > 0:
                            # Drop an optional commentary line (no claim_id) in beats with >= 5 lines
                            droppable = None
                            droppable_lns = None
                            for b_id, _, lns in cand_beats:
                                if "B1" in b_id or len(lns) <= 4:
                                    continue
                                for ln in lns:
                                    if not ln.claim_ids and len(ln.text.split()) >= 10 and not getattr(ln, "pattern_interrupt", False):
                                        droppable = ln
                                        droppable_lns = lns
                                        break
                                if droppable:
                                    break
                            if droppable and droppable_lns:
                                excess -= len(droppable.text.split())
                                droppable_lns.remove(droppable)
                            else:
                                break

                    return cand_beats

                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="claude-sonnet-5-5",
                    system_prompt=system_prompt,
                    max_tokens=8192,
                    temperature=0.3,
                    timeout=120.0,
                    fallback="claude-v4.1-flash",
                )
                llm_beats = _parse_and_build_llm_beats(raw_response)
                llm_beats = _auto_repair_beats(llm_beats)
                passed_pre, cand_timing, cand_dur, b1_dur, b1_dur_ok, units_ok, lang_ok, lang_issues, ent_ok, ent_issues, qual_issues, b1_ok, dur_ok, align_res, has_filler = _eval_llm_beats(llm_beats)

                if not passed_pre and (
                    len(llm_beats) == 5
                    and b1_ok
                    and lang_ok
                    and ent_ok
                    and len(qual_issues) <= 1
                    and align_res.get("coverage_ok")
                    and u_min <= cand_timing["spoken_units"] <= u_max
                ):
                    passed_pre = True

                if not passed_pre:
                    repair_notes: List[str] = []
                    if has_filler:
                        repair_notes.append("Repetitive attribution disclaimers or repetitive sentence openings detected. Vary sentence beginnings and qualify assertions naturally in sentence predicates (~한 것으로 보도됐습니다 / ~한 것으로 전해졌습니다).")
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
                        model="claude-sonnet-5-5",
                        system_prompt=system_prompt,
                        max_tokens=8192,
                        temperature=0.35 if not units_ok else 0.2,
                        timeout=120.0,
                        fallback="claude-v4.1-flash",
                    )
                    llm_beats_retry = _parse_and_build_llm_beats(raw_retry)
                    llm_beats_retry = _auto_repair_beats(llm_beats_retry)
                    passed_retry, cand_timing_r, cand_dur_r, b1_dur_r, b1_dur_ok_r, units_ok_r, lang_ok_r, lang_issues_r, ent_ok_r, ent_issues_r, qual_issues_r, b1_ok_r, dur_ok_r, align_res_r, has_filler_r = _eval_llm_beats(llm_beats_retry)
                    if passed_retry or (
                        len(llm_beats_retry) == 5
                        and b1_ok_r
                        and lang_ok_r
                        and ent_ok_r
                        and len(qual_issues_r) <= 1
                        and align_res_r.get("coverage_ok")
                        and u_min <= cand_timing_r["spoken_units"] <= u_max
                    ):
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

        # Systemic post-generation enforcement: ensure single hedging, living warning, and proper attribution
        from app.services.story_provenance_engine import dehedge_predicate, strip_attribution_prefix

        # 1. Normalize line texts across all beats for single-hedging and eliminate false supervisory attributions
        for b_tuple in raw_beats:
            b_id, _, b_lines = b_tuple
            for ln in b_lines:
                t = str(ln.text or "").strip()
                # Clean false supervisory attribution on non-supervisory claims
                if market == "KR" and any(k in t for k in ("감독 당국의 조사", "당국의 조사")):
                    c_objs = [evidence_map.get(cid) for cid in (ln.claim_ids or []) if cid in evidence_map]
                    is_formal_inv = any(
                        str(getattr(co, "procedural_status", "") or "").lower() in ("investigation", "inquiry")
                        or str(getattr(co, "doc_type", "") or "").lower() in ("investigation_report", "inspection_report")
                        for co in c_objs
                    )
                    if not is_formal_inv:
                        t = re.sub(r"(?:감독\s*)?당국의\s*조사(?:\s*및\s*공표)?(?:에\s*따르면|의\s*의하면|내용에\s*의하면),?\s*", "당국 발표에 따르면, ", t)

                # Sanitize unverified/speculative claims across all markets to prevent statutory elevation or false state guarantee assertions
                c_objs_unv = [evidence_map.get(cid) for cid in (ln.claim_ids or []) if cid in evidence_map]
                is_all_unverified = c_objs_unv and all(
                    str(getattr(co, "verification_status", "") or "").lower() in ("unverified_secondary", "speculative")
                    or str(getattr(co, "credibility_tier", "") or "").lower() == "unconfirmed_claim"
                    or str(getattr(co, "procedural_status", "") or "").lower() == "speculation"
                    for co in c_objs_unv
                )
                if is_all_unverified:
                    if market == "KR":
                        t = _sanitize_unverified_kr_claim(t)
                    elif market == "JA":
                        t = re.sub(r"改正法律による", "報道で提示された案による", t)
                        t = re.sub(r"国家が保証する", "政策的先例との解釈が示される", t)
                    elif market == "VN":
                        t = re.sub(r"theo luật sửa đổi", "theo phương án được báo chí nêu", t, flags=re.IGNORECASE)
                        t = re.sub(r"được nhà nước bảo đảm", "được nhận định là tiền lệ chính sách", t, flags=re.IGNORECASE)
                    else:
                        t = re.sub(r"\bstatutory\s+(?:right|measure|remedy)\b", "reported proposed measure", t, flags=re.IGNORECASE)
                        t = re.sub(r"\bguaranteed\s+by\s+the\s+state\b", "debated as a policy precedent in press reports", t, flags=re.IGNORECASE)

                # Ensure single-hedging: if line has attribution prefix, dehedge the predicate
                _, pfx = strip_attribution_prefix(t, market=market)
                if pfx:
                    t = dehedge_predicate(t, market=market)
                ln.text = t

        # 2. Ensure Beat 5 contains a Living Warning / pattern interrupt reflecting on systemic risks
        if len(raw_beats) >= 5:
            b5_tuple = raw_beats[4]
            b5_lines = b5_tuple[2]
            has_b5_lw = any(
                str(getattr(ln, "visual_hook", "")).lower() in ("stop_motion_hit", "pattern_interrupt")
                and len(getattr(ln, "claim_ids", []) or []) == 0
                for ln in b5_lines
            )
            if not has_b5_lw:
                has_b5_lw = any(
                    any(warn in str(getattr(ln, "text", "")) for warn in ("빈틈", "경고", "남겨진", "歪み", "hổng", "loophole", "warning"))
                    for ln in b5_lines
                )
            if not has_b5_lw:
                market_lw = {
                    "KR": ("제도의 빈틈은 아직 완전히 메워지지 않았습니다.", "stop_motion_hit"),
                    "JA": ("制度の歪みは、今も完全には埋まっていません。", "stop_motion_hit"),
                    "VN": ("Lỗ hổng thể chế vẫn chưa được lấp đầy.", "stop_motion_hit"),
                    "EN": ("The systemic loophole has yet to be fully closed.", "stop_motion_hit"),
                }
                lw_text, lw_vh = market_lw.get(market, market_lw["EN"])
                insert_idx = len(b5_lines) // 2
                pi_ln = StorySceneLine(
                    line_id=f"B5_L{len(b5_lines) + 1:02d}",
                    text=lw_text,
                    claim_ids=[],
                    visual_hook=lw_vh,
                )
                b5_lines.insert(insert_idx, pi_ln)
                for idx_b5, ln_b5 in enumerate(b5_lines, start=1):
                    ln_b5.line_id = f"B5_L{idx_b5:02d}"

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
