import time
from pathlib import Path

import pygame


def _init_mixer() -> None:
    """Initialise pygame mixer if not already initialised."""
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def play(path: Path) -> None:
    """Play an audio file (WAV or MP3). Blocks until playback is complete."""
    _init_mixer()
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(50)


def play_with_pause(path1: Path, pause_seconds: float, path2: Path) -> None:
    """Play path1, pause, then play path2. Blocks until complete."""
    play(path1)
    time.sleep(pause_seconds)
    play(path2)
