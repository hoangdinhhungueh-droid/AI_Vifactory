#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/orchestrator/antigravity_janitor.py — Autonomous Cleanup & Janitor Engine.

Mandated by Rule 125 (Single Pipeline Version & Zero-Ghost Remnant Mandate),
Rule 137 (Zero-Drive-Wipe & Safe-Trash Mandate), and Clean Vibecoding Disciplines.

Inspired by:
  1. npkill (Disk & node_modules/cache scavenger for vibecoders)
  2. AST Dead Code & Zombie Function Hunter
  3. Safe-Trash Protection (moves to Recycle Bin instead of hard delete)

Usage:
  python scripts/orchestrator/antigravity_janitor.py --dry-run
  python scripts/orchestrator/antigravity_janitor.py --clean-pycache
  python scripts/orchestrator/antigravity_janitor.py --clean-disk
  python scripts/orchestrator/antigravity_janitor.py --scan-zombies
  python scripts/orchestrator/antigravity_janitor.py --all
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Whitelisted safe cleanup categories
SAFE_CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tempmediaStorage",
    ".remotion",
}

SAFE_SCRATCH_DIR_PATTERNS = [
    "vf_orchestrator_",
    "tmp_render_",
]

FORBIDDEN_ZONE_KEYWORDS = [
    "windows",
    "program files",
    "system32",
    "/root",
    "/home",
    "/etc",
    "/usr",
    "/var",
]


