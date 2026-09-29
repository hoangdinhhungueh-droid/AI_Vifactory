#!/usr/bin/env python3
"""
scripts/archive_step2_assets.py
Safely archives Step 2+ stale artifacts on VPS into /var/vf/archive/<TASK_ID>_<TIMESTAMP>/
Preserves Step 1 research data: brain_input.json, competitor_intel_card.json, grounding_intel.json, flow_video_manifest.json.
"""

import sys
import os
import shutil
import time
from pathlib import Path

targets = [
    "EN_EP0006_foreign_capital_us_stocks",
    "KR_EP0006_ic_corp_fund_embezzlement"
]

ts = time.strftime("%Y%m%d_%H%M%S")
os.makedirs("/var/vf/archive", exist_ok=True)

step2_keys = [
    "story.txt", "spoken_script.txt", "spoken_sentences.json", "tts_out.mp3", 
    "subtitles.srt", "subtitles_en.srt", "subtitles_ko.srt", "audio_beats",
    "director_plan.json", "dp_plan.json", "editorial_briefing.json", 
    "prompts.json", "prompts_forge.json", "visual_convergence_audit.json",
    "images", "assets", "gate_stills", "thumbnails", "s7_checkpoint", "chunks",
    "final_169.mp4", "final_11.mp4", "final_916.mp4", "twolayer_silent.mp4", 
    "remotion_props.json", "audio_norm.mp3", "bgm_master.mp3", "bgm_director_decision.json", 
    "b5_audit_report.json", "llm_director_review.json", "quality_gate.json", 
    "resume_result.json", "b4b10_state.json", "post_render_sweep_report.json",
    "preflight_render_report.json", "ab_variants.json", "seo_payload_b10.json",
    "seo_payloads.json", "youtube_upload_payload.json", "hg3_dispatched.json",
    "director_gate_report.json", "whisper_segments.json"
]

def main():
    print(f"🚀 Starting non-destructive archive for targets: {targets} at timestamp {ts}")
    for ep in targets:
        src = Path(f"/var/vf/episodes/{ep}")
        if not src.exists():
            print(f"⚠️ Source episode dir not found on VPS: {src}")
            continue
            
        arch = Path(f"/var/vf/archive/{ep}_{ts}")
        arch.mkdir(parents=True, exist_ok=True)
        moved = []
        for k in step2_keys:
            p = src / k
            if p.exists():
                shutil.move(str(p), str(arch / k))
                moved.append(k)
                
        print(f"✅ Safely archived {len(moved)} Step 2+ items from {ep} -> {arch}")
        remaining = [f.name for f in src.iterdir()]
        print(f"   Preserved files in {ep}: {sorted(remaining)}")

if __name__ == "__main__":
    main()
