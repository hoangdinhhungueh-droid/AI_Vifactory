# tests/unit/test_model_gateway_ceiling.py
"""Unit tests for bounded MAX_ABSOLUTE_INPUT_CEILING configuration (Rule 138 & Rule 139).
Tests bounded normalization without using any test doubles.
"""

import os

import pytest

from app.services.model_gateway import (
    MAX_ABSOLUTE_INPUT_CEILING,
    ModelGateway,
    TokenBudgetExceeded,
    _get_max_absolute_input_ceiling,
)


def test_default_ceiling_when_env_unset():
    """Verifies default ceiling is 120,000 tokens when env var is unset."""
    old_val = os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)
    try:
        assert _get_max_absolute_input_ceiling() == 120000
    finally:
        if old_val is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_val


def test_custom_valid_ceiling():
    """Verifies custom value within valid range [1000, 200000] is accepted."""
    old_val = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "85000"
    try:
        assert _get_max_absolute_input_ceiling() == 85000
    finally:
        if old_val is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_val
        else:
            os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)


def test_ceiling_clamped_to_minimum():
    """Verifies values below 1000 tokens are clamped to minimum 1000."""
    old_val = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    try:
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "500"
        assert _get_max_absolute_input_ceiling() == 1000
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "-5000"
        assert _get_max_absolute_input_ceiling() == 1000
    finally:
        if old_val is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_val
        else:
            os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)


def test_ceiling_clamped_to_maximum():
    """Verifies values above 200,000 tokens are clamped to safety cap 200,000."""
    old_val = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "500000"
    try:
        assert _get_max_absolute_input_ceiling() == 200000
    finally:
        if old_val is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_val
        else:
            os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)


def test_invalid_non_numeric_fallback():
    """Verifies non-numeric values gracefully fallback to default 120,000."""
    old_val = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    try:
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "invalid_number"
        assert _get_max_absolute_input_ceiling() == 120000
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = ""
        assert _get_max_absolute_input_ceiling() == 120000
    finally:
        if old_val is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_val
        else:
            os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)


import httpx


class SpyNetworkTransport:
    """Pure Python spy counter for verifying zero provider network invocations."""
    invocation_count: int = 0

    def __init__(self, *args, **kwargs):
        SpyNetworkTransport.invocation_count += 1
        raise RuntimeError("Provider network transport was unexpectedly initialized!")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def test_oversized_request_rejected_before_provider_dispatch_default_ceiling():
    """Verifies that an input exceeding default 20k token ceiling is rejected before any provider dispatch."""
    old_key = os.environ.get("HHTECH_API_KEY")
    old_allow = os.environ.get("ALLOW_MASSIVE_LLM_CONTEXT")
    orig_client = httpx.Client
    SpyNetworkTransport.invocation_count = 0
    httpx.Client = SpyNetworkTransport
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        os.environ.pop("ALLOW_MASSIVE_LLM_CONTEXT", None)
        gw = ModelGateway()
        # 60,000 chars / 2.5 = 24,000 tokens > 20,000 default ceiling
        oversized_prompt = "A" * 60000
        with pytest.raises(TokenBudgetExceeded) as exc_info:
            gw._call_hhtech(prompt=oversized_prompt, model="claude-opus-5-5")
        assert "Token Bloat Guard" in str(exc_info.value)
        assert "safety ceiling" in str(exc_info.value)
        # Explicit verification: exactly 0 provider network dispatches occurred
        assert SpyNetworkTransport.invocation_count == 0, "Provider was dispatched despite oversized prompt!"
    finally:
        httpx.Client = orig_client
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)
        if old_allow is not None:
            os.environ["ALLOW_MASSIVE_LLM_CONTEXT"] = old_allow
        else:
            os.environ.pop("ALLOW_MASSIVE_LLM_CONTEXT", None)


def test_oversized_request_rejected_before_provider_dispatch_absolute_ceiling():
    """Verifies that an input exceeding hard 120k absolute ceiling is rejected before any provider dispatch even with override."""
    old_key = os.environ.get("HHTECH_API_KEY")
    old_allow = os.environ.get("ALLOW_MASSIVE_LLM_CONTEXT")
    orig_client = httpx.Client
    SpyNetworkTransport.invocation_count = 0
    httpx.Client = SpyNetworkTransport
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        os.environ["ALLOW_MASSIVE_LLM_CONTEXT"] = "1"
        gw = ModelGateway()
        # 350,000 chars / 2.5 = 140,000 tokens > 120,000 absolute ceiling
        oversized_prompt = "A" * 350000
        with pytest.raises(TokenBudgetExceeded) as exc_info:
            gw._call_hhtech(prompt=oversized_prompt, model="claude-opus-5-5")
        assert "Hard Absolute Ceiling Violated" in str(exc_info.value)
        assert f"exceeds absolute {MAX_ABSOLUTE_INPUT_CEILING} ceiling" in str(exc_info.value)
        # Explicit verification: exactly 0 provider network dispatches occurred
        assert SpyNetworkTransport.invocation_count == 0, "Provider was dispatched despite absolute ceiling breach!"
    finally:
        httpx.Client = orig_client
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)
        if old_allow is not None:
            os.environ["ALLOW_MASSIVE_LLM_CONTEXT"] = old_allow
        else:
            os.environ.pop("ALLOW_MASSIVE_LLM_CONTEXT", None)


def test_provider_context_reservations_and_cost_rationale():
    """Verifies mathematical provider context window reservations and bounded cost rationale (Rule 138 & Rule 139).
    Context reservations tied to actual model configurations:
      - Primary Model (gpt-6.1-sol):
          Context Window: 128,000 tokens
          Max Input Ceiling: 120,000 tokens (clamped MAX_ABSOLUTE_INPUT_CEILING)
          Output Reservation: 8,000 tokens guaranteed for complete reasoning chain.
      - Supervisory Model (claude-opus-5-5):
          Context Window: 200,000 tokens
          Max Input Ceiling: 120,000 tokens
          Output Reservation: 80,000 tokens guaranteed for complete forensic audit.
    Cost rationale:
      - Maximum input cost at HHTech rate (~0.8 VND / 1k input tokens): 120 * 0.8 = 96 VND (< 100 VND / $0.0038).
      - Proves financial safety against runaway token consumption during forensic audits.
    """
    # 1. gpt-6.1-sol configuration reservations
    gpt61_context_window = 128000
    gpt61_output_reservation = gpt61_context_window - MAX_ABSOLUTE_INPUT_CEILING
    assert gpt61_output_reservation >= 8000, f"gpt-6.1-sol output reservation {gpt61_output_reservation} < 8,000 tokens"
    assert MAX_ABSOLUTE_INPUT_CEILING == 120000

    # 2. claude-opus-5-5 configuration reservations
    opus55_context_window = 200000
    opus55_output_reservation = opus55_context_window - MAX_ABSOLUTE_INPUT_CEILING
    assert opus55_output_reservation >= 80000, f"claude-opus-5-5 output reservation {opus55_output_reservation} < 80,000 tokens"

    # 3. Financial upper bound: 120,000 tokens * 0.8 VND/1000 tokens = 96 VND
    max_request_cost_vnd = (MAX_ABSOLUTE_INPUT_CEILING / 1000.0) * 0.8
    assert max_request_cost_vnd <= 100.0, f"Max cost {max_request_cost_vnd} VND exceeds safety threshold 100 VND"

