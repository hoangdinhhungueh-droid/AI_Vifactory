
# app/services/trend_brain_mirror.py — Trend Brain (Notion DB) as the keyword store.
# Created 10/08/2026 (user directive): keyword library storage moved OFF VPS
# files (data/keyword_library.json deleted) INTO the Notion DB "VF Trend Brain"
# (under "DB Van hanh" hub). trend_commit also mirrors every committed keyword
# here (status "Approved->Story") instead of file storage.
#
# Field map (one Trend Brain DB row per keyword):
#   Keyword (title)          <- subject text
#   Market (select)          <- US / JP / KR
#   Pipeline Status (status) <- available="New (from VPS)" | committed="Approved->Story"
#                               used="Used" | rejected="Rejected"
#   Trend Score (number)     <- latest virality_score (0..1)
#   QID (rich_text)          <- Wikipedia QID when known (anti-repeat key)
#   Discovered (date)        <- first_seen (set only on create)
#   Verdict Reason (rt)      <- machine meta: "src=<source> | abs=<abs_score> | n=<score_count> | last=<date>"
#   Trend Source (multi)     <- origin lane(s) (virality / library_rescore / notion_ai_gate_*)
#
# Best-effort everywhere (same contract as the old JSON library): never raises
# into the discovery pipeline; failures are logged and callers degrade to empty
# results, not a crashed run.

import os

import json
import logging
import re
import time
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


from core.net_utils import ipv4_urlopen

DB_ID = os.getenv("TREND_BRAIN_DB_ID", "4c101989-2400-8334-8016-01d4f463b09f")
# CANONICAL_LABEL_2026_08_23: Story Library DB id, used by is_keyword_locked()
# to check whether a keyword already has an in-flight/complete story row.
STORY_DB_ID = os.getenv("STORY_LIBRARY_DB_ID", "b0301989-2400-836b-bdb5-8131fea17736")
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"
_REQ_GAP_SEC = 0.35  # Notion rate-limit courtesy (~3 req/s sustained)
_ENV_LOADED = False

_STATUS_TO_DB = {
    "available": "New (from VPS)",
    "committed": "Approved→Story",
    "used": "Used",
    "rejected": "Rejected",
}
_DB_TO_STATUS = {v: k for k, v in _STATUS_TO_DB.items()}

# CANONICAL_LABEL_2026_08_23: Pipeline Status is now the ONLY trend-brain
# status field (the orphan "Storyable Verdict" property was removed from the
# DB — it had no reader anywhere in the pipeline). These are the Pipeline
# Status / Story Library Status values that mean "already claimed" for
# is_keyword_locked() below.
_LOCKED_PIPELINE_STATUSES = {"Approved→Story", "Used"}
_LOCKED_STORY_STATUSES = {"Draft", "Gate Passed", "Locked"}


def _token():
    global _ENV_LOADED
    # ALREADY_PATCHED_1108C (11/08/2026): secrets env file = source of truth, last NOTION_TOKEN line wins (user directive); process env = fallback only
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
                        pass  # no break: last NOTION_TOKEN line in env file wins
        except Exception as e:
            logger.warning("[trend_brain] could not load secrets env: %s", e)
    return os.environ.get("NOTION_TOKEN")


def _call(method, path, payload=None):
    tok = _token()
    if not tok:
        logger.warning("[trend_brain] NOTION_TOKEN missing - skip %s %s", method, path)
        return None
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with ipv4_urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        err_body = ""
        if hasattr(e, "read"):
            try:
                err_body = e.read().decode()
            except Exception as _rd_err:
                logger.debug("Error decoding err_body: %s", _rd_err)
        logger.warning("[trend_brain] %s %s failed (tok=%s, db=%s): %s | Body: %s", method, path, tok[-4:], DB_ID, e, err_body)
        return None
    finally:
        time.sleep(_REQ_GAP_SEC)


def _rt(text):
    return [{"type": "text", "text": {"content": text}}] if text else []


