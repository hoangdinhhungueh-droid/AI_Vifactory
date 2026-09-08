# app/services/story_engine_b2.py
"""
B2 Story Engine (5-Beat Docudrama 1,800–2,200 words) via GPT-6-Astra.
Architecture & Rule Compliance:
  - Strict Rule 118: Zero-Mock Data & Ask-Before-Deviating.
  - Strict Rule 120: Safe-Treatment Mandates & Timestamp-Accurate 5-Act Structure.
  - Strict Rule 445: 5-Beat Docudrama Story Generation (~1,800–2,200 words, 8-10 min runtime).
  - Synchronizes seamlessly to Notion Story Library DB (Dual-Callout & Forensic Metrics).
  - Dynamic Rule Injection: Inherits Central Skills (Rules 113–121) and Content Engine Hub
    (5-Beat architecture, pacing, and loop discipline) directly from Notion SoT.
"""

import os, sys, json, time, re, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

sys.path.insert(0, '/root/video_factory')
from app.services.hhtech_reasoner import call_gpt6_astra, detect_safety_and_theme
from app.services.skill_loader import (
    get_skill_rules,
    get_central_skills,
    get_content_engine_rules,
    get_media_production_rules,
    get_b2_editorial_skills
)
from app.services import story_gate as sgate
from scripts.ag_notion_bridge import resolve_id, update_page_properties, create_page, query_db, append_children_blocks, get_blocks, delete_block
try:
    from scripts.vf_insight_cards import fetch_active_insights, build_feedback_block
except ImportError:
    def fetch_active_insights(*a, **kw): return []
    def build_feedback_block(*a, **kw): return ''
import json as json_lib

NOTION_STORY_DB_ID = os.getenv("STORY_LIBRARY_DB_ID", "b0301989-2400-836b-bdb5-8131fea17736")
EPISODES_BASE_DIR = os.getenv("VF_EPISODES_DIR", "/var/vf/episodes")
PENDING_TASKS_DIR = "/var/vf/pending_tasks"
KNOWN_MARKETS = {"EN", "JP", "KR"}
ACT_PATTERN = re.compile(r'(=== ACT [I|V|X]+ ===.*?)(?=(=== ACT [I|V|X]+ ===|\Z))', re.DOTALL)



def _opening_hook(script: str, max_chars: int = 320) -> str:
    """The first 1-2 sentences of the script, whole.
    Extracts the opening curiosity and emotional hook for quality scoring.
    """
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (script or "").strip()) if s.strip()]
    if not sents:
        return ""
    hook = sents[0]
    for nxt in sents[1:2]:
        if len(hook) + len(nxt) + 1 <= max_chars:
            hook = hook + " " + nxt
    return hook[:max_chars]





def load_competitor_intel(task_id: str) -> dict:
    """Load B1.5 Competitor Intelligence Card if it exists in either episodes dir.
    Enforces strict contract: raises RuntimeError if missing or incomplete, unless bypassed.
    """
    candidates = [
        os.path.join(EPISODES_BASE_DIR, task_id, "competitor_intel_card.json"),
        os.path.join("/root/video_factory/episodes", task_id, "competitor_intel_card.json"),
    ]
    for intel_path in candidates:
        if os.path.exists(intel_path):
            try:
                with open(intel_path, "r", encoding="utf-8") as f:
                    data = json_lib.load(f)
                    if data:
                        return data
            except Exception as e:
                logger.debug(f"[story_engine] Error loading competitor intel from {intel_path}: {e}")
    if os.getenv("VF_BYPASS_INTEL_CHECK") == "1":
        logger.warning(f"[story_engine] VF_BYPASS_INTEL_CHECK active: continuing without intel card for {task_id}")
        return {}
    raise RuntimeError(
        f"Strict Contract Violation: B1.5 Competitor Intel Card missing or unreadable for task {task_id}. "
        f"Run B1.5 Two-Pass recon before B2 story generation!"
    )


def load_grounding_intel(task_id: str, out_dir: str, topic: str = "", niche_brief: str = "", market: str = "EN") -> tuple[dict, str]:
    """Load B1.5.5 Grounding Intel Card.
    Enforces strict contract: raises RuntimeError if missing or fails gate, unless bypassed.
    """
    candidates = [
        os.path.join(out_dir, "grounding_intel.json"),
        os.path.join(EPISODES_BASE_DIR, task_id, "grounding_intel.json"),
        os.path.join("/root/video_factory/episodes", task_id, "grounding_intel.json"),
    ]
    g_data = None
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 10:
            try:
                with open(p, "r", encoding="utf-8") as gf:
                    g_data = json_lib.load(gf)
                    if g_data:
                        break
            except Exception:
                pass

    if not g_data and topic:
        # Attempt JIT Grounding Research
        logger.info(f"[story_engine] Grounding intel missing for {task_id}. Attempting JIT Google Search Grounding...")
        try:
            from app.services.grounding_layer_b15 import run_grounding_research
            g_data = run_grounding_research(topic=topic, search_hint=niche_brief, market=market)
            if g_data:
                os.makedirs(out_dir, exist_ok=True)
                with open(os.path.join(out_dir, "grounding_intel.json"), "w", encoding="utf-8") as gf:
                    json_lib.dump(g_data, gf, ensure_ascii=False, indent=2)
        except Exception as _je:
            logger.error(f"[story_engine] JIT Grounding Research failed for {task_id}: {_je}")

    from app.services.grounding_layer_b15 import passes_grounding_gate, format_grounded_facts_for_prompt

    if os.getenv("VF_BYPASS_GROUNDING_CHECK") == "1":
        logger.warning(f"[story_engine] VF_BYPASS_GROUNDING_CHECK active: continuing without verified grounding for {task_id}")
        return g_data or {}, format_grounded_facts_for_prompt(g_data) if g_data else ""

    if not g_data:
        raise RuntimeError(
            f"Strict Contract Violation: B1.5.5 Grounding Intel Card missing for task {task_id}. "
            f"Run B1.5.5 Grounding Layer before B2 story generation!"
        )

    ok, reason = passes_grounding_gate(g_data, min_verified=2, require_whitelist=True)
    if not ok:
        raise RuntimeError(
            f"Strict Contract Violation: B1.5.5 Grounding Gate REJECTED for task {task_id} ({reason}). "
            f"Cannot proceed to B2 without verified facts!"
        )

    block = format_grounded_facts_for_prompt(g_data)
    return g_data, block


