# tests/test_prompt_forge_r137.py
"""
Unit tests for Rule 137 Strict Prompt Linter (app/services/prompt_forge.py).
Enforces zero-text, zero-number, and blank document template invariants
across EN, JP, and KR markets.
"""

import pytest
from app.services.prompt_forge import (
    lint_visual_prompt,
    _sanitize_background_prompt,
    _sanitize_foreground_prompt,
    R137_ALLOWLIST,
    BLANK_TEMPLATE,
    NEGATIVE_R137,
    R137_CLOSING_DIRECTIVE
)


def test_r137_allowlist_passthrough():
    """Verify that cinematography and era tokens pass through without triggering violation."""
    safe_prompts = [
        "2.5D parallax layer with dramatic lighting",
        "shot on 35mm vintage camera lens",
        "close-up 50mm portrait perspective",
        "cinematic 85mm anamorphic compression",
        "1980s Wall Street trading floor atmosphere",
        "1990s Tokyo financial office interior",
        "2000s Seoul corporate headquarters boardroom",
        "16:9 cinematic widescreen environment",
        "1:1 stylized character cutout"
    ]
    for prompt in safe_prompts:
        res = lint_visual_prompt(prompt, strict=True)
        assert res.ok, f"Prompt should pass allowlist: '{prompt}', but got violations: {res.violations}"


def test_r137_banned_currencies():
    """Verify that currency symbols and currency words in EN, JP, and KR are flagged."""
    banned_samples = [
        ("A document showing $942 in purchases", "currency"),
        ("Wall Street ledger with ¥140兆 recorded", "currency"),
        ("Transaction record displaying ₩1,300조 total", "currency"),
        ("Court exhibit showing 500 million USD transfer", "currency"),
        ("Receipt showing 100 dollars fee", "currency"),
        ("Financial statement with 500 yen stamp", "currency"),
        ("Bank filing with 1000 won penalty", "currency"),
        ("회계 장부에 기록된 100억 달러", "currency"),
        ("비자금 500만 원화 송금 내역", "currency"),
        ("MOF報告書に記載された100億ドル", "currency"),
        ("巨額の資金50億円の取引", "currency")
    ]
    for prompt, expected_cat in banned_samples:
        res = lint_visual_prompt(prompt, strict=True)
        assert not res.ok, f"Prompt should fail linting: '{prompt}'"
        assert any(cat == expected_cat for cat, _ in res.violations)


def test_r137_banned_units():
    """Verify that scale units and percentages are flagged."""
    banned_units = [
        "Foreign capital inflow reached 942 billion",
        "Global hedge funds managed 1.2 trillion in assets",
        "Startup valuation peaked at 50 million",
        "Treasury yield surged 5 percent today",
        "Market share dropped by 38%",
        "経常収支の赤字が100億円に達する",
        "海外投資家が5兆円の資金を引き上げる",
        "외국인 자본 9420억 유입",
        "기업 총수 1조 원대 횡령 혐의"
    ]
    for prompt in banned_units:
        res = lint_visual_prompt(prompt, strict=True)
        assert not res.ok, f"Prompt should flag units: '{prompt}'"
        assert any(cat in ("units", "currency", "digits") for cat, _ in res.violations)


def test_r137_banned_text_claims_and_quotes():
    """Verify that prompts attempting to bake in text, titles, or quotes are flagged."""
    claims = [
        'A document with headline reading "CONFIDENTIAL"',
        'A stamp saying "APPROVED BY REGULATOR"',
        "A ledger labeled with audited values",
        "A poster with typography and bold font text",
        "A trading chart with readable numbers and chart values"
    ]
    for prompt in claims:
        res = lint_visual_prompt(prompt, strict=True)
        assert not res.ok, f"Prompt should flag text claim: '{prompt}'"
        assert any(cat in ("text_claims", "quoted") for cat, _ in res.violations)


def test_r137_document_blank_template_injection():
    """Verify that document nouns trigger blank template injection in non-strict mode."""
    doc_prompts = [
        "A forensic international banking receipt on a desk",
        "An official SEC subpoena paper exhibit",
        "An internal corporate ledger document",
        "A sworn court filing with official stamps"
    ]
    for prompt in doc_prompts:
        res = lint_visual_prompt(prompt, strict=False)
        assert "unfilled template" in res.prompt
        assert "blank amount fields" in res.prompt
        assert "no typography" in res.prompt
        assert R137_CLOSING_DIRECTIVE in res.prompt


def test_r137_sanitize_background_integration():
    """Verify that _sanitize_background_prompt includes Rule 137 negative prompts and closing directive."""
    raw_bg = "1990s Wall Street trading floor with busy terminals, 16:9 aspect ratio"
    sanitized = _sanitize_background_prompt(raw_bg, bg_key="bg_trading_floor", market="EN")
    assert NEGATIVE_R137 in sanitized
    assert R137_CLOSING_DIRECTIVE in sanitized
    assert "no prominent foreground human figures" in sanitized


def test_r137_sanitize_foreground_integration():
    """Verify that _sanitize_foreground_prompt strips numbers and injects blank templates for doc props."""
    raw_fg_doc = "Official bank receipt showing $942 billion net purchases"
    sanitized = _sanitize_foreground_prompt(raw_fg_doc, fg_key="fg_evidence_receipt", market="EN")
    assert "942 billion" not in sanitized.lower()
    assert "$942" not in sanitized
    assert "blank unfilled fields" in sanitized or "unfilled template" in sanitized
    assert NEGATIVE_R137 in sanitized
    assert R137_CLOSING_DIRECTIVE in sanitized


def test_r137_multi_market_cleanliness():
    """Verify that JP and KR market profiles receive clean prompt sanitization without leakage."""
    jp_bg = "Tokyo financial district Kabutocho office at dusk"
    jp_sanitized = _sanitize_background_prompt(jp_bg, market="JP")
    assert NEGATIVE_R137 in jp_sanitized
    assert R137_CLOSING_DIRECTIVE in jp_sanitized

    kr_fg = "Senior prosecutor examining evidence folder"
    kr_sanitized = _sanitize_foreground_prompt(kr_fg, market="KR")
    assert NEGATIVE_R137 in kr_sanitized
    assert R137_CLOSING_DIRECTIVE in kr_sanitized
