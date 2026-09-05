"""
Service: B3.5 Prompt Engineering Forge (/prompt:forge)
Single Source of Truth: HHTech GPT-6-Astra + Prompt Library Notion DB
Rule 116 & 435: Layer 1 Background (16:9) + Layer 2 Foreground (1:1 stylized graphic novel on #FF00FF).
Rule 120: Isolates prompt generation. FGs strictly generated on flat #FF00FF magenta background.
Rule 121: Dynamically loads Media Production Hub and Central Skill AI rules via skill_loader.py.
Semantic Coupling: Inherits and preserves B3 Director Plan scene-level (background, foreground) pairings.
Eradicates all archaic historical relics dynamically and dynamically matches scene era and lighting.
"""

import os, sys, json, re, requests, logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _load_env():
    from app.services.youtube_upload import _load_env as le
    le()

_load_env()

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.skill_loader import (
    get_skill_rules,
    get_central_skills,
    get_media_production_rules
)

sys.path.insert(0, "/root/video_factory/scripts")
import ag_notion_bridge as _bridge

NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
PROMPT_LIBRARY_DB_ID_FALLBACK = "8c801989-2400-831a-901d-014aebdc3b31"

# Relic regex covering singular/plural forms and historical artifacts
_RELIC_REGEX = re.compile(
    r"\b(armored\s+crusaders?|crusaders?|venetian\s+doges?|doges?|byzantine|byzantium|circa[\s\-_]*1204|imperial\s+relics?)\b",
    re.IGNORECASE
)


class ContentPolicyRefusalError(Exception):
    """
    Raised when HHTech GPT-6-Astra refuses to generate prompts due to content policy.
    Upstream should route to HG2.5 (human review gate) for manual prompt engineering.
    """
    pass


def _clean_relics(text: str, is_byzantine_topic: bool = False) -> str:
    """Scrub archaic prompt relics unless the topic is legitimately medieval history."""
    if is_byzantine_topic:
        return text
    cleaned = _RELIC_REGEX.sub("", text)
    # Clean up dangling prepositions before commas left behind
    cleaned = re.sub(r"\b(with|in|of|and|for|at)\s*,", ",", cleaned, flags=re.IGNORECASE)
    # Clean up double commas, awkward commas and spaces left behind
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s,]+|[\s,]+$", "", cleaned)
    return cleaned.strip()


def _sanitize_background_prompt(prompt: str, bg_key: str, is_byzantine: bool = False) -> str:
    """Sanitize and enforce Rule 116 standards for Layer 1 Background prompts."""
    p = _clean_relics(prompt, is_byzantine)
    # Enforce 16:9 aspect ratio and negative space safe-zone if missing
    if "16:9" not in p:
        p = f"{p}, 16:9 aspect ratio"
    if "safe-zone" not in p and "safe zone" not in p:
        p = f"{p}, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"
        # Enforce English Production Bridge tags (Rule 446)
    if "[STYLE MANDATE]" not in p:
        p = f"[STYLE MANDATE] 16:9 widescreen cinematic documentary environment, atmospheric volumetric lighting, spatial textures, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay. {p}"
    if "[ERA ANCHOR]" not in p:
        p = f"{p} [ERA ANCHOR] Authentic period architecture and narrative atmosphere."
    if "[STRICT NEGATIVE PROMPT]" not in p:
        p = f"{p} [STRICT NEGATIVE PROMPT] no prominent foreground human figures, no photorealistic faces, no text, no subtitles, no watermark, no borders, no ui elements, no split frame."
    p = re.sub(r"\s{2,}", " ", p).strip()
    return p


