"""
Unit and Contract Tests for B1.5 Grounding Layer Service.
Rule 121: Strict Verification Protocol.
Rule 128: Generic Pattern & Schema Contracts.
"""

import pytest
from app.services.grounding_layer_b15 import (
    is_trusted_domain,
    passes_grounding_gate,
    format_grounded_facts_for_prompt
)


def test_is_trusted_domain():
    # Authoritative wire services & journals
    assert is_trusted_domain("Reuters", "https://www.reuters.com/business") is True
    assert is_trusted_domain("AP News", "https://apnews.com/article/123") is True
    assert is_trusted_domain("Bloomberg", "https://bloomberg.com/news") is True
    assert is_trusted_domain("Lloyd's List", "https://lloydslist.com") is True
    assert is_trusted_domain("US MARAD", "https://marad.dot.gov") is True

    # Think tanks, security & central banks
    assert is_trusted_domain("CSIS", "https://www.csis.org/analysis") is True
    assert is_trusted_domain("Bank for International Settlements (BIS)", "https://www.bis.org") is True
    assert is_trusted_domain("Federal Reserve", "https://www.federalreserve.gov") is True

    # Japanese & Korean authoritative sources (English, Kanji, and Hangul)
    assert is_trusted_domain("Nikkei", "https://www.nikkei.com/article/123") is True
    assert is_trusted_domain("日本経済新聞") is True
    assert is_trusted_domain("NHK News", "https://www3.nhk.or.jp/news") is True
    assert is_trusted_domain("財務省") is True
    assert is_trusted_domain("共同通信") is True
    assert is_trusted_domain("時事通信") is True
    assert is_trusted_domain("金融庁") is True
    assert is_trusted_domain("Japan Gov", "https://www.kantei.go.jp") is True
    assert is_trusted_domain("Yonhap News", "https://en.yna.co.kr/view/123") is True
    assert is_trusted_domain("연합뉴스") is True
    assert is_trusted_domain("조선일보") is True
    assert is_trusted_domain("금융감독원") is True
    assert is_trusted_domain("기획재정부") is True
    assert is_trusted_domain("Korea Gov", "https://www.mofa.go.kr") is True
    assert is_trusted_domain("VnExpress") is True
    assert is_trusted_domain("Tuổi Trẻ") is True

    # Multi-source composite string check
    assert is_trusted_domain("Vertex AI Search, The National, Nautilus Shipping, Ministry of Transport") is True
    assert is_trusted_domain("Al Arabiya, WAFA (citing Kpler data)") is True

    # Untrusted / social media / content farm
    assert is_trusted_domain("Random Blog", "https://clickbait-news.xyz") is False
    assert is_trusted_domain("Anonymous Forum", "https://forum.sample.org.fake") is False


def test_passes_grounding_gate_rejection():
    # Empty result
    ok, reason = passes_grounding_gate({})
    assert ok is False

    # Explicitly rejected by model
    rejected_res = {
        "topic": "fake topic",
        "rejected": True,
        "reject_reason": "Topic has no real news sources",
        "claims": []
    }
    ok, reason = passes_grounding_gate(rejected_res)
    assert ok is False
    assert "Topic rejected by grounding" in reason

    # No claims extracted with live search
    no_claims_res = {
        "topic": "unknown topic",
        "rejected": False,
        "claims": [],
        "has_live_search": True
    }
    ok, reason = passes_grounding_gate(no_claims_res)
    assert ok is False
    assert "No factual claims" in reason


