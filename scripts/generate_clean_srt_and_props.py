import os, sys, json, asyncio
from pathlib import Path
import edge_tts

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")

with open(ep_dir / "story.txt") as f:
    story_text = f.read()

clean_lines = []
for line in story_text.splitlines():
    l = line.strip()
    if l.startswith("#") or l.startswith("**Episode") or l.startswith("TITLE:") or not l:
        continue
    clean_lines.append(l)
speech_text = " ".join(clean_lines)

print("Generating timestamped subtitles via Edge-TTS SubMaker...")
submaker = edge_tts.SubMaker()

async def gen_subs():
    communicate = edge_tts.Communicate(speech_text, "en-US-GuyNeural", rate="-8%", pitch="-2Hz")
    async for chunk in communicate.stream():
        if chunk["type"] == "WordBoundary":
            submaker.feed(chunk)

asyncio.run(gen_subs())

srt_text = submaker.get_srt()
with open(ep_dir / "subtitles.srt", "w", encoding="utf-8") as f:
    f.write(srt_text)

print(f"Saved {ep_dir / 'subtitles.srt'} ({len(srt_text)} chars) ✅")

# Prepare Remotion props
with open(ep_dir / "brain_input.json") as f:
    brain = json.load(f)

scenes = brain.get("scenes", [])
total_scenes = len(scenes)
audio_duration = 847.39
scene_duration = audio_duration / max(1, total_scenes)

remotion_scenes = []
for i, sc in enumerate(scenes):
    remotion_scenes.append({
        "index": i,
        "beat": sc.get("beat", f"Scene {i+1}"),
        "durationInSeconds": scene_duration,
        "backgroundImage": f"/pulled/{ep_id}/{sc.get('background_reuse_key', 'byz-a1-walls-dawn')}.png",
        "foregroundImage": f"/pulled/{ep_id}/{sc.get('foreground_reuse_key', 'byzantine-varangian-guard')}.png",
        "foregroundPosition": sc.get("foreground_position", "left"),
        "safeZone": sc.get("safe_zone", "top")
    })

remotion_props = {
    "episode_id": ep_id,
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "durationInFrames": int(audio_duration * 30),
    "audioSrc": f"/pulled/{ep_id}/audio/voice_norm.wav",
    "scenes": remotion_scenes
}

with open(ep_dir / "remotion_props.json", "w", encoding="utf-8") as f:
    json.dump(remotion_props, f, indent=2)
print(f"Saved {ep_dir / 'remotion_props.json'} ({len(remotion_scenes)} scenes, {audio_duration:.2f}s) ✅")
