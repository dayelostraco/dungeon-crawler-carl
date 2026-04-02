"""Tests for voice.py TTS expansion — specifically the parenthetical number
stripping added to fix double-reading of 'one (1)' etc."""

from voice import _expand_for_tts


def test_expand_parenthetical_number():
    assert _expand_for_tts("one (1) task") == "one task"


def test_expand_parenthetical_two_digit():
    assert _expand_for_tts("twenty (20) items") == "twenty items"


def test_expand_parenthetical_does_not_strip_text():
    """Non-numeric parentheticals should be preserved."""
    assert _expand_for_tts("(The sponsors are watching.)") == "(The sponsors are watching.)"


def test_expand_parenthetical_multiple():
    assert _expand_for_tts("one (1) crawler and two (2) mobs") == "one crawler and two mobs"


def test_expand_plus_and_parenthetical():
    """Combined: plus expansion + parenthetical stripping."""
    assert _expand_for_tts("+3 (3) to Stats") == "plus 3 to Stats"
