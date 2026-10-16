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

    # fossils from fossil (must match real fossil, not fossil fuel)
    assert _matches_any_term("Ancient fossil discovery in cave", ["fossil"])
    assert _matches_any_term("Prehistoric fossils unearthed in desert", ["fossil"])

    # murders/murdered from murder
    assert _matches_any_term("Series of unexplained murders in London", ["murder"])
    assert _matches_any_term("Victim was murdered in cold blood", ["murder"])

    # refunds from refund
    assert _matches_any_term("Massive tax refunds processed", ["refund"])
    assert _matches_any_term("Customer demanded refund", ["refund"])


def test_stem_matching_does_not_overmatch_unrelated_words():
    """Verify that stem matching respects word boundaries and doesn't match substrings inside different words.
    Enforces Boss Claude Opus Round 12 negative boundary assertions.
    """
    # 'car' should not match inside 'scare'
    assert not _matches_any_term("They scare everyone", ["car"])
    # 'pen' should not match inside 'open'
    assert not _matches_any_term("Open the door", ["pen"])

    # Boss Round 12 punchlist: stem matching must not over-match short words/roots
    # 'cult' must not match 'culture' or 'cultivation'
    assert not _matches_any_term("Traditional corporate culture is changing", ["cult"])
    assert not _matches_any_term("Agriculture and wheat cultivation techniques", ["cult"])
    # 'chip' must not match 'Chipotle' or 'chipmunk'
    assert not _matches_any_term("Lunch at Chipotle restaurant today", ["chip"])
    assert not _matches_any_term("Cute wild chipmunk in forest", ["chip"])
    # 'fab' must not match 'fabric' or 'fabulous'
    assert not _matches_any_term("High quality cotton fabric materials", ["fab"])
    assert not _matches_any_term("Fabulous new fashion collection", ["fab"])
    # 'slot' must not match 'sloth'
    assert not _matches_any_term("Sloth sanctuary in the tropical rainforest", ["slot"])
    # 'serial' must not match 'serialized'
    assert not _matches_any_term("The database transactions were serialized", ["serial"])
    # 'fossil' must not match 'fossil fuel'
    assert not _matches_any_term("Global fossil fuel depletion policies", ["fossil"])
    # 'revolution' must not match 'AI revolution' or 'tech revolution'
    assert not _matches_any_term("The AI revolution is transforming healthcare", ["revolution"])
    assert not _matches_any_term("Major tech revolution underway", ["revolution"])
    # 'forensic' must not match 'forensic accounting'
    assert not _matches_any_term("Forensic accounting uncovers offshore tax scheme", ["forensic"])


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

    # Military geopolitics theme (must be reachable and not swallowed by tech geopolitic)
    theme_mil, safety_mil, note_mil = detect_safety_and_theme("Geopolitical choke points and naval blockade tactical crisis")
    assert theme_mil == "military_logistics_geopolitics"
    assert safety_mil == "YT-Military-Tactical-Investigation"

    # Geopolitical crisis theme
    theme_geo, safety_geo, note_geo = detect_safety_and_theme("Geopolitical tensions and semiconductor trade embargo standoff")
    assert theme_geo == "tech_geopolitical_battle"
    assert safety_geo == "YT-Tech-Geopolitical-Investigation"

    # Ancient archaeology theme (fossil skeleton vs fossil fuel separation)
    theme_anc, safety_anc, note_anc = detect_safety_and_theme("New archaeological fossil skeleton discovered in cave")
    assert theme_anc == "ancient_prehistory_anthropology"
    assert safety_anc == "YT-Educational-Anthropology"

    # Energy fossil fuel should NOT route to ancient anthropology
    theme_fuel, safety_fuel, _ = detect_safety_and_theme("Global fossil fuel shortage triggers bankruptcy crisis")
    assert theme_fuel == "business_rise_fall"

    # Forensic accounting should route to fraud/business, NOT true crime
    theme_acc, safety_acc, _ = detect_safety_and_theme("Forensic accounting reveals secret embezzlement scheme")
    assert theme_acc == "business_rise_fall"

    # AI revolution should route to tech, NOT history
    theme_rev, safety_rev, _ = detect_safety_and_theme("The AI revolution and semiconductor microchip innovations")
    assert theme_rev == "tech_geopolitical_battle"
