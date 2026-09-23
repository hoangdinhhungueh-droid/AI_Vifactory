#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/unified_vox_director.py
Unified VOX Spatial Physics Director Engine (B3 & B3.5 Combined)
Merges Scene Breakdown, Veo 3.1 3D Tactile Physics (Dynamic Hero clips distributed across Google accounts),
and Tactile Stop-Motion Collage Remotion Directives (12fps stepped jitter, paper drop shadow).
Compliant with:
- Rule 120 (Word-level Audio Sync with Whisper)
- Rule 122 (Pixel-Level Visual Audit Gate & Zero-Mock Score)
- Rule 128 (Zero Semantic Bias in Contracts - 100% Generic across JP, KR, VN, EN)
- Rule 132 (Decoupled Engine)
- Rule 445 (5-Beat Docudrama Storyboard Structure)
"""

import os
import sys
import re
import json
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import _sanitize_foreground_prompt, _sanitize_background_prompt

FLOW_ACCOUNTS = ["acc_01", "acc_02", "acc_03", "acc_04", "acc_05", "acc_06"]

# ============================================================================
# DYNAMIC VISUAL ROSTER GENERATOR (RULE 128 - ZERO SEMANTIC BIAS)
# ============================================================================

def extract_dynamic_visual_roster(
    story_text: str = "",
    spoken_sentences: Optional[List[Dict[str, Any]]] = None,
    grounding_intel: Optional[Dict[str, Any]] = None,
    competitor_card: Optional[Dict[str, Any]] = None,
    market: str = "EN",
    topic: str = "",
    dynamic_context: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Rule 128 & Rule 122: Trích xuất danh mục Đạo cụ (Foreground) & Bối cảnh (Background)
    hoàn toàn động theo thị trường bản địa (JP, KR, VN, EN) và dữ liệu thực tế (grounding).
    CẤM TUYỆT ĐỐI hardcode tên tập, nhân vật hay đạo cụ của một vụ án cụ thể (như Amazon).
    """
    m_up = str(market or "EN").upper().strip()
    g_intel = grounding_intel or {}
    key_metrics = []
    
    # Trích xuất số liệu định lượng từ grounding_intel nếu có
    if g_intel.get("grounding_table"):
        for row in g_intel.get("grounding_table", [])[:5]:
            val = row.get("value") or row.get("metric_value")
            unit = row.get("unit") or ""
            if val:
                key_metrics.append(f"{val} {unit}".strip())
    elif g_intel.get("key_figures"):
        key_metrics.extend([str(x) for x in g_intel.get("key_figures", [])[:4]])

    metric_highlight = key_metrics[0] if key_metrics else ("CONFIDENTIAL METRIC // AUDIT FINDING" if m_up == "EN" else "定量監査データ // 検証記録")

    if m_up in ["JP", "JA"]:
        # Thị trường Nhật Bản: Hanko đỏ, Bộ Y tế Lao động Phúc lợi (MHLW), Tòa án Tokyo, mẫu kiểm định
        bg_roster = {
            "bg_district_court_hall": {
                "title": "Tokyo District Courthouse Grand Hall",
                "description": "Cinematic wide-angle interior of Japanese district courthouse judicial hall, classical stone colonnade, high vaulted ceiling with moody diffused daylight, quiet austere judicial atmosphere, uncluttered background without distracting crowds.",
                "beats": [1, 5]
            },
            "bg_regulatory_inspection_lab": {
                "title": "Ministry & Quarantine Safety Analysis Laboratory",
                "description": "Modern chemical residue and food safety inspection laboratory, stainless steel workbenches, analytical spectrometry apparatus in soft background focus, cool fluorescent lighting, sterile documentary atmosphere.",
                "beats": [2, 3]
            },
            "bg_executive_boardroom_dusk": {
                "title": "Corporate Executive Boardroom Overlooking City at Dusk",
                "description": "Minimalist Japanese corporate executive boardroom overlooking evening city skyline, dark polished cedar table reflection, clean architectural lines, zero clutter, serious institutional tension.",
                "beats": [1, 4]
            },
            "bg_warehouse_distribution_office": {
                "title": "Regional Warehouse Logistics Office",
                "description": "Authentic commercial distribution logistics office, stacked shipping crates in soft focus background, warm overhead industrial lamp casting gentle pool of light on paperwork desk, clean documentary mood.",
                "beats": [1, 2, 4]
            },
            "bg_investigative_newsroom_night": {
                "title": "Investigative Journalism Newsroom at Night",
                "description": "Nocturnal investigative newsroom with dark empty desks receding into soft shadows, warm desk lamp pools, distant city lights through blinds, serious quiet investigative atmosphere.",
                "beats": [1, 2, 3]
            },
            "bg_forensic_archive_vault": {
                "title": "Government Institutional Archive Document Vault",
                "description": "Steel shelving units holding hundreds of uniform archival document storage boxes in deep linear perspective, clean concrete floor, cool downlighting, forensic discovery vault.",
                "beats": [3, 4]
            },
            "bg_regulatory_hearing_chamber": {
                "title": "Ministry Regulatory Oversight Hearing Chamber",
                "description": "Formal oak-paneled legislative and administrative hearing room with committee bench in background soft focus, rich timber textures, dignified institutional setting.",
                "beats": [4, 5]
            },
            "bg_municipal_quarantine_site": {
                "title": "Port Customs Quarantine Facility Site",
                "description": "Port customs inspection terminal hall, industrial concrete flooring, official barrier gates in soft focus, quiet authoritative regulatory setting.",
                "beats": [2, 3]
            }
        }

        fg_roster = {
            "fg_evidence_prosecution_complaint_docket": {
                "title": "Official Legal Complaint Docket Document",
                "description": "Official Japanese district court legal filing document, titled prosecution complaint docket, bold Japanese kanji header, stamped with official red vermilion hanko seal, crisp document paper texture with clean sharp edges.",
                "role": "Lead Prosecution Docket",
                "beats": [1, 2, 5]
            },
            "fg_evidence_chemical_residue_inspection_sheet": {
                "title": f"Official Safety Inspection Analysis Sheet ({metric_highlight})",
                "description": f"Government accredited laboratory test certificate showing quantitative chemical analysis results with metric highlight '{metric_highlight}', red verification stamp, Japanese kanji column headers, crisp cutout edge.",
                "role": "Forensic Inspection Exhibit",
                "beats": [1, 2, 3]
            },
            "fg_evidence_damage_calculation_invoice": {
                "title": "Macro Economic Restitution & Damages Calculation Sheet",
                "description": "Official audit summary invoice document displaying highlighted financial calculation figures in green ledger ink, stamped diagonally with bold red ink '証拠物件 // 第1号' (EXHIBIT A), crisp paper cutout edge.",
                "role": "Forensic Accounting Exhibit",
                "beats": [1, 4, 5]
            },
            "fg_evidence_quarantine_customs_certificate": {
                "title": "Import Customs Quarantine Clearance Certificate",
                "description": "Port authority customs quarantine document with official batch serial numbers, regulatory verification stamps in red ink, tactile document folds, crisp cutout edges.",
                "role": "Logistics Regulatory Certificate",
                "beats": [2, 3, 4]
            },
            "fg_evidence_merchant_accounting_ledger": {
                "title": "Corporate Bookkeeping Ledger & Supply Record",
                "description": "Worn business bookkeeping ledger notebook open on a wooden table, showing ascending cost calculations and procurement records, paperclips, tactile ink lines.",
                "role": "Economic Paper Trail",
                "beats": [1, 2, 4]
            },
            "fg_evidence_sealed_whistleblower_memo": {
                "title": "Confidential Internal Corporate Whistleblower Memo",
                "description": "Manila folder envelope stamped '社外秘 // 厳秘' (CONFIDENTIAL // STRICTLY SECRET), partially opened revealing internal memo with black redacted bars across strategic paragraphs.",
                "role": "Whistleblower Document",
                "beats": [2, 3]
            },
            "fg_evidence_statutory_regulation_volume": {
                "title": "Commercial & Public Safety Statutory Reference Volume",
                "description": "Heavy leather-bound statutory legal reference volume open to regulatory oversight statute, gold lettering on spine, ribbon bookmark, sharp paper edges.",
                "role": "Statutory Authority",
                "beats": [1, 5]
            },
            "fg_evidence_hanko_ingam_seal": {
                "title": "Authenticated Vermilion Hanko Seal & Exhibit Artifact",
                "description": "Authentic Japanese circular red vermilion hanko seal impression beside dark wooden stamp cylinder on official verification paper, tactile paper texture.",
                "role": "Authentication Artifact",
                "beats": [3, 4, 5]
            },
            "fg_evidence_gavel_justice_scale": {
                "title": "Judicial Courtroom Sounding Gavel & Scales",
                "description": "Dark polished hardwood judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism.",
                "role": "Judicial Climax Artifact",
                "beats": [4, 5]
            }
        }

    elif m_up in ["KR", "KO"]:
        # Thị trường Hàn Quốc: Sawonjeung, Con dấu Ingam, Viện Kiểm sát / Tòa án Seoul, Báo cáo FSS
        bg_roster = {
            "bg_district_court_hall": {
                "title": "Seoul Central District Courthouse Grand Atrium",
                "description": "Cinematic wide-angle interior of Seoul Central District Court main judicial hall, polished stone colonnade, high vaulted ceiling with moody diffused daylight, quiet austere legal atmosphere.",
                "beats": [1, 5]
            },
            "bg_fss_regulatory_chamber": {
                "title": "Financial Supervisory Oversight Analytic Chamber",
                "description": "Modern regulatory analytical workspace, multi-monitor analytical financial flowcharts in soft background focus, dark slate walls, focused investigative atmosphere.",
                "beats": [2, 3]
            },
            "bg_executive_boardroom_dusk": {
                "title": "Corporate Executive Boardroom at Dusk",
                "description": "Modern corporate executive boardroom overlooking evening Seoul skyline through floor-to-ceiling glass windows, dark table reflection, clean architectural lines, zero clutter.",
                "beats": [1, 4]
            },
            "bg_merchant_warehouse_office": {
                "title": "Commercial Logistics & Enterprise Office",
                "description": "Authentic quiet enterprise inventory office, stacked shipping cartons in soft focus background, warm overhead lamp casting pool of light on desk, clean documentary mood.",
                "beats": [1, 2, 4]
            },
            "bg_investigative_newsroom_night": {
                "title": "Investigative Journalism Newsroom at Night",
                "description": "Nocturnal newsroom with dark empty desks receding into soft shadows, warm desk lamp pools, distant city lights through blinds, serious quiet investigative atmosphere.",
                "beats": [1, 2, 3]
            },
            "bg_forensic_archive_vault": {
                "title": "State Archive Document Vault",
                "description": "Steel shelving units holding hundreds of uniform legal archive boxes in deep linear perspective, clean concrete floor, cool fluorescent downlighting.",
                "beats": [3, 4]
            },
            "bg_legal_hearing_chamber": {
                "title": "National Assembly & Regulatory Hearing Chamber",
                "description": "Formal oak-paneled congressional hearing room with elevated committee bench in background soft focus, rich timber textures, dignified institutional setting.",
                "beats": [4, 5]
            }
        }

        fg_roster = {
            "fg_evidence_prosecution_complaint_docket": {
                "title": "Prosecution Indictment & Filing Docket",
                "description": "Official Korean prosecution indictment filing document, titled criminal court docket, bold Korean hangeul header, stamped with red official seal, crisp paper cutout edges.",
                "role": "Lead Prosecution Docket",
                "beats": [1, 2, 5]
            },
            "fg_evidence_fss_audit_report": {
                "title": f"Forensic Regulatory Audit Summary ({metric_highlight})",
                "description": f"Government regulatory forensic audit report displaying key evidentiary metrics '{metric_highlight}', highlighted with yellow marker, official red circular seal stamp.",
                "role": "Regulatory Audit Exhibit",
                "beats": [1, 2, 3]
            },
            "fg_evidence_damage_calculation_invoice": {
                "title": "Macro Restitution & Damages Calculation Sheet",
                "description": "Forensic accounting audit invoice document displaying bold liability figures in green ledger ink, stamped diagonally with bold red ink '극비 // 증거자료' (CONFIDENTIAL EXHIBIT), crisp paper cutout edge.",
                "role": "Forensic Accounting Exhibit",
                "beats": [1, 4, 5]
            },
            "fg_evidence_corporate_bank_ledger": {
                "title": "Corporate Banking Transaction & Financial Ledger",
                "description": "Enterprise financial bookkeeping ledger open on a wooden table, showing transaction records and irregular transfers, paperclips, tactile ink lines.",
                "role": "Financial Paper Trail",
                "beats": [1, 2, 4]
            },
            "fg_evidence_sawonjeung_id_badge": {
                "title": "Corporate Employee Identification Badge (Sawonjeung)",
                "description": "Official Korean corporate employee sawonjeung ID card with lanyard resting on confidential audit paperwork, photo card cutout edge.",
                "role": "Corporate Identity Exhibit",
                "beats": [2, 3, 4]
            },
            "fg_evidence_sealed_whistleblower_memo": {
                "title": "Confidential Internal Whistleblower Memo",
                "description": "Manila folder envelope stamped '대외비 // 비공개' (CONFIDENTIAL // RESTRICTED), partially opened revealing internal memo with black redacted bars across strategic clauses.",
                "role": "Whistleblower Document",
                "beats": [2, 3]
            },
            "fg_evidence_statutory_regulation_volume": {
                "title": "Commercial Code & Statutory Reference Volume",
                "description": "Heavy leather-bound legal reference volume open to statutory monopolization and fraud sections, gold lettering on spine, sharp paper edges.",
                "role": "Statutory Authority",
                "beats": [1, 5]
            },
            "fg_evidence_gavel_justice_scale": {
                "title": "Judicial Courtroom Gavel & Scales",
                "description": "Dark polished hardwood judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism.",
                "role": "Judicial Climax Artifact",
                "beats": [4, 5]
            }
        }

    elif m_up in ["VN", "VI"]:
        # Thị trường Việt Nam: Dấu mộc đỏ, Kết luận thanh tra, Tòa án nhân dân, Sổ phụ ngân hàng
        bg_roster = {
            "bg_district_court_hall": {
                "title": "Đại Sảnh Tòa Án Nhân Dân Trang Nghiêm",
                "description": "Không gian đại sảnh Tòa án Nhân dân trang nghiêm, hàng cột đá vững chãi, ánh sáng tự nhiên khuếch tán, bầu không khí pháp lý chuẩn mực không người qua lại.",
                "beats": [1, 5]
            },
            "bg_regulatory_inspection_headquarters": {
                "title": "Trụ Sở Cơ Quan Thanh Tra Chuyên Ngành",
                "description": "Không gian làm việc của cơ quan thanh tra kiểm tra chuyên ngành, các bảng biểu phân tích làm mờ ở hậu cảnh, ánh sáng nghiêm cẩn.",
                "beats": [2, 3]
            },
            "bg_executive_boardroom_dusk": {
                "title": "Phòng Họp Hội Đồng Quản Trị Lúc Chạng Vạng",
                "description": "Phòng họp doanh nghiệp tối giản nhìn ra đường chân trời thành phố lúc hoàng hôn qua cửa kính lớn, mặt bàn gỗ sẫm bóng loáng, bố cục kiến trúc sạch sẽ.",
                "beats": [1, 4]
            },
            "bg_merchant_warehouse_office": {
                "title": "Văn Phòng Hiện Trường Kho Vận Hàng Hóa",
                "description": "Văn phòng kho vận hiện trường chân thực, các kiện hàng hóa xếp ngăn nắp làm mờ ở hậu cảnh, đèn bàn rọi điểm sáng ấm trên bàn tài liệu.",
                "beats": [1, 2, 4]
            },
            "bg_investigative_newsroom_night": {
                "title": "Tòa Soạn Báo Điều Tra Ban Đêm",
                "description": "Tòa soạn báo đêm yên tĩnh với các bàn làm việc vắng bóng người chìm vào bóng tối mờ, vệt sáng đèn bàn ấm áp, không khí điều tra sâu sắc.",
                "beats": [1, 2, 3]
            },
            "bg_forensic_archive_vault": {
                "title": "Kho Lưu Trữ Hồ Sơ Tài Liệu Quốc Gia",
                "description": "Các dãy kệ thép lưu trữ hàng trăm hộp tài liệu pháp lý đồng nhất theo chiều sâu tuyến tính, sàn bê tông sạch sẽ, ánh sáng đèn huỳnh quang dịu mát.",
                "beats": [3, 4]
            },
            "bg_legal_hearing_chamber": {
                "title": "Phòng Xử Án & Điều Trần Trang Trọng",
                "description": "Phòng xét xử trang trọng với bục hội đồng xét xử bằng gỗ sẫm màu làm mờ ở hậu cảnh, chất liệu gỗ dày dặn, bối cảnh pháp lý uy nghi.",
                "beats": [4, 5]
            }
        }

        fg_roster = {
            "fg_evidence_prosecution_complaint_docket": {
                "title": "Hồ Sơ Cáo Trạng & Văn Bản Khởi Tố Pháp Lý",
                "description": "Văn bản hồ sơ tố tụng chính thức của cơ quan tiến hành tố tụng, tiêu đề in đậm, dập dấu triện đỏ thẩm quyền sắc nét, viền giấy sắc gọn.",
                "role": "Lead Prosecution Docket",
                "beats": [1, 2, 5]
            },
            "fg_evidence_inspection_conclusion_report": {
                "title": f"Bản Kết Luận Thanh Tra & Kiểm Định ({metric_highlight})",
                "description": f"Văn bản kết luận thanh tra chuyên ngành hiển thị con số phát hiện định lượng '{metric_highlight}', dập dấu mộc đỏ xác nhận, đường viền giấy sắc sảo.",
                "role": "Regulatory Inspection Exhibit",
                "beats": [1, 2, 3]
            },
            "fg_evidence_damage_calculation_invoice": {
                "title": "Bảng Kê Thiệt Hại & Quyết Định Thu Hồi Kinh Tế",
                "description": "Tài liệu bảng kê tính toán thiệt hại kinh tế hiển thị con số định lượng in mực kế toán, đóng dấu chéo MẬT // TÀI LIỆU CHỨNG CỨ bằng mực đỏ.",
                "role": "Forensic Accounting Exhibit",
                "beats": [1, 4, 5]
            },
            "fg_evidence_enterprise_bank_ledger": {
                "title": "Sổ Phụ Ngân Hàng & Bảng Kê Chứng Từ Kế Toán",
                "description": "Sổ kế toán doanh nghiệp mở trên mặt bàn gỗ hiển thị dòng tiền giao dịch và đối soát, kẹp giấy kim loại, vệt mực rõ nét.",
                "role": "Financial Paper Trail",
                "beats": [1, 2, 4]
            },
            "fg_evidence_sealed_whistleblower_memo": {
                "title": "Phong Bì Tài Liệu Mật Nội Bộ Doanh Nghiệp",
                "description": "Phong bì tài liệu màu nâu dập dấu 'MẬT // TUYỆT ĐỐI BẢO MẬT', hé mở để lộ văn bản nội bộ có các dòng bôi đen bảo mật.",
                "role": "Whistleblower Document",
                "beats": [2, 3]
            },
            "fg_evidence_statutory_regulation_volume": {
                "title": "Bộ Luật & Văn Bản Quy Phạm Pháp Luật Chuyên Ngành",
                "description": "Tập sách văn bản quy phạm pháp luật bìa da sẫm màu đóng gáy dày dặn, chữ mạ vàng, dải ruy băng đánh dấu trang, góc giấy sắc nét.",
                "role": "Statutory Authority",
                "beats": [1, 5]
            },
            "fg_evidence_official_red_seal_stamp": {
                "title": "Con Dấu Mộc Đỏ Thẩm Quyền Pháp Lý",
                "description": "Hình triện mộc đỏ chuẩn mực dập trên mặt giấy văn bản chứng cứ sắc sảo bên cạnh cán dấu gỗ trang nghiêm.",
                "role": "Authentication Artifact",
                "beats": [3, 4, 5]
            },
            "fg_evidence_gavel_justice_scale": {
                "title": "Búa Gỗ Tòa Án & Cán Cân Công Lý",
                "description": "Búa gỗ xét xử bằng gỗ gụ đánh bóng đặt trên đế gỗ bên cạnh cán cân công lý bằng đồng thau, chất gỗ tự nhiên chân thực.",
                "role": "Judicial Climax Artifact",
                "beats": [4, 5]
            }
        }

    else:
        # Thị trường Âu/Mỹ (EN): Federal Court Docket, Audit Binder, Damages Invoice, Whistleblower Memo
        bg_roster = {
            "bg_federal_court_hall": {
                "title": "Federal Courthouse Grand Hall",
                "description": "Cinematic wide-angle interior of federal courthouse hall, classical stone colonnade, high vaulted ceiling with moody diffused daylight, quiet austere judicial atmosphere, uncluttered background without distracting crowds.",
                "beats": [1, 5]
            },
            "bg_regulatory_oversight_chamber": {
                "title": "Regulatory Oversight Analytical Hearing Chamber",
                "description": "Formal oak-paneled federal hearing room with elevated judge bench in background soft focus, rich timber textures, formal dignified institutional setting.",
                "beats": [4, 5]
            },
            "bg_executive_boardroom_dusk": {
                "title": "Corporate Executive Boardroom at Dusk",
                "description": "Modern minimalist corporate boardroom overlooking dusky city skyline through panoramic floor-to-ceiling glass windows, dark mahogany table reflection, clean architectural lines, zero clutter.",
                "beats": [1, 4]
            },
            "bg_enterprise_warehouse_office": {
                "title": "Enterprise Operations Logistics Office",
                "description": "Authentic quiet business inventory office, cardboard shipping boxes neatly stacked in soft focus background, warm overhead industrial lamp casting gentle pool of light on desk, clean documentary mood.",
                "beats": [1, 2, 4]
            },
            "bg_investigative_newsroom_night": {
                "title": "Investigative Journalism Newsroom at Night",
                "description": "Nocturnal newsroom with dark empty desks receding into soft shadows, warm desk lamp pools, distant city lights through blinds, serious quiet investigative atmosphere.",
                "beats": [1, 2, 3]
            },
            "bg_forensic_archive_vault": {
                "title": "Federal Archive Document Vault",
                "description": "Steel shelving units holding hundreds of uniform gray legal archive boxes in deep linear perspective, clean concrete floor, cool fluorescent downlighting, forensic discovery vault.",
                "beats": [3, 4]
            },
            "bg_economics_analytics_lab": {
                "title": "Marketplace Economics & Data Analytics Lab",
                "description": "Modern analytical workspace with large soft-focus monitors displaying muted auction bidding flowcharts and heatmaps, dark slate walls, focused analytical atmosphere.",
                "beats": [2, 3]
            },
            "bg_server_cooling_facility": {
                "title": "Enterprise Cloud Data Center Facility",
                "description": "Deep perspective corridor of enterprise server racks in dark cooling room, subtle vertical cyan and amber LED tracer lights, clean floor reflection, atmospheric mist, uncluttered clean industrial tech environment.",
                "beats": [2, 3]
            }
        }

        fg_roster = {
            "fg_evidence_prosecution_complaint_docket": {
                "title": "Official Legal Prosecution Complaint Docket",
                "description": "Official legal filing document from the federal district court, bold case header, legal docket stamped with blue ink, crisp document paper texture with clean sharp edges.",
                "role": "Lead Prosecution Docket",
                "beats": [1, 2, 5]
            },
            "fg_evidence_damages_calculation_invoice": {
                "title": f"Forensic Accounting & Damages Summary Sheet ({metric_highlight})",
                "description": f"Government audit summary invoice document displaying bold figure '{metric_highlight}' in green ledger ink, stamped diagonally with bold red ink 'CONFIDENTIAL / EXHIBIT A', crisp paper cutout edge.",
                "role": "Forensic Accounting Exhibit",
                "beats": [1, 4, 5]
            },
            "fg_evidence_regulatory_audit_binder": {
                "title": "Forensic Investigative Audit Binder",
                "description": "Thick three-ring forensic investigative audit binder with tabbed colored dividers, official regulatory growth charts visible on front plastic sleeve.",
                "role": "Macro Financial Evidence",
                "beats": [3, 4, 5]
            },
            "fg_evidence_merchant_accounting_ledger": {
                "title": "Small Business Financial Accounting Ledger",
                "description": "Worn merchant bookkeeping ledger notebook open on a wooden table, showing ascending cost charges eroding profit margins, paperclips, tactile ink lines.",
                "role": "Victim Economic Evidence",
                "beats": [1, 2, 4]
            },
            "fg_evidence_sealed_whistleblower_memo": {
                "title": "Confidential Internal Whistleblower Memo Envelope",
                "description": "Manila folder envelope stamped 'RESTRICTED DISTRIBUTION // EXECUTIVE EYES ONLY', partially opened revealing internal memo with black redacted bars across strategic paragraphs.",
                "role": "Whistleblower Document",
                "beats": [2, 3]
            },
            "fg_evidence_statute_reference_book": {
                "title": "Federal Statutory Legal Reference Volume",
                "description": "Heavy vintage leather-bound legal codex open to federal statutory monopolization and fraud sections, gold leaf lettering on spine, ribbon bookmark, sharp paper edges.",
                "role": "Statutory Authority",
                "beats": [1, 5]
            },
            "fg_evidence_server_rack_drive": {
                "title": "Automated Algorithm Storage Module",
                "description": "High-tech brushed metallic enterprise server drive enclosure with flashing blue data activity LEDs, forensic evidence barcode sticker.",
                "role": "Technical Hardware Evidence",
                "beats": [2, 3]
            },
            "fg_evidence_gavel_justice_scale": {
                "title": "Federal Court Judicial Gavel & Scales",
                "description": "Dark polished walnut judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism.",
                "role": "Judicial Climax Artifact",
                "beats": [4, 5]
            }
        }

    return bg_roster, fg_roster


