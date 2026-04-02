import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

SAMPLE_ACHIEVEMENT = {
    "title": "Corporate Houdini",
    "description": "New Achievement! You vanished for 120 minutes. Your Reward!",
    "reward": "Unlocked: Nobody noticed.",
}

SAMPLE_ARCHIVE_ENTRY = {
    "id": 1,
    "timestamp": "2026-04-01T15:00:00",
    "title": "Corporate Houdini",
    "description": "New Achievement! You vanished for 120 minutes. Your Reward!",
    "reward": "Unlocked: Nobody noticed.",
    "trigger": "took a long lunch",
    "audio_files": [],
}


@pytest.fixture
def tmp_archive(tmp_path, monkeypatch):
    """Redirect archive to temp SQLite DB."""
    db_path = tmp_path / "test.db"
    import config

    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "STORAGE_MODE", "local")

    import importlib

    import archive

    archive._DB_INIT = False
    importlib.reload(archive)
    return db_path


@pytest.fixture
def client(tmp_archive):
    """TestClient with isolated archive."""
    from server import app

    return TestClient(app)


def _parse_sse(text):
    """Parse SSE response text into a dict of {event_name: data_dict}."""
    events = {}
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event, data = "", ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line[7:]
            if line.startswith("data: "):
                data = line[6:]
        if event and data:
            events[event] = json.loads(data)
    return events


@patch("server.synthesize_achievement_parallel", return_value=[])
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_generate_returns_achievement(mock_gen, mock_synth, client):
    """POST /api/generate streams achievement data via SSE."""
    res = client.post("/api/generate", json={"trigger": "took a long lunch"})
    assert res.status_code == 200
    events = _parse_sse(res.text)
    assert "achievement" in events
    assert events["achievement"]["title"] == "Corporate Houdini"
    assert events["achievement"]["trigger"] == "took a long lunch"
    assert "id" in events["achievement"]
    assert "audio" in events
    assert "done" in events


@patch("server.synthesize_achievement_parallel", return_value=[])
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_generate_without_trigger(mock_gen, mock_synth, client):
    """POST /api/generate works with null trigger."""
    res = client.post("/api/generate", json={})
    assert res.status_code == 200
    events = _parse_sse(res.text)
    assert events["achievement"]["trigger"] is None


@patch("server.synthesize_achievement_parallel", return_value=[])
@patch("server.generate", side_effect=ValueError("parse failed"))
def test_generate_claude_error(mock_gen, mock_synth, client):
    """POST /api/generate returns 502 on Claude API failure."""
    res = client.post("/api/generate", json={"trigger": "test"})
    assert res.status_code == 502
    assert "Generation failed" in res.json()["detail"]


@patch("server.synthesize_achievement_parallel", return_value=[])
@patch("server.generate", side_effect=OSError("no key"))
def test_generate_config_error(mock_gen, mock_synth, client):
    """POST /api/generate returns 500 on missing config."""
    res = client.post("/api/generate", json={"trigger": "test"})
    assert res.status_code == 500
    assert "Configuration error" in res.json()["detail"]


@patch("server.synthesize_achievement_parallel", side_effect=Exception("ElevenLabs down"))
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_generate_synthesis_failure_still_returns(mock_gen, mock_synth, client):
    """POST /api/generate streams achievement even if synthesis fails."""
    res = client.post("/api/generate", json={"trigger": "test"})
    assert res.status_code == 200
    events = _parse_sse(res.text)
    assert events["achievement"]["title"] == "Corporate Houdini"
    assert events["audio"]["audio_urls"] == []


@patch("server.synthesize_achievement_parallel", return_value=[])
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_achievements_list(mock_gen, mock_synth, client):
    """GET /api/achievements returns paginated entries."""
    client.post("/api/generate", json={"trigger": "first"})
    client.post("/api/generate", json={"trigger": "second"})

    res = client.get("/api/achievements")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 0
    assert data["total_pages"] == 1
    # Most recent first
    assert data["items"][0]["trigger"] == "second"
    assert data["items"][1]["trigger"] == "first"


@patch("server.synthesize_achievement_parallel", return_value=[])
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_achievements_list_pagination(mock_gen, mock_synth, client):
    """GET /api/achievements respects page and page_size params."""
    for i in range(3):
        client.post("/api/generate", json={"trigger": f"trigger_{i}"})

    res = client.get("/api/achievements?page=0&page_size=2")
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["total_pages"] == 2

    res2 = client.get("/api/achievements?page=1&page_size=2")
    data2 = res2.json()
    assert len(data2["items"]) == 1
    assert data2["page"] == 1


def test_achievements_list_empty(client):
    """GET /api/achievements returns empty when no achievements."""
    res = client.get("/api/achievements")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["total_pages"] == 0


@patch("server.synthesize_achievement", return_value=[])
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_get_achievement_by_id(mock_gen, mock_synth, client):
    """GET /api/achievements/{id} returns single entry."""
    client.post("/api/generate", json={"trigger": "test"})

    res = client.get("/api/achievements/1")
    assert res.status_code == 200
    assert res.json()["id"] == 1
    assert res.json()["title"] == "Corporate Houdini"


def test_get_achievement_not_found(client):
    """GET /api/achievements/{id} returns 404 for missing ID."""
    res = client.get("/api/achievements/999")
    assert res.status_code == 404


def test_serve_audio_not_found(client):
    """GET /audio/{filename} returns 404 for missing file."""
    res = client.get("/audio/nonexistent.wav")
    assert res.status_code == 404


def test_serve_audio_exists(client, tmp_path, monkeypatch):
    """GET /audio/{filename} serves existing audio file."""
    import config

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config, "OUTPUT_DIR", output_dir)

    # Reload server to pick up new OUTPUT_DIR
    import importlib

    import server

    importlib.reload(server)
    test_client = TestClient(server.app)

    test_file = output_dir / "test_audio.wav"
    test_file.write_bytes(b"RIFF" + b"\x00" * 100)

    res = test_client.get("/audio/test_audio.wav")
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"


def test_serve_audio_path_traversal(client):
    """GET /audio/ rejects path traversal attempts."""
    res = client.get("/audio/../../../etc/passwd")
    assert res.status_code == 404


def test_root_redirects(client):
    """GET / redirects to /static/index.html."""
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert "/static/index.html" in res.headers["location"]


@patch("server.concatenate_audio", return_value="/fake/path/20260401_combined.mp3")
@patch(
    "server.synthesize_achievement_parallel",
    return_value=["/fake/path/20260401_opener.mp3", "/fake/path/20260401_reward.mp3"],
)
@patch("server.generate", return_value=SAMPLE_ACHIEVEMENT)
def test_generate_returns_audio_urls(mock_gen, mock_synth, mock_concat, client):
    """POST /api/generate returns a single concatenated audio URL in SSE."""
    res = client.post("/api/generate", json={"trigger": "test"})
    events = _parse_sse(res.text)
    assert events["audio"]["audio_urls"] == ["/audio/20260401_combined.mp3"]
