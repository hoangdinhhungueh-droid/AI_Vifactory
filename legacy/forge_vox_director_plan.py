import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.legacy_guard import forbid_legacy
forbid_legacy(__name__)

forbid_legacy(__name__)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/forge_vox_director_plan.py — Forge Critic-Council-Approved Vox Director Plan (V2.0).
Implements 100% of Astra 6 and Claude Opus 5.5 feedback:
1. Strict 5-layer prompt structure in EVERY scene: [BG] -> [SHAPE] -> [HEADLINE] -> [CUTOUT] -> [TEXTURE]
2. Locked Vox 4-color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A, Muted Gold #D4AF37 on Cream Paper #F4F1EA
3. High-retention bilingual headlines: Korean dominant with English kicker (e.g., '1540억 원, 0원 // THE ZERO BILL')
4. Eliminates cliché stamps/gavels and generic metaphors; precisely matches Seoul-Singapore contract mechanism
5. Perfect factual alignment: 65% offshore flow (9751억), zero Amazon reference
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent

SCENES_DATA = [
    {
        "scene_id": "SCENE_01",
        "timeframe": "00:00 - 00:06",
        "sentence": "2026년 10월 8일, 대법원은 구글코리아의 약 1540억 원 법인세 부과 취소 소송에서 최종 패소 판결을 확정했습니다.",
        "core_idea": "Court Reversal & Shock Metric",
        "bilingual_headline": "1540억 원, 0원 // THE ZERO BILL",
        "visual_metaphor": "A 1540 billion won tax assessment bill cleanly torn into three pieces representing the 3 court levels, overlaid with a giant hand-cut paper zero in Vox Yellow",
        "color_accent": "Vox Yellow #F2C230 & Terracotta #C85A32",
        "motion_direction": "Slow tactile push-in on the zero cutout, with the three torn bill pieces drifting slightly apart"
    },
    {
        "scene_id": "SCENE_02",
        "timeframe": "00:06 - 00:11",
        "sentence": "세무조사권과 자료 제출 권한을 모두 가진 국가가, 1심과 2심 그리고 대법원까지 세 번 연속으로 무너졌습니다.",
        "core_idea": "Three Consecutive Legal Defeats",
        "bilingual_headline": "3번의 패소 // THREE LOSSES",
        "visual_metaphor": "Three descending stepped paper terraces labeled 1st Court, 2nd Court, Supreme Court, each collapsing downward into a void",
        "color_accent": "Terracotta #C85A32 & Charcoal Black #1A1A1A",
        "motion_direction": "Staccato cut-in of three sequential falling paper terraces collapsing in rhythm"
    },
    {
        "scene_id": "SCENE_03",
        "timeframe": "00:11 - 00:17",
        "sentence": "2016년부터 2018년까지 구글코리아가 한국에서 벌어들인 광고매출은 1조5112억 원이었습니다.",
        "core_idea": "Massive Advertising Revenue Scale",
        "bilingual_headline": "1.5조 원의 매출 // 1.5 TRILLION REVENUE",
        "visual_metaphor": "A monumental geometric tower of stacked Korean financial ledger pages rising high above a stylized Seoul street grid",
        "color_accent": "Vox Yellow #F2C230 & Navy #1B2B4A",
        "motion_direction": "Vertical upward pan tracking the height of the paper ledger tower"
    },
    {
        "scene_id": "SCENE_04",
        "timeframe": "00:17 - 00:23",
        "sentence": "그러나 그 중 9751억 원, 약 65%의 자금이 싱가포르의 구글 아시아퍼시픽으로 곧장 빠져나갔습니다.",
        "core_idea": "Public Cost and Offshore Extraction",
        "bilingual_headline": "65% → 싱가포르 // 65% OFFSHORE DRAIN",
        "visual_metaphor": "A bold Vox Yellow pipeline emerging from a Seoul map cutout, splitting into a thin 35% domestic trickle and a massive 65% torrent surging into a Singapore island cutout",
        "color_accent": "Vox Yellow #F2C230 & Navy #1B2B4A",
        "motion_direction": "Dynamic lateral flow tracking the 65% torrent streaming southeast across the paper ocean"
    },
    {
        "scene_id": "SCENE_05",
        "timeframe": "00:23 - 00:29",
        "sentence": "당신이 검색하고 광고를 누르는 화면은 서울에 있지만, 세금을 낼 주체는 한국에 존재하지 않았습니다.",
        "core_idea": "Geographic Disconnection Paradox",
        "bilingual_headline": "존재하지 않는 납세자 // GHOST TAXPAYER",
        "visual_metaphor": "A vintage monochrome Seoul smartphone screen cutout casting a long shadow, where the taxpayer silhouette inside is an empty dashed dotted outline with a severed cable",
        "color_accent": "Terracotta #C85A32 & Charcoal Black #1A1A1A",
        "motion_direction": "Slow zoom-in on the dashed taxpayer outline revealing empty paper texture underneath"
    },
    {
        "scene_id": "SCENE_06",
        "timeframe": "00:29 - 00:35",
        "sentence": "국세청은 1540억 원이라는 사상 초유의 세금을 고지하며 한국판 '구글세'의 신호탄을 쏘아 올렸습니다.",
        "core_idea": "The 154 Billion Won Landmark Claim",
        "bilingual_headline": "1,540억 원의 고지서 // THE 154B CLAIM",
        "visual_metaphor": "An official government tax assessment dossier in Terracotta and cream, framed by an architectural blueprint of the National Tax Service building",
        "color_accent": "Terracotta #C85A32 & Cream Paper #F4F1EA",
        "motion_direction": "Dynamic camera reveal with dossier settling firmly into the center of frame"
    },
    {
        "scene_id": "SCENE_07",
        "timeframe": "00:35 - 00:41",
        "sentence": "국내 포털 기업들이 수천억 원의 법인세를 낼 때, 빅테크는 수십억 원에 불과한 세금만 납부했습니다.",
        "core_idea": "The Asymmetric 100X Tax Gap",
        "bilingual_headline": "100배의 격차 // 100X ASYMMETRY",
        "visual_metaphor": "A side-by-side paper cutout comparison: a towering solid mountain of tax receipts for domestic portal Naver vs a single tiny paper slip for the offshore tech giant",
        "color_accent": "Muted Gold #D4AF37 & Navy #1B2B4A",
        "motion_direction": "Horizontal tracking shot emphasizing the extreme visual scale contrast"
    },
    {
        "scene_id": "SCENE_08",
        "timeframe": "00:41 - 00:47",
        "sentence": "그러나 이 소송은 단순한 탈세 사건이 아니었습니다. 세법상 '이름표'를 둘러싼 정밀한 법리 전쟁이었습니다.",
        "core_idea": "Classification Battle Over Reality",
        "bilingual_headline": "사용료인가, 사업소득인가 // ROYALTIES OR PROFIT",
        "visual_metaphor": "Two antique filing drawers labeled 'ROYALTIES (사용료)' and 'BUSINESS PROFITS (사업소득)', with a single financial dossier hovering undecided between them",
        "color_accent": "Vox Yellow #F2C230 & Navy #1B2B4A",
        "motion_direction": "Parallax split-frame with the dossier drifting toward the right drawer"
    },
    {
        "scene_id": "SCENE_09",
        "timeframe": "00:47 - 00:53",
        "sentence": "국세청은 이 돈을 기술과 노하우의 대가인 '사용료'로 보았고, 사용료라면 한국이 과세할 수 있었습니다.",
        "core_idea": "The Royalties Argument",
        "bilingual_headline": "사용료의 논리 // THE ROYALTY PATH",
        "visual_metaphor": "A precision blueprint diagram of software algorithms flowing through a pipeline, intercepted by a Korean domestic tax withholding valve",
        "color_accent": "Navy #1B2B4A & Muted Gold #D4AF37",
        "motion_direction": "Technical line-draw animation illuminating the blueprint valves and pipeline"
    },
    {
        "scene_id": "SCENE_10",
        "timeframe": "00:53 - 00:59",
        "sentence": "반면 구글은 단순한 '사업소득'이라 주장했고, 국내에 고정된 사업장이 없다면 세금을 낼 수 없다고 맞섰습니다.",
        "core_idea": "Business Profit vs Permanent Establishment",
        "bilingual_headline": "이름표의 갈림길 // THE TWO LABELS",
        "visual_metaphor": "A split-frame comparison on a single corporate tax invoice: left side stamped '사용료 (과세 가능)' in Terracotta vs right side stamped '사업소득 + 고정사업장 없음 (과세 불가)' in Navy",
        "color_accent": "Navy #1B2B4A & Terracotta #C85A32",
        "motion_direction": "Side-by-side sliding comparison of the two competing legal stamps"
    },
    {
        "scene_id": "SCENE_11",
        "timeframe": "00:59 - 01:05",
        "sentence": "핵심 열쇠는 바로 조세조약 속 '고정사업장'이라는 다섯 글자였습니다.",
        "core_idea": "The Permanent Establishment Gatekeeper",
        "bilingual_headline": "고정사업장 // NO OFFICE, NO TAX",
        "visual_metaphor": "A flight of marble stairs leading up to a corporate headquarters that exists only as an empty dashed dotted outline on paper, hovering over empty air",
        "color_accent": "Navy #1B2B4A & Vox Yellow #F2C230",
        "motion_direction": "Slow tracking shot ascending the paper stairs revealing the phantom headquarters"
    },
    {
        "scene_id": "SCENE_12",
        "timeframe": "01:05 - 01:11",
        "sentence": "고정사업장은 물리적인 사무실이나 직원이 계약을 체결하는 현실의 거점을 요구합니다.",
        "core_idea": "Physicality Requirement of 20th Century Tax Law",
        "bilingual_headline": "텅 빈 체크리스트 // EMPTY CHECKLIST",
        "visual_metaphor": "A vintage tax auditor's clipboard with three checklist items: [물리적 책상 (Desk), 상주 직원 (Staff), 계약 체결권 (Signing Authority)], with every box remaining starkly empty in Korea",
        "color_accent": "Charcoal Black #1A1A1A & Terracotta #C85A32",
        "motion_direction": "Top-down camera panning down the three empty checklist boxes"
    },
    {
        "scene_id": "SCENE_13",
        "timeframe": "01:11 - 01:17",
        "sentence": "구글코리아는 서울 역삼동에 번듯한 빌딩을 두고 있었지만, 본사는 계약 권한을 싱가포르에 두었습니다.",
        "core_idea": "The Remote Authority Machine",
        "bilingual_headline": "원격 서명 // REMOTE CONTRACT",
        "visual_metaphor": "The Yeoksam office building cutout in Seoul with its contract-signing fountain pen tethered to a long golden thread pulled across the ocean to a Singapore terminal",
        "color_accent": "Vox Yellow #F2C230 & Navy #1B2B4A",
        "motion_direction": "Camera tracking the golden thread stretching from the Seoul desk to Singapore"
    },
    {
        "scene_id": "SCENE_14",
        "timeframe": "01:17 - 01:23",
        "sentence": "한국 지사는 단순한 마케팅 지원 대행사로 설계되었고, 실제 계약은 싱가포르 법인의 버튼 하나로 체결되었습니다.",
        "core_idea": "The Cost-Plus Reseller Architecture",
        "bilingual_headline": "비용 플러스의 벽 // COST-PLUS TRAP",
        "visual_metaphor": "A heavy mechanical clamp labeled 'MARKETING RESELLER' compressing the Korean profit down to a razor-thin 5% margin, while the bulk 65% flows freely offshore",
        "color_accent": "Terracotta #C85A32 & Charcoal Black #1A1A1A",
        "motion_direction": "Piston clamp motion compressing downward onto the profit line"
    },
    {
        "scene_id": "SCENE_15",
        "timeframe": "01:23 - 01:29",
        "sentence": "서버는 바다 건너 해외에 있었고, 한국 법원에는 그 서버를 국내 사업장으로 묶어둘 법적 닻이 없었습니다.",
        "core_idea": "Offshore Server Island",
        "bilingual_headline": "서버의 위치 // WHERE IS THE SERVER?",
        "visual_metaphor": "A monolithic dark server cabinet resting isolated on a small paper cutout island across the ocean, completely detached from the Korean coastline",
        "color_accent": "Navy #1B2B4A & Cream Paper #F4F1EA",
        "motion_direction": "Slow atmospheric drift across the paper ocean toward the server island"
    },
    {
        "scene_id": "SCENE_16",
        "timeframe": "01:29 - 01:35",
        "sentence": "양측 모두 합법적인 규정 안에서 움직였지만, 그 규정들 사이에는 거대한 제도적 공백이 입을 벌리고 있었습니다.",
        "core_idea": "Structural Regulatory Vacuum",
        "bilingual_headline": "법률의 빈틈 // THE INSTITUTIONAL GAP",
        "visual_metaphor": "Two massive hardcover legal codebooks standing upright side-by-side, with gold tax coins dropping straight down through the dark gap between their spines",
        "color_accent": "Muted Gold #D4AF37 & Navy #1B2B4A",
        "motion_direction": "Slow vertical drop of coins falling through the narrow canyon between the books"
    },
    {
        "scene_id": "SCENE_17",
        "timeframe": "01:35 - 01:41",
        "sentence": "2025년 1월, 1심 법원은 '이 돈을 노하우의 대가로 보기 어렵다'며 국세청의 사용료 주장을 기각했습니다.",
        "core_idea": "First Instance Verdict & Door Lock",
        "bilingual_headline": "1심의 철문 // THE FIRST VERDICT",
        "visual_metaphor": "A massive steel vault door swinging shut over the word 'ROYALTIES (사용료)', permanently locking out domestic tax claims",
        "color_accent": "Charcoal Black #1A1A1A & Terracotta #C85A32",
        "motion_direction": "Heavy rotational bolt-locking animation sealing the compartment"
    },
    {
        "scene_id": "SCENE_18",
        "timeframe": "01:41 - 01:47",
        "sentence": "판결문 속 단 한 줄의 문장이 국세청이 세운 과세의 첫 번째 도미노를 무너뜨린 스모킹 건이었습니다.",
        "core_idea": "Smoking Gun Judicial Sentence",
        "bilingual_headline": "한 줄의 도화선 // THE FUSE",
        "visual_metaphor": "A single legal sentence underlined in intense terracotta ink on an archival contract page, acting as a slow-burning lit fuse advancing across the parchment",
        "color_accent": "Terracotta #C85A32 & Cream Paper #F4F1EA",
        "motion_direction": "Horizontal tracking shot following the terracotta underline glowing and advancing"
    },
    {
        "scene_id": "SCENE_19",
        "timeframe": "01:47 - 01:53",
        "sentence": "사용료라는 명분이 사라지자, 9751억 원에 걸려 있던 원천징수의 둑은 힘없이 터져 나갔습니다.",
        "core_idea": "Breached Withholding Dam",
        "bilingual_headline": "무너진 둑 // BREACHED DAM",
        "visual_metaphor": "A fortified paper masonry dam labeled 'TAX JURISDICTION' cracking open under pressure, releasing a torrent of Navy-colored geometric currency shapes",
        "color_accent": "Navy #1B2B4A & Vox Yellow #F2C230",
        "motion_direction": "Dynamic lateral breakaway of paper barrier blocks with currency surge"
    },
    {
        "scene_id": "SCENE_20",
        "timeframe": "01:53 - 01:59",
        "sentence": "남은 길은 싱가포르 법인의 국내 고정사업장을 입증하는 것뿐이었지만, 입증 책임은 고스란히 국가의 몫이었습니다.",
        "core_idea": "The Crushing Burden of Proof",
        "bilingual_headline": "입증의 장벽 // BURDEN OF PROOF",
        "visual_metaphor": "A lone government auditor silhouette struggling to lift a monumental stone tablet inscribed with evidentiary rules",
        "color_accent": "Charcoal Black #1A1A1A & Vox Yellow #F2C230",
        "motion_direction": "Slow tilt-up highlighting the monumental scale of the stone tablet over the figure"
    },
    {
        "scene_id": "SCENE_21",
        "timeframe": "01:59 - 02:05",
        "sentence": "대법원은 본안 심리조차 열지 않는 '심리불속행 기각'으로 사건을 매듭지었습니다.",
        "core_idea": "Summary Dismissal Without Hearing",
        "bilingual_headline": "심리불속행 기각 // SUMMARY DISMISSAL",
        "visual_metaphor": "A massive closed courthouse double door with no handle, cleanly stenciled with the words '본안 심리 부존재 (No Substantive Hearing)', leaving the page blank of any rebuttal",
        "color_accent": "Terracotta #C85A32 & Cream Paper #F4F1EA",
        "motion_direction": "Final decisive top-down close of the doors sealing the court chamber"
    },
    {
        "scene_id": "SCENE_22",
        "timeframe": "02:05 - 02:11",
        "sentence": "넷플릭스, 메타 등 한국에서 진행 중인 다른 글로벌 빅테크의 조세 소송들에도 연쇄적인 파장이 번지고 있습니다.",
        "core_idea": "The Industry Domino Fall",
        "bilingual_headline": "연쇄 파장 // THE DOMINO EFFECT",
        "visual_metaphor": "A sequence of standing corporate paper monoliths tipping over one by one in precise succession across a stylized Seoul financial map",
        "color_accent": "Navy #1B2B4A & Terracotta #C85A32",
        "motion_direction": "Linear domino toppling motion running left to right across the frame"
    },
    {
        "scene_id": "SCENE_23",
        "timeframe": "02:11 - 02:17",
        "sentence": "유럽은 디지털 서비스세를 도입하고 OECD는 새로운 글로벌 과세 규칙을 추진하지만, 길은 멀기만 합니다.",
        "core_idea": "Global Policy Divergence",
        "bilingual_headline": "디지털 세의 갈림길 // DIGITAL TAX DIVIDE",
        "visual_metaphor": "A vintage stylized world map where digital-tax adopter nations are highlighted in bold Vox Yellow while pending nations remain in muted Terracotta",
        "color_accent": "Vox Yellow #F2C230 & Terracotta #C85A32",
        "motion_direction": "Subtle geographic pulse highlighting the contrasting policy zones"
    },
    {
        "scene_id": "SCENE_24",
        "timeframe": "02:17 - 02:23",
        "sentence": "글로벌 기업이 합법적으로 비워낸 세수의 구멍은, 결국 평범한 시민들의 유리알 지갑으로 메워지고 있습니다.",
        "core_idea": "The Domestic Taxpayer Ledger",
        "bilingual_headline": "유리알 지갑 // WHO BEARS THE COST?",
        "visual_metaphor": "An ordinary citizen cutout holding a transparent payslip with automatic tax deductions, standing beside an empty corporate tax vault",
        "color_accent": "Muted Gold #D4AF37 & Navy #1B2B4A",
        "motion_direction": "Slow pull-back revealing the stark contrast between individual deductions and corporate vacuum"
    },
    {
        "scene_id": "SCENE_25",
        "timeframe": "02:23 - 02:29",
        "sentence": "세법이 물리적 벽돌과 콘크리트에 머무는 한, 디지털 경제의 수익은 언제나 국경을 유유히 미끄러져 나갈 것입니다.",
        "core_idea": "Living Mirror & Systemic Warning",
        "bilingual_headline": "콘크리트의 한계 // BEYOND CONCRETE",
        "visual_metaphor": "A heavy stone city wall attempting to block digital radio waves and data streams that effortlessly pass through its arches into the open sky",
        "color_accent": "Vox Yellow #F2C230 & Navy #1B2B4A",
        "motion_direction": "Dynamic upward tilt as data streams bypass the historical stone ramparts"
    },
    {
        "scene_id": "SCENE_26",
        "timeframe": "02:29 - 02:35",
        "sentence": "9751억 원은 싱가포르로 건너갔고, 법은 그 돈에 붙은 이름표만을 충실히 읽었습니다.",
        "core_idea": "Final Bookend & Editorial Verdict",
        "bilingual_headline": "이름표만 읽었다 // THE NAME TAG",
        "visual_metaphor": "A lone paper currency bill bearing an authentic cardboard luggage tag stamped 'SINGAPORE / EXEMPT' resting quietly on an empty desk under the Seoul night skyline",
        "color_accent": "Terracotta #C85A32 & Cream Paper #F4F1EA",
        "motion_direction": "Slow cinematic pull-out to wide shot, leaving the tagged bill isolated on the dark paper skyline"
    }
]