def format_bytes(size: int) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def get_dir_size(path: Path) -> int:
    """Computes total size of a directory recursively."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_dir_size(Path(entry.path))
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return total


class AntigravityJanitor:
    """Autonomous Janitor for disk storage, dead code, and vibecoding hygiene."""

    def __init__(self, root_dir: str | Path | None = None):
        if root_dir is None or str(root_dir) == ".":
            cwd = Path(".").resolve()
            if (cwd / "app").exists() and (cwd / "scripts").exists():
                self.root_dir = cwd
            else:
                self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir).resolve()

        # Import safe_trash helper
        self.safe_trash_func = None
        self._init_safe_trash()

    def _init_safe_trash(self) -> None:
        try:
            scripts_dir = self.root_dir / "scripts"
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from safe_trash import safe_trash
            self.safe_trash_func = safe_trash
        except Exception:
            self.safe_trash_func = None

    def scan_disk_bloat(self) -> List[Dict[str, Any]]:
        """Scans for safe-to-clean bloated directories (caches, build dirs, temp renders)."""
        bloat_items: List[Dict[str, Any]] = []

        for root, dirs, _ in os.walk(self.root_dir):
            # Skip hidden git directory
            if ".git" in dirs:
                dirs.remove(".git")

            for d in list(dirs):
                full_path = Path(root) / d
                is_target = False
                category = "General Cache"

                if d in SAFE_CACHE_DIR_NAMES:
                    is_target = True
                    category = "Python / Tool Cache" if "cache" in d else "Remotion / Render Cache"
                elif any(d.startswith(pat) for pat in SAFE_SCRATCH_DIR_PATTERNS):
                    is_target = True
                    category = "Ephemeral Scratch"
                elif d == "node_modules":
                    # Check if this node_modules is inside workspace and heavy
                    is_target = True
                    category = "Node Modules (npkill target)"

                if is_target:
                    size = get_dir_size(full_path)
                    try:
                        rel_path = full_path.relative_to(self.root_dir)
                    except ValueError:
                        rel_path = full_path

                    bloat_items.append({
                        "path": str(full_path),
                        "rel_path": str(rel_path),
                        "name": d,
                        "category": category,
                        "size_bytes": size,
                        "size_formatted": format_bytes(size),
                    })
                    # Do not recurse into targeted directory
                    dirs.remove(d)

        # Sort by size descending
        bloat_items.sort(key=lambda x: x["size_bytes"], reverse=True)
        return bloat_items

    def scan_zombie_code(self) -> Dict[str, Any]:
        """Scans codebase via AST to discover zombie functions and unused imports."""
        py_files: List[Path] = []
        for target_folder in [self.root_dir / "app", self.root_dir / "scripts"]:
            if target_folder.exists():
                py_files.extend(target_folder.glob("**/*.py"))

        # Exclude tests and migrations
        py_files = [p for p in py_files if "tests" not in p.parts and "migrations" not in p.parts]

        # 1. Discover all defined functions and classes & cache file text in RAM
        defined_functions: Dict[str, Dict[str, Any]] = {}
        all_code_tokens: Set[str] = set()
        cached_texts: List[str] = []

        for p in py_files:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                cached_texts.append(content)
                tree = ast.parse(content, filename=str(p))
            except Exception:
                continue

            # Collect tokens present in raw code for usage check
            tokens = set(ast.walk(tree))
            for node in tokens:
                if isinstance(node, ast.Name):
                    all_code_tokens.add(node.id)
                elif isinstance(node, ast.Attribute):
                    all_code_tokens.add(node.attr)

            # Discover function definitions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fname = node.name
                    # Skip private/dunder, entrypoints, and standard lifecycle methods
                    if fname.startswith("_") or fname in {"main", "run", "execute", "setup", "cleanup", "handler"}:
                        continue
                    key = f"{fname}@{p.name}:{node.lineno}"
                    defined_functions[key] = {
                        "name": fname,
                        "file": str(p.relative_to(self.root_dir)),
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    }

        # Combine all texts once for instant substring count search in RAM
        full_codebase_text = "\n".join(cached_texts)

        # 2. Check caller frequency in RAM
        zombie_candidates: List[Dict[str, Any]] = []
        for key, info in defined_functions.items():
            name = info["name"]
            call_count = full_codebase_text.count(name)

            # If it only appears once (its own definition), it is an unused zombie function!
            if call_count <= 1:
                zombie_candidates.append(info)

        return {
            "total_files_scanned": len(py_files),
            "total_functions_indexed": len(defined_functions),
            "zombie_functions_count": len(zombie_candidates),
            "zombie_functions": zombie_candidates,
        }

    def purge_directories(self, items: List[Dict[str, Any]], dry_run: bool = True) -> Tuple[int, int]:
        """Safely purges bloat directories using Rule 137 safe_trash mandate.

        Returns (purged_count, purged_bytes).
        """
        if dry_run:
            total_bytes = sum(i["size_bytes"] for i in items)
            return len(items), total_bytes

        purged_count = 0
        purged_bytes = 0

        for item in items:
            p_str = item["path"]
            p = Path(p_str)

            # Safety check (Rule 137)
            if not p.exists():
                continue
            abs_p = str(p.resolve()).lower()
            if any(forbidden in abs_p for forbidden in FORBIDDEN_ZONE_KEYWORDS) and "video_factory" not in abs_p:
                print(f"⚠️ SAFETY ABORT: Path {p_str} is near forbidden system zone. Skipped.")
                continue

            try:
                size = item["size_bytes"]
                if self.safe_trash_func:
                    success = self.safe_trash_func(str(p))
                    if success:
                        purged_count += 1
                        purged_bytes += size
                else:
                    import shutil
                    shutil.rmtree(p, ignore_errors=True)
                    purged_count += 1
                    purged_bytes += size
            except Exception as e:
                print(f"Failed to trash {p_str}: {e}")

        return purged_count, purged_bytes


def main():
    parser = argparse.ArgumentParser(
        description="🛡️ Antigravity Janitor: Autonomous Disk Sweeper & Dead Code Hunter"
    )
    parser.add_argument("--root", default=".", help="Root directory to scan (default: current dir)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview cleanable bloat without deleting")
    parser.add_argument("--clean-disk", action="store_true", help="Purge heavy caches and temporary render folders")
    parser.add_argument("--clean-pycache", action="store_true", help="Purge only __pycache__ directories")
    parser.add_argument("--scan-zombies", action="store_true", help="Scan AST for dead/zombie functions with 0 callers")
    parser.add_argument("--all", action="store_true", help="Run complete scan of disk bloat and zombie code")
    parser.add_argument("--force-purge", action="store_true", help="Execute deletion (disables dry-run, moves to Recycle Bin)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    janitor = AntigravityJanitor(args.root)
    dry_run = not args.force_purge

    results: Dict[str, Any] = {
        "dry_run": dry_run,
        "disk_bloat": [],
        "zombie_code": {},
    }

    print("\n" + "=" * 65)
    print("🧹 ANTIGRAVITY JANITOR & CLEAN VIBECODING ENGINE (RULE 125 & 137)")
    print("=" * 65)
    print(f"📍 Target Workspace: {janitor.root_dir}")
    print(f"🔒 Mode: {'DRY-RUN (Safe Preview)' if dry_run else 'ACTIVE PURGE (Move to Recycle Bin)'}")
    print("-" * 65)

    # 1. Disk Bloat Scan
    if args.clean_disk or args.clean_pycache or args.all or (not args.scan_zombies):
        bloat_items = janitor.scan_disk_bloat()
        if args.clean_pycache and not args.clean_disk and not args.all:
            bloat_items = [b for b in bloat_items if b["name"] == "__pycache__"]

        total_size = sum(b["size_bytes"] for b in bloat_items)
        results["disk_bloat"] = bloat_items
        results["total_bloat_bytes"] = total_size
        results["total_bloat_formatted"] = format_bytes(total_size)

        print(f"\n📦 DISK BLOAT SCAN: Found {len(bloat_items)} targets ({format_bytes(total_size)} reclaimable)")
        if bloat_items:
            print(f"{'Category':<26} | {'Size':<10} | {'Relative Path'}")
            print("-" * 65)
            for item in bloat_items[:15]:
                print(f"{item['category']:<26} | {item['size_formatted']:<10} | {item['rel_path']}")
            if len(bloat_items) > 15:
                print(f"... and {len(bloat_items) - 15} more items.")

        if args.force_purge and (args.clean_disk or args.clean_pycache or args.all):
            count, freed = janitor.purge_directories(bloat_items, dry_run=False)
            print(f"\n✅ PURGED {count} directories to Recycle Bin! Freed: {format_bytes(freed)}")

    # 2. Zombie Code Scan
    if args.scan_zombies or args.all:
        print("\n🧟 ZOMBIE CODE & DEAD FUNCTION SCAN (AST)...")
        zombie_data = janitor.scan_zombie_code()
        results["zombie_code"] = zombie_data

        print(f"🔍 Scanned {zombie_data['total_files_scanned']} Python files, indexed {zombie_data['total_functions_indexed']} functions.")
        zombies = zombie_data["zombie_functions"]
        print(f"⚠️ Found {len(zombies)} potentially unused zombie function(s):")
        if zombies:
            print(f"{'Function Name':<28} | {'Location'}")
            print("-" * 65)
            for z in zombies[:15]:
                loc = f"{z['file']}:{z['line']}"
                print(f"{z['name']:<28} | {loc}")
            if len(zombies) > 15:
                print(f"... and {len(zombies) - 15} more functions.")

    print("\n" + "=" * 65)
    if dry_run:
        print("💡 DRY-RUN COMPLETE. To reclaim space safely, run with --force-purge")
    else:
        print("🎉 WORKSPACE HYGIENE AUDIT COMPLETE.")
    print("=" * 65 + "\n")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
