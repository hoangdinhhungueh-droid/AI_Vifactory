"""
tests/test_gate1_order_guard.py

Tests for Human Gate 1 dispatch constraints:
1. Anti-Out-of-Order: Refuse dispatch if B3 Director Plan / HG2 visual convergence already exists.
2. Fact Audit Strict Enforcement: Refuse dispatch if fact_audit_score < 7.5 or fact_audit_passed is False.
3. Successful dispatch when all constraints pass.
"""

import os
import pytest
from unittest.mock import patch
import app.services.telegram_buttons
from app.services.trend_engine_b1 import send_pure_telegram_gate1_notification


def test_gate1_blocked_if_director_plan_exists():
    """Test Gate 1 is blocked if director_plan.json exists in episode directory."""
    task_id = "JP_EP0099_test_order_guard"

    topic_data = {
        "task_id": task_id,
        "market": "JP",
        "raw_term": "テストニュース",
        "fact_audit_score": 9.0,
        "fact_audit_passed": True,
    }

    def fake_exists(p):
        if "director_plan.json" in str(p):
            return True
        return False

    with patch("app.services.telegram_buttons.send_telegram_broadcast") as mock_send, \
         patch("os.path.exists", side_effect=fake_exists):
        send_pure_telegram_gate1_notification(topic_data)
        # MUST BE BLOCKED: send_telegram_broadcast should NOT be called
        assert not mock_send.called, "Human Gate 1 was dispatched despite B3 director plan existing!"


def test_gate1_blocked_if_fact_audit_below_threshold():
    """Test Gate 1 is blocked if fact audit score < 7.5."""
    task_id = "JP_EP0099_test_low_score"
    topic_data = {
        "task_id": task_id,
        "market": "JP",
        "raw_term": "低スコアニュース",
        "fact_audit_score": 7.4,
        "fact_audit_passed": None,
    }

    with patch("app.services.telegram_buttons.send_telegram_broadcast") as mock_send, \
         patch("os.path.exists", return_value=False):
        send_pure_telegram_gate1_notification(topic_data)
        assert not mock_send.called, "Human Gate 1 was dispatched despite fact score < 7.5!"


def test_gate1_blocked_if_fact_audit_explicitly_failed():
    """Test Gate 1 is blocked if fact_audit_passed is False even if score is high."""
    task_id = "JP_EP0099_test_explicit_fail"
    topic_data = {
        "task_id": task_id,
        "market": "JP",
        "raw_term": "不合格ニュース",
        "fact_audit_score": 8.5,
        "fact_audit_passed": False,
    }

    with patch("app.services.telegram_buttons.send_telegram_broadcast") as mock_send, \
         patch("os.path.exists", return_value=False):
        send_pure_telegram_gate1_notification(topic_data)
        assert not mock_send.called, "Human Gate 1 was dispatched despite fact_audit_passed=False!"


def test_gate1_allowed_when_clean():
    """Test Gate 1 dispatches successfully when score >= 7.5 and no B3 artifacts exist."""
    task_id = "JP_EP0099_test_pass"
    topic_data = {
        "task_id": task_id,
        "market": "JP",
        "raw_term": "合格ニュース",
        "fact_audit_score": 8.5,
        "fact_audit_passed": True,
        "viability_score": 9.0,
    }

    with patch("app.services.telegram_buttons.send_telegram_broadcast", return_value=12345) as mock_send, \
         patch("os.path.exists", return_value=False):
        send_pure_telegram_gate1_notification(topic_data)
        assert mock_send.called, "Human Gate 1 was not dispatched when all constraints were satisfied!"
        call_msg = mock_send.call_args[0][0]
        assert "PASS (8.5/10)" in call_msg
        assert task_id in call_msg
