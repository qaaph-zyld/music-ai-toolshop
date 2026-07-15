import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from run_reverse_engineering_batch import process_track
import run_reverse_engineering_batch as batch
import toolshop.reverse_engineering_adapter as rea


@pytest.fixture
def mock_adapters(tmp_path):
    adapters = MagicMock()
    adapters.reverse_engineering_adapter.analyze_track.return_value = {
        "bpm": 90.0,
        "key": "G",
        "mode": "minor",
        "duration_seconds": 120.0,
        "analysis_backend": "wav_reverse_engineer",
        "chord_progression": [{"name": "Gm", "start_time": 0.0, "duration": 1.0}],
        "instruments": [{"label": "piano", "score": 0.8}],
    }
    adapters.stem_extractor_adapter.extract_stems.return_value = {
        "stems": {"vocals": "vocals.wav", "instrumental": "instrumental.wav"}
    }
    adapters.voice_effects_adapter.analyze_voice.return_value = {
        "effects_detected": [{"effect": "reverb", "confidence": 0.9, "reason": "long tail"}]
    }
    return adapters


def test_process_track_skips_stems_when_no_stems(mock_adapters, tmp_path):
    track = tmp_path / "test.wav"
    track.touch()
    track_out = tmp_path / "out" / "test_unknown"

    result = process_track(
        track_path=track,
        track_out=track_out,
        use_gpu=False,
        high_quality=False,
        adapters=mock_adapters,
        no_stems=True,
    )

    mock_adapters.stem_extractor_adapter.extract_stems.assert_not_called()
    assert result["status"] == "completed"
    assert result["stems"] == {"skipped": True}

    recipe = Path(result["recipe_md"]).read_text(encoding="utf-8")
    assert "Skipped: analyze-only" in recipe


def test_process_track_extracts_stems_by_default(mock_adapters, tmp_path):
    track = tmp_path / "test.wav"
    track.touch()
    track_out = tmp_path / "out" / "test_unknown"

    result = process_track(
        track_path=track,
        track_out=track_out,
        use_gpu=False,
        high_quality=False,
        adapters=mock_adapters,
        no_stems=False,
    )

    mock_adapters.stem_extractor_adapter.extract_stems.assert_called_once()
    assert result["status"] == "completed"
    expected_stems_dir = track_out / "stems"
    assert result["stems"] == {
        "stems": {
            "vocals": str(expected_stems_dir / "vocals.wav"),
            "instrumental": str(expected_stems_dir / "instrumental.wav"),
        }
    }

    recipe = Path(result["recipe_md"]).read_text(encoding="utf-8")
    assert "vocals.wav" in recipe
    assert "Skipped: analyze-only" not in recipe


def test_require_advanced_fails_when_backend_unavailable(tmp_path, monkeypatch):
    """--require-advanced must fail fast if wav_reverse_engineer is not importable."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "test.mp3").touch()

    monkeypatch.setattr(rea, "_WAV_RE_AVAILABLE", False)

    argv = [
        "run_reverse_engineering_batch.py",
        "--input-dir", str(input_dir),
        "--output-dir", str(tmp_path / "out"),
        "--require-advanced",
    ]
    with patch.object(sys, "argv", argv):
        exit_code = batch.main()

    assert exit_code == 1


def test_max_duration_skips_long_tracks(tmp_path, monkeypatch):
    """Tracks longer than --max-duration should be recorded as skipped_long."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "test.mp3").touch()

    monkeypatch.setattr(batch, "probe_duration", lambda p: 500.0)

    argv = [
        "run_reverse_engineering_batch.py",
        "--input-dir", str(input_dir),
        "--output-dir", str(tmp_path / "out"),
        "--max-duration", "300",
        "--no-stems",
    ]
    with patch.object(sys, "argv", argv):
        exit_code = batch.main()

    assert exit_code == 0
    status = batch.load_or_create_status(
        tmp_path / "out", input_dir, 1, 30
    )
    track = next(t for t in status["tracks"] if t["source"].endswith("test.mp3"))
    assert track["status"] == "skipped_long"
    assert track["duration_seconds"] == 500.0