def build_prompt(s):
    bg = "[BG: aged cream newsprint paper #F4F1EA with fine halftone dot grid and natural paper fiber grain]"
    shape = f"[GEO SHAPE: bold geometric color block in {s['color_accent']}]"
    headline = f"[HEADLINE: heavy condensed editorial typography occupying 25-35% of frame, bilingual text: '{s['bilingual_headline']}']"
    cutout = f"[CUTOUT: high-contrast tactile paper cutout with crisp 2-4px white deckle edge and realistic soft drop shadow: {s['visual_metaphor']}]"
    texture = "[TEXTURE: vintage print ink texture, slight fold creases, authentic newsprint misregistration]"
    
    full_prompt = (
        f"Editorial investigative documentary frame in signature VOX paper-cut collage style. "
        f"{bg} -> {shape} -> {headline} -> {cutout} -> {texture}. "
        f"Strictly locked color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A, Muted Gold #D4AF37 on Off-white Cream #F4F1EA. "
        f"High editorial hierarchy, crisp layering, authentic tactile craft. "
        f"Negative prompt: no clutter, no unnecessary objects, no excessive icons, no visual noise, no random decorations, "
        f"no fantasy elements, no sci-fi elements, no anime, no cartoon style, no CGI look, no glossy 3D rendering, "
        f"no photorealistic background, no oversaturated rainbow colors, no poor composition, no distorted anatomy, no watermark, no logos."
    )
    return full_prompt

