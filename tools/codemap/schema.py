#!/usr/bin/env python3
"""tools/codemap/schema.py — Canonical Pydantic Schemas for Codemap & Traceability.

Governed by extra="forbid" to eliminate contract drift.
Standardizes static code map, runtime event traces, approvals, and lineage reports.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HandoffStatus = Literal["MATCH", "PARTIAL", "MISMATCH", "UNRESOLVED"]


class SourceRef(BaseModel):
    """Pinpoints exact file and lines for rapid IDE navigation."""
    model_config = ConfigDict(extra="forbid")

    file: str = Field(description="Relative path from repository root")
    line_start: int = Field(description="1-based starting line number")
    line_end: int = Field(description="1-based ending line number")


class FailureMode(BaseModel):
    """Identifies exceptions raised or handled in a stage for instant root-cause targeting."""
    model_config = ConfigDict(extra="forbid")

    exc_type: str = Field(description="e.g. ValueError, TimeoutError, GateError")
    origin: Literal["raise", "except", "declared"] = Field(description="How failure mode was detected")
    ref: SourceRef = Field(description="Location of throw/catch")
    note: str | None = Field(default=None, description="Optional diagnostic comment")


class Stage(BaseModel):
    """Static metadata for a pipeline stage node."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable canonical stage key, e.g. s03_script")
    name: str = Field(description="Human readable name")
    order: int = Field(description="Execution sequence order (1-11)")
    qualname: str = Field(description="Fully qualified dotted import path")
    ref: SourceRef = Field(description="Source file line range")
    input_model: str | None = Field(default=None, description="Input Pydantic model qualname")
    output_model: str | None = Field(default=None, description="Output Pydantic model qualname")
    triggers: list[str] = Field(default_factory=list, description="Triggers, e.g. cli:run, approval:script")
    upstream: list[str] = Field(default_factory=list, description="Predecessor stage IDs")
    downstream: list[str] = Field(default_factory=list, description="Successor stage IDs")
    artifacts: list[str] = Field(default_factory=list, description="Artifact paths or glob patterns")
    failure_modes: list[FailureMode] = Field(default_factory=list)
    verify_cmds: list[str] = Field(default_factory=list, description="CLI commands to verify stage execution")


class Symbol(BaseModel):
    """Detailed AST symbol node for caller/callee navigation."""
    model_config = ConfigDict(extra="forbid")

    qualname: str = Field(description="Fully qualified symbol name")
    kind: Literal["function", "method", "class", "async_function"] = Field(description="Symbol type")
    ref: SourceRef = Field(description="Source location")
    decorators: list[str] = Field(default_factory=list, description="Decorators on this symbol")
    calls: list[str] = Field(default_factory=list, description="Functions/classes called by this symbol")
    called_by: list[str] = Field(default_factory=list, description="Symbols calling this symbol")
    stage_id: str | None = Field(default=None, description="Stage to which symbol belongs via reachability")


class FieldIssue(BaseModel):
    """Detailed boundary discrepancy between producer and consumer schemas."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="JSON pointer path, e.g. /scenes/0/duration")
    kind: Literal["missing_in_producer", "type_mismatch", "required_not_provided", "extra_ignored"]
    detail: str = Field(description="Descriptive explanation of the discrepancy")


class Handoff(BaseModel):
    """Boundary contract check between an upstream producer and a downstream consumer."""
    model_config = ConfigDict(extra="forbid")

    from_stage: str = Field(description="Producer stage ID")
    to_stage: str = Field(description="Consumer stage ID")
    producer_model: str | None = Field(default=None, description="Upstream output model qualname")
    consumer_model: str | None = Field(default=None, description="Downstream input model qualname")
    status: HandoffStatus = Field(description="MATCH, PARTIAL, MISMATCH, or UNRESOLVED")
    issues: list[FieldIssue] = Field(default_factory=list, description="List of boundary issues")


class Entrypoint(BaseModel):
    """System entry point for CLI, daemons, watchers, and webhooks."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Identifier, e.g. cli:run_pipeline")
    qualname: str = Field(description="Python entrypoint target")
    ref: SourceRef = Field(description="File and line location")


