#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_api_auth_gating.py
Unit tests verifying auth gating on sensitive endpoints (/api/v1/s1-score, /api/v1/pipeline/run,
/api/v1/trend-commit, /api/v1/trend-virality) using timing-safe hmac.compare_digest and verifying
that 'testclient' is rejected when unauthenticated (Boss Item 11).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setenv("VF_API_TOKEN", "test_secret_token_12345")
    monkeypatch.delenv("VF_ALLOW_UNAUTH_LOOPBACK", raising=False)
    monkeypatch.delenv("ALLOW_UNAUTHENTICATED_LOOPBACK", raising=False)
    return TestClient(app)


def test_unauthenticated_request_rejected_401(auth_client):
    """Endpoints must fail-closed with 401 Unauthorized when missing Bearer token."""
    # /api/v1/trend-virality
    resp_virality = auth_client.post("/api/v1/trend-virality", json={"auto_commit": False, "max_candidates": 1})
    assert resp_virality.status_code == 401

    # /api/v1/trend-commit
    resp_commit = auth_client.post("/api/v1/trend-commit", json={"items": []})
    assert resp_commit.status_code == 401

    # /api/v1/s1-score
    resp_s1 = auth_client.post("/api/v1/s1-score", json={"niches": ["ai"], "markets": ["EN"]})
    assert resp_s1.status_code == 401

    # /api/v1/pipeline/run
    resp_run = auth_client.post("/api/v1/pipeline/run", json={"stage": "S1"})
    assert resp_run.status_code == 401


def test_invalid_bearer_token_rejected_401(auth_client):
    """Endpoints must reject invalid Bearer tokens with 401 Unauthorized."""
    headers = {"Authorization": "Bearer wrong_token_xyz"}
    resp = auth_client.post("/api/v1/trend-virality", json={"auto_commit": False, "max_candidates": 1}, headers=headers)
    assert resp.status_code == 401


def test_authenticated_request_accepted(auth_client, monkeypatch):
    """Endpoints accept valid Bearer token matching VF_API_TOKEN."""
    from unittest.mock import patch

    headers = {"Authorization": "Bearer test_secret_token_12345"}

    # Mock discover_and_produce_market_trend to avoid network call during test
    with patch("app.services.trend_engine_b1.discover_and_produce_market_trend", return_value=[]):
        resp = auth_client.post(
            "/api/v1/trend-virality",
            json={"auto_commit": False, "max_candidates": 1},
            headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        assert data.get("pipeline") == "approach_b_direct_recon"


def test_testclient_not_in_loopback_allowlist(monkeypatch):
    """When VF_API_TOKEN is unset, TestClient (client.host='testclient') must NOT be treated as loopback."""
    monkeypatch.delenv("VF_API_TOKEN", raising=False)
    monkeypatch.setenv("VF_ALLOW_UNAUTH_LOOPBACK", "1")
    client = TestClient(app)

    # Calling from TestClient has host 'testclient' which is excluded from loopback allowlist
    resp = client.post("/api/v1/trend-virality", json={"auto_commit": False, "max_candidates": 1})
    assert resp.status_code == 401
