"""
Service: B3 Dynamic Hollywood Art Director & Universal Scene Breakdown Engine (/director:plan)
Single Source of Truth: HHTech GPT-6-Astra + Director Plan Notion DB (5b201989-2400-8295-be81-81c2c0e4e138)
Rule 116 & 435: Dual-Layer Remotion Render Architecture (16:9 BG + 1:1 FG #FF00FF Chroma Key).
Rule 120: Audio & Subtitle Timing Sync (duration_est_sec strictly aligned with spoken narration timestamps).
Rule 128: Zero Semantic Bias. Dynamically analyzes story.txt to derive Era Anchor, physical/geographical environment,
          atmospheric lighting mood, color palette, and Dynamic Character Ensemble (4-8 roles) without static topic relics.
Rule 445: 5-Beat Investigative Docudrama storyboard structure (organic dynamic scene breakdown governed by story pacing).
Rule 446: English Production Bridge for all visual prompt descriptions.
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

import os
ROOT_DIR = Path(os.getenv("VF_ROOT_DIR", Path(__file__).resolve().parent.parent.parent))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.model_gateway import get_global_gateway
from app.services.skill_loader import (
    get_b3_strategic_rules,
    get_b35_strategic_rules,
    get_cinematic_tokens_dictionary
)
from app.services.text_to_number_parser import parse_spoken_number

DIRECTOR_PLAN_FLAT_DB_ID = "5b201989-2400-8295-be81-81c2c0e4e138"
DIRECTOR_PLAN_PARENT_PAGE_ID = "73801989-2400-82a7-ae5f-0110bfb666c8"

# 5 Beat Canonical Investigative Docudrama Names (Rule 445)
CANONICAL_BEATS = [
    "Beat 1: The Impossible Contradiction",
    "Beat 2: The False Narrative & Red Herring",
    "Beat 3: The Systemic Blindspot & Paper Trail",
    "Beat 4: The Real Culprit & Smoking Gun",
    "Beat 5: The Uncomfortable Modern Mirror & Living Warning"
]

# Rule 128: Concise targeted art direction rules (~1.2k chars) replacing 336k chars dump
TARGETED_ART_RULES = get_b3_strategic_rules()

# 6 Canonical Cinematic Camera Movements
CANONICAL_CAMERA_MOVES = [
    "slow_push_in",
    "snap_zoom",
    "cinematic_pan",
    "macro_tilt",
    "slow_pull_out",
    "handheld_shake"
]


def validate_cinematic_tokens(tokens: list | None, narration: str = "") -> list:
    """Rule 128 & Rule 132: Validate and sanitize cinematic flow tokens against the 20 canonical tokens.
    Provides deterministic fallback if LLM omitted tokens.
    """
    dict_data = get_cinematic_tokens_dictionary()
    valid_set = {t["token"] for t in dict_data.get("tokens", [])}
    if not valid_set:
        valid_set = {
            "/straightdown", "/groundlevel", "/birdseye", "/firstperson", "/secondview",
            "/closecrop", "/tightframe", "/extremeclose", "/thirdgrid", "/innerframe",
            "/darkmood", "/edgelight", "/spotbeam", "/lightrays", "/sunsetglow", "/duskhour",
            "/filmlook", "/highcontrast", "/edgefade", "/digitalglitch"
        }
    cleaned = []
    if isinstance(tokens, list):
        for tok in tokens:
            if isinstance(tok, str):
                t_str = tok.strip()
                if not t_str.startswith("/"):
                    t_str = f"/{t_str}"
                if t_str in valid_set and t_str not in cleaned:
                    cleaned.append(t_str)

    if not cleaned and narration:
        t_low = narration.lower()
        if any(k in t_low for k in ["hồ sơ", "con dấu", "hợp đồng", "bản án", "bàn làm việc", "dossier", "contract", "verdict", "document", "ledger", "seal", "stamp"]):
            cleaned = ["/straightdown", "/darkmood", "/edgelight"]
        elif any(k in t_low for k in ["biến mất", "toàn cảnh", "thành phố", "tòa nhà", "quốc gia", "hệ thống", "skyline", "scale"]):
            cleaned = ["/birdseye", "/duskhour", "/filmlook"]
        elif any(k in t_low for k in ["khuôn mặt", "nói", "thì thầm", "khai nhận", "nhìn thẳng", "eyes", "whisper", "confession"]):
            cleaned = ["/tightframe", "/darkmood", "/highcontrast"]
        else:
            cleaned = ["/thirdgrid", "/darkmood"]

    return cleaned[:3]

def _sanitize_beat_spoken_for_llm(spoken_list: list) -> list:
    """
    Prune heavy Whisper audio metadata (word-level timestamps, score arrays,
    and karaoke highlight tokens) from LLM director payload.
    Preserves exact sentence text, sentence ID, and duration budget.
    Downstream Remotion props generator retains full verbatim spoken_sentences.json.
    """
    if not spoken_list:
        return []
    lean = []
    for s in spoken_list:
        if not isinstance(s, dict):
            continue
        duration_s = s.get("duration_sec")
        if duration_s is None:
            start = s.get("start", 0)
            end = s.get("end", 0)
            duration_s = round(end - start, 2) if end > start else 5.0
        lean.append({
            "sentence_id": s.get("sentence_id") or s.get("id") or f"sent_{len(lean)+1:03d}",
            "text": s.get("text") or s.get("sentence") or "",
            "duration_sec": duration_s,
            "beat_index": s.get("beat_index", 1)
        })
    return lean



def detect_forensic_overlay(narration_text: str, theme: str = "vox_paper") -> dict | None:
    """Rule 128 & Vox Explanatory Engine: Detect tactile paper-collage evidentiary graphics."""
    if not narration_text:
        return None
    t = narration_text.lower()

    # 0. 3D Procedural Evidence Props (12fps Stop-Motion Quantized Physical Artifacts - Priority 0)
    # 0a. Financial Ledger 3D (Ledger, balance sheets, audit discrepancies, wire fraud records)
    if any(k in t for k in ["ledger", "balance sheet", "accounting record", "wire fraud", "sổ sách", "bảng cân đối", "kế toán gian lận", "dòng tiền ảo", "회계 장부", "원장"]):
        return {
            "type": "evidence_3d_prop",
            "legacy_type": "evidence_board",
            "theme": theme or "vox_paper",
            "layout": "split_right",
            "title": "CONFIDENTIAL EVIDENCE // FINANCIAL LEDGER",
            "badge": "FINANCIAL SPECIMEN",
            "sfx_cue": "stamp_slam",
            "label": "EXHIBIT B // PROCEDURAL 3D ACCOUNTING LEDGER",
            "payload": {
                "prop_type": "financial_ledger_3d",
                "evidence_id": "EXHIBIT-3D-LEDGER",
                "authentication": "VERIFIED FORENSIC DISCREPANCY",
                "stop_motion_fps": 12
            }
        }

    # 0b. Court Indictment 3D (Criminal docket, grand jury, indictment papers, prosecutor filings)
    if any(k in t for k in ["indictment", "docket", "grand jury", "prosecutor filing", "bản cáo trạng", "hồ sơ truy tố", "khởi tố vụ án", "công tố viện", "기소장", "공소장"]):
        return {
            "type": "evidence_3d_prop",
            "legacy_type": "evidence_board",
            "theme": theme or "vox_paper",
            "layout": "split_right",
            "title": "CRIMINAL INDICTMENT // US DISTRICT COURT",
            "badge": "GRAND JURY CHARGE",
            "sfx_cue": "stamp_slam",
            "label": "EXHIBIT C // PROCEDURAL 3D COURT INDICTMENT",
            "payload": {
                "prop_type": "court_indictment_3d",
                "evidence_id": "EXHIBIT-3D-INDICTMENT",
                "authentication": "UNSEALED CRIMINAL DOCKET",
                "stop_motion_fps": 12
            }
        }

    # 0c. Passport Specimen 3D (Identity theft, forged passport, ghost identities, fake credentials)
    if any(k in t for k in ["passport", "fake id", "stolen identity", "forged credential", "hộ chiếu giả", "danh tính ma", "giả mạo giấy tờ", "위조 여권", "신분증"]):
        return {
            "type": "evidence_3d_prop",
            "legacy_type": "evidence_board",
            "theme": theme or "vox_paper",
            "layout": "split_right",
            "title": "PASSPORT SPECIMEN // FRAUDULENT ID",
            "badge": "FORGED CREDENTIAL",
            "sfx_cue": "stamp_slam",
            "label": "EXHIBIT D // PROCEDURAL 3D IDENTITY EVIDENCE",
            "payload": {
                "prop_type": "passport_specimen_3d",
                "evidence_id": "EXHIBIT-3D-PASSPORT",
                "authentication": "FRAUDULENT SPECIMEN DETECTED",
                "stop_motion_fps": 12
            }
        }

    # 0d. Legal Contract 3D (Shell contracts, bogus agreements, backdated clauses, fake service terms)
    if any(k in t for k in ["bogus contract", "shell contract", "backdated", "sham agreement", "hợp đồng khống", "thỏa thuận ma", "điều khoản giả", "위장 계약서"]):
        return {
            "type": "evidence_3d_prop",
            "legacy_type": "evidence_board",
            "theme": theme or "vox_paper",
            "layout": "split_right",
            "title": "LEGAL CONTRACT // SHELL AGREEMENT",
            "badge": "SHAM CONTRACT",
            "sfx_cue": "stamp_slam",
            "label": "EXHIBIT E // PROCEDURAL 3D CONTRACT SPECIMEN",
            "payload": {
                "prop_type": "legal_contract_3d",
                "evidence_id": "EXHIBIT-3D-CONTRACT",
                "authentication": "NON-ARM'S-LENGTH INSTRUMENT",
                "stop_motion_fps": 12
            }
        }

    # 0e. Hanko / Imperial Seal 3D (Physical wax seals, stamps, warrants, authentications)
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
                "authentication": "VERIFIED PHYSICAL TAMPER-PROOF",
                "stop_motion_fps": 12
            }
        }

    # 1. Document Highlight (Contracts, clauses, terms, NDA, redactions, audits, subpoenas, official files)
    if any(k in t for k in ["contract", "clause", "redact", "nda", "audit", "dossier", "agreement", "classified", "subpoena", "record", "records", "inspection", "capacity", "license", "hợp đồng", "điều khoản", "tài liệu", "biên bản", "thanh tra", "hồ sơ", "chứng cứ", "조항", "감사", "서류"]):
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
                "highlight_line_index": 1 if len(clauses) > 1 else 0,
                "redacted_terms": ["CONFIDENTIAL", "UNVERIFIED", "不適切"],
                "date": "OFFICIAL RECORD // VERIFIED"
            }
        }

    # 2. Tactical Map (Flight, plane, radar, coordinates, vanish, crash, route, locations, surveillance, CCTV)
    if any(k in t for k in ["flight", "plane", "radar", "altitude", "coordinate", "vanish", "crash", "air traffic", "route", "chuyến bay", "đường bay", "tọa độ", "rơi", "rada", "chokepoint", "strait", "sea lane", "eo biển", "hải trình", "surveillance", "cctv", "camera", "facility", "address", "location", "locations", "street", "city", "county", "district", "cơ sở", "địa điểm", "địa chỉ", "khu vực", "시설", "주소", "위치", "warehouse", "giám sát", "seismic zone", "bản đồ", "지도", "좌표", "震源", "南海トラフ", "駿河湾"]):
        is_jp = any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in narration_text)
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
                "target_name": "浜岡原子力発電所 プラントサイト" if is_jp else "OPERATIONAL SITE // VERIFIED SECTOR",
                "coordinates": "34.62° N, 138.14° E (静岡県 御前崎市)" if is_jp else "TARGET REGION JURISDICTION",
                "map_region": "駿河湾沿岸 耐震・地殻変動セクター" if is_jp else "INVESTIGATIVE DISTRICT",
                "points_of_interest": ["3号機・4号機 原子炉建屋", "基準地震動観測点", "防潮堤 22m区間"] if is_jp else ["PRIMARY HUB", "INTERMEDIARY CHOKEPOINT", "ESCROW DISBURSEMENT"]
            }
        }

    # 3. Kinetic Counter / Financial Ledger (Strict: requires verified parsed number, Rule 118 Zero-Mock Data)
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
                "suspect_name": "PRIMARY TARGET // NOMINEE OPERATOR",
                "role": "UNLICENSED SHELL OPERATOR / FALSE DISBURSEMENT",
                "charges": [
                    "STATUTORY COMPLIANCE VIOLATION",
                    "SUBMISSION OF INCONSISTENT RECORD FILINGS"
                ],
                "connected_entities": ["REGULATORY OVERSIGHT DESK", "OPERATIONAL FACILITY", "FILING AUDIT ARCHIVE"],
                "evidence_tag": "OFFICIAL CASE EXHIBIT"
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

    return None


def detect_object_focus(narration_text: str, topic: str = "") -> dict | None:
    """Detect or synthesize an object_focus dictionary from narration text (Rule 118/128/VOX)."""
    if not narration_text:
        return None
    t = narration_text.lower()
    
    # 1. Court Docket / Legal Complaint / Indictment / Lawsuit
    if any(k in t for k in ["lawsuit", "complaint", "sue", "court", "judge", "docket", "indictment", "violation", "legal", "prosecutor", "antitrust", "ftc", "đơn kiện", "tòa án", "truy tố", "pháp lý", "chống độc quyền", "소송", "고소", "기소", "법원", "반독점"]):
        return {
            "type": "court_docket",
            "title": "DISTRICT COURT // OFFICIAL FILING",
            "agency": "REGULATORY ENFORCEMENT COMMISSION",
            "source_ref": "DOCKET CASE RECORD // UNSEALED",
            "key_snippet": narration_text[:70].strip(),
            "stat_metric": None
        }
    # 2. Redacted Memo / Secret Agreement / Internal Memo
    if any(k in t for k in ["memo", "internal", "confidential", "nda", "secret", "email", "slack", "unredacted", "tài liệu mật", "nội bộ", "thỏa thuận", "thư mật", "비밀", "내부", "기밀"]):
        return {
            "type": "redacted_memo",
            "title": "EXECUTIVE MEMORANDUM // RESTRICTED",
            "agency": "INTERNAL COMPLIANCE AUDIT",
            "source_ref": "EXHIBIT MEMO-FORENSIC",
            "key_snippet": narration_text[:70].strip(),
            "stat_metric": None
        }
    # 3. Financial Ledger / Accounting Discrepancy
    if any(k in t for k in ["ledger", "balance", "accounting", "audit", "revenue", "margin", "loss", "profit", "sổ sách", "kế toán", "doanh thu", "lợi nhuận", "thua lỗ", "장부", "매출", "손실"]):
        return {
            "type": "financial_ledger",
            "title": "AUDIT LEDGER // FINANCIAL STATEMENT",
            "agency": "OFFICIAL AUDIT EXAMINER",
            "source_ref": "LEDGER DISCREPANCY RECORD",
            "key_snippet": narration_text[:70].strip(),
            "stat_metric": None
        }
    # 4. Money Trail Network / Wire Transactions
    if any(k in t for k in ["wire", "transfer", "offshore", "shell", "escrow", "flow", "launder", "fees", "cut", "chuyển khoản", "dòng tiền", "rửa tiền", "phí hoa hồng", "cắt phế", "송금", "우회", "자금 흐름", "수수료"]):
        return {
            "type": "money_trail_network",
            "title": "TRANSACTION NETWORK // CAPITAL FLOW",
            "agency": "FINANCIAL CRIMES ENFORCEMENT",
            "source_ref": "TRANSMISSION CHOKEPOINT",
            "key_snippet": narration_text[:70].strip(),
            "stat_metric": None
        }
    # 5. Corporate Org Chart / Hierarchy
    if any(k in t for k in ["subsidiary", "parent company", "board", "executive", "hierarchy", "holding", "monopoly", "sellers", "merchants", "tập đoàn", "công ty con", "hội đồng", "độc quyền", "người bán", "지주회사", "계열사", "독점"]):
        return {
            "type": "corporate_org_chart",
            "title": "CORPORATE STRUCTURE // MARKET DOMINANCE",
            "agency": "REGISTRATION BUREAU",
            "source_ref": "ENTITY FILING ARCHIVE",
            "key_snippet": narration_text[:70].strip(),
            "stat_metric": None
        }
    return None


def detect_layout_zone(has_fg: bool, fg_position: str = "right", scene_idx: int = 0) -> dict:
    """Detect layout_zone based on FG presence and spatial alternation (Rule 122)."""
    if not has_fg:
        placements = ["center_hero_document", "macro_detail_focus"]
        placement = placements[scene_idx % len(placements)]
        cam_axis = ["horizontal", "push_punch", "vertical"][scene_idx % 3]
        return {
            "placement": placement,
            "safe_zone": "bottom_left",
            "camera_pan_axis": cam_axis
        }
    else:
        if fg_position == "left":
            return {
                "placement": "split_evidence_right",
                "safe_zone": "bottom_right",
                "camera_pan_axis": "horizontal"
            }
        else:
            return {
                "placement": "split_evidence_left",
                "safe_zone": "bottom_left",
                "camera_pan_axis": "horizontal"
            }


def detect_animation_cue(narration_text: str, object_focus: dict = None) -> dict:
    """Detect or synthesize an animation_cue dictionary from narration text (Rule 120/122)."""
    if not narration_text:
        return {
            "effect": "yellow_marker_highlight",
            "trigger_word": "",
            "duration_frames": 24
        }
    
    words = re.findall(r"\w+", narration_text)
    first_word = words[0] if words else ""
    t = narration_text.lower()

    # Counter Rollup
    if any(k in t for k in ["$", "%", "billion", "million", "triệu", "tỷ", "percent", "đô la", "won", "yen", "usd", "억", "조"]):
        trigger = first_word
        for w in words:
            if any(c.isdigit() for c in w) or w.lower() in ["billion", "million", "percent", "tỷ", "triệu"]:
                trigger = w
                break
        return {
            "effect": "counter_rollup",
            "trigger_word": trigger,
            "duration_frames": 30
        }

    # Red Stamp Slam
    if any(k in t for k in ["fraud", "illegal", "guilty", "busted", "seized", "void", "breach", "vi phạm", "gian lận", "bị bắt", "vô hiệu", "bất hợp pháp", "위반", "사기", "무효"]):
        trigger = first_word
        for w in words:
            if w.lower() in ["fraud", "illegal", "violation", "breach", "gian lận", "vi phạm", "사기", "위반"]:
                trigger = w
                break
        return {
            "effect": "red_stamp_slam",
            "trigger_word": trigger,
            "duration_frames": 18
        }

    # Flowchart Arrow Grow
    if any(k in t for k in ["route", "channel", "path", "flow", "through", "via", "chuyển qua", "dẫn đến", "kết nối", "경로", "통해"]):
        return {
            "effect": "flowchart_arrow_grow",
            "trigger_word": words[min(2, len(words) - 1)] if words else "",
            "duration_frames": 24
        }

    # Default: Yellow Marker Highlight on central phrase
    trigger = words[min(3, len(words) - 1)] if len(words) > 3 else (words[0] if words else "")
    return {
        "effect": "yellow_marker_highlight",
        "trigger_word": trigger,
        "duration_frames": 24
    }


def detect_frame_transition(camera_movement: str, tension_level: str, scene_idx: int = 0) -> dict:
    """Detect frame_transition and SFX punctuation."""
    if camera_movement in ("snap_zoom", "handheld_shake"):
        return {"type": "macro_zoom_through", "sfx_cue": "stamp_thud"}
    elif camera_movement in ("cinematic_pan",):
        trans_type = "whip_pan_left" if scene_idx % 2 == 0 else "whip_pan_right"
        return {"type": trans_type, "sfx_cue": "camera_whoosh"}
    elif tension_level in ("climax", "extreme"):
        return {"type": "match_cut", "sfx_cue": "paper_rustle"}
    elif scene_idx % 4 == 0:
        return {"type": "film_dissolve", "sfx_cue": "paper_rustle"}
    else:
        return {"type": "hard_cut", "sfx_cue": "digital_beep"}


def detect_stat_card(narration_text: str) -> dict | None:
    """Rule 122 & Rule 128: Extract prominent financial metrics or evidentiary scales for Remotion Stat Card."""
    if not narration_text:
        return None

    parsed = parse_spoken_number(narration_text)
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
        return {"value": parsed.formatted, "label": label}

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
        m = re.search(p, narration_text, re.IGNORECASE)
        if m:
            val = m.group(1).upper().strip()
            if len(val) >= 2:
                return {"value": val, "label": label}
    return None


def detect_stamp_badge(narration_text: str) -> str | None:
    """Rule 122: Detect high-stakes evidence stamp slam trigger for Remotion ForensicStampBadge."""
    if not narration_text:
        return None
    t = narration_text.lower()
    if any(k in t for k in ["gian lận", "lừa đảo", "vi phạm", "사기", "위반", "부당", "환불 거부", "fraud", "violation", "illegal"]):
        return "PRICE_FRAUD"
    if any(k in t for k in ["tài liệu mật", "hợp đồng mật", "비밀", "기밀", "confidential", "classified", "nda"]):
        return "CONFIDENTIAL"
    if any(k in t for k in ["bằng chứng", "chứng cứ", "vết nứt", "증거", "단서", "evidence", "proof"]):
        return "EVIDENCE"
    if any(k in t for k in ["hủy bỏ", "vô hiệu", "취소", "무효", "void", "breach"]):
        return "VOID"
    return None


class DynamicArchetypeDict(dict):
    """Rule 128: Zero-Semantic-Bias Dynamic Archetype Registry with backward compatibility."""
    def __missing__(self, key):
        return {
            "director": f"Investigative Cinematic Docudrama ({str(key).title()} Style)",
            "visual_tone": f"Atmospheric authentic narrative environment reflecting {key}",
            "palette": "Desaturated earthy ochre, slate grey, muted ambient contrasts",
            "camera_style": "Slow creeping push-ins, atmospheric tracking, high-tension staging"
        }


# 7 Golden Content Axes (Notion SoT Second Brain & Hollywood Principles)
CINEMATIC_ARCHETYPES = DynamicArchetypeDict({
    "business_rise_fall": {
        "director": "GPT-6-Astra — David Fincher & Adam McKay (Corporate Noir & Forensic Exposition) Principle",
        "visual_tone": "Glossy corporate boardroom veneer contrasting cold trading floors, shredded paper trails, creeping push-ins on forensic ledger anomalies",
        "palette": "Cold steel blue, dark charcoal, toxic amber highlights, fluorescent office hum",
        "camera_style": "Slow creeping push-ins on financial ledgers, clinical wide corporate establishing shots, whip pans on margin calls"
    },
    "systemic_crisis": {
        "director": "GPT-6-Astra — Johan Renck & Denis Villeneuve (Oppressive Institutional Realism & Brutal Scale) Principle",
        "visual_tone": "Monumental institutional corridors, decaying supply chain depots, heavy dust beams through fractured blinds, systemic infrastructure collapse",
        "palette": "Desaturated slate stone, oxidized bronze, aged ochre, industrial charcoal, deep chiaroscuro",
        "camera_style": "Slow deliberate surveillance tracking, high-angle institutional scale observation, lingering frozen tableaux"
    },
    "true_crime": {
        "director": "GPT-6-Astra — David Fincher & Errol Morris (Forensic Procedural Noir — Non-Graphic) Principle",
        "visual_tone": "Evidence locker dim lighting, sterile courtroom benches, macro document forgery examinations, high-contrast interrogation rooms",
        "palette": "Low-key obsidian black, desaturated neutral slate, cold fluorescent white, deep chiaroscuro shadows",
        "camera_style": "Precision analytical tracking, tight macro close-ups on physical evidence, static high-tension procedural compositions"
    },
    "psychology": {
        "director": "GPT-6-Astra — Denis Villeneuve & Darren Aronofsky (Psychological Mystery & Geometric Disorientation) Principle",
        "visual_tone": "Claustrophobic interrogation spaces, symbolic geometric architectural framing, disorienting shadow play dissecting herd bias and manipulation",
        "palette": "Deep graphite monochrome with solitary amber/crimson focal accents, psychological shadow contrasts",
        "camera_style": "Creeping slow push-ins creating psychological intimacy, symmetrical wide tableaus, abrupt perspective shifts"
    },
    "tech_geopolitics": {
        "director": "GPT-6-Astra — Christopher Nolan (Cold Analytical Precision & Global Asymmetric Stakes) Principle",
        "visual_tone": "Humming photolithography cleanrooms, submarine fiber-optic cable routes, satellite command telemetry, dark geopolitical summit chambers",
        "palette": "Silicon cyan, cleanroom amber, server rack emerald, cold titanium silver, deep surveillance indigo",
        "camera_style": "Clinical surveillance pans, sharp graphic whip-cuts between maps and hardware, high-angle technological dominance framing"
    },
    "institutional_regulatory": {
        "director": "GPT-6-Astra — Steven Soderbergh & Michael Mann (Clinical Whistleblower & Regulatory Chokepoint) Principle",
        "visual_tone": "Municipal registry desks, confidential inspection archives with red rejected stamps, sealed sample containers, late-night whistleblowing meetings",
        "palette": "Clinical pale cyan, antiseptic mint green, institutional beige, iodine amber, brushed stainless steel",
        "camera_style": "Forensic macro close-ups on regulatory clause stamps and approval dates, handheld observational creeping push-ins, clinical wide archive corridors"
    },
    "asymmetric_flows": {
        "director": "GPT-6-Astra — Martin Scorsese & J.C. Chandor (Asymmetric Financial Thriller & Underground Flows) Principle",
        "visual_tone": "Discreet offshore private banking suites, encrypted dark-terminal trading desks, luxury maritime harbors concealing shell company assets",
        "palette": "Deep velvet midnight blue, tarnished brass gold, dark burgundy, cigar-smoke chiaroscuro",
        "camera_style": "Slow predator tracking shots, clinical over-the-shoulder document inspections, abrupt freezing snap-zooms on hidden beneficiary names"
    },
    "consumer_injustice_institutional_trap": {
        "director": "GPT-6-Astra — Adam McKay & Laurent Cantet (Social Reality & Everyday Institutional Entrapment) Principle",
        "visual_tone": "Fluorescent consumer dispute consultation rooms, corporate storefront refund denial counters with bold exclusion notices, dense fine-print contract binders, everyday citizens confronting institutional stonewalling",
        "palette": "Institutional beige, muted slate olive, fluorescent pale blue, warning amber stamp highlights",
        "camera_style": "Macro tilts over hidden exclusion clauses, static confrontation two-shots, sudden snap zooms on predatory fine print"
    },
    "default": {
        "director": "GPT-6-Astra — Denis Villeneuve & David Fincher (Investigative Realism) Principle",
        "visual_tone": "Moody atmospheric tension, dramatic low-key lighting, textured architectural backgrounds, forensic depth of field",
        "palette": "Muted earth tones, cinematic contrast, shadow-heavy rim lighting",
        "camera_style": "Creeping push-ins, dynamic eye-level forensic staging, dramatic low-angle power shots"
    }
})

# Backward compatibility aliases for legacy callers and tests
CINEMATIC_ARCHETYPES["finance"] = CINEMATIC_ARCHETYPES["business_rise_fall"]
CINEMATIC_ARCHETYPES["history"] = CINEMATIC_ARCHETYPES["systemic_crisis"]
CINEMATIC_ARCHETYPES["consumer_injustice"] = CINEMATIC_ARCHETYPES["consumer_injustice_institutional_trap"]


def detect_cinematic_archetype(niche: str = "", topic: str = "", story_text: str = "") -> dict:
    """
    Universal dynamic cinematic archetype and visual grammar detection (Rule 128).
    Routes dynamically based on the 7 Golden Content Axes (Notion SoT Second Brain).
    """
    combined = f"{niche} {topic} {story_text[:600]}".lower()

    # 1. Consumer Injustice & Everyday Institutional Traps (Pillar 11)
    if any(k in combined for k in ["consumer", "refund", "trap", "fine print", "arbitration", "dispute", "tiêu dùng", "hoàn tiền", "bẫy", "hợp đồng tiêu dùng", "환불", "약관", "소비자", "분쟁", "조정", "구글스토어", "전자제품"]):
        return CINEMATIC_ARCHETYPES["consumer_injustice_institutional_trap"]

    # 2. Tech & Geopolitical Battles
    elif any(k in combined for k in ["tech", "chip", "semiconductor", "asml", "tsmc", "silicon", "geopolitic", "supply chain", "cable", "satellite", "cyber", "hardware", "lithography", "quantum"]):
        return CINEMATIC_ARCHETYPES["tech_geopolitics"]

    # 2. Institutional & Regulatory Chokepoints / Medical / Whistleblower
    elif any(k in combined for k in [
        "regulatory", "chokepoint", "inspector", "compliance", "oversight", "pension", "license", "permit", "coverup",
        "recall", "medical", "pharma", "clinical", "hospital", "drug", "medicine", "vaccine", "toxic", "poison", "epidemic",
        "cholera", "pesticide", "whistleblower",
        # Korean
        "내부고발", "규제", "감독", "식약처", "보건", "인허가", "은폐", "부실감사",
        # Vietnamese
        "thanh tra", "giám sát", "nội bộ", "y tế", "thu hồi", "che giấu", "giấy phép",
        # Japanese
        "内部告発", "規制", "監督", "隠蔽", "認可", "不祥事"
    ]):
        return CINEMATIC_ARCHETYPES["institutional_regulatory"]

    # 3. Hidden Asymmetric Fortunes & Underground Flows
    elif any(k in combined for k in ["underground", "illicit", "laundering", "smuggl", "offshore", "shell company", "shadow banking", "dark pool", "cartel", "asymmetric", "hidden fortune", "bribe", "kickback"]):
        return CINEMATIC_ARCHETYPES["asymmetric_flows"]

    # 4. True Crime Non-Graphic
    elif any(k in combined for k in ["crime", "murder", "killer", "investigation", "forensic", "court", "trial", "verdict", "police", "detective", "fbi", "heist"]):
        return CINEMATIC_ARCHETYPES["true_crime"]

    # 5. Psychology & Behavioral Manipulation
    elif any(k in combined for k in ["psycholog", "manipulat", "cult", "mind", "behavior", "brainwash", "cognitive", "hysteria", "bias", "propaganda", "societal", "mass panic"]):
        return CINEMATIC_ARCHETYPES["psychology"]

    # 6. Business Rise & Fall / Corporate Debt / Financial Fraud / Embezzlement
    elif any(k in combined for k in [
        "finance", "economy", "bank", "money", "fraud", "wall street", "debt", "lehman", "madoff", "enron",
        "trading", "business", "rehabilitation", "bankruptcy", "collateral", "lien", "embezzle", "audit failure",
        # Korean
        "횡령", "공금", "회계", "감사", "장부", "자금", "분식회계", "배임", "부실", "적정", "재정", "파산", "금융", "부채", "증권", "은행", "비자금",
        # Vietnamese
        "tham ô", "kiểm toán", "gian lận", "ngân hàng", "kế toán", "tài chính", "báo cáo tài chính", "rửa tiền", "nợ xấu", "phá sản",
        # Japanese
        "横領", "粉飾決算", "監査", "裏金", "公金", "破産", "債務", "銀行", "金融", "不正会計"
    ]):
        return CINEMATIC_ARCHETYPES["business_rise_fall"]

    # 7. Modern History & Systemic Crisis
    elif any(k in combined for k in ["history", "empire", "war", "monarchy", "oppenheimer", "manhattan project", "soviet", "cold war", "chernobyl", "medieval", "century", "labor day", "strike", "crisis"]):
        return CINEMATIC_ARCHETYPES["systemic_crisis"]

    return CINEMATIC_ARCHETYPES["default"]


# Universal spatial indicators for dynamic environment extraction
SPATIAL_INDICATORS = [
    "field", "farm", "valley", "village", "town", "city", "province", "district",
    "depot", "warehouse", "facility", "plant", "factory", "dock", "harbor", "port",
    "chamber", "room", "hall", "corridor", "boardroom", "office", "headquarters",
    "archive", "laboratory", "lab", "clinic", "hospital", "ward", "station", "terminal",
    "street", "alley", "square", "road", "quarry", "mine", "compound", "complex", "market"
]

AGENT_STEMS = [
    "investigator", "inspector", "analyst", "auditor", "specialist", "researcher", "scientist", "toxicologist",
    "physician", "doctor", "epidemiologist", "chemist", "biologist", "engineer", "technician",
    "official", "regulator", "director", "manager", "administrator", "executive", "officer", "commissioner",
    "witness", "eyewitness", "informant", "whistleblower", "insider", "clerk", "custodian", "archivist",
    "farmer", "cultivator", "grower", "worker", "laborer", "operator", "merchant", "trader", "dealer",
    "broker", "banker", "accountant", "lawyer", "attorney", "prosecutor", "judge",
    "journalist", "reporter", "curate", "resident", "villager", "citizen", "survivor"
]

STOP_MODIFIERS = {
    "the", "a", "an", "this", "that", "these", "those", "each", "every", "some", "any", "all",
    "in", "on", "at", "by", "with", "from", "to", "for", "of", "and", "or", "as", "into", "meanwhile",
    "however", "later", "then", "when", "while", "during", "after", "before", "several", "arrived"
}


def extract_universal_semantic_context(story_text: str, metadata: dict = None, intel_card: dict = None) -> dict:
    """
    Universal Dynamic Semantic Context & Era Extractor (Rule 128 - Zero Semantic Bias).
    Directly analyzes story.txt to derive Era Anchor, physical/geographical environment,
    lighting mood, and color palette without static hardcoded dictionaries or topic conditionals.
    """
    if not metadata:
        metadata = {}
    if not intel_card:
        intel_card = {}

    story_lower = story_text.lower()

    # 1. Dynamic Era Anchor Extraction
    era_anchor = "Contemporary investigative documentary setting with period-authentic documentation and architecture"
    years = [int(y) for y in re.findall(r"\b(1[5-9]\d{2}|20\d{2})\b", story_text)]
    if years:
        min_y = min(years)
        max_y = max(years)
        if max_y < 1900:
            cent = (max_y // 100) + 1
            suf = "th" if 11 <= cent <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(cent % 10, "th")
            era_anchor = f"{cent}{suf} Century (circa {min_y if min_y == max_y else f'{min_y}–{max_y}'}) with authentic period architecture and documentation"
        elif max_y < 1945:
            era_anchor = f"Early 20th Century era (circa {min_y if min_y == max_y else f'{min_y}–{max_y}'}) with period-authentic documentation and architecture"
        elif max_y < 1990:
            dec = (max_y // 10) * 10
            era_anchor = f"Mid-to-Late 20th Century ({dec}s era) with period-accurate setting and archival records"
        elif max_y < 2010:
            era_anchor = f"Turn of the 21st Century (circa {min_y if min_y == max_y else f'{min_y}–{max_y}'}) investigative setting with contemporary documentation"
        else:
            era_anchor = f"Contemporary era (circa {max_y}) with modern investigative documentation, setting, and infrastructure"
    else:
        cent_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+century\b", story_lower)
        if cent_match:
            era_anchor = f"{cent_match.group(1)}th Century historical period setting with authentic architecture and era documentation"
        else:
            decade_match = re.search(r"\b(19\d0s|20\d0s)\b", story_lower)
            if decade_match:
                era_anchor = f"{decade_match.group(1)} period investigative setting with era-authentic documentation and architecture"
            else:
                period_cues = []
                for term in ["victorian", "edwardian", "medieval", "feudal", "colonial", "ancient", "renaissance", "industrial revolution", "cold war", "post-war", "contemporary"]:
                    if re.search(r"\b" + re.escape(term) + r"\b", story_lower):
                        period_cues.append(term.title())
                if period_cues:
                    era_anchor = f"{', '.join(period_cues[:2])} era investigative setting with period-authentic architecture and documentation"

    # 2. Dynamic Physical & Geographical Environment Extraction
    env_cues = []
    seen_spaces = set()
    sentences = re.split(r"(?<=[.!?])\s+", story_text)
    for sent in sentences:
        for space in SPATIAL_INDICATORS:
            if space in seen_spaces:
                continue
            m = re.search(r"\b([A-Za-z-]+(?:\s+[A-Za-z-]+)?)\s+" + re.escape(space) + r"(?:s|es)?\b", sent, re.IGNORECASE)
            if m:
                pre = m.group(1).strip()
                pre_words = [w for w in pre.split() if w.lower() not in STOP_MODIFIERS]
                if pre_words:
                    env_chunk = f"{' '.join(pre_words).lower()} {space}"
                else:
                    env_chunk = f"{space} setting"
                seen_spaces.add(space)
                env_cues.append(env_chunk)
                if len(env_cues) >= 4:
                    break
        if len(env_cues) >= 4:
            break

    if env_cues:
        physical_environment = f"Authentic narrative environment: {'; '.join(env_cues)}, reflecting primary setting locations and institutional archives"
    else:
        topic_hint = metadata.get("topic") or intel_card.get("target_keyword", "Investigative Setting")
        topic_clean = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", "", str(topic_hint)).strip()
        clean_env_label = topic_clean if len(topic_clean) >= 3 else "authentic documentary setting"
        physical_environment = f"Authentic narrative environment reflecting {clean_env_label}, with dedicated field operational sites and archival document repositories"

    # 3. Dynamic Atmospheric Lighting Mood
    lighting_cues = []
    for cue in ["dawn", "morning", "twilight", "dusk", "sunset", "night", "midnight", "nocturnal",
                "fog", "mist", "haze", "rain", "storm", "overcast", "cloudy", "smoke", "dust",
                "fluorescent", "gaslit", "candlelit", "neon", "low-key", "chiaroscuro", "shadow", "dim", "flicker"]:
        if re.search(r"\b" + re.escape(cue) + r"\b", story_lower):
            lighting_cues.append(cue)

    if lighting_cues:
        lighting_mood = f"Cinematic documentary chiaroscuro with motivated directional lighting, capturing {', '.join(lighting_cues[:3])} atmosphere and textured low-key shadows"
    else:
        lighting_mood = "Cinematic documentary chiaroscuro with motivated directional lighting, dramatic low-key contrast and textured atmospheric shadows"

    # 4. Dynamic Color Palette
    color_cues = []
    for c in ["slate", "charcoal", "ochre", "amber", "sepia", "rust", "bronze", "patina", "emerald",
              "crimson", "cobalt", "cyan", "gold", "silver", "steel", "terracotta", "olive", "sage"]:
        if re.search(r"\b" + re.escape(c) + r"\b", story_lower):
            color_cues.append(c)

    if color_cues:
        color_palette = f"Cinematic desaturated palette featuring {', '.join(color_cues[:4])}, deep charcoal shadows, and naturalistic atmospheric contrast"
    else:
        if "19th" in era_anchor or "victorian" in era_anchor.lower() or "early 20th" in era_anchor.lower():
            color_palette = "Muted historical earth pigments, aged sepia, oxidized patina, iron rust, and deep charcoal shadows"
        else:
            color_palette = "Desaturated cinematic tones, muted natural pigments, charcoal blacks, and naturalistic contrast highlights"

    return {
        "era_anchor": era_anchor,
        "physical_environment": physical_environment,
        "lighting_mood": lighting_mood,
        "color_palette": color_palette
    }


def extract_dynamic_character_ensemble(story_text: str, dynamic_context: dict = None, topic: str = "") -> list[dict]:
    """
    Universal Dynamic Character Ensemble Extractor (Rule 128 - Zero Semantic Bias).
    Extracts 4-8 distinct character roles authentic to the narrative from story.txt.
    Parses narrative agent nouns and actions without hardcoded topic conditionals.
    Each character contains: role_name, archetype, visual_cues, attire.
    """
    if not dynamic_context:
        dynamic_context = {}
    era = dynamic_context.get("era_anchor", "").lower()

    roles = []
    seen_stems = set()
    sentences = re.split(r"(?<=[.!?])\s+", story_text)

    pattern = re.compile(
        r"\b(?:(?:the|a|an|with|from|by|at|in)\s+)?([A-Za-z-]+(?:\s+[A-Za-z-]+)?)\s+(" +
        "|".join(AGENT_STEMS) + r")(?:s|es)?\b",
        re.IGNORECASE
    )

    for sent in sentences:
        for match in pattern.finditer(sent):
            mod, noun = match.groups()
            stem = noun.lower()
            if stem in seen_stems:
                continue

            mod_words = [w for w in mod.split() if w.lower() not in STOP_MODIFIERS]
            if mod_words:
                role_name = f"{' '.join(mod_words).title()} {noun.title()}"
            else:
                role_name = f"{noun.title()}"

            seen_stems.add(stem)

            # Archetype derived from narrative function
            if any(k in stem for k in ["investigator", "inspector", "auditor", "researcher", "detective"]):
                archetype = "Meticulous & skeptical investigator tracing anomalies"
            elif any(k in stem for k in ["witness", "eyewitness", "resident", "villager", "citizen", "survivor", "farmer", "cultivator"]):
                archetype = "Observant & vigilant local eyewitness holding key testimony"
            elif any(k in stem for k in ["official", "regulator", "director", "manager", "administrator", "executive", "officer", "commissioner"]):
                archetype = "Conflicted & guarded institutional authority facing scrutiny"
            elif any(k in stem for k in ["scientist", "analyst", "physician", "doctor", "epidemiologist", "toxicologist", "chemist"]):
                archetype = "Clinical & objective scientific analyst uncovering empirical evidence"
            elif any(k in stem for k in ["whistleblower", "insider", "informant"]):
                archetype = "Anxious & resolute insider exposing hidden misconduct"
            else:
                archetype = "Focused & methodical key participant in the narrative"

            # Attire harmonized with era and role function
            if any(k in era for k in ["19th", "victorian", "edwardian"]):
                attire = "period-authentic 19th-century Victorian attire, wool frock coat or work apron, sturdy leather boots"
            elif any(k in era for k in ["early 20th", "mid-to-late 20th", "cold war", "1970", "1980"]):
                attire = "period-authentic mid-20th-century vintage trench coat or pressed collared workwear"
            else:
                if any(k in stem for k in ["farmer", "cultivator", "worker", "laborer", "grower"]):
                    attire = "utilitarian outdoor work jacket, weathered canvas pants, durable boots"
                elif any(k in stem for k in ["scientist", "analyst", "physician", "doctor", "toxicologist", "chemist"]):
                    attire = "sanitary laboratory coat, protective gloves, analytical attire"
                elif any(k in stem for k in ["executive", "director", "auditor", "manager", "lawyer", "attorney"]):
                    attire = "tailored formal executive suit, crisp collared shirt, professional dress shoes"
                else:
                    attire = "durable utilitarian field jacket, pressed trousers, sturdy shoes"

            # Visual Cues extracted from sentence action
            action_match = re.search(r"\b(examining|inspecting|discovering|reviewing|tracking|holding|uncovering|documenting|interviewing|testing)\s+([a-z\s]{5,35})\b", sent, re.IGNORECASE)
            if action_match:
                visual_cues = f"{action_match.group(1).lower()} {action_match.group(2).strip()}, observed in scene context"
            else:
                visual_cues = "examining critical physical documentation and artifacts in scene setting"

            roles.append({
                "role_name": role_name,
                "archetype": archetype,
                "visual_cues": visual_cues,
                "attire": attire
            })

            if len(roles) >= 8:
                break
        if len(roles) >= 8:
            break

    # Guarantee 4-8 roles using generic docudrama ensemble customized to era
    generic_archetypes = [
        ("Lead Field Investigator", "Meticulous & skeptical investigator tracing anomalies", "holding evidence dossier, reviewing records", "durable utilitarian trench coat and work trousers"),
        ("Primary Field Eyewitness", "Observant & vigilant local eyewitness holding key testimony", "standing cautiously, observing surrounding setting", "authentic civilian workwear appropriate to setting"),
        ("Administrative Oversight Official", "Conflicted & guarded institutional authority facing scrutiny", "presenting official compliance binder with stern expression", "formal municipal suit with administrative badge"),
        ("Forensic Evidence Analyst", "Clinical & objective scientific analyst uncovering empirical evidence", "inspecting physical sample container with magnifying lens", "protective laboratory jacket and utility gloves"),
        ("Archival Records Custodian", "Weary & meticulous guardian of institutional memory", "pulling heavy archival cardboard evidence box from metal shelving", "cardigan sweater over oxford shirt, spectacles on cord"),
        ("Institutional Strategic Director", "Conflicted figurehead facing public exposure", "standing before official conference table, reviewing internal memo", "formal tailored institutional suit, executive demeanor")
    ]
    gen_idx = 0
    while len(roles) < 4 and gen_idx < len(generic_archetypes):
        g_name, g_arch, g_cues, g_attire = generic_archetypes[gen_idx]
        if not any(g_name.lower() in r["role_name"].lower() for r in roles):
            roles.append({
                "role_name": g_name,
                "archetype": g_arch,
                "visual_cues": g_cues,
                "attire": g_attire
            })
        gen_idx += 1

    return roles[:8]


def extract_story_beats(story_text: str) -> list[dict]:
    """Parse story into 5 beats if headers exist, or divide dynamically."""
    beats = []
    current_beat_title = ""
    current_lines = []

    beat_patterns = [
        re.compile(r"^(?:={2,}\s*)?(?:#+\s*)?(?:ACT|BEAT)\s*([1-5]|IV|I{1,3}|V)[:\-\s=]*(.*)", re.IGNORECASE),
        re.compile(r"^(?:##\s*)?(The Impossible Contradiction|The False Narrative|The Systemic Blindspot|The Real Culprit|The Uncomfortable Modern Mirror)", re.IGNORECASE)
    ]

    for line in story_text.splitlines():
        matched = False
        for p in beat_patterns:
            m = p.match(line.strip())
            if m:
                if current_lines:
                    beats.append({
                        "title": current_beat_title or f"Beat {len(beats) + 1}",
                        "content": "\n".join(current_lines).strip()
                    })
                    current_lines = []
                current_beat_title = line.strip().strip("=").strip("#").strip()
                matched = True
                break
        if not matched:
            current_lines.append(line)

    if current_lines:
        beats.append({
            "title": current_beat_title or f"Beat {len(beats) + 1}",
            "content": "\n".join(current_lines).strip()
        })

    # If story didn't have explicit beat headers, divide into 5 chunks
    if len(beats) < 5:
        all_lines = [l for l in story_text.splitlines() if l.strip()]
        chunk_size = max(1, len(all_lines) // 5)
        beats = []
        for i in range(5):
            chunk = all_lines[i * chunk_size : (i + 1) * chunk_size] if i < 4 else all_lines[i * chunk_size :]
            beats.append({
                "title": CANONICAL_BEATS[i],
                "content": "\n".join(chunk).strip()
            })

    return beats[:5]


def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merge update dict into base dict without destructive overwriting."""
    result = dict(base)
    for k, v in update.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _is_valid_audio_spine(spoken_sentences: Optional[List[Dict[str, Any]]], dirs: List[Path]) -> bool:
    """Validate that Hollywood Audio Spine exists and is timecode-locked (Rule 120/127).
    Must satisfy:
    1. spoken_sentences is a non-empty list of dicts.
    2. At least 80% of items in spoken_sentences have valid duration_frames > 0 or duration_sec > 0.
    3. At least one directory in dirs contains valid tts_out.mp3 (> 10KB).
    4. At least one directory in dirs contains whisper_segments.json or subtitles.srt (> 100 bytes).
    """
    if not spoken_sentences or not isinstance(spoken_sentences, list):
        return False
    
    valid_durations = 0
    for s in spoken_sentences:
        if not isinstance(s, dict):
            continue
        if (s.get("duration_frames") and int(s.get("duration_frames") or 0) > 0) or \
           (s.get("duration_sec") and float(s.get("duration_sec") or 0.0) > 0.0) or \
           (s.get("end_ms", 0) > s.get("start_ms", 0)):
            valid_durations += 1
            
    if valid_durations == 0 or (valid_durations / len(spoken_sentences)) < 0.8:
        return False

    has_audio = False
    has_subtitles = False
    for d in dirs:
        if not d or not d.exists():
            continue
        audio_file = d / "tts_out.mp3"
        if audio_file.exists() and audio_file.stat().st_size > 10240:
            has_audio = True
        sub_file = d / "whisper_segments.json"
        srt_file = d / "subtitles.srt"
        if (sub_file.exists() and sub_file.stat().st_size > 100) or (srt_file.exists() and srt_file.stat().st_size > 100):
            has_subtitles = True

    return has_audio and has_subtitles