# YT_LABEL_RULES_20260819: propagate platform-safety labels from keyword rows into downstream story/upload gates.
def _yt_labels_for_subject(subject, scores=None):
    """Return (labels, treatment_note) for Trend Brain YouTube Safety Label fields.
    Sensitive true-crime is allowed, but must be handled as non-graphic case-solving documentary.
    Hard blocks only apply to current partisan politics, mainstream-religion attack framing,
    explicit sexual/18+ packaging, graphic violence/how-to harm, and child exploitation framing.
    """
    text = (subject or '').lower()
    labels = []
    note = ''
    truecrime_terms = ['killer','ripper','murder','serial','gacy','bundy','dahmer','rader','golden state','조두순','n번방','nth room','sarin','오우무','aum','真理教','サリン','신창원','유영철']
    fraud_terms = ['fraud','scam','ponzi','madoff','enron','ftx','theranos','livedoor','ライブドア','worldcom','lehman','다단계','보이스피싱','전세사기','동양그룹']
    gambling_terms = ['gambling','casino','slot','pachinko','パチンコ','도박','강원랜드','바다이야기','사행성']
    societal_terms = ['kodokushi','孤独死','過労死','ひきこもり','引きこもり','고독사','은둔']
    history_terms = ['war','uprising','movement','occupation','광주','민주화','일제강점기','한국전쟁','제주 4.3','을미사변','roman empire','byzantine','crusade','genghis khan','mongol','ottoman']
    if any(t in text for t in truecrime_terms):
        labels += ['YT-Sensitive-TrueCrime','YT-NonGraphic-Required','YT-Investigation-CaseSolving']
        note = 'CASE-SOLVING DOCUMENTARY ONLY: focus on investigation, reasoning, evidence, capture/accountability; no graphic scene, method instruction, sexual detail, victim exploitation, or killer glorification.'
    if any(t in text for t in ['sarin','aum','真理教','오우무']):
        labels = [x for x in labels if x != 'YT-Sensitive-TrueCrime'] + ['YT-Sensitive-CultCrime','YT-NonGraphic-Required','YT-Investigation-CaseSolving']
        note = 'SENSITIVE CULT/TRUE CRIME: manipulation/investigation/accountability angle only; avoid mainstream-religion framing, graphic violence, method detail, and sensational cult panic.'
    if any(t in text for t in history_terms):
        labels += ['YT-History-Factual-Neutral']
        note = note or 'FACTUAL HISTORY ONLY: neutral, source-backed, no current partisan/election persuasion or subjective political viewpoint.'
    if any(t in text for t in fraud_terms):
        labels += ['YT-Fraud-Education']
        note = note or 'FRAUD/SCAM EDUCATION: explain mechanism, red flags, accountability; no how-to fraud instruction.'
    if any(t in text for t in gambling_terms):
        labels += ['YT-Gambling-Awareness']
        note = note or 'GAMBLING AWARENESS ONLY: cautionary educational framing on psychological manipulation & regulatory loopholes; no promotion, how-to, or glamorization.'
    if any(t in text for t in societal_terms):
        labels += ['YT-Societal-Crisis-Documentary']
        note = note or 'SOCIETAL DOCUMENTARY ONLY: objective analysis of demographic structure and social welfare gaps; empathetic & constructive framing.'
    # stable order + de-dup
    ordered=[]
    for x in labels:
        if x not in ordered:
            ordered.append(x)
    if not ordered:
        ordered=['YT-Safe']
        note='Standard platform-safe nonfiction treatment.'
    return ordered, note

def _title_of(page):
    try:
        parts = page["properties"]["Keyword"]["title"]
        return "".join(p.get("plain_text", "") for p in parts)
    except Exception:
        return ""


def _plain(props, name):
    parts = props.get(name, {}).get("rich_text", [])
    return "".join(p.get("plain_text", "") for p in parts)


def _row_to_dict(page):
    props = page.get("properties", {})
    v = props.get("Trend Score", {}).get("number")
    status_db = (props.get("", {}).get("status") or {}).get("name", "")
    vr = _plain(props, "Verdict Reason")
    abs_score, score_count = 0.0, 1
    m = re.search(r"abs=([0-9.]+)", vr)
    if m:
        try:
            abs_score = float(m.group(1))
        except Exception:
            abs_score = 0.0
    m2 = re.search(r"n=(\d+)", vr)
    if m2:
        try:
            score_count = int(m2.group(1))
        except Exception:
            score_count = 1
    sources = [o.get("name") for o in props.get("Trend Source", {}).get("multi_select", []) if o.get("name")]
    return {
        "page_id": page.get("id"),
        "subject": _title_of(page),
        "market": (props.get("Market", {}).get("select") or {}).get("name", "US"),
        "status": _DB_TO_STATUS.get(status_db, "available"),
        "pipeline_status": status_db,
        "virality_score": float(v) if v is not None else 0.0,
        "abs_score": abs_score,
        "score_count": score_count,
        "qid": _plain(props, "QID") or None,
        "sources": sources,
        "verdict_reason": vr,
    }


