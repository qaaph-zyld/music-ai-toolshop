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


# ---------------------------------------------------------------------------
# S3 — simple recognizable motif
# ---------------------------------------------------------------------------

def _region_with_repeated_cell():
    """6 bars: the same 2-bar melodic cell twice, then a different cell.
    Bass notes sit low so top_line picks the melody contour."""
    b = sv.BAR_S
    mel = [_note(0.10, 0.30, 62), _note(0.45, 0.30, 65), _note(0.80, 0.40, 69),
           _note(0.10 + 2 * b, 0.30, 62), _note(0.45 + 2 * b, 0.30, 65),
           _note(0.80 + 2 * b, 0.40, 69),                       # repeat of cell A
           _note(0.10 + 4 * b, 0.30, 60), _note(0.60 + 4 * b, 0.30, 64)]  # cell B
    bass = [_note(0.0, 1.0, 38), _note(2 * b, 1.0, 38), _note(4 * b, 1.0, 41)]
    return mel + bass


def test_extract_motif_picks_the_repeated_cell():
    motif = sv.extract_motif(_region_with_repeated_cell(), motif_bars=2)
    assert 0 < len(motif) <= 8
    assert {n.note % 12 for n in motif} <= {2, 5, 9}     # pcs of cell A (D,F,A)


def test_extract_motif_monophonic_grid_quantized_diatonic():
    motif = sv.extract_motif(_region_with_repeated_cell(), motif_bars=2)
    grid = sv.GRID_8TH_S
    for i, n in enumerate(motif):
        assert abs(n.start_s / grid - round(n.start_s / grid)) * grid < 0.001
        assert n.note % 12 in sv.D_MINOR_PCS
        if i + 1 < len(motif):
            assert n.end_s <= motif[i + 1].start_s + 1e-9   # no overlap


def test_extract_motif_empty_source():
    assert sv.extract_motif([]) == []


def test_quantize_snaps_onsets_and_is_idempotent():
    grid = 0.25
    notes = [_note(0.11, 0.20, 62), _note(0.40, 0.05, 65)]
    q = sv.quantize(notes, grid)
    assert q[0].start_s == pytest.approx(0.0) and q[0].duration_s == pytest.approx(0.25)
    assert q[1].start_s == pytest.approx(0.5) and q[1].duration_s == pytest.approx(0.25)
    q2 = sv.quantize(q, grid)
    assert [(n.start_s, n.end_s) for n in q2] == [(n.start_s, n.end_s) for n in q]


def test_tile_motif_repeats_verbatim():
    motif = [_note(0.0, 0.3, 62), _note(0.34, 0.3, 65)]
    tiled = sv.tile_motif(motif, motif_s=2.0, n_reps=3)
    assert len(tiled) == 6
    for k in range(3):
        pair = tiled[2 * k: 2 * k + 2]
        assert pair[0].start_s == pytest.approx(2.0 * k)
        assert pair[1].start_s == pytest.approx(2.0 * k + 0.34)
        assert [n.note for n in pair] == [62, 65]


def test_answer_motif_resolves_tail_to_opening_pc():
    motif = [_note(0.0, 0.3, 62), _note(0.34, 0.3, 65), _note(0.68, 0.3, 69)]
    ans = sv.answer_motif(motif, n_tail=2)
    assert len(ans) == len(motif)
    assert [n.start_s for n in ans] == [n.start_s for n in motif]   # same rhythm
    assert ans[0].note == 62 and all(n.note % 12 == 2 for n in ans[-2:])
    assert [n.note for n in motif] == [62, 65, 69]                  # input untouched


def test_render_simple_lead_clean_and_deterministic():
    mel = _melody()
    a = sv.render_simple_lead(mel, sr=SR)
    b = sv.render_simple_lead(mel, sr=SR)
    assert a.shape[1] == 2 and np.abs(a).max() > 0.01
    assert np.abs(a).max() <= 1.0 and np.isfinite(a).all()
    assert np.array_equal(a, b)                                     # deterministic
    assert np.array_equal(a[:, 0], a[:, 1])                         # plain mono tone


def test_render_simple_lead_empty_is_silence():
    out = sv.render_simple_lead([], sr=SR)
    assert np.abs(out).max() == 0.0


# ---------------------------------------------------------------------------
# S4 — recognizable riff from the RAW native-key transcription (no snapping)
# ---------------------------------------------------------------------------

