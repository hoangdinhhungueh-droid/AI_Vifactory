#!/usr/bin/env python3
"""Continuity + Retake helper for the Image Asset Library (Rule 70, muc 2 + muc 4).

Standalone, read-mostly Notion API helper (mirrors scripts/pull_approved_images.py's
auth/query style). Historically NOT imported by the live s4-s7 render stages -- this
is a CLI/import-able utility for QC-time use (Notion AI chat, or a future pipeline
stage). gate_before_retake() below is the WIRED entrypoint: it is the one call site
any retake trigger (Notion AI chat, or a future automated stage) must call before
actually generating a new attempt, so muc 2's hard budget cap and muc 4's continuity
lookup are always exercised together instead of being orphaned standalone functions.
It still never touches the live s4-s7 render stages of an in-progress render.

NOTE on muc 2 (retake attempt budget): the Image Asset Library already tracks this
per-row via the existing "Review Round" number property (GATE: max 2 regen rounds;
round 3 still failing -> set Status/AI Verdict to Needs Human and stop). This helper
reads that existing field rather than re-implementing a counter, so it stays in sync
with the same gate Notion AI already enforces manually.

Usage:
  NOTION_TOKEN=... python3 scripts/continuity_retake_helper.py last-accepted \
      --episode-id genghis-khan-2026-ep005 --reuse-key-prefix hero_temujin

  NOTION_TOKEN=... python3 scripts/continuity_retake_helper.py check-budget \
      --episode-id genghis-khan-2026-ep005 --scene-index 12

  NOTION_TOKEN=... python3 scripts/continuity_retake_helper.py gate-before-retake \
      --episode-id genghis-khan-2026-ep005 --scene-index 12 --reuse-key-prefix hero_temujin

All subcommands print JSON to stdout and never write to Notion.
"""
import argparse
import json
import os
import urllib.error
import urllib.request

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"
DB_TITLE = "Image Asset Library"

# Keep in sync with the Image Asset Library's "Review Round" property gate
# (Skill AI Rule 70 muc 2): round 0/1/2 allowed, round >= MAX_REVIEW_ROUND means
# the attempt budget is exhausted and the row should already be Needs Human.
MAX_REVIEW_ROUND = 2


def _token():
    return os.environ.get("NOTION_TOKEN")


def _request(method, path, token, body=None):
    url = API_BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"raw_error": str(e)}
        return e.code, payload


def find_database_id(token):
    status, payload = _request("POST", "/search", token, {"query": DB_TITLE, "filter": {"value": "database", "property": "object"}})
    if status != 200:
        raise RuntimeError("search failed: " + json.dumps(payload)[:300])
    for result in payload.get("results", []):
        title_parts = result.get("title", [])
        title_text = "".join(t.get("plain_text", "") for t in title_parts)
        if DB_TITLE.lower() in title_text.lower():
            return result["id"]
    raise RuntimeError("database not found: " + DB_TITLE)


def _prop_text(props, name):
    prop = props.get(name)
    if not prop:
        return ""
    t = prop.get("type")
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    return ""


def _prop_number(props, name):
    prop = props.get(name)
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def _prop_select_or_status(props, name):
    prop = props.get(name)
    if not prop:
        return None
    if prop.get("type") == "select" and prop.get("select"):
        return prop["select"].get("name")
    if prop.get("type") == "status" and prop.get("status"):
        return prop["status"].get("name")
    return None


def _query_scene_rows(token, database_id, episode_id, scene_index=None, reuse_key_prefix=None):
    and_filters = [{"property": "Episode ID", "rich_text": {"equals": episode_id}}]
    if scene_index is not None:
        and_filters.append({"property": "Scene Index", "number": {"equals": scene_index}})
    if reuse_key_prefix is not None:
        and_filters.append({"property": "Reuse Key", "rich_text": {"starts_with": reuse_key_prefix}})
    body = {"filter": {"and": and_filters}, "page_size": 100}
    status, payload = _request("POST", "/databases/%s/query" % database_id, token, body)
    if status != 200:
        raise RuntimeError("query failed: " + json.dumps(payload)[:300])
    return payload.get("results", [])


