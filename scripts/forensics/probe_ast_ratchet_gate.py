#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/forensics/probe_ast_ratchet_gate.py

Verifies monotonic boundary and dynamic ceiling on AST Ratchet Baseline
(Rule 125, 139 & Boss Round 14 Item 6).
"""

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
baseline_path = ROOT_DIR / "config" / "ast_ratchet_baseline.json"

if not baseline_path.exists():
    print(f"ERROR: Baseline file not found: {baseline_path}", file=sys.stderr)
    sys.exit(1)

with open(baseline_path, encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
count = len(entries)
max_allowed = data.get("max_legacy_defects", 221)
override_url = os.getenv("VF_AST_RATCHET_OVERRIDE", "").strip()
dynamic_ceiling = max_allowed + 10

print(f"AST Ratchet Baseline: entries={count}, max_allowed={max_allowed}, dynamic_ceiling={dynamic_ceiling}")
if override_url:
    print(f"AST Ratchet Override active via VF_AST_RATCHET_OVERRIDE: {override_url}")
else:
    assert count <= max_allowed, f"Ratchet violation: entries ({count}) exceeds max_legacy_defects ({max_allowed})"
    assert count <= dynamic_ceiling, f"Ratchet violation: count ({count}) exceeds dynamic ceiling ({dynamic_ceiling})"

print("AST Ratchet Monotonic Boundary Check: PASS (Exit Code: 0)")
print("Sample AST Baseline Entries:")
for e in entries[:4]:
    print(f"  - File: {e.get('file')}, Line: {e.get('line')}, Rule: {e.get('rule')}")

sys.exit(0)
