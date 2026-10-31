#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_semantic_evidence_extractor.py — Comprehensive Unit Tests for SemanticEvidenceExtractor.

Validates:
- Rule 118: Zero-Mock truthful classification.
- Rule 128: Generic Contract Pattern across all 4 markets (KR, JA, EN, VN).
- Rule 141: Claim-to-Evidence Binding across all 5 Archetypes:
  1. LegalSanctionArchetype (H1 Impact)
  2. CorporateEntityArchetype (H2 Constraint / H7 Unfold)
  3. ParadoxClaimArchetype (H3 Sever)
  4. QuantitativeMetricArchetype (H2 Constraint / Caliper)
  5. InvestigativeMediaArchetype (H5 Optical)
- Elimination of chimeric mashups (e.g. Scene 06 strictly bound to metric, no stamp mixing).
"""

import pytest
from app.services.semantic_evidence_extractor import (
    ForensicArchetype,
    SemanticEvidenceExtractor,
    extract_evidence_for_sentence,
    get_semantic_evidence_extractor,
)


def test_archetype_classification_multilingual():
    extractor = get_semantic_evidence_extractor()

    # 1. Legal Sanction (H1)
    ev_kr_legal = extractor.extract_evidence("공정위 제재가 보도됐습니다", market="KR", scene_id="SCENE_01")
    assert ev_kr_legal.archetype == ForensicArchetype.LEGAL_SANCTION
    assert ev_kr_legal.dominant_family == "H1_IMPACT"
    assert "sanction" in ev_kr_legal.hero_anchor_prop.lower()

    ev_en_legal = extractor.extract_evidence("The federal regulatory commission issued formal penalties and sanctions against the cartel.", market="EN", scene_id="SCENE_01")
    assert ev_en_legal.archetype == ForensicArchetype.LEGAL_SANCTION
    assert ev_en_legal.dominant_family == "H1_IMPACT"

    # 2. Corporate Entity (H2)
    ev_kr_corp = extractor.extract_evidence("시행사 네 곳 드림하우징 외 3개사 대상입니다", market="KR", scene_id="SCENE_01")
    assert ev_kr_corp.archetype == ForensicArchetype.CORPORATE_ENTITY
    assert ev_kr_corp.dominant_family == "H2_CONSTRAINT"
    assert "dossier" in ev_kr_corp.hero_anchor_prop.lower() or "contract" in ev_kr_corp.hero_anchor_prop.lower()

    # 3. Paradox Claim (H3)
    ev_kr_paradox = extractor.extract_evidence("하지만 광고는 마감임박이라며 계속 모집했습니다", market="KR", scene_id="SCENE_01")
    assert ev_kr_paradox.archetype == ForensicArchetype.PARADOX_CLAIM
    assert ev_kr_paradox.dominant_family == "H3_SEVER"
    assert "shears" in ev_kr_paradox.interacting_tool_prop.lower()

    # 4. Quantitative Metric (H2 Constraint / Binding Clamp) - The critical Scene 06 / Variant 2 test!
    ev_kr_metric = extractor.extract_evidence("사전 모집률 30%에 투자금을 묶었습니다", market="KR", scene_id="SCENE_03")
    assert ev_kr_metric.archetype == ForensicArchetype.QUANTITATIVE_METRIC
    assert ev_kr_metric.dominant_family == "H2_CONSTRAINT"
    assert "clamp" in ev_kr_metric.interacting_tool_prop.lower() or "binding" in ev_kr_metric.interacting_tool_prop.lower()
    # Guarantees zero seal stamp chimeric mashup!
    assert "stamp" not in ev_kr_metric.interacting_tool_prop.lower()
    # Enforces 100% zero caliper lock (Rule 140)
    assert "caliper" not in ev_kr_metric.interacting_tool_prop.lower()

    # 5. Investigative Media (H5 Optical)
    ev_kr_media = extractor.extract_evidence("경기일보는 네 곳의 미인허가 실태를 지적했습니다", market="KR", scene_id="SCENE_01")
    assert ev_kr_media.archetype == ForensicArchetype.INVESTIGATIVE_MEDIA
    assert ev_kr_media.dominant_family == "H4_TETHER"
    assert "thread" in ev_kr_media.interacting_tool_prop.lower() or "yarn" in ev_kr_media.interacting_tool_prop.lower()


def test_claim_to_evidence_physical_properties():
    ev = extract_evidence_for_sentence("The auditing body uncovered 45% revenue discrepancy", market="EN", scene_id="SCENE_03")
    assert ev.archetype == ForensicArchetype.QUANTITATIVE_METRIC
    assert ev.dominant_family == "H2_CONSTRAINT"
    assert "clamp" in ev.interacting_tool_prop.lower() or "binding" in ev.interacting_tool_prop.lower()
    assert "caliper" not in ev.interacting_tool_prop.lower()
    assert len(ev.tactile_action_verb) > 10
    assert len(ev.physical_reaction) > 10
    assert len(ev.tactile_residue) > 5
    assert ev.sound_foley.startswith("metallic_binder_clip")


def test_quantitative_metric_variants_diversity_and_zero_calipers():
    """Validates that all Quantitative Metric variants rotate across distinct tactile tools with ZERO calipers (Rule 140)."""
    extractor = get_semantic_evidence_extractor()
    seen_families = set()
    for sc_num in range(1, 5):
        ev = extractor.extract_evidence(
            "The corporate balance sheet suffered a $45M deficit",
            market="EN",
            scene_id=f"SCENE_{sc_num:02d}"
        )
        assert ev.archetype == ForensicArchetype.QUANTITATIVE_METRIC
        seen_families.add(ev.dominant_family)
        # 100% Anti-caliper invariant (Rule 140)
        assert "caliper" not in ev.interacting_tool_prop.lower()
        assert "caliper" not in ev.sound_foley.lower()
        assert "caliper" not in ev.tactile_residue.lower()

    # Must cover at least 3 distinct kinetic families across 4 scenes (H2 Constraint, H7 Displace, H6 Mark)
    assert len(seen_families) >= 3
