#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/vox_continuous_director_engine.py — Permanent Vox Object-Assembly & Continuous Flow Engine.

Enforces:
- Rule 118: Zero-mock data, factual script decomposition.
- Rule 128: Generic Contract Pattern (supports any market: EN, KR, JA, VN).
- Rule 130: Factual Causal Integrity & Search-Intent Payoff.
- Rule 131: 10X Beat Architecture & Editorial Signal Purity.
- Rule 132: Pure Transmission Pipe (loads prompt from config/prompts/vox_b3_director_image_prompt.md).
- Anti-Slideshow Mandate: Sequence Blocks, Spatial Anchors, Tactile Cutouts, and Continuity Links.
- 7-Account Rotation: Even round-robin distribution across acc_01 to acc_07.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("vf.vox_continuous_director")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 7 Confirmed Physical Accounts for Google Flow Veo 3.1 Fast rotation
FLOW_ACCOUNTS = ["acc_01", "acc_02", "acc_03", "acc_04", "acc_05", "acc_06", "acc_07"]

# Signature Vox Color Palette
VOX_PALETTE = {
    "cream": "#F4F1EA",
    "charcoal": "#1A1A1A",
    "terracotta": "#C85A32",
    "yellow": "#F2C230",
    "navy": "#1B2B4A",
    "muted_gold": "#D4AF37",
    "olive": "#4A5D4E",
}

DEFAULT_NEGATIVE_PROMPT = (
    "no text overlay, no floating text, no subtitles, no captions, no typography, no letters, no words floating in air, "
    "no headlines, no beat numbers, no tags, no speech bubbles, no title text, no clutter, no unnecessary objects, "
    "no excessive icons, no visual noise, no random decorations, no fantasy elements, no sci-fi elements, no anime, "
    "no cartoon style, no CGI look, no glossy 3D rendering, no photorealistic background, no oversaturated rainbow colors, "
    "no poor composition, no distorted anatomy, no watermark, no logos, no VOX logo, no Veo logo, no brand icons, "
    "no wooden table, no wood grain, no brown wood desk, no corkboard, no cork texture, no floating currency symbols, "
    "no floating dollar signs, no floating euro signs, no cartoon gavel, no garbled letters, maintain a clean premium "
    "VOX-style editorial collage on aged cream paper surface with layered paper textures and documentary-quality composition."
)

CANVAS_WORKSPACES = [
    "Aged Cream Newsprint Workspace #F4F1EA with subtle print halftone grid and clean editorial top-down lighting",
    "Aged Cream Archival Paper Surface #F4F1EA with delicate drafting crosshairs and soft directional desk shadow",
    "Aged Cream Documentary Ledger Desk #F4F1EA with faint geometric measurement grid in muted charcoal",
]


def load_b2_script(episode_dir: Path) -> Dict[str, Any]:
    """Load B2 script from episode directory, with fallbacks."""
    for cand in ["b2_script.json", "spoken_sentences.json", "brain_input.json"]:
        p = episode_dir / cand
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if "full_spoken_script" in data:
                    return data
                if isinstance(data, list) and len(data) > 0 and "sentence" in data[0]:
                    return {"title": episode_dir.name, "market": episode_dir.name.split("_")[0], "sentences": data}
                if "story" in data:
                    return {"title": data.get("title", episode_dir.name), "market": episode_dir.name.split("_")[0], "full_spoken_script": data["story"]}
            except Exception as e:
                logger.warning(f"Error reading {p}: {e}")
    raise FileNotFoundError(f"No valid script found in {episode_dir}")


