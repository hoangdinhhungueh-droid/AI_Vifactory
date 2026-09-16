#!/usr/bin/env python3
"""
CLI Runner for B3.5 Prompt Engineering Forge (/prompt:forge)
Generates detailed prompts via HHTech GPT-6-Astra and pushes directly to Notion Prompt Library DB.
Rule 116 & 435: Layer 1 Background (16:9) + Layer 2 Foreground (1:1 stylized graphic novel on #FF00FF).
Rule 120: Prompts are synced to Notion SoT DB, avoiding raw prompt chat dumps.
Rule 128: Zero Semantic Bias. Dynamically matches scene era, architecture, and lighting without topic relics.
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, "/root/video_factory")
sys.path.insert(0, ".")

from app.services.prompt_forge import generate_scene_prompts, push_prompts_to_notion


def main():
    parser = argparse.ArgumentParser(description="Run B3.5 Prompt Forge")
    parser.add_argument("--episode", required=True, help="Episode ID (e.g. JP_EP0003_hamaoka_data_fraud)")
    args = parser.parse_args()

    ep_id = args.episode
    ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    ws_dir = Path(f"/root/video_factory/workspace/{ep_id}")
    local_ep_dir = Path(f"/root/video_factory/episodes/{ep_id}")

    # 1. Resolve director plan
    dplan_candidates = [
        ep_dir / "director_plan.json",
        local_ep_dir / "director_plan.json",
        ws_dir / "director_plan.json",
    ]
    director_plan = None
    for cand in dplan_candidates:
        if cand.exists():
            try:
                with open(cand, encoding="utf-8") as f:
                    director_plan = json.load(f)
                break
            except Exception:
                pass

    if not director_plan:
        raise FileNotFoundError(f"Director plan not found in candidates: {dplan_candidates}")

    # 2. Resolve brain input
    brain_candidates = [
        ep_dir / "brain_input.json",
        local_ep_dir / "brain_input.json",
        ws_dir / "brain_input.json",
    ]
    brain_data = {}
    for cand in brain_candidates:
        if cand.exists():
            try:
                with open(cand, encoding="utf-8") as f:
                    brain_data = json.load(f)
                break
            except Exception:
                pass

    scenes = director_plan.get("scenes", [])
    if not scenes and "scenes" in brain_data:
        scenes = brain_data.get("scenes", [])

    topic = brain_data.get("topic") or brain_data.get("title") or ep_id
    market = brain_data.get("market") or (ep_id.split("_")[0].upper() if "_" in ep_id else "EN")

    bg_dict = {}
    fg_dict = {}
    for s in scenes:
        bg_key = s.get("background_reuse_key") or s.get("bg_reuse_key")
        fg_key = s.get("foreground_reuse_key") or s.get("fg_reuse_key")
        narr = s.get("narration") or s.get("caption", "")
        beat_name = s.get("beat") or s.get("beat_name") or "Narrative Arc"
        if bg_key and bg_key not in bg_dict:
            bg_dict[bg_key] = {
                "beat": beat_name,
                "narration_context": narr,
                "description": s.get("bg_prompt") or f"Cinematic documentary environment for {beat_name}",
            }
        if fg_key and fg_key not in fg_dict:
            fg_dict[fg_key] = {
                "beat": beat_name,
                "narration_context": narr,
                "description": s.get("fg_prompt") or f"Stylized editorial graphic novel character for {beat_name}",
            }

    print(f"=== B3.5 PROMPT FORGE: Generating prompts for {len(bg_dict)} BGs and {len(fg_dict)} FGs (Market: {market}, Topic: {topic}) ===")
    prompts_data = generate_scene_prompts(
        bg_dict=bg_dict,
        fg_dict=fg_dict,
        story_title=topic,
        scenes=scenes,
        task_id=ep_id,
        market=market,
    )

    # 3. Map forged prompts back to each scene in director_plan
    for sc in director_plan.get("scenes", []):
        bg_k = sc.get("background_reuse_key") or sc.get("bg_reuse_key")
        if bg_k and bg_k in prompts_data.get("backgrounds", {}):
            prompt_val = prompts_data["backgrounds"][bg_k]
            sc["bg_prompt"] = prompt_val
            sc["image_prompt"] = prompt_val
        fg_k = sc.get("foreground_reuse_key") or sc.get("fg_reuse_key")
        if fg_k and fg_k in prompts_data.get("foregrounds", {}):
            fg_val = prompts_data["foregrounds"][fg_k]
            sc["fg_prompt"] = fg_val
            sc["foreground_prompt"] = fg_val

    # 4. Save to all canonical directories
    canonical_dirs = [ep_dir, ws_dir, local_ep_dir]
    for target_dir in canonical_dirs:
        if target_dir.parent.exists() or Path("/var/vf").exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
                json.dump(prompts_data, f, indent=2, ensure_ascii=False)
            with open(target_dir / "prompts.json", "w", encoding="utf-8") as f:
                json.dump(prompts_data, f, indent=2, ensure_ascii=False)
            with open(target_dir / "director_plan.json", "w", encoding="utf-8") as f:
                json.dump(director_plan, f, indent=2, ensure_ascii=False)
            with open(target_dir / "dp_plan.json", "w", encoding="utf-8") as f:
                json.dump({"scenes": director_plan.get("scenes", [])}, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(prompts_data.get('backgrounds', {}))} BG prompts and {len(prompts_data.get('foregrounds', {}))} FG prompts to canonical dirs ✅")

    # 5. Push to Notion
    print(f"=== Pushing prompts to Notion Prompt Library DB for {ep_id} ===")
    try:
        push_prompts_to_notion(prompts_data, ep_id)
        print("Notion Prompt Library synchronization complete! ✅")
    except Exception as e:
        print(f"Warning: Notion Prompt Library push encountered notice: {e}")


if __name__ == "__main__":
    main()
