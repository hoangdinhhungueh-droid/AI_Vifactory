#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/unified_vox_director.py
Unified VOX Spatial Physics Director Engine (B3 & B3.5 Combined)
Merges Scene Breakdown, Veo 3.1 3D Tactile Origami Physics (20 clips across 6 Google accounts),
and Tactile Stop-Motion Collage Remotion Directives (12fps stepped jitter, paper drop shadow).
Compliant with:
- Rule 120 (Word-level Audio Sync with Whisper)
- Rule 122 (Pixel-Level Visual Audit Gate & Zero-Mock Score)
- Rule 128 (Zero Semantic Bias in Contracts)
- Rule 132 (Decoupled Engine)
- Rule 445 (5-Beat Docudrama Storyboard Structure)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import _sanitize_foreground_prompt, _sanitize_background_prompt

# 14 Tangible Evidence Objects Roster
OBJECT_ROSTER = {
    "fg_evidence_ftc_complaint_docket": {
        "title": "FTC Seattle Court Docket No. 2:26-CV-01392",
        "description": "Official legal filing document from the US District Court for the Western District of Washington, titled Federal Trade Commission v. Amazon.com Inc, bold header, legal docket stamped with blue ink, crisp document paper texture with clean sharp edges.",
        "role": "Lead Prosecution Docket",
        "beats": [1, 2, 5]
    },
    "fg_evidence_amazon_search_sponsored_box": {
        "title": "Amazon Search Results Sponsored Card",
        "description": "Physical representation of an e-commerce search result product listing card with prominent bold red circle around the small 'Sponsored' badge, detailed star ratings, price tag, and search query field.",
        "role": "Advertising Interface Exhibit",
        "beats": [1, 2, 3]
    },
    "fg_evidence_soft_reserve_algorithm_gauge": {
        "title": "Soft Reserve Algorithm Escalation Gauge",
        "description": "Tactile circular analog-digital industrial gauge with needle pointing from 30% into the red danger zone at 80%, labeled 'SOFT RESERVE FLOOR', brass bezel, glass face reflecting subtle amber warning light.",
        "role": "Pricing Mechanism Instrument",
        "beats": [1, 3, 4]
    },
    "fg_evidence_20b_damage_invoice": {
        "title": "$20 Billion Damages Calculation Sheet",
        "description": "Government audit summary invoice document displaying bold figure '$20,482,910,000' in green ledger ink, stamped diagonally with bold red ink 'CONFIDENTIAL / EXHIBIT A', crisp paper cutout edge.",
        "role": "Forensic Accounting Exhibit",
        "beats": [1, 4, 5]
    },
    "fg_evidence_auction_bid_log_paper": {
        "title": "Second-Price Auction Bid Resolution Log",
        "description": "High-density technical printout showing algorithmic bid comparison columns, timestamps in milliseconds, runner-up bid vs clearing price, with handwritten forensic annotations in red ink.",
        "role": "Algorithmic Evidence Log",
        "beats": [2, 3, 4]
    },
    "fg_evidence_sealed_memo_envelope": {
        "title": "Confidential Internal Project Nessie Memo",
        "description": "Manila folder envelope stamped 'RESTRICTED DISTRIBUTION // EXECUTIVE EYES ONLY', partially opened revealing internal memo memo with black redacted bars across strategic pricing paragraphs.",
        "role": "Whistleblower Document",
        "beats": [2, 3]
    },
    "fg_evidence_ohio_seller_bank_ledger": {
        "title": "Ohio Small Business Merchant Financial Ledger",
        "description": "Worn merchant bookkeeping ledger notebook open on a wooden table, showing ascending cost-per-click charges eroding product profit margins, paperclips, coffee stain, tactile ink lines.",
        "role": "Victim Economic Evidence",
        "beats": [1, 2, 4]
    },
    "fg_evidence_antitrust_statute_book": {
        "title": "Sherman Act Section 2 Legal Reference Volume",
        "description": "Heavy vintage leather-bound legal codex open to federal antitrust monopolization statute, gold leaf lettering on spine, ribbon bookmark, sharp paper edges.",
        "role": "Statutory Authority",
        "beats": [1, 5]
    },
    "fg_evidence_server_rack_drive": {
        "title": "Automated Auction Engine Storage Module",
        "description": "High-tech brushed metallic enterprise server drive enclosure with flashing blue data activity LEDs, forensic evidence barcode sticker labeled 'SEATTLE DATA CENTER EXTRACT'.",
        "role": "Technical Hardware Evidence",
        "beats": [2, 3]
    },
    "fg_evidence_redacted_contract_sheet": {
        "title": "Third-Party Merchant Ad Agreement",
        "description": "Multi-page legal agreement document with heavy black marker redactions across fee schedule clauses, paperclip at top, official corporate seal embossed in lower right.",
        "role": "Merchant Terms Contract",
        "beats": [2, 4]
    },
    "fg_evidence_damages_ledger_binder": {
        "title": "$68 Billion Advertising Revenue Audit Binder",
        "description": "Thick three-ring forensic investigative audit binder with tabbed colored dividers labeled 2019 through 2025, explosive revenue growth bar chart visible on front plastic sleeve.",
        "role": "Macro Financial Evidence",
        "beats": [3, 4, 5]
    },
    "fg_evidence_dossier_stamp_lina_khan": {
        "title": "FTC Chair Lina Khan Regulatory Dossier Stamp",
        "description": "Press cutout document dossier card featuring monochrome graphic novel editorial portrait of FTC Chair Lina Khan, official FTC seal badge in corner, paper clipped to evidentiary background card.",
        "role": "Regulatory Leadership Dossier",
        "beats": [1, 5]
    },
    "fg_evidence_dossier_stamp_andy_jassy": {
        "title": "Amazon Executive Leadership Dossier Stamp",
        "description": "Press cutout dossier document card featuring monochrome graphic novel editorial portrait of Amazon CEO Andy Jassy, corporate headquarters watermark, legal subpoena stamp.",
        "role": "Corporate Leadership Dossier",
        "beats": [2, 4]
    },
    "fg_evidence_gavel_justice_scale": {
        "title": "Federal Court Judicial Gavel & Scales",
        "description": "Dark polished walnut judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism.",
        "role": "Judicial Climax Artifact",
        "beats": [4, 5]
    }
}

