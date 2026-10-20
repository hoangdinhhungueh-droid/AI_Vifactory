# -*- coding: utf-8 -*-
"""tests/test_vox_automated_director.py
Unit tests for the Autonomous Vox Director Engine (Rule 118, 120, 128, 132).
"""

import pytest
from app.services.vox_automated_director import VoxAutomatedDirector


def test_niche_classification():
    director = VoxAutomatedDirector(market="EN")
    assert director.classify_niche("Federal bank failure and sovereign bond yields") == "money_power"
    assert director.classify_niche("The 1971 D.B. Cooper hijacking and FBI manhunt") == "crime_documentary"
    assert director.classify_niche("Ancient Roman civil war and Caesar's conquest") == "history"
    assert director.classify_niche("Aviation crash over the Andes mountains") == "disasters_survival"
    assert director.classify_niche("Silicon Valley semiconductor chip war and AI computing") == "technology"


def test_word_math_calculation():
    director = VoxAutomatedDirector(market="EN")
    assert director.compute_word_budget(30) == 75
    assert director.compute_word_budget(60) == 150
    assert director.compute_word_budget(120) == 300
    assert director.compute_word_budget(180) == 450


def test_script_dna_validation():
    director = VoxAutomatedDirector(market="EN")
    script = (
        "November 24, 1971. Portland International Airport. A calm passenger named Dan Cooper boards Flight 305 to Seattle. "
        "Midway through the flight, he hands flight attendant Florence Schaffner a quiet note claiming he has a bomb. "
        "He demands two hundred thousand dollars in cash and four parachutes upon landing. "
        "Federal authorities scramble, meeting his ransom demands in exchange for thirty-six passengers. "
        "The aircraft refuels and takes off toward Reno through a freezing November storm. "
        "Somewhere over southwest Washington, Cooper lowers the aft stairs and leaps into darkness. "
        "He was never found."
    )
    audit = director.validate_script_dna(script, duration_sec=35)
    assert audit["has_temporal_anchor"] is True
    assert audit["has_tight_ending"] is True
    assert audit["has_em_dash"] is False
    assert audit["score"] >= 8.0


def test_beat_breakdown_two_shot_cadence():
    director = VoxAutomatedDirector(market="EN", fps=30)
    script = (
        "November 24, 1971. Portland International Airport. A man in a dark suit buys a one-way ticket. "
        "He boards Northwest Orient Flight 305 carrying a heavy black briefcase."
    )
    beats = director.breakdown_beats(script, duration_sec=15)
    assert len(beats) >= 2
    for beat in beats:
        # Every beat must have exactly 2 shots: Shot A (Wide) and Shot B (Detail)
        assert len(beat["shots"]) == 2
        shot_a = beat["shots"][0]
        shot_b = beat["shots"][1]
        assert shot_a["type"] == "EST_WIDE"
        assert shot_a["has_headline"] is True
        assert len(shot_a["headline_text"]) > 0
        assert shot_b["type"] == "DETAIL_CUTIN"
        assert shot_b["has_headline"] is False
        assert shot_a["start_frame"] < shot_b["start_frame"]
        assert shot_b["end_frame"] == beat["end_frame"]


def test_remotion_manifest_generation():
    director = VoxAutomatedDirector(market="EN", fps=30)
    script = "November 24, 1971. Portland Airport. Dan Cooper boards the aircraft."
    beats = director.breakdown_beats(script, duration_sec=10)
    manifest = director.build_remotion_manifest(beats, theme="newsprint-editorial", topic="D.B. Cooper")

    assert manifest["fps"] == 30
    assert manifest["width"] == 1920
    assert manifest["height"] == 1080
    assert len(manifest["scenes"]) == len(beats)
    first_scene = manifest["scenes"][0]
    assert first_scene["component"] == "VoxBuildOnStage"
    assert first_scene["theme"] == "newsprint-editorial"
    assert len(first_scene["supportingCutouts"]) == 2
    assert len(first_scene["yarns"]) == 1


