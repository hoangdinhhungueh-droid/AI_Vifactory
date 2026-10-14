#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/codemap/__main__.py — Unified CLI for Codemap GPS Brain & Lineage Tracker.

Subcommands:
  - build:   Compiles full AST symbols, stages, models, handoffs into .codemap/codemap.json
  - check:   Validates freshness and asserts 0 handoff contract MISMATCHES (exit 1 if failed)
  - where:   Instant GPS code lookup: resolves symbol name to exact file, line range, callers, callees, stage
  - trace:   Prints chronological execution event stream for a run_id
  - lineage: Audits approval vs consumed data, exits 2 on DRIFT, exits 0 on INTACT
  - ui:      Generates interactive self-contained HTML pipeline flow map
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.codemap.builder import build_codemap, check_codemap
from tools.codemap.lineage import compute_lineage_report
from tools.codemap.schema import CodemapRegistry
from tools.codemap.ui.render import generate_pipeline_html


def cmd_build(args):
    repo_root = Path(args.repo_root).resolve()
    reg = build_codemap(repo_root)
    sys.exit(0 if reg.summary.get("mismatches", 0) == 0 else 1)


def cmd_check(args):
    repo_root = Path(args.repo_root).resolve()
    code, msg = check_codemap(repo_root)
    print(msg)
    sys.exit(code)


def cmd_where(args):
    repo_root = Path(args.repo_root).resolve()
    target_json = repo_root / ".codemap" / "codemap.json"
    if not target_json.exists():
        print(f"Error: Codemap not found at {target_json}. Run 'build' first.")
        sys.exit(1)

    query = args.symbol.strip()
    raw = json.loads(target_json.read_text(encoding="utf-8"))
    symbols = raw.get("symbols", {})
    stages = raw.get("stages", [])

    # Exact or suffix match
    matches = []
    for qual, sym in symbols.items():
        if qual == query or qual.endswith(f".{query}") or query in qual:
            matches.append(sym)

    # Check stage IDs
    for stg in stages:
        if stg["id"] == query or query in stg["name"].lower():
            print(f"\n[STAGE NODE] {stg['name']} (id: {stg['id']}, order: {stg['order']})")
            print(f"  Source:   {stg['ref']['file']}:{stg['ref']['line_start']}-{stg['ref']['line_end']}")
            print(f"  Input:    {stg.get('input_model') or 'None'}")
            print(f"  Output:   {stg.get('output_model') or 'None'}")
            print(f"  Upstream: {', '.join(stg.get('upstream', [])) or 'None'}")
            print(f"  Downstream: {', '.join(stg.get('downstream', [])) or 'None'}")
            print(f"  Verify:   {', '.join(stg.get('verify_cmds', [])) or 'None'}")

    if not matches and not any(s["id"] == query for s in stages):
        print(f"No symbols found matching: '{query}'")
        sys.exit(1)

    for m in matches[:10]:
        print(f"\n[SYMBOL] {m['qualname']} ({m['kind']})")
        print(f"  File:     {m['ref']['file']}:{m['ref']['line_start']}-{m['ref']['line_end']}")
        if m.get("stage_id"):
            print(f"  Stage:    {m['stage_id']}")
        if m.get("calls"):
            print(f"  Calls ({len(m['calls'])}):    {', '.join(m['calls'][:5])}")
        if m.get("called_by"):
            print(f"  Called by ({len(m['called_by'])}): {', '.join(m['called_by'][:5])}")
    sys.exit(0)


def cmd_trace(args):
    repo_root = Path(args.repo_root).resolve()
    run_dir = repo_root / ".codemap" / "runs" / args.run_id
    events_file = run_dir / "events.jsonl"

    if not events_file.exists():
        print(f"No trace events found for run_id: {args.run_id}")
        sys.exit(1)

    print(f"=== Execution Trace for {args.run_id} ===")
    for line in events_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            status_icon = "PASS" if d["status"] == "OK" else "FAIL"
            print(f"[{d['seq']:02d}] {status_icon} Stage: {d['stage_id']:<20} | InHash: {d.get('input_hash', '')[:10]}... | OutHash: {d.get('output_hash', '')[:10]}...")
            if d.get("error"):
                print(f"     ERROR: {d['error']['type']} - {d['error']['message']}")
    sys.exit(0)


def cmd_lineage(args):
    repo_root = Path(args.repo_root).resolve()
    reports = compute_lineage_report(args.run_id, repo_root=repo_root)

    if not reports:
        print(f"No approval lineage recorded for run_id: {args.run_id}")
        sys.exit(0)

    has_drift = False
    for rep in reports:
        print(f"\nLineage Audit: Approval {rep.approval_id} -> Target Stage {rep.target_stage}")
        print(f"Verdict: {rep.overall}")
        for f in rep.fields:
            print(f"  - {f.path:<25} [{f.verdict}] {f.note or ''}")
        if rep.overall in ("DRIFT", "NOT_CONSUMED"):
            has_drift = True

    if has_drift:
        print("\nDRIFT DETECTED: Data altered, dropped, defaulted, or bypassed!")
        sys.exit(2)
    else:
        print("\nALL INTACT: Approved data bit-for-bit carried into execution.")
        sys.exit(0)


def cmd_ui(args):
    repo_root = Path(args.repo_root).resolve()
    out = generate_pipeline_html(
        run_id=args.run,
        output_html=Path(args.output) if args.output else None,
        repo_root=repo_root
    )
    print(f"Visual Map openable at: {out.as_uri()}")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="AI Video Factory — Codemap GPS Brain & Traceability CLI")
    parser.add_argument("--repo-root", default=".", help="Root directory of repository")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Compile AST and build codemap.json")
    p_build.set_defaults(func=cmd_build)

    # check
    p_check = subparsers.add_parser("check", help="Check codemap freshness and handoff mismatches")
    p_check.set_defaults(func=cmd_check)

    # where
    p_where = subparsers.add_parser("where", help="GPS code lookup for symbols or stages")
    p_where.add_argument("symbol", help="Function, class, or stage identifier to locate")
    p_where.set_defaults(func=cmd_where)

    # trace
    p_trace = subparsers.add_parser("trace", help="View chronological execution trace")
    p_trace.add_argument("run_id", help="Target run ID")
    p_trace.set_defaults(func=cmd_trace)

    # lineage
    p_lineage = subparsers.add_parser("lineage", help="Verify approval vs consumed data")
    p_lineage.add_argument("run_id", help="Target run ID")
    p_lineage.set_defaults(func=cmd_lineage)

    # ui
    p_ui = subparsers.add_parser("ui", help="Generate self-contained interactive HTML map")
    p_ui.add_argument("--run", default=None, help="Optional run_id to inspect")
    p_ui.add_argument("--output", default=None, help="Target HTML file path")
    p_ui.set_defaults(func=cmd_ui)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