# 8 Uncluttered Backgrounds Roster
BACKGROUND_ROSTER = {
    "bg_seattle_federal_court_hall": {
        "title": "Seattle Federal Courthouse Grand Hall",
        "description": "Cinematic wide-angle interior of Seattle federal courthouse hall, classical stone colonnade, high vaulted ceiling with moody diffused daylight, quiet austere judicial atmosphere, uncluttered background without distracting crowds.",
        "beats": [1, 5]
    },
    "bg_amazon_dark_server_room": {
        "title": "Amazon Cloud Computing Data Center",
        "description": "Deep perspective corridor of enterprise server racks in dark cooling room, subtle vertical cyan and amber LED tracer lights, clean floor reflection, atmospheric mist, uncluttered clean industrial tech environment.",
        "beats": [2, 3]
    },
    "bg_executive_boardroom_dusk": {
        "title": "Corporate Executive Boardroom at Dusk",
        "description": "Modern minimalist corporate boardroom overlooking dusky Seattle city skyline through panoramic floor-to-ceiling glass windows, dark mahogany table reflection, clean architectural lines, zero clutter.",
        "beats": [1, 4]
    },
    "bg_ohio_small_business_backroom": {
        "title": "Ohio Small Business Warehouse Office",
        "description": "Authentic quiet small business inventory office, cardboard shipping boxes neatly stacked in soft focus background, warm overhead industrial lamp casting gentle pool of light on desk, clean documentary mood.",
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
    "bg_auction_mechanics_lab": {
        "title": "Marketplace Economics Research Lab",
        "description": "Modern analytical workspace with large soft-focus monitors displaying muted auction bidding flowcharts and heatmaps, dark slate walls, focused analytical atmosphere.",
        "beats": [2, 3]
    },
    "bg_legal_hearing_chamber": {
        "title": "Federal Antitrust Hearing Chamber",
        "description": "Formal oak-paneled congressional or federal hearing room with elevated judge bench in background soft focus, rich timber textures, formal dignified institutional setting.",
        "beats": [4, 5]
    }
}

# 20 Canonical Hero Video Anchor Scenes (evenly distributed across 6 Google accounts)
HERO_SCENE_INDICES = [
    0,   # Beat 1: Hook opening gavel strike
    4,   # Beat 1: $20 billion paradox invoice
    10,  # Beat 1: Sponsored product listing takeover
    16,  # Beat 1: Lina Khan FTC complaint filing
    22,  # Beat 1: Climax transition into second-price auction
    28,  # Beat 2: Cloud server rack blinking in dark
    34,  # Beat 2: Small business merchant ledger
    40,  # Beat 2: Secret pricing algorithm trigger
    48,  # Beat 2 Climax: Paper trail discovery in vault
    54,  # Beat 3: Soft reserve floor rising to 80%
    60,  # Beat 3: Millisecond bidding log printout
    66,  # Beat 3: Corporate boardroom dusk meeting
    74,  # Beat 3 Climax: The 68 billion revenue explosion
    80,  # Beat 4: Redacted merchant contracts
    86,  # Beat 4: Internal Project Nessie memo
    92,  # Beat 4: Andy Jassy executive leadership dossier
    98,  # Beat 4 Climax: Ohio small business fallout
    104, # Beat 5: Federal courtroom hearing chamber
    116, # Beat 5: Algorithmic pricing spread & Sherman Act
    126  # Beat 5: Final judge gavel striking wooden block
]

FLOW_ACCOUNTS = ["acc_01", "acc_02", "acc_03", "acc_04", "acc_05", "acc_06"]

def generate_tactile_physics_prompt(scene_idx: int, narration: str, action_type: str, seed_title: str) -> str:
    """Tạo prompt xúc giác 5 thành phần cho Veo 3.1 - Fast.
    Khóa 100% Graphic Novel, 0% người thật, chuẩn hóa 4 Forensic Paper Stop-Motion Patterns.
    """
    if action_type == "CORNER_DOGEAR_PEEL":
        action = (
            f"Tactile forensic document stop-motion animation: The dog-eared corner of {seed_title} "
            f"curls and peels backward in crisp 12fps stop-motion mechanical steps, lifting upward to reveal "
            f"the underlying confidential evidence docket beneath it. Subtle 12fps organic paper flutter "
            f"and micro-jitter animate the document resting on the dark executive boardroom table."
        )
    elif action_type == "DOCUMENT_TABLE_DROP":
        action = (
            f"Tactile forensic document stop-motion animation: This confidential forensic evidence folder ({seed_title}) "
            f"slides rapidly into frame and slams onto the dark executive boardroom table with a sharp stop-motion bounce, "
            f"settling flat with micro-vibrations and paper flutter at 12fps cadence."
        )
    elif action_type == "BIFOLD_DOSSIER_OPEN":
        action = (
            f"Tactile forensic document stop-motion animation: An official confidential docket folder ({seed_title}) "
            f"with sharp center crease smoothly opens outward flat onto the executive table in clean mechanical "
            f"12fps stop-motion steps, revealing the internal financial charts and forensic ledgers."
        )
    elif action_type == "MACRO_HIGHLIGHT_WIPE":
        if "gavel" in narration.lower() or "judge" in narration.lower():
            action = (
                "Slow cinematic camera push-in on a dark wooden judge gavel resting beside brass scales of justice "
                "on mahogany table, dramatic warm directional spotlight, subtle floating dust motes, 12fps tactile motion."
            )
        elif "gauge" in narration.lower():
            action = (
                "Tactile macro push-in on an industrial circular analog gauge labeled SOFT RESERVE FLOOR, "
                "with a brass needle rising smoothly toward red danger zone, amber backlight reflection, 12fps cadence."
            )
        elif "server" in narration.lower():
            action = (
                "Slow cinematic macro drift past high-tech server rack drive module with rhythmic blue data "
                "activity LEDs flashing in cool industrial mist, steady documentary tracking."
            )
        else:
            action = (
                f"Tactile macro camera push-in on {seed_title} resting on dark mahogany desk, "
                f"dramatic directional studio keylight, 12fps documentary tracking motion."
            )
    else:
        action = (
            f"Tactile forensic document stop-motion camera drift past {seed_title} resting on dark oak table, "
            f"subtle 12fps micro-jitter, steady documentary movement."
        )

    material = "Heavy 300gsm fibrous textured cardstock paper, crisp paper creasing, tactile contact drop shadows shifting realistically across polished wood."
    lighting = "Soft 45-degree directional evening boardroom keylight, deep contact shadows onto dark mahogany surface, subtle depth of field f/2.8."
    style = "Strictly preserve the exact 2D stylized graphic novel comic ink outlines, bold linework, crosshatching, and flat cel-shading. NO photorealism, NO live-action video, NO real people."
    dynamics = "12fps tactile stop-motion documentary motion, zero warping of text, stable mechanical transition."

    return f"{action} {material} {lighting} {style} {dynamics}"

def build_unified_director_plan(spoken_sentences: List[Dict[str, Any]], ep_dir: Path) -> Dict[str, Any]:
    """Hợp nhất B3 + B3.5: Tạo cấu trúc phân cảnh, gán 20 Veo clips Tactile Physics và Remotion Stop-Motion."""
    total_scenes = len(spoken_sentences)
    layout_zones = ["split_evidence_left", "center_hero_document", "split_evidence_right", "macro_detail_focus"]
    camera_moves = ["slow_push_in", "snap_zoom", "macro_tilt", "cinematic_pan", "slow_pull_out"]

    scenes = []
    hero_clips = []
    hero_count = 0

    for idx, sent in enumerate(spoken_sentences):
        narr = sent.get("text", "")
        dur_frames = sent.get("duration_frames", 150)
        dur_sec = sent.get("duration_sec", 5.0)
        beat_idx = int(sent.get("beat_index") or ((idx // 26) + 1))
        beat_idx = min(max(beat_idx, 1), 5)

        # Matching Background
        bg_candidates = [k for k, v in BACKGROUND_ROSTER.items() if beat_idx in v["beats"]]
        bg_key = bg_candidates[(idx // 3) % len(bg_candidates)]

        # Matching Foreground Evidence
        narr_lower = narr.lower()
        if "twenty billion" in narr_lower or "20 billion" in narr_lower:
            fg_key = "fg_evidence_20b_damage_invoice"
        elif "ftc" in narr_lower or "complaint" in narr_lower or "docket" in narr_lower:
            fg_key = "fg_evidence_ftc_complaint_docket"
        elif "sponsored" in narr_lower or "search" in narr_lower:
            fg_key = "fg_evidence_amazon_search_sponsored_box"
        elif "soft reserve" in narr_lower or "floor" in narr_lower or "80%" in narr_lower or "30%" in narr_lower:
            fg_key = "fg_evidence_soft_reserve_algorithm_gauge"
        elif "auction" in narr_lower or "second-price" in narr_lower or "bid" in narr_lower:
            fg_key = "fg_evidence_auction_bid_log_paper"
        elif "ohio" in narr_lower or "small and medium" in narr_lower or "margin" in narr_lower:
            fg_key = "fg_evidence_ohio_seller_bank_ledger"
        elif "sherman" in narr_lower or "antitrust" in narr_lower or "statute" in narr_lower:
            fg_key = "fg_evidence_antitrust_statute_book"
        elif "memo" in narr_lower or "confidential" in narr_lower:
            fg_key = "fg_evidence_sealed_memo_envelope"
        elif "revenue" in narr_lower or "68 billion" in narr_lower:
            fg_key = "fg_evidence_damages_ledger_binder"
        elif "lina khan" in narr_lower:
            fg_key = "fg_evidence_dossier_stamp_lina_khan"
        elif "jassy" in narr_lower:
            fg_key = "fg_evidence_dossier_stamp_andy_jassy"
        elif "gavel" in narr_lower or "court" in narr_lower or "judge" in narr_lower:
            fg_key = "fg_evidence_gavel_justice_scale"
        elif "algorithm" in narr_lower or "server" in narr_lower:
            fg_key = "fg_evidence_server_rack_drive"
        elif "contract" in narr_lower or "terms" in narr_lower:
            fg_key = "fg_evidence_redacted_contract_sheet"
        else:
            fg_candidates = [k for k, v in OBJECT_ROSTER.items() if beat_idx in v["beats"]]
            fg_key = fg_candidates[idx % len(fg_candidates)]

        is_hero_video = idx in HERO_SCENE_INDICES
        if is_hero_video and hero_count < 20:
            flow_slot = FLOW_ACCOUNTS[hero_count % len(FLOW_ACCOUNTS)]
            
            # Phân loại Spatial Physics Action theo 4 Chuẩn Hồ Sơ Pháp Y
            if idx in [0, 126]:
                physics_type = "MACRO_HIGHLIGHT_WIPE"
                action_type = "MACRO_HIGHLIGHT_WIPE"
                seed_mode = "CUTOUT_ONLY"
                foleys = "gavel_thud"
            elif idx in [28, 40]:
                physics_type = "MACRO_HIGHLIGHT_WIPE"
                action_type = "MACRO_HIGHLIGHT_WIPE"
                seed_mode = "CUTOUT_ONLY"
                foleys = "paper_rustle"
            elif idx % 3 == 0:
                physics_type = "CORNER_DOGEAR_PEEL"
                action_type = "CORNER_DOGEAR_PEEL"
                seed_mode = "COMPOSITE_16_9"
                foleys = "paper_page_turn"
            elif idx % 3 == 1:
                physics_type = "DOCUMENT_TABLE_DROP"
                action_type = "DOCUMENT_TABLE_DROP"
                seed_mode = "COMPOSITE_16_9"
                foleys = "document_table_thud"
            else:
                physics_type = "BIFOLD_DOSSIER_OPEN"
                action_type = "BIFOLD_DOSSIER_OPEN"
                seed_mode = "COMPOSITE_16_9"
                foleys = "paper_crease_snap"

            seed_title = OBJECT_ROSTER[fg_key]["title"] if fg_key else BACKGROUND_ROSTER[bg_key]["title"]
            veo_prompt = generate_tactile_physics_prompt(idx, narr, action_type, seed_title)
            
            shot_type = "HERO_AI_VIDEO"
            clip_entry = {
                "scene_id": f"sc{idx:03d}",
                "hero_index": hero_count + 1,
                "flow_slot": flow_slot,
                "spatial_physics_type": physics_type,
                "action_type": action_type,
                "seed_asset_mode": seed_mode,
                "bg_key": bg_key,
                "fg_key": fg_key,
                "prompt": veo_prompt,
                "duration_sec": dur_sec,
                "foleys_audio": foleys,
                "output_filename": f"hero_video_sc{idx:03d}.mp4"
            }
            hero_clips.append(clip_entry)
            hero_count += 1
        else:
            shot_type = "TACTILE_STOP_MOTION_COLLAGE"
            physics_type = "REMOTION_FORENSIC"
            flow_slot = None
            veo_prompt = None
            foleys = "stamp_impact" if ("invoice" in (fg_key or "") or "docket" in (fg_key or "")) else "paper_rustle"

        has_foreground = (shot_type == "TACTILE_STOP_MOTION_COLLAGE" and idx % 3 != 2)
        assigned_fg = fg_key if has_foreground else None

        layout_choice = layout_zones[idx % len(layout_zones)]
        cam_move = camera_moves[idx % len(camera_moves)]

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
                ["RED_YARN_CONNECTOR", "YELLOW_MARKER_STRIKE"] if "docket" in (assigned_fg or "") or "contract" in (assigned_fg or "") else
                ["RED_STAMP_SLAM", "CASE_STAMP"] if "invoice" in (assigned_fg or "") or "memo" in (assigned_fg or "") else
                ["COUNTER_ROLLUP"] if "gauge" in (assigned_fg or "") or "ledger" in (assigned_fg or "") else
                []
            )
        }

        scene_obj = {
            "scene_id": f"sc{idx:03d}",
            "beat_index": beat_idx,
            "narration": narr,
            "duration_frames": dur_frames,
            "duration_sec": dur_sec,
            "shot_type": shot_type,
            "spatial_physics_type": physics_type,
            "flow_slot": flow_slot,
            "foleys_audio": foleys,
            "veo_action_prompt": veo_prompt,
            "background": {
                "reuse_key": bg_key,
                "title": BACKGROUND_ROSTER[bg_key]["title"],
                "description": BACKGROUND_ROSTER[bg_key]["description"]
            },
            "foreground": {
                "reuse_key": assigned_fg,
                "title": OBJECT_ROSTER[assigned_fg]["title"] if assigned_fg else None,
                "description": OBJECT_ROSTER[assigned_fg]["description"] if assigned_fg else None,
                "role": OBJECT_ROSTER[assigned_fg]["role"] if assigned_fg else None,
                "position": "left" if "left" in layout_choice else ("right" if "right" in layout_choice else "center")
            } if assigned_fg else None,
            "remotion_instructions": remotion_instructions
        }
        scenes.append(scene_obj)

    return {
        "scenes": scenes,
        "hero_clips": hero_clips
    }

def main():
    parser = argparse.ArgumentParser(description="Unified VOX Director Engine (B3 + B3.5)")
    parser.add_argument("--episode", default="EN_EP0004_amazon_ad_lawsuit", help="Episode ID")
    parser.add_argument("--ep-dir", default=None, help="Explicit path to episode folder")
    args = parser.parse_args()

    ep_id = args.episode
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

    result = build_unified_director_plan(spoken_sentences, ep_dir)
    scenes = result["scenes"]
    hero_clips = result["hero_clips"]

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
    print(f"✅ Đã tạo director_plan.json ({len(scenes)} cảnh, {len(hero_clips)} Veo 3D Origami clips) -> {dp_path}")

    # 2. Lưu prompts_forge.json
    bg_prompts = {k: _sanitize_background_prompt(v["description"], bg_key=k, market="EN") for k, v in BACKGROUND_ROSTER.items()}
    fg_prompts = {k: _sanitize_foreground_prompt(v["description"], fg_key=k, market="EN") for k, v in OBJECT_ROSTER.items()}
    prompts_data = {
        "episode_id": ep_id,
        "backgrounds": bg_prompts,
        "foregrounds": fg_prompts
    }
    pf_path = ep_dir / "prompts_forge.json"
    with open(pf_path, "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã tạo prompts_forge.json ({len(bg_prompts)} BGs, {len(fg_prompts)} FGs) -> {pf_path}")

    # 3. Lưu flow_video_manifest.json (20 Hero clips cho 6 tài khoản)
    manifest_data = {
        "episode_id": ep_id,
        "total_clips": len(hero_clips),
        "clips": hero_clips
    }
    man_path = ep_dir / "flow_video_manifest.json"
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã tạo flow_video_manifest.json ({len(hero_clips)} clips phân bổ 6 tài khoản) -> {man_path}")

    print("\n" + "=" * 70)
    print("📊 BẢO CHỨNG PHÂN BỔ 20 CLIPS VEO CHO 6 TÀI KHOẢN GOOGLE FLOW:")
    print("=" * 70)
    acc_distribution = {}
    for c in hero_clips:
        slot = c["flow_slot"]
        acc_distribution[slot] = acc_distribution.get(slot, 0) + 1
    for slot, count in sorted(acc_distribution.items()):
        print(f"• {slot}: {count} clips")

if __name__ == "__main__":
    main()
