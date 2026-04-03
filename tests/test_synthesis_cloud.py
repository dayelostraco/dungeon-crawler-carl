"""Tests for synthesis.py cloud mode — S3 upload in concatenate_audio and play_audio_sequence."""

from unittest.mock import patch

from pydub.generators import Sine


def test_concatenate_audio_uploads_in_cloud_mode(tmp_path, monkeypatch):
    """concatenate_audio uploads the combined file to S3 in cloud mode."""
    import config

    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)

    files = []
    for hint in ["opener", "title", "description", "your_reward", "reward"]:
        tone = Sine(440).to_audio_segment(duration=200)
        path = tmp_path / f"test_{hint}.mp3"
        tone.export(str(path), format="mp3")
        files.append(str(path))

    with (
        patch("synthesis.STORAGE_MODE", "cloud"),
        patch("synthesis.upload_to_s3", return_value="audio/combined.mp3") as mock_upload,
    ):
        result = __import__("synthesis").concatenate_audio(files)

    assert result == "audio/combined.mp3"
    mock_upload.assert_called_once()
    # The local combined file was passed to upload_to_s3
    uploaded_path = mock_upload.call_args[0][0]
    assert "combined" in str(uploaded_path)


def test_play_audio_sequence_calls_player_with_pauses(tmp_path):
    """play_audio_sequence plays each segment with correct pause timing."""
    from synthesis import (
        PAUSE_AFTER_TITLE,
        PAUSE_BEFORE_CLOSER,
        PAUSE_BEFORE_REWARD,
        PAUSE_BEFORE_TITLE,
    )

    files = [
        str(tmp_path / "20260401_opener.mp3"),
        str(tmp_path / "20260401_title.mp3"),
        str(tmp_path / "20260401_description.mp3"),
        str(tmp_path / "20260401_your_reward.mp3"),
        str(tmp_path / "20260401_reward.mp3"),
    ]

    play_calls = []
    sleep_calls = []

    with (
        patch("player.play", side_effect=lambda p: play_calls.append(str(p))),
        patch("synthesis.time.sleep", side_effect=lambda t: sleep_calls.append(t)),
    ):
        from synthesis import play_audio_sequence

        play_audio_sequence(files)

    assert len(play_calls) == 5
    # Title has pause before and after
    assert PAUSE_BEFORE_TITLE in sleep_calls
    assert PAUSE_AFTER_TITLE in sleep_calls
    # Closer has pause before
    assert PAUSE_BEFORE_CLOSER in sleep_calls
    # Reward has pause before
    assert PAUSE_BEFORE_REWARD in sleep_calls
