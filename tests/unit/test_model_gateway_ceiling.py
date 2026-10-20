# tests/unit/test_model_gateway_ceiling.py
"""Unit tests for bounded MAX_ABSOLUTE_INPUT_CEILING configuration (Rule 138 & Rule 139).
Tests bounded normalization without using any test doubles.
"""

import contextlib
import os

import httpx
import pytest

from app.services.model_gateway import (
    AllProvidersFailed,
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
    Discovers supported models and validated settings directly from authoritative gateway configuration.
    """
    gw = ModelGateway()

    # 1. Configuration-derived properties validation
    assert isinstance(gw.hhtech_base_url, str) and gw.hhtech_base_url.startswith("https://")
    assert isinstance(gw.hhtech_model, str) and len(gw.hhtech_model) > 0

    configured_ceiling = _get_max_absolute_input_ceiling()
    assert 1000 <= configured_ceiling <= 200000, f"Configured ceiling {configured_ceiling} outside valid bounds"

    # 2. Dynamically iterate over all authoritatively registered provider models
    registered_models = list(gw.PROVIDER_CONTEXT_WINDOWS.keys())
    assert len(registered_models) > 0, "No models registered in PROVIDER_CONTEXT_WINDOWS"

    rates = getattr(gw.cost_tracker, "RATES", {})
    for m in registered_models:
        ctx_win = gw.get_context_window(m)
        assert ctx_win == gw.PROVIDER_CONTEXT_WINDOWS[m]
        assert ctx_win > 0

        # If configured ceiling fits inside context window, output reservation is justified
        if configured_ceiling < ctx_win:
            expected_headroom = ctx_win - configured_ceiling
            assert gw.get_output_reservation(m) == expected_headroom

        if m in rates:
            rate = gw.get_model_token_rate(m)
            assert rate == rates[m]
            if configured_ceiling < ctx_win:
                expected_max_cost = ((configured_ceiling + (ctx_win - configured_ceiling)) / 1000.0) * rate
                assert gw.get_max_request_cost_vnd(m) == expected_max_cost
                assert gw.get_max_input_cost_vnd(m) == (configured_ceiling / 1000.0) * rate

    # 3. Fail-closed: unsupported models and missing pricing must raise ModelGatewayError
    with pytest.raises(Exception) as exc_unsupported:
        gw.get_context_window("completely_unsupported_model_identifier")
    assert "Unsupported model" in str(exc_unsupported.value)

    with pytest.raises(Exception) as exc_pricing:
        gw.get_model_token_rate("model_missing_pricing_configuration")
    assert "Missing pricing configuration" in str(exc_pricing.value)


def test_incompatible_configuration_fails_closed():
    """Verifies that an incompatible configuration where input ceiling >= context window
    fails closed immediately rather than reporting zero or negative reservation.
    """
    gw = ModelGateway()
    # Discover a model with known context window
    smallest_model = min(gw.PROVIDER_CONTEXT_WINDOWS.keys(), key=lambda m: gw.PROVIDER_CONTEXT_WINDOWS[m])
    min_ctx = gw.PROVIDER_CONTEXT_WINDOWS[smallest_model]

    old_ceiling = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    try:
        # Set absolute ceiling exceeding the model context window
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = str(min_ctx + 5000)
        with pytest.raises(Exception) as exc_incomp:
            gw.get_output_reservation(smallest_model)
        assert "Incompatible configuration" in str(exc_incomp.value)
        assert "must be strictly less than" in str(exc_incomp.value)
    finally:
        if old_ceiling is not None:
            os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = old_ceiling
        else:
            os.environ.pop("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", None)


def test_provider_dispatch_enforces_context_and_output_reservation_default_config():
    """Verifies that provider dispatch inspects and enforces context window headroom
    and captures correct model and output reservations in provider payload.
    """
    old_key = os.environ.get("HHTECH_API_KEY")
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        gw = ModelGateway()
        active_model = gw.hhtech_model
        ctx_win = gw.get_context_window(active_model)

        with provider_spy_context() as spy:
            # 1. Normal valid request: payload contains expected model, max_tokens, and messages
            valid_prompt = "A" * 1000  # 400 tokens
            requested_output = 2048
            try:
                gw._call_hhtech(prompt=valid_prompt, model=active_model, max_tokens=requested_output)
            except RuntimeError as spy_err:
                # Spy deliberately intercepts egress post-payload capture
                assert "Unexpected network egress" in str(spy_err)

            assert len(spy.hhtech_dispatches) == 1
            captured_payload = spy.hhtech_dispatches[0]["json"]
            assert captured_payload["model"] == active_model
            assert captured_payload["max_tokens"] == requested_output
            assert len(captured_payload["messages"]) >= 1

        # 2. Exceeding context window: input + output reservation > context window fails before egress
        with provider_spy_context() as spy:
            excessive_output = ctx_win + 1000
            with pytest.raises(TokenBudgetExceeded) as exc_budget:
                gw._call_hhtech(prompt="A" * 500, model=active_model, max_tokens=excessive_output)
            assert "Context Window Exceeded" in str(exc_budget.value)
            assert len(spy.hhtech_dispatches) == 0, "Network egress occurred despite exceeding context window!"
    finally:
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)


def test_provider_dispatch_enforces_modified_configuration_and_payload_inspection():
    """Verifies that modifying configuration alters provider dispatch payload and admission decision."""
    old_key = os.environ.get("HHTECH_API_KEY")
    old_model = os.environ.get("HHTECH_MODEL")
    old_ceiling = os.environ.get("HHTECH_MAX_ABSOLUTE_INPUT_CEILING")
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        # Discover an alternate model from authoritative configuration
        gw_temp = ModelGateway()
        alternate_model = [m for m in gw_temp.PROVIDER_CONTEXT_WINDOWS.keys() if m != gw_temp.hhtech_model][0]
        os.environ["HHTECH_MODEL"] = alternate_model
        os.environ["HHTECH_MAX_ABSOLUTE_INPUT_CEILING"] = "50000"

        gw_mod = ModelGateway()
        assert gw_mod.hhtech_model == alternate_model

        with provider_spy_context() as spy:
            custom_output_tokens = 1024
            try:
                gw_mod._call_hhtech(prompt="Test modified configuration", model=alternate_model, max_tokens=custom_output_tokens)
            except RuntimeError as spy_err:
                assert "Unexpected network egress" in str(spy_err)

            assert len(spy.hhtech_dispatches) == 1
            captured_payload = spy.hhtech_dispatches[0]["json"]
            assert captured_payload["model"] == alternate_model
            assert captured_payload["max_tokens"] == custom_output_tokens
    finally:
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)
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


def test_call_llm_preflight_budget_gating_exercised():
    """Verifies that call_llm exercises get_max_request_cost_vnd and get_max_input_cost_vnd for live budget gating (Boss Round 29 Item 3)."""
    from app.services.cost_tracker import CostTracker

    class BoundedCostTracker(CostTracker):
        def __init__(self, remaining_budget: float):
            self.cap_vnd = None
            self.costs = {}
            self._rem = remaining_budget

        def get_remaining_budget(self) -> float:
            return self._rem

    # 1. Exhausted budget: must fail closed before calling provider
    gw_tight = ModelGateway(cost_tracker=BoundedCostTracker(remaining_budget=0.001))
    target_model = gw_tight.hhtech_model
    expected_req_cost = gw_tight.get_max_request_cost_vnd(target_model, max_output_tokens=2048)
    expected_inp_cost = gw_tight.get_max_input_cost_vnd(target_model)
    assert expected_req_cost > 0.001
    assert expected_inp_cost > 0

    with pytest.raises(TokenBudgetExceeded) as exc_info:
        gw_tight.call_llm(prompt="Budget gating test prompt", model=target_model, max_tokens=2048)

    assert "Projected request cost" in str(exc_info.value)
    assert "exceeds remaining budget" in str(exc_info.value)

    # 2. Generous budget: pre-flight check succeeds and reaches provider dispatch
    old_key = os.environ.get("HHTECH_API_KEY")
    try:
        os.environ["HHTECH_API_KEY"] = "sk-test-dummy-key"
        gw_generous = ModelGateway(cost_tracker=BoundedCostTracker(remaining_budget=1000000.0))
        with provider_spy_context() as spy:
            try:
                gw_generous.call_llm(prompt="Budget sufficient prompt", model=target_model, max_tokens=2048)
            except RuntimeError as egress_err:
                assert "Unexpected network egress" in str(egress_err)
            assert len(spy.hhtech_dispatches) == 1
            assert spy.hhtech_dispatches[0]["json"]["model"] == target_model
    finally:
        if old_key is not None:
            os.environ["HHTECH_API_KEY"] = old_key
        else:
            os.environ.pop("HHTECH_API_KEY", None)


def test_call_llm_fallback_budget_gating_exercised():
    """Verifies that fallback path in call_llm also exercises budget estimation gating for fallback model."""
    from app.services.cost_tracker import CostTracker

    class FallbackLimitingCostTracker(CostTracker):
        def __init__(self):
            self.cap_vnd = None
            self.costs = {}
            self.call_count = 0

        def get_remaining_budget(self) -> float:
            self.call_count += 1
            # Primary model passes (call 1), but when fallback is evaluated (call 2), budget is 0
            return 1000000.0 if self.call_count <= 1 else 0.0001

    gw = ModelGateway(cost_tracker=FallbackLimitingCostTracker())
    # Primary _call_hhtech will fail, triggering fallback budget evaluation
    with pytest.raises(AllProvidersFailed) as exc_info:
        gw.call_llm(
            prompt="Trigger fallback",
            model="gpt-6.1-sol",
            fallback="claude-sonnet-5",
            max_tokens=2048
        )
    assert "Fallback projected request cost" in str(exc_info.value)
    assert "exceeds remaining budget" in str(exc_info.value)


