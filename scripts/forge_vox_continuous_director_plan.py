#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/forge_vox_continuous_director_plan.py — True Vox Object-Assembly & Continuous Flow Engine.

Triệt tiêu hoàn toàn lối mòn "Slide trình chiếu rời rạc".
Mỗi phân cảnh là một mắt xích trong chuỗi lắp ghép vật thể liên tục (Continuous Assembly):
- Canvas nền nhất quán (Aged Newsprint Paper #F4F1EA).
- Hero Cutout Objects độc lập (tờ trát thuế, con thuyền, cây bút, smartphone, hòn đảo).
- Motion Track & Assembly: Cách các vật thể trượt vào, dán đè, khóa chặt (locked) và liên kết bằng ray chuyển động.
- Visual Continuity Link: Vật thể câu trước là bệ phóng cho chuyển động của câu sau.
- Graphic Typography: Chữ đồ họa đóng dấu theo nhịp, không nhồi vào hình vẽ nền.
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent

CONTINUOUS_SCENES = [
    # =========================================================================
    # SEQUENCE BLOCK 1: TỜ TRÁT THUẾ 154 TỶ & DÒNG CHẢY VƯỢT BIỂN (00:00 - 00:23)
    # =========================================================================
    {
        "scene_id": "SCENE_01",
        "sequence_block": "BLOCK_1_TAX_INVOICE_AND_OFFSHORE_FLOW",
        "timeframe": "00:00 - 00:06",
        "sentence": "2026년 10월 8일, 대법원은 구글코리아의 약 1540억 원 법인세 부과 취소 소송에서 최종 패소 판결을 확정했습니다.",
        "canvas_workspace": "Aged Cream Newsprint Desk #F4F1EA with subtle print halftone grid",
        "hero_cutout_object": "An official 154 Billion Won corporate tax demand document (1540억 원 과세고지서) on tactile aged paper",
        "interacting_objects": [
            "A giant hand-cut paper ZERO overlay in Vox Yellow #F2C230",
            "Supreme Court crimson dismissal seal stamped over the total"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Tax notice document slides smoothly into center stage from top edge",
            "assembly_step": "2.0-4.0s: Crimson seal stamps firmly onto the document; giant paper ZERO cutout drops over the 154B won figure with paper drop shadow",
            "spatial_anchor": "Center-left of canvas, permanently locked as the base anchor for Scene 02",
            "camera_rule": "Completely static camera, no 3D pan/zoom"
        },
        "graphic_typography": {
            "korean_headline": "1540억 원, 0원",
            "english_tag": "THE ZERO BILL",
            "color_bar": "Terracotta #C85A32",
            "position": "Top-left, occupying 25% negative space"
        },
        "visual_continuity_link_to_next": "The tax notice document remains on desk; in Scene 02, paper scissors will cut this exact document into 3 descending pieces."
    },
    {
        "scene_id": "SCENE_02",
        "sequence_block": "BLOCK_1_TAX_INVOICE_AND_OFFSHORE_FLOW",
        "timeframe": "00:06 - 00:11",
        "sentence": "세무조사권과 자료 제출 권한을 모두 가진 국가가, 1심과 2심 그리고 대법원까지 세 번 연속으로 무너졌습니다.",
        "canvas_workspace": "Same Aged Cream Newsprint Desk #F4F1EA, continuing directly from Scene 01",
        "hero_cutout_object": "The exact same tax demand document from Scene 01, now cut into 3 descending paper tiers",
        "interacting_objects": [
            "Paper shears cutting through the document seam",
            "Three descending stepped labels: [1심 서울행정법원] -> [2심 서울고등법원] -> [3심 대법원]"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Cutout scissors snip across the document with a tactile paper snap",
            "assembly_step": "2.0-4.5s: The 3 document sections drop sequentially down a staggered paper staircase, landing flat and locking into place",
            "spatial_anchor": "Center stage, descending toward bottom-right",
            "camera_rule": "Static camera, motion created entirely by the falling paper tiers"
        },
        "graphic_typography": {
            "korean_headline": "3번의 패소",
            "english_tag": "THREE LOSSES",
            "color_bar": "Charcoal Black #1A1A1A",
            "position": "Top-right, balancing the descending tiers"
        },
        "visual_continuity_link_to_next": "The bottom-most paper tier becomes the foundation pad from which the 1.5 Trillion Won revenue tower rises in Scene 03."
    },
    {
        "scene_id": "SCENE_03",
        "sequence_block": "BLOCK_1_TAX_INVOICE_AND_OFFSHORE_FLOW",
        "timeframe": "00:11 - 00:17",
        "sentence": "2016년부터 2018년까지 구글코리아가 한국에서 벌어들인 광고매출은 1조5112억 원이었습니다.",
        "canvas_workspace": "Aged Cream Newsprint Desk #F4F1EA with a stylized Seoul street grid printed in muted ink",
        "hero_cutout_object": "A towering vertical skyscraper built from stacked paper ledger pages and Korean Won currency bundles",
        "interacting_objects": [
            "A bold Vox Yellow #F2C230 circle backdrop highlighting the summit",
            "A measurement caliper measuring the massive vertical height labeled '1조 5,112억 원'"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.5s: Paper ledger pages stack upward in rapid tactile succession like a rising skyscraper",
            "assembly_step": "2.5-5.0s: Caliper slides in from the right, clamping the full height; Vox Yellow circle pops behind the top",
            "spatial_anchor": "Left side of frame, vertical monolith anchored to the Seoul street grid",
            "camera_rule": "Static frame, the vertical construction guides the viewer's eye upward"
        },
        "graphic_typography": {
            "korean_headline": "1.5조 원의 매출",
            "english_tag": "1.5 TRILLION REVENUE",
            "color_bar": "Vox Yellow #F2C230",
            "position": "Top-left above the skyscraper"
        },
        "visual_continuity_link_to_next": "The top 65% slice of this ledger tower will peel away in Scene 04 and embark on an offshore motion track."
    },
    {
        "scene_id": "SCENE_04",
        "sequence_block": "BLOCK_1_TAX_INVOICE_AND_OFFSHORE_FLOW",
        "timeframe": "00:17 - 00:23",
        "sentence": "그러나 그 중 9751억 원, 약 65%의 자금이 싱가포르의 구글 아시아퍼시픽으로 곧장 빠져나갔습니다.",
        "canvas_workspace": "Expanded East Asia newsprint nautical chart spanning from Seoul (left) to Singapore (right)",
        "hero_cutout_object": "A paper-cut cargo boat carrying the 65% slice (9,751억 원) of currency bundles",
        "interacting_objects": [
            "A bold dotted Vox Yellow #F2C230 motion track curving across the ocean",
            "A stylized cutout island of Singapore on the right edge labeled 'Google Asia Pacific'"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Singapore island cutout drops onto the bottom-right of the map",
            "assembly_step": "1.5-4.5s: The paper cargo boat glides along the dotted motion track from Seoul across to Singapore, locking into the island dock",
            "spatial_anchor": "Diagonal motion path from top-left (Seoul) to bottom-right (Singapore)",
            "camera_rule": "Static frame, viewer tracks the boat along the yellow dashed line"
        },
        "graphic_typography": {
            "korean_headline": "65% → 싱가포르",
            "english_tag": "65% OFFSHORE DRAIN",
            "color_bar": "Navy #1B2B4A",
            "position": "Top-center along the flight path"
        },
        "visual_continuity_link_to_next": "A golden cable trailing behind the boat snaps back to Seoul, where in Scene 05 it connects to a user's mobile screen."
    },

    # =========================================================================
    # SEQUENCE BLOCK 2: BÓNG MA NỘP THUẾ & 2 CHIẾC NGĂN KÉO PHÂN LOẠI (00:23 - 00:47)
    # =========================================================================
    {
        "scene_id": "SCENE_05",
        "sequence_block": "BLOCK_2_GHOST_TAXPAYER_AND_TWO_DRAWERS",
        "timeframe": "00:23 - 00:29",
        "sentence": "당신이 검색하고 광고를 누르는 화면은 서울에 있지만, 세금을 낼 주체는 한국에 존재하지 않았습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with split lighting: Seoul day (left) vs Offshore shadow (right)",
        "hero_cutout_object": "A hand holding a cutout modern smartphone displaying an active Korean search screen",
        "interacting_objects": [
            "A trailing severed power cord extending from the phone into empty space",
            "A human taxpayer silhouette rendered entirely as an empty dashed dotted outline"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Hand and smartphone slide up from bottom-left; severed cable flops down",
            "assembly_step": "2.0-4.5s: Dashed taxpayer outline fades in on the right, completely hollow inside, revealing background newsprint",
            "spatial_anchor": "Phone on left, hollow outline on right",
            "camera_rule": "Static frame, visual tension created by the severed gap"
        },
        "graphic_typography": {
            "korean_headline": "존재하지 않는 납세자",
            "english_tag": "GHOST TAXPAYER",
            "color_bar": "Terracotta #C85A32",
            "position": "Top-right above the dashed silhouette"
        },
        "visual_continuity_link_to_next": "The tax audit authority enters from the left with an official assessment notice to confront the empty space."
    },
    {
        "scene_id": "SCENE_06",
        "sequence_block": "BLOCK_2_GHOST_TAXPAYER_AND_TWO_DRAWERS",
        "timeframe": "00:29 - 00:35",
        "sentence": "국세청은 1540억 원이라는 사상 초유의 세금을 고지하며 한국판 '구글세'의 신호탄을 쏘아 올렸습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with architectural engraving lines of the Seoul National Tax Service building",
        "hero_cutout_object": "A monumental formal tax penalty notice stamped with the official government seal",
        "interacting_objects": [
            "A bold Terracotta #C85A32 paper signal banner labeled '한국판 구글세'",
            "A stylized cutout gavel resting firmly against the base"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Tax notice pins firmly into the center of the building facade",
            "assembly_step": "2.0-4.5s: Signal banner unfurls diagonally upward from the seal like a launch flare",
            "spatial_anchor": "Center-aligned architectural balance",
            "camera_rule": "Static frame, clean editorial poster balance"
        },
        "graphic_typography": {
            "korean_headline": "1,540억 원의 고지서",
            "english_tag": "THE 154B CLAIM",
            "color_bar": "Terracotta #C85A32",
            "position": "Bottom-center under the document"
        },
        "visual_continuity_link_to_next": "The tax document becomes a weight placed on one side of a comparative justice balance in Scene 07."
    },
    {
        "scene_id": "SCENE_07",
        "sequence_block": "BLOCK_2_GHOST_TAXPAYER_AND_TWO_DRAWERS",
        "timeframe": "00:35 - 00:41",
        "sentence": "국내 포털 기업들이 수천억 원의 법인세를 낼 때, 빅테크는 수십억 원에 불과한 세금만 납부했습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with clean geometric horizontal baseline",
        "hero_cutout_object": "An antique balance scale in dark navy paper craft",
        "interacting_objects": [
            "Left pan: Heavy solid mountain of tax receipts (Naver / Kakao) labeled '수천억 원'",
            "Right pan: A single feather-light paper receipt slip (Big Tech) labeled '수십억 원'"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Balance scale appears in balance",
            "assembly_step": "1.5-4.0s: Domestic tax mountain drops onto left pan with a heavy thud, tilting the scale down 25 degrees; the single paper slip drifts onto the elevated right pan",
            "spatial_anchor": "Center scale, left side heavily depressed",
            "camera_rule": "Static camera, scale motion tells the entire unfairness story"
        },
        "graphic_typography": {
            "korean_headline": "세금의 비대칭",
            "english_tag": "TAX ASYMMETRY",
            "color_bar": "Muted Gold #D4AF37",
            "position": "Top-center above the scale beam"
        },
        "visual_continuity_link_to_next": "The right-hand paper slip transforms into a disputed file that slides toward two legal filing drawers in Scene 08."
    },
    {
        "scene_id": "SCENE_08",
        "sequence_block": "BLOCK_2_GHOST_TAXPAYER_AND_TWO_DRAWERS",
        "timeframe": "00:41 - 00:47",
        "sentence": "그러나 이 소송은 단순한 탈세 사건이 아니었습니다. 세법상 '이름표'를 둘러싼 정밀한 법리 전쟁이었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with a vintage dark wood filing cabinet facade",
        "hero_cutout_object": "A disputed financial dossier hovering on a central motion track",
        "interacting_objects": [
            "Left Drawer: Labeled in Terracotta '사용료 // ROYALTIES (과세 가능)'",
            "Right Drawer: Labeled in Navy '사업소득 // BUSINESS PROFIT (과세 불가)'"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Both drawers slide partially open toward the viewer",
            "assembly_step": "2.0-4.5s: The disputed dossier hovers in the center, tilting toward the left drawer, then reversing toward the right drawer",
            "spatial_anchor": "Split composition: 50% Left drawer / 50% Right drawer",
            "camera_rule": "Static frame, the dossier's hesitation visualizes the legal dilemma"
        },
        "graphic_typography": {
            "korean_headline": "이름표의 전쟁",
            "english_tag": "THE TAXONOMY WAR",
            "color_bar": "Vox Yellow #F2C230",
            "position": "Top-center dividing the two drawers"
        },
        "visual_continuity_link_to_next": "We zoom into the Left Drawer in Scene 09 to examine the tax authority's logic of 'Royalty'."
    },

    # =========================================================================
    # SEQUENCE BLOCK 3: BẢN VẼ SỞ HỮU TRÍ TUỆ & CĂN PHÒNG BÓNG MA (00:47 - 01:17)
    # =========================================================================
    {
        "scene_id": "SCENE_09",
        "sequence_block": "BLOCK_3_ROYALTY_PATH_AND_PERMANENT_ESTABLISHMENT",
        "timeframe": "00:47 - 00:53",
        "sentence": "국세청은 이 돈을 기술과 노하우의 대가인 '사용료'로 보았고, 사용료라면 한국이 과세할 수 있었습니다.",
        "canvas_workspace": "Aged Cream Newsprint with technical blueprint linework in Navy ink",
        "hero_cutout_object": "A blueprint pipeline diagram showing proprietary algorithm streams flowing through software valves",
        "interacting_objects": [
            "A Korean domestic withholding tax valve clamp labeled '원천징수'",
            "A paper seal labeled '노하우 (Know-how) 대가'"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Blueprint pipeline draws on screen from left to right",
            "assembly_step": "2.0-4.5s: Withholding valve clamp drops over the pipeline, turning the valve to intercept the royalty flow",
            "spatial_anchor": "Horizontal technical pipeline spanning frame",
            "camera_rule": "Static frame, technical clarity"
        },
        "graphic_typography": {
            "korean_headline": "사용료의 논리",
            "english_tag": "THE ROYALTY PATH",
            "color_bar": "Navy #1B2B4A",
            "position": "Top-left on blueprint margin"
        },
        "visual_continuity_link_to_next": "Google's defense enters by stamping an alternative legal status over the pipeline in Scene 10."
    },
    {
        "scene_id": "SCENE_10",
        "sequence_block": "BLOCK_3_ROYALTY_PATH_AND_PERMANENT_ESTABLISHMENT",
        "timeframe": "00:53 - 00:59",
        "sentence": "반면 구글은 단순한 '사업소득'이라 주장했고, 국내에 고정된 사업장이 없다면 세금을 낼 수 없다고 맞섰습니다.",
        "canvas_workspace": "Same Aged Cream Newsprint #F4F1EA, split vertically into two legal arguments",
        "hero_cutout_object": "A single corporate tax contract page pinned to the center",
        "interacting_objects": [
            "Left Stamp: Terracotta ink '사용료 (국내 과세 O)'",
            "Right Stamp: Navy ink '사업소득 + 고정사업장 없음 (국내 과세 X)'"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Left Terracotta stamp stamps down on contract; right Navy stamp stamps down directly opposite",
            "assembly_step": "2.0-4.5s: A heavy red X paper cutout drops over the Left Stamp; a paper lock closes over the Right Stamp",
            "spatial_anchor": "Split balance: Left vs Right across central contract",
            "camera_rule": "Static camera, dramatic ideological collision"
        },
        "graphic_typography": {
            "korean_headline": "사업소득 vs 사용료",
            "english_tag": "BUSINESS PROFIT OR ROYALTY",
            "color_bar": "Navy #1B2B4A",
            "position": "Top-center"
        },
        "visual_continuity_link_to_next": "The key term '고정사업장' (Permanent Establishment) pulls out from the right stamp to become the main architectural focus in Scene 11."
    },
    {
        "scene_id": "SCENE_11",
        "sequence_block": "BLOCK_3_ROYALTY_PATH_AND_PERMANENT_ESTABLISHMENT",
        "timeframe": "00:59 - 01:05",
        "sentence": "핵심 열쇠는 바로 조세조약 속 '고정사업장'이라는 다섯 글자였습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with Korea-Singapore tax treaty text watermark",
        "hero_cutout_object": "A grand marble staircase leading upward to an empty dashed dotted outline of a corporate building",
        "interacting_objects": [
            "A large brass paper key cutout labeled 'PE (Permanent Establishment)'",
            "The words '고정사업장' stenciled in bold Navy typography across the dashed entrance"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Marble staircase slides in from bottom-center",
            "assembly_step": "2.0-4.5s: Brass key inserts into an invisible keyhole at the top of the stairs, turning in empty space",
            "spatial_anchor": "Perspective looking up the stairs into hollow space",
            "camera_rule": "Static frame, the phantom building outline emphasizes the physical void"
        },
        "graphic_typography": {
            "korean_headline": "고정사업장",
            "english_tag": "PERMANENT ESTABLISHMENT",
            "color_bar": "Vox Yellow #F2C230",
            "position": "Top-left above the phantom stairs"
        },
        "visual_continuity_link_to_next": "An auditor's clipboard drops in Scene 12 to test the physical criteria of this phantom office."
    },
    {
        "scene_id": "SCENE_12",
        "sequence_block": "BLOCK_3_ROYALTY_PATH_AND_PERMANENT_ESTABLISHMENT",
        "timeframe": "01:05 - 01:11",
        "sentence": "고정사업장은 물리적인 사무실이나 직원이 계약을 체결하는 현실의 거점을 요구합니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with vintage clipboard wood grain texture",
        "hero_cutout_object": "An official tax auditor's inspection checklist clipboard",
        "interacting_objects": [
            "Three checkbox rows: [1. 고정된 물리적 장소 (Desk)] -> [2. 상주 직원 (Staff)] -> [3. 계약 체결 대리인 (Signer)]",
            "Three red cutout 'EMPTY / 부존재' stamps"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Clipboard drops into frame flat on the desk",
            "assembly_step": "1.5-4.5s: A tax auditor's pen moves down rows 1, 2, 3; instead of checkmarks, red '부존재' stamps hammer down on all 3 boxes",
            "spatial_anchor": "Center-stage clipboard",
            "camera_rule": "Static camera, rhythmic three-beat stamp animation"
        },
        "graphic_typography": {
            "korean_headline": "텅 빈 체크리스트",
            "english_tag": "EMPTY CHECKLIST",
            "color_bar": "Charcoal Black #1A1A1A",
            "position": "Top-right beside clipboard"
        },
        "visual_continuity_link_to_next": "The missing signing authority in box 3 is revealed in Scene 13: the pen is physically in Singapore."
    },
    {
        "scene_id": "SCENE_13",
        "sequence_block": "BLOCK_3_ROYALTY_PATH_AND_PERMANENT_ESTABLISHMENT",
        "timeframe": "01:11 - 01:17",
        "sentence": "구글코리아는 서울 역삼동에 번듯한 빌딩을 두고 있었지만, 본사는 계약 권한을 싱가포르에 두었습니다.",
        "canvas_workspace": "Wide nautical chart newsprint spanning Seoul (left) to Singapore (right)",
        "hero_cutout_object": "The Seoul Yeoksam Gangnam Finance Center building cutout on the left",
        "interacting_objects": [
            "A corporate executive desk in Yeoksam with an empty chair",
            "A golden signing fountain pen tied to a long string pulled across the ocean to a Singapore server terminal"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Yeoksam building stands tall on left; Singapore terminal appears on right",
            "assembly_step": "2.0-4.5s: The golden string tethers the desk pen and pulls it across the ocean to Singapore, hovering above the terminal",
            "spatial_anchor": "Left-to-right tether tension across frame",
            "camera_rule": "Static frame, the taut horizontal string carries the narrative weight"
        },
        "graphic_typography": {
            "korean_headline": "원격 서명",
            "english_tag": "REMOTE AUTHORITY",
            "color_bar": "Vox Yellow #F2C230",
            "position": "Top-center along the string path"
        },
        "visual_continuity_link_to_next": "Because the pen is in Singapore, the Seoul office is treated as a low-margin reseller clamped down in Scene 14."
    },

    # =========================================================================
    # SEQUENCE BLOCK 4: CHIẾC KẸP CHI PHÍ & CÁNH CỬA KHÓA CHẶT (01:17 - 01:53)
    # =========================================================================
    {
        "scene_id": "SCENE_14",
        "sequence_block": "BLOCK_4_COST_PLUS_CLAMP_AND_LEGAL_VOID",
        "timeframe": "01:17 - 01:23",
        "sentence": "한국 지사는 단순한 마케팅 지원 대행사로 설계되었고, 실제 계약은 싱가포르 법인의 버튼 하나로 체결되었습니다.",
        "canvas_workspace": "Aged Cream Newsprint with financial accounting grid in muted charcoal",
        "hero_cutout_object": "A cutout hand in Singapore pressing an 'APPROVE CONTRACT' digital terminal button, while a hollow dashed-outline Seoul office looks on from across the sea",
        "interacting_objects": [
            "A green approval checkmark seal stamping onto the contract in Singapore",
            "A thin wire connecting the terminal directly to the offshore server"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Singapore terminal button enters on right; hollow Seoul office sits on left",
            "assembly_step": "2.0-4.5s: Singapore finger presses the button with a click; green checkmark stamps down while Seoul office remains entirely passive",
            "spatial_anchor": "Split frame: Seoul passive office (left) vs Singapore active button (right)",
            "camera_rule": "Static frame, the one-click contract action contrasts the two geographies"
        },
        "graphic_typography": {
            "korean_headline": "버튼 하나의 계약",
            "english_tag": "ONE-CLICK CONTRACT",
            "color_bar": "Terracotta #C85A32",
            "position": "Top-left above Seoul office"
        },
        "visual_continuity_link_to_next": "The revenue approved by this button flows into the physical server rack isolated across the sea in Scene 15."
    },
    {
        "scene_id": "SCENE_15",
        "sequence_block": "BLOCK_4_COST_PLUS_CLAMP_AND_LEGAL_VOID",
        "timeframe": "01:23 - 01:29",
        "sentence": "서버는 바다 건너 해외에 있었고, 한국 법원에는 그 서버를 국내 사업장으로 묶어둘 법적 닻이 없었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with paper sea waves in Navy tint",
        "hero_cutout_object": "A dark monolithic computer server cabinet cutout resting isolated on a tiny paper island",
        "interacting_objects": [
            "A heavy ship's iron anchor dropped from Korea labeled '국내 세법'",
            "The anchor rope snapping halfway because it cannot reach the offshore island"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Server island rests in top-right ocean; Korean shore on bottom-left",
            "assembly_step": "2.0-4.5s: Iron anchor drops from Korean shore toward the server; rope snaps mid-ocean with a paper tear, leaving the server untethered",
            "spatial_anchor": "Diagonal sea separation from shore to island",
            "camera_rule": "Static camera, snap animation illustrates jurisdictional boundary"
        },
        "graphic_typography": {
            "korean_headline": "서버의 위치",
            "english_tag": "WHERE IS THE SERVER?",
            "color_bar": "Navy #1B2B4A",
            "position": "Top-left in open sky"
        },
        "visual_continuity_link_to_next": "Between the Korean shore and the offshore server lies the systemic gap visualized in Scene 16."
    },
    {
        "scene_id": "SCENE_16",
        "sequence_block": "BLOCK_4_COST_PLUS_CLAMP_AND_LEGAL_VOID",
        "timeframe": "01:29 - 01:35",
        "sentence": "양측 모두 합법적인 규정 안에서 움직였지만, 그 규정들 사이에는 거대한 제도적 공백이 입을 벌리고 있었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with stark negative space",
        "hero_cutout_object": "Two monumental legal codebooks standing upright side-by-side: [조세조약 (Tax Treaty)] on left, [국세기본법 (Domestic Tax Law)] on right",
        "interacting_objects": [
            "A dark canyon gap of empty space between the two book spines",
            "Gold tax coins dropping straight down through the canyon into the void"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Both massive books slam down side-by-side",
            "assembly_step": "1.5-4.5s: Gold coins stream down from the top, slipping cleanly between the two book spines into the bottom void, untouched by either law",
            "spatial_anchor": "Symmetric architectural composition with central void",
            "camera_rule": "Static frame, the falling coins through the gap are the sole focus"
        },
        "graphic_typography": {
            "korean_headline": "법률의 빈틈",
            "english_tag": "THE INSTITUTIONAL GAP",
            "color_bar": "Muted Gold #D4AF37",
            "position": "Top-center above the canyon"
        },
        "visual_continuity_link_to_next": "The court in Scene 17 rules on this gap by officially slamming shut the royalty door."
    },
    {
        "scene_id": "SCENE_17",
        "sequence_block": "BLOCK_4_COST_PLUS_CLAMP_AND_LEGAL_VOID",
        "timeframe": "01:35 - 01:41",
        "sentence": "2025년 1월, 1심 법원은 '이 돈을 노하우의 대가로 보기 어렵다'며 국세청의 사용료 주장을 기각했습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with court verdict archival stamp background",
        "hero_cutout_object": "A massive steel vault door stenciled with 'ROYALTIES (사용료)'",
        "interacting_objects": [
            "A heavy mechanical vault wheel turning with a click",
            "A red wax seal stamped 'DISMISSED (기각)' sealing the vault shut"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Vault door stands slightly ajar",
            "assembly_step": "2.0-4.5s: Vault wheel spins and slams shut with a heavy mechanical latch; DISMISSED seal clamps over the seam",
            "spatial_anchor": "Center-stage vault door",
            "camera_rule": "Static frame, finality of the door locking"
        },
        "graphic_typography": {
            "korean_headline": "1심의 철문",
            "english_tag": "THE FIRST VERDICT",
            "color_bar": "Charcoal Black #1A1A1A",
            "position": "Top-left above vault"
        },
        "visual_continuity_link_to_next": "The single underlined sentence in this verdict acts as the smoking gun fuse in Scene 18."
    },
    {
        "scene_id": "SCENE_18",
        "sequence_block": "BLOCK_4_COST_PLUS_CLAMP_AND_LEGAL_VOID",
        "timeframe": "01:41 - 01:47",
        "sentence": "판결문 속 단 한 줄의 문장이 국세청이 세운 과세의 첫 번째 도미노를 무너뜨린 스모킹 건이었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA, close-up of Seoul Administrative Court verdict page",
        "hero_cutout_object": "The printed sentence: '노하우의 대가로 보기 어렵다 (Cannot be deemed royalties)'",
        "interacting_objects": [
            "An intense Terracotta #C85A32 ink underline advancing horizontally across the page like a burning lit fuse",
            "The very first standing tax domino at the right edge wobbling as the fuse reaches its base"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Printed verdict text sits crisp on the newsprint",
            "assembly_step": "2.0-4.5s: Terracotta underline draws rapidly from left to right like a glowing fuse; as it touches the first domino, the domino tips 15 degrees",
            "spatial_anchor": "Horizontal reading line from left to right",
            "camera_rule": "Static frame, the advancing line drives the tension"
        },
        "graphic_typography": {
            "korean_headline": "첫 번째 도미노",
            "english_tag": "THE FIRST DOMINO",
            "color_bar": "Terracotta #C85A32",
            "position": "Top-right above the tipping domino"
        },
        "visual_continuity_link_to_next": "As the first domino falls, the entire withholding tax dam cracks open in Scene 19."
    },

    # =========================================================================
    # SEQUENCE BLOCK 5: ĐẬP THUẾ VỠ & THẺ HÀNH LÝ KẾT BÀI (01:47 - 02:35)
    # =========================================================================
    {
        "scene_id": "SCENE_19",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "01:47 - 01:53",
        "sentence": "사용료라는 명분이 사라지자, 9751억 원에 걸려 있던 원천징수의 둑은 힘없이 터져 나갔습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with architectural masonry texture",
        "hero_cutout_object": "A fortified paper masonry dam labeled 'WITHHOLDING TAX (원천징수)'",
        "interacting_objects": [
            "Cracks spreading through the paper dam masonry in Terracotta lines",
            "A massive flood of Navy #1B2B4A geometric currency shapes bursting through the fissure"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Paper dam stands intact",
            "assembly_step": "1.5-4.5s: Seams split open with a jagged paper tear; blocks give way as currency shapes surge through to the right",
            "spatial_anchor": "Dam wall spanning from top-left to bottom-center",
            "camera_rule": "Static camera, breakaway paper physics convey systemic collapse"
        },
        "graphic_typography": {
            "korean_headline": "무너진 둑",
            "english_tag": "BREACHED DAM",
            "color_bar": "Navy #1B2B4A",
            "position": "Top-left above the rupture"
        },
        "visual_continuity_link_to_next": "Amidst the flood, a lone tax inspector is left holding an impossibly heavy stone tablet in Scene 20."
    },
    {
        "scene_id": "SCENE_20",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "01:53 - 01:59",
        "sentence": "남은 길은 싱가포르 법인의 국내 고정사업장을 입증하는 것뿐이었지만, 입증 책임은 고스란히 국가의 몫이었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with steep incline perspective",
        "hero_cutout_object": "A monumental stone tablet inscribed with '입증 책임 (Burden of Proof)'",
        "interacting_objects": [
            "A lone vintage government auditor cutout in a classic suit straining to push the giant stone uphill (Sisyphean motif)",
            "A steep 45-degree geometric paper slope"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Steep slope and stone tablet set the daunting scale",
            "assembly_step": "2.0-4.5s: Auditor figure pushes into position; the stone tilts slightly back, proving too heavy to move",
            "spatial_anchor": "Diagonal struggle across frame from bottom-left to top-right",
            "camera_rule": "Static camera, monumental scale contrast"
        },
        "graphic_typography": {
            "korean_headline": "입증의 장벽",
            "english_tag": "BURDEN OF PROOF",
            "color_bar": "Charcoal Black #1A1A1A",
            "position": "Top-left above the slope"
        },
        "visual_continuity_link_to_next": "The struggle ends in Scene 21 as the Supreme Court shuts its doors without hearing."
    },
    {
        "scene_id": "SCENE_21",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "01:59 - 02:05",
        "sentence": "대법원은 본안 심리조차 열지 않는 '심리불속행 기각'으로 사건을 매듭지었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with grand Supreme Court marble portal lines",
        "hero_cutout_object": "A massive neoclassical courthouse double door with no handles",
        "interacting_objects": [
            "A clean stencil on the double doors: '본안 심리 부존재 (No Substantive Hearing)'",
            "A crimson Supreme Court wax seal stamped over the door seam"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Double doors stand wide open showing darkness inside",
            "assembly_step": "1.5-4.0s: Both door panels slam shut simultaneously; wax seal clamps across the central seam with zero bounce",
            "spatial_anchor": "Center-aligned majestic neoclassical symmetry",
            "camera_rule": "Static camera, total finality"
        },
        "graphic_typography": {
            "korean_headline": "심리불속행 기각",
            "english_tag": "SUMMARY DISMISSAL",
            "color_bar": "Terracotta #C85A32",
            "position": "Bottom-center under the doors"
        },
        "visual_continuity_link_to_next": "The shockwave from this door closing knocks down the remaining tech dominoes in Scene 22."
    },
    {
        "scene_id": "SCENE_22",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "02:05 - 02:11",
        "sentence": "넷플릭스, 메타 등 한국에서 진행 중인 다른 글로벌 빅테크의 조세 소송들에도 연쇄적인 파장이 번지고 있습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with Seoul Teheran Valley financial district grid",
        "hero_cutout_object": "A row of 4 corporate paper monoliths: [Google (Fallen)] -> [Netflix] -> [Meta] -> [Cloud Tech]",
        "interacting_objects": [
            "A horizontal motion track connecting all 4 bases",
            "Domino kinetic wave tipping Netflix and Meta monoliths in sequence"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-1.5s: Row of 4 monoliths stand tall across frame",
            "assembly_step": "1.5-4.5s: The fallen Google monolith strikes Netflix; Netflix strikes Meta; the chain reaction moves left to right with crisp paper snaps",
            "spatial_anchor": "Horizontal domino line spanning frame",
            "camera_rule": "Static camera, sequential kinetic wave"
        },
        "graphic_typography": {
            "korean_headline": "연쇄 파장",
            "english_tag": "THE DOMINO EFFECT",
            "color_bar": "Navy #1B2B4A",
            "position": "Top-center above the falling chain"
        },
        "visual_continuity_link_to_next": "From corporate dominoes, the scope expands to global international tax policy in Scene 23."
    },
    {
        "scene_id": "SCENE_23",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "02:11 - 02:17",
        "sentence": "유럽은 디지털 서비스세를 도입하고 OECD는 새로운 글로벌 과세 규칙을 추진하지만, 길은 멀기만 합니다.",
        "canvas_workspace": "Vintage Mercator world map printed on aged cream newsprint with latitude/longitude grid",
        "hero_cutout_object": "A stylized world map highlighting international tax fragmentation",
        "interacting_objects": [
            "DST Adopters (France, UK, Italy) highlighted in bold Vox Yellow #F2C230 paper overlays with 'DST' tags",
            "Pending nations and Korea in muted Terracotta #C85A32 and Navy #1B2B4A tints",
            "An OECD negotiation compass slowly spinning in the ocean"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: World map lies flat on desk",
            "assembly_step": "2.0-4.5s: European DST nation cutouts pop up one by one in Vox Yellow; OECD compass spins slowly in the Atlantic without pointing to a north",
            "spatial_anchor": "Global map layout with European focal point",
            "camera_rule": "Static camera, geographic data infographic clarity"
        },
        "graphic_typography": {
            "korean_headline": "디지털 세의 갈림길",
            "english_tag": "DIGITAL TAX DIVIDE",
            "color_bar": "Vox Yellow #F2C230",
            "position": "Top-left on map border"
        },
        "visual_continuity_link_to_next": "While global talks drag on, the tax burden falls on the domestic individual citizen in Scene 24."
    },
    {
        "scene_id": "SCENE_24",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "02:17 - 02:23",
        "sentence": "글로벌 기업이 합법적으로 비워낸 세수의 구멍은, 결국 평범한 시민들의 유리알 지갑으로 메워지고 있습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with domestic monthly budget ledger grid",
        "hero_cutout_object": "An ordinary salaried worker cutout holding a transparent glass wallet (유리알 지갑)",
        "interacting_objects": [
            "Coins being automatically drawn out of the glass wallet through a salary deduction tube",
            "The corporate tax vault in the background standing empty with doors open"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Worker silhouette and glass wallet enter on left",
            "assembly_step": "2.0-4.5s: Clear coins leave the glass wallet along a dotted tube, dropping into the municipal budget box, while the corporate vault remains barren",
            "spatial_anchor": "Worker on left, empty corporate vault on right",
            "camera_rule": "Static frame, poignant contrast between transparent compliance and offshore void"
        },
        "graphic_typography": {
            "korean_headline": "유리알 지갑",
            "english_tag": "WHO BEARS THE COST?",
            "color_bar": "Muted Gold #D4AF37",
            "position": "Top-left above worker"
        },
        "visual_continuity_link_to_next": "Scene 25 confronts the systemic clash between 20th century concrete law and 21st century digital flow."
    },
    {
        "scene_id": "SCENE_25",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "02:23 - 02:29",
        "sentence": "세법이 물리적 벽돌과 콘크리트에 머무는 한, 디지털 경제의 수익은 언제나 국경을 유유히 미끄러져 나갈 것입니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with stone rampart texture",
        "hero_cutout_object": "A heavy historical stone border wall labeled '20TH CENTURY TAX CODE (벽돌과 콘크리트)'",
        "interacting_objects": [
            "Digital data waves and glowing streams (representing search ads and cloud revenue) floating effortlessly over and through the stone wall arches",
            "A customs stamp lying obsolete at the wall base"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Heavy stone wall stands solid across the lower third",
            "assembly_step": "2.0-4.5s: Golden data stream curves gracefully from bottom-left, passing cleanly through the stone archway into the open sky unimpeded",
            "spatial_anchor": "Physical wall on ground, digital stream in sky",
            "camera_rule": "Static frame, the effortless bypass of physical barriers is the core metaphor"
        },
        "graphic_typography": {
            "korean_headline": "콘크리트의 한계",
            "english_tag": "BEYOND CONCRETE",
            "color_bar": "Vox Yellow #F2C230",
            "position": "Top-left in open sky"
        },
        "visual_continuity_link_to_next": "The final Scene 26 resolves the entire 5-Act journey by closing the loop on the single luggage tag."
    },
    {
        "scene_id": "SCENE_26",
        "sequence_block": "BLOCK_5_BREACHED_DAM_AND_SYSTEMIC_LEGACY",
        "timeframe": "02:29 - 02:35",
        "sentence": "9751억 원은 싱가포르로 건너갔고, 법은 그 돈에 붙은 이름표만을 충실히 읽었습니다.",
        "canvas_workspace": "Aged Cream Newsprint #F4F1EA with minimal Seoul midnight skyline silhouette along the bottom",
        "hero_cutout_object": "A single crisp Korean Won currency note lying flat on the desk",
        "interacting_objects": [
            "A tactile cardboard luggage tag attached to the note with natural twine string",
            "A stamped label on the tag: 'SINGAPORE // TAX EXEMPT' in crisp Navy ink"
        ],
        "motion_track_and_assembly": {
            "entry_action": "0.0-2.0s: Currency note and attached luggage tag rest peacefully under soft paper shadow",
            "assembly_step": "2.0-4.5s: A judicial inspection glass moves over the luggage tag, reading ONLY the printed label 'SINGAPORE // EXEMPT', completely ignoring the currency underneath",
            "spatial_anchor": "Center stage minimal composition, echoing Scene 01's opening simplicity",
            "camera_rule": "Static camera, definitive closing bookend"
        },
        "graphic_typography": {
            "korean_headline": "이름표만 읽었다",
            "english_tag": "THE NAME TAG",
            "color_bar": "Terracotta #C85A32",
            "position": "Top-center above the tagged note"
        },
        "visual_continuity_link_to_next": "FINAL SCENE. Closes the narrative loop on Scene 08 ('이름표의 전쟁') and Scene 01."
    }
]

def build_vox_object_prompt(scene):
    """
    Tạo AI Image Generation Prompt theo chuẩn Instruction Prompt 2 (media_1791881130800.md):
    - Đầy đủ 5 tầng lớp cắt dán (Layering): Background -> Geo Shape -> Headline -> Cutout Subject -> Texture.
    - Negative Prompt chuẩn 100% của Vox documentary.
    - Để lại negative space cho typography đồ họa hậu kỳ.
    """
    s_id = scene["scene_id"]
    canvas = scene["canvas_workspace"]
    hero = scene["hero_cutout_object"]
    interacting = ", ".join(scene["interacting_objects"])
    color_bar = scene["graphic_typography"]["color_bar"]
    korean_hl = scene["graphic_typography"]["korean_headline"]
    english_tag = scene["graphic_typography"]["english_tag"]
    
    layer_bg = f"Layer 1: {canvas}"
    layer_geo = f"Layer 2: bold flat geometric color block in {color_bar}"
    layer_headline = f"Layer 3: negative space reserved for large bold editorial typography '{korean_hl} // {english_tag}', occupying 25-35% of frame"
    layer_cutout = f"Layer 4: high-contrast tactile paper cutout subject with crisp 2-4px white deckle edge and realistic soft drop shadow: {hero}. Interacting elements: {interacting}"
    layer_texture = "Layer 5: vintage print ink texture, natural paper grain, subtle fold creases, authentic newspaper print misregistration"
    
    prompt = (
        f"Editorial investigative documentary frame in signature VOX paper-cut collage style. "
        f"[{layer_bg}] -> [{layer_geo}] -> [{layer_headline}] -> [{layer_cutout}] -> [{layer_texture}]. "
        f"Strictly locked color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A, Muted Gold #D4AF37 on Off-white Cream #F4F1EA. "
        f"Clear object-assembly composition, strong editorial hierarchy, tactile paper craft. "
        f"Negative prompt: no clutter, no unnecessary objects, no excessive icons, no visual noise, no random decorations, "
        f"no fantasy elements, no sci-fi elements, no anime, no cartoon style, no CGI look, no glossy 3D rendering, "
        f"no photorealistic background, no oversaturated rainbow colors, no poor composition, no distorted anatomy, no watermark, no logos, "
        f"maintain a clean premium VOX-style editorial collage with layered paper textures and documentary-quality composition."
    )
    return prompt

def main():
    plan_file = ROOT_DIR / "episodes" / "KR_EP0001_google_kr_tax_loss" / "director_plan.json"
    
    processed_scenes = []
    for s in CONTINUOUS_SCENES:
        img_prompt = build_vox_object_prompt(s)
        metaphor_summary = f"{s['hero_cutout_object']} with {', '.join(s['interacting_objects'])}"
        processed_scenes.append({
            "scene_id": s["scene_id"],
            "sequence_block": s["sequence_block"],
            "timeframe": s["timeframe"],
            "sentence": s["sentence"],
            "core_idea": s["graphic_typography"]["english_tag"],
            "headline": f"{s['graphic_typography']['korean_headline']} // {s['graphic_typography']['english_tag']}",
            "bilingual_headline": f"{s['graphic_typography']['korean_headline']} // {s['graphic_typography']['english_tag']}",
            "editorial_title": f"{s['graphic_typography']['korean_headline']} // {s['graphic_typography']['english_tag']}",
            "visual_metaphor": metaphor_summary,
            "canvas_workspace": s["canvas_workspace"],
            "hero_cutout_object": s["hero_cutout_object"],
            "interacting_objects": s["interacting_objects"],
            "motion_track_and_assembly": s["motion_track_and_assembly"],
            "graphic_typography": s["graphic_typography"],
            "visual_continuity_link_to_next": s["visual_continuity_link_to_next"],
            "color_accent": s["graphic_typography"]["color_bar"],
            "image_prompt": img_prompt
        })
    
    final_plan = {
        "episode_id": "KR_EP0001_google_kr_tax_loss",
        "title": "국세청, 구글코리아 1540억원대 법인세 취소소송에서 패소: 조세 회피와 고정사업장의 역설",
        "market": "KR",
        "format": "VOX_CONTINUOUS_OBJECT_ASSEMBLY_COLLAGE",
        "total_scenes": len(processed_scenes),
        "total_sequence_blocks": 5,
        "scenes": processed_scenes
    }
    
    plan_file.write_text(json.dumps(final_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Generated {len(processed_scenes)} continuous Vox scenes in {plan_file}")

if __name__ == "__main__":
    main()
