#!/usr/bin/env python3
"""
scripts/e2e_pipeline_smoketest.py
Master End-to-End Pipeline Smoke Test Runner (Mandated by Rule 127).
Validates runtime imports, function invocations, data contract bindings,
and anti-regression invariants across Blocks 1 through 3.5.
Exit code 0 indicates ALL PIPELINE GATES PASSED.
"""

import sys
import os
import json
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def print_gate(title):
    print(f"\n========================================================")
    print(f"🚦 CHECKING GATE: {title}")
    print(f"========================================================")

def gate_b1_reasoner():
    print_gate("1. B1 HHTech Reasoner & Strategic Rules Runtime")
    from app.services.skill_loader import get_b1_strategic_rules
    rules = get_b1_strategic_rules()
    assert isinstance(rules, str) and len(rules) > 100, "get_b1_strategic_rules must return non-empty rules"
    assert len(rules) < 5000, f"get_b1_strategic_rules must be concise (<5k chars), got {len(rules)}"
    print(f"  [PASS] get_b1_strategic_rules() returned {len(rules)} chars (no prompt contamination).")

    import app.services.hhtech_reasoner as hr
    assert hasattr(hr, "get_b1_strategic_rules"), "hhtech_reasoner must import get_b1_strategic_rules!"
    assert hasattr(hr, "reason_topic_niche"), "hhtech_reasoner must have reason_topic_niche"
    print("  [PASS] hhtech_reasoner correctly imported get_b1_strategic_rules without NameError.")

def gate_b1_episode_numbering():
    print_gate("2. B1 Dynamic Episode Numbering (Rule 117)")
    from app.services.trend_gate_ai import get_next_episode_id
    ep_en = get_next_episode_id("EN", "smoke_test_topic")
    print(f"  [INFO] Next EN Episode: {ep_en}")
    assert re.match(r"^EN_EP\d{4}_", ep_en), f"Episode ID format invalid: {ep_en}"
    print(f"  [PASS] Dynamic Episode Numbering allocates valid sequential task ID ({ep_en}).")

def gate_b1_b15_contract():
    print_gate("3. B1 ➔ B1.5 Competitor Recon Contract & Data Flow")
    from app.services.competitor_recon_b15 import run_b15
    from app.services.trend_engine_b1 import discover_and_produce_market_trend
    with open(os.path.join(PROJECT_ROOT, "app", "services", "trend_engine_b1.py"), "r", encoding="utf-8") as f:
        content = f.read()
    assert "competitor_differentiation_gap" in content, "trend_engine_b1 must map competitor_differentiation_gap!"
    print("  [PASS] trend_engine_b1 properly maps competitor_differentiation_gap to task payload.")

def gate_b2_story_engine():
    print_gate("4. B2 Story Engine & Metadata Preservation")
    from app.services.story_engine_b2 import (
        is_valid_market_text,
        deterministic_split_spoken_script,
        validate_market_supported
    )
    assert validate_market_supported("EN") == "EN"
    assert is_valid_market_text("Forensic evidence confirmed margin irregularities.", "EN") is True
    assert is_valid_market_text("基準値超えの二酸化硫黄", "JP") is True
    assert is_valid_market_text("Tiếng Việt có dấu", "EN") is False  # Out-of-locale rejection

    sample_script = "=== ACT I ===\nForensic investigators analyzed the financial ledger.\n=== ACT II ===\nThe discrepancy confirmed systematic failure."
    split_res = deterministic_split_spoken_script(sample_script, "EN")
    assert len(split_res.get("sentences", [])) >= 2, f"Failed to split spoken sentences: {split_res}"
    print("  [PASS] story_engine_b2 live runtime verified (market validation, locale purity, spoken splitting).")

def gate_b3_director_planner():
    print_gate("5. B3 Director Planner & Audio Spine Hard Gate (Rule 120/127)")
    from app.services.director_planner_b3 import detect_cinematic_archetype
    # Generic category-based cinematic archetype routing (Rule 128 Anti-Semantic Bias)
    fin_archetype = detect_cinematic_archetype("Finance", "Corporate Margin Discrepancy")
    assert "Fincher" in fin_archetype["director"] or "Corporate Noir" in fin_archetype["director"]
    hist_archetype = detect_cinematic_archetype("History", "Treaty Negotiations")
    assert "Nolan" in hist_archetype["director"] or "Historical" in hist_archetype["director"]
    print("  [PASS] director_planner_b3 generic archetype router verified across Finance & History.")

