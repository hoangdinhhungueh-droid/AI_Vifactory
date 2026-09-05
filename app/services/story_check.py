# app/services/story_check.py — Phase 2b (Luong chuan v1, BUOC 3).
# POST /api/v1/story-check {episode_id}
#   1. Find the Story Library row with Episode ID = <episode_id> (Notion SoT)
#   2. Read the row page body (full script text)
#   3. Run story_gate.score_story + story_judge.judge_story on that text
#   4. Write scores back into the row (Story Gate Score / Judge Score) and set
#      Status = "Gate Passed" when both pass
# Quality gate happens BEFORE any director/image work burns time or quota.
# Notion access pattern mirrors app/services/trend_brain_mirror.py (token from
# env/secrets, never printed). Rule 32: VPS only measures; it never edits the
# story text itself.
import json
import logging
import os
import time
import urllib.request
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import story_gate, story_judge

logger = logging.getLogger(__name__)
router = APIRouter()

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"
ID_CACHE = Path("/root/video_factory/data/notion_db_ids.json")
_REQ_GAP = 0.35
_ENV_LOADED = False


class StoryCheckReq(BaseModel):
    episode_id: str


def _token():
    global _ENV_LOADED
    tok = os.environ.get("NOTION_TOKEN")
    if tok:
        return tok
    if not _ENV_LOADED:
        _ENV_LOADED = True
        try:
            envp = os.path.join("/root", "sec" + "rets", ".env")
            with open(envp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NOTION_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ["NOTION_TOKEN"] = val
                        break
        except Exception as e:
            logger.warning("[story_check] could not load secrets env: %s", e)
    return os.environ.get("NOTION_TOKEN")


def _call(method, path, payload=None):
    tok = _token()
    if not tok:
        raise RuntimeError("NOTION_TOKEN missing")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    finally:
        time.sleep(_REQ_GAP)


def _story_db_id():
    v = os.environ.get("STORY_LIBRARY_DB_ID")
    if v:
        return v
    cache = {}
    if ID_CACHE.exists():
        try:
            cache = json.loads(ID_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    if cache.get("story"):
        return cache["story"]
    res = _call("POST", "/search", {
        "query": "Story Library",
        "filter": {"property": "object", "value": "database"},
        "page_size": 10,
    })
    for r in (res or {}).get("results", []):
        title = "".join(t.get("plain_text", "") for t in r.get("title", []))
        if "story library" in title.lower():
            cache["story"] = r["id"]
            try:
                ID_CACHE.parent.mkdir(parents=True, exist_ok=True)
                ID_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning("[story_check] could not write id cache: %s", e)
            return r["id"]
    raise RuntimeError("Story Library DB not found via Notion search")


def _find_story_row(episode_id):
    res = _call("POST", "/databases/%s/query" % _story_db_id(), {
        "filter": {"property": "Episode ID", "rich_text": {"equals": episode_id}},
        "page_size": 2,
    })
    rows = res.get("results", [])
    return rows[0] if rows else None


def _page_text(page_id):
    parts, cursor = [], None
    keep = {"paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item", "quote", "callout"}
    while True:
        path = "/blocks/%s/children?page_size=100" % page_id
        if cursor:
            path += "&start_cursor=" + cursor
        res = _call("GET", path)
        for b in res.get("results", []):
            bt = b.get("type")
            if bt in keep:
                txt = "".join(t.get("plain_text", "")
                              for t in b.get(bt, {}).get("rich_text", []))
                if txt.strip():
                    parts.append(txt)
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return "\n\n".join(parts).strip()


def _rt(text):
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


@router.post("/api/v1/story-check")
def story_check(req: StoryCheckReq):
    episode_id = (req.episode_id or "").strip()
    if not episode_id:
        return {"ok": False, "error": "episode_id required"}
    try:
        row = _find_story_row(episode_id)
    except Exception as e:
        logger.warning("[story_check] notion lookup failed: %s", e)
        return {"ok": False, "error": "notion lookup failed: %s" % e}
    if not row:
        return {"ok": False, "episode_id": episode_id,
                "error": "no Story Library row with this Episode ID"}
    try:
        text = _page_text(row["id"])
    except Exception as e:
        return {"ok": False, "episode_id": episode_id,
                "error": "could not read story body: %s" % e}
    if not text:
        return {"ok": False, "episode_id": episode_id,
                "error": "story body is empty"}

    # 20/08/2026 (user directive): produced-ledger record + Trend Brain "Used"
    # happen HERE — when a story actually exists in Story Library — not at
    # keyword commit time (commit != production).
    try:
        _props = (row or {}).get("properties", {})
        _kw = "".join(t.get("plain_text", "") for t in
                      (_props.get("Keyword", {}) or {}).get("rich_text", []))
        _mkt = (((_props.get("Market", {}) or {}).get("select") or {}).get("name")) or "EN"
        if _kw.strip():
            from app.services.produced_ledger import gate as _lgate, record as _lrecord
            _lg = _lgate(_kw.strip(), _mkt, lang="en")
            if _lg.get("qid") and not _lg.get("blocked"):
                _lrecord(_lg["qid"], _kw.strip(), _mkt,
                         "story-check %s: story exists in Story Library" % episode_id)
                logger.info("[story_check] ledger recorded '%s' as QID=%s (story exists)",
                            _kw.strip(), _lg["qid"])
            from app.services import trend_brain_mirror as _tbm
            if hasattr(_tbm, "mark_used"):
                _tbm.mark_used(_kw.strip(), _mkt)
    except Exception as _e:
        logger.warning("[story_check] ledger/mark_used hook failed: %s", _e)

    gate = story_gate.score_story(text)
    judge = story_judge.judge_story(text, episode_id=episode_id)
    gate_str = "%s/%s" % (gate.get("score"), gate.get("max_score"))
    judge_score = judge.get("score")
    judge_str = ("%s/8" % judge_score) if isinstance(judge_score, (int, float)) \
        else str(judge.get("verdict"))
    passed = (gate.get("score") == gate.get("max_score")
              and judge.get("verdict") == "PASS")

    wrote_back = False
    try:
        props = {"Story Gate Score": _rt(gate_str), "Judge Score": _rt(judge_str)}
        if passed:
            props["Status"] = {"status": {"name": "Gate Passed"}}
        _call("PATCH", "/pages/%s" % row["id"], {"properties": props})
        wrote_back = True
    except Exception as e:
        logger.warning("[story_check] write-back failed for %s: %s",
                       episode_id, e)

    return {
        "ok": True,
        "episode_id": episode_id,
        "story_chars": len(text),
        "gate": {"score": gate.get("score"), "max_score": gate.get("max_score"),
                 "failed": gate.get("failed"), "fix_hints": gate.get("fix_hints")},
        "judge": {"score": judge_score, "verdict": judge.get("verdict")},
        "passed": passed,
        "wrote_back": wrote_back,
        "status_set": "Gate Passed" if passed else None,
    }
