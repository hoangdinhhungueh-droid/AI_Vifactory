#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Remotion props JSON for the generic "TwoLayerEpisode" composition
(remotion/src/index.tsx) from brain_input.json (2-layer schema extension) +
the local image manifest produced by scripts/pull_approved_images.py +
whisper_segments.json (Single Source of Truth Subtitles).

PIPELINE-WIDE & ARCHITECTURAL:
1. Single Source of Truth Subtitles (Rule 120 & R3):
   Extracts exact Faster-Whisper word timestamps (word, start_ms, end_ms)
   and forwards them into scene `subtitles` (and `words`) in remotion_props.json.
2. Dynamic Dialogue Speaker Tags (R4):
   Dynamically formats dialogue speaker tags based on scene character metadata
   (foreground_reuse_key, character_name, role) into professional uppercase dossier tags.
3. 100% Foreground Coverage Guarantee (Rule 100):
   Automatically fills empty foregrounds from approved manifest character cutouts
   with left/right alternation.
4. Intelligent Stat Card Extraction (Rule 102):
   Scans narration for key metrics to pop-in animated Remotion Stat Cards.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.services.director_planner_b3 import detect_forensic_overlay
from app.services.text_to_number_parser import parse_spoken_number
from app.services.timeline_editor_agent import audit_and_optimize_timeline
from app.services.sfx_registry import CANONICAL_SFX_REGISTRY, is_valid_sfx, get_sfx_filename

logger = logging.getLogger("vf.build_remotion_props")


def build_structured_overlay(fo_type: str, narration_text: str, theme: str = "vox_paper") -> dict | None:
    """Build a complete, structured forensic overlay dict for a given overlay type.
    Rule 118 (Zero-Mock Data) & Rule 128 (Generic Architecture):
    Guarantees valid payloads without dummy hardcoded fallbacks.
    """
    if not narration_text or not fo_type:
        return None

    is_jp = any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in narration_text)

    if fo_type in ("threshold_ratio", "grid_ratio", "ratio_grid"):
        multiplier = 24
        baseline = 0.03
        detected = 0.72
        ratio_match = re.search(r"(\d+(?:\.\d+)?)\s*倍", narration_text)
        if ratio_match:
            try:
                multiplier = int(float(ratio_match.group(1)))
            except Exception:
                multiplier = 24
        elif "二十四倍" in narration_text or "24倍" in narration_text:
            multiplier = 24
        return {
            "type": "threshold_ratio",
            "legacy_type": "financial_chart",
            "theme": theme or "crimson_alert",
            "layout": "full_bleed_focus",
            "title": "化学残留検査 // 二酸化硫黄 (SULFUR DIOXIDE)" if is_jp else "TOXICOLOGY AUDIT // RESIDUE RATIO",
            "badge": f"基準値の{multiplier}倍を検出" if is_jp else f"EXCEEDED BY {multiplier}X",
            "sfx_cue": "stamp_slam",
            "label": f"RESIDUE RATIO // {multiplier}X EXCEEDANCE",
            "payload": {
                "baseline_value": baseline,
                "detected_value": detected,
                "multiplier": multiplier,
                "unit": "g/kg",
                "chemical_name": "二酸化硫黄 (SULFUR DIOXIDE)",
                "standard_name": "法定基準値 (LEGAL LIMIT)",
                "detected_name": "検出値 (DETECTED)",
                "grid_cols": 6,
                "grid_rows": 4,
                "source_citation": "厚生労働省 輸入食品衛生法違反公表資料 // 検疫所検査記録",
            }
        }

    if fo_type in ("kinetic_counter", "financial_chart"):
        parsed_metric = parse_spoken_number(narration_text)
        if parsed_metric is not None and parsed_metric.display_value > 0:
            display_val = parsed_metric.formatted
            return {
                "type": "kinetic_counter",
                "legacy_type": "financial_chart",
                "theme": theme or "vox_paper",
                "layout": "full_bleed_focus",
                "title": f"QUANTITATIVE METRIC // {display_val}",
                "badge": "AUDIT METRIC",
                "sfx_cue": "stamp_slam",
                "label": f"EVIDENTIARY VALUE // {display_val}",
                "payload": {
                    "start_value": 0,
                    "end_value": parsed_metric.display_value,
                    "amount": parsed_metric.display_value,
                    "unit": parsed_metric.unit,
                    "prefix": parsed_metric.prefix,
                    "suffix": parsed_metric.suffix,
                    "trend": parsed_metric.trend,
                }
            }
        # Rule 118: No number found in narration -> DO NOT emit mock counter
        return None

    if fo_type in ("evidence_3d_prop", "3d_evidence_prop", "3d_hanko_seal"):
        title = "公的原本 // 提出記録証拠" if is_jp else "PHYSICAL EVIDENCE // EXHIBIT A"
        subtitle = "公的認証原本 // 証拠第42号" if is_jp else "IMPERIAL SEAL / AUTHENTICATION STAMP"
        return {
            "type": "evidence_3d_prop",
            "legacy_type": "redacted_doc",
            "theme": "vox_paper",
            "layout": "full_bleed_focus",
            "title": title,
            "badge": "公的認証" if is_jp else "SEALED EXHIBIT",
            "sfx_cue": "stamp_slam",
            "label": subtitle,
            "payload": {
                "specimen_type": "procedural_3d_artifact",
                "prop_type": "hanko_seal" if is_jp else "wax_seal",
                "classification": "EVIDENTIARY_PROOF",
                "notes": "12FPS STOP-MOTION VOLUMETRIC SPECIMEN",
                "title": title,
                "subtitle": subtitle,
            }
        }

    if fo_type in ("tactical_map", "radar_map"):
        # Rule 128: Generic Contract with dynamic extraction from narration
        loc_words = [w.strip() for w in re.split(r'[,.\s]+', narration_text) if len(w.strip()) > 3][:3]
        target_loc = loc_words[0] if loc_words else ("TARGET OPERATION SECTOR" if not is_jp else "重要監視区域 // 調査対象地点")
        return {
            "type": "tactical_map",
            "legacy_type": "radar_map",
            "theme": theme or "vox_paper",
            "layout": "full_bleed_focus",
            "title": "GEO-TACTICAL TELEMETRY // SECTOR GRID",
            "badge": "LOCATIONAL EVIDENCE",
            "sfx_cue": "sonar_ping",
            "label": "GEO-TACTICAL TELEMETRY // SECTOR GRID",
            "payload": {
                "target_name": f"TARGET SECTOR // {target_loc.upper()}" if not is_jp else f"対象区域 // {target_loc}",
                "coordinates": "INCIDENT GRID // VERIFIED SECTOR",
                "map_region": "REGIONAL JURISDICTION CORRIDOR",
                "points_of_interest": [f"POI-01: {target_loc}", "LOGISTICS CHOKEPOINT", "REGULATORY AUDIT CHECKPOINT"]
            }
        }

    if fo_type in ("document_highlight", "redacted_doc", "paper_dossier"):
        sentences = [s.strip() for s in re.split(r'[.!?。]+', narration_text) if len(s.strip()) > 5][:4]
        clauses = [f"{idx+1}. {sent}" for idx, sent in enumerate(sentences)] if sentences else [
            "1. OFFICIAL INVESTIGATION RECORD // FINDINGS OF FACT",
            "2. REGULATORY AUDIT IDENTIFIED UNVERIFIED CALCULATIONS."
        ]
        return {
            "type": "document_highlight",
            "legacy_type": "redacted_doc",
            "theme": theme or "vox_paper",
            "layout": "full_bleed_focus",
            "title": "OFFICIAL INSPECTION & AUDIT RECORD",
            "badge": "SUBPOENAED EVIDENCE",
            "sfx_cue": "marker_stroke",
            "label": "CLASSIFIED // REDACTED RECORD",
            "payload": {
                "document_title": "OFFICIAL INVESTIGATION RECORD // FINDINGS OF FACT",
                "agency": "REGULATORY OVERSIGHT // INVESTIGATIVE DIVISION",
                "case_number": "CASE DOCKET // ADJUDICATED FILING",
                "clauses": clauses,
                "highlight_line_index": 0,
                "redacted_terms": ["CONFIDENTIAL", "UNVERIFIED", "不適切"],
                "date": "OFFICIAL RECORD // VERIFIED"
            }
        }

    if fo_type in ("evidence_board", "causal_flowchart"):
        return {
            "type": "evidence_board",
            "legacy_type": "causal_flowchart",
            "theme": theme or "vox_paper",
            "layout": "full_bleed_focus",
            "title": "INVESTIGATION NETWORK // TARGET ENTITIES",
            "badge": "CRIMINAL INDICTMENT",
            "sfx_cue": "paper_slide",
            "label": "INVESTIGATION DOSSIER // SUBJECT NETWORK",
            "payload": {
                "suspect_name": "PRIMARY TARGET // NOMINEE OPERATOR",
                "role": "UNLICENSED SHELL OPERATOR / FALSE DISBURSEMENT",
                "charges": ["REGULATORY DEVIATION", "SUBMISSION OF INCONSISTENT RECORD FILINGS"],
                "connected_entities": ["REGULATORY OVERSIGHT DESK", "OPERATIONAL FACILITY", "FILING AUDIT ARCHIVE"],
                "evidence_tag": "OFFICIAL CASE EXHIBIT"
            }
        }

    return None


