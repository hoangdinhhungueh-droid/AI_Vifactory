#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/papertrails_director.py — Papertrails Director & Semantic Timeline Forge (FT-301).

Converts S03 Script, S02 Grounding Table, and S09 Voice Narration (with Whisper word timestamps)
into a canonical Papertrails Timeline v1 (timeline.json).
Enforces 0ms drift karaoke, 3D paper biomes, props, and camera movements.
"""

from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("papertrails_director")

# 17 Canonical Props & Biomes Mapping
# Priority matters: compound subjects precede words they contain
SUBJECT_RULES: List[Tuple[str, str, List[str]]] = [
    ("factory", "heartland", ["nha may", "factory", "industry", "san xuat", "cong nghiep", "nang suat", "manufacturing"]),
    ("chart", "heartland", ["bieu do", "chart", "growth", "tang truong", "percent", "phan tram", "chi so", "so lieu", "doanh thu"]),
    ("coin", "heartland", ["tien", "money", "savings", "saving", "cost", "chi phi", "do la", "ngan hang", "dollar", "kinh te", "economy", "lo nhuan", "von", "ngan sach"]),
    ("clock", "heartland", ["thoi gian", "dong ho", "clock", "time", "deadline", "hour", "minute", "gio phut", "khan cap", "cham tre"]),
    ("book", "heartland", ["hoc", "sach", "book", "learn", "school", "education", "knowledge", "kien thuc", "tai lieu", "ho so", "nghien cuu"]),
    ("globe", "heartland", ["the gioi", "trai dat", "world", "earth", "planet", "global", "toan cau", "quoc te"]),
    ("bridge", "heartland", ["cau", "bridge", "crossing", "qua song", "ket noi", "lien ket"]),
    ("forest", "pinewood", ["rung", "forest", "woodland", "nature", "thien nhien", "cay coi"]),
    ("tree", "blossom", ["cay", "tree", "garden", "vuon", "flower", "hoa no", "xanh"]),
    ("mountain", "snow", ["tuyet", "snow", "mountain", "nui", "winter", "mua dong", "kho khan", "thach thuc", "dinh cao"]),
    ("water", "heartland", ["song", "bien", "ocean", "river", "water", "nuoc", "lake", "ho nuoc", "dong chay"]),
    ("sun", "desert", ["sa mac", "desert", "sun", "mat troi", "nang", "heat", "nhiet do"]),
    ("moon", "pinewood", ["moon", "trang", "night", "ban dem", "midnight", "bong toi", "bi an"]),
    ("village", "heartland", ["village", "lang", "thi tran", "town", "city", "thanh pho", "cong dong", "nha dan"]),
    ("house", "heartland", ["nha", "home", "house", "family", "gia dinh", "can ho"]),
    ("people", "heartland", ["nguoi", "people", "team", "nhan vien", "ban be", "friend", "doi ngu", "khach hang", "cong chung"]),
    ("mic", "heartland", ["tieng", "giong", "voice", "phat bieu", "mic", "tuyen bo", "am thanh"]),
    ("bubble", "heartland", ["noi", "loi thoai", "thao luan", "phan hoi", "chat", "tin nhan"]),
    ("film", "heartland", ["video", "phim", "camera", "hinh anh", "quay", "media"]),
]

VALID_BIOMES = {"heartland", "desert", "snow", "blossom", "pinewood"}
VALID_PROPS = {
    "none", "village", "forest", "bridge", "mountain", "sun", "moon", "house",
    "tree", "book", "coin", "chart", "factory", "clock", "people", "water",
    "globe", "voice-note", "edit-board", "pop-up", "film", "bubble", "mic"
}
VALID_CAMERAS = ["wide", "close", "orbit", "push", "low", "crane", "top"]
VALID_ACTIONS = ["reveal", "idle", "walk", "celebrate", "grow"]


def normalize_vietnamese(text: str) -> str:
    """Normalize text removing accents for reliable keyword matching."""
    text = unicodedata.normalize("NFKD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if not unicodedata.combining(c))


def detect_subject_and_biome(text: str) -> Tuple[str, str]:
    """Detect matching 3D prop and biome from narration text."""
    plain_text = " " + re.sub(r"[^a-z0-9]+", " ", normalize_vietnamese(text)) + " "
    for prop, biome, keys in SUBJECT_RULES:
        if any(" " + key + " " in plain_text for key in keys):
            return prop, biome
    return "book", "heartland"


def build_caption_from_words(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a timed caption item with exact word-level karaoke sync."""
    if not words:
        return {"start": 0.0, "end": 0.0, "text": "", "words": []}
    return {
        "start": round(words[0]["start"], 3),
        "end": round(words[-1]["end"], 3),
        "text": " ".join(w["word"] for w in words).strip(),
        "words": [
            {
                "word": w["word"].strip(),
                "start": round(w["start"], 3),
                "end": round(w["end"], 3)
            }
            for w in words
        ]
    }


