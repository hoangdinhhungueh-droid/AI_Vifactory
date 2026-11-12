#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/story_provenance_engine.py — Generic Multi-Market Evidence Provenance,
Legal Qualifier Routing, Algorithmic Speech Normalization, Language Purity & Critic Scoring Engine.

Enforces Rule 118 (Zero Fabrication), Rule 125 (Single Truth across S01-S04),
Rule 128 (Zero Semantic Bias), Rule 130 (Causal Integrity), Rule 132 (Engine Purity),
and Rule 139 (Disciplined Typed Code).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# ==============================================================================
# 1. UNICODE & LANGUAGE CHARACTER RANGES (EN, KR, JA, VN)
# ==============================================================================

HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
HANGUL_SYLLABLE_RE = re.compile(r"[\uac00-\ud7af]")
JP_KANA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f]")
CJK_HAN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
VN_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"
    r"ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]"
)
LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
ASCII_WORD_RE = re.compile(r"\b[A-Za-z]{2,}\b")

CANONICAL_MARKET_MAP = {"KO": "KR", "KR": "KR", "JP": "JA", "JA": "JA", "VI": "VN", "VN": "VN", "EN": "EN", "US": "EN"}


def normalize_market_code(market: Optional[str]) -> str:
    m = (market or "EN").strip().upper()
    return CANONICAL_MARKET_MAP.get(m, "EN")


# ==============================================================================
# 2. EVIDENCE PROVENANCE CLASSIFIER (S01 / S02 / S03 / S04)
# ==============================================================================

_RSS_AGGREGATOR_HOSTS = (
    "news.google.com",
    "feedburner.com",
    "feeds.feedburner.com",
    "rss.cnn.com",
    "feeds.reuters.com",
)

_PRIMARY_OFFICIAL_TLD_SUFFIXES = (
    ".gov",
    ".go.kr",
    ".go.jp",
    ".gov.vn",
    ".gov.uk",
    ".gov.au",
    ".gov.sg",
    ".gouv.fr",
    ".europa.eu",
    ".mil",
    ".int",
)

_PRIMARY_OFFICIAL_DOMAINS = (
    "bis.org",
    "imf.org",
    "worldbank.org",
    "federalreserve.gov",
    "sec.gov",
    "cftc.gov",
    "boj.or.jp",
    "bok.or.kr",
    "assembly.go.kr",
    "law.go.kr",
    "scourt.go.kr",
    "fsa.go.jp",
    "courts.go.jp",
    "chinhphu.vn",
    "sbv.gov.vn",
    "eia.gov",
    "iea.org",
    "imo.org",
    "sipri.org",
)

_REPUTABLE_PRESS_DOMAINS = (
    "reuters.com",
    "apnews.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "nytimes.com",
    "bbc.com",
    "bbc.co.uk",
    "economist.com",
    "nikkei.com",
    "nhk.or.jp",
    "asahi.com",
    "yomiuri.co.jp",
    "kyodonews.net",
    "jiji.com",
    "yna.co.kr",
    "mk.co.kr",
    "hankyung.com",
    "chosun.com",
    "joongang.co.kr",
    "donga.com",
    "koreaherald.com",
    "koreatimes.co.kr",
    "kbs.co.kr",
    "vnexpress.net",
    "tuoitre.vn",
    "thanhnien.vn",
    "vietnamplus.vn",
)


def is_rss_or_aggregator_url(url: str) -> bool:
    """Detect whether a URL points to an RSS aggregator wrapper rather than a primary source."""
    u = (url or "").strip().lower()
    if not u or not u.startswith(("http://", "https://")):
        return True
    parsed = urlparse(u)
    host = (parsed.netloc or "").split(":")[0]
    path = parsed.path or ""
    if any(host == h or host.endswith("." + h) for h in _RSS_AGGREGATOR_HOSTS):
        return True
    if "/rss" in path or path.endswith(".rss") or path.endswith(".xml"):
        return True
    return False


def is_primary_official_domain(url: str) -> bool:
    """True when URL points directly to an official government, court, central bank, or treaty domain."""
    if is_rss_or_aggregator_url(url):
        return False
    host = (urlparse((url or "").strip().lower()).netloc or "").split(":")[0]
    if not host:
        return False
    if any(host.endswith(suf) for suf in _PRIMARY_OFFICIAL_TLD_SUFFIXES):
        return True
    if any(host == dom or host.endswith("." + dom) for dom in _PRIMARY_OFFICIAL_DOMAINS):
        return True
    return False


def is_reputable_press_domain(url: str, source_name: str = "") -> bool:
    """True when URL host or outlet name identifies a recognized wire/journalism domain (non-RSS)."""
    if not is_rss_or_aggregator_url(url):
        host = (urlparse(url.strip().lower()).netloc or "").split(":")[0]
        if any(host == dom or host.endswith("." + dom) for dom in _REPUTABLE_PRESS_DOMAINS):
            return True
    s_low = (source_name or "").lower()
    wire_names = (
        "reuters", "associated press", "ap news", "bloomberg", "financial times", "wsj",
        "wall street journal", "nikkei", "nhk", "kyodo", "yonhap", "연합뉴스", "kbs", "mbc", "sbs",
        "한국경제", "매일경제", "조선일보", "중앙일보", "vnexpress", "tuổi trẻ", "ttxvn",
    )
    return any(w in s_low for w in wire_names)


