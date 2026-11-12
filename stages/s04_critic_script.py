#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stages/s04_critic_script.py — Stage S4: Dual-LLM & Forensic Script Critic Council (AVF-STAB-001).

Implements Stage Shape Standard. Enforces un-tautological TTS duration calibration,
full legal/procedural/verification attribution, strict target-market script & institutional
purity, generic multi-market grounding, proportional causal claim-alignment auditing,
and calibrated rubric scoring (Rule 118, Rule 128, Rule 130, Rule 139).
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from typing import Any, Dict, List, Set

from core.config import RunContext
from core.contracts.stages import CouncilDecision, CriticVerdict, Provenance, StageArtifact, StageID
from core.gates import emit_artifact, require_input
from tools.codemap.runtime import pipeline_stage

logger = logging.getLogger(__name__)

STAGE: StageID = StageID.S4_CRITIC_SCRIPT

_GENERIC_ACRONYM_ALLOWLIST = {"KRW", "USD", "JPY", "VND", "EUR", "GDP", "CPI", "IPO", "ETF", "LTV", "SEC", "FTC"}


def _detect_repetitive_explainer_filler(lines: List[Dict[str, Any]]) -> bool:
    """Detect boilerplate template filler, repetitive openings, or legal disclaimers padded across beats."""
    import math

    texts = [str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()]
    if len(texts) < 6:
        return False

    # Strip legitimate single-clause 'settled' disclaimer suffixes before checking tail repetition
    cleaned_for_tails = [
        re.sub(
            r"\s*\((?:공식적인 잘못을 인정하지 않고 합의됨|違法性を認めることなく和解|dàn xếp mà không thừa nhận hành vi sai trái|settled without admitting wrongdoing)\)\s*$",
            "",
            t,
        ).strip()
        for t in texts
    ]

    unique_cids = {str(cid) for ln in lines for cid in (ln.get("claim_ids") or []) if cid}
    # Allow unavoidable reuse when a small synthetic ledger (<6 claims) is expanded to target video duration
    tail_threshold = max(3, math.ceil(len(texts) / len(unique_cids)) + 1) if (0 < len(unique_cids) < 6) else 3

    # Check if identical normalized sentence tails (>= 18 chars) repeat beyond threshold across script
    tails = [re.sub(r"\s+", " ", t[-26:]) for t in cleaned_for_tails if len(t) >= 26]
    tail_counts = Counter(tails)
    if any(cnt >= tail_threshold for cnt in tail_counts.values()):
        return True

    # Check if identical normalized sentence openings (>= 22 chars) repeat monotonically on normal ledgers (>=6 claims or unmapped)
    if len(unique_cids) == 0 or len(unique_cids) >= 6:
        heads = [re.sub(r"\s+", " ", t[:22]) for t in texts if len(t) >= 22]
        head_counts = Counter(heads)
        if any(cnt >= max(6, int(len(texts) * 0.60)) for cnt in head_counts.values()):
            return True

    # Check generic video/meta-explainer filler phrases
    filler_patterns = [
        r"이\s*영상은\s*단순\s*정보",
        r"투자\s*판단의\s*책임은",
        r"오늘\s*이\s*영상에서는",
        r"구독과\s*좋아요",
        r"この動画は投資助言",
        r"チャンネル登録",
        r"video này chỉ mang tính",
        r"đừng quên đăng ký kênh",
        r"this video is for informational purposes only",
        r"not financial advice",
        r"before we dive in,?\s+hit subscribe",
    ]
    filler_hits = sum(1 for t in texts if any(re.search(pat, t, re.IGNORECASE) for pat in filler_patterns))
    return filler_hits >= 2


