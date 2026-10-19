# tests/unit/test_model_gateway_ceiling.py
"""Unit tests for bounded MAX_ABSOLUTE_INPUT_CEILING configuration (Rule 138 & Rule 139).
Tests bounded normalization without using any test doubles.
"""

from app.services.model_gateway import _get_max_absolute_input_ceiling


def test_default_ceiling_when_env_unset(monkeypatch):
    """Verifies default ceiling is 120,000 tokens when env var is unset."""
    monkeypatch.delenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", raising=False)
    assert _get_max_absolute_input_ceiling() == 120000


def test_custom_valid_ceiling(monkeypatch):
    """Verifies custom value within valid range [1000, 200000] is accepted."""
    monkeypatch.setenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "85000")
    assert _get_max_absolute_input_ceiling() == 85000


def test_ceiling_clamped_to_minimum(monkeypatch):
    """Verifies values below 1000 tokens are clamped to minimum 1000."""
    monkeypatch.setenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "500")
    assert _get_max_absolute_input_ceiling() == 1000
    monkeypatch.setenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "-5000")
    assert _get_max_absolute_input_ceiling() == 1000


def test_ceiling_clamped_to_maximum(monkeypatch):
    """Verifies values above 200,000 tokens are clamped to safety cap 200,000."""
    monkeypatch.setenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "500000")
    assert _get_max_absolute_input_ceiling() == 200000


def test_invalid_non_numeric_fallback(monkeypatch):
    """Verifies non-numeric values gracefully fallback to default 120,000."""
    monkeypatch.setenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "invalid_number")
    assert _get_max_absolute_input_ceiling() == 120000
    monkeypatch.setenv("HHTECH_MAX_ABSOLUTE_INPUT_CEILING", "")
    assert _get_max_absolute_input_ceiling() == 120000
