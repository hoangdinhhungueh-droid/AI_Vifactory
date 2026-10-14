#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/codemap/test_handoff.py — Unit tests for inter-stage handoff boundary validation."""

from tools.codemap.handoff import analyze_handoff


def test_handoff_exact_match():
    schema_p = {
        "properties": {"topic": {"type": "string"}, "score": {"type": "number"}},
        "required": ["topic", "score"]
    }
    schema_c = {
        "properties": {"topic": {"type": "string"}, "score": {"type": "number"}},
        "required": ["topic"]
    }
    h = analyze_handoff("s1", "s2", "ModelP", "ModelC", schema_p, schema_c)
    assert h.status == "MATCH"
    assert len(h.issues) == 0


def test_handoff_partial_extra_ignored():
    schema_p = {
        "properties": {"topic": {"type": "string"}, "extra_field": {"type": "string"}},
        "required": ["topic"]
    }
    schema_c = {
        "properties": {"topic": {"type": "string"}},
        "required": ["topic"]
    }
    h = analyze_handoff("s1", "s2", "ModelP", "ModelC", schema_p, schema_c)
    assert h.status == "PARTIAL"
    assert len(h.issues) == 1
    assert h.issues[0].kind == "extra_ignored"
    assert h.issues[0].path == "/extra_field"


def test_handoff_mismatch_required_missing():
    schema_p = {
        "properties": {"topic": {"type": "string"}},
        "required": ["topic"]
    }
    schema_c = {
        "properties": {"topic": {"type": "string"}, "mandatory_id": {"type": "string"}},
        "required": ["topic", "mandatory_id"]
    }
    h = analyze_handoff("s1", "s2", "ModelP", "ModelC", schema_p, schema_c)
    assert h.status == "MISMATCH"
    assert any(i.kind == "required_not_provided" and i.path == "/mandatory_id" for i in h.issues)


def test_handoff_mismatch_type_conflict():
    schema_p = {
        "properties": {"duration": {"type": "string"}},
        "required": ["duration"]
    }
    schema_c = {
        "properties": {"duration": {"type": "number"}},
        "required": ["duration"]
    }
    h = analyze_handoff("s1", "s2", "ModelP", "ModelC", schema_p, schema_c)
    assert h.status == "MISMATCH"
    assert any(i.kind == "type_mismatch" and i.path == "/duration" for i in h.issues)