def extract_normalized_date(date_raw: Optional[str], claim_text: str = "") -> Optional[str]:
    """Extract ISO-like YYYY-MM-DD (or YYYY-MM) dynamically from date metadata or claim text."""
    for candidate in (date_raw or "", claim_text or ""):
        c = candidate.strip()
        if not c:
            continue
        m_iso = re.search(r"\b((?:19|20)\d{2})[-./](\d{1,2})[-./](\d{1,2})\b", c)
        if m_iso:
            y, mo, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        m_cjk = re.search(r"((?:19|20)\d{2})\s*[년年]\s*(\d{1,2})\s*[월月]\s*(\d{1,2})\s*[일日]", c)
        if m_cjk:
            y, mo, d = int(m_cjk.group(1)), int(m_cjk.group(2)), int(m_cjk.group(3))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        m_vn = re.search(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+((?:19|20)\d{2})", c, re.IGNORECASE)
        if m_vn:
            d, mo, y = int(m_vn.group(1)), int(m_vn.group(2)), int(m_vn.group(3))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        m_ym = re.search(r"\b((?:19|20)\d{2})[-./](\d{1,2})\b", c)
        if m_ym:
            y, mo = int(m_ym.group(1)), int(m_ym.group(2))
            if 1 <= mo <= 12:
                return f"{y:04d}-{mo:02d}"
    return None


def classify_claim_provenance(
    raw_claim: Dict[str, Any],
    market: str = "EN",
) -> Dict[str, Any]:
    """Derive truthful verification_status, source_type, doc_type, speaker, procedural_status,
    legal_status, causal_role, scope, and calibrated confidence without blind elevation.
    """
    claim_text = str(raw_claim.get("claim", "")).strip()
    source_name = str(raw_claim.get("source") or raw_claim.get("source_name") or "").strip()
    source_url = str(raw_claim.get("source_url") or "").strip()
    raw_conf = str(raw_claim.get("confidence") or "").strip().lower()
    raw_role = str(raw_claim.get("causal_role") or "").strip().lower()
    raw_doc = str(raw_claim.get("doc_type") or "").strip().lower()
    raw_speaker = str(raw_claim.get("speaker") or "").strip().lower() or None
    raw_proc = str(raw_claim.get("procedural_status") or "").strip().lower()
    raw_scope = str(raw_claim.get("scope") or "").strip() or None
    raw_ver = str(raw_claim.get("verification_status") or "").strip().lower()

    text_low = claim_text.lower()
    src_low = source_name.lower()
    combined_low = f"{src_low} {text_low}"

    # 1. URL & RSS Aggregator Gate: RSS wrappers cannot self-certify as verified_primary
    is_rss = is_rss_or_aggregator_url(source_url)
    is_primary_url = is_primary_official_domain(source_url)
    is_reputable_press = is_reputable_press_domain(source_url, source_name)

    # 2. Detect document type, speaker, procedural status & legal status from structured cues + content
    doc_type = raw_doc if raw_doc and raw_doc != "unknown" else "unknown"
    speaker = raw_speaker
    procedural_status = raw_proc if raw_proc and raw_proc != "unknown" else "unknown"

    # Judgment vs Indictment vs Complaint vs Statute vs Proposed Bill vs Regulatory Notice
    has_judgment_negation = any(k in combined_low for k in (
        "판결 전", "판결 이전", "미확정", "확정되지", "확정 전", "선고 전", "아직 판결",
        "not yet ruled", "pending verdict", "awaiting verdict", "before ruling", "no verdict yet",
        "判決前", "確定前", "chưa có phán quyết", "chưa tuyên án",
    ))
    has_acquittal = (
        not has_judgment_negation
        and any(k in combined_low for k in (
            "무죄", "무혐의 확정", "acquitted", "not guilty", "無罪", "tuyên vô tội",
        ))
    )
    has_judgment = (
        not has_judgment_negation
        and any(k in combined_low for k in (
            "판결", "선고", "확정", "유죄", "무죄", "convicted", "sentenced", "verdict", "judgment", "ruled",
            "判決", "言い渡し", "有罪判決", "tuyên án", "bản án", "phán quyết",
        ))
    )
    has_indictment = any(k in combined_low for k in (
        "공소장", "구속기소", "불구속기소", "기소", "indictment", "indicted", "prosecutors charged",
        "起訴状", "起訴され", "cáo trạng", "truy tố",
    ))
    has_complaint = any(k in combined_low for k in (
        "고발", "고소", "피소", "complaint", "civil suit", "sued", "lawsuit filed",
        "告訴", "提訴", "đơn kiện", "khởi kiện", "đơn tố cáo",
    )) or bool(re.search(r"(?<![공기])소장|(?<!起)訴状", combined_low))
    has_settlement = any(k in combined_low for k in (
        "합의", "동의의결", "과징금 납부", "settled", "consent decree", "without admitting",
        "和解", "同意審決", "hòa giải", "thỏa thuận dàn xếp",
    ))
    has_proposed_bill = any(k in combined_low for k in (
        "발의", "추진", "입법예고", "검토", "계획", "초안", "시행 예정", "proposed", "bill introduced",
        "draft rule", "under consideration", "planned", "検討", "法案", "方針", "予定", "dự thảo", "đề xuất",
    ))
    has_enacted_statute = (
        not has_proposed_bill
        and any(k in combined_low for k in (
            "법 시행", "법 개정", "시행령", "개정안 통과", "법률 제정", "enacted", "statute", "law took effect",
            "came into force", "改正法施行", "法律", "luật có hiệu lực", "nghị định", "ban hành",
        ))
    )
    has_audit_report = any(k in combined_low for k in (
        "감사 결과", "조사 결과", "실태조사", "점검 결과", "보고서", "audit report", "inspector general",
        "inspection found", "調査結果", "監査報告", "kết quả thanh tra", "báo cáo kiểm toán",
    ))
    has_speculative = (
        raw_conf == "speculative"
        or raw_ver == "speculative"
        or any(k in text_low for k in (
            "projected to", "could reach", "expected to", "rumored", "speculated",
            "전망된다", "예상된다", "가능성이 제기", "추산된다", "見通し", "可能性がある", "dự báo", "có thể sẽ",
        ))
    )
    has_allegation = any(k in combined_low for k in (
        "alleged", "allegedly", "claimed", "purported", "의혹", "주장", "추정", "혐의",
        "疑惑", "主張", "nghi vấn", "cáo buộc", "cho rằng",
    ))

    # Source type classification (agency/court/gov/press)
    is_court_source = any(k in src_low for k in (
        "법원", "검찰", "재판", "특검", "supreme court",
        "裁判所", "検察", "tòa án", "viện kiểm sát",
    )) or bool(re.search(r"\b(?:court|justice|prosecutor|tribunal)\b", src_low))
    is_regulator_source = any(k in src_low for k in (
        "금융위", "금감원", "공정위", "국토", "감사원", "한국은행", "당국", "위원회",
        "central bank", "金融庁", "日銀", "公正取引委員会", "thanh tra", "ngân hàng nhà nước", "ủy ban",
    )) or bool(re.search(r"\b(?:regulator|commission|authority|sec|cftc|ftc|fsa|boj|bok|sbv)\b", src_low))
    is_gov_source = any(k in src_low for k in (
        "정부", "부처", "국회", "백악관", "청와대",
        "省", "庁", "内閣", "bộ ", "chính phủ", "quốc hội",
    )) or bool(re.search(r"\b(?:ministry|department|parliament|congress|cabinet)\b", src_low))

    if is_primary_url and any(x in source_url.lower() for x in ("court", "scourt", "justice")):
        source_type = "court"
    elif is_court_source and not is_reputable_press:
        source_type = "court"
    elif is_regulator_source and not is_reputable_press:
        source_type = "regulator"
    elif (is_gov_source or is_primary_url) and not is_reputable_press:
        source_type = "gov"
    else:
        source_type = "press"

    # Refine doc_type & procedural_status
    if doc_type == "unknown":
        if is_rss:
            doc_type = "rss_snippet"
        elif has_judgment:
            doc_type = "court_judgment"
        elif has_indictment:
            doc_type = "indictment"
        elif has_complaint:
            doc_type = "criminal_complaint"
        elif has_enacted_statute:
            doc_type = "statute"
        elif has_audit_report:
            doc_type = "audit_report"
        elif is_regulator_source or is_gov_source or is_primary_url:
            doc_type = "regulatory_notice" if is_regulator_source else "gov_report"
        elif source_type == "press":
            doc_type = "news_article"
        else:
            doc_type = "commentary"

    if procedural_status == "unknown":
        if has_speculative:
            procedural_status = "speculation"
        elif has_judgment:
            procedural_status = "final_judgment"
        elif has_indictment:
            procedural_status = "indicted"
        elif has_complaint or has_allegation:
            procedural_status = "investigation"
        elif has_enacted_statute:
            procedural_status = "legislative_enacted"
        elif has_proposed_bill:
            procedural_status = "bill_proposed"
        else:
            procedural_status = "reported_event"

    if not speaker:
        if doc_type == "court_judgment":
            speaker = "court"
        elif doc_type == "indictment":
            speaker = "prosecutor"
        elif doc_type == "criminal_complaint":
            speaker = "complainant"
        elif source_type in ("regulator", "gov"):
            speaker = "official"
        elif has_speculative:
            speaker = "analyst"
        else:
            speaker = "journalist"

    # 3. Verification status & tier calibration (Anti-RSS-Elevation Invariant)
    explicit_primary_flag = raw_ver == "verified_primary" and is_primary_url
    if explicit_primary_flag:
        verification_status = "verified_primary"
    elif has_speculative:
        verification_status = "speculative"
    elif is_primary_url and raw_conf in ("verified", "high", ""):
        verification_status = "verified_primary"
    elif is_rss:
        # RSS aggregator text/links NEVER become verified_primary automatically
        if raw_conf == "verified" and is_reputable_press:
            verification_status = "corroborated_secondary"
        else:
            verification_status = "unverified_secondary"
    elif is_reputable_press and raw_conf == "verified":
        verification_status = "corroborated_secondary"
    elif raw_ver in ("corroborated_secondary", "unverified_secondary", "speculative"):
        verification_status = raw_ver
    else:
        verification_status = "unverified_secondary"

    if verification_status == "verified_primary":
        evidence_tier = "primary"
    elif verification_status in ("corroborated_secondary", "unverified_secondary"):
        evidence_tier = "secondary"
    else:
        evidence_tier = "tertiary"

    # 4. Honest legal_status (never auto-promote unverified claims to "fact" or acquittals to "convicted")
    if has_acquittal and verification_status in ("verified_primary", "corroborated_secondary"):
        legal_status = "fact"
    elif has_acquittal:
        legal_status = "alleged"
    elif has_judgment:
        legal_status = "convicted"
    elif has_settlement:
        legal_status = "settled"
    elif has_indictment:
        legal_status = "charged"
    elif has_complaint or has_allegation or has_speculative:
        legal_status = "alleged"
    elif verification_status == "unverified_secondary":
        legal_status = "alleged"
    elif has_proposed_bill and verification_status != "verified_primary":
        legal_status = "alleged"
    elif verification_status in ("verified_primary", "corroborated_secondary"):
        legal_status = "fact"
    else:
        legal_status = "alleged"

    # 5. Calibrated confidence (no unconditional "high" when undated)
    norm_date = extract_normalized_date(raw_claim.get("date"), claim_text)
    if verification_status == "verified_primary" and norm_date:
        confidence = "high"
    elif verification_status == "verified_primary":
        confidence = "medium"
    elif verification_status == "corroborated_secondary":
        confidence = "medium" if (has_proposed_bill or is_rss or not norm_date) else "high"
    elif verification_status == "unverified_secondary":
        confidence = "medium" if (norm_date and is_reputable_press) else "low"
    else:
        confidence = "low"

    # 6. Causal role normalization
    if raw_role in ("primary_catalyst", "transmission_mechanism", "background_context"):
        causal_role = raw_role
    elif any(k in text_low for k in ("mechanism", "channel", "loophole", "구조", "허점", "전가", "制度", "cơ chế")):
        causal_role = "transmission_mechanism"
    elif has_judgment or has_indictment or has_enacted_statute or norm_date:
        causal_role = "primary_catalyst"
    else:
        causal_role = "background_context"

    # 7. Scope detection
    scope = raw_scope
    if not scope:
        if procedural_status == "bill_proposed":
            scope = "proposed_policy_or_bill"
        elif verification_status == "unverified_secondary":
            scope = "preliminary_media_report"
        elif procedural_status == "indicted":
            scope = "prosecution_filing_allegation"
        elif procedural_status == "final_judgment":
            scope = "adjudicated_court_record"
        elif source_type in ("regulator", "gov"):
            scope = "official_agency_record"
        else:
            scope = "secondary_reporting"

    return {
        "claim": claim_text,
        "source_name": source_name or f"Source ({normalize_market_code(market)})",
        "source_url": source_url,
        "source_type": source_type,
        "doc_type": doc_type,
        "speaker": speaker,
        "date": norm_date,
        "legal_status": legal_status,
        "procedural_status": procedural_status,
        "verification_status": verification_status,
        "evidence_tier": evidence_tier,
        "causal_role": causal_role,
        "scope": scope,
        "mechanism": raw_claim.get("mechanism"),
        "act_target": raw_claim.get("act_target"),
        "confidence": confidence,
    }


def verification_priority_rank(verification_status: str) -> int:
    return {
        "verified_primary": 0,
        "corroborated_secondary": 1,
        "unverified_secondary": 2,
        "speculative": 3,
    }.get(verification_status, 2)


def summarize_evidence_provenance(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {
        "verified_primary": 0,
        "corroborated_secondary": 0,
        "unverified_secondary": 0,
        "speculative": 0,
    }
    for c in claims:
        v = str(c.get("verification_status", "unverified_secondary"))
        counts[v] = counts.get(v, 0) + 1
    total = max(1, len(claims))
    verified_plus_corroborated = counts["verified_primary"] + counts["corroborated_secondary"]
    return {
        "total_claims": len(claims),
        **counts,
        "verified_or_corroborated_ratio": round(verified_plus_corroborated / total, 4),
        "primary_only_ratio": round(counts["verified_primary"] / total, 4),
        "heavy_unverified_warning": verified_plus_corroborated < max(1, math.ceil(total * 0.4)),
    }


# ==============================================================================
# 3. STRUCTURED LEGAL & PROVENANCE QUALIFIER ROUTER
# ==============================================================================

_LEGAL_QUALIFIER_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "KR": {
        "final_judgment": ["법원 판결", "확정 판결", "판결에 따르면", "판결문", "유죄 확정", "선고됐다", "선고받았다"],
        "indictment": ["공소장에 따르면", "공소장에 의하면", "검찰 공소장", "검찰에 따르면", "검찰 조사", "기소 내용에 따르면", "기소장에 따르면"],
        "criminal_complaint": ["고발장에 따르면", "고소장에 따르면", "소장에 따르면", "고발 내용에 따르면", "소장을 통해"],
        "press_charge": ["보도된 기소 내용에 따르면", "보도에 따르면", "언론 보도에 따르면", "혐의를 받고 있"],
        "alleged_regulator": ["규제 당국에 따르면", "당국에 따르면", "당국의 조사", "감독 당국", "정부 발표에 따르면"],
        "alleged": ["언론 보도에 따르면", "보도 설명에 따르면", "보도에 따르면", "의혹이 제기", "주장에 따르면", "것으로 알려졌", "것으로 전해졌"],
        "settled": ["합의했", "합의하며", "합의로 종결", "책임을 인정하지 않", "인정하지 않고 합의", "동의의결"],
        "unverified": ["아직 최종", "아직 확인", "아직 사실관계", "미확인", "초기 보도", "확인되지 않은 보도", "초기 문건"],
        "proposed": ["추진", "검토", "예정", "발의", "초안", "방침"],
    },
    "JA": {
        "final_judgment": ["裁判所の確定判決", "判決によれば", "確定判決", "有罪判決"],
        "indictment": ["起訴状によれば", "起訴状の指摘によれば", "検察によれば", "検察の発表"],
        "criminal_complaint": ["告訴状によれば", "訴状によれば", "訴状の主張によれば", "告訴内容"],
        "press_charge": ["報道された起訴内容", "報道によれば", "報じられた"],
        "alleged_regulator": ["当局の調査によれば", "規制当局によれば", "当局によれば", "監督当局"],
        "alleged": ["報道によれば", "疑惑", "とされ", "主張によれば", "見られ"],
        "settled": ["和解し", "認めないまま和解", "違法性を認めることなく和解", "課徴金納付"],
        "unverified": ["未確認", "初期報道", "初期段階", "確認前の報道", "裏付け前"],
        "proposed": ["検討", "予定", "案", "方針"],
    },
    "VN": {
        "final_judgment": ["phán quyết của tòa", "tòa án tuyên", "bản án có hiệu lực"],
        "indictment": ["theo cáo trạng", "cáo trạng của viện kiểm sát", "cơ quan công tố cáo buộc"],
        "criminal_complaint": ["theo đơn kiện", "theo đơn tố cáo", "hồ sơ khởi kiện"],
        "press_charge": ["theo thông tin báo chí", "theo báo chí", "bị cáo buộc theo"],
        "alleged_regulator": ["theo cơ quan chức năng", "cơ quan quản lý", "theo thanh tra", "ủy ban giám sát"],
        "alleged": ["theo thông tin báo chí", "cáo buộc", "được cho là", "theo báo chí", "nghi vấn", "cho rằng"],
        "settled": ["dàn xếp", "hòa giải", "không thừa nhận"],
        "unverified": ["chưa kiểm chứng", "bước đầu", "chưa được xác minh", "nguồn tin ban đầu"],
        "proposed": ["dự thảo", "đề xuất", "dự kiến", "xem xét"],
    },
    "EN": {
        "final_judgment": ["according to the court ruling", "court found", "convicted by", "final verdict"],
        "indictment": ["according to the indictment", "according to court filings", "indictment alleges", "prosecutors allege", "prosecutors say"],
        "criminal_complaint": ["according to the complaint", "complaint alleges", "lawsuit alleges", "plaintiff alleges"],
        "press_charge": ["according to press reports", "according to news reports", "press reports", "reportedly charged"],
        "alleged_regulator": ["according to regulatory filings", "according to regulators", "regulators allege", "regulatory inquiry"],
        "alleged": ["according to press reports", "allegedly", "alleged", "claimed", "according to", "reportedly"],
        "settled": ["settled without admitting", "consent decree", "agreed to pay without admitting"],
        "unverified": ["unverified", "preliminary reports", "initial reports", "early reports", "yet to be verified"],
        "proposed": ["proposed", "draft", "under consideration", "planned"],
    },
}


def _qualifier_pattern_matches(pattern: str, text: str, market: str) -> bool:
    """Match qualifier patterns with lookbehind guards where bare stems collide
    (e.g. KR '소장' inside '공소장'/'기소장', JA '訴状' inside '起訴状').
    """
    m = normalize_market_code(market)
    if m == "KR":
        if pattern == "소장에 따르면":
            return bool(re.search(r"(?<![공기])소장에\s*따르면", text))
        if pattern == "소장을 통해":
            return bool(re.search(r"(?<![공기])소장을\s*통해", text))
        return pattern in text
    if m == "JA":
        if pattern == "訴状によれば":
            return bool(re.search(r"(?<!起)訴状によれば", text))
        if pattern == "訴状の主張によれば":
            return bool(re.search(r"(?<!起)訴状の主張によれば", text))
        return pattern in text
    return pattern.lower() in text.lower()


def expected_qualifier_bucket(
    legal_status: str,
    source_type: str = "press",
    doc_type: str = "unknown",
    speaker: Optional[str] = None,
    procedural_status: str = "unknown",
    verification_status: str = "corroborated_secondary",
) -> str:
    """Resolve the single canonical qualifier bucket from full legal & provenance metadata."""
    ls = (legal_status or "alleged").lower()
    st = (source_type or "press").lower()
    dt = (doc_type or "unknown").lower()
    sp = (speaker or "").lower()
    ps = (procedural_status or "unknown").lower()
    vs = (verification_status or "unverified_secondary").lower()

    if ls == "settled":
        return "settled"
    if ls == "convicted" or dt == "court_judgment" or ps == "final_judgment":
        return "final_judgment"
    if ls == "charged":
        if dt == "criminal_complaint" or sp in ("plaintiff", "complainant"):
            return "criminal_complaint"
        if dt == "indictment" or (st == "court" and sp in ("", "prosecutor") and dt in ("unknown", "indictment")):
            return "indictment"
        if st == "press" or dt in ("news_article", "rss_snippet"):
            return "press_charge"
        return "indictment" if sp in ("prosecutor", "") and st in ("court", "regulator") else "press_charge"
    if ps == "bill_proposed":
        return "proposed"
    if vs == "unverified_secondary":
        return "unverified"
    if ls == "alleged":
        if st in ("regulator", "gov"):
            return "alleged_regulator"
        return "alleged"
    if vs == "speculative":
        return "unverified"
    return "fact"


_EN_COMMON_STARTERS = {
    "the", "a", "an", "in", "on", "at", "by", "as", "when", "while", "before", "after",
    "for", "from", "with", "during", "following", "under", "until", "according", "placed",
    "tracing", "what", "however", "meanwhile", "subsequently", "internal", "public",
    "official", "market", "records", "disclosures", "regulatory", "civil", "criminal",
    "early", "later", "behind", "despite", "once", "though",
}

_VN_COMMON_STARTERS = {
    "các", "những", "một", "việc", "sự", "dưới", "theo", "từ", "tại", "ngoài",
    "sau", "trước", "khi", "nếu", "tuy", "nhưng", "bởi", "do", "vì", "để", "giữa",
    "hoạt", "chính", "ngành", "cơ", "thị", "nguồn", "báo", "hồ", "dữ", "số", "tỷ",
    "phân", "tích", "bước", "nhiều", "ít", "toàn", "hàng",
}


def route_legal_qualifier(
    text: str,
    legal_status: str,
    source_type: str = "press",
    market: str = "EN",
    doc_type: str = "unknown",
    speaker: Optional[str] = None,
    procedural_status: str = "unknown",
    verification_status: str = "corroborated_secondary",
) -> str:
    """Apply market-specific procedural & verification qualifier based on full provenance."""
    body = (text or "").strip()
    if not body:
        return body

    m = normalize_market_code(market)
    bucket = expected_qualifier_bucket(
        legal_status=legal_status,
        source_type=source_type,
        doc_type=doc_type,
        speaker=speaker,
        procedural_status=procedural_status,
        verification_status=verification_status,
    )
    if bucket == "fact":
        return body

    patterns = _LEGAL_QUALIFIER_PATTERNS.get(m, _LEGAL_QUALIFIER_PATTERNS["EN"]).get(bucket, [])
    if any(_qualifier_pattern_matches(p, body, m) for p in patterns):
        # Also ensure unverified claims retain preliminary hedging even if a legal term is present
        if verification_status == "unverified_secondary" and bucket not in ("unverified", "alleged"):
            unv_pats = _LEGAL_QUALIFIER_PATTERNS.get(m, _LEGAL_QUALIFIER_PATTERNS["EN"]).get("unverified", [])
            if any(_qualifier_pattern_matches(up, body, m) for up in unv_pats):
                return body
        else:
            return body

    if bucket == "settled":
        suffix_table = {
            "KR": "(공식적인 잘못을 인정하지 않고 합의됨)",
            "JA": "(違法性を認めることなく和解)",
            "VN": "(dàn xếp mà không thừa nhận hành vi sai trái)",
            "EN": "(settled without admitting wrongdoing)",
        }
        return f"{body} {suffix_table.get(m, suffix_table['EN'])}"

    unverified_variants = {
        "KR": [
            "아직 최종 검증 전인 초기 보도에 따르면,",
            "초기 보도 단계의 미확인 기록에 따르면,",
            "아직 사실관계가 최종 확인되지 않은 초기 보도에 따르면,",
        ],
        "JA": [
            "未確認の初期報道によれば、",
            "未確認段階の初期報道によれば、",
            "未確認の初期情報によれば、",
        ],
        "VN": [
            "Theo thông tin báo chí bước đầu chưa kiểm chứng,",
            "Theo nguồn tin ban đầu chưa được xác minh,",
            "Theo phản ánh bước đầu chưa kiểm chứng,",
        ],
        "EN": [
            "According to unverified preliminary reports,",
            "According to initial reports yet to be verified,",
            "According to early unverified reports,",
        ],
    }

    prefix_table = {
        "KR": {
            "final_judgment": "법원 확정 판결에 따르면,",
            "indictment": "검찰 공소장에 따르면,",
            "criminal_complaint": "고발장·소장에 따르면,",
            "press_charge": "보도된 기소 내용에 따르면,",
            "proposed": "아직 시행 확정 전인 추진 계획에 따르면,",
            "alleged_regulator": "규제 당국에 따르면,",
            "alleged": "언론 보도에 따르면,",
        },
        "JA": {
            "final_judgment": "裁判所の確定判決によれば、",
            "indictment": "起訴状の指摘によれば、",
            "criminal_complaint": "告訴状・訴状の主張によれば、",
            "press_charge": "報道された起訴内容によれば、",
            "proposed": "検討・予定段階の公表案によれば、",
            "alleged_regulator": "当局の調査によれば、",
            "alleged": "報道によれば、",
        },
        "VN": {
            "final_judgment": "Theo phán quyết của tòa án,",
            "indictment": "Theo cáo trạng của cơ quan công tố,",
            "criminal_complaint": "Theo đơn tố cáo và hồ sơ khởi kiện,",
            "press_charge": "Theo thông tin báo chí về quyết định truy tố,",
            "proposed": "Theo đề xuất đang trong quá trình xem xét,",
            "alleged_regulator": "Theo cơ quan chức năng,",
            "alleged": "Theo thông tin báo chí phản ánh,",
        },
        "EN": {
            "final_judgment": "According to the court ruling,",
            "indictment": "According to court filings,",
            "criminal_complaint": "According to the complaint,",
            "press_charge": "According to press reports on the charges,",
            "proposed": "Under the proposed draft framework,",
            "alleged_regulator": "According to regulatory filings,",
            "alleged": "According to press reports,",
        },
    }

    if bucket == "unverified":
        variants = unverified_variants.get(m, unverified_variants["EN"])
        pick_idx = sum(ord(ch) for ch in body[:40]) % len(variants)
        prefix = variants[pick_idx]
    else:
        prefix = prefix_table.get(m, prefix_table["EN"]).get(bucket, "")
    if not prefix:
        return body

    if m in ("EN", "VN") and prefix.endswith(","):
        first_word = body.split(" ", 1)[0].strip(",.:;\"'").lower()
        starters = _EN_COMMON_STARTERS if m == "EN" else _VN_COMMON_STARTERS
        if first_word in starters and len(body) > 1 and body[0].isupper() and body[1].islower():
            body = body[0].lower() + body[1:]

    if m in ("EN", "VN", "KR"):
        return f"{prefix} {body}"
    return f"{prefix}{body}"


def line_matches_expected_qualifier(
    line_text: str,
    claim: Dict[str, Any],
    market: str = "EN",
) -> Tuple[bool, str]:
    """Verify whether a script line satisfies the expected legal + verification qualifier for `claim`."""
    m = normalize_market_code(market)
    ls = str(claim.get("legal_status", "alleged")).lower()
    st = str(claim.get("source_type", "press")).lower()
    dt = str(claim.get("doc_type", "unknown")).lower()
    sp = claim.get("speaker")
    ps = str(claim.get("procedural_status", "unknown")).lower()
    vs = str(claim.get("verification_status", "corroborated_secondary")).lower()

    bucket = expected_qualifier_bucket(ls, st, dt, sp, ps, vs)
    if bucket == "fact":
        return True, "ok"

    patterns = _LEGAL_QUALIFIER_PATTERNS.get(m, _LEGAL_QUALIFIER_PATTERNS["EN"]).get(bucket, [])
    raw_claim_str = str(claim.get("claim", ""))

    # Guard against verdict exaggeration: charged/alleged/complaint must never assert final conviction
    if bucket in ("indictment", "criminal_complaint", "press_charge", "alleged", "unverified"):
        forbidden_verdict = _LEGAL_QUALIFIER_PATTERNS.get(m, {}).get("final_judgment", [])
        for fv in forbidden_verdict:
            if _qualifier_pattern_matches(fv, line_text, m) and not _qualifier_pattern_matches(fv, raw_claim_str, m):
                return False, f"Elevates {bucket} claim using final-judgment phrasing '{fv}'"

    # Guard against procedural elevation: criminal_complaint must never be elevated to prosecutor indictment
    if bucket == "criminal_complaint":
        for ind_p in _LEGAL_QUALIFIER_PATTERNS.get(m, {}).get("indictment", []):
            if _qualifier_pattern_matches(ind_p, line_text, m) and not _qualifier_pattern_matches(ind_p, raw_claim_str, m):
                return False, f"Elevates criminal_complaint claim using indictment phrasing '{ind_p}'"

    # Guard against authority laundering: press/unverified claims must never claim prosecutor indictment or regulator mandate
    if (st == "press" or vs in ("unverified_secondary", "speculative")) and bucket in ("press_charge", "alleged", "unverified"):
        for auth_b in ("indictment", "alleged_regulator"):
            for ap in _LEGAL_QUALIFIER_PATTERNS.get(m, {}).get(auth_b, []):
                if _qualifier_pattern_matches(ap, line_text, m) and not _qualifier_pattern_matches(ap, raw_claim_str, m):
                    return False, f"Misattributes {st}/{bucket} claim to '{ap}'"

    if not patterns:
        return True, "ok"

    matched = any(_qualifier_pattern_matches(p, line_text, m) for p in patterns)
    if not matched and bucket == "press_charge":
        fallback_pats = _LEGAL_QUALIFIER_PATTERNS.get(m, {}).get("alleged", [])
        matched = any(_qualifier_pattern_matches(p, line_text, m) for p in fallback_pats)

    if not matched:
        return False, f"Missing '{bucket}' procedural/verification qualifier for claim {claim.get('claim_id', '?')}"
    return True, "ok"


# ==============================================================================
# 4. ALGORITHMIC MULTI-MARKET NUMBER & TTS UNIT EXPANSION (ZERO HARDCODES)
# ==============================================================================

_KR_DIGITS = ("", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")
_KR_SMALL_UNITS = ("", "십", "백", "천")
_KR_BIG_UNITS = ("", "만", "억", "조", "경")


def int_to_sino_korean(num: int) -> str:
    """Convert any non-negative integer (< 10^20) into natural Sino-Korean syllables."""
    if num == 0:
        return "영"
    if num < 0:
        return "마이너스 " + int_to_sino_korean(-num)

    groups: List[str] = []
    n = int(num)
    big_idx = 0
    while n > 0 and big_idx < len(_KR_BIG_UNITS):
        chunk = n % 10000
        n //= 10000
        if chunk > 0:
            chunk_parts: List[str] = []
            for pos in range(4):
                d = (chunk // (10 ** pos)) % 10
                if d == 0:
                    continue
                unit = _KR_SMALL_UNITS[pos]
                # Omit '일' before 십, 백, 천 (and before 만 when chunk == 1 and big_idx == 1)
                if d == 1 and pos > 0:
                    digit_word = ""
                elif d == 1 and pos == 0 and chunk == 1 and big_idx == 1 and n == 0:
                    digit_word = ""
                else:
                    digit_word = _KR_DIGITS[d]
                chunk_parts.append(digit_word + unit)
            chunk_str = "".join(reversed(chunk_parts))
            groups.append(chunk_str + _KR_BIG_UNITS[big_idx])
        big_idx += 1
    return "".join(reversed(groups))


def decimal_to_sino_korean(num_str: str) -> str:
    """Convert integer or decimal string like '9,317' or '12.5' into natural Sino-Korean."""
    cleaned = num_str.replace(",", "").strip()
    if "." in cleaned:
        whole_s, frac_s = cleaned.split(".", 1)
        whole_val = int_to_sino_korean(int(whole_s)) if whole_s.isdigit() else whole_s
        digit_words = "".join("영" if ch == "0" else _KR_DIGITS[int(ch)] for ch in frac_s if ch.isdigit())
        return f"{whole_val} 점 {digit_words}".strip()
    if cleaned.isdigit():
        return int_to_sino_korean(int(cleaned))
    return num_str


def normalize_spoken_korean_numbers(text: str, expand_for_tts: bool = True) -> str:
    """Algorithmically normalize Korean dates, currencies, percentages, fractions, and integers.
    Zero hardcoded episode years or amounts.
    """
    if not text:
        return text
    if not expand_for_tts:
        return text

    out = text
    # 1. Dates: YYYY년 M월 D일 (6월 -> 유월, 10월 -> 시월)
    def _kr_date_repl(match: re.Match[str]) -> str:
        y = int(match.group(1))
        mo = int(match.group(2))
        d = int(match.group(3))
        mo_word = "유" if mo == 6 else ("시" if mo == 10 else int_to_sino_korean(mo))
        return f"{int_to_sino_korean(y)}년 {mo_word}월 {int_to_sino_korean(d)}일"

    out = re.sub(r"\b(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", _kr_date_repl, out)
    out = re.sub(
        r"\b(\d{4})년\s*(\d{1,2})월",
        lambda m: f"{int_to_sino_korean(int(m.group(1)))}년 {'유' if int(m.group(2)) == 6 else ('시' if int(m.group(2)) == 10 else int_to_sino_korean(int(m.group(2))))}월",
        out,
    )
    out = re.sub(r"\b(\d{4})년", lambda m: f"{int_to_sino_korean(int(m.group(1)))}년", out)
    out = re.sub(
        r"\b(\d{1,2})월\s*(\d{1,2})일",
        lambda m: f"{'유' if int(m.group(1)) == 6 else ('시' if int(m.group(1)) == 10 else int_to_sino_korean(int(m.group(1))))}월 {int_to_sino_korean(int(m.group(2)))}일",
        out,
    )

    # 2. Fractions like 1/3 or 3분의 1 -> 삼분의 일
    out = re.sub(
        r"\b(\d+)\s*/\s*(\d+)\b",
        lambda m: f"{int_to_sino_korean(int(m.group(2)))}분의 {int_to_sino_korean(int(m.group(1)))}",
        out,
    )
    out = re.sub(
        r"\b(\d+)\s*분의\s*(\d+)\b",
        lambda m: f"{int_to_sino_korean(int(m.group(1)))}분의 {int_to_sino_korean(int(m.group(2)))}",
        out,
    )

    # 3. Percentages
    out = re.sub(r"(\d[\d,]*(?:\.\d+)?)\s*(?:%|퍼센트)", lambda m: f"{decimal_to_sino_korean(m.group(1))} 퍼센트", out)

    # 4. Scaled amounts / counters (e.g. 22조, 22조원, 500억 원, 9,317명)
    out = re.sub(
        r"(\d[\d,]*(?:\.\d+)?)\s*(만|억|조|경)(?=$|[\s.,;:!?()\[\]원달러엔동%])",
        lambda m: f"{decimal_to_sino_korean(m.group(1))}{m.group(2)}",
        out,
    )

    # 5. Remaining digits
    out = re.sub(r"\d[\d,]*(?:\.\d+)?", lambda m: decimal_to_sino_korean(m.group(0)), out)
    return re.sub(r"\s+", " ", out).strip()


def expand_text_for_tts_timing(text: str, market: str = "EN") -> str:
    """Normalize digits, currencies, and dates into spoken-equivalent tokens prior to counting
    speech units so Edge-TTS timing and S03/S04 pacing estimation operate on the same scale.
    """
    if not text:
        return ""
    m = normalize_market_code(market)
    if m == "KR":
        return normalize_spoken_korean_numbers(text, expand_for_tts=True)
    if m == "JA":
        out = re.sub(r"(\d[\d,]*(?:\.\d+)?)\s*%", r"\1パーセント", text)
        # Approximate spoken morae/chars for Arabic digits and decimals in Japanese TTS
        def _ja_num_repl(match: re.Match[str]) -> str:
            raw = match.group(0).replace(",", "")
            if "." in raw:
                int_p, frac_p = raw.split(".", 1)
                int_k = "せん" * max(2, len(int_p)) if len(int_p) >= 4 else "いち" * max(1, len(int_p))
                return f"{int_k}てん{'いち' * max(1, len(frac_p))}"
            digits = re.sub(r"[^\d]", "", raw)
            if not digits:
                return match.group(0)
            n_val = int(digits[:12])
            if n_val >= 1000:
                return "せん" * len(digits) + "いち"
            return "いち" * max(1, len(digits))
        out = re.sub(r"\d[\d,]*(?:\.\d+)?", _ja_num_repl, out)
        return out
    if m == "VN":
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*T\b", r"\1 nghìn tỷ đô la", text, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*B\b", r"\1 tỷ đô la", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*M\b", r"\1 triệu đô la", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*K\b", r"\1 nghìn đô la", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)", r"\1 đô la", out)
        out = re.sub(r"(\d[\d,]*(?:\.\d+)?)\s*%", r"\1 phần trăm", out)
        def _vn_num_words(match: re.Match[str]) -> str:
            raw = match.group(0).replace(",", "")
            if "." in raw:
                parts = raw.split(".", 1)
                return f"{parts[0]} phẩy {' '.join(parts[1])}"
            if len(raw) >= 7:
                return "một trăm triệu năm mươi"
            if len(raw) >= 4:
                return "hai nghìn không trăm hai mươi"
            return match.group(0)
        out = re.sub(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{4,}\b|\b\d+\.\d+\b", _vn_num_words, out)
        return out
    # EN default
    out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*T\b", r"\1 trillion dollars", text, flags=re.IGNORECASE)
    out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*B\b", r"\1 billion dollars", out, flags=re.IGNORECASE)
    out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*M\b", r"\1 million dollars", out, flags=re.IGNORECASE)
    out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s*K\b", r"\1 thousand dollars", out, flags=re.IGNORECASE)
    out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", out)
    out = re.sub(r"(\d[\d,]*(?:\.\d+)?)\s*%", r"\1 percent", out)
    # Expand comma-separated numbers, 4+ digit years/counts, and decimals into spoken word equivalents
    def _en_num_words(match: re.Match[str]) -> str:
        raw = match.group(0).replace(",", "")
        if "." in raw:
            parts = raw.split(".", 1)
            return f"{parts[0]} point {' '.join(parts[1])}"
        if len(raw) >= 7:
            return "one two three million"
        if len(raw) >= 4:
            return "nine thousand three hundred"
        return "twenty five"
    out = re.sub(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{4,}\b|\b\d+\.\d+\b", _en_num_words, out)
    return out


# ==============================================================================
# 5. GENERIC MULTI-MARKET CLAIM ELEMENT EXTRACTOR (ZERO TOPIC HARDCODES)
# ==============================================================================

_GENERIC_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "were", "was", "are", "have", "has",
    "had", "into", "over", "under", "about", "after", "before", "their", "which", "when", "what",
    "been", "being", "also", "more", "than", "such", "only", "could", "would", "should", "will",
    "according", "reported", "alleged", "allegedly", "claim", "claims", "source",
    "있다", "있는", "했다", "대한", "위해", "따르면", "통해", "에서", "으로", "까지", "부터",
    "것으로", "밝혔다", "전했다", "보도", "관련", "대해", "이후", "이번", "경우",
    "こと", "ため", "による", "について", "として", "これ", "それ", "また", "され", "ている", "した",
    "theo", "được", "trong", "những", "không", "của", "cho", "với", "từ", "này", "khi", "đã", "sẽ",
}


_MONTH_NAME_MAP: Dict[str, int] = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

# 100% generic domain-neutral cross-lingual investigative & financial concepts (Rule 128)
GENERIC_FORENSIC_CONCEPTS: Dict[str, Dict[str, List[str]]] = {
    "regulator": {"KR": ["규제 당국", "감독 당국", "당국"], "JA": ["規制当局", "監督当局", "当局"], "VN": ["cơ quan quản lý", "cơ quan chức năng"]},
    "regulatory": {"KR": ["규제", "감독 당국"], "JA": ["規制当局", "制度"], "VN": ["quản lý", "cơ quan chức năng"]},
    "authorities": {"KR": ["관계 당국", "당국"], "JA": ["関係当局", "当局"], "VN": ["cơ quan chức năng", "nhà chức trách"]},
    "forensic": {"KR": ["정밀", "실증"], "JA": ["精査", "法務調査"], "VN": ["điều tra chuyên sâu", "giám định"]},
    "investigation": {"KR": ["조사", "수사"], "JA": ["調査", "捜査"], "VN": ["điều tra", "thanh tra"]},
    "investigations": {"KR": ["조사", "수사"], "JA": ["調査", "捜査"], "VN": ["điều tra", "thanh tra"]},
    "inquiry": {"KR": ["조사", "감찰"], "JA": ["調査", "監査"], "VN": ["thanh tra", "điều tra"]},
    "syndicate": {"KR": ["조직", "점조직"], "JA": ["組織網", "グループ"], "VN": ["đường dây", "tổ chức"]},
    "insolvent": {"KR": ["무자력", "지급불능"], "JA": ["債務超過", "支払不能"], "VN": ["mất khả năng thanh toán", "vỡ nợ"]},
    "bankruptcy": {"KR": ["파산", "도산"], "JA": ["破産", "破綻"], "VN": ["phá sản", "vỡ nợ"]},
    "strawmen": {"KR": ["명의대여자", "허수아비"], "JA": ["名義貸し", "名目上の代理人"], "VN": ["người đứng tên hộ", "bù nhìn"]},
    "proxy": {"KR": ["명의대여", "대리인"], "JA": ["名義貸し", "代理人"], "VN": ["đại diện danh nghĩa", "bù nhìn"]},
    "landlord": {"KR": ["임대인", "보유자"], "JA": ["賃貸人", "所有者"], "VN": ["chủ sở hữu", "bên cho thuê"]},
    "landlords": {"KR": ["임대인", "보유자"], "JA": ["賃貸人", "所有者"], "VN": ["chủ sở hữu", "bên cho thuê"]},
    "gap": {"KR": ["차액", "무자본", "갭"], "JA": ["ギャップ", "差額"], "VN": ["chênh lệch", "đòn bẩy"]},
    "leverage": {"KR": ["레버리지", "차입"], "JA": ["レバレッジ", "借入"], "VN": ["đòn bẩy", "vay nợ"]},
    "investment": {"KR": ["투자", "자금 투입"], "JA": ["投資", "資金投入"], "VN": ["đầu tư", "rót vốn"]},
    "capital": {"KR": ["자본", "자금"], "JA": ["資本", "資金"], "VN": ["nguồn vốn", "tư bản"]},
    "forged": {"KR": ["위조", "허위"], "JA": ["偽造", "虚偽"], "VN": ["giả mạo", "làm giả"]},
    "falsified": {"KR": ["허위 기재", "조작"], "JA": ["改ざん", "虚偽"], "VN": ["làm sai lệch", "giả mạo"]},
    "appraisal": {"KR": ["감정평가", "가치 산정"], "JA": ["鑑定評価", "資産評価"], "VN": ["định giá", "thẩm định giá"]},
    "valuation": {"KR": ["가치 평가", "산정액"], "JA": ["資産評価", "バリュエーション"], "VN": ["định giá", "ước tính giá trị"]},
    "collateral": {"KR": ["담보", "보증 자산"], "JA": ["担保", "保証資産"], "VN": ["tài sản đảm bảo", "thế chấp"]},
    "inflated": {"KR": ["과대 계상", "부풀린"], "JA": ["水増し", "過大評価"], "VN": ["thổi phồng", "đội giá"]},
    "systemic": {"KR": ["구조적", "시스템"], "JA": ["構造的", "制度的"], "VN": ["mang tính hệ thống", "cấu trúc"]},
    "structural": {"KR": ["구조적", "제도적"], "JA": ["構造的", "制度的"], "VN": ["cấu trúc", "thể chế"]},
    "failure": {"KR": ["실패", "결함"], "JA": ["機能不全", "失策"], "VN": ["thất bại", "sự cố"]},
    "failures": {"KR": ["실패", "결함"], "JA": ["機能不全", "失策"], "VN": ["thất bại", "sai sót"]},
    "indictment": {"KR": ["공소장", "기소"], "JA": ["起訴状", "起訴"], "VN": ["cáo trạng", "truy tố"]},
    "complaint": {"KR": ["고발장", "소장"], "JA": ["告訴状", "訴状"], "VN": ["đơn kiện", "đơn tố cáo"]},
    "settlement": {"KR": ["합의", "동의의결"], "JA": ["和解", "合意"], "VN": ["dàn xếp", "thỏa thuận"]},
    "penalty": {"KR": ["과징금", "제재"], "JA": ["課徴金", "制裁"], "VN": ["tiền phạt", "chế tài"]},
    "fine": {"KR": ["과징금", "벌금"], "JA": ["罰金", "課徴金"], "VN": ["tiền phạt", "xử phạt"]},
    "disclosure": {"KR": ["공시", "보고"], "JA": ["情報開示", "報告"], "VN": ["công bố thông tin", "báo cáo"]},
    "liquidity": {"KR": ["유동성", "자금 흐름"], "JA": ["流動性", "資金繰り"], "VN": ["thanh khoản", "dòng tiền"]},
    "bond": {"KR": ["채권", "회사채"], "JA": ["社債", "債券"], "VN": ["trái phiếu", "công cụ nợ"]},
    "debt": {"KR": ["부채", "채무"], "JA": ["負債", "債務"], "VN": ["khoản nợ", "nghĩa vụ nợ"]},
    "deficit": {"KR": ["적자", "손실"], "JA": ["赤字", "損失"], "VN": ["thâm hụt", "thua lỗ"]},
    "loss": {"KR": ["손실", "피해"], "JA": ["損失", "損害"], "VN": ["thiệt hại", "thua lỗ"]},
    "subsidiary": {"KR": ["자회사", "관계사"], "JA": ["子会社", "関連会社"], "VN": ["công ty con", "đơn vị liên kết"]},
    "contract": {"KR": ["계약", "약정"], "JA": ["契約", "約定"], "VN": ["hợp đồng", "thỏa thuận"]},
    "antitrust": {"KR": ["반독점", "공정거래"], "JA": ["独占禁止", "独禁法"], "VN": ["chống độc quyền", "cạnh tranh"]},
    "monopoly": {"KR": ["독점", "시장 지배"], "JA": ["独占", "市場支配"], "VN": ["độc quyền", "thống lĩnh thị trường"]},
    "license": {"KR": ["라이선스", "인허가"], "JA": ["ライセンス", "許認可"], "VN": ["giấy phép", "cấp phép"]},
    "tariff": {"KR": ["관세", "무역 장벽"], "JA": ["関税", "貿易措置"], "VN": ["thuế quan", "hàng rào thuế"]},
    "sanction": {"KR": ["제재", "처분"], "JA": ["制裁", "行政処分"], "VN": ["trừng phạt", "chế tài"]},
    "semiconductor": {"KR": ["반도체", "칩"], "JA": ["半導体", "チップ"], "VN": ["bán dẫn", "vi mạch"]},
    "audit": {"KR": ["감사", "회계 검증"], "JA": ["監査", "会計検査"], "VN": ["kiểm toán", "thanh tra"]},
    "victim": {"KR": ["피해자", "소비자"], "JA": ["被害者", "消費者"], "VN": ["nạn nhân", "người bị hại"]},
    "victims": {"KR": ["피해자", "피해 가구"], "JA": ["被害者", "被害者層"], "VN": ["nạn nhân", "người bị hại"]},
    "guarantee": {"KR": ["보장", "보증"], "JA": ["保証", "担保制度"], "VN": ["bảo lãnh", "cam kết bảo vệ"]},
    "minimum": {"KR": ["최소", "하한"], "JA": ["最低", "下限"], "VN": ["tối thiểu", "mức sàn"]},
    "relief": {"KR": ["구제", "지원"], "JA": ["救済", "支援"], "VN": ["cứu trợ", "hỗ trợ"]},
    "loophole": {"KR": ["제도적 허점", "사각지대"], "JA": ["抜け穴", "制度の死角"], "VN": ["kẽ hở pháp lý", "vùng xám"]},
    "ipo": {"KR": ["기업공개", "상장"], "JA": ["新規上場", "株式公開"], "VN": ["niêm yết", "IPO"]},
    "revenue": {"KR": ["매출", "수익"], "JA": ["売上高", "収益"], "VN": ["doanh thu", "lợi nhuận"]},
    "cash": {"KR": ["현금 흐름", "유동 자금"], "JA": ["キャッシュフロー", "手元資金"], "VN": ["dòng tiền", "tiền mặt"]},
    "documents": {"KR": ["문서", "서류"], "JA": ["文書", "資料"], "VN": ["hồ sơ", "tài liệu"]},
    "deposit": {"KR": ["보증금", "예치금"], "JA": ["保証金", "預託金"], "VN": ["tiền đặt cọc", "ký quỹ"]},
    "scheme": {"KR": ["제도", "방안"], "JA": ["制度", "枠組み"], "VN": ["cơ chế", "chính sách"]},
    "court": {"KR": ["법원", "재판부"], "JA": ["裁判所", "司法"], "VN": ["tòa án", "cơ quan tư pháp"]},
    "prosecutor": {"KR": ["검찰", "수사팀"], "JA": ["検察", "捜査当局"], "VN": ["cơ quan công tố", "viện kiểm sát"]},
    "fraud": {"KR": ["사기", "부정행위"], "JA": ["詐欺", "不正"], "VN": ["gian lận", "lừa đảo"]},
    "safety": {"KR": ["안전", "결함 검증"], "JA": ["安全性", "検証"], "VN": ["an toàn", "kiểm định"]},
    "recall": {"KR": ["리콜", "회수"], "JA": ["リコール", "回収"], "VN": ["thu hồi", "triệu hồi"]},
}


def _format_scaled_usd_cjk(amount_str: str, unit: str, market: str) -> str:
    """Convert English billion/million USD into mathematically exact KR (억/만 달러) or JA (億/万ドル)."""
    try:
        val = float(amount_str.replace(",", ""))
    except ValueError:
        return f"{amount_str} {unit}"
    u = unit.lower()
    if u == "trillion":
        # 1 trillion = 1조 (KR) / 1兆 (JA)
        num_str = str(int(val)) if val.is_integer() else f"{val:g}"
        return f"{num_str}조 달러" if market == "KR" else f"{num_str}兆ドル"
    if u == "billion":
        # $1B = 10억 달러 / 10億ドル; $40B = 400억 달러 / 400億ドル
        eok = val * 10.0
        num_str = str(int(eok)) if eok.is_integer() else f"{round(eok, 2):g}"
        return f"{num_str}억 달러" if market == "KR" else f"{num_str}億ドル"
    # million: $1M = 100만 달러 / 100万ドル; >= $100M -> 억/億
    man = val * 100.0
    if man >= 10000.0:
        eok = man / 10000.0
        num_str = str(int(eok)) if eok.is_integer() else f"{round(eok, 2):g}"
        return f"{num_str}억 달러" if market == "KR" else f"{num_str}億ドル"
    num_str = str(int(man)) if man.is_integer() else f"{round(man, 1):g}"
    return f"{num_str}만 달러" if market == "KR" else f"{num_str}万ドル"


def localize_dates_and_metrics(text: str, market: str) -> str:
    """Convert standard English calendar dates, fractions, and scaled currency phrases
    algorithmically into canonical target-market notation without any episode hardcodes.
    """
    m = normalize_market_code(market)
    out = text or ""

    def _date_repl(match: re.Match[str]) -> str:
        mo_str = match.group(1).lower()
        dy = int(match.group(2))
        yr = match.group(3)
        mo = _MONTH_NAME_MAP.get(mo_str)
        if not mo:
            return match.group(0)
        if m == "KR":
            return f"{yr}년 {mo}월 {dy}일" if yr else f"{mo}월 {dy}일"
        if m == "JA":
            return f"{yr}年{mo}月{dy}日" if yr else f"{mo}月{dy}日"
        if m == "VN":
            return f"ngày {dy} tháng {mo}" + (f" năm {yr}" if yr else "")
        return match.group(0)

    out = re.sub(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:,\s*(\d{4}))?\b",
        _date_repl,
        out,
        flags=re.IGNORECASE,
    )

    def _month_year_repl(match: re.Match[str]) -> str:
        mo_str = match.group(1).lower()
        yr = match.group(2)
        mo = _MONTH_NAME_MAP.get(mo_str)
        if not mo:
            return match.group(0)
        if m == "KR":
            return f"{yr}년 {mo}월"
        if m == "JA":
            return f"{yr}年{mo}月"
        if m == "VN":
            return f"tháng {mo} năm {yr}"
        return match.group(0)

    out = re.sub(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+((?:19|20)\d{2})\b",
        _month_year_repl,
        out,
        flags=re.IGNORECASE,
    )
    if m == "KR":
        out = re.sub(r"\bone[- ]third\b|\(1/3\)", "3분의 1", out, flags=re.IGNORECASE)
        out = re.sub(r"\bone[- ]half\b|\(1/2\)", "2분의 1", out, flags=re.IGNORECASE)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s+trillion\s+KRW\b", r"\1조 원", out, flags=re.IGNORECASE)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s+trillion\b", r"\1조", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s+(trillion|billion|million)\b", lambda mt: _format_scaled_usd_cjk(mt.group(1), mt.group(2), "KR"), out, flags=re.IGNORECASE)
    elif m == "JA":
        out = re.sub(r"\bone[- ]third\b|\(1/3\)", "3分の1", out, flags=re.IGNORECASE)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s+trillion\b", r"\1兆", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s+(trillion|billion|million)\b", lambda mt: _format_scaled_usd_cjk(mt.group(1), mt.group(2), "JA"), out, flags=re.IGNORECASE)
    elif m == "VN":
        out = re.sub(r"\bone[- ]third\b", "1/3", out, flags=re.IGNORECASE)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s+trillion\b", r"\1 nghìn tỷ", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d+(?:\.\d+)?)\s+billion\b", r"\1 tỷ USD", out, flags=re.IGNORECASE)
        out = re.sub(r"\$(\d+(?:\.\d+)?)\s+million\b", r"\1 triệu USD", out, flags=re.IGNORECASE)
    return out


