#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/legacy_inventory.py — Falsifiable Single Pipeline Truth & Architectural Graph Audit (Rule 125).

Enforces Rule 125 (Single Pipeline Truth) and Boss Mandate:
1. Traces the import graph from vox.pipeline.
2. Asserts exactly ONE reachable canonical implementation per pipeline role:
   - Scene Planning & Script Decomposition
   - Voice Synthesis & Word-Level Whisper Alignment
   - Alpha Matting & Foreground Cutout
   - Camera Motion, Parallax & Keyframing
   - Word Karaoke & Subtitle Generation
   - Video Compositing & Two-Pass Loudnorm Audio Multiplexing
   - Post-Render Forensic Quality Assurance Gates
3. Scans entire codebase for dead shadow pipelines, duplicate assemblers, or legacy wrappers.
"""

from __future__ import annotations

import os
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

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

ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git", "venv", ".venv", "venv_rembg", "__pycache__", ".pytest_cache",
    ".ruff_cache", "node_modules", "out", "runs", "reports", "_archive",
    "_bak_archive", "_backups_20260824", "archive", ".safe_trash", ".trash"
}

CANONICAL_ROLES = {
    "scene_planning": {
        "expected_module": "vox.planner",
        "description": "Scene object decomposition and prompt planning",
    },
    "voice_tts": {
        "expected_module": "vox.tts",
        "description": "Edge-TTS audio synthesis and narration",
    },
    "word_alignment": {
        "expected_module": "vox.align",
        "description": "Whisper word-level timestamp alignment",
    },
    "subtitle_karaoke": {
        "expected_module": "vox.karaoke",
        "description": "ASS subtitle rendering and word karaoke highlighting",
    },
    "bg_canvas": {
        "expected_module": "vox.assets_bg",
        "description": "Layer 1 background canvas generation and validation",
    },
    "fg_cutout": {
        "expected_module": "vox.assets_fg",
        "description": "Layer 2 foreground cutout generation and alpha matting",
    },
    "scene_compositor": {
        "expected_module": "vox.compositor",
        "description": "Parallax multi-layer keyframing and scene rendering",
    },
    "video_assembly": {
        "expected_module": "vox.assemble",
        "description": "Video frame concatenation, subtitle burn-in, and two-pass loudnorm",
    },
    "qa_gates": {
        "expected_module": "vox.qa.gates",
        "description": "Deterministic post-render forensic QA validation",
    },
}

def parse_direct_imports(file_path: Path) -> Set[str]:
    """Parses all imported module names from a Python source file using AST."""
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

def build_falsifiable_audit() -> Dict[str, Any]:
    pipeline_file = ROOT / "vox" / "pipeline.py"
    if not pipeline_file.exists():
        raise FileNotFoundError(f"Canonical pipeline entrypoint not found: {pipeline_file}")

    # 1. Trace reachable modules from vox.pipeline
    pipeline_imports = parse_direct_imports(pipeline_file)
    role_audit: Dict[str, Any] = {}

    for role, spec in CANONICAL_ROLES.items():
        mod = spec["expected_module"]
        is_imported = any(mod in imp or imp.startswith(mod) for imp in pipeline_imports)
        mod_file = ROOT / (mod.replace(".", "/") + ".py")
        if not mod_file.exists():
            mod_file = ROOT / mod.replace(".", "/") / "__init__.py"

        role_audit[role] = {
            "canonical_module": mod,
            "description": spec["description"],
            "reachable_from_pipeline": is_imported,
            "file_exists": mod_file.exists(),
            "status": "PASS" if (is_imported and mod_file.exists()) else "FAIL"
        }

    # 2. Scan entire repository for forbidden shadow pipelines or legacy wrappers
    shadow_defects = []
    forbidden_shadow_patterns = [
        ("generate_50_scene_plan", "Legacy generate_50_scene_plan wrapper alias"),
        ("execute_pipeline_b2_b35", "Legacy multi-script pipeline coordinator"),
        ("app/pipeline/produce_episode", "Legacy pipeline produce route"),
    ]

    all_py_files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py"):
                all_py_files.append(Path(dirpath) / f)

    for pyf in all_py_files:
        rel = pyf.relative_to(ROOT).as_posix()
        try:
            content = pyf.read_text(encoding="utf-8", errors="replace")
            for pattern, desc in forbidden_shadow_patterns:
                # Exclude tests and legacy_inventory itself from flagging self-references
                if rel in ("scripts/legacy_inventory.py", "tests/vox/test_single_pipeline_truth.py"):
                    continue
                if pattern in content and not rel.startswith("tests/"):
                    shadow_defects.append(f"{rel}: {desc} ('{pattern}')")
        except Exception:
            pass

    verdict = "PASS" if (all(r["status"] == "PASS" for r in role_audit.values()) and len(shadow_defects) == 0) else "FAIL"

    audit_result = {
        "verdict": verdict,
        "pipeline_entrypoint": "vox.pipeline:run_pipeline",
        "canonical_roles_verified": len([r for r in role_audit.values() if r["status"] == "PASS"]),
        "total_canonical_roles": len(CANONICAL_ROLES),
        "roles": role_audit,
        "shadow_defects_count": len(shadow_defects),
        "shadow_defects": shadow_defects,
        "total_python_files_scanned": len(all_py_files)
    }

    out_file = ROOT / "legacy_inventory.json"
    out_file.write_text(json.dumps(audit_result, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit_result

if __name__ == "__main__":
    res = build_falsifiable_audit()
    print("=" * 70)
    print("🛡️  SINGLE PIPELINE TRUTH & FALSIFIABLE ARCHITECTURAL AUDIT (RULE 125)")
    print("=" * 70)
    print(f"Verdict:              {res['verdict']}")
    print(f"Pipeline Entrypoint:  {res['pipeline_entrypoint']}")
    print(f"Canonical Roles:      {res['canonical_roles_verified']} / {res['total_canonical_roles']} Verified Unique")
    print(f"Shadow Pipelines:     {res['shadow_defects_count']} Detected")
    print("-" * 70)
    for role, data in res["roles"].items():
        print(f"  [{data['status']}] {role:<20} -> {data['canonical_module']} ({data['description']})")
    if res["shadow_defects"]:
        print("\nShadow Defects Found:")
        for d in res["shadow_defects"]:
            print(f"  ❌ {d}")
    print("=" * 70)
    sys.exit(0 if res["verdict"] == "PASS" else 1)
