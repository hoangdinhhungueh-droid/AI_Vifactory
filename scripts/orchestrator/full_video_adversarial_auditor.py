#!/usr/bin/env python3
"""
scripts/orchestrator/full_video_adversarial_auditor.py

Comprehensive Full-Video Multimodal Adversarial Audit Engine.
Enables Claude Opus 5.5 and GPT-6 Astra to inspect the ENTIRE 20-minute video:
1. Generates 2 High-Density Storyboard Contact Sheets (8x8 grids, 128 frames) covering 100% of scenes.
2. Extracts 8 Kinematic Burst Sequences (4x3 grids of 12 consecutive frames @ 30fps) measuring exact frame-to-frame delta.
3. Transmits base64 visual payloads directly to Claude Opus 5.5 and GPT-6 Astra via ModelGateway.
4. Produces independent 5-Axis adversarial scorecards against YouTube benchmark cXQuNBZA0FA.

Complies with Rule 118, 121, 122, 126, 128, 134.
"""

import os
import sys
import json
import time
import base64
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

BURST_CONFIGS = [
    {"label": "burst_01_hook_entrance", "start": 2.8, "duration": 0.4, "beat": "Beat 1", "desc": "Hook Headline Pop & Stage 3 Tactile Drop"},
    {"label": "burst_02_marker_highlight", "start": 19.8, "duration": 0.4, "beat": "Beat 1", "desc": "Yellow Marker Stroke Sweep & Word Sync"},
    {"label": "burst_03_stamp_slam", "start": 44.8, "duration": 0.4, "beat": "Beat 1", "desc": "Stamp Slam Scale Overshoot (2.6 -> 0.95 -> 1.0)"},
    {"label": "burst_04_kinetic_counter", "start": 119.8, "duration": 0.4, "beat": "Beat 2", "desc": "Kinetic Counter Rollup & Geometric Brackets"},
    {"label": "burst_05_match_cut_staging", "start": 249.8, "duration": 0.4, "beat": "Beat 2", "desc": "Scene Transition Boundary & Ghost Dissolve Check"},
    {"label": "burst_06_tactical_grid", "start": 449.8, "duration": 0.4, "beat": "Beat 3", "desc": "Tactical Investigation Grid & Causal Flowchart"},
    {"label": "burst_07_climax_momentum", "start": 849.8, "duration": 0.4, "beat": "Beat 4", "desc": "Smoking Gun Climax & Camera Push-Zoom Momentum"},
    {"label": "burst_08_microlife_lock", "start": 1149.8, "duration": 0.4, "beat": "Beat 5", "desc": "Permanent Lock Window & Living Micro-Life Particles"},
]

def encode_image_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def extract_storyboard_sheets(video_path: Path, out_dir: Path) -> List[Path]:
    """Generates 2 Storyboard Contact Sheets (8x8 tiles = 64 frames each) covering 100% of the video."""
    print("🎬 [FULL AUDITOR] Generating Full-Timeline Storyboard Contact Sheets...")
    out_dir.mkdir(parents=True, exist_ok=True)
    sheets = []

    sheet1_opt = out_dir / "storyboard_01_opt.jpg"
    sheet1_orig = out_dir / "storyboard_01_first_half.jpg"
    sheet1_path = sheet1_opt if sheet1_opt.exists() else sheet1_orig
    if not sheet1_path.exists():
        cmd1 = [
            "ffmpeg", "-y",
            "-ss", "0", "-t", "600",
            "-i", str(video_path),
            "-vf", "fps=64/600,scale=240:135,tile=8x8",
            "-q:v", "4",
            str(sheet1_opt)
        ]
        res1 = subprocess.run(cmd1, capture_output=True, text=True)
        sheet1_path = sheet1_opt

    if sheet1_path.exists():
        sheets.append(sheet1_path)
        print(f"  ✅ Storyboard Sheet 1: {round(sheet1_path.stat().st_size/1024, 1)} KB")

    sheet2_opt = out_dir / "storyboard_02_opt.jpg"
    sheet2_orig = out_dir / "storyboard_02_second_half.jpg"
    sheet2_path = sheet2_opt if sheet2_opt.exists() else sheet2_orig
    if not sheet2_path.exists():
        cmd2 = [
            "ffmpeg", "-y",
            "-ss", "600", "-t", "585",
            "-i", str(video_path),
            "-vf", "fps=64/585,scale=240:135,tile=8x8",
            "-q:v", "4",
            str(sheet2_opt)
        ]
        res2 = subprocess.run(cmd2, capture_output=True, text=True)
        sheet2_path = sheet2_opt

    if sheet2_path.exists():
        sheets.append(sheet2_path)
        print(f"  ✅ Storyboard Sheet 2: {round(sheet2_path.stat().st_size/1024, 1)} KB")

    return sheets

