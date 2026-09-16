"""
Unit tests for B3.6 Visual Convergence Gate (DACL).
Verifies Decremental Adversarial Convergence Loop between Opus 5 and Astra,
delta-only patching, zero mock data compliance, and contract structure.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.b36_visual_convergence import (
    run_b36_visual_convergence,
    B36_AUDIT_SYSTEM_PROMPT,
    ASTRA_CROSS_AUDIT_PROMPT
)


def test_b36_prompts_integrity():
    assert "MARKET LINGUISTIC PURITY" in B36_AUDIT_SYSTEM_PROMPT
    assert "HOLLYWOOD 7-AXIS" in B36_AUDIT_SYSTEM_PROMPT
    assert "#FF00FF" in B36_AUDIT_SYSTEM_PROMPT
    assert "2560x1440" in B36_AUDIT_SYSTEM_PROMPT
    assert "delta_patch" in B36_AUDIT_SYSTEM_PROMPT
    assert "REMOTION FORENSIC GRAPHICS" in B36_AUDIT_SYSTEM_PROMPT
    assert "cross_audit_verdict" in ASTRA_CROSS_AUDIT_PROMPT



def test_b36_round1_immediate_pass():
    fake_gateway = MagicMock()
    fake_gateway.call_llm.return_value = """{
        "verdict": "PASS",
        "audit_score": 9.2,
        "criteria_scores": {
            "market_linguistic": 9.5,
            "hollywood_pacing": 9.0,
            "fg_chroma_rule122": 9.5,
            "thumbnail_and_bg_style": 9.0,
            "prompt_hygiene": 9.5,
            "causal_dramatization": 9.0
        },
        "flawed_scene_ids": [],
        "flawed_prompt_keys": [],
        "red_flags": [],
        "critical_findings": "Storyboard demonstrates flawless execution."
    }"""

    with patch("app.services.b36_visual_convergence.get_global_gateway", return_value=fake_gateway), \
         patch("app.services.b36_visual_convergence.trigger_human_gate_2", create=True) as mock_hg2, \
         patch("app.services.telegram_buttons.trigger_human_gate_2") as mock_tb_hg2:
        res = run_b36_visual_convergence(
            episode_id="TEST_EP0001_tada_mock",
            director_plan={"topic": "Tada Shrine", "scenes": [{"scene_id": "SC_001", "narration": "こんにちは"}]},
            dp_plan={},
            prompts_data={"backgrounds": {}, "foregrounds": {}, "thumbnails": {}},
            story_text="Some story text",
            grounding_intel={"claims": ["Claim 1"]}
        )

        assert res["converged"] is True
        assert res["final_score"] == 9.2
        assert res["rounds_count"] == 1
        assert fake_gateway.call_llm.call_count == 1


def test_b36_round2_convergence_with_delta_patch():
    fake_gateway = MagicMock()
    # Round 1 returns FAIL with delta patch; Round 2 Astra returns PASS with cross_audit_score 8.7
    r1_opus = """{
        "verdict": "FAIL",
        "audit_score": 4.5,
        "criteria_scores": {"market_linguistic": 2.0},
        "flawed_scene_ids": ["SC_001"],
        "flawed_prompt_keys": ["thumbnail_a"],
        "red_flags": ["Scene 1 narration was translated into English"],
        "critical_findings": "Narration must be in Japanese.",
        "delta_patch": {
            "patched_scenes": [
                {
                    "scene_id": "SC_001",
                    "narration": "多田神社の国宝が競売にかけられました。",
                    "bg_prompt": "Stylized graphic novel illustration of Japanese shrine, 16:9",
                    "fg_prompt": "Stylized graphic novel illustration of monk, #FF00FF magenta background, 1:1",
                    "camera_movement": "Slow push-in",
                    "duration_est_sec": 7
                }
            ],
            "patched_thumbnails": {
                "thumbnail_a": "Stylized graphic novel hero illustration, 2560x1440 QHD"
            }
        }
    }"""
    r2_astra = """{
        "cross_audit_verdict": "PASS",
        "cross_audit_score": 8.7,
        "approval_rate": 0.95,
        "refined_delta": {
            "patched_scenes": [
                {
                    "scene_id": "SC_001",
                    "narration": "多田神社の重要文化財が競売にかけられました。",
                    "bg_prompt": "Stylized graphic novel illustration of Japanese shrine, 16:9",
                    "fg_prompt": "Stylized graphic novel illustration of monk, #FF00FF magenta background, 1:1",
                    "camera_movement": "Slow push-in",
                    "duration_est_sec": 7
                }
            ],
            "patched_thumbnails": {
                "thumbnail_a": "Stylized graphic novel hero illustration, 2560x1440 QHD"
            }
        },
        "audit_notes": "Polished Japanese terminology to exact cultural nuance."
    }"""

    fake_gateway.call_llm.side_effect = [r1_opus, r2_astra]

    with patch("app.services.b36_visual_convergence.get_global_gateway", return_value=fake_gateway), \
         patch("app.services.b36_visual_convergence.trigger_human_gate_2", create=True) as mock_hg2, \
         patch("app.services.telegram_buttons.trigger_human_gate_2") as mock_tb_hg2:
        res = run_b36_visual_convergence(
            episode_id="TEST_EP0001_tada_mock",
            director_plan={"topic": "Tada Shrine", "scenes": [{"scene_id": "SC_001", "narration": "English narration"}]},
            dp_plan={},
            prompts_data={"backgrounds": {}, "foregrounds": {}, "thumbnails": {"thumbnail_a": "old photorealistic"}},
            story_text="Some story text",
            grounding_intel={"claims": ["Claim 1"]}
        )

        assert res["converged"] is True
        assert res["final_score"] == 8.7
        assert res["rounds_count"] == 2
        assert fake_gateway.call_llm.call_count == 2
        # Verify that visual prompts merged into director_plan while narration remains locked to audio spine
        patched_s1 = res["director_plan"]["scenes"][0]
        assert patched_s1["narration"] == "English narration"
        assert "Stylized graphic novel" in patched_s1["bg_prompt"]
        assert "Slow push-in" in patched_s1["camera_movement"]
        # Verify patched thumbnail merged into prompts_data
        assert "2560x1440" in res["prompts_data"]["thumbnails"]["thumbnail_a"]
