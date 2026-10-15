#!/usr/bin/env python3
"""tests/vox/test_rule_131_and_136.py — Rigorous Tests for Rule 131 (5-Beat Structure) and Rule 136 (Clean Speaker & Beat Headers).

Governed by:
- Rule 131: 5-Beat Docudrama Story Engine & Narrative Arc (Beat 1 Cold Strike -> Beat 2 False Narrative -> Beat 3 Paper Trail -> Beat 4 Climax -> Beat 5 Living Warning).
- Rule 136: Zero-Asset-Leak Speaker Tag & Beat Header Mandate: No internal prefixes, speaker cues, or beat labels leaked into TTS audio or ASS subtitles.
"""

from pathlib import Path

from vox.karaoke import generate_ass_subtitles, parse_words_from_ass
from vox.planner import plan_scenes_from_script, sanitize_narration_line
from vox.schemas import Word, WordTimeline


def test_sanitize_narration_line_strips_speaker_tags():
    """Rule 136: Strips speaker prefixes from speech lines."""
    raw = "NARRATOR: In September 2008, the repo market froze completely."
    cleaned = sanitize_narration_line(raw)
    assert cleaned == "In September 2008, the repo market froze completely."

    raw2 = "[SPEAKER: HOST] The balance sheet showed an unexpected void."
    cleaned2 = sanitize_narration_line(raw2)
    assert cleaned2 == "The balance sheet showed an unexpected void."

    raw3 = "HOST: (whispering) Nobody understood the contagion mechanism."
    cleaned3 = sanitize_narration_line(raw3)
    assert cleaned3 == "Nobody understood the contagion mechanism."


def test_sanitize_narration_line_strips_beat_headers_and_archive_tags():
    """Rule 136: Strips Beat headers and shadow archive tags."""
    raw1 = "BEAT 1: COLD STRIKE // Lehman Brothers faced catastrophic liquidity depletion."
    cleaned1 = sanitize_narration_line(raw1)
    assert cleaned1 == "Lehman Brothers faced catastrophic liquidity depletion."

    raw2 = "BEAT 2: THE FALSE NARRATIVE: Regulators insisted the system was adequately capitalized."
    cleaned2 = sanitize_narration_line(raw2)
    assert cleaned2 == "Regulators insisted the system was adequately capitalized."

    raw3 = "ARCHIVE 01 // Emergency discount window borrowings surged past hundreds of billions."
    cleaned3 = sanitize_narration_line(raw3)
    assert cleaned3 == "Emergency discount window borrowings surged past hundreds of billions."


def test_rule_131_5_beat_structure_planning():
    """Rule 131: 5-Beat docudrama script is decomposed into 5 distinct scenes with valid contracts."""
    script = """
    BEAT 1: COLD STRIKE // A sudden cascade of collateral margin calls immobilized interbank clearing.
    BEAT 2: FALSE NARRATIVE // Official communiques claimed counterparty exposures were fully hedged.
    BEAT 3: PAPER TRAIL // Forensic auditors unsealed secret bilateral credit agreements buried in subprime portfolios.
    BEAT 4: CLIMAX // Major clearing houses halted settlements, demanding immediate physical cash delivery.
    BEAT 5: LIVING WARNING // The structural fragilities exposed in the crisis remain latent across global shadow banks.
    """.strip()

    plan = plan_scenes_from_script(script, title="Financial Contagion 5-Beat Analysis")
    assert len(plan.scenes) == 5

    # Check that speaker / beat headers are stripped from all scenes (Rule 136)
    for sc in plan.scenes:
        assert not sc.narration.startswith("BEAT")
        assert " // " not in sc.narration
        assert len(sc.fg) >= 1
        assert len(sc.bg_prompt) >= 10

    # Check camera move diversity (no duplicate consecutive moves)
    for a, b in zip(plan.scenes, plan.scenes[1:]):
        assert a.camera != b.camera


def test_rule_136_ass_subtitles_contain_zero_speaker_or_beat_leakage(tmp_path: Path):
    """Rule 136: ASS subtitles generated from timeline contain zero speaker or beat header tokens."""
    script = "BEAT 1: COLD STRIKE // NARRATOR: The liquidity crisis immobilized global commerce."
    cleaned = sanitize_narration_line(script)
    assert cleaned == "The liquidity crisis immobilized global commerce."

    words_list = cleaned.split()
    words = []
    t = 0.0
    for w in words_list:
        words.append(Word(text=w, start=t, end=round(t + 0.4, 2), scene_idx=1))
        t = round(t + 0.45, 2)

    timeline = WordTimeline(words=words, audio_duration=t, match_ratio=1.0)
    ass_path = tmp_path / "subtitles.ass"
    generate_ass_subtitles(timeline, ass_path)

    ass_text = ass_path.read_text(encoding="utf-8")
    assert "BEAT" not in ass_text
    assert "NARRATOR" not in ass_text
    assert "COLD STRIKE" not in ass_text

    reconstructed = parse_words_from_ass(ass_path)
    recon_words = [w["text"] for w in reconstructed]
    assert "BEAT" not in recon_words
    assert "NARRATOR" not in recon_words
    assert "The" in recon_words
    assert "liquidity" in recon_words
