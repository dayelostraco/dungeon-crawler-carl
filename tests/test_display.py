import io
import sys

from display import BOX_WIDTH, WRAP_WIDTH, _wrap, print_achievement

SAMPLE_ACHIEVEMENT = {
    "title": "Baptism by Arabica",
    "description": "New Achievement! You have successfully hydrated your workspace AND your peripheral in a single fluid motion. Reward!",
    "reward": "Unlocked: The Waterproof Keyboard You Should Have Bought Months Ago",
}


def _capture_output(achievement: dict) -> str:
    """Capture stdout from print_achievement."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        print_achievement(achievement)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


def test_output_contains_title():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "Baptism by Arabica" in output


def test_output_contains_description():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "New Achievement!" in output
    assert "Reward!" in output


def test_output_contains_reward():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "Waterproof Keyboard" in output


def test_output_contains_box_drawing():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "╔" in output
    assert "╗" in output
    assert "╚" in output
    assert "╝" in output
    assert "ACHIEVEMENT UNLOCKED" in output


def test_output_contains_star_prefix():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "★" in output


def test_output_contains_reward_label():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "REWARD" in output


def test_output_contains_divider():
    output = _capture_output(SAMPLE_ACHIEVEMENT)
    assert "─" * BOX_WIDTH in output


def test_missing_keys_use_defaults():
    output = _capture_output({})
    assert "Unknown Achievement" in output


def test_wrap_short_text():
    result = _wrap("Hello world")
    assert result == "Hello world"


def test_wrap_long_text():
    long_text = "word " * 30  # ~150 chars
    result = _wrap(long_text.strip())
    lines = result.split("\n")
    assert len(lines) > 1
    for line in lines:
        assert len(line.rstrip()) <= WRAP_WIDTH + 2  # indent allowance


def test_wrap_preserves_words():
    text = "achievement unlocked congratulations"
    result = _wrap(text, indent="  ")
    # No word should be split across lines
    assert "achievement" in result
    assert "unlocked" in result
    assert "congratulations" in result
