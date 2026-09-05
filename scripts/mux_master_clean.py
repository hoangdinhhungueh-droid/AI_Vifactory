import os, sys, subprocess, json
from pathlib import Path

ep_id = 'en-byzantine-empire-ep001'
ep_dir = Path(f'/var/vf/episodes/{ep_id}')
concat_file = ep_dir / 'scenes_concat.txt'
silent_video = ep_dir / 'twolayer_silent.mp4'
master_video = ep_dir / 'master_video_pro.mp4'
voice_wav = ep_dir / 'audio' / 'voice_norm.wav'
bgm_path = Path('/root/video_factory/assets/bgm/calm_004_fs725597.mp3')
srt_path = ep_dir / 'subtitles.srt'

print('Step 1: Concatenating all 50 scenes into twolayer_silent.mp4...')
cmd_concat = [
    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
    '-i', str(concat_file),
    '-c', 'copy',
    str(silent_video)
]
subprocess.run(cmd_concat, check=True)
print(f'twolayer_silent.mp4 created: {silent_video.stat().st_size / (1024*1024):.2f} MB ✅')

print('Step 2: Muxing voice, ducked BGM, and burning subtitles...')
srt_str = str(srt_path)

cmd_master = [
    'ffmpeg', '-y',
    '-i', str(silent_video),
    '-i', str(voice_wav),
    '-stream_loop', '-1', '-i', str(bgm_path),
    '-filter_complex',
    f"[0:v]subtitles={srt_str}:force_style='FontSize=22,FontName=Arial,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=45'[v];"
    f"[2:a]volume=0.06[bgm];"
    f"[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
    '-map', '[v]', '-map', '[a]',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '320k', '-ar', '48000',
    '-shortest',
    str(master_video)
]
subprocess.run(cmd_master, check=True)
print(f'🎉 Master Video Pro generated: {master_video} ({master_video.stat().st_size / (1024*1024):.2f} MB) ✅')

print('Step 3: Quality probe (B9)...')
probe_out = subprocess.check_output([
    'ffprobe', '-v', 'error', '-show_entries',
    'format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name',
    '-of', 'json', str(master_video)
]).decode()
probe_data = json.loads(probe_out)
print(json.dumps(probe_data, indent=2))

# Cleanup scene chunk files
for sc in ep_dir.glob('sc_*.mp4'):
    sc.unlink()
print('Cleaned up scene segments. MASTER VIDEO READY! 🚀')
