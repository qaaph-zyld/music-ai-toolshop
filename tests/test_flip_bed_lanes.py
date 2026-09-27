"""Tests for toolshop.flip.bed_lanes — W1' bed-lane spike (MIDI cleanup + numpy voices).

Covers the pure-code render path of the OGCM drill-flip melodic-bed pivot
(megaplan A22-A25/A28, F8): basic-pitch ONNX transcription -> MIDI cleanup
(quantize to the 89.1 felt grid, prune confidence<0.4 and <80 ms notes,
scale-lock to the landed key) -> numpy voice render (epiano / pad / pluck),
same technique family as `bass808.py`. pretty_midi handles MIDI I/O.
"""

from __future__ import annotations

import numpy as np
import pytest

from toolshop.flip import bed_lanes


SR = 22050


# ---------------------------------------------------------------------------
# Note model + MIDI I/O
# ---------------------------------------------------------------------------

def _note(start, end, midi=60, vel=0.8):
    return bed_lanes.BedNote(start_s=start, end_s=end, note=midi, velocity=vel)


def test_bednote_duration():
    n = _note(0.1, 0.5, midi=57, vel=0.6)
    assert n.duration_s == pytest.approx(0.4)


def test_midi_round_trip(tmp_path):
    notes = [_note(0.0, 0.5, 60, 0.8), _note(0.5, 1.0, 62, 0.7)]
    pm = bed_lanes.notes_to_pretty_midi(notes, bpm=89.1)
    out = tmp_path / "rt.mid"
    bed_lanes.save_midi(out, pm)
    loaded = bed_lanes.load_midi(out)
    notes2 = bed_lanes.pretty_midi_to_notes(loaded)
    assert len(notes2) == 2
    # pitches preserved
    assert {n.note for n in notes2} == {60, 62}
    # onsets preserved within a few ms
    assert notes2[0].start_s == pytest.approx(0.0, abs=0.02)
    assert notes2[1].start_s == pytest.approx(0.5, abs=0.02)


def test_events_to_notes_basic_pitch_shape():
    # basic-pitch note events: (start_s, end_s, midi, velocity, pitch_bends)
    events = [
        (0.0, 0.4, 60, 0.7, [0, 0]),
        (0.4, 0.9, 62, 0.5, [0]),
    ]
    notes = bed_lanes.events_to_notes(events)
    assert len(notes) == 2
    assert notes[0].note == 60 and notes[0].velocity == pytest.approx(0.7)
    assert notes[1].end_s == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Cleanup: prune low confidence + short notes
# ---------------------------------------------------------------------------

def test_prune_low_confidence_drops_below_threshold():
    notes = [_note(0, 0.3, 60, 0.5), _note(0.3, 0.6, 62, 0.39), _note(0.6, 0.9, 64, 0.4)]
    kept = bed_lanes.prune_low_confidence(notes, min_conf=0.4)
    assert len(kept) == 2
    assert {n.note for n in kept} == {60, 64}


def test_prune_short_drops_below_min_ms():
    # 50 ms and 80 ms and 200 ms notes
    notes = [_note(0, 0.05), _note(0.1, 0.18), _note(0.2, 0.4)]
    kept = bed_lanes.prune_short(notes, min_ms=80.0)
    assert len(kept) == 2
    assert {round(n.duration_s * 1000) for n in kept} == {80, 200}


def test_prune_short_boundary_inclusive():
    # exactly 80 ms is kept (>=)
    notes = [_note(0, 0.08)]
    kept = bed_lanes.prune_short(notes, min_ms=80.0)
    assert len(kept) == 1


# ---------------------------------------------------------------------------
# Cleanup: quantize to the 89.1 felt grid
# ---------------------------------------------------------------------------

def test_quantize_snaps_onset_to_grid():
    # 89.1 BPM -> beat = 0.6734 s; a 16th note = beat/4 = 0.16835 s
    # subdivision = steps per beat, so 16th-note grid => subdivision=4
    beat = 60.0 / 89.1
    sixteenth = beat / 4.0
    # a note at 0.20 s should snap to the nearest 16th (~0.16835)
    notes = [_note(0.20, 0.50)]
    q = bed_lanes.quantize_to_grid(notes, bpm=89.1, subdivision=4)
    assert q[0].start_s == pytest.approx(sixteenth, abs=1e-3)


def test_quantize_preserves_relative_order_and_count():
    notes = [_note(0.17, 0.4), _note(0.5, 0.7), _note(1.0, 1.3)]
    q = bed_lanes.quantize_to_grid(notes, bpm=89.1, subdivision=4)
    assert len(q) == 3
    assert q[0].start_s <= q[1].start_s <= q[2].start_s


def test_quantize_does_not_invert_notes():
    # two close notes must not swap order after quantize
    notes = [_note(0.30, 0.5), _note(0.34, 0.6)]
    q = bed_lanes.quantize_to_grid(notes, bpm=89.1, subdivision=4)
    assert q[0].start_s <= q[1].start_s


# ---------------------------------------------------------------------------
# Cleanup: scale-lock to landed key
# ---------------------------------------------------------------------------

