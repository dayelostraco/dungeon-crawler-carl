from voice import _expand_for_tts, _slugify


# --- _expand_for_tts ---


def test_expand_minus():
    assert _expand_for_tts("-7 to Dignity") == "minus 7 to Dignity"


def test_expand_plus():
    assert _expand_for_tts("+4 to Coworker Suspicion") == "plus 4 to Coworker Suspicion"


def test_expand_decimal():
    assert _expand_for_tts("-12.5 to Confidence") == "minus 12.5 to Confidence"


def test_expand_no_touch_hyphenated():
    """Hyphenated words like 'well-known' should NOT be expanded."""
    assert _expand_for_tts("well-known fact") == "well-known fact"


def test_expand_no_touch_plain_text():
    assert _expand_for_tts("No numbers here") == "No numbers here"


def test_expand_multiple():
    assert _expand_for_tts("+3 to A and -2 to B") == "plus 3 to A and minus 2 to B"


def test_expand_at_start():
    assert _expand_for_tts("+5 Charisma") == "plus 5 Charisma"


def test_expand_mid_sentence():
    assert _expand_for_tts("You gained -1 to Hope") == "You gained minus 1 to Hope"


# --- _slugify ---


def test_slugify_simple():
    assert _slugify("hello world") == "hello_world"


def test_slugify_special_chars():
    assert _slugify("Hello, World!") == "hello_world"


def test_slugify_truncates():
    long = "a" * 100
    assert len(_slugify(long)) == 40


def test_slugify_empty():
    assert _slugify("") == "clip"


def test_slugify_only_specials():
    assert _slugify("!!!") == "clip"


def test_slugify_preserves_numbers():
    assert _slugify("test 123") == "test_123"


def test_slugify_strips_leading_trailing():
    assert _slugify("  hello  ") == "hello"
