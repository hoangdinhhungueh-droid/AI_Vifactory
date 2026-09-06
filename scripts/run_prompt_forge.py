#!/usr/bin/env python3
"""
CLI Runner for B3.5 Prompt Engineering Forge (/prompt:forge)
Generates detailed prompts via HHTech GPT-6-Astra and pushes directly to Notion Prompt Library DB.
Rule 120: Prompts are synced to Notion SoT DB, avoiding raw prompt chat dumps.
"""

import os, sys, json, argparse
from pathlib import Path

sys.path.insert(0, "/root/video_factory")

from app.services.prompt_forge import generate_scene_prompts, push_prompts_to_notion

def main():
    parser = argparse.ArgumentParser(description="Run B3.5 Prompt Forge")
    parser.add_argument("--episode", default="en-byzantine-empire-ep001", help="Episode ID (default: en-byzantine-empire-ep001)")
    args = parser.parse_args()

    ep_id = args.episode
    ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    
    brain_path = ep_dir / "brain_input.json"
    if not brain_path.exists():
        raise FileNotFoundError(f"Brain input not found at {brain_path}")
        
    with open(brain_path, encoding="utf-8") as f:
        brain_data = json.load(f)
        
    scenes = brain_data.get("scenes", [])
    title = brain_data.get("title") or "The Economic Conspiracy That Destroyed the Byzantine Empire"
    
    bg_dict = {}
    fg_dict = {}
    for s in scenes:
        bg_key = s.get("background_reuse_key")
        fg_key = s.get("foreground_reuse_key")
        if bg_key and bg_key not in bg_dict:
            bg_dict[bg_key] = {
                "beat": s.get("beat"),
                "narration_context": s.get("narration") or s.get("caption", "")
            }
        if fg_key and fg_key not in fg_dict:
            fg_dict[fg_key] = {
                "beat": s.get("beat"),
                "narration_context": s.get("narration") or s.get("caption", "")
            }
            
    print(f"=== B3.5 PROMPT FORGE: Generating prompts for {len(bg_dict)} BGs and {len(fg_dict)} FGs via HHTech GPT-6-Astra ===")
    prompts_data = generate_scene_prompts(bg_dict, fg_dict, title)
    
    out_file = ep_dir / "prompts_forge.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(prompts_data.get('backgrounds', {}))} BG prompts and {len(prompts_data.get('foregrounds', {}))} FG prompts to {out_file} ✅")
    
    print(f"=== Pushing prompts to Notion Prompt Library DB for {ep_id} (per-episode subpage+DB, resolved dynamically) ===")
    push_prompts_to_notion(prompts_data, ep_id)
    print("Notion Prompt Library synchronization complete! ✅")

if __name__ == "__main__":
    main()
