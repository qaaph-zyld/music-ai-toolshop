"""Tests for toolshop/remix_adapter.py."""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

from toolshop import remix_adapter


def _sine_wave(duration: float, sr: int = 22050, freq: float = 440.0) -> np.ndarray:
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    return np.sin(2.0 * np.pi * freq * t).astype(np.float32)


def _write_wav(path: Path, audio: np.ndarray, sr: int = 22050) -> None:
    import soundfile as sf

    sf.write(str(path), audio, sr)


def test_parse_key_variants():
    assert remix_adapter._parse_key("Gm") == ("G", "minor")
    assert remix_adapter._parse_key("G major") == ("G", "major")
    assert remix_adapter._parse_key("A#m") == ("A#", "minor")
    assert remix_adapter._parse_key("Bb") == ("A#", "major")
    assert remix_adapter._parse_key("Eb minor") == ("D#", "minor")


def test_semitone_diff_minimal():
    assert remix_adapter._semitone_diff("C", "G") == -5
    assert remix_adapter._semitone_diff("C", "F") == 5
    assert remix_adapter._semitone_diff("C", "B") == -1
    assert remix_adapter._semitone_diff("G", "G") == 0


def test_load_audio_truncates(tmp_path):
    audio = _sine_wave(6.0)
    wav = tmp_path / "long.wav"
    _write_wav(wav, audio)

    loaded, sr, duration, truncated = remix_adapter._load_audio(
        wav, max_duration=2.0, mono=True
    )
    assert sr == 22050
    assert duration == 2.0
    assert truncated is True
    assert len(loaded) == int(sr * 2.0)


def test_load_audio_no_truncation(tmp_path):
    audio = _sine_wave(1.0)
    wav = tmp_path / "short.wav"
    _write_wav(wav, audio)

    loaded, sr, duration, truncated = remix_adapter._load_audio(
        wav, max_duration=10.0, mono=True
    )
    assert truncated is False
    assert duration == 1.0


def test_slice_by_beats():
    audio = _sine_wave(4.0)
    beat_samples = np.array([0, 11025, 22050, 44100, 66150, 88200], dtype=np.int64)
    segments = remix_adapter._slice_by_beats(audio, beat_samples, segment_beats=2)
    assert len(segments) == 3
    first, start, end, beats = segments[0]
    assert beats == 2
    assert end - start == 22050


def test_slice_by_onsets(tmp_path):
    audio = _sine_wave(2.0)
    wav = tmp_path / "onsets.wav"
    _write_wav(wav, audio)
    loaded, sr, *_ = remix_adapter._load_audio(wav)
    segments = remix_adapter._slice_by_onsets(loaded, sr)
    assert isinstance(segments, list)


def test_stretch_segment_no_change():
    segment = _sine_wave(0.5)
    out = remix_adapter._stretch_segment(
        segment, 22050, src_bpm=120.0, dst_bpm=None, src_key="C", dst_key=None
    )
    assert out.shape == segment.shape
    np.testing.assert_allclose(out, segment, atol=1e-6)


def test_apply_fx_reverb_shape():
    segment = _sine_wave(0.5)
    out = remix_adapter._apply_fx(segment, 22050, ["reverb"])
    assert out.shape == segment.shape


def test_crossfade_concat():
    seg1 = _sine_wave(0.5)
    seg2 = _sine_wave(0.5)
    out = remix_adapter._crossfade_concat([seg1, seg2], 22050, crossfade_ms=10)
    expected_min = len(seg1) + len(seg2) - int(22050 * 0.01)
    assert len(out) >= expected_min


def test_create_remix_smoke(tmp_path):
    audio = _sine_wave(2.0)
    src = tmp_path / "src.wav"
    _write_wav(src, audio)
    out = tmp_path / "remix.wav"

    result = remix_adapter.create_remix(
        src,
        out,
        target_bpm=90.0,
        mode="remix",
        max_duration=240.0,
    )
    assert out.exists()
    assert result.manifest_path and result.manifest_path.exists()
    assert result.duration_seconds <= 2.0


def test_create_samples_smoke(tmp_path):
    audio = _sine_wave(2.0)
    src = tmp_path / "src.wav"
    _write_wav(src, audio)
    out_dir = tmp_path / "samples"

    result = remix_adapter.create_remix(
        src,
        out_dir,
        mode="sample",
        segment_beats=1,
        max_duration=240.0,
    )
    assert out_dir.is_dir()
    assert result.manifest_path and result.manifest_path.exists()
    assert len(result.samples) >= 1


def test_resolve_stems_dir(tmp_path):
    stem_file = tmp_path / "fake_instrumental.wav"
    stem_file.write_text("not real audio")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"stems": {"instrumental": "' + str(stem_file).replace("\\", "\\\\") + '"}}'
    )
    resolved = remix_adapter._resolve_input_path(
        Path("does_not_exist.wav"), stems_dir=tmp_path
    )
    assert resolved == stem_file
