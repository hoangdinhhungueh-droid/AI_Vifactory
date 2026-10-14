#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/codemap/runtime.py — Zero-cost @pipeline_stage decorator and execution tracer.

Guarantees:
  1. Failsafe: Never crashes pipeline if logging or disk writes fail.
  2. Isolated: When no run_context is active, executes as a plain function with zero overhead.
  3. Redacted: Sensitive tokens are automatically stripped from runtime snapshots.
"""

from __future__ import annotations

import contextvars
import datetime
import functools
import inspect
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from tools.codemap.hashing import canonical_json, field_hashes, redact, sha256_of
from tools.codemap.schema import ArtifactRef, SourceRef, StageEvent

logger = logging.getLogger("codemap.runtime")

_current_run_ctx: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "_current_run_ctx", default=None
)


class run_context:
    """Context manager activating runtime tracing for a pipeline run."""

    def __init__(
        self,
        run_id: str,
        repo_root: Optional[Union[str, Path]] = None,
        approval_refs: Optional[List[str]] = None,
        git_commit: Optional[str] = None,
    ):
        self.run_id = run_id
        self.repo_root = Path(repo_root or Path.cwd()).resolve()
        self.approval_refs = approval_refs or []
        self.git_commit = git_commit
        self.run_dir = self.repo_root / ".codemap" / "runs" / self.run_id
        self.token = None

    def __enter__(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "snapshots").mkdir(parents=True, exist_ok=True)
        ctx_data = {
            "run_id": self.run_id,
            "repo_root": self.repo_root,
            "run_dir": self.run_dir,
            "approval_refs": self.approval_refs,
            "git_commit": self.git_commit,
            "seq": 0,
        }
        self.token = _current_run_ctx.set(ctx_data)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            _current_run_ctx.reset(self.token)


def get_current_run_context() -> Optional[Dict[str, Any]]:
    return _current_run_ctx.get()


def pipeline_stage(
    id: str,
    order: int = 0,
    name: Optional[str] = None,
    input_model: Optional[Any] = None,
    output_model: Optional[Any] = None,
    triggers: Optional[List[str]] = None,
    upstream: Optional[List[str]] = None,
    downstream: Optional[List[str]] = None,
    artifacts: Optional[List[str]] = None,
    verify_cmds: Optional[List[str]] = None,
):
    """Decorator marking a function as a tracked pipeline stage."""

    def decorator(fn: Callable):
        stage_name = name or id
        in_model_name = getattr(input_model, "__name__", str(input_model)) if input_model else None
        out_model_name = getattr(output_model, "__name__", str(output_model)) if output_model else None

        # Inspect source ref once
        try:
            src_file = inspect.getsourcefile(fn) or inspect.getfile(fn)
            lines, start_line = inspect.getsourcelines(fn)
            end_line = start_line + len(lines) - 1
            rel_file = Path(src_file).as_posix()
            source_ref = SourceRef(file=rel_file, line_start=start_line, line_end=end_line)
        except Exception:
            source_ref = SourceRef(file="unknown.py", line_start=1, line_end=1)

        is_async = inspect.iscoroutinefunction(fn)

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            ctx = get_current_run_context()
            if not ctx:
                # Tracing inactive: pass-through plain execution
                return fn(*args, **kwargs)

            return _execute_traced(fn, args, kwargs, ctx, id, source_ref, artifacts)

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            ctx = get_current_run_context()
            if not ctx:
                return await fn(*args, **kwargs)

            return await _execute_traced_async(fn, args, kwargs, ctx, id, source_ref, artifacts)

        wrapped = async_wrapper if is_async else sync_wrapper
        wrapped._is_pipeline_stage = True
        wrapped._stage_id = id
        wrapped._stage_order = order
        return wrapped

    return decorator


def _execute_traced(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    ctx: Dict[str, Any],
    stage_id: str,
    code_ref: SourceRef,
    artifact_patterns: Optional[List[str]],
) -> Any:
    ts_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ctx["seq"] += 1
    seq = ctx["seq"]

    input_payload = {"args": args, "kwargs": kwargs} if (args or kwargs) else {}
    in_hash = sha256_of(input_payload)
    in_field_hashes = field_hashes(input_payload)

    # Save redacted input snapshot
    snapshot_dir = ctx["run_dir"] / "snapshots"
    in_snapshot_file = snapshot_dir / f"{stage_id}.in.json"
    try:
        in_snapshot_file.write_text(
            json.dumps(redact(input_payload), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        in_snapshot_rel = in_snapshot_file.relative_to(ctx["repo_root"]).as_posix()
    except Exception:
        in_snapshot_rel = None

    status = "OK"
    output_result = None
    error_info = None

    try:
        output_result = fn(*args, **kwargs)
        return output_result
    except Exception as exc:
        status = "ERROR"
        error_info = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }
        raise
    finally:
        ts_end = datetime.datetime.now(datetime.timezone.utc).isoformat()
        out_hash = sha256_of(output_result) if output_result is not None else None
        out_field_hashes = field_hashes(output_result) if output_result is not None else {}

        out_snapshot_rel = None
        if output_result is not None:
            out_snapshot_file = snapshot_dir / f"{stage_id}.out.json"
            try:
                out_snapshot_file.write_text(
                    json.dumps(redact(output_result), indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                out_snapshot_rel = out_snapshot_file.relative_to(ctx["repo_root"]).as_posix()
            except Exception:
                pass

        # Scan generated artifacts
        found_artifacts = []
        if artifact_patterns:
            for pat in artifact_patterns:
                resolved_pat = pat.replace("{run_id}", ctx["run_id"])
                for match_p in ctx["repo_root"].glob(resolved_pat):
                    if match_p.is_file():
                        try:
                            rel_art = match_p.relative_to(ctx["repo_root"]).as_posix()
                            file_bytes = match_p.read_bytes()
                            found_artifacts.append(ArtifactRef(
                                path=rel_art,
                                sha256=sha256_of(file_bytes),
                                bytes=len(file_bytes)
                            ))
                        except Exception:
                            pass

        event = StageEvent(
            run_id=ctx["run_id"],
            seq=seq,
            stage_id=stage_id,
            ts_start=ts_start,
            ts_end=ts_end,
            status=status,
            input_hash=in_hash,
            output_hash=out_hash,
            input_field_hashes=in_field_hashes,
            output_field_hashes=out_field_hashes,
            input_snapshot=in_snapshot_rel,
            output_snapshot=out_snapshot_rel,
            artifacts=found_artifacts,
            approval_refs=ctx.get("approval_refs", []),
            error=error_info,
            code_ref=code_ref,
            git_commit=ctx.get("git_commit")
        )

        _record_event_failsafe(ctx["run_dir"], event)


async def _execute_traced_async(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    ctx: Dict[str, Any],
    stage_id: str,
    code_ref: SourceRef,
    artifact_patterns: Optional[List[str]],
) -> Any:
    ts_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ctx["seq"] += 1
    seq = ctx["seq"]

    input_payload = {"args": args, "kwargs": kwargs} if (args or kwargs) else {}
    in_hash = sha256_of(input_payload)
    in_field_hashes = field_hashes(input_payload)

    snapshot_dir = ctx["run_dir"] / "snapshots"
    in_snapshot_file = snapshot_dir / f"{stage_id}.in.json"
    try:
        in_snapshot_file.write_text(
            json.dumps(redact(input_payload), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        in_snapshot_rel = in_snapshot_file.relative_to(ctx["repo_root"]).as_posix()
    except Exception:
        in_snapshot_rel = None

    status = "OK"
    output_result = None
    error_info = None

    try:
        output_result = await fn(*args, **kwargs)
        return output_result
    except Exception as exc:
        status = "ERROR"
        error_info = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }
        raise
    finally:
        ts_end = datetime.datetime.now(datetime.timezone.utc).isoformat()
        out_hash = sha256_of(output_result) if output_result is not None else None
        out_field_hashes = field_hashes(output_result) if output_result is not None else {}

        out_snapshot_rel = None
        if output_result is not None:
            out_snapshot_file = snapshot_dir / f"{stage_id}.out.json"
            try:
                out_snapshot_file.write_text(
                    json.dumps(redact(output_result), indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                out_snapshot_rel = out_snapshot_file.relative_to(ctx["repo_root"]).as_posix()
            except Exception:
                pass

        event = StageEvent(
            run_id=ctx["run_id"],
            seq=seq,
            stage_id=stage_id,
            ts_start=ts_start,
            ts_end=ts_end,
            status=status,
            input_hash=in_hash,
            output_hash=out_hash,
            input_field_hashes=in_field_hashes,
            output_field_hashes=out_field_hashes,
            input_snapshot=in_snapshot_rel,
            output_snapshot=out_snapshot_rel,
            artifacts=[],
            approval_refs=ctx.get("approval_refs", []),
            error=error_info,
            code_ref=code_ref,
            git_commit=ctx.get("git_commit")
        )

        _record_event_failsafe(ctx["run_dir"], event)


def _record_event_failsafe(run_dir: Path, event: StageEvent):
    """Appends event line to events.jsonl with immediate flush."""
    try:
        events_file = run_dir / "events.jsonl"
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
            f.flush()
    except Exception as e:
        logger.warning(f"Could not record trace event for {event.stage_id}: {e}")
