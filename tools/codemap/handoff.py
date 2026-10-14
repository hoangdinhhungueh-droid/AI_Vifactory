#!/usr/bin/env python3
"""tools/codemap/handoff.py — Inter-stage handoff boundary contract validation.

Compares upstream producer output schema vs downstream consumer input schema.
Eliminates contract drift and boundary blindness.
"""

from __future__ import annotations

from typing import Any

from tools.codemap.schema import FieldIssue, Handoff, HandoffStatus


def analyze_handoff(
    from_stage: str,
    to_stage: str,
    producer_model: str | None,
    consumer_model: str | None,
    producer_schema: dict[str, Any] | None,
    consumer_schema: dict[str, Any] | None,
) -> Handoff:
    """Validates contract compatibility between producer output and consumer input."""

    if not producer_schema or not consumer_schema:
        status: HandoffStatus = "UNRESOLVED"
        issues = []
        if not producer_schema and producer_model:
            issues.append(FieldIssue(
                path="/",
                kind="missing_in_producer",
                detail=f"Producer model '{producer_model}' schema could not be resolved"
            ))
        if not consumer_schema and consumer_model:
            issues.append(FieldIssue(
                path="/",
                kind="required_not_provided",
                detail=f"Consumer model '{consumer_model}' schema could not be resolved"
            ))
        return Handoff(
            from_stage=from_stage,
            to_stage=to_stage,
            producer_model=producer_model,
            consumer_model=consumer_model,
            status=status,
            issues=issues
        )

    issues: list[FieldIssue] = []

    prod_props = producer_schema.get("properties", {})
    cons_props = consumer_schema.get("properties", {})
    cons_required = set(consumer_schema.get("required", []))

    # 1. Check consumer required fields
    for req_field in sorted(cons_required):
        if req_field not in prod_props:
            issues.append(FieldIssue(
                path=f"/{req_field}",
                kind="required_not_provided",
                detail=f"Required field '{req_field}' in consumer '{to_stage}' is not provided by producer '{from_stage}'"
            ))

    # 2. Check type compatibility on common fields
    for fname, c_spec in cons_props.items():
        if fname in prod_props:
            p_spec = prod_props[fname]
            p_type = p_spec.get("type")
            c_type = c_spec.get("type")
            if p_type and c_type and p_type != c_type:
                # Permit integer to number promotion
                if not (p_type == "integer" and c_type == "number"):
                    issues.append(FieldIssue(
                        path=f"/{fname}",
                        kind="type_mismatch",
                        detail=f"Field '{fname}' type mismatch: producer has '{p_type}', consumer expects '{c_type}'"
                    ))

    # 3. Check extra fields in producer ignored by consumer
    for p_fname in sorted(prod_props.keys()):
        if p_fname not in cons_props:
            issues.append(FieldIssue(
                path=f"/{p_fname}",
                kind="extra_ignored",
                detail=f"Field '{p_fname}' produced by '{from_stage}' is ignored by '{to_stage}'"
            ))

    # Determine overall status
    has_breaking = any(i.kind in ("required_not_provided", "type_mismatch") for i in issues)
    has_extra = any(i.kind == "extra_ignored" for i in issues)

    if has_breaking:
        status = "MISMATCH"
    elif has_extra:
        status = "PARTIAL"
    else:
        status = "MATCH"

    return Handoff(
        from_stage=from_stage,
        to_stage=to_stage,
        producer_model=producer_model,
        consumer_model=consumer_model,
        status=status,
        issues=issues
    )
