"""Tests for voice.py — S3 upload, client init, and cloud mode paths."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_get_client_raises_without_key(monkeypatch):
    """_get_client raises OSError when ELEVENLABS_API_KEY is empty."""
    import voice

    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "")
    voice._client = None

    with pytest.raises(OSError, match="ELEVENLABS_API_KEY"):
        voice._get_client()


def test_upload_to_s3(tmp_path, monkeypatch):
    """_upload_to_s3 uploads file and deletes local copy."""
    import voice

    monkeypatch.setattr(voice, "S3_BUCKET", "test-bucket")

    local_file = tmp_path / "test_audio.mp3"
    local_file.write_bytes(b"fake mp3 data")

    mock_s3 = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        result = voice._upload_to_s3(local_file)

    assert result == "audio/test_audio.mp3"
    mock_s3.upload_file.assert_called_once_with(
        str(local_file),
        "test-bucket",
        "audio/test_audio.mp3",
        ExtraArgs={"ContentType": "audio/mpeg"},
    )
    assert not local_file.exists()


def test_upload_to_s3_wav_content_type(tmp_path, monkeypatch):
    """_upload_to_s3 sets correct content type for WAV files."""
    import voice

    monkeypatch.setattr(voice, "S3_BUCKET", "test-bucket")

    local_file = tmp_path / "test_audio.wav"
    local_file.write_bytes(b"fake wav data")

    mock_s3 = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        result = voice._upload_to_s3(local_file)

    assert result == "audio/test_audio.wav"
    mock_s3.upload_file.assert_called_once_with(
        str(local_file),
        "test-bucket",
        "audio/test_audio.wav",
        ExtraArgs={"ContentType": "audio/wav"},
    )


def test_upload_to_s3_public_wrapper(tmp_path, monkeypatch):
    """upload_to_s3 (public) delegates to _upload_to_s3."""
    import voice

    monkeypatch.setattr(voice, "S3_BUCKET", "test-bucket")

    local_file = tmp_path / "clip.mp3"
    local_file.write_bytes(b"data")

    mock_s3 = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        result = voice.upload_to_s3(local_file)

    assert result == "audio/clip.mp3"


def test_synthesize_cloud_mode_uploads(tmp_path, monkeypatch):
    """In cloud mode with keep_local=False, synthesize uploads to S3."""
    import voice

    monkeypatch.setattr(voice, "STORAGE_MODE", "cloud")
    monkeypatch.setattr(voice, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(voice, "OUTPUT_DIR", tmp_path)

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = [b"fake audio data"]
    voice._client = mock_client

    with (
        patch("voice._apply_ai_effect") as mock_fx,
        patch("voice._encode_mp3") as mock_encode,
        patch("voice._upload_to_s3", return_value="audio/test.mp3") as mock_upload,
    ):
        mock_fx.side_effect = lambda inp, out, **kw: out.write_bytes(b"processed")
        mock_encode.side_effect = lambda inp, out: out.write_bytes(b"encoded")

        result = voice.synthesize("Hello", filename_hint="test", keep_local=False)

    assert result == "audio/test.mp3"
    mock_upload.assert_called_once()

    voice._client = None


def test_synthesize_cloud_keep_local(tmp_path, monkeypatch):
    """In cloud mode with keep_local=True, synthesize returns local path."""
    import voice

    monkeypatch.setattr(voice, "STORAGE_MODE", "cloud")
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(voice, "OUTPUT_DIR", tmp_path)

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = [b"fake audio data"]
    voice._client = mock_client

    with (
        patch("voice._apply_ai_effect") as mock_fx,
        patch("voice._encode_mp3") as mock_encode,
        patch("voice._upload_to_s3") as mock_upload,
    ):
        mock_fx.side_effect = lambda inp, out, **kw: out.write_bytes(b"processed")
        mock_encode.side_effect = lambda inp, out: out.write_bytes(b"encoded")

        result = voice.synthesize("Hello", filename_hint="test", keep_local=True)

    assert isinstance(result, Path)
    mock_upload.assert_not_called()

    voice._client = None