def last_accepted_shot(token, episode_id, reuse_key_prefix):
    """Rule 70 muc 4: find the most recently accepted (Approved / Pulled by VPS)
    row for a given reuse-key family so the NEXT prompt can be built as a
    continuation of it instead of restarting from scratch.
    Returns the row dict with the fields needed to seed a continuation prompt,
    or None if nothing accepted yet.
    """
    database_id = find_database_id(token)
    rows = _query_scene_rows(token, database_id, episode_id, reuse_key_prefix=reuse_key_prefix)
    accepted = [r for r in rows if _prop_select_or_status(r.get("properties", {}), "Status") in ("Approved", "Pulled by VPS")]
    if not accepted:
        return None
    accepted.sort(key=lambda r: r.get("last_edited_time", ""), reverse=True)
    top = accepted[0]
    props = top.get("properties", {})
    return {
        "page_id": top["id"],
        "reuse_key": _prop_text(props, "Reuse Key"),
        "scene_index": _prop_number(props, "Scene Index"),
        "layer_type": _prop_select_or_status(props, "Layer Type"),
        "ai_review_notes": _prop_text(props, "AI Review Notes"),
        "status": _prop_select_or_status(props, "Status"),
    }


def check_review_round_budget(token, episode_id, scene_index):
    """Rule 70 muc 2: read the EXISTING "Review Round" field for this scene's
    row (single row per scene, incremented on each regen) and report whether
    the attempt budget is exhausted, instead of re-implementing a separate
    counter that could drift out of sync with the Notion-side gate.
    """
    database_id = find_database_id(token)
    rows = _query_scene_rows(token, database_id, episode_id, scene_index=scene_index)
    if not rows:
        return {"scene_index": scene_index, "found": False}
    row = rows[0]
    props = row.get("properties", {})
    review_round = _prop_number(props, "Review Round") or 0
    return {
        "scene_index": scene_index,
        "found": True,
        "page_id": row["id"],
        "review_round": review_round,
        "max_review_round": MAX_REVIEW_ROUND,
        "ai_verdict": _prop_select_or_status(props, "AI Verdict"),
        "budget_exceeded": review_round >= MAX_REVIEW_ROUND,
    }


def gate_before_retake(token, episode_id, scene_index, reuse_key_prefix=None):
    """WIRED entrypoint (Rule 70 muc 2 hard gate + muc 4 continuity, combined).

    Any process that is about to trigger a NEW image-generation attempt for
    this scene (Notion AI chat, or a future automated retake stage) should
    call this FIRST:
      - Raises RuntimeError if the attempt budget is already exhausted
        (muc 2, cap 3 lan: review_round 0/1/2 allowed, >=2 means the 3rd
        attempt already happened and used its round -- stop, do not retake
        again, set Status/AI Verdict to Needs Human instead).
      - Otherwise returns {budget, last_accepted} so the caller can seed the
        next attempt's prompt as a continuation of the last accepted shot
        (muc 4) instead of restarting from scratch.

    This never writes to Notion; the caller is still responsible for actually
    incrementing Review Round when it records the new attempt.
    """
    budget = check_review_round_budget(token, episode_id, scene_index)
    if budget.get("found") and budget.get("budget_exceeded"):
        raise RuntimeError(
            "BLOCKED: scene_index=%s review_round=%s >= max_review_round=%s -- "
            "attempt budget exhausted (Rule 70 muc 2, cap 3 lan). Set Status/AI "
            "Verdict to Needs Human instead of retaking again."
            % (scene_index, budget.get("review_round"), budget.get("max_review_round"))
        )
    last_accepted = None
    if reuse_key_prefix:
        last_accepted = last_accepted_shot(token, episode_id, reuse_key_prefix)
    return {"budget": budget, "last_accepted": last_accepted}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("last-accepted")
    p1.add_argument("--episode-id", required=True)
    p1.add_argument("--reuse-key-prefix", required=True)

    p2 = sub.add_parser("check-budget")
    p2.add_argument("--episode-id", required=True)
    p2.add_argument("--scene-index", required=True, type=int)

    p3 = sub.add_parser("gate-before-retake")
    p3.add_argument("--episode-id", required=True)
    p3.add_argument("--scene-index", required=True, type=int)
    p3.add_argument("--reuse-key-prefix", required=False, default=None)

    args = ap.parse_args()
    token = _token()
    if not token:
        print(json.dumps({"error": "NOTION_TOKEN not set"}))
        raise SystemExit(1)

    if args.cmd == "last-accepted":
        result = last_accepted_shot(token, args.episode_id, args.reuse_key_prefix)
    elif args.cmd == "check-budget":
        result = check_review_round_budget(token, args.episode_id, args.scene_index)
    else:
        try:
            result = gate_before_retake(token, args.episode_id, args.scene_index, args.reuse_key_prefix)
            result["blocked"] = False
        except RuntimeError as e:
            result = {"blocked": True, "error": str(e)}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
