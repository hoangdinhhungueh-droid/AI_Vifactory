#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/generate_opuscar_2scenes_preview.py — Generates and renders a 4-scene Opuscar preview video.

Adheres 100% to:
- Opuscar Core Boxes: visual-investigation, archive-lighttable, swiss-motion, halftone-dossier, briefing-board.
- Micro-Beat Fragmentation: Decomposes monolithic sentences into snappy 3.0s-4.5s scenes.
- T2I: 100% clean diorama paper on #F4F1EA, 0% baked English typography.
- I2V: Omni drives 100% of 3D camera (SURFACE_MACRO_GLIDE, DYNAMIC_CRASH_PUNCH, RAKE_30_RACK_FOCUS, SLOW_PUSH_IN) and tactile kinetics (H1-H7).
- Remotion: Strictly locked compositor (1.0x) with Swiss Grid vector overlays and Whisper 0ms karaoke.
- Pacing: sc_dur_sec = max(3.2, vo_dur + 0.6) with zero freeze frames.
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
from typing import Any, Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("generate_opuscar_preview")

OUT_DIR = ROOT / "out" / "opuscar_preview"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "ja-JP-KeitaNeural"

SCENES_DEF = [
    {
        "scene_id": "SCENE_01",
        "title": "THE 10X CATALYST",
        "sentence": "2026年10月9日、テレ朝NEWSが伝えた衝撃の報告。",
        "headline": "BREAKING INVESTIGATION",
        "editorialHeadline": "OCTOBER 9 SPECIAL DISPATCH",
        "statValue": "2026.10.09",
        "statLabel": "SPECIAL INVESTIGATIVE DISPATCH",
        "stampText": "TEREBI ASAHI // DISPATCHED",
        "stampBadge": "CONFIDENTIAL EXHIBIT",
        "stampColor": "#dc2626",
        "sourceCredit": "TEREBI ASAHI NEWS // BROADCAST DISPATCH // 2026.10.09",
        "accentColor": "#C85A32",
        "bg_seed": "episodes/JP_EP0003_japan_ai_ransom_economy/composite_seeds/SCENE_01.png",
        "motionDirective": "opuscar_snappy",
        "action_type": "H6_MARK",
        "camera_directive": "SURFACE_MACRO_GLIDE",
        "hero_cutout_object": "Japanese broadcast newsprint archival report document on cream paper",
        "interacting_tool": "neon yellow marker highlighting key investigative clause",
        "forensicOverlay": {
            "type": "stat_card",
            "statValue": "2026.10.09",
            "statLabel": "SPECIAL INVESTIGATIVE DISPATCH",
            "sourceTag": "TEREBI ASAHI NEWS // 2026.10.09",
            "theme": "vox_paper"
        }
    },
    {
        "scene_id": "SCENE_02",
        "title": "THE 10X MULTIPLIER",
        "sentence": "英国の専門家が警告する「身代金交渉の効率10倍」。",
        "headline": "THE 10X MULTIPLIER",
        "editorialHeadline": "RANSOM NEGOTIATION EFFICIENCY",
        "statValue": "10X",
        "statLabel": "RANSOM NEGOTIATION EFFICIENCY",
        "stampText": "10X LEVERAGE // VERIFIED",
        "stampBadge": "CONFIDENTIAL EXHIBIT",
        "stampColor": "#dc2626",
        "sourceCredit": "UK FORENSIC EXPERT TESTIMONY // 2026.10.09",
        "accentColor": "#C85A32",
        "bg_seed": "episodes/JP_EP0003_japan_ai_ransom_economy/composite_seeds/SCENE_02.png",
        "motionDirective": "opuscar_snappy",
        "action_type": "H1_IMPACT",
        "camera_directive": "DYNAMIC_CRASH_PUNCH",
        "hero_cutout_object": "accounting ledger cardstock with giant tactile cutout number 10X",
        "interacting_tool": "turned-wood vermilion seal stamp slamming down in 0.09s",
        "forensicOverlay": {
            "type": "stat_card",
            "statValue": "10X",
            "statLabel": "RANSOM NEGOTIATION EFFICIENCY",
            "sourceTag": "UK FORENSIC REPORT // 2026.10.09",
            "theme": "vox_paper"
        }
    },
    {
        "scene_id": "SCENE_03",
        "title": "THE LANGUAGE FIREWALL",
        "sentence": "それは、日本語という最後の壁が崩れたことを意味するのか。",
        "headline": "DEFENSE PERIMETER BREACH",
        "editorialHeadline": "JAPANESE LANGUAGE WALL COLLAPSE",
        "statValue": "BREACH",
        "statLabel": "LANGUAGE DEFENSE BARRIER BREACHED",
        "stampText": "PERIMETER FAILURE // CONFIRMED",
        "stampBadge": "SECURITY ADVISORY",
        "stampColor": "#b91c1c",
        "sourceCredit": "CYBERSECURITY INCIDENT ARCHIVE // 2026",
        "accentColor": "#C85A32",
        "bg_seed": "episodes/JP_EP0003_japan_ai_ransom_economy/composite_seeds/SCENE_03.png",
        "motionDirective": "opuscar_snappy",
        "action_type": "H2_CONSTRAINT",
        "camera_directive": "RAKE_30_RACK_FOCUS",
        "hero_cutout_object": "corporate network language firewall blueprint architectural diagram",
        "interacting_tool": "vintage precision brass vernier calipers clamping onto breached perimeter",
        "forensicOverlay": {
            "type": "stat_card",
            "statValue": "BREACH",
            "statLabel": "LANGUAGE BARRIER COLLAPSE",
            "sourceTag": "CYBERSECURITY ARCHIVE // 2026",
            "theme": "vox_paper"
        }
    },
    {
        "scene_id": "SCENE_04",
        "title": "THE MISSING BASELINE",
        "sentence": "この数字は市場全体で測定されたものではありません。",
        "headline": "THE MISSING BASELINE",
        "editorialHeadline": "MARKET-WIDE MEASUREMENT BASELINE",
        "statValue": "0.0%",
        "statLabel": "UNVERIFIED AGGREGATE BASELINE",
        "stampText": "UNVERIFIED AGGREGATE // MISSING",
        "stampBadge": "UNVERIFIED",
        "stampColor": "#b91c1c",
        "sourceCredit": "MARKET EVIDENCE DOSSIER // RECTIFIED SURVEY",
        "accentColor": "#C85A32",
        "bg_seed": "episodes/JP_EP0003_japan_ai_ransom_economy/composite_seeds/SCENE_04.png",
        "motionDirective": "opuscar_snappy",
        "action_type": "H7_DISPLACE",
        "camera_directive": "SLOW_PUSH_IN_0_1X",
        "hero_cutout_object": "manila market survey evidence dossier folio unfolding",
        "interacting_tool": "red evidence pointer indicator revealing zero baseline metric card",
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


def extract_whisper_words_from_wav(wav_path: Path, language: str = "ja") -> list:
    """Extract real word-level timestamps using faster-whisper with safe PyAV wrapper (Rule 120)."""
    try:
        import av
        if hasattr(av, "open") and not getattr(av.open, "_safe_metadata_wrapped", False):
            _real_av_open = av.open
            def _safe_av_open(*args, **kwargs):
                if kwargs.get("metadata_errors") == "ignore":
                    kwargs.pop("metadata_errors", None)
                return _real_av_open(*args, **kwargs)
            _safe_av_open._safe_metadata_wrapped = True
            av.open = _safe_av_open
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(wav_path), language=language, word_timestamps=True)
        words = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "start_ms": round(w.start * 1000.0, 1),
                        "end_ms": round(w.end * 1000.0, 1),
                        "confidence": round(w.probability, 3)
                    })
        return words
    except Exception as e:
        logger.warning(f"Whisper extraction failed: {e}. Falling back to TTS boundary words.")
        return []