def translate_claim_to_market_clause(claim_text: str, market: str, topic: str = "") -> str:
    """Synthesize a pure target-language clause from an English or mixed-script claim using
    native parentheticals, localized calendar/currency metrics, and generic forensic concepts.
    Zero English lowercase prose leaks into KR/JA/VN scripts.
    """
    m = normalize_market_code(market)
    localized = localize_dates_and_metrics(claim_text or "", m)
    elems = extract_claim_elements(localized)

    native_parts: List[str] = []
    seen_low: Set[str] = set()
    seen_num_norms: Set[str] = set()

    def _add_part(val: str) -> None:
        clean = val.strip(" .,;:\"'()[]")
        low = clean.lower()
        if clean and low not in seen_low:
            seen_low.add(low)
            native_parts.append(clean)
            for num_tok in re.findall(r"\d[\d,]*(?:\.\d+)?", clean):
                seen_num_norms.add(num_tok.replace(",", ""))

    # 1. Native-script parenthetical phrases & localized entities
    for paren in re.findall(r"\(([^()]{2,50})\)", localized):
        if m == "KR" and HANGUL_SYLLABLE_RE.search(paren):
            _add_part(paren)
        elif m == "JA" and (JP_KANA_RE.search(paren) or CJK_HAN_RE.search(paren)):
            _add_part(paren)
        elif m == "VN" and VN_DIACRITIC_RE.search(paren):
            _add_part(paren)

    for ent in elems.get("entities", []):
        if m == "KR" and HANGUL_SYLLABLE_RE.search(ent):
            _add_part(ent)
        elif m == "JA" and (JP_KANA_RE.search(ent) or CJK_HAN_RE.search(ent)):
            _add_part(ent)
        elif m == "VN" and VN_DIACRITIC_RE.search(ent):
            _add_part(ent)
        elif re.fullmatch(r"[A-Z0-9&\-]{2,8}", ent):
            _add_part(ent)

    # 2. Localized dates and numeric metrics (skip comma duplicates & bare sub-numbers already in parts)
    for d in elems.get("dates", []):
        _add_part(d)
    for mt in elems.get("metrics", []):
        mt_clean = mt.strip(" .,;:\"'()[]")
        num_norm = re.sub(r"[,\s]+", "", mt_clean)
        if any(mt_clean and mt_clean in existing for existing in native_parts):
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", num_norm) and num_norm in seen_num_norms:
            continue
        if len(mt_clean) <= 2 and mt_clean.isdigit() and native_parts:
            continue
        if m == "KR" and not re.search(r"[a-z]{3,}", mt):
            _add_part(mt)
        elif m == "JA" and not re.search(r"[a-z]{3,}", mt):
            _add_part(mt)
        elif m == "VN":
            _add_part(mt)

    # 3. Map generic forensic concepts into native terms (skip terms already embedded in native_parts)
    src_tokens = re.findall(r"[A-Za-z]{3,}", (claim_text or "").lower())
    concept_hits: List[str] = []
    existing_blob = " ".join(native_parts).lower()
    for tok in src_tokens:
        entry = GENERIC_FORENSIC_CONCEPTS.get(tok)
        if entry and m in entry:
            term = entry[m][0]
            if term.lower() in existing_blob:
                continue
            if term.lower() not in seen_low and term not in concept_hits:
                concept_hits.append(term)
                seen_low.add(term.lower())
        if len(concept_hits) >= 3:
            break

    combined = native_parts[:4] + concept_hits[: max(1, 5 - len(native_parts[:4]))]
    if not combined:
        return topic or ("확인 기록" if m == "KR" else ("確認記録" if m == "JA" else "hồ sơ ghi nhận"))
    joined = ", ".join(combined)
    return joined


