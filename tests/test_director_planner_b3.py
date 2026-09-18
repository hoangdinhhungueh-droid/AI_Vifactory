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


def test_cjk_beat_extraction_and_scene_breakdown():
    from app.services.director_planner_b3 import extract_story_beats, _synthesize_deterministic_director_plan, detect_cinematic_archetype

    cjk_story = """=== ACT I ===
2億1000万円――2026年9月9日、多田神社が民事再生を申し立て、名刀・鬼切丸と不動産が担保に挙がったと報じられました。
名刀が、信仰の象徴ではなく「担保」として扱われる可能性があります。
信仰の記憶を守るはずの制度が、いつ債権者の回収手続きへ接続するのか。その衝撃を、数字と文書から追跡します。

=== ACT II ===
報道の見出しは、「元宮司が借金を残した」という単純な筋書きに流れやすいものです。
しかし、神社の破綻は一個人のモラル崩壊だけで起きるものではありません。
背後には、宗教法人規則、責任役員会の議決、総代会の承認という制度的な防壁がありました。

=== ACT III ===
調査の記録の痕跡は、登記簿から始まります。次に、宗教法人の規則、責任役員の決議録、公告の記録、融資契約、担保契約、送金記録です。
問題は、誰がその契約書に押印したのかという点です。
神社の財産を処分するには、包括宗教法人の承認や規則に基づく手続きが必要です。

=== ACT IV ===
決定的な証拠は、「鬼切丸が担保になった」という見出しではありません。所有権、担保の種類、対象物の特定、承認手続き、貸し手の素性です。
誰が担保権を実行できる立場にあるのか。
その登記上の権利者が誰であるかを特定しなければ、真の危機は見えてきません。

=== ACT V ===
民事再生を申し立てれば、担保財産は自動的に守られるのでしょうか？ 答えは、そうではありません。
神社の破綻が残した教訓は、信仰と金融の境界線が曖昧になったとき、文化財すら市場の流動性に呑み込まれるという冷酷な現実です。
後悔しないための備えとは何か。そこに、次の危機を防げるかどうかの答えがあります。
"""
    beats = extract_story_beats(cjk_story)
    assert len(beats) == 5
    for b in beats:
        assert not b["content"].startswith("===")
        assert not b["content"].startswith("ACT")

    archetype = detect_cinematic_archetype("Investigative Documentary", "多田神社", cjk_story)
    plan = _synthesize_deterministic_director_plan("JP_EP0001_test", beats, archetype)
    scenes = plan.get("scenes", [])
    assert len(scenes) >= 10
    # Zero header leak in narration
    for s in scenes:
        assert not s["narration"].startswith("===")
        assert not s["narration"].startswith("ACT")


def test_trigger_human_gate_2_contract():
    """Test that trigger_human_gate_2 handles non-existent task safely and returns None."""
    from app.services.telegram_buttons import trigger_human_gate_2
    res = trigger_human_gate_2("NON_EXISTENT_TASK_99999")
    assert res is None


def test_send_gate2_card_no_redundant_buttons():
    """Verify Human Gate 2 card has buttons=None and contains 1-click command without imgdone button (Rule 125)."""
    import asyncio
    from unittest.mock import patch, AsyncMock
    from app.services.telegram_buttons import send_gate2_card

    async def _run():
        with patch("app.services.telegram_buttons.send_with_buttons", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = 9999
            msg_id = await send_gate2_card(
                task_id="TEST_EP0001_clean_hg2",
                n_scenes=50,
                n_bg=25,
                n_fg=50,
                story_score="B2: 12/12 · B3.5.1: 8.6/10",
                topic="Test Topic Clean Gate",
                director_archetype="Fincher Noir"
            )
            assert msg_id == 9999
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            # Verify text content
            sent_text = args[0]
            assert "[HUMAN GATE 2]" in sent_text
            assert "/vf-image-gen" in sent_text
            assert "/run:image --episode TEST_EP0001_clean_hg2 --headless" in sent_text
            assert "imgdone" not in sent_text

            # Verify buttons argument is None (Rule 125 - Zero Ghost Code)
            sent_buttons = kwargs.get("buttons") if "buttons" in kwargs else (args[1] if len(args) > 1 else None)
            assert sent_buttons is None

    asyncio.run(_run())


