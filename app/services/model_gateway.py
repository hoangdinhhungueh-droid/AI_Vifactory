# app/services/model_gateway.py
"""
Model Gateway for VF Pipeline - Pattern 3 Implementation.
Centralizes all model API calls with:
  - Automatic cost tracking and telemetry
  - Provider fallback support (HHTech → Anthropic)
  - A/B testing capability
  - Unified error handling
"""

import json
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from app.services.cost_tracker import get_global_tracker

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Model category types."""
    LLM = "llm"
    IMAGE = "image"
    AUDIO = "audio"


class ModelGatewayError(Exception):
    """Base exception for model gateway errors."""
    pass


class TokenBudgetExceeded(ModelGatewayError):
    """Raised when request payload exceeds safety token ceiling to prevent credit exhaustion."""
    pass


class AllProvidersFailed(ModelGatewayError):
    """Raised when primary and all fallback providers fail."""
    pass


def _get_max_absolute_input_ceiling() -> int:
    """Bounded, validated absolute ceiling for massive context overrides (Rule 138/139).
    Restricts safety ceiling strictly between 1,000 and 200,000 tokens.
    """
    raw = os.getenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "120000")
    try:
        val = int(raw)
        return max(1000, min(val, 200000))
    except (ValueError, TypeError):
        return 120000


MAX_ABSOLUTE_INPUT_CEILING = _get_max_absolute_input_ceiling()


class ModelGateway:
    """
    Centralized gateway for all model API calls.

    Features:
    - Cost tracking and telemetry
    - Automatic fallback to secondary providers
    - Standardized error handling
    - Request/response logging
    """

    PROVIDER_CONTEXT_WINDOWS: Dict[str, int] = {
        "claude-sonnet-5-5": 200000,
        "claude-opus-5-5": 200000,
        "claude-opus-5": 200000,
        "claude-sonnet-5": 200000,
        "claude-3.5-sonnet": 200000,
        "claude-3-opus": 200000,
        "gpt-6.1-sol": 128000,
        "gpt-6-astra": 128000,
        "gpt-5-sol": 128000,
        "kimi-k3": 200000,
    }

    def get_context_window(self, model: Optional[str] = None) -> int:
        """Returns the total provider context window size in tokens for the model.
        Fails closed (Rule 121 / Rule 139) if model is unknown or unsupported.
        """
        target_model = model or self.hhtech_model
        if target_model not in self.PROVIDER_CONTEXT_WINDOWS:
            raise ModelGatewayError(
                f"Unsupported model '{target_model}': not registered in PROVIDER_CONTEXT_WINDOWS. "
                f"Supported models: {sorted(self.PROVIDER_CONTEXT_WINDOWS.keys())}"
            )
        return self.PROVIDER_CONTEXT_WINDOWS[target_model]

    def get_output_reservation(self, model: Optional[str] = None, requested_max_tokens: Optional[int] = None) -> int:
        """Derives and validates reserved token headroom for output generation under live ceiling.
        If requested_max_tokens is specified, validates that it fits within available headroom.
        Fails closed if ceiling is incompatible with context window (ceiling >= ctx_win).
        """
        target_model = model or self.hhtech_model
        ctx_win = self.get_context_window(target_model)
        ceiling = _get_max_absolute_input_ceiling()
        if ceiling >= ctx_win:
            raise ModelGatewayError(
                f"Incompatible configuration for '{target_model}': absolute input ceiling ({ceiling}) "
                f"must be strictly less than model context window ({ctx_win})."
            )
        available_headroom = ctx_win - ceiling
        if requested_max_tokens is not None:
            if requested_max_tokens <= 0:
                raise ModelGatewayError(f"requested_max_tokens must be positive, got {requested_max_tokens}")
            if requested_max_tokens > available_headroom:
                raise ModelGatewayError(
                    f"Requested output tokens ({requested_max_tokens}) exceeds available headroom "
                    f"({available_headroom}) under ceiling {ceiling} for model '{target_model}' (ctx: {ctx_win})."
                )
            return requested_max_tokens
        return available_headroom

    def get_model_token_rate(self, model: Optional[str] = None) -> float:
        """Derives the VND rate per 1,000 tokens for the configured model from CostTracker.
        Fails closed if the model is not registered in CostTracker.RATES.
        """
        target_model = model or self.hhtech_model
        rates = getattr(self.cost_tracker, "RATES", {})
        if target_model not in rates:
            raise ModelGatewayError(
                f"Missing pricing configuration: model '{target_model}' is not registered in CostTracker.RATES. "
                f"Configured models: {sorted(rates.keys())}"
            )
        return rates[target_model]

    def get_max_request_cost_vnd(self, model: Optional[str] = None, max_output_tokens: Optional[int] = None) -> float:
        """Calculates justified maximum theoretical VND cost for a single request under live ceiling
        including both maximum input ceiling tokens and output reservation headroom.
        """
        target_model = model or self.hhtech_model
        ceiling = _get_max_absolute_input_ceiling()
        output_res = self.get_output_reservation(target_model, requested_max_tokens=max_output_tokens)
        total_tokens = ceiling + output_res
        rate = self.get_model_token_rate(target_model)
        return (total_tokens / 1000.0) * rate

    def get_max_input_cost_vnd(self, model: Optional[str] = None) -> float:
        """Calculates theoretical maximum VND cost for the input portion alone under live ceiling."""
        target_model = model or self.hhtech_model
        ceiling = _get_max_absolute_input_ceiling()
        rate = self.get_model_token_rate(target_model)
        return (ceiling / 1000.0) * rate

    def __init__(self, cost_tracker=None):
        """
        Initialize model gateway.

        Args:
            cost_tracker: Optional CostTracker instance (uses global if None)
        """
        self.cost_tracker = cost_tracker or get_global_tracker()
        self._load_config()

    def _load_config(self):
        """Load API keys and configuration from environment."""
        self.hhtech_key = os.getenv("HHTECH_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.hhtech_base_url = os.getenv("HHTECH_BASE_URL", "https://hhtechapi.com/v1")
        self.hhtech_model = os.getenv("HHTECH_MODEL", "claude-sonnet-5-5")

        # Load from secrets file if env vars not set or key is masked/invalid
        is_invalid_key = not self.hhtech_key or any(ord(c) > 127 for c in self.hhtech_key) or "••" in self.hhtech_key
        if is_invalid_key:
            self._try_load_secrets()

    def _try_load_secrets(self):
        """Try loading secrets from /root/secrets/.env file."""
        try:
            secrets_path = "/root/secrets/.env"
            if os.path.exists(secrets_path):
                with open(secrets_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("HHTECH_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if key:
                                self.hhtech_key = key
                                os.environ["HHTECH_API_KEY"] = key
                        elif line.startswith("ANTHROPIC_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if key:
                                self.anthropic_key = key
                                os.environ["ANTHROPIC_API_KEY"] = key
        except Exception as e:
            logger.warning(f"[GATEWAY] Could not load secrets file: {e}")

    def call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.5,
        timeout: float = 60.0,
        fallback: Optional[str] = None
    ) -> str:
        """
        Call LLM with automatic fallback and cost tracking.

        Args:
            prompt: User prompt text
            model: Model identifier (default: claude-sonnet-5-5)
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            timeout: Request timeout in seconds
            fallback: Optional fallback model (e.g., "claude-3.5-sonnet")

        Returns:
            Generated text response

        Raises:
            AllProvidersFailed: If primary and all fallbacks fail
        """
        model = model or self.hhtech_model

        # Live budget estimation gating (Boss Round 29 Punchlist Item 3)
        proj_req_cost = self.get_max_request_cost_vnd(model=model, max_output_tokens=max_tokens)
        proj_inp_cost = self.get_max_input_cost_vnd(model=model)
        remaining_budget = self.get_remaining_budget()
        if proj_req_cost > remaining_budget:
            raise TokenBudgetExceeded(
                f"Projected request cost {proj_req_cost:.2f} VND (input ceiling: {proj_inp_cost:.2f} VND) "
                f"exceeds remaining budget {remaining_budget:.2f} VND for model '{model}'"
            )
        logger.debug(
            f"[GATEWAY] Budget pre-check passed: proj_req_cost={proj_req_cost:.2f} VND, "
            f"proj_inp_cost={proj_inp_cost:.2f} VND, remaining_budget={remaining_budget:.2f} VND"
        )

        # Try primary provider
        try:
            logger.info(f"[GATEWAY] Calling primary model: {model}")
            response = self._call_hhtech(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout
            )
            return response

        except Exception as e:
            logger.warning(f"[GATEWAY] Primary model {model} failed: {e}")

            # Try fallback if configured
            if fallback:
                try:
                    logger.info(f"[GATEWAY] Trying fallback model: {fallback}")
                    fb_req_cost = self.get_max_request_cost_vnd(model=fallback, max_output_tokens=max_tokens)
                    fb_inp_cost = self.get_max_input_cost_vnd(model=fallback)
                    rem_budget = self.get_remaining_budget()
                    if fb_req_cost > rem_budget:
                        raise TokenBudgetExceeded(
                            f"Fallback projected request cost {fb_req_cost:.2f} VND (input ceiling: {fb_inp_cost:.2f} VND) "
                            f"exceeds remaining budget {rem_budget:.2f} VND for fallback model '{fallback}'"
                        )
                    response = self._call_fallback_llm(
                        prompt=prompt,
                        model=fallback,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=timeout
                    )
                    return response

                except Exception as fallback_error:
                    logger.error(f"[GATEWAY] Fallback model {fallback} also failed: {fallback_error}")
                    raise AllProvidersFailed(
                        f"Primary ({model}) and fallback ({fallback}) both failed. "
                        f"Primary error: {e}. Fallback error: {fallback_error}"
                    )
            else:
                # No fallback configured, re-raise original error
                raise

    def _call_hhtech(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: float = 120.0,
        image_base64: Optional[str] = None
    ) -> str:
        """Call HHTech API (primary provider) with automatic retry on streaming ReadTimeout."""
        if not self.hhtech_key:
            raise ModelGatewayError("HHTECH_API_KEY not configured")

        # 1. Authoritative Model & Context Window Validation (Fail-Closed)
        ctx_win = self.get_context_window(model)

        # 2. Pre-Flight Token Sanitizer & Hard Ceiling Guard (Anti-Bloat Law per vf-pipeline-teamwork)
        # Conservative factor 2.5 accounts for dense code, Vietnamese unicode, and markdown overhead
        est_tokens = int((len(prompt) + len(system_prompt or "")) / 2.5)

        # 3. Enforce combined input + requested output reservation within model context window
        combined_tokens = est_tokens + max_tokens
        if combined_tokens > ctx_win:
            err_msg = (
                f"Context Window Exceeded: Combined input estimate ({est_tokens} tokens) + "
                f"requested output ({max_tokens} tokens) = {combined_tokens} tokens "
                f"exceeds model '{model}' context window of {ctx_win} tokens."
            )
            logger.error(f"🛑 [CONTEXT EXCEEDED BLOCKED] {err_msg}")
            raise TokenBudgetExceeded(err_msg)

        max_ceiling = int(os.getenv("HHTECH_MAX_INPUT_TOKENS_CEILING", "20000"))
        allow_massive = os.getenv("ALLOW_MASSIVE_LLM_CONTEXT") == "1"
        if est_tokens > max_ceiling and not image_base64:
            if not allow_massive:
                err_msg = (
                    f"Token Bloat Guard: Input text payload estimate ({est_tokens} tokens) "
                    f"exceeds {max_ceiling} safety ceiling for model {model}. "
                    f"Aborting call to prevent credit exhaustion. Use AST/compact diff or set ALLOW_MASSIVE_LLM_CONTEXT=1."
                )
                logger.error(f"🛑 [TOKEN BLOAT BLOCKED] {err_msg}")
                raise TokenBudgetExceeded(err_msg)
            elif est_tokens > MAX_ABSOLUTE_INPUT_CEILING:
                err_msg = (
                    f"Hard Absolute Ceiling Violated: Input text payload estimate ({est_tokens} tokens) "
                    f"exceeds absolute {MAX_ABSOLUTE_INPUT_CEILING} ceiling for model {model}. "
                    f"Override aborted to protect account budget."
                )
                logger.critical(f"🚨 [ABSOLUTE CEILING BLOCKED] {err_msg}")
                raise TokenBudgetExceeded(err_msg)
            else:
                logger.warning(
                    f"⚠️ [MASSIVE CONTEXT AUDIT] Allowed override with ~{est_tokens} tokens "
                    f"(Model: {model}, Ceiling: {max_ceiling}, Absolute: {MAX_ABSOLUTE_INPUT_CEILING})."
                )

        headers = {
            "Authorization": f"Bearer {self.hhtech_key}",
            "Content-Type": "application/json"
        }
        if "claude" in model.lower():
            headers["anthropic-beta"] = "prompt-caching-2024-07-31"

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if image_base64:
            user_content: List[Dict[str, Any]] = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True
        }
        if not model.startswith("kimi"):
            payload["temperature"] = temperature

        max_retries = 3
        last_error = None
        result = ""
        total_tokens = 0

        for attempt in range(1, max_retries + 1):
            try:
                full_content: List[str] = []
                full_reasoning: List[str] = []
                total_tokens = 0
                timeout_config = httpx.Timeout(timeout=timeout, connect=30.0, read=timeout, write=30.0, pool=30.0)

                with httpx.Client(timeout=timeout_config) as client:
                    with client.stream(
                        "POST",
                        f"{self.hhtech_base_url}/chat/completions",
                        json=payload,
                        headers=headers
                    ) as response:
                        if response.status_code != 200:
                            error_body = response.read().decode("utf-8", errors="replace")
                            raise ModelGatewayError(
                                f"HHTech API returned HTTP {response.status_code}: {error_body}"
                            )

                        for line in response.iter_lines():
                            line = line.strip()
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    choices = data.get("choices", [])
                                    if choices:
                                        delta_obj = choices[0].get("delta", {})
                                        delta_text = delta_obj.get("content", "")
                                        if delta_text:
                                            full_content.append(delta_text)
                                        reasoning_text = delta_obj.get("reasoning_content", "") or delta_obj.get("reasoning", "")
                                        if reasoning_text:
                                            full_reasoning.append(reasoning_text)
                                    usage = data.get("usage", {})
                                    if usage:
                                        total_tokens = usage.get("total_tokens", 0)
                                        details = usage.get("prompt_tokens_details") or {}
                                        cached_tokens = details.get("cached_tokens", 0)
                                        if cached_tokens > 0:
                                            logger.info(f"[GATEWAY] Prompt cache hit! {cached_tokens}/{usage.get('prompt_tokens', 0)} tokens served from cache.")
                                except Exception as e:
                                    logger.debug(f"[GATEWAY] Stream parse error: {e}")

                result = "".join(full_content)
                if not result.strip() and full_reasoning:
                    result = "".join(full_reasoning)
                if not result.strip():
                    raise ModelGatewayError("Empty response from HHTech API stream")
                stripped = result.strip()
                if stripped.startswith("[Error]") or stripped.startswith("Error:") or "error occurred while processing your request" in stripped.lower():
                    raise ModelGatewayError(f"HHTech stream returned backend error: {stripped[:200]}")
                break
            except (httpx.HTTPError, ModelGatewayError) as e:
                last_error = e
                logger.warning(f"[GATEWAY] HHTech attempt {attempt}/{max_retries} failed: {e}")
                if isinstance(e, ModelGatewayError) and any(s in str(e) for s in ["502", "503", "hết nguồn khả dụng", "backend error", "400", "BAD_REQUEST", "rejected a generation parameter", "invalid_request_error"]):
                    raise e
                if attempt < max_retries:
                    import time
                    time.sleep(attempt * 3.0)
                else:
                    raise last_error

        # Estimate tokens if not provided (rough: 1 token ≈ 4 chars)
        if total_tokens == 0:
            total_tokens = (len(prompt) + len(result)) // 4

        # Record cost AFTER successful call (passive telemetry)
        try:
            self.cost_tracker.record(model, total_tokens, is_image=False)
        except Exception as e:
            logger.debug(f"[GATEWAY] Cost tracking record info: {e}")

        return result

    def _call_fallback_llm(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> str:
        """Call fallback LLM provider. Routes to Anthropic direct if claude & key present, otherwise HHTech API."""
        if model.startswith("claude-") and self.anthropic_key:
            return self._call_anthropic(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout
            )
        elif self.hhtech_key:
            return self._call_hhtech(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout
            )
        elif model.startswith("claude-"):
            return self._call_anthropic(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout
            )
        else:
            raise ModelGatewayError(f"No configured provider available for fallback model: {model}")

    def _call_anthropic(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> str:
        """Call Anthropic API."""
        if not self.anthropic_key:
            raise ModelGatewayError("ANTHROPIC_API_KEY not configured for fallback")

        # 1. Authoritative Model & Context Window Validation (Fail-Closed)
        ctx_win = self.get_context_window(model)

        # 2. Pre-Flight Token Sanitizer & Context Headroom Guard
        est_tokens = int((len(prompt) + len(system_prompt or "")) / 2.5)
        combined_tokens = est_tokens + max_tokens
        if combined_tokens > ctx_win:
            err_msg = (
                f"Context Window Exceeded: Combined input estimate ({est_tokens} tokens) + "
                f"requested output ({max_tokens} tokens) = {combined_tokens} tokens "
                f"exceeds model '{model}' context window of {ctx_win} tokens."
            )
            logger.error(f"🛑 [CONTEXT EXCEEDED BLOCKED] {err_msg}")
            raise TokenBudgetExceeded(err_msg)

        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt

        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                raise ModelGatewayError(
                    f"Anthropic API returned HTTP {response.status_code}: {response.text}"
                )

            data = response.json()
            content = data.get("content", [{}])[0].get("text", "")
            usage = data.get("usage", {})
            total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            # Record cost
            self.cost_tracker.record(model, total_tokens, is_image=False)

            return content

    def call_vision(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.3,
        timeout: float = 90.0,
        fallback: Optional[str] = None
    ) -> str:
        """
        Call multimodal LLM with an image (base64) and text prompt.

        Args:
            prompt: Text prompt / evaluation instructions
            image_base64: Base64-encoded JPEG/PNG image data
            model: Model identifier (default: gpt-6.1-sol)
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            timeout: Request timeout in seconds
            fallback: Optional fallback model (e.g., "claude-sonnet-5")

        Returns:
            Generated text analysis / critique
        """
        model = model or "gpt-6.1-sol"
        try:
            logger.info(f"[GATEWAY] Calling vision model: {model}")
            return self._call_hhtech(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                image_base64=image_base64
            )
        except Exception as e:
            logger.warning(f"[GATEWAY] Vision model {model} failed: {e}")
            if fallback:
                logger.info(f"[GATEWAY] Trying fallback vision model: {fallback}")
                return self._call_hhtech(
                    prompt=prompt,
                    model=fallback,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                    image_base64=image_base64
                )
            raise

    def call_image(
        self,
        prompt: str,
        model: str = "imagen3",
        size: str = "1024x1024",
        count: int = 1,
        fallback: Optional[str] = None
    ) -> bytes:
        """
        Call image generation model with fallback.

        Args:
            prompt: Image description prompt
            model: Model identifier (default: imagen3)
            size: Image size (e.g., "1024x1024")
            count: Number of images to generate
            fallback: Optional fallback model

        Returns:
            Image bytes (or first image if count > 1)

        Raises:
            AllProvidersFailed: If primary and all fallbacks fail
        """
        # TODO: Implement image generation when needed
        # For now, raise NotImplementedError
        raise NotImplementedError(
            "Image generation through gateway not yet implemented. "
            "Use existing image_gen.py for now."
        )

    def get_cost_report(self, month: Optional[str] = None) -> Dict[str, float]:
        """Get cost breakdown for a month."""
        return self.cost_tracker.monthly_report(month)

    def get_remaining_budget(self) -> float:
        """Get remaining budget for current month."""
        return self.cost_tracker.get_remaining_budget()

    def get_budget_usage_pct(self) -> float:
        """Get budget usage percentage."""
        return self.cost_tracker.get_budget_usage_pct()


# Singleton instance for global access
_global_gateway: Optional[ModelGateway] = None


def get_global_gateway() -> ModelGateway:
    """Get or create the global model gateway instance."""
    global _global_gateway
    if _global_gateway is None:
        _global_gateway = ModelGateway()
    return _global_gateway
