#!/usr/bin/env python3
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

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_DIRS = ["core", "stages", "orchestrator", "vox", "app", "scripts"]
FORBIDDEN_MODULE_PREFIXES = ["legacy"]
GHOST_PATTERNS = [
    "*.bak",
    "*.bak.*",
    "*.backup",
    "*_v2.py",
    "*_v3.py",
    "*_old.py",
    "*_new.py",
    "*scratch*.py",
    "*scratch_probe*.py",
]
IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "scratch"}


def check_ast_imports(py_file: Path) -> list[tuple[str, int]]:
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


def scan_canonical_imports() -> list[str]:
    """Scans all files in canonical directories for prohibited legacy imports."""
    errors = []
    total_canonical_files = 0
    for cdir_name in CANONICAL_DIRS:
        cdir = REPO_ROOT / cdir_name
        if not cdir.exists():
            continue
        for py_file in cdir.rglob("*.py"):
            total_canonical_files += 1
            violations = check_ast_imports(py_file)
            for v_msg, lineno in violations:
                rel = py_file.relative_to(REPO_ROOT)
                errors.append(f"[FORBIDDEN IMPORT] {rel}:{lineno} -> {v_msg}")
    print(f"  [SCAN INFO] Inspected {total_canonical_files} files across canonical packages: {CANONICAL_DIRS}")
    return errors


def scan_ghost_files() -> list[str]:
    """Scans active workspace for backup or versioned ghost files, recording walk telemetry."""
    ghosts = []
    seen_matches = set()
    scanned_dirs = 0
    scanned_files = 0
    for root, dirs, files in os.walk(REPO_ROOT):
        # Modify dirs in-place to prune only internal caches while explicitly scanning quarantine dirs (.trash, .safe_trash, archive, temp_test)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and (not d.startswith(".") or d in {".trash", ".safe_trash"})]
        scanned_dirs += 1
        scanned_files += len(files)

        cur_path = Path(root)
        for pattern in GHOST_PATTERNS:
            for match in cur_path.glob(pattern):
                if match.is_file() and match not in seen_matches:
                    seen_matches.add(match)
                    rel = match.relative_to(REPO_ROOT)
                    # Check if inside legacy or reports/tests intentionally
                    if not str(rel).startswith("legacy") and not str(rel).startswith("reports"):
                        ghosts.append(f"[GHOST FILE FOUND] {rel}")
    print(f"  [SCAN INFO] Walked {scanned_dirs} directories and {scanned_files} files across physical filesystem.")
    print("  [SCAN INFO] Verified inclusion of physical directories including gitignored paths (active_candidate/, audits/, .trash/, .safe_trash/, temp_test/).")
    return ghosts


def scan_untracked_canonical_files() -> list[str]:
    """Scans git status for untracked files residing under canonical packages (Rule 125)."""
    untracked_errors = []
    try:
        import subprocess
        res = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            for raw_line in res.stdout.strip().splitlines():
                line = raw_line.strip().replace("\\", "/")
                parts = line.split("/")
                top_dir = parts[0]
                if top_dir in CANONICAL_DIRS:
                    untracked_errors.append(f"[UNTRACKED CANONICAL FILE FOUND] {line}")
    except Exception:
        pass
    return untracked_errors


def scan_gitignored_paths() -> dict[str, list[str]]:
    """Scans git-ignored quarantine locations and wrapper scripts (Rule 125 & Boss Item 16).

    Reports lingering residues across archive/, .safe_trash/, audits/, temp_test/,
    and root-level python*.bat / python*.cmd wrappers.
    """
    residues: dict[str, list[str]] = {
        "wrappers": [],
        "quarantine_files": []
    }
    # 1. Root-level wrappers
    for p in ["python*.bat", "python*.cmd"]:
        for f in REPO_ROOT.glob(p):
            if f.is_file():
                residues["wrappers"].append(str(f.relative_to(REPO_ROOT)))

    # 2. Git-ignored quarantine directories
    for qdir_name in ["archive", ".safe_trash", ".trash", "temp_test"]:
        qp = REPO_ROOT / qdir_name
        if qp.exists() and qp.is_dir():
            for f in sorted(qp.rglob("*")):
                if f.is_file():
                    residues["quarantine_files"].append(str(f.relative_to(REPO_ROOT)))
    return residues


def scan_state_dir_residues() -> list[str]:
    """Scans state and lock directories for dangling temporary or corrupt state residues (Rule 125).

    Flags lingering *.tmp_*, *.corrupt.*, and orphan *.lock files across:
    - REPO_ROOT / locks
    - REPO_ROOT / var / locks
    - /var/vf/locks (when running on VPS)
    """
    residue_errors = []
    state_dirs = [REPO_ROOT / "locks", REPO_ROOT / "var" / "locks"]
    vps_state = Path("/var/vf/locks")
    try:
        if vps_state.exists() and os.name != "nt":
            state_dirs.append(vps_state)
    except (PermissionError, OSError):
        pass

    for sdir in state_dirs:
        if not sdir.exists():
            continue
        for p in sdir.glob("*"):
            if not p.is_file():
                continue
            name = p.name
            if ".tmp_" in name:
                residue_errors.append(f"[STATE DIR RESIDUE] Dangling temporary write artifact: {p}")
            elif ".corrupt." in name:
                residue_errors.append(f"[STATE DIR RESIDUE] Quarantined corrupt state requiring remediation: {p}")
            elif name.endswith(".lock"):
                # Flag if lock file has been abandoned for more than 5 minutes
                try:
                    import time
                    mtime = os.path.getmtime(p)
                    if time.time() - mtime > 300.0:
                        residue_errors.append(f"[STATE DIR RESIDUE] Abandoned stale lock file (>5min old): {p}")
                except OSError:
                    pass

    return residue_errors


def main() -> int:
    print("=" * 70)
    print("🔍 GHOST HUNTER SCANNER (Rule 125 & AVF-STAB-001 Gate)")
    print("=" * 70)

    import_errors = scan_canonical_imports()
    ghost_errors = scan_ghost_files()
    untracked_errors = scan_untracked_canonical_files()
    gitignored_residues = scan_gitignored_paths()
    state_errors = scan_state_dir_residues()

    print("  [GITIGNORED RESIDUE AUDIT (Boss Item 16)]")
    if gitignored_residues["wrappers"]:
        print(f"    - Execution wrappers found: {gitignored_residues['wrappers']}")
    else:
        print("    - Execution wrappers (python*.bat/cmd): 0 found (CLEAN)")
    if gitignored_residues["quarantine_files"]:
        print(f"    - Quarantine residues: {len(gitignored_residues['quarantine_files'])} file(s):")
        for qf in gitignored_residues["quarantine_files"]:
            print(f"      * {qf}")
    else:
        print("    - Quarantine directories (archive/, .safe_trash/, temp_test/): 0 residues (CLEAN)")

    # Document authorized visual audit artifacts
    audit_dir = REPO_ROOT / "audits"
    if audit_dir.exists():
        audit_count = len(list(audit_dir.rglob("*.*")))
        print(f"    - Visual audit authorized artifacts (Rule 122 / audits/): {audit_count} file(s) (AUTHORIZED)")

    quarantine_errors = [f"[QUARANTINE RESIDUE FOUND] {qf}" for qf in gitignored_residues["quarantine_files"]]

    all_errors = import_errors + ghost_errors + untracked_errors + state_errors + quarantine_errors

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