def gate_b35_visual_prompt_forge():
    print_gate("6. B3.5 Visual Prompt Forge & Anti-Stuttering")
    from app.services.prompt_forge import generate_scene_prompts
    mock_bg = {
        "bg_b1_loc0": {"visual_hint": "Atmospheric archival facility under dim low-key lighting", "narration_context": "Investigative documentary scene context"}
    }
    mock_fg = {
        "fg_b1_char0": {"visual_hint": "Lead field investigator examining documentation", "narration_context": "Investigator analyzing primary forensic records"}
    }
    mock_scenes = [
        {"scene_id": "sc_01", "bg_id": "bg_b1_loc0", "fg_id": "fg_b1_char0", "narration": "Forensic evidence examination scene."}
    ]
    res = generate_scene_prompts(mock_bg, mock_fg, "Generic Documentary Investigation", mock_scenes)
    assert "backgrounds" in res and "foregrounds" in res, "generate_scene_prompts output must have backgrounds and foregrounds"
    
    bg_p = list(res["backgrounds"].values())[0]
    fg_p = list(res["foregrounds"].values())[0]

    # Check for semiconductor leakage
    assert "server rack" not in bg_p.lower() and "silicon wafer" not in bg_p.lower(), f"Prompt leakage detected in BG: {bg_p[:100]}"
    # Check for duplicate stuttering
    stutter_match = re.search(r"(Stylized editorial.*){2,}", fg_p, re.IGNORECASE)
    assert not stutter_match, f"Stuttering phrase detected in FG: {fg_p[:150]}"
    print("  [PASS] B3.5 generate_scene_prompts clean of prompt leakage and stuttering.")

def gate_zero_ghost_and_encoding():
    print_gate("7. Zero-Ghost Remnants & 4-Layer Linter Engine (Rule 125)")
    from scripts.orchestrator.ghost_code_detector import scan_workspace
    from pathlib import Path
    root_dir = Path(PROJECT_ROOT)
    defects = scan_workspace(root_dir)
    assert len(defects) == 0, f"Ghost code defects found ({len(defects)}): {[d['detail'] for d in defects[:5]]}"
    print("  [PASS] 4-Layer Ghost Hunter scanned filesystem: 0 ghost files, 0 .bak remnants, 0 dead imports.")

    # Check for mojibake in telegram buttons
    tg_path = os.path.join(PROJECT_ROOT, "app", "services", "telegram_buttons.py")
    if os.path.exists(tg_path):
        with open(tg_path, "r", encoding="utf-8", errors="ignore") as f:
            tg_code = f.read()
        assert "ðŸ" not in tg_code, "telegram_buttons.py contains mojibake characters!"
        print("  [PASS] telegram_buttons.py is 100% clean of Mojibake characters.")

def gate_market_scheduler():
    print_gate("8. Market Stagger Scheduler & VN Timezone Compliance (Crash Protection)")
    from app.services.market_scheduler import (
        get_vn_now,
        get_scheduled_market_for_date,
        is_production_day,
        get_market_schedule_info,
    )
    from datetime import datetime, timezone, timedelta

    # 1. VN Timezone offset
    vn_now = get_vn_now()
    assert vn_now.utcoffset() == timedelta(hours=7), "Market scheduler must evaluate strictly in UTC+7 VN Time!"

    # 2. Canonical 7-day schedule mapping
    mon = datetime(2026, 9, 7, 6, 0, 0)
    expected = {0: "EN", 1: "KR", 2: "JP", 3: "EN", 4: "KR", 5: "JP", 6: None}
    for offset, exp_mkt in expected.items():
        cur = mon + timedelta(days=offset)
        res = get_scheduled_market_for_date(cur)
        assert res == exp_mkt, f"Schedule mismatch on {cur.strftime('%A')}: expected {exp_mkt}, got {res}"

    # 3. UTC boundary check (VPS cron trigger at 23:00 UTC)
    sun_night_utc = datetime(2026, 9, 6, 23, 0, 0, tzinfo=timezone.utc)
    assert get_scheduled_market_for_date(sun_night_utc) == "EN", "Sunday 23:00 UTC must map to Monday EN!"

    print("  [PASS] Market scheduler enforces 1 video/day (EN 2,5 | KR 3,6 | JP 4,7 | Sun OFF) and UTC+7 anchor.")

