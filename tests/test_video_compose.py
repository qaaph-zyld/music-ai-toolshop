"""Tests for toolshop/video_compose.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from toolshop.video_compose import (
    check_ffmpeg,
    render_showwaves,
    render_ken_burns,
    concat_beat_cuts,
    crossfade_clips,
    overlay_ass,
    compose_pipeline,
    _build_showwaves_cmd,
    _build_ken_burns_cmd,
    _build_overlay_ass_cmd,
)


def test_check_ffmpeg_found():
    with patch("toolshop.video_compose.shutil.which", return_value="/usr/bin/ffmpeg"):
        assert check_ffmpeg() is True


def test_check_ffmpeg_missing():
    with patch("toolshop.video_compose.shutil.which", return_value=None):
        assert check_ffmpeg() is False


def test_check_ffmpeg_raises_when_required():
    with patch("toolshop.video_compose.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            check_ffmpeg(required=True)


def test_build_showwaves_cmd():
    cmd = _build_showwaves_cmd(
        audio=Path("song.wav"),
        output=Path("out.mp4"),
        size="1280x720",
        fps=30,
        mode="cline",
    )
    assert "ffmpeg" in cmd[0]
    assert "-i" in cmd
    assert "song.wav" in cmd
    assert "showwaves" in " ".join(cmd)
    assert "1280x720" in " ".join(cmd)
    assert "libx264" in cmd


def test_render_showwaves_calls_subprocess(tmp_path):
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "out.mp4"

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = render_showwaves(audio, output, size="1280x720", fps=30)

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "showwaves" in " ".join(args)
    assert result == output


def test_render_showwaves_no_ffmpeg(tmp_path):
    with patch("toolshop.video_compose.check_ffmpeg", side_effect=RuntimeError("ffmpeg not found")):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            render_showwaves(Path("song.wav"), Path("out.mp4"))


def test_build_ken_burns_cmd():
    cmd = _build_ken_burns_cmd(
        image=Path("cover.jpg"),
        audio=Path("song.wav"),
        output=Path("out.mp4"),
        size="1280x720",
        fps=30,
        zoom=1.5,
    )
    cmd_str = " ".join(cmd)
    assert "zoompan" in cmd_str
    assert "cover.jpg" in cmd
    assert "song.wav" in cmd
    assert "libx264" in cmd


def test_render_ken_burns_calls_subprocess(tmp_path):
    image = tmp_path / "cover.jpg"
    image.touch()
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "out.mp4"

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        render_ken_burns(image, audio, output)

    mock_run.assert_called_once()


def test_concat_beat_cuts(tmp_path):
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    for c in clips:
        c.touch()
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "out.mp4"
    concat_list = tmp_path / "concat.txt"

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        concat_beat_cuts(clips, audio, output, concat_list=concat_list)

    assert concat_list.exists()
    mock_run.assert_called_once()


def test_crossfade_clips(tmp_path):
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    clip_a.touch()
    clip_b.touch()
    output = tmp_path / "out.mp4"

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        crossfade_clips(clip_a, clip_b, output, offset=3.0, duration=0.5)

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "xfade" in " ".join(args)


def test_build_overlay_ass_cmd():
    cmd = _build_overlay_ass_cmd(
        video=Path("base.mp4"),
        ass_file=Path("lyrics.ass"),
        output=Path("out.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "ass=" in cmd_str
    assert "lyrics.ass" in cmd_str
    assert "base.mp4" in cmd


def test_overlay_ass_calls_subprocess(tmp_path):
    video = tmp_path / "base.mp4"
    video.touch()
    ass_file = tmp_path / "lyrics.ass"
    ass_file.touch()
    output = tmp_path / "out.mp4"

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        overlay_ass(video, ass_file, output)

    mock_run.assert_called_once()


def test_compose_pipeline_showwaves(tmp_path):
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"
    features = {"tempo": 128.0, "beats": [0.5, 1.0, 1.5], "duration": 10.0}
    features_path = tmp_path / "features.json"
    features_path.write_text(json.dumps(features), encoding="utf-8")

    def _fake_run(cmd, **kwargs):
        # Create the output file that ffmpeg would have produced
        for arg in cmd:
            if str(arg).endswith(".mp4"):
                Path(arg).touch()
                break
        return MagicMock(returncode=0)

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run", side_effect=_fake_run
    ) as mock_run:
        compose_pipeline(
            features_path=features_path,
            audio=audio,
            output=output,
            background="showwaves",
        )

    assert mock_run.call_count >= 1


def test_compose_pipeline_with_ass(tmp_path):
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"
    ass_file = tmp_path / "lyrics.ass"
    ass_file.touch()
    features = {"tempo": 128.0, "beats": [0.5, 1.0], "duration": 5.0}
    features_path = tmp_path / "features.json"
    features_path.write_text(json.dumps(features), encoding="utf-8")

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        compose_pipeline(
            features_path=features_path,
            audio=audio,
            output=output,
            background="showwaves",
            ass_file=ass_file,
        )

    assert mock_run.call_count >= 2


def test_compose_pipeline_ffmpeg_failure(tmp_path):
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"
    features = {"tempo": 128.0, "beats": [], "duration": 5.0}
    features_path = tmp_path / "features.json"
    features_path.write_text(json.dumps(features), encoding="utf-8")

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            compose_pipeline(
                features_path=features_path,
                audio=audio,
                output=output,
                background="showwaves",
            )


def test_compose_pipeline_unknown_background(tmp_path):
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"
    features = {"tempo": 128.0, "beats": [], "duration": 5.0}
    features_path = tmp_path / "features.json"
    features_path.write_text(json.dumps(features), encoding="utf-8")

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True):
        with pytest.raises(ValueError, match="Unknown background"):
            compose_pipeline(
                features_path=features_path,
                audio=audio,
                output=output,
                background="nonexistent",
            )


def test_compose_pipeline_shader_background(tmp_path):
    audio = tmp_path / "song.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"
    features = {"tempo": 128.0, "beats": [], "duration": 5.0}
    features_path = tmp_path / "features.json"
    features_path.write_text(json.dumps(features), encoding="utf-8")

    def _fake_run(cmd, **kwargs):
        mp4_args = [Path(a) for a in cmd if str(a).endswith(".mp4")]
        if mp4_args:
            mp4_args[-1].touch()
        return MagicMock(returncode=0)

    with patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run", side_effect=_fake_run
    ), patch("toolshop.video_shaders._HAS_MODERNGL", True), patch(
        "toolshop.video_shaders.render_shader_to_frames"
    ) as mock_render:
        mock_render.return_value = [tmp_path / "frame_0000.png"]
        (tmp_path / "frame_0000.png").touch()
        compose_pipeline(
            features_path=features_path,
            audio=audio,
            output=output,
            background="shader:plasma",
        )

    mock_render.assert_called_once()
