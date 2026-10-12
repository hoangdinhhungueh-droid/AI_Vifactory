# scripts/generate_kr0001_pilot_props.py
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

def generate_pilot_props(output_path: Path) -> dict:
    ep_slug = "KR_EP0001_spacex_ai_credit_risk"
    asset_prefix = f"pulled/{ep_slug}"

    scenes = [
        # Scene 1: 0.00s - 3.30s (99 frames)
        {
            "id": "pilot_shot_01",
            "durationInFrames": 99,
            "durationSec": 3.30,
            "headline": "2026년 10월 // STARBASE RECORD",
            "subtitle": "2026년 10월 7일과 8일",
            "narration": "2026년 10월 7일과 8일,",
            "theme": "newsprint-editorial",
            "layoutVariant": "paper_collage",
            "background": None,
            "foreground": f"{asset_prefix}/fg_evidence_spcx_stock_ticker_strip.png",
            "heroSrc": f"{asset_prefix}/fg_evidence_spcx_stock_ticker_strip.png",
            "heroLabel": "SPACEX FINANCIAL MONITOR",
            "heroPosition": {
                "xPct": 34,
                "yPct": 54,
                "widthPct": 22
            },
            "supportingCutouts": [
                {
                    "id": "cutout_s0_1",
                    "src": f"{asset_prefix}/fg_evidence_40b_financing_term_sheet.png",
                    "label": "0B FINANCING TERM SHEET",
                    "xPct": 70,
                    "yPct": 46,
                    "widthPct": 16,
                    "rotation": -6,
                    "delaySec": 0.5,
                    "hasPin": True,
                    "hasTape": False,
                    "entranceType": "slide_in_deal",
                    "hasMarkerHighlight": True,
                    "highlightText": "OCT 2026 // 0B LEAK"
                },
                {
                    "id": "cutout_s0_2",
                    "src": f"{asset_prefix}/fg_evidence_senior_unsecured_notes_indenture.png",
                    "label": "NOTES INDENTURE LEAK",
                    "xPct": 84,
                    "yPct": 65,
                    "widthPct": 15,
                    "rotation": 8,
                    "delaySec": 1.1,
                    "hasPin": False,
                    "hasTape": True,
                    "entranceType": "delicate_tack",
                    "hasMarkerHighlight": False,
                    "highlightText": "INDENTURE NOTES"
                }
            ],
            "yarns": [
                {
                    "fromX": 34,
                    "fromY": 54,
                    "toX": 70,
                    "toY": 46,
                    "color": "#dc2626",
                    "delaySec": 1.4
                }
            ],
            "cameraMovement": "slow_push_in",
            "stampText": "STARBASE // RECORD",
            "stampColor": "#dc2626",
            "hasMarkerHighlight": True,
            "words": ["2026년", "10월", "7일과", "8일,"]
        },

        # Scene 2: 3.30s - 10.90s (228 frames)
        {
            "id": "pilot_shot_02",
            "durationInFrames": 228,
            "durationSec": 7.60,
            "headline": "NVIDIA AI CHIP // 0B PROCUREMENT",
            "subtitle": "AI INFRASTRUCTURE EXPANSION",
            "narration": "스페이스X가 엔비디아 AI 칩 구매를 위해 약 400억달러를 조달할 수 있다는 보도가 나왔습니다.",
            "theme": "newsprint-editorial",
            "layoutVariant": "evidence_dossier",
            "background": None,
            "foreground": f"{asset_prefix}/fg_evidence_nvidia_gpu_server_tray.png",
            "heroSrc": f"{asset_prefix}/fg_evidence_nvidia_gpu_server_tray.png",
            "heroLabel": "NVIDIA H200 / B200 SERVER TRAY",
            "heroPosition": {
                "xPct": 32,
                "yPct": 54,
                "widthPct": 22
            },
            "supportingCutouts": [
                {
                    "id": "cutout_s1_1",
                    "src": f"{asset_prefix}/fg_evidence_40b_financing_term_sheet.png",
                    "label": "400억달러 조달 계약서",
                    "xPct": 68,
                    "yPct": 44,
                    "widthPct": 17,
                    "rotation": 5,
                    "delaySec": 0.8,
                    "hasPin": True,
                    "hasTape": False,
                    "entranceType": "slide_in_deal",
                    "hasMarkerHighlight": True,
                    "highlightText": "400억달러 // 조달 계약"
                },
                {
                    "id": "cutout_s1_2",
                    "src": f"{asset_prefix}/fg_character_bond_portfolio_manager.png",
                    "label": "SYNDICATE DESK MANAGER",
                    "xPct": 83,
                    "yPct": 66,
                    "widthPct": 15,
                    "rotation": -4,
                    "delaySec": 1.6,
                    "hasPin": False,
                    "hasTape": True,
                    "entranceType": "delicate_tack",
                    "hasMarkerHighlight": False,
                    "highlightText": "SYNDICATE DESK"
                }
            ],
            "yarns": [
                {
                    "fromX": 32,
                    "fromY": 54,
                    "toX": 68,
                    "toY": 44,
                    "color": "#dc2626",
                    "delaySec": 2.2
                }
            ],
            "cameraMovement": "slow_pull_out",
            "stampText": "CONFIDENTIAL // 40B",
            "stampColor": "#dc2626",
            "hasMarkerHighlight": True,
            "words": [
                "스페이스X가", "엔비디아", "AI", "칩", "구매를",
                "위해", "약", "400억달러를", "조달할", "수",
                "있다는", "보도가", "나왔습니다."
            ]
        },

        # Scene 3: 10.90s - 17.13s (187 frames)
        {
            "id": "pilot_shot_03",
            "durationInFrames": 187,
            "durationSec": 6.23,
            "headline": "MEDIA CONSORTIUM // SIMULTANEOUS LEAK",
            "subtitle": "FT • BLOOMBERG • REUTERS",
            "narration": "파이낸셜타임스와 블룸버그, 로이터가 거의 동시에 같은 거래를 전했습니다.",
            "theme": "newsprint-editorial",
            "layoutVariant": "paper_collage",
            "background": None,
            "foreground": f"{asset_prefix}/fg_evidence_affiliate_contract_exhibit.png",
            "heroSrc": f"{asset_prefix}/fg_evidence_affiliate_contract_exhibit.png",
            "heroLabel": "AFFILIATE TRANSACTION RECORD",
            "heroPosition": {
                "xPct": 34,
                "yPct": 54,
                "widthPct": 21
            },
            "supportingCutouts": [
                {
                    "id": "cutout_s2_1",
                    "src": f"{asset_prefix}/fg_character_filing_researcher.png",
                    "label": "FORENSIC FILING RESEARCH",
                    "xPct": 68,
                    "yPct": 44,
                    "widthPct": 16,
                    "rotation": -7,
                    "delaySec": 0.6,
                    "hasPin": True,
                    "hasTape": False,
                    "entranceType": "slide_in_deal",
                    "hasMarkerHighlight": True,
                    "highlightText": "SIMULTANEOUS LEAK"
                },
                {
                    "id": "cutout_s2_2",
                    "src": f"{asset_prefix}/fg_evidence_senior_unsecured_notes_indenture.png",
                    "label": "CROSS-DEFAULT INDENTURE",
                    "xPct": 83,
                    "yPct": 65,
                    "widthPct": 15,
                    "rotation": 6,
                    "delaySec": 1.4,
                    "hasPin": False,
                    "hasTape": True,
                    "entranceType": "stamp_slam",
                    "hasMarkerHighlight": False,
                    "highlightText": "CROSS-DEFAULT"
                }
            ],
            "yarns": [
                {
                    "fromX": 34,
                    "fromY": 54,
                    "toX": 68,
                    "toY": 44,
                    "color": "#dc2626",
                    "delaySec": 1.8
                }
            ],
            "cameraMovement": "slow_push_in",
            "stampText": "PRESS LEAK // TRIO",
            "stampColor": "#b91c1c",
            "hasMarkerHighlight": True,
            "words": [
                "파이낸셜타임스와", "블룸버그,", "로이터가", "거의",
                "동시에", "같은", "거래를", "전했습니다."
            ]
        },

        # Scene 4: 17.13s - 21.50s (131 frames)
        {
            "id": "pilot_shot_04",
            "durationInFrames": 131,
            "durationSec": 4.37,
            "headline": "CREDIT DEFAULT SWAP // 5-YEAR SPREAD",
            "subtitle": "SPACEX 5Y CDS CONTRACT",
            "narration": "바로 그 시점에 스페이스X의 5년물 CDS,",
            "theme": "newsprint-editorial",
            "layoutVariant": "kinetic_headline",
            "background": None,
            "foreground": f"{asset_prefix}/fg_evidence_cds_trade_confirmation.png",
            "heroSrc": f"{asset_prefix}/fg_evidence_cds_trade_confirmation.png",
            "heroLabel": "5Y CDS TRADE CONFIRMATION",
            "heroPosition": {
                "xPct": 32,
                "yPct": 54,
                "widthPct": 22
            },
            "supportingCutouts": [
                {
                    "id": "cutout_s3_1",
                    "src": f"{asset_prefix}/fg_character_cds_trader.png",
                    "label": "CREDIT RISK DESK",
                    "xPct": 74,
                    "yPct": 50,
                    "widthPct": 16,
                    "rotation": 4,
                    "delaySec": 0.5,
                    "hasPin": True,
                    "hasTape": False,
                    "entranceType": "slide_in_deal",
                    "hasMarkerHighlight": True,
                    "highlightText": "5-YEAR CDS SPREAD"
                }
            ],
            "yarns": [
                {
                    "fromX": 32,
                    "fromY": 54,
                    "toX": 74,
                    "toY": 50,
                    "color": "#dc2626",
                    "delaySec": 1.1
                }
            ],
            "cameraMovement": "slow_push_in",
            "stampText": "MARK-TO-MARKET",
            "stampColor": "#dc2626",
            "hasMarkerHighlight": True,
            "words": [
                "바로", "그", "시점에", "스페이스X의", "5년물", "CDS,"
            ]
        },

        # Scene 5: 21.50s - 27.16s (170 frames)
        {
            "id": "pilot_shot_05",
            "durationInFrames": 170,
            "durationSec": 5.67,
            "headline": "INSURANCE SURGE // 197.3 BASIS POINTS",
            "subtitle": "DEFAULT RISK SPREAD SPIKE",
            "narration": "즉 부도위험 보험료는 약 197.3bp까지 치솟았습니다.",
            "theme": "newsprint-editorial",
            "layoutVariant": "paper_collage",
            "background": None,
            "foreground": f"{asset_prefix}/fg_evidence_cds_spread_chart_197bp.png",
            "heroSrc": f"{asset_prefix}/fg_evidence_cds_spread_chart_197bp.png",
            "heroLabel": "CDS SPREAD SURGE // 197.3 BP",
            "heroPosition": {
                "xPct": 34,
                "yPct": 54,
                "widthPct": 22
            },
            "supportingCutouts": [
                {
                    "id": "cutout_s4_1",
                    "src": f"{asset_prefix}/fg_evidence_cds_premium_calculator_card.png",
                    "label": "PREMIUM CALCULATOR CARD",
                    "xPct": 69,
                    "yPct": 45,
                    "widthPct": 17,
                    "rotation": -8,
                    "delaySec": 0.6,
                    "hasPin": True,
                    "hasTape": False,
                    "entranceType": "slide_in_deal",
                    "hasMarkerHighlight": True,
                    "highlightText": "197.3bp 치솟음"
                },
                {
                    "id": "cutout_s4_2",
                    "src": f"{asset_prefix}/fg_evidence_credit_rating_letters_trio.png",
                    "label": "RATING AGENCY ALERT",
                    "xPct": 83,
                    "yPct": 65,
                    "widthPct": 15,
                    "rotation": 7,
                    "delaySec": 1.3,
                    "hasPin": False,
                    "hasTape": True,
                    "entranceType": "stamp_slam",
                    "hasMarkerHighlight": False,
                    "highlightText": "CREDIT WATCH"
                }
            ],
            "yarns": [
                {
                    "fromX": 34,
                    "fromY": 54,
                    "toX": 69,
                    "toY": 45,
                    "color": "#dc2626",
                    "delaySec": 1.7
                }
            ],
            "cameraMovement": "slow_push_in",
            "stampText": "CRITICAL // 197.3 BP",
            "stampColor": "#dc2626",
            "hasMarkerHighlight": True,
            "words": [
                "즉", "부도위험", "보험료는", "약", "197.3bp까지", "치솟았습니다."
            ]
        },

        # Scene 6: 27.16s - 30.00s (85 frames)
        {
            "id": "pilot_shot_06",
            "durationInFrames": 85,
            "durationSec": 2.83,
            "headline": "ALL-TIME HIGH // HISTORIC APEX",
            "subtitle": "RECORD SPREAD EXPANSION",
            "narration": "사상 최고치였습니다.",
            "theme": "newsprint-editorial",
            "layoutVariant": "paper_collage",
            "background": None,
            "foreground": f"{asset_prefix}/fg_evidence_14_percent_callout_gauge.png",
            "heroSrc": f"{asset_prefix}/fg_evidence_14_percent_callout_gauge.png",
            "heroLabel": "ALL-TIME HIGH VOLATILITY GAUGE",
            "heroPosition": {
                "xPct": 34,
                "yPct": 54,
                "widthPct": 21
            },
            "supportingCutouts": [
                {
                    "id": "cutout_s5_1",
                    "src": f"{asset_prefix}/fg_evidence_spread_vs_junk_chart.png",
                    "label": "HISTORICAL SPREAD COMPARISON",
                    "xPct": 70,
                    "yPct": 46,
                    "widthPct": 16,
                    "rotation": -5,
                    "delaySec": 0.4,
                    "hasPin": True,
                    "hasTape": False,
                    "entranceType": "slide_in_deal",
                    "hasMarkerHighlight": True,
                    "highlightText": "사상 최고치 경신"
                },
                {
                    "id": "cutout_s5_2",
                    "src": f"{asset_prefix}/fg_character_credit_rating_analyst.png",
                    "label": "CREDIT ANALYST RECON",
                    "xPct": 84,
                    "yPct": 66,
                    "widthPct": 15,
                    "rotation": 8,
                    "delaySec": 0.9,
                    "hasPin": False,
                    "hasTape": True,
                    "entranceType": "delicate_tack",
                    "hasMarkerHighlight": False,
                    "highlightText": "ANALYST CONSENSUS"
                }
            ],
            "yarns": [
                {
                    "fromX": 34,
                    "fromY": 54,
                    "toX": 70,
                    "toY": 46,
                    "color": "#dc2626",
                    "delaySec": 1.2
                }
            ],
            "cameraMovement": "slow_push_in",
            "stampText": "RECORD APEX",
            "stampColor": "#dc2626",
            "hasMarkerHighlight": True,
            "words": [
                "사상", "최고치였습니다."
            ]
        }
    ]

    total_frames = sum(s["durationInFrames"] for s in scenes)

    payload = {
        "episodeId": ep_slug,
        "topic": "스페이스X 부도위험 보험료 400억달러…엔비디아 칩 조달의 진짜 위험",
        "theme": "newsprint-editorial",
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "totalFrames": total_frames,
        "audioMaster": f"{asset_prefix}/tts_out.mp3",
        "bgmFile": "bgm/vox_cinematic_pulse.mp3",
        "bgmVolume": 0.12,
        "includeAudio": True,
        "scenes": scenes,
        "meta": {
            "version": "vox_master_prompt_2_upgraded",
            "targetPilotSeconds": 30.0,
            "canvasBackground": "#f4ece1",
            "heroProportions": "21-22%",
            "supportingExhibitProportions": "14-17%",
            "entranceChoreography": ["slide_in_deal", "delicate_tack", "stamp_slam"],
            "highlighterSweep": "ProceduralMarkerSweep #ffe600",
            "tactileProps": ["VoxBrassPin", "VoxWashiTape", "VoxConnectingYarn", "RubberStamp"]
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Generated upgraded pilot props: {output_path} ({total_frames} frames, {total_frames/30:.2f}s)")
    return payload

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/video_factory/episodes/KR_EP0001_spacex_ai_credit_risk/pilot_props_30s.json")
    generate_pilot_props(out)