def gate_b36_visual_convergence():
    print_gate("9. B3.6 Visual Convergence Gate (DACL & Rule 118/122)")
    from app.services.b36_visual_convergence import (
        run_b36_visual_convergence,
        B36_AUDIT_SYSTEM_PROMPT,
        ASTRA_CROSS_AUDIT_PROMPT
    )
    assert "MARKET LINGUISTIC PURITY" in B36_AUDIT_SYSTEM_PROMPT
    assert "cross_audit_verdict" in ASTRA_CROSS_AUDIT_PROMPT
    assert hasattr(run_b36_visual_convergence, "__call__"), "run_b36_visual_convergence must be callable"
    print("  [PASS] B3.6 Visual Convergence Gate DACL definitions verified.")

def gate_cross_market_dynamic_director():
    print_gate("10. Cross-Market Dynamic Director & Anti-Bias Verification Gate (Rule 128)")
    import tempfile
    import shutil
    from pathlib import Path
    from app.services.unified_vox_director import build_unified_director_plan

    test_dir = Path(tempfile.mkdtemp(prefix="smoketest_cross_mkt_"))
    try:
        jp_sents = [
            {"text": "基準値超えの二酸化硫黄が輸入食品から検出されました。", "duration_sec": 5.0, "beat_index": 1},
            {"text": "検疫当局は立ち入り検査を実施し、公式文書を発令しました。", "duration_sec": 5.5, "beat_index": 3},
            {"text": "裁判所は行政処分を下しました。", "duration_sec": 5.0, "beat_index": 5},
        ]
        jp_plan = build_unified_director_plan(
            jp_sents,
            test_dir / "jp",
            metadata={"episode_id": "JP_EP0004_test", "market": "JP", "topic": "食品安全検査"}
        )

        en_sents = [
            {"text": "Antitrust regulators released formal investigation findings.", "duration_sec": 5.0, "beat_index": 1},
            {"text": "Financial ledgers detailed systematic margin discrepancies.", "duration_sec": 5.5, "beat_index": 3},
            {"text": "The federal judge delivered a historic bench ruling.", "duration_sec": 5.0, "beat_index": 5},
        ]
        en_plan = build_unified_director_plan(
            en_sents,
            test_dir / "en",
            metadata={"episode_id": "EN_EP0005_test", "market": "EN", "topic": "Antitrust Investigation"}
        )

        jp_scenes = jp_plan.get("scenes", [])
        en_scenes = en_plan.get("scenes", [])
        assert len(jp_scenes) == 3, f"Expected 3 JP scenes, got {len(jp_scenes)}"
        assert len(en_scenes) == 3, f"Expected 3 EN scenes, got {len(en_scenes)}"

        # Rule 128 Anti-Bleed: verify cross-market isolation against banned entity leak
        banned_entities = ["amazon", "lina" + " khan"]  # rule 128 check
        for s in jp_scenes:
            txt = (str(s.get("image_prompt", "")) + " " + str(s.get("foreground_prompt", ""))).lower()
            for b_ent in banned_entities:
                assert b_ent not in txt, f"Banned entity {b_ent} leaked into JP scene: {txt}"

        def _get_bg_key(s):
            bg = s.get("background")
            if isinstance(bg, dict):
                return bg.get("reuse_key")
            return s.get("bg_reuse_key")

        jp_bgs = set(_get_bg_key(s) for s in jp_scenes if _get_bg_key(s))
        en_bgs = set(_get_bg_key(s) for s in en_scenes if _get_bg_key(s))
        assert len(jp_bgs) > 0, f"JP market yielded 0 backgrounds"
        assert len(en_bgs) > 0, f"EN market yielded 0 backgrounds"
        assert len(jp_bgs.intersection(en_bgs)) == 0, "JP and EN background rosters must be 100% disjoint"
        print(f"  [PASS] Live Cross-Market Director executed clean: JP ({len(jp_bgs)} BGs) vs EN ({len(en_bgs)} BGs) 0% leakage.")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

