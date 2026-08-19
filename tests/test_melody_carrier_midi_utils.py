"""Tests for toolshop.melody_carrier.midi_utils — MIDI creation, F0 quantization,
chord conversion, merging, saving, audio normalization, and sine rendering.

All tests use real pretty_midi/numpy (fast, no models). No @pytest.mark.slow needed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pretty_midi
import pytest
from scipy.io import wavfile

from toolshop.melody_carrier import midi_utils


# ---------------------------------------------------------------------------
# create_midi
# ---------------------------------------------------------------------------

class TestCreateMidi:
    def test_create_midi_sets_tempo(self):
        midi = midi_utils.create_midi(bpm=140.0, key="C", mode="major")
        tempo = midi.get_tempo_changes()[1][0]
        assert tempo == pytest.approx(140.0, abs=0.01)

    def test_create_midi_major_minor(self):
        midi_major = midi_utils.create_midi(bpm=120.0, key="D", mode="major")
        midi_minor = midi_utils.create_midi(bpm=120.0, key="D", mode="minor")
        # Key signature should be set
        assert len(midi_major.key_signature_changes) == 1
        assert len(midi_minor.key_signature_changes) == 1
        # D major = key_number 2, D minor = key_number 14 (pretty_midi: 0-11=major, 12-23=minor)
        assert midi_major.key_signature_changes[0].key_number == 2
        assert midi_minor.key_signature_changes[0].key_number == 14


# ---------------------------------------------------------------------------
# f0_to_notes
# ---------------------------------------------------------------------------

class TestF0ToNotes:
    def test_f0_to_notes_basic(self):
        # 440Hz = A4 = MIDI 69
        sr = 22050
        frame_dur = 1.0 / sr  # not used directly; times array matters
        hop = 0.01  # 10ms hop
        n_frames = 200  # 2 seconds
        times = np.arange(n_frames) * hop
        f0 = np.full(n_frames, 440.0)
        notes = midi_utils.f0_to_notes(f0, times, sr)
        assert len(notes) == 1
        assert notes[0].pitch == 69
        assert notes[0].start == pytest.approx(0.0, abs=0.02)
        assert notes[0].end == pytest.approx(times[-1], abs=0.02)

    def test_f0_to_notes_handles_nan(self):
        sr = 22050
        hop = 0.01
        n_frames = 300
        times = np.arange(n_frames) * hop
        f0 = np.full(n_frames, 220.0)
        # Insert NaN gap in the middle
        f0[100:150] = np.nan
        notes = midi_utils.f0_to_notes(f0, times, sr)
        # Should produce 2 notes (before and after gap)
        assert len(notes) == 2
        # First note ends before gap, second starts after
        assert notes[0].end <= times[100]
        assert notes[1].start >= times[150]

    def test_f0_to_notes_min_duration(self):
        sr = 22050
        hop = 0.01
        # Create a very short voiced segment (10ms = below 50ms threshold)
        n_frames = 100
        times = np.arange(n_frames) * hop
        f0 = np.full(n_frames, np.nan)
        f0[0:2] = 440.0  # 2 frames = 20ms, below 50ms min_duration
        notes = midi_utils.f0_to_notes(f0, times, sr, min_duration_ms=50)
        assert len(notes) == 0

    def test_f0_to_notes_merges_gaps(self):
        sr = 22050
        hop = 0.01
        n_frames = 300
        times = np.arange(n_frames) * hop
        f0 = np.full(n_frames, 440.0)
        # Small gap: 5 frames = 50ms, within max_gap_ms=100
        f0[100:105] = np.nan
        notes = midi_utils.f0_to_notes(f0, times, sr, max_gap_ms=100)
        # Should merge into 1 note
        assert len(notes) == 1

    def test_f0_to_notes_empty(self):
        notes = midi_utils.f0_to_notes(np.array([]), np.array([]), 22050)
        assert notes == []

    def test_f0_to_notes_all_nan(self):
        hop = 0.01
        n_frames = 100
        times = np.arange(n_frames) * hop
        f0 = np.full(n_frames, np.nan)
        notes = midi_utils.f0_to_notes(f0, times, 22050)
        assert notes == []


# ---------------------------------------------------------------------------
# chords_to_midi
# ---------------------------------------------------------------------------

class TestChordsToMidi:
    def test_chords_to_midi_basic(self):
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        chord_prog = [
            {"chord": "C:maj", "start": 0.0, "end": 2.0},
            {"chord": "G:maj", "start": 2.0, "end": 4.0},
        ]
        instr = midi_utils.chords_to_midi(chord_prog, midi)
        # C major = C, E, G = 3 notes; G major = G, B, D = 3 notes
        assert len(instr.notes) == 6
        # C major pitches: 60, 64, 67
        pitches = sorted(n.pitch for n in instr.notes[:3])
        assert pitches == [60, 64, 67]
        # G major pitches: 67, 71, 74
        pitches2 = sorted(n.pitch for n in instr.notes[3:])
        assert pitches2 == [67, 71, 74]

    def test_chords_to_midi_timing(self):
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        chord_prog = [
            {"chord": "A:min", "start": 1.0, "end": 3.0},
        ]
        instr = midi_utils.chords_to_midi(chord_prog, midi)
        assert len(instr.notes) == 3
        for note in instr.notes:
            assert note.start == pytest.approx(1.0)
            assert note.end == pytest.approx(3.0)

    def test_chords_to_midi_empty(self):
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        instr = midi_utils.chords_to_midi([], midi)
        assert len(instr.notes) == 0


# ---------------------------------------------------------------------------
# merge_instruments
# ---------------------------------------------------------------------------

class TestMergeInstruments:
    def test_merge_instruments_multi_track(self):
        instr1 = pretty_midi.Instrument(program=0, name="melody")
        instr1.notes.append(pretty_midi.Note(100, 60, 0.0, 1.0))
        instr2 = pretty_midi.Instrument(program=33, name="bass")
        instr2.notes.append(pretty_midi.Note(80, 36, 0.0, 1.0))
        midi = midi_utils.merge_instruments([instr1, instr2], bpm=120.0)
        assert len(midi.instruments) == 2

    def test_merge_instruments_tempo(self):
        midi = midi_utils.merge_instruments([], bpm=90.0)
        tempo = midi.get_tempo_changes()[1][0]
        assert tempo == pytest.approx(90.0, abs=0.01)

    def test_merge_instruments_empty(self):
        midi = midi_utils.merge_instruments([], bpm=120.0)
        assert len(midi.instruments) == 0


# ---------------------------------------------------------------------------
# save_midi
# ---------------------------------------------------------------------------

class TestSaveMidi:
    def test_save_midi_writes_file(self, tmp_path):
        midi = midi_utils.create_midi(bpm=120.0, key="C", mode="major")
        out = tmp_path / "test.mid"
        midi_utils.save_midi(midi, out)
        assert out.exists()
        # Re-read
        reloaded = pretty_midi.PrettyMIDI(str(out))
        assert len(reloaded.instruments) >= 0  # no error

    def test_save_midi_creates_parent_dir(self, tmp_path):
        midi = midi_utils.create_midi(bpm=120.0, key="C", mode="major")
        out = tmp_path / "subdir" / "nested" / "test.mid"
        midi_utils.save_midi(midi, out)
        assert out.exists()
        assert out.parent.exists()


# ---------------------------------------------------------------------------
# normalize_audio
# ---------------------------------------------------------------------------

class TestNormalizeAudio:
    def test_normalize_audio_peak(self):
        audio = np.array([0.5, -0.3, 0.8, -0.1], dtype=np.float64)
        normalized = midi_utils.normalize_audio(audio, target_peak_db=-1.0)
        peak = np.max(np.abs(normalized))
        expected = 10 ** (-1.0 / 20.0)
        assert peak == pytest.approx(expected, abs=0.001)

    def test_normalize_audio_silence(self):
        audio = np.zeros(100, dtype=np.float64)
        normalized = midi_utils.normalize_audio(audio)
        assert np.all(normalized == 0)
        assert normalized.shape == audio.shape

    def test_normalize_audio_custom_target(self):
        audio = np.array([0.5, -0.3, 0.8], dtype=np.float64)
        normalized = midi_utils.normalize_audio(audio, target_peak_db=-3.0)
        peak = np.max(np.abs(normalized))
        expected = 10 ** (-3.0 / 20.0)
        assert peak == pytest.approx(expected, abs=0.001)


# ---------------------------------------------------------------------------
# render_sine
# ---------------------------------------------------------------------------

class TestRenderSine:
    def test_render_sine_writes_wav(self, tmp_path):
        # Create a simple MIDI with one note
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        instr = pretty_midi.Instrument(program=0)
        instr.notes.append(pretty_midi.Note(100, 69, 0.0, 1.0))  # A4
        midi.instruments.append(instr)
        midi_path = tmp_path / "test.mid"
        midi.write(str(midi_path))

        out_wav = tmp_path / "out" / "test.wav"
        midi_utils.render_sine(midi_path, out_wav, sr=44100)

        assert out_wav.exists()
        sr, data = wavfile.read(str(out_wav))
        assert sr == 44100
        assert data.dtype == np.int16

    def test_render_sine_normalized(self, tmp_path):
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        instr = pretty_midi.Instrument(program=0)
        instr.notes.append(pretty_midi.Note(100, 69, 0.0, 0.5))
        midi.instruments.append(instr)
        midi_path = tmp_path / "test.mid"
        midi.write(str(midi_path))

        out_wav = tmp_path / "test.wav"
        midi_utils.render_sine(midi_path, out_wav, sr=44100)

        sr, data = wavfile.read(str(out_wav))
        peak = np.max(np.abs(data)) / 32768.0
        peak_db = 20 * np.log10(peak)
        # Peak should be at approximately -1 dB
        assert peak_db <= 0.0  # no clipping
        assert peak_db >= -1.5  # close to -1 dB target

    def test_render_sine_correct_pitch(self, tmp_path):
        # A4 = 440 Hz = MIDI note 69
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        instr = pretty_midi.Instrument(program=0)
        instr.notes.append(pretty_midi.Note(100, 69, 0.0, 1.0))
        midi.instruments.append(instr)
        midi_path = tmp_path / "test.mid"
        midi.write(str(midi_path))

        out_wav = tmp_path / "test.wav"
        midi_utils.render_sine(midi_path, out_wav, sr=44100)

        sr, data = wavfile.read(str(out_wav))
        # Convert to float
        audio = data.astype(np.float64) / 32768.0
        # FFT to find spectral peak
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1.0 / sr)
        magnitudes = np.abs(fft)
        peak_idx = np.argmax(magnitudes)
        peak_freq = freqs[peak_idx]
        assert peak_freq == pytest.approx(440.0, abs=5.0)
