"""
Service: B3 Dynamic Hollywood Art Director & Universal Scene Breakdown Engine (/director:plan)
Single Source of Truth: HHTech GPT-6-Astra + Director Plan Notion DB (5b201989-2400-8295-be81-81c2c0e4e138)
Rule 116 & 435: Dual-Layer Remotion Render Architecture (16:9 BG + 1:1 FG #FF00FF Chroma Key).
Rule 120: Audio & Subtitle Timing Sync (duration_est_sec strictly aligned with spoken narration timestamps).
Rule 128: Zero Semantic Bias. Dynamically analyzes story.txt to derive Era Anchor, physical/geographical environment,
          atmospheric lighting mood, color palette, and Dynamic Character Ensemble (4-8 roles) without static topic relics.
Rule 445: 5-Beat Investigative Docudrama storyboard structure (35 to 55 dynamic scenes).
Rule 446: English Production Bridge for all visual prompt descriptions.
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

import os
ROOT_DIR = Path(os.getenv("VF_ROOT_DIR", Path(__file__).resolve().parent.parent.parent))

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.skill_loader import (
    get_b3_strategic_rules,
    get_b35_strategic_rules
)

DIRECTOR_PLAN_FLAT_DB_ID = "5b201989-2400-8295-be81-81c2c0e4e138"
DIRECTOR_PLAN_PARENT_PAGE_ID = "73801989-2400-82a7-ae5f-0110bfb666c8"

# 5 Beat Canonical Investigative Docudrama Names (Rule 445)
CANONICAL_BEATS = [
    "Beat 1: The Impossible Contradiction",
    "Beat 2: The False Narrative & Red Herring",
    "Beat 3: The Systemic Blindspot & Paper Trail",
    "Beat 4: The Real Culprit & Smoking Gun",
    "Beat 5: The Uncomfortable Modern Mirror & Living Warning"
]

# Rule 128: Concise targeted art direction rules (~1.2k chars) replacing 336k chars dump
TARGETED_ART_RULES = get_b3_strategic_rules()


class DynamicArchetypeDict(dict):
    """Rule 128: Zero-Semantic-Bias Dynamic Archetype Registry with backward compatibility."""
    def __missing__(self, key):
        return {
            "director": f"Investigative Cinematic Docudrama ({str(key).title()} Style)",
            "visual_tone": f"Atmospheric authentic narrative environment reflecting {key}",
            "palette": "Desaturated earthy ochre, slate grey, muted ambient contrasts",
            "camera_style": "Slow creeping push-ins, atmospheric tracking, high-tension staging"
        }


# 7 Golden Content Axes (Notion SoT Second Brain & Hollywood Principles)
CINEMATIC_ARCHETYPES = DynamicArchetypeDict({
    "business_rise_fall": {
        "director": "GPT-6-Astra — David Fincher & Adam McKay (Corporate Noir & Forensic Exposition) Principle",
        "visual_tone": "Glossy corporate boardroom veneer contrasting cold trading floors, shredded paper trails, creeping push-ins on forensic ledger anomalies",
        "palette": "Cold steel blue, dark charcoal, toxic amber highlights, fluorescent office hum",
        "camera_style": "Slow creeping push-ins on financial ledgers, clinical wide corporate establishing shots, whip pans on margin calls"
    },
    "systemic_crisis": {
        "director": "GPT-6-Astra — Johan Renck & Denis Villeneuve (Oppressive Institutional Realism & Brutal Scale) Principle",
        "visual_tone": "Monumental institutional corridors, decaying supply chain depots, heavy dust beams through fractured blinds, systemic infrastructure collapse",
        "palette": "Desaturated slate stone, oxidized bronze, aged ochre, industrial charcoal, deep chiaroscuro",
        "camera_style": "Slow deliberate surveillance tracking, high-angle institutional scale observation, lingering frozen tableaux"
    },
    "true_crime": {
        "director": "GPT-6-Astra — David Fincher & Errol Morris (Forensic Procedural Noir — Non-Graphic) Principle",
        "visual_tone": "Evidence locker dim lighting, sterile courtroom benches, macro document forgery examinations, high-contrast interrogation rooms",
        "palette": "Low-key obsidian black, desaturated neutral slate, cold fluorescent white, deep chiaroscuro shadows",
        "camera_style": "Precision analytical tracking, tight macro close-ups on physical evidence, static high-tension procedural compositions"
    },
    "psychology": {
        "director": "GPT-6-Astra — Denis Villeneuve & Darren Aronofsky (Psychological Mystery & Geometric Disorientation) Principle",
        "visual_tone": "Claustrophobic interrogation spaces, symbolic geometric architectural framing, disorienting shadow play dissecting herd bias and manipulation",
        "palette": "Deep graphite monochrome with solitary amber/crimson focal accents, psychological shadow contrasts",
        "camera_style": "Creeping slow push-ins creating psychological intimacy, symmetrical wide tableaus, abrupt perspective shifts"
    },
    "tech_geopolitics": {
        "director": "GPT-6-Astra — Christopher Nolan (Cold Analytical Precision & Global Asymmetric Stakes) Principle",
        "visual_tone": "Humming photolithography cleanrooms, submarine fiber-optic cable routes, satellite command telemetry, dark geopolitical summit chambers",
        "palette": "Silicon cyan, cleanroom amber, server rack emerald, cold titanium silver, deep surveillance indigo",
        "camera_style": "Clinical surveillance pans, sharp graphic whip-cuts between maps and hardware, high-angle technological dominance framing"
    },
    "institutional_regulatory": {
        "director": "GPT-6-Astra — Steven Soderbergh & Michael Mann (Clinical Whistleblower & Regulatory Chokepoint) Principle",
        "visual_tone": "Municipal registry desks, confidential inspection archives with red rejected stamps, sealed sample containers, late-night whistleblowing meetings",
        "palette": "Clinical pale cyan, antiseptic mint green, institutional beige, iodine amber, brushed stainless steel",
        "camera_style": "Forensic macro close-ups on regulatory clause stamps and approval dates, handheld observational creeping push-ins, clinical wide archive corridors"
    },
    "asymmetric_flows": {
        "director": "GPT-6-Astra — Martin Scorsese & J.C. Chandor (Asymmetric Financial Thriller & Underground Flows) Principle",
        "visual_tone": "Discreet offshore private banking suites, encrypted dark-terminal trading desks, luxury maritime harbors concealing shell company assets",
        "palette": "Deep velvet midnight blue, tarnished brass gold, dark burgundy, cigar-smoke chiaroscuro",
        "camera_style": "Slow predator tracking shots, clinical over-the-shoulder document inspections, abrupt freezing snap-zooms on hidden beneficiary names"
    },
    "default": {
        "director": "GPT-6-Astra — Denis Villeneuve & David Fincher (Investigative Realism) Principle",
        "visual_tone": "Moody atmospheric tension, dramatic low-key lighting, textured architectural backgrounds, forensic depth of field",
        "palette": "Muted earth tones, cinematic contrast, shadow-heavy rim lighting",
        "camera_style": "Creeping push-ins, dynamic eye-level forensic staging, dramatic low-angle power shots"
    }
})

# Backward compatibility aliases for legacy callers and tests
CINEMATIC_ARCHETYPES["finance"] = CINEMATIC_ARCHETYPES["business_rise_fall"]
CINEMATIC_ARCHETYPES["history"] = CINEMATIC_ARCHETYPES["systemic_crisis"]


def detect_cinematic_archetype(niche: str = "", topic: str = "", story_text: str = "") -> dict:
    """
    Universal dynamic cinematic archetype and visual grammar detection (Rule 128).
    Routes dynamically based on the 7 Golden Content Axes (Notion SoT Second Brain).
    """
    combined = f"{niche} {topic} {story_text[:600]}".lower()

    # 1. Tech & Geopolitical Battles
    if any(k in combined for k in ["tech", "chip", "semiconductor", "asml", "tsmc", "silicon", "geopolitic", "supply chain", "cable", "satellite", "cyber", "hardware", "lithography", "quantum"]):
        return CINEMATIC_ARCHETYPES["tech_geopolitics"]

    # 2. Institutional & Regulatory Chokepoints / Medical / Whistleblower
    elif any(k in combined for k in ["regulatory", "chokepoint", "inspector", "compliance", "oversight", "pension", "license", "permit", "coverup", "recall", "medical", "pharma", "clinical", "hospital", "drug", "medicine", "vaccine", "toxic", "poison", "epidemic", "cholera", "pesticide"]):
        return CINEMATIC_ARCHETYPES["institutional_regulatory"]

    # 3. Hidden Asymmetric Fortunes & Underground Flows
    elif any(k in combined for k in ["underground", "illicit", "laundering", "smuggl", "offshore", "shell company", "shadow banking", "dark pool", "cartel", "asymmetric", "hidden fortune", "bribe", "kickback"]):
        return CINEMATIC_ARCHETYPES["asymmetric_flows"]

    # 4. True Crime Non-Graphic
    elif any(k in combined for k in ["crime", "murder", "killer", "investigation", "forensic", "court", "trial", "verdict", "police", "detective", "fbi", "heist"]):
        return CINEMATIC_ARCHETYPES["true_crime"]

    # 5. Psychology & Behavioral Manipulation
    elif any(k in combined for k in ["psycholog", "manipulat", "cult", "mind", "behavior", "brainwash", "cognitive", "hysteria", "bias", "propaganda", "societal", "mass panic"]):
        return CINEMATIC_ARCHETYPES["psychology"]

    # 6. Business Rise & Fall / Corporate Debt
    elif any(k in combined for k in ["finance", "economy", "bank", "money", "fraud", "wall street", "debt", "lehman", "madoff", "enron", "trading", "business", "rehabilitation", "bankruptcy", "collateral", "lien"]):
        return CINEMATIC_ARCHETYPES["business_rise_fall"]

    # 7. Modern History & Systemic Crisis
    elif any(k in combined for k in ["history", "empire", "war", "monarchy", "oppenheimer", "manhattan project", "soviet", "cold war", "chernobyl", "medieval", "century", "labor day", "strike", "crisis"]):
        return CINEMATIC_ARCHETYPES["systemic_crisis"]

    return CINEMATIC_ARCHETYPES["default"]


# Universal spatial indicators for dynamic environment extraction
SPATIAL_INDICATORS = [
    "field", "farm", "valley", "village", "town", "city", "province", "district",
    "depot", "warehouse", "facility", "plant", "factory", "dock", "harbor", "port",
    "chamber", "room", "hall", "corridor", "boardroom", "office", "headquarters",
    "archive", "laboratory", "lab", "clinic", "hospital", "ward", "station", "terminal",
    "street", "alley", "square", "road", "quarry", "mine", "compound", "complex", "market"
]

AGENT_STEMS = [
    "investigator", "inspector", "analyst", "auditor", "specialist", "researcher", "scientist", "toxicologist",
    "physician", "doctor", "epidemiologist", "chemist", "biologist", "engineer", "technician",
    "official", "regulator", "director", "manager", "administrator", "executive", "officer", "commissioner",
    "witness", "eyewitness", "informant", "whistleblower", "insider", "clerk", "custodian", "archivist",
    "farmer", "cultivator", "grower", "worker", "laborer", "operator", "merchant", "trader", "dealer",
    "broker", "banker", "accountant", "lawyer", "attorney", "prosecutor", "judge",
    "journalist", "reporter", "curate", "resident", "villager", "citizen", "survivor"
]

STOP_MODIFIERS = {
    "the", "a", "an", "this", "that", "these", "those", "each", "every", "some", "any", "all",
    "in", "on", "at", "by", "with", "from", "to", "for", "of", "and", "or", "as", "into", "meanwhile",
    "however", "later", "then", "when", "while", "during", "after", "before", "several", "arrived"
}


def extract_universal_semantic_context(story_text: str, metadata: dict = None, intel_card: dict = None) -> dict:
    """
    Universal Dynamic Semantic Context & Era Extractor (Rule 128 - Zero Semantic Bias).
    Directly analyzes story.txt to derive Era Anchor, physical/geographical environment,
    lighting mood, and color palette without static hardcoded dictionaries or topic conditionals.
    """
    if not metadata:
        metadata = {}
    if not intel_card:
        intel_card = {}

    story_lower = story_text.lower()

    # 1. Dynamic Era Anchor Extraction
    era_anchor = "Contemporary investigative documentary setting with period-authentic documentation and architecture"
    years = [int(y) for y in re.findall(r"\b(1[5-9]\d{2}|20\d{2})\b", story_text)]
    if years:
        min_y = min(years)
        max_y = max(years)
        if max_y < 1900:
            cent = (max_y // 100) + 1
            suf = "th" if 11 <= cent <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(cent % 10, "th")
            era_anchor = f"{cent}{suf} Century (circa {min_y if min_y == max_y else f'{min_y}–{max_y}'}) with authentic period architecture and documentation"
        elif max_y < 1945:
            era_anchor = f"Early 20th Century era (circa {min_y if min_y == max_y else f'{min_y}–{max_y}'}) with period-authentic documentation and architecture"
        elif max_y < 1990:
            dec = (max_y // 10) * 10
            era_anchor = f"Mid-to-Late 20th Century ({dec}s era) with period-accurate setting and archival records"
        elif max_y < 2010:
            era_anchor = f"Turn of the 21st Century (circa {min_y if min_y == max_y else f'{min_y}–{max_y}'}) investigative setting with contemporary documentation"
        else:
            era_anchor = f"Contemporary era (circa {max_y}) with modern investigative documentation, setting, and infrastructure"
    else:
        cent_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+century\b", story_lower)
        if cent_match:
            era_anchor = f"{cent_match.group(1)}th Century historical period setting with authentic architecture and era documentation"
        else:
            decade_match = re.search(r"\b(19\d0s|20\d0s)\b", story_lower)
            if decade_match:
                era_anchor = f"{decade_match.group(1)} period investigative setting with era-authentic documentation and architecture"
            else:
                period_cues = []
                for term in ["victorian", "edwardian", "medieval", "feudal", "colonial", "ancient", "renaissance", "industrial revolution", "cold war", "post-war", "contemporary"]:
                    if re.search(r"\b" + re.escape(term) + r"\b", story_lower):
                        period_cues.append(term.title())
                if period_cues:
                    era_anchor = f"{', '.join(period_cues[:2])} era investigative setting with period-authentic architecture and documentation"

    # 2. Dynamic Physical & Geographical Environment Extraction
    env_cues = []
    seen_spaces = set()
    sentences = re.split(r"(?<=[.!?])\s+", story_text)
    for sent in sentences:
        for space in SPATIAL_INDICATORS:
            if space in seen_spaces:
                continue
            m = re.search(r"\b([A-Za-z-]+(?:\s+[A-Za-z-]+)?)\s+" + re.escape(space) + r"(?:s|es)?\b", sent, re.IGNORECASE)
            if m:
                pre = m.group(1).strip()
                pre_words = [w for w in pre.split() if w.lower() not in STOP_MODIFIERS]
                if pre_words:
                    env_chunk = f"{' '.join(pre_words).lower()} {space}"
                else:
                    env_chunk = f"{space} setting"
                seen_spaces.add(space)
                env_cues.append(env_chunk)
                if len(env_cues) >= 4:
                    break
        if len(env_cues) >= 4:
            break

    if env_cues:
        physical_environment = f"Authentic narrative environment: {'; '.join(env_cues)}, reflecting primary setting locations and institutional archives"
    else:
        topic_hint = metadata.get("topic") or intel_card.get("target_keyword", "Investigative Setting")
        topic_clean = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", "", str(topic_hint)).strip()
        clean_env_label = topic_clean if len(topic_clean) >= 3 else "authentic documentary setting"
        physical_environment = f"Authentic narrative environment reflecting {clean_env_label}, with dedicated field operational sites and archival document repositories"

    # 3. Dynamic Atmospheric Lighting Mood
    lighting_cues = []
    for cue in ["dawn", "morning", "twilight", "dusk", "sunset", "night", "midnight", "nocturnal",
                "fog", "mist", "haze", "rain", "storm", "overcast", "cloudy", "smoke", "dust",
                "fluorescent", "gaslit", "candlelit", "neon", "low-key", "chiaroscuro", "shadow", "dim", "flicker"]:
        if re.search(r"\b" + re.escape(cue) + r"\b", story_lower):
            lighting_cues.append(cue)

    if lighting_cues:
        lighting_mood = f"Cinematic documentary chiaroscuro with motivated directional lighting, capturing {', '.join(lighting_cues[:3])} atmosphere and textured low-key shadows"
    else:
        lighting_mood = "Cinematic documentary chiaroscuro with motivated directional lighting, dramatic low-key contrast and textured atmospheric shadows"

    # 4. Dynamic Color Palette
    color_cues = []
    for c in ["slate", "charcoal", "ochre", "amber", "sepia", "rust", "bronze", "patina", "emerald",
              "crimson", "cobalt", "cyan", "gold", "silver", "steel", "terracotta", "olive", "sage"]:
        if re.search(r"\b" + re.escape(c) + r"\b", story_lower):
            color_cues.append(c)

    if color_cues:
        color_palette = f"Cinematic desaturated palette featuring {', '.join(color_cues[:4])}, deep charcoal shadows, and naturalistic atmospheric contrast"
    else:
        if "19th" in era_anchor or "victorian" in era_anchor.lower() or "early 20th" in era_anchor.lower():
            color_palette = "Muted historical earth pigments, aged sepia, oxidized patina, iron rust, and deep charcoal shadows"
        else:
            color_palette = "Desaturated cinematic tones, muted natural pigments, charcoal blacks, and naturalistic contrast highlights"

    return {
        "era_anchor": era_anchor,
        "physical_environment": physical_environment,
        "lighting_mood": lighting_mood,
        "color_palette": color_palette
    }


def extract_dynamic_character_ensemble(story_text: str, dynamic_context: dict = None, topic: str = "") -> list[dict]:
    """
    Universal Dynamic Character Ensemble Extractor (Rule 128 - Zero Semantic Bias).
    Extracts 4-8 distinct character roles authentic to the narrative from story.txt.
    Parses narrative agent nouns and actions without hardcoded topic conditionals.
    Each character contains: role_name, archetype, visual_cues, attire.
    """
    if not dynamic_context:
        dynamic_context = {}
    era = dynamic_context.get("era_anchor", "").lower()

    roles = []
    seen_stems = set()
    sentences = re.split(r"(?<=[.!?])\s+", story_text)

    pattern = re.compile(
        r"\b(?:(?:the|a|an|with|from|by|at|in)\s+)?([A-Za-z-]+(?:\s+[A-Za-z-]+)?)\s+(" +
        "|".join(AGENT_STEMS) + r")(?:s|es)?\b",
        re.IGNORECASE
    )

    for sent in sentences:
        for match in pattern.finditer(sent):
            mod, noun = match.groups()
            stem = noun.lower()
            if stem in seen_stems:
                continue

            mod_words = [w for w in mod.split() if w.lower() not in STOP_MODIFIERS]
            if mod_words:
                role_name = f"{' '.join(mod_words).title()} {noun.title()}"
            else:
                role_name = f"{noun.title()}"

            seen_stems.add(stem)

            # Archetype derived from narrative function
            if any(k in stem for k in ["investigator", "inspector", "auditor", "researcher", "detective"]):
                archetype = "Meticulous & skeptical investigator tracing anomalies"
            elif any(k in stem for k in ["witness", "eyewitness", "resident", "villager", "citizen", "survivor", "farmer", "cultivator"]):
                archetype = "Observant & vigilant local eyewitness holding key testimony"
            elif any(k in stem for k in ["official", "regulator", "director", "manager", "administrator", "executive", "officer", "commissioner"]):
                archetype = "Conflicted & guarded institutional authority facing scrutiny"
            elif any(k in stem for k in ["scientist", "analyst", "physician", "doctor", "epidemiologist", "toxicologist", "chemist"]):
                archetype = "Clinical & objective scientific analyst uncovering empirical evidence"
            elif any(k in stem for k in ["whistleblower", "insider", "informant"]):
                archetype = "Anxious & resolute insider exposing hidden misconduct"
            else:
                archetype = "Focused & methodical key participant in the narrative"

            # Attire harmonized with era and role function
            if any(k in era for k in ["19th", "victorian", "edwardian"]):
                attire = "period-authentic 19th-century Victorian attire, wool frock coat or work apron, sturdy leather boots"
            elif any(k in era for k in ["early 20th", "mid-to-late 20th", "cold war", "1970", "1980"]):
                attire = "period-authentic mid-20th-century vintage trench coat or pressed collared workwear"
            else:
                if any(k in stem for k in ["farmer", "cultivator", "worker", "laborer", "grower"]):
                    attire = "utilitarian outdoor work jacket, weathered canvas pants, durable boots"
                elif any(k in stem for k in ["scientist", "analyst", "physician", "doctor", "toxicologist", "chemist"]):
                    attire = "sanitary laboratory coat, protective gloves, analytical attire"
                elif any(k in stem for k in ["executive", "director", "auditor", "manager", "lawyer", "attorney"]):
                    attire = "tailored formal executive suit, crisp collared shirt, professional dress shoes"
                else:
                    attire = "durable utilitarian field jacket, pressed trousers, sturdy shoes"

            # Visual Cues extracted from sentence action
            action_match = re.search(r"\b(examining|inspecting|discovering|reviewing|tracking|holding|uncovering|documenting|interviewing|testing)\s+([a-z\s]{5,35})\b", sent, re.IGNORECASE)
            if action_match:
                visual_cues = f"{action_match.group(1).lower()} {action_match.group(2).strip()}, observed in scene context"
            else:
                visual_cues = "examining critical physical documentation and artifacts in scene setting"

            roles.append({
                "role_name": role_name,
                "archetype": archetype,
                "visual_cues": visual_cues,
                "attire": attire
            })

            if len(roles) >= 8:
                break
        if len(roles) >= 8:
            break

    # Guarantee 4-8 roles using generic docudrama ensemble customized to era
    generic_archetypes = [
        ("Lead Field Investigator", "Meticulous & skeptical investigator tracing anomalies", "holding evidence dossier, reviewing records", "durable utilitarian trench coat and work trousers"),
        ("Primary Field Eyewitness", "Observant & vigilant local eyewitness holding key testimony", "standing cautiously, observing surrounding setting", "authentic civilian workwear appropriate to setting"),
        ("Administrative Oversight Official", "Conflicted & guarded institutional authority facing scrutiny", "presenting official compliance binder with stern expression", "formal municipal suit with administrative badge"),
        ("Forensic Evidence Analyst", "Clinical & objective scientific analyst uncovering empirical evidence", "inspecting physical sample container with magnifying lens", "protective laboratory jacket and utility gloves"),
        ("Archival Records Custodian", "Weary & meticulous guardian of institutional memory", "pulling heavy archival cardboard evidence box from metal shelving", "cardigan sweater over oxford shirt, spectacles on cord"),
        ("Institutional Strategic Director", "Conflicted figurehead facing public exposure", "standing before official conference table, reviewing internal memo", "formal tailored institutional suit, executive demeanor")
    ]
    gen_idx = 0
    while len(roles) < 4 and gen_idx < len(generic_archetypes):
        g_name, g_arch, g_cues, g_attire = generic_archetypes[gen_idx]
        if not any(g_name.lower() in r["role_name"].lower() for r in roles):
            roles.append({
                "role_name": g_name,
                "archetype": g_arch,
                "visual_cues": g_cues,
                "attire": g_attire
            })
        gen_idx += 1

    return roles[:8]


def extract_story_beats(story_text: str) -> list[dict]:
    """Parse story into 5 beats if headers exist, or divide dynamically."""
    beats = []
    current_beat_title = ""
    current_lines = []

    beat_patterns = [
        re.compile(r"^(?:={2,}\s*)?(?:#+\s*)?(?:ACT|BEAT)\s*([1-5]|IV|I{1,3}|V)[:\-\s=]*(.*)", re.IGNORECASE),
        re.compile(r"^(?:##\s*)?(The Impossible Contradiction|The False Narrative|The Systemic Blindspot|The Real Culprit|The Uncomfortable Modern Mirror)", re.IGNORECASE)
    ]

    for line in story_text.splitlines():
        matched = False
        for p in beat_patterns:
            m = p.match(line.strip())
            if m:
                if current_lines:
                    beats.append({
                        "title": current_beat_title or f"Beat {len(beats) + 1}",
                        "content": "\n".join(current_lines).strip()
                    })
                    current_lines = []
                current_beat_title = line.strip().strip("=").strip("#").strip()
                matched = True
                break
        if not matched:
            current_lines.append(line)

    if current_lines:
        beats.append({
            "title": current_beat_title or f"Beat {len(beats) + 1}",
            "content": "\n".join(current_lines).strip()
        })

    # If story didn't have explicit beat headers, divide into 5 chunks
    if len(beats) < 5:
        all_lines = [l for l in story_text.splitlines() if l.strip()]
        chunk_size = max(1, len(all_lines) // 5)
        beats = []
        for i in range(5):
            chunk = all_lines[i * chunk_size : (i + 1) * chunk_size] if i < 4 else all_lines[i * chunk_size :]
            beats.append({
                "title": CANONICAL_BEATS[i],
                "content": "\n".join(chunk).strip()
            })

    return beats[:5]


def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merge update dict into base dict without destructive overwriting."""
    result = dict(base)
    for k, v in update.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def generate_director_plan(
    episode_id: str,
    story_text: str = None,
    intel_card: dict = None,
    metadata: dict = None,
    skip_notion: bool = False
) -> dict:
    """
    Core B3 Art Director & Universal Scene Breakdown Engine (Rule 128).
    Breaks down 5-Beat story into 35-55 dynamic cinematic scenes.
    Generates flexible asset roster (BG pool and FG pool) per Beat.
    Produces director_plan.json, dp_plan.json, and brain_input.json (non-destructive deep-merge).
    """
    logger.info(f"🎬 [B3 Director] Starting Art Direction for Episode: {episode_id}")

    # 1. Resolve inputs
    ep_dir = ROOT_DIR / "episodes" / episode_id
    ws_dir = ROOT_DIR / "workspace" / episode_id
    var_vf_dir = Path(f"/var/vf/episodes/{episode_id}")
    ep_dir.mkdir(parents=True, exist_ok=True)
    ws_dir.mkdir(parents=True, exist_ok=True)
    if var_vf_dir.parent.exists() or Path("/var/vf").exists():
        var_vf_dir.mkdir(parents=True, exist_ok=True)

    if not story_text:
        story_candidates = [
            var_vf_dir / "story.txt",
            ep_dir / "story.txt",
            ws_dir / "story.txt"
        ]
        for sc in story_candidates:
            if sc.exists():
                story_text = sc.read_text(encoding="utf-8")
                break

    if not story_text:
        raise FileNotFoundError(f"Cannot find story.txt for episode {episode_id}")

    if not intel_card:
        intel_candidates = [
            var_vf_dir / "competitor_intel_card.json",
            ep_dir / "competitor_intel_card.json",
            ws_dir / "competitor_intel_card.json"
        ]
        for ic in intel_candidates:
            if ic.exists():
                try:
                    intel_card = json.loads(ic.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass
        if not intel_card:
            intel_card = {}

    if not metadata:
        metadata = {}

    niche = metadata.get("niche") or intel_card.get("niche", "Investigative Documentary")
    topic = metadata.get("topic") or intel_card.get("target_keyword", episode_id)

    # Rule 128: Universal Dynamic Context & Character Ensemble Extraction
    dynamic_context = extract_universal_semantic_context(story_text, metadata, intel_card)
    character_ensemble = extract_dynamic_character_ensemble(story_text, dynamic_context, topic)
    archetype = detect_cinematic_archetype(niche, topic, story_text)

    story_beats = extract_story_beats(story_text)
    is_cjk = any("\u4e00" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff" or "\uac00" <= char <= "\ud7af" for char in story_text[:500])
    total_words = int(len(story_text) / 2.5) if is_cjk else len(story_text.split())
    logger.info(f"  [B3] Story length: {total_words} words ({len(story_text)} chars) across {len(story_beats)} beats. Archetype: {archetype['director']}")
    logger.info(f"  [B3] Extracted Era: {dynamic_context['era_anchor']}. Ensemble: {len(character_ensemble)} roles.")

    m_up = (metadata.get("market") or episode_id.split("_")[0]).upper()
    if m_up in ["JP", "JA"]:
        market_lang_name = "Japanese (日本語)"
    elif m_up in ["KR", "KO"]:
        market_lang_name = "Korean (한국어)"
    elif m_up in ["VN", "VI"]:
        market_lang_name = "Vietnamese (Tiếng Việt)"
    else:
        market_lang_name = "English"

    # 2. Build Hollywood Art Director Prompt using concise targeted rules
    targeted_art_rules = get_b3_strategic_rules()
    system_prompt = (
        f"{targeted_art_rules}\n\n"
        "You are an Elite Hollywood Art Director, Director of Photography (DP), and Master Visual Storyboard Editor.\n"
        f"You direct in the visual style of {archetype['director']}.\n"
        f"Visual Tone: {dynamic_context['physical_environment']}.\n"
        f"Era Anchor: {dynamic_context['era_anchor']}.\n"
        f"Color Palette: {dynamic_context['color_palette']}.\n"
        f"Lighting Grammar: {dynamic_context['lighting_mood']}.\n"
        f"Camera Grammar: {archetype.get('camera_style', 'Atmospheric slow push-ins and tracking shots')}.\n\n"
        "YOUR CORE MISSION:\n"
        "Break down this complete 5-Beat Investigative Docudrama story into a DYNAMIC, HIGH-TENSION storyboard (typically 35 to 55 scenes).\n"
        "DO NOT force an arbitrary mathematical count. Let the scenes flow naturally from the narrative units (30-50 words per scene, ~8-18 seconds duration).\n"
        "EVERY SCENE MUST SERVE A PSYCHOLOGICAL AND INVESTIGATIVE PURPOSE.\n\n"
        "CRITICAL ARCHITECTURAL MANDATES:\n"
        "1. TWO-LAYER RENDER SYSTEM (Rule 116):\n"
        "   - Layer 1 Background (16:9 widescreen 2560x1440): Cinematic period/topic environment. Safe-zone clear in bottom 20% for subtitles, center-right negative space for foreground overlay.\n"
        "   - Layer 2 Foreground (1:1 2048x2048): Stylized Editorial Graphic Novel Digital Illustration isolated on pure solid flat #FF00FF magenta chroma key. Full-body standing or seated visible head-to-toe. NO photorealistic humans.\n"
        "2. DYNAMIC CHARACTER ENSEMBLE (Rule 128):\n"
        f"   - Authentically draw characters from this narrative ensemble: {[c['role_name'] for c in character_ensemble]}.\n"
        "3. FLEXIBLE ASSET ROSTER PER BEAT:\n"
        "   - Each Beat defines a pool of Backgrounds (2-4 key locations) and Foregrounds (1-3 key figures).\n"
        "   - Maintain background_reuse_key and foreground_reuse_key across continuous sequences.\n"
        "4. DUAL-LANGUAGE PROTOCOL (Production Bridge Rule 446 & Market Rule 120):\n"
        "   - VISUAL PROMPTS (bg_prompt, fg_prompt, visual_metaphor): MUST BE IN ENGLISH for the image generation engine.\n"
        f"   - SPOKEN NARRATION ('narration' field in each scene): MUST BE 100% WRITTEN IN {market_lang_name}! NEVER translate narration to English for non-English markets! Voiceover TTS & subtitles require authentic {market_lang_name}.\n\n"
        "OUTPUT FORMAT: Return ONLY a valid JSON object matching the exact schema below. No markdown fences."
    )

    user_payload = {
        "episode_id": episode_id,
        "market": m_up,
        "narration_language": market_lang_name,
        "niche": niche,
        "topic": topic,
        "director_archetype": archetype["director"],
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "fatal_explanatory_vacuum": intel_card.get("competitor_narrative_anatomy", {}).get("fatal_explanatory_vacuum", ""),
        "story_beats": [
            {
                "beat_index": i + 1,
                "beat_name": CANONICAL_BEATS[i],
                "content": story_beats[i]["content"][:1500]
            }
            for i in range(len(story_beats))
        ]
    }

    prompt_instruction = (
        f"CRITICAL HOLLYWOOD STORYBOARD & PACING DIRECTIVE (Rules 116, 120, 128, 445):\n"
        f"The full story contains {total_words} words across 5 beats. You MUST break down the complete narrative into 35 to 55 sequential scenes (typically 7 to 10 scenes per beat).\n"
        f"1. SENTENCE-ATOMIC PACING & SPOKEN LANGUAGE PURITY:\n"
        f"   - The 'narration' field MUST be in {market_lang_name} matching the verbatim storyline, strictly 1-2 complete sentences ending with terminal punctuation.\n"
        f"   - Subtitle line budget: strictly fits within 2 lines on 1920x1080 display (~35-40 characters/line). Remotion and Karaoke TTS anchor strictly to these sentence cut marks.\n"
        f"   - Calculate 'duration_est_sec' strictly at standard narration pace: max(7, min(16, round(word_count / 2.4))).\n"
        f"2. ARCHETYPE-SPECIFIC CINEMATIC GRAMMAR & CAMERA PRINCIPLES:\n"
        f"   - Adopt the visual pacing of {archetype['director']}. You choose specific camera angles (e.g. slow_push_in, clinical_macro, wide_tableaux) and tension dynamically.\n"
        f"3. BALANCED VISUAL CONTINUITY WITHIN BEATS:\n"
        f"   - Maintain visual harmony within each beat: share location anchors so scenes do not jump randomly every frame, but evolve angles naturally.\n"
        f"4. TWO-LAYER COMPOSITION & SUBTITLE SAFE-ZONE INTEGRITY:\n"
        f"   - Background (16:9 2560x1440): bottom 20% clear for subtitles.\n"
        f"   - Foreground (1:1 2048x2048 #FF00FF): position strictly 'right' or 'left' (Rule of Thirds). NEVER place full-body characters at 'center'.\n\n"
        "Output a JSON object with this EXACT structure:\n"
        "{\n"
        "  \"episode_id\": \"" + episode_id + "\",\n"
        "  \"visual_tone\": \"" + dynamic_context['physical_environment'] + "\",\n"
        "  \"color_palette\": \"" + dynamic_context['color_palette'] + "\",\n"
        "  \"director_archetype\": \"" + archetype['director'] + "\",\n"
        "  \"scenes\": [\n"
        "    {\n"
        "      \"scene_id\": \"sc001\",\n"
        "      \"beat_index\": 1,\n"
        "      \"beat_name\": \"Beat 1: The Impossible Contradiction\",\n"
        "      \"narration\": \"exact complete sentence/spoken text for this scene.\",\n"
        "      \"duration_est_sec\": 11,\n"
        "      \"visual_metaphor\": \"metaphorical meaning\",\n"
        "      \"camera\": {\n"
        "        \"movement\": \"slow_push_in\",\n"
        "        \"tension_level\": \"high\"\n"
        "      },\n"
        "      \"background\": {\n"
        "        \"reuse_key\": \"" + episode_id.lower() + "_bg_b1_loc0\",\n"
        "        \"visual_description\": \"Detailed 16:9 cinematic environment...\",\n"
        "        \"safe_zone\": \"bottom 20% clear for subtitles, center-right negative space for foreground\"\n"
        "      },\n"
        "      \"foreground\": {\n"
        "        \"reuse_key\": \"" + episode_id.lower() + "_fg_b1_char0\",\n"
        "        \"character_role\": \"" + character_ensemble[0]['role_name'] + "\",\n"
        "        \"psychological_state\": \"" + character_ensemble[0]['archetype'] + "\",\n"
        "        \"body_language\": \"" + character_ensemble[0]['visual_cues'] + "\",\n"
        "        \"position\": \"right\",\n"
        "        \"visual_description\": \"Stylized editorial graphic novel digital illustration on #FF00FF magenta background...\"\n"
        "      },\n"
        "      \"audio_sfx_cue\": \"distant_siren_and_flickering_light\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Input Data:\n" + json.dumps(user_payload, ensure_ascii=False)
    )

    logger.info("  [B3] Calling HHTech GPT-6-Astra for Hollywood Director Plan...")
    raw_res = ""
    for attempt in range(1, 3):
        try:
            raw_res = call_gpt6_astra(
                prompt=prompt_instruction,
                system_prompt=system_prompt,
                max_tokens=6500,
                timeout=180.0
            )
            if raw_res and raw_res.strip():
                break
        except Exception as e:
            logger.warning(f"  [B3] LLM attempt {attempt} failed: {e}")
            time.sleep(3)

    # 3. Parse JSON
    parsed = None
    if raw_res and raw_res.strip():
        cleaned = raw_res.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            parsed = json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"  [B3] Failed to parse LLM JSON: {e}. Attempting recovery...")
            m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception:
                    pass

    # 4. Fallback synthesis if LLM failed or generated insufficient scenes (< min_required_scenes) (Rule 445: 35-55 dynamic scenes)
    min_required_scenes = max(35, min(55, total_words // 30)) if total_words > 300 else 5
    llm_scenes = parsed.get("scenes", []) if parsed else []
    if not parsed or len(llm_scenes) < min_required_scenes:
        if parsed and llm_scenes:
            logger.warning(f"  [B3] LLM returned insufficient scenes ({len(llm_scenes)} < {min_required_scenes}). Activating robust deterministic scene synthesizer fallback...")
        else:
            logger.warning("  [B3] Activating robust deterministic scene synthesizer fallback...")
        parsed = _synthesize_deterministic_director_plan(
            episode_id,
            story_beats,
            archetype,
            dynamic_context=dynamic_context,
            character_ensemble=character_ensemble
        )

    scenes = parsed.get("scenes", [])
    logger.info(f"  [B3] Successfully created {len(scenes)} cinematic scenes across 5 beats.")

    # 5. Normalize scene structure and build dp_plan
    normalized_scenes = []
    bg_roster = {}
    fg_roster = {}

    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id") or f"sc{idx:03d}"
        beat_idx = sc.get("beat_index") or ((idx // max(1, len(scenes) // 5)) + 1)
        beat_idx = min(max(int(beat_idx), 1), 5)
        beat_name = sc.get("beat_name") or CANONICAL_BEATS[beat_idx - 1]

        narration = sc.get("narration") or ""
        dur = sc.get("duration_est_sec") or sc.get("duration_sec") or max(8, min(18, len(narration.split()) // 3))

        bg = sc.get("background") or {}
        bg_key = bg.get("reuse_key") or f"{episode_id.lower()}_bg_b{beat_idx}_loc{idx:02d}"
        bg_desc = bg.get("visual_description") or sc.get("image_prompt") or f"Cinematic documentary environment for {beat_name}"
        if bg_key in bg_roster:
            bg_desc = bg_roster[bg_key]["description"]
        else:
            bg_roster[bg_key] = {
                "key": bg_key,
                "beat": beat_name,
                "description": bg_desc,
                "safe_zone": "bottom 20% safe zone for subtitles, center-right negative space for foreground"
            }

        fg = sc.get("foreground")
        fg_key = None
        if fg and isinstance(fg, dict):
            fg_key = fg.get("reuse_key") or f"{episode_id.lower()}_fg_b{beat_idx}_char{idx:02d}"
            fg_desc = fg.get("visual_description") or sc.get("foreground_prompt") or f"Stylized editorial graphic novel character for {beat_name}"
            if fg_key in fg_roster:
                fg_desc = fg_roster[fg_key]["description"]
            else:
                fg_roster[fg_key] = {
                    "key": fg_key,
                    "beat": beat_name,
                    "role": fg.get("character_role", "Key Narrative Figure"),
                    "body_language": fg.get("body_language", "Standing full body, expressive investigative posture"),
                    "description": fg_desc,
                    "position": fg.get("position", "right" if idx % 2 == 0 else "left")
                }

        cam = sc.get("camera") or {}
        cam_mov = cam.get("movement") if isinstance(cam, dict) else str(cam)
        cam_mov = cam_mov or ("slow_push_in" if idx % 3 == 0 else ("static_tension" if idx % 3 == 1 else "tracking_left"))

        norm_sc = {
            "scene_index": idx,
            "scene_id": sc_id,
            "beat_index": beat_idx,
            "beat": beat_name,
            "narration": narration,
            "narration_segment": narration,
            "duration_est": float(dur),
            "duration_sec": int(dur),
            "visual_metaphor": sc.get("visual_metaphor", "Systemic tension and institutional conflict"),
            "camera": {
                "movement": cam_mov,
                "tension_level": cam.get("tension_level", "high") if isinstance(cam, dict) else "high"
            },
            "bg_reuse_key": bg_key,
            "bg_prompt": bg_desc,
            "background_reuse_key": bg_key,
            "image_prompt": bg_desc,
            "fg_reuse_key": fg_key or "",
            "fg_prompt": fg_roster.get(fg_key, {}).get("description", "") if fg_key else "",
            "foreground_reuse_key": fg_key or "",
            "foreground_prompt": fg_roster.get(fg_key, {}).get("description", "") if fg_key else "",
            "foreground_position": fg.get("position", "right") if fg else "right",
            "safe_zone": "bottom",
            "audio_sfx_cue": sc.get("audio_sfx_cue", "distant_room_tone")
        }
        normalized_scenes.append(norm_sc)

    # 6. Assemble complete output payloads
    director_plan = {
        "episode_id": episode_id,
        "niche": niche,
        "topic": topic,
        "director_archetype": archetype["director"],
        "visual_tone": dynamic_context["physical_environment"],
        "color_palette": dynamic_context["color_palette"],
        "camera_style": archetype.get("camera_style", "Cinematic documentary tracking"),
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "total_scenes": len(normalized_scenes),
        "background_roster": bg_roster,
        "foreground_roster": fg_roster,
        "scenes": normalized_scenes
    }

    dp_plan = {
        "episode_id": episode_id,
        "scenes": [
            {
                "scene_id": s["scene_id"],
                "scene_index": s["scene_index"],
                "camera_movement": s["camera"]["movement"],
                "tension_level": s["camera"]["tension_level"],
                "bg_key": s["bg_reuse_key"],
                "fg_key": s["fg_reuse_key"],
                "duration_est": s["duration_est"],
                "audio_sfx": s["audio_sfx_cue"]
            }
            for s in normalized_scenes
        ]
    }

    # Non-destructive deep-merge for brain_input.json preserving all B2 metadata
    existing_brain = {}
    candidate_files = [var_vf_dir / "brain_input.json", ep_dir / "brain_input.json", ws_dir / "brain_input.json"]
    for cf in candidate_files:
        if cf.exists():
            try:
                with open(cf, "r", encoding="utf-8") as bf:
                    existing_brain = json.load(bf)
                break
            except Exception:
                pass

    brain_update = {
        "episode_id": episode_id,
        "content_type": "investigative_docudrama",
        "story": story_text,
        "director_archetype": archetype["director"],
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "scenes": normalized_scenes,
        "render_architecture": "remotion_twolayer_karaoke_v4"
    }

    brain_input = _deep_merge(existing_brain, brain_update)
    # Explicitly enforce preservation of all B2 metadata
    b2_metadata_keys = [
        "story_gate_score",
        "story_verdict",
        "market",
        "topic",
        "hook_3s",
        "breakout_queries",
        "niche",
        "search_specific_keyword"
    ]
    for k in b2_metadata_keys:
        if k in existing_brain:
            brain_input[k] = existing_brain[k]

    # 7. Persist to canonical directories
    canonical_dirs = [ws_dir, ep_dir]
    if var_vf_dir.exists() and var_vf_dir not in canonical_dirs:
        canonical_dirs.append(var_vf_dir)

    for target_dir in canonical_dirs:
        with open(target_dir / "director_plan.json", "w", encoding="utf-8") as f:
            json.dump(director_plan, f, indent=2, ensure_ascii=False)
        with open(target_dir / "dp_plan.json", "w", encoding="utf-8") as f:
            json.dump(dp_plan, f, indent=2, ensure_ascii=False)
        with open(target_dir / "brain_input.json", "w", encoding="utf-8") as f:
            json.dump(brain_input, f, indent=2, ensure_ascii=False)

    logger.info(f"  [B3] Saved director_plan.json & dp_plan.json to {canonical_dirs}")

    # 8. Trigger B3.5 Prompt Forge to generate specialized visual prompts
    try:
        from app.services.prompt_forge import generate_scene_prompts, push_prompts_to_notion
        logger.info("  [B3.5] Forging visual prompts via Prompt Forge Engine...")
        bg_req = {k: {"visual_hint": v["description"], "narration_context": v["beat"]} for k, v in bg_roster.items()}
        fg_req = {k: {"visual_hint": v["description"], "narration_context": v["beat"]} for k, v in fg_roster.items()}

        prompts_res = generate_scene_prompts(
            bg_dict=bg_req,
            fg_dict=fg_req,
            story_title=topic,
            scenes=normalized_scenes,
            task_id=episode_id
        )

        # Map forged prompts back to each scene in director_plan
        for sc in director_plan.get("scenes", []):
            bg_k = sc.get("bg_reuse_key")
            if bg_k and bg_k in prompts_res.get("backgrounds", {}):
                sc["bg_prompt"] = prompts_res["backgrounds"][bg_k]
                sc["image_prompt"] = prompts_res["backgrounds"][bg_k]
            fg_k = sc.get("fg_reuse_key")
            if fg_k and fg_k in prompts_res.get("foregrounds", {}):
                sc["fg_prompt"] = prompts_res["foregrounds"][fg_k]
                sc["foreground_prompt"] = prompts_res["foregrounds"][fg_k]

        for target_dir in canonical_dirs:
            with open(target_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
                json.dump(prompts_res, f, indent=2, ensure_ascii=False)
            with open(target_dir / "prompts.json", "w", encoding="utf-8") as f:
                json.dump(prompts_res, f, indent=2, ensure_ascii=False)
            with open(target_dir / "director_plan.json", "w", encoding="utf-8") as f:
                json.dump(director_plan, f, indent=2, ensure_ascii=False)
            with open(target_dir / "dp_plan.json", "w", encoding="utf-8") as f:
                json.dump({"scenes": director_plan.get("scenes", [])}, f, indent=2, ensure_ascii=False)

        if not skip_notion:
            push_prompts_to_notion(prompts_res, episode_id)
            logger.info("  [B3.5] Prompts pushed to Notion Prompt Library DB.")
    except Exception as e:
        logger.warning(f"  [B3.5] Prompt Forge integration encountered notice: {e}")

    # 9. Sync to Notion Director Plan DB
    if not skip_notion:
        push_director_plan_to_notion(director_plan, episode_id)

    return director_plan


def _synthesize_deterministic_director_plan(
    episode_id: str,
    story_beats: list[dict],
    archetype: dict,
    dynamic_context: dict = None,
    character_ensemble: list[dict] = None
) -> dict:
    """
    Robust fallback scene breakdown with dynamic character ensemble and authentic narrative context.
    Rule 128: Uses dynamic character ensemble extracted directly from narrative. Zero static role pools.
    """
    if not dynamic_context:
        dynamic_context = {
            "era_anchor": "Contemporary investigative documentary era",
            "physical_environment": archetype.get("visual_tone", "Authentic narrative environment"),
            "lighting_mood": "Low-key cinematic chiaroscuro with motivated shadows",
            "color_palette": archetype.get("palette", "Desaturated cinematic tones")
        }

    if not character_ensemble:
        character_ensemble = [
            {
                "role_name": "Lead Field Investigator",
                "archetype": "Meticulous & skeptical investigator tracing anomalies",
                "visual_cues": "holding evidence binder, examining physical document",
                "attire": "dark utilitarian field trench coat, durable wool trousers"
            },
            {
                "role_name": "Primary Field Eyewitness",
                "archetype": "Observant & vigilant local eyewitness holding key testimony",
                "visual_cues": "standing cautiously, observing surrounding setting",
                "attire": "authentic civilian workwear appropriate to setting"
            },
            {
                "role_name": "Administrative Oversight Official",
                "archetype": "Conflicted & guarded institutional authority facing scrutiny",
                "visual_cues": "presenting official compliance binder with stern expression",
                "attire": "formal municipal suit with administrative badge"
            },
            {
                "role_name": "Forensic Evidence Analyst",
                "archetype": "Clinical & objective scientific analyst uncovering empirical evidence",
                "visual_cues": "inspecting sample container with magnifying instrument",
                "attire": "protective field jacket and utility gloves"
            }
        ]

    scenes = []
    sc_counter = 0

    d_lower = archetype.get("director", "").lower()
    if "fincher" in d_lower or "mckay" in d_lower or "noir" in d_lower:
        cam_moves = ["slow_creeping_push_in", "clinical_macro_tight", "surveillance_high_angle", "analytical_tracking"]
    elif "nolan" in d_lower or "chernobyl" in d_lower:
        cam_moves = ["monumental_wide_tableaux", "slow_atmospheric_pan", "lingering_depth_push", "dramatic_low_angle"]
    elif "soderbergh" in d_lower or "clinical" in d_lower:
        cam_moves = ["clinical_forensic_pan", "sealed_macro_push", "cold_tracking_shot", "sterile_wide_establishing"]
    elif "miller" in d_lower or "contract" in d_lower or "moneyball" in d_lower:
        cam_moves = ["observational_mid_push", "high_stakes_confrontation_angle", "forensic_ledger_close", "institutional_tracking"]
    else:
        cam_moves = ["slow_push_in", "atmospheric_tracking", "dramatic_tableaux", "static_tension"]

    for b_idx, beat in enumerate(story_beats):
        b_num = b_idx + 1
        b_name = CANONICAL_BEATS[b_idx] if b_idx < len(CANONICAL_BEATS) else f"Beat {b_num}"
        beat_raw = beat.get("content", "").strip()

        # Multi-lingual CJK detection
        is_cjk = any("\u4e00" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff" or "\uac00" <= char <= "\ud7af" for char in beat_raw[:200])
        if is_cjk:
            raw_sents = re.split(r"(?<=[。！？\n])\s*", beat_raw)
            sentences = [s.strip() for s in raw_sents if len(s.strip()) > 8]
        else:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", beat_raw) if len(s.strip()) > 15]

        if not sentences:
            sentences = [f"Narrative progression for {b_name}."]

        curr_narr = []
        curr_units = 0
        for sent in sentences:
            # Clean any lingering header tokens
            sent = re.sub(r'^(?:={2,}\s*)?(?:#+\s*)?(?:ACT|BEAT)\s*(?:[1-5]|IV|I{1,3}|V)[^\n]*?(?:={2,})?\s*', '', sent, flags=re.IGNORECASE).strip()
            if not sent:
                continue

            if is_cjk:
                sent_units = len(sent)
                cut_threshold = 85
                unit_divisor = 5.5
            else:
                sent_units = len(sent.split())
                cut_threshold = 35
                unit_divisor = 2.4

            # Sentence-Atomic Cut: flush when adding next sentence exceeds threshold or already has 2 sentences
            if curr_narr and (curr_units + sent_units > cut_threshold or len(curr_narr) >= 2):
                sc_text = "".join(curr_narr).strip() if is_cjk else " ".join(curr_narr).strip()
                if not re.search(r"[.!?。！？]$", sc_text):
                    sc_text += ("。" if is_cjk else ".")
                sc_id = f"sc{sc_counter:03d}"
                bg_k = f"{episode_id.lower()}_bg_b{b_num}_loc{sc_counter % 3}"

                char_idx = sc_counter % len(character_ensemble)
                char_obj = character_ensemble[char_idx]
                char_role = char_obj["role_name"]
                char_attire = char_obj["attire"]
                char_state = char_obj["archetype"]
                char_cues = char_obj.get("visual_cues", "standing head-to-toe")
                fg_k = f"{episode_id.lower()}_fg_b{b_num}_char{char_idx}" if sc_counter % 4 != 0 else None
                fg_pos = "right" if sc_counter % 2 == 0 else "left"

                bg_desc = f"Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, wide 16:9 cinematic setting of {b_name}, {dynamic_context['physical_environment']}, {dynamic_context['lighting_mood']}"
                fg_desc = f"Stylized editorial graphic novel digital illustration of full-body {char_role} in {char_attire}, standing head-to-toe, {char_cues}, posture {char_state}, 1:1 aspect ratio, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames" if fg_k else None
                cam_move = cam_moves[sc_counter % len(cam_moves)]
                dur = max(7, min(18, round(curr_units / unit_divisor)))

                scenes.append({
                    "scene_id": sc_id,
                    "beat_index": b_num,
                    "beat_name": b_name,
                    "narration": sc_text,
                    "duration_est_sec": dur,
                    "visual_metaphor": f"Visual metaphor representing {b_name}",
                    "camera": {
                        "movement": cam_move,
                        "tension_level": "high" if sc_counter % 3 != 0 else "medium"
                    },
                    "background": {
                        "reuse_key": bg_k,
                        "visual_description": bg_desc,
                        "safe_zone": f"bottom 20% clear for subtitles, center-{'left' if fg_pos == 'right' else 'right'} negative space"
                    },
                    "foreground": {
                        "reuse_key": fg_k,
                        "character_role": char_role,
                        "psychological_state": char_state,
                        "body_language": f"Standing full-body head-to-toe, {char_cues}",
                        "position": fg_pos,
                        "visual_description": fg_desc
                    } if fg_k else None,
                    "audio_sfx_cue": "low_sub_drone_and_paper_shuffle"
                })
                sc_counter += 1
                curr_narr = []
                curr_units = 0

            curr_narr.append(sent)
            curr_units += sent_units

        if curr_narr:
            sc_text = "".join(curr_narr).strip() if is_cjk else " ".join(curr_narr).strip()
            if not re.search(r"[.!?。！？]$", sc_text):
                sc_text += ("。" if is_cjk else ".")
            sc_id = f"sc{sc_counter:03d}"
            dur = max(7, min(18, round(curr_units / unit_divisor)))
            cam_move = cam_moves[sc_counter % len(cam_moves)]
            bg_k = f"{episode_id.lower()}_bg_b{b_num}_tail"
            bg_desc = f"Non-photorealistic 2D stylized editorial graphic novel background illustration, bold ink linework, cel-shading, wide 16:9 setting of {b_name}, {dynamic_context['physical_environment']}"
            scenes.append({
                "scene_id": sc_id,
                "beat_index": b_num,
                "beat_name": b_name,
                "narration": sc_text,
                "duration_est_sec": dur,
                "visual_metaphor": f"Closing tension of {b_name}",
                "camera": {"movement": cam_move, "tension_level": "medium"},
                "background": {
                    "reuse_key": bg_k,
                    "visual_description": bg_desc,
                    "safe_zone": "bottom 20% clear for subtitles"
                },
                "foreground": None,
                "audio_sfx_cue": "clock_ticking"
            })
            sc_counter += 1

    return {
        "episode_id": episode_id,
        "director_archetype": archetype["director"],
        "visual_tone": dynamic_context["physical_environment"],
        "color_palette": dynamic_context["color_palette"],
        "dynamic_context": dynamic_context,
        "character_ensemble": character_ensemble,
        "scenes": scenes
    }


def push_director_plan_to_notion(director_plan: dict, episode_id: str):
    """
    Sync director plan scenes to Notion Director Plan DB (5b201989-2400-8295-be81-81c2c0e4e138).
    Uses 1 EP = 1 Subpage + Child Scene DB model, setting Status to 'Compiled' and syncing all scenes.
    """
    notion_token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
    if not notion_token:
        logger.warning("[B3 Notion] No NOTION_TOKEN found, skipping Notion sync.")
        return

    try:
        import scripts.ag_notion_bridge as bridge
        scenes = director_plan.get("scenes", [])
        logger.info(f"[B3 Notion] Resolving Director Plan subpage for {episode_id}...")
        resolved = bridge.resolve_episode_director_db(episode_id, task_id=episode_id, create_if_missing=True)
        if not isinstance(resolved, dict) or resolved.get("error"):
            logger.warning(f"[B3 Notion] Could not resolve Director Plan subpage for {episode_id}: {resolved}")
            return

        subpage_id = resolved.get("subpage_id")
        scenes_db_id = resolved.get("db_id")

        if subpage_id:
            bridge.update_page_properties(subpage_id, {"Status": {"status": {"name": "Compiled"}}})
            logger.info(f"[B3 Notion] Set Director Plan [{episode_id}] status to 'Compiled' (subpage={subpage_id})")

        if not scenes_db_id:
            logger.warning(f"[B3 Notion] No child Scenes DB found for {episode_id}")
            return

        # Query existing scenes to avoid duplicate rows
        existing_scenes = {}
        try:
            q_res = bridge.query_db(scenes_db_id)
            for r in q_res.get("results", []):
                props = r.get("properties", {})
                name_list = props.get("Name", {}).get("title", [])
                t_name = "".join(t.get("plain_text", "") for t in name_list).strip()
                if t_name:
                    existing_scenes[t_name] = r.get("id")
        except Exception as q_err:
            logger.warning(f"[B3 Notion] Notice querying existing scenes in {scenes_db_id}: {q_err}")

        logger.info(f"[B3 Notion] Syncing {len(scenes)} scenes to Child DB ({scenes_db_id}). Existing scenes in DB: {len(existing_scenes)}")

        synced_count = 0
        for idx, sc in enumerate(scenes):
            sc_idx = sc.get("scene_index", idx)
            scene_title = f"Scene {sc_idx:03d}"

            # Construct properties conforming strictly to child Scenes DB schema
            props = {
                "Name": {"title": [{"text": {"content": scene_title}}]},
                "Scene Index": {"number": sc_idx},
                "Arc Index": {"number": sc.get("beat_index", 1)},
                "Beat": {"rich_text": [{"text": {"content": str(sc.get("beat") or "")[:2000]}}]},
                "Narration Segment": {"rich_text": [{"text": {"content": str(sc.get("narration_segment") or sc.get("narration") or "")[:2000]}}]},
                "Duration Est (s)": {"number": float(sc.get("duration_est") or sc.get("duration_sec") or 0.0)},
                "Background Prompt": {"rich_text": [{"text": {"content": str(sc.get("bg_prompt") or sc.get("image_prompt") or "")[:2000]}}]},
                "BG Reuse Key": {"rich_text": [{"text": {"content": str(sc.get("bg_reuse_key") or sc.get("background_reuse_key") or "")[:2000]}}]},
                "BG Layout Note": {"rich_text": [{"text": {"content": str(sc.get("visual_metaphor") or "")[:2000]}}]},
                "Foreground Prompt": {"rich_text": [{"text": {"content": str(sc.get("fg_prompt") or sc.get("foreground_prompt") or "")[:2000]}}]},
                "FG Reuse Key": {"rich_text": [{"text": {"content": str(sc.get("fg_reuse_key") or sc.get("foreground_reuse_key") or "")[:2000]}}]},
                "Status": {"status": {"name": "Compiled"}},
                "Episode ID": {"rich_text": [{"text": {"content": episode_id}}]},
                "Task ID": {"rich_text": [{"text": {"content": episode_id}}]}
            }

            # Select mappings
            pos = str(sc.get("foreground_position") or "").lower()
            if "left" in pos:
                props["FG Position"] = {"select": {"name": "Left"}}
            elif "right" in pos:
                props["FG Position"] = {"select": {"name": "Right"}}
            elif "center" in pos:
                props["FG Position"] = {"select": {"name": "Center"}}

            sz = str(sc.get("safe_zone") or "").lower()
            if "top" in sz:
                props["Safe Zone"] = {"select": {"name": "Top third"}}
            elif "right" in sz:
                props["Safe Zone"] = {"select": {"name": "Right third"}}
            else:
                props["Safe Zone"] = {"select": {"name": "Lower third"}}

            fg_sub = str(sc.get("fg_subject_type") or "").upper()
            if "A" in fg_sub or "NAMED" in fg_sub:
                props["FG Subject Type"] = {"select": {"name": "A — Named character"}}
            elif "B" in fg_sub or "SYMBOLIC" in fg_sub:
                props["FG Subject Type"] = {"select": {"name": "B — Symbolic figure"}}

            if scene_title in existing_scenes:
                page_id = existing_scenes[scene_title]
                bridge.update_page_properties(page_id, props)
            else:
                res_create = bridge.create_page(parent_db_id=scenes_db_id, properties=props)
                if isinstance(res_create, dict) and res_create.get("id"):
                    existing_scenes[scene_title] = res_create["id"]

            synced_count += 1

        logger.info(f"[B3 Notion] ✅ Pushed {synced_count}/{len(scenes)} scenes into Child DB {scenes_db_id} for {episode_id}")
    except Exception as e:
        logger.warning(f"[B3 Notion] Notion sync encountered notice: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="B3 Hollywood Art Director & Universal Scene Breakdown Engine")
    parser.add_argument("episode_id", help="Episode ID (e.g. <MARKET>_EP<0000>_<topic_slug>)")
    parser.add_argument("--skip-notion", action="store_true", help="Skip syncing to Notion")
    args = parser.parse_args()

    plan = generate_director_plan(args.episode_id, skip_notion=args.skip_notion)
    print(f"✅ Successfully generated Director Plan for {args.episode_id}: {plan['total_scenes']} scenes.")


if __name__ == "__main__":
    main()
