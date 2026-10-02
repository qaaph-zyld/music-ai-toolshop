"""Nachtfahrt beat tests. Section: drums_synth (wave b1)."""
import numpy as np
import pytest

from toolshop.beat import drums_synth as ds

SR = 44100
PEAK_MAX = 0.892


def _pieces():
    return {
        "kick": lambda: ds.kick(SR, 1),
        "snare": lambda: ds.snare(SR, 1),
        "clap": lambda: ds.clap(SR, 1),
        "hat": lambda: ds.hat_closed(SR, 1),
        "openhat": lambda: ds.hat_open(SR, 1),
        "crash": lambda: ds.crash(SR, 1),
        "riser": lambda: ds.riser(2.0, SR, 1),
    }


def _frac(x, lo, hi):
    spec = np.abs(np.fft.rfft(x.astype(np.float64))) ** 2
    f = np.fft.rfftfreq(x.size, 1 / SR)
    return spec[(f >= lo) & (f < hi)].sum() / spec.sum()


@pytest.mark.parametrize("name", list(_pieces()))
def test_piece_basic(name):
    a, b = _pieces()[name](), _pieces()[name]()
    assert a.dtype == np.float32 and a.ndim == 1
    assert np.array_equal(a, b)
    assert np.isfinite(a).all()
    pk = float(np.max(np.abs(a)))
    assert 0.1 < pk <= PEAK_MAX
    assert np.sqrt(np.mean(a.astype(np.float64) ** 2)) > 1e-3


def test_seed_changes_noise():
    assert not np.array_equal(ds.hat_closed(SR, 1), ds.hat_closed(SR, 2))


def test_kick_fundamental():
    k = ds.kick(SR, 1)[int(0.15 * SR):int(0.40 * SR)]
    spec = np.abs(np.fft.rfft(k * np.hanning(k.size), n=1 << 18))
    f = np.fft.rfftfreq(1 << 18, 1 / SR)
    assert 45 <= f[np.argmax(spec)] <= 60


def test_hats_high():
    assert _frac(ds.hat_closed(SR, 1), 5000, SR / 2) > 0.7
    assert _frac(ds.hat_open(SR, 1), 5000, SR / 2) > 0.7


def test_snare_band():
    assert _frac(ds.snare(SR, 1), 1500, 8000) > 0.4


def test_riser_centroid_rises():
    r = ds.riser(2.0, SR, 1).astype(np.float64)
    q = r.size // 4

    def cen(x):
        s = np.abs(np.fft.rfft(x))
        return float((np.fft.rfftfreq(x.size, 1 / SR) * s).sum() / s.sum())

    assert cen(r[-q:]) > 3 * cen(r[:q])


def test_riser_ends_loud():
    r = ds.riser(2.0, SR, 1)
    assert np.max(np.abs(r[-2048:])) > 0.5 * np.max(np.abs(r))


def test_gated_reverb_gate():
    gate_ms, fade_ms = 250, 20
    x = np.zeros(SR, dtype=np.float32)
    x[:2000] = ds.snare(SR, 1)[:2000]
    x[20000:22000] = ds.snare(SR, 1)[:2000]
    y = ds.gated_reverb(x, SR, gate_ms=gate_ms, fade_ms=fade_ms)
    assert y.size == x.size + int(gate_ms * SR / 1000)
    assert np.isfinite(y).all() and np.max(np.abs(y)) > 0.01
    start = 20000 + int((gate_ms + fade_ms) * SR / 1000) + 1
    tail = y[start:]
    assert tail.size > 0
    assert 20 * np.log10(np.max(np.abs(tail)) + 1e-12) < -60


def test_one_shots_keys():
    d = ds.one_shots()
    assert set(d) == {"kick", "snare", "clap", "hat", "openhat", "crash"}
    for v in d.values():
        assert v.dtype == np.float32 and v.ndim == 1



# ---------------------------------------------------------------------------
# nachtfahrt composition + lanes (wave b2). Expected values are typed from the
# plan, not imported from the module under test.
# ---------------------------------------------------------------------------
import importlib.util
import tempfile
from pathlib import Path

from toolshop.beat import nachtfahrt as nf

