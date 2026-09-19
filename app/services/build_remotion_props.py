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

from app.services.text_to_number_parser import parse_spoken_number

logger = logging.getLogger("vf.build_remotion_props")


def detect_forensic_overlay(narration_text: str, theme: str = "vox_paper") -> dict | None:
    """Rule 128 & Vox Explanatory Engine: Detect tactile paper-collage evidentiary graphics."""
    if not narration_text:
        return None
    t = narration_text.lower()

    # 1. Document Highlight (Contracts, clauses, terms, NDA, redactions, audits, subpoenas, official files)
    if any(k in t for k in ["contract", "clause", "redact", "nda", "audit", "dossier", "agreement", "classified", "subpoena", "record", "records", "inspection", "capacity", "license", "hợp đồng", "điều khoản", "tài liệu", "biên bản", "thanh tra", "hồ sơ", "chứng cứ", "조항", "감사", "서류"]):
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
                "agency": "FEDERAL BUREAU OF INVESTIGATION // US DISTRICT COURT",
                "case_number": "CASE NO. 26-CR-01844-SD",
                "clauses": [
                    "1. FIELD AGENTS CONDUCTED UNANNOUNCED INSPECTIONS OF REGISTERED FACILITIES.",
                    "2. PHYSICAL ADDRESSES REVEALED RESIDENTIAL HOUSES WITH ZERO DAYCARE OPERATION.",
                    "3. INVOICES SUBMITTED CLAIMED OVER 100 MINORS UNDER CONTINUOUS SUPERVISION.",
                    "4. ENROLLMENT LOGS WERE FABRICATED USING STOLEN IDENTIFICATION DATA."
                ],
                "highlight_line_index": 1,
                "redacted_terms": ["STOLEN IDENTIFICATION", "ZERO DAYCARE"],
                "date": "OFFICIAL FILING // OCTOBER 2026"
            }
        }

    # 2. Tactical Map (Flight, plane, radar, coordinates, vanish, crash, route, locations, surveillance, CCTV)
    if any(k in t for k in ["flight", "plane", "radar", "altitude", "coordinate", "vanish", "crash", "air traffic", "route", "chuyến bay", "đường bay", "tọa độ", "rơi", "rada", "chokepoint", "strait", "sea lane", "eo biển", "hải trình", "surveillance", "cctv", "camera", "facility", "address", "location", "locations", "street", "city", "county", "district", "cơ sở", "địa điểm", "địa chỉ", "nhà trẻ", "khu vực", "시설", "주소", "위치", "warehouse", "giám sát"]):
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
                "target_name": "UNLICENSED GHOST DAYCARE FACILITY",
                "coordinates": "SAN DIEGO COUNTY JURISDICTION",
                "map_region": "SOUTHERN DISTRICT OF CALIFORNIA",
                "points_of_interest": ["OPERATOR RESIDENCE", "CLAIM PROCESSING OFFICE", "DEPOSIT CHOKEPOINT"]
            }
        }

    # 3. Kinetic Counter / Financial Ledger (Numerical claims, government funds, subsidies, theft, fraud amounts)
    parsed_metric = parse_spoken_number(narration_text)
    if parsed_metric is not None or any(k in t for k in ["dollar", "subsidy", "subsidies", "$", "check", "claim", "claims", "billing", "payment", "reimbursement", "fund", "funds", "tiền", "ngân sách", "trợ cấp", "chi trả", "지원금", "환불", "청구", "billion", "million"]):
        display_val = parsed_metric.formatted if parsed_metric else "$10,482,910"
        return {
            "type": "kinetic_counter",
            "legacy_type": "financial_chart",
            "theme": theme or "vox_paper",
            "layout": "full_bleed_focus",
            "title": f"GOVERNMENT DISBURSEMENT // {display_val}",
            "badge": "FRAUDULENT CLAIM",
            "sfx_cue": "stamp_slam",
            "label": f"EVIDENTIARY VALUE // {display_val}",
            "payload": {
                "amount": parsed_metric.display_value if parsed_metric else 10482910,
                "payee": "NOMINEE DAYCARE HOLDINGS // TARGET OPERATOR",
                "payer": "DEPARTMENT OF SOCIAL SERVICES // CHILD DEVELOPMENT FUND",
                "memo": "CHILDCARE SUBSIDY FRAUD // UNVERIFIED ATTENDANCE",
                "date": "AUDIT BATCH // 2024-2026"
            }
        }

    # 4. Evidence Board / Suspect Network (Indicted individuals, operators, ring, conspiracy, arrest)
    if any(k in t for k in ["charged", "indicted", "indictment", "defendants", "suspects", "operator", "operators", "ring", "conspiracy", "conspirators", "arrest", "fbi", "prosecutor", "prosecutors", "khởi tố", "bị can", "đối tượng", "đường dây", "bắt giữ", "기소", "피의자", "체포"]):
        return {
            "type": "evidence_board",
            "legacy_type": "causal_flowchart",
            "theme": theme or "vox_paper",
            "layout": "full_bleed_focus",
            "title": "CONSPIRACY NETWORK // TARGET OPERATORS",
            "badge": "CRIMINAL INDICTMENT",
            "sfx_cue": "paper_slide",
            "label": "INVESTIGATION DOSSIER // SUBJECT NETWORK",
            "payload": {
                "suspect_name": "PRIMARY TARGET // NOMINEE ADMINISTRATOR",
                "role": "UNLICENSED SHELL OPERATOR / FALSE ENROLLMENT",
                "charges": [
                    "18 U.S.C. § 1343 // WIRE FRAUD CONSPIRACY",
                    "18 U.S.C. § 1956 // MONEY LAUNDERING",
                    "THEFT OF GOVERNMENT ASSISTANCE FUNDS"
                ],
                "connected_entities": ["SHELL DAYCARE ENTITY", "CHECK CASHING SCHEME", "STATE ASSISTANCE LEDGER"],
                "evidence_tag": "CRIMINAL DIVISION CASE #26-CR"
            }
        }

    # 5. Causal Flowchart (Systemic trap, network, money laundering, shell game, pipeline)
    if any(k in t for k in ["mechanism", "network", "shell", "laundering", "channel", "transmission", "intermediary", "trap", "bẫy", "chuỗi", "dòng tiền", "trung gian", "cơ chế", "dây chuyền", "구조", "우회", "경로"]):
        return {
            "type": "causal_flowchart",
            "legacy_type": "redacted_doc",
            "theme": theme or "vox_paper",
            "layout": "full_bleed_focus",
            "title": "CAUSAL TRANSMISSION // ASYMMETRIC CHOKE",
            "badge": "RESTRICTED",
            "sfx_cue": "node_pop",
            "label": "INSTITUTIONAL TRANSMISSION // SYSTEMIC CHOKE",
            "payload": {
                "nodes": [
                    {"id": "origin", "label": "Consumer Capital", "status": "normal"},
                    {"id": "intermediary", "label": "Platform Escrow", "status": "breach"},
                    {"id": "offshore", "label": "Non-Refund Vault", "status": "fatal"}
                ],
                "edges": [
                    {"from": "origin", "to": "intermediary", "label": "Deposit Stream"},
                    {"from": "intermediary", "to": "offshore", "label": "Trapped Liquidity"}
                ]
            }
        }

    # 6. 3D Procedural Evidence Prop (Physical seals, stamps, warrants, vaults, authentications, physical evidence items)
    if any(k in t for k in ["hanko", "seal", "stamp", "con dấu", "triện", "mộc đỏ", "chứng thực", "vật chứng", "tang vật", "도장", "인감", "증거물", "authenticat", "exhibit item", "vault", "evidence item"]):
        return {
            "type": "evidence_3d_prop",
            "legacy_type": "evidence_board",
            "theme": theme or "vox_paper",
            "layout": "split_right",
            "title": "CONFIDENTIAL EVIDENCE // FORENSIC ARTIFACT",
            "badge": "PHYSICAL EXHIBIT",
            "sfx_cue": "stamp_slam",
            "label": "AUTHENTICATED IMPERIAL SEAL // 3D PROCEDURAL ARTIFACT",
            "payload": {
                "prop_type": "hanko_seal",
                "evidence_id": "EXHIBIT-3D-01",
                "authentication": "VERIFIED PHYSICAL TAMPER-PROOF"
            }
        }

    return None


