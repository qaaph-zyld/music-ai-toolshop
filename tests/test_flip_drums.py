"""Tests for toolshop.flip.drums + bass808 — W2 drum mining and 808 voice."""

import numpy as np
import pytest

from toolshop.flip import bass808, drums


SR = 22050


def _kick(sr=SR):
    """Synthetic kick: 60 Hz sine with pitch drop + fast decay."""
    n = int(0.35 * sr)
    t = np.arange(n) / sr
    f = 120 * np.exp(-t / 0.02) + 45
    phase = np.cumsum(2 * np.pi * f / sr)
    return np.sin(phase) * np.exp(-t / 0.08) * 0.9


def _snare(sr=SR):
    """Synthetic snare: 200 Hz tone + broadband noise, ~150 ms."""
    n = int(0.15 * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(1)
    return (0.6 * np.sin(2 * np.pi * 200 * t) + 0.8 * rng.standard_normal(n)) * np.exp(-t / 0.05) * 0.5


def _hat(sr=SR):
    """Synthetic hat: highpassed noise, ~60 ms."""
    n = int(0.06 * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(2)
    noise = rng.standard_normal(n)
    # crude highpass: difference of consecutive samples lifts HF
    hp = np.diff(noise, prepend=0.0)
    return hp * np.exp(-t / 0.015) * 0.6


def test_classify_hit_labels():
    assert drums.classify_hit(_kick(), SR)[0] == "kick"
    assert drums.classify_hit(_hat(), SR)[0] == "hat"
    piece, conf = drums.classify_hit(_snare(), SR)
    assert piece in ("snare", "other")


def test_mine_one_shots_mixed_stem():
    sr = SR
    y = np.zeros(int(3.0 * sr), dtype=np.float32)
    for start_s, gen in ((0.5, _kick), (1.0, _snare), (1.5, _hat), (2.0, _kick)):
        sig = gen(sr)
        s = int(start_s * sr)
        y[s : s + len(sig)] += sig[: max(0, len(y) - s)]
    shots = drums.mine_one_shots(y, sr)
    assert len(shots) >= 4
    pieces = {s.piece for s in shots}
    assert "kick" in pieces and "hat" in pieces
    # onsets in order, roughly where we placed them
    assert shots[0].onset_s == pytest.approx(0.5, abs=0.05)


def test_mine_one_shots_piece_hint_skips_classifier():
    sr = SR
    y = np.zeros(int(1.5 * sr), dtype=np.float32)
    sig = _hat(sr)
    y[int(0.3 * sr) : int(0.3 * sr) + len(sig)] += sig
    shots = drums.mine_one_shots(y, sr, piece_hint="hat")
    assert shots and all(s.piece == "hat" and s.confidence == 1.0 for s in shots)


def test_drill_pattern_grammar():
    ev = drums.drill_pattern(bars=4, ghost_snare=True)
    snares = [b for b, p, v in ev if p == "snare" and v > 0.9]
    # half-time snare on beat 3 of each bar → beat offset 2.0 mod 4
    assert all(abs((b % 4) - 2.0) < 1e-6 for b in snares)
    ghosts = [e for e in ev if e[1] == "snare" and e[2] < 0.9]
    assert ghosts, "ghost snare missing"
    hats = [e for e in ev if e[1] == "hat"]
    # last bar contains a triplet burst: hat hits at non-sixteenth positions
    assert any(abs((e[0] % 1) - 1 / 6) < 1e-3 or abs((e[0] % 1) - 5 / 6) < 1e-3 for e in hats if int(e[0]) >= 15)
    kicks = [e for e in ev if e[1] == "kick"]
    assert kicks, "no kicks"
    openhats = [e for e in ev if e[1] == "openhat"]
    assert openhats, "open hats missing"


def test_grid_events_absolute_times():
    ev = drums.grid_events(drums.drill_pattern(bars=1, ghost_snare=False), bpm=140.0)
    beat_s = 60.0 / 140.0
    snare = next(e for e in ev if e.piece == "snare")
    assert snare.time_s == pytest.approx(2.0 * beat_s)
    assert all(e.time_s >= 0 for e in ev)


def test_render_drums_places_buffers():
    sr = SR
    kick = _kick(sr)
    events = drums.grid_events(drums.drill_pattern(bars=1, ghost_snare=False), bpm=140.0)
    out = drums.render_drums(events, {"kick": kick}, sr, total_s=2.0)
    # only kick piece provided: snare/hat events skipped, kicks audible
    assert np.abs(out).max() > 0.2
    # first kick at t=0
    assert np.abs(out[:100]).max() > 0.05


# ---------------------------------------------------------------------------
# bass808
# ---------------------------------------------------------------------------

def test_808_glide_converges():
    sr = SR
    notes = [
        bass808.Note808(0.0, 0.4, 36.0, 1.0),   # C2
        bass808.Note808(0.4, 0.6, 48.0, 1.0),   # octave slide up to C3
    ]
    out = bass808.render_808(notes, sr, glide_ms=200.0, drive=1.0)
    assert out.size > int(0.9 * sr)
    # instantaneous frequency late in note 2 ≈ midi 48
    import librosa
    seg = out[int(0.8 * sr) : int(0.95 * sr)]
    f0 = librosa.yin(seg, fmin=60, fmax=200, sr=sr)
    assert np.median(f0) == pytest.approx(bass808.midi_to_freq(48), rel=0.06)


def test_808_mono_and_decay():
    sr = SR
    notes = [bass808.Note808(0.0, 1.0, 36.0, 1.0)]
    out = bass808.render_808(notes, sr)
    assert np.abs(out).max() <= 1.01
    # envelope decays: tail quieter than body
    body = np.abs(out[int(0.05 * sr) : int(0.2 * sr)]).mean()
    tail = np.abs(out[int(0.8 * sr) : int(0.95 * sr)]).mean()
    assert tail < body


def test_808_transient_layer():
    sr = SR
    kick = _kick(sr)
    notes = [bass808.Note808(0.2, 0.5, 36.0, 1.0)]
    out = bass808.render_808(notes, sr, transient=kick, transient_gain=0.8)
    # transient region should exceed the pure-sub level at same phase
    assert np.abs(out[int(0.2 * sr) : int(0.25 * sr)]).max() > 0.5


def test_808_duck_dips_level():
    sr = SR
    notes = [bass808.Note808(0.0, 1.5, 36.0, 1.0)]
    no_duck = bass808.render_808(notes, sr, duck_times=None)
    ducked = bass808.render_808(notes, sr, duck_times=[0.5], duck_depth=0.8)
    # energy around t=0.52s lower when ducked
    i = int(0.52 * sr)
    assert np.abs(ducked[i : i + 500]).mean() < np.abs(no_duck[i : i + 500]).mean() * 0.7
