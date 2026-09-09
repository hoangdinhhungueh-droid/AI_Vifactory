"""
Unit tests for B3 Universal Context & Persona Extractor (Rule 128).
Verifies dynamic extraction, zero hardcoding/domain bleed, and non-destructive brain deep-merge.
"""
import pytest
from app.services.director_planner_b3 import (
    extract_universal_semantic_context,
    extract_dynamic_character_ensemble,
    detect_cinematic_archetype,
    _deep_merge,
    CANONICAL_BEATS,
    CINEMATIC_ARCHETYPES
)

STORY_FINANCE = """
In the autumn of 2008, senior financial auditors inside the Wall Street investment bank discovered anomalous debt obligations hidden off the balance sheet. 
Lead investigators examined the trading desk records under harsh fluorescent lights. 
Meanwhile, senior portfolio managers held late-night boardroom sessions, attempting to conceal the liquidity shortfall. 
A compliance whistleblower had quietly submitted encrypted ledger entries to federal regulators. 
Corporate defense attorneys hurried through marble corridors clutching nondisclosure agreements.
"""

STORY_AGRI = """
In the misty autumn dawn of a rural Korean farming province, elder crop cultivators discovered dozens of abandoned plastic pesticide containers stacked beside the terraced rice fields. 
Agricultural supply inspectors arrived with official inspection clipboards and chemical testing vials. 
Warehouse distribution managers refused to explain the counterfeit batch numbers on the shipping crates. 
At the provincial environmental toxicology laboratory, forensic chemical analysts tested residue samples. 
Regional municipal officials met in the village hall to review emergency agricultural regulations.
Local resident eyewitnesses pointed out suspicious unmarked delivery trucks.
"""

STORY_CHOLERA = """
In August 1854, a devastating cholera epidemic struck the Soho district of Victorian London. 
Epidemiological physicians tracked every fatality to the contaminated Broad Street water pump handle. 
Neighborhood residents and grieving eyewitnesses were interviewed along gaslit cobblestone streets. 
Sanitary board officials initially dismissed the waterborne transmission theory during contentious municipal vestry meetings. 
Archival registry clerks carefully documented the mortality statistics in heavy leatherbound ledgers.
Lead forensic researchers mapped the death clusters street by street.
"""


def test_canonical_beats_structure():
    assert len(CANONICAL_BEATS) == 5
    assert "Impossible Contradiction" in CANONICAL_BEATS[0]
    assert "Modern Mirror" in CANONICAL_BEATS[4]


def test_cinematic_archetype_routing():
    fin = detect_cinematic_archetype("Finance", "Forensic Wall Street Fraud")
    assert "Fincher" in fin["director"] or "Corporate Noir" in fin["director"]

    hist = detect_cinematic_archetype("History", "Cold War Manhattan Project")
    assert "Renck" in hist["director"] or "Villeneuve" in hist["director"] or "Chernobyl" in hist["director"]

    tech = detect_cinematic_archetype("Technology", "Semiconductor Supply Chain War")
    assert "Nolan" in tech["director"]

    med = detect_cinematic_archetype("Medical", "Cholera Outbreak")
    assert "Soderbergh" in med["director"] or "Villeneuve" in med["director"] or "Clinical" in med["director"]


def test_universal_semantic_context_extraction():
    ctx_fin = extract_universal_semantic_context(STORY_FINANCE, {"topic": "Wall Street Crisis"})
    assert "2008" in ctx_fin["era_anchor"] or "Century" in ctx_fin["era_anchor"]
    assert "wall street" in ctx_fin["physical_environment"].lower() or "boardroom" in ctx_fin["physical_environment"].lower()

    ctx_agr = extract_universal_semantic_context(STORY_AGRI, {"topic": "Counterfeit Pesticide"})
    assert "field" in ctx_agr["physical_environment"].lower() or "province" in ctx_agr["physical_environment"].lower() or "laboratory" in ctx_agr["physical_environment"].lower()

    ctx_med = extract_universal_semantic_context(STORY_CHOLERA, {"topic": "1854 Cholera"})
    assert "1854" in ctx_med["era_anchor"] or "19th" in ctx_med["era_anchor"]
    assert "district" in ctx_med["physical_environment"].lower() or "street" in ctx_med["physical_environment"].lower()


def test_dynamic_character_ensemble_extraction():
    ens_fin = extract_dynamic_character_ensemble(STORY_FINANCE)
    assert 4 <= len(ens_fin) <= 8
    fin_roles = [r["role_name"].lower() for r in ens_fin]
    assert any("auditor" in r or "investigator" in r or "manager" in r for r in fin_roles)
    # Zero agricultural or medical bleed
    assert not any("crop" in r or "farmer" in r or "cholera" in r for r in fin_roles)

    ens_agr = extract_dynamic_character_ensemble(STORY_AGRI)
    assert 4 <= len(ens_agr) <= 8
    agr_roles = [r["role_name"].lower() for r in ens_agr]
    assert any("cultivator" in r or "inspector" in r or "analyst" in r for r in agr_roles)
    # Zero wall street bleed
    assert not any("trading" in r or "wall street" in r for r in agr_roles)

    ens_med = extract_dynamic_character_ensemble(STORY_CHOLERA)
    assert 4 <= len(ens_med) <= 8
    med_roles = [r["role_name"].lower() for r in ens_med]
    assert any("physician" in r or "resident" in r or "researcher" in r or "clerk" in r for r in med_roles)
    # Zero semiconductor bleed
    assert not any("server" in r or "silicon" in r for r in med_roles)


def test_non_destructive_brain_deep_merge():
    b2_brain = {
        "episode_id": "EN_EP0261_test_case",
        "story_gate_score": "12/12",
        "story_verdict": "PASS",
        "market": "EN",
        "topic": "Systemic Financial Fraud",
        "hook_3s": "In 2008, the world financial system was on the brink.",
        "breakout_queries": ["subprime collapse", "leverage fraud"],
        "niche": "Corporate Noir",
        "search_specific_keyword": "subprime leverage"
    }

    b3_update = {
        "episode_id": "EN_EP0261_test_case",
        "content_type": "investigative_docudrama",
        "director_archetype": "Adam McKay / David Fincher (Corporate Noir)",
        "scenes": [{"scene_id": "sc001", "narration": "Opening scene..."}]
    }

    merged = _deep_merge(b2_brain, b3_update)

    # Ensure all B2 metadata is 100% intact
    assert merged["story_gate_score"] == "12/12"
    assert merged["story_verdict"] == "PASS"
    assert merged["market"] == "EN"
    assert merged["topic"] == "Systemic Financial Fraud"
    assert merged["hook_3s"] == "In 2008, the world financial system was on the brink."
    assert merged["breakout_queries"] == ["subprime collapse", "leverage fraud"]
    assert len(merged["scenes"]) == 1
