"""Nachtfahrt mixdown (wave b3): per-lane processing, premix, section metering.

Each processed lane is a delivered stem; the premix is the EXACT sum of the
stems times one scalar (peak -6 dBFS), so the stems stay additive.  There is no
bus compression here (glue + master live in ``scripts/build_nachtfahrt.py``).
NEVER use pedalboard Limiter in this module (see ``toolshop.flip.master``).
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy import fft as sfft
from scipy import ndimage, signal

from toolshop.beat import drums_synth
from toolshop.beat import nachtfahrt as nf

# ---- the mix recipe (all data; recorded in release_manifest.json) ----------
GAINS_DB: Dict[str, float] = {
    "kick": 0.0, "snare": -3.0, "hats": -10.0, "fx": -12.0, "bass808": -2.0,
    "synthbass": -9.0, "pad": -14.0, "arp": -16.0, "stabs": -10.0,
    "lead": -4.0,
}
HP_HZ: Dict[str, float] = {"pad": 150.0, "arp": 150.0, "stabs": 150.0,
                           "lead": 150.0, "synthbass": 90.0}
SC_DEPTH_DB: Dict[str, float] = {"bass808": -4.0, "synthbass": -6.0,
                                 "pad": -4.0, "stabs": -2.0}
SC_ATTACK_MS = 2.0
SC_RELEASE_MS = 150.0
SENDS_DB: Dict[str, float] = {"snare": -8.0, "lead": -14.0, "pad": -16.0,
                              "stabs": -18.0}
DELAY = {"seconds": 0.428571, "feedback": 0.3, "mix": 0.2}
PLATE_ROOM, HALL_ROOM, SHORT_ROOM = 0.4, 0.85, 0.2
MONO_LOW_HZ = 120.0
MONO_LOW_TAPER_HZ = 30.0
PREMIX_PEAK_DB = -6.0
SMOOTH_MS = 150.0
# Main-master loudness stage (soft-knee clipper, NOT a pedalboard Limiter):
# linear below SOFTCLIP_KNEE, tanh-rounded toward a ceiling above it.  The
# ceiling is solved per build so the true peak lands just under -1 dBTP.
SOFTCLIP_KNEE = 0.30
TP_AIM_DBTP = -1.02

# Section automation: lane -> {section kind: dB}, then {lane: [(bar0, bar1, dB)]}
# (bar ranges override kinds).  Tuned against the O1 section-loudness targets.
# The verse pad/arp lifts also feed the O6 mud guard: verses were near-empty
# in 200-500 Hz, which made the hooks-vs-verses band-share ratio explode.
AUTO_KIND: Dict[str, Dict[str, float]] = {"pad": {"verse": 4.0},
                                         "arp": {"verse": 3.0}}
AUTO_BARS: Dict[str, List[Tuple[int, int, float]]] = {"lead": [(61, 64, -4.0)]}
# Hook-side half of the mud guard (O6): a broad peaking dip centred in the
# 200-500 Hz band, applied to the mid-heavy lanes only while a hook plays.
# Blend is masked per-section with SMOOTH_MS edges, so verses keep the lanes'
# natural 200-500 Hz content.
MUD_EQ = {"lanes": ("pad", "stabs", "arp"), "f0_hz": 320.0, "q": 1.0,
          "gain_db": -3.0, "kinds": ("hook",)}


# ---- helpers ---------------------------------------------------------------
def db(x: float) -> float:
    return 10.0 ** (x / 20.0)


def kick_times_s() -> np.ndarray:
    """Kick onset times from the composition builders (not audio detection)."""
    return np.array(sorted({e.time_s for e in nf.kick_events()
                            if e.piece in ("kick", "kick_lp")}))


def sidechain_gain(n: int, sr: int, kick_times: Sequence[float], depth_db: float,
                   attack_ms: float = SC_ATTACK_MS,
                   release_ms: float = SC_RELEASE_MS) -> np.ndarray:
    """Linear gain curve: dips to ``depth_db`` over ``attack_ms`` at each kick,
    then recovers exponentially (tau = ``release_ms``)."""
    g = np.ones(n, dtype=np.float64)
    depth = 1.0 - db(depth_db)               # amount removed at full dip
    att = max(1, int(round(attack_ms * sr / 1000.0)))
    tau = release_ms * sr / 1000.0
    rel_len = int(6 * tau)
    ramp = 1.0 - depth * np.linspace(0.0, 1.0, att + 1)[1:]
    tail = 1.0 - depth * np.exp(-np.arange(1, rel_len + 1) / tau)
    shape = np.concatenate([ramp, tail])
    for t in kick_times:
        s = int(round(t * sr))
        if s >= n:
            continue
        seg = g[s:s + shape.size]
        np.minimum(seg, shape[:seg.size], out=seg)
    return g


def _hp(x: np.ndarray, sr: int, hz: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, hz, "highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def mono_low(x: np.ndarray, sr: int, f0: float = MONO_LOW_HZ,
             taper_hz: float = MONO_LOW_TAPER_HZ) -> np.ndarray:
    """M/S with the side channel removed below ``f0`` (zero-phase FFT mask,
    raised-cosine taper f0 .. f0+taper).  Linear, so it commutes with sums."""
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1])
    n = s.size
    nfft = sfft.next_fast_len(n, real=True)
    spec = sfft.rfft(s, nfft)
    f = sfft.rfftfreq(nfft, 1.0 / sr)
    mask = np.clip((f - f0) / taper_hz, 0.0, 1.0)
    mask = 0.5 - 0.5 * np.cos(np.pi * mask)
    s2 = sfft.irfft(spec * mask, nfft)[:n]
    return np.stack([m + s2, m - s2], axis=1)


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    out = np.zeros((n, 2), dtype=np.float64)
    m = min(n, x.shape[0])
    out[:m] = x[:m]
    return out


def _reverb(x: np.ndarray, sr: int, room: float, damping: float = 0.5) -> np.ndarray:
    from pedalboard import Pedalboard, Reverb
    board = Pedalboard([Reverb(room_size=room, damping=damping, wet_level=1.0,
                               dry_level=0.0, width=1.0)])
    y = board(np.ascontiguousarray(x.T, dtype=np.float32), sr).T
    return y.astype(np.float64)


def automation_db(n: int, sr: int, lane: str) -> np.ndarray:
    """Per-sample dB automation (smoothed); zeros when the lane has none."""
    kinds = AUTO_KIND.get(lane, {})
    ranges = AUTO_BARS.get(lane, [])
    if not kinds and not ranges:
        return np.zeros(n)
    rate = 1000
    nctl = int(n / sr * rate) + 2
    ctl = np.zeros(nctl)
    for bar in range(1, nf.N_BARS + 1):
        v = kinds.get(nf.SECTION_KIND[nf.section_of(bar)[0]], 0.0)
        for b0, b1, d in ranges:
            if b0 <= bar <= b1:
                v = d
        a = int(nf._bar_t(bar) * rate)
        e = int(nf._bar_t(bar + 1) * rate)
        ctl[a:e] = v
    ctl[int(nf._bar_t(nf.N_BARS + 1) * rate):] = 0.0
    ctl = ndimage.uniform_filter1d(ctl, max(1, int(SMOOTH_MS * rate / 1000)),
                                   mode="nearest")
    t = np.arange(n) / sr
    return np.interp(t, np.arange(nctl) / rate, ctl)


def _peaking_ba(f0: float, q: float, gain_db: float, sr: int):
    """RBJ peaking-EQ biquad, normalized (b, a); gain_db < 0 is a dip."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    b = np.array([1 + alpha * A, -2.0 * c, 1 - alpha * A])
    a = np.array([1 + alpha / A, -2.0 * c, 1 - alpha / A])
    return b / a[0], a / a[0]


