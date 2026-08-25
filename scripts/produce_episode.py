"""Operational episode runner  (Notion brain -> VPS hands).

Usage:
  python scripts/produce_episode.py <episode_id> [--seed-only]

Real operation, no hardcoding:
  1. Resolve the Episodes Notion DB by name via /v1/search.
  2. Query it for the row whose `episode_id` property == <episode_id>.
  3. Read the first ```json brain_input code block from that page body.
  4. Write /var/vf/episodes/<episode_id>/brain_input.json  (S5 + motion_cards read this).
  5. Call run_pipeline(...) with the brain fields  (brain_mode = bool(story_text)).

--seed-only stops after step 4 (free; validates the Notion->file contract).
"""
import sys, os, json, asyncio
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ENV_PATH = "/root/secrets/.env"
try:
    for raw in open(ENV_PATH):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:]
        k, v = line.split("=", 1)
        k = k.strip(); v = v.strip().strip('"').strip("'")
        if v and k not in os.environ:
            os.environ[k] = v
except Exception as e:
    print("ENV_LOAD_ERR", e)

os.environ["VF_REQUIRE_BRAIN"] = "1"

import requests

NOTION_API = "https://api.notion.com/v1"


def _headers():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN missing")
    return {"Authorization": "Bearer " + token,
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"}


def _resolve_episodes_db():
    r = requests.post(NOTION_API + "/search", headers=_headers(),
                      json={"query": "Episodes",
                            "filter": {"property": "object", "value": "database"}},
                      timeout=60)
    r.raise_for_status()
    for res in r.json().get("results", []):
        title = "".join(t.get("plain_text", "") for t in res.get("title", []))
        if title.strip().lower() == "episodes":
            return res["id"]
    raise RuntimeError("Episodes database not found via search")


def _find_episode_page(db_id, episode_id):
    r = requests.post(NOTION_API + "/databases/" + db_id + "/query", headers=_headers(),
                      json={"filter": {"property": "episode_id",
                                       "rich_text": {"equals": episode_id}}},
                      timeout=60)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError("No Episodes row with episode_id=" + episode_id)
    return results[0]["id"]


def _read_brain_json(page_id):
    url = NOTION_API + "/blocks/" + page_id + "/children?page_size=100"
    while url:
        r = requests.get(url, headers=_headers(), timeout=60)
        r.raise_for_status()
        data = r.json()
        for blk in data.get("results", []):
            if blk.get("type") == "code":
                code = blk["code"]
                text = "".join(t.get("plain_text", "") for t in code.get("rich_text", []))
                if text.strip().startswith("{"):
                    return json.loads(text)
        if data.get("has_more"):
            url = NOTION_API + "/blocks/" + page_id + "/children?page_size=100&start_cursor=" + data.get("next_cursor")
        else:
            url = None
    raise RuntimeError("brain_input json code block not found on page")


def _seed_file(brain):
    eid = brain["episode_id"]
    d = Path("/var/vf/episodes") / eid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "brain_input.json"
    p.write_text(json.dumps(brain, ensure_ascii=False, indent=2))
    print("WROTE", p, p.stat().st_size, "bytes")
    return p


def _visual_terms(brain):
    vt = brain.get("visual_terms")
    if vt:
        return vt
    terms = []
    for s in brain.get("scenes", []):
        ip = s.get("image_prompt", "")
        terms.append(" ".join(ip.split()[:6]))
    return terms[:8]


async def _render(brain):
    from app.pipeline.run_episode import run_pipeline
    lang = brain.get("lang_code") or "en"
    if isinstance(lang, list):
        lang = lang[0] if lang else "en"
    res = await run_pipeline(
        episode_id=brain["episode_id"],
        niche=brain.get("niche", "documentary"),
        lang_code=lang,
        tts_backend="auto",
        story_text=brain["story"],
        visual_terms=_visual_terms(brain),
        bgm_mood=brain.get("bgm_mood", "dramatic"),
        hook_3s=brain.get("hook_3s"),
        scenes=brain.get("scenes"),
        character_pack=brain.get("character_pack"),
        art_style=brain.get("art_style"),
        trend_keywords=brain.get("trend_keywords"),
        brain=brain,
    )
    print("RESULT:", res)
    return res


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("-")]
    seed_only = "--seed-only" in sys.argv
    if not pos:
        print("usage: produce_episode.py <episode_id> [--seed-only]"); sys.exit(2)
    episode_id = pos[0]
    db_id = _resolve_episodes_db()
    print("EPISODES_DB", db_id)
    page_id = _find_episode_page(db_id, episode_id)
    print("PAGE", page_id)
    brain = _read_brain_json(page_id)
    print("BRAIN keys:", sorted(brain.keys()), "| scenes:", len(brain.get("scenes", [])))
    _seed_file(brain)
    if seed_only:
        print("SEED-ONLY done; skipping render."); return
    asyncio.run(_render(brain))


if __name__ == "__main__":
    main()
