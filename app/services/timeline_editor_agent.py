#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/timeline_editor_agent.py

AI Senior Post-Production Editor Gate (Timeline Assembly Optimization).
Operates as an intelligent editorial layer between B3 Director Plan and B8 Render.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("vf.timeline_editor_agent")

PUNCH_KEYWORDS = {
    "fraud", "wire fraud", "money laundering", "stolen", "indicted", "guilty",
    "seized", "conspiracy", "millions", "collapse", "busted", "raid", "fbi",
    "subpoena", "fake", "nominee", "shell company", "crisis", "crash",
    "lừa đảo", "bắt giữ", "niêm phong", "khống", "rửa tiền", "triệu đô", "đột kích",
    "사기", "압수", "구속", "횡령", "유령회사", "사건"
}


def audit_and_optimize_timeline(
    scenes: list[dict[str, Any]],
    whisper_words: list[dict[str, Any]] | None = None,
    options: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Master entry point for Timeline Assembly optimization.
    
    Transforms raw mapped scenes into an editorially polished, pacing-optimized
    timeline suitable for Remotion rendering.
    """
    if not scenes:
        return scenes

    opts = options or {}
    max_dead_air_frames = opts.get("max_dead_air_frames", 120) # 4.0 seconds @ 30fps

    optimized: list[dict[str, Any]] = []
    prev_overlay_type: str | None = None
    consecutive_overlay_count = 0

    word_cursor_ms = 0.0

    for i, s in enumerate(scenes):
        scene = dict(s)
        dur = max(1, round(scene.get("durationInFrames", 1)))
        narration = scene.get("narration", "") or scene.get("caption", "")
        overlay = scene.get("forensicOverlay") or scene.get("forensic_overlay")

        # 1. Clean Speaker Tag per Rule 136 (Zero-Asset-Leak)
        tag = scene.get("speakerTag")
        if tag:
            clean_tag = str(tag).strip()
            clean_tag = re.sub(r'\.(png|jpg|jpeg|webp)$', '', clean_tag, flags=re.IGNORECASE)
            clean_tag = re.sub(r'^(ARCHIVE\s*X\s*//\s*|DEFAULT\s*//\s*)', '', clean_tag, flags=re.IGNORECASE)
            scene["speakerTag"] = clean_tag

        # 2. Visual Monotony Breaker
        current_type = overlay.get("type") if isinstance(overlay, dict) else None
        if current_type and current_type == prev_overlay_type:
            consecutive_overlay_count += 1
        else:
            consecutive_overlay_count = 1
            prev_overlay_type = current_type

        if consecutive_overlay_count > 2 and isinstance(overlay, dict):
            # Break monotony: Switch third identical scene to contrasting kinetic type
            if current_type == "document_highlight":
                overlay["type"] = "kinetic_counter"
                overlay["title"] = "AUDIT DISCREPANCY // SYSTEMIC VARIANCE"
                overlay["badge"] = "CRITICAL FINDING"
                overlay["sfx_cue"] = "stamp_slam"
            elif current_type == "kinetic_counter":
                overlay["type"] = "tactical_map"
                overlay["title"] = "GEOGRAPHIC TRACE // LOCATION RECON"
                overlay["badge"] = "SURVEILLANCE"
                overlay["sfx_cue"] = "radar_ping"
            scene["forensicOverlay"] = overlay
            prev_overlay_type = overlay.get("type")
            consecutive_overlay_count = 1

        # 3. Pacing & Dead-Air Elimination
        if dur > max_dead_air_frames and not overlay and not scene.get("statValue"):
            # Dead air detected: Inject kinetic focus or subtle camera push
            scene["cameraMovement"] = "snap_zoom"
            scene["tensionLevel"] = "high"
            if not scene.get("speakerTag") and not scene.get("actTitle"):
                scene["speakerTag"] = "CRITICAL EVIDENCE // FORENSIC TIMELINE"

        # 4. Word-Locked Camera Punch Alignment
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

        # 5. Enable 2.5D Parallax & Cinematic Atmosphere flags
        scene["enableParallax"] = True
        scene["atmosphericLighting"] = True

        word_cursor_ms = scene_end_ms
        optimized.append(scene)

    logger.info("AI Senior Editor optimized %d scenes (Pacing & Pushes active)", len(optimized))
    return optimized
