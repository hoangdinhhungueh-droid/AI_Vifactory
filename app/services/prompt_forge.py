"""
Service: B3.5 Prompt Engineering Forge (/prompt:forge)
Single Source of Truth: HHTech GPT-6-Astra + Prompt Library Notion DB
Rule 116 & 435: Layer 1 Background (16:9) + Layer 2 Foreground (1:1 stylized graphic novel on #FF00FF).
Rule 120: Isolates prompt generation. FGs strictly generated on flat #FF00FF magenta background.
Rule 128: Zero Semantic Bias. Dynamically matches scene era, architecture, and lighting without topic relics.
Rule 446: English Production Bridge for all visual generation prompts.
"""

import os
import sys
import json
import re
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _load_env():
    from app.services.youtube_upload import _load_env as le
    le()

_load_env()

from app.services.hhtech_reasoner import call_gpt6_astra
from app.services.skill_loader import get_b35_strategic_rules

sys.path.insert(0, "/root/video_factory/scripts")
import ag_notion_bridge as _bridge

NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
PROMPT_LIBRARY_DB_ID_FALLBACK = "8c801989-2400-831a-901d-014aebdc3b31"

# Rule 128: Concise targeted visual rules (~1.2k chars) replacing 336k chars dump
TARGETED_VISUAL_RULES = get_b35_strategic_rules()


class ContentPolicyRefusalError(Exception):
    """
    Raised when HHTech GPT-6-Astra refuses to generate prompts due to content policy.
    Upstream should route to HG2.5 (human review gate) for manual prompt engineering.
    """
    pass


def deduplicate_phrase_stutter(text: str) -> str:
    """
    Universal Anti-Stuttering & Phrase Deduplication Engine (Rule 128 & Gate 6 Guarantee).
    1. Eliminates consecutive identical words.
    2. Eliminates consecutive repeated word sequences / n-grams (2-8 words repeated consecutively).
    3. Normalizes single-instance structural phrases (such as [STYLE MANDATE], [ERA ANCHOR],
       [STRICT NEGATIVE PROMPT], 16:9, 1:1, #FF00FF, Stylized Editorial) so each appears
       AT MOST ONCE across the entire prompt.
    4. Cleans up dangling prepositions, duplicate commas, and irregular spacing.
    """
    cleaned = text

    # 1. Deduplicate consecutive identical words: e.g. "the the" -> "the"
    cleaned = re.sub(r"\b(\w+)(?:[\s,]+\1\b)+", r"\1", cleaned, flags=re.IGNORECASE)

    # 2. Deduplicate consecutive repeated phrases (2 to 8 words repeated consecutively)
    for _ in range(3):
        cleaned = re.sub(
            r"(\b[a-zA-Z0-9#_-]+(?:[\s,]+[a-zA-Z0-9#_-]+){1,8}\b)[\s,]+(?:\1\b)+",
            r"\1",
            cleaned,
            flags=re.IGNORECASE
        )

    # 3. Ensure critical architectural phrases appear at most ONCE across the entire prompt
    single_instance_phrases = [
        r"\[STYLE MANDATE\]",
        r"\[ERA ANCHOR\]",
        r"\[STRICT NEGATIVE PROMPT\]",
        r"16:9 widescreen cinematic documentary environment",
        r"16:9 aspect ratio",
        r"1:1 aspect ratio",
        r"bottom 20% safe-zone for subtitles",
        r"bottom 20% safe-zone",
        r"clear center-right negative space for foreground character overlay",
        r"clear center-right negative space",
        r"solid flat #FF00FF pure magenta background",
        r"solid #FF00FF magenta background",
        r"#FF00FF",
        r"clean chroma-key cutout, sharp silhouette, no borders, no frames",
        r"clean chroma-key cutout",
        r"full-body head-to-shoes",
        r"entire character visible within frame",
        r"Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration",
        r"Stylized Editorial Graphic Novel Digital Illustration",
        r"Stylized Editorial Graphic Novel",
        r"Stylized Editorial"
    ]

    for phrase_pat in single_instance_phrases:
        matches = list(re.finditer(phrase_pat, cleaned, flags=re.IGNORECASE))
        if len(matches) > 1:
            parts = []
            last_idx = 0
            for i, m in enumerate(matches):
                if i == 0:
                    parts.append(cleaned[last_idx:m.end()])
                else:
                    parts.append(cleaned[last_idx:m.start()])
                last_idx = m.end()
            parts.append(cleaned[last_idx:])
            cleaned = "".join(parts)

    # 4. Clean up dangling prepositions, commas, and whitespace
    cleaned = re.sub(r"\b(with|in|of|and|for|at)\s*([,.;])", r"\2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s,]+|[\s,]+$", "", cleaned)
    return cleaned.strip()