def test_thumbnail_generation():
    director = VoxAutomatedDirector(market="EN")
    thumbs = director.generate_thumbnails("D.B. Cooper Hijacking", "VANISHED", "newsprint-editorial")
    assert len(thumbs) == 3
    for t in thumbs:
        assert "censor bar" in t.lower()
        assert "16:9" in t
        assert "halftone" in t.lower()


def test_generate_ideas_state_2():
    director = VoxAutomatedDirector(market="EN")
    ideas = director.generate_ideas("crime_documentary", count=10)
    assert len(ideas) == 10
    for idx, idea in enumerate(ideas, 1):
        assert len(idea["title"]) > 10
        assert len(idea["hook"]) > 5
        # Ensure title follows non-clickbait documentary shapes
        assert any(prefix in idea["title"] for prefix in ["The ", "How ", "What ", "Why "])

    # Test with custom topic hint
    custom_ideas = director.generate_ideas("technology", count=5, topic_hint="Quantum Computing Race")
    assert len(custom_ideas) == 5
    assert "Quantum Computing Race" in custom_ideas[0]["title"]


def test_animation_duration_timing_6s_vs_10s():
    # 10s mode
    dir_10 = VoxAutomatedDirector(market="EN", fps=30, animation_duration_sec=10)
    beats = dir_10.breakdown_beats("November 24, 1971. Portland Airport. Dan Cooper buys a ticket.", duration_sec=10)
    manifest_10 = dir_10.build_remotion_manifest(beats, theme="newsprint-editorial")
    scene_10 = manifest_10["scenes"][0]
    assert scene_10["supportingCutouts"][0]["delaySec"] == 1.2
    assert scene_10["supportingCutouts"][1]["delaySec"] == 1.6
    assert scene_10["yarns"][0]["delaySec"] == 2.2
    assert manifest_10["meta"]["animationDurationSec"] == 10
    assert manifest_10["meta"]["buildEndSec"] == 7.0

    # 6s mode
    dir_6 = VoxAutomatedDirector(market="EN", fps=30, animation_duration_sec=6)
    manifest_6 = dir_6.build_remotion_manifest(beats, theme="newsprint-editorial")
    scene_6 = manifest_6["scenes"][0]
    assert scene_6["supportingCutouts"][0]["delaySec"] == 0.72
    assert scene_6["supportingCutouts"][1]["delaySec"] == 0.96
    assert scene_6["yarns"][0]["delaySec"] == 1.32
    assert manifest_6["meta"]["animationDurationSec"] == 6
    assert manifest_6["meta"]["buildEndSec"] == 3.8


def test_textify_bulk_prompts_format():
    director = VoxAutomatedDirector(market="EN")
    fake_manifest = [
        {"image_prompt": "Prompt Block 1: Hand-cut documentary paper collage on aged newsprint..."},
        {"image_prompt": "Prompt Block 2: Hand-cut documentary paper collage on aged newsprint..."},
        {"image_prompt": "Prompt Block 3: Hand-cut documentary paper collage on aged newsprint..."}
    ]
    bulk_text = director.format_textify_bulk_prompts(fake_manifest)
    blocks = bulk_text.split("\n\n")
    assert len(blocks) == 3
    for b in blocks:
        assert not b.startswith("#")
        assert not b.startswith("1.")
        assert "Hand-cut documentary paper collage" in b


