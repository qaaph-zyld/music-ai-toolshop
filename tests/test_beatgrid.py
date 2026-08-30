"""Tests for beat grid and downbeat estimation (H2-M3).

Built on synthetic click tracks where the true tempo and bar lines are known, so
these assert against real answers rather than "something came back".
"""

from __future__ import annotations

import numpy as np
import pytest

from toolshop import beatgrid


def synth_clicks(bpm=120.0, bars=8, beats_per_bar=4, sr=22050, accent=3.0):
    """Click track at a known tempo, with accented downbeats."""
    spb = 60.0 / bpm
    total = bars * beats_per_bar * spb
    y = np.zeros(int(sr * total), dtype=np.float32)
    for i in range(bars * beats_per_bar):
        idx = int(i * spb * sr)
        amp = accent if i % beats_per_bar == 0 else 1.0
        # Short decaying burst - gives onset_strength something clean to find.
        burst = np.exp(-np.linspace(0, 12, int(sr * 0.04))) * amp
        end = min(idx + burst.size, y.size)
        y[idx:end] += burst[: end - idx]
    return y / max(1e-9, np.abs(y).max()), sr


# ------------------------------------------------------------------ beat grid


def test_tempo_is_recovered_from_a_known_click_track():
    y, sr = synth_clicks(bpm=120.0, bars=8)
    g = beatgrid.analyze_beats(y, sr)
    # Allow octave errors (a classic tempo-tracking ambiguity) but not arbitrary values.
    assert any(abs(g.tempo - c) < 6 for c in (60.0, 120.0, 240.0)), f"got {g.tempo}"


def test_beat_grid_is_not_discarded():
    """The dossier used to keep only `beat_count` and throw the times away."""
    y, sr = synth_clicks(bpm=120.0, bars=8)
    g = beatgrid.analyze_beats(y, sr)
    assert len(g.beat_times) > 10
    assert g.to_dict()["beat_times"], "beat_times must survive into the output"


def test_beat_times_are_monotonic():
    y, sr = synth_clicks(bpm=128.0, bars=8)
    times = beatgrid.analyze_beats(y, sr).beat_times
    assert all(b > a for a, b in zip(times, times[1:])), "beat times must increase"


def test_median_interval_agrees_with_reported_tempo():
    """An internal cross-check: 60/interval should reproduce the tempo."""
    y, sr = synth_clicks(bpm=120.0, bars=10)
    g = beatgrid.analyze_beats(y, sr)
    implied = 60.0 / g.median_beat_interval
    assert abs(implied - g.tempo) < 2.0, f"tempo {g.tempo} vs implied {implied}"


# ------------------------------------------------------------------ downbeats


def test_downbeats_are_a_subset_of_beats():
    y, sr = synth_clicks(bpm=120.0, bars=8)
    g = beatgrid.analyze_beats(y, sr)
    beats = {round(t, 4) for t in g.beat_times}
    assert all(round(d, 4) in beats for d in g.downbeat_times)


def test_downbeats_are_spaced_one_bar_apart():
    y, sr = synth_clicks(bpm=120.0, bars=8, beats_per_bar=4)
    g = beatgrid.analyze_beats(y, sr)
    if len(g.downbeat_times) > 2:
        gaps = np.diff(g.downbeat_times)
        expected = g.median_beat_interval * 4
        assert abs(np.median(gaps) - expected) < expected * 0.3


def test_accented_downbeats_score_higher_confidence_than_a_flat_grid():
    """The confidence field must actually discriminate.

    A strongly accented click track should yield a clearer phase than one with
    every beat identical.
    """
    accented, sr = synth_clicks(bpm=120.0, bars=8, accent=4.0)
    flat, _ = synth_clicks(bpm=120.0, bars=8, accent=1.0)
    assert (
        beatgrid.analyze_beats(accented, sr).downbeat_confidence
        >= beatgrid.analyze_beats(flat, sr).downbeat_confidence
    )


