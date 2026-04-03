"""Tests for storage.py cloud mode — S3 download path."""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_resolve_cloud_s3_key_downloads(monkeypatch, tmp_path):
    """Cloud mode with S3 key downloads file and returns local path."""
    import config

    monkeypatch.setattr(config, "STORAGE_MODE", "cloud")
    monkeypatch.setattr(config, "S3_BUCKET", "test-bucket")

    import storage

    importlib.reload(storage)

    mock_s3 = MagicMock()

    def fake_download(bucket, key, local):
        Path(local).write_bytes(b"fake audio")

    mock_s3.download_file = fake_download

    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        result = storage.resolve_audio_path("audio/test_clip.mp3")

    assert result == tmp_path / "test_clip.mp3"
    assert result.exists()


def test_resolve_cloud_s3_key_skips_existing(monkeypatch, tmp_path):
    """Cloud mode skips download if file already exists in temp dir."""
    import config

    monkeypatch.setattr(config, "STORAGE_MODE", "cloud")
    monkeypatch.setattr(config, "S3_BUCKET", "test-bucket")

    import storage

    importlib.reload(storage)

    # Pre-create the file
    cached = tmp_path / "cached_clip.mp3"
    cached.write_bytes(b"already here")

    mock_boto3 = MagicMock()

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        result = storage.resolve_audio_path("audio/cached_clip.mp3")
        # boto3.client should not be called since file exists
        mock_boto3.client.return_value.download_file.assert_not_called()

    assert result == cached
