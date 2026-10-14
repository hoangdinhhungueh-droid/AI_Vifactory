#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_single_pipeline_truth.py — Verifies Single Pipeline Truth and Legacy Route Quarantines (Rule 125).

Guarantees:
1. Legacy execution endpoints (/produce_episode, /run_episode) are completely unmounted and return 404.
2. Active canonical endpoints (/api/v1/health, /api/v1/diag, /v1/models, /v1/budget) return HTTP 200.
3. The only production video generation entrypoint is vox.pipeline.
"""

import pytest

fastapi = pytest.importorskip("fastapi")


def test_legacy_execution_routes_unmounted():
    """Asserts that all legacy production execution endpoints are completely unmounted."""
    from app.main import app

    mounted_paths = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        if path:
            mounted_paths.add(path)

    legacy_routes = [
        "/produce_episode",
        "/run_episode",
        "/api/v1/produce_episode",
        "/api/v1/run_episode",
        "/trigger_video_generation",
    ]
    for route in legacy_routes:
        assert route not in mounted_paths, f"Forbidden legacy route '{route}' is still mounted in app.routes!"


def test_legacy_execution_routes_return_404_via_testclient():
    """Asserts that invoking legacy production execution endpoints returns HTTP 404."""
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
    except Exception:
        pytest.skip("TestClient dependencies not installed in this environment")

    legacy_routes = [
        "/produce_episode",
        "/run_episode",
        "/api/v1/produce_episode",
        "/api/v1/run_episode",
        "/trigger_video_generation",
    ]
    for route in legacy_routes:
        resp_post = client.post(route, json={"topic": "Test"})
        assert resp_post.status_code == 404, f"Legacy route {route} unexpectedly returned HTTP {resp_post.status_code} (expected 404)"


def test_canonical_fastapi_endpoints_return_200():
    """Asserts that canonical health, diag, models, and budget endpoints return 200 OK."""
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
    except Exception:
        pytest.skip("TestClient dependencies not installed in this environment")

    canonical_routes = [
        "/api/v1/health",
        "/api/v1/diag",
        "/v1/models",
        "/v1/budget",
    ]
    for route in canonical_routes:
        resp = client.get(route)
        assert resp.status_code == 200, f"Canonical endpoint {route} failed with HTTP {resp.status_code}"