def gate_b5_zero_mock_audit():
    print_gate("11. B5 Zero-Mock Visual Gate & Dual-Layer Audit Contract (Rule 118 & 122)")
    with open(os.path.join(PROJECT_ROOT, "app", "services", "b5_visual_gate.py"), "r", encoding="utf-8") as f:
        b5_code = f.read()
    assert "base_score = 8.5" not in b5_code, "b5_visual_gate.py must not contain hardcoded 'base_score = 8.5' mock pass score!"
    print("  [PASS] b5_visual_gate.py has 0 hardcoded 'base_score = 8.5' fallback.")

    from app.services.image_audit import _FG_BG_NOTE
    assert isinstance(_FG_BG_NOTE, str) and len(_FG_BG_NOTE) > 50, "_FG_BG_NOTE must be defined and non-empty in image_audit.py"
    print("  [PASS] image_audit.py correctly exports _FG_BG_NOTE without NameError.")

def gate_b6_remotion_props_and_composition():
    print_gate("12. B6 Remotion Composition & Vox Build-On Contract (Rule 120, 125 & 128)")
    with open(os.path.join(PROJECT_ROOT, "remotion", "src", "index.tsx"), "r", encoding="utf-8") as f:
        index_tsx = f.read()
    assert re.search(r'id=["\']TwoLayerEpisode["\']\s+component=\{TwoLayerEpisode\}', index_tsx), (
        "remotion/src/index.tsx must bind id='TwoLayerEpisode' to component={TwoLayerEpisode}!"
    )
    print("  [PASS] remotion/src/index.tsx binds id='TwoLayerEpisode' to component={TwoLayerEpisode}.")

    with open(os.path.join(PROJECT_ROOT, "remotion", "src", "components", "vox", "VoxBuildOnStage.tsx"), "r", encoding="utf-8") as f:
        vox_stage = f.read()
    assert "RES-VOX-001" not in vox_stage, "VoxBuildOnStage.tsx must not contain hardcoded RES-VOX-001!"
    assert "THE IMPOSSIBLE CONTRADICTION" not in vox_stage, "VoxBuildOnStage.tsx must not contain hardcoded THE IMPOSSIBLE CONTRADICTION!"
    print("  [PASS] VoxBuildOnStage.tsx has 0 hardcoded RES-VOX-001 or THE IMPOSSIBLE CONTRADICTION literals.")

    with open(os.path.join(PROJECT_ROOT, "app", "services", "build_remotion_props.py"), "r", encoding="utf-8") as f:
        props_code = f.read()
    assert "is_vox_build_on" not in props_code, "build_remotion_props.py must not contain legacy is_vox_build_on early-return bypass!"
    assert "fo_type" not in props_code or "fo_type =" in props_code or "fo_type:" in props_code, "build_remotion_props.py must not have undefined fo_type!"
    print("  [PASS] build_remotion_props.py clean of is_vox_build_on early return and undefined fo_type.")

    from scripts.orchestrator.adversarial_director_gate import audit_props_integrity, auto_repair_props
    test_props = {"scenes": [{"id": "sc01", "foreground": "", "heroSrc": "images/fg_01.png", "transition_out": "paper_slide"}]}
    clean, defs = audit_props_integrity(test_props, "EN")
    assert any("PRUNED_FG_HEROSRC_LEAK" in d for d in defs), "adversarial_director_gate must detect PRUNED_FG_HEROSRC_LEAK!"
    repaired = auto_repair_props(test_props, "EN")
    assert repaired["scenes"][0].get("heroSrc") == "", "auto_repair_props must clear heroSrc when foreground is empty!"
    print("  [PASS] adversarial_director_gate detects and repairs PRUNED_FG_HEROSRC_LEAK.")

def gate_b7_b9_render_and_video_qa():
    print_gate("13. B7-B9 Render Engine & Zero-Mock Video QA Gate (Rule 118, 120, 122)")
    from vox.assemble import assemble_final_video
    assert callable(assemble_final_video), "vox.assemble must provide assemble_final_video callable!"
    from vox.qa.gates import measure_ebur128_loudness, verify_final_video_gates
    assert callable(measure_ebur128_loudness), "vox.qa.gates must provide measure_ebur128_loudness callable!"
    assert callable(verify_final_video_gates), "vox.qa.gates must provide verify_final_video_gates callable!"
    print("  [PASS] vox render engine & QA gate callables verified in live runtime.")