PLAN_VOICINGS = {
    "Dm7": [57, 60, 62, 65], "Bbmaj7": [58, 62, 65, 69],
    "Gm7": [58, 62, 65, 67], "A7": [57, 61, 64, 67],
    "Cadd9": [60, 62, 64, 67], "Fmaj7": [57, 60, 64, 65],
}
PLAN_ROOTS = {"D": 38, "Bb": 34, "G": 31, "A": 33, "C": 36, "F": 29}
PLAN_MELODY = [
    (0, 0, 4, 74), (0, 4, 2, 77), (0, 6, 2, 76), (0, 8, 4, 74), (0, 12, 4, 72),
    (1, 0, 6, 76), (1, 6, 2, 79), (1, 8, 4, 76), (1, 12, 4, 72),
    (2, 0, 4, 77), (2, 4, 2, 76), (2, 6, 2, 74), (2, 8, 8, 69),
    (3, 0, 4, 74), (3, 4, 2, 76), (3, 6, 2, 77), (3, 8, 8, 81),
]


def _plan_progression(bar):
    v = ["Dm7", "Bbmaj7", "Gm7", "A7"]
    h = ["Bbmaj7", "Cadd9", "Dm7", "Dm7"]
    b = ["Gm7", "Bbmaj7", "Fmaj7", "A7"]
    o = ["Dm7", "Bbmaj7", "Gm7", "Dm7"]
    if bar <= 4:
        return v[bar - 1]
    if bar <= 12:
        return h[(bar - 5) % 4]
    if bar <= 28:
        return v[(bar - 13) % 4]
    if bar <= 36:
        return h[(bar - 29) % 4]
    if bar <= 52:
        return v[(bar - 37) % 4]
    if bar <= 60:
        return h[(bar - 53) % 4]
    if bar <= 68:
        return b[(bar - 61) % 4]
    if bar <= 76:
        return h[(bar - 69) % 4]
    return o[bar - 77]


def _steps(items, piece, bar):
    """16th-step positions of `piece` in 1-indexed `bar`."""
    return sorted(round((beat - (bar - 1) * 4) * 4, 3)
                  for beat, p, _v in items
                  if p == piece and (bar - 1) * 4 <= beat < bar * 4)


def _grid_steps(g):
    return [i for i, c in enumerate(g) if c == "x"]


def test_constants():
    assert (nf.BPM, nf.N_BARS, nf.SR, nf.TAIL_S, nf.KEY) == (105, 80, 44100, 4.0, "D minor")
    assert nf.BAR_S == pytest.approx(2.285714, abs=1e-6)
    assert nf.STEP_S == pytest.approx(0.142857, abs=1e-6)


def test_voicings_and_roots():
    assert nf.VOICINGS == PLAN_VOICINGS
    assert nf.ROOT_808 == PLAN_ROOTS


def test_progression_all_80_bars():
    for bar in range(1, 81):
        assert nf.chord_at(bar) == _plan_progression(bar), bar


def test_arrangement_covers_each_bar_once():
    assert nf.ARRANGEMENT == [
        ("intro", 1, 4), ("hook_a", 5, 8), ("verse1", 13, 16),
        ("hook_b", 29, 8), ("verse2", 37, 16), ("hook_c", 53, 8),
        ("bridge", 61, 8), ("hook_d", 69, 8), ("outro", 77, 4)]
    bars = [b for _n, f, k in nf.ARRANGEMENT for b in range(f, f + k)]
    assert sorted(bars) == list(range(1, 81))


def test_hook_melody_matches_plan():
    assert nf.HOOK_MELODY == PLAN_MELODY
    assert nf.HOOK_RESOLUTION == (3, 8, 8, 74)
    assert nf.HOOK_MELODY_REPEAT == PLAN_MELODY[:-1] + [(3, 8, 8, 74)]
    notes = nf._melody(5, 1, 0.9)
    assert round((notes[-1].start_s - nf._bar_t(12)) / nf.STEP_S) == 8
    assert notes[-1].note == 74
    assert nf._melody(5, 0, 0.9)[-1].note == 81


def test_drum_grids_match_plan():
    g = nf.DRUM_GRIDS
    assert g["verse_kick_A"] == "x.....x...x....."
    assert g["verse_kick_B"] == "x..x......x..x.."
    assert g["snare"] == "....x.......x..."
    assert g["verse_hat"] == "x.x.x.x.x.x.x.x."
    assert g["hook_kick"] == "x...x...x...x..."
    assert g["hook_open_hat"] == "..x...x...x...x."
    assert g["hook_hat_accents"] == [1.0, 0.6]
    assert g["verse_open_hat_step"] == 14
    assert g["verse_roll_steps"] == [12, 13, 14, 14.5, 15, 15.5]