def test_build_diorama_video_prompts_cl3_formula():
    director = VoxAutomatedDirector(market="EN", fps=30)
    script = (
        "November 24, 1971. Portland International Airport. A calm passenger boards Flight 305. "
        "Inside the cabin, Senator John Smith reviews a classified federal ledger with $200,000 missing. "
        "Deep inside the Washington canyon, the FBI search grid uncovers a critical smoking gun crisis. "
        "Ultimately, the vault remained empty and the case became an enduring mirror of institutional failure."
    )
    beats = director.breakdown_beats(script, duration_sec=40)
    video_prompts = director.build_diorama_video_prompts(beats, video_engine_mode="flow_veo_fast")

    assert len(video_prompts) == len(beats)
    alert_wash_count = 0
    style_blocks_seen = set()

    for vp in video_prompts:
        style_blocks_seen.add(vp["style_block_type"])
        assert vp["style_block_type"] in ("FLAT_PARALLAX", "DEEP_DIORAMA", "LOCKED_STAGE")
        assert "Use the attached style sheet" in vp["video_prompt"]
        assert "SHOT:" in vp["video_prompt"]
        assert "Settle " in vp["video_prompt"]
        assert "AUDIO:" in vp["video_prompt"]
        assert "AVOID:" in vp["video_prompt"]
        assert vp["trim_start_sec"] == 0.25
        assert vp["retain_native_sfx_volume"] == 0.18
        assert vp["style_reference_sheet"] == "config/prompts/vox_master_style_sheet.png"
        # Ensure public figure name "John Smith" was scrubbed from video prompt
        assert "John Smith" not in vp["video_prompt"]
        if vp["is_alert_wash"]:
            alert_wash_count += 1

    # Rule: Max 1 ALERT WASH per sequence
    assert alert_wash_count == 1
    assert len(style_blocks_seen) >= 2


def test_low_token_36_and_omni_48_budget_modes():
    from app.services.unified_vox_director import (
        select_dynamic_hero_indices,
        inject_speech_timestamp_cue
    )

    sents = [
        {"index": i, "text": f"Sentence {i} reveals a $500 million crisis and sudden collapse in the vault.", "duration_sec": 6.0}
        for i in range(120)
    ]

    std_indices = select_dynamic_hero_indices(sents, video_budget_mode="standard_18")
    low_token_indices = select_dynamic_hero_indices(sents, video_budget_mode="low_token_36")
    omni_indices = select_dynamic_hero_indices(sents, video_budget_mode="omni_48")

    assert 12 <= len(std_indices) <= 22
    assert len(low_token_indices) == 36
    assert len(omni_indices) == 48

    cue = inject_speech_timestamp_cue(sents[0], dur_sec=6.0)
    assert cue.startswith("At ")
    assert "s when narration hits" in cue or "s mid-sentence beat" in cue
    assert "trigger primary" in cue


