#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/legacy_inventory.py — AST Codebase & Legacy Inventory Analyzer (AVF-VOX-001).

Analyzes imports and entrypoints across the codebase to identify:
- Canonical modules to keep
- Dead or shadow pipelines to remove
- Reusable utilities for the unified vox pipeline
"""

from __future__ import annotations

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Any

ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git", "venv", ".venv", "venv_rembg", "__pycache__", ".pytest_cache",
    ".ruff_cache", "node_modules", "out", "runs", "reports", "_archive",
    "_bak_archive", "_backups_20260824", "archive"
}

def scan_python_files(root: Path) -> List[Path]:
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(Path(dirpath) / f)
    return py_files

def parse_imports(file_path: Path) -> Set[str]:
    imports = set()
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception:
        pass
    return imports

def build_inventory() -> Dict[str, Any]:
    all_files = scan_python_files(ROOT)
    rel_files = [f.relative_to(ROOT).as_posix() for f in all_files]

    # File classification heuristics
    keep = []
    remove = []
    reuse_candidates = []

    legacy_prefixes = (
        "app/pipeline/",
        "app/routes/produce_episode_route.py",
        "app/routes/run_episode_route.py",
        "archive/deprecated_scripts/",
        "scripts/execute_pipeline_b2_b35.py",
    )

    reusable_prefixes = (
        "app/services/beat_tts_engine.py",
        "app/services/cutout_service.py",
        "app/services/prompt_forge.py",
        "app/services/representation_shield.py",
        "app/services/edge_tts_generator.py",
        "stages/s09_voice_tts.py",
    )

    for rf in rel_files:
        if rf.startswith(legacy_prefixes):
            remove.append(rf)
        elif rf.startswith(reusable_prefixes):
            reuse_candidates.append(rf)
            keep.append(rf)
        else:
            keep.append(rf)

    inventory = {
        "total_python_files": len(rel_files),
        "keep_count": len(keep),
        "remove_count": len(remove),
        "reuse_candidates_count": len(reuse_candidates),
        "remove": sorted(remove),
        "reuse_candidates": sorted(reuse_candidates),
        "keep": sorted(keep)
    }

    out_file = ROOT / "legacy_inventory.json"
    out_file.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    return inventory

if __name__ == "__main__":
    inv = build_inventory()
    print(f"Inventory Complete:")
    print(f"  Total Python Files:   {inv['total_python_files']}")
    print(f"  Keep Count:           {inv['keep_count']}")
    print(f"  Remove Count:         {inv['remove_count']}")
    print(f"  Reuse Candidates:     {inv['reuse_candidates_count']}")
    print(f"Saved report to legacy_inventory.json")
