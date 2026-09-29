"""Tests for toolshop.flip.sample_voices — the Suno-sample west-coast voice set."""

import numpy as np
import pytest

from toolshop.flip.bed_lanes import BedNote
from toolshop.flip import sample_voices as sv

SR = 22050


def _note(start, dur, midi, vel=0.8):
    return BedNote(start_s=start, end_s=start + dur, note=midi, velocity=vel)


def _melody():
    return [_note(0.0, 0.3, 62), _note(0.34, 0.3, 65), _note(0.67, 0.5, 69)]


def _bass():
    return [_note(0.0, 1.0, 38), _note(2.7, 1.0, 46), _note(5.4, 1.0, 41)]


# ---------------------------------------------------------------------------
# Register split / humanize / chord derivation
# ---------------------------------------------------------------------------

def test_split_registers():
    bass, mel = sv.split_registers(_bass() + _melody(), split=50)
    assert [n.note for n in bass] == [38, 46, 41]
    assert [n.note for n in mel] == [62, 65, 69]


def test_humanize_deterministic_and_bounded():
    a = sv.humanize(_melody(), seed=1)
    b = sv.humanize(_melody(), seed=1)
    for x, y in zip(a, b):
        assert x.start_s == y.start_s and x.velocity == y.velocity
    for src, h in zip(_melody(), a):
        assert abs(h.start_s - src.start_s) <= 0.008 + 1e-9
        assert h.duration_s == pytest.approx(src.duration_s)


def test_derive_chords_root_from_bass():
    chords = sv.derive_chords(_bass(), _melody(), n_bars=3, bar_s=2.7)
    assert chords[0]["name"] == "Dm7"          # bass 38 = D2
    assert chords[1]["name"] == "Bbmaj7"       # bass 46 = Bb1
    assert chords[2]["name"] == "Fmaj7"        # bass 41 = F2 (diatonic)
    for c in chords:
        assert all(57 <= m <= 72 for m in c["notes"])
        assert len(c["notes"]) == 4


def test_derive_chords_fallback_cycle():
    chords = sv.derive_chords([], [], n_bars=4)
    assert [c["root_pc"] for c in chords] == [2, 10, 5, 0]  # i-VI-III-VII


def test_chord_and_root_bednotes():
    chords = sv.derive_chords([], [], n_bars=2)
    cb = sv.chord_bednotes(chords)
    rb = sv.bass_root_notes(chords)
    assert len(cb) == 8 and len(rb) == 2
    assert rb[0].note % 12 == 2  # D root in the bass octave


# ---------------------------------------------------------------------------
# Melody-legibility helpers (S2)
# ---------------------------------------------------------------------------

def test_top_line_keeps_max_pitch_per_cell():
    notes = [_note(0.0, 0.2, 38), _note(0.0, 0.2, 62), _note(0.01, 0.2, 50),
             _note(0.5, 0.2, 65), _note(0.51, 0.2, 40)]
    top = sv.top_line(notes, cell_s=0.08)
    assert [n.note for n in top] == [62, 65]


def test_legato_extends_to_next_onset():
    notes = [_note(0.0, 0.1, 62), _note(0.5, 0.1, 65)]
    out = sv.legato(notes, gap_ms=20)
    assert out[0].end_s == pytest.approx(0.48, abs=1e-3)
    assert out[1].end_s == pytest.approx(0.6, abs=1e-3)


def test_legato_respects_max_cap():
    notes = [_note(0.0, 0.1, 62), _note(5.0, 0.1, 65)]
    out = sv.legato(notes, gap_ms=20, max_s=1.0)
    assert out[0].end_s == pytest.approx(1.0)


def test_tempo_scale():
    out = sv.tempo_scale([_note(1.0, 0.5, 62)], 0.5)
    assert out[0].start_s == 0.5 and out[0].end_s == pytest.approx(0.75)