@pipeline_stage(
    id="s04_critic_script",
    order=4,
    name="Critic Council Script Audit",
    input_model="StageArtifact",
    output_model="StageArtifact",
    triggers=["stage:s03_script"],
    upstream=["s03_script"],
    downstream=["s05_director_plan"],
    artifacts=["runs/{run_id}/s04_critic_script/artifact.json"],
    verify_cmds=["python -m orchestrator.run_pipeline --only s04_critic_script --profile e2e_min"],
)
def run(ctx: RunContext) -> StageArtifact:
    """Executes Stage S4: Script Critic Council Audit."""
    start_ts = time.time()
    s3_art = require_input(STAGE, ctx.paths)
    scenes = s3_art.payload.get("scenes", [])

    preset_raw = (
        (getattr(ctx.preset, "name", ctx.preset) if ctx.preset else getattr(getattr(ctx, "manifest", None), "preset", None))
        or "story_forensic"
    )
    is_story = bool(preset_raw in ("story_forensic", "vox_narrative"))
    all_gates_pass = True
    critic_payload = None
    violations: List[Dict[str, Any]] = []

    if is_story:
        from app.schemas.story_contracts import StoryCriticViolation, StoryScriptCriticGates, StoryScriptCriticPayload
        from app.services.story_provenance_engine import (
            GENERIC_FORENSIC_CONCEPTS,
            HANGUL_SYLLABLE_RE,
            JP_KANA_RE,
            VN_DIACRITIC_RE,
            audit_statement_claim_alignment,
            check_market_entity_appropriateness,
            check_target_market_language_purity,
            compute_calibrated_script_score,
            extract_claim_elements,
            line_matches_expected_qualifier,
            localize_dates_and_metrics,
            normalize_market_code,
            summarize_evidence_provenance,
        )
        from core.pacing_budgeter import estimate_script_speech_duration

        beats = s3_art.payload.get("beats", [])
        evidence_raw = s3_art.payload.get("evidence_ledger", [])
        evidence_list: List[Dict[str, Any]] = [
            (c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else {}))
            for c in evidence_raw
        ]
        evidence_map: Dict[str, Dict[str, Any]] = {
            str(c["claim_id"]): c for c in evidence_list if "claim_id" in c
        }

        raw_market = s3_art.payload.get("market") or getattr(ctx.manifest, "market", None) or "EN"
        market = normalize_market_code(raw_market)
        topic = str(s3_art.payload.get("topic", ""))
        statement_claim_map = s3_art.payload.get("statement_claim_map")

        total_words = int(s3_art.payload.get("total_words", 0))
        self_est_dur = float(s3_art.payload.get("est_duration_s", 0.0))

        preset_obj = ctx.preset if hasattr(ctx.preset, "duration_window_s") else None
        if not preset_obj:
            try:
                from app.services.preset_loader import load_preset

                preset_obj = load_preset(preset_raw)
            except Exception:
                preset_obj = None

        all_lines = [ln for b in beats for ln in b.get("lines", []) if isinstance(ln, dict)]
        all_line_texts = [str(ln.get("text", "")).strip() for ln in all_lines if str(ln.get("text", "")).strip()]
        all_text = " ".join(all_line_texts)

        # ------------------------------------------------------------------
        # Gate 1: Un-Tautological TTS Duration & Spoken-Unit Budget Window
        # ------------------------------------------------------------------
        measured_timing = estimate_script_speech_duration(
            all_line_texts,
            market=market,
            docudrama_tempo=True,
        )
        measured_dur = float(measured_timing["estimated_duration_sec"])
        measured_units = int(measured_timing["spoken_units"])
        unit_type = str(measured_timing["unit_type"])

        d_min = float(preset_obj.duration_window_s.min) if (preset_obj and hasattr(preset_obj, "duration_window_s")) else 180.0
        d_max = float(preset_obj.duration_window_s.max) if (preset_obj and hasattr(preset_obj, "duration_window_s")) else 300.0

        # Market-calibrated spoken-unit bounds corresponding to ~180s-300s docudrama pacing
        if market == "KR":
            u_min, u_max = 750, 1550
        elif market == "JA":
            u_min, u_max = 900, 1950
        elif market == "VN":
            u_min, u_max = 360, 750
        else:
            wb = getattr(getattr(preset_obj, "narration", None), "word_budget", None)
            u_min = int(getattr(wb, "min", 430) or 430)
            u_max = int(getattr(wb, "max", 580) or 580)

        duration_ok = True
        drift_s = abs(self_est_dur - measured_dur)
        max_allowed_drift = max(30.0, measured_dur * 0.25)
        if self_est_dur > 0 and drift_s > max_allowed_drift:
            duration_ok = False
            violations.append({
                "line_id": None,
                "gate": "duration_estimate_in_window",
                "detail": (
                    f"Self-reported est_duration_s={self_est_dur:.1f}s diverges from measured "
                    f"TTS timing={measured_dur:.1f}s ({measured_units} {unit_type}) by {drift_s:.1f}s."
                ),
            })
        if not (u_min <= measured_units <= u_max) or not (d_min <= measured_dur <= d_max):
            duration_ok = False
            violations.append({
                "line_id": None,
                "gate": "duration_estimate_in_window",
                "detail": (
                    f"Measured TTS duration {measured_dur:.1f}s (window {d_min:.0f}-{d_max:.0f}s) "
                    f"or spoken units {measured_units} {unit_type} (window {u_min}-{u_max}) out of bounds."
                ),
            })

        # ------------------------------------------------------------------
        # Gate 2: Every factual line has valid claim_id(s)
        # Gate 3: Legal, procedural & verification qualifiers match provenance
        # ------------------------------------------------------------------
        claims_ok = True
        legal_ok = True
        for b in beats:
            for ln in b.get("lines", []):
                line_id = str(ln.get("line_id", ""))
                text = str(ln.get("text", ""))
                c_ids = ln.get("claim_ids", []) or []
                if not c_ids:
                    claims_ok = False
                    violations.append({
                        "line_id": line_id,
                        "gate": "every_factual_line_has_claim_id",
                        "detail": f"Line '{line_id}' has no claim_ids anchored to evidence ledger.",
                    })
                    continue

                for cid in c_ids:
                    claim = evidence_map.get(str(cid))
                    if not claim:
                        claims_ok = False
                        violations.append({
                            "line_id": line_id,
                            "gate": "every_factual_line_has_claim_id",
                            "detail": f"Claim ID '{cid}' in line '{line_id}' not found in evidence_ledger.",
                        })
                    else:
                        ok_q, reason_q = line_matches_expected_qualifier(text, claim, market=market)
                        if not ok_q:
                            legal_ok = False
                            violations.append({
                                "line_id": line_id,
                                "gate": "legal_language_matches_status",
                                "detail": f"Line '{line_id}' ({cid}): {reason_q}",
                            })

        # ------------------------------------------------------------------
        # Gate 4: Hook within time cap & 3+ micro-scenes decomposition
        # ------------------------------------------------------------------
        hook_ok = True
        if beats and len(beats) != 5:
            hook_ok = False
            violations.append({
                "line_id": "B1",
                "gate": "hook_within_20s",
                "detail": f"Story forensic script must contain exactly 5 narrative beats (found {len(beats)}).",
            })
        if beats:
            b1 = beats[0]
            b1_lines = [ln for ln in b1.get("lines", []) if isinstance(ln, dict)]
            b1_timing = estimate_script_speech_duration(
                [str(ln.get("text", "")) for ln in b1_lines],
                market=market,
                docudrama_tempo=True,
            )
            b1_measured_dur = float(b1_timing["estimated_duration_sec"])
            b1_reported_dur = float(b1.get("target_duration_s", 0) or 0)
            if max(b1_measured_dur, b1_reported_dur) > 28.0 or b1_reported_dur > 25.0:
                hook_ok = False
                violations.append({
                    "line_id": "B1",
                    "gate": "hook_within_20s",
                    "detail": (
                        f"Hook beat duration exceeds threshold: target={b1_reported_dur:.1f}s, "
                        f"measured={b1_measured_dur:.1f}s."
                    ),
                })
            if len(b1_lines) < 3:
                hook_ok = False
                violations.append({
                    "line_id": "B1",
                    "gate": "hook_within_20s",
                    "detail": f"Beat 1 Hook must contain 3-4 distinct micro-scenes (found {len(b1_lines)}).",
                })

        # ------------------------------------------------------------------
        # Gate 5: Pattern interrupt gap <= max_gap_s (using TTS-normalized time)
        # ------------------------------------------------------------------
        pattern_ok = True
        max_gap = float(preset_obj.retention.pattern_interrupt_max_gap_s) if (preset_obj and hasattr(preset_obj, "retention")) else 30.0
        curr_gap = 0.0
        for b in beats:
            for ln in b.get("lines", []):
                ln_text = str(ln.get("text", ""))
                ln_dur = float(
                    estimate_script_speech_duration([ln_text], market=market, docudrama_tempo=True)["estimated_duration_sec"]
                )
                curr_gap += max(1.0, ln_dur)
                if ln.get("visual_hook") and ln.get("visual_hook") != "none":
                    curr_gap = 0.0
                elif curr_gap > max_gap:
                    pattern_ok = False
                    violations.append({
                        "line_id": ln.get("line_id"),
                        "gate": "pattern_interrupt_gap_ok",
                        "detail": f"Pattern interrupt gap {curr_gap:.1f}s exceeded {max_gap}s at {ln.get('line_id')}.",
                    })

        # ------------------------------------------------------------------
        # Gate 6A: Target Market Script/Language Purity (EN/KR/JA/VN bidirectional)
        # Gate 6B: Market Institutional & Currency Appropriateness
        # ------------------------------------------------------------------
        grounded_proper_nouns: Set[str] = set(_GENERIC_ACRONYM_ALLOWLIST)
        for token in re.findall(r"\b[A-Z][A-Za-z0-9&\-]{1,}\b", topic):
            grounded_proper_nouns.add(token)
        for c_dict in evidence_list:
            elems = extract_claim_elements(str(c_dict.get("claim", "")))
            for ent in elems.get("entities", []):
                grounded_proper_nouns.add(ent)
            for token in re.findall(r"\b[A-Z][A-Za-z0-9&\-]{1,}\b", str(c_dict.get("source_name", ""))):
                grounded_proper_nouns.add(token)

        language_ok, lang_issues = check_target_market_language_purity(
            all_text,
            market=market,
            grounded_proper_nouns=grounded_proper_nouns,
        )
        for issue in lang_issues:
            violations.append({
                "line_id": None,
                "gate": "target_market_language_compliance",
                "detail": issue,
            })

        entity_fit_ok, entity_fit_issues = check_market_entity_appropriateness(
            all_text,
            market=market,
            evidence_ledger=evidence_list,
            topic=topic,
        )
        for issue in entity_fit_issues:
            violations.append({
                "line_id": None,
                "gate": "market_entity_appropriateness",
                "detail": issue,
            })

        # ------------------------------------------------------------------
        # Gate 7: Generic Topic Specificity Gate (Zero Hardcoded Episode Terms)
        # ------------------------------------------------------------------
        topic_specificity_ok = True
        evidence_entities: Set[str] = set()
        evidence_metrics: Set[str] = set()
        evidence_domain_stems: Set[str] = set()

        for c_dict in evidence_list:
            c_text = str(c_dict.get("claim", ""))
            elems = extract_claim_elements(c_text)
            for ent in elems.get("entities", []):
                evidence_entities.add(ent.lower())
            for met in elems.get("metrics", []) + elems.get("dates", []):
                clean_m = met.strip().lower()
                if clean_m:
                    evidence_metrics.add(clean_m)
            for st_tok in elems.get("stems", []):
                if len(st_tok) >= 3:
                    evidence_domain_stems.add(st_tok)

        all_text_lower = all_text.lower()
        all_text_nospace = re.sub(r"[,\s]+", "", all_text_lower)

        def _term_present(term: str) -> bool:
            t_norm = re.sub(r"[,\s]+", "", term)
            return bool(term in all_text_lower or (len(t_norm) >= 2 and t_norm in all_text_nospace))

        def _metric_present(m_tok: str) -> bool:
            if _term_present(m_tok):
                return True
            loc_m = localize_dates_and_metrics(m_tok, market).strip().lower()
            return bool(loc_m and _term_present(loc_m))

        def _stem_present(st_tok: str) -> bool:
            if st_tok in all_text_lower:
                return True
            if st_tok in GENERIC_FORENSIC_CONCEPTS:
                for lang_terms in GENERIC_FORENSIC_CONCEPTS[st_tok].values():
                    if any(lt.lower() in all_text_lower for lt in lang_terms):
                        return True
            return False

        matched_entities = [e for e in evidence_entities if _term_present(e)]
        matched_metrics = [m_tok for m_tok in evidence_metrics if _metric_present(m_tok)]
        matched_stems = [st_tok for st_tok in evidence_domain_stems if _stem_present(st_tok)]

        # In cross-script markets (e.g. EN evidence synthesized cleanly into KR/JA/VN),
        # check native entities & short acronyms rather than forcing unlocalized Latin proper phrases.
        is_cross_script_synth = False
        if market in ("KR", "JA", "VN") and evidence_entities:
            native_entities = [
                e for e in evidence_entities
                if HANGUL_SYLLABLE_RE.search(e)
                or JP_KANA_RE.search(e)
                or VN_DIACRITIC_RE.search(e)
                or re.fullmatch(r"[a-z0-9&\-]{2,8}", e)
            ]
            if len(native_entities) < len(evidence_entities) and len(matched_stems) >= 3:
                is_cross_script_synth = True

        min_req_entities = min(3, len(evidence_entities)) if evidence_entities else 0
        min_req_metrics = min(1, len(evidence_metrics)) if evidence_metrics else 0

        if evidence_entities and len(matched_entities) < min_req_entities and not is_cross_script_synth:
            # Allow high-specificity ledger domain stems only if explicit institutional entities < 3
            if len(evidence_entities) < 3 and (len(matched_entities) + len(matched_stems)) >= 3:
                pass
            else:
                topic_specificity_ok = False
                violations.append({
                    "line_id": None,
                    "gate": "topic_specificity_gate",
                    "detail": (
                        f"Script failed topic specificity: found {len(matched_entities)} concrete ledger entities "
                        f"(minimum {min_req_entities} required)."
                    ),
                })
        elif not evidence_entities and len(evidence_domain_stems) >= 3 and len(matched_stems) < 3:
            topic_specificity_ok = False
            violations.append({
                "line_id": None,
                "gate": "topic_specificity_gate",
                "detail": f"Script failed topic specificity: matched only {len(matched_stems)} domain concepts from ledger.",
            })

        if evidence_metrics and len(matched_metrics) < min_req_metrics:
            topic_specificity_ok = False
            violations.append({
                "line_id": None,
                "gate": "topic_specificity_gate",
                "detail": (
                    f"Script failed topic specificity: found {len(matched_metrics)} quantitative metrics/dates "
                    f"(minimum {min_req_metrics} required)."
                ),
            })

        # ------------------------------------------------------------------
        # Gate 8: Proportional Coverage, Catalyst/Mechanism Priority, Polarity & Statement-Claim Audit
        # ------------------------------------------------------------------
        claim_audit = audit_statement_claim_alignment(
            beats=beats,
            evidence_ledger=evidence_list,
            statement_claim_map=statement_claim_map,
            market=market,
        )
        claim_coverage_ok = bool(claim_audit["passed"])

        if not claim_audit["coverage_ok"]:
            violations.append({
                "line_id": None,
                "gate": "claim_coverage_gate",
                "detail": (
                    f"Claim coverage insufficient: substantively covered "
                    f"{claim_audit['substantive_covered_count']}/{claim_audit['total_claims']} "
                    f"({claim_audit['coverage_ratio']:.0%}, minimum 60% required)."
                ),
            })
        if not claim_audit["catalysts_ok"]:
            violations.append({
                "line_id": None,
                "gate": "claim_coverage_gate",
                "detail": (
                    f"Primary catalyst coverage incomplete: covered "
                    f"{claim_audit['verified_catalysts_covered']}/{claim_audit['verified_catalysts_total']} "
                    "verified catalysts (100% required)."
                ),
            })
        if not claim_audit["mechanisms_ok"]:
            violations.append({
                "line_id": None,
                "gate": "claim_coverage_gate",
                "detail": (
                    f"Transmission mechanism coverage incomplete: covered "
                    f"{claim_audit['verified_mechanisms_covered']}/{claim_audit['verified_mechanisms_total']} "
                    "verified mechanisms (>=75% required)."
                ),
            })
        if claim_audit["beat1_unverified_elevation"]:
            violations.append({
                "line_id": "B1",
                "gate": "claim_coverage_gate",
                "detail": "Beat 1 opening hook premise relies solely on an unverified secondary claim without verified anchor.",
            })
        for pm in claim_audit.get("polarity_mismatches", []):
            violations.append({
                "line_id": None,
                "gate": "claim_coverage_gate",
                "detail": pm,
            })
        for ugap in claim_audit.get("unverified_attribution_gaps", []):
            legal_ok = False
            violations.append({
                "line_id": None,
                "gate": "legal_language_matches_status",
                "detail": ugap,
            })

        # Guard against per-line dummy citation padding on lines lacking any claim overlap
        hollow_line_citations = 0
        total_line_citations = 0
        for ln in all_lines:
            ln_txt = str(ln.get("text", ""))
            for cid in ln.get("claim_ids", []) or []:
                cl_obj = evidence_map.get(str(cid))
                if cl_obj is None:
                    continue
                total_line_citations += 1
                from app.services.story_provenance_engine import has_entity_or_metric_signal

                ok_sig, _ = has_entity_or_metric_signal(
                    ln_txt,
                    extract_claim_elements(str(cl_obj.get("claim", ""))),
                    min_stem_hits=1,
                )
                if not ok_sig:
                    hollow_line_citations += 1

        if total_line_citations > 0 and (hollow_line_citations / total_line_citations) > 0.40:
            claim_coverage_ok = False
            violations.append({
                "line_id": None,
                "gate": "claim_coverage_gate",
                "detail": (
                    f"Excessive hollow citations: {hollow_line_citations}/{total_line_citations} line citations "
                    "lack factual entity, numeric metric, or keyword overlap."
                ),
            })

        has_explainer_filler = _detect_repetitive_explainer_filler(all_lines)
        if has_explainer_filler:
            pattern_ok = False
            violations.append({
                "line_id": None,
                "gate": "pattern_interrupt_gap_ok",
                "detail": "Repetitive explainer disclaimer/filler phrasing detected across script beats.",
            })

        prov_summary = summarize_evidence_provenance(evidence_list)
        unverified_dossier_block = bool(
            len(evidence_list) >= 8
            and prov_summary.get("verified_primary", 0) == 0
            and float(prov_summary.get("verified_or_corroborated_ratio", 0.0)) < 0.30
        )
        if unverified_dossier_block:
            violations.append({
                "line_id": None,
                "gate": "topic_specificity_gate",
                "detail": (
                    f"Insufficient primary/corroborated grounding: {prov_summary.get('verified_primary', 0)} primary, "
                    f"{prov_summary.get('verified_or_corroborated_ratio', 0.0):.0%} corroborated across {len(evidence_list)} claims."
                ),
            })

        # ------------------------------------------------------------------
        # Active LLM Critic Evaluation via model_gateway (Live Runs Only)
        # ------------------------------------------------------------------
        llm_verdict = None
        llm_score = None
        llm_feedback: List[str] = []
        if not ctx.dry_run:
            try:
                from app.services.model_gateway import get_global_gateway
                from core.llm_json import parse_llm_json

                gateway = get_global_gateway()
                prompt_file = ctx.paths.repo_root / "config" / "prompts" / "story_forensic" / "s04_critic_script.md"
                system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else ""
                if system_prompt:
                    script_summary = {
                        "market": market,
                        "topic": topic,
                        "total_words": total_words,
                        "measured_spoken_units": measured_units,
                        "measured_unit_type": unit_type,
                        "self_est_duration_s": self_est_dur,
                        "measured_speech_duration_s": measured_dur,
                        "statement_claim_audit": claim_audit,
                        "beats": beats,
                    }
                    user_prompt = (
                        f"Target Market: {market}\n"
                        f"Script Under Audit:\n{json.dumps(script_summary, indent=2, ensure_ascii=False)}\n\n"
                        f"Evidence Ledger:\n{json.dumps(evidence_list, indent=2, ensure_ascii=False)}\n\n"
                        "Audit the script against all evaluation gates (duration/TTS sync, provenance verification, "
                        "legal/procedural qualifier specificity, script/institutional purity, causal polarity & claim coverage).\n"
                        "Output ONLY a single valid JSON block starting with { and ending with }."
                    )
                    raw_resp = gateway.call_llm(
                        prompt=user_prompt,
                        model="gpt-6.1-sol",
                        system_prompt=system_prompt,
                        max_tokens=2500,
                        temperature=0.2,
                        timeout=120.0,
                        fallback="claude-v4.1-flash",
                    )
                    parsed_critic = parse_llm_json(raw_resp)
                    if isinstance(parsed_critic, list):
                        parsed_critic = parsed_critic[0] if parsed_critic and isinstance(parsed_critic[0], dict) else {}
                    if not isinstance(parsed_critic, dict):
                        parsed_critic = {}

                    raw_verdict = str(parsed_critic.get("verdict", "")).strip().lower()
                    if raw_verdict in ("fail", "rejected"):
                        llm_verdict = "fail"
                    elif raw_verdict == "revise":
                        llm_verdict = "revise"
                    elif raw_verdict in ("pass", "approved"):
                        llm_verdict = "pass"

                    if parsed_critic.get("aggregate_score") is not None:
                        llm_score = float(parsed_critic["aggregate_score"])

                    if isinstance(parsed_critic.get("gates"), dict):
                        g_map = parsed_critic["gates"]
                        if g_map.get("duration_estimate_in_window") is False:
                            duration_ok = False
                        if g_map.get("every_factual_line_has_claim_id") is False:
                            claims_ok = False
                        if g_map.get("legal_language_matches_status") is False:
                            legal_ok = False
                        if g_map.get("hook_within_20s") is False:
                            hook_ok = False
                        if g_map.get("pattern_interrupt_gap_ok") is False:
                            pattern_ok = False
                        if g_map.get("target_market_language_compliance") is False:
                            language_ok = False
                        if g_map.get("market_entity_appropriateness") is False:
                            entity_fit_ok = False
                        if g_map.get("topic_specificity_gate") is False:
                            topic_specificity_ok = False
                        if g_map.get("claim_coverage_gate") is False or g_map.get("statement_claim_alignment_ok") is False:
                            claim_coverage_ok = False

                    for v in parsed_critic.get("violations", []):
                        if isinstance(v, dict) and v.get("gate"):
                            violations.append(v)
                    for feed in parsed_critic.get("feedback", []):
                        llm_feedback.append(str(feed))
            except Exception as _llm_err:
                logger.warning(f"[S04_CRITIC] Live LLM critic evaluation unavailable: {_llm_err}")
                llm_verdict = None
                llm_score = None

        programmatic_pass = bool(
            duration_ok
            and claims_ok
            and legal_ok
            and hook_ok
            and pattern_ok
            and language_ok
            and entity_fit_ok
            and topic_specificity_ok
            and claim_coverage_ok
            and bool(claim_audit["passed"])
        )

        gates_dict: Dict[str, bool] = {
            "duration_estimate_in_window": duration_ok,
            "every_factual_line_has_claim_id": claims_ok,
            "legal_language_matches_status": legal_ok,
            "hook_within_20s": hook_ok,
            "pattern_interrupt_gap_ok": pattern_ok,
            "target_market_language_compliance": language_ok,
            "market_entity_appropriateness": entity_fit_ok,
            "topic_specificity_gate": topic_specificity_ok,
            "claim_coverage_gate": claim_coverage_ok,
            "statement_claim_alignment_ok": bool(claim_audit["passed"]),
        }

        calibrated = compute_calibrated_script_score(
            gates=gates_dict,
            evidence_ledger=evidence_list,
            claim_audit=claim_audit,
            violations_count=len(violations),
            has_explainer_filler=has_explainer_filler,
        )
        rubric_score = float(calibrated["aggregate_score"])

        if not programmatic_pass:
            verdict_str = "fail"
            if llm_score is not None:
                agg_score = min(rubric_score, float(llm_score), 6.5)
                score_source = "llm_critic_capped"
            else:
                agg_score = rubric_score
                score_source = "deterministic_calibrated_rubric"
        elif unverified_dossier_block:
            verdict_str = "revise"
            agg_score = min(rubric_score, 7.2)
            score_source = "deterministic_calibrated_rubric"
        elif llm_verdict in ("fail", "revise"):
            verdict_str = llm_verdict
            agg_score = min(float(llm_score) if llm_score is not None else rubric_score, 7.2)
            score_source = "llm_critic"
        elif llm_score is not None:
            verdict_str = "pass"
            agg_score = round(float(llm_score), 2)
            score_source = "llm_critic"
        else:
            verdict_str = "pass"
            agg_score = rubric_score
            score_source = "deterministic_calibrated_rubric"

        all_gates_pass = verdict_str == "pass"

        critic_payload = StoryScriptCriticPayload(
            verdict=verdict_str,
            gates=StoryScriptCriticGates(**gates_dict),
            violations=[StoryCriticViolation(**v) for v in violations],
            aggregate_score=agg_score,
        )
        payload = critic_payload.model_dump()
        payload["round_number"] = 1
        payload["max_rounds"] = ctx.config.limits.critic_max_rounds
        payload["score_source"] = score_source
        payload["score_breakdown"] = calibrated["breakdown"]
        payload["measured_speech_duration_s"] = measured_dur
        payload["measured_spoken_units"] = measured_units
        payload["measured_unit_type"] = unit_type
        payload["statement_claim_audit"] = claim_audit
        payload["evidence_provenance_summary"] = summarize_evidence_provenance(evidence_list)
        payload["llm_feedback"] = llm_feedback

        bd = calibrated["breakdown"]
        legal_score = round(min(9.5, (bd.get("legal_procedural_precision", 0.0) / 1.5) * 9.0), 1) if (claims_ok and legal_ok) else 4.2
        retention_score = round(min(9.5, (bd.get("structure_pacing_and_tts", 0.0) / 2.0) * 8.8), 1) if (duration_ok and hook_ok and pattern_ok) else 4.5
        market_lang_score = round(min(9.5, (bd.get("language_and_market_fit", 0.0) / 1.5) * 9.0), 1) if (language_ok and entity_fit_ok) else 3.8
        topic_score = round(min(9.5, (bd.get("evidence_provenance_quality", 0.0) / 2.5) * 8.8), 1) if topic_specificity_ok else 3.8
        claim_cov_score = round(min(9.5, (bd.get("claim_coverage_alignment", 0.0) / 2.5) * 9.0), 1) if claim_coverage_ok else 3.8

        payload["verdicts"] = [
            {
                "critic_id": "Legal-Compliance-Gate",
                "role": "Legal & Provenance Verification",
                "score": legal_score,
                "verdict": "pass" if (claims_ok and legal_ok) else "fail",
                "feedback": ["All factual lines anchored with provenance-matched procedural qualifiers."]
                if (claims_ok and legal_ok)
                else ["Unanchored claims, missing procedural attribution, or unverified elevation detected."],
            },
            {
                "critic_id": "Retention-Pacing-Gate",
                "role": "TTS Pacing & Docudrama Structure",
                "score": retention_score,
                "verdict": "pass" if (duration_ok and hook_ok and pattern_ok and not has_explainer_filler) else "fail",
                "feedback": [f"TTS-normalized pacing verified ({measured_dur:.1f}s, {measured_units} {unit_type})."]
                if (duration_ok and hook_ok and pattern_ok and not has_explainer_filler)
                else ["TTS duration drift, oversized hook, pattern gap, or explainer filler detected."],
            },
            {
                "critic_id": "Market-Language-Gate",
                "role": "Target Market Script & Institutional Purity",
                "score": market_lang_score,
                "verdict": "pass" if (language_ok and entity_fit_ok) else "fail",
                "feedback": [f"Target script purity and institutional fit verified for {market}."]
                if (language_ok and entity_fit_ok)
                else (lang_issues + entity_fit_issues)[:3],
            },
            {
                "critic_id": "Topic-Specificity-Gate",
                "role": "Forensic Grounding & Topic Anchoring",
                "score": topic_score,
                "verdict": "pass" if topic_specificity_ok else "fail",
                "feedback": ["Concrete ledger entities, metrics, and dates verified in script."]
                if topic_specificity_ok
                else ["Script lacks required grounded entities or quantitative metrics from evidence ledger."],
            },
            {
                "critic_id": "Claim-Coverage-Gate",
                "role": "Causal Alignment & Proportional Claim Coverage",
                "score": claim_cov_score,
                "verdict": "pass" if claim_coverage_ok else "fail",
                "feedback": [
                    f"Substantive coverage {claim_audit['coverage_ratio']:.0%}; primary catalysts & alignment verified."
                ]
                if claim_coverage_ok
                else ["Insufficient claim coverage, missing primary catalyst/mechanism, or polarity mismatch."],
            },
        ]

    # Non-story preset calibrated dry-run path
    elif ctx.dry_run or not scenes:
        scene_count = len(scenes)
        avg_words = round(sum(len(str(s.get("narration", "")).split()) for s in scenes) / max(1, scene_count), 1)
        calib_score = round(min(8.4, 5.5 + (0.4 * min(scene_count, 5)) + (0.9 if avg_words >= 8 else 0.2)), 2)
        decision = CouncilDecision(
            round_number=1,
            max_rounds=ctx.config.limits.critic_max_rounds,
            verdict="pass" if scene_count > 0 else "revise",
            aggregate_score=calib_score if scene_count > 0 else 4.0,
            verdicts=[
                CriticVerdict(
                    critic_id="Calibrated-DryRun-Audit",
                    role="Structural Dry-Run Gate",
                    score=calib_score if scene_count > 0 else 4.0,
                    verdict="pass" if scene_count > 0 else "revise",
                    feedback=[f"Dry-run calibration across {scene_count} scenes (avg {avg_words} words/scene)."],
                ),
            ],
            revision_directives=[] if scene_count > 0 else ["No scenes supplied to S04 critic."],
        )
        payload = decision.model_dump()
        payload["score_source"] = "dry_run_calibrated"
    else:
        # Live non-story preset path: fail-closed on exception instead of fake approval
        try:
            from app.services.vox_critic_council import run_dual_critic_review

            brief_scenes = [
                {
                    "scene_id": s.get("scene_id"),
                    "sentence": s.get("narration"),
                    "headline": s.get("headline"),
                    "visual_metaphor": s.get("visual_metaphor"),
                }
                for s in scenes
            ]
            review_res = run_dual_critic_review(brief_scenes, max_rounds=ctx.config.limits.critic_max_rounds)
            verdict_val = "pass" if review_res.get("verdict") == "PASS" else "revise"
            score_val = float(review_res["score"]) if review_res.get("score") is not None else 0.0
            decision = CouncilDecision(
                round_number=1,
                max_rounds=ctx.config.limits.critic_max_rounds,
                verdict=verdict_val,
                aggregate_score=score_val,
                verdicts=[
                    CriticVerdict(
                        critic_id="Critic-Council",
                        role="Audit Reviewer",
                        score=score_val,
                        verdict=verdict_val,
                        feedback=review_res.get("feedback", []),
                    )
                ],
                revision_directives=review_res.get("feedback", []),
            )
            score_src = "llm_critic"
        except Exception as exc:
            logger.error(f"[S04_CRITIC] Non-story dual critic council failed: {exc}")
            decision = CouncilDecision(
                round_number=1,
                max_rounds=ctx.config.limits.critic_max_rounds,
                verdict="revise",
                aggregate_score=0.0,
                verdicts=[],
                revision_directives=[f"Dual critic service error (fail-closed): {exc}"],
            )
            score_src = "critic_error"
        payload = decision.model_dump()
        payload["score_source"] = score_src

    prov = Provenance(
        generator="stages.s04_critic_script",
        latency_sec=round(time.time() - start_ts, 2),
    )

    artifact = StageArtifact(
        run_id=ctx.run_id,
        stage=STAGE,
        status="ok",
        payload=payload,
        provenance=prov,
    )

    emit_artifact(artifact, ctx.paths)

    if is_story and not all_gates_pass:
        from core.gates import GateError

        raise GateError(
            STAGE,
            f"Stage S04 Script Critic rejected script with {len(violations)} violation(s). Verdict='{critic_payload.verdict}'",
            details={"violations": violations, "gates": critic_payload.gates.model_dump()},
        )

    return artifact
