#!/usr/bin/env python3
"""tools/codemap/builder.py — Master Codemap Registry Builder and Stale Checker.

Compiles L0-L2 into .codemap/codemap.json.
Provides `build_codemap()` and `check_codemap()`.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tools.codemap.ast_scanner import EXCLUDED_PARTS, CodebaseASTScanner
from tools.codemap.handoff import analyze_handoff
from tools.codemap.introspect import introspect_model
from tools.codemap.schema import (
    CodemapRegistry,
    Entrypoint,
    Handoff,
)


def compute_source_hash(repo_root: Path) -> str:
    """Computes a deterministic SHA256 hash of all scanned Python source files."""
    hasher = hashlib.sha256()
    py_files = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_PARTS and not d.startswith(".bak")]
        for file in files:
            if file.endswith(".py"):
                py_files.append(Path(root) / file)

    for p in sorted(py_files):
        try:
            rel = p.relative_to(repo_root).as_posix()
            hasher.update(rel.encode("utf-8"))
            hasher.update(p.read_bytes())
        except Exception:
            pass

    return hasher.hexdigest()


def get_git_commit(repo_root: Path) -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def build_codemap(repo_root: Path | None = None, output_file: Path | None = None) -> CodemapRegistry:
    root = (repo_root or Path.cwd()).resolve()
    target_json = output_file or (root / ".codemap" / "codemap.json")
    target_json.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Building Code Map GPS Brain for: {root}")
    scanner = CodebaseASTScanner(root)
    symbols, stages = scanner.scan()

    # Sort stages by order
    stages = sorted(stages, key=lambda s: s.order)

    # Introspect models
    model_schemas: dict[str, dict[str, Any]] = {}
    model_defaults: dict[str, dict[str, Any]] = {}

    models_to_fetch = set()
    for s in stages:
        if s.input_model:
            models_to_fetch.add(s.input_model)
        if s.output_model:
            models_to_fetch.add(s.output_model)

    for m_qual in sorted(models_to_fetch):
        status, schema, defaults = introspect_model(m_qual, root)
        if schema:
            model_schemas[m_qual] = schema
        if defaults:
            model_defaults[m_qual] = defaults

    # Analyze Handoffs
    stage_by_id = {s.id: s for s in stages}
    handoffs: list[Handoff] = []

    for s in stages:
        for ds_id in s.downstream:
            if ds_id in stage_by_id:
                consumer = stage_by_id[ds_id]
                prod_schema = model_schemas.get(s.output_model) if s.output_model else None
                cons_schema = model_schemas.get(consumer.input_model) if consumer.input_model else None
                h = analyze_handoff(
                    from_stage=s.id,
                    to_stage=consumer.id,
                    producer_model=s.output_model,
                    consumer_model=consumer.input_model,
                    producer_schema=prod_schema,
                    consumer_schema=cons_schema,
                )
                handoffs.append(h)

    # Scan entrypoints
    entrypoints: list[Entrypoint] = []
    for s_qual, sym in symbols.items():
        if "main" in sym.qualname.lower() or "cli" in sym.qualname.lower():
            if sym.kind in ("function", "async_function"):
                entrypoints.append(Entrypoint(
                    name=sym.qualname.split(".")[-1],
                    qualname=sym.qualname,
                    ref=sym.ref
                ))

    # Source hash
    source_hash = compute_source_hash(root)
    git_head = get_git_commit(root)
    generated_at = datetime.datetime.now(datetime.UTC).isoformat()

    mismatches = sum(1 for h in handoffs if h.status == "MISMATCH")
    summary = {
        "total_stages": len(stages),
        "total_symbols": len(symbols),
        "total_handoffs": len(handoffs),
        "mismatches": mismatches,
        "entrypoints_count": len(entrypoints),
        "status": "PASS" if mismatches == 0 else "FAIL",
    }

    # Filter symbols to canonical pipeline modules & reachable symbols to keep under 300KB
    canonical_prefixes = ("stages/", "orchestrator/", "core/", "tools/codemap/")
    filtered_symbols = {
        qual: sym for qual, sym in symbols.items()
        if sym.stage_id is not None or sym.ref.file.startswith(canonical_prefixes)
    }

    registry = CodemapRegistry(
        schema_version="1.0",
        generated_at=generated_at,
        git_commit=git_head,
        source_hash=source_hash,
        summary=summary,
        entrypoints=entrypoints[:20],
        stages=stages,
        handoffs=handoffs,
        models=model_schemas,
        symbols=filtered_symbols,
    )

    # Save to disk with indent=1
    target_json.write_text(registry.model_dump_json(indent=1), encoding="utf-8")
    size_kb = target_json.stat().st_size / 1024
    print(f"[+] Codemap successfully written to: {target_json} ({size_kb:.1f} KB)")
    print(f"    - Stages: {len(stages)} | Handoffs: {len(handoffs)} (MISMATCH: {mismatches})")
    return registry


def check_codemap(repo_root: Path | None = None, codemap_file: Path | None = None) -> tuple[int, str]:
    """Validates freshness of codemap against current disk state."""
    root = (repo_root or Path.cwd()).resolve()
    target_json = codemap_file or (root / ".codemap" / "codemap.json")

    if not target_json.exists():
        return 1, f"Codemap file not found at {target_json}. Run build first."

    try:
        raw = json.loads(target_json.read_text(encoding="utf-8"))
        registry = CodemapRegistry.model_validate(raw)
    except Exception as e:
        return 1, f"Failed to validate {target_json}: {e}"

    # 1. Freshness check
    current_source_hash = compute_source_hash(root)
    if current_source_hash != registry.source_hash:
        return 1, (
            "STALE: Python source code modified since last codemap build.\n"
            f"Stored Hash:  {registry.source_hash}\n"
            f"Current Hash: {current_source_hash}\n"
            "Action required: Run 'python -m tools.codemap build' to regenerate."
        )

    # 2. Handoff mismatch check
    mismatches = [h for h in registry.handoffs if h.status == "MISMATCH"]
    if mismatches:
        err_lines = [f"MISMATCH in {len(mismatches)} handoff boundaries:"]
        for m in mismatches:
            err_lines.append(f"  - [{m.from_stage} -> {m.to_stage}]")
            for iss in m.issues:
                err_lines.append(f"      * {iss.path}: {iss.detail}")
        return 1, "\n".join(err_lines)

    return 0, f"CLEAN: Codemap is fresh ({len(registry.stages)} stages) and 0 mismatches."
