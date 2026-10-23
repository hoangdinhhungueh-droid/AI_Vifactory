#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/reforge_b3_director.py
Master Reforge Director Plan Engine for Vox Tactile Paper-Collage Pipeline.
Enforces RULE 140:
1. Pacing: 5.0 - 8.0 seconds per Beat (~70-75 Beats for 551.93s).
2. Abstract-to-Tactile Object Decomposition (Hanko seal, Japanese contracts, brass calipers, paper shears).
3. 4-Phase Kinematics Contract (S1 Entry -> S2 Stamp/Impact -> S3 Vector Growth -> S4 Spatial Hold).
4. Zero-Text on Bitmap Seed Image (Pure Remotion Typography).
"""

from __future__ import annotations

import os
import sys
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# 12 THEMATIC SEQUENCE BLOCKS FOR JP_EP0003
BLOCKS_CONFIG = [
    {
        "block_id": "BLOCK_01",
        "title": "THE 10X CATALYST & THE SHOCK METRIC",
        "act": "ACT_I",
        "theme_color": "#C85A32", # Terracotta
        "canvas_workspace": "Aged Cream Newsprint Desk #F4F1EA with subtle print halftone grid and vintage editorial ruler margin",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_02",
        "title": "SEARCH INTENT & INVISIBLE TRANSFORMATION",
        "act": "ACT_I",
        "theme_color": "#F2C230", # Vox Yellow
        "canvas_workspace": "Aged Cream Newsprint Desk #F4F1EA with forensic typewriter grid and investigative document folder",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_03",
        "title": "THE OFFICIAL SHIELD & CEO PHISHING",
        "act": "ACT_II",
        "theme_color": "#1B2B4A", # Navy
        "canvas_workspace": "Corporate Japanese Executive Desk #F4F1EA with subtle cedar wood texture and business card tray",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_04",
        "title": "THE MISCONCEPTION: LANGUAGE VS CREDENTIALS",
        "act": "ACT_II",
        "theme_color": "#8C3B2B", # Deep Crimson
        "canvas_workspace": "Forensic Inspection Ledger #F4F1EA with technical network schematic underlay",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_05",
        "title": "THE UNSEEN ENTRANCE: UNMANAGED ENDPOINTS",
        "act": "ACT_III",
        "theme_color": "#2D4A3E", # Muted Forest Green
        "canvas_workspace": "Network Infrastructure Blueprint #F4F1EA with aged blueprint grid and server rack terminal silhouette",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_06",
        "title": "FIRST NODE: SYSTEMIC SCANNING VS TRANSLATION",
        "act": "ACT_III",
        "theme_color": "#C85A32", # Terracotta
        "canvas_workspace": "Diagnostic Oscilloscope & Server Log Sheet #F4F1EA with vertical data tape margin",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_07",
        "title": "SECOND NODE: DARK WEB JAPANESE DATA PREMIUM",
        "act": "ACT_III",
        "theme_color": "#1A1A1A", # Charcoal
        "canvas_workspace": "Dark Web Auction Ledger & Banknote Examination Desk #F4F1EA with UV watermark grid",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_08",
        "title": "THE NEGOTIATION TABLE: REAL-TIME AI TRANSLATION",
        "act": "ACT_IV",
        "theme_color": "#C85A32", # Terracotta
        "canvas_workspace": "Ransom Demand Conference Board #F4F1EA with red evidence yarn cross-links",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_09",
        "title": "CRIMINAL DIVISION OF LABOR & PLUMMETING FRICTION",
        "act": "ACT_IV",
        "theme_color": "#F2C230", # Vox Yellow
        "canvas_workspace": "Industrial Conveyor & Disassembly Diagram #F4F1EA with mechanical gear schematics",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_10",
        "title": "THE COST STRUCTURE: SPREADSHEET OF EXTORTION",
        "act": "ACT_IV",
        "theme_color": "#1B2B4A", # Navy
        "canvas_workspace": "Financial Balance Sheet & Forensic Audit Ledger #F4F1EA with red and black debit columns",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_11",
        "title": "MODERN MIRROR: THE END OF LINGUISTIC ISOLATION",
        "act": "ACT_V",
        "theme_color": "#2D4A3E", # Muted Forest Green
        "canvas_workspace": "Tokyo Metropolitan Cyber Defense Command Desk #F4F1EA with security directive dossiers",
        "beats_count": 6
    },
    {
        "block_id": "BLOCK_12",
        "title": "LIVING WARNING: NATURAL JAPANESE IS NOT SAFETY",
        "act": "ACT_V",
        "theme_color": "#8C3B2B", # Deep Crimson
        "canvas_workspace": "Archival Case Folder & Evidence Closure Stamp Desk #F4F1EA with final wax seal envelope",
        "beats_count": 6
    }
]

# DETAILED 72 TACTILE BEATS DATA
BEATS_METADATA = [
    # BLOCK 1: THE 10X CATALYST (Beats 1-6)
    {
        "id": 1, "start": 0.0, "end": 7.6,
        "ja": "2026年10月9日、テレ朝NEWSが英国の専門家の見方として伝えた「身代金交渉の効率が10倍になり得る」という衝撃の数字は、日本語の壁が崩れたことを意味するのでしょうか？",
        "idea": "10X NEGOTIATION CATALYST", "title": "THE 10X MULTIPLIER",
        "hero": "Japanese corporate confidential document folio with fold creases and bold red '10X' stamp margin",
        "props": ["Crimson wooden Hanko seal stamp", "Brass document paperclip"],
        "s1": "Document folio drops onto center-left desk with realistic paper bounce.",
        "s2": "Crimson wooden Hanko seal strikes down firmly on lower right corner with micro paper dust.",
        "s3": "Bold red multiplier outline emerges from the stamp impression.",
        "s4": "Rigid living poster spatial anchor hold, subtle shadow breathing <= 2px."
    },
    {
        "id": 2, "start": 7.6, "end": 15.3,
        "ja": "この数字は市場全体で測定されたものではありません。",
        "idea": "UNVERIFIED AGGREGATE", "title": "THE MISSING BASELINE",
        "hero": "Vintage mechanical brass caliper measuring tool with engraved metric scales",
        "props": ["Unverified survey ledger sheet with question marks", "Muted gray paper bookmark"],
        "s1": "Survey ledger sheet slides into position from upper edge.",
        "s2": "Brass caliper slides across the paper, opening jaws around the metric data line.",
        "s3": "Dotted yellow dashed perimeter frames the caliper reading.",
        "s4": "All objects freeze in place with micro paper texture stop-motion jitter."
    },
    {
        "id": 3, "start": 15.3, "end": 23.0,
        "ja": "それでも11日後の10月20日、産経ニュースは、生成AIで日本語の壁を越える海外の攻撃者と、追跡を難しくする犯罪組織の分業を報じました。",
        "idea": "CRIMINAL SYNDICATE DIVISION", "title": "THE DIVISION OF LABOR",
        "hero": "Heavy forged steel paper shears cutting across international boundary map",
        "props": ["Torn Japanese news clipping from Sankei Shimbun", "Red evidence string connector"],
        "s1": "International border map slides in from top-right.",
        "s2": "Steel paper shears impact down and cleanly snip the paper along border line.",
        "s3": "Red evidence string snaps taut connecting the two severed paper segments.",
        "s4": "Permanent spatial hold with subtle ambient grain breathing."
    },
    {
        "id": 4, "start": 23.0, "end": 30.7,
        "ja": "だますメールを書く。盗んだ情報で脅す。交渉を続ける。",
        "idea": "THREE STAGES OF EXTORTION", "title": "THREE ATTACK STAGES",
        "hero": "Triptych of three sequential Japanese index cards with forensic stamp icons",
        "props": ["Fountain pen nib cutout", "Lockbox key prop", "Negotiation dialogue balloon cutout"],
        "s1": "Three index cards drop sequentially onto desk in horizontal cascade (0.5s intervals).",
        "s2": "Three rubber stamp marks slam down on each respective card.",
        "s3": "Horizontal vector line connects all three cards from left to right.",
        "s4": "Locked spatial anchor hold, no 3D drift."
    },
    {
        "id": 5, "start": 30.7, "end": 38.3,
        "ja": "日本語が必要だった複数の工程で、人手と時間の負担が下がる可能性があります。",
        "idea": "COLLAPSING HUMAN FRICTION", "title": "FRICTION DISSOLVES",
        "hero": "Mechanical hourglass cutout with descending red sand particles beside Japanese kanji card",
        "props": ["Descending stair diagram cutout", "Stopwatch chrono face cutout"],
        "s1": "Descending stair diagram slides in from left anchor.",
        "s2": "Hourglass drops firmly onto the topmost step with a soft thud.",
        "s3": "Bold downward red vector arrow draws sharply down the staircase.",
        "s4": "Static living poster hold with micro paper shadow flutter."
    },
    {
        "id": 6, "start": 38.3, "end": 46.0,
        "ja": "いま検索窓には「日本語の壁 ai」「生成ai 日本語の壁」「サイバー攻撃 日本語の壁」という言葉が並んでいます。",
        "idea": "EXPLODING SEARCH INTENT", "title": "THE VIRAL SEARCH",
        "hero": "Tactile search bar input cutout on aged newspaper with blinking cursor prop",
        "props": ["Stack of Japanese trend cards", "Neon yellow highlighter marker"],
        "s1": "Search bar cutout drops into upper-center negative space.",
        "s2": "Neon yellow highlighter marker sweeps smoothly across the input field.",
        "s3": "Three trend search tags pop out beneath the bar in staggered succession.",
        "s4": "Permanent spatial anchor hold, clean 2D matte texture."
    },

    # BLOCK 2: SEARCH INTENT & INVISIBLE TRANSFORMATION (Beats 7-12)
    {
        "id": 7, "start": 46.0, "end": 53.6,
        "ja": "前日の10月19日、東洋経済オンラインは、AIが攻撃の首謀者なのか、費用を下げる加速装置なのかを検証しました。",
        "idea": "ACCELERATOR VS MASTERMIND", "title": "THE ACCELERATOR",
        "hero": "Two-pan brass balancing scale weighing AI processor chip vs cost ledger",
        "props": ["Toyo Keizai report header clipping", "Miniature brass weights"],
        "s1": "Balancing scale drops into center canvas with gentle pendulum swing.",
        "s2": "AI chip drops into left pan while cost ledger drops into right pan.",
        "s3": "Scale tilts decisively toward the cost ledger side.",
        "s4": "Fixed anchor hold, subtle shadow breathing."
    },
    {
        "id": 8, "start": 53.6, "end": 61.3,
        "ja": "示されたのは、言葉の壁が消えたことで、日本企業が長く抱えてきた社内の弱点が直接狙われるようになったという構図でした。",
        "idea": "EXPOSED DOMESTIC FLAWS", "title": "EXPOSED UNDERBELLY",
        "hero": "Architectural floorplan of traditional Tokyo corporate headquarters with red target reticle",
        "props": ["Torn perimeter wall segment", "Red pin indicator"],
        "s1": "Architectural floorplan unfolds flat across the workspace.",
        "s2": "Perimeter wall segment lifts away revealing inner unshielded corridors.",
        "s3": "Crimson target reticle snaps onto the central server room marker.",
        "s4": "Locked spatial anchor hold, no camera roll."
    },
    {
        "id": 9, "start": 61.3, "end": 69.0,
        "ja": "表面では何も変わりません。受信箱に届くのは、敬語の整った一通の依頼文です。",
        "idea": "FLAWLESS FORMAL KEIGO", "title": "THE PERFECT INBOX",
        "hero": "Crisp ivory corporate envelope with authentic Japanese postal stamp and fold crease",
        "props": ["Business business card from Japanese CEO", "Wax seal ribbon"],
        "s1": "Ivory envelope slides smoothly from top right into center focal area.",
        "s2": "Flap folds open smoothly to reveal pristine folded document inside.",
        "s3": "Delicate green authenticity checkmark badge pops beside the address label.",
        "s4": "Rigid spatial hold, micro paper edge shadow."
    },
    {
        "id": 10, "start": 69.0, "end": 76.6,
        "ja": "誤字はない。違和感もない。けれど、その一文のために海外の誰かが払っていた翻訳の手間は、静かに消えつつあります。",
        "idea": "ZERO LINGUISTIC ARTIFACT", "title": "VANISHING FRICTION",
        "hero": "Vintage Japanese dictionary book cutout fading into transparent halftone dots",
        "props": ["Magnifying glass with optical glass reflection", "Torn translation invoice"],
        "s1": "Dictionary and invoice drop onto center desk.",
        "s2": "Magnifying glass slides over text, focusing sharp typography details.",
        "s3": "Translation invoice slowly dissolves into halftone paper fibers.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 11, "start": 76.6, "end": 84.3,
        "ja": "本当の衝撃は、その静けさにあります。では、誰が交渉の判断を担うのでしょうか？",
        "idea": "THE SILENT CRISIS", "title": "WHO DECIDES?",
        "hero": "Silhouetted executive office chair cutout behind frosted Japanese shoji glass pane",
        "props": ["Question mark cut from black cardboard", "Red evidence tag"],
        "s1": "Shoji screen panel slides into left third of canvas.",
        "s2": "Empty executive chair drops behind the screen.",
        "s3": "Black cardboard question mark slams down onto center table.",
        "s4": "Permanent hold with subtle paper grain vibration."
    },
    {
        "id": 12, "start": 84.3, "end": 92.0,
        "ja": "この調査では、攻撃件数や利益の増加を決めつけません。メール作成から脅迫交渉までの役割と費用を分解します。",
        "idea": "FORENSIC DISASSEMBLY", "title": "DECONSTRUCTING COST",
        "hero": "Exploded mechanical diagram of an extortion pipeline laid out like precision watchmaker parts",
        "props": ["Watchmaker brass tweezers", "Segmented cost breakdown cards"],
        "s1": "Central pipeline blueprint lands flat on table.",
        "s2": "Tweezers place three precision gear parts along the pipeline track.",
        "s3": "Dotted technical dimension lines draw outwards from each component.",
        "s4": "Locked spatial anchor hold."
    },

    # BLOCK 3: THE OFFICIAL SHIELD & CEO PHISHING (Beats 13-18)
    {
        "id": 13, "start": 92.0, "end": 99.6,
        "ja": "問いは一つです。言葉の壁が低くなると、日本企業を狙う犯罪の採算は、どこから変わるのか。",
        "idea": "THE CORE ECONOMIC QUESTION", "title": "WHERE PROFIT SHIFTS",
        "hero": "Vintage Japanese accounting abacus (Soroban) with wooden beads aligned in counting position",
        "props": ["Red ledger book with golden binding", "Brass coin stack"],
        "s1": "Soroban abacus slides in horizontally from left margin.",
        "s2": "Three abacus beads snap audibly upward into calculating posture.",
        "s3": "Red ledger drops beside abacus with ribbon bookmark settling.",
        "s4": "Living poster anchor hold, shadow breathing <= 2px."
    },
    {
        "id": 14, "start": 99.6, "end": 107.3,
        "ja": "最初の異変は、半年前の受信箱に現れていました。",
        "idea": "FIRST ANOMALY IN APRIL", "title": "APRIL ANOMALY",
        "hero": "Tear-off wall calendar page marked '2026年4月1日' with torn upper perforation edge",
        "props": ["Red circle ink marking around date", "Steel push pin"],
        "s1": "Calendar page flutters down from top onto aged cream board.",
        "s2": "Steel push pin drives through upper margin with paper indentation.",
        "s3": "Wet red ink circle draws around the April 1st numeral.",
        "s4": "Fixed spatial anchor hold, no rotation."
    },
    {
        "id": 15, "start": 107.3, "end": 115.0,
        "ja": "その異変の記録は、2026年4月1日にあります。ZDNET Japanは、社長になりすましたAIフィッシングメールの急増を報じました。",
        "idea": "CEO IMPERSONATION SPIKE", "title": "THE FAKE CEO",
        "hero": "Japanese corporate president Sawonjeung employee ID badge with photo masked by digital static",
        "props": ["ZDNET news clipping cutout", "Warning triangle badge"],
        "s1": "President ID badge lands on center desk with metallic clip bounce.",
        "s2": "ZDNET report cutout slides beneath badge as background documentation.",
        "s3": "Sharp upward vector line shoots up behind the badge indicating surge.",
        "s4": "Permanent anchor hold with subtle halftone breathing."
    },
    {
        "id": 16, "start": 115.0, "end": 122.6,
        "ja": "かつて見分ける手がかりだった不自然な日本語が、消えたというのです。防御側は、新しい検知モデルの開発に追われました。",
        "idea": "VANISHING RED FLAGS", "title": "SILENT DETECTION RACE",
        "hero": "Microscope aperture cutout revealing flawless Japanese typography without red correction marks",
        "props": ["Red ink correction pen lying discarded", "AI detection neural grid card"],
        "s1": "Microscope slide card slides into central view.",
        "s2": "Red correction pen rolls off to the bottom right edge.",
        "s3": "Blue neural lattice grid overlays the pristine text.",
        "s4": "Locked spatial anchor hold."
    },
    {
        "id": 17, "start": 122.6, "end": 130.3,
        "ja": "それ以前、東洋経済オンラインが指摘したように、日本語の細かなニュアンスは、非母語話者による標的型フィッシングへの構造的な盾でした。",
        "idea": "STRUCTURAL LINGUISTIC SHIELD", "title": "THE LANGUAGE SHIELD",
        "hero": "Solid cast-bronze traditional Japanese fortress shield engraved with intricate kanji characters",
        "props": ["Repelled digital arrow cutouts", "Stone foundation blocks"],
        "s1": "Bronze fortress shield drops heavily onto central desk.",
        "s2": "Two foreign arrow cutouts strike the shield and bounce harmlessly away.",
        "s3": "Gold defensive halo pulses subtly around shield perimeter.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 18, "start": 130.3, "end": 138.0,
        "ja": "敬語の段階。文脈に頼る言い回し。社内だけの呼び方。小さな手がかりが積み重なり、あなたは手を止めることができました。",
        "idea": "THREE SUBTLE CLUES", "title": "THREE WARNING SIGNS",
        "hero": "Trio of overlapping Japanese memo slips tagged 'Keigo', 'Context', 'Internal Slang'",
        "props": ["Red stop sign hand silhouette", "Yellow warning tape strip"],
        "s1": "Three memo slips land overlapping in a neat fan spread.",
        "s2": "Red hand silhouette stamps down over the memos, halting action.",
        "s3": "Yellow warning tape strips frame the upper and lower margins.",
        "s4": "Permanent spatial anchor hold."
    },

    # BLOCK 4: THE MISCONCEPTION: LANGUAGE VS ACCESS (Beats 19-24)
    {
        "id": 19, "start": 138.0, "end": 145.6,
        "ja": "そこで広がった見出しの物語は分かりやすいものでした。AIが日本語を破った。だから企業が倒れた。",
        "idea": "THE POPULAR HEADLINE MYTH", "title": "THE POPULAR MYTH",
        "hero": "Exaggerated newspaper front page with sensational giant headline and collapsing tower graphic",
        "props": ["Comic book lightning bolt cutout", "Cracked concrete fragment"],
        "s1": "Sensational tabloid newspaper slams down onto desk.",
        "s2": "Lightning bolt graphic impacts center of page.",
        "s3": "Vibrant red 'FALSE PREMISE' stamp strikes diagonally across headline.",
        "s4": "Locked living poster anchor hold."
    },
    {
        "id": 20, "start": 145.6, "end": 153.3,
        "ja": "本当にそうでしょうか？答えは、いいえです。流暢な文章は、システムへの入場券ではありません。",
        "idea": "FLUENCY IS NOT ADMISSION", "title": "WORDS ARE NOT KEYS",
        "hero": "Decorative Japanese calligraphy scroll contrasted with heavy iron server room padlock",
        "props": ["Blank key blank that does not fit lock", "Red refusal X mark"],
        "s1": "Calligraphy scroll rolls open across left canvas.",
        "s2": "Heavy iron padlock drops onto right canvas with heavy metallic clack.",
        "s3": "Key blank tries and fails to insert, bouncing back.",
        "s4": "Fixed spatial hold, shadow breathing <= 2px."
    },
    {
        "id": 21, "start": 153.3, "end": 161.0,
        "ja": "パスワードを入力する人、認証を省いた設定、更新されていない機器がなければ、侵入は成立しません。",
        "idea": "THE THREE REAL ENABLERS", "title": "THREE REAL VULNERABILITIES",
        "hero": "Technical audit card with 3 check boxes: Weak Password, Missing MFA, Unpatched Firmware",
        "props": ["Sticky note with 'password123'", "Dusty unpatched router cutout"],
        "s1": "Technical audit card drops into center view.",
        "s2": "Dusty router and password sticky note drop onto respective quadrants.",
        "s3": "Red ink checkmarks violently fill all three vulnerability boxes.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 22, "start": 161.0, "end": 168.6,
        "ja": "検索を集める言葉と技術的な原因は別物です。事実を一つずつ積み重ねると、その差が見えてきます。",
        "idea": "HYPETEXT VS TECHNICAL ROOT", "title": "HYPE VS REALITY",
        "hero": "Two-column comparison card separating 'Buzzwords (AI)' from 'Forensic Root Causes'",
        "props": ["Magnifying loupe", "Dividing ruler in matte black"],
        "s1": "Two-column card slides into center from bottom edge.",
        "s2": "Dividing black ruler drops squarely down the center dividing line.",
        "s3": "Loupe focuses on forensic root causes column, highlighting data.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 23, "start": 168.6, "end": 176.3,
        "ja": "産経ニュースは、不正アクセスの起点が中国から活動する主体に行き着くと報じました。ただし、地理的な起点の報道は、個々の事件の実行者を特定する証拠ではありません。",
        "idea": "GEOGRAPHIC ORIGIN LIMITS", "title": "ORIGIN TRACING",
        "hero": "Forensic world map route line with IP trace dotted vectors originating in East Asia",
        "props": ["Disclaimer legal stamp badge", "Magnifying reticle"],
        "s1": "World map routing sheet lands flat on desk.",
        "s2": "Dotted IP route draws across the oceanic map to Tokyo.",
        "s3": "'UNVERIFIED ATTRIBUTION' legal disclaimer stamp frames the route.",
        "s4": "Locked spatial hold with subtle paper grain texture."
    },
    {
        "id": 24, "start": 176.3, "end": 184.0,
        "ja": "この番組は、確認できる記録の範囲で話を進めます。では、言葉でないなら、本当の入口はどこにあったのでしょうか？その答えは、攻撃者自身の発言に残っていました。",
        "idea": "THE ADVERSARY'S OWN WORDS", "title": "ADVERSARY'S CONFESSION",
        "hero": "Classified hacker forum transcript document with redacted usernames and neon green quote",
        "props": ["Evidence marker placard 'EXHIBIT A'", "Dark web onion logo cutout"],
        "s1": "Transcript document drops into center frame.",
        "s2": "Evidence marker placard drops beside top-left corner.",
        "s3": "Neon green highlighter line sweeps across the attacker's admission.",
        "s4": "Permanent spatial anchor hold."
    },

    # BLOCK 5: THE UNSEEN ENTRANCE: UNMANAGED ENDPOINTS (Beats 25-30)
    {
        "id": 25, "start": 184.0, "end": 191.6,
        "ja": "10月6日、オレンジシェアの報道によれば、ランサムウェアグループのQilinは、日本の中小企業を狙いやすい標的として名指ししていました。",
        "idea": "QILIN NAMES JAPAN SMES", "title": "QILIN'S TARGET LIST",
        "hero": "Black dossiers folder marked 'QILIN RANSOM GROUP' with dossier papers spilling out",
        "props": ["Map of Japanese industrial manufacturing prefectures", "Crimson crosshair pin"],
        "s1": "Qilin dossier folder drops heavily onto desk.",
        "s2": "Folder flings open revealing list of Japanese regional SME categories.",
        "s3": "Crimson crosshair pin strikes Nagoya and Osaka industrial hubs.",
        "s4": "Locked spatial anchor hold, no 3D drift."
    },
    {
        "id": 26, "start": 191.6, "end": 199.3,
        "ja": "理由はセキュリティ対策の遅れです。言葉ではありません。これが入口の答えです。",
        "idea": "DELAYED DEFENSE, NOT LANGUAGE", "title": "THE REAL CAUSE: LAG",
        "hero": "Large bold circular stamp reading 'SECURITY LAG' impacting over Japanese language banner",
        "props": ["Broken padlock with loose shackle", "Red wax seal"],
        "s1": "Japanese language banner lies flat on table.",
        "s2": "Broken padlock drops beside banner with dull metallic thud.",
        "s3": "'SECURITY LAG' circular red stamp strikes directly over the banner.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 27, "start": 199.3, "end": 207.0,
        "ja": "5日後の10月11日、au Webポータルは、AIツールが企業ネットワークの「隅っこの脆弱性」を体系的に探し出していると伝えました。",
        "idea": "AUTOMATED SCANNING OF SHADOW IT", "title": "SCANNING THE EDGES",
        "hero": "Radar scanning grid overlaying complex enterprise IT topology chart",
        "props": ["Flashing green blip cutout on outer perimeter", "au Web Portal citation strip"],
        "s1": "Enterprise topology chart unrolls across table.",
        "s2": "Radar scanning cone sweeps clockwise across the diagram.",
        "s3": "Flashing green warning blip fixes on an obscure peripheral node.",
        "s4": "Locked spatial anchor hold."
    },
    {
        "id": 28, "start": 207.0, "end": 214.6,
        "ja": "長く見落とされた端末。古い接続口。管理表に載っていない機器。",
        "idea": "THREE FORGOTTEN ASSETS", "title": "THE FORGOTTEN THREE",
        "hero": "Trio of vintage forgotten hardware cutouts: beige desktop PC, obsolete VPN router, unmanaged NAS drive",
        "props": ["Thick layer of dust texture decal", "Red question tag on cable"],
        "s1": "Three dusty hardware units drop onto desk in staggered cascade.",
        "s2": "Loose dangling red Ethernet cable drops between them.",
        "s3": "Yellow caution frames lock around all three units.",
        "s4": "Permanent anchor hold with micro shadow breathing."
    },
    {
        "id": 29, "start": 214.6, "end": 222.3,
        "ja": "入口は、管理表の外にあった。",
        "idea": "OUTSIDE THE ASSET REGISTRY", "title": "OUTSIDE THE LEDGER",
        "hero": "Official corporate IT asset ledger document with blank lines and red line drawn past the margin",
        "props": ["Red ink pen running off edge of table", "Lone uncatalogued device icon"],
        "s1": "Official asset ledger sheet lands cleanly in center.",
        "s2": "Red pen draws down the roster, then zips off the right edge into blank space.",
        "s3": "Uncatalogued device icon appears in the empty space outside the document boundary.",
        "s4": "Locked spatial anchor hold, high-contrast editorial look."
    },
    {
        "id": 30, "start": 222.3, "end": 230.0,
        "ja": "ここが一つ目の結び目です。侵入の段階で効いているのは、文章ではなく走査です。",
        "idea": "FIRST KNOT: SCANNING WINS", "title": "FIRST KNOT: SCANNING",
        "hero": "Heavy maritime nautical rope tied in a tight intricate knot with red forensic thread",
        "props": ["Digital port scan readout strip", "Draft email draft discarded in wastebasket"],
        "s1": "Nautical knot drops into center canvas with rope texture settling.",
        "s2": "Port scanner readout strip feeds out from beneath the knot.",
        "s3": "Bold gold text badge 'KNOT 01: SYSTEM SCAN' stamps across rope.",
        "s4": "Living poster anchor hold."
    },

    # BLOCK 6: FIRST NODE: SYSTEMIC SCANNING VS TRANSLATION (Beats 31-36)
    {
        "id": 31, "start": 230.0, "end": 237.6,
        "ja": "では、侵入の後には何が変わるのでしょうか？盗んだ資料を読む。価値を見積もる。脅迫文を書く。",
        "idea": "POST-BREACH TRIAGE", "title": "POST-BREACH TRIAGE",
        "hero": "Three-tiered paper filing sorting rack holding confidential stolen dossiers",
        "props": ["Stolen salary register", "Intellectual property patent drawing", "Customer database printout"],
        "s1": "Three-tiered sorting rack drops onto center desk.",
        "s2": "Three stolen document batches slide rapidly into the three shelves.",
        "s3": "Appraisal price tag decals flutter onto each tier.",
        "s4": "Permanent spatial hold with subtle paper breathing."
    },
    {
        "id": 32, "start": 237.6, "end": 245.3,
        "ja": "かつてここには日本語を読める人材が必要でした。人を雇えば費用がかかり、返事を待てば時間がかかる。",
        "idea": "THE OLD HUMAN TRANSLATOR BOTTLENECK", "title": "THE HUMAN BOTTLENECK",
        "hero": "Old vintage analog clock with frozen hands beside an empty desk nameplate 'Translator'",
        "props": ["Stack of unpaid translation invoices", "Muted gray telephone cutout"],
        "s1": "Translator desk nameplate and vintage clock drop onto desk.",
        "s2": "Stack of translation invoices thuds down beside the clock.",
        "s3": "Red circular delay spiral draws around the clock face.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 33, "start": 245.3, "end": 253.0,
        "ja": "その摩擦が、海外の集団にとって割に合わない理由の一つだったと考えられます。",
        "idea": "HISTORIC UNPROFITABILITY", "title": "UNPROFITABLE FRICTION",
        "hero": "Traditional iron merchant scales heavily tilted down on the cost side, empty on profit",
        "props": ["Japanese yen banknotes with high expense tags", "Tiny ransom coin payoff"],
        "s1": "Iron merchant scales drop onto center canvas.",
        "s2": "Heavy expense weights slam into the expense pan, dropping it to desk level.",
        "s3": "Tiny ransom payoff coin barely moves the profit pan.",
        "s4": "Locked spatial anchor hold, 2D collage composition."
    },
    {
        "id": 34, "start": 253.0, "end": 260.6,
        "ja": "10月9日、日テレNEWS NNNは、日本の個人情報や企業データが、信頼性と支払い能力への評価から、ダークウェブで高値で取引されていると報じました。",
        "idea": "PREMIUM VALUE OF JAPANESE DATA", "title": "THE DATA PREMIUM",
        "hero": "Dark web marketplace listing card with gold price tag 'PREMIUM: JAPANESE CORPORATE DB'",
        "props": ["Japanese passport graphic cutout", "Dark web auction countdown timer"],
        "s1": "Marketplace listing card drops onto dark aged newsprint background.",
        "s2": "Gold price tag decal stamps down firmly over listing title.",
        "s3": "Green ascending price curve draws upward along right edge.",
        "s4": "Permanent anchor hold, shadow breathing <= 2px."
    },
    {
        "id": 35, "start": 260.6, "end": 268.3,
        "ja": "日本の標的は高く売れる。けれど買い手は、日本語を読めなければ価値を引き出せない。",
        "idea": "HIGH VALUE BUT LOCKED SCRIPT", "title": "THE ENCRYPTED POTENTIAL",
        "hero": "Thick Japanese financial ledger bound with heavy brass padlock and chain",
        "props": ["Golden Yen symbols glowing inside ledger", "Heavy iron padlock keyhole"],
        "s1": "Chained ledger drops heavily onto center desk.",
        "s2": "Brass chain links tighten with audible paper crease settling.",
        "s3": "Muted gold glow bleeds from the page edges between the chains.",
        "s4": "Locked living poster anchor hold."
    },
    {
        "id": 36, "start": 268.3, "end": 276.0,
        "ja": "侵入後に変わったのは、この二つ目の結び目です。AIが、その読み解きの費用を下げつつあるのです。",
        "idea": "SECOND KNOT: TRANSLATION ARBITRAGE", "title": "SECOND KNOT: ARBITRAGE",
        "hero": "Second heavy nautical rope knot with AI optical scan beam slicing through center rope fiber",
        "props": ["High-speed text translation cascade strip", "Gold badge 'KNOT 02: PARSING COST'"],
        "s1": "Second nautical rope knot drops onto desk.",
        "s2": "Laser-thin blue optical scanning line cuts across the fibers.",
        "s3": "Gold badge 'KNOT 02' stamps firmly across the knot center.",
        "s4": "Static living poster anchor hold."
    },

    # BLOCK 7: SECOND NODE: DARK WEB JAPANESE DATA (Beats 37-42)
    {
        "id": 37, "start": 276.0, "end": 283.6,
        "ja": "残る工程は一つ。身代金の交渉テーブルです。",
        "idea": "THE FINAL STAGE: NEGOTIATION", "title": "THE LAST MILE",
        "hero": "Long dark conference room negotiation table seen from top-down overhead perspective",
        "props": ["Two empty opposing chairs", "Single microphone and ransom note on table"],
        "s1": "Conference table cutout drops into center-left negative space.",
        "s2": "Two chairs slide into place on opposing ends with crisp paper stop.",
        "s3": "Single white ransom note lands squarely in the exact center.",
        "s4": "Locked spatial anchor hold."
    },
    {
        "id": 38, "start": 283.6, "end": 291.3,
        "ja": "最後まで必要だと思われていた日本語の担い手は、今も雇われているのでしょうか？",
        "idea": "IS THE HUMAN BROKER STILL THERE?", "title": "THE EXTINCT BROKER",
        "hero": "Empty vintage office desk with unplugged headset and faded silhouette of a human translator",
        "props": ["Red question mark seal", "Discontinued contract notice"],
        "s1": "Empty desk cutout drops onto canvas.",
        "s2": "Unplugged telephone headset lands on desktop with wire coiled.",
        "s3": "Red question mark seal stamps directly over the empty chair.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 39, "start": 291.3, "end": 299.0,
        "ja": "答えは、10月12日の報道にあります。TBS NEWS DIGのnews23は、生成AIによって日本語での身代金交渉をリアルタイムで進められるようになり、日本語を話す仲介役を雇う必要がなくなったと報じました。",
        "idea": "TBS REPORT: ZERO HUMAN BROKER", "title": "REAL-TIME AI NEGOTIATOR",
        "hero": "Split-screen dialogue terminal showing real-time English-to-Japanese negotiation chat stream",
        "props": ["TBS NEWS DIG news23 badge clipping", "Zero human broker stamp"],
        "s1": "Chat terminal window drops onto center workspace.",
        "s2": "English extortion demand types in, instantly mirroring into polite Japanese keigo.",
        "s3": "Red stamp 'HUMAN BROKER: NOT REQUIRED' slams onto lower margin.",
        "s4": "Locked living poster anchor hold."
    },
    {
        "id": 40, "start": 299.0, "end": 306.6,
        "ja": "冒頭の「誰が交渉の判断を担うのか」という問いも、ここで解けます。担い手は人からツールへ移りつつあります。",
        "idea": "HUMAN TO TOOL SHIFT", "title": "TOOL REPLACES HUMAN",
        "hero": "Stylized graphic novel transformation: Human silhouette dissolving into algorithmic flowchart node",
        "props": ["Flowchart decision diamond cutout", "Directional arrow line"],
        "s1": "Human silhouette stands on left quadrant.",
        "s2": "Directional arrow draws rightward into algorithmic diamond node.",
        "s3": "Human silhouette dissolves into halftone dot matrix.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 41, "start": 306.6, "end": 314.3,
        "ja": "そして「10倍」の意味も解き明かされます。この見方が正しければ、それは攻撃力の倍率ではなく、交渉一件あたりの人手の話だった可能性があります。",
        "idea": "THE 10X DECODED: HUMAN BANDWIDTH", "title": "10X BANDWIDTH DECODED",
        "hero": "One lone hacker figure operating 10 simultaneous negotiation terminals fanned out in a circle",
        "props": ["10 interconnected glowing screen cutouts", "Bold numeral '1:10' badge"],
        "s1": "Center operator silhouette drops onto desk.",
        "s2": "Ten miniature screen cards snap into an arc around the operator.",
        "s3": "Gold badge '1 OPERATOR : 10 NEGOTIATIONS' stamps across top margin.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 42, "start": 314.3, "end": 322.0,
        "ja": "8日後、産経ニュースは、犯罪組織がAI翻訳の提供役、脆弱性の探索役、恐喝の実行役へと分かれ、捜査による特定を難しくしていると報じました。",
        "idea": "THE TRIAD OF CRIMINAL SPECIALIZATION", "title": "THE THREE SPECIALISTS",
        "hero": "Triangle interlocking diagram of three specialized syndicate roles: Translation, Scanning, Extortion",
        "props": ["Three distinct syndicate badge tokens", "Dotted evasion circle"],
        "s1": "Triangle interlocking blueprint lands on desk.",
        "s2": "Three specialized badge tokens drop into the three vertices.",
        "s3": "Rotating dotted evasion circle wraps around the triangle.",
        "s4": "Locked spatial anchor hold, no camera movement."
    },

    # BLOCK 8: THE NEGOTIATION TABLE: REAL-TIME AI (Beats 43-48)
    {
        "id": 43, "start": 322.0, "end": 329.6,
        "ja": "au Webポータルは、人間の操作なしに侵入を試み続ける半自律的なスクリプトの事例も伝えています。",
        "idea": "SEMI-AUTONOMOUS SCRIPTS", "title": "AUTONOMOUS SCRIPTS",
        "hero": "Looping paper tape punch reel feeding endless automated attack scripts into a terminal",
        "props": ["Continuous green status light indicator", "au Web Portal citation tag"],
        "s1": "Punch tape reel drops onto left desk.",
        "s2": "Paper tape feeds smoothly across the desk to the terminal intake.",
        "s3": "Continuous looping arrow decal stamps over the tape path.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 44, "start": 329.6, "end": 337.3,
        "ja": "では、誰が得をしたのか。東洋経済オンラインが引用したセキュリティ調査は、自律的なAI攻撃ソフトではなく、通信費用の急落こそが、日本企業への恐喝を商業的に成り立たせる主な要因だと示しました。",
        "idea": "COMMUNICATION COST COLLAPSE", "title": "PLUMMETING COSTS",
        "hero": "Vintage telecom fee chart with steep plunging cliff graph line dropping to near-zero",
        "props": ["Toyo Keizai report clipping", "Down-pointing red caliper"],
        "s1": "Telecom fee chart drops into center canvas.",
        "s2": "Red plummeting graph line draws sharply downward to baseline.",
        "s3": "Red caliper clamps down on the near-zero cost point.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 45, "start": 337.3, "end": 345.0,
        "ja": "得をしたのは、翻訳、探索、恐喝を分業し、それぞれの費用を下げた仕組みです。AIそのものが首謀者ではありません。",
        "idea": "THE SYSTEM, NOT AI MASTERMIND", "title": "THE SYSTEM PROFITED",
        "hero": "Industrial assembly line diagram with three robotic conveyor arms stamping documents",
        "props": ["Syndicate profit safe box cutout", "Red cross through 'AI MASTERMIND' icon"],
        "s1": "Assembly line diagram unrolls across canvas.",
        "s2": "Three conveyor arms drop into place along the line.",
        "s3": "Red X stamps out the cartoonish 'evil AI brain' icon in corner.",
        "s4": "Locked spatial anchor hold."
    },
    {
        "id": 46, "start": 345.0, "end": 352.6,
        "ja": "ただし、線を引く必要があります。要求額、実際の支払額、操業停止による損害は、別々の数字です。",
        "idea": "THREE DISTINCT METRICS", "title": "THREE SEPARATE NUMBERS",
        "hero": "Three separate glass specimen slides with distinct numerical tags: Demand, Ransom Paid, Business Loss",
        "props": ["Black dividing line drawn with ruler", "Forensic evidence ruler"],
        "s1": "Three glass specimen slides drop in a row across desk.",
        "s2": "Heavy black dividing ink line draws clean separations between them.",
        "s3": "Distinct label stickers slap down below each respective slide.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 47, "start": 352.6, "end": 360.3,
        "ja": "それらを足して犯罪者の利益と呼ぶことはできません。今回の報道群には、特定事件の送金記録は示されていません。",
        "idea": "NO VERIFIED TRANSFER LEDGER", "title": "NO PAYMENT LEDGER",
        "hero": "Empty cryptographic blockchain transfer ledger page marked with missing transaction hash notices",
        "props": ["Unverified data watermark", "Red question mark seal"],
        "s1": "Blockchain transaction ledger sheet drops onto desk.",
        "s2": "Magnifying lens reveals blank recipient hash lines.",
        "s3": "Red watermark 'NO TRANSACTION RECORD' stamps across page.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 48, "start": 360.3, "end": 368.0,
        "ja": "明らかになったのは採算の構造であり、帳簿ではありません。",
        "idea": "PROFIT STRUCTURE, NOT ACCOUNTING BOOK", "title": "STRUCTURE, NOT LEDGER",
        "hero": "Architectural economic framework blueprint contrasted with an unverified accounting logbook",
        "props": ["Architectural T-square ruler", "Wax evidence seal"],
        "s1": "Framework blueprint rolls out across desk.",
        "s2": "T-square ruler slides down aligning the structural pillars.",
        "s3": "Wax evidence seal stamps the structural diagram as confirmed.",
        "s4": "Locked spatial hold, shadow breathing <= 2px."
    },

    # BLOCK 9: CRIMINAL DIVISION OF LABOR (Beats 49-54)
    {
        "id": 49, "start": 368.0, "end": 375.6,
        "ja": "結末を整理し、冒頭の問いを閉じます。日本語の壁は崩れたのか。",
        "idea": "CLOSING THE CENTRAL QUESTION", "title": "DID THE WALL FALL?",
        "hero": "Monolithic stone fortress wall with visible deep vertical structural fracture down center",
        "props": ["First question card from Scene 01", "Forensic inspection pointer"],
        "s1": "Stone fortress wall cutout drops onto center canvas.",
        "s2": "First question card from Scene 01 slides in beside wall.",
        "s3": "Deep vertical fracture line draws down the wall with subtle dust settling.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 50, "start": 375.6, "end": 383.3,
        "ja": "答えは、崩れた、しかしそれだけで企業が倒れたわけではない、です。",
        "idea": "THE NUANCED VERDICT", "title": "COLLAPSED, BUT NOT FATAL",
        "hero": "Two-part verdict card: 'WALL: COLLAPSED' in red / 'COLLAPSE REASON: SYSTEMIC' in navy",
        "props": ["Official judge's gavel cutout", "Double-ruled border frame"],
        "s1": "Verdict card drops onto center workspace.",
        "s2": "Judge's gavel impacts the lower desk with paper sound design.",
        "s3": "Two-color border frame snaps into position locking the card.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 51, "start": 383.3, "end": 391.0,
        "ja": "壁の向こうにあったのは、未更新の機器、緩い権限、高値で売れるデータでした。",
        "idea": "WHAT LAY BEHIND THE WALL", "title": "BEHIND THE WALL",
        "hero": "Torn wall opening revealing three forensic exhibits: Old Firmware, Loose Permissions, Golden Customer Data",
        "props": ["Torn jagged paper edge overlay", "Flashlight beam cutout"],
        "s1": "Torn wall opening expands across center canvas.",
        "s2": "Three internal exhibits slide into the illuminated opening.",
        "s3": "Flashlight beam cutout shines directly across all three exhibits.",
        "s4": "Locked spatial hold, no 3D distortion."
    },
    {
        "id": 52, "start": 391.0, "end": 398.6,
        "ja": "言葉の摩擦が守っていたのは、その弱さを隠す時間だったのです。",
        "idea": "LANGUAGE WAS BORROWED TIME", "title": "BORROWED TIME EXPIRES",
        "hero": "Vintage hourglass with shattered glass chamber, sand spilling out across obsolete security manuals",
        "props": ["Broken glass shard cutouts", "Old security handbook"],
        "s1": "Hourglass lands on desk, glass chamber cracking on impact.",
        "s2": "Red sand spills outward covering the old security handbook.",
        "s3": "Banner reading 'BORROWED TIME HAS RUN OUT' drops over sand.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 53, "start": 398.6, "end": 406.3,
        "ja": "採算は、翻訳と交渉の人件費が消える場所から変わります。",
        "idea": "PROFIT RESETS WHERE WAGES DISAPPEAR", "title": "WHERE WAGES DISAPPEAR",
        "hero": "Corporate payroll expense ledger with 'TRANSLATION STAFF' line crossed out with heavy red pen line",
        "props": ["Red ink fountain pen", "Calculated savings badge in green"],
        "s1": "Payroll ledger drops onto center desk.",
        "s2": "Red fountain pen slashes clean thick line through translation staff row.",
        "s3": "Green savings badge pops out on the margin with 'COST -> ZERO'.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 54, "start": 406.3, "end": 414.0,
        "ja": "その後の動きも始まっています。TBS NEWS DIGは、言語的な孤立による保護効果は終わったという専門家の警告を伝えました。",
        "idea": "LINGUISTIC ISOLATION OVER", "title": "ISOLATION HAS ENDED",
        "hero": "Map of Japanese archipelago severed from its imaginary protective moat by red dashed vector lines",
        "props": ["TBS NEWS DIG microphone flag", "Official warning dispatch bulletin"],
        "s1": "Japanese archipelago map card drops into center frame.",
        "s2": "Protective moat illustration surrounding islands peels away.",
        "s3": "Red dashed vector lines connect the islands directly to global network.",
        "s4": "Locked spatial hold, high editorial contrast."
    },

    # BLOCK 10: THE COST STRUCTURE: BALANCE SHEET (Beats 55-60)
    {
        "id": 55, "start": 414.0, "end": 421.6,
        "ja": "日テレNEWS NNNによれば、当局は経営層に、社員教育とアクセス管理の見直しを求めています。",
        "idea": "REGULATORY DIRECTIVE TO EXECUTIVES", "title": "REGULATORY MANDATE",
        "hero": "Official Japanese government administrative guidance dispatch with red ministerial seal",
        "props": ["Executive boardroom table cutout", "Red official Hanko seal"],
        "s1": "Government guidance document lands in center frame.",
        "s2": "Official red ministerial seal impacts the document footer with heavy thud.",
        "s3": "Two directive checkmarks lock onto 'Education' and 'Access Control'.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 56, "start": 421.6, "end": 429.3,
        "ja": "ZDNET Japanが報じたように、国内のセキュリティ企業は、AIが書いた日本語の文書に特有のパターンやメタデータの痕跡を検出するモデルを導入し始めました。",
        "idea": "AI METADATA DETECTION MODELS", "title": "AI METADATA DETECTORS",
        "hero": "Digital oscilloscope screen inspecting email metadata headers with synthetic probability score",
        "props": ["ZDNET citation tag", "Green synthetic artifact waveform cutout"],
        "s1": "Oscilloscope screen cutout drops onto desk.",
        "s2": "Email header data lines scroll through inspection window.",
        "s3": "Synthetic probability meter jumps to 98% with red alert border.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 57, "start": 429.3, "end": 437.0,
        "ja": "あなたの会社が文章の違和感に頼って判断してきたなら、その基準はもう機能しません。",
        "idea": "GUT-FEELING CRITERIA OBSOLETE", "title": "THE BROKEN CRITERION",
        "hero": "Old corporate compliance checklist with the rule 'Check for odd Japanese phrasing' stamped 'OBSOLETE'",
        "props": ["Heavy red 'VOID' rubber stamp", "Torn checklist corner"],
        "s1": "Old compliance checklist drops onto desk.",
        "s2": "Heavy red 'VOID' stamp slams down across the language check rule.",
        "s3": "Paper fibers tear slightly under the stamp impact.",
        "s4": "Locked spatial anchor hold."
    },
    {
        "id": 58, "start": 437.0, "end": 444.6,
        "ja": "では、何が残るのでしょうか？誰が何にアクセスできるか。止まった後にどれだけ早く戻れるか。",
        "idea": "TWO REAL DEFENSIVE PILLARS", "title": "THE REAL DEFENSE",
        "hero": "Two monumental stone pillars labeled 'ACCESS GOVERNANCE' and 'RECOVERY SPEED'",
        "props": ["Architectural foundation block", "Steel reinforcement brackets"],
        "s1": "Foundation block drops onto center canvas.",
        "s2": "Two stone pillars drop into foundation sockets with solid thud.",
        "s3": "Steel reinforcement brackets clamp around each pillar base.",
        "s4": "Permanent spatial hold, shadow breathing <= 2px."
    },
    {
        "id": 59, "start": 444.6, "end": 452.3,
        "ja": "その責任を誰が負うか。この結末の後に残る防御は、そこにあります。",
        "idea": "EXECUTIVE ACCOUNTABILITY", "title": "WHO OWNS THE RISK?",
        "hero": "Executive boardroom signature registry document with fountain pen resting in signature line",
        "props": ["Personal Hanko seal of CEO", "Legal liability disclaimer badge"],
        "s1": "Signature registry dossier drops onto center desk.",
        "s2": "CEO's personal Hanko seal strikes firmly on the designated signature box.",
        "s3": "Gold 'EXECUTIVE ACCOUNTABILITY' badge stamps above the registry.",
        "s4": "Locked living poster anchor hold."
    },
    {
        "id": 60, "start": 452.3, "end": 460.0,
        "ja": "教訓には限界もあります。今回の報道だけでは、AIが攻撃件数をどれだけ押し上げたのかは証明できません。",
        "idea": "LIMITS OF THE EVIDENCE", "title": "EVIDENTIARY BOUNDARIES",
        "hero": "Forensic balance scale with factual evidence dossiers on one side, conjecture on the other",
        "props": ["Evidence marker flag 'LIMIT OF PROOF'", "Lead measurement weight"],
        "s1": "Forensic scale lands on center desk.",
        "s2": "Factual evidence folder drops into verified pan.",
        "s3": "Yellow caution boundary tape wraps around the unproven aggregate claims.",
        "s4": "Static living poster anchor hold."
    },

    # BLOCK 11: MODERN MIRROR: LINGUISTIC ISOLATION OVER (Beats 61-66)
    {
        "id": 61, "start": 460.0, "end": 467.6,
        "ja": "分かっているのは、費用の構造が変わったという事実です。",
        "idea": "THE CERTAIN FACT: COST SHIFT", "title": "THE COST SHIFT",
        "hero": "Massive concrete cornerstone block carved with 'EXTORTION COST: DROPPED 90%'",
        "props": ["Chisel and mallet tools resting on block", "Deep relief carving texture"],
        "s1": "Cornerstone block drops heavily into center canvas.",
        "s2": "Chisel and mallet drop beside block with metallic clatter.",
        "s3": "Gold inlay fills the engraved letters of the cost shift.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 62, "start": 467.6, "end": 475.3,
        "ja": "届いた一通が、どれほど丁寧でも。",
        "idea": "REGARDLESS OF POLITENESS", "title": "REGARDLESS OF POLITENESS",
        "hero": "Pristine white Japanese ceremonial gift envelope (Noshi) with decorative red and gold Mizuhiki ribbon",
        "props": ["Hidden cyber attack code revealed behind the ribbon", "X-ray transparency window"],
        "s1": "Ceremonial Noshi envelope drops onto center desk.",
        "s2": "Decorative Mizuhiki ribbon tightens and settles on the envelope.",
        "s3": "X-ray inspection window slides across, revealing malicious script inside.",
        "s4": "Locked living poster anchor hold."
    },
    {
        "id": 63, "start": 475.3, "end": 483.0,
        "ja": "自然な日本語は、安全の証拠ではない。",
        "idea": "NATURAL JAPANESE != SECURITY", "title": "NATURAL IS NOT SAFE",
        "hero": "Massive bold editorial billboard cutout with definitive documentary statement stamped in crimson",
        "props": ["Solid crimson warning seal", "Black industrial frame"],
        "s1": "Heavy billboard frame drops into center canvas.",
        "s2": "Crimson seal stamps firmly in the lower right corner.",
        "s3": "Underline accent bar snaps into place beneath the statement.",
        "s4": "Final rigid living poster hold, micro paper shadow flutter."
    },
    {
        "id": 64, "start": 483.0, "end": 490.6,
        "ja": "防御の基準を言語から構造へと移す時が来ています。",
        "idea": "SHIFTING FROM LANGUAGE TO STRUCTURE", "title": "FROM WORDS TO STRUCTURE",
        "hero": "Architectural shift diagram: Moving foundation blocks from 'Language' to 'Zero Trust Network'",
        "props": ["Architectural compass", "Blue structural grid blueprint"],
        "s1": "Blueprint rolls open on desk.",
        "s2": "Foundation blocks slide from left (Language) to right (Structure).",
        "s3": "Architectural compass circles the new structural foundation.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 65, "start": 490.6, "end": 498.3,
        "ja": "ネットワークの端にある見落とされた端末を、今すぐ点検してください。",
        "idea": "ACTIONABLE CALL: AUDIT EDGE DEVICES", "title": "AUDIT THE PERIMETER",
        "hero": "Emergency IT audit checklist card with glowing magnifying lens examining remote terminal socket",
        "props": ["Emergency red clip", "Network plug tester"],
        "s1": "Checklist card drops into center frame.",
        "s2": "Magnifying lens slides over the remote terminal entry.",
        "s3": "Red alert indicator switches to active audit mode.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 66, "start": 498.3, "end": 506.0,
        "ja": "パスワードの多要素認証を、全社員に例外なく適用してください。",
        "idea": "ENFORCE UNIVERSAL MFA", "title": "UNIVERSAL MFA NOW",
        "hero": "Smartphone hardware authenticator cutout displaying shifting 6-digit MFA token code beside security key",
        "props": ["FIDO2 USB hardware security key", "Green encrypted lock icon"],
        "s1": "Hardware token smartphone and FIDO2 key drop onto desk.",
        "s2": "FIDO2 key plugs into side slot with crisp snap.",
        "s3": "Green encrypted lock badge stamps above the device.",
        "s4": "Locked living poster anchor hold."
    },

    # BLOCK 12: LIVING WARNING: NATURAL JAPANESE IS NOT SAFETY (Beats 67-72)
    {
        "id": 67, "start": 506.0, "end": 513.6,
        "ja": "バックアップが本当にオフラインで隔離されているか、明日確認してください。",
        "idea": "ISOLATE OFFLINE BACKUPS", "title": "VERIFY OFFLINE BACKUPS",
        "hero": "Heavy steel air-gapped backup tape vault box with physical mechanical lever in locked position",
        "props": ["Disconnected gold optical cable", "Air-gap physical separation barrier"],
        "s1": "Backup tape vault box lands squarely on desk.",
        "s2": "Mechanical lever slams down into locked offline posture.",
        "s3": "Disconnected cable pulls 10cm away, visually enforcing physical air-gap.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 68, "start": 513.6, "end": 521.3,
        "ja": "誰がインシデントの指揮を執るのか、決定権者を文書で定めてください。",
        "idea": "DOCUMENT INCIDENT COMMANDER", "title": "NAME THE COMMANDER",
        "hero": "Official Emergency Crisis Command Protocol document with single highlighted Commander box",
        "props": ["Emergency red phone cutout", "Gold command seal"],
        "s1": "Crisis Protocol document unrolls across desk.",
        "s2": "Command seal strikes the designated Incident Commander title.",
        "s3": "Red emergency phone cutout drops beside the document.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 69, "start": 521.3, "end": 529.0,
        "ja": "言葉の壁が消えた世界では、準備の遅れた者から順に狙われます。",
        "idea": "THE UNPREPARED TARGETED FIRST", "title": "THE UNPREPARED FIRST",
        "hero": "Chronological target queue card with unpatched entities prioritized by algorithmic ranking",
        "props": ["Ranking priority arrows", "Red countdown clock cutout"],
        "s1": "Target queue card slides in from upper margin.",
        "s2": "Red priority arrow drops onto the first unprepared slot.",
        "s3": "Countdown timer badge locks onto the top position.",
        "s4": "Locked spatial hold, no 3D movement."
    },
    {
        "id": 70, "start": 529.0, "end": 536.6,
        "ja": "あなたの組織を守るのは、メールの文面を疑う目ではなく、侵入を前提とした仕組みです。",
        "idea": "ASSUME BREACH PHILOSOPHY", "title": "ASSUME BREACH",
        "hero": "Zero Trust architectural shield blueprint with layered concentric rings of internal defense",
        "props": ["Concentric circular ring gates", "Hardened steel lockbolt"],
        "s1": "Zero Trust concentric blueprint unrolls in center.",
        "s2": "Three concentric ring gates snap into place from outside in.",
        "s3": "Central lockbolt drops into the core database chamber.",
        "s4": "Static living poster anchor hold."
    },
    {
        "id": 71, "start": 536.6, "end": 544.3,
        "ja": "技術の進化を恐れるのではなく、自らの弱点に向き合うこと。",
        "idea": "CONFRONT INTERNAL WEAKNESS", "title": "CONFRONT THE WEAKNESS",
        "hero": "Forensic mirror reflection card reflecting internal corporate network vulnerabilities honestly",
        "props": ["Brass inspection calipers", "Remediation action roadmap checklist"],
        "s1": "Mirror reflection card drops onto center canvas.",
        "s2": "Remediation action checklist rolls out beside it.",
        "s3": "Brass calipers measure the gap between current state and secure state.",
        "s4": "Permanent spatial anchor hold."
    },
    {
        "id": 72, "start": 544.3, "end": 551.93,
        "ja": "それが、日本語の壁が消えた時代に、日本企業が生き残る唯一の道です。",
        "idea": "THE ONLY PATH TO SURVIVAL", "title": "THE SURVIVAL MANDATE",
        "hero": "Official Archival Evidence Case Folder labeled 'JP_EP0003: CLOSED' stamped with gold seal of resilience",
        "props": ["Gold resilience wax seal", "Crimson ribbon bookmark resting on closed folder"],
        "s1": "Archival case folder closes with crisp heavy paper snap.",
        "s2": "Gold wax seal impacts firmly over the closure ribbon.",
        "s3": "Bold documentary closure stamp 'EVIDENCE SECURED' frames the lower edge.",
        "s4": "Final rigid living poster hold, micro shadow breathing <= 2px. Fade to black."
    }
]

def generate_director_plan(episode_id: str = "JP_EP0003_japan_ai_ransom_economy") -> tuple:
    scenes = []
    prompts_forge = []
    
    for i, meta in enumerate(BEATS_METADATA, start=1):
        block_idx = (i - 1) // 6
        block = BLOCKS_CONFIG[min(block_idx, len(BLOCKS_CONFIG) - 1)]
        
        scene_id = f"SCENE_{i:02d}"
        seq_block = f"{block['block_id']}_{block['title'].replace(' ', '_').replace(':', '')}"
        
        image_prompt = (
            f"Editorial investigative documentary frame in signature VOX paper-cut collage style. "
            f"[Layer 1: {block['canvas_workspace']}] -> "
            f"[Layer 2: bold flat geometric color block in {block['theme_color']}] -> "
            f"[Layer 3: negative space reserved for large bold editorial typography '{meta['title']}', occupying 25-35% of frame] -> "
            f"[Layer 4: high-contrast tactile paper cutout subject with crisp 2-4px white deckle edge and realistic soft drop shadow: {meta['hero']}. Interacting elements: {', '.join(meta['props'])}] -> "
            f"[Layer 5: vintage print ink texture, natural paper grain, subtle fold creases, authentic newspaper print misregistration]. "
            f"Strictly locked color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A, Charcoal #1A1A1A on Off-white Cream #F4F1EA. "
            f"Clear object-assembly composition, strong editorial hierarchy, tactile paper craft. "
            f"Negative prompt: no typography, no letters, no text, no captions, no sub-titles, no watermarks, no labels, no words, "
            f"no clutter, no unnecessary objects, no 3D photorealistic rooms, no anime, no cartoon, no CGI glossy look, maintain clean premium VOX editorial collage."
        )
        
        i2v_prompt = (
            f"Editorial paper cutout animation in Vox documentary style. Headline: '{meta['title']}'. "
            f"IMAGE-TO-VIDEO TECHNICAL DIRECTIVE: [Camera: STATIC_OVERHEAD]. "
            f"[Timeline Kinematics: From 0.0s to 2.0s: {meta['s1']} "
            f"From 2.0s to 4.5s: {meta['s2']} "
            f"From 4.5s to 6.0s: {meta['s3']} "
            f"From 6.0s to 8.0s: {meta['s4']}]. "
            f"[Pacing: Restrained mechanical paper physics, snappy stops, micro settling]. "
            f"[Constraints: Strict flat 2D tactile paper collage physics, zero 3D fluid morphing, zero face warping]."
        )
        
        scene_data = {
            "scene_id": scene_id,
            "beat_id": f"BEAT_{i:02d}",
            "sequence_block": seq_block,
            "block_id": block["block_id"],
            "act": block["act"],
            "time_start_s": meta["start"],
            "time_end_s": meta["end"],
            "duration_s": round(meta["end"] - meta["start"], 2),
            "sentence": meta["ja"],
            "core_idea": meta["idea"],
            "editorial_title": meta["title"],
            "canvas_workspace": block["canvas_workspace"],
            "theme_color": block["theme_color"],
            "hero_cutout_object": meta["hero"],
            "interacting_objects": meta["props"],
            "kinematics_4_phases": {
                "s1_entry": meta["s1"],
                "s2_impact": meta["s2"],
                "s3_vector_growth": meta["s3"],
                "s4_spatial_hold": meta["s4"]
            },
            "image_prompt": image_prompt,
            "flow_video_prompt": i2v_prompt
        }
        scenes.append(scene_data)
        
        prompts_forge.append({
            "scene_id": scene_id,
            "beat_id": f"BEAT_{i:02d}",
            "time_range": f"{meta['start']:.1f}s - {meta['end']:.1f}s",
            "image_prompt": image_prompt,
            "flow_video_prompt": i2v_prompt
        })
        
    director_plan = {
        "schema_version": "director_plan.v2",
        "rule_compliance": ["RULE_118", "RULE_120", "RULE_122", "RULE_126", "RULE_136", "RULE_140"],
        "episode_id": episode_id,
        "title": "Japan AI Ransom Economy: When Linguistic Moats Evaporate",
        "market": "JA",
        "format": "VOX_CONTINUOUS_TACTILE_PAPER_COLLAGE",
        "audio_runtime_seconds": 551.93,
        "total_beats": len(scenes),
        "total_sequence_blocks": len(BLOCKS_CONFIG),
        "average_beat_duration_seconds": round(551.93 / len(scenes), 2),
        "blocks": BLOCKS_CONFIG,
        "scenes": scenes
    }
    
    return director_plan, prompts_forge


def main():
    episode_id = "JP_EP0003_japan_ai_ransom_economy"
    plan, prompts = generate_director_plan(episode_id)
    
    ep_dir = ROOT_DIR / "episodes" / episode_id
    if not ep_dir.exists():
        ep_dir = Path("/var/vf/episodes") / episode_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    
    plan_path = ep_dir / "director_plan.json"
    prompts_path = ep_dir / "prompts.json"
    
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
        
    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
        
    print(f"Reforged Director Plan successfully:")
    print(f"- Total Beats: {plan['total_beats']}")
    print(f"- Total Blocks: {plan['total_sequence_blocks']}")
    print(f"- Audio Duration: {plan['audio_runtime_seconds']}s")
    print(f"- Average Beat Duration: {plan['average_beat_duration_seconds']}s")
    print(f"- Output Plan: {plan_path} ({plan_path.stat().st_size:,} bytes)")
    print(f"- Output Prompts: {prompts_path} ({prompts_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