def test_verse_drum_events():
    kick, snare, hat = nf.kick_items(), nf.snare_items(), nf.hat_items()
    assert _steps(kick, "kick", 13) == _grid_steps("x.....x...x.....")
    assert _steps(kick, "kick", 14) == _grid_steps("x..x......x..x..")
    assert _steps(snare, "snare", 13) == [4, 12]
    assert _steps(snare, "clap", 13) == [4, 12]
    assert _steps(hat, "hat", 13) == [0, 2, 4, 6, 8, 10, 12, 14]  # plain 8ths bar
    # every 4th verse bar (16, 20, ...): roll + ratchet, open hat at 14
    assert _steps(hat, "hat", 16) == [0, 2, 4, 6, 8, 10, 12, 13, 14, 14.5, 15, 15.5]
    assert _steps(hat, "openhat", 16) == [14]
    assert _steps(hat, "openhat", 15) == []
    assert _steps(hat, "openhat", 40) == [14]


def test_hook_drum_events():
    kick, hat, fx = nf.kick_items(), nf.hat_items(), nf.fx_items()
    for bar in (5, 12):
        assert _steps(kick, "kick", bar) == [0, 4, 8, 12]
        assert _steps(hat, "hat", bar) == list(range(16))
        assert _steps(hat, "openhat", bar) == [2, 6, 10, 14]
    vel = {round((b - 16) * 4): v for b, p, v in hat if p == "hat" and 16 <= b < 20}
    assert vel[0] == 1.0 and vel[1] == 0.6
    crashes = sorted(b for b, p, _v in fx if p == "crash")
    assert crashes == [4 * 4, 28 * 4, 52 * 4, 68 * 4]


def test_bridge_drum_rules():
    kick, snare = nf.kick_items(), nf.snare_items()
    for bar in (61, 62, 63, 64):
        ks = [x for x in kick if (bar - 1) * 4 <= x[0] < bar * 4]
        assert [(round((x[0] - (bar - 1) * 4) * 4), x[1]) for x in ks] == [(0, "kick_lp")]
        assert not [x for x in snare if (bar - 1) * 4 <= x[0] < bar * 4]
    for bar in (65, 66, 67, 68):
        assert _steps(kick, "kick", bar) == [0, 4, 8, 12]
    assert _steps(snare, "snare", 67) == [0, 2, 4, 6, 8, 10, 12, 14]
    roll = sorted((b, p, v) for b, p, v in snare if 67 * 4 <= b < 68 * 4)
    assert [p for _b, p, _v in roll] == [f"snare_r{i}" for i in range(16)]
    assert roll[0][2] == pytest.approx(0.4) and roll[-1][2] == pytest.approx(1.0)
    assert all(a[2] < b[2] for a, b in zip(roll, roll[1:]))
    sh = nf._shots(22050)
    assert len(sh["snare_r15"]) < len(sh["snare_r0"])  # resampled up in pitch


def test_risers_end_on_downbeat():
    fx = nf.fx_items()
    starts = sorted(b / 4 + 1 for b, p, _v in fx if p == "riser")
    assert starts == [3, 27, 51, 67]
    assert nf.RISERS == [(3, 2), (27, 2), (51, 2), (67, 2)]
    assert (3 - 1 + 2) * nf.BAR_S == pytest.approx(nf._bar_t(5))


