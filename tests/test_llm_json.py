import pytest

from core.llm_json import parse_llm_json


def test_parse_llm_json_clean():
    raw = '{"status": "ok", "count": 42}'
    data = parse_llm_json(raw)
    assert data == {"status": "ok", "count": 42}


def test_parse_llm_json_markdown_wrapped():
    raw = "Here is the response:\n```json\n{\n  \"topic\": \"Reddit\"\n}\n```\nHope this helps!"
    data = parse_llm_json(raw)
    assert data == {"topic": "Reddit"}


def test_parse_llm_json_trailing_commas():
    raw = '{\n  "claims": [\n    {"id": "C001",},\n    {"id": "C002",},\n  ],\n}'
    data = parse_llm_json(raw)
    assert len(data["claims"]) == 2
    assert data["claims"][0]["id"] == "C001"


def test_parse_llm_json_comments():
    raw = '{\n  // This is a comment\n  "topic": "Google",\n  /* Multi-line\n     comment */\n  "active": true\n}'
    data = parse_llm_json(raw)
    assert data["topic"] == "Google"
    assert data["active"] is True


def test_parse_llm_json_empty_raises():
    with pytest.raises(ValueError):
        parse_llm_json("")