def test_swing_moves_only_odd_sixteenths():
    six = 0.1683
    notes = [_note(0.0, 0.1, 62), _note(six, 0.1, 65),
             _note(2 * six, 0.1, 67), _note(3 * six, 0.1, 69)]
    out = sv.swing(notes, six, amt=0.15)
    assert out[0].start_s == 0.0                      # beat stays
    assert out[1].start_s == pytest.approx(six * 1.15)  # odd 16th delayed
    assert out[2].start_s == pytest.approx(2 * six)
    assert out[3].start_s == pytest.approx(six * 3.15)


def test_octave_double():
    out = sv.octave_double([_note(0.0, 0.2, 62, vel=0.8)], up_st=12,
                           vel_scale=0.5)
    assert len(out) == 2
    assert out[1].note == 74 and out[1].velocity == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fn", [sv.render_rhodes, sv.render_warm_pad,
                                sv.render_gfunk_lead, sv.render_sub])
def test_voices_non_silent_stereo(fn):
    out = fn(_melody() if fn is not sv.render_sub else _bass(), sr=SR)
    assert out.ndim == 2 and out.shape[1] == 2
    assert np.abs(out).max() > 0.01
    assert np.abs(out).max() <= 1.0
    assert np.isfinite(out).all()


def test_rhodes_decays():
    out = sv.render_rhodes([_note(0.0, 0.2, 60)], sr=SR)
    mono = np.abs(out[:, 0])
    n = len(mono)
    head = mono[: n // 4].max()
    tail = mono[-n // 4:].max()
    assert tail < head


def test_rhodes_stereo_tremolo_differs():
    out = sv.render_rhodes([_note(0.0, 1.5, 60)], sr=SR)
    assert not np.allclose(out[:, 0], out[:, 1])


def test_empty_notes_return_silence():
    for fn in (sv.render_rhodes, sv.render_warm_pad, sv.render_gfunk_lead,
               sv.render_sub):
        out = fn([], sr=SR)
        assert np.abs(out).max() == 0.0


# ---------------------------------------------------------------------------
# FX chain + loop fold + mixdown
# ---------------------------------------------------------------------------

def test_west_coast_chain_shape_and_gain():
    lanes = {"rhodes": sv.render_rhodes(_melody(), sr=SR),
             "sub": sv.render_sub(_bass(), sr=SR)}
    bus = sv.west_coast_chain(lanes, sr=SR)
    assert bus.shape[1] == 2 and bus.shape[0] > 0
    assert np.isfinite(bus).all()
    assert np.abs(bus).max() > 0.01


def test_fit_loop_exact_length_and_seam():
    sr = SR
    loop_s = 1.0
    # smooth signal longer than the loop -> fold + seamless boundary
    t = np.arange(int(1.8 * sr)) / sr
    audio = np.stack([np.sin(2 * np.pi * 220 * t),
                      np.sin(2 * np.pi * 221 * t)], axis=1).astype(np.float32)
    out = sv.fit_loop(audio, sr, loop_s)
    assert out.shape[0] == int(loop_s * sr)
    # tail material folded into the head -> head differs from a plain cut
    plain = audio[: int(loop_s * sr)]
    assert not np.allclose(out[:, 0], plain[:, 0])
    # seam continuity: last sample should approach head content
    assert abs(out[-1, 0] - out[0, 0]) < 0.5


def test_fit_loop_shorter_than_loop_pads():
    audio = np.ones((SR // 2, 2), dtype=np.float32) * 0.5
    out = sv.fit_loop(audio, SR, 1.0)
    assert out.shape[0] == SR
    assert out[-1, 0] == 0.0


def test_mixdown_gains():
    lanes = {"a": np.ones((100, 2), dtype=np.float32),
             "b": np.ones((200, 2), dtype=np.float32)}
    out = sv.mixdown(lanes, {"a": 0.5})
    assert out.shape == (200, 2)
    assert out[50, 0] == pytest.approx(1.5)
    assert out[150, 0] == pytest.approx(1.0)
