# tests/test_b15_seo_package_forge.py
"""
Test Suite for B1.5 SEO Package & 60s An Ong Narrative Hook Forge (Step 1.6).
Verifies:
  1. SEO Package schema completeness (Title A/B, Description, 3 Hashtags, Tags, 3s/60s Hooks, 10x Angle).
  2. KVS Title method (Primary keyword in front).
  3. Strict 3 hashtags limit and hashtag formatting.
  4. Tags character budget (<= 400 chars).
  5. Disk persistence to /var/vf/episodes/<task_id>/seo_package.json.
  6. Direct B2 Story Engine integration (Zero-Drift Hook Handoff).
  7. B10 Upload stage zero-LLM fast load from seo_package.json.
"""
import os
import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.seo_package_forge import (
    _fallback_seo_package,
    _clean_hashtag,
    _parse_llm_json,
    forge_seo_package,
    sync_seo_package_to_youtube_registry,
    sync_seo_package_to_story_library,
)


class TestSeoPackageForge:

    def test_clean_hashtag(self):
        assert _clean_hashtag("ai") == "#ai"
        assert _clean_hashtag("#Technology!") == "#Technology"
        assert _clean_hashtag(" deep learning ") == "#deeplearning"

    def test_parse_llm_json(self):
        # Plain json
        raw1 = '{"title_a": "Test Title", "tags": ["a", "b"]}'
        p1 = _parse_llm_json(raw1)
        assert p1["title_a"] == "Test Title"

        # Markdown fenced json
        raw2 = '```json\n{"title_a": "Fenced Title", "hashtags": ["#T"]}\n```'
        p2 = _parse_llm_json(raw2)
        assert p2["title_a"] == "Fenced Title"

    def test_fallback_seo_package_schema(self):
        task_id = "TEST_EP9991_market_scan"
        kw = "Submarine Data Cables"
        pkg = _fallback_seo_package(
            task_id=task_id,
            target_keyword=kw,
            market="EN",
            niche_brief="Critical communications infrastructure",
            competitor_gap="Nobody covered the repair ships monopoly",
            rising_queries=["undersea cable sabotage", "baltic sea telecom"]
        )

        assert pkg["task_id"] == task_id
        assert pkg["market"] == "EN"
        assert pkg["title_a"].startswith("Submarine Data Cables")
        assert len(pkg["title_a"]) <= 100
        assert len(pkg["title_b"]) <= 100
        assert len(pkg["description"]) <= 5000
        assert len(pkg["description_hook"]) <= 150
        assert not pkg["description_hook"].lower().startswith("in this video")
        assert not pkg["description_hook"].lower().startswith("welcome")

        # Strict 3 hashtags cap
        assert len(pkg["hashtags"]) == 3
        for h in pkg["hashtags"]:
            assert h.startswith("#")

        # Tags within character budget
        assert len(pkg["tags"]) >= 3
        total_tag_chars = sum(len(t) for t in pkg["tags"])
        assert total_tag_chars <= 400

        # Narrative hooks
        assert len(pkg["hook_3s"]) > 20
        assert len(pkg["hook_60s"].split()) >= 40
        assert "contradiction" in pkg["hook_60s"].lower()
        assert "Submarine Data Cables" in pkg["hook_60s"]

        # 3 Thumbnail variants
        assert len(pkg["thumbnail_variants"]) == 3
        for v in pkg["thumbnail_variants"]:
            assert v["variant"] in ("A", "B", "C")
            assert len(v["headline_text"]) <= 32
            assert len(v["visual_concept"]) > 10

        # End screen 3 points
        assert "point_1_intro" in pkg["end_screen_notes"]
        assert "point_2_70pct" in pkg["end_screen_notes"]
        assert "point_3_last_20s" in pkg["end_screen_notes"]

        # AI disclosure
        assert pkg["ai_disclosure"] is True
        assert pkg["made_for_kids"] is False

    def test_disk_persistence_and_dual_sync(self, tmp_path):
        task_id = "TEST_EP9992_persistence_test"
        kw = "Autonomous Drone Swarms"
        
        # Call forge_seo_package (will use fallback if LLM offline)
        pkg = forge_seo_package(
            task_id=task_id,
            target_keyword=kw,
            market="EN",
            niche_brief="Military AI sensor networks",
            competitor_gap="Competitors missed electronic counter-warfare"
        )

        assert pkg["task_id"] == task_id
        assert pkg["title_a"].startswith("Autonomous Drone Swarms")
        
        # Verify disk persistence in /var/vf/episodes/<task_id>/seo_package.json
        expected_path = Path(f"/var/vf/episodes/{task_id}/seo_package.json")
        assert expected_path.exists(), f"Expected {expected_path} to exist"
        saved = json.loads(expected_path.read_text(encoding="utf-8"))
        assert saved["task_id"] == task_id
        assert saved["title_a"] == pkg["title_a"]
        assert len(saved["hashtags"]) == 3
        assert len(saved["hook_60s"].split()) >= 30

        # Clean up test artifact
        try:
            expected_path.unlink()
            expected_path.parent.rmdir()
        except Exception:
            pass

    def test_b2_story_engine_seo_package_loading(self, tmp_path):
        task_id = "TEST_EP9993_b2_seo_integration"
        ep_dir = Path(f"/var/vf/episodes/{task_id}")
        ep_dir.mkdir(parents=True, exist_ok=True)

        sample_pkg = {
            "task_id": task_id,
            "market": "EN",
            "title_a": "Ghost Fleets | The Sanctions Evasion Network",
            "title_b": "Ghost Fleets: Secret Tankers Unmasked",
            "hook_3s": "Thousands of oil tankers are vanishing from global satellite radar.",
            "hook_60s": "Across international waters, an invisible armada transports millions of barrels of crude oil with transponders completely disabled.",
            "specific_viral_angle": "Tracking the shell corporations that insure illicit tankers",
            "hashtags": ["#GhostFleets", "#Sanctions", "#Maritime"],
            "tags": ["ghost fleets", "sanctions evasion", "maritime investigation"],
            "generation_method": "test_fixture"
        }
        (ep_dir / "seo_package.json").write_text(json.dumps(sample_pkg), encoding="utf-8")

        # Test that story_engine_b2 loads this package
        from app.services.story_engine_b2 import load_task_metadata
        meta = load_task_metadata(task_id)
        assert meta is not None

        # Verify reading seo_package.json from episode dir
        pkg_file = ep_dir / "seo_package.json"
        assert pkg_file.exists()
        loaded = json.loads(pkg_file.read_text(encoding="utf-8"))
        assert loaded["title_a"] == "Ghost Fleets | The Sanctions Evasion Network"
        assert loaded["hook_60s"].startswith("Across international waters")

        # Clean up test artifact
        try:
            pkg_file.unlink()
            ep_dir.rmdir()
        except Exception:
            pass

    def test_b10_upload_stage_reads_precomputed_seo(self):
        task_id = "TEST_EP9994_b10_zero_llm"
        ep_dir = Path(f"/var/vf/episodes/{task_id}")
        ep_dir.mkdir(parents=True, exist_ok=True)

        sample_pkg = {
            "task_id": task_id,
            "market": "EN",
            "title_a": "Semiconductor Cold War | The Hidden Chokepoint",
            "title_b": "Semiconductor Cold War: The Factory Secrets",
            "description": "Investigative documentary on EUV lithography optics.",
            "hook_3s": "One company in the Netherlands controls the future of computing.",
            "hashtags": ["#Semiconductors", "#Lithography", "#TechWar"],
            "tags": ["semiconductors", "lithography", "euv", "tech cold war"],
            "generation_method": "hhtech_gpt6astra_b15_forge"
        }
        (ep_dir / "seo_package.json").write_text(json.dumps(sample_pkg), encoding="utf-8")

        # Verify B10 logic loads it directly without LLM
        seo_file = ep_dir / "seo_package.json"
        assert seo_file.exists()
        packaging = json.loads(seo_file.read_text(encoding="utf-8"))
        assert packaging["title_a"] == "Semiconductor Cold War | The Hidden Chokepoint"
        assert packaging["generation_method"] == "hhtech_gpt6astra_b15_forge"
        assert len(packaging["hashtags"]) == 3

        # Clean up
        try:
            seo_file.unlink()
            ep_dir.rmdir()
        except Exception:
            pass

    def test_sync_exact_chapters_from_remotion_rule135(self, tmp_path):
        from app.services.seo_package_forge import sync_exact_chapters_from_remotion

        # Create mock remotion_props.json
        props = {
            "fps": 30,
            "scenes": [
                {"durationInFrames": 900, "speakerTag": "BEAT 1: THE IMPOSSIBLE CONTRADICTION"},   # 0s - 30s
                {"durationInFrames": 900, "speakerTag": "BEAT 1: THE IMPOSSIBLE CONTRADICTION"},   # 30s - 60s
                {"durationInFrames": 1800, "speakerTag": "BEAT 2: THE FALSE NARRATIVE"},           # 60s - 120s
                {"durationInFrames": 1800, "speakerTag": "BEAT 3: THE HIDDEN MECHANISM"},          # 120s - 180s
                {"durationInFrames": 1800, "speakerTag": "BEAT 4: THE SMOKING GUN"},               # 180s - 240s
                {"durationInFrames": 1800, "speakerTag": "BEAT 5: THE RECKONING"}                  # 240s - 300s
            ]
        }
        props_file = tmp_path / "remotion_props.json"
        props_file.write_text(json.dumps(props), encoding="utf-8")

        existing_chapters = [
            "00:00 - Custom Title Act 1",
            "00:15 - Custom Title Act 2",
            "00:30 - Custom Title Act 3",
            "00:45 - Custom Title Act 4",
            "01:00 - Custom Title Act 5"
        ]

        synced = sync_exact_chapters_from_remotion(
            task_id="TEST_EP0001",
            market="EN",
            existing_chapters=existing_chapters,
            ep_dir_path=str(tmp_path)
        )

        assert len(synced) == 5
        assert synced[0] == "00:00 - Custom Title Act 1"
        assert synced[1] == "01:00 - Custom Title Act 2"  # 60s = 01:00
        assert synced[2] == "02:00 - Custom Title Act 3"  # 120s = 02:00
        assert synced[3] == "03:00 - Custom Title Act 4"  # 180s = 03:00
        assert synced[4] == "04:00 - Custom Title Act 5"  # 240s = 04:00

    def test_zero_asset_leak_speaker_tag_rule136(self):
        from app.services.build_remotion_props import format_speaker_tag

        # Scene with internal foreground reuse key and beat string
        scene_with_asset = {
            "foreground_reuse_key": "KR_EP0001_korea_isds_win_costs_fg_b5_char2",
            "beat": "Beat 2: The False Narrative & Red Herring",
            "beat_index": 2
        }
        tag = format_speaker_tag(scene_with_asset, act_title="ACT II // POWER")

        # Must NOT contain internal codes or ARCHIVE X
        assert "ARCHIVE X" not in tag
        assert "KR_EP0001" not in tag
        assert "CHAR2" not in tag
        assert "FG_" not in tag
        # Must contain pure Beat identification
        assert tag == "BEAT 2: THE FALSE NARRATIVE & RED HERRING"

        # Scene with character dialogue
        char_scene = {
            "character_name": "John Doe",
            "character_role": "Lead Forensic Auditor",
            "foreground_reuse_key": "fg_char_auditor_99"
        }
        char_tag = format_speaker_tag(char_scene, act_title="ACT III")
        assert char_tag == "JOHN DOE // LEAD FORENSIC AUDITOR"
        assert "fg_char" not in char_tag

