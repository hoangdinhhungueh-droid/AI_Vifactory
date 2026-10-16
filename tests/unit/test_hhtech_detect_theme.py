#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for hhtech_reasoner.detect_safety_and_theme.
Mandated by Boss Round 8 Item 12: drives a subject through every theme branch,
including ancient_terms and default fall-through, verifying zero NameError/F821.
"""

import pytest
from app.services.hhtech_reasoner import detect_safety_and_theme


def test_theme_true_crime():
    theme, label, note = detect_safety_and_theme("Serial Killer Ted Bundy Investigation", "EN")
    assert theme == "true_crime_investigative"
    assert label == "YT-Sensitive-TrueCrime"
    assert "CASE-SOLVING DOCUMENTARY ONLY" in note


def test_theme_gambling():
    theme, label, note = detect_safety_and_theme("Underground Casino Pachinko Addiction", "JP")
    assert theme == "psychology_manipulation_fraud"
    assert label == "YT-Gambling-Awareness"
    assert "GAMBLING AWARENESS ONLY" in note


def test_theme_fraud_business():
    theme, label, note = detect_safety_and_theme("Enron Accounting Fraud and Ponzi Collapse", "EN")
    assert theme == "business_rise_fall"
    assert label == "YT-Fraud-Education"
    assert "BUSINESS & FRAUD EDUCATION" in note


def test_theme_societal_crisis():
    theme, label, note = detect_safety_and_theme("Kodokushi Solitary Death Phenomenon", "JP")
    assert theme == "psychology_manipulation_fraud"
    assert label == "YT-Societal-Crisis-Documentary"
    assert "SOCIETAL CRISIS DOCUMENTARY" in note


def test_theme_tech_geopolitical():
    theme, label, note = detect_safety_and_theme("ASML Lithography Semiconductor Sanction", "EN")
    assert theme == "tech_geopolitical_battle"
    assert label == "YT-Tech-Geopolitical-Investigation"
    assert "TECH & GEOPOLITICAL INVESTIGATION" in note


def test_theme_ancient_prehistory():
    # Tests ancient_terms branch explicitly (Boss Item 12)
    theme, label, note = detect_safety_and_theme("Göbekli Tepe Megalithic Lost Civilization", "EN")
    assert theme == "ancient_prehistory_anthropology"
    assert label == "YT-Educational-Anthropology"
    assert "PREHISTORIC ANTHROPOLOGY" in note


def test_theme_modern_history_war():
    theme, label, note = detect_safety_and_theme("Cold War Proxy Battle Tactics", "EN")
    assert theme == "modern_history_untold"
    assert label == "YT-History-Factual-Neutral"
    assert "FACTUAL HISTORY DOCUMENTARY" in note


def test_theme_history_terms():
    theme, label, note = detect_safety_and_theme("Roman Empire Byzantine Crusade Siege", "EN")
    assert theme == "modern_history_untold"
    assert label == "YT-History-Factual-Neutral"
    assert "FACTUAL HISTORY DOCUMENTARY" in note


def test_theme_philosophy_stoicism():
    theme, label, note = detect_safety_and_theme("Marcus Aurelius Stoic Mindset for Burnout", "EN")
    assert theme == "indigenous_philosophy_stoicism"
    assert label == "YT-Philosophy-Mindset"
    assert "INDIGENOUS PHILOSOPHY & CONTEMPLATIVE RESILIENCE" in note


def test_theme_military_logistics():
    theme, label, note = detect_safety_and_theme("Berlin Airlift Military Logistics and Supply Line Blunder", "EN")
    assert theme == "military_logistics_geopolitics"
    assert label == "YT-Military-Tactical-Investigation"
    assert "MILITARY LOGISTICS & GEOPOLITICAL CHOKEPOINTS" in note


def test_theme_consumer_injustice():
    theme, label, note = detect_safety_and_theme("Gym Subscription Hidden Fee and Refund Trap", "EN")
    assert theme == "consumer_injustice_institutional_trap"
    assert label == "YT-Consumer-Awareness"
    assert "CONSUMER INJUSTICE DOCUDRAMA" in note


def test_theme_default_fallthrough():
    # Tests default fall-through when no keyword matches
    theme, label, note = detect_safety_and_theme("Generic Everyday Product Lifecycle", "EN")
    assert theme == "business_rise_fall"
    assert label == "YT-Safe-Standard"
    assert "Standard platform-safe nonfiction documentary treatment" in note


def test_theme_empty_and_none_input():
    # Tests defensive handling of empty/none input
    theme1, label1, note1 = detect_safety_and_theme("", "EN")
    assert theme1 == "business_rise_fall"
    assert label1 == "YT-Safe-Standard"

    theme2, label2, note2 = detect_safety_and_theme(None, "EN")
    assert theme2 == "business_rise_fall"
    assert label2 == "YT-Safe-Standard"
