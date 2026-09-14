#!/usr/bin/env python3
"""skill_loader.py — Dynamic Notion SoT Multi-Hub Recursive Loader.

Loads editorial, structural, and visual rules dynamically from Notion Single Source of Truth:
- Central Skill AI: ac901989-2400-827e-bda2-8175dabdcf13 (Rules 113–121)
- Content Engine Hub: 9bb01989-2400-82c0-9ed4-01f19c7ee23f (5-Act narrative, pacing, curiosity loops)
- Media Production Hub: 69e01989-2400-82fe-9352-81d562f63a8b (2-Layer composition, visual art direction)

Features:
- Recursive block and child page traversal via ag_notion_bridge
- 3600s in-memory TTL caching per hub
- Persistent local snapshot fallback (/root/video_factory/data/notion_audit/skills_snapshot.json)
- Dedicated getters: get_central_skills(), get_content_engine_rules(), get_media_production_rules(), get_all_skills_bundle()
- Backward-compatible get_skill_rules() alias
"""
import os
import sys
import logging
import time
import json
from pathlib import Path

# Add scripts dir to path for ag_notion_bridge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "scripts"))
import ag_notion_bridge as bridge

logger = logging.getLogger(__name__)

# Canonical Hub IDs
CENTRAL_SKILL_PAGE_ID = "ac901989-2400-827e-bda2-8175dabdcf13"
CONTENT_ENGINE_PAGE_ID = "9bb01989-2400-82c0-9ed4-01f19c7ee23f"
MEDIA_PRODUCTION_PAGE_ID = "69e01989-2400-82fe-9352-81d562f63a8b"
SELF_LEARNING_PAGE_ID = "83cbd0d0-03af-4a60-a765-682a3c5a0a5d"

# Backward compatibility alias
SKILL_AI_PAGE_ID = CENTRAL_SKILL_PAGE_ID

ROOT_DIR = Path(os.getenv("VF_ROOT_DIR", Path(__file__).resolve().parent.parent.parent))
SNAPSHOT_FILE = Path(os.getenv("VF_SKILLS_SNAPSHOT", ROOT_DIR / "data" / "notion_audit" / "skills_snapshot.json"))
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL for Notion skills

# In-memory multi-hub cache state
_cache = {
    "central": {"data": None, "expiration": 0},
    "content_engine": {"data": None, "expiration": 0},
    "media_production": {"data": None, "expiration": 0},
    "bundle": {"data": None, "expiration": 0},
    "hits": 0,
    "misses": 0
}


def _parse_block_markdown(block: dict) -> str:
    """Parse a single Notion block into clean markdown text."""
    btype = block.get("type", "")
    texts = block.get(btype, {}).get("rich_text", [])
    text = "".join(t.get("plain_text", "") for t in texts).strip()
    
    if btype == "heading_1":
        return f"\n# {text}\n"
    elif btype == "heading_2":
        return f"\n## {text}\n"
    elif btype == "heading_3":
        return f"\n### {text}\n"
    elif btype == "bulleted_list_item":
        return f"  • {text}" if text else ""
    elif btype == "numbered_list_item":
        return f"  1. {text}" if text else ""
    elif btype == "callout":
        return f"> [CALLOUT] {text}" if text else ""
    elif btype == "quote":
        return f"> {text}" if text else ""
    elif btype == "code":
        lang = block.get("code", {}).get("language", "")
        return f"\n```{lang}\n{text}\n```\n" if text else ""
    elif btype == "paragraph":
        return text
    elif btype == "divider":
        return "---"
    return ""


def _fetch_blocks_recursive(block_or_page_id: str, depth: int = 0, max_depth: int = 2, visited: set = None) -> list:
    """Recursively fetch blocks and child pages from Notion."""
    if visited is None:
        visited = set()
    clean_id = block_or_page_id.replace("-", "")
    if clean_id in visited or depth > max_depth:
        return []
    visited.add(clean_id)

    try:
        res = bridge.get_blocks(block_or_page_id, page_size=100)
    except Exception as e:
        logger.warning(f"[skill_loader] Exception fetching blocks for {block_or_page_id}: {e}")
        return []

    if not isinstance(res, dict) or res.get("error"):
        logger.warning(f"[skill_loader] Notion error for {block_or_page_id}: {res.get('message') if isinstance(res, dict) else res}")
        return []

    blocks = res.get("results", [])
    lines = []

    for block in blocks:
        btype = block.get("type")
        if btype == "child_page":
            cp_id = block.get("id")
            title = block.get("child_page", {}).get("title", "Sub-Page")
            lines.append(f"\n### Sub-Page: {title}\n")
            if depth < max_depth and cp_id:
                sub_lines = _fetch_blocks_recursive(cp_id, depth=depth + 1, max_depth=max_depth, visited=visited)
                lines.extend(sub_lines)
        elif btype == "child_database":
            continue
        else:
            txt = _parse_block_markdown(block)
            if txt:
                lines.append(txt)
            if block.get("has_children") and depth < max_depth:
                b_id = block.get("id")
                if b_id:
                    child_lines = _fetch_blocks_recursive(b_id, depth=depth + 1, max_depth=max_depth, visited=visited)
                    lines.extend(child_lines)

    return lines


