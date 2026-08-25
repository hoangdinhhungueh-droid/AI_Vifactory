import os, sys, json
from pathlib import Path
sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.hhtech_reasoner import call_gpt56_sol

ep_id = "en-byzantine-empire-ep001"
ep_dir = Path(f"/var/vf/episodes/{ep_id}")
with open(ep_dir / "story.txt") as f:
    story_text = f.read()

prompt = f"""You are the master Art Director & Storyboard Architect for a high-end history/economics YouTube documentary (Enron/Archive X style).
Here is the complete 5-Act story:
{story_text}

TASK:
Break down the entire 1,800-word story into EXACTLY 50 chronological scenes (sc000 to sc049).
For each scene, output a JSON object with:
1. scene_index (0 to 49)
2. beat (short narrative title)
3. duration_sec (integer between 9 and 13, matching the narration pace)
4. safe_zone ("top")
5. narration (the exact portion of spoken voiceover text for this scene)
6. image_prompt (Layer 1 Background 16:9: Detailed historical documentary scene, flat editorial vector/high-key aesthetic, warm ochre, slate stone, imperial purple and gold accents, top 30% kept clear and uncluttered for data/motion graphics, 16:9 aspect ratio)
7. foreground_prompt (Layer 2 Foreground Cutout 1:1: Specific historical figure, crusader knight, doge, emperor, merchant, or symbolic icon, full-body or 3/4 pose, bold black vector outlines, isolated on a flat solid magenta background #FF00FF, no background clutter)
8. foreground_position ("left" or "right")
9. bg_layout_note (composition guideline)
10. sub_note ("16:9 subtitle bottom 15% safe zone overlay")
11. arc_index (1 to 5)

OUTPUT FORMAT:
Return ONLY a valid JSON array of 50 scene objects. No markdown ticks, no commentary."""

system_prompt = "You are an elite cinematic art director and visual storyboard architect for documentary animation."

print("Calling GPT-5.6-Sol for 50-Scene Director Plan...")
res = call_gpt56_sol(prompt, system_prompt=system_prompt)

# Clean json
res_clean = res.strip()
if res_clean.startswith("```json"):
    res_clean = res_clean[7:]
if res_clean.startswith("```"):
    res_clean = res_clean[3:]
if res_clean.endswith("```"):
    res_clean = res_clean[:-3]
res_clean = res_clean.strip()

scenes = json.loads(res_clean)
print(f"Successfully generated {len(scenes)} scenes! ✅")

brain_data = {
    "episode_id": ep_id,
    "lang_code": "en",
    "content_type": "documentary",
    "hook_3s": "For eight centuries, Constantinople survived every siege until an 85,000 silver mark debt destroyed it from within.",
    "story": story_text,
    "mood": "investigative_tense_historical",
    "art_style": "flat_editorial_vector_high_key",
    "scenes": scenes,
    "render_architecture": "remotion_twolayer_karaoke_v4"
}

with open(ep_dir / "brain_input.json", "w", encoding="utf-8") as f:
    json.dump(brain_data, f, indent=2)
print(f"Saved {ep_dir / 'brain_input.json'} ({len(scenes)} scenes) ✅")
