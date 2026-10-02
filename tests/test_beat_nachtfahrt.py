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

