import os, sys, json, asyncio, subprocess, time

sys.path.insert(0, '/root/video_factory')
import scripts.compile_episode_from_notion as comp
comp._token()

from app.pipeline.stages.s6_subtitle import run_s6
from app.services.seo_metadata import write_seo_payloads

episode_id = 'en-byzantine-empire-ep001'
out_dir = f'/var/vf/episodes/{episode_id}'
os.makedirs(out_dir, exist_ok=True)

with open(f'{out_dir}/brain_input.json', 'r', encoding='utf-8') as f:
    brain = json.load(f)

story_text = brain.get('story', '')
audio_path = f'{out_dir}/master_soundtrack.mp3'
if not os.path.exists(audio_path):
    audio_path = f'{out_dir}/voiceover_norm.mp3'

episode = {
    'episode_id': episode_id,
    'audio_path': audio_path,
    'lang_code': 'en',
    'transcript': story_text,
    'text': story_text,
    'niche': 'documentary',
    'mood': brain.get('bgm_mood', 'dramatic'),
    'hook_3s': brain.get('hook_3s', ''),
    'scenes': brain.get('scenes', []),
    'trend_keywords': brain.get('trend_keywords', []),
    'visual_terms': brain.get('visual_terms', []),
    'art_style': brain.get('art_style', {})
}

async def main():
    print('=== 1. Running S6 Whisper Subtitle Alignment ===')
    t0 = time.time()
    s6_res = await run_s6(episode)
    print(f'S6 Done in {time.time() - t0:.1f}s!')
    srt_path = s6_res.get('srt_path', f'{out_dir}/subtitles.srt')
    print('SRT Path:', srt_path, 'Exists:', os.path.exists(srt_path))

    print('=== 2. Building SEO Payloads (S7.5) ===')
    seo_res = write_seo_payloads(episode, out_dir)
    print('SEO Payloads generated:', list((seo_res or {}).keys()))
    payload_path = f'{out_dir}/youtube_upload_payload.json'
    print('YouTube Payload path:', payload_path, 'Exists:', os.path.exists(payload_path))

    print('=== 3. Burning Subtitles into 1080p Master Video ===')
    raw_video = f'{out_dir}/raw_concat_fast.mp4'
    soundtrack = f'{out_dir}/master_soundtrack.mp3'
    master_final = f'{out_dir}/master_video_pro.mp4'
    
    # Documentary grade + Subtitles Burn-in filter
    # Font styling: Arial/DejaVu Sans, 20pt, white with black outline, bottom margin 60
    vf_filters = (
        f"eq=contrast=1.06:saturation=0.92:gamma=0.98,"
        f"colorbalance=bs=0.04:rm=0.03:gm=-0.01,"
        f"noise=alls=4:allf=t,"
        f"vignette=PI/8,"
        f"subtitles='{srt_path}':force_style='Fontname=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=60,Alignment=2'"
    )

    cmd_burn = [
        'ffmpeg', '-y',
        '-i', raw_video,
        '-i', soundtrack,
        '-filter_complex', f'[0:v]{vf_filters}[v]',
        '-map', '[v]',
        '-map', '1:a:0',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '17',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        master_final
    ]
    print('Executing FFmpeg subtitle burn...')
    t1 = time.time()
    subprocess.run(cmd_burn, check=True)
    print(f'FFmpeg Master Burn complete in {time.time() - t1:.1f}s!')

    print('=== 4. Extracting Verification Snapshot Frames ===')
    snapshot_dir = f'{out_dir}/snapshots'
    os.makedirs(snapshot_dir, exist_ok=True)
    for ts in ['00:00:15', '00:01:30', '00:04:00']:
        fname = f"{snapshot_dir}/frame_{ts.replace(':', '')}.jpg"
        subprocess.run(['ffmpeg', '-y', '-ss', ts, '-i', master_final, '-vframes', '1', '-q:v', '2', fname], check=True)
        print('Saved snapshot:', fname)

    print('🎉 COMPLETE MASTER WITH SUBTITLES & SEO READY! ✅')

if __name__ == '__main__':
    asyncio.run(main())
