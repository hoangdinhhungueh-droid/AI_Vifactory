# -*- coding: utf-8 -*-
"""
Notion DB schema extension helper. Added 23/08/2026 to support syncing the
new auto-generated SEO packaging fields (Rule 119) into the Story Library DB
without hand-editing ag_notion_bridge.py. Additive module only -- reuses
ag_notion_bridge's existing _req/resolve_id, never duplicates its logic, and
never removes/overwrites existing properties (Rule 44 anti-overwrite).
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ag_notion_bridge as bridge

# New properties this module knows how to add to a Notion database schema,
# keyed by the exact property name expected downstream by
# app/services/seo_autogen_b10.py + execute_b10_auto_seo_upload_gate2.py.
SEO_PACKAGING_PROPERTIES = {
    "SEO Title A": {"rich_text": {}},
    "SEO Title B": {"rich_text": {}},
    "SEO Description": {"rich_text": {}},
    "SEO Tags": {"rich_text": {}},
    "SEO Hashtags": {"rich_text": {}},
    "Rising Queries": {"rich_text": {}},
    "Thumbnail Variants (A/B/C)": {"rich_text": {}},
    "Hook Frame Note": {"rich_text": {}},
    "End Screen Notes": {"rich_text": {}},
    "SEO Generation Method": {"rich_text": {}},
}


def ensure_db_properties(db_key_or_id: str, new_properties: dict) -> dict:
    """Idempotently PATCH a database schema to add any properties in
    `new_properties` that are not already present. Returns a summary dict;
    never removes or overwrites existing properties (Rule 44 anti-overwrite).
    """
    db_id = bridge.resolve_id(db_key_or_id)
    schema = bridge._req("GET", f"databases/{db_id}")
    if schema.get("error"):
        return schema
    existing = schema.get("properties", {})
    missing = {name: spec for name, spec in new_properties.items() if name not in existing}
    if not missing:
        return {"db_id": db_id, "added": [], "message": "all properties already present"}
    patch_res = bridge._req("PATCH", f"databases/{db_id}", {"properties": missing})
    if patch_res.get("error"):
        return patch_res
    return {"db_id": db_id, "added": list(missing.keys())}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ensure Notion DB has SEO packaging properties")
    parser.add_argument("db_key", help="Database ID or canonical key (e.g. story)")
    parser.add_argument("--properties-json", default=None, help="Optional custom properties JSON; defaults to SEO_PACKAGING_PROPERTIES")
    args = parser.parse_args()
    props = json.loads(args.properties_json) if args.properties_json else SEO_PACKAGING_PROPERTIES
    res = ensure_db_properties(args.db_key, props)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


# --- YouTube Channel & Video Metadata Registry additive extension ---------
# Added 23/08/2026 per user decision: this is the REAL, already-in-active-use
# canonical DB (confirmed via backfill_task_id.py + daily_knowledge_dreaming_sync.py,
# and referenced as DB7 in the Architecture Page pipeline diagram) for SEO
# packaging output, NOT the Story Library. Existing columns already cover
# Title A / Title B (Backup A/B) / Tags & Keywords / SEO Description /
# Pinned Comment / AI Generated Disclosure / Thumbnail URL / Publish Status.
# Only 3 Rule 119 elements were missing a dedicated column; added additively
# below (Rule 44 anti-overwrite -- never touches existing properties/rows).
YOUTUBE_REGISTRY_DB_ID = "3c301989-2400-81b9-a4bb-e5568ce942f8"

REGISTRY_SEO_PROPERTIES = {
    "Hashtags": {"rich_text": {}},
    "Hook Frame (0-3s)": {"rich_text": {}},
    "End Screen (3 diem)": {"rich_text": {}},
    "SEO Generation Method": {"rich_text": {}},
    "Task ID": {"rich_text": {}},
}