def get_ffmpeg_binary() -> str:
    candidates = [
        shutil.which("ffmpeg"),
        str(ROOT / "bin" / "ffmpeg.exe"),
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Users\\hunghd2\\AppData\\Local\\Microsoft\\WinGet\\Links\\ffmpeg.exe",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return str(c)
    return "ffmpeg"


def probe_audio_duration(file_path: Path) -> float:
    ffmpeg_bin = get_ffmpeg_binary()
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg.exe", "ffprobe.exe") if "ffmpeg.exe" in ffmpeg_bin else "ffprobe"
    try:
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        return float(data["format"]["duration"])
    except Exception:
        # Fallback using ffmpeg parse
        cmd = [ffmpeg_bin, "-i", str(file_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if m:
            h, mn, s = m.groups()
            return int(h) * 3600 + int(mn) * 60 + float(s)
        return 4.0


class FastVPSClient:
    def __init__(self):
        self.base_url = "https://n8n.kienthucquant.com/webhook/vf-terminal-v2"
        self.cf_token = os.environ.get("CF_ACCESS_TOKEN", "").strip()
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}
        if self.cf_token:
            self.headers["cf-access-token"] = self.cf_token
            self.headers["Authorization"] = f"Bearer {self.cf_token}"

    def run_command(self, cmd: str, timeout: int = 120) -> Dict[str, Any]:
        payload = {"command": cmd, "timeout": timeout, "confirm": True}
        try:
            resp = self.session.post(self.base_url, json=payload, headers=self.headers, timeout=timeout + 15)
            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as e:
            logger.error(f"VPS command failed: {e}")
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}


def upload_file_chunked(client: FastVPSClient, local_path: Path, remote_path: Path, chunk_size: int = 200_000):
    content = local_path.read_bytes()
    total_sz = len(content)
    logger.info(f"Uploading {local_path.name} ({total_sz/1024:.1f} KB) to {remote_path}...")

    client.run_command(f"rm -f '{remote_path}' '{remote_path}.tmp'")
    client.run_command(f"mkdir -p '{Path(remote_path).parent}'")

    for i in range(0, total_sz, chunk_size):
        chunk = content[i : i + chunk_size]
        b64 = base64.b64encode(chunk).decode("ascii")
        res = client.run_command(f"python3 -c \"import base64; open('{remote_path}.tmp', 'ab').write(base64.b64decode('{b64}'))\"")
        if res.get("exit_code") != 0:
            raise RuntimeError(f"Failed to append chunk: {res.get('stderr')}")

    mv_res = client.run_command(f"mv '{remote_path}.tmp' '{remote_path}'")
    if mv_res.get("exit_code") != 0:
        raise RuntimeError(f"Failed to finalize upload: {mv_res.get('stderr')}")

    stat_res = client.run_command(f"stat -c %s '{remote_path}'")
    vps_sz = int(stat_res.get("stdout", "0").strip() or "0")
    if vps_sz != total_sz:
        raise ValueError(f"Size mismatch: local={total_sz}, VPS={vps_sz}")
    logger.info(f"Uploaded {local_path.name} verified: {vps_sz} bytes matches local.")


def download_file_parallel(client: FastVPSClient, remote_path: str, local_path: Path, max_workers: int = 6):
    stat_res = client.run_command(f"stat -c %s '{remote_path}'")
    total_bytes = int(stat_res.get("stdout", "0").strip() or "0")
    if total_bytes == 0:
        raise RuntimeError(f"Remote file {remote_path} is missing or 0 bytes.")

    chunk_size = 250_000
    chunks = []
    for off in range(0, total_bytes, chunk_size):
        chunks.append((off, min(chunk_size, total_bytes - off)))

    out_bytes = bytearray(total_bytes)
    logger.info(f"Downloading {remote_path} ({total_bytes/1024/1024:.2f} MB) in {len(chunks)} chunks...")

    def fetch_chunk(idx_off):
        idx, (off, sz) = idx_off
        cmd = f"python3 -c \"import base64; f=open('{remote_path}','rb'); f.seek({off}); print(base64.b64encode(f.read({sz})).decode('ascii'))\""
        r = client.run_command(cmd, timeout=60)
        b64_str = r.get("stdout", "").strip()
        data = base64.b64decode(b64_str)
        return off, data

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = pool.map(fetch_chunk, enumerate(chunks))
        for off, data in results:
            out_bytes[off : off + len(data)] = data

    local_path.write_bytes(out_bytes)
    try:
        sz_local = local_path.stat().st_size
    except OSError as stat_err:
        logger.warning(f"Failed to read file size for {local_path}: {stat_err}")
        sz_local = 0
    if sz_local != total_bytes:
        raise ValueError(f"Download size mismatch: remote={total_bytes}, local={sz_local}")
    logger.info(f"Downloaded {local_path.name} verified ({sz_local} bytes).")


def main():
    logger.info("=================================================================")
    logger.info("   OPUSCAR 4-SCENE MICRO-BEAT PREVIEW PIPELINE (Rule 140 / v3)  ")
    logger.info("=================================================================")

    ffmpeg_bin = get_ffmpeg_binary()

    audio_scenes = []
    total_audio_dur = 0.0

    logger.info("=== STEP 1A: Synthesizing Edge TTS & Extracting Whisper Word Timestamps ===")
    for idx, sc in enumerate(SCENES_DEF):
        sc_mp3 = OUT_DIR / f"scene_{idx+1:02d}_voice.mp3"
        sc_wav = OUT_DIR / f"scene_{idx+1:02d}_voice.wav"

        logger.info(f"Synthesizing voice for Scene {idx+1}: {sc['title']}")
        words = asyncio.run(synthesize_scene_audio(sc["sentence"], sc_mp3))
        subprocess.run([ffmpeg_bin, "-y", "-i", str(sc_mp3), "-ar", "44100", "-ac", "2", str(sc_wav)], check=True, capture_output=True)

        if not words:
            logger.info(f"Extracting real Whisper word timestamps from {sc_wav.name} (Rule 120)...")
            words = extract_whisper_words_from_wav(sc_wav, language="ja")

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
    concat_lines = [f"file '{s['wav'].resolve().as_posix()}'" for s in audio_scenes]
    concat_txt.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    master_wav = OUT_DIR / "master_narration.wav"
    master_mp3 = OUT_DIR / "tts_out.mp3"
    subprocess.run([ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(master_wav)], check=True, capture_output=True)
    subprocess.run([ffmpeg_bin, "-y", "-i", str(master_wav), "-b:a", "192k", str(master_mp3)], check=True, capture_output=True)

    master_dur = probe_audio_duration(master_wav)
    logger.info(f"Master narration combined: {master_dur:.3f}s across {len(audio_scenes)} scenes")

    logger.info("=== STEP 1B: Generating 4 Opuscar Scene Manifests & Prompts ===")
    from app.services.kinetic_sub_director import (
        build_cl3_paper_diorama_prompt,
        generate_scene_sub_director_plan,
    )

    manifest = {}
    for idx, sc in enumerate(SCENES_DEF):
        sc_id = sc["scene_id"]
        sub_plan = generate_scene_sub_director_plan(
            scene_id=sc_id,
            sentence=sc["sentence"],
            hero_cutout_object=sc.get("hero_cutout_object", "archival document on cream diorama"),
            interacting_objects=[sc.get("interacting_tool", "precision tactile tool")],
            duration_sec=audio_scenes[idx]["duration"],
            market="JP",
            whisper_words=audio_scenes[idx]["words"] if audio_scenes[idx]["words"] else None,
            camera_directive=sc.get("camera_directive", "SLOW_PUSH_IN_0_1X")
        )
        prompt_i2v = build_cl3_paper_diorama_prompt(sub_plan, market="JP", style_mode="deep_diorama")
        manifest[sc_id.lower()] = {
            "definition": sc,
            "sub_director_plan": sub_plan,
            "canonical_i2v_prompt": prompt_i2v
        }

    manifest_path = OUT_DIR / "opuscar_scene_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved Opuscar Scene Manifest to: {manifest_path}")

    # Staging Real Omni Video Assets into Remotion Public
    logger.info("=== STEP 2: Staging Real Omni Video Assets into Remotion Public ===")
    remotion_dir = ROOT / "remotion"
    pub_videos = remotion_dir / "public" / "videos"
    pub_videos.mkdir(parents=True, exist_ok=True)

    staged_videos = []
    base_vids = ROOT / "episodes/JP_EP0003_japan_ai_ransom_economy/blocks/block_01_the_10x_catalyst_&_the_shock_metric/videos"
    for idx in range(len(SCENES_DEF)):
        vid_src = base_vids / f"clip_scene_{idx+1:02d}.mp4"
        vid_dst = pub_videos / f"opuscar_scene_{idx+1:02d}_omni.mp4"
        if vid_src.exists():
            shutil.copy2(vid_src, vid_dst)
            staged_videos.append(vid_dst)
            logger.info(f"Staged {vid_dst.name} ({vid_dst.stat().st_size/1024:.1f} KB)")
        else:
            logger.warning(f"Video source not found: {vid_src}")

    # Build Remotion Scene Props adhering strictly to Opuscar
    fps = 30
    remotion_scenes = []
    cur_time_sec = 0.0

    for idx, sc in enumerate(SCENES_DEF):
        aud_info = audio_scenes[idx]
        vo_dur = aud_info["duration"]

        # Fast-paced Vox explainer pacing:
        # Pacing: ~3.2s to 4.5s per shot, tail hold = 0.6s
        sc_dur_sec = max(3.2, vo_dur + 0.6)
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

        bg_name = f"videos/opuscar_scene_{idx+1:02d}_omni.mp4"

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
            "sourceTag": sc.get("sourceTag") or sc.get("sourceCredit"),
            "stampText": sc["stampText"],
            "stampBadge": sc["stampBadge"],
            "stampColor": sc["stampColor"],
            "sourceCredit": sc["sourceCredit"],
            "accentColor": sc["accentColor"],
            "background": bg_name,
            "targetBackground": bg_name,
            "backgroundSrc": bg_name,
            "layoutVariant": "cinematic_doc",
            "narration": sc["sentence"],
            "subtitles": rel_subtitles,
            "words": rel_subtitles,
            "motionDirective": sc["motionDirective"],
            "cameraMovement": "locked",
            "action_type": sc["action_type"],
            "forensicOverlay": sc["forensicOverlay"],
            "hasMarkerHighlight": True,
            "theme": "newsprint-editorial"
        })
        cur_time_sec += sc_dur_sec

    total_frames = sum(s["durationInFrames"] for s in remotion_scenes)

    remotion_props = {
        "episodeId": "JP_EP0003_OPUSCAR_PREVIEW",
        "title": "Japan AI Ransom Economy: Opuscar 4-Beat Upgraded Preview",
        "theme": "newsprint-editorial",
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "totalFrames": total_frames,
        "audioMaster": "tts_out.mp3",
        "bgmFile": "bgm.mp3",
        "bgmVolume": 0.12,
        "includeAudio": True,
        "scenes": remotion_scenes
    }

    props_file = OUT_DIR / "remotion_props.json"
    props_file.write_text(json.dumps(remotion_props, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Generated {props_file} with {len(remotion_scenes)} scenes ({total_frames} frames, {total_frames/fps:.2f}s)")

    # Stage tts_out.mp3 into remotion/public
    pub_tts = remotion_dir / "public" / "tts_out.mp3"
    shutil.copy2(master_mp3, pub_tts)

    # Ensure bgm.mp3 is staged in remotion/public
    pub_bgm = remotion_dir / "public" / "bgm.mp3"
    if not pub_bgm.exists():
        src_bgm = remotion_dir / "public" / "bgm" / "vox_cinematic_pulse.mp3"
        if src_bgm.exists():
            shutil.copy2(src_bgm, pub_bgm)
            logger.info(f"Staged {src_bgm.name} to {pub_bgm}")

    # Stage props file into remotion root
    shutil.copy2(props_file, remotion_dir / "remotion_props.json")

    logger.info("=== STEP 3: Syncing Remotion Components & Assets to VPS ===")
    client = FastVPSClient()

    # 1. Upload background real Omni videos to VPS
    vps_videos_dir = "/root/video_factory/remotion/public/videos"
    client.run_command(f"mkdir -p {vps_videos_dir}")
    for vid_file in staged_videos:
        vps_vid_path = f"{vps_videos_dir}/{vid_file.name}"
        vps_sz = int(client.run_command(f"stat -c %s '{vps_vid_path}' 2>/dev/null || echo 0").get("stdout", "0").strip() or "0")
        if vps_sz != vid_file.stat().st_size:
            upload_file_chunked(client, vid_file, vps_vid_path, chunk_size=150_000)
        else:
            logger.info(f"VPS already has {vid_file.name} ({vps_sz} bytes), skipping re-upload.")

    # 2. Upload tts_out.mp3 to VPS
    vps_tts_path = "/root/video_factory/remotion/public/tts_out.mp3"
    upload_file_chunked(client, master_mp3, vps_tts_path)

    # 3. Upload remotion_props.json to VPS
    logger.info("Uploading remotion_props.json to VPS...")
    vps_props_path = "/root/video_factory/remotion/remotion_props.json"
    upload_file_chunked(client, props_file, vps_props_path)

    # 4. Upload updated Remotion source files to VPS
    vps_remotion_src = "/root/video_factory/remotion/src"
    upload_file_chunked(client, ROOT / "remotion/src/index.tsx", f"{vps_remotion_src}/index.tsx")
    upload_file_chunked(client, ROOT / "remotion/src/components/vox/VoxBuildOnStage.tsx", f"{vps_remotion_src}/components/vox/VoxBuildOnStage.tsx")
    upload_file_chunked(client, ROOT / "remotion/src/components/vox/VoxParallaxLayer.tsx", f"{vps_remotion_src}/components/vox/VoxParallaxLayer.tsx")
    upload_file_chunked(client, ROOT / "remotion/src/components/vox/PaperStatCard.tsx", f"{vps_remotion_src}/components/vox/PaperStatCard.tsx")
    upload_file_chunked(client, ROOT / "remotion/src/components/vox/papercraft/VoxDimensionLine.tsx", f"{vps_remotion_src}/components/vox/papercraft/VoxDimensionLine.tsx")
    upload_file_chunked(client, ROOT / "remotion/src/components/vox/papercraft/index.ts", f"{vps_remotion_src}/components/vox/papercraft/index.ts")

    # 5. Render preview video via Remotion on VPS
    logger.info(f"=== STEP 4: Executing Remotion Render on VPS ({total_frames} frames @ 30fps) ===")
    vps_out_mp4 = "/root/video_factory/out/opuscar_2scenes_preview.mp4"
    client.run_command("mkdir -p /root/video_factory/out")
    client.run_command(f"rm -f {vps_out_mp4}")

    vps_log = "/tmp/remotion_render.log"
    client.run_command(f"rm -f {vps_log}")

    # Launch in background with nohup to avoid Cloudflare 100s proxy timeout (HTTP 524)
    bg_cmd = (
        f"cd /root/video_factory/remotion && "
        f"nohup npx remotion render src/index.tsx VoxBuildOnStage {vps_out_mp4} "
        f"--props=/root/video_factory/remotion/remotion_props.json "
        f"--concurrency=2 --timeout=60000 --log=info --x264-preset=fast --crf=23 > {vps_log} 2>&1 & echo $!"
    )
    logger.info(f"Launching Remotion Render on VPS: {bg_cmd}")
    res = client.run_command(bg_cmd)
    pid = res.get("stdout", "").strip()
    logger.info(f"Remotion render started in background with PID {pid}")

    # Poll until complete
    poll_start = time.time()
    max_poll_seconds = 900
    while time.time() - poll_start < max_poll_seconds:
        time.sleep(6)
        ps_chk = client.run_command(f"ps -p {pid} -o pid=")
        running = bool(ps_chk.get("stdout", "").strip())

        tail_chk = client.run_command(f"tail -n 5 {vps_log}")
        latest = tail_chk.get("stdout", "").strip()
        for line in latest.splitlines()[-2:]:
            logger.info(f"[VPS RENDER] {line}")

        if not running:
            logger.info(f"Remotion render process PID {pid} finished.")
            break
    else:
        logger.warning("Render polling timed out after 900s!")

    # Check VPS rendered MP4
    chk_res = client.run_command(f"ls -lh {vps_out_mp4}")
    logger.info(f"VPS Output Check: {chk_res.get('stdout')}")
    if not chk_res.get("stdout") or "No such file" in chk_res.get("stdout", ""):
        err_log = client.run_command(f"cat {vps_log}")
        logger.error(f"Render failed! Full log:\n{err_log.get('stdout')}")
        raise RuntimeError("Remotion render failed on VPS: output MP4 not found.")

    # Download rendered video from VPS
    logger.info("=== STEP 5: Downloading Preview MP4 to Local Workspace ===")
    local_final_mp4 = OUT_DIR / "opuscar_2scenes_preview.mp4"
    download_file_parallel(client, vps_out_mp4, local_final_mp4, max_workers=6)

    # Verify stream probe locally
    probe_dur = probe_audio_duration(local_final_mp4)
    logger.info(f"Local Final Video Verified: Duration={probe_dur:.2f}s, Size={local_final_mp4.stat().st_size} bytes")

    # Extract forensic probe frames for inspection
    logger.info("=== STEP 6: Extracting Forensic Probe Frames ===")
    probe_timestamps = [1.0, 3.0, 5.0, 8.0, 11.0, 14.0]
    for sec in probe_timestamps:
        frame_out = OUT_DIR / f"probe_{int(sec):02d}s.jpg"
        subprocess.run([
            ffmpeg_bin, "-y", "-ss", str(sec), "-i", str(local_final_mp4),
            "-vframes", "1", "-q:v", "2", str(frame_out)
        ], check=True, capture_output=True)
        try:
            sz_f = frame_out.stat().st_size
        except OSError as stat_err:
            logger.warning(f"Failed to read size for {frame_out}: {stat_err}")
            sz_f = 0
        logger.info(f"Extracted probe frame at {sec}s -> {frame_out} ({sz_f} bytes)")

    print(f"\nSUCCESS: Preview video rendered and ready at:\n{local_final_mp4.resolve()}\n")


if __name__ == "__main__":
    main()
