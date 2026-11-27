#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s02_research.py — Stage S2: Competitor Recon & Reality Grounding (AVF-STAB-001).

Implements Stage Shape Standard. Extracts factual grounding factsheet and narrative vacuums.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Tuple

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S2_RESEARCH

_GENERIC_ANCHOR_STOPWORDS: set[str] = {
    "손실", "위기", "시장", "정부", "문제", "투자", "가능성", "부담", "핵심", "확인",
    "보도", "주가", "증시", "개인투자자", "사태", "대책", "방안", "검토", "관련", "규모",
    "논란", "의혹", "결과", "발표", "기관", "금융", "회사", "기업", "한국", "국내", "아직",
    "확인되지", "않은", "loss", "crisis", "market", "government", "risk", "report",
    "issue", "fund", "price", "stock", "investors", "policy", "review", "confirmed",
    "losses", "stocks", "company", "public", "news", "korean", "korea", "trillion",
    "billion", "million", "won", "yen", "usd", "krw", "jpy", "vnd", "retail",
    "reported", "headline", "snippet", "financial", "institutions", "companies",
    "authorities", "recent", "about", "while", "their", "which", "other", "second",
    "half", "year",
    "市場", "政府", "問題", "投資", "損失", "確認", "報道",
    "thị", "trường", "chính", "phủ", "rủi", "ro", "báo", "cáo", "đầu", "tư",
}


def _extract_topical_anchors(
    topic: str,
    central_question: str = "",
    scheme_summary: str = "",
    antagonist_name: str = "",
) -> Tuple[set[str], set[str]]:
    """Extract distinctive topic anchors (specific subjects/acronyms/numbers) vs generic context words."""
    primary_text = f"{topic} {antagonist_name}"
    secondary_text = f"{central_question} {scheme_summary}"

    def _tokens(txt: str) -> set[str]:
        raw = re.findall(r"[가-힣\u3040-\u30ff\u4e00-\u9fff]{2,}|[a-z0-9]{4,}", txt.lower())
        cleaned: set[str] = set()
        for tok in raw:
            stripped = re.sub(r"(?:은|는|이|가|을|를|의|에|에서|으로|로|과|와|도|만|까지|부터)$", "", tok)
            cand = stripped if len(stripped) >= 2 else tok
            if cand in _GENERIC_ANCHOR_STOPWORDS or cand.isdigit():
                continue
            cleaned.add(cand)
        return cleaned

    primary_anchors = _tokens(primary_text)
    secondary_anchors = _tokens(secondary_text)
    return primary_anchors, (primary_anchors | secondary_anchors)


def _filter_topically_relevant_claims(
    claims: List[Any],
    topic: str,
    central_question: str = "",
    scheme_summary: str = "",
    antagonist_name: str = "",
    market: str = "EN",
) -> List[Any]:
    """Filter out off-topic keyword-collision claims while preserving valid domain coverage."""
    _ = market
    if not claims or len(claims) <= 6:
        return claims

    primary_anchors, combined_anchors = _extract_topical_anchors(
        topic=topic,
        central_question=central_question,
        scheme_summary=scheme_summary,
        antagonist_name=antagonist_name,
    )
    if not primary_anchors and not combined_anchors:
        return claims

    # Algorithmic compound-stem decomposition for 4+ char CJK/Hangul anchors (Rule 128 pure)
    _generic_stems = {
        "펀드", "기금", "시장", "회사", "기업", "금융", "투자", "손실", "위기", "은행", "정부",
        "문제", "사태", "대책", "보도", "언론", "자료", "기록", "제도", "구조",
    }
    domain_substrings = {a for a in primary_anchors if len(a) >= 2}
    for tok in primary_anchors:
        if len(tok) >= 4 and re.fullmatch(r"[가-힣\u3040-\u30ff\u4e00-\u9fff]+", tok):
            mid = len(tok) // 2
            for part in (tok[:2], tok[:mid], tok[mid:], tok[-2:]):
                if len(part) >= 2 and part not in _generic_stems and part not in _GENERIC_ANCHOR_STOPWORDS:
                    domain_substrings.add(part)

    kept: List[Any] = []
    dropped_titles: List[str] = []
    for item in claims:
        c_txt = (
            item.get("claim", "") if isinstance(item, dict) else getattr(item, "claim", "")
        )
        c_low = str(c_txt).lower()
        primary_hits = sum(1 for a in primary_anchors if a in c_low)
        sub_hits = sum(1 for s in domain_substrings if s in c_low)
        sec_hits = sum(1 for a in combined_anchors if a in c_low)
        if primary_hits >= 1 or sub_hits >= 1 or sec_hits >= 2:
            kept.append(item)
        else:
            dropped_titles.append(str(c_txt)[:80])

    if len(kept) >= 6 and dropped_titles:
        logger.info(
            f"[S02_RESEARCH] Dropped {len(dropped_titles)} off-topic keyword-collision claim(s): "
            f"{dropped_titles}"
        )
        return kept
    return claims


