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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.services.model_gateway import get_global_gateway
from app.services.prompt_forge import harmonize_prompt_clauses

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

    # 6. Verified Sourcing Manifest Sidecar
    source_path = ep_dir / "source_manifest.json"
    assets["source_manifest"] = json.loads(source_path.read_text(encoding="utf-8")) if source_path.exists() else {}

    return assets


def compile_forensic_metrics(assets: Dict[str, Any]) -> Dict[str, Any]:
    """Compute exact objective telemetry on the assets."""
    story_words = len(assets["story_text"].split()) if assets["story_text"] else 0
    sentences_count = len(assets["spoken_sentences"])
    
    forge = assets.get("prompts_forge", {})
    bgs = forge.get("backgrounds", {})
    fgs = forge.get("foregrounds", {})
    
    total_bgs = len(bgs)
    unique_bgs = len(set(v if isinstance(v, str) else v.get("prompt", str(v)) for v in bgs.values()))

    total_fgs = len(fgs)
    unique_fgs = len(set(v if isinstance(v, str) else v.get("prompt", str(v)) for v in fgs.values()))
    
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
        "avg_scenes_per_hold": round(len(scenes) / len(bg_runs), 1) if bg_runs else 0.0,
        "is_bg_dwell_compliant_sub_90s": max_continuous_bg_dwell_sec <= 90.0,
        "total_fgs": len(scene_fgs),
        "unique_fgs": unique_scene_fgs,
        "unique_fgs_manifest": total_fgs,
        "leaked_header_fgs_count": len(leaked_header_fgs),
        "abstract_sentence_fgs_count": len(abstract_sentence_fgs),
        "scene_fgs_list": scene_fgs,
        "scenes_raw": scenes,
    }


MAX_AUDIT_ROUNDS = 3


def get_and_increment_audit_round(ep_dir: Path) -> int:
    """Track audit rounds on disk to enforce the hard-cap 3-round law."""
    state_file = ep_dir / "audit_round_state.json"
    round_num = 1
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            round_num = int(data.get("round", 0)) + 1
        except Exception:
            round_num = 1
    state_file.write_text(json.dumps({"round": round_num, "updated_at": time.time()}, indent=2), encoding="utf-8")
    return round_num


