"""
tests/test_zero_semantic_bias.py -- Automated CI Linter for Zero Semantic Bias (Rule 128 & Rule 132).

Ensures that no generic pipeline code, service prompt, or orchestrator script contains
hardcoded domain terms, episode-specific entities, or case study remnants.
"""

import os
import re
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Whitelist of directories to audit
AUDIT_DIRS = [
    ROOT_DIR / "app" / "services",
    ROOT_DIR / "scripts"
]

# Files explicitly exempted (e.g. test files that explicitly test domain handling)
EXEMPTED_FILES = {
    "test_grounding_layer.py",
    "test_b15_seo_package_forge.py",
    "test_zero_semantic_bias.py"
}

# Forbidden episode-specific domain words that must NEVER appear in generic services/scripts
FORBIDDEN_DOMAIN_PATTERNS = [
    (r"\bhormuz\b", "Strait of Hormuz episode domain bleed"),
    (r"\btankers?\b", "Maritime tanker domain bleed"),
    (r"\bconwartime\b", "BIMCO CONWARTIME clause domain bleed"),
    (r"\bvoywar\b", "BIMCO VOYWAR clause domain bleed"),
    (r"\bfront\s+altair\b", "2019 Front Altair incident domain bleed"),
    (r"\bkokuka\b", "2019 Kokuka Courageous incident domain bleed"),
    (r"\birgc\b", "IRGC military entity domain bleed")
]


def get_python_files():
    py_files = []
    for audit_dir in AUDIT_DIRS:
        if not audit_dir.exists():
            continue
        for p in audit_dir.rglob("*.py"):
            parts = p.parts
            if any(part in (".venv", "venv", "__pycache__", ".git", "episodes", "workspace") for part in parts):
                continue
            if p.name.endswith((".bak", ".tmp")):
                continue
            if p.name in EXEMPTED_FILES:
                continue
            py_files.append(p)
    return py_files


class TestZeroSemanticBias:

    def test_no_episode_specific_leaks_in_generic_codebase(self):
        """Scans all production services and scripts to ensure 0 domain bleed."""
        violations = []
        py_files = get_python_files()

        assert len(py_files) > 0, "No python files discovered for semantic audit"

        for fpath in py_files:
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception as e:
                pytest.fail(f"Could not read {fpath}: {e}")

            lines = content.splitlines()
            for line_idx, line in enumerate(lines, 1):
                # Skip lines that explicitly discuss Rule 128 / zero semantic bias enforcement
                if "rule 128" in line.lower() or "zero-semantic-bias" in line.lower() or "blacklist" in line.lower():
                    continue

                for pattern, reason in FORBIDDEN_DOMAIN_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        rel_path = fpath.relative_to(ROOT_DIR)
                        violations.append(
                            f"[{reason}] at {rel_path}:{line_idx}\n"
                            f"   Snippet: {line.strip()}"
                        )

        if violations:
            err_msg = (
                f"\n🚨 SEMANTIC BIAS VIOLATION DETECTED (Rule 128 & Rule 132 Enforced):\n"
                f"Found {len(violations)} episode-specific leak(s) in generic pipeline code:\n\n"
                + "\n\n".join(violations)
                + "\n\nFix: Replace concrete episode entities with generic placeholders (<PLACEHOLDER>) "
                "or move editorial logic to Notion SoT!"
            )
            pytest.fail(err_msg)

    def test_pipeline_contracts_zero_leak(self):
        """Ensure PIPELINE_CONTRACTS.md has zero episode domain bias."""
        contract_file = ROOT_DIR / "PIPELINE_CONTRACTS.md"
        if not contract_file.exists():
            return

        content = contract_file.read_text(encoding="utf-8")
        for pattern, reason in FORBIDDEN_DOMAIN_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                pytest.fail(
                    f"PIPELINE_CONTRACTS.md violates Rule 128: Found '{match.group(0)}' ({reason})."
                )
