import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
from pedalboard import Pedalboard, Chorus, Reverb, PitchShift, Gain, Bitcrush
from pedalboard.io import AudioFile

from elevenlabs.client import ElevenLabs

from config import OUTPUT_DIR

ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID: str = os.environ.get("ELEVENLABS_VOICE_ID", "dHd5gvgSOzSfduK4CvEg")

# Module-level singleton
_client: ElevenLabs | None = None

# AI voice effect chain — split the difference
_fx = Pedalboard([
    Chorus(rate_hz=2.0, depth=0.25, mix=0.4, centre_delay_ms=7.0),
    PitchShift(semitones=-1.0),
    Bitcrush(bit_depth=11),
    Reverb(room_size=0.25, damping=0.6, wet_level=0.2, dry_level=0.8),
])


def _get_client() -> ElevenLabs:
    """Return the cached ElevenLabs client."""
    global _client
    if _client is None:
        if not ELEVENLABS_API_KEY:
            raise EnvironmentError(
                "ELEVENLABS_API_KEY is not set. Add it to your environment."
            )
        _client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    return _client


def _slugify(text: str) -> str:
    """Turn a hint string into a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:40] if slug else "clip"


def _apply_ai_effect(input_path: Path, output_path: Path, volume_ramp: bool = False, speed: float = 1.0, gain_db: float = 0.0) -> None:
    """Apply robotic AI voice effect to an audio file. Outputs WAV for clean playback."""
    with AudioFile(str(input_path)) as f:
        audio = f.read(f.frames)
        sr = f.samplerate

    processed = _fx(audio, sr)

    if speed != 1.0:
        import librosa
        mono = processed[0] if processed.ndim > 1 else processed
        stretched = librosa.effects.time_stretch(mono, rate=speed)
        processed = stretched[np.newaxis, :]

    if gain_db != 0.0:
        gain_linear = 10 ** (gain_db / 20)
        processed = processed * gain_linear

    if volume_ramp:
        num_samples = processed.shape[1]
        ramp = np.linspace(0.4, 2.2, num_samples).astype(np.float32)
        processed = processed * ramp[np.newaxis, :]

    processed = np.clip(processed, -1.0, 1.0)

    # Write as WAV to avoid MP3 double-encoding artifacts
    mono = processed[0] if processed.ndim > 1 else processed
    sf.write(str(output_path), mono, sr, format="WAV")


def synthesize(text: str, filename_hint: str = "", volume_ramp: bool = False, speed: float = 1.0, gain_db: float = 0.0) -> Path:
    """
    Synthesize text using the ElevenLabs cloned voice with AI effect.
    text: the string to speak
    filename_hint: short slug used in the output filename
    volume_ramp: if True, audio builds from low to high volume
    speed: playback speed multiplier (1.0 = normal, 1.15 = slightly faster)
    Returns Path to the generated MP3 file in output/
    """
    client = _get_client()

    slug = _slugify(filename_hint) if filename_hint else "clip"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw_path = OUTPUT_DIR / f"{timestamp}_{slug}_raw.mp3"
    out_path = OUTPUT_DIR / f"{timestamp}_{slug}.wav"

    audio = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
    )

    with open(raw_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    _apply_ai_effect(raw_path, out_path, volume_ramp=volume_ramp, speed=speed, gain_db=gain_db)
    raw_path.unlink()  # clean up raw file

    return out_path
