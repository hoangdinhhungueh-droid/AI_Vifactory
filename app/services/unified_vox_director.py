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
import yaml
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
    """Tạo mô tả hành động xúc giác ngắn gọn cho VEO physics prompt."""
    if action_type == "CORNER_DOGEAR_PEEL":
        return f"top sheet dog-ear corner curls back organically in crisp 12fps mechanical steps, lifting upward to reveal confidential audit docket beneath"
    elif action_type == "DOCUMENT_TABLE_DROP":
        return f"confidential forensic evidence folder ({seed_title}) slides rapidly into frame and slams onto executive table with a sharp stop-motion bounce, settling flat with paper flutter"
    elif action_type == "BIFOLD_DOSSIER_OPEN":
        return f"official confidential docket folder ({seed_title}) with sharp center crease opens outward flat onto table in clean mechanical 12fps steps, revealing internal financial charts"
    elif action_type == "MACRO_HIGHLIGHT_WIPE":
        n_low = narration.lower()
        if "gavel" in n_low or "judge" in n_low:
            return f"dark wooden judge gavel resting beside brass scales of justice on mahogany table under dramatic directional spotlight with subtle dust motes and micro-vibrations"
        elif "gauge" in n_low:
            return f"industrial circular analog gauge needle rising smoothly toward red danger zone with amber reflection"
        elif "server" in n_low:
            return f"high-tech enterprise server rack drive module with rhythmic blue data activity LEDs flashing in cool mist"
        else:
            return f"{seed_title} resting on dark mahogany desk under dramatic directional studio keylight with 12fps documentary tracking motion"
    else:
        return f"{seed_title} resting on table with subtle 12fps micro-jitter in steady documentary tracking"

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

def build_unified_director_plan(
    spoken_sentences: List[Dict[str, Any]],
    ep_dir: Path,
    style_preset: Optional[str] = None
) -> Dict[str, Any]:
    """Hợp nhất B3 + B3.5: Tạo cấu trúc phân cảnh, gán 20 Veo clips Tactile Physics và Remotion Stop-Motion."""
    preset = load_style_config(style_preset)
    allowed_cameras = preset.get("camera_defaults", {}).get("allowed", [
        "static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"
    ])
    layout_zones = ["split_evidence_left", "center_hero_document", "split_evidence_right", "macro_detail_focus"]

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

        cam_move = allowed_cameras[idx % len(allowed_cameras)]
        layout_choice = layout_zones[idx % len(layout_zones)]
        transition_choice = "stop_motion_flicker_cut" if idx % 2 == 1 else "hard_cut"

        seed_title = OBJECT_ROSTER[fg_key]["title"] if fg_key else BACKGROUND_ROSTER[bg_key]["title"]
        setting_desc = BACKGROUND_ROSTER[bg_key]["title"]

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
            foleys = "stamp_impact" if ("invoice" in (fg_key or "") or "docket" in (fg_key or "")) else "paper_rustle"
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
                ["RED_YARN_CONNECTOR", "YELLOW_MARKER_STRIKE"] if "docket" in (assigned_fg or "") or "contract" in (assigned_fg or "") else
                ["RED_STAMP_SLAM", "CASE_STAMP"] if "invoice" in (assigned_fg or "") or "memo" in (assigned_fg or "") else
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
    parser.add_argument("--style-preset", default="vox_forensic_paper", help="Style preset from style-config.yaml")
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

    result = build_unified_director_plan(spoken_sentences, ep_dir, style_preset=args.style_preset)
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
