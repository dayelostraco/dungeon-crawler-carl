import argparse
import json
import sys

from config import ANTHROPIC_API_KEY
from generator import generate
from display import print_achievement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="achievement",
        description="Satirical Achievement Reward System — Phase 1 CLI",
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
        help="Print raw JSON only — suitable for piping into Phase 2",
    )
    return parser.parse_args()


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

    print_achievement(achievement)


if __name__ == "__main__":
    main()
