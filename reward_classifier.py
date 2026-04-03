"""
Reward format classifier — categorize reward text into format types.

Used for analytics (issue #28) and regression testing (issue #27).
"""

import re

# Reward format categories, ordered from most specific to least.
# Each entry: (category_name, compiled_regex_pattern)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pet", re.compile(r"pet menagerie|assigned a pet|sewer snail|cave slug", re.I)),
    ("sponsor", re.compile(r"brought to you by|sponsor|sponsored", re.I)),
    ("borant_notice", re.compile(r"borant corporation|borant", re.I)),
    ("commentary_donut", re.compile(r"princess donut", re.I)),
    ("commentary_mordecai", re.compile(r"mordecai", re.I)),
    ("quest", re.compile(r"side quest|new quest|quest unlocked", re.I)),
    ("care_package", re.compile(r"care package|viewer.*package", re.I)),
    ("anti_reward", re.compile(r"^none\b|do not want to reward|no reward", re.I)),
    (
        "system_message",
        re.compile(r"crawler rating|has been adjusted|do not inquire|filed a notice", re.I),
    ),
    ("skill_unlock", re.compile(r"unlocked the passive skill|skill:|passive skill", re.I)),
    ("crafting_material", re.compile(r"crafting material|units of", re.I)),
    ("stat_boost", re.compile(r"[+-]\d+\s+to\b", re.I)),
    ("loot", re.compile(r"you've received|received a|received an|you have received", re.I)),
]

CATEGORIES = [name for name, _ in _PATTERNS] + ["other"]


def classify_reward(reward_text: str) -> str:
    """Classify a reward string into a format category.

    Returns one of the CATEGORIES strings.
    """
    if not reward_text:
        return "other"
    for name, pattern in _PATTERNS:
        if pattern.search(reward_text):
            return name
    return "other"
