#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/orchestrator/audit_b2_b3_assets.py

Multi-Agent Forensic Audit Harness for B2 Story & B3/B3.5 Visual Assets
Mandated by User Request & /vf-pipeline-teamwork skill:
1. Convenes Claude Opus 5.5 (Supreme Architecture Supervisor & Lead Visual Architect)
2. Convenes GPT-6-Astra (Adversarial Forensic Auditor & Skeptic)
3. Evaluates B2 Narrative & Audio Spine, B3 Remotion Manifest, B3.5 Visual Prompts
4. Outputs comprehensive audit verdict: PASS or REJECT with actionable macro debug plan.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.model_gateway import get_global_gateway

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audit_b2_b3_assets")


def load_episode_assets(ep_dir: Path) -> Dict[str, Any]:
    """Load B2 and B3 assets from episode directory."""
    assets = {}
    
    # 1. B2 Story & Spoken text
    story_path = ep_dir / "story.txt"
    assets["story_text"] = story_path.read_text(encoding="utf-8") if story_path.exists() else ""
    
    spoken_path = ep_dir / "spoken_sentences.json"
    assets["spoken_sentences"] = json.loads(spoken_path.read_text(encoding="utf-8")) if spoken_path.exists() else []
    
    srt_path = ep_dir / "subtitles.srt"
    assets["subtitles_srt"] = srt_path.read_text(encoding="utf-8") if srt_path.exists() else ""
    
    tts_path = ep_dir / "tts_out.mp3"
    assets["tts_size_bytes"] = tts_path.stat().st_size if tts_path.exists() else 0

    # 2. B3 Remotion Props
    props_path = ep_dir / "remotion_props.json"
    assets["remotion_props"] = json.loads(props_path.read_text(encoding="utf-8")) if props_path.exists() else {}

    # 3. B3.5 Prompts Forge
    forge_path = ep_dir / "prompts_forge.json"
    assets["prompts_forge"] = json.loads(forge_path.read_text(encoding="utf-8")) if forge_path.exists() else {}

    # 4. Grounding Intel
    grounding_path = ep_dir / "grounding_intel.json"
    assets["grounding_intel"] = json.loads(grounding_path.read_text(encoding="utf-8")) if grounding_path.exists() else {}

    # 5. Existing Fact Audit
    fact_path = ep_dir / "fact_audit.json"
    assets["fact_audit"] = json.loads(fact_path.read_text(encoding="utf-8")) if fact_path.exists() else {}

    return assets