def test_production_b2_hg2_s45_handoff_parity(tmp_path, monkeypatch):
    """Verify live production B2 -> HG1 -> B3.5 -> HG2 -> S4.5 handoff preserves all Vox & CL3 upgrades."""
    import json
    from app.services.story_gate import score_story
    from app.services.build_remotion_props import build_remotion_props_data

    monkeypatch.setattr("app.services.hhtech_reasoner.call_gpt6_astra", lambda *a, **kw: "")
    monkeypatch.setenv("DISABLE_LLM_TIMELINE_DIRECTOR", "1")

    # 1. Verify live B2 story_gate.score_story includes cliffhanger_audit
    sample_story = (
        "On March 14, 2024, $4.2 billion vanished from the clearing house ledger in 18 minutes. "
        "Wait, why did the auditor sign off on an empty vault? "
        "Then came the secret memo from Geneva. "
        "Then, in 2024, the records unsealed."
    )
    gate_res = score_story(sample_story)
    assert "cliffhanger_audit" in gate_res
    assert gate_res["cliffhanger_audit"]["matched"] is True
    assert gate_res["cliffhanger_audit"]["pattern"] == "THE_DATED_FORWARD_JUMP"

    # 2. Verify S4.5 build_remotion_props_data forwards CL3 Paper Diorama fields & meta
    brain_path = tmp_path / "brain_input.json"
    seg_path = tmp_path / "spoken_sentences.json"
    brain_payload = {
        "episode_id": "EN_EP9999_test_parity",
        "topic": "Test Parity",
        "theme": "newsprint-editorial",
        "video_engine_mode": "flow_veo_fast",
        "video_budget_mode": "low_token_36",
        "meta": {
            "generatedBy": "VoxAutomatedDirector",
            "videoEngineMode": "flow_veo_fast",
            "videoBudgetMode": "low_token_36",
            "trimStartSec": 0.25,
            "nativeSfxVolume": 0.18,
            "styleReferenceSheet": "config/prompts/vox_master_style_sheet.png",
        },
        "scenes": [
            {
                "id": "scene_01",
                "beat_index": 1,
                "durationInFrames": 180,
                "durationSec": 6.0,
                "headline": "EXHIBIT #1",
                "narration": "On March 14, $4.2 billion vanished.",
                "background_reuse_key": "bg_01",
                "foreground_reuse_key": "fg_01",
                "paper_material": {"id": "newsprint_aged", "hex": "#E8DFCA"},
                "diorama_style_block": "DEEP_DIORAMA",
                "video_prompt": "STYLE BLOCK\n\nSHOT:\nBackground...\n\nAUDIO:...\n\nAVOID:...",
                "speech_timestamp_cue": "At 1.2s when narration hits '$4.2 billion', trigger primary",
                "named_escalation_beat": "ALERT WASH",
                "routed_video_model": "flow_veo_fast",
                "flow_slot": "gmail_slot_1",
            }
        ],
    }
    brain_path.write_text(json.dumps(brain_payload), encoding="utf-8")
    seg_path.write_text(
        json.dumps([{"index": 1, "text": "On March 14, $4.2 billion vanished.", "start_sec": 0.0, "end_sec": 6.0, "duration_sec": 6.0}]),
        encoding="utf-8",
    )

    props = build_remotion_props_data(
        episode_id="EN_EP9999_test_parity",
        brain_input_path=str(brain_path),
        segments_path=str(seg_path),
        fps=30,
        skip_missing=False,
    )
    assert "meta" in props
    assert props["meta"]["videoEngineMode"] == "flow_veo_fast"
    assert props["meta"]["videoBudgetMode"] == "low_token_36"
    assert props["meta"]["trimStartSec"] == 0.25
    assert props["meta"]["nativeSfxVolume"] == 0.18
    sc0 = props["scenes"][0]
    assert sc0["diorama_style_block"] == "DEEP_DIORAMA"
    assert "STYLE BLOCK" in sc0["video_prompt"]
    assert sc0["named_escalation_beat"] == "ALERT WASH"
    assert sc0["paper_material"]["id"] == "newsprint_aged"


