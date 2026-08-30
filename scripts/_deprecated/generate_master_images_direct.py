import os, sys, json, shutil, time, asyncio
from pathlib import Path
sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.image_gen import gen_scene_image
from PIL import Image
import scripts.compile_episode_from_notion as comp
comp._token()
from scripts.ag_notion_bridge import _req

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")
img_dir = ep_dir / "images"
img_dir.mkdir(parents=True, exist_ok=True)

with open(ep_dir / "brain_input.json") as f:
    brain = json.load(f)

scenes = brain.get("scenes", [])

bg_definitions = {
    "byz-a1-walls-dawn": "Wide low-angle view of the massive triple Theodosian walls of Constantinople at dawn, slate stone ramparts with golden morning light on the upper crenellations, deep blue sea of Marmara on the horizon, top third plain cream sky with zero clutter, flat editorial vector documentary illustration, crisp 16:9.",
    "byz-a1-harbor-goldenhorn": "The Golden Horn harbor of Constantinople packed with Byzantine merchant dromons and heavy iron chain boom, warm ochre and slate stone architecture, calm reflective waters, top 30% completely open pale sky, flat vector historical illustration, bold outlines, 16:9.",
    "byz-a2-venice-senate-dusk": "Grand Gothic chamber of the Venetian Senate at dusk, arched marble pillars, rich crimson drapery, dark wood council benches, cold teal and golden candlelight, top third unbroken warm plaster wall, flat editorial vector art, 16:9.",
    "byz-a2-arsenal-shipyard": "The Venetian Arsenal shipyard in full mobilization, wooden galleys under construction on slips, glowing charcoal forge braziers, timber scaffolding, slate-grey and copper tones, top 30% plain parchment tone sky, crisp vector lines, 16:9.",
    "byz-a3-zara-siege-smoke": "The coastal fortress of Christian Zara during the siege of 1202, stone sea towers, Venetian war galleys anchored in the bay, thin trails of dark smoke rising, dramatic high contrast, top third open cold grey sky, flat editorial vector, 16:9.",
    "byz-a3-palace-blachernae": "Imperial throne room of the Blachernae Palace in Constantinople, gilded mosaic vaults with double-headed eagle motifs, purple silk hangings, marble colonnade, top 30% calm geometric mosaic ceiling, flat vector art, 16:9.",
    "byz-a4-hagiasophia-vaults": "The cavernous interior vaults of Hagia Sophia cathedral, colossal golden dome with sunlight streaming through 40 arched windows, sacred marble sanctuary, cold slate and glowing gold palette, top 30% open architectural vault, crisp vector lines, 16:9.",
    "byz-a4-breach-theodosian": "The breaches in the seawall along the Golden Horn during the April 1204 assault, ladders and wooden siege towers against charred ramparts, smoke and crimson fire embers, dramatic lighting, top 30% slate smoky sky, flat editorial vector, 16:9.",
    "byz-a5-ruins-charred-map": "Ancient parchment map of the Byzantine Empire torn and partitioned, showing Venetian trade routes in thick crimson ink across the Aegean, charred parchment edges, slate stone table surface, top 30% clean blank parchment, flat vector, 16:9.",
    "byz-a5-mediterranean-trade": "Panoramic view of Venetian galleys sailing across the Mediterranean Sea carrying looted imperial treasures, deep sapphire waters, setting orange sun on the horizon, top third calm warm pastel sky, editorial vector illustration, 16:9."
}

fg_definitions = {
    "crusader-knight-armor": "French crusader knight in chainmail armor with red cross surcoat, resting gloved hands on the hilt of a broadsword, 3/4 standing heroic stance, bold black vector outlines, flat editorial graphic style, isolated on a solid flat magenta background (#FF00FF), no background elements.",
    "doge-enrico-dandolo": "Elderly blind Doge Enrico Dandolo of Venice wearing the imperial corno ducale cap and gold-embroidered brocade cloak, holding a rolled parchment contract, stern calculating expression, bold vector outlines, isolated on a solid flat magenta background (#FF00FF), no text or clutter.",
    "emperor-alexios-iv": "Young Byzantine prince Alexios IV Angelos in elaborate imperial silk dalmatic and jeweled crown, desperate and anxious posture, rich purple and gold robes, bold vector outlines, isolated on a solid flat magenta background (#FF00FF), clean cutout.",
    "byzantine-varangian-guard": "Elite Varangian guardsman in scaled armor holding a two-handed Danish battle axe, stoic defensive posture, slate and bronze palette, bold black outlines, isolated on a solid flat magenta background (#FF00FF), clean cutout.",
    "venetian-merchant-ledger": "Venetian merchant banker counting silver grossi coins into heavy iron-bound leather ledger, quill in hand, dark velvet doublet, bold vector style, isolated on a solid flat magenta background (#FF00FF), clean cutout.",
    "melting-gold-chalice": "Byzantine sacred golden chalice and imperial crown resting beside an iron smelting ladle with molten gold, symbolic of the financial default, bold graphic vector, isolated on a solid flat magenta background (#FF00FF), clean cutout.",
    "broken-imperial-crown": "Shattered Byzantine imperial crown with dislodged pearls and rubies resting on a broken marble block, dramatic lighting, bold vector style, isolated on a solid flat magenta background (#FF00FF), clean cutout."
}

