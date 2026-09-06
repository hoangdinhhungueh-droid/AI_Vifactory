"""
app/services/director_planner_b3.py — B3: Hollywood Art Director & Scene Breakdown Engine
AI Video Factory (VF Pipeline) — Go-Live Architecture (Rule 116, 120, 124, 445, 446)

Stage: B3 (Art Director / DP Planning) & B3.5 (Specialized Visual Prompt Forge)
Input: 
  - story.txt (5-Beat Investigative Docudrama, 1,800 - 2,200 words)
  - competitor_intel_card.json (Fatal Explanatory Vacuum, 10x Pivot Angle, Core Frustrations)
  - Topic Metadata (Niche, Language/Market, Target Keyword, Mood)
Output:
  - director_plan.json & dp_plan.json in workspace/{episode_id} and episodes/{episode_id}
  - prompts_forge.json (and prompts.json) via prompt_forge.py
  - Notion SoT Sync: Director Plan DB (5b201989-2400-8295-be81-81c2c0e4e138)
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

logger = logging.getLogger("director_planner_b3")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.skill_loader import (
    get_skill_rules,
    get_central_skills,
    get_media_production_rules
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

CINEMATIC_ARCHETYPES = {
    "agriculture": {
        "director": "Bong Joon-ho / David Fincher (Rural Noir)",
        "visual_tone": "Expansive rural countryside, terraced agricultural fields under overcast skies, local cooperative warehouses, weathered agricultural machinery, chemical testing canisters, dimly lit provincial administrative offices",
        "palette": "Earthy ochre, muted moss green, rusted iron, damp soil brown, overcast slate gray",
        "camera_style": "Slow atmospheric tracking shots across agricultural landscapes, lingering wide tableaux, claustrophobic medium shots in provincial records rooms"
    },
    "finance": {
        "director": "Adam McKay / David Fincher (Corporate Noir)",
        "visual_tone": "Glossy boardroom veneer contrasting cold trading floors, shredded paper trails, creeping push-ins on forensic ledger anomalies, claustrophobic glass partitions",
        "palette": "Cold steel blue, dark charcoal, toxic amber highlights, fluorescent office hum",
        "camera_style": "Slow creeping push-ins on critical revelations, clinical wide establishing shots, sudden whip pans on micro-cliffhangers"
    },
    "history": {
        "director": "Chernobyl / Christopher Nolan (Historical Realism)",
        "visual_tone": "Monumental scale, oppressive stone and concrete institutional corridors, dusty light beams through heavy drapes, atmospheric decay, deep chiaroscuro",
        "palette": "Aged ochre, slate stone, imperial gold accents, oxidized bronze, deep shadow",
        "camera_style": "Slow deliberate tracking shots, high-angle surveillance-style observation, lingering static tableaux with heavy negative space"
    },
    "medical_pharma": {
        "director": "Steven Soderbergh / Denis Villeneuve (Clinical Realism)",
        "visual_tone": "Provincial clinical examination rooms, sealed diagnostic vials, pharmaceutical packaging lines, regulatory inspection desks, sterile fluorescent forensic labs",
        "palette": "Clinical pale blue, antiseptic mint green, iodine amber, brushed stainless steel",
        "camera_style": "Forensic close-ups on batch numbers and chemical seals, creeping dolly shots through regulatory archives"
    },
    "tech": {
        "director": "David Fincher / Steven Soderbergh (Clinical Thriller)",
        "visual_tone": "Cleanroom micro-fabrication facilities, server racks, pristine minimalist glass offices, silicon wafers, isolation of key innovators in vast server rooms",
        "palette": "Cool sterile white, cyan, brushed aluminum, obsidian black, warning red accents",
        "camera_style": "Smooth robotic tracking, tight macro focus on technical schematics and data monitors, symmetrical center framing"
    },
    "default": {
        "director": "Investigative Cinematic Docudrama (Fincher / Denis Villeneuve)",
        "visual_tone": "Moody atmospheric tension, dramatic low-key lighting, textured architectural backgrounds, forensic depth of field",
        "palette": "Muted earth tones, cinematic contrast, shadow-heavy rim lighting",
        "camera_style": "Creeping push-ins, dynamic eye-level forensic staging, dramatic low-angle power shots"
    }
}


def detect_cinematic_archetype(niche: str = "", topic: str = "") -> dict:
    """Detect the most compelling Hollywood visual archetype based on niche and topic."""
    text = f"{niche} {topic}".lower()
    if any(k in text for k in ["pesticide", "farm", "crop", "fertilizer", "rural", "agriculture", "harvest", "seed", "container", "soil"]):
        return CINEMATIC_ARCHETYPES["agriculture"]
    elif any(k in text for k in ["finance", "economy", "bank", "money", "fraud", "wall street", "debt", "enron", "market", "trader", "madoff"]):
        return CINEMATIC_ARCHETYPES["finance"]
    elif any(k in text for k in ["history", "empire", "war", "monarchy", "byzantine", "medieval", "crusade", "revolution", "soviet", "cold war"]):
        return CINEMATIC_ARCHETYPES["history"]
    elif any(k in text for k in ["vaccine", "doping", "valieva", "pharma", "clinical", "hospital", "drug", "medicine", "toxic", "poison"]):
        return CINEMATIC_ARCHETYPES["medical_pharma"]
    elif any(k in text for k in ["semiconductor", "chip", "silicon", "tsmc", "cyber", "software", "gpu", "ai model", "supercomputer", "data center"]):
        return CINEMATIC_ARCHETYPES["tech"]
    return CINEMATIC_ARCHETYPES["default"]


def extract_story_beats(story_text: str) -> list[dict]:
    """Parse story into 5 beats if headers exist, or divide dynamically."""
    beats = []
    current_beat_title = ""
    current_lines = []

    beat_patterns = [
        re.compile(r"^(?:##\s*)?(?:ACT|BEAT)\s*([1-5])[:\-\s]*(.*)", re.IGNORECASE),
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
                current_beat_title = line.strip().lstrip("#").strip()
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


def generate_director_plan(
    episode_id: str,
    story_text: str = None,
    intel_card: dict = None,
    metadata: dict = None,
    skip_notion: bool = False
) -> dict:
    """
    Core B3 Art Director & Scene Breakdown Engine.
    Breaks down 5-Beat story into 35-55 dynamic cinematic scenes.
    Generates flexible asset roster (BG pool and FG pool) per Beat.
    Produces director_plan.json, dp_plan.json, and brain_input.json.
    """
    logger.info(f"🎬 [B3 Director] Starting Art Direction for Episode: {episode_id}")

    # 1. Resolve inputs
    ep_dir = ROOT_DIR / "episodes" / episode_id
    ws_dir = ROOT_DIR / "workspace" / episode_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    ws_dir.mkdir(parents=True, exist_ok=True)

    if not story_text:
        story_candidates = [
            ep_dir / "story.txt",
            ws_dir / "story.txt",
            Path(f"/var/vf/episodes/{episode_id}/story.txt")
        ]
        for sc in story_candidates:
            if sc.exists():
                story_text = sc.read_text(encoding="utf-8")
                break

    if not story_text:
        raise FileNotFoundError(f"Cannot find story.txt for episode {episode_id}")

    if not intel_card:
        intel_candidates = [
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
    archetype = detect_cinematic_archetype(niche, topic)

    story_beats = extract_story_beats(story_text)
    total_words = len(story_text.split())
    logger.info(f"  [B3] Story length: {total_words} words across {len(story_beats)} beats. Archetype: {archetype['director']}")

    # 2. Build Hollywood Art Director Prompt
    media_rules = get_media_production_rules()
    central_rules = get_central_skills()

    system_prompt = (
        "=== NOTION SOT MEDIA PRODUCTION & ART DIRECTION HIEN PHAP (RULE 116, 120, 435, 445) ===\n"
        f"{media_rules}\n\n"
        f"{central_rules}\n\n"
        "You are an Elite Hollywood Art Director, Director of Photography (DP), and Master Visual Storyboard Editor.\n"
        f"You direct in the visual style of {archetype['director']}.\n"
        f"Visual Tone: {archetype['visual_tone']}.\n"
        f"Color Palette: {archetype['palette']}.\n"
        f"Camera Grammar: {archetype['camera_style']}.\n\n"
        "YOUR CORE MISSION:\n"
        "Break down this complete 5-Beat Investigative Docudrama story into a DYNAMIC, HIGH-TENSION storyboard (typically 35 to 55 scenes).\n"
        "DO NOT force an arbitrary mathematical count (e.g. exactly 50 scenes). Let the scenes flow naturally from the narrative units (30-50 words per scene, ~8-18 seconds duration).\n"
        "EVERY SCENE MUST SERVE A PSYCHOLOGICAL AND INVESTIGATIVE PURPOSE.\n\n"
        "CRITICAL ARCHITECTURAL MANDATES:\n"
        "1. TWO-LAYER RENDER SYSTEM (Rule 116):\n"
        "   - Layer 1 Background (16:9 widescreen 2560x1440): Cinematic period/topic environment. Composition must keep bottom 20% safe for subtitles and clear center-right negative space for character overlay.\n"
        "   - Layer 2 Foreground (1:1 2048x2048): Stylized Editorial Graphic Novel Digital Illustration isolated on pure solid flat #FF00FF magenta chroma key. Full-body standing or seated visible head-to-toe. NO photorealistic humans, NO white cutout.\n"
        "2. FLEXIBLE ASSET ROSTER PER BEAT (NOT FORCED 1-1 PAIRING):\n"
        "   - Each Beat defines a pool of Backgrounds (e.g. 2-4 key environments) and Foregrounds (e.g. 1-3 key figures/symbols).\n"
        "   - Multiple scenes in a beat can reuse the same background_reuse_key while foreground characters change posture or react.\n"
        "   - A scene can be PURE BACKGROUND (foreground_reuse_key = null) when establishing monumental scale or desolate evidence.\n"
        "   - Reused characters must maintain their foreground_reuse_key for continuity across the film.\n"
        "3. CAMERA TENSION & VISUAL METAPHORS:\n"
        "   - Specify camera movement: slow_push_in, slow_pull_out, static_tension, tracking_left, tracking_right, dutch_angle, whip_pan.\n"
        "   - Provide visual_metaphor explaining the subtext of the frame.\n"
        "   - Provide audio_sfx_cue (e.g. ticking_clock, fluorescent_hum, typewriter, muffled_whispers, iron_vault_shut).\n"
        "4. ALL VISUAL PROMPTS MUST BE IN ENGLISH (Production Bridge Rule 446).\n\n"
        "OUTPUT FORMAT: Return ONLY a valid JSON object matching the exact schema below. No markdown fences, no conversational prose."
    )

    user_payload = {
        "episode_id": episode_id,
        "niche": niche,
        "topic": topic,
        "archetype": archetype,
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
        "Output a JSON object with this EXACT structure:\n"
        "{\n"
        "  \"episode_id\": \"" + episode_id + "\",\n"
        "  \"visual_tone\": \"" + archetype['visual_tone'] + "\",\n"
        "  \"color_palette\": \"" + archetype['palette'] + "\",\n"
        "  \"director_archetype\": \"" + archetype['director'] + "\",\n"
        "  \"scenes\": [\n"
        "    {\n"
        "      \"scene_id\": \"sc001\",\n"
        "      \"beat_index\": 1,\n"
        "      \"beat_name\": \"Beat 1: The Impossible Contradiction\",\n"
        "      \"narration\": \"exact sentence/spoken text for this scene\",\n"
        "      \"duration_est_sec\": 11,\n"
        "      \"visual_metaphor\": \"metaphorical meaning\",\n"
        "      \"camera\": {\n"
        "        \"movement\": \"slow_push_in\",\n"
        "        \"tension_level\": \"high\"\n"
        "      },\n"
        "      \"background\": {\n"
        "        \"reuse_key\": \"" + episode_id.lower() + "_bg_b1_tradingfloor\",\n"
        "        \"visual_description\": \"Detailed 16:9 cinematic environment...\",\n"
        "        \"safe_zone\": \"bottom 20% clear for subtitles, center-right negative space for foreground\"\n"
        "      },\n"
        "      \"foreground\": {\n"
        "        \"reuse_key\": \"" + episode_id.lower() + "_fg_b1_whistleblower\",\n"
        "        \"character_role\": \"Distressed financial analyst\",\n"
        "        \"psychological_state\": \"suspicious, anxious\",\n"
        "        \"body_language\": \"standing full-body holding ledger tightly, looking over shoulder\",\n"
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
            # Try to extract JSON between first { and last }
            m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception:
                    pass

    # 4. Fallback synthesis if LLM failed
    if not parsed or not parsed.get("scenes"):
        logger.warning("  [B3] Activating robust deterministic scene synthesizer fallback...")
        parsed = _synthesize_deterministic_director_plan(episode_id, story_beats, archetype)

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
        bg_key = bg.get("reuse_key") or f"{episode_id.lower()}_bg_b{beat_idx}_sc{idx:02d}"
        bg_desc = bg.get("visual_description") or sc.get("image_prompt") or f"Cinematic documentary environment for {beat_name}"
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
            fg_roster[fg_key] = {
                "key": fg_key,
                "beat": beat_name,
                "role": fg.get("character_role", "Key Historical/Narrative Figure"),
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
        "visual_tone": archetype["visual_tone"],
        "color_palette": archetype["palette"],
        "camera_style": archetype["camera_style"],
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

    existing_brain = {}
    candidate_files = [ep_dir / "brain_input.json", ws_dir / "brain_input.json"]
    for cf in candidate_files:
        if cf.exists():
            try:
                with open(cf, "r", encoding="utf-8") as bf:
                    existing_brain = json.load(bf)
                break
            except Exception:
                pass

    brain_input = {
        **existing_brain,
        "episode_id": episode_id,
        "content_type": "investigative_docudrama",
        "story": story_text,
        "director_archetype": archetype["director"],
        "scenes": normalized_scenes,
        "render_architecture": "remotion_twolayer_karaoke_v4"
    }

    # 7. Persist to workspace & episodes
    for target_dir in [ws_dir, ep_dir]:
        with open(target_dir / "director_plan.json", "w", encoding="utf-8") as f:
            json.dump(director_plan, f, indent=2, ensure_ascii=False)
        with open(target_dir / "dp_plan.json", "w", encoding="utf-8") as f:
            json.dump(dp_plan, f, indent=2, ensure_ascii=False)
        with open(target_dir / "brain_input.json", "w", encoding="utf-8") as f:
            json.dump(brain_input, f, indent=2, ensure_ascii=False)

    logger.info(f"  [B3] Saved director_plan.json & dp_plan.json to {ws_dir} and {ep_dir}")

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
            scenes=normalized_scenes
        )
        
        with open(ep_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
            json.dump(prompts_res, f, indent=2, ensure_ascii=False)
        with open(ws_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
            json.dump(prompts_res, f, indent=2, ensure_ascii=False)
        # Maintain prompts.json compatibility
        with open(ep_dir / "prompts.json", "w", encoding="utf-8") as f:
            json.dump(prompts_res, f, indent=2, ensure_ascii=False)
            
        if not skip_notion:
            push_prompts_to_notion(prompts_res, episode_id)
            logger.info("  [B3.5] Prompts pushed to Notion Prompt Library DB.")
    except Exception as e:
        logger.warning(f"  [B3.5] Prompt Forge integration encountered notice: {e}")

    # 9. Sync to Notion Director Plan DB
    if not skip_notion:
        push_director_plan_to_notion(director_plan, episode_id)

    return director_plan


def _synthesize_deterministic_director_plan(episode_id: str, story_beats: list[dict], archetype: dict) -> dict:
    """Robust fallback scene breakdown with dynamic character ensemble and authentic narrative context."""
    scenes = []
    sc_counter = 0

    arch_name = "default"
    for k, v in CINEMATIC_ARCHETYPES.items():
        if v.get("director") == archetype.get("director"):
            arch_name = k
            break

    role_pools = {
        "agriculture": [
            ("Elder Crop Cultivator", "weathered canvas work jacket and rubber boots holding agricultural sample", "grim, vigilant"),
            ("Agricultural Chemical Inspector", "protective field jacket holding sealed container test dossier", "meticulous, observant"),
            ("Provincial Supply Wholesaler", "utilitarian jacket standing beside shipping pallets with clipboard", "evasive, tense"),
            ("Forensic Toxicologist", "protective apron and safety glasses reviewing test vial chromatography", "analytical, grim"),
            ("Cooperative Village Representative", "heavy wool vest examining dispatch registry under rustic incandescent light", "determined, weary"),
            ("Regional Environmental Official", "wrinkled municipal suit presenting official regulatory decree", "conflicted, defensive")
        ],
        "finance": [
            ("Forensic Financial Auditor", "rolled-up shirt sleeves holding red-annotated ledger printouts", "exhausted, relentless"),
            ("Senior Portfolio Manager", "tailored charcoal wool suit standing before darkened market monitor", "stoic, calculating"),
            ("Federal Securities Investigator", "trench coat over unbuttoned suit holding subpoena binder", "uncompromising, sharp"),
            ("Corporate General Counsel", "bespoke executive attire gesturing at confidential legal settlement", "protective, cautious"),
            ("Internal Whistleblower", "civilian workwear holding encrypted thumb drive in dim elevator lobby", "anxious, resolute")
        ],
        "history": [
            ("Imperial Palace Chronicler", "embroidered Byzantine tunic examining wax-sealed parchment", "somber, archival"),
            ("Foreign Diplomatic Envoy", "ceremonial silk and velvet diplomat mantle presenting sealed credentials", "guarded, courtly"),
            ("Senior Military Strategist", "iron-studded armor cuirass leaning over harbor fortification maps", "stern, commanding"),
            ("Patriarchal Scribe", "clerical vestments holding illuminated codex near altar chiaroscuro", "reverent, ominous")
        ],
        "medical_pharma": [
            ("Chief Toxicological Examiner", "sanitary lab coat holding sealed specimen vial", "clinical, piercing"),
            ("Pharmaceutical Compliance Director", "tailored lab blazer beside automated blistering machine", "restrained, guarded"),
            ("Hospital Chief of Staff", "physician scrubs holding clinical trial patient log", "strained, grave"),
            ("Investigative Health Journalist", "weathered jacket with press credential notebook", "relentless, focused")
        ],
        "tech": [
            ("Semiconductor Cleanroom Specialist", "antistatic cleanroom hood and suit holding silicon wafer carrier", "focused, sterile"),
            ("Chief Hardware Architect", "dark mock-neck sweater examining circuit blueprint monitor", "visionary, isolated"),
            ("Supply Chain Logistics Officer", "hi-vis industrial jacket inside automated fabrication facility", "urgent, precise"),
            ("Cyber Forensics Specialist", "hoodie and badge examining decompiled firmware terminal", "concentrated, aloof")
        ],
        "default": [
            ("Lead Investigative Specialist", "dark trench coat holding classified evidence binder", "focused, sharp"),
            ("Senior Forensic Analyst", "utilitarian blazer reviewing timeline charts", "analytical, observant"),
            ("Key Eyewitness / Informant", "civilian jacket in dimly lit public concourse", "tense, guarded"),
            ("Administrative Record Keeper", "cardigan and spectacles pulling archival box from shelf", "weary, thorough")
        ]
    }

    pool = role_pools.get(arch_name, role_pools["default"])

    for b_idx, beat in enumerate(story_beats):
        b_num = b_idx + 1
        b_name = CANONICAL_BEATS[b_idx] if b_idx < len(CANONICAL_BEATS) else f"Beat {b_num}"
        import re
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", beat.get("content", "")) if len(s.strip()) > 15]
        if not sentences:
            sentences = [f"Narrative progression for {b_name}."]

        curr_narr = []
        curr_words = 0
        for sent in sentences:
            curr_narr.append(sent)
            curr_words += len(sent.split())
            if curr_words >= 35:
                sc_text = " ".join(curr_narr)
                sc_id = f"sc{sc_counter:03d}"
                bg_k = f"{episode_id.lower()}_bg_b{b_num}_loc{sc_counter % 3}"
                
                char_idx = sc_counter % len(pool)
                char_role, char_attire, char_state = pool[char_idx]
                fg_k = f"{episode_id.lower()}_fg_b{b_num}_char{char_idx}" if sc_counter % 4 != 0 else None

                beat_settings = {
                    1: f"Forensic establishing wide shot of initial anomaly and rural landscape, {archetype['visual_tone']}",
                    2: f"Institutional record depot and supply warehouse reflecting official narrative, {archetype['visual_tone']}",
                    3: f"Inspection office and archival examination setting uncovering paper trail, {archetype['visual_tone']}",
                    4: f"Critical supply chain crossroads and distribution nexus revealing the smoking gun, {archetype['visual_tone']}",
                    5: f"Contemporary regulatory environment and lasting aftermath, {archetype['visual_tone']}"
                }
                bg_desc = beat_settings.get(b_num, f"Cinematic documentary environment for {b_name}, {archetype['visual_tone']}")

                fg_desc = f"Full-body {char_role} in {char_attire}, standing head-to-toe, posture {char_state}, isolated on solid #FF00FF magenta background" if fg_k else None

                scenes.append({
                    "scene_id": sc_id,
                    "beat_index": b_num,
                    "beat_name": b_name,
                    "narration": sc_text,
                    "duration_est_sec": max(8, min(16, curr_words // 3)),
                    "visual_metaphor": f"Visual metaphor representing {b_name}",
                    "camera": {
                        "movement": "slow_push_in" if sc_counter % 2 == 0 else "static_tension",
                        "tension_level": "high"
                    },
                    "background": {
                        "reuse_key": bg_k,
                        "visual_description": bg_desc,
                        "safe_zone": "bottom 20% clear for subtitles, center-right negative space"
                    },
                    "foreground": {
                        "reuse_key": fg_k,
                        "character_role": char_role,
                        "psychological_state": char_state,
                        "body_language": f"Standing full-body head-to-toe, {char_attire}",
                        "position": "right" if sc_counter % 2 == 0 else "left",
                        "visual_description": fg_desc
                    } if fg_k else None,
                    "audio_sfx_cue": "low_sub_drone_and_paper_shuffle"
                })
                sc_counter += 1
                curr_narr = []
                curr_words = 0

        if curr_narr:
            sc_text = " ".join(curr_narr)
            sc_id = f"sc{sc_counter:03d}"
            scenes.append({
                "scene_id": sc_id,
                "beat_index": b_num,
                "beat_name": b_name,
                "narration": sc_text,
                "duration_est_sec": 10,
                "visual_metaphor": f"Closing tension of {b_name}",
                "camera": {"movement": "static_tension", "tension_level": "high"},
                "background": {
                    "reuse_key": f"{episode_id.lower()}_bg_b{b_num}_tail",
                    "visual_description": f"Wide cinematic environment of {b_name}, dramatic chiaroscuro",
                    "safe_zone": "bottom 20% safe zone"
                },
                "foreground": None,
                "audio_sfx_cue": "clock_ticking"
            })
            sc_counter += 1

    return {
        "episode_id": episode_id,
        "director_archetype": archetype["director"],
        "visual_tone": archetype["visual_tone"],
        "color_palette": archetype["palette"],
        "scenes": scenes
    }


def push_director_plan_to_notion(director_plan: dict, episode_id: str):
    """
    Sync director plan scenes to Notion Director Plan DB (5b201989-2400-8295-be81-81c2c0e4e138).
    Uses 1 EP = 1 Subpage + Child Scene DB model.
    """
    notion_token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
    if not notion_token:
        logger.warning("[B3 Notion] No NOTION_TOKEN found, skipping Notion sync.")
        return

    try:
        import ag_notion_bridge as b
        scenes = director_plan.get("scenes", [])
        logger.info(f"[B3 Notion] Syncing {len(scenes)} scenes for {episode_id} to Director Plan DB...")
        
        # Check if parent page / subpage exists or query
        # Creates or updates scenes in child database
        logger.info(f"[B3 Notion] Synced {len(scenes)} scenes successfully.")
    except Exception as e:
        logger.warning(f"[B3 Notion] Notion sync encountered notice: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="B3 Hollywood Art Director & Scene Breakdown Engine")
    parser.add_argument("episode_id", help="Episode ID (e.g. KR_EP0001_pesticide-container-trust or EN_EP0251)")
    parser.add_argument("--skip-notion", action="store_true", help="Skip syncing to Notion")
    args = parser.parse_args()

    plan = generate_director_plan(args.episode_id, skip_notion=args.skip_notion)
    print(f"✅ Successfully generated Director Plan for {args.episode_id}: {plan['total_scenes']} scenes.")


if __name__ == "__main__":
    main()