def _section_mask(n: int, sr: int, kinds) -> np.ndarray:
    """0/1 per-sample mask, 1 inside sections whose kind is in ``kinds``."""
    rate = 1000
    nctl = int(n / sr * rate) + 2
    ctl = np.zeros(nctl)
    for s in nf.section_map():
        if nf.SECTION_KIND[s["name"]] in kinds:
            a = int(s["start_s"] * rate)
            ctl[a:min(int(s["end_s"] * rate), nctl)] = 1.0
    ctl = ndimage.uniform_filter1d(ctl, max(1, int(SMOOTH_MS * rate / 1000)),
                                   mode="nearest")
    return np.interp(np.arange(n) / sr, np.arange(nctl) / rate, ctl)


def process_lane(name: str, x: np.ndarray, sr: int,
                 kicks: np.ndarray) -> np.ndarray:
    """Gain -> HP -> sidechain -> sends -> section automation -> mono-low."""
    n = x.shape[0]
    y = x.astype(np.float64) * db(GAINS_DB[name])
    if name in HP_HZ:
        y = _hp(y, sr, HP_HZ[name])
    if name in SC_DEPTH_DB:
        y = y * sidechain_gain(n, sr, kicks, SC_DEPTH_DB[name])[:, None]
    send = db(SENDS_DB[name]) if name in SENDS_DB else 0.0
    if name == "snare":
        mono = y.mean(axis=1).astype(np.float32)
        wet = drums_synth.gated_reverb(mono, sr, wet_db=0.0).astype(np.float64)
        y = y + _fit(np.stack([wet, wet], axis=1), n) * send
    elif name == "lead":
        from pedalboard import Delay, Pedalboard
        board = Pedalboard([Delay(delay_seconds=DELAY["seconds"],
                                  feedback=DELAY["feedback"], mix=DELAY["mix"])])
        d = board(np.ascontiguousarray(y.T, dtype=np.float32), sr).T
        y = d.astype(np.float64) + _reverb(y, sr, PLATE_ROOM) * send
    elif name == "pad":
        y = y + _reverb(y, sr, HALL_ROOM) * send
    elif name == "stabs":
        y = y + _reverb(y, sr, SHORT_ROOM) * send
    a = automation_db(n, sr, name)
    if np.any(a):
        y = y * (10.0 ** (a / 20.0))[:, None]
    if name in MUD_EQ["lanes"]:
        b, aq = _peaking_ba(MUD_EQ["f0_hz"], MUD_EQ["q"], MUD_EQ["gain_db"], sr)
        yeq = signal.lfilter(b, aq, y, axis=0)
        m = _section_mask(n, sr, MUD_EQ["kinds"])[:, None]
        y = y * (1.0 - m) + yeq * m
    return mono_low(y, sr)