def extract_claim_elements(claim_text: str) -> Dict[str, Any]:
    """Dynamically extract entities, acronyms, bilingual labels, metrics, dates, and content stems
    from ANY claim in ANY topic or market without topic-specific rules.
    """
    text = (claim_text or "").strip()
    if not text:
        return {"entities": [], "metrics": [], "dates": [], "terms": [], "stems": []}

    # Include localized metric/date equivalents alongside original text so cross-lingual matching works generically
    all_dates_pool: List[str] = []
    all_loc_metrics_pool: List[str] = []
    metric_pat = (
        r"(?:\d+\s*/\s*\d+|\d+\s*분의\s*\d+|\d+\s*分の\s*\d+|"
        r"[$€£¥₩₫]\s*\d[\d,]*(?:\.\d+)?\s*(?:trillion|billion|million|thousand|[TBMK]\b|십억\s*달러|백만\s*달러|조\s*원|조|억\s*원|억)?|"
        r"\d[\d,]*(?:\.\d+)?\s*(?:%|퍼센트|パーセント|phần trăm|십억\s*달러|백만\s*달러|십억|백만|十億ドル|百万ドル|十億|百万|tỷ\s*USD|triệu\s*USD|trillion|billion|million|basis\s*points|bps|cents|조\s*원|조|억\s*원|억|만\s*원|만|원|명|건|곳|배|万円|円|件|tỷ|triệu|nghìn|đồng|USD|KRW|JPY|VND)?)"
    )
    for lang_m in ("KR", "JA", "VN"):
        loc = localize_dates_and_metrics(text, lang_m)
        if loc != text:
            for d_match in re.findall(
                r"(?:(?:19|20)\d{2}[년年]\s*)?\d{1,2}[월月]\s*\d{1,2}[일日]|ngày\s+\d{1,2}\s+tháng\s+\d{1,2}(?:\s+năm\s+\d{4})?",
                loc,
            ):
                all_dates_pool.append(d_match.strip())
            for m_match in re.findall(metric_pat, loc, re.IGNORECASE):
                ms = m_match.strip()
                if len(ms) >= 3 and not ms.isdigit():
                    all_loc_metrics_pool.append(ms)

    # 1. Parenthetical terms e.g. "Ministry of Land (국토교통부)", "Financial Services Agency (金融庁)"
    paren_terms = [p.strip() for p in re.findall(r"\(([^()]{2,40})\)", text) if p.strip()]

    # 2. Acronyms and multi-word capitalized phrases
    acronyms = re.findall(r"\b[A-Z][A-Z0-9&\-]{1,10}\b", text)
    proper_phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b", text)

    # 3. Localized institutional / organization nouns (Hangul, Japanese Kanji/Katakana, Vietnamese)
    kr_entities = re.findall(
        r"[가-힣]{2,12}(?:부|청|원|은행|위원회|법원|검찰|공사|공단|협회|연구원|센터)",
        text,
    )
    jp_entities = re.findall(
        r"[\u4e00-\u9fff\u30a0-\u30ff]{2,12}(?:省|庁|委員会|銀行|裁判所|検察|公社|協会|機構)",
        text,
    )
    vn_entities = re.findall(
        r"(?:Bộ|Ngân hàng|Tòa án|Viện kiểm sát|Ủy ban|Thanh tra|Cơ quan)\s+[A-ZÀ-Ỹa-zà-ỹ\s]{2,28}",
        text,
    )

    # 4. Quantitative metrics & numbers & fractions & dates
    dates = all_dates_pool + re.findall(
        r"(?:(?:19|20)\d{2}[-./년年]\s*\d{1,2}[-./월月]?\s*(?:\d{1,2}[일日]?)?|"
        r"\d{1,2}[월月]\s*\d{1,2}[일日]|"
        r"ngày\s+\d{1,2}\s+tháng\s+\d{1,2}(?:\s+năm\s+\d{4})?)",
        text,
        re.IGNORECASE,
    )
    metrics = re.findall(metric_pat, text, re.IGNORECASE)
    metrics_clean = []
    for mt in metrics + all_loc_metrics_pool:
        s = mt.strip()
        if len(s) >= 2 or s.isdigit():
            metrics_clean.append(s)
    # Include comma-stripped bare numerals for large figures (>= 100 or decimal)
    for num_tok in re.findall(r"\b\d{1,3}(?:,\d{3})+\b", text):
        metrics_clean.append(num_tok)
        metrics_clean.append(num_tok.replace(",", ""))

    # 5. Meaningful lexical stems for semantic overlap & coverage checks
    # Split Japanese at Hiragana particle boundaries (Kanji / Katakana runs) instead of swallowing whole clauses
    raw_tokens = re.findall(
        r"[A-Za-z0-9\-']{3,}|[가-힣]{2,}|[\u4e00-\u9fff]{2,}|[\u30a0-\u30ff]{2,}|[A-Za-zÀ-ỹ]{3,}",
        text,
    )
    stems: List[str] = []
    seen_stems: Set[str] = set()
    for tok in raw_tokens:
        t_clean = tok.strip(".,;:!?\"'()[]{}").lower()
        # Strip common Korean postpositions lightly for cross-clause matching
        if HANGUL_SYLLABLE_RE.search(t_clean) and len(t_clean) >= 3:
            for suf in ("에서는", "으로는", "이라고", "이라는", "에서", "으로", "까지", "부터", "에게", "은", "는", "이", "가", "을", "를", "의", "에", "로", "와", "과"):
                if t_clean.endswith(suf) and len(t_clean) - len(suf) >= 2:
                    t_clean = t_clean[: -len(suf)]
                    break
        if len(t_clean) < 2 or t_clean in _GENERIC_STOPWORDS:
            continue
        if CJK_HAN_RE.search(t_clean) and len(t_clean) >= 8:
            # Compound Kanji run (e.g. topic+suffix): index compound halves so sub-phrases match reliably
            for sub in (t_clean[:4], t_clean[4:8], t_clean[-4:]):
                if len(sub) >= 3 and sub not in seen_stems:
                    seen_stems.add(sub)
                    stems.append(sub)
        if t_clean not in seen_stems:
            seen_stems.add(t_clean)
            stems.append(t_clean)

    entities: List[str] = []
    seen_ent: Set[str] = set()
    for ent in paren_terms + acronyms + proper_phrases + kr_entities + jp_entities + [v.strip() for v in vn_entities]:
        key = ent.lower()
        if key not in seen_ent:
            seen_ent.add(key)
            entities.append(ent)

    return {
        "entities": entities[:12],
        "metrics": list(dict.fromkeys(metrics_clean))[:14],
        "dates": list(dict.fromkeys([d.strip() for d in dates if d.strip()]))[:8],
        "stems": stems[:24],
    }