G16 = sv.GRID_16TH_S
CELL = 2.0 * sv.BAR_S            # 2 bars (~5.39 s)
# F# natural minor pcs {F#,G#,A,B,C#,D,E} = {6,8,9,11,1,2,4}
FSM_PCS = {6, 8, 9, 11, 1, 2, 4}


def _fsm_cell(t0):
    """The 54-67 s riff shape in F# minor: C#5 repeated -> B4 -> C#5 ->
    A4-G#4-F#4 descent, then a second answering gesture — spanning the full
    2 bars so the legato fill actually covers the cell."""
    shape = [(0.17, 73), (0.51, 73), (0.84, 73), (1.18, 71), (1.52, 73),
             (1.86, 69), (2.19, 68), (2.53, 66),
             (2.87, 66), (3.37, 73), (3.71, 71), (4.22, 73), (4.73, 69),
             (5.05, 68)]
    return [_note(t0 + s, 0.22, m, vel=0.8) for s, m in shape]


def _raw_region(tail=True):
    """Full cell A at bars 0-2, the same cell at bars 2-4, a different
    (partial) tail cell after bar 4 — the tail must never win."""
    notes = _fsm_cell(0.0) + _fsm_cell(CELL)
    if tail:
        notes += [_note(4 * sv.BAR_S + 0.2, 0.3, 76),
                  _note(4 * sv.BAR_S + 0.9, 0.3, 79)]
    notes += [_note(0.0, 1.2, 42), _note(CELL, 1.2, 38)]   # sub-bass lane
    return notes


def test_extract_riff_register_floor():
    riff, _ = sv.extract_riff(_raw_region())
    assert riff and all(n.note >= 55 for n in riff)


def test_extract_riff_folds_octave_outlier():
    region = _raw_region()
    # a +24 transcription ghost sitting on top of the first cell
    region.append(_note(1.86, 0.2, 93, vel=0.9))            # A6
    riff, _ = sv.extract_riff(region)
    assert max(abs(b.note - a.note) for a, b in zip(riff, riff[1:])) <= 12


def test_extract_riff_full_cell_beats_partial_tail():
    riff, cell_t0 = sv.extract_riff(_raw_region())
    assert cell_t0 in (0.0, CELL)                 # a full 2-bar cell won
    assert {n.note % 12 for n in riff} <= {1, 6, 8, 9, 11}  # F#m riff pcs


def test_extract_riff_onsets_on_16th_grid():
    riff, _ = sv.extract_riff(_raw_region())
    for n in riff:
        assert abs(n.start_s / G16 - round(n.start_s / G16)) < 1e-6


def test_extract_riff_monophonic():
    riff, _ = sv.extract_riff(_raw_region())
    for a, b in zip(riff, riff[1:]):
        assert a.end_s <= b.start_s + 1e-9


def test_extract_riff_legato_fill_coverage():
    riff, _ = sv.extract_riff(_raw_region())
    stats = sv.riff_stats(riff, CELL)
    assert stats["coverage"] >= 0.6
    assert stats["n_notes"] >= 8
    assert stats["notes_per_s"] >= 1.5


def test_transpose_lands_fsm_riff_in_dm_intervals_preserved():
    riff, _ = sv.extract_riff(_raw_region())
    dm = sv.transpose(riff, -4)
    assert all(n.note % 12 in sv.D_MINOR_PCS for n in dm)
    iv_nat = [b.note - a.note for a, b in zip(riff, riff[1:])]
    iv_dm = [b.note - a.note for a, b in zip(dm, dm[1:])]
    assert iv_nat == iv_dm


def test_estimate_key_recovers_tonic_and_mode():
    # duration-weighted F# minor: tonic/dominant heavy
    fsm = [_note(i * 0.4, 0.4, m, vel=0.8)
           for i, m in enumerate([66, 66, 68, 69, 73, 73, 73, 71, 69,
                                  68, 66, 62, 64])]
    pc, mode, r = sv.estimate_key(fsm)
    assert (pc, mode) == (6, "minor") and r > 0.5
    dm = [_note(i * 0.4, 0.4, m, vel=0.8)
          for i, m in enumerate([62, 62, 64, 65, 69, 69, 69, 67, 65,
                                 64, 62, 60, 57])]
    pc, mode, r = sv.estimate_key(dm)
    assert (pc, mode) == (2, "minor") and r > 0.5


def test_estimate_key_empty():
    assert sv.estimate_key([]) == (0, "unknown", 0.0)


