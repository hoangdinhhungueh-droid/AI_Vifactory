#!/usr/bin/env python3
"""tools/codemap/hashing.py — Canonical JSON serialization, hashing, flattening, and redaction.

Guarantees deterministic bit-for-bit SHA256 hashes across Windows, Linux, and different Python versions.
Prevents sensitive secret leaks in audit snapshots.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

SECRET_KEY_PATTERN = re.compile(r"(api[_-]?key|token|secret|password|authorization|auth_bearer)", re.IGNORECASE)


def serialize_canonical(obj: Any) -> Any:
    """Recursively converts objects to canonical JSON-serializable primitives."""
    if isinstance(obj, BaseModel):
        return serialize_canonical(obj.model_dump(mode="json"))
    if isinstance(obj, dict):
        return {str(k): serialize_canonical(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize_canonical(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj.as_posix() if hasattr(obj, "as_posix") else str(obj))
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, float):
        # Format floats canonically to eliminate platform representation drift
        return round(obj, 8)
    return obj


def canonical_json(obj: Any) -> bytes:
    """Serializes obj into deterministic canonical bytes.
    - Keys sorted alphabetically
    - No whitespace in separators (',', ':')
    - UTF-8 encoded without ascii escaping
    """
    cleaned = serialize_canonical(obj)
    return json.dumps(
        cleaned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_of(obj: Any) -> str:
    """Computes hex SHA256 digest of canonical representation."""
    if isinstance(obj, (bytes, bytearray)):
        return hashlib.sha256(obj).hexdigest()
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flattens a nested dict or list into a flat dict of JSON pointer paths.
    e.g. {'a': [{'b': 1}]} -> {'/a/0/b': 1}
    """
    items: dict[str, Any] = {}
    cleaned = serialize_canonical(obj)

    def _recurse(curr: Any, path: str):
        if isinstance(curr, dict):
            if not curr and path:
                items[path] = {}
            for k, v in sorted(curr.items()):
                _recurse(v, f"{path}/{k}")
        elif isinstance(curr, list):
            if not curr and path:
                items[path] = []
            for idx, item in enumerate(curr):
                _recurse(item, f"{path}/{idx}")
        else:
            items[path] = curr

    _recurse(cleaned, prefix)
    return items


def field_hashes(obj: Any) -> dict[str, str]:
    """Maps every JSON pointer path to the sha256 hash of its value."""
    flat = flatten(obj)
    return {k: sha256_of(v) for k, v in flat.items()}


def redact(obj: Any) -> Any:
    """Recursively redacts sensitive keys matching SECRET_KEY_PATTERN."""
    if isinstance(obj, BaseModel):
        return redact(obj.model_dump(mode="json"))
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            if SECRET_KEY_PATTERN.search(str(k)):
                redacted[k] = "***"
            else:
                redacted[k] = redact(v)
        return redacted
    if isinstance(obj, list):
        return [redact(item) for item in obj]
    return obj
