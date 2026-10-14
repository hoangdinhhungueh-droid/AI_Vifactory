#!/usr/bin/env python3
"""tools/codemap/ast_scanner.py — High-precision Python AST Dependency & Stage Scanner.

Extracts symbols, caller/callee graphs, `@pipeline_stage` declarations, and failure modes.
"""

from __future__ import annotations

import ast
import builtins
import os
from pathlib import Path
from typing import Union

from tools.codemap.schema import FailureMode, SourceRef, Stage, Symbol

BUILTIN_NAMES = set(dir(builtins))

EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "site-packages", "dist", "build",
    "runs", "episodes", "output", "renders", ".agents",
    "tests", "fixtures"
}


def is_path_excluded(path: Path, include_tests: bool = False) -> bool:
    excluded = set(EXCLUDED_PARTS)
    if include_tests:
        excluded.discard("tests")
        excluded.discard("fixtures")
    for part in path.parts:
        if part in excluded or part.startswith(".bak"):
            return True
    return False


class FileAstVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, repo_root: Path):
        self.file_path = file_path
        self.repo_root = repo_root
        self.rel_file = file_path.relative_to(repo_root).as_posix()
        self.mod_qualname = self.rel_file.replace("/", ".").replace(".py", "")

        # Import mapping: alias -> full qualname
        self.imports: dict[str, str] = {}

        self.symbols: list[Symbol] = []
        self.stages: list[Stage] = []
        self.current_class: str | None = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            full_target = f"{mod}.{alias.name}" if mod else alias.name
            self.imports[name] = full_target
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        class_qualname = f"{self.mod_qualname}.{node.name}"
        if prev_class:
            class_qualname = f"{prev_class}.{node.name}"

        line_end = getattr(node, "end_lineno", node.lineno)
        ref = SourceRef(file=self.rel_file, line_start=node.lineno, line_end=line_end)

        decorators = [self._decorator_to_str(d) for d in node.decorator_list]
        self.symbols.append(Symbol(
            qualname=class_qualname,
            kind="class",
            ref=ref,
            decorators=decorators,
            calls=[],
            called_by=[],
            stage_id=None
        ))

        self.current_class = class_qualname
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool):
        kind = "method" if self.current_class else ("async_function" if is_async else "function")
        func_qualname = f"{self.current_class}.{node.name}" if self.current_class else f"{self.mod_qualname}.{node.name}"

        line_end = getattr(node, "end_lineno", node.lineno)
        ref = SourceRef(file=self.rel_file, line_start=node.lineno, line_end=line_end)

        decorators = [self._decorator_to_str(d) for d in node.decorator_list]
        calls = self._collect_calls(node)
        failure_modes = self._collect_failure_modes(node)

        # Check for @pipeline_stage decorator
        stage_decl = self._extract_pipeline_stage(node, func_qualname, ref, failure_modes)
        stage_id = stage_decl.id if stage_decl else None
        if stage_decl:
            self.stages.append(stage_decl)

        self.symbols.append(Symbol(
            qualname=func_qualname,
            kind=kind,
            ref=ref,
            decorators=decorators,
            calls=calls,
            called_by=[],
            stage_id=stage_id
        ))

        # Do not recurse into nested function bodies twice
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(child)

    def _decorator_to_str(self, d: ast.AST) -> str:
        try:
            return ast.unparse(d)
        except Exception:
            return getattr(d, "id", "decorator")

    def _collect_calls(self, fn_node: ast.AST) -> list[str]:
        calls = set()
        for sub in ast.walk(fn_node):
            if isinstance(sub, ast.Call):
                target = self._resolve_call_target(sub.func)
                if target:
                    calls.add(target)
        return sorted(calls)

    def _resolve_call_target(self, func_node: ast.AST) -> str | None:
        if isinstance(func_node, ast.Name):
            name = func_node.id
            if name in BUILTIN_NAMES:
                return name
            if name in self.imports:
                return self.imports[name]
            return f"{self.mod_qualname}.{name}"
        elif isinstance(func_node, ast.Attribute):
            base_str = self._resolve_call_target(func_node.value)
            if base_str:
                return f"{base_str}.{func_node.attr}"
            return f"?{func_node.attr}"
        return None

    def _collect_failure_modes(self, fn_node: ast.AST) -> list[FailureMode]:
        modes = []
        for sub in ast.walk(fn_node):
            if isinstance(sub, ast.Raise):
                exc_name = "Exception"
                if sub.exc:
                    if isinstance(sub.exc, ast.Call):
                        exc_name = self._resolve_call_target(sub.exc.func) or "Exception"
                    elif isinstance(sub.exc, ast.Name):
                        exc_name = sub.exc.id
                    elif isinstance(sub.exc, ast.Attribute):
                        exc_name = sub.exc.attr
                modes.append(FailureMode(
                    exc_type=exc_name,
                    origin="raise",
                    ref=SourceRef(
                        file=self.rel_file,
                        line_start=sub.lineno,
                        line_end=getattr(sub, "end_lineno", sub.lineno)
                    )
                ))
            elif isinstance(sub, ast.ExceptHandler):
                exc_name = "Exception"
                if sub.type:
                    if isinstance(sub.type, ast.Name):
                        exc_name = sub.type.id
                    elif isinstance(sub.type, ast.Attribute):
                        exc_name = sub.type.attr
                modes.append(FailureMode(
                    exc_type=exc_name,
                    origin="except",
                    ref=SourceRef(
                        file=self.rel_file,
                        line_start=sub.lineno,
                        line_end=getattr(sub, "end_lineno", sub.lineno)
                    )
                ))
        return modes

    def _extract_pipeline_stage(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        qualname: str,
        ref: SourceRef,
        failure_modes: list[FailureMode]
    ) -> Stage | None:
        for d in node.decorator_list:
            if isinstance(d, ast.Call):
                name = getattr(d.func, "id", "") or getattr(d.func, "attr", "")
                if name == "pipeline_stage":
                    kwargs = {}
                    for kw in d.keywords:
                        try:
                            val = ast.literal_eval(kw.value)
                            kwargs[kw.arg] = val
                        except Exception:
                            # Might be a dotted model name
                            try:
                                kwargs[kw.arg] = ast.unparse(kw.value)
                            except Exception:
                                kwargs[kw.arg] = str(kw.value)

                    stage_id = kwargs.get("id") or node.name
                    return Stage(
                        id=stage_id,
                        name=kwargs.get("name", stage_id),
                        order=int(kwargs.get("order", 0)),
                        qualname=qualname,
                        ref=ref,
                        input_model=kwargs.get("input_model"),
                        output_model=kwargs.get("output_model"),
                        triggers=kwargs.get("triggers", []),
                        upstream=kwargs.get("upstream", []),
                        downstream=kwargs.get("downstream", []),
                        artifacts=kwargs.get("artifacts", []),
                        failure_modes=failure_modes,
                        verify_cmds=kwargs.get("verify_cmds", [])
                    )
        return None


