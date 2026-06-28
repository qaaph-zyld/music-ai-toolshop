import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolshop import cli


def test_track_analyze_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["track", "analyze", "--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--chords" in captured.out
    assert "--notes" in captured.out
    assert "--separation" in captured.out
    assert "--backend" in captured.out


def test_track_analyze_runs_with_chords_and_notes(capsys, tmp_path):
    with patch("toolshop.cli.reverse_engineering_adapter") as mock_adapter:
        mock_adapter.analyze_track.return_value = {
            "file": "test.wav",
            "analysis_backend": "wav_reverse_engineer",
            "chord_progression": [],
            "notes": [],
        }
        test_file = tmp_path / "test.wav"
        test_file.touch()
        cli.main(["track", "analyze", str(test_file), "--chords", "--notes"])
        mock_adapter.analyze_track.assert_called_once()
        call_kwargs = mock_adapter.analyze_track.call_args.kwargs
        assert call_kwargs["chords"] is True
        assert call_kwargs["notes"] is True


def test_track_batch_runs(capsys, tmp_path):
    with patch("toolshop.cli.reverse_engineering_adapter") as mock_adapter:
        mock_adapter.analyze_track.return_value = {"analysis_backend": "wav_reverse_engineer"}
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        output = tmp_path / "batch.json"
        cli.main(["track", "batch", str(tmp_path), "--output", str(output)])
        assert output.exists()
        assert mock_adapter.analyze_track.call_count == 2


def test_track_yt_analyze_runs(capsys, tmp_path):
    with patch("toolshop.cli.yt_scraper_adapter") as mock_yt, patch(
        "toolshop.cli.reverse_engineering_adapter"
    ) as mock_adapter:
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        mock_yt.download_audio.return_value = audio_path
        mock_adapter.analyze_track.return_value = {"analysis_backend": "wav_reverse_engineer"}
        cli.main(
            ["track", "yt-analyze", "https://example.com/watch?v=abc", "--output-dir", str(tmp_path)]
        )
        mock_yt.download_audio.assert_called_once()
        mock_adapter.analyze_track.assert_called_once()
        assert not audio_path.exists()


def test_track_yt_analyze_keep_audio(capsys, tmp_path):
    with patch("toolshop.cli.yt_scraper_adapter") as mock_yt, patch(
        "toolshop.cli.reverse_engineering_adapter"
    ) as mock_adapter:
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        mock_yt.download_audio.return_value = audio_path
        mock_adapter.analyze_track.return_value = {"analysis_backend": "wav_reverse_engineer"}
        cli.main(["track", "yt-analyze", "url", "--output-dir", str(tmp_path), "--keep-audio"])
        assert audio_path.exists()


def test_track_visualize_runs(capsys, tmp_path):
    with patch(
        "wav_reverse_engineer.audio_analyzer.visualizer.AudioVisualizer"
    ) as mock_viz, patch(
        "wav_reverse_engineer.audio_analyzer.audio_processor.AudioProcessor"
    ) as mock_proc:
        mock_proc.load_audio.return_value = (MagicMock(), 22050)
        test_file = tmp_path / "test.wav"
        test_file.touch()
        output_dir = tmp_path / "plots"
        cli.main(["track", "visualize", str(test_file), "--output-dir", str(output_dir), "--waveform"])
        mock_proc.load_audio.assert_called_once_with(str(test_file), target_sr=22050, mono=True)
        mock_viz.plot_waveform.assert_called_once()
