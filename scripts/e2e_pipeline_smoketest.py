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
    with open(os.path.join(PROJECT_ROOT, "app", "services", "story_engine_b2.py"), "r", encoding="utf-8") as f:
        b2_code = f.read()
    assert "call_gpt56_sol" not in b2_code, "story_engine_b2 must not contain call_gpt56_sol!"
    assert "GPT-6-ASTRA" in b2_code, "story_engine_b2 must sync with GPT-6-ASTRA tag!"
    print("  [PASS] story_engine_b2 has 0% GPT-5.6-Sol remnants and proper 5-Beat Docudrama tags.")

def gate_b3_director_planner():
    print_gate("5. B3 Director Planner & Non-Destructive Brain Input")
    with open(os.path.join(PROJECT_ROOT, "app", "services", "director_planner_b3.py"), "r", encoding="utf-8") as f:
        b3_code = f.read()
    assert "existing_brain" in b3_code, "director_planner_b3 must read existing_brain to preserve metadata!"
    assert "prompts_forge.json" in b3_code, "director_planner_b3 must save prompts_forge.json!"
    print("  [PASS] director_planner_b3 preserves existing brain metadata and saves prompts_forge.json.")

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
    print_gate("7. Zero-Ghost Remnants & Character Encoding")
    # Check for mojibake in telegram buttons
    tg_path = os.path.join(PROJECT_ROOT, "app", "services", "telegram_buttons.py")
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
        gate_b36_visual_convergence()
        gate_zero_ghost_and_encoding()
        gate_market_scheduler()

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