# ---------------------------------------------------------------------------
# S5a — tempo-synced lead delay + wail-finder metrics (synthetic data only)
# ---------------------------------------------------------------------------

def _chain_lanes():
    return {"lead": sv.render_gfunk_lead(_melody(), sr=SR),
            "sub": sv.render_sub(_bass(), sr=SR)}


def test_dotted_8th_constant():
    assert sv.DOTTED_8TH_S == pytest.approx(0.505, abs=1e-3)


def test_west_coast_chain_default_lead_delay_unchanged():
    # S2-S4 reproducibility: the default and an explicit 0.375 are identical
    a = sv.west_coast_chain(_chain_lanes(), sr=SR)
    b = sv.west_coast_chain(_chain_lanes(), sr=SR, lead_delay_s=0.375)
    assert np.array_equal(a, b)


def test_west_coast_chain_honors_lead_delay():
    a = sv.west_coast_chain(_chain_lanes(), sr=SR)
    c = sv.west_coast_chain(_chain_lanes(), sr=SR, lead_delay_s=0.505)
    assert a.shape == c.shape
    assert not np.array_equal(a, c)
    assert float(np.abs(a - c).max()) > 1e-4


def _load_script(name):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sa():
    return _load_script("ogcm_stem_audition")


def _curve(sa, fn, seconds):
    n = int(seconds / sa.HOP_S)
    t = np.arange(n) * sa.HOP_S
    return fn(t), np.ones(n, dtype=bool)


def test_glide_share_steady_vs_fast_slide(sa):
    steady, v = _curve(sa, lambda t: np.full_like(t, 69.0), 2.0)
    assert sa.glide_share(steady, v) == 0.0
    slide, v = _curve(sa, lambda t: 60.0 + 24.0 * t, 1.0)   # 1.2 st / 50 ms
    assert sa.glide_share(slide, v) > 0.9


def test_glide_share_does_not_bridge_unvoiced_gaps(sa):
    # two runs, each shorter than the 50 ms comparison span, with a big jump
    # between them: no valid pair -> no glide
    midi = np.array([60.0, 60.0, np.nan, 84.0, 84.0])
    voiced = np.array([True, True, False, True, True])
    assert sa.glide_share(midi, voiced) == 0.0


def test_vibrato_metrics_detects_5p5_hz_and_rejects_steady(sa):
    vib, v = _curve(sa, lambda t: 69.0 + 0.45 * np.sin(2 * np.pi * 5.5 * t), 2.0)
    score, depth = sa.vibrato_metrics(vib, v)
    assert score > 0.9
    assert depth == pytest.approx(0.45, abs=0.1)
    rng = np.random.RandomState(0)
    flat, v = _curve(sa, lambda t: 69.0 + 0.02 * rng.randn(len(t)), 2.0)
    _, depth_flat = sa.vibrato_metrics(flat, v)
    assert depth_flat < 0.05


def test_vibrato_metrics_ignores_runs_shorter_than_min(sa):
    short, v = _curve(sa, lambda t: 69.0 + 0.45 * np.sin(2 * np.pi * 5.5 * t), 0.3)
    assert sa.vibrato_metrics(short, v) == (0.0, 0.0)


def test_register_term_and_wail_score_ordering(sa):
    assert sa.register_term(72.0) == 1.0
    assert sa.register_term(48.0) == 0.0 and sa.register_term(102.0) == 0.0
    assert sa.register_term(54.0) == pytest.approx(0.5)
    assert sum(sa.WAIL_WEIGHTS.values()) == pytest.approx(1.0)
    wail = sa.wail_score(sa.wail_terms(0.7, 76.0, 0.4, 0.95, 0.4))
    bass = sa.wail_score(sa.wail_terms(0.7, 38.0, 0.02, 0.5, 0.02))
    assert 0.0 <= bass < wail <= 1.0


def test_timeline_bins_and_top_bins(sa):
    n = int(10.0 / sa.HOP_S)
    t = np.arange(n) * sa.HOP_S
    high = (t >= 4.0) & (t < 6.0)
    frac, cnt = sa.bin_high_register(high, np.ones(n, dtype=bool))
    top = sa.top_bins(frac, cnt, n=5)
    assert top[0]["t0_s"] == 4.0 and top[0]["mmss"] == "00:04-00:06"
    assert top[0]["high_register_frac"] == pytest.approx(1.0, abs=0.02)
    assert all(b["high_register_frac"] > 0 for b in top)
    # uncovered frames never produce a bin
    frac2, cnt2 = sa.bin_high_register(high, np.zeros(n, dtype=bool))
    assert sa.top_bins(frac2, cnt2) == []


