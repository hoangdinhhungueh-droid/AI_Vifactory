#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/visual_critic_council.py
Multimodal Visual Critic Council for AI Video Factory (Skill: /vf-visual-critic).
Unites User, Antigravity Native Vision, Claude Opus 5.5, and GPT-6-Astra.
Inspects a 30-second Pilot sample via a 16-frame contact sheet.
"""

import os
import sys
import json
import base64
import argparse
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.model_gateway import get_global_gateway

VOX_RUBRIC_PROMPT = """You are a world-class documentary film director and visual effects supervisor evaluating a 30-second video pilot.
The reference benchmark standard is the tactile paper-collage Vox documentary style shown in YouTube tutorial 'https://www.youtube.com/watch?v=RaxX_Q7Apj0' (from 0:51).

You are given a 16-Frame Contact Sheet (4x4 grid) sampled chronologically across the 30-second pilot clip.

Carefully evaluate the visual output across 4 Canonical Axes (Score each 0.0 to 10.0):

1. **Cinematic Motion & Physics Realism (30% weight)**:
   - Is there genuine spatial depth, dynamic camera movement (dolly, push-in, tracking), and fluid physics?
   - Or does it look like a flat, static, robotic 2D PowerPoint slideshow with cheap CSS transforms?
   - Target: Organic living motion, realistic lighting, believable stop-motion jitter.

2. **Tactile Paper Aesthetics (Vox 0:51 Standard) (25% weight)**:
   - Does it have authentic papercraft textures: aged yellowed newsprint, torn rough edges, high-contrast halftone B&W cutouts?
   - Are tactile props convincing: washi tape, brass pushpins, red rubber verification stamps, red investigation yarn?

3. **Editing Pacing & Sound-Visual Synergy (25% weight)**:
   - Is the visual cadence energetic yet readable? Does every cut serve narrative tension?
   - Are visual punches timed to speech pauses and emphasis?

4. **Vox Typography & Data Clarity (20% weight)**:
   - Are subtitles, dates, and financial metrics crisp, readable, and properly aligned?
   - Is there any asset leakage (raw file hashes, .png extensions, clipping, or unrendered artifacts)?