def _sanitize_foreground_prompt(prompt: str, fg_key: str, is_byzantine: bool = False) -> str:
    """Sanitize and enforce Rule 116 & Rule 435 standards for Layer 2 Foreground prompts."""
    p = _clean_relics(prompt, is_byzantine)
    
    # Eliminate photorealistic studio lighting in favor of stylized editorial graphic novel illustration
    p = re.sub(r"studio portrait lighting,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic studio portrait,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic,?\s*", "", p, flags=re.IGNORECASE)

    # Ensure non-photorealistic stylized digital illustration phrasing
    if "stylized editorial graphic novel" not in p.lower() and "illustrated" not in p.lower():
        p = f"Stylized editorial graphic novel digital illustration of {p}"

    # Check if prompt already specifies full-body standing framing (Rules 116 & 435)
    has_full_body = any(term in p.lower() for term in [
        "full-body", "full body", "head-to-shoes", "head to toe", "entire character visible"
    ])

    mandatory_framing = (
        "1:1 aspect ratio, full-body head-to-shoes standing portrait, "
        "entire character visible with head and feet completely inside frame on solid #FF00FF magenta background"
    )

    if not has_full_body:
        # Strip any existing partial chroma key / aspect ratio clauses to avoid redundant phrasing
        p = re.sub(r",?\s*(?:isolated\s+on\s+(?:a\s+solid\s+flat\s+)?)?#FF00FF[^,]*", "", p, flags=re.IGNORECASE)
        p = re.sub(r",?\s*1:1 aspect ratio", "", p, flags=re.IGNORECASE)
        p = f"{p.rstrip(', ')}, {mandatory_framing}"
    else:
        # Full-body was already specified; guarantee technical #FF00FF magenta chroma-key and 1:1 aspect ratio
        if "#FF00FF" not in p:
            p = f"{p}, on solid #FF00FF magenta background"
        if "1:1 aspect ratio" not in p:
            p = f"{p}, 1:1 aspect ratio"

    # Clean up double commas or awkward spacing left behind
    p = re.sub(r",\s*,+", ", ", p)
    p = re.sub(r"\s*,\s*", ", ", p)
    p = re.sub(r"\s{2,}", " ", p)
        # Enforce English Production Bridge tags (Rule 435 & 446)
    if "[STYLE MANDATE]" not in p:
        p = f"[STYLE MANDATE] Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration, clean bold ink linework, cel-shading, rich nuanced colors, 1:1 aspect ratio, full-body head-to-shoes, entire character visible within frame, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames. {p}"
    if "[ERA ANCHOR]" not in p:
        p = f"{p} [ERA ANCHOR] Period-accurate attire, realistic investigative posture and facial expression."
    if "[STRICT NEGATIVE PROMPT]" not in p:
        p = f"{p} [STRICT NEGATIVE PROMPT] no photograph, no photorealistic human, no 3D render, no CGI skin, no white background, no gray background, no halo, no gradients, no cropped head, no cropped feet, no cutoffs, no borders, no ui elements."
    p = re.sub(r"\s{2,}", " ", p).strip()
    return p.strip()


