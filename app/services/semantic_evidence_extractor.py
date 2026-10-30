#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/semantic_evidence_extractor.py — Claim-to-Evidence Binding Engine (Rule 128 & Rule 141).

Replaces legacy hardcoded dictionaries (e.g. KOREAN_ACT_I_SCENE_PROFILES) with dynamic,
cross-market semantic classification across 5 Forensic Archetypes:
1. LegalSanctionArchetype: Regulatory decisions, vermilion sanction stamps, penalty orders (H1 Impact).
2. CorporateEntityArchetype: Developer dossiers, business registrations, corporate foldouts (H2 Clamp / H7 Unfold).
3. ParadoxClaimArchetype: False promotional ads stamped 'REVOKED/FRAUDULENT' (H3 Tear / H1 Reject).
4. QuantitativeMetricArchetype: Financial balance sheets, vernier calipers, metric discrepancy pins (H2 Caliper).
5. InvestigativeMediaArchetype: Teletype ticker, news broadcast headlines, optical magnifying glass (H5 Optical / H6 Ink).

Conforms to:
- Rule 118: Zero-Mock Data & Factual Grounding.
- Rule 128: Generic Contract Architecture across all markets (KR, JA, EN, VN).
- Rule 132: Pure Transmission Engine.
- Rule 140: Tactile Kinetic Coupling (H1 -> H7) on vintage paper (#F4F1EA).
- Rule 141: Claim-to-Evidence Binding (Hero Object MUST be tangible legal/documentary evidence).
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from core.market_resolver import resolve_canonical_market

logger = logging.getLogger(__name__)


class ForensicArchetype(str, Enum):
    LEGAL_SANCTION = "legal_sanction"
    CORPORATE_ENTITY = "corporate_entity"
    PARADOX_CLAIM = "paradox_claim"
    QUANTITATIVE_METRIC = "quantitative_metric"
    INVESTIGATIVE_MEDIA = "investigative_media"


@dataclass(frozen=True)
class ExtractedEvidence:
    """Forensic evidence bound to a specific sentence claim."""
    archetype: ForensicArchetype
    dominant_family: str  # e.g. "H1_IMPACT", "H2_CONSTRAINT", etc.
    hero_anchor_prop: str
    interacting_tool_prop: str
    tactile_action_verb: str
    physical_reaction: str
    tactile_residue: str
    layout_type: str
    camera_directive: str
    sound_foley: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["archetype"] = self.archetype.value
        return d


# Multilingual Semantic Keyword Taxonomies
_KEYWORD_TAXONOMY: Dict[ForensicArchetype, Dict[str, List[str]]] = {
    ForensicArchetype.LEGAL_SANCTION: {
        "KR": ["공정위", "제재", "시정명령", "과징금", "처분", "의결", "법원", "기소", "불법", "벌금", "수사"],
        "JA": ["公正取引", "制裁", "是正命令", "課徴金", "処分", "議決", "裁判所", "起訴", "違法", "罰金"],
        "EN": ["sanction", "regulator", "penalty", "ruling", "ftc", "sec", "doj", "order", "court", "illegal", "prosecutor", "violation"],
        "VN": ["xử phạt", "đình chỉ", "thanh tra", "vi phạm", "án phạt", "tòa án", "cơ quan điều tra", "sai phạm", "pháp luật"],
    },
    ForensicArchetype.CORPORATE_ENTITY: {
        "KR": ["시행사", "드림하우징", "시공사", "법인", "기업", "지분", "합작", "계약서", "임대", "주식회사"],
        "JA": ["施工会社", "デベロッパー", "法人", "企業", "持分", "契約書", "賃貸", "株式会社", "合弁"],
        "EN": ["developer", "firm", "corporation", "subsidiary", "contract", "lease", "entity", "syndicate", "shareholder", "license"],
        "VN": ["chủ đầu tư", "doanh nghiệp", "công ty", "tập đoàn", "hợp đồng", "dự án", "thuê nhà", "pháp nhân"],
    },
    ForensicArchetype.PARADOX_CLAIM: {
        "KR": ["마감임박", "광고", "외쳤지만", "승인도 없는데", "허위", "기만", "무엇이 마감", "과장", "선착순", "홍보"],
        "JA": ["締め切り", "広告", "宣伝", "承認なし", "虚偽", "誇大", "先着順", "勧誘"],
        "EN": ["hurry", "closing soon", "advertisement", "claimed", "unapproved", "false", "misleading", "deceptive", "paradox", "pitch"],
        "VN": ["cháy hàng", "sắp hết hạn", "quảng cáo", "gian dối", "chưa cấp phép", "lừa dối", "thổi phồng", "rao bán"],
    },
    ForensicArchetype.QUANTITATIVE_METRIC: {
        "KR": ["%", "원", "억", "조", "모집률", "투자금", "묶었습니다", "손실", "비율", "수익률", "30%", "자금"],
        "JA": ["%", "円", "億", "兆", "募集率", "投資金", "損失", "比率", "利回り", "資金"],
        "EN": ["%", "$", "billion", "million", "rate", "loss", "deposit", "ratio", "percent", "capital", "shares"],
        "VN": ["%", "đồng", "tỷ", "triệu", "tỷ lệ", "tiền gửi", "thua lỗ", "lãi suất", "vốn", "tiền cọc"],
    },
    ForensicArchetype.INVESTIGATIVE_MEDIA: {
        "KR": ["보도", "언론", "경기일보", "연합뉴스", "mbc", "kbs", "sbs", "기사", "폭로", "단독", "심층", "고발"],
        "JA": ["報道", "ニュース", "新聞", "メディア", "暴露", "特報", "独自", "告発"],
        "EN": ["report", "news", "investigation", "broadsheet", "press", "wire", "exposé", "headline", "journal", "leak"],
        "VN": ["báo chí", "truyền thông", "tin tức", "phóng sự", "điều tra", "vạch trần", "báo đài", "tiêu điểm"],
    },
}

# Metric Regex Pattern for quantitative detection
_METRIC_REGEX = re.compile(r"(\d+(\.\d+)?\s*(%|percent|billion|million|\$|₩|€|£|원|억|조|tỷ|triệu))", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Dynamic Forensic Variant Catalogues (CL3 Kim Chỉ Nam Paper Diorama Standard)
# Derived from config/prompts/cl3_vox_engine/image-prompts.md & video-prompts.md.
# Eliminates hardcoded tools (e.g. vernier calipers) by rotating across rich
# tangible props, connective actions, and camera movements.
# ---------------------------------------------------------------------------

_ARCHETYPE_VARIANTS: Dict[ForensicArchetype, List[ExtractedEvidence]] = {
    ForensicArchetype.QUANTITATIVE_METRIC: [
        # Variant 0: Stat Hero Plate & Ticking Counter
        ExtractedEvidence(
            archetype=ForensicArchetype.QUANTITATIVE_METRIC,
            dominant_family="H2_CONSTRAINT",
            hero_anchor_prop="bold crimson stat counter card and mechanical ticker gauge on aged fibrous paper",
            interacting_tool_prop="mechanical ticker counter wheels and embossed stat number plate",
            tactile_action_verb="drops in close to the lens, counter ticking up from base figure with mechanical overshoot beside",
            physical_reaction="mechanical counter wheels spin and lock firmly on the verified figure, cardstock settling with tactile paper pop",
            tactile_residue="embossed crimson stat counter plate locked firmly in place with cast shadow",
            layout_type="center_stage",
            camera_directive="Top-down push-in through the gap beside the stat number, racking focus to the hero card",
            sound_foley="ticker_counter_overshoot_snap",
        ),
        # Variant 1: Financial Route Loop & Coin Tokens
        ExtractedEvidence(
            archetype=ForensicArchetype.QUANTITATIVE_METRIC,
            dominant_family="H7_DISPLACE",
            hero_anchor_prop="audited financial ledger statement and quantitative balance sheet table on fibrous ledger paper",
            interacting_tool_prop="thick red directional route arrow and metallic coin tokens",
            tactile_action_verb="draws card-to-card into a closed loop as coin tokens race along the path, whipping past the lens with motion blur past",
            physical_reaction="coin chips land with tactile clatter along the financial route, red arrow locking the circulation circuit",
            tactile_residue="closed-loop red ink route with scattered metallic coin chips casting tactile shadows",
            layout_type="split_horizontal_feed",
            camera_directive="Top-down orbit a quarter turn, focus racking along the path",
            sound_foley="coin_chips_sliding_and_arrow_swish",
        ),
        # Variant 2: Precision Caliper (one of multiple options, not hardcoded on every metric)
        ExtractedEvidence(
            archetype=ForensicArchetype.QUANTITATIVE_METRIC,
            dominant_family="H2_CONSTRAINT",
            hero_anchor_prop="financial ledger balance column and audited valuation schedule on fibrous ledger paper",
            interacting_tool_prop="machined brass vernier caliper with engraved millimeter gradations",
            tactile_action_verb="slides horizontally into the metric column, tightening its precision jaws firmly around the flagged figure on",
            physical_reaction="caliper tips pinch the margin of the financial metric, vernier scale settling instantly with zero drift",
            tactile_residue="twin pinpoint caliper score dents bracketing the verified quantitative metric figure",
            layout_type="split_horizontal_feed",
            camera_directive="Top-down macro perspective focused on the calibrated vernier jaw measurement",
            sound_foley="caliper_vernier_metal_click_slide",
        ),
        # Variant 3: Tiered Staggered Ledger Cards & Red Underline Swipe
        ExtractedEvidence(
            archetype=ForensicArchetype.QUANTITATIVE_METRIC,
            dominant_family="H6_MARK",
            hero_anchor_prop="three tiered archival ledger cards stacked at staggered depths with bold red underline swipe",
            interacting_tool_prop="staggered index cards and hot red underline marker",
            tactile_action_verb="snap in at three distinct depths forming a tiered financial stack over",
            physical_reaction="a hot red underline swipe sweeps beneath the critical balance figure, card layers settling with micro paper flutter",
            tactile_residue="bold crimson ink underline bar and stepped paper card layers casting tiered drop shadows",
            layout_type="center_right",
            camera_directive="Dives from above through the layered paper aperture, focus racking card to card",
            sound_foley="paper_flutter_card_snap",
        ),
    ],
    ForensicArchetype.INVESTIGATIVE_MEDIA: [
        # Variant 0: Red Evidence Thread & Brass Pins (THREAD PULL)
        ExtractedEvidence(
            archetype=ForensicArchetype.INVESTIGATIVE_MEDIA,
            dominant_family="H4_TETHER",
            hero_anchor_prop="archival investigative newspaper broadsheet clipping with bold banner headlines and editorial newsprint texture",
            interacting_tool_prop="red evidence yarn pinned taut between polished brass pushpins",
            tactile_action_verb="snaps taut with mechanical tension between headline exhibits, lifting dust off the paper across",
            physical_reaction="evidence thread vibrates and settles tautly, tethering disparate investigative news clippings across physical space",
            tactile_residue="taut geometric red thread network anchored by brass pushpins casting fine line shadows",
            layout_type="center_stage",
            camera_directive="Whips decisively left to right past the near cards, focus racking front to back along the thread",
            sound_foley="pushpin_wooden_tap_thread_snap",
        ),
        # Variant 1: Optical Magnifying Loupe
        ExtractedEvidence(
            archetype=ForensicArchetype.INVESTIGATIVE_MEDIA,
            dominant_family="H5_OPTICAL",
            hero_anchor_prop="archival investigative disclosure broadsheet with high-density editorial teletype columns",
            interacting_tool_prop="heavy brass-rimmed optical magnifying loupe with convex glass lens and knurled handle",
            tactile_action_verb="glides smoothly across the investigative broadsheet, locking in sharp focus directly over the disclosure headline of",
            physical_reaction="headline text beneath the lens magnifies 1.35x with barrel edge distortion, illuminating fine-print investigative evidence",
            tactile_residue="circular cast optical shadow ring framing the highlighted investigative revelation",
            layout_type="center_left",
            camera_directive="Top-down orthographic overview on continuous cream mat (#F4F1EA) under warm 3200K tungsten lighting",
            sound_foley="heavy_glass_lens_slide_on_paper",
        ),
        # Variant 2: Fluorescent Neon Highlighter & Streaming Ticker Tape
        ExtractedEvidence(
            archetype=ForensicArchetype.INVESTIGATIVE_MEDIA,
            dominant_family="H6_MARK",
            hero_anchor_prop="teletype news wire clipping and streaming diagonal ticker tape strips on fibrous newsprint",
            interacting_tool_prop="fluorescent neon amber highlighter rule and streaming ticker tape",
            tactile_action_verb="sweeps briskly across the investigative column, laying down a vibrant translucent stroke over",
            physical_reaction="paper fibers absorb the neon ink, text blooming with vibrant glow against the aged newsprint",
            tactile_residue="bold fluorescent highlighter bar with soft ink feathering along fibrous cardstock edges",
            layout_type="top_right_diagonal",
            camera_directive="Macro slides along the document surface, focus racking alongside the moving highlighter stroke",
            sound_foley="marker_felt_tip_friction_swipe",
        ),
        # Variant 3: Archival Dossier Tabs & Seal Slam (STAMP)
        ExtractedEvidence(
            archetype=ForensicArchetype.INVESTIGATIVE_MEDIA,
            dominant_family="H1_IMPACT",
            hero_anchor_prop="investigative dossier folder with labeled index tabs and deckle clipping exhibits",
            interacting_tool_prop="turned-wood docket seal stamp and labeled folder tabs",
            tactile_action_verb="slams down at foreground depth with an impact dust puff onto",
            physical_reaction="paper fibers visibly indent under the percussion, registering an official investigation stamp",
            tactile_residue="indelible circular crimson seal impression with subtle ink bleed into paper grain",
            layout_type="vertical",
            camera_directive="Cranes upward over the stacked dossier, keeping the hero element anchored",
            sound_foley="heavy_wooden_stamp_thud_paper_rebound",
        ),
    ],
    ForensicArchetype.CORPORATE_ENTITY: [
        # Variant 0: Industrial Steel Spring Clip & Corporate Dossier
        ExtractedEvidence(
            archetype=ForensicArchetype.CORPORATE_ENTITY,
            dominant_family="H2_CONSTRAINT",
            hero_anchor_prop="multi-panel corporate foldout dossier and commercial entity registration on 250gsm fibrous cardstock",
            interacting_tool_prop="industrial blackened steel spring clip with corporate index retention tab",
            tactile_action_verb="enters from the top-right margin and snaps firmly over the top spine of",
            physical_reaction="the steel spring clamp bites into cardstock edges, binding disparate corporate entities into a single unified forensic exhibit",
            tactile_residue="dual crimped score indentations and a permanently clamped steel binding clip holding the developer stack",
            layout_type="center_right",
            camera_directive="Pulls back to reveal the expanding diorama across multiple depths",
            sound_foley="metallic_binder_clip_spring_snap",
        ),
        # Variant 1: Logo Plates & Parallax Triangle Formation
        ExtractedEvidence(
            archetype=ForensicArchetype.CORPORATE_ENTITY,
            dominant_family="H7_DISPLACE",
            hero_anchor_prop="three archival document cards carrying attached flat company logo plates",
            interacting_tool_prop="attached flat company logo plates and cardstock dividers",
            tactile_action_verb="snap in at three different depths forming a triangle around",
            physical_reaction="corporate logo cards lock into crisp spatial parallax with sharp white keylines and offset ink strokes",
            tactile_residue="triangular layout of corporate cards casting tiered drop shadows",
            layout_type="center_stage",
            camera_directive="Flies between physical paper layers, the nearest whipping past with motion blur",
            sound_foley="paper_cards_snapping_into_slot",
        ),
        # Variant 2: Accordion Hierarchy Unfold
        ExtractedEvidence(
            archetype=ForensicArchetype.CORPORATE_ENTITY,
            dominant_family="H7_DISPLACE",
            hero_anchor_prop="accordion-folded corporate organization chart on fibrous parchment cardstock",
            interacting_tool_prop="accordion fold creases and corporate hierarchy label tags",
            tactile_action_verb="fans out across the desk surface under friction, unfolding layers of",
            physical_reaction="creases unfold revealing institutional hierarchy tiers with crisp paper pops",
            tactile_residue="crisp accordion paper fold lines resting in deep perspective",
            layout_type="split_horizontal_feed",
            camera_directive="Orbits a quarter turn around the foldout stack, racking focus front to back",
            sound_foley="paper_accordion_unfold_rustle",
        ),
    ],
    ForensicArchetype.PARADOX_CLAIM: [
        # Variant 0: Editorial Shears & Paper Tear (TEAR)
        ExtractedEvidence(
            archetype=ForensicArchetype.PARADOX_CLAIM,
            dominant_family="H3_SEVER",
            hero_anchor_prop="glossy marketing promotional flyer with exaggerated urgency claims, laid over unpermitted underlying lease agreements",
            interacting_tool_prop="machined steel editorial shears",
            tactile_action_verb="slices decisively in a crisp mechanical cut across",
            physical_reaction="the glossy top layer curls open and separates with paper edge curl, exposing the unpermitted underlying reality beneath",
            tactile_residue="clean deckle cut furrow exposing the raw fibers of the suppressed contract document beneath",
            layout_type="top_right_diagonal",
            camera_directive="Pushes in through the torn incision, focus racking from cut edges to the exposed layer",
            sound_foley="shears_paper_shearing_rip",
        ),
        # Variant 1: Heavy REJECTED Strike Stamp & ALERT WASH
        ExtractedEvidence(
            archetype=ForensicArchetype.PARADOX_CLAIM,
            dominant_family="H1_IMPACT",
            hero_anchor_prop="disputed promotional advertisement clipping on aged newsprint with contradictory fine print",
            interacting_tool_prop="heavy crimson REJECTED strike stamp and alert wash tone",
            tactile_action_verb="slams diagonally across the contradictory claim, triggering an ALERT WASH on",
            physical_reaction="entire frame floods to hot accent tone (#D62E1F) on the decisive strike, indelible red strike mark registering",
            tactile_residue="heavy crimson diagonal ink strike-through bar with distressed print edges",
            layout_type="center_stage",
            camera_directive="Dives from above, landing hard on the strike impact",
            sound_foley="heavy_stamp_slam_with_sub_thud",
        ),
        # Variant 2: Cross-Referenced Evidence Pinning
        ExtractedEvidence(
            archetype=ForensicArchetype.PARADOX_CLAIM,
            dominant_family="H4_TETHER",
            hero_anchor_prop="two juxtaposed contradictory statement cards pinned side-by-side with deckle edges",
            interacting_tool_prop="brass pushpins and criss-crossing red evidence yarn",
            tactile_action_verb="snaps taut linking conflicting statements with taut thread across",
            physical_reaction="red yarn vibrates under tension, pulling contradictory documents toward each other in sharp relief",
            tactile_residue="taut red tension lines bridging the paradox documents with brass pin anchors",
            layout_type="split_horizontal_feed",
            camera_directive="Whips decisively left to right across the tension lines, focus racking between cards",
            sound_foley="pushpin_tap_and_string_tension",
        ),
    ],
    ForensicArchetype.LEGAL_SANCTION: [
        # Variant 0: Official Regulatory Docket Seal Stamp
        ExtractedEvidence(
            archetype=ForensicArchetype.LEGAL_SANCTION,
            dominant_family="H1_IMPACT",
            hero_anchor_prop="official regulatory sanction docket and enforcement decree clipping with hand-torn deckle borders on aged cream newsprint (#F4F1EA)",
            interacting_tool_prop="heavy turned-wood vermilion docket seal stamp carved with mirrored official sanction seal glyphs",
            tactile_action_verb="drops briskly from top-center frame, striking down with a firm mechanical thud onto",
            physical_reaction="paper fibers visibly indent under the percussion as vermilion oily ink registers a bold official regulatory seal mark",
            tactile_residue="indelible circular vermilion official sanction seal impression with subtle ink bleed into paper thớ",
            layout_type="vertical",
            camera_directive="Top-down orthographic perspective over aged paper desk (#F4F1EA), subtle 1-frame camera shudder on impact",
            sound_foley="heavy_wooden_stamp_thud_paper_rebound",
        ),
        # Variant 1: Formal Judicial Ruling Scroll & Red Ribbon
        ExtractedEvidence(
            archetype=ForensicArchetype.LEGAL_SANCTION,
            dominant_family="H7_DISPLACE",
            hero_anchor_prop="formal judicial ruling decree with embossed official seal and red ribbon margin",
            interacting_tool_prop="weighted judicial ruling scroll and crimson ribbon seal",
            tactile_action_verb="unrolls diagonally with mechanical snap across the desk over",
            physical_reaction="parchment flattens with weighted ribbon ends settling firmly, revealing binding legal judgment",
            tactile_residue="unrolled judicial decree scroll anchored by weighted ribbon seal casting soft drop shadows",
            layout_type="top_right_diagonal",
            camera_directive="Macro slides along the scroll margin, focus racking to the legal decree text",
            sound_foley="scroll_unroll_paper_snap",
        ),
        # Variant 2: Enforcement Clasp & Padlock
        ExtractedEvidence(
            archetype=ForensicArchetype.LEGAL_SANCTION,
            dominant_family="H2_CONSTRAINT",
            hero_anchor_prop="frozen commercial account register and asset seizure order on fibrous cardstock",
            interacting_tool_prop="heavy brass padlock clasp and enforcement boundary tape",
            tactile_action_verb="clamps down across the frozen asset register, securing the margins of",
            physical_reaction="padlock shackle clicks shut, locking the document bundle with zero drift",
            tactile_residue="heavy brass padlock and boundary tape locking the frozen asset docket",
            layout_type="center_left",
            camera_directive="Orbits a quarter turn over the locked docket, racking focus front to back",
            sound_foley="metallic_padlock_click_shut",
        ),
    ],
}


class SemanticEvidenceExtractor:
    """Extractor binding spoken claims to physical, tactile documentary exhibits (Rule 141)."""

    def __init__(self):
        pass

    def detect_archetype(self, sentence: str, market: str = "EN") -> ForensicArchetype:
        """Classify the spoken sentence into one of 5 canonical forensic archetypes."""
        if not sentence or not sentence.strip():
            return ForensicArchetype.INVESTIGATIVE_MEDIA

        canon_market = resolve_canonical_market(market_raw=market)
        s_lower = sentence.lower()

        # 1. Quantitative Metric takes high precedence if metric regex matches
        if _METRIC_REGEX.search(sentence) or any(kw in s_lower for kw in _KEYWORD_TAXONOMY[ForensicArchetype.QUANTITATIVE_METRIC].get(canon_market, [])):
            return ForensicArchetype.QUANTITATIVE_METRIC

        # 2. Check each taxonomy with market keywords
        scores: Dict[ForensicArchetype, int] = {arc: 0 for arc in ForensicArchetype}

        for arc, market_dict in _KEYWORD_TAXONOMY.items():
            for kw in market_dict.get(canon_market, []):
                if kw in s_lower:
                    scores[arc] += 2
            for kw in market_dict.get("EN", []):
                if kw in s_lower:
                    scores[arc] += 1

        best_arc, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score > 0:
            return best_arc

        return ForensicArchetype.INVESTIGATIVE_MEDIA

    def extract_evidence(
        self,
        sentence: str,
        market: str = "EN",
        scene_id: Optional[str] = None
    ) -> ExtractedEvidence:
        """Extract tactile documentary exhibits and kinetic action bound strictly to claim (Rule 141)."""
        canon_market = resolve_canonical_market(market_raw=market)
        archetype = self.detect_archetype(sentence, market=canon_market)

        variants = _ARCHETYPE_VARIANTS.get(archetype, [])
        if not variants:
            return ExtractedEvidence(
                archetype=archetype,
                dominant_family="H5_OPTICAL",
                hero_anchor_prop="archival investigative document exhibit on aged newsprint (#F4F1EA)",
                interacting_tool_prop="red directional ink marker stroke",
                tactile_action_verb="sweeps cleanly across",
                physical_reaction="text highlights with authentic print grain",
                tactile_residue="crimson underline mark",
                layout_type="center_stage",
                camera_directive="Top-down slow push-in on continuous cream mat (#F4F1EA)",
                sound_foley="crisp_paper_snap",
            )

        # Dynamic rotation: derive index from scene_id (e.g. SCENE_01 -> 0, SCENE_02 -> 1)
        # to guarantee adjacent scenes rotate across distinct tools and camera moves
        variant_idx = 0
        if scene_id:
            m = re.search(r"(\d+)", str(scene_id))
            if m:
                variant_idx = int(m.group(1)) - 1
        if variant_idx == 0 and not scene_id and sentence:
            import hashlib
            variant_idx = int(hashlib.md5(sentence.encode("utf-8")).hexdigest(), 16)

        return variants[variant_idx % len(variants)]


# Global singleton instance
_EXTRACTOR_INSTANCE: Optional[SemanticEvidenceExtractor] = None


def get_semantic_evidence_extractor() -> SemanticEvidenceExtractor:
    global _EXTRACTOR_INSTANCE
    if _EXTRACTOR_INSTANCE is None:
        _EXTRACTOR_INSTANCE = SemanticEvidenceExtractor()
    return _EXTRACTOR_INSTANCE


def extract_evidence_for_sentence(
    sentence: str,
    market: str = "EN",
    scene_id: Optional[str] = None
) -> ExtractedEvidence:
    """Convenience functional interface for Claim-to-Evidence extraction."""
    return get_semantic_evidence_extractor().extract_evidence(
        sentence=sentence,
        market=market,
        scene_id=scene_id
    )
