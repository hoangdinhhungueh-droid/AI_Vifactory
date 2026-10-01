import json, os

ep_id = "EN_EP0006_foreign_capital_us_stocks"
out_path = f"/root/video_factory/workspace/{ep_id}/demo_vox_kinetics_props.json"
public_out = f"/root/video_factory/remotion/public/props/{ep_id}_demo.json"

props = {
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "audio_path": f"/var/vf/episodes/{ep_id}/audio_norm.mp3",
    "bgm_path": f"/var/vf/episodes/{ep_id}/bgm_master.mp3",
    "scenes": [
        {
            "scene_id": "sc000",
            "durationInFrames": 150,
            "background": f"pulled/{ep_id}/bg_wall_street_opening_bell.png",
            "foreground": None,
            "headline": "THE $942 BILLION ILLUSION",
            "highlightWord": "ILLUSION",
            "category": "FORENSIC INVESTIGATION // GLOBAL FLOW ARCHITECTURE",
            "subtext": "Why Record Foreign Inflows Conceal a Dangerous Structural Exit",
            "accent_color": "#f59e0b",
            "caption": "In the summer of 2026, foreign investors pumped a historic nine hundred and forty-two billion dollars into the United States.",
            "narration": "In the summer of 2026, foreign investors pumped a historic nine hundred and forty-two billion dollars into the United States.",
            "cameraMovement": "slow_push_in",
            "tensionLevel": "high",
            "speakerTag": "BEAT 1: THE INFLOW ILLUSION",
            "forensicOverlay": {
                "type": "kinetic_headline",
                "title": "THE $942 BILLION ILLUSION",
                "badge": "FORENSIC INVESTIGATION",
                "layout": "full_bleed_focus",
                "payload": {
                    "highlight_word": "ILLUSION",
                    "subtext": "Why Record Foreign Inflows Conceal a Dangerous Structural Exit",
                    "accent_color": "#f59e0b"
                }
            }
        },
        {
            "scene_id": "sc001",
            "durationInFrames": 390,
            "background": f"pulled/{ep_id}/bg_record_inflow_dashboard.png",
            "foreground": None,
            "caption": "Capital flooded into mega-cap equities, while quietly abandoning the thirty-five trillion dollar Treasury debt foundation.",
            "narration": "Capital flooded into mega-cap equities, while quietly abandoning the thirty-five trillion dollar Treasury debt foundation.",
            "cameraMovement": "continuous_drift",
            "tensionLevel": "high",
            "speakerTag": "BEAT 1: CAUSAL TRANSMISSION",
            "forensicOverlay": {
                "type": "connected_network",
                "title": "SYSTEMIC CAPITAL TRANSMISSION // FORENSIC VECTOR MAP",
                "badge": "TIC FLOW AUDIT",
                "layout": "full_bleed_focus",
                "payload": {
                    "nodes": [
                        {
                            "id": "foreign_fund",
                            "label": "Foreign Institutional Allocators",
                            "subtext": "Tokyo, London & Zurich Outposts",
                            "image_src": f"pulled/{ep_id}/fg_character_foreign_portfolio_manager.png",
                            "x_pct": 20,
                            "y_pct": 35,
                            "enter_frame": 10,
                            "theme": "cyan",
                            "badge": "CAPITAL SOURCE"
                        },
                        {
                            "id": "us_equities",
                            "label": "US Tech & Mega-Cap Equities",
                            "subtext": "Top 7 Balance Sheets Concentration",
                            "image_src": f"pulled/{ep_id}/fg_evidence_capital_inflow_1_2t.png",
                            "x_pct": 80,
                            "y_pct": 32,
                            "enter_frame": 35,
                            "theme": "gold",
                            "badge": "SURGE TARGET"
                        },
                        {
                            "id": "treasury_debt",
                            "label": "US Treasury Liquidity Choke",
                            "subtext": "Foreign Debt Absorption Halved to $188B",
                            "image_src": f"pulled/{ep_id}/fg_evidence_treasury_bond_stack.png",
                            "x_pct": 50,
                            "y_pct": 78,
                            "enter_frame": 80,
                            "theme": "danger",
                            "badge": "SYSTEMIC CHOKE"
                        }
                    ],
                    "edges": [
                        {
                            "from": "foreign_fund",
                            "to": "us_equities",
                            "label": "+$942B CAPITAL FLIGHT",
                            "start_frame": 42,
                            "duration_frames": 26,
                            "color": "#38bdf8",
                            "curve_offset": -40,
                            "pulse": True
                        },
                        {
                            "from": "foreign_fund",
                            "to": "treasury_debt",
                            "label": "DEBT RETREAT (-48%)",
                            "start_frame": 88,
                            "duration_frames": 24,
                            "color": "#ef4444",
                            "curve_offset": 35,
                            "pulse": True
                        },
                        {
                            "from": "us_equities",
                            "to": "treasury_debt",
                            "label": "COLLATERAL DRAIN",
                            "start_frame": 130,
                            "duration_frames": 22,
                            "color": "#f59e0b",
                            "curve_offset": -30,
                            "pulse": True
                        }
                    ]
                }
            }
        },
        {
            "scene_id": "sc002",
            "durationInFrames": 300,
            "background": f"pulled/{ep_id}/bg_treasury_equity_divide.png",
            "foreground": None,
            "caption": "Treasury International Capital reports confirm foreign buyers took down just one hundred and eighty-eight billion in debt.",
            "narration": "Treasury International Capital reports confirm foreign buyers took down just one hundred and eighty-eight billion in debt.",
            "cameraMovement": "slow_pull_out",
            "tensionLevel": "medium",
            "speakerTag": "BEAT 2: THE PAPER TRAIL",
            "forensicOverlay": {
                "type": "paper_dossier",
                "title": "DEPARTMENT OF THE TREASURY // TIC RECORD INFLOW REPORT",
                "badge": "FORENSIC EVIDENCE",
                "layout": "full_bleed_focus",
                "payload": {
                    "document_number": "TIC-AUDIT-2026-Q2",
                    "date": "JULY 2026",
                    "agency": "U.S. DEPARTMENT OF THE TREASURY // FEDERAL RESERVE BOARD",
                    "highlighted_phrase": "FOREIGN DEBT DEMAND FELL FROM $314B TO $188B",
                    "stamp_text": "VERIFIED CONFLICT"
                }
            },
            "linked_secondary_objects": [
                {
                    "id": "stamp_1",
                    "type": "stamp",
                    "label": "PRICE_FRAUD",
                    "slam_frame": 24,
                    "x_pct": 68,
                    "y_pct": 45,
                    "theme": "danger",
                    "rot_deg": -5.5
                },
                {
                    "id": "marker_1",
                    "type": "marker_sweep",
                    "sweep_start_frame": 12,
                    "sweep_duration_frames": 18,
                    "color": "#ffe600"
                }
            ]
        },
        {
            "scene_id": "sc003",
            "durationInFrames": 270,
            "background": f"pulled/{ep_id}/bg_split_market_ticker.png",
            "foreground": None,
            "caption": "While headlines celebrated nine hundred and forty-two billion in equities, the underlying mechanism was fracture, not strength.",
            "narration": "While headlines celebrated nine hundred and forty-two billion in equities, the underlying mechanism was fracture, not strength.",
            "cameraMovement": "snap_zoom",
            "tensionLevel": "climax",
            "speakerTag": "BEAT 3: THE CONCENTRATION TRAP",
            "forensicOverlay": {
                "type": "kinetic_counter",
                "title": "NET FOREIGN CAPITAL CONCENTRATION // S&P 500",
                "badge": "RECORD METRIC",
                "layout": "full_bleed_focus",
                "payload": {
                    "start_value": 0,
                    "end_value": 942,
                    "amount": 942,
                    "prefix": "$",
                    "unit": "B",
                    "label": "CONCENTRATED CAPITAL SURGE",
                    "trend": "up"
                }
            }
        }
    ]
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(props, f, indent=2, ensure_ascii=False)

os.makedirs(os.path.dirname(public_out), exist_ok=True)
with open(public_out, "w", encoding="utf-8") as f:
    json.dump(props, f, indent=2, ensure_ascii=False)

total_f = sum(s["durationInFrames"] for s in props["scenes"])
print(f"Generated {out_path} and {public_out}: {len(props['scenes'])} scenes, {total_f} frames ({total_f/30:.1f}s)")
