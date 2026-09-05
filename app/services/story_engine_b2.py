# app/services/story_engine_b2.py
"""
Generic B2 Story Engine & Dynamic B3 Director Plan Generator via GPT-6-Astra.
Architecture & Rule Compliance:
  - Strict Rule 118: Zero-Mock Data.
  - Strict Rule 120: Safe-Treatment Mandates & Timestamp-Accurate 5-Act Structure.
  - Fast Single-Call 5-Act Generation (~1,200 words total, 8-10 min runtime).
  - Synchronizes seamlessly to Notion Story Library DB & Notion Director Plan DB.
  - Dynamic Rule Injection: Inherits Central Skills (Rules 113–121) and Content Engine Hub
    (5-Act architecture, pacing, and loop discipline) directly from Notion SoT.
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
from scripts.ag_notion_bridge import resolve_id, update_page_properties, create_page, query_db, append_children_blocks, get_blocks
import json as json_lib

NOTION_STORY_DB_ID = os.getenv("STORY_LIBRARY_DB_ID", "b0301989-2400-836b-bdb5-8131fea17736")
EPISODES_BASE_DIR = os.getenv("VF_EPISODES_DIR", "/var/vf/episodes")
PENDING_TASKS_DIR = "/var/vf/pending_tasks"
KNOWN_MARKETS = {"EN", "JP", "KR"}
# Rule 75 subtitle chars-per-second hard cap; mirrors compile_episode_from_notion.py.
# Used only as a physical floor for duration_sec, never to derive it.
CPS_HARD_CAP = 20.0


def _opening_hook(script: str, max_chars: int = 320) -> str:
    """The first 1-2 sentences of the script, whole.

    S3.5 scores this string on its own (app/services/story_quality.py:114):
    a curiosity cue is worth 2.5 and an emotion cue 1.5, and the open question
    that carries both is always the *second* sentence of a shock-then-question
    opening. A fixed character slice cut it off mid-word, so the hook scored
    6.3 against a 7.0 floor no matter how good the script was.
    """
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (script or "").strip()) if s.strip()]
    if not sents:
        return ""
    hook = sents[0]
    for nxt in sents[1:2]:
        if len(hook) + len(nxt) + 1 <= max_chars:
            hook = hook + " " + nxt
    return hook[:max_chars]


def _reuse_slug(text: str, fallback: str) -> str:
    """Short hyphen slug (<=4 words) used as a background/foreground reuse key."""
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return "-".join([w for w in s.split("-") if w][:4]) or fallback


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
        "story_arcs": "Hồi 1 (Hook) -> Hồi 2 (Trỗi dậy) -> Hồi 3 (Xung đột) -> Hồi 4 (Sụp đổ) -> Hồi 5 (Bài học)",
        "niche_brief": f"Cơ chế ngách và sự kiện lịch sử/kinh tế đằng sau {raw_name}.",
        "breakout_queries": [],
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note
    }


def generate_5_arc_story(task_id: str, custom_meta: dict | None = None) -> dict:
    """Generate a complete 5-Act non-fiction script (~1,200 words) using GPT-6-Astra
    enforcing YouTube Safety and Big Fish Small Pond mechanisms in a single optimized pass.
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

    system_prompt = (
        f"You are a World-Class Master Non-Fiction Investigative Documentary Scriptwriter for Video Factory.\n"
        f"Genre: Independent Investigative Docudrama (Phóng sự Điều tra Bất Đối Xứng - Multi-Layer Puzzle).\n"
        f"Narrative Architecture: 5 Beats of Investigative Docudrama:\n"
        f"  - Beat 1 / Act I (The Impossible Contradiction): Opening startling contradiction, quantitative shock (Rule 444 An Ong Hook), opening Core Curiosity Loop.\n"
        f"  - Beat 2 / Act II (The False Narrative & Red Herring): Debunking media myths and superficial competitor angles, exposing misleading clues.\n"
        f"  - Beat 3 / Act III (The Systemic Blindspot & Paper Trail): Forensic evidence, internal memos, audit leaks, and systemic loopholes (Fatal Explanatory Vacuum).\n"
        f"  - Beat 4 / Act IV (The Real Culprit & Smoking Gun): Irrefutable smoking gun evidence, profiting entities unmasked, the structural climax.\n"
        f"  - Beat 5 / Act V (The Uncomfortable Modern Mirror & Living Warning): Loop closure (>=75%), systemic verdict, and contemporary chilling mirror.\n"
        f"Micro-Cliffhangers: Plant an unresolved tension spike every 90-120 seconds throughout the script.\n"
        f"Target Narration Language: {lang_name}.\n"
        f"Total Word Count Target: 1,800 - 2,200 words (~12 to 15 minutes narration at ~150 WPM) across 5 structured Acts.\n"
        f"Structure per Act: Approximately 360-440 words across 3-4 vivid, investigative paragraphs per Act.\n"
        f"Strict Requirement: Scripts under 1,700 words will be rejected by the story gate.\n\n"
        f"{editorial_skills}\n\n"
        f"SPECIFIC CONTEXT FOR THIS SCRIPT:\n"
        f"• Subject / Case: {topic}\n"
        f"• Specific Viral Angle: {viral_angle}\n"
        f"• Core Causal Mechanism: {niche_brief}\n"
        f"• 5-Arc Direction: {story_arcs}\n"
        f"• Content Theme: {theme}\n"
        f"• Breakout Search Queries (Embed in Act 1): {', '.join(breakout_queries[:4])}\n\n"
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
            + "\n".join(f"  - {fr}" for fr in frustrations[:5])
            + "\nYour script must seamlessly and authoritatively answer every single one of these viewer doubts throughout the narrative."
        )
    if competitors:
        context_lines.append("TOP VIRAL COMPETITOR BENCHMARKS (High velocity references):")
        for c in competitors[:5]:
            v_views = c.get("views", 0)
            v_title = c.get("title", "?")
            context_lines.append(f'  - \"{v_title}\" ({v_views:,} views)')
    if intel_card and intel_card.get("audience_comment_gaps"):
        context_lines.append("High-engagement audience comment quotes:")
        for g in intel_card["audience_comment_gaps"][:10]:
            context_lines.append(f"  - [{g.get('likes_count', 0)} likes] {g.get('comment_verbatim', '')[:220]}")

    context_lines.append(
        "🚨 STRICT ZERO COMPETITOR NAME-DROP MANDATE:\n"
        "NEVER mention the names of competitor channels, creators, or rival videos. "
        "Maintain the clinical, objective authority of a premier independent investigative documentary."
    )

    if context_lines:
        competitor_context = "\n".join(context_lines) + "\n\n"

    story_file = os.path.join(out_dir, "story.txt")
    existing_script = ""
    if os.path.exists(story_file):
        try:
            with open(story_file, "r", encoding="utf-8") as sf:
                existing_script = sf.read().strip()
            if len(existing_script.split()) >= 1500:
                logger.info(f"[story_engine] Reusing existing valid story.txt ({len(existing_script.split())} words) for {task_id}.")
        except Exception as e:
            logger.warning(f"[story_engine] Error reading existing story.txt: {e}")

    if existing_script and len(existing_script.split()) >= 1500:
        full_script = existing_script
    else:
        user_prompt = (
            f"Generate the comprehensive 12-15 minute (1,800-2,200 words) Non-Fiction Investigative Documentary Script for {topic} following the 5-Beat Investigative Docudrama structure.\n"
            f"Structure: Beat 1 (The Impossible Contradiction) -> Beat 2 (The False Narrative & Red Herring) -> Beat 3 (The Systemic Blindspot & Paper Trail) -> Beat 4 (The Real Culprit & Smoking Gun) -> Beat 5 (The Uncomfortable Modern Mirror & Living Warning).\n"
            f"Language: {lang_name}.\n"
            f"Core Mechanism: {niche_brief}\n"
            f"5-Arc Narrative: {story_arcs}\n"
            f"Content Theme: {theme}\n"
            f"Breakout Search Queries to prioritize in Act I: {', '.join(breakout_queries)}\n\n"
            f"{competitor_context}"
            f"ACT I OPENING MANDATE (Rule 444 An Ong Hook Protocol): The very first sentence of Act I MUST open with a shock quantitative stake, specific economic contradiction, or irreconcilable conflict. Zero generic preamble or slow historical setup; hook cold-traffic mobile viewers within 5-10 seconds.\n"
            f"Write the full ~1,800-2,200 word script now, adhering strictly to the 5-Act markers:"
        )

        logger.info(f"[story_engine] Calling HHTech GPT-6-Astra for 5-Act Script generation (1,800-2,200 words)...")
        full_script_raw = call_gpt6_astra(user_prompt, system_prompt=system_prompt, max_tokens=4200, timeout=240.0)

        cleaned_acts = []
        act_pattern = re.compile(r'(=== ACT [I|V|X]+ ===.*?)(?=(=== ACT [I|V|X]+ ===|\Z))', re.DOTALL)
        matches = act_pattern.findall(full_script_raw)
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
    story_score_str = f"{audit.get('score', 8)}/{audit.get('max_score', 10)}"
    story_verdict = audit.get('verdict') or 'UNKNOWN'
    logger.info(f"[story_engine] Initial Story Gate Score: {story_score_str} | Verdict: {audit.get('verdict')}")

    # Auto-Refine Self-Correction Loop if Story Gate fails (<80% or banned cliches found)
    if story_verdict != "PASS":
        for refine_attempt in range(1, 3):
            logger.warning(
                f"[story_engine] Story Gate FAILED ({audit.get('score')}/{audit.get('max_score')}). "
                f"Fix hints: {audit.get('fix_hints')}. Banned hits: {audit.get('banned_phrases_found')}. "
                f"Initiating Auto-Refine Attempt {refine_attempt}/2 via GPT-6-Astra..."
            )
            refine_user = (
                f"The generated script failed our quality gate (Score: {audit.get('score')}/{audit.get('max_score')}).\n"
                f"REQUIRED CORRECTIONS:\n" + "\n".join(f"- {h}" for h in audit.get("fix_hints", [])) + "\n\n"
                f"BANNED PHRASES FOUND (MUST ELIMINATE): {', '.join(audit.get('banned_phrases_found', []))}\n\n"
                f"Please rewrite and polish the entire 5-Act script, strictly maintaining 1,800-2,200 words, "
                f"preserving all 5 Acts ('=== ACT I ===' to '=== ACT V ==='), ensuring the first sentence opens with a shock quantitative stake (Rule 444), and resolving all failed items.\n\n"
                f"Current Draft:\n{full_script}\n\n"
                f"Output ONLY the corrected 5-Act script now:"
            )
            try:
                refined_raw = call_gpt6_astra(refine_user, system_prompt=system_prompt, max_tokens=4200, timeout=240.0)
                if refined_raw and len(refined_raw.split()) >= 1000:
                    cleaned_acts_ref = []
                    matches_ref = act_pattern.findall(refined_raw)
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
                    if story_verdict == "PASS":
                        logger.info(f"[story_engine] Auto-Refine SUCCESS on attempt {refine_attempt}!")
                        break
            except Exception as _re:
                logger.warning(f"[story_engine] Auto-refine attempt {refine_attempt} error: {_re}")

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
        "hook_3s": _opening_hook(full_script),
        "breakout_queries": breakout_queries,
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note,
        "scenes": scenes,
        "total_scenes": len(scenes),
        "render_architecture": "two_layer_v1"
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
        director_db_id = resolve_id('director')
        story_page_id = meta.get("page_id")

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
                        "Story Gate Score": {"rich_text": [{"type": "text", "text": {"content": f"[AG] {story_score_str} {story_verdict} (GPT-5.6-SOL)"}}]},
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
                'Story Gate Score': {'rich_text': [{'type': 'text', 'text': {'content': f'[AG] {story_score_str} {story_verdict} (GPT-5.6-SOL)'}}]},
                'Rising Queries': {'rich_text': [{'type': 'text', 'text': {'content': ', '.join(breakout_queries)}}]}
            }
            _res = update_page_properties(story_page_id, props)
            if isinstance(_res, dict) and _res.get('error'):
                logger.error('[story_engine] Story Library patch FAILED %s: %s' % (_res.get('status_code'), _res.get('message')))

            # compile_episode_from_notion reads the full script from the page BODY,
            # not from any property; without these blocks it aborts on "empty body".
            _blk = get_blocks(story_page_id)
            _has_body = False
            if isinstance(_blk, dict):
                for _b in (_blk.get('results') or []):
                    _bt = _b.get('type')
                    if _bt in ('paragraph', 'heading_1', 'heading_2', 'heading_3', 'quote', 'callout'):
                        if ''.join(t.get('plain_text', '') for t in _b.get(_bt, {}).get('rich_text', [])).strip():
                            _has_body = True
                            break
            if _has_body:
                logger.info('[story_engine] Story Library body already present, skip append')
            else:
                _children = []
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
    except Exception as e:
        logger.warning(f"[story_engine] Notion sync exception (non-fatal): {e}")

    return brain_input


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="B2 Story Engine (GPT-6-Astra)")
    parser.add_argument("task_id", help="Task ID or Episode ID (e.g. KR_EP0001_pesticide-trust-crisis)")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if story.txt exists")
    args = parser.parse_args()

    if args.force:
        for d in ["/var/vf/episodes", "/root/video_factory/episodes"]:
            sf = os.path.join(d, args.task_id, "story.txt")
            if os.path.exists(sf):
                os.remove(sf)
                print(f"Removed {sf} for regeneration.")

    print(f"Generating 5-Act Story for {args.task_id}...")
    res = generate_5_arc_story(args.task_id)
    story_text = res.get("story", "")
    print(f"=== STORY GENERATION COMPLETED ===")
    print(f"Total Words: {len(story_text.split())}")
    print(f"Gate Score: {res.get('story_gate_score')}")
    print(f"Scenes Seeded: {len(res.get('scenes', []))}")