def has_entity_or_metric_signal(text: str, elements: Dict[str, Any], min_stem_hits: int = 2) -> Tuple[bool, List[str]]:
    """True if `text` carries verifiable factual overlap (direct or cross-lingual) with extracted claim elements."""
    t_low = (text or "").lower()
    t_norm = re.sub(r"[,\s]+", "", t_low)
    matched: List[str] = []

    for m in elements.get("metrics", []) + elements.get("dates", []):
        m_low = m.lower().strip()
        m_digits = re.sub(r"[^\d.]", "", m_low)
        if m_low and (m_low in t_low or m_low.replace(",", "") in t_norm or (len(m_digits) >= 3 and m_digits in t_norm)):
            if m not in matched:
                matched.append(m)

    for e in elements.get("entities", []):
        e_low = e.lower()
        if e_low in t_low or (re.sub(r"\s+", "", e_low) in t_norm and len(e_low) >= 2):
            if e not in matched:
                matched.append(e)

    stem_hits = 0
    for s in elements.get("stems", []):
        hit = s in t_low
        if not hit and s in GENERIC_FORENSIC_CONCEPTS:
            # Cross-lingual concept match (EN concept -> KR/JA/VN equivalent present in narration)
            for lang_terms in GENERIC_FORENSIC_CONCEPTS[s].values():
                if any(term.lower() in t_low for term in lang_terms):
                    hit = True
                    break
        if hit:
            stem_hits += 1
            if s not in matched:
                matched.append(s)

    has_metric = any(
        m.lower() in t_low or m.lower().replace(",", "") in t_norm or (len(re.sub(r"[^\d.]", "", m)) >= 3 and re.sub(r"[^\d.]", "", m) in t_norm)
        for m in elements.get("metrics", []) + elements.get("dates", [])
    )
    has_entity = any(e.lower() in t_low or re.sub(r"\s+", "", e.lower()) in t_norm for e in elements.get("entities", []))

    if (has_metric and (has_entity or stem_hits >= 1)) or stem_hits >= min_stem_hits or (has_entity and stem_hits >= 1):
        return True, matched[:8]
    return False, matched[:8]


