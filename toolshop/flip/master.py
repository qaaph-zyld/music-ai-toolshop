"""W5 mastering stage for the OGCM flip — finding F9.

`toolshop.premaster` only *analyzes* a mix against the acceptance gates; this
module is the mastering half the megaplan flagged as missing (F9): integrated
loudness normalization via pyloudnorm (BS.1770) to a target LUFS, then a
pedalboard limiter against a true-peak ceiling, iterated until both specs hold
or the report honestly says they don't.

Pipeline per file: ``mix_lanes`` (deterministic beat+vocal sum with a recorded
clip guard) -> ``master_audio`` (gain-to-target -> Limiter -> 4x-oversampled
true-peak check -> trim -> repeat) -> caller writes WAV + verifies.

Everything here is deterministic: fixed limiter settings, fixed iteration cap,
no randomness. True peak is the same documented approximation as
`premaster.true_peak_dbfs` (4x polyphase, not a certified BS.1770-4 meter).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from toolshop.premaster import true_peak_dbfs as _tp_mono
from toolshop.flip.bed_lanes import measure_lufs

#: Streaming target loudness (megaplan W5).
TARGET_LUFS = -14.0
#: Optional club arm (megaplan W5 "+optional -9 club").
CLUB_LUFS = -9.0
#: Allowed error on integrated loudness after mastering.
LUFS_TOLERANCE = 0.3
#: True-peak ceiling (dBTP, 4x-oversampled approximation).
TP_CEILING_DBTP = -1.0
#: Never apply more than this much gain in one normalize step — guards against
#: exploding near-silent/unmeasurable inputs (pyloudnorm returns ~-70 there).
MAX_GAIN_DB = 30.0
#: Normalize -> limit -> verify loop bound; converges in 2-3 in practice,
#: but hard-driven club (-9 LUFS) material needs ~6.
MAX_ITERS = 8
#: Peak the mix clip-guard rescales to (same convention as assemble.render_beat).
MIX_CLIP_GUARD = 0.99


def _as_2d(audio: np.ndarray) -> np.ndarray:
    """Return (samples, channels); mono 1-D becomes (n, 1)."""
    a = np.asarray(audio, dtype=np.float32)
    return a.reshape(-1, 1) if a.ndim == 1 else a


def integrated_lufs(audio: np.ndarray, sr: int) -> float:
    """Integrated loudness (BS.1770 via pyloudnorm; -70 on unmeasurable)."""
    return measure_lufs(_as_2d(audio), sr)


def true_peak_dbfs(audio: np.ndarray, sr: int) -> float:
    """Worst-channel true-peak estimate (4x polyphase, per premaster)."""
    a = _as_2d(audio)
    return max((_tp_mono(a[:, c]) for c in range(a.shape[1])), default=-np.inf)


def mix_lanes(beat: np.ndarray, vocal: np.ndarray,
              beat_gain: float = 1.0, vocal_gain: float = 1.0
              ) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Deterministic beat+vocal sum; zero-pads the shorter lane at the tail.

    Returns (mix, info) — info records per-lane peaks, applied gains, the
    pre-guard peak and whether the clip guard fired, so callers can persist it.
    """
    b = _as_2d(beat)
    v = _as_2d(vocal)
    n = max(b.shape[0], v.shape[0])
    ch = max(b.shape[1], v.shape[1])

    def _fit(x: np.ndarray) -> np.ndarray:
        out = np.zeros((n, ch), dtype=np.float64)
        c = min(ch, x.shape[1])
        out[: x.shape[0], :c] = x[:, :c]
        if x.shape[1] < ch:  # mono lane into stereo mix: duplicate
            out[: x.shape[0], x.shape[1]:] = x[:, :1]
        return out

    mix = _fit(b) * beat_gain + _fit(v) * vocal_gain
    pre_peak = float(np.abs(mix).max()) if mix.size else 0.0
    guarded = pre_peak > MIX_CLIP_GUARD
    if guarded:
        mix = mix * (MIX_CLIP_GUARD / pre_peak)
    info = {
        "beat_gain": beat_gain,
        "vocal_gain": vocal_gain,
        "beat_peak": float(np.abs(b).max()) if b.size else 0.0,
        "vocal_peak": float(np.abs(v).max()) if v.size else 0.0,
        "pre_guard_peak": round(pre_peak, 4),
        "clip_guard_fired": guarded,
        "post_peak": round(float(np.abs(mix).max()) if mix.size else 0.0, 4),
        "length_samples": n,
    }
    return mix.astype(np.float32), info


