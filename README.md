# Dungeon Crawler Carl — Achievement System

A snarky, AI-powered achievement reward system with voice synthesis. Give it a mundane life event, and it generates a biting achievement announcement — complete with title, description, and a reward that hits where it hurts. Optionally speaks it aloud using a cloned voice with robotic AI effects.

Inspired by the dungeon announcer from the *Dungeon Crawler Carl* book series.

---

## Project Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | CLI generation — achievements printed to terminal |
| 2 | ✅ Complete | ElevenLabs voice synthesis with AI audio effects |
| 3 | ✅ Complete | Achievement archive, audio caching, `--list`, `--replay` |
| 4 | ✅ Complete | Web UI via FastAPI + single-page app |

---

## Directory Structure

```
dungeon_crawler_carl/
├── main.py               # Entry point and CLI
├── generator.py          # Claude API achievement generation
├── config.py             # Env vars, constants, system prompt
├── display.py            # Terminal formatting
├── voice.py              # ElevenLabs TTS + AI audio effects
├── player.py             # Audio playback via pygame
├── archive.py            # Achievement history (JSON log + audio cache)
├── server.py             # FastAPI web server
├── static/index.html     # Web UI (single-page app)
├── finetune.py           # XTTS v2 fine-tuning script (experimental)
├── reference_audio/      # Voice reference samples (for fine-tuning)
├── transcripts/          # Transcript files (for fine-tuning)
├── output/               # Generated audio files
├── tests/                # Unit tests (43 tests)
├── .env.example          # Environment variable template
├── .gitignore
├── CHANGELOG.md
└── README.md
```

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/dayelostraco/dungeon-crawler-carl.git
cd dungeon-crawler-carl
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install anthropic python-dotenv elevenlabs pygame pedalboard numpy soundfile librosa fastapi "uvicorn[standard]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
ANTHROPIC_API_KEY=your_anthropic_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

### 4. ElevenLabs voice setup

Create a voice on [ElevenLabs](https://elevenlabs.io) by uploading your reference audio samples. Copy the voice ID and optionally set it in `.env`:

```
ELEVENLABS_VOICE_ID=your_voice_id_here
```

If not set, the system uses a default voice.

---

## Usage

### Generate a random achievement

```bash
python main.py
```

### Context-aware achievement

```bash
python main.py --trigger "spilled coffee on the keyboard again"
python main.py --trigger "pushed to production on a Friday at 4:59pm"
python main.py --trigger "forgot to mute on a zoom call"
```

### Speak achievement aloud

```bash
python main.py --speak
python main.py --trigger "took a 2 hour lunch and nobody noticed" --speak
```

### Audio only (no terminal output)

```bash
python main.py --speak-only
python main.py --trigger "accidentally replied-all to the entire company" --speak-only
```

### Browse achievement history

```bash
python main.py --list
```

### Replay a past achievement (with cached audio)

```bash
python main.py --replay 1
```

### Raw JSON output

```bash
python main.py --raw
python main.py --trigger "event" --raw
```

### Example terminal output

```
╔══════════════════════════════════════════════════╗
║  ACHIEVEMENT UNLOCKED                            ║
╚══════════════════════════════════════════════════╝

  ★  Corporate Houdini

  New Achievement! You vanished for 120 minutes and returned
  like nothing happened. (Nothing did — no one looks for you.)
  Your Reward!

  REWARD  Unlocked: The crushing realization that your absence
          changes absolutely nothing.

──────────────────────────────────────────────────
```

---

## Web UI (Phase 4)

A browser-based interface for generating and replaying achievements.

### Start the server

```bash
uvicorn server:app --reload
# Open http://localhost:8000
```

### Features

- Text input for trigger events with a Generate button
- Achievement card with game-style dark theme and gold accents
- Automatic audio playback in the browser with correct segment pauses
- Achievement history list — click any past achievement to replay it
- Loading indicator during the 8-15 second generation process

---

## Voice Synthesis (Phase 2)

Voice synthesis uses the [ElevenLabs API](https://elevenlabs.io) with a post-processing AI effect chain:

### Audio pipeline

1. Text is split into segments: **"New Achievement!"** | **title** | **body** | **"Your Reward!"** | **reward**
2. Each segment is synthesized via ElevenLabs with your cloned voice
3. AI effects are applied via [pedalboard](https://github.com/spotify/pedalboard):
   - **Chorus** — subtle doubling for synthetic shimmer
   - **Pitch shift** (-1.0 semitone) — slight deepening
   - **Bitcrush** (11-bit) — digital grit
   - **Reverb** — metallic AI-booth ambiance
4. Segment-specific processing:
   - **"New Achievement!"** — boosted +5dB
   - **Body** — played at 1.15x speed
   - **"Your Reward!"** — volume ramp from 40% to 220% (crescendo)
5. All segments pre-synthesized before playback for seamless delivery

### Audio caching

When `--speak` is used, synthesized audio files are cached in `output/` and linked to the achievement archive. Using `--replay` plays cached audio without re-calling the ElevenLabs API.

---

## Achievement Archive (Phase 3)

Every generated achievement is automatically saved to `achievements.json` with:
- Achievement title, description, and reward
- Trigger text (if provided)
- Timestamp
- Paths to cached audio files (if `--speak` was used)

Use `--list` to browse history and `--replay N` to replay any past achievement.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `ELEVENLABS_API_KEY` | For voice | — | ElevenLabs API key for TTS |
| `ELEVENLABS_VOICE_ID` | No | built-in default | ElevenLabs voice ID to use |
| `MODEL` | No | `claude-opus-4-5` | Claude model to use |
| `MAX_TOKENS` | No | `400` | Max tokens for generation |
| `OUTPUT_DIR` | No | `./output` | Audio output directory (set for EFS in container) |
| `ARCHIVE_FILE` | No | `./achievements.json` | Archive file path (set for EFS in container) |

---

## AWS Deployment

The app deploys to ECS Fargate behind an ALB using AWS CDK (Python).

### Architecture

```
Internet → ALB (HTTP) → ECS Fargate (0.5 vCPU, 1GB) → Container (uvicorn :8000)
                                                       ↳ EFS (/app/data — audio cache + archive)
                                                       ↳ Secrets Manager (API keys)
```

### Prerequisites

1. AWS account with CDK bootstrapped
2. Secrets created in Secrets Manager:
   - `achievement-intercom/anthropic-api-key`
   - `achievement-intercom/elevenlabs-api-key`
   - `achievement-intercom/elevenlabs-voice-id`

### Deploy

```bash
cd cdk
pip install -r requirements.txt
cdk bootstrap   # first time only
cdk deploy
```

CDK handles everything: builds the Docker image, pushes to ECR, creates VPC/ALB/EFS/ECS, and deploys.

### Local Docker test

```bash
docker build -t achievement-intercom .
docker run -p 8000:8000 --env-file .env achievement-intercom
# Open http://localhost:8000
```

---

## Development

### Run tests

```bash
pip install pytest pytest-mock
python -m pytest tests/ -v
```

### Fine-tuning (experimental)

A local XTTS v2 fine-tuning script is included for voice cloning experimentation:

```bash
python finetune.py --prepare   # Segment audio with Whisper
python finetune.py --train     # Fine-tune XTTS v2 model
python finetune.py --test      # Test fine-tuned model
```

Requires Python 3.11 and additional dependencies: `TTS`, `faster-whisper`, `torch<2.6`, `transformers>=4.40,<4.45`.
