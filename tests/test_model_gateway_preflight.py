"""tests/test_model_gateway_preflight.py — Verify Pre-Flight Token Sanitizer & Prompt Caching Header in ModelGateway."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.model_gateway import ModelGateway, ModelGatewayError


def test_model_gateway_preflight_blocks_bloat(monkeypatch):
    """Verify ModelGateway blocks massive token payload bloat (> ceiling)."""
    monkeypatch.setenv("HHTECH_API_KEY", "sk-test-key")
    gw = ModelGateway()
    massive_prompt = "A" * 100000  # ~25,000 tokens > 20,000 ceiling

    with pytest.raises(ModelGatewayError) as excinfo:
        gw._call_hhtech(prompt=massive_prompt, model="claude-opus-5-5")
    assert "Token Bloat Guard" in str(excinfo.value)
    assert "safety ceiling" in str(excinfo.value)


def test_model_gateway_preflight_allows_with_env_flag(monkeypatch):
    """Verify ALLOW_MASSIVE_LLM_CONTEXT=1 bypasses Pre-Flight Token Sanitizer check."""
    monkeypatch.setenv("HHTECH_API_KEY", "sk-test-key")
    monkeypatch.setenv("ALLOW_MASSIVE_LLM_CONTEXT", "1")
    gw = ModelGateway()
    massive_prompt = "A" * 100000

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = [
        'data: {"choices": [{"delta": {"content": "ok"}}]}',
        'data: [DONE]'
    ]

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__.return_value = mock_resp

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.stream.return_value = mock_stream_ctx
        mock_client_cls.return_value = mock_client

        res = gw._call_hhtech(prompt=massive_prompt, model="claude-opus-5-5")
        assert res == "ok"


def test_model_gateway_claude_prompt_caching_header(monkeypatch):
    """Verify prompt-caching header is injected for Claude models."""
    monkeypatch.setenv("HHTECH_API_KEY", "sk-test-key")
    gw = ModelGateway()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = [
        'data: {"choices": [{"delta": {"content": "cached ok"}}]}',
        'data: [DONE]'
    ]

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__.return_value = mock_resp

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.stream.return_value = mock_stream_ctx
        mock_client_cls.return_value = mock_client

        gw._call_hhtech(prompt="Short test prompt", model="claude-opus-5-5")
        _, kwargs = mock_client.stream.call_args
        headers = kwargs.get("headers", {})
        assert headers.get("anthropic-beta") == "prompt-caching-2024-07-31"