def test_passes_grounding_gate_strict_audit_criteria():
    # 1. Insufficient claims (< 3)
    few_claims_res = {
        "topic": "short topic",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Claim 1", "source": "Reuters", "confidence": "verified", "date": "2026-09-01"}
        ]
    }
    ok, reason = passes_grounding_gate(few_claims_res)
    assert ok is False
    assert "Insufficient total claims" in reason

    # 2. Insufficient verified claims (< 2)
    unverified_res = {
        "topic": "unverified topic",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Claim 1", "source": "Reuters", "confidence": "verified", "date": "2026-09-01"},
            {"claim": "Claim 2", "source": "Bloomberg", "confidence": "reported", "date": "2026-09-02"},
            {"claim": "Claim 3", "source": "MarketWatch", "confidence": "speculative", "date": "2026-09-03"}
        ]
    }
    ok, reason = passes_grounding_gate(unverified_res, min_verified=2)
    assert ok is False
    assert "Insufficient verified claims" in reason

    # 3. Speculative ratio too high (> 40%)
    high_spec_res = {
        "topic": "speculative topic",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Claim 1", "source": "Reuters", "confidence": "verified", "date": "2026-09-01"},
            {"claim": "Claim 2", "source": "Bloomberg", "confidence": "verified", "date": "2026-09-02"},
            {"claim": "Claim 3", "source": "Blog A", "confidence": "speculative", "date": "2026-09-03"},
            {"claim": "Claim 4", "source": "Blog B", "confidence": "speculative", "date": "2026-09-04"}
        ]
    }
    # 2 out of 4 is 50% > 40%
    ok, reason = passes_grounding_gate(high_spec_res, max_speculative_ratio=0.40)
    assert ok is False
    assert "Speculative claims ratio too high" in reason

    # 4. Insufficient dated claims (< 2)
    undated_res = {
        "topic": "undated topic",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Claim 1", "source": "Reuters", "confidence": "verified", "date": "Undated"},
            {"claim": "Claim 2", "source": "Bloomberg", "confidence": "verified", "date": ""},
            {"claim": "Claim 3", "source": "AP News", "confidence": "reported", "date": "2026-09-03"}
        ]
    }
    ok, reason = passes_grounding_gate(undated_res, min_dated_claims=2)
    assert ok is False
    assert "Insufficient temporally anchored claims" in reason

    # 5. Whitelist enforcement: verified claims not from whitelisted sources
    non_whitelist_res = {
        "topic": "local event",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Claim 1", "source": "LocalBlog1", "confidence": "verified", "date": "2026-09-01"},
            {"claim": "Claim 2", "source": "LocalBlog2", "confidence": "verified", "date": "2026-09-02"},
            {"claim": "Claim 3", "source": "LocalBlog3", "confidence": "reported", "date": "2026-09-03"}
        ]
    }
    ok, reason = passes_grounding_gate(non_whitelist_res, min_verified=2, require_whitelist=True)
    assert ok is False
    assert "authoritative domains" in reason

    # 6. Valid Grounding Gate PASS
    valid_res = {
        "topic": "official sanctions & trade",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Armed forces interdicted commercial vessel in international corridor", "source": "Reuters", "confidence": "verified", "date": "2026-09-01", "causal_role": "primary_catalyst", "mechanism": "military"},
            {"claim": "Transit fell 80%", "source": "Lloyd's List", "confidence": "verified", "date": "2026-09-02", "causal_role": "transmission_mechanism", "mechanism": "commercial"},
            {"claim": "Spot freight rates elevated", "source": "US MARAD", "confidence": "reported", "date": "2026-09-03", "causal_role": "transmission_mechanism", "mechanism": "financial"}
        ]
    }
    ok, reason = passes_grounding_gate(valid_res, min_verified=2, require_whitelist=True)
    assert ok is True
    assert "PASSED" in reason
    assert "causal_link: VALID" in reason

    # 7. Valid Japanese Grounding Gate PASS with Kanji sources
    valid_jp_res = {
        "topic": "日本の貿易収支赤字",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "2026年8月の貿易収支が1兆1056億円の赤字を記録", "source": "財務省", "confidence": "verified", "date": "2026-09-16", "causal_role": "primary_catalyst", "mechanism": "financial"},
            {"claim": "輸出額が前年同月比で3.2%減少", "source": "日本経済新聞", "confidence": "verified", "date": "2026-09-16", "causal_role": "transmission_mechanism", "mechanism": "commercial"},
            {"claim": "原油輸入価格の上昇が貿易収支を圧迫", "source": "NHKニュース", "confidence": "reported", "date": "2026-09-16", "causal_role": "transmission_mechanism", "mechanism": "financial"}
        ]
    }
    ok, reason = passes_grounding_gate(valid_jp_res, min_verified=2, require_whitelist=True)
    assert ok is True
    assert "PASSED" in reason


