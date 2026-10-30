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
import json
import logging
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.append(_SCRIPTS_DIR)

try:
    from scripts import ag_notion_bridge as bridge
except ImportError:
    import ag_notion_bridge as bridge

logger = logging.getLogger(__name__)

# Canonical Hub IDs
CENTRAL_SKILL_PAGE_ID = "ac901989-2400-827e-bda2-8175dabdcf13"
CONTENT_ENGINE_PAGE_ID = "9bb01989-2400-82c0-9ed4-01f19c7ee23f"
MEDIA_PRODUCTION_PAGE_ID = "69e01989-2400-82fe-9352-81d562f63a8b"
SELF_LEARNING_PAGE_ID = "83cbd0d0-03af-4a60-a765-682a3c5a0a5d"
PROMPT_ENGINE_HUB_ID = "3f801989-2400-81c5-9459-f75fc00f24a1"

PROMPT_ENGINE_PAGE_IDS = {
    "b1_strategy": "3f801989-2400-8157-96f9-cd29c62cd7b1",
    "b2_editorial": "3f801989-2400-818a-adf1-c5f7cc3da7ed",
    "b3_director": "3f801989-2400-81c9-bdb0-c4dc60b43988",
    "b35_visual": "3f801989-2400-81e3-8cc6-c9bb0bb4650c",
    "b10_seo": "3f801989-2400-8172-8655-cc3cd462cbef",
}

# Backward compatibility alias
SKILL_AI_PAGE_ID = CENTRAL_SKILL_PAGE_ID

ROOT_DIR = Path(os.getenv("VF_ROOT_DIR", Path(__file__).resolve().parent.parent.parent))
SNAPSHOT_FILE = Path(os.getenv("VF_SKILLS_SNAPSHOT", ROOT_DIR / "data" / "notion_audit" / "skills_snapshot.json"))
LEGACY_SNAPSHOT_FILE = Path(os.getenv("VF_LEGACY_SKILLS_SNAPSHOT", ROOT_DIR / "data" / "notion_audit" / "central_skills.md"))
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL for Notion skills

PROMPT_LOCAL_FILES = {
    "b1_strategy": ROOT_DIR / "config" / "prompts" / "b1_strategic_rules.md",
    "b2_editorial": ROOT_DIR / "config" / "prompts" / "b2_editorial_prompt.md",
    "b3_director": ROOT_DIR / "config" / "prompts" / "b3_director_prompt.md",
    "b35_visual": ROOT_DIR / "config" / "prompts" / "b35_visual_rules.md",
    "b10_seo": ROOT_DIR / "config" / "prompts" / "seo_package_prompt.md",
    "cl3_t2i": ROOT_DIR / "config" / "prompts" / "cl3_vox_engine" / "image_prompts_system.md",
    "cl3_i2v": ROOT_DIR / "config" / "prompts" / "cl3_vox_engine" / "video_prompts_system.md",
}