def test_measure_stem_pyin_on_synthetic_vibrato_and_silence(sa):
    sr = sa.PYIN_SR
    t = np.arange(int(2.5 * sr)) / sr
    f = 440.0 * 2.0 ** (0.45 * np.sin(2 * np.pi * 5.5 * t) / 12.0)
    y = (0.3 * np.sin(2 * np.pi * np.cumsum(f) / sr)).astype(np.float32)
    m = sa.measure_stem(y)
    assert m["voiced_ratio"] > 0.7 and not m["silent"]
    assert m["median_midi"] == pytest.approx(69.0, abs=0.6)
    assert m["vibrato_depth_st"] > 0.25
    silent = sa.measure_stem(np.zeros(sr, dtype=np.float32))
    assert silent["silent"] and silent["wail_score"] == 0.0


# ---------------------------------------------------------------------------
# S5b — pitch-contour wail: extract / clean / transpose / scale / stats /
# render (synthetic data only, small SR), check_contour (O6), s5 helpers
# ---------------------------------------------------------------------------

CSR = 22050
CHOP = sv.CONTOUR_HOP / sv.CONTOUR_SR          # contour frame step (s)
DM_SCALE = [62, 64, 65, 67, 69, 70, 72]         # D4 E4 F4 G4 A4 Bb4 C5


def _arr_contour(midi, hop_s=CHOP, rms=0.1):
    midi = np.asarray(midi, dtype=float)
    f0 = np.where(np.isfinite(midi), 440.0 * 2.0 ** ((midi - 69.0) / 12.0),
                  np.nan)
    t = np.arange(len(midi)) * hop_s
    return sv.contour_from_arrays(t, f0, rms=np.full(len(midi), rms),
                                  hop_s=hop_s)


def _note_contour(midis, note_frames=40, gap_frames=6):
    seq = []
    for m in midis:
        seq += [float(m)] * note_frames + [np.nan] * gap_frames
    return _arr_contour(seq)


def _glide_vibrato_tone(dur=1.6):
    t = np.arange(int(dur * CSR)) / CSR
    midi = (69.0 + 3.0 * np.clip(t / 0.3, 0.0, 1.0)
            + 0.4 * np.sin(2 * np.pi * 5.5 * t))
    f = 440.0 * 2.0 ** ((midi - 69.0) / 12.0)
    return (0.3 * np.sin(2 * np.pi * np.cumsum(f) / CSR)).astype(np.float32)


def test_contour_full_cycle_glide_vibrato_survives():
    import librosa
    y = _glide_vibrato_tone()
    raw = sv.extract_f0_contour(y, CSR)
    assert raw["voiced"].mean() > 0.7
    clean = sv.clean_contour(raw)
    m = sv.contour_midi(clean)
    # truth: glide 69 -> 72, then 72 +- 0.4 st vibrato -> median ~72
    assert np.nanmedian(m) == pytest.approx(72.0, abs=0.5)
    st = sv.contour_stats(clean)
    assert st["octave_jumps"] == 0
    assert 40.0 < st["vibrato_pp_cents"] < 120.0   # ~80 cents survives
    out = sv.render_f0_lead(clean, sr=CSR, saw=0.0)
    assert out.shape[1] == 2 and float(np.abs(out).max()) > 0.05
    x = out[:, 0].astype(np.float64)
    f0 = librosa.yin(x, fmin=196.0, fmax=1500.0, sr=CSR, frame_length=1024,
                     hop_length=256)
    mid = f0[int(0.5 * CSR / 256): int(1.4 * CSR / 256)]
    assert np.median(12 * np.log2(mid / 440.0) + 69.0) == pytest.approx(
        72.0, abs=0.5)


def test_clean_contour_fixes_injected_octave_jump():
    n = 300
    t = np.arange(n) * CHOP
    truth = 69.0 + 0.3 * np.sin(2 * np.pi * 5.5 * t)
    for shift in (+12.0, -12.0):
        bad = truth.copy()
        bad[120:170] += shift
        raw = _arr_contour(bad)
        assert sv.contour_stats(raw)["octave_jumps"] >= 2
        fixed = sv.clean_contour(raw)
        assert sv.contour_stats(fixed)["octave_jumps"] == 0
        m = sv.contour_midi(fixed)
        assert np.all(np.abs(m[120:170] - truth[120:170]) < 0.5)


