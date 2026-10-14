#!/usr/bin/env python3
"""tools/codemap/survey_inventory.py — Phase 0 Survey for Code Map & Pipeline Traceability.

Discovers:
  - Entrypoints (scripts, CLIs, main blocks)
  - Canonical & Candidate Pipeline Stages
  - Pydantic Data Models (Contracts)
  - Approval Gate Handlers (Human-in-the-loop, Council decisions)
  - Artifact Directories & Paths
"""

import ast
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".opencodereview", "dist", "build", "site-packages"
}

def is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS or part.startswith(".bak"):
            return True
    return False

def scan_entrypoints() -> list[dict[str, Any]]:
    entrypoints = []
    for py_file in ROOT_DIR.glob("**/*.py"):
        if is_excluded(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "if __name__ ==" in content:
                # Find line number
                lines = content.splitlines()
                line_no = 1
                for idx, line in enumerate(lines, 1):
                    if "if __name__ ==" in line:
                        line_no = idx
                        break
                rel_path = py_file.relative_to(ROOT_DIR).as_posix()
                entrypoints.append({
                    "name": f"cli:{py_file.stem}",
                    "qualname": f"{py_file.stem}:__main__",
                    "file": rel_path,
                    "line": line_no,
                    "type": "cli_entrypoint"
                })
        except Exception:
            pass
    return sorted(entrypoints, key=lambda x: x["file"])

def scan_candidate_stages() -> list[dict[str, Any]]:
    stages = []
    stages_dir = ROOT_DIR / "stages"
    if stages_dir.exists():
        for py_file in sorted(stages_dir.glob("s*.py")):
            rel_path = py_file.relative_to(ROOT_DIR).as_posix()
            stem = py_file.stem  # e.g. s01_ideation
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
                entry_fn = None
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name in ("run_stage", "execute", "run", f"execute_{stem}", "main"):
                            entry_fn = {"name": node.name, "line": node.lineno}
                            break
                        if entry_fn is None and not node.name.startswith("_"):
                            entry_fn = {"name": node.name, "line": node.lineno}

                stages.append({
                    "stage_id": stem,
                    "file": rel_path,
                    "entry_function": entry_fn["name"] if entry_fn else "run_stage",
                    "line": entry_fn["line"] if entry_fn else 1,
                    "canonical": True
                })
            except Exception as e:
                stages.append({
                    "stage_id": stem,
                    "file": rel_path,
                    "entry_function": "run_stage",
                    "line": 1,
                    "canonical": True,
                    "error": str(e)
                })
    return stages

def scan_models() -> list[dict[str, Any]]:
    models = []
    for py_file in ROOT_DIR.glob("**/*.py"):
        if is_excluded(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "BaseModel" not in content and "BaseModel" not in content:
                continue
            tree = ast.parse(content)
            rel_path = py_file.relative_to(ROOT_DIR).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if inherits from BaseModel
                    for base in node.bases:
                        base_name = getattr(base, "id", None) or getattr(base, "attr", None)
                        if base_name in ("BaseModel", "StageArtifact"):
                            models.append({
                                "model_name": node.name,
                                "qualname": f"{py_file.with_suffix('').as_posix().replace('/', '.')}.{node.name}",
                                "file": rel_path,
                                "line": node.lineno
                            })
        except Exception:
            pass
    return sorted(models, key=lambda x: (x["file"], x["line"]))

def scan_approval_handlers() -> list[dict[str, Any]]:
    handlers = []
    keywords = [
        "human_gate_checkpoint", "APPROVED_BY_USER", "CouncilDecision",
        "PENDING_USER_APPROVAL", "record_approval", "ask_question",
        "interactive", "review_gallery.html"
    ]
    for py_file in ROOT_DIR.glob("**/*.py"):
        if is_excluded(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            rel_path = py_file.relative_to(ROOT_DIR).as_posix()
            for idx, line in enumerate(content.splitlines(), 1):
                for kw in keywords:
                    if kw in line:
                        handlers.append({
                            "keyword": kw,
                            "file": rel_path,
                            "line": idx,
                            "snippet": line.strip()[:120]
                        })
                        break
        except Exception:
            pass
    return handlers

def scan_artifact_dirs() -> list[str]:
    common = ["runs", "episodes", "output", "renders", ".codemap", "docs", "specs/boss_plans"]
    present = []
    for d in common:
        p = ROOT_DIR / d
        if p.exists():
            present.append(d)
    return present

def main():
    print("[*] Running Phase 0 Discovery Survey on AI Video Factory...")
    inventory = {
        "repo_root": str(ROOT_DIR),
        "stage_count": 0,
        "candidate_stages": scan_candidate_stages(),
        "entrypoints": scan_entrypoints(),
        "models": scan_models(),
        "approval_handlers": scan_approval_handlers(),
        "artifact_dirs": scan_artifact_dirs(),
    }
    inventory["stage_count"] = len(inventory["candidate_stages"])

    out_file = ROOT_DIR / ".codemap" / "inventory.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[+] Inventory successfully generated: {out_file}")
    print(f"    - Stages discovered:      {inventory['stage_count']}")
    print(f"    - Entrypoints discovered: {len(inventory['entrypoints'])}")
    print(f"    - Pydantic models:        {len(inventory['models'])}")
    print(f"    - Approval handlers:      {len(inventory['approval_handlers'])}")

if __name__ == "__main__":
    main()
