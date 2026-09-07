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


def test_passes_grounding_gate_confidence_threshold():
    # Only reported and speculative claims (0 verified), min_verified = 1
    unverified_res = {
        "topic": "rumored merger",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {
                "claim": "Rumor that Company A might acquire B",
                "source": "Tech Blog",
                "confidence": "speculative",
                "date": "2026-09-01"
            },
            {
                "claim": "Unconfirmed memo leaked online",
                "source": "Social Media",
                "confidence": "reported",
                "date": "2026-09-02"
            }
        ]
    }
    ok, reason = passes_grounding_gate(unverified_res, min_verified=1)
    assert ok is False
    assert "Insufficient verified claims" in reason

    # With 1 verified claim
    verified_res = {
        "topic": "official sanction",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {
                "claim": "Official sanctions were announced by treasury",
                "source": "Reuters",
                "source_url": "https://reuters.com",
                "confidence": "verified",
                "date": "2026-09-03",
                "mechanism": "regulatory"
            }
        ]
    }
    ok, reason = passes_grounding_gate(verified_res, min_verified=1)
    assert ok is True
    assert "PASSED" in reason


def test_passes_grounding_gate_whitelist_enforcement():
    # Verified claim but from non-whitelisted source
    non_whitelist_res = {
        "topic": "local event",
        "rejected": False,
        "has_live_search": True,
        "claims": [
            {
                "claim": "Local event took place",
                "source": "MyPersonalBlog",
                "source_url": "https://mypersonalblog.net",
                "confidence": "verified",
                "date": "2026-09-04"
            }
        ]
    }
    ok, reason = passes_grounding_gate(non_whitelist_res, min_verified=1, require_whitelist=True)
    assert ok is False
    assert "whitelisted authoritative domains" in reason


def test_format_grounded_facts_for_prompt():
    sample_result = {
        "claims": [
            {
                "claim": "Vessel transits fell by 18 percent",
                "source": "Lloyd's List",
                "date": "2026-08-15",
                "confidence": "verified",
                "mechanism": "commercial"
            },
            {
                "claim": "Advisory notice issued to merchant fleet",
                "source": "US MARAD",
                "date": "2026-08-16",
                "confidence": "reported",
                "mechanism": "regulatory"
            }
        ]
    }
    formatted = format_grounded_facts_for_prompt(sample_result)
    assert "REAL-WORLD GROUNDED FACTS TABLE" in formatted
    assert "[VERIFIED] (2026-08-15) [Lloyd's List | Mechanism: commercial]: Vessel transits fell by 18 percent" in formatted
    assert "[REPORTED] (2026-08-16) [US MARAD | Mechanism: regulatory]: Advisory notice issued to merchant fleet" in formatted