def test_clean_contour_keeps_real_leaps_and_drops_spikes():
    # a genuine 7 st leap across a rest is NOT an octave error
    c = _arr_contour([69.0] * 60 + [np.nan] * 30 + [76.0] * 60)
    m = sv.contour_midi(sv.clean_contour(c))
    assert np.nanmedian(m[:60]) == pytest.approx(69.0, abs=0.01)
    assert np.nanmedian(m[-60:]) == pytest.approx(76.0, abs=0.01)
    # a 1-frame +3 st spike inside a note is removed by the median filter
    spiky = np.full(80, 69.0)
    spiky[40] = 72.0
    m2 = sv.contour_midi(sv.clean_contour(_arr_contour(spiky)))
    assert np.nanmax(m2) < 69.5


def test_clean_contour_bridges_small_steps_only_and_drops_islands():
    def cleaned(gap, step, tail=40):
        return sv.clean_contour(_arr_contour(
            [69.0] * 40 + [np.nan] * gap + [69.0 + step] * tail))
    ok = cleaned(10, 2.0)
    assert ok["bridged"].sum() == 10 and ok["voiced"].all()
    assert not cleaned(25, 2.0)["bridged"].any()         # gap > 17 frames
    assert not cleaned(10, 4.0)["bridged"].any()         # step > 3 st
    # islands under 9 frames vanish; 9 frames survive
    isl = sv.clean_contour(_arr_contour([69.0] * 8 + [np.nan] * 30
                                        + [72.0] * 40))
    assert not isl["voiced"][:8].any() and isl["voiced"][-40:].all()
    keep = sv.clean_contour(_arr_contour([69.0] * 9 + [np.nan] * 30
                                         + [72.0] * 40))
    assert keep["voiced"][:9].all()


def test_transpose_contour_is_exact():
    c = _arr_contour([60.0, 62.5, np.nan, 71.25, 80.0])
    for st in (-4, 7, 0.5, 0):
        out = sv.transpose_contour(c, st)
        a, b = sv.contour_midi(c), sv.contour_midi(out)
        assert np.array_equal(np.isfinite(a), np.isfinite(b))
        assert np.allclose(b[np.isfinite(b)], a[np.isfinite(a)] + st,
                           rtol=0, atol=1e-9)
        assert np.array_equal(out["times"], c["times"])
        assert np.array_equal(out["rms"], c["rms"])


def test_time_scale_contour_scales_time_keeps_pitch():
    c = _arr_contour([60.0, 62.5, np.nan, 71.25, 80.0])
    f0_before = c["f0_hz"].copy()
    for factor in (89.1 / 105.0, 2.0):
        out = sv.time_scale_contour(c, factor)
        assert np.allclose(out["times"], c["times"] * factor, rtol=1e-12,
                           atol=0)
        assert np.array_equal(out["f0_hz"], c["f0_hz"], equal_nan=True)
        assert np.array_equal(out["rms"], c["rms"])
        assert out["hop_s"] == pytest.approx(c["hop_s"] * factor)
    assert np.array_equal(c["f0_hz"], f0_before, equal_nan=True)  # no mutation


def test_crop_and_tile_contour():
    c = _arr_contour([69.0] * 100)
    sub = sv.crop_contour(c, 50 * CHOP, 100 * CHOP)
    assert len(sub["times"]) == 50 and sub["times"][0] == pytest.approx(0.0)
    cut = sv.crop_contour(_arr_contour([69.0] * 100), 95 * CHOP, 100 * CHOP)
    assert not cut["voiced"].any()                      # 5-frame remnant
    period = 100 * CHOP
    tiled = sv.tile_contour(c, period, 3)
    assert len(tiled["times"]) == 300
    assert np.all(np.diff(tiled["times"]) > 0)
    assert tiled["times"][100] == pytest.approx(period)