class CodemapRegistry(BaseModel):
    """Complete, self-contained Code Map GPS Brain (L0 - L2)."""
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    generated_at: str = Field(description="ISO8601 UTC timestamp")
    git_commit: str | None = Field(default=None, description="Git HEAD commit hash")
    source_hash: str = Field(description="SHA256 of all scanned python source files")
    summary: dict[str, Any] = Field(description="L0 high-level summary")
    entrypoints: list[Entrypoint] = Field(default_factory=list)
    stages: list[Stage] = Field(default_factory=list)
    handoffs: list[Handoff] = Field(default_factory=list)
    models: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Qualname -> JSON schema")
    symbols: dict[str, Symbol] = Field(default_factory=dict)


# ==============================================================================
# RUNTIME TRACE & LINEAGE AUDIT MODELS (L3)
# ==============================================================================

class ArtifactRef(BaseModel):
    """Physical artifact generated during a stage execution."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Relative path of artifact on disk")
    sha256: str = Field(description="SHA256 checksum")
    bytes: int = Field(description="File size in bytes")


class StageEvent(BaseModel):
    """Runtime event log entry recorded on each stage execution."""
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(description="Execution run ID")
    seq: int = Field(description="Sequence index within this run")
    stage_id: str = Field(description="Target stage ID")
    ts_start: str = Field(description="ISO8601 start timestamp")
    ts_end: str | None = Field(default=None, description="ISO8601 end timestamp")
    status: Literal["OK", "ERROR", "SKIPPED"] = Field(description="Execution result")
    input_hash: str | None = Field(default=None, description="SHA256 of canonical input JSON")
    output_hash: str | None = Field(default=None, description="SHA256 of canonical output JSON")
    input_field_hashes: dict[str, str] = Field(default_factory=dict, description="Path -> SHA256 of field")
    output_field_hashes: dict[str, str] = Field(default_factory=dict, description="Path -> SHA256 of field")
    input_snapshot: str | None = Field(default=None, description="Path to redacted input snapshot")
    output_snapshot: str | None = Field(default=None, description="Path to redacted output snapshot")
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    approval_refs: list[str] = Field(default_factory=list, description="IDs of approvals applied")
    error: dict[str, Any] | None = Field(default=None, description="Exception details if failed")
    code_ref: SourceRef = Field(description="Source location executed")
    git_commit: str | None = Field(default=None)


class Approval(BaseModel):
    """Audit record when user or agent approves/freezes data at a gate."""
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(description="Unique approval record ID")
    run_id: str = Field(description="Run ID this approval targets")
    target_stage: str = Field(description="Downstream stage that must consume this approval")
    actor: Literal["user", "agent"] = Field(description="Who approved this decision")
    channel: str = Field(description="chat, telegram, ide, or cli")
    ts: str = Field(description="ISO8601 approval timestamp")
    payload_hash: str = Field(description="SHA256 of canonical approved payload")
    field_hashes: dict[str, str] = Field(default_factory=dict, description="Path -> SHA256 per field")
    payload_snapshot: str = Field(description="Path to redacted snapshot file on disk")


class FieldVerdict(BaseModel):
    """Field-level verification result comparing approved vs consumed data."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="JSON pointer path to field")
    verdict: Literal["CARRIED", "MODIFIED", "DROPPED", "DEFAULTED", "ADDED"] = Field(
        description="Lineage status for this field"
    )
    approved_hash: str | None = Field(default=None)
    consumed_hash: str | None = Field(default=None)
    note: str | None = Field(default=None)


class LineageReport(BaseModel):
    """Forensic report verifying whether user approvals actually reached execution."""
    model_config = ConfigDict(extra="forbid")

    run_id: str
    approval_id: str
    target_stage: str
    overall: Literal["INTACT", "DRIFT", "NOT_CONSUMED"]
    fields: list[FieldVerdict] = Field(default_factory=list)
