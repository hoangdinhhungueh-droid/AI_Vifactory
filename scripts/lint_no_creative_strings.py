#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/lint_no_creative_strings.py — CI Linter for Rule 132 (Decoupled Engine).

Scans Python codebase to ensure no creative prompt text or hardcoded tools
(e.g., 'Use the attached style sheet', 'vernier caliper', 'precision jaws')
are embedded directly into Python string literals in canonical services.
"""

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# Files that should be strictly pure transmission engines
TARGET_PATHS = [
    ROOT / "app" / "services" / "kinetic_sub_director.py",
    ROOT / "stages" / "s05_director_plan.py",
]

# Patterns that indicate hardcoded creative prompt strings in Python code
FORBIDDEN_CREATIVE_PATTERNS = [
    (r'Use the attached style sheet for materials only', "Hardcoded Style Block (Rule 132)"),
    (r'Use the attached style sheet as the strict visual system', "Hardcoded Flat Parallax Style (Rule 132)"),
    (r'Documentary cutout-collage stage:\s*a locked', "Hardcoded Locked Stage Style (Rule 132)"),
    (r'The camera is an actor:\s*it flies between layers', "Hardcoded Camera Kinematics (Rule 132)"),
]

def main() -> int:
    print("🔍 [RULE 132 LINTER] Scanning Python services for forbidden creative string literals...")
    violations = []

    for target in TARGET_PATHS:
        if not target.exists():
            continue
        content = target.read_text(encoding="utf-8")
        lines = content.splitlines()

        for pat, desc in FORBIDDEN_CREATIVE_PATTERNS:
            for idx, line in enumerate(lines, 1):
                # Ignore comments and docstrings mentioning the rule
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("*"):
                    continue
                if re.search(pat, line, re.IGNORECASE):
                    violations.append(f"{target.relative_to(ROOT)}:{idx} — {desc}: '{line.strip()[:60]}...'")

    if violations:
        print("❌ [RULE 132 VIOLATIONS DETECTED]:")
        for v in violations:
            print(f"   - {v}")
        print("\nFix: Move creative prompt text to config/prompts/cl3_vox_engine/ and load via TemplateRegistry.")
        return 1

    print("✅ [RULE 132 PASS]: Zero hardcoded creative prompt strings in target services!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
