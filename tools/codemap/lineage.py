#!/usr/bin/env python3
"""tools/codemap/lineage.py — Forensic Approval Lineage Audit Engine.

Evaluates field-level verdicts (CARRIED, MODIFIED, DROPPED, DEFAULTED, ADDED, NOT_CONSUMED)
to detect data drift, silent bypasses, and accidental default-value overwrites.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.codemap.hashing import sha256_of
from tools.codemap.schema import Approval, FieldVerdict, LineageReport, StageEvent


def compute_lineage_report(
    run_id: str,
    approval_id: str | None = None,
    repo_root: Path | None = None,
    model_defaults: dict[str, dict[str, Any]] | None = None,
) -> list[LineageReport]:
    """Generates forensic lineage reports comparing approved payloads vs consumed inputs."""
    root = (repo_root or Path.cwd()).resolve()
    run_dir = root / ".codemap" / "runs" / run_id
    if not run_dir.exists():
        return []

    approvals_file = run_dir / "approvals.jsonl"
    events_file = run_dir / "events.jsonl"

    if not approvals_file.exists():
        return []

    # Read approvals
    approvals: list[Approval] = []
    for line in approvals_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                approvals.append(Approval.model_validate_json(line))
            except Exception:
                pass

    # Read events
    events: list[StageEvent] = []
    if events_file.exists():
        for line in events_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    events.append(StageEvent.model_validate_json(line))
                except Exception:
                    pass

    reports: list[LineageReport] = []

    for appr in approvals:
        if approval_id and appr.approval_id != approval_id:
            continue

        # Find event for target_stage that referenced this approval
        matched_event: StageEvent | None = None
        for ev in events:
            if ev.stage_id == appr.target_stage and appr.approval_id in ev.approval_refs:
                matched_event = ev
                break

        # Fallback: find any event for target stage
        if not matched_event:
            for ev in events:
                if ev.stage_id == appr.target_stage:
                    matched_event = ev
                    break

        if not matched_event:
            reports.append(LineageReport(
                run_id=run_id,
                approval_id=appr.approval_id,
                target_stage=appr.target_stage,
                overall="NOT_CONSUMED",
                fields=[
                    FieldVerdict(
                        path="/",
                        verdict="DROPPED",
                        approved_hash=appr.payload_hash,
                        consumed_hash=None,
                        note=f"Target stage '{appr.target_stage}' never executed or never consumed approval '{appr.approval_id}'"
                    )
                ]
            ))
            continue

        # Check if approval_id was actually referenced
        if appr.approval_id not in matched_event.approval_refs:
            reports.append(LineageReport(
                run_id=run_id,
                approval_id=appr.approval_id,
                target_stage=appr.target_stage,
                overall="NOT_CONSUMED",
                fields=[
                    FieldVerdict(
                        path="/",
                        verdict="DROPPED",
                        approved_hash=appr.payload_hash,
                        consumed_hash=None,
                        note=f"Target stage '{appr.target_stage}' executed but bypassed approval '{appr.approval_id}'"
                    )
                ]
            ))
            continue

        # Read actual consumed input snapshot if available
        if matched_event.input_snapshot:
            snap_path = root / matched_event.input_snapshot
            if snap_path.exists():
                try:
                    json.loads(snap_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

        # Normalize consumed paths if wrapped in args/kwargs
        def _norm_path(p: str) -> str:
            for prefix in ("/args/0/", "/kwargs/payload/", "/kwargs/request/", "/kwargs/data/", "/kwargs/req/"):
                if p.startswith(prefix):
                    return "/" + p[len(prefix):]
            if p == "/args/0":
                return "/"
            return p

        norm_consumed_fields = {_norm_path(k): v for k, v in matched_event.input_field_hashes.items()}

        # Compare field by field
        field_verdicts: list[FieldVerdict] = []
        appr_fields = appr.field_hashes
        consumed_fields = norm_consumed_fields

        all_paths = sorted(set(appr_fields.keys()) | set(consumed_fields.keys()))

        for p in all_paths:
            in_appr = p in appr_fields
            in_cons = p in consumed_fields

            h_appr = appr_fields.get(p)
            h_cons = consumed_fields.get(p)

            if in_appr and not in_cons:
                field_verdicts.append(FieldVerdict(
                    path=p,
                    verdict="DROPPED",
                    approved_hash=h_appr,
                    consumed_hash=None,
                    note="Field was present in approval decision but completely dropped from consumed input"
                ))
            elif not in_appr and in_cons:
                field_verdicts.append(FieldVerdict(
                    path=p,
                    verdict="ADDED",
                    approved_hash=None,
                    consumed_hash=h_cons,
                    note="Field was introduced into input without explicit approval"
                ))
            else:
                # Both present
                if h_appr == h_cons:
                    field_verdicts.append(FieldVerdict(
                        path=p,
                        verdict="CARRIED",
                        approved_hash=h_appr,
                        consumed_hash=h_cons,
                        note="Field hash bit-for-bit match"
                    ))
                else:
                    # Check if it was overwritten by a known default value
                    is_defaulted = False
                    short_name = p.split("/")[-1]
                    if model_defaults:
                        for m_name, d_dict in model_defaults.items():
                            if short_name in d_dict:
                                expected_def_hash = sha256_of(d_dict[short_name])
                                if h_cons == expected_def_hash:
                                    is_defaulted = True
                                    break

                    if is_defaulted:
                        field_verdicts.append(FieldVerdict(
                            path=p,
                            verdict="DEFAULTED",
                            approved_hash=h_appr,
                            consumed_hash=h_cons,
                            note=f"Field '{p}' was overwritten by the schema default value instead of approved value"
                        ))
                    else:
                        field_verdicts.append(FieldVerdict(
                            path=p,
                            verdict="MODIFIED",
                            approved_hash=h_appr,
                            consumed_hash=h_cons,
                            note="Field value changed between approval and actual consumption"
                        ))

        # Overall verdict
        has_drift = any(fv.verdict in ("MODIFIED", "DROPPED", "DEFAULTED") for fv in field_verdicts)
        overall = "DRIFT" if has_drift else "INTACT"

        reports.append(LineageReport(
            run_id=run_id,
            approval_id=appr.approval_id,
            target_stage=appr.target_stage,
            overall=overall,
            fields=field_verdicts
        ))

    return reports