def test_render_f0_lead_deterministic_finite_peak_guarded_mono_equal():
    c = _note_contour([69, 72, 76], note_frames=50, gap_frames=30)
    variants = ({}, {"sine": 0.3, "saw": 1.0, "lpf_hz": 5000.0,
                     "lpf_resonance": 0.2}, {"add_vibrato": True})
    for kw in variants:
        a = sv.render_f0_lead(c, sr=CSR, **kw)
        b = sv.render_f0_lead(c, sr=CSR, **kw)
        assert np.array_equal(a, b)
        assert a.dtype == np.float32 and a.ndim == 2 and a.shape[1] == 2
        assert np.isfinite(a).all()
        assert float(np.abs(a).max()) <= 1.0
        assert float(np.abs(a).max()) > 0.05
        assert np.array_equal(a[:, 0], a[:, 1])
        assert a.shape[0] >= int(c["times"][-1] * CSR)


def test_render_f0_lead_gates_rests_and_follows_pitch():
    c = _note_contour([69, 76], note_frames=60, gap_frames=60)
    out = sv.render_f0_lead(c, sr=CSR, saw=0.0)[:, 0].astype(np.float64)
    hop = CSR * CHOP
    rest0 = int((60 + 30) * hop)                         # middle of the rest
    assert float(np.abs(out[rest0: rest0 + int(10 * hop)]).max()) < 1e-3
    seg = out[int(20 * hop): int(50 * hop)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1.0 / CSR)[int(np.argmax(spec))]
    assert f == pytest.approx(440.0, rel=0.02)


def test_silent_input_gives_empty_contour_and_silence():
    empty = sv.extract_f0_contour(np.zeros(CSR, dtype=np.float32), CSR)
    assert len(empty["times"]) == 0 and len(empty["f0_hz"]) == 0
    assert len(sv.clean_contour(empty)["times"]) == 0
    st = sv.contour_stats(empty)
    assert st["n_voiced_frames"] == 0 and st["in_key_ratio"] == 0.0
    sil = sv.render_f0_lead(empty, sr=CSR)
    assert sil.shape == (CSR, 2) and not sil.any()
    unv = _arr_contour([np.nan] * 50)
    assert not sv.render_f0_lead(unv, sr=CSR).any()


def test_contour_stats_in_key_ratio_on_d_minor_scale():
    c = _note_contour(DM_SCALE)
    st = sv.contour_stats(c)
    assert st["in_key_ratio"] == 1.0
    assert st["n_segments"] == 7 and st["n_segments_in_key"] == 7
    assert st["octave_jumps"] == 0
    # two chromatic notes (C#4, F#4) drop the ratio to 7/9
    st2 = sv.contour_stats(_note_contour(DM_SCALE + [61, 66]))
    assert st2["in_key_ratio"] == pytest.approx(7 / 9, abs=1e-3)
    # a bend that passes through out-of-key pitches is ONE note (median)
    bend = _arr_contour(list(np.linspace(69.0, 71.0, 40)))
    segs = sv.note_segments(bend)
    assert len(segs) == 1 and segs[0]["median_midi"] == pytest.approx(70.0,
                                                                     abs=0.1)
    # legato steps with no rest still split into separate notes
    legato = sv.note_segments(_note_contour([62, 65, 69], gap_frames=0))
    assert [round(s["median_midi"]) for s in legato] == [62, 65, 69]


def test_contour_stats_voiced_coverage_and_vibrato():
    # rests longer than phrase_gap_s separate phrases and are not penalised
    c = _note_contour([69, 69], note_frames=50, gap_frames=120)
    st = sv.contour_stats(c)
    assert st["n_phrases"] == 2 and st["voiced_coverage_in_phrases"] == 1.0
    # a hole shorter than the phrase gap counts against coverage
    holey = _arr_contour([69.0] * 60 + [np.nan] * 30 + [69.0] * 60)
    assert sv.contour_stats(holey)["voiced_coverage_in_phrases"] < 0.85
    t = np.arange(200) * CHOP
    vib = _arr_contour(69.0 + 0.4 * np.sin(2 * np.pi * 5.5 * t))
    pp = sv.contour_stats(vib)["vibrato_pp_cents"]
    assert 60.0 < pp < 100.0                              # +-40 cents
    flat = sv.contour_stats(_arr_contour([69.0] * 200))
    assert flat["vibrato_pp_cents"] < 1.0 and flat["n_sustained"] == 1


# --- O6 check_contour --------------------------------------------------------