def test_phase_selection_prefers_the_strongest_beats():
    beats = np.arange(16) * 0.5
    onset = np.zeros(int(16 * 0.5 * 22050 / 512) + 10)
    # Make every 4th beat (phase 2) the loudest.
    for i, t in enumerate(beats):
        onset[int(t * 22050 / 512)] = 5.0 if i % 4 == 2 else 1.0
    phase, conf = beatgrid.estimate_downbeat_phase(beats, onset, 22050)
    assert phase == 2
    assert conf > 0.3


def test_empty_input_is_handled_without_crashing():
    phase, conf = beatgrid.estimate_downbeat_phase(np.array([]), np.array([]), 22050)
    assert (phase, conf) == (0, 0.0)


# ------------------------------------------------------------------ honesty


def test_output_declares_the_assumed_time_signature():
    """Nothing here detects metre; 4/4 is assumed and must say so."""
    y, sr = synth_clicks(bpm=120.0, bars=4)
    d = beatgrid.analyze_beats(y, sr).to_dict()
    assert d["time_signature_assumed"] == "4/4"
    assert "downbeat_confidence" in d, "a bar line the caller cannot question is a fabrication"


def test_beats_per_bar_is_configurable():
    y, sr = synth_clicks(bpm=120.0, bars=6, beats_per_bar=3)
    g = beatgrid.analyze_beats(y, sr, beats_per_bar=3)
    assert g.beats_per_bar == 3
    assert g.to_dict()["time_signature_assumed"] == "3/4"


# ------------------------------------------------------------------ MIDI click


def test_click_midi_is_written_and_readable(tmp_path):
    import pretty_midi

    y, sr = synth_clicks(bpm=120.0, bars=6)
    g = beatgrid.analyze_beats(y, sr)
    out = beatgrid.write_click_midi(g, tmp_path / "click.mid")

    assert out.exists() and out.stat().st_size > 0
    pm = pretty_midi.PrettyMIDI(str(out))
    notes = pm.instruments[0].notes
    assert len(notes) == len(g.beat_times), "one click per beat"


def test_click_midi_accents_downbeats(tmp_path):
    import pretty_midi

    y, sr = synth_clicks(bpm=120.0, bars=6)
    g = beatgrid.analyze_beats(y, sr)
    pm = pretty_midi.PrettyMIDI(str(beatgrid.write_click_midi(g, tmp_path / "c.mid")))
    pitches = {n.pitch for n in pm.instruments[0].notes}

    if g.downbeat_times:
        assert beatgrid.CLICK_DOWNBEAT_NOTE in pitches, "downbeats need a distinct note"
    velocities = {n.velocity for n in pm.instruments[0].notes}
    assert len(velocities) >= 1


def test_click_midi_creates_missing_parent_directories(tmp_path):
    y, sr = synth_clicks(bpm=120.0, bars=2)
    g = beatgrid.analyze_beats(y, sr)
    out = beatgrid.write_click_midi(g, tmp_path / "nested" / "deeper" / "click.mid")
    assert out.exists()


def test_from_dict_round_trips():
    """The CLI writes the click from the dossier's serialised `beat_grid`."""
    y, sr = synth_clicks(bpm=120.0, bars=4)
    original = beatgrid.analyze_beats(y, sr)
    restored = beatgrid.BeatGrid.from_dict(original.to_dict())

    assert restored.beats_per_bar == original.beats_per_bar
    assert len(restored.beat_times) == len(original.beat_times)
    assert len(restored.downbeat_times) == len(original.downbeat_times)
    assert restored.tempo == pytest.approx(original.tempo, abs=0.01)


def test_from_dict_tolerates_a_sparse_dict():
    g = beatgrid.BeatGrid.from_dict({})
    assert g.beat_times == [] and g.beats_per_bar == beatgrid.DEFAULT_BEATS_PER_BAR


def test_click_can_be_written_from_a_restored_grid(tmp_path):
    y, sr = synth_clicks(bpm=120.0, bars=4)
    d = beatgrid.analyze_beats(y, sr).to_dict()
    out = beatgrid.write_click_midi(beatgrid.BeatGrid.from_dict(d), tmp_path / "rt.mid")
    assert out.exists() and out.stat().st_size > 0