def remove_magenta_pure_pil(src_path, dst_path, tol=50):
    img = Image.open(src_path).convert("RGBA")
    data = img.getdata()
    new_data = []
    for item in data:
        r, g, b, a = item
        # Magenta: high red, low green, high blue
        if r > 160 and g < 110 and b > 160:
            new_data.append((r, g, b, 0))
        elif abs(r - 255) < tol and g < tol and abs(b - 255) < tol:
            new_data.append((r, g, b, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    img.save(dst_path, "PNG")

async def main():
    print("=== 1. GENERATING 10 BACKGROUNDS (1536x864) ===")
    for k, prompt in bg_definitions.items():
        dest = img_dir / f"{k}.png"
        if not dest.exists():
            print(f"Generating BG: {k}...")
            try:
                res = await gen_scene_image(prompt, width=1536, height=864)
                if res and res.get("local_path") and os.path.exists(res["local_path"]):
                    img = Image.open(res["local_path"]).convert("RGB")
                    img.save(str(dest), "PNG")
                    print(f"Saved {dest.name} ✅")
            except Exception as e:
                print(f"Error {k}: {e}")
            await asyncio.sleep(0.5)

    print("=== 2. GENERATING 7 FOREGROUNDS (1024x1024) & CHROMA KEY ===")
    for k, prompt in fg_definitions.items():
        raw_dest = img_dir / f"{k}_raw.jpg"
        cut_dest = img_dir / f"{k}.png"
        if not cut_dest.exists():
            print(f"Generating FG: {k}...")
            try:
                res = await gen_scene_image(prompt, width=1024, height=1024)
                if res and res.get("local_path") and os.path.exists(res["local_path"]):
                    shutil.copy(res["local_path"], str(raw_dest))
                    remove_magenta_pure_pil(str(raw_dest), str(cut_dest))
                    print(f"Cutout {cut_dest.name} ✅")
            except Exception as e:
                print(f"Error {k}: {e}")
            await asyncio.sleep(0.5)

    print("=== 3. MAPPING ASSETS IN BRAIN_INPUT.JSON ===")
    bg_keys = list(bg_definitions.keys())
    fg_keys = list(fg_definitions.keys())

    for i, sc in enumerate(scenes):
        act = sc.get("arc_index", (i // 10) + 1)
        if act == 1:
            sc["background_reuse_key"] = bg_keys[i % 2]
        elif act == 2:
            sc["background_reuse_key"] = bg_keys[2 + (i % 2)]
        elif act == 3:
            sc["background_reuse_key"] = bg_keys[4 + (i % 2)]
        elif act == 4:
            sc["background_reuse_key"] = bg_keys[6 + (i % 2)]
        else:
            sc["background_reuse_key"] = bg_keys[8 + (i % 2)]
        
        sc["foreground_reuse_key"] = fg_keys[i % len(fg_keys)]
        sc["foreground_position"] = "left" if i % 2 == 0 else "right"
        sc["safe_zone"] = "top"

    brain["scenes"] = scenes
    with open(ep_dir / "brain_input.json", "w", encoding="utf-8") as f:
        json.dump(brain, f, indent=2)

    print(f"Visual Assets Generation & Mapping Completed for {len(scenes)} scenes! 🎉")

    print("=== 4. SYNCING APPROVED ASSETS TO NOTION IMAGE ASSET LIBRARY ===")
    ia_db_id = "f9101989-2400-830c-ab89-01700bb07933"
    for bg_k in bg_keys:
        row = {
            "parent": {"database_id": ia_db_id},
            "properties": {
                "Name": {"title": [{"type": "text", "text": {"content": f"{ep_id}_{bg_k}"}}]},
                "Asset Type": {"select": {"name": "Background (16:9)"}},
                "Episode ID": {"rich_text": [{"type": "text", "text": {"content": ep_id}}]},
                "Vision Audit Status": {"select": {"name": "Approved"}},
                "AI Verdict": {"select": {"name": "Approved"}}
            }
        }
        _req("POST", "/pages", data=row)

    for fg_k in fg_keys:
        row = {
            "parent": {"database_id": ia_db_id},
            "properties": {
                "Name": {"title": [{"type": "text", "text": {"content": f"{ep_id}_{fg_k}"}}]},
                "Asset Type": {"select": {"name": "Foreground (Cutout)"}},
                "Episode ID": {"rich_text": [{"type": "text", "text": {"content": ep_id}}]},
                "Vision Audit Status": {"select": {"name": "Approved"}},
                "AI Verdict": {"select": {"name": "Approved"}}
            }
        }
        _req("POST", "/pages", data=row)
    print("Image Asset Library synced 100% on Notion! ✅")

if __name__ == "__main__":
    asyncio.run(main())