def _bar_of(t):
    return int((t + 1e-6) // nf.BAR_S) + 1


def test_808_silent_where_no_drums():
    bars = {_bar_of(n.start_s) for n in nf.bass808_notes()}
    silent = set(range(1, 5)) | set(range(61, 65)) | set(range(77, 81))
    assert not bars & silent
    assert {65, 66, 67, 68} <= bars
    hook = [n for n in nf.bass808_notes() if _bar_of(n.start_s) == 5]
    assert [(round((n.start_s - nf._bar_t(5)) / nf.STEP_S), n.duration_s / nf.STEP_S, n.note)
            for n in hook] == [(0, 8, 34), (8, 8, 34)]


def test_808_slides_only_m3_p4():
    notes = nf.bass808_notes()
    phrases = nf.split_808_phrases(notes)
    assert sum(len(p) for p in phrases) == len(notes)
    for p in phrases:
        for a, b in zip(p, p[1:]):
            assert abs(int(a.note) - int(b.note)) in (0, 3, 5)
    assert len(phrases) > 1


def test_synthbass_only_in_hooks_one_octave_up():
    sb = nf.synthbass_notes()
    assert sb and {nf.kind_of(_bar_of(n.start_s)) for n in sb} == {"hook"}
    assert min(n.note for n in sb) == 46  # Bb2
    d_bar = [n.note for n in sb if _bar_of(n.start_s) == 7]  # Dm7 bar
    assert min(d_bar) == 50  # D3 = 808 D2 (38) + 12


def test_lead_only_in_hooks_and_bridge_front():
    bars = {_bar_of(n.start_s) for n in nf.lead_notes()}
    assert all(nf.kind_of(b) == "hook" or 61 <= b <= 64 for b in bars)
    assert {61, 62, 63, 64} <= bars and not bars & {65, 66, 67, 68}
    br = [n for n in nf.lead_notes() if _bar_of(n.start_s) in (61, 62, 63, 64)]
    assert len(br) == 17 and {n.velocity for n in br} == {0.7}


def test_hook_d_double_at_plus_12():
    main = [n for n in nf.lead_notes() if 69 <= _bar_of(n.start_s) <= 76]
    dbl = nf.lead_double_notes()
    assert len(dbl) == len(main) == 34
    assert [d.note - m.note for d, m in zip(dbl, main)] == [12] * 34
    assert all(69 <= _bar_of(n.start_s) <= 76 for n in dbl)
    assert nf.LEVELS["lead_double_db"] == -8.0


def test_stab_grids_hooks_and_verses():
    st = nf.stab_notes()
    def onsets(bar):
        return sorted({round((n.start_s - nf._bar_t(bar)) / nf.STEP_S) for n in st
                       if _bar_of(n.start_s) == bar})
    assert onsets(5) == _grid_steps("x..x..x...x..x..")
    assert onsets(6) == _grid_steps("x..x..x.x..x..x.")
    assert onsets(13) == [0] and onsets(14) == [] and onsets(15) == [0]
    assert onsets(37) == [0] and onsets(61) == [] and onsets(2) == []


def test_pad_and_arp_lanes():
    pad = nf.pad_notes()
    at = lambda b: sorted(n.note for n in pad if _bar_of(n.start_s) == b)
    assert at(44) == sorted(PLAN_VOICINGS[nf.chord_at(44)])
    assert at(45) == sorted(PLAN_VOICINGS["Dm7"] + [m + 12 for m in PLAN_VOICINGS["Dm7"]])
    assert len(at(12)) == 4 and len(at(77)) == 4
    arp = [n for n in nf.arp_notes() if _bar_of(n.start_s) == 1]
    tones = sorted(PLAN_VOICINGS["Dm7"] + [m + 12 for m in PLAN_VOICINGS["Dm7"]])
    assert [n.note for n in arp] == tones + tones[::-1]
    fc = nf.arp_cutoff_hz(np.array([0.0, nf._bar_t(5) + 1, nf._bar_t(81)]))
    assert fc[0] == pytest.approx(400.0) and fc[1] == pytest.approx(4000.0)
    assert fc[2] == pytest.approx(400.0)
    assert nf.arp_cutoff_hz(np.array([nf._bar_t(3)]))[0] == pytest.approx(
        400 * 10 ** 0.5, rel=0.01)


def test_section_map_and_hash():
    sm = nf.section_map()
    assert sum(s["n_bars"] for s in sm) == 80
    assert sm[0]["start_s"] == 0.0
    assert sm[-1]["end_s"] == pytest.approx(182.857, abs=1e-3)
    for a, b in zip(sm, sm[1:]):
        assert a["end_s"] == pytest.approx(b["start_s"]) or b["first_bar"] > a["first_bar"] + a["n_bars"] - 1
    assert nf.composition_hash() == nf.composition_hash()
    assert len(nf.composition_hash()) == 64
    assert nf.LANES == ["kick", "snare", "hats", "fx", "bass808", "synthbass",
                        "pad", "arp", "stabs", "lead"]


def test_render_lanes_smoke_slice():
    lanes = nf.render_lanes(22050, bars=(5, 6))
    assert list(lanes) == nf.LANES
    n = int((2 * nf.BAR_S + 1.0) * 22050)
    for k, x in lanes.items():
        assert x.shape == (n, 2), k
        assert np.isfinite(x).all(), k
        assert np.abs(x).max() <= 1.0, k
    assert all(np.abs(lanes[k]).max() > 0 for k in nf.LANES)  # hook bars: all present


def test_audit_hook_catches_audio_open():
    spec = importlib.util.spec_from_file_location(
        "build_nachtfahrt", Path(nf.__file__).parents[2] / "scripts" / "build_nachtfahrt.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.mid"
        _, opened = mod.audited_call(lambda: open(p, "wb").close())
        assert opened == [str(p)]
        _, opened = mod.audited_call(lambda: open(Path(d) / "x.txt", "wb").close())
        assert opened == []


# ---------------------------------------------------------------- b3: mixdown
from toolshop.beat import mixdown as mx  # noqa: E402


def _script(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(nf.__file__).parents[2] / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sidechain_dips_at_kick_times_and_recovers():
    sr = 8000
    kicks = [0.5, 1.5]
    for depth_db in (-4.0, -6.0, -2.0):
        g = mx.sidechain_gain(sr * 3, sr, kicks, depth_db)
        assert g[int(0.49 * sr)] == pytest.approx(1.0)
        at = g[4000 + 16 - 1]                         # end of the 2 ms attack
        assert 20 * np.log10(at) == pytest.approx(depth_db, abs=0.05)
        assert g[4000 + 5] > at              # attack not instant
        # exponential release: one tau after the dip ~63% of the way back
        tau_i = 4000 + 16 + 1200
        lin = 10 ** (depth_db / 20)
        assert g[tau_i] == pytest.approx(1 - (1 - lin) * np.exp(-1), abs=0.01)
        assert g[int(1.4 * sr)] == pytest.approx(1.0, abs=3e-3)   # recovered
        assert g.min() == pytest.approx(lin, abs=1e-3)


def test_kick_times_come_from_builders():
    t = mx.kick_times_s()
    assert t.size > 100 and t[0] == pytest.approx(nf.kick_events()[0].time_s)


def test_mono_low_removes_side_below_120hz():
    sr = 44100
    rng = np.random.default_rng(1)
    x = rng.standard_normal((sr * 4, 2)) * 0.1
    y = mx.mono_low(x, sr)
    mid = 0.5 * (y[:, 0] + y[:, 1])
    side = 0.5 * (y[:, 0] - y[:, 1])
    f = np.fft.rfftfreq(side.size, 1 / sr)
    ps = np.abs(np.fft.rfft(side)) ** 2
    pm = np.abs(np.fft.rfft(mid)) ** 2
    lo = f < 120
    rel = 10 * np.log10(ps[lo].sum() / pm[lo].sum())
    assert rel < -40
    # mid is untouched; high side survives
    assert np.allclose(mid, 0.5 * (x[:, 0] + x[:, 1]), atol=1e-9)
    hi = f > 300
    assert ps[hi].sum() > 0.9 * (np.abs(np.fft.rfft(0.5 * (x[:, 0] - x[:, 1]))) ** 2)[hi].sum()


def test_stems_sum_equals_premix_and_peak_target():
    rng = np.random.default_rng(2)
    proc = {k: rng.standard_normal((4000, 2)) * 0.05 for k in nf.LANES}
    stems, premix, scalar = mx.finalize(proc)
    tot = sum(stems[k].astype(np.float64) for k in nf.LANES)
    assert np.max(np.abs(tot - premix.astype(np.float64))) < 1e-6
    assert 20 * np.log10(np.abs(premix).max()) == pytest.approx(-6.0, abs=1e-3)


def test_process_lane_sum_linearity_of_mono_low():
    sr = 22050
    rng = np.random.default_rng(3)
    a = rng.standard_normal((sr, 2)) * 0.1
    b = rng.standard_normal((sr, 2)) * 0.1
    assert np.allclose(mx.mono_low(a + b, sr), mx.mono_low(a, sr) + mx.mono_low(b, sr), atol=1e-9)


def test_process_lane_smoke_slice():
    sr = 22050
    lanes = nf.render_lanes(sr, bars=(5, 6))
    kicks = mx.kick_times_s()
    for k in ("snare", "lead", "pad", "stabs", "bass808"):
        y = mx.process_lane(k, lanes[k], sr, kicks)
        assert y.shape == lanes[k].shape and np.isfinite(y).all()


def test_peaking_eq_dips_at_f0():
    sr = 44100
    b, a = mx._peaking_ba(320.0, 1.0, -3.0, sr)
    w = 2 * np.pi * 320.0 / sr
    h = np.abs(np.polyval(b, np.exp(1j * w)) / np.polyval(a, np.exp(1j * w)))
    assert 20 * np.log10(h) == pytest.approx(-3.0, abs=0.2)
    w_off = 2 * np.pi * 4000.0 / sr   # far above the dip: ~unity
    h_off = np.abs(np.polyval(b, np.exp(1j * w_off)) /
                   np.polyval(a, np.exp(1j * w_off)))
    assert abs(20 * np.log10(h_off)) < 0.5


def test_section_mask_only_hooks():
    sr = 8000
    n = int(nf.N_BARS * nf.BAR_S * sr)
    m = mx._section_mask(n, sr, ("hook",))
    hook_bar, verse_bar = 5, 14     # hook_a starts bar 5; bar 14 is verse1
    assert m[int(nf._bar_t(hook_bar + 1) * sr)] > 0.99
    assert m[int(nf._bar_t(verse_bar) * sr + sr)] == pytest.approx(0.0)
    m_v = mx._section_mask(n, sr, ("verse",))
    assert m_v[int(nf._bar_t(verse_bar) * sr + sr)] > 0.99


def test_mud_eq_biquad_actually_dips_impulse():
    # a 320 Hz burst inside a hook is attenuated; in a verse it is not.
    # lane "arp": in MUD_EQ, no send, no sidechain -> cleanest readout.
    sr = 22050
    s_in = int((nf._bar_t(6) + 1.0) * sr)            # inside hook_a
    s_out = int((nf._bar_t(13) + 1.0) * sr)          # inside verse1
    n = s_out + sr
    x = np.zeros((n, 2))
    for s in (s_in, s_out):
        burst = 0.4 * np.sin(2 * np.pi * 320 * np.arange(sr // 2) / sr)
        x[s:s + sr // 2] = burst[:, None]
    y = mx.process_lane("arp", x, sr, np.array([]))
    rin = np.sqrt(np.mean(y[s_in + 4000:s_in + 9000] ** 2))
    rout = np.sqrt(np.mean(y[s_out + 4000:s_out + 9000] ** 2))
    rin_ref = np.sqrt(np.mean(x[s_in + 4000:s_in + 9000] ** 2))
    # hook burst: lane gain -16 dB plus ~-3 dB EQ dip; verse burst: gain plus
    # the +3 dB verse lift and NO dip -> identical bursts separate by ~6 dB.
    assert 20 * np.log10(rin / rin_ref) < -18.0
    assert 20 * np.log10(rout / rin) > 3.0


def test_index_html_links_dry_stems():
    mod = _script("build_nachtfahrt")
    meas = {"numbers": {}, "section": {"lufs": {}, "rel_lu": {}}}
    html = mod._index_html(Path("x"), meas, [])
    for lane in nf.LANES:
        assert f"stems/{lane}.wav" in html
        assert f"stems_mixed/{lane}.wav" in html


def test_audit_hook_catches_libsndfile_read(tmp_path):
    mod = _script("build_nachtfahrt")
    wav = tmp_path / "probe.wav"
    sf_mod = __import__("soundfile")
    sf_mod.write(str(wav), np.zeros((8, 2), dtype=np.float32), 8000)
    _, opened = mod.audited_call(lambda: mod.sf.read(str(wav)))
    assert opened == [str(wav)]


def test_check_beat_release_fails_on_broken_dir(tmp_path):
    chk = _script("check_beat_release")
    assert chk.run(tmp_path) == 1


def test_check_beat_release_condition_functions():
    chk = _script("check_beat_release")
    good = {"intro": -9, "verse1": -4, "verse2": -4, "bridge_p1": -5, "outro": -8,
            "hook_a": 0.2, "hook_b": 0.0, "hook_c": -0.1, "hook_d": 0.0}
    res = []
    chk.section_checks(good, res)
    assert res and all(r[0] for r in res)
    bad = dict(good, verse1=-0.5, hook_d=2.0)
    res = []
    chk.section_checks(bad, res)
    assert sum(1 for r in res if not r[0]) == 2
    x = np.random.default_rng(4).standard_normal((1000, 2))
    assert chk.residual_db([x * 0.5, x * 0.5], x) < -200
    assert chk.residual_db([x * 0.5], x) == pytest.approx(-6.02, abs=0.01)