def _load_snapshot() -> dict:
    """Load local snapshot file if present."""
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading snapshot {SNAPSHOT_FILE}: {e}")
    return {}


def _save_snapshot(hub_key: str, content: str):
    """Save content to the local snapshot file for offline fallback."""
    try:
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = _load_snapshot()
        data[hub_key] = content
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        SNAPSHOT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug(f"[skill_loader] Saved offline snapshot for {hub_key}")
    except Exception as e:
        logger.warning(f"[skill_loader] Failed saving snapshot: {e}")


DOCUDRAMA_5BEAT_PACING_X10 = """
## 10X 5-BEAT INVESTIGATIVE DOCUDRAMA ARCHITECTURE (QUY CHUẨN ĐẶC TẢ NHỊP KỊCH BẢN X10)
Genre: High-Stakes Non-Fiction Investigative Docudrama (Johnny Harris x Margin Call x Chernobyl Pacing).
Target: 1,800 - 2,200 words across 5 structured Acts (~360-440 words / Act). Total runtime: 12-15 minutes.

### 🥊 BEAT 1 / ACT I (0:00 - 3:00): THE IMPOSSIBLE CONTRADICTION & COLD STRIKE
• Primary Objective: Capture cold mobile traffic within 5-10s (Rule 444) and directly satisfy viewer search intent (Rule 130).
• Micro-Pacing Breakdown:
  1.1 Cold Strike (0:00 - 0:20): Sentence 1 MUST lead with a verified real-world event (Level 1 Primary Catalyst) and an exact quantitative figure (%, $, or metric) within 60 words. STRICTLY FORBIDDEN: Opening with 'Imagine...', 'In today's world...', or philosophical throat-clearing.
  1.2 Sensory/Structural Paradox (0:20 - 1:00): Clash two irreconcilable realities: the visible official surface (e.g. operational dashboards show normal activity, corporate headquarters announce record profits) vs. the invisible systemic failure (liquidity evaporating, legal safeguards suspended, contracts freezing).
  1.3 Ticking Clock & Human Stakes (1:00 - 2:00): Establish the ticking deadline and asymmetric exposure. Who is hemorrhaging capital or facing catastrophe right now?
  1.4 The Core Curiosity Lock & Micro-Cliffhanger 1 (2:00 - 3:00): Formulate the central investigative enigma: 'How did this catastrophe unfold in broad daylight under the watch of elite regulators/institutions?' End Act I on an alarming initial anomaly.
• Mandatory Keywords & Signals: 'collapse', 'shock', 'disappear', 'first', 'only', and at least 2 explicit curiosity questions ('?').

### 🎭 BEAT 2 / ACT II (3:00 - 6:00): THE FALSE NARRATIVE & MEDIA RED HERRING
• Primary Objective: Dismantle the superficial official narrative and expose competitor blindspots.
• Micro-Pacing Breakdown:
  2.1 The Comforting Consensus (3:00 - 4:00): Reconstruct the mainstream media headlines and PR statements that lulled the public into a false sense of security.
  2.2 The Peripheral Fracture (4:00 - 5:00): Examine peripheral data that competitors ignored: quiet revisions in fine print, anomalous ledger transfers, off-balance-sheet notes, or unusual trading spikes.
  2.3 The Red Herring Unmasked & Micro-Cliffhanger 2 (5:00 - 6:00): Prove forensically why the popular scapegoat is wrong or merely a symptom. If the official story is a myth, what hidden machine is actually pulling the strings?
• Mandatory Keywords & Signals: 'official story', 'narrative', 'headline', 'myth', 'red herring', citing official reports/statements.

### 📂 BEAT 3 / ACT III (6:00 - 9:30): THE SYSTEMIC BLINDSPOT & PAPER TRAIL
• Primary Objective: Deep-dive into technical evidence, contract clauses, internal memos, and regulatory choke points.
• Micro-Pacing Breakdown:
  3.1 Entering the Choke Point (6:00 - 7:00): Walk the viewer into the operational cockpit: specific legal sub-clauses (e.g. ISDA master terms, material adverse change clauses, margin covenants), risk algorithms, or board decisions.
  3.2 The Asymmetric Trap (7:00 - 8:00): Reveal how self-reinforcing mechanisms forced rational actors into collective disaster—not out of malice, but because automated rules left them no other choice.
  3.3 Pattern Interrupt Breaker (8:00 - 8:30): Insert a punchy, staccato sentence of 2 to 6 words maximum (e.g. 'The paper trail vanished.', 'Then came the audit.', 'No one was looking.') to freeze the narrative tempo before dropping the fatal leak.
  3.4 The Fatal Explanatory Vacuum & Micro-Cliffhanger 3 (8:30 - 9:30): Unearth the ignored early warning memo or confidential audit that predicted the exact failure months in advance.
• Mandatory Keywords & Signals: 'paper trail', 'blindspot', 'loophole', 'leak', 'memo', 'forensic', plus exactly 1 pattern-interrupt short sentence (2-6 words).

### ⚡ BEAT 4 / ACT IV (9:30 - 12:30): THE SMOKING GUN & ASYMMETRIC CLIMAX
• Primary Objective: Deliver the irrefutable structural climax and unmask the true beneficiaries and systemic breaking point.
• Micro-Pacing Breakdown:
  4.1 The Dam Breaks (9:30 - 10:30): The inevitable transmission from Level 1 catalyst to Level 2 institutional catastrophe completes: borrowing spreads spike 400%, liquidity evaporates, or default triggers fire simultaneously.
  4.2 The Smoking Gun Unmasked (10:30 - 11:30): Present the definitive document or data proof. Who anticipated the collapse? Who extracted asymmetric profit while the public or ordinary participants absorbed the loss?
  4.3 The Climax & Cascade (11:30 - 12:30): The dominoes finish falling. The regulatory or market verdict is rendered. The trap has irrevocably snapped shut.
• Mandatory Keywords & Signals: 'smoking gun', 'culprit', 'exposed', 'unmasked', 'profited', closing loops with 'that is why', 'the answer', 'which is how'.

### 🪞 BEAT 5 / ACT V (12:30 - 15:00): THE UNCOMFORTABLE MODERN MIRROR & LIVING WARNING
• Primary Objective: Deliver closure (>=80% curiosity loops answered) and hold a chilling mirror up to the contemporary world.
• Micro-Pacing Breakdown:
  5.1 The Systemic Verdict (12:30 - 13:30): Synthesize the entire causal chain into one unforgettable insight. Resolve remaining curiosity loops from Acts I-IV.
  5.2 The Living Contemporary Precedent (13:30 - 14:15): Reveal that this vulnerability did not end with this episode. Show the exact same mechanism operating today under a different corporate, financial, or geopolitical guise.
  5.3 The Final Living Warning (14:15 - 15:00): End with an unsettling, thought-provoking investigative takeaway that respects viewer intelligence. STRICTLY ZERO preachy moralizing or generic cliches ('in conclusion', 'time will tell', 'beacon of hope').
• Mandatory Keywords & Signals: 'mirror', 'warning', 'modern', 'today', 'lesson', 'verdict', loop closure >= 80%.
"""

