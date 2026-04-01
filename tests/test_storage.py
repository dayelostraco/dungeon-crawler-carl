from pathlib import Path

from storage import resolve_audio_path


def test_resolve_local_path(monkeypatch):
    """Local mode returns path as-is."""
    import config

    monkeypatch.setattr(config, "STORAGE_MODE", "local")

    import importlib

    import storage

    importlib.reload(storage)

    result = resolve_audio_path("/output/test.wav")
    assert result == Path("/output/test.wav")


def test_resolve_local_ignores_s3_key(monkeypatch):
    """Local mode returns S3-like key as a local path (no download)."""
    import config

    monkeypatch.setattr(config, "STORAGE_MODE", "local")

    import importlib

    import storage

    importlib.reload(storage)

    result = resolve_audio_path("audio/test.wav")
    assert result == Path("audio/test.wav")


def test_resolve_cloud_non_s3_key(monkeypatch):
    """Cloud mode with a local-looking path returns as-is."""
    import config

    monkeypatch.setattr(config, "STORAGE_MODE", "cloud")

    import importlib

    import storage

    importlib.reload(storage)

    result = resolve_audio_path("/local/path/test.wav")
    assert result == Path("/local/path/test.wav")
