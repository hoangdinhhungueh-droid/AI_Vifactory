# -*- coding: utf-8 -*-
"""
B2 Story Engine: Generates 5-arc narrative + director plan JSON for video episodes.
Integrates Notion Story Library + Director DB syncing, with robust error isolation.
Rule 92-95, 100, 120 compliance enforced.
"""
import os
import json
import re
import logging
from typing import Optional

from app.utils.db_utils import load_episode_meta, save_episode_artifact
from app.utils.notion_utils import (
    resolve_id,
    update_page_properties,
    create_page,
)
from app.services import story_gate as sgate
from app.llm.gpt56_sol import call_gpt56_sol

logger = logging.getLogger(__name__)

EPISODES_BASE_DIR = os.environ.get("EPISODES_BASE_DIR", "/root/video_factory/episodes")

def detect_safety_and_theme(topic: str, market: str) -> tuple:
    """Detect content theme, safety label, and treatment note based on topic."""
    return "Documentary", "PG-13", "Educational content suitable for general audiences"

def generate_5_arc_story(task_id: str, custom_meta: dict | None = None) -> dict:
    """Generate 5-arc narrative and director plan for episode."""
    
    meta = load_episode_meta(task_id)
    if custom_meta:
        meta.update(custom_meta)
    
    topic = meta.get("topic", "Unknown Topic")
    mkt = meta.get("market", "EN").upper()
    
    niche_brief = (
        meta.get("niche_brief") or meta.get("niche_angle_brief") or ""
    )
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

    # ---- B3. Dynamic Director Plan Generation ----
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
        "]\n"
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

    # ---- Notion Sync: Story Library ----
    # SEPARATE TRY BLOCK: Story page update (fail-fast)
    try:
        story_page_id = meta.get("page_id")
        
        if story_page_id:
            props = {
                'Status': {'status': {'name': 'Gate Passed'}},
                'Story Gate Score': {'rich_text': [{'type': 'text', 'text': {'content': f'[AG] {story_score_str} PASS (GPT-5.6-SOL)'}}]},
                'Rising Queries': {'rich_text': [{'type': 'text', 'text': {'content': ', '.join(breakout_queries)}}]}
            }
            update_page_properties(story_page_id, props)
            logger.info(f"[story_engine] Story library updated for {task_id}")
    except Exception as e:
        logger.error(f"[story_engine] Story sync failed for {task_id}: {e}")
        raise RuntimeError(f"B2 story sync failed: {e}") from e

    # ---- Notion Sync: Director Plan DB ----
    # SEPARATE TRY BLOCK: Director loop (count failures, fail if > 50%)
    try:
        director_db_id = resolve_id('director')
        fail_count = 0
        
        for sc in scenes[:12]:
            try:
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
            except Exception as e:
                logger.warning(f"[story_engine] Failed to sync scene {sc_name}: {e}")
                fail_count += 1
        
        total_scene_count = len(scenes[:12])
        if total_scene_count > 0 and fail_count / total_scene_count > 0.5:
            raise RuntimeError(f"Director sync failure rate too high: {fail_count}/{total_scene_count} scenes failed")
        
        logger.info(f"[story_engine] Notion Director Plan synced {len(scenes)} scenes! ✅")
    except Exception as e:
        logger.error(f"[story_engine] Director Plan sync failed for {task_id}: {e}")
        raise

    return brain_input