def test_scale_lock_snaps_out_of_scale_to_nearest_scale_degree():
    # D natural minor: D E F G A Bb C  -> MIDI 62 64 65 67 69 70 72 (one octave)
    # an out-of-scale note (C# = 61, or D# = 63) snaps in
    notes = [_note(0, 0.3, 61, 0.8), _note(0.3, 0.6, 63, 0.8)]  # C#, D#
    locked = bed_lanes.scale_lock(notes, root="D", mode="minor")
    scale_pcs = {2, 4, 5, 7, 9, 10, 0}  # D minor pitch classes
    for n in locked:
        assert (n.note % 12) in scale_pcs


def test_scale_lock_preserves_in_scale_notes():
    notes = [_note(0, 0.3, 62, 0.8)]  # D, in D minor
    locked = bed_lanes.scale_lock(notes, root="D", mode="minor")
    assert locked[0].note == 62


def test_scale_lock_csharp_minor():
    # C# natural minor: C# D# E F# G# A B -> pcs 1,3,4,6,8,9,11
    notes = [_note(0, 0.3, 60, 0.8)]  # C, out of C# minor -> snaps to C#(1) or B(11)
    locked = bed_lanes.scale_lock(notes, root="C#", mode="minor")
    assert (locked[0].note % 12) in {1, 3, 4, 6, 8, 9, 11}


# ---------------------------------------------------------------------------
# Full cleanup pipeline
# ---------------------------------------------------------------------------

def test_cleanup_pipeline_runs_all_stages():
    events = [
        (0.18, 0.20, 61, 0.30, [0]),   # low conf -> dropped
        (0.18, 0.21, 63, 0.80, [0]),   # 30 ms -> dropped by prune_short
        (0.34, 0.70, 62, 0.80, [0]),   # kept, in D minor
        (0.70, 1.10, 65, 0.80, [0]),   # kept, in D minor (F)
    ]
    notes = bed_lanes.events_to_notes(events)
    cleaned = bed_lanes.cleanup(notes, bpm=89.1, subdivision=16,
                                min_conf=0.4, min_ms=80.0,
                                root="D", mode="minor")
    assert len(cleaned) == 2
    scale_pcs = {2, 4, 5, 7, 9, 10, 0}
    for n in cleaned:
        assert (n.note % 12) in scale_pcs
        assert n.velocity >= 0.4
        assert n.duration_s * 1000 >= 80.0


# ---------------------------------------------------------------------------
# Numpy voices
# ---------------------------------------------------------------------------

def test_render_epiano_nonzero_right_length():
    notes = [_note(0.0, 0.5, 60, 0.8), _note(0.5, 1.0, 64, 0.7)]
    audio = bed_lanes.render_epiano(notes, sr=SR)
    assert audio.dtype == np.float32
    assert audio.size > 0
    assert np.abs(audio).max() > 0.01
    # at least covers the last note end
    assert audio.size >= int(1.0 * SR) - SR // 2


def test_render_pad_nonzero_sustains():
    notes = [_note(0.0, 1.0, 60, 0.8)]
    audio = bed_lanes.render_pad(notes, sr=SR)
    assert audio.dtype == np.float32
    assert np.abs(audio).max() > 0.01
    # slow attack: peak should not be at the very first sample
    assert np.abs(audio).argmax() > SR * 0.01


def test_render_pluck_karplus_strong_decays():
    notes = [_note(0.0, 0.4, 60, 0.9)]
    audio = bed_lanes.render_pluck(notes, sr=SR)
    assert audio.dtype == np.float32
    assert np.abs(audio).max() > 0.01
    # decays: tail energy < onset energy
    n = audio.size
    head = np.abs(audio[: n // 10]).mean()
    tail = np.abs(audio[-n // 10:]).mean()
    assert tail < head


def test_render_voice_empty_notes_returns_silence():
    assert bed_lanes.render_epiano([], sr=SR).size == 0
    assert bed_lanes.render_pad([], sr=SR).size == 0
    assert bed_lanes.render_pluck([], sr=SR).size == 0


def test_render_loop_tiles_to_n_bars():
    # 8-bar felt loop at 89.1 BPM = 8*4*60/89.1 s
    notes = [_note(0.0, 0.5, 60, 0.8)]
    loop = bed_lanes.render_loop(notes, voice="epiano", bars=8, bpm=89.1, sr=SR)
    expected = int(8 * 4 * 60.0 / 89.1 * SR)
    assert loop.size == pytest.approx(expected, rel=0.02)


# ---------------------------------------------------------------------------
# Loudness match (ADR-009 helper)
# ---------------------------------------------------------------------------

def test_loudness_match_targets_within_tolerance():
    rng = np.random.default_rng(0)
    # two signals at very different levels
    loud = (rng.standard_normal(int(2 * SR)) * 0.5).astype(np.float32)
    quiet = (rng.standard_normal(int(2 * SR)) * 0.02).astype(np.float32)
    a, b = bed_lanes.loudness_match_pair(loud, quiet, sr=SR, target_lufs=-18.0)
    la = bed_lanes.measure_lufs(a, sr=SR)
    lb = bed_lanes.measure_lufs(b, sr=SR)
    assert abs(la - lb) <= 0.3
    assert abs(la - (-18.0)) <= 1.0
