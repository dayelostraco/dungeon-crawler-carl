import re
from datetime import datetime
from pathlib import Path

from TTS.api import TTS

from config import REFERENCE_AUDIO_DIR, OUTPUT_DIR

REFERENCE_MP3: Path = REFERENCE_AUDIO_DIR / "reference.mp3"
REFERENCE_WAV: Path = REFERENCE_AUDIO_DIR / "reference.wav"
MODEL_NAME: str = "tts_models/multilingual/multi-dataset/xtts_v2"

# Module-level singleton — loaded once per session
_tts: TTS | None = None


def _get_tts() -> TTS:
    """Return the cached TTS model, loading it on first call."""
    global _tts
    if _tts is None:
        print("Loading XTTS v2 model — this may take a moment...")
        _tts = TTS(model_name=MODEL_NAME)
    return _tts


def _ensure_reference_wav() -> Path:
    """Convert reference MP3 to WAV if the WAV doesn't exist yet."""
    if REFERENCE_WAV.exists():
        return REFERENCE_WAV
    if not REFERENCE_MP3.exists():
        raise FileNotFoundError(
            f"Reference audio not found. Place your voice sample at {REFERENCE_MP3}"
        )
    import soundfile as sf
    import librosa

    audio, sr = librosa.load(str(REFERENCE_MP3), sr=None)
    sf.write(str(REFERENCE_WAV), audio, sr)
    return REFERENCE_WAV


def _slugify(text: str) -> str:
    """Turn a hint string into a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:40] if slug else "clip"


def synthesize(text: str, filename_hint: str = "") -> Path:
    """
    Synthesize text using the cloned voice.
    text: the string to speak
    filename_hint: short slug used in the output filename
    Returns Path to the generated WAV file in output/
    """
    tts = _get_tts()
    ref_wav = _ensure_reference_wav()

    slug = _slugify(filename_hint) if filename_hint else "clip"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = OUTPUT_DIR / f"{timestamp}_{slug}.wav"

    tts.tts_to_file(
        text=text,
        speaker_wav=str(ref_wav),
        language="en",
        file_path=str(out_path),
    )
    return out_path
