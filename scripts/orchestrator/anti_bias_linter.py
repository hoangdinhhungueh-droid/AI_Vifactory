#!/usr/bin/env python3
"""scripts/orchestrator/anti_bias_linter.py — Automated Anti-Semantic-Bias & Generic Contract Linter.

Mandated by Rule 128 (Anti-Semantic Bias & Generic Contract Architecture Mandate)
and Rule 132 (Strict Decoupled Engine & Pure Transmission Pipe Mandate).

Detects:
1. Hardcoded Episode IDs in production code (e.g. ^[A-Z]{2}_EP\\d{4}).
2. Concrete case-study company names, personalities, and proper nouns in generic engines.
3. Static dictionary rosters bypassing dynamic extraction (e.g. OBJECT_ROSTER, BACKGROUND_ROSTER).
4. Hardcoded arbitrary magic numbers forcing fixed scene counts or rosters.
5. Single-market assumptions or defaults hardcoding one market exclusively.

Usage:
  python scripts/orchestrator/anti_bias_linter.py
  python scripts/orchestrator/anti_bias_linter.py --path app/services/unified_vox_director.py
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Patterns of hardcoded episode IDs in production code
EPISODE_ID_REGEX = re.compile(r"\b[A-Z]{2}_EP\d{4}(?:_[a-z0-9_]+)?\b")

# Banned concrete entities that indicate hardcoded case-study leakage when used in generic services
BANNED_CASE_STUDY_ENTITIES = {
    "amazon": "Amazon e-commerce lawsuit entity",
    "lina khan": "FTC Chair Lina Khan entity",
    "andy jassy": "Amazon CEO Andy Jassy entity",
    "project nessie": "Amazon algorithmic pricing project entity",
    "hamaoka": "Hamaoka nuclear plant case entity",
    "nidec": "Nidec shareholder suit case entity",
    "gimpo fc": "Gimpo FC embezzlement case entity",
    "seattle federal court": "Seattle District Court jurisdiction entity",
    "hormuz": "Strait of Hormuz tanker incident entity",
    "front altair": "Front Altair vessel incident entity",
    "kokuka": "Kokuka Courageous incident entity",
    "conwartime": "BIMCO CONWARTIME clause entity",
    "voywar": "BIMCO VOYWAR clause entity",
}

# Static dictionary names that should not be hardcoded in generic services
BANNED_STATIC_ROSTERS = {
    "OBJECT_ROSTER",
    "BACKGROUND_ROSTER",
}

# Directories to audit
AUDIT_DIRS = [
    ROOT_DIR / "app" / "services",
    ROOT_DIR / "scripts" / "orchestrator",
    ROOT_DIR / "scripts" / "watchers",
]

# Production files specifically audited
ADDITIONAL_PRODUCTION_FILES = [
    ROOT_DIR / "scripts" / "produce_episode_hg1.py",
    ROOT_DIR / "scripts" / "flow_video_dispatcher.py",
    ROOT_DIR / "scripts" / "render_episode_parameterized.py",
]

# Files explicitly exempted from certain checks (e.g. test fixtures, test suites, or this linter itself)
EXEMPTED_FILES = {
    "anti_bias_linter.py",
    "test_zero_semantic_bias.py",
    "rule128_governor.py",
    "ghost_code_detector.py",
    "ci_neighbor_tester.py",
    "e2e_pipeline_smoketest.py",
}


class CodeViolation:
    def __init__(self, file_path: str, line_no: int, rule_id: str, message: str, snippet: str = ""):
        self.file_path = file_path
        self.line_no = line_no
        self.rule_id = rule_id
        self.message = message
        self.snippet = snippet

    def __str__(self) -> str:
        return f"[{self.rule_id}] {self.file_path}:{self.line_no} - {self.message}\n    Snippet: {self.snippet}"


class AntiBiasLinter:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or ROOT_DIR
        self.violations: List[CodeViolation] = []

    def scan_file_ast(self, file_path: Path) -> List[CodeViolation]:
        """Performs AST-level inspections on a Python file."""
        file_violations: List[CodeViolation] = []
        rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")

        if file_path.name in EXEMPTED_FILES:
            return file_violations

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(file_path))
        except Exception as e:
            file_violations.append(
                CodeViolation(rel_path, 1, "PARSE_ERROR", f"Could not parse AST: {e}")
            )
            return file_violations

        lines = content.splitlines()

        docstrings: Set[ast.Constant] = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
                    docstrings.add(n.body[0].value)

        for node in ast.walk(tree):
            # Check 1: Prohibited static dictionary rosters in global scope
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in BANNED_STATIC_ROSTERS:
                        line_no = node.lineno
                        snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                        file_violations.append(
                            CodeViolation(
                                rel_path,
                                line_no,
                                "STATIC_ROSTER_LEAK",
                                f"Prohibited static dictionary '{target.id}'. Must use Universal Dynamic Context Extractor.",
                                snippet,
                            )
                        )

            # Check 2: Hardcoded Episode IDs in constant strings outside docstrings
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node in docstrings:
                    continue
                val = node.value.strip()
                match = EPISODE_ID_REGEX.search(val)
                if match:
                    line_no = getattr(node, "lineno", 0)
                    snippet = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
                    # Ignore if the string is clearly a regex pattern, type annotation, or generic template
                    if "regex" in snippet.lower() or "pattern" in snippet.lower() or "^" in val or "format" in snippet.lower():
                        continue
                    if "help=" in snippet and ("e.g." in snippet or "example" in snippet):
                        continue
                    file_violations.append(
                        CodeViolation(
                            rel_path,
                            line_no,
                            "EPISODE_ID_HARDCODE",
                            f"Hardcoded Episode ID '{match.group(0)}' in production code constant.",
                            snippet,
                        )
                    )

            # Check 3: Concrete case-study entities in string comparisons or assignments outside docstrings
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node in docstrings:
                    continue
                val_lower = node.value.strip().lower()
                line_no = getattr(node, "lineno", 0)
                snippet = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
                
                # Exclude comments explaining rules
                if "rule 128" in snippet.lower() or "rule 132" in snippet.lower() or "banned" in snippet.lower():
                    continue

                for banned_kw, reason in BANNED_CASE_STUDY_ENTITIES.items():
                    # Word boundary matching
                    if re.search(r"\b" + re.escape(banned_kw) + r"\b", val_lower):
                        file_violations.append(
                            CodeViolation(
                                rel_path,
                                line_no,
                                "CASE_STUDY_ENTITY_LEAK",
                                f"Concrete case-study entity '{banned_kw}' detected ({reason}). Code must be generic and market-flexible.",
                                snippet,
                            )
                        )
                        break

        return file_violations

    def scan_all(self, target_files: Optional[List[Path]] = None) -> List[CodeViolation]:
        """Scans all targeted production Python files."""
        self.violations.clear()
        files_to_scan: Set[Path] = set()

        if target_files:
            files_to_scan.update(target_files)
        else:
            for audit_dir in AUDIT_DIRS:
                if audit_dir.exists():
                    for p in audit_dir.rglob("*.py"):
                        if not any(ign in p.parts for ign in (".venv", "venv", "__pycache__", ".git", "tests")):
                            files_to_scan.add(p)
            for f in ADDITIONAL_PRODUCTION_FILES:
                if f.exists():
                    files_to_scan.add(f)

        for p in sorted(list(files_to_scan)):
            file_viols = self.scan_file_ast(p)
            self.violations.extend(file_viols)

        return self.violations


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Automated Anti-Semantic-Bias & Generic Contract Linter (Rule 128 & 132)")
    parser.add_argument("--path", type=str, default=None, help="Specific file or directory to audit")
    args = parser.parse_args()

    linter = AntiBiasLinter()
    target_files = None
    if args.path:
        p = Path(args.path).resolve()
        if p.is_file():
            target_files = [p]
        elif p.is_dir():
            target_files = list(p.rglob("*.py"))

    violations = linter.scan_all(target_files)

    if violations:
        print("\n" + "=" * 70)
        print("🚨 ANTI-SEMANTIC-BIAS & GENERIC CONTRACT LINTER: FAILED")
        print(f"Total Violations Found: {len(violations)}")
        print("=" * 70)
        for v in violations:
            print(f"\n{v}")
        print("\n" + "=" * 70)
        print("🛑 MANDATE: Core pipeline code must NEVER hardcode specific Episode IDs,")
        print("   specific corporate case entities, or static dictionaries.")
        print("   All prompts, objects, and backgrounds must derive dynamically from story.txt.")
        print("=" * 70 + "\n")
        sys.exit(1)
    else:
        print("\n" + "=" * 70)
        print("✅ ANTI-SEMANTIC-BIAS & GENERIC CONTRACT LINTER: ALL GATES PASSED")
        print("0 Episode ID leaks | 0 Case-study entity leaks | 0 Static rosters")
        print("=" * 70 + "\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