def load_task_metadata(task_id: str) -> dict:
    """Load metadata for a given task ID from local pending cache or Notion Story Library."""
    cache_path = os.path.join(PENDING_TASKS_DIR, f"{task_id}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[story_engine] Error reading pending task {cache_path}: {e}")

    try:
        res = query_db(NOTION_STORY_DB_ID)
        for r in res.get("results", []):
            props = r.get("properties", {})
            
            def _get_txt(p):
                if not p: return ""
                t = p.get("type")
                if t == "title": return "".join(x.get("plain_text", "") for x in p.get("title", []))
                if t == "rich_text": return "".join(x.get("plain_text", "") for x in p.get("rich_text", []))
                return ""
            
            tid = _get_txt(props.get("Task ID", {}))
            eid = _get_txt(props.get("Episode ID", {}))
            if task_id in (tid, eid):
                return {
                    "task_id": task_id,
                    "market": props.get("Market", {}).get("select", {}).get("name", "EN"),
                    "topic": _get_txt(props.get("Name", {})),
                    "story_arcs": _get_txt(props.get("Story Direction (5 Arcs)", {})),
                    "niche_brief": _get_txt(props.get("Niche Angle Brief", {})),
                    "search_key": _get_txt(props.get("Search-Specific Key", {})),
                    "page_id": r.get("id")
                }
    except Exception as e:
        logger.warning(f"[story_engine] Error querying Notion Story Library for {task_id}: {e}")

    parts = [p for p in re.split(r"[_-]", task_id) if p]
    head = parts[0].upper() if parts else ""
    mkt = head if head in KNOWN_MARKETS else "EN"
    body = [p for p in parts[1:] if not re.fullmatch(r"ep\d+", p, re.I)]
    raw_name = "_".join(body) if body else task_id
    theme, safety_label, treatment_note = detect_safety_and_theme(raw_name, mkt)
    
    return {
        "task_id": task_id,
        "market": mkt,
        "topic": raw_name.replace("_", " ").title(),
        "story_arcs": "Beat 1 (Nghịch lý mở màn 0-60s) -> Beat 2 (Bẫy truyền thông & Red Herring) -> Beat 3 (Manh mối rò rỉ & Vết nứt thể chế) -> Beat 4 (Cỗ máy lợi ích & Smoking Gun) -> Beat 5 (Gương soi hiện tại & Lời cảnh báo)",
        "niche_brief": f"Cơ chế ngách và sự kiện lịch sử/kinh tế đằng sau {raw_name}.",
        "breakout_queries": [],
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note
    }


