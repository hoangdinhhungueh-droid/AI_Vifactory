#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ghost_scan.py — Automated Anti-Ghost & Anti-Bypass Scanner (Rule 125 & AVF-STAB-001).

Enforces:
1. Zero imports of legacy or deprecated modules from canonical code (core/, stages/, orchestrator/).
2. Zero leftover ghost artifacts (*.bak*, *.backup*, *_v2.py, *_v3.py) in active directories.
3. Strict Exit Code 0 on clean, 1 on violation (Gate Keeper for CI/CD).
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_DIRS = ["core", "stages", "orchestrator"]
FORBIDDEN_MODULE_PREFIXES = ["legacy"]
GHOST_PATTERNS = ["*.bak", "*.bak.*", "*.backup", "*_v2.py", "*_v3.py", "*_old.py", "*_new.py"]
IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def check_ast_imports(py_file: Path) -> List[Tuple[str, int]]:
    """Inspects AST of a python file to detect forbidden or legacy imports."""
    violations = []
    try:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(py_file))
    except SyntaxError as e:
        violations.append((f"Syntax error parsing {py_file}: {e}", 0))
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in FORBIDDEN_MODULE_PREFIXES:
                    if alias.name == prefix or alias.name.startswith(prefix + "."):
                        violations.append((f"Import '{alias.name}' is quarantined legacy", node.lineno))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for prefix in FORBIDDEN_MODULE_PREFIXES:
                if mod == prefix or mod.startswith(prefix + "."):
                    violations.append((f"Import from '{mod}' is quarantined legacy", node.lineno))
    return violations


def scan_canonical_imports() -> List[str]:
    """Scans all files in canonical directories for prohibited legacy imports."""
    errors = []
    for cdir_name in CANONICAL_DIRS:
        cdir = REPO_ROOT / cdir_name
        if not cdir.exists():
            continue
        for py_file in cdir.rglob("*.py"):
            violations = check_ast_imports(py_file)
            for v_msg, lineno in violations:
                rel = py_file.relative_to(REPO_ROOT)
                errors.append(f"[FORBIDDEN IMPORT] {rel}:{lineno} -> {v_msg}")
    return errors


def scan_ghost_files() -> List[str]:
    """Scans active workspace for backup or versioned ghost files."""
    ghosts = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Modify dirs in-place to prune ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        
        cur_path = Path(root)
        for pattern in GHOST_PATTERNS:
            for match in cur_path.glob(pattern):
                if match.is_file():
                    rel = match.relative_to(REPO_ROOT)
                    # Check if inside legacy or reports/tests intentionally
                    if not str(rel).startswith("legacy") and not str(rel).startswith("reports"):
                        ghosts.append(f"[GHOST FILE FOUND] {rel}")
    return ghosts


def main() -> int:
    print("=" * 70)
    print("🔍 GHOST HUNTER SCANNER (Rule 125 & AVF-STAB-001 Gate)")
    print("=" * 70)

    import_errors = scan_canonical_imports()
    ghost_errors = scan_ghost_files()

    all_errors = import_errors + ghost_errors

    if all_errors:
        print(f"❌ FOUND {len(all_errors)} GHOST / BYPASS VIOLATION(S):")
        for err in all_errors:
            print(f"  - {err}")
        print("\nFix these violations or move dead files to 'legacy/' to pass.")
        return 1

    print("✅ ZERO GHOST REMNANTS DETECTED:")
    print("  - Canonical code is 100% decoupled from legacy/.")
    print("  - No unapproved versioned (_v2/_v3) or backup files in active paths.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