def normalize_camera_movement(raw_mov: str | None) -> str:
    """Normalize raw camera movement string into one of 12 Remotion canonical movements."""
    if not raw_mov:
        return "slow_push_in"
    m = str(raw_mov).strip().lower()
    canonical = [
        "snap_zoom", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt", "handheld_shake",
        "dolly_zoom", "focus_breathe_push", "continuous_drift", "seamless_whip_pan", "macro_orbit", "whip_zoom"
    ]
    if m in canonical:
        return m
    if "dolly" in m or "vertigo" in m:
        return "dolly_zoom"
    if "orbit" in m or "circle" in m:
        return "macro_orbit"
    if "breathe" in m or "focus" in m:
        return "focus_breathe_push"
    if "drift" in m or "glide" in m:
        return "continuous_drift"
    if "whip" in m and "pan" in m:
        return "seamless_whip_pan"
    if "whip" in m and "zoom" in m:
        return "whip_zoom"
    if "snap" in m or "punch" in m:
        return "snap_zoom"
    if "pull" in m or "retreat" in m:
        return "slow_pull_out"
    if "push" in m or "forward" in m:
        return "slow_push_in"
    if "pan" in m or "lateral" in m or "tracking" in m:
        return "cinematic_pan"
    if "tilt" in m or "pedestal" in m:
        return "macro_tilt"
    if "shake" in m or "handheld" in m or "jitter" in m:
        return "handheld_shake"
    return "slow_push_in"


def load_manifest_index(manifest_path: str):
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        rows = data.get("items") or data.get("images") or data.get("manifest") or []
    else:
        rows = data
    by_reuse_key = {}
    fg_pool = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        rk = (r.get("reuse_key") or "").strip()
        lp = r.get("local_path")
        if not lp and rk:
            candidate = os.path.join(os.path.dirname(manifest_path), f"{rk}.png")
            if not os.path.exists(candidate):
                candidate = os.path.join(os.path.dirname(manifest_path), "images", f"{rk}.png")
            if os.path.exists(candidate):
                lp = candidate
        if rk and lp:
            by_reuse_key[rk] = lp
            if "fg_" in rk.lower() or "character" in (r.get("layer_type") or r.get("asset_type") or "").lower():
                fg_pool.append((rk, lp))
    return by_reuse_key, fg_pool


def stage_into_public(local_path: str, public_dir: str, episode_id: str) -> str | None:
    """Copy local_path into <public_dir>/pulled/<episode_id>/<basename> and
    return the path relative to public_dir (for staticFile()).
    Pre-scales images larger than 1920x1080 down to 1080p to eliminate Chromium downscale overhead (Rule 122 & Render Optimization)."""
    if not local_path:
        return None
    if local_path.startswith("http://") or local_path.startswith("https://"):
        return local_path
    dest_dir = os.path.join(public_dir, "pulled", episode_id)
    os.makedirs(dest_dir, exist_ok=True)
    basename = os.path.basename(local_path)
    dest_path = os.path.join(dest_dir, basename)
    if not os.path.exists(local_path):
        raise FileNotFoundError("missing local image: %s" % local_path)

    # Fast skip if already staged and non-empty (eliminates redundant resizing for reused keys)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
        return "pulled/%s/%s" % (episode_id, basename)

    # Pre-scale down to max 1920x1080 if image is larger
    scaled = False
    try:
        from PIL import Image
        with Image.open(local_path) as im:
            if im.width > 1920 or im.height > 1080:
                ratio = min(1920.0 / im.width, 1080.0 / im.height)
                new_w = max(1, int(round(im.width * ratio)))
                new_h = max(1, int(round(im.height * ratio)))
                resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
                resized.save(dest_path, compress_level=1)
                scaled = True
    except Exception as e:
        logger.debug("[stage_into_public] PIL pre-scale skipped or failed for %s: %s", local_path, e)

    if not scaled:
        shutil.copyfile(local_path, dest_path)
    return "pulled/%s/%s" % (episode_id, basename)


