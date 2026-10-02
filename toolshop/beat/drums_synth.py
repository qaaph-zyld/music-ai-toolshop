"""From-scratch synthesized drum and FX one-shots for the Nachtfahrt beat.

Pure numpy + scipy.signal + pedalboard. No audio reads, no samples. Every piece
is deterministic (own seeded Generator per piece) and mono float32, peak
normalized to -1 dBFS.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from scipy import signal

PEAK = 10 ** (-1 / 20)

# fixed per-piece seed offsets so pieces never share RNG state
_OFFSETS = {"kick": 1, "snare": 2, "clap": 3, "hat": 4, "openhat": 5, "crash": 6, "riser": 7}


def _rng(seed: int, piece: str) -> np.random.Generator:
    return np.random.default_rng(int(seed) + _OFFSETS[piece])


def _t(dur_s: float, sr: int) -> np.ndarray:
    return np.arange(int(round(dur_s * sr))) / float(sr)


def _filt(x, kind, freq, sr, order=4):
    sos = signal.butter(order, freq, btype=kind, fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def _finish(x: np.ndarray, sr: int, fade_ms: float = 5.0) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64).copy()
    nf = min(x.size, max(1, int(fade_ms * sr / 1000)))
    x[-nf:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, nf)))
    pk = float(np.max(np.abs(x)))
    if pk > 0:
        x *= PEAK / pk
    return x.astype(np.float32)


def kick(sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    rng = _rng(seed, "kick")
    t = _t(0.6, sr)
    freq = 48.0 + (150.0 - 48.0) * np.exp(-t / 0.02)  # ~60 ms sweep (3 tau)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase) * np.exp(-t / 0.15)  # ~450 ms to -26 dB (3 tau)
    nc = int(0.002 * sr)
    click = np.zeros_like(t)
    click[:nc] = _filt(rng.standard_normal(nc + 64), "highpass", 2000, sr, 2)[64:64 + nc] \
        * np.hanning(nc * 2)[nc:] if nc > 0 else 0
    click *= 0.25  # about -12 dB
    return _finish(body + click, sr)


def snare(sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    rng = _rng(seed, "snare")
    t = _t(0.35, sr)
    noise = _filt(rng.standard_normal(t.size), "bandpass", [1500, 8000], sr, 4)
    noise *= np.exp(-t / 0.06)  # ~180 ms to -26 dB
    noise /= np.max(np.abs(noise))
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.027)  # ~80 ms
    return _finish(0.6 * noise + 0.4 * body, sr)


def clap(sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    rng = _rng(seed, "clap")
    t = _t(0.3, sr)
    noise = _filt(rng.standard_normal(t.size), "bandpass", [1000, 3000], sr, 4)
    env = np.zeros_like(t)
    for k in range(3):
        s = int(k * 0.010 * sr)
        n = int(0.006 * sr)
        env[s:s + n] = np.maximum(env[s:s + n], np.exp(-np.arange(n) / (0.002 * sr)))
    s = int(0.030 * sr)
    env[s:] = np.maximum(env[s:], 0.6 * np.exp(-(t[s:] - t[s]) / 0.04))  # ~120 ms tail
    return _finish(noise * env, sr)


def _hat(piece: str, dur_s: float, decay_s: float, sr: int, seed: int) -> np.ndarray:
    rng = _rng(seed, piece)
    t = _t(dur_s, sr)
    noise = _filt(rng.standard_normal(t.size), "highpass", 7000, sr, 4)
    return _finish(noise * np.exp(-t / (decay_s / 3.0)), sr)


def hat_closed(sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    return _hat("hat", 0.12, 0.045, sr, seed)


def hat_open(sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    return _hat("openhat", 0.5, 0.300, sr, seed)


def crash(sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    rng = _rng(seed, "crash")
    t = _t(2.5, sr)
    noise = _filt(rng.standard_normal(t.size), "highpass", 4000, sr, 4)
    noise /= np.max(np.abs(noise))
    partials = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) for f in (3100.0, 4700.0, 6200.0))
    x = noise + 0.08 * partials
    return _finish(x * np.exp(-t / 0.6), sr, fade_ms=20.0)  # ~1.8 s to -26 dB


def riser(duration_s: float, sr: int = 44100, seed: int = 20261002) -> np.ndarray:
    rng = _rng(seed, "riser")
    n = int(round(duration_s * sr))
    noise = rng.standard_normal(n)
    block = 512
    out = np.zeros(n)
    zi = None
    nb = (n + block - 1) // block
    for b in range(nb):
        a, e = b * block, min(n, (b + 1) * block)
        frac = (a + (e - a) / 2) / max(1, n)
        fc = 300.0 * (8000.0 / 300.0) ** frac
        sos = signal.butter(2, fc, btype="lowpass", fs=sr, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[a:e], zi = signal.sosfilt(sos, noise[a:e], zi=zi)
    db = np.linspace(-30.0, 0.0, n)
    out *= 10 ** (db / 20)
    pk = float(np.max(np.abs(out)))
    out *= PEAK / pk
    return out.astype(np.float32)  # no end fade: ends at full level


def _onsets(x: np.ndarray, sr: int) -> np.ndarray:
    env = np.abs(x)
    w = max(1, int(0.005 * sr))
    env = np.convolve(env, np.ones(w) / w, mode="same")
    thr = 0.1 * float(env.max()) if env.size else 0.0
    above = env > thr
    return np.flatnonzero(above & ~np.concatenate(([False], above[:-1]))) if thr > 0 else np.array([], int)


def gated_reverb(x, sr: int = 44100, room_size: float = 0.8, wet_db: float = -6.0,
                 gate_ms: float = 250.0, fade_ms: float = 20.0) -> np.ndarray:
    from pedalboard import Pedalboard, Reverb

    x = np.asarray(x, dtype=np.float32)
    gate = int(gate_ms * sr / 1000)
    fade = int(fade_ms * sr / 1000)
    n_out = x.size + gate
    padded = np.zeros(n_out + sr, dtype=np.float32)
    padded[:x.size] = x
    board = Pedalboard([Reverb(room_size=room_size, damping=0.5,
                               wet_level=10 ** (wet_db / 20), dry_level=0.0, width=1.0)])
    wet = board(padded[None, :], sr)[0][:n_out]
    mask = np.zeros(n_out)
    ramp = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade, endpoint=False))) if fade > 0 else np.zeros(0)
    for o in _onsets(x, sr):
        mask[o:o + gate] = 1.0
        seg = mask[o + gate:o + gate + fade]
        mask[o + gate:o + gate + fade] = np.maximum(seg, ramp[:seg.size])
    return (wet * mask).astype(np.float32)


def one_shots(sr: int = 44100, seed: int = 20261002) -> Dict[str, np.ndarray]:
    """Keys compatible with flip.drums.render_drums."""
    return {
        "kick": kick(sr, seed),
        "snare": snare(sr, seed),
        "clap": clap(sr, seed),
        "hat": hat_closed(sr, seed),
        "openhat": hat_open(sr, seed),
        "crash": crash(sr, seed),
    }