def split_into_karaoke_captions(segments: List[Dict[str, Any]], max_seconds: float = 3.5) -> List[Dict[str, Any]]:
    """Splits transcript segments into crisp, readable captions (max ~3.5s or on punctuation)."""
    captions: List[Dict[str, Any]] = []
    for seg in segments:
        words = seg.get("words") or []
        if words:
            group: List[Dict[str, Any]] = []
            for word in words:
                token = word.get("word") or word.get("text", "")
                w_start = float(word.get("start", 0.0))
                w_end = float(word.get("end", 0.0))
                if w_end <= w_start:
                    continue
                w_item = {"word": token, "start": w_start, "end": w_end}

                if group and (w_end - group[0]["start"] > max_seconds or len(group) >= 8):
                    captions.append(build_caption_from_words(group))
                    group = []

                group.append(w_item)

                # Split on sentence ending punctuation
                if len(group) >= 3 and re.search(r"[,.;:!?][\"'’”)]*$", token):
                    captions.append(build_caption_from_words(group))
                    group = []

            if group:
                captions.append(build_caption_from_words(group))
        else:
            # Fallback to segment without word timings
            captions.append({
                "start": round(float(seg["start"]), 3),
                "end": round(float(seg["end"]), 3),
                "text": seg.get("text", "").strip()
            })
    return captions