def generate_scene_prompts(
    bg_dict: dict,
    fg_dict: dict,
    story_title: str,
    scenes: list = None,
    **kwargs
) -> dict:
    """
    Calls HHTech GPT-6-Astra via dedicated reasoner to generate high-fidelity image prompts
    for paired Backgrounds (16:9) and Foregrounds (1:1).
    
    Preserves scene-level pairing (background_reuse_key, foreground_reuse_key) to ensure
    Background and Foreground are semantically unified in era, lighting, and narrative context.
    
    Enforces Rule 116 & Rule 435 (non-photorealistic stylized graphic novel FG on #FF00FF).
    Eradicates all hardcoded relics and dynamically adapts to the scene era.
    """
    media_rules = get_media_production_rules()
    central_rules = get_central_skills()

    is_byzantine = "byzantine" in story_title.lower() or "fourth crusade" in story_title.lower()

    # Build scene pairing context
    scene_pairings = []
    if scenes:
        for s in scenes:
            scene_pairings.append({
                "scene_index": s.get("scene_index"),
                "arc": s.get("arc"),
                "background_reuse_key": s.get("background_reuse_key"),
                "foreground_reuse_key": s.get("foreground_reuse_key"),
                "narration_excerpt": (s.get("narration") or "")[:250],
                "bg_hint": s.get("image_prompt"),
                "fg_hint": s.get("foreground_prompt")
            })

    system_prompt = (
        "=== NOTION SOT MEDIA PRODUCTION & VISUAL DIRECTION RULES ===\n"
        f"{media_rules}\n\n"
        "=== NOTION SOT CENTRAL EDITORIAL RULES (RULES 116, 120, 435) ===\n"
        f"{central_rules}\n\n"
        "You are an Elite Visual Director and Master Prompt Engineer for the AI Video Factory (VF Pipeline).\n"
        "Your mission is to generate production-grade image generation prompts for 2-Layer video composition:\n"
        "  - Layer 1 Background (16:9 2K DCI 2560x1440): Cinematic documentary environment.\n"
        "  - Layer 2 Foreground (1:1 2048x2048): Stylized editorial graphic novel digital illustration isolated on pure #FF00FF magenta chroma key.\n\n"
        "CRITICAL ARCHITECTURAL MANDATES (RULE 116 & RULE 435):\n"
        "1. ERA & TOPIC AUTHENTICITY: Strictly derive the era, architectural style, atmosphere, color palette, and lighting dynamically from the episode topic and scene narration. NEVER hallucinate medieval or out-of-context architectural relics for modern or non-medieval topics.\n"
        "2. SCENE SEMANTIC COUPLING: Maintain 100% semantic unity between each Background and its paired Foreground character. The setting, time period, indoor/outdoor lighting angle, and mood MUST match between paired assets in each scene.\n"
        "3. LAYER 1 BACKGROUND PROMPT RULES (16:9):\n"
        "   - Wide-angle cinematic environment establishing scene atmosphere and narrative depth.\n"
        "   - Authentic period architecture, environment textures, dramatic volumetric lighting.\n"
        "   - NO prominent human figures in the foreground. Leave center/right negative space clear for the Layer 2 character overlay.\n"
        "   - Leave the bottom 20% safe zone clear of critical visual elements for on-screen subtitles.\n"
        "   - Style: Photorealistic 8k cinematic documentary environment, rich spatial textures, moody color grading, 16:9 aspect ratio.\n"
        "4. LAYER 2 FOREGROUND PROMPT RULES (1:1):\n"
        "   - NON-PHOTOREALISTIC, STYLIZED EDITORIAL GRAPHIC NOVEL DIGITAL ILLUSTRATION (clean digital artwork, illustrated character drawing, NOT a studio photograph).\n"
        "   - Exactly ONE full-body standing or seated figure/subject visible from head to toe in authentic attire appropriate to the era and role.\n"
        "   - Dynamic dramatic lighting angle aligned with the lighting angle and tone of the paired scene background.\n"
        "   - MUST ALWAYS include the exact technical clause: 'isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio'.\n"
        "   - Completely avoid 'photorealistic studio portrait lighting' for foregrounds. Foreground must be a stylized editorial graphic novel digital illustration.\n\n"
        "Output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"backgrounds\": {\n"
        "    \"<bg_key>\": \"<detailed prompt string>\", ...\n"
        "  },\n"
        "  \"foregrounds\": {\n"
        "    \"<fg_key>\": \"<detailed prompt string>\", ...\n"
        "  }\n"
        "}\n"
    )

    user_payload = {
        "title": story_title,
        "backgrounds_to_generate": bg_dict,
        "foregrounds_to_generate": fg_dict
    }
    if scene_pairings:
        user_payload["scene_level_pairings"] = scene_pairings

    raw_response = None
    for pf_attempt in range(1, 3):
        try:
            logger.info(f"[prompt_forge] Calling GPT-6-Astra for prompts (attempt {pf_attempt}/2)...")
            raw_response = call_gpt6_astra(
                prompt=json.dumps(user_payload, ensure_ascii=False),
                system_prompt=system_prompt,
                max_tokens=3500,
                timeout=120.0
            )
            if raw_response and raw_response.strip():
                break
        except Exception as e:
            logger.warning(f"[prompt_forge] HHTech API attempt {pf_attempt} encountered issue: {e}")
            if pf_attempt < 2:
                import time
                time.sleep(3.0)
            else:
                logger.warning("[prompt_forge] Activating robust metadata-driven synthesis fallback.")

    parsed = None
    if raw_response and raw_response.strip():
        content = raw_response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        # Parse JSON with refusal detection
        try:
            parsed = json.loads(content.strip())
        except json.JSONDecodeError as e:
            content_lower = content.lower()
            refusal_indicators = [
                "cannot propagate",
                "material conflict",
                "content policy",
                "unable to generate",
                "cannot create",
                "policy violation",
                "inappropriate content"
            ]
            if any(indicator in content_lower for indicator in refusal_indicators):
                logger.error("[prompt_forge] GPT-6-Astra CONTENT POLICY REFUSAL detected")
                raise ContentPolicyRefusalError(
                    f"HHTech GPT-6-Astra refused to generate prompts due to content policy for '{story_title}'. "
                    f"Refusal: {content[:250]}"
                )
            else:
                logger.warning(f"[prompt_forge] Malformed JSON from LLM: {content[:200]}, falling back to metadata synthesis.")
                parsed = None

    if not parsed or not isinstance(parsed, dict):
        parsed = {"backgrounds": {}, "foregrounds": {}}

    # Sanitize and post-process all generated prompts
    cleaned_backgrounds = {}
    cleaned_foregrounds = {}

    for k, p in parsed.get("backgrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_backgrounds[k] = _sanitize_background_prompt(prompt_str, k, is_byzantine)

    for k, p in parsed.get("foregrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_foregrounds[k] = _sanitize_foreground_prompt(prompt_str, k, is_byzantine)

    # Ensure all requested keys are covered, synthesizing from scene metadata if needed
    for bg_k, bg_meta in bg_dict.items():
        if bg_k not in cleaned_backgrounds:
            hint = bg_meta.get("visual_hint") or bg_meta.get("narration_context") or bg_k.replace("-", " ")
            paired_fgs = bg_meta.get("paired_foregrounds", [])
            paired_desc = f", paired with {', '.join(paired_fgs)}" if paired_fgs else ""
            fallback_bg = (
                f"Cinematic wide-angle documentary environment of {hint}{paired_desc}, "
                f"atmospheric volumetric natural lighting matching narrative tone, 16:9 aspect ratio, "
                f"bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"
            )
            cleaned_backgrounds[bg_k] = _sanitize_background_prompt(fallback_bg, bg_k, is_byzantine)

    for fg_k, fg_meta in fg_dict.items():
        if fg_k not in cleaned_foregrounds:
            hint = fg_meta.get("visual_hint") or fg_meta.get("narration_context") or fg_k.replace("-", " ")
            paired_bgs = fg_meta.get("paired_backgrounds", [])
            paired_desc = f", harmonized with setting {', '.join(paired_bgs)}" if paired_bgs else ""
            fallback_fg = (
                f"Stylized editorial graphic novel digital illustration of full-body {hint} figure in authentic period attire{paired_desc}, "
                f"head to toe visible, dramatic character rim light matching environment, "
                f"isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio"
            )
            cleaned_foregrounds[fg_k] = _sanitize_foreground_prompt(fallback_fg, fg_k, is_byzantine)

    result = {
        "backgrounds": cleaned_backgrounds,
        "foregrounds": cleaned_foregrounds
    }
    logger.info(f"[prompt_forge] Successfully forged {len(cleaned_backgrounds)} BG prompts and {len(cleaned_foregrounds)} FG prompts")
    return result


def push_prompts_to_notion(prompts_data: dict, episode_id: str, task_id: str = None):
    """
    Pushes generated prompts to this episode's own Prompt Library child database
    (per-episode subpage+DB resolved dynamically via ag_notion_bridge.resolve_episode_prompt_db).
    Archives old prompts for the same episode first to keep idempotency.
    """
    if not NOTION_API_KEY:
        logger.warning("[prompt_forge] No NOTION_API_KEY found, skipping Notion sync.")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    resolved = _bridge.resolve_episode_prompt_db(episode_id, task_id=task_id)
    if resolved.get("error"):
        logger.warning(f"[prompt_forge] Could not resolve episode DB for {episode_id}: {resolved}. Using fallback flat DB.")
        prompt_library_db_id = PROMPT_LIBRARY_DB_ID_FALLBACK
    else:
        prompt_library_db_id = resolved["db_id"]
        if resolved.get("created"):
            logger.info(f"[prompt_forge] Created new Prompt Library child DB for {episode_id} (db={prompt_library_db_id})")

    # 0. Archive old prompts for this episode to maintain single-truth
    try:
        q_res = requests.post(
            f"https://api.notion.com/v1/databases/{prompt_library_db_id}/query",
            headers=headers,
            json={
                "filter": {
                    "property": "Title",
                    "title": {"contains": f"[{episode_id}]"}
                }
            },
            timeout=10
        )
        if q_res.status_code == 200:
            existing = q_res.json().get("results", [])
            for r in existing:
                requests.patch(
                    f"https://api.notion.com/v1/pages/{r['id']}",
                    headers=headers,
                    json={"archived": True},
                    timeout=10
                )
            if existing:
                logger.info(f"[prompt_forge] Archived {len(existing)} older prompts for [{episode_id}] in Prompt Library DB.")
    except Exception as e:
        logger.warning(f"[prompt_forge] Error cleaning old prompts: {e}")

    # 1. Backgrounds
    for bg_key, prompt in prompts_data.get("backgrounds", {}).items():
        prompt_str = prompt if isinstance(prompt, str) else prompt.get("prompt", str(prompt))
        bg_payload = {
            "parent": {"database_id": prompt_library_db_id},
            "properties": {
                "Title": {"title": [{"text": {"content": f"[{episode_id}] {bg_key} (BG 16:9)"}}]},
                "prompt_text": {"rich_text": [{"text": {"content": prompt_str[:2000]}}]},
                "category": {"select": {"name": "image"}},
                "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 16:9, Safe Zone: Bottom 20%"}}]},
                "version": {"number": 1}
            }
        }
        try:
            res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=bg_payload, timeout=10)
            if res.status_code in (200, 201):
                logger.debug(f"[prompt_forge] Pushed BG prompt {bg_key} to Notion Prompt Library DB")
            else:
                logger.warning(f"[prompt_forge] Failed to push BG prompt {bg_key}: {res.status_code} {res.text}")
        except Exception as e:
            logger.warning(f"[prompt_forge] Exception pushing BG prompt {bg_key}: {e}")

    # 2. Foregrounds
    for fg_key, prompt in prompts_data.get("foregrounds", {}).items():
        prompt_str = prompt if isinstance(prompt, str) else prompt.get("prompt", str(prompt))
        fg_payload = {
            "parent": {"database_id": prompt_library_db_id},
            "properties": {
                "Title": {"title": [{"text": {"content": f"[{episode_id}] {fg_key} (FG 1:1 #FF00FF)"}}]},
                "prompt_text": {"rich_text": [{"text": {"content": prompt_str[:2000]}}]},
                "category": {"select": {"name": "image"}},
                "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 1:1, Chroma Key: Flat #FF00FF Magenta Background"}}]},
                "version": {"number": 1}
            }
        }
        try:
            res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=fg_payload, timeout=10)
            if res.status_code in (200, 201):
                logger.debug(f"[prompt_forge] Pushed FG prompt {fg_key} to Notion Prompt Library DB")
            else:
                logger.warning(f"[prompt_forge] Failed to push FG prompt {fg_key}: {res.status_code} {res.text}")
        except Exception as e:
            logger.warning(f"[prompt_forge] Exception pushing FG prompt {fg_key}: {e}")