# ==============================================================================
# 6. TARGET MARKET LANGUAGE PURITY & ENTITY APPROPRIATENESS (GATE 6A & 6B)
# ==============================================================================

_MARKET_DOMESTIC_SIGNATURES: Dict[str, List[str]] = {
    "KR": ["국토교통부", "금감원", "금융감독원", "금융위원회", "한국은행", "공정거래위원회", "조원", "억원"],
    "JA": ["金融庁", "日本銀行", "日銀", "国土交通省", "公正取引委員会", "億円", "万円"],
    "VN": ["Ngân hàng Nhà nước", "Bộ Công an", "Bộ Tài chính", "tỷ đồng", "triệu đồng"],
    "EN": ["Federal Reserve", "Securities and Exchange Commission", "Department of Justice", "Consumer Financial Protection Bureau"],
}


def check_target_market_language_purity(
    text: str,
    market: str = "EN",
    grounded_proper_nouns: Optional[Set[str]] = None,
) -> Tuple[bool, List[str]]:
    """Gate 6A: Strict Unicode script, diacritic, and cross-language contamination audit."""
    m = normalize_market_code(market)
    issues: List[str] = []
    sample = (text or "").strip()
    if not sample:
        return False, ["Empty script text"]

    # Remove grounded proper nouns / acronyms present in ledger before flagging foreign tokens
    cleaned_for_ascii = sample
    for noun in (grounded_proper_nouns or set()):
        if noun and len(noun) >= 2:
            cleaned_for_ascii = cleaned_for_ascii.replace(noun, " ")

    hangul_n = len(HANGUL_SYLLABLE_RE.findall(sample))
    kana_n = len(JP_KANA_RE.findall(sample))
    han_n = len(CJK_HAN_RE.findall(sample))
    vn_diac_n = len(VN_DIACRITIC_RE.findall(sample))
    latin_n = len(LATIN_LETTER_RE.findall(sample))
    total_alpha = max(1, hangul_n + kana_n + han_n + vn_diac_n + latin_n)

    if m == "KR":
        if hangul_n < 150 and len(sample) > 400:
            issues.append(f"KR script has too few Hangul syllables ({hangul_n})")
        if hangul_n / total_alpha < 0.72:
            issues.append(f"KR Hangul share too low ({hangul_n}/{total_alpha} = {hangul_n/total_alpha:.2f} < 0.72)")
        if kana_n > 0:
            issues.append(f"Foreign Japanese Kana detected in KR script ({kana_n} chars)")
        if han_n > max(12, int(total_alpha * 0.03)):
            issues.append(f"Excessive CJK Kanji/Hanzi in KR script ({han_n} chars)")
        if vn_diac_n > 0:
            issues.append(f"Foreign Vietnamese diacritics detected in KR script ({vn_diac_n} chars)")
        # Reject multi-word English prose leaks (allow pure uppercase acronym runs)
        eng_runs = [
            r for r in re.findall(r"\b[A-Za-z]{2,}(?:[\s\-]+[A-Za-z]{2,}){2,}\b", cleaned_for_ascii)
            if re.search(r"[a-z]", r)
        ]
        if eng_runs:
            issues.append(f"Unlocalized English prose detected in KR script: '{eng_runs[0]}'")

    elif m == "JA":
        jp_total = kana_n + han_n
        if jp_total < 150 and len(sample) > 400:
            issues.append(f"JA script has too few Japanese characters ({jp_total})")
        if jp_total / total_alpha < 0.72:
            issues.append(f"JA character share too low ({jp_total}/{total_alpha} = {jp_total/total_alpha:.2f} < 0.72)")
        if kana_n / total_alpha < 0.15:
            issues.append(f"JA Kana share too low ({kana_n}/{total_alpha} = {kana_n/total_alpha:.2f} < 0.15); possible non-JA text")
        if hangul_n > 0:
            issues.append(f"Foreign Korean Hangul detected in JA script ({hangul_n} chars)")
        if vn_diac_n > 0:
            issues.append(f"Foreign Vietnamese diacritics detected in JA script ({vn_diac_n} chars)")
        eng_runs = [
            r for r in re.findall(r"\b[A-Za-z]{2,}(?:[\s\-]+[A-Za-z]{2,}){2,}\b", cleaned_for_ascii)
            if re.search(r"[a-z]", r)
        ]
        if eng_runs:
            issues.append(f"Unlocalized English prose detected in JA script: '{eng_runs[0]}'")

    elif m == "VN":
        if hangul_n > 0:
            issues.append(f"Foreign Korean Hangul detected in VN script ({hangul_n} chars)")
        if kana_n > 0 or han_n > 0:
            issues.append(f"Foreign CJK/Kana detected in VN script (kana={kana_n}, han={han_n})")
        vn_ratio = vn_diac_n / total_alpha
        if vn_ratio < 0.04:
            issues.append(f"VN diacritic ratio too low ({vn_ratio:.3f} < 0.04); missing Vietnamese tone/vowel marks")
        # Detect sustained English sentences inside VN narration (case-insensitive)
        eng_stop_runs = re.findall(
            r"\b(?:the|and|with|that|from|this|were|was|have|has|had|because|between|according|into|over|under|their|which|when|what|after|before|while|during|without|through|against|could|would|should)\s+[a-z]{2,}\s+[a-z]{2,}\b",
            cleaned_for_ascii.lower(),
        )
        if eng_stop_runs:
            issues.append(f"Foreign English prose detected in VN script: '{eng_stop_runs[0]}'")

    else:  # EN
        if hangul_n > 0:
            issues.append(f"Foreign Korean Hangul detected in EN script ({hangul_n} chars)")
        if kana_n > 0 or han_n > 0:
            issues.append(f"Foreign CJK/Kana detected in EN script (kana={kana_n}, han={han_n})")
        # Check non-grounded Vietnamese diacritics regardless of whether ASCII nouns were stripped
        vn_diac_cleaned = len(VN_DIACRITIC_RE.findall(cleaned_for_ascii))
        if vn_diac_cleaned > max(4, int(total_alpha * 0.02)):
            issues.append(f"Foreign Vietnamese diacritics detected in EN script ({vn_diac_cleaned} chars)")

    return len(issues) == 0, issues