def normalize_camera_movement(raw_mov: str | None) -> str:
    """Normalize raw camera movement string into one of 6 Remotion canonical movements."""
    if not raw_mov:
        return "slow_push_in"
    m = str(raw_mov).strip().lower()
    canonical = ["snap_zoom", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt", "handheld_shake"]
    if m in canonical:
        return m
    if "snap" in m or "punch" in m or ("zoom" in m and "slow" not in m):
        return "snap_zoom"
    if "pull" in m or "retreat" in m:
        return "slow_pull_out"
    if "push" in m or "forward" in m:
        return "slow_push_in"
    if "pan" in m or "lateral" in m or "drift" in m or "whip" in m:
        return "cinematic_pan"
    if "tilt" in m or "pedestal" in m:
        return "macro_tilt"
    if "shake" in m or "handheld" in m or "jitter" in m:
        return "handheld_shake"
    return "slow_push_in"


def load_manifest_index(manifest_path: str):
    with open(manifest_path, encoding="utf-8") as f:
        rows = json.load(f)
    by_reuse_key = {}
    fg_pool = []
    for r in rows:
        rk = (r.get("reuse_key") or "").strip()
        lp = r.get("local_path")
        if rk and lp:
            by_reuse_key[rk] = lp
            if "fg_" in rk.lower() or "character" in (r.get("asset_type") or "").lower():
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

    for i, s in enumerate(raw_scenes):
        bg_key = s.get("background_reuse_key")
        fg_key = s.get("foreground_reuse_key")
        bg_local = by_reuse_key.get(bg_key) if bg_key else None
        fg_local = by_reuse_key.get(fg_key) if fg_key else None

        if bg_key and not bg_local:
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

        # Alternate Left / Right position
        default_pos = "left" if (i % 2 == 0) else "right"
        fg_pos = s.get("foreground_position") or default_pos

        # Extract or read stat cards
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
            forensic_ov = detect_forensic_overlay(narration_text)

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
        }
        if isinstance(forensic_ov, str):
            forensic_ov = {
                "type": forensic_ov,
                "label": DEFAULT_OVERLAY_LABELS.get(forensic_ov, "FORENSIC // EVIDENCE RECORD")
            }

        # Spatial Layout Collision Prevention & Full-Bleed Focus Promotion (Rule 122 & Vox Paper-Collage)
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
        elif not forensic_ov and not fg_rel and narration_text:
            # Rule 122 & Vox Architecture: Guarantee zero visual dead zones when character is absent
            forensic_ov = {
                "type": "document_highlight",
                "legacy_type": "redacted_doc",
                "theme": "vox_paper",
                "layout": "full_bleed_focus",
                "title": "OFFICIAL INVESTIGATION RECORD",
                "badge": "EVIDENTIARY EXHIBIT",
                "sfx_cue": "marker_stroke",
                "label": "CLASSIFIED // REDACTED RECORD",
                "payload": {
                    "document_title": "MEMORANDUM OF INVESTIGATION",
                    "agency": "TASK FORCE FORENSIC AUDIT DIVISION",
                    "case_number": "CASE EXHIBIT // INVESTIGATION",
                    "clauses": [
                        (narration_text[:90].upper() + "...") if narration_text else "FORENSIC CASE AUDIT IN PROGRESS.",
                        "TRANSACTIONAL AUDITS CONFIRMED IRREGULARITIES.",
                        "EVIDENTIARY ADMISSIBILITY CERTIFIED BY PROSECUTION."
                    ],
                    "highlight_line_index": 0,
                    "redacted_terms": ["IRREGULARITIES"],
                    "date": "CASE RECORD"
                }
            }

        # Extract Stamp Slam Badge (Rule 122 Acting & Evidence Props)
        stamp_badge = s.get("stamp_badge") or s.get("stampBadge")
        if not stamp_badge:
            t_lower = narration_text.lower()
            if any(k in t_lower for k in ["gian lận", "lừa đảo", "vi phạm", "사기", "위반", "부당", "환불 거부", "fraud", "violation", "illegal"]):
                stamp_badge = "PRICE_FRAUD"
            elif any(k in t_lower for k in ["tài liệu mật", "hợp đồng mật", "비밀", "기밀", "confidential", "classified", "nda"]):
                stamp_badge = "CONFIDENTIAL"
            elif any(k in t_lower for k in ["bằng chứng", "chứng cứ", "vết nứt", "증거", "단서", "evidence", "proof"]):
                stamp_badge = "EVIDENCE"
            elif any(k in t_lower for k in ["hủy bỏ", "vô hiệu", "취소", "무효", "void", "breach"]):
                stamp_badge = "VOID"

        motion_directive = s.get("motion_directive") or s.get("motionDirective") or "subtle_drift"

        # Anti-Flicker Card Segment Key (Rule 122 & Zero-Flicker Architecture)
        card_segment_key = None
        if forensic_ov or stat_val or stamp_badge:
            ov_type = forensic_ov.get("type", "") if isinstance(forensic_ov, dict) else str(forensic_ov or "")
            ov_title = forensic_ov.get("title", "") if isinstance(forensic_ov, dict) else ""
            card_segment_key = f"{ov_type}_{stat_val or ''}_{stamp_badge or ''}_{ov_title}"

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
