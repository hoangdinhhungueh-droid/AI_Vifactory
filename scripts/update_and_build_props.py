#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/update_and_build_props.py
Synchronizes brain_input.json and manifest.json from the rebuilt director_plan.json,
runs build_remotion_props.py and adversarial_director_gate.py.
"""
import json
import os
import sys
import subprocess
from pathlib import Path

EPISODE_ID = "EN_EP0004_amazon_ad_lawsuit"
EP_DIR = Path(f"/var/vf/episodes/{EPISODE_ID}")

def main():
    print(f"🚀 Updating brain_input.json and manifest.json for {EPISODE_ID}...")
    
    dp_path = EP_DIR / "director_plan.json"
    brain_path = EP_DIR / "brain_input.json"
    
    with open(dp_path, "r", encoding="utf-8") as f:
        dp = json.load(f)
        
    with open(brain_path, "r", encoding="utf-8") as f:
        brain = json.load(f)
        
    dp_scenes = {s["scene_id"]: s for s in dp.get("scenes", [])}
    
    # Update brain_input scenes
    updated_scenes = []
    for sc in brain.get("scenes", []):
        sc_id = sc.get("scene_id")
        if sc_id in dp_scenes:
            dps = dp_scenes[sc_id]
            bg_info = dps.get("background", {})
            fg_info = dps.get("foreground", {})
            
            sc["bg_reuse_key"] = bg_info.get("reuse_key")
            sc["background_reuse_key"] = bg_info.get("reuse_key")
            sc["background_title"] = bg_info.get("title")
            
            if fg_info and fg_info.get("reuse_key"):
                sc["fg_reuse_key"] = fg_info.get("reuse_key")
                sc["foreground_reuse_key"] = fg_info.get("reuse_key")
                sc["foreground_role"] = fg_info.get("role")
                sc["foreground_position"] = fg_info.get("position", "right")
            else:
                sc["fg_reuse_key"] = None
                sc["foreground_reuse_key"] = None
                
            sc["layout_zone"] = dps.get("layout_zone")
            sc["camera"] = dps.get("camera", sc.get("camera"))
            sc["animation_cue"] = dps.get("animation_cue")
            sc["motion_directive"] = dps.get("motion_directive", sc.get("motion_directive"))
            
        updated_scenes.append(sc)
        
    brain["scenes"] = updated_scenes
    
    with open(brain_path, "w", encoding="utf-8") as f:
        json.dump(brain, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated brain_input.json ({len(updated_scenes)} scenes)")
    
    # Build manifest.json with the 22 new assets
    pf_path = EP_DIR / "prompts_forge.json"
    with open(pf_path, "r", encoding="utf-8") as f:
        pf = json.load(f)
        
    manifest_items = []
    images_dir = EP_DIR / "images"
    
    for k in pf.get("backgrounds", {}).keys():
        local_png = images_dir / f"{k}.png"
        manifest_items.append({
            "name": k,
            "reuse_key": k,
            "layer_type": "Background",
            "local_path": str(local_png),
            "status": "Approved"
        })
        
    for k in pf.get("foregrounds", {}).keys():
        local_png = images_dir / f"{k}.png"
        manifest_items.append({
            "name": k,
            "reuse_key": k,
            "layer_type": "Foreground",
            "local_path": str(local_png),
            "status": "Approved"
        })
        
    manifest_path = images_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_items, f, indent=2, ensure_ascii=False)
        
    assets_manifest_path = EP_DIR / "assets" / "manifest.json"
    with open(assets_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_items, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Saved manifest.json ({len(manifest_items)} items) -> {manifest_path}")
    
    # Run build_remotion_props.py
    segments_path = EP_DIR / "whisper_segments.json"
    if not segments_path.exists():
        segments_path = EP_DIR / "spoken_sentences.json"
        
    props_path = EP_DIR / "remotion_props.json"
    
    cmd_build = [
        sys.executable, "/root/video_factory/scripts/build_remotion_props.py",
        "--episode-id", EPISODE_ID,
        "--brain-input", str(brain_path),
        "--segments", str(segments_path),
        "--manifest", str(manifest_path),
        "--out", str(props_path)
    ]
    print("🎬 Running build_remotion_props.py...")
    res_build = subprocess.run(cmd_build, capture_output=True, text=True)
    print(res_build.stdout)
    if res_build.returncode != 0:
        print(f"❌ Error in build_remotion_props: {res_build.stderr}")
        sys.exit(1)
    print("✅ build_remotion_props completed successfully!")
    
    # Run adversarial_director_gate.py
    cmd_gate = [
        sys.executable, "/root/video_factory/scripts/orchestrator/adversarial_director_gate.py",
        "--episode-id", EPISODE_ID,
        "--props", str(props_path)
    ]
    print("\n🔍 Running adversarial_director_gate.py...")
    res_gate = subprocess.run(cmd_gate, capture_output=True, text=True)
    print(res_gate.stdout)
    if res_gate.returncode != 0:
        print(f"❌ Error in adversarial_director_gate: {res_gate.stderr}")
        sys.exit(1)
        
    print("\n🎉 ALL BUILD & DIRECTOR GATES PASSED!")

if __name__ == "__main__":
    main()
