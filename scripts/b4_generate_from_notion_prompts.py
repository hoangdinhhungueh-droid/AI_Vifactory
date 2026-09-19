#!/usr/bin/env python3
"""
Step B4: Generate visual assets directly from Notion Prompt Library DB
Single Source of Truth: this episode's own Prompt Library child DB (23/08/2026
subpage-per-episode restructuring; resolved dynamically via
ag_notion_bridge.resolve_episode_prompt_db, mirrors the Director Plan migration).
Rule 120: B4 reads 100% prompts from Notion Prompt Library DB, never from chat.
Applies 16:9 for Backgrounds, 1:1 for Foregrounds, and B5 Pure PIL #FF00FF Chroma Keying.
"""

import os, sys, json, re, shutil, asyncio, argparse
from pathlib import Path
from PIL import Image

sys.path.insert(0, "/root/video_factory")

import scripts.compile_episode_from_notion as comp
comp._token()

from scripts.ag_notion_bridge import _req, resolve_episode_prompt_db
from app.services.image_gen import gen_scene_image

PROMPT_DB_ID_FALLBACK = "8c801989-2400-831a-901d-014aebdc3b31"
IMAGE_ASSET_DB_ID = "f9101989-2400-830c-ab89-01700bb07933"

def fetch_prompts_from_notion(episode_id: str):
    resolved = resolve_episode_prompt_db(episode_id, create_if_missing=False)
    if resolved.get("error"):
        print(f"[WARN] No per-episode Prompt Library DB found for {episode_id} ({resolved}); falling back to flat DB.")
        prompt_db_id = PROMPT_DB_ID_FALLBACK
    else:
        prompt_db_id = resolved["db_id"]

    res = _req("POST", f"databases/{prompt_db_id}/query", data={
        "filter": {
            "property": "Title",
            "title": {
                "contains": f"[{episode_id}]"
            }
        }
    })
    if res.get("error"):
        raise RuntimeError(f"Error querying Notion Prompt Library DB: {res}")

    results = res.get("results", [])

    # Self-Healing: If Notion prompt DB is empty, auto-push from local prompts_forge.json
    if not results:
        print(f"[SELF-HEALING] Notion Prompt DB is empty for {episode_id}. Checking local prompts_forge.json...")
        for pf_candidate in [
            Path(f"/var/vf/episodes/{episode_id}/prompts_forge.json"),
            Path(f"/root/video_factory/episodes/{episode_id}/prompts_forge.json"),
            Path(f"/root/video_factory/workspace/{episode_id}/prompts_forge.json")
        ]:
            if pf_candidate.exists():
                try:
                    with open(pf_candidate, "r", encoding="utf-8") as f:
                        prompts_data = json.load(f)
                    from app.services.prompt_forge import push_prompts_to_notion
                    print(f"[SELF-HEALING] Found {pf_candidate}. Auto-pushing prompts to Notion...")
                    push_prompts_to_notion(prompts_data, episode_id)
                    # Re-query
                    re_res = _req("POST", f"databases/{prompt_db_id}/query", data={
                        "filter": {"property": "Title", "title": {"contains": f"[{episode_id}]"}}
                    })
                    results = re_res.get("results", [])
                    print(f"[SELF-HEALING] Successfully recovered {len(results)} prompts from Notion after auto-sync.")
                    break
                except Exception as _she:
                    print(f"[SELF-HEALING] Failed auto-sync: {_she}")
    bgs = {}
    fgs = {}
    for r in results:
        title_list = r.get("properties", {}).get("Title", {}).get("title", [])
        title = title_list[0].get("plain_text", "") if title_list else ""
        prompt_list = r.get("properties", {}).get("prompt_text", {}).get("rich_text", [])
        prompt = prompt_list[0].get("plain_text", "") if prompt_list else ""

        m = re.search(rf"\[{re.escape(episode_id)}\]\s+([^\s]+)\s+\((BG|FG)", title)
        if m:
            asset_key = m.group(1).strip()
            asset_type = m.group(2).strip()
            if asset_type == "BG":
                bgs[asset_key] = prompt
            else:
                fgs[asset_key] = prompt
    return bgs, fgs

