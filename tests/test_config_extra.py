"""Additional config tests — system prompt content validation."""

import importlib


def test_system_prompt_has_badge_list():
    """System prompt includes the badge icon list for Claude."""
    import config

    importlib.reload(config)
    assert "skull" in config.SYSTEM_PROMPT
    assert "coffee" in config.SYSTEM_PROMPT
    assert "trophy" in config.SYSTEM_PROMPT
    assert "ghost" in config.SYSTEM_PROMPT
    assert "badge" in config.SYSTEM_PROMPT.lower()


def test_system_prompt_has_reward_rules():
    """System prompt includes reward variation rules."""
    import config

    importlib.reload(config)
    assert "REWARD RULES" in config.SYSTEM_PROMPT
    assert "Vary the reward format" in config.SYSTEM_PROMPT


def test_system_prompt_has_voice_rules():
    """System prompt includes voice/TTS formatting rules."""
    import config

    importlib.reload(config)
    assert "New Achievement!" in config.SYSTEM_PROMPT
    assert "Your Reward!" in config.SYSTEM_PROMPT
    assert "VOICE RULES" in config.SYSTEM_PROMPT


def test_system_prompt_has_dcc_universe():
    """System prompt references DCC universe elements."""
    import config

    importlib.reload(config)
    assert "Dungeon Crawler Carl" in config.SYSTEM_PROMPT
    assert "crawler" in config.SYSTEM_PROMPT.lower()
    assert "Princess Donut" in config.SYSTEM_PROMPT


def test_default_model_is_sonnet():
    import config

    importlib.reload(config)
    assert "sonnet" in config.MODEL
