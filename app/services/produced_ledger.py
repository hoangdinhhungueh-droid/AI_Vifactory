# app/services/produced_ledger.py - Anti-repeat "Produced Topics" ledger. Cluster (4), v5.
# Canonical entity = Wikipedia QID (language-agnostic: Enron=Q480770) so EN/JP/KR variants
# of the SAME subject collapse to ONE id. Replaces the old cooldown that compared raw
# keyword strings (which let translations / rephrasings slip through and repeat).
# File-based JSON (NO Notion schema change) -> safe & reversible. Additive, not wired.

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

LEDGER_PATH = os.getenv("PRODUCED_LEDGER_PATH", "/root/video_factory/data/produced_ledger.json")
COOLDOWN_DAYS = int(os.getenv("S1_COOLDOWN_DAYS", "7"))
_UA = {"User-Agent": "video-factory-trend/5.0 (admin@vifactory.com)"}


def _httpx():
    try:
        import httpx
        return httpx
    except Exception:
        return None


def wikipedia_qid(title, lang="en", timeout=15.0):
    """Resolve a title to its Wikidata QID via the free MediaWiki API. None if not found."""
    httpx = _httpx()
    if httpx is None or not title:
        return None
    url = "https://" + lang + ".wikipedia.org/w/api.php"
    params = {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
              "redirects": 1, "titles": title, "format": "json"}
    try:
        r = httpx.get(url, params=params, headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return None
        pages = ((r.json().get("query") or {}).get("pages") or {})
        for p in pages.values():
            qid = (p.get("pageprops") or {}).get("wikibase_item")
            if qid:
                return qid
        return None
    except Exception as e:
        logger.warning("[ledger] qid lookup failed %s: %s", title, e)
        return None


def _load():
    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    tmp = LEDGER_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, LEDGER_PATH)


# 20/08/2026 (user directive): produced/in-production = PERMANENTLY blocked, no cooldown.
# A produced topic is never re-picked even if it trends again; the gate yields the slot
# to other specific candidates from the pool. Set S1_PERMANENT_BLOCK=0 to restore cooldown.
PERMANENT_BLOCK = os.getenv("S1_PERMANENT_BLOCK", "1") == "1"


def is_blocked(qid, now=None, cooldown_days=None):
    """True if qid was produced. Since 20/08/2026 this is permanent (no cooldown) by default."""
    if not qid:
        return False
    rec = _load().get(qid)
    if not rec:
        return False
    if PERMANENT_BLOCK:
        return True
    cd = COOLDOWN_DAYS if cooldown_days is None else cooldown_days
    now = now or datetime.now(timezone.utc)
    try:
        produced = datetime.fromisoformat(rec["produced_at"])
    except Exception:
        return True
    return (now - produced).days < cd


def record(qid, title, market, theme=None):
    if not qid:
        return False
    data = _load()
    data[qid] = {"title": title, "market": market, "theme": theme,
                 "produced_at": datetime.now(timezone.utc).isoformat()}
    _save(data)
    return True


def gate(title, market, lang="en", theme=None):
    """One-shot gate: resolve QID then check block status. Returns {qid, blocked, canonical}.
    blocked=True -> skip candidate (anti-repeat); canonical=False -> no QID (needs review)."""
    qid = wikipedia_qid(title, lang=lang)
    return {"qid": qid, "blocked": is_blocked(qid), "canonical": bool(qid)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("ledger path:", LEDGER_PATH, "| cooldown", COOLDOWN_DAYS, "d")
    print("Enron QID ->", wikipedia_qid("Enron"))  # expect Q480770
    print("gate('Enron scandal') ->", gate("Enron scandal", "US", lang="en", theme="business"))
