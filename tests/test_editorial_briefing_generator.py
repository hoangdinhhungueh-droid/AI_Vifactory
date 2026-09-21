# tests/test_editorial_briefing_generator.py
"""Unit tests for editorial_briefing_generator.py.
Verifies overlay density pruning (< 20%), market localization, and briefing generation.
"""
import pytest
from app.services.editorial_briefing_generator import (
    extract_market_from_episode_id,
    select_climax_scenes,
    prune_and_localize_scenes,
    generate_editorial_briefing,
    LOCALIZED_OVERLAY_THEMES
)


def test_extract_market():
    assert extract_market_from_episode_id("JP_EP0003_hamaoka_data_fraud") == "JP"
    assert extract_market_from_episode_id("KR_EP0004_crypto_scheme") == "KR"
    assert extract_market_from_episode_id("VN_EP0002_scb_bank_run") == "VN"
    assert extract_market_from_episode_id("EN_EP0003_san_diego_daycare_fraud") == "EN"
    assert extract_market_from_episode_id("unknown_slug") == "EN"


def test_select_climax_scenes_density():
    # 72 scenes representing a real episode like JP_EP0003
    mock_scenes = []
    for i in range(72):
        beat = (i // 15) + 1
        mock_scenes.append({
            "scene_id": f"scene_{i:03d}",
            "beat_number": min(5, beat),
            "narration": f"Narration for scene {i}",
            "forensic_overlay": "document_highlight",
            "durationInFrames": 120,
        })
    # Add a quantitative metric to scene 2
    mock_scenes[2]["narration"] = "審査関連データ二百二十五件のうち、二百八件、実に九十二パーセントが不適切でした。"

    climax = select_climax_scenes(mock_scenes, target_count=7)
    assert len(climax) <= 8
    assert 2 in climax  # scene 2 has quantitative metric, must be chosen
    assert len(climax) >= 5  # at least 1 per beat


def test_prune_and_localize_scenes_japanese():
    mock_scenes = []
    for i in range(72):
        beat = (i // 15) + 1
        mock_scenes.append({
            "scene_id": f"scene_{i:03d}",
            "beat_number": min(5, beat),
            "narration": f"Narration for scene {i}",
            "forensic_overlay": "document_highlight",
            "speakerTag": "ARCHIVE X // INVESTIGATION",
            "durationInFrames": 120,
        })
    mock_scenes[2]["narration"] = "審査関連データ二百二十五件のうち、二百八件、実に九十二パーセントが不適切でした。"

    sanitized = prune_and_localize_scenes(mock_scenes, market="JP")

    overlay_count = sum(1 for s in sanitized if s.get("forensicOverlay"))
    density_pct = (overlay_count / len(sanitized)) * 100
    assert density_pct <= 20.0  # Vox rule: <= 20% overlay density

    # Non-climax scenes must have None overlay
    for idx, s in enumerate(sanitized):
        fo = s.get("forensicOverlay")
        if fo:
            # Overlays in Japanese episode must be in Japanese
            assert fo["title"] in [
                LOCALIZED_OVERLAY_THEMES["JP"]["counter_title"],
                LOCALIZED_OVERLAY_THEMES["JP"]["document_title"],
                LOCALIZED_OVERLAY_THEMES["JP"]["network_title"],
                LOCALIZED_OVERLAY_THEMES["JP"]["map_title"],
            ]
            assert "OFFICIAL INVESTIGATION RECORD" not in fo["title"]
            # Speaker tags must not be raw English or have ARCHIVE X
            assert "ARCHIVE X" not in s.get("speakerTag", "")


def test_generate_editorial_briefing(tmp_path):
    mock_scenes = [
        {"scene_id": f"sc_{i}", "beat_number": (i % 5) + 1, "narration": f"Scene {i}"}
        for i in range(50)
    ]
    briefing = generate_editorial_briefing("JP_EP0003_test", mock_scenes, output_dir=str(tmp_path))
    assert briefing["market"] == "JP"
    assert briefing["pacing_verdict"] == "APPROVED_VOX_MINIMALIST"
    assert (tmp_path / "editorial_briefing.json").exists()
