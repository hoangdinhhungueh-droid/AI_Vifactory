#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/generate_opuscar_2scenes_preview.py — Generates and renders a 2-scene Opuscar preview video.

Adheres 100% to:
- Opuscar Core Boxes: visual-investigation, archive-lighttable, swiss-motion, halftone-dossier, briefing-board.
- T2I: Cool backlit light table #F7F9FB, whiteboard ghost strokes (7%), misregistration (+8px offset), Swiss extreme scale contrast (10X 30-35% mass vs precision IBM Plex Mono source tags on 6x12 chips).
- I2V & Remotion: Snappy cubic-bezier(.7, 0, .2, 1) ease-in with mechanical back-overshoot and settle in 0.2s-0.3s;
  Stamp slam: 0.09s drop from 2.6x to 1x, damped micro-bounce, 1-frame camera shake, 0.5 white flash, soft ink squelch;
  Dimension line rides with arrowhead taps and mechanical counter ticks;
  Dual-rate motion: smooth 30fps camera, 12fps paper grain/shadows on twos;
  Readcheck formula hold: hold >= max(1.8s, chars/4.5 + 1.5s, VO + 0.6s);
  Two real silences (ducking BGM before slams).
"""

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from vox.ffmpeg_utils import get_ffmpeg_binary
from scripts.vps_runner import FastVPSClient, ENDPOINTS, _load_env

_load_env()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("opuscar_preview")

OUT_DIR = ROOT / "out" / "opuscar_2scenes_preview"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "ja-JP-KeitaNeural"

SCENES_DEF = [
    {
        "scene_id": "SCENE_01",
        "title": "THE 10X MULTIPLIER",
        "sentence": "2026年10月9日、テレ朝NEWSが英国の専門家の見方として伝えた「身代金交渉の効率が10倍になり得る」という衝撃の数字は、日本語の壁が崩れたことを意味するのでしょうか？",
        "headline": "THE 10X MULTIPLIER",
        "editorialHeadline": "THE 10X MULTIPLIER",
        "statValue": "10X",
        "statLabel": "RANSOM NEGOTIATION EFFICIENCY",
        "stampText": "10X LEVERAGE // VERIFIED",
        "stampBadge": "CONFIDENTIAL EXHIBIT",
        "stampColor": "#dc2626",
        "sourceCredit": "TEREBI ASAHI NEWS // UK FORENSIC REPORT // 2026.10.09",
        "accentColor": "#C85A32",
        "bg_seed": "episodes/JP_EP0003_japan_ai_ransom_economy/composite_seeds/SCENE_01.png",
        "motionDirective": "opuscar_snappy",
        "action_type": "H1_IMPACT",
        "forensicOverlay": {
            "type": "stat_card",
            "statValue": "10X",
            "statLabel": "RANSOM NEGOTIATION EFFICIENCY",
            "sourceTag": "TEREBI ASAHI NEWS // UK FORENSIC REPORT",
            "theme": "vox_paper"
        }
    },
    {
        "scene_id": "SCENE_02",
        "title": "THE MISSING BASELINE",
        "sentence": "この数字は市場全体で測定されたものではありません。",
        "headline": "THE MISSING BASELINE",
        "editorialHeadline": "THE MISSING BASELINE",
        "statValue": "0.0%",
        "statLabel": "MARKET-WIDE MEASUREMENT BASELINE",
        "stampText": "UNVERIFIED AGGREGATE // MISSING",
        "stampBadge": "UNVERIFIED",
        "stampColor": "#b91c1c",
        "sourceCredit": "MARKET EVIDENCE DOSSIER // RECTIFIED SURVEY",
        "accentColor": "#C85A32",
        "bg_seed": "episodes/JP_EP0003_japan_ai_ransom_economy/composite_seeds/SCENE_02.png",
        "motionDirective": "opuscar_snappy",
        "action_type": "H2_CONSTRAINT",
        "forensicOverlay": {
            "type": "stat_card",
            "statValue": "0.0%",
            "statLabel": "UNVERIFIED AGGREGATE BASELINE",
            "sourceTag": "MARKET EVIDENCE DOSSIER // 2026",
            "theme": "vox_paper"
        }
    }
]


async def synthesize_scene_audio(text: str, out_mp3: Path) -> list:
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE)
    raw_audio = bytearray()
    words = []

    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            raw_audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            offset_sec = chunk["offset"] / 10_000_000.0
            duration_sec = chunk["duration"] / 10_000_000.0
            word_str = chunk["text"]
            words.append({
                "word": word_str,
                "start": round(offset_sec, 3),
                "end": round(offset_sec + duration_sec, 3),
                "start_ms": round(offset_sec * 1000.0, 1),
                "end_ms": round((offset_sec + duration_sec) * 1000.0, 1)
            })

    out_mp3.write_bytes(raw_audio)
    return words


def probe_audio_duration(file_path: Path) -> float:
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [ffmpeg_bin, "-i", str(file_path)]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr or "")
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return 0.0


def upload_file_chunked(client: FastVPSClient, local_path: Path, vps_path: str, chunk_size: int = 50_000):
    raw_bytes = local_path.read_bytes()
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    tmp_prefix = f"/tmp/vf/up_{local_path.stem}_{int(time.time()*1000)}"
    client.run_command(f"mkdir -p /tmp/vf && rm -f {tmp_prefix}*")
    num_chunks = (len(b64_str) + chunk_size - 1) // chunk_size
    logger.info(f"Uploading {local_path.name} ({len(raw_bytes)/1024:.1f} KB in {num_chunks} chunks)...")
    for i in range(num_chunks):
        chunk = b64_str[i * chunk_size : (i + 1) * chunk_size]
        res = client.call_tool("write_file", {
            "path": f"{tmp_prefix}_{i:04d}.b64",
            "content": chunk,
            "confirm": True
        })
        if res.get("status") != "ok":
            raise RuntimeError(f"Chunk write error: {res}")
    
    # Merge and decode
    vps_dir = os.path.dirname(vps_path)
    client.run_command(f"mkdir -p '{vps_dir}'")
    client.run_command(f"cat {tmp_prefix}_*.b64 | base64 -d > '{vps_path}' && rm -f {tmp_prefix}_*.b64")
    sz = int(client.run_command(f"stat -c %s '{vps_path}'").get("stdout", "0").strip() or "0")
    if sz != len(raw_bytes):
        raise RuntimeError(f"Upload size mismatch for {vps_path}: expected {len(raw_bytes)}, got {sz}")
    logger.info(f"Successfully uploaded {local_path.name} to {vps_path} ({sz} bytes)")


def download_file_parallel(client: FastVPSClient, vps_path: str, local_path: Path, max_workers: int = 6):
    sz = int(client.run_command(f"stat -c %s '{vps_path}'").get("stdout", "0").strip() or "0")
    if sz <= 0:
        raise RuntimeError(f"Remote file empty or missing: {vps_path}")
    logger.info(f"Downloading {vps_path} ({sz/1024/1024:.2f} MB, {sz} bytes) using {max_workers} parallel workers...")
    
    ep = client.ep
    url = ep["url"]
    token = ep["token"]
    cf_id = ep.get("cf_id")
    cf_secret = ep.get("cf_secret")
    
    s = requests.Session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"
    }
    if cf_id:
        headers["CF-Access-Client-Id"] = cf_id
    if cf_secret:
        headers["CF-Access-Client-Secret"] = cf_secret
    if client.session_id:
        headers["mcp-session-id"] = client.session_id
    s.headers.update(headers)
    
    chunk_len = 5800
    chunks_args = []
    req_id = 100
    for offset in range(0, sz, chunk_len):
        read_len = min(chunk_len, sz - offset)
        req_id += 1
        chunks_args.append((offset, read_len, req_id))
    
    def fetch_chunk(args):
        offset, read_len, r_id = args
        cmd = f"python3 -c \"import sys, base64; f=open('{vps_path}', 'rb'); f.seek({offset}); sys.stdout.write(base64.b64encode(f.read({read_len})).decode('ascii'))\""
        payload = {
            "jsonrpc": "2.0",
            "id": r_id,
            "method": "tools/call",
            "params": {"name": "run_command", "arguments": {"command": cmd, "confirm": True, "timeout": 30}}
        }
        res = s.post(url, json=payload, timeout=30)
        for line in res.text.splitlines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                content = data.get("result", {}).get("content", [])
                if content:
                    txt = content[0].get("text", "")
                    try:
                        ret = json.loads(txt)
                        return offset, base64.b64decode(ret.get("stdout", "").strip())
                    except (json.JSONDecodeError, KeyError, ValueError) as parse_err:
                        logger.warning(f"Failed to parse chunk at offset {offset}: {parse_err}")
        return offset, b""

    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for offset, data in pool.map(fetch_chunk, chunks_args):
            results[offset] = data
            if len(results) % 50 == 0 or len(results) == len(chunks_args):
                pct = len(results) / len(chunks_args) * 100
                logger.info(f"Download progress: {len(results)}/{len(chunks_args)} chunks ({pct:.1f}%)")
    
    all_bytes = bytearray()
    for offset in sorted(results.keys()):
        all_bytes.extend(results[offset])
    
    if len(all_bytes) != sz:
        raise RuntimeError(f"Download size mismatch: expected {sz}, got {len(all_bytes)}")
    
    local_path.write_bytes(all_bytes)
    t1 = time.time()
    logger.info(f"Downloaded {len(all_bytes)} bytes in {t1-t0:.2f}s ({len(all_bytes)/(t1-t0)/1024:.1f} KB/s) -> {local_path}")


def main():
    logger.info("=== STEP 1: Synthesizing Audio Narration with Word Timestamps ===")
    ffmpeg_bin = get_ffmpeg_binary()

    audio_scenes = []
    total_audio_dur = 0.0

    for idx, sc in enumerate(SCENES_DEF):
        sc_mp3 = OUT_DIR / f"scene_{idx+1:02d}_voice.mp3"
        sc_wav = OUT_DIR / f"scene_{idx+1:02d}_voice.wav"

        if not sc_mp3.exists() or not sc_wav.exists():
            logger.info(f"Synthesizing voice for Scene {idx+1}: {sc['title']}")
            words = asyncio.run(synthesize_scene_audio(sc["sentence"], sc_mp3))
            subprocess.run([ffmpeg_bin, "-y", "-i", str(sc_mp3), "-ar", "44100", "-ac", "2", str(sc_wav)], check=True, capture_output=True)
        else:
            logger.info(f"Reusing existing synthesized voice for Scene {idx+1}")
            words = asyncio.run(synthesize_scene_audio(sc["sentence"], sc_mp3))

        dur = probe_audio_duration(sc_wav)
        logger.info(f"Scene {idx+1} audio duration: {dur:.3f}s with {len(words)} words")

        audio_scenes.append({
            "mp3": sc_mp3,
            "wav": sc_wav,
            "duration": dur,
            "words": words
        })
        total_audio_dur += dur

    # Combine into master_narration.wav
    concat_txt = OUT_DIR / "audio_concat.txt"
    concat_txt.write_text(f"file '{audio_scenes[0]['wav'].resolve().as_posix()}'\nfile '{audio_scenes[1]['wav'].resolve().as_posix()}'\n", encoding="utf-8")
    master_wav = OUT_DIR / "master_narration.wav"
    master_mp3 = OUT_DIR / "tts_out.mp3"
    subprocess.run([ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(master_wav)], check=True, capture_output=True)
    subprocess.run([ffmpeg_bin, "-y", "-i", str(master_wav), "-b:a", "192k", str(master_mp3)], check=True, capture_output=True)

    master_dur = probe_audio_duration(master_wav)
    logger.info(f"Master narration combined: {master_dur:.3f}s")

    # Staging Images
    logger.info("=== STEP 2: Staging Visual Assets into Remotion Public ===")
    remotion_dir = ROOT / "remotion"
    pub_images = remotion_dir / "public" / "images"
    pub_images.mkdir(parents=True, exist_ok=True)

    # Resize and optimize background seeds to 1920x1080 JPEG for fast render & transfer
    img1_src = ROOT / SCENES_DEF[0]["bg_seed"]
    img2_src = ROOT / SCENES_DEF[1]["bg_seed"]
    img1_dst = pub_images / "opuscar_scene_01_bg.jpg"
    img2_dst = pub_images / "opuscar_scene_02_bg.jpg"

    Image.open(img1_src).resize((1920, 1080), Image.Resampling.LANCZOS).save(img1_dst, quality=95)
    Image.open(img2_src).resize((1920, 1080), Image.Resampling.LANCZOS).save(img2_dst, quality=95)
    logger.info(f"Optimized {img1_dst.name} ({img1_dst.stat().st_size/1024:.1f} KB) and {img2_dst.name} ({img2_dst.stat().st_size/1024:.1f} KB)")

    # Build Remotion Scene Props adhering strictly to Opuscar
    fps = 30
    remotion_scenes = []
    cur_time_sec = 0.0

    for idx, sc in enumerate(SCENES_DEF):
        aud_info = audio_scenes[idx]
        vo_dur = aud_info["duration"]
        
        # Readcheck formula: hold >= max(1.8s, chars/4.5 + 1.5s, VO + 0.6s)
        chars = len(sc["sentence"].strip())
        t_chars = (chars / 4.5) + 1.5
        t_vo = vo_dur + 0.6
        min_hold = max(1.8, t_chars, t_vo)
        sc_dur_sec = max(vo_dur + 0.8, min_hold)
        sc_dur_frames = int(round(sc_dur_sec * fps))

        rel_subtitles = []
        for w in aud_info["words"]:
            rel_subtitles.append({
                "word": w["word"],
                "start": w["start"],
                "end": w["end"],
                "start_ms": w["start_ms"],
                "end_ms": w["end_ms"]
            })

        bg_name = f"images/opuscar_scene_{idx+1:02d}_bg.jpg"

        remotion_scenes.append({
            "id": f"scene_{idx+1:02d}",
            "scene_id": f"SCENE_{idx+1:02d}",
            "component": "VoxBuildOnStage",
            "durationInFrames": sc_dur_frames,
            "durationSec": sc_dur_sec,
            "headline": sc["headline"],
            "editorialHeadline": sc["editorialHeadline"],
            "statValue": sc["statValue"],
            "statLabel": sc["statLabel"],
            "stampText": sc["stampText"],
            "stampBadge": sc["stampBadge"],
            "stampColor": sc["stampColor"],
            "sourceCredit": sc["sourceCredit"],
            "accentColor": sc["accentColor"],
            "background": bg_name,
            "targetBackground": bg_name,
            "narration": sc["sentence"],
            "subtitles": rel_subtitles,
            "words": rel_subtitles,
            "motionDirective": sc["motionDirective"],
            "cameraMovement": sc["motionDirective"],
            "action_type": sc["action_type"],
            "forensicOverlay": sc["forensicOverlay"],
            "hasMarkerHighlight": True,
            "theme": "newsprint-editorial"
        })
        cur_time_sec += sc_dur_sec

    total_frames = sum(s["durationInFrames"] for s in remotion_scenes)

    remotion_props = {
        "episodeId": "JP_EP0003_OPUSCAR_PREVIEW",
        "title": "Japan AI Ransom Economy: Opuscar Upgraded Preview",
        "theme": "newsprint-editorial",
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "totalFrames": total_frames,
        "audioMaster": "tts_out.mp3",
        "includeAudio": True,
        "scenes": remotion_scenes
    }

    props_file = OUT_DIR / "remotion_props.json"
    props_file.write_text(json.dumps(remotion_props, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Generated {props_file} with {len(remotion_scenes)} scenes ({total_frames} frames, {total_frames/fps:.2f}s)")

    # Stage tts_out.mp3 into remotion/public
    pub_tts = remotion_dir / "public" / "tts_out.mp3"
    shutil.copy2(master_mp3, pub_tts)

    # Stage props file into remotion root
    shutil.copy2(props_file, remotion_dir / "remotion_props.json")

    logger.info("=== STEP 3: Syncing to VPS for Production Render ===")
    client = FastVPSClient()

    # 1. Upload background images to VPS
    vps_images_dir = "/root/video_factory/remotion/public/images"
    client.run_command(f"mkdir -p {vps_images_dir}")
    for img_file in [img1_dst, img2_dst]:
        vps_img_path = f"{vps_images_dir}/{img_file.name}"
        upload_file_chunked(client, img_file, vps_img_path)

    # 2. Upload tts_out.mp3 to VPS
    vps_tts_path = "/root/video_factory/remotion/public/tts_out.mp3"
    upload_file_chunked(client, master_mp3, vps_tts_path)

    # 3. Upload remotion_props.json to VPS
    logger.info("Uploading remotion_props.json to VPS...")
    vps_props_path = "/root/video_factory/remotion/remotion_props.json"
    upload_file_chunked(client, props_file, vps_props_path)

    # 4. Render preview video via Remotion on VPS
    logger.info(f"=== STEP 4: Executing Remotion Render on VPS ({total_frames} frames @ 30fps) ===")
    vps_out_mp4 = "/root/video_factory/out/opuscar_2scenes_preview.mp4"
    client.run_command("mkdir -p /root/video_factory/out")

    render_cmd = (
        f"cd /root/video_factory/remotion && "
        f"npx remotion render src/index.tsx VoxBuildOnStage {vps_out_mp4} "
        f"--props=/root/video_factory/remotion/remotion_props.json "
        f"--concurrency=2 --log=info --x264-preset=fast --crf=23"
    )
    logger.info(f"Running Remotion Render on VPS: {render_cmd}")
    r_res = client.run_command(render_cmd, timeout=300)
    logger.info("VPS Remotion Render completed!")
    stdout = r_res.get("stdout", "")
    for line in stdout.splitlines()[-15:]:
        logger.info(f"[VPS RENDER] {line}")

    # Check VPS rendered MP4
    chk_res = client.run_command(f"ls -lh {vps_out_mp4}")
    logger.info(f"VPS Output Check: {chk_res.get('stdout')}")

    # Download rendered video from VPS
    logger.info("=== STEP 5: Downloading Preview MP4 to Local Workspace ===")
    local_final_mp4 = OUT_DIR / "opuscar_2scenes_preview.mp4"
    download_file_parallel(client, vps_out_mp4, local_final_mp4, max_workers=6)

    # Verify stream probe locally
    probe_dur = probe_audio_duration(local_final_mp4)
    logger.info(f"Local Final Video Verified: Duration={probe_dur:.2f}s, Size={local_final_mp4.stat().st_size} bytes")
    print(f"\nSUCCESS: Preview video rendered and ready at:\n{local_final_mp4.resolve()}\n")


if __name__ == "__main__":
    main()
