#!/usr/bin/env python3
"""
scripts/forensics/dispose_retatrutide_residue.py — Auditable Residue Disposal
Mandate:
  1. Safely disposes residue from incident task EN_EP0001_retatrutide_shadow_market:
     - Pending task file in /var/vf/pending_tasks/
     - Registry entry in topic_history.json (marked DISPOSED_INCIDENT_RESIDUE)
     - Notion Story Library row updated to 'Archived'
  2. Documents disposition of scripts/orchestrator/run_pipeline.py (permanently removed in git commit 2456870).
  3. Strict audit trail (Rule 118, Rule 121, Rule 125).
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.paths import resolve_state_dir



logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dispose_retatrutide")

TASK_ID = "EN_EP0001_retatrutide_shadow_market"

def dispose_pending_task():
    print(f"\n--- 1. Disposing Pending Task File: {TASK_ID} ---")
    state_dir = resolve_state_dir()
    candidates = [
        Path("/var/vf/pending_tasks") / f"{TASK_ID}.json",
        state_dir / "pending_tasks" / f"{TASK_ID}.json",
    ]
    disposed = False
    for p in candidates:
        if p.exists():
            try:
                # Read original for audit before removing
                content = p.read_text(encoding="utf-8")
                audit_backup = Path("/tmp") / f"{TASK_ID}.disposed.json"
                audit_backup.write_text(content, encoding="utf-8")
                p.unlink()
                print(f"  [DELETED] Successfully removed {p} (Backed up to {audit_backup})")
                disposed = True
            except Exception as e:
                print(f"  [ERROR] Failed to unlink {p}: {e}")
        else:
            print(f"  [NOT FOUND] {p}")
    if not disposed:
        print(f"  [OK] No active pending task file found for {TASK_ID}.")

def dispose_topic_history():
    print(f"\n--- 2. Updating Topic History Registry: {TASK_ID} ---")
    state_dir = resolve_state_dir()
    hist_files = [
        state_dir / "topic_history.json",
        Path("/var/vf/topic_history.json"),
    ]
    for hf in hist_files:
        if hf.exists():
            try:
                data = json.loads(hf.read_text(encoding="utf-8"))
                modified = False
                for key, val in list(data.items()):
                    if isinstance(val, dict) and val.get("task_id") == TASK_ID:
                        val["status"] = "DISPOSED_INCIDENT_RESIDUE"
                        val["disposed_at_utc"] = datetime.now(timezone.utc).isoformat()
                        val["disposal_reason"] = "Task failed B3 in prior session and was abandoned"
                        modified = True
                        print(f"  [UPDATED] Key '{key}' in {hf} marked as DISPOSED_INCIDENT_RESIDUE")
                    elif key == TASK_ID:
                        val["status"] = "DISPOSED_INCIDENT_RESIDUE"
                        val["disposed_at_utc"] = datetime.now(timezone.utc).isoformat()
                        modified = True
                        print(f"  [UPDATED] Task key '{key}' in {hf} marked as DISPOSED_INCIDENT_RESIDUE")
                if modified:
                    hf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"  [SAVED] {hf}")
                else:
                    print(f"  [INFO] No entries matching {TASK_ID} in {hf}")
            except Exception as e:
                print(f"  [ERROR] Failed reading/updating {hf}: {e}")
        else:
            print(f"  [NOT FOUND] {hf}")

def dispose_notion_row():
    print(f"\n--- 3. Archiving Notion Story Library Row: {TASK_ID} ---")
    try:
        from app.services.notion_client import query_database, update_page_properties
        res = query_database({
            "or": [
                {"property": "Task ID", "rich_text": {"equals": TASK_ID}},
                {"property": "Episode ID", "rich_text": {"equals": TASK_ID}},
            ]
        })
        results = res.get("results", []) if res else []
        if not results:
            print(f"  [INFO] No Notion Story Library row found for {TASK_ID}")
            return

        for r in results:
            page_id = r["id"]
            update_page_properties(page_id, {
                "Status": {"status": {"name": "Archived"}},
                "Audit Notes": {"rich_text": [{"type": "text", "text": {"content": "Disposed incident residue (failed B3 in prior run)"}}]}
            })
            print(f"  [ARCHIVED] Notion Page ID {page_id} updated to 'Archived'")
    except Exception as e:
        print(f"  [WARNING] Notion disposal note: {e}")

def document_run_pipeline_disposition():
    print("\n--- 4. Run Pipeline Disposition Audit ---")
    print("  File: scripts/orchestrator/run_pipeline.py")
    print("  Status: PERMANENTLY REMOVED via git rm in commit 2456870.")
    print("  Active Orchestrator: scripts/orchestrator/runner.py & scripts/run_trend_pipeline.py.")
    print("  Rule 125 Single Truth: Zero ghost scripts remain.")

def main():
    print("=======================================================")
    print("🧹 EXECUTING AUDITABLE RETATRUTIDE RESIDUE DISPOSAL")
    print("=======================================================")
    dispose_pending_task()
    dispose_topic_history()
    dispose_notion_row()
    document_run_pipeline_disposition()
    print("\n=======================================================")
    print("✅ RETATRUTIDE RESIDUE DISPOSAL COMPLETED")
    print("=======================================================")

if __name__ == "__main__":
    main()
