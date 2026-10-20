#!/usr/bin/env python3
"""scripts/forensics/probe_ast_rule139.py — Authoritative AST Rule 139 Deterministic Anti-Symptom Scanner (v2.2.0).
Enforces Rule 139 (Disciplined Code-ification & Zero-Symptom Patching):
- Flags silent exception handlers (bare pass, ellipsis, string literals without active error handling) as RULE_139_SILENT_EXCEPT_PASS.
- Flags throwaway exception assignments (_ = exc, _: Any = exc, chained _ = a = exc, unpack (_, ...) = exc) as RULE_139_THROWAWAY_EXCEPT_SUPPRESSION.
- Flags unreachable dead code following return/raise/break/continue as RULE_139_UNREACHABLE_CODE.
Reconciles findings against config/ast_ratchet_baseline.json allowlist.
Outputs structured JSON report and exits 0 on 0 defects, 1 on defects found.
"""

import ast
import glob
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def is_throwaway_target(target: ast.AST) -> bool:
    """Checks if assignment target is '_' or contains '_' in unpacking."""
    if isinstance(target, ast.Name) and target.id == "_":
        return True
    if isinstance(target, (ast.Tuple, ast.List)):
        return any(is_throwaway_target(elt) for elt in target.elts)
    return False


def is_throwaway_assignment(stmt: ast.AST) -> bool:
    """Checks if statement assigns an exception or value to throwaway '_' target."""
    if isinstance(stmt, ast.Assign):
        return any(is_throwaway_target(t) for t in stmt.targets)
    if isinstance(stmt, ast.AnnAssign):
        return is_throwaway_target(stmt.target)
    return False


def is_noop_statement(stmt: ast.AST) -> bool:
    """Checks if statement is a no-op (pass, ellipsis, or constant expression)."""
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return True
    return False


def scan_file_ast(
    file_path: str,
    repo_rel: str,
    allowlist: Set[Tuple[str, int, str]],
) -> Tuple[List[Dict[str, Any]], int]:
    """Parses AST for file and returns (defects, allowed_count)."""
    defects: List[Dict[str, Any]] = []
    allowed_count = 0

    try:
        content = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(content, filename=file_path)
    except Exception as exc:
        return [{"file": repo_rel, "line": 1, "severity": "CRITICAL", "error": str(exc)}], 0

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Check if all statements in handler body are no-ops or throwaway assignments
            body_stmts = node.body
            all_suppression = bool(body_stmts) and all(
                is_noop_statement(s) or is_throwaway_assignment(s) for s in body_stmts
            )

            if all_suppression:
                has_throwaway = any(is_throwaway_assignment(s) for s in body_stmts)
                h_type = ast.unparse(node.type) if node.type else "bare"
                if has_throwaway:
                    rule_str = f"RULE_139_THROWAWAY_EXCEPT_SUPPRESSION ({h_type})"
                else:
                    rule_str = f"RULE_139_SILENT_EXCEPT_PASS ({h_type})"

                if (repo_rel, node.lineno, rule_str) in allowlist:
                    allowed_count += 1
                else:
                    defects.append({
                        "file": repo_rel,
                        "line": node.lineno,
                        "severity": "HIGH",
                        "rule": rule_str,
                    })

        for attr in ("body", "orelse", "finalbody"):
            b_list = getattr(node, attr, None)
            if isinstance(b_list, list) and len(b_list) > 1:
                for idx, stmt in enumerate(b_list[:-1]):
                    if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                        lineno = b_list[idx + 1].lineno
                        rule_str = "RULE_139_UNREACHABLE_CODE"
                        if (repo_rel, lineno, rule_str) in allowlist:
                            allowed_count += 1
                        else:
                            defects.append({
                                "file": repo_rel,
                                "line": lineno,
                                "severity": "HIGH",
                                "rule": rule_str,
                            })

    return defects, allowed_count


def run_scanner(repo_root: Path) -> Dict[str, Any]:
    """Runs authoritative AST Rule 139 scanner over tracked repository files."""
    allowlist_path = repo_root / "config" / "ast_ratchet_baseline.json"
    allowlist: Set[Tuple[str, int, str]] = set()
    if allowlist_path.exists():
        try:
            al_data = json.loads(allowlist_path.read_text(encoding="utf-8"))
            for ent in al_data.get("entries", []):
                allowlist.add((ent["file"].replace("\\", "/"), ent["line"], ent["rule"]))
        except Exception as exc:
            sys.stderr.write(f"Warning: could not load ratchet baseline: {exc}\n")

    # Get git tracked python files
    try:
        tracked_res = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "*.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        tracked_set = {line.strip().replace("\\", "/") for line in tracked_res.stdout.splitlines() if line.strip()}
    except Exception:
        tracked_set = set()

    patterns = [
        str(repo_root / "vox" / "**" / "*.py"),
        str(repo_root / "stages" / "**" / "*.py"),
        str(repo_root / "app" / "**" / "*.py"),
        str(repo_root / "core" / "**" / "*.py"),
        str(repo_root / "scripts" / "**" / "*.py"),
    ]

    discovered_files = sorted({f for pat in patterns for f in glob.glob(pat, recursive=True)})
    scanned_files = []
    all_defects: List[Dict[str, Any]] = []
    total_allowed = 0

    for f_path in discovered_files:
        rel = os.path.relpath(f_path, str(repo_root)).replace("\\", "/")
        if tracked_set and rel not in tracked_set:
            continue
        scanned_files.append(rel)
        file_defects, file_allowed = scan_file_ast(f_path, rel, allowlist)
        all_defects.extend(file_defects)
        total_allowed += file_allowed

    crit_count = sum(1 for d in all_defects if d.get("severity") == "CRITICAL")
    high_count = sum(1 for d in all_defects if d.get("severity") == "HIGH")

    return {
        "scanner_name": "probe_ast_rule139.py",
        "scanner_version": "2.2.0",
        "scanned_files": len(scanned_files),
        "critical_count": crit_count,
        "high_count": high_count,
        "allowed_legacy_count": total_allowed,
        "verdict": "PASS (0 Critical / 0 High)" if not all_defects else "DEFECTS_DETECTED",
        "defects": all_defects,
    }


def main():
    root = Path(__file__).resolve().parent.parent.parent
    report = run_scanner(root)
    print(json.dumps(report, indent=2))
    sys.exit(1 if report["defects"] else 0)


if __name__ == "__main__":
    main()
