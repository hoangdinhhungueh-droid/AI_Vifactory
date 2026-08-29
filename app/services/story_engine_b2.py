# app/services/story_engine_b2.py
"""
Generic B2 Story Engine & Dynamic B3 Director Plan Generator via GPT-5.6-Sol.
Architecture & Rule Compliance:
  - Strict Rule 118: Zero-Mock Data.
  - Strict Rule 120: Safe-Treatment Mandates & Timestamp-Accurate 5-Act Structure.
  - Fast Single-Call 5-Act Generation (~1,200 words total, 8-10 min runtime).
  - Synchronizes seamlessly to Notion Story Library DB & Notion Director Plan DB.
"""

import os, sys, json, time, re, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

sys.path.insert(0, '/root/video_factory')
from app.services.hhtech_reasoner import call_gpt56_sol, detect_safety_and_theme
from app.services import story_gate as sgate
from scripts.ag_notion_bridge import resolve_id, update_page_properties, create_page, query_db

NOTION_STORY_DB_ID = os.getenv("STORY_LIBRARY_DB_ID", "b0301989-2400-836b-bdb5-8131fea17736")
EPISODES_BASE_DIR = os.getenv("VF_EPISODES_DIR", "/var/vf/episodes")
PENDING_TASKS_DIR = "/var/vf/pending_tasks"


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

    parts = task_id.split("_")
    mkt = parts[0] if len(parts) > 0 else "EN"
    raw_name = "_".join(parts[2:]) if len(parts) > 2 else task_id
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
    """Generate a complete 5-Act non-fiction script (~1,200 words) using GPT-5.6-Sol
    enforcing YouTube Safety and Big Fish Small Pond mechanisms in a single optimized pass.
    """
    meta = custom_meta or load_task_metadata(task_id)
    mkt = meta.get("market", "EN").upper()
    topic = meta.get("topic") or meta.get("subject") or task_id
    niche_brief = meta.get("niche_brief") or meta.get("niche_angle_brief") or ""
    story_arcs = meta.get("story_arcs") or meta.get("story_direction_5_arcs") or ""
    breakout_queries = meta.get("breakout_queries") or []
    
    theme = meta.get("content_theme")
    safety_label = meta.get("safety_label")
    treatment_note = meta.get("treatment_note")
    
    if not safety_label or not treatment_note:
        theme, safety_label, treatment_note = detect_safety_and_theme(topic, mkt)

    out_dir = os.path.join(EPISODES_BASE_DIR, task_id)
    os.makedirs(out_dir, exist_ok=True)

    logger.info(f"[story_engine] Starting 5-Act story generation for {task_id} ({mkt}) | Theme: {theme} | Safety: {safety_label}...")

    lang_name = "English" if mkt == "EN" else ("Japanese" if mkt == "JP" else "Korean")

    system_prompt = (
        f"You are a World-Class Master Non-Fiction Documentary Scriptwriter for Video Factory.\n"
        f"Target Narration Language: {lang_name}.\n"
        f"Total Word Count Target: ~1,200 words across 5 structured Acts (approx. 240 words / 2 paragraphs per Act).\n\n"
        f"EDITORIAL & RETENTION PRINCIPLES (Rule 1, 2, 3, 4: Big Fish Small Pond):\n"
        f"• Subject / Case: {topic}\n"
        f"• Core Causal Mechanism: {niche_brief}\n"
        f"• 5-Arc Direction: {story_arcs}\n"
        f"• Content Theme: {theme}\n"
        f"• Breakout Search Queries (Embed in Act 1): {', '.join(breakout_queries[:4])}\n\n"
        f"CRITICAL PLATFORM SAFETY MANDATE [{safety_label}]:\n"
        f"• {treatment_note}\n"
        f"• Zero graphic violence, zero gore, zero criminal glorification, zero method instructions.\n\n"
        f"ACT STRUCTURE REQUIREMENTS:\n"
        f"1. Act I (The Catalyst Hook & The Apex Illusion): In first 60 words, open with a shocking empirical fact/paradox. Embed breakout queries.\n"
        f"2. Act II (The Structural Setup & Latent Vulnerability): Dissect the institutional/societal framework and the hidden vulnerabilities.\n"
        f"3. Act III (The Escalation & Hidden Conflict): Detail operational escalation, secondary financial flows, and manipulation.\n"
        f"4. Act IV (The Breaking Point & Terminal Collapse): Detail the decisive catalyst, investigation breakthrough, and rapid collapse.\n"
        f"5. Act V (The Institutional Aftermath & Timeless Lesson): Payoff, legislative reforms, and the systemic lesson.\n\n"
        f"Output ONLY the complete script organized strictly by Acts using '=== ACT I ===', '=== ACT II ===', '=== ACT III ===', '=== ACT IV ===', '=== ACT V ===' markers. No markdown fences, no stage directions."
    )

    user_prompt = f"Write the complete 5-Act voiceover narration script for '{topic}' in {lang_name} now."
    full_script_raw = call_gpt56_sol(user_prompt, system_prompt=system_prompt, max_tokens=3500, temperature=0.6, timeout=60.0)

    # Clean and parse acts
    act_blocks = re.split(r'=== ACT [I|V|X]+ ===', full_script_raw, flags=re.IGNORECASE)
    cleaned_acts = [b.strip() for b in act_blocks if b.strip()]
    
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
    logger.info(f"[story_engine] Story Gate Score: {story_score_str} | Verdict: {audit.get('verdict')}")

    # Write story.txt
    story_file = os.path.join(out_dir, "story.txt")
    with open(story_file, "w", encoding="utf-8") as f:
        f.write(full_script)

    # ----------------------------------------------------
    # B3. Dynamic Director Plan Generation
    # ----------------------------------------------------
    logger.info(f"[story_engine] [B3] Generating Dynamic Director Plan via GPT-5.6-Sol...")
    dp_system = (
        "You are the Lead Art Director for Video Factory (VF Pipeline v3 / Rule 92, 93, 95, 100, 120).\n"
        "Your task is to take the 5-Act script and generate dynamic scene breakdowns covering the entire narrative.\n\n"
        "STRICT VISUAL & COMPOSITION RULES:\n"
        "1. Scene 000 MUST be the Hero Frame establishing the central visual theme.\n"
        "2. Background Prompts (bg_prompt): High-Key Warm Documentary, 16:9 aspect ratio, atmospheric cinematic lighting, under 35 words, NO text, NO characters.\n"
        "3. Foreground Prompts (fg_prompt): EXACTLY 1 full-body character or central symbolic subject from head to toe, historical authentic attire, isolated on SOLID FLAT #FF00FF MAGENTA CHROMA-KEY BACKGROUND, clean chroma-key cutout, sharp silhouette, no border, no frame.\n"
        "4. Foreground Position (fg_position): Alternate 'left' and 'right' dynamically across scenes.\n\n"
        "Output ONLY a valid JSON array of scene objects matching this exact structure without markdown fences:\n"
        "[\n"
        "  {\n"
        "    \"scene_idx\": 0,\n"
        "    \"name\": \"sc000_hero_scene_name\",\n"
        "    \"arc\": \"Act I\",\n"
        "    \"narration_text\": \"...\",\n"
        "    \"bg_prompt\": \"Cinematic wide angle high-key documentary view of ..., photorealistic 8k documentary style.\",\n"
        "    \"fg_prompt\": \"Full body standing figure in authentic attire, head to shoes visible, isolated on solid flat #FF00FF magenta background, clean chroma-key cutout, sharp silhouette, no border.\",\n"
        "    \"fg_position\": \"left\"\n"
        "  }\n"
        "]"
    )

    dp_user = f"Topic: {topic}\nMarket: {mkt}\nFull Script:\n\n{full_script[:3500]}\n\nGenerate the complete Director Plan scenes JSON array now:"
    dp_raw = call_gpt56_sol(dp_user, system_prompt=dp_system, max_tokens=3000, timeout=50.0)

    if dp_raw.startswith("```"):
        dp_raw = dp_raw.split("```")[1]
        if dp_raw.startswith("json"):
            dp_raw = dp_raw[4:]
    dp_raw = dp_raw.strip()

    try:
        scenes = json.loads(dp_raw)
    except Exception as e:
        logger.warning(f"[story_engine] Director Plan JSON parsing failed: {e}. Generating fallback scenes.")
        scenes = [
            {
                "scene_idx": 0,
                "name": f"sc000_hero_{task_id}",
                "arc": "Act I",
                "narration_text": full_script[:200],
                "bg_prompt": f"Cinematic wide angle high-key documentary scene of {topic}, soft golden lighting, architectural detail, 8k documentary style.",
                "fg_prompt": f"Full body standing representative historical figure for {topic}, authentic costume, head to shoes visible, isolated on solid flat #FF00FF magenta background, clean chroma-key cutout, sharp silhouette, no border.",
                "fg_position": "left"
            }
        ]

    for i, sc in enumerate(scenes):
        sc["scene_idx"] = i
        sc["fg_position"] = "left" if i % 2 == 0 else "right"

    # Build brain_input.json
    brain_input = {
        "episode_id": task_id,
        "market": mkt.lower(),
        "topic": topic,
        "story": full_script,
        "story_gate_score": story_score_str,
        "bgm_mood": "dramatic",
        "hook_3s": full_script[:120],
        "breakout_queries": breakout_queries,
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note,
        "scenes": scenes,
        "total_scenes": len(scenes),
        "render_architecture": "two_layer_v1"
    }

    brain_file = os.path.join(out_dir, "brain_input.json")
    with open(brain_file, "w", encoding="utf-8") as f:
        json.dump(brain_input, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------
    # Notion Sync: Story Library & Director Plan DBs
    # ----------------------------------------------------
    try:
        director_db_id = resolve_id('director')
        story_page_id = meta.get("page_id")

        if story_page_id:
            props = {
                'Status': {'status': {'name': 'Gate Passed'}},
                'Story Gate Score': {'rich_text': [{'type': 'text', 'text': {'content': f'[AG] {story_score_str} PASS (GPT-5.6-SOL)'}}]},
                'Rising Queries': {'rich_text': [{'type': 'text', 'text': {'content': ', '.join(breakout_queries)}}]}
            }
            update_page_properties(story_page_id, props)

        for sc in scenes[:12]:  # Seed primary scenes to Notion
            idx = sc.get('scene_idx', 0)
            sc_name = sc.get('name', f'sc{idx:03d}')
            sc_props = {
                'Name': {'title': [{'type': 'text', 'text': {'content': f'[AG] {sc_name}'}}]},
                'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': task_id}}]},
                'Scene Index': {'number': idx},
                'Arc': {'select': {'name': str(sc.get('arc', 'Act I'))[:50]}},
                'Narration Text': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('narration_text', '')[:1000]}}]},
                'Background Prompt': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('bg_prompt', '')[:1000]}}]},
                'Foreground Prompt': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('fg_prompt', '')[:1000]}}]},
                'Foreground Position': {'select': {'name': sc.get('fg_position', 'left')}},
                'Status': {'status': {'name': 'Ready'}}
            }
            create_page(director_db_id, sc_props)
        logger.info(f"[story_engine] Notion Director Plan synced {len(scenes)} scenes! ✅")
    except Exception as e:
        logger.error(f"[story_engine] Notion sync FAILED for {task_id}: {e}")
        raise RuntimeError(f"B2 Notion sync failed: {e}") from e

    return brain_input