# In-memory multi-hub cache state
_cache = {
    "central": {"data": None, "expiration": 0, "source": "NONE"},
    "content_engine": {"data": None, "expiration": 0, "source": "NONE"},
    "media_production": {"data": None, "expiration": 0, "source": "NONE"},
    "bundle": {"data": None, "expiration": 0, "source": "NONE"},
    "cinematic_tokens": {"data": None, "expiration": 0, "source": "NONE"},
    "vox_docudrama": {"data": None, "expiration": 0, "source": "NONE"},
    "b1_strategy": {"data": None, "expiration": 0, "source": "NONE"},
    "b2_editorial": {"data": None, "expiration": 0, "source": "NONE"},
    "b3_director": {"data": None, "expiration": 0, "source": "NONE"},
    "b35_visual": {"data": None, "expiration": 0, "source": "NONE"},
    "b10_seo": {"data": None, "expiration": 0, "source": "NONE"},
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
    """Save content to the local snapshot file for offline fallback.
    Only mutates disk if explicitly enabled via VF_SYNC_SNAPSHOT=1 to prevent
    dirtying tracked git working tree during runtime loading.
    """
    if os.getenv("VF_SYNC_SNAPSHOT", "0").lower() not in ("1", "true"):
        return
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
• Layer 2 (Foreground 1:1 2048x2048): Stylized editorial graphic novel digital illustration, waist-up three-quarter angle action framing with active hands manipulating physical documentary prop and directional gaze, on solid #FF00FF pure magenta chroma key.
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
            logger.info("[skill_loader] Using legacy markdown snapshot for central skills")
            return LEGACY_SNAPSHOT_FILE.read_text(encoding="utf-8")
        except Exception as _ex:
            logger.debug(f"Legacy snapshot read notice: {_ex}")

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


def fetch_prompt_module(key: str, force_refresh: bool = False) -> str:
    """Dynamically fetch prompt module from Notion SoT, memory cache, or verified snapshot.
    Respects Rule 118, 126, 132: logs whether source is [NOTION_LIVE] or [NOTION_SNAPSHOT].
    """
    global _cache
    now = time.time()

    if key not in _cache:
        _cache[key] = {"data": None, "expiration": 0, "source": "NONE"}

    entry = _cache[key]
    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    page_id = PROMPT_ENGINE_PAGE_IDS.get(key)
    content = ""

    # 1. Attempt Live Notion API Fetch via ag_notion_bridge
    if page_id and bridge:
        try:
            lines = _fetch_blocks_recursive(page_id, depth=0, max_depth=1)
            fetched = "\n".join(lines).strip()
            if len(fetched) >= 100:
                content = fetched
                entry["data"] = content
                entry["expiration"] = now + CACHE_TTL_SECONDS
                entry["source"] = "NOTION_LIVE"
                _save_snapshot(key, content)
                logger.info(f"[skill_loader] [NOTION_LIVE] Successfully loaded {len(content)} chars from Notion SoT page {page_id} for {key}")
                return content
        except Exception as e:
            logger.debug(f"[skill_loader] Notion live fetch failed for {key}: {e}")

    # 2. Verified Snapshot Fallback (from skills_snapshot.json)
    snapshot = _load_snapshot()
    snap_entry = snapshot.get(key)
    if isinstance(snap_entry, dict) and snap_entry.get("content"):
        content = snap_entry["content"].strip()
    elif isinstance(snap_entry, str) and snap_entry.strip():
        content = snap_entry.strip()

    if content and len(content) >= 100:
        entry["data"] = content
        entry["expiration"] = now + 600  # 10 min cache for snapshot
        entry["source"] = "NOTION_SNAPSHOT"
        logger.info(f"[skill_loader] [NOTION_SNAPSHOT] Loaded {len(content)} chars from verified Notion snapshot for {key}")
        return content

    # 3. Local Target File Fallback
    local_file = PROMPT_LOCAL_FILES.get(key)
    if local_file and local_file.exists():
        try:
            content = local_file.read_text(encoding="utf-8").strip()
            entry["data"] = content
            entry["expiration"] = now + 300
            entry["source"] = "LOCAL_FILE"
            logger.info(f"[skill_loader] [LOCAL_FILE] Loaded {len(content)} chars from {local_file.name} for {key}")
            return content
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading local prompt file {local_file}: {e}")

    return ""


def get_b1_strategic_rules(force_refresh: bool = False) -> str:
    """Strategic rules for B1 Topic & Niche Reasoning loaded dynamically from Notion SoT."""
    content = fetch_prompt_module("b1_strategy", force_refresh=force_refresh)
    if content:
        return content
    return (
        "CORE STRATEGIC EDITORIAL PRINCIPLES (RULE 118, 444, 445):\n"
        "1. RULE 118 ZERO-MOCK: Strictly ground the topic and angle in real search signals or YouTube benchmarks.\n"
        "2. CAUSAL MECHANISM MANDATE: Every approved angle must expose an institutional, financial, or systemic mechanism.\n"
        "3. RULE 444 AN ONG HOOK: Formulate a paradoxical opening hook.\n"
        "4. RULE 445 5-BEAT DOCUDRAMA ARCHITECTURE: Beat 1 Paradox, Beat 2 Red Herring, Beat 3 Fatal Vacuum, Beat 4 Smoking Gun, Beat 5 Living Warning.\n"
        "5. 7 CANONICAL INVESTIGATIVE PILLARS: Corporate Giants, Market Crashes, True Crime Forensic, Tech Geopolitical, Consumer Injustice.\n"
        "6. NATIVE GROUND TRUTH: All keywords in native language (JP/KR/EN).\n"
        "7. ANTI-TUTORIAL PACKAGING (RULE 130): Strictly forbidden tutorial phrasing."
    )


def get_b35_strategic_rules(force_refresh: bool = False) -> str:
    """Concise strategic visual production rules for B3.5 Prompt Forge loaded from Notion SoT."""
    content = fetch_prompt_module("b35_visual", force_refresh=force_refresh)
    if content:
        return content
    return (
        "=== NOTION SOT CONCISE VISUAL PRODUCTION RULES (RULES 114, 116, 120, 122, 128, 435, 446) ===\n"
        "1. TWO-LAYER COMPOSITION: Layer 1 BG (16:9 2560x1440), Layer 2 FG (1:1 2048x2048 #FF00FF magenta).\n"
        "2. STRICT CHROMA KEY SPEC: Foregrounds strictly on solid #FF00FF magenta.\n"
        "3. GRAPHIC NOVEL ART STYLE: Editorial Graphic Novel cel-shading illustration.\n"
        "4. CINEMATIC CONTINUITY & ERA AUTHENTICITY: Zero domain bleed.\n"
        "5. INDIGENOUS CULTURAL PROPS: Tangible local artifacts (JP: hanko, KR: sawonjeung/ingam). Zero English bleed.\n"
        "6. ENGLISH PRODUCTION BRIDGE: Visual prompts in descriptive English.\n"
        "7. MARKET ETHNICITY: Authentic phenotype, micro-expressions, zero dead eyes."
    )


def get_visual_strategic_rules() -> str:
    """Alias for get_b35_strategic_rules."""
    return get_b35_strategic_rules()


def get_b3_strategic_rules(force_refresh: bool = False) -> str:
    """Canonical Vox Director & Kinetic Storyboard rules for B3 Director Planner loaded from Notion SoT / CL3 Master System."""
    content = fetch_prompt_module("b3_director", force_refresh=force_refresh)
    if content:
        return content
    return (
        "=== CANONICAL VOX DIRECTOR RULES (RULES 120, 122, 128, 140, 141 - CL3 MASTER SYSTEM) ===\n"
        "1. ROLE: Vox Master Art Director & Kinetic Storyboard Director across 5 Beats.\n"
        "2. CL3 PAPER DIORAMA ARCHITECTURE: Multi-layered 3D papercraft, aged newsprint (#F4F1EA), halftone cutouts, deckle edges.\n"
        "3. 7 KINETIC INTERACTION FAMILIES (H1->H7): Snappy mechanical strike <= 0.4s with overshoot, dead-stop hold on twos.\n"
        "4. ZERO CARTESIAN COORDINATES: Natural physical staging, zero raw percentages (X:50%, Y:36%).\n"
        "5. COMMITTED CAMERA ACTOR: Exactly one camera movement per scene, ending with mandatory 'Settle on [target]'.\n"
        "6. SUBTITLE SAFE ZONE: Preserves bottom 20% vertical safe zone for Remotion karaoke 0ms drift.\n"
        "7. AUDIO SFX COUPLING: Tactile Foley matching contact dynamics, sound design only, no music, no voice-over."
    )


def get_cl3_t2i_rules(force_refresh: bool = False) -> str:
    """CL3 Paper Diorama T2I Master Architecture rules loaded dynamically from Notion SoT or local file."""
    content = fetch_prompt_module("cl3_t2i", force_refresh=force_refresh)
    if content:
        return content
    local_p = PROMPT_LOCAL_FILES.get("cl3_t2i")
    if local_p and local_p.exists():
        return local_p.read_text(encoding="utf-8")
    return ""


def get_cl3_i2v_rules(force_refresh: bool = False) -> str:
    """CL3 Paper Diorama I2V Master Architecture rules loaded dynamically from Notion SoT or local file."""
    content = fetch_prompt_module("cl3_i2v", force_refresh=force_refresh)
    if content:
        return content
    local_p = PROMPT_LOCAL_FILES.get("cl3_i2v")
    if local_p and local_p.exists():
        return local_p.read_text(encoding="utf-8")
    return ""


def get_b10_seo_rules(force_refresh: bool = False) -> str:
    """Concise strategic rules for B10 YouTube Packaging & SEO Metadata loaded from Notion SoT."""
    content = fetch_prompt_module("b10_seo", force_refresh=force_refresh)
    if content:
        return content
    return (
        "=== NOTION SOT B10 YOUTUBE PACKAGING RULES ===\n"
        "1. ZERO-MOCK DATA: Strictly grounded in episode narrative and breakout data.\n"
        "2. TITLE DYNAMICS: Title A (Curiosity Hook), Title B (SEO Virality), Title C (Provocative Question).\n"
        "3. BREAKOUT INJECTION: Weave Trends queries into top lines of description.\n"
        "4. CHAPTERS SPEC: 00:00 start, timestamps strictly matching Remotion.\n"
        "5. TAGS & HASHTAGS: <= 500 chars tags, exactly 3 high-intent hashtags."
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
    for key in list(_cache.keys()):
        if key in ("hits", "misses"):
            continue
        c = _cache[key]
        has_data = c["data"] is not None
        rem = max(0, int(c["expiration"] - now)) if has_data else 0
        hubs_info[key] = {
            "cached": has_data,
            "char_count": len(c["data"]) if has_data else 0,
            "remaining_seconds": rem,
            "source": c.get("source", "NONE")
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
        filtered = [line for line in lines if len(line.strip()) > 15]
        text = chr(10).join(filtered[:25]).strip()
        if text:
            _cache["self_learning"] = {"data": text, "expiration": now + CACHE_TTL_SECONDS, "source": "NOTION_LIVE"}
            return text
    except Exception as e:
        logger.warning(f"[skill_loader] Failed to fetch B11 self-learning rules: {e}")
    return ""


def get_b2_editorial_skills(force_refresh: bool = False) -> str:
    """Return high-density, targeted editorial skill prompts for B2 Story Engine from Notion SoT.
    Combines 10X 5-Beat Docudrama Micro-Pacing Architecture, Rule 113/114/130 YouTube Viral Mandates,
    and B11 Self-Learning post-mortem feedback dynamically without marketing context clutter.
    """
    base_editorial = fetch_prompt_module("b2_editorial", force_refresh=force_refresh)
    b11_lessons = get_b11_self_learning_rules(force_refresh=force_refresh)

    b11_section = ""
    if b11_lessons:
        b11_section = (
            "\n\n=== B11 CONTINUOUS SELF-LEARNING LESSONS (LIVE NOTION FEEDBACK) ===\n"
            f"{b11_lessons[:1200]}\n"
        )

    if base_editorial:
        return f"{base_editorial}\n{b11_section}"

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
    """Return targeted packaging & narrative hook prompt guidelines for B1.5 SEO Package Forge from Notion SoT.
    Decoupled per Rule 132: loads dynamically from Notion SoT or snapshot with B11 feedback.
    """
    base_prompt = get_b10_seo_rules(force_refresh=force_refresh)
    b11_lessons = get_b11_self_learning_rules(force_refresh=force_refresh)
    if b11_lessons:
        return f"{base_prompt}\n\n=== B11 CONTINUOUS SELF-LEARNING LESSONS (LIVE NOTION FEEDBACK) ===\n{b11_lessons[:1200]}"
    return base_prompt


def get_cinematic_tokens_dictionary(force_refresh: bool = False) -> dict:
    """Return the curated 20 Cinematic Flow Tokens dictionary.
    Decoupled per Rule 132: loads dynamically from config/prompts/cinematic_tokens_dictionary.json
    with in-memory caching.
    """
    global _cache
    now = time.time()
    if not force_refresh and _cache.get("cinematic_tokens", {}).get("data") and now < _cache["cinematic_tokens"]["expiration"]:
        _cache["hits"] += 1
        return _cache["cinematic_tokens"]["data"]

    _cache["misses"] += 1
    dict_file = ROOT_DIR / "config" / "prompts" / "cinematic_tokens_dictionary.json"
    data = {"tokens": []}
    if dict_file.exists():
        try:
            data = json.loads(dict_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading {dict_file}: {e}")

    _cache["cinematic_tokens"] = {
        "data": data,
        "expiration": now + CACHE_TTL_SECONDS
    }
    return data


def get_vox_docudrama_prompt(force_refresh: bool = False) -> str:
    """Return decoupled Vox Docudrama & Paper Collage prompt engine guidelines (Rule 132).
    Loads dynamically from config/prompts/vox_docudrama_engine.md with caching.
    """
    global _cache
    now = time.time()
    if not force_refresh and _cache.get("vox_docudrama", {}).get("data") and now < _cache["vox_docudrama"]["expiration"]:
        _cache["hits"] += 1
        return _cache["vox_docudrama"]["data"]

    _cache["misses"] += 1
    prompt_file = ROOT_DIR / "config" / "prompts" / "vox_docudrama_engine.md"
    content = ""
    if prompt_file.exists():
        try:
            content = prompt_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading {prompt_file}: {e}")

    if not content:
        content = (
            "You are an Elite Documentary Writer and Paper Collage Art Director.\n"
            "Produce Fern-style high-retention investigative scripts (2.5 wps) and tactile paper collage cutouts."
        )

    _cache["vox_docudrama"] = {
        "data": content,
        "expiration": now + CACHE_TTL_SECONDS
    }
    return content


def resolve_vox_theme_by_keywords(topic: str = "", niche: str = "") -> str:
    """Deterministically resolve one of the 9 Canonical Vox Theme Presets from topic keywords and niche."""
    t_low = (topic or "").lower()
    n_low = (niche or "").lower()

    if any(k in t_low for k in ["court", "trial", "fbi", "cia", "classified", "leak", "dossier", "redact", "hồ sơ", "mật", "tòa án"]):
        return "legal-dossier"
    if any(k in t_low for k in ["bank", "fed", "debt", "wall street", "bond", "ledger", "stock", "ngân hàng", "nợ", "lãi suất", "chứng khoán"]) or n_low == "money_power":
        return "financial-ledger"
    if any(k in t_low for k in ["blueprint", "engine", "aviation", "boeing", "rocket", "bridge", "machinery", "kỹ thuật", "máy bay", "động cơ"]):
        return "technical-blueprint"
    if any(k in t_low for k in ["hacker", "cyber", "punk", "rebellion", "silicon valley", "crypto", "zine"]):
        return "punk-zine"
    if any(k in t_low for k in ["polaroid", "1980s", "1970s", "1990s", "vintage photo", "nostalgia"]):
        return "retro-polaroid"
    if any(k in t_low for k in ["ancient", "century", "empire", "roman", "dynasty", "archival", "war", "lịch sử", "thế chiến", "triều đại"]) or n_low == "history":
        return "vintage-archival"
    if any(k in t_low for k in ["biology", "nature", "forest", "wildlife", "botanical", "môi trường", "sinh thái"]):
        return "botanical-field"
    if any(k in t_low for k in ["app", "software", "saas", "modern", "startup"]) or n_low == "technology":
        return "minimal-modern"

    return "newsprint-editorial"


def clear_cache():
    """Manually clear all cached rules."""
    global _cache
    for key in ("central", "content_engine", "media_production", "bundle", "cinematic_tokens", "vox_docudrama"):
        if key in _cache:
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