class CodebaseASTScanner:
    """Scans all Python files across repo and compiles the complete symbol & stage graph."""

    def __init__(self, repo_root: Path, include_tests: bool = False):
        self.repo_root = repo_root.resolve()
        self.include_tests = include_tests
        self.symbols: dict[str, Symbol] = {}
        self.stages: list[Stage] = []

    def scan(self) -> tuple[dict[str, Symbol], list[Stage]]:
        self.symbols.clear()
        self.stages.clear()

        excluded = set(EXCLUDED_PARTS)
        if self.include_tests:
            excluded.discard("tests")
            excluded.discard("fixtures")

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in excluded and not d.startswith(".bak")]
            for file in files:
                if not file.endswith(".py"):
                    continue
                py_file = Path(root) / file
                if is_path_excluded(py_file, include_tests=self.include_tests):
                    continue
                try:
                    tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
                    visitor = FileAstVisitor(py_file, self.repo_root)
                    visitor.visit(tree)

                    for sym in visitor.symbols:
                        self.symbols[sym.qualname] = sym
                    self.stages.extend(visitor.stages)
                except Exception:
                    pass

        # Build fast suffix index
        suffix_index: dict[str, list[str]] = {}
        for qual in self.symbols:
            short_name = qual.split(".")[-1]
            suffix_index.setdefault(short_name, []).append(qual)

        # Invert calls to populate called_by in O(Total Calls)
        for caller_name, sym in self.symbols.items():
            for callee in sym.calls:
                # 1. Exact match
                if callee in self.symbols:
                    if caller_name not in self.symbols[callee].called_by:
                        self.symbols[callee].called_by.append(caller_name)
                else:
                    # 2. Suffix match via index
                    short = callee.split(".")[-1].lstrip("?")
                    for target_qual in suffix_index.get(short, []):
                        if target_qual.endswith(callee) or callee.endswith(short):
                            target_sym = self.symbols[target_qual]
                            if caller_name not in target_sym.called_by:
                                target_sym.called_by.append(caller_name)

        # Propagate stage reachability
        for stage in self.stages:
            self._propagate_stage_reachability(stage.id, stage.qualname)

        return self.symbols, self.stages

    def _propagate_stage_reachability(self, stage_id: str, entry_qualname: str):
        visited: set[str] = set()
        queue = [entry_qualname]

        while queue:
            curr = queue.pop(0)
            if curr in visited or curr not in self.symbols:
                continue
            visited.add(curr)
            sym = self.symbols[curr]
            if not sym.stage_id:
                sym.stage_id = stage_id
            for next_call in sym.calls:
                if next_call in self.symbols and next_call not in visited:
                    queue.append(next_call)
