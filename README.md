# Achievement System

A satirical achievement reward system with AI-generated announcements in the style of a gleefully delusional gameshow host. Inspired by the dungeon announcer from the *Dungeon Crawler Carl* series.

---

## Project Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Current | CLI generation — achievements printed to terminal |
| 2 | Planned | Local voice synthesis via Coqui XTTS v2 + audio playback |
| 3 | Planned | Achievement archive, audio caching, `--list` command |
| 4 | Planned | Web UI or global hotkey trigger |

---

## Directory Structure

```
achievement_system/
├── main.py               # Entry point and CLI
├── generator.py          # Claude API achievement generation
├── config.py             # Env vars, constants, system prompt
├── display.py            # Terminal formatting
├── reference_audio/      # Place your voice sample MP3s here
├── transcripts/          # Place your transcript TXT files here
├── output/               # Generated audio lands here (Phase 2)
├── .env.example          # Environment variable template
├── .gitignore
└── README.md
```

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd achievement_system
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install anthropic python-dotenv
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_key_here
```

### 4. Add reference audio and transcripts

Drop your MP3 files into `reference_audio/` and transcript TXT files into `transcripts/`. These will be used in Phase 2 for voice cloning.

---

## Usage

### Random achievement

```bash
python main.py
```

### Context-aware achievement

```bash
python main.py --trigger "spilled coffee on the keyboard again"
python main.py --trigger "fixed a bug I introduced three weeks ago"
python main.py --trigger "attended a meeting that could have been an email"
```

### Raw JSON output (pipe-ready for Phase 2)

```bash
python main.py --raw
python main.py --trigger "pushed to main without testing" --raw
```

### Example terminal output

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

---

## Phase 2 Preview

Phase 2 will add:

- `voice.py` — Coqui XTTS v2 local voice cloning using your `reference_audio/` samples
- `player.py` — cross-platform audio playback via pygame
- `--speak` flag — generate + print + play audio announcement
- `--speak-only` flag — audio only, no terminal output

The `--raw` flag output from Phase 1 is designed to pipe directly into the Phase 2 voice synthesizer.

First run in Phase 2 will download the XTTS v2 model (~2GB, one time only).

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key |
| `MODEL` | `claude-opus-4-5` | Claude model to use |
| `MAX_TOKENS` | `400` | Max tokens for generation |