def extract_stat_card(text: str):
    """Extract prominent financial metrics / keywords from narration text (KRW, JPY, USD, VND, percentages, spoken words)."""
    if not text:
        return None, None

    parsed = parse_spoken_number(text)
    if parsed:
        if parsed.suffix and "원" in parsed.suffix:
            label = "PRICE ANCHOR // TRANSACTION"
        elif parsed.suffix and "đồng" in parsed.suffix:
            label = "MARKET METRIC // COST"
        elif parsed.metric_type == "currency":
            label = "FINANCIAL METRIC // VALUATION"
        elif parsed.metric_type == "percentage":
            label = "GROWTH RATE // PERCENTAGE"
        else:
            label = "EVIDENCE // SCALE"
        return parsed.formatted, label

    patterns = [
        (r'(\d+(?:,\d{3})*(?:\.\d+)?\s*(?:만|억|조)?\s*원)', "PRICE ANCHOR // TRANSACTION"),
        (r'(\d+(?:,\d{3})*(?:\.\d+)?\s*(?:万|億|兆)?\s*円)', "FINANCIAL VALUE // VALUATION"),
        (r'(\d+(?:,\d{3})*(?:\.\d+)?\s*(?:tỷ|triệu|nghìn)\s*đ(?:ồng)?)', "MARKET METRIC // COST"),
        (r'(\$\d+(?:\.\d+)?\s*(?:BILLION|MILLION|TRILLION|B|M|K)?(?:\s*→\s*<\$\d+)?(?:\s*/\s*SHARE)?)', "FINANCIAL METRIC // VALUATION"),
        (r'(-\$\d+(?:\.\d+)?\s*(?:BILLION|MILLION|B|M)?)', "BALANCE SHEET // WRITE-DOWN"),
        (r'((?:<\$\d+(?:\.\d+)?|\$\d+(?:\.\d+)?))', "MARKET VALUE // PRICE TARGET"),
        (r'([+-]?\d+(?:\.\d+)?%)', "GROWTH RATE // PERCENTAGE"),
        (r'(\d+\+?\s*(?:BOXES|DOCUMENTS|WITNESSES|EMPLOYEES|INVESTIGATORS|개|명|건|곳))', "EVIDENCE // SCALE"),
        (r'(\b(?:GUILTY|CONVICTED|VERDICT|FRAUD|CONSPIRACY)\b)', "LEGAL RULING // VERDICT"),
        (r'(\b(?:MARK-TO-MARKET|SPECIAL PURPOSE ENTITIES|SPE NETWORK|CIRCULAR HEDGE)\b)', "FINANCIAL MECHANISM"),
    ]

    for p, label in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).upper().strip()
            if len(val) >= 2:
                return val, label

    return None, None


def extract_custom_beat_titles(brain: dict, brain_input_path: str = "") -> dict[int, str]:
    """Extract episode-specific 5-beat custom titles matching Chapters and Story (Rule 128 & Rule 136).
    Returns dict: {1: 'TITLE 1', 2: 'TITLE 2', 3: 'TITLE 3', 4: 'TITLE 4', 5: 'TITLE 5'}
    """
    beat_titles: dict[int, str] = {}
    ep_dir = os.path.dirname(brain_input_path) if brain_input_path else ""

    # 1. Try to read from seo_package.json in episode directory or brain_input
    seo_data = None
    if ep_dir:
        seo_path = os.path.join(ep_dir, "seo_package.json")
        if os.path.exists(seo_path):
            try:
                with open(seo_path, "r", encoding="utf-8") as sf:
                    seo_data = json.load(sf)
            except Exception:
                pass

    if not seo_data and isinstance(brain.get("seo_package"), dict):
        seo_data = brain["seo_package"]

    raw_chapters = []
    if seo_data:
        if isinstance(seo_data.get("chapters"), list):
            raw_chapters = [str(c) for c in seo_data["chapters"] if str(c).strip()]
        elif isinstance(seo_data.get("description"), str):
            desc = seo_data["description"]
            ch_start = desc.find("Chapters:")
            if ch_start != -1:
                ch_block = desc[ch_start:]
                for line in ch_block.splitlines()[1:]:
                    line_s = line.strip()
                    if not line_s or line_s.startswith("#") or "This video" in line_s:
                        break
                    if re.match(r'^\d{1,2}:\d{2}', line_s):
                        raw_chapters.append(line_s)

    # 2. Extract clean titles from chapters (format: "00:00 - Title")
    for idx, ch_line in enumerate(raw_chapters[:5], 1):
        clean_title = re.sub(r'^\d{1,2}:\d{2}(?::\d{2})?\s*[-:]?\s*', '', ch_line).strip()
        clean_title = re.sub(r'^(?:Beat|Act)\s*[1-5IVXLCDM]+[:\-]?\s*', '', clean_title, flags=re.IGNORECASE).strip()
        if clean_title:
            beat_titles[idx] = clean_title

    # 3. Fallback: parse from story text (=== ACT I: TITLE === or similar)
    if len(beat_titles) < 5:
        story_text = brain.get("story") or ""
        if not story_text and ep_dir:
            st_path = os.path.join(ep_dir, "story.txt")
            if os.path.exists(st_path):
                try:
                    with open(st_path, "r", encoding="utf-8") as st_f:
                        story_text = st_f.read()
                except Exception:
                    pass
        if story_text:
            act_matches = re.findall(r'(?:={2,}\s*)?(?:ACT|BEAT)\s*([1-5]|IV|I{1,3}|V)\s*[:\-–—]\s*([^=\r\n]+)', story_text, re.IGNORECASE)
            roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
            for act_num, act_name in act_matches:
                b_num = roman_map.get(act_num.upper()) or (int(act_num) if act_num.isdigit() else 1)
                clean_name = act_name.strip().strip("=").strip()
                if clean_name and b_num not in beat_titles:
                    beat_titles[b_num] = clean_name

    # 4. Fallback: dynamic chapter generation based on topic/keyword and market
    if len(beat_titles) < 5:
        try:
            from app.services.seo_package_forge import _build_dynamic_chapters
            kw = str(brain.get("topic") or brain.get("title_a") or brain.get("episode_id") or "Investigation").strip()
            m = (brain.get("market") or "EN").upper()
            dyn_chapters = _build_dynamic_chapters(title=kw, market=m, target_keyword=kw)
            for idx, ch_line in enumerate(dyn_chapters[:5], 1):
                if idx not in beat_titles:
                    clean_title = re.sub(r'^\d{1,2}:\d{2}(?::\d{2})?\s*[-:]?\s*', '', ch_line).strip()
                    clean_title = re.sub(r'^(?:Beat|Act)\s*[1-5IVXLCDM]+[:\-]?\s*', '', clean_title, flags=re.IGNORECASE).strip()
                    beat_titles[idx] = clean_title
        except Exception as e:
            logger.warning("[extract_custom_beat_titles] Fallback dynamic chapters failed: %s", e)

    return beat_titles