def remove_magenta_chromakey(input_path: Path, output_path: Path):
    """
    Pure PIL Chroma Keyer for flat solid #FF00FF magenta background.
    """
    img = Image.open(input_path).convert("RGBA")
    data = img.getdata()

    new_data = []
    for item in data:
        r, g, b, a = item
        # Distance from pure magenta (255, 0, 255)
        dist = ((r - 255)**2 + (g - 0)**2 + (b - 255)**2)**0.5
        if dist < 110:
            new_data.append((r, g, b, 0))
        elif dist < 150:
            alpha = int(255 * ((dist - 110) / 40.0))
            new_data.append((r, g, b, alpha))
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Chroma-keyed {input_path.name} -> {output_path.name} (Pure PIL #FF00FF) \u2705")

async def main():
    parser = argparse.ArgumentParser(description="B4 Visual Asset Generation from Notion Prompts")
    parser.add_argument("--episode", required=True, help="Episode ID (e.g. EN_EP0001_sample_topic)")
    args = parser.parse_args()

    ep_id = args.episode
    ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    img_dir = ep_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    public_dir = Path(f"/root/video_factory/remotion/public/pulled/{ep_id}")
    public_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== B4: Fetching Prompts from this episode's Prompt Library DB for {ep_id} ===")
    bgs, fgs = fetch_prompts_from_notion(ep_id)
    print(f"Fetched {len(bgs)} unique Background prompts and {len(fgs)} unique Foreground prompts from Notion.")

    if not bgs and not fgs:
        print(f"[WARN] No prompts found in Notion Prompt Library for [{ep_id}]. Please run B3.5 Prompt Forge first!")
        sys.exit(1)

    manifest = []

    # 1. Generate Backgrounds (16:9)
    print("\n--- Generating 16:9 Background Images ---")
    for key, prompt in bgs.items():
        out_jpg = img_dir / f"{key}.jpg"
        print(f"Generating BG: {key} (16:9)...")
        res = await gen_scene_image(prompt, aspect="16:9")
        src_path = Path(res["local_path"])
        shutil.copyfile(src_path, out_jpg)

        # Stage to remotion public
        shutil.copyfile(out_jpg, public_dir / f"{key}.jpg")

        manifest.append({
            "reuse_key": key,
            "asset_type": "background",
            "local_path": str(out_jpg),
            "width": 1920,
            "height": 1080
        })
        print(f"Saved and staged BG: {key}.jpg \u2705")

    # 2. Generate Foregrounds (1:1 with #FF00FF Chroma Key)
    print("\n--- Generating 1:1 Foreground Images & Applying B5 Chroma Key ---")
    for key, prompt in fgs.items():
        raw_png = img_dir / f"{key}_raw.png"
        clean_png = img_dir / f"{key}.png"
        print(f"Generating FG: {key} (1:1 #FF00FF)...")
        res = await gen_scene_image(prompt, aspect="1:1")
        src_path = Path(res["local_path"])
        shutil.copyfile(src_path, raw_png)

        # B5 Chroma keying
        remove_magenta_chromakey(raw_png, clean_png)

        # Stage to remotion public
        shutil.copyfile(clean_png, public_dir / f"{key}.png")

        manifest.append({
            "reuse_key": key,
            "asset_type": "foreground",
            "local_path": str(clean_png),
            "width": 1080,
            "height": 1080
        })
        print(f"Saved and staged FG: {key}.png \u2705")

    manifest_file = ep_dir / "images_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote images manifest to {manifest_file} ({len(manifest)} assets) \u2705")

if __name__ == "__main__":
    asyncio.run(main())
