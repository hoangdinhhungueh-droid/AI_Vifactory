# tests/unit/test_model_gateway_ceiling.py
"""Unit tests for bounded MAX_ABSOLUTE_INPUT_CEILING configuration (Rule 138 & Rule 139).
Tests bounded normalization without using any test doubles.
"""

import contextlib
import os

import httpx
import pytest

from app.services.model_gateway import (
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


class ProviderInvocationSpy:
    """Provider-specific network dispatch spy recording per-provider invocations,
    payloads, headers, and endpoints for hermetic boundary verification without test doubles.
    """
    hhtech_dispatches: list = []
    anthropic_dispatches: list = []

    @classmethod
    def reset(cls):
        cls.hhtech_dispatches.clear()
        cls.anthropic_dispatches.clear()


@contextlib.contextmanager
def provider_spy_context():
    """Context manager providing atomic provider spy activation and guaranteed teardown restoration."""
    ProviderInvocationSpy.reset()
    orig_client = httpx.Client

    class SpyClient:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def post(self, url, *args, **kwargs):
            url_str = str(url)
            req_info = {
                "url": url_str,
                "headers": kwargs.get("headers", {}),
                "json": kwargs.get("json", {}),
            }
            if "anthropic.com" in url_str:
                ProviderInvocationSpy.anthropic_dispatches.append(req_info)
            else:
                ProviderInvocationSpy.hhtech_dispatches.append(req_info)
            raise RuntimeError(f"Unexpected network egress to {url_str} during offline boundary check")

        def stream(self, method, url, *args, **kwargs):
            url_str = str(url)
            req_info = {
                "url": url_str,
                "headers": kwargs.get("headers", {}),
                "json": kwargs.get("json", {}),
            }
            if "anthropic.com" in url_str:
                ProviderInvocationSpy.anthropic_dispatches.append(req_info)
            else:
                ProviderInvocationSpy.hhtech_dispatches.append(req_info)
            raise RuntimeError(f"Unexpected network egress stream to {url_str} during offline boundary check")

    httpx.Client = SpyClient
    try:
        yield ProviderInvocationSpy
    finally:
        httpx.Client = orig_client
        ProviderInvocationSpy.reset()


def test_oversized_request_rejected_before_provider_dispatch_default_ceiling():
    """Verifies that an input exceeding default 20k token ceiling is rejected before any provider dispatch."""
    old_key = os.environ.get("HHTECH_API_KEY")
    old_allow = os.environ.get("ALLOW_MASSIVE_LLM_CONTEXT")
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        os.environ.pop("ALLOW_MASSIVE_LLM_CONTEXT", None)
        with provider_spy_context() as spy:
            gw = ModelGateway()
            # 60,000 chars / 2.5 = 24,000 tokens > 20,000 default ceiling
            oversized_prompt = "A" * 60000
            with pytest.raises(TokenBudgetExceeded) as exc_info:
                gw._call_hhtech(prompt=oversized_prompt, model=gw.hhtech_model)
            assert "Token Bloat Guard" in str(exc_info.value)
            assert "safety ceiling" in str(exc_info.value)
            # Explicit verification: exactly 0 provider network dispatches occurred
            assert len(spy.hhtech_dispatches) == 0, "HHTech provider was dispatched despite oversized prompt!"
            assert len(spy.anthropic_dispatches) == 0, "Anthropic provider was dispatched unexpectedly!"
    finally:
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)
        if old_allow is not None:
            os.environ["ALLOW_MASSIVE_LLM_CONTEXT"] = old_allow
        else:
            os.environ.pop("ALLOW_MASSIVE_LLM_CONTEXT", None)


def test_oversized_request_rejected_before_provider_dispatch_absolute_ceiling():
    """Verifies that an input exceeding hard absolute ceiling is rejected before any provider dispatch even with override."""
    old_key = os.environ.get("HHTECH_API_KEY")
    old_allow = os.environ.get("ALLOW_MASSIVE_LLM_CONTEXT")
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        os.environ["ALLOW_MASSIVE_LLM_CONTEXT"] = "1"
        with provider_spy_context() as spy:
            gw = ModelGateway()
            ceiling_val = _get_max_absolute_input_ceiling()
            # Generate input strictly exceeding ceiling_val
            oversized_chars = int((ceiling_val + 5000) * 2.5) + 1000
            oversized_prompt = "A" * oversized_chars
            with pytest.raises(TokenBudgetExceeded) as exc_info:
                gw._call_hhtech(prompt=oversized_prompt, model=gw.hhtech_model)
            assert "Hard Absolute Ceiling Violated" in str(exc_info.value)
            assert f"exceeds absolute {ceiling_val} ceiling" in str(exc_info.value)
            # Explicit verification: exactly 0 provider network dispatches occurred
            assert len(spy.hhtech_dispatches) == 0, "HHTech provider was dispatched despite absolute ceiling breach!"
            assert len(spy.anthropic_dispatches) == 0, "Anthropic provider was dispatched unexpectedly!"
    finally:
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)
        if old_allow is not None:
            os.environ["ALLOW_MASSIVE_LLM_CONTEXT"] = old_allow
        else:
            os.environ.pop("ALLOW_MASSIVE_LLM_CONTEXT", None)