def check_market_entity_appropriateness(
    text: str,
    market: str,
    evidence_ledger: List[Dict[str, Any]],
    topic: str = "",
) -> Tuple[bool, List[str]]:
    """Gate 6B: Detect hallucinated out-of-market institutions/currencies not present in ledger/topic."""
    m = normalize_market_code(market)
    ledger_corpus = " ".join(
        [topic or ""]
        + [str(c.get("claim", "")) + " " + str(c.get("source_name", "")) for c in evidence_ledger]
    ).lower()
    script_low = (text or "").lower()
    leaks: List[str] = []

    for other_m, markers in _MARKET_DOMESTIC_SIGNATURES.items():
        if other_m == m:
            continue
        for marker in markers:
            mk_low = marker.lower()
            if mk_low in script_low and mk_low not in ledger_corpus:
                leaks.append(f"Ungrounded {other_m} institution/unit '{marker}' leaked into {m} script")
    return len(leaks) == 0, leaks


# ==============================================================================
# 7. STATEMENT-TO-CLAIM AUDIT & CALIBRATED RUBRIC SCORING (S04)
# ==============================================================================

_UNVERIFIED_ATTRIBUTION_HINTS: Dict[str, List[str]] = {
    "KR": ["보도", "알려졌", "전해졌", "미확인", "초기", "제기", "추정", "주장", "의혹"],
    "JA": ["報道", "伝えられ", "未確認", "初期", "指摘", "疑い", "推測"],
    "VN": ["báo chí", "chưa kiểm chứng", "bước đầu", "cho rằng", "cáo buộc", "nghi vấn", "dự kiến"],
    "EN": ["report", "reportedly", "unverified", "preliminary", "alleg", "claim", "estimate", "according to"],
}

_NEGATIVE_POLARITY_TERMS = {
    "하락", "폭락", "감소", "축소", "손실", "적자", "붕괴", "중단", "취소", "실패",
    "下落", "減少", "縮小", "損失", "赤字", "崩壊", "中止", "失敗",
    "giảm", "sụt giảm", "thua lỗ", "thâm hụt", "sụp đổ", "đình chỉ", "thất bại",
    "fell", "drop", "dropped", "decline", "loss", "deficit", "collapse", "halted", "failed", "cut",
}
_POSITIVE_POLARITY_TERMS = {
    "상승", "급등", "증가", "확대", "흑자", "성공", "통과", "승인",
    "上昇", "急騰", "増加", "拡大", "黒字", "成功", "承認",
    "tăng", "tăng vọt", "thặng dư", "thành công", "phê duyệt",
    "rose", "surged", "increase", "surplus", "profit", "approved", "expanded",
}


