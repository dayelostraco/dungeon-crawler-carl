"""Additional archive tests — badge field, update_audio preserves badge."""

import importlib

import pytest

SAMPLE_WITH_BADGE = {
    "title": "Corporate Houdini",
    "badge": "ghost",
    "description": "New Achievement! You vanished. Your Reward!",
    "reward": "Nobody noticed.",
}


@pytest.fixture
def local_archive(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    import config

    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "STORAGE_MODE", "local")

    import archive

    archive._DB_INIT = False
    importlib.reload(archive)
    return db_path


def test_save_stores_badge(local_archive):
    import archive

    entry = archive.save(SAMPLE_WITH_BADGE, trigger="test")
    assert entry["badge"] == "ghost"


def test_load_returns_badge(local_archive):
    import archive

    archive.save(SAMPLE_WITH_BADGE, trigger="test")
    loaded = archive.get(1)
    assert loaded["badge"] == "ghost"


def test_save_without_badge(local_archive):
    import archive

    entry = archive.save({"title": "Test", "description": "Desc", "reward": "Rew"})
    assert entry["badge"] is None


def test_update_audio_preserves_badge(local_archive):
    import archive

    archive.save(SAMPLE_WITH_BADGE, audio_files=[])
    archive.update_audio(1, ["/output/combined.mp3"])
    loaded = archive.get(1)
    assert loaded["badge"] == "ghost"
    assert loaded["audio_files"] == ["/output/combined.mp3"]


def test_load_all_includes_badge(local_archive):
    import archive

    archive.save(SAMPLE_WITH_BADGE, trigger="a")
    archive.save({"title": "No Badge", "description": "D", "reward": "R"}, trigger="b")
    entries = archive.load_all()
    assert entries[0]["badge"] == "ghost"
    assert entries[1]["badge"] is None
