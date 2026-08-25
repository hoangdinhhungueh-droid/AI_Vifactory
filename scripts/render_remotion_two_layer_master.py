import os, sys, json, shutil, subprocess, time, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--episode", default="en-byzantine-empire-ep001", help="Episode ID")
args = parser.parse_args()
EP_ID = args.episode
EP_DIR = Path(f"/var/vf/episodes/{EP_ID}")
REMOTION_DIR = Path("/root/video_factory/remotion")
PUBLIC_DIR = REMOTION_DIR / "public" / "pulled" / EP_ID
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
(PUBLIC_DIR / "audio").mkdir(parents=True, exist_ok=True)

print("=== 1. SYNCING CLEAN TRANSPARENT ASSETS TO REMOTION PUBLIC ===")
img_dir = EP_DIR / "images"
for img_path in img_dir.glob("*.png"):
    dst = PUBLIC_DIR / img_path.name
    shutil.copyfile(img_path, dst)
    print(f"Copied {img_path.name} ✅")

# Copy audio
shutil.copyfile(EP_DIR / "audio" / "voice_norm.wav", PUBLIC_DIR / "audio" / "voice_norm.wav")
print("Copied voice_norm.wav ✅")

# Copy BGM to public/assets/bgm
(REMOTION_DIR / "public" / "assets" / "bgm").mkdir(parents=True, exist_ok=True)
shutil.copyfile("/root/video_factory/assets/bgm/calm_004_fs725597.mp3", REMOTION_DIR / "public" / "assets" / "bgm" / "calm_004_fs725597.mp3")

# 2. Build Rich TwoLayerEpisode remotion_props.json
print("=== 2. BUILDING RICH TWO-LAYER REMOTION PROPS ===")
with open(EP_DIR / "brain_input.json") as f:
    brain = json.load(f)

scenes = brain.get("scenes", [])
total_scenes = len(scenes)
audio_duration = 847.39
total_frames = int(audio_duration * 30)
frames_per_scene = total_frames // total_scenes

act_titles = {
    1: "ACT I // THE IMPENETRABLE CAPITAL & THE DEBT TRAP",
    2: "ACT II // THE VENETIAN NAVAL MONOPOLY",
    3: "ACT III // THE ZARA DIVERSION & THE DEFAULT",
    4: "ACT IV // THE SIEGE & SACK OF CONSTANTINOPLE (1204)",
    5: "ACT V // THE CARVING OF THE BYZANTINE EMPIRE"
}

stat_highlights = {
    0: ("800 YRS", "OF UNBROKEN IMPERIAL DEFENSE"),
    5: ("85,000", "SILVER MARKS CRUSADER DEBT"),
    12: ("500 SHIPS", "VENETIAN ARSENAL MOBILIZATION"),
    20: ("1202 A.D.", "THE SACK OF CHRISTIAN ZARA"),
    28: ("200,000", "SILVER MARKS PROMISED BY ALEXIOS IV"),
    35: ("APRIL 1204", "THE SEAWALL BREACH & COLLAPSE"),
    42: ("3/8THS", "OF THE EMPIRE SEIZED BY VENICE"),
    48: ("1204-1261", "THE LATIN EMPIRE DEBT COLONY")
}

remotion_scenes = []
for i, sc in enumerate(scenes):
    act_idx = sc.get("arc_index", (i // 10) + 1)
    act_title = act_titles.get(act_idx, f"ACT {act_idx}")
    
    bg_key = sc.get("background_reuse_key", "byz-a1-walls-dawn")
    fg_key = sc.get("foreground_reuse_key", "byzantine-varangian-guard")
    
    stat_val, stat_lbl = stat_highlights.get(i, (None, None))
    
    remotion_scenes.append({
        "durationInFrames": frames_per_scene,
        "background": f"pulled/{EP_ID}/{bg_key}.png",
        "foreground": f"pulled/{EP_ID}/{fg_key}.png",
        "foregroundPosition": sc.get("foreground_position", "left"),
        "foregroundFadeFrames": 15,
        "caption": sc.get("narration_chunk", sc.get("beat", "")),
        "statValue": stat_val,
        "statLabel": stat_lbl,
        "actTitle": act_title,
        "safeZone": "top"
    })

remotion_props = {
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "audioMaster": f"pulled/{EP_ID}/audio/voice_norm.wav",
    "bgmFile": "assets/bgm/calm_004_fs725597.mp3",
    "bgmVolume": 0.06,
    "scenes": remotion_scenes
}

props_path = EP_DIR / "remotion_props.json"
with open(props_path, "w", encoding="utf-8") as f:
    json.dump(remotion_props, f, indent=2)

print(f"Saved {props_path} with {len(remotion_scenes)} rich scenes ✅")

# 3. Render TwoLayerEpisode via Remotion CLI
print("=== 3. RENDERING MASTER VIDEO PRO VIA REMOTION ===")
out_mp4 = EP_DIR / "master_video_pro.mp4"
render_cmd = [
    "npx", "remotion", "render",
    "src/index.tsx", "TwoLayerEpisode",
    str(out_mp4),
    f"--props={props_path}",
    "--concurrency=3",
    "--log=error",
    "--gl=angle"
]

print("Executing Remotion Render Command...")
subprocess.run(render_cmd, cwd=str(REMOTION_DIR), check=True)
print(f"🎉 REMOTION MASTER VIDEO RENDERED: {out_mp4} ({out_mp4.stat().st_size / (1024*1024):.2f} MB)!")
