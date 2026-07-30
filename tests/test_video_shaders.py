"""Tests for toolshop/video_shaders.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from toolshop.video_shaders import (
    SHADER_PRESETS,
    _check_moderngl,
    render_shader_to_frames,
    render_shader_video,
    _build_uniforms,
    _HAS_MODERNGL,
)


def test_shader_presets_exist():
    assert "neon_grid" in SHADER_PRESETS
    assert "plasma" in SHADER_PRESETS
    assert "spectrum_bars" in SHADER_PRESETS
    assert "particle_swirl" in SHADER_PRESETS
    for name, source in SHADER_PRESETS.items():
        assert isinstance(source, str)
        assert "void main" in source or "fragColor" in source


def test_check_moderngl_missing():
    with patch("toolshop.video_shaders._HAS_MODERNGL", False):
        with pytest.raises(RuntimeError, match="moderngl is required"):
            _check_moderngl()


def test_build_uniforms():
    features = {
        "tempo": 128.0,
        "rms_env": [0.1, 0.2, 0.3, 0.4, 0.5],
        "onset_strength": [0.5, 0.3, 0.1],
        "spectral_centroid": [1000.0, 2000.0],
        "duration": 10.0,
    }
    uniforms = _build_uniforms(features, frame_idx=10, fps=30, n_frames=300)
    assert "u_time" in uniforms
    assert "u_bass" in uniforms
    assert "u_treble" in uniforms
    assert "u_onset" in uniforms
    assert "u_tempo" in uniforms
    assert "u_beat_phase" in uniforms
    assert uniforms["u_tempo"] == 128.0
    assert uniforms["u_time"] == pytest.approx(10 / 30, abs=0.01)


def test_build_uniforms_empty_features():
    uniforms = _build_uniforms({}, frame_idx=0, fps=30, n_frames=100)
    assert uniforms["u_bass"] == 0.0
    assert uniforms["u_treble"] == 0.0
    assert uniforms["u_onset"] == 0.0
    assert uniforms["u_tempo"] == 0.0


def test_render_shader_to_frames_no_moderngl(tmp_path):
    with patch("toolshop.video_shaders._HAS_MODERNGL", False):
        with pytest.raises(RuntimeError, match="moderngl is required"):
            render_shader_to_frames(
                preset="neon_grid",
                features={},
                output_dir=tmp_path / "frames",
                width=640,
                height=360,
                fps=30,
                n_frames=10,
            )


def test_render_shader_to_frames_mocked(tmp_path):
    frames_dir = tmp_path / "frames"
    features = {"tempo": 120.0, "rms_env": [0.1] * 10, "duration": 5.0}

    with patch("toolshop.video_shaders._HAS_MODERNGL", True), patch(
        "toolshop.video_shaders.moderngl", create=True
    ) as mock_mgl, patch("toolshop.video_shaders.np", create=True) as mock_np, patch(
        "toolshop.video_shaders.Image", create=True
    ) as mock_image_cls:
        mock_ctx = MagicMock()
        mock_mgl.create_standalone_context.return_value = mock_ctx
        mock_prog = MagicMock()
        mock_ctx.program.return_value = mock_prog
        mock_vao = MagicMock()
        mock_ctx.vertex_array.return_value = mock_vao
        mock_fbo = MagicMock()
        mock_ctx.framebuffer.return_value = mock_fbo

        mock_np.zeros.return_value = MagicMock()
        mock_np.frombuffer.return_value = MagicMock()
        mock_np.linspace.return_value = MagicMock()

        result = render_shader_to_frames(
            preset="neon_grid",
            features=features,
            output_dir=frames_dir,
            width=320,
            height=180,
            fps=15,
            n_frames=5,
        )

    assert isinstance(result, list)


def test_render_shader_video_mocked(tmp_path):
    output = tmp_path / "shader_bg.mp4"
    features = {"tempo": 120.0, "rms_env": [0.1] * 10, "duration": 5.0}

    with patch("toolshop.video_shaders._HAS_MODERNGL", True), patch(
        "toolshop.video_shaders.render_shader_to_frames"
    ) as mock_render, patch("toolshop.video_compose.check_ffmpeg", return_value=True), patch(
        "toolshop.video_compose.subprocess.run"
    ) as mock_run:
        mock_render.return_value = [tmp_path / "frame_0000.png"]
        (tmp_path / "frame_0000.png").touch()
        mock_run.return_value = MagicMock(returncode=0)

        result = render_shader_video(
            preset="plasma",
            features=features,
            output=output,
            width=320,
            height=180,
            fps=15,
            n_frames=5,
            audio=tmp_path / "song.wav",
        )

    mock_render.assert_called_once()
    mock_run.assert_called_once()


def test_render_shader_video_unknown_preset(tmp_path):
    with patch("toolshop.video_shaders._HAS_MODERNGL", True):
        with pytest.raises(KeyError, match="Unknown shader preset"):
            render_shader_video(
                preset="nonexistent",
                features={},
                output=tmp_path / "out.mp4",
                width=320,
                height=180,
                fps=15,
                n_frames=5,
                audio=tmp_path / "song.wav",
            )
