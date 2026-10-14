#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vox/pipeline.py — Master Unified Single Pipeline Orchestrator (AVF-VOX-001).

Single CLI entrypoint for Vox Tactile Explainer video generation.
Orchestrates:
1. Scene Decomposition & Planning (planner.py)
2. Voice Narration TTS (tts.py)
3. Whisper Word Alignment (align.py)
4. ASS Subtitle Generation (karaoke.py)
5. Background Canvas Generation & Gate Verification (assets_bg.py)
6. Foreground Cutout Generation & Gate Verification (assets_fg.py & cutout.py)
7. Parallax Scene Compositing (compositor.py)
8. Master Concatenation, Subtitle Burn-In & Loudnorm (assemble.py)
9. Final Quantitative Forensic Quality Audit (qa/gates.py)
10. Atomic Manifest Serialization (manifest.json)
"""

from __future__ import annotations

import sys
import os
import json
import time
import argparse
import hashlib
from pathlib import Path
from typing import Dict, Any, List

from vox.schemas import ScenePlan
from vox.planner import plan_scenes_from_script
from vox.tts import synthesize_narration
from vox.align import align_script_with_audio
from vox.karaoke import generate_ass_subtitles
from vox.assets_bg import generate_background_canvas
from vox.assets_fg import generate_fg_cutout
from vox.compositor import render_scene_clip
from vox.assemble import assemble_final_video
from vox.qa.gates import verify_final_video_gates


def compute_file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_pipeline(
    script_path: Path,
    out_dir: Path,
    title: str = "Vox Explainer Video",
) -> Dict[str, Any]:
    """Runs the complete 1-pipeline Vox video generation flow."""
    start_ts = time.time()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🎬 VOX-STYLE TACTILE EXPLAINER — SINGLE UNIFIED PIPELINE")
    print(f"📄 Script Source:   {script_path}")
    print(f"📁 Output Directory: {out_dir}")
    print("=" * 70)

    script_text = Path(script_path).read_text(encoding="utf-8").strip()

    # 1. Planning
    print("\n[1/7] Decomposing script into ScenePlan...")
    plan = plan_scenes_from_script(script_text, title=title)
    print(f"      Plan generated: {len(plan.scenes)} scenes.")

    # 2. TTS Voiceover
    print("\n[2/7] Synthesizing 48kHz mono narration audio...")
    audio_wav = out_dir / "narration.wav"
    synthesize_narration(plan, audio_wav)
    print(f"      Audio generated: {audio_wav} (SHA: {compute_file_sha256(audio_wav)[:12]})")

    # 3. Whisper Alignment
    print("\n[3/7] Aligning Whisper word timestamps with script text...")
    timeline, plan = align_script_with_audio(plan, audio_wav)
    print(f"      Aligned {len(timeline.words)} words. Match ratio: {timeline.match_ratio*100:.1f}%. Duration: {timeline.audio_duration:.2f}s.")

    # 4. ASS Karaoke Subtitles
    print("\n[4/7] Generating ASS word-level karaoke subtitles...")
    ass_file = out_dir / "subtitles.ass"
    generate_ass_subtitles(timeline, ass_file)
    print(f"      Subtitles generated: {ass_file}")

    # 5. Assets & Scene Clips Rendering
    print("\n[5/7] Generating BG/FG assets & compositing scene clips...")
    assets_dir = out_dir / "assets"
    clips_dir = out_dir / "clips"
    assets_dir.mkdir(exist_ok=True)
    clips_dir.mkdir(exist_ok=True)

    scene_clips: List[Path] = []
    manifest_assets: Dict[str, Any] = {"backgrounds": [], "foregrounds": []}

    for sc in plan.scenes:
        print(f"      Rendering Scene {sc.idx}/{len(plan.scenes)} (Camera: {sc.camera.value}, Time: {sc.start:.2f}s - {sc.end:.2f}s)...")
        # Generate Background
        bg_path, bg_meta = generate_background_canvas(sc.bg_prompt, sc.idx, assets_dir)
        manifest_assets["backgrounds"].append(bg_meta)

        # Generate Foregrounds
        fg_map: Dict[str, Path] = {}
        for fg_obj in sc.fg:
            fg_path, fg_meta = generate_fg_cutout(fg_obj, sc.idx, assets_dir)
            fg_map[fg_obj.id] = fg_path
            manifest_assets["foregrounds"].append(fg_meta)

        # Composite clip
        clip_path = clips_dir / f"clip_{sc.idx:02d}.mp4"
        render_scene_clip(sc, bg_path, fg_map, clip_path)
        scene_clips.append(clip_path)

    # 6. Assembly & Subtitle Burn-In
    print("\n[6/7] Assembling master video, burning subtitles & applying loudnorm...")
    final_video = out_dir / "final.mp4"
    assemble_final_video(scene_clips, audio_wav, ass_file, final_video)
    print(f"      Final video generated: {final_video}")

    # Calculate word-level anchors for each scene and reverse karaoke drift
    from vox.karaoke import parse_words_from_ass
    reconstructed_words = parse_words_from_ass(ass_file)
    max_drift_ms = 0.0
    for orig, rec in zip(timeline.words, reconstructed_words):
        d_start = abs(orig.start - rec["start"]) * 1000.0
        if d_start > max_drift_ms:
            max_drift_ms = d_start

    enriched_scenes = []
    max_boundary_drift_frames = 0.0
    for sc in plan.scenes:
        sc_dict = sc.model_dump()
        sc_words = [w for w in timeline.words if w.scene_idx == sc.idx]
        if sc_words:
            first_idx = timeline.words.index(sc_words[0])
            last_idx = timeline.words.index(sc_words[-1])
            drift_frames = round(abs(sc.end - sc_words[-1].end) * 30.0, 2)
            if drift_frames > max_boundary_drift_frames:
                max_boundary_drift_frames = drift_frames
            sc_dict["word_anchor"] = {
                "first_word_idx": first_idx,
                "first_word": sc_words[0].text,
                "last_word_idx": last_idx,
                "last_word": sc_words[-1].text,
                "whisper_start": sc_words[0].start,
                "whisper_end": sc_words[-1].end,
                "boundary_delta_frames": drift_frames,
            }
        else:
            sc_dict["word_anchor"] = None
        enriched_scenes.append(sc_dict)

    # 7. Quality Gates Audit
    print("\n[7/7] Executing quantitative forensic quality gates audit...")
    gate_results = verify_final_video_gates(final_video, timeline.audio_duration, plan)
    print(f"      Gate Audit Result: {gate_results['status']} (Streams: 2, Codec: {gate_results['video_codec']}+{gate_results['audio_codec']})")

    # Serialize Atomic Manifest
    total_time = round(time.time() - start_ts, 2)
    manifest = {
        "pipeline": "vox_tactile_explainer_v1",
        "title": title,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_latency_sec": total_time,
        "script_source": str(script_path),
        "final_video": {
            "path": str(final_video),
            "sha256": compute_file_sha256(final_video),
            "size_bytes": final_video.stat().st_size,
        },
        "audio": {
            "path": str(audio_wav),
            "duration_sec": timeline.audio_duration,
            "sha256": compute_file_sha256(audio_wav),
        },
        "subtitles": {
            "path": str(ass_file),
            "total_words": len(timeline.words),
            "match_ratio": timeline.match_ratio,
            "max_reverse_drift_ms": round(max_drift_ms, 2),
            "reverse_parity_status": "PASS" if max_drift_ms <= 33.3 else "FAIL",
        },
        "scene_count": len(plan.scenes),
        "scenes": enriched_scenes,
        "assets": manifest_assets,
        "qa_gates": gate_results,
    }

    manifest_file = out_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"🏆 PIPELINE COMPLETED SUCCESSFULLY IN {total_time}s!")
    print(f"📄 Atomic Manifest: {manifest_file}")
    print(f"🎥 Final Video:     {final_video}")
    print("=" * 70 + "\n")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Vox Tactile Explainer Single Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run full pipeline from script")
    run_parser.add_argument("--script", required=True, help="Path to narration script text file")
    run_parser.add_argument("--out", required=True, help="Output directory")
    run_parser.add_argument("--title", default="Vox Explainer Episode", help="Episode title")

    args = parser.parse_args()

    if args.command == "run":
        try:
            run_pipeline(Path(args.script), Path(args.out), title=args.title)
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
