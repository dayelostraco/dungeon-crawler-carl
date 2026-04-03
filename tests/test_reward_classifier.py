"""Tests for reward format classifier."""

from reward_classifier import CATEGORIES, classify_reward


def test_loot():
    assert classify_reward("You've received a Cracked Mana Vial, 11% full.") == "loot"


def test_stat_boost():
    assert classify_reward("+3 to Perceived Competence, it will wear off.") == "stat_boost"
    assert classify_reward("-7 to Remaining Credibility") == "stat_boost"


def test_skill_unlock():
    assert (
        classify_reward(
            "You've unlocked the passive skill: Lingering in Doorways, no combat applications."
        )
        == "skill_unlock"
    )


def test_pet():
    assert (
        classify_reward("You've been assigned a Pet Menagerie entry: one (1) Sewer Snail, 2 HP.")
        == "pet"
    )


def test_quest():
    assert classify_reward("New Side Quest unlocked: Do Better, reward unknown.") == "quest"


def test_sponsor():
    assert (
        classify_reward(
            "This achievement brought to you by Desperado Pete's Discount Healing Potions."
        )
        == "sponsor"
    )


def test_system_message():
    assert (
        classify_reward("Your crawler rating has been adjusted. Do not inquire further.")
        == "system_message"
    )


def test_anti_reward():
    assert (
        classify_reward("None. You did the bare minimum and we do not want to reward that.")
        == "anti_reward"
    )


def test_borant_notice():
    assert (
        classify_reward("Borant Corporation has filed a notice of crawler underperformance.")
        == "borant_notice"
    )


def test_commentary_donut():
    assert (
        classify_reward("Princess Donut has reviewed your performance and found it 'adequate.'")
        == "commentary_donut"
    )


def test_commentary_mordecai():
    assert (
        classify_reward("Mordecai has been informed. He said, 'Yeah, that tracks.'")
        == "commentary_mordecai"
    )


def test_crafting_material():
    assert (
        classify_reward("You've received 4 units of Compressed Regret, tier-2 crafting material.")
        == "crafting_material"
    )


def test_care_package():
    assert (
        classify_reward("A viewer care package has arrived, one motivational poster.")
        == "care_package"
    )


def test_other_fallback():
    assert classify_reward("Something completely unexpected.") == "other"


def test_empty_string():
    assert classify_reward("") == "other"


def test_categories_list_complete():
    """All pattern categories plus 'other' should be in CATEGORIES."""
    assert "other" in CATEGORIES
    assert "loot" in CATEGORIES
    assert "stat_boost" in CATEGORIES
    assert len(CATEGORIES) == 14
