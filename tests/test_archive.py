
import pytest

SAMPLE_ACHIEVEMENT = {
    "title": "Corporate Houdini",
    "description": "New Achievement! You vanished for 120 minutes. Your Reward!",
    "reward": "Unlocked: Nobody noticed.",
}


@pytest.fixture
def tmp_archive(tmp_path, monkeypatch):
    """Redirect ARCHIVE_FILE to a temp location."""
    archive_file = tmp_path / "achievements.json"
    import config
    monkeypatch.setattr(config, "ARCHIVE_FILE", archive_file)
    import importlib

    import archive
    importlib.reload(archive)
    return archive_file


def test_save_creates_file(tmp_archive):
    import archive
    entry = archive.save(SAMPLE_ACHIEVEMENT, trigger="took a long lunch")

    assert tmp_archive.exists()
    assert entry["id"] == 1
    assert entry["title"] == "Corporate Houdini"
    assert entry["trigger"] == "took a long lunch"
    assert "timestamp" in entry


def test_save_appends(tmp_archive):
    import archive
    archive.save(SAMPLE_ACHIEVEMENT, trigger="first")
    archive.save(SAMPLE_ACHIEVEMENT, trigger="second")

    entries = archive.load_all()
    assert len(entries) == 2
    assert entries[0]["id"] == 1
    assert entries[1]["id"] == 2
    assert entries[0]["trigger"] == "first"
    assert entries[1]["trigger"] == "second"


def test_save_with_audio_files(tmp_archive):
    import archive
    files = ["/output/opener.mp3", "/output/desc.mp3"]
    entry = archive.save(SAMPLE_ACHIEVEMENT, audio_files=files)

    assert entry["audio_files"] == files


def test_save_without_trigger(tmp_archive):
    import archive
    entry = archive.save(SAMPLE_ACHIEVEMENT)

    assert entry["trigger"] is None


def test_load_all_empty(tmp_archive):
    import archive
    assert archive.load_all() == []


def test_load_all_returns_entries(tmp_archive):
    import archive
    archive.save(SAMPLE_ACHIEVEMENT, trigger="a")
    archive.save(SAMPLE_ACHIEVEMENT, trigger="b")

    entries = archive.load_all()
    assert len(entries) == 2


def test_get_by_id(tmp_archive):
    import archive
    archive.save(SAMPLE_ACHIEVEMENT, trigger="first")
    archive.save(SAMPLE_ACHIEVEMENT, trigger="second")

    entry = archive.get(2)
    assert entry is not None
    assert entry["trigger"] == "second"


def test_get_missing_id(tmp_archive):
    import archive
    archive.save(SAMPLE_ACHIEVEMENT)

    assert archive.get(999) is None


def test_archive_preserves_all_fields(tmp_archive):
    import archive
    archive.save(SAMPLE_ACHIEVEMENT, trigger="test", audio_files=["/a.mp3"])

    loaded = archive.get(1)
    assert loaded["title"] == SAMPLE_ACHIEVEMENT["title"]
    assert loaded["description"] == SAMPLE_ACHIEVEMENT["description"]
    assert loaded["reward"] == SAMPLE_ACHIEVEMENT["reward"]
    assert loaded["trigger"] == "test"
    assert loaded["audio_files"] == ["/a.mp3"]
