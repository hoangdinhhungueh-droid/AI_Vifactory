#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_remotion_props_parity.py — Exact Parity Test between Pydantic and Remotion JSON Schema (Rule 134)."""

import json
from pathlib import Path
from core.contracts.render_props import RemotionRenderProps


def test_remotion_props_schema_exact_parity():
    """Validates that Remotion TypeScript schema file on disk exactly matches Pydantic schema."""
    schema_path = Path(__file__).resolve().parent.parent / "remotion" / "src" / "generated" / "render-props.schema.json"
    assert schema_path.exists(), f"Missing generated schema file at: {schema_path}"

    disk_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    pydantic_schema = RemotionRenderProps.model_json_schema()

    # Compare core structural keys
    assert disk_schema.get("title") == pydantic_schema.get("title")
    assert disk_schema.get("type") == pydantic_schema.get("type")
    
    disk_props = disk_schema.get("properties", {})
    pydantic_props = pydantic_schema.get("properties", {})
    
    assert set(disk_props.keys()) == set(pydantic_props.keys()), (
        f"Parity mismatch: Disk keys {set(disk_props.keys())} != Pydantic keys {set(pydantic_props.keys())}"
    )

    # Validate required fields exact match
    disk_required = set(disk_schema.get("required", []))
    pydantic_required = set(pydantic_schema.get("required", []))
    assert disk_required == pydantic_required, (
        f"Required fields mismatch: {disk_required} != {pydantic_required}"
    )