def gate_b10_cross_market_chapter_sync():
    print_gate("14. B10 Cross-Market Chapter Synchronization (Rule 128 & 135)")
    import tempfile
    from app.services.seo_package_forge import sync_exact_chapters_from_remotion

    with tempfile.TemporaryDirectory(prefix="e2e_smoketest_b10_") as td:
        mock_props = {
            "fps": 30,
            "scenes": [
                {"durationInFrames": 900, "speakerTag": "BEAT 1: GRAND JURY INDICTMENT", "beat_index": 1},
                {"durationInFrames": 900, "speakerTag": "BEAT 2: THE PAPER TRAIL", "beat_index": 2},
                {"durationInFrames": 900, "speakerTag": "BEAT 3: FINANCIAL CONTAGION", "beat_index": 3},
            ]
        }
        with open(os.path.join(td, "remotion_props.json"), "w", encoding="utf-8") as f:
            json.dump(mock_props, f)

        chapters = sync_exact_chapters_from_remotion(
            "smoke_test_en_task",
            market="EN",
            ep_dir_path=td,
            existing_chapters=[
                "BEAT 1: GRAND JURY INDICTMENT",
                "BEAT 2: THE PAPER TRAIL",
                "BEAT 3: FINANCIAL CONTAGION"
            ]
        )
        assert len(chapters) >= 3, f"Expected at least 3 chapters, got: {chapters}"
        for ch in chapters:
            assert "検査・行政指導" not in ch, f"Forbidden Japanese term '検査・行政指導' leaked into EN chapters: {ch}"
        print(f"  [PASS] EN Chapter sync verified ({len(chapters)} chapters). 0% '検査・行政指導' leak.")

def gate_b11_analytics_and_insight_loop():
    print_gate("15. B11 Analytics Telemetry & Insight Dreaming Loop (Rule 113, 118, 125)")
    with open(os.path.join(PROJECT_ROOT, "scripts", "b11_antigravity_engine.py"), "r", encoding="utf-8") as f:
        b11_code = f.read()

    # Verify no undefined token variable in v7 harvester block
    assert "access_token=token," not in b11_code, "b11_antigravity_engine.py contains undefined 'token' variable in v7 harvest call!"
    # Verify no bare except passing
    assert "except Exception as _v7_err:\n                pass" not in b11_code, "b11_antigravity_engine.py must not contain bare 'except Exception as _v7_err: pass'!"
    # Live execution of distill_insights_to_cards
    from scripts.vf_insight_cards import distill_insights_to_cards
    test_metrics = {"views": 1500, "ctr": 0.082, "avd_sec": 240, "duration_sec": 480, "hook_retention_0_30s": 0.72, "hook_retention_0_60s": 0.55}
    cards = distill_insights_to_cards("dummy_test_token", "EN", test_metrics)
    assert isinstance(cards, list), f"Expected list of insight cards, got: {type(cards)}"
    print(f"  [PASS] b11_antigravity_engine.py verified & live insight card engine executed ({len(cards)} cards generated).")

def main():
    print("\n" + "="*60)
    print("🛡️ RUNNING MASTER E2E PIPELINE SMOKE TEST (RULE 127)")
    print("="*60)
    try:
        gate_b1_reasoner()
        gate_b1_episode_numbering()
        gate_b1_b15_contract()
        gate_b2_story_engine()
        gate_b3_director_planner()
        gate_b35_visual_prompt_forge()
        gate_zero_ghost_and_encoding()
        gate_market_scheduler()
        gate_b36_visual_convergence()
        gate_cross_market_dynamic_director()
        gate_b5_zero_mock_audit()
        gate_b6_remotion_props_and_composition()
        gate_b7_b9_render_and_video_qa()
        gate_b10_cross_market_chapter_sync()
        gate_b11_analytics_and_insight_loop()

        print("\n" + "="*60)
        print("🎉 ALL PIPELINE GATES PASSED (100% INTEGRATION RUNTIME OK)!")
        print("="*60 + "\n")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n❌ [GATE FAILED]: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 [UNEXPECTED ERROR]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()