def generate_director_plan(
    episode_id: str,
    story_text: str = None,
    spoken_sentences: list = None,
    intel_card: dict = None,
    metadata: dict = None,
    skip_notion: bool = False,
    run_downstream: bool = True
) -> dict:
    """
    Core B3 Art Director & Universal Scene Breakdown Engine (Hollywood Audio-Anchored - Rule 128).
    Breaks down 5-Beat story into 45-65 dynamic cinematic shots anchored 1:1 to master audio timecodes.
    Preserves existing metadata in brain_input.json without destructive overwrite.
    Produces director_plan.json, dp_plan.json, and brain_input.json (non-destructive deep-merge).
    """
    logger.info(f"🎬 [B3 Director] Starting Art Direction for Episode: {episode_id}")

    # 1. Resolve inputs
    ep_dir = ROOT_DIR / "episodes" / episode_id
    ws_dir = ROOT_DIR / "workspace" / episode_id
    var_vf_dir = Path(f"/var/vf/episodes/{episode_id}")
    ep_dir.mkdir(parents=True, exist_ok=True)
    ws_dir.mkdir(parents=True, exist_ok=True)
    if var_vf_dir.parent.exists() or Path("/var/vf").exists():
        var_vf_dir.mkdir(parents=True, exist_ok=True)

    if not spoken_sentences:
        spoken_candidates = [
            var_vf_dir / "spoken_sentences.json",
            ep_dir / "spoken_sentences.json",
            ws_dir / "spoken_sentences.json"
        ]
        for sc in spoken_candidates:
            if sc.exists():
                try:
                    spoken_sentences = json.loads(sc.read_text(encoding="utf-8"))
                    if spoken_sentences:
                        break
                except Exception:
                    pass
    if not spoken_sentences:
        for bc in [var_vf_dir / "brain_input.json", ep_dir / "brain_input.json"]:
            if bc.exists():
                try:
                    b_data = json.loads(bc.read_text(encoding="utf-8"))
                    spoken_sentences = b_data.get("spoken_sentences", [])
                    if spoken_sentences:
                        break
                except Exception:
                    pass

    if not story_text:
        story_candidates = [
            var_vf_dir / "story.txt",
            ep_dir / "story.txt",
            ws_dir / "story.txt"
        ]
        for sc in story_candidates:
            if sc.exists():
                story_text = sc.read_text(encoding="utf-8")
                break

    if not story_text:
        raise FileNotFoundError(f"Cannot find story.txt for episode {episode_id}")

    if not intel_card:
        intel_candidates = [
            var_vf_dir / "competitor_intel_card.json",
            ep_dir / "competitor_intel_card.json",
            ws_dir / "competitor_intel_card.json"
        ]
        for ic in intel_candidates:
            if ic.exists():
                try:
                    intel_card = json.loads(ic.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass
        if not intel_card:
            intel_card = {}

    grounding_data = {}
    g_candidates = [
        var_vf_dir / "grounding_intel.json",
        ep_dir / "grounding_intel.json",
        ws_dir / "grounding_intel.json"
    ]
    for gc in g_candidates:
        if gc.exists():
            try:
                grounding_data = json.loads(gc.read_text(encoding="utf-8"))
                break
            except Exception:
                pass
    temporal_cadence = (grounding_data.get("temporal_cadence") or "ADAPTIVE").upper()
    causal_epochs = grounding_data.get("causal_epochs") or []

    if not metadata:
        metadata = {}

    niche = metadata.get("niche") or intel_card.get("niche", "Investigative Documentary")
    topic = metadata.get("topic") or intel_card.get("target_keyword", episode_id)

    # Hollywood Movie Standard: Ensure Audio Spine exists and is timecode-locked before Director Breakdown (Rule 120/127)
    audio_dirs = [ep_dir, var_vf_dir, ws_dir]
    if not _is_valid_audio_spine(spoken_sentences, audio_dirs):
        logger.info(f"  [B3 Hollywood] Audio Spine missing or invalid for {episode_id}. Auto-synthesizing Hollywood Audio Spine from story...")
        try:
            from app.services.story_engine_b2 import adapt_master_spoken_script, adversarial_audit_spoken_script
            from app.services.beat_tts_engine import synthesize_beat_tts_pipeline
            import asyncio
            
            mkt = (metadata.get("market") or episode_id.split("_")[0]).upper()
            topic_val = topic or episode_id
            
            if not spoken_sentences:
                spoken_data = adapt_master_spoken_script(story_text, market=mkt, topic=topic_val)
                spoken_audit = adversarial_audit_spoken_script(spoken_data, market=mkt, topic=topic_val)
                raw_sents = spoken_data.get("sentences", [])
                spoken_script_txt = spoken_data.get("spoken_script_text", story_text)
            else:
                raw_sents = spoken_sentences
                spoken_script_txt = story_text
                spoken_audit = {}
            
            target_dir = ep_dir if ep_dir.exists() else var_vf_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            
            (target_dir / "spoken_script.txt").write_text(spoken_script_txt, encoding="utf-8")
            (target_dir / "spoken_sentences.json").write_text(json.dumps(raw_sents, ensure_ascii=False, indent=2), encoding="utf-8")
            
            bp = target_dir / "brain_input.json"
            b_in = {}
            if bp.exists():
                try:
                    b_in = json.loads(bp.read_text(encoding="utf-8"))
                except Exception:
                    pass
            b_in["episode_id"] = episode_id
            b_in["market"] = mkt
            b_in["story"] = story_text
            b_in["spoken_script"] = spoken_script_txt
            b_in["spoken_sentences"] = raw_sents
            if spoken_audit:
                b_in["spoken_script_audit"] = spoken_audit
            bp.write_text(json.dumps(b_in, ensure_ascii=False, indent=2), encoding="utf-8")
            
            if var_vf_dir.exists() and var_vf_dir != target_dir:
                try:
                    (var_vf_dir / "spoken_script.txt").write_text(spoken_script_txt, encoding="utf-8")
                    (var_vf_dir / "spoken_sentences.json").write_text(json.dumps(raw_sents, ensure_ascii=False, indent=2), encoding="utf-8")
                    (var_vf_dir / "brain_input.json").write_text(json.dumps(b_in, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
            
            tts_res = asyncio.run(synthesize_beat_tts_pipeline(episode_id, out_dir=str(target_dir), force=True))
            spoken_sentences = tts_res.get("segments") or []
            logger.info(f"  [B3 Hollywood] Audio Spine synthesized: {len(spoken_sentences)} sentences timecode-locked.")
        except Exception as e:
            logger.error(f"  [B3 Hollywood] Auto Audio Spine synthesis failed: {e}")
            raise RuntimeError(f"HARD GATE VIOLATION (Rule 120/127): Failed to construct valid Audio Spine for {episode_id}: {e}. Zero fallback allowed.") from e

        if not _is_valid_audio_spine(spoken_sentences, audio_dirs):
            raise RuntimeError(f"HARD GATE VIOLATION (Rule 120/127): Audio Spine for {episode_id} is still invalid after synthesis. Zero fallback allowed.")

    # Rule 128: Universal Dynamic Context & Character Ensemble Extraction
    dynamic_context = extract_universal_semantic_context(story_text, metadata, intel_card)
    character_ensemble = extract_dynamic_character_ensemble(story_text, dynamic_context, topic)
    archetype = detect_cinematic_archetype(niche, topic, story_text)

    story_beats = extract_story_beats(story_text)
    is_cjk = any("\u4e00" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff" or "\uac00" <= char <= "\ud7af" for char in story_text[:500])
    total_words = int(len(story_text) / 2.5) if is_cjk else len(story_text.split())
    logger.info(f"  [B3] Story length: {total_words} words ({len(story_text)} chars) across {len(story_beats)} beats. Archetype: {archetype['director']}")
    logger.info(f"  [B3] Extracted Era: {dynamic_context['era_anchor']}. Ensemble: {len(character_ensemble)} roles.")

    m_up = (metadata.get("market") or episode_id.split("_")[0]).upper()
    if m_up in ["JP", "JA"]:
        market_lang_name = "Japanese (日本語)"
    elif m_up in ["KR", "KO"]:
        market_lang_name = "Korean (한국어)"
    elif m_up in ["VN", "VI"]:
        market_lang_name = "Vietnamese (Tiếng Việt)"
    else:
        market_lang_name = "English"

    # 2. Beat-by-Beat Hollywood Art Director Generation (Dynamic Chunking)
    # Allows full 40k input context across chunks while keeping each chunk output <= 2,800 tokens,
    # completely eliminating physical output token truncation (finish_reason: length).
    targeted_art_rules = get_b3_strategic_rules()

    cam_moves = CANONICAL_CAMERA_MOVES
    d_lower = archetype.get("director", "").lower()
    if "fincher" in d_lower or "mckay" in d_lower or "noir" in d_lower:
        cam_moves = ["snap_zoom", "slow_push_in", "cinematic_pan", "macro_tilt", "handheld_shake", "slow_pull_out"]
    elif "nolan" in d_lower or "chernobyl" in d_lower:
        cam_moves = ["slow_pull_out", "cinematic_pan", "slow_push_in", "handheld_shake", "macro_tilt", "snap_zoom"]
    elif "soderbergh" in d_lower or "clinical" in d_lower:
        cam_moves = ["macro_tilt", "slow_push_in", "cinematic_pan", "snap_zoom", "slow_pull_out", "handheld_shake"]
    elif "miller" in d_lower or "contract" in d_lower or "moneyball" in d_lower:
        cam_moves = ["cinematic_pan", "slow_push_in", "snap_zoom", "macro_tilt", "handheld_shake", "slow_pull_out"]

    all_scenes = []
    sc_counter = 0

    for b_idx, beat in enumerate(story_beats):
        b_num = b_idx + 1
        b_name = CANONICAL_BEATS[b_idx] if b_idx < len(CANONICAL_BEATS) else f"Beat {b_num}"
        beat_content = beat.get("content", "").strip()
        beat_spoken = [s for s in spoken_sentences if int(s.get("beat_index") or 1) == b_num] if spoken_sentences else None
        logger.info(f"  [B3 Dynamic Chunk {b_num}/5] Directing {b_name} (start scene: sc{sc_counter:03d}, spoken sentences: {len(beat_spoken) if beat_spoken else 'N/A'})...")

        if beat_spoken:
            system_prompt = (
                f"{targeted_art_rules}\n\n"
                "You are an Elite Hollywood Art Director, Director of Photography (DP), and Master Visual Storyboard Editor.\n"
                f"You direct in the visual style of {archetype['director']}.\n"
                f"Visual Tone: {dynamic_context['physical_environment']}.\n"
                f"Era Anchor: {dynamic_context['era_anchor']}.\n"
                f"Color Palette: {dynamic_context['color_palette']}.\n"
                f"Lighting Grammar: {dynamic_context['lighting_mood']}.\n"
                f"Camera Grammar: {archetype.get('camera_style', 'Atmospheric slow push-ins and tracking shots')}.\n\n"
                "YOUR MISSION FOR THIS BEAT (HOLLYWOOD AUDIO-ANCHORED SHOT BREAKDOWN):\n"
                f"Direct cinematic visual shots for the {len(beat_spoken)} spoken voiceover sentences of {b_name}.\n"
                "For each spoken sentence, assign 1 cinematic scene (or up to 2 shots for high-stakes climax moments).\n\n"
                "CRITICAL ARCHITECTURAL MANDATES:\n"
                "1. 0% INVENTED SPOKEN TEXT: The 'narration' field MUST BE THE VERBATIM TEXT of the spoken sentence. DO NOT INVENT ANY NEW WORDS OR DIALOGUE!\n"
                "2. TIMECODE ALIGNMENT: The scene duration MUST match the sentence audio duration ('duration_frames' and 'duration_sec').\n"
                "3. TWO-LAYER RENDER SYSTEM (Rule 116 & Rule 122):\n"
                "   - Layer 1 Background (16:9 widescreen 2560x1440): 'bg_prompt' IN ENGLISH. Cinematic environment, safe-zone clear in bottom 20% for subtitles.\n"
                "   - Layer 2 Foreground (1:1 2048x2048): 'fg_prompt' IN ENGLISH. Stylized Graphic Novel Editorial Illustration on solid flat #FF00FF magenta chroma key.\n"
                "4. DYNAMIC CHARACTER ENSEMBLE (Rule 128):\n"
                f"   - Available character roles: {[c['role_name'] for c in character_ensemble]}.\n"
                "5. 6 CANONICAL CAMERA MOVEMENTS (DIRECTOR MOTION GRAMMAR):\n"
                "   - 'slow_push_in': Fincher clinical slow push-in, cubic Bezier ease-in-out, tight tension build.\n"
                "   - 'snap_zoom': Adam McKay investigative whip snap zoom, rapid reframing on sudden conflict.\n"
                "   - 'cinematic_pan': Analytical scanning lateral pan across spatial evidence.\n"
                "   - 'macro_tilt': Errol Morris forensic macro tilt, vertical inspection of documents/props.\n"
                "   - 'slow_pull_out': Scale reveal, pulling back to expose systemic entrapment.\n"
                "   - 'handheld_shake': Tense vérité micro-jitter, subjective documentary realism.\n"
                "6. FORENSIC GRAPHICS & STAT CARDS:\n"
                "   - 'forensic_overlay': 'evidence_3d_prop' (procedural 3D physical evidence / wax seal / imperial hanko / lockbox / exhibit item with 12fps stop-motion), 'document_highlight', 'tactical_map', 'kinetic_counter', 'evidence_board', 'causal_flowchart', or null.\n"
                "   - 'stat_card': Tag high-impact metric scenes with exact numbers from narration: {\"value\": \"<EXACT_METRIC_FROM_NARRATION>\", \"label\": \"PRICE ANCHOR\" / \"VALUATION COLLAPSE\"} or null.\n"
                "   - 'stamp_badge': Climax evidentiary stamp slam: 'PRICE_FRAUD', 'VIOLATION', 'CONFIDENTIAL', 'EVIDENCE', 'VOID', or null.\n"
                "   - 'motion_directive': Parallax 2.5D visual motion: 'dramatic_push', 'subtle_drift', 'split_whip', or 'forensic_lock'.\n"
                "7. VOX EDITORIAL STORYBOARD (OBJECT-FOCUS & ANIMATION CUES - RULE 122 & RULE 128):\n"
                "   - 'object_focus': Defines central evidentiary document/network: {\"type\": \"court_docket\" | \"redacted_memo\" | \"financial_ledger\" | \"money_trail_network\" | \"corporate_org_chart\" | \"archival_photo\" | \"persona_portrait\" | \"none\", \"title\": \"<DOC_TITLE>\", \"agency\": \"<AGENCY>\", \"source_ref\": \"<CASE_NO>\", \"key_snippet\": \"<HIGHLIGHT_SNIPPET>\", \"stat_metric\": \"<METRIC_OR_NULL>\"}\n"
                "   - 'layout_zone': Directs spatial placement: {\"placement\": \"center_hero_document\" | \"split_evidence_left\" | \"split_evidence_right\" | \"macro_detail_focus\" | \"lower_third_ticker\", \"safe_zone\": \"bottom_left\", \"camera_pan_axis\": \"horizontal\" | \"vertical\" | \"push_punch\"}\n"
                "   - 'animation_cue': Synchronizes procedural animation with speech: {\"effect\": \"yellow_marker_highlight\" | \"red_stamp_slam\" | \"counter_rollup\" | \"flowchart_arrow_grow\", \"trigger_word\": \"<WORD_FROM_NARRATION>\", \"duration_frames\": 24}\n"
                "   - 'frame_transition': Directs editorial cut & SFX: {\"type\": \"match_cut\" | \"whip_pan_left\" | \"whip_pan_right\" | \"macro_zoom_through\" | \"film_dissolve\" | \"hard_cut\", \"sfx_cue\": \"paper_rustle\" | \"stamp_thud\" | \"camera_whoosh\"}\n"
                "   - 'foreground': Sparsely used (<= 10-12 scenes per episode). When explaining mechanisms/contracts/filings, foreground MUST BE NULL.\n\n"
                "OUTPUT FORMAT: Return ONLY a valid JSON object matching: {\"scenes\": [ ... ]}. No markdown fences."
            )

            beat_payload = {
                "episode_id": episode_id,
                "market": m_up,
                "narration_language": market_lang_name,
                "beat_index": b_num,
                "beat_name": b_name,
                "start_scene_index": sc_counter,
                "target_scene_count": f"{len(beat_spoken)} shots matching spoken sentences",
                "dynamic_context": dynamic_context,
                "character_ensemble": character_ensemble,
                "spoken_sentences": _sanitize_beat_spoken_for_llm(beat_spoken)
            }

            prompt_instruction = (
                f"Direct cinematic shots for the {len(beat_spoken)} spoken sentences of Beat {b_num} ({b_name}) starting from scene_id 'sc{sc_counter:03d}'.\n"
                "Each scene's narration MUST match the spoken sentence text verbatim (0% invented text).\n"
                "Return a JSON object: {\"scenes\": [...]}\n\n"
                "Input Data:\n" + json.dumps(beat_payload, ensure_ascii=False)
            )
            min_candidate_count = max(3, int(len(beat_spoken) * 0.7))
        else:
            system_prompt = (
                f"{targeted_art_rules}\n\n"
                "You are an Elite Hollywood Art Director, Director of Photography (DP), and Master Visual Storyboard Editor.\n"
                f"You direct in the visual style of {archetype['director']}.\n"
                f"Visual Tone: {dynamic_context['physical_environment']}.\n"
                f"Era Anchor: {dynamic_context['era_anchor']}.\n"
                f"Color Palette: {dynamic_context['color_palette']}.\n"
                f"Lighting Grammar: {dynamic_context['lighting_mood']}.\n"
                f"Camera Grammar: {archetype.get('camera_style', 'Atmospheric slow push-ins and tracking shots')}.\n\n"
                "YOUR MISSION FOR THIS BEAT:\n"
                f"Break down this narrative Beat ({b_name}) into 26 to 32 sequential cinematic scenes (~6-7s duration each).\n"
                + ("Act I MUST open with a 12 to 15 scene Fincher-style rapid-fire hook (Scenes sc000-sc014, 15-25 words each, ~3.5s - 5.0s per scene) structured in 3 phases: (1) Asymmetric Paradox (0-15s), (2) Hard Metric Shock (15-35s), and (3) The Investigative Contract (35-60s).\n" if b_num == 1 else "Sustain a tight sentence-atomic pacing of 25-35 words per scene (~6.0s - 7.5s duration).\n")
                + "\nCRITICAL ARCHITECTURAL MANDATES:\n"
                "1. TWO-LAYER RENDER SYSTEM (Rule 116):\n"
                "   - Layer 1 Background (16:9 widescreen 2560x1440): Cinematic environment. Safe-zone clear in bottom 20% for subtitles, center-right negative space for foreground overlay.\n"
                "   - Layer 2 Foreground (1:1 2048x2048): Stylized Editorial Graphic Novel Digital Illustration isolated on pure solid flat #FF00FF magenta chroma key. Full-body head-to-toe. NO photorealistic humans.\n"
                "2. DYNAMIC CHARACTER ENSEMBLE (Rule 128):\n"
                f"   - Available character roles: {[c['role_name'] for c in character_ensemble]}.\n"
                "3. DUAL-LANGUAGE PROTOCOL (Rule 446 & Rule 120):\n"
                "   - VISUAL PROMPTS (bg_prompt, fg_prompt, visual_metaphor): MUST BE IN ENGLISH.\n"
                f"   - SPOKEN NARRATION ('narration'): MUST BE 100% VERBATIM IN {market_lang_name}! NEVER translate narration to English!\n"
                "4. 6 CANONICAL CAMERA MOVEMENTS (DIRECTOR MOTION GRAMMAR):\n"
                "   - 'slow_push_in': Fincher clinical slow push-in, cubic Bezier ease-in-out, tight tension build.\n"
                "   - 'snap_zoom': Adam McKay investigative whip snap zoom, rapid reframing on sudden conflict.\n"
                "   - 'cinematic_pan': Analytical scanning lateral pan across spatial evidence.\n"
                "   - 'macro_tilt': Errol Morris forensic macro tilt, vertical inspection of documents/props.\n"
                "   - 'slow_pull_out': Scale reveal, pulling back to expose systemic entrapment.\n"
                "   - 'handheld_shake': Tense vérité micro-jitter, subjective documentary realism.\n"
                "5. LOCATION CONTINUITY: assign 'bg_cluster_id' (range {((b_num - 1) * 4) + 1}..{b_num * 4}).\n"
                "6. FORENSIC OVERLAYS: Tag evidentiary scenes with 'forensic_overlay': 'evidence_3d_prop' (procedural 3D physical evidence / wax seal / imperial hanko / lockbox / exhibit item with 12fps stop-motion), 'document_highlight', 'tactical_map', 'kinetic_counter', 'evidence_board', 'causal_flowchart', or null.\n"
                "7. MOTION GRAPHICS & STAT CARDS (Rule 122 Remotion Suite):\n"
                "   - 'stat_card': Tag high-impact metric scenes with exact numbers from narration: {\"value\": \"<EXACT_METRIC_FROM_NARRATION>\", \"label\": \"PRICE ANCHOR\" / \"VALUATION COLLAPSE\"} or null.\n"
                "   - 'stamp_badge': Climax evidentiary stamp slam: 'PRICE_FRAUD', 'VIOLATION', 'CONFIDENTIAL', 'EVIDENCE', 'VOID', or null.\n"
                "   - 'motion_directive': Parallax 2.5D visual motion: 'dramatic_push', 'subtle_drift', 'split_whip', or 'forensic_lock'.\n"
                "8. VOX EDITORIAL STORYBOARD (OBJECT-FOCUS & ANIMATION CUES - RULE 122 & RULE 128):\n"
                "   - 'object_focus': Defines central evidentiary document/network: {\"type\": \"court_docket\" | \"redacted_memo\" | \"financial_ledger\" | \"money_trail_network\" | \"corporate_org_chart\" | \"archival_photo\" | \"persona_portrait\" | \"none\", \"title\": \"<DOC_TITLE>\", \"agency\": \"<AGENCY>\", \"source_ref\": \"<CASE_NO>\", \"key_snippet\": \"<HIGHLIGHT_SNIPPET>\", \"stat_metric\": \"<METRIC_OR_NULL>\"}\n"
                "   - 'layout_zone': Directs spatial placement: {\"placement\": \"center_hero_document\" | \"split_evidence_left\" | \"split_evidence_right\" | \"macro_detail_focus\" | \"lower_third_ticker\", \"safe_zone\": \"bottom_left\", \"camera_pan_axis\": \"horizontal\" | \"vertical\" | \"push_punch\"}\n"
                "   - 'animation_cue': Synchronizes procedural animation with speech: {\"effect\": \"yellow_marker_highlight\" | \"red_stamp_slam\" | \"counter_rollup\" | \"flowchart_arrow_grow\", \"trigger_word\": \"<WORD_FROM_NARRATION>\", \"duration_frames\": 24}\n"
                "   - 'frame_transition': Directs editorial cut & SFX: {\"type\": \"match_cut\" | \"whip_pan_left\" | \"whip_pan_right\" | \"macro_zoom_through\" | \"film_dissolve\" | \"hard_cut\", \"sfx_cue\": \"paper_rustle\" | \"stamp_thud\" | \"camera_whoosh\"}\n"
                "   - 'foreground': Sparsely used (<= 10-12 scenes per episode). When explaining mechanisms/contracts/filings, foreground MUST BE NULL.\n\n"
                "OUTPUT FORMAT: Return ONLY a valid JSON object matching: {\"scenes\": [ ... ]}. No markdown fences."
            )

            beat_payload = {
                "episode_id": episode_id,
                "market": m_up,
                "narration_language": market_lang_name,
                "beat_index": b_num,
                "beat_name": b_name,
                "start_scene_index": sc_counter,
                "target_scene_count": "26 to 32 scenes",
                "dynamic_context": dynamic_context,
                "character_ensemble": character_ensemble,
                "beat_verbatim_storyline": beat_content
            }

            prompt_instruction = (
                f"Break down Beat {b_num} ({b_name}) into 26 to 32 sequential scenes starting from scene_id 'sc{sc_counter:03d}'.\n"
                "Return a JSON object: {\"scenes\": [...]}\n\n"
                "Input Data:\n" + json.dumps(beat_payload, ensure_ascii=False)
            )
            min_candidate_count = 15

        raw_res = ""
        gateway = get_global_gateway()
        for attempt in range(1, 3):
            try:
                logger.info(f"  [B3 Beat {b_num}] Calling Claude Opus 5 (Visual Director) attempt {attempt}/2 (fallback=gpt-6-astra)...")
                raw_res = gateway.call_llm(
                    prompt=prompt_instruction,
                    system_prompt=system_prompt,
                    model="claude-opus-5",
                    max_tokens=4500,
                    timeout=150.0,
                    fallback="gpt-6-astra"
                )
                if raw_res and raw_res.strip():
                    break
            except Exception as e:
                logger.warning(f"  [B3 Beat {b_num}] LLM attempt {attempt} failed: {e}")
                time.sleep(2)

        # Parse JSON
        parsed_beat = None
        if raw_res and raw_res.strip():
            cleaned = raw_res.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            try:
                parsed_beat = json.loads(cleaned.strip())
            except Exception:
                m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
                if m:
                    try:
                        parsed_beat = json.loads(m.group(1))
                    except Exception:
                        pass
                elif cleaned.strip().startswith("[") and cleaned.strip().endswith("]"):
                    try:
                        parsed_beat = {"scenes": json.loads(cleaned.strip())}
                    except Exception:
                        pass

        candidate_scenes = []
        if isinstance(parsed_beat, dict):
            candidate_scenes = parsed_beat.get("scenes") or []
        elif isinstance(parsed_beat, list):
            candidate_scenes = parsed_beat

        if len(candidate_scenes) >= min_candidate_count:
            logger.info(f"  [B3 Beat {b_num}] LLM generated {len(candidate_scenes)} scenes successfully.")
            for s_idx, s in enumerate(candidate_scenes):
                s["scene_id"] = f"sc{sc_counter:03d}"
                s["beat_index"] = b_num
                s["beat_name"] = b_name
                if beat_spoken and s_idx < len(beat_spoken):
                    sent = beat_spoken[s_idx]
                    s["sentence_id"] = sent.get("sentence_id")
                    s["duration_frames"] = sent.get("duration_frames") or s.get("duration_frames") or int(round(sent.get("duration_sec", 6.0) * 30))
                    s["duration_sec"] = sent.get("duration_sec") or s.get("duration_sec") or round(s["duration_frames"] / 30.0, 2)
                    s["duration_est_sec"] = s["duration_sec"]
                    s["narration"] = sent.get("text") or s.get("narration", "")

                if not s.get("bg_cluster_id"):
                    s["bg_cluster_id"] = ((b_num - 1) * 4) + (sc_counter % 3) + 1
                if not s.get("forensic_overlay"):
                    s["forensic_overlay"] = detect_forensic_overlay(s.get("narration", ""))
                if not s.get("stat_card"):
                    s["stat_card"] = detect_stat_card(s.get("narration", ""))
                if not s.get("stamp_badge"):
                    s["stamp_badge"] = detect_stamp_badge(s.get("narration", ""))
                if not s.get("motion_directive"):
                    s["motion_directive"] = "dramatic_push" if sc_counter < 15 else ("split_whip" if sc_counter % 3 == 0 else "subtle_drift")
                all_scenes.append(s)
                sc_counter += 1
        else:
            logger.warning(f"  [B3 Beat {b_num}] LLM generated insufficient scenes ({len(candidate_scenes)} < {min_candidate_count}). Activating deterministic synthesizer for Beat {b_num}...")
            synth_scenes, sc_counter = _synthesize_beat_scenes(
                b_idx=b_idx,
                beat=beat,
                episode_id=episode_id,
                archetype=archetype,
                dynamic_context=dynamic_context,
                character_ensemble=character_ensemble,
                cam_moves=cam_moves,
                start_sc_counter=sc_counter,
                beat_spoken_sents=beat_spoken
            )
            all_scenes.extend(synth_scenes)

    # 2. Rule 125 Single Truth: Delegate scene breakdown & tactile physics to unified_vox_director
    from app.services.unified_vox_director import (
        build_unified_director_plan,
        OBJECT_ROSTER,
        BACKGROUND_ROSTER,
        _sanitize_foreground_prompt,
        _sanitize_background_prompt
    )
    
    target_dir = ep_dir if ep_dir.exists() else var_vf_dir
    logger.info(f"  [B3 Bridge] Delegating Director Plan breakdown to Unified VOX Director (Rule 125 Single Truth)...")
    unified_res = build_unified_director_plan(spoken_sentences, target_dir)
    unified_scenes = unified_res.get("scenes", [])
    hero_clips = unified_res.get("hero_clips", [])

    normalized_scenes = []
    bg_roster = {
        k: {
            "key": k,
            "beat": "Evidence Setting",
            "description": v["description"],
            "safe_zone": "bottom 20% safe zone"
        }
        for k, v in BACKGROUND_ROSTER.items()
    }
    fg_roster = {
        k: {
            "key": k,
            "beat": "Evidence Exhibit",
            "role": v.get("role", "Key Evidence"),
            "description": v["description"],
            "position": "center"
        }
        for k, v in OBJECT_ROSTER.items()
    }

    for idx, sc in enumerate(unified_scenes):
        sc_id = sc.get("scene_id") or f"sc{idx:03d}"
        beat_idx = sc.get("beat_index", 1)
        beat_name = CANONICAL_BEATS[min(max(beat_idx - 1, 0), 4)]
        narration = sc.get("narration") or ""
        dur = sc.get("duration_seconds", 5.0)

        bg = sc.get("background") or {}
        fg = sc.get("foreground") or {}
        bg_key = bg.get("reuse_key") or ""
        bg_desc = bg.get("description") or ""
        fg_key = fg.get("reuse_key") or ""
        fg_desc = fg.get("description") or ""

        cam = sc.get("camera")
        cam_mov = cam if isinstance(cam, str) else (cam.get("movement", "static") if isinstance(cam, dict) else "static")
        if cam_mov not in CANONICAL_CAMERA_MOVES:
            cam_mov = CANONICAL_CAMERA_MOVES[idx % len(CANONICAL_CAMERA_MOVES)]

        bg_cluster_id = sc.get("bg_cluster_id") or sc.get("bgClusterId") or ((beat_idx - 1) * 4 + (idx % 3) + 1)
        forensic_overlay = sc.get("forensic_overlay") or sc.get("forensicOverlay")
        if not forensic_overlay or isinstance(forensic_overlay, str):
            auto_overlay = detect_forensic_overlay(narration)
            if auto_overlay:
                forensic_overlay = auto_overlay

        stat_card = sc.get("stat_card") or sc.get("statCard")
        if not stat_card:
            stat_card = detect_stat_card(narration)

        stamp_badge = sc.get("stamp_badge") or sc.get("stampBadge")
        if not stamp_badge:
            stamp_badge = detect_stamp_badge(narration)

        motion_directive = sc.get("motion_directive") or sc.get("motionDirective")
        if not motion_directive:
            motion_directive = "dramatic_push" if idx < 15 else ("split_whip" if idx % 3 == 0 else "subtle_drift")

        # Dynamic Hollywood tension curve based on beat index and scene flow
        dynamic_tension = cam.get("tension_level") if isinstance(cam, dict) else None
        if not dynamic_tension or dynamic_tension == "high":
            if beat_idx == 1:
                dynamic_tension = "high" if idx in (0, 7, 8, 9) else "medium"
            elif beat_idx == 2:
                dynamic_tension = "high" if idx % 3 == 0 else "medium"
            elif beat_idx == 3:
                dynamic_tension = "high" if idx % 2 == 0 else "medium"
            elif beat_idx == 4:
                dynamic_tension = "climax" if idx % 2 == 0 else "high"
            else:  # Beat 5
                dynamic_tension = "climax" if idx == 0 else ("medium" if idx % 2 == 0 else "low")

        # VOX Editorial Storyboard Fields (Rule 122 & Rule 128)
        object_focus = sc.get("object_focus")
        if not object_focus or not isinstance(object_focus, dict):
            object_focus = detect_object_focus(narration, topic)

        layout_zone = sc.get("layout_zone")
        if not layout_zone or not isinstance(layout_zone, dict):
            fg_pos = fg.get("position", "right") if fg else "right"
            layout_zone = detect_layout_zone(has_fg=bool(fg_key), fg_position=fg_pos, scene_idx=idx)

        animation_cue = sc.get("animation_cue")
        if not animation_cue or not isinstance(animation_cue, dict):
            animation_cue = detect_animation_cue(narration, object_focus)

        frame_transition = sc.get("frame_transition")
        if not frame_transition or not isinstance(frame_transition, dict):
            frame_transition = detect_frame_transition(cam_mov, dynamic_tension or "medium", scene_idx=idx)

        norm_sc = {
            "scene_index": idx,
            "scene_id": sc_id,
            "beat_index": beat_idx,
            "beat": beat_name,
            "narration": narration,
            "narration_segment": narration,
            "duration_est": round(float(dur), 3),
            "duration_sec": max(1, int(round(dur))),
            "duration_frames": int(sc.get("duration_frames") or round(dur * 30)),
            "visual_metaphor": sc.get("visual_metaphor", "Systemic tension and institutional conflict"),
            "bg_cluster_id": int(bg_cluster_id),
            "forensic_overlay": forensic_overlay,
            "stat_card": stat_card,
            "stamp_badge": stamp_badge,
            "motion_directive": motion_directive,
            "object_focus": object_focus,
            "layout_zone": layout_zone,
            "animation_cue": animation_cue,
            "frame_transition": frame_transition,
            "camera": {
                "movement": cam_mov,
                "tension_level": dynamic_tension
            },
            "bg_reuse_key": bg_key,
            "bg_prompt": bg_desc,
            "background_reuse_key": bg_key,
            "image_prompt": bg_desc,
            "fg_reuse_key": fg_key or "",
            "fg_prompt": fg_roster.get(fg_key, {}).get("description", "") if fg_key else "",
            "foreground_reuse_key": fg_key or "",
            "foreground_prompt": fg_roster.get(fg_key, {}).get("description", "") if fg_key else "",
            "foreground_position": fg.get("position", "right") if fg else "right",
            "safe_zone": "bottom",
            "cinematic_tokens": validate_cinematic_tokens(sc.get("cinematic_tokens") or sc.get("cinematicTokens"), narration),
            "audio_sfx_cue": sc.get("audio_sfx_cue", "distant_room_tone")
        }
        normalized_scenes.append(norm_sc)

    # VOX Hard Cap on Foreground characters (Rule 122 & Rule 128):
    # Strictly <= 10-12 scenes per episode with foreground characters.
    # Focus on documents, metrics, and systemic mechanisms; prevent CPU render bottlenecks.
    fg_indices = [i for i, sc in enumerate(normalized_scenes) if sc.get("fg_reuse_key") or sc.get("foreground_reuse_key")]
    if len(fg_indices) > 12:
        logger.info(f"  [B3 VOX Gate] Pruning foreground characters from {len(fg_indices)} to <= 12 to enforce VOX object-focus minimalism...")
        step = max(1, len(fg_indices) // 12)
        kept_set = set(fg_indices[::step][:12])
        for i, sc in enumerate(normalized_scenes):
            if (sc.get("fg_reuse_key") or sc.get("foreground_reuse_key")) and i not in kept_set:
                sc["fg_reuse_key"] = ""
                sc["fg_prompt"] = ""
                sc["foreground_reuse_key"] = ""
                sc["foreground_prompt"] = ""
                if sc.get("layout_zone"):
                    sc["layout_zone"]["placement"] = "center_hero_document"
                    sc["layout_zone"]["camera_pan_axis"] = "push_punch"

    # 6. Assemble complete output payloads
    director_plan = {
        "episode_id": episode_id,
        "niche": niche,
        "topic": topic,
        "director_archetype": archetype["director"],
        "visual_tone": dynamic_context["physical_environment"],
        "color_palette": dynamic_context["color_palette"],
        "camera_style": archetype.get("camera_style", "Cinematic documentary tracking"),
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "total_scenes": len(normalized_scenes),
        "background_roster": bg_roster,
        "foreground_roster": fg_roster,
        "scenes": normalized_scenes
    }

    dp_plan = {
        "episode_id": episode_id,
        "scenes": [
            {
                "scene_id": s["scene_id"],
                "scene_index": s["scene_index"],
                "camera_movement": s["camera"]["movement"],
                "tension_level": s["camera"]["tension_level"],
                "bg_key": s["bg_reuse_key"],
                "fg_key": s["fg_reuse_key"],
                "duration_est": s["duration_est"],
                "audio_sfx": s["audio_sfx_cue"]
            }
            for s in normalized_scenes
        ]
    }

    # Non-destructive deep-merge for brain_input.json preserving all B2 metadata
    existing_brain = {}
    candidate_files = [var_vf_dir / "brain_input.json", ep_dir / "brain_input.json", ws_dir / "brain_input.json"]
    for cf in candidate_files:
        if cf.exists():
            try:
                with open(cf, "r", encoding="utf-8") as bf:
                    existing_brain = json.load(bf)
                break
            except Exception:
                pass

    brain_update = {
        "episode_id": episode_id,
        "content_type": "investigative_docudrama",
        "story": story_text,
        "director_archetype": archetype["director"],
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "scenes": normalized_scenes,
        "render_architecture": "remotion_twolayer_karaoke_v4"
    }

    brain_input = _deep_merge(existing_brain, brain_update)
    # Explicitly enforce preservation of all B2 metadata
    b2_metadata_keys = [
        "story_gate_score",
        "story_verdict",
        "market",
        "topic",
        "hook_3s",
        "breakout_queries",
        "niche",
        "search_specific_keyword"
    ]
    for k in b2_metadata_keys:
        if k in existing_brain:
            brain_input[k] = existing_brain[k]

    # 7. Persist to canonical directories
    canonical_dirs = [ws_dir, ep_dir]
    if var_vf_dir.exists() and var_vf_dir not in canonical_dirs:
        canonical_dirs.append(var_vf_dir)

    for target_dir in canonical_dirs:
        with open(target_dir / "director_plan.json", "w", encoding="utf-8") as f:
            json.dump(director_plan, f, indent=2, ensure_ascii=False)
        with open(target_dir / "dp_plan.json", "w", encoding="utf-8") as f:
            json.dump(dp_plan, f, indent=2, ensure_ascii=False)
        with open(target_dir / "brain_input.json", "w", encoding="utf-8") as f:
            json.dump(brain_input, f, indent=2, ensure_ascii=False)

    logger.info(f"  [B3] Saved director_plan.json & dp_plan.json to {canonical_dirs}")

    # 8. Trigger B3.5 Prompt Forge & B3.6 Visual Convergence (if run_downstream)
    if run_downstream:
        try:
            from app.services.prompt_forge import generate_scene_prompts, push_prompts_to_notion
            logger.info("  [B3.5] Forging visual prompts via Prompt Forge Engine...")
            bg_req = {k: {"visual_hint": v["description"], "narration_context": v["beat"]} for k, v in bg_roster.items()}
            fg_req = {k: {"visual_hint": v["description"], "narration_context": v["beat"]} for k, v in fg_roster.items()}

            prompts_res = generate_scene_prompts(
                bg_dict=bg_req,
                fg_dict=fg_req,
                story_title=topic,
                scenes=normalized_scenes,
                task_id=episode_id,
                market=m_up
            )

            # Map forged prompts back to each scene in director_plan
            for sc in director_plan.get("scenes", []):
                bg_k = sc.get("bg_reuse_key")
                if bg_k and bg_k in prompts_res.get("backgrounds", {}):
                    sc["bg_prompt"] = prompts_res["backgrounds"][bg_k]
                    sc["image_prompt"] = prompts_res["backgrounds"][bg_k]
                fg_k = sc.get("fg_reuse_key")
                if fg_k and fg_k in prompts_res.get("foregrounds", {}):
                    sc["fg_prompt"] = prompts_res["foregrounds"][fg_k]
                    sc["foreground_prompt"] = prompts_res["foregrounds"][fg_k]

            for target_dir in canonical_dirs:
                with open(target_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
                    json.dump(prompts_res, f, indent=2, ensure_ascii=False)
                with open(target_dir / "prompts.json", "w", encoding="utf-8") as f:
                    json.dump(prompts_res, f, indent=2, ensure_ascii=False)
                with open(target_dir / "director_plan.json", "w", encoding="utf-8") as f:
                    json.dump(director_plan, f, indent=2, ensure_ascii=False)
                with open(target_dir / "dp_plan.json", "w", encoding="utf-8") as f:
                    json.dump({"scenes": director_plan.get("scenes", [])}, f, indent=2, ensure_ascii=False)

            logger.info("  [B3.5] Initial Prompt Forge assets written to canonical directories.")
        except Exception as e:
            logger.warning(f"  [B3.5] Prompt Forge integration encountered notice: {e}")

        # 8.5. Step B3.5.1: Dual-LLM Adversarial Visual Convergence (Claude Opus 5 ⇄ GPT-6-Astra)
        try:
            from app.services.b36_visual_convergence import run_b36_visual_convergence
            logger.info("  [B3.5.1] Launching Dual-LLM Adversarial Visual Convergence (Claude Opus 5 ⇄ GPT-6-Astra)...")
            conv_res = run_b36_visual_convergence(
                episode_id=episode_id,
                director_plan=director_plan,
                dp_plan={"scenes": director_plan.get("scenes", [])},
                prompts_data=prompts_res if 'prompts_res' in locals() else None,
                story_text=story_text,
                grounding_intel=grounding_intel if 'grounding_intel' in locals() and grounding_intel else None,
                seo_package=intel_card.get("seo_package") if 'intel_card' in locals() and isinstance(intel_card, dict) else None
            )
            if conv_res and "director_plan" in conv_res:
                director_plan = conv_res["director_plan"]
            if conv_res and "prompts_data" in conv_res:
                prompts_res = conv_res["prompts_data"]
        except Exception as e:
            logger.warning(f"  [B3.5.1] Adversarial Visual Convergence encountered notice: {e}")

    # 9. Sync Director Plan to Notion
    if not skip_notion:
        try:
            push_director_plan_to_notion(director_plan, episode_id)
            if run_downstream and 'prompts_res' in locals() and prompts_res:
                push_prompts_to_notion(prompts_res, episode_id)
                logger.info("  [B3.5.1] Converged Prompts pushed to Notion Prompt Library DB.")
        except Exception as e:
            logger.warning(f"  [B3 Notion] Failed to push assets to Notion: {e}")

    return director_plan


def _synthesize_deterministic_director_plan(
    episode_id: str,
    story_beats: list[dict],
    archetype: dict,
    dynamic_context: dict = None,
    character_ensemble: list[dict] = None,
    spoken_sentences: list = None
) -> dict:
    """
    Robust fallback scene breakdown with dynamic character ensemble and authentic narrative context.
    Rule 128: Uses dynamic character ensemble extracted directly from narrative. Zero static role pools.
    """
    if not dynamic_context:
        dynamic_context = {
            "era_anchor": "Contemporary investigative documentary era",
            "physical_environment": archetype.get("visual_tone", "Authentic narrative environment"),
            "lighting_mood": "Low-key cinematic chiaroscuro with motivated shadows",
            "color_palette": archetype.get("palette", "Desaturated cinematic tones")
        }

    if not character_ensemble:
        character_ensemble = [
            {
                "role_name": "Lead Field Investigator",
                "archetype": "Meticulous & skeptical investigator tracing anomalies",
                "visual_cues": "holding evidence binder, examining physical document",
                "attire": "dark utilitarian field trench coat, durable wool trousers"
            },
            {
                "role_name": "Primary Field Eyewitness",
                "archetype": "Observant & vigilant local eyewitness holding key testimony",
                "visual_cues": "standing cautiously, observing surrounding setting",
                "attire": "authentic civilian workwear appropriate to setting"
            },
            {
                "role_name": "Administrative Oversight Official",
                "archetype": "Conflicted & guarded institutional authority facing scrutiny",
                "visual_cues": "presenting official compliance binder with stern expression",
                "attire": "formal municipal suit with administrative badge"
            },
            {
                "role_name": "Forensic Evidence Analyst",
                "archetype": "Clinical & objective scientific analyst uncovering empirical evidence",
                "visual_cues": "inspecting sample container with magnifying instrument",
                "attire": "protective field jacket and utility gloves"
            }
        ]

    cam_moves = CANONICAL_CAMERA_MOVES
    d_lower = archetype.get("director", "").lower()
    if "fincher" in d_lower or "mckay" in d_lower or "noir" in d_lower:
        cam_moves = ["snap_zoom", "slow_push_in", "cinematic_pan", "macro_tilt", "handheld_shake", "slow_pull_out"]
    elif "nolan" in d_lower or "chernobyl" in d_lower:
        cam_moves = ["slow_pull_out", "cinematic_pan", "slow_push_in", "handheld_shake", "macro_tilt", "snap_zoom"]
    elif "soderbergh" in d_lower or "clinical" in d_lower:
        cam_moves = ["macro_tilt", "slow_push_in", "cinematic_pan", "snap_zoom", "slow_pull_out", "handheld_shake"]
    elif "miller" in d_lower or "contract" in d_lower or "moneyball" in d_lower:
        cam_moves = ["cinematic_pan", "slow_push_in", "snap_zoom", "macro_tilt", "handheld_shake", "slow_pull_out"]

    scenes = []
    sc_counter = 0

    for b_idx, beat in enumerate(story_beats):
        b_num = b_idx + 1
        beat_spoken = [s for s in spoken_sentences if int(s.get("beat_index") or 1) == b_num] if spoken_sentences else None
        b_scenes, sc_counter = _synthesize_beat_scenes(
            b_idx=b_idx,
            beat=beat,
            episode_id=episode_id,
            archetype=archetype,
            dynamic_context=dynamic_context,
            character_ensemble=character_ensemble,
            cam_moves=cam_moves,
            start_sc_counter=sc_counter,
            beat_spoken_sents=beat_spoken
        )
        scenes.extend(b_scenes)

    return {
        "episode_id": episode_id,
        "director_archetype": archetype["director"],
        "visual_tone": dynamic_context["physical_environment"],
        "color_palette": dynamic_context["color_palette"],
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "scenes": scenes
    }


def _synthesize_beat_scenes(
    b_idx: int,
    beat: dict,
    episode_id: str,
    archetype: dict,
    dynamic_context: dict,
    character_ensemble: list[dict],
    cam_moves: list[str],
    start_sc_counter: int,
    beat_spoken_sents: list[dict] = None
) -> tuple[list[dict], int]:
    """
    Synthesize deterministic scenes for a single beat.
    If beat_spoken_sents is provided (Hollywood Audio-Anchored architecture):
    Synthesizes 1:1 scenes anchored to the spoken sentence timecodes with 0% invented dialogue.
    Otherwise, splits raw text into breath chunks.
    """
    b_num = b_idx + 1
    b_name = CANONICAL_BEATS[b_idx] if b_idx < len(CANONICAL_BEATS) else f"Beat {b_num}"

    # Hollywood Audio-Anchored path: 1:1 mapping from spoken sentences
    if beat_spoken_sents:
        beat_scenes = []
        sc_counter = start_sc_counter
        for sent in beat_spoken_sents:
            sc_text = sent.get("text", "").strip()
            if not sc_text:
                continue
            sc_id = f"sc{sc_counter:03d}"
            bg_cluster_id = ((b_num - 1) * 4) + (sc_counter % 3) + 1
            bg_k = f"{episode_id.lower()}_bg_b{b_num}_loc{sc_counter % 3}"

            char_idx = sc_counter % len(character_ensemble)
            char_obj = character_ensemble[char_idx]
            char_role = char_obj["role_name"]
            char_attire = char_obj["attire"]
            char_state = char_obj["archetype"]
            char_cues = char_obj.get("visual_cues", "standing head-to-toe")
            fg_k = f"{episode_id.lower()}_fg_b{b_num}_char{char_idx}" if sc_counter % 3 != 0 else None
            fg_pos = "right" if sc_counter % 2 == 0 else "left"

            bg_desc = f"Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, wide 16:9 cinematic setting of {b_name}, {dynamic_context['physical_environment']}, {dynamic_context['lighting_mood']}"
            fg_desc = f"Stylized editorial graphic novel digital illustration of full-body {char_role} in {char_attire}, standing head-to-toe, {char_cues}, posture {char_state}, 1:1 aspect ratio, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames" if fg_k else None
            cam_move = cam_moves[sc_counter % len(cam_moves)]

            dur_frames = sent.get("duration_frames") or int(round(sent.get("duration_sec", 6.0) * 30))
            dur_sec = sent.get("duration_sec") or round(dur_frames / 30.0, 2)

            forensic_overlay = detect_forensic_overlay(sc_text)
            stat_card = detect_stat_card(sc_text)
            stamp_badge = detect_stamp_badge(sc_text)
            motion_directive = "dramatic_push" if sc_counter < 10 else ("split_whip" if sc_counter % 3 == 0 else "subtle_drift")

            beat_scenes.append({
                "scene_id": sc_id,
                "sentence_id": sent.get("sentence_id"),
                "beat_index": b_num,
                "beat_name": b_name,
                "narration": sc_text,
                "duration_est_sec": dur_sec,
                "duration_sec": dur_sec,
                "duration_frames": dur_frames,
                "visual_metaphor": f"Visual metaphor representing {b_name}",
                "bg_cluster_id": bg_cluster_id,
                "forensic_overlay": forensic_overlay,
                "stat_card": stat_card,
                "stamp_badge": stamp_badge,
                "motion_directive": motion_directive,
                "camera": {
                    "movement": cam_move,
                    "target_focal": "medium_shot" if fg_k else "wide_shot",
                    "transition": "cut"
                },
                "camera_movement": cam_move,
                "bg_prompt": bg_desc,
                "image_prompt": bg_desc,
                "fg_prompt": fg_desc,
                "foreground_prompt": fg_desc,
                "background_reuse_key": bg_k,
                "foreground_reuse_key": fg_k,
                "fg_position": fg_pos if fg_k else None,
                "safe_zone": "bottom 20% clear for subtitles",
                "cinematic_tokens": validate_cinematic_tokens(None, sc_text)
            })
            sc_counter += 1
        return beat_scenes, sc_counter

    beat_raw = beat.get("content", "").strip()

    # Multi-lingual CJK detection (Chinese, Japanese, Korean)
    is_cjk = any("\u4e00" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff" or "\uac00" <= char <= "\ud7af" for char in beat_raw[:200])
    if is_cjk:
        # Korean uses Latin period/punctuation [.!?] along with CJK characters; Japanese/Chinese use [。！？]
        raw_sents = re.split(r"(?<=[.!?。！？\n])\s*", beat_raw)
        sentences = [s.strip() for s in raw_sents if len(s.strip()) > 8]
    else:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", beat_raw) if len(s.strip()) > 15]

    if not sentences:
        sentences = [f"Narrative progression for {b_name}."]

    beat_scenes = []
    sc_counter = start_sc_counter
    curr_narr = []
    curr_units = 0

    for sent in sentences:
        # Clean any lingering header tokens
        sent = re.sub(r'^(?:={2,}\s*)?(?:#+\s*)?(?:ACT|BEAT)\s*(?:[1-5]|IV|I{1,3}|V)[^\n]*?(?:={2,})?\s*', '', sent, flags=re.IGNORECASE).strip()
        if not sent:
            continue

        is_hook = (b_num == 1 and sc_counter < 15)
        if is_cjk:
            sent_units = len(sent)
            cut_threshold = 45 if is_hook else 70
            unit_divisor = 4.0 if is_hook else 5.5
        else:
            sent_units = len(sent.split())
            cut_threshold = 20 if is_hook else 30
            unit_divisor = 3.0 if is_hook else 2.5

        max_sentences = 1 if is_hook else 2
        # Sentence-Atomic Cut: flush when adding next sentence exceeds threshold or already has max_sentences
        if curr_narr and (curr_units + sent_units > cut_threshold or len(curr_narr) >= max_sentences):
            sc_text = "".join(curr_narr).strip() if is_cjk else " ".join(curr_narr).strip()
            if not re.search(r"[.!?。！？]$", sc_text):
                is_ja_zh = any("\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff" for c in sc_text)
                sc_text += ("。" if is_ja_zh else ".")
            sc_id = f"sc{sc_counter:03d}"
            bg_cluster_id = ((b_num - 1) * 4) + (sc_counter % 3) + 1
            bg_k = f"{episode_id.lower()}_bg_b{b_num}_loc{sc_counter % 3}"

            char_idx = sc_counter % len(character_ensemble)
            char_obj = character_ensemble[char_idx]
            char_role = char_obj["role_name"]
            char_attire = char_obj["attire"]
            char_state = char_obj["archetype"]
            char_cues = char_obj.get("visual_cues", "standing head-to-toe")
            fg_k = f"{episode_id.lower()}_fg_b{b_num}_char{char_idx}" if sc_counter % 4 != 0 else None
            fg_pos = "right" if sc_counter % 2 == 0 else "left"

            bg_desc = f"Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, wide 16:9 cinematic setting of {b_name}, {dynamic_context['physical_environment']}, {dynamic_context['lighting_mood']}"
            fg_desc = f"Stylized editorial graphic novel digital illustration of full-body {char_role} in {char_attire}, standing head-to-toe, {char_cues}, posture {char_state}, 1:1 aspect ratio, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames" if fg_k else None
            cam_move = cam_moves[sc_counter % len(cam_moves)]
            if is_hook:
                dur = max(3, min(5, round(curr_units / unit_divisor)))
            else:
                dur = max(5, min(9, round(curr_units / unit_divisor)))

            forensic_overlay = detect_forensic_overlay(sc_text)
            stat_card = detect_stat_card(sc_text)
            stamp_badge = detect_stamp_badge(sc_text)
            motion_directive = "dramatic_push" if is_hook else ("split_whip" if sc_counter % 3 == 0 else "subtle_drift")

            beat_scenes.append({
                "scene_id": sc_id,
                "beat_index": b_num,
                "beat_name": b_name,
                "narration": sc_text,
                "duration_est_sec": dur,
                "visual_metaphor": f"Visual metaphor representing {b_name}",
                "bg_cluster_id": bg_cluster_id,
                "forensic_overlay": forensic_overlay,
                "stat_card": stat_card,
                "stamp_badge": stamp_badge,
                "motion_directive": motion_directive,
                "camera": {
                    "movement": cam_move,
                    "tension_level": "high" if is_hook or sc_counter % 3 == 0 else "medium"
                },
                "background": {
                    "reuse_key": bg_k,
                    "visual_description": bg_desc,
                    "safe_zone": "bottom 20% clear for subtitles, center-right negative space for foreground"
                },
                "foreground": {
                    "reuse_key": fg_k,
                    "character_role": char_role,
                    "psychological_state": char_state,
                    "body_language": char_cues,
                    "position": fg_pos,
                    "visual_description": fg_desc
                } if fg_k else None,
                "cinematic_tokens": validate_cinematic_tokens(None, sc_text),
                "audio_sfx_cue": "tense_ambient_drone" if sc_counter % 2 == 0 else "paper_shuffling"
            })
            sc_counter += 1
            curr_narr = []
            curr_units = 0

        curr_narr.append(sent)
        curr_units += sent_units

    if curr_narr:
        sc_text = "".join(curr_narr).strip() if is_cjk else " ".join(curr_narr).strip()
        if not re.search(r"[.!?。！？]$", sc_text):
            is_ja_zh = any("\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff" for c in sc_text)
            sc_text += ("。" if is_ja_zh else ".")
        sc_id = f"sc{sc_counter:03d}"
        dur = max(5, min(9, round(curr_units / unit_divisor)))
        cam_move = cam_moves[sc_counter % len(cam_moves)]
        bg_cluster_id = ((b_num - 1) * 4) + (sc_counter % 3) + 1
        bg_k = f"{episode_id.lower()}_bg_b{b_num}_tail"
        bg_desc = f"Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, wide 16:9 setting of {b_name}, {dynamic_context['physical_environment']}"
        forensic_overlay = detect_forensic_overlay(sc_text)
        stat_card = detect_stat_card(sc_text)
        stamp_badge = detect_stamp_badge(sc_text)
        motion_directive = "subtle_drift"
        beat_scenes.append({
            "scene_id": sc_id,
            "beat_index": b_num,
            "beat_name": b_name,
            "narration": sc_text,
            "duration_est_sec": dur,
            "visual_metaphor": f"Closing tension of {b_name}",
            "bg_cluster_id": bg_cluster_id,
            "forensic_overlay": forensic_overlay,
            "stat_card": stat_card,
            "stamp_badge": stamp_badge,
            "motion_directive": motion_directive,
            "camera": {"movement": cam_move, "tension_level": "medium"},
            "background": {
                "reuse_key": bg_k,
                "visual_description": bg_desc,
                "safe_zone": "bottom 20% clear for subtitles"
            },
            "foreground": None,
            "audio_sfx_cue": "clock_ticking"
        })
        sc_counter += 1

    return beat_scenes, sc_counter


def push_director_plan_to_notion(director_plan: dict, episode_id: str):
    """
    Sync director plan scenes to Notion Director Plan DB (5b201989-2400-8295-be81-81c2c0e4e138).
    Uses 1 EP = 1 Subpage + Child Scene DB model, setting Status to 'Compiled' and syncing all scenes.
    """
    notion_token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
    if not notion_token:
        logger.warning("[B3 Notion] No NOTION_TOKEN found, skipping Notion sync.")
        return

    try:
        import scripts.ag_notion_bridge as bridge
        scenes = director_plan.get("scenes", [])
        logger.info(f"[B3 Notion] Resolving Director Plan subpage for {episode_id}...")
        resolved = bridge.resolve_episode_director_db(episode_id, task_id=episode_id, create_if_missing=True)
        if not isinstance(resolved, dict) or resolved.get("error"):
            logger.warning(f"[B3 Notion] Could not resolve Director Plan subpage for {episode_id}: {resolved}")
            return

        subpage_id = resolved.get("subpage_id")
        scenes_db_id = resolved.get("db_id")

        if subpage_id:
            bridge.update_page_properties(subpage_id, {"Status": {"status": {"name": "Compiled"}}})
            logger.info(f"[B3 Notion] Set Director Plan [{episode_id}] status to 'Compiled' (subpage={subpage_id})")

        if not scenes_db_id:
            logger.warning(f"[B3 Notion] No child Scenes DB found for {episode_id}")
            return

        # Query existing scenes to avoid duplicate rows
        existing_scenes = {}
        try:
            q_res = bridge.query_db(scenes_db_id)
            for r in q_res.get("results", []):
                props = r.get("properties", {})
                name_list = props.get("Name", {}).get("title", [])
                t_name = "".join(t.get("plain_text", "") for t in name_list).strip()
                if t_name:
                    existing_scenes[t_name] = r.get("id")
        except Exception as q_err:
            logger.warning(f"[B3 Notion] Notice querying existing scenes in {scenes_db_id}: {q_err}")

        logger.info(f"[B3 Notion] Syncing {len(scenes)} scenes to Child DB ({scenes_db_id}). Existing scenes in DB: {len(existing_scenes)}")

        synced_count = 0
        for idx, sc in enumerate(scenes):
            sc_idx = sc.get("scene_index", idx)
            scene_title = f"Scene {sc_idx:03d}"

            # Construct properties conforming strictly to child Scenes DB schema
            props = {
                "Name": {"title": [{"text": {"content": scene_title}}]},
                "Scene Index": {"number": sc_idx},
                "Arc Index": {"number": sc.get("beat_index", 1)},
                "Beat": {"rich_text": [{"text": {"content": str(sc.get("beat") or "")[:2000]}}]},
                "Narration Segment": {"rich_text": [{"text": {"content": str(sc.get("narration_segment") or sc.get("narration") or "")[:2000]}}]},
                "Duration Est (s)": {"number": float(sc.get("duration_est") or sc.get("duration_sec") or 0.0)},
                "Background Prompt": {"rich_text": [{"text": {"content": str(sc.get("bg_prompt") or sc.get("image_prompt") or "")[:2000]}}]},
                "BG Reuse Key": {"rich_text": [{"text": {"content": str(sc.get("bg_reuse_key") or sc.get("background_reuse_key") or "")[:2000]}}]},
                "BG Layout Note": {"rich_text": [{"text": {"content": str(sc.get("visual_metaphor") or "")[:2000]}}]},
                "Foreground Prompt": {"rich_text": [{"text": {"content": str(sc.get("fg_prompt") or sc.get("foreground_prompt") or "")[:2000]}}]},
                "FG Reuse Key": {"rich_text": [{"text": {"content": str(sc.get("fg_reuse_key") or sc.get("foreground_reuse_key") or "")[:2000]}}]},
                "Status": {"status": {"name": "Compiled"}},
                "Episode ID": {"rich_text": [{"text": {"content": episode_id}}]},
                "Task ID": {"rich_text": [{"text": {"content": episode_id}}]}
            }

            # Select mappings
            pos = str(sc.get("foreground_position") or "").lower()
            if "left" in pos:
                props["FG Position"] = {"select": {"name": "Left"}}
            elif "right" in pos:
                props["FG Position"] = {"select": {"name": "Right"}}
            elif "center" in pos:
                props["FG Position"] = {"select": {"name": "Center"}}

            sz = str(sc.get("safe_zone") or "").lower()
            if "top" in sz:
                props["Safe Zone"] = {"select": {"name": "Top third"}}
            elif "right" in sz:
                props["Safe Zone"] = {"select": {"name": "Right third"}}
            else:
                props["Safe Zone"] = {"select": {"name": "Lower third"}}

            fg_sub = str(sc.get("fg_subject_type") or "").upper()
            if "A" in fg_sub or "NAMED" in fg_sub:
                props["FG Subject Type"] = {"select": {"name": "A — Named character"}}
            elif "B" in fg_sub or "SYMBOLIC" in fg_sub:
                props["FG Subject Type"] = {"select": {"name": "B — Symbolic figure"}}

            if scene_title in existing_scenes:
                page_id = existing_scenes[scene_title]
                bridge.update_page_properties(page_id, props)
            else:
                res_create = bridge.create_page(parent_db_id=scenes_db_id, properties=props)
                if isinstance(res_create, dict) and res_create.get("id"):
                    existing_scenes[scene_title] = res_create["id"]

            synced_count += 1

        logger.info(f"[B3 Notion] ✅ Pushed {synced_count}/{len(scenes)} scenes into Child DB {scenes_db_id} for {episode_id}")
    except Exception as e:
        logger.warning(f"[B3 Notion] Notion sync encountered notice: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="B3 Hollywood Art Director & Universal Scene Breakdown Engine")
    parser.add_argument("episode_id", help="Episode ID (e.g. <MARKET>_EP<0000>_<topic_slug>)")
    parser.add_argument("--skip-notion", action="store_true", help="Skip syncing to Notion")
    args = parser.parse_args()

    plan = generate_director_plan(args.episode_id, skip_notion=args.skip_notion)
    print(f"✅ Successfully generated Director Plan for {args.episode_id}: {plan['total_scenes']} scenes.")


if __name__ == "__main__":
    main()
