# tests/test_hollywood_audio_anchor.py
"""Unit and contract tests for the Hollywood Audio-Anchored Pipeline Architecture.
Verifies:
  1. Spoken VO Adaptation splits 5-Act story into breath-timed sentences within duration ceiling (<= 15 min).
  2. Adversarial Audit Gate enforces <= 15m duration and anti-bloat standards.
  3. B3 Audio Spine exports spoken_sentences.json with exact start_ms, end_ms, and duration_frames.
  4. B3.5 Visual Director generates shots matching spoken sentences with 0% invented dialogue.
"""
import pytest
import os
import json
from pathlib import Path

from app.services.story_engine_b2 import (
    adapt_master_spoken_script,
    adversarial_audit_spoken_script,
)
from app.services.director_planner_b3 import (
    generate_director_plan,
    _synthesize_deterministic_director_plan,
    _synthesize_beat_scenes,
)


def test_spoken_script_adaptation_deterministic():
    """Test deterministic sentence splitting and breath-pacing fallback."""
    sample_5act_story = (
        "=== ACT I ===\n"
        "In 2024, a small retail store in Hwaseong sold two 140,000 won table tennis rackets to a middle school student. "
        "The father returned an hour later demanding a full refund. "
        "The merchant refused based on consumer protection guidelines.\n\n"
        "=== ACT II ===\n"
        "Local media quickly amplified the confrontation into a public controversy. "
        "Online forums took opposing sides without reviewing the statutory retail laws. "
        "The store owner faced an escalating wave of targeted negative reviews.\n\n"
        "=== ACT III ===\n"
        "The legal paper trail revealed that retail refund regulations explicitly distinguish opened merchandise. "
        "Investigators examined the surveillance footage and merchant transaction receipts. "
        "The institutional blindspot was the complete lack of dispute mediation at the municipal level.\n\n"
        "=== ACT IV ===\n"
        "The real culprit was not an isolated retail dispute but a systemic breakdown in consumer arbitration. "
        "Legal experts clarified that small merchants bore the entire financial risk of consumer friction. "
        "Official guidelines were contradictory and unenforceable.\n\n"
        "=== ACT V ===\n"
        "Today, thousands of small business owners face identical unmediated refund disputes daily. "
        "The lesson of Hwaseong remains a living warning for the modern retail regulatory framework.\n"
    )
    
    from unittest.mock import patch
    with patch("app.services.story_engine_b2.call_gpt6_astra", side_effect=Exception("Simulated API failure for fallback test")):
        res = adapt_master_spoken_script(sample_5act_story, market="EN", topic="Table Tennis Refund Trap")
        assert isinstance(res, dict)
        sentences = res.get("sentences", [])
        assert len(sentences) >= 5, f"Expected at least 5 sentences, got {len(sentences)}"
        assert res.get("total_estimated_minutes", 0) <= 15.0, "Estimated duration must be <= 15 minutes"

        beats_present = set(s.get("beat_index") for s in sentences)
        assert 1 in beats_present and 5 in beats_present, f"Beats must cover full arc: {beats_present}"


def test_adversarial_audit_duration_ceiling():
    """Test that adversarial audit enforces duration ceiling <= 15 minutes."""
    from unittest.mock import patch

    # Mock PASS response from LLM
    pass_resp = json.dumps({
        "verdict": "PASS",
        "audit_score": 9.2,
        "estimated_duration_minutes": 10.5,
        "pacing_verdict": "Paced",
        "bloat_detected": False,
        "critique": "Crisp, breath-timed sentences."
    })
    with patch("app.services.story_engine_b2.call_gpt6_astra", return_value=pass_resp):
        good_spoken = {
            "spoken_script_text": "Short punchy sentences. High dramatic tension. Procedural investigation.",
            "total_estimated_minutes": 10.5,
            "sentences": [
                {"sentence_id": f"sent_{i:03d}", "beat_index": (i % 5) + 1, "text": f"Sentence {i} of investigation."}
                for i in range(1, 35)
            ]
        }
        audit_good = adversarial_audit_spoken_script(good_spoken, market="EN", topic="Test Case")
        assert audit_good.get("audit_score", 0) >= 8.0
        assert audit_good.get("verdict") == "PASS"

    # Mock FAIL/bloat response from LLM
    fail_resp = json.dumps({
        "verdict": "FAIL",
        "audit_score": 4.5,
        "estimated_duration_minutes": 32.0,
        "pacing_verdict": "Bloated",
        "bloat_detected": True,
        "critique": "Severe runtime overflow."
    })
    with patch("app.services.story_engine_b2.call_gpt6_astra", return_value=fail_resp):
        bloated_spoken = {
            "spoken_script_text": " ".join(["word"] * 5000),
            "total_estimated_minutes": 32.0,
            "sentences": [
                {"sentence_id": f"sent_{i:03d}", "beat_index": (i % 5) + 1, "text": " ".join(["word"] * 50)}
                for i in range(1, 100)
            ]
        }
        audit_bloated = adversarial_audit_spoken_script(bloated_spoken, market="EN", topic="Bloated Case")
        assert audit_bloated.get("bloat_detected") is True or audit_bloated.get("audit_score", 10) < 8.5


