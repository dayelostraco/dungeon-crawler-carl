import argparse
import json
import os
import sys

from config import ANTHROPIC_API_KEY
from generator import generate
from display import print_achievement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="achievement",
        description="Satirical Achievement Reward System",
    )
    parser.add_argument(
        "--trigger",
        type=str,
        default=None,
        metavar="EVENT",
        help='Context for the achievement (e.g. "spilled coffee again")',
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw JSON only — suitable for piping",
    )
    parser.add_argument(
        "--speak",
        action="store_true",
        help="Generate achievement, print to terminal, and play audio",
    )
    parser.add_argument(
        "--speak-only",
        action="store_true",
        help="Generate achievement and play audio only — no terminal output",
    )
    return parser.parse_args()


def _speak(achievement: dict) -> None:
    """Synthesize and play the achievement audio."""
    from voice import synthesize
    from player import play, play_with_pause
    import re

    desc = achievement["description"]

    # Split into: "New Achievement!" | body | "Your Reward!"
    opener = None
    body = desc
    closer = None

    # Extract opener
    opener_match = re.match(r"(New Achievement!)\s*(.*)", body, flags=re.IGNORECASE | re.DOTALL)
    if opener_match:
        opener = opener_match.group(1).strip()
        body = opener_match.group(2).strip()

    # Extract closer
    closer_match = re.split(r"(Your Reward!)\s*$", body, flags=re.IGNORECASE)
    if len(closer_match) >= 2:
        body = closer_match[0].strip()
        closer = closer_match[1].strip()

    title = achievement.get("title", "")

    # Pre-synthesize all pieces before playback
    opener_audio = synthesize(opener, filename_hint="opener", gain_db=5.0) if opener else None
    title_audio = synthesize(title, filename_hint="title", gain_db=3.0) if title else None
    body_audio = synthesize(body, filename_hint="description", speed=1.15)
    closer_audio = synthesize(closer, filename_hint="your_reward", volume_ramp=True) if closer else None
    reward_audio = synthesize(achievement["reward"], filename_hint="reward")

    # Play back: opener → pause → title → pause → body → closer → pause → reward
    import time

    if opener_audio:
        play(opener_audio)

    if title_audio:
        time.sleep(0.3)
        play(title_audio)
        time.sleep(0.4)

    play(body_audio)

    if closer_audio:
        play(closer_audio)

    time.sleep(0.6)
    play(reward_audio)


def main() -> None:
    args = parse_args()

    if not ANTHROPIC_API_KEY:
        print(
            "\nSetup required:\n"
            "  1. Copy .env.example to .env\n"
            "  2. Add your Anthropic API key\n"
            "  3. Run again\n",
            file=sys.stderr,
        )
        sys.exit(1)

    if (args.speak or args.speak_only) and not os.environ.get("ELEVENLABS_API_KEY"):
        print(
            "\nElevenLabs API key not found. "
            "Set ELEVENLABS_API_KEY in your environment.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        achievement = generate(trigger=args.trigger)
    except EnvironmentError as e:
        print(f"\nConfiguration error: {e}\n", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\nGeneration error: {e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAPI error: {e}\n", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        print(json.dumps(achievement, ensure_ascii=False))
        sys.exit(0)

    if not args.speak_only:
        print_achievement(achievement)

    if args.speak or args.speak_only:
        _speak(achievement)


if __name__ == "__main__":
    main()
