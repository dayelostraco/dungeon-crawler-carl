"""
Achievement Intercom — Web UI Server

Usage:
    uvicorn server:app --reload
    Open http://localhost:8000
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import OUTPUT_DIR
from generator import generate
from main import _synthesize_achievement
import archive

app = FastAPI(title="Achievement Intercom")

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class GenerateRequest(BaseModel):
    trigger: str | None = None


def _audio_urls(audio_files: list[str]) -> list[str]:
    """Convert absolute file paths to /audio/{filename} URLs."""
    return [f"/audio/{Path(f).name}" for f in audio_files if f]


def _entry_response(entry: dict) -> dict:
    """Format an archive entry for the API response."""
    return {
        "id": entry["id"],
        "timestamp": entry["timestamp"],
        "title": entry["title"],
        "description": entry["description"],
        "reward": entry["reward"],
        "trigger": entry.get("trigger"),
        "audio_urls": _audio_urls(entry.get("audio_files", [])),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    achievement = generate(trigger=req.trigger)
    audio_files = _synthesize_achievement(achievement)
    entry = archive.save(
        achievement=achievement,
        trigger=req.trigger,
        audio_files=audio_files,
    )
    return _entry_response(entry)


@app.get("/api/achievements")
def api_achievements():
    entries = archive.load_all()
    return [_entry_response(e) for e in reversed(entries)]


@app.get("/api/achievements/{entry_id}")
def api_achievement(entry_id: int):
    entry = archive.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Achievement not found")

    # Re-synthesize if audio files are missing
    if entry.get("audio_files"):
        existing = [f for f in entry["audio_files"] if os.path.exists(f)]
        if not existing:
            audio_files = _synthesize_achievement(entry)
            entry["audio_files"] = audio_files

    return _entry_response(entry)


@app.get("/audio/{filename}")
def serve_audio(filename: str):
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path), media_type="audio/mpeg")