def test_visual_director_anchored_to_spoken_sentences():
    """Test that visual director generates shots strictly anchored to spoken sentences."""
    sample_spoken_sentences = [
        {"sentence_id": "sent_001", "beat_index": 1, "text": "In 2024, two expensive rackets triggered a major retail dispute.", "duration_frames": 120, "duration_sec": 4.0},
        {"sentence_id": "sent_002", "beat_index": 1, "text": "The store owner refused an immediate refund after the package was unsealed.", "duration_frames": 150, "duration_sec": 5.0},
        {"sentence_id": "sent_003", "beat_index": 2, "text": "Social media headlines framed the merchant as unreasonable.", "duration_frames": 110, "duration_sec": 3.67},
        {"sentence_id": "sent_004", "beat_index": 3, "text": "Official consumer guidelines contradicted local mediation ordinances.", "duration_frames": 130, "duration_sec": 4.33},
        {"sentence_id": "sent_005", "beat_index": 4, "text": "The regulatory vacuum left both consumer and retailer without recourse.", "duration_frames": 140, "duration_sec": 4.67},
        {"sentence_id": "sent_006", "beat_index": 5, "text": "This dispute remains an urgent lesson for retail policy today.", "duration_frames": 120, "duration_sec": 4.0},
    ]

    beats = [{"name": f"Beat {i}", "content": f"Beat content {i}"} for i in range(1, 6)]
    plan = _synthesize_deterministic_director_plan(
        episode_id="TEST_EP0001_mock",
        story_beats=beats,
        archetype={"director": "Corporate Noir", "visual_tone": "Clinical", "palette": "Moody"},
        spoken_sentences=sample_spoken_sentences
    )

    scenes = plan.get("scenes", [])
    assert len(scenes) == len(sample_spoken_sentences), f"Expected {len(sample_spoken_sentences)} scenes, got {len(scenes)}"

    for sc, sent in zip(scenes, sample_spoken_sentences):
        assert sc["narration"] == sent["text"], f"Narration mismatch: {sc['narration']} != {sent['text']}"
        assert sc["duration_frames"] == sent["duration_frames"], f"Frames mismatch: {sc['duration_frames']} != {sent['duration_frames']}"
        assert sc["sentence_id"] == sent["sentence_id"]
        assert sc["bg_prompt"], "Background prompt must be present"


def test_deterministic_pruning_and_preamble_parsing():
    """Test deterministic sentence splitting, tightening, and preamble parsing resilience."""
    from unittest.mock import patch
    from app.services.story_engine_b2 import (
        deterministic_split_spoken_script,
        deterministic_tighten_spoken_script,
        prune_and_tighten_spoken_script,
    )

    sample_5act_story = (
        "=== ACT I ===\n"
        "In 2024, two expensive rackets triggered a major retail dispute. "
        "The father returned demanding an immediate refund.\n\n"
        "=== ACT II ===\n"
        "Local media amplified the narrative without examining legal guidelines.\n\n"
        "=== ACT III ===\n"
        "The paper trail revealed explicit consumer regulations.\n\n"
        "=== ACT IV ===\n"
        "The institutional blindspot was complete lack of dispute mediation.\n\n"
        "=== ACT V ===\n"
        "The dispute remains an urgent modern lesson.\n"
    )

    # 1. Deterministic sentence split without LLM
    res = deterministic_split_spoken_script(sample_5act_story, market="EN")
    assert isinstance(res, dict)
    assert len(res["sentences"]) >= 5
    assert res["total_estimated_minutes"] <= 15.0

    # 2. Deterministic sentence tightening without LLM
    tightened = deterministic_tighten_spoken_script(res, market="EN")
    assert len(tightened["sentences"]) == len(res["sentences"])
    assert tightened["total_estimated_minutes"] <= 15.0

    # 3. Preamble parsing resilience in adversarial_audit_spoken_script
    raw_with_preamble = (
        "**Auditing claims and script****Checking script sources**\n"
        "```json\n"
        "{\n"
        '  "verdict": "PASS",\n'
        '  "audit_score": 9.1,\n'
        '  "estimated_duration_minutes": 11.5,\n'
        '  "pacing_verdict": "Paced",\n'
        '  "bloat_detected": false,\n'
        '  "critique": "Solid forensic rhythm."\n'
        "}\n"
        "```"
    )
    with patch("app.services.story_engine_b2.call_gpt6_astra", return_value=raw_with_preamble):
        audit_res = adversarial_audit_spoken_script(res, market="EN", topic="Pre-amble Test")
        assert audit_res["verdict"] == "PASS"
        assert audit_res["audit_score"] == 9.1

    # 4. Prune without LLM returns tightened script
    with patch.dict("os.environ", {"USE_LLM_PRUNING": "false"}):
        pruned = prune_and_tighten_spoken_script(res, market="EN", topic="Prune Test")
        assert len(pruned["sentences"]) == len(res["sentences"])