def test_round3_beat_phase_and_layout_anti_collision(tmp_path, monkeypatch):
    """Verify 30+ sentence beats do not collide with 5-Beat act phases or poison layout variants/heroPosition."""
    import json
    from app.services.build_remotion_props import build_remotion_props_data
    from scripts.orchestrator.adversarial_director_gate import auto_repair_props

    monkeypatch.setattr("app.services.hhtech_reasoner.call_gpt6_astra", lambda *a, **kw: "")
    monkeypatch.setenv("DISABLE_LLM_TIMELINE_DIRECTOR", "1")

    director = VoxAutomatedDirector(market="EN", fps=30)
    sentences = [
        f"Sentence {i + 1} exposes a critical $250 million sovereign audit discrepancy in vault {i + 1}."
        for i in range(30)
    ]
    script_text = " ".join(sentences)
    beats = director.breakdown_beats(script_text, duration_sec=180)
    assert len(beats) == 30

    prompts_manifest = director.forge_image_prompts(
        beats=beats,
        theme="newsprint-editorial",
        topic="Sovereign Treasury Vault Discrepancy",
        story_text=script_text,
    )
    assert len(prompts_manifest) == 30
    assert len(director.last_bg_roster) >= 30

    # Zero consecutive BG repeats
    for i in range(1, len(prompts_manifest)):
        assert prompts_manifest[i]["bg_key"] != prompts_manifest[i - 1]["bg_key"]
        assert prompts_manifest[i]["paper_material"] is not None

    manifest = director.build_remotion_manifest(
        beats=beats,
        theme="newsprint-editorial",
        topic="Sovereign Vault Discrepancy",
        episode_id="EN_EP9998_round3_test",
    )

    brain_path = tmp_path / "brain_input.json"
    seg_path = tmp_path / "spoken_sentences.json"
    brain_path.write_text(
        json.dumps(
            {
                "episode_id": "EN_EP9998_round3_test",
                "market": "EN",
                "topic": "Sovereign Vault Discrepancy",
                "theme": "newsprint-editorial",
                "scenes": manifest["scenes"],
            }
        ),
        encoding="utf-8",
    )
    seg_path.write_text(
        json.dumps(
            [
                {
                    "index": i + 1,
                    "text": sentences[i],
                    "start_sec": i * 6.0,
                    "end_sec": (i + 1) * 6.0,
                    "duration_sec": 6.0,
                }
                for i in range(30)
            ]
        ),
        encoding="utf-8",
    )

    props = build_remotion_props_data(
        episode_id="EN_EP9998_round3_test",
        brain_input_path=str(brain_path),
        segments_path=str(seg_path),
        fps=30,
        skip_missing=False,
    )
    scenes = props["scenes"]
    assert len(scenes) == 30

    # First 4 scenes (<= 15% of 30) must ALL stay in Beat 1 (never jumping 1->2->3->4->5->1)
    first_four_beats = [s["beat_index"] for s in scenes[:4]]
    assert first_four_beats == [1, 1, 1, 1]

    # Beat phases across entire 30-scene episode must progress monotonically 1 -> 2 -> 3 -> 4 -> 5
    all_beats = [s["beat_index"] for s in scenes]
    assert all_beats == sorted(all_beats)
    assert set(all_beats) == {1, 2, 3, 4, 5}

    # Check layout variants and non-centered heroPosition
    variants_seen = {s["layoutVariant"] for s in scenes}
    assert variants_seen == {"paper_collage", "cinematic_doc", "kinetic_headline", "evidence_dossier"}
    for s in scenes:
        assert s["heroPosition"]["xPct"] != 50
        assert s["background"].endswith(".png")
        if s["layoutVariant"] != "paper_collage":
            assert s["supportingCutouts"] == []
            assert s["yarns"] == []

    # Verify auto_repair_props transitions pruned FG scenes to cinematic_doc
    repaired = auto_repair_props(props, market="EN")
    for s in repaired["scenes"]:
        if not s.get("foreground"):
            assert not s.get("heroSrc")
            assert s.get("layoutVariant") not in ("evidence_dossier", "paper_collage")


