#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/timeline_editor_agent.py

AI Senior Post-Production Editor Gate (Timeline Assembly Optimization).
Frontier LLM Director (gpt-6-astra / claude-opus-5-5 via ModelGateway) +
Deterministic Heuristic Safety Gate (Word-Locked Punches, Visual Monotony Breaker, Rule 136 Clean Tags).
Operates as an intelligent editorial layer between B3 Director Plan and B8 Render.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vf.timeline_editor_agent")

PUNCH_KEYWORDS = {
    "fraud", "wire fraud", "money laundering", "stolen", "indicted", "guilty",
    "seized", "conspiracy", "millions", "collapse", "busted", "raid", "fbi",
    "subpoena", "fake", "nominee", "shell company", "crisis", "crash",
    "lừa đảo", "bắt giữ", "niêm phong", "khống", "rửa tiền", "triệu đô", "đột kích",
    "사기", "압수", "구속", "횡령", "유령회사", "사건"
}

VALID_CAMERA_MOVEMENTS = {
    "slow_push_in", "snap_zoom", "slow_pull_out", "cinematic_pan", "macro_tilt",
    "continuous_drift", "seamless_whip_pan", "macro_orbit", "cinematic_orbit", "handheld_shake",
    "dramatic_push", "subtle_drift", "split_whip", "forensic_lock"
}

VALID_TENSION_LEVELS = {"low", "medium", "high", "extreme"}
VALID_TRANSITIONS = {
    "cut", "cross_fade", "continuous_whip", "match_cut",
    "push_zoom", "paper_wipe", "tape_snap", "ink_bleed", "whip_pan_right", "hard_cut", "light_leak", "smash_cut"
}
VALID_MOTION_DIRECTIVES = {
    "dramatic_push", "subtle_drift", "split_whip", "forensic_lock", "counter_rollup", "yellow_marker_highlight"
}