AUTHENTIC_5_ACT_PACING_RULES = DOCUDRAMA_5BEAT_PACING_X10

TWO_LAYER_VISUAL_RULES = """

## 2-Layer Visual Composition & Remotion Architecture (Rule 116 & Rule 435)
• Layer 1 (Background 16:9 2K DCI 2560x1440): Wide-angle cinematic documentary environment, unobstructed bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay.
• Layer 2 (Foreground 1:1 2048x2048): Stylized editorial graphic novel digital illustration, full-body head-to-shoes standing portrait, on solid #FF00FF pure magenta chroma key.
• Remotion Safe-Zone Subtitle Container: Sole on-screen subtitle mechanism with millisecond karaoke sync. Redundant FFmpeg burning bypassed."""


def _fallback_for_hub(hub_key: str) -> str:
    """Provide a reliable fallback if Notion API is unavailable."""
    snapshot = _load_snapshot()
    if snapshot.get(hub_key):
        content = snapshot[hub_key]
        if hub_key == "content_engine" and ("5-Act" not in content and "5-act" not in content.lower()):
            content = f"{content}{AUTHENTIC_5_ACT_PACING_RULES}".strip()
        elif hub_key == "media_production" and ("Layer 1" not in content and "2-Layer" not in content):
            content = f"{content}{TWO_LAYER_VISUAL_RULES}".strip()
        logger.info(f"[skill_loader] Using offline snapshot for {hub_key}")
        return content

    if hub_key == "central" and LEGACY_SNAPSHOT_FILE.exists():
        try:
            logger.info(f"[skill_loader] Using legacy markdown snapshot for central skills")
            return LEGACY_SNAPSHOT_FILE.read_text(encoding="utf-8")
        except Exception:
            pass

    # Built-in authoritative fallbacks aligned with Notion SoT
    if hub_key == "content_engine":
        return (
            """# Content Engine Hub (Fallback Snapshot)
## 5 HARD Rules
1. Brand voice before content — Never draft an article or script without first defining tone and audience.
2. Fact-check before publish — Any factual claim (statistics, dates, names) MUST be verified.
3. No AI disclosure bypass — Comply strictly with synthetic media disclosure mandates.
4. No publish without quality gate — Story gate score must meet threshold (score >= 8/10).
5. Platform spec compliance — Length, tags, character limits strictly enforced.
"""
            + AUTHENTIC_5_ACT_PACING_RULES.strip()
        )
    elif hub_key == "media_production":
        return (
            """# Media Production Hub (Fallback Snapshot)
## 5 HARD Rules
1. Aspect ratio lock — 16:9 for documentary master (2560x1440 or 1920x1080).
2. Script before render — Narration copy must exist and pass quality gates before rendering.
3. Offline render only — Render locally on CPU/GPU, probe integrity before upload.
4. No hardcoded configuration — All runtime settings loaded via environment variables.
5. Version every output — Version all artifacts (final_169.mp4, remotion_props.json).
"""
            + TWO_LAYER_VISUAL_RULES.strip()
        )
    return ""


