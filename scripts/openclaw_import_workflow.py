#!/usr/bin/env python3
"""
Import n8n workflow JSON via n8n REST API.
Usage: python openclaw_import_workflow.py --name <workflow_name> --json @<file>.json
"""

import os, json, argparse, requests, sys

N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")

def import_workflow(name: str, workflow_json: dict):
    headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
    workflow_json["name"] = name
    resp = requests.get(f"{N8N_BASE_URL}/api/v1/workflows", headers=headers, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"Failed to list workflows: {resp.text}")
    existing = {w["name"]: w["id"] for w in resp.json().get("data", [])}
    if name in existing:
        wf_id = existing[name]
        resp = requests.put(f"{N8N_BASE_URL}/api/v1/workflows/{wf_id}",
                            headers=headers, json=workflow_json, timeout=30)
    else:
        resp = requests.post(f"{N8N_BASE_URL}/api/v1/workflows",
                             headers=headers, json=workflow_json, timeout=30)
    resp.raise_for_status()
    print(f"✅ Imported: {name} → ID {resp.json()['id']}")
    return resp.json()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Workflow name")
    ap.add_argument(
        "--json",
        required=True,
        help="@file.json (or raw JSON string directly)",
    )
    args = ap.parse_args()
    raw = args.json
    if raw.startswith("@"):
        with open(raw[1:], "r", encoding="utf-8") as f:
            wf = json.load(f)
    else:
        wf = json.loads(raw)
    try:
        import_workflow(args.name, wf)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)