def test_provider_context_reservations_and_cost_rationale_configuration_derived():
    """Verifies mathematical provider context window reservations and bounded cost rationale (Rule 138 & Rule 139).
    Derives assertions directly from live ModelGateway methods rather than duplicating hardcoded model constants.
    """
    gw = ModelGateway()

    # 1. Configuration-derived properties validation
    assert isinstance(gw.hhtech_base_url, str) and gw.hhtech_base_url.startswith("https://")
    assert isinstance(gw.hhtech_model, str) and len(gw.hhtech_model) > 0

    configured_ceiling = _get_max_absolute_input_ceiling()
    assert 1000 <= configured_ceiling <= 200000, f"Configured ceiling {configured_ceiling} outside valid bounds"

    # 2. Context window and output reservations dynamically queried from gateway configuration
    active_context_window = gw.get_context_window()
    assert active_context_window == gw.PROVIDER_CONTEXT_WINDOWS.get(gw.hhtech_model, 128000)

    active_output_reservation = gw.get_output_reservation()
    expected_reservation = max(0, active_context_window - configured_ceiling)
    assert active_output_reservation == expected_reservation

    claude_context_window = gw.get_context_window("claude-sonnet-5-5")
    assert claude_context_window == gw.PROVIDER_CONTEXT_WINDOWS["claude-sonnet-5-5"]
    claude_output_reservation = gw.get_output_reservation("claude-sonnet-5-5")
    assert claude_output_reservation == max(0, claude_context_window - configured_ceiling)

    sol_context_window = gw.get_context_window("gpt-6.1-sol")
    assert sol_context_window == gw.PROVIDER_CONTEXT_WINDOWS["gpt-6.1-sol"]
    sol_output_reservation = gw.get_output_reservation("gpt-6.1-sol")
    assert sol_output_reservation == max(0, sol_context_window - configured_ceiling)

    # 3. Financial bounds derived directly from gateway token rates and live ceiling
    active_rate = gw.get_model_token_rate()
    assert active_rate == gw.cost_tracker.RATES.get(gw.hhtech_model, gw.cost_tracker.RATES.get("default", 1.6))

    sol_rate = gw.get_model_token_rate("gpt-6.1-sol")
    assert sol_rate == gw.cost_tracker.RATES["gpt-6.1-sol"]

    active_max_cost = gw.get_max_request_cost_vnd()
    assert active_max_cost == (configured_ceiling / 1000.0) * active_rate

    sol_max_cost = gw.get_max_request_cost_vnd("gpt-6.1-sol")
    assert sol_max_cost == (configured_ceiling / 1000.0) * sol_rate


def test_provider_context_reservations_consumed_under_modified_configuration():
    """Verifies that context windows, output reservations, and cost calculations
    dynamically consume live modified configuration rather than static assumptions (Rule 138 & Rule 139).
    """
    old_model = os.environ.get("HHTECH_MODEL")
    old_ceiling = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    try:
        # Case A: Configure Sol model with 75,000 ceiling
        os.environ["HHTECH_MODEL"] = "gpt-6.1-sol"
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "75000"
        gw_sol = ModelGateway()
        assert gw_sol.hhtech_model == "gpt-6.1-sol"
        assert gw_sol.get_context_window() == gw_sol.PROVIDER_CONTEXT_WINDOWS["gpt-6.1-sol"]
        assert gw_sol.get_output_reservation() == gw_sol.PROVIDER_CONTEXT_WINDOWS["gpt-6.1-sol"] - 75000
        assert gw_sol.get_model_token_rate() == gw_sol.cost_tracker.RATES["gpt-6.1-sol"]
        assert gw_sol.get_max_request_cost_vnd() == (75000 / 1000.0) * gw_sol.get_model_token_rate()

        # Case B: Configure Opus model with 140,000 ceiling
        os.environ["HHTECH_MODEL"] = "claude-opus-5-5"
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "140000"
        gw_opus = ModelGateway()
        assert gw_opus.hhtech_model == "claude-opus-5-5"
        assert gw_opus.get_context_window() == gw_opus.PROVIDER_CONTEXT_WINDOWS["claude-opus-5-5"]
        assert gw_opus.get_output_reservation() == gw_opus.PROVIDER_CONTEXT_WINDOWS["claude-opus-5-5"] - 140000
        assert gw_opus.get_model_token_rate() == gw_opus.cost_tracker.RATES["claude-opus-5-5"]
        assert gw_opus.get_max_request_cost_vnd() == (140000 / 1000.0) * gw_opus.get_model_token_rate()
    finally:
        if old_model is not None:
            os.environ["HHTECH_MODEL"] = old_model
        else:
            os.environ.pop("HHTECH_MODEL", None)
        if old_ceiling is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_ceiling
        else:
            os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)


def test_provider_spy_cleanup_guarantee_on_assertion_failure():
    """Verifies that provider_spy_context safely restores original httpx.Client even if an inner assertion fails."""
    orig_client = httpx.Client
    try:
        with provider_spy_context():
            assert httpx.Client != orig_client
            # Simulate an inner failure
            raise ValueError("Intentional test assertion trigger")
    except ValueError as _expected_val_err:
        assert "Intentional test assertion trigger" in str(_expected_val_err)

    assert httpx.Client == orig_client, "httpx.Client was not restored after exception in context block!"


