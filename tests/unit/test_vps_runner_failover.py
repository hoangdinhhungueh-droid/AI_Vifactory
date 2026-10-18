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
    """Verifies that FastVPSClient can be targeted to either primary or secondary endpoint."""
    client_0 = FastVPSClient(endpoint_idx=0)
    assert client_0.endpoint_idx == 0
    assert client_0.ep["name"] == ENDPOINTS[0]["name"]

    client_1 = FastVPSClient(endpoint_idx=1)
    assert client_1.endpoint_idx == 1
    assert client_1.ep["name"] == ENDPOINTS[1]["name"]
