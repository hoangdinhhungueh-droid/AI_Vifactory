#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_vps_runner_failover.py

Verifies FastVPSClient endpoint configuration and fallback order (Rule 138 & Boss Item 6).
"""

from scripts.vps_runner import ENDPOINTS, FastVPSClient


def test_vps_endpoints_configuration_and_failover_order():
    """Rule 138: Asserts endpoints are defined with failover support and valid schema."""
    assert len(ENDPOINTS) >= 2, "Expected at least 2 VPS endpoints for high-availability failover"
    
    endpoint_names = [ep["name"] for ep in ENDPOINTS]
    assert "mcp2" in endpoint_names
    assert "ag" in endpoint_names

    for ep in ENDPOINTS:
        assert "name" in ep and ep["name"]
        assert "url" in ep and ep["url"].startswith("https://")
        assert "token" in ep
        assert "cf_id" in ep
        assert "cf_secret" in ep


def test_fast_vps_client_initialization_with_custom_endpoint():
    """Verifies that FastVPSClient can be targeted to either primary or secondary endpoint using isolated fixtures."""
    isolated_endpoints = [
        {
            "name": "isolated_primary",
            "url": "https://mcp-primary.test.internal/mcp",
            "token": "tok_pri_abc123",
            "cf_id": "cf_id_primary",
            "cf_secret": "cf_sec_primary",
        },
        {
            "name": "isolated_secondary",
            "url": "https://mcp-secondary.test.internal/mcp",
            "token": "tok_sec_xyz789",
            "cf_id": "cf_id_secondary",
            "cf_secret": "cf_sec_secondary",
        },
    ]

    client_0 = FastVPSClient(endpoint_idx=0, auto_connect=False, endpoints=isolated_endpoints)
    assert client_0.endpoint_idx == 0
    assert client_0.ep["name"] == "isolated_primary"
    assert client_0.url == "https://mcp-primary.test.internal/mcp"

    client_0.switch_endpoint()
    assert client_0.endpoint_idx == 1
    assert client_0.ep["name"] == "isolated_secondary"
    assert client_0.url == "https://mcp-secondary.test.internal/mcp"


def test_fast_vps_client_real_failover_and_recovery(monkeypatch):
    """Boss Round 5 Item 7: Exercises connection failure, endpoint rotation, token selection, and recovery without synthetic production credentials."""
    import urllib.error
    import urllib.request

    isolated_endpoints = [
        {
            "name": "isolated_primary",
            "url": "https://mcp-primary.test.internal/mcp",
            "token": "tok_pri_abc123",
            "cf_id": "cf_id_primary",
            "cf_secret": "cf_sec_primary",
        },
        {
            "name": "isolated_secondary",
            "url": "https://mcp-secondary.test.internal/mcp",
            "token": "tok_sec_xyz789",
            "cf_id": "cf_id_secondary",
            "cf_secret": "cf_sec_secondary",
        },
    ]

    call_history = []

    class DummyResponse:
        headers = {"mcp-session-id": "sess_recovered_secondary_999"}
        def read(self):
            return b'{"jsonrpc": "2.0", "result": {}}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    def mock_urlopen(req, *args, **kwargs):
        target_url = req.full_url if hasattr(req, "full_url") else str(req)
        call_history.append({
            "url": target_url,
            "auth": req.headers.get("Authorization"),
            "cf_id": req.headers.get("Cf-access-client-id"),
        })
        if "primary" in target_url:
            raise urllib.error.URLError("Connection refused to primary endpoint")
        return DummyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    client = FastVPSClient(endpoint_idx=0, auto_connect=True, endpoints=isolated_endpoints)
    # Assert client successfully failed over and recovered
    assert client.endpoint_idx == 1
    assert client.ep["name"] == "isolated_secondary"
    assert client.url == "https://mcp-secondary.test.internal/mcp"
    assert client.token == "tok_sec_xyz789"
    assert client.session_id == "sess_recovered_secondary_999"

    # Verify that primary failed first, then secondary was contacted with correct token
    assert len(call_history) >= 2
    assert "primary" in call_history[0]["url"]
    assert call_history[0]["auth"] == "Bearer tok_pri_abc123"
    assert "secondary" in call_history[1]["url"]
    assert call_history[1]["auth"] == "Bearer tok_sec_xyz789"
