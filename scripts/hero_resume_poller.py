#!/usr/bin/env python3
"""Hero-approval resume poller (Moc 1 hero-flag flow).

Polls Notion DB "Image Asset Library" for rows where:
  - Is Hero Reference = true
  - Status = Approved
  - not yet Status = Pulled by VPS (query already excludes those, since
    Approved != Pulled by VPS)

Current version: detects eligible hero rows, prints their reuse info
(Reuse Key / Tags / Prompt / Episode ID), and marks Status = Pulled by VPS
so the row is not reprocessed.

TODO (not yet wired): trigger continuation of scene image generation for
the remaining scenes of that episode using this hero's Reuse Key/Tags/
Prompt as a text style-anchor (img2img free-tier confirmed unavailable).
Needs S5 resume-capability confirmed before wiring.

Run manually or via cron:
  set -a; source /root/secrets/.env; set +a
  python3 scripts/hero_resume_poller.py
"""
import os
import sys
import json
import urllib.request
import urllib.error

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"
DB_TITLE = "Image Asset Library"


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


def query_hero_approved(token, database_id):
    body = {
        "filter": {
            "and": [
                {"property": "Is Hero Reference", "checkbox": {"equals": True}},
                {"property": "Status", "status": {"equals": "Approved"}},
            ]
        }
    }
    status, payload = _request("POST", "/databases/%s/query" % database_id, token, body)
    if status != 200:
        raise RuntimeError("query failed: " + json.dumps(payload)[:300])
    return payload.get("results", [])


def get_prop_text(props, name):
    prop = props.get(name)
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    return ""


def get_prop_multiselect(props, name):
    prop = props.get(name)
    if not prop or prop.get("type") != "multi_select":
        return []
    return [o.get("name", "") for o in prop.get("multi_select", [])]


def mark_pulled(token, page_id):
    body = {"properties": {"Status": {"status": {"name": "Pulled by VPS"}}}}
    status, payload = _request("PATCH", "/pages/%s" % page_id, token, body)
    return status == 200


def main():
    token = _token()
    if not token:
        print("ERROR: no Notion token found in env (NOTION_TOKEN)")
        sys.exit(1)
    database_id = find_database_id(token)
    rows = query_hero_approved(token, database_id)
    print("FOUND_HERO_APPROVED=%d" % len(rows))
    for row in rows:
        page_id = row["id"]
        props = row.get("properties", {})
        name = get_prop_text(props, "Name")
        reuse_key = get_prop_text(props, "Reuse Key")
        tags = get_prop_multiselect(props, "Tags")
        episode_id = get_prop_text(props, "Episode ID")
        prompt = get_prop_text(props, "Prompt")
        print("HERO_ROW page_id=%s name=%r episode_id=%r reuse_key=%r tags=%r prompt_len=%d" % (
            page_id, name, episode_id, reuse_key, tags, len(prompt)))
        # TODO: trigger resume of remaining scene generation for this episode,
        # using reuse_key/tags/prompt as text style-anchor (no img2img available).
        # Needs S5 resume-capability confirmed before wiring here.
        ok = mark_pulled(token, page_id)
        print("MARKED_PULLED page_id=%s ok=%s" % (page_id, ok))


if __name__ == "__main__":
    main()
