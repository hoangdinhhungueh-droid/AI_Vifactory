#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/orchestrator/layer_boundary_checker.py — Antigravity Architectural Layer Boundary & Cycle Linter.

Inspired by CodeFlow's layer-violation-direction tests and anti-pattern detectors.
Enforces strict 4-Layer architectural hierarchy in Antigravity pipelines:

  Layer 1 (Contracts & Models):
    - Path: app/models/*, db/*, schemas, PIPELINE_CONTRACTS.md
    - Invariant: Zero dependencies on upper layers.

  Layer 2 (Core Engine & Primitives):
    - Path: scripts/orchestrator/*, app/utils/*, lifecycle/resource managers
    - Invariant: Can only import Layer 1. CẤM import Layer 3 (Domain Services) or Layer 4 (Renderers).

  Layer 3 (Domain Pipeline Services):
    - Path: app/services/* (B1..B11 business logic)
    - Invariant: Can import Layer 1 & 2. CẤM import Layer 4 (Presentation/Renderers).

  Layer 4 (Application & Presentation):
    - Path: app/main.py, remotion/*, workflows/*
    - Invariant: Consumer layer. Can import Layer 1, 2, 3.

Also detects:
  - Circular Dependencies (Tarjan/DFS cycle detection)
  - Orphan / Dead Modules (files with 0 callers not marked as entrypoints)

Exit Codes:
  0: CLEAN — Zero layer inversions, zero circular dependencies.
  1: DEFECTS DETECTED — Violations found; prints actionable forensic verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if __package__ is None or __package__ == "":
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from scripts.orchestrator.blast_radius_scanner import CodebaseGraph, normalize_rel_path
else:
    from .blast_radius_scanner import CodebaseGraph, normalize_rel_path


# Define Layer Rules
LAYER_DEFINITIONS = [
    {
        "level": 1,
        "name": "L1_CONTRACTS_MODELS",
        "prefixes": ["app/models", "db", "PIPELINE_CONTRACTS.md"],
        "max_import_level": 1,
    },
    {
        "level": 2,
        "name": "L2_CORE_INFRA",
        "prefixes": ["scripts/orchestrator", "app/utils", "scripts/vps_runner.py"],
        "max_import_level": 2,
    },
    {
        "level": 3,
        "name": "L3_DOMAIN_SERVICES",
        "prefixes": ["app/services"],
        "max_import_level": 3,
    },
    {
        "level": 4,
        "name": "L4_APP_PRESENTATION",
        "prefixes": ["app/main.py", "remotion", "workflows"],
        "max_import_level": 4,
    },
]


def get_file_layer(rel_path: str) -> Optional[Dict[str, Any]]:
    """Determine the architectural layer of a file based on its path prefix."""
    norm = normalize_rel_path(rel_path)
    for layer in LAYER_DEFINITIONS:
        for prefix in layer["prefixes"]:
            if norm == prefix or norm.startswith(prefix + "/"):
                return layer
    return None


class LayerBoundaryChecker:
    """Forensic linter for architectural layer boundaries and circular dependencies."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.graph = CodebaseGraph(self.root_dir)
        self.layer_violations: List[Dict[str, Any]] = []
        self.circular_dependencies: List[List[str]] = []
        self.orphan_modules: List[str] = []

    def run_audit(self) -> Dict[str, Any]:
        """Execute full forensic audit across all files."""
        self.graph.scan()
        self._check_layer_violations()
        self._check_circular_dependencies()
        self._check_orphan_modules()

        is_clean = len(self.layer_violations) == 0 and len(self.circular_dependencies) == 0

        return {
            "is_clean": is_clean,
            "layer_violations_count": len(self.layer_violations),
            "circular_dependencies_count": len(self.circular_dependencies),
            "orphan_modules_count": len(self.orphan_modules),
            "layer_violations": self.layer_violations,
            "circular_dependencies": self.circular_dependencies,
            "orphan_modules": self.orphan_modules,
            "total_files_analyzed": len(self.graph.file_metadata),
        }

    def _check_layer_violations(self) -> None:
        """Check for downward or horizontal violations where lower layers import higher layers."""
        for source_file, imported_files in self.graph.forward_graph.items():
            source_layer = get_file_layer(source_file)
            if not source_layer:
                continue

            for target_file in imported_files:
                target_layer = get_file_layer(target_file)
                if not target_layer:
                    continue

                if target_layer["level"] > source_layer["max_import_level"]:
                    self.layer_violations.append({
                        "source": source_file,
                        "source_layer": source_layer["name"],
                        "target": target_file,
                        "target_layer": target_layer["name"],
                        "severity": "CRITICAL" if target_layer["level"] - source_layer["level"] >= 2 else "WARNING",
                        "message": (
                            f"Layer Inversion: {source_file} ({source_layer['name']}, Level {source_layer['level']}) "
                            f"imports {target_file} ({target_layer['name']}, Level {target_layer['level']})"
                        ),
                    })

    def _check_circular_dependencies(self) -> None:
        """Find circular dependency cycles using DFS cycle detection."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path_stack: List[str] = []
        found_cycles: List[List[str]] = []
        seen_cycle_signatures: Set[str] = set()

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path_stack.append(node)

            for neighbor in self.graph.forward_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Cycle detected: extract subpath from neighbor to end
                    cycle_start = path_stack.index(neighbor)
                    cycle = path_stack[cycle_start:] + [neighbor]
                    # Canonical signature to deduplicate rotated representations of same cycle
                    sig = "->".join(sorted(cycle[:-1]))
                    if sig not in seen_cycle_signatures:
                        seen_cycle_signatures.add(sig)
                        found_cycles.append(cycle)

            path_stack.pop()
            rec_stack.remove(node)

        for file_node in list(self.graph.forward_graph.keys()):
            if file_node not in visited:
                dfs(file_node)

        self.circular_dependencies = found_cycles

    def _check_orphan_modules(self) -> None:
        """Find non-entrypoint code files that are never imported anywhere."""
        entrypoint_prefixes = ["scripts/", "tests/", "remotion/", "workflows/", "app/main.py", "conftest.py"]
        orphans: List[str] = []

        for file_path, meta in self.graph.file_metadata.items():
            if not file_path.endswith(".py"):
                continue
            if any(file_path.startswith(prefix) or file_path == prefix for prefix in entrypoint_prefixes):
                continue
            # If nothing imports it and it imports nothing or few things
            callers = self.graph.reverse_graph.get(file_path, set())
            if len(callers) == 0:
                orphans.append(file_path)

        self.orphan_modules = sorted(orphans)


def main() -> int:
    parser = argparse.ArgumentParser(description="Antigravity Architectural Layer Boundary & Cycle Linter")
    parser.add_argument("--root", type=str, default=".", help="Root workspace directory")
    parser.add_argument("--check", action="store_true", help="Run audit and return exit code 1 if violations found")
    parser.add_argument("--json-output", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    root_dir = Path(args.root).resolve()
    checker = LayerBoundaryChecker(root_dir)
    result = checker.run_audit()

    if args.json_output:
        print(json.dumps(result, indent=2))
        return 0 if result["is_clean"] else 1

    print("\n" + "=" * 70)
    print("🏛️  ANTIGRAVITY ARCHITECTURAL LAYER BOUNDARY & CYCLE AUDIT")
    print("=" * 70)
    print(f"Total Files Analyzed       : {result['total_files_analyzed']}")
    print(f"Layer Inversion Violations : {result['layer_violations_count']}")
    print(f"Circular Dependency Chains : {result['circular_dependencies_count']}")
    print(f"Potential Orphan Modules   : {result['orphan_modules_count']}")
    print("-" * 70)

    if result["circular_dependencies"]:
        print("\n❌ CRITICAL: CIRCULAR DEPENDENCIES DETECTED:")
        for idx, cycle in enumerate(result["circular_dependencies"], 1):
            print(f"   [{idx}] {' -> '.join(cycle)}")

    if result["layer_violations"]:
        print("\n⚠️  LAYER INVERSIONS DETECTED:")
        for idx, violation in enumerate(result["layer_violations"], 1):
            sev = violation["severity"]
            print(f"   [{idx}] [{sev}] {violation['message']}")

    if result["orphan_modules"]:
        print(f"\nℹ️  ORPHAN MODULES ({len(result['orphan_modules'])}):")
        for orphan in result["orphan_modules"][:10]:
            print(f"   • {orphan}")
        if len(result["orphan_modules"]) > 10:
            print(f"   • ... (+{len(result['orphan_modules']) - 10} more)")

    print("\n" + "-" * 70)
    if result["is_clean"]:
        print("✅ VERDICT: ARCHITECTURAL BOUNDARIES 100% CLEAN (PASS)")
        print("=" * 70 + "\n")
        return 0
    else:
        print("❌ VERDICT: ARCHITECTURAL BOUNDARY DEFECTS FOUND (FAIL)")
        print("=" * 70 + "\n")
        return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