def _query(filter_obj=None, sorts=None):
    body = {"page_size": 100}
    if filter_obj:
        body["filter"] = filter_obj
    if sorts:
        body["sorts"] = sorts
    results, cursor = [], None
    for _ in range(10):  # hard cap 1000 rows
        if cursor:
            body["start_cursor"] = cursor
        resp = _call("POST", "/databases/%s/query" % DB_ID, body)
        if resp is None:
            break
        results.extend(resp.get("results", []))
        if resp.get("has_more") and resp.get("next_cursor"):
            cursor = resp["next_cursor"]
        else:
            break
    return results


def _find_page(subject, market):
    """Fast title-filter lookup, with a full-market scan fallback so a
    case-variant of an existing keyword never creates a duplicate row."""
    want = (subject or "").strip()
    if not want:
        return None
    market = (market or "US").upper()
    pages = _query({"and": [
        {"property": "Market", "select": {"equals": market}},
        {"property": "Keyword", "title": {"equals": want[:1900]}},
    ]})
    wl = want.lower()
    for p in pages:
        if _title_of(p).strip().lower() == wl:
            return p
    # fallback: full-market scan, case-insensitive compare in Python
    for p in _query({"property": "Market", "select": {"equals": market}}):
        if _title_of(p).strip().lower() == wl:
            return p
    return None


def upsert_scored(subject, market, scores=None, source="virality", status=None):
    """Add or update a scored subject. Same semantics as the old JSON library:
    existing row -> update Trend Score / abs meta / score_count (+status only if
    explicitly given, and NEVER downgrade a 'Used' row); new row -> create with
    Discovered=today.
    status: 'available' | 'committed' | 'used' | 'rejected' (or raw DB name)."""
    if not subject or not subject.strip():
        return False
    scores = scores or {}
    market = (market or "US").upper()
    today = datetime.now(timezone.utc).date().isoformat()
    existing = _find_page(subject, market)
    if existing:
        row = _row_to_dict(existing)
        new_v = scores.get("virality_score", row["virality_score"])
        new_a = scores.get("abs_score", row["abs_score"])
        n = row["score_count"] + 1
        note = ("src=%s | abs=%.3f | n=%d | last=%s" % (source, float(new_a), n, today))[:1900]
        merged_sources = sorted(set(row["sources"]) | {source})
        labels, treatment_note = _yt_labels_for_subject(subject, scores)
        props = {
            "Trend Score": {"number": round(float(new_v), 4)},
            "Verdict Reason": {"rich_text": _rt(note)},
            "Trend Source": {"multi_select": [{"name": s} for s in merged_sources]},
            "YouTube Safety Label": {"multi_select": [{"name": x} for x in labels]},
            "Upload Treatment Note": {"rich_text": _rt(treatment_note)},
        }
        if scores.get("qid"):
            props["QID"] = {"rich_text": _rt(str(scores["qid"]))}
        if status and row["pipeline_status"] != "Used":
            props[""] = {"status": {"name": _STATUS_TO_DB.get(status, status)}}
        resp = _call("PATCH", "/pages/%s" % existing["id"], {"properties": props})
        return bool(resp and resp.get("id"))
    db_status = _STATUS_TO_DB.get(status or "available", status or "New (from VPS)")
    new_v = float(scores.get("virality_score", 0.0) or 0.0)
    new_a = float(scores.get("abs_score", 0.0) or 0.0)
    note = ("src=%s | abs=%.3f | n=1 | last=%s" % (source, new_a, today))[:1900]
    payload = {
        "parent": {"database_id": DB_ID},
        "properties": {
            "Keyword": {"title": [{"type": "text", "text": {"content": subject.strip()[:1900]}}]},
            "Market": {"select": {"name": market}},
            "": {"status": {"name": db_status}},
            "Trend Score": {"number": round(new_v, 4)},
            "Discovered": {"date": {"start": today}},
            "Verdict Reason": {"rich_text": _rt(note)},
            "Trend Source": {"multi_select": [{"name": source}]},
            "YouTube Safety Label": {"multi_select": [{"name": x} for x in _yt_labels_for_subject(subject, scores)[0]]},
            "Upload Treatment Note": {"rich_text": _rt(_yt_labels_for_subject(subject, scores)[1])},
        },
    }
    if scores.get("qid"):
        payload["properties"]["QID"] = {"rich_text": _rt(str(scores["qid"]))}
    resp = _call("POST", "/pages", payload)
    if resp and resp.get("id"):
        logger.info("[trend_brain] created: %s (%s, %s)", subject.strip(), market, db_status)
        return True
    return False


