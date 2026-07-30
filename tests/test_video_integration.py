"""P0 integration test: end-to-end video generation pipeline with mocked FFmpeg."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from toolshop.video_features import extract_features
from toolshop.video_ass import lrc_to_ass
from toolshop.video_compose import compose_pipeline
from toolshop.video_cli import run


@pytest.fixture
def _fake_audio(tmp_path):
    """Create a dummy audio file."""
    audio = tmp_path / "test_song.wav"
    audio.write_bytes(b"\x00" * 1024)
    return audio


@pytest.fixture
def _fake_lrc(tmp_path):
    """Create a simple LRC file."""
    lrc = tmp_path / "test_song.lrc"
    lrc.write_text(
        "[00:00.50]Intro line\n[00:02.00]First verse\n[00:04.00]Chorus line\n",
        encoding="utf-8",
    )
    return lrc


def test_end_to_end_features_to_video(tmp_path, _fake_audio):
    """Features → ASS → compose pipeline → output video (mocked FFmpeg)."""
    # Step 1: Extract features (mocked librosa)
    features_path = tmp_path / "features.json"
    with patch("toolshop.video_features._HAS_LIBROSA", True), patch(
        "toolshop.video_features.librosa"
    ) as mock_lib, patch("toolshop.video_features.np") as mock_np:
        mock_lib.load.return_value = (MagicMock(), 22050)
        mock_lib.get_duration.return_value = 5.0
        mock_lib.beat.beat_track.return_value = (120.0, MagicMock())
        mock_lib.frames_to_time.return_value = MagicMock()
        mock_lib.frames_to_time.__iter__ = lambda self: iter([0.5, 1.0, 1.5])
        mock_lib.onset.onset_detect.return_value = MagicMock()
        mock_lib.onset.onset_strength.return_value = MagicMock()
        mock_lib.feature.rms.return_value = MagicMock()
        mock_lib.feature.spectral_centroid.return_value = MagicMock()
        mock_lib.feature.chroma_cqt.return_value = MagicMock()
        mock_np.atleast_1d.return_value = MagicMock()
        mock_np.atleast_1d.return_value.__getitem__ = lambda self, i: 120.0
        mock_np.mean.return_value = [0.8] * 12
        mock_np.argmax.return_value = 0

        features = extract_features(_fake_audio, output_path=features_path)

    assert features_path.exists()
    loaded = json.loads(features_path.read_text(encoding="utf-8"))
    assert "tempo" in loaded
    assert "beats" in loaded

    # Step 2: Generate ASS from LRC
    lrc = tmp_path / "lyrics.lrc"
    lrc.write_text("[00:01.00]Hello\n[00:03.00]World\n", encoding="utf-8")
    ass_path = tmp_path / "lyrics.ass"
    lrc_to_ass(lrc, ass_path, style="neon")
    assert ass_path.exists()
    ass_content = ass_path.read_text(encoding="utf-8")
    assert "Dialogue:" in ass_content
    assert "Hello" in ass_content

    # Step 3: Compose pipeline (mocked FFmpeg)
    output = tmp_path / "output.mp4"

    def _fake_run(cmd, **kwargs):
        mp4_args = [Path(a) for a in cmd if str(a).endswith(".mp4")]
        if mp4_args:
            mp4_args[-1].touch()
        return MagicMock(returncode=0)

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run", side_effect=_fake_run
    ):
        result = compose_pipeline(
            features_path=features_path,
            audio=_fake_audio,
            output=output,
            background="showwaves",
            ass_file=ass_path,
        )

    assert result == output
    assert output.exists()


def test_cli_generate_end_to_end(tmp_path, _fake_audio, _fake_lrc):
    """Full CLI dispatch: video generate with lyrics (all mocked)."""
    output = tmp_path / "mv.mp4"

    args = MagicMock(
        video_command="generate",
        audio=_fake_audio,
        lyrics=_fake_lrc,
        features=None,
        style="neon",
        background="showwaves",
        image=None,
        resolution="1280x720",
        fps=30,
        out=output,
        json=False,
    )

    def _fake_run(cmd, **kwargs):
        for arg in cmd:
            if str(arg).endswith(".mp4"):
                Path(arg).touch()
                break
        return MagicMock(returncode=0)

    with patch("toolshop.video_cli.extract_features") as mock_extract, patch(
        "toolshop.video_cli.compose_pipeline"
    ) as mock_compose, patch("toolshop.video_cli.lrc_to_ass") as mock_lrc:
        mock_extract.return_value = {"tempo": 120.0, "beats": [], "duration": 5.0}
        mock_compose.return_value = output
        mock_lrc.return_value = tmp_path / "lyrics.ass"
        code = run(args)

    assert code == 0
    mock_extract.assert_called_once()
    mock_lrc.assert_called_once()
    mock_compose.assert_called_once()


def test_cli_features_to_json(tmp_path, _fake_audio):
    """CLI video features --json prints JSON to stdout."""
    out = tmp_path / "features.json"
    args = MagicMock(
        video_command="features",
        audio=_fake_audio,
        output=out,
        stems_dir=None,
        json=True,
    )

    with patch("toolshop.video_cli.extract_features") as mock_extract:
        mock_extract.return_value = {
            "tempo": 128.0,
            "key": "C",
            "mode": "major",
            "duration": 30.0,
            "beats": [0.5, 1.0],
            "onsets": [0.3, 0.7],
        }
        code = run(args)

    assert code == 0