Respond with a strictly valid JSON object matching this schema:
{
  "evaluator": "<YOUR_MODEL_NAME>",
  "axis_scores": {
    "cinematic_motion_physics": <float 0-10>,
    "tactile_paper_aesthetics": <float 0-10>,
    "editing_pacing": <float 0-10>,
    "typography_data_clarity": <float 0-10>
  },
  "overall_score": <float 0-10>,
  "verdict": "<PASS or FAIL>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "critical_flaws": ["<flaw 1>", "<flaw 2>"],
  "actionable_patch_instructions": "<Concrete instructions to fix any flaws in the next pilot pass>"
}
"""

def extract_frames_and_build_contact_sheet(video_path: Path, out_dir: Path, num_frames=16, duration_sec=30.0) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "extracted_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    interval = duration_sec / (num_frames + 1)
    frame_paths = []
    
    for i in range(1, num_frames + 1):
        timestamp = round(i * interval, 2)
        frame_file = frames_dir / f"frame_{i:02d}_{timestamp:.1f}s.jpg"
        cmd = [
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video_path),
            "-vframes", "1", "-q:v", "2", str(frame_file)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if frame_file.exists() and frame_file.stat().st_size > 1000:
                frame_paths.append((frame_file, timestamp))
        except Exception as e:
            print(f"Warning extracting frame at {timestamp}s: {e}", file=sys.stderr)
            
    if not frame_paths:
        raise RuntimeError("No frames could be extracted from video.")
        
    # Stitch into 4x4 Grid
    grid_cols = 4
    grid_rows = 4
    cell_w = 480
    cell_h = 270
    contact_sheet = Image.new("RGB", (grid_cols * cell_w, grid_rows * cell_h), color=(15, 23, 42))
    draw = ImageDraw.Draw(contact_sheet)
    
    for idx, (fpath, t_sec) in enumerate(frame_paths[:16]):
        r = idx // grid_cols
        c = idx % grid_cols
        x = c * cell_w
        y = r * cell_h
        
        try:
            with Image.open(fpath) as img:
                img_resized = img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                contact_sheet.paste(img_resized, (x, y))
                
            # Draw timestamp badge
            label = f"{t_sec:.1f}s (F{idx+1})"
            draw.rectangle([x + 6, y + 6, x + 90, y + 26], fill=(0, 0, 0, 180))
            draw.text((x + 10, y + 8), label, fill=(255, 255, 255))
        except Exception as e:
            print(f"Error pasting frame {idx}: {e}", file=sys.stderr)
            
    contact_sheet_path = out_dir / "contact_sheet_30s.jpg"
    contact_sheet.save(contact_sheet_path, quality=90)
    print(f"📸 Contact Sheet 4x4 created at: {contact_sheet_path}")
    return contact_sheet_path

def evaluate_with_council(contact_sheet_path: Path, episode_id: str) -> dict:
    gateway = get_global_gateway()
    
    # Read image base64
    with open(contact_sheet_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    prompt = f"Episode ID: {episode_id}\n\n{VOX_RUBRIC_PROMPT}"
    
    print("🧠 [Hội Đồng Thị Giác] Đang chất vấn Claude Opus 5.5...")
    opus_resp = gateway.call_vision(
        prompt=prompt,
        image_base64=img_b64,
        model="claude-opus-5-5",
        system_prompt="You are Senior Film Director Claude Opus 5.5 conducting visual audit of video pilot.",
        fallback="claude-sonnet-5-5"
    )
    
    print("🧠 [Hội Đồng Thị Giác] Đang chất vấn GPT-6-Astra...")
    astra_resp = gateway.call_vision(
        prompt=prompt,
        image_base64=img_b64,
        model="gpt-6-astra",
        system_prompt="You are Cinematography & Physics Supervisor GPT-6-Astra conducting visual audit of video pilot.",
        fallback="gpt-6.1-sol"
    )
    
    # Parse responses
    def parse_json(raw: str):
        try:
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(cleaned)
        except Exception:
            return {"raw": raw, "overall_score": 5.0, "verdict": "FAIL", "critical_flaws": ["Unparseable JSON"]}
            
    opus_json = parse_json(opus_resp)
    astra_json = parse_json(astra_resp)
    
    opus_score = float(opus_json.get("overall_score", 0.0))
    astra_score = float(astra_json.get("overall_score", 0.0))
    avg_score = round((opus_score + astra_score) / 2.0, 2)
    
    council_pass = (opus_score >= 8.5 and astra_score >= 8.5)
    
    report = {
        "episode_id": episode_id,
        "council_status": "APPROVED" if council_pass else "REVISION_REQUIRED",
        "average_score": avg_score,
        "opus_5_5": opus_json,
        "astra_6": astra_json,
        "requires_human_sign_off": True,
        "contact_sheet": str(contact_sheet_path)
    }
    
    return report

def main():
    parser = argparse.ArgumentParser(description="Multimodal Visual Critic Council Runner")
    parser.add_argument("--episode", required=True, help="Episode ID")
    parser.add_argument("--video", required=True, help="Path to pilot video (mp4)")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration in seconds")
    parser.add_argument("--out-dir", default=None, help="Output directory")
    args = parser.parse_args()
    
    vid_path = Path(args.video)
    if not vid_path.exists():
        print(f"Error: Video file not found: {vid_path}", file=sys.stderr)
        sys.exit(1)
        
    out_dir = Path(args.out_dir) if args.out_dir else vid_path.parent / "visual_audit"
    cs_path = extract_frames_and_build_contact_sheet(vid_path, out_dir, num_frames=16, duration_sec=args.duration)
    
    verdict = evaluate_with_council(cs_path, args.episode)
    
    report_file = out_dir / "visual_critic_council_verdict.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2, ensure_ascii=False)
        
    print("\n" + "="*70)
    print(f"🏛️ KẾT QUẢ HỘI ĐỒNG THỊ GIÁC: {verdict['council_status']} (Điểm TB: {verdict['average_score']}/10)")
    print(f"   • Claude Opus 5.5: {verdict['opus_5_5'].get('overall_score')}/10 ({verdict['opus_5_5'].get('verdict')})")
    print(f"   • GPT-6-Astra:     {verdict['astra_6'].get('overall_score')}/10 ({verdict['astra_6'].get('verdict')})")
    print(f"📁 Báo cáo chi tiết: {report_file}")
    print("="*70)

if __name__ == "__main__":
    main()