def mark_used(subject, market):
    p = _find_page(subject, market)
    if not p:
        return False
    resp = _call("PATCH", "/pages/%s" % p["id"],
                 {"properties": {"": {"status": {"name": "Used"}}}})
    ok = bool(resp and resp.get("id"))
    if ok:
        logger.info("[trend_brain] marked used: %s (%s)", subject, market)
    return ok


def available_subjects(market=None, limit=None):
    """Available (scored, not committed, not used) subjects, Trend Score desc.
    Same return shape as the old JSON library entries."""
    filt = {"property": "", "status": {"equals": "New (from VPS)"}}
    if market:
        filt = {"and": [filt, {"property": "Market", "select": {"equals": market.upper()}}]}
    pages = _query(filt, sorts=[{"property": "Trend Score", "direction": "descending"}])
    rows = [_row_to_dict(p) for p in pages]
    if limit:
        rows = rows[: int(limit)]
    return rows


def get_subject(subject, market):
    p = _find_page(subject, market)
    return _row_to_dict(p) if p else None


# CANONICAL_LABEL_2026_08_23: keyword-lock check added as part of the Human
# Gate 1 / Trend Brain standardization plan (23/08/2026). Callers (discovery
# crawlers) should skip re-scoring/re-queuing any subject this returns True
# for, so an already-approved/used/in-flight keyword never gets re-surfaced
# as a "new" candidate.
def is_keyword_locked(subject, market=None):
    """Return True if `subject` is already claimed by the human-gate/
    production pipeline and must NOT be re-crawled or re-scored as new.

    Locked when either:
      - the Trend Brain row's Pipeline Status is "Approved→Story" or "Used", OR
      - a Story Library row with a matching Keyword has Status in
        {"Draft", "Gate Passed", "Locked"}.

    Best-effort / fail-open: any lookup error returns False so a transient
    Notion outage never blocks a legitimate crawl.
    """
    want = (subject or "").strip()
    if not want:
        return False

    try:
        p = _find_page(want, market or "US")
        if p:
            row = _row_to_dict(p)
            if row.get("pipeline_status") in _LOCKED_PIPELINE_STATUSES:
                return True
    except Exception as e:
        logger.warning("[trend_brain] is_keyword_locked Trend Brain lookup failed: %s", e)

    try:
        resp = _call("POST", "/databases/%s/query" % STORY_DB_ID, {
            "filter": {"property": "Keyword", "rich_text": {"contains": want[:1900]}},
            "page_size": 5,
        })
        if resp:
            for row in resp.get("results", []):
                st = (row.get("properties", {}).get("Status", {}).get("status") or {}).get("name")
                if st in _LOCKED_STORY_STATUSES:
                    return True
    except Exception as e:
        logger.warning("[trend_brain] is_keyword_locked Story Library lookup failed: %s", e)

    return False


def stats():
    pages = _query()
    by_market = {}
    for p in pages:
        r = _row_to_dict(p)
        d = by_market.setdefault(r["market"], {"total": 0, "available": 0, "committed": 0, "used": 0, "rejected": 0})
        d["total"] += 1
        if r["status"] in d:
            d[r["status"]] += 1
    return {"total": len(pages), "by_market": by_market, "backend": "notion_trend_brain"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(stats(), indent=2, ensure_ascii=False))
