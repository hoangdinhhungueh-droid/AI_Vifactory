#!/usr/bin/env python3
"""Antigravity Notion Bridge (ag_notion_bridge.py)
A secure CLI & Python helper for Antigravity co-existence agent to read/write Notion SoT.
Strictly respects Rule 32 (never invent content), Rule 94 (secrets authoritative), Rule 44 (anti-overwrite).
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
from pathlib import Path

# Add scripts dir to path to import _token from compile_episode_from_notion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import compile_episode_from_notion as comp
    _get_token = comp._token
except Exception:
    def _get_token():
        return os.environ.get("NOTION_TOKEN", "")

NOTION_VERSION = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"
ID_CACHE = Path("/root/video_factory/data/notion_db_ids.json")

CANONICAL_DBS = {
    "prompt": ("PROMPT_LIBRARY_DB_ID", "Prompt Library"),
    "prompt_library": ("PROMPT_LIBRARY_DB_ID", "Prompt Library"),
    "story": ("STORY_LIBRARY_DB_ID", "Story Library"),
    "director": ("DIRECTOR_PLAN_DB_ID", "Director Plan"),
    "bible": ("VISUAL_BIBLE_DB_ID", "Episode Visual Bible"),
    "images": ("IMAGE_ASSET_DB_ID", "Image Asset Library"),
    "trend_brain": ("TREND_BRAIN_DB_ID", "VF Trend Brain"),
    "episodes": ("EPISODES_REGISTRY_DB_ID", "Episodes DB"),
    "experience_lab": ("EXPERIENCE_LAB_DB_ID", "Experience Lab"),
}

KNOWN_PAGES = {
    "master_plan": "17d01989-2400-8270-b0a9-81ad394b1b07",
    "pipeline_live": "8d501989-2400-83cf-8c04-0168106ca6b7",
    "db_registries": "73801989-2400-82a7-ae5f-0110bfb666c8",
    "test_ep006": "a5e9353b-7c24-4473-a14a-07ac1702b6e2",
    "decision_log": "1f001989-2400-82ea-81d9-0156fc0b9932",
    "skill_ai": "ac901989-2400-827e-bda2-8175dabdcf13"
}


def _headers():
    token = _get_token()
    if not token:
        raise ValueError("NOTION_TOKEN could not be resolved from secrets or environment.")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }


def _req(method, endpoint, data=None):
    url = f"{NOTION_API}/{endpoint.lstrip('/')}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status_code": e.code, "message": err_msg}
    except Exception as e:
        return {"error": True, "message": str(e)}


def resolve_id(name_or_id):
    cleaned = name_or_id.replace("-", "").lower()
    if len(cleaned) == 32:
        return name_or_id
    if name_or_id in KNOWN_PAGES:
        return KNOWN_PAGES[name_or_id]
    
    # Check cache
    if ID_CACHE.exists():
        try:
            cache = json.loads(ID_CACHE.read_text(encoding="utf-8"))
            if name_or_id in cache:
                return cache[name_or_id]
        except Exception:
            pass

    # Check canonical env
    if name_or_id in CANONICAL_DBS:
        env_var, title = CANONICAL_DBS[name_or_id]
        val = os.environ.get(env_var)
        if val:
            return val
    return name_or_id


def get_page(page_id):
    resolved = resolve_id(page_id)
    return _req("GET", f"pages/{resolved}")


def get_blocks(block_id, page_size=100):
    resolved = resolve_id(block_id)
    blocks = []
    cursor = None
    while True:
        endpoint = f"blocks/{resolved}/children?page_size={page_size}"
        if cursor:
            endpoint += f"&start_cursor={cursor}"
        res = _req("GET", endpoint)
        if res.get("error"):
            return res
        results = res.get("results", [])
        blocks.extend(results)
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return {"results": blocks, "total": len(blocks)}


def query_db(db_id, filter_obj=None, sorts=None, page_size=100):
    resolved = resolve_id(db_id)
    payload = {"page_size": page_size}
    if filter_obj:
        payload["filter"] = filter_obj
    if sorts:
        payload["sorts"] = sorts

    rows = []
    cursor = None
    while True:
        if cursor:
            payload["start_cursor"] = cursor
        res = _req("POST", f"databases/{resolved}/query", payload)
        if res.get("error"):
            return res
        results = res.get("results", [])
        rows.extend(results)
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return {"results": rows, "total": len(rows)}


def update_page_properties(page_id, properties):
    resolved = resolve_id(page_id)
    return _req("PATCH", f"pages/{resolved}", {"properties": properties})


def create_page(parent_db_id, properties, children=None):
    resolved = resolve_id(parent_db_id)
    payload = {
        "parent": {"database_id": resolved},
        "properties": properties
    }
    if children:
        payload["children"] = children
    return _req("POST", "pages", payload)


def append_children_blocks(block_id, children):
    resolved = resolve_id(block_id)
    return _req("PATCH", f"blocks/{resolved}/children", {"children": children})


def delete_block(block_id):
    resolved = resolve_id(block_id)
    return _req("DELETE", f"blocks/{resolved}")


def _strip_ids(obj):
    if isinstance(obj, dict):
        return {k: _strip_ids(v) for k, v in obj.items() if k != "id"}
    if isinstance(obj, list):
        return [_strip_ids(v) for v in obj]
    return obj


def resolve_episode_prompt_db(episode_id, task_id=None, create_if_missing=True):
    """Find (or create) the per-episode Prompt Library child database as a
    ROW inside the flat Prompt Library DB.

    Fixed 23/08/2026: the original version created a loose child_page
    directly under db_registries (sibling to the DB blocks) instead of
    nesting inside the Prompt Library database as a proper row. Existing
    EP001 data was migrated by /tmp/vf/fix_subpage_placement.py; this
    function now creates/finds rows the correct way going forward.
    Returns {"db_id", "subpage_id", "created"} on success, or an error dict.
    """
    flat_db_id = resolve_id("prompt_library")
    marker = f"({episode_id})"
    rows = query_db(flat_db_id)
    if rows.get("error"):
        return rows
    for row in rows.get("results", []):
        title_prop = row.get("properties", {}).get("Title", {})
        title = "".join(t.get("plain_text", "") for t in title_prop.get("title", []))
        if title.startswith("Prompt Library") and marker in title:
            sub_blocks = get_blocks(row["id"])
            if sub_blocks.get("error"):
                continue
            for sub in sub_blocks.get("results", []):
                if sub.get("type") == "child_database":
                    return {"db_id": sub["id"], "subpage_id": row["id"], "created": False}

    if not create_if_missing:
        return {"error": True, "message": f"No Prompt Library row found for {episode_id}"}

    schema_res = _req("GET", f"databases/{flat_db_id}")
    if schema_res.get("error"):
        return schema_res
    props_schema = schema_res.get("properties", {})

    new_db_properties = {"Title": {"title": {}}}
    for name, spec in props_schema.items():
        if name == "Title":
            continue
        t = spec["type"]
        if t == "created_time":
            continue
        new_db_properties[name] = {"type": t, t: _strip_ids(spec.get(t, {}))}

    tid = task_id or episode_id
    page_title = f"Prompt Library — {tid} ({episode_id})"
    page_res = _req("POST", "pages", {
        "parent": {"type": "database_id", "database_id": flat_db_id},
        "icon": {"type": "emoji", "emoji": "🧩"},
        "properties": {
            "Title": {"title": [{"type": "text", "text": {"content": page_title}}]},
            "category": {"select": {"name": "episode"}},
        },
        "children": [{
            "object": "block", "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "🧩"},
                "rich_text": [{"type": "text", "text": {"content": f"Task ID: {tid} | Episode ID: {episode_id}. Auto-created by resolve_episode_prompt_db() on first prompt push."}}]
            }
        }]
    })
    if page_res.get("error"):
        return page_res
    subpage_id = page_res["id"]

    db_res = _req("POST", "databases", {
        "parent": {"type": "page_id", "page_id": subpage_id},
        "title": [{"type": "text", "text": {"content": "Prompts"}}],
        "properties": new_db_properties,
    })
    if db_res.get("error"):
        return db_res
    return {"db_id": db_res["id"], "subpage_id": subpage_id, "created": True}


def resolve_episode_director_db(episode_id, task_id=None, create_if_missing=True):
    """Find (or create) the per-episode Director Plan child 'Scenes' database
    as a ROW inside the flat Director Plan DB. Mirrors
    resolve_episode_prompt_db(); added 23/08/2026 as part of the structural
    placement fix. Returns {"db_id", "subpage_id", "created"} on success, or
    an error dict.
    """
    flat_db_id = resolve_id("director")
    marker = f"({episode_id})"
    rows = query_db(flat_db_id)
    if rows.get("error"):
        return rows
    for row in rows.get("results", []):
        title_prop = row.get("properties", {}).get("Name", {})
        title = "".join(t.get("plain_text", "") for t in title_prop.get("title", []))
        if title.startswith("Director Plan") and marker in title:
            sub_blocks = get_blocks(row["id"])
            if sub_blocks.get("error"):
                continue
            for sub in sub_blocks.get("results", []):
                if sub.get("type") == "child_database":
                    return {"db_id": sub["id"], "subpage_id": row["id"], "created": False}

    if not create_if_missing:
        return {"error": True, "message": f"No Director Plan row found for {episode_id}"}

    schema_res = _req("GET", f"databases/{flat_db_id}")
    if schema_res.get("error"):
        return schema_res
    props_schema = schema_res.get("properties", {})

    new_db_properties = {"Name": {"title": {}}}
    for name, spec in props_schema.items():
        if name == "Name":
            continue
        t = spec["type"]
        if t == "created_time":
            continue
        new_db_properties[name] = {"type": t, t: _strip_ids(spec.get(t, {}))}

    tid = task_id or episode_id
    page_title = f"Director Plan — {tid} ({episode_id})"
    page_res = _req("POST", "pages", {
        "parent": {"type": "database_id", "database_id": flat_db_id},
        "icon": {"type": "emoji", "emoji": "🎬"},
        "properties": {
            "Name": {"title": [{"type": "text", "text": {"content": page_title}}]},
            "Episode ID": {"rich_text": [{"type": "text", "text": {"content": episode_id}}]},
            "Task ID": {"rich_text": [{"type": "text", "text": {"content": tid}}]},
        },
        "children": [{
            "object": "block", "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "🎬"},
                "rich_text": [{"type": "text", "text": {"content": f"Task ID: {tid} | Episode ID: {episode_id}. Auto-created by resolve_episode_director_db() on first scene push."}}]
            }
        }]
    })
    if page_res.get("error"):
        return page_res
    subpage_id = page_res["id"]

    db_res = _req("POST", "databases", {
        "parent": {"type": "page_id", "page_id": subpage_id},
        "title": [{"type": "text", "text": {"content": "Scenes"}}],
        "properties": new_db_properties,
    })
    if db_res.get("error"):
        return db_res
    return {"db_id": db_res["id"], "subpage_id": subpage_id, "created": True}



def resolve_episode_image_asset_db(episode_id, task_id=None, create_if_missing=True):
    flat_db_id = "f9101989-2400-830c-ab89-01700bb07933"
    marker = f"({episode_id})"
    rows = query_db(flat_db_id)
    if rows.get("error"):
        return rows
    for row in rows.get("results", []):
        title_prop = row.get("properties", {}).get("Name", {})
        title = "".join(t.get("plain_text", "") for t in title_prop.get("title", []))
        if title.startswith("Image Asset") and marker in title:
            sub_blocks = get_blocks(row["id"])
            if sub_blocks.get("error"):
                continue
            for sub in sub_blocks.get("results", []):
                if sub.get("type") == "child_database":
                    return {"db_id": sub["id"], "subpage_id": row["id"], "created": False}

    if not create_if_missing:
        return {"error": True, "message": f"No Image Asset Library row found for {episode_id}"}

    schema_res = _req("GET", f"databases/{flat_db_id}")
    if schema_res.get("error"):
        return schema_res
    props_schema = schema_res.get("properties", {})

    new_db_properties = {"Name": {"title": {}}}
    for name, spec in props_schema.items():
        if name == "Name":
            continue
        t = spec["type"]
        if t in ["created_time", "last_edited_time"]:
            continue
        new_db_properties[name] = {"type": t, t: _strip_ids(spec.get(t, {}))}

    tid = task_id or episode_id
    page_title = f"Image Asset Library — {tid} ({episode_id})"
    
    page_props = {
        "Name": {"title": [{"type": "text", "text": {"content": page_title}}]}
    }
    
    page_res = _req("POST", "pages", {
        "parent": {"type": "database_id", "database_id": flat_db_id},
        "icon": {"type": "emoji", "emoji": "🖼️"},
        "properties": page_props,
        "children": [{
            "object": "block", "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "🖼️"},
                "rich_text": [{"type": "text", "text": {"content": f"Task ID: {tid} | Episode ID: {episode_id}. Auto-created by resolve_episode_image_asset_db()."}}]
            }
        }]
    })
    if page_res.get("error"):
        return page_res
    subpage_id = page_res["id"]

    db_res = _req("POST", "databases", {
        "parent": {"type": "page_id", "page_id": subpage_id},
        "title": [{"type": "text", "text": {"content": "Assets"}}],
        "properties": new_db_properties,
    })
    if db_res.get("error"):
        return db_res
    return {"db_id": db_res["id"], "subpage_id": subpage_id, "created": True}


def read_skill_rule(rule_query):
    audit_file = Path("/root/video_factory/data/notion_audit/skill_ai.md")
    if not audit_file.exists():
        return {"error": True, "message": "skill_ai.md audit file not found. Run audit dump first."}
    
    content = audit_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    matching_blocks = []
    current_rule = []
    recording = False
    
    q = rule_query.lower()
    for line in lines:
        if line.strip().startswith("### Rule ") or line.strip().startswith("Rule ") or line.strip().startswith("## "):
            if recording and current_rule:
                matching_blocks.append("\n".join(current_rule))
                current_rule = []
                recording = False
            if q in line.lower():
                recording = True
                current_rule.append(line)
        elif recording:
            current_rule.append(line)
            
    if recording and current_rule:
        matching_blocks.append("\n".join(current_rule))
        
    return {"query": rule_query, "matches_count": len(matching_blocks), "results": matching_blocks}


def main():
    parser = argparse.ArgumentParser(description="Antigravity Notion Bridge CLI")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # selftest
    subparsers.add_parser("selftest")

    # get-page
    p_get = subparsers.add_parser("get-page")
    p_get.add_argument("page_id", help="Page ID or canonical name")

    # get-blocks
    p_blk = subparsers.add_parser("get-blocks")
    p_blk.add_argument("block_id", help="Block/Page ID")

    # query-db
    p_qdb = subparsers.add_parser("query-db")
    p_qdb.add_argument("db_id", help="Database ID or canonical key (story, director, etc.)")
    p_qdb.add_argument("--filter-json", help="JSON string for Notion query filter", default=None)
    p_qdb.add_argument("--sort-json", help="JSON string for Notion query sorts", default=None)

    # update-page
    p_upd = subparsers.add_parser("update-page")
    p_upd.add_argument("page_id", help="Page ID")
    p_upd.add_argument("--properties-json", required=True, help="JSON string for properties")

    # create-row
    p_crow = subparsers.add_parser("create-row")
    p_crow.add_argument("db_id", help="Database ID or canonical key")
    p_crow.add_argument("--properties-json", required=True, help="JSON string for properties")
    p_crow.add_argument("--children-json", help="JSON string for page body blocks", default=None)

    # append-blocks
    p_app = subparsers.add_parser("append-blocks")
    p_app.add_argument("block_id", help="Block or Page ID")
    p_app.add_argument("--children-json", required=True, help="JSON string of block children array")

    # get-rule
    p_rule = subparsers.add_parser("get-rule")
    p_rule.add_argument("rule_query", help="Rule number or query string (e.g. 'Rule 90', 'Rule 106', 'anti-ai')")

    args = parser.parse_args()

    if args.action == "selftest":
        print("[Bridge] Running Notion Bridge Selftest...")
        tok = _get_token()
        print(f"[Bridge] Token loaded: {'YES' if tok else 'NO'}")
        p = get_page("master_plan")
        if p.get("error"):
            print(f"[Bridge] Error loading master_plan: {p}")
            sys.exit(1)
        print(f"[Bridge] Master Plan access OK: {p.get('id')}")
        print("[Bridge] Selftest PASS ✅")
        return

    if args.action == "get-page":
        res = get_page(args.page_id)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.action == "get-blocks":
        res = get_blocks(args.block_id)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.action == "query-db":
        filt = json.loads(args.filter_json) if args.filter_json else None
        sorts = json.loads(args.sort_json) if args.sort_json else None
        res = query_db(args.db_id, filter_obj=filt, sorts=sorts)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.action == "update-page":
        props = json.loads(args.properties_json)
        res = update_page_properties(args.page_id, props)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.action == "create-row":
        props = json.loads(args.properties_json)
        children = json.loads(args.children_json) if args.children_json else None
        res = create_page(args.db_id, props, children)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.action == "append-blocks":
        children = json.loads(args.children_json)
        res = append_children_blocks(args.block_id, children)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.action == "get-rule":
        res = read_skill_rule(args.rule_query)
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
