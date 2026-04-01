import argparse
import json
import os
import re
import sys
import time

from config import ANTHROPIC_API_KEY
from generator import generate
from display import print_achievement
import archive


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
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all archived achievements",
    )
    parser.add_argument(
        "--replay",
        type=int,
        default=None,
        metavar="ID",
        help="Replay an archived achievement by ID (with audio)",
    )
    return parser.parse_args()


def _synthesize_achievement(achievement: dict) -> list[str]:
    """Pre-synthesize all audio pieces. Returns list of file paths."""
    from voice import synthesize

    desc = achievement["description"]
    audio_files = []

    # Split into: "New Achievement!" | body | "Your Reward!"
    opener = None
    body = desc
    closer = None

    opener_match = re.match(r"(New Achievement!)\s*(.*)", body, flags=re.IGNORECASE | re.DOTALL)
    if opener_match:
        opener = opener_match.group(1).strip()
        body = opener_match.group(2).strip()

    closer_match = re.split(r"(Your Reward!)\s*$", body, flags=re.IGNORECASE)
    if len(closer_match) >= 2:
        body = closer_match[0].strip()
        closer = closer_match[1].strip()

    title = achievement.get("title", "")

    if opener:
        audio_files.append(str(synthesize(opener, filename_hint="opener", gain_db=5.0)))
    if title:
        audio_files.append(str(synthesize(title, filename_hint="title", gain_db=3.0)))

    audio_files.append(str(synthesize(body, filename_hint="description", speed=1.15)))

    if closer:
        audio_files.append(str(synthesize(closer, filename_hint="your_reward", volume_ramp=True)))

    audio_files.append(str(synthesize(achievement["reward"], filename_hint="reward")))

    return audio_files


def _play_audio_sequence(audio_files: list[str]) -> None:
    """Play a pre-synthesized audio sequence with proper pauses."""
    from pathlib import Path
    from player import play

    # Sequence: opener, title, body, [closer], reward
    # Detect segments by filename hints
    for i, path in enumerate(audio_files):
        name = Path(path).name

        # Pause before title
        if "_title" in name:
            time.sleep(0.3)
            play(Path(path))
            time.sleep(0.4)
        # Pause before reward
        elif "_reward" in name:
            time.sleep(0.6)
            play(Path(path))
        else:
            play(Path(path))


def _list_achievements() -> None:
    """Display all archived achievements."""
    entries = archive.load_all()
    if not entries:
        print("\nNo achievements archived yet.\n")
        return

    print(f"\n  {'ID':>4}  {'Timestamp':<20} {'Title':<30} Trigger")
    print("  " + "─" * 78)
    for e in entries:
        ts = e["timestamp"][:19].replace("T", " ")
        title = e["title"][:28]
        trigger = (e.get("trigger") or "random")[:30]
        print(f"  {e['id']:>4}  {ts:<20} {title:<30} {trigger}")
    print()


def main() -> None:
    args = parse_args()

    # --list mode
    if args.list:
        _list_achievements()
        sys.exit(0)

    # --replay mode
    if args.replay is not None:
        entry = archive.get(args.replay)
        if not entry:
            print(f"\nNo achievement found with ID {args.replay}\n", file=sys.stderr)
            sys.exit(1)

        print_achievement(entry)

        if entry.get("audio_files"):
            # Replay cached audio
            existing = [f for f in entry["audio_files"] if os.path.exists(f)]
            if existing:
                _play_audio_sequence(existing)
            else:
                # Re-synthesize if audio files are gone
                audio_files = _synthesize_achievement(entry)
                _play_audio_sequence(audio_files)
        else:
            # No audio was ever generated — synthesize now
            if os.environ.get("ELEVENLABS_API_KEY"):
                audio_files = _synthesize_achievement(entry)
                _play_audio_sequence(audio_files)
            else:
                print("  (No audio — set ELEVENLABS_API_KEY to enable)\n")
        sys.exit(0)

    # Normal generation mode
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

    # Synthesize and play if requested
    audio_files = []
    if args.speak or args.speak_only:
        audio_files = _synthesize_achievement(achievement)
        _play_audio_sequence(audio_files)

    # Archive every generated achievement
    archive.save(
        achievement=achievement,
        trigger=args.trigger,
        audio_files=audio_files,
    )


if __name__ == "__main__":
    main()