def _load_story_context(episode_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load story context from episode workspace or options."""
    context: Dict[str, Any] = {"story_snippet": "", "beats": {}}
    opts = options or {}

    if opts.get("story_text"):
        context["story_snippet"] = str(opts["story_text"])[:2500]
        return context

    if not episode_id:
        return context

    # Candidate paths for story script
    candidate_paths = [
        Path(f"/var/vf/episodes/{episode_id}/story.txt"),
        Path(f"/var/vf/episodes/{episode_id}/spoken_script.txt"),
        Path(f"workspace/{episode_id}/story.txt"),
        Path(f"workspace/{episode_id}/spoken_script.txt"),
    ]

    for p in candidate_paths:
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
                context["story_snippet"] = content[:3000]
                # Extract beat markers if present
                for idx in range(1, 6):
                    pattern = rf"(?:BEAT\s*{idx}|Beat\s*{idx})[:\s\-]+(.*?)(?=(?:BEAT\s*\d|Beat\s*\d|\Z))"
                    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if m:
                        context["beats"][idx] = m.group(1).strip()[:400]
                break
            except Exception as e:
                logger.debug("[timeline_editor_agent] Error reading %s: %s", p, e)

    # Check for showrunner dossier if present
    dossier_candidates = [
        Path(f"/var/vf/episodes/{episode_id}/showrunner_dossier.json"),
        Path(f"workspace/{episode_id}/showrunner_dossier.json"),
    ]
    for dp in dossier_candidates:
        if dp.exists():
            try:
                dossier_data = json.loads(dp.read_text(encoding="utf-8"))
                context["showrunner_dossier"] = dossier_data
                if dossier_data.get("vision_statement"):
                    context["vision_statement"] = dossier_data["vision_statement"]
                break
            except Exception as e:
                logger.debug("[timeline_editor_agent] Error reading %s: %s", dp, e)

    return context


def llm_timeline_director_review(
    scenes: List[Dict[str, Any]],
    episode_id: Optional[str] = None,
    story_context: Optional[Dict[str, Any]] = None,
    model_override: Optional[str] = None,
    timeout: float = 35.0,
) -> Dict[str, Any]:
    """Invoke Frontier LLM (claude-opus-5-5 / gpt-6-astra) to conduct Senior Director review of timeline.

    Evaluates narrative tension, pacing rhythm, camera flow (continuous drift/whip/orbit),
    and scene transitions before Remotion render.
    Returns structured directorial adjustments with resilient fallback.
    """
    start_time = time.time()
    result_record: Dict[str, Any] = {
        "status": "fallback",
        "model": "heuristic",
        "editorial_rationale": "Default heuristic pacing and continuity applied.",
        "scene_adjustments": [],
        "duration_sec": 0.0,
    }

    try:
        from app.services.model_gateway import get_global_gateway
        gateway = get_global_gateway()
    except Exception as e:
        logger.info("[timeline_editor_agent] ModelGateway unavailable (%s), using heuristic engine", e)
        return result_record

    model = model_override or os.getenv("TIMELINE_DIRECTOR_MODEL", "claude-opus-5-5")
    fallback_model = os.getenv("TIMELINE_DIRECTOR_FALLBACK_MODEL", "gpt-6-astra")

    context = story_context or _load_story_context(episode_id)
    story_snippet = context.get("story_snippet", "")

    # Build concise scene manifest for LLM inspection
    scene_summaries = []
    for i, s in enumerate(scenes):
        dur_f = max(1, round(s.get("durationInFrames", 1)))
        dur_s = round(dur_f / 30.0, 2)
        narration = s.get("narration", "") or s.get("caption", "")
        clean_narration = (narration[:90] + "...") if len(narration) > 90 else narration
        current_cam = s.get("cameraMovement") or (s.get("camera", {}).get("movement") if isinstance(s.get("camera"), dict) else "slow_push_in")
        scene_summaries.append({
            "idx": i,
            "scene_id": s.get("scene_id", f"sc_{i+1:02d}"),
            "dur_sec": dur_s,
            "narration": clean_narration,
            "current_cam": current_cam,
            "overlay": bool(s.get("forensicOverlay") or s.get("forensic_overlay")),
            "has_fg": bool(s.get("foreground")),
        })

    system_prompt = (
        "You are an award-winning Hollywood Documentary Executive Post-Production Film Director "
        "and Senior Colorist/Editor. Your task is to perform the final Director's Cut review of "
        "the mapped scene timeline before master rendering.\n\n"
        "Your Goals:\n"
        "1. Dynamic Pacing & Emotional Curve: Modulate rhythm between slow reflective beats and rapid investigative tension.\n"
        "2. Vox & Veo Style Continuous Motion: Where scenes belong to the same narrative beat, use continuous camera momentum "
        "('continuous_drift', 'macro_orbit', 'cinematic_pan') to eliminate jerky stops.\n"
        "3. High-Impact Reveals: Use 'snap_zoom' or 'seamless_whip_pan' on catalyst revelations and smoking guns.\n"
        "4. Rule 136 Clean Lower-Thirds: Ensure speaker tags are clean ('NAME // ROLE' or 'BEAT X // TITLE'), never file extensions or asset codes.\n\n"
        "Valid Camera Movements:\n"
        "slow_push_in, snap_zoom, slow_pull_out, cinematic_pan, macro_tilt, continuous_drift, seamless_whip_pan, macro_orbit, cinematic_orbit, handheld_shake, dramatic_push, subtle_drift, split_whip, forensic_lock\n\n"
        "Valid Tension Levels: low, medium, high, extreme\n"
        "Valid Transitions: cut, cross_fade, continuous_whip, match_cut, push_zoom, paper_wipe, tape_snap, ink_bleed, whip_pan_right, hard_cut, light_leak, smash_cut\n"
        "Valid Motion Directives: dramatic_push, subtle_drift, split_whip, forensic_lock, counter_rollup, yellow_marker_highlight\n\n"
        "OUTPUT REQUIREMENT: Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "editorial_rationale": "1-2 sentences on your overall directorial vision for this sequence",\n'
        '  "scene_adjustments": [\n'
        '    {\n'
        '      "idx": 0,\n'
        '      "cameraMovement": "snap_zoom",\n'
        '      "tensionLevel": "high",\n'
        '      "transition": "push_zoom",\n'
        '      "motionDirective": "dramatic_push",\n'
        '      "speakerTag": "OPTIONAL CLEAN TITLE // SUBTITLE",\n'
        '      "directorNote": "Immediate hook impact"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    vision_str = f"Showrunner Vision Statement: {context['vision_statement']}\n\n" if context.get("vision_statement") else ""
    user_prompt = (
        f"Episode ID: {episode_id or 'EPISODE'}\n"
        f"{vision_str}"
        f"Story Overview:\n{story_snippet[:1200] if story_snippet else 'Investigative non-fiction docudrama.'}\n\n"
        f"Mapped Scenes Timeline ({len(scenes)} scenes):\n"
        f"{json.dumps(scene_summaries, ensure_ascii=False, indent=2)}\n\n"
        "Review each scene and provide your directorial adjustments in JSON format."
    )

    try:
        logger.info("[timeline_editor_agent] Invoking LLM Director (%s, timeout=%.1fs)...", model, timeout)
        response_text = gateway.call_llm(
            prompt=user_prompt,
            model=model,
            system_prompt=system_prompt,
            max_tokens=3500,
            temperature=0.3,
            timeout=timeout,
            fallback=fallback_model,
        )

        # Parse JSON response
        cleaned_json = response_text.strip()
        json_match = re.search(r"\{.*\}", cleaned_json, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            adjustments = parsed.get("scene_adjustments", [])
            rationale = parsed.get("editorial_rationale", "Director review complete.")

            result_record["status"] = "success"
            result_record["model"] = model
            result_record["editorial_rationale"] = rationale
            result_record["scene_adjustments"] = adjustments
            result_record["duration_sec"] = round(time.time() - start_time, 2)
            logger.info(
                "[timeline_editor_agent] LLM Director (%s) returned %d scene adjustments in %.2fs: %s",
                model, len(adjustments), result_record["duration_sec"], rationale[:80]
            )

            # Persist review artifact if directory available
            if episode_id:
                for out_dir in [Path(f"/var/vf/episodes/{episode_id}"), Path(f"workspace/{episode_id}")]:
                    if out_dir.exists():
                        try:
                            review_path = out_dir / "llm_director_review.json"
                            review_path.write_text(json.dumps(result_record, ensure_ascii=False, indent=2), encoding="utf-8")
                            logger.info("[timeline_editor_agent] Saved review artifact to %s", review_path)
                            break
                        except Exception as write_err:
                            logger.debug("[timeline_editor_agent] Could not save review artifact: %s", write_err)

            return result_record
        else:
            logger.warning("[timeline_editor_agent] LLM returned non-JSON response, using heuristic fallback")
    except Exception as exc:
        logger.warning("[timeline_editor_agent] LLM Director call failed (%s), smoothly falling back to heuristic engine", exc)

    result_record["duration_sec"] = round(time.time() - start_time, 2)
    return result_record


def audit_and_optimize_timeline(
    scenes: list[dict[str, Any]],
    whisper_words: list[dict[str, Any]] | None = None,
    options: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Master entry point for Timeline Assembly optimization.
    
    Coordinates Frontier LLM Director Review (gpt-6-astra / claude-opus-5-5) and
    Deterministic Heuristic Safety Gate (Word-Locked Punches, Visual Monotony Breaker, Rule 136 Clean Tags).
    Transforms raw mapped scenes into an editorially polished, pacing-optimized
    timeline ready for Remotion rendering.
    """
    if not scenes:
        return scenes

    opts = options or {}
    episode_id = opts.get("episode_id")
    enable_llm = opts.get("enable_llm_director", True)
    if os.getenv("DISABLE_LLM_TIMELINE_DIRECTOR", "").lower() in ("1", "true", "yes"):
        enable_llm = False

    max_dead_air_frames = opts.get("max_dead_air_frames", 120)  # 4.0 seconds @ 30fps

    # Step 1: Frontier LLM Director Review (if enabled)
    llm_adjustments_by_idx: Dict[int, Dict[str, Any]] = {}
    if enable_llm and len(scenes) > 0:
        review = llm_timeline_director_review(
            scenes=scenes,
            episode_id=episode_id,
            model_override=opts.get("model"),
            timeout=float(opts.get("timeout_sec", 35.0)),
        )
        for adj in review.get("scene_adjustments", []):
            idx = adj.get("idx")
            if isinstance(idx, int) and 0 <= idx < len(scenes):
                llm_adjustments_by_idx[idx] = adj

    optimized: list[dict[str, Any]] = []
    prev_overlay_type: str | None = None
    consecutive_overlay_count = 0
    word_cursor_ms = 0.0

    for i, s in enumerate(scenes):
        scene = dict(s)
        dur = max(1, round(scene.get("durationInFrames", 1)))
        overlay = scene.get("forensicOverlay") or scene.get("forensic_overlay")

        # Step 2: Apply LLM Director adjustments where specified
        llm_adj = llm_adjustments_by_idx.get(i)
        if llm_adj:
            new_cam = llm_adj.get("cameraMovement")
            if new_cam and new_cam in VALID_CAMERA_MOVEMENTS:
                scene["cameraMovement"] = new_cam
            new_tension = llm_adj.get("tensionLevel")
            if new_tension and new_tension in VALID_TENSION_LEVELS:
                scene["tensionLevel"] = new_tension
            new_trans = llm_adj.get("transition")
            if new_trans and new_trans in VALID_TRANSITIONS:
                scene["transition"] = new_trans
            new_motion = llm_adj.get("motionDirective") or llm_adj.get("motion_directive")
            if new_motion and new_motion in VALID_MOTION_DIRECTIVES:
                scene["motionDirective"] = new_motion
            llm_speaker = llm_adj.get("speakerTag")
            if llm_speaker and isinstance(llm_speaker, str) and llm_speaker.strip():
                scene["speakerTag"] = llm_speaker.strip()
            if llm_adj.get("directorNote"):
                scene["directorNote"] = llm_adj["directorNote"]

        # Step 3: Enforce Rule 136 (Zero-Asset-Leak Clean Speaker Tag)
        tag = scene.get("speakerTag")
        if tag:
            clean_tag = str(tag).strip()
            clean_tag = re.sub(r'\.(png|jpg|jpeg|webp)$', '', clean_tag, flags=re.IGNORECASE)
            clean_tag = re.sub(r'^(ARCHIVE\s*X\s*//\s*|DEFAULT\s*//\s*)', '', clean_tag, flags=re.IGNORECASE)
            scene["speakerTag"] = clean_tag

        # Step 4: Visual Monotony Breaker
        current_type = overlay.get("type") if isinstance(overlay, dict) else None
        if current_type and current_type == prev_overlay_type:
            consecutive_overlay_count += 1
        else:
            consecutive_overlay_count = 1
            prev_overlay_type = current_type

        # Extract market theme for localized labels
        from app.services.editorial_briefing_generator import extract_market_from_episode_id, LOCALIZED_OVERLAY_THEMES
        m_code = extract_market_from_episode_id(episode_id or (options or {}).get("episode_id", ""))
        m_theme = LOCALIZED_OVERLAY_THEMES.get(m_code, LOCALIZED_OVERLAY_THEMES["EN"])

        if consecutive_overlay_count > 2 and isinstance(overlay, dict):
            # Break monotony: Switch third identical scene to contrasting kinetic type
            if current_type == "document_highlight":
                overlay["type"] = "kinetic_counter"
                overlay["title"] = m_theme["counter_title"]
                overlay["badge"] = m_theme["counter_badge"]
                overlay["sfx_cue"] = "stamp_slam"
            elif current_type == "kinetic_counter":
                overlay["type"] = "tactical_map"
                overlay["title"] = m_theme["map_title"]
                overlay["badge"] = m_theme["map_badge"]
                overlay["sfx_cue"] = "radar_ping"
            scene["forensicOverlay"] = overlay
            prev_overlay_type = overlay.get("type")
            consecutive_overlay_count = 1

        # Step 5: Pacing & Dead-Air Elimination
        if dur > max_dead_air_frames and not overlay and not scene.get("statValue") and not scene.get("cameraMovement"):
            # Dead air detected: Inject kinetic focus or subtle camera push
            scene["cameraMovement"] = "snap_zoom"
            scene["tensionLevel"] = "high"
            if not scene.get("speakerTag") and not scene.get("actTitle"):
                scene["speakerTag"] = m_theme["default_speaker"]

        # Step 6: Word-Locked Camera Punch Alignment
        scene_start_ms = word_cursor_ms
        scene_dur_ms = (dur / 30.0) * 1000.0
        scene_end_ms = scene_start_ms + scene_dur_ms

        punches = []
        if whisper_words and isinstance(whisper_words, list):
            for w in whisper_words:
                w_start = float(w.get("start_ms", 0))
                if scene_start_ms <= w_start < scene_end_ms:
                    word_clean = re.sub(r'[^a-zA-Z0-9\s]', '', str(w.get("word", "")).lower().strip())
                    if word_clean in PUNCH_KEYWORDS or any(pk in word_clean for pk in PUNCH_KEYWORDS):
                        frame_offset = max(0, min(dur - 1, round(((w_start - scene_start_ms) / 1000.0) * 30.0)))
                        punches.append({
                            "word": w.get("word"),
                            "frame_offset": frame_offset,
                            "camera": "snap_zoom",
                            "sfx_cue": "stamp_slam"
                        })
                        scene["cameraMovement"] = "snap_zoom"
                        scene["tensionLevel"] = "high"
                        break

        if punches:
            scene["wordLockedPunches"] = punches

        # Step 7: Enable 2.5D Parallax & Cinematic Atmosphere flags
        scene["enableParallax"] = True
        scene["atmosphericLighting"] = True

        word_cursor_ms = scene_end_ms
        optimized.append(scene)

    logger.info(
        "AI Senior Editor optimized %d scenes (LLM Directorial Inputs: %d, Pushes/Parallax active)",
        len(optimized), len(llm_adjustments_by_idx)
    )
    return optimized