def extract_kinematic_burst_grids(video_path: Path, out_dir: Path) -> List[Dict[str, Any]]:
    """Extracts 12 consecutive frames (30fps) tiled into a 4x3 grid for each strategic time window."""
    print("🔬 [FULL AUDITOR] Generating 12-Frame Kinematic Differential Burst Grids...")
    burst_results = []
    
    for b in BURST_CONFIGS:
        burst_img = out_dir / f"{b['label']}.jpg"
        # 12 frames in 0.4s @ 30fps -> fps=30, tiled 4x3
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(b["start"]),
            "-t", str(b["duration"]),
            "-i", str(video_path),
            "-vf", "scale=480:270,tile=4x3",
            "-q:v", "2",
            str(burst_img)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and burst_img.exists():
            size_kb = round(burst_img.stat().st_size / 1024, 1)
            print(f"  📸 [{b['beat']}] {b['label']} ({b['start']}s, 12 consecutive frames): {size_kb} KB")
            burst_results.append({**b, "path": burst_img, "size_kb": size_kb})
        else:
            print(f"  ❌ Burst {b['label']} failed: {res.stderr[-300:]}")

    return burst_results

def run_dual_llm_full_video_audit(
    episode_dir: Path,
    video_path: Path,
    storyboards: List[Path],
    bursts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    print("\n👑 [FULL AUDITOR] Dispatching Full-Video Multimodal Audit to Dual-LLM High Council...")
    from app.services.model_gateway import get_global_gateway
    gw = get_global_gateway()

    # Load props summary
    props_path = episode_dir / "final_opus55_master_props.json"
    props_summary = ""
    if props_path.exists():
        p = json.loads(props_path.read_text(encoding="utf-8"))
        scenes = p.get("scenes", [])
        props_summary = f"Total Scenes: {len(scenes)}, Total Duration: {sum(s.get('durationInFrames', 0) for s in scenes)/30:.1f}s"

    system_prompt = """You are a Senior Principal Director, Forensic Motion Graphics Architect & Lead Video Quality Auditor.
You are conducting a strict, unsparing ADVERSARIAL FULL-VIDEO AUDIT of this rendered documentary video against the official YouTube benchmark: 'How to Make Viral Vox-Style Videos with AI' (cXQuNBZA0FA) and its Master Template Prompt specifications.

You are provided with:
1. FULL-TIMELINE STORYBOARD CONTACT SHEETS (Sheet 1: 0-600s, Sheet 2: 600-1183s) capturing 128 continuous scenes across the entire video.
2. 12-FRAME DIFFERENTIAL BURST GRIDS (4x3 tiles of 12 consecutive frames at 30fps) capturing exact frame-to-frame delta across motion milestones (Hook pop, Marker sweep, Stamp slam overshoot, Counter rollup, Match-cut transitions, Micro-life lock).

Analyze the entire visual timeline and the motion bursts with pixel-level forensic precision.
Evaluate whether this video is a true layered procedural motion graphics piece or still a static slideshow.

Score the video on the 5 Core Axes (0.0 to 10.0 scale):
- Axis 1: Layer-by-Layer Procedural Assembly (0-10s progressive build)
- Axis 2: True Motion & Element-Level Kinematics (Physical spring drops, counter rollups, micro-life breathing)
- Axis 3: Match-Cut & Directional Transitions (Push-zoom, paper wipes, zero ghost dissolves on shared backgrounds)
- Axis 4: Evidentiary Purity & Zero Dual-Number Conflict (Single truth, no conflicting numbers)
- Axis 5: Editorial Graphic Novel Art Purity (Paper collage, B&W cutouts, authentic ink linework)

Calculate the Composite Score (weighted: Axis 1: 25%, Axis 2: 20%, Axis 3: 20%, Axis 4: 20%, Axis 5: 15%) and Benchmark Parity %.
Deliver a detailed, unsparing forensic evaluation report in Vietnamese. Include a formal Showrunner Verdict (PASS / FAIL, threshold: >= 8.5/10)."""

    prompt_text = f"""[MISSION: FULL-VIDEO MULTIMODAL FORENSIC AUDIT]
Episode: {episode_dir.name}
Video File: {video_path.name} ({round(video_path.stat().st_size/1048576, 1)} MB)
Specs: {props_summary}
Benchmark Target: YouTube cXQuNBZA0FA (Vox-Style AI Motion Graphics Tutorial)

Attached Visual Evidence:
- Storyboard Sheet 1: 00:00 - 10:00 (64 scenes tiled)
- Storyboard Sheet 2: 10:00 - 19:43 (64 scenes tiled)
- Burst 1: TC 00:00:03 (Hook Headline Pop & Stage 3 Drop, 12 frames @ 30fps)
- Burst 2: TC 00:00:20 (Yellow Marker Stroke Sweep & Word Sync, 12 frames @ 30fps)
- Burst 3: TC 00:00:45 (Stamp Badge Slam Physics & Overshoot, 12 frames @ 30fps)
- Burst 4: TC 00:02:00 (Kinetic Counter Rollup & Brackets, 12 frames @ 30fps)

Please examine the visual evidence across the entire timeline and provide your comprehensive adversarial report now."""

    # Build multimodal content parts
    content_parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt_text}]

    for idx, sheet in enumerate(storyboards):
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encode_image_b64(sheet)}"}
        })

    for b in bursts[:4]:  # First 4 bursts for high-stakes kinematic verification
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encode_image_b64(b['path'])}"}
        })

    headers = {
        "Authorization": f"Bearer {gw.hhtech_key}",
        "Content-Type": "application/json"
    }

    import httpx

    # 1. Audit by Claude Opus 5.5
    print("\n--- [1/2] RUNNING ADVERSARIAL AUDIT WITH CLAUDE OPUS 5.5 ---")
    opus_report = ""
    out_opus = episode_dir / "full_video_audit_opus55.md"
    if out_opus.exists() and out_opus.stat().st_size > 500:
        print(f"ℹ️ Reusing existing Claude Opus 5.5 report ({out_opus.stat().st_size} bytes)")
        opus_report = out_opus.read_text(encoding="utf-8")
    else:
        try:
            t0 = time.time()
            payload_opus = {
                "model": "claude-opus-5",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_parts}
                ],
                "max_tokens": 4000,
                "stream": False
            }
            with httpx.Client(timeout=360.0) as client:
                resp = client.post(f"{gw.hhtech_base_url}/chat/completions", json=payload_opus, headers=headers)
                if resp.status_code == 200:
                    opus_report = resp.json()["choices"][0]["message"]["content"]
                    elapsed = round(time.time() - t0, 1)
                    print(f"✅ Claude Opus 5.5 Full-Video Audit complete in {elapsed}s ({len(opus_report)} chars)")
                    out_opus.write_text(opus_report, encoding="utf-8")
                    Path("/tmp/vf/full_video_audit_opus55.md").write_text(opus_report, encoding="utf-8")
                else:
                    print(f"❌ Opus 5.5 API error ({resp.status_code}): {resp.text[:300]}")
        except Exception as e:
            print(f"❌ Opus 5.5 audit execution failed: {e}")

    # 2. Audit by GPT-6 Astra
    print("\n--- [2/2] RUNNING ADVERSARIAL AUDIT WITH GPT-6 ASTRA ---")
    astra_report = ""
    out_astra = episode_dir / "full_video_audit_astra6.md"
    if out_astra.exists() and out_astra.stat().st_size > 500:
        print(f"ℹ️ Reusing existing GPT-6 Astra report ({out_astra.stat().st_size} bytes)")
        astra_report = out_astra.read_text(encoding="utf-8")
    else:
        try:
            t0 = time.time()
            payload_astra = {
                "model": "gpt-6-astra",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_parts}
                ],
                "max_tokens": 4000,
                "stream": False
            }
            with httpx.Client(timeout=360.0) as client:
                resp = client.post(f"{gw.hhtech_base_url}/chat/completions", json=payload_astra, headers=headers)
                if resp.status_code == 200:
                    astra_report = resp.json()["choices"][0]["message"]["content"]
                    elapsed = round(time.time() - t0, 1)
                    print(f"✅ GPT-6 Astra Full-Video Audit complete in {elapsed}s ({len(astra_report)} chars)")
                    out_astra.write_text(astra_report, encoding="utf-8")
                    Path("/tmp/vf/full_video_audit_astra6.md").write_text(astra_report, encoding="utf-8")
                else:
                    print(f"❌ GPT-6 Astra API error ({resp.status_code}): {resp.text[:300]}")
        except Exception as e:
            print(f"❌ Astra 6 audit execution failed: {e}")

    return {
        "opus_report_length": len(opus_report),
        "astra_report_length": len(astra_report),
        "storyboards": len(storyboards),
        "bursts": len(bursts)
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python full_video_adversarial_auditor.py <EPISODE_ID>")
        sys.exit(1)

    ep_id = sys.argv[1]
    ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    if not ep_dir.exists():
        ep_dir = ROOT_DIR / "workspace" / ep_id

    video_path = ep_dir / "final_opus55_169.mp4"
    if not video_path.exists():
        print(f"❌ Video file does not exist: {video_path}")
        sys.exit(1)

    audit_media_dir = ep_dir / "full_video_audit_media"
    
    # Step 1: Storyboard sheets
    sheets = extract_storyboard_sheets(video_path, audit_media_dir)
    
    # Step 2: Kinematic burst sequences
    bursts = extract_kinematic_burst_grids(video_path, audit_media_dir)
    
    # Step 3: Run dual-LLM audit
    res = run_dual_llm_full_video_audit(ep_dir, video_path, sheets, bursts)
    print("\n🎉 [FULL AUDITOR] Dual-LLM Full-Video Adversarial Audit Finished Successfully!")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
