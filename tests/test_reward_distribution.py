"""Tests for the reward distribution checker logic."""

import sys
from pathlib import Path

# Allow imports from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_reward_distribution import check_distribution, extract_numbers


def _make_sample(reward: str, description: str = "New Achievement! Test. Your Reward!") -> dict:
    return {"title": "Test", "description": description, "reward": reward}


def test_extract_numbers():
    assert extract_numbers("You scored 42 points in 3 rounds") == [42, 3]
    assert extract_numbers("no numbers here") == []


def test_passes_with_varied_formats():
    """Distribution check passes when formats are varied."""
    samples = [
        _make_sample("You've received a Cracked Mana Vial."),
        _make_sample("+3 to Perceived Competence."),
        _make_sample("You've unlocked the passive skill: Loitering."),
        _make_sample("You've been assigned a Pet Menagerie entry: one snail."),
        _make_sample("New Side Quest unlocked: Do Better."),
    ]
    failures = check_distribution(samples)
    assert failures == []


def test_fails_when_single_format_dominates():
    """Distribution check fails when one format exceeds 40%."""
    samples = [
        _make_sample("You've received a thing."),
        _make_sample("You've received another thing."),
        _make_sample("You've received yet another thing."),
        _make_sample("+3 to Competence."),
        _make_sample("Quest unlocked: whatever."),
    ]
    failures = check_distribution(samples)
    assert any("dominates" in f for f in failures)


def test_fails_on_banned_numbers():
    """Distribution check fails when 47 or 847 appear."""
    samples = [
        _make_sample("You scored 47 points.", "New Achievement! You did 47 things. Your Reward!"),
        _make_sample("+3 to Competence."),
        _make_sample("Quest unlocked: whatever."),
    ]
    failures = check_distribution(samples)
    assert any("Banned" in f or "47" in f for f in failures)


def test_fails_on_repeated_numbers():
    """Distribution check fails when a number repeats too many times."""
    samples = [
        _make_sample("You scored 99 points.", "New Achievement! 99 crawlers. Your Reward!"),
        _make_sample("+99 to Competence.", "New Achievement! Floor 99. Your Reward!"),
        _make_sample("Quest 99 unlocked.", "New Achievement! Test. Your Reward!"),
    ]
    # 99 appears 5 times across all samples — exceeds MAX_NUMBER_REPEAT (3)
    failures = check_distribution(samples)
    assert any("99" in f and "repeated" in f for f in failures)


def test_empty_samples():
    failures = check_distribution([])
    assert any("No samples" in f for f in failures)