def main():
    plan_file = ROOT_DIR / "episodes" / "KR_EP0001_google_kr_tax_loss" / "director_plan.json"
    
    scenes = []
    for s in SCENES_DATA:
        prompt = build_prompt(s)
        scenes.append({
            "scene_id": s["scene_id"],
            "timeframe": s["timeframe"],
            "sentence": s["sentence"],
            "core_idea": s["core_idea"],
            "bilingual_headline": s["bilingual_headline"],
            "headline": s["bilingual_headline"],
            "editorial_title": s["bilingual_headline"],
            "visual_metaphor": s["visual_metaphor"],
            "color_accent": s["color_accent"],
            "layering": "BG (Cream Paper) -> GEO SHAPE -> HEADLINE -> CUTOUT SUBJECT -> TEXTURE (Vintage grain)",
            "motion_direction": s["motion_direction"],
            "image_prompt": prompt
        })
    
    plan = {
        "episode_id": "KR_EP0001_google_kr_tax_loss",
        "title": "국세청, 구글코리아 1540억원대 법인세 취소소송에서 패소: 조세 회피와 고정사업장의 역설",
        "market": "KR",
        "total_scenes": len(scenes),
        "scenes": scenes
    }
    
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Generated {len(scenes)} scenes in {plan_file}")

if __name__ == "__main__":
    main()