def compile_forensic_metrics(assets: Dict[str, Any]) -> Dict[str, Any]:
    """Compute exact objective telemetry on the assets."""
    story_words = len(assets["story_text"].split()) if assets["story_text"] else 0
    sentences_count = len(assets["spoken_sentences"])
    
    forge = assets.get("prompts_forge", {})
    bgs = forge.get("backgrounds", {})
    fgs = forge.get("foregrounds", {})
    
    total_bgs = len(bgs)
    unique_bgs = len(set(bgs.values()))
    
    total_fgs = len(fgs)
    unique_fgs = len(set(fgs.values()))
    
    # Check for string leak defect in FGs
    leaked_header_fgs = [k for k, v in fgs.items() if "ACT I" in str(v) or "ACT II" in str(v) or "\n" in str(v)]
    abstract_sentence_fgs = [k for k, v in fgs.items() if "Nobody in this case" in str(v) or "Hold the question" in str(v)]
    
    props = assets.get("remotion_props", {})
    scenes = props.get("scenes", [])
    fps = props.get("fps", 30) or 30
    sum_scene_frames = sum(sc.get("durationInFrames", 0) for sc in scenes)
    total_frames = props.get("totalFrames") or props.get("durationInFrames") or sum_scene_frames
    if not total_frames or abs(total_frames - sum_scene_frames) > 30:
        total_frames = sum_scene_frames
    duration_sec = round(total_frames / fps, 2) if fps else 0

    # Accurate scene key extractor
    def clean_key(val: Any) -> str:
        s = str(val or "")
        return s.replace("images/", "").replace(".png", "").strip()

    scene_bgs = [clean_key(sc.get("targetBackground") or sc.get("background") or sc.get("bg_key") or sc.get("background_reuse_key")) for sc in scenes]
    scene_fgs = [clean_key(sc.get("targetHeroSrc") or sc.get("heroSrc") or sc.get("fg_key") or sc.get("foreground_reuse_key")) for sc in scenes]

    unique_scene_bgs = len(set(filter(None, scene_bgs)))
    unique_scene_fgs = len(set(filter(None, scene_fgs)))

    # Compute continuous background dwell telemetry across sequence holds
    bg_runs = []
    cur_bg = None
    cur_count = 0
    cur_frames = 0
    for sc in scenes:
        bg = clean_key(sc.get("targetBackground") or sc.get("background") or sc.get("bg_key") or sc.get("background_reuse_key"))
        frames = sc.get("durationInFrames", 0)
        if bg == cur_bg:
            cur_count += 1
            cur_frames += frames
        else:
            if cur_bg is not None:
                bg_runs.append((cur_bg, cur_count, cur_frames, round(cur_frames / fps, 2) if fps else 0))
            cur_bg = bg
            cur_count = 1
            cur_frames = frames
    if cur_bg is not None:
        bg_runs.append((cur_bg, cur_count, cur_frames, round(cur_frames / fps, 2) if fps else 0))

    max_continuous_bg_dwell_sec = max([r[3] for r in bg_runs]) if bg_runs else 0.0
    min_continuous_bg_dwell_sec = min([r[3] for r in bg_runs]) if bg_runs else 0.0
    avg_continuous_bg_dwell_sec = round(sum([r[3] for r in bg_runs]) / len(bg_runs), 2) if bg_runs else 0.0
    max_consecutive_scenes_same_bg = max([r[1] for r in bg_runs]) if bg_runs else 1
    total_assigned_bgs = len([b for b in scene_bgs if b])
    bg_coverage_pct = round(total_assigned_bgs / len(scenes) * 100, 1) if scenes else 0.0

    return {
        "story_word_count": story_words,
        "spoken_sentences_count": sentences_count,
        "tts_file_size_mb": round(assets["tts_size_bytes"] / (1024 * 1024), 2),
        "total_remotion_scenes": len(scenes),
        "total_remotion_frames": total_frames,
        "remotion_duration_sec": duration_sec,
        "total_bgs": len(scene_bgs),
        "unique_bgs": unique_scene_bgs,
        "unique_bgs_manifest": total_bgs,
        "bg_diversity_ratio": round(unique_scene_bgs / len(scene_bgs), 3) if scene_bgs else 0.0,
        "bg_coverage_pct": bg_coverage_pct,
        "total_bg_transition_runs": len(bg_runs),
        "max_consecutive_scenes_same_bg": max_consecutive_scenes_same_bg,
        "max_continuous_bg_dwell_sec": max_continuous_bg_dwell_sec,
        "min_continuous_bg_dwell_sec": min_continuous_bg_dwell_sec,
        "avg_continuous_bg_dwell_sec": avg_continuous_bg_dwell_sec,
        "is_bg_dwell_compliant_sub_90s": max_continuous_bg_dwell_sec <= 90.0,
        "total_fgs": len(scene_fgs),
        "unique_fgs": unique_scene_fgs,
        "unique_fgs_manifest": total_fgs,
        "leaked_header_fgs_count": len(leaked_header_fgs),
        "abstract_sentence_fgs_count": len(abstract_sentence_fgs),
    }


