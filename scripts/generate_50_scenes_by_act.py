import os, sys, json
from pathlib import Path
sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.hhtech_reasoner import call_gpt56_sol

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")
with open(ep_dir / "story.txt") as f:
    story_text = f.read()

# Split story into 5 Acts
acts = []
current_act = []
for line in story_text.splitlines():
    if line.strip().startswith("## ACT") or line.strip().startswith("ACT "):
        if current_act:
            acts.append("\n".join(current_act))
            current_act = []
    current_act.append(line)
if current_act:
    acts.append("\n".join(current_act))

if len(acts) < 5:
    # Split roughly if headings not strictly matched
    lines = story_text.splitlines()
    chunk_size = max(1, len(lines) // 5)
    acts = ["\n".join(lines[i*chunk_size:(i+1)*chunk_size]) for i in range(5)]

print(f"Divided story into {len(acts)} acts.")

all_scenes = []
for act_idx in range(5):
    act_num = act_idx + 1
    start_sc = act_idx * 10
    end_sc = start_sc + 9
    act_content = acts[act_idx]
    
    prompt = f"""You are the master Art Director & Storyboard Architect for a high-end history/economics YouTube documentary (Enron/Archive X style).
Here is the text for ACT {act_num}:
{act_content}

TASK:
Break down ACT {act_num} into EXACTLY 10 chronological scenes (scene_index {start_sc} to {end_sc}).
For each scene, output a JSON object with:
1. "scene_index": {start_sc} to {end_sc}
2. "beat": short narrative title (e.g. "Triple Theodosian Walls & Golden Horn")
3. "duration_sec": integer between 10 and 12
4. "safe_zone": "top"
5. "narration": the spoken voiceover sentence for this scene from ACT {act_num}
6. "image_prompt": Layer 1 Background 16:9 prompt (flat editorial vector/high-key aesthetic, warm ochre, slate stone, imperial purple and gold accents, top 30% kept clear and uncluttered for data/motion graphics, 16:9 aspect ratio)
7. "foreground_prompt": Layer 2 Foreground Cutout 1:1 prompt (specific historical figure, crusader knight, doge, emperor, merchant, or symbolic icon, full-body or 3/4 pose, bold black vector outlines, isolated on a flat solid magenta background #FF00FF, no background clutter)
8. "foreground_position": "left" or "right"
9. "bg_layout_note": "Slate stone walls on right, open counterweight on left"
10. "sub_note": "16:9 subtitle bottom 15% safe zone overlay"
11. "arc_index": {act_num}

OUTPUT FORMAT:
Return ONLY a valid JSON array of 10 scene objects. No markdown ticks, no commentary."""

    print(f"Generating Act {act_num} (Scenes {start_sc}-{end_sc})...")
    res = call_gpt56_sol(prompt, system_prompt="You are an elite cinematic art director and visual storyboard architect.")
    
    res_clean = res.strip()
    if res_clean.startswith("```json"):
        res_clean = res_clean[7:]
    if res_clean.startswith("```"):
        res_clean = res_clean[3:]
    if res_clean.endswith("```"):
        res_clean = res_clean[:-3]
    res_clean = res_clean.strip()
    
    try:
        act_scenes = json.loads(res_clean)
        print(f"Act {act_num} generated {len(act_scenes)} scenes ✅")
        all_scenes.extend(act_scenes)
    except Exception as e:
        print(f"Error parsing Act {act_num}: {e}")

print(f"Total scenes generated across 5 acts: {len(all_scenes)}")

# Re-index scenes cleanly 0 to len-1
for i, sc in enumerate(all_scenes):
    sc["scene_index"] = i

brain_data = {
    "episode_id": ep_id,
    "lang_code": "en",
    "content_type": "documentary",
    "hook_3s": "For eight centuries, Constantinople survived every siege until an 85,000 silver mark debt destroyed it from within.",
    "story": story_text,
    "mood": "investigative_tense_historical",
    "art_style": "flat_editorial_vector_high_key",
    "scenes": all_scenes,
    "render_architecture": "remotion_twolayer_karaoke_v4"
}

with open(ep_dir / "brain_input.json", "w", encoding="utf-8") as f:
    json.dump(brain_data, f, indent=2)
print(f"Saved {ep_dir / 'brain_input.json'} ({len(all_scenes)} scenes) ✅")
