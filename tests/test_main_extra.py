"""Tests for main.py — --list, --replay, --speak, and --speak-only CLI paths."""

import importlib
from unittest.mock import patch

import pytest

SAMPLE_ACHIEVEMENT = {
    "title": "Corporate Houdini",
    "badge": "ghost",
    "description": "New Achievement! You vanished for 120 minutes. Your Reward!",
    "reward": "Nobody noticed.",
}

SAMPLE_ENTRY = {
    "id": 1,
    "timestamp": "2026-04-01T15:00:00",
    "title": "Corporate Houdini",
    "badge": "ghost",
    "description": "New Achievement! You vanished for 120 minutes. Your Reward!",
    "reward": "Nobody noticed.",
    "trigger": "took a long lunch",
    "audio_files": ["/output/test.mp3"],
}


@pytest.fixture(autouse=True)
def _isolate_archive(tmp_path, monkeypatch):
    """Redirect archive to temp DB for all tests."""
    import config

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "STORAGE_MODE", "local")

    import archive

    archive._DB_INIT = False
    importlib.reload(archive)


def test_list_shows_entries(capsys):
    """--list displays archived achievements."""
    import archive

    archive.save(SAMPLE_ACHIEVEMENT, trigger="test")

    with patch("sys.argv", ["main.py", "--list"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    output = capsys.readouterr().out
    assert "Corporate Houdini" in output
    assert "test" in output


def test_list_empty(capsys):
    """--list with no achievements shows message."""
    with patch("sys.argv", ["main.py", "--list"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    output = capsys.readouterr().out
    assert "No achievements" in output


@patch("main.play_audio_sequence")
@patch("main.resolve_audio_path", return_value="/output/test.mp3")
def test_replay_with_cached_audio(mock_resolve, mock_play, capsys):
    """--replay plays cached audio files."""
    import archive

    archive.save(SAMPLE_ACHIEVEMENT, trigger="test", audio_files=["/output/test.mp3"])

    with patch("sys.argv", ["main.py", "--replay", "1"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    mock_play.assert_called_once()
    output = capsys.readouterr().out
    assert "Corporate Houdini" in output


@patch("main.play_audio_sequence")
@patch("main.synthesize_achievement", return_value=["/output/resynth.mp3"])
def test_replay_resynthesizes_when_no_audio(mock_synth, mock_play, monkeypatch, capsys):
    """--replay re-synthesizes audio if none cached and ElevenLabs key available."""
    import archive

    archive.save(SAMPLE_ACHIEVEMENT, trigger="test", audio_files=[])
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    with patch("sys.argv", ["main.py", "--replay", "1"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    mock_synth.assert_called_once()
    mock_play.assert_called_once()


def test_replay_no_audio_no_key(monkeypatch, capsys):
    """--replay without audio or ElevenLabs key shows message."""
    import archive

    archive.save(SAMPLE_ACHIEVEMENT, trigger="test", audio_files=[])
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    with patch("sys.argv", ["main.py", "--replay", "1"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    output = capsys.readouterr().out
    assert "No audio" in output


def test_replay_not_found(capsys):
    """--replay with invalid ID exits with error."""
    with patch("sys.argv", ["main.py", "--replay", "999"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    assert "No achievement found" in capsys.readouterr().err


@patch("main.archive.save", return_value={"id": 1})
@patch("main.play_audio_sequence")
@patch("main.synthesize_achievement", return_value=["/output/test.mp3"])
@patch("main.generate", return_value=SAMPLE_ACHIEVEMENT)
@patch("main.ANTHROPIC_API_KEY", "sk-test")
def test_speak_mode(mock_gen, mock_synth, mock_play, mock_save, monkeypatch):
    """--speak generates, prints, synthesizes, and plays audio."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    with patch("sys.argv", ["main.py", "--speak", "--trigger", "test"]):
        from main import main

        main()

    mock_gen.assert_called_once()
    mock_synth.assert_called_once()
    mock_play.assert_called_once()


@patch("main.archive.save", return_value={"id": 1})
@patch("main.play_audio_sequence")
@patch("main.synthesize_achievement", return_value=["/output/test.mp3"])
@patch("main.generate", return_value=SAMPLE_ACHIEVEMENT)
@patch("main.print_achievement")
@patch("main.ANTHROPIC_API_KEY", "sk-test")
def test_speak_only_mode(mock_print, mock_gen, mock_synth, mock_play, mock_save, monkeypatch):
    """--speak-only skips terminal output."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    with patch("sys.argv", ["main.py", "--speak-only"]):
        from main import main

        main()

    mock_print.assert_not_called()
    mock_synth.assert_called_once()
    mock_play.assert_called_once()


def test_speak_without_elevenlabs_key(monkeypatch, capsys):
    """--speak without ELEVENLABS_API_KEY exits with error."""
    monkeypatch.setattr("main.ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    with patch("sys.argv", ["main.py", "--speak"]):
        from main import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    assert "ElevenLabs" in capsys.readouterr().err
