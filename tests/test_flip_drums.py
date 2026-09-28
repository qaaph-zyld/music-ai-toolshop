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


def test_drill_pattern_true_two_bar_cycle():
    """F5 (fixed properly): kick row is a genuine 2-bar cycle, not per-bar."""
    ev = drums.drill_pattern(bars=4, ghost_snare=False)
    kicks = [b for b, p, _v in ev if p == "kick"]
    bar0 = [b for b in kicks if b < 4]
    bar1 = [b - 4 for b in kicks if 4 <= b < 8]
    bar2 = [b - 8 for b in kicks if 8 <= b < 12]
    bar3 = [b - 12 for b in kicks if b >= 12]
    assert bar0 != bar1, "cycle bars must differ (was per-bar before F5 fix)"
    assert bar0 == bar2 and bar1 == bar3, "cycle must repeat every 2 bars"
    # cycle bar B drops the "a"-of-1 accent (step 3 = beat 0.75)
    assert 0.75 in bar0 and 0.75 not in bar1


def test_audit_kit_manifest_verdicts():
    """A29: kept-hit audit — pass/weak/fail + declared fallback path."""
    manifest = {"pieces": {
        "kick": {"src_rms": 0.097, "n_kept": 3,
                 "reps": [{"peak": 0.71, "file": "kick_01.wav"}]},
        "cymbal": {"src_rms": 0.0003, "n_kept": 3,
                   "reps": [{"peak": 0.026, "file": "cymbal_01.wav"}]},
        "ghost": {"src_rms": 0.0001, "n_kept": 0, "reps": []},
    }}
    rep = drums.audit_kit_manifest(manifest)
    assert rep["pieces"]["kick"]["verdict"] == "pass"
    assert rep["pieces"]["cymbal"]["verdict"] == "weak"   # thin but >= floor
    assert rep["pieces"]["ghost"]["verdict"] == "fail"
    assert rep["ok"] is False and "ghost" in rep["failed_pieces"]
    # declared (never silent) fallback path
    assert rep["classifier_path"] == drums.CLASSIFIER_PRIMARY
    assert "classify_hit" in rep["fallback_classifier"]


def test_audit_kit_manifest_checks_files(tmp_path):
    manifest = {"pieces": {"kick": {"n_kept": 1,
                "reps": [{"peak": 0.5, "file": "kick_01.wav"}]}}}
    rep = drums.audit_kit_manifest(manifest, kit_dir=tmp_path)
    assert rep["pieces"]["kick"]["verdict"] == "fail"  # file missing
    assert rep["pieces"]["kick"]["files_exist"] is False


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


# ---------------------------------------------------------------------------
# bass808 drill-spec retune (megaplan W2)
# ---------------------------------------------------------------------------

def test_808_glide_window():
    """Spec: slides sit in the 90–200 ms window."""
    assert bass808.GLIDE_MS_MIN <= bass808.GLIDE_MS_DEFAULT <= bass808.GLIDE_MS_MAX
    assert bass808.GLIDE_MS_MIN == 90.0 and bass808.GLIDE_MS_MAX == 200.0


def test_808_mono_legato_overlap_converges():
    """Mono-legato: an overlapping second note takes the pitch; no polyphony."""
    sr = SR
    notes = [
        bass808.Note808(0.0, 1.2, 38.0, 1.0),   # D2 held past the next onset
        bass808.Note808(0.5, 0.8, 45.0, 1.0),   # A2 arrives mid-note (P4 up)
    ]
    out = bass808.render_808(notes, sr, glide_ms=140.0, drive=1.0)
    import librosa
    seg = out[int(0.9 * sr) : int(1.1 * sr)]
    f0 = librosa.yin(seg, fmin=50, fmax=300, sr=sr)
    assert np.median(f0) == pytest.approx(bass808.midi_to_freq(45), rel=0.06)


def test_plan_808_line_drill_spec():
    """m3/P4 approach notes, 2–3 slides per 4 bars, landings on kicks."""
    bpm = 140.0
    beat_s = 60.0 / bpm
    # dense kick grid: sixteenth positions of the 3+3+2 rows over 8 bars
    rows = ((0, 3, 6, 8, 11, 14), (0, 6, 8, 11, 13, 14))
    kicks = sorted((bar * 4 + s / 4.0) * beat_s
                   for bar in range(8) for s in rows[bar % 2])
    notes, slides = bass808.plan_808_line(kicks, bpm=bpm, root_note=38.0,
                                          slides_per_4bars=2)
    # mono: strictly increasing onsets, every onset on a kick
    onsets = [n.start_s for n in notes]
    assert onsets == sorted(onsets) and len(set(onsets)) == len(onsets)
    assert {round(n.start_s, 6) for n in notes} <= {round(k, 6) for k in kicks}
    # pitches: only root or m3/P4-raised approaches
    assert {n.note for n in notes} <= {38.0, 41.0, 43.0}
    # slides land exactly on kicks, intervals sanctioned
    assert 4 <= len(slides) <= 6  # 8 bars at 2 per 4 bars (minus collisions)
    for sl in slides:
        assert sl["interval_st"] in bass808.SLIDE_INTERVALS_ST
        assert any(abs(sl["time_s"] - k) < 1e-3 for k in kicks)
    # per-4-bar count inside spec window
    block_s = 16 * beat_s
    counts: dict = {}
    for sl in slides:
        counts[sl["block"]] = counts.get(sl["block"], 0) + 1
    assert all(1 <= c <= 3 for c in counts.values())
    # at least one full block reaches the spec's lower bound
    assert max(counts.values()) >= 2


def test_plan_808_line_rejects_out_of_spec_density():
    kicks = [0.0, 0.5, 1.0]
    with pytest.raises(ValueError):
        bass808.plan_808_line(kicks, bpm=140.0, root_note=38.0,
                              slides_per_4bars=4)


def test_plan_808_line_empty():
    assert bass808.plan_808_line([], bpm=140.0, root_note=38.0) == ([], [])
