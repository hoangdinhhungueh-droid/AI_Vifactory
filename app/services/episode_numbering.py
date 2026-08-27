"""
episode_numbering.py -- Delayed EP increment (2026-08-23).

Problem: previously, get_next_episode_id() (in trend_gate_ai.py) computed the
next episode number correctly, but the Gate-1 sender scripts (e.g.
send_dynamic_gate1.py) immediately wrote a Notion Story Library row for EVERY
reasoned topic -- including topics the human later rejects at Gate 1. That
permanently "burns" an episode number on a topic that never gets produced.

Fix: split PREVIEW from COMMIT.
  1. Gate-1 senders keep calling get_next_episode_id() to PREVIEW the number
     shown in the "/run task:<episode_id>" message, but must call
     cache_pending_task() instead of writing to Notion directly. This only
     drops a JSON file under /var/vf/pending_tasks/, nothing is claimed yet.
  2. app.pipeline.run_episode.run_pipeline() calls commit_if_pending(episode_id)
     right after episode_id is resolved -- i.e. exactly when the user's
     "/run task:<episode_id>" actually triggers POST /api/v1/run-episode.
     Only then is the real Notion Story Library row written (the true
     "increment"), and the pending cache file is removed so it can never be
     double-committed on retries.
  3. If a topic is rejected at Gate 1 and /run is never typed, the cache
     file is simply never consumed -- no Notion row, no number burned.

Both functions fail open (log + return False) so a Notion outage never
blocks Gate-1 sending or episode production.
"""
import os

# --- PATCH: FORCED IPV4 FOR NOTION API ---
import socket
_old_getaddrinfo = socket.getaddrinfo
def _new_getaddrinfo(*args, **kwargs):
    res = _old_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET]
socket.getaddrinfo = _new_getaddrinfo
# ----------------------------------------
import json
import time
import logging

logger = logging.getLogger(__name__)

PENDING_DIR = "/var/vf/pending_tasks"
PENDING_CACHE_TTL_HOURS = 24
STORY_DB_ID = "b0301989-2400-836b-bdb5-8131fea17736"
NOTION_PAGES_URL = "https://api.notion.com/v1/pages"


def _pending_path(episode_id: str) -> str:
    safe_id = str(episode_id).strip()
    return os.path.join(PENDING_DIR, safe_id + ".json")


def cache_pending_task(episode_id: str, market: str, payload: dict) -> str:
    """Save a pending (not-yet-committed) task's metadata to disk.

    payload may include: topic_name, keyword, niche_brief, story_arcs,
    virality_score. Nothing is written to Notion by this call.
    """
    os.makedirs(PENDING_DIR, exist_ok=True)
    # Sweep expired caches before adding a new one: stale pending files are what
    # made get_next_episode_id() skip numbers (each stale file still claims an EP).
    try:
        swept = cleanup_stale_pending_tasks()
        if swept:
            logger.info("[episode_numbering] swept %d stale pending cache(s) before caching %s", swept, episode_id)
    except Exception as _ce:
        logger.debug("[episode_numbering] stale sweep failed: %s", _ce)
    path = _pending_path(episode_id)
    data = {"episode_id": episode_id, "market": (market or "EN").upper(), "cached_at": time.time()}
    data.update(payload or {})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("[episode_numbering] cached pending task %s market=%s (NOT yet committed to Notion)", episode_id, market)
    return path