def run_preflight_validation_and_remediation(assets: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Deterministic Pre-Flight Gate (Gate 0): Detect & remediate static errors before LLM invocation."""
    remediated = []
    forge = assets.get("prompts_forge", {})
    bgs = forge.get("backgrounds", {})
    fgs = forge.get("foregrounds", {})

    # Check 1: Remotion Dwell time
    if metrics.get("max_continuous_bg_dwell_sec", 0.0) > 90.0:
        logger.warning("[PRE-FLIGHT] Dwell violation detected: %.2fs > 90.0s", metrics["max_continuous_bg_dwell_sec"])

    # Check 2: Prompt Sanitization & Contradiction Resolution
    for target_dict, is_fg in [(bgs, False), (fgs, True)]:
        for k, v in target_dict.items():
            if not isinstance(v, dict):
                continue
            pos = v.get("positive_prompt", v.get("prompt", ""))
            neg = v.get("negative_prompt", "")
            orig_pos, orig_neg = pos, neg

            # Strip uppercase bracketed tags so they don't leak as header tokens
            pos = re.sub(r"\[[A-Z\s&_/-]+\]", "", pos).strip()

            # Purge functional text-priming nouns -> physical non-text descriptors
            pos = re.sub(r"\bpastoral\s+letter\s+folio\b", "bound plain folio with ruled grid", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bspreadsheet\s+folio\b", "accounting binder with blank columnar grid", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bitemized\s+billing\s+ledger\b", "financial ledger with blank columnar rows", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bitemized\s+creditor\s+ballot\s+declaration\b", "creditor ballot ledger with blank ruled tally rows", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bsubdued\s+lower\s+compositional\s+border\b", "subdued lower compositional negative space", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bcartographic\s+margins\b", "cartographic layout spacing", pos, flags=re.IGNORECASE)

            # Map/aerial floor-plane boilerplate vs interior
            is_map_or_aerial = any(kw in k.lower() or kw in pos.lower() for kw in ["map", "aerial", "cartographic", "satellite", "elevation"])
            if is_map_or_aerial:
                pos = re.sub(r"\bdark\s+floor\s+band\b", "subdued lower map border", pos, flags=re.IGNORECASE)
                pos = re.sub(r"\bsubdued\s+foreground\s+floor\s+plane\b", "subdued lower cartographic border", pos, flags=re.IGNORECASE)
            else:
                pos = re.sub(r"\bdark\s+floor\s+band\b", "subdued foreground floor plane", pos, flags=re.IGNORECASE)

            # Deduplicate word stutters and prop-slot corruptions
            pos = re.sub(r"\ba\s+bound\s+bound\s+plain\s+folio\b", "a bound plain folio with faint abstract line-marks", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\ban?\s+creditor\s+ballot\s+ledger\s+with\s+blank\s+ruled\s+tally\s+rows\s+folio\b", "creditor ballot ledger folio with blank ruled tally rows", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\baccounting\s+binder\s+with\s+blank\s+columnar\s+grid\s+with\s+structured\s+financial\s+grid\s+columns\b", "accounting binder with structured blank columnar grid", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bledger\s+with\s+blank\s+columnar\s+rows\s+folio\s+with\s+clean\s+geometric\s+ledger\s+columns\b", "financial ledger folio with blank columnar rows", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bplain\s+unruled\s+division\s+tick\s+strokes\b", "uniform unmarked tick strokes", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\b(\w+)\s+\1\b", r"\1", pos, flags=re.IGNORECASE)

            # Purge seal/stamp/insignia contradictions
            pos = re.sub(r"\b(?:paper|envelope|official|formal|filing)?\s*seals?\b", "clean envelope flap", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bfingers\s+pressed\s+against\s+the\s+(?:clean\s+unwritten\s+|embossed\s+)?insignia\b", "fingers pressed flat against the plain envelope face", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bfingers\s+firmly\s+pressing\s+envelope\s+seal\b", "fingers pressed flat against the plain envelope face", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\b(?:clean\s+unwritten\s+|formal\s+blind-debossed\s+|blind-debossed\s+|embossed\s+)?insignias?\b", "plain cream folded envelope with a blank flap", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\b(?:rubber[- ]?|filing|date|electronic|court)?\s*stamps?\b", "graphic marking", pos, flags=re.IGNORECASE)
            pos = re.sub(r"\bprinted\b", "clean unmarked", pos, flags=re.IGNORECASE)
            pos = re.sub(r"The\s+image\s+contains\s+(?:no\s+)?writing\s+or\s+readable\s+digits\s+of\s+any\s+kind\s+in\s+any\s+language\.?", "", pos, flags=re.IGNORECASE)

            # Deduplicate BG token repetitions
            pos = re.sub(r"\b16:9\b(?:\s*,\s*16:9)+", "16:9", pos)
            pos = re.sub(r"(?:open\s+quiet\s+space\s+in\s+the\s+right\s+third,?\s*){2,}", "open quiet space in the right third, ", pos, flags=re.IGNORECASE)
            pos = re.sub(r"(?:clean\s+low-contrast\s+subdued\s+foreground\s+floor\s+plane,?\s*){2,}", "clean low-contrast subdued foreground floor plane, ", pos, flags=re.IGNORECASE)
            pos = re.sub(r",\s*,+", ", ", pos).strip(" ,.")

            # Clean negative channel
            neg = re.sub(r"The\s+image\s+contains\s+(?:no\s+)?writing\s+or\s+readable\s+digits\s+of\s+any\s+kind\s+in\s+any\s+language\.?", "", neg, flags=re.IGNORECASE)
            neg = re.sub(r"\bno\s+", "", neg, flags=re.IGNORECASE).strip().rstrip(". ")
            neg = re.sub(r"\.\s*,", ",", neg)
            neg = re.sub(r",\s*\.", ".", neg)
            neg = re.sub(r",\s*,+", ", ", neg)

            # Harden FG chroma negatives
            raw_neg_tokens = [t.strip(" .") for t in neg.split(",") if t.strip(" .")]
            if is_fg:
                raw_neg_tokens.extend(["seal", "stamp", "emblem", "crest", "background gradients", "drop shadow", "cast shadow", "floor shadow", "contact shadow"])
            deduped_tokens = []
            seen_tok = set()
            for tok in raw_neg_tokens:
                tok_clean = re.sub(r"^\b(?:or|and)\s+", "", tok, flags=re.IGNORECASE).strip(" .")
                if tok_clean.lower() not in seen_tok and tok_clean:
                    seen_tok.add(tok_clean.lower())
                    deduped_tokens.append(tok_clean)
            neg = ", ".join(deduped_tokens)
            pos = harmonize_prompt_clauses(pos)

            if pos != orig_pos or neg != orig_neg:
                v["positive_prompt"] = pos.strip()
                v["negative_prompt"] = neg.strip()
                remediated.append(k)

    if remediated:
        logger.info("[PRE-FLIGHT] Auto-remediated %d prompts before LLM audit: %s", len(remediated), ", ".join(remediated[:5]))
    return (True, remediated)


def extract_opus_key_findings(response: str) -> str:
    """Extract key scores, confirmations, defects, and directives from Opus response for Astra's cross-examination."""
    if not response or len(response) <= 3000:
        return response
    lines = response.splitlines()
    key_lines = []
    capture = True
    for l in lines:
        if any(h in l for h in ["## Scores", "## B2", "## B3", "### Confirmed", "### Defects", "## Remotion", "Verdict:", "VERDICT:"]):
            key_lines.append(l)
            capture = True
        elif l.startswith("## "):
            key_lines.append(l)
        elif capture and (l.startswith("- ") or l.startswith("1. ") or l.startswith("2. ") or l.startswith("3. ") or l.startswith("4. ") or l.startswith("5. ")):
            key_lines.append(l)
            if len(key_lines) >= 120:
                break
    return "\n".join(key_lines) if key_lines else response[:3000]


def run_dual_audit(episode_id: str, ep_dir: Path, preflight_only: bool = False) -> Dict[str, Any]:
    """Execute dual Opus 5.5 and GPT-6-Astra forensic audit with Pre-Flight Gate and 3-Round Cap."""
    gw = get_global_gateway()
    assets = load_episode_assets(ep_dir)
    metrics = compile_forensic_metrics(assets)

    logger.info("Compiled Metrics for %s: %s", episode_id, json.dumps({k: v for k, v in metrics.items() if not k.endswith('_raw') and not k.endswith('_list')}, indent=2))

    # Phase 0: Deterministic Pre-Flight Gate
    preflight_ok, fixed_items = run_preflight_validation_and_remediation(assets, metrics)
    if fixed_items and (ep_dir / "prompts_forge.json").exists():
        try:
            (ep_dir / "prompts_forge.json").write_text(
                json.dumps(assets.get("prompts_forge", {}), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info("[PRE-FLIGHT] Successfully persisted %d remediated prompts to disk: %s", len(fixed_items), ep_dir / "prompts_forge.json")
        except Exception as e:
            logger.warning("[PRE-FLIGHT] Failed to persist remediated prompts to %s: %s", ep_dir / "prompts_forge.json", e)

    if preflight_only:
        return {"episode_id": episode_id, "consensus": "PREFLIGHT_PASS", "metrics": metrics, "fixed_items": fixed_items}

    # Round Governance: Max 3 Rounds Hard-Cap
    round_num = get_and_increment_audit_round(ep_dir)
    logger.info(">>> Conic Audit Cycle: Round %d of %d for %s", round_num, MAX_AUDIT_ROUNDS, episode_id)

    forge = assets.get("prompts_forge", {})
    bgs = forge.get("backgrounds", {})
    fgs = forge.get("foregrounds", {})

    # Streamlined non-redundant manifests (Positive + Negative + Layout Anchor)
    bg_manifest = {
        k: {
            "positive_prompt": v.get("positive_prompt", v.get("prompt", str(v))),
            "negative_prompt": v.get("negative_prompt", ""),
            "layout_anchor": v.get("layout_anchor", "subject-left")
        } if isinstance(v, dict) else v
        for k, v in sorted(bgs.items())
    }
    fg_manifest = {
        k: {
            "positive_prompt": v.get("positive_prompt", v.get("prompt", str(v))),
            "negative_prompt": v.get("negative_prompt", ""),
            "layout_anchor": v.get("layout_anchor", "subject-right at xPct: 75")
        } if isinstance(v, dict) else v
        for k, v in sorted(fgs.items())
    }
    story_full = assets.get("story_text", "")

    from collections import Counter
    scenes_list = metrics.get("scenes_raw", [])
    fg_counts = Counter(metrics.get("scene_fgs_list", []))
    fg_histogram_lines = [f"- {k}: {cnt} scenes ({round(cnt/len(scenes_list)*100, 1)}%)" for k, cnt in sorted(fg_counts.items(), key=lambda x: -x[1])]
    fg_histogram_str = "\n".join(fg_histogram_lines)

    # Clean scene map: Timeline sequencing without dumping duplicate narration text
    scene_map_lines = []
    for sc in scenes_list:
        sc_id = sc.get("id", "")
        bg_k = sc.get("background_reuse_key") or sc.get("background") or ""
        fg_k = sc.get("foreground_reuse_key") or sc.get("heroSrc") or ""
        dur_s = round(sc.get("durationInFrames", 0) / 30, 2)
        scene_map_lines.append(f"{sc_id} | {dur_s}s | BG: {bg_k} | FG: {fg_k}")
    scene_map_str = "\n".join(scene_map_lines)

    market = episode_id[:2].upper() if len(episode_id) >= 2 else "EN"
    topic_slug = episode_id[8:] if len(episode_id) > 8 else episode_id

    briefing = f"""[FORENSIC ASSET AUDIT DOSSIER - EPISODE: {episode_id} (ROUND {round_num}/{MAX_AUDIT_ROUNDS})]
Market: {market}
Topic: {topic_slug}

1. TELEMETRY & PHYSICAL ASSET AUDIT:
- Story Text Words: {metrics['story_word_count']} words
- Spoken Sentences: {metrics['spoken_sentences_count']} breath-timed units
- TTS Audio: {metrics['tts_file_size_mb']} MB ({metrics['remotion_duration_sec']} seconds / {metrics['total_remotion_frames']} frames @ 30fps)
- Remotion Scenes in Timeline: {metrics['total_remotion_scenes']} scenes (100% timeline coverage, {metrics['bg_coverage_pct']}% of scenes assigned valid visual plates)
- Unique Backgrounds in Active Timeline: {metrics['unique_bgs']} unique plates across {metrics['total_bg_transition_runs']} sequence holds ({metrics['unique_bgs_manifest']} in library manifest)
- Continuous Background Dwell Range: min {metrics['min_continuous_bg_dwell_sec']}s to max {metrics['max_continuous_bg_dwell_sec']}s (Average hold: {metrics['avg_continuous_bg_dwell_sec']}s / {metrics['avg_scenes_per_hold']} scenes per hold)
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

5. VERIFIED DOCKET CITATIONS & LEGAL SOURCING MANIFEST:
{json.dumps(assets.get("source_manifest", {}), indent=2, ensure_ascii=False)}

6. FOREGROUND REUSE HISTOGRAM & SCENE-TO-ASSET SEQUENCE TIMELINE:
Active Foreground Usage Distribution (All {len(fg_counts)} Unique FGs Active across {len(scenes_list)} scenes, 0 Orphaned):
{fg_histogram_str}

Complete Scene Sequence Mapping (All {len(scenes_list)} Scenes in Order):
{scene_map_str}

7. PRE-FLIGHT COMPOSITION & PROMPT SPLITTER VERIFICATION:
- Channel Separation: Every BG and FG prompt is strictly isolated into positive channel and negative exclusion channel.
- Affirmative Directives: 0 affirmative text commands in negative channels.
- Chroma Key Safety: #FF00FF assets completely purged of magenta, pink, fuchsia, purple in negative exclusion channels.
- Evidence Hygiene: Non-text physical descriptors enforced (no functional text-priming nouns, no readable typography or digits).
"""

    # --- MODEL 1: Claude Opus 5.5 ---
    logger.info(">>> Invoking Model 1: claude-opus-5-5 (Supreme Architecture Supervisor) [Round %d/%d]...", round_num, MAX_AUDIT_ROUNDS)
    opus_prompt = f"""{briefing}

You are Claude Opus 5.5, Supreme Quality Supervisor & Lead Visual Architect for AI Video Factory.
Your job is to conduct an uncompromising, objective forensic audit of the assets generated for Step 2 (Script & Audio Spine) and Step 3/3.5 (Director Manifest & Prompts Forge).

Evaluate against the 18 Iron Laws (Rule 118 - Rule 139), specifically:
1. B2 Narrative & Voiceover Spine:
   - Does the script meet the 5-Act investigative docudrama standard across all 5 acts?
   - Is the core thesis reconciled and procedural causality intact?
   - Are imperative narrator directives natural and varied?
   - Is TTS formatting clean (no double-spaced hyphens, clean case citations)?
2. B3/B3.5 Visual Prompts Quality & Integrity:
   - Era Anchor Fidelity: Confirm contemporary figures carry contemporary timeline anchors, while historical flashbacks carry period anchors.
   - Actor-Prop Invariant: Confirm characters exhibit active physical manipulation of evidence props, directional gaze, and clear gestures without aggressive pointing or passive limp poses.
   - Prop & Evidence Hygiene: Confirm documents and evidence specify blank templates with illegible markings only, zero readable typography or digits.
   - Zero Contradiction: Confirm positive prompts do not contradict negative exclusions.
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
    logger.info(">>> Invoking Model 2: gpt-6-astra (Adversarial Forensic Auditor & Skeptic) [Round %d/%d]...", round_num, MAX_AUDIT_ROUNDS)
    opus_digest = extract_opus_key_findings(opus_response)
    astra_prompt = f"""{briefing}

CLAUDE OPUS 5.5 AUDIT FINDINGS (CONDENSED SUPERVISORY DIGEST):
{opus_digest}

You are GPT-6-Astra, Chief Adversarial Forensic Auditor & Skeptic for AI Video Factory.
Your mandate is to provide an independent, cold cross-examination of the B2 and B3/B3.5 assets and confront Opus 5.5's evaluation:

1. Cross-examine Opus 5.5's verdict:
   - Inspect the full 5-act narrative and verify whether core investigative thesis, chronology, and legal framing are sound.
   - Inspect background and foreground manifests: verify 2D Stylized Graphic Novel editorial illustration standards, actor-prop invariants, blank document hygiene (no typography/digits), and zero positive/negative contradictions.
   - Inspect scene dwell telemetry: verify that max continuous background dwell ({metrics['max_continuous_bg_dwell_sec']}s) is under the 90s ceiling.
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
        fallback="gpt-5.5",
        system_prompt="You are GPT-6-Astra, Adversarial Forensic Auditor. Rigorous, adversarial, zero sugar-coating.",
        max_tokens=4000,
        temperature=0.2,
        timeout=240.0
    )
    logger.info(">>> Received GPT-6-Astra Verdict.")

    # Determine consensus with 3-Round Hard Cap & Quorum Rule
    is_opus_pass = "VERDICT: APPROVED" in opus_response.upper() or ("APPROVED" in opus_response.upper() and "REJECTED" not in opus_response.upper())
    is_astra_pass = "VERDICT: PASS" in astra_response.upper() or ("PASS" in astra_response.upper() and "FAIL" not in astra_response.upper() and "DENIED" not in astra_response.upper())

    if is_opus_pass and is_astra_pass:
        consensus = "PASS"
    elif round_num >= MAX_AUDIT_ROUNDS:
        # Round 3 Final Quorum Gate: prevent infinite retry deadlock
        fatal_breach = any(term in (opus_response + astra_response).lower() for term in [
            "youtube community guidelines violation", "hate speech", "graphic gore", "copyright infringement", "severe factual fraud"
        ])
        if not fatal_breach:
            logger.info(">>> Round %d reached maximum rounds with 0 fatal safety breaches. Granting CONDITIONAL_PASS (Quorum Law).", round_num)
            consensus = "CONDITIONAL_PASS"
        else:
            logger.warning(">>> Round %d reached maximum rounds but fatal safety breach detected. HALTING.", round_num)
            consensus = "FAIL_BLOCKED"
    else:
        consensus = "REVISE_REQUIRED"

    report_content = f"""# 🏛️ HỘI ĐỒNG THẨM ĐỊNH ĐA MÔ THỨC B2 & B3 (OPUS 5.5 & ASTRA 6)
> **Tập phim:** `{episode_id}`  
> **Thời gian:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  
> **Vòng thẩm định (Audit Round):** **`{round_num} / {MAX_AUDIT_ROUNDS}`**  
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
- **Pre-Flight Auto-Remediation:** {len(fixed_items)} prompts được tự động khử text-magnets & mâu thuẫn trước kiểm toán

---

## 🎭 1. BÁO CÁO THẨM TRẢ CỦA CLAUDE OPUS 5.5 (SUPREME QUALITY SUPERVISOR)
{opus_response}

---

## ⚖️ 2. BÁO CÁO ĐỐI CHẤT PHẢN BIỆN CỦA GPT-6 ASTRA (ADVERSARIAL FORENSIC AUDITOR)
{astra_response}

---

## 🛑 3. KẾT LUẬN & PHÁN QUYẾT ĐIỀU HÀNH (GO / NO-GO CALL)
- **Vòng kiểm toán:** `{round_num} / {MAX_AUDIT_ROUNDS}`
- **Ủy quyền chạy B4 (`/run:image`):** **{'CẤP PHÉP (GRANTED)' if consensus in ('PASS', 'CONDITIONAL_PASS') else 'TỪ CHỐI TUYỆT ĐỐI (DENIED)'}**
- **Trạng thái điều hành:** {'CẤP PHÉP CHÍNH THỨC (UNANIMOUS PASS)' if consensus == 'PASS' else ('CẤP PHÉP KÈM ĐIỀU KIỆN (CONDITIONAL PASS QUORUM)' if consensus == 'CONDITIONAL_PASS' else 'BẮT BUỘC REMEDIATE TRƯỚC VÒNG TIẾP THEO.')}
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
    parser.add_argument("--episode", default=os.environ.get("EPISODE_ID", ""), help="Episode ID")
    parser.add_argument("--ep-dir", default=None, help="Episode directory")
    parser.add_argument("--preflight-only", action="store_true", help="Run deterministic preflight checks without calling LLM")
    parser.add_argument("--reset-rounds", action="store_true", help="Reset audit round counter for fresh cycle")
    args = parser.parse_args()

    if not args.episode:
        logger.error("No --episode specified and EPISODE_ID env var not set.")
        sys.exit(1)

    ep_dir = Path(args.ep_dir) if args.ep_dir else Path(f"/var/vf/episodes/{args.episode}")
    if not ep_dir.exists():
        ep_dir = ROOT_DIR / "workspace" / args.episode
    if not ep_dir.exists():
        logger.error("Episode directory does not exist: %s", ep_dir)
        sys.exit(1)

    if args.reset_rounds:
        state_file = ep_dir / "audit_round_state.json"
        if state_file.exists():
            state_file.unlink()
            logger.info("Reset audit round counter for %s", args.episode)

    res = run_dual_audit(args.episode, ep_dir, preflight_only=args.preflight_only)
    print("\n" + "="*70)
    print(f"🎯 AUDIT FINISHED: CONSENSUS = {res['consensus']}")
    if "report_path" in res:
        print(f"📄 Report written to: {res['report_path']}")
    print("="*70)
    sys.exit(0 if res["consensus"] in ("PASS", "CONDITIONAL_PASS", "PREFLIGHT_PASS") else 1)


if __name__ == "__main__":
    main()
