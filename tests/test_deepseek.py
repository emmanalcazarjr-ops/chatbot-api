"""Unit tests for the DeepSeek client helpers (no network access)."""

from shared.deepseek import call_deepseek_with_messages, parse_json_response


def test_call_fails_cleanly_without_api_key():
    # conftest removed DEEPSEEK_API_KEY from the environment
    result = call_deepseek_with_messages([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert "not configured" in result["error"]


def test_parse_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_fenced_json():
    content = "Here you go:\n```json\n{\"a\": [1, 2]}\n```\nDone."
    assert parse_json_response(content) == {"a": [1, 2]}


def test_parse_json_embedded_in_prose():
    content = 'The answer is {"b": true} as requested.'
    assert parse_json_response(content) == {"b": True}


def test_parse_invalid_returns_raw_response():
    out = parse_json_response("no json at all")
    assert out == {"raw_response": "no json at all"}
