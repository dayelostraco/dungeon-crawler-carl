# Achievement System

A satirical achievement reward system with AI-generated announcements in the style of a gleefully delusional gameshow host. Inspired by the dungeon announcer from the *Dungeon Crawler Carl* series.

---

## Project Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | CLI generation — achievements printed to terminal |
| 2 | ✅ Complete | Local voice synthesis via Coqui XTTS v2 + audio playback |
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
├── voice.py              # Coqui XTTS v2 voice synthesis
├── player.py             # Audio playback via pygame
├── reference_audio/      # Place your voice sample MP3s here
├── transcripts/          # Place your transcript TXT files here
├── output/               # Generated audio lands here
├── tests/                # Unit tests
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
pip install anthropic python-dotenv          # Phase 1 (CLI only)
pip install TTS pygame                       # Phase 2 (voice synthesis + playback)
```

> **Note:** Coqui TTS requires Python <3.12. Use Python 3.11 for full compatibility.

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

### Speak achievement aloud

```bash
python main.py --speak
python main.py --trigger "spilled coffee on the keyboard again" --speak
```

### Audio only (no terminal output)

```bash
python main.py --speak-only
python main.py --trigger "fixed a bug I introduced three weeks ago" --speak-only
```

### Raw JSON output (pipe-ready)

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

## Voice Synthesis (Phase 2)

Phase 2 adds local voice cloning via Coqui XTTS v2:

- **`voice.py`** — synthesizes text using your cloned voice from `reference_audio/reference.mp3`
- **`player.py`** — cross-platform audio playback via pygame
- **`--speak`** — generate + print + play audio (description, 0.6s pause, reward)
- **`--speak-only`** — audio only, no terminal output

### First run

The first time you use `--speak` or `--speak-only`, the XTTS v2 model (~2GB) will be downloaded automatically. This only happens once.

### Reference audio

Place your merged voice sample at `reference_audio/reference.mp3`. More audio = better voice cloning (30+ minutes recommended).

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key |
| `MODEL` | `claude-opus-4-5` | Claude model to use |
| `MAX_TOKENS` | `400` | Max tokens for generation |
