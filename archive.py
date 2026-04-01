import json
from datetime import datetime
from pathlib import Path

from config import ARCHIVE_FILE


def save(achievement: dict, trigger: str | None = None, audio_files: list[str] | None = None) -> dict:
    """
    Append an achievement to the archive.
    Returns the saved entry (with id and timestamp).
    """
    entries = load_all()

    entry = {
        "id": len(entries) + 1,
        "timestamp": datetime.now().isoformat(),
        "title": achievement.get("title", ""),
        "description": achievement.get("description", ""),
        "reward": achievement.get("reward", ""),
        "trigger": trigger,
        "audio_files": audio_files or [],
    }

    entries.append(entry)

    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    return entry


def load_all() -> list[dict]:
    """Load all archived achievements."""
    if not ARCHIVE_FILE.exists():
        return []
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get(entry_id: int) -> dict | None:
    """Get a single achievement by ID."""
    for entry in load_all():
        if entry["id"] == entry_id:
            return entry
    return None