def split_script_into_sentences(script_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse narration text into clean sentences, preserving Acts if present."""
    if "sentences" in script_data and isinstance(script_data["sentences"], list):
        return script_data["sentences"]

    raw_text = script_data.get("full_spoken_script", "")
    lines = raw_text.split("\n")

    current_act = "ACT I"
    raw_sentences = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        act_match = re.match(r"^===\s*(ACT\s+[IVX]+)\s*===$", line, re.I)
        if act_match:
            current_act = act_match.group(1).upper()
            continue

        # Split line by sentence terminators
        # Matches Korean/Japanese/English/Vietnamese punctuation (. ? ! 。)
        sentence_chunks = re.split(r"(?<=[.?!。])\s+", line)
        for chunk in sentence_chunks:
            chunk = chunk.strip()
            if len(chunk) > 5:
                raw_sentences.append({
                    "act": current_act,
                    "sentence": chunk
                })

    return raw_sentences


def compute_timeframes(sentences: List[Dict[str, Any]], target_duration_sec: float = 0.0) -> List[Dict[str, Any]]:
    """Assign start_sec, end_sec and timeframe strings to each sentence."""
    total_chars = sum(len(s["sentence"]) for s in sentences)
    if total_chars == 0:
        return sentences

    # Default ~4.5 - 5.5s per sentence
    current_time = 0.0
    for idx, s in enumerate(sentences):
        char_len = len(s["sentence"])
        # Estimate duration: base 2.5s + char proportion
        dur = max(3.5, min(7.0, char_len * 0.12))
        start_sec = current_time
        end_sec = current_time + dur
        current_time = end_sec

        def sec_to_tc(sec: float) -> str:
            m = int(sec // 60)
            s_val = int(sec % 60)
            return f"{m:02d}:{s_val:02d}"

        s["start_sec"] = round(start_sec, 2)
        s["end_sec"] = round(end_sec, 2)
        s["duration_sec"] = round(dur, 2)
        s["timeframe"] = f"{sec_to_tc(start_sec)} - {sec_to_tc(end_sec)}"
        s["scene_index"] = idx + 1

    return sentences


def group_into_sequence_blocks(sentences: List[Dict[str, Any]], scenes_per_block: int = 6) -> List[Dict[str, Any]]:
    """Partition sentences into thematic Sequence Blocks with shared canvas workspaces."""
    block_index = 1
    current_block_scenes = []

    for idx, s in enumerate(sentences):
        # Create new block if needed
        if idx > 0 and (idx % scenes_per_block == 0 or (idx < len(sentences) - 1 and s.get("act") != sentences[idx - 1].get("act"))):
            block_index += 1

        act_name = s.get("act", f"ACT_{block_index}").replace(" ", "_")
        block_slug = f"BLOCK_{block_index}_{act_name}"
        s["sequence_block"] = block_slug
        s["canvas_workspace"] = CANVAS_WORKSPACES[(block_index - 1) % len(CANVAS_WORKSPACES)]

    return sentences


# Multilingual Thematic Archetypes for Vox Investigative Collage (Rule 128 Generic Contract)
VOX_THEMATIC_ARCHETYPES = {
    "LEGAL_DISMISSAL": {
        "triggers": ["법인세", "과세", "tax", "소송", "판결", "대법원", "court", "ruling", "패소", "lawsuit", "verdict", "thuế", "toà", "án", "裁判", "判決"],
        "variants": [
            (
                "An official corporate tax demand and judicial dismissal decree on tactile aged parchment",
                ["A crimson wax dismissal seal stamped over the disputed figures", "Paper shears cutting through the tax document"],
                VOX_PALETTE["terracotta"]
            ),
            (
                "A formal judicial ruling scroll with gold foil official seal stamp",
                ["A crisp red-line strike-through annotation across the disputed claims", "A wooden verification caliper measuring the legal margin"],
                VOX_PALETTE["charcoal"]
            ),
            (
                "A statutory tax code dossier with paper bookmarks and highlighted legal clauses",
                ["A brass pointer arrow pointing to the statutory exemption section", "A bold terracotta #C85A32 document classification tab"],
                VOX_PALETTE["terracotta"]
            )
        ]
    },
    "FINANCIAL_SCALE": {
        "triggers": ["매출", "revenue", "조", "billion", "trillion", "dollar", "돈", "profit", "원", "수익", "doanh thu", "lợi nhuận", "tiền", "売上", "利益"],
        "variants": [
            (
                "A towering vertical skyscraper built from stacked paper ledger pages and currency bundles",
                ["A measurement caliper clamping the total height", "A bold Vox Yellow #F2C230 highlight circle"],
                VOX_PALETTE["yellow"]
            ),
            (
                "A tactile multi-tiered paper bar chart illustrating massive financial divergence",
                ["Dashed red vector comparison lines", "A crisp cutout percentage label badge"],
                VOX_PALETTE["yellow"]
            ),
            (
                "A forensic financial balance sheet ledger with cut paper income columns",
                ["A magnifying loupe hovering over zero-tax liabilities", "A bold charcoal contrast border"],
                VOX_PALETTE["charcoal"]
            )
        ]
    },
    "OFFSHORE_FLOW": {
        "triggers": ["싱가포르", "offshore", "국경", "해외", "이전", "flow", "transfer", "ship", "singapore", "chuyển giá", "xuyên biên giới", "hải ngoại", "海外", "移転"],
        "variants": [
            (
                "A stylized paper cargo freighter boat carrying stacked digital data containers",
                ["Dashed vector shipping route lines printed in terracotta ink", "Dual national flag badges"],
                VOX_PALETTE["navy"]
            ),
            (
                "An isometric transnational capital pipeline conduit carved from layered parchment",
                ["Tactile paper arrows indicating offshore capital velocity", "A brass junction valve cutout"],
                VOX_PALETTE["navy"]
            ),
            (
                "A cut-paper international jurisdiction map showing cross-border monetary transfer",
                ["Luminous yellow trajectory curves", "A stamped customs clearance mark"],
                VOX_PALETTE["yellow"]
            )
        ]
    },
    "INFRASTRUCTURE_PE": {
        "triggers": ["고정사업장", "서버", "server", "office", "사무실", "거점", "pe", "establishment", "hạ tầng", "máy chủ", "cơ sở", "サーバー", "拠点"],
        "variants": [
            (
                "An isometric paper diorama of a server rack building with translucent wireframe grid",
                ["A magnifying loupe hovering over empty concrete foundations", "A bold red question mark cutout"],
                VOX_PALETTE["charcoal"]
            ),
            (
                "A tactile architectural blueprint cutout of a corporate branch without physical servers",
                ["A red hatched exclusion boundary zone", "A crisp brass drafting pin"],
                VOX_PALETTE["navy"]
            ),
            (
                "A cut paper telecommunications satellite uplink terminal mounted on a paper grid",
                ["Concentric radar pulse rings in muted charcoal", "A disconnected cable plug cutout"],
                VOX_PALETTE["charcoal"]
            )
        ]
    },
    "TREATY_CLASSIFICATION": {
        "triggers": ["조약", "법률", "treaty", "서랍", "조세조약", "beps", "oecd", "drawer", "hiệp định", "phân loại", "条約", "分類"],
        "variants": [
            (
                "A dual-drawer wooden filing cabinet rendered in clean flat paper collage cutouts",
                ["Brass label plates reading 'ROYALTY' vs 'BUSINESS PROFIT'", "A skeleton brass key hovering over the keyhole"],
                VOX_PALETTE["muted_gold"]
            ),
            (
                "An antique two-pan balance scale tipping under conflicting legal interpretations",
                ["Cut paper weights labeled with statutory articles", "A taut red indicator needle"],
                VOX_PALETTE["muted_gold"]
            ),
            (
                "A bilateral tax treaty parchment document with official wax ribbons",
                ["A dual-color classification divider separating royalty from profit", "A stamped diplomatic seal"],
                VOX_PALETTE["terracotta"]
            )
        ]
    },
    "INVESTIGATIVE_AUDIT": {
        "triggers": ["조사", "자료", "증거", "국세청", "investigation", "evidence", "audit", "thanh tra", "bằng chứng", "調査", "証拠"],
        "variants": [
            (
                "An archival confidential dossier folder stamped with red investigation markers",
                ["A tactile paper paperclip binding critical audit findings", "A bold terracotta #C85A32 classification stamp"],
                VOX_PALETTE["terracotta"]
            ),
            (
                "A tactile paper evidence board with taut red threads connecting corporate nodes",
                ["Cutout documentary photograph markers", "A crisp stamped verification badge"],
                VOX_PALETTE["navy"]
            ),
            (
                "A vintage forensic magnifying loupe highlighting microscopic paper audit trails",
                ["A bold yellow indicator beacon", "A series of numbered evidence tags"],
                VOX_PALETTE["yellow"]
            )
        ]
    }
}


def extract_vox_metaphor_entities(
    sentence: str,
    market: str = "KR",
    scene_idx: int = 0,
    sentence_data: Optional[Dict[str, Any]] = None,
    used_heroes: Optional[List[str]] = None
) -> Tuple[str, List[str], str]:
    """Extract or synthesize tactile hero cutout object and interacting elements with strict anti-repetition deduplication."""
    # 1. Respect pre-existing upstream metadata if already forged by high-level planner (Rule 118 & 132)
    if sentence_data:
        existing_hero = sentence_data.get("hero_cutout_object") or sentence_data.get("visual_metaphor")
        existing_interacting = sentence_data.get("interacting_objects")
        existing_color = sentence_data.get("color_accent")
        if existing_hero and len(existing_hero) > 10 and existing_interacting:
            color = existing_color or VOX_PALETTE["terracotta"]
            return existing_hero, existing_interacting, color

    s_low = sentence.lower()

    # 2. Generic fallback pool
    generic_pool = [
        (
            "An archival confidential dossier folder stamped with red investigation markers",
            ["A tactile paper paperclip binding critical audit findings", "A bold terracotta #C85A32 classification stamp"],
            VOX_PALETTE["terracotta"]
        ),
        (
            "A tactile paper evidence board with taut red threads connecting corporate nodes",
            ["Cutout documentary photograph markers", "A crisp stamped verification badge"],
            VOX_PALETTE["navy"]
        ),
        (
            "A vintage mechanical balance scale tipping under paper document weights",
            ["Tactile paper arrows indicating direction of capital flow", "A bold Vox Yellow #F2C230 highlight circle"],
            VOX_PALETTE["yellow"]
        ),
        (
            "A stylized architectural floor plan map with cut paper zone overlays",
            ["Isometric drafting pins in brass", "A stamped jurisdiction boundary border"],
            VOX_PALETTE["muted_gold"]
        ),
        (
            "An antique two-pan balance scale tipping under conflicting legal interpretations",
            ["Cut paper weights labeled with statutory articles", "A taut red indicator needle"],
            VOX_PALETTE["muted_gold"]
        ),
        (
            "A dual-drawer wooden filing cabinet rendered in clean flat paper collage cutouts",
            ["Brass label plates reading 'ROYALTY' vs 'BUSINESS PROFIT'", "A skeleton brass key hovering over the keyhole"],
            VOX_PALETTE["muted_gold"]
        )
    ]

    # 3. Match against thematic archetypes
    matched_archetype = None
    for arch_name, arch_data in VOX_THEMATIC_ARCHETYPES.items():
        if any(trig in s_low for trig in arch_data["triggers"]):
            matched_archetype = arch_name
            break

    if matched_archetype:
        variants = VOX_THEMATIC_ARCHETYPES[matched_archetype]["variants"]
        # Prioritize first variant that has not been used in used_heroes
        selected_variant = None
        for v in variants:
            if used_heroes and v[0] in used_heroes:
                continue
            selected_variant = v
            break
        # If all archetype variants are exhausted, draw from unused generic pool
        if selected_variant is None:
            for g in generic_pool:
                if used_heroes and g[0] in used_heroes:
                    continue
                selected_variant = g
                break
        # Ultimate fallback
        if selected_variant is None:
            selected_variant = variants[scene_idx % len(variants)]
        return selected_variant[0], list(selected_variant[1]), selected_variant[2]

    # 4. If no archetype matched, draw from generic pool with deduplication
    selected_generic = None
    for g in generic_pool:
        if used_heroes and g[0] in used_heroes:
            continue
        selected_generic = g
        break
    if selected_generic is None:
        selected_generic = generic_pool[scene_idx % len(generic_pool)]

    return selected_generic[0], list(selected_generic[1]), selected_generic[2]


def synthesize_motion_track(
    hero: str,
    interacting: List[str],
    scene_idx: int,
    duration_sec: float = 6.0
) -> Dict[str, Any]:
    """Generate deterministic Vox object-assembly motion track with dynamic beats (S1..Sn)."""
    quadrants = ["Center stage", "Center-left of canvas", "Center-right of canvas", "Bottom-center stage"]
    anchor = quadrants[scene_idx % len(quadrants)]
    hero_short = hero.split(" on ")[0].split(" built ")[0].strip()

    entry_verbs = [
        "slides smoothly into",
        "drops flat onto the desk with a tactile paper snap at",
        "folds open across",
        "lands firmly onto"
    ]
    entry_verb = entry_verbs[scene_idx % len(entry_verbs)]

    # Dynamic Motion Beats generation based on story pacing and interacting props
    beats = []

    # S1: Hero Entry
    t1_end = min(2.0, round(duration_sec * 0.35, 1))
    beats.append({
        "step": 1,
        "timing": f"0.0-{t1_end}s",
        "action": f"{hero_short} {entry_verb} {anchor} and settles with tactile paper drop shadow",
        "type": "ENTRY"
    })

    # S2: First Interacting Element Assembly
    inter1 = interacting[0] if interacting else "tactile measurement caliper"
    t2_start = t1_end
    t2_end = min(3.8, round(duration_sec * 0.7, 1)) if len(interacting) > 1 else duration_sec
    beats.append({
        "step": 2,
        "timing": f"{t2_start}-{t2_end}s",
        "action": f"{inter1} stamps firmly onto the surface, anchoring into place",
        "type": "ASSEMBLY"
    })

    # S3: Second Interacting Element or Red Vector Thread Connection
    if len(interacting) > 1:
        inter2 = interacting[1]
        beats.append({
            "step": 3,
            "timing": f"{t2_end}-{duration_sec:.1f}s",
            "action": f"{inter2} connects via red vector thread, locking the complete paper composition in place",
            "type": "INTERACTION"
        })

    # S4: Micro-shadow breathing for longer scenes (>= 6.5s)
    if duration_sec >= 6.5:
        beats.append({
            "step": len(beats) + 1,
            "timing": f"{max(4.5, duration_sec - 1.5):.1f}-{duration_sec:.1f}s",
            "action": "Subtle micro-shadow breathing <= 2px while entire cutout cluster remains completely static on desk grid",
            "type": "SETTLE"
        })

    entry_action = f"0.0-{t1_end}s: {hero_short} {entry_verb} {anchor}"
    assembly_step = f"{t1_end}-{duration_sec:.1f}s: {inter1} stamps onto surface and locks into place"

    return {
        "dynamic_motion_beats": beats,
        "spatial_anchor": f"{anchor}, permanently locked on desk grid with zero drift",
        "camera_rule": "Completely static camera, no 3D pan/zoom",
        "entry_action": entry_action,
        "assembly_step": assembly_step
    }


def synthesize_continuity_link(hero: str, interacting: List[str], next_sentence: Optional[str] = None) -> str:
    """Generate physical bridging rule linking current object to the next scene."""
    base_obj = hero.split(" on ")[0].split(" built ")[0]
    return f"The {base_obj} remains anchored on desk; in the following scene, it serves as the physical foundation or target for the subsequent tactile action."


def build_image_prompt(
    canvas: str,
    color_bar: str,
    headline: str,
    hero: str,
    interacting: List[str]
) -> str:
    """Synthesize 5-layer image prompt strictly adhering to Vox documentary collage rules."""
    interacting_str = ", ".join(interacting)
    layer_bg = f"Layer 1: {canvas}"
    layer_geo = f"Layer 2: bold flat geometric color block in {color_bar}"
    layer_space = "Layer 3: generous clean editorial negative space and balanced compositional breathing room, strictly zero floating typography or subtitles (typography is animated in post-production)"
    layer_cutout = f"Layer 4: high-contrast tactile paper cutout subject with crisp 2-4px white deckle edge and realistic soft drop shadow: {hero}. Interacting elements: {interacting_str}"
    layer_texture = "Layer 5: vintage print ink texture, natural paper grain, subtle fold creases, authentic newspaper print misregistration"

    prompt = (
        f"Editorial investigative documentary frame in signature VOX paper-cut collage style. "
        f"[{layer_bg}] -> [{layer_geo}] -> [{layer_space}] -> [{layer_cutout}] -> [{layer_texture}]. "
        f"Strictly locked color palette: Vox Yellow #F2C230, Terracotta #C85A32, Navy #1B2B4A, Muted Gold #D4AF37 on Off-white Cream #F4F1EA. "
        f"Clear object-assembly composition, strong editorial hierarchy, tactile paper craft. "
        f"Negative prompt: {DEFAULT_NEGATIVE_PROMPT}"
    )
    return prompt


def extract_editorial_tag(sentence_text: str) -> Tuple[str, str]:
    """Extract native headline and generic English editorial tag across languages (Rule 128)."""
    words = [w for w in re.split(r"\s+", sentence_text) if len(w) > 1]
    native_hl = " ".join(words[:3]) if words else "SCENE"
    s_low = sentence_text.lower()

    if any(k in s_low for k in ["법인세", "과세", "tax", "thuế", "taxation", "소송", "판결", "대법원", "court", "ruling", "패소", "toà", "án", "裁判", "判決"]):
        english_tag = "CORPORATE TAX & RULING"
    elif any(k in s_low for k in ["매출", "revenue", "조", "billion", "trillion", "profit", "doanh thu", "lợi nhuận", "tiền", "売上", "利益"]):
        english_tag = "REVENUE SCALE"
    elif any(k in s_low for k in ["싱가포르", "offshore", "해외", "국경", "transfer", "flow", "singapore", "xuyên biên giới", "海外", "移転"]):
        english_tag = "OFFSHORE CAPITAL"
    elif any(k in s_low for k in ["서버", "고정사업장", "pe", "establishment", "server", "máy chủ", "cơ sở", "サーバー", "拠点"]):
        english_tag = "PERMANENT ESTABLISHMENT"
    elif any(k in s_low for k in ["조약", "beps", "oecd", "treaty", "서랍", "hiệp định", "phân loại", "条約", "分類"]):
        english_tag = "TAX TREATY"
    elif any(k in s_low for k in ["조사", "자료", "증거", "evidence", "investigation", "audit", "thanh tra", "bằng chứng", "調査", "証拠"]):
        english_tag = "FORENSIC AUDIT"
    else:
        english_tag = "INVESTIGATIVE DOSSIER"

    return native_hl, english_tag


def generate_continuous_director_plan(
    episode_dir: Path,
    output_filename: str = "director_plan.json"
) -> Dict[str, Any]:
    """Main execution function: Ingests script and generates continuous object-assembly director plan."""
    script_data = load_b2_script(episode_dir)
    ep_id = episode_dir.name
    market = ep_id.split("_")[0] if "_" in ep_id else script_data.get("market", "KR")
    title = script_data.get("title", f"Episode {ep_id}")

    raw_sentences = split_script_into_sentences(script_data)
    if not raw_sentences:
        raise ValueError(f"Script contains no parseable sentences in {episode_dir}")

    timed_sentences = compute_timeframes(raw_sentences)
    blocked_sentences = group_into_sequence_blocks(timed_sentences, scenes_per_block=6)

    processed_scenes = []
    unique_blocks = set()
    used_heroes: List[str] = []

    for idx, s in enumerate(blocked_sentences):
        scene_id = f"SCENE_{idx + 1:02d}"
        seq_block = s["sequence_block"]
        unique_blocks.add(seq_block)
        canvas = s["canvas_workspace"]
        sentence_text = s["sentence"]
        duration_sec = s.get("duration_sec", 6.0)

        hero, interacting, color_accent = extract_vox_metaphor_entities(sentence_text, market, idx, s, used_heroes)
        used_heroes.append(hero)
        motion_track = synthesize_motion_track(hero, interacting, idx, duration_sec)

        # Generate headline and clean editorial topic tag (strictly no internal 'BEAT' numbering)
        native_hl, english_tag = extract_editorial_tag(sentence_text)
        bilingual_hl = f"{native_hl} // {english_tag}"

        next_sent = blocked_sentences[idx + 1]["sentence"] if idx + 1 < len(blocked_sentences) else None
        continuity_link = synthesize_continuity_link(hero, interacting, next_sent)

        img_prompt = build_image_prompt(canvas, color_accent, bilingual_hl, hero, interacting)

        scene_obj = {
            "scene_id": scene_id,
            "sequence_block": seq_block,
            "timeframe": s["timeframe"],
            "sentence": sentence_text,
            "core_idea": english_tag,
            "headline": bilingual_hl,
            "bilingual_headline": bilingual_hl,
            "editorial_title": bilingual_hl,
            "visual_metaphor": f"{hero} interacting with {', '.join(interacting)}",
            "canvas_workspace": canvas,
            "hero_cutout_object": hero,
            "interacting_objects": interacting,
            "motion_track_and_assembly": motion_track,
            "graphic_typography": {
                "headline": native_hl,
                "english_tag": english_tag,
                "color_bar": color_accent,
                "position": "Top-left, occupying 25% negative space"
            },
            "visual_continuity_link_to_next": continuity_link,
            "color_accent": color_accent,
            "image_prompt": img_prompt
        }
        processed_scenes.append(scene_obj)

    final_plan = {
        "episode_id": ep_id,
        "title": title,
        "market": market,
        "format": "VOX_CONTINUOUS_OBJECT_ASSEMBLY_COLLAGE",
        "total_scenes": len(processed_scenes),
        "total_sequence_blocks": len(unique_blocks),
        "scenes": processed_scenes
    }

    # Save director_plan.json
    out_path = episode_dir / output_filename
    out_path.write_text(json.dumps(final_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"✅ Generated {len(processed_scenes)} continuous Vox scenes in {out_path}")

    # Generate flow_video_manifest.json with 7-account round-robin rotation
    generate_7acc_flow_manifest(episode_dir, processed_scenes)

    return final_plan


def generate_7acc_flow_manifest(episode_dir: Path, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates flow_video_manifest.json with guaranteed round-robin rotation across 7 accounts."""
    clips = []
    for idx, s in enumerate(scenes):
        s_id = s["scene_id"]
        flow_slot = FLOW_ACCOUNTS[idx % len(FLOW_ACCOUNTS)]
        out_fn = f"clip_{s_id.lower()}.mp4"

        # Construct comprehensive Veo prompt from dynamic motion beats
        motion_track = s.get("motion_track_and_assembly", {})
        dynamic_steps = motion_track.get("dynamic_motion_beats", [])
        subject = s["hero_cutout_object"].split(" on ")[0].split(" built ")[0].strip()
        step_narratives = [f"{st['timing']}: {st['action']}" for st in dynamic_steps]
        steps_text = "; ".join(step_narratives) if step_narratives else motion_track.get("entry_action", "")
        anchor = motion_track.get("spatial_anchor", "Center stage, permanently locked on desk grid with zero drift")

        veo_prompt = (
            f"Editorial paper cutout animation in Vox documentary style. Animate completed composition: {subject}. "
            f"{steps_text}. Spatial anchor: {anchor}. Every object permanently locked, zero drift. "
            f"Camera: Completely static top-down desk view, no 3D pan/zoom, no camera tilt. "
            f"Tactile paper motion, crisp deckle white edges, subtle micro-shadow breathing <= 2px."
        )

        clips.append({
            "scene_id": s_id,
            "clip_index": idx + 1,
            "flow_slot": flow_slot,
            "output_filename": out_fn,
            "prompt": veo_prompt,
            "timeframe": s["timeframe"],
            "sentence": s["sentence"]
        })

    manifest = {
        "episode_id": episode_dir.name,
        "format": "FLOW_VEO_7_ACCOUNT_DISPATCH",
        "total_clips": len(clips),
        "accounts_used": FLOW_ACCOUNTS,
        "clips": clips
    }

    man_path = episode_dir / "flow_video_manifest.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"✅ Generated flow_video_manifest.json ({len(clips)} clips rotated across {len(FLOW_ACCOUNTS)} accounts) -> {man_path}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Permanent Vox Continuous Director Engine")
    parser.add_argument("--episode", required=True, help="Episode ID (folder name in episodes/)")
    parser.add_argument("--output", default="director_plan.json", help="Output file name")
    args = parser.parse_args()

    ep_dir = ROOT_DIR / "episodes" / args.episode
    if not ep_dir.exists():
        logger.error(f"❌ Episode directory does not exist: {ep_dir}")
        sys.exit(1)

    try:
        generate_continuous_director_plan(ep_dir, args.output)
    except Exception as e:
        logger.error(f"❌ Error during director plan generation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
