import json
import sys
from pathlib import Path

# When running on VPS or local:
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.desk_world_director import build_continuous_desk_world

def generate_props():
    audio_path = ROOT / "remotion" / "public" / "episodes" / "EN_EP0268_general_pants_collapse" / "audio" / "timestamps_act1.json"
    if not audio_path.exists():
        # Fallback if in different location
        audio_path = Path("/root/video_factory/remotion/public/episodes/EN_EP0268_general_pants_collapse/audio/timestamps_act1.json")
    
    with open(audio_path, "r", encoding="utf-8") as f:
        ts_data = json.load(f)

    # 1. Build continuous desk world model
    desk_model = build_continuous_desk_world(
        act_id="ACT_01",
        timestamps=ts_data,
        assets_base_dir="episodes/EN_EP0268_general_pants_collapse/images"
    )
    props_dict = desk_model.model_dump()

    # 2. Add act title and global metadata
    props_dict["act_title"] = "THE COLLAPSE OF GENERAL PANTS CO."
    props_dict["audio_src"] = "episodes/EN_EP0268_general_pants_collapse/audio/audio_master_act1.mp3"
    
    # 3. Compile continuous Faster-Whisper subtitles
    dur1 = ts_data.get("scene_01", {}).get("duration", 7.42)
    dur2 = ts_data.get("scene_02", {}).get("duration", 7.84)
    dur3 = ts_data.get("scene_03", {}).get("duration", 8.26)
    dur4 = ts_data.get("scene_04", {}).get("duration", 8.55)

    offsets = [
        ("scene_01", 0.0),
        ("scene_02", dur1),
        ("scene_03", dur1 + dur2),
        ("scene_04", dur1 + dur2 + dur3),
    ]

    all_subtitles = []
    for sc_key, offset in offsets:
        words = ts_data.get(sc_key, {}).get("words", [])
        for w in words:
            all_subtitles.append({
                "word": w["word"],
                "start": round(w["start"] + offset, 3),
                "end": round(w["end"] + offset, 3),
            })

    props_dict["subtitles"] = all_subtitles
    total_sec = dur1 + dur2 + dur3 + dur4
    props_dict["durationInFrames"] = int(round(total_sec * 30))
    props_dict["fps"] = 30
    props_dict["width"] = 1920
    props_dict["height"] = 1080

    out_file = ROOT / "remotion" / "props_act1_deskworld.json"
    if not out_file.parent.exists():
        out_file = Path("/root/video_factory/remotion/props_act1_deskworld.json")
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(props_dict, f, indent=2)

    print(f"Generated Continuous DeskWorld props -> {out_file}")
    print(f"Total Duration: {total_sec:.2f}s ({props_dict['durationInFrames']} frames at 30fps)")
    print(f"Stations: {len(props_dict['stations'])}")
    print(f"Subtitles: {len(all_subtitles)} words")
    print(f"Global Yarns: {len(props_dict['global_yarns'])}")
    print(f"Camera Keyframes: {len(props_dict['camera_keyframes'])}")

if __name__ == "__main__":
    generate_props()