def get_central_skills(force_refresh: bool = False) -> str:
    """Get Rules 113-121 and Core Editorial Principles from Central Skill AI page.
    
    Target: CENTRAL_SKILL_PAGE_ID ('ac901989-2400-827e-bda2-8175dabdcf13')
    """
    global _cache
    now = time.time()
    entry = _cache["central"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    logger.info("[skill_loader] Fetching Central Skills from Notion...")

    try:
        lines = _fetch_blocks_recursive(CENTRAL_SKILL_PAGE_ID, depth=0, max_depth=1)
        content = "\n".join(lines).strip()
        if content:
            # Ensure Rule 120 is explicitly referenced if not already present in raw Notion blocks
            if "Rule 120" not in content:
                rule_120_text = (
                    "\n\n### Rule 120 — Prompt Engineering Isolation & Subtitle Karaoke Sync (23/08/2026)\n"
                    "• Foregrounds strictly generated on #FF00FF pure magenta chroma key background.\n"
                    "• Remotion safe-zone box with word-level karaoke sync; eliminate redundant FFmpeg subtitle burning.\n"
                    "• Complete removal of legacy VPS visual engine; browser-driven generation with 3-5s spacing.\n"
                )
                content += rule_120_text

            entry["data"] = content
            entry["expiration"] = now + CACHE_TTL_SECONDS
            _save_snapshot("central", content)
            logger.info(f"[skill_loader] Loaded {len(content)} chars from Central Skill AI")
            return content
    except Exception as e:
        logger.warning(f"[skill_loader] Exception during central skill fetch: {e}")

    fallback = _fallback_for_hub("central")
    entry["data"] = fallback
    entry["expiration"] = now + 300  # Shorter TTL for fallback
    return fallback


def get_content_engine_rules(force_refresh: bool = False) -> str:
    """Get 5-Act narrative structure, pacing, and loop discipline from Content Engine Hub.
    
    Target: CONTENT_ENGINE_PAGE_ID ('9bb01989-2400-82c0-9ed4-01f19c7ee23f')
    """
    global _cache
    now = time.time()
    entry = _cache["content_engine"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    logger.info("[skill_loader] Fetching Content Engine Hub from Notion...")

    content = ""
    try:
        lines = _fetch_blocks_recursive(CONTENT_ENGINE_PAGE_ID, depth=0, max_depth=1)
        content = "\n".join(lines).strip()
        if content:
            logger.info(f"[skill_loader] Loaded {len(content)} chars from Content Engine Hub")
    except Exception as e:
        logger.warning(f"[skill_loader] Exception during Content Engine fetch: {e}")

    if not content:
        content = _fallback_for_hub("content_engine")

    # ALWAYS ensure authentic 5-Act narrative pacing rules are merged with raw Notion text
    # so B2 Story Engine never loses the 5-Act structure
    if "5-Act" not in content and "5-act" not in content.lower():
        content = f"{content}{AUTHENTIC_5_ACT_PACING_RULES}".strip()
    elif "curiosity loop" not in content.lower() or "first 60 words" not in content.lower():
        content = f"{content}{AUTHENTIC_5_ACT_PACING_RULES}".strip()

    entry["data"] = content
    entry["expiration"] = now + CACHE_TTL_SECONDS
    _save_snapshot("content_engine", content)
    return content


def get_media_production_rules(force_refresh: bool = False) -> str:
    """Get 2-Layer composition, visual art direction, and chroma keying rules from Media Production Hub.
    
    Target: MEDIA_PRODUCTION_PAGE_ID ('69e01989-2400-82fe-9352-81d562f63a8b')
    """
    global _cache
    now = time.time()
    entry = _cache["media_production"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    logger.info("[skill_loader] Fetching Media Production Hub from Notion...")

    content = ""
    try:
        lines = _fetch_blocks_recursive(MEDIA_PRODUCTION_PAGE_ID, depth=0, max_depth=1)
        content = "\n".join(lines).strip()
        if content:
            logger.info(f"[skill_loader] Loaded {len(content)} chars from Media Production Hub")
    except Exception as e:
        logger.warning(f"[skill_loader] Exception during Media Production fetch: {e}")

    if not content:
        content = _fallback_for_hub("media_production")

    # Ensure 2-Layer composition rules are merged with raw Notion text
    if "Layer 1" not in content and "2-Layer" not in content:
        content = f"{content}{TWO_LAYER_VISUAL_RULES}".strip()

    entry["data"] = content
    entry["expiration"] = now + CACHE_TTL_SECONDS
    _save_snapshot("media_production", content)
    return content


def get_all_skills_bundle(force_refresh: bool = False) -> str:
    """Assembles a unified markdown bundle containing Central Skills, Content Engine, and Media Production rules."""
    global _cache
    now = time.time()
    entry = _cache["bundle"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    central = get_central_skills(force_refresh=force_refresh)
    content_engine = get_content_engine_rules(force_refresh=force_refresh)
    media_production = get_media_production_rules(force_refresh=force_refresh)

    bundle = (
        "# VIDEO FACTORY SINGLE SOURCE OF TRUTH (NOTION SOT SKILL BUNDLE)\n\n"
        "## I. CENTRAL SKILL AI (RULES 113-121)\n"
        f"{central}\n\n"
        "## II. CONTENT ENGINE HUB (5-ACT ARCHITECTURE & NARRATIVE DISCIPLINE)\n"
        f"{content_engine}\n\n"
        "## III. MEDIA PRODUCTION HUB (2-LAYER VISUAL DIRECTION & REMOTION)\n"
        f"{media_production}\n"
    )

    entry["data"] = bundle
    entry["expiration"] = now + CACHE_TTL_SECONDS
    return bundle


def get_b1_strategic_rules() -> str:
    """Concise strategic rules (~1,200 chars) for B1 Topic & Niche Reasoning.
    Distills Rule 1-4 Causal Mechanisms, Rule 444 An Ong Hook, Rule 118 Zero-Mock,
    and Rule 445 5-Beat Docudrama Architecture without prompt bloat.
    """
    return (
        "CORE STRATEGIC EDITORIAL PRINCIPLES (RULE 118, 444, 445):\n"
        "1. RULE 118 ZERO-MOCK: Strictly ground the topic and angle in real search signals or YouTube benchmarks. Never invent speculative or synthetic themes.\n"
        "2. CAUSAL MECHANISM MANDATE: Every approved angle must expose an institutional, financial, or systemic mechanism (how the system broke, who profited, why oversight failed).\n"
        "3. RULE 444 AN ONG HOOK: Formulate a paradoxical, curiosity-inducing opening hook that subverts conventional wisdom.\n"
        "4. RULE 445 5-BEAT DOCUDRAMA ARCHITECTURE:\n"
        "   - Beat 1: Paradox & Shock Opening (0-60s)\n"
        "   - Beat 2: The Red Herring / False Narrative & Early Warning Signs\n"
        "   - Beat 3: The Fatal Explanatory Vacuum / Institutional Crack (Competitor Gap)\n"
        "   - Beat 4: The Smoking Gun / Systemic Exposure & Climax\n"
        "   - Beat 5: The Living Warning & Enduring Consequence\n"
        "5. 7 CANONICAL INVESTIGATIVE PILLARS:\n"
        "   - Pillar 1: Rise and Fall of Corporate Giants\n"
        "   - Pillar 2: Systemic Financial & Market Crashes\n"
        "   - Pillar 3: True Crime Non-Graphic & Forensic Fraud\n"
        "   - Pillar 4: Psychology & Behavioral Manipulation\n"
        "   - Pillar 5: Technological & Geopolitical Battles\n"
        "   - Pillar 6: Institutional & Regulatory Chokepoints\n"
        "   - Pillar 7: Hidden Asymmetric Fortunes & Wealth Transfers\n"
        "6. NATIVE GROUND TRUTH: All search keywords must be in the native language of the target market (JP/KR/EN)."
    )




def get_b35_strategic_rules() -> str:
    """Concise strategic visual production rules (~1,800 chars) for B3.5 Prompt Forge.
    Distills Rule 116 (Two-Layer Composition), Rule 120 (Chroma Key Spec),
    Rule 122 (Visual Audit & Market Ethnicity Conformance), Rule 128 (Zero Semantic Bias & Era Authenticity),
    Rule 435 (Graphic Novel Style), Rule 446 (English Production Bridge), and Rule 114 (Hero Thumbnails).
    """
    return (
        "=== NOTION SOT CONCISE VISUAL PRODUCTION RULES (RULES 114, 116, 120, 122, 128, 435, 446) ===\n"
        "1. TWO-LAYER COMPOSITION (Rule 116):\n"
        "   - Layer 1 Background (16:9 widescreen 2560x1440): Cinematic documentary environment. Period architecture, dramatic lighting. No foreground humans. Bottom 20% safe-zone clear for subtitles, center-right negative space for character overlay.\n"
        "   - Layer 2 Foreground (1:1 2048x2048): Stylized Editorial Graphic Novel Digital Illustration. Cel-shading, bold ink linework. Exactly one full-body character head-to-toe in authentic attire. Positioned Right or Left.\n"
        "2. STRICT CHROMA KEY SPEC (Rule 120):\n"
        "   - Foreground MUST be isolated on pure flat solid #FF00FF magenta background for chroma extraction.\n"
        "   - No white borders, no halos, no gradients, no scenery in Layer 2.\n"
        "3. GRAPHIC NOVEL ART STYLE (Rule 435):\n"
        "   - Non-photorealistic stylized 2D graphic novel illustration. Cel-shading ink. NO photorealism, NO 3D CGI skin.\n"
        "4. CINEMATIC CONTINUITY & ERA AUTHENTICITY (Rule 128):\n"
        "   - Harmonize lighting angle, color palette, atmosphere between paired Layer 1 & 2 assets.\n"
        "   - Zero domain bleed: never inject modern tech into historical scenes or rural relics into corporate scenes.\n"
        "5. INDIGENOUS CULTURAL PROPS & ANTI-ENGLISH BLEED (Rule 122 & Rule 128):\n"
        "   - Every scene MUST include tangible local cultural artifacts (JP: hanko cinnabar red seals, King File spine tabs, sha-sho lapel pins; KR: official round seals/stamps, sawonjeung ID lanyards, Taegeuk/court crests; VN: red circular stamps, Quoc huy crests, mahogany lacquer).\n"
        "   - STRICTLY FORBIDDEN: English/Latin text or English words on whiteboards, walls, signs, or folders for Asian markets (JP/KR/VN).\n"
        "6. ENGLISH PRODUCTION BRIDGE (Rule 446): All visual prompt outputs must be in clear descriptive English.\n"
        "7. MARKET ETHNICITY & REGIONAL ARCHITECTURE CONFORMANCE (Rule 122 & Rule 128):\n"
        "   - Foreground characters MUST feature authentic ethnic phenotype (bone structure, eye shape, styling, attire), dynamic high-stakes body posture (leaning forward, decisive pointing, clenched fist), intense facial micro-expressions (furrowed brow, sharp intense glare, zero dead eyes/blank stare), and active interaction with tangible indigenous props. ZERO Caucasian/Western bias.\n"
        "   - Backgrounds MUST feature authentic local corporate/urban architecture matching target market. ZERO generic American cubicles or Western skyline mismatch."
    )


def get_visual_strategic_rules() -> str:
    """Alias for get_b35_strategic_rules."""
    return get_b35_strategic_rules()


def get_b3_strategic_rules() -> str:
    """Concise strategic art direction rules (~2,000 chars) for B3 Director Planner.
    Distills Rule 116 (Two-Layer Architecture), Rule 120 (Chroma Key & Safe Zone),
    Rule 128 (Universal Dynamic Context & Character Ensemble), Rule 130 (Factual Causal Integrity
    & Visual Catalyst Anchoring), Rule 131 (10X 5-Beat Storyboard Pacing), Rule 445 (5-Beat Structure),
    Sentence-Atomic Pacing (Subtitle Overflow Prevention), and Archetype-Specific Grammar.
    """
    b3_template_file = ROOT_DIR / "config" / "prompts" / "b3_director_prompt.md"
    if b3_template_file.exists():
        try:
            return b3_template_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading {b3_template_file}: {e}")

    return (
        "=== NOTION SOT HOLLYWOOD ART DIRECTION & SCENE BREAKDOWN RULES (RULES 116, 120, 128, 130, 131, 445, 446) ===\n"
        "1. ROLE: You are the Hollywood Master Visual Director & Lead Cinematographer. Your decisions dictate video pacing across 130 to 160 dynamic scenes (~6-7s per scene) for an 18-20 minute docudrama.\n"
        "2. FINCHER-STYLE RAPID-FIRE HOOK (0-60s / ACT I, SCENES 1-15):\n"
        "   - The first 60 seconds MUST be broken down into 12 to 15 rapid-fire scenes (15-25 words each, ~3.5s - 5.0s per scene) across 3 phases: The Asymmetric Paradox (0-15s), The Hard Metric Shock (15-35s), The Investigative Contract (35-60s).\n"
        "3. CORE INVESTIGATIVE NARRATIVE PACING (ACTS II - V, SCENES 16-160):\n"
        "   - Narration: strictly 25-35 words per scene (~6.0s - 7.5s duration), 1-2 complete grammatical sentences ending strictly with '.', '!', '?'. NEVER cut mid-sentence.\n"
        "   - Subtitle line budget: strictly fit within 2 lines on 1920x1080 display (~35-40 characters/line).\n"
        "   - Duration Estimation: Hook (Scenes 1-15): max(3, min(6, round(word_count / 3.0))); Core (Scenes 16+): max(5, min(9, round(word_count / 2.5))).\n"
        "4. 6 CANONICAL CINEMATIC CAMERA MOVEMENTS:\n"
        "   - slow_push_in, snap_zoom, cinematic_pan, macro_tilt, slow_pull_out, handheld_shake.\n"
        "5. LOCATION CONTINUITY CLUSTERED BACKGROUNDS (Rule 131):\n"
        "   - 3-4 solid location anchors per Beat (~15-20 total background clusters). Assign 'bg_cluster_id' (1..20) per scene.\n"
        "6. FORENSIC OVERLAY DIRECTIVES:\n"
        "   - Tag evidentiary scenes with 'forensic_overlay': 'redacted_doc', 'radar_map', 'financial_chart', 'surveillance_crt', or null.\n"
        "7. TWO-LAYER COMPOSITION & SUBTITLE SAFE-ZONE INTEGRITY (Rule 116):\n"
        "   - Layer 1 Background (16:9 2560x1440): Bottom 20% clear for subtitles.\n"
        "   - Layer 2 Foreground (1:1 2048x2048 #FF00FF): Position strictly 'Right' or 'Left' (Rule of Thirds). NEVER place full-body characters at 'Center'.\n"
        "8. PRODUCTION BRIDGE (Rule 446): All prompt descriptions and visual hints must be in descriptive English."
    )
def get_b10_seo_rules() -> str:
    """Concise strategic rules (~1,200 chars) for B10 YouTube Packaging & SEO Metadata.
    Distills Rule 118 (Zero-Mock), Rule 444 (An Ong Curiosity Hook in Titles),
    Breakout Query Search Injections, A/B Testing Title Specs, YouTube 2026
    Hashtags and Tags algorithms without prompt bloat.
    """
    return (
        "=== NOTION SOT CONCISE B10 YOUTUBE PACKAGING & SEO RULES (RULES 118, 444, 446) ===\n"
        "1. RULE 118 ZERO-MOCK & FACTUAL ANCHOR: All titles, descriptions, and tags must be strictly grounded in the real episode narrative and search breakout data. Never invent fictitious events, deceptive clickbait, or hallucinated characters.\n"
        "2. TITLE DYNAMICS & A/B TESTING (Rule 444 An Ong Hook):\n"
        "   - Title A (Curiosity / Mystery Hook): High CTR, paradox-driven, emotion-inducing under 70 characters.\n"
        "   - Title B (Search Intent / High Virality): SEO-optimized, authoritative, incorporating primary keywords under 70 characters.\n"
        "   - Title C (Casual / Provocative Question): Question-driven angle that triggers immediate curiosity.\n"
        "3. BREAKOUT QUERY INJECTION (Native-First):\n"
        "   - Naturally weave Google Trends breakout queries into the top 3 lines of the description and tags for maximum search volume discovery.\n"
        "4. DESCRIPTION & CHAPTERS SPEC:\n"
        "   - 3-second hook restated in opening lines followed by deep causal summary.\n"
        "   - Timestamps/Chapters clearly formatted (e.g. 00:00 [Chapter Title]). Never omit 00:00.\n"
        "5. TAGS & HASHTAGS BUDGETING:\n"
        "   - Tags: Comma-separated, priority to breakout terms, capped at <= 500 chars and <= 7 core tags.\n"
        "   - Hashtags: CamelCase slugs (e.g. #ByzantineEmpire), capped at strictly 3 to 5 hashtags."
    )


def get_skill_rules(force_refresh: bool = False) -> str:
    """Universal backward-compatible strategic rules (~1,500 chars).
    Returns core foundational guardrails (Rules 118, 126, 128, 444, 446)
    to prevent massive prompt pollution (100k tokens) across legacy callers.
    """
    return (
        "=== NOTION SOT CORE STRATEGIC GUARDRAILS (RULES 118, 126, 128, 444, 446) ===\n"
        "1. RULE 118 ZERO-MOCK DATA: Strictly use empirical, ground-truth factual data. Zero speculation, synthetic metrics, or hallucinated details.\n"
        "2. RULE 128 UNIVERSAL DYNAMIC CONTEXT (Zero Semantic Bias): Strictly derive era, environment, and characters from the specific narrative. Zero domain bleed.\n"
        "3. RULE 444 AN ONG CURIOSITY PROTOCOL: Frame narratives and hooks around causal paradoxes, hidden mechanisms, and systemic truths.\n"
        "4. RULE 446 ENGLISH PRODUCTION BRIDGE: Internal prompts, art direction, and scene parameters must be in clear English; user-facing metadata in target market native language.\n"
        "5. PLATFORM CONFORMANCE: Adhere strictly to YouTube editorial, algorithmic CTR/AVD retention, and visual quality requirements."
    )


def get_cache_info() -> dict:
    """Get cache statistics for monitoring."""
    global _cache
    now = time.time()

    hubs_info = {}
    for key in ("central", "content_engine", "media_production", "bundle"):
        c = _cache[key]
        has_data = c["data"] is not None
        rem = max(0, int(c["expiration"] - now)) if has_data else 0
        hubs_info[key] = {
            "cached": has_data,
            "char_count": len(c["data"]) if has_data else 0,
            "remaining_seconds": rem
        }

    return {
        "hits": _cache["hits"],
        "misses": _cache["misses"],
        "ttl_seconds": CACHE_TTL_SECONDS,
        "hubs": hubs_info
    }




def get_b11_self_learning_rules(force_refresh: bool = False) -> str:
    """Fetch actionable post-mortem lessons from Notion B11 Self-Learning Loop (83cbd0d0-03af-4a60-a765-682a3c5a0a5d)."""
    global _cache
    now = time.time()
    if not force_refresh and _cache.get("self_learning", {}).get("data") and now < _cache.get("self_learning", {}).get("expiration", 0):
        return _cache["self_learning"]["data"]

    try:
        lines = _fetch_blocks_recursive(SELF_LEARNING_PAGE_ID, depth=0, max_depth=1)
        if not lines:
            return ""
        filtered = [l for l in lines if len(l.strip()) > 15]
        text = chr(10).join(filtered[:25]).strip()
        if text:
            _cache["self_learning"] = {"data": text, "expiration": now + CACHE_TTL_SECONDS}
            return text
    except Exception as e:
        logger.warning(f"[skill_loader] Failed to fetch B11 self-learning rules: {e}")
    return ""


def get_b2_editorial_skills(force_refresh: bool = False) -> str:
    """Return high-density, targeted editorial skill prompts for B2 Story Engine.
    Combines 10X 5-Beat Docudrama Micro-Pacing Architecture, Rule 113/114/130 YouTube Viral Mandates,
    and B11 Self-Learning post-mortem feedback dynamically without marketing context clutter.
    """
    b11_lessons = get_b11_self_learning_rules(force_refresh=force_refresh)
    
    b11_section = ""
    if b11_lessons:
        b11_section = (
            "\n\n=== B11 CONTINUOUS SELF-LEARNING LESSONS (LIVE NOTION FEEDBACK) ===\n"
            f"{b11_lessons[:1200]}\n"
        )

    b2_template_file = ROOT_DIR / "config" / "prompts" / "b2_editorial_prompt.md"
    if b2_template_file.exists():
        try:
            base_editorial = b2_template_file.read_text(encoding="utf-8").strip()
            return f"{base_editorial}\n{b11_section}"
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading {b2_template_file}: {e}")

    editorial_prompt = (
        "=== B2 10X EDITORIAL & INVESTIGATIVE CINEMATIC MANDATES ===\n"
        "1. RULE 130: FACTUAL CAUSAL INTEGRITY & SEARCH-INTENT DIRECT PAYOFF:\n"
        "   - Suspense arises from forensic clarity: the collision between a verified real catalyst event and its systemic transmission.\n"
        "   - Strictly distinguish Level 1 Primary Catalyst (direct verified event, dates, actors) from Level 2 Transmission Mechanism (institutional, contractual, regulatory, or financial transmission).\n"
        "   - Act I and Act II must directly address and resolve the viewer's burning search query. ZERO hypotheticals ('Imagine a scenario...'), ZERO clickbait bait-and-switch.\n"
        "   - Ground all statements in verified facts from the Grounding Table; zero speculative gossip.\n\n"
        "2. CINEMATIC HUMAN TENSION INSIDE SYSTEMIC TRAPS:\n"
        "   - Banish dry, passive corporate encyclopedia summaries. Systemic forces are felt through the humans trapped inside them:\n"
        "     the operations director facing an abrupt halt, the margin clerk watching red liquidation warnings, the regulator signing an emergency waiver.\n"
        "   - Visual Staging: Anchor scenes with concrete physical reality (blinking radar consoles, frantic late-night phone logs, leaked internal memos, courtroom transcripts) so Remotion visuals pair seamlessly.\n\n"
        "3. RULE 113 & 114: YOUTUBE RETENTION & CURIOSITY DISCIPLINE:\n"
        "   - Rule 444 Cold Traffic Hook: Mobile viewers decide in 5-10 seconds. Sentence 1 of Act I MUST open with a shock quantitative stake (%, $, or metric).\n"
        "   - Micro-Cliffhangers: Plant an unresolved tension spike every 90-120 seconds throughout the script.\n"
        "   - Continuous Loop Pacing: Plant at least 8 to 10 explicit curiosity questions with '?' across the script (~2 per Act), and frequently close loops using resolving phrases ('that is why', 'which is how', 'the answer', 'in the end').\n"
        "   - Anti-AI Mandate: ZERO banned cliches (delve, testament, tapestry, crucible, beacon, in conclusion, time will tell).\n\n"
        f"{DOCUDRAMA_5BEAT_PACING_X10}\n"
        f"{b11_section}"
    )
    return editorial_prompt


def get_seo_editorial_skills(force_refresh: bool = False) -> str:
    """Return targeted packaging & narrative hook prompt guidelines for B1.5 SEO Package Forge.
    Decoupled from Python code: loads from config/prompts/seo_package_prompt.md or Notion SoT,
    and dynamically integrates B11 Continuous Self-Learning feedback.
    """
    base_prompt = "You are the Packaging & Narrative Hook Director for Video Factory."
    prompt_file = ROOT_DIR / "config" / "prompts" / "seo_package_prompt.md"
    if prompt_file.exists():
        try:
            base_prompt = prompt_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading {prompt_file}: {e}")
            
    b11_lessons = get_b11_self_learning_rules(force_refresh=force_refresh)
    if b11_lessons:
        return f"{base_prompt}\n\n=== B11 CONTINUOUS SELF-LEARNING LESSONS (LIVE NOTION FEEDBACK) ===\n{b11_lessons[:1200]}"
    return base_prompt


def clear_cache():
    """Manually clear all cached rules."""
    global _cache
    for key in ("central", "content_engine", "media_production", "bundle"):
        _cache[key]["data"] = None
        _cache[key]["expiration"] = 0
    logger.info("[skill_loader] All multi-hub caches cleared")


if __name__ == "__main__":
    print("Testing Multi-Hub Skill Loader...")
    print("=" * 60)

    start = time.time()
    c_skills = get_central_skills()
    t1 = time.time() - start
    print(f"✅ Central Skills: {len(c_skills)} chars in {t1:.2f}s")

    start = time.time()
    ce_rules = get_content_engine_rules()
    t2 = time.time() - start
    print(f"✅ Content Engine Rules: {len(ce_rules)} chars in {t2:.2f}s")

    start = time.time()
    mp_rules = get_media_production_rules()
    t3 = time.time() - start
    print(f"✅ Media Production Rules: {len(mp_rules)} chars in {t3:.2f}s")

    start = time.time()
    bundle = get_all_skills_bundle()
    t4 = time.time() - start
    print(f"✅ Full Skills Bundle: {len(bundle)} chars in {t4:.4f}s")

    print("\nCache Info:")
    print(json.dumps(get_cache_info(), indent=2))