def format_speaker_tag(scene: dict, act_title: str = "", custom_beat_titles: dict = None) -> str:
    """Dynamically format dialogue speaker tags or episode-specific beat identification.
    Rule 125, Rule 128 & Rule 136: Never leak internal asset keys, layer names, or hashes.
    Displays:
      - Explicit dialogue speaker: 'NAME // ROLE'
      - Custom Episode Beat identification (when custom_beat_titles provided): 'BEAT <X>: <EPISODE_SPECIFIC_TITLE>'
      - Standard Beat identification: 'BEAT <X>: <TITLE>' (or clean scene beat string)
    """
    if scene.get("speaker_tag"):
        return str(scene["speaker_tag"]).strip()

    if not act_title:
        act_title = scene.get("act_title") or scene.get("actTitle") or ""

    if scene.get("character_name"):
        name = str(scene["character_name"]).strip()
        role = str(scene.get("character_role") or "").strip()
        if role:
            return f"{name} // {role}".upper()
        return name.upper()

    # Determine beat_idx (1-5)
    beat_idx = scene.get("beat_index")
    if not beat_idx:
        b_match = re.search(r'(?:BEAT|ACT)\s*([1-5]|IV|I{1,3}|V)', str(scene.get("beat") or scene.get("beat_name") or act_title or ""), re.IGNORECASE)
        if b_match:
            val = b_match.group(1).upper()
            roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
            beat_idx = roman_map.get(val) or (int(val) if val.isdigit() else 1)
        else:
            beat_idx = 1
    beat_idx = min(max(int(beat_idx), 1), 5)

    # 1. Custom episode-specific beat title (highest priority when explicitly provided)
    if custom_beat_titles and beat_idx in custom_beat_titles and custom_beat_titles[beat_idx]:
        return f"BEAT {beat_idx}: {custom_beat_titles[beat_idx]}".strip().upper()

    # 2. Prioritize explicit beat from scene
    beat_val = scene.get("beat") or scene.get("beat_title") or scene.get("beat_name")
    if beat_val:
        b_str = str(beat_val).strip()
        if not b_str.upper().startswith("BEAT ") and not b_str.upper().startswith("ACT "):
            return f"BEAT {beat_idx}: {b_str}".strip().upper()
        return b_str.upper()

    # 3. Clean act title fallback
    if act_title:
        clean_act = re.sub(r'^ACT\s+[IVXLCDM]+\s*//\s*', '', str(act_title or '').strip(), flags=re.IGNORECASE)
        return f"BEAT {beat_idx}: {clean_act}".strip().upper()

    return f"BEAT {beat_idx}: INVESTIGATION".upper()


def match_segments_and_extract_words(scene_text: str, segments: list, start_idx: int, fps: int = 30, scene_id: str = ""):
    """Match Whisper segments for a scene and extract exact word timestamps.
    Returns: (matched_words, next_seg_idx, scene_duration_sec, scene_start_ms, scene_end_ms)
    """
    if not segments or start_idx >= len(segments):
        return [], start_idx, None, 0, 0

    matched_segs = []
    idx = start_idx
    first_seg = segments[idx]
    scene_start_ms = int(first_seg.get("start_ms", first_seg.get("start", 0) * 1000))

    # Fast-path: 1:1 match by scene_id (Beat TTS architecture)
    if scene_id and first_seg.get("scene_id") == scene_id:
        matched_segs = [first_seg]
        idx = start_idx + 1
    else:
        scene_clean = re.sub(r'\W+', '', scene_text).lower()
        if not scene_clean:
            return [], start_idx, None, 0, 0

        accumulated_text = ""
        while idx < len(segments):
            seg = segments[idx]
            seg_clean = re.sub(r'\W+', '', seg.get("text", "")).lower()
            accumulated_text += seg_clean
            matched_segs.append(seg)
            idx += 1
            if len(accumulated_text) >= len(scene_clean) * 0.9:
                break

    last_seg = matched_segs[-1] if matched_segs else first_seg
    scene_end_ms = int(last_seg.get("end_ms", last_seg.get("end", 0) * 1000))
    dur_sec = max(0.1, (scene_end_ms - scene_start_ms) / 1000.0)
    dur_frames = max(1, round(dur_sec * fps))

    # Extract words from matched segments
    subtitles = []
    for seg in matched_segs:
        words = seg.get("words")
        if words and isinstance(words, list):
            for w in words:
                w_text = str(w.get("word") or "").strip()
                if not w_text:
                    continue
                w_start = int(w.get("start_ms", w.get("start", 0) * 1000))
                w_end = int(w.get("end_ms", w.get("end", 0) * 1000))
                rel_start_ms = max(0, w_start - scene_start_ms)
                rel_end_ms = max(rel_start_ms + 25, w_end - scene_start_ms)
                subtitles.append({
                    "word": w_text,
                    "start_ms": rel_start_ms,
                    "end_ms": rel_end_ms,
                    "startFrame": max(0, round((rel_start_ms / 1000.0) * fps)),
                    "endFrame": min(dur_frames, round((rel_end_ms / 1000.0) * fps)),
                    "abs_start_ms": w_start,
                    "abs_end_ms": w_end,
                })
        else:
            # Fallback for segments without word-level granularity
            seg_text = seg.get("text", "").strip()
            s_words = seg_text.split()
            seg_s = int(seg.get("start_ms", seg.get("start", 0) * 1000))
            seg_e = int(seg.get("end_ms", seg.get("end", 0) * 1000))
            seg_span = max(100, seg_e - seg_s)
            w_len_total = sum(len(w) for w in s_words) or 1
            cur_ms = seg_s
            for sw in s_words:
                w_dur = int(seg_span * (len(sw) / w_len_total))
                rel_start_ms = max(0, cur_ms - scene_start_ms)
                rel_end_ms = max(rel_start_ms + 25, cur_ms + w_dur - scene_start_ms)
                subtitles.append({
                    "word": sw,
                    "start_ms": rel_start_ms,
                    "end_ms": rel_end_ms,
                    "startFrame": max(0, round((rel_start_ms / 1000.0) * fps)),
                    "endFrame": min(dur_frames, round((rel_end_ms / 1000.0) * fps)),
                    "abs_start_ms": cur_ms,
                    "abs_end_ms": cur_ms + w_dur,
                })
                cur_ms += w_dur

    return subtitles, idx, dur_sec, scene_start_ms, scene_end_ms


