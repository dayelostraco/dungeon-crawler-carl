import argparse
import json
import sys

from config import ANTHROPIC_API_KEY, REFERENCE_AUDIO_DIR
from generator import generate
from display import print_achievement

REFERENCE_MP3 = REFERENCE_AUDIO_DIR / "reference.mp3"


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
    from player import play_with_pause

    desc_wav = synthesize(achievement["description"], filename_hint="description")
    reward_wav = synthesize(achievement["reward"], filename_hint="reward")
    play_with_pause(desc_wav, 0.6, reward_wav)


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

    if (args.speak or args.speak_only) and not REFERENCE_MP3.exists():
        print(
            "\nReference audio not found. "
            f"Place your voice sample at {REFERENCE_MP3}\n",
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