def test_round3_part2_midstream_and_chapter_sync_integrity(tmp_path, monkeypatch):
    """Verify Round 3 Part 2 fixes across editorial_briefing_generator, timeline_editor_agent, and seo_package_forge."""
    import json
    from app.services.editorial_briefing_generator import select_climax_scenes, prune_and_localize_scenes
    from app.services.timeline_editor_agent import audit_and_optimize_timeline
    from app.services.seo_package_forge import sync_exact_chapters_from_remotion

    monkeypatch.setenv("DISABLE_LLM_TIMELINE_DIRECTOR", "1")

    # 1. Verify select_climax_scenes and prune_and_localize_scenes respect 1..5 beat phases on 20-scene input
    raw_scenes = []
    for i in range(20):
        b_phase = 1 if i < 4 else (2 if i < 8 else (3 if i < 12 else (4 if i < 16 else 5)))
        raw_scenes.append({
            "scene_id": f"scene_{i + 1:02d}",
            "beat_index": i + 1,  # sequential sentence index 1..20
            "beat_phase": b_phase,
            "narration": f"Scene {i + 1} reveals $450 million in the bank vault without any warning.",
            "foreground": f"fg_{(i % 4) + 1:02d}.png",
            "background": f"bg_{(i % 6) + 1:02d}.png",
            "speakerTag": f"BEAT {b_phase}: GENERIC TOPIC HEADER: SOVEREIGN AUDIT TRAIL PHASE {b_phase}",
            "statValue": "$450M",
            "durationInFrames": 360,
        })

    climax = select_climax_scenes(raw_scenes, target_count=5)
    assert len(climax) == 5

    pruned = prune_and_localize_scenes([dict(s) for s in raw_scenes], market="EN")
    pruned_beats = [s["beat_index"] for s in pruned]
    assert pruned_beats == [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5]
    for s in pruned:
        assert "GENERIC TOPIC HEADER:" not in s["speakerTag"]
        ov = s.get("forensicOverlay")
        if isinstance(ov, dict):
            assert ov.get("sfx_cue") != "shutter_click"
            if ov.get("type") == "kinetic_counter":
                assert ov.get("payload", {}).get("end_value") is not None

    # 2. Verify timeline_editor_agent does NOT trigger false word-punch on substring words ("bank", "afraid", "believe", "warning")
    test_scenes = [
        {
            "id": "scene_01",
            "beat_index": 1,
            "beat_phase": 1,
            "durationInFrames": 90,  # 3.0s (0..3000ms)
            "speakerTag": "BEAT 1: THE COLD STRIKE",
            "actTitle": "ACT I // THE HOOK & EXPOSURE",
            "cameraMovement": "slow_push_in",
        },
        {
            "id": "scene_02",
            "beat_index": 1,
            "beat_phase": 1,
            "durationInFrames": 90,  # 3.0s (3000..6000ms)
            "speakerTag": "AUDITOR // FEDERAL RESERVE",
            "actTitle": "ACT I // THE HOOK & EXPOSURE",
            "cameraMovement": "pan_right",
        },
    ]
    whisper_words = [
        {"word": "urban", "start_ms": 200, "end_ms": 500},
        {"word": "bank", "start_ms": 600, "end_ms": 1000},
        {"word": "afraid", "start_ms": 1100, "end_ms": 1500},
        {"word": "believe", "start_ms": 1600, "end_ms": 2000},
        {"word": "warning", "start_ms": 2100, "end_ms": 2600},
        {"word": "collapse", "start_ms": 3500, "end_ms": 4200},
    ]
    refined = audit_and_optimize_timeline(
        test_scenes,
        whisper_words=whisper_words,
        options={"episode_id": "EN_EP9997_test", "enable_llm_director": False},
    )
    # Scene 1 has only substring matches ("urban", "bank", "afraid", "believe", "warning") -> must NOT punch
    assert refined[0]["cameraMovement"] == "slow_push_in"
    # Scene 2 has exact token "collapse" -> must trigger snap_zoom
    assert refined[1]["cameraMovement"] == "snap_zoom"

    # 3. Verify sync_exact_chapters_from_remotion does not create false chapter splits when speakerTag alternates with character names
    remotion_file = tmp_path / "remotion_props.json"
    chapter_scenes = []
    for b in range(1, 6):
        for sub_idx in range(3):
            chapter_scenes.append({
                "id": f"sc_{b}_{sub_idx}",
                "beat": b,
                "beat_index": b,
                "beat_phase": b,
                "speakerTag": f"BEAT {b}: PHASE {b}" if sub_idx != 1 else "WITNESS // TREASURY DEPT",
                "actTitle": f"ACT {b} // INVESTIGATION",
                "durationInFrames": 450,  # 15s per scene -> 45s per beat
            })
    remotion_file.write_text(json.dumps({"fps": 30, "scenes": chapter_scenes}), encoding="utf-8")
    chapters = sync_exact_chapters_from_remotion(
        existing_chapters=[
            "00:00 - The Hook",
            "01:00 - The Trap",
            "02:00 - The Paper Trail",
            "03:00 - The Smoking Gun",
            "04:00 - The Reckoning",
        ],
        market="EN",
        title="Test Investigation",
        target_keyword="Test Investigation",
        remotion_props_path=str(remotion_file),
    )
    # Must produce exactly 5 chapters at 00:00, 00:45, 01:30, 02:15, 03:00 (no false splits inside Beat 1..5)
    assert [c.split(" - ")[0] for c in chapters] == ["00:00", "00:45", "01:30", "02:15", "03:00"]


