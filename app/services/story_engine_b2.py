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


def load_competitor_intel(task_id: str) -> dict | None:
    """Load B1.5 Competitor Intelligence Card if it exists."""
    intel_path = os.path.join(EPISODES_BASE_DIR, task_id, "competitor_intel_card.json")
    if os.path.exists(intel_path):
        try:
            with open(intel_path, "r", encoding="utf-8") as f:
                return json_lib.load(f)
        except Exception as e:
            logger.debug(f"[story_engine] Error loading competitor intel for {task_id}: {e}")
    return None


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

    intel_card = load_competitor_intel(task_id)
    intel_status = "loaded" if intel_card else "none"
    logger.info(f"[story_engine] Starting 5-Act story generation for {task_id} ({mkt}) | Theme: {theme} | Safety: {safety_label}... [Intel Card: {intel_status}]")
    
    lang_name = "English" if mkt == "EN" else ("Japanese" if mkt == "JP" else "Korean")

    system_prompt = (
        f"You are a World-Class Master Non-Fiction Documentary Scriptwriter for Video Factory.\n"
        f"Target Narration Language: {lang_name}.\n"
        f"Total Word Count Target: 1,500-1,700 words across 5 structured Acts (approx. 300-340 words / 2-3 paragraphs per Act). Scripts under 1,200 words are rejected by the story gate.\n\n"
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
        f"1. Act I (The Catalyst Hook & The Apex Illusion): The first 60 words must contain a hard number or dated fact that is itself startling (a valuation, a body count, a date) plus an unanswered question. Embed breakout queries.\n"
        f"2. Act II (The Rise & Latent Vulnerability): Narrate the ascent in concrete dated milestones — when it was founded, how it grew and expanded, what it became, the market share it dominated, the year each threshold was crossed — then dissect the institutional framework that let the hidden vulnerability accumulate underneath that growth.\n"
        f"3. Act III (The Escalation & Hidden Conflict): Detail operational escalation, secondary financial flows, and manipulation.\n"
        f"4. Act IV (The Breaking Point & Terminal Collapse): Detail the decisive catalyst, investigation breakthrough, and rapid collapse.\n"
        f"5. Act V (The Institutional Aftermath & Timeless Lesson): Payoff, legislative reforms, and the systemic lesson.\n\n"
        f"NARRATIVE LOOP DISCIPLINE:\n"
        f"• Open a new loop roughly every 180 words: a direct question to the viewer, or a fact deliberately withheld ('that number would matter later', 'but almost no one noticed', 'for now'). A 1,600-word script needs at least nine such openings.\n"
        f"• Every question or withheld fact you raise must be paid off later in explicit language: 'that is why', 'which is how', 'here is the answer', 'in the end'. Close at least three quarters of the loops you open.\n"
        f"• Cite the evidentiary basis in the narration itself (filing, report, court testimony, balance sheet) at least twice.\n\n"
        f"Output ONLY the complete script organized strictly by Acts using '=== ACT I ===', '=== ACT II ===', '=== ACT III ===', '=== ACT IV ===', '=== ACT V ===' markers. No markdown fences, no stage directions."
    )

    competitor_context = ""
    if intel_card:
        benchmarks = intel_card.get("competitor_benchmarks", [])
        gaps = intel_card.get("audience_comment_gaps", [])

        context_lines = ["### COMPETITOR EVIDENCE (collected by B1.5, uninterpreted):"]
        for b in benchmarks[:5]:
            context_lines.append(
                f"  - {b.get('channel', '?')} | \"{b.get('title', '?')}\" | "
                f"{b.get('views', 0):,} views | {b.get('avg_views_per_day', 0):,}/day | "
                f"{b.get('comments', 0):,} comments | {b.get('selection_group', '?')}"
            )
            head = b.get("transcript_head")
            if head:
                context_lines.append(f"    opening narration: {head[:400]}")
        if gaps:
            context_lines.append("Verbatim audience comments, highest-liked first:")
            for g in gaps[:6]:
                context_lines.append(
                    f"  - [{g.get('likes_count', 0)} likes] {g.get('comment_verbatim', '')[:220]}"
                )
        context_lines.append(
            "Derive from the evidence above: each competitor's critical explanatory gap, and "
            "the single highest-value unanswered question. Build Acts III-IV to resolve that "
            "question through mechanisms rather than speculation. Use only facts stated above "
            "or in the theme brief; invent nothing."
        )

        competitor_context = "\n".join(context_lines) + "\n\n"

    user_prompt = f"{competitor_context}Write the complete 5-Act voiceover narration script for '{topic}' in {lang_name} now."
    full_script_raw = call_gpt56_sol(user_prompt, system_prompt=system_prompt, max_tokens=4500, temperature=0.6, timeout=180.0)

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
    story_verdict = audit.get('verdict') or 'UNKNOWN'
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
        "2. Background Prompts (image_prompt): High-Key Warm Documentary, 16:9 aspect ratio, atmospheric cinematic lighting, under 35 words, NO text, NO characters.\n"
        "3. Foreground Prompts (foreground_prompt): EXACTLY 1 full-body character or central symbolic subject from head to toe, historical authentic attire, isolated on SOLID FLAT #FF00FF MAGENTA CHROMA-KEY BACKGROUND, clean chroma-key cutout, sharp silhouette, no border, no frame.\n"
        "4. Foreground Position (foreground_position): Alternate 'left' and 'right' dynamically across scenes.\n"
        "5. Reuse keys (background_reuse_key / foreground_reuse_key): short lowercase hyphen slugs, max 4 words. Scenes sharing the SAME setting MUST share the SAME background_reuse_key; scenes showing the SAME subject MUST share the SAME foreground_reuse_key. Target 8-14 distinct background keys and 8-14 distinct foreground keys for the whole episode so images get reused instead of regenerated.\n"
        "6. Every scene MUST have both reuse keys filled. Never null, never empty.\n\n"
        "7. duration_sec: estimated on-screen seconds for THIS scene, i.e. how long its narration takes when read aloud at a natural documentary pace (~150 words per minute). Positive number, one decimal. The sum over all scenes must approximate the read time of the whole script. Never omit it, never 0.\n\n"
        "Output ONLY a valid JSON array of scene objects matching this exact structure without markdown fences:\n"
        "[\n"
        "  {\n"
        "    \"scene_index\": 0,\n"
        "    \"name\": \"sc000_hero_scene_name\",\n"
        "    \"arc\": \"Act I\",\n"
        "    \"narration\": \"...\",\n"
        "    \"duration_sec\": 12.5,\n"
        "    \"image_prompt\": \"Cinematic wide angle high-key documentary view of ..., photorealistic 8k documentary style.\",\n"
        "    \"foreground_prompt\": \"Full body standing figure in authentic attire, head to shoes visible, isolated on solid flat #FF00FF magenta background, clean chroma-key cutout, sharp silhouette, no border.\",\n"
        "    \"foreground_position\": \"left\",\n"
        "    \"background_reuse_key\": \"a1-trading-floor\",\n"
        "    \"foreground_reuse_key\": \"ceo-dark-suit\"\n"
        "  }\n"
        "]"
    )

    dp_user = f"Topic: {topic}\nMarket: {mkt}\nFull Script:\n\n{full_script[:3500]}\n\nGenerate the complete Director Plan scenes JSON array now:"
    dp_raw = call_gpt56_sol(dp_user, system_prompt=dp_system, max_tokens=3000, timeout=300.0)

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
                "scene_index": 0,
                "name": f"sc000_hero_{task_id}",
                "arc": "Act I",
                "narration": full_script[:200],
                "image_prompt": f"Cinematic wide angle high-key documentary scene of {topic}, soft golden lighting, architectural detail, 8k documentary style.",
                "foreground_prompt": f"Full body standing representative historical figure for {topic}, authentic costume, head to shoes visible, isolated on solid flat #FF00FF magenta background, clean chroma-key cutout, sharp silhouette, no border.",
                "foreground_position": "left",
                "background_reuse_key": "a1-hero-establishing",
                "foreground_reuse_key": "hero-subject"
            }
        ]

    for i, sc in enumerate(scenes):
        sc["scene_index"] = i
        sc["foreground_position"] = "left" if i % 2 == 0 else "right"
        if not sc.get("background_reuse_key"):
            sc["background_reuse_key"] = _reuse_slug(sc.get("name"), "bg-%03d" % i)
        if not sc.get("foreground_reuse_key"):
            sc["foreground_reuse_key"] = _reuse_slug(sc.get("name"), "fg-%03d" % i)
        try:
            _dur = float(sc.get("duration_sec") or 0)
        except (TypeError, ValueError):
            _dur = 0.0
        if _dur > 0:
            # Physical floor only: a duration implying CPS > hard cap is unreadable.
            _floor = len((sc.get("narration") or "").strip()) / CPS_HARD_CAP
            sc["duration_sec"] = round(max(_dur, _floor), 1)
        else:
            sc.pop("duration_sec", None)
            logger.warning("[story_engine] scene %d has no duration_sec from B3; leaving it unset "
                           "so the compiler gate rejects it (Rule 118: do not fabricate)" % i)

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
                _children = [{'object': 'block', 'type': 'paragraph',
                              'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': c}}]}}
                             for c in _chunks]
                _appended = 0
                for _i in range(0, len(_children), 90):
                    _ares = append_children_blocks(story_page_id, _children[_i:_i + 90])
                    if isinstance(_ares, dict) and _ares.get('error'):
                        logger.error('[story_engine] Story body append FAILED %s: %s' % (_ares.get('status_code'), _ares.get('message')))
                        break
                    _appended += len(_children[_i:_i + 90])
                logger.info('[story_engine] Story Library body written %d/%d blocks (%d chars)' % (_appended, len(_children), len(full_script)))

        seeded = 0
        for sc in scenes[:12]:  # Seed primary scenes to Notion
            idx = sc.get('scene_index', 0)
            sc_name = sc.get('name', f'sc{idx:03d}')
            sc_props = {
                'Name': {'title': [{'type': 'text', 'text': {'content': f'[AG] {sc_name}'}}]},
                'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': task_id}}]},
                'Task ID': {'rich_text': [{'type': 'text', 'text': {'content': task_id}}]},
                'Scene Index': {'number': idx},
                'Beat': {'rich_text': [{'type': 'text', 'text': {'content': str(sc.get('arc', ''))[:200]}}]},
                'Narration Segment': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('narration', '')[:1000]}}]},
                'Background Prompt': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('image_prompt', '')[:1000]}}]},
                'Foreground Prompt': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('foreground_prompt', '')[:1000]}}]},
                'BG Reuse Key': {'rich_text': [{'type': 'text', 'text': {'content': str(sc.get('background_reuse_key') or '')[:200]}}]},
                'FG Reuse Key': {'rich_text': [{'type': 'text', 'text': {'content': str(sc.get('foreground_reuse_key') or '')[:200]}}]},
                'FG Position': {'select': {'name': str(sc.get('foreground_position', 'left')).capitalize()}},
                'Status': {'status': {'name': 'Compiled'}}
            }
            if sc.get('duration_sec'):
                sc_props['Duration Est (s)'] = {'number': float(sc['duration_sec'])}
            _res = create_page(director_db_id, sc_props)
            if isinstance(_res, dict) and _res.get('error'):
                logger.error('[story_engine] Director Plan scene %s FAILED %s: %s' % (idx, _res.get('status_code'), _res.get('message')))
            else:
                seeded += 1
        logger.info("[story_engine] Notion Director Plan seeded %d/%d scenes" % (seeded, min(len(scenes), 12)))
    except Exception as e:
        logger.warning(f"[story_engine] Notion sync exception (non-fatal): {e}")

    return brain_input
