"""scripts/orchestrator/rule128_governor.py — Rule 128 Architectural Governance Guard.

Enforces Rule 128 (Anti-Semantic-Bias & Generic Contract Architecture Mandate):
1. Prohibits episode-specific monkey-patching, hardcoded topic dictionaries, or sector
   conditionals in core pipeline code.
2. Validates generic Task ID naming conventions (^[A-Z]{2}_EP\\d{4}_[a-z0-9_]+$).
3. Performs runtime prompt audits to detect cross-domain semantic bleed (e.g. server racks
   in rural/agricultural stories) and prompt phrase stuttering.
4. Audits Director Plans for dynamic context & character extraction rather than static templates.
"""

import ast
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class Rule128ViolationError(Exception):
    """Raised when an architectural or runtime component violates Rule 128."""

    def __init__(self, message: str, violations: Optional[List[str]] = None):
        super().__init__(message)
        self.violations = violations or []


TASK_ID_REGEX = re.compile(r"^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$")

# Domain-specific keyword signatures used for cross-domain bleed detection
DOMAIN_LEAK_SIGNATURES = {
    "tech_infrastructure": [
        "server rack",
        "server room",
        "silicon wafer",
        "semiconductor",
        "cleanroom suit",
        "printed circuit board",
        "microchip fab",
        "data center aisle",
    ],
    "agriculture": [
        "pesticide bottle",
        "terraced field",
        "rice paddy",
        "combine harvester",
        "rural cooperative warehouse",
        "agrochemical",
    ],
    "financial_trading": [
        "wall street trading floor",
        "bloomberg terminal",
        "stock ticker tape",
        "trading desk pit",
        "nyse trading floor",
    ],
    "victorian_medical": [
        "victorian cholera ward",
        "broad street pump handle",
        "19th century physician coat",
        "epidemiological ledger map",
        "gas lamp cobblestone",
    ],
}

# Regex to detect phrase stuttering / repeated word sequences (2+ words repeated consecutively)
STUTTER_REGEX = re.compile(
    r"(\b[a-zA-Z0-9_-]+(?:[\s,]+[a-zA-Z0-9_-]+){1,10}\b)[\s,]+\1\b",
    re.IGNORECASE,
)
COMMON_STUTTER_PREFIXES = [
    "stylized editorial graphic novel",
    "cinematic documentary",
    "16:9 widescreen",
]


def validate_generic_task_id(task_id: str) -> bool:
    """Validates that task_id matches generic pattern ^[A-Z]{2}_EP\\d{4}_[a-z0-9_]+$."""
    if not task_id or not isinstance(task_id, str):
        return False
    return bool(TASK_ID_REGEX.match(task_id))


