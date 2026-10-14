#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/codemap/introspect.py — Safe subprocess Pydantic model introspection.

Extracts JSON Schema and field defaults in an isolated subprocess with timeout to prevent side effects.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def introspect_model(
    model_qualname: str,
    repo_root: Optional[Path] = None,
    timeout: int = 15,
) -> Tuple[str, Optional[Dict[str, Any]], Dict[str, Any]]:
    """Imports model_qualname in an isolated subprocess and extracts JSON schema + field defaults.

    Returns:
        status: "RESOLVED" or "UNRESOLVED"
        schema: Dict of JSON schema if resolved, else None
        defaults: Dict of field_name -> default_value
    """
    root_str = str(repo_root.resolve()) if repo_root else str(Path.cwd())

    # Python script executed in subprocess
    script = f"""
import sys, json
sys.path.insert(0, r"{root_str}")

qualname = "{model_qualname}"
parts = qualname.split(".")
mod_name = ".".join(parts[:-1])
cls_name = parts[-1]

try:
    mod = __import__(mod_name, fromlist=[cls_name])
    cls = getattr(mod, cls_name)
    schema = cls.model_json_schema() if hasattr(cls, "model_json_schema") else cls.schema()
    
    # Extract defaults
    defaults = {{}}
    fields = getattr(cls, "model_fields", {{}})
    for fname, f_info in fields.items():
        if f_info.default is not None and str(f_info.default) != "PydanticUndefined":
            try:
                # Test json serializability
                json.dumps(f_info.default)
                defaults[fname] = f_info.default
            except Exception:
                defaults[fname] = str(f_info.default)

    print(json.dumps({{"status": "RESOLVED", "schema": schema, "defaults": defaults}}))
except Exception as e:
    print(json.dumps({{"status": "UNRESOLVED", "error": str(e), "schema": None, "defaults": {{}}}}))
"""

    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=root_str,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            # Find the last JSON line
            for line in reversed(proc.stdout.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    return data.get("status", "UNRESOLVED"), data.get("schema"), data.get("defaults", {})
        return "UNRESOLVED", None, {}
    except Exception:
        return "UNRESOLVED", None, {}
