#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/rebuild_en0004_director_plan.py
Rebuilds B3 Director Plan and B3.5 Prompts for EN_EP0004_amazon_ad_lawsuit
with 100% Tangible Evidence Objects (Zero Generic Cartoon Humans)
and Continuous Kinetic Montage pacing (~55-65 scenes with dynamic overlays).
"""

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import _sanitize_foreground_prompt, _sanitize_background_prompt

EPISODE_ID = "EN_EP0004_amazon_ad_lawsuit"

# 1. Curated 14 Tangible Evidence Objects Roster
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

# 2. Curated 8 Uncluttered Context-Rich Backgrounds Roster
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


def main():
    print(f"🚀 Rebuilding B3 Director Plan & B3.5 Prompts for {EPISODE_ID}...")
    ep_dir = Path(f"/var/vf/episodes/{EPISODE_ID}")
    if not ep_dir.exists():
        # Fallback to local
        ep_dir = ROOT_DIR / "archive" / EPISODE_ID
    
    # Load spoken_sentences
    spoken_file = Path(f"/var/vf/episodes/{EPISODE_ID}/spoken_sentences.json")
    if not spoken_file.exists():
        print(f"❌ Spoken sentences not found at {spoken_file}")
        sys.exit(1)

    with open(spoken_file, "r", encoding="utf-8") as f:
        spoken_sentences = json.load(f)

    total_scenes = len(spoken_sentences)
    print(f"📊 Total spoken sentences: {total_scenes}")

    # Build 131 scenes with object-first assignment & continuous kinetic montage
    bg_keys = list(BACKGROUND_ROSTER.keys())
    fg_keys = list(OBJECT_ROSTER.keys())
    layout_zones = ["split_evidence_left", "center_hero_document", "split_evidence_right", "macro_detail_focus"]
    camera_moves = ["slow_push_in", "snap_zoom", "macro_tilt", "cinematic_pan", "slow_pull_out"]

    scenes = []
    
    for idx, sent in enumerate(spoken_sentences):
        narr = sent.get("text", "")
        dur_frames = sent.get("duration_frames", 150)
        dur_sec = sent.get("duration_sec", 5.0)
        beat_idx = int(sent.get("beat_index") or ((idx // 26) + 1))
        beat_idx = min(max(beat_idx, 1), 5)

        # Assign Background matching Beat
        bg_candidates = [k for k, v in BACKGROUND_ROSTER.items() if beat_idx in v["beats"]]
        bg_key = bg_candidates[(idx // 3) % len(bg_candidates)]

        # Assign Foreground matching Beat
        fg_candidates = [k for k, v in OBJECT_ROSTER.items() if beat_idx in v["beats"]]
        
        # Specific semantic keyword matching for maximum relevance
        narr_lower = narr.lower()
        if "twenty billion" in narr_lower or "20 billion" in narr_lower or "extract" in narr_lower:
            fg_key = "fg_evidence_20b_damage_invoice"
        elif "federal trade commission" in narr_lower or "ftc" in narr_lower or "complaint" in narr_lower or "docket" in narr_lower:
            fg_key = "fg_evidence_ftc_complaint_docket"
        elif "sponsored products" in narr_lower or "sponsored" in narr_lower or "search" in narr_lower or "visibility" in narr_lower:
            fg_key = "fg_evidence_amazon_search_sponsored_box"
        elif "soft reserve" in narr_lower or "floor" in narr_lower or "80%" in narr_lower or "30%" in narr_lower or "seventy percent" in narr_lower:
            fg_key = "fg_evidence_soft_reserve_algorithm_gauge"
        elif "auction" in narr_lower or "second-price" in narr_lower or "bid" in narr_lower:
            fg_key = "fg_evidence_auction_bid_log_paper"
        elif "ohio" in narr_lower or "small and medium" in narr_lower or "margin" in narr_lower or "mortgage" in narr_lower:
            fg_key = "fg_evidence_ohio_seller_bank_ledger"
        elif "sherman" in narr_lower or "antitrust" in narr_lower or "statute" in narr_lower or "illegal" in narr_lower:
            fg_key = "fg_evidence_antitrust_statute_book"
        elif "memo" in narr_lower or "confidential" in narr_lower or "secret" in narr_lower:
            fg_key = "fg_evidence_sealed_memo_envelope"
        elif "revenue" in narr_lower or "68 billion" in narr_lower or "14 billion" in narr_lower:
            fg_key = "fg_evidence_damages_ledger_binder"
        elif "lina khan" in narr_lower or "chair" in narr_lower:
            fg_key = "fg_evidence_dossier_stamp_lina_khan"
        elif "jassy" in narr_lower or "andy" in narr_lower or "executive" in narr_lower:
            fg_key = "fg_evidence_dossier_stamp_andy_jassy"
        elif "gavel" in narr_lower or "court" in narr_lower or "judge" in narr_lower or "verdict" in narr_lower:
            fg_key = "fg_evidence_gavel_justice_scale"
        elif "algorithm" in narr_lower or "server" in narr_lower or "data" in narr_lower or "code" in narr_lower:
            fg_key = "fg_evidence_server_rack_drive"
        elif "contract" in narr_lower or "terms" in narr_lower or "fine print" in narr_lower:
            fg_key = "fg_evidence_redacted_contract_sheet"
        else:
            # Cyclic assignment within candidates
            fg_key = fg_candidates[idx % len(fg_candidates)]

        # Continuous Kinetic Montage: Give breathing room every 3rd scene
        has_foreground = (idx % 3 != 2)
        assigned_fg = fg_key if has_foreground else None

        layout_zone_choice = layout_zones[idx % len(layout_zones)]
        cam_move = camera_moves[idx % len(camera_moves)]

        # Animation Cues tied to words in narration
        words_in_narr = [w.strip(".,!?:;\"'") for w in narr.split() if len(w.strip(".,!?:;\"'")) >= 4]
        trigger_word = words_in_narr[min(2, len(words_in_narr)-1)] if words_in_narr else ""
        
        anim_effect = (
            "yellow_marker_highlight" if "docket" in fg_key or "contract" in fg_key else
            "red_stamp_slam" if "invoice" in fg_key or "stamp" in fg_key or "memo" in fg_key else
            "counter_rollup" if "gauge" in fg_key or "ledger" in fg_key else
            "flowchart_arrow_grow"
        )

        sc = {
            "scene_id": f"sc{idx:03d}",
            "beat_index": beat_idx,
            "narration": narr,
            "duration_frames": dur_frames,
            "duration_sec": dur_sec,
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
                "position": "left" if "left" in layout_zone_choice else ("right" if "right" in layout_zone_choice else "center")
            } if assigned_fg else None,
            "layout_zone": {
                "placement": layout_zone_choice,
                "safe_zone": "bottom_left" if "left" in layout_zone_choice else "bottom_right",
                "camera_pan_axis": "horizontal" if idx % 2 == 0 else "vertical"
            },
            "camera": {
                "movement": cam_move
            },
            "animation_cue": {
                "effect": anim_effect,
                "trigger_word": trigger_word,
                "duration_frames": 24
            } if has_foreground and trigger_word else None,
            "motion_directive": "dramatic_push" if idx < 15 else ("split_whip" if idx % 3 == 0 else "subtle_drift")
        }
        scenes.append(sc)

    dp_data = {
        "episode_id": EPISODE_ID,
        "scenes": scenes
    }

    dp_out_path = ep_dir / "director_plan.json"
    with open(dp_out_path, "w", encoding="utf-8") as f:
        json.dump(dp_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved new Object-Driven director_plan.json ({len(scenes)} scenes) -> {dp_out_path}")

    # Build Prompts Forge
    bg_prompts = {}
    for k, v in BACKGROUND_ROSTER.items():
        bg_prompts[k] = _sanitize_background_prompt(v["description"], bg_key=k, market="EN")

    fg_prompts = {}
    for k, v in OBJECT_ROSTER.items():
        fg_prompts[k] = _sanitize_foreground_prompt(v["description"], fg_key=k, market="EN")

    prompts_data = {
        "episode_id": EPISODE_ID,
        "backgrounds": bg_prompts,
        "foregrounds": fg_prompts
    }

    pf_out_path = ep_dir / "prompts_forge.json"
    with open(pf_out_path, "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved new prompts_forge.json ({len(bg_prompts)} BGs, {len(fg_prompts)} FGs) -> {pf_out_path}")

    # Also save prompts.json mirror
    with open(ep_dir / "prompts.json", "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