class Rule128Governor:
    """Governance guard enforcing Rule 128 statically and at runtime."""

    def __init__(self, strict: bool = True):
        self.strict = strict
        self.violations: List[str] = []

    def reset(self) -> None:
        """Reset recorded violations."""
        self.violations.clear()

    def check_task_id(self, task_id: str) -> bool:
        """Validates Task ID against Rule 117/Rule 128 generic format."""
        if not validate_generic_task_id(task_id):
            msg = (
                f"Task ID '{task_id}' violates Rule 128 generic pattern "
                f"(expected '^[A-Z]{{2}}_EP\\d{{4}}_[a-z0-9_]+$', e.g. 'EN_EP0260_topic_slug')"
            )
            self.violations.append(msg)
            if self.strict:
                raise Rule128ViolationError(msg, [msg])
            return False
        return True

    def scan_code_ast(self, code_str: str, filename: str = "<string>") -> List[str]:
        """Statically inspects Python code AST for prohibited hardcoded sector/episode branching."""
        file_violations: List[str] = []
        try:
            tree = ast.parse(code_str, filename=filename)
        except SyntaxError as e:
            file_violations.append(f"Syntax error in {filename}: {e}")
            return file_violations

        # Ban hardcoded episode IDs inside production conditionals or assignments (outside comments/docstrings)
        banned_ep_pattern = re.compile(r"^[A-Z]{2}_EP\d{4}_")

        for node in ast.walk(tree):
            # Check constant strings
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip()
                # Check for hardcoded episode IDs being assigned or compared
                if banned_ep_pattern.match(val) and not filename.endswith(
                    ("test_", "smoketest.py", "ci_neighbor_tester.py", "fixtures.py")
                ):
                    # Flag if this is used in equality checks or hardcoded fallback
                    parent = getattr(node, "parent", None)
                    file_violations.append(
                        f"{filename}:{getattr(node, 'lineno', 0)}: Prohibited hardcoded episode ID "
                        f"constant '{val}' in production code."
                    )

            # Check for suspicious static dict naming (e.g. hardcoding domain archetype lists)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # If a developer re-introduces static domain dictionaries like CINEMATIC_ARCHETYPES
                        if name == "CINEMATIC_ARCHETYPES" and not filename.endswith(
                            ("audit", "test", "legacy")
                        ):
                            file_violations.append(
                                f"{filename}:{node.lineno}: Prohibited static dictionary '{name}' "
                                f"violates Rule 128. Must use Universal Dynamic Context Extractor."
                            )

        return file_violations

    def scan_file(self, filepath: str) -> List[str]:
        """Scans a python file on disk for Rule 128 static violations."""
        if not os.path.isfile(filepath):
            return []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            violations = self.scan_code_ast(content, filename=filepath)
            self.violations.extend(violations)
            return violations
        except Exception as e:
            err = f"Failed to scan {filepath}: {e}"
            self.violations.append(err)
            return [err]

    def scan_directory(self, dir_path: str, excludes: Optional[List[str]] = None) -> List[str]:
        """Recursively scans directory for Rule 128 violations."""
        excludes = excludes or ["tests", "test_", ".git", "__pycache__", ".agents", "venv"]
        all_violations: List[str] = []
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not any(exc in d for exc in excludes)]
            for file in files:
                if file.endswith(".py") and not any(exc in file for exc in excludes):
                    path = os.path.join(root, file)
                    v = self.scan_file(path)
                    all_violations.extend(v)
        return all_violations

    def audit_director_plan(
        self, director_plan: Dict[str, Any], story_topic: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """Audits Director Plan for dynamic context and persona extraction without domain hardcoding."""
        issues: List[str] = []
        scenes = director_plan.get("scenes", [])
        if not scenes:
            issues.append("Director plan has no scenes.")
            return False, issues

        # Check for dynamic context representation
        dyn_ctx = director_plan.get("dynamic_context") or {}
        # Dynamic context should provide era and physical environment if present
        if dyn_ctx:
            if not isinstance(dyn_ctx, dict):
                issues.append("dynamic_context must be a dictionary.")

        # Check for character ensemble dynamic extraction
        ensemble = director_plan.get("character_ensemble") or []
        if ensemble and not isinstance(ensemble, list):
            issues.append("character_ensemble must be an array of dynamic roles.")

        # Check scene prompt relevance
        for idx, scene in enumerate(scenes):
            bg_desc = str(scene.get("setting_description") or scene.get("image_prompt") or "")
            fg_desc = str(
                scene.get("character_description") or scene.get("foreground_prompt") or ""
            )

            # Check stutter in descriptions
            if STUTTER_REGEX.search(bg_desc):
                issues.append(f"Scene {idx + 1} setting description contains phrase stuttering.")
            if STUTTER_REGEX.search(fg_desc):
                issues.append(f"Scene {idx + 1} character description contains phrase stuttering.")

        passed = len(issues) == 0
        if not passed:
            self.violations.extend(issues)
            if self.strict:
                raise Rule128ViolationError(
                    f"Director plan failed Rule 128 audit ({len(issues)} issues)", issues
                )
        return passed, issues

    def audit_prompts(
        self,
        prompts_dict: Dict[str, Any],
        topic_domain: str = "general",
        allowed_domains: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """Audits generated prompts (prompts_forge.json) for cross-domain bleed and stuttering.

        Args:
            prompts_dict: The dictionary containing 'backgrounds' and 'foregrounds'.
            topic_domain: Narrative domain of current episode (e.g. 'agriculture', 'finance', 'medical', 'tech').
            allowed_domains: Domains explicitly allowed to appear in visual prompts.
        """
        issues: List[str] = []
        allowed = set(allowed_domains or [topic_domain])

        bgs = prompts_dict.get("backgrounds") or {}
        fgs = prompts_dict.get("foregrounds") or {}

        # Collect all prompt texts
        prompt_texts: List[Tuple[str, str]] = []
        if isinstance(bgs, dict):
            for k, v in bgs.items():
                prompt_texts.append((f"BG:{k}", str(v.get("prompt", v) if isinstance(v, dict) else v)))
        elif isinstance(bgs, list):
            for idx, item in enumerate(bgs):
                prompt_texts.append((f"BG:{idx}", str(item.get("prompt", item) if isinstance(item, dict) else item)))

        if isinstance(fgs, dict):
            for k, v in fgs.items():
                prompt_texts.append((f"FG:{k}", str(v.get("prompt", v) if isinstance(v, dict) else v)))
        elif isinstance(fgs, list):
            for idx, item in enumerate(fgs):
                prompt_texts.append((f"FG:{idx}", str(item.get("prompt", item) if isinstance(item, dict) else item)))

        # 1. Check for cross-domain bleed
        for domain_name, leak_keywords in DOMAIN_LEAK_SIGNATURES.items():
            if domain_name in allowed or domain_name == topic_domain:
                continue  # This domain is expected/allowed

            for label, text in prompt_texts:
                text_lower = text.lower()
                for kw in leak_keywords:
                    if kw in text_lower:
                        msg = (
                            f"Cross-Domain Bleed detected in {label}: Found '{kw}' "
                            f"(signature of '{domain_name}') in episode domain '{topic_domain}'."
                        )
                        issues.append(msg)

        # 2. Check for phrase stuttering / repeated tokens
        for label, text in prompt_texts:
            text_lower = text.lower()
            # Check for common stutter prefixes repeated > 1
            for prefix in COMMON_STUTTER_PREFIXES:
                if text_lower.count(prefix) > 1:
                    issues.append(
                        f"Phrase stuttering in {label}: Prefix '{prefix}' repeated {text_lower.count(prefix)} times."
                    )

            # Check repeated consecutive phrases via regex finditer
            for match in STUTTER_REGEX.finditer(text):
                repeated_phrase = match.group(1).strip()
                issues.append(f"Phrase stuttering in {label}: Repeated sequence '{repeated_phrase}'.")

        # 3. Check Layer 2 FG Chroma Key requirement (#FF00FF)
        for label, text in prompt_texts:
            if label.startswith("FG:"):
                text_lower = text.lower()
                if "#ff00ff" not in text_lower and "magenta" not in text_lower:
                    issues.append(
                        f"{label} missing mandatory Layer 2 #FF00FF magenta chroma key isolation."
                    )

        passed = len(issues) == 0
        if not passed:
            self.violations.extend(issues)
            if self.strict:
                raise Rule128ViolationError(
                    f"Prompts failed Rule 128 audit with {len(issues)} violations", issues
                )
        return passed, issues
