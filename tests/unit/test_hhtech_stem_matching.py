#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_hhtech_stem_matching.py
Unit tests verifying stem and inflection regex matching (_matches_any_term)
and decoupled generic taxonomy detection in detect_safety_and_theme (Rule 128 & Boss Round 11).
"""

from app.services.hhtech_reasoner import _matches_any_term, detect_safety_and_theme


def test_stem_and_inflection_matching():
    """Verify that _matches_any_term matches morphological stems and plurals."""
    # archaeology from stem archaeolog
    assert _matches_any_term("New archaeological discoveries in Egypt", ["archaeolog"])
    assert _matches_any_term("Ancient archaeology reveals secret tomb", ["archaeolog"])

    # geopolitical from geopolitic
    assert _matches_any_term("Current geopolitical tensions escalate", ["geopolitic"])
    assert _matches_any_term("Geopolitics of rare earth minerals", ["geopolitic"])

    # sanctions from sanction
    assert _matches_any_term("Global economic sanctions announced", ["sanction"])
    assert _matches_any_term("Government sanctions foreign entity", ["sanction"])

    # semiconductors from semiconductor
    assert _matches_any_term("Shortage of advanced semiconductors", ["semiconductor"])
    assert _matches_any_term("The semiconductor supply chain shock", ["semiconductor"])

    # fossils from fossil
    assert _matches_any_term("Fossil fuel phaseout policies", ["fossil"])
    assert _matches_any_term("Prehistoric fossils unearthed in desert", ["fossil"])

    # murders/murdered from murder
    assert _matches_any_term("Series of unexplained murders in London", ["murder"])
    assert _matches_any_term("Victim was murdered in cold blood", ["murder"])

    # refunds from refund
    assert _matches_any_term("Massive tax refunds processed", ["refund"])
    assert _matches_any_term("Customer demanded refund", ["refund"])


def test_stem_matching_does_not_overmatch_unrelated_words():
    """Verify that stem matching respects word boundaries and doesn't match substrings inside different words."""
    # 'car' should not match inside 'scare'
    assert not _matches_any_term("They scare everyone", ["car"])
    # 'pen' should not match inside 'open'
    assert not _matches_any_term("Open the door", ["pen"])


def test_decoupled_detect_safety_and_theme():
    """Verify generic topic detection works without hardcoded named entities (Rule 128)."""
    # Crime / forensic theme via generic terms
    theme, safety_label, treatment_note = detect_safety_and_theme("Forensic investigation of cold case serial killer evidence")
    assert theme == "true_crime_investigative"
    assert safety_label == "YT-Sensitive-TrueCrime"
    assert "CASE-SOLVING DOCUMENTARY" in treatment_note

    # Financial scandal theme via generic terms
    theme_fin, safety_fin, note_fin = detect_safety_and_theme("Whistleblower exposes offshore ponzi embezzlement and fraud conspiracy")
    assert theme_fin == "business_rise_fall"
    assert safety_fin == "YT-Fraud-Education"

    # Geopolitical crisis theme
    theme_geo, safety_geo, note_geo = detect_safety_and_theme("Geopolitical tensions and semiconductor trade embargo standoff")
    assert theme_geo == "tech_geopolitical_battle"
    assert safety_geo == "YT-Tech-Geopolitical-Investigation"

    # Ancient archaeology theme
    theme_anc, safety_anc, note_anc = detect_safety_and_theme("New archaeological fossil discovered in cave")
    assert theme_anc == "ancient_prehistory_anthropology"
    assert safety_anc == "YT-Educational-Anthropology"