def remove_pending_task(episode_id: str) -> bool:
    """Remove a pending task cache file matching episode_id (case-insensitive & prefix-tolerant)."""
    if not episode_id:
        return False
    safe_id = str(episode_id).strip()
    removed = False
    path = _pending_path(safe_id)
    if os.path.exists(path):
        try:
            os.remove(path)
            removed = True
        except Exception:
            pass
    if os.path.exists(PENDING_DIR):
        for fname in os.listdir(PENDING_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(PENDING_DIR, fname)
            f_clean = fname[:-5]
            if (fname.lower() == (safe_id.lower() + ".json") or
                f_clean.lower() == safe_id.lower() or
                f_clean.lower().startswith(safe_id.lower() + "_") or
                safe_id.lower() in f_clean.lower()):
                try:
                    os.remove(fpath)
                    removed = True
                except Exception:
                    pass
    return removed


def _write_story_library_row(episode_id: str, market: str, data: dict) -> bool:
    import httpx
    ntoken = os.getenv("NOTION_TOKEN")
    if not ntoken:
        logger.warning("[episode_numbering] NOTION_TOKEN missing, cannot commit %s", episode_id)
        return False
    headers = {
        "Authorization": "Bearer " + ntoken,
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    mkt = (market or "EN").upper()
    topic_name = data.get("topic_name") or episode_id
    if str(topic_name).startswith(f"[{mkt}]"):
        name_title = str(topic_name)
    else:
        name_title = f"[{mkt}] {topic_name}"
    try:
        raw_v = float(data.get("virality_score", 0) or 0)
        virality_num = int(round(raw_v * 100 if raw_v <= 1.0 else raw_v))
    except Exception:
        virality_num = 0
    props = {
        "Name": {"title": [{"type": "text", "text": {"content": name_title}}]},
        "Task ID": {"rich_text": [{"type": "text", "text": {"content": str(episode_id)}}]},
        "Episode ID": {"rich_text": [{"type": "text", "text": {"content": str(episode_id)}}]},
        "Keyword": {"rich_text": [{"type": "text", "text": {"content": str(data.get("keyword", ""))}}]},
        "Market": {"select": {"name": str(mkt)}},
        "Virality Score": {"number": virality_num},
        "Niche Angle Brief": {"rich_text": [{"type": "text", "text": {"content": str(data.get("niche_brief", ""))[:1999]}}]},
        "Story Direction (5 Arcs)": {"rich_text": [{"type": "text", "text": {"content": str(data.get("story_arcs", ""))[:1999]}}]},
        "Status": {"status": {"name": "Draft"}},
    }
    bqs = data.get("breakout_queries") or []
    bqs_clean = [str(q.get("query") if isinstance(q, dict) else q).strip() for q in bqs if q]
    bqs_clean = [q for q in bqs_clean if q]
    if bqs_clean:
        props["Rising Queries"] = {"rich_text": [{"type": "text", "text": {"content": ", ".join(bqs_clean)[:1999]}}]}

    # 1. Check if page already exists in Story Library to avoid duplicate rows
    try:
        q_body = {
            "filter": {
                "or": [
                    {"property": "Task ID", "rich_text": {"equals": str(episode_id)}},
                    {"property": "Episode ID", "rich_text": {"equals": str(episode_id)}},
                ]
            },
            "page_size": 1
        }
        q_res = httpx.post(f"https://api.notion.com/v1/databases/{STORY_DB_ID}/query", headers=headers, json=q_body, timeout=10.0)
        if q_res.status_code == 200:
            results = q_res.json().get("results", [])
            if results:
                existing_page_id = results[0]["id"]
                patch_res = httpx.patch(f"https://api.notion.com/v1/pages/{existing_page_id}", headers=headers, json={"properties": props}, timeout=10.0)
                if patch_res.status_code in (200, 201):
                    logger.info("[episode_numbering] UPDATED existing Story Library row %s for %s", existing_page_id, episode_id)
                    return True
    except Exception as _qe:
        logger.warning("[episode_numbering] query existing check failed %s: %s", episode_id, _qe)

    # 2. If not found, create new row
    row = {
        "parent": {"database_id": STORY_DB_ID},
        "properties": props,
    }
    try:
        res = httpx.post(NOTION_PAGES_URL, headers=headers, json=row, timeout=15.0)
        if res.status_code in (200, 201):
            logger.info("[episode_numbering] COMMITTED %s to Story Library (delayed increment now claimed)", episode_id)
            return True
        logger.warning("[episode_numbering] Notion write failed %s: %s %s", episode_id, res.status_code, res.text[:300])
        return False
    except Exception as e:
        logger.warning("[episode_numbering] Notion write error for %s: %s", episode_id, e)
        return False


def cleanup_stale_pending_tasks() -> int:
    if not os.path.exists(PENDING_DIR):
        return 0
    cutoff_time = time.time() - (PENDING_CACHE_TTL_HOURS * 3600)
    deleted = 0
    for fname in os.listdir(PENDING_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(PENDING_DIR, fname)
        try:
            mtime = os.path.getmtime(fpath)
            if mtime < cutoff_time:
                os.remove(fpath)
                deleted += 1
                logger.info("[episode_numbering] cleaned stale cache %s (age > %dh)", fname, PENDING_CACHE_TTL_HOURS)
        except Exception as e:
            logger.debug("[episode_numbering] cleanup error on %s: %s", fname, e)
    return deleted


def commit_if_pending(episode_id: str) -> bool:
    """Call at the exact moment production starts (run_pipeline entry).

    If a cached pending task matches this episode_id, write it to the Story
    Library now (the real, delayed increment) and remove the cache file.
    Supports exact match, case-insensitive match, or prefix matching.
    No-op (returns False) if no cache file exists -- e.g. episode_id was
    typed manually, or was already committed by a previous run.
    """
    if not episode_id:
        return False
    safe_id = str(episode_id).strip()
    path = _pending_path(safe_id)
    if not os.path.exists(path):
        found_file = None
        if os.path.exists(PENDING_DIR):
            for fname in os.listdir(PENDING_DIR):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(PENDING_DIR, fname)
                f_clean = fname[:-5]
                # Case-insensitive filename or prefix match
                if (fname.lower() == (safe_id.lower() + ".json") or
                    f_clean.lower() == safe_id.lower() or
                    f_clean.lower().startswith(safe_id.lower() + "_") or
                    safe_id.lower() in f_clean.lower()):
                    found_file = fpath
                    break
                # Check contents
                try:
                    with open(fpath, "r", encoding="utf-8") as jf:
                        jdata = json.load(jf)
                    row_eid = str(jdata.get("episode_id", "")).strip()
                    if row_eid.lower() == safe_id.lower() or safe_id.lower() in row_eid.lower():
                        found_file = fpath
                        break
                except Exception:
                    pass
        if found_file:
            path = found_file
        else:
            return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_at = data.get("cached_at", 0)
        age_hours = (time.time() - cached_at) / 3600 if cached_at else 0
        if age_hours > PENDING_CACHE_TTL_HOURS:
            logger.warning("[episode_numbering] stale pending task %s (age %.1fh > %dh TTL), removing", episode_id, age_hours, PENDING_CACHE_TTL_HOURS)
            try:
                os.remove(path)
            except Exception:
                pass
            return False
        market = data.get("market", "EN")
        resolved_eid = data.get("episode_id") or episode_id
        ok = _write_story_library_row(resolved_eid, market, data)
        if ok:
            try:
                os.remove(path)
            except Exception:
                pass
        return ok
    except Exception as e:
        logger.warning("[episode_numbering] commit_if_pending failed for %s: %s", episode_id, e)
        return False