def master_audio(audio: np.ndarray, sr: int,
                 target_lufs: float = TARGET_LUFS,
                 tp_ceiling_dbtp: float = TP_CEILING_DBTP,
                 lufs_tol: float = LUFS_TOLERANCE,
                 max_gain_db: float = MAX_GAIN_DB,
                 max_iters: int = MAX_ITERS) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Master to `target_lufs` with a `tp_ceiling_dbtp` true-peak ceiling.

    `pedalboard.Limiter` is a maximizer: it applies makeup drive toward its
    0 dBFS hard clipper (measured ≈ +4.75 dB at threshold -1). A naive
    "normalize to target, then limit" loop can never converge — the limiter
    re-inflates every pass. This loop therefore estimates the chain's loudness
    delta (`boost_est`, measured post-limiter minus pre-limiter) and aims the
    gain stage at `target - boost_est`; the estimate refines itself each pass
    and converges in ~2-3 iterations because the drive is near-constant in the
    limiter's linear region. True peak is enforced after the limiter: the
    pedalboard clipper caps at 0 dBFS, a fixed `ceiling_shift` moves that to
    the requested ceiling, and a final trim absorbs inter-sample overshoot.
    """
    from pedalboard import Limiter, Pedalboard

    a = _as_2d(audio).astype(np.float32)
    report: Dict[str, Any] = {
        "target_lufs": target_lufs,
        "tp_ceiling_dbtp": tp_ceiling_dbtp,
        "lufs_tol": lufs_tol,
        "input_lufs": round(integrated_lufs(a, sr), 2),
        "input_true_peak_dbtp": round(true_peak_dbfs(a, sr), 2),
        "iterations": [],
        "gain_capped": False,
    }
    ceiling_shift = np.float32(10.0 ** (tp_ceiling_dbtp / 20.0))
    boost_est = 0.0  # measured chain loudness delta (post-limiter - pre)
    for it in range(max_iters):
        cur = integrated_lufs(a, sr)
        pre_target = target_lufs - boost_est
        delta = pre_target - cur
        if abs(delta) > max_gain_db:
            delta = float(np.sign(delta)) * max_gain_db
            report["gain_capped"] = True
        if np.isfinite(delta) and abs(delta) > 1e-4:
            a = a * np.float32(10.0 ** (delta / 20.0))
        pre_lufs = integrated_lufs(a, sr)
        board = Pedalboard([Limiter(threshold_db=tp_ceiling_dbtp,
                                    release_ms=100.0)])
        # pedalboard wants (channels, samples)
        a = (board(a.T, sr).T * ceiling_shift).astype(np.float32)
        tp = true_peak_dbfs(a, sr)
        trim_db = 0.0
        if tp > tp_ceiling_dbtp:  # inter-sample overshoot -> trim
            trim_db = tp_ceiling_dbtp - tp  # negative
            a = (a * np.float32(10.0 ** (trim_db / 20.0))).astype(np.float32)
            tp = true_peak_dbfs(a, sr)
        lufs = integrated_lufs(a, sr)
        measured_boost = lufs - pre_lufs
        if np.isfinite(measured_boost):
            boost_est = measured_boost
        report["iterations"].append({
            "iter": it,
            "in_lufs": round(cur, 2),
            "gain_db": round(float(delta), 3),
            "post_lufs": round(lufs, 2),
            "true_peak_dbtp": round(tp, 2),
            "tp_trim_db": round(trim_db, 3),
            "chain_boost_db": round(float(measured_boost), 3)
            if np.isfinite(measured_boost) else None,
        })
        if abs(lufs - target_lufs) <= lufs_tol and tp <= tp_ceiling_dbtp + 0.05:
            break
    report["final_lufs"] = report["iterations"][-1]["post_lufs"]
    report["final_true_peak_dbtp"] = report["iterations"][-1]["true_peak_dbtp"]
    report["passed"] = bool(
        abs(report["final_lufs"] - target_lufs) <= lufs_tol
        and report["final_true_peak_dbtp"] <= tp_ceiling_dbtp + 0.05
    )
    return a, report


def master_file(in_path: Path, out_path: Path, sr_out: Optional[int] = None,
                subtype: str = "PCM_24", **kwargs) -> Dict[str, Any]:
    """Read a WAV, master it, write the result. Returns the report + paths."""
    import soundfile as sf

    in_path = Path(in_path)
    out_path = Path(out_path)
    audio, sr = sf.read(str(in_path), always_2d=True)
    mastered, report = master_audio(audio, sr, **kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), mastered, sr_out or sr, subtype=subtype)
    report.update({
        "in": str(in_path),
        "out": str(out_path),
        "sr": sr_out or sr,
        "subtype": subtype,
        "duration_s": round(mastered.shape[0] / float(sr), 3),
    })
    return report
