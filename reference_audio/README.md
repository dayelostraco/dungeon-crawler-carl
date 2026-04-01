# reference_audio/

Voice reference samples for fine-tuning and experimentation.

## Current usage

The primary voice synthesis pipeline uses **ElevenLabs API** — voice cloning is configured on the ElevenLabs platform, not from local files.

These reference audio files are used for:
- **XTTS v2 fine-tuning** (experimental, via `finetune.py`)
- Backup/archive of the original voice samples used to create the ElevenLabs voice

## Files

- Individual MP3 clips (timestamped filenames) — segments of the reference voice
- `reference.mp3` — merged file of all segments (~33 minutes)

## Notes

- Audio files are excluded from git via `.gitignore` (too large)
- This directory is committed but its contents are not — add your files locally
