# app/services/model_gateway.py
"""
Model Gateway for VF Pipeline - Pattern 3 Implementation.
Centralizes all model API calls with:
  - Automatic cost tracking and telemetry
  - Provider fallback support (HHTech → Anthropic)
  - A/B testing capability
  - Unified error handling
"""

import os
import json
import logging
import httpx
from typing import Optional, Dict, Any, List
from enum import Enum

from app.services.cost_tracker import get_global_tracker, CostCapExceededError

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Model category types."""
    LLM = "llm"
    IMAGE = "image"
    AUDIO = "audio"


class ModelGatewayError(Exception):
    """Base exception for model gateway errors."""
    pass


class AllProvidersFailed(ModelGatewayError):
    """Raised when primary and all fallback providers fail."""
    pass


class ModelGateway:
    """
    Centralized gateway for all model API calls.
    
    Features:
    - Cost tracking and telemetry
    - Automatic fallback to secondary providers
    - Standardized error handling
    - Request/response logging
    """
    
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
        self.hhtech_model = os.getenv("HHTECH_MODEL", "gpt-6-astra")
        
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
            model: Model identifier (default: gpt-6-astra)
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
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> str:
        """Call HHTech API (primary provider) with automatic retry on streaming ReadTimeout."""
        if not self.hhtech_key:
            raise ModelGatewayError("HHTECH_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {self.hhtech_key}",
            "Content-Type": "application/json"
        }
        
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
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
                                    delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        full_content.append(delta)
                                    usage = data.get("usage", {})
                                    if usage:
                                        total_tokens = usage.get("total_tokens", 0)
                                except Exception as e:
                                    logger.debug(f"[GATEWAY] Stream parse error: {e}")
                
                result = "".join(full_content)
                if not result.strip():
                    raise ModelGatewayError("Empty response from HHTech API stream")
                stripped = result.strip()
                if stripped.startswith("[Error]") or stripped.startswith("Error:") or "error occurred while processing your request" in stripped.lower():
                    raise ModelGatewayError(f"HHTech stream returned backend error: {stripped[:200]}")
                break
            except (httpx.HTTPError, ModelGatewayError) as e:
                last_error = e
                logger.warning(f"[GATEWAY] HHTech attempt {attempt}/{max_retries} failed: {e}")
                if isinstance(e, ModelGatewayError) and any(s in str(e) for s in ["503", "hết nguồn khả dụng", "backend error", "400", "BAD_REQUEST", "rejected a generation parameter", "invalid_request_error"]):
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
        
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
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
