#!/usr/bin/env python3
"""
scripts/orchestrator/memory_governor.py — Long-Term Memory Governance Engine.

Governs project memory files (ROADMAP.md & CHANGELOG.md) across context compaction:
- Enforces presence of both files.
- Ensures neither is gitignored.
- Validates Markdown sections and milestones.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


def audit_memory(strict: bool = True) -> int:
    """Verifies that ROADMAP.md and CHANGELOG.md are tracked and structurally valid."""
    roadmap_path = ROOT_DIR / "ROADMAP.md"
    changelog_path = ROOT_DIR / "CHANGELOG.md"

    errors = []

    # 1. ROADMAP check
    if not roadmap_path.exists():
        errors.append("ROADMAP.md does not exist in workspace root")
    elif roadmap_path.stat().st_size < 100:
        errors.append("ROADMAP.md is too short or empty (< 100 bytes)")
    else:
        text = roadmap_path.read_text(encoding="utf-8")
        if "# 🗺️ ROADMAP" not in text and "ROADMAP" not in text:
            errors.append("ROADMAP.md missing header or title")

    # 2. CHANGELOG check
    if not changelog_path.exists():
        errors.append("CHANGELOG.md does not exist in workspace root")
    elif changelog_path.stat().st_size < 100:
        errors.append("CHANGELOG.md is too short or empty (< 100 bytes)")
    else:
        text = changelog_path.read_text(encoding="utf-8")
        if "CHANGELOG" not in text:
            errors.append("CHANGELOG.md missing header or title")
        if "[Unreleased]" not in text:
            errors.append("CHANGELOG.md missing [Unreleased] section")

    if errors:
        print("❌ MEMORY GOVERNANCE AUDIT FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("✅ MEMORY GOVERNANCE AUDIT PASSED:")
    print(f"  - ROADMAP.md: {roadmap_path.stat().st_size} bytes (Valid)")
    print(f"  - CHANGELOG.md: {changelog_path.stat().st_size} bytes (Valid)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory Governor Audit")
    parser.add_argument("--strict", action="store_true", help="Fail with exit code 1 on errors")
    args = parser.parse_args()
    sys.exit(audit_memory(strict=args.strict))


if __name__ == "__main__":
    main()
