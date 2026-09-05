#!/usr/bin/env python3
"""
Unified render + finalize entrypoint (D13 chuẩn hóa).
Chạy: python3 render_and_finalize_episode.py --episode-id EN_EP0206_topic --market EN

Thay thế 3 file cũ:
  - render_byzantine_master.py (hardcode EP_ID + audio_duration=847.39)
  - render_remotion_two_layer_master.py (hardcode EP_ID)
  - finalize_master_and_gate2.py (hardcode, chỉ là Gate-2 callback)
"""
import argparse
import os
import sys
import json
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '/root/video_factory')

def main():
    parser = argparse.ArgumentParser(description='Unified render + finalize')
    parser.add_argument('--episode-id', required=True, help='Episode ID (EN_EP0206_topic)')
    parser.add_argument('--market', required=True, help='Market code (EN/JP/KR)')
    args = parser.parse_args()

    episode_id = args.episode_id
    market = args.market
    ep_dir = f"/var/vf/episodes/{episode_id}"

    logger.info(f"[RENDER] Starting {episode_id} ({market})")

    # 1. Validate episode dir + load metadata
    if not os.path.exists(ep_dir):
        logger.error(f"Episode dir not found: {ep_dir}")
        return False
    
    brain_path = f"{ep_dir}/brain_input.json"
    if not os.path.exists(brain_path):
        logger.error(f"brain_input.json not found")
        return False
    
    with open(brain_path) as f:
        brain = json.load(f)
    
    # 2. Get audio duration dynamically (D20: không hardcode)
    audio_path = f"{ep_dir}/tts_out.mp3"
    if not os.path.exists(audio_path):
        logger.error(f"Audio not found: {audio_path}")
        return False
    
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1:novalue=1", audio_path],
            capture_output=True, text=True, timeout=10
        )
        audio_duration = float(result.stdout.strip())
        logger.info(f"[RENDER] Audio duration: {audio_duration:.3f}s")
    except Exception as e:
        logger.error(f"ffprobe failed: {e}")
        return False
    
    # 3. Build Remotion props (D20: lấy duration động)
    try:
        from app.services.mpt_ported.build_timestamp_accurate_props import build_remotion_props
        
        # Load scenes + segments từ episode
        whisper_path = f"{ep_dir}/whisper_segments.json"
        if os.path.exists(whisper_path):
            with open(whisper_path) as f:
                segments = json.load(f)
        else:
            segments = []
        
        scenes = brain.get("scenes", [])
        
        props = build_remotion_props(
            episode_id=episode_id,
            scenes=scenes,
            segments=segments,
            audio_duration=audio_duration,
            fps=30
        )
        
        props_path = f"{ep_dir}/remotion_props.json"
        with open(props_path, 'w') as f:
            json.dump(props, f)
        
        logger.info(f"[RENDER] Props built: {props_path}")
    except Exception as e:
        logger.error(f"Props build failed: {e}", exc_info=True)
        return False
    
    # 4. Call Remotion render (không hardcode EP_ID)
    try:
        logger.info(f"[RENDER] Calling Remotion...")
        # Giả sử: cd /root/video_factory && npm run render -- --props-path <path> --output <out>
        silent_mp4 = f"{ep_dir}/twolayer_silent.mp4"
        result = subprocess.run(
            ["npm", "run", "render", "--", "--props-path", props_path, "--output", silent_mp4],
            cwd="/root/video_factory",
            timeout=300
        )
        if result.returncode != 0:
            logger.error(f"Remotion render failed (rc={result.returncode})")
            return False
        logger.info(f"[RENDER] Remotion done: {silent_mp4}")
    except Exception as e:
        logger.error(f"Remotion call failed: {e}", exc_info=True)
        return False
    
    # 5. Mux audio + loudnorm (D20, D91: -14 LUFS)
    try:
        logger.info(f"[RENDER] Normalizing audio...")
        voice_norm = f"{ep_dir}/voice_norm.wav"
        
        # Loudnorm normalize
        result = subprocess.run(
            ["ffmpeg", "-i", audio_path, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-q:a", "9", voice_norm, "-y"],
            capture_output=True, timeout=60
        )
        if result.returncode != 0:
            logger.warning(f"Loudnorm failed, trying direct copy")
            subprocess.run(["cp", audio_path, voice_norm], timeout=10)
        
        logger.info(f"[RENDER] Audio normalized: {voice_norm}")
    except Exception as e:
        logger.error(f"Audio normalize failed: {e}", exc_info=True)
        return False
    
    # 6. Mux video + audio (D20: động duration)
    try:
        logger.info(f"[RENDER] Muxing audio → master video...")
        master_mp4 = f"{ep_dir}/master_video_pro.mp4"
        
        # Mux: video + normalized audio
        result = subprocess.run([
            "ffmpeg",
            "-i", silent_mp4,
            "-i", voice_norm,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            master_mp4, "-y"
        ], timeout=120)
        
        if result.returncode != 0:
            logger.error(f"Mux failed (rc={result.returncode})")
            return False
        
        logger.info(f"[RENDER] Master ready: {master_mp4}")
    except Exception as e:
        logger.error(f"Mux failed: {e}", exc_info=True)
        return False
    
    logger.info(f"[RENDER] ✅ Render complete: {episode_id}")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