def _clean_relics(text: str, is_byzantine_topic: bool = False) -> str:
    """Universal prompt text sanitization: deduplication, spacing, and punctuation cleanup (Rule 128)."""
    return deduplicate_phrase_stutter(text)


def _sanitize_background_prompt(prompt: str, bg_key: str = "", is_byzantine: bool = False) -> str:
    """Sanitize and enforce Rule 116 standards for Layer 1 Background prompts."""
    p = prompt.strip()
    p = re.sub(r"\[STYLE MANDATE\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[ERA ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)

    if "16:9" not in p:
        p = f"{p}, 16:9 aspect ratio"
    if "safe-zone" not in p and "safe zone" not in p:
        p = f"{p}, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"

    style_prefix = "[STYLE MANDATE] 16:9 widescreen cinematic documentary environment, atmospheric volumetric lighting, spatial textures, bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay."

    p = f"{style_prefix} {p} [ERA ANCHOR] Authentic period architecture and narrative atmosphere. [STRICT NEGATIVE PROMPT] no prominent foreground human figures, no photorealistic faces, no text, no subtitles, no watermark, no borders, no ui elements, no split frame."

    return deduplicate_phrase_stutter(p)


def _sanitize_foreground_prompt(prompt: str, fg_key: str = "", is_byzantine: bool = False) -> str:
    """Sanitize and enforce Rule 116 & Rule 435 standards for Layer 2 Foreground prompts."""
    p = prompt.strip()

    p = re.sub(r"studio portrait lighting,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic studio portrait,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"photorealistic,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"3D render,?\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"CGI skin,?\s*", "", p, flags=re.IGNORECASE)

    p = re.sub(r"\[STYLE MANDATE\]\s*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[ERA ANCHOR\]\s*[^\[]*", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[STRICT NEGATIVE PROMPT\]\s*.*$", "", p, flags=re.IGNORECASE)
    p = re.sub(
        r"(?:Non-photorealistic\s+2D\s+)?Stylized\s+Editorial(?:\s+Graphic\s+Novel)?(?:\s+Digital)?(?:\s+Illustration)?(?:\s+of)?\s*,?\s*",
        "",
        p,
        flags=re.IGNORECASE
    ).strip()

    has_full_body = any(term in p.lower() for term in [
        "full-body", "full body", "head-to-shoes", "head to toe", "entire character visible"
    ])

    mandatory_framing = (
        "1:1 aspect ratio, full-body head-to-shoes standing portrait, "
        "entire character visible with head and feet completely inside frame on solid #FF00FF magenta background"
    )

    if not has_full_body:
        p = re.sub(r",?\s*(?:isolated\s+on\s+(?:a\s+solid\s+flat\s+)?)?#FF00FF[^,]*", "", p, flags=re.IGNORECASE)
        p = re.sub(r",?\s*1:1 aspect ratio", "", p, flags=re.IGNORECASE)
        p = f"{p.rstrip(', ')}, {mandatory_framing}"
    else:
        if "#FF00FF" not in p:
            p = f"{p}, on solid #FF00FF magenta background"
        if "1:1 aspect ratio" not in p:
            p = f"{p}, 1:1 aspect ratio"

    style_prefix = "[STYLE MANDATE] Non-photorealistic 2D Stylized Editorial Graphic Novel Digital Illustration, clean bold ink linework, cel-shading, rich nuanced colors, 1:1 aspect ratio, full-body head-to-shoes, entire character visible within frame, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames."

    p = f"{style_prefix} {p} [ERA ANCHOR] Period-accurate attire, realistic investigative posture and facial expression. [STRICT NEGATIVE PROMPT] no photograph, no photorealistic human, no 3D render, no CGI skin, no white background, no gray background, no halo, no gradients, no cropped head, no cropped feet, no cutoffs, no borders, no ui elements."

    p = deduplicate_phrase_stutter(p)

    matches = list(re.finditer(r"Stylized\s+editorial", p, flags=re.IGNORECASE))
    if len(matches) > 1:
        parts = []
        last_idx = 0
        for i, m in enumerate(matches):
            parts.append(p[last_idx:m.start()])
            if i == 0:
                parts.append(p[m.start():m.end()])
            else:
                parts.append("expressive illustrated")
            last_idx = m.end()
        parts.append(p[last_idx:])
        p = "".join(parts)

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
    Eradicates all hardcoded relics and dynamically adapts to the scene era (Rule 128).
    """
    scene_pairings = []
    if scenes:
        for s in scenes:
            scene_pairings.append({
                "scene_index": s.get("scene_index"),
                "arc": s.get("arc"),
                "background_reuse_key": s.get("background_reuse_key") or s.get("bg_id"),
                "foreground_reuse_key": s.get("foreground_reuse_key") or s.get("fg_id"),
                "narration_excerpt": (s.get("narration") or "")[:250],
                "bg_hint": s.get("image_prompt"),
                "fg_hint": s.get("foreground_prompt")
            })

    # Rule 128: Use concise strategic rules loader (~1.2k chars) to eliminate token explosion
    visual_rules = get_b35_strategic_rules()
    system_prompt = (
        f"{visual_rules}\n\n"
        "You are an Elite Visual Director and Master Prompt Engineer for the AI Video Factory (VF Pipeline).\n"
        "Your mission is to generate production-grade image generation prompts for 2-Layer video composition:\n"
        "  - Layer 1 Background (16:9 2K DCI 2560x1440): Cinematic documentary environment.\n"
        "  - Layer 2 Foreground (1:1 2048x2048): Stylized editorial graphic novel digital illustration isolated on pure #FF00FF magenta chroma key.\n\n"
        "CRITICAL ARCHITECTURAL MANDATES (RULE 116 & RULE 435 & RULE 128):\n"
        "1. ERA & TOPIC AUTHENTICITY (Rule 128): Strictly derive era, architectural style, atmosphere, color palette, and lighting dynamically from the episode topic and scene narration. Zero domain bleed.\n"
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
                max_tokens=4500,
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
        content = content.strip()

        # Check for content policy refusal
        content_lower = content.lower()
        refusal_indicators = [
            "i cannot generate",
            "i am unable to",
            "content policy",
            "safety policy",
            "against my programming",
            "sensitive themes",
            "violates",
            "inappropriate content"
        ]
        if any(indicator in content_lower for indicator in refusal_indicators):
            logger.error("[prompt_forge] GPT-6-Astra CONTENT POLICY REFUSAL detected")
            raise ContentPolicyRefusalError(
                f"HHTech GPT-6-Astra refused to generate prompts due to content policy for '{story_title}'. "
                f"Refusal: {content[:250]}"
            )

        try:
            parsed = json.loads(content)
        except Exception as e:
            logger.warning(f"[prompt_forge] JSON decode error: {e}. Attempting recovery...")
            m = re.search(r"(\{.*\})", content, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception:
                    pass

    if not parsed or not isinstance(parsed, dict):
        parsed = {"backgrounds": {}, "foregrounds": {}}

    cleaned_backgrounds = {}
    cleaned_foregrounds = {}

    for k, p in parsed.get("backgrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_backgrounds[k] = _sanitize_background_prompt(prompt_str, k)

    for k, p in parsed.get("foregrounds", {}).items():
        prompt_str = p if isinstance(p, str) else p.get("prompt", str(p))
        cleaned_foregrounds[k] = _sanitize_foreground_prompt(prompt_str, k)

    # Ensure all requested keys are covered, synthesizing from scene metadata if needed
    for bg_k, bg_meta in bg_dict.items():
        if bg_k not in cleaned_backgrounds:
            if isinstance(bg_meta, dict):
                hint = bg_meta.get("visual_hint") or bg_meta.get("narration_context") or bg_k.replace("-", " ")
                paired_fgs = bg_meta.get("paired_foregrounds", [])
            elif isinstance(bg_meta, str):
                hint = bg_meta
                paired_fgs = []
            else:
                hint = str(bg_meta or bg_k).replace("-", " ")
                paired_fgs = []
            paired_desc = f", paired with {', '.join(paired_fgs)}" if paired_fgs else ""
            fallback_bg = (
                f"Cinematic wide-angle documentary environment of {hint}{paired_desc}, "
                f"atmospheric volumetric natural lighting matching narrative tone, 16:9 aspect ratio, "
                f"bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay"
            )
            cleaned_backgrounds[bg_k] = _sanitize_background_prompt(fallback_bg, bg_k)

    for fg_k, fg_meta in fg_dict.items():
        if fg_k not in cleaned_foregrounds:
            if isinstance(fg_meta, dict):
                hint = fg_meta.get("visual_hint") or fg_meta.get("narration_context") or fg_k.replace("-", " ")
                paired_bgs = fg_meta.get("paired_backgrounds", [])
            elif isinstance(fg_meta, str):
                hint = fg_meta
                paired_bgs = []
            else:
                hint = str(fg_meta or fg_k).replace("-", " ")
                paired_bgs = []
            paired_desc = f", harmonized with setting {', '.join(paired_bgs)}" if paired_bgs else ""
            fallback_fg = (
                f"Full-body {hint} figure in authentic period attire{paired_desc}, "
                f"head to toe visible, dramatic character rim light matching environment, "
                f"isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, no frames, 1:1 aspect ratio"
            )
            cleaned_foregrounds[fg_k] = _sanitize_foreground_prompt(fallback_fg, fg_k)

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

    # 3. Cross-DB State Transitions:
    # Update Director Plan status -> 'Prompted' and Story Library status -> 'Produced'
    try:
        import scripts.ag_notion_bridge as bridge
        # 3a. Update Director Plan status -> 'Prompted'
        dir_res = bridge.resolve_episode_director_db(episode_id, task_id=task_id, create_if_missing=False)
        if isinstance(dir_res, dict) and not dir_res.get("error"):
            subpage_id = dir_res.get("subpage_id")
            if subpage_id:
                bridge.update_page_properties(subpage_id, {"Status": {"status": {"name": "Prompted"}}})
                logger.info(f"[prompt_forge] Transitioned Director Plan [{episode_id}] status to 'Prompted'")

        # 3b. Update Story Library status -> 'Produced'
        story_db_id = bridge.resolve_id("story")
        if story_db_id:
            q_story = bridge.query_db(story_db_id, filter_obj={"or": [
                {"property": "Task ID", "rich_text": {"equals": episode_id}},
                {"property": "Episode ID", "rich_text": {"equals": episode_id}}
            ]})
            if q_story.get("results"):
                story_page_id = q_story["results"][0]["id"]
                bridge.update_page_properties(story_page_id, {"Status": {"status": {"name": "Produced"}}})
                logger.info(f"[prompt_forge] Transitioned Story Library [{episode_id}] status to 'Produced'")
    except Exception as _st_err:
        logger.warning(f"[prompt_forge] Notice updating downstream Notion statuses: {_st_err}")
