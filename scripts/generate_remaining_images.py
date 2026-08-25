import os, sys, json, shutil, time, asyncio
from pathlib import Path
sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.image_gen import gen_scene_image
from PIL import Image

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")
img_dir = ep_dir / "images"
img_dir.mkdir(parents=True, exist_ok=True)

bg_definitions = {
    "byz-a3-zara-siege-smoke": "The coastal fortress of Christian Zara during the siege of 1202, stone sea towers, Venetian war galleys anchored in the bay, thin trails of dark smoke rising, dramatic high contrast, top third open cold grey sky, flat editorial vector, 16:9.",
    "byz-a3-palace-blachernae": "Imperial throne room of the Blachernae Palace in Constantinople, gilded mosaic vaults with double-headed eagle motifs, purple silk hangings, marble colonnade, top 30% calm geometric mosaic ceiling, flat vector art, 16:9.",
    "byz-a4-hagiasophia-vaults": "The cavernous interior vaults of Hagia Sophia cathedral, colossal golden dome with sunlight streaming through 40 arched windows, sacred marble sanctuary, cold slate and glowing gold palette, top 30% open architectural vault, crisp vector lines, 16:9.",
    "byz-a4-breach-theodosian": "The breaches in the seawall along the Golden Horn during the April 1204 assault, ladders and wooden siege towers against charred ramparts, smoke and crimson fire embers, dramatic lighting, top 30% slate smoky sky, flat editorial vector, 16:9.",
    "byz-a5-ruins-charred-map": "Ancient parchment map of the Byzantine Empire torn and partitioned, showing Venetian trade routes in thick crimson ink across the Aegean, charred parchment edges, slate stone table surface, top 30% clean blank parchment, flat vector, 16:9."
}

fg_definitions = {
    "crusader-knight-armor": "French crusader knight in chainmail armor with red cross surcoat, resting gloved hands on the hilt of a broadsword, 3/4 standing heroic stance, bold black vector outlines, flat editorial graphic style, isolated on a solid flat magenta background (#FF00FF), no background elements.",
    "doge-enrico-dandolo": "Elderly blind Doge Enrico Dandolo of Venice wearing the imperial corno ducale cap and gold-embroidered brocade cloak, holding a rolled parchment contract, stern calculating expression, bold vector outlines, isolated on a solid flat magenta background (#FF00FF), no text or clutter.",
    "emperor-alexios-iv": "Young Byzantine prince Alexios IV Angelos in elaborate imperial silk dalmatic and jeweled crown, desperate and anxious posture, rich purple and gold robes, bold vector outlines, isolated on a solid flat magenta background (#FF00FF), clean cutout.",
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
        if r > 160 and g < 110 and b > 160:
            new_data.append((r, g, b, 0))
        elif abs(r - 255) < tol and g < tol and abs(b - 255) < tol:
            new_data.append((r, g, b, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    img.save(dst_path, "PNG")

async def main():
    print("=== GENERATING REMAINING BACKGROUNDS ===")
    for k, prompt in bg_definitions.items():
        dest = img_dir / f"{k}.png"
        if not dest.exists():
            print(f"Generating BG: {k}...")
            for attempt in range(3):
                try:
                    res = await gen_scene_image(prompt, width=1536, height=864)
                    if res and res.get("local_path") and os.path.exists(res["local_path"]):
                        img = Image.open(res["local_path"]).convert("RGB")
                        img.save(str(dest), "PNG")
                        print(f"Saved {dest.name} ✅")
                        break
                except Exception as e:
                    print(f"Retry {k} ({attempt+1}/3): {e}")
                    await asyncio.sleep(4)
            await asyncio.sleep(3)

    print("=== GENERATING REMAINING FOREGROUNDS ===")
    for k, prompt in fg_definitions.items():
        raw_dest = img_dir / f"{k}_raw.jpg"
        cut_dest = img_dir / f"{k}.png"
        if not cut_dest.exists():
            print(f"Generating FG: {k}...")
            for attempt in range(3):
                try:
                    res = await gen_scene_image(prompt, width=1024, height=1024)
                    if res and res.get("local_path") and os.path.exists(res["local_path"]):
                        shutil.copy(res["local_path"], str(raw_dest))
                        remove_magenta_pure_pil(str(raw_dest), str(cut_dest))
                        print(f"Cutout {cut_dest.name} ✅")
                        break
                except Exception as e:
                    print(f"Retry {k} ({attempt+1}/3): {e}")
                    await asyncio.sleep(4)
            await asyncio.sleep(3)

    print("ALL REMAINING ASSETS GENERATED SUCCESSFULLY! 🎉")

if __name__ == "__main__":
    asyncio.run(main())
