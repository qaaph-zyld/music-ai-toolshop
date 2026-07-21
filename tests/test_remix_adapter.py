"""Tests for toolshop/remix_adapter.py."""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

from toolshop import remix_adapter

pytest.importorskip("numpy")

_pedalboard = pytest.importorskip("pedalboard", reason="[remix] extra not installed")
_librosa = pytest.importorskip("librosa", reason="[remix] extra not installed")
_soundfile = pytest.importorskip("soundfile", reason="[remix] extra not installed")


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


def test_load_audio_truncates(tmp_path):  # requires [remix]
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


def test_load_audio_no_truncation(tmp_path):  # requires [remix]
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


def test_slice_by_onsets(tmp_path):  # requires [remix]
    audio = _sine_wave(2.0)
    wav = tmp_path / "onsets.wav"
    _write_wav(wav, audio)
    loaded, sr, *_ = remix_adapter._load_audio(wav)
    segments = remix_adapter._slice_by_onsets(loaded, sr)
    assert isinstance(segments, list)


def test_stretch_segment_no_change():  # requires [remix]
    segment = _sine_wave(0.5)
    out = remix_adapter._stretch_segment(
        segment, 22050, src_bpm=120.0, dst_bpm=None, src_key="C", dst_key=None
    )
    assert out.shape == segment.shape
    np.testing.assert_allclose(out, segment, atol=1e-6)


def test_apply_fx_reverb_shape():  # requires [remix]
    segment = _sine_wave(0.5)
    out = remix_adapter._apply_fx(segment, 22050, ["reverb"])
    assert out.shape == segment.shape


def test_crossfade_concat():
    seg1 = _sine_wave(0.5)
    seg2 = _sine_wave(0.5)
    out = remix_adapter._crossfade_concat([seg1, seg2], 22050, crossfade_ms=10)
    expected_min = len(seg1) + len(seg2) - int(22050 * 0.01)
    assert len(out) >= expected_min


def test_create_remix_smoke(tmp_path):  # requires [remix]
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


def test_create_samples_smoke(tmp_path):  # requires [remix]
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


def test_load_sections_valid(tmp_path):
    import json
    sections_file = tmp_path / "sections.json"
    sections_file.write_text(json.dumps({
        "sections": [
            {"label": "intro", "start": 0.0, "end": 10.0},
            {"label": "verse", "start": 10.0, "end": 30.0},
            {"label": "chorus", "start": 30.0, "end": 50.0},
        ]
    }))
    result = remix_adapter._load_sections(sections_file)
    assert len(result) == 3
    assert result[0]["label"] == "intro"
    assert result[1]["label"] == "verse"
    assert result[2]["label"] == "chorus"


def test_load_sections_invalid_skips_bad(tmp_path):
    import json
    sections_file = tmp_path / "sections.json"
    sections_file.write_text(json.dumps({
        "sections": [
            {"label": "good", "start": 0.0, "end": 10.0},
            {"label": "bad_end", "start": 10.0, "end": 5.0},
            {"label": "missing_end", "start": 20.0},
            {"start": 0.0, "end": 5.0},
        ]
    }))
    result = remix_adapter._load_sections(sections_file)
    assert len(result) == 1
    assert result[0]["label"] == "good"


def test_load_sections_nested_structure_key(tmp_path):
    import json
    sections_file = tmp_path / "sections.json"
    sections_file.write_text(json.dumps({
        "structure": {
            "sections": [
                {"label": "intro", "start": 0.0, "end": 5.0},
                {"label": "drop", "start": 5.0, "end": 15.0},
            ]
        }
    }))
    result = remix_adapter._load_sections(sections_file)
    assert len(result) == 2
    assert result[0]["label"] == "intro"
    assert result[1]["label"] == "drop"


def test_load_sections_no_sections_raises(tmp_path):
    import json
    sections_file = tmp_path / "sections.json"
    sections_file.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(ValueError, match="No 'sections'"):
        remix_adapter._load_sections(sections_file)


def test_load_sections_all_bad_raises(tmp_path):
    import json
    sections_file = tmp_path / "sections.json"
    sections_file.write_text(json.dumps({
        "sections": [{"label": "bad", "start": 10.0, "end": 5.0}]
    }))
    with pytest.raises(ValueError, match="No valid sections"):
        remix_adapter._load_sections(sections_file)


def test_slice_by_sections_labels_and_bounds():
    sr = 22050
    audio = _sine_wave(3.0, sr=sr)
    sections = [
        {"label": "intro", "start": 0.0, "end": 1.0},
        {"label": "verse", "start": 1.0, "end": 2.0},
        {"label": "chorus", "start": 2.0, "end": 3.0},
    ]
    result = remix_adapter._slice_by_sections(audio, sr, sections)
    assert len(result) == 3
    seg, start, end, label, n = result[0]
    assert label == "intro"
    assert n == 1
    assert start == 0
    assert end == int(1.0 * sr)
    seg, start, end, label, n = result[1]
    assert label == "verse"
    assert n == 1
    seg, start, end, label, n = result[2]
    assert label == "chorus"
    assert n == 1


def test_slice_by_sections_snaps_to_beats():
    sr = 22050
    audio = _sine_wave(4.0, sr=sr)
    beat_samples = np.array([0, 11025, 22050, 33060, 44100, 55125, 66150, 88200], dtype=np.int64)
    sections = [
        {"label": "intro", "start": 0.1, "end": 1.1},
    ]
    result = remix_adapter._slice_by_sections(
        audio, sr, sections, beat_samples=beat_samples, snap_to_beats=True
    )
    assert len(result) == 1
    seg, start, end, label, n = result[0]
    assert label == "intro"
    assert n == 1
    assert start == 0
    assert end == 22050


def test_slice_by_sections_no_snap():
    sr = 22050
    audio = _sine_wave(4.0, sr=sr)
    beat_samples = np.array([0, 11025, 22050, 33060, 44100], dtype=np.int64)
    sections = [
        {"label": "intro", "start": 0.5, "end": 1.5},
    ]
    result = remix_adapter._slice_by_sections(
        audio, sr, sections, beat_samples=beat_samples, snap_to_beats=False
    )
    assert len(result) == 1
    seg, start, end, label, n = result[0]
    assert start == int(0.5 * sr)
    assert end == int(1.5 * sr)


def test_slice_by_sections_sub_slice():
    sr = 22050
    audio = _sine_wave(4.0, sr=sr)
    beat_samples = np.array([0, 11025, 22050, 33060, 44100, 55125, 66150, 77175, 88200], dtype=np.int64)
    sections = [
        {"label": "verse", "start": 0.0, "end": 4.0},
    ]
    result = remix_adapter._slice_by_sections(
        audio, sr, sections, beat_samples=beat_samples,
        snap_to_beats=True, sub_slice_beats=2,
    )
    assert len(result) >= 2
    labels = [r[3] for r in result]
    ns = [r[4] for r in result]
    assert all(l == "verse" for l in labels)
    assert ns == list(range(1, len(result) + 1))


def test_slice_by_sections_clamps_bounds():
    sr = 22050
    audio = _sine_wave(2.0, sr=sr)
    sections = [
        {"label": "past", "start": -1.0, "end": 0.5},
        {"label": "future", "start": 1.5, "end": 10.0},
    ]
    result = remix_adapter._slice_by_sections(audio, sr, sections)
    assert len(result) == 2
    seg, start, end, label, n = result[0]
    assert start == 0
    assert end == int(0.5 * sr)
    seg, start, end, label, n = result[1]
    assert start == int(1.5 * sr)
    assert end == len(audio)


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
