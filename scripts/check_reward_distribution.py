#!/usr/bin/env python3
"""
Prompt regression test — reward format distribution checker.

Generates N achievements and validates:
  1. No single reward format dominates (>40% of total)
  2. Numbers in descriptions don't repeat excessively
  3. Banned numbers (47, 847) never appear

Usage:
    python scripts/check_reward_distribution.py            # 10 samples (default)
    python scripts/check_reward_distribution.py --count 20  # 20 samples
    python scripts/check_reward_distribution.py --dry-run   # parse existing DB instead

Exit code 0 = pass, 1 = fail.
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reward_classifier import classify_reward

BANNED_NUMBERS = {47, 847}
MAX_FORMAT_SHARE = 0.40  # No format should exceed 40%
MAX_NUMBER_REPEAT = 3  # Same number shouldn't appear more than 3 times across N samples


def extract_numbers(text: str) -> list[int]:
    """Extract all integers from text."""
    return [int(n) for n in re.findall(r"\b\d+\b", text)]


def generate_samples(count: int) -> list[dict]:
    """Generate fresh achievements via the Claude API."""
    from generator import generate

    samples = []
    for i in range(count):
        print(f"  Generating {i + 1}/{count}...", flush=True)
        try:
            samples.append(generate())
        except Exception as e:
            print(f"  WARNING: Generation {i + 1} failed: {e}")
    return samples


def load_from_db() -> list[dict]:
    """Load existing achievements from the local archive."""
    import archive

    return archive.load_all()


def check_distribution(samples: list[dict]) -> list[str]:
    """Run all checks. Returns list of failure messages (empty = pass)."""
    failures = []

    if not samples:
        failures.append("No samples to check")
        return failures

    # 1. Reward format distribution
    formats = [classify_reward(s.get("reward", "")) for s in samples]
    format_counts = Counter(formats)
    total = len(formats)

    print(f"\n  Reward format distribution ({total} samples):")
    for fmt, count in format_counts.most_common():
        pct = count / total * 100
        marker = " <<<" if pct > MAX_FORMAT_SHARE * 100 else ""
        print(f"    {fmt:25s} {count:3d} ({pct:5.1f}%){marker}")

    for fmt, count in format_counts.items():
        share = count / total
        if share > MAX_FORMAT_SHARE:
            failures.append(
                f"Format '{fmt}' dominates at {share:.0%} ({count}/{total}), "
                f"max allowed is {MAX_FORMAT_SHARE:.0%}"
            )

    # 2. Number repetition
    all_numbers: list[int] = []
    for s in samples:
        text = f"{s.get('description', '')} {s.get('reward', '')}"
        all_numbers.extend(extract_numbers(text))

    number_counts = Counter(all_numbers)
    repeated = {n: c for n, c in number_counts.items() if c > MAX_NUMBER_REPEAT}
    if repeated:
        for n, c in repeated.items():
            failures.append(f"Number {n} repeated {c} times (max {MAX_NUMBER_REPEAT})")
        print(f"\n  Repeated numbers: {repeated}")
    else:
        print(f"\n  Number variety: OK (no number repeated >{MAX_NUMBER_REPEAT}x)")

    # 3. Banned numbers
    for s in samples:
        text = f"{s.get('description', '')} {s.get('reward', '')}"
        found_banned = BANNED_NUMBERS & set(extract_numbers(text))
        if found_banned:
            title = s.get("title", "?")
            failures.append(f"Banned number(s) {found_banned} found in '{title}'")

    banned_total = sum(
        1
        for s in samples
        if BANNED_NUMBERS
        & set(extract_numbers(f"{s.get('description', '')} {s.get('reward', '')}"))
    )
    if banned_total:
        print(f"  Banned numbers: FAIL ({banned_total} samples contain 47 or 847)")
    else:
        print("  Banned numbers: OK")

    return failures


def main():
    parser = argparse.ArgumentParser(description="Check reward format distribution")
    parser.add_argument("--count", type=int, default=10, help="Number of samples to generate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check existing DB entries instead of generating new ones",
    )
    args = parser.parse_args()

    print("Reward Format Distribution Check")
    print("=" * 40)

    if args.dry_run:
        print("  Mode: dry-run (checking existing DB)")
        samples = load_from_db()
    else:
        print(f"  Mode: generate ({args.count} samples)")
        samples = generate_samples(args.count)

    failures = check_distribution(samples)

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("PASSED: All checks OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
