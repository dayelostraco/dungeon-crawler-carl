import json
from unittest.mock import MagicMock, patch

import pytest

SAMPLE_ACHIEVEMENT = {
    "title": "Baptism by Arabica",
    "description": "New Achievement! You hydrated your keyboard. Reward!",
    "reward": "+5 to Perceived Momentum",
}


def _mock_response(text: str) -> MagicMock:
    """Build a mock Anthropic response with the given text content."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@patch("generator.ANTHROPIC_API_KEY", "sk-test")
@patch("generator.anthropic.Anthropic")
def test_generate_with_trigger(mock_cls):
    """generate() with a trigger sends context-aware user message."""
    from generator import generate

    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = _mock_response(json.dumps(SAMPLE_ACHIEVEMENT))

    result = generate(trigger="spilled coffee")

    assert result == SAMPLE_ACHIEVEMENT
    call_kwargs = client.messages.create.call_args[1]
    assert "spilled coffee" in call_kwargs["messages"][0]["content"]


@patch("generator.ANTHROPIC_API_KEY", "sk-test")
@patch("generator.anthropic.Anthropic")
def test_generate_random(mock_cls):
    """generate() without a trigger sends a random-achievement message."""
    from generator import generate

    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = _mock_response(json.dumps(SAMPLE_ACHIEVEMENT))

    result = generate(trigger=None)

    assert result == SAMPLE_ACHIEVEMENT
    call_kwargs = client.messages.create.call_args[1]
    assert "random" in call_kwargs["messages"][0]["content"].lower()


@patch("generator.ANTHROPIC_API_KEY", "sk-test")
@patch("generator.anthropic.Anthropic")
def test_generate_retries_on_bad_json(mock_cls):
    """generate() retries once when the first response is not valid JSON."""
    from generator import generate

    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_response("this is not json"),
        _mock_response(json.dumps(SAMPLE_ACHIEVEMENT)),
    ]

    result = generate()
    assert result == SAMPLE_ACHIEVEMENT
    assert client.messages.create.call_count == 2


@patch("generator.ANTHROPIC_API_KEY", "sk-test")
@patch("generator.anthropic.Anthropic")
def test_generate_raises_after_two_failures(mock_cls):
    """generate() raises ValueError after two consecutive JSON parse failures."""
    from generator import generate

    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_response("bad json 1"),
        _mock_response("bad json 2"),
    ]

    with pytest.raises(ValueError, match="Failed to parse"):
        generate()


@patch("generator.ANTHROPIC_API_KEY", "")
def test_generate_missing_api_key():
    """generate() raises EnvironmentError when API key is empty."""
    from generator import generate

    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        generate()


@patch("generator.ANTHROPIC_API_KEY", "sk-test")
@patch("generator.anthropic.Anthropic")
def test_generate_uses_system_prompt(mock_cls):
    """generate() passes the system prompt to the API call."""
    from generator import generate

    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = _mock_response(json.dumps(SAMPLE_ACHIEVEMENT))

    generate()

    call_kwargs = client.messages.create.call_args[1]
    assert "Dungeon Intercom" in call_kwargs["system"]


@patch("generator.ANTHROPIC_API_KEY", "sk-test")
@patch("generator.anthropic.Anthropic")
def test_generate_passes_model_and_max_tokens(mock_cls):
    """generate() passes MODEL and MAX_TOKENS from config."""
    from generator import MAX_TOKENS, MODEL, generate

    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = _mock_response(json.dumps(SAMPLE_ACHIEVEMENT))

    generate()

    call_kwargs = client.messages.create.call_args[1]
    assert call_kwargs["model"] == MODEL
    assert call_kwargs["max_tokens"] == MAX_TOKENS
