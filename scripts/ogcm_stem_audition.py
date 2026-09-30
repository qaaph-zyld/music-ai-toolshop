"""GATE S5a - wail finder: local stem audition, pyin ranking, whole-song timelines.

LOCAL IDENTIFICATION AID ONLY. The clips this script writes are slices of the
separated stems of the record (source audio). They exist so the user can hear
which stem carries the "wailing" sound. They must NEVER be uploaded to Suno -
Suno already rejected the raw chop. Nothing Suno-bound is produced here; the
Suno-bound pack (``audition_s5/s5_*``) is built by ``ogcm_sample.py`` from
synthesis only.

Stages (wall time of each is printed and stored in the JSON):
  1. clips   - cut the window from each candidate stem, loudness-match to
               -20 LUFS, peak-guard to <= -1 dBTP, write stem_<name>.wav
               (44.1 kHz stereo PCM_24).
  2. rank    - librosa.pyin on a mono 22.05 kHz copy of the window (fmin 65,
               fmax 2000, hop 256), per-stem wail metrics + documented
               ``wail_score`` -> stem_ranking.json (sorted).
  3. timeline - for the top-2 stems by wail_score: pyin over the WHOLE song in
               ~30 s chunks, per-2-s bins of high-register voiced activity
               (voiced AND midi >= 60) -> timeline_<name>.json with the top-5
               bins as mm:ss. Stops (and reports) if one stem exceeds the
               wall-time budget (~6 min); it never loops.

Usage:
    python scripts/ogcm_stem_audition.py [--start 54.0] [--end 67.0]
        [--outdir <dir>] [--no-timeline | --timeline-only]

``--timeline-only`` reuses stem_ranking.json (so a long run can be split
across calls); ``--no-timeline`` stops after stage 2.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import master  # noqa: E402
from toolshop.flip import sample_voices as sv  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
H6_DIR = STEMS / "htdemucs_6s" / "2Pac - Only God Can Judge Me"
V2_DIR = STEMS / "v2"
DEFAULT_OUT = STEMS / "flip_sample" / "audition_s5_stems"

# v2 backing-vocal residue: the "(vocals)" stem's "(Instrumental)" karaoke
# output. fnmatch treats "(" / ")" literally (only * ? [ ] are special).
BACKING_VOX_PATTERN = "*_(vocals)_*_(Instrumental)_*.wav"

OUT_SR = 44100
TARGET_LUFS = -20.0
TP_CEILING_DBTP = -1.0
MAX_GAIN_DB = 30.0
SUBTYPE = "PCM_24"

# pyin analysis
PYIN_SR = 22050
FMIN_HZ = 65.0
FMAX_HZ = 2000.0
FRAME = 2048
HOP = 256
HOP_S = HOP / PYIN_SR
# a frame only counts as voiced if it is not near-silent: above an absolute
# floor AND within REL dB of the stem's own p95 frame RMS (separated stems
# carry dither-level noise that pyin otherwise labels as voiced)
RMS_GATE_ABS_DB = -60.0
RMS_GATE_REL_DB = 35.0

# glide: |d midi| > GLIDE_ST per GLIDE_WIN_S inside a continuous voiced run
GLIDE_ST = 0.5
GLIDE_WIN_S = 0.05
# vibrato: spectrum of the detrended voiced MIDI curve
VIB_BAND_HZ = (4.0, 7.0)
VIB_ALL_HZ = (1.0, 15.0)
VIB_MIN_RUN_S = 0.4
VIB_TREND_S = 0.3
VIB_NFFT = 2048

# wail_score = sum(weight * term); every term is in [0, 1]
WAIL_WEIGHTS = {"V": 0.30, "R": 0.20, "G": 0.25, "B": 0.25}
V_SAT_RATIO = 0.60      # voiced_ratio at which V saturates at 1
G_SAT_SHARE = 0.30      # glide_share at which G saturates at 1
B_SAT_DEPTH_ST = 0.25   # vibrato depth (st) at which the vibrato term saturates
REG_LO, REG_HI, REG_FALL_ST = 60.0, 90.0, 12.0
WAIL_FORMULA = (
    "wail_score = 0.30*V + 0.20*R + 0.25*G + 0.25*B, each term in [0,1]. "
    "V = min(1, voiced_ratio/0.60). "
    "R = 1 if median voiced MIDI in [60,90]; linear fall to 0 over 12 st "
    "outside that band. "
    "G = min(1, glide_share/0.30). "
    "B = vibrato_score * min(1, vibrato_depth_st/0.25) "
    "(vibrato_score alone is ~0.6-0.8 on pitch noise, so it is weighted by "
    "the depth of the 4-7 Hz component). "
    "Silent stems score 0. A heuristic aid for where to LISTEN - only the "
    "user's ear decides what the wail is."
)

# timeline. Measured rank-stage cost: ~25 s of pyin per 13 s of audio at hop
# 256 (cost ~ frames x states^2), i.e. ~9.7 min for a 297 s stem - over the
# ~6 min budget. The timeline therefore runs pyin at hop 512 (every other
# setting identical); 2-s bins do not need 11.6 ms frames.
HIGH_REGISTER_MIDI = 60
BIN_S = 2.0
TIMELINE_HOP = 512
CHUNK_SAMPLES = 661_504             # = 2584*256 = 1292*512 samples ~ 30.0 s
TIMELINE_TIME_BUDGET_S = 360.0
TIMELINE_TOP_N = 2
SPACED_MIN_SEP_S = 8.0


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _r(x: float, nd: int = 4) -> Optional[float]:
    """JSON-safe rounded float (NaN/inf -> None)."""
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def mmss(t: float) -> str:
    t = int(round(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def candidate_stems() -> Dict[str, Path]:
    """Ordered name -> source path. Raises SystemExit on a missing stem or an
    ambiguous backing-vox glob (never guess)."""
    cands: Dict[str, Path] = {}
    for name in ("guitar", "other", "vocals", "bass"):
        p = H6_DIR / f"{name}.wav"
        if not p.is_file():
            raise SystemExit(f"[stem_audition] missing stem: {p}")
        cands[name] = p
    hits = sorted(n for n in os.listdir(V2_DIR)
                  if fnmatch.fnmatchcase(n, BACKING_VOX_PATTERN))
    if len(hits) != 1:
        raise SystemExit(f"[stem_audition] backing_vox glob "
                         f"'{BACKING_VOX_PATTERN}' matched {len(hits)} files "
                         f"in {V2_DIR}: {hits}")
    cands["backing_vox"] = V2_DIR / hits[0]
    return cands


def _voiced_runs(voiced: np.ndarray) -> List[Tuple[int, int]]:
    """Half-open [start, stop) runs of consecutive True."""
    v = np.concatenate([[False], np.asarray(voiced, dtype=bool), [False]])
    d = np.diff(v.astype(np.int8))
    return list(zip(np.flatnonzero(d == 1).tolist(),
                    np.flatnonzero(d == -1).tolist()))


# ---------------------------------------------------------------------------
# Pitch-curve metrics (pure numpy; unit-tested on synthetic curves)
# ---------------------------------------------------------------------------

def glide_share(midi: np.ndarray, voiced: np.ndarray,
                hop_s: float = HOP_S, win_s: float = GLIDE_WIN_S,
                thr_st: float = GLIDE_ST) -> float:
    """Share of voiced frames whose pitch moves more than ``thr_st``
    semitones per ``win_s`` seconds. Pitch is compared ``k`` frames apart
    (k = round(win_s/hop_s)) INSIDE a continuous voiced run, and the change
    is rescaled to exactly ``win_s``."""
    k = max(1, int(round(win_s / hop_s)))
    scale = win_s / (k * hop_s)
    n_valid = n_glide = 0
    for a, b in _voiced_runs(voiced):
        run = midi[a:b]
        if len(run) <= k:
            continue
        d = np.abs(run[k:] - run[:-k]) * scale
        n_valid += d.size
        n_glide += int((d > thr_st).sum())
    return n_glide / n_valid if n_valid else 0.0


def vibrato_metrics(midi: np.ndarray, voiced: np.ndarray,
                    hop_s: float = HOP_S) -> Tuple[float, float]:
    """(vibrato_score, vibrato_depth_st), weighted by run length.

    Per continuous voiced run >= VIB_MIN_RUN_S: subtract a moving-average
    trend (VIB_TREND_S), Hann-window, zero-padded FFT.
    vibrato_score = peak magnitude in 4-7 Hz / peak magnitude in 1-15 Hz.
    vibrato_depth_st = semitone amplitude of the 4-7 Hz peak.
    """
    freqs = np.fft.rfftfreq(VIB_NFFT, d=hop_s)
    band = (freqs >= VIB_BAND_HZ[0]) & (freqs <= VIB_BAND_HZ[1])
    full = (freqs >= VIB_ALL_HZ[0]) & (freqs <= VIB_ALL_HZ[1])
    trend_n = max(3, int(round(VIB_TREND_S / hop_s)))
    trend_n += 1 - trend_n % 2                      # odd
    min_frames = int(math.ceil(VIB_MIN_RUN_S / hop_s))
    tot_w = s_acc = a_acc = 0.0
    for a, b in _voiced_runs(voiced):
        if b - a < min_frames:
            continue
        y = np.asarray(midi[a:b], dtype=np.float64)
        pad = trend_n // 2
        trend = np.convolve(np.pad(y, pad, mode="edge"),
                            np.ones(trend_n) / trend_n, mode="valid")
        w = np.hanning(len(y))
        spec = np.abs(np.fft.rfft((y - trend) * w, VIB_NFFT))
        p_full = float(spec[full].max())
        if p_full <= 0.0:
            continue
        pk = float(spec[band].max())
        weight = float(b - a)
        s_acc += weight * pk / p_full
        a_acc += weight * 2.0 * pk / float(w.sum())
        tot_w += weight
    return (s_acc / tot_w, a_acc / tot_w) if tot_w else (0.0, 0.0)


def register_term(median_midi: float) -> float:
    """1.0 for a median voiced pitch in [60, 90]; linear fall-off outside."""
    if not math.isfinite(median_midi):
        return 0.0
    if median_midi < REG_LO:
        return max(0.0, 1.0 - (REG_LO - median_midi) / REG_FALL_ST)
    if median_midi > REG_HI:
        return max(0.0, 1.0 - (median_midi - REG_HI) / REG_FALL_ST)
    return 1.0


def wail_terms(voiced_ratio: float, median_midi: float, glide: float,
               vib_score: float, vib_depth_st: float) -> Dict[str, float]:
    return {"V": min(1.0, voiced_ratio / V_SAT_RATIO),
            "R": register_term(median_midi),
            "G": min(1.0, glide / G_SAT_SHARE),
            "B": vib_score * min(1.0, vib_depth_st / B_SAT_DEPTH_ST)}


def wail_score(terms: Dict[str, float]) -> float:
    return float(sum(WAIL_WEIGHTS[k] * terms[k] for k in WAIL_WEIGHTS))


def voiced_mask(f0: np.ndarray, flag: np.ndarray, rms_db: np.ndarray,
                p95_db: Optional[float] = None) -> Tuple[np.ndarray, float]:
    """pyin voiced flag AND finite f0 AND not near-silent. Returns
    (mask, gate_db). ``p95_db`` lets the timeline reuse the whole-song p95."""
    if p95_db is None:
        p95_db = float(np.percentile(rms_db, 95)) if len(rms_db) else -120.0
    gate_db = max(RMS_GATE_ABS_DB, p95_db - RMS_GATE_REL_DB)
    mask = np.asarray(flag, dtype=bool) & np.isfinite(f0) & (rms_db >= gate_db)
    return mask, gate_db


def hz_to_midi(f0: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return 69.0 + 12.0 * np.log2(np.asarray(f0, dtype=np.float64) / 440.0)


def bin_high_register(high: np.ndarray, covered: np.ndarray,
                      hop_s: float = HOP_S, bin_s: float = BIN_S
                      ) -> Tuple[np.ndarray, np.ndarray]:
    """Per-``bin_s`` fraction of covered frames that are high-register voiced.
    Returns (frac, n_covered_frames_per_bin)."""
    n = len(high)
    idx = (np.arange(n) * hop_s // bin_s).astype(int)
    n_bins = int(idx[-1]) + 1 if n else 0
    hits = np.bincount(idx, weights=(high & covered).astype(float),
                       minlength=n_bins)
    cnt = np.bincount(idx, weights=covered.astype(float), minlength=n_bins)
    frac = np.divide(hits, cnt, out=np.zeros(n_bins), where=cnt > 0)
    return frac, cnt


def top_bins(frac: np.ndarray, cnt: np.ndarray, bin_s: float = BIN_S,
             n: int = 5, min_sep_s: float = 0.0) -> List[dict]:
    """Top-``n`` bins by activity (ties -> earlier). ``min_sep_s`` > 0 keeps
    only bins at least that far from an already-chosen one."""
    order = sorted((i for i in range(len(frac)) if cnt[i] > 0 and frac[i] > 0),
                   key=lambda i: (-frac[i], i))
    chosen: List[int] = []
    for i in order:
        if all(abs(i - j) * bin_s >= min_sep_s for j in chosen):
            chosen.append(i)
        if len(chosen) == n:
            break
    return [{"rank": r + 1, "t0_s": round(i * bin_s, 2),
             "mmss": f"{mmss(i * bin_s)}-{mmss((i + 1) * bin_s)}",
             "high_register_frac": round(float(frac[i]), 4)}
            for r, i in enumerate(chosen)]


# ---------------------------------------------------------------------------
# Audio I/O + pyin
# ---------------------------------------------------------------------------

def read_window(path: Path, start_s: float, end_s: float
                ) -> Tuple[np.ndarray, int]:
    """Stereo float32 window; mono sources are duplicated to stereo."""
    sr = sf.info(str(path)).samplerate
    y, sr = sf.read(str(path), start=int(round(start_s * sr)),
                    stop=int(round(end_s * sr)), always_2d=True,
                    dtype="float32")
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return y, sr


def to_mono_22k(y: np.ndarray, sr: int) -> np.ndarray:
    import librosa
    mono = y.mean(axis=1).astype(np.float32)
    if sr != PYIN_SR:
        mono = librosa.resample(mono, orig_sr=sr, target_sr=PYIN_SR)
    return np.ascontiguousarray(mono, dtype=np.float32)


def frame_rms_db(y22: np.ndarray, hop: int = HOP) -> np.ndarray:
    import librosa
    rms = librosa.feature.rms(y=y22, frame_length=FRAME, hop_length=hop)[0]
    return 20.0 * np.log10(np.maximum(rms, 1e-10))


def run_pyin(y22: np.ndarray, hop: int = HOP
             ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    import librosa
    f0, flag, prob = librosa.pyin(y22, fmin=FMIN_HZ, fmax=FMAX_HZ,
                                  sr=PYIN_SR, frame_length=FRAME,
                                  hop_length=hop)
    return f0, flag, prob


def mid_share_700_3000(y: np.ndarray, sr: int) -> float:
    """Share of spectral energy in 700-3000 Hz (cross-check of the plan's
    measured per-stem numbers: guitar 0.54 / backing 0.35 / other 0.20)."""
    mono = y.mean(axis=1).astype(np.float64)
    spec = np.abs(np.fft.rfft(mono)) ** 2
    freqs = np.fft.rfftfreq(len(mono), d=1.0 / sr)
    tot = float(spec.sum())
    return float(spec[(freqs >= 700.0) & (freqs <= 3000.0)].sum() / tot) \
        if tot > 0 else 0.0


def measure_stem(y22: np.ndarray) -> Dict:
    """Window metrics for one mono 22.05 kHz stem slice."""
    f0, flag, prob = run_pyin(y22)
    rms_db = frame_rms_db(y22)
    n = min(len(f0), len(rms_db))
    f0, flag, prob, rms_db = f0[:n], flag[:n], prob[:n], rms_db[:n]
    voiced, gate_db = voiced_mask(f0, flag, rms_db)
    midi = hz_to_midi(f0)
    midi[~voiced] = np.nan
    vm = midi[voiced]
    silent = not voiced.any()
    if silent:
        med = p10 = p90 = float("nan")
    else:
        med = float(np.median(vm))
        p10, p90 = (float(x) for x in np.percentile(vm, [10, 90]))
    voiced_ratio = float(voiced.mean()) if n else 0.0
    gl = glide_share(midi, voiced)
    vib_score, vib_depth = vibrato_metrics(midi, voiced)
    terms = wail_terms(voiced_ratio, med, gl, vib_score, vib_depth)
    score = 0.0 if silent else wail_score(terms)
    return {"n_frames": int(n), "rms_gate_db": _r(gate_db, 2),
            "silent": bool(silent), "voiced_ratio": voiced_ratio,
            "median_midi": med, "p10_midi": p10, "p90_midi": p90,
            "glide_share": gl, "vibrato_score": vib_score,
            "vibrato_depth_st": vib_depth,
            "mean_voiced_prob": float(np.mean(prob)) if n else 0.0,
            "terms": terms, "wail_score": score}


def write_clip(y: np.ndarray, sr: int, out: Path) -> Dict:
    """Loudness-match to -20 LUFS, peak-guard to <= -1 dBTP, write PCM_24
    44.1 kHz stereo. Returns the measurements re-read from the written file."""
    if sr != OUT_SR:
        import librosa
        y = librosa.resample(y.T, orig_sr=sr, target_sr=OUT_SR).T
    y = np.ascontiguousarray(y, dtype=np.float32)
    lufs_in = master.integrated_lufs(y, OUT_SR)
    measurable = bool(np.isfinite(lufs_in) and lufs_in > -60.0)
    gain_db = (float(np.clip(TARGET_LUFS - lufs_in, -MAX_GAIN_DB, MAX_GAIN_DB))
               if measurable else 0.0)
    z = (y * np.float32(10.0 ** (gain_db / 20.0))).astype(np.float32)
    tp = master.true_peak_dbfs(z, OUT_SR)
    guard_db = 0.0
    if tp > TP_CEILING_DBTP:
        guard_db = TP_CEILING_DBTP - tp
        z = (z * np.float32(10.0 ** (guard_db / 20.0))).astype(np.float32)
    sf.write(str(out), z, OUT_SR, subtype=SUBTYPE)
    back, _ = sf.read(str(out), always_2d=True)
    return {"lufs_in": _r(lufs_in, 2), "measurable": measurable,
            "gain_db": _r(gain_db, 2), "peak_guard_db": _r(guard_db, 2),
            "lufs_out": _r(master.integrated_lufs(back, OUT_SR), 2),
            "true_peak_dbtp": _r(master.true_peak_dbfs(back, OUT_SR), 2)}


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def stage_rank(start_s: float, end_s: float, outdir: Path) -> Dict:
    outdir.mkdir(parents=True, exist_ok=True)
    cands = candidate_stems()
    per_stem: Dict[str, Dict] = {}
    rows: List[Dict] = []
    t_stage = time.perf_counter()
    for name, path in cands.items():
        t0 = time.perf_counter()
        y, sr = read_window(path, start_s, end_s)
        level = 20.0 * math.log10(max(float(np.sqrt(np.mean(
            y.astype(np.float64) ** 2))), 1e-10))
        level_mono = 20.0 * math.log10(max(float(np.sqrt(np.mean(
            y.astype(np.float64).mean(axis=1) ** 2))), 1e-10))
        mid_share = mid_share_700_3000(y, sr)
        y22 = to_mono_22k(y, sr)
        t_read = time.perf_counter() - t0

        t0 = time.perf_counter()
        clip_path = outdir / f"stem_{name}.wav"
        clip = write_clip(y, sr, clip_path)
        t_clip = time.perf_counter() - t0

        t0 = time.perf_counter()
        m = measure_stem(y22)
        t_pyin = time.perf_counter() - t0

        per_stem[name] = {"read_resample_s": round(t_read, 2),
                          "clip_write_s": round(t_clip, 2),
                          "pyin_s": round(t_pyin, 2)}
        med = m["median_midi"]
        rows.append({
            "name": name, "source": str(path), "clip": clip_path.name,
            "window_rms_dbfs": _r(level, 2),
            "window_rms_dbfs_monomix": _r(level_mono, 2),
            "mid_share_700_3000": _r(mid_share, 3),
            "voiced_ratio": _r(m["voiced_ratio"], 3),
            "median_midi": _r(med, 2),
            "median_note": (sv.note_name(int(round(med)))
                            if math.isfinite(med) else None),
            "p10_midi": _r(m["p10_midi"], 2), "p90_midi": _r(m["p90_midi"], 2),
            "glide_share": _r(m["glide_share"], 3),
            "vibrato_score": _r(m["vibrato_score"], 3),
            "vibrato_depth_st": _r(m["vibrato_depth_st"], 3),
            "mean_voiced_prob": _r(m["mean_voiced_prob"], 3),
            "rms_gate_db": m["rms_gate_db"], "silent": m["silent"],
            "terms": {k: _r(v, 3) for k, v in m["terms"].items()},
            "wail_score": _r(m["wail_score"], 4),
            "clip_measure": clip})
        print(f"[rank] {name:12s} level={level:6.1f} dBFS "
              f"voiced={m['voiced_ratio']:.3f} "
              f"med={'-' if not math.isfinite(med) else round(med, 1)} "
              f"glide={m['glide_share']:.3f} vib={m['vibrato_score']:.3f}"
              f"/{m['vibrato_depth_st']:.2f}st "
              f"-> wail_score={m['wail_score']:.4f}  "
              f"(read {t_read:.1f}s clip {t_clip:.1f}s pyin {t_pyin:.1f}s)",
              flush=True)
    total = time.perf_counter() - t_stage
    rows.sort(key=lambda r: (-(r["wail_score"] or 0.0), r["name"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    result = {
        "tool": "scripts/ogcm_stem_audition.py",
        "local_id_only": True,
        "warning": "stem clips contain SOURCE AUDIO - local identification "
                   "only, never upload to Suno",
        "window": {"start_s": start_s, "end_s": end_s},
        "skipped": {"piano": "effectively silent in the window "
                             "(-71.6 dBFS per the plan) - not analysed"},
        "pyin": {"fmin_hz": FMIN_HZ, "fmax_hz": FMAX_HZ, "sr": PYIN_SR,
                 "frame_length": FRAME, "hop_length": HOP,
                 "hop_s": round(HOP_S, 6),
                 "rms_gate": f"frame RMS >= max({RMS_GATE_ABS_DB} dBFS, "
                             f"p95 - {RMS_GATE_REL_DB} dB)"},
        "metric_defs": {
            "window_rms_dbfs": "RMS over both channels of the raw window "
                               "(window_rms_dbfs_monomix = RMS of the L+R "
                               "mean; the mono-mix figure is the one that "
                               "reproduces the plan's -33.5/-38.0/-38.2)",
            "voiced_ratio": "voiced frames / all frames in the window",
            "glide_share": f"share of voiced frames (inside continuous "
                           f"voiced runs) with |d midi| > {GLIDE_ST} st per "
                           f"{int(GLIDE_WIN_S * 1000)} ms",
            "vibrato_score": "peak |FFT| of the detrended voiced MIDI curve "
                             "in 4-7 Hz / peak in 1-15 Hz (run-length "
                             "weighted, runs >= 0.4 s)",
            "vibrato_depth_st": "semitone amplitude of the 4-7 Hz peak",
            "mid_share_700_3000": "share of window spectral energy in "
                                  "700-3000 Hz (cross-check of the plan)"},
        "wail_score_formula": WAIL_FORMULA,
        "weights": WAIL_WEIGHTS,
        "clip_spec": {"lufs": TARGET_LUFS, "tp_ceiling_dbtp": TP_CEILING_DBTP,
                      "sr": OUT_SR, "channels": 2, "subtype": SUBTYPE},
        "timing_s": {"rank_stage_total": round(total, 2),
                     "per_stem": per_stem},
        "ranking": rows}
    (outdir / "stem_ranking.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(f"[time] rank stage total: {total:.1f}s", flush=True)
    return result


def pyin_chunked(y22: np.ndarray, budget_s: float, hop: int = TIMELINE_HOP
                 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """pyin over the whole signal in ~30 s chunks (``CHUNK_SAMPLES``, a whole
    number of frames). Returns (f0, flag, prob, chunks_done, chunks_total);
    frames of chunks not reached stay NaN/False."""
    n_total = 1 + len(y22) // hop
    f0 = np.full(n_total, np.nan)
    flag = np.zeros(n_total, dtype=bool)
    prob = np.zeros(n_total)
    chunk_frames = CHUNK_SAMPLES // hop
    n_chunks = int(math.ceil(len(y22) / CHUNK_SAMPLES))
    t0 = time.perf_counter()
    done = 0
    for c in range(n_chunks):
        if time.perf_counter() - t0 > budget_s:
            break
        seg = y22[c * CHUNK_SAMPLES:(c + 1) * CHUNK_SAMPLES]
        a, b, p = run_pyin(seg, hop)
        keep = len(a) if c == n_chunks - 1 else chunk_frames
        g0 = c * chunk_frames
        g1 = min(n_total, g0 + keep)
        f0[g0:g1], flag[g0:g1], prob[g0:g1] = a[:g1 - g0], b[:g1 - g0], p[:g1 - g0]
        done += 1
        print(f"         chunk {c + 1}/{n_chunks} "
              f"({time.perf_counter() - t0:.0f}s elapsed)", flush=True)
    return f0, flag, prob, done, n_chunks


def stage_timeline(name: str, path: Path, window: Tuple[float, float],
                   outdir: Path, budget_s: float = TIMELINE_TIME_BUDGET_S
                   ) -> Dict:
    t_all = time.perf_counter()
    info = sf.info(str(path))
    y, sr = read_window(path, 0.0, info.frames / info.samplerate)
    y22 = to_mono_22k(y, sr)
    del y
    hop = TIMELINE_HOP
    hop_s = hop / PYIN_SR
    rms_db = frame_rms_db(y22, hop)
    t_prep = time.perf_counter() - t_all

    f0, flag, prob, done, total = pyin_chunked(y22, budget_s, hop)
    n = len(f0)
    covered = np.zeros(n, dtype=bool)
    covered[:min(n, done * (CHUNK_SAMPLES // hop))] = True
    if done == total:
        covered[:] = True
    rms_db = rms_db[:n]
    p95 = float(np.percentile(rms_db, 95))
    voiced, gate_db = voiced_mask(f0, flag, rms_db, p95_db=p95)
    midi = hz_to_midi(f0)
    high = voiced & (midi >= HIGH_REGISTER_MIDI)
    frac, cnt = bin_high_register(high, covered, hop_s=hop_s)
    truncated = done < total
    t_axis = np.arange(n) * hop_s
    in_win = covered & (t_axis >= window[0]) & (t_axis < window[1])
    wall = time.perf_counter() - t_all
    result = {
        "stem": name, "source": str(path), "local_id_only": True,
        "rule": f"high-register voiced activity = pyin voiced AND midi >= "
                f"{HIGH_REGISTER_MIDI} AND frame RMS >= {gate_db:.1f} dBFS "
                f"(max({RMS_GATE_ABS_DB}, song p95 {p95:.1f} - "
                f"{RMS_GATE_REL_DB}))",
        "pyin": {"fmin_hz": FMIN_HZ, "fmax_hz": FMAX_HZ, "sr": PYIN_SR,
                 "frame_length": FRAME, "hop_length": hop,
                 "hop_note": "hop 512 (not the ranking's 256): measured "
                             "~25 s pyin per 13 s at hop 256 => ~9.7 min per "
                             "stem, over the ~6 min budget; all other pyin "
                             "settings identical"},
        "bin_s": BIN_S, "chunk_s": round(CHUNK_SAMPLES / PYIN_SR, 3),
        "chunks_done": done, "chunks_total": total, "truncated": truncated,
        "budget_s": budget_s,
        "covered_s": round(float(covered.sum()) * hop_s, 1),
        "song_mean_frac": _r(float(high[covered].mean())
                             if covered.any() else 0.0, 4),
        "plan_window": {"start_s": window[0], "end_s": window[1],
                        "mean_frac": _r(float(high[in_win].mean())
                                        if in_win.any() else 0.0, 4)},
        "top5_bins": top_bins(frac, cnt, n=5),
        "top5_bins_spaced_8s": top_bins(frac, cnt, n=5,
                                        min_sep_s=SPACED_MIN_SEP_S),
        "bins_frac": [round(float(v), 3) for v in frac],
        "wall_s": {"total": round(wall, 1), "read_resample_rms": round(t_prep, 1),
                   "pyin": round(wall - t_prep, 1)}}
    (outdir / f"timeline_{name}.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    flag_txt = "  ** TRUNCATED at budget **" if truncated else ""
    print(f"[timeline] {name}: {done}/{total} chunks, wall {wall:.1f}s{flag_txt}")
    for b in result["top5_bins"]:
        print(f"           top{b['rank']}: {b['mmss']}  "
              f"frac={b['high_register_frac']}")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="GATE S5a wail finder "
                                 "(LOCAL ID ONLY - not for Suno).")
    ap.add_argument("--start", type=float, default=54.0)
    ap.add_argument("--end", type=float, default=67.0)
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--no-timeline", action="store_true",
                   help="stop after clips + ranking")
    g.add_argument("--timeline-only", action="store_true",
                   help="reuse stem_ranking.json; run only the timelines")
    ap.add_argument("--timeline-top", type=int, default=TIMELINE_TOP_N,
                    help="how many of the top-ranked stems get a whole-song "
                         "timeline (default 2)")
    ap.add_argument("--timeline-stems", default=None,
                    help="comma-separated stem names to time-line instead of "
                         "the top-N (lets a long run be split across calls)")
    ap.add_argument("--time-budget-s", type=float,
                    default=TIMELINE_TIME_BUDGET_S,
                    help="per-stem wall-time budget for the whole-song "
                         "timeline (default 360 s)")
    args = ap.parse_args(argv)
    outdir = Path(args.outdir)
    if not args.end > args.start >= 0.0:
        raise SystemExit("[stem_audition] need 0 <= --start < --end")

    if args.timeline_only:
        rk = outdir / "stem_ranking.json"
        if not rk.is_file():
            raise SystemExit(f"[stem_audition] {rk} missing - run the rank "
                             f"stage first")
        result = json.loads(rk.read_text(encoding="utf-8"))
        window = (result["window"]["start_s"], result["window"]["end_s"])
    else:
        result = stage_rank(args.start, args.end, outdir)
        window = (args.start, args.end)

    if args.no_timeline:
        print("[stem_audition] --no-timeline: done after ranking")
        return 0

    cands = candidate_stems()
    if args.timeline_stems:
        top = [s.strip() for s in args.timeline_stems.split(",") if s.strip()]
        unknown = [s for s in top if s not in cands]
        if unknown:
            raise SystemExit(f"[stem_audition] unknown stem(s): {unknown}")
        print(f"[timeline] explicit stems: {top}", flush=True)
    else:
        top = [r["name"] for r in result["ranking"] if not r["silent"]
               ][:args.timeline_top]
        print(f"[timeline] top-{args.timeline_top} by wail_score: {top}",
              flush=True)
    for name in top:
        stage_timeline(name, cands[name], window, outdir, args.time_budget_s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