@pipeline_stage(
    id="s02_research",
    order=2,
    name="Deep Investigative Research",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s01_ideation"],
    upstream=["s01_ideation"],
    downstream=["s03_script"],
    artifacts=["runs/{run_id}/s02_research/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s02_research --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S2: Research & Grounding."""
    start_ts = time.time()
    s1_art = require_input(STAGE, ctx.paths)
    topic = s1_art.payload.get("topic", "Corporate Monopoly Inquest")
    market = s1_art.payload.get("market", "EN")

    preset_raw = (getattr(ctx.preset, "name", ctx.preset) if ctx.preset else getattr(getattr(ctx, "manifest", None), "preset", None)) or "story_forensic"
    is_story = bool(preset_raw in ("story_forensic", "vox_narrative"))

    from app.services.story_provenance_engine import load_matching_grounding_intel

    grounding_intel = load_matching_grounding_intel(
        ctx.paths.root,
        ctx.paths.repo_root,
        topic_override=topic,
        market=market,
    )

    if is_story:
        from app.schemas.story_contracts import EvidenceClaim, StoryResearchPayload, TimelineEvent

        prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s02_research.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""

        def _build_generic_evidence_ledger(topic_name: str, s1_payload: Dict[str, Any]) -> Tuple[List[EvidenceClaim], List[TimelineEvent]]:
            from app.services.story_provenance_engine import (
                classify_claim_provenance,
                credibility_tier_rank,
                verification_priority_rank,
            )

            if grounding_intel and grounding_intel.get("claims"):
                classified_list = [
                    classify_claim_provenance(c, market=market) for c in grounding_intel["claims"]
                ]
                classified_list.sort(
                    key=lambda x: (
                        credibility_tier_rank(x.get("credibility_tier", "unconfirmed_claim")),
                        verification_priority_rank(x.get("verification_status", "unverified_secondary")),
                        0 if x.get("causal_role") == "primary_catalyst" else (1 if x.get("causal_role") == "transmission_mechanism" else 2),
                    )
                )
                claims = []
                for idx, prov_c in enumerate(classified_list, start=1):
                    c_id = f"C{idx:03d}"
                    def_src_url = (
                        "https://www.korea.kr" if market == "KR"
                        else ("https://www.fsa.go.jp" if market == "JA"
                              else ("https://chinhphu.vn" if market == "VN" else "https://www.sec.gov"))
                    )
                    source_url = prov_c.get("source_url") or def_src_url
                    raw_cl_text = str(prov_c.get("claim") or f"Factual evidentiary claim regarding {topic_name}")
                    if "विकल्प" in raw_cl_text:
                        raw_cl_text = raw_cl_text.replace("विकल्प", "선택권" if market == "KR" else ("選択肢" if market == "JA" else "lựa chọn"))
                    raw_cl_text = re.sub(r"[\u0900-\u097F]+", "", raw_cl_text)
                    raw_cl_text = re.sub(r"\s+", " ", raw_cl_text).strip()
                    claims.append(EvidenceClaim(
                        claim_id=c_id,
                        claim=raw_cl_text,
                        source_url=source_url,
                        source_name=prov_c.get("source_name", ""),
                        source_type=prov_c.get("source_type", "press"),
                        doc_type=prov_c.get("doc_type", "unknown"),
                        speaker=prov_c.get("speaker"),
                        date=prov_c.get("date"),
                        legal_status=prov_c.get("legal_status", "alleged"),
                        procedural_status=prov_c.get("procedural_status", "unknown"),
                        verification_status=prov_c.get("verification_status", "unverified_secondary"),
                        credibility_tier=prov_c.get("credibility_tier", "unconfirmed_claim"),
                        evidence_tier=prov_c.get("evidence_tier", "secondary"),
                        causal_role=prov_c.get("causal_role", "unknown"),
                        scope=prov_c.get("scope"),
                        mechanism=prov_c.get("mechanism"),
                        act_target=prov_c.get("act_target"),
                        confidence=prov_c.get("confidence", "low"),
                    ))
                events = []
                causal_epochs = grounding_intel.get("causal_epochs", [])
                if causal_epochs:
                    for ep_idx, ep in enumerate(causal_epochs, start=1):
                        events.append(TimelineEvent(
                            date=ep.get("time_marker") or "Undated",
                            event=f"[{ep.get('epoch_stage', '').upper()}] {ep.get('event_summary', '')}: {ep.get('verified_claim', '')}",
                            claim_ids=[claims[min(ep_idx - 1, len(claims) - 1)].claim_id] if claims else ["C001"]
                        ))
                else:
                    for idx, clm in enumerate(claims[:7], start=1):
                        events.append(TimelineEvent(
                            date=clm.date or "Undated",
                            event=clm.claim,
                            claim_ids=[clm.claim_id]
                        ))
                return claims, events

            s1_scheme = s1_payload.get("scheme_mechanism_summary") or {
                "KR": f"{topic_name} 관련 제도적·계약적 구조.",
                "JA": f"{topic_name}に関する制度的・契約的構造。",
                "VN": f"Cơ chế hợp đồng và kẽ hở quản lý xoay quanh {topic_name}.",
            }.get(market, f"Structural agreements and commercial mechanisms behind {topic_name}.")
            s1_outcome = s1_payload.get("documented_outcome") or {
                "KR": f"{topic_name}에 대한 감독 조사 및 사법 절차 진행.",
                "JA": f"{topic_name}に対する監督調査および司法手続きの推移。",
                "VN": f"Quá trình thanh tra, xử lý pháp lý và điều chỉnh tại {topic_name}.",
            }.get(market, f"Regulatory oversight, court proceedings, and valuation adjustments in {topic_name}.")
            antagonist_data = s1_payload.get("antagonist") or {}
            antagonist_name = antagonist_data.get("name") if isinstance(antagonist_data, dict) else (getattr(antagonist_data, "name", None) or topic_name.split()[0])

            if market == "KR":
                claims = [
                    EvidenceClaim(
                        claim_id="C001",
                        claim=f"공식 기업 공시 및 정부 인허가 등록 문서를 통해 {topic_name} 관련 기본 운영 구조와 사업 모델이 확인됨.",
                        source_url="https://www.korea.kr",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-02-15",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="primary_catalyst",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C002",
                        claim=f"이해관계자 간 주요 상업 계약 및 거래 구조의 실행 내역 확인: {s1_scheme}",
                        source_url="https://www.ftc.go.kr",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-03-01",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C003",
                        claim=f"{topic_name}과 직접 연계된 시장 유동성 및 재무적 변동성 급증이 확인됨.",
                        source_url="https://www.yna.co.kr",
                        source_type="press",
                        doc_type="news_article",
                        speaker="journalist",
                        date="2024-05-20",
                        legal_status="fact",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C004",
                        claim=f"감독 당국 및 금융 조사 기관이 {topic_name}에 대한 구조적 건전성 및 공시 적정성 정밀 조사에 착수함.",
                        source_url="https://www.fss.or.kr",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-08-10",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C005",
                        claim=f"{topic_name} 관련 계약 불이행 및 내부 통제 결함 의혹에 대한 민원과 피해 진정이 제기됨.",
                        source_url="https://www.scourt.go.kr",
                        source_type="court",
                        doc_type="criminal_complaint",
                        speaker="complainant",
                        date="2024-11-15",
                        legal_status="alleged",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C006",
                        claim=f"사법 당국이 {topic_name} 관련 주요 책임자 및 유관 조직에 대해 특정 혐의로 정식 수사 및 기소 절차를 진행함.",
                        source_url="https://www.scourt.go.kr",
                        source_type="court",
                        doc_type="indictment",
                        speaker="prosecutor",
                        date="2025-01-20",
                        legal_status="charged",
                        verification_status="verified_primary",
                        credibility_tier="press_allegation",
                        causal_role="transmission_mechanism",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C007",
                        claim=f"제도적 감독 조치 및 공식 법적 대응 결과 확정: {s1_outcome}",
                        source_url="https://www.korea.kr",
                        source_type="court",
                        doc_type="court_judgment",
                        speaker="court",
                        date="2025-06-30",
                        legal_status="settled",
                        verification_status="verified_primary",
                        credibility_tier="verified_fact",
                        causal_role="background_context",
                        confidence="high",
                    ),
                ]
                events = [
                    TimelineEvent(date="2024-02-15", event=f"공식 등록 공시를 통해 {topic_name} 관련 구조적 운영 개시.", claim_ids=["C001"]),
                    TimelineEvent(date="2024-03-01", event=f"{antagonist_name} 관련 주요 상업 계약 및 금융 약정 체결.", claim_ids=["C002"]),
                    TimelineEvent(date="2024-05-20", event=f"시장 유동성 축소와 함께 {topic_name} 관련 재무적 압박 가시화.", claim_ids=["C003"]),
                    TimelineEvent(date="2024-08-10", event=f"감독 당국, {topic_name}에 대한 정밀 회계 및 구조적 리스크 조사 착수.", claim_ids=["C004"]),
                    TimelineEvent(date="2024-11-15", event="계약 불이행 및 이해상충 관련 민원 제기 및 법적 분쟁 확산.", claim_ids=["C005"]),
                    TimelineEvent(date="2025-01-20", event=f"사법 기관, {topic_name} 관련 혐의로 정식 수사 및 기소.", claim_ids=["C006"]),
                    TimelineEvent(date="2025-06-30", event=f"감독 당국 공식 제재 및 제도 개선안 확정: {s1_outcome}", claim_ids=["C007"]),
                ]
            elif market == "JA":
                claims = [
                    EvidenceClaim(
                        claim_id="C001",
                        claim=f"公的企業開示および行政許認可資料により、{topic_name}の基本運営構造と事業体制が確認された。",
                        source_url="https://www.fsa.go.jp",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-02-15",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="primary_catalyst",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C002",
                        claim=f"{antagonist_name}に関わる主要契約および取引構造の履行履歴が確認された：{s1_scheme}",
                        source_url="https://www.fsa.go.jp",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-03-01",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C003",
                        claim=f"{topic_name}に直結する市場流動性の急変と財務的変動が確認された。",
                        source_url="https://www.nikkei.com",
                        source_type="press",
                        doc_type="news_article",
                        speaker="journalist",
                        date="2024-05-20",
                        legal_status="fact",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C004",
                        claim=f"監督当局および検査機関が、{topic_name}の健全性と開示の適正性について公式調査を開始した。",
                        source_url="https://www.fsa.go.jp",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-08-10",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C005",
                        claim=f"{topic_name}における契約不履行および内部統制上の問題に関する申立て・疑惑が提起された。",
                        source_url="https://www.courts.go.jp",
                        source_type="court",
                        doc_type="criminal_complaint",
                        speaker="complainant",
                        date="2024-11-15",
                        legal_status="alleged",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C006",
                        claim=f"司法当局が{topic_name}の主要関係者に対し、関連法令違反の容疑で捜査および起訴手続きを進めた。",
                        source_url="https://www.courts.go.jp",
                        source_type="court",
                        doc_type="indictment",
                        speaker="prosecutor",
                        date="2025-01-20",
                        legal_status="charged",
                        verification_status="verified_primary",
                        credibility_tier="press_allegation",
                        causal_role="transmission_mechanism",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C007",
                        claim=f"監督上の行政措置および公式な法的対応の結果が確認された：{s1_outcome}",
                        source_url="https://www.courts.go.jp",
                        source_type="court",
                        doc_type="court_judgment",
                        speaker="court",
                        date="2025-06-30",
                        legal_status="settled",
                        verification_status="verified_primary",
                        credibility_tier="verified_fact",
                        causal_role="background_context",
                        confidence="high",
                    ),
                ]
                events = [
                    TimelineEvent(date="2024-02-15", event=f"公的登録資料を通じて{topic_name}の構造的運用が開始。", claim_ids=["C001"]),
                    TimelineEvent(date="2024-03-01", event=f"{antagonist_name}に関わる主要商業契約および金融スキームを締結。", claim_ids=["C002"]),
                    TimelineEvent(date="2024-05-20", event=f"市場流동性の縮小とともに{topic_name}の財務圧迫が顕在化。", claim_ids=["C003"]),
                    TimelineEvent(date="2024-08-10", event=f"監督当局が{topic_name}に関する会計・構造リスク調査に着手。", claim_ids=["C004"]),
                    TimelineEvent(date="2024-11-15", event="契約不履行と利害衝突をめぐる申立ておよび法的紛争が拡大。", claim_ids=["C005"]),
                    TimelineEvent(date="2025-01-20", event=f"司法機関が{topic_name}関連容疑で正式な捜査・起訴へ移行。", claim_ids=["C006"]),
                    TimelineEvent(date="2025-06-30", event=f"監督当局の公式処分および制度見直しが決定：{s1_outcome}", claim_ids=["C007"]),
                ]
            elif market == "VN":
                claims = [
                    EvidenceClaim(
                        claim_id="C001",
                        claim=f"Hồ sơ công bố doanh nghiệp và giấy phép cơ quan quản lý xác nhận cấu trúc vận hành nền tảng của {topic_name}.",
                        source_url="https://chinhphu.vn",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-02-15",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="primary_catalyst",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C002",
                        claim=f"Lịch sử giao dịch và hợp đồng thương mại trọng yếu do {antagonist_name} thực hiện đã được ghi nhận: {s1_scheme}",
                        source_url="https://chinhphu.vn",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-03-01",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C003",
                        claim=f"Thanh khoản thị trường và biến động tài chính gắn trực tiếp với {topic_name} ghi nhận mức gia tăng bất thường.",
                        source_url="https://vnexpress.net",
                        source_type="press",
                        doc_type="news_article",
                        speaker="journalist",
                        date="2024-05-20",
                        legal_status="fact",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C004",
                        claim=f"Cơ quan thanh tra và giám sát tài chính đã mở cuộc kiểm tra chính thức đối với tính minh bạch công bố thông tin của {topic_name}.",
                        source_url="https://chinhphu.vn",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-08-10",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C005",
                        claim=f"Đơn khiếu nại và nghi vấn vi phạm nghĩa vụ hợp đồng cùng lỗ hổng kiểm soát nội bộ liên quan đến {topic_name} đã được tiếp nhận.",
                        source_url="https://toaan.gov.vn",
                        source_type="court",
                        doc_type="criminal_complaint",
                        speaker="complainant",
                        date="2024-11-15",
                        legal_status="alleged",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C006",
                        claim=f"Cơ quan tiến hành tố tụng đã khởi tố và truy tố các cá nhân, tổ chức liên quan đến {topic_name} về các sai phạm tài chính.",
                        source_url="https://toaan.gov.vn",
                        source_type="court",
                        doc_type="indictment",
                        speaker="prosecutor",
                        date="2025-01-20",
                        legal_status="charged",
                        verification_status="verified_primary",
                        credibility_tier="press_allegation",
                        causal_role="transmission_mechanism",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C007",
                        claim=f"Biện pháp chế tài của cơ quan quản lý và kết quả xử lý pháp lý chính thức được xác nhận: {s1_outcome}",
                        source_url="https://toaan.gov.vn",
                        source_type="court",
                        doc_type="court_judgment",
                        speaker="court",
                        date="2025-06-30",
                        legal_status="settled",
                        verification_status="verified_primary",
                        credibility_tier="verified_fact",
                        causal_role="background_context",
                        confidence="high",
                    ),
                ]
                events = [
                    TimelineEvent(date="2024-02-15", event=f"Hồ sơ đăng ký chính thức ghi nhận hoạt động ban đầu của {topic_name}.", claim_ids=["C001"]),
                    TimelineEvent(date="2024-03-01", event=f"{antagonist_name} ký kết các hợp đồng thương mại và cơ chế đòn bẩy trọng yếu.", claim_ids=["C002"]),
                    TimelineEvent(date="2024-05-20", event=f"Áp lực thanh khoản và biến động dòng tiền xuất hiện tại {topic_name}.", claim_ids=["C003"]),
                    TimelineEvent(date="2024-08-10", event=f"Cơ quan chức năng khởi động thanh tra rủi ro cấu trúc tại {topic_name}.", claim_ids=["C004"]),
                    TimelineEvent(date="2024-11-15", event="Tranh chấp hợp đồng và khiếu nại xung đột lợi ích gia tăng.", claim_ids=["C005"]),
                    TimelineEvent(date="2025-01-20", event=f"Cơ quan tố tụng tiến hành điều tra và truy tố sai phạm liên quan {topic_name}.", claim_ids=["C006"]),
                    TimelineEvent(date="2025-06-30", event=f"Quyết định xử lý và khung chấn chỉnh thể chế được ban hành: {s1_outcome}", claim_ids=["C007"]),
                ]
            else:
                claims = [
                    EvidenceClaim(
                        claim_id="C001",
                        claim=f"Official corporate filings and regulatory registration disclosures established foundational business operations for {topic_name}.",
                        source_url="https://www.sec.gov",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-02-15",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="primary_catalyst",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C002",
                        claim=f"Commercial agreements and operational risk mechanisms were executed by {antagonist_name}: {s1_scheme}",
                        source_url="https://www.sec.gov",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-03-01",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C003",
                        claim=f"Capital markets recorded intense valuation volatility and financial reallocation directly tied to {topic_name}.",
                        source_url="https://www.reuters.com",
                        source_type="press",
                        doc_type="news_article",
                        speaker="journalist",
                        date="2024-05-20",
                        legal_status="fact",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C004",
                        claim=f"Institutional supervisory agencies and examiners commenced formal reviews into contractual dependencies and market disclosure integrity for {topic_name}.",
                        source_url="https://www.sec.gov",
                        source_type="regulator",
                        doc_type="regulatory_notice",
                        speaker="regulator",
                        date="2024-08-10",
                        legal_status="fact",
                        verification_status="verified_primary",
                        credibility_tier="official_regulation",
                        causal_role="transmission_mechanism",
                        confidence="high",
                    ),
                    EvidenceClaim(
                        claim_id="C005",
                        claim=f"Civil litigation and regulatory complaints alleged material governance failures and breach of internal compliance controls surrounding {topic_name}.",
                        source_url="https://www.courtlistener.com",
                        source_type="court",
                        doc_type="criminal_complaint",
                        speaker="complainant",
                        date="2024-11-15",
                        legal_status="alleged",
                        verification_status="corroborated_secondary",
                        credibility_tier="press_allegation",
                        causal_role="background_context",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C006",
                        claim=f"Formal judicial petitions charged counterparties and responsible entities with systematic statutory and contractual breaches related to {topic_name}.",
                        source_url="https://www.courtlistener.com",
                        source_type="court",
                        doc_type="indictment",
                        speaker="prosecutor",
                        date="2025-01-20",
                        legal_status="charged",
                        verification_status="verified_primary",
                        credibility_tier="press_allegation",
                        causal_role="transmission_mechanism",
                        confidence="medium",
                    ),
                    EvidenceClaim(
                        claim_id="C007",
                        claim=f"Documented enforcement outcomes and market restructuring materialized: {s1_outcome}",
                        source_url="https://www.justice.gov",
                        source_type="court",
                        doc_type="court_judgment",
                        speaker="court",
                        date="2025-06-30",
                        legal_status="settled",
                        verification_status="verified_primary",
                        credibility_tier="verified_fact",
                        causal_role="background_context",
                        confidence="high",
                    ),
                ]
                events = [
                    TimelineEvent(date="2024-02-15", event=f"Initial filings and disclosures registered for {topic_name}.", claim_ids=["C001"]),
                    TimelineEvent(date="2024-03-01", event=f"Major commercial agreements and operational frameworks enacted by {antagonist_name}.", claim_ids=["C002"]),
                    TimelineEvent(date="2024-05-20", event=f"Market reaction and trading volatility accelerate surrounding {topic_name}.", claim_ids=["C003"]),
                    TimelineEvent(date="2024-08-10", event="Supervisory inquiries initiated regarding operational dependencies.", claim_ids=["C004"]),
                    TimelineEvent(date="2024-11-15", event="Civil complaints allege governance and compliance control failures.", claim_ids=["C005"]),
                    TimelineEvent(date="2025-01-20", event="Federal court dockets document statutory and breach-of-contract charges.", claim_ids=["C006"]),
                    TimelineEvent(date="2025-06-30", event="Final enforcement decrees, settlements, and institutional reforms concluded.", claim_ids=["C007"]),
                ]
            return claims, events

        ledger = []
        timeline = []

        if not ctx.dry_run and system_prompt:
            try:
                from app.services.model_gateway import get_global_gateway
                gateway = get_global_gateway()
                w_title = s1_art.payload.get("title_working") or topic
                c_quest = s1_art.payload.get("central_question") or f"Core structural mechanisms and liabilities underlying {topic}."
                s_summary = s1_art.payload.get("scheme_mechanism_summary") or f"Commercial agreements, regulatory dependencies, and valuation volatility surrounding {topic}."
                antag_obj = s1_art.payload.get("antagonist") or {}
                if isinstance(antag_obj, dict):
                    antag_name = antag_obj.get("name")
                elif hasattr(antag_obj, "name"):
                    antag_name = getattr(antag_obj, "name", None)
                else:
                    antag_name = None
                if not antag_name:
                    antag_name = topic.split()[0] if topic else "Corporate Target"

                doc_outcome = s1_art.payload.get("documented_outcome") or ""
                user_prompt = (
                    f"Topic: {topic}\n"
                    f"Target Market: {market}\n"
                    f"Working Title: {w_title}\n"
                    f"Central Investigative Paradox: {c_quest}\n"
                    f"Antagonist: {json.dumps({'name': antag_name, 'type': 'company'}, ensure_ascii=False)}\n"
                    f"Scheme Summary: {s_summary}\n"
                    f"Documented Outcome: {doc_outcome}\n"
                    f"Source Seeds: {json.dumps(s1_art.payload.get('source_seeds', []), ensure_ascii=False)}\n\n"
                )
                tagged_claims = []
                if grounding_intel and grounding_intel.get("claims"):
                    from app.services.story_provenance_engine import classify_claim_provenance as _classify_g_claim

                    epoch_context = " ".join(
                        f"{ep.get('event_summary', '')} {ep.get('verified_claim', '')}"
                        for ep in grounding_intel.get("causal_epochs", [])
                        if isinstance(ep, dict)
                    )
                    rel_g_claims = _filter_topically_relevant_claims(
                        grounding_intel["claims"],
                        topic=topic,
                        central_question=c_quest,
                        scheme_summary=f"{s_summary} {epoch_context}".strip(),
                        antagonist_name=antag_name,
                        market=market,
                    )
                    tagged_claims = [_classify_g_claim(gc, market=market) for gc in rel_g_claims]
                    user_prompt += (
                        f"GROUNDING INTEL CLAIMS WITH VERIFIED PROVENANCE METADATA ({len(tagged_claims)} claims):\n"
                        f"{json.dumps(tagged_claims, indent=2, ensure_ascii=False)}\n\n"
                        f"CAUSAL EPOCHS:\n"
                        f"{json.dumps(grounding_intel.get('causal_epochs', []), indent=2, ensure_ascii=False)}\n\n"
                        f"MANDATE: Preserve verification_status, doc_type, speaker, procedural_status, and scope for every claim in market '{market}'. "
                        f"NEVER convert 'unverified_secondary' / RSS claims into settled 'fact' or 'verified_primary'. "
                        "Forbid out-of-market agencies not present in the dossier. "
                        "Exclude any claim whose core subject belongs to an unrelated asset class, foreign market, or side story that merely shares a generic keyword without addressing the episode topic.\n\n"
                    )
                if market == "KR":
                    user_prompt += "MANDATE: Output all claim text and event descriptions in 100% natural Korean (Hangul).\n\n"
                elif market == "JA":
                    user_prompt += "MANDATE: Output all claim text and event descriptions in 100% natural Japanese.\n\n"
                elif market == "VN":
                    user_prompt += "MANDATE: Output all claim text and event descriptions in 100% natural Vietnamese.\n\n"
                target_claim_str = (
                    f"target {min(14, max(8, len(tagged_claims)))} distinct topically relevant claims"
                    if tagged_claims
                    else "minimum 6-8 claims"
                )
                user_prompt += (
                    "CRITICAL MANDATE FOR CLAIM TEXT:\n"
                    "- The 'claim' field must contain ONLY the direct, substantive factual statement itself (e.g. '<ENTITY> officially announced the implementation of <POLICY/MEASURE>').\n"
                    "- DO NOT write meta-commentary, audit caveats, or verification evaluations inside the 'claim' field (NEVER write 'The provided document claims that...' or 'However, ... was not confirmed').\n"
                    "- All evidentiary reservations and caveats belong EXCLUSIVELY in the metadata fields ('legal_status', 'verification_status', 'doc_type', 'confidence').\n\n"
                    f"Extract and compile an exhaustive, timestamped evidence_ledger ({target_claim_str}: C001, C002, ...) and chronological timeline strictly adhering to the schema.\n"
                    "Ensure every claim has a valid legal_status ('convicted' | 'charged' | 'alleged' | 'settled' | 'fact') and confidence ('high' | 'medium').\n"
                    "Start response immediately with { and end with }. Output ONLY valid JSON with NO conversational preamble."
                )
                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="gpt-6.1-sol",
                    system_prompt=system_prompt,
                    max_tokens=5000,
                    temperature=0.3,
                    fallback="claude-v4.1-flash"
                )
                from core.llm_json import parse_llm_json
                parsed_json = parse_llm_json(raw_response)

                from app.services.story_provenance_engine import (
                    classify_claim_provenance as _classify_llm_claim,
                )
                from app.services.story_provenance_engine import (
                    is_official_portal_name as _is_official_portal,
                )
                from app.services.story_provenance_engine import (
                    is_primary_official_domain as _is_primary_url,
                )
                from app.services.story_provenance_engine import (
                    is_reputable_press_domain as _is_reputable_press,
                )
                from app.services.story_provenance_engine import (
                    is_rss_or_aggregator_url as _is_rss_url,
                )
                from app.services.story_provenance_engine import (
                    resolve_true_publisher as _resolve_true_publisher,
                )

                # Index grounding URLs/claims so LLM cannot launder an RSS claim into verified_primary
                g_claims_raw = grounding_intel.get("claims", []) if grounding_intel else []
                raw_ledger = parsed_json.get("evidence_ledger", [])
                from app.services.story_provenance_engine import sanitize_substantive_claim_text
                for idx, c in enumerate(raw_ledger, start=1):
                    c_id = c.get("claim_id") or f"C{idx:03d}"
                    c_dict = dict(c)
                    if c_dict.get("claim"):
                        c_dict["claim"] = sanitize_substantive_claim_text(c_dict["claim"], market=market)
                    if not c_dict.get("source") and c_dict.get("source_name"):
                        c_dict["source"] = c_dict["source_name"]

                    # Cross-reference grounding_intel to anchor verified provenance before LLM classification
                    if g_claims_raw:
                        topic_words = set(re.findall(r"\w{3,}", (topic or "").lower()))
                        c_words = set(re.findall(r"\w{4,}", str(c_dict.get("claim", "")).lower()))
                        substantive_c = c_words - topic_words
                        best_gc = None
                        best_overlap = 0
                        for gc in g_claims_raw:
                            if gc.get("source_url") and gc.get("source_url") == c_dict.get("source_url"):
                                best_gc = gc
                                break
                            gc_words = set(re.findall(r"\w{4,}", str(gc.get("claim", "")).lower()))
                            substantive_gc = gc_words - topic_words
                            overlap = len(substantive_c & substantive_gc)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                best_gc = gc

                        if best_gc and (best_gc.get("source_url") == c_dict.get("source_url") or best_overlap >= 2):
                            for k in ("source", "source_url", "date", "confidence", "causal_role", "mechanism", "act_target"):
                                if best_gc.get(k) is not None:
                                    c_dict[k] = best_gc[k]
                            if best_gc.get("confidence") in ("verified", "high"):
                                c_dict.pop("procedural_status", None)
                                c_dict.pop("verification_status", None)

                    prov_c = _classify_llm_claim(c_dict, market=market)
                    # Cross-check against grounding_intel URL provenance if matching source_url is RSS
                    src_url = prov_c.get("source_url") or c.get("source_url") or ""
                    if not src_url and g_claims_raw:
                        for gc in g_claims_raw:
                            if gc.get("source") and str(gc.get("source")).lower() in str(prov_c.get("source_name", "")).lower():
                                src_url = str(gc.get("source_url") or "")
                                if src_url:
                                    break

                    src_name_check = str(prov_c.get("source_name") or c.get("source") or "").strip()
                    pub_res = _resolve_true_publisher(src_name_check, src_url)
                    src_clean = pub_res["true_source_name"]
                    prov_c["source_name"] = src_clean
                    is_off_portal = pub_res["is_official"] or _is_official_portal(src_name_check) or _is_official_portal(src_clean) or _is_primary_url(src_url)
                    is_rep_press = pub_res["is_reputable_press"] or _is_reputable_press(src_url, src_name_check) or _is_reputable_press(src_url, src_clean)

                    is_rss_hit = (pub_res["is_aggregator"] or _is_rss_url(src_url) or any(
                        _is_rss_url(str(gc.get("source_url", "")))
                        and (
                            str(gc.get("source", "")).strip().lower() in src_name_check.lower()
                            or str(gc.get("source", "")).strip().lower() in src_clean.lower()
                        )
                        for gc in g_claims_raw
                    )) and not is_off_portal and not is_rep_press

                    claim_text_check = str(prov_c.get("claim", "")).strip().lower()
                    has_press_lead = any(k in claim_text_check for k in (
                        "보도에 따르면", "언론에 따르면", "취재에 따르면", "보도됐다", "전해졌다",
                        "according to reports", "according to press", "according to media", "as reported",
                        "報道によれば", "報道によると", "theo báo", "báo chí phản ánh"
                    ))

                    if is_off_portal and not has_press_lead:
                        if any(x in (src_url + src_name_check).lower() for x in ("justice.gov", "department of justice", "antitrust division")):
                            prov_c["source_type"] = "regulator" if "antitrust" in (src_url + src_name_check).lower() else "gov"
                        else:
                            prov_c["source_type"] = "gov" if prov_c.get("source_type") not in ("court", "regulator") else prov_c.get("source_type")
                        if prov_c.get("doc_type") in ("unknown", "rss_snippet", None, ""):
                            prov_c["doc_type"] = "regulatory_notice"
                        prov_c["verification_status"] = "verified_primary"
                        prov_c["evidence_tier"] = "primary"
                        if prov_c.get("credibility_tier") in ("unconfirmed_claim", "press_allegation", None, ""):
                            prov_c["credibility_tier"] = "official_regulation"
                        prov_c["confidence"] = "high"
                    elif is_rep_press or (is_off_portal and has_press_lead):
                        prov_c["source_type"] = "press"
                        if prov_c.get("doc_type") in ("unknown", "rss_snippet", None, ""):
                            prov_c["doc_type"] = "news_article"
                        prov_c["verification_status"] = "corroborated_secondary"
                        prov_c["evidence_tier"] = "secondary"
                        prov_c["credibility_tier"] = "press_allegation"
                        if has_press_lead:
                            prov_c["legal_status"] = "alleged"
                    elif is_rss_hit:
                        # Genuinely unverified anonymous RSS snippet or unknown aggregator
                        prov_c["verification_status"] = "unverified_secondary"
                        prov_c["evidence_tier"] = "secondary"
                        prov_c["credibility_tier"] = "unconfirmed_claim"
                        prov_c["confidence"] = "low"
                        if prov_c.get("causal_role") == "primary_catalyst":
                            prov_c["causal_role"] = "background_context"

                    # Preserve explicit valid legal_status only when provenance supports it
                    llm_ls = str(c.get("legal_status", "")).lower()
                    st = prov_c["legal_status"]
                    if llm_ls in ("charged", "settled", "alleged") and prov_c["verification_status"] != "unverified_secondary":
                        st = llm_ls
                    elif llm_ls == "convicted" and prov_c.get("doc_type") == "court_judgment":
                        st = "convicted"
                    elif prov_c["verification_status"] == "unverified_secondary" and llm_ls == "fact":
                        st = "alleged"

                    raw_llm_claim = str(prov_c.get("claim") or f"Factual evidentiary claim regarding {topic}")
                    if "विकल्प" in raw_llm_claim:
                        raw_llm_claim = raw_llm_claim.replace("विकल्प", "선택권" if market == "KR" else ("選択肢" if market == "JA" else "lựa chọn"))
                    raw_llm_claim = re.sub(r"[\u0900-\u097F]+", "", raw_llm_claim)
                    raw_llm_claim = re.sub(r"\s+", " ", raw_llm_claim).strip()

                    matched_gc = None
                    if g_claims_raw:
                        for gc in g_claims_raw:
                            if gc.get("source_url") and gc.get("source_url") == src_url:
                                matched_gc = gc
                                break
                            gc_words = set(re.findall(r"\w{4,}", str(gc.get("claim", "")).lower()))
                            c_words = set(re.findall(r"\w{4,}", str(raw_llm_claim).lower()))
                            if len(gc_words & c_words) >= 2:
                                matched_gc = gc
                                break

                    final_causal_role = prov_c.get("causal_role")
                    final_mechanism = prov_c.get("mechanism") or c.get("mechanism")
                    final_act_target = prov_c.get("act_target") or c.get("act_target")

                    if matched_gc:
                        if matched_gc.get("causal_role") and (not final_causal_role or final_causal_role in ("background_context", "unknown")):
                            if prov_c.get("verification_status") in ("verified_primary", "corroborated_secondary"):
                                final_causal_role = matched_gc["causal_role"]
                        if matched_gc.get("mechanism") and not final_mechanism:
                            final_mechanism = matched_gc["mechanism"]
                        if matched_gc.get("act_target") and not final_act_target:
                            final_act_target = matched_gc["act_target"]

                    ledger.append(EvidenceClaim(
                        claim_id=c_id,
                        claim=raw_llm_claim,
                        source_url=src_url,
                        source_name=prov_c.get("source_name", ""),
                        source_type=prov_c.get("source_type", "press"),
                        doc_type=prov_c.get("doc_type", "unknown"),
                        speaker=prov_c.get("speaker"),
                        date=prov_c.get("date") or c.get("date"),
                        legal_status=st,
                        procedural_status=prov_c.get("procedural_status", "unknown"),
                        verification_status=prov_c.get("verification_status", "unverified_secondary"),
                        credibility_tier=prov_c.get("credibility_tier", "unconfirmed_claim"),
                        evidence_tier=prov_c.get("evidence_tier", "secondary"),
                        causal_role=final_causal_role or "background_context",
                        scope=prov_c.get("scope"),
                        mechanism=final_mechanism,
                        act_target=final_act_target,
                        confidence=prov_c.get("confidence", "low"),
                    ))

                if ctx.dry_run and doc_outcome and len(ledger) < 4:
                    outcome_covered = any(
                        len(set(c.claim.lower().split()) & set(doc_outcome.lower().split())) >= 4
                        for c in ledger
                    )
                    if not outcome_covered:
                        c_id = f"C{len(ledger) + 1:03d}"
                        out_prov = _classify_llm_claim(
                            {"claim": doc_outcome, "source": "Ideation Synthesis", "source_url": ""},
                            market=market,
                        )
                        ledger.append(EvidenceClaim(
                            claim_id=c_id,
                            claim=doc_outcome,
                            source_url=out_prov.get("source_url") or "",
                            source_name=out_prov.get("source_name") or "Ideation Synthesis",
                            source_type=out_prov.get("source_type", "press"),
                            doc_type=out_prov.get("doc_type", "commentary"),
                            speaker=out_prov.get("speaker"),
                            date=out_prov.get("date"),
                            legal_status=out_prov.get("legal_status", "alleged"),
                            procedural_status=out_prov.get("procedural_status", "unknown"),
                            verification_status=out_prov.get("verification_status", "unverified_secondary"),
                            credibility_tier=out_prov.get("credibility_tier", "unconfirmed_claim"),
                            evidence_tier=out_prov.get("evidence_tier", "secondary"),
                            causal_role=out_prov.get("causal_role", "background_context"),
                            scope=out_prov.get("scope"),
                            confidence=out_prov.get("confidence", "low"),
                        ))

                raw_timeline = parsed_json.get("timeline", [])
                valid_cids = {c.claim_id for c in ledger}
                for t in raw_timeline:
                    t_cids = [cid for cid in t.get("claim_ids", []) if cid in valid_cids]
                    if not t_cids and ledger:
                        t_cids = [ledger[0].claim_id]
                    timeline.append(TimelineEvent(
                        date=t.get("date", "2026-01-01"),
                        event=t.get("event", f"Key event in {topic} timeline"),
                        claim_ids=t_cids,
                    ))
            except Exception as _research_err:
                import logging
                logging.getLogger(__name__).warning(f"[S02_RESEARCH] LLM research call failed: {_research_err}, using resilient dynamic evidence ledger.")
                ledger = []
                timeline = []

        if not ledger:
            if not ctx.dry_run:
                if grounding_intel and grounding_intel.get("claims"):
                    from app.services.story_provenance_engine import (
                        classify_claim_provenance as _classify_g_fallback,
                    )

                    for idx_g, gc in enumerate(grounding_intel.get("claims", [])[:8], start=1):
                        prov_g = _classify_g_fallback(gc, market=market)
                        cid_g = f"C{idx_g:03d}"
                        ledger.append(EvidenceClaim(
                            claim_id=cid_g,
                            claim=prov_g.get("claim") or str(gc.get("claim") or f"Documented record on {topic}"),
                            source_url=prov_g.get("source_url") or str(gc.get("source_url") or ""),
                            source_name=prov_g.get("source_name") or str(gc.get("source") or ""),
                            source_type=prov_g.get("source_type", "press"),
                            doc_type=prov_g.get("doc_type", "unknown"),
                            speaker=prov_g.get("speaker"),
                            date=prov_g.get("date") or gc.get("date"),
                            legal_status=prov_g.get("legal_status", "alleged"),
                            procedural_status=prov_g.get("procedural_status", "unknown"),
                            verification_status=prov_g.get("verification_status", "unverified_secondary"),
                            credibility_tier=prov_g.get("credibility_tier", "unconfirmed_claim"),
                            evidence_tier=prov_g.get("evidence_tier", "secondary"),
                            causal_role=prov_g.get("causal_role", "unknown"),
                            scope=prov_g.get("scope"),
                            mechanism=gc.get("mechanism"),
                            act_target=gc.get("act_target"),
                            confidence=prov_g.get("confidence", "low"),
                        ))
                        timeline.append(TimelineEvent(
                            date=str(prov_g.get("date") or "2026-01-01"),
                            event=str(prov_g.get("claim") or "")[:140],
                            claim_ids=[cid_g],
                        ))
                else:
                    raise RuntimeError(
                        "[S02_RESEARCH] Live research failed and no grounding_intel claims are available; "
                        "refusing to fabricate verified_primary claims in production (Rule 118)."
                    )
            else:
                ledger, timeline = _build_generic_evidence_ledger(topic, s1_art.payload)

        # Build dynamic factsheet anchors from S1 payload early so topical relevance filter can use them
        s1_scheme = s1_art.payload.get("scheme_mechanism_summary") or f"Systemic mechanisms and operational dependencies underlying {topic}."
        central_q = s1_art.payload.get("central_question") or f"Core investigative paradox regarding {topic}."
        antagonist_data = s1_art.payload.get("antagonist") or {}
        antagonist_name = (antagonist_data.get("name") if isinstance(antagonist_data, dict) else getattr(antagonist_data, "name", None)) or (topic.split()[0] if topic else "Corporate Target")

        if ledger:
            from app.services.story_provenance_engine import (
                corroborate_evidence_ledger,
                credibility_tier_rank,
                verification_priority_rank,
            )

            corr_dicts = corroborate_evidence_ledger([c.model_dump() for c in ledger], market=market)
            for idx_c, c_dict in enumerate(corr_dicts):
                ledger[idx_c].verification_status = c_dict.get("verification_status", ledger[idx_c].verification_status)
                ledger[idx_c].credibility_tier = c_dict.get("credibility_tier", ledger[idx_c].credibility_tier)
                ledger[idx_c].evidence_tier = c_dict.get("evidence_tier", ledger[idx_c].evidence_tier)
                ledger[idx_c].confidence = c_dict.get("confidence", ledger[idx_c].confidence)
                ledger[idx_c].source_type = c_dict.get("source_type", ledger[idx_c].source_type)
                if c_dict.get("doc_type") and c_dict.get("doc_type") != "unknown":
                    ledger[idx_c].doc_type = c_dict.get("doc_type")

            ledger = _filter_topically_relevant_claims(
                ledger,
                topic=topic,
                central_question=central_q,
                scheme_summary=s1_scheme,
                antagonist_name=antagonist_name,
                market=market,
            )

            ledger.sort(
                key=lambda x: (
                    credibility_tier_rank(getattr(x, "credibility_tier", "unconfirmed_claim")),
                    verification_priority_rank(getattr(x, "verification_status", "unverified_secondary")),
                    0 if getattr(x, "causal_role", "") == "primary_catalyst" else (1 if getattr(x, "causal_role", "") == "transmission_mechanism" else 2),
                )
            )

            kept_cids = {c.claim_id for c in ledger}
            if timeline and kept_cids:
                cleaned_tl: List[TimelineEvent] = []
                for te in timeline:
                    valid_te_cids = [cid for cid in (te.claim_ids or []) if cid in kept_cids]
                    if valid_te_cids:
                        te.claim_ids = valid_te_cids
                        cleaned_tl.append(te)
                timeline = cleaned_tl

        # Extract dynamic key entities from claims, grounding intel, and antagonist
        extracted_entities = [antagonist_name] if antagonist_name else []
        if grounding_intel:
            for c in grounding_intel.get("claims", []):
                s_name = c.get("source")
                if s_name and s_name not in extracted_entities and len(extracted_entities) < 4:
                    extracted_entities.append(s_name)
        if len(extracted_entities) < 3:
            if market == "KR":
                extracted_entities.extend(["감독 당국", "시장 거래 상대방"])
            elif market == "JA":
                extracted_entities.extend(["監督当局", "取引相手方"])
            elif market == "VN":
                extracted_entities.extend(["Cơ quan giám sát", "Đối tác thị trường"])
            else:
                extracted_entities.extend(["Regulatory Authorities", "Market Counterparties"])
        extracted_entities = list(dict.fromkeys(extracted_entities))[:4]

        # Market-aware verified anchor, metric, and competitor vacuums
        if market == "KR":
            v_anchor = f"{topic} 공식 검증 실증 분석 자료"
            g_metric = f"{len(ledger)}건의 공공 기록 및 언론 검증 팩트체크 완료"
            comp_vacs = [
                f"기존 언론은 단순 표면적 갈등만 다루며 {topic}의 본질적 메커니즘 분석 부재.",
                f"핵심 모순을 해결하는 심층적인 제도적·금융적 실증 분석 부재: {central_q}"
            ]
        elif market == "JA":
            v_anchor = f"{topic} 公式検証実証分析資料"
            g_metric = f"{len(ledger)}件の公式記録および報道検証ファクトチェック完了"
            comp_vacs = [
                f"既存メディアは表面的な対立のみを報じ、{topic}の本質的メカニズムの分析が欠落。",
                f"根本的矛盾を解明する制度的・金融的実証分析の不在：{central_q}"
            ]
        elif market == "VN":
            v_anchor = f"Hồ sơ phân tích thực chứng đã xác minh về {topic}"
            g_metric = f"{len(ledger)} tuyên bố chứng cứ được xác thực từ hồ sơ công khai và báo chí."
            comp_vacs = [
                f"Truyền thông truyền thống chỉ đưa tin bề nổi mà thiếu phân tích bản chất cơ chế của {topic}.",
                f"Thiếu vắng phân tích pháp lý và tài chính giải mã nghịch lý cốt lõi: {central_q}"
            ]
        else:
            v_anchor = f"Forensic Evidence Ledger Audit on {topic}"
            g_metric = f"{len(ledger)} corroborated evidentiary claims from public records and investigative press."
            comp_vacs = [
                f"Competitors cover superficial headlines without mechanical analysis of {topic}.",
                f"Zero forensic breakdown resolving the core paradox: {central_q}"
            ]

        story_research = StoryResearchPayload(
            preset=preset_raw if preset_raw in ("story_forensic", "vox_narrative") else "story_forensic",
            topic=topic,
            evidence_ledger=ledger,
            timeline=timeline,
            task_id=ctx.run_id,
            market=market,
            factsheet={
                "verified_anchor": v_anchor,
                "key_entities": extracted_entities,
                "core_mechanism": s1_scheme,
                "ground_truth_metric": g_metric,
            },
            competitor_vacuums=comp_vacs,
            status="APPROVED",
        )
        from app.services.story_provenance_engine import summarize_evidence_provenance

        payload = story_research.model_dump()
        payload["evidence_summary"] = summarize_evidence_provenance(payload.get("evidence_ledger", []))
    else:
        payload = {
            "task_id": ctx.run_id,
            "market": market,
            "topic": topic,
            "factsheet": {
                "verified_anchor": f"Baseline documentary inquiry into {topic}",
                "key_entities": ["Primary Subject", "Oversight Authority", "Affected Stakeholders"],
                "core_mechanism": f"Structural mechanics and institutional dynamics underlying {topic}.",
                "ground_truth_metric": "Pending verified ledger compilation."
            },
            "competitor_vacuums": [
                "Competitors only cover superficial headlines without technical mechanics.",
                "Lack of source-verified causal breakdown."
            ],
            "status": "APPROVED"
        }

    prov = Provenance(
        generator="stages.s02_research",
        latency_sec=round(time.time() - start_ts, 2)
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=prov
    )

    stale_feedback = ctx.paths.root / "s04_critic_feedback.json"
    if stale_feedback.is_file():
        stale_feedback.unlink(missing_ok=True)

    emit_artifact(artifact, ctx.paths)
    return artifact
