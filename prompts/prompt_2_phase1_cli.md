# Phase 1 — Claude Code Prompt
## CLI Generation Only (No Audio)

> Paste this into Claude Code to scaffold Phase 1 of the Satirical Achievement Reward System.

---

Build Phase 1 of a Satirical Achievement Reward System CLI. This is a multi-phase project. Build only Phase 1 now.

## Project Vision (context only — do not build phases 2–4 yet)

- Phase 1 (NOW): CLI that generates satirical achievements via Claude and prints them to terminal
- Phase 2: Add Coqui XTTS v2 local voice synthesis and audio playback
- Phase 3: Achievement archive (JSON log), audio caching, --list command
- Phase 4: Optional web UI or hotkey trigger

---

## Directory Structure

```
achievement_system/
├── main.py           # Entry point and CLI
├── generator.py      # Claude API achievement generation
├── config.py         # Env vars, constants, paths
├── display.py        # Terminal formatting and output
├── .env.example      # Template env file
└── README.md
```

---

## config.py

Load from environment variables using python-dotenv:
- `ANTHROPIC_API_KEY` (required)
- `MODEL` (default: `"claude-opus-4-5"`)
- `MAX_TOKENS` (default: `400`)

Use pathlib for all paths. Define project root as the directory containing main.py.

---

## generator.py

Use the Anthropic Python SDK.

Paste the announcer system prompt verbatim as the `system` parameter (see `prompt_1_announcer_system.md`).

Expose one function:

```python
def generate(trigger: str | None = None) -> dict:
    """
    Generate a satirical achievement.
    trigger: optional context string (e.g. "spilled coffee again")
    Returns dict with keys: title, description, reward
    """
```

- If `trigger` is None, user message is: `"Generate a random satirical achievement."`
- If `trigger` is provided, user message is: `f"Generate a satirical achievement for this event: {trigger}"`

Parse response as JSON. If parsing fails, retry once. If it fails again, raise a clear `ValueError` with the raw response included.

---

## display.py

Terminal formatting using only Python stdlib — no rich, no click, no curses.

Expose one function: `print_achievement(achievement: dict) -> None`

Format output using box-drawing characters:

```
╔══════════════════════════════════════════════════╗
║  ACHIEVEMENT UNLOCKED                            ║
╚══════════════════════════════════════════════════╝

  ★  Baptism by Arabica

  New Achievement! You have successfully hydrated your
  workspace AND your peripheral in a single fluid motion —
  a two-for-one that our judges are calling unprecedented.
  (The studio audience is on their feet.) Reward!

  REWARD  Unlocked: The Waterproof Keyboard You Should
          Have Bought Months Ago

──────────────────────────────────────────────────
```

Rules:
- Wrap description and reward text at 60 characters, preserving words
- No color escape codes — compatible with all terminals
- Fixed box width of 52 chars
- Blank line before and after the full block

---

## main.py

argparse CLI. Support these modes:

```bash
python main.py
# → Random achievement

python main.py --trigger "spilled coffee again"
# → Context-aware achievement

python main.py --trigger "spilled coffee again" --raw
# → Print raw JSON only (for piping into Phase 2)

python main.py --help
# → Clean usage message
```

Flow for normal mode:
1. Parse args
2. Call `generator.generate(trigger)`
3. Call `display.print_achievement(result)`
4. Exit 0

Handle exceptions gracefully:
- Missing `ANTHROPIC_API_KEY`: print clear setup message, exit 1
- API errors: print error, exit 1
- JSON parse failure: print raw response, exit 1

---

## .env.example

```
ANTHROPIC_API_KEY=your_key_here
MODEL=claude-opus-4-5
MAX_TOKENS=400
```

---

## README.md

Include:
- What this is and what Phase 1 does
- Setup: `python -m venv`, `pip install anthropic python-dotenv`, `cp .env.example .env`
- Usage examples for all three CLI modes
- Note that Phase 2 will add local voice synthesis via Coqui XTTS v2

---

## Constraints

- Python 3.10+
- Type hints throughout
- pathlib for all paths
- No third-party packages beyond `anthropic` and `python-dotenv`
- No async
- No audio, TTS, or pygame — that is Phase 2
- `--raw` output must be valid JSON suitable for piping
