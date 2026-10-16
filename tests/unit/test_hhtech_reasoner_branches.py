#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests verifying all 11 branches in detect_safety_and_theme (Boss Round 8 Revision 1)."""

import pytest
from app.services.hhtech_reasoner import detect_safety_and_theme


def test_detect_safety_and_theme_all_branches():
    """Verify that every single theme branch and the fallback branch execute with zero NameErrors."""
    cases = [
        # (subject, expected_theme, expected_safety)
        ("infamous serial killer investigation", "true_crime_investigative", "YT-Sensitive-TrueCrime"),
        ("underground casino gambling addiction trap", "psychology_manipulation_fraud", "YT-Gambling-Awareness"),
        ("massive corporate ponzi fraud collapse", "business_rise_fall", "YT-Fraud-Education"),
        ("silent epidemic of kodokushi isolation", "psychology_manipulation_fraud", "YT-Societal-Crisis-Documentary"),
        ("semiconductor chip supply chain embargo", "tech_geopolitical_battle", "YT-Tech-Geopolitical-Investigation"),
        ("mysterious gobekli tepe ancient megalith", "ancient_prehistory_anthropology", "YT-Educational-Anthropology"),
        ("the cold war naval confrontation", "modern_history_untold", "YT-History-Factual-Neutral"),
        ("historical ottoman empire uprising", "modern_history_untold", "YT-History-Factual-Neutral"),
        ("marcus aurelius stoic mindset protocol", "indigenous_philosophy_stoicism", "YT-Philosophy-Mindset"),
        ("strategic malacca strait maritime blockade", "military_logistics_geopolitics", "YT-Military-Tactical-Investigation"),
        ("unilateral contract cancellation fee hidden refund trap", "consumer_injustice_institutional_trap", "YT-Consumer-Awareness"),
        ("routine commercial corporate quarterly report", "business_rise_fall", "YT-Safe-Standard"),
    ]

    for subject, expected_theme, expected_safety in cases:
        theme, safety, note = detect_safety_and_theme(subject, market="EN")
        assert theme == expected_theme, f"Failed theme for '{subject}': got {theme}, expected {expected_theme}"
        assert safety == expected_safety, f"Failed safety for '{subject}': got {safety}, expected {expected_safety}"
        assert isinstance(note, str) and len(note) > 10, f"Empty or short treatment note for '{subject}'"
