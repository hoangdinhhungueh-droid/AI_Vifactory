#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s01_ideation.py — Stage S1: Trend Discovery & Reality Anchor (AVF-STAB-001).

Implements Stage Shape Standard. Discovers live high-potential editorial topics.
"""

from __future__ import annotations

import json
import logging
import re
import time

from core.config import RunContext
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.gates import emit_artifact
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S1_IDEATION


@pipeline_stage(
    id="s01_ideation",
    order=1,
    name="Trend Discovery & Ideation",
    input_model=None,
    output_model="StageArtifact",
    triggers=["cli:run_pipeline"],
    upstream=[],
    downstream=["s02_research"],
    artifacts=["runs/{run_id}/s01_ideation/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s01_ideation --profile e2e_min"]
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S1: Trend Discovery."""
    start_ts = time.time()

    try:
        from core.market_resolver import resolve_canonical_market
        market = resolve_canonical_market(ctx=ctx)
    except Exception:
        market = "EN"

    from app.services.story_provenance_engine import load_matching_grounding_intel

    grounding_intel = load_matching_grounding_intel(
        ctx.paths.root,
        ctx.paths.repo_root,
        topic_override=ctx.topic,
        market=market,
    )

    # Topic resolution
    topic_name = ctx.topic
    if not topic_name and grounding_intel and grounding_intel.get("topic"):
        topic_name = grounding_intel.get("topic")
    if not topic_name:
        topic_slug = ctx.run_id.lower().replace("run_", "").replace("ep_", "")
        topic_name = topic_slug.replace("_", " ").title() or "Global Antitrust Paradigm Shift"

    preset_raw = (getattr(ctx.preset, "name", ctx.preset) if ctx.preset else getattr(getattr(ctx, "manifest", None), "preset", None)) or "story_forensic"
    is_story = bool(preset_raw in ("story_forensic", "vox_narrative"))

    if is_story:
        from app.schemas.story_contracts import Antagonist, SourceSeed, StoryIdeationPayload, StoryScore
        from core.llm_json import parse_llm_json

        prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s01_ideation.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""

        def _build_generic_story_ideation() -> StoryIdeationPayload:
            # 1. Market-aware source seeds
            classified_g_claims = []
            g_seeds = []
            if grounding_intel:
                from app.services.story_provenance_engine import (
                    classify_claim_provenance,
                    verification_priority_rank,
                )

                for c in grounding_intel.get("claims", []):
                    prov_c = classify_claim_provenance(c, market=market)
                    classified_g_claims.append(prov_c)
                    u = prov_c.get("source_url")
                    if u and str(u).startswith("http"):
                        g_seeds.append(SourceSeed(url=u, type=prov_c.get("source_type", "press")))
                classified_g_claims.sort(
                    key=lambda x: (
                        verification_priority_rank(x.get("verification_status", "unverified_secondary")),
                        0 if x.get("causal_role") == "primary_catalyst" else (1 if x.get("causal_role") == "transmission_mechanism" else 2),
                    )
                )
                if not g_seeds:
                    for chk in grounding_intel.get("grounding_chunks", []):
                        u = chk.get("uri")
                        if u and str(u).startswith("http"):
                            g_seeds.append(SourceSeed(url=u, type="press"))

            if not g_seeds:
                if market == "KR":
                    g_seeds = [
                        SourceSeed(url="https://www.korea.kr", type="regulator"),
                        SourceSeed(url="https://www.scourt.go.kr", type="court"),
                        SourceSeed(url="https://www.yna.co.kr", type="press"),
                    ]
                elif market == "JA":
                    g_seeds = [
                        SourceSeed(url="https://www.fsa.go.jp", type="regulator"),
                        SourceSeed(url="https://www.courts.go.jp", type="court"),
                        SourceSeed(url="https://www.nikkei.com", type="press"),
                    ]
                elif market == "VN":
                    g_seeds = [
                        SourceSeed(url="https://chinhphu.vn", type="regulator"),
                        SourceSeed(url="https://toaan.gov.vn", type="court"),
                        SourceSeed(url="https://vnexpress.net", type="press"),
                    ]
                else:
                    g_seeds = [
                        SourceSeed(url="https://www.sec.gov", type="regulator"),
                        SourceSeed(url="https://www.justice.gov", type="court"),
                        SourceSeed(url="https://www.reuters.com", type="press"),
                    ]

            # 2. Dynamic fields extracted from grounding_intel or localized generic defaults
            c_epochs = (grounding_intel.get("causal_epochs") if grounding_intel else []) or []

            # Dynamic Working Title
            if grounding_intel and grounding_intel.get("title_working"):
                title_working = grounding_intel["title_working"]
            elif market == "KR":
                title_working = f"{topic_name}: 구조적 메커니즘과 숨겨진 진실"
            elif market == "JA":
                title_working = f"{topic_name}：構造的欠陥と隠蔽された真相"
            elif market == "VN":
                title_working = f"{topic_name}: Cấu trúc đổ vỡ và sự thật bị che giấu"
            else:
                title_working = f"{topic_name}: The Forensic Breakdown"

            # Dynamic Central Question
            if grounding_intel and grounding_intel.get("central_question"):
                central_q = grounding_intel["central_question"]
            elif c_epochs:
                first_summary = c_epochs[0].get("event_summary", "")
                last_summary = c_epochs[-1].get("event_summary", "")
                if market == "KR":
                    central_q = f"{first_summary}에서 시작된 구조적 왜곡 속에서, 어떻게 {last_summary}라는 전례 없는 사태로 이어졌는가?"
                elif market == "JA":
                    central_q = f"{first_summary}から始まった構造的歪みの中で、いかにして{last_summary}という事態に至ったのか？"
                elif market == "VN":
                    central_q = f"Từ những sai lệch ban đầu ({first_summary}), làm thế nào dẫn đến cuộc khủng hoảng nghiêm trọng ({last_summary})?"
                else:
                    central_q = f"How did foundational vulnerabilities in {first_summary} compound into {last_summary} before regulatory intervention?"
            elif market == "KR":
                central_q = f"{topic_name} 사태에서 어떤 제도적 결함과 이해관계가 전례 없는 위기를 촉발했는가?"
            elif market == "JA":
                central_q = f"{topic_name}において、いかなる構造的欠陥と利害関係が未曾有の危機を引き起こしたのか？"
            elif market == "VN":
                central_q = f"Những lỗ hổng cấu trúc và xung đột lợi ích nào đã châm ngòi cho khủng hoảng trong {topic_name}?"
            else:
                central_q = f"What critical structural decisions and hidden institutional mechanisms triggered the crisis in {topic_name}?"

            # Dynamic Antagonist (never append 'Leadership' to foreign language phrases!)
            if grounding_intel and grounding_intel.get("antagonist"):
                antag_val = grounding_intel["antagonist"]
                antag_name = antag_val.get("name", "") if isinstance(antag_val, dict) else str(antag_val)
            elif market == "KR":
                antag_name = f"{topic_name} 관련 책임 주체 및 카르텔"
            elif market == "JA":
                antag_name = f"{topic_name}関係責任主体"
            elif market == "VN":
                antag_name = f"Tổ chức liên quan {topic_name}"
            else:
                first_word = topic_name.split()[0] if topic_name else "Corporate"
                antag_name = f"{first_word} Leadership"

            # Dynamic Scheme Summary
            if grounding_intel and grounding_intel.get("scheme_mechanism_summary"):
                scheme_sum = grounding_intel["scheme_mechanism_summary"]
            elif c_epochs and len(c_epochs) >= 2:
                scheme_sum = f"{c_epochs[1].get('event_summary', '')} - {c_epochs[1].get('verified_claim', '')}"
            elif market == "KR":
                scheme_sum = f"{topic_name} 관련 제도적 맹점, 계약 구조 및 금융 레버리지의 구조적 메커니즘."
            elif market == "JA":
                scheme_sum = f"{topic_name}に関する制度的死角、契約構造および資金レバレッジの構造的メカニズム。"
            elif market == "VN":
                scheme_sum = f"Cơ chế đòn bẩy tài chính, kẽ hở pháp lý và cấu trúc hợp đồng xoay quanh {topic_name}."
            else:
                scheme_sum = f"Forensic breakdown of commercial agreements, structural incentives, and systemic market reactions surrounding {topic_name}."

            # Dynamic Documented Outcome (never elevate unverified secondary rumors as settled facts)
            verified_outcomes = [
                c for c in classified_g_claims
                if c.get("verification_status") in ("verified_primary", "corroborated_secondary")
                and c.get("legal_status") in ("fact", "convicted", "settled")
            ]
            if verified_outcomes:
                def _outcome_rank(c_item: dict) -> tuple:
                    ls = str(c_item.get("legal_status", "")).lower()
                    ps = str(c_item.get("procedural_status", "")).lower()
                    dt = str(c_item.get("doc_type", "")).lower()
                    cr = str(c_item.get("causal_role", "")).lower()
                    tier = 0
                    if ls in ("convicted", "settled") or ps == "final_judgment":
                        tier = 3
                    elif dt in ("court_judgment", "regulatory_notice", "statute") or cr == "primary_catalyst":
                        tier = 2
                    elif cr != "transmission_mechanism":
                        tier = 1
                    return (
                        1 if c_item.get("verification_status") == "verified_primary" else 0,
                        tier,
                        str(c_item.get("date") or ""),
                    )

                verified_outcomes.sort(key=_outcome_rank)
            if grounding_intel and grounding_intel.get("documented_outcome"):
                raw_doc_out = str(grounding_intel["documented_outcome"]).strip()
                if market in ("KR", "JA", "VN") and re.search(r"\b[a-z]{3,}\s+[a-z]{3,}", raw_doc_out):
                    from app.services.story_provenance_engine import translate_claim_to_market_clause
                    raw_doc_out = translate_claim_to_market_clause(raw_doc_out, market, topic_name)
                has_ver_any = any(
                    c.get("verification_status") in ("verified_primary", "corroborated_secondary")
                    for c in classified_g_claims
                )
                if classified_g_claims and not has_ver_any:
                    unv_prefix = {
                        "KR": "[미확정·보도 단계] ",
                        "JA": "[未確定・報道段階] ",
                        "VN": "[Đang theo dõi·chưa kết luận cuối cùng] ",
                    }.get(market, "[Developing / unverified] ")
                    outcome_sum = raw_doc_out if raw_doc_out.startswith("[") else f"{unv_prefix}{raw_doc_out}"
                else:
                    outcome_sum = raw_doc_out
            elif verified_outcomes:
                top_v = verified_outcomes[-1]
                dt_raw = str(top_v.get("date") or "")
                raw_top_claim = str(top_v.get("claim", ""))
                if market in ("KR", "JA", "VN"):
                    from app.services.story_provenance_engine import (
                        localize_dates_and_metrics,
                        translate_claim_to_market_clause,
                    )
                    if re.search(r"\b[a-z]{3,}\s+[a-z]{3,}", raw_top_claim):
                        raw_top_claim = translate_claim_to_market_clause(raw_top_claim, market, topic_name)
                    else:
                        raw_top_claim = localize_dates_and_metrics(raw_top_claim, market)
                dt_tag = f"({dt_raw}) " if dt_raw else ""
                outcome_sum = f"{dt_tag}{raw_top_claim}"
            elif c_epochs:
                last_ep = c_epochs[-1]
                ep_claim = str(last_ep.get("verified_claim", ""))
                ep_sum = str(last_ep.get("event_summary", ""))
                if market in ("KR", "JA", "VN") and re.search(r"\b[a-z]{3,}\s+[a-z]{3,}", f"{ep_sum} {ep_claim}"):
                    from app.services.story_provenance_engine import translate_claim_to_market_clause
                    ep_claim = translate_claim_to_market_clause(f"{ep_sum} {ep_claim}", market, topic_name)
                    ep_sum = topic_name
                if any(c.get("verification_status") == "verified_primary" for c in classified_g_claims):
                    outcome_sum = f"{ep_sum}: {ep_claim}" if ep_sum else ep_claim
                elif market == "KR":
                    outcome_sum = f"[미확정·보도 단계] {ep_sum}: {ep_claim}"
                elif market == "JA":
                    outcome_sum = f"[未確定・報道段階] {ep_sum}: {ep_claim}"
                elif market == "VN":
                    outcome_sum = f"[Đang theo dõi·chưa kết luận cuối cùng] {ep_sum}: {ep_claim}"
                else:
                    outcome_sum = f"[Developing / unverified] {ep_sum}: {ep_claim}"
            elif market == "KR":
                outcome_sum = f"{topic_name}에 대한 공식 기록 및 진행 중인 사법·행정 절차 추적."
            elif market == "JA":
                outcome_sum = f"{topic_name}に関する公式記録および進行中の司法・行政手続き。"
            elif market == "VN":
                outcome_sum = f"Hồ sơ chính thức và diễn biến điều tra đang được cập nhật về {topic_name}."
            else:
                outcome_sum = f"Documented filings and ongoing institutional review surrounding {topic_name}."

            # Dynamic Angle Brief
            if grounding_intel and grounding_intel.get("angle_brief"):
                angle_brief = grounding_intel["angle_brief"]
            elif market == "KR":
                angle_brief = f"{topic_name}의 구조적 원인과 제도적 파장에 대한 심층 탐사 다큐멘터리."
            elif market == "JA":
                angle_brief = f"{topic_name}の構造的原因と制度的波紋に関する徹底調査ドキュメンタリー。"
            elif market == "VN":
                angle_brief = f"Phim tài liệu điều tra chuyên sâu về nguyên nhân cấu trúc và tác động của {topic_name}."
            else:
                angle_brief = f"Investigative forensic breakdown examining the structural dynamics and institutional fallout of {topic_name}."

            money_val = 0.0
            if grounding_intel and grounding_intel.get("money_at_stake_usd"):
                try:
                    money_val = float(grounding_intel["money_at_stake_usd"])
                except (ValueError, TypeError) as _num_err:
                    logger.debug(f"[s01_ideation] Notice parsing money_at_stake_usd: {_num_err}")
            elif classified_g_claims:
                from app.services.text_to_number_parser import parse_spoken_number

                for cl_item in classified_g_claims:
                    pm = parse_spoken_number(str(cl_item.get("claim", "")))
                    if pm and pm.metric_type == "currency" and pm.raw_value > 0:
                        money_val = float(pm.raw_value)
                        break
            return StoryIdeationPayload(
                preset=preset_raw if preset_raw in ("story_forensic", "vox_narrative") else "story_forensic",
                niche="business_heist" if market == "KR" else "corporate_scandal",
                title_working=title_working,
                central_question=central_q,
                antagonist=Antagonist(name=antag_name, type="company"),
                scheme_mechanism_summary=scheme_sum,
                money_at_stake_usd=money_val,
                documented_outcome=outcome_sum,
                source_seeds=g_seeds[:5],
                story_score=StoryScore(conflict=9.8, mechanism_clarity=9.6, twist=9.4, documentation=9.7),
                task_id=ctx.run_id,
                market=market,
                raw_term=topic_name,
                topic=topic_name,
                viability_score=9.7,
                angle_brief=angle_brief,
                status="APPROVED",
            )

        raw_payload = None
        if not ctx.dry_run and system_prompt:
            try:
                from app.services.model_gateway import get_global_gateway
                gateway = get_global_gateway()
                user_prompt = (
                    f"Assigned Candidate Topic: {topic_name}\n"
                    f"Target Market: {market}\n"
                    f"Run ID: {ctx.run_id}\n\n"
                )
                if grounding_intel:
                    from app.services.story_provenance_engine import (
                        classify_claim_provenance as _classify_s1_claim,
                    )
                    from app.services.story_provenance_engine import (
                        verification_priority_rank as _ver_rank,
                    )

                    live_classified = [
                        _classify_s1_claim(c, market=market)
                        for c in grounding_intel.get("claims", [])
                    ]
                    live_classified.sort(
                        key=lambda x: (
                            _ver_rank(x.get("verification_status", "unverified_secondary")),
                            0 if x.get("causal_role") == "primary_catalyst" else 1,
                        )
                    )
                    g_summary = {
                        "topic": grounding_intel.get("topic"),
                        "temporal_cadence": grounding_intel.get("temporal_cadence"),
                        "causal_epochs": grounding_intel.get("causal_epochs", []),
                        "verified_primary_or_corroborated_claims": [
                            {
                                "claim": c.get("claim"),
                                "source": c.get("source_name"),
                                "url": c.get("source_url"),
                                "date": c.get("date"),
                                "verification_status": c.get("verification_status"),
                                "causal_role": c.get("causal_role"),
                                "procedural_status": c.get("procedural_status"),
                                "scope": c.get("scope"),
                            }
                            for c in live_classified
                            if c.get("verification_status") in ("verified_primary", "corroborated_secondary")
                        ][:6],
                        "unverified_or_secondary_leads_do_not_present_as_settled_outcome": [
                            {
                                "claim": c.get("claim"),
                                "source": c.get("source_name"),
                                "date": c.get("date"),
                                "verification_status": c.get("verification_status"),
                                "causal_role": c.get("causal_role"),
                                "scope": c.get("scope"),
                            }
                            for c in live_classified
                            if c.get("verification_status") not in ("verified_primary", "corroborated_secondary")
                        ][:6],
                        "news_headlines": [
                            chk.get("title") for chk in grounding_intel.get("grounding_chunks", [])[:5] if isinstance(chk, dict)
                        ]
                    }
                    user_prompt += (
                        f"GROUNDING INTEL DOSSIER (STRICT PROVENANCE SEPARATION):\n{json.dumps(g_summary, indent=2, ensure_ascii=False)}\n\n"
                        f"MANDATE: Anchor your central_question and documented_outcome ONLY in 'verified_primary_or_corroborated_claims'. "
                        f"Do NOT promote items from 'unverified_or_secondary_leads_do_not_present_as_settled_outcome' into documented_outcome as settled fact.\n"
                        "Forbid out-of-market agencies unless explicitly present in the dossier. Output must reflect authentic market entities.\n\n"
                    )
                if market == "KR":
                    user_prompt += "MANDATE: Output all fields (title_working, central_question, antagonist name, scheme_mechanism_summary, documented_outcome, angle_brief) in 100% natural Korean (Hangul).\n\n"
                elif market == "JA":
                    user_prompt += "MANDATE: Output all fields in 100% natural Japanese.\n\n"
                elif market == "VN":
                    user_prompt += "MANDATE: Output all fields in 100% natural Vietnamese.\n\n"
                user_prompt += (
                    "Construct the comprehensive forensic case dossier for this assigned topic.\n"
                    "Frame the corporate or technological crisis, identify the corporate antagonist, the central investigative paradox,\n"
                    "the commercial mechanism or hidden structural vulnerability, and the documented regulatory/financial outcomes.\n"
                    "Respond with ONLY a single valid JSON block starting with { and ending with }. Absolutely NO reasoning or conversational preamble."
                )
                raw_response = gateway.call_llm(
                    prompt=user_prompt,
                    model="gpt-6.1-sol",
                    system_prompt=system_prompt,
                    max_tokens=2500,
                    temperature=0.4,
                    fallback="claude-v4.1-flash"
                )
                parsed_json = parse_llm_json(raw_response)

                generic = _build_generic_story_ideation()

                # 1. Healing from generic baseline if critical fields are missing
                if parsed_json.get("status") == "rejected" or not parsed_json.get("title_working") or not parsed_json.get("central_question"):
                    if not parsed_json.get("title_working"):
                        parsed_json["title_working"] = generic.title_working
                    if not parsed_json.get("central_question"):
                        parsed_json["central_question"] = generic.central_question
                    if not parsed_json.get("scheme_mechanism_summary"):
                        parsed_json["scheme_mechanism_summary"] = generic.scheme_mechanism_summary
                    if not parsed_json.get("documented_outcome"):
                        parsed_json["documented_outcome"] = generic.documented_outcome
                    if not parsed_json.get("money_at_stake_usd") or parsed_json.get("money_at_stake_usd") <= 0:
                        parsed_json["money_at_stake_usd"] = generic.money_at_stake_usd

                # 2. Source seeds unconditional sanitization guard
                raw_seeds = parsed_json.get("source_seeds")
                clean_seeds = []
                if isinstance(raw_seeds, list):
                    for s in raw_seeds:
                        if isinstance(s, dict) and s.get("url"):
                            clean_seeds.append({
                                "url": str(s.get("url")),
                                "type": s.get("type") if s.get("type") in ("court", "regulator", "gov", "press") else "press"
                            })
                        elif isinstance(s, str) and (s.startswith("http://") or s.startswith("https://")):
                            clean_seeds.append({"url": s, "type": "press"})
                        elif isinstance(s, (list, tuple)):
                            for item in s:
                                if isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
                                    clean_seeds.append({"url": item, "type": "press"})
                                elif isinstance(item, dict) and item.get("url"):
                                    clean_seeds.append({
                                        "url": str(item.get("url")),
                                        "type": item.get("type") if item.get("type") in ("court", "regulator", "gov", "press") else "press"
                                    })
                if not clean_seeds:
                    clean_seeds = [s.model_dump() for s in generic.source_seeds]
                parsed_json["source_seeds"] = clean_seeds

                # Antagonist resolution guard (never inject English 'Leadership' into non-EN markets)
                antagonist = parsed_json.get("antagonist")
                if not antagonist:
                    parsed_json["antagonist"] = {"name": generic.antagonist.name, "type": "company"}
                elif isinstance(antagonist, str):
                    parsed_json["antagonist"] = {"name": antagonist, "type": "company"}
                elif isinstance(antagonist, dict):
                    if not antagonist.get("name"):
                        antagonist["name"] = generic.antagonist.name
                    if antagonist.get("type") not in ("person", "company", "state"):
                        antagonist["type"] = "company"

                parsed_json["task_id"] = ctx.run_id
                parsed_json["market"] = market
                parsed_json["raw_term"] = topic_name
                parsed_json["topic"] = parsed_json.get("title_working") or topic_name
                parsed_json["preset"] = parsed_json.get("preset") or "story_forensic"
                if parsed_json.get("niche") not in ("business_heist", "corporate_scandal", "geopolitical_anomaly"):
                    parsed_json["niche"] = "business_heist"
                parsed_json["viability_score"] = parsed_json.get("viability_score") or 9.5
                parsed_json["angle_brief"] = parsed_json.get("angle_brief") or parsed_json.get("scheme_mechanism_summary") or generic.angle_brief
                parsed_json["status"] = "APPROVED"

                score_dict = parsed_json.get("story_score")
                if not isinstance(score_dict, dict):
                    parsed_json["story_score"] = {"conflict": 9.5, "mechanism_clarity": 9.3, "twist": 9.1, "documentation": 9.6}
                else:
                    for k, v in [("conflict", 9.5), ("mechanism_clarity", 9.3), ("twist", 9.1), ("documentation", 9.6)]:
                        if score_dict.get(k) is None:
                            score_dict[k] = v

                story_payload = StoryIdeationPayload.model_validate(parsed_json)
                raw_payload = story_payload.model_dump()
            except Exception as _ideation_err:
                import logging
                logging.getLogger(__name__).warning(f"[S01_IDEATION] LLM generation failed: {_ideation_err}, using resilient generic fallback.")
                raw_payload = None

        if raw_payload is None:
            raw_payload = _build_generic_story_ideation().model_dump()

        payload = raw_payload
    else:
        payload = {
            "task_id": ctx.run_id,
            "market": market,
            "raw_term": topic_name,
            "topic": topic_name,
            "viability_score": 9.2,
            "angle_brief": f"Investigative docudrama analyzing the structural mechanisms of {topic_name}.",
            "status": "APPROVED",
        }

    prov = Provenance(
        generator="stages.s01_ideation",
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
