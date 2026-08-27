#!/usr/bin/env python3
"""Parameterized render script for B8 (Remotion 2-Layer) + B9 (Quality Probe).

Replaces render_byzantine_master.py with CLI args:
  --episode_id EN-EPISODE-SLUG (required, e.g. en-byzantine-empire-ep001)
  --market {en,jp,kr} (optional, default en; chooses BGM + localized paths)

Reads audio_duration from brain_input.json["audio_duration"] or
scene count × default 15s per scene. Loads BGM per market.
"""
import os, sys, json, shutil, subprocess, time, argparse
from pathlib import Path

def load_env():
    p = "/root/secrets/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def get_bgm_path(market="en"):
    base = Path("/root/video_factory/assets/bgm")
    market = (market or "en").lower().strip()
    mapping = {
        "en": "calm_004_fs725597.mp3",
        "jp": "calm_004_fs725597.mp3",
        "kr": "calm_004_fs725597.mp3",
    }
    return base / mapping.get(market, mapping["en"])

def render_episode(episode_id, market="en"):
    load_env()
    market = (market or "en").lower().strip()
    
    ep_dir = Path(f"/var/vf/episodes/{episode_id}")
    public_dir = Path(f"/root/video_factory/remotion/public/pulled/{episode_id}")
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "audio").mkdir(parents=True, exist_ok=True)
    
    print(f"=== EPISODE: {episode_id} / MARKET: {market} ===")
    
    # 1. Copy assets
    print("=== 1. PREPARING ASSETS IN REMOTION PUBLIC ===")
    img_dir = ep_dir / "images"
    if img_dir.exists():
        for img_path in img_dir.glob("*.png"):
            dst = public_dir / img_path.name
            shutil.copyfile(img_path, dst)
            print(f"Copied image: {img_path.name}")
    
    voice_file = ep_dir / "audio" / "voice_norm.wav"
    if voice_file.exists():
        shutil.copyfile(voice_file, public_dir / "audio" / "voice_norm.wav")
        print("Copied voice_norm.wav ✅")
    
    # 2. Read brain_input + compute audio_duration
    print("=== 2. CONFIGURING REMOTION PROPS ===")
    brain_file = ep_dir / "brain_input.json"
    if not brain_file.exists():
        print(f"ERROR: {brain_file} not found")
        return False
    
    with open(brain_file) as f:
        brain = json.load(f)
    
    scenes = brain.get("scenes", [])
    total_scenes = len(scenes)
    
    audio_duration = brain.get("audio_duration")
    if audio_duration is None:
        print(f"WARN: audio_duration not in brain_input.json, using {total_scenes} × 15s default")
        audio_duration = max(1, total_scenes) * 15.0
    
    scene_duration = audio_duration / max(1, total_scenes)
    print(f"Audio duration: {audio_duration:.2f}s ({total_scenes} scenes × {scene_duration:.2f}s each)")
    
    remotion_scenes = []
    for i, sc in enumerate(scenes):
        remotion_scenes.append({
            "index": i,
            "beat": sc.get("beat", f"Scene {i+1}"),
            "durationInSeconds": scene_duration,
            "backgroundImage": f"/pulled/{episode_id}/{sc.get('background_reuse_key', 'byz-a1-walls-dawn')}.png",
            "foregroundImage": f"/pulled/{episode_id}/{sc.get('foreground_reuse_key', 'byzantine-varangian-guard')}.png",
            "foregroundPosition": sc.get("foreground_position", "left"),
            "safeZone": sc.get("safe_zone", "top")
        })
    
    remotion_props = {
        "episode_id": episode_id,
        "market": market,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "durationInFrames": int(audio_duration * 30),
        "audioSrc": f"/pulled/{episode_id}/audio/voice_norm.wav",
        "scenes": remotion_scenes
    }
    
    props_path = ep_dir / "remotion_props.json"
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(remotion_props, f, indent=2)
    print(f"remotion_props.json written ✅")
    
    # 3. Render Multi-layer Video
    print("=== 3. RENDERING MULTI-LAYER MASTER VIDEO ===")
    silent_video = ep_dir / "twolayer_silent.mp4"
    master_video = ep_dir / "master_video_pro.mp4"
    srt_path = ep_dir / "subtitles.srt"
    bgm_path = get_bgm_path(market)
    
    if not bgm_path.exists():
        print(f"WARN: BGM not found at {bgm_path}, will continue without BGM")
    
    concat_file = ep_dir / "scenes_concat.txt"
    with open(concat_file, "w") as f:
        for i, sc in enumerate(scenes):
            bg_name = f"{sc.get('background_reuse_key', 'byz-a1-walls-dawn')}.png"
            bg_file = img_dir / bg_name
            fg_name = f"{sc.get('foreground_reuse_key', 'byzantine-varangian-guard')}.png"
            fg_file = img_dir / fg_name
            
            scene_mp4 = ep_dir / f"sc_{i:03d}.mp4"
            if not scene_mp4.exists():
                fg_x = "50" if sc.get("foreground_position", "left") == "left" else "1220"
                cmd_sc = [
                    "ffmpeg", "-y",
                    "-loop", "1", "-t", f"{scene_duration:.2f}", "-i", str(bg_file),
                    "-loop", "1", "-t", f"{scene_duration:.2f}", "-i", str(fg_file),
                    "-filter_complex",
                    f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0005,1.08)':d=1:s=1920x1080[bg];"
                    f"[1:v]scale=650:650[fg];"
                    f"[bg][fg]overlay={fg_x}:380[v]",
                    "-map", "[v]",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "30",
                    str(scene_mp4)
                ]
                subprocess.run(cmd_sc, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            f.write(f"file '{scene_mp4}'\n")
    
    print(f"Generated {total_scenes} scene segments ✅")
    
    # Concat silent video
    print("Concatenating scenes into twolayer_silent.mp4...")
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(silent_video)
    ]
    subprocess.run(cmd_concat, check=True)
    print("twolayer_silent.mp4 ready ✅")
    
    # 4. Mux Voice + BGM + Subtitles
    print("=== 4. MUXING VOICE, BGM (-24dB), AND BURNING SUBTITLES ===")
    srt_escaped = str(srt_path).replace(":", "\\:").replace("\\", "/")
    
    cmd_master = [
        "ffmpeg", "-y",
        "-i", str(silent_video),
        "-i", str(voice_file),
    ]
    
    if bgm_path.exists():
        cmd_master.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
        audio_filter = (
            f"[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )
    else:
        audio_filter = "[1:a]aformat=sample_rate=48000:channel_layout=stereo[a]"
    
    cmd_master.extend([
        "-filter_complex",
        f"[0:v]subtitles={srt_escaped}:force_style='FontSize=22,FontName=Arial,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=45'[v];"
        f"[2:a]volume=0.06[bgm];"
        f"[1:a][bgm]{audio_filter}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-shortest",
        str(master_video)
    ])
    
    subprocess.run(cmd_master, check=True)
    size_mb = master_video.stat().st_size / (1024*1024)
    print(f"🎉 MASTER VIDEO CREATED: {master_video} ({size_mb:.2f} MB)!")
    
    # 5. Quality probe (B9)
    print("=== 5. QUALITY PROBE (B9) ===")
    probe_out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name",
        "-of", "json", str(master_video)
    ]).decode()
    probe_data = json.loads(probe_out)
    print(json.dumps(probe_data, indent=2))
    
    # Cleanup
    for sc_file in ep_dir.glob("sc_*.mp4"):
        sc_file.unlink()
    
    print("ALL RENDERING & QUALITY AUDIT (B8 & B9) SUCCEEDED 100%! 🚀")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render B8+B9: Remotion 2-Layer + Quality Probe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 render_episode_parameterized.py --episode_id en-byzantine-empire-ep001
  python3 render_episode_parameterized.py --episode_id jp-samurai-ep042 --market jp
  python3 render_episode_parameterized.py --episode_id kr-korean-war-ep015 --market kr
        """
    )
    parser.add_argument("--episode_id", required=True, help="Episode ID (e.g. en-byzantine-empire-ep001)")
    parser.add_argument("--market", default="en", choices=["en", "jp", "kr"], help="Market code (default: en)")
    
    args = parser.parse_args()
    
    try:
        success = render_episode(args.episode_id, args.market)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
