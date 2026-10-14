#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/codemap/test_hashing.py — Unit tests for canonical hashing and redaction."""

import pytest
from tools.codemap.hashing import canonical_json, sha256_of, flatten, field_hashes, redact


def test_key_order_independence():
    d1 = {"z": 100, "a": 1, "m": {"nested_b": 2, "nested_a": 1}}
    d2 = {"a": 1, "m": {"nested_a": 1, "nested_b": 2}, "z": 100}
    assert canonical_json(d1) == canonical_json(d2)
    assert sha256_of(d1) == sha256_of(d2)


def test_list_order_sensitivity():
    l1 = ["item1", "item2"]
    l2 = ["item2", "item1"]
    assert sha256_of(l1) != sha256_of(l2)


def test_redact_sensitive_keys():
    payload = {
        "user_id": "usr_123",
        "api_key": "sk-secret12345",
        "nested": {
            "bearer_token": "token-xyz",
            "password": "super-secret-password",
            "safe_data": "visible"
        }
    }
    redacted = redact(payload)
    assert redacted["api_key"] == "***"
    assert redacted["nested"]["bearer_token"] == "***"
    assert redacted["nested"]["password"] == "***"
    assert redacted["nested"]["safe_data"] == "visible"
    assert redacted["user_id"] == "usr_123"


def test_unicode_stability():
    vietnamese_payload = {
        "title": "Chiến lược Tiền tệ và Khủng hoảng Thuế Google tại Hàn Quốc",
        "scenes": ["Phân cảnh 1: Mở đầu kịch tính", "Phân cảnh 2: Dòng tiền luân chuyển"]
    }
    b1 = canonical_json(vietnamese_payload)
    b2 = canonical_json(vietnamese_payload)
    assert b1 == b2
    assert "Chiến lược" in b1.decode("utf-8")


def test_flatten_and_field_hashes():
    doc = {
        "scenes": [
            {"id": "sc_1", "duration": 5.0},
            {"id": "sc_2", "duration": 10.0}
        ]
    }
    flat = flatten(doc)
    assert flat["/scenes/0/id"] == "sc_1"
    assert flat["/scenes/0/duration"] == 5.0
    assert flat["/scenes/1/id"] == "sc_2"
    assert flat["/scenes/1/duration"] == 10.0

    f_hashes = field_hashes(doc)
    assert len(f_hashes) == 4
    assert "/scenes/0/id" in f_hashes
    assert isinstance(f_hashes["/scenes/0/id"], str)
    assert len(f_hashes["/scenes/0/id"]) == 64