def test_classify_causal_role():
    from app.services.grounding_layer_b15 import classify_causal_role

    # Explicit tagging
    assert classify_causal_role({"causal_role": "primary_catalyst"}) == "primary_catalyst"
    assert classify_causal_role({"causal_role": "transmission_mechanism"}) == "transmission_mechanism"
    assert classify_causal_role({"causal_role": "background_context"}) == "background_context"

    # Heuristic fallback: Catalyst signals
    assert classify_causal_role({"claim": "Forces struck two oil tankers", "mechanism": "military"}) == "primary_catalyst"
    assert classify_causal_role({"claim": "Court issued indictment against executive", "mechanism": "legal"}) == "primary_catalyst"

    # Heuristic fallback: Transmission signals
    assert classify_causal_role({"claim": "War risk insurance premiums surged to 3%", "mechanism": "financial"}) == "transmission_mechanism"
    assert classify_causal_role({"claim": "Vessel traffic dropped by 85%", "mechanism": "commercial"}) == "transmission_mechanism"


def test_passes_grounding_gate_causal_link_missing_catalyst():
    # Only transmission claims, no primary catalyst
    no_catalyst_res = {
        "topic": "only transmission topic",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "War risk insurance rose to 3%", "source": "Reuters", "confidence": "verified", "date": "2026-09-01", "causal_role": "transmission_mechanism"},
            {"claim": "Vessel traffic fell 80%", "source": "Lloyd's List", "confidence": "verified", "date": "2026-09-02", "causal_role": "transmission_mechanism"},
            {"claim": "Advisory notice issued", "source": "US MARAD", "confidence": "reported", "date": "2026-09-03", "causal_role": "transmission_mechanism"}
        ]
    }
    ok, reason = passes_grounding_gate(no_catalyst_res, require_causal_link=True)
    assert ok is False
    assert "Causal Link Failure" in reason
    assert "primary catalyst" in reason


def test_passes_grounding_gate_causal_link_missing_transmission():
    # Only catalyst claims, no transmission mechanism
    no_trans_res = {
        "topic": "only catalyst topic",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Missile attack struck port facility", "source": "Reuters", "confidence": "verified", "date": "2026-09-01", "causal_role": "primary_catalyst"},
            {"claim": "Naval strike launched against depot", "source": "AP News", "confidence": "verified", "date": "2026-09-02", "causal_role": "primary_catalyst"},
            {"claim": "Subpoena issued for executive records", "source": "Bloomberg", "confidence": "reported", "date": "2026-09-03", "causal_role": "primary_catalyst"}
        ]
    }
    ok, reason = passes_grounding_gate(no_trans_res, require_causal_link=True)
    assert ok is False
    assert "Causal Link Failure" in reason
    assert "transmission mechanism" in reason


def test_format_grounded_facts_for_prompt():
    sample_result = {
        "claims": [
            {
                "claim": "Forces ordered immediate corridor closure",
                "source": "Reuters",
                "date": "2026-08-14",
                "confidence": "verified",
                "causal_role": "primary_catalyst",
                "mechanism": "military"
            },
            {
                "claim": "Vessel transits fell by 18 percent",
                "source": "Lloyd's List",
                "date": "2026-08-15",
                "confidence": "verified",
                "causal_role": "transmission_mechanism",
                "mechanism": "commercial"
            },
            {
                "claim": "Advisory notice issued to merchant fleet",
                "source": "US MARAD",
                "date": "2026-08-16",
                "confidence": "reported",
                "causal_role": "transmission_mechanism",
                "mechanism": "regulatory"
            }
        ]
    }
    formatted = format_grounded_facts_for_prompt(sample_result)
    assert "REAL-WORLD GROUNDED FACTS TABLE" in formatted
    assert "RULE 130" in formatted
    assert "[VERIFIED] [PRIMARY_CATALYST] (2026-08-14) [Reuters | Mechanism: military]" in formatted
    assert "[VERIFIED] [TRANSMISSION_MECHANISM] (2026-08-15) [Lloyd's List | Mechanism: commercial]" in formatted
    assert "[REPORTED] [TRANSMISSION_MECHANISM] (2026-08-16) [US MARAD | Mechanism: regulatory]" in formatted


