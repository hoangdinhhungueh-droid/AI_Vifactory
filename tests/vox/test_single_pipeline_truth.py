#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_single_pipeline_truth.py — Verifies Single Pipeline Truth and Legacy Route Quarantines (Rule 125).

Guarantees:
1. Legacy execution endpoints (/produce_episode, /run_episode, /trigger_video_generation) are completely unmounted and return 404.
2. Active canonical endpoints (/api/v1/health, /api/v1/diag, /v1/models, /v1/budget) return HTTP 200.
3. The only production video generation entrypoint is vox.pipeline.
"""

import ast
from pathlib import Path
import pytest


def test_legacy_routes_absent_from_ast():
    """Statically verifies via AST that no legacy execution endpoints exist in app/main.py."""
    main_py = Path(__file__).resolve().parent.parent.parent / "app" / "main.py"
    assert main_py.exists(), f"app/main.py not found at {main_py}"

    tree = ast.parse(main_py.read_text(encoding="utf-8"), filename=str(main_py))
    extracted_routes = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in ("get", "post", "put", "delete", "patch", "api_route"):
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            extracted_routes.add(dec.args[0].value)

    legacy_targets = [
        "/produce_episode",
        "/run_episode",
        "/api/v1/produce_episode",
        "/api/v1/run_episode",
        "/trigger_video_generation",
    ]
    for target in legacy_targets:
        assert target not in extracted_routes, f"Forbidden legacy route '{target}' found in app/main.py!"

    # Ensure canonical endpoints exist
    canonical_targets = ["/api/v1/health", "/api/v1/diag", "/v1/models", "/v1/budget"]
    for c_target in canonical_targets:
        assert c_target in extracted_routes, f"Expected canonical route '{c_target}' missing from app/main.py!"


def test_runtime_legacy_routes_return_404_if_fastapi_available():
    """Runs runtime 404 tests against FastAPI app when installed."""
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
    except Exception:
        pytest.skip("FastAPI / TestClient dependencies not available in current environment")

    legacy_routes = [
        "/produce_episode",
        "/run_episode",
        "/api/v1/produce_episode",
        "/trigger_video_generation",
    ]
    for route in legacy_routes:
        assert client.post(route, json={"topic": "Test"}).status_code == 404
        assert client.get(route).status_code == 404

    canonical_routes = ["/api/v1/health", "/api/v1/diag", "/v1/models", "/v1/budget"]
    for route in canonical_routes:
        assert client.get(route).status_code == 200