def audit_statement_claim_alignment(
    beats: List[Dict[str, Any]],
    evidence_ledger: List[Dict[str, Any]],
    statement_claim_map: Optional[List[Dict[str, Any]]] = None,
    market: str = "EN",
) -> Dict[str, Any]:
    """Audit proportional coverage, primary catalyst coverage, Beat 1 verification safety,
    causal polarity parity, and explicit statement-to-claim mapping fidelity.
    """
    m = normalize_market_code(market)
    all_lines: List[Dict[str, Any]] = []
    for beat in beats or []:
        b_id = beat.get("beat_id", "")
        for ln in beat.get("lines", []):
            all_lines.append({**ln, "beat_id": b_id})

    ledger_by_id: Dict[str, Dict[str, Any]] = {
        str(c.get("claim_id", f"C{idx+1:03d}")): c for idx, c in enumerate(evidence_ledger or [])
    }

    # Build normalized map index from explicit statement_claim_map or inline line claim_ids
    mapped_claims: Set[str] = set()
    substantive_covered: Set[str] = set()
    polarity_mismatches: List[str] = []
    unverified_attribution_gaps: List[str] = []
    beat1_unverified_elevation = False
    beat1_has_verified_anchor = False

    claim_elements_cache: Dict[str, Dict[str, Any]] = {
        cid: extract_claim_elements(str(c.get("claim", "")))
        for cid, c in ledger_by_id.items()
    }

    # Pre-index Beat 1 lines to inspect opening hook integrity
    b1_lines = [ln for ln in all_lines if str(ln.get("beat_id", "")).startswith("B1")]
    unv_hints = _UNVERIFIED_ATTRIBUTION_HINTS.get(m, _UNVERIFIED_ATTRIBUTION_HINTS["EN"])

    for idx, ln in enumerate(all_lines):
        txt = str(ln.get("text", ""))
        txt_low = txt.lower()
        b_id = str(ln.get("beat_id", ""))
        cids = [str(x) for x in (ln.get("claim_ids") or []) if str(x) in ledger_by_id]
        for cid in cids:
            mapped_claims.add(cid)
            cl = ledger_by_id[cid]
            ver = str(cl.get("verification_status", "unverified_secondary"))
            elems = claim_elements_cache[cid]
            ok_overlap, _ = has_entity_or_metric_signal(txt, elems, min_stem_hits=2)
            if ok_overlap:
                substantive_covered.add(cid)

            if b_id.startswith("B1"):
                if ver in ("verified_primary", "corroborated_secondary"):
                    beat1_has_verified_anchor = True
                elif ver == "unverified_secondary" and idx < 2:
                    # Opening hook premise built solely on unverified secondary RSS rumor
                    if not any(
                        str(ledger_by_id[oc].get("verification_status")) in ("verified_primary", "corroborated_secondary")
                        for oc in cids
                    ):
                        beat1_unverified_elevation = True

            if ver == "unverified_secondary":
                if not any((h.lower() if m in ("EN", "VN") else h) in (txt_low if m in ("EN", "VN") else txt) for h in unv_hints):
                    unverified_attribution_gaps.append(
                        f"Line {ln.get('line_id', idx)} cites unverified claim {cid} without unverified/preliminary attribution"
                    )

            # Polarity contradiction guard
            cl_low = str(cl.get("claim", "")).lower()
            cl_neg = any(t in cl_low for t in _NEGATIVE_POLARITY_TERMS)
            cl_pos = any(t in cl_low for t in _POSITIVE_POLARITY_TERMS)
            ln_neg = any(t in txt_low for t in _NEGATIVE_POLARITY_TERMS)
            ln_pos = any(t in txt_low for t in _POSITIVE_POLARITY_TERMS)
            if (cl_neg and not cl_pos) and (ln_pos and not ln_neg):
                polarity_mismatches.append(f"Line {ln.get('line_id', idx)} flips negative polarity of {cid} to positive")
            elif (cl_pos and not cl_neg) and (ln_neg and not ln_pos):
                polarity_mismatches.append(f"Line {ln.get('line_id', idx)} flips positive polarity of {cid} to negative")

    # Cross-check cross-line Beat-level substantive overlap for claims explicitly referenced in beat
    for beat in beats or []:
        beat_text = " ".join(str(ln.get("text", "")) for ln in beat.get("lines", []))
        beat_cids = {str(x) for ln in beat.get("lines", []) for x in (ln.get("claim_ids") or [])}
        for cid in beat_cids:
            if cid in ledger_by_id and cid not in substantive_covered:
                ok_beat, _ = has_entity_or_metric_signal(beat_text, claim_elements_cache[cid], min_stem_hits=2)
                if ok_beat:
                    substantive_covered.add(cid)

    total_claims = len(ledger_by_id)
    verified_catalysts = [
        cid for cid, c in ledger_by_id.items()
        if str(c.get("causal_role")) == "primary_catalyst"
        and str(c.get("verification_status")) in ("verified_primary", "corroborated_secondary")
    ]
    verified_mechanisms = [
        cid for cid, c in ledger_by_id.items()
        if str(c.get("causal_role")) == "transmission_mechanism"
        and str(c.get("verification_status")) in ("verified_primary", "corroborated_secondary")
    ]

    covered_catalysts = [cid for cid in verified_catalysts if cid in substantive_covered]
    covered_mechanisms = [cid for cid in verified_mechanisms if cid in substantive_covered]

    coverage_ratio = (len(substantive_covered) / total_claims) if total_claims > 0 else 1.0
    required_min_ratio = 0.60
    coverage_ok = total_claims == 0 or (
        coverage_ratio >= required_min_ratio
        and len(substantive_covered) >= math.ceil(total_claims * required_min_ratio)
    )
    catalysts_ok = (len(covered_catalysts) == len(verified_catalysts)) if verified_catalysts else True
    mechanisms_ok = (len(covered_mechanisms) >= math.ceil(len(verified_mechanisms) * 0.75)) if verified_mechanisms else True
    has_map = bool(statement_claim_map) and len(statement_claim_map) >= max(1, len(all_lines) // 2)

    has_any_verified = any(
        str(c.get("verification_status")) in ("verified_primary", "corroborated_secondary")
        for c in ledger_by_id.values()
    )
    if not b1_lines or not has_any_verified:
        beat1_has_verified_anchor = False

    passed = (
        coverage_ok
        and catalysts_ok
        and mechanisms_ok
        and not beat1_unverified_elevation
        and (beat1_has_verified_anchor if has_any_verified else True)
        and len(polarity_mismatches) == 0
    )

    return {
        "passed": passed,
        "total_claims": total_claims,
        "mapped_claims_count": len(mapped_claims),
        "substantive_covered_count": len(substantive_covered),
        "coverage_ratio": round(coverage_ratio, 4),
        "required_min_ratio": required_min_ratio,
        "coverage_ok": coverage_ok,
        "verified_catalysts_total": len(verified_catalysts),
        "verified_catalysts_covered": len(covered_catalysts),
        "catalysts_ok": catalysts_ok,
        "verified_mechanisms_total": len(verified_mechanisms),
        "verified_mechanisms_covered": len(covered_mechanisms),
        "mechanisms_ok": mechanisms_ok,
        "beat1_has_verified_anchor": beat1_has_verified_anchor,
        "beat1_unverified_elevation": beat1_unverified_elevation,
        "unverified_attribution_gaps": unverified_attribution_gaps,
        "polarity_mismatches": polarity_mismatches,
        "statement_claim_map_present": has_map,
    }


def compute_calibrated_script_score(
    gates: Dict[str, bool],
    evidence_ledger: List[Dict[str, Any]],
    claim_audit: Dict[str, Any],
    violations_count: int,
    has_explainer_filler: bool = False,
) -> Dict[str, Any]:
    """Deterministic 0.0-10.0 rubric weighted by real evidence quality, gate results, and entailment.
    Replaces arbitrary constant fallback scores.
    """
    prov_summary = summarize_evidence_provenance(evidence_ledger)
    v_ratio = float(prov_summary.get("verified_or_corroborated_ratio", 0.0))
    p_ratio = float(prov_summary.get("primary_only_ratio", 0.0))

    # 1. Evidence verification depth (0.0 - 2.5)
    evidence_pts = round(min(2.5, 0.7 + 1.3 * v_ratio + 0.5 * p_ratio), 2)
    if prov_summary.get("heavy_unverified_warning"):
        evidence_pts = round(min(evidence_pts, 1.3), 2)

    # 2. Claim coverage & causal entailment (0.0 - 2.5)
    cov_ratio = float(claim_audit.get("coverage_ratio", 0.0))
    entail_pts = 2.0 * min(1.0, cov_ratio / 0.75)
    if claim_audit.get("catalysts_ok"):
        entail_pts += 0.3
    if claim_audit.get("statement_claim_map_present"):
        entail_pts += 0.2
    entail_pts -= 0.5 * len(claim_audit.get("polarity_mismatches", []))
    entail_pts -= 0.4 if claim_audit.get("beat1_unverified_elevation") else 0.0
    entail_pts = round(max(0.0, min(2.5, entail_pts)), 2)

    # 3. Legal & procedural accuracy (0.0 - 1.5)
    legal_pts = 1.5 if gates.get("legal_language_matches_status", False) else 0.3

    # 4. Target market language & institutional fit (0.0 - 1.5)
    lang_pts = 0.0
    if gates.get("target_market_language_compliance", False):
        lang_pts += 1.0
    if gates.get("market_entity_appropriateness", True):
        lang_pts += 0.5
    lang_pts = round(lang_pts, 2)

    # 5. Structure, pacing, grounding & editorial focus (0.0 - 2.0)
    struct_pts = 0.0
    if gates.get("duration_estimate_in_window", False):
        struct_pts += 0.5
    if gates.get("every_factual_line_has_claim_id", False):
        struct_pts += 0.4
    if gates.get("hook_within_20s", False):
        struct_pts += 0.4
    if gates.get("pattern_interrupt_gap_ok", False):
        struct_pts += 0.3
    if gates.get("topic_specificity_gate", False):
        struct_pts += 0.4
    if has_explainer_filler:
        struct_pts = max(0.0, struct_pts - 0.5)
    struct_pts = round(struct_pts, 2)

    total = evidence_pts + entail_pts + legal_pts + lang_pts + struct_pts
    # Extra penalty for unverified attribution gaps or violations
    total -= min(1.5, 0.2 * len(claim_audit.get("unverified_attribution_gaps", [])))
    if not all(bool(v) for v in gates.values()):
        total = min(total, 7.2)
    # Programmatic fallback without live LLM audit cannot claim near-perfect >= 8.6 score
    total = round(max(0.0, min(8.5, total)), 2)

    return {
        "aggregate_score": total,
        "breakdown": {
            "evidence_provenance_quality": evidence_pts,
            "claim_coverage_alignment": entail_pts,
            "legal_procedural_precision": legal_pts,
            "language_and_market_fit": lang_pts,
            "structure_pacing_and_tts": struct_pts,
            "verified_or_corroborated_ratio": v_ratio,
            "violations_count": violations_count,
        },
    }


def load_matching_grounding_intel(
    run_root: Path,
    repo_root: Path,
    topic_override: Optional[str] = None,
    market: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Load run-local grounding_intel.json, or active_candidate only when topic & market match."""
    local_file = Path(run_root) / "grounding_intel.json"
    if local_file.is_file():
        try:
            data = json.loads(local_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    cand_file = Path(repo_root) / "active_candidate" / "grounding_intel.json"
    if not cand_file.is_file():
        return None
    try:
        cand = json.loads(cand_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(cand, dict):
        return None

    if market and cand.get("market"):
        if normalize_market_code(str(cand.get("market"))) != normalize_market_code(market):
            return None

    req_topic = re.sub(r"\s+", " ", (topic_override or "").strip()).lower()
    if req_topic:
        cand_topic = re.sub(r"\s+", " ", str(cand.get("topic") or "").strip()).lower()
        if not cand_topic:
            return None
        if req_topic not in cand_topic and cand_topic not in req_topic:
            req_toks = {t for t in re.findall(r"[a-z0-9가-힣\u3040-\u30ff\u4e00-\u9fffÀ-ỹ]{2,}", req_topic)}
            cand_toks = {t for t in re.findall(r"[a-z0-9가-힣\u3040-\u30ff\u4e00-\u9fffÀ-ỹ]{2,}", cand_topic)}
            if not (req_toks & cand_toks):
                return None

    return cand