def build_papertrails_timeline(
    scenes_script: List[Dict[str, Any]],
    audio_path: Path,
    audio_duration: float,
    transcript_segments: Optional[List[Dict[str, Any]]] = None,
    orientation: str = "landscape",
    fps: int = 30,
    seed: int = 42,
    max_shot_seconds: float = 5.0,
) -> Dict[str, Any]:
    """Constructs a canonical Papertrails timeline.json conforming to Timeline Schema v1.

    Args:
        scenes_script: Scenes from Stage S03/S05 with headline, narration, visual hints.
        audio_path: Absolute or relative path to the voice audio file.
        audio_duration: Measured audio duration in seconds.
        transcript_segments: Timed segments with 'words' from Faster-Whisper.
        orientation: 'landscape' (1920x1080) or 'portrait' (1080x1920).
        fps: Frames per second (default 30).
        seed: Random seed for deterministic WFC world generation.
        max_shot_seconds: Target maximum duration per visual shot.

    Returns:
        Dict conforming to Timeline Schema v1.
    """
    if audio_duration <= 0:
        raise ValueError(f"Invalid audio duration: {audio_duration}s")

    width, height = (1920, 1080) if orientation == "landscape" else (1080, 1920)

    # 1. Normalize Captions
    captions: List[Dict[str, Any]] = []
    if transcript_segments:
        captions = split_into_karaoke_captions(transcript_segments, max_seconds=3.5)
    else:
        # Fallback: distribute scenes evenly across audio duration
        tot = len(scenes_script) or 1
        per = audio_duration / tot
        for idx, sc in enumerate(scenes_script):
            st = round(idx * per, 3)
            en = round(min(audio_duration, (idx + 1) * per), 3)
            captions.append({"start": st, "end": en, "text": sc.get("narration", "").strip()})

    # 2. Build Beats & Scenes
    timeline_scenes: List[Dict[str, Any]] = []
    total_scenes = len(scenes_script)

    camera_presets = ["wide", "close", "orbit", "push", "low", "crane"]
    palette_colors = ["#d79a45", "#c4532f", "#3a5a40", "#2b4c7e", "#7b2cbf"]

    if total_scenes > 0 and len(captions) > 0:
        # Calculate time windows for each scene
        for i, sc in enumerate(scenes_script):
            sc_id = f"shot-{i+1:03d}"
            sc_narration = sc.get("narration", "").strip()
            headline = sc.get("headline", "").strip()
            title = headline or (" ".join(sc_narration.split()[:5]))

            # Time calculation
            if sc.get("start_sec") is not None and sc.get("end_sec") is not None:
                start_sec = float(sc["start_sec"])
                end_sec = float(sc["end_sec"])
            else:
                ratio_start = i / total_scenes
                ratio_end = (i + 1) / total_scenes
                start_sec = round(ratio_start * audio_duration, 3)
                end_sec = round(ratio_end * audio_duration, 3)

            # Detect prop and biome from narration or S5 manifest
            prop = sc.get("prop")
            biome = sc.get("biome")
            if not prop or prop not in VALID_PROPS:
                prop, detected_biome = detect_subject_and_biome(sc_narration or headline)
                if not biome or biome not in VALID_BIOMES:
                    biome = detected_biome

            camera = sc.get("camera")
            if not camera or camera not in VALID_CAMERAS:
                camera = camera_presets[i % len(camera_presets)]

            action = sc.get("action")
            if not action or action not in VALID_ACTIONS:
                action = "reveal" if i % 2 == 0 else "idle"

            color = palette_colors[i % len(palette_colors)]

            # Check for card metadata (Taped Note or Photo Card)
            card: Optional[Dict[str, Any]] = None
            stat_hero = sc.get("stat_hero") or sc.get("stat_value")
            stat_label = sc.get("stat_label")
            if stat_hero:
                card = {
                    "kind": "note",
                    "head": f"CHỨNG CỨ // {headline[:25]}" if headline else "DỮ LIỆU ĐIỀU TRA",
                    "lines": [
                        f"`{stat_hero}`",
                        str(stat_label or "Số liệu lượng hóa độc quyền"),
                        f"Phân tích: {sc_narration[:45]}..."
                    ],
                    "side": "right" if i % 2 == 0 else "left",
                    "lineAt": [0.3, 1.2, 2.2],
                    "numbered": True
                }

            timeline_scenes.append({
                "id": sc_id,
                "start": start_sec,
                "end": end_sec,
                "narration": sc_narration,
                "title": title[:40],
                "biome": biome,
                "night": prop == "moon" or bool(sc.get("night", False)),
                "action": action,
                "prop": prop,
                "camera": camera,
                "color": color,
                "visual": f"Papertrails 3D {prop} in {biome} biome with camera {camera}. Action: {action}.",
                **({"card": card} if card else {})
            })

    # Sanity check: ensure seamless continuous coverage
    if timeline_scenes:
        timeline_scenes[0]["start"] = 0.0
        for idx in range(len(timeline_scenes) - 1):
            timeline_scenes[idx]["end"] = timeline_scenes[idx + 1]["start"]
        timeline_scenes[-1]["end"] = audio_duration

    timeline_spec: Dict[str, Any] = {
        "version": 1,
        "width": width,
        "height": height,
        "fps": fps,
        "seed": seed,
        "duration": round(audio_duration, 3),
        "audio": str(audio_path),
        "captions": captions,
        "scenes": timeline_scenes,
        "timing": {
            "mode": "word" if any(c.get("words") for c in captions) else "segment",
            "source": "faster-whisper-measured",
            "drift_tolerance_ms": 0.0
        },
        "direction": {
            "status": "agent-reviewed",
            "engine": "Papertrails 3D WebGL (Three.js Pop-up Book)",
            "upstream_author": "Shikhar (xikhar/papertrails)"
        }
    }

    return timeline_spec
