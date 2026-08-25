"""
Service: B3.5 Prompt Engineering Forge (/prompt:forge)
Single Source of Truth: HHTech GPT-5.6-Sol + Prompt Library Notion DB
Rule 120: Isolates prompt generation. FGs strictly generated on flat #FF00FF magenta background.
Rule 121: MUST prepend a LIVE fresh fetch of the Skill AI Notion page to the system prompt on
every call -- never rely on a cached/hardcoded rule snapshot (see scripts/skill_ai_live.py).
23/08/2026: Prompt Library restructured to 1-episode-per-subpage + child "Prompts" DB
(mirrors the Director Plan restructuring). push_prompts_to_notion now resolves/creates the
episode's own child DB via ag_notion_bridge.resolve_episode_prompt_db instead of writing to a
single flat DB. PROMPT_LIBRARY_DB_ID_FALLBACK is kept only as a last-resort fallback.
"""

import os, sys, json, requests
from pathlib import Path

def _load_env():
    from app.services.youtube_upload import _load_env as le
    le()

_load_env()

from app.services.hhtech_reasoner import call_gpt56_sol
from scripts.skill_ai_live import load_skill_ai_live

sys.path.insert(0, "/root/video_factory/scripts")
import ag_notion_bridge as _bridge  # 23/08/2026: per-episode Prompt Library subpage+DB resolver

NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN", "")
PROMPT_LIBRARY_DB_ID_FALLBACK = "8c801989-2400-831a-901d-014aebdc3b31"

def generate_scene_prompts(bg_dict: dict, fg_dict: dict, story_title: str) -> dict:
    """
    Calls HHTech GPT-5.6-Sol via dedicated reasoner to generate high-fidelity image prompts for unique BGs and FGs.
    Rule 121: always prepends a freshly-fetched (live, not cached) Skill AI digest.
    """
    skill_ai_context = load_skill_ai_live()

    system_prompt = (
        skill_ai_context + "\n\n" +
        "You are an elite Hollywood Visual Director and Master Prompt Engineer specialized in 2-layer historical documentary video production.\n"
        "Generate high-fidelity, photorealistic image prompts for the given Backgrounds (16:9) and Foregrounds (1:1).\n\n"
        "RULES FOR LAYER 1 BACKGROUNDS (16:9):\n"
        "- Wide-angle cinematic environment, historical architecture circa 1204, dramatic volumetric atmospheric lighting.\n"
        "- NO prominent human close-ups on background. Center/right clear for Layer 2 foreground overlay and bottom 20% safe-zone for subtitles.\n"
        "- Style: Photorealistic 8k cinematic historical documentary, rich textures, moody color grading, 16:9 aspect ratio.\n\n"
        "RULES FOR LAYER 2 FOREGROUNDS (1:1 Chroma-Key Cutout):\n"
        "- MUST ALWAYS include the exact mandatory clause: 'isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, studio portrait lighting, highly detailed historical subject, 1:1 aspect ratio'.\n"
        "- Clear, iconic historical portraits, armored crusaders, Venetian doges, imperial relics, gold coins, ledgers.\n\n"
        "Output ONLY a valid JSON object with schema:\n"
        "{\n"
        "  \"backgrounds\": {\n"
        "    \"<bg_key>\": \"<prompt string>\", ...\n"
        "  },\n"
        "  \"foregrounds\": {\n"
        "    \"<fg_key>\": \"<prompt string>\", ...\n"
        "  }\n"
        "}"
    )

    user_payload = {
        "title": story_title,
        "backgrounds_to_generate": bg_dict,
        "foregrounds_to_generate": fg_dict
    }

    raw_response = call_gpt56_sol(
        prompt=json.dumps(user_payload, ensure_ascii=False),
        system_prompt=system_prompt,
        max_tokens=3000,
        timeout=120.0
    )

    content = raw_response.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    return json.loads(content.strip())


def push_prompts_to_notion(prompts_data: dict, episode_id: str, task_id: str = None):
    """
    Pushes generated prompts to this episode's own Prompt Library child database
    (23/08/2026 subpage-per-episode restructuring -- resolved/created dynamically
    via ag_notion_bridge.resolve_episode_prompt_db). Archives old prompts for the
    same episode first, within that same child database, to keep idempotency.
    """
    if not NOTION_API_KEY:
        print("[WARN] No NOTION_API_KEY found, skipping Notion sync.")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    resolved = _bridge.resolve_episode_prompt_db(episode_id, task_id=task_id)
    if resolved.get("error"):
        print(f"[WARN] Could not resolve/create per-episode Prompt Library DB for {episode_id}: {resolved}. Falling back to flat DB.")
        prompt_library_db_id = PROMPT_LIBRARY_DB_ID_FALLBACK
    else:
        prompt_library_db_id = resolved["db_id"]
        if resolved.get("created"):
            print(f"Created new Prompt Library subpage+DB for {episode_id} (db={prompt_library_db_id}).")

    # 0. Query and archive existing prompts for this episode to maintain single-truth
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
                requests.patch(f"https://api.notion.com/v1/pages/{r['id']}", headers=headers, json={"archived": True}, timeout=10)
            if existing:
                print(f"Archived {len(existing)} older prompts for [{episode_id}] in this episode's Prompt Library DB.")
    except Exception as e:
        print(f"[WARN] Error cleaning old prompts: {e}")

    # 1. Backgrounds
    for bg_key, prompt in prompts_data.get("backgrounds", {}).items():
        bg_payload = {
            "parent": {"database_id": prompt_library_db_id},
            "properties": {
                "Title": {"title": [{"text": {"content": f"[{episode_id}] {bg_key} (BG 16:9)"}}]},
                "prompt_text": {"rich_text": [{"text": {"content": prompt[:2000]}}]},
                "category": {"select": {"name": "image"}},
                "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 16:9, Safe Zone: Bottom 20%"}}]},
                "version": {"number": 1}
            }
        }
        res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=bg_payload, timeout=10)
        if res.status_code in (200, 201):
            print(f"Pushed BG prompt {bg_key} to Notion Prompt Library DB \u2705")
        else:
            print(f"[WARN] Failed to push BG prompt {bg_key}: {res.status_code} {res.text}")

    # 2. Foregrounds
    for fg_key, prompt in prompts_data.get("foregrounds", {}).items():
        fg_payload = {
            "parent": {"database_id": prompt_library_db_id},
            "properties": {
                "Title": {"title": [{"text": {"content": f"[{episode_id}] {fg_key} (FG 1:1 #FF00FF)"}}]},
                "prompt_text": {"rich_text": [{"text": {"content": prompt[:2000]}}]},
                "category": {"select": {"name": "image"}},
                "variables": {"rich_text": [{"text": {"content": "Aspect Ratio: 1:1, Chroma Key: Flat #FF00FF Magenta Background"}}]},
                "version": {"number": 1}
            }
        }
        res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=fg_payload, timeout=10)
        if res.status_code in (200, 201):
            print(f"Pushed FG prompt {fg_key} to Notion Prompt Library DB \u2705")
        else:
            print(f"[WARN] Failed to push FG prompt {fg_key}: {res.status_code} {res.text}")
