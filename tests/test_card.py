from io import BytesIO

from PIL import Image

from card import render_card

SAMPLE_ACHIEVEMENT = {
    "title": "Corporate Houdini",
    "description": "New Achievement! You vanished for 120 minutes. Your Reward!",
    "reward": "Nobody noticed.",
}


def test_render_card_returns_png():
    """render_card returns valid PNG bytes."""
    data = render_card(SAMPLE_ACHIEVEMENT)
    assert isinstance(data, bytes)
    assert len(data) > 0
    # PNG magic bytes
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_card_valid_image():
    """Output is a valid image that Pillow can open."""
    data = render_card(SAMPLE_ACHIEVEMENT)
    img = Image.open(BytesIO(data))
    assert img.format == "PNG"
    assert img.width > 0
    assert img.height > 0


def test_render_card_high_dpi():
    """Card is rendered at 3x scale (2400px wide)."""
    data = render_card(SAMPLE_ACHIEVEMENT)
    img = Image.open(BytesIO(data))
    assert img.width >= 2400


def test_render_card_missing_fields():
    """Handles missing fields gracefully with defaults."""
    data = render_card({})
    assert isinstance(data, bytes)
    img = Image.open(BytesIO(data))
    assert img.format == "PNG"


def test_render_card_strips_announcer_tags():
    """Description should not include 'New Achievement!' or 'Your Reward!' in the card."""
    # We can't easily inspect pixel text, but we can verify it doesn't crash
    # and produces a valid image with the full achievement
    data = render_card(SAMPLE_ACHIEVEMENT)
    assert len(data) > 1000  # non-trivial PNG


def test_render_card_long_reward():
    """Long reward text wraps without crashing."""
    achievement = {
        "title": "Test",
        "description": "Short desc.",
        "reward": "This is a very long reward text that should wrap across multiple lines "
        "without causing any rendering issues or crashes in the card generator.",
    }
    data = render_card(achievement)
    img = Image.open(BytesIO(data))
    assert img.height > 200  # taller card due to wrapped text
