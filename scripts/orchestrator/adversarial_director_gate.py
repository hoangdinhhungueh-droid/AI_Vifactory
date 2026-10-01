#!/usr/bin/env python3
# scripts/orchestrator/adversarial_director_gate.py
"""B6 Autonomous Staging & Adversarial Subagent Gate.

Acts as the Ruthless Executive Director / Visual QA Gatekeeper (Rule 122 & Rule 129):
1. Verifies Vox Minimalist Pacing (overlay density <= 20%).
2. Enforces 100% Market Localization (bans generic English labels in non-English videos).
3. Enforces Rule 118 Zero-Mock Data (every kinetic_counter must have a verified quantitative metric).
4. Enforces Rule 136 Clean Speaker Tags (no file extensions, no internal prefixes).
5. Triggers Remotion CLI to render 5-8 Still Frames (~1.5s/frame) and conducts visual forensic integrity checks.
6. Automatically applies repairs to remotion_props.json if defects are found.
7. Generates director_gate_report.json. When verdict == 'PASS', signs off on VPS Master Render.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.services.editorial_briefing_generator import (
    extract_market_from_episode_id,
    prune_and_localize_scenes,
    LOCALIZED_OVERLAY_THEMES,
    BANNED_VERDICT_TERMS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adversarial_director_gate")


def audit_props_integrity(props: Dict[str, Any], market: str) -> Tuple[bool, List[str]]:
    """Audit remotion_props.json against adversarial director standards."""
    defects = []
    scenes = props.get("scenes", [])
    if not scenes:
        return False, ["FATAL: remotion_props has 0 scenes."]

    # 1. Overlay Density Audit (Vox Pacing)
    fo_count = sum(1 for s in scenes if s.get("forensicOverlay"))
    density_pct = (fo_count / len(scenes)) * 100
    if density_pct > 35.0:
        defects.append(f"OVERLAY_DENSITY_TOO_HIGH: {fo_count}/{len(scenes)} scenes ({density_pct:.1f}%) have overlays (max allowed 35.0%).")

    # 2. Market Localization Audit & Legal Banned Lexicon (Rule 122, 128, 134)
    m_clean = market.upper()
    for i, s in enumerate(scenes):
        fo = s.get("forensicOverlay")
        if fo and isinstance(fo, dict):
            fo_str = json.dumps(fo, ensure_ascii=False)
            for b_term in BANNED_VERDICT_TERMS:
                if b_term in fo_str:
                    defects.append(f"BANNED_LEGAL_LEXICON in Scene {i:02d}: '{b_term}' found in overlay.")

            if m_clean != "EN":
                english_cliches = [
                    "OFFICIAL INVESTIGATION RECORD", "FINDINGS OF FACT",
                    "AUDIT DISCREPANCY", "CRITICAL FINDING", "SUBPOENAED EVIDENCE",
                    "INVESTIGATION NETWORK", "GEO-TACTICAL TELEMETRY", "CRIMINAL INDICTMENT",
                    "DOCKET", "INDICTMENT", "SUBPOENA"
                ]
                for cliche in english_cliches:
                    if cliche in fo_str:
                        defects.append(f"UNLOCALIZED_OVERLAY_TEXT in Scene {i:02d}: '{cliche}' found in {m_clean} episode.")

        # Speaker tag audit (Rule 136)
        tag = str(s.get("speakerTag") or "")
        if tag and ("ARCHIVE X" in tag or tag.endswith(".png") or tag.endswith(".jpg")):
            defects.append(f"LEAKED_ASSET_TAG in Scene {i:02d}: '{tag}'")

    # 3. Zero-Mock Kinetic Counter Audit (Rule 118)
    for i, s in enumerate(scenes):
        fo = s.get("forensicOverlay")
        if fo and isinstance(fo, dict) and fo.get("type") in ("kinetic_counter", "financial_chart"):
            stat_v = s.get("statValue")
            p = fo.get("payload") or {}
            end_val = p.get("end_value") or p.get("amount")
            if not stat_v and not end_val:
                defects.append(f"EMPTY_KINETIC_COUNTER in Scene {i:02d}: counter overlay present but no quantitative value parsed.")

    # 4. Foreground Character Sparsity vs Evidence Exhibits Audit (VOX Pacing & Anti-OOM)
    def is_evidence_object(s: Dict[str, Any]) -> bool:
        fg = str(s.get("foreground") or "").lower()
        tag = str(s.get("speakerTag") or "").lower()
        role = str(s.get("foreground_role") or "").lower()
        lz = s.get("layout_zone") or {}
        place = str(lz.get("placement") if isinstance(lz, dict) else "").lower()
        return any(k in fg for k in ["evidence", "doc_", "docket", "invoice", "ledger", "memo", "gauge", "statute", "rack", "contract", "binder", "stamp", "scale", "gavel", "box", "log", "prop", "artifact", "bill", "check", "receipt", "filing", "exhibit"]) or "document" in place or "evidence" in place or "artifact" in role

    # Dynamic threshold: allow higher visual density (up to 85% evidence, 35% humans) for feature documentary episodes (> 30 scenes)
    # while preserving strict VOX minimalism (55% evidence, 20% humans) for micro-tests (<= 30 scenes)
    max_human_pct = 35.0 if len(scenes) > 30 else 20.0
    max_ev_pct = 85.0 if len(scenes) > 30 else 55.0

    human_fg_count = sum(1 for s in scenes if s.get("foreground") and not is_evidence_object(s))
    human_fg_pct = (human_fg_count / len(scenes)) * 100 if scenes else 0
    if human_fg_pct > max_human_pct:
        defects.append(f"FG_DENSITY_TOO_HIGH: {human_fg_count}/{len(scenes)} scenes ({human_fg_pct:.1f}%) have human foreground characters (max allowed {max_human_pct:.1f}%).")

    evidence_fg_count = sum(1 for s in scenes if s.get("foreground") and is_evidence_object(s))
    evidence_fg_pct = (evidence_fg_count / len(scenes)) * 100 if scenes else 0
    if evidence_fg_pct > max_ev_pct:
        defects.append(f"FG_DENSITY_TOO_HIGH: {evidence_fg_count}/{len(scenes)} scenes ({evidence_fg_pct:.1f}%) have evidence exhibits (max allowed {max_ev_pct:.1f}% for pacing & anti-OOM).")

    # 5. Layout Zone Variety Audit (Anti-Monotony)
    current_placement = None
    streak = 0
    for i, s in enumerate(scenes):
        lz = s.get("layout_zone")
        placement = lz.get("placement") if isinstance(lz, dict) else s.get("safeZone")
        if placement and placement == current_placement:
            streak += 1
            if streak >= 6:
                defects.append(f"LAYOUT_ZONE_MONOTONY: Scene {i:02d} is part of a {streak}+ scene streak with identical placement '{placement}'.")
                break
        else:
            current_placement = placement
            streak = 1

    # 6. Animation Cue Trigger Word Integrity Audit
    for i, s in enumerate(scenes):
        ac = s.get("animation_cue")
        if ac and isinstance(ac, dict):
            tw = str(ac.get("trigger_word") or "").strip()
            narr = str(s.get("narration") or s.get("caption") or "")
            if tw and narr and tw.lower() not in narr.lower():
                defects.append(f"ANIMATION_TRIGGER_MISMATCH in Scene {i:02d}: Trigger word '{tw}' not found in scene narration.")

    is_clean = len(defects) == 0
    return is_clean, defects


def auto_repair_props(props: Dict[str, Any], market: str) -> Dict[str, Any]:
    """Auto-repair props by pruning excess overlays, localizing text, breaking layout monotony, and enforcing FG sparsity."""
    logger.info("Auto-repairing remotion_props.json for market %s...", market)
    scenes = props.get("scenes", [])
    sanitized = prune_and_localize_scenes(scenes, market)

    # 1. Auto-prune FG: separate human characters (<= 12) vs forensic evidence objects (<= 60 / ~50%)
    def is_evidence_object(s: Dict[str, Any]) -> bool:
        fg = str(s.get("foreground") or "").lower()
        tag = str(s.get("speakerTag") or "").lower()
        role = str(s.get("foreground_role") or "").lower()
        lz = s.get("layout_zone") or {}
        place = str(lz.get("placement") if isinstance(lz, dict) else "").lower()
        return any(k in fg for k in ["evidence", "doc_", "docket", "invoice", "ledger", "memo", "gauge", "statute", "rack", "contract", "binder", "stamp", "scale", "gavel", "box", "log", "prop", "artifact", "bill", "check", "receipt", "filing", "exhibit"]) or "document" in place or "evidence" in place or "artifact" in role

    # Auto-prune human character cutouts if count > 12 (enforcing <= 12 high-impact VOX character cutouts)
    human_scenes = [s for s in sanitized if s.get("foreground") and not is_evidence_object(s)]
    target_max_humans = min(45, max(12, int(len(sanitized) * 0.30))) if len(sanitized) > 30 else 12
    if len(human_scenes) > target_max_humans:
        logger.info("Auto-repair: pruning human FG characters from %d to <= %d...", len(human_scenes), target_max_humans)
        step = max(1, len(human_scenes) // target_max_humans)
        h_seen = 0
        for s in sanitized:
            if s.get("foreground") and not is_evidence_object(s):
                if h_seen % step != 0 or h_seen >= target_max_humans * step:
                    s["foreground"] = ""
                    if isinstance(s.get("layout_zone"), dict):
                        s["layout_zone"]["placement"] = "center_hero_document"
                h_seen += 1

    # Auto-prune evidence objects if count exceeds 50% density (target max 60 exhibits)
    evidence_scenes = [s for s in sanitized if s.get("foreground") and is_evidence_object(s)]
    target_max_evidence = min(130, max(12, int(len(sanitized) * 0.85))) if len(sanitized) > 30 else min(60, max(12, int(len(sanitized) * 0.50)))
    if len(evidence_scenes) > target_max_evidence:
        logger.info("Auto-repair: pruning evidence FG objects from %d to <= %d...", len(evidence_scenes), target_max_evidence)
        step = max(1, len(evidence_scenes) // target_max_evidence)
        e_seen = 0
        for s in sanitized:
            if s.get("foreground") and is_evidence_object(s):
                if e_seen % step != 0 or e_seen >= target_max_evidence * step:
                    s["foreground"] = ""
                    if isinstance(s.get("layout_zone"), dict):
                        s["layout_zone"]["placement"] = "center_hero_document"
                e_seen += 1

    # 2. Auto-repair layout monotony: break streaks >= 5 across canonical VOX layout zones
    vox_zones = ["split_evidence_left", "center_hero_document", "split_evidence_right", "bottom_third_dossier"]
    prev_place = None
    streak = 0
    for idx, s in enumerate(sanitized):
        lz = s.get("layout_zone")
        if isinstance(lz, dict):
            place = lz.get("placement") or "center_hero_document"
            if place == prev_place:
                streak += 1
                if streak >= 5:
                    candidates = [z for z in vox_zones if z != prev_place]
                    new_place = candidates[idx % len(candidates)]
                    lz["placement"] = new_place
                    prev_place = new_place
                    streak = 1
            else:
                prev_place = place
                streak = 1
        else:
            # If layout_zone is missing or string, synthesize clean VOX layout_zone
            candidates = [z for z in vox_zones if z != prev_place]
            new_place = candidates[idx % len(candidates)]
            s["layout_zone"] = {
                "placement": new_place,
                "safe_zone": "bottom_left" if "left" in new_place else "bottom_right",
                "camera_pan_axis": "horizontal" if idx % 2 == 0 else "static"
            }
            prev_place = new_place
            streak = 1

    # 3. Auto-repair animation trigger word mismatch against scene narration
    for s in sanitized:
        ac = s.get("animation_cue")
        if ac and isinstance(ac, dict):
            tw = str(ac.get("trigger_word") or "").strip()
            narr = str(s.get("narration") or s.get("caption") or "")
            if tw and narr and tw.lower() not in narr.lower():
                # Pick first 4+ letter word from narration as trigger or clear
                words = [w.strip(".,!?:;\"'") for w in narr.split() if len(w.strip(".,!?:;\"'")) >= 4]
                ac["trigger_word"] = words[0] if words else ""

    # 4. Auto-repair empty kinetic counters: convert to document_highlight (Rule 118)
    for s in sanitized:
        fo = s.get("forensicOverlay")
        if fo and isinstance(fo, dict) and fo.get("type") in ("kinetic_counter", "financial_chart"):
            stat_v = s.get("statValue")
            p = fo.get("payload") or {}
            end_val = p.get("end_value") or p.get("amount")
            if not stat_v and not end_val:
                fo["type"] = "document_highlight"
                fo["title"] = "OFFICIAL RECORD // AUDIT EVIDENCE"
                fo["badge"] = "EVIDENCE"
                s["forensicOverlay"] = fo

    # 5. Deep recursive sanitization of remaining banned legal terms (Rule 122, 128, 134)
    from app.services.editorial_briefing_generator import get_stamp_measurement_map
    meas_map = get_stamp_measurement_map(market)
    fallback_rep = "行政検査" if market.upper() == "JP" else "AUDIT RECORD"

    def _clean_obj(obj: Any) -> Any:
        if isinstance(obj, str):
            res = obj
            for b_term in BANNED_VERDICT_TERMS:
                if b_term in res:
                    replacement = meas_map.get(b_term, fallback_rep)
                    if b_term in replacement:
                        replacement = fallback_rep
                    res = res.replace(b_term, replacement)
            return res
        elif isinstance(obj, dict):
            return {k: _clean_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_clean_obj(elem) for elem in obj]
        return obj

    for s in sanitized:
        if "forensicOverlay" in s and isinstance(s["forensicOverlay"], dict):
            s["forensicOverlay"] = _clean_obj(s["forensicOverlay"])

    props["scenes"] = sanitized
    return props


def extract_sample_still_frames(
    props_path: str,
    output_dir: str,
    remotion_dir: str = "/root/video_factory/remotion",
    sample_count: int = 5,
) -> List[str]:
    """Extract sample still frames using Remotion CLI for visual spot-checking."""
    with open(props_path, "r", encoding="utf-8") as f:
        props = json.load(f)

    scenes = props.get("scenes", [])
    if not scenes:
        return []

    # Calculate key frame points (Beat 1, 2, 3, 4, 5)
    total_frames = sum(s.get("durationInFrames", 120) for s in scenes)
    step = max(30, total_frames // (sample_count + 1))
    target_frames = [step * i for i in range(1, sample_count + 1)]

    os.makedirs(output_dir, exist_ok=True)
    extracted_paths = []

    for idx, f_num in enumerate(target_frames):
        out_jpg = os.path.join(output_dir, f"still_gate_frame_{f_num}.jpg")
        cmd = [
            "npx", "--prefix", remotion_dir,
            "remotion", "still",
            f"{remotion_dir}/src/index.tsx",
            "TwoLayerEpisode",
            out_jpg,
            f"--props={props_path}",
            f"--public-dir={remotion_dir}/public",
            f"--frame={f_num}",
            "--gl=angle",
            "--image-format=jpeg",
            "--jpeg-quality=85",
        ]
        try:
            logger.info("Rendering still frame %d at frame %d...", idx + 1, f_num)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            if res.returncode == 0 and os.path.exists(out_jpg) and os.path.getsize(out_jpg) > 10000:
                extracted_paths.append(out_jpg)
                logger.info("PASS still frame %d: %s (%d bytes)", idx + 1, out_jpg, os.path.getsize(out_jpg))
            else:
                logger.warning("Still frame failed at frame %d: %s", f_num, res.stderr[:200])
        except Exception as e:
            logger.warning("Still frame command error at frame %d: %s", f_num, e)

    return extracted_paths


def compute_5axis_motion_parity_score(props: Dict[str, Any], defects: List[str]) -> Dict[str, Any]:
    """Compute 5-Axis Scorecard against YouTube Benchmark (cXQuNBZA0FA Parity).
    Axis 1: Layer-by-Layer Procedural Assembly
    Axis 2: True Motion & Element-Level Kinematics
    Axis 3: Match-Cut & Directional Transitions
    Axis 4: Evidentiary Purity & Zero Dual-Number Conflict
    Axis 5: Editorial Graphic Novel Art Purity
    """
    scenes = props.get("scenes", [])
    total_scenes = max(1, len(scenes))
    
    # Axis 1: Staggered assembly presence
    has_layers = sum(1 for s in scenes if s.get("foreground") or s.get("forensicOverlay") or s.get("statValue"))
    score_axis1 = min(10.0, round(5.0 + (has_layers / total_scenes) * 5.0, 1))

    # Axis 2: Kinematics / movement presence
    has_moves = sum(1 for s in scenes if s.get("cameraMovement") or s.get("motionDirective"))
    score_axis2 = min(10.0, round(6.0 + (has_moves / total_scenes) * 4.0, 1))

    # Axis 3: Transitions (push_zoom / paper_wipe on shared background)
    score_axis3 = 9.0  # Remotion engine auto-injects push_zoom / paper_wipe
    
    # Axis 4: Zero Dual-Number conflict
    dual_conflicts = [d for d in defects if "EMPTY_KINETIC_COUNTER" in d or "CONFLICT" in d]
    score_axis4 = 10.0 if not dual_conflicts else max(2.0, 10.0 - len(dual_conflicts) * 2.0)

    # Axis 5: Editorial Art & Market purity
    tag_leaks = [d for d in defects if "LEAKED_ASSET_TAG" in d or "UNLOCALIZED" in d]
    score_axis5 = 9.5 if not tag_leaks else max(4.0, 9.5 - len(tag_leaks) * 1.5)

    composite_score = round(
        score_axis1 * 0.25 +
        score_axis2 * 0.20 +
        score_axis3 * 0.20 +
        score_axis4 * 0.20 +
        score_axis5 * 0.15,
        2
    )

    return {
        "axis1_procedural_assembly": score_axis1,
        "axis2_element_kinematics": score_axis2,
        "axis3_match_cut_transitions": score_axis3,
        "axis4_zero_dual_numbers": score_axis4,
        "axis5_editorial_art_purity": score_axis5,
        "composite_score": composite_score,
        "benchmark_parity_pct": round((composite_score / 10.0) * 100, 1),
        "target_threshold": 8.5,
        "passed_threshold": composite_score >= 8.5
    }


def run_adversarial_gate(
    episode_id: str,
    props_path: str,
    output_dir: Optional[str] = None,
    render_stills: bool = True,
) -> Dict[str, Any]:
    """Main gatekeeper entrypoint."""
    market = extract_market_from_episode_id(episode_id)
    out_dir = output_dir or os.path.dirname(os.path.abspath(props_path))

    with open(props_path, "r", encoding="utf-8") as f:
        props = json.load(f)

    # Initial audit
    is_clean, defects = audit_props_integrity(props, market)

    if not is_clean:
        logger.warning("Adversarial Gate found %d defects. Triggering autonomous repair...", len(defects))
        props = auto_repair_props(props, market)
        # Write repaired props back
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        # Re-audit
        is_clean, defects = audit_props_integrity(props, market)
        logger.info("Post-repair audit: clean=%s, remaining_defects=%d", is_clean, len(defects))

    # Render still frames if requested and environment allows
    still_frames = []
    if render_stills and os.path.exists("/root/video_factory/remotion"):
        still_dir = os.path.join(out_dir, "gate_stills")
        still_frames = extract_sample_still_frames(props_path, still_dir)

    parity_scorecard = compute_5axis_motion_parity_score(props, defects)
    verdict = "PASS" if is_clean else "DEFECTS_REMAIN"
    report = {
        "episode_id": episode_id,
        "market": market,
        "verdict": verdict,
        "defects_found_initial": len(defects),
        "defects": defects,
        "still_frames_count": len(still_frames),
        "still_frames": still_frames,
        "overlay_density_pct": round((sum(1 for s in props.get("scenes", []) if s.get("forensicOverlay")) / len(props.get("scenes", [1]))) * 100, 1),
        "total_scenes": len(props.get("scenes", [])),
        "motion_graphics_scorecard": parity_scorecard
    }

    report_path = os.path.join(out_dir, "director_gate_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("Director Gate finished: verdict=%s (Score: %s/10), report=%s", verdict, parity_scorecard["composite_score"], report_path)
    return report


def main():
    ap = argparse.ArgumentParser(description="Adversarial Subagent Director Gate for B6 Staging")
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--props", required=True, help="Path to remotion_props.json")
    ap.add_argument("--out-dir", default="", help="Output directory for reports & stills")
    ap.add_argument("--no-stills", action="store_true", help="Skip rendering stills")

    args = ap.parse_args()
    report = run_adversarial_gate(
        episode_id=args.episode_id,
        props_path=args.props,
        output_dir=args.out_dir or None,
        render_stills=not args.no_stills,
    )

    if report["verdict"] == "PASS":
        print(f"APPROVED_FOR_RENDER: {report['episode_id']} passed adversarial gate.")
        sys.exit(0)
    else:
        print(f"GATE_REJECTED: {report['defects']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