def _write_pack(tmp_path, midis, bpm=105.0, source_audio=False,
                tamper=None):
    import json
    c = _note_contour(midis)
    dm = c
    np.savez(str(tmp_path / "contour.npz"), times=dm["times"],
             f0_hz=dm["f0_hz"], voiced=dm["voiced"], rms=dm["rms"],
             f0_hz_native=sv.transpose_contour(dm, 4)["f0_hz"],
             transpose_st=np.float64(-4.0), hop_s=np.float64(dm["hop_s"]))
    stats = sv.contour_stats(dm)
    if tamper:
        stats[tamper[0]] = tamper[1]
    manifest = {"bpm": bpm, "source_audio_in_output": source_audio,
                "files": [{"file": "s5_A_layer.wav"}],
                "contour_stats": stats}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest),
                                            encoding="utf-8")
    return str(tmp_path / "manifest.json")


def test_check_contour_passes_good_pack(tmp_path):
    cc = _load_script("check_contour")
    assert cc.main(["--manifest", _write_pack(tmp_path, DM_SCALE)]) == 0


@pytest.mark.parametrize("kw", [
    {"bpm": 89.1}, {"bpm": 120.0}, {"source_audio": True},
    {"tamper": ("in_key_ratio", 0.5)},
    {"tamper": ("voiced_coverage_in_phrases", 0.9)},
])
def test_check_contour_fails_bad_packs(tmp_path, kw):
    cc = _load_script("check_contour")
    assert cc.main(["--manifest", _write_pack(tmp_path, DM_SCALE, **kw)]) == 1


def test_check_contour_reports_out_of_key_segments(tmp_path, capsys):
    cc = _load_script("check_contour")
    mp = _write_pack(tmp_path, [62, 61, 66, 64, 69])        # 2 of 5 off-key
    assert cc.main(["--manifest", mp]) == 1
    out = capsys.readouterr().out
    assert "offending segments" in out and "C#4" in out and "F#4" in out


def test_check_contour_missing_npz_fails(tmp_path):
    import json
    cc = _load_script("check_contour")
    (tmp_path / "manifest.json").write_text(json.dumps({"bpm": 105.0}),
                                            encoding="utf-8")
    assert cc.main(["--manifest", str(tmp_path / "manifest.json")]) == 1


# --- ogcm_sample s5 helpers --------------------------------------------------

@pytest.fixture(scope="module")
def om():
    return _load_script("ogcm_sample")


def test_s5_tempo_flag_only_for_s5(om):
    with pytest.raises(SystemExit):
        om.main(["--pack", "s4", "--tempo-bpm", "100"])
    with pytest.raises(SystemExit):
        om.main(["--pack", "s5", "--tempo-bpm", "-5"])


def test_s5_phrase_continues_rule(om):
    sustained = _arr_contour([69.0] * 100 + [np.nan] * 20 + [72.0] * 50)
    boundary = 50 * CHOP
    ok, why = om._phrase_continues(sustained, boundary)
    assert ok and "sustains" in why
    rest = _arr_contour([69.0] * 40 + [np.nan] * 120 + [72.0] * 50)
    ok2, _ = om._phrase_continues(rest, 60 * CHOP)
    assert not ok2
    soon = _arr_contour([69.0] * 40 + [np.nan] * 20 + [72.0] * 50)
    ok3, _ = om._phrase_continues(soon, 50 * CHOP)
    assert ok3                                          # next onset < 0.3 s


def test_s5_riff_agreement_onset_and_pitch_tolerances(om):
    six = sv.GRID_16TH_S
    riff = [_note(0.0, 0.3, 68), _note(1.0, 0.3, 66), _note(2.0, 0.3, 73)]
    segs = [{"start_s": 0.05, "median_midi": 68.4},          # match
            {"start_s": 1.0 + 0.9 * six, "median_midi": 66.0},   # match
            {"start_s": 2.0, "median_midi": 71.0}]           # 2 st off
    ag = om._riff_agreement(riff, segs, cell_s=3.0, n_cells=1)
    assert ag["riff_notes"] == 3 and ag["riff_notes_matched"] == 2
    assert ag["riff_recall"] == pytest.approx(2 / 3, abs=1e-3)
    late = [{"start_s": 0.0 + 1.3 * six, "median_midi": 68.0}]
    assert om._riff_agreement(riff, late, 3.0, 1)["riff_notes_matched"] == 0
    assert ag["offset_sweep_best_s"] == 0.0


def test_s5_level_helpers(om):
    a = np.ones((100, 2), dtype=np.float32)
    assert om._rms(a, 50) == pytest.approx(1.0)
    b = om._sum_pad(a, np.ones((150, 2), dtype=np.float32))
    assert b.shape == (150, 2) and b[0, 0] == 2.0 and b[120, 0] == 1.0