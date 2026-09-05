#!/usr/bin/env python3
"""Auto B5 Vision Audit with Auto-Approval (31/08/2026).

Automatically audits pending images in Image Asset Library and auto-approves
those with final_score >= 8.0 by setting Status="Approved".

Flow:
  1. Query Notion for images with empty Audit Final Score
  2. Run vision audit via existing image_audit service
  3. If final_score >= 8.0 → Status="Approved" (auto-approve)
  4. If final_score < 8.0 → Status="Review Required" (human gate)
  5. Update all audit fields (D1/D2/D3, confidence, issues, notes)
  6. Log results to /var/log/auto_b5_audit.log

Scheduled via cron: */15 * * * * (every 15 minutes)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load secrets
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(os.path.join("/root", "secrets", ".env"))
except Exception:
    pass

# Import existing audit infrastructure
from app.services.image_audit import (
    fetch_pending_rows,
    audit_image_hhtech,
    compute_verdict,
    run_gating_checks,
    _image_bytes,
    _row_field,
    _save_pg,
    _notion_call,
    _map_issues,
    HHTECH_MODEL,
    AUDIT_METHOD_NAME,
)

# Auto-approval threshold
AUTO_APPROVE_THRESHOLD = 8.0

# Setup logging
LOG_FILE = "/var/log/auto_b5_audit.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def write_audit_with_status(
    page_id: str,
    verdict: str,
    final: float,
    d1: float,
    d2: float,
    d3: float,
    conf: float,
    method: str,
    issues: list[str],
    notes: str,
    auto_approve: bool = False
) -> None:
    """Write audit results to Notion with Status field update.
    
    Args:
        page_id: Notion page ID
        verdict: APPROVED/REVIEW/REJECTED
        final: Final weighted score
        d1-d3: Dimension scores
        conf: Confidence score
        method: Audit method name
        issues: List of issue strings
        notes: Audit notes
        auto_approve: If True and final >= threshold, set Status="Approved"
    """
    props = {
        "Audit D1 Score": {"number": d1},
        "Audit D2 Score": {"number": d2},
        "Audit D3 Score": {"number": d3},
        "Audit Final Score": {"number": round(final, 2)},
        "Audit Confidence": {"number": round(conf, 2)},
        "Audit Method": {"select": {"name": method}},
        "Audit Date": {"date": {"start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}},
        "Prompt Issues": {"multi_select": _map_issues(issues)},
        "Enhancement Notes": {
            "rich_text": [{"text": {"content": (f"[{verdict}] " + notes)[:1900]}}]
        },
    }
    
    # Add Status field for auto-approval logic
    if auto_approve:
        if final >= AUTO_APPROVE_THRESHOLD:
            props["Status"] = {"select": {"name": "Approved"}}
            logger.info(f"Auto-approving {page_id[:8]}... with score {final:.2f}")
        else:
            props["Status"] = {"select": {"name": "Review Required"}}
            logger.info(f"Marking {page_id[:8]}... for review with score {final:.2f}")
    
    _notion_call("PATCH", f"/pages/{page_id}", {"properties": props})


def run_auto_audit(limit: int = 50) -> dict:
    """Run automatic audit with auto-approval logic.
    
    Args:
        limit: Max number of images to process per run
        
    Returns:
        Stats dict with counts and results
    """
    logger.info(f"Starting auto B5 audit (limit={limit})")
    
    try:
        rows = fetch_pending_rows(limit=limit)
    except Exception as e:
        logger.error(f"Failed to fetch pending rows: {e}")
        return {"error": str(e), "total": 0}
    
    stats = {
        "total": len(rows),
        "approved": 0,
        "review": 0,
        "rejected": 0,
        "gated": 0,
        "errors": 0,
        "model": HHTECH_MODEL,
        "tokens": {"prompt": 0, "completion": 0},
        "results": []
    }
    
    logger.info(f"Found {len(rows)} pending images")
    
    for idx, row in enumerate(rows, 1):
        pid = row["id"]
        name = _row_field(row, "Name") or pid
        episode = _row_field(row, "Episode ID") or "unknown"
        reuse_key = _row_field(row, "Reuse Key") or None
        prompt = _row_field(row, "Prompt")
        
        logger.info(f"[{idx}/{len(rows)}] Processing {name[:50]}... (ID: {pid[:8]}...)")
        
        try:
            # Load image bytes
            image_bytes, _src = _image_bytes(row)
            
            # 1) Rule-based gating (no vision API call on hard failure)
            gating = run_gating_checks(image_bytes, reuse_key)
            if not gating["passed"]:
                logger.warning(f"Gating failed for {name[:50]}: {gating['issues']}")
                stats["rejected"] += 1
                stats["gated"] += 1
                stats["results"].append({
                    "page": pid,
                    "name": name,
                    "verdict": "REJECTED",
                    "reason": "gating",
                    "issues": gating["issues"]
                })
                
                write_audit_with_status(
                    pid, "REJECTED", 0.0, 0.0, 0.0, 0.0, 1.0,
                    "Auto gating (rule)", gating["issues"],
                    "auto-rejected by rule-based gating",
                    auto_approve=True  # Will set Status="Review Required"
                )
                _save_pg(episode, 0.0, "REJECTED", {"gating": 0.0}, gating["issues"], "rule_gating")
                continue
            
            # 2) Vision audit via hhtech (Claude Haiku)
            layer = _row_field(row, "Layer Type")
            r = audit_image_hhtech(image_bytes, prompt, layer=layer)
            stats["tokens"]["prompt"] += r.pop("_tok_in", 0)
            stats["tokens"]["completion"] += r.pop("_tok_out", 0)
            
            verdict, final = compute_verdict(r["d1"], r["d2"], r["d3"], r["confidence"])
            
            # Count by verdict
            stats[{"APPROVED": "approved", "REVIEW": "review", "REJECTED": "rejected"}[verdict]] += 1
            
            stats["results"].append({
                "page": pid,
                "name": name,
                "episode": episode,
                "verdict": verdict,
                "final": round(final, 2),
                "auto_approved": final >= AUTO_APPROVE_THRESHOLD
            })
            
            # Write audit with Status update
            write_audit_with_status(
                pid, verdict, final, r["d1"], r["d2"], r["d3"],
                r["confidence"], AUDIT_METHOD_NAME,
                r["issues"], r["notes"],
                auto_approve=True
            )
            
            _save_pg(episode, final, verdict,
                     {"d1": r["d1"], "d2": r["d2"], "d3": r["d3"], "confidence": r["confidence"]},
                     r["issues"], HHTECH_MODEL)
            
            logger.info(f"✓ {name[:40]}: {verdict} (score={final:.2f})")
            
        except Exception as e:
            logger.error(f"Error processing {name[:50]}: {e}", exc_info=True)
            stats["errors"] += 1
            stats["results"].append({
                "page": pid,
                "name": name,
                "verdict": "ERROR",
                "error": str(e)[:300]
            })
    
    # Summary
    tok_in = stats["tokens"]["prompt"]
    tok_out = stats["tokens"]["completion"]
    logger.info(f"=== Auto B5 Audit Complete ===")
    logger.info(f"Total: {stats['total']} | APPROVED: {stats['approved']} | REVIEW: {stats['review']} | REJECTED: {stats['rejected']} (gated: {stats['gated']}) | ERRORS: {stats['errors']}")
    logger.info(f"Model: {HHTECH_MODEL} | Tokens: {tok_in:,} in + {tok_out:,} out = {tok_in + tok_out:,}")
    
    return stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto B5 Vision Audit with Auto-Approval")
    parser.add_argument("--limit", type=int, default=50, help="Max images to process per run")
    args = parser.parse_args()
    
    try:
        stats = run_auto_audit(limit=args.limit)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        sys.exit(0 if stats.get("errors", 0) == 0 else 1)
    except Exception as e:
        logger.error(f"Fatal error in auto_b5_audit: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
