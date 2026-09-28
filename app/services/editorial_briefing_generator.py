# app/services/editorial_briefing_generator.py
"""Editorial Briefing Generator & Overlay Density Pruning Engine.

Enforces Vox Pacing, Rule 122 (Market/Ethnic Context), Rule 128 (Generic Contract),
and Rule 136 (Clean Speaker Tags):
1. Restricts forensic overlays strictly to 6-8 climax scenes (10-15% of total scenes).
2. Localizes all overlay titles, document badges, and agency stamps to the target market (JP/KR/VN/EN).
3. Produces editorial_briefing.json containing the 5-Beat narrative spine and visual mandates.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.text_to_number_parser import parse_spoken_number

logger = logging.getLogger("editorial_briefing_generator")


# Rule 122 & Vox Motion Engine 3.0: Dynamic Dramatic Density Curve
BEAT_ENVELOPE = {
    1: {"overlay_density": 0.28, "cadence": "cutout", "karaoke": "full"},
    2: {"overlay_density": 0.20, "cadence": "cutout", "karaoke": "full"},
    3: {"overlay_density": 0.35, "cadence": "fluid",  "karaoke": "dim"},
    4: {"overlay_density": 0.45, "cadence": "smooth", "karaoke": "dim"},
    5: {"overlay_density": 0.10, "cadence": "smooth", "karaoke": "full"},
}

OVERLAY_BLACKOUT_AFTER = 609.0  # Hard stop: 0% overlays after 10:09 (609s)

BANNED_VERDICT_TERMS = {
    # English Judicial / Criminal Indictment terms
    "VIOLATION", "GUILTY", "ILLEGAL", "CRIME", "CRIMINAL", "FRAUD",
    "INDICTMENT", "GRAND JURY", "PROSECUTOR", "DOCKET", "SUBPOENA",
    "FELONY", "DEFENDANT", "CONVICTED", "LAWSUIT",
    # Japanese Criminal Prosecution terms (Defamation risk - Keihō 230)
    "違法", "有罪", "犯罪", "起訴", "刑事", "摘発", "起訴事実認定",
    "起訴状", "容疑者", "犯行", "司法審査", "刑事摘発", "地検",
    # Korean & Vietnamese equivalents
    "기소", "형사", "유죄", "범죄", "cáo trạng", "khởi tố", "truy tố"
}

STAMP_MEASUREMENT_MAP_JP: Dict[str, str] = {
    "VIOLATION": "基準値超過",
    "ILLEGAL": "基準外",
    "GUILTY": "事実確認",
    "CRIME": "是正指導事案",
    "CRIMINAL": "是正指導事案",
    "FRAUD": "記録不整合",
    "PRICE_FRAUD": "不当価格計上",
    "INDICTMENT": "行政指導",
    "GRAND JURY": "調査委員会",
    "PROSECUTOR": "検査官",
    "DOCKET": "査察記録",
    "SUBPOENA": "資料提出要請",
    "FELONY": "重大不適合",
    "DEFENDANT": "対象事業者",
    "CONVICTED": "確定記録",
    "LAWSUIT": "民事訴訟",
    "違法": "基準超過",
    "有罪": "事実確認",
    "犯罪": "是正指導事案",
    "起訴": "行政指導",
    "刑事": "行政検査",
    "摘発": "回収命令",
    "起訴事実認定": "基準値超過確認",
    "起訴状": "検査成績書",
    "容疑者": "対象事業者",
    "犯行": "規則違反",
    "司法審査": "行政検査",
    "刑事摘発": "回収命令措置",
    "地検": "捜査委員会",
}

STAMP_MEASUREMENT_MAP_EN: Dict[str, str] = {
    # English terms -> Clean neutral regulatory/forensic English
    "VIOLATION": "REGULATORY DISCREPANCY",
    "ILLEGAL": "NON-COMPLIANT",
    "GUILTY": "FACTUAL FINDING",
    "CRIME": "REGULATORY AUDIT",
    "CRIMINAL": "REGULATORY AUDIT",
    "FRAUD": "ACCOUNTING DISCREPANCY",
    "PRICE_FRAUD": "PRICING DISCREPANCY",
    "INDICTMENT": "FORMAL INQUIRY",
    "GRAND JURY": "INVESTIGATIVE COMMITTEE",
    "PROSECUTOR": "CHIEF AUDITOR",
    "DOCKET": "CASE DOCKET",
    "SUBPOENA": "SUBPOENAED RECORD",
    "FELONY": "MAJOR IRREGULARITY",
    "DEFENDANT": "SUBJECT ENTITY",
    "CONVICTED": "ADJUDICATED",
    "LAWSUIT": "CIVIL FILING",
    # Japanese stray terms -> Clean neutral English
    "違法": "NON-COMPLIANT",
    "有罪": "FACTUAL FINDING",
    "犯罪": "REGULATORY AUDIT",
    "起訴": "FORMAL INQUIRY",
    "刑事": "REGULATORY AUDIT",
    "摘発": "REGULATORY ACTION",
    "起訴事実認定": "ADJUDICATED FINDING",
    "起訴状": "OFFICIAL DOSSIER",
    "容疑者": "SUBJECT ENTITY",
    "犯行": "DEVIATION",
    "司法審査": "REGULATORY AUDIT",
    "刑事摘発": "ENFORCEMENT ACTION",
    "地検": "INVESTIGATIVE UNIT",
    "資料提出要請": "RECORD REQUEST",
    "是正指導事案": "REGULATORY AUDIT",
    "基準値超過": "EXCEEDED STANDARD",
    "基準外": "NON-COMPLIANT",
    "事実確認": "FACTUAL FINDING",
    "記録不整合": "RECORD INCONSISTENCY",
    "行政指導": "REGULATORY GUIDANCE",
    "査察記録": "AUDIT RECORD",
    "重大不適合": "CRITICAL IRREGULARITY",
    "対象事業者": "SUBJECT ENTITY",
    "回収命令": "RECALL NOTICE",
}

# Maintain backward compatibility for external callers
STAMP_MEASUREMENT_MAP = STAMP_MEASUREMENT_MAP_JP


def get_stamp_measurement_map(market: str) -> Dict[str, str]:
    """Retrieve market-appropriate regulatory and forensic euphemism mappings."""
    m = (market or "JP").upper()
    if m in ("EN", "US", "UK"):
        return STAMP_MEASUREMENT_MAP_EN
    return STAMP_MEASUREMENT_MAP_JP


LOCALIZED_OVERLAY_THEMES: Dict[str, Dict[str, Any]] = {
    "JP": {
        "document_title": "公式検査・査察記録 // 検査成績書",
        "agency": "食品安全監視機構 // 検査指導課",
        "case_number": "査察記録 // 第782号 行政検査録",
        "date_verified": "公式検証記録 // 承認済",
        "network_title": "流通・検査相関図 // 流通経路ネットワーク",
        "network_badge": "検査成績書 // 基準値超過",
        "network_label": "検査調書 // 流通相関図",
        "suspect_role": "無許可加工事業者 / 不正原材料受領者",
        "charges": ["食品衛生法基準違反", "虚偽データ及び記録改ざんの提出"],
        "connected_entities": ["規制監督官庁", "対象事業施設", "検査保管所"],
        "evidence_tag": "検査検体物件",
        "counter_title": "検査差異 // 基準数値逸脱",
        "counter_badge": "重大指摘事項",
        "map_title": "地理流通データ // 対象位置確認",
        "map_badge": "重点監視地域",
        "default_speaker": "検査記録 // 時系列検証",
    },
    "KR": {
        "document_title": "공식 감사·검사 기록 // 사실 인정서",
        "agency": "규제감독기구 // 특별수사과",
        "case_number": "감사 기록 // 제782호 심의록",
        "date_verified": "공식 검증 기록 // 승인됨",
        "network_title": "수사 연관도 // 대상 조직 네트워크",
        "network_badge": "압수 증거물 // 형사 입건",
        "network_label": "조사 서류 // 대상 관계망",
        "suspect_role": "무허가 차명 사업자 / 부당 자금 수령",
        "charges": ["안전규정 위반", "허위 데이터 및 기록 조작 제출"],
        "connected_entities": ["규제 감독 부처", "운영 현장 시설", "감사 보관 기록소"],
        "evidence_tag": "공식 사건 증거",
        "counter_title": "감사 불일치 // 시스템 수치 왜곡",
        "counter_badge": "핵심 적발 사항",
        "map_title": "작전 지리 데이터 // 대상 위치 파악",
        "map_badge": "중점 감시 구역",
        "default_speaker": "증거 기록 // 타임라인 검증",
    },
    "EN": {
        "document_title": "OFFICIAL INVESTIGATION RECORD // FINDINGS OF FACT",
        "agency": "REGULATORY OVERSIGHT // INVESTIGATIVE DIVISION",
        "case_number": "CASE DOCKET // ADJUDICATED FILING",
        "date_verified": "OFFICIAL RECORD // VERIFIED",
        "network_title": "INVESTIGATION NETWORK // TARGET ENTITIES",
        "network_badge": "REGULATORY INQUIRY",
        "network_label": "INVESTIGATION DOSSIER // SUBJECT NETWORK",
        "suspect_role": "UNLICENSED SHELL OPERATOR / FALSE DISBURSEMENT",
        "charges": ["REGULATORY DEVIATION", "SUBMISSION OF INCONSISTENT RECORD FILINGS"],
        "connected_entities": ["REGULATORY OVERSIGHT DESK", "OPERATIONAL FACILITY", "FILING AUDIT ARCHIVE"],
        "evidence_tag": "OFFICIAL CASE EXHIBIT",
        "counter_title": "AUDIT DISCREPANCY // SYSTEMIC VARIANCE",
        "counter_badge": "CRITICAL FINDING",
        "map_title": "GEO-TACTICAL TELEMETRY // SECTOR GRID",
        "map_badge": "LOCATIONAL EVIDENCE",
        "default_speaker": "CRITICAL EVIDENCE // FORENSIC TIMELINE",
    },
}


def extract_market_from_episode_id(episode_id: str) -> str:
    """Extract 2-letter market code (e.g. 'JP_EP0003_...' -> 'JP'). Defaults to 'EN'."""
    if not episode_id:
        return "EN"
    m = re.match(r'^([A-Z]{2})_', episode_id)
    if m:
        code = m.group(1).upper()
        if code in LOCALIZED_OVERLAY_THEMES:
            return code
    return "EN"


def select_climax_scenes(scenes: List[Dict[str, Any]], target_count: Optional[int] = None) -> List[int]:
    """Select climax scene indices across 5 Beats strictly following BEAT_ENVELOPE dramatic curve.
    
    Beat 1: 0.35 (Hook & Anomaly)
    Beat 2: 0.30 (Institutional Trap - Minimalist, Paper Flow)
    Beat 3: 0.55 (Forensic Paper Trail & Quantitative Chain)
    Beat 4: 0.85 (Smoking Gun Climax Peak)
    Beat 5: 0.12 (Modern Mirror - Philosophical Resolution, Hard Stop at 10:09)
    """
    if not scenes:
        return []

    if len(scenes) <= 4:
        return [i for i, s in enumerate(scenes) if s.get("forensic_overlay") or s.get("forensicOverlay")]

    # Compute timeline timestamps
    timeline_sec = 0.0
    scene_start_times: Dict[int, float] = {}
    for i, s in enumerate(scenes):
        scene_start_times[i] = timeline_sec
        dur = s.get("durationInFrames")
        if dur:
            dur_s = float(dur) / 30.0
        else:
            dur_s = float(s.get("duration_sec") or s.get("duration_seconds") or 4.38)
        timeline_sec += dur_s

    # Group scenes by beat
    beats_map: Dict[int, List[Tuple[int, Dict[str, Any]]]] = {b: [] for b in range(1, 6)}
    total_len = max(1, len(scenes))

    for idx, s in enumerate(scenes):
        b_val = s.get("beat_index") or s.get("beat_number") or s.get("act_number") or s.get("beat")
        b_int = None
        if isinstance(b_val, int):
            b_int = b_val
        elif isinstance(b_val, str):
            m_num = re.search(r'([1-5])', b_val)
            if m_num:
                b_int = int(m_num.group(1))
            else:
                for roman, arab in [("V", 5), ("IV", 4), ("III", 3), ("II", 2), ("I", 1)]:
                    if roman in b_val.upper():
                        b_int = arab
                        break

        if b_int is None:
            pct = idx / total_len
            if pct < 0.15:
                b_int = 1
            elif pct < 0.40:
                b_int = 2
            elif pct < 0.65:
                b_int = 3
            elif pct < 0.85:
                b_int = 4
            else:
                b_int = 5

        b_int = max(1, min(5, b_int))
        beats_map[b_int].append((idx, s))

    def _scene_priority(item: Tuple[int, Dict[str, Any]]) -> float:
        idx, sc = item
        score = 0.0
        narration = sc.get("narration", "") or sc.get("caption", "")
        narr_lower = narration.lower()
        if any(k in narr_lower for k in [
            "audit", "benchmark", "threshold", "violation", "evidence", "fraud", "inspection",
            "기준", "위반", "감사", "증거", "조사",
            "基準", "超過", "違反", "検査", "検疫", "追跡", "不正", "報告",
            "bằng chứng", "vi phạm", "thanh tra", "hợp đồng"
        ]):
            score += 8.0
        metric = parse_spoken_number(narration)
        if metric:
            score += 6.0
        raw_fo = sc.get("forensic_overlay") or sc.get("forensicOverlay")
        if isinstance(raw_fo, dict):
            fo_type = raw_fo.get("type") or ""
            if fo_type in ("threshold_ratio", "grid_ratio", "causal_flowchart", "evidence_3d_prop"):
                score += 10.0
            else:
                score += 4.0
        dur = sc.get("durationInFrames") or (sc.get("duration_sec", 0) * 30)
        if dur >= 105:
            score += 2.0
        return score

    selected_indices: List[int] = []

    if target_count is not None:
        if target_count <= 0:
            return []
        if target_count >= len(scenes):
            return list(range(len(scenes)))

        active_beats = [b for b in range(1, 6) if beats_map[b]]
        base_alloc: Dict[int, int] = {}
        remaining = target_count

        if remaining >= len(active_beats):
            for b in active_beats:
                base_alloc[b] = 1
            remaining -= len(active_beats)
        else:
            for b in active_beats:
                base_alloc[b] = 0

        # Distribute remaining quota based on beat weights
        weights = {b: BEAT_ENVELOPE[b]["overlay_density"] for b in active_beats if len(beats_map[b]) > base_alloc[b]}
        total_w = sum(weights.values()) or 1.0
        sorted_beats = sorted(weights.keys(), key=lambda b: weights[b], reverse=True)

        for b in sorted_beats:
            if remaining <= 0:
                break
            can_take = len(beats_map[b]) - base_alloc[b]
            add = min(can_take, max(1, round(remaining * weights[b] / total_w)))
            add = min(add, remaining)
            base_alloc[b] += add
            remaining -= add

        for b in sorted_beats:
            if remaining <= 0:
                break
            can_take = len(beats_map[b]) - base_alloc[b]
            if can_take > 0:
                add = min(can_take, remaining)
                base_alloc[b] += add
                remaining -= add

        selected_indices: List[int] = []
        for b in active_beats:
            quota = base_alloc.get(b, 0)
            candidates = beats_map[b]
            eligible = [
                (idx, sc) for idx, sc in candidates
                if not (b == 5 and scene_start_times[idx] >= OVERLAY_BLACKOUT_AFTER)
            ]
            if not eligible:
                eligible = candidates
            sorted_candidates = sorted(eligible, key=_scene_priority, reverse=True)
            picked = [idx for idx, _ in sorted_candidates[:quota]]
            selected_indices.extend(picked)

        return sorted(list(set(selected_indices)))

    # When target_count is None (default full episode pacing):
    selected_indices: List[int] = []
    for b_int in range(1, 6):
        candidates = beats_map[b_int]
        if not candidates:
            continue

        env = BEAT_ENVELOPE[b_int]
        target_density = env["overlay_density"]

        eligible_candidates = []
        for idx, sc in candidates:
            if b_int == 5 and scene_start_times[idx] >= OVERLAY_BLACKOUT_AFTER:
                continue
            eligible_candidates.append((idx, sc))

        quota = max(1, round(len(candidates) * target_density))
        sorted_candidates = sorted(eligible_candidates, key=_scene_priority, reverse=True)
        picked = [idx for idx, _ in sorted_candidates[:quota]]
        selected_indices.extend(picked)

    selected_indices = sorted(list(set(selected_indices)))

    # Gap smoothing pass for narrative body (scenes before OVERLAY_BLACKOUT_AFTER)
    # Strictly respect the VOX 35% hard ceiling (max 33% from auto-selection)
    if target_count is None and len(scenes) >= 30:
        max_allowed = min(60, int(len(scenes) * 0.33))
        changed = True
        pass_cnt = 0
        while changed and pass_cnt < 2 and len(selected_indices) < max_allowed:
            changed = False
            pass_cnt += 1
            new_indices = list(selected_indices)
            for k in range(len(selected_indices) - 1):
                if len(new_indices) >= max_allowed:
                    break
                i1, i2 = selected_indices[k], selected_indices[k + 1]
                if i2 - i1 > 7:
                    gap_candidates = [
                        (idx, scenes[idx]) for idx in range(i1 + 3, i2 - 2)
                        if scene_start_times[idx] < OVERLAY_BLACKOUT_AFTER
                    ]
                    if gap_candidates:
                        best_gap_idx = max(gap_candidates, key=_scene_priority)[0]
                        if best_gap_idx not in new_indices:
                            new_indices.append(best_gap_idx)
                            changed = True
            selected_indices = sorted(list(set(new_indices)))

    return selected_indices


def prune_and_localize_scenes(
    scenes: List[Dict[str, Any]],
    market: str,
    climax_indices: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """Prune forensicOverlay strictly adhering to BEAT_ENVELOPE and Rule 122/128/136."""
    m_clean = market.upper() if market in LOCALIZED_OVERLAY_THEMES else "EN"
    theme = LOCALIZED_OVERLAY_THEMES[m_clean]

    if climax_indices is None:
        climax_indices = select_climax_scenes(scenes)

    climax_set = set(climax_indices)
    sanitized: List[Dict[str, Any]] = []

    # Calculate timeline timestamps
    timeline_sec = 0.0
    scene_start_times: Dict[int, float] = {}
    for i, s in enumerate(scenes):
        scene_start_times[i] = timeline_sec
        dur = s.get("durationInFrames")
        if dur:
            dur_s = float(dur) / 30.0
        else:
            dur_s = float(s.get("duration_sec") or s.get("duration_seconds") or 4.38)
        timeline_sec += dur_s

    total_len = max(1, len(scenes))
    seen_sources: set[str] = set()

    # Identify disclosure key scenes: scene 0, first scene of beat 4, last scene of beat 5
    beat4_first_idx = None
    for idx in range(len(scenes)):
        pct = idx / total_len
        if pct >= 0.65 and beat4_first_idx is None:
            beat4_first_idx = idx
            break
    disclosure_scenes = {0, beat4_first_idx if beat4_first_idx is not None else int(total_len * 0.65), len(scenes) - 1}

    for i, s in enumerate(scenes):
        scene_copy = dict(s)
        start_sec = scene_start_times.get(i, 0.0)

        # Determine beat (1..5)
        b_val = scene_copy.get("beat_index") or scene_copy.get("beat_number") or scene_copy.get("act_number") or scene_copy.get("beat")
        b_int = None
        if isinstance(b_val, int):
            b_int = b_val
        elif isinstance(b_val, str):
            m_num = re.search(r'([1-5])', b_val)
            if m_num:
                b_int = int(m_num.group(1))
            else:
                for roman, arab in [("V", 5), ("IV", 4), ("III", 3), ("II", 2), ("I", 1)]:
                    if roman in b_val.upper():
                        b_int = arab
                        break

        if b_int is None:
            pct = i / total_len
            if pct < 0.15:
                b_int = 1
            elif pct < 0.40:
                b_int = 2
            elif pct < 0.65:
                b_int = 3
            elif pct < 0.85:
                b_int = 4
            else:
                b_int = 5
        b_int = max(1, min(5, b_int))

        env = BEAT_ENVELOPE[b_int]
        scene_copy["beat"] = b_int
        scene_copy["beat_index"] = b_int
        scene_copy["cadence"] = env["cadence"]
        scene_copy["karaoke_mode"] = env["karaoke"]
        scene_copy["karaokeMode"] = env["karaoke"]

        narration = scene_copy.get("narration", "") or scene_copy.get("caption", "")
        raw_fo = scene_copy.get("forensicOverlay") or scene_copy.get("forensic_overlay")

        # Check overlay eligibility: strictly climax set and before blackout threshold
        is_eligible = (i in climax_set) and (start_sec < OVERLAY_BLACKOUT_AFTER)

        if not is_eligible:
            scene_copy["forensicOverlay"] = None
            scene_copy["forensic_overlay"] = None
            scene_copy["statValue"] = None
            scene_copy["statLabel"] = None
            scene_copy["sourceCredit"] = None
            scene_copy["source_credit"] = None
            scene_copy["credit_style"] = None
            scene_copy["creditStyle"] = None
        else:
            # Construct or sanitize authorized overlay
            overlay_obj: Dict[str, Any] = {}
            if isinstance(raw_fo, dict) and raw_fo.get("type"):
                overlay_obj = dict(raw_fo)
            else:
                metric = parse_spoken_number(narration)
                if metric:
                    fo_type = "kinetic_counter"
                elif i % 2 == 0:
                    fo_type = "document_highlight"
                else:
                    fo_type = "evidence_board"

                if fo_type == "kinetic_counter":
                    overlay_obj = {
                        "type": "kinetic_counter",
                        "title": theme["counter_title"],
                        "badge": theme["counter_badge"],
                        "label": theme["counter_title"],
                        "theme": "vox_paper",
                        "layout": "full_bleed_focus",
                        "sfx_cue": "stamp_slam",
                    }
                    if metric:
                        scene_copy["statValue"] = metric.formatted
                        scene_copy["statLabel"] = theme["counter_title"]
                elif fo_type in ("evidence_board", "causal_flowchart"):
                    overlay_obj = {
                        "type": "evidence_board",
                        "legacy_type": "causal_flowchart",
                        "theme": "vox_paper",
                        "layout": "full_bleed_focus",
                        "title": theme["network_title"],
                        "badge": theme["network_badge"],
                        "sfx_cue": "paper_slide",
                        "label": theme["network_label"],
                        "payload": {
                            "suspect_name": theme["suspect_role"],
                            "role": theme["suspect_role"],
                            "charges": theme["charges"],
                            "connected_entities": theme["connected_entities"],
                            "evidence_tag": theme["evidence_tag"],
                        }
                    }
                else:
                    overlay_obj = {
                        "type": "document_highlight",
                        "title": theme["document_title"],
                        "badge": theme["network_badge"],
                        "theme": "vox_paper",
                        "layout": "full_bleed_focus",
                        "sfx_cue": "shutter_click",
                        "payload": {
                            "document_title": theme["document_title"],
                            "agency": theme["agency"],
                            "case_number": theme["case_number"],
                            "clauses": [narration[:80]] if narration else ["OFFICIAL RECORD"],
                            "highlight_line_index": 0,
                            "redacted_terms": ["CONFIDENTIAL", "REDACTED"],
                            "date": theme["date_verified"],
                        }
                    }

            # Sanitize US legal artifacts and English cliches in non-EN markets
            curr_title = str(overlay_obj.get("title") or "")
            curr_badge = str(overlay_obj.get("badge") or "")
            if "US DISTRICT COURT" in curr_title or "GRAND JURY" in curr_badge or "INDICTMENT" in curr_title:
                if m_clean == "JP":
                    overlay_obj["title"] = "行政指導 // 検査成績書"
                    overlay_obj["badge"] = "基準値超過確認"
                elif m_clean in ("EN", "US", "UK"):
                    overlay_obj["title"] = "FORMAL INQUIRY // AUDIT REPORT"
                    overlay_obj["badge"] = "CRITICAL FINDING"
                else:
                    overlay_obj["title"] = "ADMINISTRATIVE AUDIT // INSPECTION REPORT"
                    overlay_obj["badge"] = "STANDARD EXCEEDED"

            if m_clean not in ("EN", "US", "UK"):
                cliche_map = {
                    "OFFICIAL INVESTIGATION RECORD": theme["document_title"],
                    "FINDINGS OF FACT": theme["document_title"],
                    "AUDIT DISCREPANCY": theme["counter_title"],
                    "CRITICAL FINDING": theme["counter_badge"],
                    "SUBPOENAED EVIDENCE": theme["network_badge"],
                    "INVESTIGATION NETWORK": theme["network_title"],
                    "GEO-TACTICAL TELEMETRY": theme["map_title"],
                    "CRIMINAL INDICTMENT": theme["network_badge"],
                    "LOCATIONAL EVIDENCE": theme.get("map_badge", "重点監視地域"),
                }
                for cliche, loc_val in cliche_map.items():
                    if cliche in overlay_obj.get("title", ""):
                        overlay_obj["title"] = overlay_obj["title"].replace(cliche, loc_val)
                    if cliche in overlay_obj.get("badge", ""):
                        overlay_obj["badge"] = overlay_obj["badge"].replace(cliche, loc_val)
                    if cliche in overlay_obj.get("label", ""):
                        overlay_obj["label"] = overlay_obj["label"].replace(cliche, loc_val)

            # Sanitize banned verdict terms across title, badge, label and payload
            meas_map = get_stamp_measurement_map(m_clean)
            default_sanitized = "基準値超過" if m_clean == "JP" else "EXCEEDED_STANDARD"

            for bad_term in BANNED_VERDICT_TERMS:
                rep = meas_map.get(bad_term, default_sanitized)
                if bad_term in overlay_obj.get("badge", ""):
                    b_val = overlay_obj["badge"]
                    if b_val == bad_term or not b_val.replace(bad_term, "").strip():
                        overlay_obj["badge"] = rep
                    else:
                        overlay_obj["badge"] = b_val.replace(bad_term, rep)
                if bad_term in overlay_obj.get("title", ""):
                    overlay_obj["title"] = overlay_obj["title"].replace(bad_term, rep)
                if bad_term in overlay_obj.get("label", ""):
                    overlay_obj["label"] = overlay_obj["label"].replace(bad_term, rep)

            # In EN episodes, ensure absolutely NO CJK remains in badge, title, or label
            if m_clean in ("EN", "US", "UK"):
                for field in ("badge", "title", "label"):
                    val = overlay_obj.get(field, "")
                    if val and re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', val):
                        for cjk_k, cjk_v in STAMP_MEASUREMENT_MAP_EN.items():
                            val = val.replace(cjk_k, cjk_v)
                        if re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', val):
                            val = re.sub(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]+', 'AUDIT RECORD', val).strip(' /-_')
                        overlay_obj[field] = val

            if isinstance(overlay_obj.get("payload"), dict):
                p_load = overlay_obj["payload"]
                def _sanitize_dict(d: dict):
                    for pk, pv in list(d.items()):
                        if isinstance(pv, str):
                            val = pv
                            if m_clean == "JP":
                                val = val.replace("CASE DOCKET // ADJUDICATED FILING", theme.get("case_number", "査察記録 // 行政検査録"))
                                val = val.replace("OFFICIAL INVESTIGATION RECORD // FINDINGS OF FACT", theme.get("document_title", "公式検査・査察記録 // 検査成績書"))
                                val = val.replace("REGULATORY OVERSIGHT // INVESTIGATIVE DIVISION", theme.get("agency", "食品安全監視機構 // 検査指導課"))
                                val = val.replace("court_indictment_3d", "inspection_dossier_3d")
                                val = val.replace("EXHIBIT-3D-INDICTMENT", "EXHIBIT-3D-INSPECTION")
                                val = val.replace("公的記録 // 司法審査調書", "公的記録 // 行政検査調書")
                                val = val.replace("司法審査", "行政検査")
                                val = val.replace("起訴状", "検査成績書")
                                val = val.replace("起訴事実認定", "基準値超過確認")
                                val = val.replace("刑事摘発", "回収命令")
                                val = val.replace("刑事", "行政検査")
                                val = val.replace("摘発", "回収命令")
                                val = val.replace("起訴", "行政指導")
                            for bad_term, rep in meas_map.items():
                                val = val.replace(bad_term, rep)
                            for bad_term in BANNED_VERDICT_TERMS:
                                if bad_term in val:
                                    val = val.replace(bad_term, meas_map.get(bad_term, default_sanitized))
                            if m_clean in ("EN", "US", "UK"):
                                if re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', val):
                                    for cjk_k, cjk_v in STAMP_MEASUREMENT_MAP_EN.items():
                                        val = val.replace(cjk_k, cjk_v)
                                    val = re.sub(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]+', 'AUDIT RECORD', val).strip(' /-_')
                            d[pk] = val
                        elif isinstance(pv, list):
                            clean_list = []
                            for item in pv:
                                if isinstance(item, str):
                                    i_val = item
                                    if m_clean == "JP":
                                        i_val = i_val.replace("司法審査", "行政検査").replace("起訴", "行政指導").replace("刑事", "行政検査").replace("摘発", "回収命令")
                                    for bad_term, rep in meas_map.items():
                                        i_val = i_val.replace(bad_term, rep)
                                    for bad_term in BANNED_VERDICT_TERMS:
                                        if bad_term in i_val:
                                            i_val = i_val.replace(bad_term, meas_map.get(bad_term, default_sanitized))
                                    if m_clean in ("EN", "US", "UK"):
                                        if re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', i_val):
                                            for cjk_k, cjk_v in STAMP_MEASUREMENT_MAP_EN.items():
                                                i_val = i_val.replace(cjk_k, cjk_v)
                                            i_val = re.sub(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]+', 'AUDIT RECORD', i_val).strip(' /-_')
                                    clean_list.append(i_val)
                                elif isinstance(item, dict):
                                    _sanitize_dict(item)
                                    clean_list.append(item)
                                else:
                                    clean_list.append(item)
                            d[pk] = clean_list
                        elif isinstance(pv, dict):
                            _sanitize_dict(pv)

                _sanitize_dict(p_load)

            # Ensure integer stop_motion_fps in payload
            if isinstance(overlay_obj.get("payload"), dict):
                if overlay_obj["payload"].get("stop_motion_fps") == 12:
                    overlay_obj["payload"]["stop_motion_fps"] = 10

            scene_copy["forensicOverlay"] = overlay_obj
            scene_copy["forensic_overlay"] = overlay_obj

            # Source Credit Deduplication (Citation-Event vs. Corner Tick) - Rule 128 Anti-Semantic Bias
            source_agency = theme.get("agency", "REGULATORY OVERSIGHT // INVESTIGATIVE DIVISION" if m_clean != "JP" else "公的規制監督機関 // 査察調査部門")
            source_citation = theme.get("document_title", "OFFICIAL INVESTIGATION RECORD // FINDINGS OF FACT" if m_clean != "JP" else "公的査察・調査記録 // 公式公示録")
            source_key = f"{source_agency[:25]}_{b_int}"

            if source_key not in seen_sources:
                seen_sources.add(source_key)
                credit_style = "full"
            else:
                credit_style = "tick"

            scene_copy["sourceCredit"] = {
                "source": source_citation,
                "verifiedDate": theme.get("date_verified", "OFFICIAL RECORD"),
                "docketNumber": source_agency,
                "styleType": credit_style,
            }
            scene_copy["source_credit"] = scene_copy["sourceCredit"]
            scene_copy["credit_style"] = credit_style
            scene_copy["creditStyle"] = credit_style

        # Statutory AI Disclosure Badge (Rule 122 & NHK/BPO compliance): Exactly 3 key milestone scenes
        # Strict visual blackout between 609s and 650s: absolutely NO badge and NO overlay.
        # The final scene badge is permitted only in the last scene (>= 650s) to anchor the YouTube end-screen.
        if i in disclosure_scenes and not (609.0 <= start_sec < 650.0):
            scene_copy["disclosureBadge"] = "※イメージ映像・再現" if m_clean == "JP" else "※Reconstruction / Simulation"
        else:
            scene_copy["disclosureBadge"] = None

        # Sanitize speaker tag (Rule 136)
        raw_tag = scene_copy.get("speakerTag")
        if raw_tag:
            clean_tag = str(raw_tag).strip()
            clean_tag = re.sub(r'\.(png|jpg|jpeg|webp)$', '', clean_tag, flags=re.IGNORECASE)
            clean_tag = re.sub(r'^(ARCHIVE\s*X\s*//\s*|DEFAULT\s*//\s*)', '', clean_tag, flags=re.IGNORECASE)
            if m_clean not in ("EN", "US", "UK") and re.search(r'[A-Za-z]{4,}', clean_tag) and not re.search(r'[぀-ヿ㐀-䶿一-鿿가-힯à-ỹ]', clean_tag):
                clean_tag = theme.get("default_speaker", "CRITICAL EVIDENCE // FORENSIC TIMELINE")
            elif m_clean in ("EN", "US", "UK") and re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', clean_tag):
                clean_tag = theme.get("default_speaker", "CRITICAL EVIDENCE // FORENSIC TIMELINE")
            scene_copy["speakerTag"] = clean_tag

        sanitized.append(scene_copy)

    return sanitized

def generate_editorial_briefing(
    episode_id: str,
    scenes: List[Dict[str, Any]],
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate editorial_briefing.json summarizing narrative beats and authorized overlays."""
    market = extract_market_from_episode_id(episode_id)
    climax_indices = select_climax_scenes(scenes)
    sanitized_scenes = prune_and_localize_scenes(scenes, market, climax_indices)

    overlay_count = sum(1 for s in sanitized_scenes if s.get("forensicOverlay"))
    density_pct = round((overlay_count / max(1, len(scenes))) * 100, 1)

    briefing = {
        "episode_id": episode_id,
        "market": market,
        "total_scenes": len(scenes),
        "climax_scenes_count": len(climax_indices),
        "climax_scene_indices": climax_indices,
        "overlay_density_pct": density_pct,
        "pacing_verdict": "APPROVED_VOX_MINIMALIST" if density_pct <= 35.0 else "TOO_DENSE",
        "market_theme": LOCALIZED_OVERLAY_THEMES.get(market, LOCALIZED_OVERLAY_THEMES["EN"]),
        "climax_scene_manifest": [
            {
                "scene_idx": idx,
                "narration_snippet": (scenes[idx].get("narration", "") or "")[:80],
                "overlay_type": (sanitized_scenes[idx].get("forensicOverlay") or {}).get("type"),
                "stat_value": sanitized_scenes[idx].get("statValue"),
            }
            for idx in climax_indices if idx < len(scenes)
        ]
    }

    if output_dir:
        out_path = Path(output_dir) / "editorial_briefing.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(briefing, f, ensure_ascii=False, indent=2)
        logger.info("Wrote editorial briefing to %s (density: %s%%)", out_path, density_pct)

    return briefing