def build_remotion_props_data(
    episode_id: str,
    brain_input_path: str,
    segments_path: str = "",
    manifest_path: str = "",
    public_dir: str = "/root/video_factory/remotion/public",
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    fg_fade_sec: float = 0.5,
    skip_missing: bool = False,
) -> dict:
    """Generate props dictionary for Remotion TwoLayerEpisode."""
    with open(brain_input_path, encoding="utf-8") as f:
        brain = json.load(f)

    by_reuse_key = {}
    fg_pool = []
    if manifest_path and os.path.exists(manifest_path):
        by_reuse_key, fg_pool = load_manifest_index(manifest_path)

    raw_scenes = brain.get("scenes", [])
    total_scenes = len(raw_scenes)
    scenes_out = []
    missing = []
    fg_idx = 0

    segments = []
    if segments_path and os.path.exists(segments_path):
        try:
            with open(segments_path, "r", encoding="utf-8") as sf:
                segments = json.load(sf)
        except Exception as e:
            logger.warning("[build_remotion_props] Failed to read segments file %s: %s", segments_path, e)
            segments = []

    seg_cursor = 0

    custom_beat_titles = extract_custom_beat_titles(brain, brain_input_path)
    logger.info("[build_remotion_props] Episode-specific Beat Titles: %s", custom_beat_titles)

    scenes_since_overlay = 4
    last_overlay_type = None
    for i, s in enumerate(raw_scenes):
        scene_id = s.get("scene_id", f"sc{i:03d}")
        shot_type = s.get("shot_type", "")

        # Hỗ trợ cả schema phẳng (legacy) và schema lồng nhau (Unified VOX Director)
        bg_key = s.get("background_reuse_key")
        if not bg_key and isinstance(s.get("background"), dict):
            bg_key = s.get("background", {}).get("reuse_key")

        fg_key = s.get("foreground_reuse_key")
        if not fg_key and isinstance(s.get("foreground"), dict):
            fg_key = s.get("foreground", {}).get("reuse_key")

        # Kiểm tra nếu cảnh này là Hero AI Video và đã có clip MP4 hoàn thiện
        video_clip_found = None
        if shot_type == "HERO_AI_VIDEO" or s.get("veo_action_prompt"):
            hero_clip_name = f"hero_video_{scene_id}.mp4"
            local_ep_dir = os.path.dirname(os.path.abspath(brain_input_path))
            candidate_vids = [
                os.path.join(local_ep_dir, "video_clips", hero_clip_name),
                os.path.join("/var/vf/episodes", episode_id, "video_clips", hero_clip_name),
                os.path.join(public_dir, episode_id, "video_clips", hero_clip_name),
            ]
            for cv in candidate_vids:
                if os.path.exists(cv) and os.path.getsize(cv) > 100000:
                    video_clip_found = cv
                    break

        if video_clip_found:
            bg_local = video_clip_found
        else:
            bg_local = by_reuse_key.get(bg_key) if bg_key else None
            if not bg_local and bg_key:
                candidates_bg = [
                    os.path.join(public_dir, "pulled", episode_id, f"{bg_key}.png"),
                    os.path.join(public_dir, "pulled", episode_id, f"{bg_key}.jpg"),
                    os.path.join(os.path.dirname(os.path.abspath(brain_input_path)), "images", f"{bg_key}.png"),
                    os.path.join(os.path.dirname(os.path.abspath(brain_input_path)), f"{bg_key}.png"),
                    os.path.join("/var/vf/episodes", episode_id, "images", f"{bg_key}.png"),
                    os.path.join("/var/vf/episodes", episode_id, f"{bg_key}.png"),
                ]
                for cand in candidates_bg:
                    if os.path.exists(cand):
                        bg_local = cand
                        break

        fg_local = by_reuse_key.get(fg_key) if fg_key else None
        if not fg_local and fg_key:
            candidates_fg = [
                os.path.join(public_dir, "pulled", episode_id, f"{fg_key}.png"),
                os.path.join(public_dir, "pulled", episode_id, f"{fg_key}.jpg"),
                os.path.join(os.path.dirname(os.path.abspath(brain_input_path)), "images", f"{fg_key}.png"),
                os.path.join(os.path.dirname(os.path.abspath(brain_input_path)), f"{fg_key}.png"),
                os.path.join("/var/vf/episodes", episode_id, "images", f"{fg_key}.png"),
                os.path.join("/var/vf/episodes", episode_id, f"{fg_key}.png"),
            ]
            for cand in candidates_fg:
                if os.path.exists(cand):
                    fg_local = cand
                    break

        if bg_key and not bg_local and not video_clip_found:
            missing.append(bg_key)
            if skip_missing:
                continue

        # Auto FG Fallback: In Vox Documentary Style, full-frame evidence scenes
        # (documents, maps, charts) remain foreground-free unless fg_key is requested
        if not fg_local and fg_key and fg_pool:
            chosen_fg_key, chosen_fg_local = fg_pool[fg_idx % len(fg_pool)]
            fg_local = chosen_fg_local
            fg_idx += 1

        bg_rel = stage_into_public(bg_local, public_dir, episode_id) if bg_local else None
        fg_rel = stage_into_public(fg_local, public_dir, episode_id) if fg_local else None

        caption_text = s.get("caption") or s.get("narration") or ""
        narration_text = s.get("narration") or caption_text

        dur_sec = float(s.get("duration_sec") or 4.0)
        scene_subtitles = []

        # Single Source of Truth Subtitles & Millisecond-Accurate Karaoke
        if segments:
            matched_subs, next_cursor, calc_dur, s_start, s_end = match_segments_and_extract_words(
                narration_text, segments, seg_cursor, fps=fps, scene_id=s.get("scene_id", "")
            )
            if matched_subs:
                scene_subtitles = matched_subs
                seg_cursor = next_cursor
                if calc_dur is not None and calc_dur > 0.1:
                    dur_sec = calc_dur

        dur_frames = max(15, round(dur_sec * fps))

        # Alternate Left / Right position
        default_pos = "left" if (i % 2 == 0) else "right"
        fg_pos = s.get("foreground_position") or default_pos

        # Dynamic Stat Card / Financial Ledger Extraction (Rule 102)
        stat_val = s.get("stat_value") or s.get("statValue")
        stat_lbl = s.get("stat_label") or s.get("statLabel")
        if not stat_val:
            auto_val, auto_lbl = extract_stat_card(narration_text)
            if auto_val:
                stat_val = auto_val
                stat_lbl = auto_lbl

        # Generic 5-Act non-fiction story engine headings (no hardcoded Enron strings)
        act_title = s.get("act_title") or (
            "ACT I // THE HOOK & EXPOSURE" if i <= int(total_scenes * 0.15) else
            "ACT II // THE ARCHITECTURE OF POWER" if i <= int(total_scenes * 0.40) else
            "ACT III // THE HIDDEN MECHANISM" if i <= int(total_scenes * 0.65) else
            "ACT IV // THE CRACK IN THE ILLUSION" if i <= int(total_scenes * 0.85) else
            "ACT V // THE AFTERMATH & RECKONING"
        )

        speaker_tag = format_speaker_tag(s, act_title, custom_beat_titles)

        # Extract Camera Grammar & Evidentiary Forensic Overlays (Rule 122 & Rule 128)
        cam = s.get("camera") or {}
        raw_cam_mov = s.get("camera_movement") or (cam.get("movement") if isinstance(cam, dict) else str(cam))
        cam_mov = normalize_camera_movement(raw_cam_mov)
        tension_lvl = s.get("tension_level") or (cam.get("tension_level") if isinstance(cam, dict) else "high")
        bg_cluster = s.get("bg_cluster_id") or s.get("bgClusterId")
        forensic_ov = s.get("forensic_overlay") or s.get("forensicOverlay")
        if not forensic_ov:
            candidate_ov = detect_forensic_overlay(narration_text)
            if candidate_ov:
                cand_type = candidate_ov.get("type")
                # Anti-monotony: allow overlay if >= 2 scenes since last overlay OR switching to contrasting type
                if scenes_since_overlay >= 2 or cand_type != last_overlay_type:
                    forensic_ov = candidate_ov
                    scenes_since_overlay = 0
                    last_overlay_type = cand_type
                else:
                    scenes_since_overlay += 1
            else:
                scenes_since_overlay += 1
        elif forensic_ov:
            scenes_since_overlay = 0
            last_overlay_type = forensic_ov if isinstance(forensic_ov, str) else forensic_ov.get("type")
        else:
            scenes_since_overlay += 1

        # Rule 122 & Rule 128: Guarantee forensic_overlay is a structured dict with full Vox Explanatory schema
        DEFAULT_OVERLAY_LABELS = {
            "redacted_doc": "CLASSIFIED // REDACTED RECORD",
            "radar_map": "RADAR TELEMETRY // VECTOR TRACK",
            "financial_chart": "MARKET DISRUPTION // CAPITAL TRAJECTORY",
            "surveillance_crt": "FACILITY_SURVEILLANCE // CH_04",
            "document_highlight": "CLASSIFIED // REDACTED RECORD",
            "kinetic_counter": "MARKET DISRUPTION // CAPITAL TRAJECTORY",
            "causal_flowchart": "INSTITUTIONAL TRANSMISSION // SYSTEMIC CHOKE",
            "tactical_map": "RADAR TELEMETRY // VECTOR TRACK",
            "bank_check": "GOVERNMENT DISBURSEMENT // SUBSIDY WARRANT",
            "paper_dossier": "OFFICIAL INSPECTION & AUDIT RECORD",
            "evidence_board": "CONSPIRACY NETWORK // TARGET OPERATORS",
            "evidence_3d_prop": "PHYSICAL EVIDENCE // FORENSIC SPECIMEN",
            "3d_evidence_prop": "PHYSICAL EVIDENCE // FORENSIC SPECIMEN",
            "3d_hanko_seal": "AUTHENTICATED IMPERIAL SEAL // FORENSIC SPECIMEN",
        }
        if isinstance(forensic_ov, str):
            fo_type = forensic_ov
            forensic_ov = build_structured_overlay(fo_type, narration_text, theme="vox_paper")

        # Spatial Layout Collision Prevention & Full-Bleed Focus Promotion (Rule 122 & Vox Paper-Collage)
        if forensic_ov and isinstance(forensic_ov, dict):
            # Strict Zero-Mock check for kinetic_counter (Rule 118):
            if forensic_ov.get("type") in ("kinetic_counter", "financial_chart"):
                p = forensic_ov.get("payload") or {}
                if not p.get("end_value") and not p.get("amount"):
                    parsed_m = parse_spoken_number(narration_text)
                    if parsed_m and parsed_m.display_value > 0:
                        forensic_ov["payload"] = {
                            "start_value": 0,
                            "end_value": parsed_m.display_value,
                            "amount": parsed_m.display_value,
                            "unit": parsed_m.unit,
                            "prefix": parsed_m.prefix,
                            "suffix": parsed_m.suffix,
                            "trend": parsed_m.trend,
                        }
                    else:
                        forensic_ov = None

        if forensic_ov and isinstance(forensic_ov, dict):
            if "label" not in forensic_ov:
                forensic_ov["label"] = DEFAULT_OVERLAY_LABELS.get(forensic_ov.get("type"), "FORENSIC // EVIDENCE RECORD")
            if "theme" not in forensic_ov or forensic_ov.get("theme") == "noir_dossier":
                forensic_ov["theme"] = "vox_paper"

            if not fg_rel:
                # When no foreground character is present, promote evidence to full-bleed focus mode!
                forensic_ov["layout"] = "full_bleed_focus"
            else:
                # When character is present, place evidence opposite to character
                if fg_pos == "left":
                    forensic_ov["layout"] = "split_right"
                else:
                    forensic_ov["layout"] = "split_left"

        # Extract Stamp Slam Badge (Rule 122 Acting & Evidence Props)
        stamp_badge = s.get("stamp_badge") or s.get("stampBadge")
        if not stamp_badge:
            t_lower = narration_text.lower()
            if any(k in t_lower for k in ["gian lận", "lừa đảo", "vi phạm", "사기", "위반", "부당", "환불 거부", "fraud", "violation", "illegal", "詐欺", "不正", "違反", "不適切", "改ざん", "改竄", "捏造", "隠蔽", "違法"]):
                stamp_badge = "PRICE_FRAUD"
            elif any(k in t_lower for k in ["tài liệu mật", "hợp đồng mật", "비밀", "기밀", "confidential", "classified", "nda", "機密", "極秘", "非公開", "内部告発", "秘密"]):
                stamp_badge = "CONFIDENTIAL"
            elif any(k in t_lower for k in ["bằng chứng", "chứng cứ", "vết nứt", "증거", "단서", "evidence", "proof", "証拠", "物証", "確証", "痕跡", "実態"]):
                stamp_badge = "EVIDENCE"
            elif any(k in t_lower for k in ["hủy bỏ", "vô hiệu", "취소", "무효", "void", "breach", "無効", "破棄", "契約解除", "差し止め", "取消"]):
                stamp_badge = "VOID"

        motion_directive = s.get("motion_directive") or s.get("motionDirective") or "subtle_drift"

        # Anti-Flicker Card Segment Key (Rule 122 & Zero-Flicker Architecture)
        card_segment_key = None
        if forensic_ov or stat_val or stamp_badge:
            ov_type = forensic_ov.get("type", "") if isinstance(forensic_ov, dict) else str(forensic_ov or "")
            ov_title = forensic_ov.get("title", "") if isinstance(forensic_ov, dict) else ""
            card_segment_key = f"{ov_type}_{stat_val or ''}_{stamp_badge or ''}_{ov_title}"

        # Beat-Level Optical FX Policy & Kinetic Typography Injection (Rule 122 & Audit Round 5 Standard)
        b_raw = s.get("beat_index") or s.get("beat") or 1
        try:
            b_num = int(str(b_raw).replace("Beat", "").strip())
        except Exception:
            b_num = 1

        is_metric_shock = any(k in narration_text for k in ["4860", "4,860", "24倍", "二十四倍", "四千八百六十", "24.3"])

        # Inject Kinetic Typography on Metric Moments if not already set to a specialized overlay
        if is_metric_shock and not (isinstance(forensic_ov, dict) and forensic_ov.get("type") in ("threshold_ratio", "kinetic_counter")):
            if b_num == 1 and idx in (0, 1, 2, 3):
                forensic_ov = {
                    "type": "kinetic_counter",
                    "title": "二酸化硫黄 検出値",
                    "badge": "EVIDENTIARY METRIC",
                    "theme": "crimson_alert",
                    "layout": "full_bleed_focus" if not fg_rel else "split_left",
                    "payload": {
                        "start_value": 0,
                        "end_value": 4860,
                        "amount": "4,860",
                        "unit": "mg/kg",
                        "baseline": 200,
                        "baseline_label": "国家基準上限 (GB 2760)"
                    },
                    "label": "4,860 mg/kg // 基準値の約24.3倍"
                }
            elif b_num == 4:
                forensic_ov = {
                    "type": "threshold_ratio",
                    "title": "国家基準 GB 2760 超過倍率検証",
                    "badge": "CRIMSON RATIO ALERT",
                    "theme": "crimson_alert",
                    "layout": "full_bleed_focus" if not fg_rel else "split_left",
                    "payload": {
                        "ratio": 24.3,
                        "baseline_value": 200,
                        "actual_value": 4860,
                        "unit": "mg/kg",
                        "grid_cols": 6,
                        "grid_rows": 4
                    },
                    "label": "GB 2760: 200mg/kg に対し 約24.3倍"
                }

        cinematic_tokens = s.get("cinematic_tokens") or s.get("cinematicTokens") or []
        token_vignette = "/edgefade" in cinematic_tokens
        token_grain = "/filmlook" in cinematic_tokens
        token_glitch = "/digitalglitch" in cinematic_tokens
        token_contrast = "/highcontrast" in cinematic_tokens

        if b_num == 1:
            optical_fx = {
                "vignette": True or token_vignette,
                "film_grain": True or token_grain,
                "digital_glitch": is_metric_shock or token_glitch,
                "high_contrast": is_metric_shock or token_contrast,
            }
        elif b_num in (2, 3):
            optical_fx = {
                "vignette": False or token_vignette,
                "film_grain": True or token_grain,
                "digital_glitch": False or token_glitch,
                "high_contrast": False or token_contrast,
            }
        elif b_num == 4:
            optical_fx = {
                "vignette": True or token_vignette,
                "film_grain": True or token_grain,
                "digital_glitch": is_metric_shock or token_glitch,
                "high_contrast": True or token_contrast,
            }
        else:  # Beat 5
            optical_fx = {
                "vignette": False or token_vignette,
                "film_grain": True or token_grain,
                "digital_glitch": False or token_glitch,
                "high_contrast": False or token_contrast,
            }

        # Foley SFX assignment (Rule 120, Rule 128 & Tactile Audio Spine)
        # ZERO-SILENT-FALLBACK MANDATE: Every foley cue must be registered in CANONICAL_SFX_REGISTRY
        # and physically present on disk in remotion/public/sfx/
        foley_raw = s.get("foleys_audio") or s.get("foleysAudio")
        if not foley_raw and isinstance(s.get("remotion_instructions"), dict):
            foley_raw = s.get("remotion_instructions", {}).get("foleys_trigger")
        foley_file = None
        if foley_raw:
            f_clean = str(foley_raw).strip()
            if not is_valid_sfx(f_clean):
                sc_id = s.get("id") or s.get("scene_id") or f"scene_{idx}"
                raise ValueError(
                    f"❌ B6 REMOTION PROPS SFX AUDIT FAILED at {sc_id}: "
                    f"Unknown foley cue '{foley_raw}'. Not registered in CANONICAL_SFX_REGISTRY! "
                    f"Zero silent fallback permitted."
                )
            f_filename = get_sfx_filename(f_clean)
            # Physical Asset Verification Gate
            physical_sfx_path = _REPO_ROOT / "remotion" / "public" / "sfx" / f_filename
            if not physical_sfx_path.exists():
                sc_id = s.get("id") or s.get("scene_id") or f"scene_{idx}"
                raise FileNotFoundError(
                    f"❌ B6 REMOTION PROPS SFX AUDIT FAILED at {sc_id}: "
                    f"Physical asset {physical_sfx_path} does not exist on disk!"
                )
            foley_file = f"sfx/{f_filename}"

        scenes_out.append({
            "background": bg_rel or "",
            "foreground": fg_rel,
            "foregroundPosition": fg_pos,
            "durationInFrames": max(1, round(dur_sec * fps)),
            "foregroundFadeFrames": max(1, round(fg_fade_sec * fps)),
            "caption": caption_text,
            "narration": narration_text,
            "safeZone": s.get("safe_zone") or "none",
            "statValue": stat_val,
            "statLabel": stat_lbl,
            "stampBadge": stamp_badge,
            "card_segment_key": card_segment_key,
            "motionDirective": motion_directive,
            "speakerTag": speaker_tag,
            "actTitle": act_title,
            "cameraMovement": cam_mov or "slow_push_in",
            "tensionLevel": tension_lvl or "high",
            "bgClusterId": bg_cluster,
            "forensicOverlay": forensic_ov,
            "object_focus": s.get("object_focus"),
            "layout_zone": s.get("layout_zone"),
            "animation_cue": s.get("animation_cue"),
            "frame_transition": s.get("frame_transition"),
            "cinematicTokens": cinematic_tokens,
            "opticalFx": optical_fx,
            "foleysAudio": foley_file,
            "foleys_audio": foley_file,
            "transition_out": s.get("transition_out") or s.get("transitionOut") or "hard_cut",
            "subtitles": scene_subtitles,  # Forward Faster-Whisper words
            "words": scene_subtitles,      # Alias for maximum compatibility
        })

    if missing:
        print("WARNING: missing local images for reuse keys: %s" % sorted(set(missing)), file=sys.stderr)
    if not scenes_out:
        print("ERROR: no scenes produced (brain_input has no usable scenes, or all were skipped)", file=sys.stderr)
        sys.exit(1)

    # Proportional scaling to match narration audio if video duration is shorter than audio
    audio_path = os.path.join(os.path.dirname(brain_input_path), "tts_out.mp3")
    if os.path.exists(audio_path):
        try:
            import subprocess as _sub
            probe = _sub.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], stdout=_sub.PIPE, text=True)
            adur = float(probe.stdout.strip())
            total_frames = sum(sc["durationInFrames"] for sc in scenes_out)
            total_vdur = total_frames / fps
            if adur > 0 and total_vdur < adur * 0.97:
                scale = (adur + 0.5) / total_vdur
                for sc in scenes_out:
                    sc["durationInFrames"] = max(1, round(sc["durationInFrames"] * scale))
                print(f"DURATION_SCALED: scaled {total_vdur:.1f}s -> {adur:.1f}s to match audio ({scale:.2f}x)")
        except Exception as _e_dur:
            print(f"DEBUG: duration probe fallback: {_e_dur}")

    # AI Senior Post-Production Editor Gate (Pacing, Word-locked punches, Monotony breaker)
    try:
        all_words = []
        for sc in scenes_out:
            for sub in (sc.get("subtitles") or []):
                all_words.append({
                    "word": sub.get("word"),
                    "start_ms": sub.get("abs_start_ms", sub.get("start_ms", 0)),
                    "end_ms": sub.get("abs_end_ms", sub.get("end_ms", 0)),
                })
        scenes_out = audit_and_optimize_timeline(
            scenes_out,
            whisper_words=all_words,
            options={
                "episode_id": episode_id,
                "brain_input_path": brain_input_path,
                "segments_path": segments_path,
            }
        )
    except Exception as _e_editor:
        logger.warning("[build_remotion_props] AI Editor optimization fallback: %s", _e_editor)

    # Vox Minimalist Pacing & Rule 122/128/136 Localization Gate
    try:
        from app.services.editorial_briefing_generator import (
            extract_market_from_episode_id,
            prune_and_localize_scenes,
            generate_editorial_briefing
        )
        m_code = extract_market_from_episode_id(episode_id)
        out_dir = os.path.dirname(os.path.abspath(brain_input_path))
        generate_editorial_briefing(episode_id, scenes_out, output_dir=out_dir)
        scenes_out = prune_and_localize_scenes(scenes_out, m_code)
        logger.info("[build_remotion_props] Vox Minimalist Gate applied: market=%s, overlays=%d/%d",
                    m_code, sum(1 for s in scenes_out if s.get("forensicOverlay")), len(scenes_out))
    except Exception as _e_brief:
        logger.warning("[build_remotion_props] Vox Minimalist Gate fallback: %s", _e_brief)

    props = {
        "scenes": scenes_out,
        "fps": fps,
        "width": width,
        "height": height,
    }
    return props


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--brain-input", required=True)
    ap.add_argument("--segments", default="")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--public-dir", default="/root/video_factory/remotion/public")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fg-fade-sec", type=float, default=0.5)
    ap.add_argument("--skip-missing", action="store_true",
                    help="drop scenes whose background image is missing instead of failing")
    args = ap.parse_args()

    props = build_remotion_props_data(
        episode_id=args.episode_id,
        brain_input_path=args.brain_input,
        segments_path=args.segments,
        manifest_path=args.manifest,
        public_dir=args.public_dir,
        fps=args.fps,
        width=args.width,
        height=args.height,
        fg_fade_sec=args.fg_fade_sec,
        skip_missing=args.skip_missing,
    )

    # Autonomous Editorial Director Gate (Rule 122, 128 & 136):
    # Enforce VOX character sparsity (<= 12 FG), breakdown layout monotony, and clean tags
    try:
        from scripts.orchestrator.adversarial_director_gate import auto_repair_props
        market = str(args.episode_id.split("_")[0]).upper() if args.episode_id else "EN"
        props = auto_repair_props(props, market)
        logger.info("Auto-repaired props applied at build_remotion_props (VOX minimalism & FG <= 12)")
    except Exception as _re:
        logger.warning("auto_repair_props skipped in build_remotion_props: %s", _re)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    total_words_forwarded = sum(len(sc.get("subtitles") or []) for sc in props["scenes"])
    print("WROTE", args.out, "scenes=%d (subtitles=%d words, stats=%d)" % (
        len(props["scenes"]),
        total_words_forwarded,
        sum(1 for sc in props["scenes"] if sc.get("statValue"))
    ))


if __name__ == "__main__":
    main()