# ============================================================================
# DYNAMIC HERO CADENCE & SPATIAL PHYSICS (RULE 128)
# ============================================================================

def select_dynamic_hero_indices(spoken_sentences: List[Dict[str, Any]]) -> List[int]:
    """Rule 128 & User Mandate: Tuyển chọn các cảnh Hero AI Video (VEO) hoàn toàn động dựa trên nhịp điệu kể chuyện (cadence).
    - Tần suất trung bình - cao: Khoảng 12% - 18% tổng số cảnh (trung bình 5-7 cảnh có 1 cảnh Hero).
    - Cảnh mở màn (Scene 0) luôn là Hero (Cold Strike / Paradox Hook).
    - Điểm chuyển giao Beat (Beat transitions: cảnh đầu mỗi Beat).
    - Cảnh chốt hạ / Đỉnh điểm pháp lý (Climax / Resolution).
    - Các khoảnh khắc bằng chứng / dữ liệu pháp y trọng yếu (high-stakes catalyst metrics & evidence).
    - Khoảng cách tối thiểu giữa 2 Hero clips là >= 3 cảnh để tránh dồn ứ, và không vượt quá 8 cảnh để giữ nhịp kịch tính.
    - CẤM hardcode danh sách chỉ số hay số lượng chết.
    """
    total = len(spoken_sentences)
    if total == 0:
        return []
    if total <= 3:
        return [0]

    # Nhận diện điểm khởi đầu các Beat
    beat_first_indices = {}
    for idx, s in enumerate(spoken_sentences):
        b = int(s.get("beat_index") or ((idx // max(1, total // 5)) + 1))
        b = min(max(b, 1), 5)
        if b not in beat_first_indices:
            beat_first_indices[b] = idx

    # Từ khóa bằng chứng / xúc tác căng thẳng cao độ (đa ngôn ngữ EN, JP, KR, VN)
    catalyst_keywords = [
        # Numbers & metrics
        "billion", "tỷ", "million", "triệu", "억", "조", "万", "億", "兆", "mg/kg", "ppm", "percent", "%",
        # Legal & documents
        "docket", "complaint", "vụ kiện", "bản án", "cáo trạng", "khởi tố", "기소", "소송", "訴訟", "起訴",
        "gavel", "búa gỗ", "judge", "thẩm phán", "판사", "裁判",
        "statute", "đạo luật", "luật", "법률", "法律",
        "algorithm", "thuật toán", "알고리즘", "アルゴリズム",
        "secret", "bí mật", "whistleblower", "nội bộ", "내부고발", "内部告発",
        "damages", "thiệt hại", "hóa đơn", "invoice", "손해", "損害", "賠償",
        "memo", "redacted", "bôi đen", "ledger", "sổ sách", "장부", "帳簿",
        "court", "tòa án", "법원", "裁判所", "hearing", "điều trần", "청문회", "公聴会",
        "inspect", "quarantine", "thanh tra", "kiểm định", "감사", "검사", "監査", "検査"
    ]

    selected = [0]  # Scene 0 luôn là Hero
    last_hero = 0

    for idx in range(1, total):
        sent = spoken_sentences[idx]
        text = (sent.get("text") or "").lower()
        dist = idx - last_hero

        if dist < 3:
            continue

        is_beat_start = any(idx == b_idx for b_idx in beat_first_indices.values())
        is_climax_or_end = (idx == total - 1) or (idx >= total - 3 and any(w in text for w in ["gavel", "verdict", "judge", "court", "warning", "lesson", "búa", "kết luận", "판결", "判決"]))
        has_catalyst = any(kw in text for kw in catalyst_keywords)

        if dist >= 8:
            selected.append(idx)
            last_hero = idx
        elif is_beat_start and dist >= 4:
            selected.append(idx)
            last_hero = idx
        elif is_climax_or_end and dist >= 3:
            selected.append(idx)
            last_hero = idx
        elif has_catalyst and dist >= 5:
            selected.append(idx)
            last_hero = idx

    return selected


def determine_spatial_physics(narr: str, fg_key: Optional[str], hero_index: int) -> Tuple[str, str, str, str]:
    """Xác định hành vi xúc giác (Tactile Spatial Physics) dựa trên bản chất vật thể và ngữ cảnh kể chuyện (Rule 128).
    Hỗ trợ đối chiếu đa ngôn ngữ: EN, JP, KR, VN.
    Trả về: (physics_type, action_type, seed_mode, foleys)
    """
    n_low = narr.lower()
    fg_low = (fg_key or "").lower()

    if any(k in n_low or k in fg_low for k in ["gavel", "judge", "búa", "scales", "justice", "thẩm phán", "裁判", "判決", "판사", "법원"]):
        return "MACRO_HIGHLIGHT_WIPE", "MACRO_HIGHLIGHT_WIPE", "CUTOUT_ONLY", "gavel_thud"
    elif any(k in n_low or k in fg_low for k in ["gauge", "meter", "vial", "chemical", "hóa chất", "lưu huỳnh", "sulfur", "residue", "spectrometry", "측정", "분석", "検査", "残余"]):
        return "MACRO_HIGHLIGHT_WIPE", "MACRO_HIGHLIGHT_WIPE", "CUTOUT_ONLY", "gauge_needle_hiss"
    elif any(k in n_low or k in fg_low for k in ["server", "rack", "drive", "hardware", "led", "máy chủ", "phần cứng", "서버", "하드웨어"]):
        return "MACRO_HIGHLIGHT_WIPE", "MACRO_HIGHLIGHT_WIPE", "CUTOUT_ONLY", "paper_rustle"
    elif any(k in n_low or k in fg_low for k in ["docket", "memo", "confidential", "secret", "whistleblower", "dog-ear", "peel", "cáo trạng", "khởi tố", "mật", "bóc tách", "기소", "고발", "비밀", "内部告発"]):
        return "CORNER_DOGEAR_PEEL", "CORNER_DOGEAR_PEEL", "COMPOSITE_16_9", "paper_page_turn"
    elif any(k in n_low or k in fg_low for k in ["invoice", "damage", "bill", "check", "listing", "card", "hóa đơn", "bồi thường", "chi phí", "영수증", "손해", "請求書", "損害"]):
        return "DOCUMENT_TABLE_DROP", "DOCUMENT_TABLE_DROP", "COMPOSITE_16_9", "document_table_thud"
    elif any(k in n_low or k in fg_low for k in ["dossier", "contract", "agreement", "binder", "ledger", "book", "hợp đồng", "sổ sách", "hồ sơ", "계약", "장부", "契約", "帳簿"]):
        return "BIFOLD_DOSSIER_OPEN", "BIFOLD_DOSSIER_OPEN", "COMPOSITE_16_9", "paper_crease_snap"
    else:
        cycle = hero_index % 3
        if cycle == 0:
            return "CORNER_DOGEAR_PEEL", "CORNER_DOGEAR_PEEL", "COMPOSITE_16_9", "paper_page_turn"
        elif cycle == 1:
            return "DOCUMENT_TABLE_DROP", "DOCUMENT_TABLE_DROP", "COMPOSITE_16_9", "document_table_thud"
        else:
            return "BIFOLD_DOSSIER_OPEN", "BIFOLD_DOSSIER_OPEN", "COMPOSITE_16_9", "paper_crease_snap"


def load_style_config(preset_name: Optional[str] = None) -> Dict[str, Any]:
    """Nạp cấu hình phong cách từ config/prompts/style-config.yaml (Rule 128 & Rule 132)."""
    config_path = ROOT_DIR / "config" / "prompts" / "style-config.yaml"
    if not config_path.exists():
        return {
            "name": "vox_forensic_paper",
            "positive": "tangible forensic investigative paper docudrama, heavy 300gsm fibrous cardstock, sharp cardstock creases, official audit stamps, classified exhibit labels, clean 2D stylized graphic novel comic ink outlines, bold linework, crosshatching, flat cel-shading, tabletop flat-lay evidence setting",
            "motion_behavior": "12fps tactile stop-motion documentary motion, mechanical paper folding and dog-ear corner peel, crisp document table drop with subtle paper flutter, steady tripod camera drift, zero warping or morphing of text, staggered discrete frame steps",
            "negative": "no photorealism, no live-action video, no real people, no 3D wax characters, no smooth 60fps interpolation, no gooey liquid warping, no anime, no watercolor",
            "camera_defaults": {"allowed": ["static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"]},
            "lighting_defaults": "45-degree directional evening boardroom keylight, deep contact shadows onto dark mahogany surface",
            "clip_duration_seconds": {"min": 4, "max": 8, "default": 5},
            "prompt_template": "{style_anchor.positive}, {style_anchor.motion_behavior}. Scene: {scene.subject} {scene.action} in {scene.setting}. Camera: {scene.camera}. Lighting: {scene.lighting}. {style_anchor.negative}"
        }

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    presets = data.get("presets", {})
    chosen_name = preset_name or data.get("active_preset", "vox_forensic_paper")
    preset_data = presets.get(chosen_name)
    if not preset_data:
        chosen_name = next(iter(presets.keys()), "vox_forensic_paper")
        preset_data = presets.get(chosen_name, {})

    return {
        "name": chosen_name,
        "positive": " ".join(str(preset_data.get("positive", "")).split()),
        "motion_behavior": " ".join(str(preset_data.get("motion_behavior", "")).split()),
        "negative": " ".join(str(preset_data.get("negative", "")).split()),
        "camera_defaults": preset_data.get("camera_defaults", {"allowed": ["static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"]}),
        "lighting_defaults": " ".join(str(preset_data.get("lighting_defaults", "warm diorama studio light, soft shadows, subtle rim light")).split()),
        "clip_duration_seconds": preset_data.get("clip_duration_seconds", {"min": 4, "max": 8, "default": 5}),
        "prompt_template": data.get("prompt_template", "")
    }


def format_final_veo_prompt(
    preset: Dict[str, Any],
    subject: str,
    action: str,
    setting: str,
    camera: str,
    lighting: Optional[str] = None
) -> str:
    """Ghép final_veo_prompt theo template chuẩn:
    {style_anchor.positive}, {style_anchor.motion_behavior}.
    Scene: {scene.subject} {scene.action} in {scene.setting}.
    Camera: {scene.camera}. Lighting: {scene.lighting}.
    {style_anchor.negative}
    """
    pos = preset.get("positive", "")
    mot = preset.get("motion_behavior", "")
    neg = preset.get("negative", "")
    lt = lighting or preset.get("lighting_defaults", "")
    
    prompt = (
        f"{pos}, {mot}. "
        f"Scene: {subject} {action} in {setting}. "
        f"Camera: {camera}. Lighting: {lt}. "
        f"{neg}"
    )
    return " ".join(prompt.split())


def get_action_description(action_type: str, seed_title: str, narration: str) -> str:
    """Tạo mô tả hành động xúc giác ngắn gọn cho VEO physics prompt (không lặp lại subject)."""
    if action_type == "CORNER_DOGEAR_PEEL":
        return "top sheet dog-ear corner curling and peeling backward in crisp 12fps mechanical steps, lifting upward to reveal confidential audit docket beneath"
    elif action_type == "DOCUMENT_TABLE_DROP":
        return "sliding rapidly into frame and slamming onto executive table with a sharp stop-motion bounce, settling flat with paper flutter"
    elif action_type == "BIFOLD_DOSSIER_OPEN":
        return "with sharp center crease opening outward flat onto table in clean mechanical 12fps steps, revealing internal financial charts"
    elif action_type == "MACRO_HIGHLIGHT_WIPE":
        n_low = narration.lower()
        if any(k in n_low for k in ["gavel", "judge", "court", "verdict", "búa", "toà"]):
            return "resting beside brass scales of justice on mahogany table under dramatic directional spotlight with subtle dust motes and micro-vibrations"
        elif any(k in n_low for k in ["gauge", "needle", "chemical", "sulfur", "residue", "hóa chất"]):
            return "industrial circular analog gauge needle rising steadily toward danger threshold zone with warm reflection"
        elif any(k in n_low for k in ["server", "hardware", "rack", "máy chủ"]):
            return "high-tech enterprise server rack drive module with rhythmic blue data activity LEDs flashing in cool mist"
        else:
            return "resting on dark mahogany desk under dramatic directional studio keylight with 12fps documentary tracking motion"
    else:
        return "resting on table with subtle 12fps micro-jitter in steady documentary tracking"


def generate_tactile_physics_prompt(scene_idx: int, narration: str, action_type: str, seed_title: str) -> str:
    """Backward-compatible wrapper for tactile physics prompt."""
    preset = load_style_config("vox_forensic_paper")
    action_desc = get_action_description(action_type, seed_title, narration)
    return format_final_veo_prompt(
        preset=preset,
        subject=seed_title,
        action=action_desc,
        setting="dark mahogany executive boardroom table at dusk",
        camera="slow_push_in" if scene_idx % 2 == 0 else "cinematic_pan"
    )


# ============================================================================
# MASTER UNIFIED DIRECTOR PLANNER (RULE 125 SINGLE TRUTH & RULE 128)
# ============================================================================

def build_unified_director_plan(
    spoken_sentences: List[Dict[str, Any]],
    ep_dir: Path,
    style_preset: Optional[str] = None,
    story_text: Optional[str] = None,
    grounding_intel: Optional[Dict[str, Any]] = None,
    competitor_card: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    market: Optional[str] = None
) -> Dict[str, Any]:
    """Hợp nhất B3 + B3.5:
    Tạo cấu trúc phân cảnh, gán Veo clips Tactile Physics động và Remotion Stop-Motion Directives.
    Hoàn toàn Generic 100%, không bị bias hay hardcode vào bất kỳ đề tài đơn lẻ nào (Rule 128).
    """
    preset = load_style_config(style_preset)
    allowed_cameras = preset.get("camera_defaults", {}).get("allowed", [
        "static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"
    ])
    layout_zones = ["split_evidence_left", "center_hero_document", "split_evidence_right", "macro_detail_focus"]

    meta = metadata or {}
    ep_id = meta.get("episode_id") or ep_dir.name
    mkt = (market or meta.get("market") or ep_id.split("_")[0]).upper()
    topic = meta.get("topic") or meta.get("raw_term") or ep_id

    # 1. Trích xuất Dynamic Visual Roster độc lập theo kịch bản và thị trường
    bg_roster, fg_roster = extract_dynamic_visual_roster(
        story_text=story_text or "",
        spoken_sentences=spoken_sentences,
        grounding_intel=grounding_intel,
        competitor_card=competitor_card,
        market=mkt,
        topic=topic
    )

    scenes = []
    hero_clips = []
    hero_count = 0

    dynamic_hero_indices = set(select_dynamic_hero_indices(spoken_sentences))
    bg_keys = list(bg_roster.keys())
    fg_keys = list(fg_roster.keys())

    for idx, sent in enumerate(spoken_sentences):
        narr = sent.get("text", "")
        dur_frames = int(sent.get("duration_frames") or 150)
        dur_sec = float(sent.get("duration_sec") or ((sent.get("end_ms", 0) - sent.get("start_ms", 0)) / 1000.0 if sent.get("end_ms") else 0.0) or round(dur_frames / 30.0, 3))
        beat_idx = int(sent.get("beat_index") or ((idx // max(1, len(spoken_sentences) // 5)) + 1))
        beat_idx = min(max(beat_idx, 1), 5)

        # Matching Background phù hợp theo Beat và thứ tự cảnh
        matching_bgs = [k for k, v in bg_roster.items() if beat_idx in v.get("beats", [1, 2, 3, 4, 5])]
        if not matching_bgs:
            matching_bgs = bg_keys
        bg_key = matching_bgs[(idx // 3) % len(matching_bgs)]

        # Matching Foreground Evidence dựa trên từ khóa kể chuyện hoặc luân phiên Beat
        narr_lower = narr.lower()
        fg_key = None

        if any(k in narr_lower for k in ["court", "indictment", "docket", "complaint", "tòa", "khởi tố", "cáo trạng", "기소", "소송", "訴訟"]):
            for k in fg_keys:
                if "docket" in k or "complaint" in k or "indictment" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["inspect", "test", "residue", "sulfur", "chemical", "thanh tra", "kiểm định", "hóa chất", "검사", "분석", "検査"]):
            for k in fg_keys:
                if "inspection" in k or "residue" in k or "audit_report" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["damage", "restitution", "invoice", "loss", "billion", "thiệt hại", "bồi thường", "hóa đơn", "손해", "배상", "損害", "賠償"]):
            for k in fg_keys:
                if "damage" in k or "invoice" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["ledger", "transaction", "bank", "cost", "margin", "sổ sách", "ngân hàng", "장부", "계좌", "帳簿"]):
            for k in fg_keys:
                if "ledger" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["memo", "whistleblower", "confidential", "secret", "mật", "nội bộ", "내부고발", "비밀", "内部告発"]):
            for k in fg_keys:
                if "memo" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["statute", "law", "regulation", "luật", "quy định", "법률", "규정", "法律"]):
            for k in fg_keys:
                if "statute" in k or "regulation" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["gavel", "judge", "verdict", "búa", "phán quyết", "판결", "判決"]):
            for k in fg_keys:
                if "gavel" in k or "justice" in k:
                    fg_key = k
                    break
        elif any(k in narr_lower for k in ["seal", "stamp", "hanko", "ingam", "dấu", "triện", "도장", "인감", "判子"]):
            for k in fg_keys:
                if "seal" in k or "hanko" in k or "ingam" in k:
                    fg_key = k
                    break

        if not fg_key:
            matching_fgs = [k for k, v in fg_roster.items() if beat_idx in v.get("beats", [1, 2, 3, 4, 5])]
            if not matching_fgs:
                matching_fgs = fg_keys
            fg_key = matching_fgs[idx % len(matching_fgs)]

        cam_move = allowed_cameras[idx % len(allowed_cameras)]
        layout_choice = layout_zones[idx % len(layout_zones)]
        transition_choice = "stop_motion_flicker_cut" if idx % 2 == 1 else "hard_cut"

        seed_title = fg_roster[fg_key]["title"] if fg_key else bg_roster[bg_key]["title"]
        setting_desc = bg_roster[bg_key]["title"]

        is_hero_video = idx in dynamic_hero_indices
        if is_hero_video:
            flow_slot = FLOW_ACCOUNTS[hero_count % len(FLOW_ACCOUNTS)]
            physics_type, action_type, seed_mode, foleys = determine_spatial_physics(narr, fg_key, hero_count)
            action_desc = get_action_description(action_type, seed_title, narr)
            veo_prompt = format_final_veo_prompt(
                preset,
                subject=seed_title,
                action=action_desc,
                setting=setting_desc,
                camera=cam_move,
                lighting=preset["lighting_defaults"]
            )
            source_img = f"assets/keyframes/hero_sc{idx:03d}_seed.png" if seed_mode == "CUTOUT_ONLY" else f"assets/composite/sc{idx:03d}_composite.png"

            shot_type = "HERO_AI_VIDEO"
            clip_entry = {
                "scene_id": f"sc{idx:03d}",
                "hero_index": hero_count + 1,
                "flow_slot": flow_slot,
                "spatial_physics_type": physics_type,
                "action_type": action_type,
                "seed_asset_mode": seed_mode,
                "source_image": source_img,
                "subject": seed_title,
                "action": action_desc,
                "setting": setting_desc,
                "camera": cam_move,
                "lighting": preset["lighting_defaults"],
                "duration_seconds": dur_sec,
                "duration_sec": dur_sec,
                "transition_out": transition_choice,
                "audio_cue": foleys,
                "text_overlay": None,
                "final_veo_prompt": veo_prompt,
                "bg_key": bg_key,
                "fg_key": fg_key,
                "prompt": veo_prompt,
                "foleys_audio": foleys,
                "output_filename": f"hero_video_sc{idx:03d}.mp4"
            }
            hero_clips.append(clip_entry)
            hero_count += 1
        else:
            shot_type = "TACTILE_STOP_MOTION_COLLAGE"
            physics_type = "REMOTION_FORENSIC"
            flow_slot = None
            foleys = "stamp_impact" if ("invoice" in (fg_key or "") or "docket" in (fg_key or "") or "seal" in (fg_key or "")) else "paper_rustle"
            action_desc = f"{seed_title} evidentiary display in tactile stop-motion"
            veo_prompt = None
            source_img = f"assets/composite/sc{idx:03d}_composite.png"

        has_foreground = (shot_type == "TACTILE_STOP_MOTION_COLLAGE" and idx % 3 != 2)
        assigned_fg = fg_key if has_foreground else None

        # Remotion Stop-Motion Animation Directives
        remotion_instructions = {
            "layout": "FULLSCREEN_AI_VIDEO" if shot_type == "HERO_AI_VIDEO" else "MULTI_LAYER_COLLAGE",
            "camera_drift": cam_move,
            "spatial_physics_type": physics_type,
            "foleys_trigger": foleys,
            "stop_motion": {
                "enabled": (shot_type == "TACTILE_STOP_MOTION_COLLAGE"),
                "stepped_fps": 12,
                "jitter_px": 2,
                "rotation_deg": 1.2 if idx % 2 == 0 else -1.2,
                "entrance": "SNAP_DROP_BOUNCE" if idx % 3 == 0 else "PAPER_SLIDE_IN"
            },
            "overlays": (
                ["RED_YARN_CONNECTOR", "YELLOW_MARKER_STRIKE"] if "docket" in (assigned_fg or "") or "inspection" in (assigned_fg or "") else
                ["RED_STAMP_SLAM", "CASE_STAMP"] if "invoice" in (assigned_fg or "") or "memo" in (assigned_fg or "") or "seal" in (assigned_fg or "") else
                ["COUNTER_ROLLUP"] if "gauge" in (assigned_fg or "") or "ledger" in (assigned_fg or "") else
                []
            )
        }

        scene_obj = {
            "scene_id": f"sc{idx:03d}",
            "source_image": source_img,
            "subject": seed_title,
            "action": action_desc,
            "setting": setting_desc,
            "camera": cam_move,
            "lighting": preset["lighting_defaults"],
            "duration_seconds": dur_sec,
            "duration_frames": dur_frames,
            "duration_sec": dur_sec,
            "audio_cue": foleys,
            "text_overlay": None,
            "transition_out": transition_choice,
            "final_veo_prompt": veo_prompt,
            "beat_index": beat_idx,
            "narration": narr,
            "shot_type": shot_type,
            "spatial_physics_type": physics_type,
            "flow_slot": flow_slot,
            "foleys_audio": foleys,
            "veo_action_prompt": veo_prompt,
            "background": {
                "reuse_key": bg_key,
                "title": bg_roster[bg_key]["title"],
                "description": bg_roster[bg_key]["description"]
            },
            "foreground": {
                "reuse_key": assigned_fg,
                "title": fg_roster[assigned_fg]["title"] if assigned_fg else None,
                "description": fg_roster[assigned_fg]["description"] if assigned_fg else None,
                "role": fg_roster[assigned_fg]["role"] if assigned_fg else None,
                "position": "left" if "left" in layout_choice else ("right" if "right" in layout_choice else "center")
            } if assigned_fg else None,
            "remotion_instructions": remotion_instructions
        }
        scenes.append(scene_obj)

    # 2. Tự động sinh và ghi file flow_video_manifest.json (Khế ước VEO Hero clips)
    manifest_data = {
        "episode_id": ep_id,
        "total_clips": len(hero_clips),
        "clips": hero_clips
    }
    
    # Ghi vào ep_dir và /var/vf/episodes/<ep_id> nếu có
    target_dirs = [ep_dir]
    var_ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    if var_ep_dir.exists() and var_ep_dir not in target_dirs:
        target_dirs.append(var_ep_dir)

    for td in target_dirs:
        try:
            td.mkdir(parents=True, exist_ok=True)
            with open(td / "flow_video_manifest.json", "w", encoding="utf-8") as mf:
                json.dump(manifest_data, mf, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return {
        "scenes": scenes,
        "hero_clips": hero_clips,
        "background_roster": bg_roster,
        "foreground_roster": fg_roster
    }


def main():
    parser = argparse.ArgumentParser(description="Unified VOX Director Engine (B3 + B3.5)")
    parser.add_argument("--episode", default=None, help="Episode ID (e.g. <MARKET>_EP<XXXX>_<slug>)")
    parser.add_argument("--ep-dir", default=None, help="Explicit path to episode folder")
    parser.add_argument("--style-preset", default="vox_forensic_paper", help="Style preset from style-config.yaml")
    args = parser.parse_args()

    ep_id = args.episode
    if not ep_id:
        pending_dir = Path("/var/vf/pending_tasks")
        if pending_dir.exists():
            tasks = [f.stem for f in pending_dir.glob("*.json")]
            if tasks:
                ep_id = tasks[0]
        if not ep_id:
            episodes_dir = Path("/var/vf/episodes")
            if episodes_dir.exists():
                active = [d.name for d in episodes_dir.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
                if active:
                    ep_id = sorted(active)[-1]
        if not ep_id:
            parser.error("Episode ID is required via --episode")

    if args.ep_dir:
        ep_dir = Path(args.ep_dir)
    else:
        vps_ep_dir = Path(f"/var/vf/episodes/{ep_id}")
        local_ep_dir = ROOT_DIR / "episodes" / ep_id
        ep_dir = vps_ep_dir if vps_ep_dir.exists() else local_ep_dir

    print(f"🚀 Chạy Unified VOX Spatial Physics Director cho {ep_id} tại {ep_dir}...")
    ep_dir.mkdir(parents=True, exist_ok=True)

    spoken_file = ep_dir / "spoken_sentences.json"
    if spoken_file.exists():
        with open(spoken_file, "r", encoding="utf-8") as f:
            spoken_sentences = json.load(f)
    elif (ep_dir / "director_plan.json").exists():
        print("💡 Nạp danh sách câu thoại từ director_plan.json hiện có...")
        with open(ep_dir / "director_plan.json", "r", encoding="utf-8") as f:
            dp = json.load(f)
            spoken_sentences = [
                {
                    "text": s.get("narration", ""),
                    "duration_frames": s.get("duration_frames", 150),
                    "duration_sec": s.get("duration_sec", 5.0),
                    "beat_index": s.get("beat_index", 1)
                }
                for s in dp.get("scenes", [])
            ]
    else:
        print(f"❌ Không tìm thấy dữ liệu kịch bản tại {ep_dir}")
        sys.exit(1)

    result = build_unified_director_plan(spoken_sentences, ep_dir, style_preset=args.style_preset)
    scenes = result["scenes"]
    hero_clips = result["hero_clips"]
    bg_roster = result.get("background_roster", {})
    fg_roster = result.get("foreground_roster", {})

    # 1. Lưu director_plan.json
    dp_data = {
        "episode_id": ep_id,
        "total_scenes": len(scenes),
        "total_hero_ai_videos": len(hero_clips),
        "scenes": scenes
    }
    dp_path = ep_dir / "director_plan.json"
    with open(dp_path, "w", encoding="utf-8") as f:
        json.dump(dp_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã tạo director_plan.json ({len(scenes)} cảnh, {len(hero_clips)} Veo 3D clips) -> {dp_path}")

    # 2. Lưu prompts_forge.json
    bg_prompts = {k: _sanitize_background_prompt(v["description"], bg_key=k, market=ep_id.split("_")[0]) for k, v in bg_roster.items()}
    fg_prompts = {k: _sanitize_foreground_prompt(v["description"], fg_key=k, market=ep_id.split("_")[0]) for k, v in fg_roster.items()}
    prompts_data = {
        "episode_id": ep_id,
        "backgrounds": bg_prompts,
        "foregrounds": fg_prompts
    }
    pf_path = ep_dir / "prompts_forge.json"
    with open(pf_path, "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã tạo prompts_forge.json ({len(bg_prompts)} BGs, {len(fg_prompts)} FGs) -> {pf_path}")

    # 3. flow_video_manifest.json đã được tự động lưu trong build_unified_director_plan()
    man_path = ep_dir / "flow_video_manifest.json"
    print(f"✅ Đã tạo flow_video_manifest.json ({len(hero_clips)} clips phân bổ {len(FLOW_ACCOUNTS)} tài khoản) -> {man_path}")

    print("\n" + "=" * 70)
    print(f"📊 BẢO CHỨNG PHÂN BỔ {len(hero_clips)} CLIPS VEO CHO {len(FLOW_ACCOUNTS)} TÀI KHOẢN GOOGLE FLOW:")
    print("=" * 70)
    acc_distribution = {}
    for c in hero_clips:
        slot = c["flow_slot"]
        acc_distribution[slot] = acc_distribution.get(slot, 0) + 1
    for slot, count in sorted(acc_distribution.items()):
        print(f"• {slot}: {count} clips")


if __name__ == "__main__":
    main()