def test_story_engine_strict_grounding_contract(tmp_path):
    from app.services.story_engine_b2 import load_grounding_intel
    import os, json

    # 1. Missing grounding intel card -> raises RuntimeError
    with pytest.raises(RuntimeError, match="Strict Contract Violation: B1.5.5 Grounding Intel Card missing"):
        load_grounding_intel("NON_EXISTENT_TASK_XYZ", str(tmp_path))

    # 2. Existing but rejected grounding intel card -> raises RuntimeError
    bad_intel = tmp_path / "grounding_intel.json"
    bad_intel.write_text(json.dumps({"topic": "bad", "rejected": True, "claims": []}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Strict Contract Violation: B1.5.5 Grounding Gate REJECTED"):
        load_grounding_intel("TASK_BAD", str(tmp_path))

    # 3. Valid grounding card with >= 2 verified whitelisted claims & valid causal link -> passes and returns block
    good_intel = {
        "topic": "verified",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {"claim": "Hostile strike ordered against cargo corridor", "source": "Reuters", "confidence": "verified", "date": "2026-09-01", "causal_role": "primary_catalyst", "mechanism": "military"},
            {"claim": "Vessel transits plunged 84 percent", "source": "Lloyd's List", "confidence": "verified", "date": "2026-09-02", "causal_role": "transmission_mechanism", "mechanism": "commercial"},
            {"claim": "Official advisory notice issued to fleet", "source": "US MARAD", "confidence": "reported", "date": "2026-09-03", "causal_role": "transmission_mechanism", "mechanism": "regulatory"}
        ]
    }
    bad_intel.write_text(json.dumps(good_intel), encoding="utf-8")
    data, block = load_grounding_intel("TASK_GOOD", str(tmp_path))
    assert len(data["claims"]) == 3
    assert "REAL-WORLD GROUNDED FACTS TABLE" in block
    assert "RULE 130" in block


def test_format_grounded_facts_with_chrono_epochs():
    sample_result = {
        "temporal_cadence": "MACRO_SAGA",
        "claims": [
            {
                "claim": "Direct breach event",
                "source": "Reuters",
                "date": "2026-08-14",
                "confidence": "verified",
                "causal_role": "primary_catalyst",
                "mechanism": "legal"
            },
            {
                "claim": "Regulatory sanction notice",
                "source": "SEC",
                "date": "2026-08-15",
                "confidence": "verified",
                "causal_role": "transmission_mechanism",
                "mechanism": "regulatory"
            }
        ],
        "causal_epochs": [
            {
                "epoch_stage": "genesis_seed",
                "time_marker": "2007",
                "event_summary": "Initial loan guaranteed by commercial bank",
                "verified_claim": "380 billion won loan contracted"
            },
            {
                "epoch_stage": "incubation_mutation",
                "time_marker": "2015",
                "event_summary": "Collateral sold at auction after debt default",
                "verified_claim": "Auction completed"
            },
            {
                "epoch_stage": "critical_rupture",
                "time_marker": "2026",
                "event_summary": "Arbitration tribunal dismisses all claims with costs",
                "verified_claim": "Zero payout award"
            }
        ]
    }
    formatted = format_grounded_facts_for_prompt(sample_result)
    assert "CHRONO-CAUSAL EPOCHS TABLE (TEMPORAL CADENCE: MACRO_SAGA)" in formatted
    assert "[GENESIS_SEED] (2007): Initial loan guaranteed by commercial bank" in formatted
    assert "[INCUBATION_MUTATION] (2015): Collateral sold at auction" in formatted
    assert "[CRITICAL_RUPTURE] (2026): Arbitration tribunal dismisses all claims" in formatted


