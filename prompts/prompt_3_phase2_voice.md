# Phase 2 — Claude Code Prompt
## Voice Synthesis and Audio Playback

> Run this in Claude Code after Phase 1 is complete and working. Do not modify Phase 1 files except `main.py` and `README.md`.

---

Build Phase 2 of the Satirical Achievement Reward System. Phase 1 is complete and working. Add local voice synthesis and audio playback. Do not modify Phase 1 files except main.py and README.md.

## What Phase 2 Adds

- `voice.py`: Coqui XTTS v2 voice cloning and synthesis
- `player.py`: cross-platform audio playback
- Two new CLI flags: `--speak` and `--speak-only`
- Reference audio support from `reference_audio/reference.mp3`

---

## Directory Changes

Add to existing structure:

```
achievement_system/
├── voice.py              # NEW — Coqui XTTS v2 synthesis
├── player.py             # NEW — audio playback
├── reference_audio/      # NEW dir — place reference.mp3 here
└── output/               # NEW dir — synthesized WAVs land here
```

---

## voice.py

Use Coqui XTTS v2: `tts_models/multilingual/multi-dataset/xtts_v2`

Reference audio lives at `reference_audio/reference.mp3`. On first run, convert to WAV if needed using the TTS library's built-in tooling — XTTS prefers WAV input.

Cache the loaded TTS model in memory as a module-level singleton so repeated calls within a session don't reload the ~2GB model.

Expose one function:

```python
def synthesize(text: str, filename_hint: str = "") -> Path:
    """
    Synthesize text using the cloned voice.
    text: the string to speak
    filename_hint: short slug used in the output filename
    Returns Path to the generated WAV file in output/
    """
```

Output filenames: `output/{timestamp}_{slug}.wav`

**IMPORTANT** — description and reward are synthesized as two separate calls:
- Call 1: the full description string (contains `"New Achievement!"` opener and `"Reward!"` closer)
- Call 2: the reward string

Callers handle the pause between them. `voice.py` just synthesizes what it's given.

Handle the case where XTTS model files haven't been downloaded — print a clear one-time message:

```
Downloading XTTS v2 model (~2GB) — this only happens once.
```

and let the download proceed.

---

## player.py

Use `pygame.mixer` for cross-platform playback.

Expose two functions:

```python
def play(path: Path) -> None:
    """Play a WAV file. Blocks until playback is complete."""

def play_with_pause(path1: Path, pause_seconds: float, path2: Path) -> None:
    """Play path1, pause, then play path2. Blocks until complete."""
```

The pause between description and reward should default to `0.6` seconds — long enough to land the "Reward!" beat before the reward text plays.

---

## main.py changes

Add two new flags to the existing argparse setup:

```bash
python main.py --speak
# Generate achievement, print to terminal, synthesize and play
# description + 0.6s pause + reward

python main.py --speak-only
# Same as --speak but suppress terminal output — audio only

python main.py --trigger "event" --speak
# Context-aware achievement with audio

python main.py --raw
# Unchanged — never triggers audio
```

Both `--speak` and `--speak-only` require `reference_audio/reference.mp3` to exist. If missing, print:

```
Reference audio not found. Place your voice sample at reference_audio/reference.mp3
```

and exit 1.

---

## Constraints

- No changes to `generator.py`, `config.py`, `display.py`, or `.env.example`
- New dependencies: `TTS` (Coqui), `pygame`
- Python 3.10+, type hints, pathlib throughout
- All output WAVs go in `output/` with timestamped filenames
- Model loading happens once per session — not per synthesis call

---

## README.md

Update to add a Phase 2 section:

- New dependencies: `pip install TTS pygame`
- Place reference audio at `reference_audio/reference.mp3`
- Note on first-run model download (~2GB, one time only)
- New usage examples for `--speak` and `--speak-only` flags