def mix_lanes(lanes: Dict[str, np.ndarray], sr: int
              ) -> Tuple[Dict[str, np.ndarray], np.ndarray, float]:
    """Process every lane; returns (scaled stems, premix, scalar)."""
    kicks = kick_times_s()
    proc = {k: process_lane(k, lanes[k], sr, kicks) for k in nf.LANES}
    return finalize(proc)


def finalize(proc: Dict[str, np.ndarray],
             peak_db: float = PREMIX_PEAK_DB
             ) -> Tuple[Dict[str, np.ndarray], np.ndarray, float]:
    """One scalar so the exact sum peaks at ``peak_db``; same scalar on stems."""
    total = sum(proc[k] for k in proc)
    pk = float(np.abs(total).max())
    scalar = db(peak_db) / pk if pk > 0 else 1.0
    stems = {k: (v * scalar).astype(np.float32) for k, v in proc.items()}
    premix = sum(stems[k].astype(np.float64) for k in nf.LANES if k in stems)
    return stems, premix.astype(np.float32), scalar


def soft_clip(x: np.ndarray, knee: float = SOFTCLIP_KNEE,
              ceil: float = 0.89) -> np.ndarray:
    """Deterministic soft-knee clipper used between glue and master."""
    a = np.abs(x.astype(np.float64))
    over = np.maximum(a - knee, 0.0)
    y = np.where(a <= knee, a, knee + (ceil - knee) * np.tanh(over / (ceil - knee)))
    return (np.sign(x) * y).astype(np.float32)


def loud_master(audio: np.ndarray, sr: int, target_lufs: float = -9.0,
                tp_ceiling_dbtp: float = -1.0, knee: float = SOFTCLIP_KNEE,
                max_iters: int = 24) -> Tuple[np.ndarray, dict]:
    """Drive + soft-clip to ``target_lufs`` with true peak <= ``tp_ceiling_dbtp``.

    Used for the -9 LUFS main master because ``master_audio``'s limiter loop
    flattens section dynamics (see the b3 handoff).  Deterministic, no Limiter.
    """
    from toolshop.flip.master import integrated_lufs, true_peak_dbfs
    aim = min(TP_AIM_DBTP, tp_ceiling_dbtp - 0.02)
    x = audio.astype(np.float64)
    g_db = target_lufs - integrated_lufs(audio, sr)
    ceil = 0.89
    its = []
    best = None
    for i in range(max_iters):
        y = soft_clip((x * 10 ** (g_db / 20)).astype(np.float32), knee, ceil)
        lufs = float(integrated_lufs(y, sr))
        tp = float(true_peak_dbfs(y, sr))
        its.append({"iter": i, "gain_db": round(g_db, 3), "ceil": round(ceil, 4),
                    "lufs": round(lufs, 3), "true_peak_dbtp": round(tp, 3)})
        ok = abs(lufs - target_lufs) <= 0.05 and aim - 0.1 <= tp <= tp_ceiling_dbtp
        if tp <= tp_ceiling_dbtp and (best is None or abs(lufs - target_lufs) < best[0]):
            best = (abs(lufs - target_lufs), y, its[-1])
        if ok:
            break
        g_db += (target_lufs - lufs) * 0.9
        ceil = float(np.clip(ceil * 10 ** ((aim - tp) / 20 * 0.9), knee + 0.05, 0.999))
    if best is not None and not ok:
        y = best[1]
    lufs = float(integrated_lufs(y, sr)); tp = float(true_peak_dbfs(y, sr))
    rep = {"method": "drive + soft-knee clip (mixdown.loud_master)",
           "target_lufs": target_lufs, "tp_ceiling_dbtp": tp_ceiling_dbtp,
           "knee": knee, "iterations": its,
           "final_lufs": round(lufs, 2), "final_true_peak_dbtp": round(tp, 2),
           "passed": bool(abs(lufs - target_lufs) <= 0.3 and tp <= tp_ceiling_dbtp)}
    return y, rep


def section_slices(sr: int) -> List[dict]:
    return nf.section_map()


def section_loudness(master: np.ndarray, sr: int) -> dict:
    """Integrated LUFS of each section slice + relative-to-hooks table."""
    from toolshop.flip.master import integrated_lufs
    out = {}
    for s in nf.section_map():
        a, b = int(s["start_s"] * sr), int(s["end_s"] * sr)
        out[s["name"]] = round(float(integrated_lufs(master[a:b], sr)), 2)
    hooks = [out[k] for k in out if nf.SECTION_KIND[k] == "hook"]
    ref = float(np.mean(hooks))
    rel = {k: round(v - ref, 2) for k, v in out.items()}
    return {"lufs": out, "hook_mean_lufs": round(ref, 2), "rel_lu": rel,
            "hook_spread_lu": round(max(hooks) - min(hooks), 2)}
