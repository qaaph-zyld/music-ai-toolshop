"""Tests for toolshop.melody_carrier.extractor and drum_extractor.

All model calls are mocked. Uses patch.dict("sys.modules", ...) for optional
import mocking and patch.object for adapter mocking.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pretty_midi
import pytest

from toolshop.melody_carrier import extractor
from toolshop.melody_carrier import drum_extractor


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

MOCK_STEMS = {
    "stems": {
        "vocals": Path("vocals.wav"),
        "drums": Path("drums.wav"),
        "bass": Path("bass.wav"),
        "other": Path("other.wav"),
    }
}

MOCK_ANALYSIS = {
    "bpm": 140.0,
    "key": "C#",
    "mode": "minor",
    "duration_seconds": 30.0,
    "spectral_centroid": 2500.0,
    "spectral_bandwidth": 1800.0,
    "harmonic_ratio": 0.65,
    "onset_strength": 0.8,
    "tuning_offset": 5.0,
    "instruments": {"piano": 0.9, "synth pad": 0.7},
}


def _make_mock_input_wav(tmp_path):
    """Create a dummy WAV file for tests."""
    wav_path = tmp_path / "input.wav"
    wav_path.write_bytes(b"RIFF" + b"\x00" * 100)
    return wav_path


def _mock_extract_stems_preset(input_file, preset_id="4stem", output_dir=None, **kwargs):
    """Mock extract_stems_preset that creates dummy stem files."""
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for name in ["vocals", "drums", "bass", "other"]:
            (output_dir / f"{name}.wav").write_bytes(b"RIFF" + b"\x00" * 50)
    return MOCK_STEMS


def _mock_analyze_track(path, **kwargs):
    """Mock analyze_track that returns the standard analysis dict."""
    return MOCK_ANALYSIS


# ---------------------------------------------------------------------------
# extract() — full pipeline
# ---------------------------------------------------------------------------

class TestExtract:
    @patch.object(extractor, "_check_duration")
    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_extract_full_pipeline(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        mock_check_dur,
        tmp_path,
    ):
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = _mock_analyze_track

        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = ([], "autochord")
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")

        mock_drum_instr = pretty_midi.Instrument(program=0, is_drum=True, name="drums")
        mock_drum_instr.notes.append(pretty_midi.Note(100, 36, 0.0, 0.1))
        mock_drums.return_value = mock_drum_instr

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "drill")

        assert "stage1_dir" in result
        assert "midi_files" in result
        assert "analysis" in result
        assert "stems_dir" in result
        assert set(result["midi_files"].keys()) == {"melody", "chords", "bass", "drums", "full_sketch"}

    def test_extract_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extractor.extract(tmp_path / "nonexistent.wav", tmp_path / "output", "drill")

    def test_extract_empty_genre_raises(self, tmp_path):
        wav_path = _make_mock_input_wav(tmp_path)
        with pytest.raises(ValueError, match="genre"):
            extractor.extract(wav_path, tmp_path / "output", "")

    @patch.object(extractor, "_check_duration")
    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_extract_creates_stage1_dir(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        mock_check_dur,
        tmp_path,
    ):
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = _mock_analyze_track
        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = ([], "autochord")
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")
        mock_drums.return_value = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "drill")
        assert result["stage1_dir"].exists()

    @patch.object(extractor, "_check_duration")
    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_extract_analysis_json_has_required_fields(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        mock_check_dur,
        tmp_path,
    ):
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = _mock_analyze_track
        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = (
            [{"chord": "C#:min", "start": 0.0, "end": 2.0}],
            "autochord",
        )
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")
        mock_drums.return_value = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "drill")

        analysis = result["analysis"]
        required_fields = [
            "bpm", "key", "mode", "genre", "chord_progression",
            "detected_instruments", "spectral_centroid", "spectral_bandwidth",
            "harmonic_ratio", "onset_strength", "tuning_offset",
            "duration_seconds", "melody_source", "extraction_tools",
            "drum_pattern",
        ]
        for field in required_fields:
            assert field in analysis, f"Missing field: {field}"

        analysis_json = result["stage1_dir"] / "analysis.json"
        assert analysis_json.exists()
        loaded = json.loads(analysis_json.read_text(encoding="utf-8"))
        for field in required_fields:
            assert field in loaded, f"Missing field in JSON: {field}"

    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_extract_short_duration_warning(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        tmp_path,
        capsys,
    ):
        short_analysis = dict(MOCK_ANALYSIS, duration_seconds=10.0)
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = lambda *a, **kw: short_analysis
        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = ([], "autochord")
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")
        mock_drums.return_value = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "drill")

        captured = capsys.readouterr()
        assert "15s" in captured.err
        assert "stage1_dir" in result

    @patch.object(extractor, "_check_duration")
    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_extract_genre_in_analysis(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        mock_check_dur,
        tmp_path,
    ):
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = _mock_analyze_track
        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = ([], "autochord")
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")
        mock_drums.return_value = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "lofi")
        assert result["analysis"]["genre"] == "lofi"

    @patch.object(extractor, "_check_duration")
    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_full_sketch_created(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        mock_check_dur,
        tmp_path,
    ):
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = _mock_analyze_track
        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = ([], "autochord")
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")
        mock_drums.return_value = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "drill")
        full_sketch = result["midi_files"]["full_sketch"]
        assert Path(full_sketch).exists()

    @patch.object(extractor, "_check_duration")
    @patch.object(extractor.drum_ext, "extract_drums")
    @patch.object(extractor, "_extract_bass")
    @patch.object(extractor, "_extract_chords")
    @patch.object(extractor, "_extract_melody")
    @patch.object(extractor, "_determine_melody_source")
    @patch("toolshop.stem_extractor_adapter.extract_stems_preset")
    @patch("toolshop.reverse_engineering_adapter.analyze_track")
    def test_extract_returns_paths(
        self,
        mock_analyze,
        mock_extract_stems,
        mock_melody_source,
        mock_melody,
        mock_chords,
        mock_bass,
        mock_drums,
        mock_check_dur,
        tmp_path,
    ):
        mock_extract_stems.side_effect = _mock_extract_stems_preset
        mock_analyze.side_effect = _mock_analyze_track
        mock_melody_source.return_value = (Path("vocals.wav"), "vocals")
        mock_melody.return_value = (tmp_path / "melody.mid", "basic_pitch")
        mock_chords.return_value = ([], "autochord")
        mock_bass.return_value = (tmp_path / "bass.mid", "pyin")
        mock_drums.return_value = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

        wav_path = _make_mock_input_wav(tmp_path)
        result = extractor.extract(wav_path, tmp_path / "output", "drill")

        assert isinstance(result["stage1_dir"], Path)
        assert isinstance(result["stems_dir"], Path)
        assert isinstance(result["analysis"], dict)
        assert set(result["midi_files"].keys()) == {"melody", "chords", "bass", "drums", "full_sketch"}
        for key, path in result["midi_files"].items():
            assert isinstance(path, Path), f"midi_files[{key}] is not a Path"


# ---------------------------------------------------------------------------
# _extract_melody
# ---------------------------------------------------------------------------

class TestExtractMelody:
    @patch.dict("sys.modules", {"basic_pitch": MagicMock(), "basic_pitch.inference": MagicMock()})
    def test_extract_melody_basic_pitch(self, tmp_path):
        from toolshop.melody_carrier import extractor as ext

        stem_path = tmp_path / "vocals.wav"
        stem_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_mid = tmp_path / "melody.mid"

        mock_midi = pretty_midi.PrettyMIDI(initial_tempo=140)
        instr = pretty_midi.Instrument(program=0, name="melody")
        instr.notes.append(pretty_midi.Note(100, 69, 0.0, 1.0))
        mock_midi.instruments.append(instr)

        with patch("basic_pitch.inference.predict", return_value=(None, mock_midi, None)):
            result_path, tool = ext._extract_melody(stem_path, 140.0, "C", "major", output_mid)

        assert tool == "basic_pitch"
        assert result_path.exists()

    @patch.dict("sys.modules", {"basic_pitch": None})
    def test_extract_melody_pyin_fallback(self, tmp_path):
        from toolshop.melody_carrier import extractor as ext

        stem_path = tmp_path / "vocals.wav"
        stem_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_mid = tmp_path / "melody.mid"

        sr = 22050
        n_frames = 200
        f0 = np.full(n_frames, 440.0)
        f0[::3] = np.nan
        times = np.linspace(0, 2.0, n_frames)

        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (np.zeros(sr * 2), sr)
        mock_librosa.pyin.return_value = (f0, np.ones(n_frames, dtype=bool), np.ones(n_frames))
        mock_librosa.times_like.return_value = times

        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result_path, tool = ext._extract_melody(stem_path, 140.0, "C", "major", output_mid)

        assert tool == "pyin_fallback"
        assert result_path.exists()


# ---------------------------------------------------------------------------
# _extract_chords
# ---------------------------------------------------------------------------

class TestExtractChords:
    @patch.dict("sys.modules", {"autochord": MagicMock()})
    def test_extract_chords_autochord(self, tmp_path):
        from toolshop.melody_carrier import extractor as ext

        stem_path = tmp_path / "other.wav"
        stem_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_mid = tmp_path / "chords.mid"

        lab_path = output_mid.with_suffix(".lab")
        lab_path.parent.mkdir(parents=True, exist_ok=True)
        lab_path.write_text("0.0 2.0 C:maj\n2.0 4.0 A:min\n", encoding="utf-8")

        with patch("autochord.recognize"):
            chord_prog, tool = ext._extract_chords(stem_path, output_mid, 140.0)

        assert tool == "autochord"
        assert len(chord_prog) == 2
        assert chord_prog[0]["chord"] == "C:maj"

    @patch.dict("sys.modules", {"autochord": None})
    def test_extract_chords_librosa_fallback(self, tmp_path):
        from toolshop.melody_carrier import extractor as ext

        stem_path = tmp_path / "other.wav"
        stem_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_mid = tmp_path / "chords.mid"

        mock_analysis = {
            "chord_progression": [
                {"chord": "C:maj", "start": 0.0, "end": 2.0},
                {"chord": "A:min", "start": 2.0, "end": 4.0},
            ]
        }

        with patch("toolshop.reverse_engineering_adapter.analyze_track", return_value=mock_analysis):
            chord_prog, tool = ext._extract_chords(stem_path, output_mid, 140.0)

        assert tool == "librosa_fallback"
        assert len(chord_prog) == 2


# ---------------------------------------------------------------------------
# _extract_bass
# ---------------------------------------------------------------------------

class TestExtractBass:
    def test_extract_bass_pyin(self, tmp_path):
        from toolshop.melody_carrier import extractor as ext

        stem_path = tmp_path / "bass.wav"
        stem_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_mid = tmp_path / "bass.mid"

        sr = 22050
        n_frames = 200
        f0 = np.full(n_frames, 82.41)
        times = np.linspace(0, 2.0, n_frames)

        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (np.zeros(sr * 2), sr)
        mock_librosa.pyin.return_value = (f0, np.ones(n_frames, dtype=bool), np.ones(n_frames))
        mock_librosa.times_like.return_value = times

        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result_path, tool = ext._extract_bass(stem_path, 140.0, "C", "major", output_mid)

        assert tool == "pyin"
        assert result_path.exists()

    def test_extract_bass_all_nan(self, tmp_path):
        from toolshop.melody_carrier import extractor as ext

        stem_path = tmp_path / "bass.wav"
        stem_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_mid = tmp_path / "bass.mid"

        sr = 22050
        n_frames = 200
        f0 = np.full(n_frames, np.nan)
        times = np.linspace(0, 2.0, n_frames)

        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (np.zeros(sr * 2), sr)
        mock_librosa.pyin.return_value = (f0, np.zeros(n_frames, dtype=bool), np.zeros(n_frames))
        mock_librosa.times_like.return_value = times

        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result_path, tool = ext._extract_bass(stem_path, 140.0, "C", "major", output_mid)

        assert tool == "skipped"
        assert result_path.exists()


# ---------------------------------------------------------------------------
# _determine_melody_source
# ---------------------------------------------------------------------------

class TestDetermineMelodySource:
    def test_melody_source_vocals(self, tmp_path):
        vocals_path = tmp_path / "vocals.wav"
        vocals_path.write_bytes(b"RIFF")
        other_path = tmp_path / "other.wav"
        other_path.write_bytes(b"RIFF")

        stems = {"vocals": vocals_path, "other": other_path}
        result_path, name = extractor._determine_melody_source(stems)
        assert name == "vocals"
        assert result_path == vocals_path

    def test_melody_source_other_fallback(self, tmp_path):
        other_path = tmp_path / "other.wav"
        other_path.write_bytes(b"RIFF")

        stems = {"other": other_path}
        result_path, name = extractor._determine_melody_source(stems)
        assert name == "other"
        assert result_path == other_path


# ---------------------------------------------------------------------------
# drum_extractor.extract_drums
# ---------------------------------------------------------------------------

class TestExtractDrums:
    @patch.dict("sys.modules", {"adtof_pytorch": MagicMock()})
    def test_extract_drums_adtof(self, tmp_path):
        drums_wav = tmp_path / "drums.wav"
        drums_wav.write_bytes(b"RIFF" + b"\x00" * 100)

        mock_instr = pretty_midi.Instrument(program=0, is_drum=True, name="drums")
        mock_instr.notes.append(pretty_midi.Note(100, 36, 0.0, 0.1))
        mock_instr.notes.append(pretty_midi.Note(100, 38, 0.5, 0.6))

        mock_transcribe = MagicMock(return_value=mock_instr)

        with patch("adtof_pytorch.transcribe_to_midi", mock_transcribe):
            result = drum_extractor.extract_drums(drums_wav, 140.0)

        assert isinstance(result, pretty_midi.Instrument)
        assert result.is_drum is True
        assert len(result.notes) == 2

    @patch.dict("sys.modules", {"adtof_pytorch": None})
    def test_extract_drums_librosa_fallback(self, tmp_path):
        drums_wav = tmp_path / "drums.wav"
        drums_wav.write_bytes(b"RIFF" + b"\x00" * 100)

        sr = 22050
        duration = 2.0
        y = np.zeros(int(sr * duration))
        y[1000] = 1.0
        y[11025] = 0.8
        y[22050] = 1.0

        onset_frames = np.array([0, 50, 100])
        onset_times = np.array([0.0, 0.5, 1.0])

        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (y, sr)
        mock_librosa.onset.onset_detect.return_value = onset_frames
        mock_librosa.frames_to_time.return_value = onset_times

        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result = drum_extractor.extract_drums(drums_wav, 140.0)

        assert isinstance(result, pretty_midi.Instrument)
        assert result.is_drum is True
        assert len(result.notes) > 0

    @patch.dict("sys.modules", {"adtof_pytorch": None})
    def test_extract_drums_kick_classification(self, tmp_path):
        drums_wav = tmp_path / "drums.wav"
        drums_wav.write_bytes(b"RIFF" + b"\x00" * 100)

        sr = 22050
        duration = 2.0
        y = np.zeros(int(sr * duration))
        # Low-frequency sine wave (80 Hz) at the onset → spectral centroid < 200 Hz → kick
        n_samples = int(0.05 * sr)
        t = np.arange(n_samples) / sr
        y[:n_samples] = np.sin(2 * np.pi * 80 * t)

        onset_frames = np.array([0])
        onset_times = np.array([0.0])

        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (y, sr)
        mock_librosa.onset.onset_detect.return_value = onset_frames
        mock_librosa.frames_to_time.return_value = onset_times

        with patch.dict("sys.modules", {"librosa": mock_librosa}):
            result = drum_extractor.extract_drums(drums_wav, 140.0)

        kick_notes = [n for n in result.notes if n.pitch == 36]
        assert len(kick_notes) > 0