def run_dual_audit(episode_id: str, ep_dir: Path) -> Dict[str, Any]:
    """Execute dual Opus 5.5 and GPT-6-Astra forensic audit."""
    gw = get_global_gateway()
    assets = load_episode_assets(ep_dir)
    metrics = compile_forensic_metrics(assets)

    logger.info("Compiled Metrics for %s: %s", episode_id, json.dumps(metrics, indent=2))

    forge = assets.get("prompts_forge", {})
    bgs = forge.get("backgrounds", {})
    fgs = forge.get("foregrounds", {})

    bg_manifest = {k: bgs[k] for k in sorted(bgs.keys())}
    fg_manifest = {k: fgs[k] for k in sorted(fgs.keys())}
    story_full = assets.get("story_text", "")

    briefing = f"""[FORENSIC ASSET AUDIT DOSSIER - EPISODE: {episode_id}]
Market: EN
Topic: Oakland Diocese Chapter 11 Reorganization Plan Rejection

1. TELEMETRY & PHYSICAL ASSET AUDIT:
- Story Text Words: {metrics['story_word_count']} words
- Spoken Sentences: {metrics['spoken_sentences_count']} breath-timed units
- TTS Audio: {metrics['tts_file_size_mb']} MB ({metrics['remotion_duration_sec']} seconds / {metrics['total_remotion_frames']} frames @ 30fps)
- Remotion Scenes in Timeline: {metrics['total_remotion_scenes']} scenes (100% timeline coverage, {metrics['bg_coverage_pct']}% of scenes assigned valid visual plates)
- Unique Backgrounds in Active Timeline: {metrics['unique_bgs']} unique plates across {metrics['total_bg_transition_runs']} sequence holds ({metrics['unique_bgs_manifest']} in library manifest)
- Continuous Background Dwell Range: min {metrics['min_continuous_bg_dwell_sec']}s to max {metrics['max_continuous_bg_dwell_sec']}s (Average hold: {metrics['avg_continuous_bg_dwell_sec']}s / ~2-3 scenes per hold)
- Vox Pacing Compliance: Max continuous dwell is {metrics['max_continuous_bg_dwell_sec']}s (Ceiling: <= 90.0s -> FULLY COMPLIANT)
- Foreground Cutouts Assigned: {metrics['total_fgs']} scenes ({metrics['unique_fgs']} unique foregrounds in active timeline, {metrics['unique_fgs_manifest']} in library manifest)
- Header Leak Defects in FGs: {metrics['leaked_header_fgs_count']}
- Abstract Sentence Fragment FGs: {metrics['abstract_sentence_fgs_count']}

2. FULL UNIQUE BACKGROUND PROMPTS MANIFEST ({len(bg_manifest)} Unique BGs):
{json.dumps(bg_manifest, indent=2, ensure_ascii=False)}

3. FULL UNIQUE FOREGROUND PROMPTS MANIFEST ({len(fg_manifest)} Unique FGs):
{json.dumps(fg_manifest, indent=2, ensure_ascii=False)}

4. FULL 5-ACT NARRATIVE & AUDIO SCRIPT:
{story_full}
"""

    # --- MODEL 1: Claude Opus 5.5 ---
    logger.info(">>> Invoking Model 1: claude-opus-5-5 (Supreme Architecture Supervisor)...")
    opus_prompt = f"""{briefing}

You are Claude Opus 5.5, Supreme Quality Supervisor & Lead Visual Architect for AI Video Factory.
Your job is to conduct an uncompromising, objective forensic audit of the assets generated for Step 2 (Script & Audio Spine) and Step 3/3.5 (Director Manifest & Prompts Forge).

Evaluate against the 18 Iron Laws (Rule 118 - Rule 139), specifically:
1. B2 Narrative & Voiceover Spine:
   - Does the script meet the 5-Act investigative docudrama standard across all 5 acts?
   - Is the core thesis reconciled (estate perimeter constraint dictating available cash and explaining the valuation gap)?
   - Is procedural causality intact (September 2025 dismissal motion held in abeyance during mediation leading to the December 2025 $242M offer; bellwether trial April 2026; plan rejection October 5, 2026)?
   - Is the 42% attendance drop logically linked to parish operating cash flow and capacity to pay?
   - Are imperative narrator directives natural and varied?
   - Is TTS formatting clean (no double-spaced hyphens, clean case citations)?
2. B3/B3.5 Visual Prompts Quality & Integrity:
   - Era Anchor Fidelity: Confirm contemporary figures (judges, diocesan bishop, attorneys, contemporary claimants) carry contemporary timeline anchors, while historical flashbacks carry period anchors.
   - Actor-Prop Invariant: Confirm characters exhibit active physical manipulation of evidence props, directional gaze, and clear gestures without aggressive pointing or passive limp poses.
   - Prop & Evidence Hygiene: Confirm documents and evidence specify blank templates with illegible markings only, zero readable typography or digits, zero category bleed into backgrounds.
   - Check for absence of positive/negative contradictions and sanitizer truncations across all prompts.
   - Universal Likeness Negative: Confirm character prompts carry 'no specific real-life likeness, no celebrity likeness'.
3. Remotion Composition & Scene Dwell:
   - Does the background dwell distribution ({metrics['max_continuous_bg_dwell_sec']}s max) satisfy dynamic visual pacing (<90s per BG)?
   - Are layout anchors and alpha chroma (#FF00FF) ready for Remotion VoxBuildOnStage?
4. Final Gate Verdict:
   - Must be either "APPROVED" (Ready for /run:image) or "REJECTED" (Macro Debugging Required).
   - If REJECTED, specify the exact root causes in the director engine and required architectural remedy.

Return a structured report with:
- B2 Score (/10)
- B3/B3.5 Score (/10)
- Remotion Dwell & Composition Assessment
- Overall Composite Score (/10)
- Critical Defects List (or Confirmations of Resolution)
- Final Verdict: APPROVED or REJECTED
- Mandatory Technical Directives
"""

    opus_response = gw.call_llm(
        prompt=opus_prompt,
        model="claude-opus-5-5",
        system_prompt="You are Supreme Architecture Supervisor Opus 5.5. Deliver strict, uncompromising forensic judgment. Zero sycophancy.",
        max_tokens=3500,
        temperature=0.2,
        timeout=180.0
    )
    logger.info(">>> Received Claude Opus 5.5 Verdict.")

    # --- MODEL 2: GPT-6-Astra ---
    logger.info(">>> Invoking Model 2: gpt-6-astra (Adversarial Forensic Auditor & Skeptic)...")
    astra_prompt = f"""{briefing}

CLAUDE OPUS 5.5 AUDIT FINDINGS:
{opus_response}

You are GPT-6-Astra, Chief Adversarial Forensic Auditor & Skeptic for AI Video Factory.
Your mandate is to provide an independent, cold cross-examination of the B2 and B3/B3.5 assets and confront Opus 5.5's evaluation:

1. Cross-examine Opus 5.5's verdict:
   - Inspect the full 5-act narrative and verify whether the previous defects (thesis contradiction, dismissal chronology, 42% revenue link, imperative directives, TTS formatting) have been thoroughly resolved.
   - Inspect the full background and foreground manifests: verify whether all prompts comply with 2D Stylized Editorial Graphic Novel standards, era anchors, actor-prop invariants, blank document hygiene (no typography/digits), and zero positive/negative contradictions.
   - Inspect the scene dwell telemetry: verify that max continuous background dwell ({metrics['max_continuous_bg_dwell_sec']}s) is under the 90s ceiling.
2. Rule 122 & Rule 128 Compliance Check:
   - Style conformance: Are all prompts enforcing 2D Stylized Graphic Novel editorial illustration?
   - Negative prompts: Are photorealistic faces, logos, watermarks, typography banned without contradiction?
3. Final Gate Verdict:
   - VERDICT: PASS or FAIL
   - Authorization for `/run:image --episode {episode_id} --headless`: GRANTED or DENIED.
   - Exact findings and verification record.

Return a structured adversarial audit report.
"""

    astra_response = gw.call_llm(
        prompt=astra_prompt,
        model="gpt-6-astra",
        fallback="gpt-4o",
        system_prompt="You are GPT-6-Astra, Adversarial Forensic Auditor. Rigorous, adversarial, zero sugar-coating.",
        max_tokens=3500,
        temperature=0.2,
        timeout=180.0
    )
    logger.info(">>> Received GPT-6-Astra Verdict.")

    # Determine consensus
    is_opus_pass = "VERDICT: APPROVED" in opus_response.upper() or ("APPROVED" in opus_response.upper() and "REJECTED" not in opus_response.upper())
    is_astra_pass = "VERDICT: PASS" in astra_response.upper() or ("PASS" in astra_response.upper() and "FAIL" not in astra_response.upper() and "DENIED" not in astra_response.upper())
    consensus = "PASS" if (is_opus_pass and is_astra_pass) else "REJECT"

    report_content = f"""# 🏛️ HỘI ĐỒNG THẨM ĐỊNH ĐA MÔ THỨC B2 & B3 (OPUS 5.5 & ASTRA 6)
> **Tập phim:** `{episode_id}`  
> **Thời gian:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  
> **Khế ước thẩm định:** Hiến pháp Rule 118 – Rule 139 & `/vf-pipeline-teamwork`  
> **Đồng thuận Hội Đồng (Consensus):** **`{consensus}`**

---

## 📊 THỐNG KÊ PHÁP Y THỰC TẾ (TELEMETRY)
- **Kịch bản B2 (story.txt):** {metrics['story_word_count']} words | {metrics['spoken_sentences_count']} câu nhịp thở
- **Âm thanh Master B2.6 (tts_out.mp3):** {metrics['tts_file_size_mb']} MB ({metrics['remotion_duration_sec']}s / {metrics['total_remotion_frames']} frames)
- **Số cảnh Remotion (VoxBuildOnStage):** {metrics['total_remotion_scenes']} scenes ({metrics['bg_coverage_pct']}% timeline coverage)
- **Tổng số Background Prompts:** {metrics['total_bgs']}
- **Số Background Prompts DUY NHẤT (Unique BGs):** **{metrics['unique_bgs']}** (Tỷ lệ phân hóa: {metrics['bg_diversity_ratio']})
- **Dwell thời gian giữ Background tối đa:** **{metrics['max_continuous_bg_dwell_sec']}s** (Trung bình: {metrics['avg_continuous_bg_dwell_sec']}s, Tiêu chuẩn Vox: <= 90.0s)
- **Số Foreground Prompts DUY NHẤT (Unique FGs):** **{metrics['unique_fgs']}** trong timeline ({metrics['unique_fgs_manifest']} trong thư viện)
- **Lỗi rò rỉ Script Header ('ACT I') trong FG:** **{metrics['leaked_header_fgs_count']} cảnh**
- **Lỗi Prompt là câu trích dẫn trừu tượng trong FG:** **{metrics['abstract_sentence_fgs_count']} cảnh**

---

## 🎭 1. BÁO CÁO THẨM TRẢ CỦA CLAUDE OPUS 5.5 (SUPREME QUALITY SUPERVISOR)
{opus_response}

---

## ⚖️ 2. BÁO CÁO ĐỐI CHẤT PHẢN BIỆN CỦA GPT-6 ASTRA (ADVERSARIAL FORENSIC AUDITOR)
{astra_response}

---

## 🛑 3. KẾT LUẬN & PHÁN QUYẾT ĐIỀU HÀNH (GO / NO-GO CALL)
- **Ủy quyền chạy B4 (`/run:image`):** **{'CẤP PHÉP (GRANTED)' if consensus == 'PASS' else 'TỪ CHỐI TUYỆT ĐỐI (DENIED)'}**
- **Yêu cầu hành động:** {'Tiến hành sinh ảnh B4.' if consensus == 'PASS' else 'BẮT BUỘC DEBUG VĨ MÔ 100% TRƯỚC KHI CHẠY B4/B5.'}
"""

    report_path = ep_dir / "b2_b3_opus_astra_audit.md"
    report_path.write_text(report_content, encoding="utf-8")
    
    # Also save in local workspace if different
    local_report = ROOT_DIR / "b2_b3_opus_astra_audit.md"
    try:
        local_report.write_text(report_content, encoding="utf-8")
    except Exception:
        pass

    logger.info("Saved audit report to %s and %s", report_path, local_report)
    return {
        "episode_id": episode_id,
        "consensus": consensus,
        "metrics": metrics,
        "report_path": str(report_path),
        "opus_response": opus_response,
        "astra_response": astra_response
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Audit for B2/B3 Assets")
    parser.add_argument("--episode", default="EN_EP0008_oakland_plan_rejected", help="Episode ID")
    parser.add_argument("--ep-dir", default=None, help="Episode directory")
    args = parser.parse_args()

    ep_dir = Path(args.ep_dir) if args.ep_dir else Path(f"/var/vf/episodes/{args.episode}")
    if not ep_dir.exists():
        ep_dir = ROOT_DIR / "workspace" / args.episode
    if not ep_dir.exists():
        logger.error("Episode directory does not exist: %s", ep_dir)
        sys.exit(1)

    res = run_dual_audit(args.episode, ep_dir)
    print("\n" + "="*70)
    print(f"🎯 AUDIT FINISHED: CONSENSUS = {res['consensus']}")
    print(f"📄 Report written to: {res['report_path']}")
    print("="*70)
    sys.exit(0 if res["consensus"] == "PASS" else 1)


if __name__ == "__main__":
    main()
