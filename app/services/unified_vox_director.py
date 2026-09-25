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
import logging
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import _sanitize_foreground_prompt, _sanitize_background_prompt
from app.services.sfx_registry import (
    CANONICAL_SFX_REGISTRY,
    get_canonical_sfx_list,
    is_valid_sfx,
    resolve_semantic_foley
)

FLOW_ACCOUNTS = ["acc_01", "acc_02", "acc_03", "acc_04", "acc_05", "acc_06"]

# ============================================================================
# DYNAMIC VISUAL ROSTER GENERATOR (RULE 128 - ZERO SEMANTIC BIAS)
# ============================================================================

def _generate_topic_anchored_roster_fallback(
    topic: str,
    market: str,
    key_metrics: list,
    claims: list
) -> tuple:
    """Rule 128: Topic-Anchored Deterministic Visual Roster Fallback (16-18 BGs & 20-24 FGs).
    Generates rich, fully differentiated environmental BGs and tactile evidentiary FGs tailored
    to the target market (JP, KR, VN, EN) and narrative domain (Financial/Debt, Tech/Antitrust, Corporate Scandal).
    Guarantees zero photorealism, strict 2D stylized graphic novel aesthetic, and zero empty scenes.
    """
    m_up = str(market or "EN").upper().strip()
    topic_low = (topic or "").lower()
    if key_metrics:
        metric_highlight = key_metrics[0]
    elif m_up in ["JP", "JA"]:
        metric_highlight = "定量監査データ // 検証記録"
    elif m_up in ["KR", "KO"]:
        metric_highlight = "정량감사데이터 // 검증기록"
    elif m_up in ["VN", "VI"]:
        metric_highlight = "SỐ LIỆU ĐỊNH LƯỢNG // HỒ SƠ PHÁP Y"
    else:
        metric_highlight = "CONFIDENTIAL METRIC // AUDIT FINDING"

    pat = r'(?i)\b(debts?|nợ|bonds?|trái phiếu|yields?|rates?|lãi suất|banks?|ngân hàng|dollars?|currency|currencies|rollover|đáo hạn|finances?|financial|tài chính|gdp|imf|fed|treasury|kho bạc|inflation|lạm phát|credits?|tín dụng|365|trillions?|nghìn tỷ|securities|chứng khoán|deficits?|thâm hụt|채무|국채|금리|国債)\b'
    is_financial = bool(re.search(pat, topic_low))

    if is_financial:
        # =========================================================================
        # FINANCIAL MACRO / SOVEREIGN DEBT ROSTER (BY MARKET)
        # =========================================================================
        if m_up in ["JP", "JA"]:
            bg_roster = {
                "bg_boj_market_operations_floor": {
                    "title": "日本銀行金融市場局オープン・マーケット・オペレーションフロア",
                    "description": "Expansive architectural wide shot of Bank of Japan market operations execution floor, multiple curved multi-monitor desks displaying desaturated Japanese government bond yield curves, stone pillars with diffused daylight, serious central bank macroeconomic regulatory atmosphere, clean negative space.",
                    "beats": [1, 4]
                },
                "bg_jgb_syndicate_auction_hall": {
                    "title": "日本国債引受シンジケート入札場",
                    "description": "Grand Tokyo institutional auction hall with rows of dark cedar dealer desks facing muted digital JGB debt bidding boards, dramatic chiaroscuro lighting, dignified Japanese sovereign financial setting.",
                    "beats": [1, 3]
                },
                "bg_marunouchi_financial_skyline_dusk": {
                    "title": "丸の内・大手町金融街夕景",
                    "description": "Dramatic wide view from executive terrace overlooking Marunouchi Tokyo nocturnal skyscraper canyon, illuminated office windows receding into cold foggy blue night, dark stone ledge in foreground.",
                    "beats": [1, 5]
                },
                "bg_mof_kasumigaseki_press_briefing": {
                    "title": "財務省主計局・国債企画課会見室",
                    "description": "Formal Kasumigaseki Ministry of Finance briefing chamber, long polished table reflecting warm overhead downlights, Japanese crest in soft focus background, austere bureaucratic authority.",
                    "beats": [1, 2]
                },
                "bg_multilateral_financial_summit": {
                    "title": "アジア太平洋金融安定化サミット議場",
                    "description": "Panoramic horseshoe conference hall for sovereign debt ministers, minimalist translation audio consoles, rich dark acoustic wood textures, formal multilateral negotiations mood.",
                    "beats": [2, 3]
                },
                "bg_boj_heritage_vault_corridor": {
                    "title": "日本銀行旧地下金庫通路",
                    "description": "Deep perspective corridor of reinforced steel archival vault doors inside Bank of Japan underground vaults, cool industrial concrete walls, overhead security lighting casting rhythmic shadows.",
                    "beats": [2, 4]
                },
                "bg_boj_policy_board_chamber": {
                    "title": "日本銀行政策委員会正庁",
                    "description": "Vintage heritage boardroom with coffered timber ceilings, oil portraits in soft focus background, dark cedar council table, solemn historical financial gravity.",
                    "beats": [2, 3]
                },
                "bg_todai_macroeconomics_amphitheater": {
                    "title": "東京大学経済学部大講義室",
                    "description": "Steep tiered wooden university lecture hall, chalkboards in soft background covered with faint mathematical differential equations, warm directional spot lighting, analytical scholarly atmosphere.",
                    "beats": [2, 5]
                },
                "bg_fsa_regulatory_inspection_bullpen": {
                    "title": "金融庁市場監視局特別査察室",
                    "description": "Spacious regulatory analytical bullpen with desks piled with tabbed sovereign debt dossiers, glowing financial terminals in soft focus, slate-colored partitions, intense forensic research atmosphere.",
                    "beats": [3, 4]
                },
                "bg_mof_debt_archive_records_vault": {
                    "title": "財務省国債登録原簿記録書庫",
                    "description": "Endless rows of steel shelving containing uniform archival debt registry boxes, clean polished epoxy floor, cool white downlighting, forensic paper trail discovery setting.",
                    "beats": [3, 4]
                },
                "bg_tokyo_terminal_analytics_room": {
                    "title": "日本橋証券クオンツ・アナリティクスルーム",
                    "description": "Dark analytical operations room with high-density workstation displays showing desaturated repo matrices and sovereign CDS heatmaps, muted amber and cyan indicator lights, intense forensic mood.",
                    "beats": [3, 4]
                },
                "bg_mof_debt_management_office": {
                    "title": "財務省理財局国債課執務室",
                    "description": "Quiet executive operations office, desk lamp casting warm circular pool of light over debt rollover maturity schedules, Tokyo city skyline outside window at dusk, focused fiscal tension.",
                    "beats": [3, 5]
                },
                "bg_emergency_liquidity_crisis_hq": {
                    "title": "金融危機対策タスクフォース対策本部",
                    "description": "Urgent government crisis coordination room, whiteboards covered with debt maturity timelines and interbank swap diagrams, scattered coffee cups on meeting table, high-stakes institutional stress.",
                    "beats": [4, 5]
                },
                "bg_mega_bank_fixed_income_floor": {
                    "title": "メガバンク市場営業部債券デスク",
                    "description": "Quiet after-hours dealing floor with abandoned trader terminals showing red yield spikes, dim emergency lighting, deep shadows between rows of monitors, aftermath of liquidity shock.",
                    "beats": [4]
                },
                "bg_roppongi_investment_office_dawn": {
                    "title": "六本木投資会社エグゼクティブオフィス黎明",
                    "description": "Corner executive office with floor-to-ceiling glass catching early morning indigo and amber dawn light over Tokyo Tower, sleek minimalist desk, profound institutional isolation.",
                    "beats": [4, 5]
                },
                "bg_national_diet_financial_audit_room": {
                    "title": "衆議院予算委員会第一特別室",
                    "description": "Formal semicircular legislative committee chamber, carved walnut witness tables in foreground, elevated committee dais in background soft focus, dignified democratic scrutiny.",
                    "beats": [4, 5]
                },
                "bg_global_financial_forum_hall": {
                    "title": "国際金融フォーラム国際会議場",
                    "description": "Vast futuristic auditorium with dark acoustic wall panels, subtle uplighting along tiered seats, empty speaker lectern in clean focus, sweeping monumental perspective.",
                    "beats": [1, 5]
                },
                "bg_boj_financial_research_library": {
                    "title": "日本銀行金融研究所特別図書室",
                    "description": "Quiet double-height institutional library with floor-to-ceiling leather-bound statutory ledgers, spiral brass reading staircase, green banker lamps on dark oak tables, reflective analytical stillness.",
                    "beats": [1, 5]
                }
            }
            fg_roster = {
                "fg_character_boj_governor": {
                    "title": "日本銀行総裁",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a senior Bank of Japan governor in tailored dark charcoal suit, holding official monetary policy brief with quiet resolute authority, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Authority",
                    "beats": [1, 4, 5],
                    "keywords": ["governor", "boj", "monetary", "日本銀行", "総裁", "日銀", "金利"],
                    "type": "character"
                },
                "fg_character_jgb_bond_trader": {
                    "title": "メガバンク国債チーフトレーダー",
                    "description": "Full-body stylized editorial graphic novel digital illustration of an intense Japanese bond trader in crisp white shirt with rolled-up sleeves, reviewing printed yield curve slips with urgent skeptical gaze, corporate lapel badge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Actor",
                    "beats": [1, 2, 4],
                    "keywords": ["trader", "jgb", "yield", "bond", "国債", "トレーダー", "利回り"],
                    "type": "character"
                },
                "fg_character_mof_bureaucrat": {
                    "title": "財務省理財局次長",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a senior Ministry of Finance bureaucrat in dark navy suit and spectacles, holding tabbed sovereign debt issuance forecast binder, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Fiscal Architect",
                    "beats": [2, 3, 5],
                    "keywords": ["mof", "treasury", "fiscal", "財務省", "理財局", "主計局", "予算"],
                    "type": "character"
                },
                "fg_character_macro_financial_auditor": {
                    "title": "国際金融特別査察官",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a meticulous Japanese financial auditor in trench coat, holding heavy forensic dossier and magnifying loupe, stern analytical expression, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Investigator",
                    "beats": [3, 4, 5],
                    "keywords": ["auditor", "fsa", "investigation", "金融庁", "査察官", "監査"],
                    "type": "character"
                },
                "fg_evidence_jgb_10year_bond_certificate": {
                    "title": "第10年利付日本国債証券朱肉判子押印",
                    "description": "Official 300gsm Japanese government 10-year bond certificate with intricate security border engraving, bold coupon yield rate heading in Japanese kanji, stamped with official vermilion Ministry of Finance hanko seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Core Debt Exhibit",
                    "beats": [1, 2, 3],
                    "keywords": ["bond", "jgb", "certificate", "hanko", "国債", "利付国債", "判子"],
                    "type": "document"
                },
                "fg_evidence_debt_maturity_rollover_chart": {
                    "title": "国債償還借換スケジュール集中図表",
                    "description": "High-contrast quantitative bar graph document printed on heavy cardstock, illustrating the impending multi-trillion yen debt maturity rollover wall, highlighted in fluorescent green and red marker ink, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Quantitative Maturity Proof",
                    "beats": [1, 3, 4],
                    "keywords": ["maturity", "rollover", "wall", "chart", "借換", "償還", "図表"],
                    "type": "data_metric"
                },
                "fg_evidence_boj_balance_sheet_ledger": {
                    "title": "日本銀行資産買入勘定元帳",
                    "description": "Worn double-page central bank accounting ledger displaying ballooning asset holdings, Japanese kanji column headers, red verification hanko checkmarks, tactile paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Expansion Evidence",
                    "beats": [1, 2, 4],
                    "keywords": ["balance sheet", "boj", "assets", "日銀", "資産買入", "勘定元帳"],
                    "type": "document"
                },
                "fg_evidence_credit_rating_downgrade_letter": {
                    "title": "格付機関による日本国債格下げ勧告書",
                    "description": "Official formal rating advisory letter from credit agency, bold header stamped in red ink 'DOWNGRADED // OUTLOOK NEGATIVE', bold kanji text detailing fiscal debt overhang, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sovereign Rating Exhibit",
                    "beats": [2, 4, 5],
                    "keywords": ["rating", "downgrade", "credit", "格下げ", "格付", "信用"],
                    "type": "document"
                },
                "fg_evidence_imf_japan_surveillance_matrix": {
                    "title": "IMF第4条対日審査債務持続性マトリクス",
                    "description": "Technical macroeconomic assessment document featuring multi-column debt-to-GDP projection tables for Japan, colored risk threshold heatmaps, official institutional header, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sustainability Framework",
                    "beats": [3, 4, 5],
                    "keywords": ["imf", "gdp", "sustainability", "matrix", "持続可能性", "債務残高"],
                    "type": "data_metric"
                },
                "fg_evidence_bilateral_currency_swap_accord": {
                    "title": "日米中央銀行二国間通貨スワップ協定書",
                    "description": "Thick legal bilateral treaty contract document, multiple pages stapled at top left with official vermilion hanko seal, Japanese and English text, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Liquidity Mechanism Accord",
                    "beats": [2, 3, 4],
                    "keywords": ["swap", "currency", "bilateral", "スワップ", "為替", "協定"],
                    "type": "document"
                },
                "fg_evidence_gensaki_repo_ticket": {
                    "title": "現先取引約定確認票",
                    "description": "Tactile transaction slip on carbon-copy paper with perforated edges, showing overnight gensaki repo rate interest calculations and collateralized JGB numbers, circular red hanko stamp, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Interbank Liquidity Exhibit",
                    "beats": [2, 3, 4],
                    "keywords": ["repo", "gensaki", "ticket", "現先", "レポ", "約定確認"],
                    "type": "document"
                },
                "fg_evidence_core_cpi_inflation_sheet": {
                    "title": "全国消費者物価指数公表速報資料",
                    "description": "Official Ministry of Internal Affairs price index ledger sheet displaying escalating headline CPI numbers, red circled inflation metrics, crisp fibrous paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Inflation Metric Exhibit",
                    "beats": [1, 2, 5],
                    "keywords": ["inflation", "cpi", "price", "物価", "消費者物価指数", "インフレ"],
                    "type": "document"
                },
                "fg_evidence_g7_tokyo_communique": {
                    "title": "G7財務相・中央銀行総裁会議共同声明書",
                    "description": "Formal multilateral joint communique on heavy diplomatic letterhead, embossed gold seal, diplomatic Japanese kanji text regarding sovereign debt stabilization, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Multilateral Policy Exhibit",
                    "beats": [4, 5],
                    "keywords": ["g7", "communique", "finance", "共同声明", "財務相"],
                    "type": "document"
                },
                "fg_evidence_interbank_liquidity_crisis_memo": {
                    "title": "極秘金融危機介入通告書",
                    "description": "Manila folder document stamped '極秘 // 金融市場局長限り', heavy black redaction marker bars over vulnerable bank reserve numbers, official paperclips, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Classified Risk Memo",
                    "beats": [3, 4],
                    "keywords": ["emergency", "liquidity", "secret", "memo", "極秘", "流動性危機"],
                    "type": "document"
                },
                "fg_evidence_damages_calculation_invoice": {
                    "title": f"国債利払い費財政試算書 ({metric_highlight})",
                    "description": f"Government audit summary invoice document displaying bold figure '{metric_highlight}' in green ledger ink, stamped diagonally with bold red vermilion hanko '重要証拠 // 第1号', crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Accounting Exhibit",
                    "beats": [1, 3, 5],
                    "keywords": ["invoice", "servicing", "cost", "利払い費", "試算書", "財政"],
                    "type": "document"
                },
                "fg_evidence_japan_sovereign_cds_slip": {
                    "title": "日本国債クレジット・デフォルト・スワップスプレッド伝票",
                    "description": "Derivative order confirmation ticket, showing surging basis point credit default swap premiums on Japanese sovereign debt, stamped with red ink 'CRITICAL SPREAD', isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Default Pricing",
                    "beats": [3, 4],
                    "keywords": ["cds", "spread", "derivative", "スプレッド", "デフォルト"],
                    "type": "document"
                },
                "fg_evidence_foreign_exchange_reserve_record": {
                    "title": "財務省特別会計外国為替準備金保有証明書",
                    "description": "Official central treasury certificate documenting official gold bullion holdings and foreign reserve currency allocations, stamped with official gold star seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Reserve Backing Exhibit",
                    "beats": [2, 3, 5],
                    "keywords": ["reserve", "forex", "gold", "外貨準備", "為替特会"],
                    "type": "document"
                },
                "fg_evidence_gpif_pension_portfolio_binder": {
                    "title": "年金積立金管理運用独立行政法人ポートフォリオ報告書",
                    "description": "Thick three-ring binder open on desk showing domestic bond allocation charts losing value to yield shifts, colored tab dividers, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Institutional Impact Exhibit",
                    "beats": [3, 4, 5],
                    "keywords": ["pension", "gpif", "fund", "allocation", "年金積立金", "ポートフォリオ"],
                    "type": "document"
                },
                "fg_evidence_emergency_fiscal_injection_decree": {
                    "title": "政府緊急財政投融資発動令",
                    "description": "Formal executive decree on government letterhead signed with blue fountain pen ink, authorising emergency sovereign treasury liquidity backstops, vermilion cabinet seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "State Intervention Order",
                    "beats": [4, 5],
                    "keywords": ["decree", "bailout", "injection", "財政投融資", "緊急支援"],
                    "type": "document"
                },
                "fg_evidence_statutory_finance_law_codex": {
                    "title": "財政法・日本銀行法大系法規集",
                    "description": "Heavy vintage leather-bound legal codex open to statutory debt limit and central bank charter sections, gold kanji lettering on spine, crisp cream paper edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Statutory Authority",
                    "beats": [1, 2, 5],
                    "keywords": ["statute", "law", "code", "codex", "財政法", "日本銀行法", "六法"],
                    "type": "document"
                },
                "fg_evidence_tokyo_district_court_insolvency_docket": {
                    "title": "東京地方裁判所会社更生手続申立書",
                    "description": "Official legal filing document from Tokyo District Court, bold case docket header in Japanese kanji, stamped with vermilion court hanko seal, crisp document paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Lead Prosecution Docket",
                    "beats": [1, 4, 5],
                    "keywords": ["docket", "insolvency", "court", "更生手続", "裁判所", "倒産"],
                    "type": "document"
                },
                "fg_evidence_judicial_gavel_sounding_block": {
                    "title": "司法審判用小槌及び量刑台",
                    "description": "Dark polished Japanese cherry-wood judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Judicial Climax Artifact",
                    "beats": [4, 5],
                    "keywords": ["gavel", "scales", "judge", "court", "小槌", "判決", "法廷"],
                    "type": "evidence_prop"
                }
            }
            return bg_roster, fg_roster

        elif m_up in ["KR", "KO"]:
            bg_roster = {
                "bg_bok_monetary_policy_floor": {
                    "title": "한국은행 공개시장운영 종합상황실",
                    "description": "Expansive architectural wide shot of Bank of Korea open market execution room, curved multi-monitor desks displaying desaturated Korean Treasury Bond yield curves, granite colonnade with diffused daylight, serious central bank macroeconomic regulatory atmosphere, clean negative space.",
                    "beats": [1, 4]
                },
                "bg_ktb_primary_dealer_auction_hall": {
                    "title": "국고채 전문딜러 입찰실",
                    "description": "Grand Yeouido institutional auction hall with rows of dark walnut dealer desks facing muted digital KTB debt bidding boards, dramatic high-contrast chiaroscuro lighting, dignified Korean sovereign financial setting.",
                    "beats": [1, 3]
                },
                "bg_yeouido_financial_district_night": {
                    "title": "여의도 증권가 야경",
                    "description": "Dramatic wide view from executive terrace overlooking Yeouido nocturnal skyscraper canyon, illuminated office windows receding into cold foggy blue night, dark sleek granite ledge in foreground.",
                    "beats": [1, 5]
                },
                "bg_moef_sejong_briefing_room": {
                    "title": "기획재정부 국채발행 브리핑룸",
                    "description": "Formal Sejong government complex fiscal policy briefing chamber, long polished table reflecting warm overhead downlights, national emblem in soft focus background, austere bureaucratic authority.",
                    "beats": [1, 2]
                },
                "bg_multilateral_east_asia_summit": {
                    "title": "한중일 거시경제금융안정 회의장",
                    "description": "Panoramic horseshoe conference hall for sovereign debt ministers, minimalist translation audio consoles, rich dark acoustic wood textures, formal multilateral negotiations mood.",
                    "beats": [2, 3]
                },
                "bg_bok_secure_vault_corridor": {
                    "title": "한국은행 금고 지하 통로",
                    "description": "Deep perspective corridor of reinforced steel archival vault doors inside Bank of Korea underground vaults, cool industrial concrete walls, overhead fluorescent security lighting casting rhythmic shadows.",
                    "beats": [2, 4]
                },
                "bg_bok_financial_monetary_committee_chamber": {
                    "title": "한국은행 금융통화위원회 본회의장",
                    "description": "Vintage heritage council chamber with coffered timber ceilings, national emblem on mahogany backdrop, dark oak council table, solemn historical financial gravity.",
                    "beats": [2, 3]
                },
                "bg_seoul_national_econ_amphitheater": {
                    "title": "서울대학교 경제학부 대강의실",
                    "description": "Steep tiered wooden university lecture hall, chalkboards in soft background covered with faint mathematical differential equations, warm directional spot lighting, analytical scholarly atmosphere.",
                    "beats": [2, 5]
                },
                "bg_fsc_fss_inspection_bullpen": {
                    "title": "금융위원회 금융감독원 자본시장 특별조사국",
                    "description": "Spacious regulatory analytical bullpen with desks piled with tabbed sovereign debt dossiers, glowing financial terminals in soft focus, slate-colored partitions, intense forensic research atmosphere.",
                    "beats": [3, 4]
                },
                "bg_moef_debt_archive_records_vault": {
                    "title": "국가채무관리기록보존서고",
                    "description": "Endless rows of steel shelving containing uniform archival debt registry boxes, clean polished epoxy floor, cool white downlighting, forensic paper trail discovery setting.",
                    "beats": [3, 4]
                },
                "bg_krx_derivatives_analytics_room": {
                    "title": "한국거래소 파생상품 퀀트분석센터",
                    "description": "Dark analytical operations room with high-density workstation displays showing desaturated repo matrices and sovereign CDS heatmaps, muted amber and cyan indicator lights, intense forensic mood.",
                    "beats": [3, 4]
                },
                "bg_moef_fiscal_management_office": {
                    "title": "기획재정부 재정관리국 국채과",
                    "description": "Quiet executive operations office, desk lamp casting warm circular pool of light over debt rollover maturity schedules, city skyline outside window at dusk, focused fiscal tension.",
                    "beats": [3, 5]
                },
                "bg_emergency_financial_war_room": {
                    "title": "금융위기 비상대응상황실",
                    "description": "Urgent government crisis coordination room, whiteboards covered with debt maturity timelines and interbank swap diagrams, scattered coffee cups on meeting table, high-stakes institutional stress.",
                    "beats": [4, 5]
                },
                "bg_commercial_bank_treasury_desk": {
                    "title": "시중은행 자금운용부 채권트레이딩룸",
                    "description": "Quiet after-hours dealing floor with abandoned trader terminals showing red yield spikes, dim emergency lighting, deep shadows between rows of monitors, aftermath of liquidity shock.",
                    "beats": [4]
                },
                "bg_teheranro_asset_management_dawn": {
                    "title": "테헤란로 자산운용사 총괄집무실 여명",
                    "description": "Corner executive office with floor-to-ceiling glass catching early morning indigo and amber dawn light over Seoul skyline, sleek minimalist desk, profound institutional isolation.",
                    "beats": [4, 5]
                },
                "bg_national_assembly_strategy_finance_hall": {
                    "title": "국회 기획재정위원회 대회의실",
                    "description": "Formal semicircular legislative committee chamber, carved walnut witness tables in foreground, elevated committee dais in background soft focus, dignified democratic scrutiny.",
                    "beats": [4, 5]
                },
                "bg_global_financial_governance_hall": {
                    "title": "국제금융기구 연례협의 총회장",
                    "description": "Vast futuristic auditorium with dark acoustic wall panels, subtle uplighting along tiered seats, empty speaker lectern in clean focus, sweeping monumental perspective.",
                    "beats": [1, 5]
                },
                "bg_bok_economic_research_library": {
                    "title": "한국은행 경제연구원 전문학술도서관",
                    "description": "Quiet double-height institutional library with floor-to-ceiling leather-bound statutory ledgers, spiral brass reading staircase, green banker lamps on dark oak tables, reflective analytical stillness.",
                    "beats": [1, 5]
                }
            }
            fg_roster = {
                "fg_character_bok_governor": {
                    "title": "한국은행 총재",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a senior Bank of Korea governor in tailored dark charcoal suit, holding official monetary policy brief with composed authoritative posture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Authority",
                    "beats": [1, 4, 5],
                    "keywords": ["governor", "bok", "monetary", "한국은행", "총재", "금리", "금융통화위원회"],
                    "type": "character"
                },
                "fg_character_ktb_bond_trader": {
                    "title": "여의도 국고채 수석 딜러",
                    "description": "Full-body stylized editorial graphic novel digital illustration of an intense Korean sovereign bond trader in crisp white shirt with rolled-up sleeves, reviewing printed yield curve slips with urgent skeptical gaze, wearing Sawonjeung corporate ID lanyard, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Actor",
                    "beats": [1, 2, 4],
                    "keywords": ["trader", "ktb", "yield", "bond", "국고채", "딜러", "채권"],
                    "type": "character"
                },
                "fg_character_moef_fiscal_director": {
                    "title": "기획재정부 국채과장",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a senior MOEF fiscal official in dark navy blazer and glasses, holding tabbed sovereign borrowing forecast binder, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Fiscal Architect",
                    "beats": [2, 3, 5],
                    "keywords": ["moef", "treasury", "fiscal", "기획재정부", "국채", "재정"],
                    "type": "character"
                },
                "fg_character_macro_financial_auditor": {
                    "title": "감사원 금융기금 감사관",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a meticulous sovereign debt auditor in gray trench coat, holding heavy forensic dossier and magnifying loupe, stern analytical expression, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Investigator",
                    "beats": [3, 4, 5],
                    "keywords": ["auditor", "fss", "investigation", "감사원", "금융감독원", "검사"],
                    "type": "character"
                },
                "fg_evidence_ktb_10year_bond_certificate": {
                    "title": "대한민국 국고채권 10년물 증서 인감 날인",
                    "description": "Official 300gsm fibrous paper Republic of Korea 10-year Treasury Bond certificate with intricate guilloche security borders, bold coupon yield rate heading in Hangul, stamped diagonally with official crimson Ingam seal, crisp cutout edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Core Debt Exhibit",
                    "beats": [1, 2, 3],
                    "keywords": ["bond", "ktb", "certificate", "ingam", "국고채권", "인감", "채권"],
                    "type": "document"
                },
                "fg_evidence_debt_maturity_rollover_chart": {
                    "title": "국채 만기도래 상환 집중구간 차트",
                    "description": "High-contrast quantitative bar graph document printed on heavy cardstock, illustrating the impending multi-trillion won debt maturity rollover wall across upcoming fiscal years, highlighted in fluorescent green and red marker ink, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Quantitative Maturity Proof",
                    "beats": [1, 3, 4],
                    "keywords": ["maturity", "rollover", "wall", "chart", "만기도래", "차환", "상환"],
                    "type": "data_metric"
                },
                "fg_evidence_bok_balance_sheet_ledger": {
                    "title": "한국은행 대차대조표 및 유동성 자산대장",
                    "description": "Worn double-page central bank accounting ledger displaying ballooning asset holdings, Hangul column headers, red verification checkmarks, tactile paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Expansion Evidence",
                    "beats": [1, 2, 4],
                    "keywords": ["balance sheet", "bok", "assets", "한국은행", "대차대조표", "자산"],
                    "type": "document"
                },
                "fg_evidence_credit_rating_downgrade_letter": {
                    "title": "국제신용평가사 국가신용등급 강등 통보서",
                    "description": "Official formal rating advisory letter from credit agency, bold header stamped in red ink 'DOWNGRADED // OUTLOOK NEGATIVE', bold Hangul text detailing fiscal debt overhang, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sovereign Rating Exhibit",
                    "beats": [2, 4, 5],
                    "keywords": ["rating", "downgrade", "credit", "신용등급", "강등", "신용평가"],
                    "type": "document"
                },
                "fg_evidence_imf_korea_surveillance_matrix": {
                    "title": "IMF 연례협의 대외채무 지속가능성 평가표",
                    "description": "Technical macroeconomic assessment document featuring multi-column debt-to-GDP projection tables for South Korea, colored risk threshold heatmaps, official institutional header, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sustainability Framework",
                    "beats": [3, 4, 5],
                    "keywords": ["imf", "gdp", "sustainability", "matrix", "지속가능성", "국가채무"],
                    "type": "data_metric"
                },
                "fg_evidence_bilateral_currency_swap_accord": {
                    "title": "한미 중앙은행 통화스와프 계약서",
                    "description": "Thick legal bilateral treaty contract document, multiple pages stapled at top left with circular crimson Ingam seal, Korean and English text, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Liquidity Mechanism Accord",
                    "beats": [2, 3, 4],
                    "keywords": ["swap", "currency", "bilateral", "통화스와프", "외환", "계약서"],
                    "type": "document"
                },
                "fg_evidence_rp_repo_transaction_ticket": {
                    "title": "환매조건부채권(RP) 매매 체결확인서",
                    "description": "Small tactile transaction slip on yellow carbon-copy paper with perforated edges, showing overnight RP repo rate interest calculations and collateralized bond numbers, circular red teller stamp, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Interbank Liquidity Exhibit",
                    "beats": [2, 3, 4],
                    "keywords": ["repo", "rp", "ticket", "환매조건부채권", "콜시장", "체결확인서"],
                    "type": "document"
                },
                "fg_evidence_cpi_inflation_ledger_slip": {
                    "title": "소비자물가지수(CPI) 동향 분석표",
                    "description": "Official Statistics Korea price index ledger sheet displaying escalating headline CPI numbers, red circled inflation metrics, crisp fibrous paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Inflation Metric Exhibit",
                    "beats": [1, 2, 5],
                    "keywords": ["inflation", "cpi", "price", "소비자물가", "인플레이션", "통계청"],
                    "type": "document"
                },
                "fg_evidence_g20_seoul_finance_communique": {
                    "title": "G20 재무장관 회의 공동선언문",
                    "description": "Formal multilateral joint communique on heavy diplomatic letterhead, official emblem at top, embossed gold foil seal, diplomatic clauses regarding debt restructuring in Hangul, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Multilateral Policy Exhibit",
                    "beats": [4, 5],
                    "keywords": ["g20", "ministers", "communique", "공동선언문", "재무장관"],
                    "type": "document"
                },
                "fg_evidence_interbank_liquidity_crisis_memo": {
                    "title": "대외비 은행간 유동성 위기 경보 전문",
                    "description": "Manila folder document stamped '대외비 // 금융통화위원 한정', heavy black redaction marker bars over vulnerable bank reserve numbers, official paperclips, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Classified Risk Memo",
                    "beats": [3, 4],
                    "keywords": ["emergency", "liquidity", "secret", "memo", "대외비", "유동성위기"],
                    "type": "document"
                },
                "fg_evidence_damages_calculation_invoice": {
                    "title": f"국채 이자비용 재정소요 산출명세서 ({metric_highlight})",
                    "description": f"Government audit summary invoice document displaying bold figure '{metric_highlight}' in green ledger ink, stamped diagonally with bold red ink '증거 제1호', crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Accounting Exhibit",
                    "beats": [1, 3, 5],
                    "keywords": ["invoice", "interest", "servicing", "이자비용", "재정소요", "산출명세서"],
                    "type": "document"
                },
                "fg_evidence_korea_sovereign_cds_slip": {
                    "title": "대한민국 외평채 CDS 프리미엄 체결전표",
                    "description": "High-finance derivative order confirmation ticket, showing surging basis point credit default swap premiums on Korean Foreign Exchange Stabilization Bonds, stamped with red ink 'CRITICAL EXPOSURE', isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Default Pricing",
                    "beats": [3, 4],
                    "keywords": ["cds", "spread", "derivative", "외평채", "프리미엄", "부도스왑"],
                    "type": "document"
                },
                "fg_evidence_foreign_exchange_reserve_record": {
                    "title": "한국은행 외환보유액 감사증명서",
                    "description": "Official central treasury certificate documenting official gold bullion holdings and foreign reserve currency allocations, stamped with official gold seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Reserve Backing Exhibit",
                    "beats": [2, 3, 5],
                    "keywords": ["reserve", "forex", "gold", "외환보유액", "준비자산"],
                    "type": "document"
                },
                "fg_evidence_nps_national_pension_binder": {
                    "title": "국민연금공단(NPS) 채권포트폴리오 분석철",
                    "description": "Thick three-ring binder open on desk showing domestic fixed-income allocation pie charts losing principal value to high yields, colored tab dividers, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Institutional Impact Exhibit",
                    "beats": [3, 4, 5],
                    "keywords": ["pension", "nps", "fund", "allocation", "국민연금", "채권포트폴리오"],
                    "type": "document"
                },
                "fg_evidence_emergency_recapitalization_order": {
                    "title": "공적자금관리위원회 긴급출자명령서",
                    "description": "Formal executive decree on government letterhead signed with blue fountain pen ink, authorising emergency sovereign treasury backstops and public funds recapitalisation, circular crimson Ingam seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "State Intervention Order",
                    "beats": [4, 5],
                    "keywords": ["decree", "bailout", "recapitalization", "공적자금", "출자명령"],
                    "type": "document"
                },
                "fg_evidence_statutory_finance_law_codex": {
                    "title": "국가재정법 및 한국은행법 주해집",
                    "description": "Heavy vintage leather-bound legal codex open to statutory debt limit and central bank charter sections, gold leaf Hangul lettering on spine, crisp cream paper edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Statutory Authority",
                    "beats": [1, 2, 5],
                    "keywords": ["statute", "law", "code", "국가재정법", "한국은행법", "법전"],
                    "type": "document"
                },
                "fg_evidence_seoul_court_insolvency_docket": {
                    "title": "서울회생법원 회생절차개시신청서",
                    "description": "Official legal filing document from Seoul Bankruptcy Court, bold case docket header in Hangul, stamped with circular red court seal, crisp document paper texture with clean sharp edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Lead Prosecution Docket",
                    "beats": [1, 4, 5],
                    "keywords": ["docket", "insolvency", "court", "회생신청", "회생법원", "부도"],
                    "type": "document"
                },
                "fg_evidence_judicial_gavel_sounding_block": {
                    "title": "법원 사법 심판봉 및 정의의 저울",
                    "description": "Dark polished walnut judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Judicial Climax Artifact",
                    "beats": [4, 5],
                    "keywords": ["gavel", "scales", "judge", "court", "심판봉", "판결", "법원"],
                    "type": "evidence_prop"
                }
            }
            return bg_roster, fg_roster

        elif m_up in ["VN", "VI"]:
            bg_roster = {
                "bg_sbv_open_market_floor": {
                    "title": "Sàn Giao Dịch Thị Trường Mở Ngân Hàng Nhà Nước Việt Nam",
                    "description": "Không gian sàn điều hành nghiệp vụ thị trường mở OMO của Ngân hàng Nhà nước, các dãy bàn chuyên viên với hệ thống màn hình hiển thị đường cong lợi suất trái phiếu chính phủ VND, cột trụ đá cổ điển với ánh sáng ban ngày khuếch tán, bầu không khí pháp lý tiền tệ uy nghiêm.",
                    "beats": [1, 4]
                },
                "bg_treasury_bond_auction_hall": {
                    "title": "Hội Trường Đấu Thầu Trái Phiếu Chính Phủ Sở Giao Dịch HNX",
                    "description": "Hội trường đấu thầu trái phiếu chính phủ trang trọng với các dãy bàn thành viên đấu thầu nhìn về bảng điện tử định giá trái phiếu trung ương, ánh sáng tương phản chiaroscuro sắc nét, không gian tài chính công trang nghiêm.",
                    "beats": [1, 3]
                },
                "bg_saigon_financial_district_night": {
                    "title": "Đại Lộ Tài Chính Bến Bạch Đằng & Sông Sài Gòn Về Đêm",
                    "description": "Góc nhìn toàn cảnh từ ban công tầng cao nhìn xuống đại lộ tài chính lung linh ánh đèn phản chiếu trên mặt sông về đêm, lan can đá granit tối màu ở tiền cảnh, sự tĩnh lặng sâu sắc của trung tâm vốn.",
                    "beats": [1, 5]
                },
                "bg_mof_vietnam_briefing_room": {
                    "title": "Phòng Họp Báo Cục Quản Lý Nợ & Tài Chính Đối Ngoại Bộ Tài Chính",
                    "description": "Phòng họp báo nghiệp vụ của Bộ Tài chính với bàn gỗ bóng phản chiếu ánh đèn rọi trần, quốc huy Việt Nam trên phông nền phía sau mờ nhẹ, không khí hành chính quyền lực.",
                    "beats": [1, 2]
                },
                "bg_asean_financial_stability_summit": {
                    "title": "Hội Trường Hội Nghị Bộ Trưởng Tài Chính ASEAN",
                    "description": "Hội trường bàn tròn hình móng ngựa dành cho các bộ trưởng tài chính khu vực, cabin dịch thuật hội nghị mờ nhẹ phía sau, vách gỗ tiêu âm hiện đại sang trọng.",
                    "beats": [2, 3]
                },
                "bg_sbv_vault_corridor": {
                    "title": "Hành Lang Kho Tiền Trung Ương Ngân Hàng Nhà Nước",
                    "description": "Hành lang sâu hun hút với các cửa vòm thép kiên cố của kho dự trữ tiền tệ quốc gia, tường bê tông công nghiệp sạch bóng, ánh đèn tuýp trắng rọi theo nhịp bước.",
                    "beats": [2, 4]
                },
                "bg_sbv_monetary_council_chamber": {
                    "title": "Phòng Họp Hội Đồng Tư Vấn Chính Sách Tiền Tệ Quốc Gia",
                    "description": "Phòng họp trang trọng với bàn họp dài bằng gỗ xoan đào, cờ đỏ sao vàng ở góc trang trọng, tài liệu điều hành vĩ mô xếp ngay ngắn, không khí tư pháp tiền tệ trang nghiêm.",
                    "beats": [2, 3]
                },
                "bg_national_economics_amphitheater": {
                    "title": "Giảng Đường Lớn Đại Học Kinh Tế Quốc Dân",
                    "description": "Giảng đường bậc thang dốc bằng gỗ tự nhiên, bảng đen phía sau viết các phương trình vi phân kinh tế vĩ mô mờ nhẹ, ánh đèn rọi tập trung học thuật chuyên sâu.",
                    "beats": [2, 5]
                },
                "bg_ssc_market_surveillance_bullpen": {
                    "title": "Cục Thanh Tra Giám Sát Thị Trường Ủy Ban Chứng Khoán Nhà Nước",
                    "description": "Khu làm việc thanh tra chứng khoán với các dãy bàn chất đầy hồ sơ phát hành trái phiếu doanh nghiệp, màn hình giám sát dòng tiền, vách ngăn văn phòng tối giản.",
                    "beats": [3, 4]
                },
                "bg_state_treasury_archive_vault": {
                    "title": "Kho Lưu Trữ Hồ Sơ Nợ Công & Ngân Sách Kho Bạc Nhà Nước",
                    "description": "Hệ thống giá kệ kim loại sâu hun hút chứa hàng trăm hộp tài liệu đăng ký trái phiếu chính phủ, nền epoxy sạch bóng, ánh sáng đèn trắng chuẩn mực pháp y.",
                    "beats": [3, 4]
                },
                "bg_financial_analytics_terminal_room": {
                    "title": "Phòng Phân Tích Dòng Tiền & Định Lượng Trái Phiếu",
                    "description": "Trung tâm phân tích tài chính hiện đại với các trạm máy tính hiển thị ma trận thanh khoản liên ngân hàng và biểu đồ hoán đổi rủi ro nợ, ánh sáng dịu tập trung.",
                    "beats": [3, 4]
                },
                "bg_debt_management_director_office": {
                    "title": "Văn Phòng Cục Quản Lý Nợ Công Bộ Tài Chính",
                    "description": "Văn phòng lãnh đạo cục quản lý nợ công lúc hoàng hôn, đèn bàn rọi vào tập lịch trình đáo hạn trái phiếu chính phủ, cửa sổ nhìn ra phố xá trung tâm.",
                    "beats": [3, 5]
                },
                "bg_emergency_liquidity_crisis_hq": {
                    "title": "Phòng Tác Chiến Xử Lý Khủng Hoảng Thanh Khoản Ngân Hàng",
                    "description": "Phòng tác chiến khẩn cấp của ban điều hành, bảng trắng vẽ sơ đồ dòng tiền cứu trợ liên ngân hàng và tái cấp vốn, tách cà phê trên bàn họp dã chiến, áp lực điều hành cao độ.",
                    "beats": [4, 5]
                },
                "bg_commercial_bank_treasury_pit": {
                    "title": "Sàn Giao Dịch Nguồn Vốn & Trái Phiếu Ngân Hàng Thương Mại",
                    "description": "Sàn giao dịch nguồn vốn sau giờ làm việc với các dãy màn hình hiển thị cảnh báo lãi suất qua đêm tăng vọt, ánh đèn khẩn cấp mờ tối, dư âm cú sốc thanh khoản.",
                    "beats": [4]
                },
                "bg_financial_executive_office_dawn": {
                    "title": "Văn Phòng Chủ Tịch Hội Đồng Quản Trị Nhìn Xuống Thành Phố Lúc Bình Minh",
                    "description": "Văn phòng góc tầng cao với vách kính phản chiếu ánh bình minh vàng lam trên các cao ốc tài chính, bàn làm việc gỗ mun hiện đại, cảm giác cô độc thể chế.",
                    "beats": [4, 5]
                },
                "bg_national_assembly_budget_committee_hall": {
                    "title": "Hội Trường Ủy Ban Tài Chính Ngân Sách Quốc Hội",
                    "description": "Hội trường giám sát ngân sách nhà nước hình bán nguyệt của Quốc hội, bàn đại biểu bằng gỗ gụ phía trước, bục chủ tọa phía sau mờ nhẹ, sự thẩm tra dân chủ nghiêm minh.",
                    "beats": [4, 5]
                },
                "bg_macro_economic_forum_hall": {
                    "title": "Hội Trường Diễn Đàn Kinh Tế Vĩ Mô & Thị Trường Vốn",
                    "description": "Hội trường lớn với vách tiêu âm tối màu, ánh đèn rọi tinh tế dọc các hàng ghế đại biểu, bục diễn giả sắc nét, góc nhìn kiến trúc hoành tráng.",
                    "beats": [1, 5]
                },
                "bg_sbv_banking_academy_library": {
                    "title": "Thư Viện Nghiên Cứu Lịch Sử Tiền Tệ & Ngân Hàng",
                    "description": "Thư viện tư liệu ngân hàng trung ương với các kệ sách luật ngân sách bọc da cổ điển, cầu thang sắt uốn, đèn bàn xanh ngọc trên bàn gỗ, không gian chiêm nghiệm sâu lắng.",
                    "beats": [1, 5]
                }
            }
            fg_roster = {
                "fg_character_sbv_governor": {
                    "title": "Thống Đốc Ngân Hàng Nhà Nước Việt Nam",
                    "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một vị Thống đốc Ngân hàng Nhà nước trong trang phục vest tối màu trang trọng, dáng đứng uy quyền điềm tĩnh, cầm tập hồ sơ chỉ đạo điều hành chính sách tiền tệ, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Authority",
                    "beats": [1, 4, 5],
                    "keywords": ["thống đốc", "ngân hàng nhà nước", "nhnn", "tiền tệ", "lãi suất", "chính sách"],
                    "type": "character"
                },
                "fg_character_sovereign_bond_trader": {
                    "title": "Trưởng Bộ Phận Kinh Doanh Nguồn Vốn & Trái Phiếu",
                    "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một trưởng phòng kinh doanh nguồn vốn ngân hàng thương mại trong áo sơ mi trắng thắt cà vạt xắn tay áo, nét mặt căng thẳng xem xét bảng số liệu đường cong lợi suất, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Actor",
                    "beats": [1, 2, 4],
                    "keywords": ["trader", "trái phiếu", "lợi suất", "nguồn vốn", "kinh doanh", "dealer"],
                    "type": "character"
                },
                "fg_character_debt_management_director": {
                    "title": "Cục Trưởng Cục Quản Lý Nợ Công Bộ Tài Chính",
                    "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một cục trưởng quản lý nợ công trong bộ vest xanh navy chỉn chu đeo kính gọng kim loại, cầm tập kẹp dự báo hạn mức vay nợ quốc gia, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Fiscal Architect",
                    "beats": [2, 3, 5],
                    "keywords": ["nợ công", "bộ tài chính", "ngân sách", "cục trưởng", "kho bạc"],
                    "type": "character"
                },
                "fg_character_macro_debt_auditor": {
                    "title": "Trưởng Đoàn Thanh Tra Pháp Y Thị Trường Trái Phiếu",
                    "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một thanh tra viên kiểm toán tài chính trong trang phục thanh tra nghiêm nghị, tay cầm kính lúp và tập hồ sơ chứng cứ dòng tiền, ánh mắt sắc sảo truy tìm sai phạm, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Investigator",
                    "beats": [3, 4, 5],
                    "keywords": ["thanh tra", "kiểm toán", "pháp y", "sai phạm", "điều tra"],
                    "type": "character"
                },
                "fg_evidence_vn_government_bond_certificate": {
                    "title": "Trái Phiếu Chính Phủ Việt Nam Mệnh Giá VND Đóng Mộc Đỏ Quốc Huy",
                    "description": "Văn bản chứng chỉ Trái phiếu Chính phủ Việt Nam in bảo an chống giả trên giấy 300gsm, hoa văn chìm tinh xảo, ghi rõ lãi suất danh nghĩa và kỳ hạn 10 năm bằng tiền đồng VND, đóng dấu mộc đỏ tươi hình quốc huy của Bộ Tài chính, mép giấy sắc nét, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Core Debt Exhibit",
                    "beats": [1, 2, 3],
                    "keywords": ["trái phiếu chính phủ", "tpcp", "mộc đỏ", "quốc huy", "vnd", "kho bạc"],
                    "type": "document"
                },
                "fg_evidence_debt_maturity_rollover_chart": {
                    "title": "Biểu Đồ Cột Đáo Hạn Trái Phiếu Doanh Nghiệp & Nợ Công (Maturity Wall)",
                    "description": "Biểu đồ cột định lượng độ tương phản cao in trên bìa cứng dày, thể hiện áp lực đáo hạn hàng trăm nghìn tỷ đồng dồn toa giai đoạn tới, đánh dấu bút dạ quang xanh và đỏ nổi bật, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Quantitative Maturity Proof",
                    "beats": [1, 3, 4],
                    "keywords": ["đáo hạn", "rollover", "dồn toa", "áp lực trả nợ", "biểu đồ"],
                    "type": "data_metric"
                },
                "fg_evidence_sbv_balance_sheet_ledger": {
                    "title": "Sổ Cái Cân Đối Thanh Khoản & Mua Bán Ngoại Tệ NHNN",
                    "description": "Quyển sổ cái kế toán điều hành tiền tệ mở rộng hiển thị các khoản can thiệp thanh khoản tiền đồng và dự trữ ngoại hối, tiêu đề cột bằng tiếng Việt, dấu tích kiểm tra bút mực đỏ, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Expansion Evidence",
                    "beats": [1, 2, 4],
                    "keywords": ["bảng cân đối", "nhnn", "ngoại tệ", "dòng tiền", "sổ cái"],
                    "type": "document"
                },
                "fg_evidence_credit_rating_downgrade_letter": {
                    "title": "Thông Báo Đánh Giá Xếp Hạng Tín Nhiệm Quốc Gia & Doanh Nghiệp",
                    "description": "Văn bản thông báo chính thức của tổ chức xếp hạng tín nhiệm, đóng dấu chéo mực đỏ 'HẠ TRIỂN VỌNG // TIÊU CỰC', chữ in rõ nét phân tích gánh nặng nợ và hệ số đòn bẩy, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sovereign Rating Exhibit",
                    "beats": [2, 4, 5],
                    "keywords": ["xếp hạng", "tín nhiệm", "hạ bậc", "rủi ro", "đánh giá"],
                    "type": "document"
                },
                "fg_evidence_imf_vietnam_surveillance_matrix": {
                    "title": "Bảng Phân Tích Tính Bền Vững Nợ Công Khung Đánh Giá IMF",
                    "description": "Tài liệu đánh giá kinh tế vĩ mô nhiều cột với các bảng dự báo tỷ lệ nợ trên GDP của Việt Nam, bản đồ nhiệt phân tầng rủi ro, tiêu đề cơ quan chính thức, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sustainability Framework",
                    "beats": [3, 4, 5],
                    "keywords": ["imf", "gdp", "nợ công", "bền vững", "chỉ số"],
                    "type": "data_metric"
                },
                "fg_evidence_bilateral_currency_swap_accord": {
                    "title": "Hợp Đồng Hạn Mức Tín Dụng & Hoán Đổi Ngoại Tệ Song Phương",
                    "description": "Tập hợp đồng tín dụng song phương dày nhiều trang đóng ghim đồng góc trái, đóng dấu mộc đỏ giáp lai giữa các mép giấy, chữ ký đại diện ngân hàng bằng mực xanh, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Liquidity Mechanism Accord",
                    "beats": [2, 3, 4],
                    "keywords": ["hoán đổi", "ngoại hối", "tín dụng", "hợp đồng", "giáp lai"],
                    "type": "document"
                },
                "fg_evidence_interbank_repo_ticket": {
                    "title": "Lệnh Giao Dịch Repo Thị Trường Liên Ngân Hàng Có Mộc Tròn Ngân Hàng",
                    "description": "Phiếu lệnh xác nhận giao dịch mua bán có kỳ hạn (Repo) in trên giấy carbon vàng có răng cưa, ghi rõ lãi suất qua đêm và mã trái phiếu thế chấp, dấu tròn đỏ ngân hàng, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Interbank Liquidity Exhibit",
                    "beats": [2, 3, 4],
                    "keywords": ["repo", "liên ngân hàng", "phiếu lệnh", "chiết khấu", "thanh khoản"],
                    "type": "document"
                },
                "fg_evidence_cpi_inflation_ledger_slip": {
                    "title": "Bảng Số Liệu Chỉ Số Giá Tiêu Dùng CPI Tổng Cục Thống Kê",
                    "description": "Bản tin thống kê chính thức của Tổng cục Thống kê hiển thị đà leo thang của chỉ số CPI qua các quý, khoanh tròn đỏ số liệu lạm phát cốt lõi, chất liệu giấy in văn phòng sắc nét, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Inflation Metric Exhibit",
                    "beats": [1, 2, 5],
                    "keywords": ["cpi", "lạm phát", "giá tiêu dùng", "thống kê", "chỉ số"],
                    "type": "document"
                },
                "fg_evidence_asean_finance_communique": {
                    "title": "Tuyên Bố Chung Hội Nghị Bộ Trưởng Tài Chính & Thống Đốc ASEAN",
                    "description": "Văn bản tuyên bố chung ngoại giao trên giấy tiêu đề trang trọng, biểu trưng ASEAN phía trên, dấu dập nổi mạ vàng, nội dung thỏa thuận ổn định thị trường tài chính khu vực, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Multilateral Policy Exhibit",
                    "beats": [4, 5],
                    "keywords": ["tuyên bố", "asean", "hội nghị", "bộ trưởng", "tài chính"],
                    "type": "document"
                },
                "fg_evidence_classified_liquidity_memo": {
                    "title": "Báo Cáo Khẩn Về Nguy Cơ Mất Thanh Khoản Dấu Đỏ Tuyệt Mật",
                    "description": "Túi hồ sơ giấy xi măng màu nâu đóng dấu đỏ 'TUYỆT MẬT // CHỈ LƯU HÀNH LÃNH ĐẠO', tài liệu bên trong bị gạch đen xóa thông tin số dư thanh khoản các ngân hàng yếu kém, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Classified Risk Memo",
                    "beats": [3, 4],
                    "keywords": ["tuyệt mật", "khẩn cấp", "thanh khoản", "báo cáo", "rủi ro"],
                    "type": "document"
                },
                "fg_evidence_damages_calculation_invoice": {
                    "title": f"Bảng Tính Chi Phí Nghĩa Vụ Trả Nợ & Lãi Vay Quá Hạn ({metric_highlight})",
                    "description": f"Bảng phụ lục kiểm toán tài chính hiển thị con số nghĩa vụ trả nợ '{metric_highlight}' mực xanh nổi bật, đóng dấu chéo mực đỏ 'TÀI LIỆU CHỨNG CỨ PHÁP LÝ', viền cắt sắc sảo, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Accounting Exhibit",
                    "beats": [1, 3, 5],
                    "keywords": ["chi phí", "nghĩa vụ trả nợ", "lãi vay", "thiệt hại", "bảng tính"],
                    "type": "document"
                },
                "fg_evidence_cds_spread_ticket": {
                    "title": "Bảng Định Giá Phí Phòng Ngừa Rủi Ro Vỡ Nợ Trái Phiếu",
                    "description": "Phiếu xác nhận giao dịch phòng ngừa rủi ro tài chính hiển thị mức phí CDS tăng vọt hàng trăm điểm cơ bản, đóng dấu mực đỏ 'RỦI RO BÁO ĐỘNG ĐỎ', isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Default Pricing",
                    "beats": [3, 4],
                    "keywords": ["cds", "vỡ nợ", "phí rủi ro", "trái phiếu", "spread"],
                    "type": "document"
                },
                "fg_evidence_foreign_exchange_reserve_record": {
                    "title": "Giấy Chứng Nhận Dự Trữ Ngoại Hối & Kim Loại Quý Nhà Nước",
                    "description": "Văn bản xác nhận chính thức của Kho bạc và NHNN ghi nhận quy mô dự trữ ngoại tệ và vàng miếng quốc gia, đóng dấu sao vàng nổi, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Reserve Backing Exhibit",
                    "beats": [2, 3, 5],
                    "keywords": ["dự trữ", "ngoại hối", "vàng", "bảo chứng", "ngân khố"],
                    "type": "document"
                },
                "fg_evidence_social_security_fund_binder": {
                    "title": "Hồ Sơ Đầu Tư Trái Phiếu Quỹ Bảo Hiểm Xã Hội Việt Nam",
                    "description": "Tập cặp file ba còng mở rộng hiển thị cơ cấu danh mục đầu tư trái phiếu dài hạn bị hao hụt giá trị trước biến động lãi suất thị trường, các nhãn ngăn phân màu, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Institutional Impact Exhibit",
                    "beats": [3, 4, 5],
                    "keywords": ["bảo hiểm xã hội", "quỹ hưu trí", "danh mục", "đầu tư", "trái phiếu"],
                    "type": "document"
                },
                "fg_evidence_special_refinancing_order": {
                    "title": "Quyết Định Cho Vay Tái Cấp Vốn Đặc Biệt của Ngân Hàng Nhà Nước Mộc Đỏ",
                    "description": "Quyết định hành chính chính thức của Thống đốc về việc can thiệp cho vay tái cấp vốn đặc biệt ổn định thanh khoản, tiêu ngữ quốc gia sắc nét, dấu mộc đỏ tươi giáp lai mép giấy, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "State Intervention Order",
                    "beats": [4, 5],
                    "keywords": ["tái cấp vốn", "quyết định", "can thiệp", "mộc đỏ", "nhnn"],
                    "type": "document"
                },
                "fg_evidence_statutory_budget_law_codex": {
                    "title": "Bộ Luật Quản Lý Nợ Công & Luật Ngân Sách Nhà Nước Bìa Da Đỏ",
                    "description": "Bộ luật bìa da đỏ in quốc huy vàng bóng loáng mở ra trang điều khoản quy định trần nợ công và giới hạn thâm hụt ngân sách quốc gia, góc giấy sắc nét, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Statutory Authority",
                    "beats": [1, 2, 5],
                    "keywords": ["luật", "ngân sách", "nợ công", "trần nợ", "pháp luật"],
                    "type": "document"
                },
                "fg_evidence_insolvency_restructuring_docket": {
                    "title": "Đơn Yêu Cầu Mở Thủ Tục Phá Sản & Tái Cơ Cấu Nợ Tòa Án Nhân Dân",
                    "description": "Hồ sơ thụ lý vụ việc phục hồi kinh doanh và tái cấu trúc tài chính nợ của Tòa án nhân dân, tiêu ngữ quốc gia và dấu mộc đỏ của Tòa án, chất liệu giấy hồ sơ dày dặn, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Lead Prosecution Docket",
                    "beats": [1, 4, 5],
                    "keywords": ["tòa án", "phá sản", "tái cơ cấu", "hồ sơ", "mộc đỏ"],
                    "type": "document"
                },
                "fg_evidence_judicial_gavel_sounding_block": {
                    "title": "Búa Gỗ Xét Xử Tòa Án & Cán Cân Công Lý Bằng Đồng",
                    "description": "Búa gỗ xét xử bằng gỗ gụ đánh bóng đặt trên đế gỗ bên cạnh cán cân công lý bằng đồng thau, chất gỗ tự nhiên chân thực, không khí pháp đình uy nghiêm, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Judicial Climax Artifact",
                    "beats": [4, 5],
                    "keywords": ["búa gỗ", "tòa án", "cán cân", "công lý", "phán quyết"],
                    "type": "evidence_prop"
                }
            }
            return bg_roster, fg_roster

        else:
            # Default Global / EN Financial Macro Sovereign Debt
            bg_roster = {
                "bg_central_bank_trading_floor": {
                    "title": "Central Bank Open Market Trading Floor",
                    "description": "Expansive architectural wide shot of central bank open market execution floor, multiple curved multi-monitor desks displaying desaturated yield curves, towering stone columns with dramatic diffused daylight, serious macroeconomic regulatory atmosphere, clean negative space.",
                    "beats": [1, 4]
                },
                "bg_sovereign_bond_auction_gallery": {
                    "title": "Sovereign Bond Syndicate Auction Hall",
                    "description": "Grand institutional auction hall with rows of mahogany dealer desks facing muted digital debt bidding boards, dramatic high-contrast chiaroscuro lighting, subtle dust motes in sunbeams, dignified financial sovereign setting.",
                    "beats": [1, 3]
                },
                "bg_financial_district_night_skyline": {
                    "title": "Nocturnal Financial District High-Rise Overlook",
                    "description": "Dramatic wide view from executive terrace overlooking nocturnal skyscraper canyon, illuminated office windows receding into cold foggy blue night, dark sleek stone ledge in foreground, quiet tension of global finance.",
                    "beats": [1, 5]
                },
                "bg_treasury_briefing_room": {
                    "title": "Ministry of Finance & Treasury Briefing Room",
                    "description": "Formal oak-paneled fiscal policy briefing chamber, long polished table reflecting warm overhead downlights, national crest in deep background soft focus, austere institutional authority.",
                    "beats": [1, 2]
                },
                "bg_post_crisis_fiscal_summit_chamber": {
                    "title": "International Fiscal Stabilization Summit Hall",
                    "description": "Panoramic horseshoe conference hall for sovereign debt ministers, minimalist translation audio consoles, rich dark acoustic wood textures, formal multilateral negotiations mood.",
                    "beats": [2, 3]
                },
                "bg_treasury_vault_corridor": {
                    "title": "Sovereign Bullion & Secure Reserve Vault Corridor",
                    "description": "Deep perspective corridor of reinforced steel archival vault doors, cool industrial concrete walls, overhead fluorescent security lighting casting rhythmic shadows, heavy vault atmosphere.",
                    "beats": [2, 4]
                },
                "bg_historical_bank_boardroom": {
                    "title": "Heritage Central Bank Executive Council Chamber",
                    "description": "Vintage heritage boardroom with coffered timber ceilings, oil portraits in soft focus background, dark mahogany council table, solemn historical financial gravity.",
                    "beats": [2, 3]
                },
                "bg_academic_economics_lecture_hall": {
                    "title": "University Macroeconomic Policy Amphitheater",
                    "description": "Steep tiered wooden university lecture hall, chalkboards in soft background covered with faint mathematical differential equations, warm directional spot lighting, analytical scholarly atmosphere.",
                    "beats": [2, 5]
                },
                "bg_imf_analytical_bullpen": {
                    "title": "Multilateral Monetary Policy Research Bullpen",
                    "description": "Spacious analytical bullpen with desks piled with tabbed sovereign debt dossiers, glowing Bloomberg terminals in soft focus, slate-colored partitions, intense forensic research atmosphere.",
                    "beats": [3, 4]
                },
                "bg_sovereign_debt_archive_records_vault": {
                    "title": "National Debt Management Archival Records Vault",
                    "description": "Endless rows of steel shelving containing uniform archival debt registry boxes, clean polished epoxy floor, cool white downlighting, forensic paper trail discovery setting.",
                    "beats": [3, 4]
                },
                "bg_bloomberg_analytics_terminal_room": {
                    "title": "Financial Market Quantitative Analytics Center",
                    "description": "Dark analytical operations room with high-density workstation displays showing desaturated repo matrices and sovereign CDS heatmaps, muted amber and cyan indicator lights, intense forensic mood.",
                    "beats": [3, 4]
                },
                "bg_debt_management_office": {
                    "title": "Sovereign Debt Issuance Execution Office",
                    "description": "Quiet executive operations office, desk lamp casting warm circular pool of light over debt rollover maturity schedules, city skyline outside window at dusk, focused fiscal tension.",
                    "beats": [3, 5]
                },
                "bg_emergency_finance_ministry_war_room": {
                    "title": "Emergency Liquidity Crisis War Room",
                    "description": "Urgent government crisis coordination room, whiteboards covered with debt maturity timelines and interbank swap diagrams, scattered coffee cups on meeting table, high-stakes institutional stress.",
                    "beats": [4, 5]
                },
                "bg_distressed_bank_trading_pit": {
                    "title": "Commercial Bank Fixed-Income Dealing Room",
                    "description": "Quiet after-hours dealing floor with abandoned trader terminals showing red yield spikes, dim emergency lighting, deep shadows between rows of monitors, aftermath of liquidity shock.",
                    "beats": [4]
                },
                "bg_nocturnal_sovereign_wealth_office": {
                    "title": "Sovereign Wealth Management Office at Dawn",
                    "description": "Corner executive office with floor-to-ceiling glass catching early morning indigo and amber dawn light over harbor, sleek minimalist desk, profound institutional isolation.",
                    "beats": [4, 5]
                },
                "bg_parliament_budget_committee_hall": {
                    "title": "Parliamentary Public Accounts Oversight Hall",
                    "description": "Formal semicircular legislative committee chamber, carved walnut witness tables in foreground, elevated committee dais in background soft focus, dignified democratic scrutiny.",
                    "beats": [4, 5]
                },
                "bg_global_economic_forum_hall": {
                    "title": "Global Economic Governance Assembly Hall",
                    "description": "Vast futuristic auditorium with dark acoustic wall panels, subtle uplighting along tiered seats, empty speaker lectern in clean focus, sweeping monumental perspective.",
                    "beats": [1, 5]
                },
                "bg_executive_reading_library": {
                    "title": "Central Bank Presidential Research Library",
                    "description": "Quiet double-height institutional library with floor-to-ceiling leather-bound statutory ledgers, spiral brass reading staircase, green banker lamps on dark oak tables, reflective analytical stillness.",
                    "beats": [1, 5]
                }
            }
            fg_roster = {
                "fg_character_central_bank_governor": {
                    "title": "Central Bank Monetary Authority",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a senior central bank governor in tailored charcoal formal suit, standing with composed authoritative posture, holding official monetary policy brief, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, 1:1 aspect ratio.",
                    "role": "Monetary Authority",
                    "beats": [1, 4, 5],
                    "keywords": ["governor", "central bank", "fed", "monetary", "rate hike", "policy", "thống đốc", "ngân hàng trung ương"],
                    "type": "character"
                },
                "fg_character_sovereign_bond_trader": {
                    "title": "Sovereign Fixed-Income Desk Head",
                    "description": "Full-body stylized editorial graphic novel digital illustration of an intense sovereign bond trader in crisp white shirt with rolled-up sleeves and dark trousers, reviewing printed yield curve slips with urgent skeptical gaze, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, 1:1 aspect ratio.",
                    "role": "Market Actor",
                    "beats": [1, 2, 4],
                    "keywords": ["trader", "bond desk", "yield", "spread", "market", "dealer", "nhà giao dịch", "trái phiếu"],
                    "type": "character"
                },
                "fg_character_treasury_fiscal_official": {
                    "title": "Treasury Debt Management Director",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a senior government debt management official in dark navy blazer and spectacles, holding tabbed sovereign borrowing forecast binder, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, 1:1 aspect ratio.",
                    "role": "Fiscal Architect",
                    "beats": [2, 3, 5],
                    "keywords": ["treasury", "fiscal", "deficit", "borrowing", "issuance", "kho bạc", "ngân sách"],
                    "type": "character"
                },
                "fg_character_macro_auditor": {
                    "title": "Forensic Macroeconomic Sovereign Debt Auditor",
                    "description": "Full-body stylized editorial graphic novel digital illustration of a meticulous sovereign debt auditor in gray trench coat, holding heavy forensic dossier and magnifying loupe, stern analytical expression, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, 1:1 aspect ratio.",
                    "role": "Forensic Investigator",
                    "beats": [3, 4, 5],
                    "keywords": ["auditor", "investigator", "imf", "scrutiny", "finding", "kiểm toán", "thanh tra"],
                    "type": "character"
                },
                "fg_evidence_sovereign_treasury_bond": {
                    "title": "Official Sovereign 10-Year Treasury Bond Certificate",
                    "description": "Official 300gsm fibrous paper sovereign government bond certificate with intricate guilloche security borders, bold coupon yield rate heading, stamped diagonally with official vermilion treasury seal, crisp cutout edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Core Debt Exhibit",
                    "beats": [1, 2, 3],
                    "keywords": ["bond", "treasury", "yield", "coupon", "certificate", "trái phiếu", "kho bạc", "10-year"],
                    "type": "document"
                },
                "fg_evidence_debt_maturity_wall_chart": {
                    "title": "Macro Debt Maturity Rollover Wall Chart",
                    "description": "High-contrast quantitative bar graph document printed on heavy cardstock, illustrating the impending trillion-dollar debt maturity rollover wall across 2026-2029, highlighted in fluorescent green and red marker ink, crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Quantitative Maturity Proof",
                    "beats": [1, 3, 4],
                    "keywords": ["maturity", "rollover", "wall", "cliff", "refinance", "đáo hạn", "tái cấp vốn", "chart"],
                    "type": "data_metric"
                },
                "fg_evidence_central_bank_balance_sheet": {
                    "title": "Central Bank Balance Sheet Expansion Ledger",
                    "description": "Worn double-page central bank accounting ledger displaying ballooning asset holdings, quantitative easing and repo facilities in muted green ink, red verification checkmarks, tactile paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Monetary Expansion Evidence",
                    "beats": [1, 2, 4],
                    "keywords": ["balance sheet", "assets", "reserves", "qe", "qt", "expansion", "bảng cân đối"],
                    "type": "document"
                },
                "fg_evidence_sovereign_credit_downgrade_notice": {
                    "title": "Credit Rating Agency Sovereign Downgrade Letter",
                    "description": "Official formal rating advisory letter from credit agency, bold header stamped in red ink 'DOWNGRADED // OUTLOOK NEGATIVE', bold black typewriter font detailing fiscal debt overhang, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sovereign Rating Exhibit",
                    "beats": [2, 4, 5],
                    "keywords": ["rating", "downgrade", "moody", "fitch", "s&p", "credit", "xếp hạng", "hạ bậc"],
                    "type": "document"
                },
                "fg_evidence_imf_debt_sustainability_matrix": {
                    "title": "IMF Debt-to-GDP Sustainability Framework Matrix",
                    "description": "Technical macroeconomic assessment document featuring multi-column debt-to-GDP projection tables, colored risk threshold heatmaps, official institutional header, sharp clean paper edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Sustainability Framework",
                    "beats": [3, 4, 5],
                    "keywords": ["imf", "gdp", "sustainability", "ratio", "framework", "matrix", "tỷ lệ gdp"],
                    "type": "data_metric"
                },
                "fg_evidence_currency_swap_facility_agreement": {
                    "title": "Bilateral Central Bank Currency Swap Agreement",
                    "description": "Thick legal bilateral treaty contract document, multiple pages stapled at top left with blue brass eyelet, blue ballpoint signature lines and embossed institutional seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Liquidity Mechanism Accord",
                    "beats": [2, 3, 4],
                    "keywords": ["swap", "currency", "liquidity", "foreign exchange", "agreement", "hoán đổi", "ngoại hối"],
                    "type": "document"
                },
                "fg_evidence_repo_rate_transaction_ticket": {
                    "title": "Overnight Repo Facility Repurchase Ticket",
                    "description": "Small tactile transaction slip on yellow carbon-copy paper with perforated edges, showing overnight repo rate interest calculations and collateralized bond numbers, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Interbank Liquidity Exhibit",
                    "beats": [2, 3, 4],
                    "keywords": ["repo", "repurchase", "overnight", "ticket", "collateral", "chiết khấu"],
                    "type": "document"
                },
                "fg_evidence_inflation_cpi_breakdown_ledger": {
                    "title": "Consumer Price Index Inflation Ledger Slip",
                    "description": "Official statistical bureau price index ledger sheet displaying escalating headline CPI numbers, red circled inflation metrics, crisp fibrous paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Inflation Metric Exhibit",
                    "beats": [1, 2, 5],
                    "keywords": ["inflation", "cpi", "price", "index", "purchasing power", "lạm phát", "giá cả"],
                    "type": "document"
                },
                "fg_evidence_g7_finance_communique": {
                    "title": "G7 Finance Ministers Sovereign Debt Resolution Accord",
                    "description": "Formal multilateral joint communique on heavy diplomatic letterhead, official emblem at top, embossed gold foil seal, diplomatic clauses regarding debt restructuring, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Multilateral Policy Exhibit",
                    "beats": [4, 5],
                    "keywords": ["g7", "ministers", "communique", "resolution", "accord", "thông cáo"],
                    "type": "document"
                },
                "fg_evidence_liquidity_crisis_redacted_memo": {
                    "title": "Confidential Emergency Interbank Liquidity Memo",
                    "description": "Manila folder document stamped 'STRICTLY CONFIDENTIAL // GOVERNORS EYES ONLY', heavy black redaction marker bars over vulnerable bank reserve numbers, official paperclips, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Classified Risk Memo",
                    "beats": [3, 4],
                    "keywords": ["emergency", "liquidity", "confidential", "secret", "memo", "redacted", "khẩn cấp"],
                    "type": "document"
                },
                "fg_evidence_damages_calculation_invoice": {
                    "title": f"Forensic Interest Servicing Cost Calculation Sheet ({metric_highlight})",
                    "description": f"Government audit summary invoice document displaying bold figure '{metric_highlight}' in green ledger ink, stamped diagonally with bold red ink 'CONFIDENTIAL / EXHIBIT A', crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Forensic Accounting Exhibit",
                    "beats": [1, 3, 5],
                    "keywords": ["invoice", "interest expense", "service", "cost", "calculation", "bill", "chi phí lãi"],
                    "type": "document"
                },
                "fg_evidence_sovereign_cds_spread_ticket": {
                    "title": "Sovereign Credit Default Swap Pricing Slip",
                    "description": "High-finance derivative order confirmation ticket, showing surging basis point credit default swap premiums, stamped with red ink 'CRITICAL EXPOSURE', isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Market Default Pricing",
                    "beats": [3, 4],
                    "keywords": ["cds", "default", "spread", "derivative", "swap", "vỡ nợ"],
                    "type": "document"
                },
                "fg_evidence_foreign_exchange_reserve_certificate": {
                    "title": "Official Sovereign Foreign Exchange & Bullion Audit Certificate",
                    "description": "Official central treasury certificate documenting official gold bullion holdings and foreign reserve currency allocations, stamped with official gold star seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Reserve Backing Exhibit",
                    "beats": [2, 3, 5],
                    "keywords": ["reserve", "gold", "bullion", "forex", "foreign exchange", "dự trữ ngoại hối"],
                    "type": "document"
                },
                "fg_evidence_pension_fund_asset_audit_binder": {
                    "title": "Institutional Pension Fund Fixed-Income Allocation Binder",
                    "description": "Thick three-ring binder open on desk showing asset allocation pie charts losing principal value to high interest yields, colored plastic tab dividers, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Institutional Impact Exhibit",
                    "beats": [3, 4, 5],
                    "keywords": ["pension", "fund", "allocation", "yield", "binder", "hưu trí", "quỹ đầu tư"],
                    "type": "document"
                },
                "fg_evidence_emergency_recapitalization_order": {
                    "title": "Executive Statutory Liquidity Intervention Order",
                    "description": "Formal executive decree on government letterhead signed with blue fountain pen ink, authorising emergency sovereign treasury backstops and recapitalisation funds, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "State Intervention Order",
                    "beats": [4, 5],
                    "keywords": ["order", "statutory", "executive", "bailout", "recapitalization", "can thiệp"],
                    "type": "document"
                },
                "fg_evidence_statute_reference_book": {
                    "title": "Monetary Code & Statutory Debt Ceiling Reference Codex",
                    "description": "Heavy vintage leather-bound legal codex open to statutory debt limit and central bank charter sections, gold leaf lettering on spine, crisp cream paper edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Statutory Authority",
                    "beats": [1, 2, 5],
                    "keywords": ["statute", "law", "code", "ceiling", "reference", "trần nợ", "luật ngân sách"],
                    "type": "document"
                },
                "fg_evidence_prosecution_complaint_docket": {
                    "title": "Official Sovereign Debt Default Legal Filing Docket",
                    "description": "Official legal filing document from the international arbitration court, bold case docket header, stamped with blue official seal, crisp document paper texture with clean sharp edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Lead Prosecution Docket",
                    "beats": [1, 4, 5],
                    "keywords": ["docket", "complaint", "default", "legal", "filing", "khởi kiện", "hồ sơ pháp lý"],
                    "type": "document"
                },
                "fg_evidence_gavel_justice_scale": {
                    "title": "Judicial Sovereign Restructuring Climax Gavel & Scales",
                    "description": "Dark polished walnut judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.",
                    "role": "Judicial Climax Artifact",
                    "beats": [4, 5],
                    "keywords": ["gavel", "scales", "judge", "court", "verdict", "búa gỗ", "phán quyết"],
                    "type": "evidence_prop"
                }
            }
            return bg_roster, fg_roster

    # =========================================================================
    # GENERAL INVESTIGATIVE / CORPORATE / REGULATORY FALLBACK (BY MARKET)
    # =========================================================================
    if m_up in ["JP", "JA"]:
        bg_roster = {
            "bg_district_court_hall": {"title": "Tokyo District Courthouse Grand Hall", "description": "Cinematic wide-angle interior of Japanese district courthouse judicial hall, classical stone colonnade, high vaulted ceiling with moody diffused daylight, quiet austere judicial atmosphere, uncluttered background without distracting crowds.", "beats": [1, 5]},
            "bg_regulatory_inspection_lab": {"title": "Ministry & Quarantine Safety Analysis Laboratory", "description": "Modern chemical residue and food safety inspection laboratory, stainless steel workbenches, analytical spectrometry apparatus in soft background focus, cool fluorescent lighting, sterile documentary atmosphere.", "beats": [2, 3]},
            "bg_executive_boardroom_dusk": {"title": "Corporate Executive Boardroom Overlooking Tokyo at Dusk", "description": "Minimalist Japanese corporate executive boardroom overlooking evening city skyline, dark polished cedar table reflection, clean architectural lines, zero clutter, serious institutional tension.", "beats": [1, 4]},
            "bg_warehouse_distribution_office": {"title": "Regional Warehouse Logistics Office", "description": "Authentic commercial distribution logistics office, stacked shipping crates in soft focus background, warm overhead industrial lamp casting gentle pool of light on paperwork desk, clean documentary mood.", "beats": [1, 2, 4]},
            "bg_investigative_newsroom_night": {"title": "Investigative Journalism Newsroom at Night", "description": "Nocturnal investigative newsroom with dark empty desks receding into soft shadows, warm desk lamp pools, distant city lights through blinds, serious quiet investigative atmosphere.", "beats": [1, 2, 3]},
            "bg_forensic_archive_vault": {"title": "Government Institutional Archive Document Vault", "description": "Steel shelving units holding hundreds of uniform archival document storage boxes in deep linear perspective, clean concrete floor, cool downlighting, forensic discovery vault.", "beats": [3, 4]},
            "bg_regulatory_hearing_chamber": {"title": "Ministry Regulatory Oversight Hearing Chamber", "description": "Formal oak-paneled legislative and administrative hearing room with committee bench in background soft focus, rich timber textures, dignified institutional setting.", "beats": [4, 5]},
            "bg_municipal_quarantine_site": {"title": "Port Customs Quarantine Facility Site", "description": "Port customs inspection terminal hall, industrial concrete flooring, official barrier gates in soft focus, quiet authoritative regulatory setting.", "beats": [2, 3]},
            "bg_tokyo_customs_inspection_hall": {"title": "Tokyo Port Customs Clearance Inspection Hall", "description": "Wide customs terminal hall with steel counters, official inspection barriers in background, industrial daylight, authoritative border control atmosphere.", "beats": [1, 2]},
            "bg_kasumigaseki_ministry_corridor": {"title": "Kasumigaseki Government Ministry Corridor", "description": "Long austere government ministry hallway, polished terrazzo floor, tall wooden doors with brass room numbers, quiet bureaucratic gravity.", "beats": [2, 4]},
            "bg_shinjuku_financial_boardroom": {"title": "Shinjuku Financial Tower Executive Chamber", "description": "High-altitude corporate boardroom overlooking Mount Fuji at dusk, dark mahogany table, sleek modern lighting, high corporate tension.", "beats": [3, 4]},
            "bg_yokohama_port_logistics_office": {"title": "Yokohama Port Maritime Shipping Logistics Office", "description": "Maritime dispatch office overlooking cargo container cranes through rainy window pane, desk maps, tactile documentary atmosphere.", "beats": [2, 3]},
            "bg_metropolitan_police_investigative_hq": {"title": "Metropolitan Police Special Investigation Headquarters", "description": "Nocturnal police taskforce briefing room, whiteboards with suspect timeline flowcharts, warm desk spotlights, focused detective mood.", "beats": [3, 4]},
            "bg_consumer_affairs_agency_briefing_room": {"title": "Consumer Affairs Agency Press Briefing Room", "description": "Formal government press conference room, blue backdrop banner with Japanese seal, rows of empty reporter chairs in soft focus, solemn transparency.", "beats": [4, 5]},
            "bg_national_diet_committee_room": {"title": "National Diet Judicial Oversight Committee Hall", "description": "Historic Diet building committee room with carved wood wainscoting, green baize witness table, dignified legislative scrutiny.", "beats": [4, 5]},
            "bg_tokyo_district_archive_vault": {"title": "Tokyo District Judicial Evidence Archive Vault", "description": "Reinforced steel evidence vault with labeled brown cardboard litigation boxes, heavy vault door ajar in background, archival authenticity.", "beats": [3, 5]},
            "bg_marunouchi_commercial_headquarters": {"title": "Marunouchi Commercial Tower Executive Lobby", "description": "Quiet monumental lobby of historic Tokyo business headquarters, polished granite columns, filtered natural morning light, dignified commercial scale.", "beats": [1, 2]},
            "bg_tokyo_high_court_bench": {"title": "Tokyo High Court Appellate Chamber", "description": "Formal high court courtroom with elevated judicial bench in polished cedar, Japanese national seal in deep focus, solemn final reckoning atmosphere.", "beats": [4, 5]}
        }
        fg_roster = {
            "fg_character_tokyo_district_prosecutor": {"title": "Tokyo District Public Prosecutor", "description": "Full-body stylized editorial graphic novel digital illustration of a sharp Japanese public prosecutor in tailored dark suit with prosecutor autumn-frost badge on lapel, holding official filing folder, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Prosecutor", "beats": [1, 4, 5], "keywords": ["prosecutor", "court", "indictment", "検察官", "起訴", "裁判"], "type": "character"},
            "fg_character_ministry_safety_inspector": {"title": "Ministry Food & Safety Lead Inspector", "description": "Full-body stylized editorial graphic novel digital illustration of a diligent Japanese ministry quarantine inspector in navy administrative uniform with ministry identification armband, holding inspection checklist, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Regulatory Inspector", "beats": [1, 2, 3], "keywords": ["inspector", "quarantine", "ministry", "検査官", "厚生労働省"], "type": "character"},
            "fg_character_corporate_director": {"title": "Corporate Compliance Managing Director", "description": "Full-body stylized editorial graphic novel digital illustration of a conflicted Japanese corporate director in crisp white shirt and dark trousers, bowing slightly in formal apology posture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Corporate Executive", "beats": [2, 4], "keywords": ["director", "executive", "apology", "役員", "企業"], "type": "character"},
            "fg_character_forensic_auditor": {"title": "Forensic Financial Accounting Auditor", "description": "Full-body stylized editorial graphic novel digital illustration of a focused Japanese auditor holding a thick ledger and red verification pen, spectacles reflecting desk light, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Auditor", "beats": [3, 4, 5], "keywords": ["auditor", "accounting", "ledger", "監査", "会計"], "type": "character"},
            "fg_character_whistleblower_insider": {"title": "Corporate Whistleblower Insider", "description": "Full-body stylized editorial graphic novel digital illustration of a cautious Japanese company employee in business casual jacket, holding confidential manila envelope, resolute watchful expression, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower Insider", "beats": [2, 3, 4], "keywords": ["whistleblower", "insider", "告発者", "社員", "証言"], "type": "character"},
            "fg_evidence_hanko_stamped_docket": {"title": "Official Vermilion Hanko Stamped Legal Docket", "description": "Official Japanese district court legal filing document, titled prosecution complaint docket, bold Japanese kanji header, stamped with official red vermilion hanko seal, crisp document paper texture with clean sharp edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Prosecution Docket", "beats": [1, 2, 5], "keywords": ["hanko", "docket", "complaint", "kanji", "seal", "判子", "訴状"], "type": "document"},
            "fg_evidence_chemical_residue_inspection_sheet": {"title": f"Official Safety Inspection Analysis Sheet ({metric_highlight})", "description": f"Government accredited laboratory test certificate showing quantitative chemical analysis results with metric highlight '{metric_highlight}', red verification stamp, Japanese kanji column headers, crisp cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Inspection Exhibit", "beats": [1, 2, 3], "keywords": ["inspection", "chemical", "residue", "analysis", "lab", "検査", "分析"], "type": "document"},
            "fg_evidence_damage_calculation_invoice": {"title": "Macro Economic Restitution & Damages Calculation Sheet", "description": "Official audit summary invoice document displaying highlighted financial calculation figures in green ledger ink, stamped diagonally with bold red ink '証拠物件 // 第1号' (EXHIBIT A), crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Accounting Exhibit", "beats": [1, 4, 5], "keywords": ["damage", "invoice", "restitution", "loss", "損害", "賠償", "請求書"], "type": "document"},
            "fg_evidence_quarantine_customs_certificate": {"title": "Official Port Customs Quarantine Certificate", "description": "Port customs import entry clearance form with official inspection stamps, Japanese kanji column headers, tabbed colored sticker, tactile paper creases, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Border Compliance Exhibit", "beats": [2, 3], "keywords": ["quarantine", "customs", "port", "clearance", "通関", "検疫"], "type": "document"},
            "fg_evidence_investigative_audit_binder": {"title": "Government Forensic Investigation Audit Binder", "description": "Thick three-ring binder with navy vinyl cover and clear spine label in Japanese kanji '特別監査調書', tabbed colored dividers visible, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Core Investigative Dossier", "beats": [3, 4, 5], "keywords": ["binder", "audit", "investigation", "dossier", "監査調書"], "type": "document"},
            "fg_evidence_corporate_accounting_ledger": {"title": "Business Financial Accounting Ledger", "description": "Worn merchant bookkeeping ledger notebook open on a wooden table, showing ascending cost charges eroding profit margins, red hanko approval stamps, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Commercial Transaction Record", "beats": [1, 2, 4], "keywords": ["ledger", "accounting", "transaction", "book", "帳簿", "元帳"], "type": "document"},
            "fg_evidence_sealed_whistleblower_envelope": {"title": "Confidential Internal Whistleblower Envelope", "description": "Manila envelope stamped with bold red characters '極秘 // 内部告発' (TOP SECRET // WHISTLEBLOWER), partially open revealing folded document with black redacted lines, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower Evidence", "beats": [2, 3], "keywords": ["whistleblower", "envelope", "secret", "confidential", "内部告発", "極秘"], "type": "document"},
            "fg_evidence_statutory_penal_code_book": {"title": "Japanese Penal & Statutory Reference Codex", "description": "Heavy dark-leather bound Japanese law codex open to commercial fraud and public health violation articles, gold kanji lettering on spine, ribbon marker, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Statutory Authority", "beats": [1, 5], "keywords": ["statute", "penal", "law", "code", "六法全書", "法律"], "type": "document"},
            "fg_evidence_forensic_laboratory_sample_vial": {"title": "Official Evidence Sample Container with Barcode", "description": "Clear glass forensic laboratory evidence vial sealed with tamper-evident red security tape, official laboratory barcode label, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Physical Evidence Exhibit", "beats": [2, 3], "keywords": ["sample", "vial", "specimen", "evidence", "証拠品", "検体"], "type": "evidence_prop"},
            "fg_evidence_judicial_gavel_sounding_block": {"title": "Judicial Sounding Block & Verdict Seal", "description": "Polished Japanese cherry-wood judicial gavel resting on round sounding block beside official red court seal, tactile timber grain, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Climax Artifact", "beats": [4, 5], "keywords": ["gavel", "judge", "verdict", "court", "判決", "法廷"], "type": "evidence_prop"},
            "fg_evidence_ministry_recall_order": {"title": "Official Ministry Mandatory Product Recall Order", "description": "Official administrative decree on Ministry of Health labor and welfare letterhead, bold heading '回収命令', official vermilion seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Administrative Enforcement Exhibit", "beats": [4, 5], "keywords": ["recall", "order", "decree", "ministry", "回収命令"], "type": "document"},
            "fg_evidence_customs_clearance_stamp_docket": {"title": "Import Declaration & Customs Tariff Docket", "description": "Multi-page import customs declaration with green tariff stamps and circular inspector approval seals, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Trade Import Exhibit", "beats": [2, 3], "keywords": ["customs", "declaration", "tariff", "import", "輸入申告"], "type": "document"},
            "fg_evidence_internal_meeting_minutes_dossier": {"title": "Executive Board Emergency Meeting Minutes", "description": "Stapled confidential corporate document with bold header '臨時取締役会議事録', margin notes written in pencil, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Corporate Knowledge Exhibit", "beats": [3, 4], "keywords": ["minutes", "meeting", "board", "executive", "議事録"], "type": "document"},
            "fg_evidence_red_sealed_violation_notice": {"title": "Formal Regulatory Violation & Cease Order", "description": "Government violation notice stamped with prominent square red ministerial seal, crisp paper texture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Regulatory Violation Exhibit", "beats": [4, 5], "keywords": ["violation", "notice", "cease", "seal", "違反通知"], "type": "document"},
            "fg_evidence_food_safety_test_report": {"title": "Public Health Environmental Test Certificate", "description": "Official spectrometry test report displaying quantitative safety threshold tables, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Technical Test Proof", "beats": [2, 3], "keywords": ["test", "report", "health", "analysis", "検査成績書"], "type": "document"},
            "fg_evidence_subpoena_search_warrant": {"title": "Tokyo District Court Search & Seizure Warrant", "description": "Official search and seizure warrant document issued by Tokyo District Court, bold kanji heading '差押許可状', stamped with square red vermilion seal, crisp legal paper edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Compulsory Judicial Warrant", "beats": [2, 4], "keywords": ["warrant", "search", "court", "令状", "差押許可状", "家宅捜索"], "type": "document"},
            "fg_evidence_encrypted_usb_drive": {"title": "Forensic Tamper-Evident Digital Storage Drive", "description": "High-durability metallic USB evidence flash drive with serialized forensic police tamper-proof label in Japanese, glowing amber indicator LED, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Digital Evidence Artifact", "beats": [2, 3], "keywords": ["usb", "drive", "data", "digital", "証拠品", "デジタル証拠"], "type": "evidence_prop"}
        }
        return bg_roster, fg_roster

    elif m_up in ["KR", "KO"]:
        bg_roster = {
            "bg_district_court_hall": {"title": "Seoul Central District Courthouse Grand Hall", "description": "Monumental judicial corridor of Seoul Central District Court, marble colonnade, cool modern diffused lighting, solemn authoritative atmosphere.", "beats": [1, 5]},
            "bg_seoul_prosecutors_office": {"title": "Supreme Prosecutors' Office Special Investigation Room", "description": "High-security prosecution interrogation and evidence review office in Seocho-dong, desks stacked with blue legal record boxes, city dusk through blinds.", "beats": [1, 4]},
            "bg_yeouido_financial_boardroom": {"title": "Yeouido Corporate Headquarters Executive Boardroom", "description": "High-altitude corporate boardroom overlooking Han River and National Assembly at dusk, dark granite table, crisp minimalist lines.", "beats": [1, 4]},
            "bg_incheon_customs_logistics_hall": {"title": "Incheon International Airport Customs Cargo Terminal", "description": "Vast industrial cargo inspection warehouse, stainless steel customs counters, automated conveyor belts in soft focus, authoritative regulatory mood.", "beats": [1, 2, 4]},
            "bg_investigative_newsroom_night": {"title": "Seoul Broadcasting Investigative Desk at Night", "description": "Nocturnal newsroom with empty desks, warm desk lamps illuminating evidence binders, Seoul neon reflection on rainy windows.", "beats": [1, 2, 3]},
            "bg_forensic_archive_vault": {"title": "Government Institutional Document Archive Vault", "description": "Steel mobile shelving units holding thousands of uniform gray legal archival binders, cool downlighting, forensic records discovery room.", "beats": [3, 4]},
            "bg_regulatory_hearing_chamber": {"title": "Fair Trade Commission Regulatory Hearing Chamber", "description": "Formal oak-paneled hearing hall in Sejong Government Complex, commissioners' bench in soft focus background, dignified institutional setting.", "beats": [4, 5]},
            "bg_corporate_digital_forensics_lab": {"title": "Digital Forensics & Electronic Discovery Center", "description": "High-tech data recovery laboratory with server diagnostic racks, glowing forensic analysis monitors displaying filesystem trees.", "beats": [2, 3]},
            "bg_sejong_ministry_headquarters": {"title": "Sejong Government Complex Ministry Corridor", "description": "Modern government administrative complex, sleek white marble walls, expansive glass atrium, quiet bureaucratic tension.", "beats": [2, 3]},
            "bg_gangnam_corporate_tower_office": {"title": "Gangnam Technology Enterprise Executive Suite", "description": "Floor-to-ceiling glass executive office overlooking Teheran-ro night traffic, dark walnut desk, severe corporate gravity.", "beats": [2, 4]},
            "bg_national_assembly_hearing_hall": {"title": "National Assembly Parliamentary Audit Chamber", "description": "Iconic semicircular legislative hearing room, microphone consoles in sharp focus, national emblem on mahogany backdrop.", "beats": [4, 5]},
            "bg_port_quarantine_terminal": {"title": "Busan Port Container Inspection Terminal", "description": "Industrial container customs staging yard, shipping cranes in misty background, wet asphalt reflection, cold maritime air.", "beats": [1, 2]},
            "bg_audit_board_investigative_room": {"title": "Board of Audit and Inspection Examination Room", "description": "Formal government audit review suite, long conference table covered with audit dossiers, solemn oversight atmosphere.", "beats": [3, 4]},
            "bg_public_health_research_center": {"title": "National Institute of Food and Drug Safety Analysis Lab", "description": "Sterile scientific analysis facility with chromatography instruments, cool fluorescent lighting, clinical documentary feel.", "beats": [2, 3]},
            "bg_appellate_courtroom_interior": {"title": "Seoul High Court Appellate Chamber", "description": "Formal high court chamber with elevated judicial bench, traditional carved timber trim, solemn legal reckoning.", "beats": [4, 5]},
            "bg_executive_library_archive": {"title": "Supreme Court Legal Library Archive", "description": "Quiet double-height jurisprudence library, rows of bound legal precedents, bronze banker lamps, reflective analytical silence.", "beats": [1, 5]},
            "bg_mapo_police_investigative_squad": {"title": "Seoul Metropolitan Police Financial Investigation Team", "description": "Nocturnal white-collar crime police office, whiteboards with money trail flowcharts, fluorescent task lighting, serious detective mood.", "beats": [2, 3]},
            "bg_jongno_corporate_headquarters_lobby": {"title": "Jongno Historic Corporate Tower Atrium", "description": "Monumental polished granite atrium of major South Korean enterprise, soaring glass facade reflecting twilight city, solemn institutional scale.", "beats": [1, 2]}
        }
        fg_roster = {
            "fg_character_seoul_prosecutor": {"title": "Senior Special Prosecutor", "description": "Full-body stylized editorial graphic novel digital illustration of a resolute Korean senior prosecutor in dark charcoal suit with prosecution emblem pin, holding a thick legal dossier, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Prosecutor", "beats": [1, 4, 5], "keywords": ["prosecutor", "court", "검사", "기소", "검찰"], "type": "character"},
            "fg_character_corporate_sawon": {"title": "Corporate Accounting Manager", "description": "Full-body stylized editorial graphic novel digital illustration of a conflicted Korean corporate manager in crisp white business shirt wearing corporate lanyard ID badge (Sawonjeung), holding financial ledger, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Corporate Insider", "beats": [2, 3, 4], "keywords": ["sawonjeung", "manager", "employee", "사원증", "과장"], "type": "character"},
            "fg_character_regulatory_commissioner": {"title": "Fair Trade Oversight Commissioner", "description": "Full-body stylized editorial graphic novel digital illustration of a senior Korean regulatory commissioner in formal navy attire and glasses, holding an administrative cease order, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Regulatory Commissioner", "beats": [3, 4, 5], "keywords": ["commissioner", "ftc", "위탁", "공정거래위원회"], "type": "character"},
            "fg_character_forensic_auditor": {"title": "Senior Forensic Accounting Auditor", "description": "Full-body stylized editorial graphic novel digital illustration of a Korean forensic accountant holding an audit binder and tablet, analytical sharp gaze, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Auditor", "beats": [2, 3, 5], "keywords": ["auditor", "accountant", "회계사", "감사"], "type": "character"},
            "fg_character_whistleblower_analyst": {"title": "Corporate Risk Whistleblower Analyst", "description": "Full-body stylized editorial graphic novel digital illustration of a conflicted Korean corporate analyst in business casual coat, holding sealed whistleblower file, determined intense gaze, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower", "beats": [2, 3, 4], "keywords": ["whistleblower", "insider", "analyst", "내부고발", "제보자"], "type": "character"},
            "fg_evidence_ingam_stamped_docket": {"title": "Official Red Vermilion Ingam Stamped Legal Filing Docket", "description": "Official Korean district court legal indictment document, bold Korean Hangul header, stamped with circular crimson ingam seal, crisp paper texture with clean sharp edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Prosecution Docket", "beats": [1, 2, 5], "keywords": ["ingam", "docket", "complaint", "indictment", "seal", "인감", "공소장"], "type": "document"},
            "fg_evidence_corporate_sawonjeung_badge": {"title": "Corporate Employee Sawonjeung Identification Card", "description": "Official plastic corporate employee ID badge with lanyard clip, Hangul title '경영지원본부 / 회계팀' (Management Support / Accounting Team), barcode and chip, authentic institutional realism, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Corporate Insider Artifact", "beats": [1, 2, 3], "keywords": ["sawonjeung", "badge", "id", "card", "사원증", "신분증"], "type": "evidence_prop"},
            "fg_evidence_damages_calculation_invoice": {"title": f"Forensic Accounting & Damages Summary Sheet ({metric_highlight})", "description": f"Government audit summary invoice document displaying bold figure '{metric_highlight}' in green ledger ink, stamped diagonally with bold red ink '증거 제1호' (EXHIBIT 1), crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Accounting Exhibit", "beats": [1, 4, 5], "keywords": ["damage", "invoice", "restitution", "손해배상", "세금계산서"], "type": "document"},
            "fg_evidence_regulatory_audit_binder": {"title": "Regulatory Oversight Forensic Audit Dossier", "description": "Heavy three-ring binder labeled in Hangul '특별감사보고서' (Special Audit Report), colored tab dividers, official regulatory growth charts visible, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Core Investigative Dossier", "beats": [3, 4, 5], "keywords": ["binder", "audit", "dossier", "감사보고서"], "type": "document"},
            "fg_evidence_merchant_accounting_ledger": {"title": "Corporate Accounting & Transaction Ledger", "description": "Business bookkeeping ledger notebook open on wooden table showing ascending financial transactions, red verification stamps, sharp paper edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Transaction Evidence", "beats": [1, 2, 4], "keywords": ["ledger", "bookkeeping", "accounting", "장부", "회계"], "type": "document"},
            "fg_evidence_sealed_whistleblower_memo": {"title": "Confidential Internal Whistleblower Memo Envelope", "description": "Manila folder envelope stamped with bold red Hangul '대외비 // 내부고발' (RESTRICTED // WHISTLEBLOWER), partially opened revealing internal memo with black redacted bars across strategic paragraphs, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower Document", "beats": [2, 3], "keywords": ["memo", "whistleblower", "confidential", "내부고발", "대외비"], "type": "document"},
            "fg_evidence_statute_reference_book": {"title": "Korean Commercial & Statutory Legal Codex", "description": "Heavy vintage dark-bound legal codex open to commercial code and antitrust enforcement articles, gold leaf Hangul on spine, ribbon bookmark, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Statutory Authority", "beats": [1, 5], "keywords": ["statute", "law", "codex", "법전", "상법"], "type": "document"},
            "fg_evidence_server_rack_drive": {"title": "Digital Forensic Storage Drive Module", "description": "Enterprise server drive enclosure with flashing blue data activity LEDs, forensic evidence barcode label in Korean and English, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Digital Evidence", "beats": [2, 3], "keywords": ["server", "drive", "data", "digital", "디지털포렌식"], "type": "evidence_prop"},
            "fg_evidence_gavel_justice_scale": {"title": "Judicial Gavel & Sounding Block", "description": "Polished dark wood judicial gavel resting on sounding block beside brass balance scales, courtroom documentary realism, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Climax Artifact", "beats": [4, 5], "keywords": ["gavel", "judge", "scales", "court", "법원", "판결"], "type": "evidence_prop"},
            "fg_evidence_ftc_corrective_order": {"title": "Fair Trade Commission Formal Sanction Decree", "description": "Government sanction order on official Fair Trade Commission letterhead, bold Hangul title '시정명령서', red ministerial seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Regulatory Sanction Exhibit", "beats": [4, 5], "keywords": ["order", "sanction", "ftc", "시정명령"], "type": "document"},
            "fg_evidence_tax_audit_discrepancy_sheet": {"title": "National Tax Service Audit Discrepancy Statement", "description": "Official tax authority assessment slip showing calculated revenue discrepancies and unpaid corporate tax penalties, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Tax Discrepancy Exhibit", "beats": [2, 3], "keywords": ["tax", "discrepancy", "penalty", "국세청", "추징금"], "type": "document"},
            "fg_evidence_bank_transaction_voucher": {"title": "Commercial Bank Wire Transfer Verification Voucher", "description": "Bank transaction voucher slip with dot-matrix printing, official cashier red stamp, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Financial Paper Trail", "beats": [2, 3], "keywords": ["wire", "bank", "voucher", "transfer", "송금확인서"], "type": "document"},
            "fg_evidence_board_resolution_minutes": {"title": "Board of Directors Emergency Resolution Minutes", "description": "Formally bound board meeting minutes document with attendee signatures and red registered seal impressions, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Corporate Minutes Exhibit", "beats": [3, 4], "keywords": ["resolution", "board", "minutes", "이사회", "의사록"], "type": "document"},
            "fg_evidence_forensic_cellphone_extraction_report": {"title": "Mobile Device Digital Extraction Forensic Report", "description": "Official police forensic extraction log showing chat logs and timestamps with highlighted red evidence callouts, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Digital Communication Proof", "beats": [2, 4], "keywords": ["chat", "extraction", "forensic", "phone", "포렌식보고서"], "type": "document"},
            "fg_evidence_prosecution_summons_notice": {"title": "Official Public Prosecution Summons Order", "description": "Formal legal summons notice commanding executive appearance for questioning, red official stamp, crisp paper creases, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Summons Exhibit", "beats": [1, 4], "keywords": ["summons", "notice", "prosecution", "출석요구서"], "type": "document"},
            "fg_evidence_search_seizure_warrant": {"title": "Seoul District Court Search & Seizure Warrant", "description": "Official legal search warrant issued by Seoul Central District Court, titled '압수·수색·검증영장' in bold Hangul, stamped with circular crimson Ingam seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Compulsory Legal Warrant", "beats": [2, 4], "keywords": ["warrant", "search", "court", "영장", "압수수색"], "type": "document"},
            "fg_evidence_corporate_slush_fund_ledger": {"title": "Confidential Corporate Slush Fund Double Ledger", "description": "Tactile handwritten double-entry accounting ledger notebook recording undisclosed corporate accounts, red stamp impressions, yellow highlighter, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Illicit Finance Paper Trail", "beats": [2, 3], "keywords": ["ledger", "slush fund", "accounting", "비자금", "이중장부"], "type": "document"}
        }
        return bg_roster, fg_roster

    elif m_up in ["VN", "VI"]:
        bg_roster = {
            "bg_people_court_grand_hall": {"title": "Tòa Án Nhân Dân Thành Phố Hội Trường Lớn", "description": "Không gian hội trường xét xử của Tòa án nhân dân với quốc huy Việt Nam trên phông đỏ trung tâm, hàng ghế hội đồng xét xử bằng gỗ gụ uy nghiêm, ánh sáng ban ngày khuếch tán qua cửa sổ vòm cao.", "beats": [1, 5]},
            "bg_inspectorate_hearing_room": {"title": "Phòng Họp Thanh Tra Chính Phủ & Ban Nội Chính", "description": "Phòng họp trang trọng với bàn họp dài bằng gỗ xoan đào, cờ đỏ sao vàng ở góc trang trọng, tài liệu thanh tra xếp ngay ngắn, không khí pháp lý nghiêm nghị.", "beats": [4, 5]},
            "bg_corporate_executive_boardroom": {"title": "Phòng Họp Hội Đồng Quản Trị Tập Đoàn", "description": "Phòng họp cao tầng nhìn ra toàn cảnh sông Sài Gòn hoặc hồ Tây lúc hoàng hôn, bàn kính phản chiếu ánh đèn rọi trần, vách gỗ hiện đại sang trọng.", "beats": [1, 4]},
            "bg_customs_logistics_warehouse": {"title": "Kho Hàng Giám Sát Hải Quan & Quản Lý Thị Trường", "description": "Kho hàng vận tải logistics với các kiện hàng xếp lớp phía sau mờ nhẹ, ngọn đèn công nghiệp chiếu rọi xuống bàn làm việc kiểm định giấy tờ.", "beats": [1, 2, 4]},
            "bg_investigative_newsroom_night": {"title": "Tòa Soạn Báo Điều Tra Đêm Khuya", "description": "Không gian phòng biên tập báo chí lúc đêm muộn, bàn làm việc với đèn bàn rọi vào hồ sơ, cửa sổ nhìn ra ánh đèn thành phố mờ sương.", "beats": [1, 2, 3]},
            "bg_state_records_archive_vault": {"title": "Trung Tâm Lưu Trữ Quốc Gia & Kho Hồ Sơ Vụ Án", "description": "Hệ thống giá kệ kim loại chứa hàng trăm hộp lưu trữ hồ sơ tài liệu xếp thẳng tắp, nền bê tông sạch bóng, ánh đèn tuýp trắng mát dịu.", "beats": [3, 4]},
            "bg_market_surveillance_hq": {"title": "Trụ Sở Cục Quản Lý Thị Trường & Kiểm Tra Chuyên Ngành", "description": "Phòng họp tác chiến của cơ quan thanh tra thị trường, bảng sơ đồ mạng lưới phân phối, ánh sáng tập trung nghiêm túc.", "beats": [2, 3]},
            "bg_bank_operations_center": {"title": "Trung Tâm Điều Hành Ngân Hàng & Giao Dịch Tài Chính", "description": "Không gian làm việc ngân hàng hiện đại với màn hình hiển thị biểu đồ dòng tiền mờ nhẹ phía sau, vách kính mờ, không khí phân tích tập trung.", "beats": [2, 3]},
            "bg_ministry_briefing_hall": {"title": "Hội Trường Bộ Ngành Trung Ương", "description": "Hội trường hội nghị bộ ngành với hàng ghế bọc da sẫm màu, bục phát biểu bằng gỗ tự nhiên, không khí hành chính quyền lực.", "beats": [2, 4]},
            "bg_tax_audit_office": {"title": "Phòng Thanh Tra Kiểm Tra Thuế Doanh Nghiệp", "description": "Văn phòng thanh tra thuế với chồng hồ sơ quyết toán tài chính, ánh đèn tuýp sáng rõ, máy tính hiển thị bảng cân đối số liệu.", "beats": [3, 4]},
            "bg_police_investigation_agency": {"title": "Cơ Quan Cảnh Sát Điều Tra Trụ Sở Làm Việc", "description": "Phòng làm việc điều tra viên với bảng dòng thời gian chứng cứ, hồ sơ án tài chính, đèn bàn rọi vào biên bản ghi lời khai.", "beats": [3, 4]},
            "bg_port_quarantine_terminal": {"title": "Cảng Biển Cửa Khẩu Kiểm Định Hàng Hóa", "description": "Khu vực kiểm hóa cảng biển Hải Phòng hoặc Cát Lái, cần cẩu container phía sau mờ nhẹ, mặt sàn công nghiệp mát mẻ.", "beats": [1, 2]},
            "bg_notary_public_office": {"title": "Văn Phòng Công Chứng & Xác Thực Hồ Sơ Đất Đai", "description": "Phòng công chứng tư pháp với kệ sách lưu trữ văn bản pháp luật, dấu mộc đỏ trên bàn làm việc, ánh sáng chân thực.", "beats": [2, 3]},
            "bg_financial_institute_amphitheater": {"title": "Giảng Đường Viện Chiến Lược Kinh Tế", "description": "Hội trường phân tích kinh tế vĩ mô, bảng số liệu biểu đồ dòng tiền phía sau, bầu không khí học thuật chuyên sâu.", "beats": [2, 5]},
            "bg_appellate_courtroom": {"title": "Phòng Xét Xử Phúc Thẩm Tòa Án Cấp Cao", "description": "Phòng xét xử phúc thẩm với bục hội đồng ba thẩm phán, phù hiệu quốc gia trang nghiêm, bầu không khí phán quyết đanh thép.", "beats": [4, 5]},
            "bg_executive_reading_room": {"title": "Thư Viện Pháp Luật & Nghiên Cứu Lịch Sử Tư Pháp", "description": "Thư viện tư pháp yên tĩnh với kệ sách bọc da cổ điển, đèn bàn màu xanh ngọc, không gian chiêm nghiệm sâu lắng.", "beats": [1, 5]},
            "bg_state_audit_headquarters_chamber": {"title": "Trụ Sở Kiểm Toán Nhà Nước & Hội Trường Kết Luận", "description": "Phòng họp hội trường của Kiểm toán Nhà nước với bàn chữ U gỗ tự nhiên, quốc huy trang trọng, hồ sơ quyết toán ngân sách trên bàn, không khí minh bạch thanh liêm.", "beats": [3, 4]},
            "bg_city_financial_district_night": {"title": "Đại Lộ Tài Chính Trung Tâm Thành Phố Về Đêm", "description": "Góc nhìn toàn cảnh trung tâm tài chính Quận 1 hoặc Hoàn Kiếm rực sáng ánh đèn cao ốc trong đêm mù sương, sự tĩnh lặng sâu sắc của trung tâm kinh tế.", "beats": [1, 5]}
        }
        fg_roster = {
            "fg_character_vietnamese_inspector": {"title": "Trưởng Đoàn Thanh Tra Nhà Nước", "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một trưởng đoàn thanh tra trong trang phục thanh tra nhà nước trang trọng, cầm kẹp hồ sơ kết luận thanh tra, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Inspector", "beats": [1, 4, 5], "keywords": ["thanh tra", "kết luận", "cán bộ", "đoàn thanh tra"], "type": "character"},
            "fg_character_corporate_chairperson": {"title": "Chủ Tịch Hội Đồng Quản Trị Tập Đoàn", "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một chủ tịch tập đoàn trong bộ vest tối màu trang trọng, nét mặt căng thẳng kiềm chế trước các chứng cứ tài chính, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Corporate Figure", "beats": [1, 2, 4], "keywords": ["chủ tịch", "hội đồng quản trị", "doanh nghiệp", "tập đoàn"], "type": "character"},
            "fg_character_forensic_auditor": {"title": "Kiểm Toán Viên Trưởng Pháp Y Tài Chính", "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một kiểm toán viên tài chính cầm tập báo cáo kiểm toán độc lập dày cộp, kính gọng kim loại phản chiếu ánh đèn, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Auditor", "beats": [2, 3, 5], "keywords": ["kiểm toán", "tài chính", "dòng tiền", "báo cáo"], "type": "character"},
            "fg_character_investigative_journalist": {"title": "Nhà Báo Điều Tra Chuyên Sâu", "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một nhà báo điều tra cầm sổ tay ghi chép và thẻ nhà báo, ánh mắt sắc sảo truy tìm chân tướng, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Investigative Reporter", "beats": [1, 3, 4], "keywords": ["nhà báo", "phóng viên", "điều tra", "chân tướng"], "type": "character"},
            "fg_character_whistleblower_executive": {"title": "Phó Giám Đốc Đấu Thầu Tố Giác Sai Phạm", "description": "Hình minh họa đồ họa biên tập toàn thân sắc nét của một cựu lãnh đạo doanh nghiệp cầm túi hồ sơ tài liệu mật, ánh mắt kiên định nhưng thận trọng, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower Insider", "beats": [2, 3, 4], "keywords": ["tố giác", "nội bộ", "nhân chứng", "sai phạm", "hồ sơ"], "type": "character"},
            "fg_evidence_moc_do_stamped_docket": {"title": "Kết Luận Thanh Tra Đóng Dấu Mộc Đỏ & Chữ Ký Tươi", "description": "Văn bản kết luận thanh tra chính thức của cơ quan nhà nước, tiêu ngữ quốc gia sắc nét, đóng dấu mộc đỏ tươi hình quốc huy và chữ ký bút mực xanh, chất liệu giấy 300gsm góc cạnh sắc sảo, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Official Docket", "beats": [1, 2, 5], "keywords": ["mộc đỏ", "thanh tra", "kết luận", "dấu đỏ", "quuyết định"], "type": "document"},
            "fg_evidence_damages_calculation_invoice": {"title": f"Bảng Tính Chi Phí Thiệt Hại & Bồi Thường Tài Chính ({metric_highlight})", "description": f"Bảng phụ lục kiểm toán tổng hợp thiệt hại kinh tế hiển thị con số '{metric_highlight}' mực xanh nổi bật, đóng dấu chéo mực đỏ 'TÀI LIỆU CHỨNG CỨ', viền cắt giấy sắc nét, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Accounting Exhibit", "beats": [1, 4, 5], "keywords": ["thiệt hại", "hóa đơn", "bồi thường", "tài chính", "invoice"], "type": "document"},
            "fg_evidence_red_sealed_violation_notice": {"title": "Biên Bản Vi Phạm Hành Chính & Quyết Định Xử Phạt", "description": "Biên bản xử phạt vi phạm hành chính có dấu mộc đỏ của cơ quan chức năng, chữ in vi tính rõ nét, có dấu giáp lai đỏ tươi mép giấy, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Administrative Sanction Exhibit", "beats": [4, 5], "keywords": ["biên bản", "xử phạt", "vi phạm", "mộc đỏ"], "type": "document"},
            "fg_evidence_accounting_ledger": {"title": "Sổ Kế Toán & Báo Cáo Lưu Chuyển Dòng Tiền", "description": "Quyển sổ cái ghi chép giao dịch tài chính dòng tiền mở rộng trên mặt bàn gỗ, hiển thị số liệu thu chi lệch pha, có đánh dấu bút dạ quang vàng, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Accounting Exhibit", "beats": [1, 2, 4], "keywords": ["sổ sách", "kế toán", "dòng tiền", "ledger"], "type": "document"},
            "fg_evidence_sealed_whistleblower_folder": {"title": "Hồ Sơ Tài Liệu Mật Bị Phát Giác", "description": "Túi hồ sơ giấy xi măng màu nâu đóng dấu đỏ 'MẬT // LƯU HÀNH NỘI BỘ', mở hé lộ các tài liệu nội bộ bị gạch đen xóa thông tin nhạy cảm, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower Evidence", "beats": [2, 3], "keywords": ["hồ sơ", "mật", "nội bộ", "tố giác", "memo"], "type": "document"},
            "fg_evidence_statutory_law_codex": {"title": "Bộ Luật Hình Sự & Luật Doanh Nghiệp Hiện Hành", "description": "Sách luật bìa da đỏ in quốc huy vàng bóng loáng mở ra trang điều khoản vi phạm quản lý kinh tế, góc giấy sắc nét, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Statutory Authority", "beats": [1, 5], "keywords": ["luật", "bộ luật", "pháp luật", "statute"], "type": "document"},
            "fg_evidence_server_storage_disk": {"title": "Ổ Đĩa Lưu Trữ Dữ Liệu Thuật Toán Doanh Nghiệp", "description": "Thiết bị ổ cứng kim loại chuyên dụng của hệ thống máy chủ máy chủ doanh nghiệp có dán tem niêm phong bằng chứng điều tra màu cam, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Technical Hardware Evidence", "beats": [2, 3], "keywords": ["ổ đĩa", "dữ liệu", "máy chủ", "server"], "type": "evidence_prop"},
            "fg_evidence_gavel_justice_scale": {"title": "Búa Gỗ Xét Xử Tòa Án & Cán Cân Công Lý", "description": "Búa gỗ xét xử bằng gỗ gụ đánh bóng đặt trên đế gỗ bên cạnh cán cân công lý bằng đồng thau, chất gỗ tự nhiên chân thực, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Climax Artifact", "beats": [4, 5], "keywords": ["búa", "tòa án", "phán quyết", "công lý", "gavel"], "type": "evidence_prop"},
            "fg_evidence_notarized_contract": {"title": "Hợp Đồng Kinh Tế Công Chứng Có Dấu Giáp Lai", "description": "Hợp đồng kinh tế nhiều trang được dập dấu mộc đỏ giáp lai giữa các mép giấy, đóng ghim góc trái, có chữ ký đại diện pháp luật, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Contractual Exhibit", "beats": [2, 3], "keywords": ["hợp đồng", "công chứng", "giáp lai", "contract"], "type": "document"},
            "fg_evidence_bank_statement_slip": {"title": "Sao Kê Tài Khoản Ngân Hàng Dấu Giáp Lai Đỏ", "description": "Tập bảng sao kê tài khoản ngân hàng in kim hiển thị các giao dịch chuyển khoản hàng trăm tỷ đồng, dấu tròn ngân hàng đỏ tươi, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Banking Paper Trail", "beats": [2, 3], "keywords": ["sao kê", "ngân hàng", "giao dịch", "chuyển tiền"], "type": "document"},
            "fg_evidence_forensic_sealing_tape": {"title": "Băng Keo Niêm Phong Tang Vật Pháp Lý", "description": "Dải băng keo giấy niêm phong chính thức có đóng dấu giáp lai đỏ đè lên mép dán thùng tài liệu tang vật, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Seal Exhibit", "beats": [3, 4], "keywords": ["niêm phong", "tang vật", "băng keo", "seal"], "type": "evidence_prop"},
            "fg_evidence_tax_assessment_notice": {"title": "Thông Báo Truy Thu Thuế & Phạt Chậm Nộp", "description": "Văn bản quyết định truy thu thuế và xử phạt vi phạm của Cục Thuế, dấu mộc tròn đỏ của cơ quan thuế, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Tax Penalty Exhibit", "beats": [3, 5], "keywords": ["truy thu", "thuế", "xử phạt", "thông báo"], "type": "document"},
            "fg_evidence_c03_investigation_subpoena": {"title": "Giấy Triệu Tập của Cơ Quan Cảnh Sát Điều Tra", "description": "Giấy triệu tập làm việc chính thức của Cơ quan Cảnh sát điều tra Bộ Công an, có quốc huy và dấu mộc đỏ tươi, chữ ký của Thủ trưởng cơ quan điều tra, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Police Investigation Subpoena", "beats": [2, 4], "keywords": ["triệu tập", "công an", "cảnh sát điều tra", "c03", "mộc đỏ"], "type": "document"},
            "fg_evidence_asset_freeze_decision": {"title": "Quyết Định Phong Tỏa Tài Khoản & Kê Biên Bất Động Sản", "description": "Văn bản pháp lý của Viện kiểm sát nhân dân tối cao về việc phong tỏa tài khoản ngân hàng và kê biên tài sản, đóng dấu mộc đỏ tươi giáp lai, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Asset Freezing Injunction", "beats": [4, 5], "keywords": ["phong tỏa", "kê biên", "viện kiểm sát", "tài khoản", "mộc đỏ"], "type": "document"},
            "fg_evidence_bidding_collusion_matrix": {"title": "Hồ Sơ Chứng Cứ Thông Thầu & Quân Xanh Quân Đỏ", "description": "Bảng sơ đồ ma trận điều tra bóc tách hành vi liên danh thông thầu, đánh dấu bút dạ quang vàng các nhà thầu chân gỗ, đóng dấu tài liệu mật, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Procurement Fraud Exhibit", "beats": [2, 3], "keywords": ["thông thầu", "quân xanh", "đấu thầu", "chân gỗ", "bằng chứng"], "type": "document"},
            "fg_evidence_audit_discrepancy_sheet": {"title": "Bảng Đối Soát Chênh Lệch Dòng Tiền & Rút Ruột Dự Án", "description": "Bảng đối soát kiểm toán độc lập hiển thị số liệu rút ruột vốn nhà nước, cột chênh lệch ghi bằng mực đỏ nổi bật, viền giấy sắc nét, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Audit Discrepancy Exhibit", "beats": [3, 4], "keywords": ["đối soát", "chênh lệch", "rút ruột", "kiểm toán", "dòng tiền"], "type": "document"},
            "fg_evidence_land_notarized_title_deed": {"title": "Giấy Chứng Nhận Quyền Sử Dụng Đất (Sổ Đỏ) Có Dấu Giáp Lai", "description": "Giấy chứng nhận quyền sử dụng đất bìa hồng đỏ chính thức có phôi bảo an quốc gia, đóng dấu mộc tròn đỏ của Sở Tài nguyên & Môi trường, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Real Estate Title Exhibit", "beats": [1, 2], "keywords": ["sổ đỏ", "đất đai", "bất động sản", "chứng nhận", "mộc đỏ"], "type": "document"}
        }
        return bg_roster, fg_roster

    else:
        # Default EN Corporate / Regulatory Fallback
        bg_roster = {
            "bg_federal_court_hall": {"title": "Federal Courthouse Grand Hall", "description": "Cinematic wide-angle interior of federal courthouse hall, classical stone colonnade, high vaulted ceiling with moody diffused daylight, quiet austere judicial atmosphere, uncluttered background without distracting crowds.", "beats": [1, 5]},
            "bg_regulatory_oversight_chamber": {"title": "Regulatory Oversight Analytical Hearing Chamber", "description": "Formal oak-paneled federal hearing room with elevated judge bench in background soft focus, rich timber textures, formal dignified institutional setting.", "beats": [4, 5]},
            "bg_executive_boardroom_dusk": {"title": "Corporate Executive Boardroom at Dusk", "description": "Modern minimalist corporate boardroom overlooking dusky city skyline through panoramic floor-to-ceiling glass windows, dark mahogany table reflection, clean architectural lines, zero clutter.", "beats": [1, 4]},
            "bg_enterprise_warehouse_office": {"title": "Enterprise Operations Logistics Office", "description": "Authentic quiet business inventory office, cardboard shipping boxes neatly stacked in soft focus background, warm overhead industrial lamp casting gentle pool of light on desk, clean documentary mood.", "beats": [1, 2, 4]},
            "bg_investigative_newsroom_night": {"title": "Investigative Journalism Newsroom at Night", "description": "Nocturnal newsroom with dark empty desks receding into soft shadows, warm desk lamp pools, distant city lights through blinds, serious quiet investigative atmosphere.", "beats": [1, 2, 3]},
            "bg_forensic_archive_vault": {"title": "Federal Archive Document Vault", "description": "Steel shelving units holding hundreds of uniform gray legal archive boxes in deep linear perspective, clean concrete floor, cool fluorescent downlighting, forensic discovery vault.", "beats": [3, 4]},
            "bg_economics_analytics_lab": {"title": "Marketplace Economics & Data Analytics Lab", "description": "Modern analytical workspace with large soft-focus monitors displaying muted auction bidding flowcharts and heatmaps, dark slate walls, focused analytical atmosphere.", "beats": [2, 3]},
            "bg_server_cooling_facility": {"title": "Enterprise Cloud Data Center Facility", "description": "Deep perspective corridor of enterprise server racks in dark cooling room, subtle vertical cyan and amber LED tracer lights, clean floor reflection, atmospheric mist, uncluttered clean industrial tech environment.", "beats": [2, 3]},
            "bg_corporate_headquarters_atrium": {"title": "Corporate Glass Atrium at Twilight", "description": "Vast minimalist architectural corporate atrium, towering cantilevered glass walls, sleek granite floor reflecting twilight city sky, monumental scale.", "beats": [1, 2]},
            "bg_compliance_audit_room": {"title": "Internal Corporate Compliance Review Suite", "description": "Focused internal audit room with desks covered in organized evidence folders, warm directional task lighting, slate gray acoustic walls, serious institutional tone.", "beats": [2, 3]},
            "bg_legislative_hearing_rotunda": {"title": "Congressional Committee Hearing Rotunda", "description": "Curved neoclassical rotunda hearing room with mahogany witness tables in foreground, elevated committee dais in background, dignified congressional scrutiny.", "beats": [4, 5]},
            "bg_nocturnal_city_overlook": {"title": "Nocturnal Metropolis Financial Center Overlook", "description": "Expansive view from executive office balcony overlooking illuminated financial skyscrapers shrouded in evening mist, profound quiet scale.", "beats": [1, 5]},
            "bg_logistics_shipping_terminal": {"title": "Maritime Commercial Logistics Dock", "description": "Quiet commercial shipping terminal office overlooking automated gantry cranes through rainy glass, industrial authenticity.", "beats": [2, 4]},
            "bg_secure_data_vault": {"title": "Forensic Electronic Evidence Cleanroom", "description": "High-security digital forensic cleanroom with anti-static workbenches, data recovery docks in soft focus, focused investigative realism.", "beats": [3, 4]},
            "bg_press_conference_briefing_hall": {"title": "Government Press Briefing Auditorium", "description": "Formal government agency press theater, dark blue backdrop with federal eagle emblem, empty wooden lectern in sharp focus.", "beats": [4, 5]},
            "bg_institutional_archive_records_room": {"title": "National Institutional Records Hall", "description": "Double-height archival records room with rolling ladder system, rows of bound legal dockets, soft ambient illumination.", "beats": [3, 5]},
            "bg_sec_enforcement_war_room": {"title": "Securities Enforcement Strategy War Room", "description": "Government regulatory enforcement command room with whiteboards displaying corporate ownership flowcharts, glowing document scanners, serious investigative mood.", "beats": [3, 4]},
            "bg_capitol_hill_press_corridor": {"title": "Capitol Hill Congressional Scrutiny Press Corridor", "description": "Neoclassical marble colonnade corridor outside congressional hearing rooms, warm brass chandeliers, media microphones on stanchions in soft focus, dignified institutional setting.", "beats": [1, 5]}
        }
        fg_roster = {
            "fg_character_lead_prosecutor": {"title": "Federal District Lead Prosecutor", "description": "Full-body stylized editorial graphic novel digital illustration of a focused federal prosecutor in dark tailored wool suit, holding prosecution complaint folder, standing with composed authority, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Prosecutor", "beats": [1, 4, 5], "keywords": ["prosecutor", "complaint", "indictment", "court", "justice"], "type": "character"},
            "fg_character_corporate_general_counsel": {"title": "Corporate General Counsel", "description": "Full-body stylized editorial graphic novel digital illustration of a guarded corporate defense attorney in charcoal pinstripe suit, holding closed leather briefcase with firm defensive posture, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Defense Counsel", "beats": [1, 2, 4], "keywords": ["counsel", "attorney", "corporate", "defense", "executive"], "type": "character"},
            "fg_character_forensic_accountant": {"title": "Senior Forensic Financial Accountant", "description": "Full-body stylized editorial graphic novel digital illustration of a meticulous forensic accountant holding tabulated financial ledger and red audit pen, spectacles reflecting light, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Accountant", "beats": [2, 3, 5], "keywords": ["accountant", "audit", "forensic", "ledger", "numbers"], "type": "character"},
            "fg_character_whistleblower_insider": {"title": "Key Corporate Whistleblower Insider", "description": "Full-body stylized editorial graphic novel digital illustration of an observant corporate insider in casual business jacket, holding confidential manila envelope with cautious resolute gaze, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower", "beats": [2, 3, 4], "keywords": ["whistleblower", "insider", "confidential", "secret", "memo"], "type": "character"},
            "fg_character_investigative_journalist": {"title": "Senior Investigative Financial Journalist", "description": "Full-body stylized editorial graphic novel digital illustration of an investigative journalist in trench coat with press badge on lanyard, holding reporter notepad and pen, focused inquisitive expression, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Investigative Reporter", "beats": [1, 3, 5], "keywords": ["journalist", "reporter", "investigation", "press", "media"], "type": "character"},
            "fg_evidence_prosecution_complaint_docket": {"title": "Official Legal Prosecution Complaint Docket", "description": "Official legal filing document from the federal district court, bold case header, legal docket stamped with blue ink, crisp document paper texture with clean sharp edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Lead Prosecution Docket", "beats": [1, 2, 5], "keywords": ["docket", "complaint", "indictment", "court", "legal"], "type": "document"},
            "fg_evidence_damages_calculation_invoice": {"title": f"Forensic Accounting & Damages Summary Sheet ({metric_highlight})", "description": f"Government audit summary invoice document displaying bold figure '{metric_highlight}' in green ledger ink, stamped diagonally with bold red ink 'CONFIDENTIAL / EXHIBIT A', crisp paper cutout edge, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Forensic Accounting Exhibit", "beats": [1, 4, 5], "keywords": ["damages", "invoice", "restitution", "loss", "bill"], "type": "document"},
            "fg_evidence_regulatory_audit_binder": {"title": "Forensic Investigative Audit Binder", "description": "Thick three-ring forensic investigative audit binder with tabbed colored dividers, official regulatory growth charts visible on front plastic sleeve, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Macro Financial Evidence", "beats": [3, 4, 5], "keywords": ["binder", "audit", "investigation", "dossier"], "type": "document"},
            "fg_evidence_merchant_accounting_ledger": {"title": "Small Business Financial Accounting Ledger", "description": "Worn merchant bookkeeping ledger notebook open on a wooden table, showing ascending cost charges eroding profit margins, paperclips, tactile ink lines, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Victim Economic Evidence", "beats": [1, 2, 4], "keywords": ["ledger", "bookkeeping", "accounting", "transaction"], "type": "document"},
            "fg_evidence_sealed_whistleblower_memo": {"title": "Confidential Internal Whistleblower Memo Envelope", "description": "Manila folder envelope stamped 'RESTRICTED DISTRIBUTION // EXECUTIVE EYES ONLY', partially opened revealing internal memo with black redacted bars across strategic paragraphs, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Whistleblower Document", "beats": [2, 3], "keywords": ["memo", "whistleblower", "confidential", "secret", "envelope"], "type": "document"},
            "fg_evidence_statute_reference_book": {"title": "Federal Statutory Legal Reference Volume", "description": "Heavy vintage leather-bound legal codex open to federal statutory monopolization and fraud sections, gold leaf lettering on spine, ribbon bookmark, sharp paper edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Statutory Authority", "beats": [1, 5], "keywords": ["statute", "law", "code", "reference", "volume"], "type": "document"},
            "fg_evidence_server_rack_drive": {"title": "Automated Algorithm Storage Module", "description": "High-tech brushed metallic enterprise server drive enclosure with flashing blue data activity LEDs, forensic evidence barcode sticker, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Technical Hardware Evidence", "beats": [2, 3], "keywords": ["server", "drive", "data", "algorithm", "module"], "type": "evidence_prop"},
            "fg_evidence_gavel_justice_scale": {"title": "Federal Court Judicial Gavel & Scales", "description": "Dark polished walnut judge gavel resting on sounding block beside balanced brass scales of justice, tactile wood grain, courtroom documentary realism, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Climax Artifact", "beats": [4, 5], "keywords": ["gavel", "judge", "scales", "court", "verdict"], "type": "evidence_prop"},
            "fg_evidence_subpoena_compliance_order": {"title": "Federal Subpoena Duces Tecum Order", "description": "Official federal court subpoena order commanding production of records, embossed blue judicial seal, signed command line, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Compulsory Legal Order", "beats": [2, 4], "keywords": ["subpoena", "order", "records", "compliance"], "type": "document"},
            "fg_evidence_internal_email_chain_exhibit": {"title": "Printed Executive Internal Email Chain Exhibit", "description": "Printed email records stamped with exhibit letter, highlighting strategic discussions with bold yellow highlighter ink, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Internal Communications Exhibit", "beats": [2, 3], "keywords": ["email", "chain", "exhibit", "communication"], "type": "document"},
            "fg_evidence_financial_audit_reconciliation": {"title": "Forensic Revenue Reconciliation Audit Sheet", "description": "Multi-column audit reconciliation spread sheet on green-tinted paper, red penalty calculations stamped in bottom right corner, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Audit Reconciliation Exhibit", "beats": [3, 4], "keywords": ["reconciliation", "audit", "revenue", "penalty"], "type": "document"},
            "fg_evidence_compliance_violation_notice": {"title": "Federal Regulatory Formal Violation Notice", "description": "Formal administrative cease-and-desist violation decree with red stamped border and gold agency seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Regulatory Violation Exhibit", "beats": [4, 5], "keywords": ["violation", "notice", "cease", "sanction"], "type": "document"},
            "fg_evidence_search_warrant_affidavit": {"title": "Federal Court Search Warrant Affidavit", "description": "Sworn legal affidavit for federal search warrant, stamped with blue court seal and signed by special agent, crisp paper textures, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Search Warrant", "beats": [2, 4], "keywords": ["warrant", "search", "affidavit", "federal", "court"], "type": "document"},
            "fg_evidence_wire_fraud_indictment_sheet": {"title": "Federal Grand Jury True Bill Indictment", "description": "Formal multi-count federal indictment docket with grand jury foreman signature line and embossed gold seal, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Grand Jury Indictment Exhibit", "beats": [1, 4], "keywords": ["indictment", "grand jury", "charges", "fraud", "true bill"], "type": "document"},
            "fg_evidence_encrypted_flash_drive": {"title": "Forensic Encrypted Storage Flash Drive", "description": "Metallic USB evidence drive with yellow forensic evidence tag and barcode sticker, tamper-evident security tape, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Digital Hardware Evidence", "beats": [2, 3], "keywords": ["flash drive", "usb", "digital", "evidence", "storage"], "type": "evidence_prop"},
            "fg_evidence_asset_freeze_injunction_order": {"title": "Federal Asset Freezing Injunction Decree", "description": "Judicial injunction decree commanding worldwide freeze of corporate and executive assets, red embossed court seal, crisp legal edges, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Judicial Restraining Order", "beats": [4, 5], "keywords": ["freeze", "injunction", "assets", "order", "court"], "type": "document"},
            "fg_evidence_whistleblower_audio_recorder": {"title": "Forensic Digital Audio Recording Device", "description": "Compact brushed metal digital audio dictaphone with visible audio waveform on illuminated LCD screen, marked with yellow evidence label, isolated on a solid flat #FF00FF pure magenta background, 1:1 aspect ratio.", "role": "Audio Surveillance Evidence", "beats": [2, 3], "keywords": ["recorder", "audio", "wiretap", "dictaphone", "evidence"], "type": "evidence_prop"}
        }
        return bg_roster, fg_roster

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
    Sản sinh:
      - 16 đến 20 Backgrounds (16:9 2560x1440) phân bổ đều qua 5 Beats.
      - 20 đến 26 Foregrounds (1:1 2048x2048 trên nền phẳng #FF00FF magenta chroma):
        + 4-6 Nhân vật chủ chốt (type: 'character')
        + 16-20 Đạo cụ bằng chứng / Chứng từ pháp y / Biểu đồ xúc giác (type: 'evidence_prop' | 'document' | 'data_metric')
    CẤM TUYỆT ĐỐI hardcode chỉ 8 items hoặc hardcode tên tập/đạo cụ vụ án cụ thể.
    """
    m_up = str(market or "EN").upper().strip()
    g_intel = grounding_intel or {}
    topic_str = topic or (g_intel.get("topic") if isinstance(g_intel, dict) else "") or "Investigative Docudrama"

    # Trích xuất số liệu định lượng và claims thực tế từ grounding
    claims = []
    if isinstance(g_intel, dict):
        for c in g_intel.get("claims", [])[:10]:
            txt = c.get("claim") or c.get("text") if isinstance(c, dict) else str(c)
            if txt:
                claims.append(txt[:150])

    key_metrics = []
    if isinstance(g_intel, dict) and g_intel.get("grounding_table"):
        for row in g_intel.get("grounding_table", [])[:8]:
            val = row.get("value") or row.get("metric_value")
            unit = row.get("unit") or ""
            param = row.get("parameter") or row.get("claim_id") or ""
            if val:
                key_metrics.append(f"{param}: {val} {unit}".strip())
    elif isinstance(g_intel, dict) and g_intel.get("key_figures"):
        key_metrics.extend([str(x) for x in g_intel.get("key_figures", [])[:6]])

    # Narrative sample
    sample_narr = []
    if spoken_sentences:
        step = max(1, len(spoken_sentences) // 10)
        sample_narr = [s.get("text", "") for s in spoken_sentences[::step][:8]]
    elif story_text:
        sample_narr = [line.strip() for line in story_text.split("\n") if line.strip()][:5]

    bg_roster = None
    fg_roster = None

    # Thử gọi LLM Gateway để sinh Roster hoàn toàn độc lập và động (bỏ qua trong pytest để test chạy tức thì)
    is_testing = bool(os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules or os.getenv("VF_SMOKE_TEST") or os.getenv("FAST_ROSTER"))
    if not is_testing:
        try:
            from app.services.model_gateway import get_global_gateway
            gateway = get_global_gateway()

            system_prompt = (
                "You are the Lead Cinematographer & VOX Motion Graphics Visual Director for AI Video Factory.\n"
                "Your mission is to architect an exhaustive, topic-anchored Visual Asset Roster for a 12-20 minute investigative docudrama in VOX / Johnny Harris style.\n"
                "The documentary is structured across 5 Beats:\n"
                "Beat 1: Cold Strike & Paradox Hook (0-60s)\n"
                "Beat 2: Historical Origin & False Narrative\n"
                "Beat 3: Forensic Paper Trail & Quantitative Mechanism\n"
                "Beat 4: The Systemic Climax & Crisis\n"
                "Beat 5: Modern Mirror & Living Warning\n\n"
                "MANDATES:\n"
                "1. 'background_roster': Exactly 16 to 20 distinct environmental Backgrounds (16:9 2560x1440).\n"
                "   - Distributed evenly across Beats 1 to 5 (3 to 4 distinct BGs per Beat).\n"
                "   - Non-photorealistic 2D stylized graphic novel editorial illustration, bold ink linework, cel-shading, moody chiaroscuro lighting, rich textures.\n"
                "   - ZERO prominent human figures in the foreground. Leave center/right negative space clear for tactile foreground overlays. Leave bottom 20% safe zone clear for subtitles.\n"
                "   - Strictly authentic to target market and topic era.\n"
                "   - Keys MUST be 'bg_<semantic_slug>'.\n"
                "   - Schema: {\"title\": \"...\", \"description\": \"...\", \"beats\": [1, 2]}\n\n"
                "2. 'foreground_roster': Exactly 20 to 26 distinct Foregrounds (1:1 2048x2048) on pure flat #FF00FF magenta chroma key.\n"
                "   Divided into:\n"
                "   A. Key Character Archetypes (4 to 6 items): 'type': 'character', full-body or 3/4 stylized graphic novel figure visible from head to toe/waist on flat #FF00FF magenta background. Authentic ethnic phenotype for target market. Keys: 'fg_character_<role>'.\n"
                "   B. Tactile Evidence Props, Documents & Charts (16 to 20 items): 'type': 'evidence_prop' | 'document' | 'data_metric'. High-impact, topic-specific evidentiary artifacts (e.g. debt bonds, auction sheets, balance ledgers, contracts, audit memos, charts, stamped dockets, currency swaps, default tickets). Keys: 'fg_evidence_<object_name>'.\n"
                "   - Schema: {\"title\": \"...\", \"description\": \"...\", \"role\": \"...\", \"beats\": [1, 2, 3], \"keywords\": [\"kw1\", \"kw2\"], \"type\": \"character\"|\"document\"|\"evidence_prop\"|\"data_metric\"}\n\n"
                "Output ONLY valid JSON matching:\n"
                "{\n"
                "  \"background_roster\": { \"<bg_key>\": { \"title\": \"...\", \"description\": \"...\", \"beats\": [...] } },\n"
                "  \"foreground_roster\": { \"<fg_key>\": { \"title\": \"...\", \"description\": \"...\", \"role\": \"...\", \"beats\": [...], \"keywords\": [...], \"type\": \"...\" } }\n"
                "}"
            )

            user_prompt = json.dumps({
                "topic": topic_str,
                "target_market": m_up,
                "verified_claims": claims,
                "key_metrics": key_metrics,
                "narrative_samples": sample_narr
            }, ensure_ascii=False)

            models_to_try = ["gpt-6-astra", "claude-opus-5", "claude-sonnet-5"]
            resp = None
            for m_candidate in models_to_try:
                try:
                    logger.info(f"[unified_vox_director] Attempting High-Tier LLM: {m_candidate}")
                    resp = gateway.call_llm(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        model=m_candidate,
                        max_tokens=4500,
                        timeout=45.0
                    )
                    if resp:
                        break
                except Exception as ex_m:
                    logger.warning(f"[unified_vox_director] Model {m_candidate} failed: {ex_m}")
            if resp:
                cleaned_json = re.sub(r"^```(?:json)?\s*", "", resp.strip(), flags=re.MULTILINE)
                cleaned_json = re.sub(r"\s*```$", "", cleaned_json, flags=re.MULTILINE)
                parsed = json.loads(cleaned_json)
                bgs = parsed.get("background_roster", {})
                fgs = parsed.get("foreground_roster", {})
                if len(bgs) >= 14 and len(fgs) >= 18:
                    bg_roster = bgs
                    fg_roster = fgs
        except Exception as e:
            logger.info(f"[unified_vox_director] LLM dynamic roster extraction bypassed or failed: {e}")

    # Fallback chất lượng cao nếu LLM không trả kết quả đủ chuẩn
    if not bg_roster or not fg_roster:
        bg_roster, fg_roster = _generate_topic_anchored_roster_fallback(topic_str, m_up, key_metrics, claims)

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

    # Rule 128 & User Mandate: Cap to maximum 18 hero clips for long-form episodes (12-14 mins)
    # to enforce mathematical budget of 6 accounts x 3 clips = 18 clips.
    if len(selected) > 18:
        mandatory = {0, selected[-1]}
        for b_idx in beat_first_indices.values():
            if b_idx in selected:
                mandatory.add(b_idx)
        remaining = [x for x in selected if x not in mandatory]
        needed = 18 - len(mandatory)
        if needed > 0 and remaining:
            step = len(remaining) / needed
            picked = [remaining[int(i * step)] for i in range(needed)]
            selected = sorted(list(mandatory.union(picked)))
        else:
            selected = sorted(list(mandatory))[:18]

    return selected


def determine_spatial_physics(narr: str, fg_key: Optional[str], hero_index: int) -> Tuple[str, str, str, str]:
    """Xác định hành vi xúc giác (Tactile Spatial Physics) dựa trên bản chất vật thể và ngữ cảnh kể chuyện (Rule 128).
    Hỗ trợ đối chiếu đa ngôn ngữ: EN, JP, KR, VN.
    Sử dụng CANONICAL_SFX_REGISTRY tuyệt đối, cấm sinh cue tùy tiện.
    Trả về: (physics_type, action_type, seed_mode, foleys)
    """
    foleys = resolve_semantic_foley(narr, fg_key, hero_index)
    n_low = (narr or "").lower()
    fg_low = (fg_key or "").lower()
    combined = f"{n_low} {fg_low}"

    if foleys in ["gavel_thud", "gauge_needle_hiss"]:
        return "MACRO_HIGHLIGHT_WIPE", "MACRO_HIGHLIGHT_WIPE", "CUTOUT_ONLY", foleys
    elif any(k in combined for k in ["docket", "memo", "confidential", "secret", "whistleblower", "dog-ear", "peel", "cáo trạng", "khởi tố", "mật", "bóc tách", "기소", "고발", "비밀", "内部告発"]):
        return "CORNER_DOGEAR_PEEL", "CORNER_DOGEAR_PEEL", "COMPOSITE_16_9", foleys
    elif any(k in combined for k in ["invoice", "damage", "bill", "check", "listing", "card", "hóa đơn", "bồi thường", "chi phí", "영수증", "손해", "請求書", "損害"]):
        return "DOCUMENT_TABLE_DROP", "DOCUMENT_TABLE_DROP", "COMPOSITE_16_9", foleys
    elif any(k in combined for k in ["dossier", "contract", "agreement", "binder", "ledger", "book", "hợp đồng", "sổ sách", "hồ sơ", "계약", "장부", "契約", "帳簿"]):
        return "BIFOLD_DOSSIER_OPEN", "BIFOLD_DOSSIER_OPEN", "COMPOSITE_16_9", foleys
    else:
        cycle = hero_index % 3
        if cycle == 0:
            return "CORNER_DOGEAR_PEEL", "CORNER_DOGEAR_PEEL", "COMPOSITE_16_9", foleys
        elif cycle == 1:
            return "DOCUMENT_TABLE_DROP", "DOCUMENT_TABLE_DROP", "COMPOSITE_16_9", foleys
        else:
            return "BIFOLD_DOSSIER_OPEN", "BIFOLD_DOSSIER_OPEN", "COMPOSITE_16_9", foleys


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


def validate_director_sfx_compliance(scenes: List[Dict[str, Any]], hero_clips: List[Dict[str, Any]]) -> None:
    """Chốt chặn kiểm toán pháp y SFX B3 (Rule 120, Rule 128 & Rule 134).
    Bắt buộc 100% scenes và hero_clips phải dùng foley cue nằm trong CANONICAL_SFX_REGISTRY.
    CẤM TUYỆT ĐỐI lọt cue lạ hoặc unconstrained string sang B4-B6.
    """
    invalid_cues = []
    for sc in scenes:
        cue = sc.get("foleys_audio") or sc.get("audio_cue")
        if cue and not is_valid_sfx(cue):
            invalid_cues.append(f"Scene {sc.get('scene_id')}: invalid foley cue '{cue}'")
    for hc in hero_clips:
        cue = hc.get("foleys_audio") or hc.get("audio_cue")
        if cue and not is_valid_sfx(cue):
            invalid_cues.append(f"Hero Clip {hc.get('scene_id')}: invalid foley cue '{cue}'")

    if invalid_cues:
        raise ValueError(
            f"❌ B3 DIRECTOR SFX COMPLIANCE FAILED ({len(invalid_cues)} violations):\n" +
            "\n".join(invalid_cues) +
            f"\nAllowed Canonical SFX: {get_canonical_sfx_list()}"
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

    # Phân loại Foreground: Nhân vật (character) vs Đạo cụ bằng chứng (evidence prop / document)
    char_fg_keys = [
        k for k in fg_keys
        if fg_roster[k].get("type") == "character"
        or k.startswith("char_") or k.startswith("fg_character_")
        or any(w in k.lower() for w in ["character", "official", "banker", "investigator", "trader", "eyewitness", "minister"])
    ]
    prop_fg_keys = [k for k in fg_keys if k not in char_fg_keys]
    if not prop_fg_keys:
        prop_fg_keys = fg_keys

    char_count = 0
    last_char_scene = -99

    for idx, sent in enumerate(spoken_sentences):
        narr = sent.get("text", "")
        dur_frames = int(sent.get("duration_frames") or 150)
        dur_sec = float(sent.get("duration_sec") or ((sent.get("end_ms", 0) - sent.get("start_ms", 0)) / 1000.0 if sent.get("end_ms") else 0.0) or round(dur_frames / 30.0, 3))
        beat_idx = int(sent.get("beat_index") or ((idx // max(1, len(spoken_sentences) // 5)) + 1))
        beat_idx = min(max(beat_idx, 1), 5)

        # Matching Background phù hợp theo Beat và thứ tự cảnh (luân phiên 3 cảnh / 1 BG)
        matching_bgs = [k for k, v in bg_roster.items() if beat_idx in v.get("beats", [1, 2, 3, 4, 5])]
        if not matching_bgs:
            matching_bgs = bg_keys
        bg_key = matching_bgs[(idx // 3) % len(matching_bgs)]

        # Matching Foreground Evidence dựa trên từ khóa kể chuyện hoặc luân phiên Beat
        narr_lower = narr.lower()
        fg_key = None

        # Kiểm tra khoảnh khắc xuất hiện nhân vật (nhân vật con người xuất hiện có chọn lọc <= 10-12 cảnh)
        is_char_moment = (
            bool(char_fg_keys) and
            (char_count < 10) and
            (idx - last_char_scene >= 12) and
            (any(q in narr for q in ['"', '“', '”', '「', '」']) or
             any(w in narr_lower for w in ["said", "testified", "admitted", "warned", "declared", "tuyên bố", "thừa nhận", "chỉ trích", "phát biểu", "증언", "발언", "発言", "証言"]))
        )

        if is_char_moment:
            matched_char = None
            for ck in char_fg_keys:
                c_info = fg_roster[ck]
                kws = c_info.get("keywords", []) + c_info.get("title", "").lower().split()
                if any(kw in narr_lower for kw in kws if len(kw) > 3):
                    matched_char = ck
                    break
            if not matched_char:
                matched_char = char_fg_keys[char_count % len(char_fg_keys)]
            fg_key = matched_char
            char_count += 1
            last_char_scene = idx
        else:
            # Gán đạo cụ bằng chứng pháp y dựa trên điểm tương đồng từ khóa
            matched_prop = None
            best_score = 0
            for pk in prop_fg_keys:
                p_info = fg_roster[pk]
                p_beats = p_info.get("beats", [1, 2, 3, 4, 5])
                kws = p_info.get("keywords", []) + p_info.get("title", "").lower().split()
                score = sum(1 for kw in kws if len(kw) > 3 and kw in narr_lower)
                if beat_idx in p_beats:
                    score += 1
                if score > best_score:
                    best_score = score
                    matched_prop = pk

            if not matched_prop or best_score <= 1:
                beat_props = [k for k in prop_fg_keys if beat_idx in fg_roster[k].get("beats", [1, 2, 3, 4, 5])] or prop_fg_keys
                matched_prop = beat_props[(idx // 2) % len(beat_props)]
            fg_key = matched_prop

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
            foleys = resolve_semantic_foley(narr, fg_key, idx)
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

    # Validate director SFX compliance prior to return (Fail-Fast Gate)
    validate_director_sfx_compliance(scenes, hero_clips)

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
    mkt = ep_id.split("_")[0].upper() if ep_id and "_" in ep_id else "EN"
    bg_prompts = {k: _sanitize_background_prompt(v["description"], bg_key=k, market=mkt) for k, v in bg_roster.items()}
    fg_prompts = {k: _sanitize_foreground_prompt(v["description"], fg_key=k, market=mkt) for k, v in fg_roster.items()}
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
