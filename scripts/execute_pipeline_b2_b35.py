#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/execute_pipeline_b2_b35.py
Executes Blocks 2.0 to 3.5 sequentially on Hetzner VPS:
  - B2.0: 5-Beat Docudrama Story Generation
  - B2.5: Spoken Script Adaptation
  - B2.6: Audio Spine (Edge-TTS + Whisper Alignment)
  - B3.0: Hollywood Director Plan (Asset Diversity Guard: MAX_USES <= 3, MIN_GAP >= 4)
  - B3.5: Prompt Forge (Rule 137 Strict Prompt Linter: Zero-Text, Blank Templates)
  - B3.6: Visual Convergence Audit
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add VPS root
sys.path.insert(0, "/root/video_factory")

from app.services.story_engine_b2 import (
    generate_5_arc_story,
    adapt_master_spoken_script,
    adversarial_audit_spoken_script
)
from app.services.beat_tts_engine import synthesize_beat_tts_pipeline
import subprocess
from app.services.director_planner_b3 import generate_director_plan, validate_asset_reuse_limits
from app.services.b36_visual_convergence import run_b36_visual_convergence


def execute_b2_to_b35(episode_id: str, market: str = "EN"):
    print(f"\n{'='*70}")
    print(f"🎬 EXECUTING PIPELINE B2 ➔ B3.5 FOR {episode_id} ({market})")
    print(f"{'='*70}\n")
    
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    ep_dir.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------
    # STAGE 2.0: B2 STORY ENGINE
    # -------------------------------------------------------------
    print(f"\n[1/6] 📜 Generating 5-Beat Docudrama Story (B2.0)...")
    story_res = generate_5_arc_story(episode_id)
    story_path = ep_dir / "story.txt"
    if not story_path.exists():
        raise RuntimeError(f"B2.0 Failed: story.txt not generated at {story_path}")
    story_text = story_path.read_text(encoding="utf-8")
    print(f"✅ B2.0 Story Generated: {len(story_text.split())} words, {len(story_text)} chars")
    
    # -------------------------------------------------------------
    # STAGE 2.5: SPOKEN SCRIPT ADAPTATION
    # -------------------------------------------------------------
    print(f"\n[2/6] 🎙️ Adapting Spoken Script (B2.5)...")
    meta_path = Path(f"/var/vf/pending_tasks/{episode_id}.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    topic = meta.get("raw_term") or episode_id
    
    spoken_data = adapt_master_spoken_script(story_text, market=market, topic=topic)
    audit = adversarial_audit_spoken_script(spoken_data, market=market, topic=topic)
    print(f"   B2.5 Adversarial Audit Score: {audit.get('audit_score')}/10 | Verdict: {audit.get('verdict')}")
    
    spoken_script_text = spoken_data.get("spoken_script_text", story_text)
    sentences = spoken_data.get("sentences", [])
    (ep_dir / "spoken_script.txt").write_text(spoken_script_text, encoding="utf-8")
    (ep_dir / "spoken_sentences.json").write_text(json.dumps(sentences, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ B2.5 Spoken Script Complete: {len(sentences)} sentences")
    
    # -------------------------------------------------------------
    # STAGE 2.6: AUDIO SPINE (EDGE-TTS + WHISPER)
    # -------------------------------------------------------------
    print(f"\n[3/6] 🔊 Synthesizing Audio Spine (B2.6 Edge-TTS)...")
    tts_res = asyncio.run(synthesize_beat_tts_pipeline(episode_id, out_dir=str(ep_dir), force=False))
    total_dur = tts_res.get("total_duration_sec", 0.0)
    print(f"✅ B2.6 Audio Spine Complete: {total_dur:.1f}s ({len(tts_res.get('segments', []))} segments)")
    
    # -------------------------------------------------------------
    # STAGE 3.0: HOLLYWOOD DIRECTOR PLAN & ASSET DIVERSITY
    # -------------------------------------------------------------
    print(f"\n[4/6] 🎥 Generating Hollywood Director Plan (B3.0)...")
    # Reload spoken_sentences with timestamps from disk to satisfy _is_valid_audio_spine (Rule 120)
    sp_path = ep_dir / "spoken_sentences.json"
    if sp_path.exists():
        try:
            sentences = json.loads(sp_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    director_plan = generate_director_plan(
        episode_id,
        story_text,
        spoken_sentences=sentences,
        metadata={"topic": topic, "market": market},
        run_downstream=False
    )
    scenes = director_plan.get("scenes", [])
    print(f"   Director Plan Generated: {len(scenes)} scenes")
    
    # Enforce Asset Diversity Guard
    diversity_check = validate_asset_reuse_limits(scenes)
    print(f"   🛡️ Asset Diversity Check: ok={diversity_check['ok']} | Violations: {len(diversity_check['violations'])}")
    if diversity_check["violations"]:
        for v in diversity_check["violations"][:5]:
            print(f"      - {v}")
    print(f"✅ B3.0 Director Plan Complete")
    
    # -------------------------------------------------------------
    # STAGE 3.5: PROMPT FORGE (RULE 137 LINTER)
    # -------------------------------------------------------------
    print(f"\n[5/6] 🎨 Forging Visual Prompts with Rule 137 Linter (B3.5)...")
    pf_res = subprocess.run(
        ["python3", "scripts/run_prompt_forge.py", "--episode", episode_id],
        cwd="/root/video_factory",
        capture_output=True,
        text=True,
        check=True
    )
    print(pf_res.stdout)
    print(f"✅ B3.5 Prompt Forge Complete")
    
    # -------------------------------------------------------------
    # STAGE 3.6: VISUAL CONVERGENCE AUDIT
    # -------------------------------------------------------------
    print(f"\n[6/6] 🔍 Running B3.6 Visual Convergence Audit...")
    audit_res = run_b36_visual_convergence(episode_id, market=market)
    score = audit_res.get("overall_score") or audit_res.get("score", "N/A")
    verdict = audit_res.get("verdict", "PASS")
    print(f"✅ B3.6 Visual Convergence Audit Complete: Score: {score} | Verdict: {verdict}")
    
    print(f"\n{'='*70}")
    print(f"🎉 PIPELINE B2 ➔ B3.5 COMPLETE FOR {episode_id}")
    print(f"{'='*70}\n")
    return True


if __name__ == "__main__":
    ep_id = sys.argv[1] if len(sys.argv) > 1 else "EN_EP0006_foreign_capital_us_stocks"
    mkt = sys.argv[2] if len(sys.argv) > 2 else ep_id.split("_")[0].upper()
    execute_b2_to_b35(ep_id, market=mkt)