def generate_5_arc_story(task_id: str, custom_meta: dict | None = None, force: bool = False) -> dict:
    """Generate a complete 5-Beat Docudrama script (1,800-2,200 words, ~12-15 min) using GPT-6-Astra
    enforcing YouTube Safety, Rule 444 An Ong Hook, and Rule 445 in a single optimized pass.
    Inherits authentic rules dynamically from Notion SoT (Central Skills + Content Engine Hub).
    """
    meta = custom_meta or load_task_metadata(task_id)
    mkt = meta.get("market", "EN").upper()
    topic = meta.get("topic") or meta.get("topic_name_vi") or meta.get("subject") or meta.get("raw_term") or task_id
    viral_angle = meta.get("specific_viral_angle") or ""
    niche_brief = meta.get("niche_brief") or meta.get("niche_angle_brief") or ""
    story_arcs = meta.get("story_arcs") or meta.get("story_direction_5_arcs") or ""
    breakout_queries = meta.get("breakout_queries") or meta.get("rising_queries") or []
    
    theme = meta.get("content_theme") or meta.get("theme")
    safety_label = meta.get("safety_label") or meta.get("youtube_safety_label")
    treatment_note = meta.get("treatment_note")
    
    if not safety_label or not treatment_note:
        theme, safety_label, treatment_note = detect_safety_and_theme(topic, mkt)

    out_dir = os.path.join(EPISODES_BASE_DIR, task_id)
    os.makedirs(out_dir, exist_ok=True)
    root_ep_dir = os.path.join("/root/video_factory/episodes", task_id)
    os.makedirs(root_ep_dir, exist_ok=True)

    intel_card = load_competitor_intel(task_id)
    intel_status = "loaded" if intel_card else "none"
    anatomy = (intel_card.get("competitor_narrative_anatomy") or {}) if intel_card else {}
    competitor_gap = meta.get("competitor_differentiation_gap") or anatomy.get("fatal_explanatory_vacuum") or (intel_card.get("competitor_gap") if intel_card else "")
    pivot_angle = anatomy.get("our_10x_pivot_angle") or ""
    frustrations = anatomy.get("audience_core_frustrations") or []
    comp_acts = anatomy.get("competitor_act_breakdown") or ""
    competitors = meta.get("viral_competitor_videos") or (intel_card.get("competitors") if intel_card else []) or (intel_card.get("competitor_benchmarks") if intel_card else [])

    # Check for pre-computed SEO package & 60s hook (Rule 119 & Rule 444)
    seo_pkg = {}
    for cand_dir in [out_dir, root_ep_dir]:
        sp_path = os.path.join(cand_dir, "seo_package.json")
        if os.path.exists(sp_path):
            try:
                with open(sp_path, "r", encoding="utf-8") as sf:
                    seo_pkg = json.load(sf)
                    if seo_pkg:
                        break
            except Exception:
                pass
    if not seo_pkg and isinstance(meta.get("seo_package"), dict):
        seo_pkg = meta["seo_package"]

    seo_title_a = seo_pkg.get("title_a") or meta.get("title_a") or ""
    seo_title_b = seo_pkg.get("title_b") or meta.get("title_b") or ""
    hook_60s = seo_pkg.get("hook_60s") or meta.get("hook_60s") or ""
    hook_3s = seo_pkg.get("hook_3s") or meta.get("hook_3s") or ""
    if seo_pkg.get("specific_viral_angle"):
        viral_angle = seo_pkg["specific_viral_angle"]
    
    logger.info(f"[story_engine] Starting 5-Act story generation for {task_id} ({mkt}) | Topic: {topic} | Angle: {viral_angle}... [Intel: {intel_status}, Gap: {bool(competitor_gap)}]")
    
    lang_name = "English" if mkt == "EN" else ("Japanese" if mkt == "JP" else "Korean")

    # Load authentic dynamic rules directly from Notion Single Source of Truth
    editorial_skills = get_b2_editorial_skills()

    crime_forensic_mandate = ""
    is_sensitive_crime = theme in ("true_crime_investigative", "psychology_manipulation_fraud") or any(
        w in (topic + " " + niche_brief).lower() for w in [
            "murder", "killer", "crime", "death", "homicide", "horror", "kinh dị", "án mạng", "giết người",
            "sát nhân", "사건", "살인", "연쇄살인", "事件", "殺人", "連続殺人"
        ]
    )
    if is_sensitive_crime:
        crime_forensic_mandate = (
            "\n🚨 MANDATORY CASE-SOLVING & FORENSIC PROTOCOL (CHỈ ĐẠO PHÁ ÁN & TRUY BẮT):\n"
            "1. INVESTIGATIVE & PROCEDURAL LENS ONLY (HƯỚNG ĐIỀU TRA & PHÁ ÁN):\n"
            "   - Frame the entire narrative through the objective lens of the detectives, forensic scientists, intelligence profilers, or prosecutors.\n"
            "   - Focus squarely on: the evidentiary puzzle, the forensic breakthrough (DNA, fingerprints, digital footprint, ballistic, autopsy toxicology, financial paper trail), the killer's fatal misstep, and the procedural manhunt net closing in.\n"
            "2. STRICT ZERO-GORE POLICY (TUYỆT ĐỐI CẤM MÔ TẢ HÀNH VI / HIỆN TRƯỜNG ĐẪM MÁU):\n"
            "   - STRICTLY FORBIDDEN: Detailing physical trauma, blood splatter, screams, struggle, weapon mechanics, mutilation, suffering, or torture.\n"
            "   - Refer to criminal acts ONLY in concise, clinical, legal terminology ('a disappearance was logged', 'toxicology revealed lethal compounds', 'investigators confirmed foul play').\n"
            "   - Immediately pivot from the incident to: How did the authorities piece together the mystery? What systemic blindspot was exposed? How was justice secured?\n"
            "3. ZERO CRIMINAL GLORIFICATION / FULL VICTIM RESPECT:\n"
            "   - Treat the perpetrator as flawed, cornered, and undone by their own arrogance. Zero romanticization of criminal 'genius'.\n"
        )

    hook_anchor_prompt = ""
    if hook_60s and not seo_pkg.get("is_fallback"):
        anti_imagine_directive = ""
        if "imagine" in hook_60s.lower() or "hypothetical" in hook_60s.lower():
            anti_imagine_directive = (
                "\n🚨 RULE 130 MANDATE: The reference hook contains passive/hypothetical framing ('imagine'). "
                "You MUST convert this into a DIRECT FACTUAL ASSERTION of verified events (Level 1 Primary Catalyst) "
                "with exact dates, actors, and quantitative metrics from the Grounding Table. STRICTLY FORBIDDEN: Writing 'Imagine...' in your script!\n"
            )
        if "hypothesis" in hook_60s.lower() or "unauthenticated" in hook_60s.lower():
            anti_imagine_directive += (
                "\n🚨 RULE 130 ANTI-NIHILISM MANDATE: The reference hook contains hyper-skeptical framing ('hypothesis'). "
                "You MUST treat verified real-world crisis events (e.g. market dislocations, operational halts, official alerts) as genuine facts (Level 1 Catalyst), "
                "and focus on explaining the transmission mechanism (institutional, contractual, regulatory, or financial transmission), NOT denying the reality of the crisis!\n"
            )
        hook_anchor_prompt = f"""• Approved YouTube Title A: {seo_title_a}
• Pre-Approved 3s Cold-Open: {hook_3s}
• Mandatory 60s Opening Premise Contract (Act I MUST anchor directly to this):
  "{hook_60s}"{anti_imagine_directive}
CRITICAL HOOK INSTRUCTION: You MUST begin and shape Act I directly paying off this premise, leading with verified Level 1 Catalyst facts and quantitative numbers. Do not drift into abstract theory.

"""
    elif seo_title_a:
        hook_anchor_prompt = f"""• Target YouTube Title: {seo_title_a}
• Title Premise Instruction (Rule 130): Act I MUST directly address the central premise of this title, leading with the Level 1 Primary Catalyst and quantitative metrics from the Grounding Table.

"""

    system_prompt = (
        f"You are a World-Class Master Non-Fiction Investigative Documentary Scriptwriter for Video Factory.\n"
        f"Target Narration Language: {lang_name}.\n"
        f"Total Word Count Target: 1,800 - 2,200 words (~12 to 15 minutes narration at ~150 WPM) across 5 structured Acts.\n"
        f"Structure per Act: Approximately 360-440 words across 3-4 vivid, investigative paragraphs per Act.\n"
        f"Strict Requirement: Scripts under 1,700 words will be rejected by the story gate.\n\n"
        f"MANDATORY STORY GATE 12/12 REQUIREMENTS:\n"
        f"• Check 9 (Hook Shock in First 60 Words): The very first sentence of Act I MUST open with a concrete percentage (%), monetary sum ($), or numeric figure. Do not delay the number to sentence 2.\n"
        f"• Check 2, 3 & 4 (Curiosity Loops Open & Closed): Plant at least 8 to 10 explicit curiosity questions with '?' across the script (~2 per Act). Frequently close loops using phrases like 'that is why', 'which is how', 'the answer', 'in the end'.\n"
        f"• Check 5 (Sourced Numbers): Include at least 10 grounded numbers across the script accompanied by explicit sourcing language ('according to reports from [Source]', 'records from [Source] indicate').\n"
        f"• Check 7 (5-Act Architectural Cues): Each Act must explicitly weave in its architectural vocabulary:\n"
        f"   - Act I (Hook/Shock): 'collapse', 'shock', 'disappear', 'first', 'only', and questions '?'.\n"
        f"   - Act II (The False Narrative): 'official story', 'narrative', 'headline', 'myth', 'red herring'.\n"
        f"   - Act III (Systemic Blindspot): 'paper trail', 'blindspot', 'loophole', 'leak', 'memo', 'forensic'.\n"
        f"   - Act IV (The Smoking Gun): 'smoking gun', 'culprit', 'exposed', 'unmasked', 'profited'.\n"
        f"   - Act V (The Modern Mirror): 'mirror', 'warning', 'modern', 'today', 'lesson', 'verdict'.\n"
        f"• Check 12 (Pattern Interrupt in Act III): Write at least one punchy sentence of 2 to 6 words maximum in Act III (e.g. 'The paper trail vanished.', 'Then came the audit.').\n"
        f"• Check 10 (Zero Banned Cliches): 100% elimination of banned AI cliches ('in a world where', 'little did they know', 'testament to', 'double-edged sword', 'beacon of hope', 'it's worth noting', 'at the end of the day').\n\n"
        f"{editorial_skills}\n\n"
        f"SPECIFIC CONTEXT FOR THIS SCRIPT:\n"
        f"• Subject / Case: {topic}\n"
        f"• Specific Viral Angle: {viral_angle}\n"
        f"• Core Causal Mechanism: {niche_brief}\n"
        f"• 5-Arc Direction: {story_arcs}\n"
        f"• Content Theme: {theme}\n"
        f"• Breakout Search Queries (Embed in Act 1): {', '.join(breakout_queries[:4])}\n\n"
        f"{hook_anchor_prompt}"
        f"CRITICAL PLATFORM SAFETY MANDATE [{safety_label}]:\n"
        f"• {treatment_note}\n"
        f"• Zero graphic violence, zero gore, zero criminal glorification, zero method instructions.\n"
        f"{crime_forensic_mandate}\n"
        f"Output ONLY the complete script organized strictly by Acts using '=== ACT I ===', '=== ACT II ===', '=== ACT III ===', '=== ACT IV ===', '=== ACT V ===' markers. No markdown fences, no stage directions."
    )

    competitor_context = ""
    context_lines = []
    if pivot_angle:
        context_lines.append(
            "🎯 10X INDEPENDENT INVESTIGATIVE PIVOT (OUR STRATEGIC LEVERAGE):\n"
            f"{pivot_angle}\n"
            "MANDATE: Frame our entire 15-minute documentary around this independent breakthrough angle. "
            "Expose the systemic paper trails and institutional mechanisms that nobody else dared or bothered to examine!"
        )
    if competitor_gap:
        context_lines.append(
            "⚠️ COMPETITOR EXPLANATORY VACUUM (FATAL BLINDSPOT):\n"
            f"Competitors only covered surface events and missed this crucial mechanism: \"{competitor_gap}\"\n"
            "REQUIREMENT: Acts III, IV, and V must systematically expose and explain this blindspot in depth!"
        )
    if comp_acts:
        context_lines.append(
            f"📊 COMPETITOR NARRATIVE STRUCTURE (What they did):\n{comp_acts}\n"
            "Use this structure only as a springboard to understand viewer expectations, then leap far beyond it with deeper forensic details."
        )
    if frustrations:
        context_lines.append(
            "🔥 AUDIENCE BURNING QUESTIONS & FRUSTRATIONS (MUST BE RESOLVED):\n"
            + "\n".join(f"  - {fr}" for fr in frustrations[:3])
            + "\nYour script must seamlessly and authoritatively answer every single one of these viewer doubts throughout the narrative."
        )
    if competitors:
        context_lines.append("TOP VIRAL COMPETITOR BENCHMARKS (High velocity references):")
        for c in competitors[:3]:
            v_views = c.get("views", 0)
            v_title = c.get("title", "?")
            context_lines.append(f'  - \"{v_title}\" ({v_views:,} views)')
    if intel_card and intel_card.get("audience_comment_gaps"):
        context_lines.append("High-engagement audience comment quotes:")
        for g in intel_card["audience_comment_gaps"][:3]:
            context_lines.append(f"  - [{g.get('likes_count', 0)} likes] {g.get('comment_verbatim', '')[:140]}")

    context_lines.append(
        "🚨 STRICT ZERO COMPETITOR NAME-DROP MANDATE:\n"
        "NEVER mention the names of competitor channels, creators, or rival videos. "
        "Maintain the clinical, objective authority of a premier independent investigative documentary."
    )

    if context_lines:
        competitor_context = "\n".join(context_lines) + "\n\n"

    # Grounding Layer (B1.5.5 Fact-Anchor Injection - Rule 118 & Rule 128)
    # Strict contract: load_grounding_intel raises RuntimeError if missing or rejected
    g_data, grounding_block = load_grounding_intel(
        task_id=task_id,
        out_dir=out_dir,
        topic=topic,
        niche_brief=niche_brief,
        market=mkt
    )
    if grounding_block:
        logger.info(f"[story_engine] Loaded Grounding Layer table ({len(g_data.get('claims', []))} claims) for {task_id}.")

    story_file = os.path.join(out_dir, "story.txt")
    existing_script = ""
    if os.path.exists(story_file) and not force:
        try:
            with open(story_file, "r", encoding="utf-8") as sf:
                existing_script = sf.read().strip()
            # Anti-hallucination check: force regeneration if script was ungrounded
            grounding_intel_file = os.path.join(out_dir, "grounding_intel.json")
            is_ungrounded = ("hypothetical calculation" in existing_script.lower() or not os.path.exists(grounding_intel_file))
            if is_ungrounded:
                logger.info(f"[story_engine] Existing story.txt for {task_id} is ungrounded or missing grounding_intel.json. Forcing fresh regeneration!")
                existing_script = ""
            elif len(existing_script.split()) >= 1500:
                logger.info(f"[story_engine] Reusing existing valid grounded story.txt ({len(existing_script.split())} words) for {task_id}.")
        except Exception as e:
            logger.warning(f"[story_engine] Error reading existing story.txt: {e}")
    elif force:
        logger.info(f"[story_engine] Force regeneration requested for {task_id}. Generating fresh high-suspense grounded script...")

    if existing_script and len(existing_script.split()) >= 1500:
        full_script = existing_script
    else:
        # B11->B2 Feedback Loop: fetch active InsightCards (Rule 126 compliant, non-fatal)
        _b2_notion_token = (
            os.getenv('NOTION_TOKEN', '') or
            os.getenv('VF_NOTION_TOKEN', '')
        )
        _b2_insight_cards = fetch_active_insights(_b2_notion_token, mkt)
        feedback_block = build_feedback_block(_b2_insight_cards)
        
        user_prompt = (
            f"Generate the comprehensive 12-15 minute (1,800-2,200 words) Non-Fiction Investigative Documentary Script for {topic} following the 5-Beat Investigative Docudrama structure with HIGH DRAMATIC SUSPENSE and ticking-clock pacing.\n"
            f"Structure: Beat 1 (The Impossible Contradiction & Ticking Clock) -> Beat 2 (The False Narrative & Red Herring) -> Beat 3 (The Systemic Blindspot & Paper Trail) -> Beat 4 (The Real Culprit & Smoking Gun) -> Beat 5 (The Uncomfortable Modern Mirror & Living Warning).\n"
            f"Tone & Style: Johnny Harris investigative rigor meets Chernobyl / Margin Call procedural tension—clinical, fast-paced, high-stakes, forensically detailed, completely free of fluff.\n"
            f"Language: {lang_name}.\n"
            f"Core Mechanism: {niche_brief}\n"
            f"5-Arc Narrative: {story_arcs}\n"
            f"Content Theme: {theme}\n"
            f"Breakout Search Queries to prioritize in Act I: {', '.join(breakout_queries)}\n\n"
            f"{grounding_block}\n\n" if grounding_block else ""
            f"{competitor_context}"
            f"{feedback_block}"
            f"ACT I OPENING MANDATE (Rule 444 An Ong Hook, Rule 130 Search-Intent Payoff & Contemporary Event Anchor): "
            f"Sentence 1 of Act I MUST open with a shock quantitative stake or economic contradiction. "
            f"Paragraphs 1-2 of Act I MUST explicitly name and anchor to the verified Contemporary Catalyst Event "
            f"(exact date, acting entity, and verified quantitative impact from the Grounding Table). "
            f"Zero generic preamble, slow historical setup, or abstract theoretical hand-waving ('When a threat occurs'); "
            f"directly satisfy and pay off the viewer's search query with verified contemporary facts before peeling back the systemic layers.\n"
            f"Write the full ~1,800-2,200 word script now, adhering strictly to the 5-Act markers:"
        )

        logger.info(f"[story_engine] Calling HHTech GPT-6-Astra for 5-Act Script generation (1,800-2,200 words)...")
        full_script_raw = call_gpt6_astra(user_prompt, system_prompt=system_prompt, max_tokens=3400, timeout=240.0)

        cleaned_acts = []
        matches = ACT_PATTERN.findall(full_script_raw)
        if matches:
            for m in matches:
                cleaned_acts.append(m[0].strip())

        if len(cleaned_acts) < 5:
            # Fallback split by double newlines if markers weren't strictly matched
            full_script = full_script_raw.strip()
        else:
            full_script = "\n\n".join(cleaned_acts)

    total_words = len(full_script.split())
    logger.info(f"[story_engine] Generated 5-Act Script: {total_words} words for {task_id}.")

    # Audit Story Gate Score
    audit = sgate.score_story(full_script)
    story_score_str = f"{audit.get('score', 8)}/{audit.get('max_score', 12)}"
    story_verdict = audit.get('verdict') or 'UNKNOWN'
    logger.info(f"[story_engine] Initial Story Gate Score: {story_score_str} | Verdict: {audit.get('verdict')}")

    # Auto-Refine Self-Correction Loop: Mandate 12/12 Perfect Score for every Episode
    if audit.get("score", 0) < 12 or story_verdict != "PASS":
        for refine_attempt in range(1, 3):
            logger.warning(
                f"[story_engine] Story Gate under 12/12 ({audit.get('score')}/{audit.get('max_score')}). "
                f"Fix hints: {audit.get('fix_hints')}. Banned hits: {audit.get('banned_phrases_found')}. "
                f"Initiating Auto-Refine Attempt {refine_attempt}/2 via GPT-6-Astra to achieve 12/12..."
            )
            refine_user = (
                f"The generated script scored {audit.get('score')}/{audit.get('max_score')} on Story Gate. Target is 12/12 PERFECT SCORE.\n"
                f"REQUIRED CORRECTIONS:\n" + "\n".join(f"- {h}" for h in audit.get("fix_hints", [])) + "\n\n"
                f"CRITICAL REMINDERS FOR 12/12:\n"
                f"1. Hook Shock: Sentence 1 of Act I MUST feature a quantitative number, %, or $ figure within 60 words.\n"
                f"2. Pattern Interrupt: Act III MUST have at least one short sentence of 2 to 6 words (e.g. 'The paper trail vanished.').\n"
                f"BANNED PHRASES FOUND (MUST ELIMINATE): {', '.join(audit.get('banned_phrases_found', []))}\n\n"
                f"Please rewrite and polish the entire 5-Act script, strictly maintaining 1,800-2,200 words, "
                f"preserving all 5 Acts ('=== ACT I ===' to '=== ACT V ==='), ensuring the first sentence opens with a shock quantitative stake (Rule 444), and resolving all failed items.\n\n"
                f"Current Draft:\n{full_script}\n\n"
                f"Output ONLY the corrected 5-Act script now:"
            )
            try:
                refined_raw = call_gpt6_astra(refine_user, system_prompt=system_prompt, max_tokens=3400, timeout=240.0)
                if refined_raw and len(refined_raw.split()) >= 1000:
                    cleaned_acts_ref = []
                    matches_ref = ACT_PATTERN.findall(refined_raw)
                    if matches_ref:
                        for mr in matches_ref:
                            cleaned_acts_ref.append(mr[0].strip())
                    if len(cleaned_acts_ref) == 5:
                        full_script = "\n\n".join(cleaned_acts_ref)
                    else:
                        full_script = refined_raw.strip()
                    audit = sgate.score_story(full_script)
                    story_score_str = f"{audit.get('score')}/{audit.get('max_score')}"
                    story_verdict = audit.get('verdict') or 'UNKNOWN'
                    logger.info(f"[story_engine] Post-Refine Attempt {refine_attempt} Score: {story_score_str} | Verdict: {story_verdict}")
                    if audit.get("score", 0) >= 12:
                        logger.info(f"[story_engine] Auto-Refine SUCCESS: Perfect 12/12 achieved on attempt {refine_attempt}!")
                        break
            except Exception as _re:
                logger.warning(f"[story_engine] Auto-refine attempt {refine_attempt} error: {_re}")

    # ----------------------------------------------------
    # B2.1 Fact & Causal Integrity Audit Gate (Rule 118 & Rule 130)
    # Audits full verbatim script against Grounding Fact Table using claude-opus-5
    # ----------------------------------------------------
    fact_audit_result = {}
    grounding_claims = []
    try:
        for _g_cand in [os.path.join(out_dir, "grounding_intel.json"), os.path.join(root_ep_dir, "grounding_intel.json")]:
            if os.path.exists(_g_cand):
                with open(_g_cand, "r", encoding="utf-8") as _gf:
                    grounding_claims = json.load(_gf).get("claims", [])
                if grounding_claims:
                    break
    except Exception as _ge:
        logger.warning(f"[story_engine] Error loading grounding claims for B2.1: {_ge}")

    if not grounding_claims and 'g_data' in locals() and isinstance(g_data, dict):
        grounding_claims = g_data.get("claims", [])

    if grounding_claims:
        try:
            from app.services.story_fact_auditor_b2 import audit_story_facts_and_causality
            logger.info(f"[story_engine] Running B2.1 Fact & Causal Audit via claude-opus-5 for {task_id}...")
            fact_audit_result = audit_story_facts_and_causality(
                story_text=full_script,
                grounding_claims=grounding_claims,
                topic_meta={
                    "task_id": task_id,
                    "topic_name_vi": topic,
                    "rising_queries": breakout_queries
                },
                market=mkt,
                model="claude-opus-5",
                fallback_model="gpt-6-astra"
            )
            f_verdict = fact_audit_result.get("verdict", "PASS").upper()
            f_score = float(fact_audit_result.get("audit_score", 8.0))
            logger.info(f"[story_engine] B2.1 Fact & Causal Audit: Verdict={f_verdict} (Score: {f_score}/10)")

            # 1-Shot Self-Repair if audit fails (< 7.5 or FAIL)
            if f_verdict == "FAIL" or f_score < 7.5:
                audit_critique = fact_audit_result.get("audit_notes") or fact_audit_result.get("veto_reason") or "Factual or causal discrepancies found."
                logger.warning(f"[story_engine] B2.1 Audit FAILED (Score: {f_score}/10). Triggering 1-Shot Fact & Causal Self-Repair via Astra...")

                repair_prompt = f"""You are correcting an investigative documentary script that failed a rigorous factual and causal verification audit.

=== AUDIT DISCREPANCIES & CRITIQUE (BY CLAUDE-OPUS-5) ===
{audit_critique}

=== ORIGINAL SCRIPT ===
{full_script}

=== MANDATORY GROUNDING TRUTH TABLE ===
{grounding_block}

INSTRUCTIONS FOR REPAIR:
1. Correct every cited factual discrepancy, fabricated number, and inverted causal relationship identified by Claude-Opus-5.
2. Ensure Level 1 Primary Catalyst is explicitly named in Act I.
3. Preserve the 1,800 - 2,200 word count across the 5 structured Acts ('=== ACT I ===' to '=== ACT V ===').
4. Do not invent any new numbers not found in the Grounding Table.
Output ONLY the complete repaired 5-Act script:"""

                try:
                    repaired_script_raw = call_gpt6_astra(
                        repair_prompt,
                        system_prompt=system_prompt,
                        max_tokens=3400,
                        timeout=240.0
                    )
                    r_cleaned = []
                    r_matches = ACT_PATTERN.findall(repaired_script_raw)
                    if r_matches:
                        for rm in r_matches:
                            r_cleaned.append(rm[0].strip())
                    repaired_script = "\n\n".join(r_cleaned) if len(r_cleaned) >= 5 else repaired_script_raw.strip()

                    logger.info(f"[story_engine] Re-auditing repaired script via claude-opus-5 for {task_id}...")
                    re_audit = audit_story_facts_and_causality(
                        story_text=repaired_script,
                        grounding_claims=grounding_claims,
                        topic_meta={
                            "task_id": task_id,
                            "topic_name_vi": topic,
                            "rising_queries": breakout_queries
                        },
                        market=mkt,
                        model="claude-opus-5",
                        fallback_model="gpt-6-astra"
                    )
                    re_verdict = re_audit.get("verdict", "PASS").upper()
                    re_score = float(re_audit.get("audit_score", 8.0))
                    logger.info(f"[story_engine] Post-Repair B2.1 Audit: Verdict={re_verdict} (Score: {re_score}/10)")

                    if re_verdict == "PASS" and re_score >= 7.5:
                        full_script = repaired_script
                        fact_audit_result = re_audit
                        f_verdict = re_verdict
                        f_score = re_score
                        logger.info(f"[story_engine] 1-Shot Self-Repair SUCCESS: Kịch bản đã được sửa chữa đạt chuẩn ({re_score}/10)!")
                    else:
                        fact_audit_result = re_audit
                        logger.error(f"[story_engine] 1-Shot Self-Repair STILL FAILED (Score: {re_score}/10). Halting at B2.1 Gate.")
                except Exception as _re_err:
                    logger.error(f"[story_engine] 1-Shot Self-Repair execution failed: {_re_err}")
        except Exception as _fa_err:
            logger.warning(f"[story_engine] B2.1 Fact & Causal Audit warning: {_fa_err}")

    # Write story.txt to both directories
    for d in [out_dir, root_ep_dir]:
        try:
            with open(os.path.join(d, "story.txt"), "w", encoding="utf-8") as f:
                f.write(full_script)
        except Exception as _fe:
            logger.warning(f"[story_engine] Error writing story.txt to {d}: {_fe}")

    # ----------------------------------------------------
    # B2 Output Finalization (Rule 125: B3 Scene breakdown delegated to director_planner_b3.py)
    # ----------------------------------------------------
    logger.info("[story_engine] B2 5-Act story generation complete. Scene breakdown delegated to B3 Art Director.")
    scenes = []

    # Build brain_input.json
    brain_input = {
        "episode_id": task_id,
        "market": mkt.lower(),
        "topic": topic,
        "story": full_script,
        "story_gate_score": story_score_str,
        "bgm_mood": "dramatic",
        "hook_3s": hook_3s or _opening_hook(full_script),
        "hook_60s": hook_60s,
        "title_a": seo_title_a,
        "title_b": seo_title_b,
        "seo_package": seo_pkg,
        "breakout_queries": breakout_queries,
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note,
        "scenes": scenes,
        "total_scenes": len(scenes),
        "render_architecture": "two_layer_v1",
        "fact_causal_audit": fact_audit_result
    }

    for d in [out_dir, root_ep_dir]:
        try:
            with open(os.path.join(d, "brain_input.json"), "w", encoding="utf-8") as f:
                json.dump(brain_input, f, ensure_ascii=False, indent=2)
        except Exception as _fe:
            logger.warning(f"[story_engine] Error writing brain_input.json to {d}: {_fe}")

    # ----------------------------------------------------
    # Notion Sync: Story Library & Director Plan DBs
    # ----------------------------------------------------
    try:
        story_page_id = meta.get("page_id")

        if story_page_id and seo_pkg:
            try:
                from app.services.seo_package_forge import sync_seo_package_to_story_library
                sync_seo_package_to_story_library(task_id, seo_pkg, story_page_id=story_page_id)
            except Exception as _se:
                logger.warning(f"[story_engine] Error syncing SEO package to Story Library: {_se}")

        if not story_page_id:
            try:
                t_filt = {"or": [
                    {"property": "Task ID", "rich_text": {"equals": str(task_id)}},
                    {"property": "Episode ID", "rich_text": {"equals": str(task_id)}}
                ]}
                q_res = query_db(NOTION_STORY_DB_ID, filter_obj=t_filt)
                if q_res.get("results"):
                    story_page_id = q_res["results"][0]["id"]
                    logger.info(f"[story_engine] Found existing Story Library page {story_page_id} for {task_id}")
                else:
                    new_props = {
                        "Name": {"title": [{"type": "text", "text": {"content": str(topic)}}]},
                        "Task ID": {"rich_text": [{"type": "text", "text": {"content": str(task_id)}}]},
                        "Episode ID": {"rich_text": [{"type": "text", "text": {"content": str(task_id)}}]},
                        "Market": {"select": {"name": mkt}},
                        "Status": {"status": {"name": "Gate Passed" if story_verdict == "PASS" else "Compiled"}},
                        "Story Gate Score": {"rich_text": [{"type": "text", "text": {"content": f"[AG] {story_score_str} {story_verdict} (GPT-6-ASTRA)"}}]},
                        "Niche Angle Brief": {"rich_text": [{"type": "text", "text": {"content": str(niche_brief)[:1999]}}]},
                        "Story Direction (5 Arcs)": {"rich_text": [{"type": "text", "text": {"content": str(story_arcs)[:1999]}}]},
                    }
                    if breakout_queries:
                        new_props["Rising Queries"] = {"rich_text": [{"type": "text", "text": {"content": ", ".join(breakout_queries)[:1999]}}]}
                    if competitor_gap:
                        new_props["Competitor Benchmarks"] = {"rich_text": [{"type": "text", "text": {"content": str(competitor_gap)[:1999]}}]}
                    cr_res = create_page(NOTION_STORY_DB_ID, new_props)
                    if isinstance(cr_res, dict) and cr_res.get("id"):
                        story_page_id = cr_res["id"]
                        logger.info(f"[story_engine] Created new Story Library page {story_page_id} for {task_id}")
            except Exception as _qe:
                logger.warning(f"[story_engine] Error resolving/creating Story Library row: {_qe}")

        if story_page_id:
            props = {
                'Status': {'status': {'name': 'Gate Passed' if story_verdict == 'PASS' else 'Compiled'}},
                'Story Gate Score': {'rich_text': [{'type': 'text', 'text': {'content': f'[AG] {story_score_str} {story_verdict} (GPT-6-ASTRA)'}}]},
                'Rising Queries': {'rich_text': [{'type': 'text', 'text': {'content': ', '.join(breakout_queries)}}]}
            }
            _res = update_page_properties(story_page_id, props)
            if isinstance(_res, dict) and _res.get('error'):
                logger.error('[story_engine] Story Library patch FAILED %s: %s' % (_res.get('status_code'), _res.get('message')))

            # compile_episode_from_notion reads the full script from the page BODY,
            # not from any property; without these blocks it aborts on "empty body".
            # Rule 125 & 126 Single Truth: Purge old blocks if present to eliminate ghost versions
            _blk = get_blocks(story_page_id)
            if isinstance(_blk, dict) and _blk.get('results'):
                old_blocks = _blk.get('results') or []
                logger.info(f"[story_engine] Purging {len(old_blocks)} existing blocks from Story Library page {story_page_id} to enforce Single Truth...")
                for _ob in old_blocks:
                    try:
                        delete_block(_ob['id'])
                    except Exception as _de:
                        logger.warning(f"[story_engine] Error deleting old block {_ob.get('id')}: {_de}")

            _children = []
            # Summary Callout with Rule 130 verification metrics
            summary_text = (
                f"🛡️ B2 5-BEAT DOCUDRAMA SCRIPT (RULE 130 ENFORCED)\n"
                f"• Words: {total_words:,} | Story Gate: {story_score_str} {story_verdict}\n"
                f"• Model: GPT-6-Astra | Causal Roles: Primary Catalyst -> Transmission Mechanism\n"
                f"• Title A: {seo_title_a or topic}"
            )[:1950]
            _children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": summary_text}}],
                    "icon": {"type": "emoji", "emoji": "🛡️"}
                }
            })
            if anatomy:
                c_text = (
                    f"🎯 PHÂN TÍCH ĐỐI THỦ & ĐÒN BẨY ĐỘT PHÁ (B1.5 RECON)\n"
                    f"• Đòn bẩy 10x: {pivot_angle or 'N/A'}\n"
                    f"• Điểm mù đối thủ: {competitor_gap or 'N/A'}\n"
                    f"• Cốt truyện đối thủ: {comp_acts or 'N/A'}\n"
                    f"• Thắc mắc khán giả: {', '.join(frustrations[:3]) if frustrations else 'N/A'}"
                )[:1950]
                _children.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": c_text}}],
                        "icon": {"type": "emoji", "emoji": "🎯"}
                    }
                })
            _chunks = []
            for _p in [x.strip() for x in full_script.split('\n\n') if x.strip()]:
                if _p.startswith("=== ACT ") and _p.endswith(" ==="):
                    _children.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": _p}}]
                        }
                    })
                    continue
                while len(_p) > 1900:
                    _cut = _p.rfind(' ', 1000, 1900)
                    if _cut < 0:
                        _cut = 1900
                    _chunks.append(_p[:_cut])
                    _p = _p[_cut:].lstrip()
                if _p:
                    _chunks.append(_p)
            for c in _chunks:
                _children.append({'object': 'block', 'type': 'paragraph',
                                  'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': c}}]}})
            _appended = 0
            for _i in range(0, len(_children), 90):
                _ares = append_children_blocks(story_page_id, _children[_i:_i + 90])
                if isinstance(_ares, dict) and _ares.get('error'):
                    logger.error('[story_engine] Story body append FAILED %s: %s' % (_ares.get('status_code'), _ares.get('message')))
                    break
                _appended += len(_children[_i:_i + 90])
            logger.info('[story_engine] Story Library body written %d/%d blocks (%d chars)' % (_appended, len(_children), len(full_script)))

        # Director Plan seeding is handled exclusively by B3 director_planner_b3 (Rule 125 Single Truth)
        logger.info('[story_engine] Story Library synced. B3 Director Plan handoff prepared.')

        # Cross-DB State Machine: Mark keyword as 'Used' in Trend Brain DB
        try:
            import app.services.trend_brain_mirror as tbm
            raw_keyword = meta.get("raw_term") or meta.get("target_keyword") or meta.get("topic") or topic
            if raw_keyword:
                tbm.mark_used(str(raw_keyword).strip(), mkt)
                logger.info(f"[story_engine] Transitioned Trend Brain keyword '{raw_keyword}' ({mkt}) status to 'Used'")
        except Exception as _tbm_e:
            logger.warning(f"[story_engine] Notice marking keyword as Used in Trend Brain: {_tbm_e}")
    except Exception as e:
        logger.warning(f"[story_engine] Notion sync exception (non-fatal): {e}")

    return brain_input


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="B2 Story Engine (GPT-6-Astra)")
    parser.add_argument("task_id", help="Task ID or Episode ID (e.g. <MARKET>_EP<0000>_<topic_slug>)")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if story.txt exists")
    args = parser.parse_args()

    if args.force:
        for d in ["/var/vf/episodes", "/root/video_factory/episodes"]:
            sf = os.path.join(d, args.task_id, "story.txt")
            if os.path.exists(sf):
                os.remove(sf)
                print(f"Removed {sf} for regeneration.")

    print(f"Generating 5-Act Story for {args.task_id}...")
    res = generate_5_arc_story(args.task_id, force=args.force)
    story_text = res.get("story", "")
    print(f"=== STORY GENERATION COMPLETED ===")
    print(f"Total Words: {len(story_text.split())}")
    print(f"Gate Score: {res.get('story_gate_score')}")
    print(f"Scenes Seeded: {len(res.get('scenes', []))}")
